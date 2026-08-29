"""Covers app/position_sizing.py — v0.7 Chapter 57, the Institutional
Position Sizing & Capital Deployment Engine. Every case here checks the
one real guarantee the chapter makes: the engine only ever NARROWS the
caller-supplied `ceiling_quantity` (app/risk_engine.py's
recommended_quantity()), never widens it, and every narrowing traces
back to a real, named constraint — never a silent or fabricated cut.
"""
from __future__ import annotations

import math
from datetime import datetime, timedelta

import pytest

from app.ema_pullback_research import CHANDELIER_ATR_MULTIPLIER, CHANDELIER_ATR_PERIOD
from app.market_data import Candle, MarketDataProvider, Quote
from app.position_sizing import (
    REGIME_SUITABILITY_CANDLE_COUNT,
    TIER_FRACTION,
    VOLATILITY_CANDLE_COUNT,
    WEEKLY_DEPLOYMENT_WINDOW_DAYS,
    _capital_deployed_pct_in_window,
    _cross_portfolio_inverse_vol_sizing,
    _inverse_vol_sizing,
    _regime_suitability_sizing,
    _session_suitability_sizing,
    _tier_for_sizing_score,
    compute_volatility_sizing,
    build_position_sizing,
)
from app.risk_engine import SIM_MINUTES_PER_DAY, portfolio_equity
from app.session_evidence import MIN_SESSION_REGIME_SAMPLE
from app.schemas import (
    DecisionScoreBreakdown,
    DecisionVaultEntry,
    ExpectedValueAnalysis,
    LiquidityRead,
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

    def test_position_sizing_result_validates_with_nocompute_volatility_sizing_key_at_all(self) -> None:
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
            session="closed",
            regime="transitional",
            decision_vault=[],
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
            session="closed",
            regime="transitional",
            decision_vault=[],
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
    TO STOP. Tests compute_volatility_sizing() directly against the directive's
    own explicit scenario list (low/high volatility, insufficient
    history) before testing the end-to-end narrowing effect below."""

    def test_insufficient_candle_history_reports_unavailable_not_fabricated(self) -> None:
        read = compute_volatility_sizing(_Proposal(), _FakeProvider([], raise_for_missing=True), equity=100_000.0, risk_limits=RiskLimits())
        assert read.available is False
        assert read.stop_distance is None
        assert read.volatility_cap_quantity is None
        assert "no real candle history" in read.detail.lower()

    def test_a_short_candle_history_below_the_atr_period_reports_unavailable(self) -> None:
        # Real candles exist, but too few for a real CHANDELIER_ATR_PERIOD-bar ATR window.
        short_history = [100.0 + (i % 2) for i in range(CHANDELIER_ATR_PERIOD - 1)]
        read = compute_volatility_sizing(_Proposal(), _FakeProvider(short_history), equity=100_000.0, risk_limits=RiskLimits())
        assert read.available is False
        assert read.volatility_cap_quantity is None

    def test_low_volatility_symbol_gets_a_real_available_read(self) -> None:
        calm = [100.0 + (i % 2) * 0.1 for i in range(VOLATILITY_CANDLE_COUNT)]
        read = compute_volatility_sizing(_Proposal(price=100.0), _FakeProvider(calm), equity=100_000.0, risk_limits=RiskLimits())
        assert read.available is True
        assert read.atr_value is not None and read.atr_value > 0
        assert read.stop_distance == round(CHANDELIER_ATR_MULTIPLIER * read.atr_value, 4)

    def test_higher_volatility_produces_a_smaller_cap_at_the_same_dollar_risk(self) -> None:
        calm = [100.0 + (i % 2) * 0.5 for i in range(VOLATILITY_CANDLE_COUNT)]
        wild = [100.0 + (i % 2) * 5.0 for i in range(VOLATILITY_CANDLE_COUNT)]
        calm_read = compute_volatility_sizing(_Proposal(price=100.0), _FakeProvider(calm), equity=100_000.0, risk_limits=RiskLimits())
        wild_read = compute_volatility_sizing(_Proposal(price=100.0), _FakeProvider(wild), equity=100_000.0, risk_limits=RiskLimits())
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
        read = compute_volatility_sizing(_Proposal(), _FakeProvider(), equity=100_000.0, risk_limits=limits)
        assert read.risk_budget_usd == 100_000.0 * 3.5 / 100

    def test_a_tighter_atr_multiplier_stop_widens_the_cap_a_wider_stop_narrows_it(self) -> None:
        # Same real ATR, compared against what a tighter vs. wider real
        # stop distance would imply — confirms the division direction is
        # correct (cap = budget / distance, not the reverse).
        moderate = [100.0 + (i % 2) * 2.0 for i in range(VOLATILITY_CANDLE_COUNT)]
        read = compute_volatility_sizing(_Proposal(price=100.0), _FakeProvider(moderate), equity=100_000.0, risk_limits=RiskLimits())
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
            session="closed",
            regime="transitional",
            decision_vault=[],
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


class _FixedCandlesProvider(MarketDataProvider):
    """Returns one pre-built, real candle series verbatim for every
    symbol requested — used only by the regime-suitability tests below,
    which (unlike every other cap in this module) actually run their
    real candle sample through app/trend_engine.py's own
    compute_trend_regime_breakdown(), and that function's own real data-
    quality gate (_candle_data_invalid_reason) rejects non-increasing
    real timestamps. _FakeProvider/_PerSymbolProvider above both stamp
    an `i % 24` hour-of-day that WRAPS (and so goes backwards) past 24
    candles — harmless for every OTHER cap in this module (none of them
    read a candle's own timestamp), but it would make every regime-
    breakdown read here silently invalid. This provider's own candles
    already carry real, strictly increasing multi-day timestamps."""

    def __init__(self, candles: list[Candle]) -> None:
        self._candles = candles

    def get_quote(self, symbol: str) -> Quote:
        raise NotImplementedError

    def get_candles(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        return self._candles


def _trend_candles(n: int, *, start: float = 100.0, step_pct: float = 0.6) -> list[Candle]:
    """A real, smooth, monotonic trend — real strictly increasing
    hourly timestamps starting 2026-01-01T00:00:00Z."""
    closes = [start]
    for _ in range(n - 1):
        closes.append(closes[-1] * (1 + step_pct / 100))
    return _timestamped_candles(closes)


def _whipsaw_candles(n: int, *, start: float = 100.0, amplitude: float = 6.0, period_bars: int = 24) -> list[Candle]:
    """A real oscillating series whose period is deliberately close to
    compute_trend_regime_breakdown()'s own default 10-bar forward_bars
    window — a real, disclosed adversarial case for trend-following
    signals (a "strong" directional read at any given bar is frequently
    on the wrong side by the time the forward window resolves), used to
    exercise a real, deterministic low-hit-rate regime bucket rather
    than fabricating one."""
    omega = 2 * math.pi / period_bars
    closes = [start + amplitude * math.sin(omega * i) for i in range(n)]
    return _timestamped_candles(closes)


def _timestamped_candles(closes: list[float]) -> list[Candle]:
    start = datetime(2026, 1, 1)
    return [
        Candle(
            symbol="TEST",
            timeframe="1h",
            timestamp=(start + timedelta(hours=i)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            open=c,
            high=c + 0.3,
            low=c - 0.3,
            close=c,
            volume=1000.0,
            data_status="simulated",
        )
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
            session="closed",
            regime="transitional",
            decision_vault=[],
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


class TestBuildPositionSizingMarginalRiskCap:
    """CEO directive "Portfolio Risk Engine, 11/10 Professional Quant-
    Firm Implementation" — the real correlation/concentration-cluster
    reduction from app/portfolio_risk.py::evaluate_marginal_portfolio_
    risk() wired in as a real, narrowing-only cap. Deliberately scoped
    to correlation/concentration ONLY (via compute_correlation_
    concentration_cap()) — never inherits Sentinel's own critical hard
    gates, which remain exclusively app/gatekeeper.py's job (see
    TestNeverInheritsSentinelVeto below for the regression this class
    exists to prevent)."""

    def _build(self, **overrides):
        # Same wide_open + maxed decision_score convention
        # TestBuildPositionSizingVolatility's own _build already
        # establishes — every OTHER cap becomes a real no-op by
        # construction, so a test can isolate this cap's own real
        # effect (or lack of one) without a second, unrelated cap
        # muddying the assertion.
        wide_open = RiskLimits(
            tierAllocation=TierAllocationLimits(tier1Pct=100.0, tier2Pct=100.0, tier3Pct=100.0, tier4Pct=100.0),
            maxWeeklyDeploymentPct=100.0,
            cashReservePct=0.0,
            maxPositionPct=100.0,
            maxSectorConcentrationPct=100.0,
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
            session="closed",
            regime="transitional",
            decision_vault=[],
        )
        defaults.update(overrides)
        return build_position_sizing(**defaults)

    def test_marginal_risk_decision_is_populated(self) -> None:
        result = self._build()
        assert result.marginal_risk_decision is not None

    def test_marginal_risk_decision_is_none_when_ceiling_is_zero(self) -> None:
        result = self._build(ceiling_quantity=0.0)
        assert result.marginal_risk_decision is None

    def test_joining_an_already_correlated_cluster_narrows_final_quantity(self) -> None:
        wide_open = RiskLimits(
            tierAllocation=TierAllocationLimits(tier1Pct=100.0, tier2Pct=100.0, tier3Pct=100.0, tier4Pct=100.0),
            maxWeeklyDeploymentPct=100.0,
            cashReservePct=0.0,
            maxPositionPct=100.0,
            maxSectorConcentrationPct=100.0,
        )
        # MSFT already at 25% of equity alone (not yet a "cluster" —
        # a lone symbol never is); NVDA is a perfectly-correlated
        # candidate (real Pearson correlation of 1.0 via proportional
        # closes) requesting far more than the 40% real restricted-
        # cluster threshold would allow once the two are considered
        # together.
        closes = [100.0 + i for i in range(VOLATILITY_CANDLE_COUNT)]
        provider = _PerSymbolProvider({"MSFT": closes, "NVDA": [c * 2 for c in closes]}, default_closes=closes)
        portfolio = _portfolio(cash_balance=75_000.0, positions=[_position(symbol="MSFT", quantity=125.0, entry_price=200.0)])
        result = self._build(
            ceiling_quantity=1_000.0,
            risk_limits=wide_open,
            provider=provider,
            portfolio=portfolio,
            proposal=_Proposal(symbol="NVDA", price=200.0),
            decision_score=_decision_score(95.0),
        )
        assert result.marginal_risk_decision is not None
        assert result.marginal_risk_decision.decision in ("approved_reduced", "vetoed")
        assert result.reduced_from_ceiling is True
        # Rounded to 4 decimal places on quantity before being reported
        # (see build_position_sizing()'s own `round(final_quantity, 4)`)
        # — a small, real rounding tolerance at $200/share, not a loose
        # assertion.
        assert result.final_quantity * 200.0 <= max(result.marginal_risk_decision.allowed_value, 0.0) + 0.05

    def test_binding_constraint_names_the_marginal_risk_test_when_it_is_tightest(self) -> None:
        wide_open = RiskLimits(
            tierAllocation=TierAllocationLimits(tier1Pct=100.0, tier2Pct=100.0, tier3Pct=100.0, tier4Pct=100.0),
            maxWeeklyDeploymentPct=100.0,
            cashReservePct=0.0,
            maxPositionPct=100.0,
            maxSectorConcentrationPct=100.0,
        )
        closes = [100.0 + i for i in range(VOLATILITY_CANDLE_COUNT)]
        provider = _PerSymbolProvider({"MSFT": closes, "NVDA": [c * 2 for c in closes]}, default_closes=closes)
        portfolio = _portfolio(cash_balance=75_000.0, positions=[_position(symbol="MSFT", quantity=125.0, entry_price=200.0)])
        result = self._build(
            ceiling_quantity=1_000.0,
            risk_limits=wide_open,
            provider=provider,
            portfolio=portfolio,
            proposal=_Proposal(symbol="NVDA", price=200.0),
            decision_score=_decision_score(95.0),
        )
        assert result.reduced_from_ceiling is True
        assert "Marginal Risk Test" in result.detail or "correlated cluster" in result.detail

    def test_no_real_candle_history_is_honestly_data_blocked_and_never_narrows_further(self) -> None:
        result = self._build(ceiling_quantity=10.0, provider=_FakeProvider(closes=[], raise_for_missing=True))
        assert result.marginal_risk_decision is not None
        assert result.marginal_risk_decision.decision == "data_blocked"
        # Nothing fabricated — with every other cap a real no-op by this
        # class's own wide-open _build() convention, and no real candle
        # history for either the volatility or the marginal-risk cap,
        # final_quantity falls all the way back to the real ceiling.
        assert result.final_quantity == 10.0


class TestMarginalRiskCapNeverInheritsSentinelVeto:
    """The regression this class exists to prevent: composing app/
    portfolio_risk.py::evaluate_marginal_portfolio_risk()'s FULL veto
    (which includes Sentinel's own critical hard gates — drawdown,
    daily loss, position size) directly into position_sizing.py's cap
    chain would make this module start rejecting candidates on grounds
    that remain exclusively app/gatekeeper.py's real job downstream —
    exactly the "how much, never whether" boundary this module's own
    docstring draws. compute_correlation_concentration_cap() must never
    let an unrelated critical Sentinel violation zero out the real
    weekly/heat/cash caps' own, differently-reasoned narrowing."""

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
            session="closed",
            regime="transitional",
            decision_vault=[],
        )
        defaults.update(overrides)
        return build_position_sizing(**defaults)

    def test_a_candidate_that_would_breach_max_position_pct_is_still_capped_by_the_real_weekly_budget_not_vetoed_to_zero(self) -> None:
        # A candidate requesting 100% of equity trips Sentinel's own
        # critical max_position_pct check inside evaluate_pretrade_risk_
        # decision() — if that composed into this module's own cap
        # chain, final_quantity would incorrectly zero out here instead
        # of being narrowed by the real weekly deployment budget this
        # test is actually isolating.
        portfolio = _portfolio(trade_history=[_trade(quantity=140.0, entry_price=100.0, opened_sim_minutes=0)])
        result = self._build(
            decision_score=_decision_score(95.0, passed=True),
            ceiling_quantity=1_000.0,
            portfolio=portfolio,
            risk_limits=RiskLimits(tierAllocation=TierAllocationLimits(tier1Pct=100.0, tier2Pct=100.0, tier3Pct=100.0, tier4Pct=100.0), maxWeeklyDeploymentPct=15.0),
            sim_day=1,
        )
        assert result.final_quantity > 0.0
        assert "weekly capital deployment budget" in result.detail
        assert result.marginal_risk_decision is not None


