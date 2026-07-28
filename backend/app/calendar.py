"""CalendarManager — v0.7 Feature 36, the CEO Calendar & Company Schedule.

Aggregates every real, already-computable recurring company event into one
list rather than fabricating the brief's fixed "8:00 Morning Briefing, 8:30
department assignments, 10:00 Research Sessions, ..." company-wide
timetable — that exact hourly choreography doesn't exist in this codebase.
Each of the 11 agents already runs its own believable, personality-distinct
daily schedule (see schedule.py, v0.7 Feature 35), not a single
synchronized company-wide slot system, so reproducing the brief's Example
Day here would misrepresent what actually happens tick to tick.

What IS real and genuinely useful to put on one calendar:
  - The fixed evening/monthly/weekly cadence checkpoints nexus.tick()
    already runs on: Weekly/Monthly Coach Reports, the Monthly Executive
    Review, the Monthly Treasury Savings Report, Weekly/Monthly Reflection
    Sessions, and the daily Question of the Day.
  - The two *conditional* cadences nexus.tick() already gates on (the
    Reasoning Lab challenge and the Academy mentorship check) — this
    module recomputes the exact same real gate those two features already
    use, live, against current data, so the nearest occurrence's
    `eligible` flag is an honest "would this actually fire right now"
    check, never a guess about a day that hasn't arrived yet.
  - Honest ESTIMATED research completion dates, projected from each
    active ResearchItem's real current confidence and the real average
    per-tick confidence-gain rate (research.py's CONFIDENCE_GAIN_RANGE,
    scaled by the real Company Priority research-speed multiplier if
    active) — clearly labeled ESTIMATED, the same "never claim more
    certainty than the data supports" convention the WhatIf Simulation
    Lab's "SIMULATED" badge already established.
  - Player-created custom calendar entries — the one genuinely new piece
    of state this feature adds. These are informational only: creating a
    "Company Holiday" event does not pause research, and an "Extra
    Training Day" does not boost Academy points. Giving player events a
    real mechanical effect on top of the ones Feature 34's Company
    Priority already covers would either duplicate that lever under a new
    name or require fabricating brand-new systems (a payroll/attendance
    model, a training-boost mechanic) with no other grounding anywhere in
    this codebase — cut for the same reason Feature 33's CEO Benefits list
    was cut.

Explicit scope cuts (see docs/Architecture.md for the full note):
  - "Academy Classes" gets no fixed calendar slot or ETA — unlike
    research's steady per-tick confidence gain, Academy project progress
    moves in irregular real bursts (a research completion, a meeting
    attendance) with no steady rate an honest projection could be built
    from.
  - "Department Meetings" gets no fixed slot either — MEETING_CHANCE_PER_TICK
    in nexus.py means meetings are called spontaneously, never on a
    schedule. The calendar surfaces today's real meeting count instead
    (computed client-side from the real meetingMinutes log already
    shipped — see CalendarPanel.tsx).
  - "Employee Birthdays" (marked optional in the brief) is cut outright —
    no agent has a birth date anywhere in this codebase.
  - "Missed Meetings" (the brief's own Executive View field) is cut —
    meetings pick their attendees from whoever's `available` at call
    time; no agent is ever "invited" in a way that could later be marked
    absent.
  - The brief's Guest Lecturer, Academy Exam, Innovation Day, Department
    Workshop, Knowledge Fair, Reflection Conference, Celebration Party,
    and Research Presentation event types have no real system behind them
    anywhere in this codebase and are not fabricated here.
  - "Company Anniversary" is kept, on the same honestly-arbitrary-but-
    fixed-and-disclosed footing this codebase already uses for its 30-day
    "month" (see analytics.py's own note on TradeTown's clock having "no
    real month/year, just an incrementing Day N") — a 365-day "year"
    counted from the real Day 1 start, applied consistently, never hidden.
"""
from __future__ import annotations

from app.academy import MENTORSHIP_GAP_THRESHOLD
from app.research import CONFIDENCE_GAIN_RANGE
from app.schemas import (
    AgentId,
    AgentKnowledgeState,
    CalendarEvent,
    CalendarEventCategory,
    CalendarState,
    Debate,
    PlayerEventCategory,
    ReasoningChallenge,
    ResearchItem,
    TimeState,
    TradeDecision,
)

CALENDAR_HORIZON_DAYS = 35
ANNIVERSARY_INTERVAL_DAYS = 365
MAX_PLAYER_CALENDAR_EVENTS = 60
MAX_TITLE_LENGTH = 140

