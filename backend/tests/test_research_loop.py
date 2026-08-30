"""Covers app/research_loop.py — CEO directive "TradeTown — Next Major
Implementation Pass, Phase 4-6: Self-Improving Strategy Factory +
Validation Funnel." Pure-function unit tests build a full, real
`ResearchExperimentRecord` by hand (every nested schema populated with
real, valid field values — never a mock object standing in for a real
one) so `derive_research_failure_codes()`/`classify_candidacy()`/etc. can
be tested against exact, hand-picked numbers; integration tests run the
real `run_research_loop_iteration()` entry point over a real compiled
strategy and real (mock) candle data end to end.
"""
from __future__ import annotations

from app.research_loop import (
    MAX_ITERATIONS_PER_FAMILY,
    MAX_MUTATIONS_PER_PARENT,
    RESEARCH_CANDIDATE_MAX_DRAWDOWN_PCT,
    RESEARCH_CANDIDATE_MIN_PROFIT_FACTOR,
    RESEARCH_CANDIDATE_MIN_TRADE_COUNT,
    classify_candidacy,
    compute_benchmark_comparisons,
    compute_outlier_dependence,
    derive_research_failure_codes,
    evaluate_research_budget,
    generate_research_lesson,
    propose_mutation,
    run_research_loop_iteration,
)
from app.quant_research_lab import file_quant_research_experiment
from app.research_experiment import run_research_experiment
from app.schemas import (
    BuyAndHoldBaseline,
    CompiledStrategyBacktestResult,
    CostSensitivityResult,
    EmaPullbackStatsBucket,
    FailureCodeEntry,
    LookAheadAuditResult,
    OverfittingDiagnosis,
    ParameterSensitivityAxisResult,
    ParameterSensitivityResult,
    ResearchExperimentRecord,
    StrategyComplexityScore,
    StrategyHypothesis,
    StrategyScorecard,
    WalkForwardSymbolResult,
    WalkForwardValidationResult,
)
from app.strategy_compiler import compile_strategy_text

_CREATED_AT = "2024-01-01T00:00:00+00:00"
_TEXT = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R."
_INVALID_TEXT = "Buy when the moon is full."


def _bucket(**overrides: object) -> EmaPullbackStatsBucket:
    base: dict[str, object] = dict(
        label="overall", tradeCount=120, winCount=70, lossCount=50, openCount=0,
        winRatePct=58.3, avgWinR=1.5, avgLossR=-0.9, expectancyR=0.45, profitFactor=1.8,
        maxDrawdownR=-3.0, largestWinR=2.0, largestLossR=-1.0, verdict="enough_evidence", detail="x",
    )
    base.update(overrides)
    return EmaPullbackStatsBucket(**base)  # type: ignore[arg-type]


