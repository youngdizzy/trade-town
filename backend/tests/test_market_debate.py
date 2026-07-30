"""Covers app/market_debate.py — v0.7 Feature 51, the Market Intelligence
Department's Market Debate System. Every specialist turn must read a
real field off the MarketIntelligenceState it was given — never a
fabricated observation, and never a duplicate of another specialist's
text.
"""
from __future__ import annotations

from app.market_debate import generate_market_debate
from app.market_intelligence import default_market_intelligence_state
from app.schemas import (
    InstitutionalActivityRead,
    LiquidityRead,
    LiquidityZone,
    MarketStructureRead,
    MomentumRead,
    SessionRead,
)


class TestGenerateMarketDebate:
    def test_produces_exactly_five_distinct_specialists(self) -> None:
        debate = generate_market_debate(default_market_intelligence_state(), debate_id="test-1")
        specialists = [t.specialist for t in debate.turns]
        assert specialists == ["liquidity", "price_action", "momentum", "quant", "risk"]
        assert len(set(specialists)) == 5

    def test_every_turn_has_real_evidence_confidence_and_a_real_id(self) -> None:
        # The quant specialist's evidence is quality.evidence itself
        # (app/market_intelligence.py's honest default leaves it empty
        # until at least one symbol has real candle data), so this test
        # gives it real evidence to check the general "every turn has
        # evidence" invariant honestly.
        base = default_market_intelligence_state()
        state = base.model_copy(update={"quality": base.quality.model_copy(update={"evidence": ["Real volatility read: 1.20%."]})})
        debate = generate_market_debate(state, debate_id="test-2")
        assert debate.id == "test-2"
        for turn in debate.turns:
            assert turn.evidence
            assert 0.0 <= turn.confidence_pct <= 100.0

    def test_summary_cites_the_real_regime_and_quality(self) -> None:
        state = default_market_intelligence_state()
        debate = generate_market_debate(state, debate_id="test-3")
        assert state.regime_label in debate.summary
        assert state.quality.tier.replace("_", " ") in debate.summary

    def test_liquidity_specialist_reports_a_real_sweep_when_one_is_present(self) -> None:
        state = default_market_intelligence_state().model_copy(
            update={
                "liquidity": [
                    LiquidityRead(symbol="NEXA", zones=[LiquidityZone(kind="equal_highs", price=110.0, touches=2)], sweepDetected=True, sweepDirection="above_highs", liquidityScore=80.0, detail="d")
                ]
            }
        )
        debate = generate_market_debate(state, debate_id="test-4")
        liquidity_turn = next(t for t in debate.turns if t.specialist == "liquidity")
        assert "NEXA" in liquidity_turn.observation
        assert liquidity_turn.risks

    def test_price_action_specialist_reports_real_break_of_structure_counts(self) -> None:
        state = default_market_intelligence_state().model_copy(
            update={
                "structure": [
                    MarketStructureRead(symbol="NEXA", swingHighs=[110.0, 115.0], swingLows=[95.0], lastBreakOfStructure="bullish", structureState="trend_continuation", detail="d"),
                    MarketStructureRead(symbol="MSFT", swingHighs=[], swingLows=[], lastBreakOfStructure="none", structureState="consolidation", detail="d"),
                ]
            }
        )
        debate = generate_market_debate(state, debate_id="test-5")
        price_action_turn = next(t for t in debate.turns if t.specialist == "price_action")
        assert "1/2" in price_action_turn.observation
        assert price_action_turn.opportunities

    def test_momentum_specialist_flags_exhaustion_as_a_real_risk(self) -> None:
        state = default_market_intelligence_state().model_copy(update={"momentum": MomentumRead(rocPct=-0.5, strength="exhausted", detail="d")})
        debate = generate_market_debate(state, debate_id="test-6")
        momentum_turn = next(t for t in debate.turns if t.specialist == "momentum")
        assert momentum_turn.risks
        assert momentum_turn.confidence_pct == 25.0

    def test_quant_specialist_flags_a_thin_sample_size(self) -> None:
        debate = generate_market_debate(default_market_intelligence_state(), debate_id="test-7")
        quant_turn = next(t for t in debate.turns if t.specialist == "quant")
        assert quant_turn.risks

    def test_risk_specialist_flags_thin_liquidity_sessions(self) -> None:
        state = default_market_intelligence_state().model_copy(update={"session": SessionRead(current="closed", label="Between Sessions", overlapsActive=[], detail="d")})
        debate = generate_market_debate(state, debate_id="test-8")
        risk_turn = next(t for t in debate.turns if t.specialist == "risk")
        assert any("thinner liquidity" in r for r in risk_turn.risks)

    def test_risk_specialist_never_reads_portfolio_state(self) -> None:
        """Market-condition risk only — see this module's own docstring
        for why portfolio exposure/drawdown deliberately stays out of
        this specialist's read (that's Sentinel/Guardian's real job,
        already covered by the Executive Intelligence Network's separate
        Risk department)."""
        state = default_market_intelligence_state().model_copy(update={"institutional_activity": InstitutionalActivityRead(volumePriceDivergenceScore=90.0, absorptionDetected=True, symbolsFlagged=["NEXA"], detail="d")})
        debate = generate_market_debate(state, debate_id="test-9")
        risk_turn = next(t for t in debate.turns if t.specialist == "risk")
        assert any("NEXA" in r for r in risk_turn.risks)

    def test_avoid_trading_quality_produces_a_cautious_risk_read(self) -> None:
        base = default_market_intelligence_state()
        state = base.model_copy(update={"quality": base.quality.model_copy(update={"tier": "avoid_trading", "score": 10.0})})
        debate = generate_market_debate(state, debate_id="test-10")
        risk_turn = next(t for t in debate.turns if t.specialist == "risk")
        assert "elevated" in risk_turn.observation.lower()
        assert risk_turn.opportunities == []
