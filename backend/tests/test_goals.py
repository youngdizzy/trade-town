"""Covers app/goals.py — v0.7 Design Bible Chapter 64's smallest real
slice: a CEO-authored goal tracking one real, already-computed metric.
Every metric reading here comes from an already-real object
(CompanyHealth/CompanyScore/PaperPortfolio/AcademyState) — nothing is
randomized or fabricated.
"""
from __future__ import annotations

from app.goals import (
    MAX_STRATEGIC_REVIEWS,
    compute_goal_priority,
    compute_resource_allocation,
    create_goal,
    generate_strategic_review,
    rank_goals_by_priority,
    record_goal,
    record_strategic_review,
    resolve_metric_value,
    tick_goal,
    tick_goals,
    validate_target_value,
)
from app.goals import cancel_goal as cancel_goal_entry
from app.portfolio import default_portfolio
from app.schemas import AcademyState, CompanyHealth, CompanyScore, Goal, StrategicReview, TimeState


def _now_iso() -> str:
    return "2026-01-01T00:00:00+00:00"


def _company_score(overall: float = 65.0) -> CompanyScore:
    return CompanyScore(
        overall=overall,
        researchQuality=60.0,
        decisionQuality=60.0,
        riskManagement=60.0,
        paperTradingPerformance=60.0,
        teamCoordination=60.0,
        knowledgeGrowth=60.0,
        simulationSuccess=60.0,
        updatedAt=_now_iso(),
    )


def _company_health(combined_overall: float = 60.0) -> CompanyHealth:
    return CompanyHealth(
        overall=60.0,
        tier="stable",
        operationalStability=60.0,
        departmentEfficiency=60.0,
        employeeMorale=60.0,
        researchProgress=60.0,
        capitalHealth=60.0,
        resourceUsage=60.0,
        reputation=60.0,
        technologyLevel=60.0,
        officeExpansion=60.0,
        educationProgress=60.0,
        combinedOverall=combined_overall,
        updatedAt=_now_iso(),
    )


def _academy_state(level: int = 2) -> AcademyState:
    return AcademyState(level=level, levelLabel="Research Library", totalPoints=50.0, completedProjectCount=5, updatedAt=_now_iso())


def _goal(**overrides) -> Goal:
    defaults = dict(
        goal_id="goal-1",
        title="Reach a Company Score of 80",
        category="growth",
        target_metric="company_score_overall",
        target_value=80.0,
        deadline_sim_day=None,
        created_sim_day=1,
        current_value=65.0,
    )
    defaults.update(overrides)
    return create_goal(**defaults)


class TestValidateTargetValue:
    def test_rejects_a_non_positive_target(self) -> None:
        assert validate_target_value("company_score_overall", 0.0) is not None
        assert validate_target_value("company_score_overall", -5.0) is not None

    def test_rejects_a_target_above_the_real_ceiling(self) -> None:
        assert validate_target_value("company_health_combined", 101.0) is not None
        assert validate_target_value("academy_level", 6.0) is not None

    def test_accepts_a_real_achievable_target(self) -> None:
        assert validate_target_value("company_score_overall", 85.0) is None
        assert validate_target_value("academy_level", 5.0) is None

    def test_portfolio_return_has_no_upper_ceiling(self) -> None:
        assert validate_target_value("portfolio_return_pct", 500.0) is None


class TestResolveMetricValue:
    def test_reads_the_real_combined_company_health(self) -> None:
        value = resolve_metric_value("company_health_combined", company_health=_company_health(72.5), company_score=_company_score(), portfolio=default_portfolio(), academy_state=_academy_state())
        assert value == 72.5

    def test_reads_the_real_company_score(self) -> None:
        value = resolve_metric_value("company_score_overall", company_health=_company_health(), company_score=_company_score(88.0), portfolio=default_portfolio(), academy_state=_academy_state())
        assert value == 88.0

    def test_reads_the_real_portfolio_return(self) -> None:
        portfolio = default_portfolio().model_copy(update={"total_pnl_pct": 12.3})
        value = resolve_metric_value("portfolio_return_pct", company_health=_company_health(), company_score=_company_score(), portfolio=portfolio, academy_state=_academy_state())
        assert value == 12.3

    def test_reads_the_real_academy_level(self) -> None:
        value = resolve_metric_value("academy_level", company_health=_company_health(), company_score=_company_score(), portfolio=default_portfolio(), academy_state=_academy_state(level=4))
        assert value == 4.0


