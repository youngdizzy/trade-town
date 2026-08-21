"""Covers app/knowledge_graph.py — v0.7 Feature 25.5, the Company
Knowledge Graph. Every edge here must trace to a real, checkable shared
attribute on the underlying records; nothing here is a fabricated or
invented connection.
"""

from __future__ import annotations

from app.knowledge_graph import build_knowledge_graph
from app.schemas import (
    AcademyProject,
    AgentKnowledgeState,
    CaseStudy,
    CoachReport,
    DecisionVaultEntry,
    EconomicConfidenceRead,
    EconomicHealthScore,
    EconomicIntelligenceReport,
    EconomicIntelligenceState,
    ExecutiveReview,
    HallOfFameEntry,
    MarketNarrativeEntry,
    ModelValidationCheck,
    ModelValidationReport,
    NewsRiskRead,
    ResearchItem,
    Strategy,
)
from app.quant_research_lab import file_quant_research_experiment
from app.research_experiment import run_research_experiment
from app.strategy_compiler import compile_strategy_text

_STRATEGY_TEXT = (
    "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. "
    "Place the stop at the Chandelier Stop and target 2R."
)


def _research(
    agent: str,
    symbol: str,
    category: str = "stock",
    updated_at: str = "2026-01-01T00:00:00+00:00",
    status: str = "completed",
) -> ResearchItem:
    return ResearchItem(
        id=f"r-{agent}-{symbol}-{updated_at}",
        title=f"Research on {symbol}",
        symbol=symbol,
        category=category,  # type: ignore[arg-type]
        priority="normal",
        status=status,  # type: ignore[arg-type]
        assignedAgent=agent,  # type: ignore[arg-type]
        summary="test",
        confidence=80.0,
        createdAt=updated_at,
        updatedAt=updated_at,
    )


def _project(
    agent: str, topic: str, title: str, updated_at: str = "2026-01-01T00:00:00+00:00"
) -> AcademyProject:
    return AcademyProject(
        id=f"p-{agent}-{title}-{updated_at}",
        topic=topic,  # type: ignore[arg-type]
        title=title,
        assignedAgent=agent,  # type: ignore[arg-type]
        status="completed",
        progress=100.0,
        summary="test",
        createdAt=updated_at,
        updatedAt=updated_at,
    )


def _hof(agent_id: str | None, title: str = "5-trade streak") -> HallOfFameEntry:
    return HallOfFameEntry(
        id=f"hof-{title}",
        category="winning_streak",
        title=title,
        description="test",
        agentId=agent_id,  # type: ignore[arg-type]
        value=5.0,
        achievedAt="2026-01-01T00:00:00+00:00",
    )


def _coach_report(top_agent: str) -> CoachReport:
    from app.schemas import AgentScore

    return CoachReport(
        id="report-1",
        period="weekly",
        companyScore=60.0,
        agentRankings=[
            AgentScore(
                agentId=top_agent,  # type: ignore[arg-type]
                score=90.0,
                researchAccuracy=90.0,
                confidenceCalibration=90.0,
            )
        ],
        researchAccuracy=60.0,
        winRate=60.0,
        lossRate=40.0,
        averageConfidence=60.0,
        riskScore=20.0,
        commonMistakes=[],
        strengths=[],
        recommendations=[],
        createdAt="2026-01-01T00:00:00+00:00",
    )


def _vault_entry(
    entry_id: str,
    symbol: str,
    case_study_id: str | None = None,
    created_at: str = "2026-01-01T00:00:00+00:00",
) -> DecisionVaultEntry:
    return DecisionVaultEntry(
        id=entry_id,
        tradeId=f"trade-{entry_id}",
        decisionId=f"decision-{entry_id}",
        symbol=symbol,
        simDay=1,
        session="market_open",  # type: ignore[arg-type]
        marketRegime="sideways_range",  # type: ignore[arg-type]
        marketRegimeLabel="Sideways Range",
        liquidityContext={  # type: ignore[arg-type]
            "symbol": symbol,
            "zones": [],
            "sweepDetected": False,
            "sweepDirection": "none",
            "liquidityScore": 50.0,
            "detail": "test",
        },
        evidenceScore=80.0,
        confidenceScore=80.0,
        confidenceTier="strong",  # type: ignore[arg-type]
        capitalAllocationGrade="B",  # type: ignore[arg-type]
        decisionGrade="B",  # type: ignore[arg-type]
        decisionGradeScore=80.0,
        disciplineTier="sound",  # type: ignore[arg-type]
        disciplineScore=75.0,
        patienceGrade="B",  # type: ignore[arg-type]
        positionSize=10.0,
        entryPrice=100.0,
        exitPrice=105.0,
        pnl=50.0,
        pnlPct=5.0,
        holdDurationMinutes=120,
        caseStudyId=case_study_id,
        lessonsLearned="test",
        ceoOverride=False,
        createdAt=created_at,
    )


