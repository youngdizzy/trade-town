"""Covers app/market_intelligence.py — v0.7 Feature 51, the Market
Intelligence Department. Every read must trace back to real (mock) OHLCV
Candle data or real wall-clock time — never a fabricated number — and
every named proxy (Institutional Activity, Accumulation/Distribution,
News Risk) must stay honestly labeled, never presented as verified
order-flow/economic-calendar data.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.market_data import Candle, MockMarketDataProvider
from app.market_intelligence import (
    _classify_regime,
    _session_for_hour,
    compute_historical_similarity,
    compute_liquidity,
    compute_market_intelligence_state,
    compute_market_quality,
    compute_market_structure,
    compute_news_risk,
    compute_session,
    compute_strategy_match,
    default_market_intelligence_state,
    filter_environment_entries_for_day,
    filter_trades_for_day,
    generate_learning_entry,
    generate_market_intelligence_report,
    record_learning_entry,
    record_market_intelligence_report,
)
from app.schemas import (
    MarketEnvironmentEntry,
    MarketIntelligenceReport,
    NewsItem,
    NewsRiskRead,
    PaperTrade,
    SessionRead,
    Strategy,
    StrategyReport,
    VolatilityRead,
    WatchlistEntry,
)
from app.watchlist import SEED_SYMBOLS


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _candle(i: int, *, open_: float, high: float, low: float, close: float, volume: float = 200_000.0, symbol: str = "NEXA", hour: int | None = None) -> Candle:
    timestamp = f"2026-01-0{1 + i // 24}T{(hour if hour is not None else i % 24):02d}:00:00+00:00"
    return Candle(symbol=symbol, timeframe="1h", timestamp=timestamp, open=open_, high=high, low=low, close=close, volume=volume, data_status="simulated")


def _flat_candles(n: int = 40, *, price: float = 100.0, volume: float = 200_000.0) -> list[Candle]:
    return [_candle(i, open_=price, high=price + 0.2, low=price - 0.2, close=price, volume=volume) for i in range(n)]


def _uptrend_candles(n: int = 40, *, start: float = 100.0, step: float = 1.0) -> list[Candle]:
    candles = []
    price = start
    for i in range(n):
        close = price + step
        candles.append(_candle(i, open_=price, high=close + 0.3, low=price - 0.3, close=close))
        price = close
    return candles


class TestComputeMarketStructure:
    def test_not_enough_history_is_an_honest_default(self) -> None:
        structure = compute_market_structure("NEXA", _flat_candles(n=4))
        assert structure.last_break_of_structure == "none"
        assert structure.structure_state == "consolidation"

    def test_rising_swing_highs_are_a_real_bullish_break_of_structure(self) -> None:
        # Two clean up-legs with a real local-max swing high each,
        # the second higher than the first — a real, standard BOS.
        candles = []
        for i in range(6):
            candles.append(_candle(i, open_=100 + i, high=101 + i, low=99 + i, close=100 + i))
        candles.append(_candle(6, open_=106, high=112, low=105, close=111))  # first swing high ~112
        for i in range(7, 13):
            candles.append(_candle(i, open_=110 - (i - 7), high=111 - (i - 7), low=108 - (i - 7), close=109 - (i - 7)))
        candles.append(_candle(13, open_=104, high=105, low=95, close=96))  # local low
        for i in range(14, 20):
            candles.append(_candle(i, open_=96 + (i - 14) * 3, high=98 + (i - 14) * 3, low=95 + (i - 14) * 3, close=97 + (i - 14) * 3))
        candles.append(_candle(20, open_=114, high=125, low=113, close=124))  # second swing high, higher than the first
        for i in range(21, 27):
            candles.append(_candle(i, open_=123 - (i - 21), high=124 - (i - 21), low=121 - (i - 21), close=122 - (i - 21)))

        structure = compute_market_structure("NEXA", candles)
        assert len(structure.swing_highs) >= 2
        assert structure.swing_highs[-1] > structure.swing_highs[-2]
        assert structure.last_break_of_structure == "bullish"

    def test_flat_series_reads_as_consolidation(self) -> None:
        structure = compute_market_structure("NEXA", _flat_candles())
        assert structure.structure_state == "consolidation"
        assert structure.last_break_of_structure == "none"


class TestComputeLiquidity:
    def test_not_enough_history_is_an_honest_default(self) -> None:
        liquidity = compute_liquidity("NEXA", _flat_candles(n=4))
        assert liquidity.zones == []
        assert liquidity.sweep_detected is False

    def test_two_equal_highs_form_a_real_liquidity_zone(self) -> None:
        candles = []
        for i in range(3):
            candles.append(_candle(i, open_=100, high=100.5, low=99.5, close=100))
        candles.append(_candle(3, open_=100, high=110.0, low=99.5, close=101))  # swing high #1 at 110
        for i in range(4, 8):
            candles.append(_candle(i, open_=101 - i * 0.1, high=102, low=100, close=101))
        candles.append(_candle(8, open_=101, high=110.1, low=100.5, close=102))  # swing high #2 at 110.1 — equal-ish to #1
        for i in range(9, 15):
            candles.append(_candle(i, open_=102, high=102.5, low=101.5, close=102))
        # Final (non-piercing) candles — no sweep, just zone formation.
        for i in range(15, 20):
            candles.append(_candle(i, open_=102, high=103, low=101, close=102))

        liquidity = compute_liquidity("NEXA", candles)
        assert any(z.kind == "equal_highs" for z in liquidity.zones)
        assert liquidity.liquidity_score > 0

    def test_a_wick_above_a_real_zone_that_closes_back_inside_is_a_real_sweep(self) -> None:
        candles = []
        for i in range(3):
            candles.append(_candle(i, open_=100, high=100.5, low=99.5, close=100))
        candles.append(_candle(3, open_=100, high=110.0, low=99.5, close=101))
        for i in range(4, 8):
            candles.append(_candle(i, open_=101, high=102, low=100, close=101))
        candles.append(_candle(8, open_=101, high=110.0, low=100.5, close=102))
        for i in range(9, 15):
            candles.append(_candle(i, open_=102, high=103, low=101, close=102))
        # Sweep candle: wick pierces the ~110 zone, closes back below it.
        candles.append(_candle(15, open_=105, high=112.0, low=104.0, close=106.0))
        for i in range(16, 19):
            candles.append(_candle(i, open_=106, high=107, low=105, close=106))

        liquidity = compute_liquidity("NEXA", candles)
        assert liquidity.sweep_detected is True
        assert liquidity.sweep_direction == "above_highs"


class TestComputeSession:
    def test_asian_hour_is_real(self) -> None:
        assert _session_for_hour(2.0) == "asian"

    def test_overlap_hour_is_real(self) -> None:
        assert _session_for_hour(14.0) == "london_ny_overlap"

    def test_market_open_window_is_real(self) -> None:
        assert _session_for_hour(13.6) == "market_open"

    def test_closed_gap_hour_is_real(self) -> None:
        assert _session_for_hour(23.0) == "closed"

    def test_compute_session_uses_real_utc_time(self) -> None:
        now = datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc)
        session = compute_session(now)
        assert session.current == "asian"
        assert "02:00" in session.detail


class TestComputeSessionDstAware:
    """CEO directive "Complete Trade Provenance," Part 4 — compute_session()
    is real, DST-aware exchange-hours classification via zoneinfo, deliberately
    separate from the still-fixed-UTC _session_for_hour() backtesting uses."""

    def test_the_same_utc_hour_classifies_differently_across_a_dst_transition(self) -> None:
        # The core proof of real DST-awareness: 13:45 UTC is NYSE market_open
        # (9:45 EDT) in July, but only the London session (8:45 EST, before
        # the 9:30 NYSE open) in January — a fixed-UTC classifier could
        # never produce two different answers for the identical UTC time.
        summer = compute_session(datetime(2026, 7, 15, 13, 45, tzinfo=timezone.utc))
        winter = compute_session(datetime(2026, 1, 15, 13, 45, tzinfo=timezone.utc))
        assert summer.current == "market_open"
        assert winter.current == "london"

    def test_a_real_saturday_reports_closed_even_during_what_would_be_market_open_hours(self) -> None:
        # 2026-01-17 is a real Saturday; 14:45 UTC is exactly NYSE
        # market_open on the equivalent weekday (see the winter
        # market_open test below) -- markets are honestly closed on
        # weekends, never misreported as open.
        saturday = compute_session(datetime(2026, 1, 17, 14, 45, tzinfo=timezone.utc))
        assert saturday.current == "closed"

    def test_winter_market_open_shifts_a_full_hour_later_in_utc_than_summer(self) -> None:
        winter_open = compute_session(datetime(2026, 1, 15, 14, 45, tzinfo=timezone.utc))
        assert winter_open.current == "market_open"

    def test_ny_lunch_hour_is_real(self) -> None:
        session = compute_session(datetime(2026, 7, 15, 16, 15, tzinfo=timezone.utc))
        assert session.current == "ny_lunch_hour"

    def test_london_ny_overlap_reports_both_names_in_overlaps_active(self) -> None:
        session = compute_session(datetime(2026, 7, 15, 14, 30, tzinfo=timezone.utc))
        assert session.current == "london_ny_overlap"
        assert set(session.overlaps_active) == {"london", "new_york"}

    def test_asian_session_has_no_dst_since_tokyo_observes_none(self) -> None:
        # Japan does not observe daylight saving -- the same real UTC
        # hour should classify identically regardless of time of year.
        summer = compute_session(datetime(2026, 7, 1, 2, 0, tzinfo=timezone.utc))
        winter = compute_session(datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc))
        assert summer.current == winter.current == "asian"

    def test_a_naive_datetime_is_treated_as_real_utc(self) -> None:
        naive = compute_session(datetime(2026, 1, 1, 2, 0))
        aware = compute_session(datetime(2026, 1, 1, 2, 0, tzinfo=timezone.utc))
        assert naive.current == aware.current == "asian"

    def test_backtesting_classifier_is_completely_unchanged_by_this_directive(self) -> None:
        # _session_for_hour() must still be the exact fixed-UTC function
        # every backtest/certification already depends on -- confirmed by
        # the pre-existing hour-based tests above still passing unmodified.
        assert _session_for_hour(2.0) == "asian"
        assert _session_for_hour(13.6) == "market_open"


class TestComputeSessionExactBoundaryInstants:
    """CEO directive "Complete Trade Provenance," Part 20 — explicitly
    required: test boundary timestamps around session open, session
    close, DST transitions, midnight, and weekend/market closure. Every
    test below hits the exact instant, one second either side of a real
    classification change -- not a comfortably-inside-the-window time
    like the tests above, which only prove the season/hour differs, not
    that the edge itself is drawn correctly."""

    def test_one_second_before_nyse_open_is_london_one_second_after_is_market_open(self) -> None:
        # 2026-01-07 (Wednesday, EST/UTC-5, no DST in effect). NYSE
        # opens 9:30 ET == 14:30 UTC in winter. London (GMT, UTC+0) is
        # still open at 14:29 GMT (LSE: 08:00-16:30).
        just_before = compute_session(datetime(2026, 1, 7, 14, 29, 59, tzinfo=timezone.utc))
        at_open = compute_session(datetime(2026, 1, 7, 14, 30, 0, tzinfo=timezone.utc))
        assert just_before.current == "london"
        assert at_open.current == "market_open"

    def test_one_second_before_nyse_close_is_market_close_one_second_after_is_closed(self) -> None:
        # Same real Wednesday. NYSE closes 16:00 ET == 21:00 UTC in
        # winter; at that exact instant London (closed since 16:30 GMT
        # the day's local clock has already... no, London closes 16:30
        # GMT == 16:30 UTC in winter, well before 21:00) and Tokyo (past
        # its own 9:00-15:00 JST window by then) are both honestly
        # closed too -- a real, all-exchanges-closed instant.
        just_before = compute_session(datetime(2026, 1, 7, 20, 59, 59, tzinfo=timezone.utc))
        at_close = compute_session(datetime(2026, 1, 7, 21, 0, 0, tzinfo=timezone.utc))
        assert just_before.current == "market_close"
        assert at_close.current == "closed"

    def test_midnight_utc_is_not_itself_meaningful_only_each_exchanges_own_local_clock_is(self) -> None:
        # 2026-01-04 is a real Sunday; 2026-01-05 the following real
        # Monday. One second before UTC midnight, Tokyo's own local
        # clock already reads Monday 08:59:59 JST (UTC+9) -- still
        # before TSE's 9:00 open, so honestly closed. Exactly at UTC
        # midnight, Tokyo's local clock reads Monday 09:00:00 JST --
        # exactly TSE's real open. A naive "is it past UTC midnight"
        # check would get this wrong in both directions; this proves
        # the real per-exchange local-time boundary is what's used.
        just_before_midnight = compute_session(datetime(2026, 1, 4, 23, 59, 59, tzinfo=timezone.utc))
        at_midnight = compute_session(datetime(2026, 1, 5, 0, 0, 0, tzinfo=timezone.utc))
        assert just_before_midnight.current == "closed"
        assert at_midnight.current == "asian"

    def test_saturday_close_to_market_open_hours_is_still_honestly_closed(self) -> None:
        # 2026-01-10 is a real Saturday. Even at the exact UTC instant
        # that would be NYSE's real market-open window on a weekday,
        # weekend/market-closure must still win.
        saturday_at_would_be_open = compute_session(datetime(2026, 1, 10, 14, 30, 0, tzinfo=timezone.utc))
        assert saturday_at_would_be_open.current == "closed"

    def test_dst_transition_weekend_shifts_the_real_utc_open_instant_by_exactly_one_hour(self) -> None:
        # 2026-03-08 is the real US spring-forward Sunday (clocks jump
        # 2:00 AM -> 3:00 AM local). Friday 2026-03-06 (before the
        # transition) is still EST (UTC-5); Monday 2026-03-09 (after
        # it) is EDT (UTC-4). NYSE's real 9:30 ET open therefore falls
        # at a different real UTC instant on each side of the same
        # weekend -- not a same-UTC-hour-different-season comparison
        # like the test above, but the literal transition boundary
        # itself, straddled by the two nearest real trading days.
        friday_before_transition = compute_session(datetime(2026, 3, 6, 14, 30, 0, tzinfo=timezone.utc))
        monday_after_transition = compute_session(datetime(2026, 3, 9, 13, 30, 0, tzinfo=timezone.utc))
        assert friday_before_transition.current == "market_open"
        assert friday_before_transition.session_started_at == "2026-03-06T14:30:00+00:00"
        assert monday_after_transition.current == "market_open"
        assert monday_after_transition.session_started_at == "2026-03-09T13:30:00+00:00"
        # The same real UTC clock time (14:30 UTC) that was exactly
        # NYSE's open on Friday is now an hour past open on Monday --
        # proving the transition itself is honestly reflected.
        monday_at_fridays_utc_open_time = compute_session(datetime(2026, 3, 9, 14, 30, 0, tzinfo=timezone.utc))
        assert monday_at_fridays_utc_open_time.minutes_since_session_open == 60


class TestComputeNewsRisk:
    def _news(self, n: int) -> list[NewsItem]:
        return [NewsItem(id=f"n{i}", headline="Broad rally extends.", category="market", timestamp=_now_iso()) for i in range(n)]

    def test_low_activity(self) -> None:
        assert compute_news_risk(self._news(1)).risk_level == "low"

    def test_moderate_activity(self) -> None:
        assert compute_news_risk(self._news(4)).risk_level == "moderate"

    def test_elevated_activity(self) -> None:
        assert compute_news_risk(self._news(7)).risk_level == "elevated"

    def test_non_market_news_is_not_counted(self) -> None:
        news = [NewsItem(id="n1", headline="x", category="company", timestamp=_now_iso())]
        assert compute_news_risk(news).active_market_news_count == 0


class TestClassifyRegime:
    def test_strong_bull_trend(self) -> None:
        regime, label, _ = _classify_regime(avg_trend=5.0, avg_abs_trend=5.0, avg_vol=1.0, vol_ratio=1.0, sweep_share=0.0, reversal_share=0.0, volume_trend=1.0)
        assert regime == "strong_bull_trend"
        assert "Bull" in label

    def test_strong_bear_trend(self) -> None:
        regime, _, _ = _classify_regime(avg_trend=-5.0, avg_abs_trend=5.0, avg_vol=1.0, vol_ratio=1.0, sweep_share=0.0, reversal_share=0.0, volume_trend=1.0)
        assert regime == "strong_bear_trend"

    def test_liquidity_hunt_outranks_trend(self) -> None:
        regime, _, _ = _classify_regime(avg_trend=5.0, avg_abs_trend=5.0, avg_vol=1.0, vol_ratio=1.0, sweep_share=0.5, reversal_share=0.0, volume_trend=1.0)
        assert regime == "liquidity_hunt"

    def test_expansion_from_rising_volatility_ratio(self) -> None:
        regime, _, _ = _classify_regime(avg_trend=0.2, avg_abs_trend=0.2, avg_vol=1.0, vol_ratio=1.5, sweep_share=0.0, reversal_share=0.0, volume_trend=1.0)
        assert regime == "expansion"

    def test_compression_from_falling_volatility_ratio(self) -> None:
        regime, _, _ = _classify_regime(avg_trend=0.2, avg_abs_trend=0.2, avg_vol=1.0, vol_ratio=0.5, sweep_share=0.0, reversal_share=0.0, volume_trend=1.0)
        assert regime == "compression"

    def test_accumulation_proxy_from_flat_price_rising_volume(self) -> None:
        regime, _, detail = _classify_regime(avg_trend=0.1, avg_abs_trend=0.1, avg_vol=1.0, vol_ratio=1.0, sweep_share=0.0, reversal_share=0.0, volume_trend=1.3)
        assert regime == "accumulation"
        assert "proxy" in detail.lower()

    def test_distribution_proxy_from_flat_price_falling_volume(self) -> None:
        regime, _, detail = _classify_regime(avg_trend=0.1, avg_abs_trend=0.1, avg_vol=1.0, vol_ratio=1.0, sweep_share=0.0, reversal_share=0.0, volume_trend=0.7)
        assert regime == "distribution"
        assert "proxy" in detail.lower()

    def test_ordinary_sideways_range(self) -> None:
        regime, _, _ = _classify_regime(avg_trend=0.1, avg_abs_trend=0.1, avg_vol=1.0, vol_ratio=1.0, sweep_share=0.0, reversal_share=0.0, volume_trend=1.0)
        assert regime == "sideways_range"


class TestComputeHistoricalSimilarity:
    def test_no_history_is_honest(self) -> None:
        assert "No real prior" in compute_historical_similarity("sideways_range", [])

    def test_counts_real_matches(self) -> None:
        state = default_market_intelligence_state()
        report = generate_market_intelligence_report(state.model_copy(update={"regime": "sideways_range"}), _debate_stub(), _strategy_match_stub(), sim_day=1)
        other_report = generate_market_intelligence_report(state.model_copy(update={"regime": "strong_bull_trend"}), _debate_stub(), _strategy_match_stub(), sim_day=2)
        similarity = compute_historical_similarity("sideways_range", [report, other_report])
        assert "1 of the last 2" in similarity


class TestComputeMarketQuality:
    def test_avoid_trading_tier_at_a_low_composite_score(self) -> None:
        volatility = VolatilityRead(currentPct=10.0, historicalAvgPct=1.5, sessionPct=10.0, percentile=100.0, expectedPct=1.5, detail="d")
        session = SessionRead(current="closed", label="Between Sessions", overlapsActive=[], detail="d")
        news_risk = NewsRiskRead(activeMarketNewsCount=8, riskLevel="elevated", detail="d")
        quality = compute_market_quality("liquidity_hunt", volatility, session, sweep_share=0.8, news_risk=news_risk, structure_reads=[], reports_history=[], data_symbol_count=1)
        assert quality.tier in ("poor", "avoid_trading")
        assert quality.confidence_pct < 90.0

    def test_confidence_never_claims_full_certainty(self) -> None:
        volatility = VolatilityRead(currentPct=1.5, historicalAvgPct=1.5, sessionPct=1.5, percentile=50.0, expectedPct=1.5, detail="d")
        session = SessionRead(current="london_ny_overlap", label="London/New York Overlap", overlapsActive=["london", "new_york"], detail="d")
        news_risk = NewsRiskRead(activeMarketNewsCount=0, riskLevel="low", detail="d")
        quality = compute_market_quality("sideways_range", volatility, session, sweep_share=0.0, news_risk=news_risk, structure_reads=[], reports_history=[], data_symbol_count=20)
        assert quality.confidence_pct < 100.0


class TestComputeStrategyMatch:
    def _strategy(self, strategy_id: str = "strategy-1") -> Strategy:
        return Strategy(id=strategy_id, name="Momentum Breakout", description="d", createdBy="echo", focusCategory="stock", createdAt=_now_iso(), stage="market_simulation")  # type: ignore[arg-type]

    def _report(self, *, strategy_id: str = "strategy-1", best_market_environment: str) -> StrategyReport:
        return StrategyReport(
            id=f"report-{strategy_id}",
            strategyId=strategy_id,
            strategyName="Momentum Breakout",
            sourceResultId="result-1",
            scenario="bull",  # type: ignore[arg-type]
            executiveSummary="d",
            strengths=[],
            weaknesses=[],
            failureConditions=[],
            bestMarketEnvironment=best_market_environment,
            recommendedImprovements=[],
            simDay=1,
            createdAt=_now_iso(),
        )

    def test_recommends_a_strategy_with_real_positive_evidence_in_a_matching_regime(self) -> None:
        strategy = self._strategy()
        report = self._report(best_market_environment="Bull (based on this run — re-test other scenarios to compare).")
        match = compute_strategy_match("strong_bull_trend", [strategy], [report])
        assert "strategy-1" in match.recommended_strategy_ids

    def test_avoids_a_strategy_that_lost_money_in_a_matching_regime(self) -> None:
        strategy = self._strategy()
        report = self._report(best_market_environment="Not yet Bull — this run lost money under this scenario.")
        match = compute_strategy_match("strong_bull_trend", [strategy], [report])
        assert "strategy-1" in match.avoided_strategy_ids

    def test_no_real_match_is_honest(self) -> None:
        strategy = self._strategy()
        report = self._report(best_market_environment="Sideways (based on this run — re-test other scenarios to compare).")
        match = compute_strategy_match("strong_bull_trend", [strategy], [report])
        assert match.recommended_strategy_ids == []
        assert match.avoided_strategy_ids == []


class TestLearningLoop:
    def _report(self, regime: str, *, sim_day: int = 5) -> MarketIntelligenceReport:
        state = default_market_intelligence_state().model_copy(update={"regime": regime})
        return generate_market_intelligence_report(state, _debate_stub(), _strategy_match_stub(), sim_day=sim_day)

    def test_no_real_outcomes_yet_is_honest(self) -> None:
        entry = generate_learning_entry(self._report("sideways_range"), [], [])
        assert entry.regime_consistent is None
        assert entry.trades_win_rate_pct is None
        assert "nothing real to compare" in entry.lesson.lower()

    def test_consistent_regime_is_marked_true(self) -> None:
        entries = [MarketEnvironmentEntry(id="e1", regime="sideways", label="SIDEWAYS", detail="d", simMinutes=7200, createdAt=_now_iso())]
        entry = generate_learning_entry(self._report("sideways_range"), entries, [])
        assert entry.regime_consistent is True

    def test_inconsistent_regime_is_marked_false_and_explained(self) -> None:
        entries = [MarketEnvironmentEntry(id="e1", regime="bull", label="BULL MARKET", detail="d", simMinutes=7200, createdAt=_now_iso())]
        entry = generate_learning_entry(self._report("strong_bear_trend"), entries, [])
        assert entry.regime_consistent is False
        assert "did not match" in entry.lesson

    def test_real_win_rate_is_computed_from_closed_trades(self) -> None:
        trades = [_paper_trade(pnl=10.0), _paper_trade(pnl=-5.0), _paper_trade(pnl=20.0)]
        entry = generate_learning_entry(self._report("sideways_range"), [], trades)
        assert entry.trades_closed_that_day == 3
        assert entry.trades_win_rate_pct == round(2 / 3 * 100, 1)

    def test_filter_trades_for_day_buckets_by_real_closed_sim_minutes(self) -> None:
        day5_trade = _paper_trade(pnl=1.0, closed_sim_minutes=5 * 1440 + 100)
        day6_trade = _paper_trade(pnl=1.0, closed_sim_minutes=6 * 1440 + 100)
        filtered = filter_trades_for_day([day5_trade, day6_trade], 5)
        assert filtered == [day5_trade]

    def test_filter_environment_entries_for_day_buckets_by_real_sim_minutes(self) -> None:
        day5_entry = MarketEnvironmentEntry(id="e1", regime="bull", label="BULL MARKET", detail="d", simMinutes=5 * 1440 + 50, createdAt=_now_iso())
        day6_entry = MarketEnvironmentEntry(id="e2", regime="bear", label="BEAR MARKET", detail="d", simMinutes=6 * 1440 + 50, createdAt=_now_iso())
        filtered = filter_environment_entries_for_day([day5_entry, day6_entry], 6)
        assert filtered == [day6_entry]


class TestRecordCaps:
    def test_record_market_intelligence_report_caps_at_the_max(self) -> None:
        from app.market_intelligence import MAX_MARKET_INTELLIGENCE_REPORTS

        history: list[MarketIntelligenceReport] = []
        for day in range(MAX_MARKET_INTELLIGENCE_REPORTS + 5):
            state = default_market_intelligence_state()
            report = generate_market_intelligence_report(state, _debate_stub(), _strategy_match_stub(), sim_day=day)
            history = record_market_intelligence_report(history, report)
        assert len(history) == MAX_MARKET_INTELLIGENCE_REPORTS

    def test_record_learning_entry_caps_at_the_max(self) -> None:
        from app.market_intelligence import MAX_MARKET_INTELLIGENCE_LEARNING

        history: list = []
        for day in range(MAX_MARKET_INTELLIGENCE_LEARNING + 5):
            state = default_market_intelligence_state()
            report = generate_market_intelligence_report(state, _debate_stub(), _strategy_match_stub(), sim_day=day)
            entry = generate_learning_entry(report, [], [])
            history = record_learning_entry(history, entry)
        assert len(history) == MAX_MARKET_INTELLIGENCE_LEARNING


class TestComputeMarketIntelligenceStateEndToEnd:
    def test_real_mock_provider_produces_a_full_state_with_no_exceptions(self) -> None:
        provider = MockMarketDataProvider()
        watchlist = [WatchlistEntry(symbol=symbol, name=name, lastPrice=100.0, dailyChangePct=0.0, status="queued", researchProgress=0.0, assignedAgent=None) for symbol, name, _ in SEED_SYMBOLS]  # type: ignore[arg-type]
        state = compute_market_intelligence_state(watchlist, [], [], provider)
        assert state.regime is not None
        assert len(state.liquidity) == len(watchlist)
        assert len(state.structure) == len(watchlist)
        assert 0.0 <= state.quality.score <= 100.0
        assert 0.0 <= state.quality.confidence_pct <= 100.0

    def test_empty_watchlist_is_an_honest_default(self) -> None:
        provider = MockMarketDataProvider()
        state = compute_market_intelligence_state([], [], [], provider)
        assert state.regime == "sideways_range"
        assert state.liquidity == []
        assert state.structure == []


class TestDefaultMarketIntelligenceState:
    def test_fresh_game_default_is_honest_neutral(self) -> None:
        state = default_market_intelligence_state()
        assert state.quality.tier == "average"
        assert state.quality.confidence_pct < 90.0
        assert state.liquidity == []
        assert state.structure == []


def _paper_trade(*, pnl: float, closed_sim_minutes: int = 100) -> PaperTrade:
    return PaperTrade(
        id="trade-1",
        symbol="NEXA",
        side="buy",
        quantity=1.0,
        entryPrice=100.0,
        exitPrice=100.0 + pnl,
        pnl=pnl,
        pnlPct=pnl,
        durationMinutes=60,
        confidence=80.0,
        reason="test",
        marketConditions="test",
        openedAt=_now_iso(),
        closedAt=_now_iso(),
        closedSimMinutes=closed_sim_minutes,
    )


def _debate_stub():  # type: ignore[no-untyped-def]
    from app.market_debate import generate_market_debate

    return generate_market_debate(default_market_intelligence_state(), debate_id="test-debate")


def _strategy_match_stub():  # type: ignore[no-untyped-def]
    return compute_strategy_match("sideways_range", [], [])
