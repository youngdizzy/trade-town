"""The Foundational Mentor Program / Professional Academy's endpoints
(v0.7 Feature 49, Phase 3 — revised so employees, not the CEO, are the
real students) — see app/foundational_mentors.py's module docstring for
the full content-attribution boundary, the employee auto-progression
engine, and what's real vs. roadmap. `/view` and `/quiz` below operate
on the CEO's own entirely optional personal learning progress
(`ceoProgress`) — real employee progress advances automatically every
tick and is never driven by these two endpoints.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.persistence import persist_modules
from app.schemas import AgentId, FoundationalMentorId, FoundationalMentorState, FoundationalResourceType
from app.state import game_state

router = APIRouter(prefix="/api/foundational-mentors", tags=["foundational-mentors"])


class FoundationalMentorStateResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    foundational_mentor_state: FoundationalMentorState = Field(alias="foundationalMentorState")


class QuizResultResponse(FoundationalMentorStateResponse):
    correct: bool
    correct_index: int = Field(alias="correctIndex")
    correct_option: str = Field(alias="correctOption")


class ApproveGraduationResponse(FoundationalMentorStateResponse):
    company_graduated: bool = Field(alias="companyGraduated")


class ViewLessonRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mentor_id: FoundationalMentorId = Field(alias="mentorId")
    lesson_id: str = Field(alias="lessonId")


class QuizRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mentor_id: FoundationalMentorId = Field(alias="mentorId")
    lesson_id: str = Field(alias="lessonId")
    selected_index: int = Field(alias="selectedIndex")


class MentorIdRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mentor_id: FoundationalMentorId = Field(alias="mentorId")


class ApproveGraduationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    agent_id: AgentId = Field(alias="agentId")
    mentor_id: FoundationalMentorId = Field(alias="mentorId")


class AddResourceRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mentor_id: FoundationalMentorId = Field(alias="mentorId")
    title: str
    url: str | None = None
    resource_type: FoundationalResourceType = Field(alias="resourceType")


class AddMentorRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    track_label: str = Field(alias="trackLabel")
    focus_areas: list[str] = Field(alias="focusAreas")


class AddMentorResponse(FoundationalMentorStateResponse):
    mentor_id: str = Field(alias="mentorId")


class AddLessonRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mentor_id: FoundationalMentorId = Field(alias="mentorId")
    title: str
    simple_explanation: str = Field(alias="simpleExplanation")
    deeper_explanation: str = Field(alias="deeperExplanation")
    quiz_question: str = Field(alias="quizQuestion")
    quiz_options: list[str] = Field(alias="quizOptions")
    correct_index: int = Field(alias="correctIndex")


# --- The CEO's own optional personal Learning Mode (ceoProgress only) ---


@router.post("/ceo/view", response_model=FoundationalMentorStateResponse)
async def ceo_view_lesson(payload: ViewLessonRequest) -> FoundationalMentorStateResponse:
    state = await game_state.view_ceo_academy_lesson(payload.mentor_id, payload.lesson_id)
    persist_modules(state)
    return FoundationalMentorStateResponse(foundationalMentorState=state.foundational_mentor_state)


@router.post("/ceo/quiz", response_model=QuizResultResponse)
async def ceo_submit_quiz(payload: QuizRequest) -> QuizResultResponse:
    result = await game_state.grade_ceo_academy_quiz(payload.mentor_id, payload.lesson_id, payload.selected_index)
    if result is None:
        raise HTTPException(status_code=404, detail="Unknown mentor or lesson.")
    state, correct, correct_index, correct_option = result
    persist_modules(state)
    return QuizResultResponse(
        foundationalMentorState=state.foundational_mentor_state,
        correct=correct,
        correctIndex=correct_index,
        correctOption=correct_option,
    )


# --- Real CEO management actions over the real employee cohort ---


@router.post("/approve-graduation", response_model=ApproveGraduationResponse)
async def approve_graduation(payload: ApproveGraduationRequest) -> ApproveGraduationResponse:
    state, company_graduated, error = await game_state.approve_academy_graduation(payload.agent_id, payload.mentor_id)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return ApproveGraduationResponse(foundationalMentorState=state.foundational_mentor_state, companyGraduated=company_graduated)


@router.post("/revoke-graduation", response_model=FoundationalMentorStateResponse)
async def revoke_graduation(payload: ApproveGraduationRequest) -> FoundationalMentorStateResponse:
    """The Executive Action "Revoke Graduation" — remedial education, not
    deletion: the employee's certification and graduation status revert,
    their lesson/quiz progress on this track resets so they genuinely
    repeat it, and the Coach's real note explains why. Company Knowledge
    (`academy_research.py`) and the mentor track's own company-wide
    status are untouched — see revoke_employee_graduation's docstring."""
    state, error = await game_state.revoke_academy_graduation(payload.agent_id, payload.mentor_id)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return FoundationalMentorStateResponse(foundationalMentorState=state.foundational_mentor_state)


