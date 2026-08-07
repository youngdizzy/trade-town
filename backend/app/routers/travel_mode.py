"""Design Bible Chapter 73.5 — Mobile Command Center & Remote
Operations. See app/travel_mode.py's module docstring for the full
honesty boundary. TravelModeState/TravelModeBriefing are real,
already-persisted GameSaveState.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.schemas import NotificationSensitivity, TravelModeBriefing, TravelModeState
from app.state import game_state

router = APIRouter(prefix="/api/travel-mode", tags=["travel-mode"])


class UpdateTravelModeSettingsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    position_size_cap_pct: float | None = Field(default=None, alias="positionSizeCapPct")
    daily_risk_cap_pct: float | None = Field(default=None, alias="dailyRiskCapPct")
    notification_sensitivity: NotificationSensitivity | None = Field(default=None, alias="notificationSensitivity")
    auto_activate_enabled: bool | None = Field(default=None, alias="autoActivateEnabled")
    auto_activate_after_minutes: int | None = Field(default=None, alias="autoActivateAfterMinutes")


@router.get("", response_model=TravelModeState)
async def get_travel_mode() -> TravelModeState:
    state = await game_state.snapshot()
    return state.travel_mode


@router.post("/activate", response_model=TravelModeState)
async def post_activate_travel_mode() -> TravelModeState:
    state, error = await game_state.activate_travel_mode()
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    return state.travel_mode


@router.post("/deactivate", response_model=TravelModeBriefing)
async def post_deactivate_travel_mode() -> TravelModeBriefing:
    state, error = await game_state.deactivate_travel_mode()
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    return state.travel_mode_briefings[-1]


@router.patch("/settings", response_model=TravelModeState)
async def patch_travel_mode_settings(payload: UpdateTravelModeSettingsRequest) -> TravelModeState:
    update = payload.model_dump(exclude_unset=True, exclude_none=True)
    state, error = await game_state.update_travel_mode_settings(update)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    return state.travel_mode
