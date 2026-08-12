"""KnowledgeGraph — v0.7 Feature 25.5, the Company Knowledge Graph.

Connects every already-real, already-persisted record this codebase
produces (completed research, completed Academy projects, Executive
Reviews, Coach reports, Hall of Fame entries, closed trades, filed case
studies, strategies, and the agents/knowledge branches behind them) into
one queryable node-edge graph. Computed fresh on every request (like
app/whatif.py) rather than persisted — the underlying records are
already persisted and capped elsewhere, so recomputing the graph's
structure from them on demand is a derived view, not a second, possibly-
stale store of the same data.

Every edge traces to a real, checkable shared attribute: a research
item's own `assigned_agent`, two research items sharing the same real
`category` (or two Academy projects sharing the same real `topic`,
ordered by their own real `updated_at` into a "builds_on" chain), an
agent's own real Knowledge Branch, an agent appearing in an
ExecutiveReview's real `department_activity`, a Coach report's real
top-ranked agent, a closed trade's own real `caseStudyId` link to its
filed CaseStudy, a closed trade and a completed research item sharing
the same real `symbol` (v0.7 Design Bible Chapter 61 — labeled
"same symbol", never claimed as "this research caused this trade", since
no field anywhere actually links a specific ResearchItem to a specific
trade), a Strategy and a completed research item sharing the same real
`category`/`focusCategory` (labeled "same category", same non-causal
honesty boundary), or a Strategy's own real `createdBy` agent. Nothing
here is a fabricated or invented connection.

Scope cut: this graph does NOT auto-generate new Academy lessons/
seminars/museum exhibits/quizzes/company presentations from research —
this codebase has no content-generation capability, and
`education.py`'s ten lessons are a fixed, hand-authored curriculum with
no real thematic overlap with the six Academy research topics (checked
directly: education topics are all technical trading mechanics —
candlesticks, stop-loss, position sizing — while Academy topics are
market history/psychology/economics, a genuinely different subject
area), so no AcademyProject-to-EducationLesson edge is fabricated either.

v0.7 Design Bible Chapter 61 — three new node types (`trade`,
`case_study`, `strategy`), each backed by an already-real object
(`DecisionVaultEntry`, `CaseStudy`, `Strategy`) this codebase already
persists elsewhere — the exact gap the chapter's own Implementation
Notes named as "the single largest real, closeable piece of work."
Strategies still in the raw `idea` stage are not graphed, mirroring the
existing research filter (only `completed` research items become
nodes) — an unstarted idea has no real work behind it yet to connect."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from itertools import groupby

from app.agents import AGENT_PROFILES
from app.schemas import (
    AcademyProject,
    AgentId,
    AgentKnowledgeState,
    BlackSwanEventRecord,
    CaseStudy,
    CoachReport,
    DecisionVaultEntry,
    EconomicIntelligenceReport,
    ExecutiveReview,
    HallOfFameEntry,
    KnowledgeEdge,
    KnowledgeGraph,
    KnowledgeNode,
    ResearchItem,
    Strategy,
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
            edges.append(
                KnowledgeEdge(
                    source=later[0],
                    target=earlier[0],
                    relation="builds_on",
                    label="builds on",
                )
            )
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
    decision_vault: list[DecisionVaultEntry],
    case_studies: list[CaseStudy],
    strategies: list[Strategy],
    black_swan_events: list[BlackSwanEventRecord],
    economic_reports: list[EconomicIntelligenceReport],
) -> KnowledgeGraph:
    nodes: list[KnowledgeNode] = []
    edges: list[KnowledgeEdge] = []

    for agent_id in agent_ids:
        profile = AGENT_PROFILES[agent_id]
        nodes.append(
            KnowledgeNode(
                id=f"agent-{agent_id}",
                type="agent",
                label=profile.name,
                subtitle=profile.occupation,
            )
        )

    seen_branches: set[str] = set()
    for agent_id, state in agent_knowledge.items():
        branch_id = f"branch-{_slug(state.branch)}"
        if branch_id not in seen_branches:
            seen_branches.add(branch_id)
            nodes.append(
                KnowledgeNode(
                    id=branch_id,
                    type="branch",
                    label=state.branch,
                    subtitle="Knowledge Branch",
                )
            )
        edges.append(
            KnowledgeEdge(
                source=f"agent-{agent_id}",
                target=branch_id,
                relation="has_branch",
                label=f"{state.level.title()} (Tier {state.tier})",
            )
        )

    # v0.7 Design Bible Chapter 61 — tracked so trade/strategy nodes below
    # can connect to completed research sharing a real symbol/category,
    # without a second pass over `research`.
    research_by_symbol: dict[str, list[str]] = {}
    research_by_category: dict[str, list[str]] = {}
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
        edges.append(
            KnowledgeEdge(
                source=f"agent-{item.assigned_agent}",
                target=node_id,
                relation="researched",
                label="researched",
            )
        )
        research_chain_items.append((node_id, item.category, item.updated_at))
        if item.symbol:
            research_by_symbol.setdefault(item.symbol, []).append(node_id)
        research_by_category.setdefault(item.category, []).append(node_id)
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
        edges.append(
            KnowledgeEdge(
                source=f"agent-{project.assigned_agent}",
                target=node_id,
                relation="completed",
                label="completed",
            )
        )
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
            edges.append(
                KnowledgeEdge(
                    source=f"agent-{activity.agent_id}",
                    target=node_id,
                    relation="featured_in",
                    label="featured in",
                )
            )

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
            edges.append(
                KnowledgeEdge(
                    source=f"agent-{top.agent_id}",
                    target=node_id,
                    relation="ranked_top_agent",
                    label="top ranked",
                )
            )

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
            edges.append(
                KnowledgeEdge(
                    source=f"agent-{entry.agent_id}",
                    target=node_id,
                    relation="achieved",
                    label="achieved",
                )
            )

    # v0.7 Design Bible Chapter 61 — case studies first, so trade nodes
    # (below) can look up their own real caseStudyId. Design Bible
    # Chapter 74 Part 1 tracks each node's real simDay here too, so the
    # economic_event nodes below can draw a real same-day edge without a
    # second pass.
    case_study_ids = {cs.id for cs in case_studies}
    same_day_node_ids: dict[int, list[str]] = {}
    for cs in case_studies:
        node_id = f"casestudy-{cs.id}"
        nodes.append(
            KnowledgeNode(
                id=node_id,
                type="case_study",
                label=cs.title,
                subtitle=cs.category.replace("_", " ").title(),
                timestamp=cs.created_at,
            )
        )
        same_day_node_ids.setdefault(cs.sim_day, []).append(node_id)

    for vault_entry in decision_vault:
        node_id = f"trade-{vault_entry.id}"
        nodes.append(
            KnowledgeNode(
                id=node_id,
                type="trade",
                label=vault_entry.symbol,
                subtitle=f"Grade {vault_entry.decision_grade} · {vault_entry.pnl_pct:+.1f}%",
                timestamp=vault_entry.created_at,
            )
        )
        same_day_node_ids.setdefault(vault_entry.sim_day, []).append(node_id)
        # A real, direct 1:1 link already stored on the vault entry —
        # never a fuzzy match.
        if vault_entry.case_study_id is not None and vault_entry.case_study_id in case_study_ids:
            edges.append(
                KnowledgeEdge(
                    source=node_id,
                    target=f"casestudy-{vault_entry.case_study_id}",
                    relation="documented_by",
                    label="documented by",
                )
            )
        # Descriptive, not causal — see module docstring for why this is
        # "same symbol" rather than a claim that this research caused
        # this specific trade.
        for research_node_id in research_by_symbol.get(vault_entry.symbol, []):
            edges.append(
                KnowledgeEdge(
                    source=node_id,
                    target=research_node_id,
                    relation="same_symbol",
                    label="same symbol",
                )
            )

    for strategy in strategies:
        if strategy.stage == "idea":
            continue  # mirrors the research filter — no real work behind an unstarted idea yet
        node_id = f"strategy-{strategy.id}"
        nodes.append(
            KnowledgeNode(
                id=node_id,
                type="strategy",
                label=strategy.name,
                subtitle=f"{strategy.stage.replace('_', ' ').title()} · {strategy.focus_category}",
                timestamp=strategy.created_at,
            )
        )
        # Strategy.createdBy is a real, direct field — this edge is a
        # literal fact, not an inference.
        edges.append(
            KnowledgeEdge(
                source=f"agent-{strategy.created_by}",
                target=node_id,
                relation="created",
                label="created",
            )
        )
        for research_node_id in research_by_category.get(strategy.focus_category, []):
            edges.append(
                KnowledgeEdge(
                    source=node_id,
                    target=research_node_id,
                    relation="same_category",
                    label="same category",
                )
            )

    # Design Bible Chapter 72 — one real node per completed Defensive
    # Mode episode. Edges are "same symbol" only, the identical
    # non-causal honesty rule the trade nodes above already use — never
    # a claim that this episode was "caused by" a specific symbol.
    for event in black_swan_events:
        node_id = f"blackswan-{event.id}"
        nodes.append(
            KnowledgeNode(
                id=node_id,
                type="black_swan_event",
                label=f"Defensive Mode — {event.peak_tier.title()}",
                subtitle=f"{event.duration_sim_minutes} sim min · equity {event.equity_change_pct:+.1f}%",
                timestamp=event.created_at,
            )
        )
        for symbol in event.affected_symbols:
            for research_node_id in research_by_symbol.get(symbol, []):
                edges.append(
                    KnowledgeEdge(
                        source=node_id,
                        target=research_node_id,
                        relation="same_symbol",
                        label="same symbol",
                    )
                )

    # Design Bible Chapter 74 Part 1 — one real node per daily
    # EconomicIntelligenceReport, linked to any trade/case_study node
    # recorded the same real simDay. A real, checkable temporal
    # proximity only — never a causal claim (see module docstring).
    for econ_report in economic_reports:
        node_id = f"econevent-{econ_report.id}"
        nodes.append(
            KnowledgeNode(
                id=node_id,
                type="economic_event",
                label=econ_report.narrative.headline,
                subtitle=f"Day {econ_report.sim_day} Economic Intelligence Brief",
                timestamp=econ_report.created_at,
            )
        )
        for target_id in same_day_node_ids.get(econ_report.sim_day, []):
            edges.append(
                KnowledgeEdge(
                    source=node_id,
                    target=target_id,
                    relation="same_day",
                    label="same day",
                )
            )

    return KnowledgeGraph(nodes=nodes, edges=edges, generatedAt=_now_iso())