def _case_study(cs_id: str, category: str = "overconfidence", title: str = "Test Case Study") -> CaseStudy:
    return CaseStudy(
        id=cs_id,
        category=category,  # type: ignore[arg-type]
        title=title,
        symbol="AAPL",
        decisionId=f"decision-{cs_id}",
        background="test",
        decisionProcess="test",
        missedInformation="test",
        lessonsLearned="test",
        recommendedImprovements="test",
        tradePnlPct=-2.0,
        simDay=1,
        createdAt="2026-01-01T00:00:00+00:00",
    )


def _economic_report(report_id: str, sim_day: int, headline: str = "Steady conditions") -> EconomicIntelligenceReport:
    snapshot = EconomicIntelligenceState(
        regime="bull",  # type: ignore[arg-type]
        regimeLabel="Bull",
        marketQualityTier="good",  # type: ignore[arg-type]
        health=EconomicHealthScore(overall=70.0, tier="stable", factors=[], reasoning="test"),  # type: ignore[arg-type]
        confidence=EconomicConfidenceRead(confidencePct=70.0, evidenceQuality="moderate", supportingEvidence=[], contradictingEvidence=[], alternativeOutcome="test"),  # type: ignore[arg-type]
        correlationPairs=[],
        categoryExposure=[],
        newsRisk=NewsRiskRead(activeMarketNewsCount=0, riskLevel="low", detail="test"),  # type: ignore[arg-type]
        updatedAt="2026-01-01T00:00:00+00:00",
    )
    narrative = MarketNarrativeEntry(id=f"narrative-{report_id}", headline=headline, body="test", evidence=[], simDay=sim_day, createdAt="2026-01-01T00:00:00+00:00")
    return EconomicIntelligenceReport(id=report_id, simDay=sim_day, snapshot=snapshot, narrative=narrative, createdAt="2026-01-01T00:00:00+00:00")


def _strategy(
    strategy_id: str,
    agent: str,
    category: str = "stock",
    stage: str = "research",
    created_at: str = "2026-01-01T00:00:00+00:00",
    compiled_definition_id: str | None = None,
) -> Strategy:
    return Strategy(
        id=strategy_id,
        name=f"Strategy {strategy_id}",
        description="test",
        createdBy=agent,  # type: ignore[arg-type]
        focusCategory=category,  # type: ignore[arg-type]
        createdAt=created_at,
        stage=stage,  # type: ignore[arg-type]
        compiledDefinitionId=compiled_definition_id,
    )


def _validation(strategy_id: str, verdict: str = "rejected") -> ModelValidationReport:
    return ModelValidationReport(
        id=f"validation-{strategy_id}",
        strategyId=strategy_id,
        strategyName=f"Strategy {strategy_id}",
        reviewId="review-1",
        existingReviewCount=0,
        verdict=verdict,  # type: ignore[arg-type]
        checks=[
            ModelValidationCheck(
                id="tail_risk",
                label="Tail Risk",
                passed=False,
                evidence="test",
                reasoning="test",
                thresholdSource="CERTIFICATION_MAX_RUIN_PCT (strategy_lab.py)",
            ),
        ],
        evidenceSummary="1 of 6 real checks failed: Tail Risk.",
        simDay=5,
        createdAt="2026-01-01T00:00:00+00:00",
    )


def _review(agent_ids: list[str]) -> ExecutiveReview:
    from app.schemas import DepartmentActivity

    return ExecutiveReview(
        id="review-1",
        companyScore=60.0,
        companyScoreChange=0.0,
        companyHealthTier="stable",
        departmentActivity=[
            DepartmentActivity(agentId=a, researchCompleted=1, decisionsInvolved=0)  # type: ignore[arg-type]
            for a in agent_ids
        ],
        researchCompleted=1,
        knowledgeGained=0,
        lessonsCompleted=0,
        majorEvents=[],
        conflictsDetected=0,
        flags=[],
        recommendations=[],
        longTermGoals=[],
        summary="test",
        createdAt="2026-01-01T00:00:00+00:00",
    )


