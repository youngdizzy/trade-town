"""app/compliance_incidents.py — CEO directive "Features 31-35:
Compliance, Governance & Continuous Improvement System," Feature 31 (the
first stage of the 31->32->33->34->35 loop; per the directive's own
staging rule, 32-35 do not start until this feature is tested, verified,
and documented).

RESEARCH FINDING, recorded here per the directive's own "research first"
rule: `app/audit_log.py`'s `compute_incidents()` already exists and is a
real, working filter — every Audit Log entry with `severity != "info"`.
But it is a PURE, STATELESS, EPHEMERAL view: `compute_audit_log()` is
"Computed fresh per request (never persisted, never a new GameSaveState
field)" (that module's own docstring), so `compute_incidents()` inherits
the same property — the exact "175 open incidents" the CEO's own brief
describes is recomputed from scratch on every `GET /api/audit/incidents`
call, with zero mutable state anywhere. The Incidents tab's own UI text
already discloses this honestly: "There is no open/acknowledged/resolved
workflow: incident resolution is not a real mechanic anywhere in this
codebase today." That sentence is the exact, confirmed gap this module
closes — not a rename, not a second incident-detection system.

WHAT THIS MODULE DOES NOT DO: it does not re-detect incidents a second
way. `sync_incidents_from_audit_log()` below is the ONLY creation path,
and it operates strictly downstream of `app/audit_log.py`'s own real
`compute_audit_log()`/`compute_incidents()` — every `ComplianceIncident`
traces back to exactly one real `AuditEntry.id` via `source_entry_id`,
deduplicated by that id (the same event can never open two incidents).
The underlying event catalogue (CEO overrides, Gatekeeper rejections,
critical Risk Warnings, weak/reckless Discipline Reviews, Emergency
Stop, Defensive Mode, Crisis Briefings, Rule Engine violations) is
entirely `audit_log.py`'s — this module adds only the stateful case
record and its lifecycle on top.

HISTORICAL PRESERVATION: the first real sync after this feature ships
opens one real `ComplianceIncident` per currently-open (severity !=
"info") `AuditEntry`, in status `"open"`, using that entry's own real
`created_at`/`sim_day` — never today's date, never a fabricated origin.
Every resolution-related field (`resolved_at`, `root_cause`,
`verification_status`, ...) starts at its honest default (`None` /
`"not_verified"`) because none of these 175 incidents has ever actually
been through a real resolution workflow — that is the literal truth
this codebase is in, not a bug to hide. Nothing here invents a
historical resolution time for an incident that was never really
resolved.

LIFECYCLE: a strict, enforced state machine (`ALLOWED_TRANSITIONS`)
matching the CEO's own specified order —

    open -> investigating -> remediation -> awaiting_verification -> resolved
                                                      |                  |
                                                      v                  v
                                                 remediation          reopened -> investigating

`open -> resolved` in one step is structurally impossible: every
transition function below checks the incident's CURRENT status against
`ALLOWED_TRANSITIONS` and returns `None` (never raises, never silently
succeeds) on an invalid request — the same "return None, let the caller
reject the request" convention `app/executive.py`'s `hold_proposal()`
already established. `verify_and_resolve()` is the only path to
`"resolved"`, and it is the only function that ever sets `resolved_at`/
`resolution_sim_day`/`root_cause` — together, atomically, never
partially. A verification can also fail (`fail_verification()`),
bouncing back to `"remediation"` rather than forcing a false resolution
— "Only mark an incident RESOLVED when the remediation has actually
been completed and, where required, verified" (the CEO's own words).

`root_cause` is genuinely optional at every stage except the one real
call that sets it (`verify_and_resolve`), and even there
`ROOT_CAUSE_UNKNOWN` ("unknown") is always an honest, valid answer —
never forced to a specific category when the evidence doesn't support
one.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.company_health import _SEVERITY_PENALTY
from app.schemas import (
    AgentId,
    AuditEntry,
    ComplianceIncident,
    ComplianceIncidentSummary,
    IncidentRootCause,
    IncidentStatus,
)

MAX_COMPLIANCE_INCIDENTS = 500

# The real, ordered lifecycle the CEO's own brief specified, as an
# explicit allowed-transitions map — the one source of truth every
# transition function below checks against, so "open -> resolved" is
# impossible by construction, not by convention.
ALLOWED_TRANSITIONS: dict[IncidentStatus, frozenset[IncidentStatus]] = {
    "open": frozenset({"investigating"}),
    "investigating": frozenset({"remediation"}),
    "remediation": frozenset({"awaiting_verification"}),
    "awaiting_verification": frozenset({"resolved", "remediation"}),
    "resolved": frozenset({"reopened"}),
    "reopened": frozenset({"investigating"}),
}

# Reused verbatim from app/company_health.py's own real Operational
# Stability penalty table — the same relative critical/warning/info
# weighting, never a second, independently-invented severity scale.
SEVERITY_WEIGHT: dict[str, float] = dict(_SEVERITY_PENALTY)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def sync_incidents_from_audit_log(
    existing: list[ComplianceIncident], audit_entries: list[AuditEntry]
) -> list[ComplianceIncident]:
    """The one real creation path. Opens a new `ComplianceIncident` for
    every real Audit Log entry with `severity != "info"` (the exact same
    filter `app/audit_log.py`'s own `compute_incidents()` already
    applies — reused, never reinvented) that doesn't already have one,
    matched by `source_entry_id` — the real, working deduplication this
    directive's own testing requirements ask for. Never touches an
    incident that already exists; existing incidents keep their real,
    possibly-advanced lifecycle state untouched."""
    known_source_ids = {i.source_entry_id for i in existing}
    new_incidents = [
        ComplianceIncident(
            id=f"incident-{entry.id}",
            sourceEntryId=entry.id,
            category=entry.category,
            severity=entry.severity,
            department=entry.department,
            summary=entry.summary,
            detail=entry.detail,
            relatedId=entry.related_id,
            createdAt=entry.timestamp,
            simDay=entry.sim_day,
            status="open",
            updatedAt=_now_iso(),
        )
        for entry in audit_entries
        if entry.severity != "info" and entry.id not in known_source_ids
    ]
    if not new_incidents:
        return existing
    updated = [*existing, *new_incidents]
    if len(updated) > MAX_COMPLIANCE_INCIDENTS:
        del updated[: len(updated) - MAX_COMPLIANCE_INCIDENTS]
    return updated


def start_investigating(incident: ComplianceIncident, *, owner: AgentId) -> ComplianceIncident | None:
    if "investigating" not in ALLOWED_TRANSITIONS.get(incident.status, frozenset()):
        return None
    return incident.model_copy(update={"status": "investigating", "owner": owner, "updated_at": _now_iso()})


def begin_remediation(
    incident: ComplianceIncident, *, remediation_plan: str, deadline_sim_day: int
) -> ComplianceIncident | None:
    if "remediation" not in ALLOWED_TRANSITIONS.get(incident.status, frozenset()):
        return None
    return incident.model_copy(
        update={
            "status": "remediation",
            "remediation_plan": remediation_plan,
            "deadline_sim_day": deadline_sim_day,
            "updated_at": _now_iso(),
        }
    )


def add_evidence(incident: ComplianceIncident, *, note: str) -> ComplianceIncident:
    """Real evidence can be logged at any stage before resolution — this
    never itself transitions status, only appends to the honest,
    permanent evidence trail."""
    return incident.model_copy(update={"evidence": [*incident.evidence, note], "updated_at": _now_iso()})


def submit_for_verification(incident: ComplianceIncident) -> ComplianceIncident | None:
    if "awaiting_verification" not in ALLOWED_TRANSITIONS.get(incident.status, frozenset()):
        return None
    return incident.model_copy(update={"status": "awaiting_verification", "updated_at": _now_iso()})


def fail_verification(incident: ComplianceIncident, *, note: str) -> ComplianceIncident | None:
    """A real, honest outcome — the remediation did not actually hold up
    to verification. Bounces back to "remediation" rather than forcing a
    false resolution; never silently discards the failed attempt (kept
    as a real evidence entry)."""
    if incident.status != "awaiting_verification":
        return None
    return incident.model_copy(
        update={
            "status": "remediation",
            "verification_status": "verification_failed",
            "evidence": [*incident.evidence, note],
            "updated_at": _now_iso(),
        }
    )


def verify_and_resolve(
    incident: ComplianceIncident,
    *,
    verifier: AgentId,
    root_cause: IncidentRootCause,
    corrective_action: str,
    sim_day: int,
) -> ComplianceIncident | None:
    """The one and only real path to `status="resolved"`. Sets every
    resolution-related field together, atomically — never a partial
    resolution. `root_cause="unknown"` is always a valid, honest answer;
    nothing here forces a specific category the evidence doesn't
    support."""
    if "resolved" not in ALLOWED_TRANSITIONS.get(incident.status, frozenset()):
        return None
    now = _now_iso()
    return incident.model_copy(
        update={
            "status": "resolved",
            "resolved_at": now,
            "resolution_sim_day": sim_day,
            "verification_status": "verified",
            "verifier": verifier,
            "root_cause": root_cause,
            "corrective_action": corrective_action,
            "updated_at": now,
        }
    )


def reopen(incident: ComplianceIncident, *, note: str) -> ComplianceIncident | None:
    """RESOLVED -> REOPENED — the same underlying issue recurred. Never
    clears the original `resolved_at`/`root_cause`/`corrective_action`
    from the prior resolution (preserved as real history of what was
    tried); `reopened_count` increments so the recurrence is visible,
    not silently overwritten."""
    if incident.status != "resolved":
        return None
    return incident.model_copy(
        update={
            "status": "reopened",
            "verification_status": "not_verified",
            "evidence": [*incident.evidence, note],
            "reopened_count": incident.reopened_count + 1,
            "updated_at": _now_iso(),
        }
    )


def is_overdue(incident: ComplianceIncident, current_sim_day: int) -> bool:
    """`False` (never `None`) once resolved or once no deadline has ever
    been set — a real SLA deadline is only stamped at
    `begin_remediation()`, matching the CEO's own instruction not to
    guess a deadline before anyone has assessed the real work involved."""
    if incident.status == "resolved" or incident.deadline_sim_day is None:
        return False
    return current_sim_day > incident.deadline_sim_day


def severity_weighted_backlog(incidents: list[ComplianceIncident]) -> float:
    """The real, disclosed sum of `SEVERITY_WEIGHT` over every
    unresolved incident — critical incidents count for more than
    warnings, reusing Company Health's own existing weight table rather
    than inventing a second one."""
    return round(sum(SEVERITY_WEIGHT.get(i.severity, 2.0) for i in incidents if i.status != "resolved"), 1)


def average_resolution_sim_days(incidents: list[ComplianceIncident]) -> float | None:
    """`None` (NOT_ENOUGH_EVIDENCE) when nothing has ever been resolved
    through a real lifecycle yet — never a fabricated 0. Only counts an
    incident actually resolved via `verify_and_resolve()`
    (`resolution_sim_day` is set only there), so a `"reopened"`
    incident's prior resolution still contributes its own real duration."""
    durations = [
        i.resolution_sim_day - i.sim_day
        for i in incidents
        if i.resolution_sim_day is not None and i.resolution_sim_day >= i.sim_day
    ]
    if not durations:
        return None
    return round(sum(durations) / len(durations), 1)


def compute_incident_summary(incidents: list[ComplianceIncident], current_sim_day: int) -> ComplianceIncidentSummary:
    """The one real, disclosed aggregate over the persisted incident
    backlog — every field is a direct count or reuses a function already
    defined above, never a second, independently-blended score."""
    resolved = [i for i in incidents if i.status == "resolved"]
    return ComplianceIncidentSummary(
        totalCount=len(incidents),
        openCount=len(incidents) - len(resolved),
        resolvedCount=len(resolved),
        overdueCount=sum(1 for i in incidents if is_overdue(i, current_sim_day)),
        reopenedIncidentCount=sum(1 for i in incidents if i.reopened_count > 0),
        severityWeightedBacklog=severity_weighted_backlog(incidents),
        averageResolutionSimDays=average_resolution_sim_days(incidents),
        updatedAt=_now_iso(),
    )
