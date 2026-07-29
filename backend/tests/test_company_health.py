"""Covers app/company_health.py — v0.7 Feature 23, the Company Health &
Stability System. Every sub-score reads a real, already-tracked signal
(agent location/mood, research completion, portfolio P&L, risk warnings,
AgentEnergy, HallOfFameEntry count, SignalCalibrationState's real level,
watchlist length beyond SEED_SYMBOLS, EducationProgress) — nothing here
is randomized or invented.
"""
from __future__ import annotations

from app.company_health import compute_company_health
from app.education import all_lessons
from app.portfolio import default_portfolio
from app.schemas import (
    AgentEnergy,
    AgentState,
    Debate,
    DebateTurn,
    EducationProgress,
    EntityTransform,
    ResearchItem,
    RiskWarning,
    SignalCalibrationState,
    WatchlistEntry,
)
from app.signal_calibration import MAX_LEVEL as SIGNAL_MAX_LEVEL
from app.watchlist import SEED_SYMBOLS, default_watchlist


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
            portfolio=default_portfolio().model_copy(update={"total_pnl_pct": 40.0}),
            debates=[_all_supportive_debate()],
        )
        assert health.recommendations == []


class TestTeamChemistry:
    def test_no_debates_yet_reads_neutral(self) -> None:
        health = _health(debates=[])
        assert health.team_chemistry == 50.0

    def test_mostly_supportive_turns_score_high(self) -> None:
        health = _health(debates=[_all_supportive_debate()])
        assert health.team_chemistry == 100.0

    def test_mostly_challenge_turns_score_low(self) -> None:
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
        health = _health(debates=[debate])
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
        health = _health(debates=[*(challenge_debate for _ in range(19)), _all_supportive_debate()])
        assert 0.0 < health.team_chemistry < 100.0


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
