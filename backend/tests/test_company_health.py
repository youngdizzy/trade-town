"""Covers app/company_health.py — v0.7 Feature 23, the Company Health &
Stability System. Every sub-score reads a real, already-tracked signal
(agent location/mood, research completion, portfolio P&L, risk warnings,
AgentEnergy, HallOfFameEntry count, SignalCalibrationState's real level,
watchlist length beyond SEED_SYMBOLS, EducationProgress) — nothing here
is randomized or invented.
"""
from __future__ import annotations

from app.agents import all_agent_ids
from app.company_health import compute_company_health, diff_company_health
from app.debate import generate_debate
from app.education import all_lessons
from app.foundational_mentors import STUDENT_AGENT_IDS, default_foundational_mentor_state
from app.portfolio import default_portfolio
from app.schemas import (
    AgentEnergy,
    AgentKnowledgeState,
    AgentState,
    AnalystVote,
    CompanyHealth,
    Debate,
    DebateTurn,
    DecisionConfidence,
    DepartmentOpinion,
    DepartmentSelfEvaluation,
    DisciplineReview,
    EducationProgress,
    EntityTransform,
    ExecutiveDepartmentRole,
    ExecutiveMeetingLogEntry,
    FoundationalMentorProgress,
    FounderCouncilSession,
    InnovationState,
    PaperTrade,
    PostDecisionReview,
    ResearchItem,
    RiskWarning,
    SignalCalibrationState,
    Strategy,
    StrategyHealthAssessment,
    TradeDecision,
    TradeProposal,
    WatchlistEntry,
    WisdomState,
)
from app.signal_calibration import MAX_LEVEL as SIGNAL_MAX_LEVEL
from app.watchlist import SEED_SYMBOLS, default_watchlist

_ALL_ROLES: tuple[ExecutiveDepartmentRole, ...] = ("research", "quant", "risk", "simulation", "decision_intelligence", "coach", "founders", "devils_advocate")


def _strong_trade_history() -> list[PaperTrade]:
    """Real closed trades with no matching gatekeeper rejections, so
    `_risk_governance` reads a clean 100% approval rate."""
    return [
        PaperTrade(
            id=f"t{i}",
            symbol="AAPL",
            side="buy",
            quantity=1.0,
            entryPrice=100.0,
            exitPrice=105.0,
            pnl=5.0,
            pnlPct=5.0,
            durationMinutes=60,
            confidence=90.0,
            reason="x",
            marketConditions="x",
            openedAt="2026-01-01T00:00:00+00:00",
            closedAt="2026-01-01T01:00:00+00:00",
        )
        for i in range(5)
    ]


def _strong_executive_overrides() -> dict:
    """Every real Executive-tier input maxed out, mirroring `_health`'s
    own "everything strong" convention for the Operational tier below —
    used by TestOverallAndTier's combined "nothing to recommend" test."""
    opinions = [DepartmentOpinion(role=role, departmentLabel=role, stance="agree", summary="x", confidencePct=95.0) for role in _ALL_ROLES]
    meeting_log = [
        ExecutiveMeetingLogEntry(
            id=f"m{i}",
            proposalId=f"p{i}",
            symbol="AAPL",
            simDay=i,
            opinions=opinions,
            recommendedAction="trade_normally",
            recommendationReason="x",
            ceoDecision="buy",
            networkAgreed=True,
            decisionGrade="A+",
            decisionGradeScore=98.0,
            resolvedBy="ceo",
            createdAt="2026-01-01T00:00:00+00:00",
        )
        for i in range(5)
    ]
    decisions = [
        TradeDecision(
            id=f"d{i}",
            symbol="AAPL",
            outcome="trade",
            votes=[],
            researchSummary="x",
            technicalSummary="x",
            fundamentalSummary="x",
            riskSummary="x",
            supportingAgents=[],
            opposingAgents=[],
            confidence=90.0,
            finalReasoning="x",
            orderId=None,
            decisionGrade="A+",
            decisionGradeScore=98.0,
            createdAt="2026-01-01T00:00:00+00:00",
        )
        for i in range(5)
    ]
    self_evaluations = [
        DepartmentSelfEvaluation(
            id=f"s-{role}",
            role=role,
            departmentLabel=role,
            weekEndingSimDay=7,
            decisionsReviewed=5,
            score=95.0,
            summary="x",
            strengths=["x"],
            improvementAreas=[],
            createdAt="2026-01-01T00:00:00+00:00",
        )
        for role in _ALL_ROLES
    ]
    # v0.7 Feature 51 added market_intelligence, and Trading Psychology &
    # Discipline Piece F added mark_douglas/linda_raschke, as real active
    # tracks by default, so talent_development's real denominator now
    # spans all four — every real active track needs a real graduated
    # student here too, or talent_development would drag this "nothing
    # to recommend" fixture below the recommendation threshold.
    #
    # CEO Company/Executive Health directive, Phase 3 — talent_development
    # now also reads real post-graduation DisciplineReview performance
    # (see app/company_health.py's _talent_development()), so a genuinely
    # "everything maxed" fixture needs a real graduatedSimDay plus real
    # strong post-graduation reviews for every graduated student, not just
    # the graduation badge itself.
    graduated_by_mentor = {
        mentor_id: FoundationalMentorProgress(mentorId=mentor_id, graduationStatus="graduated", graduatedSimDay=1)  # type: ignore[call-arg]
        for mentor_id in ("tjr", "market_intelligence", "mark_douglas", "linda_raschke")
    }
    fm_state = default_foundational_mentor_state().model_copy(
        update={"progress": {agent_id: dict(graduated_by_mentor) for agent_id in STUDENT_AGENT_IDS}}
    )
    strong_post_graduation_reviews = [
        DisciplineReview(
            id=f"post-grad-{agent_id}",
            decisionId=f"d-post-grad-{agent_id}",
            symbol="AAPL",
            score=95.0,
            tier="exemplary",
            attendees=[agent_id],
            summary="x",
            postDecisionReview=PostDecisionReview(),
            outcome="win",
            tradePnlPct=5.0,
            holdDurationMinutes=60,
            simDay=10,
            createdAt="2026-01-10T00:00:00+00:00",
        )
        for agent_id in STUDENT_AGENT_IDS
    ]
    # CEO Company/Executive Health directive, Phase 5 — self_evaluation_health
    # now also reads a real calibration TREND across discipline_reviews
    # (earlier-half vs later-half misalignment rate). "cio" is not a real
    # student (STUDENT_AGENT_IDS), so these earlier, deliberately
    # misaligned reviews affect only that trend, never talent_development's
    # own post-graduation performance reading above. Placed first in the
    # list (list order, not simDay, is what earlier/later means here — the
    # same real-tick-append-order convention nexus.py's own discipline_reviews
    # list already follows) so the real trend reads a full misaligned ->
    # aligned improvement, maxing calibration_trend at 100.
    earlier_misaligned_reviews = [
        DisciplineReview(
            id=f"early-{i}",
            decisionId=f"d-early-{i}",
            symbol="AAPL",
            score=95.0,
            tier="exemplary",
            attendees=["cio"],
            summary="x",
            postDecisionReview=PostDecisionReview(),
            outcome="loss",
            tradePnlPct=-2.0,
            holdDurationMinutes=60,
            simDay=1,
            createdAt="2026-01-01T00:00:00+00:00",
        )
        for i in range(len(STUDENT_AGENT_IDS))
    ]
    # CEO Company/Executive Health directive, Phase 6 — decision_quality's
    # own real calibration component needs each of the five real
    # decisions above to have a matching, agreeing DisciplineReview, or
    # this "everything maxed" fixture would honestly (and correctly)
    # read a lower decision_quality than a genuinely fully-calibrated
    # company would.
    matching_calibration_reviews = [
        DisciplineReview(
            id=f"calib-{i}",
            decisionId=f"d{i}",
            symbol="AAPL",
            score=99.0,
            tier="exemplary",
            attendees=["scout"],
            summary="x",
            postDecisionReview=PostDecisionReview(),
            outcome="win",
            tradePnlPct=5.0,
            holdDurationMinutes=60,
            simDay=1,
            createdAt="2026-01-01T00:00:00+00:00",
        )
        for i in range(5)
    ]
    all_discipline_reviews = earlier_misaligned_reviews + strong_post_graduation_reviews + matching_calibration_reviews
    founder_council_sessions = [
        FounderCouncilSession(id=f"c{i}", simDay=i, coachHighlight="x", keystoneNote="x", compassNote="x", createdAt="2026-01-01T00:00:00+00:00") for i in range(5)
    ]
    # CEO Company/Executive Health directive, Phase "Institutional
    # Memory" — institutional_memory now also reads real per-agent
    # Academy mastery (app/academy.py's is_mentor_level()), so every
    # real agent needs to have actually reached the real top "mentor"
    # KnowledgeLevel here, not just a high WisdomState.score.
    agent_knowledge = {
        agent_id: AgentKnowledgeState(agentId=agent_id, branch="x", points=100.0, tier=6, level="mentor") for agent_id in all_agent_ids()
    }
    # CEO Company/Executive Health directive, Phase "Innovation
    # Velocity" — innovation_velocity now also reads real Strategy Lab
    # pipeline depth and real post-deployment StrategyHealthAssessment
    # trends, so this fixture needs real strategies that have actually
    # reached the real furthest "approved" stage with a real "improving"
    # health read, not just Devil's Advocate points.
    strong_strategies = [
        Strategy(id=f"strong-strategy-{i}", name=f"Strategy {i}", description="x", createdBy="scout", focusCategory="stock", createdAt="2026-01-01T00:00:00+00:00", stage="approved")
        for i in range(3)
    ]
    strong_strategy_health_assessments = [
        StrategyHealthAssessment(
            id=f"health-{s.id}",
            strategyId=s.id,
            strategyName=s.name,
            status="excellent",
            trend="improving",
            recentWinRate=90.0,
            lifetimeWinRate=80.0,
            recentAvgReturnPct=6.0,
            lifetimeAvgReturnPct=3.0,
            recentAvgDrawdownPct=2.0,
            lifetimeAvgDrawdownPct=3.0,
            recentSampleSize=5,
            lifetimeSampleSize=10,
            reasoning=["x"],
            simDay=10,
            createdAt="2026-01-10T00:00:00+00:00",
        )
        for s in strong_strategies
    ]
    return dict(
        decisions=decisions,
        meeting_log=meeting_log,
        self_evaluations=self_evaluations,
        wisdom_state=WisdomState(score=95.0, tier="enduring_wisdom", tierLabel="Enduring Wisdom", factors=[], updatedAt="2026-01-01T00:00:00+00:00"),
        innovation_state={"scout": InnovationState(agentId="scout", points=35.0, tier=4, tierName="legendary_innovator")},
        foundational_mentor_state=fm_state,
        founder_council_sessions=founder_council_sessions,
        gatekeeper_rejections=[],
        discipline_reviews=all_discipline_reviews,
        agent_knowledge=agent_knowledge,
        strategies=strong_strategies,
        strategy_health_assessments=strong_strategy_health_assessments,
    )


