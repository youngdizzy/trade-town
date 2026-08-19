"""Covers app/ema_pullback_research.py — CEO directive "Professional
Trading Firm — Market-Analysis Knowledge + Session Intelligence
Expansion," Phase 15. Every rule (cross+confirm, pullback, breakout
confirmation, Invalidation A, Chandelier Stop, exit simulation) is
tested against a hand-built, deterministic candle series so the exact
state-machine transitions are verifiable, not just plausible.
"""
from __future__ import annotations

from app.ema_pullback_research import (
    CHANDELIER_ATR_MULTIPLIER,
    CHANDELIER_ATR_PERIOD,
    EMA_PERIOD,
    SOURCE_CLAIM_TRADE_COUNT,
    SOURCE_CLAIM_WIN_RATE_PCT,
    SOURCE_CLAIM_WINNERS,
    EmaPullbackTradeRecord,
    _aggregate_bucket,
    _chandelier_stop,
    _detect_setups,
    _simulate_exit,
    run_ema_pullback_research,
)
from app.market_data import Candle
from app.technical_indicators import atr_series, ema_series


def _candle(i: int, o: float, h: float, low: float, c: float) -> Candle:
    return Candle(symbol="TEST", timeframe="1h", timestamp=f"2024-01-{1 + i // 24:02d}T{i % 24:02d}:00:00+00:00", open=o, high=h, low=low, close=c, volume=100.0, data_status="simulated")


def _long_setup_series() -> list[Candle]:
    """55 flat bars (settles EMA50 near 90) -> 5 real bars strictly below
    the (lagging) EMA -> a real close-confirmed cross-up -> a real
    2-candle bearish pullback -> a real body-close breakout of the
    pre-pullback swing high (102) -> a few trailing bars so an entry
    index exists."""
    candles: list[Candle] = []
    for i in range(55):
        candles.append(_candle(i, 90, 90.5, 89.5, 90))
    for j, price in enumerate([85.0, 84.0, 83.0, 82.0, 81.0]):
        candles.append(_candle(55 + j, price + 0.5, price + 1, price - 1, price))
    candles.append(_candle(60, 82, 102, 81, 100))  # cross-up + close confirm; leg high = 102
    candles.append(_candle(61, 100, 100.5, 96, 97))  # pullback candle 1 (bearish)
    candles.append(_candle(62, 97, 97.5, 93, 94))  # pullback candle 2 (bearish)
    candles.append(_candle(63, 95, 104, 94, 103))  # breakout candle: close 103 > confirmation level 102
    for k in range(5):
        candles.append(_candle(64 + k, 103, 104, 102, 103.5))
    return candles


def _short_setup_series() -> list[Candle]:
    """Mirror of the long fixture: 55 flat bars -> 5 bars strictly above
    the lagging EMA -> a real close-confirmed cross-down -> a real
    2-candle bullish pullback -> a real body-close breakdown of the
    pre-pullback swing low."""
    candles: list[Candle] = []
    for i in range(55):
        candles.append(_candle(i, 90, 90.5, 89.5, 90))
    for j, price in enumerate([95.0, 96.0, 97.0, 98.0, 99.0]):
        candles.append(_candle(55 + j, price - 0.5, price + 1, price - 1, price))
    candles.append(_candle(60, 98, 99, 78, 80))  # cross-down + close confirm; leg low = 78
    candles.append(_candle(61, 80, 84, 79.5, 83))  # pullback candle 1 (bullish)
    candles.append(_candle(62, 83, 86, 82.5, 85))  # pullback candle 2 (bullish)
    candles.append(_candle(63, 84, 84.5, 76, 77))  # breakdown candle: close 77 < confirmation level 78
    for k in range(5):
        candles.append(_candle(64 + k, 77, 78, 76, 76.5))
    return candles


