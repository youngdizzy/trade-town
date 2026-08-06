"""Design Bible Chapter 69 Part 1 — Multi-Account & Fund Management
System endpoints. See app/accounts.py's module docstring for the honest
scope: real, CEO-manageable capital pools, not yet wired to live trading
execution.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.persistence import persist_modules
from app.schemas import Account, AccountType, TreasuryState
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
