"""Covers app/vision_board.py — Design Bible Chapter 74.5, the CEO Vision
Board & Strategic Alignment Engine. Every alignment score must trace to
the CEO's own real, explicit ranking — never an inferred guess.
"""
from __future__ import annotations

from app.schemas import ConstitutionAmendment, Goal, SelfImprovementProposal
from app.vision_board import (
    RANKED_CONFIDENCE,
    SELF_IMPROVEMENT_TO_PRIORITY_CATEGORY,
    UNRANKED_CONFIDENCE,
    UNRANKED_SCORE,
    add_vision_objective,
    compute_constitution_amendment_alignment,
    compute_goal_alignment,
    compute_self_correction_note,
    compute_self_improvement_proposal_alignment,
    default_vision_board,
    remove_vision_objective,
    set_vision_identity_note,
    set_vision_mission,
    set_vision_priorities,
)


def _goal(goal_id: str = "goal-1", category: str = "risk") -> Goal:
    return Goal(
        id=goal_id,
        title="Test Goal",
        category=category,  # type: ignore[arg-type]
        targetMetric="company_health_combined",
        targetValue=80.0,
        currentValue=50.0,
        progressPct=50.0,
        createdSimDay=1,
        createdAt="2026-01-01T00:00:00+00:00",
        updatedAt="2026-01-01T00:00:00+00:00",
    )


def _amendment(amendment_id: str = "amendment-1") -> ConstitutionAmendment:
    return ConstitutionAmendment(
        id=amendment_id,
        proposedTitle="Test Amendment",
        proposedText="Test text.",
        status="proposed",
        simDay=1,
        createdAt="2026-01-01T00:00:00+00:00",
    )


def _proposal(proposal_id: str = "proposal-1", category: str = "risk_rule") -> SelfImprovementProposal:
    return SelfImprovementProposal(
        id=proposal_id,
        category=category,  # type: ignore[arg-type]
        title="Test Proposal",
        reasoning="test",
        estimatedComplexity="small",
        priority="medium",
        confidence=80.0,
        simDay=1,
        createdAt="2026-01-01T00:00:00+00:00",
    )


class TestDefaultVisionBoard:
    def test_starts_empty_and_honest(self) -> None:
        board = default_vision_board()
        assert board.mission is None
        assert board.priorities == []
        assert board.objectives == []
        assert board.identity_note is None


class TestSetVisionMission:
    def test_sets_mission_text(self) -> None:
        board = default_vision_board()
        updated = set_vision_mission(board, "Become the most disciplined fund in TradeTown.")
        assert updated.mission == "Become the most disciplined fund in TradeTown."

    def test_clears_mission(self) -> None:
        board = set_vision_mission(default_vision_board(), "Something")
        cleared = set_vision_mission(board, None)
        assert cleared.mission is None


class TestSetVisionIdentityNote:
    def test_sets_identity_note(self) -> None:
        board = set_vision_identity_note(default_vision_board(), "We are a risk-first shop.")
        assert board.identity_note == "We are a risk-first shop."


class TestSetVisionPriorities:
    def test_sets_a_valid_ranking(self) -> None:
        board, error = set_vision_priorities(default_vision_board(), ["risk", "growth", "governance"])
        assert error is None
        assert board.priorities == ["risk", "growth", "governance"]

    def test_rejects_duplicate_categories(self) -> None:
        board, error = set_vision_priorities(default_vision_board(), ["risk", "risk"])
        assert error is not None
        assert board.priorities == []

    def test_rejects_unknown_category(self) -> None:
        board, error = set_vision_priorities(default_vision_board(), ["not_a_real_category"])
        assert error is not None
        assert board.priorities == []


class TestAddVisionObjective:
    def test_adds_a_real_objective(self) -> None:
        board, error = add_vision_objective(default_vision_board(), "Focus on options trading", "trading_style")
        assert error is None
        assert len(board.objectives) == 1
        assert board.objectives[0].text == "Focus on options trading"
        assert board.objectives[0].category == "trading_style"

    def test_rejects_empty_text(self) -> None:
        board, error = add_vision_objective(default_vision_board(), "   ", "trading_style")
        assert error is not None
        assert board.objectives == []

    def test_rejects_unknown_category(self) -> None:
        board, error = add_vision_objective(default_vision_board(), "Real text", "not_a_real_category")
        assert error is not None
        assert board.objectives == []


