"""Reads/writes the authoritative GameSaveState to SQLite.

THE BUG THIS FILE ORIGINALLY FIXED (read before changing anything here):
every past version of TradeTown has added new fields to the save schema
(v0.2 added agents, v0.3 added research/watchlist, v0.5 added trading, v0.6
added risk/decisions, v0.6.1 added two PaperTrade fields). The *old*
version of `load_save()` treated ANY Pydantic validation failure — which is
exactly what happens when a stored save predates a newly-added field — as
"no save exists yet," returning None. `main.py`'s startup then read that
None as "fresh deployment" and immediately overwrote the existing row with
a brand-new default state, permanently destroying the real save. This was
the actual root cause of reported progress loss after every code update,
not a Docker volume problem (the volume itself was always configured
correctly — see docker-compose.yml's `tradetown-data` named volume). The
fix: treat "row exists but doesn't validate" as a recoverable case, not an
empty one — attempt a generic migration (`_migrate_dict`) before ever
giving up, and only overwrite the live data after backing up the raw,
unrecoverable payload to `save_backups`, which is never automatically
deleted. `load_modules()` below applies the exact same philosophy to the
new per-module storage.

v0.7 SAVE ARCHITECTURE REDESIGN PHASE 2: the primary storage target moved
from one `saves` row holding the entire ~840KB blob (`load_save()` /
`persist_save()`, both still here but now only used for the one-time
migration of a pre-Phase-2 deployment's existing save) to one row per
module in `save_modules` (`load_modules()` / `persist_modules()`, see
app/save_modules.py for the module map). `load_state()` is the real
startup entry point — it prefers modules, falling back to the legacy blob
only if no module rows exist yet.

CEO directive "Proper Multi-Run / Save Isolation System": every table
above already stores a real, indexed `slot` column — this file was
already structurally multi-slot-capable; only this module's own
`SLOT = "default"` constant collapsed it to exactly one. No schema
migration, and no change to any of the ~90 existing
`persist_modules(state)` call sites elsewhere in the codebase, was
needed to add real multi-run support — see below.

`SLOT` is now a genuinely mutable module-level pointer (still named
`SLOT`, still read by every function below exactly as before) rather
than a constant, changed only via `set_active_slot()`. Every one of the
~90 existing call sites across the routers calls `persist_modules(state)`
with no `await` between the locked mutation that produced `state` and
that call — confirmed by direct inspection before this change — so
asyncio's cooperative, single-threaded scheduling already makes each of
them atomic with respect to a concurrent run switch (no other coroutine
can run in the gap, because there isn't one). The one real exception was
`app/sim.py`'s tick loop, which awaits a WS broadcast between producing
`state` and persisting it — fixed there by reordering, not by touching
this file's own call-site contract (see sim.py's own comment).

`list_runs()`/`read_module_for_slot()` are the one deliberate exception
to "everything reads the mutable `SLOT` pointer" — they take an explicit
`slot` argument and never touch or depend on the mutable pointer, so
listing every run's real current day is safe to call at any time,
including while a different run is the one actually active and ticking,
without disturbing it.
"""
from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from app.db import get_session
from app.models import ActiveRun, Run, SaveBackup, SaveGame, SaveModule
from app.save_modules import ALL_MODULES, assemble_state, merge_module_dicts, split_state
from app.schemas import GameSaveState, ModuleWriteResult, RunSummary
from app.state import default_state

logger = logging.getLogger("tradetown.persistence")

DEFAULT_SLOT = "default"
SLOT = DEFAULT_SLOT


def get_active_slot() -> str:
    return SLOT


def set_active_slot(slot: str) -> None:
    """The one real point of control over which run every persist/load
    call below operates on. Callers that switch this must do so while
    holding GameState's own lock for the entire switch (see
    app/state.py's switch_run()/create_run()) so no concurrent tick or
    request can persist mid-switch using the wrong slot."""
    global SLOT
    SLOT = slot

