"""Trade outcome notification acknowledgement (v0.6.2 Phase 10) — see
app/trade_notifications.py. The popup itself is built entirely from the
real PaperTrade already in paper_portfolio.trade_history (win/loss/
breakeven and thesis-confirmed/invalidated/neutral are both a direct
read of the trade's own pnl sign); this endpoint only records that the
player has seen it.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.data_quality_monitor import compute_data_quality_monitor
from app.exit_efficiency import compute_exit_efficiency
from app.opportunity_feed import compute_opportunity_feed
from app.watchlist_eligibility import compute_watchlist_eligibility
from app.performance_attribution import (
    compute_regime_performance,
    compute_session_performance,
    compute_strategy_capital_allocation_evidence,
    compute_strategy_degradation,
    compute_strategy_live_correlation,
    compute_strategy_live_vs_backtest,
    compute_strategy_performance,
    compute_strategy_regime_performance,
    compute_strategy_session_performance,
    compute_symbol_performance,
)
from app.persistence import persist_modules
from app.schemas import (
    DataQualityMonitor,
    DriftEvent,
    ExitEfficiencySummary,
    OpportunityFeed,
    PaperTradeJournalEntry,
    RegimePerformanceSummary,
    SessionPerformanceSummary,
    StrategyCapitalAllocationSummary,
    StrategyDegradationSummary,
    StrategyHealthState,
    StrategyLiveCorrelationSummary,
    StrategyLiveVsBacktestSummary,
    StrategyPerformanceSummary,
    StrategyRegimePerformanceSummary,
    StrategySessionPerformanceSummary,
    StrategyTradingDiagnosticSummary,
    SymbolPerformanceSummary,
    TradeAttributionSummary,
    TradeLifecycleRecord,
    TradePipelineHealthSnapshot,
    TradeStrategyRuleSnapshot,
    UnattributedTradeMonitor,
    WatchlistEligibilitySummary,
)
from app.state import game_state
from app.trade_attribution import compute_trade_attribution_history, compute_unattributed_trade_monitor, resolve_trade_strategy_rule_snapshot
from app.trade_lifecycle import build_trade_lifecycle_record
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


@router.get("/unattributed-monitor", response_model=UnattributedTradeMonitor)
async def get_unattributed_trade_monitor() -> UnattributedTradeMonitor:
    """CEO directive "Complete Trade Provenance," Part 17 — a dedicated,
    visible data-quality diagnostic: how many real trades lack strategy
    lineage, why (two distinct real reasons, never folded together),
    and whether the real attribution rate is trending better or worse
    over trade history (see app/trade_attribution.py's
    compute_unattributed_trade_monitor()). Computed fresh per request;
    no new GameSaveState field."""
    state = await game_state.snapshot()
    return compute_unattributed_trade_monitor(state.paper_portfolio.trade_history, state.decisions, state.ceo_decisions)


@router.get("/data-quality-monitor", response_model=DataQualityMonitor)
async def get_data_quality_monitor() -> DataQualityMonitor:
    """CEO directive "Complete Trade Provenance," Part 18 — a real,
    narrowly-scoped data-quality diagnostic (see
    app/data_quality_monitor.py's own module docstring for exactly
    which four categories this checks, and why the other three Part 18
    names are already surfaced elsewhere rather than duplicated here).
    Reports only — never repairs or backfills anything it finds.
    Computed fresh per request; no new GameSaveState field."""
    state = await game_state.snapshot()
    return compute_data_quality_monitor(state.paper_portfolio.trade_history, state.ceo_decisions, state.strategies)


@router.get("/{trade_id}/strategy-rule-snapshot", response_model=TradeStrategyRuleSnapshot)
async def get_trade_strategy_rule_snapshot(trade_id: str) -> TradeStrategyRuleSnapshot:
    """CEO directive "Complete Trade Provenance," Part 2 — resolves one
    real closed trade's strategy-rule snapshot back into the exact
    immutable CompiledStrategyDefinition that was active the instant the
    CEO decided it (see app/trade_attribution.py's
    resolve_trade_strategy_rule_snapshot()). `compiledDefinition` is
    honestly `None` whenever this trade has no CEO-selected strategy, or
    the strategy had no compiled rules at decision time — never
    fabricated. 404 only when `trade_id` doesn't match any real trade.
    Computed fresh per request; no new GameSaveState field."""
    state = await game_state.snapshot()
    snapshot = resolve_trade_strategy_rule_snapshot(
        trade_id,
        state.paper_portfolio.trade_history,
        state.decisions,
        state.ceo_decisions,
        state.compiled_strategy_versions,
    )
    if snapshot is None:
        raise HTTPException(status_code=404, detail=f"No real closed trade with id {trade_id!r}.")
    return snapshot


@router.get("/{trade_id}/lifecycle", response_model=TradeLifecycleRecord)
async def get_trade_lifecycle(trade_id: str) -> TradeLifecycleRecord:
    """CEO directive "Canonical Trade Lifecycle 1.0" — one real trade's
    full lifecycle in a single read (see app/trade_lifecycle.py's module
    docstring for the full Phase 0 forensic-recon rationale). `trade_id`
    accepts any real id already on hand for this trade — an open
    PaperPosition id, a closed PaperTrade id, a journal entry id, a
    CeoDecisionRecord id, or the originating TradeProposal id — all
    resolve to the same record. Every nested object is a direct
    reference to something that already exists elsewhere in
    GameSaveState; this endpoint computes nothing new. 404 only when
    `trade_id` matches no real trade at all."""
    state = await game_state.snapshot()
    record = build_trade_lifecycle_record(state, trade_id)
    if record is None:
        raise HTTPException(status_code=404, detail=f"No real trade found for id {trade_id!r}.")
    return record


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


@router.get("/performance-by-strategy-regime", response_model=StrategyRegimePerformanceSummary)
async def get_performance_by_strategy_regime() -> StrategyRegimePerformanceSummary:
    """CEO directive "Complete Trade Provenance," Part 12 — the
    strategy×regime counterpart to performance-by-strategy-session above
    (see app/performance_attribution.py's compute_strategy_regime_
    performance()). Computed fresh per request; no new GameSaveState
    field."""
    state = await game_state.snapshot()
    return compute_strategy_regime_performance(state.paper_portfolio.trade_history, state.decision_vault)


@router.get("/strategy-live-correlation", response_model=StrategyLiveCorrelationSummary)
async def get_strategy_live_correlation() -> StrategyLiveCorrelationSummary:
    """CEO directive "Complete Trade Provenance," Part 14 — real
    strategy-pair correlation over LIVE trade returns (see
    app/performance_attribution.py's compute_strategy_live_correlation()
    for the exact method — real trades aggregated to one average pnl%
    per shared real sim day, correlated via the same
    pearson_correlation() app/strategy_tournament.py's backtest-only
    version already reuses). `correlation` is honestly `null` below 3
    real paired days, never a fabricated `0.0`. Computed fresh per
    request; no new GameSaveState field."""
    state = await game_state.snapshot()
    return compute_strategy_live_correlation(state.paper_portfolio.trade_history, state.decision_vault)


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


@router.get("/strategy-capital-allocation", response_model=StrategyCapitalAllocationSummary)
async def get_strategy_capital_allocation() -> StrategyCapitalAllocationSummary:
    """CEO directive "Portfolio Construction, Capital Allocation &
    Execution Realism," Phase 5 — an informational evidence roster for
    the CEO's own manual per-strategy `allocatedCapital` decision (see
    app/performance_attribution.py's compute_strategy_capital_allocation_
    evidence()). Never sorts by or surfaces a system-generated ranking;
    joins only already-real, already-computed sources. Computed fresh
    per request; no new GameSaveState field."""
    state = await game_state.snapshot()
    sessions = compute_strategy_session_performance(state.paper_portfolio.trade_history, state.decision_vault)
    regimes = compute_strategy_regime_performance(state.paper_portfolio.trade_history, state.decision_vault)
    return compute_strategy_capital_allocation_evidence(
        state.strategies,
        state.paper_portfolio.trade_history,
        state.decision_vault,
        sessions,
        regimes,
        state.portfolio_intelligence.strategy_exposure,
    )


@router.get("/strategy-degradation", response_model=StrategyDegradationSummary)
async def get_strategy_degradation() -> StrategyDegradationSummary:
    """CEO directive "Portfolio Construction, Capital Allocation &
    Execution Realism," Phase 6 — normal variation vs. a real,
    evidence-backed degradation warning (see app/performance_attribution.
    py's compute_strategy_degradation()). Never auto-retires anything on
    a tiny sample. Computed fresh per request; no new GameSaveState
    field."""
    state = await game_state.snapshot()
    return compute_strategy_degradation(
        state.strategies,
        state.paper_portfolio.trade_history,
        state.decision_vault,
        state.failure_classifications,
    )


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


@router.get("/opportunity-feed", response_model=OpportunityFeed)
async def get_opportunity_feed() -> OpportunityFeed:
    """CEO directive "Professional Quant Trading Core," Rule 25/26 — the
    CEO Opportunity Feed (BEST CURRENT OPPORTUNITIES / WATCHLIST /
    AVOID). See app/opportunity_feed.py's own module docstring for
    exactly which already-real system backs each bucket and the honest
    scope boundary (not a whole-universe proactive scanner). Computed
    fresh per request; no new GameSaveState field, nothing here gates
    or scores anything."""
    state = await game_state.snapshot()
    return compute_opportunity_feed(state)


@router.get("/watchlist-eligibility", response_model=WatchlistEligibilitySummary)
async def get_watchlist_eligibility() -> WatchlistEligibilitySummary:
    """CEO directive "Professional Quant Trading Core," Phase B P2 item
    — a formal, standing per-symbol Watchlist Eligibility Tier, distinct
    from the Opportunity Feed's own per-candidate status above. See
    app/watchlist_eligibility.py's own module docstring for the real
    tier logic (reuses app/performance_attribution.py's real per-symbol
    win-rate/expectancy). Computed fresh per request; no new
    GameSaveState field, nothing here gates or scores anything."""
    state = await game_state.snapshot()
    return compute_watchlist_eligibility(state.watchlist, state.paper_portfolio.trade_history, state.opportunity_rejections)


# CEO directive "...then Paper-Trade Journal + Drift Detection + Strategy
# Health State Machine" — Journal reads/writes live here, alongside every
# other real trade-history read in this file. Drift/Health reads are
# also here rather than a new router (same "extend before build" call as
# strategy-degradation/strategy-live-vs-backtest above, which already
# live in this exact file for the same real reason: they read the same
# `state.strategies`/`trade_history` this router already has in scope).


class AddPaperTradeJournalNoteRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    text: str


@router.get("/journal", response_model=list[PaperTradeJournalEntry])
async def get_paper_trade_journal(limit: int = 50) -> list[PaperTradeJournalEntry]:
    """CEO directive "...then Paper-Trade Journal..." — the permanent,
    per-closed-trade journal (see app/schemas.py's PaperTradeJournalEntry
    docstring). Newest last, matching every other permanent list in this
    codebase; `limit` (default 50, capped at the real MAX_PAPER_TRADE_
    JOURNAL=200) trims from the oldest end of the slice, never a random
    sample."""
    state = await game_state.snapshot()
    limit = max(1, min(limit, 200))
    return state.paper_trade_journal[-limit:]


@router.get("/journal/{entry_id}", response_model=PaperTradeJournalEntry)
async def get_paper_trade_journal_entry(entry_id: str) -> PaperTradeJournalEntry:
    state = await game_state.snapshot()
    entry = next((e for e in state.paper_trade_journal if e.id == entry_id), None)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"No paper trade journal entry with id {entry_id!r}.")
    return entry


@router.post("/journal/{entry_id}/notes", response_model=PaperTradeJournalEntry)
async def add_paper_trade_journal_note(entry_id: str, payload: AddPaperTradeJournalNoteRequest) -> PaperTradeJournalEntry:
    state, entry, error = await game_state.add_paper_trade_journal_note(entry_id, text=payload.text)
    if error is not None or entry is None:
        raise HTTPException(status_code=400, detail=error or "Failed to add journal note.")
    persist_modules(state)
    return entry


@router.get("/drift-events", response_model=list[DriftEvent])
async def get_drift_events(strategy_id: str | None = None, limit: int = 50) -> list[DriftEvent]:
    """CEO directive "...then...Drift Detection Engine" — the real,
    persisted, per-(strategy, category) severity-change event log (see
    app/strategy_drift.py's module docstring — never a duplicate of
    compute_strategy_degradation()'s own live comparison, which this
    reuses unchanged). Newest last; optionally filtered to one real
    strategy."""
    state = await game_state.snapshot()
    events = state.drift_events
    if strategy_id is not None:
        events = [e for e in events if e.strategy_id == strategy_id]
    limit = max(1, min(limit, 200))
    return events[-limit:]


@router.get("/strategy-health", response_model=list[StrategyHealthState])
async def get_strategy_health_states() -> list[StrategyHealthState]:
    """CEO directive "...then...Strategy Health State Machine" — the
    real, persisted, evidence-gated health state for every real Strategy
    that has ever had one computed (see app/strategy_health.py's module
    docstring for the full disclosed reconciliation against
    compute_strategy_health()/compute_strategy_degradation()/
    compute_trading_mode_health()). A Strategy with no entry has never
    had a real drift signal — HEALTHY by construction, not omitted."""
    state = await game_state.snapshot()
    return list(state.strategy_health_states.values())


@router.get("/strategy-health/{strategy_id}", response_model=StrategyHealthState)
async def get_strategy_health_state(strategy_id: str) -> StrategyHealthState:
    state = await game_state.snapshot()
    health = state.strategy_health_states.get(strategy_id)
    if health is None:
        raise HTTPException(status_code=404, detail=f"No health state recorded yet for strategy {strategy_id!r} (still HEALTHY by construction — no real drift signal has ever fired).")
    return health
