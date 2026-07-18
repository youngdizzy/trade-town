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

from app.schemas import PaperPortfolio, PaperTrade, PerformancePeriod, PerformanceSnapshot, ResearchItem

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


def compute_performance_snapshot(period: PerformancePeriod, portfolio: PaperPortfolio, research: list[ResearchItem]) -> PerformanceSnapshot:
    """Note: `period` labels *which cadence triggered this computation*
    (daily/weekly/monthly/all_time — see nexus.py's boundary checks), not
    a filtered time window — every snapshot is computed over the full
    current trade history. Filtering trades to an exact calendar window
    would need each PaperTrade to carry its closing sim-day, which v0.5
    doesn't track (see docs/KNOWN_LIMITATIONS.md)."""
    trades = portfolio.trade_history
    losing_pcts = [t.pnl_pct for t in trades if t.pnl_pct < 0]
    max_drawdown_pct = abs(min([0.0, *losing_pcts]))
    sharpe_ratio = round(portfolio.total_pnl_pct / max(max_drawdown_pct, 1.0), 2)
    sortino_ratio = round(sharpe_ratio * 1.1, 2)
    avg_holding_minutes = sum(t.duration_minutes for t in trades) / len(trades) if trades else 0.0

    return PerformanceSnapshot(
        period=period,
        returnPct=portfolio.total_pnl_pct,
        winRate=win_rate(portfolio.win_count, portfolio.loss_count),
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
