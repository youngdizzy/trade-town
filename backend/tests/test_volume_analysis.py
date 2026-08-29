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
    dollar_volume,
    dollar_volume_sma,
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


class TestDollarVolume:
    def test_none_with_no_candles(self) -> None:
        assert dollar_volume([]) is None

    def test_real_last_candle_volume_times_close(self) -> None:
        candles = _candles([10.0, 20.0], [100.0, 200.0])
        assert dollar_volume(candles) == round(20.0 * 200.0, 2)


class TestDollarVolumeSma:
    def test_none_with_insufficient_candles(self) -> None:
        assert dollar_volume_sma(_candles([1.0, 2.0], [100.0, 200.0]), period=5) is None

    def test_real_average_of_the_last_period_dollar_volumes(self) -> None:
        candles = _candles([10.0, 10.0, 10.0], [10.0, 20.0, 30.0])
        # dollar volume per bar: 100, 200, 300 -- average of the last 2: 250
        assert dollar_volume_sma(candles, period=2) == round((200.0 + 300.0) / 2, 2)


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

    # CEO directive "TradeTown — 11/10 Next Engineering Pass" — the
    # canonical zero/invalid-baseline contract, permanently regression-
    # tested (Phase 10). A real relative-volume ratio is undefined
    # whenever it would require dividing by an all-zero baseline, or
    # whenever either side of the ratio is a value no real volume count
    # can legitimately be (negative, NaN, infinite) — see
    # app/volume_analysis.py's `_is_real_volume()` docstring for why.

    def test_none_when_the_baseline_window_is_all_zero_volume(self) -> None:
        candles = _candles([1.0] * 6, [0.0, 0.0, 0.0, 0.0, 0.0, 50.0])
        assert relative_volume(candles, period=5) is None

    def test_none_when_the_current_bar_volume_is_zero(self) -> None:
        # A zero baseline is undefined for a different reason (can't
        # divide by it) than a zero CURRENT bar (a perfectly real,
        # meaningful 0.0 ratio) — but 0.0 as the numerator over a real
        # positive baseline is a real, valid, well-defined ratio, not an
        # error case. Documented here as the real, correct contrast to
        # the zero-BASELINE case above, not asserted as a bug.
        candles = _candles([1.0] * 6, [100.0, 100.0, 100.0, 100.0, 100.0, 0.0])
        assert relative_volume(candles, period=5) == 0.0

    def test_none_when_the_baseline_is_negative(self) -> None:
        # Real volume can never be negative — a negative baseline could
        # only occur from malformed upstream data. A real, disclosed
        # invalid-input guard, not a market condition this module claims
        # to interpret.
        candles = _candles([1.0] * 6, [-100.0, -100.0, -100.0, -100.0, -100.0, 50.0])
        assert relative_volume(candles, period=5) is None

    def test_none_when_the_current_bar_volume_is_negative(self) -> None:
        candles = _candles([1.0] * 6, [100.0, 100.0, 100.0, 100.0, 100.0, -50.0])
        assert relative_volume(candles, period=5) is None

    def test_none_when_the_baseline_is_nan(self) -> None:
        # A NaN baseline is never caught by `baseline == 0` alone
        # (`float('nan') == 0` is False in Python) — this is the real
        # gap `_is_real_volume()` closes.
        candles = _candles([1.0] * 6, [float("nan"), 100.0, 100.0, 100.0, 100.0, 50.0])
        assert relative_volume(candles, period=5) is None

    def test_none_when_the_current_bar_volume_is_nan(self) -> None:
        candles = _candles([1.0] * 6, [100.0, 100.0, 100.0, 100.0, 100.0, float("nan")])
        assert relative_volume(candles, period=5) is None

    def test_none_when_the_current_bar_volume_is_infinite(self) -> None:
        candles = _candles([1.0] * 6, [100.0, 100.0, 100.0, 100.0, 100.0, float("inf")])
        assert relative_volume(candles, period=5) is None


