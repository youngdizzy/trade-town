"""Library of Successes — v0.7 Feature 42, the Decision Replay Center's
"Successes" lesson type.

The mirror image of app/mistakes.py: files a permanent CaseStudy whenever
a closed, WINNING trade's own DisciplineReview shows a specific real
process strength — never merely "the trade won" on its own. A weak
process that wins on real market variance is exactly the case
discipline.py's own `_summary()` already warns against ("treat this as a
warning, not a validation"); it does not belong here.

Three categories, each the crisp inversion of one of mistakes.py's six —
the other three mistake signals have no equally crisp opposite (see
schemas.py's SUCCESS_CASE_STUDY_CATEGORIES comment for why they are not
mirrored):

  disciplined_process        — overall discipline score was 70+ (tier
                                "sound" or "exemplary") and the trade won —
                                the inverse of a general weak-process loss.
  rigorous_cross_examination — the linked AI Debate produced real
                                cross-examination beyond opening statements
                                (cross_exam_score == 100), the inverse of
                                "unchallenged_assumptions".
  patient_execution          — the position held to or past the patient-
                                hold target (patience_score >= 100), the
                                inverse of "acted_too_quickly".

A single trade can trigger more than one category — same convention
mistakes.py uses. Every field is built from real structured data already
computed by app/discipline.py's DisciplineReview, filled into a fixed
template, never a fabricated narrative.
"""
from __future__ import annotations

from app.schemas import (
    CaseStudy,
    CaseStudyCategory,
    CaseStudyTimelineEntry,
    Debate,
    DisciplineReview,
    PaperTrade,
    TradeDecision,
)

MAX_SUCCESS_STUDIES = 60
CROSS_EXAM_SCORE_THRESHOLD = 100.0
PATIENCE_SCORE_THRESHOLD = 100.0

CATEGORY_TITLES: dict[CaseStudyCategory, str] = {
    "disciplined_process": "A Well-Disciplined Process",
    "rigorous_cross_examination": "Rigorous Cross-Examination",
    "patient_execution": "Patient Execution",
}

_RELATED_PRINCIPLES: list[str] = [
    "A sound or exemplary Discipline Chamber score reflects a real, checkable process, not a guess.",
    "Real cross-examination during the AI Debate is what separates a tested thesis from an untested one.",
    "Holding a position to its patient-hold target lets the original thesis actually play out.",
]


def _factor_score(review: DisciplineReview, factor_id: str) -> float | None:
    factor = next((f for f in review.factors if f.id == factor_id), None)
    return factor.score if factor is not None else None


def _detect_categories(review: DisciplineReview) -> list[CaseStudyCategory]:
    categories: list[CaseStudyCategory] = []

    if review.score >= 70.0:
        categories.append("disciplined_process")

    cross_exam_score = _factor_score(review, "cross_examination")
    if cross_exam_score is not None and cross_exam_score >= CROSS_EXAM_SCORE_THRESHOLD:
        categories.append("rigorous_cross_examination")

    patience_score = _factor_score(review, "patience")
    if patience_score is not None and patience_score >= PATIENCE_SCORE_THRESHOLD:
        categories.append("patient_execution")

    return categories


def _timeline(decision: TradeDecision, trade: PaperTrade) -> list[CaseStudyTimelineEntry]:
    return [
        CaseStudyTimelineEntry(label="Decision made", timestamp=decision.created_at),
        CaseStudyTimelineEntry(label="Position opened", timestamp=trade.opened_at),
        CaseStudyTimelineEntry(label="Position closed", timestamp=trade.closed_at),
    ]


def _missed_information(category: CaseStudyCategory, review: DisciplineReview) -> str:
    """Named to match CaseStudy's field, but on the success side this
    answers "what did the process get right" rather than "what was
    missed" — the honest positive framing of the same real factor data."""
    if category == "disciplined_process":
        return f"The Discipline Chamber scored this decision's process {review.score:.0f}/100 — a {review.tier} read, independent of the outcome."
    if category == "rigorous_cross_examination":
        cross_exam = next(f for f in review.factors if f.id == "cross_examination")
        return cross_exam.detail
    patience = next(f for f in review.factors if f.id == "patience")
    return patience.detail


def _recommended_improvement(category: CaseStudyCategory) -> str:
    return {
        "disciplined_process": "Keep running the same real process — diverse viewpoints, uncertainty acknowledged, sized responsibly — regardless of any single trade's outcome.",
        "rigorous_cross_examination": "Keep requesting the AI Debate before executing — real cross-examination is what this record shows working.",
        "patient_execution": "Keep holding positions to their patient-hold window before reassessing rather than closing on early noise.",
    }[category]


def generate_success_studies(
    decision: TradeDecision,
    debate: Debate | None,
    trade: PaperTrade,
    discipline_review: DisciplineReview,
    *,
    id_prefix: str,
) -> list[CaseStudy]:
    """Only ever called for a real win (see nexus.py's wiring) — a losing
    trade has no real "process worked" story to tell, regardless of how
    strong its factor scores were (that case is mistakes.py's territory,
    or simply an honest "good process, bad luck" left unfiled by either
    module)."""
    del debate  # unused today; kept for signature symmetry with mistakes.py
    categories = _detect_categories(discipline_review)
    timeline = _timeline(decision, trade)
    background = f"{decision.symbol}: {decision.research_summary}"
    supporting = ", ".join(decision.supporting_agents) or "no one"
    opposing = ", ".join(decision.opposing_agents) or "no one"
    decision_process = (
        f"{len(decision.votes)} analysts voted; {supporting} supported the call, {opposing} opposed it. "
        f"{decision.final_reasoning}"
    )
    department_opinions = [f"{v.agent_id.title()}: {v.reason}" for v in decision.votes]

    return [
        CaseStudy(
            id=f"{id_prefix}-{category}",
            category=category,
            title=CATEGORY_TITLES[category],
            symbol=decision.symbol,
            decisionId=decision.id,
            timeline=timeline,
            background=background,
            decisionProcess=decision_process,
            departmentOpinions=department_opinions,
            missedInformation=_missed_information(category, discipline_review),
            lessonsLearned=discipline_review.summary,
            recommendedImprovements=_recommended_improvement(category),
            relatedPrinciples=_RELATED_PRINCIPLES,
            tradePnlPct=discipline_review.trade_pnl_pct,
            simDay=discipline_review.sim_day,
            createdAt=discipline_review.created_at,
        )
        for category in categories
    ]


def record_success_studies(case_studies: list[CaseStudy], new_studies: list[CaseStudy]) -> list[CaseStudy]:
    updated = [*case_studies, *new_studies]
    if len(updated) > MAX_SUCCESS_STUDIES:
        del updated[: len(updated) - MAX_SUCCESS_STUDIES]
    return updated