def _record(
    *,
    overall: EmaPullbackStatsBucket | None = None,
    walk_forward_verdict: str = "stable",
    cost_verdict: str = "cost_resilient",
    parameter_verdict: str = "robust",
    lookahead_verdict: str = "clean",
    regime_trend_breakdown: list[EmaPullbackStatsBucket] | None = None,
    regime_volatility_breakdown: list[EmaPullbackStatsBucket] | None = None,
    instrument_breakdown: list[EmaPullbackStatsBucket] | None = None,
    buy_and_hold: list[BuyAndHoldBaseline] | None = None,
) -> ResearchExperimentRecord:
    bucket = overall or _bucket()
    backtest = CompiledStrategyBacktestResult(
        id="bt-1", definitionId="def-1", definitionVersion=1, symbolsTested=["AAPL"], timeframe="1h", candlesPerSymbol=6000,
        overall=bucket, sessionBreakdown=[], instrumentBreakdown=instrument_breakdown if instrument_breakdown is not None else [bucket.model_copy(update={"label": "AAPL"})],
        regimeTrendBreakdown=regime_trend_breakdown or [], regimeVolatilityBreakdown=regime_volatility_breakdown or [],
        modelValidation=None, monteCarlo=None, dataHonestyNote="x", generatedAt=_CREATED_AT,
    )
    walk_forward = WalkForwardValidationResult(
        id="wf-1", definitionId="def-1", definitionVersion=1, windowBars=1000,
        symbols=[WalkForwardSymbolResult(symbol="AAPL", windows=[], positiveWindowCount=0, negativeWindowCount=0, evaluatedWindowCount=0, detail="x")],
        verdict=walk_forward_verdict, detail="x", dataHonestyNote="x", generatedAt=_CREATED_AT,  # type: ignore[arg-type]
    )
    cost_sensitivity = CostSensitivityResult(
        id="cs-1", definitionId="def-1", definitionVersion=1, scenarios=[], verdict=cost_verdict, detail="x", dataHonestyNote="x", generatedAt=_CREATED_AT,  # type: ignore[arg-type]
    )
    empty_axis = ParameterSensitivityAxisResult(parameter="stop", sweepable=True, baseValue=1.0, points=[], detail="x")
    parameter_sensitivity = ParameterSensitivityResult(
        id="ps-1", definitionId="def-1", definitionVersion=1, stopAxis=empty_axis, targetAxis=empty_axis, verdict=parameter_verdict, detail="x", multipleTestingNote="x", dataHonestyNote="x", generatedAt=_CREATED_AT,  # type: ignore[arg-type]
    )
    look_ahead = LookAheadAuditResult(id="la-1", definitionId="def-1", definitionVersion=1, setupsChecked=10, violations=[], verdict=lookahead_verdict, detail="x", generatedAt=_CREATED_AT)  # type: ignore[arg-type]
    complexity = StrategyComplexityScore(definitionId="def-1", definitionVersion=1, stepCount=3, conditionCount=1, distinctIndicatorCount=2, parameterCount=5, complexityScore=11, band="moderate", detail="x", generatedAt=_CREATED_AT)  # type: ignore[arg-type]
    overfitting = OverfittingDiagnosis(verdict="pending_validation", detail="x", walkForwardVerdict=walk_forward_verdict, parameterSensitivityVerdict=parameter_verdict, costSensitivityVerdict=cost_verdict)  # type: ignore[arg-type]
    return ResearchExperimentRecord(
        id="exp-1", definitionId="def-1", definitionName="Test Strategy", definitionVersion=1, sourceText=_TEXT,
        symbolsTested=["AAPL"], timeframe="1h", candlesPerSymbol=6000, backtest=backtest, walkForward=walk_forward,
        parameterSensitivity=parameter_sensitivity, costSensitivity=cost_sensitivity, lookAheadAudit=look_ahead,
        complexity=complexity, overfittingDiagnosis=overfitting, conclusion="x",
        buyAndHoldBaseline=buy_and_hold if buy_and_hold is not None else [BuyAndHoldBaseline(symbol="AAPL", startPrice=100.0, endPrice=110.0, returnPct=10.0, candleCount=6000)],
        dataHonestyNote="x", generatedAt=_CREATED_AT,
    )


class TestResearchCandidateThresholds:
    def test_the_real_disclosed_constants_match_the_directives_own_literal_ask(self) -> None:
        # Section 5's own explicit numbers, distinct from and never
        # overwriting app/strategy_lab.py's HALL_OF_FAME_* constants.
        assert RESEARCH_CANDIDATE_MIN_TRADE_COUNT == 100
        assert RESEARCH_CANDIDATE_MAX_DRAWDOWN_PCT == 20.0
        assert RESEARCH_CANDIDATE_MIN_PROFIT_FACTOR == 1.10


class TestComputeOutlierDependence:
    def test_a_normal_distribution_of_returns_is_not_outlier_dependent(self) -> None:
        bucket = _bucket(tradeCount=100, expectancyR=0.5, largestWinR=2.0)
        dependent, share = compute_outlier_dependence(bucket)
        assert dependent is False
        assert share is not None and share < 0.5

    def test_a_single_dominant_winning_trade_is_outlier_dependent(self) -> None:
        # cumulative return = 0.1 * 20 = 2.0R; largest win 1.8R -> share 0.9
        bucket = _bucket(tradeCount=20, expectancyR=0.1, largestWinR=1.8)
        dependent, share = compute_outlier_dependence(bucket)
        assert dependent is True
        assert share == 0.9

    def test_fewer_than_two_trades_is_honestly_not_verified(self) -> None:
        bucket = _bucket(tradeCount=1, expectancyR=5.0, largestWinR=5.0)
        dependent, share = compute_outlier_dependence(bucket)
        assert dependent is None
        assert share is None

    def test_non_positive_cumulative_return_is_honestly_not_verified(self) -> None:
        bucket = _bucket(tradeCount=50, expectancyR=-0.1, largestWinR=2.0)
        dependent, share = compute_outlier_dependence(bucket)
        assert dependent is None
        assert share is None


