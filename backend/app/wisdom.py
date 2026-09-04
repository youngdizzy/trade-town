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
from app.audit_log import compute_compliance_score
from app.mistakes import CATEGORY_TITLES as MISTAKE_CATEGORY_TITLES
from app.mistakes import INCOMPLETE_RESEARCH_THRESHOLD, OVERCONFIDENCE_THRESHOLD
from app.successes import CATEGORY_TITLES as SUCCESS_CATEGORY_TITLES
from app.schemas import (
    AuditEntry,
    CaseStudy,
    CaseStudyCategory,
    CeoDecisionRecord,
    Debate,
    DisciplineReview,
    ExecutiveReview,
    GatekeeperRejection,
    InstitutionalMemoryEntry,
    KnowledgeEvent,
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
    TradeDecision,
    WisdomFactor,
    WisdomFactorId,
    WisdomState,
    WisdomTier,
)

MAX_REFLECTION_SESSIONS = 80

# case_studies (app/mistakes.py's record_case_studies + app/successes.py's
# record_success_studies) is one shared, mixed list — a real CaseStudy's
# category can be any of mistakes.py's six or successes.py's three. Bug
# fix: _most_common_category() below scans that full mixed list, so its
# title lookup must cover both, not just the mistake-only dict (a save
# whose most common real category happened to be a success one — e.g.
# "disciplined_process" — crashed this module's weekly/monthly tick with
# a KeyError otherwise).
_CATEGORY_TITLES: dict[CaseStudyCategory, str] = {**MISTAKE_CATEGORY_TITLES, **SUCCESS_CATEGORY_TITLES}

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
                f'"{_CATEGORY_TITLES[common[0]]}" has recurred {common[1]} time(s) in the Library of Mistakes — the most common real pattern on record.'
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
            answer=(f'Stop repeating the conditions behind "{_CATEGORY_TITLES[common[0]]}" — it is the most common real mistake on record.' if common is not None else "No repeated mistake pattern to stop yet."),
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


def _learn_from_experience(discipline_reviews: list[DisciplineReview], decisions: list[TradeDecision]) -> float:
    """"TradeTown — Learning Organization 1.0" — the real DisciplineReview
    trend needs a real closed trade to exist at all (DisciplineReview is
    only ever built post-close), so it stays the primary read once there
    are enough (unchanged formula/threshold). Below that, this falls
    back to the exact same trend-of-a-real-process-quality-score shape
    applied to `TradeDecision.decision_grade_score` — a real, disclosed,
    decision-TIME score (app/executive.py's compute_decision_grade: 50%
    Decision Confidence Engine, 25% analyst agreement, 25% Gatekeeper
    approval) set the moment the CEO resolves a proposal, never waiting
    for that trade to eventually close. Not the same measurement as the
    real DisciplineReview trend — disclosed here, not conflated — but a
    real answer to the same question ("is the desk's own process
    trending better over time") that doesn't require a closed trade to
    exist yet."""
    if len(discipline_reviews) >= 4:
        midpoint = len(discipline_reviews) // 2
        earlier_avg = sum(r.score for r in discipline_reviews[:midpoint]) / midpoint
        later_avg = sum(r.score for r in discipline_reviews[midpoint:]) / (len(discipline_reviews) - midpoint)
        return round(max(0.0, min(100.0, 50.0 + (later_avg - earlier_avg))), 1)
    graded = [d.decision_grade_score for d in decisions if d.decision_grade_score is not None]
    if len(graded) < 4:
        return 30.0
    midpoint = len(graded) // 2
    earlier_avg = sum(graded[:midpoint]) / midpoint
    later_avg = sum(graded[midpoint:]) / (len(graded) - midpoint)
    return round(max(0.0, min(100.0, 50.0 + (later_avg - earlier_avg))), 1)


