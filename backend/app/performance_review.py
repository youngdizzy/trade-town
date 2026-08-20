"""Agent Performance Reviews — CEO directive "Features 26-30: Agent
Intelligence, Learning & Institutional Memory System," Feature 27 (the
second stage of the 26->27->28->29->30 learning loop; per the
directive's own staging rule, this does not begin until Feature 26 is
tested and integrated, and Feature 28 does not begin until this one is).

Research finding (recorded here per the directive's "document what was
found before coding" rule): this codebase already has several real,
narrow, single-dimension per-agent signals — app/coach.py's `AgentScore`
(but scoped to only the 4 `RESEARCHER_IDS`, never Sentinel/Guardian/
Keystone/etc.), app/mentor.py's `ThinkingProfile` (universal, but every
trait fake-defaults to a neutral 50.0 with zero real evidence instead of
an honest NOT_ENOUGH_EVIDENCE state), app/executive_intelligence.py's
`ExecutiveAccuracyScore`/`DepartmentSelfEvaluation` (per-department-seat,
not per-agent — a seat's occupant varies by decision), and
app/self_improvement.py's `ExecutiveLearningSummary` (a thin composition
of the above with no new evaluation logic, no sample-size disclosure,
no role-awareness, no process-vs-outcome split). None of these is a
multi-dimensional, role-aware, evidence-gated, process-vs-outcome-
separated per-agent review — that gap is what this module closes, as a
SYNTHESIS layer over real, already-computed evidence, not a parallel
scoring engine. app/mentor.py's own module docstring already names this
exact gap explicitly: "Personal Coaching / improvement areas per
employee — would require a real per-agent weakness signal distinct from
ThinkingProfile's own traits ... none exists, so this is left as an
explicit scope cut."

Every dimension below reuses an existing real computation or an
existing real field wherever one exists (app/analytics.py's
research_accuracy()/confidence_accuracy(), app/mentor.py's
_factor_average() and _COLLABORATION_EVENTS_FOR_100, app/discipline.py's
own process-score-never-sees-pnl separation, app/academy.py's
AgentKnowledgeState.tier) — nothing here recomputes an existing formula
a second, possibly-drifting way. Where a dimension's underlying record
type has no sim_day field to bucket by real period (ResearchItem,
LearningEvent), the dimension is honestly computed all-time instead of
period-scoped, and says so in its own `evidence` string, rather than
faking a period boundary.

NOT_ENOUGH_EVIDENCE is `PerformanceDimension.value=None` — reusing
app/process_adherence.py's exact two-tier honesty shape (a nullable
float at the aggregate, `sample_size` always disclosed alongside it)
rather than app/mentor.py's fake-neutral-50 anti-pattern. `role_class`
(this codebase's first machine-usable role taxonomy over AGENT_PROFILES)
exists so a reader can tell "Sentinel has no decisionAccuracy evidence"
apart from "this review is broken" — Sentinel structurally never
receives a ResearchItem assignment (see app/research.py's
RESEARCHER_IDS), so that's the honest truth about the role, not a gap.

Outcome quality and process quality are kept structurally separate
(`process_quality_avg`/`outcome_quality_avg`), mirroring
app/discipline.py's own discipline (a good process that lost to real
market variance never drags down process quality; a lucky win from a
weak process never inflates it) — see PROCESS_DIMENSION_IDS/
OUTCOME_DIMENSION_IDS below. `learning_trend` and `pnl_attribution` sit
outside both averages: the former is a growth signal, not a quality
judgment; the latter is a real percentage-point P&L figure, not a 0-100
quality score, and averaging the two scales together would misrepresent
both.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from app.analytics import confidence_accuracy, research_accuracy
from app.mentor import _COLLABORATION_EVENTS_FOR_100, _factor_average
from app.schemas import (
    AgentId,
    AgentKnowledgeState,
    AgentPerformanceReview,
    AgentPerformanceReviewHistoryEntry,
    AgentReviewDataSplit,
    AgentRoleClass,
    CaseStudy,
    DisciplineReview,
    FailureClassification,
    LearningEvent,
    PaperTrade,
    PerformanceDimension,
    PerformanceDimensionId,
    ReasoningChallenge,
    ReflectionSession,
    ResearchItem,
    SUCCESS_CASE_STUDY_CATEGORIES,
    TradeDecision,
)

MAX_AGENT_PERFORMANCE_REVIEWS = 150

# This codebase's first machine-usable role-evaluation taxonomy over
# AGENT_PROFILES (previously only free-text `occupation` strings
# existed — see app/agents.py). Static: AGENT_PROFILES is a frozen
# dataclass and no career-change/role-transfer mechanism exists anywhere
# (app/talent.py's own module docstring confirms this), so this mapping
# never goes stale from game logic.
AGENT_ROLE_CLASS: dict[AgentId, AgentRoleClass] = {
    "scout": "researcher",
    "atlas": "researcher",
    "echo": "researcher",
    "nova": "researcher",
    "pulse": "researcher",
    "sentinel": "risk",
    "guardian": "risk",
    "keystone": "risk",
    "quant": "quant",
    "forge": "quant",
    "cio": "leadership",
    "coach": "mentor_support",
    "sage": "mentor_support",
    "compass": "mentor_support",
    "scribe": "mentor_support",
}

# Dimensions judged as process quality (never see P&L) vs outcome
# quality (real result, never process). learning_trend and
# pnl_attribution are deliberately in neither set — see module
# docstring for why.
PROCESS_DIMENSION_IDS: frozenset[PerformanceDimensionId] = frozenset(
    {"process_quality", "risk_discipline", "collaboration", "recurring_mistakes"}
)
OUTCOME_DIMENSION_IDS: frozenset[PerformanceDimensionId] = frozenset({"decision_accuracy", "calibration"})
# The 0-100-scaled dimensions eligible to be named "weakest" — excludes
# pnl_attribution, which is a real percentage-point figure on a
# different scale that would not be a fair comparison against a 0-100
# quality score.
COMPARABLE_DIMENSION_IDS: frozenset[PerformanceDimensionId] = PROCESS_DIMENSION_IDS | OUTCOME_DIMENSION_IDS | {"learning_trend"}

# Disclosed research assumptions (this module's own choices, not values
# already load-bearing elsewhere) — the same provenance discipline
# app/model_validation.py's threshold table and app/institutional_memory.py's
# CORROBORATION_CAP/MIN_RELEVANCE_FOR_RETRIEVAL already use.
MIN_EVIDENCE_COUNT_FOR_EVALUATED = 3
TREND_CHANGE_THRESHOLD_PCT = 5.0
LEARNING_EVENTS_FOR_100 = 2.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_dimension(dimension_id: PerformanceDimensionId, label: str, evidence: str) -> PerformanceDimension:
    return PerformanceDimension(id=dimension_id, label=label, value=None, sampleSize=0, evidence=evidence)


def _process_quality(agent_id: AgentId, reviews: list[DisciplineReview]) -> PerformanceDimension:
    if not reviews:
        return _empty_dimension("process_quality", "Process Quality", "No Discipline Reviews attended this period.")
    avg = sum(r.score for r in reviews) / len(reviews)
    return PerformanceDimension(
        id="process_quality",
        label="Process Quality",
        value=round(avg, 1),
        sampleSize=len(reviews),
        evidence=f"Averaged {avg:.1f}/100 real Discipline Review process score across {len(reviews)} review(s) this period — never includes trade P&L (app/discipline.py's own separation).",
    )


def _risk_discipline(reviews: list[DisciplineReview]) -> PerformanceDimension:
    sizing = _factor_average(reviews, "position_sizing_discipline")
    patience = _factor_average(reviews, "patience")
    parts = [v for v in (sizing, patience) if v is not None]
    if not parts:
        return _empty_dimension("risk_discipline", "Risk Discipline", "No Discipline Reviews attended this period.")
    avg = sum(parts) / len(parts)
    return PerformanceDimension(
        id="risk_discipline",
        label="Risk Discipline",
        value=round(avg, 1),
        sampleSize=len(reviews),
        evidence=f"Averaged {avg:.1f}/100 across the real Position Sizing Discipline / Patience Discipline Factors in {len(reviews)} review(s) this period.",
    )


def _decision_accuracy(agent_id: AgentId, research: list[ResearchItem]) -> PerformanceDimension:
    completed = [r for r in research if r.assigned_agent == agent_id and r.status == "completed"]
    if not completed:
        return _empty_dimension("decision_accuracy", "Decision Accuracy", "No completed research items on file (all-time — ResearchItem carries no simDay to bucket by period).")
    value = round(research_accuracy(completed), 1)
    return PerformanceDimension(
        id="decision_accuracy",
        label="Decision Accuracy",
        value=value,
        sampleSize=len(completed),
        evidence=f"{value:.1f}% of {len(completed)} completed research item(s) reached >=70% confidence (all-time, via app/analytics.py's research_accuracy()).",
    )


def _calibration(agent_id: AgentId, trades: list[PaperTrade]) -> PerformanceDimension:
    supported = [t for t in trades if agent_id in t.supporting_agents]
    if not supported:
        return _empty_dimension("calibration", "Calibration", "No closed trades supported this period.")
    value = round(confidence_accuracy(supported), 1)
    return PerformanceDimension(
        id="calibration",
        label="Calibration",
        value=value,
        sampleSize=len(supported),
        evidence=f"Averaged {value:.1f}/100 real confidence-vs-outcome calibration across {len(supported)} closed trade(s) supported this period (app/analytics.py's confidence_accuracy()).",
    )


def _collaboration(agent_id: AgentId, reasoning_challenges: list[ReasoningChallenge], reflection_sessions: list[ReflectionSession]) -> PerformanceDimension:
    contribution_count = sum(1 for c in reasoning_challenges for x in c.contributions if x.agent_id == agent_id)
    insight_count = sum(1 for s in reflection_sessions for i in s.insights if i.agent_id == agent_id)
    total = contribution_count + insight_count
    if total == 0:
        return _empty_dimension("collaboration", "Collaboration", "No Reasoning Lab contributions or Reflection Chamber insights this period.")
    value = round(min(100.0, (total / _COLLABORATION_EVENTS_FOR_100) * 100.0), 1)
    return PerformanceDimension(
        id="collaboration",
        label="Collaboration",
        value=value,
        sampleSize=total,
        evidence=f"{contribution_count} Reasoning Lab contribution(s) + {insight_count} Reflection Chamber insight(s) this period (same real signal/cap as app/mentor.py's ThinkingProfile collaboration trait).",
    )


def _learning_trend(agent_id: AgentId, knowledge: AgentKnowledgeState | None, learning_events: list[LearningEvent]) -> PerformanceDimension:
    agent_events = [e for e in learning_events if e.agent_id == agent_id]
    if not agent_events:
        return _empty_dimension("learning_trend", "Learning Trend", "No recorded Knowledge-tier crossings yet.")
    value = round(min(100.0, (len(agent_events) / LEARNING_EVENTS_FOR_100) * 100.0), 1)
    tier_note = f", currently tier {knowledge.tier} ({knowledge.level})" if knowledge is not None else ""
    return PerformanceDimension(
        id="learning_trend",
        label="Learning Trend",
        value=value,
        sampleSize=len(agent_events),
        evidence=f"{len(agent_events)} real Knowledge-tier crossing(s) on record (all-time — LearningEvent carries no simDay to bucket by period){tier_note}.",
    )


def _recurring_mistakes(
    agent_id: AgentId,
    mistake_studies: list[CaseStudy],
    trades_in_period: list[PaperTrade],
    decision_by_id: dict[str, TradeDecision],
    failure_classifications: list[FailureClassification] | None = None,
) -> PerformanceDimension:
    supported_trades = [t for t in trades_in_period if agent_id in t.supporting_agents]
    if not supported_trades:
        return _empty_dimension("recurring_mistakes", "Recurring Mistakes (inverse)", "No closed trades supported this period.")
    attributable = 0
    for study in mistake_studies:
        decision = decision_by_id.get(study.decision_id)
        if decision is not None and agent_id in decision.supporting_agents:
            attributable += 1
    mistake_free_rate = round((1 - attributable / len(supported_trades)) * 100, 1)
    evidence = (
        f"{attributable} of {len(supported_trades)} supported trade(s) this period produced a real process-gap mistake case study "
        "(higher = fewer real mistakes; a well-disciplined loss to market variance is never counted — app/mistakes.py's own distinction)."
    )
    # CEO directive Feature 30 feed-back — the Failure Review Board's own
    # real classification of WHY those trades failed, layered onto this
    # dimension's evidence string as real specificity; never changes
    # `value`/`sample_size` above, which stay CaseStudy-derived exactly
    # as before.
    if failure_classifications:
        attributed_reasons = [
            c.reason
            for c in failure_classifications
            if agent_id in c.attributed_agents and any(t.id == c.trade_id for t in supported_trades)
        ]
        if attributed_reasons:
            most_common = Counter(attributed_reasons).most_common(1)[0]
            evidence += f' The Failure Review Board most often attributed these losses to "{most_common[0].replace("_", " ")}" ({most_common[1]} trade(s)).'
    return PerformanceDimension(
        id="recurring_mistakes",
        label="Recurring Mistakes (inverse)",
        value=mistake_free_rate,
        sampleSize=len(supported_trades),
        evidence=evidence,
    )


def _pnl_attribution(agent_id: AgentId, trades_in_period: list[PaperTrade]) -> PerformanceDimension:
    supported = [t for t in trades_in_period if agent_id in t.supporting_agents]
    if not supported:
        return _empty_dimension("pnl_attribution", "P&L Attribution", "No closed trades supported this period.")
    avg_pnl_pct = round(sum(t.pnl_pct for t in supported) / len(supported), 2)
    return PerformanceDimension(
        id="pnl_attribution",
        label="P&L Attribution",
        value=avg_pnl_pct,
        sampleSize=len(supported),
        evidence=f"Averaged {avg_pnl_pct:+.2f}% real P&L across {len(supported)} closed trade(s) supported this period — a real percentage, not a 0-100 quality score.",
    )


def compute_agent_performance_review(
    agent_id: AgentId,
    *,
    discipline_reviews: list[DisciplineReview],
    research: list[ResearchItem],
    trades: list[PaperTrade],
    decisions: list[TradeDecision],
    case_studies: list[CaseStudy],
    reasoning_challenges: list[ReasoningChallenge],
    reflection_sessions: list[ReflectionSession],
    agent_knowledge: dict[AgentId, AgentKnowledgeState],
    learning_events: list[LearningEvent],
    failure_classifications: list[FailureClassification] | None = None,
    period_start_sim_day: int,
    period_end_sim_day: int,
    sim_day: int,
    previous_review: AgentPerformanceReview | None,
) -> AgentPerformanceReview:
    """One real review for one agent over [period_start_sim_day,
    period_end_sim_day]. Every dimension is computed from real,
    already-existing state; nothing here is randomly generated or
    interpolated. See module docstring for exactly which dimensions can
    honestly be period-scoped vs. must stay all-time given this
    codebase's real field availability."""
    reviews_in_period = [r for r in discipline_reviews if agent_id in r.attendees and period_start_sim_day <= r.sim_day <= period_end_sim_day]
    trades_in_period = [t for t in trades if period_start_sim_day <= t.closed_sim_minutes // 1440 <= period_end_sim_day]
    mistake_studies_in_period = [
        cs for cs in case_studies if cs.category not in SUCCESS_CASE_STUDY_CATEGORIES and period_start_sim_day <= cs.sim_day <= period_end_sim_day
    ]
    reasoning_in_period = [c for c in reasoning_challenges if period_start_sim_day <= c.sim_day <= period_end_sim_day]
    reflection_in_period = [s for s in reflection_sessions if period_start_sim_day <= s.sim_day <= period_end_sim_day]
    decision_by_id = {d.id: d for d in decisions}

    dimensions = [
        _process_quality(agent_id, reviews_in_period),
        _risk_discipline(reviews_in_period),
        _decision_accuracy(agent_id, research),
        _calibration(agent_id, trades_in_period),
        _collaboration(agent_id, reasoning_in_period, reflection_in_period),
        _learning_trend(agent_id, agent_knowledge.get(agent_id), learning_events),
        _recurring_mistakes(agent_id, mistake_studies_in_period, trades_in_period, decision_by_id, failure_classifications),
        _pnl_attribution(agent_id, trades_in_period),
    ]

    process_values = [d.value for d in dimensions if d.id in PROCESS_DIMENSION_IDS and d.value is not None]
    outcome_values = [d.value for d in dimensions if d.id in OUTCOME_DIMENSION_IDS and d.value is not None]
    process_quality_avg = round(sum(process_values) / len(process_values), 1) if process_values else None
    outcome_quality_avg = round(sum(outcome_values) / len(outcome_values), 1) if outcome_values else None

    evidence_count = sum(d.sample_size for d in dimensions)
    confidence_pct = round(sum(1 for d in dimensions if d.value is not None) / len(dimensions) * 100, 1)
    status = "evaluated" if evidence_count >= MIN_EVIDENCE_COUNT_FOR_EVALUATED else "not_enough_evidence"

    comparable = [d for d in dimensions if d.id in COMPARABLE_DIMENSION_IDS and d.value is not None]
    weakest_dimension_id = min(comparable, key=lambda d: d.value if d.value is not None else 0.0).id if comparable else None

    trend: str
    current_composite_parts = [v for v in (process_quality_avg, outcome_quality_avg) if v is not None]
    current_composite = sum(current_composite_parts) / len(current_composite_parts) if current_composite_parts else None
    if previous_review is None or current_composite is None:
        trend = "not_enough_history"
    else:
        previous_composite_parts = [v for v in (previous_review.process_quality_avg, previous_review.outcome_quality_avg) if v is not None]
        previous_composite = sum(previous_composite_parts) / len(previous_composite_parts) if previous_composite_parts else None
        if previous_composite is None:
            trend = "not_enough_history"
        else:
            diff = current_composite - previous_composite
            trend = "improving" if diff >= TREND_CHANGE_THRESHOLD_PCT else "declining" if diff <= -TREND_CHANGE_THRESHOLD_PCT else "stable"

    return AgentPerformanceReview(
        id=f"perfreview-{agent_id}-{period_end_sim_day}",
        agentId=agent_id,
        roleClass=AGENT_ROLE_CLASS[agent_id],
        periodStartSimDay=period_start_sim_day,
        periodEndSimDay=period_end_sim_day,
        dimensions=dimensions,
        processQualityAvg=process_quality_avg,
        outcomeQualityAvg=outcome_quality_avg,
        evidenceCount=evidence_count,
        confidencePct=confidence_pct,
        trend=trend,  # type: ignore[arg-type]
        weakestDimensionId=weakest_dimension_id,
        status=status,  # type: ignore[arg-type]
        simDay=sim_day,
        createdAt=_now_iso(),
    )


def record_agent_performance_review(
    existing: list[AgentPerformanceReview], review: AgentPerformanceReview, *, max_reviews: int = MAX_AGENT_PERFORMANCE_REVIEWS
) -> list[AgentPerformanceReview]:
    updated = [*existing, review]
    if len(updated) > max_reviews:
        del updated[: len(updated) - max_reviews]
    return updated


def latest_review_for_agent(reviews: list[AgentPerformanceReview], agent_id: AgentId) -> AgentPerformanceReview | None:
    return next((r for r in reversed(reviews) if r.agent_id == agent_id), None)


# CEO directive "Professional Quant Firm Phase 41-45," Feature 44 — the
# real, non-shuffled, chronological rule behind AgentReviewDataSplit
# (see that type's own docstring in app/schemas.py for the full
# preventive-labeling reasoning). Named windows mirror app/walk_
# forward.py's own window discipline, applied to agent-level review
# evidence instead of strategy-level backtest windows.
_LIVE_PAPER_WINDOW = 1
_TEST_WINDOW = 1
_VALIDATION_WINDOW = 2


def classify_review_data_splits(reviews_for_agent: list[AgentPerformanceReview]) -> list[AgentPerformanceReviewHistoryEntry]:
    """Real, deterministic, chronological data-split labeling over one
    agent's own review history — never randomly shuffled. Recomputed
    fresh from the full list every call rather than stored on the
    review itself, so a review's label correctly ages as later reviews
    accumulate (e.g. today's `live_paper` review becomes `test` the
    moment a newer review is generated next week). `reviews_for_agent`
    need not be pre-sorted; sorted here by `period_end_sim_day`
    ascending so "most recent" is unambiguous regardless of storage
    order. The single most recent review is `live_paper`; the review it
    superseded is `test` (the first genuinely held-out period); the
    next two are `validation`; everything older is `training`."""
    ordered = sorted(reviews_for_agent, key=lambda r: r.period_end_sim_day)
    total = len(ordered)
    entries: list[AgentPerformanceReviewHistoryEntry] = []
    for position, review in enumerate(ordered):
        age = total - 1 - position  # 0 = most recent
        split: AgentReviewDataSplit
        if age < _LIVE_PAPER_WINDOW:
            split = "live_paper"
        elif age < _LIVE_PAPER_WINDOW + _TEST_WINDOW:
            split = "test"
        elif age < _LIVE_PAPER_WINDOW + _TEST_WINDOW + _VALIDATION_WINDOW:
            split = "validation"
        else:
            split = "training"
        entries.append(AgentPerformanceReviewHistoryEntry(review=review, dataSplit=split))
    return entries
