"""LibraryOfMistakes — v0.7 Feature 27, the Library of Mistakes.

Files a permanent CaseStudy whenever a closed, losing trade's own
DisciplineReview (app/discipline.py) shows a specific real process gap —
never merely "the trade lost" on its own. A well-disciplined process that
loses to real market variance is the Discipline Chamber's whole point to
protect, not punish (see discipline.py's _summary()); a mistake, in this
codebase's honest sense, is a real, checkable process failure that
coincided with a real loss.

Six categories, each mapped to one real, checkable signal already present
on the linked TradeDecision/Debate/DisciplineReview/PaperTrade — never a
fabricated pattern:

  overconfidence          — Decision Confidence Engine scored the setup
                             80+ at decision time, yet it lost.
  incomplete_research      — the underlying research's own confidence
                             factor was below 50 at decision time.
  unchallenged_assumptions — the linked AI Debate had zero real
                             "challenge" turns (or no debate at all).
  acted_too_quickly        — the position closed within
                             QUICK_CLOSE_MINUTES (the exact real threshold
                             app/coach.py's own "quick loss" pattern uses).
  ignored_dissent          — the AI Debate's own real final synthesis
                             recommended the opposite of what actually
                             executed (the CEO overrode the committee).
  confirmation_bias        — a real, specific dissenting analyst (Echo or
                             Scout — see discipline.py's
                             DISSENT_CHECKABLE_AGENTS for why Sentinel is
                             excluded) was overridden and, since the trade
                             lost, that dissent proved right.

A single trade can trigger more than one category — each becomes its own
CaseStudy, matching the brief's own framing of these as distinct,
separately-filed examples rather than one bundled report.

Every field in the resulting CaseStudy is built from real structured data
— the linked TradeDecision's own real vote reasoning, the real Debate
turns, the real RiskLimits/Gatekeeper thresholds, real timestamps — filled
into a fixed template, never a fabricated narrative. Same convention
app/executive_review.py and app/academy_research.py already established.
"""
from __future__ import annotations

from app.discipline import QUICK_CLOSE_MINUTES, overridden_dissent
from app.gatekeeper import MIN_CONFIDENCE
from app.risk_engine import default_risk_limits
from app.schemas import (
    AnalystChoice,
    CaseStudy,
    CaseStudyCategory,
    CaseStudyTimelineEntry,
    Debate,
    DisciplineReview,
    PaperTrade,
    TradeDecision,
)

MAX_CASE_STUDIES = 60
OVERCONFIDENCE_THRESHOLD = 80.0
INCOMPLETE_RESEARCH_THRESHOLD = 50.0

_TITLES: dict[CaseStudyCategory, str] = {
    "overconfidence": "The Cost of Overconfidence",
    "incomplete_research": "Incomplete Research",
    "unchallenged_assumptions": "Failure to Challenge Assumptions",
    "acted_too_quickly": "Acting Too Quickly",
    "ignored_dissent": "Poor Communication",
    "confirmation_bias": "Confirmation Bias",
}

_RISK_LIMITS = default_risk_limits()
_RELATED_PRINCIPLES: list[str] = [
    f"Decision Confidence must clear {MIN_CONFIDENCE:.0f}/100 before the Trade Gatekeeper approves a trade.",
    f"Position risk is capped at {_RISK_LIMITS.risk_per_trade_pct:.0f}% of equity per trade.",
    f"Portfolio drawdown is capped at {_RISK_LIMITS.max_drawdown_pct:.0f}% before new trades pause.",
]


def _research_confidence(decision: TradeDecision) -> float | None:
    if decision.confidence_engine is None:
        return None
    factor = next((f for f in decision.confidence_engine.factors if f.name == "Research Confidence"), None)
    return factor.score if factor is not None else None


def _detect_categories(decision: TradeDecision, debate: Debate | None, trade: PaperTrade) -> list[CaseStudyCategory]:
    categories: list[CaseStudyCategory] = []

    if decision.confidence_engine is not None and decision.confidence_engine.score >= OVERCONFIDENCE_THRESHOLD:
        categories.append("overconfidence")

    research_confidence = _research_confidence(decision)
    if research_confidence is not None and research_confidence < INCOMPLETE_RESEARCH_THRESHOLD:
        categories.append("incomplete_research")

    challenge_turns = [t for t in debate.turns if t.stance == "challenge"] if debate else []
    if not challenge_turns:
        categories.append("unchallenged_assumptions")

    if trade.duration_minutes < QUICK_CLOSE_MINUTES:
        categories.append("acted_too_quickly")

    ceo_choice: AnalystChoice = "buy" if trade.side == "buy" else "sell"
    if debate is not None and debate.final_recommendation != ceo_choice:
        categories.append("ignored_dissent")

    if overridden_dissent(decision):
        categories.append("confirmation_bias")

    return categories


