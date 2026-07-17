from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter

from app.persistence import persist_save
from app.schemas import GameSaveState, SaveResponse
from app.state import game_state

router = APIRouter(prefix="/api", tags=["save"])


@router.get("/load", response_model=GameSaveState)
async def load_game() -> GameSaveState:
    """Returns the current authoritative game state (server-tracked agents/tasks/
    time, plus the last-known player position/settings/dialogue). There is always
    a valid state to return — a fresh deployment simply returns sensible defaults."""
    return await game_state.snapshot()


@router.post("/save", response_model=SaveResponse)
async def save_game(payload: GameSaveState) -> SaveResponse:
    state = await game_state.apply_client_save(payload)
    persist_save(state)
    return SaveResponse(updatedAt=datetime.now(timezone.utc).isoformat())
