"""app/strategy_registry.py — CEO directive "Professional Quant Firm
Phase," Feature 37: real, persisted version history for
`CompiledStrategyDefinition`.

RESEARCH FIRST. app/strategy_compiler.py's `compile_strategy_text()` is
already deterministic and already computes a real, slug-based
`definition_id` from `name` alone (`re.sub(r"[^a-z0-9]+", "-",
name.lower())` — the SAME id every time the same name is compiled), so
"the same logical strategy" already has a real, stable key in this
codebase; the only real gap is that nothing stores the history under
that key. `version` itself was already a real field on
`CompiledStrategyDefinition` — CompileStrategyRequest.previous_version
was CALLER-supplied and explicitly disclosed as not-yet-persisted (see
that field's own docstring in app/schemas.py), which is exactly the
"never silently overwrite" risk Feature 37 flags: a caller could pass
any previous_version it wanted, real or not.

This module does not change `compile_strategy_text()` at all (it stays
the pure, stateless, already-tested function every existing caller —
including the stateless `/compile-strategy` preview endpoint —
continues to use unmodified). It adds ONE new function,
`register_strategy_version()`, that computes the REAL next version from
a persisted history list's own real length rather than trusting a
caller-supplied number, and returns the newly-compiled definition
alongside the FULL updated history — the caller (app/state.py) is
responsible for actually persisting that updated list, matching this
codebase's own state-mutation convention (pure functions in app/*.py,
persistence only in app/state.py under its lock).

CEO directive "Strategy Intelligence + Live Strategy Attribution" — a
full repo audit (see this directive's own Phase 1) found a SECOND real
identity gap this module is the natural home to close: Strategy Lab's
own stage-gated `Strategy` (dossier/certification/health-tracked, but
with zero represented trading logic) and `CompiledStrategyDefinition`
(the real trigger/requirement/entry/stop/target rules, but with no
stage/dossier/certification tracking) were two disconnected identity
spaces — a `Strategy` had no field naming which compiled definition, if
any, represents its actual rules. `register_researchable_strategy()`
below is the one real bridge: it reuses `register_strategy_version()`
unchanged to compile+persist the rules, then — only when compilation
genuinely reached `status == "compiled"` — creates a real, new
`Strategy` whose `compiled_definition_id` names that exact definition.
Never a fabricated link: an "ambiguous"/"invalid" compilation still
returns its own real definition (with its own real `ambiguities`/
`detail`) but no `Strategy` is created for it.
"""
from __future__ import annotations

from app.ema_pullback_research import (
    CHANDELIER_ATR_MULTIPLIER,
    CHANDELIER_ATR_PERIOD,
    DEFAULT_TIMEFRAME,
    EMA_PERIOD,
    MIN_PULLBACK_CANDLES,
    REFERENCE_R_MULTIPLE,
)
from app.schemas import AgentId, CompiledStrategyDefinition, ResearchCategory, Strategy
from app.strategy_compiler import compile_strategy_text, strategy_definition_slug

# Deliberately uncapped, unlike app/quant_research_lab.py's
# MAX_QUANT_RESEARCH_EXPERIMENTS or app/strategy_lab.py's
# MAX_STRATEGY_HALL_OF_FAME: Feature 37 explicitly requires "preserve
# historical versions, never silently overwrite," and the real next
# version number below is derived directly from this list's own real
# length — capping it would both violate that requirement and corrupt
# the version count. A strategy's real version count is expected to
# stay small (each version is a deliberate CEO/agent edit, not a
# high-frequency event like a research experiment).


def register_strategy_version(
    registry: dict[str, list[CompiledStrategyDefinition]],
    *,
    name: str,
    source_text: str,
    timeframe: str = "1h",
    created_by: AgentId = "quant",
) -> tuple[CompiledStrategyDefinition, dict[str, list[CompiledStrategyDefinition]]]:
    """The one real entry point. `registry` is the FULL persisted
    version registry (every strategy's own history, keyed by its real
    slug id) — this function looks up this strategy's own real slug
    (`strategy_definition_slug(name)`) itself, so callers never have to
    pre-filter. The real next version number is
    `len(existing_versions_for_this_slug) + 1`, never a caller-supplied
    guess. Returns (new_definition, updated_registry) — the full,
    real, append-only history for this one slug, every other strategy's
    history in `registry` left untouched, and no prior version of THIS
    strategy ever silently overwritten."""
    slug = strategy_definition_slug(name)
    existing_versions = registry.get(slug, [])
    real_previous_version = len(existing_versions) if existing_versions else None
    new_definition = compile_strategy_text(
        name=name,
        source_text=source_text,
        timeframe=timeframe,
        created_by=created_by,
        previous_version=real_previous_version,
    )
    updated_registry = {**registry, slug: [*existing_versions, new_definition]}
    return new_definition, updated_registry


