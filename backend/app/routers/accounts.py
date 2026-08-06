"""Design Bible Chapter 69 Part 1 — Multi-Account & Fund Management
System endpoints. See app/accounts.py's module docstring for the honest
scope: real, CEO-manageable capital pools, not yet wired to live trading
execution.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.persistence import persist_modules
from app.prop_firm import compute_prop_firm_status
from app.schemas import Account, AccountType, PropFirmStatus, TreasuryState
from app.state import game_state

router = APIRouter(prefix="/api/accounts", tags=["accounts"])


class AccountsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    accounts: list[Account]


class CreateAccountRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    account_type: AccountType = Field(alias="accountType")
    starting_balance: float = Field(alias="startingBalance")


class AccountIdRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    account_id: str = Field(alias="accountId")


class AccountAmountRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    account_id: str = Field(alias="accountId")
    amount: float


class SwitchActiveAccountRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    account_id: str | None = Field(default=None, alias="accountId")


class AccountFundsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    accounts: list[Account]
    treasury: TreasuryState


class ActiveAccountResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    active_account_id: str | None = Field(alias="activeAccountId")


@router.post("/create", response_model=AccountsResponse)
async def create_account(payload: CreateAccountRequest) -> AccountsResponse:
    state, error = await game_state.create_account(payload.name, payload.account_type, payload.starting_balance)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return AccountsResponse(accounts=state.accounts)


@router.post("/close", response_model=AccountsResponse)
async def close_account(payload: AccountIdRequest) -> AccountsResponse:
    state, error = await game_state.close_account(payload.account_id)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return AccountsResponse(accounts=state.accounts)


@router.post("/allocate", response_model=AccountFundsResponse)
async def allocate_capital(payload: AccountAmountRequest) -> AccountFundsResponse:
    state, error = await game_state.allocate_account_capital(payload.account_id, payload.amount)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return AccountFundsResponse(accounts=state.accounts, treasury=state.treasury)


@router.post("/deallocate", response_model=AccountFundsResponse)
async def deallocate_capital(payload: AccountAmountRequest) -> AccountFundsResponse:
    state, error = await game_state.deallocate_account_capital(payload.account_id, payload.amount)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return AccountFundsResponse(accounts=state.accounts, treasury=state.treasury)


@router.post("/switch-active", response_model=ActiveAccountResponse)
async def switch_active_account(payload: SwitchActiveAccountRequest) -> ActiveAccountResponse:
    state, error = await game_state.switch_active_account(payload.account_id)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return ActiveAccountResponse(activeAccountId=state.active_account_id)


# Design Bible Chapter 69 Part 2 — Prop Firm Rule Engine.
class ConfigurePropFirmRulesRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    account_id: str = Field(alias="accountId")
    trailing_drawdown_limit_pct: float | None = Field(default=None, alias="trailingDrawdownLimitPct")
    consistency_limit_pct: float | None = Field(default=None, alias="consistencyLimitPct")
    # None means "start the challenge window now" (the current sim day);
    # explicitly pass a past day to backdate, or omit entirely alongside
    # every other field to clear a previously configured window.
    challenge_start_sim_day: int | None = Field(default=None, alias="challengeStartSimDay")
    challenge_duration_days: int | None = Field(default=None, alias="challengeDurationDays")
    challenge_profit_target_pct: float | None = Field(default=None, alias="challengeProfitTargetPct")


@router.post("/prop-firm/configure", response_model=AccountsResponse)
async def configure_prop_firm_rules(payload: ConfigurePropFirmRulesRequest) -> AccountsResponse:
    state, error = await game_state.configure_prop_firm_rules(
        payload.account_id,
        trailing_drawdown_limit_pct=payload.trailing_drawdown_limit_pct,
        consistency_limit_pct=payload.consistency_limit_pct,
        challenge_start_sim_day=payload.challenge_start_sim_day,
        challenge_duration_days=payload.challenge_duration_days,
        challenge_profit_target_pct=payload.challenge_profit_target_pct,
    )
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return AccountsResponse(accounts=state.accounts)


@router.get("/prop-firm/status", response_model=PropFirmStatus)
async def prop_firm_status(account_id: str) -> PropFirmStatus:
    """Read-only and computed fresh (same convention as GET
    /api/executive/intelligence) — every input already lives on the
    real Account, so this is a synthesis, not a second source of truth.
    No game-state lock needed — nothing here mutates the save."""
    state = await game_state.snapshot()
    account = next((a for a in state.accounts if a.id == account_id), None)
    if account is None:
        raise HTTPException(status_code=404, detail=f"No account with id {account_id!r}.")
    return compute_prop_firm_status(account, sim_day=state.time.day)
