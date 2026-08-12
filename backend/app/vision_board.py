"""app/vision_board.py — Design Bible Chapter 74.5, the CEO Vision Board
& Strategic Alignment Engine.

Researched first, and the finding was stark: most of the source brief
already exists as a real system under a different name (Company
Philosophy is `app/constitution.py`, Company Identity is
`app/company_dna.py::classify_identity()`, CEO Long-Term Objectives with
a real signal is `app/goals.py`'s `Goal`). This module's real job is
narrow — a small CEO-authored priority ranking (`VisionBoardState`) plus
a real, disclosed Vision Alignment Engine
(`compute_vision_alignment_score()`) scoped to exactly three real
subject types: `SelfImprovementProposal`, `Goal`, `ConstitutionAmendment`.
See the Design Bible chapter's own Ownership table for the full
duplication audit.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import (
    ConstitutionAmendment,
    DailyCircuitBreakerTier,
    Goal,
    SelfImprovementCategory,
    SelfImprovementProposal,
    VisionAlignmentScore,
    VisionBoardObjective,
    VisionBoardState,
    VisionPriorityCategory,
    VisionSelfCorrectionNote,
)

# The "no hidden weighting" convention app/company_score.py established —
# every SelfImprovementCategory maps to exactly one VisionPriorityCategory,
# published here rather than inferred at score time.
SELF_IMPROVEMENT_TO_PRIORITY_CATEGORY: dict[SelfImprovementCategory, VisionPriorityCategory] = {
    "risk_rule": "risk",
    "dashboard": "operations",
    "research_workflow": "research",
    "position_sizing": "risk",
    "new_executive": "growth",
    "automation": "operations",
    "knowledge_organization": "research",
    "ui": "operations",
}

# The explicit, disclosed neutral default when the CEO hasn't ranked a
# mapped category at all — never an invented "we think you'd care about
# this" guess.
UNRANKED_SCORE = 50.0
UNRANKED_CONFIDENCE = 40.0
RANKED_CONFIDENCE = 100.0

MAX_VISION_BOARD_OBJECTIVES = 20

VISION_PRIORITY_CATEGORIES: frozenset[str] = frozenset(
    {"growth", "risk", "research", "trading", "operations", "governance"}
)
VISION_OBJECTIVE_CATEGORIES: frozenset[str] = frozenset(
    {"trading_style", "expansion", "research_priority", "technology", "lifestyle", "other"}
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_vision_board() -> VisionBoardState:
    return VisionBoardState(mission=None, priorities=[], objectives=[], identityNote=None, updatedAt=_now_iso())


def set_vision_mission(board: VisionBoardState, mission: str | None) -> VisionBoardState:
    return board.model_copy(update={"mission": mission, "updated_at": _now_iso()})


def set_vision_identity_note(board: VisionBoardState, identity_note: str | None) -> VisionBoardState:
    return board.model_copy(update={"identity_note": identity_note, "updated_at": _now_iso()})


def set_vision_priorities(
    board: VisionBoardState, priorities: list[str]
) -> tuple[VisionBoardState, str | None]:
    if len(priorities) != len(set(priorities)):
        return board, "Priority categories must not repeat."
    invalid = [p for p in priorities if p not in VISION_PRIORITY_CATEGORIES]
    if invalid:
        return board, f"Unknown priority category: {invalid[0]}."
    return board.model_copy(update={"priorities": priorities, "updated_at": _now_iso()}), None  # type: ignore[arg-type]


def add_vision_objective(
    board: VisionBoardState, text: str, category: str
) -> tuple[VisionBoardState, str | None]:
    text = text.strip()
    if not text:
        return board, "An objective needs real text."
    if category not in VISION_OBJECTIVE_CATEGORIES:
        return board, f"Unknown objective category: {category}."
    objective = VisionBoardObjective(
        id=f"vision-objective-{len(board.objectives)}-{int(datetime.now(timezone.utc).timestamp() * 1000)}",
        text=text,
        category=category,  # type: ignore[arg-type]
        createdAt=_now_iso(),
    )
    objectives = [*board.objectives, objective]
    if len(objectives) > MAX_VISION_BOARD_OBJECTIVES:
        del objectives[: len(objectives) - MAX_VISION_BOARD_OBJECTIVES]
    return board.model_copy(update={"objectives": objectives, "updated_at": _now_iso()}), None


def remove_vision_objective(board: VisionBoardState, objective_id: str) -> VisionBoardState:
    objectives = [o for o in board.objectives if o.id != objective_id]
    return board.model_copy(update={"objectives": objectives, "updated_at": _now_iso()})


def _score_for_category(
    category: VisionPriorityCategory, priorities: list[VisionPriorityCategory]
) -> tuple[float, float, list[str], list[str]]:
    if category not in priorities:
        return (
            UNRANKED_SCORE,
            UNRANKED_CONFIDENCE,
            [f'"{category}" is not among the CEO\'s ranked priorities — neutral default applied.'],
            [],
        )
    rank = priorities.index(category) + 1
    total = len(priorities)
    score = round(100.0 * (total - rank + 1) / total, 1)
    reasons = [f'"{category}" is ranked #{rank} of {total} CEO priorities.']
    conflicts: list[str] = [str(category)] if rank == total and total > 1 else []
    return score, RANKED_CONFIDENCE, reasons, conflicts


def compute_self_improvement_proposal_alignment(
    proposal: SelfImprovementProposal, board: VisionBoardState
) -> VisionAlignmentScore:
    category = SELF_IMPROVEMENT_TO_PRIORITY_CATEGORY[proposal.category]
    score, confidence, reasons, conflicts = _score_for_category(category, board.priorities)
    return VisionAlignmentScore(
        subjectType="self_improvement_proposal",
        subjectId=proposal.id,
        score=score,
        supportingReasons=reasons,
        conflictingGoals=conflicts,
        confidence=confidence,
        computedAt=_now_iso(),
    )


def compute_goal_alignment(goal: Goal, board: VisionBoardState) -> VisionAlignmentScore:
    score, confidence, reasons, conflicts = _score_for_category(goal.category, board.priorities)
    return VisionAlignmentScore(
        subjectType="goal",
        subjectId=goal.id,
        score=score,
        supportingReasons=reasons,
        conflictingGoals=conflicts,
        confidence=confidence,
        computedAt=_now_iso(),
    )


def compute_constitution_amendment_alignment(
    amendment: ConstitutionAmendment, board: VisionBoardState
) -> VisionAlignmentScore:
    score, confidence, reasons, conflicts = _score_for_category("governance", board.priorities)
    return VisionAlignmentScore(
        subjectType="constitution_amendment",
        subjectId=amendment.id,
        score=score,
        supportingReasons=reasons,
        conflictingGoals=conflicts,
        confidence=confidence,
        computedAt=_now_iso(),
    )


def compute_self_correction_note(
    board: VisionBoardState, circuit_breaker_tier: DailyCircuitBreakerTier
) -> VisionSelfCorrectionNote:
    """The one real, narrow Self-Correction check: the CEO's own rank-1
    priority is "risk" and the real Daily Circuit Breaker tier is tier2
    or worse. No other drift scenario has an equally clean single real
    signal — see the chapter's own Deferred Features."""
    top_priority = board.priorities[0] if board.priorities else None
    triggered = top_priority == "risk" and circuit_breaker_tier in ("tier2", "tier3", "tier4")
    message = (
        f'Your top-ranked priority is "risk," but the company\'s real Daily Circuit Breaker '
        f'is currently at {circuit_breaker_tier} — your own stated priority and the company\'s '
        "real current risk state have diverged."
        if triggered
        else None
    )
    return VisionSelfCorrectionNote(
        triggered=triggered,
        message=message,
        circuitBreakerTier=circuit_breaker_tier,
        computedAt=_now_iso(),
    )
