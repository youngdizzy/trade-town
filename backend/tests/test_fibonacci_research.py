"""Covers app/fibonacci_research.py — CEO directive "AHL-Inspired
Systematic Trend & Momentum Research Engine," Phase 10. The signal
series must reuse app/technical_patterns.py::compute_fibonacci_levels()'s
own real 61.8% retracement price exactly (never a second, drifting
definition), stay index-aligned one-to-one with the input candles, never
look ahead of the index it's reporting at, and never fabricate a `0.0`
placeholder price before enough real swing history exists.
"""
from __future__ import annotations

from app.fibonacci_research import FIBONACCI_SCAN_WINDOW, fibonacci_618_level_series
from app.market_data import Candle
from app.technical_patterns import compute_fibonacci_levels


def _candle(i: int, *, open_: float, high: float, low: float, close: float, volume: float = 200_000.0, symbol: str = "NEXA") -> Candle:
    timestamp = f"2026-01-0{1 + i // 24}T{i % 24:02d}:00:00+00:00"
    return Candle(symbol=symbol, timeframe="1h", timestamp=timestamp, open=open_, high=high, low=low, close=close, volume=volume, data_status="simulated")


def _flat_candles(n: int) -> list[Candle]:
    return [_candle(i, open_=100.0, high=100.5, low=99.5, close=100.0) for i in range(n)]


def _real_swing_candles() -> list[Candle]:
    """The exact real fixture test_market_intelligence.py's own
    TestComputeMarketStructure uses for a confirmed real swing high/low
    pair — reused here (not re-derived) so this test proves the wrapper
    reports the identical real level compute_fibonacci_levels() itself
    would compute."""
    candles = []
    for i in range(6):
        candles.append(_candle(i, open_=100 + i, high=101 + i, low=99 + i, close=100 + i))
    candles.append(_candle(6, open_=106, high=112, low=105, close=111))
    for i in range(7, 13):
        candles.append(_candle(i, open_=110 - (i - 7), high=111 - (i - 7), low=108 - (i - 7), close=109 - (i - 7)))
    candles.append(_candle(13, open_=104, high=105, low=95, close=96))
    for i in range(14, 20):
        candles.append(_candle(i, open_=96 + (i - 14) * 3, high=98 + (i - 14) * 3, low=95 + (i - 14) * 3, close=97 + (i - 14) * 3))
    candles.append(_candle(20, open_=114, high=125, low=113, close=124))
    for i in range(21, 27):
        candles.append(_candle(i, open_=123 - (i - 21), high=124 - (i - 21), low=121 - (i - 21), close=122 - (i - 21)))
    return candles


class TestFibonacci618LevelSeries:
    def test_index_aligned_one_to_one_with_candles(self) -> None:
        candles = _flat_candles(30)
        series = fibonacci_618_level_series(candles, "NEXA")
        assert len(series) == len(candles)

    def test_too_short_a_history_stays_none_never_a_fabricated_zero(self) -> None:
        # Below compute_market_structure()'s own real minimum
        # (SWING_LOOKBACK * 2 + 2 = 8 bars) there is no real swing high
        # or low to compute a level from at all — every point must stay
        # None, never a fabricated 0.0.
        candles = _flat_candles(4)
        series = fibonacci_618_level_series(candles, "NEXA")
        assert all(v is None for v in series)

    def test_none_before_a_real_swing_high_and_low_both_exist(self) -> None:
        candles = _real_swing_candles()
        series = fibonacci_618_level_series(candles, "NEXA")
        assert series[0] is None

    def test_reports_the_exact_same_real_level_the_underlying_detector_computes(self) -> None:
        candles = _real_swing_candles()
        series = fibonacci_618_level_series(candles, "NEXA")
        last_value = series[-1]
        assert last_value is not None
        direct_read = compute_fibonacci_levels("NEXA", candles)
        expected = next(lv.price for lv in direct_read.levels if lv.ratio == 0.618)
        assert last_value == expected

    def test_bounded_window_does_not_crash_on_a_long_series(self) -> None:
        candles = _flat_candles(FIBONACCI_SCAN_WINDOW * 5)
        series = fibonacci_618_level_series(candles, "NEXA")
        assert len(series) == len(candles)