def _timeline(decision: TradeDecision, trade: PaperTrade) -> list[CaseStudyTimelineEntry]:
    return [
        CaseStudyTimelineEntry(label="Decision made", timestamp=decision.created_at),
        CaseStudyTimelineEntry(label="Position opened", timestamp=trade.opened_at),
        CaseStudyTimelineEntry(label="Position closed", timestamp=trade.closed_at),
    ]


def _missed_information(category: CaseStudyCategory, decision: TradeDecision, debate: Debate | None) -> str:
    if category == "overconfidence":
        score = decision.confidence_engine.score if decision.confidence_engine else 0.0
        return f"The setup read {score:.0f}/100 on the Decision Confidence Engine — high confidence did not translate to accuracy here."
    if category == "incomplete_research":
        confidence = _research_confidence(decision) or 0.0
        return f"The underlying research had only reached {confidence:.0f}% confidence before this decision proceeded."
    if category == "unchallenged_assumptions":
        return "No analyst pushed back during the AI Debate — the thesis went untested before execution." if debate else "No AI Debate was generated for this proposal at all."
    if category == "acted_too_quickly":
        return "The position closed well inside the patient-hold window, before the original thesis had time to play out."
    if category == "ignored_dissent":
        rec = debate.final_recommendation.upper() if debate else "WAIT"
        return f"The AI Debate's own committee synthesis recommended {rec}, but a different call was actually executed."
    overridden = overridden_dissent(decision)
    names = " and ".join(a.title() for a in overridden)
    return f"{names}'s dissenting vote was overridden going into this trade."


def _recommended_improvement(category: CaseStudyCategory) -> str:
    return {
        "overconfidence": "Treat Decision Confidence scores above 80 with continued scrutiny — they have not reliably predicted outcomes on this record.",
        "incomplete_research": "Hold off executing on research below 50% confidence; let it develop further before it reaches a trade proposal.",
        "unchallenged_assumptions": "Request another AI Debate before proceeding when the first pass produced no real cross-examination.",
        "acted_too_quickly": "Let a position clear the patient-hold window before reassessing, rather than closing on early noise.",
        "ignored_dissent": "Weigh the AI Debate's own final synthesis at least as heavily as the individual analyst votes that fed into it.",
        "confirmation_bias": "When a specific analyst dissents, treat that dissent as a real data point to investigate, not an obstacle to route around.",
    }[category]


def generate_case_studies(
    decision: TradeDecision,
    debate: Debate | None,
    trade: PaperTrade,
    discipline_review: DisciplineReview,
    *,
    id_prefix: str,
) -> list[CaseStudy]:
    """Only ever called for a real loss (see nexus.py's wiring) — a
    winning trade has no real "missed information" to name, regardless of
    how weak its process score was (that case is handled honestly in
    discipline.py's own summary/post-decision-review instead, not here)."""
    categories = _detect_categories(decision, debate, trade)
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
            title=_TITLES[category],
            symbol=decision.symbol,
            decisionId=decision.id,
            timeline=timeline,
            background=background,
            decisionProcess=decision_process,
            departmentOpinions=department_opinions,
            missedInformation=_missed_information(category, decision, debate),
            lessonsLearned=discipline_review.summary,
            recommendedImprovements=_recommended_improvement(category),
            relatedPrinciples=_RELATED_PRINCIPLES,
            tradePnlPct=discipline_review.trade_pnl_pct,
            simDay=discipline_review.sim_day,
            createdAt=discipline_review.created_at,
        )
        for category in categories
    ]


def record_case_studies(case_studies: list[CaseStudy], new_studies: list[CaseStudy]) -> list[CaseStudy]:
    updated = [*case_studies, *new_studies]
    if len(updated) > MAX_CASE_STUDIES:
        del updated[: len(updated) - MAX_CASE_STUDIES]
    return updated
