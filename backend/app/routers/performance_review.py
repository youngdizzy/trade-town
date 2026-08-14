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

from app.performance_review import latest_review_for_agent
from app.schemas import AgentId, AgentPerformanceReview
from app.state import game_state

router = APIRouter(prefix="/api/performance-reviews", tags=["performance-reviews"])


@router.get("/{agent_id}/latest", response_model=AgentPerformanceReview | None)
async def latest_review(agent_id: AgentId = Path(...)) -> AgentPerformanceReview | None:
    """The most recent real AgentPerformanceReview on file for this
    agent, or null if none has been generated yet (reviews are only
    generated weekly — see app/nexus.py's tick)."""
    state = await game_state.snapshot()
    return latest_review_for_agent(state.agent_performance_reviews, agent_id)