def _agent(location: str = "brain-room", mood: float = 70.0) -> AgentState:
    return AgentState(
        transform=EntityTransform(scene="LobbyScene", x=0, y=0, facing="down"),
        location=location,  # type: ignore[arg-type]
        currentTask="working",
        mood=mood,
        energy=80.0,
    )


def _research(status: str = "completed") -> ResearchItem:
    return ResearchItem(
        id="r1",
        title="test",
        symbol="AAPL",
        category="stock",
        priority="normal",
        status=status,  # type: ignore[arg-type]
        assignedAgent="nova",
        summary="test",
        confidence=80.0,
        createdAt="2026-01-01T00:00:00+00:00",
        updatedAt="2026-01-01T00:00:00+00:00",
    )


def _health(**overrides):
    defaults = dict(
        agents={"nova": _agent()},
        research=[_research()],
        portfolio=default_portfolio(),
        risk_warnings=[],
        agent_energy=AgentEnergy(current=100.0, cap=100.0, updatedAt="2026-01-01T00:00:00+00:00"),
        hall_of_fame=[],
        signal_calibration=SignalCalibrationState(),
        watchlist=default_watchlist(),
        education=EducationProgress(),
        debates=[],
        decisions=[],
        meeting_log=[],
        self_evaluations=[],
        wisdom_state=WisdomState(score=50.0, tier="young_company", tierLabel="Young Company", factors=[], updatedAt="2026-01-01T00:00:00+00:00"),
        innovation_state={},
        foundational_mentor_state=default_foundational_mentor_state(),
        founder_council_sessions=[],
        gatekeeper_rejections=[],
        discipline_reviews=[],
        agent_knowledge={},
        strategies=[],
        strategy_health_assessments=[],
    )
    defaults.update(overrides)
    return compute_company_health(**defaults)


def _ch(**overrides) -> CompanyHealth:
    """A full, directly-constructed CompanyHealth reading for
    diff_company_health() tests — bypasses compute_company_health()
    entirely so each test can isolate exactly one real before/after
    change without needing to fabricate the raw inputs that would
    produce it."""
    defaults: dict = dict(
        overall=70.0,
        tier="good",
        operationalStability=70.0,
        departmentEfficiency=70.0,
        employeeMorale=70.0,
        researchProgress=70.0,
        capitalHealth=70.0,
        resourceUsage=70.0,
        reputation=70.0,
        technologyLevel=70.0,
        marketCoverage=70.0,
        educationProgress=70.0,
        teamChemistry=70.0,
        updatedAt="2026-01-01T00:00:00+00:00",
        decisionQuality=70.0,
        executiveAlignment=70.0,
        riskGovernance=70.0,
        simulationCoverage=70.0,
        departmentConsensus=70.0,
        selfEvaluationHealth=70.0,
        institutionalMemory=70.0,
        innovationVelocity=70.0,
        talentDevelopment=70.0,
        founderOversight=70.0,
        executiveOverall=70.0,
        executiveTier="good",
        combinedOverall=70.0,
        combinedTier="good",
    )
    defaults.update(overrides)
    return CompanyHealth(**defaults)


class TestOperationalStability:
    def test_no_warnings_is_a_perfect_score(self) -> None:
        health = _health(risk_warnings=[])
        assert health.operational_stability == 100.0

    def test_critical_warnings_penalize_more_than_info(self) -> None:
        critical = _health(risk_warnings=[RiskWarning(id="w1", symbol="AAPL", severity="critical", message="x", createdAt="2026-01-01T00:00:00+00:00")])
        info = _health(risk_warnings=[RiskWarning(id="w2", symbol="AAPL", severity="info", message="x", createdAt="2026-01-01T00:00:00+00:00")])
        assert critical.operational_stability < info.operational_stability


class TestDepartmentEfficiencyAndMorale:
    def test_all_agents_working_is_full_efficiency(self) -> None:
        health = _health(agents={"nova": _agent("brain-room"), "echo": _agent("trading-floor")})
        assert health.department_efficiency == 100.0

    def test_all_agents_resting_is_zero_efficiency(self) -> None:
        health = _health(agents={"nova": _agent("lobby"), "echo": _agent("break-room")})
        assert health.department_efficiency == 0.0

    def test_morale_reflects_the_real_average_mood(self) -> None:
        health = _health(agents={"nova": _agent(mood=40.0), "echo": _agent(mood=60.0)})
        assert health.employee_morale == 50.0


class TestResearchProgress:
    def test_all_completed_is_full_progress(self) -> None:
        health = _health(research=[_research("completed"), _research("completed")])
        assert health.research_progress == 100.0

    def test_none_completed_is_zero_progress(self) -> None:
        health = _health(research=[_research("in_progress"), _research("queued")])
        assert health.research_progress == 0.0


class TestCapitalHealth:
    def test_profitable_portfolio_scores_above_fifty(self) -> None:
        portfolio = default_portfolio().model_copy(update={"total_pnl_pct": 10.0})
        health = _health(portfolio=portfolio)
        assert health.capital_health > 50.0

    def test_losing_portfolio_scores_below_fifty(self) -> None:
        portfolio = default_portfolio().model_copy(update={"total_pnl_pct": -10.0})
        health = _health(portfolio=portfolio)
        assert health.capital_health < 50.0


class TestResourceUsage:
    def test_full_energy_pool_is_full_score(self) -> None:
        health = _health(agent_energy=AgentEnergy(current=100.0, cap=100.0, updatedAt="2026-01-01T00:00:00+00:00"))
        assert health.resource_usage == 100.0

    def test_depleted_energy_pool_is_zero_score(self) -> None:
        health = _health(agent_energy=AgentEnergy(current=0.0, cap=100.0, updatedAt="2026-01-01T00:00:00+00:00"))
        assert health.resource_usage == 0.0


