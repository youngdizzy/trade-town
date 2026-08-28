"""Covers app/portfolio_risk.py — CEO directive "Portfolio Risk Engine +
Firm-Wide Risk Governance." Every value must trace back to a real
already-computed source; this file focuses on the composition logic
itself (risk-state escalation, pre-trade decision reason aggregation),
not re-testing the underlying real checks (already covered by
test_risk_engine.py / test_portfolio_intelligence.py).
"""
from __future__ import annotations

from app.portfolio_intelligence import compute_portfolio_intelligence
from app.portfolio_risk import compute_portfolio_risk_snapshot, evaluate_pretrade_risk_decision
from app.schemas import PaperPortfolio, PaperPosition, PaperTrade, RiskLimits
from tests.test_portfolio_intelligence import _FakeProvider


def _trade(*, pnl: float, opened_sim_minutes: int = 0, closed_sim_minutes: int = 30) -> PaperTrade:
    return PaperTrade(
        id=f"trade-{opened_sim_minutes}-{closed_sim_minutes}-{pnl}",
        symbol="AAPL",
        side="buy",  # type: ignore[arg-type]
        quantity=1.0,
        entryPrice=100.0,
        exitPrice=100.0 + pnl,
        pnl=pnl,
        pnlPct=pnl,
        durationMinutes=closed_sim_minutes - opened_sim_minutes,
        confidence=80.0,
        reason="test",
        marketConditions="test",
        supportingAgents=["scout"],  # type: ignore[arg-type]
        opposingAgents=[],
        openedAt="2024-01-01T00:00:00+00:00",
        closedAt="2024-01-01T00:00:00+00:00",
        openedSimMinutes=opened_sim_minutes,
        closedSimMinutes=closed_sim_minutes,
    )


def _portfolio(
    *,
    cash: float = 100_000.0,
    starting: float = 100_000.0,
    positions: list[PaperPosition] | None = None,
    trades: list[PaperTrade] | None = None,
) -> PaperPortfolio:
    return PaperPortfolio(
        cashBalance=cash,
        startingBalance=starting,
        positions=positions or [],
        orders=[],
        tradeHistory=trades or [],
        totalPnl=sum(t.pnl for t in (trades or [])),
        totalPnlPct=0.0,
        winCount=0,
        lossCount=0,
    )


class TestComputePortfolioRiskSnapshot:
    def test_normal_state_when_nothing_is_wrong(self) -> None:
        portfolio = _portfolio()
        intelligence = compute_portfolio_intelligence(portfolio, _FakeProvider({}), pending_proposal_count=0)
        snapshot = compute_portfolio_risk_snapshot(
            portfolio, RiskLimits(), intelligence, daily_circuit_breaker_tier="none", daily_pnl_pct=0.0, emergency_stop_active=False
        )
        assert snapshot.risk_state == "normal"
        assert snapshot.risk_state_reasons == []
        assert snapshot.equity == 100_000.0
        assert snapshot.leverage == 0.0

    def test_emergency_stop_forces_halted_regardless_of_everything_else(self) -> None:
        portfolio = _portfolio()
        intelligence = compute_portfolio_intelligence(portfolio, _FakeProvider({}), pending_proposal_count=0)
        snapshot = compute_portfolio_risk_snapshot(
            portfolio, RiskLimits(), intelligence, daily_circuit_breaker_tier="none", daily_pnl_pct=0.0, emergency_stop_active=True
        )
        assert snapshot.risk_state == "halted"
        assert any("emergency stop" in r.lower() for r in snapshot.risk_state_reasons)

    def test_daily_circuit_breaker_tier4_is_halted(self) -> None:
        portfolio = _portfolio()
        intelligence = compute_portfolio_intelligence(portfolio, _FakeProvider({}), pending_proposal_count=0)
        snapshot = compute_portfolio_risk_snapshot(
            portfolio, RiskLimits(), intelligence, daily_circuit_breaker_tier="tier4", daily_pnl_pct=-10.0, emergency_stop_active=False
        )
        assert snapshot.risk_state == "halted"

    def test_real_drawdown_at_limit_is_halted(self) -> None:
        limits = RiskLimits(maxDrawdownPct=20.0)
        portfolio = _portfolio(trades=[_trade(pnl=-25_000.0)], cash=75_000.0)
        intelligence = compute_portfolio_intelligence(portfolio, _FakeProvider({}), pending_proposal_count=0)
        snapshot = compute_portfolio_risk_snapshot(
            portfolio, limits, intelligence, daily_circuit_breaker_tier="none", daily_pnl_pct=0.0, emergency_stop_active=False
        )
        assert snapshot.risk_state == "halted"
        assert snapshot.current_drawdown_pct == 25.0

    def test_daily_circuit_breaker_tier2_is_restricted(self) -> None:
        portfolio = _portfolio()
        intelligence = compute_portfolio_intelligence(portfolio, _FakeProvider({}), pending_proposal_count=0)
        snapshot = compute_portfolio_risk_snapshot(
            portfolio, RiskLimits(), intelligence, daily_circuit_breaker_tier="tier2", daily_pnl_pct=-2.0, emergency_stop_active=False
        )
        assert snapshot.risk_state == "restricted"

    def test_daily_circuit_breaker_tier1_is_warning_not_restricted(self) -> None:
        portfolio = _portfolio()
        intelligence = compute_portfolio_intelligence(portfolio, _FakeProvider({}), pending_proposal_count=0)
        snapshot = compute_portfolio_risk_snapshot(
            portfolio, RiskLimits(), intelligence, daily_circuit_breaker_tier="tier1", daily_pnl_pct=-1.0, emergency_stop_active=False
        )
        assert snapshot.risk_state == "warning"

    def test_snapshot_carries_the_real_correlated_clusters_through(self) -> None:
        closes = [100.0 + i for i in range(10)]
        portfolio = _portfolio(
            positions=[
                PaperPosition(
                    id="p1", symbol="AAPL", side="buy", quantity=10.0, entryPrice=100.0, currentPrice=100.0,  # type: ignore[arg-type]
                    unrealizedPnl=0.0, unrealizedPnlPct=0.0, openedBy="sentinel", confidence=80.0,  # type: ignore[arg-type]
                    openedAt="2024-01-01T00:00:00+00:00",
                ),
                PaperPosition(
                    id="p2", symbol="MSFT", side="buy", quantity=10.0, entryPrice=200.0, currentPrice=200.0,  # type: ignore[arg-type]
                    unrealizedPnl=0.0, unrealizedPnlPct=0.0, openedBy="sentinel", confidence=80.0,  # type: ignore[arg-type]
                    openedAt="2024-01-01T00:00:00+00:00",
                ),
            ]
        )
        provider = _FakeProvider({"AAPL": closes, "MSFT": [c * 2 for c in closes]})
        intelligence = compute_portfolio_intelligence(portfolio, provider, pending_proposal_count=0)
        snapshot = compute_portfolio_risk_snapshot(
            portfolio, RiskLimits(), intelligence, daily_circuit_breaker_tier="none", daily_pnl_pct=0.0, emergency_stop_active=False
        )
        assert len(snapshot.correlated_clusters) == 1
        assert snapshot.largest_correlated_cluster_pct > 0.0


