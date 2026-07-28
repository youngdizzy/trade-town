"""KnowledgeGraph — v0.7 Feature 25.5, the Company Knowledge Graph.

Connects every already-real, already-persisted record this codebase
produces (completed research, completed Academy projects, Executive
Reviews, Coach reports, Hall of Fame entries, and the agents/knowledge
branches behind them) into one queryable node-edge graph. Computed fresh
on every request (like app/whatif.py) rather than persisted — the
underlying records are already persisted and capped elsewhere, so
recomputing the graph's structure from them on demand is a derived view,
not a second, possibly-stale store of the same data.

Every edge traces to a real, checkable shared attribute: a research
item's own `assigned_agent`, two research items sharing the same real
`category` (or two Academy projects sharing the same real `topic`,
ordered by their own real `updated_at` into a "builds_on" chain), an
agent's own real Knowledge Branch, an agent appearing in an
ExecutiveReview's real `department_activity`, or a Coach report's real
top-ranked agent. Nothing here is a fabricated or invented connection.

Scope cut: this graph does NOT auto-generate new Academy lessons/
seminars/museum exhibits/quizzes/company presentations from research —
this codebase has no content-generation capability, and
`education.py`'s ten lessons are a fixed, hand-authored curriculum with
no real thematic overlap with the six Academy research topics (checked
directly: education topics are all technical trading mechanics —
candlesticks, stop-loss, position sizing — while Academy topics are
market history/psychology/economics, a genuinely different subject
area), so no AcademyProject-to-EducationLesson edge is fabricated either.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from itertools import groupby

from app.agents import AGENT_PROFILES
from app.schemas import (
    AcademyProject,
    AgentId,
    AgentKnowledgeState,
    CoachReport,
    ExecutiveReview,
    HallOfFameEntry,
    KnowledgeEdge,
    KnowledgeGraph,
    KnowledgeNode,
    ResearchItem,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _builds_on_chain(items: list[tuple[str, str, str]]) -> list[KnowledgeEdge]:
    """items: list of (node_id, group_key, updated_at). Within each group
    (a shared research category or Academy topic), links each item to the
    one immediately before it in real time — a real "this came after
    that, on the same subject" chain, not a fabricated dependency."""
    edges: list[KnowledgeEdge] = []
    keyed = sorted(items, key=lambda t: t[1])
    for _key, group in groupby(keyed, key=lambda t: t[1]):
        ordered = sorted(group, key=lambda t: t[2])
        for earlier, later in zip(ordered, ordered[1:]):
            edges.append(KnowledgeEdge(source=later[0], target=earlier[0], relation="builds_on", label="builds on"))
    return edges


def build_knowledge_graph(
    *,
    agent_ids: tuple[AgentId, ...],
    research: list[ResearchItem],
    academy_completed_projects: list[AcademyProject],
    agent_knowledge: dict[AgentId, AgentKnowledgeState],
    executive_reviews: list[ExecutiveReview],
    coach_reports: list[CoachReport],
    hall_of_fame: list[HallOfFameEntry],
) -> KnowledgeGraph:
    nodes: list[KnowledgeNode] = []
    edges: list[KnowledgeEdge] = []

    for agent_id in agent_ids:
        profile = AGENT_PROFILES[agent_id]
        nodes.append(KnowledgeNode(id=f"agent-{agent_id}", type="agent", label=profile.name, subtitle=profile.occupation))

    seen_branches: set[str] = set()
    for agent_id, state in agent_knowledge.items():
        branch_id = f"branch-{_slug(state.branch)}"
        if branch_id not in seen_branches:
            seen_branches.add(branch_id)
            nodes.append(KnowledgeNode(id=branch_id, type="branch", label=state.branch, subtitle="Knowledge Branch"))
        edges.append(KnowledgeEdge(source=f"agent-{agent_id}", target=branch_id, relation="has_branch", label=f"{state.level.title()} (Tier {state.tier})"))

    research_chain_items: list[tuple[str, str, str]] = []
    for item in research:
        if item.status != "completed":
            continue
        node_id = f"research-{item.id}"
        nodes.append(
            KnowledgeNode(
                id=node_id,
                type="research",
                label=item.title,
                subtitle=f"{item.symbol or item.category} · {item.confidence:.0f}% confidence",
                timestamp=item.updated_at,
            )
        )
        edges.append(KnowledgeEdge(source=f"agent-{item.assigned_agent}", target=node_id, relation="researched", label="researched"))
        research_chain_items.append((node_id, item.category, item.updated_at))
    edges.extend(_builds_on_chain(research_chain_items))

    academy_chain_items: list[tuple[str, str, str]] = []
    for project in academy_completed_projects:
        node_id = f"academy-{project.id}"
        nodes.append(
            KnowledgeNode(
                id=node_id,
                type="academy_project",
                label=project.title,
                subtitle=project.topic.replace("_", " ").title(),
                timestamp=project.updated_at,
            )
        )
        edges.append(KnowledgeEdge(source=f"agent-{project.assigned_agent}", target=node_id, relation="completed", label="completed"))
        academy_chain_items.append((node_id, project.topic, project.updated_at))
    edges.extend(_builds_on_chain(academy_chain_items))

    for review in executive_reviews:
        node_id = f"review-{review.id}"
        nodes.append(
            KnowledgeNode(
                id=node_id,
                type="executive_review",
                label="Executive Review",
                subtitle=f"Score {review.company_score:.0f}/100 ({review.company_health_tier.replace('_', ' ')})",
                timestamp=review.created_at,
            )
        )
        for activity in review.department_activity:
            edges.append(KnowledgeEdge(source=f"agent-{activity.agent_id}", target=node_id, relation="featured_in", label="featured in"))

    for report in coach_reports:
        node_id = f"coach-{report.id}"
        nodes.append(
            KnowledgeNode(
                id=node_id,
                type="coach_report",
                label=f"{report.period.title()} Coach Report",
                subtitle=f"Score {report.company_score:.0f}/100",
                timestamp=report.created_at,
            )
        )
        if report.agent_rankings:
            top = report.agent_rankings[0]
            edges.append(KnowledgeEdge(source=f"agent-{top.agent_id}", target=node_id, relation="ranked_top_agent", label="top ranked"))

    for entry in hall_of_fame:
        node_id = f"hof-{entry.id}"
        nodes.append(
            KnowledgeNode(
                id=node_id,
                type="hall_of_fame",
                label=entry.title,
                subtitle=entry.category.replace("_", " ").title(),
                timestamp=entry.achieved_at,
            )
        )
        if entry.agent_id is not None:
            edges.append(KnowledgeEdge(source=f"agent-{entry.agent_id}", target=node_id, relation="achieved", label="achieved"))

    return KnowledgeGraph(nodes=nodes, edges=edges, generatedAt=_now_iso())