class TestReputation:
    def test_no_hall_of_fame_entries_is_zero(self) -> None:
        health = _health(hall_of_fame=[])
        assert health.reputation == 0.0

    def test_more_entries_scores_higher(self) -> None:
        from app.schemas import HallOfFameEntry

        entries = [HallOfFameEntry(id=f"h{i}", category="best_research", title="x", description="x", value=1.0, achievedAt="2026-01-01T00:00:00+00:00") for i in range(3)]
        health = _health(hall_of_fame=entries)
        assert health.reputation > 0.0


class TestTechnologyLevel:
    def test_unlocked_level_one_is_zero(self) -> None:
        health = _health(signal_calibration=SignalCalibrationState(unlockedLevel=1))
        assert health.technology_level == 0.0

    def test_max_unlocked_level_is_full(self) -> None:
        health = _health(signal_calibration=SignalCalibrationState(unlockedLevel=SIGNAL_MAX_LEVEL))
        assert health.technology_level == 100.0


class TestMarketCoverage:
    """CEO Company/Executive Health directive — renamed from
    TestOfficeExpansion/office_expansion. Same real formula (real extra
    watchlist symbols beyond SEED_SYMBOLS), honest new name — see
    app/company_health.py's _market_coverage() docstring."""

    def test_seed_watchlist_only_is_zero_coverage(self) -> None:
        health = _health(watchlist=default_watchlist())
        assert health.market_coverage == 0.0

    def test_added_symbols_increase_coverage(self) -> None:
        extra = WatchlistEntry(symbol="AMZN", name="Amazon", lastPrice=100.0, dailyChangePct=0.0, status="queued", researchProgress=0.0, assignedAgent=None)
        watchlist = [*default_watchlist(), extra]
        health = _health(watchlist=watchlist)
        assert health.market_coverage > 0.0
        assert len(default_watchlist()) == len(SEED_SYMBOLS)


class TestEducationProgress:
    def test_no_completed_lessons_and_no_quiz_attempts_reads_the_blended_neutral_default(self) -> None:
        """CEO Company/Executive Health directive — education_progress is
        now an equal blend of real completion share and real quiz
        accuracy. A brand-new player has 0% completion (real) blended
        with a neutral 50.0 accuracy (no real quiz attempted yet, not a
        fabricated zero) = 25.0, not the old formula's flat 0.0."""
        health = _health(education=EducationProgress())
        assert health.education_progress == 25.0

    def test_full_completion_with_perfect_accuracy_is_a_perfect_score(self) -> None:
        from app.education import all_lessons

        lesson_ids = [lesson.id for lesson in all_lessons()]
        health = _health(
            education=EducationProgress(
                completedLessonIds=lesson_ids,
                quizAttempts=len(lesson_ids),
                correctQuizAttempts=len(lesson_ids),
            )
        )
        assert health.education_progress == 100.0

    def test_quiz_accuracy_rewards_getting_it_right_without_wrong_guesses(self) -> None:
        """Two players who have both completed every real lesson
        (identical `completed_lesson_ids`) are told apart by their real
        quiz accuracy — the one who needed several wrong real attempts to
        land on the same completed set scores lower."""
        from app.education import all_lessons

        lesson_ids = [lesson.id for lesson in all_lessons()]
        first_try = _health(
            education=EducationProgress(
                completedLessonIds=lesson_ids,
                quizAttempts=len(lesson_ids),
                correctQuizAttempts=len(lesson_ids),
            )
        )
        several_wrong_guesses = _health(
            education=EducationProgress(
                completedLessonIds=lesson_ids,
                quizAttempts=len(lesson_ids) * 3,
                correctQuizAttempts=len(lesson_ids),
            )
        )
        assert first_try.education_progress > several_wrong_guesses.education_progress


class TestOverallAndTier:
    def test_overall_is_the_mean_of_the_eleven_metrics(self) -> None:
        health = _health()
        metrics = [
            health.operational_stability,
            health.department_efficiency,
            health.employee_morale,
            health.research_progress,
            health.capital_health,
            health.resource_usage,
            health.reputation,
            health.technology_level,
            health.market_coverage,
            health.education_progress,
            health.team_chemistry,
        ]
        assert health.overall == round(sum(metrics) / len(metrics), 1)

    def test_tier_labels_a_low_overall_as_critical(self) -> None:
        health = _health(
            agents={"nova": _agent("lobby", mood=0.0)},
            research=[_research("in_progress")],
            risk_warnings=[RiskWarning(id="w1", symbol="AAPL", severity="critical", message="x", createdAt="2026-01-01T00:00:00+00:00")],
            agent_energy=AgentEnergy(current=0.0, cap=100.0, updatedAt="2026-01-01T00:00:00+00:00"),
            portfolio=default_portfolio().model_copy(update={"total_pnl_pct": -50.0}),
        )
        assert health.tier in ("critical", "needs_attention")

    def test_recommendations_name_the_real_weakest_metrics(self) -> None:
        health = _health(
            agents={"nova": _agent("lobby", mood=0.0)},
            agent_energy=AgentEnergy(current=0.0, cap=100.0, updatedAt="2026-01-01T00:00:00+00:00"),
        )
        assert len(health.recommendations) >= 1
        assert any("Resource Usage" in r or "Employee Morale" in r or "Department Efficiency" in r or "Technology Level" in r or "Market Coverage" in r or "Education Progress" in r for r in health.recommendations)

    def test_no_recommendations_when_every_metric_is_already_strong(self) -> None:
        from app.schemas import HallOfFameEntry

        health = _health(
            hall_of_fame=[HallOfFameEntry(id=f"h{i}", category="best_research", title="x", description="x", value=1.0, achievedAt="2026-01-01T00:00:00+00:00") for i in range(30)],
            signal_calibration=SignalCalibrationState(unlockedLevel=SIGNAL_MAX_LEVEL),
            education=EducationProgress(completedLessonIds=[lesson.id for lesson in all_lessons()]),
            watchlist=[*default_watchlist(), *(WatchlistEntry(symbol=s, name=s, lastPrice=1.0, dailyChangePct=0.0, status="queued", researchProgress=0.0, assignedAgent=None) for s in ["AMZN", "GOOGL", "TSLA", "NVDA", "SLV", "USO"])],
            portfolio=default_portfolio().model_copy(update={"total_pnl_pct": 40.0, "trade_history": _strong_trade_history()}),
            debates=[_all_supportive_debate()],
            **_strong_executive_overrides(),
        )
        assert health.recommendations == []


def _research_at(agent: str, category: str, updated_at: str, item_id: str) -> ResearchItem:
    return ResearchItem(
        id=item_id,
        title="test",
        symbol="AAPL",
        category=category,  # type: ignore[arg-type]
        priority="normal",
        status="completed",  # type: ignore[arg-type]
        assignedAgent=agent,  # type: ignore[arg-type]
        summary="test",
        confidence=80.0,
        createdAt=updated_at,
        updatedAt=updated_at,
    )


