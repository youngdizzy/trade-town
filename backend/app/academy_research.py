"""AcademyResearch — the AI Academy's non-market "knowledge" research
projects (v0.7 Feature 25). Mirrors app/research.py's own rotating-queue
shape (progress climbs each tick, completes, rotates onto the next
topic) but keyed to a fixed catalog of knowledge topics instead of a
ticker symbol, since these projects (market history, trading psychology,
...) have no natural watchlist symbol to attach to.

Exactly one project is active company-wide at a time (not one per
agent, unlike research.py's four researchers each running their own) —
the six-topic catalog cycles in a fixed order, and the assigned agent
rotates through every agent except the CIO, who oversees rather than
researches (see app/agents.py). Both rotations are derived from
`completed_count` (the length of the already-persisted completed-
projects list) rather than a separate counter, so no extra state is
needed beyond the list itself.

Every project's summary is real in the sense that it names the actual
assigned agent and topic, but the "content" of a completed project (no
LLM is available to write original research) is the same honestly
templated one-line description used for the whole catalog — see
_TOPIC_CATALOG. This is the Academy's counterpart to Coach/Scribe's
existing "templated framing over real state" convention, applied here
because there is no deeper real content to derive it from.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone

from app.agents import AGENT_PROFILES
from app.schemas import AcademyProject, AcademyTopic, AgentId

MAX_ACADEMY_LIBRARY = 50
PROGRESS_COMPLETE = 100.0
# A bit slower than market research's 2.0-6.0 (research.py) — these are
# meant to read as longer-running projects than a single symbol scan.
PROGRESS_GAIN_RANGE = (1.5, 4.0)

# The CIO oversees the Academy rather than running its projects (mirrors
# research.py excluding Scribe/Coach from RESEARCHER_IDS).
ACADEMY_RESEARCHER_IDS: tuple[AgentId, ...] = ("scout", "atlas", "echo", "nova", "scribe", "coach", "sentinel", "pulse", "guardian")

_TOPIC_CATALOG: tuple[tuple[AcademyTopic, str, str], ...] = (
    ("market_history", 'Studying the 1987 Crash and Black Monday', "a study of historical market panics and what triggered them"),
    ("trading_psychology", "Cataloging Common Trading Psychology Pitfalls", "an examination of the emotional patterns behind overtrading and panic selling"),
    ("economic_concepts", "Explaining Interest Rates and Market Cycles", "a plain-language breakdown of how rate policy moves through the market"),
    ("visualization_tools", "Prototyping a New Confidence Visualization", "design notes for a clearer way to show the desk's own confidence readings"),
    ("decision_biases", "Cataloging Decision-Making Biases in Trading", "a survey of anchoring, recency, and confirmation bias as they show up in trade decisions"),
    ("trading_philosophies", "Comparing Value, Momentum, and Trend-Following Philosophies", "a comparative study of three well-known trading philosophies"),
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _topic_info(topic: AcademyTopic) -> tuple[str, str]:
    for candidate, title, description in _TOPIC_CATALOG:
        if candidate == topic:
            return title, description
    raise ValueError(f"Unknown academy topic {topic!r}")


def _new_project(agent_id: AgentId, topic: AcademyTopic) -> AcademyProject:
    title, description = _topic_info(topic)
    now = _now_iso()
    return AcademyProject(
        id=f"academy-{topic}-{now}",
        topic=topic,
        title=title,
        assignedAgent=agent_id,
        status="in_progress",
        progress=round(random.uniform(2.0, 8.0), 1),
        summary=f"{AGENT_PROFILES[agent_id].name} is getting started: {description}.",
        createdAt=now,
        updatedAt=now,
    )


def default_academy_projects() -> list[AcademyProject]:
    return [_new_project(ACADEMY_RESEARCHER_IDS[0], _TOPIC_CATALOG[0][0])]


def tick_academy_projects(projects: list[AcademyProject], completed_count: int) -> tuple[list[AcademyProject], AcademyProject | None]:
    """Advances the one active project. Returns (updated_active_list,
    newly_completed_or_None) — the caller appends the completed project
    into the permanent Knowledge Library itself and caps it there."""
    if not projects:
        agent = ACADEMY_RESEARCHER_IDS[completed_count % len(ACADEMY_RESEARCHER_IDS)]
        topic = _TOPIC_CATALOG[completed_count % len(_TOPIC_CATALOG)][0]
        return [_new_project(agent, topic)], None

    current = projects[0]
    progress = min(PROGRESS_COMPLETE, current.progress + random.uniform(*PROGRESS_GAIN_RANGE))
    current = current.model_copy(update={"progress": round(progress, 1), "updated_at": _now_iso()})

    if current.progress >= PROGRESS_COMPLETE:
        title, _description = _topic_info(current.topic)
        completed = current.model_copy(update={"status": "completed", "summary": f'{AGENT_PROFILES[current.assigned_agent].name} completed "{title}".'})
        next_count = completed_count + 1
        next_agent = ACADEMY_RESEARCHER_IDS[next_count % len(ACADEMY_RESEARCHER_IDS)]
        next_topic = _TOPIC_CATALOG[next_count % len(_TOPIC_CATALOG)][0]
        return [_new_project(next_agent, next_topic)], completed

    return [current], None
