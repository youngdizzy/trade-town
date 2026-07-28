"""Covers app/executive_review.py — v0.7 Feature 24's CIO Monthly
Executive Review. Every field is a fresh cumulative snapshot over
already-real, already-computed state (research/decisions/debates/news),
the same convention app/coach.py's CoachReport already uses — nothing
here is randomized or fabricated.
"""
from __future__ import annotations

from app.executive_review import generate_executive_review
from app.schemas import (
    AcademyState,
    CompanyHealth,
    CompanyScore,
    Debate,
    DebateTurn,
    NewsItem,
    ResearchItem,
    RiskLimits,
    TimeState,
    TradeDecision,
)


def _now_iso() -> str:
    return "2026-01-01T00:00:00+00:00"


def _research(agent: str = "nova", status: str = "completed", confidence: float = 80.0, symbol: str = "AAPL") -> ResearchItem:
    return ResearchItem(
        id=f"r-{agent}-{symbol}",
        title="test",
        symbol=symbol,
        category="stock",
        priority="normal",
        status=status,  # type: ignore[arg-type]
        assignedAgent=agent,  # type: ignore[arg-type]
        summary="test",
        confidence=confidence,
        createdAt=_now_iso(),
        updatedAt=_now_iso(),
    )


def _decision(supporting: list[str], opposing: list[str]) -> TradeDecision:
    return TradeDecision(
        id="d1",
        symbol="AAPL",
        outcome="trade",
        votes=[],
        researchSummary="test",
        technicalSummary="test",
        fundamentalSummary="test",
        riskSummary="test",
        supportingAgents=supporting,  # type: ignore[arg-type]
        opposingAgents=opposing,  # type: ignore[arg-type]
        confidence=80.0,
        finalReasoning="test",
        orderId="order-1",
        createdAt=_now_iso(),
    )


def _debate(stances: list[str]) -> Debate:
    return Debate(
        id="debate-1",
        proposalId="proposal-1",
        symbol="AAPL",
        turns=[DebateTurn(agentId="echo", role="technical", stance=s, respondingTo=None, text="test") for s in stances],  # type: ignore[arg-type]
        finalRecommendation="buy",
        finalSummary="test",
        createdAt=_now_iso(),
    )


def _company_score(overall: float = 65.0) -> CompanyScore:
    return CompanyScore(
        overall=overall,
        researchQuality=60.0,
        decisionQuality=60.0,
        riskManagement=60.0,
        paperTradingPerformance=60.0,
        teamCoordination=60.0,
        knowledgeGrowth=60.0,
        simulationSuccess=60.0,
        updatedAt=_now_iso(),
    )


def _company_health(tier: str = "stable", recommendations: list[str] | None = None) -> CompanyHealth:
    return CompanyHealth(
        overall=60.0,
        tier=tier,  # type: ignore[arg-type]
        operationalStability=60.0,
        departmentEfficiency=60.0,
        employeeMorale=60.0,
        researchProgress=60.0,
        capitalHealth=60.0,
        resourceUsage=60.0,
        reputation=60.0,
        technologyLevel=60.0,
        officeExpansion=60.0,
        educationProgress=60.0,
        recommendations=recommendations or [],
        updatedAt=_now_iso(),
    )


def _academy_state(level: int = 2) -> AcademyState:
    return AcademyState(level=level, levelLabel="Research Library", totalPoints=50.0, completedProjectCount=5, updatedAt=_now_iso())


def _time() -> TimeState:
    return TimeState(day=30, hour=20, minute=0)


