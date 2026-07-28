"""Covers app/mentor.py — v0.7 Feature 32, Sage the Socratic Mentor."""
from __future__ import annotations

from datetime import datetime, timezone

from app.mentor import (
    QUESTION_LIBRARY,
    compute_mentor_state,
    compute_thinking_profiles,
    generate_question_of_the_day,
    record_question,
    submit_response,
)
from app.schemas import (
    CaseStudy,
    CaseStudyTimelineEntry,
    DisciplineFactor,
    DisciplineReview,
    PostDecisionReview,
    QuestionOfTheDay,
    ReasoningChallenge,
    ReasoningContribution,
    ReasoningSolution,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _question(sim_day: int = 1, *, question_id: str = "qotd-1") -> QuestionOfTheDay:
    return generate_question_of_the_day(
        sim_day=sim_day,
        question_id=question_id,
        created_at=_now_iso(),
        case_studies=[],
        reasoning_challenges=[],
        research=[],
        reflection_sessions=[],
        risk_warnings=[],
        executive_reviews=[],
    )


def _case_study(*, category: str = "overconfidence") -> CaseStudy:
    return CaseStudy(
        id="case-1",
        category=category,  # type: ignore[arg-type]
        title="Chased a rally on NEXA",
        symbol="NEXA",
        decisionId="decision-1",
        timeline=[CaseStudyTimelineEntry(label="Opened", timestamp=_now_iso())],
        background="test background",
        decisionProcess="test process",
        departmentOpinions=["echo: momentum looked strong"],
        missedInformation="test missed info",
        lessonsLearned="Don't chase strength without confirmation.",
        recommendedImprovements="test improvements",
        relatedPrinciples=["Max position size"],
        tradePnlPct=-4.2,
        simDay=3,
        createdAt=_now_iso(),
    )


def _discipline_review(*, attendees: list[str], factors: list[DisciplineFactor]) -> DisciplineReview:
    return DisciplineReview(
        id="review-1",
        decisionId="decision-1",
        symbol="NEXA",
        score=70.0,
        tier="sound",
        factors=factors,
        attendees=attendees,  # type: ignore[arg-type]
        summary="test summary",
        postDecisionReview=PostDecisionReview(),
        outcome="win",
        tradePnlPct=3.5,
        holdDurationMinutes=300,
        simDay=2,
        createdAt=_now_iso(),
    )


class TestQuestionOfTheDay:
    def test_rotation_is_deterministic_by_sim_day(self) -> None:
        first = _question(sim_day=1)
        again = _question(sim_day=1)
        assert first.category == again.category
        assert first.question == again.question

    def test_cycles_through_the_whole_library(self) -> None:
        seen = {_question(sim_day=day, question_id=f"qotd-{day}").question for day in range(len(QUESTION_LIBRARY))}
        assert len(seen) == len(QUESTION_LIBRARY)

    def test_no_reference_when_no_real_history_exists(self) -> None:
        question = _question(sim_day=1)
        # Day 1 lands on QUESTION_LIBRARY[1 % len] == "decision_making" with
        # no case studies supplied, so no honest reference exists yet.
        assert question.category == QUESTION_LIBRARY[1][0]
        assert question.related_reference is None

    def test_psychology_question_references_real_case_study(self) -> None:
        # Find the sim_day that lands on a "psychology" question.
        day = next(i for i, (category, _) in enumerate(QUESTION_LIBRARY) if category == "psychology")
        question = generate_question_of_the_day(
            sim_day=day,
            question_id="qotd-psych",
            created_at=_now_iso(),
            case_studies=[_case_study()],
            reasoning_challenges=[],
            research=[],
            reflection_sessions=[],
            risk_warnings=[],
            executive_reviews=[],
        )
        assert question.related_reference is not None
        assert "Chased a rally on NEXA" in question.related_reference


class TestRecordQuestion:
    def test_caps_the_archive(self) -> None:
        archive: list[QuestionOfTheDay] = []
        for day in range(140):
            archive = record_question(archive, _question(sim_day=day, question_id=f"qotd-{day}"))
        assert len(archive) == 120
        assert archive[-1].id == "qotd-139"


class TestSubmitResponse:
    def test_stores_a_real_response(self) -> None:
        archive = [_question()]
        updated, error = submit_response(archive, "qotd-1", "  I think we're overconfident.  ", responded_at=_now_iso())
        assert error is None
        assert updated[0].player_response == "I think we're overconfident."
        assert updated[0].player_responded_at is not None

    def test_rejects_empty_response(self) -> None:
        archive = [_question()]
        updated, error = submit_response(archive, "qotd-1", "   ", responded_at=_now_iso())
        assert error is not None
        assert updated[0].player_response is None

    def test_rejects_unknown_question_id(self) -> None:
        archive = [_question()]
        updated, error = submit_response(archive, "qotd-does-not-exist", "an answer", responded_at=_now_iso())
        assert error is not None
        assert updated == archive


class TestComputeThinkingProfiles:
    def test_agents_with_no_history_get_honest_neutral_defaults(self) -> None:
        profiles = compute_thinking_profiles(("scribe",), discipline_reviews=[], reasoning_challenges=[], reflection_sessions=[], agent_knowledge={}, updated_at=_now_iso())
        traits = {t.id: t.score for t in profiles["scribe"].traits}
        assert traits["curiosity"] == 0.0
        assert traits["evidence_quality"] == 50.0
        assert traits["collaboration"] == 0.0

    def test_discipline_review_attendance_raises_evidence_quality(self) -> None:
        review = _discipline_review(
            attendees=["echo"],
            factors=[DisciplineFactor(id="research_depth", name="Research Depth", score=90.0, weight=0.2, detail="deep research")],
        )
        profiles = compute_thinking_profiles(("echo",), discipline_reviews=[review], reasoning_challenges=[], reflection_sessions=[], agent_knowledge={}, updated_at=_now_iso())
        evidence = next(t for t in profiles["echo"].traits if t.id == "evidence_quality")
        assert evidence.score == 90.0

    def test_reasoning_lab_contribution_raises_collaboration(self) -> None:
        challenge = ReasoningChallenge(
            id="reasoning-1",
            category="finding_missing_information",
            title="test challenge",
            symbol="NEXA",
            decisionId="decision-1",
            contributions=[ReasoningContribution(agentId="echo", role="technical", stance="opening", contribution="test")],  # type: ignore[arg-type]
            solution=ReasoningSolution(whatWeKnow=[], whatWeDoNotKnow=[], assumptions=[], whyReasonable="test", confidence=80.0, whatCouldChangeOurConclusion="test"),
            reasoningLevel=1,
            simDay=1,
            createdAt=_now_iso(),
        )
        profiles = compute_thinking_profiles(("echo",), discipline_reviews=[], reasoning_challenges=[challenge], reflection_sessions=[], agent_knowledge={}, updated_at=_now_iso())
        collaboration = next(t for t in profiles["echo"].traits if t.id == "collaboration")
        assert collaboration.score > 0.0


class TestComputeMentorState:
    def test_starts_at_new_tradition(self) -> None:
        state = compute_mentor_state(1, _now_iso())
        assert state.tier == 0
        assert state.tier_label == "New Tradition"

    def test_crosses_into_taking_root_at_a_week(self) -> None:
        assert compute_mentor_state(6, _now_iso()).tier == 0
        assert compute_mentor_state(7, _now_iso()).tier == 1
        assert compute_mentor_state(7, _now_iso()).tier_label == "Taking Root"

    def test_crosses_into_defining_tradition_at_ninety(self) -> None:
        assert compute_mentor_state(89, _now_iso()).tier == 2
        assert compute_mentor_state(90, _now_iso()).tier == 3
        assert compute_mentor_state(90, _now_iso()).tier_label == "Defining Tradition"
