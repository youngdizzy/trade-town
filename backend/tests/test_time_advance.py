"""Covers GameState.advance_time() — v0.7 Feature 34's CEO time controls
(End Workday/Week/Month, and a bounded custom fast-forward). Each test
builds its own GameState() rather than importing the process-wide
app.state.game_state singleton, so runs stay isolated from each other."""
from __future__ import annotations

import asyncio

from app.nexus import EVENING_REVIEW_HOUR, MONTHLY_INTERVAL_DAYS, WEEKLY_INTERVAL_DAYS
from app.state import MAX_FAST_FORWARD_HOURS, GameState


def test_workday_end_lands_exactly_on_the_evening_review_hour() -> None:
    state = GameState()
    saved, error = asyncio.run(state.advance_time("workday_end", None))
    assert error is None
    assert saved.time.hour == EVENING_REVIEW_HOUR
    assert saved.time.minute == 0


def test_workday_end_always_advances_at_least_one_step_even_when_already_at_target() -> None:
    state = GameState()
    # Land exactly on the evening review hour first...
    first, error = asyncio.run(state.advance_time("workday_end", None))
    assert error is None
    assert first.time.hour == EVENING_REVIEW_HOUR and first.time.minute == 0
    first_day = first.time.day

    # ...then calling it again right at that exact minute must jump to the
    # *next* occurrence, not silently no-op.
    second, error = asyncio.run(state.advance_time("workday_end", None))
    assert error is None
    assert second.time.hour == EVENING_REVIEW_HOUR and second.time.minute == 0
    assert second.time.day == first_day + 1


def test_week_end_lands_on_a_real_multiple_of_the_weekly_interval() -> None:
    state = GameState()
    saved, error = asyncio.run(state.advance_time("week_end", None))
    assert error is None
    assert saved.time.hour == EVENING_REVIEW_HOUR
    assert saved.time.day % WEEKLY_INTERVAL_DAYS == 0


def test_month_end_lands_on_a_real_multiple_of_the_monthly_interval() -> None:
    state = GameState()
    saved, error = asyncio.run(state.advance_time("month_end", None))
    assert error is None
    assert saved.time.hour == EVENING_REVIEW_HOUR
    assert saved.time.day % MONTHLY_INTERVAL_DAYS == 0


def test_hours_target_advances_the_clock_by_the_real_requested_amount() -> None:
    state = GameState()
    start = state.data.time
    saved, error = asyncio.run(state.advance_time("hours", 3))
    assert error is None
    start_total = start.day * 24 * 60 + start.hour * 60 + start.minute
    end_total = saved.time.day * 24 * 60 + saved.time.hour * 60 + saved.time.minute
    assert end_total - start_total == 3 * 60


def test_hours_target_rejects_zero_or_negative() -> None:
    state = GameState()
    before = state.data
    saved, error = asyncio.run(state.advance_time("hours", 0))
    assert error is not None
    assert saved == before

    saved, error = asyncio.run(state.advance_time("hours", -5))
    assert error is not None
    assert saved == before


def test_hours_target_rejects_more_than_the_real_cap() -> None:
    state = GameState()
    before = state.data
    saved, error = asyncio.run(state.advance_time("hours", MAX_FAST_FORWARD_HOURS + 1))
    assert error is not None
    assert saved == before


def test_hours_target_accepts_exactly_the_cap() -> None:
    state = GameState()
    saved, error = asyncio.run(state.advance_time("hours", MAX_FAST_FORWARD_HOURS))
    assert error is None
