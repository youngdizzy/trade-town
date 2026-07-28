"""WisdomManager — v0.7 Feature 30, the Reflection Chamber.

Generates a real ReflectionSession every in-game week and month, and a
real, never-profit-based Company Wisdom Score updated only when a
session is generated (see WisdomState's own docstring for why that's a
deliberate design choice, not a shortcut). Every field is built from
data this codebase already computes elsewhere for other real reasons —
DisciplineReview, CaseStudy, ReasoningChallenge, ResearchItem,
GatekeeperRejection, PaperTrade, MemoryRecord — never a fabricated
meeting transcript or invented statistic.

The brief's nine reflection questions map onto real signals as follows
(several deliberately reuse the same underlying number from opposite
ends, the same "strong factors vs weak factors from the same list"
convention app/discipline.py's own _post_decision_review already
established):

  What surprised us?              — the most recent DisciplineReview
                                     whose real score/outcome pairing
                                     was a genuine mismatch (a sound
                                     process that still lost, or a weak
                                     process that happened to win).
  What assumptions turned out to
  be wrong?                       — the most recent real
                                     "confirmation_bias" CaseStudy (a
                                     specific dissenting analyst was
                                     overridden and proven right).
  What patterns are repeating?    — the most common real CaseStudy
                                     category on record.
  What are we consistently doing
  well? / What should we
  continue doing?                 — the DisciplineFactor with the
                                     highest real average score across
                                     recent reviews (asked twice, once
                                     backward- and once forward-facing).
  Where are we becoming
  overconfident?                  — the real count of "overconfidence"
                                     CaseStudy entries on record.
  What knowledge are we still
  missing?                        — the DisciplineFactor with the
                                     lowest real average score.
  What should we stop doing?      — the same most-common CaseStudy
                                     category, forward-facing.
  What new questions should we
  investigate?                    — the most recent real
                                     ReasoningChallenge's category, or a
                                     real still-in-progress research item.

Two of the brief's cross-department examples name department roles this
codebase doesn't have as distinct entities ("Education turns it into a
lesson" — see app/education.py's own static curriculum, which has no
per-discovery lesson-generation capability; a distinct "Risk"
department already exists as Sentinel/Guardian). Cross-department
sharing here is represented honestly: real recent output from real
existing agents (Research → the latest completed ResearchItem's own
title/summary, News → the latest real NewsItem headline, Risk → the
latest real RiskWarning or GatekeeperRejection reason, Executive → the
latest real ExecutiveReview summary), not invented dialogue between
department roles that don't exist here.

Company Wisdom is an equal, unweighted mean of eight real, independent
factors — the same "plain mean, no hidden weighting" convention
app/company_score.py already established. Several factors (avoiding
repeated mistakes, following the Gatekeeper's own configured
principles) are realistically hard to max at the same time as the
others, which is what actually makes this "one of the hardest
progression systems to maximize," per the brief — not an artificial
gate.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from app.agents import all_agent_ids
from app.mistakes import CATEGORY_TITLES, INCOMPLETE_RESEARCH_THRESHOLD, OVERCONFIDENCE_THRESHOLD
from app.schemas import (
    CaseStudy,
    CaseStudyCategory,
    DisciplineReview,
    ExecutiveReview,
    GatekeeperRejection,
    MemoryRecord,
    NewsItem,
    PaperTrade,
    ReasoningChallenge,
    ReflectionCadence,
    ReflectionInsight,
    ReflectionQuestion,
    ReflectionSession,
    ResearchItem,
    RiskWarning,
    TimeState,
    WisdomFactor,
    WisdomFactorId,
    WisdomState,
    WisdomTier,
)

MAX_REFLECTION_SESSIONS = 80

_WISDOM_TIER_THRESHOLDS: tuple[tuple[float, WisdomTier, str], ...] = (
    (0.0, "young_company", "Young Company"),
    (30.0, "developing_judgment", "Developing Judgment"),
    (50.0, "institutional_memory", "Institutional Memory"),
    (70.0, "seasoned_wisdom", "Seasoned Wisdom"),
    (85.0, "enduring_wisdom", "Enduring Wisdom"),
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _tier_for_score(score: float) -> tuple[WisdomTier, str]:
    tier: WisdomTier = "young_company"
    label = "Young Company"
    for threshold, t, lbl in _WISDOM_TIER_THRESHOLDS:
        if score >= threshold:
            tier, label = t, lbl
    return tier, label


def _factor_scores(discipline_reviews: list[DisciplineReview], factor_id: str) -> list[float]:
    return [f.score for r in discipline_reviews for f in r.factors if f.id == factor_id]


def _strongest_and_weakest_factors(discipline_reviews: list[DisciplineReview]) -> tuple[tuple[str, float] | None, tuple[str, float] | None]:
    """Real average score per real DisciplineFactor name across every
    recent review — the same real per-factor breakdown discipline.py
    already computes, aggregated across the whole recent window rather
    than one review at a time."""
    if not discipline_reviews:
        return None, None
    totals: dict[str, list[float]] = {}
    for review in discipline_reviews:
        for factor in review.factors:
            totals.setdefault(factor.name, []).append(factor.score)
    averages = {name: sum(scores) / len(scores) for name, scores in totals.items()}
    if not averages:
        return None, None
    strongest = max(averages.items(), key=lambda kv: kv[1])
    weakest = min(averages.items(), key=lambda kv: kv[1])
    return strongest, weakest


def _most_common_category(case_studies: list[CaseStudy]) -> tuple[CaseStudyCategory, int] | None:
    if not case_studies:
        return None
    counts = Counter(c.category for c in case_studies)
    category, count = counts.most_common(1)[0]
    return category, count


def _questions(
    discipline_reviews: list[DisciplineReview],
    case_studies: list[CaseStudy],
    reasoning_challenges: list[ReasoningChallenge],
    research: list[ResearchItem],
) -> list[ReflectionQuestion]:
    mismatches = [r for r in discipline_reviews if (r.score >= 70 and r.outcome == "loss") or (r.score < 55 and r.outcome == "win")]
    surprise = mismatches[-1] if mismatches else None

    confirmation_bias_cases = [c for c in case_studies if c.category == "confirmation_bias"]
    wrong_assumption = confirmation_bias_cases[-1] if confirmation_bias_cases else None

    strongest, weakest = _strongest_and_weakest_factors(discipline_reviews)
    common = _most_common_category(case_studies)
    overconfident_count = sum(1 for c in case_studies if c.category == "overconfidence")

    latest_challenge = reasoning_challenges[-1] if reasoning_challenges else None
    stalled_research = next((r for r in research if r.status != "completed" and r.confidence < INCOMPLETE_RESEARCH_THRESHOLD), None)

    return [
        ReflectionQuestion(
            question="What surprised us?",
            answer=(
                f"{surprise.symbol}: a {surprise.tier} process still {'lost' if surprise.outcome == 'loss' else 'won'} "
                f"({surprise.trade_pnl_pct:+.1f}%) — {surprise.summary}"
                if surprise is not None
                else "No real mismatch between process and outcome this period — results have tracked the process."
            ),
        ),
        ReflectionQuestion(
            question="What assumptions turned out to be wrong?",
            answer=(
                f'On {wrong_assumption.symbol}, a dissenting analyst\'s overridden vote proved right — see the "{wrong_assumption.title}" case study.'
                if wrong_assumption is not None
                else "No dissenting analyst's overridden vote has been proven right yet."
            ),
        ),
        ReflectionQuestion(
            question="What patterns are repeating?",
            answer=(
                f'"{CATEGORY_TITLES[common[0]]}" has recurred {common[1]} time(s) in the Library of Mistakes — the most common real pattern on record.'
                if common is not None
                else "No repeated mistake pattern has emerged yet in the Library of Mistakes."
            ),
        ),
        ReflectionQuestion(
            question="What are we consistently doing well?",
            answer=(f"{strongest[0]} — averaging {strongest[1]:.0f}/100 across recent Discipline Reviews." if strongest is not None else "Not enough closed trades yet to identify a consistent strength."),
        ),
        ReflectionQuestion(
            question="Where are we becoming overconfident?",
            answer=(
                f"{overconfident_count} case stud(y/ies) in the Library of Mistakes trace back to overconfidence — decision confidence above {OVERCONFIDENCE_THRESHOLD:.0f}/100 that still lost."
                if overconfident_count
                else "No overconfidence pattern has been detected in the Library of Mistakes yet."
            ),
        ),
        ReflectionQuestion(
            question="What knowledge are we still missing?",
            answer=(f"{weakest[0]} — averaging only {weakest[1]:.0f}/100 across recent Discipline Reviews." if weakest is not None else "Not enough closed trades yet to identify a knowledge gap."),
        ),
        ReflectionQuestion(
            question="What should we continue doing?",
            answer=(f"Keep leaning on {strongest[0]} — it's the desk's most consistent real strength." if strongest is not None else "Too little history yet to recommend continuing a specific behavior."),
        ),
        ReflectionQuestion(
            question="What should we stop doing?",
            answer=(f'Stop repeating the conditions behind "{CATEGORY_TITLES[common[0]]}" — it is the most common real mistake on record.' if common is not None else "No repeated mistake pattern to stop yet."),
        ),
        ReflectionQuestion(
            question="What new questions should we investigate?",
            answer=(
                f'The Reasoning Lab\'s most recent "{latest_challenge.title}" challenge on {latest_challenge.symbol} — worth a follow-up pass.'
                if latest_challenge is not None
                else (f"{stalled_research.title} ({stalled_research.symbol or stalled_research.category}) remains low-confidence and worth another research pass." if stalled_research is not None else "No standout open question this period — the desk's current queue looks settled.")
            ),
        ),
    ]


def _insights(
    research: list[ResearchItem],
    news: list[NewsItem],
    risk_warnings: list[RiskWarning],
    gatekeeper_rejections: list[GatekeeperRejection],
    executive_reviews: list[ExecutiveReview],
) -> list[ReflectionInsight]:
    """The honest version of the brief's "departments share discoveries" —
    real recent output from real existing agents, never invented
    dialogue between department roles this codebase doesn't have."""
    insights: list[ReflectionInsight] = []

    completed_research = [r for r in research if r.status == "completed"]
    if completed_research:
        latest = completed_research[-1]
        insights.append(ReflectionInsight(agentId=latest.assigned_agent, insight=f"{latest.title}: {latest.summary}"))

    if news:
        scout_headline = news[-1]
        insights.append(ReflectionInsight(agentId="scout", insight=f"Historical context from the newsroom: {scout_headline.headline}"))

    if risk_warnings:
        latest_warning = risk_warnings[-1]
        insights.append(ReflectionInsight(agentId="sentinel", insight=f"Standing concern on {latest_warning.symbol}: {latest_warning.message}"))
    elif gatekeeper_rejections:
        latest_rejection = gatekeeper_rejections[-1]
        insights.append(ReflectionInsight(agentId="sentinel", insight=f"The Gatekeeper's most recent block, on {latest_rejection.symbol}, is worth revisiting: {'; '.join(latest_rejection.reasons)}"))

    if executive_reviews:
        latest_review = executive_reviews[-1]
        insights.append(ReflectionInsight(agentId="cio", insight=latest_review.summary))

    return insights


