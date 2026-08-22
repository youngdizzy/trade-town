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
  - STRATEGY: at the time this module was first written,
    `DecisionVaultEntry.strategy_id` was always `None` on a live Trading
    Floor trade — closed since by CEO directive "Live Trade → Strategy
    Provenance," whose Phase 2 gave the CEO a real, explicit way to
    select a strategy at decision time. See `compute_strategy_
    performance()` below — that directive's own Phase 4, built once the
    blocker it names here was gone.
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
from statistics import pstdev
from typing import Any

from app.portfolio_intelligence import pearson_correlation
from app.schemas import (
    DecisionVaultEntry,
    FailureClassification,
    MarketIntelligenceRegime,
    PaperTrade,
    RegimePerformanceRead,
    RegimePerformanceSummary,
    SessionPerformanceRead,
    SessionPerformanceSummary,
    Strategy,
    StrategyCapitalAllocationRead,
    StrategyCapitalAllocationSummary,
    StrategyDegradationLevel,
    StrategyDegradationRead,
    StrategyDegradationSummary,
    StrategyExposureRead,
    StrategyHealthAssessment,
    StrategyLiveVsBacktestRead,
    StrategyLiveVsBacktestSummary,
    StrategyLiveVsBacktestVerdict,
    StrategyLiveCorrelationRead,
    StrategyLiveCorrelationSummary,
    StrategyPerformanceRead,
    StrategyPerformanceSummary,
    StrategyRegimePerformanceRead,
    StrategyRegimePerformanceSummary,
    StrategySessionPerformanceRead,
    StrategySessionPerformanceSummary,
    SymbolPerformanceRead,
    SymbolPerformanceSummary,
    TradingSession,
)
from app.strategy_lab import HEALTH_RECENT_WINDOW

# CEO directive "Live Trade → Strategy Provenance," Phase 5 — a disclosed,
# arbitrary judgment threshold (same convention as MIN_SYMBOL_SAMPLE_FOR_
# VERDICT above): a live-vs-backtest win-rate gap this wide or wider is
# treated as a real divergence worth flagging, not silently absorbed into
# "consistent." Chosen, not derived — small samples on both sides mean
# a tighter bar would flag noise as signal constantly.
WIN_RATE_DIVERGENCE_THRESHOLD_PCT = 15.0

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


def compute_strategy_performance(trade_history: list[PaperTrade], decision_vault: list[DecisionVaultEntry]) -> StrategyPerformanceSummary:
    """CEO directive "Live Trade → Strategy Provenance," Phase 4 — the
    Strategy Exposure view. Same real Decision Vault join as session/
    regime above, but split into two distinct exclusion counts instead
    of one: a trade can be missing strategy context either because no
    vault entry matches it at all (`unavailable`, same as session/regime's
    single `excluded` count), or because a real vault entry exists but the
    CEO simply never selected a strategy on it (`unknown` — see
    app/trade_attribution.py's three-way provenance split). Collapsing
    those into one number would erase a real, meaningful distinction the
    rest of this codebase already treats as separate."""
    vault_by_trade_id = _vault_entries_by_trade_id(decision_vault)
    by_strategy: dict[str, list[PaperTrade]] = {}
    excluded_no_vault_entry = 0
    excluded_no_strategy_selected = 0
    for trade in trade_history:
        entry = vault_by_trade_id.get(trade.id)
        if entry is None:
            excluded_no_vault_entry += 1
            continue
        if entry.strategy_id is None:
            excluded_no_strategy_selected += 1
            continue
        by_strategy.setdefault(entry.strategy_id, []).append(trade)

    reads = [StrategyPerformanceRead(strategyId=strategy_id, **_group_metrics(trades)) for strategy_id, trades in by_strategy.items()]
    reads.sort(key=lambda r: r.total_pnl, reverse=True)

    return StrategyPerformanceSummary(
        reads=reads,
        tradesExcludedNoStrategySelected=excluded_no_strategy_selected,
        tradesExcludedNoVaultEntry=excluded_no_vault_entry,
        updatedAt=_now_iso(),
    )


