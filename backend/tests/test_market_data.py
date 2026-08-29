"""Covers app/market_data.py's OHLC candle generation — added for v0.6.2's
Market Data Abstraction / candlestick chart feature.
"""
from __future__ import annotations

import random

import pytest

from app.market_data import RECENT_REGIME_BIAS_WINDOW, TIMEFRAME_ORDER, MockMarketDataProvider


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


# CEO Company Health + Live Market Realism directive — the sections below
# prove the *statistical behavior* the module's own docstring claims
# (volatility clustering, momentum persistence, mean reversion, internal
# regime-switching, and real two-way regime<->price coupling), not just
# that numbers render. See app/market_data.py's `_step()`/`_WalkState`
# for what's under test.


class TestVolatilityClustering:
    def test_a_large_shock_immediately_raises_the_next_steps_volatility(self):
        """GARCH(1,1) recurrence: variance_t depends on shock_{t-1}^2 —
        a real large move must raise the very next step's real
        volatility level, not leave it independent of what just
        happened (the bug the old iid-uniform-draw generator had)."""
        from app.market_data import _WalkState, _step

        rng = random.Random(1)
        calm = _WalkState(price=100.0, prev_shock=0.05, vol=1.0)
        shocked = _WalkState(price=100.0, prev_shock=8.0, vol=1.0)
        _step(calm, rng, time_scale=1.0, external_regime=None, apply_bias=False)
        _step(shocked, rng, time_scale=1.0, external_regime=None, apply_bias=False)
        assert shocked.vol > calm.vol

    def test_real_series_shows_positive_autocorrelation_in_squared_returns(self):
        """The real, emergent signature of volatility clustering: big
        moves cluster near other big moves. An i.i.d. generator (the
        prior implementation) reads ~0 here; a real clustered process
        reads clearly positive."""
        provider = MockMarketDataProvider()
        candles = provider.get_candles("VOLTEST", "1h", 400)
        returns = [(b.close - a.close) / a.close for a, b in zip(candles, candles[1:]) if a.close]
        squared = [r * r for r in returns]
        mean_sq = sum(squared) / len(squared)
        centered = [s - mean_sq for s in squared]
        numerator = sum(centered[i] * centered[i + 1] for i in range(len(centered) - 1))
        denominator = sum(c * c for c in centered)
        autocorr = numerator / denominator if denominator else 0.0
        assert autocorr > 0.05


class TestTrendPersistence:
    def test_real_series_has_longer_same_direction_runs_than_a_coin_flip(self):
        """A real trending/regime-switching process produces longer runs
        of same-direction moves than independent coin-flip noise would
        (whose expected average run length is exactly 2.0)."""
        provider = MockMarketDataProvider()
        run_lengths: list[int] = []
        for i in range(20):
            candles = provider.get_candles(f"TRENDTEST{i}", "1h", 200)
            directions = [c.close >= c.open for c in candles]
            current_run = 1
            for prev, curr in zip(directions, directions[1:]):
                if curr == prev:
                    current_run += 1
                else:
                    run_lengths.append(current_run)
                    current_run = 1
            run_lengths.append(current_run)
        avg_run = sum(run_lengths) / len(run_lengths)
        assert avg_run > 2.2


class TestMeanReversion:
    def test_range_regime_pulls_price_back_toward_its_anchor(self):
        """A "range" internal regime must exert a real, measurable pull
        back toward the slow-moving anchor once price is displaced far
        from it — the mean-reversion term app/market_data.py's own
        docstring claims."""
        from app.market_data import _WalkState, _step

        rng = random.Random(7)
        state = _WalkState(price=150.0, anchor=100.0, regime="range", regime_bars_left=50)
        distance_before = state.price - state.anchor
        for _ in range(40):
            _step(state, rng, time_scale=1.0, external_regime=None, apply_bias=False)
            if state.regime != "range":
                state.regime = "range"
                state.regime_bars_left = 50
        distance_after = state.price - state.anchor
        assert abs(distance_after) < abs(distance_before)


class TestRegimeSwitchingDuration:
    def test_a_regime_segment_lasts_more_than_one_bar(self):
        """Real consolidation/trend runs, not a bar-by-bar coin flip —
        the same internal regime should still be active a few bars after
        it was picked, most of the time."""
        from app.market_data import _WalkState, _step

        rng = random.Random(3)
        state = _WalkState(price=100.0)
        _step(state, rng, time_scale=1.0, external_regime=None, apply_bias=False)
        first_regime = state.regime
        same_regime_count = 0
        for _ in range(4):
            _step(state, rng, time_scale=1.0, external_regime=None, apply_bias=False)
            if state.regime == first_regime:
                same_regime_count += 1
        assert same_regime_count >= 1


