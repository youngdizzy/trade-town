"""Each agent's daily routine. Mirrors frontend/src/game/systems/Schedule.ts — this
is the authoritative copy; the frontend copy is only an offline fallback.

Meetings and break-room visits are NOT modeled here — they're event-driven
overrides NEXUS applies on top of whatever this schedule says (see
app/nexus.py), so a schedule block only ever describes an agent's *default*
behavior when nothing more interesting is happening.

v0.7 Feature 35 — the Living World & Workday System. Every agent's
workday now runs 6:00-20:00 (ending exactly at EVENING_REVIEW_HOUR, the
same real cadence point app/nexus.py already treats as "end of day" and
GameState.advance_time()'s "workday_end" jumps straight to — see
app/state.py), followed by three real, distinct off-duty blocks at the
existing break-room location: a 20:00-22:00 wind-down, a 22:00-24:00
evening activity (both genuinely varied per agent, reflecting their own
personality — see AGENT_PROFILES), and a shared 0:00-6:00 "Sleeping"
block. This is the honest, fully-scoped-down version of the brief's
Employee Residence (ten named rooms) and City Life (ten named outside
locations): no new physical scene was built and no new location data
exists to back either — see docs/Architecture.md's scope-cut note for
why a 2D, tile-based codebase with no indoor-furniture assets in its
supplied asset pack can't honestly back that much new physical space in
one pass. What IS real here: agents genuinely leave their workstations
for a real block of in-game time, the player can genuinely walk up and
talk to them during it (DialogueManager's existing per-task-line
mechanism — see its own AGENT_TASK_LINES — already covers whatever task
label a schedule block names, no new systems needed), and their morning
transition back into the 6:00 block is the same schedule-driven location
change that already existed, honestly standing in for the brief's
"morning routine."
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
        ScheduleBlock(17, 20, "brain-room", "Reviewing overnight positions"),
        ScheduleBlock(20, 22, "break-room", "Trading watchlist stories with whoever's around"),
        ScheduleBlock(22, 24, "break-room", "Reading market history for fun"),
        ScheduleBlock(0, 6, "break-room", "Sleeping"),
    ],
    "atlas": [
        ScheduleBlock(6, 9, "meeting-room", "Reviewing overnight strategy"),
        ScheduleBlock(9, 12, "brain-room", "Assessing agent performance"),
        ScheduleBlock(12, 13, "break-room", "Resting"),
        ScheduleBlock(13, 16, "meeting-room", "Weighing strategic options"),
        ScheduleBlock(16, 20, "brain-room", "Finalizing decisions"),
        ScheduleBlock(20, 22, "break-room", "Reviewing the day one more time before letting it go"),
        ScheduleBlock(22, 24, "break-room", "Reading quietly"),
        ScheduleBlock(0, 6, "break-room", "Sleeping"),
    ],
    "echo": [
        ScheduleBlock(6, 10, "brain-room", "Charting technical patterns"),
        ScheduleBlock(10, 11, "break-room", "Refilling coffee"),
        ScheduleBlock(11, 15, "brain-room", "Studying monitor feeds"),
        ScheduleBlock(15, 16, "lobby", "Stretching legs"),
        ScheduleBlock(16, 20, "brain-room", "Tracking momentum indicators"),
        ScheduleBlock(20, 22, "break-room", "Watching an old chart pattern for fun, off the clock"),
        ScheduleBlock(22, 24, "break-room", "Sketching new indicator ideas in a notebook"),
        ScheduleBlock(0, 6, "break-room", "Sleeping"),
    ],
    "nova": [
        ScheduleBlock(6, 11, "brain-room", "Reading quarterly reports"),
        ScheduleBlock(11, 12, "lobby", "Taking a walk"),
        ScheduleBlock(12, 13, "break-room", "Lunch break"),
        ScheduleBlock(13, 17, "brain-room", "Summarizing research findings"),
        ScheduleBlock(17, 20, "scout-office", "Cross-checking Scout's notes"),
        ScheduleBlock(20, 22, "break-room", "Reading a novel, finally not about markets"),
        ScheduleBlock(22, 24, "break-room", "Journaling a few thoughts from the day"),
        ScheduleBlock(0, 6, "break-room", "Sleeping"),
    ],
    "scribe": [
        ScheduleBlock(6, 9, "brain-room", "Reviewing overnight logs"),
        ScheduleBlock(9, 12, "meeting-room", "Filing yesterday's minutes"),
        ScheduleBlock(12, 13, "break-room", "Resting"),
        ScheduleBlock(13, 17, "brain-room", "Logging research updates"),
        ScheduleBlock(17, 20, "scout-office", "Cross-referencing the archive"),
        ScheduleBlock(20, 22, "break-room", "Writing in a personal journal, just for once"),
        ScheduleBlock(22, 24, "break-room", "Reading quietly"),
        ScheduleBlock(0, 6, "break-room", "Sleeping"),
    ],
    "coach": [
        ScheduleBlock(6, 9, "performance-center", "Reviewing yesterday's paper trades"),
        ScheduleBlock(9, 12, "brain-room", "Observing research in progress"),
        ScheduleBlock(12, 13, "break-room", "Resting"),
        ScheduleBlock(13, 17, "performance-center", "Analyzing confidence calibration"),
        ScheduleBlock(17, 20, "simulation-lab", "Reviewing simulation results"),
        ScheduleBlock(20, 22, "break-room", "Exercising to clear the mind"),
        ScheduleBlock(22, 24, "break-room", "Watching game film, but for fun this time"),
        ScheduleBlock(0, 6, "break-room", "Sleeping"),
    ],
    "sentinel": [
        ScheduleBlock(6, 9, "trading-floor", "Reviewing overnight risk exposure"),
        ScheduleBlock(9, 12, "trading-floor", "Monitoring position sizing"),
        ScheduleBlock(12, 13, "break-room", "Resting"),
        ScheduleBlock(13, 17, "trading-floor", "Evaluating trade candidates"),
        ScheduleBlock(17, 20, "performance-center", "Cross-checking risk against Coach's reports"),
        ScheduleBlock(20, 22, "break-room", "Finally letting the guard down for a few hours"),
        ScheduleBlock(22, 24, "break-room", "Reading, off the clock"),
        ScheduleBlock(0, 6, "break-room", "Sleeping"),
    ],
    "pulse": [
        ScheduleBlock(6, 9, "trading-floor", "Scanning premarket movers"),
        ScheduleBlock(9, 12, "trading-floor", "Watching for breakouts"),
        ScheduleBlock(12, 13, "break-room", "Resting"),
        ScheduleBlock(13, 17, "trading-floor", "Tracking volume spikes"),
        ScheduleBlock(17, 20, "brain-room", "Cross-referencing research with scanner alerts"),
        ScheduleBlock(20, 22, "break-room", "Still glancing at a ticker out of habit"),
        ScheduleBlock(22, 24, "break-room", "Playing a game to unwind"),
        ScheduleBlock(0, 6, "break-room", "Sleeping"),
    ],
    "guardian": [
        ScheduleBlock(6, 9, "trading-floor", "Checking overnight portfolio exposure"),
        ScheduleBlock(9, 12, "trading-floor", "Monitoring concentration risk"),
        ScheduleBlock(12, 13, "break-room", "Resting"),
        ScheduleBlock(13, 17, "trading-floor", "Watching drawdown levels"),
        ScheduleBlock(17, 20, "performance-center", "Reviewing portfolio performance"),
        ScheduleBlock(20, 22, "break-room", "Making sure everything is squared away before bed"),
        ScheduleBlock(22, 24, "break-room", "Reading quietly"),
        ScheduleBlock(0, 6, "break-room", "Sleeping"),
    ],
    "cio": [
        ScheduleBlock(6, 9, "executive-boardroom", "Reviewing overnight department reports"),
        ScheduleBlock(9, 12, "brain-room", "Sitting in on the research desk"),
        ScheduleBlock(12, 13, "break-room", "Resting"),
        ScheduleBlock(13, 16, "trading-floor", "Reviewing risk and execution together"),
        ScheduleBlock(16, 20, "executive-boardroom", "Preparing the executive briefing"),
        ScheduleBlock(20, 22, "break-room", "Reflecting on today's decisions, off the clock"),
        ScheduleBlock(22, 24, "break-room", "Reading, away from the boardroom"),
        ScheduleBlock(0, 6, "break-room", "Sleeping"),
    ],
    "sage": [
        ScheduleBlock(6, 8, "brain-room", "Writing today's question"),
        ScheduleBlock(8, 11, "brain-room", "Listening in on the research desk"),
        ScheduleBlock(11, 12, "trading-floor", "Asking Risk what it's most uncertain about"),
        ScheduleBlock(12, 13, "break-room", "Resting"),
        ScheduleBlock(13, 16, "meeting-room", "Holding a Thinking Session"),
        ScheduleBlock(16, 20, "brain-room", "Reviewing the day's reasoning"),
        ScheduleBlock(20, 22, "break-room", "Sitting quietly with today's question, off the clock"),
        ScheduleBlock(22, 24, "break-room", "Reading something unrelated to work, for once"),
        ScheduleBlock(0, 6, "break-room", "Sleeping"),
    ],
    # v0.7 Feature 39 — the Original Founders. Neither routes through a
    # trading task anywhere in this schedule; both spend their day
    # walking the real campus locations tied to the system cluster each
    # one originated (see app/founders.py's module docstring).
    "keystone": [
        ScheduleBlock(6, 9, "trading-floor", "Reviewing overnight risk with Sentinel and Guardian"),
        ScheduleBlock(9, 11, "executive-boardroom", "Studying yesterday's closed trades for discipline lapses"),
        ScheduleBlock(11, 12, "lobby", "Walking the campus"),
        ScheduleBlock(12, 13, "break-room", "Resting"),
        ScheduleBlock(13, 16, "trading-floor", "Watching how the desk handles pressure"),
        ScheduleBlock(16, 18, "meeting-room", "Holding office hours on risk discipline"),
        ScheduleBlock(18, 20, "executive-boardroom", "Weighing today's decisions against the firm's own history"),
        ScheduleBlock(20, 22, "break-room", "Sitting with the day's numbers, off the clock"),
        ScheduleBlock(22, 24, "break-room", "Reading quietly"),
        ScheduleBlock(0, 6, "break-room", "Sleeping"),
    ],
    "compass": [
        ScheduleBlock(6, 9, "brain-room", "Reading yesterday's research with fresh eyes"),
        ScheduleBlock(9, 11, "brain-room", "Watching the research desk work"),
        ScheduleBlock(11, 12, "lobby", "Walking the campus"),
        ScheduleBlock(12, 13, "break-room", "Resting"),
        ScheduleBlock(13, 16, "meeting-room", "Holding an open discussion on company philosophy"),
        ScheduleBlock(16, 18, "brain-room", "Reviewing the day's reasoning challenges"),
        ScheduleBlock(18, 20, "hall-of-fame", "Looking over the company's own history for lessons"),
        ScheduleBlock(20, 22, "break-room", "Following a curiosity that has nothing to do with work"),
        ScheduleBlock(22, 24, "break-room", "Reading quietly"),
        ScheduleBlock(0, 6, "break-room", "Sleeping"),
    ],
}


def block_for_hour(agent_id: AgentId, hour: int) -> ScheduleBlock:
    for block in AGENT_SCHEDULES[agent_id]:
        if block.start_hour <= hour < block.end_hour:
            return block
    return AGENT_SCHEDULES[agent_id][0]