def compute_strategy_session_performance(trade_history: list[PaperTrade], decision_vault: list[DecisionVaultEntry]) -> StrategySessionPerformanceSummary:
    """CEO directive "Live Trade → Strategy Provenance," Phase 6 — the
    one real gap left in the session/regime axis: a strategy's own live
    performance, cut by session. Same real Decision Vault join and same
    two distinct exclusion reasons as `compute_strategy_performance()`
    above — grouped on the (strategy_id, session) pair instead of
    strategy_id alone."""
    vault_by_trade_id = _vault_entries_by_trade_id(decision_vault)
    by_strategy_session: dict[tuple[str, TradingSession], list[PaperTrade]] = {}
    excluded_no_vault_entry = 0
    excluded_no_strategy_selected = 0
    for trade in trade_history:
        entry = vault_by_trade_id.get(trade.id)
        if entry is None:
            excluded_no_vault_entry += 1
            continue
        if entry.strategy_id is None:
            excluded_no_strategy_selected += 1
            continue
        by_strategy_session.setdefault((entry.strategy_id, entry.session), []).append(trade)

    reads = [
        StrategySessionPerformanceRead(strategyId=strategy_id, session=session, **_group_metrics(trades))
        for (strategy_id, session), trades in by_strategy_session.items()
    ]
    reads.sort(key=lambda r: r.total_pnl, reverse=True)

    return StrategySessionPerformanceSummary(
        reads=reads,
        tradesExcludedNoStrategySelected=excluded_no_strategy_selected,
        tradesExcludedNoVaultEntry=excluded_no_vault_entry,
        updatedAt=_now_iso(),
    )


def compute_strategy_regime_performance(trade_history: list[PaperTrade], decision_vault: list[DecisionVaultEntry]) -> StrategyRegimePerformanceSummary:
    """CEO directive "Complete Trade Provenance," Part 12 — the
    strategy×regime counterpart to compute_strategy_session_performance()
    above, grouped on the (strategy_id, market_regime) pair instead of
    (strategy_id, session). Same real Decision Vault join, same two
    distinct exclusion reasons — mirrors the session version exactly."""
    vault_by_trade_id = _vault_entries_by_trade_id(decision_vault)
    by_strategy_regime: dict[tuple[str, MarketIntelligenceRegime], list[PaperTrade]] = {}
    excluded_no_vault_entry = 0
    excluded_no_strategy_selected = 0
    for trade in trade_history:
        entry = vault_by_trade_id.get(trade.id)
        if entry is None:
            excluded_no_vault_entry += 1
            continue
        if entry.strategy_id is None:
            excluded_no_strategy_selected += 1
            continue
        by_strategy_regime.setdefault((entry.strategy_id, entry.market_regime), []).append(trade)

    reads = [
        StrategyRegimePerformanceRead(strategyId=strategy_id, regime=regime, **_group_metrics(trades))
        for (strategy_id, regime), trades in by_strategy_regime.items()
    ]
    reads.sort(key=lambda r: r.total_pnl, reverse=True)

    return StrategyRegimePerformanceSummary(
        reads=reads,
        tradesExcludedNoStrategySelected=excluded_no_strategy_selected,
        tradesExcludedNoVaultEntry=excluded_no_vault_entry,
        updatedAt=_now_iso(),
    )


# Same real bar app/strategy_tournament.py's backtest-only
# MIN_PAIRED_WINDOWS_FOR_CORRELATION already uses — not a separately
# invented threshold.
MIN_PAIRED_DAYS_FOR_LIVE_CORRELATION = 3


