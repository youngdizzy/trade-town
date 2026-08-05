"""app/regime_reconciliation.py — v0.7 Design Bible Chapter 65, Market
Regime Detection & Adaptive Strategy Engine.

RESEARCHED FIRST. This codebase already has two independent, real,
indicator-driven regime classifiers: app/market_environment.py's
coarse 5-way threshold classifier, and app/market_intelligence.py's
richer 13-way multi-factor classifier (the latter already computing a
real Regime Confidence Score via MarketQualityScore.confidence_pct).
Neither reads the other, and neither is CEO-configurable. That is the
one real gap this module closes for its first honest slice: a
reconciled, CEO-facing read combining both, plus a transparent
categorical posture recommendation — never a third, competing
classifier, and never an automatic write to any real RiskLimits field.

REUSES, DOES NOT DUPLICATE. `agreement` reuses
app/market_intelligence.py's own real REGIME_CONSISTENCY_MAP — the
exact same mapping the Learning Loop already uses to grade a prior
day's regime call against what actually happened — rather than
inventing a second, competing definition of "these two regimes agree."

HONESTY BOUNDARY (see Chapter 65's own Safety Systems / Ownership
sections): `posture` is read-only, informational text. It is never
applied to any RiskLimits field automatically, and this module has no
write path at all — Position Sizing, the Trade Gatekeeper, and Capital
Priority remain exclusively Chapters 57/58/59's own domain.
"""
from __future__ import annotations

from app.market_intelligence import REGIME_CONSISTENCY_MAP
from app.schemas import (
    MarketEnvironmentState,
    MarketIntelligenceState,
    MarketQualityTier,
    RegimeAgreement,
    RegimePosture,
    RegimeReconciliation,
)

# A real, transparent, three-way read off the same MarketQualityScore
# tier every trade-time gate already reads (app/gatekeeper.py,
# app/opportunity_gatekeeper.py) — never a new score, never a hidden
# weighting. "opportunistic" additionally requires real confidence
# above this stated threshold, not just a good tier alone, so a
# good-but-uncertain read doesn't overstate itself.
OPPORTUNISTIC_MIN_CONFIDENCE_PCT = 70.0

_CAUTIOUS_TIERS: frozenset[MarketQualityTier] = frozenset({"poor", "avoid_trading"})
_OPPORTUNISTIC_ELIGIBLE_TIERS: frozenset[MarketQualityTier] = frozenset({"excellent", "good"})


def _posture(tier: MarketQualityTier, confidence_pct: float) -> tuple[RegimePosture, str]:
    if tier in _CAUTIOUS_TIERS:
        return "cautious", f"Market Quality reads {tier.replace('_', ' ')} — a real signal worth weighing before sizing up."
    if tier in _OPPORTUNISTIC_ELIGIBLE_TIERS and confidence_pct >= OPPORTUNISTIC_MIN_CONFIDENCE_PCT:
        return "opportunistic", f"Market Quality reads {tier.replace('_', ' ')} with {confidence_pct:.0f}% confidence — real evidence supports leaning in."
    if tier in _OPPORTUNISTIC_ELIGIBLE_TIERS:
        return "normal", f"Market Quality reads {tier.replace('_', ' ')}, but confidence is only {confidence_pct:.0f}% — not yet enough to call this opportunistic."
    return "normal", f"Market Quality reads {tier.replace('_', ' ')} — no real reason to lean cautious or aggressive right now."


def _agreement(environment: MarketEnvironmentState, intelligence: MarketIntelligenceState) -> tuple[RegimeAgreement, str]:
    acceptable = REGIME_CONSISTENCY_MAP[intelligence.regime]
    if environment.current in acceptable:
        return "aligned", f"The two live regime reads agree: {environment.label} and {intelligence.regime_label} point the same direction."
    return "diverging", f"The two live regime reads disagree: {environment.label} vs. {intelligence.regime_label} — worth a closer look before trusting either alone."


def compute_regime_reconciliation(environment: MarketEnvironmentState, intelligence: MarketIntelligenceState) -> RegimeReconciliation:
    """The real reconciliation read — computed fresh per request, never
    persisted, the same convention every other on-demand recommendation
    in this codebase already follows (Chapter 64's GoalPriority/
    GoalAllocation, Chapter 63's Benchmarking)."""
    posture, posture_rationale = _posture(intelligence.quality.tier, intelligence.quality.confidence_pct)
    agreement, agreement_rationale = _agreement(environment, intelligence)
    rationale = f"{agreement_rationale} {posture_rationale}"
    return RegimeReconciliation(
        environmentRegime=environment.current,
        environmentLabel=environment.label,
        intelligenceRegime=intelligence.regime,
        intelligenceLabel=intelligence.regime_label,
        qualityTier=intelligence.quality.tier,
        confidencePct=intelligence.quality.confidence_pct,
        agreement=agreement,
        posture=posture,
        rationale=rationale,
    )
