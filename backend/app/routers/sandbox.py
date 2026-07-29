"""The Research Sandbox (v0.7 Feature 45). See app/sandbox.py's module
docstring for what this feature extends vs. builds new.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.persistence import persist_modules
from app.schemas import BacktestSession, Strategy, StrategyReview, TestScenario
from app.state import game_state

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
    return StrategyStateResponse(strategies=state.strategies, strategyReviews=state.strategy_reviews)


@router.post("/decide", response_model=StrategyStateResponse)
async def decide_review(payload: DecideReviewRequest) -> StrategyStateResponse:
    state, error = await game_state.decide_strategy_review(payload.review_id, payload.approve)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return StrategyStateResponse(strategies=state.strategies, strategyReviews=state.strategy_reviews)