class TestExternalRegimeCoupling:
    def test_a_bullish_external_regime_produces_a_higher_recent_average_return_than_bearish(self):
        """The real two-way coupling app/market_data.py's docstring
        describes: app/nexus.py feeds the real, already-computed
        aggregate regime into set_market_regime(), which must measurably
        bias the most recent bars of a freshly generated series —
        checked here by averaging across many symbols so a single
        series' own internal regime-switching noise doesn't drown out
        the real, systematic bias."""
        symbols = [f"REGIMETEST{i}" for i in range(40)]

        bull_provider = MockMarketDataProvider()
        bull_provider.set_market_regime("bull")
        bull_returns = []
        for symbol in symbols:
            candles = bull_provider.get_candles(symbol, "1h", 60)
            recent = candles[-RECENT_REGIME_BIAS_WINDOW:]
            bull_returns.append((recent[-1].close - recent[0].open) / recent[0].open)

        bear_provider = MockMarketDataProvider()
        bear_provider.set_market_regime("bear")
        bear_returns = []
        for symbol in symbols:
            candles = bear_provider.get_candles(symbol, "1h", 60)
            recent = candles[-RECENT_REGIME_BIAS_WINDOW:]
            bear_returns.append((recent[-1].close - recent[0].open) / recent[0].open)

        assert sum(bull_returns) / len(bull_returns) > sum(bear_returns) / len(bear_returns)

    def test_set_market_regime_does_not_affect_bars_outside_the_recent_window(self):
        """Historical candles must not retroactively change just because
        the real aggregate regime later flips — see
        RECENT_REGIME_BIAS_WINDOW's own docstring for why only the
        chart's right edge is ever biased."""
        provider = MockMarketDataProvider()
        provider.set_market_regime(None)
        neutral = provider.get_candles("STABLETEST", "1h", 100)

        provider.set_market_regime("bull")
        biased = provider.get_candles("STABLETEST", "1h", 100)

        older_neutral = neutral[: -RECENT_REGIME_BIAS_WINDOW]
        older_biased = biased[: -RECENT_REGIME_BIAS_WINDOW]
        assert [c.close for c in older_neutral] == [c.close for c in older_biased]

    def test_get_quote_also_reads_the_external_regime(self):
        """The live per-symbol quote walk (app/watchlist.py's own real
        feed into app/market_environment.py's regime classification)
        shares the identical real step function as get_candles() — see
        app/market_data.py's _step() docstring — so it must be
        influenceable by the same real external bias, not a second,
        divergent implementation."""
        provider = MockMarketDataProvider()
        provider.set_market_regime("bull")
        bull_moves = []
        for i in range(30):
            quote = provider.get_quote(f"LIVETEST{i}")
            bull_moves.append(quote.change_pct)

        provider2 = MockMarketDataProvider()
        provider2.set_market_regime("bear")
        bear_moves = []
        for i in range(30):
            quote = provider2.get_quote(f"LIVETEST{i}")
            bear_moves.append(quote.change_pct)

        assert sum(bull_moves) / len(bull_moves) > sum(bear_moves) / len(bear_moves)


class TestNoObviouslySyntheticPatterns:
    def test_candle_direction_does_not_perfectly_alternate(self):
        """The CEO's directive explicitly calls out "perfectly
        alternating candles" as a symptom of an obviously synthetic
        generator — a real (even a range-bound) series shouldn't produce
        a strict up/down/up/down/... sequence."""
        provider = MockMarketDataProvider()
        candles = provider.get_candles("PATTERNTEST", "1h", 200)
        directions = [c.close >= c.open for c in candles]
        perfectly_alternating = all(a != b for a, b in zip(directions, directions[1:]))
        assert not perfectly_alternating

    def test_body_sizes_show_real_variety_not_a_uniform_magnitude(self):
        """The CEO's directive calls out "identical candle sizes" as a
        symptom of an obviously synthetic generator — real body sizes
        (across a long enough sample to cross multiple internal
        regimes/volatility levels) should span a real range, not cluster
        at one uniform magnitude."""
        provider = MockMarketDataProvider()
        candles = provider.get_candles("PATTERNTEST", "1h", 200)
        magnitudes = [abs(c.close - c.open) for c in candles]
        assert max(magnitudes) > min(m for m in magnitudes if m > 0) * 5


class TestFuturesFxTreasurySeedPrices:
    """CEO directive "AHL-Inspired Systematic Trend & Momentum Research
    Engine" follow-up — a prior audit pass labeled futures/FX/Treasury a
    hard blocker ("no data feeds exist"); re-audited and found the
    opposite. `_SEED_PRICE_OVERRIDE` gives each of these real, disclosed
    symbols a realistic real starting PRICE LEVEL instead of the generic
    stock-calibrated "$20-$500" hash range every other symbol uses."""

    @pytest.mark.parametrize(
        "symbol,low,high",
        [
            ("ES=F", 1000.0, 20000.0),
            ("CL=F", 20.0, 200.0),
            ("ZN=F", 50.0, 200.0),
            ("EURUSD=X", 0.5, 2.0),
            ("GBPUSD=X", 0.5, 2.0),
            ("NQ=F", 1000.0, 40000.0),
            ("ZB=F", 50.0, 200.0),
            ("USDJPY=X", 50.0, 300.0),
        ],
    )
    def test_real_starting_price_lands_in_a_realistic_range_for_the_instrument(self, symbol, low, high):
        # Never the generic $20-$500 stock-calibrated range these
        # specific instruments would otherwise fall into — a real,
        # explicit override for each one instead.
        seed = MockMarketDataProvider._seed_price(symbol)
        assert low <= seed <= high

    def test_get_quote_and_get_candles_work_normally_for_a_futures_symbol(self):
        provider = MockMarketDataProvider()
        quote = provider.get_quote("ES=F")
        assert quote.price > 0
        candles = provider.get_candles("ES=F", "1h", 30)
        assert len(candles) == 30
        assert all(c.close > 0 for c in candles)

    def test_a_symbol_with_no_override_still_uses_the_generic_hash_range(self):
        seed = MockMarketDataProvider._seed_price("SOME-UNKNOWN-SYMBOL")
        assert 20.0 <= seed <= 500.0
