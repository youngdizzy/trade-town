"""DecisionConfidence — v0.7 Feature 15, the Decision Confidence Engine.

Never predicts whether a trade will win. It scores the *quality of the
evidence* behind the current setup, the same "process, not outcome"
principle app/executive.py's Trade Quality read already established in
v0.6.3 — this module formalizes and persists that read server-side
(at proposal-generation time, carried onto the resulting TradeDecision)
instead of recomputing it client-side on every render, so Trade
History / Post-Trade Review can compare the *exact* reading a decision
was actually made under against its real later outcome.

Every factor below is derived from data this codebase already computes
for other real reasons — the six AnalystVotes (app/executive.py),
the research item's own confidence, real portfolio exposure, and (CEO
directive "Professional Quant Trading Core," Phase B) real higher-
timeframe trend confirmation (app/multi_timeframe.py). The v0.7 brief
also names several factors with no real backing data in this codebase:
support & resistance levels, liquidity quality, historical strategy
performance, and similar-historical-setup matching. None of these are
computed here; inventing numbers for them would be exactly the kind of
fabrication this project avoids. "Multi-timeframe agreement" was on
that same disclosed-gap list until Multi-Timeframe Confirmation closed
it — see this factor's own weight-rebalancing note below. The seven
factors below are the honest, real subset.
"""
from __future__ import annotations

from app.schemas import AnalystChoice, AnalystVote, ConfidenceFactor, DecisionConfidence, ConfidenceTier, MultiTimeframeConfirmation, PaperPortfolio, RiskLimits

# Must sum to 1.0 — see the module docstring for why each was chosen and
# what was deliberately left out.
#
# CEO directive "Professional Quant Trading Core," Phase B — adding
# "multi_timeframe" required freeing 0.15 from the existing six. Trimmed
# 0.05 each from "agreement" (.30->.25), "technical" (.20->.15), and
# "research" (.15->.10) — an even, disclosed cut across the three
# largest weights, not a targeted shrink of any one factor's real
# importance. No other factor's weight changed.
_WEIGHTS: dict[str, float] = {
    "agreement": 0.25,
    "technical": 0.15,
    "multi_timeframe": 0.15,
    "risk": 0.20,
    "research": 0.10,
    "sentiment": 0.10,
    "exposure": 0.05,
}


def tier_for_score(score: float) -> ConfidenceTier:
    if score >= 95:
        return "elite"
    if score >= 85:
        return "strong"
    if score >= 70:
        return "good"
    if score >= 55:
        return "moderate"
    if score >= 40:
        return "weak"
    return "poor"


_TIER_LABEL: dict[ConfidenceTier, str] = {
    "elite": "Elite Setup",
    "strong": "Strong Setup",
    "good": "Good Setup",
    "moderate": "Moderate Setup",
    "weak": "Weak Setup",
    "poor": "Poor Setup",
}


def _vote(votes: list[AnalystVote], role: str) -> AnalystVote | None:
    return next((v for v in votes if v.role == role), None)


def _match_score(vote: AnalystVote | None, overall: AnalystChoice, *, oppose: float = 15.0, wait: float = 50.0, match: float = 90.0) -> float:
    if vote is None:
        return wait
    if vote.choice == overall:
        return match
    if vote.choice == "wait":
        return wait
    return oppose


