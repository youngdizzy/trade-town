"""Covers app/evaluation_simulator.py — Quantitative Research &
Intelligence System, Requirements 21/22/23/25 (Piece 10). Every field
must trace to a real simulated outcome, never a fabricated conclusion —
and this module must never declare a risk policy superior merely
because it's faster (Requirement 25)."""
from __future__ import annotations

from app.accounts import create_account
from app.evaluation_simulator import (
    CONSECUTIVE_LOSS_STREAK_THRESHOLD,
    RISK_POLICY_PER_TRADE_PCT,
    compare_evaluation_policies,
    simulate_evaluation_policy,
)
from app.risk_engine import default_risk_limits
from app.schemas import Account, SimulationResult, Strategy


def _now_iso() -> str:
    return "2026-01-01T00:00:00+00:00"


def _strategy(*, strategy_id: str = "strategy-1") -> Strategy:
    return Strategy(
        id=strategy_id,
        name="Momentum Breakout",
        description="Follows short-term price momentum.",
        createdBy="echo",  # type: ignore[arg-type]
        focusCategory="stock",  # type: ignore[arg-type]
        createdAt=_now_iso(),
    )


def _result(
    *,
    strategy_id: str = "strategy-1",
    win_rate: float = 60.0,
    avg_win_pct: float = 5.0,
    avg_loss_pct: float = -3.0,
    trade_count: int = 20,
) -> SimulationResult:
    return SimulationResult(
        id=f"result-{strategy_id}-{win_rate}",
        strategyId=strategy_id,
        strategyName="Momentum Breakout",
        symbol="NEXA",
        totalReturnPct=10.0,
        winRate=win_rate,
        maxDrawdownPct=10.0,
        sharpeRatio=1.0,
        sortinoRatio=1.2,
        tradeCount=trade_count,
        runBy="echo",  # type: ignore[arg-type]
        completedAt=_now_iso(),
        avgWinPct=avg_win_pct,
        avgLossPct=avg_loss_pct,
    )


def _account(*, trailing_drawdown_limit_pct: float | None = None, challenge_profit_target_pct: float | None = None, challenge_duration_days: int | None = None, evaluation_cost: float | None = None) -> Account:
    accounts, error = create_account(
        [], name="Eval Test", account_type="prop_firm", starting_balance=50_000.0, base_risk_limits=default_risk_limits(), account_id="acct-eval", now_iso=_now_iso()
    )
    assert error is None
    account = accounts[0]
    return account.model_copy(
        update={
            "trailing_drawdown_limit_pct": trailing_drawdown_limit_pct,
            "challenge_profit_target_pct": challenge_profit_target_pct,
            "challenge_duration_days": challenge_duration_days,
            "evaluation_cost": evaluation_cost,
        }
    )


class TestSimulateEvaluationPolicyDeterminism:
    """Professional Research → Certification → Paper → Capital
    Allocation Pipeline — an audit found this module's Monte Carlo used
    the bare, unseeded global `random` module, so identical certification
    questions could get different real answers on every re-run. This
    confirms the fix: the exact same inputs now always produce the exact
    same real distribution."""

    def test_identical_inputs_produce_identical_results(self) -> None:
        kwargs = dict(
            policy_id="moderate",
            risk_per_trade_pct=2.0,
            win_rate=0.55,
            avg_win_pct=4.0,
            avg_loss_pct=-2.5,
            profit_target_pct=8.0,
            drawdown_limit_pct=10.0,
            max_trades=100,
            evaluation_cost=None,
            paths=100,
            seed_key="strategy-determinism-test",
        )
        first = simulate_evaluation_policy(**kwargs)  # type: ignore[arg-type]
        second = simulate_evaluation_policy(**kwargs)  # type: ignore[arg-type]
        assert first == second


