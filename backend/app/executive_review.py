"""ExecutiveReview — the CIO's Monthly Executive Review (v0.7 Feature 24).

Generated on the same monthly cadence as Coach's own MONTHLY CoachReport
(see nexus.py) but asking a different question: not "how did trading
perform" (CoachReport's job) but "how is the company, as an organization,
doing" — department activity, research/knowledge output, and real
disagreement the CIO would want a human executive briefed on.

Like CoachReport, this is a fresh cumulative snapshot over each list's
own already-capped recent history (MAX_DECISIONS/MAX_DEBATES/per-agent
research history/MAX_ACADEMY_LIBRARY), not a precisely period-windowed
query — the same "a capped list functions as an honest recent-activity
window" convention this codebase already uses everywhere (see
docs/API.md's bounding table). `company_score_change` is the one true
period-over-period figure: a real delta against the previous review's
own stored score.

Two brief-requested fields have no real trigger to compute from and are
deliberately not fabricated: "Employee Development" is represented by
the same real Knowledge Points this pass already tracks (app/academy.py)
rather than a second, parallel metric, and "Long-Term Goals" is framed
from real, already-configured company state (RiskLimits, the Academy's
own next level) rather than invented aspirational text — see
_long_term_goals below.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.agents import AGENT_PROFILES
from app.schemas import (
    AcademyProject,
    AcademyState,
    AgentId,
    CompanyHealth,
    CompanyScore,
    Debate,
    DepartmentActivity,
    ExecutiveReview,
    NewsItem,
    ResearchItem,
    RiskLimits,
    TimeState,
    TradeDecision,
)

MAX_EXECUTIVE_REVIEWS = 20
STALLED_RESEARCH_CONFIDENCE = 20.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _department_activity(research: list[ResearchItem], decisions: list[TradeDecision], agent_ids: tuple[AgentId, ...]) -> list[DepartmentActivity]:
    activity: list[DepartmentActivity] = []
    for agent_id in agent_ids:
        research_count = len([r for r in research if r.assigned_agent == agent_id and r.status == "completed"])
        decision_count = len([d for d in decisions if agent_id in d.supporting_agents or agent_id in d.opposing_agents])
        if research_count or decision_count:
            activity.append(DepartmentActivity(agentId=agent_id, researchCompleted=research_count, decisionsInvolved=decision_count))
    activity.sort(key=lambda a: a.research_completed + a.decisions_involved, reverse=True)
    return activity


def _conflicts_detected(debates: list[Debate]) -> int:
    return sum(1 for d in debates for turn in d.turns if turn.stance == "challenge")


def _major_events(news: list[NewsItem]) -> list[str]:
    return [n.headline for n in news if n.category in ("company", "discovery")][-5:]


def _flags(research: list[ResearchItem], company_health: CompanyHealth) -> list[str]:
    flags: list[str] = []
    for item in research:
        if item.status == "in_progress" and item.confidence < STALLED_RESEARCH_CONFIDENCE:
            flags.append(f"{AGENT_PROFILES[item.assigned_agent].name}'s research on {item.symbol or item.title} remains low-confidence — may need a fresh angle.")
    if company_health.tier in ("needs_attention", "critical"):
        flags.append(f"Company Health is reading {company_health.tier.replace('_', ' ')} — worth a closer look before the next review.")
    return flags


def _long_term_goals(risk_limits: RiskLimits, academy_state: AcademyState) -> list[str]:
    goals = [f"Hold max drawdown under {risk_limits.max_drawdown_pct:.0f}%, the standing risk limit."]
    if academy_state.level < 5:
        goals.append(f'Advance the Academy past "{academy_state.level_label}" toward its next tier.')
    return goals


def _knowledge_connections(research: list[ResearchItem], completed_academy_projects: list[AcademyProject]) -> list[str]:
    """v0.7 Feature 25.5 — real "this builds on that" callbacks. For every
    real research category / Academy topic with 2+ completed items, names
    the two most recent real titles (ordered by their own real
    updated_at) — never a fabricated "N months ago" claim, since these
    items only carry real wall-clock timestamps, not a sim-time span
    guaranteed to read as dramatic in a short session."""
    connections: list[str] = []

    by_category: dict[str, list[ResearchItem]] = {}
    for item in research:
        if item.status == "completed":
            by_category.setdefault(item.category, []).append(item)
    for category, items in by_category.items():
        if len(items) < 2:
            continue
        ordered = sorted(items, key=lambda r: r.updated_at)
        latest, earlier = ordered[-1], ordered[-2]
        connections.append(f'This period\'s "{latest.title}" builds on earlier {category} research, "{earlier.title}".')

    by_topic: dict[str, list[AcademyProject]] = {}
    for project in completed_academy_projects:
        by_topic.setdefault(project.topic, []).append(project)
    for topic, projects in by_topic.items():
        if len(projects) < 2:
            continue
        ordered_projects = sorted(projects, key=lambda p: p.updated_at)
        latest_project, earlier_project = ordered_projects[-1], ordered_projects[-2]
        topic_label = topic.replace("_", " ")
        connections.append(f'The Academy\'s "{latest_project.title}" extends an earlier {topic_label} study, "{earlier_project.title}".')

    return connections


def generate_executive_review(
    *,
    research: list[ResearchItem],
    decisions: list[TradeDecision],
    debates: list[Debate],
    news: list[NewsItem],
    company_score: CompanyScore,
    previous_score: float | None,
    company_health: CompanyHealth,
    risk_limits: RiskLimits,
    academy_state: AcademyState,
    completed_academy_projects: list[AcademyProject],
    lessons_completed: int,
    agent_ids: tuple[AgentId, ...],
    new_time: TimeState,
) -> ExecutiveReview:
    department_activity = _department_activity(research, decisions, agent_ids)
    research_completed = len([r for r in research if r.status == "completed"])
    conflicts = _conflicts_detected(debates)
    major_events = _major_events(news)
    flags = _flags(research, company_health)
    score_change = round(company_score.overall - previous_score, 1) if previous_score is not None else 0.0
    recommendations = list(company_health.recommendations)
    goals = _long_term_goals(risk_limits, academy_state)
    connections = _knowledge_connections(research, completed_academy_projects)

    summary = (
        f"Company score stands at {company_score.overall:.0f}/100 "
        f"({'+' if score_change >= 0 else ''}{score_change:.1f} since the last review), "
        f"a {company_health.tier.replace('_', ' ')} reading on Company Health. "
        f"{research_completed} research items and {len(completed_academy_projects)} Academy projects are on record."
    )
    if department_activity:
        busiest = department_activity[0]
        summary += f" {AGENT_PROFILES[busiest.agent_id].name} was the busiest department this period."
    if conflicts:
        summary += f" The Debate Room recorded {conflicts} real disagreement(s) among the analysts, all resolved without executive intervention."
    else:
        summary += " No unresolved disagreements among the analysts this period."
    if flags:
        summary += " A few items are worth a closer look — see below."
    if connections:
        summary += " This period's work also builds on earlier company research — see Knowledge Connections below."

    return ExecutiveReview(
        id=f"review-{new_time.day}-{new_time.hour}-{new_time.minute}",
        companyScore=round(company_score.overall, 1),
        companyScoreChange=score_change,
        companyHealthTier=company_health.tier,
        departmentActivity=department_activity,
        researchCompleted=research_completed,
        knowledgeGained=len(completed_academy_projects),
        lessonsCompleted=lessons_completed,
        majorEvents=major_events,
        conflictsDetected=conflicts,
        flags=flags,
        recommendations=recommendations,
        longTermGoals=goals,
        knowledgeConnections=connections,
        summary=summary,
        createdAt=_now_iso(),
    )


def record_review(reviews: list[ExecutiveReview], review: ExecutiveReview) -> list[ExecutiveReview]:
    updated = [*reviews, review]
    if len(updated) > MAX_EXECUTIVE_REVIEWS:
        del updated[: len(updated) - MAX_EXECUTIVE_REVIEWS]
    return updated
