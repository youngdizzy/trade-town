"""Design Bible Chapter 73 — Compliance, Audit & Governance System
(CAGS) endpoints. See app/audit_log.py's module docstring for the full
honesty boundary. The original endpoints below are read-only, computed
fresh per request from state this codebase already persisted — no
GameSaveState field, no WS broadcast change.

CEO directive "Features 31-35," Feature 31 added the first real, mutable
endpoints in this router — the Compliance Incident Resolution Engine's
lifecycle (see app/compliance_incidents.py). These ARE persisted
(GameSaveState.compliance_incidents) and DO mutate state, deliberately
kept out of the WS broadcast the same way the rest of CAGS already is
(this router's own original docstring: "genuine on-demand fetch," never
part of gameStore) — a 500-entry incident backlog has no reason to ride
every real-time tick broadcast when the Compliance panel already fetches
on demand.

Feature 32 adds the CEO Override Governance endpoints on the same
pattern (see app/override_governance.py) — real, persisted
CeoOverrideEvaluations, also kept off the WS broadcast.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from app.audit_log import (
    GOVERNANCE_LAYERS,
    compute_audit_log,
    compute_ceo_overrides,
    compute_compliance_overview,
    compute_incidents,
    filter_audit_log,
)
from app.compliance_incidents import compute_incident_summary
from app.continuous_improvement import compute_continuous_improvement_summary
from app.control_effectiveness import compute_control_effectiveness
from app.override_governance import compute_override_governance_summary
from app.persistence import persist_modules
from app.portfolio import sim_minutes
from app.schemas import (
    AgentId,
    AuditEntry,
    CeoOverrideEvaluation,
    CeoOverrideGovernanceSummary,
    CeoOverrideRecord,
    ComplianceIncident,
    ComplianceIncidentSummary,
    ComplianceOverview,
    ContinuousImprovementSummary,
    ControlEffectivenessSummary,
    GovernanceLayer,
    IncidentRootCause,
)
from app.state import game_state

router = APIRouter(prefix="/api/audit", tags=["audit"])


async def _current_audit_log() -> list[AuditEntry]:
    state = await game_state.snapshot()
    current_sim_day = sim_minutes(state.time) // 1440
    return compute_audit_log(
        ceo_decisions=state.ceo_decisions,
        gatekeeper_rejections=state.gatekeeper_rejections,
        opportunity_rejections=state.opportunity_rejections,
        risk_warnings=state.risk_warnings,
        discipline_reviews=state.discipline_reviews,
        memory=state.memory,
        black_swan_events=state.black_swan_events,
        accounts=state.accounts,
        current_sim_day=current_sim_day,
    )


@router.get("/log", response_model=list[AuditEntry])
async def get_audit_log(
    category: str | None = Query(default=None),
    severity: str | None = Query(default=None),
    search: str | None = Query(default=None),
    limit: int = Query(default=200, ge=1, le=500),
) -> list[AuditEntry]:
    """The unified, searchable Audit Log — every real event this company
    already produces, newest first. `category`/`severity`/`search` are
    real, working server-side filters."""
    entries = await _current_audit_log()
    return filter_audit_log(entries, category=category, severity=severity, search=search, limit=limit)


@router.get("/incidents", response_model=list[AuditEntry])
async def get_incidents() -> list[AuditEntry]:
    """The same Audit Log, filtered to warning/critical severity only —
    never a second, independently-built incident list."""
    entries = await _current_audit_log()
    return compute_incidents(entries)


@router.get("/governance", response_model=list[GovernanceLayer])
async def get_governance() -> list[GovernanceLayer]:
    """The real, disclosed order app/gatekeeper.py checks a trade
    candidate in, plus the Institutional Rule Engine's real (still
    disconnected) position — never a new authority chain."""
    return GOVERNANCE_LAYERS


@router.get("/overview", response_model=ComplianceOverview)
async def get_compliance_overview() -> ComplianceOverview:
    """The Compliance Dashboard's real aggregate — see
    app/audit_log.py's compute_compliance_overview() for exactly which
    numbers are real counts vs. reused verbatim from an already-real
    source."""
    state = await game_state.snapshot()
    entries = await _current_audit_log()
    return compute_compliance_overview(
        entries=entries,
        ceo_decisions=state.ceo_decisions,
        meeting_log=state.executive_meeting_log,
        defensive_mode_active=state.defensive_mode.active,
        emergency_stop_active=state.emergency_stop.active,
    )


@router.get("/overrides", response_model=list[CeoOverrideRecord])
async def get_ceo_overrides() -> list[CeoOverrideRecord]:
    """Every real CEO decision that disagreed with the AI's own
    recommendation — sourced directly from CeoDecisionRecord.agreedWithAi
    (Chapter 70 Part 2)."""
    state = await game_state.snapshot()
    return compute_ceo_overrides(state.ceo_decisions)


# CEO directive "Features 31-35," Feature 31 — the Compliance Incident
# Resolution Engine. The real, persisted case list and its lifecycle
# mutations, distinct from /incidents above (which stays the original
# ephemeral Audit Log filter, untouched).


@router.get("/incidents/cases", response_model=list[ComplianceIncident])
async def get_compliance_incident_cases() -> list[ComplianceIncident]:
    """The real, persisted incident backlog with its full lifecycle —
    never recomputed from scratch each request the way /incidents above
    is; these are stateful records app/nexus.py's tick() syncs from the
    real Audit Log and this router's own POST endpoints below mutate."""
    state = await game_state.snapshot()
    return state.compliance_incidents