class TestSimulateEvaluationPolicy:
    def test_a_guaranteed_winner_always_passes(self) -> None:
        result = simulate_evaluation_policy(
            policy_id="moderate",
            risk_per_trade_pct=2.0,
            win_rate=1.0,
            avg_win_pct=5.0,
            avg_loss_pct=-3.0,
            profit_target_pct=8.0,
            drawdown_limit_pct=10.0,
            max_trades=200,
            evaluation_cost=None,
            paths=50,
        )
        assert result.probability_of_passing_pct == 100.0
        assert result.probability_of_failing_drawdown_pct == 0.0
        assert result.probability_of_failing_time_expiry_pct == 0.0
        assert result.expected_trades_to_pass is not None

    def test_a_guaranteed_loser_never_passes(self) -> None:
        result = simulate_evaluation_policy(
            policy_id="moderate",
            risk_per_trade_pct=2.0,
            win_rate=0.0,
            avg_win_pct=5.0,
            avg_loss_pct=-3.0,
            profit_target_pct=8.0,
            drawdown_limit_pct=10.0,
            max_trades=200,
            evaluation_cost=None,
            paths=50,
        )
        assert result.probability_of_passing_pct == 0.0
        assert result.expected_trades_to_pass is None
        assert result.expected_trading_days_to_pass is None
        assert result.expected_cost_to_pass is None
        # A guaranteed loser must fail either by drawdown or by running
        # out of simulated trades — never silently "pass" some other way.
        assert result.probability_of_failing_drawdown_pct + result.probability_of_failing_time_expiry_pct == 100.0

    def test_a_guaranteed_loser_always_hits_the_consecutive_loss_streak(self) -> None:
        # A wide drawdown limit (99%, effectively unreachable at this
        # loss size/trade count) so the path survives long enough via
        # time-expiry to actually accumulate 5 consecutive real losses,
        # rather than failing on drawdown first.
        result = simulate_evaluation_policy(
            policy_id="moderate",
            risk_per_trade_pct=2.0,
            win_rate=0.0,
            avg_win_pct=5.0,
            avg_loss_pct=-1.0,
            profit_target_pct=8.0,
            drawdown_limit_pct=99.0,
            max_trades=50,
            evaluation_cost=None,
            paths=50,
        )
        assert result.consecutive_loss_streak_threshold == CONSECUTIVE_LOSS_STREAK_THRESHOLD
        assert result.probability_of_consecutive_loss_streak_pct == 100.0

    def test_a_strong_edge_passes_far_more_often_than_a_weak_edge(self) -> None:
        strong = simulate_evaluation_policy(
            policy_id="moderate",
            risk_per_trade_pct=2.0,
            win_rate=0.85,
            avg_win_pct=6.0,
            avg_loss_pct=-2.0,
            profit_target_pct=8.0,
            drawdown_limit_pct=15.0,
            max_trades=100,
            evaluation_cost=None,
            paths=300,
        )
        weak = simulate_evaluation_policy(
            policy_id="moderate",
            risk_per_trade_pct=2.0,
            win_rate=0.25,
            avg_win_pct=1.0,
            avg_loss_pct=-6.0,
            profit_target_pct=8.0,
            drawdown_limit_pct=15.0,
            max_trades=100,
            evaluation_cost=None,
            paths=300,
        )
        assert strong.probability_of_passing_pct > weak.probability_of_passing_pct

    def test_a_higher_risk_per_trade_produces_more_drawdown_failures_for_a_losing_edge(self) -> None:
        # Requirement 22: "slower" (lower risk/trade) does not
        # automatically mean safer, but a real losing edge sized more
        # aggressively should show measurably higher drawdown-failure
        # risk than the same losing edge sized conservatively.
        conservative = simulate_evaluation_policy(
            policy_id="conservative",
            risk_per_trade_pct=RISK_POLICY_PER_TRADE_PCT["conservative"],
            win_rate=0.45,
            avg_win_pct=2.0,
            avg_loss_pct=-2.2,
            profit_target_pct=20.0,
            drawdown_limit_pct=8.0,
            max_trades=60,
            evaluation_cost=None,
            paths=500,
        )
        aggressive = simulate_evaluation_policy(
            policy_id="aggressive",
            risk_per_trade_pct=RISK_POLICY_PER_TRADE_PCT["aggressive"],
            win_rate=0.45,
            avg_win_pct=2.0,
            avg_loss_pct=-2.2,
            profit_target_pct=20.0,
            drawdown_limit_pct=8.0,
            max_trades=60,
            evaluation_cost=None,
            paths=500,
        )
        assert aggressive.probability_of_failing_drawdown_pct >= conservative.probability_of_failing_drawdown_pct

    def test_expected_cost_to_pass_only_computed_when_paths_actually_pass(self) -> None:
        result = simulate_evaluation_policy(
            policy_id="moderate",
            risk_per_trade_pct=2.0,
            win_rate=0.9,
            avg_win_pct=6.0,
            avg_loss_pct=-2.0,
            profit_target_pct=8.0,
            drawdown_limit_pct=20.0,
            max_trades=100,
            evaluation_cost=150.0,
            paths=100,
        )
        assert result.probability_of_passing_pct > 0.0
        assert result.expected_cost_to_pass is not None
        assert result.expected_cost_to_pass >= 150.0  # never cheaper than one real evaluation fee

    def test_sensitivity_to_strategy_quality_moves_in_the_right_direction(self) -> None:
        result = simulate_evaluation_policy(
            policy_id="moderate",
            risk_per_trade_pct=2.0,
            win_rate=0.5,
            avg_win_pct=3.0,
            avg_loss_pct=-3.0,
            profit_target_pct=8.0,
            drawdown_limit_pct=15.0,
            max_trades=150,
            evaluation_cost=None,
            paths=300,
        )
        assert result.probability_of_passing_at_higher_quality_pct >= result.probability_of_passing_at_lower_quality_pct