def compute_strategy_live_correlation(trade_history: list[PaperTrade], decision_vault: list[DecisionVaultEntry]) -> StrategyLiveCorrelationSummary:
    """CEO directive "Complete Trade Provenance," Part 14 — see
    StrategyLiveCorrelationRead's own docstring in schemas.py for the
    full method. Reuses `_trades_by_strategy_id()` (the identical real
    strategy-attribution grouping every other function in this module
    uses) and `pearson_correlation()` directly — never a second
    implementation of either."""
    by_strategy = _trades_by_strategy_id(trade_history, decision_vault)
    daily_returns_by_strategy: dict[str, dict[int, list[float]]] = {}
    for strategy_id, trades in by_strategy.items():
        by_day: dict[int, list[float]] = {}
        for trade in trades:
            sim_day = trade.closed_sim_minutes // 1440
            by_day.setdefault(sim_day, []).append(trade.pnl_pct)
        daily_returns_by_strategy[strategy_id] = {day: [round(_mean(values), 4)] for day, values in by_day.items()}

    strategy_ids = sorted(daily_returns_by_strategy)
    reads: list[StrategyLiveCorrelationRead] = []
    for i, strategy_id_a in enumerate(strategy_ids):
        for strategy_id_b in strategy_ids[i + 1 :]:
            days_a = daily_returns_by_strategy[strategy_id_a]
            days_b = daily_returns_by_strategy[strategy_id_b]
            shared_days = sorted(set(days_a) & set(days_b))
            paired = [(days_a[day][0], days_b[day][0]) for day in shared_days]
            if len(paired) < MIN_PAIRED_DAYS_FOR_LIVE_CORRELATION:
                reads.append(
                    StrategyLiveCorrelationRead(
                        strategyIdA=strategy_id_a,
                        strategyIdB=strategy_id_b,
                        correlation=None,
                        pairedDays=len(paired),
                        detail=f"Only {len(paired)} real paired day(s) where both strategies had a closed trade — below the {MIN_PAIRED_DAYS_FOR_LIVE_CORRELATION}-day bar this module uses for a real correlation read.",
                    )
                )
                continue
            a_values = [p[0] for p in paired]
            b_values = [p[1] for p in paired]
            correlation = round(pearson_correlation(a_values, b_values), 3)
            reads.append(
                StrategyLiveCorrelationRead(
                    strategyIdA=strategy_id_a,
                    strategyIdB=strategy_id_b,
                    correlation=correlation,
                    pairedDays=len(paired),
                    detail=f"Real Pearson correlation over {len(paired)} shared real sim day(s) of average daily pnl% — live trade returns, not a backtest proxy.",
                )
            )

    return StrategyLiveCorrelationSummary(reads=reads, updatedAt=_now_iso())


