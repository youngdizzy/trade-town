"""Covers app/quant_research_lab.py — CEO directive "Professional Quant
Firm Phase," Feature 36: the Quant Research Lab's real outcome
classification, duplicate-detection heuristic, and persisted filing.
"""
from __future__ import annotations

import asyncio

from app.quant_research_lab import (
    NEAR_DUPLICATE_OVERLAP_THRESHOLD,
    OVERTESTED_FAMILY_THRESHOLD,
    classify_research_relationship,
    count_experiments_for_family,
    file_quant_research_experiment,
    find_similar_experiments,
)
from app.schemas import FailedStrategyArchiveEntry, QuantResearchExperimentSimilarity
from app.research_experiment import run_research_experiment
from app.state import GameState
from app.strategy_compiler import compile_strategy_text

_TEXT = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R."
_INVALID_TEXT = "Buy when the moon is full."


class TestFileQuantResearchExperiment:
    def test_an_uncompilable_definitions_experiment_is_filed_inconclusive_never_a_silent_pass(self) -> None:
        # An uncompilable definition never reaches real evidence at all (no model validation
        # verdict, every axis reads insufficient_data) — the honest read is "inconclusive"
        # (no real evidence either way), never "rejected" (which means real evidence disqualified
        # it) and never "promising" (which would be a silent pass with zero real backing).
        definition = compile_strategy_text(name="Moon Strategy", source_text=_INVALID_TEXT)
        record = run_research_experiment(definition, symbols=["AAPL"])
        experiment = file_quant_research_experiment(record, experiment_id="exp-1", hypothesis="The moon phase predicts price.", researcher_agent_id="quant", created_at="2024-01-01T00:00:00+00:00")
        assert experiment.outcome == "inconclusive"

    def test_the_experiment_always_preserves_the_real_hypothesis_and_researcher_verbatim(self) -> None:
        definition = compile_strategy_text(name="Moon Strategy 2", source_text=_INVALID_TEXT)
        record = run_research_experiment(definition, symbols=["AAPL"])
        experiment = file_quant_research_experiment(record, experiment_id="exp-2", hypothesis="A real, specific, testable hypothesis.", researcher_agent_id="nova", created_at="2024-01-01T00:00:00+00:00")
        assert experiment.hypothesis == "A real, specific, testable hypothesis."
        assert experiment.researcher_agent_id == "nova"
        assert experiment.record is record


