"""Institutional Evolution Engine — Design Bible Chapter 74 Part 2.

Same underlying architecture as Part 1's CLSIS (app/self_improvement.py)
at a longer time horizon: company-wide/monthly rather than
individual/event-level. Composes already-real monthly reports
(StrategicReview, ExecutiveReview, CoachReport) rather than competing
with them — see the Design Bible chapter's own cadence/focus table
against BoardReport/StrategicReview/ExecutiveReview/CoachReport.

The Company Evolution Score is a disclosed, unweighted mean of five
real, period-scoped counts or deltas — explicitly NOT a re-read of
CompanyHealth's 21 sub-scores or CompanyScore's 7-metric mean (see the
chapter's own Ownership table for why that would be duplication). Every
factor is published alongside the overall score.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import (
    SUCCESS_CASE_STUDY_CATEGORIES,
    AgentId,
    CaseStudy,
    CoachReport,
    CompanyEvolutionScore,
    ConstitutionAmendment,
    ExecutiveReview,
    FailedStrategyArchiveEntry,
    FoundationalMentorId,
    FoundationalMentorProgress,
    InstitutionalEvolutionReport,
    SelfImprovementProposal,
    StrategicReview,
    StrategyHallOfFameEntry,
)

MAX_EVOLUTION_REPORTS = 20

# Window lengths in real sim-days, matching this codebase's own
# monthly/quarterly cadence conventions elsewhere (30-day months).
WINDOW_DAYS = {"monthly": 30, "quarterly": 90, "yearly": 365}

# Normalization caps for each factor below — fixed, published constants,
# no adaptive or hidden weighting (see the Design Bible chapter's own
# Decision Logic section).
LEARNING_VOLUME_CAP = 10
KNOWLEDGE_GROWTH_CAP = 5
STRATEGY_MATURATION_CAP = 3


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _pct(count: float, cap: float) -> float:
    return round(min(100.0, count / cap * 100.0), 1) if cap > 0 else 0.0


def compute_company_evolution_score(
    *,
    window: str,
    current_sim_day: int,
    case_studies: list[CaseStudy],
    self_improvement_proposals: list[SelfImprovementProposal],
    mentor_progress: dict[AgentId, dict[FoundationalMentorId, FoundationalMentorProgress]],
    strategy_hall_of_fame: list[StrategyHallOfFameEntry],
    strategy_failed_archive: list[FailedStrategyArchiveEntry],
    constitution_amendments: list[ConstitutionAmendment],
) -> CompanyEvolutionScore:
    days = WINDOW_DAYS[window]
    period_start = max(0, current_sim_day - days)

    learning_volume_count = sum(1 for c in case_studies if period_start <= c.sim_day <= current_sim_day)
    learning_volume = _pct(learning_volume_count, LEARNING_VOLUME_CAP)

    generated_in_period = [
        p for p in self_improvement_proposals if period_start <= p.sim_day <= current_sim_day
    ]
    resolved_favorably = sum(1 for p in generated_in_period if p.status in ("approved", "implemented"))
    proposal_execution = (
        round(resolved_favorably / len(generated_in_period) * 100.0, 1) if generated_in_period else 0.0
    )

    # graduated_sim_day is the one real, period-scoped signal
    # FoundationalMentorProgress carries — a real graduation event, not
    # a fabricated "knowledge gained" delta.
    graduations_in_period = sum(
        1
        for tracks in mentor_progress.values()
        for p in tracks.values()
        if p.graduated_sim_day is not None and period_start <= p.graduated_sim_day <= current_sim_day
    )
    knowledge_growth = _pct(graduations_in_period, KNOWLEDGE_GROWTH_CAP)

    hof_in_period = sum(1 for e in strategy_hall_of_fame if period_start <= e.sim_day <= current_sim_day)
    failed_in_period = sum(1 for e in strategy_failed_archive if period_start <= e.sim_day <= current_sim_day)
    strategy_maturation = _pct(max(0, hof_in_period - failed_in_period), STRATEGY_MATURATION_CAP)

    # sim_day on a ConstitutionAmendment is stamped when it was proposed,
    # not when it was ratified — the closest real, period-scoped proxy
    # this codebase has, since no separate ratified-at sim_day exists.
    # A rare, binary signal by design (amendments are intentionally
    # infrequent), so an approximate window is an honest trade-off, not
    # a fabricated one.
    amendment_ratified = any(
        a.ceo_decision == "approved" and period_start <= a.sim_day <= current_sim_day
        for a in constitution_amendments
    )
    governance_evolution = 100.0 if amendment_ratified else 0.0

    overall = round(
        (learning_volume + proposal_execution + knowledge_growth + strategy_maturation + governance_evolution) / 5,
        1,
    )

    return CompanyEvolutionScore(
        window=window,  # type: ignore[arg-type]
        overall=overall,
        learningVolume=learning_volume,
        proposalExecution=proposal_execution,
        knowledgeGrowth=knowledge_growth,
        strategyMaturation=strategy_maturation,
        governanceEvolution=governance_evolution,
        periodStartSimDay=period_start,
        periodEndSimDay=current_sim_day,
        computedAt=_now_iso(),
    )


def generate_institutional_evolution_report(
    *,
    report_id: str,
    sim_day: int,
    strategic_reviews: list[StrategicReview],
    executive_reviews: list[ExecutiveReview],
    coach_reports: list[CoachReport],
    case_studies: list[CaseStudy],
    self_improvement_proposals: list[SelfImprovementProposal],
    evolution_score: CompanyEvolutionScore,
) -> InstitutionalEvolutionReport:
    """Composes — never recomputes — the period's own already-real
    monthly reports. proposals_generated/resolved are windowed to the
    same period the evolution_score itself was computed over."""
    latest_strategic = strategic_reviews[-1] if strategic_reviews else None
    latest_executive = executive_reviews[-1] if executive_reviews else None
    monthly_coach_reports = [r for r in coach_reports if r.period == "monthly"]
    latest_coach = monthly_coach_reports[-1] if monthly_coach_reports else None

    period_studies = [
        c
        for c in case_studies
        if evolution_score.period_start_sim_day <= c.sim_day <= evolution_score.period_end_sim_day
    ]
    top_case_studies = sorted(
        (c for c in period_studies if c.category not in SUCCESS_CASE_STUDY_CATEGORIES),
        key=lambda c: c.trade_pnl_pct,
    )[:3]
    top_success_studies = sorted(
        (c for c in period_studies if c.category in SUCCESS_CASE_STUDY_CATEGORIES),
        key=lambda c: c.trade_pnl_pct,
        reverse=True,
    )[:3]

    generated_in_period = [
        p
        for p in self_improvement_proposals
        if evolution_score.period_start_sim_day <= p.sim_day <= evolution_score.period_end_sim_day
    ]
    resolved_in_period = [p for p in generated_in_period if p.status != "pending"]

    summary = (
        f"This period filed {len(period_studies)} case studies, generated {len(generated_in_period)} "
        f"self-improvement proposals ({len(resolved_in_period)} resolved), and closed with a Company "
        f"Evolution Score of {evolution_score.overall:.0f}/100."
    )

    return InstitutionalEvolutionReport(
        id=report_id,
        strategicReviewId=latest_strategic.id if latest_strategic else None,
        executiveReviewId=latest_executive.id if latest_executive else None,
        coachReportId=latest_coach.id if latest_coach else None,
        topCaseStudyIds=[c.id for c in top_case_studies],
        topSuccessStudyIds=[c.id for c in top_success_studies],
        proposalsGenerated=[p.id for p in generated_in_period],
        proposalsResolved=[p.id for p in resolved_in_period],
        evolutionScore=evolution_score,
        summary=summary,
        simDay=sim_day,
        createdAt=_now_iso(),
    )


def record_evolution_report(
    reports: list[InstitutionalEvolutionReport], report: InstitutionalEvolutionReport
) -> list[InstitutionalEvolutionReport]:
    updated = [*reports, report]
    if len(updated) > MAX_EVOLUTION_REPORTS:
        del updated[: len(updated) - MAX_EVOLUTION_REPORTS]
    return updated