class TestEvaluatePretradeRiskDecision:
    def test_no_violations_is_approved_with_no_reasons(self) -> None:
        portfolio = _portfolio()
        decision = evaluate_pretrade_risk_decision(
            RiskLimits(), portfolio, symbol="AAPL", proposed_value=100.0, sim_day=0, emergency_stop_active=False
        )
        assert decision.verdict == "approved"
        assert decision.reasons == []

    def test_emergency_stop_short_circuits_to_halted(self) -> None:
        portfolio = _portfolio()
        decision = evaluate_pretrade_risk_decision(
            RiskLimits(), portfolio, symbol="AAPL", proposed_value=100.0, sim_day=0, emergency_stop_active=True
        )
        assert decision.verdict == "halted"
        assert decision.reason_codes == ["emergency_stop_active"]

    def test_critical_sentinel_violation_is_rejected_with_a_real_reason(self) -> None:
        limits = RiskLimits(maxDrawdownPct=20.0)
        portfolio = _portfolio(trades=[_trade(pnl=-25_000.0)], cash=75_000.0)
        decision = evaluate_pretrade_risk_decision(
            limits, portfolio, symbol="AAPL", proposed_value=100.0, sim_day=5, emergency_stop_active=False
        )
        assert decision.verdict == "rejected"
        assert "risk_lifetime_drawdown" in decision.reason_codes
        assert any("drawdown" in r.lower() for r in decision.reasons)

    def test_only_guardian_warning_is_approved_with_reduction_not_rejected(self) -> None:
        limits = RiskLimits(maxSectorConcentrationPct=10.0)
        position = PaperPosition(
            id="pos-1", symbol="AAPL", side="buy", quantity=100.0, entryPrice=50.0, currentPrice=50.0,  # type: ignore[arg-type]
            unrealizedPnl=0.0, unrealizedPnlPct=0.0, openedBy="sentinel", confidence=80.0,  # type: ignore[arg-type]
            openedAt="2024-01-01T00:00:00+00:00",
        )
        # starting_balance matches the position's own real value so this
        # isolates the concentration check alone — a lower starting
        # balance would also (correctly, under the new real drawdown
        # fix) trip a genuine drawdown violation from capital already
        # deployed into this one position.
        portfolio = _portfolio(cash=0.0, starting=5_000.0, positions=[position])
        decision = evaluate_pretrade_risk_decision(
            limits, portfolio, symbol="AAPL", proposed_value=100.0, sim_day=0, emergency_stop_active=False
        )
        assert decision.verdict == "approved_with_reduction"
        assert "risk_concentration_limit" in decision.reason_codes

    def test_reasons_are_every_real_violation_not_just_the_first(self) -> None:
        limits = RiskLimits(maxOpenPositions=1, maxPositionPct=1.0)
        position = PaperPosition(
            id="pos-1", symbol="MSFT", side="buy", quantity=10.0, entryPrice=50.0, currentPrice=50.0,  # type: ignore[arg-type]
            unrealizedPnl=0.0, unrealizedPnlPct=0.0, openedBy="sentinel", confidence=80.0,  # type: ignore[arg-type]
            openedAt="2024-01-01T00:00:00+00:00",
        )
        portfolio = _portfolio(cash=10_000.0, starting=10_000.0, positions=[position])
        decision = evaluate_pretrade_risk_decision(
            limits, portfolio, symbol="AAPL", proposed_value=5_000.0, sim_day=0, emergency_stop_active=False
        )
        assert len(decision.reasons) >= 2
        assert "risk_max_open_positions" in decision.reason_codes
        assert "risk_position_size_limit" in decision.reason_codes
