"""Covers app/execution_quality.py — CEO directive "Next Professional
Trading Firm Phase," Priority 1 (Execution Realism). Slippage must be a
real, disclosed function of MarketIntelligenceState (never a random
number), always adverse to the trader, and a graceful, honest 0.0 when
no MarketIntelligenceState is available.
"""
from __future__ import annotations

from app.execution_quality import (
    BASE_SLIPPAGE_BPS,
    MAX_SLIPPAGE_BPS,
    apply_slippage,
    compute_slippage_bps,
)
from app.market_intelligence import default_market_intelligence_state
from app.schemas import LiquidityRead


def _state_with_quality(score: float):
    state = default_market_intelligence_state()
    return state.model_copy(update={"quality": state.quality.model_copy(update={"score": score})})


def _liquidity_read(symbol: str, liquidity_score: float) -> LiquidityRead:
    return LiquidityRead(symbol=symbol, zones=[], sweepDetected=False, sweepDirection="none", liquidityScore=liquidity_score, detail="test")


class TestComputeSlippageBps:
    def test_perfect_quality_and_no_liquidity_read_returns_the_base_rate(self) -> None:
        state = _state_with_quality(100.0)
        assert compute_slippage_bps(state, "AAPL") == BASE_SLIPPAGE_BPS

    def test_worst_quality_and_no_liquidity_read_returns_the_max_rate(self) -> None:
        state = _state_with_quality(0.0)
        assert compute_slippage_bps(state, "AAPL") == MAX_SLIPPAGE_BPS

    def test_mid_quality_and_no_liquidity_read_returns_the_midpoint(self) -> None:
        state = _state_with_quality(50.0)
        expected = round(BASE_SLIPPAGE_BPS + 0.5 * (MAX_SLIPPAGE_BPS - BASE_SLIPPAGE_BPS), 2)
        assert compute_slippage_bps(state, "AAPL") == expected

    def test_a_real_per_symbol_liquidity_read_refines_the_baseline(self) -> None:
        # Whole-watchlist quality is mediocre (50), but this specific
        # symbol has a perfect liquidity read (100) -- the combined
        # penalty should land below the quality-only midpoint.
        state = _state_with_quality(50.0).model_copy(update={"liquidity": [_liquidity_read("AAPL", 100.0)]})
        quality_only = compute_slippage_bps(_state_with_quality(50.0), "AAPL")
        assert compute_slippage_bps(state, "AAPL") < quality_only

    def test_a_liquidity_read_for_a_different_symbol_does_not_affect_this_ones_rate(self) -> None:
        state = _state_with_quality(50.0).model_copy(update={"liquidity": [_liquidity_read("MSFT", 100.0)]})
        quality_only = compute_slippage_bps(_state_with_quality(50.0), "AAPL")
        assert compute_slippage_bps(state, "AAPL") == quality_only

    def test_result_is_always_within_the_disclosed_bounds(self) -> None:
        for score in (0.0, 12.5, 50.0, 87.0, 100.0):
            rate = compute_slippage_bps(_state_with_quality(score), "AAPL")
            assert BASE_SLIPPAGE_BPS <= rate <= MAX_SLIPPAGE_BPS


class TestApplySlippage:
    def test_no_market_intelligence_leaves_price_unchanged_and_reports_zero_bps(self) -> None:
        fill_price, bps = apply_slippage(100.0, action_side="buy", market_intelligence=None, symbol="AAPL")
        assert fill_price == 100.0
        assert bps == 0.0

    def test_zero_or_negative_price_is_left_unchanged(self) -> None:
        state = _state_with_quality(50.0)
        fill_price, bps = apply_slippage(0.0, action_side="buy", market_intelligence=state, symbol="AAPL")
        assert fill_price == 0.0
        assert bps == 0.0

    def test_a_buy_fills_at_a_real_price_worse_than_signal_higher(self) -> None:
        state = _state_with_quality(50.0)
        fill_price, bps = apply_slippage(100.0, action_side="buy", market_intelligence=state, symbol="AAPL")
        assert fill_price > 100.0
        assert bps > 0.0

    def test_a_sell_fills_at_a_real_price_worse_than_signal_lower(self) -> None:
        state = _state_with_quality(50.0)
        fill_price, bps = apply_slippage(100.0, action_side="sell", market_intelligence=state, symbol="AAPL")
        assert fill_price < 100.0
        assert bps > 0.0

    def test_perfect_conditions_still_apply_a_real_nonzero_base_slippage(self) -> None:
        # Even the best realistic simulated conditions have some real
        # friction -- slippage is never fabricated as exactly zero for a
        # real fill under a real MarketIntelligenceState.
        state = _state_with_quality(100.0)
        fill_price, bps = apply_slippage(100.0, action_side="buy", market_intelligence=state, symbol="AAPL")
        assert bps == BASE_SLIPPAGE_BPS
        assert fill_price == round(100.0 * (1 + BASE_SLIPPAGE_BPS / 10_000.0), 4)
