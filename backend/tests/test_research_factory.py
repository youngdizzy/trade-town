"""Covers app/research_factory.py — CEO directive "TradeTown — Phase 7:
Autonomous Strategy Evolution Engine." Pure-function unit tests exercise
each bounded mutation operator directly against real, hand-built
`CompiledStrategyDefinition` structures; integration tests run the real
`run_research_factory_cycle()` entry point over real compiled strategies
and real (mock) candle data end to end — no mocked evidence anywhere.
"""
from __future__ import annotations

import inspect

from app.research_factory import (
    MAX_CHANDELIER_ATR_MULTIPLIER,
    MAX_CONSECUTIVE_CANDLES,
    MAX_GENERATIONS_PER_FACTORY_RUN,
    MAX_TARGET_R,
    MIN_TARGET_R,
    _add_confirmation_bar,
    _adjust_target,
    _infer_direction,
    _relax_threshold,
    _widen_stop,
    build_mutation_candidate,
    derive_lifecycle_stage,
    generate_next_hypothesis,
    run_research_factory_cycle,
    summarize_lesson_evidence,
)
from app.research_loop import MAX_ITERATIONS_PER_FAMILY, MAX_MUTATIONS_PER_PARENT
from app.quant_research_lab import file_quant_research_experiment
from app.research_experiment import run_research_experiment
from app.schemas import FailureCode, MutationRecord, ResearchLessonRecord, StrategyHypothesis
from app.strategy_compiler import compile_strategy_text

_CREATED_AT = "2024-01-01T00:00:00+00:00"
_EMA_TEXT = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R."
_SHORT_TEXT = "Sell when price closes below the 50 EMA, then enter when price closes below the previous swing low. Place the stop at the Chandelier Stop and target 2R."
_RSI_TEXT = "Buy when the RSI is above 70. Enter when price closes above the previous swing high. Place a 5% stop. Target 2R."
_REQUIREMENT_TEXT = (
    "Buy when price closes above the 50 EMA. It requires at least two bearish candles as the pullback. "
    "Enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R."
)
_INVALID_TEXT = "Buy when the moon is full."


def _hypothesis(**overrides: object) -> StrategyHypothesis:
    base: dict[str, object] = dict(
        id="hyp-seed", hypothesis="Trend continuation after a confirmed breakout.", marketMechanism="Momentum continuation",
        expectedEdge="Positive expectancy in trending regimes", invalidationConditions="Flat/negative walk-forward expectancy",
        symbolUniverse=["AAPL"], timeframe="1h", entryConditions="x", exitConditions="x", stopLossLogic="x",
        takeProfitLogic="x", positionSizingLogic="x", riskConstraints="x", proposedBy="quant", createdAt=_CREATED_AT,
    )
    base.update(overrides)
    return StrategyHypothesis(**base)  # type: ignore[arg-type]


class TestInferDirection:
    def test_long_ema_trigger(self) -> None:
        definition = compile_strategy_text(name="Long EMA", source_text=_EMA_TEXT)
        assert _infer_direction(definition) == "long"

    def test_short_ema_trigger(self) -> None:
        definition = compile_strategy_text(name="Short EMA", source_text=_SHORT_TEXT)
        assert _infer_direction(definition) == "short"

    def test_no_trigger_returns_none(self) -> None:
        definition = compile_strategy_text(name="Invalid", source_text=_INVALID_TEXT)
        assert _infer_direction(definition) is None