class TestTeamChemistry:
    """Team Chemistry is an equal mean of two real signals — see
    app/company_health.py's _team_chemistry()/_debate_collaboration_quality()/
    _cross_agent_research_handoffs(). Both default to the neutral 50.0
    _health()'s own defaults produce (debates=[], and the single default
    `research=[_research()]` has no same-category pair to check), so
    every test below overrides both signals' real inputs explicitly to
    isolate what it's testing."""

    def test_no_data_at_all_reads_neutral(self) -> None:
        health = _health(debates=[], research=[])
        assert health.team_chemistry == 50.0

    def test_fully_supportive_debates_and_real_handoffs_score_high(self) -> None:
        health = _health(
            debates=[_all_supportive_debate()],
            research=[_research_at("nova", "stock", "2026-01-01T00:00:00+00:00", "r1"), _research_at("echo", "stock", "2026-01-02T00:00:00+00:00", "r2")],
        )
        assert health.team_chemistry == 100.0

    def test_fully_adversarial_debates_and_isolated_research_score_low(self) -> None:
        # Under the fixed app/debate.py logic, a genuinely all-challenge
        # debate only occurs when every analyst's vote opposes the
        # desk's own final recommendation (not merely "someone
        # disagreed with someone") — a real full-desk override.
        debate = Debate(
            id="d1",
            proposalId="p1",
            symbol="AAPL",
            turns=[
                DebateTurn(agentId="echo", role="technical", stance="opening", respondingTo=None, text="x"),  # type: ignore[arg-type]
                DebateTurn(agentId="scout", role="news", stance="challenge", respondingTo="echo", text="x"),  # type: ignore[arg-type]
                DebateTurn(agentId="nova", role="macro", stance="challenge", respondingTo="echo", text="x"),  # type: ignore[arg-type]
            ],
            finalRecommendation="wait",
            finalSummary="x",
            createdAt="2026-01-01T00:00:00+00:00",
        )
        health = _health(
            debates=[debate],
            # Same agent worked both items in the same category — no
            # real cross-agent handoff occurred.
            research=[_research_at("nova", "stock", "2026-01-01T00:00:00+00:00", "r1"), _research_at("nova", "stock", "2026-01-02T00:00:00+00:00", "r2")],
        )
        assert health.team_chemistry == 0.0

    def test_only_the_most_recent_window_of_debates_counts(self) -> None:
        # 19 challenge-only debates followed by 1 fully supportive one —
        # only the most recent TEAM_CHEMISTRY_WINDOW (20) debates count,
        # and the supportive one alone tips the ratio, so this stays
        # well below a clean 100 (proving old debates aren't discarded
        # entirely) but should read distinctly higher than a run of pure
        # challenge debates would.
        challenge_debate = Debate(
            id="d-challenge",
            proposalId="p1",
            symbol="AAPL",
            turns=[
                DebateTurn(agentId="echo", role="technical", stance="opening", respondingTo=None, text="x"),  # type: ignore[arg-type]
                DebateTurn(agentId="scout", role="news", stance="challenge", respondingTo="echo", text="x"),  # type: ignore[arg-type]
            ],
            finalRecommendation="wait",
            finalSummary="x",
            createdAt="2026-01-01T00:00:00+00:00",
        )
        health = _health(debates=[*(challenge_debate for _ in range(19)), _all_supportive_debate()], research=[])
        assert 0.0 < health.team_chemistry < 100.0

    def test_a_real_minority_dissent_is_not_scored_as_total_conflict(self) -> None:
        """The exact anti-pattern the CEO's directive named: a debate
        with real, healthy minority disagreement (2 of 6 analysts
        dissent from the desk's own final call) must NOT collapse Team
        Chemistry to 0 just because disagreement exists somewhere —
        only the real dissenters get a challenge turn, the real
        majority still gets credited for backing the desk."""
        votes = [
            AnalystVote(role=role, agentId=agent, choice=choice, reasoning=f"{role} reasoning", evidence=["e"])  # type: ignore[arg-type]
            for role, agent, choice in [
                ("technical", "echo", "buy"),
                ("news", "scout", "buy"),
                ("macro", "nova", "buy"),
                ("risk", "sentinel", "buy"),
                ("sentiment", "pulse", "sell"),
                ("execution", "atlas", "sell"),
            ]
        ]
        proposal = TradeProposal(
            id="p1",
            symbol="AAPL",
            category="stock",
            quantity=10.0,
            price=100.0,
            confidence=80.0,
            analystVotes=votes,  # type: ignore[arg-type]
            overallRecommendation="buy",  # type: ignore[arg-type]
            researchSummary="x",
            riskSummary="x",
            confidenceEngine=DecisionConfidence(score=80.0, tier="strong", summary="x", factors=[]),
            createdAt="2026-01-01T00:00:00+00:00",
            createdSimMinutes=0,
        )
        debate = generate_debate(proposal)
        cross = [t for t in debate.turns if t.stance != "opening"]
        assert sum(1 for t in cross if t.stance == "support") == 4
        assert sum(1 for t in cross if t.stance == "challenge") == 2
        health = _health(debates=[debate], research=[])
        # debate signal = 4/6 support = 66.7; research signal (empty) = 50 neutral
        assert health.team_chemistry == round((4 / 6 * 100.0 + 50.0) / 2.0, 1)


class TestCrossAgentResearchHandoffs:
    def test_no_completed_research_reads_neutral(self) -> None:
        health = _health(debates=[], research=[])
        assert health.team_chemistry == 50.0

    def test_single_item_per_category_has_no_pair_to_check(self) -> None:
        health = _health(debates=[], research=[_research_at("nova", "stock", "2026-01-01T00:00:00+00:00", "r1")])
        assert health.team_chemistry == 50.0

    def test_different_agents_in_the_same_category_is_a_real_handoff(self) -> None:
        health = _health(
            debates=[],
            research=[_research_at("nova", "stock", "2026-01-01T00:00:00+00:00", "r1"), _research_at("echo", "stock", "2026-01-02T00:00:00+00:00", "r2")],
        )
        # debate signal (no debates) = 50 neutral; handoff signal = 100 (1/1 pairs crossed agents)
        assert health.team_chemistry == 75.0

    def test_same_agent_working_a_category_alone_is_not_a_handoff(self) -> None:
        health = _health(
            debates=[],
            research=[_research_at("nova", "stock", "2026-01-01T00:00:00+00:00", "r1"), _research_at("nova", "stock", "2026-01-02T00:00:00+00:00", "r2")],
        )
        assert health.team_chemistry == 25.0

    def test_in_progress_research_is_not_counted(self) -> None:
        item = _research_at("nova", "stock", "2026-01-01T00:00:00+00:00", "r1").model_copy(update={"status": "in_progress"})
        health = _health(debates=[], research=[item, _research_at("echo", "stock", "2026-01-02T00:00:00+00:00", "r2")])
        assert health.team_chemistry == 50.0  # only one real completed item — no pair yet

    def test_different_categories_never_form_a_pair(self) -> None:
        health = _health(
            debates=[],
            research=[_research_at("nova", "stock", "2026-01-01T00:00:00+00:00", "r1"), _research_at("echo", "bitcoin", "2026-01-02T00:00:00+00:00", "r2")],
        )
        assert health.team_chemistry == 50.0


def _all_supportive_debate() -> Debate:
    return Debate(
        id="d-supportive",
        proposalId="p1",
        symbol="AAPL",
        turns=[
            DebateTurn(agentId="echo", role="technical", stance="opening", respondingTo=None, text="x"),  # type: ignore[arg-type]
            DebateTurn(agentId="scout", role="news", stance="support", respondingTo="echo", text="x"),  # type: ignore[arg-type]
            DebateTurn(agentId="nova", role="macro", stance="support", respondingTo="echo", text="x"),  # type: ignore[arg-type]
        ],
        finalRecommendation="buy",
        finalSummary="x",
        createdAt="2026-01-01T00:00:00+00:00",
    )


