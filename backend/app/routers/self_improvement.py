"""Design Bible Chapter 74 — Continuous Learning & Self-Improvement
System (CLSIS, Part 1) and the Institutional Evolution Engine (Part 2).
See app/self_improvement.py's and app/evolution.py's own module
docstrings for what's real vs. explicitly deferred.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.evolution import WINDOW_DAYS, compute_company_evolution_score
from app.persistence import persist_modules
from app.self_improvement import compute_executive_learning_summary
from app.schemas import (
    AgentId,
    CompanyEvolutionScore,
    ExecutiveLearningSummary,
    InstitutionalEvolutionReport,
    SelfImprovementProposal,
)
from app.state import game_state

router = APIRouter(prefix="/api/self-improvement", tags=["self-improvement"])


class DecideProposalRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    proposal_id: str = Field(alias="proposalId")
    approve: bool
    ceo_note: str | None = Field(default=None, alias="ceoNote")


@router.get("/proposals", response_model=list[SelfImprovementProposal])
async def get_self_improvement_proposals() -> list[SelfImprovementProposal]:
    state = await game_state.snapshot()
    return state.self_improvement_proposals


@router.post("/proposals/decide", response_model=list[SelfImprovementProposal])
async def decide_proposal(payload: DecideProposalRequest) -> list[SelfImprovementProposal]:
    state, error = await game_state.decide_self_improvement_proposal(
        payload.proposal_id, payload.approve, payload.ceo_note
    )
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return state.self_improvement_proposals


@router.get("/executive-learning/{agent_id}", response_model=ExecutiveLearningSummary)
async def get_executive_learning_summary(agent_id: AgentId) -> ExecutiveLearningSummary:
    state = await game_state.snapshot()
    return compute_executive_learning_summary(
        agent_id,
        coach_reports=state.coach_reports,
        thinking_profiles=state.thinking_profiles,
        agent_knowledge=state.agent_knowledge,
        mentor_progress=state.foundational_mentor_state.progress.get(agent_id, {}),
    )


@router.get("/evolution-reports", response_model=list[InstitutionalEvolutionReport])
async def get_evolution_reports() -> list[InstitutionalEvolutionReport]:
    state = await game_state.snapshot()
    return state.evolution_reports


@router.get("/evolution-score/{window}", response_model=CompanyEvolutionScore)
async def get_evolution_score(window: str) -> CompanyEvolutionScore:
    if window not in WINDOW_DAYS:
        raise HTTPException(status_code=400, detail=f"window must be one of {sorted(WINDOW_DAYS)}.")
    state = await game_state.snapshot()
    return compute_company_evolution_score(
        window=window,
        current_sim_day=state.time.day,
        case_studies=state.case_studies,
        self_improvement_proposals=state.self_improvement_proposals,
        mentor_progress=state.foundational_mentor_state.progress,
        strategy_hall_of_fame=state.strategy_hall_of_fame,
        strategy_failed_archive=state.strategy_failed_archive,
        constitution_amendments=state.constitution.amendments,
    )
