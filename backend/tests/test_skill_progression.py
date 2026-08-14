"""Covers app/skill_progression.py — CEO directive "Features 26-30,"
Feature 28 (Academy + Skill Progression). Every measurable domain must
reuse real evidence or return an honest None; every NOT_TRACKABLE_YET
domain must stay None regardless of input data; trend must be a real
improve/stagnate/regress read against the agent's own previous
assessment of the SAME domain; the training recommendation must only
fire when a real weak dimension maps to a real, content-backed mentor
track the agent hasn't already graduated.
"""
from __future__ import annotations

from app.schemas import (
    AgentId,
    AgentPerformanceReview,
    DisciplineFactor,
    DisciplineReview,
    FoundationalMentorProgress,
    FoundationalMentorState,
    PerformanceDimension,
    PostDecisionReview,
    ReasoningChallenge,
    ReasoningContribution,
    ReasoningSolution,
    ReflectionInsight,
    ReflectionSession,
    ResearchItem,
)
from app.skill_progression import (
    ALL_SKILL_DOMAIN_IDS,
    SKILL_DOMAIN_RECOMMENDED_MENTOR,
    compute_agent_skill_profile,
    latest_skill_profile_for_agent,
    record_agent_skill_profile,
)

NOT_TRACKABLE_DOMAINS = {"market_structure", "quant_research", "technical_fundamental_analysis", "execution", "regime_detection", "communication"}
MEASURABLE_DOMAINS = {"risk_management", "research_quality", "prediction_calibration", "collaboration", "statistical_reasoning"}


def _now_iso() -> str:
    return "2026-01-01T00:00:00+00:00"


def _empty_kwargs() -> dict:
    return dict(
        discipline_reviews=[],
        research=[],
        trades=[],
        reasoning_challenges=[],
        reflection_sessions=[],
        period_start_sim_day=1,
        period_end_sim_day=7,
        sim_day=7,
        previous_profile=None,
        latest_review=None,
        foundational_mentor_state=FoundationalMentorState(mentors=[], progress={}, ceoProgress={}, activeMentorId=None, roadmapOrder=[], customLessonAnswers={}, updatedAt=_now_iso()),
    )


def _discipline_factor(factor_id: str, score: float) -> DisciplineFactor:
    return DisciplineFactor(id=factor_id, name=factor_id, score=score, weight=0.1, detail="test")  # type: ignore[arg-type]


def _discipline_review(*, attendees: list[AgentId], factors: list[DisciplineFactor], sim_day: int = 3) -> DisciplineReview:
    return DisciplineReview(
        id=f"review-{sim_day}",
        decisionId="decision-1",
        symbol="NEXA",
        score=70.0,
        tier="sound",  # type: ignore[arg-type]
        factors=factors,
        attendees=attendees,
        summary="test",
        postDecisionReview=PostDecisionReview(),
        outcome="win",  # type: ignore[arg-type]
        tradePnlPct=1.0,
        holdDurationMinutes=60,
        simDay=sim_day,
        createdAt=_now_iso(),
    )


def _research_item(*, agent_id: AgentId, confidence: float) -> ResearchItem:
    return ResearchItem(
        id=f"research-{agent_id}-{confidence}",
        title="test",
        symbol="NEXA",
        category="stock",  # type: ignore[arg-type]
        priority="normal",  # type: ignore[arg-type]
        status="completed",  # type: ignore[arg-type]
        assignedAgent=agent_id,
        summary="test",
        confidence=confidence,
        createdAt=_now_iso(),
        updatedAt=_now_iso(),
    )


