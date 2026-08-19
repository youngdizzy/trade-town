"""CEO directive "Next Professional Trading Firm Phase," Priority 2 —
Unified Professional P&L/Performance Reporting.

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
  - SESSION / MARKET REGIME: `DecisionVaultEntry` DOES carry a real
    `session`/`market_regime` per trade, but only for trades closed
    through the CEO-proposal path (`app/nexus.py`'s `build_vault_entry()`
    call site) — broker fills, hold-duration closes, and day-end
    flattens never get a vault entry, so a join against it would silently
    under-report those trades' real P&L rather than including it. A
    partial-coverage join dressed up as a full report is its own kind
    of dishonesty; left for a dedicated pass that either extends vault
    coverage to every close path or discloses the gap explicitly in the
    UI, not smuggled in here.
  - TIMEFRAME: no per-trade "chart timeframe analyzed" concept exists
    anywhere in this codebase to group by — `PerformancePeriod`
    (today/week/month) already covers time-BUCKETED reporting and isn't
    duplicated here.

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

from app.schemas import PaperTrade, SymbolPerformanceRead, SymbolPerformanceSummary

# Disclosed, arbitrary floor — matches this session's existing precedent
# (MIN_ACCURACY_SAMPLE_FOR_VERDICT / MIN_CONTROL_SAMPLE_FOR_VERDICT /
# MIN_SESSION_REGIME_SAMPLE) for "enough real trades to trust a derived
# ratio, not just a raw count."
MIN_SYMBOL_SAMPLE_FOR_VERDICT = 3


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


def _symbol_read(symbol: str, trades: list[PaperTrade]) -> SymbolPerformanceRead:
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

    return SymbolPerformanceRead(
        symbol=symbol,
        tradeCount=trade_count,
        winCount=win_count,
        lossCount=loss_count,
        winRatePct=win_rate_pct,
        totalPnl=total_pnl,
        avgPnlPct=avg_pnl_pct,
        avgWinnerPct=avg_winner_pct,
        avgLoserPct=avg_loser_pct,
        expectancyPct=expectancy_pct,
        profitFactor=profit_factor,
        avgMaePct=_mean([t.mae_pct for t in trades]),
        avgMfePct=_mean([t.mfe_pct for t in trades]),
        bestTradePnlPct=max(t.pnl_pct for t in trades),
        worstTradePnlPct=min(t.pnl_pct for t in trades),
        evidenceState="sufficient_evidence" if has_enough_evidence else "not_enough_data",
    )


def compute_symbol_performance(trade_history: list[PaperTrade]) -> SymbolPerformanceSummary:
    by_symbol: dict[str, list[PaperTrade]] = {}
    for trade in trade_history:
        by_symbol.setdefault(trade.symbol, []).append(trade)

    reads = [_symbol_read(symbol, trades) for symbol, trades in by_symbol.items()]
    reads.sort(key=lambda r: r.total_pnl, reverse=True)

    return SymbolPerformanceSummary(reads=reads, updatedAt=_now_iso())
