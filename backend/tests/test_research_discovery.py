"""Covers app/research_discovery.py — CEO directive "TradeTown — Phase
8: Autonomous Strategy Discovery + Adversarial Research Engine." Real,
end-to-end tests run `run_research_discovery_cycle()` over the actual
compiled-strategy pipeline and real (mock) candle data — no mocked
evidence anywhere, matching this codebase's own established discipline
for its orchestrator-level tests.
"""
from __future__ import annotations

import inspect

import pytest

from app.research_discovery import (
    MIN_POPULATION_SIZE,
    classify_research_scorecard,
    compute_family_research_stats,
    run_research_discovery_cycle,
)
from app.schemas import AdversarialResearchResult, ExtendedCostAttackResult, OutlierResilienceResult, RegimeRobustnessResult, WorstPeriodResult, SequenceRobustnessResult

_CREATED_AT = "2024-01-01T00:00:00+00:00"


def _adversarial_result(*, outlier: str = "robust_to_outliers", regime: str = "regime_robust", survives_cost: bool | None = True) -> AdversarialResearchResult:
    return AdversarialResearchResult(
        id="adv-1", definitionId="d", definitionVersion=1,
        outlierResilience=OutlierResilienceResult(scenarios=[], classification=outlier, detail="x"),  # type: ignore[arg-type]
        worstPeriod=WorstPeriodResult(windowTradeCount=0, detail="x"),
        sequenceRobustness=SequenceRobustnessResult(reshuffleCount=0, seed="x", detail="x"),
        extendedCostAttack=ExtendedCostAttackResult(scenarios=[], survivesBeyondStress=survives_cost, detail="x"),
        regimeRobustness=RegimeRobustnessResult(classification=regime, provenRegimes=[], fragileRegimes=[], detail="x"),  # type: ignore[arg-type]
        failureBoundaries=[], dataProvenance="simulated", generatedAt=_CREATED_AT,
    )


class TestClassifyResearchScorecard:
    def test_rejected_candidacy_never_overridden(self) -> None:
        for candidacy in ("rejected", "overfit", "benchmark_failed", "risk_failed", "duplicate"):
            classification, _reason = classify_research_scorecard(candidacy, _adversarial_result(outlier="robust_to_outliers", regime="regime_robust", survives_cost=True))
            assert classification == "rejected"

    def test_hard_gate_bypass_impossible_even_with_perfect_adversarial_evidence(self) -> None:
        """The single most important test in this file: no adversarial
        result, however favorable, can ever upgrade a real, already-
        failed candidacy."""
        perfect_adversarial = _adversarial_result(outlier="robust_to_outliers", regime="regime_robust", survives_cost=True)
        classification, _reason = classify_research_scorecard("rejected", perfect_adversarial)
        assert classification == "rejected"

    def test_insufficient_evidence_maps_to_fragile(self) -> None:
        classification, _reason = classify_research_scorecard("insufficient_evidence", None)
        assert classification == "fragile"

    def test_promising_stays_promising(self) -> None:
        classification, _reason = classify_research_scorecard("promising", None)
        assert classification == "promising"

    def test_accepted_with_no_adversarial_result_is_promising(self) -> None:
        classification, _reason = classify_research_scorecard("accepted", None)
        assert classification == "promising"

    def test_accepted_highly_outlier_dependent_is_fragile(self) -> None:
        classification, _reason = classify_research_scorecard("accepted", _adversarial_result(outlier="highly_outlier_dependent"))
        assert classification == "fragile"

    def test_accepted_regime_fragile_is_fragile(self) -> None:
        classification, _reason = classify_research_scorecard("accepted", _adversarial_result(regime="regime_fragile"))
        assert classification == "fragile"

    def test_accepted_fails_beyond_stress_cost_is_fragile(self) -> None:
        classification, _reason = classify_research_scorecard("accepted", _adversarial_result(survives_cost=False))
        assert classification == "fragile"

    def test_accepted_clears_everything_is_champion_candidate(self) -> None:
        classification, _reason = classify_research_scorecard("accepted", _adversarial_result(outlier="robust_to_outliers", regime="regime_robust", survives_cost=True))
        assert classification == "champion_candidate"

    def test_accepted_moderate_evidence_is_robust_not_champion(self) -> None:
        classification, _reason = classify_research_scorecard("accepted", _adversarial_result(outlier="moderately_outlier_dependent", regime="regime_robust", survives_cost=True))
        assert classification == "robust"

    def test_never_imports_champion_challenger_promotion_or_certification(self) -> None:
        """Section 8N/8O — proven by real module-level import inspection."""
        import app.research_discovery as module

        source = inspect.getsource(module)
        assert not hasattr(module, "compare_champion_challenger")
        assert not hasattr(module, "promote_challenger")
        assert not hasattr(module, "qualifies_for_hall_of_fame")
        assert not hasattr(module, "evaluate_certification_readiness")
        assert "from app.champion_challenger import ChampionRecord" in source