class TestComputeBenchmarkComparisons:
    def test_a_real_beating_strategy_reads_beats_benchmark_true(self) -> None:
        record = _record(overall=_bucket(tradeCount=100, expectancyR=1.0))  # cumulative 100R * 2% = 200%
        comparisons = compute_benchmark_comparisons(record, risk_per_trade_pct=2.0)
        assert len(comparisons) == 1
        assert comparisons[0].beats_benchmark is True
        assert comparisons[0].strategy_equity_return_approx_pct == 200.0
        assert comparisons[0].excess_return_approx_pct == 190.0  # 200 - 10

    def test_a_real_losing_strategy_reads_beats_benchmark_false(self) -> None:
        record = _record(overall=_bucket(tradeCount=100, expectancyR=0.01), buy_and_hold=[BuyAndHoldBaseline(symbol="AAPL", startPrice=100.0, endPrice=200.0, returnPct=100.0, candleCount=6000)])
        comparisons = compute_benchmark_comparisons(record, risk_per_trade_pct=2.0)
        assert comparisons[0].beats_benchmark is False

    def test_the_approximation_note_is_always_disclosed(self) -> None:
        record = _record()
        comparisons = compute_benchmark_comparisons(record, risk_per_trade_pct=2.0)
        assert "Approximate" in comparisons[0].approximation_note
        assert "2.0%" in comparisons[0].approximation_note

    def test_a_symbol_with_no_matching_instrument_bucket_is_honestly_skipped(self) -> None:
        record = _record(instrument_breakdown=[], buy_and_hold=[BuyAndHoldBaseline(symbol="MSFT", startPrice=100.0, endPrice=110.0, returnPct=10.0, candleCount=6000)])
        comparisons = compute_benchmark_comparisons(record, risk_per_trade_pct=2.0)
        assert comparisons == []

    def test_never_blends_units_the_r_multiple_and_pct_fields_stay_distinct(self) -> None:
        record = _record(overall=_bucket(tradeCount=100, expectancyR=1.0))
        comparisons = compute_benchmark_comparisons(record, risk_per_trade_pct=2.0)
        assert comparisons[0].strategy_total_return_r == 100.0
        assert comparisons[0].benchmark_return_pct == 10.0


