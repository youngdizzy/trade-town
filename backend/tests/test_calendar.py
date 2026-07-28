"""Covers app/calendar.py — v0.7 Feature 36, the CEO Calendar & Company Schedule."""
from __future__ import annotations

from datetime import datetime, timezone

from app.calendar import (
    CALENDAR_HORIZON_DAYS,
    MAX_PLAYER_CALENDAR_EVENTS,
    compute_system_events,
    create_player_event,
    default_calendar,
    delete_player_event,
)
from app.schemas import Debate, ReasoningChallenge, ReasoningSolution, ResearchItem, TimeState, TradeDecision


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _research_item(*, confidence: float, status: str = "in_progress", title: str = "test research") -> ResearchItem:
    return ResearchItem(
        id="research-1",
        title=title,
        symbol="AAPL",
        category="stock",  # type: ignore[arg-type]
        priority="normal",
        status=status,  # type: ignore[arg-type]
        assignedAgent="scout",
        summary="in progress",
        confidence=confidence,
        createdAt="2026-01-01T00:00:00+00:00",
        updatedAt="2026-01-01T00:00:00+00:00",
    )


def _decision(decision_id: str) -> TradeDecision:
    return TradeDecision(
        id=decision_id,
        symbol="AAPL",
        outcome="trade",
        votes=[],
        researchSummary="x",
        technicalSummary="x",
        fundamentalSummary="x",
        riskSummary="x",
        supportingAgents=[],
        opposingAgents=[],
        confidence=90.0,
        finalReasoning="x",
        createdAt="2026-01-01T00:00:00+00:00",
    )


def _debate(proposal_id: str = "proposal-1") -> Debate:
    return Debate(
        id="debate-1",
        proposalId=proposal_id,
        symbol="AAPL",
        turns=[],
        finalRecommendation="buy",  # type: ignore[arg-type]
        finalSummary="x",
        createdAt="2026-01-01T00:00:00+00:00",
    )


def _base_kwargs(now: TimeState, **overrides: object) -> dict:
    kwargs: dict = {
        "now": now,
        "now_iso": _now_iso(),
        "research": [],
        "debates": [],
        "decisions": [],
        "reasoning_challenges": [],
        "agent_knowledge": {},
        "research_speed_multiplier": 1.0,
        "game_minutes_per_tick": 5,
    }
    kwargs.update(overrides)
    return kwargs


class TestDefaultCalendar:
    def test_starts_empty(self) -> None:
        calendar = default_calendar(_now_iso())
        assert calendar.system_events == []
        assert calendar.player_events == []


class TestComputeSystemEventsCadence:
    def test_morning_briefing_appears_every_day_within_horizon(self) -> None:
        now = TimeState(day=1, hour=0, minute=0)
        events = compute_system_events(**_base_kwargs(now))
        morning = [e for e in events if e.category == "morning_briefing"]
        assert len(morning) == CALENDAR_HORIZON_DAYS + 1
        assert morning[0].day == 1 and morning[0].hour == 8

    def test_morning_briefing_skips_today_once_the_hour_has_passed(self) -> None:
        now = TimeState(day=1, hour=9, minute=0)
        events = compute_system_events(**_base_kwargs(now))
        morning = [e for e in events if e.category == "morning_briefing"]
        assert all(e.day > 1 for e in morning)

    def test_weekly_events_land_on_real_multiples_of_seven(self) -> None:
        now = TimeState(day=1, hour=0, minute=0)
        events = compute_system_events(**_base_kwargs(now))
        weekly_days = {e.day for e in events if e.category == "weekly_coach_report"}
        assert weekly_days
        assert all(d % 7 == 0 for d in weekly_days)

    def test_monthly_events_land_on_real_multiples_of_thirty(self) -> None:
        now = TimeState(day=1, hour=0, minute=0)
        events = compute_system_events(**_base_kwargs(now))
        monthly_categories = {"monthly_coach_report", "monthly_reflection", "monthly_executive_review", "monthly_treasury_report"}
        monthly_events = [e for e in events if e.category in monthly_categories]
        assert monthly_events
        assert all(e.day % 30 == 0 for e in monthly_events)

    def test_events_are_sorted_chronologically(self) -> None:
        now = TimeState(day=5, hour=10, minute=0)
        events = compute_system_events(**_base_kwargs(now))
        minutes = [e.day * 1440 + e.hour * 60 + e.minute for e in events]
        assert minutes == sorted(minutes)


