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
from app.performance_attribution import (
    compute_regime_performance,
    compute_session_performance,
    compute_strategy_live_vs_backtest,
    compute_strategy_performance,
    compute_strategy_session_performance,
    compute_symbol_performance,
)
from app.persistence import persist_modules
from app.schemas import (
    ExitEfficiencySummary,
    RegimePerformanceSummary,
    SessionPerformanceSummary,
    StrategyLiveVsBacktestSummary,
    StrategyPerformanceSummary,
    StrategySessionPerformanceSummary,
    StrategyTradingDiagnosticSummary,
    SymbolPerformanceSummary,
    TradeAttributionSummary,
    TradePipelineHealthSnapshot,
)
from app.state import game_state
from app.trade_attribution import compute_trade_attribution_history
from app.trade_pipeline_health import compute_strategy_trading_diagnostics, compute_trade_pipeline_health

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


@router.get("/performance-by-strategy-session", response_model=StrategySessionPerformanceSummary)
async def get_performance_by_strategy_session() -> StrategySessionPerformanceSummary:
    """CEO directive "Live Trade → Strategy Provenance," Phase 6 — the
    one real strategy×session axis that didn't exist yet (see
    app/performance_attribution.py's own module docstring: session was
    previously blocked from a strategy join for the same reason
    performance-by-strategy itself was). Computed fresh per request; no
    new GameSaveState field."""
    state = await game_state.snapshot()
    return compute_strategy_session_performance(state.paper_portfolio.trade_history, state.decision_vault)


@router.get("/strategy-live-vs-backtest", response_model=StrategyLiveVsBacktestSummary)
async def get_strategy_live_vs_backtest() -> StrategyLiveVsBacktestSummary:
    """CEO directive "Live Trade → Strategy Provenance," Phase 5 — does a
    strategy's real live performance match what its own real backtest
    evidence (StrategyHealthAssessment) claimed? Joins two already-real,
    already-computed sources (see app/performance_attribution.py's
    compute_strategy_live_vs_backtest()) — computes no new trade-level
    statistics. Computed fresh per request; no new GameSaveState field."""
    state = await game_state.snapshot()
    live = compute_strategy_performance(state.paper_portfolio.trade_history, state.decision_vault)
    return compute_strategy_live_vs_backtest(live, state.strategy_health_assessments)


@router.get("/strategy-trading-diagnostics", response_model=StrategyTradingDiagnosticSummary)
async def get_strategy_trading_diagnostics() -> StrategyTradingDiagnosticSummary:
    """CEO directive "Live Trade → Strategy Provenance," Phase 9 — "why
    isn't this strategy trading live?" answered per strategy, real and
    diagnostic-only (see app/trade_pipeline_health.py's
    compute_strategy_trading_diagnostics()). Computed fresh per request;
    no new GameSaveState field, nothing here gates or scores anything."""
    state = await game_state.snapshot()
    return compute_strategy_trading_diagnostics(state)


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
