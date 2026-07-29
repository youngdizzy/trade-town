"""Agent Energy spend endpoint (v0.6.2 Phase 6) — see app/agent_energy.py
and app/nexus.py's apply_energy_action for what each action actually does.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.persistence import persist_modules
from app.schemas import AgentEnergy
from app.state import game_state

router = APIRouter(prefix="/api/energy", tags=["energy"])


class SpendEnergyRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    action: str
    # Required for "research_boost" (which in-progress ResearchItem to
    # advance); ignored by the other actions.
    research_id: str | None = Field(default=None, alias="researchId")


class SpendEnergyResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    agent_energy: AgentEnergy = Field(alias="agentEnergy")


@router.post("/spend", response_model=SpendEnergyResponse)
async def spend_energy(payload: SpendEnergyRequest) -> SpendEnergyResponse:
    state, error = await game_state.spend_agent_energy(payload.action, payload.research_id)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)  # a spend is a meaningful event — see v0.6.2's save-strategy brief
    return SpendEnergyResponse(agentEnergy=state.agent_energy)
