"""Covers app/academy.py — v0.7 Feature 25's per-agent Knowledge Points/
Tiers, company-wide Academy level, and the mentorship substitute. Every
point awarded here traces back to real completed work in the caller
(nexus.py); this module only owns the arithmetic and thresholds.
"""
from __future__ import annotations

from app.academy import (
    MAX_LEARNING_EVENTS,
    MENTORSHIP_BONUS_POINTS,
    MENTORSHIP_GAP_THRESHOLD,
    TIER_THRESHOLDS,
    award_points,
    compute_academy_state,
    default_agent_knowledge,
    is_mentor_level,
    maybe_run_mentorship,
    record_learning_event,
)
from app.schemas import AGENT_IDS, LearningEvent


class TestDefaultAgentKnowledge:
    def test_every_agent_starts_at_zero_points_and_tier(self) -> None:
        knowledge = default_agent_knowledge()
        # v0.7 Feature 39 — the Original Founders (keystone/compass)
        # deliberately have no KNOWLEDGE_BRANCH entry: they're the
        # spiritual originators of the Academy/Reasoning Lab system, not
        # students earning points inside it (see app/founders.py's
        # module docstring). The Quant is the same case — its own real
        # progression is Innovation Points (app/black_box.py), not the
        # general Academy ladder. Quantitative Research & Intelligence
        # System, Piece 7 — Forge is the same case again: its own real
        # progression is the Monte Carlo reliability audit
        # (app/quant_developer.py), not the general Academy ladder.
        assert set(knowledge.keys()) == set(AGENT_IDS) - {"keystone", "compass", "quant", "forge"}
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
        updated, learning_event = award_points(knowledge, "echo", 2.0, source="research_completion")
        assert updated["echo"].points == 2.0
        assert updated["scout"].points == 0.0
        assert learning_event is None

    def test_crossing_a_threshold_returns_a_learning_event(self) -> None:
        knowledge = default_agent_knowledge()
        _updated, learning_event = award_points(knowledge, "echo", TIER_THRESHOLDS[0], source="research_completion")
        assert learning_event is not None
        assert learning_event.agent_id == "echo"
        assert learning_event.new_competency == 1
        assert learning_event.previous_competency == 0
        assert learning_event.previous_level == "novice"
        assert learning_event.new_level == "beginner"
        assert learning_event.source == "research_completion"
        assert learning_event.points_awarded == TIER_THRESHOLDS[0]
        assert learning_event.total_points == TIER_THRESHOLDS[0]

    def test_learning_event_source_reflects_the_real_caller(self) -> None:
        knowledge = default_agent_knowledge()
        _updated, learning_event = award_points(knowledge, "echo", TIER_THRESHOLDS[0], source="academy_project")
        assert learning_event is not None
        assert learning_event.source == "academy_project"

    def test_staying_below_threshold_does_not_report_a_learning_event(self) -> None:
        knowledge = default_agent_knowledge()
        _updated, learning_event = award_points(knowledge, "echo", TIER_THRESHOLDS[0] - 1.0, source="research_completion")
        assert learning_event is None

    def test_repeated_awards_accumulate_and_only_report_once_per_crossing(self) -> None:
        knowledge = default_agent_knowledge()
        knowledge, first = award_points(knowledge, "echo", TIER_THRESHOLDS[0], source="research_completion")
        assert first is not None
        knowledge, second = award_points(knowledge, "echo", 0.5, source="research_completion")
        assert second is None
        assert knowledge["echo"].points == TIER_THRESHOLDS[0] + 0.5

    def test_unknown_agent_id_is_a_no_op(self) -> None:
        knowledge = default_agent_knowledge()
        updated, learning_event = award_points(knowledge, "not-a-real-agent", 5.0, source="research_completion")  # type: ignore[arg-type]
        assert updated == knowledge
        assert learning_event is None


class TestRecordLearningEvent:
    def _event(self, suffix: str) -> LearningEvent:
        return LearningEvent(
            id=f"learning-echo-{suffix}",
            agentId="echo",
            skillDomain="Technical Analysis",
            previousCompetency=0,
            previousLevel="novice",
            newCompetency=1,
            newLevel="beginner",
            source="research_completion",
            pointsAwarded=3.0,
            totalPoints=3.0,
            createdAt="2026-01-01T00:00:00+00:00",
        )

    def test_appends_a_real_event(self) -> None:
        updated = record_learning_event([], self._event("1"))
        assert len(updated) == 1
        assert updated[0].id == "learning-echo-1"

    def test_caps_at_max_learning_events(self) -> None:
        events = [self._event(str(i)) for i in range(MAX_LEARNING_EVENTS)]
        updated = record_learning_event(events, self._event("overflow"))
        assert len(updated) == MAX_LEARNING_EVENTS
        assert updated[0].id == "learning-echo-1"
        assert updated[-1].id == "learning-echo-overflow"