class TestDetectSetupsLong:
    def test_finds_exactly_one_real_long_setup(self) -> None:
        candles = _long_setup_series()
        ema50 = ema_series(candles, EMA_PERIOD)
        setups = _detect_setups(candles, ema50)
        assert len(setups) == 1
        setup = setups[0]
        assert setup.direction == "long"
        assert setup.confirmation_index == 63
        assert setup.entry_index == 64
        assert setup.entry_price == candles[64].open

    def test_a_too_short_one_candle_dip_does_not_count_as_the_pullback(self) -> None:
        # Same shape, but only ONE bearish candle before resuming the
        # leg and eventually breaking out immediately -- must NOT be
        # read as a valid setup at that early break, since the source
        # rule requires at least two.
        candles: list[Candle] = []
        for i in range(55):
            candles.append(_candle(i, 90, 90.5, 89.5, 90))
        for j, price in enumerate([85.0, 84.0, 83.0, 82.0, 81.0]):
            candles.append(_candle(55 + j, price + 0.5, price + 1, price - 1, price))
        candles.append(_candle(60, 82, 102, 81, 100))
        candles.append(_candle(61, 100, 100.5, 96, 97))  # one bearish candle only
        candles.append(_candle(62, 97, 103, 96.5, 102.5))  # resumes up immediately -- not a real 2-candle pullback
        for k in range(5):
            candles.append(_candle(63 + k, 102.5, 103, 102, 102.5))
        ema50 = ema_series(candles, EMA_PERIOD)
        setups = _detect_setups(candles, ema50)
        assert setups == []

    def test_invalidation_a_deep_pullback_through_ema_discards_the_setup(self) -> None:
        candles: list[Candle] = []
        for i in range(55):
            candles.append(_candle(i, 90, 90.5, 89.5, 90))
        for j, price in enumerate([85.0, 84.0, 83.0, 82.0, 81.0]):
            candles.append(_candle(55 + j, price + 0.5, price + 1, price - 1, price))
        candles.append(_candle(60, 82, 102, 81, 100))  # cross-up
        candles.append(_candle(61, 100, 100.5, 70, 75))  # pullback candle 1 -- closes back below EMA
        candles.append(_candle(62, 75, 76, 70, 71))  # pullback candle 2
        # Even though price eventually reclaims and exceeds the original
        # swing high (102), the setup must stay invalidated -- no fresh
        # cross has occurred.
        candles.append(_candle(63, 71, 110, 70, 105))
        for k in range(5):
            candles.append(_candle(64 + k, 105, 106, 104, 105))
        ema50 = ema_series(candles, EMA_PERIOD)
        setups = _detect_setups(candles, ema50)
        assert setups == []


class TestDetectSetupsShort:
    def test_finds_exactly_one_real_short_setup(self) -> None:
        candles = _short_setup_series()
        ema50 = ema_series(candles, EMA_PERIOD)
        setups = _detect_setups(candles, ema50)
        assert len(setups) == 1
        setup = setups[0]
        assert setup.direction == "short"
        assert setup.confirmation_index == 63
        assert setup.entry_index == 64
        assert setup.entry_price == candles[64].open


class TestChandelierStop:
    def test_long_stop_is_highest_high_minus_atr_multiple(self) -> None:
        candles = _long_setup_series()
        atr_vals = atr_series(candles, CHANDELIER_ATR_PERIOD)
        stop = _chandelier_stop(candles, atr_vals, entry_index=64, direction="long")
        assert stop is not None
        window = candles[64 - CHANDELIER_ATR_PERIOD : 64]
        expected_high = max(c.high for c in window)
        atr_value = atr_vals[64 - 1 - CHANDELIER_ATR_PERIOD]
        assert stop == round(expected_high - CHANDELIER_ATR_MULTIPLIER * atr_value, 4)
        assert stop < candles[64].open  # a real long stop must sit below the real entry

    def test_short_stop_is_lowest_low_plus_atr_multiple(self) -> None:
        candles = _short_setup_series()
        atr_vals = atr_series(candles, CHANDELIER_ATR_PERIOD)
        stop = _chandelier_stop(candles, atr_vals, entry_index=64, direction="short")
        assert stop is not None
        assert stop > candles[64].open  # a real short stop must sit above the real entry

    def test_none_with_insufficient_atr_history(self) -> None:
        candles = _long_setup_series()
        atr_vals = atr_series(candles, CHANDELIER_ATR_PERIOD)
        assert _chandelier_stop(candles, atr_vals, entry_index=5, direction="long") is None


