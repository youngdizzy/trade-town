"""CEO Treasury endpoints (v0.7 Feature 33) — see app/treasury.py's module
docstring for the structural isolation guarantee every one of these
handlers upholds: only an explicit player action reaches this router.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.persistence import persist_save
from app.schemas import PaperPortfolio, SavingsRuleType, TreasuryState
from app.state import game_state

router = APIRouter(prefix="/api/treasury", tags=["treasury"])


class AmountRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    amount: float


class TreasuryFundsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    treasury: TreasuryState
    paper_portfolio: PaperPortfolio = Field(alias="paperPortfolio")


class CreateRuleRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    rule_type: SavingsRuleType = Field(alias="ruleType")
    percent: float = 0.0
    reserve_target: float | None = Field(default=None, alias="reserveTarget")


class ToggleRuleRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    rule_id: str = Field(alias="ruleId")
    active: bool


class TreasuryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    treasury: TreasuryState


@router.post("/deposit", response_model=TreasuryFundsResponse)
async def deposit_treasury(payload: AmountRequest) -> TreasuryFundsResponse:
    state, error = await game_state.deposit_treasury(payload.amount)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_save(state)
    return TreasuryFundsResponse(treasury=state.treasury, paperPortfolio=state.paper_portfolio)


@router.post("/withdraw", response_model=TreasuryFundsResponse)
async def withdraw_treasury(payload: AmountRequest) -> TreasuryFundsResponse:
    state, error = await game_state.withdraw_treasury(payload.amount)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_save(state)
    return TreasuryFundsResponse(treasury=state.treasury, paperPortfolio=state.paper_portfolio)


@router.post("/rules/create", response_model=TreasuryResponse)
async def create_savings_rule(payload: CreateRuleRequest) -> TreasuryResponse:
    state, error = await game_state.create_savings_rule(payload.rule_type, payload.percent, payload.reserve_target)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_save(state)
    return TreasuryResponse(treasury=state.treasury)


@router.post("/rules/toggle", response_model=TreasuryResponse)
async def toggle_savings_rule(payload: ToggleRuleRequest) -> TreasuryResponse:
    state, error = await game_state.toggle_savings_rule(payload.rule_id, payload.active)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_save(state)
    return TreasuryResponse(treasury=state.treasury)


@router.post("/rules/pause-all", response_model=TreasuryResponse)
async def pause_all_savings_rules() -> TreasuryResponse:
    state = await game_state.pause_all_savings_rules()
    persist_save(state)
    return TreasuryResponse(treasury=state.treasury)