# Bump this whenever a change to GameSaveState (or anything nested inside
# it) could make an older save fail validation. It's purely a diagnostic
# breadcrumb recorded on the DB row — migration itself doesn't branch on
# it, because the generic deep-merge-onto-defaults strategy below handles
# "a new field was added somewhere" uniformly, without needing a
# hand-written migration function per version. If a future change ever
# does something a deep-merge can't fix (a field renamed or restructured,
# not just added), add a targeted fixup to `_migrate_dict` and note it
# here rather than bumping this silently.
SCHEMA_VERSION = 1

# How many routine ('periodic') backups to keep per slot. Kept small
# since one is written on every persist_save() call — anything written
# because of an actual recovery ('pre_fresh_fallback') is exempt from
# this cap and kept forever.
MAX_PERIODIC_BACKUPS = 20


def _insert_backup(session: Any, *, reason: str, raw_data: str) -> None:
    session.add(SaveBackup(slot=SLOT, reason=reason, data=raw_data, created_at=datetime.now(timezone.utc)))
    if reason == "periodic":
        # The session has autoflush disabled, so without an explicit flush
        # here the row just added above wouldn't be visible to the count
        # query below yet, undercounting by one and leaving the table one
        # row over MAX_PERIODIC_BACKUPS after every call.
        session.flush()
        ids = [
            row.id
            for row in session.query(SaveBackup.id)
            .filter_by(slot=SLOT, reason="periodic")
            .order_by(SaveBackup.created_at.desc())
            .all()
        ]
        stale_ids = ids[MAX_PERIODIC_BACKUPS:]
        if stale_ids:
            session.query(SaveBackup).filter(SaveBackup.id.in_(stale_ids)).delete(synchronize_session=False)


def _deep_merge_defaults(old: Any, default: Any) -> Any:
    """Fills in anything the current schema requires that `old` is missing,
    recursively, while otherwise preferring `old`'s real values. Only
    recurses into dicts (agents keyed by id, nested objects like
    paperPortfolio/companyScore) — lists (trade history, decisions,
    research, memory, ...) are taken wholesale from `old` when present,
    since those are real records to preserve, not something to merge
    against an empty default list. This is why every field added to a
    model that lives inside one of those lists must have a default value
    (see PaperTrade.opened_sim_minutes for the pattern) — Pydantic fills
    those in per-item during validation; this function only needs to
    handle the outer, dict-shaped structure."""
    if isinstance(default, dict) and isinstance(old, dict):
        merged = dict(default)
        for key, old_value in old.items():
            merged[key] = _deep_merge_defaults(old_value, default[key]) if key in default else old_value
        return merged
    return old


def _migrate_dict(raw: dict[str, Any]) -> GameSaveState | None:
    """Attempts to bring an old, schema-incompatible save dict up to the
    current shape by deep-merging it onto a fresh default state (see
    `_deep_merge_defaults`), then re-validating. Returns None if the
    result still doesn't validate — e.g. `raw` isn't even a recognizable
    GameSaveState shape at all, not just missing a field."""
    fresh = default_state().model_dump(by_alias=True)
    merged = _deep_merge_defaults(raw, fresh)
    try:
        return GameSaveState.model_validate(merged)
    except ValidationError as exc:
        logger.error("Migration attempt failed even after merging onto defaults: %s", exc)
        return None