class TestRegimeSuitabilitySizing:
    """CEO directive "Portfolio Risk Engine, 11/10 Professional Quant-
    Firm Implementation," Phase 2 — promotes app/trend_engine.py's own
    real, previously-unconsumed regime-conditional hit-rate evidence
    (compute_trend_regime_breakdown()) into a real, narrowing-only cap.
    See _regime_suitability_sizing()'s own docstring."""

    def test_none_with_too_little_real_candle_history(self) -> None:
        provider = _FixedCandlesProvider(_trend_candles(50))
        assert _regime_suitability_sizing(_Proposal(), provider, 10.0) is None

    def test_none_when_no_real_candle_history_exists(self) -> None:
        provider = _FixedCandlesProvider([])
        assert _regime_suitability_sizing(_Proposal(), provider, 10.0) is None

    def test_insufficient_evidence_is_reported_honestly_not_fabricated(self) -> None:
        # Just above the real minimum window (70 bars) but nowhere near
        # enough real strong-signal history to fill any regime bucket to
        # the _MIN_BARS_FOR_REGIME_EVIDENCE floor.
        provider = _FixedCandlesProvider(_trend_candles(75))
        read = _regime_suitability_sizing(_Proposal(), provider, 10.0)
        assert read is not None
        assert read.available is False
        assert read.regime_cap_quantity is None
        assert "Insufficient" in read.detail

    def test_strong_favorable_regime_evidence_does_not_reduce_below_the_ceiling(self) -> None:
        # A real, smooth, sustained uptrend: every real strong-signal bar
        # in the 'trending_up' regime is followed by a real continued
        # real forward gain — a real 100% historical hit rate in the
        # CURRENT regime specifically, at or above the 50% real floor.
        provider = _FixedCandlesProvider(_trend_candles(REGIME_SUITABILITY_CANDLE_COUNT + 20))
        read = _regime_suitability_sizing(_Proposal(), provider, 10.0)
        assert read is not None
        assert read.available is True
        assert read.current_regime == "trending_up"
        assert read.bars_observed >= 5
        assert read.hit_rate_pct == 100.0
        assert read.suitability_scale == 1.0
        assert read.regime_cap_quantity == 10.0

    def test_weak_historical_regime_evidence_reduces_the_cap(self) -> None:
        # A real oscillating (whipsaw) series whose period is close to
        # the regime breakdown's own forward-return window — a real,
        # deterministic case where the CURRENT regime's own historical
        # strong-signal bars were frequently on the wrong side of the
        # real forward return, well under the 50% real floor.
        provider = _FixedCandlesProvider(_whipsaw_candles(REGIME_SUITABILITY_CANDLE_COUNT + 20, period_bars=24))
        read = _regime_suitability_sizing(_Proposal(), provider, 10.0)
        assert read is not None
        assert read.available is True
        assert read.current_regime == "trending_down"
        assert read.bars_observed >= 5
        assert read.hit_rate_pct < 50.0
        assert 0.0 < read.suitability_scale < 1.0
        assert read.regime_cap_quantity is not None
        assert read.regime_cap_quantity < 10.0
        # scale = hit_rate / 50.0, cap = candidate_quantity * scale — the
        # one real, disclosed formula, checked exactly (not just its
        # direction), rounded exactly as the function itself rounds.
        assert read.regime_cap_quantity == round(10.0 * read.suitability_scale, 6)