class TestCompareEvaluationPolicies:
    def test_no_completed_simulation_runs_returns_none(self) -> None:
        assert compare_evaluation_policies(_strategy(), [], account=None, sim_day=5) is None

    def test_returns_three_fixed_policies_without_an_account(self) -> None:
        strategy = _strategy()
        report = compare_evaluation_policies(strategy, [_result()], account=None, sim_day=5)
        assert report is not None
        assert {p.policy_id for p in report.policies} == {"conservative", "moderate", "aggressive"}
        assert any("NOT_TRACKABLE_YET" in limitation for limitation in report.limitations)

    def test_adds_the_fourth_failure_boundary_relative_policy_with_a_real_account_boundary(self) -> None:
        strategy = _strategy()
        account = _account(trailing_drawdown_limit_pct=8.0)
        report = compare_evaluation_policies(strategy, [_result()], account=account, sim_day=5)
        assert report is not None
        assert {p.policy_id for p in report.policies} == {"conservative", "moderate", "aggressive", "failure_boundary_relative"}
        boundary_policy = next(p for p in report.policies if p.policy_id == "failure_boundary_relative")
        assert boundary_policy.risk_per_trade_pct == 1.0  # 8.0 * 0.125

    def test_uses_real_account_profit_target_and_drawdown_limit_when_configured(self) -> None:
        strategy = _strategy()
        account = _account(trailing_drawdown_limit_pct=12.0, challenge_profit_target_pct=6.0, challenge_duration_days=20)
        report = compare_evaluation_policies(strategy, [_result()], account=account, sim_day=5)
        assert report is not None
        assert report.profit_target_pct == 6.0
        assert report.drawdown_limit_pct == 12.0
        assert report.max_trades == 40  # 20 days * ASSUMED_TRADES_PER_DAY (2.0)

    def test_falls_back_to_disclosed_defaults_without_a_configured_account(self) -> None:
        strategy = _strategy()
        report = compare_evaluation_policies(strategy, [_result()], account=None, sim_day=5)
        assert report is not None
        assert any("disclosed default" in a for a in report.assumptions)

    def test_never_declares_a_winning_policy(self) -> None:
        strategy = _strategy()
        report = compare_evaluation_policies(strategy, [_result()], account=None, sim_day=5)
        assert report is not None
        assert "no policy is declared superior" in report.conclusion

    def test_sample_trade_count_reflects_real_aggregated_data(self) -> None:
        strategy = _strategy()
        results = [_result(trade_count=20), _result(win_rate=70.0, trade_count=15)]
        report = compare_evaluation_policies(strategy, results, account=None, sim_day=5)
        assert report is not None
        assert report.sample_trade_count == 35

    def test_only_this_strategys_own_results_are_used(self) -> None:
        strategy = _strategy(strategy_id="strategy-1")
        other_result = _result(strategy_id="strategy-2")
        report = compare_evaluation_policies(strategy, [other_result], account=None, sim_day=5)
        assert report is None
