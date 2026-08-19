"""CEO directive "Next Professional Trading Firm Phase," Priority 2 —
Unified Professional P&L/Performance Reporting. Extended by CEO
directive "Next Phase: Professional Trading Firm Intelligence," Phase 3
(Session + Market Regime P&L) — see `compute_session_performance()`/
`compute_regime_performance()` below.

RESEARCH FIRST (per the directive's own mandatory rule): a full audit of
every existing P&L/reporting surface — `app/analytics.py`'s
`PerformanceSnapshot` (win rate, real Sharpe/Sortino, all computed over
the WHOLE trade history), `PerformancePanel.tsx`'s "All-Time Trade
Journal" (the same whole-history rollup, rendered), `app/coach.py`'s
`CoachReport`, `app/decision_vault.py`'s per-trade `DecisionVaultEntry`,
`app/exit_efficiency.py`'s per-trade capture-percent read — found real,
rich PER-TRADE and WHOLE-PORTFOLIO data, but confirmed (grep, zero
matches) no symbol-level, agent-level, or strategy-level P&L
AGGREGATION anywhere. This module adds exactly that one missing axis —
SYMBOL — computed fresh over `state.paper_portfolio.trade_history` (the
same CAGS convention `app/exit_efficiency.py`/`app/session_evidence.py`
already established: no new `GameSaveState` field, nothing persisted,
always current).

WHY ONLY SYMBOL THIS PASS (the directive asked for AGENT, SYMBOL,
STRATEGY, SESSION, TIMEFRAME, and MARKET REGIME breakdowns): SYMBOL is
the one axis with zero apportionment ambiguity and 100% real-data
coverage — every `PaperTrade` already carries its own real `symbol`,
full stop. The others are each blocked for a real, specific reason, not
skipped for convenience:

  - AGENT: a trade carries a real `supportingAgents`/`opposingAgents`
    LIST, not a single owner — there is no existing, CEO-authorized
    rule for how to split credit across multiple agents on one trade
    (even, weighted by role, primary-opener-only?). Inventing one here
    would be a fabricated convention wearing a real metric's name.
  - STRATEGY: `DecisionVaultEntry.strategy_id` is always `None` on a
    live Trading Floor trade (only Research Sandbox-tested strategies
    populate it — see `app/sandbox.py`) — already disclosed by the
    Session Trading Education work.
  - TIMEFRAME: no per-trade "chart timeframe analyzed" concept exists
    anywhere in this codebase to group by — `PerformancePeriod`
    (today/week/month) already covers time-BUCKETED reporting and isn't
    duplicated here.

SESSION / MARKET REGIME (Phase 3, previously deferred, now built): the
prior deferral was real — `DecisionVaultEntry` carries `session`/
`market_regime` per trade, but at the time only trades closed through
the CEO-proposal path got a vault entry at all; a join would have
silently under-reported day-end-flattened trades. `app/nexus.py`'s
Phase 2 fix (merging `flattened_trades` into the same real closed-trade
list every other close already flows through) closed that gap, so this
join is now honest. A trade with genuinely no matching vault entry
(the disclosed edge case in `app/trade_attribution.py`'s own docstring
— an evicted decision, or the still-unreachable broker order-book path)
is EXCLUDED from these two breakdowns, not silently zero-filled — see
`trades_excluded_no_vault_entry` on each summary.

THE METRICS: `win_rate_pct` (the same `pnl > 0` win / `pnl <= 0` loss
convention `app/portfolio.py::close_position()` already uses, so a
symbol's win count here always agrees with the portfolio-wide one).
`expectancy_pct` is the standard win-rate/avg-win/avg-loss decomposition
— algebraically identical to the simple `avg_pnl_pct` under this same
partition (see this module's own test for why), exposed because the
decomposition itself (avg_winner_pct vs. avg_loser_pct) is diagnostic.
`profit_factor` (gross profit / gross loss) is `None` — a real
"undefined," never a fabricated infinity — when a symbol has zero
losing trades yet. Both `expectancy_pct` and `profit_factor` are
withheld (`None`, `evidence_state = "not_enough_data"`) below
`MIN_SYMBOL_SAMPLE_FOR_VERDICT` trades; raw counts and `total_pnl` still
show regardless, since those are real at any sample size.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.schemas import (
    DecisionVaultEntry,
    MarketIntelligenceRegime,
    PaperTrade,
    RegimePerformanceRead,
    RegimePerformanceSummary,
    SessionPerformanceRead,
    SessionPerformanceSummary,
    SymbolPerformanceRead,
    SymbolPerformanceSummary,
    TradingSession,
)

# Disclosed, arbitrary floor — matches this session's existing precedent
# (MIN_ACCURACY_SAMPLE_FOR_VERDICT / MIN_CONTROL_SAMPLE_FOR_VERDICT /
# MIN_SESSION_REGIME_SAMPLE) for "enough real trades to trust a derived
# ratio, not just a raw count." Reused for the symbol/session/regime
# breakdowns alike — the same real-sample-size reasoning applies to all
# three axes.
MIN_SYMBOL_SAMPLE_FOR_VERDICT = 3


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


def _group_metrics(trades: list[PaperTrade]) -> dict[str, Any]:
    """The 12 real, shared metric fields every SYMBOL/SESSION/REGIME
    breakdown computes identically over its own trade group — see this
    module's own docstring for what each one means and why. Returns
    camelCase-keyed kwargs so each caller can splat them straight into
    its own Pydantic read model alongside that model's own key field
    (symbol/session/regime)."""
    winners = [t for t in trades if t.pnl > 0]
    losers = [t for t in trades if t.pnl <= 0]
    trade_count = len(trades)
    win_count = len(winners)
    loss_count = len(losers)
    win_rate_pct = round(win_count / trade_count * 100.0, 1) if trade_count else 0.0
    total_pnl = round(sum(t.pnl for t in trades), 2)
    avg_pnl_pct = _mean([t.pnl_pct for t in trades])
    avg_winner_pct = _mean([t.pnl_pct for t in winners]) if winners else None
    avg_loser_pct = _mean([t.pnl_pct for t in losers]) if losers else None

    has_enough_evidence = trade_count >= MIN_SYMBOL_SAMPLE_FOR_VERDICT
    expectancy_pct: float | None = None
    profit_factor: float | None = None
    if has_enough_evidence:
        win_share = win_count / trade_count
        loss_share = loss_count / trade_count
        expectancy_pct = round(win_share * (avg_winner_pct or 0.0) + loss_share * (avg_loser_pct or 0.0), 2)
        gross_profit = sum(t.pnl for t in winners)
        gross_loss_abs = abs(sum(t.pnl for t in losers))
        profit_factor = round(gross_profit / gross_loss_abs, 2) if gross_loss_abs > 0 else None

    return {
        "tradeCount": trade_count,
        "winCount": win_count,
        "lossCount": loss_count,
        "winRatePct": win_rate_pct,
        "totalPnl": total_pnl,
        "avgPnlPct": avg_pnl_pct,
        "avgWinnerPct": avg_winner_pct,
        "avgLoserPct": avg_loser_pct,
        "expectancyPct": expectancy_pct,
        "profitFactor": profit_factor,
        "avgMaePct": _mean([t.mae_pct for t in trades]),
        "avgMfePct": _mean([t.mfe_pct for t in trades]),
        "bestTradePnlPct": max(t.pnl_pct for t in trades),
        "worstTradePnlPct": min(t.pnl_pct for t in trades),
        "evidenceState": "sufficient_evidence" if has_enough_evidence else "not_enough_data",
    }


def compute_symbol_performance(trade_history: list[PaperTrade]) -> SymbolPerformanceSummary:
    by_symbol: dict[str, list[PaperTrade]] = {}
    for trade in trade_history:
        by_symbol.setdefault(trade.symbol, []).append(trade)

    reads = [SymbolPerformanceRead(symbol=symbol, **_group_metrics(trades)) for symbol, trades in by_symbol.items()]
    reads.sort(key=lambda r: r.total_pnl, reverse=True)

    return SymbolPerformanceSummary(reads=reads, updatedAt=_now_iso())


def _vault_entries_by_trade_id(decision_vault: list[DecisionVaultEntry]) -> dict[str, DecisionVaultEntry]:
    return {entry.trade_id: entry for entry in decision_vault}


def compute_session_performance(trade_history: list[PaperTrade], decision_vault: list[DecisionVaultEntry]) -> SessionPerformanceSummary:
    vault_by_trade_id = _vault_entries_by_trade_id(decision_vault)
    by_session: dict[TradingSession, list[PaperTrade]] = {}
    excluded = 0
    for trade in trade_history:
        entry = vault_by_trade_id.get(trade.id)
        if entry is None:
            excluded += 1
            continue
        by_session.setdefault(entry.session, []).append(trade)

    reads = [SessionPerformanceRead(session=session, **_group_metrics(trades)) for session, trades in by_session.items()]
    reads.sort(key=lambda r: r.total_pnl, reverse=True)

    return SessionPerformanceSummary(reads=reads, tradesExcludedNoVaultEntry=excluded, updatedAt=_now_iso())


def compute_regime_performance(trade_history: list[PaperTrade], decision_vault: list[DecisionVaultEntry]) -> RegimePerformanceSummary:
    vault_by_trade_id = _vault_entries_by_trade_id(decision_vault)
    by_regime: dict[MarketIntelligenceRegime, list[PaperTrade]] = {}
    excluded = 0
    for trade in trade_history:
        entry = vault_by_trade_id.get(trade.id)
        if entry is None:
            excluded += 1
            continue
        by_regime.setdefault(entry.market_regime, []).append(trade)

    reads = [RegimePerformanceRead(regime=regime, **_group_metrics(trades)) for regime, trades in by_regime.items()]
    reads.sort(key=lambda r: r.total_pnl, reverse=True)

    return RegimePerformanceSummary(reads=reads, tradesExcludedNoVaultEntry=excluded, updatedAt=_now_iso())