class TestBuildPositionSizingRegimeSuitabilityCap:
    """CEO directive "Portfolio Risk Engine, 11/10 Professional Quant-
    Firm Implementation," Phase 2 — the regime-suitability cap wired
    into build_position_sizing()'s own real min(...) cap chain, isolated
    with this module's own established wide_open + maxed decision_score
    convention (see TestBuildPositionSizingVolatility's own _build)."""

    def _build(self, **overrides):
        wide_open = RiskLimits(
            tierAllocation=TierAllocationLimits(tier1Pct=100.0, tier2Pct=100.0, tier3Pct=100.0, tier4Pct=100.0),
            maxWeeklyDeploymentPct=100.0,
            cashReservePct=0.0,
            maxPositionPct=100.0,
            maxSectorConcentrationPct=100.0,
        )
        defaults = dict(
            proposal=_Proposal(),
            ceiling_quantity=10.0,
            expected_value=_expected_value(),
            decision_score=_decision_score(95.0, passed=True),
            portfolio=_portfolio(),
            portfolio_heat=_heat(),
            risk_limits=wide_open,
            risk_warnings=[],
            sim_day=1,
            provider=_FakeProvider(),
            session="closed",
            regime="transitional",
            decision_vault=[],
        )
        defaults.update(overrides)
        return build_position_sizing(**defaults)

    def test_default_fake_provider_has_too_little_history_and_never_narrows(self) -> None:
        # This module's own default _FakeProvider (used pervasively
        # across every OTHER test in this file) supplies well under the
        # real 70-bar regime-evidence minimum — the regime-suitability
        # cap must stay a real, honest no-op here, exactly like every
        # pre-existing test in this file that never set it up.
        result = self._build()
        assert result.regime_suitability_sizing.available is False
        assert result.final_quantity == 10.0

    def test_weak_regime_evidence_narrows_final_quantity(self) -> None:
        provider = _FixedCandlesProvider(_whipsaw_candles(REGIME_SUITABILITY_CANDLE_COUNT + 20, period_bars=24))
        result = self._build(ceiling_quantity=10.0, provider=provider)
        assert result.regime_suitability_sizing.available is True
        assert result.regime_suitability_sizing.suitability_scale < 1.0
        assert result.reduced_from_ceiling is True
        assert result.final_quantity < 10.0
        assert result.final_quantity == round(10.0 * result.regime_suitability_sizing.suitability_scale, 4)

    def test_binding_constraint_names_the_regime_cap_when_it_is_tightest(self) -> None:
        provider = _FixedCandlesProvider(_whipsaw_candles(REGIME_SUITABILITY_CANDLE_COUNT + 20, period_bars=24))
        result = self._build(ceiling_quantity=10.0, provider=provider)
        assert result.reduced_from_ceiling is True
        assert "regime" in result.detail.lower()
        assert result.marginal_risk_decision.decision != "vetoed"


