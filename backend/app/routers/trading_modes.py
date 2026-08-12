"""Design Bible Chapter 75 — Company Trading Modes & Institutional
Capital Protection endpoints. See app/trading_modes.py's module
docstring for the full honesty boundary. TradingModeState/
DailyCircuitBreaker/LosingStreak/RecoveryBriefings are real, already-
persisted GameSaveState (recomputed every tick where noted — see
app/nexus.py's tick()). Performance split, Trading Mode Health, and the
Adaptive Mode recommendation are computed fresh per request, never
persisted — the same convention app/regime_reconciliation.py and
app/audit_log.py already established.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.regime_reconciliation import compute_regime_reconciliation
from app.schemas import (
    AdaptiveModeRecommendation,
    BehavioralCircuitBreakerRead,
    DailyCircuitBreakerRead,
    LosingStreakRead,
    RecoveryBriefing,
    TradingMode,
    TradingModeHealthAssessment,
    TradingModeState,
    TradingStylePerformance,
)
from app.state import game_state
from app.trading_modes import (
    adaptive_recommendations_disabled_reading,
    compute_adaptive_mode_recommendation,
    compute_trading_mode_health,
    compute_trading_style_performance,
)

router = APIRouter(prefix="/api/trading-modes", tags=["trading-modes"])


class SetTradingModeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    mode: TradingMode
    hybrid_day_allocation_pct: float | None = Field(default=None, alias="hybridDayAllocationPct")


@router.get("/state", response_model=TradingModeState)
async def get_trading_mode_state() -> TradingModeState:
    state = await game_state.snapshot()
    return state.trading_modes


@router.post("/set", response_model=TradingModeState)
async def post_set_trading_mode(payload: SetTradingModeRequest) -> TradingModeState:
    state, error = await game_state.set_trading_mode(mode=payload.mode, hybrid_day_allocation_pct=payload.hybrid_day_allocation_pct)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    return state.trading_modes


@router.get("/circuit-breaker", response_model=DailyCircuitBreakerRead)
async def get_daily_circuit_breaker() -> DailyCircuitBreakerRead:
    state = await game_state.snapshot()
    return state.daily_circuit_breaker


@router.get("/losing-streak", response_model=LosingStreakRead)
async def get_losing_streak() -> LosingStreakRead:
    state = await game_state.snapshot()
    return state.losing_streak


@router.post("/losing-streak/acknowledge", response_model=LosingStreakRead)
async def post_acknowledge_losing_streak() -> LosingStreakRead:
    state, error = await game_state.acknowledge_losing_streak()
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    return state.losing_streak


@router.get("/behavioral-circuit-breaker", response_model=BehavioralCircuitBreakerRead)
async def get_behavioral_circuit_breaker() -> BehavioralCircuitBreakerRead:
    state = await game_state.snapshot()
    return state.behavioral_circuit_breaker


class SetBehavioralThresholdsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    cooldown_minutes: int = Field(alias="cooldownMinutes")
    size_increase_threshold_pct: float = Field(alias="sizeIncreaseThresholdPct")


@router.post("/behavioral-circuit-breaker/thresholds", response_model=TradingModeState)
async def post_set_behavioral_thresholds(payload: SetBehavioralThresholdsRequest) -> TradingModeState:
    state, error = await game_state.set_behavioral_thresholds(cooldown_minutes=payload.cooldown_minutes, size_increase_threshold_pct=payload.size_increase_threshold_pct)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    return state.trading_modes


@router.get("/performance", response_model=list[TradingStylePerformance])
async def get_trading_style_performance() -> list[TradingStylePerformance]:
    state = await game_state.snapshot()
    return compute_trading_style_performance(state.paper_portfolio.trade_history)


@router.get("/health", response_model=list[TradingModeHealthAssessment])
async def get_trading_mode_health() -> list[TradingModeHealthAssessment]:
    state = await game_state.snapshot()
    return compute_trading_mode_health(state.paper_portfolio.trade_history, state.time.day)


@router.get("/adaptive-recommendation", response_model=AdaptiveModeRecommendation)
async def get_adaptive_mode_recommendation() -> AdaptiveModeRecommendation:
    state = await game_state.snapshot()
    if not state.trading_modes.adaptive_recommendations_enabled:
        return adaptive_recommendations_disabled_reading()
    reconciliation = compute_regime_reconciliation(state.market_environment, state.market_intelligence)
    return compute_adaptive_mode_recommendation(reconciliation)


class SetAdaptiveRecommendationsEnabledRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    enabled: bool


@router.post("/adaptive-recommendations-enabled", response_model=TradingModeState)
async def post_set_adaptive_recommendations_enabled(payload: SetAdaptiveRecommendationsEnabledRequest) -> TradingModeState:
    state = await game_state.set_adaptive_recommendations_enabled(payload.enabled)
    return state.trading_modes


@router.get("/recovery-briefings", response_model=list[RecoveryBriefing])
async def get_recovery_briefings() -> list[RecoveryBriefing]:
    state = await game_state.snapshot()
    return state.recovery_briefings