def compute_confidence(
    votes: list[AnalystVote],
    overall: AnalystChoice,
    research_confidence: float,
    portfolio: PaperPortfolio,
    risk_limits: RiskLimits,
    multi_timeframe: MultiTimeframeConfirmation,
) -> DecisionConfidence:
    """`multi_timeframe` is required, not optional-with-a-default: the
    one real production caller (app/executive.py's generate_proposal())
    always has real provider access to compute it, and a silent "not
    evaluated yet" default would mean this factor quietly stops being
    real evidence the moment a caller forgets to pass it. Test call
    sites build one explicitly (see test_confidence.py)."""
    agreeing = sum(1 for v in votes if v.choice == overall)
    agreement_score = (agreeing / len(votes)) * 100 if votes else 0.0

    technical_score = _match_score(_vote(votes, "technical"), overall)
    risk_score = _match_score(_vote(votes, "risk"), overall, oppose=35.0, wait=35.0, match=90.0)
    research_score = max(0.0, min(100.0, research_confidence))

    news_score = _match_score(_vote(votes, "news"), overall, oppose=20.0, wait=50.0, match=80.0)
    macro_score = _match_score(_vote(votes, "macro"), overall, oppose=20.0, wait=50.0, match=80.0)
    sentiment_analyst_score = _match_score(_vote(votes, "sentiment"), overall, oppose=20.0, wait=50.0, match=80.0)
    sentiment_score = (news_score + macro_score + sentiment_analyst_score) / 3

    max_positions = max(risk_limits.max_open_positions, 1)
    exposure_pct = min(1.0, len(portfolio.positions) / max_positions)
    exposure_score = (1.0 - exposure_pct) * 100

    raw_scores = {
        "agreement": agreement_score,
        "technical": technical_score,
        "multi_timeframe": multi_timeframe.agreement_score,
        "risk": risk_score,
        "research": research_score,
        "sentiment": sentiment_score,
        "exposure": exposure_score,
    }
    total = sum(raw_scores[key] * weight for key, weight in _WEIGHTS.items())
    tier = tier_for_score(total)

    factors = [
        ConfidenceFactor(
            name="Multi-Agent Agreement",
            score=round(agreement_score, 1),
            weight=_WEIGHTS["agreement"],
            detail=f"{agreeing}/{len(votes)} analysts agree with {overall.upper()}.",
        ),
        ConfidenceFactor(
            name="Technical Alignment",
            score=round(technical_score, 1),
            weight=_WEIGHTS["technical"],
            detail=(_vote(votes, "technical") or AnalystVote(role="technical", agentId="echo", choice="wait", reasoning="No technical read available.", evidence=[])).reasoning,
        ),
        ConfidenceFactor(
            name="Risk Conditions",
            score=round(risk_score, 1),
            weight=_WEIGHTS["risk"],
            detail=(_vote(votes, "risk") or AnalystVote(role="risk", agentId="sentinel", choice="wait", reasoning="No risk read available.", evidence=[])).reasoning,
        ),
        ConfidenceFactor(
            name="Multi-Timeframe Confirmation",
            score=round(multi_timeframe.agreement_score, 1),
            weight=_WEIGHTS["multi_timeframe"],
            detail=multi_timeframe.summary,
        ),
        ConfidenceFactor(
            name="Research Confidence",
            score=round(research_score, 1),
            weight=_WEIGHTS["research"],
            detail=f"Underlying research reached {research_confidence:.0f}% confidence before this proposal was generated.",
        ),
        ConfidenceFactor(
            name="News, Macro & Sentiment",
            score=round(sentiment_score, 1),
            weight=_WEIGHTS["sentiment"],
            detail="Average alignment of the news, macro, and sentiment analyst votes with the desk's overall call.",
        ),
        ConfidenceFactor(
            name="Portfolio Exposure",
            score=round(exposure_score, 1),
            weight=_WEIGHTS["exposure"],
            detail=f"{len(portfolio.positions)}/{max_positions} open positions — {'ample' if exposure_score >= 60 else 'limited'} room for a new one.",
        ),
    ]

    strongest = max(factors, key=lambda f: f.score)
    weakest = min(factors, key=lambda f: f.score)
    summary = f"{_TIER_LABEL[tier]} ({round(total)}/100) — strongest: {strongest.name} ({strongest.score:.0f}), weakest: {weakest.name} ({weakest.score:.0f})."

    return DecisionConfidence(score=round(total, 1), tier=tier, summary=summary, factors=factors)
