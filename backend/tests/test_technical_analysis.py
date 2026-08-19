"""Covers app/technical_analysis.py — the bundled technical desk
briefing aggregating app/technical_indicators.py and app/
technical_patterns.py. Every field must be a direct, unmodified
pass-through of those already-tested functions.
"""
from __future__ import annotations

from app.market_data import Candle
from app.technical_analysis import compute_technical_analysis, compute_technical_indicators
from app.technical_indicators import rsi, sma


def _candle(*, close: float, i: int = 0) -> Candle:
    return Candle(symbol="TEST", timeframe="1h", timestamp=f"2024-01-01T{i:02d}:00:00+00:00", open=close, high=close + 1, low=close - 1, close=close, volume=100.0, data_status="simulated")


def _candles(n: int) -> list[Candle]:
    return [_candle(close=100.0 + i, i=i) for i in range(n)]


class TestComputeTechnicalIndicators:
    def test_insufficient_candles_reads_all_none(self) -> None:
        read = compute_technical_indicators("TEST", _candles(1))
        assert read.sma20 is None
        assert read.rsi14 is None
        assert read.macd_line is None
        assert read.stochastic_percent_k is None

    def test_values_match_the_underlying_indicator_functions_exactly(self) -> None:
        candles = _candles(30)
        read = compute_technical_indicators("TEST", candles)
        assert read.sma20 == sma(candles, period=20)
        assert read.rsi14 == rsi(candles)

    def test_symbol_is_passed_through(self) -> None:
        read = compute_technical_indicators("NEXA", _candles(5))
        assert read.symbol == "NEXA"


class TestComputeTechnicalAnalysis:
    def test_bundles_indicators_and_patterns_for_the_same_symbol(self) -> None:
        read = compute_technical_analysis("NEXA", _candles(30))
        assert read.symbol == "NEXA"
        assert read.indicators.symbol == "NEXA"
        assert read.swing_structure.symbol == "NEXA"
        assert read.fair_value_gaps.symbol == "NEXA"
        assert read.candlestick_patterns.symbol == "NEXA"
        assert read.fibonacci.symbol == "NEXA"
        assert read.order_block.symbol == "NEXA"

    def test_no_candles_reads_honest_empty_state_throughout(self) -> None:
        read = compute_technical_analysis("NEXA", [])
        assert read.indicators.sma20 is None
        assert read.swing_structure.labels == []
        assert read.fair_value_gaps.gaps == []
        assert read.candlestick_patterns.patterns == []
        assert read.fibonacci.levels == []
        assert read.order_block.direction == "none"