class TestWidenStop:
    def test_widens_explicit_chandelier_params(self) -> None:
        text = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Use a chandelier stop with a 22-period ATR and a 3.0x multiplier. Target 2R."
        definition = compile_strategy_text(name="Explicit Chandelier", source_text=text)
        assert definition.status == "compiled"
        mutated, changed, constraints = _widen_stop(definition.source_text, definition)
        assert mutated is not None
        assert "3.5x" in mutated
        assert changed["chandelierAtrMultiplier"] == "3x -> 3.5x"
        assert "Bounded" in constraints
        child = compile_strategy_text(name="Explicit Chandelier", source_text=mutated, previous_version=definition.version)
        assert child.status == "compiled"
        assert child.stop is not None and child.stop.atr_multiplier == 3.5

    def test_widens_bare_chandelier_by_appending_explicit_params(self) -> None:
        definition = compile_strategy_text(name="Bare Chandelier", source_text=_EMA_TEXT)
        mutated, changed, _constraints = _widen_stop(definition.source_text, definition)
        assert mutated is not None
        assert "chandelierAtrMultiplier" in changed
        child = compile_strategy_text(name="Bare Chandelier", source_text=mutated, previous_version=definition.version)
        assert child.status == "compiled"
        assert child.stop is not None and child.stop.atr_multiplier == 3.5

    def test_caps_at_max_multiplier(self) -> None:
        text = f"Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Use a chandelier stop with a 22-period ATR and a {MAX_CHANDELIER_ATR_MULTIPLIER:g}x multiplier. Target 2R."
        definition = compile_strategy_text(name="Capped Chandelier", source_text=text)
        mutated, changed, constraints = _widen_stop(definition.source_text, definition)
        assert mutated is None
        assert changed == {}
        assert "bound" in constraints

    def test_widens_fixed_percent_stop(self) -> None:
        text = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place a 3% stop. Target 2R."
        definition = compile_strategy_text(name="Percent Stop", source_text=text)
        mutated, changed, _constraints = _widen_stop(definition.source_text, definition)
        assert mutated is not None
        assert "4%" in mutated
        assert changed["fixedStopPercent"] == "3% -> 4%"

    def test_swing_level_stop_has_no_operator(self) -> None:
        text = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Stop at the swing low. Target 2R."
        definition = compile_strategy_text(name="Swing Stop", source_text=text)
        assert definition.stop is not None and definition.stop.method == "swing_level"
        mutated, changed, _constraints = _widen_stop(definition.source_text, definition)
        assert mutated is None
        assert changed == {}

    def test_no_stop_returns_none(self) -> None:
        definition = compile_strategy_text(name="No Stop", source_text=_INVALID_TEXT)
        mutated, changed, _constraints = _widen_stop(definition.source_text, definition)
        assert mutated is None
        assert changed == {}


class TestAdjustTarget:
    def test_widens_r_multiple_target(self) -> None:
        definition = compile_strategy_text(name="Widen Target", source_text=_EMA_TEXT)
        mutated, changed, _c = _adjust_target(definition.source_text, definition, delta=0.5)
        assert mutated is not None
        assert changed["targetRMultiple"] == "2R -> 2.5R"
        child = compile_strategy_text(name="Widen Target", source_text=mutated, previous_version=definition.version)
        assert child.status == "compiled" and child.target is not None and child.target.value == 2.5

    def test_narrows_r_multiple_target(self) -> None:
        definition = compile_strategy_text(name="Narrow Target", source_text=_EMA_TEXT)
        mutated, changed, _c = _adjust_target(definition.source_text, definition, delta=-0.5)
        assert mutated is not None
        assert changed["targetRMultiple"] == "2R -> 1.5R"

    def test_caps_at_max_target(self) -> None:
        text = f"Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target {MAX_TARGET_R:g}R."
        definition = compile_strategy_text(name="Max Target", source_text=text)
        mutated, changed, constraints = _adjust_target(definition.source_text, definition, delta=0.5)
        assert mutated is None and changed == {} and "bound" in constraints

    def test_floors_at_min_target(self) -> None:
        text = f"Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target {MIN_TARGET_R:g}R."
        definition = compile_strategy_text(name="Min Target", source_text=text)
        mutated, changed, _c = _adjust_target(definition.source_text, definition, delta=-0.5)
        assert mutated is None and changed == {}

    def test_ratio_target_phrasing_also_adjustable(self) -> None:
        text = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop. Target a 2:1 reward."
        definition = compile_strategy_text(name="Ratio Target", source_text=text)
        assert definition.target is not None and definition.target.value == 2.0
        mutated, changed, _c = _adjust_target(definition.source_text, definition, delta=0.5)
        assert mutated is not None
        assert "2.5:1 reward" in mutated

    def test_fixed_percent_target_has_no_operator(self) -> None:
        text = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target a 4% target."
        definition = compile_strategy_text(name="Percent Target", source_text=text)
        assert definition.target is not None and definition.target.method == "fixed_percent"
        mutated, changed, _c = _adjust_target(definition.source_text, definition, delta=0.5)
        assert mutated is None and changed == {}

    def test_no_target_returns_none(self) -> None:
        definition = compile_strategy_text(name="No Target", source_text=_INVALID_TEXT)
        mutated, changed, _c = _adjust_target(definition.source_text, definition, delta=0.5)
        assert mutated is None and changed == {}