def _vault_entry(*, entry_id: str, session: str = "new_york", market_regime: str = "sideways_range", pnl_pct: float = 1.0) -> DecisionVaultEntry:
    """Minimal real DecisionVaultEntry fixture — mirrors
    tests/test_session_evidence.py's own `_vault_entry()` builder (same
    required fields, same honest test-double conventions), duplicated
    here rather than imported since it's a private test helper local to
    that file."""
    return DecisionVaultEntry(
        id=entry_id,
        tradeId=f"trade-{entry_id}",
        decisionId=f"decision-{entry_id}",
        symbol="NEXA",
        simDay=1,
        session=session,  # type: ignore[arg-type]
        strategyId=None,
        marketRegime=market_regime,  # type: ignore[arg-type]
        marketRegimeLabel="test regime",
        liquidityContext=LiquidityRead(symbol="NEXA", zones=[], sweepDetected=False, sweepDirection="none", liquidityScore=50.0, detail="test"),
        evidenceScore=70.0,
        confidenceScore=70.0,
        confidenceTier="strong",  # type: ignore[arg-type]
        capitalAllocationGrade="B",  # type: ignore[arg-type]
        decisionGrade="B",  # type: ignore[arg-type]
        decisionGradeScore=80.0,
        disciplineTier="sound",  # type: ignore[arg-type]
        disciplineScore=75.0,
        patienceGrade="B",  # type: ignore[arg-type]
        positionSize=10.0,
        entryPrice=100.0,
        exitPrice=100.0 + pnl_pct,
        pnl=pnl_pct * 10.0,
        pnlPct=pnl_pct,
        holdDurationMinutes=60,
        rMultiple=None,
        caseStudyId=None,
        caseStudyCategory=None,
        executiveNotes=None,
        lessonsLearned="test lesson",
        companyDnaChange=None,
        ceoOverride=False,
        createdAt="2026-01-01T00:00:00+00:00",
    )