class TestExecutiveTier:
    """v0.7 Feature 50 (Part 2/3) — the ten new Executive-tier dimensions,
    additive alongside the eleven Operational ones covered above."""

    def test_defaults_to_neutral_fifty_with_no_executive_data_yet(self) -> None:
        health = _health()
        assert health.decision_quality == 50.0
        assert health.executive_alignment == 50.0
        assert health.department_consensus == 50.0
        assert health.self_evaluation_health == 50.0
        # CEO Company/Executive Health directive — institutional_memory is
        # now an equal blend of WisdomState.score (50.0 neutral default)
        # and real per-agent Academy mastery (0.0 — no agent_knowledge on
        # record yet), not a pure WisdomState.score passthrough.
        assert health.institutional_memory == 25.0
        assert health.talent_development == 0.0  # no active mentor track has any graduate yet
        assert health.simulation_coverage == 0.0  # honestly "no coverage" rather than neutral
        assert health.innovation_velocity == 0.0
        assert health.founder_oversight == 0.0

    def test_decision_quality_averages_recent_real_decision_grades(self) -> None:
        decisions = [
            TradeDecision(
                id=f"d{i}",
                symbol="AAPL",
                outcome="trade",
                researchSummary="x",
                technicalSummary="x",
                fundamentalSummary="x",
                riskSummary="x",
                confidence=90.0,
                finalReasoning="x",
                decisionGrade="A+",
                decisionGradeScore=score,
                createdAt="2026-01-01T00:00:00+00:00",
            )
            for i, score in enumerate([80.0, 90.0])
        ]
        health = _health(decisions=decisions)
        # CEO Company/Executive Health directive, Phase 6 — base (the
        # real average decision_grade_score, unchanged) is now blended
        # with a real calibration component. With no discipline_reviews
        # here, calibration reads its own honest neutral 50.0.
        assert health.decision_quality == 67.5

    def test_decision_quality_rewards_agreement_with_the_later_independent_discipline_review(self) -> None:
        """CEO Company/Executive Health directive, Phase 6 — the exact
        calibration chain: a decision graded highly at decision time
        whose later, fully independent Discipline Review (never reading
        the same inputs, never reading pnl either) lands on a matching
        real score demonstrates the initial grade was genuinely
        calibrated, not merely optimistic."""
        decision = TradeDecision(
            id="d1", symbol="AAPL", outcome="trade", researchSummary="x", technicalSummary="x", fundamentalSummary="x", riskSummary="x",
            confidence=90.0, finalReasoning="x", decisionGrade="A+", decisionGradeScore=90.0, createdAt="2026-01-01T00:00:00+00:00",
        )
        matching_review = DisciplineReview(
            id="r1", decisionId="d1", symbol="AAPL", score=90.0, tier="exemplary", attendees=["scout"], summary="x",
            postDecisionReview=PostDecisionReview(), outcome="win", tradePnlPct=3.0, holdDurationMinutes=60, simDay=1, createdAt="2026-01-01T00:00:00+00:00",
        )
        health = _health(decisions=[decision], discipline_reviews=[matching_review])
        # base = 90.0; calibration = 100 - |90-90| = 100. (90+100)/2 = 95.0.
        assert health.decision_quality == 95.0

    def test_decision_quality_penalizes_a_grade_that_disagrees_with_the_later_review(self) -> None:
        decision = TradeDecision(
            id="d1", symbol="AAPL", outcome="trade", researchSummary="x", technicalSummary="x", fundamentalSummary="x", riskSummary="x",
            confidence=90.0, finalReasoning="x", decisionGrade="A+", decisionGradeScore=95.0, createdAt="2026-01-01T00:00:00+00:00",
        )
        disagreeing_review = DisciplineReview(
            id="r1", decisionId="d1", symbol="AAPL", score=25.0, tier="weak", attendees=["scout"], summary="x",
            postDecisionReview=PostDecisionReview(), outcome="loss", tradePnlPct=-3.0, holdDurationMinutes=60, simDay=1, createdAt="2026-01-01T00:00:00+00:00",
        )
        health = _health(decisions=[decision], discipline_reviews=[disagreeing_review])
        # base = 95.0; calibration = 100 - |95-25| = 30. (95+30)/2 = 62.5.
        assert health.decision_quality == 62.5

    def test_decision_quality_only_compares_a_decisions_own_real_review(self) -> None:
        """A Discipline Review for an unrelated decision must never be
        used to calibrate this one."""
        decision = TradeDecision(
            id="d1", symbol="AAPL", outcome="trade", researchSummary="x", technicalSummary="x", fundamentalSummary="x", riskSummary="x",
            confidence=90.0, finalReasoning="x", decisionGrade="A+", decisionGradeScore=90.0, createdAt="2026-01-01T00:00:00+00:00",
        )
        unrelated_review = DisciplineReview(
            id="r1", decisionId="d999", symbol="AAPL", score=10.0, tier="reckless", attendees=["scout"], summary="x",
            postDecisionReview=PostDecisionReview(), outcome="loss", tradePnlPct=-3.0, holdDurationMinutes=60, simDay=1, createdAt="2026-01-01T00:00:00+00:00",
        )
        health = _health(decisions=[decision], discipline_reviews=[unrelated_review])
        # No real matching review -> calibration stays neutral 50.
        assert health.decision_quality == 70.0

    def test_executive_alignment_reads_the_real_network_agreed_flag(self) -> None:
        opinions = [DepartmentOpinion(role=role, departmentLabel=role, stance="agree", summary="x", confidencePct=90.0) for role in _ALL_ROLES]
        agreeing = ExecutiveMeetingLogEntry(
            id="m1", proposalId="p1", symbol="AAPL", simDay=1, opinions=opinions, recommendedAction="trade_normally", recommendationReason="x",
            ceoDecision="buy", networkAgreed=True, decisionGrade="A", decisionGradeScore=90.0, resolvedBy="ceo", createdAt="2026-01-01T00:00:00+00:00",
        )
        disagreeing = agreeing.model_copy(update={"id": "m2", "network_agreed": False})
        health = _health(meeting_log=[agreeing, disagreeing])
        assert health.executive_alignment == 50.0

    def test_simulation_coverage_counts_real_stress_tested_decisions(self) -> None:
        stress_tested = [DepartmentOpinion(role="simulation", departmentLabel="Simulation", stance="agree", summary="x", confidencePct=80.0)]
        not_yet = [DepartmentOpinion(role="simulation", departmentLabel="Simulation", stance="request_more_research", summary="x", confidencePct=50.0)]
        covered = ExecutiveMeetingLogEntry(
            id="m1", proposalId="p1", symbol="AAPL", simDay=1, opinions=stress_tested, recommendedAction="trade_normally", recommendationReason="x",
            ceoDecision="buy", networkAgreed=True, decisionGrade="A", decisionGradeScore=90.0, resolvedBy="ceo", createdAt="2026-01-01T00:00:00+00:00",
        )
        uncovered = covered.model_copy(update={"id": "m2", "opinions": not_yet})
        health = _health(meeting_log=[covered, uncovered])
        assert health.simulation_coverage == 50.0

    def test_self_evaluation_health_uses_the_latest_entry_per_department(self) -> None:
        # CEO Company/Executive Health directive, Phase 5 — engagement
        # (the latest-per-role average, unchanged) is now blended with a
        # real calibration_trend component. With no discipline_reviews
        # here, calibration_trend reads its own honest neutral 50.0.
        old = DepartmentSelfEvaluation(id="s1", role="research", departmentLabel="Research", weekEndingSimDay=7, decisionsReviewed=1, score=20.0, summary="x", createdAt="2026-01-01T00:00:00+00:00")
        new = DepartmentSelfEvaluation(id="s2", role="research", departmentLabel="Research", weekEndingSimDay=14, decisionsReviewed=1, score=90.0, summary="x", createdAt="2026-01-08T00:00:00+00:00")
        health = _health(self_evaluations=[old, new])
        assert health.self_evaluation_health == 70.0

    def _discipline_review(self, *, tier: str, outcome: str) -> DisciplineReview:
        return DisciplineReview(
            id=f"r-{tier}-{outcome}-{id(object())}",
            decisionId="d1",
            symbol="AAPL",
            score=80.0,
            tier=tier,  # type: ignore[arg-type]
            attendees=["scout"],
            summary="x",
            postDecisionReview=PostDecisionReview(),
            outcome=outcome,  # type: ignore[arg-type]
            tradePnlPct=1.0,
            holdDurationMinutes=60,
            simDay=1,
            createdAt="2026-01-01T00:00:00+00:00",
        )

    def test_self_evaluation_health_defaults_to_neutral_with_too_little_history(self) -> None:
        reviews = [self._discipline_review(tier="exemplary", outcome="loss") for _ in range(3)]
        health = _health(self_evaluations=[], discipline_reviews=reviews)
        assert health.self_evaluation_health == 50.0

    def test_self_evaluation_health_rewards_reduced_misalignment_over_time(self) -> None:
        """CEO Company/Executive Health directive, Phase 5 — the exact
        PREDICTION -> OUTCOME -> CORRECTION chain: an organization whose
        real misalignment rate drops from 100% (earlier half, all
        good-tier-process-but-lost) to 0% (later half, all
        good-tier-process-and-won) demonstrates real learning."""
        earlier = [self._discipline_review(tier="exemplary", outcome="loss") for _ in range(4)]
        later = [self._discipline_review(tier="exemplary", outcome="win") for _ in range(4)]
        health = _health(self_evaluations=[], discipline_reviews=earlier + later)
        # engagement defaults to 50 (no self_evaluations); calibration_trend = 100.
        assert health.self_evaluation_health == 75.0

    def test_self_evaluation_health_does_not_reward_a_flat_misalignment_rate(self) -> None:
        """Do not reward agents merely for reporting that they made a
        mistake — a constant, unchanging misalignment rate earns no
        real credit, since nothing was actually corrected."""
        reviews = [self._discipline_review(tier="exemplary", outcome="loss") for _ in range(8)]
        health = _health(self_evaluations=[], discipline_reviews=reviews)
        # calibration_trend = 50 (no real change in misalignment rate).
        assert health.self_evaluation_health == 50.0

    def test_self_evaluation_health_penalizes_worsening_misalignment(self) -> None:
        earlier = [self._discipline_review(tier="exemplary", outcome="win") for _ in range(4)]
        later = [self._discipline_review(tier="exemplary", outcome="loss") for _ in range(4)]
        health = _health(self_evaluations=[], discipline_reviews=earlier + later)
        # engagement defaults to 50 (no self_evaluations); calibration_trend
        # floors at 0 (misalignment rate rose from 0% to 100%).
        assert health.self_evaluation_health == 25.0

    def test_self_evaluation_health_ignores_the_adequate_middle_tier(self) -> None:
        """An "adequate"-tier review counts toward neither aligned nor
        misaligned — the same real middle-tier convention
        app/discipline.py already established."""
        earlier = [self._discipline_review(tier="adequate", outcome="loss") for _ in range(4)]
        later = [self._discipline_review(tier="adequate", outcome="win") for _ in range(4)]
        health = _health(self_evaluations=[], discipline_reviews=earlier + later)
        # No checkable reviews in either half -> calibration_trend stays neutral 50.
        assert health.self_evaluation_health == 50.0

    def test_institutional_memory_blends_wisdom_score_and_knowledge_retention(self) -> None:
        """CEO Company/Executive Health directive — institutional_memory
        is now an equal blend of the real WisdomState.score and real
        per-agent Academy mastery (see app/company_health.py's
        _knowledge_retention()), not a pure WisdomState.score
        passthrough."""
        agent_knowledge = {
            "scout": AgentKnowledgeState(agentId="scout", branch="x", points=100.0, tier=6, level="mentor"),
            "atlas": AgentKnowledgeState(agentId="atlas", branch="x", points=0.0, tier=0, level="novice"),
        }
        health = _health(
            wisdom_state=WisdomState(score=72.5, tier="seasoned_wisdom", tierLabel="Seasoned Wisdom", factors=[], updatedAt="2026-01-01T00:00:00+00:00"),
            agent_knowledge=agent_knowledge,
        )
        # knowledge_retention = 1 real mentor / 2 real agents * 100 = 50.0
        assert health.institutional_memory == 61.2

    def test_institutional_memory_knowledge_retention_rewards_real_mentor_level_agents(self) -> None:
        """A company whose agents have genuinely reached the real top
        "mentor" Academy level scores higher than one whose agents are
        all still novices, even with an identical WisdomState.score —
        knowledge retention, not reflection alone."""
        wisdom_state = WisdomState(score=50.0, tier="developing_judgment", tierLabel="Developing Judgment", factors=[], updatedAt="2026-01-01T00:00:00+00:00")
        all_novice = {aid: AgentKnowledgeState(agentId=aid, branch="x", points=0.0, tier=0, level="novice") for aid in all_agent_ids()}
        all_mentor = {aid: AgentKnowledgeState(agentId=aid, branch="x", points=100.0, tier=6, level="mentor") for aid in all_agent_ids()}
        novice_health = _health(wisdom_state=wisdom_state, agent_knowledge=all_novice)
        mentor_health = _health(wisdom_state=wisdom_state, agent_knowledge=all_mentor)
        assert novice_health.institutional_memory == 25.0
        assert mentor_health.institutional_memory == 75.0

    @staticmethod
    def _strategy(strategy_id: str, stage: str) -> Strategy:
        return Strategy(id=strategy_id, name=strategy_id, description="x", createdBy="scout", focusCategory="stock", createdAt="2026-01-01T00:00:00+00:00", stage=stage)  # type: ignore[arg-type]

    @staticmethod
    def _health_assessment(assessment_id: str, strategy_id: str, trend: str, sim_day: int) -> StrategyHealthAssessment:
        return StrategyHealthAssessment(
            id=assessment_id,
            strategyId=strategy_id,
            strategyName=strategy_id,
            status="excellent" if trend == "improving" else "declining",
            trend=trend,  # type: ignore[arg-type]
            recentWinRate=90.0,
            lifetimeWinRate=80.0,
            recentAvgReturnPct=5.0,
            lifetimeAvgReturnPct=2.0,
            recentAvgDrawdownPct=1.0,
            lifetimeAvgDrawdownPct=2.0,
            recentSampleSize=5,
            lifetimeSampleSize=10,
            reasoning=["x"],
            simDay=sim_day,
            createdAt="2026-01-01T00:00:00+00:00",
        )

    def test_innovation_velocity_blends_three_real_pipeline_signals(self) -> None:
        """CEO Company/Executive Health directive — innovation_velocity
        is now an equal blend of _validation_rigor() (the original,
        unchanged Devil's Advocate reading), _pipeline_progress() (real
        Strategy Lab stage depth), and _measured_improvement() (real
        post-deployment StrategyHealthAssessment trend), not Devil's
        Advocate points alone."""
        health = _health(
            innovation_state={"scout": InnovationState(agentId="scout", points=17.5, tier=2, tierName="innovation_leader")},
            strategies=[self._strategy("s1", "research")],
            strategy_health_assessments=[],
        )
        # rigor = 17.5/35*100 = 50.0; pipeline_progress = stage_index("research")=1 / 8 * 100 = 12.5;
        # measured_improvement = 50.0 neutral (nothing has reached real deployment yet).
        assert health.innovation_velocity == 37.5

    def test_innovation_velocity_pipeline_progress_rewards_real_stage_depth(self) -> None:
        """A strategy that has actually traveled further down the real,
        gated Strategy Lab pipeline scores higher than one still at the
        idea stage, with no Devil's Advocate activity either way."""
        idea_health = _health(strategies=[self._strategy("s1", "idea")])
        approved_health = _health(
            strategies=[self._strategy("s2", "approved")],
            strategy_health_assessments=[self._health_assessment("h1", "s2", "stable", 1)],
        )
        assert approved_health.innovation_velocity > idea_health.innovation_velocity

    def test_innovation_velocity_measured_improvement_rewards_a_real_improving_trend(self) -> None:
        """Two identically-deployed strategies, differing only in their
        own real, independently-computed StrategyHealthAssessment
        trend — the improving one scores higher."""
        strategy = self._strategy("s1", "approved")
        improving = _health(strategies=[strategy], strategy_health_assessments=[self._health_assessment("h1", "s1", "improving", 1)])
        declining = _health(strategies=[strategy], strategy_health_assessments=[self._health_assessment("h2", "s1", "declining", 1)])
        assert improving.innovation_velocity > declining.innovation_velocity

    def test_innovation_velocity_uses_only_the_latest_health_assessment_per_strategy(self) -> None:
        """List order = chronological order, the same convention this
        module already uses elsewhere (e.g. talent_development's
        post-graduation reviews) — an older "declining" read must not
        outvote a newer real "improving" one for the same strategy."""
        strategy = self._strategy("s1", "approved")
        health = _health(
            strategies=[strategy],
            strategy_health_assessments=[
                self._health_assessment("h1", "s1", "declining", 1),
                self._health_assessment("h2", "s1", "improving", 5),
            ],
        )
        only_improving = _health(strategies=[strategy], strategy_health_assessments=[self._health_assessment("h2", "s1", "improving", 5)])
        assert health.innovation_velocity == only_improving.innovation_velocity

    def test_founder_oversight_caps_at_one_hundred(self) -> None:
        # All three notes real (the schema default), so both the
        # occurrence and substance components read 100.
        sessions = [FounderCouncilSession(id=f"c{i}", simDay=i, coachHighlight="x", keystoneNote="x", compassNote="x", createdAt="2026-01-01T00:00:00+00:00") for i in range(10)]
        health = _health(founder_council_sessions=sessions)
        assert health.founder_oversight == 100.0

    def test_no_council_sessions_yet_reads_zero(self) -> None:
        health = _health(founder_council_sessions=[])
        assert health.founder_oversight == 0.0

    def test_founder_oversight_penalizes_placeholder_only_sessions(self) -> None:
        """CEO Company/Executive Health directive, Phase 4 — five real
        sessions that all landed on founders.py's own honest "nothing to
        review yet" fallback (no real content in any of the three notes)
        must read lower than five sessions that surfaced real company
        content, even though both hit the same occurrence count."""
        placeholder_sessions = [
            FounderCouncilSession(
                id=f"c{i}", simDay=i, coachHighlight="x", keystoneNote="x", compassNote="x",
                coachHighlightIsReal=False, keystoneNoteIsReal=False, compassNoteIsReal=False,
                createdAt="2026-01-01T00:00:00+00:00",
            )
            for i in range(5)
        ]
        real_sessions = [FounderCouncilSession(id=f"c{i}", simDay=i, coachHighlight="x", keystoneNote="x", compassNote="x", createdAt="2026-01-01T00:00:00+00:00") for i in range(5)]
        placeholder_health = _health(founder_council_sessions=placeholder_sessions)
        real_health = _health(founder_council_sessions=real_sessions)
        # occurrence = min(100, 5*20) = 100 for both; substance = 0 vs 100.
        assert placeholder_health.founder_oversight == 50.0
        assert real_health.founder_oversight == 100.0
        assert placeholder_health.founder_oversight < real_health.founder_oversight

    def test_founder_oversight_averages_partial_substance_across_sessions(self) -> None:
        """A single session with two of its three real notes and one
        placeholder reads partial substance credit, not all-or-nothing."""
        session = FounderCouncilSession(
            id="c1", simDay=1, coachHighlight="x", keystoneNote="x", compassNote="x",
            coachHighlightIsReal=True, keystoneNoteIsReal=True, compassNoteIsReal=False,
            createdAt="2026-01-01T00:00:00+00:00",
        )
        health = _health(founder_council_sessions=[session])
        # occurrence = min(100, 1*20) = 20; substance = 2/3 * 100 = 66.7.
        assert health.founder_oversight == round((20.0 + 200.0 / 3.0) / 2.0, 1)

    def test_talent_development_reads_real_graduation_progress(self) -> None:
        # Isolated to a single real active track (tjr) — market_intelligence
        # (v0.7 Feature 51) and mark_douglas/linda_raschke (Trading
        # Psychology & Discipline, Piece F) are also "active" by default
        # on a fresh game, so they're explicitly parked back to "planned"
        # here to test the single-active-track case cleanly; see the next
        # test for the real multi-active-track denominator.
        #
        # CEO Company/Executive Health directive, Phase 3 — no
        # graduatedSimDay and no discipline_reviews means each graduated
        # pair's real post-graduation performance is honestly "not yet
        # measurable" (neutral 50.0), so each pair now contributes
        # (100 + 50) / 2 = 75 credit rather than a flat 100 — see
        # test_talent_development_rewards_demonstrated_post_graduation_performance
        # below for the case where real post-graduation data exists.
        fm_state = default_foundational_mentor_state()
        parked = {"market_intelligence", "mark_douglas", "linda_raschke"}
        fm_state = fm_state.model_copy(update={"mentors": [m.model_copy(update={"status": "planned"}) if m.id in parked else m for m in fm_state.mentors]})
        graduated = FoundationalMentorProgress(mentorId="tjr", graduationStatus="graduated")  # type: ignore[call-arg]
        fm_state = fm_state.model_copy(update={"progress": {agent_id: {"tjr": graduated} for agent_id in list(STUDENT_AGENT_IDS)[:4]}})
        health = _health(foundational_mentor_state=fm_state)
        assert health.talent_development == 37.5

    def test_talent_development_divides_across_every_real_active_track(self) -> None:
        # v0.7 Feature 51 and Trading Psychology & Discipline Piece F — a
        # fresh game legitimately has four real active tracks (tjr,
        # market_intelligence, mark_douglas, linda_raschke) until one
        # graduates, so the real denominator is students × active tracks,
        # not just students.
        fm_state = default_foundational_mentor_state()
        assert sum(1 for m in fm_state.mentors if m.status == "active") == 4
        graduated = FoundationalMentorProgress(mentorId="tjr", graduationStatus="graduated")  # type: ignore[call-arg]
        fm_state = fm_state.model_copy(update={"progress": {agent_id: {"tjr": graduated} for agent_id in list(STUDENT_AGENT_IDS)[:4]}})
        health = _health(foundational_mentor_state=fm_state)
        assert health.talent_development == round(9.375, 1)

    def _graduated_state(self, *, graduated_sim_day: int | None):
        fm_state = default_foundational_mentor_state()
        parked = {"market_intelligence", "mark_douglas", "linda_raschke"}
        fm_state = fm_state.model_copy(update={"mentors": [m.model_copy(update={"status": "planned"}) if m.id in parked else m for m in fm_state.mentors]})
        graduated = FoundationalMentorProgress(mentorId="tjr", graduationStatus="graduated", graduatedSimDay=graduated_sim_day)  # type: ignore[call-arg]
        return fm_state.model_copy(update={"progress": {"scout": {"tjr": graduated}}})

    def _review(self, *, agent_id: str, score: float, sim_day: int) -> DisciplineReview:
        return DisciplineReview(
            id=f"r-{agent_id}-{sim_day}",
            decisionId="d1",
            symbol="AAPL",
            score=score,
            tier="adequate",
            attendees=[agent_id],  # type: ignore[list-item]
            summary="x",
            postDecisionReview=PostDecisionReview(),
            outcome="win",
            tradePnlPct=1.0,
            holdDurationMinutes=60,
            simDay=sim_day,
            createdAt="2026-01-01T00:00:00+00:00",
        )

    def test_talent_development_rewards_demonstrated_post_graduation_performance(self) -> None:
        """CEO Company/Executive Health directive, Phase 3 — the exact
        TRAINING -> APPLICATION -> PERFORMANCE chain: a graduate whose
        real post-graduation Discipline Scores are strong earns close to
        full credit for that pair, not merely the graduation badge."""
        fm_state = self._graduated_state(graduated_sim_day=5)
        strong_reviews = [self._review(agent_id="scout", score=95.0, sim_day=day) for day in (6, 7, 8)]
        health = _health(foundational_mentor_state=fm_state, discipline_reviews=strong_reviews)
        # 1 graduated pair out of 8 real slots: (100 + 95) / 2 = 97.5 credit / 8 slots.
        assert health.talent_development == round(97.5 / 8, 1)

    def test_talent_development_does_not_award_full_credit_for_weak_post_graduation_performance(self) -> None:
        """Do NOT award Talent Development merely because a training
        event occurred — a real graduate whose post-graduation behavior
        is weak earns less than one whose real behavior is strong, even
        though both hold the same graduation badge."""
        fm_state = self._graduated_state(graduated_sim_day=5)
        weak_reviews = [self._review(agent_id="scout", score=20.0, sim_day=day) for day in (6, 7, 8)]
        strong_health = _health(foundational_mentor_state=fm_state, discipline_reviews=[self._review(agent_id="scout", score=95.0, sim_day=6)])
        weak_health = _health(foundational_mentor_state=fm_state, discipline_reviews=weak_reviews)
        assert weak_health.talent_development < strong_health.talent_development

    def test_talent_development_ignores_reviews_from_before_graduation(self) -> None:
        """A weak review filed BEFORE this agent even graduated must not
        count as real "post-graduation" performance — the whole point is
        measuring what happened after training, not before it."""
        fm_state = self._graduated_state(graduated_sim_day=5)
        pre_graduation_only = [self._review(agent_id="scout", score=10.0, sim_day=1)]
        health = _health(foundational_mentor_state=fm_state, discipline_reviews=pre_graduation_only)
        # No real post-graduation review exists yet, so this pair reads
        # the same honest neutral-50 fallback as having no reviews at all.
        assert health.talent_development == round(75.0 / 8, 1)

    def test_talent_development_ignores_other_agents_reviews(self) -> None:
        """A strong review filed for a DIFFERENT real agent must not
        count toward this graduate's own demonstrated performance."""
        fm_state = self._graduated_state(graduated_sim_day=5)
        someone_elses_review = [self._review(agent_id="echo", score=95.0, sim_day=6)]
        health = _health(foundational_mentor_state=fm_state, discipline_reviews=someone_elses_review)
        assert health.talent_development == round(75.0 / 8, 1)

    def test_executive_overall_is_the_mean_of_the_ten_executive_metrics_and_never_moves_the_operational_overall(self) -> None:
        baseline = _health()
        strong = _health(**_strong_executive_overrides())
        # The original Operational overall/tier are completely
        # unaffected by Executive-tier inputs — the redesign is additive.
        assert strong.overall == baseline.overall
        assert strong.tier == baseline.tier
        assert strong.executive_overall > baseline.executive_overall
        assert strong.combined_overall > baseline.combined_overall

    def test_combined_overall_is_the_equal_blend_of_both_tiers(self) -> None:
        health = _health(**_strong_executive_overrides())
        assert health.combined_overall == round((health.overall + health.executive_overall) / 2.0, 1)


