"""Design Bible Chapter 74.5 — CEO Vision Board & Strategic Alignment
Engine. See app/vision_board.py's own module docstring for what's real
vs. explicitly deferred.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.persistence import persist_modules
from app.schemas import VisionAlignmentScore, VisionBoardState, VisionSelfCorrectionNote
from app.state import game_state
from app.vision_board import (
    compute_constitution_amendment_alignment,
    compute_goal_alignment,
    compute_self_correction_note,
)

router = APIRouter(prefix="/api/vision-board", tags=["vision-board"])


class SetMissionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mission: str | None = None


class SetIdentityNoteRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    identity_note: str | None = Field(default=None, alias="identityNote")


class SetPrioritiesRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    priorities: list[str]


class AddObjectiveRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    text: str
    category: str


@router.get("", response_model=VisionBoardState)
async def get_vision_board() -> VisionBoardState:
    state = await game_state.snapshot()
    return state.vision_board


@router.post("/mission", response_model=VisionBoardState)
async def set_mission(payload: SetMissionRequest) -> VisionBoardState:
    state = await game_state.set_vision_board_mission(payload.mission)
    persist_modules(state)
    return state.vision_board


@router.post("/identity-note", response_model=VisionBoardState)
async def set_identity_note(payload: SetIdentityNoteRequest) -> VisionBoardState:
    state = await game_state.set_vision_board_identity_note(payload.identity_note)
    persist_modules(state)
    return state.vision_board


@router.post("/priorities", response_model=VisionBoardState)
async def set_priorities(payload: SetPrioritiesRequest) -> VisionBoardState:
    state, error = await game_state.set_vision_board_priorities(payload.priorities)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return state.vision_board


@router.post("/objectives", response_model=VisionBoardState)
async def add_objective(payload: AddObjectiveRequest) -> VisionBoardState:
    state, error = await game_state.add_vision_board_objective(payload.text, payload.category)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return state.vision_board


@router.delete("/objectives/{objective_id}", response_model=VisionBoardState)
async def remove_objective(objective_id: str) -> VisionBoardState:
    state = await game_state.remove_vision_board_objective(objective_id)
    persist_modules(state)
    return state.vision_board


@router.get("/alignment/goal/{goal_id}", response_model=VisionAlignmentScore)
async def get_goal_alignment(goal_id: str) -> VisionAlignmentScore:
    state = await game_state.snapshot()
    goal = next((g for g in state.goals if g.id == goal_id), None)
    if goal is None:
        raise HTTPException(status_code=404, detail="No goal found with that id.")
    return compute_goal_alignment(goal, state.vision_board)


@router.get(
    "/alignment/constitution-amendment/{amendment_id}", response_model=VisionAlignmentScore
)
async def get_constitution_amendment_alignment(amendment_id: str) -> VisionAlignmentScore:
    state = await game_state.snapshot()
    amendment = next((a for a in state.constitution.amendments if a.id == amendment_id), None)
    if amendment is None:
        raise HTTPException(status_code=404, detail="No constitution amendment found with that id.")
    return compute_constitution_amendment_alignment(amendment, state.vision_board)


@router.get("/self-correction", response_model=VisionSelfCorrectionNote)
async def get_self_correction_note() -> VisionSelfCorrectionNote:
    state = await game_state.snapshot()
    return compute_self_correction_note(state.vision_board, state.daily_circuit_breaker.tier)
