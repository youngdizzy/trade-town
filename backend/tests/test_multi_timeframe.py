"""Covers app/multi_timeframe.py — CEO directive "Professional Quant
Trading Core," Phase B, the Multi-Timeframe Confirmation P2 item. Every
per-timeframe direction read reuses app/trend_engine.py's own real
compute_horizon_trend() — this test suite proves the CONFIRMATION
composition (does a higher timeframe's real trend agree with the desk's
own buy/sell call), not the trend math itself (already covered by
test_trend_engine.py).
"""
from __future__ import annotations

from app.market_data import Candle, MarketDataProvider, Quote
from app.multi_timeframe import CONFIRMATION_TIMEFRAMES, compute_multi_timeframe_confirmation


def _candles(symbol: str, timeframe: str, closes: list[float]) -> list[Candle]:
    return [
        Candle(symbol=symbol, timeframe=timeframe, timestamp=f"t{i}", open=c, high=c + 1, low=c - 1, close=c, volume=1000, data_status="simulated")
        for i, c in enumerate(closes)
    ]


class _FixedProvider(MarketDataProvider):
    """A deterministic fake — real MockMarketDataProvider is a stochastic
    regime-switching walk with no way to force a specific trend per
    timeframe, so this test suite controls the exact candle series each
    real timeframe returns instead."""

    def __init__(self, by_timeframe: dict[str, list[float]]) -> None:
        self._by_timeframe = by_timeframe

    def get_quote(self, symbol: str) -> Quote:
        raise NotImplementedError

    def get_candles(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        closes = self._by_timeframe.get(timeframe, [])
        return _candles(symbol, timeframe, closes)


def _uptrend(n: int = 30, start: float = 100.0) -> list[float]:
    return [start + i for i in range(n)]


def _downtrend(n: int = 30, start: float = 100.0) -> list[float]:
    return [start - i for i in range(n)]


def _flat(n: int = 30, price: float = 100.0) -> list[float]:
    return [price for _ in range(n)]


class TestComputeMultiTimeframeConfirmation:
    def test_wait_is_always_neutral(self) -> None:
        provider = _FixedProvider({tf: _uptrend() for tf in CONFIRMATION_TIMEFRAMES})
        result = compute_multi_timeframe_confirmation(provider, "NEXA", "wait")
        assert result.agreement_score == 50.0
        assert "WAIT" in result.summary
        # Still real readings computed and disclosed, even though they
        # don't feed the score for a "wait" call.
        assert len(result.readings) == len(CONFIRMATION_TIMEFRAMES)

    def test_full_confirmation_when_every_higher_timeframe_agrees_with_buy(self) -> None:
        provider = _FixedProvider({tf: _uptrend() for tf in CONFIRMATION_TIMEFRAMES})
        result = compute_multi_timeframe_confirmation(provider, "NEXA", "buy")
        assert result.agreement_score == 100.0
        assert all(r.direction == 1 for r in result.readings)

    def test_zero_confirmation_when_every_higher_timeframe_disagrees_with_buy(self) -> None:
        provider = _FixedProvider({tf: _downtrend() for tf in CONFIRMATION_TIMEFRAMES})
        result = compute_multi_timeframe_confirmation(provider, "NEXA", "buy")
        assert result.agreement_score == 0.0

    def test_sell_is_confirmed_by_a_real_downtrend(self) -> None:
        provider = _FixedProvider({tf: _downtrend() for tf in CONFIRMATION_TIMEFRAMES})
        result = compute_multi_timeframe_confirmation(provider, "NEXA", "sell")
        assert result.agreement_score == 100.0

    def test_partial_confirmation_when_timeframes_disagree_with_each_other(self) -> None:
        timeframes = list(CONFIRMATION_TIMEFRAMES)
        assert len(timeframes) == 2  # this test's math assumes exactly two confirmation timeframes
        provider = _FixedProvider({timeframes[0]: _uptrend(), timeframes[1]: _downtrend()})
        result = compute_multi_timeframe_confirmation(provider, "NEXA", "buy")
        assert result.agreement_score == 50.0

    def test_insufficient_history_is_excluded_not_counted_as_disagreement(self) -> None:
        timeframes = list(CONFIRMATION_TIMEFRAMES)
        # One real timeframe has plenty of history and agrees; the other
        # has only one candle (insufficient for compute_horizon_trend).
        provider = _FixedProvider({timeframes[0]: _uptrend(), timeframes[1]: [100.0]})
        result = compute_multi_timeframe_confirmation(provider, "NEXA", "buy")
        assert result.agreement_score == 100.0  # the one evaluable timeframe fully confirms
        assert "insufficient" in result.summary.lower()

    def test_all_insufficient_history_is_neutral_not_fabricated(self) -> None:
        provider = _FixedProvider({tf: [] for tf in CONFIRMATION_TIMEFRAMES})
        result = compute_multi_timeframe_confirmation(provider, "NEXA", "buy")
        assert result.agreement_score == 50.0
        assert "Not enough real candle history" in result.summary

    def test_flat_market_readings_are_excluded_like_insufficient_history(self) -> None:
        # A real endpoint-slope direction of 0 (flat) on both timeframes
        # means nothing real to confirm against — treated the same
        # honest-neutral way as insufficient history, never counted
        # against the trade.
        provider = _FixedProvider({tf: _flat() for tf in CONFIRMATION_TIMEFRAMES})
        result = compute_multi_timeframe_confirmation(provider, "NEXA", "buy")
        assert result.agreement_score == 50.0

    def test_readings_disclose_the_real_timeframe_and_detail(self) -> None:
        provider = _FixedProvider({tf: _uptrend() for tf in CONFIRMATION_TIMEFRAMES})
        result = compute_multi_timeframe_confirmation(provider, "NEXA", "buy")
        assert {r.timeframe for r in result.readings} == set(CONFIRMATION_TIMEFRAMES)
        assert all(r.detail for r in result.readings)