class TestCeoConfiguredTierThresholds:
    """v0.7 Design Bible Chapter 63 — Company Health tier thresholds are
    now CEO-configurable, defaulting to the exact prior fixed constants
    (85/70/50/30) so existing behavior is unchanged until the CEO
    adjusts them."""

    def test_default_thresholds_match_the_prior_fixed_constants(self) -> None:
        # A pure, near-neutral company (default _health()) reads "stable"
        # under both the old fixed constants and the new defaults.
        health = _health()
        assert health.tier == "stable"

    def test_ceo_lowered_excellent_threshold_reclassifies_the_same_score(self) -> None:
        default_health = _health()
        # CEO Company/Executive Health directive, Education Progress fix —
        # the default fixture's raw (unrounded) overall now lands just
        # under a .1 rounding boundary (54.0909... rounds display-side to
        # 54.1), so using the exact rounded `overall` as the threshold
        # would fail the real `>=` comparison against the raw value by a
        # sliver. Subtracting a small margin keeps this test's real intent
        # (a threshold clearly at-or-below the company's real score
        # reclassifies it) without depending on which side of a rounding
        # boundary the fixture's raw score happens to land on.
        lowered = _health(excellent_threshold=default_health.overall - 0.5)
        assert lowered.tier == "excellent"
        assert default_health.tier != "excellent"

    def test_ceo_raised_stable_threshold_reclassifies_the_same_score(self) -> None:
        default_health = _health()
        raised = _health(stable_threshold=default_health.overall + 1.0, needs_attention_threshold=default_health.overall - 1.0)
        assert raised.tier == "needs_attention"

    def test_thresholds_apply_identically_to_executive_and_combined_tiers(self) -> None:
        health = _health(excellent_threshold=0.0, good_threshold=-1.0, stable_threshold=-2.0, needs_attention_threshold=-3.0)
        assert health.tier == "excellent"
        assert health.executive_tier == "excellent"
        assert health.combined_tier == "excellent"


