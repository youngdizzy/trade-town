"""Trading Education endpoints (v0.6.2 Phase 9) — see app/education.py
for the curriculum and grading. GET returns the static lesson list
(never mutates state, no lock needed); the two POSTs update real
persisted progress, so both go through game_state and persist_save, the
same "a real progress event" reasoning already applied elsewhere.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.education import all_lessons
from app.persistence import persist_save
from app.schemas import EducationLesson, EducationProgress
from app.state import game_state

router = APIRouter(prefix="/api/education", tags=["education"])


class ViewLessonRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    lesson_id: str = Field(alias="lessonId")


class ViewLessonResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    education: EducationProgress


class SubmitQuizRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    lesson_id: str = Field(alias="lessonId")
    selected_index: int = Field(alias="selectedIndex")


class SubmitQuizResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    correct: bool
    correct_index: int = Field(alias="correctIndex")
    correct_option: str = Field(alias="correctOption")
    education: EducationProgress


@router.get("/lessons", response_model=list[EducationLesson])
async def get_lessons() -> list[EducationLesson]:
    return all_lessons()


@router.post("/view", response_model=ViewLessonResponse)
async def view_lesson(payload: ViewLessonRequest) -> ViewLessonResponse:
    progress = await game_state.mark_lesson_viewed(payload.lesson_id)
    persist_save(await game_state.snapshot())
    return ViewLessonResponse(education=progress)


@router.post("/quiz", response_model=SubmitQuizResponse)
async def submit_quiz(payload: SubmitQuizRequest) -> SubmitQuizResponse:
    result = await game_state.submit_education_quiz(payload.lesson_id, payload.selected_index)
    if result is None:
        raise HTTPException(status_code=400, detail=f"Unknown lesson {payload.lesson_id!r}.")
    progress, correct, correct_index, correct_option = result
    persist_save(await game_state.snapshot())
    return SubmitQuizResponse(correct=correct, correctIndex=correct_index, correctOption=correct_option, education=progress)
