"""Covers app/compliance_incidents.py — CEO directive "Features 31-35:
Compliance, Governance & Continuous Improvement System," Feature 31 (the
Compliance Incident Resolution Engine). The lifecycle must be strictly
enforced (no OPEN -> RESOLVED shortcut), historical origin must never be
rewritten, resolution must never be fabricated, and duplicate incidents
must never be created for the same real Audit Log entry.
"""
from __future__ import annotations

from app.compliance_incidents import (
    ALLOWED_TRANSITIONS,
    MAX_COMPLIANCE_INCIDENTS,
    add_evidence,
    average_resolution_sim_days,
    begin_remediation,
    compute_incident_summary,
    fail_verification,
    is_overdue,
    reopen,
    severity_weighted_backlog,
    start_investigating,
    submit_for_verification,
    sync_incidents_from_audit_log,
    verify_and_resolve,
)
from app.schemas import AuditEntry, ComplianceIncident


def _now_iso() -> str:
    return "2026-01-01T00:00:00+00:00"


def _entry(*, entry_id: str = "audit-1", severity: str = "warning", sim_day: int = 5) -> AuditEntry:
    return AuditEntry(
        id=entry_id,
        timestamp=_now_iso(),
        simDay=sim_day,
        category="gatekeeper_rejection",  # type: ignore[arg-type]
        severity=severity,  # type: ignore[arg-type]
        department="Trade Gatekeeper",
        summary="Blocked a buy on NEXA.",
        detail="Risk manager alignment failed.",
        relatedId="proposal-1",
    )


def _open_incident(*, incident_id: str = "incident-audit-1", sim_day: int = 5) -> ComplianceIncident:
    return ComplianceIncident(
        id=incident_id,
        sourceEntryId="audit-1",
        category="gatekeeper_rejection",  # type: ignore[arg-type]
        severity="warning",  # type: ignore[arg-type]
        department="Trade Gatekeeper",
        summary="Blocked a buy on NEXA.",
        detail="Risk manager alignment failed.",
        relatedId="proposal-1",
        createdAt=_now_iso(),
        simDay=sim_day,
        status="open",
        updatedAt=_now_iso(),
    )


def _advance_to_awaiting_verification(incident: ComplianceIncident, *, deadline_sim_day: int = 5) -> ComplianceIncident:
    """Real, shared test helper — open -> investigating -> remediation ->
    awaiting_verification, asserting each real transition succeeds."""
    investigating = start_investigating(incident, owner="scout")
    assert investigating is not None
    remediating = begin_remediation(investigating, remediation_plan="Real remediation plan.", deadline_sim_day=deadline_sim_day)
    assert remediating is not None
    awaiting = submit_for_verification(remediating)
    assert awaiting is not None
    return awaiting


def _resolved_incident(*, sim_day: int = 1, resolution_sim_day: int = 4) -> ComplianceIncident:
    awaiting = _advance_to_awaiting_verification(_open_incident(sim_day=sim_day), deadline_sim_day=sim_day + 4)
    resolved = verify_and_resolve(awaiting, verifier="scout", root_cause="process_failure", corrective_action="Real fix applied.", sim_day=resolution_sim_day)
    assert resolved is not None
    return resolved


