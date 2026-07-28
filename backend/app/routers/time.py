"""CEO time control endpoints (v0.7 Feature 34) — see
GameState.advance_time()'s own docstring for why this loops real ticks
rather than jumping the clock directly.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict

from app.persistence import persist_save
from app.schemas import GameSaveState, TimeAdvanceTarget
from app.state import game_state

router = APIRouter(prefix="/api/time", tags=["time"])


class AdvanceTimeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    target: TimeAdvanceTarget
    hours: int | None = None


@router.post("/advance", response_model=GameSaveState)
async def advance_time(payload: AdvanceTimeRequest) -> GameSaveState:
    """A fast-forward can touch everything nexus.tick() touches across
    many real ticks (agents, research, trades, reports, treasury, ...) —
    returns the full GameSaveState (the same shape GET /api/load and the
    WS "state" broadcast use) rather than just the new time, so the
    client can apply it in one step instead of showing a stale UI for up
    to one real-time tick interval."""
    state, error = await game_state.advance_time(payload.target, payload.hours)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_save(state)
    return state
