"""Covers app/black_box.py — the Advanced Quantitative Research Division.
Every field must trace back to a real signal already computed elsewhere
(the project's own progress/obstacles/confidence, or the Devil's Advocate's
existing eligible pool) — never invented evidence.
"""
from __future__ import annotations

from app.black_box import (
    STARTING_BUDGET,
    _CATEGORY_CATALOG,
    default_black_box_state,
    generate_project_challenge,
    mark_breakthrough_viewed,
    tick_black_box_daily,
)
from app.devils_advocate import ELIGIBLE_DEVILS_ADVOCATES
from app.founders import generate_breakthrough_review


def test_default_state_has_no_active_project() -> None:
    state = default_black_box_state()
    assert state.active is None
    assert state.archive == []
    assert state.reviews == []


def test_first_tick_starts_a_new_project() -> None:
    state = default_black_box_state()
    updated = tick_black_box_daily(state, sim_day=1, innovation_state={})
    assert updated.active is not None
    assert updated.active.status == "active"
    assert updated.active.budget == STARTING_BUDGET
    assert updated.active.team[0].agent_id == "quant"
    assert updated.active.team[0].role == "Project Leader"
    # No "AI Research Scientist" seat — see module docstring.
    assert all(m.role != "AI Research Scientist" for m in updated.active.team)


def test_devils_advocate_never_collides_with_the_fixed_team() -> None:
    state = default_black_box_state()
    updated = tick_black_box_daily(state, sim_day=1, innovation_state={})
    assert updated.active is not None
    team_ids = {m.agent_id for m in updated.active.team}
    assert updated.active.devils_advocate not in team_ids
    assert updated.active.devils_advocate in ELIGIBLE_DEVILS_ADVOCATES


def test_paused_project_makes_no_progress() -> None:
    state = default_black_box_state()
    state = tick_black_box_daily(state, sim_day=1, innovation_state={})
    assert state.active is not None
    paused = state.model_copy(update={"active": state.active.model_copy(update={"status": "paused"})})
    ticked = tick_black_box_daily(paused, sim_day=2, innovation_state={})
    assert ticked.active is not None
    assert ticked.active.progress == paused.active.progress  # type: ignore[union-attr]


def test_progress_advances_and_eventually_reaches_review() -> None:
    state = default_black_box_state()
    for day in range(1, 60):
        state = tick_black_box_daily(state, sim_day=day, innovation_state={})
        if state.active is not None and state.active.status == "under_review":
            break
    assert state.active is not None
    assert state.active.status == "under_review"
    assert state.active.progress >= 100.0


def test_unfunded_project_stalls_and_logs_a_real_obstacle() -> None:
    state = default_black_box_state()
    state = tick_black_box_daily(state, sim_day=1, innovation_state={})
    assert state.active is not None
    broke = state.model_copy(update={"active": state.active.model_copy(update={"budget": 0.0})})
    ticked = tick_black_box_daily(broke, sim_day=2, innovation_state={})
    assert ticked.active is not None
    assert "Insufficient funding is slowing this project down." in ticked.active.obstacles


def test_generate_project_challenge_reuses_real_project_fields() -> None:
    state = default_black_box_state()
    state = tick_black_box_daily(state, sim_day=1, innovation_state={})
    assert state.active is not None
    project = state.active.model_copy(update={"progress": 100.0, "confidence_level": 90.0, "obstacles": [], "research_notes": ["Backtest replicated across three independent samples."]})
    challenge = generate_project_challenge(project, existing_count=0)
    assert challenge.assigned_agent == project.devils_advocate
    assert challenge.severity == "none_found"
    assert challenge.hidden_risks == []


def test_generate_project_challenge_flags_real_weaknesses() -> None:
    state = default_black_box_state()
    state = tick_black_box_daily(state, sim_day=1, innovation_state={})
    assert state.active is not None
    project = state.active.model_copy(update={"progress": 100.0, "confidence_level": 20.0, "obstacles": ["Backtest data for this period is noisier than expected."]})
    challenge = generate_project_challenge(project, existing_count=0)
    assert challenge.severity == "major"
    assert challenge.hidden_risks == project.obstacles


def test_breakthrough_review_approves_a_clean_project() -> None:
    state = default_black_box_state()
    state = tick_black_box_daily(state, sim_day=1, innovation_state={})
    assert state.active is not None
    project = state.active.model_copy(update={"progress": 100.0, "confidence_level": 90.0, "obstacles": []})
    challenge = generate_project_challenge(project, existing_count=0)
    review = generate_breakthrough_review(project, challenge=challenge, sim_day=30, review_id="rev-1", created_at="2024-01-01T00:00:00+00:00")
    assert review.verdict == "approved"
    assert review.project_id == project.id


def test_breakthrough_review_rejects_a_weak_project() -> None:
    state = default_black_box_state()
    state = tick_black_box_daily(state, sim_day=1, innovation_state={})
    assert state.active is not None
    project = state.active.model_copy(update={"progress": 100.0, "confidence_level": 10.0, "obstacles": ["a", "b", "c"]})
    challenge = generate_project_challenge(project, existing_count=0)
    review = generate_breakthrough_review(project, challenge=challenge, sim_day=30, review_id="rev-2", created_at="2024-01-01T00:00:00+00:00")
    assert review.verdict == "rejected"


def test_category_catalog_covers_every_brief_named_example() -> None:
    categories = {c for c, _title, _objective in _CATEGORY_CATALOG}
    assert categories == {
        "new_trading_framework",
        "portfolio_allocation",
        "statistical_edge",
        "ai_communication",
        "risk_model",
        "decision_framework",
        "journaling_improvement",
        "automation_improvement",
        "market_regime_detection",
        "portfolio_optimization",
        "academy_improvement",
    }


def test_mark_breakthrough_viewed_is_idempotent() -> None:
    ids = mark_breakthrough_viewed([], "rev-1")
    assert ids == ["rev-1"]
    assert mark_breakthrough_viewed(ids, "rev-1") == ["rev-1"]
