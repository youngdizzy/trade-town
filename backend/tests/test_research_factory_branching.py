"""Covers CEO directive "TradeTown — Phase 9: Full Autonomous Quant
Research Factory" — the real, additive extensions to
app/research_factory.py::run_research_factory_cycle(): every candidate
now also runs a real adversarial attack + Research Council pass,
multi-child branching (`max_children_per_parent`), the real wall-clock
safety net (`max_runtime_seconds`), and structured lesson-memory
retrieval (`retrieve_relevant_lessons()`). tests/test_research_factory.py's
own 49 pre-existing tests already prove every original (single-child,
`max_children_per_parent=1`) behavior is completely unchanged — this
file covers only what's new.
"""
from __future__ import annotations

import app.research_factory as research_factory_module
from app.research_factory import _mutation_record_for_code, retrieve_relevant_lessons, run_research_factory_cycle
from app.schemas import ResearchLessonRecord, StrategyHypothesis
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


def _lesson(*, lesson_id: str, family: str, failure_codes: list[str], created_at: str = _CREATED_AT) -> ResearchLessonRecord:
    return ResearchLessonRecord(
        id=lesson_id, strategyFamily=family, definitionId="def-1", definitionVersion=1, iterationId="iter-1",
        hypothesis="x", candidacy="rejected", reason="x", confidencePct=50.0, lesson="x", createdAt=created_at,
        failureCodes=failure_codes,  # type: ignore[arg-type]
    )


class TestMutationRecordForCode:
    def test_different_codes_produce_different_text(self) -> None:
        mr_dd = _mutation_record_for_code(
            "excessive_drawdown", parent_definition_id="d", parent_definition_version=1, parent_iteration_id="i",
            mutation_number=1, mutation_id="m1", created_at=_CREATED_AT,
        )
        mr_cost = _mutation_record_for_code(
            "cost_sensitivity", parent_definition_id="d", parent_definition_version=1, parent_iteration_id="i",
            mutation_number=2, mutation_id="m2", created_at=_CREATED_AT,
        )
        assert mr_dd is not None and mr_cost is not None
        assert mr_dd.proposed_change != mr_cost.proposed_change
        assert mr_dd.observed_failure_codes == ["excessive_drawdown"]
        assert mr_cost.observed_failure_codes == ["cost_sensitivity"]

    def test_unknown_code_has_no_template(self) -> None:
        # Every real FailureCode currently has a real app/research_loop.py
        # _MUTATION_TEMPLATES entry (including "regime_failure" — that
        # code's real limitation is having no BOUNDED TEXT OPERATOR in
        # app/research_factory.py's own _MUTATION_OPERATOR_TYPE, checked
        # separately by build_mutation_candidate(), not a missing
        # descriptive template here). Cast past the Literal to prove the
        # real `code not in _MUTATION_TEMPLATES` guard itself works.
        from typing import cast

        from app.schemas import FailureCode

        mr = _mutation_record_for_code(
            cast(FailureCode, "not_a_real_code"), parent_definition_id="d", parent_definition_version=1, parent_iteration_id="i",
            mutation_number=1, mutation_id="m1", created_at=_CREATED_AT,
        )
        assert mr is None

    def test_regime_failure_has_a_template_but_no_bounded_operator(self) -> None:
        from app.research_factory import build_mutation_candidate
        from app.strategy_compiler import compile_strategy_text

        definition = compile_strategy_text(name="Regime Test", source_text=_EMA_TEXT)
        mr = _mutation_record_for_code(
            "regime_failure", parent_definition_id=definition.id, parent_definition_version=definition.version, parent_iteration_id="i",
            mutation_number=1, mutation_id="m1", created_at=_CREATED_AT,
        )
        assert mr is not None  # real descriptive text exists
        mc = build_mutation_candidate(mr, definition, mutation_candidate_id="mc1", created_at=_CREATED_AT)
        assert mc.mutated_source_text is None  # but no bounded, deterministic text-splice operator exists for it