class TestMaybeRunMentorship:
    def test_no_pairing_when_every_agent_is_still_at_zero(self) -> None:
        knowledge = default_agent_knowledge()
        updated, pairing, learning_event = maybe_run_mentorship(knowledge)
        assert pairing is None
        assert learning_event is None
        assert updated == knowledge

    def test_pairing_fires_once_the_gap_crosses_threshold(self) -> None:
        knowledge = default_agent_knowledge()
        knowledge, _ = award_points(knowledge, "echo", MENTORSHIP_GAP_THRESHOLD, source="research_completion")
        _updated, pairing, _learning_event = maybe_run_mentorship(knowledge)
        assert pairing is not None
        assert pairing[0] == "echo"

    def test_pairing_awards_the_mentee_a_real_bonus(self) -> None:
        knowledge = default_agent_knowledge()
        knowledge, _ = award_points(knowledge, "echo", MENTORSHIP_GAP_THRESHOLD, source="research_completion")
        updated, pairing, _learning_event = maybe_run_mentorship(knowledge)
        assert pairing is not None
        _mentor_id, mentee_id = pairing
        assert updated[mentee_id].points == MENTORSHIP_BONUS_POINTS

    def test_no_pairing_just_below_the_gap_threshold(self) -> None:
        knowledge = default_agent_knowledge()
        knowledge, _ = award_points(knowledge, "echo", MENTORSHIP_GAP_THRESHOLD - 1.0, source="research_completion")
        _updated, pairing, learning_event = maybe_run_mentorship(knowledge)
        assert pairing is None
        assert learning_event is None

    def test_mentorship_bonus_crossing_a_tier_reports_a_learning_event(self) -> None:
        # Award every non-mentor agent just below TIER_THRESHOLDS[0] so
        # the mentorship bonus itself is what pushes the mentee over;
        # keep echo exactly MENTORSHIP_GAP_THRESHOLD above the rest so
        # it's the unique mentor and the pairing still fires.
        knowledge = default_agent_knowledge()
        floor_points = TIER_THRESHOLDS[0] - MENTORSHIP_BONUS_POINTS
        for agent_id in list(knowledge.keys()):
            if agent_id != "echo":
                knowledge, _ = award_points(knowledge, agent_id, floor_points, source="research_completion")
        knowledge, _ = award_points(knowledge, "echo", floor_points + MENTORSHIP_GAP_THRESHOLD, source="research_completion")
        _updated, pairing, learning_event = maybe_run_mentorship(knowledge)
        assert pairing is not None
        assert learning_event is not None
        assert learning_event.agent_id == pairing[1]
        assert learning_event.source == "mentorship"


class TestComputeAcademyState:
    def test_fresh_knowledge_reads_as_level_one(self) -> None:
        state = compute_academy_state(default_agent_knowledge(), 0)
        assert state.level == 1
        assert state.level_label == "Training Room"
        assert state.total_points == 0.0
        assert state.completed_project_count == 0

    def test_total_points_sums_across_every_agent(self) -> None:
        knowledge = default_agent_knowledge()
        knowledge, _ = award_points(knowledge, "echo", 5.0, source="research_completion")
        knowledge, _ = award_points(knowledge, "scout", 3.0, source="research_completion")
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
        knowledge, _ = award_points(knowledge, "echo", TIER_THRESHOLDS[-1], source="research_completion")
        assert knowledge["echo"].level == "mentor"
        assert knowledge["echo"].tier == 6

    def test_level_advances_with_each_real_threshold_crossed(self) -> None:
        knowledge = default_agent_knowledge()
        expected = ("novice", "beginner", "intermediate", "advanced", "expert", "master", "mentor")
        for i, threshold in enumerate(TIER_THRESHOLDS):
            knowledge, learning_event = award_points(knowledge, "echo", threshold - knowledge["echo"].points, source="research_completion")
            assert learning_event is not None
            assert knowledge["echo"].level == expected[i + 1]

    def test_is_mentor_level_false_below_the_top_threshold(self) -> None:
        knowledge = default_agent_knowledge()
        knowledge, _ = award_points(knowledge, "echo", TIER_THRESHOLDS[-1] - 1.0, source="research_completion")
        assert not is_mentor_level(knowledge["echo"])

    def test_is_mentor_level_true_at_the_top_threshold(self) -> None:
        knowledge = default_agent_knowledge()
        knowledge, _ = award_points(knowledge, "echo", TIER_THRESHOLDS[-1], source="research_completion")
        assert is_mentor_level(knowledge["echo"])
