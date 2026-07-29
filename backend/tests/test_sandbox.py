"""Covers app/sandbox.py — v0.7 Feature 45, the Research Sandbox. Every
stage transition must trace to a real signal (a completed ResearchItem,
a completed SimulationResult in the right scenario bucket, a real CEO
action) and strategies must never skip stages. Company Review verdicts
must be computed from that strategy's own real, aggregated history.
"""
from __future__ import annotations

from app.sandbox import (
    QUANT_MIN_SAMPLE_SIZE,
    RISK_MAX_AVG_DRAWDOWN,
    apply_review_decision,
    begin_company_review,
    begin_limited_live,
    begin_paper_trial,
    generate_strategy_report,
    generate_strategy_review,
    maybe_advance_after_research,
    maybe_advance_after_result,
)
from app.schemas import ResearchItem, SimulationResult, Strategy


def _now_iso() -> str:
    return "2026-01-01T00:00:00+00:00"


def _strategy(stage: str = "idea", *, allocated_capital: float = 0.0) -> Strategy:
    return Strategy(
        id="strategy-1",
        name="Momentum Breakout",
        description="Follows short-term price momentum.",
        createdBy="echo",  # type: ignore[arg-type]
        focusCategory="stock",  # type: ignore[arg-type]
        createdAt=_now_iso(),
        stage=stage,  # type: ignore[arg-type]
        allocatedCapital=allocated_capital,
    )


def _research_item(*, category: str = "stock", status: str = "completed") -> ResearchItem:
    return ResearchItem(
        id="research-1",
        title="Momentum screen",
        symbol="NEXA",
        category=category,  # type: ignore[arg-type]
        priority="normal",  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        assignedAgent="echo",  # type: ignore[arg-type]
        summary="Momentum looks strong.",
        confidence=70.0,
        createdAt=_now_iso(),
        updatedAt=_now_iso(),
    )


def _result(
    *,
    strategy_id: str = "strategy-1",
    scenario: str = "historical",
    win_rate: float = 60.0,
    sharpe_ratio: float = 1.5,
    max_drawdown_pct: float = 10.0,
    expected_value_pct: float = 1.0,
    win_count: int = 6,
    loss_count: int = 4,
    avg_win_pct: float = 5.0,
    avg_loss_pct: float = -3.0,
    profit_factor: float = 2.5,
    total_return_pct: float = 18.0,
    trade_count: int = 10,
) -> SimulationResult:
    return SimulationResult(
        id=f"result-{strategy_id}-{scenario}",
        strategyId=strategy_id,
        strategyName="Momentum Breakout",
        symbol="NEXA",
        totalReturnPct=total_return_pct,
        winRate=win_rate,
        maxDrawdownPct=max_drawdown_pct,
        sharpeRatio=sharpe_ratio,
        sortinoRatio=sharpe_ratio,
        tradeCount=trade_count,
        runBy="quant",  # type: ignore[arg-type]
        completedAt=_now_iso(),
        scenario=scenario,  # type: ignore[arg-type]
        winCount=win_count,
        lossCount=loss_count,
        avgWinPct=avg_win_pct,
        avgLossPct=avg_loss_pct,
        expectedValuePct=expected_value_pct,
        profitFactor=profit_factor,
        riskRewardRatio=avg_win_pct / abs(avg_loss_pct),
    )


class TestMaybeAdvanceAfterResearch:
    def test_advances_idea_to_research_when_a_matching_completed_item_exists(self) -> None:
        strategy = _strategy(stage="idea")
        updated = maybe_advance_after_research(strategy, [_research_item()], sim_day=5)
        assert updated.stage == "research"
        assert len(updated.stage_history) == 1
        assert updated.stage_history[0].sim_day == 5

    def test_does_not_advance_without_a_matching_category(self) -> None:
        strategy = _strategy(stage="idea")
        updated = maybe_advance_after_research(strategy, [_research_item(category="gold")], sim_day=5)
        assert updated.stage == "idea"

    def test_does_not_advance_on_an_incomplete_item(self) -> None:
        strategy = _strategy(stage="idea")
        updated = maybe_advance_after_research(strategy, [_research_item(status="in_progress")], sim_day=5)
        assert updated.stage == "idea"

    def test_does_not_re_advance_a_strategy_already_past_idea(self) -> None:
        strategy = _strategy(stage="market_simulation")
        updated = maybe_advance_after_research(strategy, [_research_item()], sim_day=5)
        assert updated.stage == "market_simulation"