class TestRetrieveRelevantLessons:
    def test_matches_same_family_and_overlapping_code(self) -> None:
        lessons = [
            _lesson(lesson_id="l1", family="Fam A", failure_codes=["excessive_drawdown"]),
            _lesson(lesson_id="l2", family="Fam B", failure_codes=["excessive_drawdown"]),
            _lesson(lesson_id="l3", family="Fam A", failure_codes=["cost_sensitivity"]),
        ]
        matches = retrieve_relevant_lessons(lessons, strategy_family="Fam A", failure_codes=["excessive_drawdown"])
        assert [m.id for m in matches] == ["l1"]

    def test_most_recent_first(self) -> None:
        lessons = [
            _lesson(lesson_id="l1", family="Fam A", failure_codes=["excessive_drawdown"]),
            _lesson(lesson_id="l2", family="Fam A", failure_codes=["excessive_drawdown"]),
        ]
        matches = retrieve_relevant_lessons(lessons, strategy_family="Fam A", failure_codes=["excessive_drawdown"])
        assert [m.id for m in matches] == ["l2", "l1"]

    def test_no_match_returns_empty(self) -> None:
        lessons = [_lesson(lesson_id="l1", family="Fam A", failure_codes=["excessive_drawdown"])]
        assert retrieve_relevant_lessons(lessons, strategy_family="Fam A", failure_codes=["cost_sensitivity"]) == []

    def test_respects_max_matches(self) -> None:
        lessons = [_lesson(lesson_id=f"l{i}", family="Fam A", failure_codes=["excessive_drawdown"]) for i in range(10)]
        matches = retrieve_relevant_lessons(lessons, strategy_family="Fam A", failure_codes=["excessive_drawdown"], max_matches=3)
        assert len(matches) == 3


