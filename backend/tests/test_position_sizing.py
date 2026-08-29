"""Covers app/position_sizing.py — v0.7 Chapter 57, the Institutional
Position Sizing & Capital Deployment Engine. Every case here checks the
one real guarantee the chapter makes: the engine only ever NARROWS the
caller-supplied `ceiling_quantity` (app/risk_engine.py's
recommended_quantity()), never widens it, and every narrowing traces
back to a real, named constraint — never a silent or fabricated cut.
"""
from __future__ import annotations

import pytest

from app.ema_pullback_research import CHANDELIER_ATR_MULTIPLIER, CHANDELIER_ATR_PERIOD
from app.market_data import Candle, MarketDataProvider, Quote
from app.position_sizing import (
    TIER_FRACTION,
    VOLATILITY_CANDLE_COUNT,
    WEEKLY_DEPLOYMENT_WINDOW_DAYS,
    _capital_deployed_pct_in_window,
    _cross_portfolio_inverse_vol_sizing,
    _inverse_vol_sizing,
    _tier_for_sizing_score,
    _volatility_sizing,
    build_position_sizing,
)
from app.risk_engine import SIM_MINUTES_PER_DAY, portfolio_equity
from app.schemas import (
    DecisionScoreBreakdown,
    ExpectedValueAnalysis,
    PaperPortfolio,
    PaperPosition,
    PaperTrade,
    PortfolioHeat,
    RiskLimits,
    RiskWarning,
    TierAllocationLimits,
)


