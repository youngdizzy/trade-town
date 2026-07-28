"""DisciplineChamber — v0.7 Feature 26, the Discipline Chamber.

Generates a permanent DisciplineReview for every trade that closes,
scoring the DECISION PROCESS that led to it — never the outcome. The
brief's core rule ("a lucky outcome should NEVER automatically produce a
high Discipline Score") is enforced structurally, not just by convention:
compute_discipline_score() below never receives the trade's pnl, only its
real hold duration (a behavioral/process signal, not a result) plus the
original TradeDecision's own real process trail — the six real analyst
votes, the AI Debate (Feature 17), and the Decision Confidence Engine's
own already-computed factors (Feature 15). The trade's real win/loss
outcome is attached to the finished review afterward, purely so the
player can see whether a good process and a good outcome actually lined
up — see _summary() below for how a good-process/bad-outcome or a
bad-process/lucky-win mismatch is called out explicitly, the whole
pedagogical point of this feature.

Every factor reuses data this codebase already computes for other real
reasons. Two real traps were checked and avoided while designing the
factor set: `TradeDecision.votes` always contains all six real analyst
votes (so "were multiple viewpoints gathered" is structurally constant,
not a real discriminator — "viewpoint diversity," how many *distinct*
choices those six votes actually contained, is the real, varying signal
used instead), and every trade that ever reaches this module already
passed the Trade Gatekeeper's full checklist to open at all (a rejected
verdict means no PaperTrade ever exists — see app/gatekeeper.py), so
"did it pass the Gatekeeper" is also structurally constant for this
population; "position sizing discipline" reuses the Decision Confidence
Engine's own real, still-varying Portfolio Exposure factor instead. The
brief's "was proper documentation created" has no real discriminating
signal either — every decision's summaries/reasoning are unconditionally
auto-populated in this codebase, so scoring it would be fake precision on
an invariant. The seven factors below are the honest, real, and
genuinely-varying subset — the same "checked, not assumed, cut where
there's no real signal" convention app/confidence.py and
app/gatekeeper.py already established.
"""
from __future__ import annotations

from typing import Literal

from app.schemas import (
    AgentId,
    Debate,
    DisciplineFactor,
    DisciplineReview,
    DisciplineTier,
    PostDecisionReview,
    TradeDecision,
)

MAX_DISCIPLINE_REVIEWS = 60
# Matches app/coach.py's own "patient win" bar (patient_wins >= 240
# minutes) — reused rather than inventing a second patience threshold.
PATIENCE_TARGET_MINUTES = 240
# Matches app/coach.py's own "quick loss" bar.
QUICK_CLOSE_MINUTES = 180

_WEIGHTS: dict[str, float] = {
    "research_depth": 0.20,
    "viewpoint_diversity": 0.15,
    "uncertainty_acknowledged": 0.10,
    "cross_examination": 0.15,
    "assumptions_challenged": 0.15,
    "position_sizing_discipline": 0.15,
    "patience": 0.10,
}


def tier_for_score(score: float) -> DisciplineTier:
    if score >= 85:
        return "exemplary"
    if score >= 70:
        return "sound"
    if score >= 55:
        return "adequate"
    if score >= 40:
        return "weak"
    return "reckless"


def confidence_factor_score(decision: TradeDecision, name: str, default: float = 50.0) -> float:
    if decision.confidence_engine is None:
        return default
    factor = next((f for f in decision.confidence_engine.factors if f.name == name), None)
    return factor.score if factor is not None else default