class TestMaybeAdvanceAfterResult:
    def test_historical_result_advances_idea_or_research_to_historical_backtest(self) -> None:
        strategy = _strategy(stage="research")
        updated = maybe_advance_after_result(strategy, _result(scenario="historical"), sim_day=6)
        assert updated.stage == "historical_backtest"

    def test_non_historical_result_cannot_skip_to_market_simulation_without_historical_first(self) -> None:
        strategy = _strategy(stage="research")
        updated = maybe_advance_after_result(strategy, _result(scenario="bull"), sim_day=6)
        assert updated.stage == "research"

    def test_non_historical_result_advances_historical_backtest_to_market_simulation(self) -> None:
        strategy = _strategy(stage="historical_backtest")
        updated = maybe_advance_after_result(strategy, _result(scenario="bull"), sim_day=7)
        assert updated.stage == "market_simulation"

    def test_never_moves_backward(self) -> None:
        strategy = _strategy(stage="paper_trading")
        updated = maybe_advance_after_result(strategy, _result(scenario="historical"), sim_day=8)
        assert updated.stage == "paper_trading"


class TestPipelineCeoActions:
    def test_begin_paper_trial_requires_market_simulation_stage(self) -> None:
        strategy = _strategy(stage="historical_backtest")
        updated, error = begin_paper_trial(strategy, sim_day=9)
        assert updated is None
        assert error is not None

    def test_begin_paper_trial_succeeds_from_market_simulation(self) -> None:
        strategy = _strategy(stage="market_simulation")
        updated, error = begin_paper_trial(strategy, sim_day=9)
        assert error is None
        assert updated is not None
        assert updated.stage == "paper_trading"

    def test_begin_limited_live_requires_paper_trading_stage(self) -> None:
        strategy = _strategy(stage="market_simulation")
        updated, error = begin_limited_live(strategy, 500.0, sim_day=10)
        assert updated is None
        assert error is not None

    def test_begin_limited_live_rejects_a_cap_over_the_maximum(self) -> None:
        strategy, _ = begin_paper_trial(_strategy(stage="market_simulation"), sim_day=9)
        assert strategy is not None
        updated, error = begin_limited_live(strategy, 999_999.0, sim_day=9)
        assert updated is None
        assert error is not None

    def test_begin_limited_live_sets_the_real_allocated_capital(self) -> None:
        strategy, _ = begin_paper_trial(_strategy(stage="market_simulation"), sim_day=9)
        assert strategy is not None
        updated, error = begin_limited_live(strategy, 500.0, sim_day=10)
        assert error is None
        assert updated is not None
        assert updated.stage == "limited_live_capital"
        assert updated.allocated_capital == 500.0

    def test_begin_company_review_requires_limited_live_capital_stage(self) -> None:
        strategy = _strategy(stage="paper_trading")
        updated, error = begin_company_review(strategy, sim_day=11)
        assert updated is None
        assert error is not None

    def test_begin_company_review_succeeds_from_limited_live_capital(self) -> None:
        strategy = _strategy(stage="limited_live_capital")
        updated, error = begin_company_review(strategy, sim_day=11)
        assert error is None
        assert updated is not None
        assert updated.stage == "company_review"


class TestApplyReviewDecision:
    def test_approval_advances_to_approved(self) -> None:
        strategy = _strategy(stage="company_review")
        review = generate_strategy_review(strategy, [_result()] * QUANT_MIN_SAMPLE_SIZE, [_research_item()], 0, sim_day=12)
        updated = apply_review_decision(strategy, review, True, sim_day=12)
        assert updated.stage == "approved"

    def test_rejection_sends_it_back_to_limited_live_capital_without_losing_history(self) -> None:
        strategy = _strategy(stage="company_review")
        strategy = strategy.model_copy(update={"stage_history": [*strategy.stage_history]})
        review = generate_strategy_review(strategy, [], [], 0, sim_day=12)
        updated = apply_review_decision(strategy, review, False, sim_day=12)
        assert updated.stage == "limited_live_capital"
        assert len(updated.stage_history) == 1


