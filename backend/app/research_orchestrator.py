"""CEO directive "TradeTown — Autonomous Research Orchestrator 1.0" — the
one real answer to "should TradeTown start a research factory cycle right
now?"

Phase 0 forensic audit (source inspection, not documentation) found:

- `app/research_factory.py::run_research_factory_cycle()` is a real, pure,
  bounded, multi-generation research loop. It is fully automatic once
  started but requires a caller to already hold a real `StrategyHypothesis`
  AND a real, already-compiled `CompiledStrategyDefinition` to seed it —
  it does not generate either itself.
- The only production entry point, `GameState.submit_research_factory_run()`
  (`app/state.py`), is called from exactly one place:
  `POST /api/sandbox/research-factory/run` (`app/routers/sandbox.py`) — a
  human/API caller supplies both the hypothesis and the seed definition
  every single time. Nothing in `app/nexus.py`'s tick loop calls it.
- There is no automated hypothesis-generation loop anywhere in this
  codebase (`StrategyHypothesis`'s own docstring in `app/schemas.py`
  already discloses this). A genuinely NEW research question — one no
  human or agent has ever typed — cannot be conjured by this module
  without fabricating one, which the CEO's own directives explicitly and
  repeatedly forbid.
- Every real, already-authored `StrategyHypothesis` a human or agent has
  ever submitted is, however, already permanently persisted: once on
  `ResearchLoopIterationRecord.hypothesis` (the simpler, single-pass
  research loop, `app/research_loop.py`) and once per factory run on its
  generation-0 `FactoryCandidateRecord.hypothesis`
  (`state.factory_runs[*].candidates`). Continuing research on an
  already-real, already-vetted hypothesis by re-running the (bounded,
  budget-capped) factory against the family's current best compiled
  version is NOT fabrication — it is exactly what a human clicking "run
  again" on their own prior research would do.
- `nexus.py` already has a canonical simulation-time cadence concept
  (`WEEKLY_INTERVAL_DAYS`, used for the existing weekly evening-report/
  reflection cadence) — reused here rather than inventing a second one.
  At the default sim speed (`GAME_MINUTES_PER_TICK=5` sim-minutes every
  `TICK_INTERVAL_SECONDS=2.0` real seconds), one simulated week is
  ~67 real minutes — frequent enough that the company visibly keeps
  researching in the background, rare enough that repeated runs (each
  bounded to `MAX_TOTAL_BACKTESTS_PER_FACTORY_RUN=10` backtests and
  `MAX_RUNTIME_SECONDS=300` real seconds) never compete with each other
  or with the rest of the simulation loop for attention.

What this module deliberately is, and is not (Part II of the directive):
it answers exactly one question — `decide_research_orchestration()` — and
resolves exactly one supporting fact — `find_research_seed()`, which real
existing hypothesis+definition pair to continue. It never itself performs
research, generates strategies, validates them, or promotes them; it never
imports or calls anything from `app/champion_challenger.py`,
`app/autonomous_promotion.py`, `app/risk_contract.py`, `app/broker.py`, or
any order/position/Gatekeeper code. The actual invocation of the existing,
unmodified `GameState.submit_research_factory_run()` — and the concurrency/
retry/observability plumbing around it — lives in `app/state.py` and
`app/sim.py`, exactly where the equally slow, equally real
`submit_research_factory_run()` call already lives today.

Disclosed scope boundary: only two triggers are implemented this pass —
a deterministic scheduled cadence, and a first-run rule for when no
cadence baseline exists yet (Part IV: "implement the smallest safe
trigger set"). Evidence-driven triggers (a detected research-to-decision
stall, a critical drift backlog, ...) are explicitly NOT implemented here
even though `SystemHealthSnapshot` already exposes real signals for them
— wiring a NEW trigger class is a distinct, separately-scoped milestone,
not a rider on this one.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from app.nexus import WEEKLY_INTERVAL_DAYS
from app.schemas import CompiledStrategyDefinition, GameSaveState, StrategyHypothesis
from app.strategy_compiler import strategy_definition_slug

# Part III — the one authoritative research cadence. Reuses nexus.py's own
# existing simulated-week concept rather than inventing a second cadence
# constant; see this module's own docstring above for why one simulated
# week is the safest default given the factory's own real budget/runtime
# caps.
RESEARCH_CADENCE_SIM_DAYS = WEEKLY_INTERVAL_DAYS

ResearchOrchestratorReason = Literal[
    "FIRST_AUTONOMOUS_RUN",
    "SCHEDULED_CADENCE",
    "NOT_DUE",
    "FACTORY_ALREADY_RUNNING",
    "NO_RESEARCH_INPUT",
    "EMERGENCY_STOP",
]


@dataclass(frozen=True)
class ResearchOrchestratorSeed:
    """One real, already-authored (never fabricated) research input to
    continue: a hypothesis a human or agent already wrote, and the
    strategy family's current best real compiled version."""

    strategy_family: str
    hypothesis: StrategyHypothesis
    definition: CompiledStrategyDefinition
    source: Literal["factory_run", "research_loop_iteration"]
    source_created_at: str