@router.get("/incidents/summary", response_model=ComplianceIncidentSummary)
async def get_compliance_incident_summary() -> ComplianceIncidentSummary:
    """The real, disclosed aggregate over the incident backlog above —
    see app/compliance_incidents.py's compute_incident_summary()."""
    state = await game_state.snapshot()
    return compute_incident_summary(state.compliance_incidents, state.time.day)


class OwnerRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    owner: AgentId


@router.post("/incidents/{incident_id}/investigate", response_model=ComplianceIncident)
async def start_investigating_incident(incident_id: str, payload: OwnerRequest) -> ComplianceIncident:
    state, error = await game_state.start_investigating_incident(incident_id, payload.owner)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return next(i for i in state.compliance_incidents if i.id == incident_id)


class RemediationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    remediation_plan: str
    deadline_sim_day: int


@router.post("/incidents/{incident_id}/remediate", response_model=ComplianceIncident)
async def begin_incident_remediation(incident_id: str, payload: RemediationRequest) -> ComplianceIncident:
    state, error = await game_state.begin_incident_remediation(
        incident_id, payload.remediation_plan, payload.deadline_sim_day
    )
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return next(i for i in state.compliance_incidents if i.id == incident_id)


class NoteRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    note: str


@router.post("/incidents/{incident_id}/evidence", response_model=ComplianceIncident)
async def add_incident_evidence(incident_id: str, payload: NoteRequest) -> ComplianceIncident:
    state, error = await game_state.add_incident_evidence(incident_id, payload.note)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return next(i for i in state.compliance_incidents if i.id == incident_id)


@router.post("/incidents/{incident_id}/submit-verification", response_model=ComplianceIncident)
async def submit_incident_for_verification(incident_id: str) -> ComplianceIncident:
    state, error = await game_state.submit_incident_for_verification(incident_id)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return next(i for i in state.compliance_incidents if i.id == incident_id)


@router.post("/incidents/{incident_id}/fail-verification", response_model=ComplianceIncident)
async def fail_incident_verification(incident_id: str, payload: NoteRequest) -> ComplianceIncident:
    state, error = await game_state.fail_incident_verification(incident_id, payload.note)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return next(i for i in state.compliance_incidents if i.id == incident_id)


class ResolveRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    verifier: AgentId
    root_cause: IncidentRootCause
    corrective_action: str