class TestCreateGoal:
    def test_builds_a_real_active_goal_with_computed_progress(self) -> None:
        goal = _goal(target_value=80.0, current_value=40.0)
        assert goal.status == "active"
        assert goal.current_value == 40.0
        assert goal.progress_pct == 50.0
        assert goal.completed_at is None


class TestTickGoal:
    def test_stays_active_while_below_target(self) -> None:
        goal = _goal(target_value=100.0, current_value=50.0)
        updated = tick_goal(goal, current_value=60.0, sim_day=5)
        assert updated.status == "active"
        assert updated.current_value == 60.0
        assert updated.progress_pct == 60.0

    def test_completes_once_current_value_reaches_target(self) -> None:
        goal = _goal(target_value=80.0, current_value=40.0)
        updated = tick_goal(goal, current_value=85.0, sim_day=5)
        assert updated.status == "completed"
        assert updated.completed_at is not None
        assert updated.progress_pct == 100.0

    def test_expires_past_an_unmet_deadline(self) -> None:
        goal = _goal(target_value=100.0, current_value=40.0, deadline_sim_day=10)
        updated = tick_goal(goal, current_value=50.0, sim_day=11)
        assert updated.status == "expired"

    def test_a_completed_goal_never_changes_again(self) -> None:
        goal = _goal(target_value=80.0, current_value=40.0)
        completed = tick_goal(goal, current_value=85.0, sim_day=5)
        unchanged = tick_goal(completed, current_value=10.0, sim_day=6)
        assert unchanged.status == "completed"
        assert unchanged.current_value == completed.current_value

    def test_a_cancelled_goal_never_changes_again(self) -> None:
        goal = _goal(target_value=80.0, current_value=40.0)
        cancelled = cancel_goal_entry([goal], goal.id)[0]
        unchanged = tick_goal(cancelled, current_value=90.0, sim_day=6)
        assert unchanged.status == "cancelled"
        assert unchanged.current_value == 40.0


class TestTickGoals:
    def test_recomputes_every_active_goal_from_real_current_state(self) -> None:
        health_goal = _goal(goal_id="g1", target_metric="company_health_combined", target_value=90.0, current_value=50.0)
        score_goal = _goal(goal_id="g2", target_metric="company_score_overall", target_value=90.0, current_value=50.0)
        updated = tick_goals(
            [health_goal, score_goal],
            company_health=_company_health(combined_overall=75.0),
            company_score=_company_score(overall=95.0),
            portfolio=default_portfolio(),
            academy_state=_academy_state(),
            sim_day=2,
        )
        assert updated[0].current_value == 75.0
        assert updated[0].status == "active"
        assert updated[1].current_value == 95.0
        assert updated[1].status == "completed"


class TestRecordGoal:
    def test_caps_at_max_goals_evicting_the_oldest(self) -> None:
        goals = [_goal(goal_id=f"g{i}") for i in range(20)]
        overflowed = record_goal(goals, _goal(goal_id="g20"))
        assert len(overflowed) == 20
        assert overflowed[0].id == "g1"
        assert overflowed[-1].id == "g20"


class TestCancelGoal:
    def test_cancels_an_active_goal(self) -> None:
        goal = _goal()
        updated = cancel_goal_entry([goal], goal.id)
        assert updated[0].status == "cancelled"

    def test_leaves_other_goals_untouched(self) -> None:
        a, b = _goal(goal_id="a"), _goal(goal_id="b")
        updated = cancel_goal_entry([a, b], "a")
        assert updated[0].status == "cancelled"
        assert updated[1].status == "active"


