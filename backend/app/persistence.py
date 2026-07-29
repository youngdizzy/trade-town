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
"""
from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from app.db import get_session
from app.models import SaveBackup, SaveGame, SaveModule
from app.save_modules import ALL_MODULES, assemble_state, merge_module_dicts, split_state
from app.schemas import GameSaveState, ModuleWriteResult
from app.state import default_state

logger = logging.getLogger("tradetown.persistence")

SLOT = "default"

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