class TestAddConfirmationBar:
    def test_increments_existing_requirement(self) -> None:
        definition = compile_strategy_text(name="Existing Requirement", source_text=_REQUIREMENT_TEXT)
        req_step = next(s for s in definition.sequence if s.step_type == "requirement")
        assert req_step.min_consecutive_bars == 2
        mutated, changed, _c = _add_confirmation_bar(definition.source_text, definition)
        assert mutated is not None
        assert changed["minConsecutiveBars"] == "2 -> 3"
        child = compile_strategy_text(name="Existing Requirement", source_text=mutated, previous_version=definition.version)
        child_req = next(s for s in child.sequence if s.step_type == "requirement")
        assert child_req.min_consecutive_bars == 3

    def test_caps_at_max_consecutive_candles(self) -> None:
        text = f"Buy when price closes above the 50 EMA. It requires at least {MAX_CONSECUTIVE_CANDLES} bearish candles as the pullback. Enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R."
        definition = compile_strategy_text(name="Max Requirement", source_text=text)
        mutated, changed, _c = _add_confirmation_bar(definition.source_text, definition)
        assert mutated is None and changed == {}

    def test_appends_new_requirement_for_long_strategy(self) -> None:
        definition = compile_strategy_text(name="No Requirement Long", source_text=_EMA_TEXT)
        mutated, changed, _c = _add_confirmation_bar(definition.source_text, definition)
        assert mutated is not None
        assert "bearish" in mutated  # long -> bearish pullback, matching this codebase's own seed-strategy convention
        assert changed["minConsecutiveBars"] == "none -> 2 bearish"

    def test_appends_new_requirement_for_short_strategy(self) -> None:
        definition = compile_strategy_text(name="No Requirement Short", source_text=_SHORT_TEXT)
        mutated, changed, _c = _add_confirmation_bar(definition.source_text, definition)
        assert mutated is not None
        assert "bullish" in mutated

    def test_no_direction_and_no_requirement_returns_none(self) -> None:
        definition = compile_strategy_text(name="No Direction", source_text=_INVALID_TEXT)
        mutated, changed, _c = _add_confirmation_bar(definition.source_text, definition)
        assert mutated is None and changed == {}


class TestRelaxThreshold:
    def test_relaxes_rsi_threshold_toward_neutral(self) -> None:
        definition = compile_strategy_text(name="RSI Strategy", source_text=_RSI_TEXT)
        mutated, changed, _c = _relax_threshold(definition.source_text, definition)
        assert mutated is not None
        assert changed["rsiThreshold"] == "70 -> 65"
        child = compile_strategy_text(name="RSI Strategy", source_text=mutated, previous_version=definition.version)
        assert child.status == "compiled"

    def test_relaxes_trend_score_threshold(self) -> None:
        text = "Buy when the multi-horizon trend score is above 2. Enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R."
        definition = compile_strategy_text(name="Trend Score Strategy", source_text=text)
        mutated, changed, _c = _relax_threshold(definition.source_text, definition)
        assert mutated is not None
        assert changed["trendScoreThreshold"] == "2 -> 1.5"

    def test_caps_at_neutral_floor(self) -> None:
        text = "Buy when the RSI is above 55. Enter when price closes above the previous swing high. Place a 5% stop. Target 2R."
        definition = compile_strategy_text(name="Near Neutral RSI", source_text=text)
        mutated, changed, constraints = _relax_threshold(definition.source_text, definition)
        assert mutated is None and changed == {}
        assert "floor" in constraints

    def test_ema_trigger_has_no_threshold_to_relax(self) -> None:
        definition = compile_strategy_text(name="EMA Strategy", source_text=_EMA_TEXT)
        mutated, changed, constraints = _relax_threshold(definition.source_text, definition)
        assert mutated is None and changed == {}
        assert "no swept numeric threshold" in constraints


