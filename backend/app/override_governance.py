"""app/override_governance.py — CEO directive "Features 31-35:
Compliance, Governance & Continuous Improvement System," Feature 32
(CEO Override Governance). Per the directive's own staging rule, this
does not start until Feature 31 is tested, verified, and documented.

RESEARCH FINDING, recorded here per the directive's own "research
first" rule: the CEO's brief warns "CEO OVERRIDES: 138, 69.0% — do not
assume this is good or bad." Tracing `CeoDecisionRecord.outcome`
(app/executive.py's `resolve_proposal()`) shows the earlier assumption
that overrides are permanently ungraded is only half true —
`outcome="pending" if order_id is not None else "undecidable"` is keyed
on whether a real order was placed, not on `agreed_with_ai`. An override
that actually places a trade (e.g. the CEO buys when the network said
wait) gets graded exactly like any other decision once that trade
closes, via `grade_ceo_decisions()`. Only an override that resolves to
"wait" (no order at all) stays `"undecidable"` forever — correctly, since
there is no real trade to test it against. This module never re-grades
that outcome a second way; `refresh_override_outcomes()` below only
mirrors it.

WHAT THIS MODULE ADDS: a second, genuinely new axis — PROCESS QUALITY —
answering "was the override justified by the evidence that existed at
the moment the CEO decided," independent of whatever the trade's P&L
later turned out to be (the CEO directive's own "no hindsight-only
evaluation" rule). Sourced entirely from the real, already-persisted
`ExecutiveMeetingLogEntry` for that same proposal (`opinions`,
`decisionGrade`/`decisionGradeScore`) — never a fabricated confidence or
risk score, and never a second copy of `app/risk_engine.py`'s own real
risk logic (only the Risk department's own already-recorded `opinion`
stance is read here).

PROCESS QUALITY HEURISTIC (disclosed, not scientific — the same
"conservative but arbitrary, no real regulatory requirement behind it"
honesty note `RiskLimits` and Chapter 73's own Compliance Score already
carry): a 2x2 table over two real, already-computed signals —

- "strong" recommendation: `decisionGradeScore >= 80.0` — reusing the
  exact B-/B/B-... "passing" cutoff `app/executive.py`'s own
  `GRADE_THRESHOLDS` already established as the B- boundary, not a new
  number invented for this module.
- "contested" recommendation: fewer than half of the real department
  opinions on file plainly agreed with the recommended action.

    strong=False, contested=True  -> justified   (weak setup, real dissent — a skeptical override is reasonable)
    strong=False, contested=False -> mixed        (weak setup the departments still backed — ambiguous)
    strong=True,  contested=True  -> mixed        (strong setup but genuinely split opinion — ambiguous)
    strong=True,  contested=False -> unjustified  (strong, consensus setup overridden with no recorded dissent)

`not_enough_evidence` when no `ExecutiveMeetingLogEntry` exists for the
proposal at all (a real gap, e.g. very old decisions) — never silently
defaulted to any of the four states above.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.executive import GRADE_THRESHOLDS
from app.schemas import (
    AgentId,
    CeoDecisionRecord,
    CeoOverrideEvaluation,
    CeoOverrideGovernanceSummary,
    DecisionGrade,
    ExecutiveDepartmentRole,
    ExecutiveMeetingLogEntry,
    OverrideProcessQuality,
)

MAX_OVERRIDE_EVALUATIONS = 500

# Reused verbatim from app/executive.py's own real GRADE_THRESHOLDS — the
# "B-" boundary, i.e. the same passing/non-passing cutoff already shown
# to the CEO as a letter grade, not a new number invented for this
# module.
_STRONG_RECOMMENDATION_SCORE = next(score for score, grade in GRADE_THRESHOLDS if grade == "B-")

# A real, disclosed, arbitrary sample-size floor before governance
# trends (rather than individual records) are reported as meaningful —
# the same honesty pattern Chapter 73's own Compliance Score carries.
MIN_OVERRIDE_SAMPLE_FOR_TREND = 5


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def evaluate_override_process_quality(
    meeting_entry: ExecutiveMeetingLogEntry | None,
) -> tuple[
    OverrideProcessQuality,
    float | None,
    float | None,
    DecisionGrade | None,
    float | None,
    list[ExecutiveDepartmentRole],
    list[str],
]:
    """Returns (process_quality, original_confidence_pct,
    original_decision_grade_score, original_decision_grade,
    department_agreement_pct, agreeing_departments,
    evidence_at_decision_time). Every value is `None`/empty when
    `meeting_entry` is `None` — an honest NOT_ENOUGH_EVIDENCE gap, never
    a fabricated read."""
    if meeting_entry is None:
        return "not_enough_evidence", None, None, None, None, [], []

    opinions = meeting_entry.opinions
    original_confidence_pct = round(sum(o.confidence_pct for o in opinions) / len(opinions), 1) if opinions else None
    agreeing = [o for o in opinions if o.stance == "agree"]
    department_agreement_pct = round(len(agreeing) / len(opinions) * 100.0, 1) if opinions else None
    agreeing_departments: list[ExecutiveDepartmentRole] = [o.role for o in agreeing]
    dissenting_evidence: list[str] = [
        item for o in opinions if o.stance != "agree" for item in (*o.evidence, *o.concerns)
    ]

    strong = meeting_entry.decision_grade_score >= _STRONG_RECOMMENDATION_SCORE
    contested = department_agreement_pct is not None and department_agreement_pct < 50.0

    quality: OverrideProcessQuality
    if not strong and contested:
        quality = "justified"
    elif strong and not contested:
        quality = "unjustified"
    else:
        quality = "mixed"

    return (
        quality,
        original_confidence_pct,
        meeting_entry.decision_grade_score,
        meeting_entry.decision_grade,
        department_agreement_pct,
        agreeing_departments,
        dissenting_evidence,
    )


def sync_override_evaluations(
    existing: list[CeoOverrideEvaluation],
    ceo_decisions: list[CeoDecisionRecord],
    meeting_log: list[ExecutiveMeetingLogEntry],
) -> list[CeoOverrideEvaluation]:
    """The one real creation path. Opens a `CeoOverrideEvaluation` for
    every real `CeoDecisionRecord` where `agreed_with_ai=False` that
    doesn't already have one, matched by `decision_id` — real,
    deduplicated the same way Feature 31's `sync_incidents_from_audit_log()`
    matches by `source_entry_id`. Never touches an evaluation that
    already exists."""
    known_decision_ids = {e.decision_id for e in existing}
    meeting_by_proposal = {m.proposal_id: m for m in meeting_log}
    new_evals: list[CeoOverrideEvaluation] = []
    for d in ceo_decisions:
        if d.agreed_with_ai or d.id in known_decision_ids:
            continue
        meeting_entry = meeting_by_proposal.get(d.proposal_id)
        (
            process_quality,
            original_confidence_pct,
            original_decision_grade_score,
            original_decision_grade,
            department_agreement_pct,
            agreeing_departments,
            evidence,
        ) = evaluate_override_process_quality(meeting_entry)
        now = _now_iso()
        new_evals.append(
            CeoOverrideEvaluation(
                id=f"override-eval-{d.id}",
                decisionId=d.id,
                proposalId=d.proposal_id,
                symbol=d.symbol,
                createdAt=d.created_at,
                simDay=meeting_entry.sim_day if meeting_entry is not None else 0,
                originalRecommendation=d.ai_recommendation,
                ceoDecision=d.ceo_decision,
                overrideReason=d.override_reason,
                originalConfidencePct=original_confidence_pct,
                originalDecisionGrade=original_decision_grade,
                originalDecisionGradeScore=original_decision_grade_score,
                riskDepartmentStance=next((o.stance for o in meeting_entry.opinions if o.role == "risk"), None) if meeting_entry else None,
                departmentAgreementPct=department_agreement_pct,
                agreeingDepartments=agreeing_departments,
                evidenceAtDecisionTime=evidence,
                processQuality=process_quality,
                outcome=d.outcome,
                updatedAt=now,
            )
        )
    if not new_evals:
        return existing
    updated = [*existing, *new_evals]
    if len(updated) > MAX_OVERRIDE_EVALUATIONS:
        del updated[: len(updated) - MAX_OVERRIDE_EVALUATIONS]
    return updated


def refresh_override_outcomes(
    evaluations: list[CeoOverrideEvaluation], ceo_decisions: list[CeoDecisionRecord]
) -> list[CeoOverrideEvaluation]:
    """Keeps `outcome` in sync with its real source `CeoDecisionRecord`
    — never re-derived, only mirrored — so an override that started
    `"pending"` picks up its real `"correct"`/`"incorrect"` the moment
    `grade_ceo_decisions()` resolves the underlying trade."""
    by_decision_id = {d.id: d for d in ceo_decisions}
    changed = False
    updated: list[CeoOverrideEvaluation] = []
    for e in evaluations:
        d = by_decision_id.get(e.decision_id)
        if d is not None and d.outcome != e.outcome:
            updated.append(e.model_copy(update={"outcome": d.outcome, "updated_at": _now_iso()}))
            changed = True
        else:
            updated.append(e)
    return updated if changed else evaluations


def add_override_review(
    evaluation: CeoOverrideEvaluation, *, reviewer: AgentId, note: str
) -> CeoOverrideEvaluation:
    """A real, optional human/agent review note — never gates or changes
    `processQuality`/`outcome`, only records that a reviewer looked at
    this override and what they said."""
    return evaluation.model_copy(
        update={"reviewer": reviewer, "review_note": note, "reviewed_at": _now_iso(), "updated_at": _now_iso()}
    )


def compute_override_governance_summary(
    evaluations: list[CeoOverrideEvaluation], total_decision_count: int
) -> CeoOverrideGovernanceSummary:
    """The one real, disclosed aggregate — every field a direct count or
    a function already defined above. `overrideRatePct` is `None`, never
    a fabricated 0%, when there are no real decisions to divide by."""
    department_override_impact: dict[str, int] = {}
    for e in evaluations:
        for role in e.agreeing_departments:
            department_override_impact[role] = department_override_impact.get(role, 0) + 1
    return CeoOverrideGovernanceSummary(
        totalOverrideCount=len(evaluations),
        totalDecisionCount=total_decision_count,
        overrideRatePct=round(len(evaluations) / total_decision_count * 100.0, 1) if total_decision_count > 0 else None,
        justifiedCount=sum(1 for e in evaluations if e.process_quality == "justified"),
        unjustifiedCount=sum(1 for e in evaluations if e.process_quality == "unjustified"),
        mixedCount=sum(1 for e in evaluations if e.process_quality == "mixed"),
        notEnoughEvidenceCount=sum(1 for e in evaluations if e.process_quality == "not_enough_evidence"),
        outcomeCorrectCount=sum(1 for e in evaluations if e.outcome == "correct"),
        outcomeIncorrectCount=sum(1 for e in evaluations if e.outcome == "incorrect"),
        outcomePendingCount=sum(1 for e in evaluations if e.outcome == "pending"),
        outcomeUndecidableCount=sum(1 for e in evaluations if e.outcome == "undecidable"),
        departmentOverrideImpact=department_override_impact,
        sampleSizeSufficient=len(evaluations) >= MIN_OVERRIDE_SAMPLE_FOR_TREND,
        updatedAt=_now_iso(),
    )
