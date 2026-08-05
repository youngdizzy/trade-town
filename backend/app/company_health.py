"""CompanyHealth — v0.7 Feature 23, the Company Health & Stability System.

Ten sub-scores, each a small, named, documented formula (same
"transparency over automation" convention `app/company_score.py`
already established) rather than a single opaque number. Several
sub-scores necessarily reuse the exact same underlying real signal an
existing v0.5 CompanyScore metric already reads (agent mood, research
completion, portfolio P&L) — that's an intentional, documented overlap
(the two systems answer different questions: "is the company performing
well" vs. "is the company healthy to keep operating"), never two
independently-invented readings of the same thing.

Four of the ten map onto real state that has no prior aggregate reading
anywhere else in this codebase: Resource Usage (AgentEnergy's real
current/cap), Reputation (real HallOfFameEntry count), Technology Level
(the real SignalCalibrationState.unlockedLevel progression), and Office
Expansion (the real count of extra symbols added to the watchlist beyond
the eight SEED_SYMBOLS via the "watch_symbol" Agent Energy action — see
app/watchlist.py's EXTRA_SYMBOL_POOL). None of these are fabricated
company-management mechanics; every one is a real, already-tracked
number this module is the first to actually read.

v0.7 Feature 50 (Part 2/3) — the Company Health redesign adds a second,
Executive tier of ten more real, checkable dimensions
(`_EXECUTIVE_METRIC_LABELS` below), computed from data the Executive
Intelligence Network itself now produces (Decision Grade, the Executive
Meeting Log, Weekly Self-Evaluation) plus real existing systems this
module never previously read (Wisdom, Innovation Points, the Academy,
the Founder Council). This is additive, not a replacement: the original
eleven Operational dimensions above keep their exact original meaning
and formula — `overall`/`tier` are unchanged, so every existing
consumer (Company Priorities, the Founders' retirement trigger, the
COMPANY tab) keeps working identically. `executiveOverall`/
`executiveTier` are the new tier's own headline; `combinedOverall`/
`combinedTier` (an equal blend of the two) is the true redesigned
headline number.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.education import all_lessons
from app.foundational_mentors import STUDENT_AGENT_IDS
from app.innovation import TIER_THRESHOLDS as INNOVATION_TIER_THRESHOLDS
from app.schemas import (
    AgentEnergy,
    AgentId,
    AgentState,
    CompanyHealth,
    CompanyHealthTier,
    Debate,
    DepartmentSelfEvaluation,
    EducationProgress,
    ExecutiveMeetingLogEntry,
    FounderCouncilSession,
    FoundationalMentorState,
    GatekeeperRejection,
    HallOfFameEntry,
    InnovationState,
    PaperPortfolio,
    PaperTrade,
    ResearchItem,
    RiskWarning,
    SignalCalibrationState,
    TradeDecision,
    WatchlistEntry,
    WisdomState,
)
from app.signal_calibration import MAX_LEVEL as SIGNAL_MAX_LEVEL
from app.watchlist import EXTRA_SYMBOL_POOL, SEED_SYMBOLS

# v0.7 Feature 50 (Part 2/3) — how many recent decisions/meeting-log
# entries the new Executive-tier metrics look back over. Deliberately
# the same order of magnitude as MAX_DECISIONS' own recent-history
# reasoning elsewhere in this codebase — recent behavior, not the
# company's entire history.
EXECUTIVE_METRIC_WINDOW = 30
LEGENDARY_INNOVATOR_THRESHOLD = INNOVATION_TIER_THRESHOLDS[-1]

RESTFUL_LOCATIONS = {"lobby", "break-room"}

_SEVERITY_PENALTY = {"critical": 15.0, "warning": 6.0, "info": 2.0}

_TIER_THRESHOLDS: list[tuple[float, CompanyHealthTier]] = [
    (85.0, "excellent"),
    (70.0, "good"),
    (50.0, "stable"),
    (30.0, "needs_attention"),
]

_METRIC_LABELS: dict[str, str] = {
    "operational_stability": "Operational Stability",
    "department_efficiency": "Department Efficiency",
    "employee_morale": "Employee Morale",
    "research_progress": "Research Progress",
    "capital_health": "Capital Health",
    "resource_usage": "Resource Usage",
    "reputation": "Reputation",
    "technology_level": "Technology Level",
    "office_expansion": "Office Expansion",
    "education_progress": "Education Progress",
    "team_chemistry": "Team Chemistry",
}

# v0.7 Feature 50 (Part 2/3) — the Company Health redesign. Ten new
# Executive-tier dimensions, real and checkable, computed from data the
# Executive Intelligence Network itself now produces (Decision Grade,
# the Executive Meeting Log, Weekly Self-Evaluation) plus real existing
# systems this file never previously read (Wisdom, Innovation Points,
# the Academy, the Founder Council). Additive alongside the eleven
# Operational dimensions above — never replacing them (see this
# module's own docstring for why).
_EXECUTIVE_METRIC_LABELS: dict[str, str] = {
    "decision_quality": "Decision Quality",
    "executive_alignment": "Executive Alignment",
    "risk_governance": "Risk Governance",
    "simulation_coverage": "Simulation Coverage",
    "department_consensus": "Department Consensus",
    "self_evaluation_health": "Self-Evaluation Health",
    "institutional_memory": "Institutional Memory",
    "innovation_velocity": "Innovation Velocity",
    "talent_development": "Talent Development",
    "founder_oversight": "Founder Oversight",
}

# The window of most-recent debates a fresh Team Chemistry reading is
# computed over — recent behavior, not the company's entire history.
TEAM_CHEMISTRY_WINDOW = 20


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tier(overall: float, thresholds: list[tuple[float, CompanyHealthTier]] = _TIER_THRESHOLDS) -> CompanyHealthTier:
    for threshold, tier in thresholds:
        if overall >= threshold:
            return tier
    return "critical"


def _operational_stability(risk_warnings: list[RiskWarning]) -> float:
    penalty = sum(_SEVERITY_PENALTY.get(w.severity, 2.0) for w in risk_warnings)
    return max(0.0, 100.0 - penalty)


def _department_efficiency(agents: dict[AgentId, AgentState]) -> float:
    if not agents:
        return 50.0
    working = sum(1 for a in agents.values() if a.location not in RESTFUL_LOCATIONS)
    return working / len(agents) * 100.0


def _employee_morale(agents: dict[AgentId, AgentState]) -> float:
    if not agents:
        return 50.0
    return sum(a.mood for a in agents.values()) / len(agents)


def _research_progress(research: list[ResearchItem]) -> float:
    if not research:
        return 50.0
    completed = sum(1 for r in research if r.status == "completed")
    return completed / len(research) * 100.0


def _capital_health(portfolio: PaperPortfolio) -> float:
    return max(0.0, min(100.0, 50.0 + portfolio.total_pnl_pct * 1.5))


def _resource_usage(agent_energy: AgentEnergy) -> float:
    if agent_energy.cap <= 0:
        return 50.0
    return max(0.0, min(100.0, agent_energy.current / agent_energy.cap * 100.0))


def _reputation(hall_of_fame: list[HallOfFameEntry]) -> float:
    return min(100.0, len(hall_of_fame) * 4.0)


def _technology_level(signal_calibration: SignalCalibrationState) -> float:
    if SIGNAL_MAX_LEVEL <= 1:
        return 100.0
    return (signal_calibration.unlocked_level - 1) / (SIGNAL_MAX_LEVEL - 1) * 100.0


def _office_expansion(watchlist: list[WatchlistEntry]) -> float:
    if not EXTRA_SYMBOL_POOL:
        return 100.0
    added = max(0, len(watchlist) - len(SEED_SYMBOLS))
    return min(100.0, added / len(EXTRA_SYMBOL_POOL) * 100.0)


def _education_progress(education: EducationProgress) -> float:
    total = len(all_lessons())
    if total == 0:
        return 50.0
    return len(education.completed_lesson_ids) / total * 100.0


def _team_chemistry(debates: list[Debate]) -> float:
    """v0.7 Feature 43 — a real, checkable reading of whether the team
    tends to back each other's calls during the AI Debate or mostly push
    back, over the most recent TEAM_CHEMISTRY_WINDOW debates. Distinct
    from `employee_morale` (individual mood) and `department_efficiency`
    (time at desk) — this is specifically about how the team behaves
    *together*, never a fabricated pairwise relationship graph (there is
    no per-agent-pair data anywhere in this codebase to build one from).
    50.0 (neutral) until the company has held at least one real debate."""
    recent = debates[-TEAM_CHEMISTRY_WINDOW:]
    turns = [t for d in recent for t in d.turns if t.stance != "opening"]
    if not turns:
        return 50.0
    supportive = sum(1 for t in turns if t.stance == "support")
    return supportive / len(turns) * 100.0


def _decision_quality(decisions: list[TradeDecision]) -> float:
    graded = [d for d in decisions if d.decision_grade_score is not None][-EXECUTIVE_METRIC_WINDOW:]
    if not graded:
        return 50.0
    return sum(d.decision_grade_score for d in graded if d.decision_grade_score is not None) / len(graded)


def _executive_alignment(meeting_log: list[ExecutiveMeetingLogEntry]) -> float:
    recent = meeting_log[-EXECUTIVE_METRIC_WINDOW:]
    if not recent:
        return 50.0
    agreed = sum(1 for e in recent if e.network_agreed)
    return agreed / len(recent) * 100.0


def _risk_governance(trade_history: list[PaperTrade], gatekeeper_rejections: list[GatekeeperRejection]) -> float:
    total = len(trade_history) + len(gatekeeper_rejections)
    if total == 0:
        return 50.0
    return len(trade_history) / total * 100.0


def _simulation_coverage(meeting_log: list[ExecutiveMeetingLogEntry]) -> float:
    recent = meeting_log[-EXECUTIVE_METRIC_WINDOW:]
    if not recent:
        return 0.0
    covered = sum(1 for e in recent for op in e.opinions if op.role == "simulation" and op.stance != "request_more_research")
    return covered / len(recent) * 100.0


def _department_consensus(meeting_log: list[ExecutiveMeetingLogEntry]) -> float:
    recent = meeting_log[-EXECUTIVE_METRIC_WINDOW:]
    opinions = [op for e in recent for op in e.opinions]
    if not opinions:
        return 50.0
    agree = sum(1 for op in opinions if op.stance == "agree")
    return agree / len(opinions) * 100.0


def _self_evaluation_health(self_evaluations: list[DepartmentSelfEvaluation]) -> float:
    if not self_evaluations:
        return 50.0
    latest_by_role: dict[str, float] = {}
    for entry in self_evaluations:
        latest_by_role[entry.role] = entry.score
    return sum(latest_by_role.values()) / len(latest_by_role)


def _institutional_memory(wisdom_state: WisdomState) -> float:
    return wisdom_state.score


def _innovation_velocity(innovation_state: dict[AgentId, InnovationState]) -> float:
    if not innovation_state:
        return 0.0
    avg_points = sum(s.points for s in innovation_state.values()) / len(innovation_state)
    return min(100.0, avg_points / LEGENDARY_INNOVATOR_THRESHOLD * 100.0)


def _talent_development(foundational_mentor_state: FoundationalMentorState) -> float:
    active_mentors = [m for m in foundational_mentor_state.mentors if m.status == "active"]
    if not active_mentors:
        return 0.0
    total_slots = len(STUDENT_AGENT_IDS) * len(active_mentors)
    graduated = 0
    for agent_id in STUDENT_AGENT_IDS:
        by_mentor = foundational_mentor_state.progress.get(agent_id, {})
        for mentor in active_mentors:
            progress = by_mentor.get(mentor.id)
            if progress is not None and progress.graduation_status == "graduated":
                graduated += 1
    return graduated / total_slots * 100.0 if total_slots else 0.0


def _founder_oversight(council_sessions: list[FounderCouncilSession]) -> float:
    return min(100.0, len(council_sessions) * 20.0)


def compute_company_health(
    *,
    agents: dict[AgentId, AgentState],
    research: list[ResearchItem],
    portfolio: PaperPortfolio,
    risk_warnings: list[RiskWarning],
    agent_energy: AgentEnergy,
    hall_of_fame: list[HallOfFameEntry],
    signal_calibration: SignalCalibrationState,
    watchlist: list[WatchlistEntry],
    education: EducationProgress,
    debates: list[Debate],
    decisions: list[TradeDecision],
    meeting_log: list[ExecutiveMeetingLogEntry],
    self_evaluations: list[DepartmentSelfEvaluation],
    wisdom_state: WisdomState,
    innovation_state: dict[AgentId, InnovationState],
    foundational_mentor_state: FoundationalMentorState,
    founder_council_sessions: list[FounderCouncilSession],
    gatekeeper_rejections: list[GatekeeperRejection],
    # v0.7 Design Bible Chapter 63 — CEO-configurable tier thresholds
    # (RiskLimits.companyHealth*Threshold), defaulting to the exact
    # module constants above so existing behavior is unchanged until the
    # CEO adjusts them. Always passed together (see app/state.py's
    # update_risk_limits for the descending-order validation).
    excellent_threshold: float = 85.0,
    good_threshold: float = 70.0,
    stable_threshold: float = 50.0,
    needs_attention_threshold: float = 30.0,
) -> CompanyHealth:
    tier_thresholds: list[tuple[float, CompanyHealthTier]] = [
        (excellent_threshold, "excellent"),
        (good_threshold, "good"),
        (stable_threshold, "stable"),
        (needs_attention_threshold, "needs_attention"),
    ]
    metrics = {
        "operational_stability": _operational_stability(risk_warnings),
        "department_efficiency": _department_efficiency(agents),
        "employee_morale": _employee_morale(agents),
        "research_progress": _research_progress(research),
        "capital_health": _capital_health(portfolio),
        "resource_usage": _resource_usage(agent_energy),
        "reputation": _reputation(hall_of_fame),
        "technology_level": _technology_level(signal_calibration),
        "office_expansion": _office_expansion(watchlist),
        "education_progress": _education_progress(education),
        "team_chemistry": _team_chemistry(debates),
    }
    overall = sum(metrics.values()) / len(metrics)

    executive_metrics = {
        "decision_quality": _decision_quality(decisions),
        "executive_alignment": _executive_alignment(meeting_log),
        "risk_governance": _risk_governance(portfolio.trade_history, gatekeeper_rejections),
        "simulation_coverage": _simulation_coverage(meeting_log),
        "department_consensus": _department_consensus(meeting_log),
        "self_evaluation_health": _self_evaluation_health(self_evaluations),
        "institutional_memory": _institutional_memory(wisdom_state),
        "innovation_velocity": _innovation_velocity(innovation_state),
        "talent_development": _talent_development(foundational_mentor_state),
        "founder_oversight": _founder_oversight(founder_council_sessions),
    }
    executive_overall = sum(executive_metrics.values()) / len(executive_metrics)
    combined_overall = (overall + executive_overall) / 2.0

    # The two (or more, on a tie) weakest real sub-scores from EACH tier,
    # named in plain language — never generic filler. A company already
    # at 100 everywhere gets no recommendations at all, honestly.
    weakest_operational = sorted(metrics.items(), key=lambda kv: kv[1])[:2]
    weakest_executive = sorted(executive_metrics.items(), key=lambda kv: kv[1])[:2]
    recommendations = [f"{_METRIC_LABELS[name]} is low ({score:.0f}/100) — worth attention." for name, score in weakest_operational if score < 70.0]
    recommendations += [f"{_EXECUTIVE_METRIC_LABELS[name]} is low ({score:.0f}/100) — worth attention." for name, score in weakest_executive if score < 70.0]

    return CompanyHealth(
        overall=round(overall, 1),
        tier=_tier(overall, tier_thresholds),
        operationalStability=round(metrics["operational_stability"], 1),
        departmentEfficiency=round(metrics["department_efficiency"], 1),
        employeeMorale=round(metrics["employee_morale"], 1),
        researchProgress=round(metrics["research_progress"], 1),
        capitalHealth=round(metrics["capital_health"], 1),
        resourceUsage=round(metrics["resource_usage"], 1),
        reputation=round(metrics["reputation"], 1),
        technologyLevel=round(metrics["technology_level"], 1),
        officeExpansion=round(metrics["office_expansion"], 1),
        educationProgress=round(metrics["education_progress"], 1),
        teamChemistry=round(metrics["team_chemistry"], 1),
        recommendations=recommendations,
        updatedAt=_now_iso(),
        decisionQuality=round(executive_metrics["decision_quality"], 1),
        executiveAlignment=round(executive_metrics["executive_alignment"], 1),
        riskGovernance=round(executive_metrics["risk_governance"], 1),
        simulationCoverage=round(executive_metrics["simulation_coverage"], 1),
        departmentConsensus=round(executive_metrics["department_consensus"], 1),
        selfEvaluationHealth=round(executive_metrics["self_evaluation_health"], 1),
        institutionalMemory=round(executive_metrics["institutional_memory"], 1),
        innovationVelocity=round(executive_metrics["innovation_velocity"], 1),
        talentDevelopment=round(executive_metrics["talent_development"], 1),
        founderOversight=round(executive_metrics["founder_oversight"], 1),
        executiveOverall=round(executive_overall, 1),
        executiveTier=_tier(executive_overall, tier_thresholds),
        combinedOverall=round(combined_overall, 1),
        combinedTier=_tier(combined_overall, tier_thresholds),
    )