def compute_strategy_live_vs_backtest(strategy_performance: StrategyPerformanceSummary, health_assessments: list[StrategyHealthAssessment]) -> StrategyLiveVsBacktestSummary:
    """CEO directive "Live Trade → Strategy Provenance," Phase 5 — does a
    strategy's real live performance actually match what its own real
    backtest evidence (StrategyHealthAssessment, Feature 52 Part 2)
    claimed? Joins two already-real, already-computed sources — never
    recomputes either. `health_assessments` is a chronologically-ordered
    list (this codebase's own established convention — see
    app/model_validation.py's own comment on that same ordering
    guarantee); the LAST matching entry per strategy is its most recent
    real assessment. Only compares win_rate_pct — see this module's own
    schema docstring (app/schemas.py's StrategyLiveVsBacktestRead) for
    why expectancy is deliberately never compared (different units,
    R-multiple vs. percent)."""
    latest_health_by_strategy: dict[str, StrategyHealthAssessment] = {}
    for entry in health_assessments:
        latest_health_by_strategy[entry.strategy_id] = entry

    reads: list[StrategyLiveVsBacktestRead] = []
    for live in strategy_performance.reads:
        health: StrategyHealthAssessment | None = latest_health_by_strategy.get(live.strategy_id)
        if health is None:
            reads.append(
                StrategyLiveVsBacktestRead(
                    strategyId=live.strategy_id,
                    liveWinRatePct=live.win_rate_pct,
                    liveTradeCount=live.trade_count,
                    backtestRecentWinRatePct=None,
                    backtestRecentSampleSize=None,
                    winRateDeltaPct=None,
                    verdict="no_backtest_health_on_record",
                    detail="No real StrategyHealthAssessment exists yet for this strategy — it hasn't completed a Market Simulation run.",
                )
            )
            continue

        if live.trade_count < MIN_SYMBOL_SAMPLE_FOR_VERDICT:
            reads.append(
                StrategyLiveVsBacktestRead(
                    strategyId=live.strategy_id,
                    liveWinRatePct=live.win_rate_pct,
                    liveTradeCount=live.trade_count,
                    backtestRecentWinRatePct=health.recent_win_rate,
                    backtestRecentSampleSize=health.recent_sample_size,
                    winRateDeltaPct=None,
                    verdict="not_enough_live_data",
                    detail=f"Only {live.trade_count} live trade(s) with a real, CEO-selected strategy — too few to compare against backtest evidence yet.",
                )
            )
            continue

        delta = round(live.win_rate_pct - health.recent_win_rate, 1)
        verdict: StrategyLiveVsBacktestVerdict = "diverging_from_backtest" if abs(delta) > WIN_RATE_DIVERGENCE_THRESHOLD_PCT else "consistent_with_backtest"
        detail = (
            f"Live win rate {live.win_rate_pct:.0f}% vs. backtest's recent {health.recent_win_rate:.0f}% "
            f"(over {health.recent_sample_size} real simulation run(s)) — a {abs(delta):.1f} point gap."
        )
        reads.append(
            StrategyLiveVsBacktestRead(
                strategyId=live.strategy_id,
                liveWinRatePct=live.win_rate_pct,
                liveTradeCount=live.trade_count,
                backtestRecentWinRatePct=health.recent_win_rate,
                backtestRecentSampleSize=health.recent_sample_size,
                winRateDeltaPct=delta,
                verdict=verdict,
                detail=detail,
            )
        )

    return StrategyLiveVsBacktestSummary(reads=reads, updatedAt=_now_iso())


# CEO directive "Portfolio Construction, Capital Allocation & Execution
# Realism," Phase 5 — a fixed, disclosed sentence for each directive-
# named evidence dimension this codebase genuinely cannot compute for a
# live-traded strategy today, said once here rather than reworded ad hoc
# per row. ROBUSTNESS: strategy_tournament.py's walk-forward/regime-
# stability rounds (its own Rounds 4/6/9) operate only on Sandbox
# CompiledStrategyDefinition backtests against synthetic OHLCV — there is
# no walk-forward window structure for a live-traded Strategy's real,
# irregularly-timed paper trades, and inventing one now would fabricate
# a windowing convention this sim's actual trade cadence doesn't have.
# CORRELATION: a true return-correlation between two strategies' own
# live P&L streams would need synchronized time-bucketing across
# strategies that trade on their own independent schedules — no such
# convention exists anywhere in this codebase (the same real gap
# performance_attribution.py's own module docstring already names for
# the AGENT/TIMEFRAME axes). The real, already-computed alternative
# shown instead is this strategy's own live position-value exposure
# (StrategyExposureRead, app/portfolio_intelligence.py) — a genuinely
# different concept (capital concentration, not return correlation),
# named as such rather than allowed to imply more than it is.
ROBUSTNESS_UNAVAILABLE_NOTE = (
    "Unavailable — walk-forward/regime-stability robustness (see strategy_tournament.py's Rounds 4/6/9) "
    "only exists for Sandbox research candidates on synthetic backtest data; no equivalent windowing "
    "convention exists for a live-traded strategy's own real, irregularly-timed trades."
)


def _correlation_note(exposure: StrategyExposureRead | None) -> str:
    if exposure is None or exposure.position_count == 0:
        return (
            "No real return-correlation-between-strategies metric exists in this codebase (would need "
            "synchronized time-bucketing across independently-scheduled strategies — see this module's "
            "own ROBUSTNESS_UNAVAILABLE_NOTE for the same real gap). No open positions to report exposure for either."
        )
    return (
        f"No real return-correlation-between-strategies metric exists in this codebase (see "
        f"ROBUSTNESS_UNAVAILABLE_NOTE for why). Real position-value exposure instead: "
        f"${exposure.value:,.0f} across {exposure.position_count} open position(s), "
        f"{exposure.pct_of_equity:.1f}% of equity — capital concentration, not a return correlation."
    )


