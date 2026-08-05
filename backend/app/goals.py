"""GoalManager — v0.7 Design Bible Chapter 64, Executive Strategic
Planning & Goal Management Engine.

Per that chapter's own Implementation Notes ("a future implementation
should likely start with the smallest real, independently-useful
slice"), this is deliberately small: the CEO authors a goal naming one
real, already-computed metric and a target value; this module recomputes
real progress against it every tick, the same "cheap, always current"
convention `app/company_health.py`/`app/company_dna.py` already use for
their own always-fresh reads.

Milestone Tracking (v0.7 Design Bible Chapter 64, second pass) extends
this same `Goal` object with real, fixed intermediate checkpoints
(MILESTONE_THRESHOLDS below) rather than introducing a second tracking
concept.

The Executive Priority Engine (v0.7 Design Bible Chapter 64, third pass)
ranks active goals by a real, named formula — `compute_goal_priority()`
below — combining two real signals every `Goal` already carries:
distance-to-target (`100 - progress_pct`) and, when a real deadline
exists, the real pace required to hit it (`remaining_pct / days
remaining`). This is deliberately NOT a reuse of Chapter 59's
trade-proposal Priority Score (`app/capital_priority.py`'s
`rank_trade_proposals()`) — that engine reads `WarRoomSession.decisionScore`,
a composite built entirely from trade-specific signals (Expected Value,
Evidence, Risk, Portfolio Compatibility, ...) that don't exist for a
goal. A goal's own real priority is a structurally different
computation over structurally different inputs, per this chapter's own
Decision Logic section.

Resource Allocation remains explicitly out of scope: it depends on this
Priority Engine existing first to have anything real to allocate
against, and no real capital-to-goal linkage has been designed yet. A
goal is always "reach at least targetValue" — every real metric below
is a "higher is better" number, so a reduce-below-X goal type would need
its own honest design, not invented here.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import (
    AcademyState,
    CompanyHealth,
    CompanyScore,
    Goal,
    GoalCategory,
    GoalMetric,
    GoalPriority,
    Milestone,
    PaperPortfolio,
)

# CEO-authored, not automatically generated — capped the same way every
# other real list in this codebase is (oldest evicted first, regardless
# of status), so a CEO who keeps creating goals can't grow this list
# without bound.
MAX_GOALS = 20

GOAL_METRIC_LABELS: dict[GoalMetric, str] = {
    "company_health_combined": "Company Health (Combined)",
    "company_score_overall": "Company Score",
    "portfolio_return_pct": "Portfolio Return %",
    "academy_level": "Academy Level",
}

# Every one of these already has a real, sensible maximum the CEO's own
# target_value is checked against at creation time — never an arbitrary
# guess. Company Health/Company Score are 0-100 composites; Academy
# level is a real 1-5 progression; portfolio return has no real ceiling
# (a company can always keep growing), so None means "no upper bound."
_METRIC_MAX_TARGET: dict[GoalMetric, float | None] = {
    "company_health_combined": 100.0,
    "company_score_overall": 100.0,
    "portfolio_return_pct": None,
    "academy_level": 5.0,
}

# v0.7 Design Bible Chapter 64 — Milestone Tracking. Three fixed,
# real checkpoints on the way to a goal's own real 100% (goal
# completion itself already tracks the 100% point via `status`, so no
# milestone is generated for it — that would just be a second read of
# the same real fact).
MILESTONE_THRESHOLDS: tuple[float, ...] = (25.0, 50.0, 75.0)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def validate_target_value(metric: GoalMetric, target_value: float) -> str | None:
    """Returns an error message, or None if target_value is a real,
    achievable target for this metric. Every goal is "reach at least
    target_value" (see module docstring), so target_value must exceed
    zero and stay within the metric's own real ceiling."""
    if target_value <= 0:
        return f"{GOAL_METRIC_LABELS[metric]} target must be a positive number."
    ceiling = _METRIC_MAX_TARGET[metric]
    if ceiling is not None and target_value > ceiling:
        return f"{GOAL_METRIC_LABELS[metric]} target cannot exceed {ceiling:.0f} — that's the real maximum this metric can reach."
    return None


def resolve_metric_value(
    metric: GoalMetric,
    *,
    company_health: CompanyHealth,
    company_score: CompanyScore,
    portfolio: PaperPortfolio,
    academy_state: AcademyState,
) -> float:
    """The one real number each GoalMetric tracks — see this module's own
    docstring for why each of these four, and only these four, is
    offered."""
    if metric == "company_health_combined":
        return company_health.combined_overall
    if metric == "company_score_overall":
        return company_score.overall
    if metric == "portfolio_return_pct":
        return portfolio.total_pnl_pct
    return float(academy_state.level)


def _build_milestones(goal_id: str) -> list[Milestone]:
    return [Milestone(id=f"{goal_id}-milestone-{int(threshold)}", thresholdPct=threshold) for threshold in MILESTONE_THRESHOLDS]


def create_goal(
    *,
    goal_id: str,
    title: str,
    category: GoalCategory,
    target_metric: GoalMetric,
    target_value: float,
    deadline_sim_day: int | None,
    created_sim_day: int,
    current_value: float,
) -> Goal:
    now = _now_iso()
    initial_progress = _progress_pct(current_value, target_value)
    return Goal(
        id=goal_id,
        title=title,
        category=category,
        targetMetric=target_metric,
        targetValue=target_value,
        currentValue=round(current_value, 2),
        progressPct=initial_progress,
        createdSimDay=created_sim_day,
        deadlineSimDay=deadline_sim_day,
        status="active",
        createdAt=now,
        updatedAt=now,
        # A goal can honestly start past a milestone (e.g. the CEO sets
        # a target the company already exceeds part of the way to) — the
        # real starting progress is checked here too, not just on every
        # later tick.
        milestones=_mark_reached_milestones(_build_milestones(goal_id), initial_progress, now),
    )