def _share_knowledge(memory: list[MemoryRecord], knowledge_events: list[KnowledgeEvent]) -> float:
    """"TradeTown — Learning Organization 1.0" broadens this beyond
    mentorship alone (real, but gated behind a >12-point knowledge-gap
    trigger — see app/academy.py's MENTORSHIP_GAP_THRESHOLD, rare in
    practice) to also count real lesson_shared KnowledgeEvents — the
    same kind of act (this company's own knowledge actually distributed
    to a named agent), at the same disclosed per-event weight, just
    routed through app/knowledge_sharing.py instead of Academy
    mentorship. Never double-counts: knowledge_received (one per
    recipient of the same lesson_shared act) deliberately isn't counted
    here, so one popular lesson isn't worth more than one mentorship
    session."""
    mentorship_count = sum(1 for m in memory if m.category == "mentorship")
    lesson_shared_count = sum(1 for e in knowledge_events if e.type == "lesson_shared")
    return round(min(100.0, (mentorship_count + lesson_shared_count) * 15.0), 1)


def _follow_principles(
    trade_history: list[PaperTrade], gatekeeper_rejections: list[GatekeeperRejection], audit_entries: list[AuditEntry]
) -> float:
    """"TradeTown — Learning Organization 1.0" replaces the bare 50.0
    default (which fires whenever no trade has cleared or been blocked
    by the Gatekeeper yet — true of every real save with 0 closed
    trades) with app/audit_log.py's own real, already-computed
    compute_compliance_score() — a real count over the real Audit Log
    rather than an invented placeholder. Once real trade/rejection
    history exists, the original real ratio takes over unchanged."""
    total = len(trade_history) + len(gatekeeper_rejections)
    if total == 0:
        return compute_compliance_score(audit_entries)
    return round(len(trade_history) / total * 100.0, 1)


def _decision_viewpoint_and_cross_exam_scores(
    decisions: list[TradeDecision],
    ceo_decisions: list[CeoDecisionRecord],
    debates: list[Debate],
) -> tuple[list[float], list[float]]:
    """"TradeTown — Learning Organization 1.0" — real, decision-TIME
    analogues of app/discipline.py's own viewpoint_diversity/cross_
    examination DisciplineFactor formulas, reused verbatim (same
    thresholds, same tiers), just read the moment the CEO resolves a
    proposal (buy/sell/wait — TradeDecision/CeoDecisionRecord are both
    built then) instead of waiting for that trade to eventually close
    and get a DisciplineReview. Joins each real TradeDecision to its own
    real CeoDecisionRecord (matching id/decisionId) for the real
    proposal_id, then to the real Debate with that same proposal_id, if
    one exists — the exact same real signals compute_discipline_score()
    reads, never a second, differently-shaped proxy."""
    proposal_id_by_decision_id = {cd.decision_id: cd.proposal_id for cd in ceo_decisions if cd.decision_id is not None}
    turn_count_by_proposal_id = {d.proposal_id: len(d.turns) for d in debates}
    viewpoint_scores: list[float] = []
    cross_exam_scores: list[float] = []
    for decision in decisions:
        distinct_choices = len({v.choice for v in decision.votes}) if decision.votes else 1
        viewpoint_scores.append(100.0 if distinct_choices >= 3 else 65.0 if distinct_choices == 2 else 35.0)

        proposal_id = proposal_id_by_decision_id.get(decision.id)
        analyst_count = len(decision.votes) or 6
        turn_count = turn_count_by_proposal_id.get(proposal_id) if proposal_id is not None else None
        if turn_count is None:
            cross_exam_scores.append(0.0)
        elif turn_count <= analyst_count:
            cross_exam_scores.append(30.0)
        else:
            cross_exam_scores.append(100.0)
    return viewpoint_scores, cross_exam_scores


def _improve_communication(discipline_reviews: list[DisciplineReview], decision_cross_exam_scores: list[float]) -> float:
    """"TradeTown — Learning Organization 1.0" — the real DisciplineReview
    average stays primary once real closed-trade reviews exist
    (unchanged formula). Below that, falls back to the real decision-
    time cross-examination analogue (see
    _decision_viewpoint_and_cross_exam_scores()) instead of the bare
    30.0 default."""
    scores = _factor_scores(discipline_reviews, "cross_examination")
    if scores:
        return round(sum(scores) / len(scores), 1)
    if not decision_cross_exam_scores:
        return 30.0
    return round(sum(decision_cross_exam_scores) / len(decision_cross_exam_scores), 1)