def _journal_fields(
    research: list[ResearchItem],
    discipline_reviews: list[DisciplineReview],
    case_studies: list[CaseStudy],
    reasoning_challenges: list[ReasoningChallenge],
    questions: list[ReflectionQuestion],
) -> tuple[list[str], list[str], list[str], list[str]]:
    completed_research = [r for r in research if r.status == "completed"]
    key_discoveries = [f"{r.title} ({r.symbol or r.category})" for r in completed_research[-3:]]

    if case_studies:
        lessons_learned = [c.lessons_learned for c in case_studies[-3:]]
    else:
        lessons_learned = [r.summary for r in discipline_reviews[-3:]]

    new_questions_answer = next(q.answer for q in questions if q.question == "What new questions should we investigate?")
    important_questions = [new_questions_answer]

    recommended_future_projects: list[str] = []
    _, weakest = _strongest_and_weakest_factors(discipline_reviews)
    if weakest is not None:
        recommended_future_projects.append(f"A focused push on {weakest[0]} — the desk's weakest real factor this period.")
    if reasoning_challenges:
        recommended_future_projects.append(f"Extend the Reasoning Lab's \"{reasoning_challenges[-1].title}\" line of thinking into a full research item.")
    if not recommended_future_projects:
        recommended_future_projects.append("No specific gap stands out yet — continue the current research cadence.")

    return key_discoveries, lessons_learned, important_questions, recommended_future_projects


