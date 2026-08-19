"""Covers app/backtest_primitives.py — the one authoritative Chandelier
Stop / exit-simulation implementation shared by app/ema_pullback_
research.py and app/strategy_engine.py. See tests/test_ema_pullback_
research.py for the original, still-passing coverage of this same real
math via that module's own fixtures; this file covers the shared
primitives directly and in isolation.
"""
from __future__ import annotations

from app.backtest_primitives import atr_at, chandelier_stop, ema_at, simulate_exit
from app.market_data import Candle


def _candle(i: int, o: float, h: float, low: float, c: float) -> Candle:
    return Candle(symbol="TEST", timeframe="1h", timestamp=f"2024-01-{1 + i // 24:02d}T{i % 24:02d}:00:00+00:00", open=o, high=h, low=low, close=c, volume=100.0, data_status="simulated")


class TestAtrAt:
    def test_none_out_of_range(self) -> None:
        assert atr_at([1.0, 2.0, 3.0], period=14, index=5) is None

    def test_real_lookup_at_the_aligned_index(self) -> None:
        # atr_series values start at real candle index `period`.
        values = [10.0, 11.0, 12.0]
        assert atr_at(values, period=14, index=14) == 10.0
        assert atr_at(values, period=14, index=16) == 12.0


class TestEmaAt:
    def test_none_out_of_range(self) -> None:
        assert ema_at([1.0, 2.0, 3.0], period=50, index=5) is None

    def test_real_lookup_at_the_aligned_index(self) -> None:
        # ema_series values start at real candle index `period - 1`.
        values = [10.0, 11.0, 12.0]
        assert ema_at(values, period=50, index=49) == 10.0
        assert ema_at(values, period=50, index=51) == 12.0


class TestChandelierStop:
    def test_none_with_no_real_atr_history(self) -> None:
        candles = [_candle(i, 100, 101, 99, 100) for i in range(5)]
        assert chandelier_stop(candles, [], entry_index=3, direction="long", atr_period=22, atr_multiplier=3.0) is None

    def test_long_stop_sits_below_the_real_highest_high(self) -> None:
        candles = [_candle(i, 100, 105 + i, 95, 100) for i in range(25)]
        atr_vals = [2.0] * 25
        stop = chandelier_stop(candles, atr_vals, entry_index=24, direction="long", atr_period=22, atr_multiplier=3.0)
        window = candles[2:24]
        expected_high = max(c.high for c in window)
        assert stop == round(expected_high - 3.0 * atr_vals[24 - 1 - 22], 4)

    def test_short_stop_sits_above_the_real_lowest_low(self) -> None:
        candles = [_candle(i, 100, 105, 95 - i, 100) for i in range(25)]
        atr_vals = [2.0] * 25
        stop = chandelier_stop(candles, atr_vals, entry_index=24, direction="short", atr_period=22, atr_multiplier=3.0)
        window = candles[2:24]
        expected_low = min(c.low for c in window)
        assert stop == round(expected_low + 3.0 * atr_vals[24 - 1 - 22], 4)


class TestSimulateExit:
    def test_win_at_the_real_target_r_multiple(self) -> None:
        path = [_candle(0, 101, 111, 100, 110)]
        result = simulate_exit("long", entry_price=100.0, stop_price=95.0, target_price=110.0, path=path)
        assert result.outcome == "win"
        assert result.r_multiple_realized == 2.0

    def test_loss_at_exactly_minus_one_r(self) -> None:
        path = [_candle(0, 99, 100, 94, 96)]
        result = simulate_exit("long", entry_price=100.0, stop_price=95.0, target_price=110.0, path=path)
        assert result.outcome == "loss"
        assert result.r_multiple_realized == -1.0

    def test_zero_risk_reads_open_never_a_division_error(self) -> None:
        path = [_candle(0, 100, 101, 99, 100)]
        result = simulate_exit("long", entry_price=100.0, stop_price=100.0, target_price=110.0, path=path)
        assert result.outcome == "open"

    def test_open_when_neither_level_is_touched(self) -> None:
        path = [_candle(0, 100, 101, 99, 100)]
        result = simulate_exit("long", entry_price=100.0, stop_price=90.0, target_price=120.0, path=path)
        assert result.outcome == "open"
        assert result.exit_price is None

    def test_mae_mfe_track_the_real_worst_and_best_excursion(self) -> None:
        path = [_candle(0, 100, 103, 92, 98), _candle(1, 98, 99, 97, 98)]
        result = simulate_exit("long", entry_price=100.0, stop_price=90.0, target_price=120.0, path=path)
        # risk = 10; worst excursion = 100-92=8 -> 0.8R; best = 103-100=3 -> 0.3R
        assert result.mae_r == 0.8
        assert result.mfe_r == 0.3
