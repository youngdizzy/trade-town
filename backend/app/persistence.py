"""Reads/writes the single authoritative GameSaveState row to SQLite.

THE BUG THIS FILE FIXES (read before changing anything here): every past
version of TradeTown has added new fields to the save schema (v0.2 added
agents, v0.3 added research/watchlist, v0.5 added trading, v0.6 added
risk/decisions, v0.6.1 added two PaperTrade fields). The *old* version of
`load_save()` treated ANY Pydantic validation failure — which is exactly
what happens when a stored save predates a newly-added field — as "no
save exists yet," returning None. `main.py`'s startup then read that None
as "fresh deployment" and immediately overwrote the existing row with a
brand-new default state, permanently destroying the real save. This was
the actual root cause of reported progress loss after every code update,
not a Docker volume problem (the volume itself was always configured
correctly — see docker-compose.yml's `tradetown-data` named volume).

The fix: `load_save()` now treats "row exists but doesn't validate" as a
recoverable case, not an empty one. It attempts a generic migration
(`_migrate_dict`) before ever giving up, and only overwrites the live row
after backing up the raw, unrecoverable payload to `save_backups` — which
is never automatically deleted.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from pydantic import ValidationError

from app.db import get_session
from app.models import SaveBackup, SaveGame
from app.schemas import GameSaveState
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