def _mark_reached_milestones(milestones: list[Milestone], progress_pct: float, now: str) -> list[Milestone]:
    return [m.model_copy(update={"reached": True, "reached_at": now}) if not m.reached and progress_pct >= m.threshold_pct else m for m in milestones]


def _progress_pct(current_value: float, target_value: float) -> float:
    if target_value <= 0:
        return 100.0
    return round(max(0.0, min(100.0, current_value / target_value * 100.0)), 1)


def tick_goal(goal: Goal, *, current_value: float, sim_day: int) -> Goal:
    """Recomputes one goal's real progress, including which real
    milestones it has now crossed. A goal that's already completed or
    cancelled never changes again — the same "a crossed milestone stays
    crossed" convention `app/hall_of_fame.py` and `app/founders.py`
    already establish for their own permanent records (and, at the
    per-milestone level, that this goal's own `milestones` list already
    follows)."""
    if goal.status != "active":
        return goal
    progress_pct = _progress_pct(current_value, goal.target_value)
    now = _now_iso()
    milestones = _mark_reached_milestones(goal.milestones, progress_pct, now)
    if current_value >= goal.target_value:
        return goal.model_copy(
            update={
                "current_value": round(current_value, 2),
                "progress_pct": progress_pct,
                "status": "completed",
                "completed_at": now,
                "updated_at": now,
                "milestones": milestones,
            }
        )
    if goal.deadline_sim_day is not None and sim_day > goal.deadline_sim_day:
        return goal.model_copy(
            update={
                "current_value": round(current_value, 2),
                "progress_pct": progress_pct,
                "status": "expired",
                "updated_at": now,
                "milestones": milestones,
            }
        )
    return goal.model_copy(update={"current_value": round(current_value, 2), "progress_pct": progress_pct, "updated_at": now, "milestones": milestones})


def tick_goals(
    goals: list[Goal],
    *,
    company_health: CompanyHealth,
    company_score: CompanyScore,
    portfolio: PaperPortfolio,
    academy_state: AcademyState,
    sim_day: int,
) -> list[Goal]:
    return [
        tick_goal(
            g,
            current_value=resolve_metric_value(g.target_metric, company_health=company_health, company_score=company_score, portfolio=portfolio, academy_state=academy_state),
            sim_day=sim_day,
        )
        for g in goals
    ]


def record_goal(goals: list[Goal], goal: Goal) -> list[Goal]:
    updated = [*goals, goal]
    if len(updated) > MAX_GOALS:
        del updated[: len(updated) - MAX_GOALS]
    return updated


def cancel_goal(goals: list[Goal], goal_id: str) -> list[Goal]:
    now = _now_iso()
    return [g.model_copy(update={"status": "cancelled", "updated_at": now}) if g.id == goal_id and g.status == "active" else g for g in goals]


# v0.7 Design Bible Chapter 64 (third pass) — the Executive Priority
# Engine's own real, stated urgency ceiling: a goal needing 5 or more
# percentage points of real progress per real remaining day to hit its
# deadline reads as maximally urgent (a real score of 100). Below that
# pace, urgency scales down linearly and transparently — never a hidden
# weighting, the same "no black-box composite" convention every other
# scoring engine in this codebase already follows.
MAX_URGENCY_PACE_PCT_PER_DAY = 5.0


def compute_goal_priority(goal: Goal, *, sim_day: int) -> GoalPriority | None:
    """The real Executive Priority Score for one ACTIVE goal — None for
    any other status, since a completed/expired/cancelled goal has
    nothing left to prioritize. Two real cases, both built entirely from
    fields the goal already carries:

    - No real deadline: scored purely by how much real distance is left
      (`100 - progress_pct`) — an open-ended goal still deserves
      attention proportional to how far it has to go, just with no time
      pressure driving it.
    - A real deadline: scored by the real pace required to hit it —
      remaining_pct divided by real days left — clamped against
      MAX_URGENCY_PACE_PCT_PER_DAY and scaled into the same 0-100 range,
      so a goal running out of runway always reads as urgent regardless
      of how much distance remains.
    """
    if goal.status != "active":
        return None
    remaining_pct = round(max(0.0, 100.0 - goal.progress_pct), 1)
    if goal.deadline_sim_day is None:
        return GoalPriority(goalId=goal.id, score=remaining_pct, remainingPct=remaining_pct, daysRemaining=None)
    days_remaining = max(0, goal.deadline_sim_day - sim_day)
    pace_required = remaining_pct / max(days_remaining, 1)
    score = round(min(100.0, pace_required / MAX_URGENCY_PACE_PCT_PER_DAY * 100.0), 1)
    return GoalPriority(goalId=goal.id, score=score, remainingPct=remaining_pct, daysRemaining=days_remaining)


def rank_goals_by_priority(goals: list[Goal], *, sim_day: int) -> list[GoalPriority]:
    """Every active goal's real GoalPriority, highest score first —
    the Executive Priority Engine's real, checkable ranking. Non-active
    goals are simply excluded, the same way Chapter 59's own
    `rank_trade_proposals()` never ranks anything outside its own real
    pending-queue scope."""
    priorities = [compute_goal_priority(g, sim_day=sim_day) for g in goals]
    real_priorities = [p for p in priorities if p is not None]
    real_priorities.sort(key=lambda p: p.score, reverse=True)
    return real_priorities
