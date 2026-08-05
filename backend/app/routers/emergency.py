"""Design Bible Chapter 67 (TTOS) Part 3 — the real Global Emergency
Stop endpoints. See app/emergency_stop.py's module docstring for exactly
what activating/resuming blocks and does not block.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.persistence import persist_modules
from app.schemas import EmergencyStopState
from app.state import game_state

router = APIRouter(prefix="/api/emergency-stop", tags=["emergency"])


class EmergencyStopResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    emergency_stop: EmergencyStopState = Field(alias="emergencyStop")


@router.post("/activate", response_model=EmergencyStopResponse)
async def activate() -> EmergencyStopResponse:
    state, error = await game_state.activate_emergency_stop()
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return EmergencyStopResponse(emergencyStop=state.emergency_stop)


@router.post("/resume", response_model=EmergencyStopResponse)
async def resume() -> EmergencyStopResponse:
    state, error = await game_state.resume_trading()
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return EmergencyStopResponse(emergencyStop=state.emergency_stop)
