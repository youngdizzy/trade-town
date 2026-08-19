"""Covers app/continuous_improvement.py — CEO directive "Features 31-35:
Compliance, Governance & Continuous Improvement System," Feature 35 (the
Continuous Compliance Improvement Loop). A remediation must never read
EFFECTIVE before its real observation window has elapsed; a real
`reopen()` is the strongest possible evidence of failure and must always
win; and RECURRING FAILURE must be a real, disclosed count over real
root causes, never fabricated.
"""
from __future__ import annotations

from app.continuous_improvement import (
    RECURRING_FAILURE_MIN_COUNT,
    REMEDIATION_EVAL_WINDOW_SIM_DAYS,
    compute_continuous_improvement_summary,
    compute_remediation_effectiveness,
    compute_root_cause_recurrence,
)
from app.schemas import ComplianceIncident


def _now_iso() -> str:
    return "2026-01-01T00:00:00+00:00"


def _resolved_incident(
    *,
    incident_id: str,
    root_cause: str = "control_failure",
    category: str = "gatekeeper_rejection",
    department: str = "Trade Gatekeeper",
    sim_day: int = 5,
    resolution_sim_day: int = 6,
    reopened_count: int = 0,
    status: str = "resolved",
) -> ComplianceIncident:
    return ComplianceIncident(
        id=incident_id,
        sourceEntryId=f"audit-{incident_id}",
        category=category,  # type: ignore[arg-type]
        severity="warning",  # type: ignore[arg-type]
        department=department,
        summary="Blocked a buy on NEXA.",
        detail="Risk manager alignment failed.",
        createdAt=_now_iso(),
        simDay=sim_day,
        status=status,  # type: ignore[arg-type]
        resolvedAt=_now_iso(),
        resolutionSimDay=resolution_sim_day,
        verificationStatus="verified",
        verifier="sentinel",
        rootCause=root_cause,  # type: ignore[arg-type]
        correctiveAction="Tightened the check.",
        reopenedCount=reopened_count,
        updatedAt=_now_iso(),
    )


def _open_incident(*, incident_id: str) -> ComplianceIncident:
    return ComplianceIncident(
        id=incident_id,
        sourceEntryId=f"audit-{incident_id}",
        category="gatekeeper_rejection",  # type: ignore[arg-type]
        severity="warning",  # type: ignore[arg-type]
        department="Trade Gatekeeper",
        summary="Blocked a buy on NEXA.",
        detail="Risk manager alignment failed.",
        createdAt=_now_iso(),
        simDay=5,
        status="open",
        updatedAt=_now_iso(),
    )


class TestRemediationEffectiveness:
    def test_never_resolved_incidents_are_excluded_entirely(self) -> None:
        records = compute_remediation_effectiveness([_open_incident(incident_id="i1")], current_sim_day=100)
        assert records == []

    def test_too_soon_since_resolution_reads_not_enough_evidence(self) -> None:
        incident = _resolved_incident(incident_id="i1", resolution_sim_day=10)
        records = compute_remediation_effectiveness([incident], current_sim_day=10 + REMEDIATION_EVAL_WINDOW_SIM_DAYS - 1)
        assert records[0].effectiveness_state == "not_enough_evidence"

    def test_reopened_incident_always_reads_ineffective_even_after_the_window(self) -> None:
        incident = _resolved_incident(incident_id="i1", resolution_sim_day=10, reopened_count=1, status="reopened")
        records = compute_remediation_effectiveness([incident], current_sim_day=10 + REMEDIATION_EVAL_WINDOW_SIM_DAYS + 50)
        assert records[0].effectiveness_state == "ineffective"

    def test_no_recurrence_after_the_window_reads_effective(self) -> None:
        incident = _resolved_incident(incident_id="i1", resolution_sim_day=10)
        records = compute_remediation_effectiveness([incident], current_sim_day=10 + REMEDIATION_EVAL_WINDOW_SIM_DAYS)
        assert records[0].effectiveness_state == "effective"
        assert records[0].recurrence_count == 0

    def test_a_same_signature_incident_opening_after_resolution_reads_partially_effective(self) -> None:
        first = _resolved_incident(incident_id="i1", resolution_sim_day=10)
        later = _resolved_incident(incident_id="i2", sim_day=20, resolution_sim_day=25)
        records = compute_remediation_effectiveness([first, later], current_sim_day=10 + REMEDIATION_EVAL_WINDOW_SIM_DAYS)
        first_record = next(r for r in records if r.incident_id == "i1")
        assert first_record.recurrence_count == 1
        assert first_record.effectiveness_state == "partially_effective"

    def test_a_same_signature_incident_that_opened_before_resolution_does_not_count_as_recurrence(self) -> None:
        first = _resolved_incident(incident_id="i1", resolution_sim_day=10, sim_day=5)
        earlier = _resolved_incident(incident_id="i2", sim_day=3, resolution_sim_day=4)
        records = compute_remediation_effectiveness([first, earlier], current_sim_day=10 + REMEDIATION_EVAL_WINDOW_SIM_DAYS)
        first_record = next(r for r in records if r.incident_id == "i1")
        assert first_record.recurrence_count == 0
        assert first_record.effectiveness_state == "effective"

    def test_a_different_department_does_not_count_as_the_same_signature(self) -> None:
        first = _resolved_incident(incident_id="i1", resolution_sim_day=10)
        different_dept = _resolved_incident(incident_id="i2", sim_day=20, resolution_sim_day=25, department="Risk Engine")
        records = compute_remediation_effectiveness([first, different_dept], current_sim_day=10 + REMEDIATION_EVAL_WINDOW_SIM_DAYS)
        first_record = next(r for r in records if r.incident_id == "i1")
        assert first_record.recurrence_count == 0


