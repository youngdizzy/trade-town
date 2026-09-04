"""Covers app/research_orchestrator.py — CEO directive "TradeTown —
Autonomous Research Orchestrator 1.0." Pure decision-function unit tests
build real `GameSaveState` fixtures by running the actual
`run_research_factory_cycle()`/`run_research_loop_iteration()` entry
points (never hand-built `FactoryRunRecord`/`ResearchLoopIterationRecord`
fixtures prone to schema drift); integration tests exercise the real,
unmodified `app/state.py::GameState` wiring end to end, including the
real concurrency guard, using a fresh `GameState()` instance per test
(mirroring tests/test_autonomous_promotion.py's own
`TestAutonomousPromotionWiredIntoState` convention).
"""
from __future__ import annotations

import asyncio

from app.research_factory import run_research_factory_cycle
from app.research_loop import run_research_loop_iteration
from app.research_orchestrator import (
    RESEARCH_CADENCE_SIM_DAYS,
    decide_research_orchestration,
    find_research_seed,
)
from app.schemas import GameSaveState, StrategyHypothesis
from app.state import GameState, default_state
from app.strategy_compiler import strategy_definition_slug
from app.strategy_registry import register_strategy_version

_CREATED_AT = "2024-01-01T00:00:00+00:00"
_EMA_TEXT = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R."


def _hypothesis(**overrides: object) -> StrategyHypothesis:
    base: dict[str, object] = dict(
        id="hyp-seed", hypothesis="Trend continuation after a confirmed breakout.", marketMechanism="Momentum continuation",
        expectedEdge="Positive expectancy in trending regimes", invalidationConditions="Flat/negative walk-forward expectancy",
        symbolUniverse=["AAPL"], timeframe="1h", entryConditions="x", exitConditions="x", stopLossLogic="x",
        takeProfitLogic="x", positionSizingLogic="x", riskConstraints="x", proposedBy="quant", createdAt=_CREATED_AT,
    )
    base.update(overrides)
    return StrategyHypothesis(**base)  # type: ignore[arg-type]


def _seed_via_factory_run(state: GameSaveState, *, family_name: str, sim_day: int | None, created_at: str = _CREATED_AT) -> GameSaveState:
    """Real, end-to-end: registers a real strategy version (the same real
    `register_strategy_version()` `POST /register-strategy-version` uses
    — Phase 0 found the factory's OWN registry only ever gains an entry
    for a MUTATED child, never the original seed, so a seed the
    orchestrator can find a "current best version" for must already be
    a REGISTERED version, exactly like a CEO/agent would do before
    running the factory), then runs the real, unmodified
    `run_research_factory_cycle()`, and merges the result into `state`
    the EXACT same way `GameState.submit_research_factory_run()` does
    (app/state.py) — never a hand-built `FactoryRunRecord`."""
    definition, registry_with_seed = register_strategy_version(state.compiled_strategy_versions, name=family_name, source_text=_EMA_TEXT)
    run, updated_registry, _iterations, _lessons = run_research_factory_cycle(
        _hypothesis(id=f"hyp-{family_name}"), definition, compiled_strategy_registry=registry_with_seed, quant_research_experiments=[],
        research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
        run_id=f"factory-run-{family_name}", created_at=created_at, symbols=["AAPL"], max_generations=1, max_total_backtests=1,
    )
    run = run.model_copy(update={"sim_day": sim_day})
    family_slug = strategy_definition_slug(family_name)
    updated_versions = {**state.compiled_strategy_versions, family_slug: updated_registry.get(family_slug, [definition])}
    return state.model_copy(update={"factory_runs": [*state.factory_runs, run], "compiled_strategy_versions": updated_versions})


