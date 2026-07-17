"""DiscussionManager — the placeholder conversation generated when a
meeting starts, tied to whatever each participant is currently
researching (see app/research.py). Lines are templated, not model-
generated (the v0.3 brief is explicit that placeholder text is fine here)
— what's real is that the discussion is driven by actual research state
and gets recorded by Scribe into CompanyMemory (app/scribe.py), not that
the dialogue itself is AI-written.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone

from app.schemas import AgentId, DiscussionMessage, ResearchItem

_ROLE_LINES: dict[AgentId, list[str]] = {
    "scout": [
        "Wire feeds are lighting up on {topic}. Flagging it for the team.",
        "Nothing alpha-worthy on {topic} yet, but I'm still watching the tape.",
    ],
    "echo": [
        "Price on {topic} is holding above its recent average.",
        "Technicals on {topic} still look constructive to me.",
    ],
    "nova": [
        "Fundamentals on {topic} remain solid based on what I've read.",
        "The numbers behind {topic} still support the thesis.",
    ],
    "atlas": [
        "Noted. Let's keep monitoring {topic}.",
        "Good work — continue tracking {topic} and report back.",
    ],
    "scribe": [
        "Recording this for the minutes.",
        "Noted for the record.",
    ],
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def generate_discussion(participants: list[AgentId], research: list[ResearchItem], day: int, hour: int, minute: int) -> list[DiscussionMessage]:
    """One line per participant, generated once when the meeting starts —
    see MeetingState.discussion, which carries this transcript through to
    meeting-end so Scribe can turn it into minutes."""
    active_by_agent = {item.assigned_agent: item for item in research if item.status == "in_progress"}
    messages: list[DiscussionMessage] = []
    for index, agent_id in enumerate(participants):
        item = active_by_agent.get(agent_id)
        topic = item.symbol or item.title if item is not None else "the watchlist"
        templates = _ROLE_LINES.get(agent_id, _ROLE_LINES["scribe"])
        line = random.choice(templates).format(topic=topic)
        messages.append(
            DiscussionMessage(
                id=f"discussion-{day}-{hour}-{minute}-{index}-{agent_id}",
                speaker=agent_id,
                line=line,
                timestamp=_now_iso(),
            )
        )
    return messages
