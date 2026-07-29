"""The CEO Research Dashboard / Black Box Dashboard (v0.7 — the Advanced
Quantitative Research Division). See app/black_box.py's module docstring
for what this feature extends vs. builds new.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.persistence import persist_modules
from app.schemas import AgentId, BlackBoxPriority, BlackBoxState
from app.state import game_state

router = APIRouter(prefix="/api/black-box", tags=["black-box"])


class BlackBoxStateResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    black_box: BlackBoxState = Field(alias="blackBox")


class FundRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    amount: float


class PriorityRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    priority: BlackBoxPriority


class NoteRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    note: str


class ReassignRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    agent_id: AgentId = Field(alias="agentId")
    new_agent_id: AgentId = Field(alias="newAgentId")


class AckBreakthroughRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    review_id: str = Field(alias="reviewId")


class AckBreakthroughResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    viewed_breakthrough_ids: list[str] = Field(alias="viewedBreakthroughIds")


@router.post("/fund", response_model=BlackBoxStateResponse)
async def fund_project(payload: FundRequest) -> BlackBoxStateResponse:
    state, error = await game_state.fund_black_box_project(payload.amount)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return BlackBoxStateResponse(blackBox=state.black_box)


@router.post("/pause", response_model=BlackBoxStateResponse)
async def pause_project() -> BlackBoxStateResponse:
    state, error = await game_state.set_black_box_paused(True)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return BlackBoxStateResponse(blackBox=state.black_box)


@router.post("/resume", response_model=BlackBoxStateResponse)
async def resume_project() -> BlackBoxStateResponse:
    state, error = await game_state.set_black_box_paused(False)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return BlackBoxStateResponse(blackBox=state.black_box)


@router.post("/cancel", response_model=BlackBoxStateResponse)
async def cancel_project() -> BlackBoxStateResponse:
    state, error = await game_state.cancel_black_box_project()
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return BlackBoxStateResponse(blackBox=state.black_box)


@router.post("/priority", response_model=BlackBoxStateResponse)
async def set_priority(payload: PriorityRequest) -> BlackBoxStateResponse:
    state, error = await game_state.set_black_box_priority(payload.priority)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return BlackBoxStateResponse(blackBox=state.black_box)


@router.post("/notes", response_model=BlackBoxStateResponse)
async def add_note(payload: NoteRequest) -> BlackBoxStateResponse:
    state, error = await game_state.add_black_box_note(payload.note)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return BlackBoxStateResponse(blackBox=state.black_box)


@router.post("/reassign", response_model=BlackBoxStateResponse)
async def reassign_specialist(payload: ReassignRequest) -> BlackBoxStateResponse:
    state, error = await game_state.reassign_black_box_specialist(payload.agent_id, payload.new_agent_id)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return BlackBoxStateResponse(blackBox=state.black_box)


@router.post("/ack-breakthrough", response_model=AckBreakthroughResponse)
async def ack_breakthrough(payload: AckBreakthroughRequest) -> AckBreakthroughResponse:
    viewed_ids = await game_state.ack_breakthrough(payload.review_id)
    persist_modules(await game_state.snapshot())
    return AckBreakthroughResponse(viewedBreakthroughIds=viewed_ids)
