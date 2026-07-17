"""NexusManager — coordinates the AI company.

Responsibilities (per the v0.2 brief): register agents, assign tasks, track
progress, drive the office whiteboards, and call meetings / break-room
visits. NEXUS does not trade and does not connect to markets — every
"discovery" and market headline here is generated placeholder flavor text,
clearly not real data (see MARKET_HEADLINES).

Design note: meetings and break-room visits are both implemented as the
same mechanism — a temporary `AgentOverride` on an agent's location that
takes priority over their normal schedule and expires after N game-minutes
(see AgentOverride in schemas.py). A "meeting" is just that override
applied to several agents at once. This avoids two parallel state machines
for what is structurally the same behavior.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone

from app.agents import AGENT_PROFILES, LOCATION_TO_SCENE, all_agent_ids
from app.schedule import block_for_hour
from app.schemas import (
    AgentId,
    AgentOverride,
    AgentState,
    EntityTransform,
    GameSaveState,
    MemoryEntry,
    MeetingState,
    NewsItem,
    Task,
    TimeState,
)

MAX_MEMORY = 50
MAX_TASKS = 60
# Per-category, not a single shared cap: discovery news fires far more
# often than market/company news (it's tied to every task-changing event
# across four agents, vs. a flat per-tick roll for market headlines), so a
# single shared cap would eventually let discovery evict every market
# headline during normal play, leaving the Market Status panel
# permanently empty. See _trim_news().
MAX_NEWS_PER_CATEGORY = 8

MEETING_CHANCE_PER_TICK = 0.03
MEETING_DURATION_MINUTES = 20
MEETING_MIN_ATTENDEES = 2

BREAK_ENERGY_THRESHOLD = 35
BREAK_CHANCE_PER_TICK = 0.10
BREAK_DURATION_MINUTES = 15
BREAK_ENERGY_BONUS = 20

RESTFUL_LOCATIONS = {"lobby", "break-room"}

DISCOVERY_LINES = [
    "flagged an unusual volume spike worth a second look",
    "found a pattern that held up across three timeframes",
    "cross-referenced two data sources and turned up a discrepancy",
    "spotted a correlation nobody had logged before",
    "finished a backtest that beat the benchmark",
    "caught an outlier the rest of the team had missed",
]

MARKET_HEADLINES = [
    "Markets drift sideways in a quiet overnight session",
    "Analysts split on next move as volume thins",
    "Sector rotation continues into a second week",
    "Volatility index ticks lower for a third straight day",
    "Traders await fresh catalysts amid a slow news cycle",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default_agent_state(agent_id: AgentId) -> AgentState:
    profile = AGENT_PROFILES[agent_id]
    block = block_for_hour(agent_id, 8)
    return AgentState(
        transform=EntityTransform(scene=LOCATION_TO_SCENE[profile.home_location], x=100, y=80, facing="down"),
        location=profile.home_location,
        currentTask=block.task,
        mood=65,
        energy=80,
        memory=[],
        override=None,
    )


def default_agents() -> dict[AgentId, AgentState]:
    return {agent_id: _default_agent_state(agent_id) for agent_id in all_agent_ids()}


def register_agents(state: GameSaveState) -> GameSaveState:
    """Ensures every known agent id has a state entry — self-healing for saves from an older roster."""
    agents = dict(state.agents)
    changed = False
    for agent_id in all_agent_ids():
        if agent_id not in agents:
            agents[agent_id] = _default_agent_state(agent_id)
            changed = True
    return state.model_copy(update={"agents": agents}) if changed else state


def _task_priority(agent_id: AgentId, location: str) -> str:
    if location in RESTFUL_LOCATIONS or location == "meeting-room":
        return "low" if location != "meeting-room" else "high"
    return "high" if agent_id == "atlas" else "normal"


def _override_task_label(reason: str) -> str:
    return "In a meeting" if reason == "meeting" else "Taking a break"


def _tick_agent(
    agent_id: AgentId,
    agent: AgentState,
    new_time: TimeState,
    minutes: int,
    tasks: list[Task],
    news: list[NewsItem],
) -> AgentState:
    profile = AGENT_PROFILES[agent_id]

    if agent.override is not None:
        remaining = agent.override.remaining_minutes - minutes
        if remaining <= 0:
            bonus = BREAK_ENERGY_BONUS if agent.override.reason == "break" else 0
            block = block_for_hour(agent_id, new_time.hour)
            location, task_label = block.location, block.task
            energy = min(100.0, agent.energy + bonus)
            override = None
        else:
            location = agent.override.location
            task_label = _override_task_label(agent.override.reason)
            energy = agent.energy
            override = agent.override.model_copy(update={"remaining_minutes": remaining})
    else:
        block = block_for_hour(agent_id, new_time.hour)
        location, task_label = block.location, block.task
        energy = agent.energy
        override = None

        if energy < BREAK_ENERGY_THRESHOLD and random.random() < BREAK_CHANCE_PER_TICK:
            override = AgentOverride(location="break-room", reason="break", remainingMinutes=BREAK_DURATION_MINUTES)
            location, task_label = override.location, _override_task_label(override.reason)

    energy_delta = 3 if location in RESTFUL_LOCATIONS else -1.5
    energy = min(100.0, max(5.0, energy + energy_delta))
    mood = min(100.0, max(5.0, agent.mood + random.uniform(-2, 2.5)))

    task_changed = task_label != agent.current_task
    memory = agent.memory
    if task_changed:
        memory = [
            *agent.memory,
            MemoryEntry(id=f"{agent_id}-{new_time.day}-{new_time.hour}-{new_time.minute}", summary=f"Started: {task_label}", day=new_time.day, hour=new_time.hour),
        ][-MAX_MEMORY:]

        for existing in tasks:
            if existing.owner == agent_id and existing.status == "working":
                existing.status = "completed"
                existing.completed_at = _now_iso()
        tasks.append(
            Task(
                id=f"task-{agent_id}-{new_time.day}-{new_time.hour}-{new_time.minute}",
                owner=agent_id,
                priority=_task_priority(agent_id, location),  # type: ignore[arg-type]
                description=task_label,
                status="working",
                createdAt=_now_iso(),
                completedAt=None,
            )
        )

        if location not in RESTFUL_LOCATIONS and location != "meeting-room" and random.random() < 0.2:
            news.append(
                NewsItem(
                    id=f"news-{agent_id}-{new_time.day}-{new_time.hour}-{new_time.minute}",
                    headline=f"{profile.name} {random.choice(DISCOVERY_LINES)}.",
                    category="discovery",
                    timestamp=_now_iso(),
                )
            )

    return agent.model_copy(
        update={
            "transform": agent.transform.model_copy(update={"scene": LOCATION_TO_SCENE[location]}),
            "location": location,
            "currentTask": task_label,
            "mood": mood,
            "energy": energy,
            "memory": memory,
            "override": override,
        }
    )


def _maybe_call_meeting(agents: dict[AgentId, AgentState], meeting: MeetingState, new_time: TimeState, news: list[NewsItem]) -> tuple[dict[AgentId, AgentState], MeetingState]:
    if meeting.active:
        still_meeting = [aid for aid in meeting.participants if (override := agents[aid].override) is not None and override.reason == "meeting"]
        if not still_meeting:
            news.append(
                NewsItem(
                    id=f"news-meeting-end-{new_time.day}-{new_time.hour}-{new_time.minute}",
                    headline="The team wrapped up its meeting in the Meeting Room.",
                    category="company",
                    timestamp=_now_iso(),
                )
            )
            return agents, MeetingState(active=False, participants=[])
        return agents, meeting

    if random.random() >= MEETING_CHANCE_PER_TICK:
        return agents, meeting

    available = [aid for aid in all_agent_ids() if agents[aid].override is None]
    if len(available) < MEETING_MIN_ATTENDEES:
        return agents, meeting

    attendees = available if len(available) <= 4 else random.sample(available, k=random.randint(MEETING_MIN_ATTENDEES, len(available)))
    updated = dict(agents)
    for aid in attendees:
        updated[aid] = agents[aid].model_copy(
            update={
                "override": AgentOverride(location="meeting-room", reason="meeting", remainingMinutes=MEETING_DURATION_MINUTES),
                "location": "meeting-room",
                "currentTask": "In a meeting",
                "transform": agents[aid].transform.model_copy(update={"scene": "MeetingRoomScene"}),
            }
        )
    news.append(
        NewsItem(
            id=f"news-meeting-start-{new_time.day}-{new_time.hour}-{new_time.minute}",
            headline=f"Meeting called in the Meeting Room ({', '.join(AGENT_PROFILES[a].name for a in attendees)}).",
            category="company",
            timestamp=_now_iso(),
        )
    )
    return updated, MeetingState(active=True, participants=list(attendees))


def _trim_news(news: list[NewsItem]) -> list[NewsItem]:
    """Keep the most recent MAX_NEWS_PER_CATEGORY items per category
    instead of one global cap on the combined list, so a burst of
    discovery news can't evict every market/company headline. Relative
    chronological order is preserved."""
    counts: dict[str, int] = {}
    keep: list[NewsItem] = []
    for item in reversed(news):
        counts[item.category] = counts.get(item.category, 0) + 1
        if counts[item.category] <= MAX_NEWS_PER_CATEGORY:
            keep.append(item)
    keep.reverse()
    return keep


def _update_whiteboards(agents: dict[AgentId, AgentState], meeting: MeetingState) -> dict[str, str]:
    working = sum(1 for a in agents.values() if a.location not in RESTFUL_LOCATIONS)
    return {
        "scout-office": agents["scout"].current_task,
        "meeting-room": "Meeting in progress" if meeting.active else agents["atlas"].current_task,
        "ceo-office": f"{working} of {len(agents)} agents actively working",
    }


def tick(state: GameSaveState, new_time: TimeState, minutes: int) -> GameSaveState:
    state = register_agents(state)
    tasks = list(state.tasks)
    news = list(state.news)

    agents = {aid: _tick_agent(aid, agent, new_time, minutes, tasks, news) for aid, agent in state.agents.items()}
    agents, meeting = _maybe_call_meeting(agents, state.meeting, new_time, news)

    if random.random() < 0.04:
        news.append(
            NewsItem(
                id=f"news-market-{new_time.day}-{new_time.hour}-{new_time.minute}",
                headline=random.choice(MARKET_HEADLINES),
                category="market",
                timestamp=_now_iso(),
            )
        )

    return state.model_copy(
        update={
            "time": new_time,
            "agents": agents,
            "tasks": tasks[-MAX_TASKS:],
            "news": _trim_news(news),
            "meeting": meeting,
            "whiteboards": _update_whiteboards(agents, meeting),
            "updatedAt": _now_iso(),
        }
    )
