"""Covers app/market_data.py's OHLC candle generation — added for v0.6.2's
Market Data Abstraction / candlestick chart feature.
"""
from __future__ import annotations

import pytest

from app.market_data import TIMEFRAME_ORDER, MockMarketDataProvider


def test_get_candles_returns_the_requested_count():
    provider = MockMarketDataProvider()
    candles = provider.get_candles("AAPL", "1h", 42)
    assert len(candles) == 42


def test_candles_are_internally_consistent_ohlc():
    provider = MockMarketDataProvider()
    for candle in provider.get_candles("MSFT", "5m", 100):
        assert candle.high >= candle.open
        assert candle.high >= candle.close
        assert candle.low <= candle.open
        assert candle.low <= candle.close
        assert candle.high >= candle.low
        assert candle.volume >= 0


def test_candles_are_oldest_first_by_timestamp():
    provider = MockMarketDataProvider()
    candles = provider.get_candles("SPY", "1d", 20)
    timestamps = [c.timestamp for c in candles]
    assert timestamps == sorted(timestamps)


def test_candles_are_always_labeled_simulated_never_live():
    provider = MockMarketDataProvider()
    for candle in provider.get_candles("QQQ", "15m", 30):
        assert candle.data_status == "simulated"


def test_historical_candles_are_stable_across_repeated_calls():
    """A chart the player reopens shouldn't reshuffle its own history —
    only get_quote()'s live-mutating price should ever change between
    calls, not the deterministic historical walk."""
    provider = MockMarketDataProvider()
    first = provider.get_candles("GLD", "1h", 50)
    second = provider.get_candles("GLD", "1h", 50)
    # Every candle except possibly the last (which tracks get_quote()'s
    # live price, and get_quote() was never called here so it's also
    # untouched) must match exactly.
    assert [c.open for c in first] == [c.open for c in second]
    assert [c.close for c in first] == [c.close for c in second]


def test_different_symbols_produce_different_series():
    provider = MockMarketDataProvider()
    a = provider.get_candles("AAPL", "1h", 30)
    b = provider.get_candles("MSFT", "1h", 30)
    assert [c.close for c in a] != [c.close for c in b]


def test_unsupported_timeframe_raises_value_error():
    provider = MockMarketDataProvider()
    with pytest.raises(ValueError):
        provider.get_candles("AAPL", "3m", 10)


def test_all_advertised_timeframes_are_actually_supported():
    provider = MockMarketDataProvider()
    for timeframe in TIMEFRAME_ORDER:
        candles = provider.get_candles("AAPL", timeframe, 5)
        assert len(candles) == 5
        assert all(c.timeframe == timeframe for c in candles)


def test_latest_candle_tracks_the_live_mock_price_after_a_quote():
    provider = MockMarketDataProvider()
    quote = provider.get_quote("AAPL")
    candles = provider.get_candles("AAPL", "1h", 10)
    assert candles[-1].close == quote.price
