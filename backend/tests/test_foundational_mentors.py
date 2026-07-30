"""Covers app/foundational_mentors.py — v0.7 Feature 49 (Phase 3). Real
lesson content only exists for the "tjr" track; the other five roadmap
entries are real, named, ordered, but intentionally empty until their
own content is authored — see the module's own docstring."""
from __future__ import annotations

from app.foundational_mentors import (
    _ROADMAP_ORDER,
    add_resource,
    default_foundational_mentor_state,
    grade_lesson_quiz,
    mark_lesson_viewed,
    pause_mentor,
    repeat_mentor,
    resume_mentor,
    skip_mentor,
)
from app.schemas import FoundationalMentorId, FoundationalMentorState


def _tjr_lesson_ids(state: FoundationalMentorState) -> list[str]:
    mentor = next(m for m in state.mentors if m.id == "tjr")
    return [lesson.id for lesson in sorted(mentor.lessons, key=lambda x: x.order)]


def _correct_index_for(state: FoundationalMentorState, mentor_id: FoundationalMentorId, lesson_id: str) -> int:
    for idx in range(4):
        result = grade_lesson_quiz(state, mentor_id, lesson_id, idx, sim_day=1)
        assert result is not None
        _, correct, correct_index, _ = result
        if correct:
            assert correct_index == idx
            return idx
    raise AssertionError(f"no correct option found for {mentor_id}/{lesson_id}")


class TestDefaultState:
    def test_seeds_all_six_mentors_in_roadmap_order(self):
        state = default_foundational_mentor_state()
        assert [m.id for m in state.mentors] == list(_ROADMAP_ORDER)

    def test_only_tjr_has_lesson_content(self):
        state = default_foundational_mentor_state()
        by_id = {m.id: m for m in state.mentors}
        assert by_id["tjr"].status == "active"
        assert len(by_id["tjr"].lessons) == 6
        for mentor_id in _ROADMAP_ORDER:
            if mentor_id == "tjr":
                continue
            assert by_id[mentor_id].status == "planned"
            assert by_id[mentor_id].lessons == []

    def test_tjr_starts_active_by_default(self):
        state = default_foundational_mentor_state()
        assert state.active_mentor_id == "tjr"

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


class TestMarkLessonViewed:
    def test_adds_lesson_to_viewed_once(self):
        state = default_foundational_mentor_state()
        lesson_id = _tjr_lesson_ids(state)[0]
        state = mark_lesson_viewed(state, "tjr", lesson_id)
        state = mark_lesson_viewed(state, "tjr", lesson_id)
        progress = state.progress["tjr"]
        assert progress.viewed_lesson_ids.count(lesson_id) == 1

    def test_unknown_lesson_is_a_no_op(self):
        state = default_foundational_mentor_state()
        new_state = mark_lesson_viewed(state, "tjr", "not-a-real-lesson")
        assert new_state == state


class TestGradeLessonQuiz:
    def test_correct_answer_marks_lesson_completed(self):
        state = default_foundational_mentor_state()
        lesson_id = _tjr_lesson_ids(state)[0]
        idx = _correct_index_for(state, "tjr", lesson_id)
        result = grade_lesson_quiz(state, "tjr", lesson_id, idx, sim_day=1)
        assert result is not None
        new_state, correct, _, _ = result
        assert correct is True
        assert lesson_id in new_state.progress["tjr"].completed_lesson_ids

    def test_wrong_answer_does_not_complete_lesson(self):
        state = default_foundational_mentor_state()
        lesson_id = _tjr_lesson_ids(state)[0]
        correct_idx = _correct_index_for(state, "tjr", lesson_id)
        wrong_idx = (correct_idx + 1) % 4
        result = grade_lesson_quiz(state, "tjr", lesson_id, wrong_idx, sim_day=1)
        assert result is not None
        new_state, correct, _, _ = result
        assert correct is False
        assert lesson_id not in new_state.progress["tjr"].completed_lesson_ids

    def test_completing_all_lessons_graduates_and_unlocks_al_brooks(self):
        state = default_foundational_mentor_state()
        for lesson_id in _tjr_lesson_ids(state):
            idx = _correct_index_for(state, "tjr", lesson_id)
            result = grade_lesson_quiz(state, "tjr", lesson_id, idx, sim_day=5)
            assert result is not None
            state = result[0]
        tjr = next(m for m in state.mentors if m.id == "tjr")
        al_brooks = next(m for m in state.mentors if m.id == "al_brooks")
        assert tjr.status == "graduated"
        assert state.progress["tjr"].graduated_sim_day == 5
        assert al_brooks.status == "active"
        assert state.active_mentor_id == "al_brooks"

    def test_unknown_mentor_or_lesson_returns_none(self):
        state = default_foundational_mentor_state()
        assert grade_lesson_quiz(state, "tjr", "not-a-real-lesson", 0, sim_day=1) is None
        assert grade_lesson_quiz(state, "al_brooks", "tjr-psychology", 0, sim_day=1) is None

    def test_completing_a_lesson_twice_does_not_duplicate_completion(self):
        state = default_foundational_mentor_state()
        lesson_id = _tjr_lesson_ids(state)[0]
        idx = _correct_index_for(state, "tjr", lesson_id)
        result = grade_lesson_quiz(state, "tjr", lesson_id, idx, sim_day=1)
        assert result is not None
        state = result[0]
        result2 = grade_lesson_quiz(state, "tjr", lesson_id, idx, sim_day=2)
        assert result2 is not None
        state = result2[0]
        assert state.progress["tjr"].completed_lesson_ids.count(lesson_id) == 1