class TestRunResearchFactoryCycleBranching:
    def test_default_call_never_sets_sibling_rank(self) -> None:
        """Backward compatibility, directly proven: the default
        (max_children_per_parent=1) path never populates the new
        sibling_rank/fitness_rationale fields — same real shape every
        pre-existing test already exercises."""
        definition = compile_strategy_text(name="Branching Default Strategy", source_text=_EMA_TEXT)
        registry = {definition.id: [definition]}
        run, _r, _i, _l = run_research_factory_cycle(
            _hypothesis(), definition, compiled_strategy_registry=registry, quant_research_experiments=[],
            research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
            run_id="branch-default", created_at=_CREATED_AT, symbols=["AAPL"],
        )
        assert run.config.max_children_per_parent == 1
        assert all(c.sibling_rank is None for c in run.candidates)

    def test_every_backtested_candidate_carries_adversarial_and_council_evidence(self) -> None:
        definition = compile_strategy_text(name="Branching Evidence Strategy", source_text=_EMA_TEXT)
        registry = {definition.id: [definition]}
        run, _r, _i, _l = run_research_factory_cycle(
            _hypothesis(), definition, compiled_strategy_registry=registry, quant_research_experiments=[],
            research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
            run_id="branch-evidence", created_at=_CREATED_AT, symbols=["AAPL"],
        )
        backtested = [c for c in run.candidates if c.iteration is not None]
        assert backtested
        for candidate in backtested:
            assert candidate.adversarial_result is not None
            assert candidate.research_council is not None
            assert len(candidate.research_council.findings) == 7
            assert candidate.research_council.recommendation in ("continue", "mutate", "retest", "archive", "insufficient_evidence")

    def test_multi_children_config_is_recorded_and_no_crash(self) -> None:
        definition = compile_strategy_text(name="Branching Multi Strategy", source_text=_RSI_TEXT)
        registry = {definition.id: [definition]}
        run, _r, _i, _l = run_research_factory_cycle(
            _hypothesis(), definition, compiled_strategy_registry=registry, quant_research_experiments=[],
            research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
            run_id="branch-multi", created_at=_CREATED_AT, symbols=["AAPL"], max_children_per_parent=3, max_generations=3,
        )
        assert run.config.max_children_per_parent == 3
        assert run.candidates_generated >= 1
        # Real, disclosed invariant regardless of how many distinct failure
        # codes this particular real backtest happened to diagnose: every
        # group of siblings sharing the same real parent gets a real,
        # gap-free 1..N sibling_rank once ranked.
        by_parent: dict[str, list[int]] = {}
        for c in run.candidates:
            if c.sibling_rank is not None and c.parent_candidate_id is not None:
                by_parent.setdefault(c.parent_candidate_id, []).append(c.sibling_rank)
        for parent_id, ranks in by_parent.items():
            assert sorted(ranks) == list(range(1, len(ranks) + 1)), f"parent {parent_id} siblings have non-contiguous ranks {ranks}"

    def test_backtests_run_never_exceeds_the_real_cap_even_with_branching(self) -> None:
        definition = compile_strategy_text(name="Branching Budget Strategy", source_text=_RSI_TEXT)
        registry = {definition.id: [definition]}
        run, _r, iterations, _l = run_research_factory_cycle(
            _hypothesis(), definition, compiled_strategy_registry=registry, quant_research_experiments=[],
            research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
            run_id="branch-budget", created_at=_CREATED_AT, symbols=["AAPL"], max_children_per_parent=3, max_total_backtests=2,
        )
        assert run.candidates_backtested <= 2
        assert len(iterations) <= 2

    def test_max_runtime_seconds_stops_the_run(self, monkeypatch) -> None:
        """A real wall-clock safety net — proven deterministically by
        monkeypatching time.monotonic() rather than relying on a real
        strategy actually taking that long (would make the test itself
        slow and flaky)."""
        definition = compile_strategy_text(name="Branching Runtime Strategy", source_text=_EMA_TEXT)
        registry = {definition.id: [definition]}

        real_monotonic = research_factory_module.time.monotonic
        call_count = {"n": 0}

        def _fake_monotonic() -> float:
            call_count["n"] += 1
            # First call establishes start_time; every call after that
            # reports far enough in the future to trip a tiny cap.
            return real_monotonic() if call_count["n"] == 1 else real_monotonic() + 999.0

        monkeypatch.setattr(research_factory_module.time, "monotonic", _fake_monotonic)

        run, _r, _i, _l = run_research_factory_cycle(
            _hypothesis(), definition, compiled_strategy_registry=registry, quant_research_experiments=[],
            research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
            run_id="branch-runtime", created_at=_CREATED_AT, symbols=["AAPL"], max_runtime_seconds=1, max_generations=5,
        )
        assert "runtime cap" in run.stop_reason

    def test_max_runtime_seconds_zero_disables_the_check(self) -> None:
        definition = compile_strategy_text(name="Branching Runtime Disabled Strategy", source_text=_EMA_TEXT)
        registry = {definition.id: [definition]}
        run, _r, _i, _l = run_research_factory_cycle(
            _hypothesis(), definition, compiled_strategy_registry=registry, quant_research_experiments=[],
            research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
            run_id="branch-runtime-disabled", created_at=_CREATED_AT, symbols=["AAPL"], max_runtime_seconds=0,
        )
        assert "runtime cap" not in run.stop_reason

    def test_no_duplicate_candidate_ids(self) -> None:
        """Direct proof the double-append bug class is closed: every
        real candidate id appears in `run.candidates` exactly once,
        with branching enabled across multiple generations."""
        definition = compile_strategy_text(name="Branching Dedup Strategy", source_text=_RSI_TEXT)
        registry = {definition.id: [definition]}
        run, _r, _i, _l = run_research_factory_cycle(
            _hypothesis(), definition, compiled_strategy_registry=registry, quant_research_experiments=[],
            research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
            run_id="branch-dedup", created_at=_CREATED_AT, symbols=["AAPL"], max_children_per_parent=3, max_generations=4,
        )
        ids = [c.id for c in run.candidates]
        assert len(ids) == len(set(ids)), f"duplicate candidate ids found: {ids}"
