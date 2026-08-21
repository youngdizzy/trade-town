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
from app.executive_intelligence import compute_executive_accuracy_scores, compute_executive_recommendation, generate_department_opinions
from app.market_data import market_data_provider
from app.persistence import persist_modules
from app.process_adherence import compute_process_adherence, compute_recent_process_adherence_summary
from app.schemas import (
    AgentId,
    CeoDecisionRecord,
    ChallengeReport,
    ConfluenceRead,
    Debate,
    ExecutiveAccuracyScore,
    ExecutiveRecommendation,
    GatekeeperRejection,
    HoldReason,
    InnovationState,
    PaperPortfolio,
    ProcessAdherenceRead,
    ProcessAdherenceSummaryRead,
    TradeDecision,
    TradeProposal,
    WeightedExecutiveRecommendation,
    WeightProfile,
    WhatIfSimulation,
)
from app.signal_correlation import assess_confluence
from app.state import game_state
from app.weighted_decisions import compute_weighted_recommendation
from app.whatif import run_whatif_simulation

router = APIRouter(prefix="/api/executive", tags=["executive"])


class SubmitCeoDecisionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    proposal_id: str = Field(alias="proposalId")
    choice: AnalystChoice
    # Design Bible Chapter 70 Part 2 — "Delegate to the Executive Board."
    # True only when the CEO explicitly clicked Delegate; `choice` is
    # still required and should be the Executive Intelligence Network's
    # own recommended action (mapped client-side from GET
    # /api/executive/intelligence) so this endpoint never has to guess
    # what "delegate" means — it only changes what gets recorded about
    # who decided.
    delegated: bool = False
    # CEO directive "Features 31-35," Feature 32 — an optional real
    # reason the CEO typed for this decision, stored on the resulting
    # CeoDecisionRecord only when this decision is actually an override
    # (see app/state.py's submit_ceo_decision).
    override_reason: str | None = Field(default=None, alias="overrideReason")
    # CEO directive "Live Trade -> Strategy Provenance" — an optional
    # real Strategy Lab strategy the CEO explicitly selected for this
    # decision (see app/state.py's submit_ceo_decision for the
    # real-strategy-exists validation before this is ever stored).
    strategy_id: str | None = Field(default=None, alias="strategyId")


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
    state, error = await game_state.submit_ceo_decision(
        payload.proposal_id,
        payload.choice,
        delegated=payload.delegated,
        override_reason=payload.override_reason,
        strategy_id=payload.strategy_id,
    )
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
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
    persist_modules(state)
    return HoldProposalResponse(tradeProposals=state.trade_proposals)


class ModifyProposalRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    proposal_id: str = Field(alias="proposalId")
    quantity: float


class ModifyProposalResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    trade_proposals: list[TradeProposal] = Field(alias="tradeProposals")


@router.post("/modify", response_model=ModifyProposalResponse)
async def modify(payload: ModifyProposalRequest) -> ModifyProposalResponse:
    """Design Bible Chapter 70 Part 2 — "Modify" as a real CEO decision
    action. Downsize-only; the proposal stays pending. See
    app/state.py's modify_trade_proposal."""
    state, error = await game_state.modify_trade_proposal(payload.proposal_id, payload.quantity)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return ModifyProposalResponse(tradeProposals=state.trade_proposals)


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
    persist_modules(state)
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
    persist_modules(state)
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


@router.get("/intelligence", response_model=ExecutiveRecommendation)
async def executive_intelligence(proposal_id: str = Query(..., alias="proposalId")) -> ExecutiveRecommendation:
    """v0.7 Feature 50 (Part 1) — the Executive Intelligence Network's
    real "combine every perspective" read for one pending TradeProposal.
    Read-only and computed fresh (see app/executive_intelligence.py's
    module docstring for why: every input already lives somewhere
    permanent, so this is a synthesis, not a second source of truth).
    No game-state lock needed — nothing here mutates the save.

    Design Bible Chapter 70 Part 2 — merges in the What-If Simulation
    Lab's own real Probability of Success / Estimated Return / Estimated
    Risk numbers (the same real bootstrap sim GET /api/executive/whatif
    already computes) rather than inventing a parallel Institutional
    Risk/Opportunity Score; left None (never fabricated) if the symbol's
    candles aren't available."""
    state = await game_state.snapshot()
    proposal = next((p for p in state.trade_proposals if p.id == proposal_id), None)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Unknown or already-resolved proposal.")
    challenge_report = next((c for c in reversed(state.challenge_reports) if c.proposal_id == proposal_id), None)
    opinions = generate_department_opinions(proposal, challenge_report, state.coach_reports, state.market_intelligence, state.decision_vault)
    recommendation = compute_executive_recommendation(proposal, opinions)
    try:
        candles = market_data_provider.get_candles(proposal.symbol, PROPOSAL_TIMEFRAME, PROPOSAL_CANDLE_COUNT)
        whatif = run_whatif_simulation(proposal.symbol, candles)
        recommendation = recommendation.model_copy(
            update={
                "probability_of_success_pct": whatif.baseline.probability_of_profit_pct,
                "estimated_return_pct": whatif.baseline.most_likely_pct,
                "estimated_risk_pct": whatif.baseline.typical_drawdown_pct,
            }
        )
    except ValueError:
        pass
    return recommendation


