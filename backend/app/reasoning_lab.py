"""ReasoningLab — v0.7 Feature 29, the Reasoning Lab.

Files a permanent ReasoningChallenge periodically from the company's most
recent real AI Debate (app/debate.py) plus its linked TradeDecision —
practicing the reasoning process itself, never a trade outcome. Like
app/discipline.py, this is a structural guarantee: no function in this
module ever reads a trade's pnl or a decision's realized outcome, only
the real votes/debate turns/confidence factors that existed at decision
time.

Seven honest categories, each mapped to one real, checkable signal
already present on the linked TradeDecision/Debate — the brief named
nine; two ("Detecting Logical Fallacies", "Building Better Questions")
would require actual fallacy-detection or question-quality scoring this
codebase has no real data source for, and are deliberately not built —
the same "checked, not assumed, cut where there's no real signal"
convention app/discipline.py and app/mistakes.py already established:

  finding_missing_information       — the underlying research's own
                                       confidence factor was below the
                                       same INCOMPLETE_RESEARCH_THRESHOLD
                                       app/mistakes.py uses.
  identifying_weak_evidence         — at least one analyst's real opening
                                       statement carried no real backing
                                       evidence (app/debate.py only
                                       appends "(...)" to an opening turn
                                       when the source AnalystVote had
                                       real evidence — the same indirect,
                                       honest proxy discipline.py's
                                       cross-examination check relies on).
  recognizing_contradictory_data    — the six analysts' real votes
                                       actually split three ways.
  separating_facts_from_assumptions — the AI Debate had at least one real
                                       "challenge" turn (someone actually
                                       contested an assumption).
  comparing_competing_explanations  — at least two distinct analysts each
                                       filed a real "support" turn,
                                       meaning more than one line of
                                       reasoning was actively reinforced.
  evaluating_multiple_hypotheses    — the six votes split exactly two
                                       ways (two live hypotheses).
  improving_communication           — the honest fallback when no
                                       stronger signal fired (including
                                       no real Debate existing at all) —
                                       the desk's own communication, not
                                       its research, is the real gap.

Reasoning Level (see compute_reasoning_lab_state) gates which categories
can actually be selected — a real, monotonic completed-challenge count,
mirroring app/academy.py's AcademyState convention exactly. New seminar
content / collaboration animations per level are an explicit scope cut
(no real data source), same boundary AcademyState already drew.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.discipline import confidence_factor_score
from app.mistakes import INCOMPLETE_RESEARCH_THRESHOLD
from app.schemas import (
    Debate,
    ReasoningChallenge,
    ReasoningChallengeCategory,
    ReasoningContribution,
    ReasoningLabState,
    ReasoningSolution,
    TradeDecision,
)

MAX_REASONING_CHALLENGES = 60

# Crossing each threshold advances one Reasoning Level (1-3) — the same
# cumulative-count gate app/academy.py's own company-wide Academy Level
# uses, since every challenge already came from a real Debate; there is
# no "attempt" to grind.
_REASONING_LEVEL_THRESHOLDS: tuple[tuple[int, str], ...] = (
    (0, "Foundations"),
    (5, "Applied Reasoning"),
    (12, "Advanced Reasoning"),
)

# The Reasoning Level required before each category can actually be
# detected — see module docstring. The three foundational categories need
# no prior progress; the four that require a specific, less-common real
# debate shape only appear once the company has practiced the basics.
_LEVEL_FOR_CATEGORY: dict[ReasoningChallengeCategory, int] = {
    "finding_missing_information": 1,
    "evaluating_multiple_hypotheses": 1,
    "improving_communication": 1,
    "identifying_weak_evidence": 2,
    "separating_facts_from_assumptions": 2,
    "recognizing_contradictory_data": 3,
    "comparing_competing_explanations": 3,
}

_TITLES: dict[ReasoningChallengeCategory, str] = {
    "finding_missing_information": "Finding Missing Information",
    "identifying_weak_evidence": "Identifying Weak Evidence",
    "recognizing_contradictory_data": "Recognizing Contradictory Data",
    "separating_facts_from_assumptions": "Separating Facts from Assumptions",
    "evaluating_multiple_hypotheses": "Evaluating Multiple Hypotheses",
    "comparing_competing_explanations": "Comparing Competing Explanations",
    "improving_communication": "Improving Communication",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_reasoning_lab_state(completed_challenge_count: int) -> ReasoningLabState:
    level = 1
    label = _REASONING_LEVEL_THRESHOLDS[0][1]
    for i, (threshold, lbl) in enumerate(_REASONING_LEVEL_THRESHOLDS):
        if completed_challenge_count >= threshold:
            level = i + 1
            label = lbl
    return ReasoningLabState(
        level=level,
        levelLabel=label,
        completedChallengeCount=completed_challenge_count,
        updatedAt=_now_iso(),
    )


def _detect_category(decision: TradeDecision, debate: Debate | None, unlocked_level: int) -> ReasoningChallengeCategory:
    votes = decision.votes
    distinct_choices = len({v.choice for v in votes}) if votes else 1
    turns = debate.turns if debate else []
    opening_turns = [t for t in turns if t.stance == "opening"]
    challenge_turns = [t for t in turns if t.stance == "challenge"]
    support_agents = {t.agent_id for t in turns if t.stance == "support"}
    research_score = confidence_factor_score(decision, "Research Confidence")

    ordered_candidates: list[tuple[ReasoningChallengeCategory, bool]] = [
        ("comparing_competing_explanations", len(support_agents) >= 2),
        ("recognizing_contradictory_data", distinct_choices >= 3),
        ("separating_facts_from_assumptions", bool(challenge_turns)),
        ("identifying_weak_evidence", any("(" not in t.text for t in opening_turns)),
        ("finding_missing_information", research_score < INCOMPLETE_RESEARCH_THRESHOLD),
        ("evaluating_multiple_hypotheses", distinct_choices == 2),
    ]
    for category, is_real in ordered_candidates:
        if is_real and _LEVEL_FOR_CATEGORY[category] <= unlocked_level:
            return category
    return "improving_communication"


def _contributions(debate: Debate | None) -> list[ReasoningContribution]:
    if debate is None:
        return []
    return [
        ReasoningContribution(
            agentId=t.agent_id,
            role=t.role,
            stance=t.stance,
            contribution=t.text,
        )
        for t in debate.turns
    ]


def _solution(decision: TradeDecision) -> ReasoningSolution:
    factors = decision.confidence_engine.factors if decision.confidence_engine else []
    strong = [f for f in factors if f.score >= 70]
    weak = [f for f in factors if f.score < 50]
    what_we_know = [f"{f.name}: {f.detail}" for f in strong] or [decision.research_summary]
    what_we_do_not_know = [f"{f.name}: {f.detail}" for f in weak]
    opposing_reasons = [v.reason for v in decision.votes if v.agent_id in decision.opposing_agents]
    assumptions = opposing_reasons or ["No analyst dissented from this call, so no opposing assumption is on the record."]
    confidence = decision.confidence_engine.score if decision.confidence_engine else decision.confidence
    weakest = min(factors, key=lambda f: f.score) if factors else None
    what_could_change = (
        f"A material change in {weakest.name} (currently {weakest.score:.0f}/100) is the most likely thing to overturn this conclusion."
        if weakest is not None
        else "New evidence contradicting the desk's own votes above would change this conclusion."
    )
    return ReasoningSolution(
        whatWeKnow=what_we_know,
        whatWeDoNotKnow=what_we_do_not_know,
        assumptions=assumptions,
        whyReasonable=decision.final_reasoning,
        confidence=round(confidence, 1),
        whatCouldChangeOurConclusion=what_could_change,
    )


def generate_challenge(
    decision: TradeDecision,
    debate: Debate | None,
    *,
    challenge_id: str,
    unlocked_level: int,
    sim_day: int,
    created_at: str,
) -> ReasoningChallenge:
    category = _detect_category(decision, debate, unlocked_level)
    return ReasoningChallenge(
        id=challenge_id,
        category=category,
        title=_TITLES[category],
        symbol=decision.symbol,
        decisionId=decision.id,
        contributions=_contributions(debate),
        solution=_solution(decision),
        reasoningLevel=unlocked_level,
        simDay=sim_day,
        createdAt=created_at,
    )


def record_challenge(challenges: list[ReasoningChallenge], challenge: ReasoningChallenge) -> list[ReasoningChallenge]:
    updated = [*challenges, challenge]
    if len(updated) > MAX_REASONING_CHALLENGES:
        del updated[: len(updated) - MAX_REASONING_CHALLENGES]
    return updated