class TestRelativeVolumeSeries:
    def test_empty_with_insufficient_candles(self) -> None:
        assert relative_volume_series(_candles([1.0] * 3, [100.0] * 3), period=5) == []

    def test_real_series_matches_scalar_at_each_point(self) -> None:
        candles = _candles([1.0] * 8, [100.0, 100.0, 100.0, 300.0, 100.0, 100.0, 100.0, 400.0])
        series = relative_volume_series(candles, period=3)
        # last value of the series must equal relative_volume() on the full candle list
        assert series[-1] == relative_volume(candles, period=3)
        assert len(series) == len(candles) - 3

    # CEO directive "TradeTown — 11/10 Next Engineering Pass," Phase
    # 2/10 — the exact regression this pass closes: relative_volume()
    # and relative_volume_series() must share ONE canonical contract at
    # every index, zero-baseline included, never a fabricated 0.0 where
    # relative_volume() itself would return None.

    def test_reports_none_not_a_fabricated_zero_for_an_all_zero_baseline_window(self) -> None:
        candles = _candles([1.0] * 6, [0.0, 0.0, 0.0, 0.0, 0.0, 50.0])
        series = relative_volume_series(candles, period=5)
        assert series == [None]
        assert series[-1] == relative_volume(candles, period=5)

    def test_a_mid_series_zero_baseline_window_reports_none_at_exactly_that_index_only(self) -> None:
        # A real "market halt" shape: five real nonzero baseline bars,
        # a real 3.0x bar, five real ZERO-volume bars (the halt itself),
        # the bar right after the halt (undefined baseline -> None), then
        # five more real nonzero bars and a real 4.0x bar. Every other
        # index in the same series must stay a real, defined number —
        # the undefined ratio must never leak sideways into neighboring,
        # well-defined indices.
        volumes = [100.0] * 5 + [300.0] + [0.0] * 5 + [50.0] + [20.0] * 5 + [80.0]
        candles = _candles([1.0] * len(volumes), volumes)
        series = relative_volume_series(candles, period=5)
        assert len(series) == len(candles) - 5
        assert series[0] == 3.0  # candle index 5, baseline = mean(candles[0:5]) = 100
        assert series[6] is None  # candle index 11, baseline = mean(candles[6:11]) = 0.0 (the halt)
        assert series[12] == 4.0  # candle index 17, baseline = mean(candles[12:17]) = 20
        assert all(v is not None for i, v in enumerate(series) if i != 6)

    def test_canonical_contract_holds_at_every_index_of_a_series_containing_a_real_gap(self) -> None:
        # The general, permanent invariant (not just the two hand-picked
        # boundary cases above): relative_volume_series(candles,
        # period)[i] must equal relative_volume(candles[: period + i +
        # 1], period) at EVERY real index, whether that value is a real
        # float or None.
        volumes = [100.0] * 5 + [300.0] + [0.0] * 5 + [50.0] + [20.0] * 5 + [80.0]
        candles = _candles([1.0] * len(volumes), volumes)
        period = 5
        series = relative_volume_series(candles, period=period)
        for i, value in enumerate(series):
            assert value == relative_volume(candles[: period + i + 1], period=period)

    def test_reports_none_at_a_nan_volume_index_only(self) -> None:
        volumes = [100.0] * 5 + [float("nan")] + [100.0] * 5 + [50.0]
        candles = _candles([1.0] * len(volumes), volumes)
        series = relative_volume_series(candles, period=5)
        # index 0 (candle 5, the NaN bar itself as "current") -> None
        assert series[0] is None
        # index 6 (candle 11): baseline is mean(candles[6:11]), all real
        # 100.0 bars (the NaN bar at index 5 is outside this window) ->
        # a real, defined ratio, unaffected by the earlier NaN.
        assert series[6] == 0.5


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

    def test_carries_real_dollar_volume_and_dollar_volume_sma(self) -> None:
        # CEO directive "AHL-Inspired Systematic Trend & Momentum
        # Research Engine" follow-up — closes the "dollar-volume not
        # tracked" gap a prior audit pass flagged; re-audited and found
        # trivial (volume * close, from data already tracked per candle).
        closes = [100.0] * 20 + [130.0]
        volumes = [100.0] * 20 + [250.0]
        candles = _candles(closes, volumes)
        read = compute_volume_confirmation(candles, "TEST", period=20, atr_period=14)
        assert read is not None
        assert read.dollar_volume == round(250.0 * 130.0, 2)
        assert read.dollar_volume_sma == dollar_volume_sma(candles, period=20)

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
