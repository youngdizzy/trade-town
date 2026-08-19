"""The Research Sandbox (v0.7 Feature 45). See app/sandbox.py's module
docstring for what this feature extends vs. builds new.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.ema_pullback_research import DEFAULT_CANDLES_PER_SYMBOL, DEFAULT_TIMEFRAME, run_ema_pullback_research
from app.evaluation_simulator import compare_evaluation_policies
from app.persistence import persist_modules
from app.schemas import (
    BacktestSession,
    EmaPullbackResearchResult,
    EvaluationPolicyComparisonReport,
    FailedStrategyArchiveEntry,
    ModelValidationReport,
    Strategy,
    StrategyCertification,
    StrategyDossier,
    StrategyExecutiveDashboard,
    StrategyExecutiveReview,
    StrategyFounderApproval,
    StrategyHallOfFameEntry,
    StrategyReview,
    TestScenario,
)
from app.state import game_state
from app.strategy_lab import compute_strategy_certification, compute_strategy_executive_dashboard, generate_strategy_dossier

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


class RetireStrategyRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    strategy_id: str = Field(alias="strategyId")
    reason: str


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
    # v0.7 Quantitative Research & Intelligence System, Piece 4 — Meridian/
    # CIO's independent, advisory-only ModelValidationReport. Only
    # populated by /request-review, the one action that files it (see
    # app/state.py's request_strategy_company_review()); every other
    # action here leaves it empty rather than re-sending the whole list.
    strategy_model_validation: ModelValidationReport | None = Field(default=None, alias="strategyModelValidation")
    # v0.7 Feature 52 (Part 2) — only populated by /retire; exactly one of
    # the two is ever non-empty for a given retirement (see
    # app/strategy_lab.py's generate_strategy_retirement_outcome()).
    strategy_hall_of_fame_entry: StrategyHallOfFameEntry | None = Field(default=None, alias="strategyHallOfFameEntry")
    strategy_failed_archive_entry: FailedStrategyArchiveEntry | None = Field(default=None, alias="strategyFailedArchiveEntry")


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
    latest_model_validation = next((r for r in reversed(state.strategy_model_validations) if r.strategy_id == payload.strategy_id), None)
    return StrategyStateResponse(
        strategies=state.strategies,
        strategyReviews=state.strategy_reviews,
        strategyExecutiveReviews=latest_executive_review,
        strategyFounderApprovals=latest_founder_approval,
        strategyModelValidation=latest_model_validation,
    )


@router.post("/decide", response_model=StrategyStateResponse)
async def decide_review(payload: DecideReviewRequest) -> StrategyStateResponse:
    state, error = await game_state.decide_strategy_review(payload.review_id, payload.approve)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return StrategyStateResponse(strategies=state.strategies, strategyReviews=state.strategy_reviews)


@router.post("/retire", response_model=StrategyStateResponse)
async def retire_strategy(payload: RetireStrategyRequest) -> StrategyStateResponse:
    """v0.7 Feature 52 (Part 2) — the only real way a strategy's stage
    ever reaches "retired" (see app/state.py's retire_strategy())."""
    state, error = await game_state.retire_strategy(payload.strategy_id, payload.reason)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    hall_of_fame_entry = next((e for e in reversed(state.strategy_hall_of_fame) if e.strategy_id == payload.strategy_id), None)
    failed_archive_entry = next((e for e in reversed(state.strategy_failed_archive) if e.strategy_id == payload.strategy_id), None)
    return StrategyStateResponse(
        strategies=state.strategies,
        strategyReviews=state.strategy_reviews,
        strategyHallOfFameEntry=hall_of_fame_entry,
        strategyFailedArchiveEntry=failed_archive_entry,
    )


@router.get("/dashboard", response_model=StrategyExecutiveDashboard)
async def strategy_executive_dashboard() -> StrategyExecutiveDashboard:
    """v0.7 Feature 52 (Part 2) — the brief's Executive Dashboard.
    Read-only and computed fresh every call (see app/strategy_lab.py's
    compute_strategy_executive_dashboard()), same reasoning as
    GET /api/sandbox/dossier."""
    state = await game_state.snapshot()
    return compute_strategy_executive_dashboard(
        state.strategies,
        state.simulation_results,
        state.strategy_reviews,
        state.strategy_monte_carlo_results,
        state.strategy_regime_tests,
        state.strategy_executive_reviews,
        state.strategy_hall_of_fame,
        state.strategy_failed_archive,
        sim_day=state.time.day,
    )


@router.get("/ema-pullback-research", response_model=EmaPullbackResearchResult)
async def ema_pullback_research(
    timeframe: str = Query(DEFAULT_TIMEFRAME),
    candles_per_symbol: int = Query(DEFAULT_CANDLES_PER_SYMBOL, alias="candlesPerSymbol", ge=200, le=20000),
) -> EmaPullbackResearchResult:
    """CEO directive "Professional Trading Firm — Market-Analysis
    Knowledge + Session Intelligence Expansion," Phase 15 — the 50 EMA
    breakout + pullback strategy, converted into a formal, reproducible
    research hypothesis and independently backtested against this
    codebase's own real (mock) candle history (see
    app/ema_pullback_research.py's module docstring for the full rule
    definitions and the SOURCE CLAIM vs. TRADETOWN EVIDENCE distinction
    this endpoint exists to keep honest). Read-only, computed fresh every
    call — nothing here is persisted, and no agent or live trading
    decision is ever wired to this endpoint's result."""
    state = await game_state.snapshot()
    return run_ema_pullback_research(timeframe=timeframe, candles_per_symbol=candles_per_symbol, sim_day=state.time.day)


@router.get("/certification", response_model=StrategyCertification)
async def strategy_certification(strategy_id: str = Query(..., alias="strategyId")) -> StrategyCertification:
    """v0.7 Feature 53 — Company Certification. Read-only and computed
    fresh every call (see app/strategy_lab.py's
    compute_strategy_certification()): every requirement reads an
    already-real Feature 52 artifact, so "certified" is always a live
    read of the strategy's own current real state — including a real,
    automatic drop to uncertified the moment its Health degrades. No
    game-state lock needed — nothing here mutates the save."""
    state = await game_state.snapshot()
    strategy = next((s for s in state.strategies if s.id == strategy_id), None)
    if strategy is None:
        raise HTTPException(status_code=404, detail="No strategy found with that id.")
    review = next((r for r in reversed(state.strategy_reviews) if r.strategy_id == strategy_id), None)
    monte_carlo = next((r for r in reversed(state.strategy_monte_carlo_results) if r.strategy_id == strategy_id), None)
    regime_test = next((r for r in reversed(state.strategy_regime_tests) if r.strategy_id == strategy_id), None)
    executive_review = next((r for r in reversed(state.strategy_executive_reviews) if r.strategy_id == strategy_id), None)
    founder_approval = next((r for r in reversed(state.strategy_founder_approvals) if r.strategy_id == strategy_id), None)
    health = next((r for r in reversed(state.strategy_health_assessments) if r.strategy_id == strategy_id), None)
    return compute_strategy_certification(strategy, state.simulation_results, review, monte_carlo, regime_test, executive_review, founder_approval, health)


@router.get("/model-validation", response_model=ModelValidationReport | None)
async def strategy_model_validation(strategy_id: str = Query(..., alias="strategyId")) -> ModelValidationReport | None:
    """v0.7 Quantitative Research & Intelligence System, Piece 4 —
    Meridian/CIO's most recent independent, advisory-only validation
    report for this strategy. Read-only; returns None if the strategy
    has never been through Company Review yet (see app/state.py's
    request_strategy_company_review(), the one real place this is
    generated)."""
    state = await game_state.snapshot()
    strategy = next((s for s in state.strategies if s.id == strategy_id), None)
    if strategy is None:
        raise HTTPException(status_code=404, detail="No strategy found with that id.")
    return next((r for r in reversed(state.strategy_model_validations) if r.strategy_id == strategy_id), None)


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


@router.get("/evaluation-policy-comparison", response_model=EvaluationPolicyComparisonReport | None)
async def evaluation_policy_comparison(
    strategy_id: str = Query(..., alias="strategyId"),
    account_id: str | None = Query(default=None, alias="accountId"),
) -> EvaluationPolicyComparisonReport | None:
    """Quantitative Research & Intelligence System, Requirements
    21/22/23/25 (Piece 10) — a real, on-demand Monte Carlo comparison of
    four named evaluation-stage risk policies for this strategy. None
    when the strategy has no completed simulation runs yet — nothing
    real to bootstrap from (same honesty boundary as GET /model-
    validation and .../monte-carlo). Read-only and computed fresh every
    call — nothing here is persisted or auto-generated in the background
    sim tick, unlike StrategyMonteCarloResult; see app/
    evaluation_simulator.py's own module docstring for why this piece
    stays a real, on-demand research computation rather than a second
    autonomous background pipeline."""
    state = await game_state.snapshot()
    strategy = next((s for s in state.strategies if s.id == strategy_id), None)
    if strategy is None:
        raise HTTPException(status_code=404, detail="No strategy found with that id.")
    account = None
    if account_id is not None:
        account = next((a for a in state.accounts if a.id == account_id), None)
        if account is None:
            raise HTTPException(status_code=404, detail=f"No account with id {account_id!r}.")
    return compare_evaluation_policies(strategy, state.simulation_results, account=account, sim_day=state.time.day)
