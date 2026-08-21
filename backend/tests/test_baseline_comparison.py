"""Covers app/baseline_comparison.py — CEO directive "Quant Research
Factory / Strategy Discovery Engine," Phase 5: a real, per-symbol
buy-and-hold price-return baseline over the exact same real (mock)
candle window a research experiment's own backtest already tested.
"""
from __future__ import annotations

from app.baseline_comparison import compute_buy_and_hold_baseline
from app.market_data import market_data_provider


class TestComputeBuyAndHoldBaseline:
    def test_one_real_entry_per_symbol_in_the_same_order(self) -> None:
        baselines = compute_buy_and_hold_baseline(symbols=["AAPL", "MSFT"], timeframe="1h", candles_per_symbol=500)
        assert [b.symbol for b in baselines] == ["AAPL", "MSFT"]

    def test_the_return_matches_the_real_first_and_last_close_of_the_same_window(self) -> None:
        candles = market_data_provider.get_candles("AAPL", "1h", 500)
        baselines = compute_buy_and_hold_baseline(symbols=["AAPL"], timeframe="1h", candles_per_symbol=500)
        baseline = baselines[0]
        assert baseline.start_price == round(candles[0].close, 4)
        assert baseline.end_price == round(candles[-1].close, 4)
        expected_return_pct = round((candles[-1].close - candles[0].close) / candles[0].close * 100, 2)
        assert baseline.return_pct == expected_return_pct
        assert baseline.candle_count == len(candles)

    def test_repeated_calls_read_the_identical_real_series_never_a_resampled_one(self) -> None:
        first = compute_buy_and_hold_baseline(symbols=["AAPL"], timeframe="1h", candles_per_symbol=500)
        second = compute_buy_and_hold_baseline(symbols=["AAPL"], timeframe="1h", candles_per_symbol=500)
        assert first[0].start_price == second[0].start_price
        assert first[0].end_price == second[0].end_price
        assert first[0].return_pct == second[0].return_pct

    def test_a_window_too_small_to_measure_a_return_is_skipped_not_fabricated_as_zero(self) -> None:
        baselines = compute_buy_and_hold_baseline(symbols=["AAPL"], timeframe="1h", candles_per_symbol=1)
        assert baselines == []

    def test_an_empty_symbol_list_reads_an_honestly_empty_result(self) -> None:
        assert compute_buy_and_hold_baseline(symbols=[], timeframe="1h", candles_per_symbol=500) == []
