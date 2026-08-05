"""CEO Goal endpoints (v0.7 Design Bible Chapter 64) — create and cancel
a company goal. Real progress is never written here; it's recomputed
every tick by app/nexus.py's tick_goals() and simply read back on the
next /api/load or WS broadcast, the same "server-authoritative, no
client-computed number" convention every other real system in this
codebase already follows.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.goals import compute_resource_allocation, rank_goals_by_priority
from app.persistence import persist_modules
from app.schemas import Goal, GoalAllocation, GoalCategory, GoalMetric, GoalPriority
from app.state import game_state

router = APIRouter(prefix="/api/goals", tags=["goals"])


class CreateGoalRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    title: str
    category: GoalCategory
    target_metric: GoalMetric = Field(alias="targetMetric")
    target_value: float = Field(alias="targetValue")
    deadline_sim_day: int | None = Field(default=None, alias="deadlineSimDay")


class CancelGoalRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    goal_id: str = Field(alias="goalId")


class GoalsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    goals: list[Goal]


@router.post("/create", response_model=GoalsResponse)
async def create_goal(payload: CreateGoalRequest) -> GoalsResponse:
    state, error = await game_state.create_goal(
        title=payload.title,
        category=payload.category,
        target_metric=payload.target_metric,
        target_value=payload.target_value,
        deadline_sim_day=payload.deadline_sim_day,
    )
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return GoalsResponse(goals=state.goals)


@router.post("/cancel", response_model=GoalsResponse)
async def cancel_goal(payload: CancelGoalRequest) -> GoalsResponse:
    state, error = await game_state.cancel_goal(payload.goal_id)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return GoalsResponse(goals=state.goals)


@router.get("/priorities", response_model=list[GoalPriority])
async def goal_priorities() -> list[GoalPriority]:
    """Design Bible Chapter 64 (third pass) — the Executive Priority
    Engine. Computed fresh per request from the current real goals and
    sim day, never a second persisted/driftable copy — see
    app/goals.py's rank_goals_by_priority()."""
    state = await game_state.snapshot()
    return rank_goals_by_priority(state.goals, sim_day=state.time.day)


@router.get("/allocations", response_model=list[GoalAllocation])
async def goal_allocations() -> list[GoalAllocation]:
    """Design Bible Chapter 64 (fourth pass) — Resource Allocation. A
    recommend-only share of executive ATTENTION across active goals,
    computed fresh per request from the same real Priority Engine
    scores above — never a second persisted/driftable copy, and never a
    claim about real capital movement. See app/goals.py's
    compute_resource_allocation() for why."""
    state = await game_state.snapshot()
    return compute_resource_allocation(state.goals, sim_day=state.time.day)