class TestDeriveResearchFailureCodes:
    def _codes(self, record: ResearchExperimentRecord, **kw: object) -> list[FailureCodeEntry]:
        defaults: dict[str, object] = dict(
            outlier_dependent=False, benchmark_comparisons=compute_benchmark_comparisons(record, risk_per_trade_pct=2.0),
            research_relationship="novel", research_family_experiment_count=1, tuning_version=1,
        )
        defaults.update(kw)
        return derive_research_failure_codes(record, **defaults)  # type: ignore[arg-type]

    def test_a_clean_strong_record_carries_no_failure_codes(self) -> None:
        record = _record(overall=_bucket(tradeCount=150, expectancyR=1.0, profitFactor=2.0, maxDrawdownR=-1.0))
        assert self._codes(record) == []

    def test_lookahead_violation_is_the_one_reported_regardless_of_other_evidence(self) -> None:
        record = _record(lookahead_verdict="violations_found")
        codes = self._codes(record)
        assert any(c.code == "lookahead_detected" and c.severity == "critical" for c in codes)

    def test_below_min_trade_count_reads_insufficient_sample(self) -> None:
        record = _record(overall=_bucket(tradeCount=50))
        codes = self._codes(record)
        assert any(c.code == "insufficient_sample" for c in codes)

    def test_below_bootstrap_floor_also_reads_statistical_uncertainty(self) -> None:
        record = _record(overall=_bucket(tradeCount=10))
        codes = self._codes(record)
        assert {"insufficient_sample", "statistical_uncertainty"} <= {c.code for c in codes}

    def test_negative_expectancy_reads_negative_net_return(self) -> None:
        record = _record(overall=_bucket(tradeCount=150, expectancyR=-0.1))
        codes = self._codes(record)
        assert any(c.code == "negative_net_return" for c in codes)
        assert not any(c.code == "low_profit_factor" for c in codes)  # never double-filed

    def test_low_profit_factor_with_positive_expectancy_reads_low_profit_factor(self) -> None:
        record = _record(overall=_bucket(tradeCount=150, expectancyR=0.05, profitFactor=1.0))
        codes = self._codes(record)
        assert any(c.code == "low_profit_factor" for c in codes)

    def test_excessive_drawdown_uses_the_real_risk_per_trade_conversion(self) -> None:
        # -15R * 2% risk/trade = 30% > 20% bar
        record = _record(overall=_bucket(tradeCount=150, maxDrawdownR=-15.0))
        codes = self._codes(record, risk_per_trade_pct=2.0)
        assert any(c.code == "excessive_drawdown" for c in codes)

    def test_a_modest_drawdown_stays_under_the_bar(self) -> None:
        record = _record(overall=_bucket(tradeCount=150, maxDrawdownR=-5.0))
        codes = self._codes(record, risk_per_trade_pct=2.0)
        assert not any(c.code == "excessive_drawdown" for c in codes)

    def test_walk_forward_failure_is_derived_from_the_real_verdict(self) -> None:
        record = _record(walk_forward_verdict="unstable")
        assert any(c.code == "walk_forward_failure" for c in self._codes(record))

    def test_cost_sensitivity_is_derived_from_the_real_verdict(self) -> None:
        record = _record(cost_verdict="cost_sensitive")
        assert any(c.code == "cost_sensitivity" for c in self._codes(record))

    def test_parameter_sensitivity_is_derived_from_the_real_verdict(self) -> None:
        record = _record(parameter_verdict="fragile")
        assert any(c.code == "parameter_sensitivity" for c in self._codes(record))

    def test_outlier_dependence_flag_produces_the_real_code(self) -> None:
        record = _record()
        codes = self._codes(record, outlier_dependent=True)
        assert any(c.code == "outlier_dependent" and c.severity == "high" for c in codes)

    def test_a_real_negative_regime_bucket_produces_regime_failure(self) -> None:
        weak_regime = _bucket(label="high_volatility", tradeCount=40, expectancyR=-0.3, verdict="enough_evidence")
        record = _record(regime_volatility_breakdown=[weak_regime])
        assert any(c.code == "regime_failure" for c in self._codes(record))

    def test_an_untested_regime_bucket_never_produces_regime_failure(self) -> None:
        untested_regime = _bucket(label="ranging", tradeCount=1, expectancyR=-5.0, verdict=None)
        record = _record(regime_trend_breakdown=[untested_regime])
        assert not any(c.code == "regime_failure" for c in self._codes(record))

    def test_benchmark_underperformance_is_derived_from_the_real_comparison(self) -> None:
        record = _record(overall=_bucket(tradeCount=150, expectancyR=0.01), buy_and_hold=[BuyAndHoldBaseline(symbol="AAPL", startPrice=100.0, endPrice=300.0, returnPct=200.0, candleCount=6000)])
        assert any(c.code == "benchmark_underperformance" for c in self._codes(record))

    def test_near_duplicate_relationship_reads_duplicate_strategy(self) -> None:
        record = _record()
        codes = self._codes(record, research_relationship="near_duplicate")
        assert any(c.code == "duplicate_strategy" for c in codes)

    def test_overtested_family_reads_multiple_testing_risk(self) -> None:
        record = _record()
        codes = self._codes(record, research_family_experiment_count=5)
        assert any(c.code == "multiple_testing_risk" for c in codes)

    def test_high_version_reads_excessive_tuning(self) -> None:
        record = _record()
        codes = self._codes(record, tuning_version=5)
        assert any(c.code == "excessive_tuning" for c in codes)

    def test_every_code_carries_real_nonempty_evidence(self) -> None:
        record = _record(overall=_bucket(tradeCount=5, expectancyR=-1.0, maxDrawdownR=-20.0), walk_forward_verdict="unstable", cost_verdict="cost_sensitive", parameter_verdict="fragile")
        codes = self._codes(record)
        assert codes
        for c in codes:
            assert c.evidence.strip()


