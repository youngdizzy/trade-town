"""Self-Improvement Proposals — Design Bible Chapter 74 Part 1, the
Continuous Learning & Self-Improvement System (CLSIS).

TradeTown may propose a company-level change to itself — never a trade,
never a strategy (app/sandbox.py/app/strategy_lab.py already own
strategy-level proposals via Chapter 62's real idea-to-retirement
pipeline) — grounded only in real, citable evidence, never a fabricated
trigger. Two of the brief's eight named categories have a real,
evidence-gated generator here:

  risk_rule          — a real CaseStudyCategory recurs at or above
                        RECURRING_MISTAKE_THRESHOLD times among the most
                        recent RECURRING_MISTAKE_WINDOW loss-side
                        CaseStudy records (see app/mistakes.py).
  research_workflow  — at or above RETIREMENT_CLUSTER_THRESHOLD
                        strategies retire to the Failed Archive within
                        the most recent RETIREMENT_CLUSTER_WINDOW
                        retirements (see app/strategy_lab.py).

The other six categories (dashboard, position_sizing, new_executive,
automation, knowledge_organization, ui) are named on the
SelfImprovementCategory schema but have no real trigger signal
anywhere in this codebase yet — see the Design Bible chapter's own
Deferred Features section for why they stay unbuilt rather than faked.

Also home to compute_executive_learning_summary() — Part 1's other real
addition, a pure aggregation of four already-real per-agent systems
(app/coach.py's AgentScore, app/mentor.py's ThinkingProfile,
app/academy.py's AgentKnowledgeState, app/foundational_mentors.py's
per-track progress). No new computation, only composition.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from app.schemas import (
    SUCCESS_CASE_STUDY_CATEGORIES,
    AgentId,
    AgentKnowledgeState,
    CaseStudy,
    CoachReport,
    ExecutiveLearningSummary,
    FailedStrategyArchiveEntry,
    FoundationalMentorProgress,
    SelfImprovementProposal,
    ThinkingProfile,
)

MAX_SELF_IMPROVEMENT_PROPOSALS = 40

RECURRING_MISTAKE_THRESHOLD = 3
RECURRING_MISTAKE_WINDOW = 15

RETIREMENT_CLUSTER_THRESHOLD = 2
RETIREMENT_CLUSTER_WINDOW = 5


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _already_cited(evidence_id: str, existing_proposals: list[SelfImprovementProposal]) -> bool:
    return any(evidence_id in p.evidence for p in existing_proposals)


def maybe_propose_recurring_mistake(
    case_studies: list[CaseStudy],
    existing_proposals: list[SelfImprovementProposal],
    *,
    sim_day: int,
) -> SelfImprovementProposal | None:
    """Fires once per newest CaseStudy that pushes its category over
    RECURRING_MISTAKE_THRESHOLD within the most recent window — dedup is
    edge-triggered off that CaseStudy's own id, never a fixed proposal
    id, so a fresh cluster after a resolved proposal can still surface."""
    loss_studies = [c for c in case_studies if c.category not in SUCCESS_CASE_STUDY_CATEGORIES]
    recent = loss_studies[-RECURRING_MISTAKE_WINDOW:]
    if not recent:
        return None
    counts = Counter(c.category for c in recent)
    for category, count in counts.most_common():
        if count < RECURRING_MISTAKE_THRESHOLD:
            continue
        matching = [c for c in recent if c.category == category]
        newest = matching[-1]
        if _already_cited(newest.id, existing_proposals):
            continue
        readable = category.replace("_", " ")
        return SelfImprovementProposal(
            id=f"self-improve-mistake-{newest.id}",
            category="risk_rule",
            title=f"Add a risk rule addressing recurring {readable}",
            reasoning=(
                f'{count} of the last {len(recent)} filed case studies were categorized "{readable}" — '
                "a real, recurring process gap, not an isolated incident."
            ),
            evidence=[c.id for c in matching],
            benefits=[f'Could reduce the recurrence of "{readable}" going forward.'],
            risks=["A new risk rule could reduce trade frequency or introduce false positives on unrelated trades."],
            estimatedComplexity="small",
            priority="high" if count >= RECURRING_MISTAKE_THRESHOLD + 2 else "medium",
            confidence=round(min(100.0, count / len(recent) * 100.0), 1),
            simDay=sim_day,
            createdAt=_now_iso(),
        )
    return None


def maybe_propose_retirement_cluster(
    failed_archive: list[FailedStrategyArchiveEntry],
    existing_proposals: list[SelfImprovementProposal],
    *,
    sim_day: int,
) -> SelfImprovementProposal | None:
    """Fires once per newest Failed Archive entry that pushes the recent
    window over RETIREMENT_CLUSTER_THRESHOLD — same edge-triggered dedup
    convention as maybe_propose_recurring_mistake()."""
    recent = failed_archive[-RETIREMENT_CLUSTER_WINDOW:]
    if len(recent) < RETIREMENT_CLUSTER_THRESHOLD:
        return None
    newest = recent[-1]
    if _already_cited(newest.id, existing_proposals):
        return None
    return SelfImprovementProposal(
        id=f"self-improve-retirement-{newest.id}",
        category="research_workflow",
        title="Review the research workflow after a cluster of strategy retirements",
        reasoning=(
            f"{len(recent)} strategies retired to the Failed Archive within the last "
            f"{RETIREMENT_CLUSTER_WINDOW} retirements — a real, recent cluster worth reviewing "
            "before another idea enters the pipeline."
        ),
        evidence=[e.id for e in recent],
        benefits=["Could surface a shared root cause across recent failed strategies before more time is spent on similar ideas."],
        risks=["A workflow change could slow down legitimate new strategy ideas if the cluster turns out to be coincidental."],
        estimatedComplexity="medium",
        priority="medium",
        confidence=round(min(100.0, len(recent) / RETIREMENT_CLUSTER_WINDOW * 100.0), 1),
        simDay=sim_day,
        createdAt=_now_iso(),
    )


def record_self_improvement_proposal(
    proposals: list[SelfImprovementProposal], proposal: SelfImprovementProposal
) -> list[SelfImprovementProposal]:
    updated = [*proposals, proposal]
    if len(updated) > MAX_SELF_IMPROVEMENT_PROPOSALS:
        del updated[: len(updated) - MAX_SELF_IMPROVEMENT_PROPOSALS]
    return updated


def decide_self_improvement_proposal(
    proposals: list[SelfImprovementProposal],
    proposal_id: str,
    *,
    approve: bool,
    ceo_note: str | None,
) -> list[SelfImprovementProposal]:
    now = _now_iso()
    return [
        p.model_copy(
            update={
                "status": "approved" if approve else "rejected",
                "ceo_note": ceo_note,
                "decided_at": now,
            }
        )
        if p.id == proposal_id and p.status == "pending"
        else p
        for p in proposals
    ]


def compute_executive_learning_summary(
    agent_id: AgentId,
    *,
    coach_reports: list[CoachReport],
    thinking_profiles: dict[AgentId, ThinkingProfile],
    agent_knowledge: dict[AgentId, AgentKnowledgeState],
    mentor_progress: dict[str, FoundationalMentorProgress],
) -> ExecutiveLearningSummary:
    """Composes four already-real per-agent systems into one view —
    zero new computation. mentor_progress is this one agent's own
    (mentorId -> FoundationalMentorProgress) slice of
    FoundationalMentorState.progress[agent_id]."""
    latest_report = next(
        (r for r in reversed(coach_reports) if any(s.agent_id == agent_id for s in r.agent_rankings)),
        None,
    )
    agent_score = None
    if latest_report is not None:
        agent_score = next((s for s in latest_report.agent_rankings if s.agent_id == agent_id), None)
    knowledge = agent_knowledge.get(agent_id)
    graduated_count = sum(1 for p in mentor_progress.values() if p.graduation_status == "graduated")

    return ExecutiveLearningSummary(
        agentId=agent_id,
        researchAccuracy=agent_score.research_accuracy if agent_score else None,
        confidenceCalibration=agent_score.confidence_calibration if agent_score else None,
        thinkingProfile=thinking_profiles.get(agent_id),
        knowledgePoints=knowledge.points if knowledge else 0.0,
        knowledgeTier=knowledge.tier if knowledge else 0,
        knowledgeLevel=knowledge.level if knowledge else "novice",
        mentorTracks=list(mentor_progress.keys()),
        graduatedTrackCount=graduated_count,
    )