def register_researchable_strategy(
    registry: dict[str, list[CompiledStrategyDefinition]],
    existing_strategies: list[Strategy],
    *,
    name: str,
    description: str,
    source_text: str,
    timeframe: str = "1h",
    created_by: AgentId = "quant",
    focus_category: ResearchCategory = "stock",
) -> tuple[CompiledStrategyDefinition, Strategy | None, dict[str, list[CompiledStrategyDefinition]]]:
    """CEO directive "Strategy Intelligence + Live Strategy Attribution"
    — the real bridge between this codebase's two previously-disconnected
    strategy identity spaces (Strategy Lab's stage-gated `Strategy.id`
    and `app/strategy_compiler.py`'s rule-bearing
    `CompiledStrategyDefinition.id`, both real name-derived slugs, but
    never the same object before this function existed). Reuses
    `register_strategy_version()` above unchanged (never a second
    compile/persist path) to produce the real compiled definition, then
    — ONLY if that definition's own real vocabulary match actually
    reached `status == "compiled"` (never for "ambiguous"/"invalid" —
    see `compile_strategy_text()`'s own docstring) — constructs a new
    `Strategy` whose `compiled_definition_id` names that exact real
    definition. Returns `(definition, None, updated_registry)` when
    compilation didn't fully succeed: the real compiled definition (with
    its own real `ambiguities`/`detail` explaining exactly what's
    missing) is still returned and still persisted via
    `updated_registry`, so a CEO/agent can see why no Strategy was
    created and try again — never a silently-abandoned attempt.

    Raises `ValueError` if a Strategy with this exact real slug already
    exists in `existing_strategies` — this function only ever creates a
    genuinely NEW Strategy Lab strategy; a second version of an existing
    strategy's rules should go through `register_strategy_version()`
    directly and stay linked to the SAME real `Strategy.compiled_
    definition_id` (never a second, duplicate Strategy for the same
    real idea)."""
    slug = strategy_definition_slug(name)
    if any(s.id == slug for s in existing_strategies):
        raise ValueError(
            f"A Strategy Lab strategy with id '{slug}' already exists — register a new version of its "
            "compiled definition via register_strategy_version() instead of creating a second Strategy "
            "under the same name."
        )
    new_definition, updated_registry = register_strategy_version(
        registry, name=name, source_text=source_text, timeframe=timeframe, created_by=created_by
    )
    new_strategy: Strategy | None = None
    if new_definition.status == "compiled":
        new_strategy = Strategy(
            id=slug,
            name=name,
            description=description,
            createdBy=created_by,
            focusCategory=focus_category,
            createdAt=new_definition.created_at,
            compiledDefinitionId=new_definition.id,
        )
    return new_definition, new_strategy, updated_registry


def get_compiled_definition_version(
    registry: dict[str, list[CompiledStrategyDefinition]], definition_id: str, version: int
) -> CompiledStrategyDefinition | None:
    """CEO directive "Complete Trade Provenance," Part 2 — resolves a
    trade's real, immutable strategy-rule snapshot
    (`CeoDecisionRecord.strategyCompiledDefinitionId`/`.Version`) back
    into the exact `CompiledStrategyDefinition` that was active at
    decision time, by reading the same real, append-only history
    `register_strategy_version()` already writes — never a second
    lookup mechanism. `None` when the id has no history at all (should
    not happen for any id this codebase itself ever wrote, but a save
    file is untrusted input) or when no entry in that real history
    matches this exact version (same defensive posture)."""
    return next((d for d in registry.get(definition_id, []) if d.version == version), None)


