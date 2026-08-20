"""ExecutiveIntelligence — v0.7 Feature 50, the Executive Intelligence
Network.

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

Part 2/3 adds three more real, permanent systems on top of the Part 1
synthesis above — none of them a second opinion engine, all of them
consumers of the exact same `generate_department_opinions()`/
`compute_executive_recommendation()` pair:

  Decision Grade          -> app/executive.py's `compute_decision_grade()`,
                            a real A+-F letter grade on the decision-
                            making PROCESS at the moment it's made (never
                            the trade's own P&L), attached directly to
                            the TradeDecision resolve_proposal() already
                            builds.
  Executive Meeting Log    -> `generate_meeting_log_entry()` below makes
                            the synthesis permanent: one real entry per
                            actual resolve_proposal() call (CEO-driven,
                            auto-resolved, or stale-expired), reusing
                            that same call's already-computed
                            TradeDecision's own Decision Grade.
  Weekly Self-Evaluation   -> `generate_weekly_self_evaluations()` below,
                            one real entry per department per week, built
                            entirely from that department's own real
                            opinions already logged to the Meeting Log
                            over the trailing 7 sim days.

Explicit cut, not deferred: the brief's "Session Changes / Market Open /
Market Close" simulation environments — no session-boundary model exists
anywhere in this codebase's continuous sim clock to back them honestly,
and none is being invented. The Company Health formula redesign lives in
app/company_health.py, not here — see that module's own docstring.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from app.schemas import (
    AnalystChoice,
    CeoDecisionRecord,
    ChallengeReport,
    CoachReport,
    DecisionConfidence,
    DecisionVaultEntry,
    DepartmentOpinion,
    DepartmentSelfEvaluation,
    ExecutiveAccuracyScore,
    ExecutiveAction,
    ExecutiveDepartmentRole,
    ExecutiveEvidenceState,
    ExecutiveMeetingLogEntry,
    ExecutiveRecommendation,
    ExecutiveStance,
    MarketIntelligenceState,
    TradeDecision,
    TradeProposal,
)
from app.session_evidence import compute_session_regime_evidence, lookup_session_regime_evidence

MAX_MEETING_LOG_ENTRIES = 200
MAX_SELF_EVAL_HISTORY = 250
# The Weekly Self-Evaluation's own trailing window — same 7-sim-day
# cadence as app/wisdom.py's weekly ReflectionSession (see nexus.py's
# WEEKLY_INTERVAL_DAYS).
SELF_EVAL_WINDOW_DAYS = 7
# v0.7 Feature 51 adds "market_intelligence" as a ninth department — its
# own opinion reads the real, always-current MarketIntelligenceState
# (app/market_intelligence.py), a company-wide read rather than a
# proposal-specific one (there is no per-proposal market intelligence —
# every proposal generated at the same moment shares the same real read).
# Both generic consumers below (Weekly Self-Evaluation, the Executive
# Meeting Log) already iterate this tuple generically, so no other change
# was needed to fold it into either.
_ALL_DEPARTMENT_ROLES: tuple[ExecutiveDepartmentRole, ...] = (
    "research",
    "quant",
    "risk",
    "simulation",
    "decision_intelligence",
    "coach",
    "founders",
    "devils_advocate",
    "market_intelligence",
)
# An Executive Recommendation's action never maps 1:1 onto the CEO's own
# buy/sell/wait choice (six actions vs. three choices) — these two sets
# define "the network and the CEO were pointed the same direction" for
# ExecutiveMeetingLogEntry.network_agreed, real and checkable either way.
_TRADING_ACTIONS: frozenset[ExecutiveAction] = frozenset({"trade_normally", "reduce_risk"})
_HOLDING_ACTIONS: frozenset[ExecutiveAction] = frozenset({"wait", "research_more", "pause_trading", "focus_on_simulation"})

_DEPARTMENT_LABELS: dict[str, str] = {
    "research": "Research",
    "quant": "Quant",
    "risk": "Risk",
    "simulation": "Simulation",
    "decision_intelligence": "Decision Intelligence",
    "coach": "Coach",
    "founders": "Founders",
    "devils_advocate": "Devil's Advocate",
    "market_intelligence": "Market Intelligence",
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
        evidence=[proposal.research_summary, f"Research confidence factor: {effective:.0f}/100."],
        concerns=[] if effective >= 60 else ["Research confidence factor is below the 60/100 bar this department votes to agree at."],
        benefits=[f"Research confidence factor at {effective:.0f}/100."] if effective >= 60 else [],
        alternative="Wait for a stronger research read before committing capital." if effective < 60 else None,
    )


def _quant_opinion(proposal: TradeProposal) -> DepartmentOpinion:
    technical = _factor_score(proposal.confidence_engine, "technical")
    research = _factor_score(proposal.confidence_engine, "research")
    parts = [f"Technical read {technical:.0f}/100" if technical is not None else None, f"research backing {research:.0f}/100" if research is not None else None]
    summary = " — ".join(p for p in parts if p) or "No real statistical factors available yet for this proposal."
    avg = sum(v for v in (technical, research) if v is not None) / max(1, sum(1 for v in (technical, research) if v is not None)) if (technical is not None or research is not None) else 50.0
    stance: ExecutiveStance = "agree" if avg >= 60 else "disagree" if avg < 40 else "request_more_research"
    evidence = [p for p in parts if p]
    return DepartmentOpinion(
        role="quant",
        departmentLabel=_DEPARTMENT_LABELS["quant"],
        stance=stance,
        summary=summary,
        confidencePct=round(avg, 1),
        evidence=evidence,
        concerns=["Combined statistical read is below 40/100."] if avg < 40 else [],
        benefits=[f"Combined statistical read at {avg:.0f}/100."] if avg >= 60 else [],
        alternative="A smaller position sizes the same statistical edge more conservatively." if 40 <= avg < 60 else None,
    )


def _risk_opinion(proposal: TradeProposal) -> DepartmentOpinion:
    risk_vote = next((v for v in proposal.analyst_votes if v.role == "risk"), None)
    risk_factor = _factor_score(proposal.confidence_engine, "risk")
    exposure_factor = _factor_score(proposal.confidence_engine, "exposure")
    combined = [v for v in (risk_factor, exposure_factor) if v is not None]
    avg = sum(combined) / len(combined) if combined else 50.0
    is_wait = risk_vote is not None and risk_vote.choice == "wait"
    stance: ExecutiveStance = "disagree" if is_wait else ("recommend_position_change" if avg < 50 else "agree")
    summary = proposal.risk_summary if proposal.risk_summary else (risk_vote.reasoning if risk_vote else "No real risk read available yet.")
    return DepartmentOpinion(
        role="risk",
        departmentLabel=_DEPARTMENT_LABELS["risk"],
        agentId=risk_vote.agent_id if risk_vote else None,
        stance=stance,
        summary=summary,
        confidencePct=round(avg, 1),
        evidence=(risk_vote.evidence if risk_vote else []) or [summary],
        concerns=[summary] if stance != "agree" else [],
        benefits=[f"Risk/exposure read at {avg:.0f}/100."] if stance == "agree" else [],
        alternative="Reduce position size before proceeding." if stance == "recommend_position_change" else None,
    )


def _simulation_opinion(challenge_report: ChallengeReport | None) -> DepartmentOpinion:
    if challenge_report is None:
        return DepartmentOpinion(
            role="simulation",
            departmentLabel=_DEPARTMENT_LABELS["simulation"],
            stance="request_more_research",
            summary="Not yet stress-tested — request a Devil's Advocate review to generate a real What-If Simulation read.",
            confidencePct=50.0,
            concerns=["No real stress test exists yet for this proposal."],
        )
    severity_conf = {"none_found": 80.0, "minor": 55.0, "major": 30.0}[challenge_report.severity]
    stance: ExecutiveStance = "agree" if challenge_report.severity == "none_found" else "recommend_waiting" if challenge_report.severity == "minor" else "disagree"
    worst_case = f"Worst case simulated: {challenge_report.worst_case_scenario}" if challenge_report.worst_case_scenario else "No worst-case scenario recorded."
    return DepartmentOpinion(
        role="simulation",
        departmentLabel=_DEPARTMENT_LABELS["simulation"],
        agentId=challenge_report.assigned_agent,
        stance=stance,
        summary=worst_case,
        confidencePct=severity_conf,
        evidence=[worst_case],
        concerns=[worst_case] if stance != "agree" else [],
        benefits=["No weaknesses found in the stress test."] if stance == "agree" else [],
    )


def _decision_intelligence_opinion(proposal: TradeProposal) -> DepartmentOpinion:
    confidence = proposal.confidence_engine
    tier_stances: dict[str, ExecutiveStance] = {"elite": "agree", "strong": "agree", "good": "agree", "moderate": "request_more_research", "weak": "disagree", "poor": "recommend_rejecting"}
    stance: ExecutiveStance = tier_stances.get(confidence.tier, "request_more_research")
    return DepartmentOpinion(
        role="decision_intelligence",
        departmentLabel=_DEPARTMENT_LABELS["decision_intelligence"],
        stance=stance,
        summary=confidence.summary,
        confidencePct=round(confidence.score, 1),
        evidence=[f"{f.name}: {f.score:.0f}/100 — {f.detail}" for f in confidence.factors],
        concerns=[confidence.summary] if stance in ("disagree", "recommend_rejecting") else [],
        benefits=[confidence.summary] if stance == "agree" else [],
    )


def _coach_opinion(coach_reports: list[CoachReport]) -> DepartmentOpinion:
    if not coach_reports:
        return DepartmentOpinion(role="coach", departmentLabel=_DEPARTMENT_LABELS["coach"], stance="request_more_research", summary="No Coach report filed yet this game — too early for a real development read.", confidencePct=50.0)
    latest = coach_reports[-1]
    notes = latest.recommendations or latest.strengths or latest.common_mistakes
    summary = notes[0] if notes else f"Company Score {latest.company_score:.0f}/100 as of the last report."
    stance: ExecutiveStance = "agree" if latest.company_score >= 60 else "request_more_research"
    return DepartmentOpinion(
        role="coach",
        departmentLabel=_DEPARTMENT_LABELS["coach"],
        stance=stance,
        summary=summary,
        confidencePct=round(latest.company_score, 1),
        evidence=[f"Company Score {latest.company_score:.0f}/100 as of the last Coach report."],
        concerns=list(latest.common_mistakes[:2]) if stance != "agree" else [],
        benefits=list(latest.strengths[:2]) if stance == "agree" else [],
    )


def _founders_opinion(challenge_report: ChallengeReport | None) -> DepartmentOpinion:
    comparisons = challenge_report.historical_comparisons if challenge_report else []
    if not comparisons:
        return DepartmentOpinion(role="founders", departmentLabel=_DEPARTMENT_LABELS["founders"], stance="agree", summary="No past company history on this symbol yet — nothing to caution against.", confidencePct=60.0)
    return DepartmentOpinion(
        role="founders",
        departmentLabel=_DEPARTMENT_LABELS["founders"],
        stance="recommend_waiting",
        summary=f"We've been here before: {comparisons[0]}",
        confidencePct=40.0,
        evidence=list(comparisons),
        concerns=[comparisons[0]],
        alternative="Review the Library of Mistakes entry before repeating this setup.",
    )


def _devils_advocate_opinion(challenge_report: ChallengeReport | None) -> DepartmentOpinion:
    if challenge_report is None:
        return DepartmentOpinion(role="devils_advocate", departmentLabel=_DEPARTMENT_LABELS["devils_advocate"], stance="request_more_research", summary="Not yet challenged — request a Devil's Advocate report.", agentId=None, confidencePct=50.0)
    severity_stances: dict[str, ExecutiveStance] = {"none_found": "agree", "minor": "recommend_waiting", "major": "recommend_rejecting"}
    stance: ExecutiveStance = severity_stances[challenge_report.severity]
    return DepartmentOpinion(
        role="devils_advocate",
        departmentLabel=_DEPARTMENT_LABELS["devils_advocate"],
        agentId=challenge_report.assigned_agent,
        stance=stance,
        summary=challenge_report.final_recommendation,
        confidencePct={"none_found": 80.0, "minor": 55.0, "major": 25.0}[challenge_report.severity],
        evidence=list(challenge_report.missing_evidence),
        concerns=list(challenge_report.hidden_risks) + list(challenge_report.weak_assumptions),
        benefits=["No hidden risks or weak assumptions found."] if challenge_report.severity == "none_found" else [],
        alternative=challenge_report.suggested_improvements[0] if challenge_report.suggested_improvements else None,
    )


# v0.7 Feature 51 — Market Intelligence's own opinion, real and
# company-wide rather than proposal-specific (every proposal generated at
# the same moment shares the same real MarketIntelligenceState read).
# Never recomputed here — reads app/market_intelligence.py's own already-
# computed Market Quality Score directly.
#
# CEO directive "Session Trading Education & Agent Training" — the real
# integration point session context reaches the live decision pipeline
# through: `decision_vault` (already in scope at every real call site
# below) feeds app/session_evidence.py's real SESSION x REGIME evidence,
# looked up for the CURRENT real session/regime pairing and cited
# directly in this opinion's own summary/evidence — the exact GOOD-
# explanation format the directive asks for ("N historical observations,
# X% favorable" or an honest "NOT ENOUGH EVIDENCE"), reached through this
# already-real, already-informational department-opinion channel. This
# NEVER changes `stance` (still driven purely by the real Market Quality
# tier above) and never touches the Trade Gatekeeper or RiskLimits —
# session evidence informs the explanation text only, exactly the
# directive's own "session context is evidence, not permission" rule.
def _market_intelligence_opinion(market_intelligence: MarketIntelligenceState, decision_vault: list[DecisionVaultEntry]) -> DepartmentOpinion:
    stance_by_tier: dict[str, ExecutiveStance] = {
        "excellent": "agree",
        "good": "agree",
        "average": "request_more_research",
        "poor": "recommend_waiting",
        "avoid_trading": "recommend_rejecting",
    }
    quality = market_intelligence.quality
    stance = stance_by_tier[quality.tier]

    session_evidence_summary = compute_session_regime_evidence(decision_vault)
    bucket = lookup_session_regime_evidence(session_evidence_summary, market_intelligence.session.current, market_intelligence.regime)
    if bucket is None or bucket.evidence_state == "not_enough_evidence":
        sample = bucket.sample_size if bucket is not None else 0
        session_note = (
            f"NOT ENOUGH EVIDENCE for {market_intelligence.session.label} under this regime yet "
            f"({sample} real observation{'s' if sample != 1 else ''}, {session_evidence_summary.min_sample_size} required)."
        )
    else:
        session_note = (
            f"{market_intelligence.session.label} under this regime: {bucket.sample_size} real observations, "
            f"{bucket.win_rate_pct:.0f}% favorable ({bucket.evidence_state})."
        )

    summary = f"{market_intelligence.regime_label} — {quality.reasoning} {session_note}"
    return DepartmentOpinion(
        role="market_intelligence",
        departmentLabel=_DEPARTMENT_LABELS["market_intelligence"],
        stance=stance,
        summary=summary,
        confidencePct=quality.confidence_pct,
        evidence=[market_intelligence.regime_label, quality.reasoning, session_note],
        concerns=[quality.reasoning] if stance in ("recommend_waiting", "recommend_rejecting") else [],
        benefits=[quality.reasoning] if stance == "agree" else [],
    )


def generate_department_opinions(
    proposal: TradeProposal, challenge_report: ChallengeReport | None, coach_reports: list[CoachReport], market_intelligence: MarketIntelligenceState, decision_vault: list[DecisionVaultEntry]
) -> list[DepartmentOpinion]:
    return [
        _research_opinion(proposal),
        _quant_opinion(proposal),
        _risk_opinion(proposal),
        _simulation_opinion(challenge_report),
        _decision_intelligence_opinion(proposal),
        _coach_opinion(coach_reports),
        _founders_opinion(challenge_report),
        _devils_advocate_opinion(challenge_report),
        _market_intelligence_opinion(market_intelligence, decision_vault),
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
    # v0.7 Feature 51 — checked first: the brief's own rule that "no
    # department may recommend a trade without first explaining the
    # current market environment." A real "avoid_trading" Market Quality
    # read outranks every other department's opinion, the same way the
    # Gatekeeper's own market_intelligence check mechanically blocks the
    # trade itself (app/gatekeeper.py) — this just makes the Network's own
    # recommendation say so too, rather than silently disagreeing with
    # what the Gatekeeper is about to do.
    if any(o.role == "market_intelligence" and o.stance == "recommend_rejecting" for o in opinions):
        action = "pause_trading"
        reason = "Market Intelligence reads today's conditions as Avoid Trading — the company shouldn't force a trade into a real, currently poor environment."
    elif any(o.role == "devils_advocate" and o.stance == "recommend_rejecting" for o in opinions) or any(o.role == "risk" and o.stance == "recommend_position_change" for o in opinions):
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
    # Design Bible Chapter 70 Part 2 — Consensus % is a deliberately
    # different, real number from Confidence % above: the share of
    # departments that plainly AGREE, not their average conviction.
    # A proposal every department "agrees" with at low confidence reads
    # high consensus / low confidence; a proposal one department
    # passionately opposes and eight mildly agree with reads high
    # confidence / imperfect consensus. Both are real and worth showing
    # separately, matching the brief's own two-number example.
    consensus_pct = round(len(supporting) / len(opinions) * 100.0, 1) if opinions else 0.0
    disagreement_summary = _build_disagreement_summary(opinions)

    return ExecutiveRecommendation(
        proposalId=proposal.id,
        action=action,
        confidencePct=confidence_pct,
        reason=reason,
        supporting=supporting,
        opposing=opposing,
        opinions=opinions,
        generatedAt=_now_iso(),
        consensusPct=consensus_pct,
        disagreementSummary=disagreement_summary,
    )


# Design Bible Chapter 70 Part 2 — Disagreement Analysis. A real,
# generated paragraph over the same opinions the panel already shows
# card-by-card — never a fabricated synthesis, just naming what's
# already there in one place instead of leaving the CEO to assemble it.
def _build_disagreement_summary(opinions: list[DepartmentOpinion]) -> str:
    non_agreeing = [o for o in opinions if o.stance != "agree"]
    if not non_agreeing:
        return "Every department agrees — no disagreement to explain."
    parts = [f"{o.department_label} {EXECUTIVE_STANCE_PHRASING.get(o.stance, o.stance)} ({o.confidence_pct:.0f}% confidence): {o.summary}" for o in non_agreeing]
    return " ".join(parts)


EXECUTIVE_STANCE_PHRASING: dict[str, str] = {
    "disagree": "disagrees",
    "request_more_research": "wants more research before deciding",
    "recommend_waiting": "recommends waiting",
    "recommend_position_change": "recommends changing position size",
    "recommend_rejecting": "recommends rejecting",
}


# v0.7 Feature 50 (Part 2/3) — the Executive Meeting Log. Makes Part 1's
# previously ephemeral, compute-on-open synthesis permanent: generated
# once per real resolve_proposal() call (app/executive.py), reusing that
# same call's own already-computed TradeDecision (its decisionGrade/
# decisionGradeScore is read straight off it, never recomputed).
def generate_meeting_log_entry(
    proposal: TradeProposal,
    decision: TradeDecision,
    ceo_decision: AnalystChoice,
    challenge_report: ChallengeReport | None,
    coach_reports: list[CoachReport],
    market_intelligence: MarketIntelligenceState,
    decision_vault: list[DecisionVaultEntry],
    *,
    sim_day: int,
    resolved_by: Literal["ceo", "auto", "delegated"],
) -> ExecutiveMeetingLogEntry:
    opinions = generate_department_opinions(proposal, challenge_report, coach_reports, market_intelligence, decision_vault)
    recommendation = compute_executive_recommendation(proposal, opinions)
    if ceo_decision in ("buy", "sell"):
        network_agreed = recommendation.action in _TRADING_ACTIONS
    else:
        network_agreed = recommendation.action in _HOLDING_ACTIONS
    grade = decision.decision_grade or "F"
    grade_score = decision.decision_grade_score if decision.decision_grade_score is not None else 0.0
    return ExecutiveMeetingLogEntry(
        id=f"meeting-{proposal.id}",
        proposalId=proposal.id,
        symbol=proposal.symbol,
        simDay=sim_day,
        opinions=opinions,
        recommendedAction=recommendation.action,
        recommendationReason=recommendation.reason,
        ceoDecision=ceo_decision,
        networkAgreed=network_agreed,
        decisionGrade=grade,
        decisionGradeScore=grade_score,
        resolvedBy=resolved_by,
        createdAt=_now_iso(),
    )


def record_meeting_log_entry(log: list[ExecutiveMeetingLogEntry], entry: ExecutiveMeetingLogEntry) -> list[ExecutiveMeetingLogEntry]:
    updated = [*log, entry]
    if len(updated) > MAX_MEETING_LOG_ENTRIES:
        del updated[: len(updated) - MAX_MEETING_LOG_ENTRIES]
    return updated


# v0.7 Feature 50 (Part 2/3) — Weekly Self-Evaluation. One real,
# evidence-backed evaluation per department per week, built entirely
# from that department's own real DepartmentOpinion entries logged to
# the Executive Meeting Log over the trailing SELF_EVAL_WINDOW_DAYS —
# never a fabricated self-assessment, and honestly neutral (50.0, "no
# real decisions yet") for a department with nothing on record this week.
def generate_weekly_self_evaluations(meeting_log: list[ExecutiveMeetingLogEntry], *, sim_day: int) -> list[DepartmentSelfEvaluation]:
    window_start = sim_day - SELF_EVAL_WINDOW_DAYS + 1
    week_entries = [e for e in meeting_log if window_start <= e.sim_day <= sim_day]
    evaluations: list[DepartmentSelfEvaluation] = []
    for role in _ALL_DEPARTMENT_ROLES:
        label = _DEPARTMENT_LABELS[role]
        role_opinions = [op for entry in week_entries for op in entry.opinions if op.role == role]
        if not role_opinions:
            evaluations.append(
                DepartmentSelfEvaluation(
                    id=f"selfeval-{role}-{sim_day}",
                    role=role,
                    departmentLabel=label,
                    weekEndingSimDay=sim_day,
                    decisionsReviewed=0,
                    score=50.0,
                    summary="No real decisions reached the network this week — nothing to evaluate yet.",
                    strengths=[],
                    improvementAreas=[],
                    createdAt=_now_iso(),
                )
            )
            continue
        score = sum(op.confidence_pct for op in role_opinions) / len(role_opinions)
        agree_count = sum(1 for op in role_opinions if op.stance == "agree")
        concern_count = sum(1 for op in role_opinions if op.stance in ("disagree", "recommend_rejecting"))
        strengths = [f"Weighed in on {len(role_opinions)} real decision(s) this week, averaging {score:.0f}/100 confidence."]
        if agree_count:
            strengths.append(f"Agreed with the desk's overall call on {agree_count}/{len(role_opinions)} decisions.")
        improvement_areas: list[str] = []
        if concern_count:
            improvement_areas.append(f"Raised a real concern on {concern_count}/{len(role_opinions)} decisions — worth revisiting whether those calls held up.")
        if score < 50:
            improvement_areas.append("Average confidence stayed below 50/100 this week — real evidence was thin more often than not.")
        evaluations.append(
            DepartmentSelfEvaluation(
                id=f"selfeval-{role}-{sim_day}",
                role=role,
                departmentLabel=label,
                weekEndingSimDay=sim_day,
                decisionsReviewed=len(role_opinions),
                score=round(score, 1),
                summary=f"{len(role_opinions)} real decision(s) reviewed this week; {score:.0f}/100 average confidence.",
                strengths=strengths,
                improvementAreas=improvement_areas,
                createdAt=_now_iso(),
            )
        )
    return evaluations


def record_self_evaluations(history: list[DepartmentSelfEvaluation], new_entries: list[DepartmentSelfEvaluation]) -> list[DepartmentSelfEvaluation]:
    updated = [*history, *new_entries]
    if len(updated) > MAX_SELF_EVAL_HISTORY:
        del updated[: len(updated) - MAX_SELF_EVAL_HISTORY]
    return updated


# Design Bible Chapter 70 Part 2 — Executive Accuracy Score. Scored ONLY
# over trades the CEO actually took AND that have since closed with a
# real, known outcome (CeoDecisionRecord.outcome resolved to "correct"/
# "incorrect" by app/executive.py's grade_ceo_decisions once the linked
# PaperTrade closes with a real realized P&L) — never a counterfactual
# judgment about a trade that was never placed, matching this codebase's
# existing, explicit refusal to fabricate what a never-taken trade
# "would have" done (app/coach.py, app/player_vs_ai.py). A department's
# hedged stances (recommend_waiting/request_more_research/recommend_
# position_change) never took a clear directional position on the
# trade's own success, so they're excluded from this binary score
# rather than counted either way.
_DIRECTIONAL_STANCE_PREDICTS_PROFIT: dict[str, bool] = {
    "agree": True,
    "disagree": False,
    "recommend_rejecting": False,
}


# CEO directive "Features 31-35," Feature 33 — Executive Accuracy
# Evidence System. Real, disclosed floor before a tracked accuracy
# reads as a meaningful PASS/FAIL/INCONCLUSIVE verdict rather than
# still-thin evidence — the same honesty convention Chapter 73's own
# Compliance Score and Feature 32's MIN_OVERRIDE_SAMPLE_FOR_TREND
# already carry. Below this, a department may have 1-2 real tracked
# calls but not enough for the verdict to mean anything yet.
MIN_ACCURACY_SAMPLE_FOR_VERDICT = 3

# Reused verbatim from the existing Command Center UI's own real
# green/amber/red boundary (frontend/src/ui/components/CommandCenter/
# ExecutiveVoting.tsx's ExecutiveAccuracyPanel) — not a new number
# invented for this feature.
_PASS_THRESHOLD_PCT = 60.0
_FAIL_THRESHOLD_PCT = 40.0


def _evaluation_state(tracked: int, accuracy_pct: float | None) -> ExecutiveEvidenceState:
    if tracked < MIN_ACCURACY_SAMPLE_FOR_VERDICT or accuracy_pct is None:
        return "not_enough_evidence"
    if accuracy_pct >= _PASS_THRESHOLD_PCT:
        return "pass"
    if accuracy_pct < _FAIL_THRESHOLD_PCT:
        return "fail"
    return "inconclusive"


def compute_executive_accuracy_scores(
    meeting_log: list[ExecutiveMeetingLogEntry], ceo_decisions: list[CeoDecisionRecord]
) -> list[ExecutiveAccuracyScore]:
    """Directional accuracy — did this department's real stance predict
    whether the trade it was cast on eventually closed profitable —
    tracked identically across all nine departments; the one real,
    cross-department signal this codebase already had. A genuinely
    role-specific second metric per department (Research: evidence
    quality; Quant: statistical validity; Risk: risk identification;
    ...) is a real, disclosed, deliberate cut this pass, not fabricated
    or silently dropped — see this feature's CHANGELOG/Architecture.md
    entry for the concrete real data sources identified during research
    (ChallengeReport, MarketIntelligenceLearningEntry, DecisionVaultEntry)
    and why wiring them in required more cross-referencing than this
    pass safely had room for.

    `accuracyPct` is `None` (NOT_ENOUGH_EVIDENCE), never a fabricated
    `0.0`, when a department has zero tracked, evaluable stances yet —
    the CEO directive's own named bug fix. `evaluationState` exposes
    PASS/FAIL/INCONCLUSIVE/NOT_ENOUGH_EVIDENCE explicitly rather than
    leaving every caller to reinvent its own good/bad interpretation of
    a raw percentage.

    CEO directive "Professional Quant Firm Phase 41-45," Feature 44 —
    audited for data leakage since this score feeds live vote weighting
    (see app/weighted_decisions.py's compute_accuracy_multiplier()):
    `resolved_by_proposal` is built only from `ceo_decisions` whose
    `outcome` already reads `"correct"`/`"incorrect"` — a proposal only
    gets an outcome once its underlying trade has actually closed. The
    department stance being weighted RIGHT NOW belongs to a proposal
    that is, by definition, not yet resolved (an unresolved proposal has
    no `outcome` yet, so it can never appear in `resolved_by_proposal`)
    — so a decision's own outcome can never leak into its own weight.
    This is causally sound as a live trailing-accuracy signal, not a
    train/validation/test split — see AgentReviewDataSplit's own
    schema docstring for where this directive's real train/validation/
    test/live-paper separation was actually needed and built (Agent
    Performance Reviews, which this signal is NOT)."""
    resolved_by_proposal: dict[str, bool] = {
        r.proposal_id: r.outcome == "correct" for r in ceo_decisions if r.outcome in ("correct", "incorrect")
    }
    scores: list[ExecutiveAccuracyScore] = []
    for role in _ALL_DEPARTMENT_ROLES:
        tracked = 0
        correct = 0
        for entry in meeting_log:
            was_profitable = resolved_by_proposal.get(entry.proposal_id)
            if was_profitable is None:
                continue
            opinion = next((o for o in entry.opinions if o.role == role), None)
            if opinion is None or opinion.stance not in _DIRECTIONAL_STANCE_PREDICTS_PROFIT:
                continue
            predicted_profitable = _DIRECTIONAL_STANCE_PREDICTS_PROFIT[opinion.stance]
            tracked += 1
            if predicted_profitable == was_profitable:
                correct += 1
        accuracy = round(correct / tracked * 100.0, 1) if tracked else None
        scores.append(
            ExecutiveAccuracyScore(
                role=role,
                departmentLabel=_DEPARTMENT_LABELS[role],
                decisionsTracked=tracked,
                correctCount=correct,
                accuracyPct=accuracy,
                evaluationState=_evaluation_state(tracked, accuracy),
            )
        )
    return scores
