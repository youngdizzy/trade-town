"""Executive Voting endpoints (v0.6.3 Feature 12) — the CEO's (the
player's) real buy/sell/wait call on a pending TradeProposal. See
app/executive.py for how proposals are generated and resolved, and
app/state.py's submit_ceo_decision() for the locked state mutation this
router calls into.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.executive import PROPOSAL_CANDLE_COUNT, PROPOSAL_TIMEFRAME, AnalystChoice
from app.market_data import market_data_provider
from app.persistence import persist_save
from app.schemas import (
    AgentId,
    CeoDecisionRecord,
    ChallengeReport,
    Debate,
    GatekeeperRejection,
    HoldReason,
    InnovationState,
    PaperPortfolio,
    TradeDecision,
    TradeProposal,
    WhatIfSimulation,
)
from app.state import game_state
from app.whatif import run_whatif_simulation

router = APIRouter(prefix="/api/executive", tags=["executive"])


class SubmitCeoDecisionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    proposal_id: str = Field(alias="proposalId")
    choice: AnalystChoice


class SubmitCeoDecisionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    trade_proposals: list[TradeProposal] = Field(alias="tradeProposals")
    ceo_decisions: list[CeoDecisionRecord] = Field(alias="ceoDecisions")
    decisions: list[TradeDecision]
    paper_portfolio: PaperPortfolio = Field(alias="paperPortfolio")
    # v0.7 Feature 20 — sent back immediately so the CEO sees a fresh
    # rejection (if this decision produced one) without waiting for the
    # next WS tick broadcast.
    gatekeeper_rejections: list[GatekeeperRejection] = Field(alias="gatekeeperRejections")


@router.post("/decide", response_model=SubmitCeoDecisionResponse)
async def decide(payload: SubmitCeoDecisionRequest) -> SubmitCeoDecisionResponse:
    state, error = await game_state.submit_ceo_decision(payload.proposal_id, payload.choice)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_save(state)
    return SubmitCeoDecisionResponse(
        tradeProposals=state.trade_proposals,
        ceoDecisions=state.ceo_decisions,
        decisions=state.decisions,
        paperPortfolio=state.paper_portfolio,
        gatekeeperRejections=state.gatekeeper_rejections,
    )


class HoldProposalRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    proposal_id: str = Field(alias="proposalId")
    reason: HoldReason


class HoldProposalResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    trade_proposals: list[TradeProposal] = Field(alias="tradeProposals")


@router.post("/hold", response_model=HoldProposalResponse)
async def hold(payload: HoldProposalRequest) -> HoldProposalResponse:
    """v0.7 Feature 40.5 — "Request More Research" / "Delay Decision".
    The proposal stays pending; see app/state.py's hold_trade_proposal."""
    state, error = await game_state.hold_trade_proposal(payload.proposal_id, payload.reason)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_save(state)
    return HoldProposalResponse(tradeProposals=state.trade_proposals)


class RegenerateDebateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    proposal_id: str = Field(alias="proposalId")


class RegenerateDebateResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    debates: list[Debate]


@router.post("/debate/regenerate", response_model=RegenerateDebateResponse)
async def regenerate_debate(payload: RegenerateDebateRequest) -> RegenerateDebateResponse:
    """v0.7 Feature 17 — "request another debate" on a still-pending
    proposal. See GameState.regenerate_debate for why this appends
    rather than replaces."""
    state, error = await game_state.regenerate_debate(payload.proposal_id)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_save(state)
    return RegenerateDebateResponse(debates=state.debates)


class RegenerateChallengeReportRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    proposal_id: str = Field(alias="proposalId")


class RegenerateChallengeReportResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    challenge_reports: list[ChallengeReport] = Field(alias="challengeReports")
    innovation_state: dict[AgentId, InnovationState] = Field(alias="innovationState")


@router.post("/challenge/regenerate", response_model=RegenerateChallengeReportResponse)
async def regenerate_challenge_report(payload: RegenerateChallengeReportRequest) -> RegenerateChallengeReportResponse:
    """v0.7 Feature 41 — "request another review" on a still-pending
    proposal. See GameState.regenerate_challenge_report for why this
    appends rather than replaces."""
    state, error = await game_state.regenerate_challenge_report(payload.proposal_id)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_save(state)
    return RegenerateChallengeReportResponse(challengeReports=state.challenge_reports, innovationState=state.innovation_state)


@router.get("/whatif", response_model=WhatIfSimulation)
async def whatif(symbol: str = Query(..., min_length=1, max_length=16)) -> WhatIfSimulation:
    """v0.7 Feature 16 — the What-If Simulation Lab. Read-only and
    computed fresh (see app/whatif.py's module docstring for why it's
    never persisted): reuses the exact same candle sample the technical
    analyst vote reads for this same symbol (see app/executive.py's
    _technical_vote) so both readings stay grounded in the same real
    data. No game-state lock needed — nothing here mutates the save."""
    try:
        candles = market_data_provider.get_candles(symbol.upper(), PROPOSAL_TIMEFRAME, PROPOSAL_CANDLE_COUNT)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return run_whatif_simulation(symbol.upper(), candles)
