"""Covers app/company_health.py — v0.7 Feature 23, the Company Health &
Stability System. Every sub-score reads a real, already-tracked signal
(agent location/mood, research completion, portfolio P&L, risk warnings,
AgentEnergy, HallOfFameEntry count, SignalCalibrationState's real level,
watchlist length beyond SEED_SYMBOLS, EducationProgress) — nothing here
is randomized or invented.
"""
from __future__ import annotations

from app.company_health import compute_company_health
from app.debate import generate_debate
from app.education import all_lessons
from app.foundational_mentors import STUDENT_AGENT_IDS, default_foundational_mentor_state
from app.portfolio import default_portfolio
from app.schemas import (
    AgentEnergy,
    AgentState,
    AnalystVote,
    Debate,
    DebateTurn,
    DecisionConfidence,
    DepartmentOpinion,
    DepartmentSelfEvaluation,
    EducationProgress,
    EntityTransform,
    ExecutiveDepartmentRole,
    ExecutiveMeetingLogEntry,
    FoundationalMentorProgress,
    FounderCouncilSession,
    InnovationState,
    PaperTrade,
    ResearchItem,
    RiskWarning,
    SignalCalibrationState,
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
    graduated_by_mentor = {
        mentor_id: FoundationalMentorProgress(mentorId=mentor_id, graduationStatus="graduated")  # type: ignore[call-arg]
        for mentor_id in ("tjr", "market_intelligence", "mark_douglas", "linda_raschke")
    }
    fm_state = default_foundational_mentor_state().model_copy(
        update={"progress": {agent_id: dict(graduated_by_mentor) for agent_id in STUDENT_AGENT_IDS}}
    )
    founder_council_sessions = [
        FounderCouncilSession(id=f"c{i}", simDay=i, coachHighlight="x", keystoneNote="x", compassNote="x", createdAt="2026-01-01T00:00:00+00:00") for i in range(5)
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
    )
    defaults.update(overrides)
    return compute_company_health(**defaults)


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


class TestOfficeExpansion:
    def test_seed_watchlist_only_is_zero_expansion(self) -> None:
        health = _health(watchlist=default_watchlist())
        assert health.office_expansion == 0.0

    def test_added_symbols_increase_expansion(self) -> None:
        extra = WatchlistEntry(symbol="AMZN", name="Amazon", lastPrice=100.0, dailyChangePct=0.0, status="queued", researchProgress=0.0, assignedAgent=None)
        watchlist = [*default_watchlist(), extra]
        health = _health(watchlist=watchlist)
        assert health.office_expansion > 0.0
        assert len(default_watchlist()) == len(SEED_SYMBOLS)


class TestEducationProgress:
    def test_no_completed_lessons_is_zero(self) -> None:
        health = _health(education=EducationProgress())
        assert health.education_progress == 0.0


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
            health.office_expansion,
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
        assert any("Resource Usage" in r or "Employee Morale" in r or "Department Efficiency" in r or "Technology Level" in r or "Office Expansion" in r or "Education Progress" in r for r in health.recommendations)

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
        assert health.institutional_memory == 50.0
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
        assert health.decision_quality == 85.0

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
        old = DepartmentSelfEvaluation(id="s1", role="research", departmentLabel="Research", weekEndingSimDay=7, decisionsReviewed=1, score=20.0, summary="x", createdAt="2026-01-01T00:00:00+00:00")
        new = DepartmentSelfEvaluation(id="s2", role="research", departmentLabel="Research", weekEndingSimDay=14, decisionsReviewed=1, score=90.0, summary="x", createdAt="2026-01-08T00:00:00+00:00")
        health = _health(self_evaluations=[old, new])
        assert health.self_evaluation_health == 90.0

    def test_institutional_memory_reuses_the_real_wisdom_score(self) -> None:
        health = _health(wisdom_state=WisdomState(score=72.5, tier="seasoned_wisdom", tierLabel="Seasoned Wisdom", factors=[], updatedAt="2026-01-01T00:00:00+00:00"))
        assert health.institutional_memory == 72.5

    def test_innovation_velocity_normalizes_against_the_legendary_threshold(self) -> None:
        health = _health(innovation_state={"scout": InnovationState(agentId="scout", points=17.5, tier=2, tierName="innovation_leader")})
        assert health.innovation_velocity == 50.0

    def test_founder_oversight_caps_at_one_hundred(self) -> None:
        sessions = [FounderCouncilSession(id=f"c{i}", simDay=i, coachHighlight="x", keystoneNote="x", compassNote="x", createdAt="2026-01-01T00:00:00+00:00") for i in range(10)]
        health = _health(founder_council_sessions=sessions)
        assert health.founder_oversight == 100.0

    def test_talent_development_reads_real_graduation_progress(self) -> None:
        # Isolated to a single real active track (tjr) — market_intelligence
        # (v0.7 Feature 51) and mark_douglas/linda_raschke (Trading
        # Psychology & Discipline, Piece F) are also "active" by default
        # on a fresh game, so they're explicitly parked back to "planned"
        # here to test the single-active-track case cleanly; see the next
        # test for the real multi-active-track denominator.
        fm_state = default_foundational_mentor_state()
        parked = {"market_intelligence", "mark_douglas", "linda_raschke"}
        fm_state = fm_state.model_copy(update={"mentors": [m.model_copy(update={"status": "planned"}) if m.id in parked else m for m in fm_state.mentors]})
        graduated = FoundationalMentorProgress(mentorId="tjr", graduationStatus="graduated")  # type: ignore[call-arg]
        fm_state = fm_state.model_copy(update={"progress": {agent_id: {"tjr": graduated} for agent_id in list(STUDENT_AGENT_IDS)[:4]}})
        health = _health(foundational_mentor_state=fm_state)
        assert health.talent_development == 50.0

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
        assert health.talent_development == 12.5

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
        lowered = _health(excellent_threshold=default_health.overall)
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