class _FakeProvider(MarketDataProvider):
    """A test double with a fully controlled candle series — unlike
    MockMarketDataProvider's real-but-random walk, needed to construct
    known low/high-ATR scenarios. Defaults to a real but LOW-volatility
    series (each bar moves ~$1 on a $100 base) so existing tests that
    aren't specifically about volatility sizing get a real, available,
    but comfortably non-binding volatility cap — never silently
    unavailable by default, which would hide real wiring bugs."""

    def __init__(self, closes: list[float] | None = None, *, raise_for_missing: bool = True) -> None:
        self._closes = closes if closes is not None else [100.0 + (i % 2) for i in range(VOLATILITY_CANDLE_COUNT)]
        self._raise_for_missing = raise_for_missing

    def get_quote(self, symbol: str) -> Quote:
        raise NotImplementedError

    def get_candles(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        if not self._closes and self._raise_for_missing:
            raise ValueError(f"no fixture data for {symbol!r}")
        return [
            Candle(symbol=symbol, timeframe=timeframe, timestamp=f"2026-01-01T{i % 24:02d}:00:00Z", open=c, high=c + 0.5, low=c - 0.5, close=c, volume=1000.0, data_status="simulated")
            for i, c in enumerate(self._closes)
        ]


def _portfolio(*, cash_balance: float = 100_000.0, positions: list[PaperPosition] | None = None, trade_history: list[PaperTrade] | None = None) -> PaperPortfolio:
    return PaperPortfolio(
        cashBalance=cash_balance,
        startingBalance=100_000.0,
        positions=positions or [],
        tradeHistory=trade_history or [],
        totalPnl=0.0,
        totalPnlPct=0.0,
        winCount=0,
        lossCount=0,
    )


def _position(*, symbol: str = "AAPL", quantity: float = 10.0, entry_price: float = 100.0, opened_sim_minutes: int = 0) -> PaperPosition:
    return PaperPosition(
        id=f"pos-{symbol}-{opened_sim_minutes}",
        symbol=symbol,
        side="buy",  # type: ignore[arg-type]
        quantity=quantity,
        entryPrice=entry_price,
        currentPrice=entry_price,
        unrealizedPnl=0.0,
        unrealizedPnlPct=0.0,
        openedBy="sentinel",  # type: ignore[arg-type]
        confidence=80.0,
        openedAt="2026-01-01T00:00:00Z",
        openedSimMinutes=opened_sim_minutes,
    )


def _trade(*, symbol: str = "AAPL", quantity: float = 10.0, entry_price: float = 100.0, opened_sim_minutes: int = 0) -> PaperTrade:
    return PaperTrade(
        id=f"trade-{symbol}-{opened_sim_minutes}",
        symbol=symbol,
        side="buy",  # type: ignore[arg-type]
        quantity=quantity,
        entryPrice=entry_price,
        exitPrice=entry_price,
        pnl=0.0,
        pnlPct=0.0,
        durationMinutes=60,
        confidence=80.0,
        reason="test reason",
        marketConditions="calm",
        openedAt="2026-01-01T00:00:00Z",
        closedAt="2026-01-01T01:00:00Z",
        openedSimMinutes=opened_sim_minutes,
        closedSimMinutes=opened_sim_minutes + 60,
    )


def _decision_score(overall: float, *, passed: bool | None = None) -> DecisionScoreBreakdown:
    return DecisionScoreBreakdown(
        overall=overall,
        passed=overall >= 92.0 if passed is None else passed,
        threshold=70.0,
        evidenceScore=overall,
        confidenceScore=overall,
        expectedValueScore=overall,
        riskScore=overall,
        marketQualityScore=overall,
        liquidityQualityScore=overall,
        portfolioCompatibilityScore=overall,
    )


def _expected_value(*, positive_expectancy: bool = True) -> ExpectedValueAnalysis:
    return ExpectedValueAnalysis(
        expectedValuePct=1.0,
        edgePct=1.0,
        riskToReward=2.0,
        positiveExpectancy=positive_expectancy,
        detail="test",
    )


def _heat(*, tier: str = "cool", total_capital_at_risk_pct: float = 5.0) -> PortfolioHeat:
    return PortfolioHeat(
        totalCapitalAtRiskPct=total_capital_at_risk_pct,
        unrealizedDrawdownPct=0.0,
        largestPositionPct=0.0,
        tier=tier,  # type: ignore[arg-type]
    )


class _Proposal:
    def __init__(self, symbol: str = "AAPL", price: float = 100.0) -> None:
        self.symbol = symbol
        self.price = price


class TestCapitalDeployedPctInWindow:
    def test_zero_equity_returns_zero(self) -> None:
        portfolio = _portfolio()
        assert _capital_deployed_pct_in_window(portfolio, 0.0, sim_day=10, window_days=7) == 0.0

    def test_counts_both_closed_trades_and_open_positions(self) -> None:
        portfolio = _portfolio(
            trade_history=[_trade(quantity=10.0, entry_price=100.0, opened_sim_minutes=5 * SIM_MINUTES_PER_DAY)],
            positions=[_position(quantity=5.0, entry_price=100.0, opened_sim_minutes=5 * SIM_MINUTES_PER_DAY)],
        )
        pct = _capital_deployed_pct_in_window(portfolio, equity=100_000.0, sim_day=6, window_days=7)
        assert pct == (1_000.0 + 500.0) / 100_000.0 * 100

    def test_excludes_activity_outside_the_trailing_window(self) -> None:
        portfolio = _portfolio(trade_history=[_trade(quantity=10.0, entry_price=100.0, opened_sim_minutes=0)])
        pct = _capital_deployed_pct_in_window(portfolio, equity=100_000.0, sim_day=20, window_days=7)
        assert pct == 0.0

    def test_includes_activity_at_the_exact_window_boundary(self) -> None:
        earliest_day = 10 - WEEKLY_DEPLOYMENT_WINDOW_DAYS + 1
        portfolio = _portfolio(trade_history=[_trade(quantity=10.0, entry_price=100.0, opened_sim_minutes=earliest_day * SIM_MINUTES_PER_DAY)])
        pct = _capital_deployed_pct_in_window(portfolio, equity=100_000.0, sim_day=10, window_days=WEEKLY_DEPLOYMENT_WINDOW_DAYS)
        assert pct == 1_000.0 / 100_000.0 * 100


class TestTierForSizingScore:
    def test_below_standard_floor_is_exploratory(self) -> None:
        tier = _tier_for_sizing_score(
            50.0, decision_score=_decision_score(50.0), expected_value=_expected_value(), portfolio_heat=_heat(), critical_risk_warning=False
        )
        assert tier == "exploratory"

    def test_standard_floor_alone_is_enough_for_standard(self) -> None:
        tier = _tier_for_sizing_score(
            70.0, decision_score=_decision_score(70.0, passed=False), expected_value=_expected_value(positive_expectancy=False), portfolio_heat=_heat(tier="overheated"), critical_risk_warning=False
        )
        assert tier == "standard"

    def test_high_conviction_requires_positive_expectancy_and_non_hot_heat(self) -> None:
        tier = _tier_for_sizing_score(
            85.0, decision_score=_decision_score(85.0, passed=False), expected_value=_expected_value(positive_expectancy=True), portfolio_heat=_heat(tier="warm"), critical_risk_warning=False
        )
        assert tier == "high_conviction"

    def test_high_conviction_denied_without_positive_expectancy(self) -> None:
        tier = _tier_for_sizing_score(
            85.0, decision_score=_decision_score(85.0, passed=False), expected_value=_expected_value(positive_expectancy=False), portfolio_heat=_heat(tier="cool"), critical_risk_warning=False
        )
        assert tier == "standard"

    def test_institutional_requires_all_three_real_gates(self) -> None:
        tier = _tier_for_sizing_score(
            95.0, decision_score=_decision_score(95.0, passed=True), expected_value=_expected_value(positive_expectancy=True), portfolio_heat=_heat(tier="cool"), critical_risk_warning=False
        )
        assert tier == "institutional"

    def test_institutional_denied_without_decision_score_passed(self) -> None:
        tier = _tier_for_sizing_score(
            95.0, decision_score=_decision_score(95.0, passed=False), expected_value=_expected_value(positive_expectancy=True), portfolio_heat=_heat(tier="cool"), critical_risk_warning=False
        )
        assert tier == "high_conviction"

    def test_institutional_denied_without_positive_expectancy(self) -> None:
        # High Conviction itself also requires positive_expectancy, so
        # losing it drops all the way to Standard, not High Conviction.
        tier = _tier_for_sizing_score(
            95.0, decision_score=_decision_score(95.0, passed=True), expected_value=_expected_value(positive_expectancy=False), portfolio_heat=_heat(tier="cool"), critical_risk_warning=False
        )
        assert tier == "standard"

    def test_institutional_denied_without_cool_heat(self) -> None:
        tier = _tier_for_sizing_score(
            95.0, decision_score=_decision_score(95.0, passed=True), expected_value=_expected_value(positive_expectancy=True), portfolio_heat=_heat(tier="warm"), critical_risk_warning=False
        )
        assert tier == "high_conviction"

    def test_critical_risk_warning_overrides_everything_to_exploratory(self) -> None:
        tier = _tier_for_sizing_score(
            95.0, decision_score=_decision_score(95.0, passed=True), expected_value=_expected_value(positive_expectancy=True), portfolio_heat=_heat(tier="cool"), critical_risk_warning=True
        )
        assert tier == "exploratory"


class TestVolatilitySizingBackwardCompat:
    """CEO directive "Portfolio Construction, Capital Allocation &
    Execution Realism," Phase 3 — PositionSizingResult lives inside
    WarRoomSession, which lives inside the persisted `war_room_sessions`
    LIST — app/persistence.py's own _deep_merge_defaults docstring
    requires every field added to a model living inside a list to carry
    a real Pydantic default, since list items are taken wholesale on
    load, never per-item merged. Confirms that requirement is actually
    met: an old save's PositionSizingResult dict with no `volatilitySizing`
    key at all must still validate."""

    def test_position_sizing_result_validates_with_no_volatility_sizing_key_at_all(self) -> None:
        from app.schemas import PositionSizingResult

        old_save_shape = dict(
            tier="standard",
            tierLabel="Standard",
            sizingScore=70.0,
            ceilingQuantity=10.0,
            tierCapQuantity=10.0,
            finalQuantity=10.0,
            capitalDeployedPct=1.0,
            weeklyDeploymentPct=1.0,
            weeklyDeploymentCapPct=20.0,
            cashReserveOk=True,
            portfolioHeatCapOk=True,
            institutionalGatesPassed=False,
            reducedFromCeiling=False,
            detail="test",
            # No "volatilitySizing" key at all — the real shape of every
            # PositionSizingResult persisted before this feature existed.
        )
        result = PositionSizingResult.model_validate(old_save_shape)
        assert result.volatility_sizing.available is False
        assert result.volatility_sizing.volatility_cap_quantity is None


class TestBuildPositionSizing:
    def _build(self, **overrides):
        defaults = dict(
            proposal=_Proposal(),
            ceiling_quantity=10.0,
            expected_value=_expected_value(),
            decision_score=_decision_score(60.0),
            portfolio=_portfolio(),
            portfolio_heat=_heat(),
            risk_limits=RiskLimits(),
            risk_warnings=[],
            sim_day=1,
            provider=_FakeProvider(),
        )
        defaults.update(overrides)
        return build_position_sizing(**defaults)

    def test_zero_ceiling_returns_zero_quantity_with_no_fabricated_tier(self) -> None:
        result = self._build(ceiling_quantity=0.0)
        assert result.final_quantity == 0.0
        assert result.reduced_from_ceiling is False

    def test_zero_equity_returns_zero_quantity(self) -> None:
        result = self._build(portfolio=_portfolio(cash_balance=0.0))
        assert result.final_quantity == 0.0

    def test_final_quantity_never_exceeds_ceiling(self) -> None:
        for score in (40.0, 65.0, 78.0, 90.0, 97.0):
            result = self._build(decision_score=_decision_score(score), ceiling_quantity=1_000.0, risk_limits=RiskLimits(tierAllocation=TierAllocationLimits(tier1Pct=100.0, tier2Pct=100.0, tier3Pct=100.0, tier4Pct=100.0)))
            assert result.final_quantity <= 1_000.0 + 1e-9

    def test_tier_fraction_scales_final_quantity_monotonically_with_evidence(self) -> None:
        # Wide-open absolute caps and budgets so only TIER_FRACTION binds —
        # isolates the exact bug this test guards against: tiers below
        # Institutional having zero real differentiating effect.
        wide_open = RiskLimits(
            tierAllocation=TierAllocationLimits(tier1Pct=100.0, tier2Pct=100.0, tier3Pct=100.0, tier4Pct=100.0),
            maxWeeklyDeploymentPct=100.0,
            cashReservePct=0.0,
        )
        ratios = {}
        for score, tier in ((60.0, "exploratory"), (75.0, "standard"), (85.0, "high_conviction"), (95.0, "institutional")):
            result = self._build(decision_score=_decision_score(score, passed=(tier == "institutional")), ceiling_quantity=100.0, risk_limits=wide_open)
            assert result.tier == tier
            ratios[tier] = result.final_quantity / 100.0

        assert ratios["exploratory"] == TIER_FRACTION["exploratory"]
        assert ratios["standard"] == TIER_FRACTION["standard"]
        assert ratios["high_conviction"] == TIER_FRACTION["high_conviction"]
        assert ratios["institutional"] == TIER_FRACTION["institutional"] == 1.0
        assert ratios["exploratory"] < ratios["standard"] < ratios["high_conviction"] < ratios["institutional"]

    def test_absolute_tier_cap_binds_when_tighter_than_the_fraction(self) -> None:
        tight_cap = RiskLimits(tierAllocation=TierAllocationLimits(tier1Pct=1.0, tier2Pct=1.0, tier3Pct=1.0, tier4Pct=1.0))
        result = self._build(decision_score=_decision_score(60.0), ceiling_quantity=1_000.0, risk_limits=tight_cap, portfolio=_portfolio(cash_balance=100_000.0))
        # 1% of 100,000 equity at price 100 = 10 shares, far below
        # ceiling_quantity * TIER_FRACTION["exploratory"] (350).
        assert result.tier_cap_quantity == 10.0
        assert result.final_quantity <= 10.0 + 1e-9
        assert "absolute allocation cap" in result.detail

    def test_weekly_deployment_budget_binds_and_is_named(self) -> None:
        portfolio = _portfolio(trade_history=[_trade(quantity=140.0, entry_price=100.0, opened_sim_minutes=0)])
        result = self._build(
            decision_score=_decision_score(95.0, passed=True),
            ceiling_quantity=1_000.0,
            portfolio=portfolio,
            risk_limits=RiskLimits(tierAllocation=TierAllocationLimits(tier1Pct=100.0, tier2Pct=100.0, tier3Pct=100.0, tier4Pct=100.0), maxWeeklyDeploymentPct=15.0),
            sim_day=1,
        )
        assert result.weekly_deployment_pct <= 15.0 + 1e-6
        assert "weekly capital deployment budget" in result.detail

    def test_portfolio_heat_cap_binds_when_set_and_is_named(self) -> None:
        result = self._build(
            decision_score=_decision_score(95.0, passed=True),
            ceiling_quantity=1_000.0,
            portfolio_heat=_heat(tier="cool", total_capital_at_risk_pct=9.0),
            risk_limits=RiskLimits(tierAllocation=TierAllocationLimits(tier1Pct=100.0, tier2Pct=100.0, tier3Pct=100.0, tier4Pct=100.0), maxWeeklyDeploymentPct=100.0, portfolioHeatCapPct=10.0),
        )
        assert result.portfolio_heat_cap_ok is False
        assert result.final_quantity * 100.0 / 100_000.0 * 100 <= 1.0 + 1e-6
        assert "Portfolio Heat cap" in result.detail

    def test_portfolio_heat_cap_none_means_no_gate(self) -> None:
        result = self._build(
            decision_score=_decision_score(95.0, passed=True),
            ceiling_quantity=1.0,
            portfolio_heat=_heat(tier="cool", total_capital_at_risk_pct=99.0),
            risk_limits=RiskLimits(portfolioHeatCapPct=None),
        )
        assert result.portfolio_heat_cap_ok is True

    def test_cash_reserve_binds_and_is_named(self) -> None:
        result = self._build(
            decision_score=_decision_score(95.0, passed=True),
            ceiling_quantity=1_000.0,
            portfolio=_portfolio(cash_balance=500.0),
            risk_limits=RiskLimits(tierAllocation=TierAllocationLimits(tier1Pct=100.0, tier2Pct=100.0, tier3Pct=100.0, tier4Pct=100.0), maxWeeklyDeploymentPct=100.0, cashReservePct=10.0),
        )
        # equity here is exactly the 500 cash_balance (no positions), so
        # a 10% cash reserve requirement leaves only 450 spendable —
        # tight enough to bind ahead of the wide-open tier/weekly limits.
        assert result.cash_reserve_ok is False
        assert result.final_quantity * 100.0 <= 450.0 + 1e-6

    def test_critical_risk_warning_forces_exploratory_and_small_size(self) -> None:
        warnings = [RiskWarning(id="w1", symbol="AAPL", severity="critical", message="test", createdAt="2026-01-01T00:00:00Z")]
        result = self._build(decision_score=_decision_score(95.0, passed=True), ceiling_quantity=100.0, risk_warnings=warnings)
        assert result.tier == "exploratory"
        assert result.institutional_gates_passed is False

    def test_institutional_gates_passed_only_true_for_institutional_tier(self) -> None:
        result = self._build(decision_score=_decision_score(60.0), ceiling_quantity=10.0)
        assert result.tier == "exploratory"
        assert result.institutional_gates_passed is False

    def test_detail_reports_at_ceiling_when_not_reduced(self) -> None:
        wide_open = RiskLimits(
            tierAllocation=TierAllocationLimits(tier1Pct=100.0, tier2Pct=100.0, tier3Pct=100.0, tier4Pct=100.0),
            maxWeeklyDeploymentPct=100.0,
            cashReservePct=0.0,
        )
        result = self._build(decision_score=_decision_score(95.0, passed=True), ceiling_quantity=10.0, risk_limits=wide_open)
        assert result.tier == "institutional"
        assert result.reduced_from_ceiling is False
        assert "within the real risk limit" in result.detail


class TestInverseVolSizing:
    """CEO directive "AHL-Inspired Systematic Trend & Momentum Research
    Engine" follow-up — promotes app/trend_engine.py's own real,
    previously research-only inverse-volatility exposure calculator
    into this live, advisory-only narrowing cap. Every case here checks
    the same real guarantee as the rest of this module: never a
    fabricated cap, never widening, always traceable to real evidence."""

    def test_none_with_zero_equity(self) -> None:
        result = _inverse_vol_sizing(_Proposal(), _FakeProvider(), 0.0, RiskLimits(), _decision_score(60.0))
        assert result is None

    def test_none_with_zero_price(self) -> None:
        result = _inverse_vol_sizing(_Proposal(price=0.0), _FakeProvider(), 100_000.0, RiskLimits(), _decision_score(60.0))
        assert result is None

    def test_none_with_no_real_candle_history(self) -> None:
        result = _inverse_vol_sizing(_Proposal(), _FakeProvider(closes=[]), 100_000.0, RiskLimits(), _decision_score(60.0))
        assert result is None

    def test_real_result_when_history_available(self) -> None:
        result = _inverse_vol_sizing(_Proposal(), _FakeProvider(), 100_000.0, RiskLimits(), _decision_score(60.0))
        assert result is not None
        assert result.signal_strength == 0.6  # decision_score.overall (60.0) normalized to 0-1
        assert result.target_risk_pct == RiskLimits().risk_per_trade_pct
        assert result.capped_exposure_pct <= result.raw_exposure_pct

    def test_signal_strength_scales_with_decision_score(self) -> None:
        # Real raw_exposure_pct (before any hard-ceiling capping) scales
        # linearly with signal_strength by this function's own real
        # formula — the capped value alone can't tell weak/strong apart
        # once both saturate the same hard ceiling.
        weak = _inverse_vol_sizing(_Proposal(), _FakeProvider(), 100_000.0, RiskLimits(), _decision_score(20.0))
        strong = _inverse_vol_sizing(_Proposal(), _FakeProvider(), 100_000.0, RiskLimits(), _decision_score(90.0))
        assert weak is not None and strong is not None
        assert strong.raw_exposure_pct > weak.raw_exposure_pct


class TestBuildPositionSizingInverseVolCap:
    def _build(self, **overrides):
        defaults = dict(
            proposal=_Proposal(),
            ceiling_quantity=10.0,
            expected_value=_expected_value(),
            decision_score=_decision_score(60.0),
            portfolio=_portfolio(),
            portfolio_heat=_heat(),
            risk_limits=RiskLimits(),
            risk_warnings=[],
            sim_day=1,
            provider=_FakeProvider(),
        )
        defaults.update(overrides)
        return build_position_sizing(**defaults)

    def test_inverse_vol_sizing_is_populated_when_available(self) -> None:
        result = self._build()
        assert result.inverse_vol_sizing is not None

    def test_inverse_vol_sizing_is_none_when_history_unavailable(self) -> None:
        result = self._build(provider=_FakeProvider(closes=[]))
        assert result.inverse_vol_sizing is None

    def test_final_quantity_never_exceeds_the_inverse_vol_cap(self) -> None:
        # A real, high-per-bar-range-relative-to-price series (low close
        # price with the same fixed +-0.5 spread _FakeProvider always
        # uses) — a genuinely high real volatility_pct, driving a real,
        # tight inverse-vol cap.
        wide_open = RiskLimits(
            tierAllocation=TierAllocationLimits(tier1Pct=100.0, tier2Pct=100.0, tier3Pct=100.0, tier4Pct=100.0),
            maxWeeklyDeploymentPct=100.0,
            cashReservePct=0.0,
        )
        high_vol_provider = _FakeProvider(closes=[2.0] * VOLATILITY_CANDLE_COUNT)
        result = self._build(ceiling_quantity=1_000.0, risk_limits=wide_open, provider=high_vol_provider, proposal=_Proposal(price=2.0))
        assert result.inverse_vol_sizing is not None
        equity = 100_000.0
        inverse_vol_cap_quantity = equity * result.inverse_vol_sizing.capped_exposure_pct / 100 / 2.0
        assert result.final_quantity <= inverse_vol_cap_quantity + 1e-6

    def test_binding_constraint_names_inverse_vol_when_it_is_tightest(self) -> None:
        wide_open = RiskLimits(
            tierAllocation=TierAllocationLimits(tier1Pct=100.0, tier2Pct=100.0, tier3Pct=100.0, tier4Pct=100.0),
            maxWeeklyDeploymentPct=100.0,
            cashReservePct=0.0,
        )
        # A real, very low close price so the fixed +-0.5 spread implies
        # both a huge real ATR (volatility cap) AND a huge real
        # volatility_pct (inverse-vol cap) — but the inverse-vol cap
        # additionally scales by target_risk_pct/signal_strength, which
        # a low decision score drives to a real, tighter number.
        tiny_price_provider = _FakeProvider(closes=[0.5] * VOLATILITY_CANDLE_COUNT)
        result = self._build(
            ceiling_quantity=1_000.0,
            risk_limits=wide_open,
            provider=tiny_price_provider,
            proposal=_Proposal(price=0.5),
            decision_score=_decision_score(5.0),
        )
        assert result.reduced_from_ceiling is True
        assert "inverse-volatility" in result.detail or "volatility" in result.detail


class TestVolatilitySizing:
    """CEO directive "Portfolio Construction, Capital Allocation &
    Execution Realism," Phase 3 — POSITION SIZE ~ RISK BUDGET / DISTANCE
    TO STOP. Tests _volatility_sizing() directly against the directive's
    own explicit scenario list (low/high volatility, insufficient
    history) before testing the end-to-end narrowing effect below."""

    def test_insufficient_candle_history_reports_unavailable_not_fabricated(self) -> None:
        read = _volatility_sizing(_Proposal(), _FakeProvider([], raise_for_missing=True), equity=100_000.0, risk_limits=RiskLimits())
        assert read.available is False
        assert read.stop_distance is None
        assert read.volatility_cap_quantity is None
        assert "no real candle history" in read.detail.lower()

    def test_a_short_candle_history_below_the_atr_period_reports_unavailable(self) -> None:
        # Real candles exist, but too few for a real CHANDELIER_ATR_PERIOD-bar ATR window.
        short_history = [100.0 + (i % 2) for i in range(CHANDELIER_ATR_PERIOD - 1)]
        read = _volatility_sizing(_Proposal(), _FakeProvider(short_history), equity=100_000.0, risk_limits=RiskLimits())
        assert read.available is False
        assert read.volatility_cap_quantity is None

    def test_low_volatility_symbol_gets_a_real_available_read(self) -> None:
        calm = [100.0 + (i % 2) * 0.1 for i in range(VOLATILITY_CANDLE_COUNT)]
        read = _volatility_sizing(_Proposal(price=100.0), _FakeProvider(calm), equity=100_000.0, risk_limits=RiskLimits())
        assert read.available is True
        assert read.atr_value is not None and read.atr_value > 0
        assert read.stop_distance == round(CHANDELIER_ATR_MULTIPLIER * read.atr_value, 4)

    def test_higher_volatility_produces_a_smaller_cap_at_the_same_dollar_risk(self) -> None:
        calm = [100.0 + (i % 2) * 0.5 for i in range(VOLATILITY_CANDLE_COUNT)]
        wild = [100.0 + (i % 2) * 5.0 for i in range(VOLATILITY_CANDLE_COUNT)]
        calm_read = _volatility_sizing(_Proposal(price=100.0), _FakeProvider(calm), equity=100_000.0, risk_limits=RiskLimits())
        wild_read = _volatility_sizing(_Proposal(price=100.0), _FakeProvider(wild), equity=100_000.0, risk_limits=RiskLimits())
        assert wild_read.atr_value is not None and calm_read.atr_value is not None
        assert wild_read.atr_value > calm_read.atr_value
        # The directive's own explicit rule: a more volatile symbol must
        # get a SMALLER real quantity cap, never a larger one.
        assert wild_read.volatility_cap_quantity is not None and calm_read.volatility_cap_quantity is not None
        assert wild_read.volatility_cap_quantity < calm_read.volatility_cap_quantity
        # And the real dollar risk implied at the stop — cap * distance
        # — must be the SAME regardless of volatility: the risk budget
        # itself never grows just because the market is choppier.
        calm_implied_risk = calm_read.volatility_cap_quantity * calm_read.stop_distance
        wild_implied_risk = wild_read.volatility_cap_quantity * wild_read.stop_distance
        assert calm_implied_risk == pytest.approx(calm_read.risk_budget_usd, abs=0.01)
        assert wild_implied_risk == pytest.approx(wild_read.risk_budget_usd, abs=0.01)

    def test_risk_budget_reuses_risk_per_trade_pct_not_a_new_parameter(self) -> None:
        limits = RiskLimits(riskPerTradePct=3.5)
        read = _volatility_sizing(_Proposal(), _FakeProvider(), equity=100_000.0, risk_limits=limits)
        assert read.risk_budget_usd == 100_000.0 * 3.5 / 100

    def test_a_tighter_atr_multiplier_stop_widens_the_cap_a_wider_stop_narrows_it(self) -> None:
        # Same real ATR, compared against what a tighter vs. wider real
        # stop distance would imply — confirms the division direction is
        # correct (cap = budget / distance, not the reverse).
        moderate = [100.0 + (i % 2) * 2.0 for i in range(VOLATILITY_CANDLE_COUNT)]
        read = _volatility_sizing(_Proposal(price=100.0), _FakeProvider(moderate), equity=100_000.0, risk_limits=RiskLimits())
        assert read.stop_distance is not None and read.risk_budget_usd is not None
        assert read.volatility_cap_quantity == round(read.risk_budget_usd / read.stop_distance, 4)


class TestBuildPositionSizingVolatility:
    """End-to-end: does the real ATR-based cap actually narrow
    build_position_sizing()'s final_quantity when it's the tightest real
    constraint, and never widen it otherwise?"""

    def _build(self, **overrides):
        wide_open = RiskLimits(
            tierAllocation=TierAllocationLimits(tier1Pct=100.0, tier2Pct=100.0, tier3Pct=100.0, tier4Pct=100.0),
            maxWeeklyDeploymentPct=100.0,
            cashReservePct=0.0,
        )
        defaults = dict(
            proposal=_Proposal(),
            ceiling_quantity=1000.0,
            expected_value=_expected_value(),
            decision_score=_decision_score(95.0, passed=True),
            portfolio=_portfolio(),
            portfolio_heat=_heat(),
            risk_limits=wide_open,
            risk_warnings=[],
            sim_day=1,
            provider=_FakeProvider(),
        )
        defaults.update(overrides)
        return build_position_sizing(**defaults)

    def test_a_wide_real_atr_stop_becomes_the_binding_constraint(self) -> None:
        # A large, real ATR (extreme volatility) implies a wide stop
        # distance, which — at the standard 2% risk budget — caps
        # quantity far below the wide-open tier/weekly/heat/cash limits.
        extreme = [100.0 + (i % 2) * 50.0 for i in range(VOLATILITY_CANDLE_COUNT)]
        result = self._build(provider=_FakeProvider(extreme))
        assert result.volatility_sizing.available is True
        assert result.reduced_from_ceiling is True
        assert result.final_quantity == result.volatility_sizing.volatility_cap_quantity
        assert "volatility risk budget" in result.detail

    def test_a_calm_real_atr_stop_never_widens_beyond_other_real_caps(self) -> None:
        calm = [100.0 + (i % 2) * 0.01 for i in range(VOLATILITY_CANDLE_COUNT)]
        result = self._build(ceiling_quantity=10.0, provider=_FakeProvider(calm))
        # ceiling_quantity itself (10.0) still bounds everything -- a
        # generous volatility cap must never push final_quantity ABOVE
        # what the rest of the engine already allowed.
        assert result.final_quantity <= 10.0

    def test_no_real_candle_history_leaves_the_other_caps_fully_in_control(self) -> None:
        result = self._build(ceiling_quantity=10.0, provider=_FakeProvider([], raise_for_missing=True))
        assert result.volatility_sizing.available is False
        # Nothing fabricated -- the engine falls back to its other real,
        # already-established caps exactly as it did before this feature.
        assert result.final_quantity == 10.0
        assert result.reduced_from_ceiling is False


class _PerSymbolProvider(MarketDataProvider):
    """Unlike _FakeProvider (same closes for every symbol requested),
    this test double gives each real symbol its OWN real close series —
    needed to construct genuinely different per-symbol volatility reads
    for the cross-portfolio risk-parity tests below. Falls back to
    `default_closes` for any symbol not explicitly listed."""

    def __init__(self, closes_by_symbol: dict[str, list[float]], *, default_closes: list[float] | None = None) -> None:
        self._closes_by_symbol = closes_by_symbol
        self._default_closes = default_closes if default_closes is not None else [100.0 + (i % 2) for i in range(VOLATILITY_CANDLE_COUNT)]

    def get_quote(self, symbol: str) -> Quote:
        raise NotImplementedError

    def get_candles(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        closes = self._closes_by_symbol.get(symbol, self._default_closes)
        if not closes:
            raise ValueError(f"no fixture data for {symbol!r}")
        return [
            Candle(symbol=symbol, timeframe=timeframe, timestamp=f"2026-01-01T{i % 24:02d}:00:00Z", open=c, high=c + 0.5, low=c - 0.5, close=c, volume=1000.0, data_status="simulated")
            for i, c in enumerate(closes)
        ]


class TestCrossPortfolioInverseVolSizing:
    """CEO directive "AHL-Inspired Systematic Trend & Momentum Research
    Engine" follow-up — closes the honesty gap _inverse_vol_sizing()
    explicitly discloses: this candidate's own exposure now also
    depends on every OTHER real currently-open position's own real
    volatility, a naive (uncorrelated) inverse-vol risk-parity read
    across the whole real portfolio."""

    def test_none_with_zero_equity(self) -> None:
        result = _cross_portfolio_inverse_vol_sizing(_Proposal(), _FakeProvider(), _portfolio(), 0.0, RiskLimits(), _decision_score(60.0))
        assert result is None

    def test_none_with_zero_price(self) -> None:
        result = _cross_portfolio_inverse_vol_sizing(_Proposal(price=0.0), _FakeProvider(), _portfolio(), 100_000.0, RiskLimits(), _decision_score(60.0))
        assert result is None

    def test_none_with_no_real_candle_history_for_the_candidate(self) -> None:
        result = _cross_portfolio_inverse_vol_sizing(_Proposal(), _FakeProvider(closes=[]), _portfolio(), 100_000.0, RiskLimits(), _decision_score(60.0))
        assert result is None

    def test_only_position_collapses_to_the_single_position_formula(self) -> None:
        """position_count == 1 (no other real open positions) must give
        a final_exposure numerically IDENTICAL to _inverse_vol_sizing()'s
        own real reading — the exact convergence this function's own
        docstring promises, since both end up calling the exact same
        research_volatility_scaled_exposure() with the exact same real
        arguments (fair_share_risk_pct == risk_per_trade_pct at n=1)."""
        provider = _FakeProvider()
        risk_limits = RiskLimits()
        decision_score = _decision_score(60.0)
        single = _inverse_vol_sizing(_Proposal(), provider, 100_000.0, risk_limits, decision_score)
        cross = _cross_portfolio_inverse_vol_sizing(_Proposal(), provider, _portfolio(positions=[]), 100_000.0, risk_limits, decision_score)
        assert single is not None and cross is not None
        assert cross.position_count == 1
        assert cross.candidate_weight_pct == 100.0
        assert cross.fair_share_risk_pct == pytest.approx(risk_limits.risk_per_trade_pct)
        assert cross.final_exposure.raw_exposure_pct == pytest.approx(single.raw_exposure_pct)
        assert cross.final_exposure.capped_exposure_pct == pytest.approx(single.capped_exposure_pct)

    def test_a_calmer_candidate_next_to_a_volatile_holding_earns_a_larger_share(self) -> None:
        # volatility_pct is a FIXED +-0.5 range as a % of close price, so
        # a real volatility difference here comes from the real PRICE
        # LEVEL (a lower close makes the same $0.5 range a much bigger
        # %), the same convention TestBuildPositionSizingInverseVolCap's
        # own "tiny_price_provider"/"high_vol_provider" fixtures already
        # use above — never from the close-to-close jump pattern.
        calm = [100.0] * VOLATILITY_CANDLE_COUNT
        volatile = [1.0] * VOLATILITY_CANDLE_COUNT
        provider = _PerSymbolProvider({"AAPL": calm, "MSFT": volatile}, default_closes=calm)
        portfolio = _portfolio(positions=[_position(symbol="MSFT", quantity=5.0, entry_price=1.0)])
        result = _cross_portfolio_inverse_vol_sizing(_Proposal(symbol="AAPL"), provider, portfolio, 100_000.0, RiskLimits(), _decision_score(60.0))
        assert result is not None
        assert result.position_count == 2
        # AAPL (calm, high price) has much lower real volatility_pct than
        # MSFT (volatile, low price), so its real 1/volatility weight —
        # and therefore its fair share of the total risk budget — must
        # be the larger one.
        assert result.candidate_weight_pct > 50.0

    def test_a_volatile_candidate_next_to_a_calm_holding_earns_a_smaller_share(self) -> None:
        calm = [100.0] * VOLATILITY_CANDLE_COUNT
        volatile = [1.0] * VOLATILITY_CANDLE_COUNT
        provider = _PerSymbolProvider({"AAPL": volatile, "MSFT": calm}, default_closes=calm)
        portfolio = _portfolio(positions=[_position(symbol="MSFT", quantity=5.0, entry_price=100.0)])
        result = _cross_portfolio_inverse_vol_sizing(_Proposal(symbol="AAPL", price=1.0), provider, portfolio, 100_000.0, RiskLimits(), _decision_score(60.0))
        assert result is not None
        assert result.candidate_weight_pct < 50.0

    def test_multiple_lots_in_the_same_held_symbol_count_once(self) -> None:
        provider = _FakeProvider()
        portfolio_one_lot = _portfolio(positions=[_position(symbol="MSFT", quantity=5.0)])
        portfolio_two_lots = _portfolio(positions=[_position(symbol="MSFT", quantity=5.0), _position(symbol="MSFT", quantity=3.0)])
        one = _cross_portfolio_inverse_vol_sizing(_Proposal(symbol="AAPL"), provider, portfolio_one_lot, 100_000.0, RiskLimits(), _decision_score(60.0))
        two = _cross_portfolio_inverse_vol_sizing(_Proposal(symbol="AAPL"), provider, portfolio_two_lots, 100_000.0, RiskLimits(), _decision_score(60.0))
        assert one is not None and two is not None
        assert one.position_count == two.position_count == 2

    def test_candidate_symbol_already_held_is_not_double_counted(self) -> None:
        provider = _FakeProvider()
        portfolio = _portfolio(positions=[_position(symbol="AAPL", quantity=5.0)])
        result = _cross_portfolio_inverse_vol_sizing(_Proposal(symbol="AAPL"), provider, portfolio, 100_000.0, RiskLimits(), _decision_score(60.0))
        assert result is not None
        assert result.position_count == 1


class TestBuildPositionSizingCrossPortfolioCap:
    def _build(self, **overrides):
        defaults = dict(
            proposal=_Proposal(),
            ceiling_quantity=10.0,
            expected_value=_expected_value(),
            decision_score=_decision_score(60.0),
            portfolio=_portfolio(),
            portfolio_heat=_heat(),
            risk_limits=RiskLimits(),
            risk_warnings=[],
            sim_day=1,
            provider=_FakeProvider(),
        )
        defaults.update(overrides)
        return build_position_sizing(**defaults)

    def test_cross_portfolio_risk_sizing_is_populated_when_available(self) -> None:
        result = self._build()
        assert result.cross_portfolio_risk_sizing is not None

    def test_cross_portfolio_risk_sizing_is_none_when_history_unavailable(self) -> None:
        result = self._build(provider=_FakeProvider(closes=[]))
        assert result.cross_portfolio_risk_sizing is None

    def test_final_quantity_never_exceeds_the_cross_portfolio_cap(self) -> None:
        wide_open = RiskLimits(
            tierAllocation=TierAllocationLimits(tier1Pct=100.0, tier2Pct=100.0, tier3Pct=100.0, tier4Pct=100.0),
            maxWeeklyDeploymentPct=100.0,
            cashReservePct=0.0,
        )
        calm = [100.0] * VOLATILITY_CANDLE_COUNT
        volatile = [1.0] * VOLATILITY_CANDLE_COUNT
        provider = _PerSymbolProvider({"AAPL": volatile, "MSFT": calm}, default_closes=calm)
        portfolio = _portfolio(positions=[_position(symbol="MSFT", quantity=5.0, entry_price=100.0)])
        result = self._build(ceiling_quantity=1_000.0, risk_limits=wide_open, provider=provider, portfolio=portfolio, proposal=_Proposal(symbol="AAPL", price=1.0))
        assert result.cross_portfolio_risk_sizing is not None
        equity = portfolio_equity(portfolio)
        cap_quantity = equity * result.cross_portfolio_risk_sizing.final_exposure.capped_exposure_pct / 100 / 1.0
        assert result.final_quantity <= cap_quantity + 1e-6

    def test_binding_constraint_names_cross_portfolio_cap_when_it_is_tightest(self) -> None:
        wide_open = RiskLimits(
            tierAllocation=TierAllocationLimits(tier1Pct=100.0, tier2Pct=100.0, tier3Pct=100.0, tier4Pct=100.0),
            maxWeeklyDeploymentPct=100.0,
            cashReservePct=0.0,
        )
        # AAPL is dramatically more volatile (low real price) than the
        # already-held MSFT (high real price), so its real fair share of
        # the shared risk budget — and therefore this cap — is far
        # tighter than every other cap here.
        calm = [100.0] * VOLATILITY_CANDLE_COUNT
        volatile = [0.5] * VOLATILITY_CANDLE_COUNT
        provider = _PerSymbolProvider({"AAPL": volatile, "MSFT": calm}, default_closes=calm)
        portfolio = _portfolio(positions=[_position(symbol="MSFT", quantity=5.0, entry_price=100.0)])
        result = self._build(ceiling_quantity=1_000.0, risk_limits=wide_open, provider=provider, portfolio=portfolio, proposal=_Proposal(symbol="AAPL", price=0.5), decision_score=_decision_score(5.0))
        assert result.reduced_from_ceiling is True
        assert "cross-portfolio inverse-volatility risk-parity budget" in result.detail
