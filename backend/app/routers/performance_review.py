"""CEO directive "Features 26-30," Feature 27 — read-only endpoints over
Agent Performance Reviews, mirroring routers/institutional_memory.py's
own convention: `await game_state.snapshot()`, computed fresh every
call, nothing here mutates the save. The full list is already broadcast
on every WS tick (see app/ws_manager.py's `agentPerformanceReviews`
field) — this router adds the one genuinely new query the broadcast
can't offer cheaply on the frontend: "what's this one agent's latest
real review."
"""
from __future__ import annotations

from fastapi import APIRouter, Path

from app.performance_review import classify_review_data_splits, latest_review_for_agent
from app.schemas import AgentId, AgentPerformanceReview, AgentPerformanceReviewHistoryEntry
from app.state import game_state

router = APIRouter(prefix="/api/performance-reviews", tags=["performance-reviews"])


@router.get("/{agent_id}/latest", response_model=AgentPerformanceReview | None)
async def latest_review(agent_id: AgentId = Path(...)) -> AgentPerformanceReview | None:
    """The most recent real AgentPerformanceReview on file for this
    agent, or null if none has been generated yet (reviews are only
    generated weekly — see app/nexus.py's tick)."""
    state = await game_state.snapshot()
    return latest_review_for_agent(state.agent_performance_reviews, agent_id)


@router.get("/{agent_id}/history", response_model=list[AgentPerformanceReviewHistoryEntry])
async def review_history(agent_id: AgentId = Path(...)) -> list[AgentPerformanceReviewHistoryEntry]:
    """CEO directive "Professional Quant Firm Phase 41-45," Feature 44 —
    this agent's full stored review history, each paired with a real,
    freshly computed `AgentReviewDataSplit` (see app/performance_
    review.py's classify_review_data_splits() for the exact,
    non-shuffled chronological rule). Oldest first, matching storage
    order. A preventive labeling layer, not a fix for an existing leak
    — see that function's own docstring and AgentReviewDataSplit's
    schema docstring for the full disclosure."""
    state = await game_state.snapshot()
    reviews_for_agent = [r for r in state.agent_performance_reviews if r.agent_id == agent_id]
    return classify_review_data_splits(reviews_for_agent)