def compute_discipline_score(
    decision: TradeDecision,
    debate: Debate | None,
    hold_duration_minutes: int,
) -> tuple[float, list[DisciplineFactor]]:
    """Never reads `decision`'s outcome or any trade pnl — only takes a
    real hold duration (known once a trade closes, but a behavioral
    signal, not a result) as its one time-of-close input. Everything else
    was already real and fixed at the moment the CEO actually decided."""
    votes = decision.votes
    distinct_choices = len({v.choice for v in votes}) if votes else 1
    viewpoint_score = 100.0 if distinct_choices >= 3 else 65.0 if distinct_choices == 2 else 35.0

    uncertainty_score = 100.0 if any(v.choice == "hold" for v in votes) else 55.0

    analyst_count = len(votes) or 6
    if debate is None:
        cross_exam_score = 0.0
        cross_exam_detail = "No AI Debate was generated for this proposal."
    elif len(debate.turns) <= analyst_count:
        cross_exam_score = 30.0
        cross_exam_detail = "The debate only recorded opening statements — no real cross-examination followed."
    else:
        cross_exam_score = 100.0
        cross_exam_detail = f"The AI Debate produced {len(debate.turns) - analyst_count} real cross-examination turn(s) beyond the opening statements."

    challenge_turns = [t for t in debate.turns if t.stance == "challenge"] if debate else []
    challenge_score = min(100.0, len(challenge_turns) * 40.0)

    exposure_score = confidence_factor_score(decision, "Portfolio Exposure")
    research_score = confidence_factor_score(decision, "Research Confidence")

    patience_score = min(100.0, (hold_duration_minutes / PATIENCE_TARGET_MINUTES) * 100.0)

    raw_scores = {
        "research_depth": research_score,
        "viewpoint_diversity": viewpoint_score,
        "uncertainty_acknowledged": uncertainty_score,
        "cross_examination": cross_exam_score,
        "assumptions_challenged": challenge_score,
        "position_sizing_discipline": exposure_score,
        "patience": patience_score,
    }
    total = sum(raw_scores[key] * weight for key, weight in _WEIGHTS.items())

    factors = [
        DisciplineFactor(
            id="research_depth",
            name="Research Depth",
            score=round(research_score, 1),
            weight=_WEIGHTS["research_depth"],
            detail=f"The underlying research had reached {research_score:.0f}% confidence before this decision was made.",
        ),
        DisciplineFactor(
            id="viewpoint_diversity",
            name="Viewpoint Diversity",
            score=round(viewpoint_score, 1),
            weight=_WEIGHTS["viewpoint_diversity"],
            detail=f"The six analysts returned {distinct_choices} distinct real position(s) — {'genuine independent thinking' if distinct_choices >= 2 else 'no real disagreement among the desk'}.",
        ),
        DisciplineFactor(
            id="uncertainty_acknowledged",
            name="Uncertainty Acknowledged",
            score=round(uncertainty_score, 1),
            weight=_WEIGHTS["uncertainty_acknowledged"],
            detail="At least one analyst voted to wait, an explicit real signal of uncertainty." if uncertainty_score >= 100 else "Every analyst voted a direction — no one on the desk explicitly flagged uncertainty.",
        ),
        DisciplineFactor(
            id="cross_examination",
            name="Cross-Examination Occurred",
            score=round(cross_exam_score, 1),
            weight=_WEIGHTS["cross_examination"],
            detail=cross_exam_detail,
        ),
        DisciplineFactor(
            id="assumptions_challenged",
            name="Assumptions Challenged",
            score=round(challenge_score, 1),
            weight=_WEIGHTS["assumptions_challenged"],
            detail=f"{len(challenge_turns)} real challenge turn(s) pushed back on the desk's thesis in the AI Debate." if challenge_turns else "No analyst real pushed back on the thesis during the AI Debate.",
        ),
        DisciplineFactor(
            id="position_sizing_discipline",
            name="Position Sizing Discipline",
            score=round(exposure_score, 1),
            weight=_WEIGHTS["position_sizing_discipline"],
            detail=f"Portfolio exposure at decision time scored {exposure_score:.0f}/100 for room to size this position responsibly.",
        ),
        DisciplineFactor(
            id="patience",
            name="Patience",
            score=round(patience_score, 1),
            weight=_WEIGHTS["patience"],
            detail=f"The position held for {hold_duration_minutes} simulated minutes ({'at or past' if hold_duration_minutes >= PATIENCE_TARGET_MINUTES else 'short of'} the {PATIENCE_TARGET_MINUTES}-minute patient-hold bar).",
        ),
    ]
    return round(total, 1), factors


def _attendees(decision: TradeDecision) -> list[AgentId]:
    seen: list[AgentId] = []
    for agent_id in [*decision.supporting_agents, *decision.opposing_agents]:
        if agent_id not in seen:
            seen.append(agent_id)
    return seen