def load_save() -> GameSaveState | None:
    """Returns None only when there is genuinely no usable save to load —
    either no row exists yet (fresh deployment) or a row exists but is
    unrecoverable even after a migration attempt (in which case the raw
    payload is preserved in `save_backups` before this returns None, so
    the caller's "start fresh" response never destroys the only copy of
    the data)."""
    session = get_session()
    try:
        row = session.query(SaveGame).filter_by(slot=SLOT).one_or_none()
        if row is None:
            return None

        try:
            parsed = json.loads(row.data)
        except json.JSONDecodeError:
            logger.error("Stored save is not valid JSON; backing it up and starting fresh.")
            _insert_backup(session, reason="pre_fresh_fallback", raw_data=row.data)
            session.commit()
            return None

        try:
            return GameSaveState.model_validate(parsed)
        except ValidationError:
            pass

        logger.warning(
            "Stored save doesn't match the current schema (likely from an older version) — "
            "attempting migration instead of discarding it."
        )
        migrated = _migrate_dict(parsed) if isinstance(parsed, dict) else None
        if migrated is not None:
            logger.info("Migration succeeded; the recovered save will be re-persisted in its new shape.")
            return migrated

        logger.error("Save could not be migrated; backing up the raw payload and starting fresh.")
        _insert_backup(session, reason="pre_fresh_fallback", raw_data=row.data)
        session.commit()
        return None
    finally:
        session.close()


def persist_save(state: GameSaveState) -> None:
    """Legacy single-blob write path. No longer called on the hot path (see
    persist_modules() below) — kept only so a pre-Phase-2 deployment's
    `saves` row can still be read and migrated once by load_state(), and so
    `_migrate_dict`'s existing tests keep exercising real code."""
    session = get_session()
    try:
        payload = state.model_dump_json(by_alias=True)
        row = session.query(SaveGame).filter_by(slot=SLOT).one_or_none()
        if row is None:
            row = SaveGame(slot=SLOT, data=payload, updated_at=datetime.now(timezone.utc), schema_version=SCHEMA_VERSION)
            session.add(row)
        else:
            row.data = payload
            row.updated_at = datetime.now(timezone.utc)
            row.schema_version = SCHEMA_VERSION
        _insert_backup(session, reason="periodic", raw_data=payload)
        session.commit()
    finally:
        session.close()


def _hash(payload: str) -> str:
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def persist_modules(state: GameSaveState) -> list[ModuleWriteResult]:
    """v0.7 Save Architecture Redesign Phase 2 — the real primary write path.

    Splits `state` into the modules from app/save_modules.py and writes each
    to its own SaveModule row, independently. Two requirements from the
    spec, both handled here:

    - "Delta system / only save what changed": each module's JSON is
      SHA-256 hashed and compared against the hash already stored for that
      (slot, module) row; an unchanged module is skipped entirely (no
      write, bytes_written=0 in its result). This is the real per-tick win
      — most modules don't change most ticks (research/settings/founders
      can go many ticks untouched even while `derived`/`world` change every
      tick), unlike the old single-blob persist_save() which rewrote all
      ~840KB every single time regardless of what changed.
    - "Save recovery: if one module fails, others still save": each
      module's write happens inside its own SAVEPOINT
      (session.begin_nested()), so a failure writing one module rolls back
      only that module's change and lets the loop continue to the rest,
      all still committed together at the end.

    A periodic full-state backup (save_backups, reused from the legacy
    path) is taken only when at least one module actually changed — an
    unchanged tick costs nothing, same as the module writes themselves.
    """
    modules = split_state(state)
    session = get_session()
    results: list[ModuleWriteResult] = []
    any_changed = False
    try:
        for module in ALL_MODULES:
            try:
                payload = json.dumps(modules[module], separators=(",", ":"))
                digest = _hash(payload)
                with session.begin_nested():
                    row = session.query(SaveModule).filter_by(slot=SLOT, module=module).one_or_none()
                    if row is not None and row.data_hash == digest:
                        results.append(ModuleWriteResult(name=module, ok=True, bytesWritten=0))
                        continue
                    now = datetime.now(timezone.utc)
                    if row is None:
                        session.add(SaveModule(slot=SLOT, module=module, data=payload, data_hash=digest, updated_at=now))
                    else:
                        row.data = payload
                        row.data_hash = digest
                        row.updated_at = now
                    session.flush()
                any_changed = True
                results.append(ModuleWriteResult(name=module, ok=True, bytesWritten=len(payload)))
            except Exception as exc:
                logger.error("Failed to persist save module %r: %s", module, exc)
                results.append(ModuleWriteResult(name=module, ok=False, error=str(exc)))

        if any_changed:
            _insert_backup(session, reason="periodic", raw_data=state.model_dump_json(by_alias=True))
        session.commit()
    finally:
        session.close()
    return results


