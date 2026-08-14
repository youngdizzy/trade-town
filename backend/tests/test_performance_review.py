"""Covers app/performance_review.py — CEO directive "Features 26-30,"
Feature 27 (Agent Performance Reviews). Every dimension must be real
evidence or an honest NOT_ENOUGH_EVIDENCE (None); process quality must
never see P&L; outcome quality must never be blended with process; role
class must be static and exhaustive; trend/weakest-dimension must be
derivable only from real measured data.
"""
from __future__ import annotations

from app.performance_review import (
    AGENT_ROLE_CLASS,
    MIN_EVIDENCE_COUNT_FOR_EVALUATED,
    compute_agent_performance_review,
    latest_review_for_agent,
    record_agent_performance_review,
)
from app.schemas import (
    AgentId,
    CaseStudy,
    DisciplineFactor,
    DisciplineReview,
    PaperTrade,
    ReasoningChallenge,
    ReasoningContribution,
    ReasoningSolution,
    ReflectionInsight,
    ReflectionSession,
    ResearchItem,
    TradeDecision,
)


def _now_iso() -> str:
    return "2026-01-01T00:00:00+00:00"


def _empty_review_kwargs() -> dict:
    return dict(
        discipline_reviews=[],
        research=[],
        trades=[],
        decisions=[],
        case_studies=[],
        reasoning_challenges=[],
        reflection_sessions=[],
        agent_knowledge={},
        learning_events=[],
        period_start_sim_day=1,
        period_end_sim_day=7,
        sim_day=7,
        previous_review=None,
    )


def _discipline_factor(factor_id: str, score: float) -> DisciplineFactor:
    return DisciplineFactor(id=factor_id, name=factor_id, score=score, weight=0.1, detail="test")  # type: ignore[arg-type]


def _discipline_review(
    *,
    review_id: str = "review-1",
    attendees: list[AgentId],
    score: float = 70.0,
    sim_day: int = 3,
    factors: list[DisciplineFactor] | None = None,
) -> DisciplineReview:
    from app.schemas import PostDecisionReview

    return DisciplineReview(
        id=review_id,
        decisionId="decision-1",
        symbol="NEXA",
        score=score,
        tier="sound",  # type: ignore[arg-type]
        factors=factors or [],
        attendees=attendees,
        summary="test summary",
        postDecisionReview=PostDecisionReview(
            wouldRepeat=True, whatWentWell="test", whatToImprove="test", keyLesson="test"
        ),
        outcome="win",  # type: ignore[arg-type]
        tradePnlPct=1.0,
        holdDurationMinutes=60,
        simDay=sim_day,
        createdAt=_now_iso(),
    )


def _research_item(*, agent_id: AgentId, confidence: float, status: str = "completed") -> ResearchItem:
    return ResearchItem(
        id=f"research-{agent_id}-{confidence}",
        title="test",
        symbol="NEXA",
        category="stock",  # type: ignore[arg-type]
        priority="normal",  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        assignedAgent=agent_id,
        summary="test",
        confidence=confidence,
        createdAt=_now_iso(),
        updatedAt=_now_iso(),
    )


def _trade(*, trade_id: str, supporting_agents: list[AgentId], confidence: float = 80.0, pnl: float = 5.0, pnl_pct: float = 2.0, closed_sim_minutes: int = 3 * 1440) -> PaperTrade:
    return PaperTrade(
        id=trade_id,
        symbol="NEXA",
        side="buy",  # type: ignore[arg-type]
        quantity=10.0,
        entryPrice=100.0,
        exitPrice=102.0,
        pnl=pnl,
        pnlPct=pnl_pct,
        durationMinutes=60,
        confidence=confidence,
        reason="test",
        marketConditions="test",
        supportingAgents=supporting_agents,
        openedAt=_now_iso(),
        closedAt=_now_iso(),
        openedSimMinutes=closed_sim_minutes - 60,
        closedSimMinutes=closed_sim_minutes,
        decisionId="decision-1",
    )