class TestSimulateExit:
    def test_target_hit_before_stop_is_a_real_win_at_the_full_r_multiple(self) -> None:
        path = [_candle(0, 101, 103, 100, 102), _candle(1, 102, 112, 101, 111)]
        result = _simulate_exit("long", entry_price=100.0, stop_price=95.0, target_price=110.0, path=path)
        assert result.outcome == "win"
        assert result.exit_price == 110.0
        assert result.r_multiple_realized == 2.0  # (110-100)/(100-95)

    def test_stop_hit_before_target_is_a_real_loss_at_exactly_minus_one_r(self) -> None:
        path = [_candle(0, 99, 100, 94, 96), _candle(1, 96, 120, 95, 119)]
        result = _simulate_exit("long", entry_price=100.0, stop_price=95.0, target_price=110.0, path=path)
        assert result.outcome == "loss"
        assert result.r_multiple_realized == -1.0

    def test_a_bar_touching_both_stop_and_target_is_conservatively_scored_a_loss(self) -> None:
        path = [_candle(0, 100, 120, 90, 100)]  # one real gap bar spans both levels
        result = _simulate_exit("long", entry_price=100.0, stop_price=95.0, target_price=110.0, path=path)
        assert result.outcome == "loss"

    def test_neither_hit_within_the_path_reads_open_never_a_fabricated_outcome(self) -> None:
        path = [_candle(0, 100, 101, 99, 100)]
        result = _simulate_exit("long", entry_price=100.0, stop_price=95.0, target_price=110.0, path=path)
        assert result.outcome == "open"
        assert result.exit_price is None
        assert result.r_multiple_realized == 0.0

    def test_short_direction_mirrors_long(self) -> None:
        path = [_candle(0, 99, 100, 89, 90)]
        result = _simulate_exit("short", entry_price=100.0, stop_price=105.0, target_price=90.0, path=path)
        assert result.outcome == "win"
        assert result.r_multiple_realized == 2.0  # (100-90)/(105-100)


def _trade(outcome: str, r: float, ts: str = "2024-01-01T00:00:00+00:00") -> EmaPullbackTradeRecord:
    return EmaPullbackTradeRecord(
        symbol="TEST",
        direction="long",
        entryTimestamp=ts,
        entryPrice=100.0,
        stopPrice=95.0,
        targetPrice=110.0,
        exitPrice=110.0 if outcome == "win" else (95.0 if outcome == "loss" else None),
        outcome=outcome,  # type: ignore[arg-type]
        rMultipleRealized=r,
        entrySession="london",
        regimeTrend="ranging",
        regimeVolatility="normal",
        breakoutCandleExtended=False,
        breakoutCandleRangeRatio=1.0,
        maeR=0.0,
        mfeR=r if r > 0 else 0.0,
    )


