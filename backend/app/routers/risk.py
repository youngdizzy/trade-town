"""Daily Trading Objectives (v0.7 Feature 49) — the first real CEO write
path for RiskLimits. See app/risk_engine.py's module docstring for
exactly how each configured limit is enforced.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.persistence import persist_modules
from app.schemas import RiskLimits
from app.state import game_state

router = APIRouter(prefix="/api/risk-limits", tags=["risk"])


class UpdateRiskLimitsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    daily_profit_target_pct: float | None = Field(default=None, alias="dailyProfitTargetPct")
    max_daily_loss_pct: float | None = Field(default=None, alias="maxDailyLossPct")
    max_trades_per_day: int | None = Field(default=None, alias="maxTradesPerDay")
    risk_per_trade_pct: float | None = Field(default=None, alias="riskPerTradePct")
    max_open_positions: int | None = Field(default=None, alias="maxOpenPositions")


class RiskLimitsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    risk_limits: RiskLimits = Field(alias="riskLimits")


@router.post("", response_model=RiskLimitsResponse)
async def update_risk_limits(payload: UpdateRiskLimitsRequest) -> RiskLimitsResponse:
    state, error = await game_state.update_risk_limits(
        daily_profit_target_pct=payload.daily_profit_target_pct,
        max_daily_loss_pct=payload.max_daily_loss_pct,
        max_trades_per_day=payload.max_trades_per_day,
        risk_per_trade_pct=payload.risk_per_trade_pct,
        max_open_positions=payload.max_open_positions,
    )
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return RiskLimitsResponse(riskLimits=state.risk_limits)
