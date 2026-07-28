"""CEO Calendar endpoints (v0.7 Feature 36) — player-created custom
calendar entries only; the real system-computed cadence events are part
of every state broadcast (see app/calendar.py's own module docstring),
so there's nothing to fetch separately for those.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.persistence import persist_save
from app.schemas import CalendarState, PlayerEventCategory
from app.state import game_state

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


class CreateEventRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    category: PlayerEventCategory
    title: str
    day: int
    hour: int
    minute: int = 0


class DeleteEventRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    event_id: str = Field(alias="eventId")


class CalendarResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    calendar: CalendarState


@router.post("/events/create", response_model=CalendarResponse)
async def create_event(payload: CreateEventRequest) -> CalendarResponse:
    state, error = await game_state.create_calendar_event(payload.category, payload.title, payload.day, payload.hour, payload.minute)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_save(state)
    return CalendarResponse(calendar=state.calendar)


@router.post("/events/delete", response_model=CalendarResponse)
async def delete_event(payload: DeleteEventRequest) -> CalendarResponse:
    state, error = await game_state.delete_calendar_event(payload.event_id)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_save(state)
    return CalendarResponse(calendar=state.calendar)
