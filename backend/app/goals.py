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
concept — the "next honest slice" this chapter's own Implementation
Notes named, deliberately sequenced ahead of the Executive Priority
Engine and Resource Allocation (both still explicitly out of scope: an
Executive Priority Engine ranking goals against each other — Chapter
59's own trade-proposal Priority Score is a structurally different
object, not reused here — and Resource Allocation recommendations,
which depend on the other two existing first). A goal is always "reach
at least targetValue" — every real metric below is a "higher is better"
number, so a reduce-below-X goal type would need its own honest design,
not invented here.
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