def _live_drawdown_usd(trades: list[PaperTrade]) -> float | None:
    """Real peak-to-trough drawdown of cumulative realized P&L, ordered
    by real closed_at (ISO 8601 strings sort chronologically as-is).
    Dollars, never a percentage — see StrategyCapitalAllocationRead's own
    docstring for why a percentage would need a fabricated sub-account
    equity base this codebase doesn't have."""
    if len(trades) < MIN_SYMBOL_SAMPLE_FOR_VERDICT:
        return None
    ordered = sorted(trades, key=lambda t: t.closed_at)
    cumulative = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for trade in ordered:
        cumulative += trade.pnl
        peak = max(peak, cumulative)
        max_drawdown = max(max_drawdown, peak - cumulative)
    return round(max_drawdown, 2)


def _live_return_volatility_pct(trades: list[PaperTrade]) -> float | None:
    """Real population standard deviation of this strategy's own
    per-trade pnl_pct — a return-volatility read, distinct from the
    ATR/price-volatility concept position_sizing.py's VolatilitySizingRead
    already covers."""
    if len(trades) < MIN_SYMBOL_SAMPLE_FOR_VERDICT:
        return None
    return round(pstdev(t.pnl_pct for t in trades), 2)


def _avg_slippage_bps(trades: list[PaperTrade]) -> tuple[float | None, float | None]:
    if len(trades) < MIN_SYMBOL_SAMPLE_FOR_VERDICT:
        return None, None
    return (
        round(_mean([t.entry_slippage_bps for t in trades]), 2),
        round(_mean([t.exit_slippage_bps for t in trades]), 2),
    )


def _trades_by_strategy_id(trade_history: list[PaperTrade], decision_vault: list[DecisionVaultEntry]) -> dict[str, list[PaperTrade]]:
    """The real trades themselves (not just an already-aggregated *Read),
    grouped the identical way compute_strategy_performance() itself
    groups them — shared by every function below that needs the raw
    trade objects for a strategy rather than pre-aggregated metrics."""
    vault_by_trade_id = _vault_entries_by_trade_id(decision_vault)
    by_strategy: dict[str, list[PaperTrade]] = {}
    for trade in trade_history:
        entry = vault_by_trade_id.get(trade.id)
        if entry is None or entry.strategy_id is None:
            continue
        by_strategy.setdefault(entry.strategy_id, []).append(trade)
    return by_strategy