def _trade(*, trade_id: str, supporting_agents: list[AgentId], confidence: float = 80.0, closed_sim_minutes: int = 3 * 1440):
    from app.schemas import PaperTrade

    return PaperTrade(
        id=trade_id,
        symbol="NEXA",
        side="buy",  # type: ignore[arg-type]
        quantity=10.0,
        entryPrice=100.0,
        exitPrice=102.0,
        pnl=5.0,
        pnlPct=2.0,
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


def _performance_review(*, weakest_dimension_id: str | None, period_end_sim_day: int = 7) -> AgentPerformanceReview:
    dims = [
        PerformanceDimension(id="risk_discipline", label="Risk Discipline", value=20.0, sampleSize=3, evidence="test"),  # type: ignore[arg-type]
        PerformanceDimension(id="process_quality", label="Process Quality", value=90.0, sampleSize=3, evidence="test"),  # type: ignore[arg-type]
    ]
    return AgentPerformanceReview(
        id="review-1",
        agentId="scout",
        roleClass="researcher",  # type: ignore[arg-type]
        periodStartSimDay=1,
        periodEndSimDay=period_end_sim_day,
        dimensions=dims,
        processQualityAvg=90.0,
        outcomeQualityAvg=None,
        evidenceCount=3,
        confidencePct=50.0,
        trend="declining",  # type: ignore[arg-type]
        weakestDimensionId=weakest_dimension_id,  # type: ignore[arg-type]
        status="evaluated",  # type: ignore[arg-type]
        simDay=period_end_sim_day,
        createdAt=_now_iso(),
    )


def _mentor_state(*, progress: dict | None = None) -> FoundationalMentorState:
    return FoundationalMentorState(
        mentors=[], progress=progress or {}, ceoProgress={}, activeMentorId=None, roadmapOrder=[], customLessonAnswers={}, updatedAt=_now_iso()
    )


class TestDomainTaxonomy:
    def test_every_profile_has_exactly_eleven_domains(self) -> None:
        profile = compute_agent_skill_profile("scout", **_empty_kwargs())
        assert len(profile.assessments) == 11
        assert {a.domain_id for a in profile.assessments} == set(ALL_SKILL_DOMAIN_IDS)

    def test_not_trackable_domains_are_always_none_with_zero_evidence(self) -> None:
        profile = compute_agent_skill_profile("scout", **_empty_kwargs())
        for a in profile.assessments:
            if a.domain_id in NOT_TRACKABLE_DOMAINS:
                assert a.value is None
                assert a.sample_size == 0
                assert a.trend == "not_enough_history"
                assert len(a.evidence) > 0

    def test_not_trackable_stays_none_even_with_heavy_real_data(self) -> None:
        kwargs = _empty_kwargs()
        kwargs["discipline_reviews"] = [
            _discipline_review(attendees=["scout"], factors=[_discipline_factor("position_sizing_discipline", 95.0), _discipline_factor("patience", 95.0)], sim_day=i)
            for i in range(1, 6)
        ]
        kwargs["research"] = [_research_item(agent_id="scout", confidence=95.0) for _ in range(5)]
        profile = compute_agent_skill_profile("scout", **kwargs)
        for a in profile.assessments:
            if a.domain_id in NOT_TRACKABLE_DOMAINS:
                assert a.value is None


class TestMeasurableDomains:
    def test_zero_evidence_is_honest_none_for_every_measurable_domain(self) -> None:
        profile = compute_agent_skill_profile("scout", **_empty_kwargs())
        for a in profile.assessments:
            if a.domain_id in MEASURABLE_DOMAINS:
                assert a.value is None
                assert a.sample_size == 0

    def test_risk_management_reuses_position_sizing_and_patience_factors(self) -> None:
        kwargs = _empty_kwargs()
        kwargs["discipline_reviews"] = [
            _discipline_review(attendees=["scout"], factors=[_discipline_factor("position_sizing_discipline", 80.0), _discipline_factor("patience", 60.0)])
        ]
        profile = compute_agent_skill_profile("scout", **kwargs)
        dim = next(a for a in profile.assessments if a.domain_id == "risk_management")
        assert dim.value == 70.0

    def test_research_quality_only_counts_own_agent_completed_research(self) -> None:
        kwargs = _empty_kwargs()
        kwargs["research"] = [_research_item(agent_id="scout", confidence=80.0), _research_item(agent_id="nova", confidence=80.0)]
        profile = compute_agent_skill_profile("scout", **kwargs)
        dim = next(a for a in profile.assessments if a.domain_id == "research_quality")
        assert dim.sample_size == 1

    def test_prediction_calibration_filters_by_period(self) -> None:
        kwargs = _empty_kwargs()
        kwargs["trades"] = [
            _trade(trade_id="in-period", supporting_agents=["scout"], closed_sim_minutes=5 * 1440),
            _trade(trade_id="out-of-period", supporting_agents=["scout"], closed_sim_minutes=100 * 1440),
        ]
        profile = compute_agent_skill_profile("scout", **kwargs)
        dim = next(a for a in profile.assessments if a.domain_id == "prediction_calibration")
        assert dim.sample_size == 1

    def test_collaboration_counts_real_contributions_and_insights(self) -> None:
        kwargs = _empty_kwargs()
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
            id="session-1", cadence="weekly", attendees=["scout"], questions=[], insights=[ReflectionInsight(agentId="scout", insight="test")],  # type: ignore[arg-type]
            wisdomScore=50.0, simDay=3, createdAt=_now_iso(),
        )
        kwargs["reasoning_challenges"] = [challenge]
        kwargs["reflection_sessions"] = [session]
        profile = compute_agent_skill_profile("scout", **kwargs)
        dim = next(a for a in profile.assessments if a.domain_id == "collaboration")
        assert dim.sample_size == 2

    def test_statistical_reasoning_averages_assumptions_and_cross_exam(self) -> None:
        kwargs = _empty_kwargs()
        kwargs["discipline_reviews"] = [
            _discipline_review(attendees=["scout"], factors=[_discipline_factor("assumptions_challenged", 80.0), _discipline_factor("cross_examination", 40.0)])
        ]
        profile = compute_agent_skill_profile("scout", **kwargs)
        dim = next(a for a in profile.assessments if a.domain_id == "statistical_reasoning")
        assert dim.value == 60.0


