"""v0.7 — Save Architecture Redesign Phase 2. The module map GameSaveState is
split into for storage, plus the split/assemble helpers persistence.py's
per-module read/write path is built on.

Every field on GameSaveState belongs to exactly one module here — enforced
at import time by `_validate_module_map()` below, not just by a test, so a
field added to schemas.py without a module assignment fails loudly at
startup instead of silently never being persisted.

Module boundaries (core vs. archive) follow what actually changes together
and how big it actually gets, not the field's feature name:

- `derived` is its own module specifically because every field in it is
  recomputed from scratch on nearly every tick (company_score,
  company_health, company_dna, academy_state, ...) — grouping any of them into a
  feature module (e.g. company_health into `company`) would make that
  whole module "dirty" on every persist, defeating the hash-based
  dirty-skip in persistence.py.persist_modules().
- The archive modules (`trade_history`, `knowledge_archive`, `academy`)
  hold exactly the fields that are real permanent history and only ever
  grow: debate/decision logs, case studies, completed projects. They are
  deliberately excluded from GET /api/load (see routers/save.py) — every
  Command Center panel that reads them hydrates live from the WebSocket
  tick broadcast (ws_manager.py) regardless of when the initial load
  response arrives, so nothing breaks by fetching these lazily instead
  (see routers/save.py's `/api/load/archive/{module}`).

No "Buildings" module: this codebase has no persisted building/construction
state beyond company_health.marketCoverage (a recomputed float, already in
`derived` — named for what it actually measures, real watchlist growth, not
a facility/office-capability mechanic this game doesn't have) — the Campus
Map is derived from static Lobby layout data plus live agent locations, not
saved state. Documented here rather than inventing an empty module for a
section the spec named but this game doesn't have.
"""
from __future__ import annotations

from typing import Any

from app.schemas import GameSaveState

CORE_MODULES: tuple[str, ...] = (
    "meta",
    "settings",
    "world",
    "employees",
    "company",
    "research",
    "training",
    "founders",
    "derived",
)

# Fetched only via GET /api/load/archive/{module} — never part of GET
# /api/load or a save POST. These are the "Large Archives" the redesign
# spec called out: historical logs/journals/case studies that only grow.
ARCHIVE_MODULES: tuple[str, ...] = (
    "trade_history",
    "knowledge_archive",
    "academy",
)

ALL_MODULES: tuple[str, ...] = CORE_MODULES + ARCHIVE_MODULES

# Python (snake_case) field names from GameSaveState, grouped by module.
MODULE_FIELDS: dict[str, tuple[str, ...]] = {
    "meta": ("version", "updated_at"),
    "settings": ("player", "settings", "dialogue_history"),
    "world": ("time", "calendar", "whiteboards", "meeting", "news", "scanner_alerts"),
    "employees": ("agents", "agent_energy", "tasks"),
    "company": (
        "paper_portfolio",
        "treasury",
        "risk_limits",
        "risk_warnings",
        "emergency_stop",
        "viewed_trade_notification_ids",
        "performance_snapshots",
        "coach_reports",
        "strategies",
        "backtest_sessions",
        "simulation_results",
        "strategy_reports",
        "strategy_reviews",
        "strategy_model_validations",
        "strategy_monte_carlo_results",
        "strategy_regime_tests",
        "strategy_liquidity_validations",
        "strategy_executive_reviews",
        "strategy_founder_approvals",
        "strategy_health_assessments",
        "strategy_hall_of_fame",
        "strategy_failed_archive",
        "goals",
        "strategic_reviews",
        # Design Bible Chapter 69 Part 1 — Multi-Account & Fund
        # Management System (app/accounts.py). Grouped with
        # paper_portfolio/treasury above, not `derived`: an Account's
        # portfolio is real mutated state, never recomputed from scratch.
        "accounts",
        "active_account_id",
        # Design Bible Chapter 72 — Black Swan Intelligence & Resilience
        # System (app/black_swan.py). Real, CEO-mutated posture state —
        # not recomputed, so it belongs here, not in `derived`.
        "defensive_mode",
        # Design Bible Chapter 75 — Company Trading Modes. Real,
        # CEO-mutated mode/thresholds (plus internal rotation/
        # acknowledgment bookkeeping) — not recomputed, same as
        # defensive_mode above.
        "trading_modes",
        # Design Bible Chapter 73.5 — Mobile Command Center & Remote
        # Operations. Real, CEO-mutated Travel Mode posture/settings —
        # not recomputed, same as trading_modes above.
        "travel_mode",
        # Design Bible Chapter 74.5 — CEO Vision Board & Strategic
        # Alignment Engine (app/vision_board.py). Real, CEO-mutated
        # singleton — not recomputed, same as trading_modes/travel_mode
        # above.
        "vision_board",
    ),
    "research": ("research", "watchlist", "black_box"),
    # foundational_mentor_state lives here (not in `derived`) because,
    # unlike mentor_state (Sage), it isn't recomputed from scratch each
    # tick — its per-mentor progress (viewed/completed lessons, quiz
    # counters, resources, pause/skip/repeat status) is real mutated
    # state, the same category education's own progress already is.
    "training": ("signal_calibration", "player_vs_ai", "education", "foundational_mentor_state"),
    "founders": ("founder_state", "constitution"),
    "derived": (
        "company_score",
        "company_health",
        "company_health_delta",
        "company_dna",
        "company_dna_legacy",
        "daily_objective_status",
        "risk_budget_status",
        "academy_state",
        "reasoning_lab_state",
        "wisdom_state",
        "mentor_state",
        "thinking_profiles",
        "innovation_state",
        "market_environment",
        "market_intelligence",
        "portfolio_intelligence",
        "economic_intelligence",
        "black_swan_intelligence",
        "institutional_survival_score",
        "daily_circuit_breaker",
        "losing_streak",
        # Behavioral Circuit Breaker (app/behavioral_risk.py) — recomputed
        # fresh every tick exactly like daily_circuit_breaker/losing_streak
        # above, never a second drifting copy.
        "behavioral_circuit_breaker",
    ),
    "trade_history": (
        "decisions",
        "ceo_decisions",
        "trade_proposals",
        "debates",
        "challenge_reports",
        "gatekeeper_rejections",
        "opportunity_rejections",
        "executive_meeting_log",
    ),
    "knowledge_archive": (
        "case_studies",
        "decision_vault",
        "war_room_sessions",
        "question_archive",
        "reasoning_challenges",
        "reflection_sessions",
        "discipline_reviews",
        "hall_of_fame",
        "memory",
        "meeting_minutes",
        "executive_reviews",
        "board_reports",
        # Design Bible Chapter 74 — Self-Improvement Proposals and the
        # Institutional Evolution Engine. Real, capped, permanent
        # history, same as board_reports/executive_reviews above.
        "self_improvement_proposals",
        "evolution_reports",
        "talent",
        "department_self_evaluations",
        "market_intelligence_reports",
        "market_intelligence_learning",
        "economic_intelligence_reports",
        "black_swan_reports",
        "black_swan_events",
        "recovery_briefings",
        # Design Bible Chapter 73.5 — Mobile Command Center & Remote
        # Operations. A small, capped, append-only history, same as
        # recovery_briefings above.
        "travel_mode_briefings",
    ),
    "academy": ("academy_projects", "academy_completed_projects", "agent_knowledge"),
}