class TestMilestoneTracking:
    """v0.7 Design Bible Chapter 64 (second pass) — real, fixed
    checkpoints (25/50/75%) on a goal's own real progress, never a
    second independently-tracked concept."""

    def test_a_new_goal_starts_with_three_unreached_milestones(self) -> None:
        goal = _goal(target_value=100.0, current_value=0.0)
        assert [m.threshold_pct for m in goal.milestones] == [25.0, 50.0, 75.0]
        assert all(not m.reached and m.reached_at is None for m in goal.milestones)

    def test_a_goal_can_start_past_a_milestone(self) -> None:
        # Real starting progress is checked at creation too, not just on
        # the next tick — e.g. the CEO sets a target the company is
        # already 40% of the way to.
        goal = _goal(target_value=100.0, current_value=40.0)
        reached = {m.threshold_pct: m.reached for m in goal.milestones}
        assert reached[25.0] is True
        assert reached[50.0] is False
        assert reached[75.0] is False

    def test_tick_marks_a_newly_crossed_milestone_reached(self) -> None:
        goal = _goal(target_value=100.0, current_value=10.0)
        updated = tick_goal(goal, current_value=30.0, sim_day=2)
        milestone_25 = next(m for m in updated.milestones if m.threshold_pct == 25.0)
        assert milestone_25.reached is True
        assert milestone_25.reached_at is not None
        milestone_50 = next(m for m in updated.milestones if m.threshold_pct == 50.0)
        assert milestone_50.reached is False

    def test_a_reached_milestone_never_reverts(self) -> None:
        goal = _goal(target_value=100.0, current_value=10.0)
        crossed = tick_goal(goal, current_value=30.0, sim_day=2)
        milestone_25_first = next(m for m in crossed.milestones if m.threshold_pct == 25.0)
        # A later tick where the metric happens to dip back down must not
        # un-reach an already-crossed milestone.
        dipped = tick_goal(crossed, current_value=20.0, sim_day=3)
        milestone_25_after = next(m for m in dipped.milestones if m.threshold_pct == 25.0)
        assert milestone_25_after.reached is True
        assert milestone_25_after.reached_at == milestone_25_first.reached_at

    def test_completion_marks_every_milestone_reached(self) -> None:
        goal = _goal(target_value=100.0, current_value=10.0)
        completed = tick_goal(goal, current_value=100.0, sim_day=2)
        assert completed.status == "completed"
        assert all(m.reached for m in completed.milestones)

    def test_milestones_never_change_once_a_goal_is_no_longer_active(self) -> None:
        goal = _goal(target_value=100.0, current_value=10.0)
        cancelled = cancel_goal_entry([goal], goal.id)[0]
        unchanged = tick_goal(cancelled, current_value=90.0, sim_day=2)
        assert unchanged.milestones == cancelled.milestones


class TestComputeGoalPriority:
    """v0.7 Design Bible Chapter 64 (third pass) — the Executive
    Priority Engine's real, named formula over real fields only."""

    def test_none_for_a_non_active_goal(self) -> None:
        goal = _goal(target_value=100.0, current_value=50.0)
        cancelled = cancel_goal_entry([goal], goal.id)[0]
        assert compute_goal_priority(cancelled, sim_day=5) is None

    def test_no_deadline_scores_by_remaining_distance_alone(self) -> None:
        goal = _goal(target_value=100.0, current_value=40.0, deadline_sim_day=None)
        priority = compute_goal_priority(goal, sim_day=5)
        assert priority is not None
        assert priority.score == 60.0
        assert priority.remaining_pct == 60.0
        assert priority.days_remaining is None

    def test_a_tight_deadline_reads_as_maximally_urgent(self) -> None:
        # 50% remaining with only 1 real day left is a 50%/day pace,
        # far above the real MAX_URGENCY_PACE_PCT_PER_DAY ceiling (5.0)
        # — the score clamps at the real maximum, 100.
        goal = _goal(target_value=100.0, current_value=50.0, deadline_sim_day=6)
        priority = compute_goal_priority(goal, sim_day=5)
        assert priority is not None
        assert priority.score == 100.0
        assert priority.days_remaining == 1

    def test_a_generous_deadline_reads_as_low_urgency(self) -> None:
        # 10% remaining over 100 real days is a 0.1%/day pace — a real,
        # low fraction of the 5.0%/day ceiling.
        goal = _goal(target_value=100.0, current_value=90.0, deadline_sim_day=105)
        priority = compute_goal_priority(goal, sim_day=5)
        assert priority is not None
        assert priority.score == 2.0
        assert priority.days_remaining == 100

    def test_a_passed_deadline_still_computes_a_real_score(self) -> None:
        # days_remaining floors at 0, never negative — the pace
        # calculation still produces a real, maximally-urgent number
        # rather than dividing by a negative/zero day count.
        goal = _goal(target_value=100.0, current_value=50.0, deadline_sim_day=3)
        priority = compute_goal_priority(goal, sim_day=5)
        assert priority is not None
        assert priority.days_remaining == 0
        assert priority.score == 100.0