class TestBuildKnowledgeGraph:
    def test_every_agent_gets_a_node(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=("scout", "cio"),
            research=[],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[],
            strategies=[],
            black_swan_events=[],
            economic_reports=[],
        )
        agent_node_ids = {n.id for n in graph.nodes if n.type == "agent"}
        assert agent_node_ids == {"agent-scout", "agent-cio"}

    def test_completed_research_becomes_a_node_linked_to_its_real_agent(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=("nova",),
            research=[_research("nova", "AAPL")],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[],
            strategies=[],
            black_swan_events=[],
            economic_reports=[],
        )
        research_nodes = [n for n in graph.nodes if n.type == "research"]
        assert len(research_nodes) == 1
        edge = next(e for e in graph.edges if e.relation == "researched")
        assert edge.source == "agent-nova"
        assert edge.target == research_nodes[0].id

    def test_in_progress_research_is_not_a_node(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=("nova",),
            research=[_research("nova", "AAPL", status="in_progress")],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[],
            strategies=[],
            black_swan_events=[],
            economic_reports=[],
        )
        assert not any(n.type == "research" for n in graph.nodes)

    def test_same_category_research_gets_a_real_builds_on_chain(self) -> None:
        older = _research(
            "nova", "AAPL", category="stock", updated_at="2026-01-01T00:00:00+00:00"
        )
        newer = _research(
            "scout", "MSFT", category="stock", updated_at="2026-02-01T00:00:00+00:00"
        )
        graph = build_knowledge_graph(
            agent_ids=("nova", "scout"),
            research=[older, newer],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[],
            strategies=[],
            black_swan_events=[],
            economic_reports=[],
        )
        builds_on = [e for e in graph.edges if e.relation == "builds_on"]
        assert len(builds_on) == 1
        assert builds_on[0].source == f"research-{newer.id}"
        assert builds_on[0].target == f"research-{older.id}"

    def test_different_category_research_gets_no_builds_on_edge(self) -> None:
        a = _research("nova", "AAPL", category="stock")
        b = _research("scout", "BTC-USD", category="bitcoin")
        graph = build_knowledge_graph(
            agent_ids=("nova", "scout"),
            research=[a, b],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[],
            strategies=[],
            black_swan_events=[],
            economic_reports=[],
        )
        assert not any(e.relation == "builds_on" for e in graph.edges)

    def test_completed_academy_project_becomes_a_node_linked_to_its_real_agent(
        self,
    ) -> None:
        graph = build_knowledge_graph(
            agent_ids=("scout",),
            research=[],
            academy_completed_projects=[
                _project("scout", "market_history", "Studying Black Monday")
            ],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[],
            strategies=[],
            black_swan_events=[],
            economic_reports=[],
        )
        academy_nodes = [n for n in graph.nodes if n.type == "academy_project"]
        assert len(academy_nodes) == 1
        edge = next(e for e in graph.edges if e.relation == "completed")
        assert edge.source == "agent-scout"
        assert edge.target == academy_nodes[0].id

    def test_agent_knowledge_creates_a_shared_branch_node(self) -> None:
        knowledge = {
            "echo": AgentKnowledgeState(
                agentId="echo",
                branch="Technical Analysis",
                points=10.0,
                tier=1,
                level="beginner",
            ),  # type: ignore[arg-type]
            "pulse": AgentKnowledgeState(
                agentId="pulse", branch="Statistics", points=5.0, tier=0, level="novice"
            ),  # type: ignore[arg-type]
        }
        graph = build_knowledge_graph(
            agent_ids=("echo", "pulse"),
            research=[],
            academy_completed_projects=[],
            agent_knowledge=knowledge,
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[],
            strategies=[],
            black_swan_events=[],
            economic_reports=[],
        )
        branch_nodes = [n for n in graph.nodes if n.type == "branch"]
        assert len(branch_nodes) == 2
        has_branch_edges = [e for e in graph.edges if e.relation == "has_branch"]
        assert len(has_branch_edges) == 2

    def test_hall_of_fame_entry_with_an_agent_gets_an_achieved_edge(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=("nova",),
            research=[],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[_hof("nova")],
            decision_vault=[],
            case_studies=[],
            strategies=[],
            black_swan_events=[],
            economic_reports=[],
        )
        edge = next(e for e in graph.edges if e.relation == "achieved")
        assert edge.source == "agent-nova"

    def test_hall_of_fame_entry_with_no_agent_gets_no_achieved_edge(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=(),
            research=[],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[_hof(None)],
            decision_vault=[],
            case_studies=[],
            strategies=[],
            black_swan_events=[],
            economic_reports=[],
        )
        assert not any(e.relation == "achieved" for e in graph.edges)
        assert any(n.type == "hall_of_fame" for n in graph.nodes)

    def test_coach_report_links_to_its_real_top_ranked_agent(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=("nova",),
            research=[],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[_coach_report("nova")],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[],
            strategies=[],
            black_swan_events=[],
            economic_reports=[],
        )
        edge = next(e for e in graph.edges if e.relation == "ranked_top_agent")
        assert edge.source == "agent-nova"

    def test_executive_review_links_every_agent_in_its_real_department_activity(
        self,
    ) -> None:
        graph = build_knowledge_graph(
            agent_ids=("nova", "scout"),
            research=[],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[_review(["nova", "scout"])],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[],
            strategies=[],
            black_swan_events=[],
            economic_reports=[],
        )
        featured_edges = [e for e in graph.edges if e.relation == "featured_in"]
        assert {e.source for e in featured_edges} == {"agent-nova", "agent-scout"}

    def test_generated_at_is_a_real_timestamp(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=(),
            research=[],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[],
            strategies=[],
            black_swan_events=[],
            economic_reports=[],
        )
        assert graph.generated_at