def _decision(*, decision_id: str = "decision-1", supporting_agents: list[AgentId]) -> TradeDecision:
    return TradeDecision(
        id=decision_id,
        symbol="NEXA",
        outcome="trade",  # type: ignore[arg-type]
        researchSummary="test",
        technicalSummary="test",
        fundamentalSummary="test",
        riskSummary="test",
        supportingAgents=supporting_agents,
        opposingAgents=[],
        confidence=80.0,
        finalReasoning="test",
        createdAt=_now_iso(),
    )


def _case_study(*, decision_id: str = "decision-1", category: str = "acted_too_quickly", sim_day: int = 3) -> CaseStudy:
    return CaseStudy(
        id="case-1",
        category=category,  # type: ignore[arg-type]
        title="test",
        symbol="NEXA",
        decisionId=decision_id,
        timeline=[],
        background="test",
        decisionProcess="test",
        departmentOpinions=[],
        missedInformation="test",
        lessonsLearned="test",
        recommendedImprovements="test",
        relatedPrinciples=[],
        tradePnlPct=-2.0,
        simDay=sim_day,
        createdAt=_now_iso(),
    )


class TestAgentRoleClass:
    def test_every_real_agent_has_a_role_class(self) -> None:
        from app.agents import all_agent_ids

        for agent_id in all_agent_ids():
            assert agent_id in AGENT_ROLE_CLASS

    def test_researchers_and_risk_agents_are_correctly_classed(self) -> None:
        assert AGENT_ROLE_CLASS["scout"] == "researcher"
        assert AGENT_ROLE_CLASS["sentinel"] == "risk"
        assert AGENT_ROLE_CLASS["quant"] == "quant"


class TestNoEvidenceIsHonest:
    def test_agent_with_zero_evidence_gets_all_none_dimensions(self) -> None:
        review = compute_agent_performance_review("scout", **_empty_review_kwargs())
        assert all(d.value is None for d in review.dimensions)
        assert all(d.sample_size == 0 for d in review.dimensions)
        assert review.process_quality_avg is None
        assert review.outcome_quality_avg is None
        assert review.status == "not_enough_evidence"
        assert review.confidence_pct == 0.0
        assert review.weakest_dimension_id is None
        assert review.trend == "not_enough_history"


class TestProcessQualityNeverSeesPnl:
    def test_process_quality_ignores_trade_outcome(self) -> None:
        kwargs = _empty_review_kwargs()
        kwargs["discipline_reviews"] = [_discipline_review(attendees=["scout"], score=85.0, sim_day=3)]
        # A losing trade attached to a case study should not move process_quality.
        kwargs["case_studies"] = [_case_study(category="acted_too_quickly", sim_day=3)]
        kwargs["decisions"] = [_decision(supporting_agents=["scout"])]
        kwargs["trades"] = [_trade(trade_id="trade-1", supporting_agents=["scout"], pnl=-50.0, pnl_pct=-10.0)]
        review = compute_agent_performance_review("scout", **kwargs)
        process_dim = next(d for d in review.dimensions if d.id == "process_quality")
        assert process_dim.value == 85.0


class TestRecurringMistakesRealAttribution:
    def test_mistake_case_study_attributed_only_to_supporting_agent(self) -> None:
        kwargs = _empty_review_kwargs()
        kwargs["decisions"] = [_decision(supporting_agents=["scout"])]
        kwargs["case_studies"] = [_case_study(category="acted_too_quickly", sim_day=3)]
        kwargs["trades"] = [_trade(trade_id="trade-1", supporting_agents=["scout"], pnl=-10.0, pnl_pct=-2.0, closed_sim_minutes=3 * 1440)]
        review = compute_agent_performance_review("scout", **kwargs)
        dim = next(d for d in review.dimensions if d.id == "recurring_mistakes")
        assert dim.value == 0.0  # 1 of 1 supported trades was a real mistake -> 0% mistake-free
        assert dim.sample_size == 1

    def test_success_category_case_study_never_counted_as_mistake(self) -> None:
        kwargs = _empty_review_kwargs()
        kwargs["decisions"] = [_decision(supporting_agents=["scout"])]
        kwargs["case_studies"] = [_case_study(category="disciplined_process", sim_day=3)]
        kwargs["trades"] = [_trade(trade_id="trade-1", supporting_agents=["scout"], closed_sim_minutes=3 * 1440)]
        review = compute_agent_performance_review("scout", **kwargs)
        dim = next(d for d in review.dimensions if d.id == "recurring_mistakes")
        assert dim.value == 100.0  # no real mistake attributed

    def test_agent_not_supporting_the_decision_is_not_blamed(self) -> None:
        kwargs = _empty_review_kwargs()
        kwargs["decisions"] = [_decision(supporting_agents=["nova"])]
        kwargs["case_studies"] = [_case_study(category="acted_too_quickly", sim_day=3)]
        kwargs["trades"] = [_trade(trade_id="trade-1", supporting_agents=["scout"], closed_sim_minutes=3 * 1440)]
        review = compute_agent_performance_review("scout", **kwargs)
        dim = next(d for d in review.dimensions if d.id == "recurring_mistakes")
        assert dim.value == 100.0  # scout supported the trade but not the (mistake-tagged) decision