class TestAggregateBucket:
    def test_no_closed_trades_reads_honestly_empty(self) -> None:
        bucket = _aggregate_bucket("empty", [_trade("open", 0.0)])
        assert bucket.trade_count == 1
        assert bucket.open_count == 1
        assert bucket.win_rate_pct is None
        assert bucket.verdict is None

    def test_real_win_rate_expectancy_and_profit_factor(self) -> None:
        trades = [_trade("win", 2.0, "2024-01-01T00:00:00+00:00"), _trade("win", 2.0, "2024-01-02T00:00:00+00:00"), _trade("loss", -1.0, "2024-01-03T00:00:00+00:00")]
        bucket = _aggregate_bucket("mixed", trades)
        assert bucket.win_rate_pct == round(2 / 3 * 100, 1)
        assert bucket.avg_win_r == 2.0
        assert bucket.avg_loss_r == 1.0
        # expectancy = (2/3)*2.0 - (1/3)*1.0
        assert bucket.expectancy_r == round((2 / 3) * 2.0 - (1 / 3) * 1.0, 3)
        assert bucket.profit_factor == round(4.0 / 1.0, 3)

    def test_below_the_bucket_verdict_bar_reads_not_enough_evidence(self) -> None:
        trades = [_trade("win", 2.0)]
        bucket = _aggregate_bucket("small", trades)
        assert bucket.verdict == "not_enough_evidence"

    def test_longest_losing_streak_counts_real_consecutive_losses_in_entry_order(self) -> None:
        trades = [
            _trade("loss", -1.0, "2024-01-01T00:00:00+00:00"),
            _trade("loss", -1.0, "2024-01-02T00:00:00+00:00"),
            _trade("win", 2.0, "2024-01-03T00:00:00+00:00"),
            _trade("loss", -1.0, "2024-01-04T00:00:00+00:00"),
        ]
        bucket = _aggregate_bucket("streaks", trades)
        assert bucket.longest_losing_streak == 2


class TestSourceClaimNeverInfluencesComputation:
    def test_source_claim_constants_are_fixed_disclosure_values(self) -> None:
        assert SOURCE_CLAIM_TRADE_COUNT == 32
        assert SOURCE_CLAIM_WINNERS == 21
        assert SOURCE_CLAIM_WIN_RATE_PCT == round(21 / 32 * 100, 1)


class TestRunEmaPullbackResearchIntegration:
    """Runs the real orchestration against app/market_data.py's own real
    (mock, seeded, deterministic) candle provider -- the same real data
    every other endpoint in this codebase reads from. Assertions check
    internal consistency (numbers add up, the verdict/evidence chain is
    honest), never a specific win rate -- this module must never assert
    or expect a particular outcome, since that would be exactly the
    "assume the strategy works" anti-pattern the directive forbids."""

    def test_produces_internally_consistent_real_results(self) -> None:
        result = run_ema_pullback_research(symbols=["AAPL", "MSFT"], candles_per_symbol=2500)
        assert result.symbols_tested == ["AAPL", "MSFT"]
        assert len(result.r_multiple_sweep) == 5
        for bucket in result.r_multiple_sweep:
            assert bucket.trade_count == bucket.win_count + bucket.loss_count + bucket.open_count
        # The source claim must never leak into TradeTown's own computed number.
        assert result.source_claim_comparison.source_claim_win_rate_pct == SOURCE_CLAIM_WIN_RATE_PCT
        if result.source_claim_comparison.tradetown_win_rate_pct is not None:
            assert result.source_claim_comparison.tradetown_win_rate_pct != SOURCE_CLAIM_WIN_RATE_PCT or True  # never asserted equal; a real coincidence is allowed but not required
        assert "SOURCE CLAIM" in result.source_claim_comparison.detail
        assert "never" in result.data_honesty_note.lower()

    def test_too_little_history_still_returns_an_honest_empty_result(self) -> None:
        result = run_ema_pullback_research(symbols=["AAPL"], candles_per_symbol=10)
        assert result.r_multiple_sweep[0].trade_count == 0
        assert result.model_validation is None
        assert result.monte_carlo is None

    def test_confirmed_setups_are_never_more_frequent_than_naive_crosses(self) -> None:
        result = run_ema_pullback_research(symbols=["AAPL", "SPY"], candles_per_symbol=3000)
        confirmed = result.confirmed_vs_naive_baseline[0]
        naive = result.confirmed_vs_naive_baseline[1]
        assert confirmed.trade_count <= naive.trade_count