class TestSessionSuitabilitySizing:
    """CEO directive "You are now entering the NEXT major TradeTown
    build phase," Phase 10 — promotes app/session_evidence.py's own
    real, previously read-only SESSION x REGIME win-rate evidence into a
    real, narrowing-only cap. See _session_suitability_sizing()'s own
    docstring."""

    def test_unavailable_with_empty_decision_vault(self) -> None:
        read = _session_suitability_sizing("london", "sideways_range", [], 10.0)
        assert read.available is False
        assert read.session_cap_quantity is None
        assert "Insufficient" in read.detail

    def test_unavailable_below_the_real_minimum_sample(self) -> None:
        entries = [_vault_entry(entry_id=f"e{i}", session="london", market_regime="sideways_range", pnl_pct=1.0) for i in range(MIN_SESSION_REGIME_SAMPLE - 1)]
        read = _session_suitability_sizing("london", "sideways_range", entries, 10.0)
        assert read.available is False
        assert read.sample_size == MIN_SESSION_REGIME_SAMPLE - 1

    def test_a_different_session_or_regime_pairing_is_not_matched(self) -> None:
        entries = [_vault_entry(entry_id=f"e{i}", session="london", market_regime="sideways_range", pnl_pct=1.0) for i in range(MIN_SESSION_REGIME_SAMPLE)]
        read = _session_suitability_sizing("asian", "sideways_range", entries, 10.0)
        assert read.available is False
        assert read.sample_size == 0

    def test_favorable_real_evidence_does_not_reduce_below_the_ceiling(self) -> None:
        # 100% real historical win rate for this exact (session, regime)
        # pairing — at or above the 50% real floor, no reduction.
        entries = [_vault_entry(entry_id=f"e{i}", session="london", market_regime="sideways_range", pnl_pct=1.0) for i in range(MIN_SESSION_REGIME_SAMPLE)]
        read = _session_suitability_sizing("london", "sideways_range", entries, 10.0)
        assert read.available is True
        assert read.win_rate_pct == 100.0
        assert read.suitability_scale == 1.0
        assert read.session_cap_quantity == 10.0

    def test_weak_real_evidence_reduces_the_cap(self) -> None:
        # 1 real win, 4 real losses — a real 20% historical win rate,
        # well under the 50% real floor.
        entries = [_vault_entry(entry_id="win", session="asian", market_regime="high_volatility", pnl_pct=1.0)] + [
            _vault_entry(entry_id=f"loss{i}", session="asian", market_regime="high_volatility", pnl_pct=-1.0) for i in range(4)
        ]
        read = _session_suitability_sizing("asian", "high_volatility", entries, 10.0)
        assert read.available is True
        assert read.win_rate_pct == 20.0
        assert read.suitability_scale == pytest.approx(0.4)
        assert read.session_cap_quantity == pytest.approx(4.0)


