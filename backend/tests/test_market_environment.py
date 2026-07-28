"""Covers app/market_environment.py — v0.7 Feature 22, the Market
Environment Simulation. Every regime is computed from real
WatchlistEntry.dailyChangePct values (refreshed every tick from the real
MarketDataProvider — see app/watchlist.py's tick_watchlist); nothing here
is a random or fabricated regime.
"""
from __future__ import annotations

from app.market_environment import (
    HIGH_VOLATILITY_THRESHOLD,
    LOW_VOLATILITY_THRESHOLD,
    TREND_THRESHOLD,
    default_market_environment,
    evaluate_market_environment,
    tick_market_environment,
)
from app.schemas import WatchlistEntry


def _entry(symbol: str, daily_change_pct: float) -> WatchlistEntry:
    return WatchlistEntry(symbol=symbol, name=symbol, lastPrice=100.0, dailyChangePct=daily_change_pct, status="completed", researchProgress=1.0, assignedAgent=None)


class TestEvaluateMarketEnvironment:
    def test_empty_watchlist_reads_as_sideways(self) -> None:
        regime, label, _detail = evaluate_market_environment([])
        assert regime == "sideways"
        assert label == "SIDEWAYS"

    def test_high_average_moves_read_as_high_volatility_regardless_of_direction(self) -> None:
        watchlist = [_entry("AAPL", HIGH_VOLATILITY_THRESHOLD + 1), _entry("MSFT", -(HIGH_VOLATILITY_THRESHOLD + 1))]
        regime, _label, _detail = evaluate_market_environment(watchlist)
        assert regime == "high_volatility"

    def test_tiny_moves_read_as_low_volatility(self) -> None:
        watchlist = [_entry("AAPL", LOW_VOLATILITY_THRESHOLD / 2), _entry("MSFT", -LOW_VOLATILITY_THRESHOLD / 2)]
        regime, _label, _detail = evaluate_market_environment(watchlist)
        assert regime == "low_volatility"

    def test_positive_average_beyond_threshold_reads_as_bull(self) -> None:
        watchlist = [_entry("AAPL", TREND_THRESHOLD + 0.5), _entry("MSFT", TREND_THRESHOLD + 0.3)]
        regime, _label, _detail = evaluate_market_environment(watchlist)
        assert regime == "bull"

    def test_negative_average_beyond_threshold_reads_as_bear(self) -> None:
        watchlist = [_entry("AAPL", -(TREND_THRESHOLD + 0.5)), _entry("MSFT", -(TREND_THRESHOLD + 0.3))]
        regime, _label, _detail = evaluate_market_environment(watchlist)
        assert regime == "bear"

    def test_small_moves_near_zero_read_as_sideways(self) -> None:
        watchlist = [_entry("AAPL", 0.5), _entry("MSFT", -0.5)]
        regime, _label, _detail = evaluate_market_environment(watchlist)
        assert regime == "sideways"

    def test_detail_reports_the_real_aggregate_numbers(self) -> None:
        watchlist = [_entry("AAPL", 2.0), _entry("MSFT", 4.0)]
        _regime, _label, detail = evaluate_market_environment(watchlist)
        assert "2 tracked symbols" in detail
        assert "avg move +3.00%" in detail


class TestTickMarketEnvironment:
    def test_stays_sideways_and_unchanged_when_the_regime_does_not_move(self) -> None:
        state = default_market_environment()
        # avg_abs=0.8 sits between LOW_VOLATILITY_THRESHOLD (0.4) and
        # TREND_THRESHOLD (1.0) with avg~0 — squarely "sideways", not
        # "low_volatility" (see the boundary tests above/below for those).
        watchlist = [_entry("AAPL", 0.8), _entry("MSFT", -0.8)]
        new_state, changed = tick_market_environment(state, watchlist, now_sim_minutes=100)
        assert changed is False
        assert new_state.current == "sideways"
        assert new_state.timeline == []

    def test_appends_a_timeline_entry_on_a_real_regime_change(self) -> None:
        state = default_market_environment()
        bull_watchlist = [_entry("AAPL", TREND_THRESHOLD + 1), _entry("MSFT", TREND_THRESHOLD + 1)]
        new_state, changed = tick_market_environment(state, bull_watchlist, now_sim_minutes=200)
        assert changed is True
        assert new_state.current == "bull"
        assert len(new_state.timeline) == 1
        assert new_state.timeline[0].regime == "bull"
        assert new_state.timeline[0].sim_minutes == 200

    def test_does_not_append_a_second_entry_while_the_regime_stays_the_same(self) -> None:
        state = default_market_environment()
        bull_watchlist = [_entry("AAPL", TREND_THRESHOLD + 1), _entry("MSFT", TREND_THRESHOLD + 1)]
        state, _ = tick_market_environment(state, bull_watchlist, now_sim_minutes=200)
        state, changed = tick_market_environment(state, bull_watchlist, now_sim_minutes=205)
        assert changed is False
        assert len(state.timeline) == 1

    def test_appends_a_second_entry_on_a_second_real_change(self) -> None:
        state = default_market_environment()
        bull_watchlist = [_entry("AAPL", TREND_THRESHOLD + 1), _entry("MSFT", TREND_THRESHOLD + 1)]
        bear_watchlist = [_entry("AAPL", -(TREND_THRESHOLD + 1)), _entry("MSFT", -(TREND_THRESHOLD + 1))]
        state, _ = tick_market_environment(state, bull_watchlist, now_sim_minutes=200)
        state, changed = tick_market_environment(state, bear_watchlist, now_sim_minutes=400)
        assert changed is True
        assert state.current == "bear"
        assert [e.regime for e in state.timeline] == ["bull", "bear"]