class TestRemoveVisionObjective:
    def test_removes_the_matching_objective(self) -> None:
        board, _ = add_vision_objective(default_vision_board(), "First", "trading_style")
        objective_id = board.objectives[0].id
        updated = remove_vision_objective(board, objective_id)
        assert updated.objectives == []


class TestComputeGoalAlignment:
    def test_ranked_category_scores_by_rank(self) -> None:
        board, _ = set_vision_priorities(default_vision_board(), ["risk", "growth", "research"])
        score = compute_goal_alignment(_goal(category="risk"), board)
        assert score.score == 100.0
        assert score.confidence == RANKED_CONFIDENCE
        assert score.conflicting_goals == []

    def test_lowest_ranked_category_flags_a_conflict(self) -> None:
        board, _ = set_vision_priorities(default_vision_board(), ["risk", "growth", "research"])
        score = compute_goal_alignment(_goal(category="research"), board)
        assert score.score == round(100.0 / 3, 1)
        assert score.conflicting_goals == ["research"]

    def test_unranked_category_gets_neutral_default(self) -> None:
        board, _ = set_vision_priorities(default_vision_board(), ["risk"])
        score = compute_goal_alignment(_goal(category="growth"), board)
        assert score.score == UNRANKED_SCORE
        assert score.confidence == UNRANKED_CONFIDENCE

    def test_no_priorities_set_is_always_neutral(self) -> None:
        score = compute_goal_alignment(_goal(category="risk"), default_vision_board())
        assert score.score == UNRANKED_SCORE
        assert score.confidence == UNRANKED_CONFIDENCE


class TestComputeConstitutionAmendmentAlignment:
    def test_maps_to_governance(self) -> None:
        board, _ = set_vision_priorities(default_vision_board(), ["governance", "risk"])
        score = compute_constitution_amendment_alignment(_amendment(), board)
        assert score.score == 100.0
        assert score.subject_type == "constitution_amendment"

    def test_governance_unranked_gets_neutral_default(self) -> None:
        board, _ = set_vision_priorities(default_vision_board(), ["risk", "growth"])
        score = compute_constitution_amendment_alignment(_amendment(), board)
        assert score.score == UNRANKED_SCORE


class TestComputeSelfImprovementProposalAlignment:
    def test_every_category_has_a_disclosed_mapping(self) -> None:
        # No hidden weighting — every real SelfImprovementCategory must
        # map to exactly one VisionPriorityCategory.
        assert set(SELF_IMPROVEMENT_TO_PRIORITY_CATEGORY.keys()) == {
            "risk_rule", "dashboard", "research_workflow", "position_sizing",
            "new_executive", "automation", "knowledge_organization", "ui",
        }

    def test_risk_rule_maps_to_risk(self) -> None:
        board, _ = set_vision_priorities(default_vision_board(), ["risk"])
        score = compute_self_improvement_proposal_alignment(_proposal(category="risk_rule"), board)
        assert score.score == 100.0
        assert score.subject_type == "self_improvement_proposal"

    def test_research_workflow_maps_to_research(self) -> None:
        board, _ = set_vision_priorities(default_vision_board(), ["research"])
        score = compute_self_improvement_proposal_alignment(_proposal(category="research_workflow"), board)
        assert score.score == 100.0


class TestComputeSelfCorrectionNote:
    def test_triggers_when_top_priority_is_risk_and_breaker_is_tier2(self) -> None:
        board, _ = set_vision_priorities(default_vision_board(), ["risk", "growth"])
        note = compute_self_correction_note(board, "tier2")
        assert note.triggered is True
        assert note.message is not None

    def test_does_not_trigger_when_breaker_is_none(self) -> None:
        board, _ = set_vision_priorities(default_vision_board(), ["risk", "growth"])
        note = compute_self_correction_note(board, "none")
        assert note.triggered is False
        assert note.message is None

    def test_does_not_trigger_when_top_priority_is_not_risk(self) -> None:
        board, _ = set_vision_priorities(default_vision_board(), ["growth", "risk"])
        note = compute_self_correction_note(board, "tier3")
        assert note.triggered is False

    def test_does_not_trigger_with_no_priorities_set(self) -> None:
        note = compute_self_correction_note(default_vision_board(), "tier4")
        assert note.triggered is False
