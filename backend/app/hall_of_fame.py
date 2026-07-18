"""HallOfFameManager — evaluates the company's own current-best records
each tick and files a new entry whenever one is actually broken. Never
retroactively rewrites history: once filed, an entry stays in the Hall
of Fame even if a later run doesn't beat it — the record itself is the
trophy, not a leaderboard slot that can be evicted.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.agents import AGENT_PROFILES
from app.schemas import (
    AgentId,
    AgentScore,
    CoachReport,
    HallOfFameCategory,
    HallOfFameEntry,
    PaperTrade,
    ResearchItem,
    SimulationResult,
    TimeState,
)

MAX_HALL_OF_FAME = 40


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _best_value(entries: list[HallOfFameEntry], category: HallOfFameCategory, *, higher_is_better: bool) -> float | None:
    values = [e.value for e in entries if e.category == category]
    if not values:
        return None
    return max(values) if higher_is_better else min(values)


def _maybe_file(
    entries: list[HallOfFameEntry],
    *,
    category: HallOfFameCategory,
    title: str,
    description: str,
    agent_id: AgentId | None,
    value: float,
    higher_is_better: bool,
    new_time: TimeState,
) -> list[HallOfFameEntry]:
    best = _best_value(entries, category, higher_is_better=higher_is_better)
    beats = best is None or (value > best if higher_is_better else value < best)
    if not beats:
        return entries
    entry = HallOfFameEntry(
        id=f"hof-{category}-{new_time.day}-{new_time.hour}-{new_time.minute}",
        category=category,
        title=title,
        description=description,
        agentId=agent_id,
        value=value,
        achievedAt=_now_iso(),
    )
    updated = [*entries, entry]
    if len(updated) > MAX_HALL_OF_FAME:
        del updated[: len(updated) - MAX_HALL_OF_FAME]
    return updated


def _current_streak(trades: list[PaperTrade]) -> int:
    streak = 0
    for trade in reversed(trades):
        if trade.pnl <= 0:
            break
        streak += 1
    return streak


def evaluate_hall_of_fame(
    entries: list[HallOfFameEntry],
    *,
    completed_research: list[ResearchItem],
    completed_simulations: list[SimulationResult],
    all_trades: list[PaperTrade],
    coach_report: CoachReport | None,
    confidence_accuracy_value: float | None,
    new_time: TimeState,
) -> list[HallOfFameEntry]:
    for item in completed_research:
        entries = _maybe_file(
            entries,
            category="best_research",
            title=f"Best research: {item.symbol or item.title}",
            description=f"{AGENT_PROFILES[item.assigned_agent].name} completed \"{item.title}\" at {item.confidence:.0f}% confidence.",
            agent_id=item.assigned_agent,
            value=item.confidence,
            higher_is_better=True,
            new_time=new_time,
        )

    for result in completed_simulations:
        entries = _maybe_file(
            entries,
            category="best_strategy",
            title=f"Best strategy: {result.strategy_name}",
            description=f"{AGENT_PROFILES[result.run_by].name}'s \"{result.strategy_name}\" run on {result.symbol} returned {result.total_return_pct:.1f}%.",
            agent_id=result.run_by,
            value=result.total_return_pct,
            higher_is_better=True,
            new_time=new_time,
        )
        entries = _maybe_file(
            entries,
            category="best_simulation",
            title=f"Highest simulation win rate: {result.strategy_name}",
            description=f"\"{result.strategy_name}\" on {result.symbol} hit a {result.win_rate:.1f}% simulated win rate.",
            agent_id=result.run_by,
            value=result.win_rate,
            higher_is_better=True,
            new_time=new_time,
        )
        entries = _maybe_file(
            entries,
            category="lowest_drawdown",
            title=f"Lowest drawdown: {result.strategy_name}",
            description=f"\"{result.strategy_name}\" on {result.symbol} kept drawdown to {result.max_drawdown_pct:.1f}%.",
            agent_id=result.run_by,
            value=result.max_drawdown_pct,
            higher_is_better=False,
            new_time=new_time,
        )

    streak = _current_streak(all_trades)
    if streak > 0:
        entries = _maybe_file(
            entries,
            category="winning_streak",
            title=f"{streak}-trade winning streak",
            description=f"TradeTown closed {streak} consecutive winning paper trades.",
            agent_id=None,
            value=float(streak),
            higher_is_better=True,
            new_time=new_time,
        )

    if confidence_accuracy_value is not None:
        entries = _maybe_file(
            entries,
            category="highest_confidence_accuracy",
            title="Highest confidence calibration",
            description=f"Confidence-to-outcome calibration reached {confidence_accuracy_value:.1f}%.",
            agent_id=None,
            value=confidence_accuracy_value,
            higher_is_better=True,
            new_time=new_time,
        )

    if coach_report is not None:
        # "Best monthly performance" per the v0.5 brief — weekly reports
        # still feed agent_rankings (below) but don't file their own
        # best_month entry, since there is no matching weekly category.
        if coach_report.period == "monthly":
            entries = _maybe_file(
                entries,
                category="best_month",
                title="Best monthly company score",
                description=f"TradeTown scored {coach_report.company_score:.1f}/100 for the monthly period ending Day {new_time.day}.",
                agent_id=None,
                value=coach_report.company_score,
                higher_is_better=True,
                new_time=new_time,
            )
        top: AgentScore | None = coach_report.agent_rankings[0] if coach_report.agent_rankings else None
        if top is not None:
            entries = _maybe_file(
                entries,
                category="top_agent",
                title=f"Top agent: {AGENT_PROFILES[top.agent_id].name}",
                description=f"{AGENT_PROFILES[top.agent_id].name} led the {coach_report.period} rankings with a score of {top.score:.1f}.",
                agent_id=top.agent_id,
                value=top.score,
                higher_is_better=True,
                new_time=new_time,
            )

    return entries
