"""Compliance, Audit & Governance System (CAGS) — Design Bible Chapter 73.

THE HONESTY BOUNDARY (read this before adding anything to the brief's
much longer list of sections):

This codebase has one player (no separate "User" identity distinct from
"CEO"), one broker (`PaperBroker`, 100% simulated — see app/broker.py's
own docstring), no credentials of any kind, and no per-event historical
version tag. So the brief's biggest sections are cut outright:

  - Per-event Broker/User/Software Version fields — cut from AuditEntry
    entirely rather than populated with a repeated constant on every
    single row.
  - Encrypted credentials / access permissions / a Security section —
    cut entirely. There is nothing to encrypt anywhere in this codebase.
  - A mutable Incident workflow (open -> acknowledged -> resolved,
    CEO-editable corrective actions, after-the-fact "Lessons Learned")
    — cut. Every incident here is resolved-by-construction the instant
    it's recorded (a blocked trade never executed; a Discipline Review
    is filed only after the trade already closed) — there is no real
    pending state to triage.
  - An in-game Version History browser — cut. CHANGELOG.md and git
    history are already this codebase's real, authoritative version
    record; a second in-game copy would drift.
  - The Institutional Time Machine's full arbitrary-instant state
    reconstruction — this codebase takes no periodic full-state
    snapshots. What ships is real: the Audit Log's own chronological
    order, covering every timestamped moment this codebase actually
    recorded — a real history browser, never a claim of omniscient
    rewind.

What IS real and newly built here — a genuine cross-cutting SYNTHESIS
layer over state this codebase already computes honestly, tying
together nine already-real, already-persisted source types with no
shared, searchable view until now:

  - CEO Decisions (including real overrides via the already-real
    `agreedWithAi` field, Chapter 70 Part 2).
  - Gatekeeper Rejections / Opportunity Rejections (real blocked
    trades, real reasons).
  - Critical Risk Warnings (Sentinel/Guardian's real gates).
  - Discipline Reviews (`weak`/`reckless` tiers).
  - Emergency Stop activation/resume (its own real CompanyMemory
    record, `category="emergency"`).
  - Defensive Mode activation/deactivation (Chapter 72's real
    BlackSwanEventRecord).
  - Crisis Briefings (Chapter 72, via their own real CompanyMemory
    record).
  - Rule Engine evaluations (real per-account custom rule checks,
    real corrective-action text reused verbatim).

Computed fresh per request (never persisted, never a new GameSaveState
field) — the identical convention app/knowledge_graph.py,
app/whatif.py, and app/regime_reconciliation.py already established for
a read-only, cross-cutting view.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.executive_intelligence import compute_executive_accuracy_scores
from app.risk_engine import SIM_MINUTES_PER_DAY
from app.rule_engine import evaluate_rules
from app.schemas import (
    Account,
    AuditEntry,
    BlackSwanEventRecord,
    CeoDecisionRecord,
    CeoOverrideRecord,
    ComplianceOverview,
    DisciplineReview,
    ExecutiveMeetingLogEntry,
    GatekeeperRejection,
    GovernanceLayer,
    MemoryRecord,
    OpportunityRejection,
    RiskWarning,
)

# Disclosed, static — the real order app/gatekeeper.py::evaluate_gatekeeper()
# checks in. Never re-derived or recomputed; if that function's real
# check order ever changes, this list must be updated to match, the same
# discipline app/regime_reconciliation.py already applies to
# REGIME_CONSISTENCY_MAP.
GOVERNANCE_LAYERS: list[GovernanceLayer] = [
    GovernanceLayer(order=1, name="Executive Board", module="app/executive_intelligence.py", description="Nine department opinions synthesized into one recommendation before a proposal ever reaches the Gatekeeper.", wired=True),
    GovernanceLayer(order=2, name="Decision Confidence", module="app/gatekeeper.py::_confidence_check", description="The proposal's own real Decision Confidence Engine score must clear a minimum threshold.", wired=True),
    GovernanceLayer(order=3, name="Risk Manager Alignment", module="app/gatekeeper.py::_risk_manager_check", description="Sentinel's real risk vote must not conflict with the CEO's chosen action.", wired=True),
    GovernanceLayer(order=4, name="CEO/AI Agreement", module="app/gatekeeper.py::_agreement_check", description="Tracks whether the CEO's choice matches the AI's own recommendation.", wired=True),
    GovernanceLayer(order=5, name="AI Debate Outcome", module="app/gatekeeper.py::_debate_check", description="The real bull/bear debate's own conclusion must not contradict the chosen action.", wired=True),
    GovernanceLayer(order=6, name="Portfolio Exposure", module="app/gatekeeper.py::_exposure_check", description="Guardian's real concentration/exposure check against current RiskLimits.", wired=True),
    GovernanceLayer(order=7, name="Correlation", module="app/gatekeeper.py::_correlation_check", description="Real category co-occurrence across current open positions.", wired=True),
    GovernanceLayer(order=8, name="Active Risk Warnings", module="app/gatekeeper.py::_risk_warning_check", description="Any real, currently-active critical RiskWarning blocks the trade outright.", wired=True),
    GovernanceLayer(order=9, name="Market Intelligence Quality", module="app/gatekeeper.py::_market_intelligence_check", description="Real Market Quality tier must not read avoid_trading.", wired=True),
    GovernanceLayer(order=10, name="Weighted Executive Recommendation", module="app/gatekeeper.py::_weighted_executive_check", description="Chapter 70 Part 3's real per-department influence-weighted recommendation, advisory-only — can contribute to a rejection, never force an approval.", wired=True),
    GovernanceLayer(order=11, name="Institutional Rule Engine", module="app/rule_engine.py", description="Real, per-account custom rules (Chapter 69 Part 3) — not yet routed into live trade execution for non-primary accounts. Evaluated on demand, shown here for transparency, not enforced in this pipeline.", wired=False),
    GovernanceLayer(order=12, name="Broker (PaperBroker)", module="app/broker.py", description="100% simulated fill logic — no real broker connection exists anywhere in this codebase.", wired=True),
    GovernanceLayer(order=13, name="Execution", module="app/portfolio.py", description="Real position open/close against the company's own simulated paper portfolio.", wired=True),
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sim_day_from_minutes(sim_minutes: int) -> int:
    return sim_minutes // SIM_MINUTES_PER_DAY


def _entries_from_ceo_decisions(decisions: list[CeoDecisionRecord], current_sim_day: int) -> list[AuditEntry]:
    entries: list[AuditEntry] = []
    for d in decisions:
        override = not d.agreed_with_ai
        summary = f"{'Overrode' if override else 'Followed'} AI recommendation on {d.symbol}: chose {d.ceo_decision}, AI said {d.ai_recommendation}."
        detail = f"Outcome: {d.outcome}. Resolved by: {d.resolved_by}."
        entries.append(
            AuditEntry(
                id=f"audit-ceo-{d.id}",
                timestamp=d.created_at,
                simDay=current_sim_day,
                category="ceo_decision",
                severity="warning" if override else "info",
                department="Executive",
                summary=summary,
                detail=detail,
                relatedId=d.proposal_id,
            )
        )
    return entries


def _entries_from_gatekeeper_rejections(rejections: list[GatekeeperRejection], current_sim_day: int) -> list[AuditEntry]:
    return [
        AuditEntry(
            id=f"audit-gk-{r.id}",
            timestamp=r.created_at,
            simDay=_sim_day_from_minutes(r.rejected_sim_minutes),
            category="gatekeeper_rejection",
            severity="warning",
            department="Trade Gatekeeper",
            summary=f"Blocked a {r.ceo_choice} on {r.symbol}.",
            detail="; ".join(r.reasons) if r.reasons else "No specific reason on file.",
            relatedId=r.proposal_id,
        )
        for r in rejections
    ]


def _entries_from_opportunity_rejections(rejections: list[OpportunityRejection], current_sim_day: int) -> list[AuditEntry]:
    return [
        AuditEntry(
            id=f"audit-opp-{r.id}",
            timestamp=r.created_at,
            simDay=_sim_day_from_minutes(r.rejected_sim_minutes),
            category="opportunity_rejection",
            severity="info",
            department="Opportunity Gatekeeper",
            summary=f"A {r.symbol} candidate never became a real proposal (would have recommended {r.would_have_recommended}).",
            detail="; ".join(r.reasons) if r.reasons else "No specific reason on file.",
            relatedId=r.id,
        )
        for r in rejections
    ]


def _entries_from_risk_warnings(warnings: list[RiskWarning], current_sim_day: int) -> list[AuditEntry]:
    return [
        AuditEntry(
            id=f"audit-risk-{w.id}",
            timestamp=w.created_at,
            simDay=current_sim_day,
            category="risk_warning",
            severity=w.severity,
            department="Risk",
            summary=f"Risk warning on {w.symbol}.",
            detail=w.message,
            relatedId=w.symbol,
        )
        for w in warnings
        if w.severity == "critical"
    ]


def _entries_from_discipline_reviews(reviews: list[DisciplineReview]) -> list[AuditEntry]:
    entries: list[AuditEntry] = []
    for r in reviews:
        if r.tier not in ("weak", "reckless"):
            continue
        entries.append(
            AuditEntry(
                id=f"audit-discipline-{r.id}",
                timestamp=r.created_at,
                simDay=r.sim_day,
                category="discipline_review",
                severity="critical" if r.tier == "reckless" else "warning",
                department="Discipline Chamber",
                summary=f"{r.tier.title()} process on a {r.symbol} {r.outcome} ({r.trade_pnl_pct:+.1f}%).",
                detail=r.summary,
                relatedId=r.decision_id,
            )
        )
    return entries


def _entries_from_memory(memory: list[MemoryRecord], current_sim_day: int) -> list[AuditEntry]:
    entries: list[AuditEntry] = []
    for m in memory:
        if m.category == "emergency":
            entries.append(
                AuditEntry(
                    id=f"audit-emergency-{m.id}",
                    timestamp=m.timestamp,
                    simDay=current_sim_day,
                    category="emergency_stop",
                    severity="critical" if "activated" in m.title.lower() else "info",
                    department="CEO",
                    summary=m.title,
                    detail=m.body,
                    relatedId=None,
                )
            )
        elif m.category == "alert" and m.title.startswith("Crisis Briefing"):
            entries.append(
                AuditEntry(
                    id=f"audit-crisis-{m.id}",
                    timestamp=m.timestamp,
                    simDay=current_sim_day,
                    category="crisis_briefing",
                    severity="critical",
                    department="Black Swan Intelligence",
                    summary=m.title,
                    detail=m.body,
                    relatedId=None,
                )
            )
        elif m.category == "alert" and m.title.startswith("Trading Mode changed"):
            # Design Bible Chapter 74 — app/trading_modes.py's change_trading_mode().
            entries.append(
                AuditEntry(
                    id=f"audit-tradingmode-{m.id}",
                    timestamp=m.timestamp,
                    simDay=current_sim_day,
                    category="trading_mode_change",
                    severity="info",
                    department="Trading Modes",
                    summary=m.title,
                    detail=m.body,
                    relatedId=None,
                )
            )
        elif m.category == "alert" and m.title.startswith("Daily Circuit Breaker"):
            # Design Bible Chapter 74 — app/trading_modes.py's build_circuit_breaker_tier_memory().
            entries.append(
                AuditEntry(
                    id=f"audit-circuitbreaker-{m.id}",
                    timestamp=m.timestamp,
                    simDay=current_sim_day,
                    category="circuit_breaker_tier",
                    severity="warning" if "tier3" in m.title.lower() or "tier4" in m.title.lower() else "info",
                    department="Trading Modes",
                    summary=m.title,
                    detail=m.body,
                    relatedId=None,
                )
            )
    return entries


def _entries_from_black_swan_events(events: list[BlackSwanEventRecord], current_sim_day: int) -> list[AuditEntry]:
    return [
        AuditEntry(
            id=f"audit-defensive-{e.id}",
            timestamp=e.deactivated_at,
            simDay=current_sim_day,
            category="defensive_mode",
            severity="warning" if e.peak_tier in ("orange", "red", "critical") else "info",
            department="Black Swan Intelligence",
            summary=f"Defensive Mode episode ended — peaked at {e.peak_tier.upper()}.",
            detail=e.lesson,
            relatedId=e.id,
        )
        for e in events
    ]


def _entries_from_rule_engine(accounts: list[Account], sim_day: int) -> list[AuditEntry]:
    entries: list[AuditEntry] = []
    for account in accounts:
        if not account.custom_rules:
            continue
        result = evaluate_rules(account, sim_day=sim_day)
        for check in result.checks:
            if check.passed:
                continue
            entries.append(
                AuditEntry(
                    id=f"audit-rule-{account.id}-{check.rule_id}-{sim_day}",
                    timestamp=_now_iso(),
                    simDay=sim_day,
                    category="rule_violation",
                    severity="warning",
                    department="Institutional Rule Engine",
                    summary=f"{account.name}: {check.label} rule failed.",
                    detail=f"{check.detail} {check.corrective_action or ''}".strip(),
                    relatedId=account.id,
                )
            )
    return entries


def compute_audit_log(
    *,
    ceo_decisions: list[CeoDecisionRecord],
    gatekeeper_rejections: list[GatekeeperRejection],
    opportunity_rejections: list[OpportunityRejection],
    risk_warnings: list[RiskWarning],
    discipline_reviews: list[DisciplineReview],
    memory: list[MemoryRecord],
    black_swan_events: list[BlackSwanEventRecord],
    accounts: list[Account],
    current_sim_day: int,
) -> list[AuditEntry]:
    """The unified Audit Log — every real event this company already
    produces, merged and sorted newest-first. Never persisted; computed
    fresh from state this codebase already holds."""
    entries: list[AuditEntry] = [
        *_entries_from_ceo_decisions(ceo_decisions, current_sim_day),
        *_entries_from_gatekeeper_rejections(gatekeeper_rejections, current_sim_day),
        *_entries_from_opportunity_rejections(opportunity_rejections, current_sim_day),
        *_entries_from_risk_warnings(risk_warnings, current_sim_day),
        *_entries_from_discipline_reviews(discipline_reviews),
        *_entries_from_memory(memory, current_sim_day),
        *_entries_from_black_swan_events(black_swan_events, current_sim_day),
        *_entries_from_rule_engine(accounts, current_sim_day),
    ]
    entries.sort(key=lambda e: e.timestamp, reverse=True)
    return entries


def filter_audit_log(
    entries: list[AuditEntry],
    *,
    category: str | None = None,
    severity: str | None = None,
    search: str | None = None,
    limit: int = 200,
) -> list[AuditEntry]:
    """Real, working server-side filtering — never a UI placeholder over
    an unfiltered dump."""
    filtered = entries
    if category is not None:
        filtered = [e for e in filtered if e.category == category]
    if severity is not None:
        filtered = [e for e in filtered if e.severity == severity]
    if search:
        needle = search.lower()
        filtered = [e for e in filtered if needle in e.summary.lower() or needle in e.detail.lower() or needle in e.department.lower()]
    return filtered[:limit]


def compute_incidents(entries: list[AuditEntry]) -> list[AuditEntry]:
    """A pure filter over the same Audit Log — never a second,
    independently-built list that could drift from it."""
    return [e for e in entries if e.severity != "info"]


def compute_ceo_overrides(ceo_decisions: list[CeoDecisionRecord]) -> list[CeoOverrideRecord]:
    return [
        CeoOverrideRecord(
            id=f"override-{d.id}",
            proposalId=d.proposal_id,
            symbol=d.symbol,
            aiRecommendation=d.ai_recommendation,
            ceoDecision=d.ceo_decision,
            outcome=d.outcome,
            createdAt=d.created_at,
        )
        for d in ceo_decisions
        if not d.agreed_with_ai
    ]


def compute_compliance_score(incidents: list[AuditEntry]) -> float:
    """Disclosed, simple, real — a real count over the real Audit Log,
    never a fitted or backtested model."""
    return round(max(40.0, 100.0 - min(60.0, 5.0 * len(incidents))), 1)


def compute_compliance_overview(
    *,
    entries: list[AuditEntry],
    ceo_decisions: list[CeoDecisionRecord],
    meeting_log: list[ExecutiveMeetingLogEntry],
    defensive_mode_active: bool,
    emergency_stop_active: bool,
) -> ComplianceOverview:
    incidents = compute_incidents(entries)
    critical_incidents = [i for i in incidents if i.severity == "critical"]
    overrides = compute_ceo_overrides(ceo_decisions)
    override_rate = round(len(overrides) / len(ceo_decisions) * 100, 1) if ceo_decisions else 0.0
    return ComplianceOverview(
        complianceScore=compute_compliance_score(incidents),
        openIncidentCount=len(incidents),
        criticalIncidentCount=len(critical_incidents),
        totalAuditEntries=len(entries),
        ceoOverrideCount=len(overrides),
        ceoOverrideRatePct=override_rate,
        defensiveModeActive=defensive_mode_active,
        emergencyStopActive=emergency_stop_active,
        executiveAccuracy=compute_executive_accuracy_scores(meeting_log, ceo_decisions),
        updatedAt=_now_iso(),
    )