class TestFindSimilarExperiments:
    def test_no_prior_experiments_reads_an_honest_empty_list(self) -> None:
        assert find_similar_experiments([], hypothesis="Any hypothesis.", definition_id="def-1", timeframe="1h") == []

    def test_the_same_definition_and_timeframe_is_always_flagged_regardless_of_hypothesis_wording(self) -> None:
        definition = compile_strategy_text(name="Shared Def", source_text=_TEXT)
        record = run_research_experiment(definition, symbols=["AAPL"])
        prior = file_quant_research_experiment(record, experiment_id="exp-1", hypothesis="Completely different wording here.", researcher_agent_id="quant", created_at="2024-01-01T00:00:00+00:00")
        matches = find_similar_experiments([prior], hypothesis="Nothing at all alike, unrelated words only.", definition_id=definition.id, timeframe="1h")
        assert len(matches) == 1
        assert matches[0].experiment_id == "exp-1"
        assert "Same compiled strategy" in matches[0].reason

    def test_overlapping_hypothesis_wording_is_flagged_even_on_a_different_definition(self) -> None:
        definition_a = compile_strategy_text(name="Def A", source_text=_TEXT)
        record_a = run_research_experiment(definition_a, symbols=["AAPL"])
        prior = file_quant_research_experiment(record_a, experiment_id="exp-1", hypothesis="The 50 EMA breakout works better during the London session", researcher_agent_id="quant", created_at="2024-01-01T00:00:00+00:00")
        matches = find_similar_experiments([prior], hypothesis="The 50 EMA breakout works better during the London session open", definition_id="a-totally-different-definition", timeframe="4h")
        assert len(matches) == 1
        assert "overlaps" in matches[0].reason

    def test_unrelated_prior_experiments_are_never_flagged(self) -> None:
        definition_a = compile_strategy_text(name="Def A", source_text=_TEXT)
        record_a = run_research_experiment(definition_a, symbols=["AAPL"])
        prior = file_quant_research_experiment(record_a, experiment_id="exp-1", hypothesis="Liquidity confirmation improves out-of-sample performance.", researcher_agent_id="quant", created_at="2024-01-01T00:00:00+00:00")
        matches = find_similar_experiments([prior], hypothesis="Fibonacci confirmation increases expectancy rather than just trade frequency.", definition_id="unrelated-definition", timeframe="15m")
        assert matches == []

    def test_a_matched_similarity_carries_the_matched_experiments_own_real_outcome(self) -> None:
        # CEO directive "Quant Research Factory / Strategy Discovery
        # Engine," Phase 14/16 — a CEO/agent about to file near-duplicate
        # research must see the prior experiment's own real outcome, not
        # just that a duplicate exists, so a known-rejected idea isn't
        # silently re-tested.
        definition = compile_strategy_text(name="Moon Strategy 3", source_text=_INVALID_TEXT)
        record = run_research_experiment(definition, symbols=["AAPL"])
        prior = file_quant_research_experiment(record, experiment_id="exp-1", hypothesis="The moon phase predicts price.", researcher_agent_id="quant", created_at="2024-01-01T00:00:00+00:00")
        matches = find_similar_experiments([prior], hypothesis="Completely unrelated wording.", definition_id=definition.id, timeframe="1h")
        assert len(matches) == 1
        assert matches[0].outcome == prior.outcome
        assert matches[0].outcome_reason == prior.outcome_reason

    def test_a_hypothesis_overlap_match_also_carries_the_matched_experiments_real_outcome(self) -> None:
        definition_a = compile_strategy_text(name="Def A", source_text=_TEXT)
        record_a = run_research_experiment(definition_a, symbols=["AAPL"])
        prior = file_quant_research_experiment(record_a, experiment_id="exp-1", hypothesis="The 50 EMA breakout works better during the London session", researcher_agent_id="quant", created_at="2024-01-01T00:00:00+00:00")
        matches = find_similar_experiments([prior], hypothesis="The 50 EMA breakout works better during the London session open", definition_id="a-totally-different-definition", timeframe="4h")
        assert len(matches) == 1
        assert matches[0].outcome == prior.outcome
        assert matches[0].outcome_reason == prior.outcome_reason


def _experiment_similarity(overlap: float, outcome: str) -> QuantResearchExperimentSimilarity:
    return QuantResearchExperimentSimilarity(experimentId="exp-1", hypothesis="x", overlapScore=overlap, reason="x", outcome=outcome, outcomeReason="x")  # type: ignore[arg-type]


def _failed_match(overlap: float = 0.5) -> object:
    from app.schemas import SimilarFailedStrategyMatch

    return SimilarFailedStrategyMatch(strategyArchiveId="a1", strategyName="x", overlapScore=overlap, reason="x", failedAtStage="market_simulation", failureCodes=[], evidence=[], simDay=1)