@router.get("/confluence", response_model=ConfluenceRead)
async def confluence(proposal_id: str = Query(..., alias="proposalId")) -> ConfluenceRead:
    """CEO directive "Professional Trading Firm — Market-Analysis
    Knowledge + Session Intelligence Expansion," Phase 6 — the
    Confluence Engine's real-time read for one pending TradeProposal.
    Read-only and computed fresh from the proposal's own already-real
    analyst_votes (see app/signal_correlation.py's module docstring for
    the real correlation audit this is built on). Purely informational:
    never gates, vetoes, or adjusts the Gatekeeper/Risk/Model Validation
    pipeline."""
    state = await game_state.snapshot()
    proposal = next((p for p in state.trade_proposals if p.id == proposal_id), None)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Unknown or already-resolved proposal.")
    return assess_confluence(proposal.analyst_votes, proposal.overall_recommendation)


@router.get("/decisions/{decision_id}/process-adherence", response_model=ProcessAdherenceRead)
async def process_adherence(decision_id: str) -> ProcessAdherenceRead:
    """Trading Psychology & Discipline, Piece C — the Process Adherence
    Score (Design Bible Chapter 66 addendum, app/process_adherence.py).
    Read-only and computed fresh every call (the same convention GET
    /whatif above and app/strategy_lab.py's Certification already
    established) — never persisted, so a Discipline Review filed after
    this was first read automatically shows up on the next read. No
    game-state lock needed — nothing here mutates the save."""
    state = await game_state.snapshot()
    decision = next((d for d in state.decisions if d.id == decision_id), None)
    if decision is None:
        raise HTTPException(status_code=404, detail="Unknown trade decision.")
    trade = next((t for t in state.paper_portfolio.trade_history if t.decision_id == decision_id), None)
    discipline_review = next((r for r in state.discipline_reviews if r.decision_id == decision_id), None)
    return compute_process_adherence(decision, trade, discipline_review)


@router.get("/process-adherence-summary", response_model=ProcessAdherenceSummaryRead)
async def process_adherence_summary() -> ProcessAdherenceSummaryRead:
    """Trading Psychology & Discipline, Piece G — the one company-wide
    aggregate over Process Adherence this codebase never needed before
    (every other consumer reads a single decision by id — see
    DecisionDetail.tsx above). Read-only, computed fresh every call, same
    convention as the per-decision endpoint above."""
    state = await game_state.snapshot()
    return compute_recent_process_adherence_summary(state.decisions, state.paper_portfolio.trade_history, state.discipline_reviews)


@router.get("/accuracy", response_model=list[ExecutiveAccuracyScore])
async def executive_accuracy() -> list[ExecutiveAccuracyScore]:
    """Design Bible Chapter 70 Part 2 — Executive Accuracy Score.
    Read-only and computed fresh from the permanent Executive Meeting
    Log + CEO Decision Records (see app/executive_intelligence.py's
    compute_executive_accuracy_scores for the honesty boundary: scored
    only over trades actually taken and since closed with a real
    outcome). No game-state lock needed — nothing here mutates the save."""
    state = await game_state.snapshot()
    return compute_executive_accuracy_scores(state.executive_meeting_log, state.ceo_decisions)


@router.get("/weighted-decision", response_model=WeightedExecutiveRecommendation)
async def weighted_decision(
    proposal_id: str = Query(..., alias="proposalId"),
    profile: WeightProfile | None = Query(default=None),
) -> WeightedExecutiveRecommendation:
    """Design Bible Chapter 70 Part 3 — Weighted Executive Decision
    Engine. Read-only and computed fresh (same convention as
    /intelligence and /accuracy above) — this is purely advisory and
    never gates or resolves a trade; the Trade Gatekeeper's real,
    unconditional veto (Chapters 58/66) is untouched.

    `profile` optionally previews a different Weight Profile than the
    CEO's persisted `settings.activeWeightProfile` without changing it —
    switching for real happens via the normal settings save, the same
    client-authoritative mechanism `operatingMode` already uses. No
    game-state lock needed — nothing here mutates the save."""
    state = await game_state.snapshot()
    proposal = next((p for p in state.trade_proposals if p.id == proposal_id), None)
    if proposal is None:
        raise HTTPException(status_code=404, detail="Unknown or already-resolved proposal.")
    challenge_report = next((c for c in reversed(state.challenge_reports) if c.proposal_id == proposal_id), None)
    opinions = generate_department_opinions(proposal, challenge_report, state.coach_reports, state.market_intelligence, state.decision_vault)
    recommendation = compute_executive_recommendation(proposal, opinions)
    accuracy_scores = compute_executive_accuracy_scores(state.executive_meeting_log, state.ceo_decisions)
    active_profile = profile if profile is not None else state.settings.active_weight_profile
    return compute_weighted_recommendation(
        proposal.id,
        opinions,
        accuracy_scores,
        regime=state.market_environment.current,
        profile=active_profile,
        custom_weights=state.settings.custom_department_weights,
        raw_action=recommendation.action,
    )
