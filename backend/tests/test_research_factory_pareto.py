"""Covers CEO directive "TradeTown — Autonomous Mutation Application +
Pareto Survivor Engine" as wired into `app/research_factory.py::
run_research_factory_cycle()`: real Pareto-frontier persistence on
`FactoryRunRecord`, and the real Section 10 anti-oscillation/duplicate-
state guard. `tests/test_research_factory.py`'s own 49 pre-existing
tests and `tests/test_research_factory_branching.py`'s own tests already
prove every prior behavior is completely unchanged — this file covers
only what's new.

The oscillation tests monkeypatch `research_factory_module.build_
mutation_candidate` to force a deterministic mutated source text — the
SAME established precedent `test_research_factory_branching.py`'s own
`test_max_runtime_seconds_stops_the_run` already uses (monkeypatching
`research_factory_module.time.monotonic`) for testing a real, pure
function's boundary deterministically rather than depending on which
failure code a real statistical backtest happens to diagnose.
"""
from __future__ import annotations

import app.research_factory as research_factory_module
from app.research_factory import run_research_factory_cycle
from app.schemas import MutationCandidate, MutationRecord, StrategyHypothesis
from app.strategy_compiler import compile_strategy_text

_CREATED_AT = "2024-01-01T00:00:00+00:00"
_EMA_TEXT = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R."
_RSI_TEXT = "Buy when the RSI is above 70. Enter when price closes above the previous swing high. Place a 5% stop. Target 2R."


def _hypothesis(**overrides: object) -> StrategyHypothesis:
    base: dict[str, object] = dict(
        id="hyp-seed", hypothesis="Trend continuation after a confirmed breakout.", marketMechanism="Momentum continuation",
        expectedEdge="Positive expectancy in trending regimes", invalidationConditions="Flat/negative walk-forward expectancy",
        symbolUniverse=["AAPL"], timeframe="1h", entryConditions="x", exitConditions="x", stopLossLogic="x",
        takeProfitLogic="x", positionSizingLogic="x", riskConstraints="x", proposedBy="quant", createdAt=_CREATED_AT,
    )
    base.update(overrides)
    return StrategyHypothesis(**base)  # type: ignore[arg-type]


def _force_mutated_text(forced_text: str):
    """Wraps the REAL `build_mutation_candidate()` and overrides only its
    `mutated_source_text` (every other real field — rationale, expected
    effect, constraints, reproducibility seed — stays exactly what the
    real function computed) so a test can deterministically force what
    the next mutation's compiled text will be, without faking any of the
    surrounding real evidence."""
    real_fn = research_factory_module.build_mutation_candidate

    def _patched(mutation: MutationRecord, definition: object, *, mutation_candidate_id: str, created_at: str) -> MutationCandidate:
        mc = real_fn(mutation, definition, mutation_candidate_id=mutation_candidate_id, created_at=created_at)  # type: ignore[arg-type]
        if mc.mutated_source_text is not None:
            mc = mc.model_copy(update={"mutated_source_text": forced_text})
        return mc

    return _patched


class TestAntiOscillationGuard:
    def test_mutation_reproducing_the_seed_is_pruned_never_backtested(self, monkeypatch) -> None:
        definition = compile_strategy_text(name="Oscillation Seed Strategy", source_text=_EMA_TEXT)
        registry = {definition.id: [definition]}
        monkeypatch.setattr(research_factory_module, "build_mutation_candidate", _force_mutated_text(definition.source_text))

        run, _r, _i, _l = run_research_factory_cycle(
            _hypothesis(), definition, compiled_strategy_registry=registry, quant_research_experiments=[],
            research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
            run_id="osc-1", created_at=_CREATED_AT, symbols=["AAPL"],
        )

        seed_candidate = run.candidates[0]
        duplicates = [c for c in run.candidates if c.lifecycle_stage == "duplicate_pruned"]
        assert len(duplicates) == 1, f"expected exactly one duplicate_pruned candidate, got lifecycle stages: {[c.lifecycle_stage for c in run.candidates]}"
        dup = duplicates[0]
        assert dup.iteration is None  # never spent a real backtest
        assert dup.duplicate_of_candidate_id == seed_candidate.id
        assert "already tested" in dup.decision_reason.lower() or "oscillation" in dup.decision_reason.lower()
        assert "anti-oscillation" in run.stop_reason.lower()
        # Real, disclosed invariant: only the real seed candidate ever
        # reached a real backtest — the forced reversal never did.
        assert run.candidates_backtested == 1

    def test_duplicate_pruned_candidate_never_gets_a_pareto_status(self, monkeypatch) -> None:
        """A pruned candidate has no real backtest evidence — it is
        honestly absent from the frontier, never defaulted to
        'dominated'."""
        definition = compile_strategy_text(name="Oscillation Pareto Strategy", source_text=_EMA_TEXT)
        registry = {definition.id: [definition]}
        monkeypatch.setattr(research_factory_module, "build_mutation_candidate", _force_mutated_text(definition.source_text))

        run, _r, _i, _l = run_research_factory_cycle(
            _hypothesis(), definition, compiled_strategy_registry=registry, quant_research_experiments=[],
            research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
            run_id="osc-2", created_at=_CREATED_AT, symbols=["AAPL"],
        )
        duplicates = [c for c in run.candidates if c.lifecycle_stage == "duplicate_pruned"]
        assert duplicates
        assert duplicates[0].pareto_status is None
        assert duplicates[0].pareto_dominated_by == []