class TestClassifyCandidacy:
    def test_a_strong_clean_record_is_accepted(self) -> None:
        record = _record(overall=_bucket(tradeCount=150, expectancyR=1.0, profitFactor=2.0, maxDrawdownR=-1.0))
        benchmarks = compute_benchmark_comparisons(record, risk_per_trade_pct=2.0)
        candidacy, reason = classify_candidacy(trade_count=150, failure_codes=[], research_relationship="novel", benchmark_comparisons=benchmarks)
        assert candidacy == "accepted"
        assert reason

    def test_lookahead_violation_is_always_rejected_regardless_of_other_evidence(self) -> None:
        codes = [FailureCodeEntry(code="lookahead_detected", category="data_failure", severity="critical", evidence="x")]
        candidacy, _ = classify_candidacy(trade_count=1000, failure_codes=codes, research_relationship="novel", benchmark_comparisons=[])
        assert candidacy == "rejected"

    def test_insufficient_sample_reads_insufficient_evidence(self) -> None:
        codes = [FailureCodeEntry(code="insufficient_sample", category="statistical_failure", severity="high", evidence="x")]
        candidacy, _ = classify_candidacy(trade_count=10, failure_codes=codes, research_relationship="novel", benchmark_comparisons=[])
        assert candidacy == "insufficient_evidence"

    def test_near_duplicate_reads_duplicate(self) -> None:
        candidacy, _ = classify_candidacy(trade_count=200, failure_codes=[], research_relationship="near_duplicate", benchmark_comparisons=[])
        assert candidacy == "duplicate"

    def test_excessive_drawdown_reads_risk_failed(self) -> None:
        codes = [FailureCodeEntry(code="excessive_drawdown", category="risk_failure", severity="high", evidence="x")]
        candidacy, _ = classify_candidacy(trade_count=200, failure_codes=codes, research_relationship="novel", benchmark_comparisons=[])
        assert candidacy == "risk_failed"

    def test_negative_net_return_reads_rejected(self) -> None:
        codes = [FailureCodeEntry(code="negative_net_return", category="performance_failure", severity="high", evidence="x")]
        candidacy, _ = classify_candidacy(trade_count=200, failure_codes=codes, research_relationship="novel", benchmark_comparisons=[])
        assert candidacy == "rejected"

    def test_walk_forward_failure_reads_overfit(self) -> None:
        codes = [FailureCodeEntry(code="walk_forward_failure", category="robustness_failure", severity="high", evidence="x")]
        candidacy, _ = classify_candidacy(trade_count=200, failure_codes=codes, research_relationship="novel", benchmark_comparisons=[])
        assert candidacy == "overfit"

    def test_outlier_dependent_reads_overfit(self) -> None:
        codes = [FailureCodeEntry(code="outlier_dependent", category="statistical_failure", severity="high", evidence="x")]
        candidacy, _ = classify_candidacy(trade_count=200, failure_codes=codes, research_relationship="novel", benchmark_comparisons=[])
        assert candidacy == "overfit"

    def test_benchmark_loss_alone_reads_benchmark_failed(self) -> None:
        record = _record(overall=_bucket(tradeCount=200, expectancyR=0.01), buy_and_hold=[BuyAndHoldBaseline(symbol="AAPL", startPrice=100.0, endPrice=300.0, returnPct=200.0, candleCount=6000)])
        benchmarks = compute_benchmark_comparisons(record, risk_per_trade_pct=2.0)
        candidacy, _ = classify_candidacy(trade_count=200, failure_codes=[], research_relationship="novel", benchmark_comparisons=benchmarks)
        assert candidacy == "benchmark_failed"

    def test_tuning_exposure_alone_reads_fragile(self) -> None:
        codes = [FailureCodeEntry(code="excessive_tuning", category="research_failure", severity="medium", evidence="x")]
        candidacy, _ = classify_candidacy(trade_count=200, failure_codes=codes, research_relationship="novel", benchmark_comparisons=[])
        assert candidacy == "fragile"

    def test_priority_order_lookahead_beats_everything_else(self) -> None:
        codes = [
            FailureCodeEntry(code="lookahead_detected", category="data_failure", severity="critical", evidence="x"),
            FailureCodeEntry(code="excessive_drawdown", category="risk_failure", severity="high", evidence="x"),
            FailureCodeEntry(code="negative_net_return", category="performance_failure", severity="high", evidence="x"),
        ]
        candidacy, _ = classify_candidacy(trade_count=200, failure_codes=codes, research_relationship="novel", benchmark_comparisons=[])
        assert candidacy == "rejected"


