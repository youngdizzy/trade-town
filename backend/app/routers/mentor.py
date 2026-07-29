"""Sage's QuestionOfTheDay response endpoint (v0.7 Feature 32) — see
app/mentor.py's module docstring for what this does and doesn't do
(never graded; see its "Daily Thinking Bonus" cut).
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.persistence import persist_modules
from app.schemas import QuestionOfTheDay
from app.state import game_state

router = APIRouter(prefix="/api/mentor", tags=["mentor"])


class SubmitQotdResponseRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    question_id: str = Field(alias="questionId")
    response: str


class SubmitQotdResponseResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    question: QuestionOfTheDay


@router.post("/qotd/respond", response_model=SubmitQotdResponseResponse)
async def submit_qotd_response(payload: SubmitQotdResponseRequest) -> SubmitQotdResponseResponse:
    state, error = await game_state.submit_qotd_response(payload.question_id, payload.response)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    question = next(q for q in state.question_archive if q.id == payload.question_id)
    return SubmitQotdResponseResponse(question=question)