def _meeting_log_entry(entry_id: str, opinions: list[DepartmentOpinion]) -> ExecutiveMeetingLogEntry:
    return ExecutiveMeetingLogEntry(
        id=entry_id, proposalId=entry_id, symbol="AAPL", simDay=1, opinions=opinions, recommendedAction="trade_normally", recommendationReason="x",
        ceoDecision="buy", networkAgreed=True, decisionGrade="A", decisionGradeScore=90.0, resolvedBy="ceo", createdAt="2026-01-01T00:00:00+00:00",
    )


class TestDepartmentConsensus:
    """CEO Company/Executive Health directive, Phase 2: Department
    Consensus must measure "can the organization reach a coherent,
    evidence-supported decision," not "did everybody vote yes" — see
    app/company_health.py's _department_consensus()."""

    def test_no_opinions_yet_reads_neutral(self) -> None:
        health = _health(meeting_log=[])
        assert health.department_consensus == 50.0

    def test_full_agreement_reads_full_consensus(self) -> None:
        opinions = [DepartmentOpinion(role=role, departmentLabel=role, stance="agree", summary="x", confidencePct=90.0) for role in _ALL_ROLES]
        health = _health(meeting_log=[_meeting_log_entry("m1", opinions)])
        assert health.department_consensus == 100.0

    def test_requesting_more_research_is_not_scored_as_disagreement(self) -> None:
        """The exact anti-pattern the CEO named: a department asking for
        more evidence before committing is a constructive, real epistemic
        stance — not a vote against consensus. Under the OLD agree-only
        formula, this scenario would have read 50.0 (half "no"); the
        corrected formula reads 100.0 because none of these opinions are
        real substantive opposition."""
        opinions = [
            DepartmentOpinion(role="research", departmentLabel="Research", stance="agree", summary="x", confidencePct=90.0),
            DepartmentOpinion(role="quant", departmentLabel="Quant", stance="request_more_research", summary="x", confidencePct=50.0),
            DepartmentOpinion(role="risk", departmentLabel="Risk", stance="recommend_waiting", summary="x", confidencePct=50.0),
            DepartmentOpinion(role="simulation", departmentLabel="Simulation", stance="recommend_position_change", summary="x", confidencePct=50.0),
        ]
        health = _health(meeting_log=[_meeting_log_entry("m1", opinions)])
        assert health.department_consensus == 100.0

    def test_evidence_backed_disagreement_still_counts_as_coherent(self) -> None:
        """The CEO's own "GOOD DISAGREEMENT + EVIDENCE" case: a real
        substantive objection that names real concerns is healthy
        organizational functioning, not a penalty."""
        opinions = [
            DepartmentOpinion(role="research", departmentLabel="Research", stance="agree", summary="x", confidencePct=90.0),
            DepartmentOpinion(role="risk", departmentLabel="Risk", stance="disagree", summary="x", confidencePct=30.0, concerns=["Exposure factor is below the risk bar."]),
        ]
        health = _health(meeting_log=[_meeting_log_entry("m1", opinions)])
        assert health.department_consensus == 100.0

    def test_bare_unsubstantiated_opposition_counts_against_consensus(self) -> None:
        """The one real case this metric should still penalize: a
        genuinely opposing stance with no real evidence behind it at
        all — an unsupported block, not a reasoned objection."""
        opinions = [
            DepartmentOpinion(role="research", departmentLabel="Research", stance="agree", summary="x", confidencePct=90.0),
            DepartmentOpinion(role="devils_advocate", departmentLabel="Devil's Advocate", stance="recommend_rejecting", summary="x", confidencePct=25.0, concerns=[]),
        ]
        health = _health(meeting_log=[_meeting_log_entry("m1", opinions)])
        assert health.department_consensus == 50.0

    def test_cannot_be_gamed_by_forcing_universal_agreement_alone(self) -> None:
        """Full agreement and full evidence-backed disagreement both read
        100 — proving this metric cannot be raised merely by suppressing
        real dissent, only by ensuring real objections are substantiated."""
        agree_only = [DepartmentOpinion(role=role, departmentLabel=role, stance="agree", summary="x", confidencePct=90.0) for role in _ALL_ROLES]
        evidence_backed_dissent = [
            DepartmentOpinion(role=role, departmentLabel=role, stance="disagree", summary="x", confidencePct=30.0, concerns=["A real, named concern."]) for role in _ALL_ROLES
        ]
        agree_health = _health(meeting_log=[_meeting_log_entry("m1", agree_only)])
        dissent_health = _health(meeting_log=[_meeting_log_entry("m2", evidence_backed_dissent)])
        assert agree_health.department_consensus == dissent_health.department_consensus == 100.0