def _document_lessons(
    discipline_reviews: list[DisciplineReview],
    case_studies: list[CaseStudy],
    reasoning_challenges: list[ReasoningChallenge],
    institutional_memory: list[InstitutionalMemoryEntry],
) -> float:
    """"TradeTown — Learning Organization 1.0" extends the same real,
    uncapped-weight raw count (unchanged: 1.0 per item, capped at 100)
    to also include real InstitutionalMemoryEntry rows that actually
    carry a documented `lesson` (many entries honestly don't — see that
    schema's own docstring). Unlike DisciplineReview/CaseStudy, several
    institutional-memory sources (risk_event, market_regime_shift,
    research_lesson, model_validation) are promoted independent of any
    trade ever closing, so this factor is no longer entirely gated
    behind trade-closure the way the original three counts alone were."""
    documented_lessons = sum(1 for entry in institutional_memory if entry.lesson is not None)
    total = len(discipline_reviews) + len(case_studies) + len(reasoning_challenges) + documented_lessons
    return round(min(100.0, total * 1.0), 1)


def _avoid_repeating_mistakes(
    case_studies: list[CaseStudy],
    knowledge_events: list[KnowledgeEvent],
    institutional_memory: list[InstitutionalMemoryEntry],
) -> float:
    """"TradeTown — Learning Organization 1.0" replaces the bare 50.0
    default (which fires whenever no case study exists yet — true of
    every real save with 0 closed trades) with a real, disclosed check:
    a lesson_confirmed KnowledgeEvent whose linked institutional-memory
    entry is itself a mistake/risk-pattern source (behavioral_mistake,
    failure_classification, risk_event) means new real evidence just
    corroborated a STANDING mistake-or-risk lesson — i.e. the same real
    pattern recurring, which is exactly what this factor measures. No
    real signal exists yet to detect the mistake NOT repeating in the
    absence of any case study, so a clean record with zero such
    confirmations still reads as the same disclosed 50.0 baseline as
    before, not an invented high score. Once real case studies exist,
    the original real category-diversity formula takes over unchanged."""
    if not case_studies:
        mistake_pattern_ids = {
            entry.id for entry in institutional_memory if entry.source in ("behavioral_mistake", "failure_classification", "risk_event")
        }
        repeat_confirmations = sum(1 for e in knowledge_events if e.type == "lesson_confirmed" and e.lesson_id in mistake_pattern_ids)
        if repeat_confirmations == 0:
            return 50.0
        return round(max(0.0, 50.0 - repeat_confirmations * 10.0), 1)
    counts = Counter(c.category for c in case_studies)
    dominant_share = max(counts.values()) / len(case_studies)
    return round(max(0.0, 100.0 - dominant_share * 100.0), 1)


def _complete_research(research: list[ResearchItem]) -> float:
    if not research:
        return 50.0
    completed = sum(1 for r in research if r.status == "completed")
    return round(completed / len(research) * 100.0, 1)


def _support_collaboration(
    discipline_reviews: list[DisciplineReview],
    collaboration_case_score: float | None,
    decision_viewpoint_scores: list[float],
) -> float:
    """"TradeTown — Department Debate & Collaboration Intelligence 1.0"
    layered this on top of "Learning Organization 1.0"'s own earlier
    fallback (never replacing it, since analyst-vote viewpoint diversity
    is still real evidence when nothing richer exists yet):

    1. The real DisciplineReview average stays primary, unchanged, once
       real closed-trade reviews exist.
    2. Below that, the real department-level collaboration-case score
       (app/collaboration_intelligence.py's `average_collaboration_
       case_score()` — real cross-department stance diversity + real
       evidence-reuse, over already-permanent ExecutiveMeetingLogEntry/
       ChallengeReport data) is a strictly more apt "is the company
       collaborating" signal than analyst-vote diversity, and is
       available at the exact same real gate (a resolved decision) — so
       it's tried next.
    3. Only when NEITHER real signal exists yet does this fall further
       back to "Learning Organization 1.0"'s original decision-time
       analyst-vote analogue, then finally the disclosed 30.0 baseline."""
    scores = _factor_scores(discipline_reviews, "viewpoint_diversity")
    if scores:
        return round(sum(scores) / len(scores), 1)
    if collaboration_case_score is not None:
        return collaboration_case_score
    if not decision_viewpoint_scores:
        return 30.0
    return round(sum(decision_viewpoint_scores) / len(decision_viewpoint_scores), 1)