class TestClassifyResearchRelationship:
    """CEO directive "TradeTown — Research Engine Hardening +
    Self-Improvement Implementation Pass," Phase 3 — "classify the
    relationship: NOVEL / SIMILAR_SUCCESS / SIMILAR_FAILURE /
    NEAR_DUPLICATE / CONTRADICTORY_EVIDENCE." Purely informational —
    every test here only proves the real classification, never a
    reject/block path (this function has none)."""

    def test_no_matches_at_all_reads_novel(self) -> None:
        assert classify_research_relationship([], []) == "novel"

    def test_a_real_failed_archive_match_reads_similar_failure(self) -> None:
        assert classify_research_relationship([], [_failed_match()]) == "similar_failure"  # type: ignore[list-item]

    def test_a_rejected_prior_experiment_reads_similar_failure(self) -> None:
        matches = [_experiment_similarity(0.5, "rejected")]
        assert classify_research_relationship(matches, []) == "similar_failure"

    def test_a_promising_prior_experiment_reads_similar_success(self) -> None:
        matches = [_experiment_similarity(0.5, "promising")]
        assert classify_research_relationship(matches, []) == "similar_success"

    def test_an_inconclusive_prior_experiment_alone_reads_novel(self) -> None:
        matches = [_experiment_similarity(0.5, "inconclusive")]
        assert classify_research_relationship(matches, []) == "novel"

    def test_both_a_promising_match_and_a_real_failed_archive_match_reads_contradictory_evidence(self) -> None:
        matches = [_experiment_similarity(0.5, "promising")]
        assert classify_research_relationship(matches, [_failed_match()]) == "contradictory_evidence"  # type: ignore[list-item]

    def test_both_a_promising_and_a_rejected_prior_experiment_reads_contradictory_evidence(self) -> None:
        matches = [_experiment_similarity(0.5, "promising"), _experiment_similarity(0.5, "rejected")]
        assert classify_research_relationship(matches, []) == "contradictory_evidence"

    def test_an_overlap_at_or_above_the_near_duplicate_bar_always_wins_reads_near_duplicate(self) -> None:
        matches = [_experiment_similarity(NEAR_DUPLICATE_OVERLAP_THRESHOLD, "promising")]
        assert classify_research_relationship(matches, []) == "near_duplicate"

    def test_an_overlap_just_below_the_near_duplicate_bar_does_not_read_near_duplicate(self) -> None:
        matches = [_experiment_similarity(NEAR_DUPLICATE_OVERLAP_THRESHOLD - 0.01, "promising")]
        assert classify_research_relationship(matches, []) != "near_duplicate"

    def test_a_high_overlap_failed_archive_match_alone_reads_near_duplicate(self) -> None:
        assert classify_research_relationship([], [_failed_match(overlap=NEAR_DUPLICATE_OVERLAP_THRESHOLD)]) == "near_duplicate"  # type: ignore[list-item]