class TestDecisionAccuracyAndCalibration:
    def test_decision_accuracy_uses_real_research_confidence(self) -> None:
        kwargs = _empty_review_kwargs()
        kwargs["research"] = [
            _research_item(agent_id="scout", confidence=80.0),
            _research_item(agent_id="scout", confidence=40.0),
        ]
        review = compute_agent_performance_review("scout", **kwargs)
        dim = next(d for d in review.dimensions if d.id == "decision_accuracy")
        assert dim.value == 50.0  # 1 of 2 >= 70%
        assert dim.sample_size == 2

    def test_research_from_other_agents_not_counted(self) -> None:
        kwargs = _empty_review_kwargs()
        kwargs["research"] = [_research_item(agent_id="nova", confidence=80.0)]
        review = compute_agent_performance_review("scout", **kwargs)
        dim = next(d for d in review.dimensions if d.id == "decision_accuracy")
        assert dim.value is None

    def test_calibration_filters_by_supporting_agents_and_period(self) -> None:
        kwargs = _empty_review_kwargs()
        kwargs["trades"] = [
            _trade(trade_id="in-period", supporting_agents=["scout"], confidence=90.0, pnl=10.0, closed_sim_minutes=5 * 1440),
            _trade(trade_id="out-of-period", supporting_agents=["scout"], confidence=10.0, pnl=-10.0, closed_sim_minutes=100 * 1440),
        ]
        review = compute_agent_performance_review("scout", **kwargs)
        dim = next(d for d in review.dimensions if d.id == "calibration")
        assert dim.sample_size == 1  # only the in-period trade counts


class TestCollaboration:
    def test_zero_contributions_is_not_enough_evidence(self) -> None:
        review = compute_agent_performance_review("scout", **_empty_review_kwargs())
        dim = next(d for d in review.dimensions if d.id == "collaboration")
        assert dim.value is None

    def test_real_contributions_and_insights_are_counted(self) -> None:
        kwargs = _empty_review_kwargs()
        challenge = ReasoningChallenge(
            id="challenge-1",
            category="finding_missing_information",  # type: ignore[arg-type]
            title="test",
            symbol="NEXA",
            decisionId="decision-1",
            contributions=[ReasoningContribution(agentId="scout", role="technical", stance="opening", contribution="test")],  # type: ignore[arg-type]
            solution=ReasoningSolution(whyReasonable="test", confidence=70.0, whatCouldChangeOurConclusion="test"),
            reasoningLevel=1,
            simDay=3,
            createdAt=_now_iso(),
        )
        session = ReflectionSession(
            id="session-1",
            cadence="weekly",  # type: ignore[arg-type]
            attendees=["scout"],
            questions=[],
            insights=[ReflectionInsight(agentId="scout", insight="test")],
            wisdomScore=50.0,
            simDay=3,
            createdAt=_now_iso(),
        )
        kwargs["reasoning_challenges"] = [challenge]
        kwargs["reflection_sessions"] = [session]
        review = compute_agent_performance_review("scout", **kwargs)
        dim = next(d for d in review.dimensions if d.id == "collaboration")
        assert dim.value is not None
        assert dim.sample_size == 2