def compute_strategy_capital_allocation_evidence(
    strategies: list[Strategy],
    trade_history: list[PaperTrade],
    decision_vault: list[DecisionVaultEntry],
    strategy_session_performance: StrategySessionPerformanceSummary,
    strategy_regime_performance: StrategyRegimePerformanceSummary,
    strategy_exposure: list[StrategyExposureRead],
) -> StrategyCapitalAllocationSummary:
    """CEO directive "Portfolio Construction, Capital Allocation &
    Execution Realism," Phase 5 — an informational evidence roster for
    the CEO's own manual `allocated_capital` decision, never a system-
    generated ranking or auto-allocation. Joins only already-real,
    already-computed sources (`compute_strategy_performance()`'s own
    `_group_metrics()`, the already-real `StrategySessionPerformanceSummary`,
    the already-real `StrategyExposureRead` from PortfolioIntelligence) plus
    two genuinely new real reads this phase adds (`_live_drawdown_usd()`,
    `_live_return_volatility_pct()`) — never a second, competing
    expectancy/profit-factor/win-rate calculation.

    Every real `Strategy` in the roster gets a row, including one with
    zero live trades (`evidence_state = "no_live_trades_yet"`, every
    derived metric `None` — its real `allocated_capital` still shows,
    since that field exists independently of live trade history)."""
    live = compute_strategy_performance(trade_history, decision_vault)
    live_by_strategy_id = {read.strategy_id: read for read in live.reads}
    sessions_by_strategy_id: dict[str, list[StrategySessionPerformanceRead]] = {}
    for session_read in strategy_session_performance.reads:
        sessions_by_strategy_id.setdefault(session_read.strategy_id, []).append(session_read)
    regimes_by_strategy_id: dict[str, list[StrategyRegimePerformanceRead]] = {}
    for regime_read in strategy_regime_performance.reads:
        regimes_by_strategy_id.setdefault(regime_read.strategy_id, []).append(regime_read)
    exposure_by_strategy_id = {exposure.strategy_id: exposure for exposure in strategy_exposure if exposure.strategy_id is not None}
    trades_by_strategy_id = _trades_by_strategy_id(trade_history, decision_vault)

    reads: list[StrategyCapitalAllocationRead] = []
    for strategy in strategies:
        strategy_trades = trades_by_strategy_id.get(strategy.id, [])
        live_read = live_by_strategy_id.get(strategy.id)
        exposure = exposure_by_strategy_id.get(strategy.id)

        if live_read is None:
            reads.append(
                StrategyCapitalAllocationRead(
                    strategyId=strategy.id,
                    strategyName=strategy.name,
                    stage=strategy.stage,
                    allocatedCapital=strategy.allocated_capital,
                    evidenceState="no_live_trades_yet",
                    tradeCount=0,
                    sessionReads=sessions_by_strategy_id.get(strategy.id, []),
                    regimeReads=regimes_by_strategy_id.get(strategy.id, []),
                    currentExposureValue=exposure.value if exposure else 0.0,
                    currentExposurePctOfEquity=exposure.pct_of_equity if exposure else 0.0,
                    robustnessNote=ROBUSTNESS_UNAVAILABLE_NOTE,
                    correlationNote=_correlation_note(exposure),
                )
            )
            continue

        entry_slippage, exit_slippage = _avg_slippage_bps(strategy_trades)
        reads.append(
            StrategyCapitalAllocationRead(
                strategyId=strategy.id,
                strategyName=strategy.name,
                stage=strategy.stage,
                allocatedCapital=strategy.allocated_capital,
                evidenceState=live_read.evidence_state,
                tradeCount=live_read.trade_count,
                winRatePct=live_read.win_rate_pct,
                expectancyPct=live_read.expectancy_pct,
                profitFactor=live_read.profit_factor,
                liveDrawdownUsd=_live_drawdown_usd(strategy_trades),
                liveReturnVolatilityPct=_live_return_volatility_pct(strategy_trades),
                avgEntrySlippageBps=entry_slippage,
                avgExitSlippageBps=exit_slippage,
                sessionReads=sessions_by_strategy_id.get(strategy.id, []),
                regimeReads=regimes_by_strategy_id.get(strategy.id, []),
                currentExposureValue=exposure.value if exposure else 0.0,
                currentExposurePctOfEquity=exposure.pct_of_equity if exposure else 0.0,
                robustnessNote=ROBUSTNESS_UNAVAILABLE_NOTE,
                correlationNote=_correlation_note(exposure),
            )
        )

    reads.sort(key=lambda r: r.allocated_capital, reverse=True)
    return StrategyCapitalAllocationSummary(reads=reads, minSampleForEvidence=MIN_SYMBOL_SAMPLE_FOR_VERDICT, updatedAt=_now_iso())


# CEO directive "Portfolio Construction, Capital Allocation & Execution
# Realism," Phase 6 — every threshold below is a disclosed, arbitrary
# judgment call (the same convention as WIN_RATE_DIVERGENCE_THRESHOLD_PCT
# above), never derived from a statistical test this sample size could
# actually support. Chosen conservatively: a level only escalates past
# NORMAL_VARIATION when a real signal is unambiguous, per the directive's
# own "don't auto-retire on tiny samples" rule.
CRITICAL_LOSS_STREAK = 4
POSSIBLE_LOSS_STREAK = 3
EXPECTANCY_DETERIORATION_PCT = 3.0
VOLATILITY_REGIME_CHANGE_MULTIPLE = 1.5
EXECUTION_DEGRADATION_BPS = 10.0
ABNORMAL_DRAWDOWN_LOSS_MULTIPLE = 3.0
CRITICAL_DRAWDOWN_LOSS_MULTIPLE = 5.0
REPEATED_INVALIDATION_THRESHOLD = 2


