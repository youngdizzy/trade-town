"""Scout's daily routine. Mirrors frontend/src/game/systems/Schedule.ts — this is the
authoritative copy; the frontend copy is only an offline fallback."""
from __future__ import annotations

from dataclasses import dataclass

from app.schemas import ScoutLocation


@dataclass(frozen=True)
class ScheduleBlock:
    start_hour: int
    end_hour: int
    location: ScoutLocation
    task: str


SCOUT_SCHEDULE: list[ScheduleBlock] = [
    ScheduleBlock(6, 9, "scout-office", "Scanning market news"),
    ScheduleBlock(9, 12, "brain-room", "Back-testing a strategy"),
    ScheduleBlock(12, 13, "lobby", "Resting"),
    ScheduleBlock(13, 17, "scout-office", "Building a research memo"),
    ScheduleBlock(17, 19, "brain-room", "Reviewing overnight positions"),
    ScheduleBlock(19, 22, "lobby", "Resting"),
    ScheduleBlock(22, 24, "scout-office", "Scanning market news"),
    ScheduleBlock(0, 6, "scout-office", "Reviewing overnight positions"),
]


def block_for_hour(hour: int) -> ScheduleBlock:
    for block in SCOUT_SCHEDULE:
        if block.start_hour <= hour < block.end_hour:
            return block
    return SCOUT_SCHEDULE[0]
