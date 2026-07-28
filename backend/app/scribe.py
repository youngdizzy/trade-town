"""ScribeManager — turns what other managers produce into CompanyMemory
records and meeting minutes.

Scribe (the agent) doesn't run any simulation logic of its own beyond its
schedule (see app/schedule.py) — it's the "everyone else's output becomes
the historical record" glue, called from app/nexus.py's tick.
"""
from __future__ import annotations

from app.agents import AGENT_PROFILES
from app.knowledge import derive_lesson
from app.memory import record
from app.schemas import (
    AgentId,
    CoachReport,
    DiscussionMessage,
    HallOfFameEntry,
    MemoryRecord,
    MeetingMinutes,
    PaperOrder,
    PaperTrade,
    ResearchItem,
    ScannerAlert,
    SimulationResult,
    TimeState,
    TradeDecision,
)

# Crossing this confidence on completion also logs a "future trade"
# candidate note — a flag for a human to consider later, not a trade.
# TradeTown v0.3 does not execute trades (see app/market_data.py).
FUTURE_TRADE_CONFIDENCE_THRESHOLD = 85.0


def record_research_completions(memory: list[MemoryRecord], completed: list[ResearchItem]) -> None:
    for item in completed:
        record(memory, "research", item.title, item.summary)
        record(memory, "discovery", f"Discovery: {item.symbol or item.title}", item.summary)
        if item.confidence >= FUTURE_TRADE_CONFIDENCE_THRESHOLD:
            record(
                memory,
                "future_trade",
                f"Candidate flagged: {item.symbol}",
                f"{AGENT_PROFILES[item.assigned_agent].name} finished research on {item.symbol} with "
                f"{item.confidence:.0f}% confidence — flagged as a candidate for future trade consideration. "
                "No trade was placed; TradeTown does not execute trades.",
            )


def build_minutes(participants: list[AgentId], discussion: list[DiscussionMessage], research: list[ResearchItem], new_time: TimeState) -> MeetingMinutes:
    # Only each participant's *current* research focus, matching what
    # discussion.py actually generated lines about — research also holds
    # each agent's completed history (see research.py), and including
    # that here would claim the meeting covered everything an attendee
    # has ever researched instead of what was actually discussed.
    topics = sorted({item.symbol for item in research if item.status == "in_progress" and item.assigned_agent in participants and item.symbol})
    names = ", ".join(AGENT_PROFILES[a].name for a in participants)
    summary = f"{len(participants)} attended: {names}. Discussed {', '.join(topics)}." if topics else f"{len(participants)} attended: {names}."
    return MeetingMinutes(
        id=f"minutes-{new_time.day}-{new_time.hour}-{new_time.minute}",
        day=new_time.day,
        hour=new_time.hour,
        minute=new_time.minute,
        participants=participants,
        summary=summary,
        discussion=discussion,
    )


def record_meeting(memory: list[MemoryRecord], minutes: MeetingMinutes) -> None:
    when = f"Day {minutes.day} {minutes.hour:02d}:{minutes.minute:02d}"
    record(memory, "meeting", f"Meeting — {when}", minutes.summary)
    if minutes.discussion:
        transcript = " / ".join(f"{AGENT_PROFILES[m.speaker].name}: {m.line}" for m in minutes.discussion)
        record(memory, "discussion", f"Discussion — {when}", transcript)


def record_paper_trade(memory: list[MemoryRecord], trade: PaperTrade) -> None:
    """Logs a closed paper trade's outcome, then hands it to
    app/knowledge.py to derive a lesson/mistake record from the same
    trade — see the v0.5 brief's Feature 5 (Learning System) and Feature
    9 (searchable knowledge)."""
    outcome = "gained" if trade.pnl > 0 else "lost"
    record(
        memory,
        "paper_trade",
        f"Paper trade closed: {trade.symbol}",
        f"{trade.symbol} {outcome} {abs(trade.pnl_pct):.1f}% ({trade.pnl:+.2f} simulated) over a "
        f"{trade.duration_minutes}-minute hold. {trade.reason}. No real capital was involved.",
    )
    category, title, body = derive_lesson(trade)
    record(memory, category, title, body)


def record_simulation_result(memory: list[MemoryRecord], result: SimulationResult) -> None:
    record(
        memory,
        "simulation",
        f"Simulation complete: {result.strategy_name}",
        f"{AGENT_PROFILES[result.run_by].name} ran \"{result.strategy_name}\" on {result.symbol}: "
        f"{result.total_return_pct:+.1f}% return, {result.win_rate:.0f}% win rate, "
        f"{result.max_drawdown_pct:.1f}% max drawdown across {result.trade_count} simulated trades. "
        "Historical placeholder data — no real backtest data source is connected yet.",
    )


def record_coach_report(memory: list[MemoryRecord], report: CoachReport) -> None:
    top = f"{AGENT_PROFILES[report.agent_rankings[0].agent_id].name}" if report.agent_rankings else "no ranked agent yet"
    record(
        memory,
        "coach_review",
        f"Coach's {report.period} report",
        f"Company score {report.company_score:.1f}/100. Win rate {report.win_rate:.0f}%, research accuracy "
        f"{report.research_accuracy:.0f}%, risk score {report.risk_score:.0f}/100. Top agent this period: {top}. "
        f"{' '.join(report.recommendations)}",
    )


def record_hall_of_fame_entry(memory: list[MemoryRecord], entry: HallOfFameEntry) -> None:
    record(memory, "event", f"Hall of Fame: {entry.title}", entry.description)


def record_scanner_alert(memory: list[MemoryRecord], alert: ScannerAlert) -> None:
    record(memory, "alert", f"Scanner alert: {alert.symbol}", alert.message)


def record_ceo_decision(memory: list[MemoryRecord], decision: TradeDecision) -> None:
    """Feature 12 — every CEO Approval outcome (a player's real buy/sell/
    wait call, or an unactioned proposal auto-resolved as wait on
    expiry — see app/executive.py's resolve_proposal()) is logged here.
    decision.final_reasoning already states who decided and why, so it's
    used verbatim rather than re-deriving an attribution string."""
    record(memory, "decision", f"CEO decision: {decision.symbol}", decision.final_reasoning)


def record_order_placed(memory: list[MemoryRecord], order: PaperOrder) -> None:
    record(
        memory,
        "order",
        f"Order placed: {order.symbol}",
        f"{AGENT_PROFILES[order.placed_by].name} placed a {order.order_type} {order.side} order for "
        f"{order.quantity:.2f} {order.symbol} — {order.reason}",
    )