# field name -> wire alias (e.g. "dialogue_history" -> "dialogueHistory"),
# precomputed once from the model itself so this file never hand-duplicates
# an alias and drifts from schemas.py.
_FIELD_ALIASES: dict[str, str] = {name: (field.alias or name) for name, field in GameSaveState.model_fields.items()}


def _validate_module_map() -> None:
    seen: set[str] = set()
    for module, fields in MODULE_FIELDS.items():
        for field in fields:
            if field not in _FIELD_ALIASES:
                raise AssertionError(f"save_modules.MODULE_FIELDS[{module!r}] references unknown GameSaveState field {field!r}")
            if field in seen:
                raise AssertionError(f"save_modules.MODULE_FIELDS lists {field!r} in more than one module")
            seen.add(field)
    missing = set(_FIELD_ALIASES) - seen
    if missing:
        raise AssertionError(f"save_modules.MODULE_FIELDS is missing GameSaveState field(s): {sorted(missing)}")
    unknown_modules = set(MODULE_FIELDS) - set(ALL_MODULES)
    if unknown_modules:
        raise AssertionError(f"MODULE_FIELDS has module(s) not listed in ALL_MODULES: {sorted(unknown_modules)}")


_validate_module_map()


def _dump(state: GameSaveState) -> dict[str, Any]:
    return state.model_dump(mode="json", by_alias=True)


def split_state(state: GameSaveState) -> dict[str, dict[str, Any]]:
    """One alias-keyed (wire-shaped) dict per module, ready to be JSON-encoded
    and written to its own SaveModule row."""
    full = _dump(state)
    return {module: {_FIELD_ALIASES[f]: full[_FIELD_ALIASES[f]] for f in fields} for module, fields in MODULE_FIELDS.items()}


def module_defaults(module: str) -> dict[str, Any]:
    """Real fallback for a module missing from storage (a brand-new game, or
    one module recovering after another failed to validate) — reuses
    default_state() so a fallback is never a fabricated stub, just the same
    values a fresh game already starts with."""
    from app.state import default_state  # local import: avoids importing the whole manager graph for callers that only need split_state/assemble_state

    full = _dump(default_state())
    return {_FIELD_ALIASES[f]: full[_FIELD_ALIASES[f]] for f in MODULE_FIELDS[module]}


def merge_module_dicts(modules: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Combines alias-keyed per-module dicts into one full wire-shaped dict,
    without validating. Any module missing or empty falls back to
    module_defaults() for just that module, so a save that's missing one
    freshly-added archive module (e.g. upgrading from a build that didn't
    have it yet) still assembles into a complete dict rather than an
    incomplete one. Exposed separately from assemble_state() so
    persistence.py's migration path can deep-merge this onto full defaults
    before validating, same as the legacy single-blob recovery path."""
    merged: dict[str, Any] = {}
    defaults: dict[str, Any] | None = None
    for module in ALL_MODULES:
        data = modules.get(module)
        if not data:
            if defaults is None:
                from app.state import default_state

                defaults = _dump(default_state())
            data = {_FIELD_ALIASES[f]: defaults[_FIELD_ALIASES[f]] for f in MODULE_FIELDS[module]}
        merged.update(data)
    return merged


def assemble_state(modules: dict[str, dict[str, Any]]) -> GameSaveState:
    """Inverse of split_state(): merges alias-keyed per-module dicts back
    into one validated GameSaveState. Raises ValidationError if the result
    doesn't match the current schema even after per-module defaulting (e.g.
    a stored module predates a field added inside it) — persistence.py
    catches this and falls back to a deep-merge migration, same as the
    legacy single-blob path."""
    return GameSaveState.model_validate(merge_module_dicts(modules))
