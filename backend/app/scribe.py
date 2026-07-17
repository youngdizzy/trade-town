"""ScribeManager — turns what other managers produce into CompanyMemory
records and meeting minutes.

Scribe (the agent) doesn't run any simulation logic of its own beyond its
schedule (see app/schedule.py) — it's the "everyone else's output becomes
the historical record" glue, called from app/nexus.py's tick.
"""
from __future__ import annotations

from app.agents import AGENT_PROFILES
from app.memory import record
from app.schemas import AgentId, DiscussionMessage, MemoryRecord, MeetingMinutes, ResearchItem, TimeState

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