# v0.7 Design Bible Chapter 61 — the three new node types.
class TestKnowledgeGraphChapter61Extension:
    def test_case_study_becomes_a_node(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=(),
            research=[],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[_case_study("cs-1")],
            strategies=[],
            black_swan_events=[],
            economic_reports=[],
        )
        cs_nodes = [n for n in graph.nodes if n.type == "case_study"]
        assert len(cs_nodes) == 1
        assert cs_nodes[0].id == "casestudy-cs-1"

    def test_closed_trade_becomes_a_node(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=(),
            research=[],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[_vault_entry("v1", "AAPL")],
            case_studies=[],
            strategies=[],
            black_swan_events=[],
            economic_reports=[],
        )
        trade_nodes = [n for n in graph.nodes if n.type == "trade"]
        assert len(trade_nodes) == 1
        assert trade_nodes[0].label == "AAPL"

    def test_trade_with_a_real_case_study_id_gets_a_documented_by_edge(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=(),
            research=[],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[_vault_entry("v1", "AAPL", case_study_id="cs-1")],
            case_studies=[_case_study("cs-1")],
            strategies=[],
            black_swan_events=[],
            economic_reports=[],
        )
        edge = next(e for e in graph.edges if e.relation == "documented_by")
        assert edge.source == "trade-v1"
        assert edge.target == "casestudy-cs-1"

    def test_trade_with_a_case_study_id_not_in_the_real_list_gets_no_edge(self) -> None:
        # The linked case study was evicted from the capped list — never
        # fabricate an edge to a node that doesn't exist in this graph.
        graph = build_knowledge_graph(
            agent_ids=(),
            research=[],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[_vault_entry("v1", "AAPL", case_study_id="evicted")],
            case_studies=[],
            strategies=[],
            black_swan_events=[],
            economic_reports=[],
        )
        assert not any(e.relation == "documented_by" for e in graph.edges)

    def test_trade_and_research_sharing_a_real_symbol_get_a_same_symbol_edge(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=("nova",),
            research=[_research("nova", "AAPL")],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[_vault_entry("v1", "AAPL")],
            case_studies=[],
            strategies=[],
            black_swan_events=[],
            economic_reports=[],
        )
        edge = next(e for e in graph.edges if e.relation == "same_symbol")
        assert edge.source == "trade-v1"
        assert edge.target.startswith("research-")

    def test_trade_and_research_with_different_symbols_get_no_same_symbol_edge(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=("nova",),
            research=[_research("nova", "MSFT")],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[_vault_entry("v1", "AAPL")],
            case_studies=[],
            strategies=[],
            black_swan_events=[],
            economic_reports=[],
        )
        assert not any(e.relation == "same_symbol" for e in graph.edges)

    def test_strategy_becomes_a_node_and_links_to_its_real_creator(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=("nova",),
            research=[],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[],
            strategies=[_strategy("s1", "nova")],
            black_swan_events=[],
            economic_reports=[],
        )
        strategy_nodes = [n for n in graph.nodes if n.type == "strategy"]
        assert len(strategy_nodes) == 1
        edge = next(e for e in graph.edges if e.relation == "created")
        assert edge.source == "agent-nova"
        assert edge.target == "strategy-s1"

    def test_strategy_still_in_the_idea_stage_is_not_a_node(self) -> None:
        # Mirrors the existing research filter — no real work behind an
        # unstarted idea yet to graph.
        graph = build_knowledge_graph(
            agent_ids=("nova",),
            research=[],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[],
            strategies=[_strategy("s1", "nova", stage="idea")],
            black_swan_events=[],
            economic_reports=[],
        )
        assert not any(n.type == "strategy" for n in graph.nodes)

    def test_strategy_and_research_sharing_a_real_category_get_a_same_category_edge(
        self,
    ) -> None:
        graph = build_knowledge_graph(
            agent_ids=("nova",),
            research=[_research("nova", "AAPL", category="stock")],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[],
            strategies=[_strategy("s1", "nova", category="stock")],
            black_swan_events=[],
            economic_reports=[],
        )
        edge = next(e for e in graph.edges if e.relation == "same_category")
        assert edge.source == "strategy-s1"
        assert edge.target.startswith("research-")

    def test_strategy_and_research_with_different_categories_get_no_same_category_edge(
        self,
    ) -> None:
        graph = build_knowledge_graph(
            agent_ids=("nova",),
            research=[_research("nova", "BTC-USD", category="bitcoin")],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[],
            strategies=[_strategy("s1", "nova", category="stock")],
            black_swan_events=[],
            economic_reports=[],
        )
        assert not any(e.relation == "same_category" for e in graph.edges)