class TestReasoningChallengeEligibility:
    def test_ineligible_with_no_debates(self) -> None:
        now = TimeState(day=2, hour=0, minute=0)
        events = compute_system_events(**_base_kwargs(now, debates=[]))
        nearest = next(e for e in events if e.category == "reasoning_challenge_window")
        assert nearest.eligible is False

    def test_eligible_when_a_real_debate_is_unused(self) -> None:
        now = TimeState(day=2, hour=0, minute=0)
        events = compute_system_events(
            **_base_kwargs(now, debates=[_debate("proposal-1")], decisions=[_decision("decision-proposal-1")], reasoning_challenges=[])
        )
        nearest = next(e for e in events if e.category == "reasoning_challenge_window")
        assert nearest.eligible is True

    def test_ineligible_once_the_latest_debate_was_already_used(self) -> None:
        now = TimeState(day=2, hour=0, minute=0)
        challenge = ReasoningChallenge(
            id="reasoning-1",
            category="finding_missing_information",
            title="x",
            symbol="AAPL",
            decisionId="decision-proposal-1",
            contributions=[],
            solution=ReasoningSolution(whatWeKnow=[], whatWeDoNotKnow=[], assumptions=[], whyReasonable="test", confidence=80.0, whatCouldChangeOurConclusion="test"),
            reasoningLevel=1,
            simDay=1,
            createdAt="2026-01-01T00:00:00+00:00",
        )
        events = compute_system_events(
            **_base_kwargs(
                now, debates=[_debate("proposal-1")], decisions=[_decision("decision-proposal-1")], reasoning_challenges=[challenge]
            )
        )
        nearest = next(e for e in events if e.category == "reasoning_challenge_window")
        assert nearest.eligible is False

    def test_only_the_nearest_occurrence_carries_an_eligibility_flag(self) -> None:
        now = TimeState(day=2, hour=0, minute=0)
        events = compute_system_events(**_base_kwargs(now, debates=[_debate("proposal-1")], decisions=[_decision("decision-proposal-1")]))
        windows = [e for e in events if e.category == "reasoning_challenge_window"]
        assert len(windows) > 1
        assert windows[0].eligible is not None
        assert all(w.eligible is None for w in windows[1:])


class TestMentorshipEligibility:
    def test_ineligible_when_gap_is_too_small(self) -> None:
        from app.schemas import AgentKnowledgeState

        now = TimeState(day=3, hour=0, minute=0)
        knowledge = {
            "scout": AgentKnowledgeState(agentId="scout", branch="x", points=10.0, tier=0, level="novice"),  # type: ignore[arg-type]
            "atlas": AgentKnowledgeState(agentId="atlas", branch="x", points=5.0, tier=0, level="novice"),  # type: ignore[arg-type]
        }
        events = compute_system_events(**_base_kwargs(now, agent_knowledge=knowledge))
        nearest = next(e for e in events if e.category == "mentorship_window")
        assert nearest.eligible is False

    def test_eligible_when_the_real_points_gap_is_wide_enough(self) -> None:
        from app.schemas import AgentKnowledgeState

        now = TimeState(day=3, hour=0, minute=0)
        knowledge = {
            "scout": AgentKnowledgeState(agentId="scout", branch="x", points=30.0, tier=1, level="beginner"),  # type: ignore[arg-type]
            "atlas": AgentKnowledgeState(agentId="atlas", branch="x", points=1.0, tier=0, level="novice"),  # type: ignore[arg-type]
        }
        events = compute_system_events(**_base_kwargs(now, agent_knowledge=knowledge))
        nearest = next(e for e in events if e.category == "mentorship_window")
        assert nearest.eligible is True


class TestCompanyAnniversary:
    def test_appears_at_the_real_365_day_mark(self) -> None:
        now = TimeState(day=1, hour=0, minute=0)
        events = compute_system_events(**_base_kwargs(now, research_speed_multiplier=1.0))
        # Default horizon (35 days) never reaches day 365 — extend the
        # horizon-independent check by starting close to the anniversary.
        now_near = TimeState(day=360, hour=0, minute=0)
        events_near = compute_system_events(**_base_kwargs(now_near))
        anniversaries = [e for e in events_near if e.category == "company_anniversary"]
        assert len(anniversaries) == 1
        assert anniversaries[0].day == 365
        assert not events or all(e.category != "company_anniversary" for e in events)


