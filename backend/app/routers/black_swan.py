"""Design Bible Chapter 72 — Black Swan Intelligence & Resilience System
(BSIRS) endpoints. See app/black_swan.py's module docstring for the full
honesty boundary. Stress Tests and Scenario Simulations are computed
fresh per request, never persisted (same convention app/whatif.py's own
Simulation Lab already established) — every other endpoint here reads or
mutates real, already-persisted GameSaveState.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.black_swan import (
    broker_resilience_read,
    build_black_swan_playbook,
    run_portfolio_scenario,
    run_portfolio_stress_test,
)
from app.market_data import market_data_provider
from app.persistence import persist_modules
from app.schemas import (
    Account,
    BlackSwanEventRecord,
    BlackSwanIntelligenceState,
    BlackSwanPlaybook,
    BlackSwanReport,
    BlackSwanRiskTier,
    BlackSwanScenarioType,
    BrokerResilienceRead,
    DefensiveModeState,
    InstitutionalSurvivalScore,
    PaperPortfolio,
    PortfolioScenarioResult,
    PortfolioStressTestResult,
    RiskLimits,
)
from app.state import game_state

router = APIRouter(prefix="/api/black-swan", tags=["black-swan"])


def _resolve_account(state_accounts: list[Account], primary_portfolio: PaperPortfolio, primary_limits: RiskLimits, account_id: str | None) -> tuple[PaperPortfolio, RiskLimits, str, str | None]:
    """Every real portfolio this company has — the primary one, or any
    Account (Chapter 69) — can be stress-tested or scenario-simulated.
    Returns (portfolio, limits, label, error)."""
    if account_id is None:
        return primary_portfolio, primary_limits, "Primary Portfolio", None
    account = next((a for a in state_accounts if a.id == account_id), None)
    if account is None:
        return primary_portfolio, primary_limits, "Primary Portfolio", f"No account with id {account_id!r}."
    return account.portfolio, account.risk_limits, account.name, None


class DefensiveModeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    defensive_mode: DefensiveModeState = Field(alias="defensiveMode")
    risk_limits: RiskLimits = Field(alias="riskLimits")


class ConfigureDefensiveModeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    trigger_tier: BlackSwanRiskTier | None = Field(default=None, alias="triggerTier")
    auto_trigger_enabled: bool | None = Field(default=None, alias="autoTriggerEnabled")


class ActivateDefensiveModeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    reason: str | None = None


class StressTestRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    account_id: str | None = Field(default=None, alias="accountId")


class ScenarioRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    scenario_type: BlackSwanScenarioType = Field(alias="scenarioType")
    account_id: str | None = Field(default=None, alias="accountId")


@router.get("/intelligence", response_model=BlackSwanIntelligenceState)
async def get_black_swan_intelligence() -> BlackSwanIntelligenceState:
    """The always-current Early Warning Score / Risk Level / Confidence
    Read (recomputed every tick, already on the game state snapshot —
    never a second copy computed here)."""
    state = await game_state.snapshot()
    return state.black_swan_intelligence


@router.get("/reports", response_model=list[BlackSwanReport])
async def get_black_swan_reports() -> list[BlackSwanReport]:
    """The permanent daily Black Swan Situation Report history, oldest
    first, capped at MAX_BLACK_SWAN_REPORTS."""
    state = await game_state.snapshot()
    return state.black_swan_reports


@router.get("/survival-score", response_model=InstitutionalSurvivalScore)
async def get_institutional_survival_score() -> InstitutionalSurvivalScore:
    """Design Bible Chapter 72 Part 2 — the always-current Institutional
    Survival Score (recomputed every tick, already on the game state
    snapshot — never a second copy computed here). See app/black_swan.py's
    module docstring for the honesty boundary: no "Estimated Survival
    Probability" is fabricated, and Leverage/Counterparty Risk are cut
    outright as unsupported by any real data in this codebase."""
    state = await game_state.snapshot()
    return state.institutional_survival_score


@router.get("/events", response_model=list[BlackSwanEventRecord])
async def get_black_swan_events() -> list[BlackSwanEventRecord]:
    """The permanent Post-Event Analysis history — one record per
    completed Defensive Mode episode, oldest first."""
    state = await game_state.snapshot()
    return state.black_swan_events


@router.get("/playbook", response_model=BlackSwanPlaybook)
async def get_playbook() -> BlackSwanPlaybook:
    """The one real Elevated Risk Response Playbook, live-populated with
    today's actual Defensive Mode recommendations — see
    app/black_swan.py's module docstring for why this is a single,
    generically-named playbook rather than eight fabricated ones."""
    state = await game_state.snapshot()
    return build_black_swan_playbook(state.black_swan_intelligence, state.defensive_mode, state.paper_portfolio, state.risk_limits)


@router.get("/broker-resilience", response_model=BrokerResilienceRead)
async def get_broker_resilience() -> BrokerResilienceRead:
    """The honest, static answer to the brief's Broker Resilience
    section — see BrokerResilienceRead's own docstring for why this is
    never a live monitor."""
    return broker_resilience_read()


@router.post("/stress-test", response_model=PortfolioStressTestResult)
async def post_stress_test(payload: StressTestRequest) -> PortfolioStressTestResult:
    """The brief's own -10/-20/-35/-50/-70% ladder, computed fresh
    against a chosen real portfolio (the primary one, or any Account's —
    see app/accounts.py). Never persisted."""
    state = await game_state.snapshot()
    portfolio, limits, label, error = _resolve_account(state.accounts, state.paper_portfolio, state.risk_limits, payload.account_id)
    if error is not None:
        raise HTTPException(status_code=404, detail=error)
    return run_portfolio_stress_test(portfolio, limits, state.market_intelligence.liquidity, account_id=payload.account_id, account_label=label, sim_day=state.time.day)


@router.post("/scenario", response_model=PortfolioScenarioResult)
async def post_scenario(payload: ScenarioRequest) -> PortfolioScenarioResult:
    """One of four scenarios, each named for its real mechanism (never a
    fabricated historical event) — see app/black_swan.py's module
    docstring for the full list and why the brief's named historical
    scenarios were cut."""
    state = await game_state.snapshot()
    portfolio, limits, label, error = _resolve_account(state.accounts, state.paper_portfolio, state.risk_limits, payload.account_id)
    if error is not None:
        raise HTTPException(status_code=404, detail=error)
    return run_portfolio_scenario(payload.scenario_type, portfolio, limits, market_data_provider, account_id=payload.account_id, account_label=label)


@router.post("/defensive-mode/configure", response_model=DefensiveModeResponse)
async def post_configure_defensive_mode(payload: ConfigureDefensiveModeRequest) -> DefensiveModeResponse:
    state, error = await game_state.configure_defensive_mode(trigger_tier=payload.trigger_tier, auto_trigger_enabled=payload.auto_trigger_enabled)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return DefensiveModeResponse(defensiveMode=state.defensive_mode, riskLimits=state.risk_limits)


@router.post("/defensive-mode/activate", response_model=DefensiveModeResponse)
async def post_activate_defensive_mode(payload: ActivateDefensiveModeRequest) -> DefensiveModeResponse:
    state, error = await game_state.activate_defensive_mode(reason=payload.reason or "Manually activated by the CEO.")
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return DefensiveModeResponse(defensiveMode=state.defensive_mode, riskLimits=state.risk_limits)


@router.post("/defensive-mode/deactivate", response_model=DefensiveModeResponse)
async def post_deactivate_defensive_mode() -> DefensiveModeResponse:
    state, error = await game_state.deactivate_defensive_mode()
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return DefensiveModeResponse(defensiveMode=state.defensive_mode, riskLimits=state.risk_limits)