def _summary(score: float, tier: DisciplineTier, outcome: Literal["win", "loss"], pnl_pct: float) -> str:
    base = f"{tier.title()} discipline ({score:.0f}/100)"
    if score >= 70 and outcome == "win":
        return f"{base} — the process was sound and the trade won ({pnl_pct:+.1f}%): good decision, good outcome, aligned."
    if score >= 70 and outcome == "loss":
        return f"{base} that still lost ({pnl_pct:+.1f}%) — this reads as a good decision undone by real market variance, not a process failure. Don't let the result discourage this process."
    if score < 55 and outcome == "win":
        return f"{base} that happened to win ({pnl_pct:+.1f}%) — treat this as a warning, not a validation. The same process is likely to lose next time."
    if score < 55 and outcome == "loss":
        return f"{base} that also lost ({pnl_pct:+.1f}%) — the weak process and the bad outcome are connected here."
    return f"{base}, closed {'up' if pnl_pct >= 0 else 'down'} {pnl_pct:+.1f}%."


# Analysts whose real dissent (being in a decision's own opposing_agents)
# is checkable against a later real outcome — Sentinel is deliberately
# excluded: the Trade Gatekeeper's risk_manager_check hard-requires the
# risk analyst's vote to match the CEO's choice before a trade can even
# open (see app/gatekeeper.py), so Sentinel can never actually appear in
# opposing_agents on a trade that reached this module — including it here
# would describe a code path that cannot occur.
DISSENT_CHECKABLE_AGENTS: tuple[AgentId, ...] = ("echo", "scout")


def overridden_dissent(decision: TradeDecision) -> list[AgentId]:
    """Real analysts in DISSENT_CHECKABLE_AGENTS whose vote the CEO
    overrode for this decision — shared with app/mistakes.py's
    "Confirmation Bias" case-study category so both modules read the
    exact same real signal rather than two independently-drifting
    definitions."""
    return [a for a in decision.opposing_agents if a in DISSENT_CHECKABLE_AGENTS]


def _post_decision_review(decision: TradeDecision, factors: list[DisciplineFactor], outcome: Literal["win", "loss"]) -> PostDecisionReview:
    strong = [f for f in factors if f.score >= 75]
    weak = [f for f in factors if f.score < 55]
    overridden = overridden_dissent(decision) if outcome == "loss" else []
    return PostDecisionReview(
        whatWeDidWell=[f"{f.name}: {f.detail}" for f in strong],
        mistakesMade=[f"{f.name}: {f.detail}" for f in weak],
        informationOverlooked=[f.detail for f in weak if f.id in ("research_depth", "assumptions_challenged", "cross_examination")],
        # Only a real loss can show a real "the desk's assumption proved
        # incorrect" — a win never disproves the thesis that produced it.
        # Named specifically to the real dissenting analyst who was
        # overridden and turned out right, not a vague "we were wrong."
        assumptionsIncorrect=[f"{agent.title()}'s dissent was overridden — and the trade lost, so that dissent proved right." for agent in overridden],
        whatToRepeat=[f.name for f in strong],
        whatToNeverRepeat=[f.name for f in weak] if outcome == "loss" else [],
        howToImprove=[f"Raise {min(factors, key=lambda f: f.score).name} — {min(factors, key=lambda f: f.score).detail}"] if factors else [],
    )


def generate_discipline_review(
    decision: TradeDecision,
    debate: Debate | None,
    *,
    hold_duration_minutes: int,
    pnl: float,
    pnl_pct: float,
    review_id: str,
    sim_day: int,
    created_at: str,
) -> DisciplineReview:
    score, factors = compute_discipline_score(decision, debate, hold_duration_minutes)
    tier = tier_for_score(score)
    outcome: Literal["win", "loss"] = "win" if pnl > 0 else "loss"
    return DisciplineReview(
        id=review_id,
        decisionId=decision.id,
        symbol=decision.symbol,
        score=score,
        tier=tier,
        factors=factors,
        attendees=_attendees(decision),
        summary=_summary(score, tier, outcome, pnl_pct),
        postDecisionReview=_post_decision_review(decision, factors, outcome),
        outcome=outcome,
        tradePnlPct=round(pnl_pct, 2),
        holdDurationMinutes=hold_duration_minutes,
        simDay=sim_day,
        createdAt=created_at,
    )


def record_review(reviews: list[DisciplineReview], review: DisciplineReview) -> list[DisciplineReview]:
    updated = [*reviews, review]
    if len(updated) > MAX_DISCIPLINE_REVIEWS:
        del updated[: len(updated) - MAX_DISCIPLINE_REVIEWS]
    return updated
