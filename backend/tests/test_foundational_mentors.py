"""Covers app/foundational_mentors.py — v0.7 Feature 49 (Phase 3,
revised). Employees are the real students — real progress advances via
tick_employee_progress(), never via a player click. Real lesson content
only exists for the "tjr" track; the other five roadmap entries are
real, named, ordered, but intentionally empty until their own content is
authored — see the module's own docstring."""
from __future__ import annotations

from app.foundational_mentors import (
    COACH_ESCALATION_THRESHOLD,
    STUDENT_AGENT_IDS,
    _ROADMAP_ORDER,
    add_resource,
    approve_graduation,
    default_foundational_mentor_state,
    grade_ceo_lesson_quiz,
    mark_ceo_lesson_viewed,
    pause_company_training,
    repeat_mentor_company_wide,
    resume_company_training,
    skip_to_next_mentor,
    tick_employee_progress,
)
from app.schemas import DisciplineReview, FoundationalMentorState, PostDecisionReview


def _tjr_lesson_ids(state: FoundationalMentorState) -> list[str]:
    mentor = next(m for m in state.mentors if m.id == "tjr")
    return [lesson.id for lesson in sorted(mentor.lessons, key=lambda x: x.order)]


def _correct_index_for(state: FoundationalMentorState, mentor_id: str, lesson_id: str) -> int:
    for idx in range(4):
        result = grade_ceo_lesson_quiz(state, mentor_id, lesson_id, idx)  # type: ignore[arg-type]
        assert result is not None
        _, correct, correct_index, _ = result
        if correct:
            assert correct_index == idx
            return idx
    raise AssertionError(f"no correct option found for {mentor_id}/{lesson_id}")


def _high_aptitude_review(agent_id: str) -> DisciplineReview:
    """A review with a real max score, guaranteeing the auto-quiz pass
    probability clamps to MAX_QUIZ_PASS_PROBABILITY for this agent."""
    return DisciplineReview(
        id=f"review-{agent_id}",
        decisionId="decision-1",
        symbol="AAPL",
        score=100.0,
        tier="exemplary",
        factors=[],
        attendees=[agent_id],  # type: ignore[list-item]
        summary="Clean execution.",
        postDecisionReview=PostDecisionReview(),
        outcome="win",
        tradePnlPct=1.0,
        holdDurationMinutes=250,
        simDay=1,
        createdAt="2026-01-01T00:00:00+00:00",
    )


def _tick_until_all_students_pending(state: FoundationalMentorState, *, max_ticks: int = 500) -> FoundationalMentorState:
    """Runs enough real ticks, with every student given a max-aptitude
    Discipline Review (guaranteeing the highest legal pass probability),
    for the whole tjr cohort to reach pending_approval. Some quiz
    failures are still possible even at max aptitude (a real, clamped
    <100% chance) — max_ticks is generous to absorb that."""
    reviews = [_high_aptitude_review(aid) for aid in STUDENT_AGENT_IDS]
    for _ in range(max_ticks):
        state, _ = tick_employee_progress(state, discipline_reviews=reviews, sim_day=1)
        tjr_progress = [state.progress.get(aid, {}).get("tjr") for aid in STUDENT_AGENT_IDS]  # type: ignore[arg-type]
        if all(p is not None and p.graduation_status == "pending_approval" for p in tjr_progress):
            break
    return state


class TestDefaultState:
    def test_seeds_all_six_mentors_in_roadmap_order(self):
        state = default_foundational_mentor_state()
        assert [m.id for m in state.mentors] == list(_ROADMAP_ORDER)

    def test_only_tjr_has_lesson_content(self):
        state = default_foundational_mentor_state()
        by_id = {m.id: m for m in state.mentors}
        assert by_id["tjr"].status == "active"
        assert len(by_id["tjr"].lessons) == 8
        for mentor_id in _ROADMAP_ORDER:
            if mentor_id == "tjr":
                continue
            assert by_id[mentor_id].status == "planned"
            assert by_id[mentor_id].lessons == []

    def test_tjr_starts_active_company_wide(self):
        state = default_foundational_mentor_state()
        assert state.active_mentor_id == "tjr"

    def test_no_employee_progress_until_the_first_tick(self):
        state = default_foundational_mentor_state()
        assert state.progress == {}
        assert state.ceo_progress == {}

    def test_every_profile_carries_the_content_disclaimer(self):
        state = default_foundational_mentor_state()
        for mentor in state.mentors:
            assert "original TradeTown-authored teaching material" in mentor.content_note
            assert mentor.name in mentor.track_label

    def test_lesson_public_shape_hides_the_answer_key(self):
        state = default_foundational_mentor_state()
        tjr = next(m for m in state.mentors if m.id == "tjr")
        for lesson in tjr.lessons:
            assert not hasattr(lesson, "correct_index")
            assert not hasattr(lesson, "correctIndex")
            assert len(lesson.quiz_options) == 4


