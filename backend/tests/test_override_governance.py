"""Covers app/override_governance.py — CEO directive "Features 31-35:
Compliance, Governance & Continuous Improvement System," Feature 32
(CEO Override Governance). Process quality must be evaluated from
evidence available at decision time, never from the trade's own P&L
(no hindsight contamination); outcome must mirror CeoDecisionRecord
verbatim, never be re-derived a second way; missing evidence must
report NOT_ENOUGH_EVIDENCE, never a fabricated default.
"""
from __future__ import annotations

from app.override_governance import (
    MIN_OVERRIDE_SAMPLE_FOR_TREND,
    add_override_review,
    compute_override_governance_summary,
    evaluate_override_process_quality,
    refresh_override_outcomes,
    sync_override_evaluations,
)
from app.schemas import CeoDecisionRecord, CeoOverrideEvaluation, DepartmentOpinion, ExecutiveMeetingLogEntry


def _now_iso() -> str:
    return "2026-01-01T00:00:00+00:00"


def _opinion(role: str, stance: str, *, confidence: float = 70.0, evidence: list[str] | None = None, concerns: list[str] | None = None) -> DepartmentOpinion:
    return DepartmentOpinion(
        role=role,  # type: ignore[arg-type]
        departmentLabel=role,
        stance=stance,  # type: ignore[arg-type]
        summary="x",
        confidencePct=confidence,
        evidence=evidence or [],
        concerns=concerns or [],
    )


def _meeting_entry(*, opinions: list[DepartmentOpinion], decision_grade_score: float, proposal_id: str = "proposal-1", sim_day: int = 3) -> ExecutiveMeetingLogEntry:
    return ExecutiveMeetingLogEntry(
        id=f"meeting-{proposal_id}",
        proposalId=proposal_id,
        symbol="NEXA",
        simDay=sim_day,
        opinions=opinions,
        recommendedAction="trade_normally",
        recommendationReason="x",
        ceoDecision="wait",
        networkAgreed=False,
        decisionGrade="A" if decision_grade_score >= 90 else "C",
        decisionGradeScore=decision_grade_score,
        resolvedBy="ceo",
        createdAt=_now_iso(),
    )


def _override_decision(*, decision_id: str = "ceo-1", proposal_id: str = "proposal-1", outcome: str = "pending", override_reason: str | None = None) -> CeoDecisionRecord:
    return CeoDecisionRecord(
        id=decision_id,
        proposalId=proposal_id,
        symbol="NEXA",
        category="stock",  # type: ignore[arg-type]
        aiRecommendation="wait",
        ceoDecision="buy",
        agreedWithAi=False,
        decisionId=f"decision-{decision_id}",
        outcome=outcome,  # type: ignore[arg-type]
        resolvedBy="ceo",
        createdAt=_now_iso(),
        overrideReason=override_reason,
    )


def _agreeing_decision(*, decision_id: str = "ceo-agree-1") -> CeoDecisionRecord:
    return CeoDecisionRecord(
        id=decision_id,
        proposalId="proposal-agree-1",
        symbol="NEXA",
        category="stock",  # type: ignore[arg-type]
        aiRecommendation="buy",
        ceoDecision="buy",
        agreedWithAi=True,
        decisionId=f"decision-{decision_id}",
        outcome="pending",
        resolvedBy="ceo",
        createdAt=_now_iso(),
    )