class TestSubmitQuantResearchExperimentState:
    def test_a_filed_experiment_is_really_persisted_and_searchable(self) -> None:
        state = GameState()
        definition = compile_strategy_text(name="Persisted Strategy", source_text=_TEXT)
        saved, result = asyncio.run(
            state.submit_quant_research_experiment(definition, hypothesis="The 50 EMA breakout works.", researcher_agent_id="quant", symbols=["AAPL"])
        )
        assert len(saved.quant_research_experiments) == 1
        assert saved.quant_research_experiments[0].id == result.experiment.id
        assert saved.quant_research_experiments[0].hypothesis == "The 50 EMA breakout works."

    def test_a_second_experiment_on_the_same_definition_surfaces_a_real_similar_match(self) -> None:
        state = GameState()
        definition = compile_strategy_text(name="Duplicate Check Strategy", source_text=_TEXT)
        asyncio.run(state.submit_quant_research_experiment(definition, hypothesis="First real hypothesis.", researcher_agent_id="quant", symbols=["AAPL"]))
        _, result = asyncio.run(state.submit_quant_research_experiment(definition, hypothesis="Second, differently-worded hypothesis.", researcher_agent_id="nova", symbols=["AAPL"]))
        assert len(result.similar_experiments) == 1

    def test_nothing_is_ever_deleted_even_when_the_evidence_is_bad(self) -> None:
        state = GameState()
        definition = compile_strategy_text(name="Moon Strategy 3", source_text=_INVALID_TEXT)
        saved, result = asyncio.run(state.submit_quant_research_experiment(definition, hypothesis="Moon phases predict returns.", researcher_agent_id="quant", symbols=["AAPL"]))
        assert result.experiment.outcome == "inconclusive"
        assert len(saved.quant_research_experiments) == 1  # an inconclusive experiment is still archived, never deleted

    def test_expected_mechanism_and_falsification_criteria_thread_through_end_to_end(self) -> None:
        # CEO directive "Quant Research Factory / Strategy Discovery
        # Engine," Phase 1.
        state = GameState()
        definition = compile_strategy_text(name="Disciplined Strategy", source_text=_TEXT)
        saved, result = asyncio.run(
            state.submit_quant_research_experiment(
                definition,
                hypothesis="The 50 EMA breakout works better during trending regimes.",
                researcher_agent_id="quant",
                symbols=["AAPL"],
                expected_mechanism="Momentum continuation after a confirmed trend-following breakout.",
                falsification_criteria="If expectancy is flat or negative across a real out-of-sample walk-forward window, this hypothesis is wrong.",
            )
        )
        assert result.experiment.expected_mechanism == "Momentum continuation after a confirmed trend-following breakout."
        assert result.experiment.falsification_criteria == "If expectancy is flat or negative across a real out-of-sample walk-forward window, this hypothesis is wrong."
        assert saved.quant_research_experiments[0].falsification_criteria == result.experiment.falsification_criteria

    def test_omitting_expected_mechanism_and_falsification_criteria_leaves_them_honestly_none(self) -> None:
        state = GameState()
        definition = compile_strategy_text(name="Undisciplined Strategy", source_text=_TEXT)
        _, result = asyncio.run(state.submit_quant_research_experiment(definition, hypothesis="No stated mechanism.", researcher_agent_id="quant", symbols=["AAPL"]))
        assert result.experiment.expected_mechanism is None
        assert result.experiment.falsification_criteria is None

    def test_a_new_hypothesis_with_no_failed_archive_reads_novel_and_an_empty_match_list(self) -> None:
        # CEO directive "TradeTown — Research Engine Hardening +
        # Self-Improvement Implementation Pass," Phase 3.
        state = GameState()
        definition = compile_strategy_text(name="No Prior History Strategy", source_text=_TEXT)
        _, result = asyncio.run(state.submit_quant_research_experiment(definition, hypothesis="A genuinely novel idea.", researcher_agent_id="quant", symbols=["AAPL"]))
        assert result.similar_failed_strategies == []
        assert result.research_relationship == "novel"

    def test_the_directives_own_test_scenario_a_similar_failed_strategy_is_surfaced_and_never_blocks_filing(self) -> None:
        state = GameState()
        failed_entry = FailedStrategyArchiveEntry(
            id="failedarchive-x", strategyId="x", strategyName="EMA Breakout Momentum", createdBy="quant",
            failedAtStage="market_simulation", whatFailed=["Excessive drawdown"], lessonsLearned=["x"],
            failureCodes=[], retiredReason="x", simDay=1, createdAt="2024-01-01T00:00:00+00:00",
        )
        state.data = state.data.model_copy(update={"strategy_failed_archive": [failed_entry]})
        definition = compile_strategy_text(name="EMA Breakout Momentum", source_text=_TEXT)
        saved, result = asyncio.run(
            state.submit_quant_research_experiment(definition, hypothesis="excessive drawdown risk", researcher_agent_id="quant", symbols=["AAPL"])
        )
        assert len(result.similar_failed_strategies) == 1
        assert result.similar_failed_strategies[0].strategy_name == "EMA Breakout Momentum"
        assert result.research_relationship == "similar_failure"
        # The directive's own explicit rule: never auto-reject. Filing still succeeds.
        assert len(saved.quant_research_experiments) == 1


