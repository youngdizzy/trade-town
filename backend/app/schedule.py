"""Each agent's daily routine. Mirrors frontend/src/game/systems/Schedule.ts — this
is the authoritative copy; the frontend copy is only an offline fallback.

Meetings and break-room visits are NOT modeled here — they're event-driven
overrides NEXUS applies on top of whatever this schedule says (see
app/nexus.py), so a schedule block only ever describes an agent's *default*
behavior when nothing more interesting is happening.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.schemas import AgentId, AgentLocation


@dataclass(frozen=True)
class ScheduleBlock:
    start_hour: int
    end_hour: int
    location: AgentLocation
    task: str


AGENT_SCHEDULES: dict[AgentId, list[ScheduleBlock]] = {
    "scout": [
        ScheduleBlock(6, 9, "scout-office", "Scanning market news"),
        ScheduleBlock(9, 12, "brain-room", "Back-testing a strategy"),
        ScheduleBlock(12, 13, "lobby", "Resting"),
        ScheduleBlock(13, 17, "scout-office", "Building a research memo"),
        ScheduleBlock(17, 19, "brain-room", "Reviewing overnight positions"),
        ScheduleBlock(19, 22, "lobby", "Resting"),
        ScheduleBlock(22, 24, "scout-office", "Scanning market news"),
        ScheduleBlock(0, 6, "scout-office", "Reviewing overnight positions"),
    ],
    "atlas": [
        ScheduleBlock(6, 9, "meeting-room", "Reviewing overnight strategy"),
        ScheduleBlock(9, 12, "brain-room", "Assessing agent performance"),
        ScheduleBlock(12, 13, "break-room", "Resting"),
        ScheduleBlock(13, 16, "meeting-room", "Weighing strategic options"),
        ScheduleBlock(16, 19, "brain-room", "Finalizing decisions"),
        ScheduleBlock(19, 22, "meeting-room", "Planning tomorrow's priorities"),
        ScheduleBlock(22, 24, "meeting-room", "Reviewing the day"),
        ScheduleBlock(0, 6, "meeting-room", "Standing by"),
    ],
    "echo": [
        ScheduleBlock(6, 10, "brain-room", "Charting technical patterns"),
        ScheduleBlock(10, 11, "break-room", "Refilling coffee"),
        ScheduleBlock(11, 15, "brain-room", "Studying monitor feeds"),
        ScheduleBlock(15, 16, "lobby", "Stretching legs"),
        ScheduleBlock(16, 20, "brain-room", "Tracking momentum indicators"),
        ScheduleBlock(20, 22, "lobby", "Resting"),
        ScheduleBlock(22, 24, "brain-room", "Scanning overnight charts"),
        ScheduleBlock(0, 6, "brain-room", "Monitoring after-hours signals"),
    ],
    "nova": [
        ScheduleBlock(7, 11, "brain-room", "Reading quarterly reports"),
        ScheduleBlock(11, 12, "lobby", "Taking a walk"),
        ScheduleBlock(12, 13, "break-room", "Lunch break"),
        ScheduleBlock(13, 17, "brain-room", "Summarizing research findings"),
        ScheduleBlock(17, 19, "scout-office", "Cross-checking Scout's notes"),
        ScheduleBlock(19, 22, "lobby", "Resting"),
        ScheduleBlock(22, 24, "brain-room", "Reading overnight filings"),
        ScheduleBlock(0, 7, "brain-room", "Reviewing archived reports"),
    ],
    "scribe": [
        ScheduleBlock(6, 9, "brain-room", "Reviewing overnight logs"),
        ScheduleBlock(9, 12, "meeting-room", "Filing yesterday's minutes"),
        ScheduleBlock(12, 13, "break-room", "Resting"),
        ScheduleBlock(13, 17, "brain-room", "Logging research updates"),
        ScheduleBlock(17, 19, "scout-office", "Cross-referencing the archive"),
        ScheduleBlock(19, 22, "lobby", "Resting"),
        ScheduleBlock(22, 24, "brain-room", "Indexing the day's discoveries"),
        ScheduleBlock(0, 6, "brain-room", "Archiving overnight records"),
    ],
    "coach": [
        ScheduleBlock(6, 9, "performance-center", "Reviewing yesterday's paper trades"),
        ScheduleBlock(9, 12, "brain-room", "Observing research in progress"),
        ScheduleBlock(12, 13, "break-room", "Resting"),
        ScheduleBlock(13, 17, "performance-center", "Analyzing confidence calibration"),
        ScheduleBlock(17, 19, "simulation-lab", "Reviewing simulation results"),
        ScheduleBlock(19, 22, "performance-center", "Evening performance review"),
        ScheduleBlock(22, 24, "performance-center", "Drafting recommendations"),
        ScheduleBlock(0, 6, "performance-center", "Standing by"),
    ],
    "sentinel": [
        ScheduleBlock(6, 9, "trading-floor", "Reviewing overnight risk exposure"),
        ScheduleBlock(9, 12, "trading-floor", "Monitoring position sizing"),
        ScheduleBlock(12, 13, "break-room", "Resting"),
        ScheduleBlock(13, 17, "trading-floor", "Evaluating trade candidates"),
        ScheduleBlock(17, 19, "performance-center", "Cross-checking risk against Coach's reports"),
        ScheduleBlock(19, 22, "trading-floor", "Setting tomorrow's risk limits"),
        ScheduleBlock(22, 24, "trading-floor", "Auditing the day's approvals"),
        ScheduleBlock(0, 6, "trading-floor", "Standing watch"),
    ],
    "pulse": [
        ScheduleBlock(6, 9, "trading-floor", "Scanning premarket movers"),
        ScheduleBlock(9, 12, "trading-floor", "Watching for breakouts"),
        ScheduleBlock(12, 13, "break-room", "Resting"),
        ScheduleBlock(13, 17, "trading-floor", "Tracking volume spikes"),
        ScheduleBlock(17, 19, "brain-room", "Cross-referencing research with scanner alerts"),
        ScheduleBlock(19, 22, "trading-floor", "Scanning after-hours activity"),
        ScheduleBlock(22, 24, "trading-floor", "Compiling the day's alerts"),
        ScheduleBlock(0, 6, "trading-floor", "Monitoring overnight volatility"),
    ],
    "guardian": [
        ScheduleBlock(6, 9, "trading-floor", "Checking overnight portfolio exposure"),
        ScheduleBlock(9, 12, "trading-floor", "Monitoring concentration risk"),
        ScheduleBlock(12, 13, "break-room", "Resting"),
        ScheduleBlock(13, 17, "trading-floor", "Watching drawdown levels"),
        ScheduleBlock(17, 19, "performance-center", "Reviewing portfolio performance"),
        ScheduleBlock(19, 22, "trading-floor", "Recommending risk reductions"),
        ScheduleBlock(22, 24, "trading-floor", "Filing the day's exposure report"),
        ScheduleBlock(0, 6, "trading-floor", "Standing watch over the book"),
    ],
}


def block_for_hour(agent_id: AgentId, hour: int) -> ScheduleBlock:
    for block in AGENT_SCHEDULES[agent_id]:
        if block.start_hour <= hour < block.end_hour:
            return block
    return AGENT_SCHEDULES[agent_id][0]
