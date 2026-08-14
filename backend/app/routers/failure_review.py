"""CEO directive "Features 26-30," Feature 30 — read-only endpoints over
FailureClassifications, mirroring routers/prediction_tracking.py's own
convention: `await game_state.snapshot()`, computed fresh every call,
nothing here mutates the save. The full list is already broadcast on
every WS tick (see app/ws_manager.py's `failureClassifications` field) —
this router adds the one genuinely new query the broadcast can't offer
cheaply on the frontend: "what's this one agent's own recent failure
classification record."
"""
from __future__ import annotations

from fastapi import APIRouter, Path

from app.schemas import AgentId, FailureClassification
from app.state import game_state

router = APIRouter(prefix="/api/failures", tags=["failures"])


@router.get("/{agent_id}", response_model=list[FailureClassification])
async def failures_for_agent(agent_id: AgentId = Path(...)) -> list[FailureClassification]:
    """Every real FailureClassification this agent is a real supporting
    agent on, oldest first."""
    state = await game_state.snapshot()
    return [c for c in state.failure_classifications if agent_id in c.attributed_agents]