def _consecutive_losses(ordered_trades: list[PaperTrade]) -> int:
    """Real trailing loss streak — how many of this strategy's most
    recent trades, counting back from the end of its own real
    chronological order, were losses (pnl <= 0, the same convention
    close_position() uses) with no win breaking the streak."""
    count = 0
    for trade in reversed(ordered_trades):
        if trade.pnl > 0:
            break
        count += 1
    return count


def _avg_loss_usd(trades: list[PaperTrade]) -> float | None:
    losers = [t.pnl for t in trades if t.pnl <= 0]
    return round(sum(losers) / len(losers), 2) if losers else None


def compute_strategy_degradation(
    strategies: list[Strategy],
    trade_history: list[PaperTrade],
    decision_vault: list[DecisionVaultEntry],
    failure_classifications: list[FailureClassification],
) -> StrategyDegradationSummary:
    """CEO directive "Portfolio Construction, Capital Allocation &
    Execution Realism," Phase 6 — distinguishes normal live-trading
    variation from a real, evidence-backed warning sign, never auto-
    retiring anything on a tiny sample. Every recent-vs-lifetime metric
    pair reuses an already-computed source (`_group_metrics()`,
    `_live_return_volatility_pct()`, `_avg_slippage_bps()`,
    `_live_drawdown_usd()`) computed twice — once over the strategy's own
    most recent `HEALTH_RECENT_WINDOW` trades (the identical recent-
    window convention `app/strategy_lab.py`'s `compute_strategy_health()`
    already established for backtest runs, reused here for live trades),
    once over its full lifetime. `recent_invalidation_count` is the one
    genuinely new join: how many of those recent trades the real,
    already-existing Discipline Chamber (`app/failure_review.py`)
    classified `reason == "bad_thesis"` — a real "this strategy's own
    thesis was wrong again" signal, not a fabricated one."""
    trades_by_strategy_id = _trades_by_strategy_id(trade_history, decision_vault)
    failure_reason_by_trade_id = {fc.trade_id: fc.reason for fc in failure_classifications}

    reads: list[StrategyDegradationRead] = []
    for strategy in strategies:
        strategy_trades = trades_by_strategy_id.get(strategy.id, [])
        if len(strategy_trades) < MIN_SYMBOL_SAMPLE_FOR_VERDICT:
            reads.append(
                StrategyDegradationRead(
                    strategyId=strategy.id,
                    strategyName=strategy.name,
                    level="not_enough_data",
                    signals=[],
                    recentTradeCount=len(strategy_trades),
                    lifetimeTradeCount=len(strategy_trades),
                    consecutiveLosses=_consecutive_losses(strategy_trades),
                    recentInvalidationCount=sum(1 for t in strategy_trades if failure_reason_by_trade_id.get(t.id) == "bad_thesis"),
                )
            )
            continue

        ordered = sorted(strategy_trades, key=lambda t: t.closed_at)
        recent = ordered[-HEALTH_RECENT_WINDOW:]

        lifetime_metrics = _group_metrics(ordered)
        recent_metrics = _group_metrics(recent)
        recent_volatility = _live_return_volatility_pct(recent)
        lifetime_volatility = _live_return_volatility_pct(ordered)
        recent_entry_slip, _recent_exit_slip = _avg_slippage_bps(recent)
        lifetime_entry_slip, _lifetime_exit_slip = _avg_slippage_bps(ordered)
        recent_drawdown = _live_drawdown_usd(recent)
        avg_loss = _avg_loss_usd(ordered)
        consecutive_losses = _consecutive_losses(ordered)
        recent_invalidation_count = sum(1 for t in recent if failure_reason_by_trade_id.get(t.id) == "bad_thesis")

        critical_signals: list[str] = []
        possible_signals: list[str] = []

        if consecutive_losses >= CRITICAL_LOSS_STREAK:
            critical_signals.append(f"Loss clustering — {consecutive_losses} consecutive losing trades.")
        elif consecutive_losses >= POSSIBLE_LOSS_STREAK:
            possible_signals.append(f"Loss clustering — {consecutive_losses} consecutive losing trades.")

        recent_expectancy = recent_metrics["expectancyPct"]
        lifetime_expectancy = lifetime_metrics["expectancyPct"]
        if recent_expectancy is not None and lifetime_expectancy is not None:
            if recent_expectancy < 0 <= lifetime_expectancy:
                critical_signals.append(f"Expectancy deterioration — recent {recent_expectancy:+.2f}% has flipped negative from a lifetime {lifetime_expectancy:+.2f}%.")
            elif recent_expectancy < lifetime_expectancy - EXPECTANCY_DETERIORATION_PCT:
                possible_signals.append(f"Expectancy deterioration — recent {recent_expectancy:+.2f}% vs. lifetime {lifetime_expectancy:+.2f}%.")

        if recent_volatility is not None and lifetime_volatility is not None and lifetime_volatility > 0 and recent_volatility > lifetime_volatility * VOLATILITY_REGIME_CHANGE_MULTIPLE:
            possible_signals.append(f"Volatility regime change — recent return volatility {recent_volatility:.2f}% vs. lifetime {lifetime_volatility:.2f}%.")

        if recent_entry_slip is not None and lifetime_entry_slip is not None and recent_entry_slip > lifetime_entry_slip + EXECUTION_DEGRADATION_BPS:
            possible_signals.append(f"Execution degradation — recent avg entry slippage {recent_entry_slip:.1f} bps vs. lifetime {lifetime_entry_slip:.1f} bps.")

        if recent_drawdown is not None and avg_loss is not None and avg_loss < 0:
            if recent_drawdown > abs(avg_loss) * CRITICAL_DRAWDOWN_LOSS_MULTIPLE:
                critical_signals.append(f"Abnormal drawdown — recent ${recent_drawdown:,.0f} pullback vs. a typical single-trade loss of ${abs(avg_loss):,.0f}.")
            elif recent_drawdown > abs(avg_loss) * ABNORMAL_DRAWDOWN_LOSS_MULTIPLE:
                possible_signals.append(f"Abnormal drawdown — recent ${recent_drawdown:,.0f} pullback vs. a typical single-trade loss of ${abs(avg_loss):,.0f}.")

        if recent_invalidation_count >= REPEATED_INVALIDATION_THRESHOLD:
            critical_signals.append(f"Repeated invalidations — {recent_invalidation_count} of the last {len(recent)} trades were classified 'bad thesis' by the Discipline Chamber.")

        if critical_signals:
            level: StrategyDegradationLevel = "critical_degradation"
            signals = critical_signals + possible_signals
        elif possible_signals:
            level = "possible_degradation"
            signals = possible_signals
        else:
            level = "normal_variation"
            signals = []

        reads.append(
            StrategyDegradationRead(
                strategyId=strategy.id,
                strategyName=strategy.name,
                level=level,
                signals=signals,
                recentTradeCount=len(recent),
                lifetimeTradeCount=len(ordered),
                recentExpectancyPct=recent_expectancy,
                lifetimeExpectancyPct=lifetime_expectancy,
                recentReturnVolatilityPct=recent_volatility,
                lifetimeReturnVolatilityPct=lifetime_volatility,
                recentAvgSlippageBps=recent_entry_slip,
                lifetimeAvgSlippageBps=lifetime_entry_slip,
                recentDrawdownUsd=recent_drawdown,
                consecutiveLosses=consecutive_losses,
                recentInvalidationCount=recent_invalidation_count,
            )
        )

    return StrategyDegradationSummary(reads=reads, recentWindowSize=HEALTH_RECENT_WINDOW, minSampleForVerdict=MIN_SYMBOL_SAMPLE_FOR_VERDICT, updatedAt=_now_iso())