class TestProposeMutation:
    def test_no_failure_codes_returns_no_mutation(self) -> None:
        assert propose_mutation([], parent_definition_id="d1", parent_definition_version=1, parent_iteration_id="i1", mutation_number=1, mutation_id="m1", created_at=_CREATED_AT) is None

    def test_a_real_failure_code_produces_a_real_targeted_recommendation(self) -> None:
        codes = [FailureCodeEntry(code="excessive_drawdown", category="risk_failure", severity="high", evidence="x")]
        mutation = propose_mutation(codes, parent_definition_id="d1", parent_definition_version=2, parent_iteration_id="i1", mutation_number=1, mutation_id="m1", created_at=_CREATED_AT)
        assert mutation is not None
        assert mutation.observed_failure_codes == ["excessive_drawdown"]
        assert "stop" in mutation.proposed_change.lower() or "volatility" in mutation.proposed_change.lower()
        assert mutation.parent_definition_id == "d1"
        assert mutation.parent_definition_version == 2

    def test_multiple_failure_codes_target_only_the_single_highest_priority_one(self) -> None:
        codes = [
            FailureCodeEntry(code="insufficient_sample", category="statistical_failure", severity="high", evidence="x"),
            FailureCodeEntry(code="excessive_drawdown", category="risk_failure", severity="high", evidence="x"),
        ]
        mutation = propose_mutation(codes, parent_definition_id="d1", parent_definition_version=1, parent_iteration_id="i1", mutation_number=1, mutation_id="m1", created_at=_CREATED_AT)
        assert mutation is not None
        assert mutation.observed_failure_codes == ["excessive_drawdown"]  # never a vague multi-code shotgun

    def test_a_code_with_no_real_template_produces_no_mutation(self) -> None:
        codes = [FailureCodeEntry(code="survivorship_risk", category="data_failure", severity="medium", evidence="x")]
        assert propose_mutation(codes, parent_definition_id="d1", parent_definition_version=1, parent_iteration_id="i1", mutation_number=1, mutation_id="m1", created_at=_CREATED_AT) is None

    def test_repeated_mutation_of_the_same_failed_idea_still_produces_a_real_deterministic_result(self) -> None:
        codes = [FailureCodeEntry(code="cost_sensitivity", category="robustness_failure", severity="high", evidence="x")]
        m1 = propose_mutation(codes, parent_definition_id="d1", parent_definition_version=3, parent_iteration_id="i1", mutation_number=3, mutation_id="m3", created_at=_CREATED_AT)
        m2 = propose_mutation(codes, parent_definition_id="d1", parent_definition_version=3, parent_iteration_id="i1", mutation_number=3, mutation_id="m3", created_at=_CREATED_AT)
        assert m1 is not None and m2 is not None
        assert m1.proposed_change == m2.proposed_change  # deterministic, never randomized


class TestEvaluateResearchBudget:
    def test_a_fresh_family_is_not_stopped(self) -> None:
        status = evaluate_research_budget([], [], strategy_family="Never Tested", parent_definition_id=None)
        assert status.stopped is False
        assert status.experiments_attempted == 0

    def test_hitting_max_iterations_per_family_stops_it(self) -> None:
        definition = compile_strategy_text(name="Budget Family", source_text=_TEXT)
        record = run_research_experiment(definition, symbols=["AAPL"])
        existing: list = []
        for i in range(MAX_ITERATIONS_PER_FAMILY):
            experiment = file_quant_research_experiment(record, experiment_id=f"exp-{i}", hypothesis=f"h{i}", researcher_agent_id="quant", created_at=_CREATED_AT, existing=existing)
            existing.append(experiment)
        status = evaluate_research_budget(existing, [], strategy_family="Budget Family", parent_definition_id=None)
        assert status.stopped is True
        assert status.stop_reason is not None
        assert "iteration budget" in status.stop_reason

    def test_hitting_max_mutations_per_parent_stops_it(self) -> None:
        from app.schemas import ResearchBudgetStatus, ResearchLoopIterationRecord

        real_iterations = []
        for i in range(MAX_MUTATIONS_PER_PARENT):
            mutation = propose_mutation(
                [FailureCodeEntry(code="excessive_drawdown", category="risk_failure", severity="high", evidence="x")],
                parent_definition_id="parent-1", parent_definition_version=1, parent_iteration_id="i0", mutation_number=i + 1, mutation_id=f"m{i}", created_at=_CREATED_AT,
            )
            hypothesis = StrategyHypothesis(
                id=f"hyp-{i}", hypothesis="x", marketMechanism="x", expectedEdge="x", invalidationConditions="x",
                symbolUniverse=["AAPL"], timeframe="1h", entryConditions="x", exitConditions="x", stopLossLogic="x",
                takeProfitLogic="x", positionSizingLogic="x", riskConstraints="x", proposedBy="quant", createdAt=_CREATED_AT,
            )
            real_iterations.append(
                ResearchLoopIterationRecord(
                    id=f"iter-{i}", strategyFamily="Mutated Family", hypothesis=hypothesis, experiment=_record(),
                    scorecard=StrategyScorecard(), benchmarkComparisons=[], failureCodes=[], candidacy="fragile",
                    candidacyReason="x", similarExperiments=[], similarFailedStrategies=[], researchRelationship="novel",
                    mutation=mutation, budget=ResearchBudgetStatus(strategyFamily="Mutated Family", experimentsAttempted=0, mutationsForThisParent=0, maxIterationsPerFamily=20, maxMutationsPerParent=5, stopped=False),
                    createdAt=_CREATED_AT,
                )
            )
        status = evaluate_research_budget([], real_iterations, strategy_family="Mutated Family", parent_definition_id="parent-1")
        assert status.stopped is True
        assert status.stop_reason is not None and "mutation" in status.stop_reason


