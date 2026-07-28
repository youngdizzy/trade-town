"""Covers app/nexus.py's Work Mode gating — v0.7 Feature 37, the Work
Mode System. Trading/risk systems are deliberately never touched by
work_mode anywhere in nexus.py, so there is nothing to test for them
here — their behavior under both modes is identical by construction."""
from __future__ import annotations

import random

from app.agents import all_agent_ids
from app.nexus import _effective_block, _maybe_call_meeting, _rest_block, default_agents, tick
from app.schedule import block_for_hour
from app.schemas import AgentOverride, MeetingState, TimeState
from app.state import default_state


def _tick_with_work_mode(work_mode: str, *, hour: int = 10, minute: int = 0):
    state = default_state()
    state = state.model_copy(update={"settings": state.settings.model_copy(update={"work_mode": work_mode})})
    new_time = TimeState(day=state.time.day, hour=hour, minute=minute)
    return state, tick(state, new_time, 5)


class TestEffectiveBlock:
    def test_work_mode_matches_the_real_unmodified_schedule(self) -> None:
        now = TimeState(day=1, hour=10, minute=0)
        assert _effective_block("scout", now, False) == block_for_hour("scout", 10)

    def test_rest_mode_never_returns_a_working_hour_block(self) -> None:
        # Scout's real working blocks (6-20) never include "break-room";
        # every real off-hour block (20-24, 0-6) does.
        for hour in range(24):
            for minute in (0, 15, 30, 45):
                now = TimeState(day=1, hour=hour, minute=minute)
                block = _effective_block("scout", now, True)
                assert block.location == "break-room"


class TestRestBlockCycling:
    def test_cycles_through_all_three_real_off_hour_blocks(self) -> None:
        seen_tasks = {_rest_block("scout", TimeState(day=1, hour=h, minute=0)).task for h in range(24)}
        real_off_hour_tasks = {block.task for block in [block_for_hour("scout", h) for h in (20, 22, 0)]}
        assert seen_tasks == real_off_hour_tasks

    def test_is_a_pure_function_of_the_clock_not_random(self) -> None:
        now = TimeState(day=5, hour=13, minute=20)
        first = _rest_block("scout", now)
        second = _rest_block("scout", now)
        assert first == second

    def test_repeats_every_ten_hours(self) -> None:
        early = _rest_block("scout", TimeState(day=1, hour=3, minute=0))
        ten_hours_later = _rest_block("scout", TimeState(day=1, hour=13, minute=0))  # 3 + 10 = 13, same 600-minute cycle position
        assert early == ten_hours_later


class TestTickResting:
    def test_every_agent_routes_to_break_room_at_a_normal_working_hour(self) -> None:
        _, resting_state = _tick_with_work_mode("rest", hour=10)
        assert all(a.location == "break-room" for a in resting_state.agents.values())

    def test_work_mode_leaves_at_least_one_agent_at_a_real_workstation(self) -> None:
        _, working_state = _tick_with_work_mode("work", hour=10)
        assert any(a.location != "break-room" for a in working_state.agents.values())

    def test_research_confidence_does_not_advance_while_resting(self) -> None:
        before, resting_state = _tick_with_work_mode("rest")
        before_confidences = [r.confidence for r in before.research]
        after_confidences = [r.confidence for r in resting_state.research]
        assert before_confidences == after_confidences

    def test_research_confidence_can_advance_while_working(self) -> None:
        before, working_state = _tick_with_work_mode("work")
        before_confidences = [r.confidence for r in before.research]
        after_confidences = [r.confidence for r in working_state.research]
        assert before_confidences != after_confidences

    def test_academy_project_does_not_advance_while_resting(self) -> None:
        before, resting_state = _tick_with_work_mode("rest")
        assert resting_state.academy_projects == before.academy_projects


class TestMaybeCallMeetingResting:
    def test_no_new_meeting_starts_while_resting(self, monkeypatch) -> None:
        monkeypatch.setattr(random, "random", lambda: 0.0)  # would normally clear MEETING_CHANCE_PER_TICK's gate
        agents = default_agents()
        meeting = MeetingState()
        _, updated_meeting = _maybe_call_meeting(agents, meeting, [], TimeState(day=1, hour=10, minute=0), [], [], [], [], resting=True)
        assert updated_meeting.active is False

    def test_a_new_meeting_can_start_while_working(self, monkeypatch) -> None:
        monkeypatch.setattr(random, "random", lambda: 0.0)
        agents = default_agents()
        meeting = MeetingState()
        _, updated_meeting = _maybe_call_meeting(agents, meeting, [], TimeState(day=1, hour=10, minute=0), [], [], [], [], resting=False)
        assert updated_meeting.active is True

    def test_an_already_active_meeting_still_finishes_naturally_while_resting(self) -> None:
        """`resting` only ever gates whether a NEW meeting is allowed to
        start (the `else` branch below) — the `meeting.active` branch
        above it is reached unconditionally either way, so an in-progress
        meeting is completely unaffected by Rest Mode; it wraps up only
        once its own real override actually expires (via `_tick_agent`,
        not this function)."""
        agents = default_agents()
        participants = list(all_agent_ids())[:3]
        for aid in participants:
            agents[aid] = agents[aid].model_copy(update={"override": AgentOverride(location="meeting-room", reason="meeting", remainingMinutes=5)})
        meeting = MeetingState(active=True, participants=participants, discussion=[])
        updated_agents, updated_meeting = _maybe_call_meeting(agents, meeting, [], TimeState(day=1, hour=10, minute=5), [], [], [], [], resting=True)
        assert updated_meeting.active is True
        assert updated_agents[participants[0]].override is not None
