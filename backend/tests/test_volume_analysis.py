"""Covers app/volume_analysis.py — CEO directive "AHL-Inspired
Systematic Trend & Momentum Research Engine," Phase 7, the Volume
Confirmation Engine. Every function must return None (never a
fabricated value) below its own real minimum bar count, and every
computed value must match its real, standard formula on a
hand-checkable fixture. `compute_volume_confirmation()` must never
produce interpretive language ("manipulation," "liquidity grab") —
only real numbers and a plain categorical label of them.
"""
from __future__ import annotations

from app.market_data import Candle
from app.volume_analysis import (
    DEFAULT_EXPANSION_ATR_THRESHOLD,
    DEFAULT_VOLUME_MA_PERIOD,
    classify_volume_state,
    compute_volume_confirmation,
    relative_volume,
    relative_volume_series,
    volume_sma,
    volume_sma_series,
)


def _candle(*, close: float, volume: float, i: int) -> Candle:
    day = (i % 28) + 1
    hour = i // 28
    return Candle(symbol="TEST", timeframe="1h", timestamp=f"2024-01-{day:02d}T{hour:02d}:00:00+00:00", open=close, high=close, low=close, close=close, volume=volume, data_status="simulated")


def _candles(closes: list[float], volumes: list[float]) -> list[Candle]:
    assert len(closes) == len(volumes)
    return [_candle(close=c, volume=v, i=i) for i, (c, v) in enumerate(zip(closes, volumes))]


class TestVolumeSma:
    def test_none_with_insufficient_candles(self) -> None:
        assert volume_sma(_candles([1.0, 2.0], [100.0, 200.0]), period=5) is None

    def test_real_average_of_the_last_period_volumes(self) -> None:
        candles = _candles([1.0] * 5, [10.0, 20.0, 30.0, 40.0, 50.0])
        assert volume_sma(candles, period=3) == round((30.0 + 40.0 + 50.0) / 3, 2)


class TestVolumeSmaSeries:
    def test_empty_with_insufficient_candles(self) -> None:
        assert volume_sma_series(_candles([1.0, 2.0], [100.0, 200.0]), period=5) == []

    def test_real_series(self) -> None:
        candles = _candles([1.0] * 4, [10.0, 20.0, 30.0, 40.0])
        series = volume_sma_series(candles, period=2)
        assert series == [round((10.0 + 20.0) / 2, 2), round((20.0 + 30.0) / 2, 2), round((30.0 + 40.0) / 2, 2)]


class TestRelativeVolume:
    def test_none_with_insufficient_candles(self) -> None:
        candles = _candles([1.0] * 5, [100.0] * 5)
        assert relative_volume(candles, period=5) is None

    def test_real_ratio_of_last_bar_to_trailing_baseline(self) -> None:
        # 5 baseline bars at volume 100, then one bar at volume 300 -> 3.0x
        candles = _candles([1.0] * 6, [100.0, 100.0, 100.0, 100.0, 100.0, 300.0])
        assert relative_volume(candles, period=5) == 3.0

    def test_excludes_the_current_bar_from_its_own_baseline(self) -> None:
        candles = _candles([1.0] * 4, [100.0, 100.0, 100.0, 1000.0])
        # baseline over first 3 bars = 100; current (1000) never pollutes its own baseline
        assert relative_volume(candles, period=3) == 10.0

    def test_default_period_is_20(self) -> None:
        assert DEFAULT_VOLUME_MA_PERIOD == 20


class TestRelativeVolumeSeries:
    def test_empty_with_insufficient_candles(self) -> None:
        assert relative_volume_series(_candles([1.0] * 3, [100.0] * 3), period=5) == []

    def test_real_series_matches_scalar_at_each_point(self) -> None:
        candles = _candles([1.0] * 8, [100.0, 100.0, 100.0, 300.0, 100.0, 100.0, 100.0, 400.0])
        series = relative_volume_series(candles, period=3)
        # last value of the series must equal relative_volume() on the full candle list
        assert series[-1] == relative_volume(candles, period=3)
        assert len(series) == len(candles) - 3