class TestRankGoalsByPriority:
    def test_ranks_by_score_descending(self) -> None:
        urgent = _goal(goal_id="urgent", target_value=100.0, current_value=50.0, deadline_sim_day=6)
        relaxed = _goal(goal_id="relaxed", target_value=100.0, current_value=90.0, deadline_sim_day=105)
        ranked = rank_goals_by_priority([relaxed, urgent], sim_day=5)
        assert [p.goal_id for p in ranked] == ["urgent", "relaxed"]

    def test_excludes_non_active_goals(self) -> None:
        active = _goal(goal_id="active", target_value=100.0, current_value=50.0)
        cancelled_goal = _goal(goal_id="gone", target_value=100.0, current_value=50.0)
        cancelled = cancel_goal_entry([cancelled_goal], cancelled_goal.id)[0]
        ranked = rank_goals_by_priority([active, cancelled], sim_day=5)
        assert [p.goal_id for p in ranked] == ["active"]


class TestComputeResourceAllocation:
    """v0.7 Design Bible Chapter 64 (fourth pass) — Resource Allocation.
    A recommend-only share of executive attention normalized from the
    same real Priority Engine scores, never a claim about capital."""

    def test_empty_for_no_active_goals(self) -> None:
        assert compute_resource_allocation([], sim_day=5) == []

    def test_single_active_goal_gets_full_allocation(self) -> None:
        goal = _goal(goal_id="solo", target_value=100.0, current_value=50.0)
        allocations = compute_resource_allocation([goal], sim_day=5)
        assert len(allocations) == 1
        assert allocations[0].goal_id == "solo"
        assert allocations[0].allocation_pct == 100.0

    def test_allocations_sum_to_100_and_favor_the_more_urgent_goal(self) -> None:
        urgent = _goal(goal_id="urgent", target_value=100.0, current_value=50.0, deadline_sim_day=6)
        relaxed = _goal(goal_id="relaxed", target_value=100.0, current_value=90.0, deadline_sim_day=105)
        allocations = compute_resource_allocation([relaxed, urgent], sim_day=5)
        assert [a.goal_id for a in allocations] == ["urgent", "relaxed"]
        assert sum(a.allocation_pct for a in allocations) == 100.0
        assert allocations[0].allocation_pct > allocations[1].allocation_pct

    def test_excludes_non_active_goals(self) -> None:
        active = _goal(goal_id="active", target_value=100.0, current_value=50.0)
        cancelled_goal = _goal(goal_id="gone", target_value=100.0, current_value=50.0)
        cancelled = cancel_goal_entry([cancelled_goal], cancelled_goal.id)[0]
        allocations = compute_resource_allocation([active, cancelled], sim_day=5)
        assert [a.goal_id for a in allocations] == ["active"]

    def test_even_split_when_every_active_goal_has_zero_urgency(self) -> None:
        # A goal created with current_value already at/above target_value
        # stays "active" until the next tick marks it completed — a
        # real, honest edge case, not a fabricated scenario.
        maxed_a = _goal(goal_id="maxed-a", target_value=100.0, current_value=100.0)
        maxed_b = _goal(goal_id="maxed-b", target_value=100.0, current_value=100.0)
        allocations = compute_resource_allocation([maxed_a, maxed_b], sim_day=5)
        assert {a.allocation_pct for a in allocations} == {50.0}


def _time(day: int = 30) -> TimeState:
    return TimeState(day=day, hour=20, minute=0)


def _completed_goal(goal_id: str, *, completed_at: str, title: str = "Completed goal") -> Goal:
    return Goal(
        id=goal_id,
        title=title,
        category="growth",
        targetMetric="company_score_overall",
        targetValue=80.0,
        currentValue=80.0,
        progressPct=100.0,
        createdSimDay=1,
        deadlineSimDay=None,
        status="completed",
        createdAt="2026-01-01T00:00:00+00:00",
        updatedAt=completed_at,
        completedAt=completed_at,
        milestones=[],
    )


def _expired_goal(goal_id: str, *, updated_at: str, title: str = "Expired goal") -> Goal:
    return Goal(
        id=goal_id,
        title=title,
        category="growth",
        targetMetric="company_score_overall",
        targetValue=80.0,
        currentValue=40.0,
        progressPct=50.0,
        createdSimDay=1,
        deadlineSimDay=5,
        status="expired",
        createdAt="2026-01-01T00:00:00+00:00",
        updatedAt=updated_at,
        completedAt=None,
        milestones=[],
    )