def load_modules() -> GameSaveState | None:
    """Reads every SaveModule row for the slot and assembles them back into
    one GameSaveState. Returns None only if no module rows exist at all
    (nothing has been migrated/persisted yet — see load_state() below).

    Recovery is layered, cheapest first:
    - A single module row with corrupt (non-JSON) `data` is logged and
      dropped from the merge; assemble_state() fills that one module back
      in from module_defaults() rather than failing the whole load.
    - If the fully assembled dict still doesn't validate against the
      current schema (a module's *shape* predates a field added inside
      it), fall back to the same deep-merge-onto-full-defaults migration
      persist_save()'s legacy path already uses, applied to the
      reassembled dict — same guarantee, just fed from modules instead of
      one blob.
    - If even that fails, every raw module row is backed up (never
      silently discarded) and this returns None, so the caller starts a
      fresh default state instead of crashing.
    """
    session = get_session()
    try:
        rows = session.query(SaveModule).filter_by(slot=SLOT).all()
        if not rows:
            return None

        parsed: dict[str, dict[str, Any]] = {}
        corrupt_raw: dict[str, str] = {}
        for row in rows:
            try:
                parsed[row.module] = json.loads(row.data)
            except json.JSONDecodeError:
                logger.error("Save module %r is not valid JSON; it will load from defaults instead.", row.module)
                corrupt_raw[row.module] = row.data

        try:
            return assemble_state(parsed)
        except ValidationError:
            pass

        logger.warning(
            "Assembled save modules don't match the current schema (likely from an older version) — "
            "attempting migration instead of discarding them."
        )
        fresh = default_state().model_dump(by_alias=True)
        merged = _deep_merge_defaults(merge_module_dicts(parsed), fresh)
        try:
            migrated = GameSaveState.model_validate(merged)
            logger.info("Migration succeeded; the recovered save will be re-persisted in its new shape.")
            return migrated
        except ValidationError as exc:
            logger.error("Save modules could not be migrated even after merging onto defaults: %s", exc)

        for row in rows:
            _insert_backup(session, reason="pre_fresh_fallback", raw_data=corrupt_raw.get(row.module, row.data))
        session.commit()
        return None
    finally:
        session.close()


def load_state() -> GameSaveState | None:
    """The real startup entry point (see main.py). Prefers the new
    per-module tables; if none exist yet, falls back to the legacy
    single-blob `saves` row (pre-Phase-2 deployment) and migrates it into
    modules exactly once so every future persist uses persist_modules()."""
    modules_state = load_modules()
    if modules_state is not None:
        return modules_state

    legacy = load_save()
    if legacy is not None:
        logger.info("Migrating legacy single-blob save into the new per-module tables.")
        persist_modules(legacy)
        return legacy

    return None


def read_module_for_slot(slot: str, module: str) -> dict[str, Any] | None:
    """Read-only, single-module fetch for an ARBITRARY slot — deliberately
    independent of the mutable `SLOT` pointer above (never reads or writes
    it), so this is always safe to call from `list_runs()` even while a
    different run is the one actually active and ticking. Returns None if
    that slot has no row for this module, or the stored JSON is corrupt
    (an honest "unavailable," never a fabricated empty dict)."""
    session = get_session()
    try:
        row = session.query(SaveModule).filter_by(slot=slot, module=module).one_or_none()
        if row is None:
            return None
        try:
            result: dict[str, Any] = json.loads(row.data)
            return result
        except json.JSONDecodeError:
            return None
    finally:
        session.close()