@router.post("/pause", response_model=FoundationalMentorStateResponse)
async def pause() -> FoundationalMentorStateResponse:
    state, error = await game_state.pause_academy_training()
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return FoundationalMentorStateResponse(foundationalMentorState=state.foundational_mentor_state)


@router.post("/resume", response_model=FoundationalMentorStateResponse)
async def resume() -> FoundationalMentorStateResponse:
    state, error = await game_state.resume_academy_training()
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return FoundationalMentorStateResponse(foundationalMentorState=state.foundational_mentor_state)


@router.post("/skip", response_model=FoundationalMentorStateResponse)
async def skip() -> FoundationalMentorStateResponse:
    state, error = await game_state.skip_academy_to_next_mentor()
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return FoundationalMentorStateResponse(foundationalMentorState=state.foundational_mentor_state)


@router.post("/repeat", response_model=FoundationalMentorStateResponse)
async def repeat(payload: MentorIdRequest) -> FoundationalMentorStateResponse:
    state, error = await game_state.repeat_academy_mentor(payload.mentor_id)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return FoundationalMentorStateResponse(foundationalMentorState=state.foundational_mentor_state)


@router.post("/resource", response_model=FoundationalMentorStateResponse)
async def add_resource(payload: AddResourceRequest) -> FoundationalMentorStateResponse:
    state, error = await game_state.add_foundational_mentor_resource(
        payload.mentor_id, title=payload.title, url=payload.url, resource_type=payload.resource_type
    )
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return FoundationalMentorStateResponse(foundationalMentorState=state.foundational_mentor_state)


# --- Mentor Lab: real, in-product Foundational Mentor Library expansion ---


@router.post("/add-mentor", response_model=AddMentorResponse)
async def add_mentor(payload: AddMentorRequest) -> AddMentorResponse:
    state, mentor_id, error = await game_state.add_custom_academy_mentor(name=payload.name, track_label=payload.track_label, focus_areas=payload.focus_areas)
    if error is not None or mentor_id is None:
        raise HTTPException(status_code=400, detail=error or "Could not add mentor.")
    persist_modules(state)
    return AddMentorResponse(foundationalMentorState=state.foundational_mentor_state, mentorId=mentor_id)


@router.post("/add-lesson", response_model=FoundationalMentorStateResponse)
async def add_lesson(payload: AddLessonRequest) -> FoundationalMentorStateResponse:
    state, error = await game_state.add_custom_academy_lesson(
        payload.mentor_id,
        title=payload.title,
        simple_explanation=payload.simple_explanation,
        deeper_explanation=payload.deeper_explanation,
        quiz_question=payload.quiz_question,
        quiz_options=payload.quiz_options,
        correct_index=payload.correct_index,
    )
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return FoundationalMentorStateResponse(foundationalMentorState=state.foundational_mentor_state)


@router.post("/set-active", response_model=FoundationalMentorStateResponse)
async def set_active(payload: MentorIdRequest) -> FoundationalMentorStateResponse:
    state, error = await game_state.set_active_academy_mentor(payload.mentor_id)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return FoundationalMentorStateResponse(foundationalMentorState=state.foundational_mentor_state)