class TestSyncIncidentsFromAuditLog:
    def test_creates_a_real_incident_from_a_warning_entry(self) -> None:
        incidents = sync_incidents_from_audit_log([], [_entry()])
        assert len(incidents) == 1
        assert incidents[0].status == "open"
        assert incidents[0].source_entry_id == "audit-1"
        assert incidents[0].created_at == _now_iso()
        assert incidents[0].sim_day == 5

    def test_info_severity_never_becomes_an_incident(self) -> None:
        incidents = sync_incidents_from_audit_log([], [_entry(severity="info")])
        assert incidents == []

    def test_never_creates_a_duplicate_incident_for_the_same_source_entry(self) -> None:
        existing = sync_incidents_from_audit_log([], [_entry()])
        resynced = sync_incidents_from_audit_log(existing, [_entry()])
        assert len(resynced) == 1
        assert resynced[0] is existing[0]

    def test_never_touches_an_already_advanced_incident(self) -> None:
        existing = [_open_incident()]
        investigating = start_investigating(existing[0], owner="scout")
        assert investigating is not None
        resynced = sync_incidents_from_audit_log([investigating], [_entry()])
        assert resynced[0].status == "investigating"

    def test_caps_at_max_compliance_incidents(self) -> None:
        entries = [_entry(entry_id=f"audit-{i}") for i in range(MAX_COMPLIANCE_INCIDENTS + 10)]
        incidents = sync_incidents_from_audit_log([], entries)
        assert len(incidents) == MAX_COMPLIANCE_INCIDENTS
        assert incidents[-1].source_entry_id == f"audit-{MAX_COMPLIANCE_INCIDENTS + 9}"

    def test_historical_origin_is_the_real_source_entrys_own_timestamp_never_today(self) -> None:
        old_entry = _entry(sim_day=1)
        incidents = sync_incidents_from_audit_log([], [old_entry])
        assert incidents[0].sim_day == 1
        assert incidents[0].created_at == old_entry.timestamp


class TestLifecycleTransitions:
    def test_open_cannot_skip_directly_to_resolved(self) -> None:
        assert "resolved" not in ALLOWED_TRANSITIONS["open"]
        result = verify_and_resolve(_open_incident(), verifier="scout", root_cause="unknown", corrective_action="n/a", sim_day=6)
        assert result is None

    def test_open_to_investigating_sets_owner(self) -> None:
        result = start_investigating(_open_incident(), owner="scout")
        assert result is not None
        assert result.status == "investigating"
        assert result.owner == "scout"

    def test_investigating_cannot_go_straight_to_awaiting_verification(self) -> None:
        investigating = start_investigating(_open_incident(), owner="scout")
        assert investigating is not None
        result = submit_for_verification(investigating)
        assert result is None

    def test_full_real_lifecycle_to_resolution(self) -> None:
        awaiting = _advance_to_awaiting_verification(_open_incident(), deadline_sim_day=10)
        assert awaiting.status == "awaiting_verification"
        assert awaiting.deadline_sim_day == 10
        resolved = verify_and_resolve(awaiting, verifier="sentinel", root_cause="process_failure", corrective_action="Added a second check.", sim_day=9)
        assert resolved is not None
        assert resolved.status == "resolved"
        assert resolved.resolved_at is not None
        assert resolved.resolution_sim_day == 9
        assert resolved.root_cause == "process_failure"
        assert resolved.verification_status == "verified"
        assert resolved.verifier == "sentinel"

    def test_resolve_requires_awaiting_verification(self) -> None:
        investigating = start_investigating(_open_incident(), owner="scout")
        assert investigating is not None
        result = verify_and_resolve(investigating, verifier="scout", root_cause="unknown", corrective_action="n/a", sim_day=6)
        assert result is None

    def test_root_cause_unknown_is_a_valid_honest_answer(self) -> None:
        awaiting = _advance_to_awaiting_verification(_open_incident(sim_day=1))
        resolved = verify_and_resolve(awaiting, verifier="scout", root_cause="unknown", corrective_action="n/a", sim_day=4)
        assert resolved is not None
        assert resolved.root_cause == "unknown"


class TestVerificationCanFail:
    def test_fail_verification_bounces_back_to_remediation_not_resolved(self) -> None:
        awaiting = _advance_to_awaiting_verification(_open_incident())
        bounced = fail_verification(awaiting, note="The fix did not hold under real conditions.")
        assert bounced is not None
        assert bounced.status == "remediation"
        assert bounced.verification_status == "verification_failed"
        assert bounced.evidence[-1] == "The fix did not hold under real conditions."

    def test_fail_verification_only_valid_from_awaiting_verification(self) -> None:
        result = fail_verification(_open_incident(), note="n/a")
        assert result is None


