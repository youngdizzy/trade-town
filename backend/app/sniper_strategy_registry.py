"""app/sniper_strategy_registry.py — CEO directive "TradeTown — Sniper
Strategy Engine + Registry 1.0."

FORENSIC FINDING THIS MODULE ACTS ON. Before this directive, Memecoin
Sniper's "strategy identity" was two bare module-level constants
(`SNIPER_STRATEGY_ID`/`SNIPER_STRATEGY_NAME`, app/schemas.py) baked in
as `SniperPosition`/`SniperTrade`'s own pydantic field defaults —
never resolved through any lookup, never enable/disable-aware, never a
real object a caller could enumerate or reject an unknown id against.
`SniperStrategyVersionStatus` (`"versioned" | "unavailable"`) already
existed specifically so a future real versioning system would have a
real state to report into — its own docstring called `"versioned"` "a
real but honestly-unreachable value today." This module is that real
system.

WHY A SEPARATE REGISTRY FROM app/strategy_registry.py (DUPLICATION
AUDIT). The equities side's `Strategy`/`CompiledStrategyDefinition`
(app/schemas.py, app/strategy_registry.py) represent a strategy
COMPILED FROM CEO/agent-AUTHORED TEXT through app/strategy_compiler.py's
real trigger/requirement/entry/stop/target DSL, gated by a stage-based
Research Sandbox lifecycle (`Strategy.stage`: idea -> paper ->
limited_live -> ...). Memecoin Sniper has none of that: its one
strategy is a hand-written, deterministic Python pipeline
(`app/memecoin_sniper.py`'s `run_safety_firewall()`/`score_candidate()`/
`classify_candidate()`/`classify_timing()`/`evaluate_entry_firewall()`)
with no source text to compile and no research-sandbox stage. Reusing
`Strategy`/`CompiledStrategyDefinition` here would force one of two bad
outcomes: fabricating a fake `source_text` for code that was never
compiled from text, or leaving most of that object's real fields
(`focus_category` — an equities-only `ResearchCategory` Literal that
has no memecoin/liquidity analog — `stage`, `allocated_capital`)
permanently meaningless. `SniperStrategyDefinition`
(app/schemas.py) is deliberately small and honest about being a
different, domain-specific kind of thing.

SCOPE. This module is METADATA + GOVERNANCE, never a risk system and
never an execution dispatcher: it never touches SniperRiskState, never
evaluates a candidate, never calls evaluate_entry_firewall(), and
registering/enabling a strategy here can never itself authorize a
trade (see app/memecoin_sniper.py::tick_sniper_engine()'s own docstring
for the real gate order this composes with). It also never imports or
executes arbitrary code — a "strategy" here is a metadata record
naming one of this codebase's own hardcoded, reviewed pipelines, never
a caller-supplied function or module path.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import (
    SNIPER_STRATEGY_FAMILY,
    SNIPER_STRATEGY_ID,
    SNIPER_STRATEGY_NAME,
    SNIPER_STRATEGY_VERSION,
    SniperStrategyDefinition,
    SniperStrategyStatus,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_sniper_strategies() -> list[SniperStrategyDefinition]:
    """The one real registered strategy today — the exact hardcoded
    engine `app/memecoin_sniper.py` has always run, given a real,
    resolvable identity for the first time instead of bare constants.
    Mirrors `app/simulation.py::default_strategies()`'s own seed-list
    convention for `GameSaveState.strategies`. `provenance="hardcoded"`
    is the one honest value that applies — never "backtest_validated"/
    "champion"/"ai_discovered", none of which are true of this engine."""
    return [
        SniperStrategyDefinition(
            id=SNIPER_STRATEGY_ID,
            name=SNIPER_STRATEGY_NAME,
            family=SNIPER_STRATEGY_FAMILY,
            version=SNIPER_STRATEGY_VERSION,
            status="enabled",
            provenance="hardcoded",
            createdAt=_now_iso(),
        )
    ]


def resolve_sniper_strategy(strategies: list[SniperStrategyDefinition], strategy_id: str) -> SniperStrategyDefinition | None:
    """The one real lookup every real caller (app/memecoin_sniper.py's
    tick_sniper_engine(), this module's own set_sniper_strategy_status()
    below) uses — `None` (never a guess, never the first entry) when
    `strategy_id` isn't registered."""
    return next((s for s in strategies if s.id == strategy_id), None)


def register_sniper_strategy(
    strategies: list[SniperStrategyDefinition], new_strategy: SniperStrategyDefinition
) -> tuple[list[SniperStrategyDefinition], str | None]:
    """Appends `new_strategy` — rejects a duplicate id outright (`error`
    naming it) rather than silently overwriting or creating an
    ambiguous second entry with the same identity, since every real
    resolution above depends on `id` being unique. Returns
    `(strategies, error)`, the same shape as this codebase's other real
    state-mutating functions (see app/state.py's own conventions) —
    `strategies` unchanged when `error` is not `None`."""
    if resolve_sniper_strategy(strategies, new_strategy.id) is not None:
        return strategies, f"A Sniper strategy with id {new_strategy.id!r} is already registered."
    return [*strategies, new_strategy], None


def set_sniper_strategy_status(
    strategies: list[SniperStrategyDefinition], strategy_id: str, status: SniperStrategyStatus
) -> tuple[list[SniperStrategyDefinition], str | None]:
    """The one real enable/disable mutator. Only ever changes `status`
    on the matching entry — `id`/`name`/`family`/`version`/`provenance`/
    `createdAt` are never touched, so this can never retroactively
    change what a historical position/trade's already-stamped identity
    means (see SniperStrategyDefinition's own docstring). Returns
    `(strategies, error)` — `error` names an unknown id rather than
    silently no-oping, matching resolve_sniper_strategy()'s own
    never-guess convention."""
    index = next((i for i, s in enumerate(strategies) if s.id == strategy_id), None)
    if index is None:
        return strategies, f"No registered Sniper strategy with id {strategy_id!r}."
    updated = list(strategies)
    updated[index] = updated[index].model_copy(update={"status": status})
    return updated, None
