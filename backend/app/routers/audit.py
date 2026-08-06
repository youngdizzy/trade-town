"""Design Bible Chapter 73 — Compliance, Audit & Governance System
(CAGS) endpoints. See app/audit_log.py's module docstring for the full
honesty boundary. Everything here is read-only, computed fresh per
request from state this codebase already persists — no new
GameSaveState field, no WS broadcast change.
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.audit_log import (
    GOVERNANCE_LAYERS,
    compute_audit_log,
    compute_ceo_overrides,
    compute_compliance_overview,
    compute_incidents,
    filter_audit_log,
)
from app.portfolio import sim_minutes
from app.schemas import AuditEntry, CeoOverrideRecord, ComplianceOverview, GovernanceLayer
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
