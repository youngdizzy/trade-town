"""Covers app/quant_research_lab.py — CEO directive "Professional Quant
Firm Phase," Feature 36: the Quant Research Lab's real outcome
classification, duplicate-detection heuristic, and persisted filing.
"""
from __future__ import annotations

import asyncio

from app.quant_research_lab import file_quant_research_experiment, find_similar_experiments
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