class TestModelValidationOnStrategyNodes:
    """Quantitative Research & Intelligence System, Piece 6 — a strategy
    node's subtitle names Meridian/CIO's real latest ModelValidationReport
    verdict when one exists for that strategy."""

    def test_strategy_with_a_real_validation_report_shows_its_verdict(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=("nova",),
            research=[],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[],
            strategies=[_strategy("s1", "nova")],
            black_swan_events=[],
            economic_reports=[],
            model_validations=[_validation("s1", verdict="rejected")],
        )
        node = next(n for n in graph.nodes if n.type == "strategy")
        assert "Model Validation: rejected" in node.subtitle

    def test_strategy_with_no_validation_report_has_no_validation_text(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=("nova",),
            research=[],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[],
            strategies=[_strategy("s1", "nova")],
            black_swan_events=[],
            economic_reports=[],
        )
        node = next(n for n in graph.nodes if n.type == "strategy")
        assert "Model Validation" not in node.subtitle

    def test_validation_for_a_different_strategy_is_not_shown(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=("nova",),
            research=[],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[],
            strategies=[_strategy("s1", "nova")],
            black_swan_events=[],
            economic_reports=[],
            model_validations=[_validation("s2", verdict="rejected")],
        )
        node = next(n for n in graph.nodes if n.type == "strategy")
        assert "Model Validation" not in node.subtitle

    def test_the_latest_report_wins_when_a_strategy_has_more_than_one(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=("nova",),
            research=[],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[],
            strategies=[_strategy("s1", "nova")],
            black_swan_events=[],
            economic_reports=[],
            model_validations=[
                _validation("s1", verdict="needs_more_evidence"),
                _validation("s1", verdict="approved"),
            ],
        )
        node = next(n for n in graph.nodes if n.type == "strategy")
        assert "Model Validation: approved" in node.subtitle


class TestEconomicEventNodes:
    """Design Bible Chapter 74 Part 1's one real Knowledge Graph
    addition: economic_event nodes, same-day-edged to trade/case_study
    nodes — never a causal claim, see module docstring."""

    def test_economic_report_becomes_an_economic_event_node(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=(),
            research=[],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[],
            strategies=[],
            black_swan_events=[],
            economic_reports=[_economic_report("econ-1", sim_day=5)],
        )
        node = next(n for n in graph.nodes if n.type == "economic_event")
        assert node.id == "econevent-econ-1"

    def test_economic_event_links_to_case_study_filed_the_same_sim_day(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=(),
            research=[],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[_case_study("cs1")],  # simDay=1
            strategies=[],
            black_swan_events=[],
            economic_reports=[_economic_report("econ-1", sim_day=1)],
        )
        edge = next(e for e in graph.edges if e.relation == "same_day")
        assert edge.source == "econevent-econ-1"
        assert edge.target == "casestudy-cs1"

    def test_economic_event_on_a_different_sim_day_gets_no_same_day_edge(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=(),
            research=[],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[_case_study("cs1")],  # simDay=1
            strategies=[],
            black_swan_events=[],
            economic_reports=[_economic_report("econ-2", sim_day=9)],
        )
        assert not any(e.relation == "same_day" for e in graph.edges)