def register_run(run_id: str, display_name: str) -> None:
    """Registers a new real, persisted run identity. Idempotent — calling
    this again for a `run_id` that's already registered updates nothing
    (the row already exists); it never creates a duplicate row, since
    `run_id` is a real, unique, indexed column."""
    session = get_session()
    try:
        existing = session.query(Run).filter_by(run_id=run_id).one_or_none()
        if existing is not None:
            return
        now = datetime.now(timezone.utc)
        session.add(Run(run_id=run_id, display_name=display_name, created_at=now, last_played_at=now))
        session.commit()
    finally:
        session.close()


def touch_run_last_played(run_id: str) -> None:
    session = get_session()
    try:
        row = session.query(Run).filter_by(run_id=run_id).one_or_none()
        if row is not None:
            row.last_played_at = datetime.now(timezone.utc)
            session.commit()
    finally:
        session.close()


def list_runs() -> list[RunSummary]:
    """Every real, registered run, most-recently-played first. Each
    entry's `current_day` is read live from that run's own real `world`
    module (via `read_module_for_slot()`, never the mutable `SLOT`
    pointer) — never cached on the `Run` row itself, so it can never go
    stale relative to that run's own real save data."""
    session = get_session()
    try:
        rows = session.query(Run).order_by(Run.last_played_at.desc()).all()
        summaries: list[RunSummary] = []
        for row in rows:
            world = read_module_for_slot(row.run_id, "world")
            current_day: int | None = None
            if world is not None:
                time_field = world.get("time")
                if isinstance(time_field, dict) and isinstance(time_field.get("day"), int):
                    current_day = time_field["day"]
            summaries.append(
                RunSummary(
                    runId=row.run_id,
                    displayName=row.display_name,
                    createdAt=row.created_at.isoformat(),
                    lastPlayedAt=row.last_played_at.isoformat(),
                    currentDay=current_day,
                )
            )
        return summaries
    finally:
        session.close()


def run_exists(run_id: str) -> bool:
    session = get_session()
    try:
        return session.query(Run).filter_by(run_id=run_id).one_or_none() is not None
    finally:
        session.close()


def generate_run_id() -> str:
    return f"run-{uuid.uuid4().hex[:12]}"


def get_active_run_id() -> str:
    """The real, persisted pointer to which registered run should load on
    startup — read once at boot (see main.py's lifespan()) so a backend
    restart resumes the same run the player was last on, rather than
    silently reverting to DEFAULT_SLOT. Falls back to DEFAULT_SLOT only
    when no row has ever been written yet (a genuinely fresh deployment,
    or one from before this feature existed)."""
    session = get_session()
    try:
        row = session.query(ActiveRun).filter_by(id=1).one_or_none()
        return row.run_id if row is not None else DEFAULT_SLOT
    finally:
        session.close()


def set_active_run_pointer(run_id: str) -> None:
    session = get_session()
    try:
        row = session.query(ActiveRun).filter_by(id=1).one_or_none()
        if row is None:
            session.add(ActiveRun(id=1, run_id=run_id))
        else:
            row.run_id = run_id
        session.commit()
    finally:
        session.close()


def ensure_default_run_registered() -> None:
    """Called once at startup (main.py's lifespan(), before the active
    slot is resolved). If the `runs` registry is empty AND real save data
    already exists at DEFAULT_SLOT (a deployment from before this feature
    existed — exactly the case that must preserve an existing long-running
    save, never reset or fabricate it), registers that existing save as a
    real run named "Original Run" — using the real current time as its
    `created_at`/`last_played_at`, since this codebase has no record of
    when that save actually began (never fabricated as an earlier date).
    Idempotent: a no-op once any run is registered. A genuinely fresh
    deployment with no existing save registers nothing here — its first
    real run gets created the normal way, the first time one is."""
    session = get_session()
    try:
        any_run = session.query(Run.id).first()
    finally:
        session.close()
    if any_run is not None:
        return

    previous_slot = SLOT
    set_active_slot(DEFAULT_SLOT)
    try:
        existing = load_state()
    finally:
        set_active_slot(previous_slot)
    if existing is not None:
        register_run(DEFAULT_SLOT, "Original Run")
