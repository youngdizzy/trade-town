"""Daily Trading Objectives (v0.7 Feature 49) — the first real CEO write
path for RiskLimits. See app/risk_engine.py's module docstring for
exactly how each configured limit is enforced.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.analytics import compute_recovery_factor
from app.market_data import market_data_provider
from app.persistence import persist_modules
from app.portfolio_intelligence import compute_portfolio_intelligence
from app.portfolio_monte_carlo import compute_portfolio_monte_carlo
from app.portfolio_risk import compute_portfolio_risk_snapshot, evaluate_marginal_portfolio_risk, evaluate_pretrade_risk_decision
from app.risk_contract import get_risk_contract_version
from app.risk_engine import daily_realized_pnl_pct, portfolio_equity, project_loss_after_n_losses
from app.schemas import (
    PortfolioMarginalRiskDecision,
    PortfolioMonteCarloResult,
    PortfolioRiskSnapshot,
    PretradeRiskDecision,
    ProjectedLossPath,
    RecoveryFactorRead,
    RiskContract,
    RiskContractScalingPolicy,
    RiskContractValidationResult,
    RiskDecision,
    RiskLimits,
    TierAllocationLimits,
)
from app.state import game_state

router = APIRouter(prefix="/api/risk-limits", tags=["risk"])


class UpdateRiskLimitsRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    daily_profit_target_pct: float | None = Field(default=None, alias="dailyProfitTargetPct")
    max_daily_loss_pct: float | None = Field(default=None, alias="maxDailyLossPct")
    # Design Bible Chapter 67 (TTOS) Safety Settings.
    max_weekly_loss_pct: float | None = Field(default=None, alias="maxWeeklyLossPct")
    max_monthly_loss_pct: float | None = Field(default=None, alias="maxMonthlyLossPct")
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
    # v0.7 Design Bible Chapter 63 — the Executive Performance & Company
    # Health Engine's Company Health tier threshold controls.
    company_health_excellent_threshold: float | None = Field(default=None, alias="companyHealthExcellentThreshold")
    company_health_good_threshold: float | None = Field(default=None, alias="companyHealthGoodThreshold")
    company_health_stable_threshold: float | None = Field(default=None, alias="companyHealthStableThreshold")
    company_health_needs_attention_threshold: float | None = Field(default=None, alias="companyHealthNeedsAttentionThreshold")


class RiskLimitsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    risk_limits: RiskLimits = Field(alias="riskLimits")


@router.post("", response_model=RiskLimitsResponse)
async def update_risk_limits(payload: UpdateRiskLimitsRequest) -> RiskLimitsResponse:
    state, error = await game_state.update_risk_limits(
        daily_profit_target_pct=payload.daily_profit_target_pct,
        max_daily_loss_pct=payload.max_daily_loss_pct,
        max_weekly_loss_pct=payload.max_weekly_loss_pct,
        max_monthly_loss_pct=payload.max_monthly_loss_pct,
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
        company_health_excellent_threshold=payload.company_health_excellent_threshold,
        company_health_good_threshold=payload.company_health_good_threshold,
        company_health_stable_threshold=payload.company_health_stable_threshold,
        company_health_needs_attention_threshold=payload.company_health_needs_attention_threshold,
    )
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return RiskLimitsResponse(riskLimits=state.risk_limits)


@router.get("/projected-loss", response_model=ProjectedLossPath)
async def projected_loss(n: int) -> ProjectedLossPath:
    """Prop-Firm Risk Intelligence Addendum, Piece 11a. Read-only,
    computed fresh from the primary portfolio's real current equity and
    RiskLimits — no game-state lock needed, nothing here mutates the
    save."""
    if n < 0:
        raise HTTPException(status_code=400, detail="n must be 0 or greater.")
    state = await game_state.snapshot()
    return project_loss_after_n_losses(state.risk_limits, state.paper_portfolio, n)


# CEO directive "Portfolio Risk Engine + Firm-Wide Risk Governance" —
# real, read-only composition reads (see app/portfolio_risk.py's own
# module docstring). Never a game-state mutation, never a second risk
# engine — both compose already-real state this codebase already
# computes and already enforces.
@router.get("/portfolio-snapshot", response_model=PortfolioRiskSnapshot)
async def portfolio_risk_snapshot() -> PortfolioRiskSnapshot:
    state = await game_state.snapshot()
    intelligence = compute_portfolio_intelligence(state.paper_portfolio, market_data_provider, pending_proposal_count=len(state.trade_proposals))
    return compute_portfolio_risk_snapshot(
        state.paper_portfolio,
        state.risk_limits,
        intelligence,
        daily_circuit_breaker_tier=state.daily_circuit_breaker.tier,
        daily_pnl_pct=daily_realized_pnl_pct(state.paper_portfolio, state.time.day),
        emergency_stop_active=state.emergency_stop.active,
    )


@router.get("/pretrade-decision", response_model=PretradeRiskDecision)
async def pretrade_risk_decision(
    symbol: str = Query(..., min_length=1, max_length=16),
    proposed_value: float = Query(..., gt=0),
) -> PretradeRiskDecision:
    state = await game_state.snapshot()
    return evaluate_pretrade_risk_decision(
        state.risk_limits,
        state.paper_portfolio,
        symbol=symbol.upper(),
        proposed_value=proposed_value,
        sim_day=state.time.day,
        emergency_stop_active=state.emergency_stop.active,
    )


# CEO directive "Portfolio Risk Engine + Firm-Wide Risk Governance,"
# final follow-up — see app/portfolio_monte_carlo.py's module docstring
# for the real historical-bootstrap methodology. Computed fresh (CAGS),
# never persisted; None below MIN_TRADES_FOR_PORTFOLIO_MONTE_CARLO real
# closed trades, never a bootstrap from too thin a real sample.
# CEO directive "Portfolio Risk Engine + Cross-Trade Capital Allocation"
# — the real Marginal Risk Test (Phase 17): portfolio state computed
# once WITHOUT the candidate and once WITH it, via a real synthetic-
# portfolio recomputation. See app/portfolio_risk.py's own
# `evaluate_marginal_portfolio_risk()` and `PortfolioMarginalRiskDecision`
# docstrings for the full methodology and disclosed simplifications.
@router.get("/marginal-decision", response_model=PortfolioMarginalRiskDecision)
async def marginal_portfolio_risk_decision(
    symbol: str = Query(..., min_length=1, max_length=16),
    proposed_value: float = Query(..., gt=0),
) -> PortfolioMarginalRiskDecision:
    state = await game_state.snapshot()
    return evaluate_marginal_portfolio_risk(
        state.risk_limits,
        state.paper_portfolio,
        market_data_provider,
        symbol=symbol.upper(),
        proposed_value=proposed_value,
        sim_day=state.time.day,
        emergency_stop_active=state.emergency_stop.active,
    )


@router.get("/portfolio-monte-carlo", response_model=PortfolioMonteCarloResult | None)
async def portfolio_monte_carlo() -> PortfolioMonteCarloResult | None:
    state = await game_state.snapshot()
    return compute_portfolio_monte_carlo(state.paper_portfolio, state.risk_limits, sim_day=state.time.day)


# CEO directive "Professional Quant Trading Core," Phase B P2 item —
# the Live Recovery Factor. See app/analytics.py's
# compute_recovery_factor() for the real methodology (net profit over
# the account's own real worst peak-to-trough drawdown, both measured
# against today's real live equity). Computed fresh per request; no new
# GameSaveState field.
@router.get("/recovery-factor", response_model=RecoveryFactorRead)
async def recovery_factor() -> RecoveryFactorRead:
    state = await game_state.snapshot()
    return compute_recovery_factor(state.paper_portfolio, current_equity=portfolio_equity(state.paper_portfolio))


# CEO directive "TradeTown — Persisted Risk Contract + Dynamic Risk
# Scaling" — a separate router (same file — same risk domain, same
# game_state POST-writes-via-game_state/GET-reads-computed-fresh
# convention as everything above) rather than overloading the
# RiskLimits-shaped `/api/risk-limits` prefix above with a distinct,
# versioned entity. See app/risk_contract.py's module docstring for the
# full DRAFT -> VALIDATED -> ACTIVE -> SUPERSEDED/ARCHIVED lifecycle this
# thinly wraps — every real rule (immutable-once-active, at most one
# ACTIVE contract, no draft skips validation) is enforced in
# app/state.py/app/risk_contract.py; this router adds no policy of its
# own.
risk_contracts_router = APIRouter(prefix="/api/risk-contracts", tags=["risk-contracts"])


class CreateDraftRiskContractRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    limits: RiskLimits
    scaling_policy: RiskContractScalingPolicy | None = Field(default=None, alias="scalingPolicy")
    reason: str
    created_by: str = Field(default="ceo", alias="createdBy")


class RiskContractHistoryResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    contracts: list[RiskContract]


class RiskDecisionsResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    decisions: list[RiskDecision]


@risk_contracts_router.get("/active", response_model=RiskContract)
async def active_risk_contract() -> RiskContract:
    """Lazily derives and persists a real v1 contract from the CEO's own
    already-configured RiskLimits the first time one is needed (Phase 12
    fail-closed guarantee) — see app/state.py::ensure_active_risk_contract()."""
    return await game_state.ensure_active_risk_contract()


@risk_contracts_router.get("/history", response_model=RiskContractHistoryResponse)
async def risk_contract_history() -> RiskContractHistoryResponse:
    state = await game_state.snapshot()
    return RiskContractHistoryResponse(contracts=state.risk_contracts)


@risk_contracts_router.get("/decisions", response_model=RiskDecisionsResponse)
async def risk_decisions_history(limit: int = Query(default=50, ge=1, le=200)) -> RiskDecisionsResponse:
    state = await game_state.snapshot()
    return RiskDecisionsResponse(decisions=state.risk_decisions[-limit:])


@risk_contracts_router.get("/{contract_id}/{version}", response_model=RiskContract)
async def risk_contract_version(contract_id: str, version: int) -> RiskContract:
    state = await game_state.snapshot()
    contract = get_risk_contract_version(state.risk_contracts, contract_id, version)
    if contract is None:
        raise HTTPException(status_code=404, detail=f"No risk contract {contract_id!r} version {version}.")
    return contract


@risk_contracts_router.post("/draft", response_model=RiskContract)
async def create_draft_risk_contract(payload: CreateDraftRiskContractRequest) -> RiskContract:
    state, draft, error = await game_state.create_draft_risk_contract(
        limits=payload.limits,
        scaling_policy=payload.scaling_policy,
        reason=payload.reason,
        created_by=payload.created_by,
    )
    if error is not None or draft is None:
        raise HTTPException(status_code=400, detail=error or "Failed to create draft risk contract.")
    persist_modules(state)
    return draft


@risk_contracts_router.post("/{contract_id}/validate", response_model=RiskContractValidationResult)
async def validate_draft_risk_contract(contract_id: str) -> RiskContractValidationResult:
    state, result, error = await game_state.validate_draft_risk_contract(contract_id)
    if error is not None or result is None:
        raise HTTPException(status_code=400, detail=error or "Failed to validate risk contract.")
    persist_modules(state)
    return result


@risk_contracts_router.post("/{contract_id}/activate", response_model=RiskContract)
async def activate_risk_contract(contract_id: str) -> RiskContract:
    state, active, error = await game_state.activate_risk_contract(contract_id)
    if error is not None or active is None:
        raise HTTPException(status_code=400, detail=error or "Failed to activate risk contract.")
    persist_modules(state)
    return active


@risk_contracts_router.post("/{contract_id}/archive", response_model=RiskContractHistoryResponse)
async def archive_risk_contract(contract_id: str) -> RiskContractHistoryResponse:
    state, error = await game_state.archive_risk_contract(contract_id)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return RiskContractHistoryResponse(contracts=state.risk_contracts)
