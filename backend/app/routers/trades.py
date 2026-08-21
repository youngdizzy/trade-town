"""Trade outcome notification acknowledgement (v0.6.2 Phase 10) — see
app/trade_notifications.py. The popup itself is built entirely from the
real PaperTrade already in paper_portfolio.trade_history (win/loss/
breakeven and thesis-confirmed/invalidated/neutral are both a direct
read of the trade's own pnl sign); this endpoint only records that the
player has seen it.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from app.exit_efficiency import compute_exit_efficiency
from app.performance_attribution import compute_regime_performance, compute_session_performance, compute_strategy_performance, compute_symbol_performance
from app.persistence import persist_modules
from app.schemas import (
    ExitEfficiencySummary,
    RegimePerformanceSummary,
    SessionPerformanceSummary,
    StrategyPerformanceSummary,
    SymbolPerformanceSummary,
    TradeAttributionSummary,
    TradePipelineHealthSnapshot,
)
from app.state import game_state
from app.trade_attribution import compute_trade_attribution_history
from app.trade_pipeline_health import compute_trade_pipeline_health

router = APIRouter(prefix="/api/trades", tags=["trades"])


class AckNotificationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    trade_id: str = Field(alias="tradeId")


class AckNotificationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    viewed_trade_notification_ids: list[str] = Field(alias="viewedTradeNotificationIds")


@router.post("/ack", response_model=AckNotificationResponse)
async def ack_notification(payload: AckNotificationRequest) -> AckNotificationResponse:
    viewed_ids = await game_state.ack_trade_notification(payload.trade_id)
    persist_modules(await game_state.snapshot())
    return AckNotificationResponse(viewedTradeNotificationIds=viewed_ids)


@router.get("/exit-efficiency", response_model=ExitEfficiencySummary)
async def get_exit_efficiency() -> ExitEfficiencySummary:
    """CEO directive "Professional Trading Firm Transformation" — Post-
    Trade Review, Exit Efficiency (see app/exit_efficiency.py). Read-
    only, computed fresh per request from the already-real
    `trade_history` — no new GameSaveState field."""
    state = await game_state.snapshot()
    return compute_exit_efficiency(state.paper_portfolio.trade_history)


@router.get("/performance-by-symbol", response_model=SymbolPerformanceSummary)
async def get_performance_by_symbol() -> SymbolPerformanceSummary:
    """CEO directive "Next Professional Trading Firm Phase," Priority 2
    (see app/performance_attribution.py). Read-only, computed fresh per
    request from the already-real `trade_history` — no new
    GameSaveState field."""
    state = await game_state.snapshot()
    return compute_symbol_performance(state.paper_portfolio.trade_history)


@router.get("/attribution", response_model=TradeAttributionSummary)
async def get_trade_attribution() -> TradeAttributionSummary:
    """CEO directive "Next Phase: Professional Trading Firm Intelligence,"
    Phase 1 (see app/trade_attribution.py). Real per-trade evidence —
    who advised what, real CEO-override/risk-approval provenance, real
    execution detail — never a numeric P&L-per-agent credit split (no
    CEO-authorized methodology for one exists). Computed fresh per
    request; no new GameSaveState field."""
    state = await game_state.snapshot()
    return compute_trade_attribution_history(state.paper_portfolio.trade_history, state.decisions, state.ceo_decisions)


@router.get("/performance-by-session", response_model=SessionPerformanceSummary)
async def get_performance_by_session() -> SessionPerformanceSummary:
    """CEO directive "Next Phase: Professional Trading Firm Intelligence,"
    Phase 3 (see app/performance_attribution.py). Joins the real
    Decision Vault for session context; a trade with no matching vault
    entry is excluded and counted, never fabricated. Computed fresh per
    request; no new GameSaveState field."""
    state = await game_state.snapshot()
    return compute_session_performance(state.paper_portfolio.trade_history, state.decision_vault)


@router.get("/performance-by-regime", response_model=RegimePerformanceSummary)
async def get_performance_by_regime() -> RegimePerformanceSummary:
    """CEO directive "Next Phase: Professional Trading Firm Intelligence,"
    Phase 3 (see app/performance_attribution.py). Same real Decision
    Vault join as performance-by-session, grouped by market regime
    instead. Computed fresh per request; no new GameSaveState field."""
    state = await game_state.snapshot()
    return compute_regime_performance(state.paper_portfolio.trade_history, state.decision_vault)


@router.get("/performance-by-strategy", response_model=StrategyPerformanceSummary)
async def get_performance_by_strategy() -> StrategyPerformanceSummary:
    """CEO directive "Live Trade → Strategy Provenance," Phase 4 — the
    Strategy Exposure view (see app/performance_attribution.py). Only
    ever groups trades where the CEO explicitly selected a real strategy
    at decision time (`strategyProvenanceState == "known"`); every other
    trade is excluded and counted under one of two distinct, honest
    reasons, never silently dropped or fabricated into a strategy it
    wasn't actually attributed to. Computed fresh per request; no new
    GameSaveState field."""
    state = await game_state.snapshot()
    return compute_strategy_performance(state.paper_portfolio.trade_history, state.decision_vault)


@router.get("/pipeline-health", response_model=TradePipelineHealthSnapshot)
async def get_trade_pipeline_health() -> TradePipelineHealthSnapshot:
    """CEO directive "Professional Quant Firm Phase 41-45," Critical Task
    #0 — real funnel diagnostics distinguishing "no valid trade existed"
    from "a valid trade existed but the system failed to execute it."
    Diagnostic only — see app/trade_pipeline_health.py's own module
    docstring for the full forensic audit this was built from and the
    exact caps/honesty boundary on each count. Computed fresh per
    request; no new GameSaveState field, nothing here gates or scores
    anything."""
    state = await game_state.snapshot()
    return compute_trade_pipeline_health(state)
