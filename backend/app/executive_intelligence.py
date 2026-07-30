"""ExecutiveIntelligence — v0.7 Feature 50 (Part 1 of a phased build),
the Executive Intelligence Network.

The brief's own instruction: "Do NOT create duplicate systems. Refactor
and upgrade the current implementation so all existing functionality is
preserved while expanding it." Researched first, and every one of the
eight named departments already has a real, checkable system behind it —
this module is a synthesis/presentation layer over them, not a new
computation engine:

  Research              -> the proposal's own real `research_summary`
                            (already generated in app/executive.py from
                            real ResearchItem confidence).
  Quant                  -> DecisionConfidence's own real "technical" and
                            "research" ConfidenceFactor readings
                            (app/confidence.py) — the statistical read
                            already computed at proposal time.
  Risk                   -> the proposal's own real `risk_summary`
                            (Sentinel/Guardian, app/risk_engine.py) plus
                            the real "risk" AnalystVote.
  Simulation              -> the real What-If Simulation Lab worst-case
                            read already carried on a ChallengeReport
                            (`worst_case_scenario`, app/whatif.py) when
                            one exists for this proposal; an honest
                            "not yet stress-tested" otherwise — never a
                            fabricated forecast.
  Decision Intelligence   -> DecisionConfidence itself (score/tier/
                            summary) — this department's own opinion IS
                            the Decision Confidence Engine's real read,
                            not a second independently-invented one.
  Coach                   -> the most recent real CoachReport's
                            strengths/recommendations (app/coach.py) —
                            an honest "no report yet" before the first
                            weekly/monthly one exists.
  Founders                -> the real Library of Mistakes titles already
                            attached to a ChallengeReport as
                            `historical_comparisons` — "we've made
                            similar mistakes before" is literally that
                            real field, never a fabricated pairing.
  Devil's Advocate        -> the ChallengeReport itself when one exists;
                            an honest "not yet challenged" otherwise
                            (a report is CEO-requested, not automatic —
                            see app/devils_advocate.py's own docstring).

Explicit cuts for this phase (documented, not silently dropped — see
docs/Architecture.md's Feature 50 section for the full phased plan):
Executive Meeting Log (a new permanent-record persistence feature),
per-department weekly Self-Evaluation, the Company Health formula
redesign, and the brief's "Session Changes / Market Open / Market Close"
simulation environments (no session-boundary model exists anywhere in
this codebase's continuous sim clock to back them) are all deferred to
later phases or cut outright, not fabricated here.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import (
    ChallengeReport,
    CoachReport,
    DecisionConfidence,
    DepartmentOpinion,
    ExecutiveAction,
    ExecutiveRecommendation,
    ExecutiveStance,
    TradeProposal,
)

_DEPARTMENT_LABELS: dict[str, str] = {
    "research": "Research",
    "quant": "Quant",
    "risk": "Risk",
    "simulation": "Simulation",
    "decision_intelligence": "Decision Intelligence",
    "coach": "Coach",
    "founders": "Founders",
    "devils_advocate": "Devil's Advocate",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _factor_score(confidence: DecisionConfidence, name: str) -> float | None:
    return next((f.score for f in confidence.factors if f.name == name), None)


def _research_opinion(proposal: TradeProposal) -> DepartmentOpinion:
    research_factor = _factor_score(proposal.confidence_engine, "research")
    effective = research_factor if research_factor is not None else 50.0
    stance: ExecutiveStance = "agree" if effective >= 60 else "request_more_research"
    return DepartmentOpinion(
        role="research",
        departmentLabel=_DEPARTMENT_LABELS["research"],
        stance=stance,
        summary=proposal.research_summary,
        confidencePct=round(effective, 1),
    )


def _quant_opinion(proposal: TradeProposal) -> DepartmentOpinion:
    technical = _factor_score(proposal.confidence_engine, "technical")
    research = _factor_score(proposal.confidence_engine, "research")
    parts = [f"Technical read {technical:.0f}/100" if technical is not None else None, f"research backing {research:.0f}/100" if research is not None else None]
    summary = " — ".join(p for p in parts if p) or "No real statistical factors available yet for this proposal."
    avg = sum(v for v in (technical, research) if v is not None) / max(1, sum(1 for v in (technical, research) if v is not None)) if (technical is not None or research is not None) else 50.0
    stance: ExecutiveStance = "agree" if avg >= 60 else "disagree" if avg < 40 else "request_more_research"
    return DepartmentOpinion(role="quant", departmentLabel=_DEPARTMENT_LABELS["quant"], stance=stance, summary=summary, confidencePct=round(avg, 1))


def _risk_opinion(proposal: TradeProposal) -> DepartmentOpinion:
    risk_vote = next((v for v in proposal.analyst_votes if v.role == "risk"), None)
    risk_factor = _factor_score(proposal.confidence_engine, "risk")
    exposure_factor = _factor_score(proposal.confidence_engine, "exposure")
    combined = [v for v in (risk_factor, exposure_factor) if v is not None]
    avg = sum(combined) / len(combined) if combined else 50.0
    is_wait = risk_vote is not None and risk_vote.choice == "wait"
    stance: ExecutiveStance = "disagree" if is_wait else ("recommend_position_change" if avg < 50 else "agree")
    summary = proposal.risk_summary if proposal.risk_summary else (risk_vote.reasoning if risk_vote else "No real risk read available yet.")
    return DepartmentOpinion(role="risk", departmentLabel=_DEPARTMENT_LABELS["risk"], agentId=risk_vote.agent_id if risk_vote else None, stance=stance, summary=summary, confidencePct=round(avg, 1))


def _simulation_opinion(challenge_report: ChallengeReport | None) -> DepartmentOpinion:
    if challenge_report is None:
        return DepartmentOpinion(role="simulation", departmentLabel=_DEPARTMENT_LABELS["simulation"], stance="request_more_research", summary="Not yet stress-tested — request a Devil's Advocate review to generate a real What-If Simulation read.", confidencePct=50.0)
    severity_conf = {"none_found": 80.0, "minor": 55.0, "major": 30.0}[challenge_report.severity]
    stance: ExecutiveStance = "agree" if challenge_report.severity == "none_found" else "recommend_waiting" if challenge_report.severity == "minor" else "disagree"
    return DepartmentOpinion(
        role="simulation",
        departmentLabel=_DEPARTMENT_LABELS["simulation"],
        agentId=challenge_report.assigned_agent,
        stance=stance,
        summary=f"Worst case simulated: {challenge_report.worst_case_scenario}" if challenge_report.worst_case_scenario else "No worst-case scenario recorded.",
        confidencePct=severity_conf,
    )


def _decision_intelligence_opinion(proposal: TradeProposal) -> DepartmentOpinion:
    confidence = proposal.confidence_engine
    tier_stances: dict[str, ExecutiveStance] = {"elite": "agree", "strong": "agree", "good": "agree", "moderate": "request_more_research", "weak": "disagree", "poor": "recommend_rejecting"}
    stance: ExecutiveStance = tier_stances.get(confidence.tier, "request_more_research")
    return DepartmentOpinion(role="decision_intelligence", departmentLabel=_DEPARTMENT_LABELS["decision_intelligence"], stance=stance, summary=confidence.summary, confidencePct=round(confidence.score, 1))


def _coach_opinion(coach_reports: list[CoachReport]) -> DepartmentOpinion:
    if not coach_reports:
        return DepartmentOpinion(role="coach", departmentLabel=_DEPARTMENT_LABELS["coach"], stance="request_more_research", summary="No Coach report filed yet this game — too early for a real development read.", confidencePct=50.0)
    latest = coach_reports[-1]
    notes = latest.recommendations or latest.strengths or latest.common_mistakes
    summary = notes[0] if notes else f"Company Score {latest.company_score:.0f}/100 as of the last report."
    stance: ExecutiveStance = "agree" if latest.company_score >= 60 else "request_more_research"
    return DepartmentOpinion(role="coach", departmentLabel=_DEPARTMENT_LABELS["coach"], stance=stance, summary=summary, confidencePct=round(latest.company_score, 1))


def _founders_opinion(challenge_report: ChallengeReport | None) -> DepartmentOpinion:
    comparisons = challenge_report.historical_comparisons if challenge_report else []
    if not comparisons:
        return DepartmentOpinion(role="founders", departmentLabel=_DEPARTMENT_LABELS["founders"], stance="agree", summary="No past company history on this symbol yet — nothing to caution against.", confidencePct=60.0)
    return DepartmentOpinion(role="founders", departmentLabel=_DEPARTMENT_LABELS["founders"], stance="recommend_waiting", summary=f"We've been here before: {comparisons[0]}", confidencePct=40.0)


def _devils_advocate_opinion(challenge_report: ChallengeReport | None) -> DepartmentOpinion:
    if challenge_report is None:
        return DepartmentOpinion(role="devils_advocate", departmentLabel=_DEPARTMENT_LABELS["devils_advocate"], stance="request_more_research", summary="Not yet challenged — request a Devil's Advocate report.", agentId=None, confidencePct=50.0)
    severity_stances: dict[str, ExecutiveStance] = {"none_found": "agree", "minor": "recommend_waiting", "major": "recommend_rejecting"}
    stance: ExecutiveStance = severity_stances[challenge_report.severity]
    return DepartmentOpinion(role="devils_advocate", departmentLabel=_DEPARTMENT_LABELS["devils_advocate"], agentId=challenge_report.assigned_agent, stance=stance, summary=challenge_report.final_recommendation, confidencePct={"none_found": 80.0, "minor": 55.0, "major": 25.0}[challenge_report.severity])


def generate_department_opinions(proposal: TradeProposal, challenge_report: ChallengeReport | None, coach_reports: list[CoachReport]) -> list[DepartmentOpinion]:
    return [
        _research_opinion(proposal),
        _quant_opinion(proposal),
        _risk_opinion(proposal),
        _simulation_opinion(challenge_report),
        _decision_intelligence_opinion(proposal),
        _coach_opinion(coach_reports),
        _founders_opinion(challenge_report),
        _devils_advocate_opinion(challenge_report),
    ]


# Real, rule-based — never a fabricated aggregate. Checked in priority
# order: an active major weakness or critical risk always wins over a
# merely-lukewarm-but-not-negative average.
def compute_executive_recommendation(proposal: TradeProposal, opinions: list[DepartmentOpinion]) -> ExecutiveRecommendation:
    supporting = [o.role for o in opinions if o.stance == "agree"]
    opposing = [o.role for o in opinions if o.stance in ("disagree", "recommend_rejecting")]
    waiting = [o for o in opinions if o.stance in ("recommend_waiting", "request_more_research", "recommend_position_change")]

    action: ExecutiveAction
    reason: str
    if any(o.role == "devils_advocate" and o.stance == "recommend_rejecting" for o in opinions) or any(o.role == "risk" and o.stance == "recommend_position_change" for o in opinions):
        action = "reduce_risk"
        reason = "Risk or Devil's Advocate flagged a real concern serious enough to size down before proceeding."
    elif any(o.role == "simulation" and o.stance == "request_more_research" for o in opinions):
        action = "focus_on_simulation"
        reason = "No real stress test exists yet for this proposal — Simulation has nothing to report."
    elif len(opposing) >= 2:
        action = "pause_trading"
        reason = f"{len(opposing)} departments actively disagree — the company shouldn't force this one."
    elif any(o.role == "research" and o.stance == "request_more_research" for o in opinions):
        action = "research_more"
        reason = "Research's own confidence factor is too low to back this proposal yet."
    elif len(waiting) >= 3:
        action = "wait"
        reason = "A majority of departments want more information before committing."
    else:
        action = "trade_normally"
        reason = "No department raised a real concern serious enough to change course."

    confidence_pct = round(sum(o.confidence_pct for o in opinions) / len(opinions), 1) if opinions else 50.0

    return ExecutiveRecommendation(
        proposalId=proposal.id,
        action=action,
        confidencePct=confidence_pct,
        reason=reason,
        supporting=supporting,
        opposing=opposing,
        opinions=opinions,
        generatedAt=_now_iso(),
    )