class TestTrend:
    def test_no_previous_profile_is_not_enough_history(self) -> None:
        kwargs = _empty_kwargs()
        kwargs["discipline_reviews"] = [_discipline_review(attendees=["scout"], factors=[_discipline_factor("position_sizing_discipline", 50.0), _discipline_factor("patience", 50.0)])]
        profile = compute_agent_skill_profile("scout", **kwargs)
        dim = next(a for a in profile.assessments if a.domain_id == "risk_management")
        assert dim.trend == "not_enough_history"

    def test_improving_trend_against_a_real_previous_assessment(self) -> None:
        kwargs = _empty_kwargs()
        kwargs["discipline_reviews"] = [_discipline_review(attendees=["scout"], factors=[_discipline_factor("position_sizing_discipline", 30.0), _discipline_factor("patience", 30.0)])]
        previous = compute_agent_skill_profile("scout", **kwargs)

        kwargs2 = _empty_kwargs()
        kwargs2["discipline_reviews"] = [_discipline_review(attendees=["scout"], factors=[_discipline_factor("position_sizing_discipline", 90.0), _discipline_factor("patience", 90.0)], sim_day=10)]
        kwargs2["period_start_sim_day"] = 8
        kwargs2["period_end_sim_day"] = 14
        kwargs2["sim_day"] = 14
        kwargs2["previous_profile"] = previous
        current = compute_agent_skill_profile("scout", **kwargs2)
        dim = next(a for a in current.assessments if a.domain_id == "risk_management")
        assert dim.trend == "improving"

    def test_regressed_trend_against_a_real_previous_assessment(self) -> None:
        kwargs = _empty_kwargs()
        kwargs["discipline_reviews"] = [_discipline_review(attendees=["scout"], factors=[_discipline_factor("position_sizing_discipline", 90.0), _discipline_factor("patience", 90.0)])]
        previous = compute_agent_skill_profile("scout", **kwargs)

        kwargs2 = _empty_kwargs()
        kwargs2["discipline_reviews"] = [_discipline_review(attendees=["scout"], factors=[_discipline_factor("position_sizing_discipline", 30.0), _discipline_factor("patience", 30.0)], sim_day=10)]
        kwargs2["period_start_sim_day"] = 8
        kwargs2["period_end_sim_day"] = 14
        kwargs2["sim_day"] = 14
        kwargs2["previous_profile"] = previous
        current = compute_agent_skill_profile("scout", **kwargs2)
        dim = next(a for a in current.assessments if a.domain_id == "risk_management")
        assert dim.trend == "regressed"

    def test_stagnant_trend_within_the_dead_zone(self) -> None:
        kwargs = _empty_kwargs()
        kwargs["discipline_reviews"] = [_discipline_review(attendees=["scout"], factors=[_discipline_factor("position_sizing_discipline", 70.0), _discipline_factor("patience", 70.0)])]
        previous = compute_agent_skill_profile("scout", **kwargs)

        kwargs2 = _empty_kwargs()
        kwargs2["discipline_reviews"] = [_discipline_review(attendees=["scout"], factors=[_discipline_factor("position_sizing_discipline", 71.0), _discipline_factor("patience", 71.0)], sim_day=10)]
        kwargs2["period_start_sim_day"] = 8
        kwargs2["period_end_sim_day"] = 14
        kwargs2["sim_day"] = 14
        kwargs2["previous_profile"] = previous
        current = compute_agent_skill_profile("scout", **kwargs2)
        dim = next(a for a in current.assessments if a.domain_id == "risk_management")
        assert dim.trend == "stagnant"


