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

sharpe_ratio/sortino_ratio are explicitly placeholder return-to-drawdown
ratios, not real risk-adjusted-return statistics — see app/simulation.py's
module docstring for why (no real historical daily-return series exists
yet in v0.5).
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import PaperPortfolio, PaperTrade, PerformancePeriod, PerformanceSnapshot, ResearchItem, TimeState

MAX_PERFORMANCE_SNAPSHOTS = 60


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def research_accuracy(research: list[ResearchItem]) -> float:
    completed = [r for r in research if r.status == "completed"]
    if not completed:
        return 50.0
    accurate = sum(1 for r in completed if r.confidence >= 70.0)
    return accurate / len(completed) * 100


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
    profitable month 3 doesn't get diluted by a rough month 1."""
    start_minutes = _period_start_sim_minutes(period, now)
    all_trades = portfolio.trade_history
    trades = all_trades if start_minutes is None else [t for t in all_trades if t.closed_sim_minutes >= start_minutes]

    if start_minutes is None:
        win_count, loss_count = portfolio.win_count, portfolio.loss_count
        return_pct = portfolio.total_pnl_pct
    else:
        win_count = sum(1 for t in trades if t.pnl > 0)
        loss_count = sum(1 for t in trades if t.pnl <= 0)
        trades_before = [t for t in all_trades if t.closed_sim_minutes < start_minutes]
        baseline = portfolio.starting_balance + sum(t.pnl for t in trades_before)
        period_pnl = sum(t.pnl for t in trades)
        return_pct = (period_pnl / baseline * 100) if baseline else 0.0

    losing_pcts = [t.pnl_pct for t in trades if t.pnl_pct < 0]
    max_drawdown_pct = abs(min([0.0, *losing_pcts]))
    sharpe_ratio = round(return_pct / max(max_drawdown_pct, 1.0), 2)
    sortino_ratio = round(sharpe_ratio * 1.1, 2)
    avg_holding_minutes = sum(t.duration_minutes for t in trades) / len(trades) if trades else 0.0

    return PerformanceSnapshot(
        period=period,
        returnPct=return_pct,
        winRate=win_rate(win_count, loss_count),
        maxDrawdownPct=max_drawdown_pct,
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