class TestTickEmployeeProgress:
    def test_only_real_student_agents_get_progress_records(self):
        state = default_foundational_mentor_state()
        state, _ = tick_employee_progress(state, discipline_reviews=[], sim_day=1)
        assert set(state.progress.keys()) <= set(STUDENT_AGENT_IDS)
        assert "coach" not in state.progress
        assert "sage" not in state.progress
        assert "cio" not in state.progress
        assert "quant" not in state.progress

    def test_study_progress_accrues_toward_the_current_lesson(self):
        state = default_foundational_mentor_state()
        state, _ = tick_employee_progress(state, discipline_reviews=[], sim_day=1)
        progress = state.progress["scout"]["tjr"]
        assert progress.current_lesson_study_pct > 0.0
        assert progress.completed_lesson_ids == []
        assert _tjr_lesson_ids(state)[0] in progress.viewed_lesson_ids

    def test_no_op_when_no_mentor_has_real_content_active(self):
        state = default_foundational_mentor_state()
        state = state.model_copy(update={"active_mentor_id": "al_brooks"})
        state, newly_pending = tick_employee_progress(state, discipline_reviews=[], sim_day=1)
        assert state.progress == {}
        assert newly_pending == []

    def test_high_aptitude_cohort_eventually_reaches_pending_approval(self):
        state = default_foundational_mentor_state()
        state = _tick_until_all_students_pending(state)
        for agent_id in STUDENT_AGENT_IDS:
            progress = state.progress[agent_id]["tjr"]
            assert progress.graduation_status == "pending_approval"
            assert set(progress.completed_lesson_ids) == set(_tjr_lesson_ids(state))

    def test_low_aptitude_agent_racks_up_consecutive_failures_eventually(self):
        state = default_foundational_mentor_state()
        # A review with the minimum real score, guaranteeing the lowest
        # legal pass probability (MIN_QUIZ_PASS_PROBABILITY) for scout.
        low_review = DisciplineReview(
            id="review-low",
            decisionId="decision-1",
            symbol="AAPL",
            score=0.0,
            tier="reckless",
            factors=[],
            attendees=["scout"],
            summary="Sloppy execution.",
            postDecisionReview=PostDecisionReview(mistakesMade=["Rushed in without a plan."]),
            outcome="loss",
            tradePnlPct=-1.0,
            holdDurationMinutes=5,
            simDay=1,
            createdAt="2026-01-01T00:00:00+00:00",
        )
        saw_a_failure = False
        for _ in range(400):
            state, _ = tick_employee_progress(state, discipline_reviews=[low_review], sim_day=1)
            progress = state.progress.get("scout", {}).get("tjr")
            if progress is not None and progress.consecutive_quiz_failures >= COACH_ESCALATION_THRESHOLD:
                saw_a_failure = True
                break
        assert saw_a_failure


class TestApproveGraduation:
    def test_approve_flips_status_and_records_the_sim_day(self):
        state = default_foundational_mentor_state()
        state = _tick_until_all_students_pending(state)
        state, company_graduated, error = approve_graduation(state, "scout", "tjr", sim_day=7)  # type: ignore[arg-type]
        assert error is None
        progress = state.progress["scout"]["tjr"]
        assert progress.graduation_status == "graduated"
        assert progress.graduated_sim_day == 7
        assert company_graduated is False  # only one of eight approved so far

    def test_company_graduates_once_every_student_is_approved_and_unlocks_next(self):
        state = default_foundational_mentor_state()
        state = _tick_until_all_students_pending(state)
        company_graduated = False
        for agent_id in STUDENT_AGENT_IDS:
            state, company_graduated, error = approve_graduation(state, agent_id, "tjr", sim_day=7)  # type: ignore[arg-type]
            assert error is None
        assert company_graduated is True
        tjr = next(m for m in state.mentors if m.id == "tjr")
        al_brooks = next(m for m in state.mentors if m.id == "al_brooks")
        assert tjr.status == "graduated"
        assert tjr.company_graduated_sim_day == 7
        assert al_brooks.status == "active"
        assert state.active_mentor_id == "al_brooks"

    def test_cannot_approve_without_a_pending_graduation(self):
        state = default_foundational_mentor_state()
        state, company_graduated, error = approve_graduation(state, "scout", "tjr", sim_day=1)  # type: ignore[arg-type]
        assert error is not None
        assert company_graduated is False

    def test_rejects_unknown_agent(self):
        state = default_foundational_mentor_state()
        _, _, error = approve_graduation(state, "not-a-real-agent", "tjr", sim_day=1)  # type: ignore[arg-type]
        assert error is not None