@dataclass(frozen=True)
class ResearchOrchestratorOutcome:
    """Part XI/XV — what actually happened the last time the orchestrator
    fired, kept in memory only (see `app/state.py::GameState`'s own
    docstring for why this is deliberately not persisted). Real failure
    evidence, never a fabricated success."""

    triggered_at: str
    strategy_family: str
    succeeded: bool
    factory_run_id: str | None
    detail: str | None


@dataclass(frozen=True)
class ResearchOrchestratorDecision:
    """Part XV — an auditable answer to "why did/didn't the factory run,"
    never a bare boolean."""

    should_run: bool
    reason: ResearchOrchestratorReason
    sim_day: int
    research_cadence_sim_days: int
    last_factory_run_sim_day: int | None
    seed: ResearchOrchestratorSeed | None = None


def _latest_compiled_definition(state: GameSaveState, strategy_family: str) -> CompiledStrategyDefinition | None:
    """The family's current best real compiled version — never the
    original seed version frozen at whatever point a human first tested
    it. Continuing research against the family's most evolved real
    version is the same choice a human re-running their own research
    would make, not a new decision this module invents."""
    slug = strategy_definition_slug(strategy_family)
    versions = [d for d in state.compiled_strategy_versions.get(slug, []) if d.status == "compiled"]
    if not versions:
        return None
    return max(versions, key=lambda d: d.version)


def find_research_seed(state: GameSaveState) -> ResearchOrchestratorSeed | None:
    """Part VI — the real research-input prerequisite. Returns the most
    recently authored, real (hypothesis, strategy_family) pair drawn from
    every already-persisted source — factory-run generation-0 candidates
    and simple research-loop iterations alike — resolved against that
    family's current best real compiled version. Returns `None` (never a
    fabricated hypothesis) when nothing real exists yet; that is the
    honest, disclosed reason a fresh save cannot self-start its very
    first research cycle (see this module's own docstring)."""
    best: tuple[str, str, StrategyHypothesis, Literal["factory_run", "research_loop_iteration"]] | None = None
    for run in state.factory_runs:
        seed_candidate = next((c for c in run.candidates if c.generation == 0), None)
        if seed_candidate is None:
            continue
        if best is None or run.created_at > best[0]:
            best = (run.created_at, run.strategy_family, seed_candidate.hypothesis, "factory_run")
    for record in state.research_iterations:
        if best is None or record.created_at > best[0]:
            best = (record.created_at, record.strategy_family, record.hypothesis, "research_loop_iteration")
    if best is None:
        return None
    created_at, strategy_family, hypothesis, source = best
    definition = _latest_compiled_definition(state, strategy_family)
    if definition is None:
        return None
    return ResearchOrchestratorSeed(
        strategy_family=strategy_family, hypothesis=hypothesis, definition=definition, source=source, source_created_at=created_at
    )


def decide_research_orchestration(
    state: GameSaveState,
    *,
    factory_currently_running: bool,
    last_orchestrator_attempt_sim_day: int | None = None,
) -> ResearchOrchestratorDecision:
    """The orchestrator's one real decision. Pure — reads `state` (and the
    two runtime-only inputs the caller, `app/state.py`'s `GameState`,
    tracks in memory) and returns a decision; performs no I/O, starts no
    research, mutates nothing.

    Precedence (Part XIV, "smallest safe trigger set"):
    FACTORY_ALREADY_RUNNING > EMERGENCY_STOP > NO_RESEARCH_INPUT >
    FIRST_AUTONOMOUS_RUN > SCHEDULED_CADENCE > NOT_DUE.

    `last_orchestrator_attempt_sim_day` folds in-flight/just-failed
    orchestrator attempts into the SAME cadence tracker
    `state.factory_runs` already provides (Part XII bounded retry): a
    run that failed before a `FactoryRunRecord` could be persisted still
    consumes this cadence window, so a persistently-failing seed cannot
    retry every tick — only once per `RESEARCH_CADENCE_SIM_DAYS`."""
    sim_day = state.time.day
    persisted_last_run_sim_day = max((r.sim_day for r in state.factory_runs if r.sim_day is not None), default=None)
    last_factory_run_sim_day = max(d for d in (persisted_last_run_sim_day, last_orchestrator_attempt_sim_day) if d is not None) if (
        persisted_last_run_sim_day is not None or last_orchestrator_attempt_sim_day is not None
    ) else None

    def _decision(should_run: bool, reason: ResearchOrchestratorReason, seed: ResearchOrchestratorSeed | None = None) -> ResearchOrchestratorDecision:
        return ResearchOrchestratorDecision(
            should_run=should_run,
            reason=reason,
            sim_day=sim_day,
            research_cadence_sim_days=RESEARCH_CADENCE_SIM_DAYS,
            last_factory_run_sim_day=last_factory_run_sim_day,
            seed=seed,
        )

    if factory_currently_running:
        return _decision(False, "FACTORY_ALREADY_RUNNING")
    if state.emergency_stop.active:
        return _decision(False, "EMERGENCY_STOP")
    seed = find_research_seed(state)
    if seed is None:
        return _decision(False, "NO_RESEARCH_INPUT")
    if last_factory_run_sim_day is None:
        return _decision(True, "FIRST_AUTONOMOUS_RUN", seed)
    if sim_day - last_factory_run_sim_day >= RESEARCH_CADENCE_SIM_DAYS:
        return _decision(True, "SCHEDULED_CADENCE", seed)
    return _decision(False, "NOT_DUE")