class TestBuildMutationCandidate:
    def _mutation_record(self, code: FailureCode, *, parent_version: int = 1) -> MutationRecord:
        return MutationRecord(
            id="mut-1", parentDefinitionId="def-1", parentDefinitionVersion=parent_version, parentIterationId="iter-1",
            mutationNumber=1, observedFailureCodes=[code], proposedChange="x", reason="x", expectedEffect="x",
            validationRequirements="x", createdAt=_CREATED_AT,
        )

    def test_excessive_drawdown_produces_widen_stop(self) -> None:
        definition = compile_strategy_text(name="DD Strategy", source_text=_EMA_TEXT)
        mutation = self._mutation_record("excessive_drawdown")
        candidate = build_mutation_candidate(mutation, definition, mutation_candidate_id="mc-1", created_at=_CREATED_AT)
        assert candidate.mutation_type == "widen_stop"
        assert candidate.mutated_source_text is not None
        assert candidate.parent_definition_id == "def-1"

    def test_regime_failure_has_no_bounded_operator(self) -> None:
        definition = compile_strategy_text(name="Regime Strategy", source_text=_EMA_TEXT)
        mutation = self._mutation_record("regime_failure")
        candidate = build_mutation_candidate(mutation, definition, mutation_candidate_id="mc-2", created_at=_CREATED_AT)
        assert candidate.mutated_source_text is None
        assert "compiler" in candidate.constraints or "combined regime" in candidate.constraints

    def test_negative_net_return_has_no_bounded_operator(self) -> None:
        definition = compile_strategy_text(name="Neg Return Strategy", source_text=_EMA_TEXT)
        mutation = self._mutation_record("negative_net_return")
        candidate = build_mutation_candidate(mutation, definition, mutation_candidate_id="mc-3", created_at=_CREATED_AT)
        assert candidate.mutated_source_text is None

    def test_empty_failure_codes_produces_unsupported_type(self) -> None:
        definition = compile_strategy_text(name="Empty Codes", source_text=_EMA_TEXT)
        mutation = MutationRecord(
            id="mut-empty", parentDefinitionId="def-1", parentDefinitionVersion=1, parentIterationId="iter-1",
            mutationNumber=1, observedFailureCodes=[], proposedChange="x", reason="x", expectedEffect="x",
            validationRequirements="x", createdAt=_CREATED_AT,
        )
        candidate = build_mutation_candidate(mutation, definition, mutation_candidate_id="mc-4", created_at=_CREATED_AT)
        assert candidate.mutation_type == "unsupported"
        assert candidate.mutated_source_text is None

    def test_reproducibility_seed_is_deterministic(self) -> None:
        definition = compile_strategy_text(name="Seed Strategy", source_text=_EMA_TEXT)
        mutation = self._mutation_record("excessive_drawdown")
        c1 = build_mutation_candidate(mutation, definition, mutation_candidate_id="mc-5", created_at=_CREATED_AT)
        c2 = build_mutation_candidate(mutation, definition, mutation_candidate_id="mc-6", created_at="2099-01-01T00:00:00+00:00")
        assert c1.reproducibility_seed == c2.reproducibility_seed  # depends only on definition id/version/mutation type/number, never on wall-clock time


class TestGenerateNextHypothesis:
    def test_increments_generation_and_sets_lineage(self) -> None:
        parent_hyp = _hypothesis(generation=0)
        definition = compile_strategy_text(name="Lineage Strategy", source_text=_EMA_TEXT)
        mutation_record = TestBuildMutationCandidate()._mutation_record("excessive_drawdown")
        mutation_candidate = build_mutation_candidate(mutation_record, definition, mutation_candidate_id="mc-7", created_at=_CREATED_AT)
        next_hyp = generate_next_hypothesis(
            parent_hyp, definition, mutation_candidate, lesson_ids_used=["lesson-1"], failure_codes_addressed=["excessive_drawdown"],
            hypothesis_id="hyp-gen1", lineage_id="lineage-1", created_at=_CREATED_AT,
        )
        assert next_hyp.generation == 1
        assert next_hyp.lineage_id == "lineage-1"
        assert next_hyp.parent_definition_id == definition.id
        assert next_hyp.parent_definition_version == definition.version
        assert next_hyp.lessons_used == ["lesson-1"]
        assert next_hyp.failure_codes_addressed == ["excessive_drawdown"]
        assert next_hyp.mutation_operator_used == mutation_candidate.mutation_type
        assert next_hyp.source_evidence_ids == [mutation_candidate.id, "lesson-1"]


