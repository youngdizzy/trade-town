"""Covers app/education.py — v0.6.2 Phase 9. The curriculum is static
content (not fabricated game data), but progress tracking and grading
must still be real and correct."""
from __future__ import annotations

from app.education import all_lessons, default_education_progress, grade_quiz, mark_viewed
from app.schemas import EducationProgress


def test_all_lessons_covers_the_eighteen_topic_curriculum_in_order():
    # v0.7 Feature 49 (Phase 2) extended the original 10-lesson
    # curriculum with an 8-lesson Liquidity/Market Structure module.
    lessons = all_lessons()
    assert len(lessons) == 18
    orders = [lesson.order for lesson in lessons]
    assert orders == sorted(orders)
    assert orders == list(range(1, 19))


def test_liquidity_module_lessons_are_present_and_unique():
    liquidity_ids = {
        "liquidity_basics",
        "swing_structure",
        "equal_highs_lows",
        "liquidity_sweeps",
        "inducement",
        "structure_shifts",
        "premium_discount",
        "order_flow_intro",
    }
    lesson_ids = {lesson.id for lesson in all_lessons()}
    assert liquidity_ids <= lesson_ids
    assert len(lesson_ids) == 18  # no duplicate ids across all 18


def test_lesson_public_shape_never_leaks_the_quiz_answer():
    for lesson in all_lessons():
        assert not hasattr(lesson, "correct_index")
        assert not hasattr(lesson, "correctIndex")
        assert len(lesson.quiz_options) == 4


def test_mark_viewed_adds_the_lesson_once():
    progress = default_education_progress()
    lesson_id = all_lessons()[0].id
    progress = mark_viewed(progress, lesson_id)
    assert progress.viewed_lesson_ids == [lesson_id]
    progress_again = mark_viewed(progress, lesson_id)
    assert progress_again.viewed_lesson_ids == [lesson_id]  # not duplicated


def test_mark_viewed_ignores_unknown_lesson_ids():
    progress = default_education_progress()
    result = mark_viewed(progress, "not-a-real-lesson")
    assert result == progress


def test_grade_quiz_returns_none_for_unknown_lesson():
    progress = default_education_progress()
    assert grade_quiz(progress, "not-a-real-lesson", 0) is None


def test_grade_quiz_correct_answer_completes_the_lesson_and_updates_counters():
    progress = default_education_progress()
    lesson = all_lessons()[0]
    # Find the real correct index by trying each option — grade_quiz is
    # the only way to learn it since the public lesson shape hides it.
    correct_index = None
    for i in range(len(lesson.quiz_options)):
        result = grade_quiz(progress, lesson.id, i)
        assert result is not None
        _, correct, real_correct_index, _ = result
        correct_index = real_correct_index
        if correct:
            break
    assert correct_index is not None

    new_progress, correct, _, correct_option = grade_quiz(progress, lesson.id, correct_index)
    assert correct is True
    assert lesson.id in new_progress.completed_lesson_ids
    assert new_progress.quiz_attempts == 1
    assert new_progress.correct_quiz_attempts == 1
    assert correct_option in lesson.quiz_options


def test_grade_quiz_wrong_answer_does_not_complete_the_lesson():
    progress = default_education_progress()
    lesson = all_lessons()[0]
    # Try every option; at least one must be wrong for a 4-option quiz.
    wrong_index = None
    for i in range(len(lesson.quiz_options)):
        result = grade_quiz(progress, lesson.id, i)
        assert result is not None
        _, correct, _, _ = result
        if not correct:
            wrong_index = i
            break
    assert wrong_index is not None

    new_progress, correct, _, _ = grade_quiz(progress, lesson.id, wrong_index)
    assert correct is False
    assert lesson.id not in new_progress.completed_lesson_ids
    assert new_progress.quiz_attempts == 1
    assert new_progress.correct_quiz_attempts == 0


def test_grade_quiz_a_second_correct_attempt_does_not_duplicate_the_completed_id():
    progress = default_education_progress()
    lesson = all_lessons()[0]
    correct_index = next(i for i in range(len(lesson.quiz_options)) if grade_quiz(progress, lesson.id, i)[1])  # type: ignore[index]

    progress, _, _, _ = grade_quiz(progress, lesson.id, correct_index)  # type: ignore[misc]
    progress, _, _, _ = grade_quiz(progress, lesson.id, correct_index)  # type: ignore[misc]
    assert progress.completed_lesson_ids.count(lesson.id) == 1
    assert progress.quiz_attempts == 2


def test_default_education_progress_starts_empty():
    progress = default_education_progress()
    assert progress == EducationProgress()
    assert progress.viewed_lesson_ids == []
    assert progress.completed_lesson_ids == []