class TestReopen:
    def test_resolved_can_reopen(self) -> None:
        resolved = _resolved_incident()
        reopened = reopen(resolved, note="Same underlying issue recurred.")
        assert reopened is not None
        assert reopened.status == "reopened"
        assert reopened.reopened_count == 1
        # Preserve the original resolution as real history — never wiped.
        assert reopened.root_cause == "process_failure"
        assert reopened.resolved_at == resolved.resolved_at

    def test_only_resolved_incidents_can_reopen(self) -> None:
        assert reopen(_open_incident(), note="n/a") is None

    def test_reopened_returns_to_investigating_not_open(self) -> None:
        resolved = _resolved_incident()
        reopened = reopen(resolved, note="recurred")
        assert reopened is not None
        assert "investigating" in ALLOWED_TRANSITIONS["reopened"]
        assert "open" not in ALLOWED_TRANSITIONS["reopened"]


class TestAddEvidence:
    def test_evidence_can_be_added_without_changing_status(self) -> None:
        updated = add_evidence(_open_incident(), note="Confirmed via a real second review.")
        assert updated.status == "open"
        assert updated.evidence == ["Confirmed via a real second review."]


class TestOverdue:
    def test_no_deadline_is_never_overdue(self) -> None:
        assert is_overdue(_open_incident(), current_sim_day=999) is False

    def test_past_deadline_while_unresolved_is_overdue(self) -> None:
        investigating = start_investigating(_open_incident(), owner="scout")
        assert investigating is not None
        remediating = begin_remediation(investigating, remediation_plan="p", deadline_sim_day=10)
        assert remediating is not None
        assert is_overdue(remediating, current_sim_day=11) is True
        assert is_overdue(remediating, current_sim_day=10) is False

    def test_resolved_is_never_overdue_even_past_deadline(self) -> None:
        awaiting = _advance_to_awaiting_verification(_open_incident(sim_day=1), deadline_sim_day=2)
        resolved = verify_and_resolve(awaiting, verifier="scout", root_cause="unknown", corrective_action="n/a", sim_day=100)
        assert resolved is not None
        assert is_overdue(resolved, current_sim_day=999) is False


class TestSeverityWeightedBacklog:
    def test_only_counts_unresolved_incidents(self) -> None:
        critical = _open_incident(incident_id="i-1").model_copy(update={"severity": "critical"})
        resolved = _resolved_incident()
        backlog = severity_weighted_backlog([critical, resolved])
        assert backlog > 0
        # Only the unresolved critical incident should contribute.
        assert backlog == severity_weighted_backlog([critical])


class TestAverageResolutionSimDays:
    def test_none_when_nothing_has_ever_resolved_not_a_fabricated_zero(self) -> None:
        assert average_resolution_sim_days([_open_incident()]) is None

    def test_real_average_over_actually_resolved_incidents(self) -> None:
        resolved = _resolved_incident(sim_day=1, resolution_sim_day=4)
        assert average_resolution_sim_days([resolved]) == 3.0


class TestComputeIncidentSummary:
    def test_empty_backlog_reports_honest_zeros_and_none(self) -> None:
        summary = compute_incident_summary([], current_sim_day=10)
        assert summary.total_count == 0
        assert summary.open_count == 0
        assert summary.resolved_count == 0
        assert summary.overdue_count == 0
        assert summary.average_resolution_sim_days is None

    def test_mixed_backlog_counts_correctly(self) -> None:
        open_incident = _open_incident(incident_id="i-open")
        investigating = start_investigating(_open_incident(incident_id="i-overdue"), owner="scout")
        assert investigating is not None
        overdue_incident = begin_remediation(investigating, remediation_plan="p", deadline_sim_day=1)
        assert overdue_incident is not None
        summary = compute_incident_summary([open_incident, overdue_incident], current_sim_day=100)
        assert summary.total_count == 2
        assert summary.open_count == 2
        assert summary.overdue_count == 1