def _learn_from_experience(discipline_reviews: list[DisciplineReview]) -> float:
    if len(discipline_reviews) < 4:
        return 30.0
    midpoint = len(discipline_reviews) // 2
    earlier_avg = sum(r.score for r in discipline_reviews[:midpoint]) / midpoint
    later_avg = sum(r.score for r in discipline_reviews[midpoint:]) / (len(discipline_reviews) - midpoint)
    return round(max(0.0, min(100.0, 50.0 + (later_avg - earlier_avg))), 1)


def _share_knowledge(memory: list[MemoryRecord]) -> float:
    mentorship_count = sum(1 for m in memory if m.category == "mentorship")
    return round(min(100.0, mentorship_count * 15.0), 1)


def _follow_principles(trade_history: list[PaperTrade], gatekeeper_rejections: list[GatekeeperRejection]) -> float:
    total = len(trade_history) + len(gatekeeper_rejections)
    if total == 0:
        return 50.0
    return round(len(trade_history) / total * 100.0, 1)


def _improve_communication(discipline_reviews: list[DisciplineReview]) -> float:
    scores = _factor_scores(discipline_reviews, "cross_examination")
    if not scores:
        return 30.0
    return round(sum(scores) / len(scores), 1)


def _document_lessons(discipline_reviews: list[DisciplineReview], case_studies: list[CaseStudy], reasoning_challenges: list[ReasoningChallenge]) -> float:
    total = len(discipline_reviews) + len(case_studies) + len(reasoning_challenges)
    return round(min(100.0, total * 1.0), 1)