class TestEvaluateOverrideProcessQuality:
    def test_no_meeting_entry_is_not_enough_evidence(self) -> None:
        quality, confidence, grade_score, grade, agreement, agreeing, evidence = evaluate_override_process_quality(None)
        assert quality == "not_enough_evidence"
        assert confidence is None
        assert grade_score is None
        assert grade is None
        assert agreement is None
        assert agreeing == []
        assert evidence == []

    def test_weak_and_contested_is_justified(self) -> None:
        opinions = [
            _opinion("research", "disagree", concerns=["Thin volume on the breakout."]),
            _opinion("risk", "disagree", evidence=["Correlation with existing position too high."]),
            _opinion("quant", "agree"),
        ]
        entry = _meeting_entry(opinions=opinions, decision_grade_score=65.0)
        quality, *_ = evaluate_override_process_quality(entry)
        assert quality == "justified"

    def test_strong_and_uncontested_is_unjustified(self) -> None:
        opinions = [
            _opinion("research", "agree"),
            _opinion("risk", "agree"),
            _opinion("quant", "agree"),
        ]
        entry = _meeting_entry(opinions=opinions, decision_grade_score=92.0)
        quality, *_ = evaluate_override_process_quality(entry)
        assert quality == "unjustified"

    def test_weak_and_uncontested_is_mixed(self) -> None:
        opinions = [_opinion("research", "agree"), _opinion("risk", "agree")]
        entry = _meeting_entry(opinions=opinions, decision_grade_score=65.0)
        quality, *_ = evaluate_override_process_quality(entry)
        assert quality == "mixed"

    def test_strong_and_contested_is_mixed(self) -> None:
        opinions = [_opinion("research", "agree"), _opinion("risk", "disagree"), _opinion("quant", "disagree")]
        entry = _meeting_entry(opinions=opinions, decision_grade_score=92.0)
        quality, *_ = evaluate_override_process_quality(entry)
        assert quality == "mixed"

    def test_dissenting_evidence_is_drawn_from_real_opposing_opinions_only(self) -> None:
        opinions = [
            _opinion("research", "agree", evidence=["Strong earnings beat."]),
            _opinion("risk", "disagree", evidence=["Position size already at limit."], concerns=["Correlation risk."]),
        ]
        entry = _meeting_entry(opinions=opinions, decision_grade_score=92.0)
        _, _, _, _, _, _, evidence = evaluate_override_process_quality(entry)
        assert evidence == ["Position size already at limit.", "Correlation risk."]

    def test_risk_department_stance_and_confidence_are_real_averages(self) -> None:
        opinions = [
            _opinion("research", "agree", confidence=80.0),
            _opinion("risk", "disagree", confidence=40.0),
        ]
        entry = _meeting_entry(opinions=opinions, decision_grade_score=70.0)
        _, confidence, grade_score, grade, agreement, agreeing, _ = evaluate_override_process_quality(entry)
        assert confidence == 60.0
        assert grade_score == 70.0
        assert grade == "C"
        assert agreement == 50.0
        assert agreeing == ["research"]


class TestSyncOverrideEvaluations:
    def test_creates_one_evaluation_per_real_override(self) -> None:
        decision = _override_decision()
        entry = _meeting_entry(opinions=[_opinion("research", "agree")], decision_grade_score=90.0)
        evaluations = sync_override_evaluations([], [decision], [entry])
        assert len(evaluations) == 1
        assert evaluations[0].decision_id == decision.id
        assert evaluations[0].original_recommendation == "wait"
        assert evaluations[0].ceo_decision == "buy"

    def test_never_creates_an_evaluation_for_an_agreeing_decision(self) -> None:
        evaluations = sync_override_evaluations([], [_agreeing_decision()], [])
        assert evaluations == []

    def test_never_creates_a_duplicate_for_the_same_decision(self) -> None:
        decision = _override_decision()
        existing = sync_override_evaluations([], [decision], [])
        resynced = sync_override_evaluations(existing, [decision], [])
        assert len(resynced) == 1
        assert resynced[0] is existing[0]

    def test_override_reason_is_carried_over_verbatim(self) -> None:
        decision = _override_decision(override_reason="Research thesis looked stale given yesterday's guidance cut.")
        evaluations = sync_override_evaluations([], [decision], [])
        assert evaluations[0].override_reason == "Research thesis looked stale given yesterday's guidance cut."

    def test_missing_meeting_entry_is_not_enough_evidence(self) -> None:
        decision = _override_decision()
        evaluations = sync_override_evaluations([], [decision], [])
        assert evaluations[0].process_quality == "not_enough_evidence"
        assert evaluations[0].original_confidence_pct is None

    def test_outcome_is_mirrored_never_re_derived(self) -> None:
        decision = _override_decision(outcome="undecidable")
        evaluations = sync_override_evaluations([], [decision], [])
        assert evaluations[0].outcome == "undecidable"