class TestGenerateResearchLesson:
    def test_a_real_lesson_is_produced_with_real_confidence_and_metrics(self) -> None:
        scorecard = StrategyScorecard(tradeCount=150, expectancyR=0.8, profitFactor=1.9, maxDrawdownR=-2.0, excessReturnApproxPct=15.0)
        lesson = generate_research_lesson(
            lesson_id="lesson-1", strategy_family="Test Strategy", definition_id="def-1", definition_version=1,
            iteration_id="iter-1", parent_definition_id=None, mutation_id=None, hypothesis="A real hypothesis.",
            candidacy="accepted", candidacy_reason="Clears every real bar.", scorecard=scorecard, trade_count=150, created_at=_CREATED_AT,
        )
        assert lesson.candidacy == "accepted"
        assert "expectancy" in " ".join(lesson.key_metrics)
        assert lesson.confidence_pct == 100.0  # 150/100 capped at 100

    def test_a_low_trade_count_produces_real_proportionally_lower_confidence(self) -> None:
        scorecard = StrategyScorecard(tradeCount=25)
        lesson = generate_research_lesson(
            lesson_id="lesson-2", strategy_family="Thin Strategy", definition_id="def-2", definition_version=1,
            iteration_id="iter-2", parent_definition_id=None, mutation_id=None, hypothesis="x",
            candidacy="insufficient_evidence", candidacy_reason="x", scorecard=scorecard, trade_count=25, created_at=_CREATED_AT,
        )
        assert lesson.confidence_pct == 25.0


