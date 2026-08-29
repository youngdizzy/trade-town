"""Covers app/portfolio_risk.py — CEO directive "Portfolio Risk Engine +
Firm-Wide Risk Governance." Every value must trace back to a real
already-computed source; this file focuses on the composition logic
itself (risk-state escalation, pre-trade decision reason aggregation),
not re-testing the underlying real checks (already covered by
test_risk_engine.py / test_portfolio_intelligence.py).
"""
from __future__ import annotations

from app.portfolio_intelligence import compute_portfolio_intelligence
from app.portfolio_risk import compute_portfolio_risk_snapshot, evaluate_marginal_portfolio_risk, evaluate_pretrade_risk_decision
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


class TestEvaluateMarginalPortfolioRisk:
    """CEO directive "Portfolio Risk Engine + Cross-Trade Capital
    Allocation," Phase 17 — the real Marginal Risk Test: portfolio
    state computed once WITHOUT the candidate, once WITH it, via a real
    synthetic-portfolio recomputation through the exact same
    compute_portfolio_intelligence() every other real portfolio read
    already uses."""

    def test_no_existing_positions_is_approved_at_full_requested_value(self) -> None:
        portfolio = _portfolio()
        provider = _FakeProvider({"AAPL": [100.0 + i for i in range(30)]})
        decision = evaluate_marginal_portfolio_risk(
            RiskLimits(), portfolio, provider, symbol="AAPL", proposed_value=5_000.0, sim_day=0, emergency_stop_active=False
        )
        assert decision.decision == "approved"
        assert decision.allowed_value == 5_000.0
        assert decision.reduction_factor == 1.0
        assert decision.correlation_impact == "low"
        assert decision.veto_reasons == []

    def test_no_real_candle_history_is_data_blocked(self) -> None:
        portfolio = _portfolio()
        provider = _FakeProvider({})
        decision = evaluate_marginal_portfolio_risk(
            RiskLimits(), portfolio, provider, symbol="ZZZZ", proposed_value=5_000.0, sim_day=0, emergency_stop_active=False
        )
        assert decision.decision == "data_blocked"
        assert decision.allowed_value == 0.0
        assert decision.individual_risk_usd is None
        assert decision.veto_reasons

    def test_emergency_stop_vetoes_regardless_of_correlation(self) -> None:
        portfolio = _portfolio()
        provider = _FakeProvider({"AAPL": [100.0 + i for i in range(30)]})
        decision = evaluate_marginal_portfolio_risk(
            RiskLimits(), portfolio, provider, symbol="AAPL", proposed_value=5_000.0, sim_day=0, emergency_stop_active=True
        )
        assert decision.decision == "vetoed"
        assert decision.allowed_value == 0.0
        assert any("emergency stop" in r.lower() for r in decision.veto_reasons)

    def test_critical_sentinel_violation_vetoes_the_marginal_decision_too(self) -> None:
        limits = RiskLimits(maxDrawdownPct=20.0)
        portfolio = _portfolio(trades=[_trade(pnl=-25_000.0)], cash=75_000.0)
        provider = _FakeProvider({"AAPL": [100.0 + i for i in range(30)]})
        decision = evaluate_marginal_portfolio_risk(
            limits, portfolio, provider, symbol="AAPL", proposed_value=1_000.0, sim_day=5, emergency_stop_active=False
        )
        assert decision.decision == "vetoed"
        assert decision.allowed_value == 0.0
        assert any("drawdown" in r.lower() for r in decision.veto_reasons)

    def test_joining_an_already_correlated_cluster_reduces_the_allocation(self) -> None:
        # AAPL closes and its own perfectly-scaled counterpart clear
        # CORRELATION_CLUSTER_THRESHOLD (0.6) — same real construction
        # TestComputePortfolioRiskSnapshot's own cluster test above uses.
        closes = [100.0 + i for i in range(30)]
        held = PaperPosition(
            id="held-1", symbol="MSFT", side="buy", quantity=125.0, entryPrice=200.0, currentPrice=200.0,  # type: ignore[arg-type]
            unrealizedPnl=0.0, unrealizedPnlPct=0.0, openedBy="sentinel", confidence=80.0,  # type: ignore[arg-type]
            openedAt="2024-01-01T00:00:00+00:00",
        )
        # $25,000 of MSFT against $100,000 equity (cash 75,000 + 25,000
        # position) = 25% held alone, under the 40% threshold by itself
        # — so the cluster only crosses 40% once a correlated NVDA
        # candidate's OWN value pushes it there, leaving real room for a
        # genuine partial reduction rather than an immediate veto (see
        # the next test for the case where the existing cluster is
        # already over the threshold on its own).
        portfolio = _portfolio(cash=75_000.0, starting=100_000.0, positions=[held])
        provider = _FakeProvider({"MSFT": closes, "NVDA": [c * 2 for c in closes]})
        # maxPositionPct raised well past 50% so this test isolates the
        # correlation-cluster mechanism alone — the same isolation
        # convention TestEvaluatePretradeRiskDecision's own
        # test_only_guardian_warning_is_approved_with_reduction_not_
        # rejected already establishes for a different single check.
        limits = RiskLimits(maxPositionPct=100.0, maxSectorConcentrationPct=100.0)
        decision = evaluate_marginal_portfolio_risk(
            limits, portfolio, provider, symbol="NVDA", proposed_value=50_000.0, sim_day=0, emergency_stop_active=False
        )
        assert decision.decision == "approved_reduced"
        assert decision.allowed_value < 50_000.0
        assert decision.allowed_value > 0.0
        assert decision.correlation_impact in ("medium", "high")
        assert decision.largest_cluster_pct_after < 40.0 + 0.5  # binary search converges just under the threshold

    def test_cluster_already_at_the_threshold_is_vetoed_not_reduced_to_a_token_size(self) -> None:
        closes = [100.0 + i for i in range(30)]
        # Two correlated positions already at 45% of equity BEFORE any
        # candidate is considered — MSFT/NVDA correlated pair.
        msft = PaperPosition(
            id="held-1", symbol="MSFT", side="buy", quantity=225.0, entryPrice=200.0, currentPrice=200.0,  # type: ignore[arg-type]
            unrealizedPnl=0.0, unrealizedPnlPct=0.0, openedBy="sentinel", confidence=80.0,  # type: ignore[arg-type]
            openedAt="2024-01-01T00:00:00+00:00",
        )
        nvda = PaperPosition(
            id="held-2", symbol="NVDA", side="buy", quantity=225.0, entryPrice=200.0, currentPrice=200.0,  # type: ignore[arg-type]
            unrealizedPnl=0.0, unrealizedPnlPct=0.0, openedBy="sentinel", confidence=80.0,  # type: ignore[arg-type]
            openedAt="2024-01-01T00:00:00+00:00",
        )
        portfolio = _portfolio(cash=10_000.0, starting=100_000.0, positions=[msft, nvda])
        # AMD joins the SAME correlated cluster (perfectly scaled from
        # the same closes as MSFT/NVDA).
        provider = _FakeProvider({"MSFT": closes, "NVDA": closes, "AMD": [c * 3 for c in closes]})
        decision = evaluate_marginal_portfolio_risk(
            RiskLimits(), portfolio, provider, symbol="AMD", proposed_value=1_000.0, sim_day=0, emergency_stop_active=False
        )
        assert decision.decision == "vetoed"
        assert decision.allowed_value == 0.0
        assert decision.veto_reasons

    def test_a_candidate_unrelated_to_an_already_over_concentrated_cluster_is_not_punished_for_it(self) -> None:
        """The correlation-based reduction must be scoped to the
        CANDIDATE's own cluster, never a portfolio-wide max driven by a
        cluster the candidate has nothing to do with."""
        closes = [100.0 + i for i in range(30)]
        msft = PaperPosition(
            id="held-1", symbol="MSFT", side="buy", quantity=225.0, entryPrice=200.0, currentPrice=200.0,  # type: ignore[arg-type]
            unrealizedPnl=0.0, unrealizedPnlPct=0.0, openedBy="sentinel", confidence=80.0,  # type: ignore[arg-type]
            openedAt="2024-01-01T00:00:00+00:00",
        )
        nvda = PaperPosition(
            id="held-2", symbol="NVDA", side="buy", quantity=225.0, entryPrice=200.0, currentPrice=200.0,  # type: ignore[arg-type]
            unrealizedPnl=0.0, unrealizedPnlPct=0.0, openedBy="sentinel", confidence=80.0,  # type: ignore[arg-type]
            openedAt="2024-01-01T00:00:00+00:00",
        )
        portfolio = _portfolio(cash=10_000.0, starting=100_000.0, positions=[msft, nvda])
        # GLD is a real, distinct flat/uncorrelated series — shares no
        # real correlation with the already-concentrated MSFT/NVDA
        # cluster.
        provider = _FakeProvider({"MSFT": closes, "NVDA": closes, "GLD": [200.0 for _ in range(30)]})
        decision = evaluate_marginal_portfolio_risk(
            RiskLimits(), portfolio, provider, symbol="GLD", proposed_value=1_000.0, sim_day=0, emergency_stop_active=False
        )
        assert decision.decision == "approved"
        assert decision.allowed_value == 1_000.0
        assert decision.correlation_impact == "low"

    def test_individual_risk_usd_is_none_without_enough_real_candle_history(self) -> None:
        portfolio = _portfolio()
        provider = _FakeProvider({"AAPL": [100.0, 101.0]})
        decision = evaluate_marginal_portfolio_risk(
            RiskLimits(), portfolio, provider, symbol="AAPL", proposed_value=1_000.0, sim_day=0, emergency_stop_active=False
        )
        assert decision.individual_risk_usd is None

    def test_liquidity_status_data_unavailable_without_enough_volume_history(self) -> None:
        portfolio = _portfolio()
        provider = _FakeProvider({"AAPL": [100.0, 101.0, 102.0]})
        decision = evaluate_marginal_portfolio_risk(
            RiskLimits(), portfolio, provider, symbol="AAPL", proposed_value=1_000.0, sim_day=0, emergency_stop_active=False
        )
        assert decision.liquidity_status == "data_unavailable"

    def test_liquidity_status_valid_with_enough_uniform_volume_history(self) -> None:
        portfolio = _portfolio()
        provider = _FakeProvider({"AAPL": [100.0 + i for i in range(30)]})
        decision = evaluate_marginal_portfolio_risk(
            RiskLimits(), portfolio, provider, symbol="AAPL", proposed_value=1_000.0, sim_day=0, emergency_stop_active=False
        )
        # _FakeProvider's candles carry a uniform real volume (1000.0)
        # across every bar, so relative volume reads at (or very near)
        # 1.0 — comfortably "valid," never "data_unavailable" once
        # there's enough real history for the baseline window.
        assert decision.liquidity_status == "valid"

    def test_correlation_regime_state_reads_elevated_with_a_highly_correlated_book(self) -> None:
        closes = [100.0 + i for i in range(30)]
        msft = PaperPosition(
            id="held-1", symbol="MSFT", side="buy", quantity=10.0, entryPrice=200.0, currentPrice=200.0,  # type: ignore[arg-type]
            unrealizedPnl=0.0, unrealizedPnlPct=0.0, openedBy="sentinel", confidence=80.0,  # type: ignore[arg-type]
            openedAt="2024-01-01T00:00:00+00:00",
        )
        nvda = PaperPosition(
            id="held-2", symbol="NVDA", side="buy", quantity=10.0, entryPrice=200.0, currentPrice=200.0,  # type: ignore[arg-type]
            unrealizedPnl=0.0, unrealizedPnlPct=0.0, openedBy="sentinel", confidence=80.0,  # type: ignore[arg-type]
            openedAt="2024-01-01T00:00:00+00:00",
        )
        portfolio = _portfolio(cash=90_000.0, starting=100_000.0, positions=[msft, nvda])
        provider = _FakeProvider({"MSFT": closes, "NVDA": closes, "AAPL": [100.0 + i for i in range(30)]})
        decision = evaluate_marginal_portfolio_risk(
            RiskLimits(), portfolio, provider, symbol="AAPL", proposed_value=1_000.0, sim_day=0, emergency_stop_active=False
        )
        assert decision.correlation_regime_state in ("elevated", "extreme")

    def test_correlation_regime_state_reads_normal_with_a_single_held_position(self) -> None:
        held = PaperPosition(
            id="held-1", symbol="MSFT", side="buy", quantity=10.0, entryPrice=200.0, currentPrice=200.0,  # type: ignore[arg-type]
            unrealizedPnl=0.0, unrealizedPnlPct=0.0, openedBy="sentinel", confidence=80.0,  # type: ignore[arg-type]
            openedAt="2024-01-01T00:00:00+00:00",
        )
        portfolio = _portfolio(cash=98_000.0, starting=100_000.0, positions=[held])
        provider = _FakeProvider({"MSFT": [100.0 + i for i in range(30)], "AAPL": [100.0 + i for i in range(30)]})
        decision = evaluate_marginal_portfolio_risk(
            RiskLimits(), portfolio, provider, symbol="AAPL", proposed_value=1_000.0, sim_day=0, emergency_stop_active=False
        )
        assert decision.correlation_regime_state == "normal"

    def test_gross_and_net_exposure_after_reflect_the_added_candidate(self) -> None:
        portfolio = _portfolio()
        provider = _FakeProvider({"AAPL": [100.0 + i for i in range(30)]})
        decision = evaluate_marginal_portfolio_risk(
            RiskLimits(), portfolio, provider, symbol="AAPL", proposed_value=5_000.0, sim_day=0, emergency_stop_active=False
        )
        assert decision.gross_exposure_usd_before == 0.0
        assert decision.gross_exposure_usd_after == 5_000.0
        assert decision.net_exposure_usd_after == 5_000.0
        assert decision.leverage_before == 0.0
        assert decision.leverage_after > 0.0

    def test_deterministic_replay(self) -> None:
        closes = [100.0 + i for i in range(30)]
        held = PaperPosition(
            id="held-1", symbol="MSFT", side="buy", quantity=125.0, entryPrice=200.0, currentPrice=200.0,  # type: ignore[arg-type]
            unrealizedPnl=0.0, unrealizedPnlPct=0.0, openedBy="sentinel", confidence=80.0,  # type: ignore[arg-type]
            openedAt="2024-01-01T00:00:00+00:00",
        )
        portfolio = _portfolio(cash=75_000.0, starting=100_000.0, positions=[held])
        provider = _FakeProvider({"MSFT": closes, "NVDA": [c * 2 for c in closes]})
        limits = RiskLimits(maxPositionPct=100.0, maxSectorConcentrationPct=100.0)
        decision_1 = evaluate_marginal_portfolio_risk(limits, portfolio, provider, symbol="NVDA", proposed_value=50_000.0, sim_day=0, emergency_stop_active=False)
        decision_2 = evaluate_marginal_portfolio_risk(limits, portfolio, provider, symbol="NVDA", proposed_value=50_000.0, sim_day=0, emergency_stop_active=False)
        assert decision_1.model_dump(exclude={"computed_at"}) == decision_2.model_dump(exclude={"computed_at"})
        # A real, non-trivial case (not a vacuous "approved" replay).
        assert decision_1.decision == "approved_reduced"