class TestGenerateStrategicReview:
    """v0.7 Design Bible Chapter 64 (fifth pass) — the Strategic Review
    Cycle. Every field is a real derivation from Goal/Milestone/
    GoalPriority — no fabricated period-over-period number."""

    def test_no_previous_review_counts_active_goals(self) -> None:
        active = _goal(goal_id="active-1", target_value=100.0, current_value=50.0)
        review = generate_strategic_review([active], sim_day=5, new_time=_time(), previous_review_created_at=None)
        assert review.active_goal_count == 1
        assert review.id == "strategic-review-30-20-0"

    def test_no_previous_review_includes_every_real_completion_and_expiry(self) -> None:
        completed = _completed_goal("done-1", completed_at="2026-01-05T00:00:00+00:00", title="Reach elite score")
        expired = _expired_goal("gone-1", updated_at="2026-01-05T00:00:00+00:00", title="Missed deadline goal")
        review = generate_strategic_review([completed, expired], sim_day=5, new_time=_time(), previous_review_created_at=None)
        assert review.completed_since_last_review == ["Reach elite score"]
        assert review.expired_since_last_review == ["Missed deadline goal"]

    def test_excludes_completions_and_expiries_from_before_the_previous_review(self) -> None:
        previous_review_at = "2026-02-01T00:00:00+00:00"
        old_completion = _completed_goal("old-done", completed_at="2026-01-05T00:00:00+00:00", title="Old completion")
        new_completion = _completed_goal("new-done", completed_at="2026-02-15T00:00:00+00:00", title="New completion")
        old_expiry = _expired_goal("old-expired", updated_at="2026-01-05T00:00:00+00:00", title="Old expiry")
        review = generate_strategic_review(
            [old_completion, new_completion, old_expiry], sim_day=5, new_time=_time(), previous_review_created_at=previous_review_at
        )
        assert review.completed_since_last_review == ["New completion"]
        assert review.expired_since_last_review == []

    def test_counts_milestones_reached_since_the_previous_review(self) -> None:
        previous_review_at = "2026-02-01T00:00:00+00:00"
        goal = _goal(goal_id="milestone-goal", target_value=100.0, current_value=10.0)
        goal = tick_goal(goal, current_value=80.0, sim_day=5)  # crosses 25/50/75 in one tick, all reached "now"
        review = generate_strategic_review([goal], sim_day=5, new_time=_time(), previous_review_created_at=previous_review_at)
        assert review.milestones_reached_since_last_review == 3

    def test_top_priority_reflects_the_real_priority_engine(self) -> None:
        urgent = _goal(goal_id="urgent", target_value=100.0, current_value=50.0, deadline_sim_day=6)
        relaxed = _goal(goal_id="relaxed", target_value=100.0, current_value=90.0, deadline_sim_day=105)
        review = generate_strategic_review([relaxed, urgent], sim_day=5, new_time=_time(), previous_review_created_at=None)
        assert review.top_priority_goal_id == "urgent"
        assert review.top_priority_score == 100.0

    def test_no_goals_at_all_produces_an_honest_empty_review(self) -> None:
        review = generate_strategic_review([], sim_day=5, new_time=_time(), previous_review_created_at=None)
        assert review.active_goal_count == 0
        assert review.top_priority_goal_id is None
        assert "No goal activity to report" in review.summary


class TestRecordStrategicReview:
    def test_appends_a_review(self) -> None:
        review = StrategicReview(
            id="strategic-review-1-0-0",
            createdAt="2026-01-01T00:00:00+00:00",
            activeGoalCount=1,
            completedSinceLastReview=[],
            expiredSinceLastReview=[],
            milestonesReachedSinceLastReview=0,
            topPriorityGoalId=None,
            topPriorityScore=None,
            summary="1 active goal(s) this period.",
        )
        updated = record_strategic_review([], review)
        assert updated == [review]

    def test_caps_at_max_strategic_reviews_evicting_oldest_first(self) -> None:
        reviews: list[StrategicReview] = []
        for i in range(MAX_STRATEGIC_REVIEWS + 5):
            review = StrategicReview(
                id=f"strategic-review-{i}",
                createdAt=f"2026-01-{(i % 28) + 1:02d}T00:00:00+00:00",
                activeGoalCount=0,
                completedSinceLastReview=[],
                expiredSinceLastReview=[],
                milestonesReachedSinceLastReview=0,
                topPriorityGoalId=None,
                topPriorityScore=None,
                summary="",
            )
            reviews = record_strategic_review(reviews, review)
        assert len(reviews) == MAX_STRATEGIC_REVIEWS
        assert reviews[0].id == "strategic-review-5"
        assert reviews[-1].id == f"strategic-review-{MAX_STRATEGIC_REVIEWS + 4}"
