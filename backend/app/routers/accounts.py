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
from app.rule_engine import evaluate_rules
from app.schemas import Account, AccountType, PropFirmStatus, RuleEvaluationResult, RuleType, TreasuryState, Weekday
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


# Prop-Firm Risk Intelligence Addendum, Piece 10a — evaluation cost /
# funded-stage / payout tracking.
class ConfigureEvaluationTrackingRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    account_id: str = Field(alias="accountId")
    evaluation_cost: float | None = Field(default=None, alias="evaluationCost")
    payout_eligibility_min_profit_pct: float | None = Field(default=None, alias="payoutEligibilityMinProfitPct")


@router.post("/evaluation/configure", response_model=AccountsResponse)
async def configure_evaluation_tracking(payload: ConfigureEvaluationTrackingRequest) -> AccountsResponse:
    state, error = await game_state.configure_evaluation_tracking(
        payload.account_id,
        evaluation_cost=payload.evaluation_cost,
        payout_eligibility_min_profit_pct=payload.payout_eligibility_min_profit_pct,
    )
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return AccountsResponse(accounts=state.accounts)


@router.post("/evaluation/mark-funded", response_model=AccountsResponse)
async def mark_account_funded(payload: AccountIdRequest) -> AccountsResponse:
    state, error = await game_state.mark_account_funded(payload.account_id)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return AccountsResponse(accounts=state.accounts)


@router.post("/evaluation/record-payout", response_model=AccountsResponse)
async def record_account_payout(payload: AccountAmountRequest) -> AccountsResponse:
    state, error = await game_state.record_account_payout(payload.account_id, payload.amount)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return AccountsResponse(accounts=state.accounts)


# Design Bible Chapter 69 Part 3 — Institutional Rule Engine (IRE).
class AddCustomRuleRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    account_id: str = Field(alias="accountId")
    rule_type: RuleType = Field(alias="ruleType")
    label: str
    limit: float = 0.0
    weekday: Weekday | None = None


class RuleIdRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    account_id: str = Field(alias="accountId")
    rule_id: str = Field(alias="ruleId")


class ToggleCustomRuleRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    account_id: str = Field(alias="accountId")
    rule_id: str = Field(alias="ruleId")
    enabled: bool


@router.post("/rules/add", response_model=AccountsResponse)
async def add_custom_rule(payload: AddCustomRuleRequest) -> AccountsResponse:
    state, error = await game_state.add_custom_rule(payload.account_id, rule_type=payload.rule_type, label=payload.label, limit=payload.limit, weekday=payload.weekday)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return AccountsResponse(accounts=state.accounts)


@router.post("/rules/remove", response_model=AccountsResponse)
async def remove_custom_rule(payload: RuleIdRequest) -> AccountsResponse:
    state, error = await game_state.remove_custom_rule(payload.account_id, payload.rule_id)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return AccountsResponse(accounts=state.accounts)


@router.post("/rules/toggle", response_model=AccountsResponse)
async def toggle_custom_rule(payload: ToggleCustomRuleRequest) -> AccountsResponse:
    state, error = await game_state.toggle_custom_rule(payload.account_id, payload.rule_id, payload.enabled)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return AccountsResponse(accounts=state.accounts)


@router.get("/rules/evaluate", response_model=RuleEvaluationResult)
async def evaluate_account_rules(account_id: str) -> RuleEvaluationResult:
    """Read-only and computed fresh (same convention as prop_firm_status
    above) — every enabled Custom Rule on this account, checked
    individually and transparently by the one centralized
    app/rule_engine.py. No game-state lock needed."""
    state = await game_state.snapshot()
    account = next((a for a in state.accounts if a.id == account_id), None)
    if account is None:
        raise HTTPException(status_code=404, detail=f"No account with id {account_id!r}.")
    return evaluate_rules(account, sim_day=state.time.day)


@router.post("/rules/evaluate-and-record", response_model=RuleEvaluationResult)
async def evaluate_and_record_account_rules(payload: AccountIdRequest) -> RuleEvaluationResult:
    """The locked, permanent-recording counterpart to GET
    /rules/evaluate above — writes a real Company Memory record for any
    real violation found (see app/state.py's evaluate_account_rules),
    then returns the same real evaluation that was just recorded."""
    state, error = await game_state.evaluate_account_rules(payload.account_id)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    account = next(a for a in state.accounts if a.id == payload.account_id)
    return evaluate_rules(account, sim_day=state.time.day)
