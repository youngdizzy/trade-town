"""Covers app/strategy_families.py — CEO directive "TradeTown — Phase 8:
Autonomous Strategy Discovery + Adversarial Research Engine," Sections
8A-8C: deterministic, materially-diverse strategy family generation and
real, deterministic near-duplicate pruning.
"""
from __future__ import annotations

from app.strategy_compiler import compile_strategy_text
from app.schemas import FamilyResearchStats
from app.strategy_families import (
    SUPPORTED_FAMILIES,
    UNSUPPORTED_FAMILIES,
    GeneratedCandidateSeed,
    allocate_research_budget,
    generate_candidate_population,
    prune_duplicates,
)


class TestGenerateCandidatePopulation:
    def test_zero_candidates(self) -> None:
        pop = generate_candidate_population(seed="s", population_size=0)
        assert pop == []

    def test_one_candidate(self) -> None:
        pop = generate_candidate_population(seed="s", population_size=1)
        assert len(pop) == 1
        assert pop[0].family in SUPPORTED_FAMILIES

    def test_thirty_candidates_all_compile_or_are_real_ambiguous(self) -> None:
        pop = generate_candidate_population(seed="s-30", population_size=30)
        assert len(pop) == 30
        for candidate in pop:
            definition = compile_strategy_text(name=f"Fam {candidate.index}", source_text=candidate.source_text)
            assert definition.status == "compiled", f"family={candidate.family} text={candidate.source_text!r} detail={definition.detail}"

    def test_every_supported_family_is_reachable(self) -> None:
        pop = generate_candidate_population(seed="s-reach", population_size=len(SUPPORTED_FAMILIES) * 3)
        families_seen = {c.family for c in pop}
        assert families_seen == set(SUPPORTED_FAMILIES)

    def test_deterministic_generation(self) -> None:
        pop1 = generate_candidate_population(seed="deterministic-seed", population_size=15)
        pop2 = generate_candidate_population(seed="deterministic-seed", population_size=15)
        assert [c.source_text for c in pop1] == [c.source_text for c in pop2]
        assert [c.family for c in pop1] == [c.family for c in pop2]
        assert [c.direction for c in pop1] == [c.direction for c in pop2]

    def test_different_seed_produces_different_population(self) -> None:
        pop1 = generate_candidate_population(seed="seed-a", population_size=10)
        pop2 = generate_candidate_population(seed="seed-b", population_size=10)
        assert [c.source_text for c in pop1] != [c.source_text for c in pop2]

    def test_restricted_family_list_only_generates_those_families(self) -> None:
        pop = generate_candidate_population(seed="s-restrict", population_size=6, families=("trend_following",))
        assert all(c.family == "trend_following" for c in pop)

    def test_each_candidate_has_a_real_deterministic_candidate_seed(self) -> None:
        pop = generate_candidate_population(seed="s-seed-audit", population_size=4)
        seeds = [c.candidate_seed for c in pop]
        assert len(set(seeds)) == len(seeds)  # every real candidate gets its own unique, deterministic sub-seed
        assert all(s.startswith("s-seed-audit:") for s in seeds)


class TestUnsupportedFamilies:
    def test_unsupported_families_are_disclosed_not_generated(self) -> None:
        assert set(UNSUPPORTED_FAMILIES.keys()) & set(SUPPORTED_FAMILIES) == set()
        assert "mean_reversion" in UNSUPPORTED_FAMILIES
        assert "volatility_expansion" in UNSUPPORTED_FAMILIES
        assert "volatility_contraction" in UNSUPPORTED_FAMILIES
        assert "regime_conditioned" in UNSUPPORTED_FAMILIES
        for reason in UNSUPPORTED_FAMILIES.values():
            assert len(reason) > 20  # a real, disclosed reason, never an empty placeholder