class TestDeriveLifecycleStage:
    def test_compile_rejected_when_not_compiled(self) -> None:
        assert derive_lifecycle_stage(compile_status="invalid", candidacy=None) == "compile_rejected"
        assert derive_lifecycle_stage(compile_status="ambiguous", candidacy=None) == "compile_rejected"

    def test_backtested_when_compiled_but_no_candidacy_yet(self) -> None:
        assert derive_lifecycle_stage(compile_status="compiled", candidacy=None) == "backtested"

    def test_survivor_when_accepted(self) -> None:
        assert derive_lifecycle_stage(compile_status="compiled", candidacy="accepted") == "survivor"

    def test_candidate_when_promising(self) -> None:
        assert derive_lifecycle_stage(compile_status="compiled", candidacy="promising") == "candidate"

    def test_rejected_for_every_other_candidacy(self) -> None:
        for candidacy in ("rejected", "duplicate", "insufficient_evidence", "overfit", "benchmark_failed", "risk_failed", "fragile"):
            assert derive_lifecycle_stage(compile_status="compiled", candidacy=candidacy) == "rejected"  # type: ignore[arg-type]


class TestSummarizeLessonEvidence:
    def _lesson(self, lesson_id: str, family: str, candidacy: str) -> ResearchLessonRecord:
        return ResearchLessonRecord(
            id=lesson_id, strategyFamily=family, definitionId="def-1", definitionVersion=1, iterationId="iter-1",
            hypothesis="x", candidacy=candidacy, reason="x", keyMetrics=[], confidencePct=50.0,  # type: ignore[arg-type]
            lesson="x", createdAt=_CREATED_AT,
        )

    def test_supporting_and_contradicting_counts(self) -> None:
        lessons = [
            self._lesson("l1", "Family A", "accepted"),
            self._lesson("l2", "Family A", "promising"),
            self._lesson("l3", "Family A", "rejected"),
            self._lesson("l4", "Family B", "rejected"),
        ]
        summaries = {s.lesson_id: s for s in summarize_lesson_evidence(lessons)}
        assert summaries["l1"].supporting_iterations == 1  # l2 (also favorable)
        assert summaries["l1"].contradicting_iterations == 1  # l3 (unfavorable)
        assert summaries["l4"].supporting_iterations == 0  # no other Family B lessons
        assert summaries["l4"].contradicting_iterations == 0

    def test_empty_list_returns_empty(self) -> None:
        assert summarize_lesson_evidence([]) == []