class TestDeterministicReplay:
    """CEO directive "Portfolio Risk Engine + Firm-Wide Risk Governance,
    11/10 Professional Quant Implementation," Phase 27 — "given same
    portfolio, same market data, same risk configuration, same
    timestamp, the result must be reproducible." A repo audit (grepped
    both functions and every function they call in app/risk_engine.py
    for `random`/non-deterministic state) found neither
    evaluate_pretrade_risk_decision() nor compute_portfolio_risk_snapshot()
    contains any randomness or hidden wall-clock dependency in their
    actual DECISION content — the only real wall-clock read anywhere in
    the call chain (app/risk_engine.py's own `_now_iso()`) feeds a
    metadata timestamp field, never the verdict/reasons/risk-state logic
    itself. These tests PROVE that real property with real evidence,
    rather than assuming it from reading the code: both functions are
    called twice with byte-identical inputs and their real outputs
    compared field-by-field."""

    def test_pretrade_decision_is_byte_for_byte_reproducible(self) -> None:
        # PretradeRiskDecision carries no timestamp field at all — a
        # real, exact equality check is the correct, strongest possible
        # proof here, not an approximation.
        limits = RiskLimits(maxOpenPositions=1, maxPositionPct=1.0)
        position = PaperPosition(
            id="pos-1", symbol="MSFT", side="buy", quantity=10.0, entryPrice=50.0, currentPrice=50.0,  # type: ignore[arg-type]
            unrealizedPnl=0.0, unrealizedPnlPct=0.0, openedBy="sentinel", confidence=80.0,  # type: ignore[arg-type]
            openedAt="2024-01-01T00:00:00+00:00",
        )
        portfolio = _portfolio(cash=10_000.0, starting=10_000.0, positions=[position])
        decision_1 = evaluate_pretrade_risk_decision(limits, portfolio, symbol="AAPL", proposed_value=5_000.0, sim_day=0, emergency_stop_active=False)
        decision_2 = evaluate_pretrade_risk_decision(limits, portfolio, symbol="AAPL", proposed_value=5_000.0, sim_day=0, emergency_stop_active=False)
        assert decision_1 == decision_2
        # A real, non-trivial case (not a vacuous empty-reasons replay).
        assert len(decision_1.reasons) >= 2

    def test_portfolio_risk_snapshot_is_reproducible_apart_from_its_own_real_timestamp(self) -> None:
        # PortfolioRiskSnapshot carries one real, honest wall-clock
        # metadata field (computedAt — literally "when was this
        # snapshot taken," a real, correct thing to vary run-to-run) —
        # excluded from the equality check below, never silently
        # smoothed over the rest of the real decision content.
        position = PaperPosition(
            id="pos-1", symbol="AAPL", side="buy", quantity=100.0, entryPrice=50.0, currentPrice=50.0,  # type: ignore[arg-type]
            unrealizedPnl=0.0, unrealizedPnlPct=0.0, openedBy="sentinel", confidence=80.0,  # type: ignore[arg-type]
            openedAt="2024-01-01T00:00:00+00:00",
        )
        portfolio = _portfolio(cash=50_000.0, starting=100_000.0, positions=[position])
        intelligence = compute_portfolio_intelligence(portfolio, _FakeProvider({}), pending_proposal_count=0)
        snapshot_1 = compute_portfolio_risk_snapshot(portfolio, RiskLimits(), intelligence, daily_circuit_breaker_tier="tier2", daily_pnl_pct=-2.0, emergency_stop_active=False)
        snapshot_2 = compute_portfolio_risk_snapshot(portfolio, RiskLimits(), intelligence, daily_circuit_breaker_tier="tier2", daily_pnl_pct=-2.0, emergency_stop_active=False)
        assert snapshot_1.model_dump(exclude={"computed_at"}) == snapshot_2.model_dump(exclude={"computed_at"})
        # A real, non-trivial case (not a vacuous "normal" replay) — the
        # real 50% drawdown from this fixture's own starting balance
        # breaches RiskLimits()'s own default max_drawdown_pct.
        assert snapshot_1.risk_state == "halted"