def _seed_via_research_loop_iteration(state: GameSaveState, *, family_name: str, created_at: str = _CREATED_AT) -> GameSaveState:
    """Real, end-to-end via the SIMPLER, non-factory research loop —
    proves the orchestrator can also continue research a human only ever
    ran through `POST /research-loop/run`, never the factory. Also
    registers the seed version first — see `_seed_via_factory_run`'s own
    docstring for why."""
    definition, registry_with_seed = register_strategy_version(state.compiled_strategy_versions, name=family_name, source_text=_EMA_TEXT)
    iteration = run_research_loop_iteration(
        _hypothesis(id=f"hyp-{family_name}"), definition, quant_research_experiments=[], research_iterations=[], failed_archive=[],
        risk_per_trade_pct=2.0, iteration_id=f"iter-{family_name}", mutation_id="mut-0", created_at=created_at, symbols=["AAPL"],
    )
    return state.model_copy(update={"research_iterations": [*state.research_iterations, iteration], "compiled_strategy_versions": registry_with_seed})


class TestFindResearchSeed:
    def test_a_fresh_save_has_no_real_seed_to_reuse(self) -> None:
        assert find_research_seed(default_state()) is None

    def test_finds_a_real_seed_from_a_prior_factory_run(self) -> None:
        state = _seed_via_factory_run(default_state(), family_name="Factory Family", sim_day=10)
        seed = find_research_seed(state)
        assert seed is not None
        assert seed.strategy_family == "Factory Family"
        assert seed.source == "factory_run"
        assert seed.definition.status == "compiled"

    def test_finds_a_real_seed_from_a_prior_simple_research_loop_iteration(self) -> None:
        state = _seed_via_research_loop_iteration(default_state(), family_name="Loop Family")
        seed = find_research_seed(state)
        assert seed is not None
        assert seed.strategy_family == "Loop Family"
        assert seed.source == "research_loop_iteration"

    def test_picks_the_most_recently_created_source_across_both_kinds(self) -> None:
        state = default_state()
        state = _seed_via_factory_run(state, family_name="Older Family", sim_day=1, created_at="2024-01-01T00:00:00+00:00")
        state = _seed_via_research_loop_iteration(state, family_name="Newer Family", created_at="2024-06-01T00:00:00+00:00")
        seed = find_research_seed(state)
        assert seed is not None
        assert seed.strategy_family == "Newer Family"

    def test_resolves_the_latest_compiled_version_not_the_original_seed_version(self) -> None:
        state = _seed_via_factory_run(default_state(), family_name="Evolving Family", sim_day=1)
        slug = strategy_definition_slug("Evolving Family")
        versions = state.compiled_strategy_versions[slug]
        seed = find_research_seed(state)
        assert seed is not None
        assert seed.definition.version == max(v.version for v in versions)

    def test_never_mutates_the_input_state(self) -> None:
        state = _seed_via_factory_run(default_state(), family_name="Immutable Family", sim_day=1)
        before = state.model_copy()
        find_research_seed(state)
        find_research_seed(state)
        assert state == before


