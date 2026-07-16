"""Reads/writes the single authoritative GameSaveState row to SQLite."""
from __future__ import annotations

from datetime import datetime, timezone

from app.db import get_session
from app.models import SaveGame
from app.schemas import GameSaveState

SLOT = "default"


def load_save() -> GameSaveState | None:
    session = get_session()
    try:
        row = session.query(SaveGame).filter_by(slot=SLOT).one_or_none()
        if row is None:
            return None
        return GameSaveState.model_validate_json(row.data)
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
