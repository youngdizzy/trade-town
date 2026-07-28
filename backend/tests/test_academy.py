"""Covers app/academy.py — v0.7 Feature 25's per-agent Knowledge Points/
Tiers, company-wide Academy level, and the mentorship substitute. Every
point awarded here traces back to real completed work in the caller
(nexus.py); this module only owns the arithmetic and thresholds.
"""
from __future__ import annotations

from app.academy import (
    MENTORSHIP_BONUS_POINTS,
    MENTORSHIP_GAP_THRESHOLD,
    TIER_THRESHOLDS,
    award_points,
    compute_academy_state,
    default_agent_knowledge,
    is_mentor_level,
    maybe_run_mentorship,
)
from app.schemas import AGENT_IDS


class TestDefaultAgentKnowledge:
    def test_every_agent_starts_at_zero_points_and_tier(self) -> None:
        knowledge = default_agent_knowledge()
        assert set(knowledge.keys()) == set(AGENT_IDS)
        for state in knowledge.values():
            assert state.points == 0.0
            assert state.tier == 0

    def test_every_agent_starts_at_novice_level(self) -> None:
        knowledge = default_agent_knowledge()
        for state in knowledge.values():
            assert state.level == "novice"

    def test_every_agent_has_a_non_empty_branch(self) -> None:
        knowledge = default_agent_knowledge()
        for state in knowledge.values():
            assert state.branch


class TestAwardPoints:
    def test_awards_real_points_to_the_named_agent_only(self) -> None:
        knowledge = default_agent_knowledge()
        updated, tier_up = award_points(knowledge, "echo", 2.0)
        assert updated["echo"].points == 2.0
        assert updated["scout"].points == 0.0
        assert tier_up is None

    def test_crossing_a_threshold_returns_the_tier_up_state(self) -> None:
        knowledge = default_agent_knowledge()
        updated, tier_up = award_points(knowledge, "echo", TIER_THRESHOLDS[0])
        assert tier_up is not None
        assert tier_up.agent_id == "echo"
        assert tier_up.tier == 1

    def test_staying_below_threshold_does_not_report_a_tier_up(self) -> None:
        knowledge = default_agent_knowledge()
        _updated, tier_up = award_points(knowledge, "echo", TIER_THRESHOLDS[0] - 1.0)
        assert tier_up is None

    def test_repeated_awards_accumulate_and_only_tier_up_once_per_crossing(self) -> None:
        knowledge = default_agent_knowledge()
        knowledge, first = award_points(knowledge, "echo", TIER_THRESHOLDS[0])
        assert first is not None
        knowledge, second = award_points(knowledge, "echo", 0.5)
        assert second is None
        assert knowledge["echo"].points == TIER_THRESHOLDS[0] + 0.5

    def test_unknown_agent_id_is_a_no_op(self) -> None:
        knowledge = default_agent_knowledge()
        updated, tier_up = award_points(knowledge, "not-a-real-agent", 5.0)  # type: ignore[arg-type]
        assert updated == knowledge
        assert tier_up is None


class TestMaybeRunMentorship:
    def test_no_pairing_when_every_agent_is_still_at_zero(self) -> None:
        knowledge = default_agent_knowledge()
        updated, pairing = maybe_run_mentorship(knowledge)
        assert pairing is None
        assert updated == knowledge

    def test_pairing_fires_once_the_gap_crosses_threshold(self) -> None:
        knowledge = default_agent_knowledge()
        knowledge, _ = award_points(knowledge, "echo", MENTORSHIP_GAP_THRESHOLD)
        _updated, pairing = maybe_run_mentorship(knowledge)
        assert pairing is not None
        assert pairing[0] == "echo"

    def test_pairing_awards_the_mentee_a_real_bonus(self) -> None:
        knowledge = default_agent_knowledge()
        knowledge, _ = award_points(knowledge, "echo", MENTORSHIP_GAP_THRESHOLD)
        updated, pairing = maybe_run_mentorship(knowledge)
        assert pairing is not None
        _mentor_id, mentee_id = pairing
        assert updated[mentee_id].points == MENTORSHIP_BONUS_POINTS

    def test_no_pairing_just_below_the_gap_threshold(self) -> None:
        knowledge = default_agent_knowledge()
        knowledge, _ = award_points(knowledge, "echo", MENTORSHIP_GAP_THRESHOLD - 1.0)
        _updated, pairing = maybe_run_mentorship(knowledge)
        assert pairing is None


class TestComputeAcademyState:
    def test_fresh_knowledge_reads_as_level_one(self) -> None:
        state = compute_academy_state(default_agent_knowledge(), 0)
        assert state.level == 1
        assert state.level_label == "Training Room"
        assert state.total_points == 0.0
        assert state.completed_project_count == 0

    def test_total_points_sums_across_every_agent(self) -> None:
        knowledge = default_agent_knowledge()
        knowledge, _ = award_points(knowledge, "echo", 5.0)
        knowledge, _ = award_points(knowledge, "scout", 3.0)
        state = compute_academy_state(knowledge, 0)
        assert state.total_points == 8.0

    def test_completed_projects_also_raise_the_level(self) -> None:
        low = compute_academy_state(default_agent_knowledge(), 0)
        high = compute_academy_state(default_agent_knowledge(), 50)
        assert high.level > low.level


class TestKnowledgeLevels:
    """v0.7 Feature 31 — the same real points, a real seven-level
    Novice-through-Mentor name."""

    def test_six_thresholds_give_seven_real_levels(self) -> None:
        assert len(TIER_THRESHOLDS) == 6

    def test_crossing_every_threshold_reaches_mentor_level(self) -> None:
        knowledge = default_agent_knowledge()
        knowledge, _ = award_points(knowledge, "echo", TIER_THRESHOLDS[-1])
        assert knowledge["echo"].level == "mentor"
        assert knowledge["echo"].tier == 6

    def test_level_advances_with_each_real_threshold_crossed(self) -> None:
        knowledge = default_agent_knowledge()
        expected = ("novice", "beginner", "intermediate", "advanced", "expert", "master", "mentor")
        for i, threshold in enumerate(TIER_THRESHOLDS):
            knowledge, tier_up = award_points(knowledge, "echo", threshold - knowledge["echo"].points)
            assert tier_up is not None
            assert knowledge["echo"].level == expected[i + 1]

    def test_is_mentor_level_false_below_the_top_threshold(self) -> None:
        knowledge = default_agent_knowledge()
        knowledge, _ = award_points(knowledge, "echo", TIER_THRESHOLDS[-1] - 1.0)
        assert not is_mentor_level(knowledge["echo"])

    def test_is_mentor_level_true_at_the_top_threshold(self) -> None:
        knowledge = default_agent_knowledge()
        knowledge, _ = award_points(knowledge, "echo", TIER_THRESHOLDS[-1])
        assert is_mentor_level(knowledge["echo"])