class TestQuantResearchExperimentBackwardCompat:
    """CEO directive "Quant Research Factory / Strategy Discovery
    Engine," Phase 1 — `QuantResearchExperiment` lives inside the
    persisted `quant_research_experiments` LIST, so per app/
    persistence.py's own `_deep_merge_defaults` rule, a new field needs
    a real Pydantic default or an old save's existing experiments fail
    to validate on load."""

    def test_an_experiment_persisted_before_these_fields_existed_still_validates(self) -> None:
        from app.schemas import QuantResearchExperiment

        definition = compile_strategy_text(name="Old Save Strategy", source_text=_TEXT)
        record = run_research_experiment(definition, symbols=["AAPL"])
        old_save_shape = file_quant_research_experiment(
            record, experiment_id="exp-old", hypothesis="Old-format hypothesis.", researcher_agent_id="quant", created_at="2024-01-01T00:00:00+00:00"
        ).model_dump(by_alias=True)
        del old_save_shape["expectedMechanism"]
        del old_save_shape["falsificationCriteria"]
        restored = QuantResearchExperiment.model_validate(old_save_shape)
        assert restored.expected_mechanism is None
        assert restored.falsification_criteria is None

    def test_an_experiment_persisted_before_family_experiment_count_existed_still_validates(self) -> None:
        from app.schemas import QuantResearchExperiment

        definition = compile_strategy_text(name="Old Save Strategy 2", source_text=_TEXT)
        record = run_research_experiment(definition, symbols=["AAPL"])
        old_save_shape = file_quant_research_experiment(
            record, experiment_id="exp-old-2", hypothesis="Old-format hypothesis.", researcher_agent_id="quant", created_at="2024-01-01T00:00:00+00:00"
        ).model_dump(by_alias=True)
        del old_save_shape["familyExperimentCount"]
        restored = QuantResearchExperiment.model_validate(old_save_shape)
        assert restored.family_experiment_count is None

    def test_an_experiment_persisted_before_research_integrity_flag_existed_still_validates(self) -> None:
        from app.schemas import QuantResearchExperiment

        definition = compile_strategy_text(name="Old Save Strategy 4", source_text=_TEXT)
        record = run_research_experiment(definition, symbols=["AAPL"])
        old_save_shape = file_quant_research_experiment(
            record, experiment_id="exp-old-4", hypothesis="Old-format hypothesis.", researcher_agent_id="quant", created_at="2024-01-01T00:00:00+00:00"
        ).model_dump(by_alias=True)
        del old_save_shape["researchIntegrityFlag"]
        restored = QuantResearchExperiment.model_validate(old_save_shape)
        assert restored.research_integrity_flag is None

    def test_an_experiment_persisted_before_buy_and_hold_baseline_existed_still_validates(self) -> None:
        from app.schemas import QuantResearchExperiment

        definition = compile_strategy_text(name="Old Save Strategy 3", source_text=_TEXT)
        record = run_research_experiment(definition, symbols=["AAPL"])
        old_save_shape = file_quant_research_experiment(
            record, experiment_id="exp-old-3", hypothesis="Old-format hypothesis.", researcher_agent_id="quant", created_at="2024-01-01T00:00:00+00:00"
        ).model_dump(by_alias=True)
        del old_save_shape["record"]["buyAndHoldBaseline"]
        restored = QuantResearchExperiment.model_validate(old_save_shape)
        assert restored.record.buy_and_hold_baseline == []


class TestCountExperimentsForFamily:
    """CEO directive "Quant Research Factory / Strategy Discovery
    Engine," Phase 10 — a real multiple-testing/research-selection-bias
    signal, never a fabricated statistical correction."""

    def test_no_prior_experiments_reads_zero(self) -> None:
        assert count_experiments_for_family([], definition_name="Any Strategy") == 0

    def test_counts_only_experiments_sharing_the_real_definition_name(self) -> None:
        definition_a = compile_strategy_text(name="Family A", source_text=_TEXT)
        record_a = run_research_experiment(definition_a, symbols=["AAPL"])
        definition_b = compile_strategy_text(name="Family B", source_text=_TEXT)
        record_b = run_research_experiment(definition_b, symbols=["AAPL"])
        experiments = [
            file_quant_research_experiment(record_a, experiment_id="exp-1", hypothesis="h1", researcher_agent_id="quant", created_at="2024-01-01T00:00:00+00:00"),
            file_quant_research_experiment(record_a, experiment_id="exp-2", hypothesis="h2", researcher_agent_id="quant", created_at="2024-01-01T00:00:00+00:00"),
            file_quant_research_experiment(record_b, experiment_id="exp-3", hypothesis="h3", researcher_agent_id="quant", created_at="2024-01-01T00:00:00+00:00"),
        ]
        assert count_experiments_for_family(experiments, definition_name="Family A") == 2
        assert count_experiments_for_family(experiments, definition_name="Family B") == 1

    def test_a_never_tested_family_reads_zero_not_fabricated(self) -> None:
        definition_a = compile_strategy_text(name="Family A", source_text=_TEXT)
        record_a = run_research_experiment(definition_a, symbols=["AAPL"])
        experiments = [file_quant_research_experiment(record_a, experiment_id="exp-1", hypothesis="h1", researcher_agent_id="quant", created_at="2024-01-01T00:00:00+00:00")]
        assert count_experiments_for_family(experiments, definition_name="Never Tested Family") == 0


