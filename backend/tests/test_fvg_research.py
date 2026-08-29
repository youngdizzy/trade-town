"""Covers app/fvg_research.py — CEO directive "AHL-Inspired Systematic
Trend & Momentum Research Engine," Phase 10. The signal series must
reuse app/technical_patterns.py::detect_fair_value_gaps()'s own real
3-candle FVG detector exactly (never a second, drifting definition),
stay index-aligned one-to-one with the input candles, and never look
ahead of the index it's reporting at.
"""
from __future__ import annotations

from app.fvg_research import FVG_SCAN_WINDOW, fvg_signal_series
from app.market_data import Candle


def _candle(i: int, *, open_: float, high: float, low: float, close: float, volume: float = 200_000.0, symbol: str = "NEXA") -> Candle:
    timestamp = f"2026-01-0{1 + i // 24}T{i % 24:02d}:00:00+00:00"
    return Candle(symbol=symbol, timeframe="1h", timestamp=timestamp, open=open_, high=high, low=low, close=close, volume=volume, data_status="simulated")


def _flat_candles(n: int) -> list[Candle]:
    return [_candle(i, open_=100.0, high=100.5, low=99.5, close=100.0) for i in range(n)]


def _bullish_fvg_candles() -> list[Candle]:
    """The exact real fixture test_technical_patterns.py's own
    TestDetectFairValueGaps uses for a confirmed bullish FVG — reused
    here (not re-derived) so this test proves the wrapper reports the
    identical real event the underlying detector already does."""
    return [
        _candle(0, open_=100, high=101, low=99, close=100.5),
        _candle(1, open_=105, high=106, low=104, close=105.5),
        _candle(2, open_=108, high=109, low=107, close=108.5),
    ]


def _bearish_fvg_candles() -> list[Candle]:
    return [
        _candle(0, open_=109, high=110, low=108, close=108.5),
        _candle(1, open_=104, high=105, low=103, close=103.5),
        _candle(2, open_=101, high=102, low=100, close=100.5),
    ]


class TestFvgSignalSeries:
    def test_index_aligned_one_to_one_with_candles(self) -> None:
        candles = _flat_candles(30)
        series = fvg_signal_series(candles, "NEXA")
        assert len(series) == len(candles)

    def test_flat_series_never_signals(self) -> None:
        candles = _flat_candles(40)
        series = fvg_signal_series(candles, "NEXA")
        assert all(v == 0.0 for v in series)

    def test_reports_a_real_bullish_fvg(self) -> None:
        candles = _bullish_fvg_candles()
        series = fvg_signal_series(candles, "NEXA")
        assert series[-1] == 1.0

    def test_reports_a_real_bearish_fvg(self) -> None:
        candles = _bearish_fvg_candles()
        series = fvg_signal_series(candles, "NEXA")
        assert series[-1] == -1.0

    def test_never_signals_before_the_third_candle(self) -> None:
        candles = _bullish_fvg_candles()
        series = fvg_signal_series(candles, "NEXA")
        # The real gap can't exist until its own third real candle closes.
        assert series[0] == 0.0
        assert series[1] == 0.0

    def test_bounded_window_does_not_crash_on_a_long_series(self) -> None:
        candles = _flat_candles(FVG_SCAN_WINDOW * 5)
        series = fvg_signal_series(candles, "NEXA")
        assert len(series) == len(candles)
