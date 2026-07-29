"""InnovationManager — v0.7 Feature 41, Innovation Points.

A second, deliberately narrow ladder alongside Academy's KnowledgeLevel
(app/academy.py, Feature 31). Academy tracks general knowledge mastery
across everything an agent does; this tracks one specific real skill —
the ability to find genuine weaknesses before capital is committed — so
it is driven by exactly one real, new signal this same v0.7 feature
introduces: an agent's own record as a Devil's Advocate
(app/devils_advocate.py's ChallengeReport).

Re-awarding points for events Academy already scores (course completion,
research, mentoring) would be double-counting the same real signal under
two names — the exact duplication this session's convention exists to
avoid — so those are deliberately not wired here. The brief's other
named earning activities (CEO Innovation Challenges, Reasoning Lab
"contribution quality," cross-department collaboration scoring) have no
real, checkable signal anywhere in this codebase and are not fabricated.

Points are awarded per ChallengeReport, weighted by its own real
severity — finding nothing wrong is still a real contribution (the
brief's own "intellectual honesty" philosophy), just a smaller one than
catching an actual major weakness. Five tiers mirror the brief's
Research Contributor → Legendary Innovator ladder, gated by real
cumulative point thresholds, the same "crossing a threshold advances one
tier" pattern app/academy.py already established.
"""
from __future__ import annotations

from app.schemas import AgentId, ChallengeReport, ChallengeSeverity, InnovationState, InnovationTierName

NONE_FOUND_POINTS = 0.5
MINOR_POINTS = 1.0
MAJOR_POINTS = 3.0

_SEVERITY_POINTS: dict[ChallengeSeverity, float] = {
    "none_found": NONE_FOUND_POINTS,
    "minor": MINOR_POINTS,
    "major": MAJOR_POINTS,
}

# Four thresholds give five real tiers (0-4), matching the brief's
# Research Contributor/Research Specialist/Innovation Leader/Chief
# Innovator/Legendary Innovator ladder.
TIER_THRESHOLDS = (3.0, 8.0, 18.0, 35.0)
_TIER_NAMES: tuple[InnovationTierName, ...] = (
    "research_contributor",
    "research_specialist",
    "innovation_leader",
    "chief_innovator",
    "legendary_innovator",
)
TIER_LABELS: dict[InnovationTierName, str] = {
    "research_contributor": "Research Contributor",
    "research_specialist": "Research Specialist",
    "innovation_leader": "Innovation Leader",
    "chief_innovator": "Chief Innovator",
    "legendary_innovator": "Legendary Innovator",
}


def _tier_for_points(points: float) -> int:
    tier = 0
    for threshold in TIER_THRESHOLDS:
        if points >= threshold:
            tier += 1
    return tier


def compute_innovation_state(challenge_reports: list[ChallengeReport]) -> dict[AgentId, InnovationState]:
    """Recomputed fresh from the full challenge_reports history every
    tick — a pure function of already-persisted data, the same
    "recomputed, not incrementally mutated" convention app/academy.py's
    own compute_academy_state() already established, so there is never a
    risk of this drifting from the reports it's derived from."""
    totals: dict[AgentId, float] = {}
    for report in challenge_reports:
        totals[report.assigned_agent] = totals.get(report.assigned_agent, 0.0) + _SEVERITY_POINTS[report.severity]

    state: dict[AgentId, InnovationState] = {}
    for agent_id, points in totals.items():
        tier = _tier_for_points(points)
        state[agent_id] = InnovationState(agentId=agent_id, points=points, tier=tier, tierName=_TIER_NAMES[tier])
    return state
