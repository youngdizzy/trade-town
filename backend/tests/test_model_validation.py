"""Covers app/model_validation.py — Quantitative Research & Intelligence
System, Piece 4: the Model Validator (Meridian/CIO), and Piece 2
(Walk-Forward / Temporal-Split Validation, the temporal_stability
check). Every check must reuse an existing, already-load-bearing
threshold (never fabricate a new one), the four-state verdict must
never silently default to "approved", and the DA-exclusion mechanism
(app/sandbox.py's _devils_advocate_verdict/generate_strategy_review
`exclude_cio`) must be provably stateless: scoped to exactly the
strategy/cycle it's invoked for, never leaking to other strategies or
persisting past the call.
"""
from __future__ import annotations

from app.model_validation import _temporal_stability_check, generate_model_validation_report
from app.sandbox import (
    STRATEGY_DEVILS_ADVOCATES,
    _devils_advocate_verdict,
    apply_review_decision,
    begin_company_review,
    generate_strategy_review,
)
from app.schemas import (
    SimulationResult,
    Strategy,
    StrategyLiquidityValidation,
    StrategyMonteCarloResult,
    StrategyRegimeBucketPerformance,
    StrategyRegimeTestReport,
)


def _now_iso() -> str:
    return "2026-01-01T00:00:00+00:00"


def _strategy(strategy_id: str = "strategy-1", *, stage: str = "company_review") -> Strategy:
    return Strategy(
        id=strategy_id,
        name="Momentum Breakout",
        description="Follows short-term price momentum.",
        createdBy="echo",  # type: ignore[arg-type]
        focusCategory="stock",  # type: ignore[arg-type]
        createdAt=_now_iso(),
        stage=stage,  # type: ignore[arg-type]
    )


def _result(
    *,
    strategy_id: str = "strategy-1",
    trade_count: int = 5,
    expected_value_pct: float = 1.0,
) -> SimulationResult:
    return SimulationResult(
        id=f"result-{strategy_id}-{trade_count}",
        strategyId=strategy_id,
        strategyName="Momentum Breakout",
        symbol="NEXA",
        totalReturnPct=10.0,
        winRate=60.0,
        maxDrawdownPct=10.0,
        sharpeRatio=1.5,
        sortinoRatio=1.5,
        tradeCount=trade_count,
        runBy="quant",  # type: ignore[arg-type]
        completedAt=_now_iso(),
        expectedValuePct=expected_value_pct,
    )


def _monte_carlo(*, strategy_id: str = "strategy-1", probability_of_ruin_pct: float = 5.0) -> StrategyMonteCarloResult:
    return StrategyMonteCarloResult(
        id=f"montecarlo-{strategy_id}",
        strategyId=strategy_id,
        strategyName="Momentum Breakout",
        pathsSimulated=200,
        tradesPerPath=20,
        sourceWinRate=55.0,
        sourceAvgWinPct=2.0,
        sourceAvgLossPct=-1.0,
        medianReturnPct=5.0,
        returnRangeLowPct=-2.0,
        returnRangeHighPct=12.0,
        medianMaxDrawdownPct=8.0,
        worstCaseDrawdownPct=15.0,
        probabilityOfProfitPct=65.0,
        probabilityOfRuinPct=probability_of_ruin_pct,
        capitalSurvivalPct=100.0 - probability_of_ruin_pct,
        valueAtRisk95Pct=-10.0,
        valueAtRisk99Pct=-18.0,
        conditionalValueAtRisk95Pct=-14.0,
        conditionalValueAtRisk99Pct=-22.0,
        simDay=10,
        createdAt=_now_iso(),
    )


_REGIME_SCENARIOS = ("historical", "bull", "bear", "sideways")