class TestDecideResearchOrchestration:
    def test_no_research_input_blocks_a_fresh_save(self) -> None:
        decision = decide_research_orchestration(default_state(), factory_currently_running=False)
        assert decision.should_run is False
        assert decision.reason == "NO_RESEARCH_INPUT"
        assert decision.seed is None

    def test_a_real_seed_with_no_cadence_baseline_is_a_first_autonomous_run(self) -> None:
        state = _seed_via_research_loop_iteration(default_state(), family_name="First Run Family")
        decision = decide_research_orchestration(state, factory_currently_running=False)
        assert decision.should_run is True
        assert decision.reason == "FIRST_AUTONOMOUS_RUN"
        assert decision.seed is not None
        assert decision.last_factory_run_sim_day is None

    def test_a_pre_existing_run_with_no_sim_day_baseline_is_also_a_first_autonomous_run(self) -> None:
        """A save from before this feature shipped: every FactoryRunRecord
        has sim_day=None. There is no reliable cadence baseline — the
        honest, disclosed behavior (Part IX restart safety) is to treat
        it the same as never having run, not to fabricate a baseline."""
        state = _seed_via_factory_run(default_state(), family_name="Pre-Existing Family", sim_day=None)
        decision = decide_research_orchestration(state, factory_currently_running=False)
        assert decision.should_run is True
        assert decision.reason == "FIRST_AUTONOMOUS_RUN"

    def test_not_yet_due_before_the_cadence_boundary(self) -> None:
        state = _seed_via_factory_run(default_state(), family_name="Cadence Family", sim_day=10)
        state = state.model_copy(update={"time": state.time.model_copy(update={"day": 10 + RESEARCH_CADENCE_SIM_DAYS - 1})})
        decision = decide_research_orchestration(state, factory_currently_running=False)
        assert decision.should_run is False
        assert decision.reason == "NOT_DUE"

    def test_due_exactly_at_the_cadence_boundary(self) -> None:
        state = _seed_via_factory_run(default_state(), family_name="Cadence Family", sim_day=10)
        state = state.model_copy(update={"time": state.time.model_copy(update={"day": 10 + RESEARCH_CADENCE_SIM_DAYS})})
        decision = decide_research_orchestration(state, factory_currently_running=False)
        assert decision.should_run is True
        assert decision.reason == "SCHEDULED_CADENCE"

    def test_due_past_the_cadence_boundary(self) -> None:
        state = _seed_via_factory_run(default_state(), family_name="Cadence Family", sim_day=10)
        state = state.model_copy(update={"time": state.time.model_copy(update={"day": 10 + RESEARCH_CADENCE_SIM_DAYS + 5})})
        decision = decide_research_orchestration(state, factory_currently_running=False)
        assert decision.should_run is True
        assert decision.reason == "SCHEDULED_CADENCE"

    def test_factory_already_running_takes_precedence_over_everything_else(self) -> None:
        state = _seed_via_factory_run(default_state(), family_name="Busy Family", sim_day=10)
        state = state.model_copy(update={"time": state.time.model_copy(update={"day": 10 + RESEARCH_CADENCE_SIM_DAYS + 5})})
        decision = decide_research_orchestration(state, factory_currently_running=True)
        assert decision.should_run is False
        assert decision.reason == "FACTORY_ALREADY_RUNNING"

    def test_emergency_stop_blocks_an_otherwise_due_run(self) -> None:
        state = _seed_via_factory_run(default_state(), family_name="Halted Family", sim_day=10)
        state = state.model_copy(update={"time": state.time.model_copy(update={"day": 10 + RESEARCH_CADENCE_SIM_DAYS})})
        state = state.model_copy(update={"emergency_stop": state.emergency_stop.model_copy(update={"active": True})})
        decision = decide_research_orchestration(state, factory_currently_running=False)
        assert decision.should_run is False
        assert decision.reason == "EMERGENCY_STOP"

    def test_bounded_retry_an_in_memory_attempt_counts_toward_cadence_even_with_no_persisted_run(self) -> None:
        """Part XII — a failed attempt (never persisted as a FactoryRunRecord)
        must still block same-window re-attempts, using ONLY the
        in-memory last-attempt tracker `app/state.py::GameState` supplies."""
        state = _seed_via_research_loop_iteration(default_state(), family_name="Retry Family")
        state = state.model_copy(update={"time": state.time.model_copy(update={"day": 3})})
        decision = decide_research_orchestration(state, factory_currently_running=False, last_orchestrator_attempt_sim_day=1)
        assert decision.should_run is False
        assert decision.reason == "NOT_DUE"

    def test_bounded_retry_eventually_becomes_due_again_after_the_cadence_window(self) -> None:
        state = _seed_via_research_loop_iteration(default_state(), family_name="Retry Family")
        state = state.model_copy(update={"time": state.time.model_copy(update={"day": RESEARCH_CADENCE_SIM_DAYS + 1})})
        decision = decide_research_orchestration(state, factory_currently_running=False, last_orchestrator_attempt_sim_day=1)
        assert decision.should_run is True
        assert decision.reason == "SCHEDULED_CADENCE"

    def test_repeated_evaluation_on_the_same_sim_day_is_idempotent(self) -> None:
        """Part VIII — evaluating the exact same due state 500 times must
        keep returning the SAME decision, never escalate/duplicate."""
        state = _seed_via_factory_run(default_state(), family_name="Idempotent Family", sim_day=10)
        state = state.model_copy(update={"time": state.time.model_copy(update={"day": 10 + RESEARCH_CADENCE_SIM_DAYS})})
        decisions = [decide_research_orchestration(state, factory_currently_running=False) for _ in range(500)]
        assert all(d.should_run and d.reason == "SCHEDULED_CADENCE" for d in decisions)

    def test_never_mutates_the_input_state(self) -> None:
        state = _seed_via_factory_run(default_state(), family_name="Pure Family", sim_day=10)
        before = state.model_copy()
        decide_research_orchestration(state, factory_currently_running=False)
        assert state == before