class TestCeoControls:
    def test_pause_then_resume_active_mentor(self):
        state = default_foundational_mentor_state()
        state, error = pause_mentor(state, "tjr")
        assert error is None
        assert next(m for m in state.mentors if m.id == "tjr").status == "paused"
        state, error = resume_mentor(state, "tjr")
        assert error is None
        assert next(m for m in state.mentors if m.id == "tjr").status == "active"

    def test_cannot_pause_a_non_active_mentor(self):
        state = default_foundational_mentor_state()
        _, error = pause_mentor(state, "al_brooks")
        assert error is not None

    def test_skip_preserves_progress_and_advances_roadmap(self):
        state = default_foundational_mentor_state()
        lesson_id = _tjr_lesson_ids(state)[0]
        idx = _correct_index_for(state, "tjr", lesson_id)
        result = grade_lesson_quiz(state, "tjr", lesson_id, idx, sim_day=1)
        assert result is not None
        state = result[0]
        state, error = skip_mentor(state, "tjr")
        assert error is None
        tjr = next(m for m in state.mentors if m.id == "tjr")
        assert tjr.status == "paused"
        assert lesson_id in state.progress["tjr"].completed_lesson_ids
        assert state.active_mentor_id == "al_brooks"

    def test_skip_on_last_roadmap_entry_errors(self):
        state = default_foundational_mentor_state()
        # mike_bellafiore starts "planned" (locked behind the roadmap) —
        # force it active here to isolate the "nothing to skip to" path
        # from the separate "must be active/paused" rejection.
        new_mentors = [m.model_copy(update={"status": "active"}) if m.id == "mike_bellafiore" else m for m in state.mentors]
        state = state.model_copy(update={"mentors": new_mentors})
        state, error = skip_mentor(state, "mike_bellafiore")
        assert error == "This is the last track on the roadmap — nothing to skip to."

    def test_repeat_resets_progress(self):
        state = default_foundational_mentor_state()
        for lesson_id in _tjr_lesson_ids(state):
            idx = _correct_index_for(state, "tjr", lesson_id)
            result = grade_lesson_quiz(state, "tjr", lesson_id, idx, sim_day=1)
            assert result is not None
            state = result[0]
        assert next(m for m in state.mentors if m.id == "tjr").status == "graduated"
        state, error = repeat_mentor(state, "tjr")
        assert error is None
        assert next(m for m in state.mentors if m.id == "tjr").status == "active"
        assert state.progress["tjr"].completed_lesson_ids == []

    def test_repeat_only_valid_on_graduated_mentor(self):
        state = default_foundational_mentor_state()
        _, error = repeat_mentor(state, "tjr")
        assert error is not None


class TestAddResource:
    def test_adds_a_bookmark(self):
        state = default_foundational_mentor_state()
        state, error = add_resource(state, "tjr", title="Real Trade Reviews", url="https://example.com", resource_type="video")
        assert error is None
        tjr = next(m for m in state.mentors if m.id == "tjr")
        assert len(tjr.resources) == 1
        assert tjr.resources[0].title == "Real Trade Reviews"

    def test_rejects_empty_title(self):
        state = default_foundational_mentor_state()
        _, error = add_resource(state, "tjr", title="   ", url=None, resource_type="note")
        assert error is not None

    def test_rejects_unknown_mentor(self):
        state = default_foundational_mentor_state()
        _, error = add_resource(state, "nonexistent", title="X", url=None, resource_type="note")  # type: ignore[arg-type]
        assert error is not None