class TestRunResearchFactoryCycleIntegration:
    """Real, end-to-end tests over the actual compiled-strategy pipeline
    and real (mock) candle data — no mocked evidence anywhere."""

    def test_multi_generation_run_actually_evolves_the_strategy(self) -> None:
        definition = compile_strategy_text(name="Factory Test Strategy A", source_text=_EMA_TEXT)
        registry = {definition.id: [definition]}
        run, updated_registry, iterations, lessons = run_research_factory_cycle(
            _hypothesis(), definition, compiled_strategy_registry=registry, quant_research_experiments=[],
            research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
            run_id="factory-run-a", created_at=_CREATED_AT, symbols=["AAPL"],
        )
        assert run.candidates_generated >= 1
        assert run.seed_definition_id == definition.id
        assert run.lineage_id == "factory-run-a"
        assert len(iterations) == run.candidates_backtested
        assert len(lessons) == run.candidates_backtested
        # Real, ordered lineage: each candidate after the first names the
        # one immediately before it as its own real parent.
        for i in range(1, len(run.candidates)):
            assert run.candidates[i].parent_candidate_id == run.candidates[i - 1].id
        # Real, increasing definition versions as each real mutation compiles.
        versions = [c.definition_version for c in run.candidates]
        assert versions == sorted(versions)
        assert len(set(versions)) == len(versions)  # every generation gets its own real version, never reused
        # The real updated registry actually contains every real compiled version.
        assert len(updated_registry[definition.id]) == max(versions)

    def test_compile_rejected_seed_stops_immediately_with_no_backtest(self) -> None:
        bad_definition = compile_strategy_text(name="Factory Test Bad Seed", source_text=_INVALID_TEXT)
        assert bad_definition.status != "compiled"
        registry: dict[str, list[object]] = {}
        run, _registry, iterations, lessons = run_research_factory_cycle(  # type: ignore[var-annotated]
            _hypothesis(), bad_definition, compiled_strategy_registry=registry, quant_research_experiments=[],  # type: ignore[arg-type]
            research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
            run_id="factory-run-bad-seed", created_at=_CREATED_AT, symbols=["AAPL"],
        )
        assert len(run.candidates) == 1
        assert run.candidates[0].lifecycle_stage == "compile_rejected"
        assert run.candidates[0].iteration is None
        assert iterations == []
        assert lessons == []
        assert "did not compile" in run.stop_reason
        assert run.candidates_backtested == 0

    def test_max_total_backtests_caps_the_run(self) -> None:
        definition = compile_strategy_text(name="Factory Test Strategy B", source_text=_EMA_TEXT)
        registry = {definition.id: [definition]}
        run, _r, _i, _l = run_research_factory_cycle(
            _hypothesis(), definition, compiled_strategy_registry=registry, quant_research_experiments=[],
            research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
            run_id="factory-run-b", created_at=_CREATED_AT, symbols=["AAPL"], max_total_backtests=1,
        )
        assert run.candidates_backtested <= 1
        if run.candidates_backtested == 1 and not run.survivor_candidate_ids:
            assert "backtest cap" in run.stop_reason or "SURVIVOR" in run.stop_reason

    def test_max_generations_caps_the_run(self) -> None:
        definition = compile_strategy_text(name="Factory Test Strategy C", source_text=_EMA_TEXT)
        registry = {definition.id: [definition]}
        run, _r, _i, _l = run_research_factory_cycle(
            _hypothesis(), definition, compiled_strategy_registry=registry, quant_research_experiments=[],
            research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
            run_id="factory-run-c", created_at=_CREATED_AT, symbols=["AAPL"], max_generations=1,
        )
        assert run.generations_completed <= 2  # generation 0 and, if it mutated, one attempt at generation 1

    def test_budget_exhaustion_stops_the_run(self) -> None:
        definition = compile_strategy_text(name="Budget Family", source_text=_EMA_TEXT)
        record = run_research_experiment(definition, symbols=["AAPL"])
        existing_experiments = [
            file_quant_research_experiment(record, experiment_id=f"exp-{i}", hypothesis="x", researcher_agent_id="quant", created_at=_CREATED_AT, existing=[])
            for i in range(MAX_ITERATIONS_PER_FAMILY)
        ]
        registry = {definition.id: [definition]}
        run, _r, iterations, _l = run_research_factory_cycle(
            _hypothesis(), definition, compiled_strategy_registry=registry, quant_research_experiments=existing_experiments,
            research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
            run_id="factory-run-budget", created_at=_CREATED_AT, symbols=["AAPL"],
        )
        assert run.candidates_backtested == 0
        assert "budget" in run.stop_reason.lower()
        assert iterations == []

    def test_mutations_for_parent_budget_also_enforced(self) -> None:
        """MAX_MUTATIONS_PER_PARENT is a real, existing app/research_loop.py
        constant this module reuses, never a second independent limit."""
        definition = compile_strategy_text(name="Factory Test Strategy D", source_text=_EMA_TEXT)
        registry = {definition.id: [definition]}
        run, _r, _i, _l = run_research_factory_cycle(
            _hypothesis(), definition, compiled_strategy_registry=registry, quant_research_experiments=[],
            research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
            run_id="factory-run-d", created_at=_CREATED_AT, symbols=["AAPL"], max_generations=MAX_MUTATIONS_PER_PARENT + 5,
        )
        assert run.generations_completed <= MAX_MUTATIONS_PER_PARENT + 2

    def test_determinism_same_inputs_produce_the_same_lineage(self) -> None:
        definition = compile_strategy_text(name="Deterministic Strategy", source_text=_EMA_TEXT)
        registry = {definition.id: [definition]}
        run1, _r1, _i1, _l1 = run_research_factory_cycle(
            _hypothesis(), definition, compiled_strategy_registry=dict(registry), quant_research_experiments=[],
            research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
            run_id="factory-run-det", created_at=_CREATED_AT, symbols=["AAPL"],
        )
        run2, _r2, _i2, _l2 = run_research_factory_cycle(
            _hypothesis(), definition, compiled_strategy_registry=dict(registry), quant_research_experiments=[],
            research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
            run_id="factory-run-det", created_at=_CREATED_AT, symbols=["AAPL"],
        )
        assert [c.definition_version for c in run1.candidates] == [c.definition_version for c in run2.candidates]
        assert [c.lifecycle_stage for c in run1.candidates] == [c.lifecycle_stage for c in run2.candidates]
        assert run1.stop_reason == run2.stop_reason
        assert [c.mutation_candidate.reproducibility_seed if c.mutation_candidate else None for c in run1.candidates] == [
            c.mutation_candidate.reproducibility_seed if c.mutation_candidate else None for c in run2.candidates
        ]

    def test_broken_lineage_missing_parent_definition_id_does_not_crash(self) -> None:
        """A hypothesis with an explicit parent_definition_id pointing at
        a definition that isn't the one actually being tested is
        malformed caller input — the real funnel still runs to
        completion rather than crashing (matching this codebase's own
        defensive posture toward untrusted/malformed input elsewhere)."""
        definition = compile_strategy_text(name="Broken Lineage Strategy", source_text=_EMA_TEXT)
        hypothesis = _hypothesis(parentDefinitionId="nonexistent-definition", parentDefinitionVersion=99)
        registry = {definition.id: [definition]}
        run, _r, _i, _l = run_research_factory_cycle(
            hypothesis, definition, compiled_strategy_registry=registry, quant_research_experiments=[],
            research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
            run_id="factory-run-broken", created_at=_CREATED_AT, symbols=["AAPL"],
        )
        assert run.candidates_generated >= 1  # real completion, no crash

    def test_run_never_produces_more_generations_than_the_configured_cap(self) -> None:
        definition = compile_strategy_text(name="Factory Test Strategy E", source_text=_EMA_TEXT)
        registry = {definition.id: [definition]}
        run, _r, _i, _l = run_research_factory_cycle(
            _hypothesis(), definition, compiled_strategy_registry=registry, quant_research_experiments=[],
            research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
            run_id="factory-run-e", created_at=_CREATED_AT, symbols=["AAPL"], max_generations=MAX_GENERATIONS_PER_FACTORY_RUN,
        )
        assert max((c.generation for c in run.candidates), default=0) <= MAX_GENERATIONS_PER_FACTORY_RUN

    def test_never_touches_champion_challenger_promotion_or_comparison(self) -> None:
        """Section 10 — proven by real module-level import inspection
        (never string-matching prose that could legitimately mention a
        gate's name while explaining it is untouched)."""
        import app.research_factory as module

        source = inspect.getsource(module)
        assert not hasattr(module, "compare_champion_challenger")
        assert not hasattr(module, "promote_challenger")
        assert not hasattr(module, "qualifies_for_hall_of_fame")
        assert not hasattr(module, "evaluate_certification_readiness")
        # get_current_champion is the one real, read-only symbol this
        # module is allowed to import from app.champion_challenger.
        assert "from app.champion_challenger import ChampionRecord, get_current_champion" in source

    def test_candidates_carry_real_benchmark_and_failure_evidence(self) -> None:
        definition = compile_strategy_text(name="Factory Test Strategy F", source_text=_EMA_TEXT)
        registry = {definition.id: [definition]}
        run, _r, _i, _l = run_research_factory_cycle(
            _hypothesis(), definition, compiled_strategy_registry=registry, quant_research_experiments=[],
            research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
            run_id="factory-run-f", created_at=_CREATED_AT, symbols=["AAPL"],
        )
        backtested = [c for c in run.candidates if c.iteration is not None]
        assert backtested
        for candidate in backtested:
            assert candidate.iteration is not None
            assert candidate.iteration.scorecard.trade_count is not None
            assert candidate.iteration.research_relationship in ("novel", "similar_success", "similar_failure", "near_duplicate", "contradictory_evidence")
