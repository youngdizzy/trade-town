"""Academy + Skill Progression — CEO directive "Features 26-30: Agent
Intelligence, Learning & Institutional Memory System," Feature 28 (the
third stage of the 26->27->28->29->30 learning loop; per the directive's
own staging rule, this does not begin until Feature 27 is tested and
integrated, and Feature 29 does not begin until this one is).

Research finding (recorded here per the directive's "document what was
found before coding" rule): this codebase already has two real, adjacent
systems, neither of which is a multi-domain per-agent SKILL system.
app/academy.py is a single-scalar knowledge-points/tier ladder — one
`points` number and one fixed `branch` string per agent, no domain
breakdown. app/foundational_mentors.py is a curriculum/certification
delivery engine — named-educator "tracks" (TJR, Mark Douglas, Linda
Raschke, Market Intelligence Department, ...) with real lessons, quizzes,
and a genuine active/suspended/revoked certification lifecycle
(CertificationRecord) — but its tracks are curricula, not the 11 skill
domains this feature's brief names, and graduating a track produces a
pass/fail certification, never a 0-100 skill score with real history.
No `Skill*` schema existed anywhere before this module (confirmed by
direct grep). This module is a third sibling, not a merge into either:
it defines the skill-domain taxonomy the brief actually asked for, reuses
app/foundational_mentors.py's existing certification lifecycle as the
real regression/reassessment mechanic instead of inventing a second one,
and reads app/performance_review.py's `weakest_dimension_id`/evidence as
its own real training-recommendation trigger — exactly the "Performance
Review flags a weak dimension -> Academy recommends training" closed
loop the CEO's own worked example asked for.

Each of the 11 domains named in the brief (market structure, risk
management, quant research, technical/fundamental analysis, execution,
statistical reasoning, regime detection, prediction calibration,
communication, collaboration, research quality) was checked individually
against real, already-computed per-agent evidence:

  MEASURABLE (5) — real, already-computed per-agent evidence exists:
    risk_management        -> app/performance_review.py's _risk_discipline()
                               (Position Sizing Discipline / Patience
                               Discipline Factors), reused directly, not
                               recomputed.
    research_quality        -> app/performance_review.py's _decision_accuracy()
                               (app/analytics.py's research_accuracy()),
                               reused directly.
    prediction_calibration   -> app/performance_review.py's _calibration()
                               (app/analytics.py's confidence_accuracy()),
                               reused directly — the literal name in the
                               brief matches a real dimension already.
    collaboration            -> app/performance_review.py's _collaboration()
                               (Reasoning Lab contributions + Reflection
                               Chamber insights), reused directly.
    statistical_reasoning    -> PARTIAL evidence, disclosed as a proxy:
                               this codebase has no dedicated statistics-
                               methodology signal, so this domain reuses
                               the same Assumptions Challenged /
                               Cross-Examination Discipline Factor
                               average app/mentor.py's ThinkingProfile
                               "Reasoning" trait already computes
                               (app/mentor.py's `_factor_average()`) —
                               the same real numbers, not a new formula.

  NOT_TRACKABLE_YET (6) — no per-agent attribution mechanism exists in
  this codebase today; `value` is permanently `None` with a stated,
  domain-specific structural reason rather than an occupation-label
  guess (see `_NOT_TRACKABLE_REASON` below for each domain's exact
  reasoning, cited against the real module that computes the company-
  level version of that signal):
    market_structure, quant_research, technical_fundamental_analysis,
    execution, regime_detection, communication.

Two of the 11 (process_quality/learning_trend/recurring_mistakes/
pnl_attribution's own kind of "meta" dimensions have no 1:1 skill-domain
analog either) are intentionally not force-mapped to anything — see
`_DIMENSION_TO_SKILL_DOMAIN` below, which only maps the 4 Performance
Review dimensions that really do correspond to one of the 5 measurable
skill domains above.

Trend (`SkillAssessment.trend`) is this module's own real
improve/stagnate/regress read, computed by comparing this period's real
value against the agent's own previous real assessment of the SAME
domain — never a different domain, never a fabricated baseline. A domain
that's currently `None` (either NOT_ENOUGH_EVIDENCE or
NOT_TRACKABLE_YET) is always `"not_enough_history"`; there is nothing
honest to compare.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.mentor import _factor_average
from app.performance_review import TREND_CHANGE_THRESHOLD_PCT, _calibration, _collaboration, _decision_accuracy, _risk_discipline
from app.schemas import (
    AgentId,
    AgentPerformanceReview,
    AgentSkillProfile,
    DisciplineReview,
    FoundationalMentorId,
    FoundationalMentorState,
    PaperTrade,
    PerformanceDimensionId,
    ReasoningChallenge,
    ReflectionSession,
    ResearchItem,
    SkillAssessment,
    SkillDomainId,
)

MAX_AGENT_SKILL_PROFILES = 150

ALL_SKILL_DOMAIN_IDS: tuple[SkillDomainId, ...] = (
    "market_structure",
    "risk_management",
    "quant_research",
    "technical_fundamental_analysis",
    "execution",
    "statistical_reasoning",
    "regime_detection",
    "prediction_calibration",
    "communication",
    "collaboration",
    "research_quality",
)

_SKILL_LABEL: dict[SkillDomainId, str] = {
    "market_structure": "Market Structure",
    "risk_management": "Risk Management",
    "quant_research": "Quant Research",
    "technical_fundamental_analysis": "Technical / Fundamental Analysis",
    "execution": "Execution",
    "statistical_reasoning": "Statistical & Critical Reasoning",
    "regime_detection": "Regime Detection",
    "prediction_calibration": "Prediction Calibration",
    "communication": "Communication",
    "collaboration": "Collaboration",
    "research_quality": "Research Quality",
}

# The 6 domains this codebase cannot honestly measure per-agent today —
# each reason cites the real module that computes the COMPANY-level
# version of this signal and explains exactly why it doesn't reduce to a
# per-agent number, rather than a generic "not implemented."
_NOT_TRACKABLE_REASON: dict[SkillDomainId, str] = {
    "market_structure": "app/market_intelligence.py computes real market-structure reads, but only company-wide — no mechanism attributes a specific structure call to one agent's individual judgment.",
    "quant_research": "app/model_validation.py's Model Validator (Meridian/CIO) is a company/strategy-level governance seat, not a per-agent quant-skill signal, and this directive's governance rule forbids repurposing it into one; no per-agent quant-research score exists distinct from Research Quality.",
    "technical_fundamental_analysis": "No mechanism records which analysis type (technical vs. fundamental) a given ResearchItem exercised or grades it — occupation titles like Echo's 'Technical Analyst' are labels, not measured evidence.",
    "execution": "Trade execution happens at the company/broker level (app/broker.py, app/portfolio.py), never attributed to any individual supporting agent.",
    "regime_detection": "app/market_intelligence.py's regime classifier and its own Learning Loop grade yesterday's regime read against the outcome, but only at the company level — no per-agent regime-call accuracy record exists anywhere.",
    "communication": "No per-agent, per-period discriminating communication signal exists in this codebase — app/mentor.py's own ThinkingProfile explicitly reached the same conclusion and cut a Communication trait for the same reason.",
}

# Only the 4 real Performance Review dimensions that correspond 1:1 to a
# measurable skill domain above. process_quality/learning_trend/
# recurring_mistakes/pnl_attribution are composite or differently-scaled
# meta-signals with no single matching domain and are deliberately left
# unmapped rather than force-fit.
_DIMENSION_TO_SKILL_DOMAIN: dict[PerformanceDimensionId, SkillDomainId] = {
    "risk_discipline": "risk_management",
    "decision_accuracy": "research_quality",
    "calibration": "prediction_calibration",
    "collaboration": "collaboration",
}

# Real, content-backed Foundational Mentor tracks only. al_brooks/
# tom_hougaard/mike_bellafiore intentionally have zero real lesson
# content yet (see foundational_mentors.py's `_LESSON_SPECS_BY_MENTOR`),
# so recommending them would point the CEO at an empty track — never
# done here. Each mapped track below was chosen because it has a real,
# already-written lesson whose id or the track's own real `focus_areas`
# directly names this skill domain (cited in each comment), never an
# arbitrary pick. `collaboration` has no real match: Mike Bellafiore's
# "Trading Team Development" focus area exists but has zero written
# lessons, so it is deliberately left unmapped rather than recommending
# an empty track.
SKILL_DOMAIN_RECOMMENDED_MENTOR: dict[SkillDomainId, FoundationalMentorId] = {
    # Real lesson "tjr-risk-management"; "Risk Management" is one of TJR's own real focus_areas.
    "risk_management": "tjr",
    # Real lesson "md-probability"; "Probability"/"Confidence" are Mark Douglas's own real focus_areas — the direct match for calibration.
    "prediction_calibration": "mark_douglas",
    # Real lesson "mi-probability" ("Probability Thinking" focus area) — the closest real content to a statistics-methodology track.
    "statistical_reasoning": "market_intelligence",
    # Real lessons "lr-gatekeeper-checklist"/"lr-position-sizing"; "Professional Process"/"Preparation" are Linda Raschke's own real focus_areas — the closest real content to research preparation/quality.
    "research_quality": "linda_raschke",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _trend_for(domain_id: SkillDomainId, current_value: float | None, previous_profile: AgentSkillProfile | None) -> str:
    if current_value is None or previous_profile is None:
        return "not_enough_history"
    previous = next((a for a in previous_profile.assessments if a.domain_id == domain_id), None)
    if previous is None or previous.value is None:
        return "not_enough_history"
    diff = current_value - previous.value
    if diff >= TREND_CHANGE_THRESHOLD_PCT:
        return "improving"
    if diff <= -TREND_CHANGE_THRESHOLD_PCT:
        return "regressed"
    return "stagnant"


def _statistical_reasoning(reviews_in_period: list[DisciplineReview]) -> tuple[float | None, int, str]:
    assumptions_avg = _factor_average(reviews_in_period, "assumptions_challenged")
    cross_exam_avg = _factor_average(reviews_in_period, "cross_examination")
    if assumptions_avg is None or cross_exam_avg is None:
        return None, 0, "No Discipline Reviews attended this period."
    value = round((assumptions_avg + cross_exam_avg) / 2, 1)
    evidence = (
        f"Averaged {value:.1f}/100 across the real Assumptions Challenged / Cross-Examination Discipline Factors in "
        f"{len(reviews_in_period)} review(s) this period — a disclosed proxy (this codebase has no dedicated "
        "statistics-methodology signal), the same real numbers app/mentor.py's ThinkingProfile 'Reasoning' trait already uses."
    )
    return value, len(reviews_in_period), evidence


def _training_recommendation(
    agent_id: AgentId, latest_review: AgentPerformanceReview | None, foundational_mentor_state: FoundationalMentorState
) -> tuple[SkillDomainId | None, FoundationalMentorId | None, str | None]:
    if latest_review is None or latest_review.weakest_dimension_id is None:
        return None, None, None
    domain_id = _DIMENSION_TO_SKILL_DOMAIN.get(latest_review.weakest_dimension_id)
    if domain_id is None:
        return None, None, None
    mentor_id = SKILL_DOMAIN_RECOMMENDED_MENTOR.get(domain_id)
    if mentor_id is None:
        return None, None, None
    progress = foundational_mentor_state.progress.get(agent_id, {}).get(mentor_id)
    if progress is not None and progress.graduation_status == "graduated":
        return None, None, None
    weakest_dim = next((d for d in latest_review.dimensions if d.id == latest_review.weakest_dimension_id), None)
    evidence_note = f" ({weakest_dim.evidence})" if weakest_dim is not None else ""
    label = weakest_dim.label if weakest_dim is not None else latest_review.weakest_dimension_id
    reason = (
        f"Agent Performance Review flagged {label} as the weakest real dimension for the period ending sim day "
        f"{latest_review.period_end_sim_day}{evidence_note} — the {mentor_id} Foundational Mentor track is the real, "
        "content-backed program matching this skill domain."
    )
    return domain_id, mentor_id, reason


def compute_agent_skill_profile(
    agent_id: AgentId,
    *,
    discipline_reviews: list[DisciplineReview],
    research: list[ResearchItem],
    trades: list[PaperTrade],
    reasoning_challenges: list[ReasoningChallenge],
    reflection_sessions: list[ReflectionSession],
    period_start_sim_day: int,
    period_end_sim_day: int,
    sim_day: int,
    previous_profile: AgentSkillProfile | None,
    latest_review: AgentPerformanceReview | None,
    foundational_mentor_state: FoundationalMentorState,
) -> AgentSkillProfile:
    """One real skill snapshot for one agent over one real period. Every
    measurable domain reuses an existing real computation from
    app/performance_review.py or app/mentor.py — nothing here recomputes
    an existing formula a second, possibly-drifting way. See module
    docstring for exactly which of the 11 named domains is measurable
    today and which is honestly NOT_TRACKABLE_YET."""
    reviews_in_period = [r for r in discipline_reviews if agent_id in r.attendees and period_start_sim_day <= r.sim_day <= period_end_sim_day]
    trades_in_period = [t for t in trades if period_start_sim_day <= t.closed_sim_minutes // 1440 <= period_end_sim_day]
    reasoning_in_period = [c for c in reasoning_challenges if period_start_sim_day <= c.sim_day <= period_end_sim_day]
    reflection_in_period = [s for s in reflection_sessions if period_start_sim_day <= s.sim_day <= period_end_sim_day]

    risk_dim = _risk_discipline(reviews_in_period)
    accuracy_dim = _decision_accuracy(agent_id, research)
    calibration_dim = _calibration(agent_id, trades_in_period)
    collaboration_dim = _collaboration(agent_id, reasoning_in_period, reflection_in_period)
    stat_value, stat_sample, stat_evidence = _statistical_reasoning(reviews_in_period)

    measurable: dict[SkillDomainId, tuple[float | None, int, str]] = {
        "risk_management": (risk_dim.value, risk_dim.sample_size, risk_dim.evidence),
        "research_quality": (accuracy_dim.value, accuracy_dim.sample_size, accuracy_dim.evidence),
        "prediction_calibration": (calibration_dim.value, calibration_dim.sample_size, calibration_dim.evidence),
        "collaboration": (collaboration_dim.value, collaboration_dim.sample_size, collaboration_dim.evidence),
        "statistical_reasoning": (stat_value, stat_sample, stat_evidence),
    }

    assessments: list[SkillAssessment] = []
    for domain_id in ALL_SKILL_DOMAIN_IDS:
        if domain_id in measurable:
            value, sample_size, evidence = measurable[domain_id]
        else:
            value, sample_size, evidence = None, 0, _NOT_TRACKABLE_REASON[domain_id]
        trend = _trend_for(domain_id, value, previous_profile)
        assessments.append(
            SkillAssessment(
                domainId=domain_id,
                label=_SKILL_LABEL[domain_id],
                value=value,
                sampleSize=sample_size,
                evidence=evidence,
                trend=trend,  # type: ignore[arg-type]
            )
        )

    recommended_domain_id, recommended_mentor_id, recommendation_reason = _training_recommendation(agent_id, latest_review, foundational_mentor_state)

    return AgentSkillProfile(
        id=f"skillprofile-{agent_id}-{period_end_sim_day}",
        agentId=agent_id,
        periodStartSimDay=period_start_sim_day,
        periodEndSimDay=period_end_sim_day,
        assessments=assessments,
        recommendedDomainId=recommended_domain_id,
        recommendedMentorId=recommended_mentor_id,
        recommendationReason=recommendation_reason,
        simDay=sim_day,
        createdAt=_now_iso(),
    )


def record_agent_skill_profile(
    existing: list[AgentSkillProfile], profile: AgentSkillProfile, *, max_profiles: int = MAX_AGENT_SKILL_PROFILES
) -> list[AgentSkillProfile]:
    updated = [*existing, profile]
    if len(updated) > max_profiles:
        del updated[: len(updated) - max_profiles]
    return updated


def latest_skill_profile_for_agent(profiles: list[AgentSkillProfile], agent_id: AgentId) -> AgentSkillProfile | None:
    return next((p for p in reversed(profiles) if p.agent_id == agent_id), None)
