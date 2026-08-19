"""Covers app/technical_indicators.py — CEO directive "Professional
Trading Firm — Market-Analysis Knowledge + Session Intelligence
Expansion," Phase 3. Every function must return None (never a fabricated
value computed from too little real history) below its own real minimum
bar count, and every computed value must match its real, standard
formula exactly on a hand-checkable fixture.
"""
from __future__ import annotations

from app.market_data import Candle
from app.technical_indicators import atr, atr_series, ema, macd, parabolic_sar, parabolic_sar_series, rsi, sma, sma_series, stochastic, supertrend, supertrend_series, vwap


def _candle(*, close: float, high: float | None = None, low: float | None = None, volume: float = 100.0, i: int = 0) -> Candle:
    high = high if high is not None else close
    low = low if low is not None else close
    return Candle(symbol="TEST", timeframe="1h", timestamp=f"2024-01-01T{i:02d}:00:00+00:00", open=close, high=high, low=low, close=close, volume=volume, data_status="simulated")


def _candles(closes: list[float]) -> list[Candle]:
    return [_candle(close=c, i=i) for i, c in enumerate(closes)]


class TestSma:
    def test_none_with_insufficient_candles(self) -> None:
        assert sma(_candles([1.0, 2.0]), period=5) is None

    def test_real_average_of_the_last_period_closes(self) -> None:
        candles = _candles([10.0, 20.0, 30.0, 40.0, 50.0])
        assert sma(candles, period=3) == round((30.0 + 40.0 + 50.0) / 3, 4)

    def test_uses_only_the_trailing_window_not_the_whole_series(self) -> None:
        candles = _candles([1000.0, 1000.0, 10.0, 20.0, 30.0])
        assert sma(candles, period=3) == round((10.0 + 20.0 + 30.0) / 3, 4)


class TestSmaSeries:
    def test_empty_with_insufficient_candles(self) -> None:
        assert sma_series(_candles([1.0, 2.0]), period=5) == []

    def test_last_value_matches_sma(self) -> None:
        candles = _candles([10.0 + i for i in range(20)])
        series = sma_series(candles, period=5)
        assert series
        assert series[-1] == sma(candles, period=5)

    def test_first_value_matches_sma_of_the_real_seed_window(self) -> None:
        candles = _candles([10.0 + i for i in range(20)])
        series = sma_series(candles, period=5)
        assert series[0] == sma(candles[:5], period=5)


class TestEma:
    def test_none_with_insufficient_candles(self) -> None:
        assert ema(_candles([1.0, 2.0]), period=5) is None

    def test_seeds_from_a_real_sma_of_the_first_period_closes(self) -> None:
        # With exactly `period` candles, EMA's one real seed value must
        # equal a plain SMA of those same candles.
        candles = _candles([10.0, 20.0, 30.0])
        assert ema(candles, period=3) == sma(candles, period=3)

    def test_weights_recent_closes_more_than_sma_does(self) -> None:
        # A sharp recent jump should move EMA further than SMA, since EMA
        # weights the latest bar more heavily -- a real, checkable
        # structural property, not a magic number. Needs more than
        # `period` candles: with exactly `period` candles EMA's only
        # value is its real SMA-seed itself, with no smoothing step yet
        # applied to diverge from a plain trailing SMA.
        candles = _candles([10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 100.0])
        sma_value = sma(candles, period=5)
        ema_value = ema(candles, period=5)
        assert sma_value is not None and ema_value is not None
        assert ema_value > sma_value


class TestRsi:
    def test_none_with_insufficient_candles(self) -> None:
        assert rsi(_candles([1.0] * 5), period=14) is None

    def test_all_gains_reads_100(self) -> None:
        # Strictly rising closes -> zero average loss -> RSI must read
        # the real, defined boundary case of 100, never a division error.
        candles = _candles([float(i) for i in range(1, 16)])
        assert rsi(candles, period=14) == 100.0

    def test_all_losses_reads_near_zero(self) -> None:
        candles = _candles([float(i) for i in range(15, 0, -1)])
        result = rsi(candles, period=14)
        assert result is not None
        assert result < 1.0

    def test_flat_series_reads_neutral_50(self) -> None:
        candles = _candles([10.0] * 15)
        assert rsi(candles, period=14) == 50.0


