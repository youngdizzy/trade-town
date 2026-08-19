"""CEO directive "Features 31-35," Feature 35 — the Continuous
Compliance Improvement Loop, the final stage of the CEO's own
31->32->33->34->35 closed loop.

RESEARCH FIRST: closing this loop needed no new persisted state.
`ComplianceIncident` (Feature 31, `app/compliance_incidents.py`) already
carries every real fact the loop's own named stages need — INCIDENT
(the incident itself), ROOT CAUSE (`rootCause`, set once at
`verify_and_resolve()`, never guessed at creation time), REMEDIATION
(`correctiveAction`, the CEO's own real text). What this module adds is
MONITORING/OUTCOME/EFFECTIVENESS REVIEW: did the fix actually hold, read
purely from two already-real signals — whether the CEO ever explicitly
`reopen()`ed that exact case (the strongest, most direct evidence a fix
failed), and whether another real incident sharing the same root cause
later opened. Nothing here invents a "did it work" verdict from
anything but those two real, already-persisted facts.

WHAT THIS MODULE DELIBERATELY DOES NOT DO: it does not touch
`app/audit_log.py::compute_compliance_score()`. The CEO directive's own
Feature 35 rules require that any change to that formula be (1)
documented as a limitation, (2) proposed, and (3) only applied once the
CEO has explicitly authorized changing it — see this module's own
"Compliance Score formula" note in the Design Bible/Architecture.md.
Nothing here silently rewrites it, weakens it, or feeds its
`open_incident_count` count. Company Health integration instead adds a
genuinely NEW, separate `complianceHealth` sub-score to the EXISTING
Company Health architecture (`app/company_health.py`) — the same
"new dimension, not a rewritten old one" pattern that dimension's own
`risk_governance`/`decision_quality` siblings already established.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import (
    ComplianceIncident,
    ContinuousImprovementSummary,
    IncidentRootCause,
    RemediationEffectivenessRecord,
    RemediationEffectivenessState,
    RootCauseRecurrence,
)

# The CEO-facing Incident Cases UI's own existing default SLA window
# (`CompliancePanel.tsx`'s `deadlineSimDay = incident.simDay + 5`) is
# this codebase's own established real expectation for how long a
# remediation reasonably takes — reused here, not a fourth invented
# number, as the real, disclosed floor before "no recurrence yet" can
# honestly read as "the fix held" rather than "too soon to tell."
REMEDIATION_EVAL_WINDOW_SIM_DAYS = 5

# "Recurring" honestly means "happened more than once" — a structural
# count, not a statistical rate, so this floor is deliberately lower
# than the rate-verdict evidence floors (`MIN_ACCURACY_SAMPLE_FOR_VERDICT
# = 3`, `MIN_CONTROL_SAMPLE_FOR_VERDICT = 3`) Features 33/34 use for
# genuinely statistical pass/fail splits.
RECURRING_FAILURE_MIN_COUNT = 2

_EVER_RESOLVED_STATUSES = ("resolved", "reopened")


def compute_remediation_effectiveness(
    incidents: list[ComplianceIncident], *, current_sim_day: int
) -> list[RemediationEffectivenessRecord]:
    """One record per incident that has ever been resolved at least
    once (`rootCause`/`correctiveAction` are only ever set together, by
    `verify_and_resolve()`) — a currently-`reopened` incident still
    carries its prior resolution's real `rootCause`/`correctiveAction`/
    `resolvedAt` from before it reopened (see that function's own
    docstring: "never clears the original... from the prior
    resolution"), so it is included here too, correctly scored
    `ineffective` via its own `reopenedCount`."""
    ever_resolved = [i for i in incidents if i.status in _EVER_RESOLVED_STATUSES and i.root_cause is not None and i.resolved_at is not None and i.resolution_sim_day is not None]

    records: list[RemediationEffectivenessRecord] = []
    for incident in ever_resolved:
        root_cause = incident.root_cause
        resolved_at = incident.resolved_at
        resolution_sim_day = incident.resolution_sim_day
        assert root_cause is not None
        assert resolved_at is not None
        assert resolution_sim_day is not None

        recurrence_count = sum(
            1
            for other in incidents
            if other.id != incident.id
            and other.root_cause == root_cause
            and other.category == incident.category
            and other.department == incident.department
            and other.sim_day > resolution_sim_day
        )

        if incident.reopened_count > 0:
            state: RemediationEffectivenessState = "ineffective"
        elif current_sim_day - resolution_sim_day < REMEDIATION_EVAL_WINDOW_SIM_DAYS:
            state = "not_enough_evidence"
        elif recurrence_count == 0:
            state = "effective"
        else:
            state = "partially_effective"

        records.append(
            RemediationEffectivenessRecord(
                incidentId=incident.id,
                rootCause=root_cause,
                correctiveAction=incident.corrective_action or "",
                category=incident.category,
                department=incident.department,
                resolvedAt=resolved_at,
                resolutionSimDay=resolution_sim_day,
                reopenedCount=incident.reopened_count,
                recurrenceCount=recurrence_count,
                effectivenessState=state,
            )
        )
    return records


def compute_root_cause_recurrence(incidents: list[ComplianceIncident]) -> list[RootCauseRecurrence]:
    """Per real `rootCause` (only ever set once an incident has actually
    been resolved at least once), a coarse, disclosed-broader-than
    `recurrenceCount` count of every distinct incident that root cause
    has ever been recorded on — the directive's own literal "same root
    cause repeatedly produces incidents" reading, not narrowed by
    category/department the way per-incident effectiveness scoring
    above is."""
    by_root_cause: dict[IncidentRootCause, list[ComplianceIncident]] = {}
    for incident in incidents:
        if incident.root_cause is None:
            continue
        by_root_cause.setdefault(incident.root_cause, []).append(incident)

    recurrences: list[RootCauseRecurrence] = []
    for root_cause, group in by_root_cause.items():
        ordered = sorted(group, key=lambda i: i.created_at)
        recurrences.append(
            RootCauseRecurrence(
                rootCause=root_cause,
                incidentCount=len(group),
                recurringFailure=len(group) >= RECURRING_FAILURE_MIN_COUNT,
                firstOccurredAt=ordered[0].created_at,
                lastOccurredAt=ordered[-1].created_at,
                incidentIds=[i.id for i in ordered],
            )
        )
    recurrences.sort(key=lambda r: r.incident_count, reverse=True)
    return recurrences


def compute_continuous_improvement_summary(
    incidents: list[ComplianceIncident], *, current_sim_day: int
) -> ContinuousImprovementSummary:
    remediations = compute_remediation_effectiveness(incidents, current_sim_day=current_sim_day)
    recurrences = compute_root_cause_recurrence(incidents)
    return ContinuousImprovementSummary(
        remediations=remediations,
        rootCauseRecurrences=recurrences,
        effectiveCount=sum(1 for r in remediations if r.effectiveness_state == "effective"),
        partiallyEffectiveCount=sum(1 for r in remediations if r.effectiveness_state == "partially_effective"),
        ineffectiveCount=sum(1 for r in remediations if r.effectiveness_state == "ineffective"),
        notEnoughEvidenceCount=sum(1 for r in remediations if r.effectiveness_state == "not_enough_evidence"),
        recurringFailureCount=sum(1 for r in recurrences if r.recurring_failure),
        updatedAt=datetime.now(timezone.utc).isoformat(),
    )