class TestRefreshOverrideOutcomes:
    def test_refreshes_outcome_when_underlying_decision_resolves(self) -> None:
        decision = _override_decision(outcome="pending")
        evaluations = sync_override_evaluations([], [decision], [])
        resolved_decision = decision.model_copy(update={"outcome": "correct"})
        refreshed = refresh_override_outcomes(evaluations, [resolved_decision])
        assert refreshed[0].outcome == "correct"

    def test_no_change_returns_the_same_list_object(self) -> None:
        decision = _override_decision(outcome="pending")
        evaluations = sync_override_evaluations([], [decision], [])
        refreshed = refresh_override_outcomes(evaluations, [decision])
        assert refreshed is evaluations


class TestAddOverrideReview:
    def test_records_a_real_reviewer_and_note_without_touching_process_quality_or_outcome(self) -> None:
        decision = _override_decision(outcome="incorrect")
        evaluation = sync_override_evaluations([], [decision], [])[0]
        reviewed = add_override_review(evaluation, reviewer="sentinel", note="Confirmed the risk desk's concern was on record.")
        assert reviewed.reviewer == "sentinel"
        assert reviewed.review_note == "Confirmed the risk desk's concern was on record."
        assert reviewed.reviewed_at is not None
        assert reviewed.process_quality == evaluation.process_quality
        assert reviewed.outcome == "incorrect"


class TestComputeOverrideGovernanceSummary:
    def test_empty_backlog_reports_honest_zeros_and_none_rate(self) -> None:
        summary = compute_override_governance_summary([], total_decision_count=0)
        assert summary.total_override_count == 0
        assert summary.override_rate_pct is None
        assert summary.sample_size_sufficient is False

    def test_real_override_rate_and_counts(self) -> None:
        justified = sync_override_evaluations(
            [], [_override_decision(decision_id="ceo-1", proposal_id="proposal-1")],
            [_meeting_entry(opinions=[_opinion("research", "disagree")], decision_grade_score=60.0, proposal_id="proposal-1")],
        )
        summary = compute_override_governance_summary(justified, total_decision_count=4)
        assert summary.total_override_count == 1
        assert summary.total_decision_count == 4
        assert summary.override_rate_pct == 25.0
        assert summary.justified_count == 1

    def test_sample_size_sufficiency_uses_the_disclosed_floor(self) -> None:
        evaluations: list[CeoOverrideEvaluation] = []
        for i in range(MIN_OVERRIDE_SAMPLE_FOR_TREND):
            evaluations = sync_override_evaluations(evaluations, [_override_decision(decision_id=f"ceo-{i}", proposal_id=f"proposal-{i}")], [])
        summary = compute_override_governance_summary(evaluations, total_decision_count=10)
        assert summary.sample_size_sufficient is True
        fewer = evaluations[:-1]
        summary_fewer = compute_override_governance_summary(fewer, total_decision_count=10)
        assert summary_fewer.sample_size_sufficient is False

    def test_department_override_impact_counts_real_agreeing_departments(self) -> None:
        entry = _meeting_entry(opinions=[_opinion("research", "agree"), _opinion("risk", "agree")], decision_grade_score=90.0, proposal_id="proposal-1")
        evaluations = sync_override_evaluations([], [_override_decision(proposal_id="proposal-1")], [entry])
        summary = compute_override_governance_summary(evaluations, total_decision_count=1)
        assert summary.department_override_impact == {"research": 1, "risk": 1}
