"""The Company Constitution (v0.7 Feature 46). See app/constitution.py's
module docstring for what this feature builds vs. deliberately cuts.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.persistence import persist_modules
from app.schemas import ConstitutionState
from app.state import game_state

router = APIRouter(prefix="/api/constitution", tags=["constitution"])


class ConstitutionStateResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    constitution: ConstitutionState


class ProposeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str
    text: str


class AmendmentIdRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    amendment_id: str = Field(alias="amendmentId")


class DecideRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    amendment_id: str = Field(alias="amendmentId")
    approve: bool


@router.post("/propose", response_model=ConstitutionStateResponse)
async def propose(payload: ProposeRequest) -> ConstitutionStateResponse:
    state, error = await game_state.propose_constitution_amendment(payload.title, payload.text)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return ConstitutionStateResponse(constitution=state.constitution)


@router.post("/advance", response_model=ConstitutionStateResponse)
async def advance(payload: AmendmentIdRequest) -> ConstitutionStateResponse:
    state, error = await game_state.advance_constitution_amendment(payload.amendment_id)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return ConstitutionStateResponse(constitution=state.constitution)


@router.post("/decide", response_model=ConstitutionStateResponse)
async def decide(payload: DecideRequest) -> ConstitutionStateResponse:
    state, error = await game_state.decide_constitution_amendment(payload.amendment_id, payload.approve)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return ConstitutionStateResponse(constitution=state.constitution)
