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
"""
from __future__ import annotations

from app.schemas import AgentId, CompiledStrategyDefinition
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