def compute_wisdom_score(
    *,
    discipline_reviews: list[DisciplineReview],
    case_studies: list[CaseStudy],
    reasoning_challenges: list[ReasoningChallenge],
    research: list[ResearchItem],
    trade_history: list[PaperTrade],
    gatekeeper_rejections: list[GatekeeperRejection],
    memory: list[MemoryRecord],
    institutional_memory: list[InstitutionalMemoryEntry],
    knowledge_events: list[KnowledgeEvent],
    audit_entries: list[AuditEntry],
    decisions: list[TradeDecision],
    ceo_decisions: list[CeoDecisionRecord],
    debates: list[Debate],
    collaboration_case_score: float | None,
) -> WisdomState:
    """"TradeTown — Learning Organization 1.0" added `institutional_
    memory`/`knowledge_events`/`audit_entries` (real evidence from
    app/institutional_memory.py, app/knowledge_sharing.py, and
    app/audit_log.py) so share_knowledge/document_lessons/avoid_
    repeating_mistakes/follow_principles draw on real evidence that
    doesn't require a trade to have closed yet; then `decisions`/
    `ceo_decisions`/`debates` (real evidence from app/executive.py and
    app/debate.py, already permanent and built the moment the CEO
    resolves a proposal, never gated behind that trade eventually
    closing) so learn_from_experience/improve_communication/support_
    collaboration get the same real, disclosed treatment. "TradeTown —
    Department Debate & Collaboration Intelligence 1.0" then added
    `collaboration_case_score` — app/collaboration_intelligence.py's
    real, department-level collaboration-case average (computed by the
    caller from `ceo_decisions`'/`decisions`' own real `executive_
    meeting_log`/`challenge_reports`, never recomputed twice) — as a
    richer, more apt fallback for support_collaboration specifically,
    layered ABOVE (never replacing) the decision-time analyst-vote
    fallback the prior milestone already built. See each function's own
    docstring for exactly which real signal backs it, and CHANGELOG.md
    for why `complete_research` is the one factor with no real trade-
    closure-gating problem to fix in the first place (it already reads
    a real completed/total ratio with no data-availability gate)."""
    decision_viewpoint_scores, decision_cross_exam_scores = _decision_viewpoint_and_cross_exam_scores(decisions, ceo_decisions, debates)
    readings: list[tuple[WisdomFactorId, str, float, str]] = [
        ("learn_from_experience", "Learning From Experience", _learn_from_experience(discipline_reviews, decisions), "Whether recent Discipline Scores are trending up against the desk's own earlier record, or the real decision-time Decision Grade trend before enough closed trades exist."),
        ("share_knowledge", "Sharing Knowledge", _share_knowledge(memory, knowledge_events), "Real mentorship sessions plus real lesson-sharing events (Institutional Memory → relevant agents)."),
        ("follow_principles", "Following Principles", _follow_principles(trade_history, gatekeeper_rejections, audit_entries), "Share of trades that cleared the Trade Gatekeeper's real configured limits without a block, or the real Audit Log compliance score before any trade exists."),
        ("improve_communication", "Improving Communication", _improve_communication(discipline_reviews, decision_cross_exam_scores), "Average real Cross-Examination factor across recent Discipline Reviews, or the same real signal read at decision time before enough closed trades exist."),
        ("document_lessons", "Documenting Lessons", _document_lessons(discipline_reviews, case_studies, reasoning_challenges, institutional_memory), "Real Discipline Reviews, Case Studies, Reasoning Challenges, and documented Institutional Memory lessons filed to date."),
        ("avoid_repeating_mistakes", "Avoiding Repeated Mistakes", _avoid_repeating_mistakes(case_studies, knowledge_events, institutional_memory), "How diversified the Library of Mistakes' real categories are, or whether new evidence keeps confirming the same standing mistake/risk pattern."),
        ("complete_research", "Completing Research", _complete_research(research), "Share of the research queue that has actually reached completed status."),
        (
            "support_collaboration",
            "Supporting Collaboration",
            _support_collaboration(discipline_reviews, collaboration_case_score, decision_viewpoint_scores),
            "Average real Viewpoint Diversity factor across recent Discipline Reviews, or real cross-department collaboration-case evidence (stance diversity + evidence reuse) at decision time before enough closed trades exist.",
        ),
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