def _avoid_repeating_mistakes(case_studies: list[CaseStudy]) -> float:
    if not case_studies:
        return 50.0
    counts = Counter(c.category for c in case_studies)
    dominant_share = max(counts.values()) / len(case_studies)
    return round(max(0.0, 100.0 - dominant_share * 100.0), 1)


def _complete_research(research: list[ResearchItem]) -> float:
    if not research:
        return 50.0
    completed = sum(1 for r in research if r.status == "completed")
    return round(completed / len(research) * 100.0, 1)


def _support_collaboration(discipline_reviews: list[DisciplineReview]) -> float:
    scores = _factor_scores(discipline_reviews, "viewpoint_diversity")
    if not scores:
        return 30.0
    return round(sum(scores) / len(scores), 1)


def compute_wisdom_score(
    *,
    discipline_reviews: list[DisciplineReview],
    case_studies: list[CaseStudy],
    reasoning_challenges: list[ReasoningChallenge],
    research: list[ResearchItem],
    trade_history: list[PaperTrade],
    gatekeeper_rejections: list[GatekeeperRejection],
    memory: list[MemoryRecord],
) -> WisdomState:
    readings: list[tuple[WisdomFactorId, str, float, str]] = [
        ("learn_from_experience", "Learning From Experience", _learn_from_experience(discipline_reviews), "Whether recent Discipline Scores are trending up against the desk's own earlier record."),
        ("share_knowledge", "Sharing Knowledge", _share_knowledge(memory), "Real mentorship/teaching sessions logged in Company Memory."),
        ("follow_principles", "Following Principles", _follow_principles(trade_history, gatekeeper_rejections), "Share of trades that cleared the Trade Gatekeeper's real configured limits without a block."),
        ("improve_communication", "Improving Communication", _improve_communication(discipline_reviews), "Average real Cross-Examination factor across recent Discipline Reviews."),
        ("document_lessons", "Documenting Lessons", _document_lessons(discipline_reviews, case_studies, reasoning_challenges), "Real Discipline Reviews, Case Studies, and Reasoning Challenges filed to date."),
        ("avoid_repeating_mistakes", "Avoiding Repeated Mistakes", _avoid_repeating_mistakes(case_studies), "How diversified the Library of Mistakes' real categories are, rather than one repeating pattern."),
        ("complete_research", "Completing Research", _complete_research(research), "Share of the research queue that has actually reached completed status."),
        ("support_collaboration", "Supporting Collaboration", _support_collaboration(discipline_reviews), "Average real Viewpoint Diversity factor across recent Discipline Reviews."),
    ]
    factors = [WisdomFactor(id=fid, name=name, score=score, weight=round(1.0 / len(readings), 3), detail=detail) for fid, name, score, detail in readings]
    total = sum(f.score for f in factors) / len(factors)
    tier, tier_label = _tier_for_score(total)
    return WisdomState(
        score=round(total, 1),
        tier=tier,
        tierLabel=tier_label,
        factors=factors,
        updatedAt=_now_iso(),
    )


def generate_reflection_session(
    cadence: ReflectionCadence,
    *,
    discipline_reviews: list[DisciplineReview],
    case_studies: list[CaseStudy],
    reasoning_challenges: list[ReasoningChallenge],
    research: list[ResearchItem],
    news: list[NewsItem],
    risk_warnings: list[RiskWarning],
    gatekeeper_rejections: list[GatekeeperRejection],
    executive_reviews: list[ExecutiveReview],
    wisdom_state: WisdomState,
    new_time: TimeState,
) -> ReflectionSession:
    questions = _questions(discipline_reviews, case_studies, reasoning_challenges, research)
    insights = _insights(research, news, risk_warnings, gatekeeper_rejections, executive_reviews)
    key_discoveries, lessons_learned, important_questions, recommended_future_projects = _journal_fields(research, discipline_reviews, case_studies, reasoning_challenges, questions)
    return ReflectionSession(
        id=f"reflection-{cadence}-{new_time.day}-{new_time.hour}-{new_time.minute}",
        cadence=cadence,
        attendees=list(all_agent_ids()),
        questions=questions,
        insights=insights,
        keyDiscoveries=key_discoveries,
        lessonsLearned=lessons_learned,
        importantQuestions=important_questions,
        recommendedFutureProjects=recommended_future_projects,
        wisdomScore=wisdom_state.score,
        simDay=new_time.day,
        createdAt=_now_iso(),
    )


def record_session(sessions: list[ReflectionSession], session: ReflectionSession) -> list[ReflectionSession]:
    updated = [*sessions, session]
    if len(updated) > MAX_REFLECTION_SESSIONS:
        del updated[: len(updated) - MAX_REFLECTION_SESSIONS]
    return updated