class TestDiffCompanyHealth:
    """CEO Company Health + Live Market Realism directive, Section 6 —
    diff_company_health() computes the explicit before/after delta
    breakdown as a pure diff between two real CompanyHealth readings,
    never fabricated "reason"/"evidence" text."""

    def test_returns_none_when_no_previous_reading(self) -> None:
        current = _ch()
        assert diff_company_health(None, current) is None

    def test_no_components_when_nothing_actually_changed(self) -> None:
        previous = _ch(updatedAt="2026-01-01T00:00:00+00:00")
        current = _ch(updatedAt="2026-01-01T01:00:00+00:00")
        delta = diff_company_health(previous, current)
        assert delta is not None
        assert delta.components == []
        assert delta.overall_delta == 0.0
        assert delta.executive_overall_delta == 0.0
        assert delta.combined_overall_delta == 0.0
        assert delta.tier_changed is False
        assert delta.executive_tier_changed is False
        assert delta.combined_tier_changed is False
        assert delta.previous_updated_at == "2026-01-01T00:00:00+00:00"
        assert delta.current_updated_at == "2026-01-01T01:00:00+00:00"

    def test_a_real_operational_change_appears_with_correct_values(self) -> None:
        previous = _ch(reputation=40.0)
        current = _ch(reputation=64.0)
        delta = diff_company_health(previous, current)
        assert delta is not None
        assert len(delta.components) == 1
        component = delta.components[0]
        assert component.key == "reputation"
        assert component.label == "Reputation"
        assert component.group == "operational"
        assert component.previous == 40.0
        assert component.current == 64.0
        assert component.delta == 24.0

    def test_a_real_executive_change_appears_with_correct_group(self) -> None:
        previous = _ch(decisionQuality=60.0)
        current = _ch(decisionQuality=55.0)
        delta = diff_company_health(previous, current)
        assert delta is not None
        assert len(delta.components) == 1
        component = delta.components[0]
        assert component.key == "decision_quality"
        assert component.group == "executive"
        assert component.delta == -5.0

    def test_components_are_sorted_by_magnitude_descending(self) -> None:
        previous = _ch(reputation=50.0, decisionQuality=50.0)
        current = _ch(reputation=51.0, decisionQuality=80.0)
        delta = diff_company_health(previous, current)
        assert delta is not None
        assert [c.key for c in delta.components] == ["decision_quality", "reputation"]

    def test_overall_and_tier_deltas_are_computed(self) -> None:
        previous = _ch(overall=60.0, tier="good", executiveOverall=55.0, executiveTier="stable", combinedOverall=57.5, combinedTier="stable")
        current = _ch(overall=65.0, tier="good", executiveOverall=55.0, executiveTier="excellent", combinedOverall=60.0, combinedTier="stable")
        delta = diff_company_health(previous, current)
        assert delta is not None
        assert delta.overall_delta == 5.0
        assert delta.executive_overall_delta == 0.0
        assert delta.combined_overall_delta == 2.5
        assert delta.tier_changed is False
        assert delta.executive_tier_changed is True
        assert delta.combined_tier_changed is False