class TestMacd:
    def test_none_with_insufficient_candles(self) -> None:
        assert macd(_candles([1.0] * 10), fast=12, slow=26, signal=9) is None

    def test_real_histogram_is_macd_line_minus_signal_line(self) -> None:
        candles = _candles([10.0 + i * 0.5 for i in range(60)])
        result = macd(candles, fast=12, slow=26, signal=9)
        assert result is not None
        macd_line, signal_line, histogram = result
        assert histogram == round(macd_line - signal_line, 4)

    def test_steady_uptrend_produces_a_positive_macd_line(self) -> None:
        # Fast EMA (12) should sit above slow EMA (26) during a steady
        # real uptrend -- a real, checkable structural property.
        candles = _candles([10.0 + i * 0.5 for i in range(60)])
        result = macd(candles, fast=12, slow=26, signal=9)
        assert result is not None
        macd_line, _signal_line, _histogram = result
        assert macd_line > 0


class TestStochastic:
    def test_none_with_insufficient_candles(self) -> None:
        assert stochastic(_candles([1.0] * 5), period=14, smoothing=3) is None

    def test_close_at_the_periods_high_reads_100(self) -> None:
        candles = [_candle(close=10.0, high=10.0, low=5.0, i=i) for i in range(13)]
        candles.append(_candle(close=20.0, high=20.0, low=5.0, i=13))
        result = stochastic(candles, period=14, smoothing=1)
        assert result is not None
        percent_k, _percent_d = result
        assert percent_k == 100.0

    def test_close_at_the_periods_low_reads_0(self) -> None:
        candles = [_candle(close=10.0, high=15.0, low=10.0, i=i) for i in range(13)]
        candles.append(_candle(close=5.0, high=15.0, low=5.0, i=13))
        result = stochastic(candles, period=14, smoothing=1)
        assert result is not None
        percent_k, _percent_d = result
        assert percent_k == 0.0


class TestAtr:
    def test_none_with_insufficient_candles(self) -> None:
        assert atr(_candles([1.0] * 3), period=14) is None

    def test_real_average_true_range_over_a_flat_series(self) -> None:
        # No gaps, constant 2-point high-low range every bar -> ATR must
        # equal exactly that range.
        candles = [_candle(close=10.0, high=11.0, low=9.0, i=i) for i in range(15)]
        assert atr(candles, period=14) == 2.0

    def test_a_real_gap_widens_true_range_beyond_the_bars_own_high_low(self) -> None:
        candles = [_candle(close=10.0, high=10.5, low=9.5, i=i) for i in range(14)]
        # A real gap-up open: this bar's own high-low range is small, but
        # true range must capture the real distance from the prior close.
        candles.append(_candle(close=20.0, high=20.5, low=19.5, i=14))
        result = atr(candles, period=14)
        assert result is not None
        assert result > 1.0


class TestAtrSeries:
    def test_empty_with_insufficient_candles(self) -> None:
        assert atr_series(_candles([1.0] * 3), period=14) == []

    def test_last_value_matches_atr(self) -> None:
        candles = [_candle(close=10.0, high=11.0, low=9.0, i=i) for i in range(20)]
        series = atr_series(candles, period=14)
        assert series
        assert series[-1] == atr(candles, period=14)

    def test_one_value_per_candle_from_the_real_minimum_window_onward(self) -> None:
        candles = [_candle(close=10.0, high=11.0, low=9.0, i=i) for i in range(20)]
        series = atr_series(candles, period=14)
        assert len(series) == len(candles) - 14

    def test_real_value_at_an_earlier_point_matches_atr_of_the_series_up_to_that_point(self) -> None:
        candles = [_candle(close=10.0 + i * 0.3, high=10.0 + i * 0.3 + 1, low=10.0 + i * 0.3 - 1, i=i) for i in range(30)]
        series = atr_series(candles, period=14)
        # series[0] is ATR "as of" candle index 14 -- must equal atr() computed over just that prefix.
        assert series[0] == atr(candles[:15], period=14)