class TestCompanyWideControls:
    def test_pause_then_resume(self):
        state = default_foundational_mentor_state()
        state, error = pause_company_training(state)
        assert error is None
        assert next(m for m in state.mentors if m.id == "tjr").status == "paused"
        state, newly_pending = tick_employee_progress(state, discipline_reviews=[], sim_day=1)
        assert state.progress == {}  # paused — no study progress happens
        state, error = resume_company_training(state)
        assert error is None
        assert next(m for m in state.mentors if m.id == "tjr").status == "active"

    def test_cannot_pause_a_non_active_mentor(self):
        state = default_foundational_mentor_state()
        state, _ = pause_company_training(state)
        _, error = pause_company_training(state)
        assert error is not None

    def test_skip_preserves_progress_and_advances_roadmap(self):
        state = default_foundational_mentor_state()
        state, _ = tick_employee_progress(state, discipline_reviews=[], sim_day=1)
        state, error = skip_to_next_mentor(state)
        assert error is None
        tjr = next(m for m in state.mentors if m.id == "tjr")
        assert tjr.status == "paused"
        assert "scout" in state.progress and "tjr" in state.progress["scout"]
        assert state.active_mentor_id == "al_brooks"

    def test_skip_on_last_roadmap_entry_errors(self):
        state = default_foundational_mentor_state()
        new_mentors = [m.model_copy(update={"status": "active"}) if m.id == "mike_bellafiore" else (m.model_copy(update={"status": "paused"}) if m.id == "tjr" else m) for m in state.mentors]
        state = state.model_copy(update={"mentors": new_mentors, "active_mentor_id": "mike_bellafiore"})
        _, error = skip_to_next_mentor(state)
        assert error == "This is the last track on the roadmap — nothing to skip to."

    def test_repeat_resets_every_students_progress(self):
        state = default_foundational_mentor_state()
        state = _tick_until_all_students_pending(state)
        for agent_id in STUDENT_AGENT_IDS:
            state, _, error = approve_graduation(state, agent_id, "tjr", sim_day=5)  # type: ignore[arg-type]
            assert error is None
        state, error = repeat_mentor_company_wide(state, "tjr")  # type: ignore[arg-type]
        assert error is None
        assert next(m for m in state.mentors if m.id == "tjr").status == "active"
        for agent_id in STUDENT_AGENT_IDS:
            progress = state.progress[agent_id]["tjr"]
            assert progress.completed_lesson_ids == []
            assert progress.graduation_status == "in_progress"

    def test_repeat_only_valid_on_graduated_mentor(self):
        state = default_foundational_mentor_state()
        _, error = repeat_mentor_company_wide(state, "tjr")  # type: ignore[arg-type]
        assert error is not None


class TestCeoPersonalLearning:
    def test_ceo_progress_is_entirely_separate_from_employee_progress(self):
        state = default_foundational_mentor_state()
        lesson_id = _tjr_lesson_ids(state)[0]
        state = mark_ceo_lesson_viewed(state, "tjr", lesson_id)  # type: ignore[arg-type]
        assert lesson_id in state.ceo_progress["tjr"].viewed_lesson_ids
        assert state.progress == {}  # never touches real employee records

    def test_ceo_quiz_grades_against_the_real_hidden_answer(self):
        state = default_foundational_mentor_state()
        lesson_id = _tjr_lesson_ids(state)[0]
        idx = _correct_index_for(state, "tjr", lesson_id)
        result = grade_ceo_lesson_quiz(state, "tjr", lesson_id, idx)  # type: ignore[arg-type]
        assert result is not None
        new_state, correct, _, _ = result
        assert correct is True
        assert lesson_id in new_state.ceo_progress["tjr"].completed_lesson_ids

    def test_unknown_mentor_or_lesson_returns_none(self):
        state = default_foundational_mentor_state()
        assert grade_ceo_lesson_quiz(state, "tjr", "not-a-real-lesson", 0) is None  # type: ignore[arg-type]
        assert grade_ceo_lesson_quiz(state, "al_brooks", "tjr-psychology", 0) is None  # type: ignore[arg-type]


class TestAddResource:
    def test_adds_a_bookmark(self):
        state = default_foundational_mentor_state()
        state, error = add_resource(state, "tjr", title="Real Trade Reviews", url="https://example.com", resource_type="video")  # type: ignore[arg-type]
        assert error is None
        tjr = next(m for m in state.mentors if m.id == "tjr")
        assert len(tjr.resources) == 1
        assert tjr.resources[0].title == "Real Trade Reviews"

    def test_rejects_empty_title(self):
        state = default_foundational_mentor_state()
        _, error = add_resource(state, "tjr", title="   ", url=None, resource_type="note")  # type: ignore[arg-type]
        assert error is not None

    def test_rejects_unknown_mentor(self):
        state = default_foundational_mentor_state()
        _, error = add_resource(state, "nonexistent", title="X", url=None, resource_type="note")  # type: ignore[arg-type]
        assert error is not None