class TestFileQuantResearchExperimentFamilyCount:
    def test_no_existing_list_supplied_leaves_the_count_honestly_none(self) -> None:
        definition = compile_strategy_text(name="No Count Family", source_text=_TEXT)
        record = run_research_experiment(definition, symbols=["AAPL"])
        experiment = file_quant_research_experiment(record, experiment_id="exp-1", hypothesis="h1", researcher_agent_id="quant", created_at="2024-01-01T00:00:00+00:00")
        assert experiment.family_experiment_count is None

    def test_the_count_includes_the_experiment_being_filed_right_now(self) -> None:
        definition = compile_strategy_text(name="Counted Family", source_text=_TEXT)
        record = run_research_experiment(definition, symbols=["AAPL"])
        experiment = file_quant_research_experiment(record, experiment_id="exp-1", hypothesis="h1", researcher_agent_id="quant", created_at="2024-01-01T00:00:00+00:00", existing=[])
        assert experiment.family_experiment_count == 1

    def test_the_count_grows_across_real_repeated_filings_of_the_same_family(self) -> None:
        state = GameState()
        definition = compile_strategy_text(name="Repeated Family", source_text=_TEXT)
        _, first = asyncio.run(state.submit_quant_research_experiment(definition, hypothesis="first pass", researcher_agent_id="quant", symbols=["AAPL"]))
        _, second = asyncio.run(state.submit_quant_research_experiment(definition, hypothesis="second pass, differently worded", researcher_agent_id="nova", symbols=["AAPL"]))
        assert first.experiment.family_experiment_count == 1
        assert second.experiment.family_experiment_count == 2


class TestResearchIntegrityFlag:
    """CEO directive "TradeTown — 11/10 Strategy Factory + Ruthless
    Backtesting Engine," Section 12 (Multiple-Testing Penalty) — a real,
    disclosed flag derived from family_experiment_count, never a
    fabricated statistical correction."""

    def test_no_count_leaves_the_flag_honestly_none(self) -> None:
        definition = compile_strategy_text(name="No Flag Family", source_text=_TEXT)
        record = run_research_experiment(definition, symbols=["AAPL"])
        experiment = file_quant_research_experiment(record, experiment_id="exp-1", hypothesis="h1", researcher_agent_id="quant", created_at="2024-01-01T00:00:00+00:00")
        assert experiment.family_experiment_count is None
        assert experiment.research_integrity_flag is None

    def test_below_the_real_threshold_reads_normal(self) -> None:
        definition = compile_strategy_text(name="Normal Flag Family", source_text=_TEXT)
        record = run_research_experiment(definition, symbols=["AAPL"])
        experiment = file_quant_research_experiment(record, experiment_id="exp-1", hypothesis="h1", researcher_agent_id="quant", created_at="2024-01-01T00:00:00+00:00", existing=[])
        assert experiment.family_experiment_count == 1
        assert experiment.research_integrity_flag == "normal"

    def test_one_below_the_real_threshold_still_reads_normal(self) -> None:
        definition = compile_strategy_text(name="Just Under Family", source_text=_TEXT)
        record = run_research_experiment(definition, symbols=["AAPL"])
        existing = []
        experiment = None
        for i in range(OVERTESTED_FAMILY_THRESHOLD - 1):
            experiment = file_quant_research_experiment(record, experiment_id=f"exp-{i}", hypothesis=f"h{i}", researcher_agent_id="quant", created_at="2024-01-01T00:00:00+00:00", existing=existing)
            existing.append(experiment)
        assert experiment is not None
        assert experiment.family_experiment_count == OVERTESTED_FAMILY_THRESHOLD - 1
        assert experiment.research_integrity_flag == "normal"

    def test_at_the_real_threshold_reads_overtested(self) -> None:
        definition = compile_strategy_text(name="Overtested Flag Family", source_text=_TEXT)
        record = run_research_experiment(definition, symbols=["AAPL"])
        existing = []
        experiment = None
        for i in range(OVERTESTED_FAMILY_THRESHOLD):
            experiment = file_quant_research_experiment(record, experiment_id=f"exp-{i}", hypothesis=f"h{i}", researcher_agent_id="quant", created_at="2024-01-01T00:00:00+00:00", existing=existing)
            existing.append(experiment)
        assert experiment is not None
        assert experiment.family_experiment_count == OVERTESTED_FAMILY_THRESHOLD
        assert experiment.research_integrity_flag == "overtested"