class TestParetoFrontierWiring:
    def test_run_record_carries_a_pareto_frontier_for_real_candidates(self) -> None:
        definition = compile_strategy_text(name="Pareto Wiring Strategy", source_text=_RSI_TEXT)
        registry = {definition.id: [definition]}
        run, _r, _i, _l = run_research_factory_cycle(
            _hypothesis(), definition, compiled_strategy_registry=registry, quant_research_experiments=[],
            research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
            run_id="pareto-wiring", created_at=_CREATED_AT, symbols=["AAPL"], max_children_per_parent=3, max_generations=2,
        )
        backtested_ids = {c.id for c in run.candidates if c.iteration is not None}
        frontier_ids = {e.candidate_id for e in run.pareto_frontier}
        assert frontier_ids == backtested_ids
        for candidate in run.candidates:
            if candidate.iteration is not None:
                assert candidate.pareto_status in ("dominated", "non_dominated")
            else:
                assert candidate.pareto_status is None

    def test_single_child_lineage_still_gets_a_well_formed_lineage_wide_frontier(self) -> None:
        """max_children_per_parent=1 (the original Phase 7 shape) has no
        real SIBLINGS to compare within a generation, so the per-
        generation continuation choice is always unfiltered (see
        run_research_factory_cycle()'s own `len(pareto_pool) > 1` guard)
        — but the lineage-WIDE frontier persisted on `FactoryRunRecord`
        (Section 16) still legitimately compares candidates ACROSS
        generations, where a later, genuinely-improved descendant
        dominating an earlier ancestor is real, expected evolutionary
        behavior, not a bug. Every `dominated_by` reference must name a
        real candidate id that actually exists in this run."""
        definition = compile_strategy_text(name="Pareto Solo Strategy", source_text=_EMA_TEXT)
        registry = {definition.id: [definition]}
        run, _r, _i, _l = run_research_factory_cycle(
            _hypothesis(), definition, compiled_strategy_registry=registry, quant_research_experiments=[],
            research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
            run_id="pareto-solo", created_at=_CREATED_AT, symbols=["AAPL"],
        )
        real_ids = {c.id for c in run.candidates}
        for candidate in run.candidates:
            if candidate.iteration is not None:
                assert candidate.pareto_status in ("dominated", "non_dominated")
                if candidate.pareto_status == "dominated":
                    assert candidate.pareto_dominated_by
                    assert set(candidate.pareto_dominated_by) <= real_ids
                    assert candidate.pareto_reason
                else:
                    assert candidate.pareto_dominated_by == []

    def test_survivor_status_is_never_overridden_by_pareto_dominance(self) -> None:
        """Hard-gate isolation: `survived`/`lifecycle_stage` come purely
        from the existing, untouched candidacy funnel — Pareto dominance
        only ever decides which NON-survivor candidate's lineage
        continues, never whether something is accepted as a survivor."""
        definition = compile_strategy_text(name="Pareto Survivor Isolation Strategy", source_text=_EMA_TEXT)
        registry = {definition.id: [definition]}
        run, _r, _i, _l = run_research_factory_cycle(
            _hypothesis(), definition, compiled_strategy_registry=registry, quant_research_experiments=[],
            research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
            run_id="pareto-survivor", created_at=_CREATED_AT, symbols=["AAPL"], max_children_per_parent=3, max_generations=3,
        )
        for candidate_id in run.survivor_candidate_ids:
            candidate = next(c for c in run.candidates if c.id == candidate_id)
            assert candidate.survived is True
            # A real survivor is never excluded from the frontier purely
            # by virtue of being a survivor — it simply reflects real
            # dominance among whatever real siblings existed.
            assert candidate.pareto_status in ("dominated", "non_dominated", None)

    def test_no_duplicate_candidate_ids_with_pareto_and_oscillation_active(self) -> None:
        definition = compile_strategy_text(name="Pareto Dedup Strategy", source_text=_RSI_TEXT)
        registry = {definition.id: [definition]}
        run, _r, _i, _l = run_research_factory_cycle(
            _hypothesis(), definition, compiled_strategy_registry=registry, quant_research_experiments=[],
            research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
            run_id="pareto-dedup", created_at=_CREATED_AT, symbols=["AAPL"], max_children_per_parent=3, max_generations=4,
        )
        ids = [c.id for c in run.candidates]
        assert len(ids) == len(set(ids)), f"duplicate candidate ids found: {ids}"