@router.post("/incidents/{incident_id}/resolve", response_model=ComplianceIncident)
async def verify_and_resolve_incident(incident_id: str, payload: ResolveRequest) -> ComplianceIncident:
    state, error = await game_state.verify_and_resolve_incident(
        incident_id, payload.verifier, payload.root_cause, payload.corrective_action
    )
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return next(i for i in state.compliance_incidents if i.id == incident_id)


@router.post("/incidents/{incident_id}/reopen", response_model=ComplianceIncident)
async def reopen_incident(incident_id: str, payload: NoteRequest) -> ComplianceIncident:
    state, error = await game_state.reopen_incident(incident_id, payload.note)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return next(i for i in state.compliance_incidents if i.id == incident_id)


# CEO directive "Features 31-35," Feature 32 — CEO Override Governance.
# The real, persisted override-evaluation list and its one real
# mutation (a reviewer's note), distinct from /overrides above (the
# original ephemeral CeoOverrideRecord list, untouched).


@router.get("/overrides/evaluations", response_model=list[CeoOverrideEvaluation])
async def get_ceo_override_evaluations() -> list[CeoOverrideEvaluation]:
    """The real, persisted override backlog — synced/refreshed every
    tick from the real CeoDecisionRecord/ExecutiveMeetingLogEntry lists
    (app/nexus.py's tick(), never recomputed from scratch each request)."""
    state = await game_state.snapshot()
    return state.ceo_override_evaluations


@router.get("/overrides/summary", response_model=CeoOverrideGovernanceSummary)
async def get_ceo_override_governance_summary() -> CeoOverrideGovernanceSummary:
    """The real, disclosed aggregate over the override backlog — see
    app/override_governance.py's compute_override_governance_summary()."""
    state = await game_state.snapshot()
    return compute_override_governance_summary(state.ceo_override_evaluations, len(state.ceo_decisions))


class OverrideReviewRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    reviewer: AgentId
    note: str


@router.post("/overrides/{evaluation_id}/review", response_model=CeoOverrideEvaluation)
async def add_ceo_override_review(evaluation_id: str, payload: OverrideReviewRequest) -> CeoOverrideEvaluation:
    state, error = await game_state.add_override_review(evaluation_id, payload.reviewer, payload.note)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return next(e for e in state.ceo_override_evaluations if e.id == evaluation_id)


# CEO directive "Features 31-35," Feature 34 — Compliance Control
# Effectiveness. Read-only, computed fresh per request from state this
# codebase already persisted — no GameSaveState field, no WS broadcast
# change, the same original CAGS convention this router's own module
# docstring describes (see app/control_effectiveness.py's module
# docstring for the full research finding and attribution-honesty rule).


@router.get("/controls/effectiveness", response_model=ControlEffectivenessSummary)
async def get_control_effectiveness() -> ControlEffectivenessSummary:
    """Per-control effectiveness for all 11 real Gatekeeper checks — did
    each control actually prevent or detect what it was designed to
    address, backed only by confirmed, unambiguously-attributed real
    outcomes (see app/control_effectiveness.py)."""
    state = await game_state.snapshot()
    return compute_control_effectiveness(state.decisions, state.gatekeeper_rejections)


# CEO directive "Features 31-35," Feature 35 — the Continuous Compliance
# Improvement Loop. Read-only, computed fresh per request over
# `state.compliance_incidents` (Feature 31, already persisted) — no new
# GameSaveState field, the same original CAGS convention as Feature 34
# (see app/continuous_improvement.py's module docstring).


@router.get("/continuous-improvement", response_model=ContinuousImprovementSummary)
async def get_continuous_improvement() -> ContinuousImprovementSummary:
    """Did a real remediation actually hold, and is any real root cause
    recurring across the real incident backlog — see
    app/continuous_improvement.py for the exact evidence and honesty
    rules."""
    state = await game_state.snapshot()
    current_sim_day = sim_minutes(state.time) // 1440
    return compute_continuous_improvement_summary(state.compliance_incidents, current_sim_day=current_sim_day)