PLAYER_EVENT_LABEL: dict[PlayerEventCategory, str] = {
    "emergency_meeting": "Emergency Meeting",
    "company_holiday": "Company Holiday",
    "extra_training_day": "Extra Training Day",
    "research_marathon": "Research Marathon",
    "hackathon": "Hackathon",
    "strategy_day": "Strategy Day",
    "celebration": "Celebration",
    "town_hall": "Town Hall Meeting",
    "other": "Custom Event",
}


def default_calendar(now_iso: str) -> CalendarState:
    return CalendarState(systemEvents=[], playerEvents=[], updatedAt=now_iso)


def _daily_days(now: TimeState, at_hour: int) -> list[int]:
    """Every real day within the horizon where `at_hour:00` still lies
    ahead of `now` — including today, unless that hour already passed."""
    days: list[int] = []
    for day in range(now.day, now.day + CALENDAR_HORIZON_DAYS + 1):
        if day == now.day and (now.hour, now.minute) >= (at_hour, 0):
            continue
        days.append(day)
    return days


def _cadence_days(now: TimeState, interval_days: int, at_hour: int) -> list[int]:
    """Every real day within the horizon matching nexus.tick()'s own
    `new_time.day % interval_days == 0` gate, still ahead of `now`."""
    days: list[int] = []
    for day in range(now.day, now.day + CALENDAR_HORIZON_DAYS + 1):
        if day <= 0 or day % interval_days != 0:
            continue
        if day == now.day and (now.hour, now.minute) >= (at_hour, 0):
            continue
        days.append(day)
    return days


def _event(
    category: CalendarEventCategory,
    title: str,
    detail: str,
    day: int,
    hour: int,
    minute: int,
    now_iso: str,
    *,
    eligible: bool | None = None,
) -> CalendarEvent:
    return CalendarEvent(
        id=f"calendar-{category}-{day}-{hour}-{minute}",
        source="system",
        category=category,
        title=title,
        detail=detail,
        day=day,
        hour=hour,
        minute=minute,
        eligible=eligible,
        createdAt=now_iso,
    )


def _reasoning_challenge_eligible(debates: list[Debate], decisions: list[TradeDecision], reasoning_challenges: list[ReasoningChallenge]) -> bool:
    """Mirrors nexus.tick()'s own reasoning-challenge gate exactly (see
    its `is_evening and ... and debates` block) as a pure, non-mutating
    read, so the calendar's `eligible` flag can never drift from the real
    gate that actually decides whether a challenge fires."""
    if not debates:
        return False
    latest_debate = debates[-1]
    linked_decision = next((d for d in decisions if d.id == f"decision-{latest_debate.proposal_id}"), None)
    if linked_decision is None:
        return False
    already_used = bool(reasoning_challenges) and reasoning_challenges[-1].decision_id == linked_decision.id
    return not already_used


def _mentorship_eligible(agent_knowledge: dict[AgentId, AgentKnowledgeState]) -> bool:
    """Mirrors app/academy.py's maybe_run_mentorship() gate exactly, as a
    pure, non-mutating read (no points are awarded here — only nexus.tick()'s
    own real call does that)."""
    if len(agent_knowledge) < 2:
        return False
    ranked = sorted(agent_knowledge.values(), key=lambda s: s.points, reverse=True)
    return ranked[0].points - ranked[-1].points >= MENTORSHIP_GAP_THRESHOLD


