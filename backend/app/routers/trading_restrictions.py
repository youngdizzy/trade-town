"""CEO directive "Portfolio Risk Engine + Firm-Wide Risk Governance,"
follow-up "Layered Kill Switches" — the real, scoped trading restriction
endpoints. See app/trading_restrictions.py's module docstring for exactly
what activating/lifting a restriction does and does not block.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.persistence import persist_modules
from app.schemas import RestrictionScope, TradingRestriction
from app.state import game_state

router = APIRouter(prefix="/api/trading-restrictions", tags=["trading-restrictions"])


class TradingRestrictionsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    trading_restrictions: list[TradingRestriction] = Field(alias="tradingRestrictions")


class ActivateTradingRestrictionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    scope: RestrictionScope
    target: str
    reason: str


class LiftTradingRestrictionRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    reason: str = ""


@router.get("", response_model=TradingRestrictionsResponse)
async def list_trading_restrictions() -> TradingRestrictionsResponse:
    state = await game_state.snapshot()
    return TradingRestrictionsResponse(tradingRestrictions=state.trading_restrictions)


@router.post("/activate", response_model=TradingRestrictionsResponse)
async def activate(body: ActivateTradingRestrictionRequest) -> TradingRestrictionsResponse:
    state, error = await game_state.activate_trading_restriction(scope=body.scope, target=body.target, reason=body.reason)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return TradingRestrictionsResponse(tradingRestrictions=state.trading_restrictions)


@router.post("/{restriction_id}/lift", response_model=TradingRestrictionsResponse)
async def lift(restriction_id: str, body: LiftTradingRestrictionRequest) -> TradingRestrictionsResponse:
    state, error = await game_state.lift_trading_restriction(restriction_id, reason=body.reason)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return TradingRestrictionsResponse(tradingRestrictions=state.trading_restrictions)
