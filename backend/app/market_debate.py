"""MarketDebate — v0.7 Feature 51, the Market Intelligence Department's
Market Debate System.

Five specialists, each inspired by a different real trading discipline
(never a copy of a real trader), independently reading the exact same
real MarketIntelligenceState (app/market_intelligence.py) — never a
trade-specific opinion, and never a second computation of anything: every
number and claim in a turn below is read straight off a field
compute_market_intelligence_state() already computed, the same
"deterministic-but-varied templated framing over real state" discipline
app/discussion.py and app/debate.py already established.

Distinct from two other real debate-shaped systems already in this
codebase, on purpose:
  - app/debate.py's AiDebate is proposal-scoped (one specific trade
    candidate, six analyst-vote seats already tied to that proposal).
    This module is market-condition-scoped — no proposal, no symbol
    picked yet, just "what does today's environment look like."
  - app/executive_intelligence.py's "Risk" department opinion is a
    proposal's own portfolio-exposure read (Sentinel/Guardian's real
    risk_summary). This module's Risk specialist deliberately does NOT
    duplicate that — it reads only real market-CONDITION risk (session
    liquidity, quality tier, news volume), never portfolio positions or
    drawdown, which stay Sentinel/Guardian's job.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import MarketDebate, MarketDebateTurn, MarketIntelligenceState

_SPECIALIST_LABEL: dict[str, str] = {
    "liquidity": "Liquidity Specialist",
    "price_action": "Price Action Specialist",
    "momentum": "Momentum Specialist",
    "quant": "Quant Specialist",
    "risk": "Risk Specialist",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _liquidity_turn(state: MarketIntelligenceState) -> MarketDebateTurn:
    sweeping = [lr for lr in state.liquidity if lr.sweep_detected]
    zoned = [lr for lr in state.liquidity if lr.zones]
    avg_score = (sum(lr.liquidity_score for lr in state.liquidity) / len(state.liquidity)) if state.liquidity else 0.0

    if sweeping:
        observation = f"{len(sweeping)}/{len(state.liquidity)} tracked symbol(s) just swept a real liquidity zone — {', '.join(s.symbol for s in sweeping[:3])}."
        risks = ["A sweep this fresh can still be a trap — price sometimes returns through the zone before actually reversing."]
        opportunities = ["A real sweep-and-reverse is the same setup price-action traders look for once the zone is confirmed broken and closed back inside."]
    elif zoned:
        observation = f"{len(zoned)}/{len(state.liquidity)} tracked symbol(s) carry a real, unswept equal-high/low cluster — probable liquidity sitting nearby."
        risks = ["A probable zone is not a guarantee price ever reaches it."]
        opportunities = ["These zones are real, checkable magnets for price if the current move continues toward them."]
    else:
        observation = "No real equal-high/low clustering or sweep found across the tracked watchlist right now."
        risks = ["Thin real structure data makes this a weaker-than-usual liquidity read."]
        opportunities = []
    evidence = [lr.detail for lr in state.liquidity[:3]] or ["No real liquidity data sampled yet."]
    return MarketDebateTurn(specialist="liquidity", label=_SPECIALIST_LABEL["liquidity"], observation=observation, confidencePct=round(avg_score, 1), evidence=evidence, risks=risks, opportunities=opportunities)


def _price_action_turn(state: MarketIntelligenceState) -> MarketDebateTurn:
    continuing = [s for s in state.structure if s.structure_state == "trend_continuation"]
    reversing = [s for s in state.structure if s.structure_state == "trend_reversal"]
    bos_count = sum(1 for s in state.structure if s.last_break_of_structure != "none")
    total = len(state.structure) or 1

    observation = f"{bos_count}/{len(state.structure)} tracked symbol(s) show a real Break of Structure; {len(continuing)} continuing, {len(reversing)} reversing."
    confidence = round((bos_count / total) * 100, 1)
    risks = ["A Break of Structure on one symbol doesn't confirm the whole market moved — this is an aggregate read, not a single-symbol call."] if reversing else []
    opportunities = [f"{len(continuing)} symbol(s) show real trend continuation structure — the highest-clarity setups today."] if continuing else []
    evidence = [s.detail for s in state.structure[:3]] or ["No real structure data sampled yet."]
    return MarketDebateTurn(specialist="price_action", label=_SPECIALIST_LABEL["price_action"], observation=observation, confidencePct=confidence, evidence=evidence, risks=risks, opportunities=opportunities)


def _momentum_turn(state: MarketIntelligenceState) -> MarketDebateTurn:
    momentum = state.momentum
    strength_confidence: dict[str, float] = {"accelerating": 75.0, "steady": 55.0, "decelerating": 40.0, "exhausted": 25.0}
    observation = f"Real rate of change reads {momentum.roc_pct:+.2f}% and is currently {momentum.strength.replace('_', ' ')}."
    risks = ["Exhausted momentum often precedes a real reversal — not confirmation one is coming."] if momentum.strength == "exhausted" else []
    opportunities = ["Accelerating momentum is the real signal continuation traders look for."] if momentum.strength == "accelerating" else []
    return MarketDebateTurn(
        specialist="momentum",
        label=_SPECIALIST_LABEL["momentum"],
        observation=observation,
        confidencePct=strength_confidence[momentum.strength],
        evidence=[momentum.detail],
        risks=risks,
        opportunities=opportunities,
    )


def _quant_turn(state: MarketIntelligenceState) -> MarketDebateTurn:
    quality = state.quality
    observation = f"Composite Market Quality reads {quality.score:.0f}/100 ({quality.tier.replace('_', ' ')}). {quality.historical_similarity}"
    risks = ["Small real sample size — this comparison is only as strong as how many real days are on record so far."] if "No real prior" in quality.historical_similarity or "occurred on 0" in quality.historical_similarity else []
    opportunities = [f"Volatility sits at the {state.volatility.percentile:.0f}th percentile of this symbol set's own real trailing range."]
    return MarketDebateTurn(specialist="quant", label=_SPECIALIST_LABEL["quant"], observation=observation, confidencePct=quality.confidence_pct, evidence=quality.evidence[:3], risks=risks, opportunities=opportunities)


def _risk_turn(state: MarketIntelligenceState) -> MarketDebateTurn:
    """Market-CONDITION risk only — session liquidity, quality tier, news
    volume. Never portfolio exposure or drawdown; see this module's own
    docstring for why that stays Sentinel/Guardian's job."""
    concerns: list[str] = []
    if state.session.current in ("closed", "ny_lunch_hour", "asian"):
        concerns.append(f"{state.session.label} is real, historically thinner liquidity — wider real slippage risk.")
    if state.news_risk.risk_level == "elevated":
        concerns.append(state.news_risk.detail)
    if state.institutional_activity.absorption_detected:
        concerns.append(f"Real absorption flagged on {', '.join(state.institutional_activity.symbols_flagged[:3])} — a real volume/price-divergence signal worth caution around, not confirmed order flow.")

    if state.quality.tier in ("poor", "avoid_trading"):
        observation = f"Market condition risk is real and elevated today — Market Quality reads {state.quality.tier.replace('_', ' ')}."
        risks = concerns or [f"Composite quality score is only {state.quality.score:.0f}/100."]
        opportunities = []
        confidence = max(10.0, 100.0 - state.quality.score)
    else:
        observation = f"No major real market-condition red flag today — Market Quality reads {state.quality.tier.replace('_', ' ')}."
        risks = concerns
        opportunities = [f"{state.session.label} — a real, comparatively favorable liquidity window."] if state.session.current in ("london_ny_overlap", "market_open") else []
        confidence = state.quality.score
    return MarketDebateTurn(specialist="risk", label=_SPECIALIST_LABEL["risk"], observation=observation, confidencePct=round(confidence, 1), evidence=[state.quality.reasoning], risks=risks, opportunities=opportunities)


def generate_market_debate(state: MarketIntelligenceState, *, debate_id: str) -> MarketDebate:
    turns = [_liquidity_turn(state), _price_action_turn(state), _momentum_turn(state), _quant_turn(state), _risk_turn(state)]
    avg_confidence = sum(t.confidence_pct for t in turns) / len(turns)
    summary = f"{len(turns)} independent specialist read(s) on today's {state.regime_label} — average confidence {avg_confidence:.0f}/100. Market Quality: {state.quality.tier.replace('_', ' ')} ({state.quality.score:.0f}/100)."
    return MarketDebate(id=debate_id, turns=turns, summary=summary, createdAt=_now_iso())
