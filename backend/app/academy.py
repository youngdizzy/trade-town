"""AcademyManager — per-agent Knowledge Points and Tiers (v0.7 Feature 25).

Every agent has exactly one real "Knowledge Branch" (occupation-linked —
Echo's is Technical Analysis, Sentinel's is Risk Management) and a points
total that only ever grows from real completed work: a finished
ResearchItem (research.py), a finished AcademyProject
(academy_research.py), or attending a meeting (scribe.py's
MeetingMinutes.participants). Points cross three fixed thresholds
("tiers"), mirroring signal_calibration.py's single-number progression
pattern (a persisted number that only goes up) — but per-agent rather
than a single global counter. A tier-up appends one real, honestly-
grounded memory/library entry naming the agent's own real point total;
there is no fabricated per-tier dialogue or animation (an explicit scope
cut — see docs/Architecture.md).

Mentorship (the brief's "senior employees mentor junior employees") has
no real seniority/relationship data anywhere in this codebase. Rather
than inventing a fabricated status label, "seniority" here is the one
real number that legitimately reflects it: an agent's own earned
knowledge points. When the gap between the most- and least-experienced
agent crosses MENTORSHIP_GAP_THRESHOLD, a real mentorship session
transfers a small real point bonus to the lower agent (the mentor loses
nothing — mentoring doesn't cost them), logged with both agents' own
real point totals. A full mentor/mentee relationship graph and visible
in-world mentoring animations are an explicit scope cut, not built here.

v0.7 Feature 31 — "Knowledge Levels." The brief asks for a real
Novice-through-Mentor progression per topic; this codebase already has
exactly one real, per-agent, monotonically-growing knowledge number
(the same points this module has tracked since Feature 25), so rather
than inventing a second parallel progression system, `TIER_THRESHOLDS`
widened from 3 thresholds (4 tiers) to 6 (7 tiers) and each tier now
also carries a real `KnowledgeLevel` name — the same points, a richer
label. `is_mentor_level()` is the real, checkable gate the brief's own
"Teaching System" needs ("agents who master a subject may become
instructors"): `maybe_run_mentorship()`'s existing mechanism already
finds the single most experienced agent for a real pairing; when that
agent has actually reached the top "mentor" level, `scribe.py` phrases
the resulting memory entry as real teaching rather than generic
mentorship — no separate teaching subsystem, since the same points-gap
mechanism already is the real trigger for "a more experienced agent
helps a less experienced one."
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import AcademyState, AgentId, AgentKnowledgeState, KnowledgeLevel

KNOWLEDGE_BRANCH: dict[AgentId, str] = {
    "scout": "Market Structure",
    "atlas": "Portfolio Theory",
    "echo": "Technical Analysis",
    "nova": "Economics",
    "scribe": "Communication",
    "coach": "Psychology",
    "sentinel": "Risk Management",
    "pulse": "Statistics",
    "guardian": "Risk Management",
    "cio": "Leadership",
    "sage": "Critical Thinking",
}

RESEARCH_COMPLETION_POINTS = 1.0
ACADEMY_PROJECT_POINTS = 2.0
MEETING_ATTENDANCE_POINTS = 0.5
MENTORSHIP_BONUS_POINTS = 2.0

# Crossing each threshold advances one tier/level — a plain cumulative
# gate, unlike Signal Calibration's streak gate, since there's no
# "attempt" to grind here; every point already came from real completed
# work, so cumulative is honest on its own. Six thresholds give seven
# real levels (tier 0-6), matching v0.7 Feature 31's Novice-through-
# Mentor scale.
TIER_THRESHOLDS = (3.0, 8.0, 15.0, 25.0, 40.0, 60.0)
_KNOWLEDGE_LEVELS: tuple[KnowledgeLevel, ...] = ("novice", "beginner", "intermediate", "advanced", "expert", "master", "mentor")
MENTORSHIP_GAP_THRESHOLD = 12.0

# Company-wide Academy level thresholds (v0.7 brief's five named tiers).
# Gated on a blend of real total knowledge points and real completed
# projects — deliberately NOT five new physical rooms/art (see
# docs/Architecture.md's scope-cut note); this is a progression number
# and label, the same honesty boundary signal_calibration.py's level
# already applies to unlocking richer content without new art per level.
_ACADEMY_LEVEL_THRESHOLDS: tuple[tuple[float, str], ...] = (
    (0.0, "Training Room"),
    (150.0, "Research Library"),
    (350.0, "Innovation Lab"),
    (600.0, "Simulation Center"),
    (1000.0, "Executive Institute"),
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tier_for_points(points: float) -> int:
    tier = 0
    for threshold in TIER_THRESHOLDS:
        if points >= threshold:
            tier += 1
    return tier


def _level_for_tier(tier: int) -> KnowledgeLevel:
    return _KNOWLEDGE_LEVELS[tier]


def is_mentor_level(state: AgentKnowledgeState) -> bool:
    """The real, checkable gate for the brief's "Teaching System" —
    true only once an agent's own real points have actually crossed
    every threshold. See module docstring."""
    return state.level == "mentor"


def default_agent_knowledge() -> dict[AgentId, AgentKnowledgeState]:
    return {agent_id: AgentKnowledgeState(agentId=agent_id, branch=branch, points=0.0, tier=0, level="novice") for agent_id, branch in KNOWLEDGE_BRANCH.items()}


def award_points(knowledge: dict[AgentId, AgentKnowledgeState], agent_id: AgentId, amount: float) -> tuple[dict[AgentId, AgentKnowledgeState], AgentKnowledgeState | None]:
    """Returns (updated_knowledge, tier_up_or_None) — tier_up is only
    non-None the instant a threshold is actually crossed, so the caller
    logs exactly one real memory entry per real tier-up."""
    state = knowledge.get(agent_id)
    if state is None:
        return knowledge, None
    new_points = round(state.points + amount, 1)
    new_tier = _tier_for_points(new_points)
    updated = state.model_copy(update={"points": new_points, "tier": new_tier, "level": _level_for_tier(new_tier)})
    new_knowledge = {**knowledge, agent_id: updated}
    tier_up = updated if new_tier > state.tier else None
    return new_knowledge, tier_up


def maybe_run_mentorship(knowledge: dict[AgentId, AgentKnowledgeState]) -> tuple[dict[AgentId, AgentKnowledgeState], tuple[AgentId, AgentId] | None]:
    """A modest, honestly-grounded substitute for the brief's senior/
    junior mentorship system — see module docstring. Returns (updated,
    (mentor_id, mentee_id)) the moment the real points gap crosses
    MENTORSHIP_GAP_THRESHOLD; (knowledge, None) if nothing qualifies."""
    if len(knowledge) < 2:
        return knowledge, None
    ranked = sorted(knowledge.values(), key=lambda s: s.points, reverse=True)
    mentor, mentee = ranked[0], ranked[-1]
    if mentor.points - mentee.points < MENTORSHIP_GAP_THRESHOLD:
        return knowledge, None
    updated_knowledge, _tier_up = award_points(knowledge, mentee.agent_id, MENTORSHIP_BONUS_POINTS)
    return updated_knowledge, (mentor.agent_id, mentee.agent_id)


def compute_academy_state(knowledge: dict[AgentId, AgentKnowledgeState], completed_project_count: int) -> AcademyState:
    total_points = sum(s.points for s in knowledge.values())
    combined = total_points + completed_project_count * 5.0
    level = 1
    label = _ACADEMY_LEVEL_THRESHOLDS[0][1]
    for i, (threshold, lbl) in enumerate(_ACADEMY_LEVEL_THRESHOLDS):
        if combined >= threshold:
            level = i + 1
            label = lbl
    return AcademyState(
        level=level,
        levelLabel=label,
        totalPoints=round(total_points, 1),
        completedProjectCount=completed_project_count,
        updatedAt=_now_iso(),
    )