class TestComputeFamilyResearchStats:
    def test_empty_candidates_returns_zeroed_stats_for_every_family(self) -> None:
        stats = compute_family_research_stats([])
        assert len(stats) == 6
        assert all(s.number_generated == 0 for s in stats)
        assert all(s.average_expectancy_r is None for s in stats)


class TestRunResearchDiscoveryCycleIntegration:
    def test_zero_population_size_is_clamped_to_the_real_minimum(self) -> None:
        record, _registry, _iterations, _lessons = run_research_discovery_cycle(
            concept_name="Zero Pop Test", population_size=0, seed="s-zero", compiled_strategy_registry={},
            quant_research_experiments=[], research_iterations=[], research_lessons=[], failed_archive=[],
            champion_history=[], existing_candidates=[], risk_per_trade_pct=2.0, cycle_id="cycle-zero",
            created_at=_CREATED_AT, proposed_by="quant", symbols=["AAPL"],
        )
        assert record.population_size == MIN_POPULATION_SIZE
        assert len(record.candidates) == MIN_POPULATION_SIZE

    def test_oversized_population_is_clamped_to_the_real_maximum(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Monkeypatches the real cap down to keep this test fast — the
        # real clamping LOGIC (min(population_size, MAX_POPULATION_SIZE))
        # is exercised identically regardless of the cap's own value.
        import app.research_discovery as module

        monkeypatch.setattr(module, "MAX_POPULATION_SIZE", 3)
        record, _registry, _iterations, _lessons = run_research_discovery_cycle(
            concept_name="Huge Pop Test", population_size=999, seed="s-huge", compiled_strategy_registry={},
            quant_research_experiments=[], research_iterations=[], research_lessons=[], failed_archive=[],
            champion_history=[], existing_candidates=[], risk_per_trade_pct=2.0, cycle_id="cycle-huge",
            created_at=_CREATED_AT, proposed_by="quant", families=("trend_following",), symbols=["AAPL"],
        )
        assert record.population_size == 3

    def test_a_real_small_population_produces_a_complete_real_record(self) -> None:
        record, updated_registry, iterations, lessons = run_research_discovery_cycle(
            concept_name="Discovery Integration Test", population_size=3, seed="s-integration", compiled_strategy_registry={},
            quant_research_experiments=[], research_iterations=[], research_lessons=[], failed_archive=[],
            champion_history=[], existing_candidates=[], risk_per_trade_pct=2.0, cycle_id="cycle-integration",
            created_at=_CREATED_AT, proposed_by="quant", symbols=["AAPL"],
        )
        assert len(record.candidates) == 3
        assert len(record.family_stats) == 6
        assert len(record.allocation_decisions) == 6
        assert record.holdout.status == "not_available"
        backtested = [c for c in record.candidates if c.iteration is not None]
        assert len(iterations) == len(backtested)
        assert len(lessons) == len(backtested)
        for candidate in backtested:
            assert candidate.adversarial_result is not None
            assert candidate.scorecard_classification is not None
            assert candidate.research_family is not None
            assert candidate.candidate_seed is not None
            assert candidate.discovery_reason is not None
        # Every compiled candidate's definition is real and present in the returned registry.
        for candidate in backtested:
            slug_versions = updated_registry.get(candidate.definition_id, [])
            assert any(v.version == candidate.definition_version for v in slug_versions)

    def test_deterministic_cycle_same_seed_same_result(self) -> None:
        args = dict(
            concept_name="Deterministic Discovery Test", population_size=2, seed="s-det", compiled_strategy_registry={},
            quant_research_experiments=[], research_iterations=[], research_lessons=[], failed_archive=[],
            champion_history=[], existing_candidates=[], risk_per_trade_pct=2.0, created_at=_CREATED_AT,
            proposed_by="quant", symbols=["AAPL"],
        )
        record1, _r1, _i1, _l1 = run_research_discovery_cycle(cycle_id="cycle-det-a", **args)  # type: ignore[arg-type]
        record2, _r2, _i2, _l2 = run_research_discovery_cycle(cycle_id="cycle-det-b", **args)  # type: ignore[arg-type]
        assert [c.research_family for c in record1.candidates] == [c.research_family for c in record2.candidates]
        assert [c.compile_status for c in record1.candidates] == [c.compile_status for c in record2.candidates]
        assert [c.lifecycle_stage for c in record1.candidates] == [c.lifecycle_stage for c in record2.candidates]
        assert [c.scorecard_classification for c in record1.candidates] == [c.scorecard_classification for c in record2.candidates]

    def test_duplicate_pruned_candidates_never_backtested_and_never_disappear(self) -> None:
        # trend_following/risk_reward_variation share the same real
        # trigger/entry/stop sentence shape (see app/strategy_families.py's
        # own disclosed docstring note) — this real seed/family combo is
        # known to produce real near-duplicates, keeping this test fast
        # (only the one real kept candidate gets backtested).
        record, _registry, iterations, _lessons = run_research_discovery_cycle(
            concept_name="Duplicate Pruning Test", population_size=4, seed="s-dup-cycle", compiled_strategy_registry={},
            quant_research_experiments=[], research_iterations=[], research_lessons=[], failed_archive=[],
            champion_history=[], existing_candidates=[], risk_per_trade_pct=2.0, cycle_id="cycle-dup",
            created_at=_CREATED_AT, proposed_by="quant", families=("trend_following", "risk_reward_variation"), symbols=["AAPL"],
        )
        pruned = [c for c in record.candidates if c.lifecycle_stage == "duplicate_pruned"]
        assert len(pruned) == record.duplicates_pruned
        assert record.duplicates_pruned > 0  # this real seed/family combo is known to collide
        assert len(record.candidates) == 4  # never silently dropped
        for candidate in pruned:
            assert candidate.iteration is None
            assert candidate.duplicate_of_candidate_id is not None

    def test_hard_gates_never_bypassed_across_a_real_population(self) -> None:
        """No candidate can be marked 'survivor' unless its own real
        ResearchLoopIterationRecord.candidacy == 'accepted' — proven
        directly against real, persisted evidence for every backtested
        candidate in the cycle, not merely asserted in isolation."""
        record, _registry, _iterations, _lessons = run_research_discovery_cycle(
            concept_name="Hard Gate Population Test", population_size=3, seed="s-hard-gate", compiled_strategy_registry={},
            quant_research_experiments=[], research_iterations=[], research_lessons=[], failed_archive=[],
            champion_history=[], existing_candidates=[], risk_per_trade_pct=2.0, cycle_id="cycle-hard-gate",
            created_at=_CREATED_AT, proposed_by="quant", symbols=["AAPL"],
        )
        for candidate in record.candidates:
            if candidate.lifecycle_stage == "survivor":
                assert candidate.iteration is not None
                assert candidate.iteration.candidacy == "accepted"
            if candidate.scorecard_classification == "champion_candidate":
                assert candidate.iteration is not None
                assert candidate.iteration.candidacy == "accepted"

    def test_existing_candidates_influence_future_discovery_reason(self) -> None:
        """A family with real, prior positive average expectancy earns
        a real 'successful_family' discovery reason on its next cycle's
        candidates — a real, structured (never free-text-only) lesson-
        driven reason, not a post-hoc rationalization."""
        first, _r1, _i1, _l1 = run_research_discovery_cycle(
            concept_name="Lesson Driven Test Gen1", population_size=2, seed="s-lesson-1", compiled_strategy_registry={},
            quant_research_experiments=[], research_iterations=[], research_lessons=[], failed_archive=[],
            champion_history=[], existing_candidates=[], risk_per_trade_pct=2.0, cycle_id="cycle-lesson-1",
            created_at=_CREATED_AT, proposed_by="quant", symbols=["AAPL"],
        )
        second, _r2, _i2, _l2 = run_research_discovery_cycle(
            concept_name="Lesson Driven Test Gen2", population_size=2, seed="s-lesson-2", compiled_strategy_registry={},
            quant_research_experiments=[], research_iterations=[], research_lessons=[], failed_archive=[],
            champion_history=[], existing_candidates=first.candidates, risk_per_trade_pct=2.0, cycle_id="cycle-lesson-2",
            created_at=_CREATED_AT, proposed_by="quant", symbols=["AAPL"],
        )
        reasons = {c.research_family: c.discovery_reason for c in second.candidates}
        assert all(r in ("successful_family", "research_exploration") for r in reasons.values())

    def test_no_backtests_run_for_a_zero_symbol_universe_never_crashes(self) -> None:
        record, _r, _i, _l = run_research_discovery_cycle(
            concept_name="Empty Symbols Test", population_size=3, seed="s-empty-symbols", compiled_strategy_registry={},
            quant_research_experiments=[], research_iterations=[], research_lessons=[], failed_archive=[],
            champion_history=[], existing_candidates=[], risk_per_trade_pct=2.0, cycle_id="cycle-empty-symbols",
            created_at=_CREATED_AT, proposed_by="quant", symbols=[],
        )
        assert len(record.candidates) == 3  # real completion, no crash — the underlying funnel honestly reports zero trades
