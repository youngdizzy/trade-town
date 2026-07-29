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
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.education import all_lessons
from app.schemas import (
    AgentEnergy,
    AgentId,
    AgentState,
    CompanyHealth,
    CompanyHealthTier,
    Debate,
    EducationProgress,
    HallOfFameEntry,
    PaperPortfolio,
    ResearchItem,
    RiskWarning,
    SignalCalibrationState,
    WatchlistEntry,
)
from app.signal_calibration import MAX_LEVEL as SIGNAL_MAX_LEVEL
from app.watchlist import EXTRA_SYMBOL_POOL, SEED_SYMBOLS

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

# The window of most-recent debates a fresh Team Chemistry reading is
# computed over — recent behavior, not the company's entire history.
TEAM_CHEMISTRY_WINDOW = 20


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tier(overall: float) -> CompanyHealthTier:
    for threshold, tier in _TIER_THRESHOLDS:
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
) -> CompanyHealth:
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

    # The two (or more, on a tie) weakest real sub-scores, named in
    # plain language — never generic filler. A company already at 100
    # everywhere gets no recommendations at all, honestly.
    weakest = sorted(metrics.items(), key=lambda kv: kv[1])[:2]
    recommendations = [f"{_METRIC_LABELS[name]} is low ({score:.0f}/100) — worth attention." for name, score in weakest if score < 70.0]

    return CompanyHealth(
        overall=round(overall, 1),
        tier=_tier(overall),
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
    )
