"""Covers app/regime_reconciliation.py — v0.7 Design Bible Chapter 65's
smallest real slice: reconciling the two already-real regime engines
(app/market_environment.py's 5-way, app/market_intelligence.py's
13-way) into one CEO-facing read, plus a read-only posture
recommendation. Every field here traces back to an already-real value
(MarketEnvironmentState/MarketIntelligenceState) — nothing invented.
"""
from __future__ import annotations

from typing import get_args

from app.market_environment import default_market_environment
from app.market_intelligence import REGIME_CONSISTENCY_MAP, default_market_intelligence_state
from app.regime_reconciliation import OPPORTUNISTIC_MIN_CONFIDENCE_PCT, compute_regime_reconciliation
from app.schemas import MarketIntelligenceRegime


class TestRegimeConsistencyMapCompleteness:
    def test_every_real_intelligence_regime_has_a_real_consistency_entry(self) -> None:
        # Guards against a future new MarketIntelligenceRegime value
        # silently KeyError-ing compute_regime_reconciliation() —
        # every real regime must map to at least one real environment
        # regime, never left undefined.
        for regime in get_args(MarketIntelligenceRegime):
            assert regime in REGIME_CONSISTENCY_MAP
            assert len(REGIME_CONSISTENCY_MAP[regime]) > 0


class TestComputeRegimeReconciliation:
    def test_default_states_are_aligned_and_normal(self) -> None:
        environment = default_market_environment()
        intelligence = default_market_intelligence_state()
        result = compute_regime_reconciliation(environment, intelligence)
        assert result.environment_regime == "sideways"
        assert result.intelligence_regime == "sideways_range"
        assert result.quality_tier == "average"
        assert result.agreement == "aligned"
        assert result.posture == "normal"
        assert result.confidence_pct == intelligence.quality.confidence_pct

    def test_diverging_when_the_two_engines_disagree(self) -> None:
        environment = default_market_environment().model_copy(update={"current": "bear", "label": "Bear Market"})
        intelligence = default_market_intelligence_state()  # regime="sideways_range"
        result = compute_regime_reconciliation(environment, intelligence)
        assert result.agreement == "diverging"
        assert "disagree" in result.rationale

    def test_avoid_trading_tier_is_always_cautious_regardless_of_confidence(self) -> None:
        environment = default_market_environment()
        intelligence = default_market_intelligence_state()
        intelligence = intelligence.model_copy(update={"quality": intelligence.quality.model_copy(update={"tier": "avoid_trading", "confidence_pct": 90.0})})
        result = compute_regime_reconciliation(environment, intelligence)
        assert result.posture == "cautious"

    def test_poor_tier_is_cautious(self) -> None:
        environment = default_market_environment()
        intelligence = default_market_intelligence_state()
        intelligence = intelligence.model_copy(update={"quality": intelligence.quality.model_copy(update={"tier": "poor"})})
        result = compute_regime_reconciliation(environment, intelligence)
        assert result.posture == "cautious"

    def test_excellent_tier_with_high_confidence_is_opportunistic(self) -> None:
        environment = default_market_environment()
        intelligence = default_market_intelligence_state()
        intelligence = intelligence.model_copy(
            update={"quality": intelligence.quality.model_copy(update={"tier": "excellent", "confidence_pct": OPPORTUNISTIC_MIN_CONFIDENCE_PCT})}
        )
        result = compute_regime_reconciliation(environment, intelligence)
        assert result.posture == "opportunistic"

    def test_good_tier_with_low_confidence_stays_normal_not_opportunistic(self) -> None:
        environment = default_market_environment()
        intelligence = default_market_intelligence_state()
        intelligence = intelligence.model_copy(
            update={"quality": intelligence.quality.model_copy(update={"tier": "good", "confidence_pct": OPPORTUNISTIC_MIN_CONFIDENCE_PCT - 1})}
        )
        result = compute_regime_reconciliation(environment, intelligence)
        assert result.posture == "normal"

    def test_rationale_mentions_both_the_agreement_and_the_posture(self) -> None:
        environment = default_market_environment()
        intelligence = default_market_intelligence_state()
        result = compute_regime_reconciliation(environment, intelligence)
        assert environment.label in result.rationale
        assert intelligence.regime_label in result.rationale