class TestGenerateStrategyReview:
    def test_all_five_reviewers_pass_on_strong_consistent_history(self) -> None:
        strategy = _strategy(stage="company_review")
        results = [_result(scenario="historical"), _result(scenario="bull"), _result(scenario="bear")]
        review = generate_strategy_review(strategy, results, [_research_item()], 0, sim_day=13)
        assert len(review.verdicts) == 5
        assert review.overall_verdict == "pass"
        assert all(v.verdict == "pass" for v in review.verdicts)

    def test_quant_flags_a_concern_below_the_minimum_sample_size(self) -> None:
        strategy = _strategy(stage="company_review")
        review = generate_strategy_review(strategy, [_result()], [_research_item()], 0, sim_day=13)
        quant = next(v for v in review.verdicts if v.reviewer_role == "quant")
        assert quant.verdict != "pass"

    def test_quant_fails_on_a_low_win_rate_with_enough_samples(self) -> None:
        strategy = _strategy(stage="company_review")
        results = [_result(win_rate=20.0, sharpe_ratio=0.2) for _ in range(QUANT_MIN_SAMPLE_SIZE)]
        review = generate_strategy_review(strategy, results, [_research_item()], 0, sim_day=13)
        quant = next(v for v in review.verdicts if v.reviewer_role == "quant")
        assert quant.verdict == "fail"
        assert review.overall_verdict == "fail"

    def test_risk_flags_high_average_drawdown(self) -> None:
        strategy = _strategy(stage="company_review")
        results = [_result(max_drawdown_pct=RISK_MAX_AVG_DRAWDOWN + 20.0)]
        review = generate_strategy_review(strategy, results, [_research_item()], 0, sim_day=13)
        risk = next(v for v in review.verdicts if v.reviewer_role == "risk")
        assert risk.verdict != "pass"

    def test_technical_wants_more_than_one_scenario_tested(self) -> None:
        strategy = _strategy(stage="company_review")
        results = [_result(scenario="historical")]
        review = generate_strategy_review(strategy, results, [_research_item()], 0, sim_day=13)
        technical = next(v for v in review.verdicts if v.reviewer_role == "technical")
        assert technical.verdict == "concern"

    def test_fundamental_flags_missing_research(self) -> None:
        strategy = _strategy(stage="company_review")
        review = generate_strategy_review(strategy, [_result()], [], 0, sim_day=13)
        fundamental = next(v for v in review.verdicts if v.reviewer_role == "fundamental")
        assert fundamental.verdict == "concern"

    def test_devils_advocate_flags_a_negative_expected_value_run(self) -> None:
        strategy = _strategy(stage="company_review")
        results = [_result(expected_value_pct=-0.5, max_drawdown_pct=5.0)]
        review = generate_strategy_review(strategy, results, [_research_item()], 0, sim_day=13)
        devils_advocate = next(v for v in review.verdicts if v.reviewer_role == "devils_advocate")
        assert devils_advocate.verdict == "concern"

    def test_devils_advocate_rotates_through_a_distinct_pool_across_reviews(self) -> None:
        strategy = _strategy(stage="company_review")
        results = [_result()] * QUANT_MIN_SAMPLE_SIZE
        first = generate_strategy_review(strategy, results, [_research_item()], 0, sim_day=13)
        second = generate_strategy_review(strategy, results, [_research_item()], 1, sim_day=13)
        first_da = next(v for v in first.verdicts if v.reviewer_role == "devils_advocate")
        second_da = next(v for v in second.verdicts if v.reviewer_role == "devils_advocate")
        assert first_da.reviewer_agent != second_da.reviewer_agent

    def test_reviewer_agents_never_repeat_within_one_review(self) -> None:
        strategy = _strategy(stage="company_review")
        results = [_result()] * QUANT_MIN_SAMPLE_SIZE
        review = generate_strategy_review(strategy, results, [_research_item()], 0, sim_day=13)
        agents = [v.reviewer_agent for v in review.verdicts]
        assert len(agents) == len(set(agents))


class TestGenerateStrategyReport:
    def test_report_cites_the_real_scenario_and_numbers(self) -> None:
        strategy = _strategy()
        result = _result(scenario="bull", win_rate=70.0, total_return_pct=25.0)
        report = generate_strategy_report(strategy, result, sim_day=14)
        assert report.scenario == "bull"
        assert report.source_result_id == result.id
        assert "70" in report.executive_summary or "Bull" in report.executive_summary

    def test_weak_profit_factor_produces_a_real_weakness_and_failure_condition(self) -> None:
        strategy = _strategy()
        result = _result(profit_factor=0.7, win_count=3, loss_count=7, avg_win_pct=1.0, avg_loss_pct=-2.0)
        report = generate_strategy_report(strategy, result, sim_day=14)
        assert any("Profit factor" in w for w in report.weaknesses)
        assert report.failure_conditions

    def test_strong_result_produces_real_strengths_and_no_forced_weaknesses_list(self) -> None:
        strategy = _strategy()
        result = _result(win_rate=65.0, profit_factor=2.0, max_drawdown_pct=8.0)
        report = generate_strategy_report(strategy, result, sim_day=14)
        assert len(report.strengths) >= 2