class TestTrainingRecommendation:
    def test_no_review_means_no_recommendation(self) -> None:
        profile = compute_agent_skill_profile("scout", **_empty_kwargs())
        assert profile.recommended_domain_id is None
        assert profile.recommended_mentor_id is None
        assert profile.recommendation_reason is None

    def test_weakest_dimension_with_no_skill_domain_mapping_yields_no_recommendation(self) -> None:
        kwargs = _empty_kwargs()
        kwargs["latest_review"] = _performance_review(weakest_dimension_id="process_quality")
        profile = compute_agent_skill_profile("scout", **kwargs)
        assert profile.recommended_domain_id is None

    def test_mapped_weak_dimension_recommends_the_real_content_backed_track(self) -> None:
        kwargs = _empty_kwargs()
        kwargs["latest_review"] = _performance_review(weakest_dimension_id="risk_discipline")
        profile = compute_agent_skill_profile("scout", **kwargs)
        assert profile.recommended_domain_id == "risk_management"
        assert profile.recommended_mentor_id == SKILL_DOMAIN_RECOMMENDED_MENTOR["risk_management"]
        assert profile.recommendation_reason is not None
        assert "Risk Discipline" in profile.recommendation_reason

    def test_already_graduated_track_yields_no_recommendation(self) -> None:
        kwargs = _empty_kwargs()
        kwargs["latest_review"] = _performance_review(weakest_dimension_id="risk_discipline")
        mentor_id = SKILL_DOMAIN_RECOMMENDED_MENTOR["risk_management"]
        kwargs["foundational_mentor_state"] = _mentor_state(
            progress={"scout": {mentor_id: FoundationalMentorProgress(mentorId=mentor_id, graduationStatus="graduated")}}  # type: ignore[arg-type]
        )
        profile = compute_agent_skill_profile("scout", **kwargs)
        assert profile.recommended_domain_id is None
        assert profile.recommended_mentor_id is None


class TestRecordAndLatest:
    def test_record_caps_the_list(self) -> None:
        profiles = []
        for i in range(5):
            kwargs = _empty_kwargs()
            kwargs["sim_day"] = i
            profile = compute_agent_skill_profile("scout", **kwargs)
            profiles = record_agent_skill_profile(profiles, profile, max_profiles=3)
        assert len(profiles) == 3

    def test_latest_skill_profile_for_agent_filters_correctly(self) -> None:
        profiles = []
        for agent_id, sim_day in [("scout", 1), ("nova", 2), ("scout", 3)]:
            kwargs = _empty_kwargs()
            kwargs["sim_day"] = sim_day
            profile = compute_agent_skill_profile(agent_id, **kwargs)  # type: ignore[arg-type]
            profiles.append(profile)
        latest = latest_skill_profile_for_agent(profiles, "scout")
        assert latest is not None
        assert latest.sim_day == 3

    def test_latest_returns_none_when_agent_has_no_profiles(self) -> None:
        assert latest_skill_profile_for_agent([], "scout") is None