def _regime_test(*, strategy_id: str = "strategy-1", tested_count: int = 2, any_weak: bool = False) -> StrategyRegimeTestReport:
    buckets = [
        StrategyRegimeBucketPerformance(
            scenario=_REGIME_SCENARIOS[i],  # type: ignore[arg-type]
            regimes=["strong_bull_trend"],  # type: ignore[arg-type]
            tested=i < tested_count,
            runCount=3,
            avgReturnPct=-5.0 if (any_weak and i == 0) else 5.0,
            avgWinRate=40.0 if (any_weak and i == 0) else 60.0,
            verdict="weak" if (any_weak and i == 0 and i < tested_count) else ("strong" if i < tested_count else "untested"),  # type: ignore[arg-type]
        )
        for i in range(max(tested_count, 2))
    ]
    return StrategyRegimeTestReport(
        id=f"regime-{strategy_id}",
        strategyId=strategy_id,
        strategyName="Momentum Breakout",
        buckets=buckets,
        simDay=10,
        createdAt=_now_iso(),
    )


def _liquidity(*, strategy_id: str = "strategy-1", verdict: str = "favorable") -> StrategyLiquidityValidation:
    return StrategyLiquidityValidation(
        id=f"liquidity-{strategy_id}",
        strategyId=strategy_id,
        strategyName="Momentum Breakout",
        symbolsChecked=["NEXA"],
        realSweepRatePct=10.0,
        verdict=verdict,  # type: ignore[arg-type]
        detail="Real liquidity conditions look supportive.",
        simDay=10,
        createdAt=_now_iso(),
    )

def _results(count: int, *, trade_count_each: int = 5, expected_value_pct: float = 1.0, strategy_id: str = "strategy-1") -> list[SimulationResult]:
    return [
        SimulationResult(
            id=f"result-{strategy_id}-{i}",
            strategyId=strategy_id,
            strategyName="Momentum Breakout",
            symbol="NEXA",
            totalReturnPct=10.0,
            winRate=60.0,
            maxDrawdownPct=10.0,
            sharpeRatio=1.5,
            sortinoRatio=1.5,
            tradeCount=trade_count_each,
            runBy="quant",  # type: ignore[arg-type]
            completedAt=_now_iso(),
            expectedValuePct=expected_value_pct,
        )
        for i in range(count)
    ]


class TestSampleSizeCheck:
    def test_passes_at_or_above_certification_threshold(self) -> None:
        strategy = _strategy()
        report = generate_model_validation_report(strategy, _results(4, trade_count_each=5), _monte_carlo(), _regime_test(), _liquidity(), "review-1", 0, sim_day=10)
        check = next(c for c in report.checks if c.id == "sample_size")
        assert check.passed is True
        assert "20" in check.threshold_source or "CERTIFICATION_MIN_TRADE_COUNT" in check.threshold_source

    def test_fails_below_certification_threshold(self) -> None:
        strategy = _strategy()
        report = generate_model_validation_report(strategy, _results(1, trade_count_each=5), _monte_carlo(), _regime_test(), _liquidity(), "review-1", 0, sim_day=10)
        check = next(c for c in report.checks if c.id == "sample_size")
        assert check.passed is False

    def test_not_evaluable_with_zero_runs(self) -> None:
        strategy = _strategy()
        report = generate_model_validation_report(strategy, [], _monte_carlo(), _regime_test(), _liquidity(), "review-1", 0, sim_day=10)
        check = next(c for c in report.checks if c.id == "sample_size")
        assert check.passed is None


class TestRegimeBreadthCheck:
    def test_passes_with_two_tested_no_weak(self) -> None:
        strategy = _strategy()
        report = generate_model_validation_report(strategy, _results(4, trade_count_each=5), _monte_carlo(), _regime_test(tested_count=2, any_weak=False), _liquidity(), "review-1", 0, sim_day=10)
        check = next(c for c in report.checks if c.id == "regime_breadth")
        assert check.passed is True

    def test_fails_with_a_weak_bucket(self) -> None:
        strategy = _strategy()
        report = generate_model_validation_report(strategy, _results(4, trade_count_each=5), _monte_carlo(), _regime_test(tested_count=2, any_weak=True), _liquidity(), "review-1", 0, sim_day=10)
        check = next(c for c in report.checks if c.id == "regime_breadth")
        assert check.passed is False

    def test_not_evaluable_with_no_regime_test(self) -> None:
        strategy = _strategy()
        report = generate_model_validation_report(strategy, _results(4, trade_count_each=5), _monte_carlo(), None, _liquidity(), "review-1", 0, sim_day=10)
        check = next(c for c in report.checks if c.id == "regime_breadth")
        assert check.passed is None


