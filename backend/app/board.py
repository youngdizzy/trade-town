"""Design Bible Chapter 70 Part 1 — Executive Board & CEO Intelligence
System: the Board Roster and the Board Report.

Both compose already-real signals rather than recompute or duplicate
them — the same discipline Chapter 70's own Ownership table applied
before any line here was written. `compute_board_roster()` is a pure,
fresh-per-request read over the same static `AGENT_PROFILES` every
agent-identity display in this codebase already uses. `generate_board_
report()` reuses `compute_department_activity()` (moved here from
app/executive_review.py, now shared by both), `CompanyHealth.
recommendations`, and `CompanyHealth.department_consensus` verbatim —
never a second, competing computation of any of them.

Three cadences, all real: "daily" (the same is_evening-only gate v0.7
Feature 51's Market Brief already established), "quarterly" (a new
day % 90 == 0 gate, the identical shape Weekly/Monthly already use),
and "emergency" (fired once on a real edge-crossing — an Emergency Stop
activation from any source, or a Black Swan tier crossing into
red/critical — never every tick while the condition holds). Weekly and
Monthly cadences are deliberately not built here: CoachReport and
ExecutiveReview already cover them, and duplicating either would be
exactly the kind of parallel system this Design Bible's own Appendix G
forbids.

Only 11 of the brief's own 12 named board seats are represented in the
roster. The 12th is never named anywhere in the source brief itself —
grepped, confirmed absent — and is deliberately not invented; see the
Design Bible chapter's own Implementation Notes for the full accounting
of what's real, what's deferred, and why.
"""
from __future__ import annotations

from app.agents import AGENT_PROFILES
from app.executive_review import compute_department_activity
from app.schemas import (
    AgentId,
    BlackSwanRiskTier,
    BoardReport,
    BoardReportCadence,
    BoardReportTrigger,
    BoardRoster,
    BoardSeat,
    CompanyHealth,
    DailyCircuitBreakerTier,
    ResearchItem,
    TradeDecision,
)

MAX_BOARD_REPORTS = 60

# Design Bible Chapter 70 Part 1's own Ownership table, verbatim: 7 of
# the brief's named Chief-Officer seats have no real occupant. Listed
# here, not invented — every title below is copied from the chapter's
# own source brief, never authored fresh for this module.
VACANT_BOARD_SEAT_TITLES: tuple[str, ...] = (
    "Chief Research Officer",
    "Chief Technology Officer",
    "Chief Operations Officer",
    "Chief Compliance Officer",
    "Chief Innovation Officer",
    "Chief Portfolio Officer",
    "Chief Market Intelligence Officer",
)

# The 4 real, filled seats — occupation strings are each agent's own
# real `AgentProfile.occupation` (agents.py / AgentProfiles.ts, kept in
# sync), never a fabricated "Chief X Officer" relabel. Three are close
# to, but not exact matches for, the brief's own CRO/Chief Knowledge
# Officer/CQO naming — disclosed as such in the Design Bible chapter
# rather than silently renamed to fit.
FILLED_BOARD_SEAT_AGENT_IDS: tuple[AgentId, ...] = ("cio", "keystone", "compass", "quant")


def compute_board_roster(*, now_iso: str) -> BoardRoster:
    seats: list[BoardSeat] = []
    for agent_id in FILLED_BOARD_SEAT_AGENT_IDS:
        profile = AGENT_PROFILES[agent_id]
        seats.append(BoardSeat(title=profile.occupation, agentId=agent_id, agentName=profile.name))
    for title in VACANT_BOARD_SEAT_TITLES:
        seats.append(BoardSeat(title=title, agentId=None, agentName=None))
    return BoardRoster(seats=seats, generatedAt=now_iso)


def _risk_assessment(black_swan_tier: BlackSwanRiskTier, circuit_breaker_tier: DailyCircuitBreakerTier) -> str:
    parts = [f"Black Swan Risk reads {black_swan_tier.upper()}"]
    if circuit_breaker_tier != "none":
        parts.append(f"the Daily Circuit Breaker is at {circuit_breaker_tier.upper()}")
    else:
        parts.append("the Daily Circuit Breaker is untriggered")
    return "; ".join(parts) + "."


def _problems(company_health: CompanyHealth, black_swan_tier: BlackSwanRiskTier, circuit_breaker_tier: DailyCircuitBreakerTier) -> list[str]:
    problems: list[str] = []
    if company_health.tier in ("needs_attention", "critical"):
        problems.append(f"Company Health is reading {company_health.tier.replace('_', ' ')}.")
    if black_swan_tier in ("red", "critical"):
        problems.append(f"Black Swan Risk has reached {black_swan_tier.upper()}.")
    if circuit_breaker_tier in ("tier3", "tier4"):
        problems.append(f"Daily Circuit Breaker is at {circuit_breaker_tier.upper()}.")
    return problems


def generate_board_report(
    *,
    cadence: BoardReportCadence,
    trigger: BoardReportTrigger | None,
    trigger_detail: str | None,
    research: list[ResearchItem],
    decisions: list[TradeDecision],
    agent_ids: tuple[AgentId, ...],
    company_health: CompanyHealth,
    black_swan_tier: BlackSwanRiskTier,
    circuit_breaker_tier: DailyCircuitBreakerTier,
    pending_ceo_decisions: int,
    sim_day: int,
    report_id: str,
    now_iso: str,
) -> BoardReport:
    department_activity = compute_department_activity(research, decisions, agent_ids)
    problems = _problems(company_health, black_swan_tier, circuit_breaker_tier)
    risk_assessment = _risk_assessment(black_swan_tier, circuit_breaker_tier)

    cadence_label = {"daily": "Daily", "quarterly": "Quarterly", "emergency": "Emergency"}[cadence]
    summary = (
        f"{cadence_label} Board Report — Company Health {company_health.tier.replace('_', ' ')} "
        f"({company_health.overall:.0f}/100), Department Consensus {company_health.department_consensus:.0f}%. "
        f"{risk_assessment} {pending_ceo_decisions} decision(s) awaiting the CEO."
    )
    if cadence == "emergency" and trigger_detail:
        summary = f"{summary} Triggered by {trigger_detail}."

    return BoardReport(
        id=report_id,
        cadence=cadence,
        trigger=trigger,
        departmentActivity=department_activity,
        problems=problems,
        recommendations=list(company_health.recommendations),
        riskAssessment=risk_assessment,
        confidenceLevel=company_health.department_consensus,
        requiredCeoDecisions=pending_ceo_decisions,
        summary=summary,
        simDay=sim_day,
        createdAt=now_iso,
    )


def record_board_report(reports: list[BoardReport], report: BoardReport) -> list[BoardReport]:
    updated = [*reports, report]
    if len(updated) > MAX_BOARD_REPORTS:
        del updated[: len(updated) - MAX_BOARD_REPORTS]
    return updated
