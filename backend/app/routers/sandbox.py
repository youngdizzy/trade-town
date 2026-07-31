"""The Research Sandbox (v0.7 Feature 45). See app/sandbox.py's module
docstring for what this feature extends vs. builds new.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.persistence import persist_modules
from app.schemas import BacktestSession, Strategy, StrategyDossier, StrategyExecutiveReview, StrategyFounderApproval, StrategyReview, TestScenario
from app.state import game_state
from app.strategy_lab import generate_strategy_dossier

router = APIRouter(prefix="/api/sandbox", tags=["sandbox"])


class BacktestRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    strategy_id: str = Field(alias="strategyId")
    scenario: TestScenario = "historical"
    custom_return_bias_pct: float = Field(default=0.0, alias="customReturnBiasPct")
    custom_volatility_bias: float = Field(default=1.0, alias="customVolatilityBias")


class BacktestResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    backtest_sessions: list[BacktestSession] = Field(alias="backtestSessions")


class StrategyIdRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    strategy_id: str = Field(alias="strategyId")


class LimitedLiveRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    strategy_id: str = Field(alias="strategyId")
    amount: float


class DecideReviewRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    review_id: str = Field(alias="reviewId")
    approve: bool


class StrategyStateResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    strategies: list[Strategy]
    strategy_reviews: list[StrategyReview] = Field(alias="strategyReviews")
    # v0.7 Feature 52 (Part 1) — only populated by /request-review, which is
    # the one CEO action that files these in the same real moment (see
    # app/state.py's request_strategy_company_review()); every other
    # action here leaves them empty rather than re-sending the whole list.
    strategy_executive_reviews: list[StrategyExecutiveReview] = Field(default_factory=list, alias="strategyExecutiveReviews")
    strategy_founder_approvals: list[StrategyFounderApproval] = Field(default_factory=list, alias="strategyFounderApprovals")


@router.post("/backtest", response_model=BacktestResponse)
async def queue_backtest(payload: BacktestRequest) -> BacktestResponse:
    state, error = await game_state.queue_sandbox_backtest(payload.strategy_id, payload.scenario, payload.custom_return_bias_pct, payload.custom_volatility_bias)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return BacktestResponse(backtestSessions=state.backtest_sessions)


@router.post("/begin-paper-trial", response_model=StrategyStateResponse)
async def begin_paper_trial(payload: StrategyIdRequest) -> StrategyStateResponse:
    state, error = await game_state.begin_strategy_paper_trial(payload.strategy_id)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return StrategyStateResponse(strategies=state.strategies, strategyReviews=state.strategy_reviews)


@router.post("/begin-limited-live", response_model=StrategyStateResponse)
async def begin_limited_live(payload: LimitedLiveRequest) -> StrategyStateResponse:
    state, error = await game_state.begin_strategy_limited_live(payload.strategy_id, payload.amount)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return StrategyStateResponse(strategies=state.strategies, strategyReviews=state.strategy_reviews)


@router.post("/request-review", response_model=StrategyStateResponse)
async def request_company_review(payload: StrategyIdRequest) -> StrategyStateResponse:
    state, error = await game_state.request_strategy_company_review(payload.strategy_id)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    latest_executive_review = [r for r in state.strategy_executive_reviews if r.strategy_id == payload.strategy_id][-1:]
    latest_founder_approval = [a for a in state.strategy_founder_approvals if a.strategy_id == payload.strategy_id][-1:]
    return StrategyStateResponse(
        strategies=state.strategies,
        strategyReviews=state.strategy_reviews,
        strategyExecutiveReviews=latest_executive_review,
        strategyFounderApprovals=latest_founder_approval,
    )


@router.post("/decide", response_model=StrategyStateResponse)
async def decide_review(payload: DecideReviewRequest) -> StrategyStateResponse:
    state, error = await game_state.decide_strategy_review(payload.review_id, payload.approve)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return StrategyStateResponse(strategies=state.strategies, strategyReviews=state.strategy_reviews)


@router.get("/dossier", response_model=StrategyDossier)
async def strategy_dossier(strategy_id: str = Query(..., alias="strategyId")) -> StrategyDossier:
    """v0.7 Feature 52 (Part 1) — the brief's auto-generated professional
    Strategy Report. Read-only and computed fresh every call (see
    app/strategy_lab.py's generate_strategy_dossier()): every field it
    returns already lives somewhere permanent (StrategyReport/Review/
    MonteCarloResult/RegimeTestReport/LiquidityValidation/
    ExecutiveReview/FounderApproval), so this is a synthesis, not a
    second source of truth — matches GET /api/executive/intelligence's
    same no-lock-needed, compute-on-request pattern."""
    state = await game_state.snapshot()
    strategy = next((s for s in state.strategies if s.id == strategy_id), None)
    if strategy is None:
        raise HTTPException(status_code=404, detail="No strategy found with that id.")
    return generate_strategy_dossier(
        strategy,
        state.strategy_reports,
        state.strategy_reviews,
        state.strategy_monte_carlo_results,
        state.strategy_regime_tests,
        state.strategy_liquidity_validations,
        state.strategy_executive_reviews,
        state.strategy_founder_approvals,
    )