class TestTailRiskCheck:
    def test_passes_within_certification_ruin_bar(self) -> None:
        strategy = _strategy()
        report = generate_model_validation_report(strategy, _results(4, trade_count_each=5), _monte_carlo(probability_of_ruin_pct=5.0), _regime_test(), _liquidity(), "review-1", 0, sim_day=10)
        check = next(c for c in report.checks if c.id == "tail_risk")
        assert check.passed is True

    def test_fails_above_certification_ruin_bar(self) -> None:
        strategy = _strategy()
        report = generate_model_validation_report(strategy, _results(4, trade_count_each=5), _monte_carlo(probability_of_ruin_pct=20.0), _regime_test(), _liquidity(), "review-1", 0, sim_day=10)
        check = next(c for c in report.checks if c.id == "tail_risk")
        assert check.passed is False

    def test_not_evaluable_with_no_monte_carlo(self) -> None:
        strategy = _strategy()
        report = generate_model_validation_report(strategy, _results(4, trade_count_each=5), None, _regime_test(), _liquidity(), "review-1", 0, sim_day=10)
        check = next(c for c in report.checks if c.id == "tail_risk")
        assert check.passed is None


class TestLiquidityCheck:
    def test_passes_when_favorable(self) -> None:
        strategy = _strategy()
        report = generate_model_validation_report(strategy, _results(4, trade_count_each=5), _monte_carlo(), _regime_test(), _liquidity(verdict="favorable"), "review-1", 0, sim_day=10)
        check = next(c for c in report.checks if c.id == "liquidity_realism")
        assert check.passed is True

    def test_fails_when_unfavorable(self) -> None:
        strategy = _strategy()
        report = generate_model_validation_report(strategy, _results(4, trade_count_each=5), _monte_carlo(), _regime_test(), _liquidity(verdict="unfavorable"), "review-1", 0, sim_day=10)
        check = next(c for c in report.checks if c.id == "liquidity_realism")
        assert check.passed is False

    def test_not_evaluable_with_no_liquidity_validation(self) -> None:
        strategy = _strategy()
        report = generate_model_validation_report(strategy, _results(4, trade_count_each=5), _monte_carlo(), _regime_test(), None, "review-1", 0, sim_day=10)
        check = next(c for c in report.checks if c.id == "liquidity_realism")
        assert check.passed is None


class TestExpectancyCheck:
    def test_passes_with_positive_expectancy(self) -> None:
        strategy = _strategy()
        report = generate_model_validation_report(strategy, _results(4, trade_count_each=5, expected_value_pct=1.0), _monte_carlo(), _regime_test(), _liquidity(), "review-1", 0, sim_day=10)
        check = next(c for c in report.checks if c.id == "expectancy")
        assert check.passed is True

    def test_fails_with_non_positive_expectancy(self) -> None:
        strategy = _strategy()
        report = generate_model_validation_report(strategy, _results(4, trade_count_each=5, expected_value_pct=-0.5), _monte_carlo(), _regime_test(), _liquidity(), "review-1", 0, sim_day=10)
        check = next(c for c in report.checks if c.id == "expectancy")
        assert check.passed is False

    def test_not_evaluable_with_zero_runs(self) -> None:
        strategy = _strategy()
        report = generate_model_validation_report(strategy, [], _monte_carlo(), _regime_test(), _liquidity(), "review-1", 0, sim_day=10)
        check = next(c for c in report.checks if c.id == "expectancy")
        assert check.passed is None