class TestBuildPositionSizingSessionSuitabilityCap:
    """CEO directive "You are now entering the NEXT major TradeTown
    build phase," Phase 10 — the session-suitability cap wired into
    build_position_sizing()'s own real min(...) cap chain, isolated with
    this module's own established wide_open + maxed decision_score
    convention (see TestBuildPositionSizingVolatility's own _build)."""

    def _build(self, **overrides):
        wide_open = RiskLimits(
            tierAllocation=TierAllocationLimits(tier1Pct=100.0, tier2Pct=100.0, tier3Pct=100.0, tier4Pct=100.0),
            maxWeeklyDeploymentPct=100.0,
            cashReservePct=0.0,
            maxPositionPct=100.0,
            maxSectorConcentrationPct=100.0,
        )
        defaults = dict(
            proposal=_Proposal(),
            ceiling_quantity=10.0,
            expected_value=_expected_value(),
            decision_score=_decision_score(95.0, passed=True),
            portfolio=_portfolio(),
            portfolio_heat=_heat(),
            risk_limits=wide_open,
            risk_warnings=[],
            sim_day=1,
            provider=_FakeProvider(),
            session="closed",
            regime="transitional",
            decision_vault=[],
        )
        defaults.update(overrides)
        return build_position_sizing(**defaults)

    def test_default_empty_vault_never_narrows(self) -> None:
        result = self._build()
        assert result.session_suitability_sizing.available is False
        assert result.final_quantity == 10.0

    def test_weak_session_evidence_narrows_final_quantity(self) -> None:
        entries = [_vault_entry(entry_id="win", session="asian", market_regime="high_volatility", pnl_pct=1.0)] + [
            _vault_entry(entry_id=f"loss{i}", session="asian", market_regime="high_volatility", pnl_pct=-1.0) for i in range(4)
        ]
        result = self._build(ceiling_quantity=10.0, session="asian", regime="high_volatility", decision_vault=entries)
        assert result.session_suitability_sizing.available is True
        assert result.session_suitability_sizing.suitability_scale == pytest.approx(0.4)
        assert result.reduced_from_ceiling is True
        assert result.final_quantity == round(10.0 * 0.4, 4)

    def test_binding_constraint_names_the_session_cap_when_it_is_tightest(self) -> None:
        entries = [_vault_entry(entry_id="win", session="asian", market_regime="high_volatility", pnl_pct=1.0)] + [
            _vault_entry(entry_id=f"loss{i}", session="asian", market_regime="high_volatility", pnl_pct=-1.0) for i in range(4)
        ]
        result = self._build(ceiling_quantity=10.0, session="asian", regime="high_volatility", decision_vault=entries)
        assert result.reduced_from_ceiling is True
        assert "session" in result.detail.lower()
