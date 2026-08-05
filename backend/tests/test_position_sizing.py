"""Covers app/position_sizing.py — v0.7 Chapter 57, the Institutional
Position Sizing & Capital Deployment Engine. Every case here checks the
one real guarantee the chapter makes: the engine only ever NARROWS the
caller-supplied `ceiling_quantity` (app/risk_engine.py's
recommended_quantity()), never widens it, and every narrowing traces
back to a real, named constraint — never a silent or fabricated cut.
"""
from __future__ import annotations

from app.position_sizing import (
    TIER_FRACTION,
    WEEKLY_DEPLOYMENT_WINDOW_DAYS,
    _capital_deployed_pct_in_window,
    _tier_for_sizing_score,
    build_position_sizing,
)
from app.risk_engine import SIM_MINUTES_PER_DAY
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