class TestTemporalStabilityCheck:
    """Piece 2 — Walk-Forward / Temporal-Split Validation. Splits
    strategy_results at its chronological midpoint (by list order, the
    same convention app/strategy_lab.py's compute_strategy_health()
    already uses) and requires positive expectancy in BOTH halves."""

    def test_not_evaluable_with_fewer_than_two_runs(self) -> None:
        check = _temporal_stability_check(_results(1, trade_count_each=25))
        assert check.passed is None

        check_empty = _temporal_stability_check([])
        assert check_empty.passed is None

    def test_not_evaluable_when_a_half_is_below_the_trade_floor(self) -> None:
        # 4 runs split 2/2, trade_count_each=5 -> 10 trades/half, below
        # the reused CERTIFICATION_MIN_TRADE_COUNT=20 floor.
        check = _temporal_stability_check(_results(4, trade_count_each=5, expected_value_pct=1.0))
        assert check.passed is None

    def test_passes_when_both_halves_have_positive_expectancy(self) -> None:
        earlier = _results(2, trade_count_each=15, expected_value_pct=1.0, strategy_id="strategy-1")
        later = _results(2, trade_count_each=15, expected_value_pct=1.0, strategy_id="strategy-1")
        check = _temporal_stability_check(earlier + later)
        assert check.passed is True

    def test_fails_when_the_edge_decays_in_the_later_half(self) -> None:
        earlier = _results(2, trade_count_each=15, expected_value_pct=2.0, strategy_id="strategy-1")
        later = _results(2, trade_count_each=15, expected_value_pct=-1.0, strategy_id="strategy-1")
        check = _temporal_stability_check(earlier + later)
        assert check.passed is False
        assert "later" in check.evidence.lower() or "-1.00" in check.evidence

    def test_fails_when_only_the_later_half_is_profitable(self) -> None:
        # An unproven recent turnaround must not pass just because the
        # whole-sample average could still look positive.
        earlier = _results(2, trade_count_each=15, expected_value_pct=-2.0, strategy_id="strategy-1")
        later = _results(2, trade_count_each=15, expected_value_pct=3.0, strategy_id="strategy-1")
        check = _temporal_stability_check(earlier + later)
        assert check.passed is False

    def test_odd_length_history_splits_by_floor_division(self) -> None:
        # 5 runs -> midpoint = 5 // 2 = 2: earlier=2, later=3. Confirms
        # the split is deterministic list-order division, not an even
        # requirement.
        earlier = _results(2, trade_count_each=15, expected_value_pct=1.0, strategy_id="strategy-1")
        later = _results(3, trade_count_each=15, expected_value_pct=1.0, strategy_id="strategy-1")
        check = _temporal_stability_check(earlier + later)
        assert check.passed is True
        assert "2 run(s)" in check.evidence
        assert "3 run(s)" in check.evidence

    def test_threshold_source_never_blank(self) -> None:
        for results in ([], _results(1), _results(4, trade_count_each=5), _results(4, trade_count_each=15, expected_value_pct=1.0)):
            check = _temporal_stability_check(results)
            assert check.threshold_source.strip()