class TestResearchDeadlineEstimate:
    def test_computes_a_real_eta_from_confidence_and_gain_rate(self) -> None:
        now = TimeState(day=1, hour=0, minute=0)
        item = _research_item(confidence=60.0)
        events = compute_system_events(**_base_kwargs(now, research=[item], research_speed_multiplier=1.0, game_minutes_per_tick=5))
        deadline = next(e for e in events if e.category == "research_deadline")
        # remaining = 40, avg_gain_per_tick = (2+6)/2 = 4 -> 10 ticks -> 50 minutes ahead of now
        now_minutes = now.day * 1440 + now.hour * 60 + now.minute
        eta_minutes = deadline.day * 1440 + deadline.hour * 60 + deadline.minute
        assert eta_minutes - now_minutes == 50

    def test_faster_speed_multiplier_produces_a_sooner_eta(self) -> None:
        now = TimeState(day=1, hour=0, minute=0)
        item = _research_item(confidence=60.0)
        slow = compute_system_events(**_base_kwargs(now, research=[item], research_speed_multiplier=1.0))
        fast = compute_system_events(**_base_kwargs(now, research=[item], research_speed_multiplier=1.5))
        slow_deadline = next(e for e in slow if e.category == "research_deadline")
        fast_deadline = next(e for e in fast if e.category == "research_deadline")
        slow_minutes = slow_deadline.day * 1440 + slow_deadline.hour * 60 + slow_deadline.minute
        fast_minutes = fast_deadline.day * 1440 + fast_deadline.hour * 60 + fast_deadline.minute
        assert fast_minutes < slow_minutes

    def test_completed_research_produces_no_deadline(self) -> None:
        now = TimeState(day=1, hour=0, minute=0)
        item = _research_item(confidence=100.0, status="completed")
        events = compute_system_events(**_base_kwargs(now, research=[item]))
        assert all(e.category != "research_deadline" for e in events)

    def test_far_out_estimate_beyond_the_horizon_is_omitted(self) -> None:
        now = TimeState(day=1, hour=0, minute=0)
        item = _research_item(confidence=1.0)
        # An unrealistically large per-tick minute step pushes the real
        # ETA formula's result far past CALENDAR_HORIZON_DAYS.
        events = compute_system_events(**_base_kwargs(now, research=[item], game_minutes_per_tick=100_000))
        assert all(e.category != "research_deadline" for e in events)


class TestCreatePlayerEvent:
    def test_creates_a_real_event(self) -> None:
        now = TimeState(day=1, hour=9, minute=0)
        events, error = create_player_event(
            [], category="town_hall", title="All-hands on risk limits", day=1, hour=15, minute=0, now=now, now_iso=_now_iso(), event_id="e1"
        )
        assert error is None
        assert len(events) == 1
        assert events[0].source == "player"
        assert events[0].title == "All-hands on risk limits"

    def test_rejects_empty_title(self) -> None:
        now = TimeState(day=1, hour=9, minute=0)
        events, error = create_player_event([], category="celebration", title="   ", day=1, hour=15, minute=0, now=now, now_iso=_now_iso(), event_id="e1")
        assert error is not None
        assert events == []

    def test_rejects_a_title_over_the_length_cap(self) -> None:
        now = TimeState(day=1, hour=9, minute=0)
        events, error = create_player_event(
            [], category="celebration", title="x" * 141, day=1, hour=15, minute=0, now=now, now_iso=_now_iso(), event_id="e1"
        )
        assert error is not None
        assert events == []

    def test_rejects_an_out_of_range_hour_or_minute(self) -> None:
        now = TimeState(day=1, hour=9, minute=0)
        _, error = create_player_event([], category="hackathon", title="x", day=1, hour=24, minute=0, now=now, now_iso=_now_iso(), event_id="e1")
        assert error is not None
        _, error2 = create_player_event([], category="hackathon", title="x", day=1, hour=10, minute=60, now=now, now_iso=_now_iso(), event_id="e1")
        assert error2 is not None

    def test_rejects_scheduling_in_the_past(self) -> None:
        now = TimeState(day=5, hour=10, minute=0)
        _, error = create_player_event([], category="hackathon", title="x", day=5, hour=9, minute=0, now=now, now_iso=_now_iso(), event_id="e1")
        assert error is not None
        _, error2 = create_player_event([], category="hackathon", title="x", day=4, hour=23, minute=0, now=now, now_iso=_now_iso(), event_id="e1")
        assert error2 is not None

    def test_accepts_the_exact_current_minute(self) -> None:
        now = TimeState(day=5, hour=10, minute=0)
        events, error = create_player_event([], category="hackathon", title="x", day=5, hour=10, minute=0, now=now, now_iso=_now_iso(), event_id="e1")
        assert error is None
        assert len(events) == 1

    def test_caps_the_event_list(self) -> None:
        now = TimeState(day=1, hour=0, minute=0)
        events: list = []
        for i in range(MAX_PLAYER_CALENDAR_EVENTS + 10):
            events, error = create_player_event(events, category="other", title=f"event {i}", day=1, hour=1, minute=0, now=now, now_iso=_now_iso(), event_id=f"e{i}")
            assert error is None
        assert len(events) == MAX_PLAYER_CALENDAR_EVENTS


class TestDeletePlayerEvent:
    def test_deletes_a_real_existing_event(self) -> None:
        now = TimeState(day=1, hour=9, minute=0)
        events, _ = create_player_event([], category="town_hall", title="x", day=1, hour=15, minute=0, now=now, now_iso=_now_iso(), event_id="e1")
        updated, error = delete_player_event(events, "e1")
        assert error is None
        assert updated == []

    def test_rejects_unknown_event_id(self) -> None:
        updated, error = delete_player_event([], "does-not-exist")
        assert error is not None
        assert updated == []