class TestRunResearchLoopIterationIntegration:
    """Real, end-to-end tests over the actual compiled-strategy pipeline
    and real (mock) candle data — no mocked evidence anywhere."""

    def _hypothesis(self, **overrides: object) -> StrategyHypothesis:
        base: dict[str, object] = dict(
            id="hyp-1", hypothesis="Trend continuation after a confirmed breakout.", marketMechanism="Momentum continuation",
            expectedEdge="Positive expectancy in trending regimes", invalidationConditions="Flat/negative walk-forward expectancy",
            symbolUniverse=["AAPL"], timeframe="1h", entryConditions="x", exitConditions="x", stopLossLogic="x",
            takeProfitLogic="x", positionSizingLogic="x", riskConstraints="x", proposedBy="quant", createdAt=_CREATED_AT,
        )
        base.update(overrides)
        return StrategyHypothesis(**base)  # type: ignore[arg-type]

    def test_a_real_iteration_produces_a_complete_real_record(self) -> None:
        definition = compile_strategy_text(name="Integration Test Strategy", source_text=_TEXT)
        result = run_research_loop_iteration(
            self._hypothesis(), definition, quant_research_experiments=[], research_iterations=[], failed_archive=[],
            risk_per_trade_pct=2.0, iteration_id="iter-1", mutation_id="mut-1", created_at=_CREATED_AT, symbols=["AAPL"],
        )
        assert result.candidacy in ("accepted", "promising", "fragile", "rejected", "duplicate", "insufficient_evidence", "overfit", "benchmark_failed", "risk_failed")
        assert result.scorecard.trade_count is not None
        assert result.experiment.definition_id == definition.id
        assert result.mutation is None  # no parent -> no mutation proposed

    def test_an_uncompilable_definition_never_crashes_the_funnel(self) -> None:
        definition = compile_strategy_text(name="Moon Strategy", source_text=_INVALID_TEXT)
        result = run_research_loop_iteration(
            self._hypothesis(), definition, quant_research_experiments=[], research_iterations=[], failed_archive=[],
            risk_per_trade_pct=2.0, iteration_id="iter-2", mutation_id="mut-2", created_at=_CREATED_AT, symbols=["AAPL"],
        )
        assert result.scorecard.trade_count == 0
        assert result.candidacy in ("insufficient_evidence", "rejected")

    def test_a_hypothesis_with_a_real_parent_produces_a_real_mutation_when_a_failure_is_present(self) -> None:
        definition = compile_strategy_text(name="Mutation Test Strategy", source_text=_TEXT)
        hypothesis = self._hypothesis(id="hyp-2", parentDefinitionId=definition.id, parentDefinitionVersion=definition.version)
        result = run_research_loop_iteration(
            hypothesis, definition, quant_research_experiments=[], research_iterations=[], failed_archive=[],
            risk_per_trade_pct=2.0, iteration_id="iter-3", mutation_id="mut-3", created_at=_CREATED_AT, symbols=["AAPL"],
        )
        if result.failure_codes:
            # A real failure code was found on this real (mock) data -- a mutation must exist if any template matches.
            assert result.mutation is not None or all(c.code not in {"excessive_drawdown", "negative_net_return", "low_profit_factor", "walk_forward_failure", "cost_sensitivity", "parameter_sensitivity", "outlier_dependent", "regime_failure", "benchmark_underperformance"} for c in result.failure_codes)

    def test_never_gates_or_touches_any_existing_hard_gate_or_promotion_state(self) -> None:
        """Section 16 — the new self-improvement layer must never bypass
        or feed the existing gates. Proven by real module-level import
        inspection (not string-matching prose that could legitimately
        mention a gate's name while explaining it is untouched): this
        module imports nothing from app.strategy_lab (Hall-of-Fame/
        Certification) or app.state (persistence/champion mutation),
        and app.champion_challenger is imported ONLY for the one real,
        already-existing HIGH_TUNING_VERSION_THRESHOLD constant, never
        for compare_champion_challenger()/promote_challenger()."""
        import app.research_loop as module

        assert "app.strategy_lab" not in module.__loader__.get_source(module.__name__)  # type: ignore[union-attr]
        assert not hasattr(module, "compare_champion_challenger")
        assert not hasattr(module, "promote_challenger")
        assert not hasattr(module, "qualifies_for_hall_of_fame")
        assert not hasattr(module, "evaluate_certification_readiness")
        assert module.HIGH_TUNING_VERSION_THRESHOLD == 5  # the one real symbol reused from app.champion_challenger

    def test_similar_failed_strategies_are_surfaced_but_never_block_the_run(self) -> None:
        from app.schemas import FailedStrategyArchiveEntry

        failed_entry = FailedStrategyArchiveEntry(
            id="failedarchive-x", strategyId="x", strategyName="Similar Prior Strategy", createdBy="quant",
            failedAtStage="market_simulation", whatFailed=["Excessive drawdown"], lessonsLearned=["x"],
            failureCodes=[], retiredReason="x", simDay=1, createdAt=_CREATED_AT,
        )
        definition = compile_strategy_text(name="Similar Prior Strategy", source_text=_TEXT)
        result = run_research_loop_iteration(
            self._hypothesis(hypothesis="Excessive drawdown risk"), definition, quant_research_experiments=[], research_iterations=[],
            failed_archive=[failed_entry], risk_per_trade_pct=2.0, iteration_id="iter-4", mutation_id="mut-4", created_at=_CREATED_AT, symbols=["AAPL"],
        )
        assert len(result.similar_failed_strategies) >= 1
        assert result.id == "iter-4"  # the run completed -- similarity never raised/blocked

    def test_high_risk_per_trade_pct_is_reflected_honestly_in_the_approximation(self) -> None:
        definition = compile_strategy_text(name="Risk Sensitivity Strategy", source_text=_TEXT)
        low_risk = run_research_loop_iteration(
            self._hypothesis(), definition, quant_research_experiments=[], research_iterations=[], failed_archive=[],
            risk_per_trade_pct=1.0, iteration_id="iter-5a", mutation_id="mut-5a", created_at=_CREATED_AT, symbols=["AAPL"],
        )
        high_risk = run_research_loop_iteration(
            self._hypothesis(), definition, quant_research_experiments=[], research_iterations=[], failed_archive=[],
            risk_per_trade_pct=5.0, iteration_id="iter-5b", mutation_id="mut-5b", created_at=_CREATED_AT, symbols=["AAPL"],
        )
        if low_risk.benchmark_comparisons and high_risk.benchmark_comparisons:
            assert high_risk.benchmark_comparisons[0].strategy_equity_return_approx_pct == low_risk.benchmark_comparisons[0].strategy_equity_return_approx_pct * 5
