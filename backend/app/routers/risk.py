"""Daily Trading Objectives (v0.7 Feature 49) — the first real CEO write
path for RiskLimits. See app/risk_engine.py's module docstring for
exactly how each configured limit is enforced.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.persistence import persist_modules
from app.schemas import RiskLimits, TierAllocationLimits
from app.state import game_state

router = APIRouter(prefix="/api/risk-limits", tags=["risk"])


class UpdateRiskLimitsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    daily_profit_target_pct: float | None = Field(default=None, alias="dailyProfitTargetPct")
    max_daily_loss_pct: float | None = Field(default=None, alias="maxDailyLossPct")
    max_trades_per_day: int | None = Field(default=None, alias="maxTradesPerDay")
    risk_per_trade_pct: float | None = Field(default=None, alias="riskPerTradePct")
    max_open_positions: int | None = Field(default=None, alias="maxOpenPositions")
    # v0.7 Chapter 57 — four of the engine's six new CEO controls.
    # portfolio_heat_cap_pct is float|None already (None = disabled), but
    # that alone can't distinguish "field omitted" from "CEO wants to
    # disable the cap" — clear_portfolio_heat_cap resolves that.
    max_weekly_deployment_pct: float | None = Field(default=None, alias="maxWeeklyDeploymentPct")
    portfolio_heat_cap_pct: float | None = Field(default=None, alias="portfolioHeatCapPct")
    clear_portfolio_heat_cap: bool = Field(default=False, alias="clearPortfolioHeatCap")
    cash_reserve_pct: float | None = Field(default=None, alias="cashReservePct")
    tier_allocation: TierAllocationLimits | None = Field(default=None, alias="tierAllocation")
    # v0.7 Chapter 58 — the Opportunity Gatekeeper's two new CEO controls.
    min_trade_quality_score: float | None = Field(default=None, alias="minTradeQualityScore")
    min_expected_value_pct: float | None = Field(default=None, alias="minExpectedValuePct")
    # v0.7 Chapter 59 — the Capital Priority & Opportunity Cost Engine's
    # two new CEO controls.
    min_priority_score: float | None = Field(default=None, alias="minPriorityScore")
    capital_reserve_pct: float | None = Field(default=None, alias="capitalReservePct")
    # v0.7 Chapter 61 — the Knowledge Graph & Company Memory Engine's
    # Pattern Detection Sensitivity controls, plus both slices of
    # Knowledge Retention Rules.
    min_similar_matches: int | None = Field(default=None, alias="minSimilarMatches")
    mistake_warning_share_pct: float | None = Field(default=None, alias="mistakeWarningSharePct")
    max_decision_vault_entries: int | None = Field(default=None, alias="maxDecisionVaultEntries")
    max_memory_records: int | None = Field(default=None, alias="maxMemoryRecords")
    # v0.7 Design Bible Chapter 62 — the Innovation Lab's Innovation
    # Budget CEO control.
    max_limited_live_capital: float | None = Field(default=None, alias="maxLimitedLiveCapital")


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
        max_weekly_deployment_pct=payload.max_weekly_deployment_pct,
        portfolio_heat_cap_pct=payload.portfolio_heat_cap_pct,
        clear_portfolio_heat_cap=payload.clear_portfolio_heat_cap,
        cash_reserve_pct=payload.cash_reserve_pct,
        tier_allocation=payload.tier_allocation,
        min_trade_quality_score=payload.min_trade_quality_score,
        min_expected_value_pct=payload.min_expected_value_pct,
        min_priority_score=payload.min_priority_score,
        capital_reserve_pct=payload.capital_reserve_pct,
        min_similar_matches=payload.min_similar_matches,
        mistake_warning_share_pct=payload.mistake_warning_share_pct,
        max_decision_vault_entries=payload.max_decision_vault_entries,
        max_memory_records=payload.max_memory_records,
        max_limited_live_capital=payload.max_limited_live_capital,
    )
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return RiskLimitsResponse(riskLimits=state.risk_limits)
