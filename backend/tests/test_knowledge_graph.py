"""Covers app/knowledge_graph.py — v0.7 Feature 25.5, the Company
Knowledge Graph. Every edge here must trace to a real, checkable shared
attribute on the underlying records; nothing here is a fabricated or
invented connection.
"""
from __future__ import annotations

from app.knowledge_graph import build_knowledge_graph
from app.schemas import AcademyProject, AgentKnowledgeState, CoachReport, ExecutiveReview, HallOfFameEntry, ResearchItem


def _research(agent: str, symbol: str, category: str = "stock", updated_at: str = "2026-01-01T00:00:00+00:00", status: str = "completed") -> ResearchItem:
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


def _project(agent: str, topic: str, title: str, updated_at: str = "2026-01-01T00:00:00+00:00") -> AcademyProject:
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
    return HallOfFameEntry(id=f"hof-{title}", category="winning_streak", title=title, description="test", agentId=agent_id, value=5.0, achievedAt="2026-01-01T00:00:00+00:00")  # type: ignore[arg-type]


def _coach_report(top_agent: str) -> CoachReport:
    from app.schemas import AgentScore

    return CoachReport(
        id="report-1",
        period="weekly",
        companyScore=60.0,
        agentRankings=[AgentScore(agentId=top_agent, score=90.0, researchAccuracy=90.0, confidenceCalibration=90.0)],  # type: ignore[arg-type]
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


def _review(agent_ids: list[str]) -> ExecutiveReview:
    from app.schemas import DepartmentActivity

    return ExecutiveReview(
        id="review-1",
        companyScore=60.0,
        companyScoreChange=0.0,
        companyHealthTier="stable",
        departmentActivity=[DepartmentActivity(agentId=a, researchCompleted=1, decisionsInvolved=0) for a in agent_ids],  # type: ignore[arg-type]
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
            agent_ids=("scout", "cio"), research=[], academy_completed_projects=[], agent_knowledge={},
            executive_reviews=[], coach_reports=[], hall_of_fame=[],
        )
        agent_node_ids = {n.id for n in graph.nodes if n.type == "agent"}
        assert agent_node_ids == {"agent-scout", "agent-cio"}

    def test_completed_research_becomes_a_node_linked_to_its_real_agent(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=("nova",), research=[_research("nova", "AAPL")], academy_completed_projects=[], agent_knowledge={},
            executive_reviews=[], coach_reports=[], hall_of_fame=[],
        )
        research_nodes = [n for n in graph.nodes if n.type == "research"]
        assert len(research_nodes) == 1
        edge = next(e for e in graph.edges if e.relation == "researched")
        assert edge.source == "agent-nova"
        assert edge.target == research_nodes[0].id

    def test_in_progress_research_is_not_a_node(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=("nova",), research=[_research("nova", "AAPL", status="in_progress")], academy_completed_projects=[],
            agent_knowledge={}, executive_reviews=[], coach_reports=[], hall_of_fame=[],
        )
        assert not any(n.type == "research" for n in graph.nodes)

    def test_same_category_research_gets_a_real_builds_on_chain(self) -> None:
        older = _research("nova", "AAPL", category="stock", updated_at="2026-01-01T00:00:00+00:00")
        newer = _research("scout", "MSFT", category="stock", updated_at="2026-02-01T00:00:00+00:00")
        graph = build_knowledge_graph(
            agent_ids=("nova", "scout"), research=[older, newer], academy_completed_projects=[], agent_knowledge={},
            executive_reviews=[], coach_reports=[], hall_of_fame=[],
        )
        builds_on = [e for e in graph.edges if e.relation == "builds_on"]
        assert len(builds_on) == 1
        assert builds_on[0].source == f"research-{newer.id}"
        assert builds_on[0].target == f"research-{older.id}"

    def test_different_category_research_gets_no_builds_on_edge(self) -> None:
        a = _research("nova", "AAPL", category="stock")
        b = _research("scout", "BTC-USD", category="bitcoin")
        graph = build_knowledge_graph(
            agent_ids=("nova", "scout"), research=[a, b], academy_completed_projects=[], agent_knowledge={},
            executive_reviews=[], coach_reports=[], hall_of_fame=[],
        )
        assert not any(e.relation == "builds_on" for e in graph.edges)

    def test_completed_academy_project_becomes_a_node_linked_to_its_real_agent(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=("scout",), research=[], academy_completed_projects=[_project("scout", "market_history", "Studying Black Monday")],
            agent_knowledge={}, executive_reviews=[], coach_reports=[], hall_of_fame=[],
        )
        academy_nodes = [n for n in graph.nodes if n.type == "academy_project"]
        assert len(academy_nodes) == 1
        edge = next(e for e in graph.edges if e.relation == "completed")
        assert edge.source == "agent-scout"
        assert edge.target == academy_nodes[0].id

    def test_agent_knowledge_creates_a_shared_branch_node(self) -> None:
        knowledge = {
            "echo": AgentKnowledgeState(agentId="echo", branch="Technical Analysis", points=10.0, tier=1),  # type: ignore[arg-type]
            "pulse": AgentKnowledgeState(agentId="pulse", branch="Statistics", points=5.0, tier=0),  # type: ignore[arg-type]
        }
        graph = build_knowledge_graph(
            agent_ids=("echo", "pulse"), research=[], academy_completed_projects=[], agent_knowledge=knowledge,
            executive_reviews=[], coach_reports=[], hall_of_fame=[],
        )
        branch_nodes = [n for n in graph.nodes if n.type == "branch"]
        assert len(branch_nodes) == 2
        has_branch_edges = [e for e in graph.edges if e.relation == "has_branch"]
        assert len(has_branch_edges) == 2

    def test_hall_of_fame_entry_with_an_agent_gets_an_achieved_edge(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=("nova",), research=[], academy_completed_projects=[], agent_knowledge={},
            executive_reviews=[], coach_reports=[], hall_of_fame=[_hof("nova")],
        )
        edge = next(e for e in graph.edges if e.relation == "achieved")
        assert edge.source == "agent-nova"

    def test_hall_of_fame_entry_with_no_agent_gets_no_achieved_edge(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=(), research=[], academy_completed_projects=[], agent_knowledge={},
            executive_reviews=[], coach_reports=[], hall_of_fame=[_hof(None)],
        )
        assert not any(e.relation == "achieved" for e in graph.edges)
        assert any(n.type == "hall_of_fame" for n in graph.nodes)

    def test_coach_report_links_to_its_real_top_ranked_agent(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=("nova",), research=[], academy_completed_projects=[], agent_knowledge={},
            executive_reviews=[], coach_reports=[_coach_report("nova")], hall_of_fame=[],
        )
        edge = next(e for e in graph.edges if e.relation == "ranked_top_agent")
        assert edge.source == "agent-nova"

    def test_executive_review_links_every_agent_in_its_real_department_activity(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=("nova", "scout"), research=[], academy_completed_projects=[], agent_knowledge={},
            executive_reviews=[_review(["nova", "scout"])], coach_reports=[], hall_of_fame=[],
        )
        featured_edges = [e for e in graph.edges if e.relation == "featured_in"]
        assert {e.source for e in featured_edges} == {"agent-nova", "agent-scout"}

    def test_generated_at_is_a_real_timestamp(self) -> None:
        graph = build_knowledge_graph(
            agent_ids=(), research=[], academy_completed_projects=[], agent_knowledge={},
            executive_reviews=[], coach_reports=[], hall_of_fame=[],
        )
        assert graph.generated_at