class TestStatusGating:
    def test_status_evaluated_once_evidence_threshold_met(self) -> None:
        kwargs = _empty_review_kwargs()
        kwargs["discipline_reviews"] = [_discipline_review(attendees=["scout"], score=80.0, sim_day=i) for i in range(1, MIN_EVIDENCE_COUNT_FOR_EVALUATED + 1)]
        review = compute_agent_performance_review("scout", **kwargs)
        assert review.evidence_count >= MIN_EVIDENCE_COUNT_FOR_EVALUATED
        assert review.status == "evaluated"

    def test_status_stays_not_enough_evidence_below_threshold(self) -> None:
        kwargs = _empty_review_kwargs()
        kwargs["discipline_reviews"] = [_discipline_review(attendees=["scout"], score=80.0, sim_day=3)]
        review = compute_agent_performance_review("scout", **kwargs)
        assert review.evidence_count < MIN_EVIDENCE_COUNT_FOR_EVALUATED
        assert review.status == "not_enough_evidence"


class TestTrend:
    def test_no_previous_review_is_not_enough_history(self) -> None:
        kwargs = _empty_review_kwargs()
        kwargs["discipline_reviews"] = [_discipline_review(attendees=["scout"], score=80.0, sim_day=3)]
        review = compute_agent_performance_review("scout", **kwargs)
        assert review.trend == "not_enough_history"

    def test_improving_trend_detected_against_a_real_previous_review(self) -> None:
        kwargs = _empty_review_kwargs()
        kwargs["discipline_reviews"] = [_discipline_review(attendees=["scout"], score=50.0, sim_day=3)]
        previous = compute_agent_performance_review("scout", **kwargs)

        kwargs2 = _empty_review_kwargs()
        kwargs2["discipline_reviews"] = [_discipline_review(attendees=["scout"], score=90.0, sim_day=10)]
        kwargs2["period_start_sim_day"] = 8
        kwargs2["period_end_sim_day"] = 14
        kwargs2["sim_day"] = 14
        kwargs2["previous_review"] = previous
        current = compute_agent_performance_review("scout", **kwargs2)
        assert current.trend == "improving"

    def test_declining_trend_detected(self) -> None:
        kwargs = _empty_review_kwargs()
        kwargs["discipline_reviews"] = [_discipline_review(attendees=["scout"], score=90.0, sim_day=3)]
        previous = compute_agent_performance_review("scout", **kwargs)

        kwargs2 = _empty_review_kwargs()
        kwargs2["discipline_reviews"] = [_discipline_review(attendees=["scout"], score=50.0, sim_day=10)]
        kwargs2["period_start_sim_day"] = 8
        kwargs2["period_end_sim_day"] = 14
        kwargs2["sim_day"] = 14
        kwargs2["previous_review"] = previous
        current = compute_agent_performance_review("scout", **kwargs2)
        assert current.trend == "declining"


class TestWeakestDimension:
    def test_weakest_dimension_is_the_lowest_real_measured_one(self) -> None:
        kwargs = _empty_review_kwargs()
        kwargs["discipline_reviews"] = [_discipline_review(attendees=["scout"], score=20.0, sim_day=3)]
        kwargs["research"] = [_research_item(agent_id="scout", confidence=90.0)]
        review = compute_agent_performance_review("scout", **kwargs)
        assert review.weakest_dimension_id == "process_quality"


class TestRecordAndLatest:
    def test_record_caps_the_list(self) -> None:
        reviews = []
        for i in range(5):
            kwargs = _empty_review_kwargs()
            kwargs["sim_day"] = i
            review = compute_agent_performance_review("scout", **kwargs)
            reviews = record_agent_performance_review(reviews, review, max_reviews=3)
        assert len(reviews) == 3

    def test_latest_review_for_agent_filters_correctly(self) -> None:
        reviews = []
        for agent_id, sim_day in [("scout", 1), ("nova", 2), ("scout", 3)]:
            kwargs = _empty_review_kwargs()
            kwargs["sim_day"] = sim_day
            review = compute_agent_performance_review(agent_id, **kwargs)  # type: ignore[arg-type]
            reviews.append(review)
        latest = latest_review_for_agent(reviews, "scout")
        assert latest is not None
        assert latest.sim_day == 3

    def test_latest_review_returns_none_when_agent_has_no_reviews(self) -> None:
        assert latest_review_for_agent([], "scout") is None