class TestPruneDuplicates:
    def test_mechanism_distinct_families_never_collide_across_families(self) -> None:
        """trend_following/breakout/momentum_threshold each use a
        genuinely different real trigger phrasing (EMA cross vs.
        trend-score threshold vs. RSI threshold). A small discrete
        parameter space means WITHIN one family, two candidates can
        legitimately draw the exact same real parameters by chance —
        real, correct duplicate detection, not a bug. What must never
        happen is a candidate from one family being pruned as a
        duplicate of a candidate from a DIFFERENT, mechanism-distinct
        family — real word overlap between genuinely different trigger
        phrasing should never cross the real near-duplicate bar."""
        pop = generate_candidate_population(seed="s-mech-diverse", population_size=30, families=("trend_following", "breakout", "momentum_threshold"))
        family_by_index = {c.index: c.family for c in pop}
        _kept, dup_of = prune_duplicates(pop)
        for dup_index, original_index in dup_of.items():
            assert family_by_index[dup_index] == family_by_index[original_index], (
                f"candidate {dup_index} ({family_by_index[dup_index]}) was incorrectly pruned as a duplicate of "
                f"candidate {original_index} ({family_by_index[original_index]}) — a mechanism-distinct family collision."
            )

    def test_textually_similar_families_can_legitimately_collide(self) -> None:
        """trend_following and risk_reward_variation (and
        volatility_adjusted_risk) share the SAME real trigger/entry/stop
        sentence shape, differing only in one swept numeric parameter —
        real word-level overlap between them is often >= the real near-
        duplicate bar, and pruning that IS correct (Section 8C's own
        "if uncertain, keep the candidate" concerns near-duplicate
        UNCERTAINTY, not two templates that are genuinely this close).
        This documents that real behavior rather than asserting a false
        "every family label guarantees diversity" invariant."""
        pop = generate_candidate_population(seed="s-similar", population_size=12, families=("trend_following", "risk_reward_variation"))
        kept, dup_of = prune_duplicates(pop)
        assert len(kept) + len(dup_of) == 12
        assert len(kept) >= 1  # never prunes every candidate

    def test_identical_candidates_are_pruned(self) -> None:
        pop = generate_candidate_population(seed="s-dup", population_size=1)
        original = pop[0]
        duplicate = GeneratedCandidateSeed(
            index=1, family=original.family, direction=original.direction, source_text=original.source_text,
            params=dict(original.params), candidate_seed="s-dup:1", research_reason=original.research_reason,
        )
        kept, dup_of = prune_duplicates([original, duplicate])
        assert len(kept) == 1
        assert dup_of == {1: 0}

    def test_pruning_is_order_stable_first_occurrence_kept(self) -> None:
        pop = generate_candidate_population(seed="s-dup-order", population_size=1)
        original = pop[0]
        duplicate = GeneratedCandidateSeed(
            index=1, family=original.family, direction=original.direction, source_text=original.source_text,
            params=dict(original.params), candidate_seed="s-dup-order:1", research_reason=original.research_reason,
        )
        kept, dup_of = prune_duplicates([original, duplicate])
        assert kept[0].index == 0
        assert dup_of[1] == 0

    def test_near_duplicate_relationship_is_preserved_not_silently_dropped(self) -> None:
        pop = generate_candidate_population(seed="s-preserve", population_size=1)
        original = pop[0]
        duplicate = GeneratedCandidateSeed(
            index=1, family=original.family, direction=original.direction, source_text=original.source_text,
            params=dict(original.params), candidate_seed="s-preserve:1", research_reason=original.research_reason,
        )
        _kept, dup_of = prune_duplicates([original, duplicate])
        assert 1 in dup_of  # the relationship is real, structured data — never silently discarded

    def test_thirty_candidates_pruning_never_raises(self) -> None:
        pop = generate_candidate_population(seed="s-30-prune", population_size=30)
        kept, dup_of = prune_duplicates(pop)
        assert len(kept) + len(dup_of) == 30
        assert len(kept) >= 1  # never prunes EVERY candidate — real diversity across 6 families guarantees at least one survivor


class TestAllocateResearchBudget:
    def _stats(self, family: str, *, avg_expectancy: float | None, backtested: int = 5) -> FamilyResearchStats:
        return FamilyResearchStats(
            family=family,  # type: ignore[arg-type]
            numberGenerated=backtested, numberBacktested=backtested, numberRejected=0, numberPromising=0, numberRobust=0,
            averageExpectancyR=avg_expectancy, medianExpectancyR=avg_expectancy, averageMaxDrawdownR=None,
            benchmarkBeatRatePct=None, costSurvivalRatePct=None, walkForwardPassRatePct=None, adversarialSurvivalRatePct=None,
        )

    def test_empty_stats_returns_empty(self) -> None:
        assert allocate_research_budget([]) == []

    def test_weights_sum_to_100(self) -> None:
        stats = [self._stats("trend_following", avg_expectancy=0.5), self._stats("breakout", avg_expectancy=None), self._stats("momentum_threshold", avg_expectancy=-0.2)]
        decisions = allocate_research_budget(stats)
        assert abs(sum(w for _f, w, _r in decisions) - 100.0) < 0.05

    def test_no_family_ever_gets_zero_exploration_floor(self) -> None:
        stats = [self._stats("trend_following", avg_expectancy=5.0), self._stats("breakout", avg_expectancy=None)]
        decisions = allocate_research_budget(stats)
        weak_family_weight = next(w for f, w, _r in decisions if f == "breakout")
        assert weak_family_weight > 0.0  # never fully abandoned (Section 8J's own explicit instruction)

    def test_stronger_expectancy_earns_proportionally_more_exploitation_share(self) -> None:
        stats = [self._stats("trend_following", avg_expectancy=1.0), self._stats("breakout", avg_expectancy=0.1)]
        decisions = allocate_research_budget(stats)
        strong_weight = next(w for f, w, _r in decisions if f == "trend_following")
        weak_weight = next(w for f, w, _r in decisions if f == "breakout")
        assert strong_weight > weak_weight

    def test_deterministic_allocation(self) -> None:
        stats = [self._stats("trend_following", avg_expectancy=0.7), self._stats("breakout", avg_expectancy=None)]
        d1 = allocate_research_budget(stats)
        d2 = allocate_research_budget(stats)
        assert d1 == d2