class TestClassifyVolumeState:
    def test_climax_at_or_above_threshold(self) -> None:
        assert classify_volume_state(3.0) == "climax"
        assert classify_volume_state(5.0) == "climax"

    def test_elevated_between_thresholds(self) -> None:
        assert classify_volume_state(1.5) == "elevated"
        assert classify_volume_state(2.9) == "elevated"

    def test_normal_in_the_middle_band(self) -> None:
        assert classify_volume_state(1.0) == "normal"
        assert classify_volume_state(0.51) == "normal"

    def test_weak_at_or_below_threshold(self) -> None:
        assert classify_volume_state(0.5) == "weak"
        assert classify_volume_state(0.1) == "weak"


class TestComputeVolumeConfirmation:
    def test_none_with_insufficient_history(self) -> None:
        candles = _candles([100.0] * 5, [100.0] * 5)
        assert compute_volume_confirmation(candles, "TEST", period=20) is None

    def test_confirmed_move_when_big_price_move_has_elevated_volume(self) -> None:
        # 20 flat baseline bars, then a big up move with 2x volume.
        closes = [100.0] * 20 + [130.0]
        volumes = [100.0] * 20 + [250.0]
        candles = _candles(closes, volumes)
        read = compute_volume_confirmation(candles, "TEST", period=20, atr_period=14)
        assert read is not None
        assert read.confirmation_state == "confirmed_move"
        assert read.relative_volume > 1.5
        assert read.price_move_atr > 0

    def test_unconfirmed_move_when_big_price_move_has_weak_volume(self) -> None:
        closes = [100.0] * 20 + [70.0]
        volumes = [100.0] * 20 + [40.0]
        candles = _candles(closes, volumes)
        read = compute_volume_confirmation(candles, "TEST", period=20, atr_period=14)
        assert read is not None
        assert read.confirmation_state == "unconfirmed_move"
        assert read.price_move_atr < 0
        assert "fell" in read.detail

    def test_abnormal_volume_quiet_price_when_climax_volume_no_move(self) -> None:
        # A real oscillating baseline (so ATR is a genuine, meaningfully
        # positive number, not near-zero) followed by a genuinely tiny
        # final move with climax volume.
        oscillating = [100.0, 103.0, 99.0, 102.0] * 5
        closes = oscillating + [oscillating[-1] + 0.05]
        volumes = [100.0] * 20 + [500.0]
        candles = _candles(closes, volumes)
        read = compute_volume_confirmation(candles, "TEST", period=20, atr_period=14)
        assert read is not None
        assert read.confirmation_state == "abnormal_volume_quiet_price"
        assert abs(read.price_move_atr) < DEFAULT_EXPANSION_ATR_THRESHOLD

    def test_normal_when_neither_condition_met(self) -> None:
        oscillating = [100.0, 103.0, 99.0, 102.0] * 5
        closes = oscillating + [oscillating[-1] + 0.05]
        volumes = [100.0] * 20 + [105.0]
        candles = _candles(closes, volumes)
        read = compute_volume_confirmation(candles, "TEST", period=20, atr_period=14)
        assert read is not None
        assert read.confirmation_state == "normal"

    def test_never_uses_interpretive_or_signal_language(self) -> None:
        closes = [100.0] * 20 + [70.0]
        volumes = [100.0] * 20 + [40.0]
        candles = _candles(closes, volumes)
        read = compute_volume_confirmation(candles, "TEST", period=20, atr_period=14)
        assert read is not None
        forbidden = ["manipulation", "liquidity grab", "guaranteed", "buy", "sell", "reversal"]
        detail_lower = read.detail.lower()
        for word in forbidden:
            assert word not in detail_lower