class TestResearchOrchestratorWiredIntoState:
    """Real, end-to-end wiring through app/state.py::GameState — a fresh
    instance per test (mirrors tests/test_autonomous_promotion.py's own
    TestAutonomousPromotionWiredIntoState convention), never the shared
    process-wide game_state singleton."""

    def test_a_fresh_game_state_schedules_nothing(self) -> None:
        state = GameState()
        decision = asyncio.run(state.maybe_orchestrate_research())
        assert decision.should_run is False
        assert decision.reason == "NO_RESEARCH_INPUT"
        assert state._research_orchestrator_task is None

    def test_a_due_seed_is_actually_run_through_the_real_unmodified_submit_research_factory_run(self) -> None:
        async def _run() -> tuple[bool, int, int]:
            state = GameState()
            state.data = _seed_via_research_loop_iteration(state.data, family_name="Orchestrated Family")
            before_run_count = len(state.data.factory_runs)

            decision = await state.maybe_orchestrate_research()
            assert state._research_orchestrator_task is not None
            await state._research_orchestrator_task

            after_run_count = len(state.data.factory_runs)
            new_run = state.data.factory_runs[-1]
            assert new_run.strategy_family == "Orchestrated Family"
            assert new_run.sim_day == state.data.time.day
            outcome = state._research_orchestrator_last_outcome
            assert outcome is not None
            assert outcome.succeeded is True
            assert outcome.factory_run_id == new_run.id
            return decision.should_run, before_run_count, after_run_count

        should_run, before_run_count, after_run_count = asyncio.run(_run())
        assert should_run is True
        assert after_run_count == before_run_count + 1

    def test_concurrency_a_second_evaluation_while_the_first_run_is_still_in_flight_is_skipped(self) -> None:
        """Part VII — asyncio.create_task() only SCHEDULES the coroutine;
        it has not executed yet immediately after creation, so a second
        evaluation issued right away must see FACTORY_ALREADY_RUNNING,
        never start a second overlapping run."""

        async def _run() -> tuple[str, str, int]:
            state = GameState()
            state.data = _seed_via_research_loop_iteration(state.data, family_name="Concurrent Family")
            first = await state.maybe_orchestrate_research()
            second = await state.maybe_orchestrate_research()
            assert state._research_orchestrator_task is not None
            await state._research_orchestrator_task
            return first.reason, second.reason, len(state.data.factory_runs)

        first_reason, second_reason, run_count = asyncio.run(_run())
        assert first_reason == "FIRST_AUTONOMOUS_RUN"
        assert second_reason == "FACTORY_ALREADY_RUNNING"
        assert run_count == 1  # never duplicated

    def test_after_the_in_flight_run_completes_the_guard_clears(self) -> None:
        async def _run() -> tuple[str, str]:
            state = GameState()
            state.data = _seed_via_research_loop_iteration(state.data, family_name="Cleared Family")
            first = await state.maybe_orchestrate_research()
            assert state._research_orchestrator_task is not None
            await state._research_orchestrator_task
            # Not yet due again (no cadence has elapsed) — reason must be
            # NOT_DUE, never FACTORY_ALREADY_RUNNING, proving the guard
            # correctly cleared once the task finished.
            second = await state.maybe_orchestrate_research()
            return first.reason, second.reason

        first_reason, second_reason = asyncio.run(_run())
        assert first_reason == "FIRST_AUTONOMOUS_RUN"
        assert second_reason == "NOT_DUE"

    def test_restart_safety_a_brand_new_gamestate_derives_cadence_purely_from_persisted_data(self) -> None:
        """Simulates a backend restart: a fresh GameState (in-memory
        attributes all reset to None) loaded with data that already has
        a real persisted factory run. The cadence decision must come
        entirely from `state.factory_runs[*].sim_day`, never from
        anything in-memory that no longer exists."""
        restarted = GameState()
        restarted.data = _seed_via_factory_run(restarted.data, family_name="Restarted Family", sim_day=5)
        restarted.data = restarted.data.model_copy(update={"time": restarted.data.time.model_copy(update={"day": 5 + RESEARCH_CADENCE_SIM_DAYS + 1})})
        assert restarted._research_orchestrator_task is None
        assert restarted._research_orchestrator_last_attempt_sim_day is None
        decision = asyncio.run(restarted.maybe_orchestrate_research())
        assert decision.should_run is True
        assert decision.reason == "SCHEDULED_CADENCE"

    def test_a_factory_failure_is_captured_as_real_evidence_never_a_fabricated_success(self) -> None:
        async def _run() -> tuple[bool, str, int]:
            state = GameState()
            state.data = _seed_via_research_loop_iteration(state.data, family_name="Failing Family")

            async def _boom(hypothesis: object, definition: object, **kwargs: object) -> object:
                raise RuntimeError("simulated factory failure")

            state.submit_research_factory_run = _boom  # type: ignore[assignment]
            decision = await state.maybe_orchestrate_research()
            assert state._research_orchestrator_task is not None
            await state._research_orchestrator_task
            outcome = state._research_orchestrator_last_outcome
            assert outcome is not None
            return outcome.succeeded, decision.reason, len(state.data.factory_runs)

        succeeded, reason, run_count = asyncio.run(_run())
        assert succeeded is False
        assert reason == "FIRST_AUTONOMOUS_RUN"
        assert run_count == 0  # no fabricated FactoryRunRecord on failure

    def test_a_failed_attempt_still_consumes_the_cadence_window_bounded_retry(self) -> None:
        async def _run() -> tuple[str, str]:
            state = GameState()
            state.data = _seed_via_research_loop_iteration(state.data, family_name="Bounded Retry Family")

            async def _boom(hypothesis: object, definition: object, **kwargs: object) -> object:
                raise RuntimeError("simulated factory failure")

            state.submit_research_factory_run = _boom  # type: ignore[assignment]
            first = await state.maybe_orchestrate_research()
            assert state._research_orchestrator_task is not None
            await state._research_orchestrator_task
            # Same sim day, same failing seed — must NOT retry immediately.
            second = await state.maybe_orchestrate_research()
            return first.reason, second.reason

        first_reason, second_reason = asyncio.run(_run())
        assert first_reason == "FIRST_AUTONOMOUS_RUN"
        assert second_reason == "NOT_DUE"

    def test_describe_status_reflects_a_real_completed_run_without_triggering_anything(self) -> None:
        async def _run() -> tuple[int, bool]:
            state = GameState()
            state.data = _seed_via_research_loop_iteration(state.data, family_name="Status Family")
            await state.maybe_orchestrate_research()
            assert state._research_orchestrator_task is not None
            await state._research_orchestrator_task
            run_count_before = len(state.data.factory_runs)
            status = await state.describe_research_orchestrator_status()
            run_count_after = len(state.data.factory_runs)
            return run_count_before, (run_count_after == run_count_before and status.last_outcome_succeeded is True)

        run_count_before, unchanged_and_correct = asyncio.run(_run())
        assert run_count_before == 1
        assert unchanged_and_correct is True

    def test_describe_status_on_a_fresh_state_is_an_honest_no_research_input(self) -> None:
        status = asyncio.run(GameState().describe_research_orchestrator_status())
        assert status.would_run_now is False
        assert status.reason == "NO_RESEARCH_INPUT"
        assert status.factory_currently_running is False
        assert status.last_outcome_succeeded is None
