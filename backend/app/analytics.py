"""AnalyticsManager — TradeTown's performance-metrics layer.

Exposes two things: a handful of small, pure metric functions (reused by
both this module's own snapshots and app/coach.py's reports, so the two
never compute "win rate" or "confidence accuracy" two different ways),
and compute_performance_snapshot(), which turns the current paper
portfolio + research state into one PerformanceSnapshot.

Every function here defaults to 50.0 (a neutral midpoint) when there
isn't enough data yet to compute a real number, rather than defaulting
to 0 — a fresh company with zero trades hasn't "failed," it just hasn't
been measured yet, and a 0 would read as a failing score on a dashboard.

PerformanceSnapshot's sharpe_ratio/sortino_ratio (Quantitative Research
& Intelligence System, Piece 3) are REAL, computed from
PaperPortfolio.trade_history's own real, sequential per-trade pnl_pct
returns — mean/population-stdev for Sharpe, mean/downside-deviation for
Sortino. Two honest, disclosed simplifications rather than fabrications:
(1) risk-free rate is assumed 0 — this codebase has no bond/cash-yield
concept to draw a real rate from, and inventing one would itself be a
fabrication; (2) these are PER-TRADE ratios, not annualized — trades
close at irregular sim-minute intervals, so there is no real fixed-
period (daily/weekly) return series to normalize against. Both are real
statistics over a real (if capped at MAX_TRADE_HISTORY=50 in
app/portfolio.py) return sequence — never a fabricated formula.

`app/simulation.py`'s own `SimulationResult.sharpe_ratio/sortino_ratio`
(distinct from the PerformanceSnapshot ones above) remain an explicitly
placeholder return-to-drawdown ratio — that engine has no real per-trade
return sequence backing it at all (only randomly-generated aggregate
scalars), so there is nothing real to compute a real Sharpe/Sortino FROM
there yet.

CEO directive "Professional Quant Firm Phase," Feature 38 — `app/
strategy_engine.py`'s real, bar-by-bar compiled-strategy backtest DOES
have a real per-trade return sequence (`EmaPullbackTradeRecord.
r_multiple_realized`, chronologically ordered by `entry_timestamp`), so
`mean()`/`population_stdev()`/`downside_deviation()` below are exported
(no longer private) specifically so `app/backtest_primitives.py`'s
`aggregate_bucket()` can compute a REAL Sharpe/Sortino for that engine's
own trade buckets using the exact same real, disclosed formulas — never
a second, duplicate statistics implementation. Closed a real fabrication
bug in the process: `app/strategy_engine.py`'s own ad hoc
`SimulationResult` construction had been hardcoding `sharpeRatio=0.0,
sortinoRatio=0.0` as literal placeholders instead of computing them —
see `app/backtest_primitives.py`'s own module docstring for the fix.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

from app.schemas import PaperPortfolio, PaperTrade, PerformancePeriod, PerformanceSnapshot, ResearchItem, TimeState

MAX_PERFORMANCE_SNAPSHOTS = 60


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def population_stdev(values: list[float], mean_value: float) -> float:
    """Population-style stdev (divides by len(values), not len(values)-1)
    — with at most 50 real trades on file (PaperPortfolio.MAX_TRADE_HISTORY
    in app/portfolio.py), this codebase's own real sample is always
    small; a sample-correction factor would overstate a precision this
    data doesn't actually support. Returns 0.0 (undefined) below 2
    values, matching this module's existing "not enough data" fallback
    reasoning."""
    if len(values) < 2:
        return 0.0
    variance = sum((v - mean_value) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def downside_deviation(values: list[float]) -> float:
    """Real Sortino input: root-mean-square of only the sub-zero returns
    (target = 0.0, since this codebase has no real risk-free rate to
    use as the minimum acceptable return — see this module's own
    docstring). Returns 0.0 when there are no losing trades to measure
    downside from."""
    downside = [min(0.0, v) for v in values]
    if not downside:
        return 0.0
    return math.sqrt(sum(d * d for d in downside) / len(downside))


def research_accuracy(research: list[ResearchItem]) -> float:
    completed = [r for r in research if r.status == "completed"]
    if not completed:
        return 50.0
    accurate = sum(1 for r in completed if r.confidence >= 70.0)
    return accurate / len(completed) * 100


def max_drawdown_pct(trades: list[PaperTrade], starting_equity: float, *, current_equity: float | None = None) -> float:
    """Real peak-to-trough drawdown (%) over the closed-trade equity
    curve, in the same chronological order PaperPortfolio.trade_history
    is built in (append-only — see app/portfolio.py::close_position()).
    This is the same peak-vs-cumulative convention already used by
    app/performance_attribution.py::_live_drawdown_usd(),
    app/strategy_lab.py, app/backtest_primitives.py, and app/whatif.py —
    reused here, not reimplemented differently. Unlike
    _live_drawdown_usd() (which stays in dollars because a single
    strategy has no real sub-account equity base to express a percentage
    against), this operates on the whole portfolio, which does have a
    real equity base (`starting_equity`), so a real percentage is
    computable without fabricating one.

    Replaces an earlier proxy that returned only the single worst
    losing trade's own pnl_pct — a real number, but one that understates
    true risk whenever several smaller consecutive losses compound into
    a larger cumulative decline than any one trade shows alone.

    `current_equity` (CEO directive "Portfolio Risk Engine + Firm-Wide
    Risk Governance") — optional, folds today's real live equity (cash +
    mark-to-market of any still-open positions, e.g.
    app/risk_engine.py::portfolio_equity()) into the same real peak/
    trough comparison as one more point AFTER every closed trade, without
    counting it as a trade itself. Omitted (`None`), behavior is
    byte-for-byte identical to before this parameter existed — every
    existing caller computing REALIZED-only drawdown over a historical
    trade window is unaffected. Passed, this correctly catches an
    open position's own real unrealized loss dragging the portfolio into
    a fresh drawdown before that position ever closes — the realized-only
    read would stay silent about that risk until close_position() runs."""
    if starting_equity <= 0:
        return 0.0
    equity = starting_equity
    peak = starting_equity
    worst_pct = 0.0
    for trade in trades:
        equity += trade.pnl
        peak = max(peak, equity)
        if peak > 0:
            worst_pct = max(worst_pct, (peak - equity) / peak * 100)
    if current_equity is not None:
        peak = max(peak, current_equity)
        if peak > 0:
            worst_pct = max(worst_pct, (peak - current_equity) / peak * 100)
    return worst_pct


def real_peak_equity(trades: list[PaperTrade], starting_equity: float, *, current_equity: float | None = None) -> float:
    """The real high-water mark `max_drawdown_pct()` above measures
    against, exposed separately (CEO directive "Portfolio Risk Engine +
    Firm-Wide Risk Governance") for callers that need the peak dollar
    value itself rather than a drawdown percentage from it — e.g. a
    stress test asking "how far would a hypothetical shock push the
    portfolio below its own real peak," not just today's already-
    realized drawdown. Same real peak-tracking walk `max_drawdown_pct()`
    uses internally, so the two can never disagree about what the real
    peak is."""
    if starting_equity <= 0:
        return max(0.0, current_equity or 0.0)
    equity = starting_equity
    peak = starting_equity
    for trade in trades:
        equity += trade.pnl
        peak = max(peak, equity)
    if current_equity is not None:
        peak = max(peak, current_equity)
    return peak


def win_rate(win_count: int, loss_count: int) -> float:
    total = win_count + loss_count
    if total == 0:
        return 50.0
    return win_count / total * 100


def confidence_accuracy(trades: list[PaperTrade]) -> float:
    """A simple calibration score: a confident winner or an unconfident
    loser both score high (confidence tracked the outcome); an
    overconfident loser scores low."""
    if not trades:
        return 50.0
    scores = [t.confidence if t.pnl > 0 else (100.0 - t.confidence) for t in trades]
    return sum(scores) / len(scores)


def average_confidence(research: list[ResearchItem]) -> float:
    active = [r for r in research if r.status in ("in_progress", "completed")]
    if not active:
        return 0.0
    return sum(r.confidence for r in active) / len(active)


def _period_start_sim_minutes(period: PerformancePeriod, now: TimeState) -> int | None:
    """The in-game-clock minute a period began at, aligned to day
    boundaries on TradeTown's own Day-N calendar (see app/portfolio.py's
    sim_minutes() for the same day*1440+hour*60+minute convention).
    `None` means "no lower bound" — all_time is meant to stay genuinely
    cumulative, not windowed."""
    if period == "all_time":
        return None
    if period == "daily":
        start_day = now.day
    elif period == "weekly":
        start_day = now.day - ((now.day - 1) % 7)
    else:  # monthly — 30-day blocks; TradeTown's clock has no real month/year, just an incrementing Day N
        start_day = now.day - ((now.day - 1) % 30)
    return start_day * 1440


def period_profit_dollars(period: PerformancePeriod, portfolio: PaperPortfolio, now: TimeState) -> float:
    """The real dollar sum of `portfolio.trade_history` closed within
    `period`'s current window — the same `_period_start_sim_minutes()`
    filter `compute_performance_snapshot()` uses for its own `returnPct`,
    exposed separately so callers that need a raw dollar figure (v0.7
    Feature 33's Smart Savings Rules) don't have to re-derive it from a
    percentage or duplicate the filtering logic."""
    start_minutes = _period_start_sim_minutes(period, now)
    trades = portfolio.trade_history if start_minutes is None else [t for t in portfolio.trade_history if t.closed_sim_minutes >= start_minutes]
    return sum(t.pnl for t in trades)


def compute_performance_snapshot(period: PerformancePeriod, portfolio: PaperPortfolio, research: list[ResearchItem], now: TimeState) -> PerformanceSnapshot:
    """`period` genuinely filters `portfolio.trade_history` to the matching
    in-game calendar window via PaperTrade.closed_sim_minutes (added in
    v0.6.1 for the Command Center's monthly P&L view — see that field's
    own docstring in app/schemas.py). Earlier versions computed the same
    all-time totals under all four period labels, which is exactly the
    "cumulative P&L disguised as monthly" failure mode the Command Center
    was built to avoid. `returnPct` for a windowed period is relative to the account's
    equity *at the start of that period* (starting_balance plus every
    trade closed before it), not the global starting_balance, so a
    profitable month 3 doesn't get diluted by a rough month 1.
    sharpeRatio/sortinoRatio are real per-trade statistics over this
    same windowed `trades` list's own real pnl_pct sequence — see this
    module's own docstring for the risk-free-rate=0 and
    not-annualized disclosures."""
    start_minutes = _period_start_sim_minutes(period, now)
    all_trades = portfolio.trade_history
    trades = all_trades if start_minutes is None else [t for t in all_trades if t.closed_sim_minutes >= start_minutes]

    if start_minutes is None:
        win_count, loss_count = portfolio.win_count, portfolio.loss_count
        return_pct = portfolio.total_pnl_pct
        baseline = portfolio.starting_balance
    else:
        win_count = sum(1 for t in trades if t.pnl > 0)
        loss_count = sum(1 for t in trades if t.pnl <= 0)
        trades_before = [t for t in all_trades if t.closed_sim_minutes < start_minutes]
        baseline = portfolio.starting_balance + sum(t.pnl for t in trades_before)
        period_pnl = sum(t.pnl for t in trades)
        return_pct = (period_pnl / baseline * 100) if baseline else 0.0

    drawdown_pct = max_drawdown_pct(trades, baseline)

    returns = [t.pnl_pct for t in trades]
    mean_return = mean(returns)
    stdev_return = population_stdev(returns, mean_return)
    downside_dev = downside_deviation(returns)
    sharpe_ratio = round(mean_return / stdev_return, 2) if stdev_return > 0 else 0.0
    sortino_ratio = round(mean_return / downside_dev, 2) if downside_dev > 0 else 0.0
    avg_holding_minutes = sum(t.duration_minutes for t in trades) / len(trades) if trades else 0.0

    return PerformanceSnapshot(
        period=period,
        returnPct=return_pct,
        winRate=win_rate(win_count, loss_count),
        maxDrawdownPct=drawdown_pct,
        sharpeRatio=sharpe_ratio,
        sortinoRatio=sortino_ratio,
        avgHoldingMinutes=round(avg_holding_minutes, 1),
        researchAccuracy=round(research_accuracy(research), 1),
        confidenceAccuracy=round(confidence_accuracy(trades), 1),
        computedAt=_now_iso(),
    )


def record_snapshot(snapshots: list[PerformanceSnapshot], snapshot: PerformanceSnapshot) -> list[PerformanceSnapshot]:
    updated = [*snapshots, snapshot]
    if len(updated) > MAX_PERFORMANCE_SNAPSHOTS:
        del updated[: len(updated) - MAX_PERFORMANCE_SNAPSHOTS]
    return updated