# CEO directive "Strategy Intelligence + Live Strategy Attribution,"
# Phase 13 — "encode the previously supplied [50 EMA] strategy as an
# explicit research strategy rather than hard-coding it into the
# trading brain." `app/ema_pullback_research.py`'s hand-built engine
# already validates the shape (real, disclosed gaps: no transaction
# costs/slippage, no out-of-sample split — see that module's own
# docstring); this is the real Strategy Lab CITIZENSHIP half — every
# real parameter below (`EMA_PERIOD`, `MIN_PULLBACK_CANDLES`,
# `CHANDELIER_ATR_PERIOD`/`_MULTIPLIER`, `REFERENCE_R_MULTIPLE`)
# is imported from that exact module, never a second, independently-typed
# copy of the same numbers that could silently drift out of sync.
def _ema_pullback_source_text(*, direction: str) -> str:
    if direction == "long":
        return (
            f"This strategy waits for price to stay below the {EMA_PERIOD} EMA, then closes above the {EMA_PERIOD} EMA on a confirmed candle. "
            f"It then requires at least {MIN_PULLBACK_CANDLES} bearish candles as the pullback. "
            "Entry triggers when price closes above the previous swing high established before the pullback. "
            f"Use a chandelier stop with a {CHANDELIER_ATR_PERIOD}-period ATR and a {CHANDELIER_ATR_MULTIPLIER:g}x multiplier. "
            f"Target {REFERENCE_R_MULTIPLE:g}R."
        )
    return (
        f"This strategy waits for price to stay above the {EMA_PERIOD} EMA, then closes below the {EMA_PERIOD} EMA on a confirmed candle. "
        f"It then requires at least {MIN_PULLBACK_CANDLES} bullish candles as the pullback. "
        "Entry triggers when price closes below the previous swing low established before the pullback. "
        f"Use a chandelier stop with a {CHANDELIER_ATR_PERIOD}-period ATR and a {CHANDELIER_ATR_MULTIPLIER:g}x multiplier. "
        f"Target {REFERENCE_R_MULTIPLE:g}R."
    )


def default_researchable_strategies() -> tuple[list[Strategy], dict[str, list[CompiledStrategyDefinition]]]:
    """The real, on-by-default Strategy Lab citizenship for the 50 EMA
    breakout/pullback pattern — long and short, the symmetric inverse
    the CEO directive itself asked for. Each source text is composed
    from `app/ema_pullback_research.py`'s own real constants (see
    `_ema_pullback_source_text()` above) and run through the SAME real
    `register_researchable_strategy()` every CEO/agent-triggered
    `POST /api/sandbox/register-researchable-strategy` call uses — never
    a hand-authored `CompiledStrategyDefinition` that could drift from
    what the compiler would actually produce. Both texts are verified
    (see tests/test_strategy_registry.py) to reach `status == "compiled"`
    — if `app/strategy_compiler.py`'s vocabulary ever regresses, this
    seed step raises, loudly, rather than silently shipping a broken
    or absent strategy."""
    strategies: list[Strategy] = []
    registry: dict[str, list[CompiledStrategyDefinition]] = {}
    for name, description, direction in (
        (
            "50 EMA Breakout Pullback (Long)",
            f"A real, disclosed-vocabulary long setup: closes above the {EMA_PERIOD} EMA, a real pullback, a swing-high breakout entry, a chandelier stop, an R-multiple target. See app/ema_pullback_research.py for this codebase's own independent, hand-built backtest of the same shape.",
            "long",
        ),
        (
            "50 EMA Breakout Pullback (Short)",
            f"The symmetric short inverse: closes below the {EMA_PERIOD} EMA, a real pullback, a swing-low breakdown entry, a chandelier stop, an R-multiple target.",
            "short",
        ),
    ):
        definition, new_strategy, registry = register_researchable_strategy(
            registry,
            strategies,
            name=name,
            description=description,
            source_text=_ema_pullback_source_text(direction=direction),
            timeframe=DEFAULT_TIMEFRAME,
            created_by="quant",
            focus_category="stock",
        )
        if new_strategy is None:
            raise AssertionError(
                f"default_researchable_strategies(): the real 50 EMA {direction} source text failed to compile "
                f"(status={definition.status!r}, detail={definition.detail!r}) — this seed step never ships a "
                "silently-broken or silently-absent strategy."
            )
        strategies.append(new_strategy)
    return strategies, registry