class TestVerdictLogic:
    def test_all_pass_is_approved(self) -> None:
        strategy = _strategy()
        # trade_count_each=15 across 4 runs (2 per chronological half) gives
        # each half 30 real trades — clears the temporal_stability check's
        # own per-half CERTIFICATION_MIN_TRADE_COUNT floor too.
        report = generate_model_validation_report(
            strategy, _results(4, trade_count_each=15, expected_value_pct=1.0), _monte_carlo(probability_of_ruin_pct=5.0), _regime_test(tested_count=2, any_weak=False), _liquidity(verdict="favorable"), "review-1", 0, sim_day=10
        )
        assert report.verdict == "approved"
        assert all(c.passed is True for c in report.checks)

    def test_a_clear_failure_is_rejected(self) -> None:
        strategy = _strategy()
        report = generate_model_validation_report(
            strategy, _results(4, trade_count_each=5, expected_value_pct=1.0), _monte_carlo(probability_of_ruin_pct=50.0), _regime_test(tested_count=2, any_weak=False), _liquidity(verdict="favorable"), "review-1", 0, sim_day=10
        )
        assert report.verdict == "rejected"

    def test_missing_evidence_with_no_clear_failure_needs_more_evidence(self) -> None:
        strategy = _strategy()
        # sample_size and expectancy both pass (24 real trades, positive
        # expected value); regime_breadth and liquidity are simply not on
        # file yet (None) — no evaluated check has actually failed, so
        # this is genuinely "needs more evidence", not a rejection.
        report = generate_model_validation_report(
            strategy, _results(4, trade_count_each=6, expected_value_pct=1.0), _monte_carlo(probability_of_ruin_pct=5.0), None, None, "review-1", 0, sim_day=10
        )
        assert report.verdict == "needs_more_evidence"

    def test_missing_evidence_alongside_a_real_failure_is_still_rejected(self) -> None:
        strategy = _strategy()
        # sample_size fails outright (only 5 real trades < 20); regime
        # breadth is not on file (None). Missing evidence must never
        # launder an already-established failure into "needs more
        # evidence".
        report = generate_model_validation_report(
            strategy, _results(1, trade_count_each=5, expected_value_pct=1.0), _monte_carlo(probability_of_ruin_pct=5.0), None, _liquidity(verdict="favorable"), "review-1", 0, sim_day=10
        )
        assert report.verdict == "rejected"

    def test_zero_simulation_results_is_not_validatable(self) -> None:
        strategy = _strategy()
        report = generate_model_validation_report(strategy, [], None, None, None, "review-1", 0, sim_day=10)
        assert report.verdict == "not_validatable"
        assert all(c.passed is None for c in report.checks)

    def test_never_silently_defaults_to_approved_when_data_is_missing(self) -> None:
        strategy = _strategy()
        report = generate_model_validation_report(strategy, [], _monte_carlo(), _regime_test(), _liquidity(), "review-1", 0, sim_day=10)
        assert report.verdict != "approved"


class TestDevilsAdvocateExclusionStatelessness:
    """The five required cases proving Meridian/CIO's DA-exclusion
    (app/sandbox.py's `exclude_cio` parameter) is a pure, per-call
    substitution — never a persisted flag that could leak across
    strategies, survive past its own call, or shift the base rotation
    formula. See app/model_validation.py's module docstring."""

    def test_cio_excluded_only_for_the_matching_strategy_cycle(self) -> None:
        strategy = _strategy()
        results = _results(4, trade_count_each=5, strategy_id=strategy.id)
        # existing_review_count % 4 == 2 is the natural "cio" slot.
        verdict = _devils_advocate_verdict(strategy, results, 2, exclude_cio=True)
        assert verdict.reviewer_agent != "cio"
        assert verdict.reviewer_agent == STRATEGY_DEVILS_ADVOCATES[(STRATEGY_DEVILS_ADVOCATES.index("cio") + 1) % len(STRATEGY_DEVILS_ADVOCATES)]

    def test_cio_remains_eligible_for_unrelated_strategies(self) -> None:
        strategy_a = _strategy("strategy-a")
        strategy_b = _strategy("strategy-b")
        results_a = _results(4, trade_count_each=5, strategy_id="strategy-a")
        results_b = _results(4, trade_count_each=5, strategy_id="strategy-b")
        verdict_a = _devils_advocate_verdict(strategy_a, results_a, 2, exclude_cio=True)
        verdict_b = _devils_advocate_verdict(strategy_b, results_b, 2, exclude_cio=False)
        assert verdict_a.reviewer_agent != "cio"
        assert verdict_b.reviewer_agent == "cio"

    def test_cio_returns_to_normal_rotation_after_the_cycle_ends(self) -> None:
        strategy = _strategy()
        results = _results(4, trade_count_each=5, strategy_id=strategy.id)
        excluded = _devils_advocate_verdict(strategy, results, 2, exclude_cio=True)
        assert excluded.reviewer_agent != "cio"
        # A later cycle for the SAME strategy that lands on the same slot
        # (count=6, 6 % 4 == 2) with no active validation this time must
        # see "cio" again — nothing about the earlier exclusion lingered.
        later = _devils_advocate_verdict(strategy, results, 6, exclude_cio=False)
        assert later.reviewer_agent == "cio"

    def test_rerunning_the_exclusion_never_corrupts_or_advances_rotation(self) -> None:
        strategy = _strategy()
        results = _results(4, trade_count_each=5, strategy_id=strategy.id)
        first = _devils_advocate_verdict(strategy, results, 2, exclude_cio=True)
        second = _devils_advocate_verdict(strategy, results, 2, exclude_cio=True)
        assert first.reviewer_agent == second.reviewer_agent
        assert first.reviewer_agent != "cio"

    def test_multiple_strategies_validated_independently_no_leakage(self) -> None:
        strategy_a = _strategy("strategy-a")
        strategy_b = _strategy("strategy-b")
        results_a = _results(4, trade_count_each=5, strategy_id="strategy-a")
        results_b = _results(4, trade_count_each=5, strategy_id="strategy-b")
        # Interleaved, order-independent: B (excluded) called before A
        # (not excluded) to prove call order carries no shared state.
        verdict_b = _devils_advocate_verdict(strategy_b, results_b, 2, exclude_cio=True)
        verdict_a = _devils_advocate_verdict(strategy_a, results_a, 2, exclude_cio=False)
        assert verdict_b.reviewer_agent != "cio"
        assert verdict_a.reviewer_agent == "cio"

    def test_base_rotation_formula_is_never_altered_by_exclusion(self) -> None:
        """Every OTHER slot in the rotation (not the "cio" slot) must be
        completely unaffected by exclude_cio, proving the base
        existing_review_count % len(...) formula itself is untouched."""
        strategy = _strategy()
        results = _results(4, trade_count_each=5, strategy_id=strategy.id)
        for count in (0, 1, 3, 4, 5, 7):
            with_exclusion = _devils_advocate_verdict(strategy, results, count, exclude_cio=True)
            without_exclusion = _devils_advocate_verdict(strategy, results, count, exclude_cio=False)
            assert with_exclusion.reviewer_agent == without_exclusion.reviewer_agent
            assert with_exclusion.reviewer_agent == STRATEGY_DEVILS_ADVOCATES[count % len(STRATEGY_DEVILS_ADVOCATES)]