class TestGenerateExecutiveReview:
    def test_company_score_change_is_zero_with_no_previous_review(self) -> None:
        review = generate_executive_review(
            research=[], decisions=[], debates=[], news=[],
            company_score=_company_score(70.0), previous_score=None, company_health=_company_health(),
            risk_limits=RiskLimits(), academy_state=_academy_state(), completed_academy_projects=[],
            lessons_completed=0, agent_ids=("scout", "cio"), new_time=_time(),
        )
        assert review.company_score_change == 0.0

    def test_company_score_change_is_a_real_delta_against_the_previous_score(self) -> None:
        review = generate_executive_review(
            research=[], decisions=[], debates=[], news=[],
            company_score=_company_score(70.0), previous_score=60.0, company_health=_company_health(),
            risk_limits=RiskLimits(), academy_state=_academy_state(), completed_academy_projects=[],
            lessons_completed=0, agent_ids=("scout", "cio"), new_time=_time(),
        )
        assert review.company_score_change == 10.0

    def test_department_activity_only_lists_agents_with_real_activity(self) -> None:
        research = [_research(agent="nova", status="completed")]
        decisions = [_decision(supporting=["nova"], opposing=[])]
        review = generate_executive_review(
            research=research, decisions=decisions, debates=[], news=[],
            company_score=_company_score(), previous_score=None, company_health=_company_health(),
            risk_limits=RiskLimits(), academy_state=_academy_state(), completed_academy_projects=[],
            lessons_completed=0, agent_ids=("scout", "nova", "cio"), new_time=_time(),
        )
        agent_ids_in_activity = {a.agent_id for a in review.department_activity}
        assert agent_ids_in_activity == {"nova"}
        assert review.department_activity[0].research_completed == 1
        assert review.department_activity[0].decisions_involved == 1

    def test_research_completed_only_counts_completed_items(self) -> None:
        research = [_research(status="completed"), _research(status="in_progress", symbol="MSFT")]
        review = generate_executive_review(
            research=research, decisions=[], debates=[], news=[],
            company_score=_company_score(), previous_score=None, company_health=_company_health(),
            risk_limits=RiskLimits(), academy_state=_academy_state(), completed_academy_projects=[],
            lessons_completed=0, agent_ids=("nova",), new_time=_time(),
        )
        assert review.research_completed == 1

    def test_conflicts_detected_counts_only_challenge_stance_turns(self) -> None:
        debates = [_debate(["opening", "challenge", "support"]), _debate(["opening", "challenge"])]
        review = generate_executive_review(
            research=[], decisions=[], debates=debates, news=[],
            company_score=_company_score(), previous_score=None, company_health=_company_health(),
            risk_limits=RiskLimits(), academy_state=_academy_state(), completed_academy_projects=[],
            lessons_completed=0, agent_ids=("cio",), new_time=_time(),
        )
        assert review.conflicts_detected == 2

    def test_major_events_only_includes_company_and_discovery_news(self) -> None:
        news = [
            NewsItem(id="n1", headline="market thing", category="market", timestamp=_now_iso()),
            NewsItem(id="n2", headline="company thing", category="company", timestamp=_now_iso()),
            NewsItem(id="n3", headline="discovery thing", category="discovery", timestamp=_now_iso()),
        ]
        review = generate_executive_review(
            research=[], decisions=[], debates=[], news=news,
            company_score=_company_score(), previous_score=None, company_health=_company_health(),
            risk_limits=RiskLimits(), academy_state=_academy_state(), completed_academy_projects=[],
            lessons_completed=0, agent_ids=("cio",), new_time=_time(),
        )
        assert review.major_events == ["company thing", "discovery thing"]

    def test_flags_stalled_low_confidence_research(self) -> None:
        research = [_research(status="in_progress", confidence=5.0)]
        review = generate_executive_review(
            research=research, decisions=[], debates=[], news=[],
            company_score=_company_score(), previous_score=None, company_health=_company_health(),
            risk_limits=RiskLimits(), academy_state=_academy_state(), completed_academy_projects=[],
            lessons_completed=0, agent_ids=("nova",), new_time=_time(),
        )
        assert len(review.flags) == 1
        assert "nova" not in review.flags[0]  # names the display name, not the id
        assert "Nova" in review.flags[0]

    def test_flags_a_poor_company_health_tier(self) -> None:
        review = generate_executive_review(
            research=[], decisions=[], debates=[], news=[],
            company_score=_company_score(), previous_score=None, company_health=_company_health(tier="critical"),
            risk_limits=RiskLimits(), academy_state=_academy_state(), completed_academy_projects=[],
            lessons_completed=0, agent_ids=("cio",), new_time=_time(),
        )
        assert any("critical" in f for f in review.flags)

    def test_recommendations_are_reused_verbatim_from_company_health(self) -> None:
        review = generate_executive_review(
            research=[], decisions=[], debates=[], news=[],
            company_score=_company_score(), previous_score=None, company_health=_company_health(recommendations=["Fix X."]),
            risk_limits=RiskLimits(), academy_state=_academy_state(), completed_academy_projects=[],
            lessons_completed=0, agent_ids=("cio",), new_time=_time(),
        )
        assert review.recommendations == ["Fix X."]

    def test_long_term_goals_names_the_real_risk_limit(self) -> None:
        review = generate_executive_review(
            research=[], decisions=[], debates=[], news=[],
            company_score=_company_score(), previous_score=None, company_health=_company_health(),
            risk_limits=RiskLimits(maxDrawdownPct=15.0), academy_state=_academy_state(), completed_academy_projects=[],
            lessons_completed=0, agent_ids=("cio",), new_time=_time(),
        )
        assert any("15" in g for g in review.long_term_goals)

    def test_long_term_goals_drops_the_academy_goal_once_maxed(self) -> None:
        review = generate_executive_review(
            research=[], decisions=[], debates=[], news=[],
            company_score=_company_score(), previous_score=None, company_health=_company_health(),
            risk_limits=RiskLimits(), academy_state=_academy_state(level=5), completed_academy_projects=[],
            lessons_completed=0, agent_ids=("cio",), new_time=_time(),
        )
        assert len(review.long_term_goals) == 1

    def test_summary_names_the_real_company_score(self) -> None:
        review = generate_executive_review(
            research=[], decisions=[], debates=[], news=[],
            company_score=_company_score(72.0), previous_score=None, company_health=_company_health(),
            risk_limits=RiskLimits(), academy_state=_academy_state(), completed_academy_projects=[],
            lessons_completed=0, agent_ids=("cio",), new_time=_time(),
        )
        assert "72" in review.summary