class TestRootCauseRecurrence:
    def test_a_single_incident_with_a_root_cause_is_not_a_recurring_failure(self) -> None:
        incident = _resolved_incident(incident_id="i1", root_cause="human_error")
        recurrences = compute_root_cause_recurrence([incident])
        assert len(recurrences) == 1
        assert recurrences[0].incident_count == 1
        assert recurrences[0].recurring_failure is False

    def test_two_incidents_sharing_a_root_cause_across_different_categories_still_recur(self) -> None:
        first = _resolved_incident(incident_id="i1", root_cause="human_error", category="gatekeeper_rejection")
        second = _resolved_incident(incident_id="i2", root_cause="human_error", category="ceo_decision", department="Executive")
        recurrences = compute_root_cause_recurrence([first, second])
        assert recurrences[0].incident_count == RECURRING_FAILURE_MIN_COUNT
        assert recurrences[0].recurring_failure is True
        assert set(recurrences[0].incident_ids) == {"i1", "i2"}

    def test_incidents_without_a_root_cause_yet_are_excluded(self) -> None:
        recurrences = compute_root_cause_recurrence([_open_incident(incident_id="i1")])
        assert recurrences == []

    def test_recurrences_are_sorted_by_incident_count_descending(self) -> None:
        a1 = _resolved_incident(incident_id="a1", root_cause="human_error")
        a2 = _resolved_incident(incident_id="a2", root_cause="human_error")
        a3 = _resolved_incident(incident_id="a3", root_cause="human_error")
        b1 = _resolved_incident(incident_id="b1", root_cause="data_failure")
        recurrences = compute_root_cause_recurrence([a1, a2, a3, b1])
        assert [r.root_cause for r in recurrences] == ["human_error", "data_failure"]


class TestContinuousImprovementSummary:
    def test_summary_counts_match_the_underlying_records(self) -> None:
        never_reopened = _resolved_incident(incident_id="i1", resolution_sim_day=10)
        reopened = _resolved_incident(incident_id="i2", resolution_sim_day=10, reopened_count=1, status="reopened")
        summary = compute_continuous_improvement_summary([never_reopened, reopened], current_sim_day=10 + REMEDIATION_EVAL_WINDOW_SIM_DAYS)
        assert summary.effective_count == 1
        assert summary.ineffective_count == 1
        assert summary.partially_effective_count == 0
        assert summary.not_enough_evidence_count == 0
        assert len(summary.remediations) == 2

    def test_empty_incident_list_produces_an_honest_empty_summary(self) -> None:
        summary = compute_continuous_improvement_summary([], current_sim_day=50)
        assert summary.remediations == []
        assert summary.root_cause_recurrences == []
        assert summary.recurring_failure_count == 0