class TestVwap:
    def test_none_with_empty_candles(self) -> None:
        assert vwap([]) is None

    def test_none_with_zero_total_volume(self) -> None:
        candles = [_candle(close=10.0, volume=0.0, i=0)]
        assert vwap(candles) is None

    def test_real_volume_weighted_average(self) -> None:
        # Two bars, identical typical price (10.0) but different volume
        # -- VWAP must still land on 10.0 since both bars agree on price.
        candles = [_candle(close=10.0, high=10.0, low=10.0, volume=100.0, i=0), _candle(close=10.0, high=10.0, low=10.0, volume=900.0, i=1)]
        assert vwap(candles) == 10.0

    def test_higher_volume_bar_pulls_vwap_toward_its_own_price(self) -> None:
        low_vol = _candle(close=10.0, high=10.0, low=10.0, volume=10.0, i=0)
        high_vol = _candle(close=20.0, high=20.0, low=20.0, volume=990.0, i=1)
        result = vwap([low_vol, high_vol])
        assert result is not None
        assert result > 19.0  # pulled close to the high-volume bar's price


# Hand-traced fixture for TestParabolicSar — the real Wilder recurrence
# worked out by hand bar-by-bar (see the CEO directive "Next Research +
# Validation Pass" implementation notes), not derived by running the
# function against itself.
def _sar_candles() -> list[Candle]:
    rows = [
        (10.0, 8.0, 9.0),
        (11.0, 9.0, 10.5),
        (12.0, 10.0, 11.5),
        (13.0, 11.0, 12.5),
        (11.5, 9.0, 9.5),
        (8.5, 7.0, 7.5),
    ]
    return [_candle(high=h, low=lo, close=c, i=i) for i, (h, lo, c) in enumerate(rows)]


class TestParabolicSar:
    def test_empty_with_fewer_than_two_candles(self) -> None:
        assert parabolic_sar_series(_candles([1.0])) == []
        assert parabolic_sar(_candles([1.0])) is None

    def test_real_hand_traced_recurrence_including_a_real_trend_flip(self) -> None:
        series = parabolic_sar_series(_sar_candles())
        # Hand-traced expected (sar_value, trend) pairs for candles[1..5] —
        # see the module's own worked derivation. The acceleration factor
        # climbs 0.02 -> 0.04 -> 0.06 -> 0.08 while new extreme points are
        # made each bar, then bar 5's real low (7.0) breaks below the
        # accumulated SAR (8.971...), flipping the trend to "down" and
        # resetting SAR to the old extreme point (13.0).
        assert series == [
            (8.0, "up"),
            (8.0, "up"),
            (8.24, "up"),
            (8.6208, "up"),
            (13.0, "down"),
        ]

    def test_last_value_matches_the_series(self) -> None:
        candles = _sar_candles()
        assert parabolic_sar(candles) == parabolic_sar_series(candles)[-1]

    def test_sar_never_penetrates_the_real_recent_low_high_it_is_clamped_against(self) -> None:
        # Structural invariant, not just the one hand-traced fixture: in
        # an uptrend, SAR must never sit above the low of either of the
        # last two real bars (the real, standard non-penetration clamp).
        candles = _sar_candles()
        series = parabolic_sar_series(candles)
        for i in range(2, len(candles)):
            sar_value, trend = series[i - 1]
            if trend == "up":
                assert sar_value <= min(candles[i - 1].low, candles[i - 2].low) + 1e-6


class TestSupertrend:
    def test_empty_with_insufficient_candles(self) -> None:
        assert supertrend_series(_candles([1.0, 2.0])) == []
        assert supertrend(_candles([1.0, 2.0])) is None

    def test_real_hand_traced_bands_including_a_real_trend_flip(self) -> None:
        rows = [
            (10.0, 8.0, 9.0),
            (11.0, 9.0, 10.0),
            (12.0, 10.0, 11.0),
            (10.0, 8.0, 8.5),
            (7.0, 5.0, 5.5),
        ]
        candles = [_candle(high=h, low=lo, close=c, i=i) for i, (h, lo, c) in enumerate(rows)]
        series = supertrend_series(candles, period=2, multiplier=2.0)
        # Hand-traced against the real ATR(period=2) series [2.0, 2.5, 3.25]
        # this fixture produces — see the module's own worked derivation.
        assert series == [(7.0, "up"), (7.0, "up"), (12.5, "down")]

    def test_last_value_matches_the_series(self) -> None:
        # Enough real bars for a real ATR(10) window to exist.
        candles = [_candle(high=c.high, low=c.low, close=c.close, i=i) for i, c in enumerate(_sar_candles() * 3)]
        assert supertrend(candles) == supertrend_series(candles)[-1]
