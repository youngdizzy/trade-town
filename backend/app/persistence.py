"""Reads/writes the single authoritative GameSaveState row to SQLite."""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from pydantic import ValidationError

from app.db import get_session
from app.models import SaveGame
from app.schemas import GameSaveState

logger = logging.getLogger("tradetown.persistence")

SLOT = "default"


def load_save() -> GameSaveState | None:
    """Returns None (treated as "no save yet") both when nothing is stored and when
    a stored row doesn't match the current schema — e.g. a v0.1 save (no `agents`
    field) found after upgrading to v0.2. We intentionally don't migrate old saves;
    the app just starts fresh rather than crashing on an incompatible shape."""
    session = get_session()
    try:
        row = session.query(SaveGame).filter_by(slot=SLOT).one_or_none()
        if row is None:
            return None
        try:
            return GameSaveState.model_validate_json(row.data)
        except ValidationError:
            logger.warning("Stored save doesn't match the current schema (likely from an older version); starting fresh.")
            return None
    finally:
        session.close()


def persist_save(state: GameSaveState) -> None:
    session = get_session()
    try:
        row = session.query(SaveGame).filter_by(slot=SLOT).one_or_none()
        payload = state.model_dump_json(by_alias=True)
        if row is None:
            row = SaveGame(slot=SLOT, data=payload, updated_at=datetime.now(timezone.utc))
            session.add(row)
        else:
            row.data = payload
            row.updated_at = datetime.now(timezone.utc)
        session.commit()
    finally:
        session.close()