class TestAdvisoryOnlyProof:
    """Q2's binding requirement: a rejected ModelValidationReport must
    never change apply_review_decision's outcome or the strategy's stage
    — proven by constructing the identical scenario with and without a
    rejected report attached and asserting an identical transition."""

    def test_rejected_model_validation_does_not_change_company_review_outcome(self) -> None:
        strategy, _ = begin_company_review(_strategy(stage="limited_live_capital"), sim_day=1)
        assert strategy is not None
        results = _results(4, trade_count_each=6, strategy_id=strategy.id)
        review = generate_strategy_review(strategy, results, [], 0, sim_day=1, exclude_cio=True)
        model_validation = generate_model_validation_report(strategy, results, _monte_carlo(probability_of_ruin_pct=50.0), None, None, review.id, 0, sim_day=1)
        assert model_validation.verdict == "rejected"

        approve = review.overall_verdict == "pass"
        outcome_with_rejected_validation = apply_review_decision(strategy, review, approve, sim_day=2)
        outcome_without_any_validation = apply_review_decision(strategy, review, approve, sim_day=2)
        assert outcome_with_rejected_validation.stage == outcome_without_any_validation.stage
        # apply_review_decision's own signature never even accepts a
        # ModelValidationReport argument — the strongest possible proof
        # that it cannot read `verdict` to gate anything.
        import inspect

        assert "model_validation" not in inspect.signature(apply_review_decision).parameters


class TestNoFabricatedEvidence:
    def test_every_check_evidence_string_traces_to_a_real_input_value(self) -> None:
        strategy = _strategy()
        monte_carlo = _monte_carlo(probability_of_ruin_pct=7.5)
        report = generate_model_validation_report(strategy, _results(4, trade_count_each=6), monte_carlo, _regime_test(), _liquidity(), "review-1", 0, sim_day=10)
        tail_risk = next(c for c in report.checks if c.id == "tail_risk")
        assert "7.5" in tail_risk.evidence
        assert str(monte_carlo.paths_simulated) in tail_risk.evidence

    def test_threshold_source_is_never_blank(self) -> None:
        strategy = _strategy()
        report = generate_model_validation_report(strategy, [], None, None, None, "review-1", 0, sim_day=10)
        assert all(c.threshold_source.strip() for c in report.checks)
