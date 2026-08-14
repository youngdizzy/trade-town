"""CEO directive "Features 26-30," Feature 28 — read-only endpoints over
Agent Skill Profiles, mirroring routers/performance_review.py's own
convention: `await game_state.snapshot()`, computed fresh every call,
nothing here mutates the save. The full list is already broadcast on
every WS tick (see app/ws_manager.py's `agentSkillProfiles` field) —
this router adds the one genuinely new query the broadcast can't offer
cheaply on the frontend: "what's this one agent's latest real skill
snapshot."
"""
from __future__ import annotations

from fastapi import APIRouter, Path

from app.schemas import AgentId, AgentSkillProfile
from app.skill_progression import latest_skill_profile_for_agent
from app.state import game_state

router = APIRouter(prefix="/api/skill-profiles", tags=["skill-profiles"])


@router.get("/{agent_id}/latest", response_model=AgentSkillProfile | None)
async def latest_skill_profile(agent_id: AgentId = Path(...)) -> AgentSkillProfile | None:
    """The most recent real AgentSkillProfile on file for this agent, or
    null if none has been generated yet (profiles are only generated
    weekly — see app/nexus.py's tick)."""
    state = await game_state.snapshot()
    return latest_skill_profile_for_agent(state.agent_skill_profiles, agent_id)
