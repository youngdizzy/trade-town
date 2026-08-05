"""Market data endpoints — the v0.6.2 Market Data Abstraction. Chart data
is deliberately never part of GameSaveState: it's fully regenerable from
the provider on demand, not game progress (see v0.6.2's save-payload-size
fix), so it lives behind its own REST endpoint instead of riding along on
/api/save or the WebSocket state broadcast.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.market_data import TIMEFRAME_ORDER, market_data_provider
from app.regime_reconciliation import compute_regime_reconciliation
from app.schemas import Candle, RegimeReconciliation
from app.state import game_state

router = APIRouter(prefix="/api/market", tags=["market"])

MIN_LIMIT = 10
MAX_LIMIT = 500


@router.get("/timeframes", response_model=list[str])
async def get_timeframes() -> list[str]:
    """Only the timeframes the currently-configured provider actually
    supports — never a hardcoded list a real provider might not honor."""
    return TIMEFRAME_ORDER


@router.get("/candles", response_model=list[Candle])
async def get_candles(
    symbol: str = Query(..., min_length=1, max_length=16),
    timeframe: str = Query(...),
    limit: int = Query(150, ge=MIN_LIMIT, le=MAX_LIMIT),
) -> list[Candle]:
    if timeframe not in TIMEFRAME_ORDER:
        raise HTTPException(status_code=400, detail=f"Unsupported timeframe {timeframe!r}. Supported: {TIMEFRAME_ORDER}")
    try:
        candles = market_data_provider.get_candles(symbol.upper(), timeframe, limit)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    return [Candle.model_validate(c.__dict__) for c in candles]


@router.get("/regime-reconciliation", response_model=RegimeReconciliation)
async def get_regime_reconciliation() -> RegimeReconciliation:
    """Design Bible Chapter 65 — reconciles app/market_environment.py's
    real 5-way regime read with app/market_intelligence.py's real 13-way
    read (and its own real Regime Confidence Score) into one CEO-facing
    answer, plus a read-only posture recommendation. Computed fresh per
    request from the current real state — never a second persisted
    copy, and never a write to any RiskLimits field (see
    app/regime_reconciliation.py's own module docstring)."""
    state = await game_state.snapshot()
    return compute_regime_reconciliation(state.market_environment, state.market_intelligence)