class TestResearchExperimentNodes:
    """CEO directive "Quant Research Factory / Strategy Discovery
    Engine," Phase 15 — one real research_experiment node per persisted
    QuantResearchExperiment, linked to its real researcher agent and,
    when a real match exists, to the strategy node testing the same
    real compiled definition."""

    def test_a_filed_experiment_becomes_a_research_experiment_node(self) -> None:
        definition = compile_strategy_text(name="KG Test Strategy", source_text=_STRATEGY_TEXT)
        record = run_research_experiment(definition, symbols=["AAPL"])
        experiment = file_quant_research_experiment(
            record, experiment_id="exp-kg-1", hypothesis="A real test hypothesis.", researcher_agent_id="quant", created_at="2026-01-01T00:00:00+00:00"
        )
        graph = build_knowledge_graph(
            agent_ids=("quant",),
            research=[],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[],
            strategies=[],
            black_swan_events=[],
            economic_reports=[],
            quant_research_experiments=[experiment],
        )
        node = next(n for n in graph.nodes if n.type == "research_experiment")
        assert node.id == "researchexp-exp-kg-1"
        assert node.label == definition.name

    def test_the_researcher_agent_gets_a_real_researched_edge(self) -> None:
        definition = compile_strategy_text(name="KG Test Strategy 2", source_text=_STRATEGY_TEXT)
        record = run_research_experiment(definition, symbols=["AAPL"])
        experiment = file_quant_research_experiment(
            record, experiment_id="exp-kg-2", hypothesis="A real test hypothesis.", researcher_agent_id="nova", created_at="2026-01-01T00:00:00+00:00"
        )
        graph = build_knowledge_graph(
            agent_ids=("nova",),
            research=[],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[],
            strategies=[],
            black_swan_events=[],
            economic_reports=[],
            quant_research_experiments=[experiment],
        )
        edge = next(e for e in graph.edges if e.relation == "researched" and e.target == "researchexp-exp-kg-2")
        assert edge.source == "agent-nova"

    def test_an_experiment_links_to_the_strategy_sharing_its_real_compiled_definition_id(self) -> None:
        definition = compile_strategy_text(name="KG Test Strategy 3", source_text=_STRATEGY_TEXT)
        record = run_research_experiment(definition, symbols=["AAPL"])
        experiment = file_quant_research_experiment(
            record, experiment_id="exp-kg-3", hypothesis="A real test hypothesis.", researcher_agent_id="quant", created_at="2026-01-01T00:00:00+00:00"
        )
        graph = build_knowledge_graph(
            agent_ids=("quant",),
            research=[],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[],
            strategies=[_strategy("s1", "quant", compiled_definition_id=definition.id)],
            black_swan_events=[],
            economic_reports=[],
            quant_research_experiments=[experiment],
        )
        edge = next(e for e in graph.edges if e.relation == "tested")
        assert edge.source == "researchexp-exp-kg-3"
        assert edge.target == "strategy-s1"

    def test_an_experiment_with_no_matching_strategy_gets_no_tested_edge(self) -> None:
        definition = compile_strategy_text(name="KG Test Strategy 4", source_text=_STRATEGY_TEXT)
        record = run_research_experiment(definition, symbols=["AAPL"])
        experiment = file_quant_research_experiment(
            record, experiment_id="exp-kg-4", hypothesis="A real test hypothesis.", researcher_agent_id="quant", created_at="2026-01-01T00:00:00+00:00"
        )
        graph = build_knowledge_graph(
            agent_ids=("quant",),
            research=[],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[],
            strategies=[_strategy("s1", "quant", compiled_definition_id="some-other-definition")],
            black_swan_events=[],
            economic_reports=[],
            quant_research_experiments=[experiment],
        )
        assert not any(e.relation == "tested" for e in graph.edges)

    def test_omitting_quant_research_experiments_produces_no_research_experiment_nodes(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=(),
            research=[],
            academy_completed_projects=[],
            agent_knowledge={},
            executive_reviews=[],
            coach_reports=[],
            hall_of_fame=[],
            decision_vault=[],
            case_studies=[],
            strategies=[],
            black_swan_events=[],
            economic_reports=[],
        )
        assert not any(n.type == "research_experiment" for n in graph.nodes)