def compute_system_events(
    *,
    now: TimeState,
    now_iso: str,
    research: list[ResearchItem],
    debates: list[Debate],
    decisions: list[TradeDecision],
    reasoning_challenges: list[ReasoningChallenge],
    agent_knowledge: dict[AgentId, AgentKnowledgeState],
    research_speed_multiplier: float,
    game_minutes_per_tick: int,
) -> list[CalendarEvent]:
    events: list[CalendarEvent] = []

    for day in _daily_days(now, 8):
        events.append(_event("morning_briefing", "Morning Briefing — Question of the Day", "Sage publishes today's real Question of the Day.", day, 8, 0, now_iso))

    for day in _cadence_days(now, 7, 20):
        events.append(_event("weekly_coach_report", "Weekly Coach Report", "Coach files this week's real performance report.", day, 20, 0, now_iso))
        events.append(_event("weekly_reflection", "Weekly Reflection Session", "The Reflection Chamber holds this week's session.", day, 20, 0, now_iso))

    for day in _cadence_days(now, 30, 20):
        events.append(_event("monthly_coach_report", "Monthly Coach Report", "Coach files this month's real performance report.", day, 20, 0, now_iso))
        events.append(_event("monthly_reflection", "Monthly Reflection Session", "The Reflection Chamber holds this month's session.", day, 20, 0, now_iso))
        events.append(_event("monthly_executive_review", "Monthly Executive Review", "Meridian files this month's real Executive Review.", day, 20, 0, now_iso))
        events.append(_event("monthly_treasury_report", "Monthly Savings Report", "The Treasury files this month's real Savings Report; any active Smart Savings Rules run.", day, 20, 0, now_iso))

    reasoning_days = _cadence_days(now, 2, 20)
    if reasoning_days:
        eligible = _reasoning_challenge_eligible(debates, decisions, reasoning_challenges)
        detail = "A real AI Debate is ready to become a challenge right now." if eligible else "Fires only if a new AI Debate has occurred since the last challenge — none is ready yet."
        events.append(_event("reasoning_challenge_window", "Reasoning Lab Challenge Window", detail, reasoning_days[0], 20, 0, now_iso, eligible=eligible))
        for day in reasoning_days[1:]:
            events.append(_event("reasoning_challenge_window", "Reasoning Lab Challenge Window", "Fires only if a new AI Debate has occurred by then.", day, 20, 0, now_iso))

    mentorship_days = _cadence_days(now, 3, 20)
    if mentorship_days:
        eligible = _mentorship_eligible(agent_knowledge)
        detail = "The real knowledge-points gap is wide enough right now." if eligible else "Fires only if the real knowledge-points gap between the strongest and weakest agent is wide enough — it isn't yet."
        events.append(_event("mentorship_window", "Academy Mentorship Check", detail, mentorship_days[0], 20, 0, now_iso, eligible=eligible))
        for day in mentorship_days[1:]:
            events.append(_event("mentorship_window", "Academy Mentorship Check", "Fires only if the real knowledge-points gap is wide enough by then.", day, 20, 0, now_iso))

    for day in range(now.day + 1, now.day + CALENDAR_HORIZON_DAYS + 1):
        if day % ANNIVERSARY_INTERVAL_DAYS == 0:
            years = day // ANNIVERSARY_INTERVAL_DAYS
            events.append(
                _event(
                    "company_anniversary",
                    f"Company Anniversary — Year {years}",
                    f"{day} in-game days since the real Day 1 founding (a fixed, disclosed {ANNIVERSARY_INTERVAL_DAYS}-day 'year' convention — see this module's docstring).",
                    day,
                    9,
                    0,
                    now_iso,
                )
            )

    avg_gain_per_tick = (sum(CONFIDENCE_GAIN_RANGE) / 2) * max(research_speed_multiplier, 0.01)
    now_minutes = now.day * 1440 + now.hour * 60 + now.minute
    for item in research:
        if item.status != "in_progress":
            continue
        remaining = max(0.0, 100.0 - item.confidence)
        ticks_needed = remaining / avg_gain_per_tick
        eta_minutes_total = now_minutes + ticks_needed * game_minutes_per_tick
        eta_day = int(eta_minutes_total // 1440)
        eta_hour, eta_minute = divmod(int(eta_minutes_total % 1440), 60)
        if eta_day - now.day > CALENDAR_HORIZON_DAYS:
            continue
        events.append(
            _event(
                "research_deadline",
                f"ESTIMATED completion — {item.title}",
                f"Projected from the real current {item.confidence:.0f}% confidence and the real average per-tick gain rate — an estimate, not a guarantee.",
                eta_day,
                eta_hour,
                eta_minute,
                now_iso,
            )
        )

    events.sort(key=lambda e: (e.day, e.hour, e.minute, e.category))
    return events


def create_player_event(
    events: list[CalendarEvent],
    *,
    category: PlayerEventCategory,
    title: str,
    day: int,
    hour: int,
    minute: int,
    now: TimeState,
    now_iso: str,
    event_id: str,
) -> tuple[list[CalendarEvent], str | None]:
    title = title.strip()
    if not title:
        return events, "Event title can't be empty."
    if len(title) > MAX_TITLE_LENGTH:
        return events, f"Event title is too long ({MAX_TITLE_LENGTH} characters max)."
    if not (0 <= hour <= 23):
        return events, "Hour must be between 0 and 23."
    if not (0 <= minute <= 59):
        return events, "Minute must be between 0 and 59."
    if day < now.day or (day == now.day and (hour, minute) < (now.hour, now.minute)):
        return events, "Can't schedule an event in the past."
    event = CalendarEvent(
        id=event_id,
        source="player",
        category=category,
        title=title,
        detail="",
        day=day,
        hour=hour,
        minute=minute,
        eligible=None,
        createdAt=now_iso,
    )
    updated = [*events, event]
    if len(updated) > MAX_PLAYER_CALENDAR_EVENTS:
        del updated[: len(updated) - MAX_PLAYER_CALENDAR_EVENTS]
    return updated, None


def delete_player_event(events: list[CalendarEvent], event_id: str) -> tuple[list[CalendarEvent], str | None]:
    if not any(e.id == event_id for e in events):
        return events, f"No player event found with id {event_id!r}."
    return [e for e in events if e.id != event_id], None
