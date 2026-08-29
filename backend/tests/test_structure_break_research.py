"""Covers app/structure_break_research.py — CEO directive "AHL-Inspired
Systematic Trend & Momentum Research Engine," Phase 10. The signal
series must reuse app/market_intelligence.py::compute_market_structure()'s
own real Break of Structure read exactly (never a second, drifting
definition), stay index-aligned one-to-one with the input candles, and
never look ahead of the index it's reporting at.
"""
from __future__ import annotations

from app.market_data import Candle
from app.structure_break_research import STRUCTURE_SCAN_WINDOW, change_of_character_signal_series, structure_break_signal_series


def _candle(i: int, *, open_: float, high: float, low: float, close: float, volume: float = 200_000.0, symbol: str = "NEXA") -> Candle:
    timestamp = f"2026-01-0{1 + i // 24}T{i % 24:02d}:00:00+00:00"
    return Candle(symbol=symbol, timeframe="1h", timestamp=timestamp, open=open_, high=high, low=low, close=close, volume=volume, data_status="simulated")


def _flat_candles(n: int) -> list[Candle]:
    return [_candle(i, open_=100.0, high=100.5, low=99.5, close=100.0) for i in range(n)]


def _bullish_bos_candles() -> list[Candle]:
    """The exact real fixture test_market_intelligence.py's own
    TestComputeMarketStructure uses for a confirmed bullish BOS —
    reused here (not re-derived) so this test proves the wrapper
    reports the identical real event the underlying detector already
    does."""
    candles = []
    for i in range(6):
        candles.append(_candle(i, open_=100 + i, high=101 + i, low=99 + i, close=100 + i))
    candles.append(_candle(6, open_=106, high=112, low=105, close=111))  # first swing high ~112
    for i in range(7, 13):
        candles.append(_candle(i, open_=110 - (i - 7), high=111 - (i - 7), low=108 - (i - 7), close=109 - (i - 7)))
    candles.append(_candle(13, open_=104, high=105, low=95, close=96))  # local low
    for i in range(14, 20):
        candles.append(_candle(i, open_=96 + (i - 14) * 3, high=98 + (i - 14) * 3, low=95 + (i - 14) * 3, close=97 + (i - 14) * 3))
    candles.append(_candle(20, open_=114, high=125, low=113, close=124))  # second swing high, higher than the first
    for i in range(21, 27):
        candles.append(_candle(i, open_=123 - (i - 21), high=124 - (i - 21), low=121 - (i - 21), close=122 - (i - 21)))
    return candles


def _bullish_choch_candles() -> list[Candle]:
    """A steep decline from 300 down to ~100 sets a strongly NEGATIVE
    real net trend over the full sample; the same real rising-swing-
    highs wiggle _bullish_bos_candles() uses is then appended, still
    forming a real bullish BOS locally — the two disagree, so this must
    read as a real bullish Change of Character (see
    MarketStructureRead.change_of_character's own docstring for the
    exact, disclosed definition)."""
    candles = []
    for i in range(10):
        price = 300 - i * 20
        candles.append(_candle(i, open_=price + 2, high=price + 3, low=price - 3, close=price))
    base_i = 10
    for i in range(6):
        candles.append(_candle(base_i + i, open_=100 + i, high=101 + i, low=99 + i, close=100 + i))
    candles.append(_candle(base_i + 6, open_=106, high=112, low=105, close=111))
    for i in range(7, 13):
        candles.append(_candle(base_i + i, open_=110 - (i - 7), high=111 - (i - 7), low=108 - (i - 7), close=109 - (i - 7)))
    candles.append(_candle(base_i + 13, open_=104, high=105, low=95, close=96))
    for i in range(14, 20):
        candles.append(_candle(base_i + i, open_=96 + (i - 14) * 3, high=98 + (i - 14) * 3, low=95 + (i - 14) * 3, close=97 + (i - 14) * 3))
    candles.append(_candle(base_i + 20, open_=114, high=125, low=113, close=124))
    for i in range(21, 27):
        candles.append(_candle(base_i + i, open_=123 - (i - 21), high=124 - (i - 21), low=121 - (i - 21), close=122 - (i - 21)))
    return candles


class TestStructureBreakSignalSeries:
    def test_index_aligned_one_to_one_with_candles(self) -> None:
        candles = _flat_candles(30)
        series = structure_break_signal_series(candles, "NEXA")
        assert len(series) == len(candles)

    def test_flat_series_never_signals(self) -> None:
        candles = _flat_candles(40)
        series = structure_break_signal_series(candles, "NEXA")
        assert all(v == 0.0 for v in series)

    def test_reports_a_real_bullish_break_of_structure(self) -> None:
        candles = _bullish_bos_candles()
        series = structure_break_signal_series(candles, "NEXA")
        assert any(v == 1.0 for v in series)

    def test_never_signals_before_the_second_swing_high_candle(self) -> None:
        candles = _bullish_bos_candles()
        series = structure_break_signal_series(candles, "NEXA")
        # The real second swing high (the one that actually creates the
        # BOS) is at index 20 — nothing before it can possibly know
        # about a break that hasn't happened yet.
        assert all(v == 0.0 for v in series[:20])

    def test_bounded_window_does_not_crash_on_a_long_series(self) -> None:
        candles = _flat_candles(STRUCTURE_SCAN_WINDOW * 5)
        series = structure_break_signal_series(candles, "NEXA")
        assert len(series) == len(candles)


class TestChangeOfCharacterSignalSeries:
    def test_index_aligned_one_to_one_with_candles(self) -> None:
        candles = _flat_candles(30)
        series = change_of_character_signal_series(candles, "NEXA")
        assert len(series) == len(candles)

    def test_flat_series_never_signals(self) -> None:
        candles = _flat_candles(40)
        series = change_of_character_signal_series(candles, "NEXA")
        assert all(v == 0.0 for v in series)

    def test_a_bullish_bos_agreeing_with_the_net_trend_never_signals_choch(self) -> None:
        # _bullish_bos_candles() nets UP overall, so its real bullish
        # BOS agrees with the real net trend — never a real CHoCH.
        candles = _bullish_bos_candles()
        series = change_of_character_signal_series(candles, "NEXA")
        assert all(v == 0.0 for v in series)

    def test_reports_a_real_bullish_change_of_character(self) -> None:
        candles = _bullish_choch_candles()
        series = change_of_character_signal_series(candles, "NEXA")
        assert any(v == 1.0 for v in series)

    def test_bounded_window_does_not_crash_on_a_long_series(self) -> None:
        candles = _flat_candles(STRUCTURE_SCAN_WINDOW * 5)
        series = change_of_character_signal_series(candles, "NEXA")
        assert len(series) == len(candles)
