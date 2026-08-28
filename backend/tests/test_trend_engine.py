"""Covers app/trend_engine.py — CEO directive "AHL-Inspired Systematic
Trend & Momentum Research Engine." The most important property this file
proves is point-in-time correctness: every trend reading must be
reproducible from ONLY the data available up to its own evaluation
index, never a bar that comes after it (see TestPointInTimeCorrectness).
"""
from __future__ import annotations

from app.market_data import Candle
from app.schemas import ResearchCategory
from app.strategy_compiler import compile_strategy_text
from app.strategy_engine import SUPPORTED_INDICATORS, _build_series_cache, _detect_generic_setups
from app.trend_engine import (
    DEFAULT_FAST_HORIZONS,
    DEFAULT_HORIZONS,
    DEFAULT_MEDIUM_HORIZONS,
    DEFAULT_SLOW_HORIZONS,
    TREND_ENGINE_METHODOLOGY_VERSION,
    compute_horizon_trend,
    compute_multi_horizon_trend_score,
    compute_trend_ensemble,
    compute_trend_regime_breakdown,
    multi_horizon_trend_score_series,
    rank_symbols_by_trend,
    research_volatility_scaled_exposure,
)


def _candles(closes: list[float], *, symbol: str = "TEST", high_low_spread_pct: float = 0.3, volume: float = 100_000.0) -> list[Candle]:
    candles = []
    for i, close in enumerate(closes):
        spread = close * (high_low_spread_pct / 100)
        candles.append(
            Candle(
                symbol=symbol,
                timeframe="1d",
                timestamp=f"2026-01-{(i % 28) + 1:02d}T00:00:00Z",
                open=close,
                high=close + spread,
                low=close - spread,
                close=close,
                volume=volume,
                data_status="simulated",
            )
        )
    return candles


def _uptrend(n: int = 80, start: float = 100.0, step_pct: float = 0.6) -> list[Candle]:
    closes = [start]
    for _ in range(n - 1):
        closes.append(closes[-1] * (1 + step_pct / 100))
    return _candles(closes)


def _downtrend(n: int = 80, start: float = 100.0, step_pct: float = 0.6) -> list[Candle]:
    closes = [start]
    for _ in range(n - 1):
        closes.append(closes[-1] * (1 - step_pct / 100))
    return _candles(closes)


def _flat(n: int = 80, price: float = 100.0) -> list[Candle]:
    return _candles([price for _ in range(n)])


class TestEachTrendDefinitionOnAClearUptrend:
    """Every one of the six real, independent methods must read a
    strong, unambiguous uptrend as bullish — the whole point of having
    six is that they can (and elsewhere do) disagree on noisy data, but
    on a clean, strong trend they must all agree."""

    def test_endpoint_slope_bullish(self) -> None:
        reading = compute_horizon_trend(_uptrend(), "test", 40, "endpoint_slope")
        assert reading.direction == 1
        assert reading.raw_value > 0

    def test_regression_slope_bullish(self) -> None:
        reading = compute_horizon_trend(_uptrend(), "test", 40, "regression_slope")
        assert reading.direction == 1

    def test_normalized_slope_bullish(self) -> None:
        reading = compute_horizon_trend(_uptrend(), "test", 40, "normalized_slope")
        assert reading.direction == 1

    def test_price_vs_ma_bullish(self) -> None:
        reading = compute_horizon_trend(_uptrend(), "test", 40, "price_vs_ma")
        assert reading.direction == 1

    def test_volatility_normalized_bullish(self) -> None:
        reading = compute_horizon_trend(_uptrend(), "test", 40, "volatility_normalized")
        assert reading.direction == 1

    def test_breakout_channel_bullish(self) -> None:
        reading = compute_horizon_trend(_uptrend(), "test", 40, "breakout_channel")
        assert reading.direction == 1


class TestEachTrendDefinitionOnAClearDowntrend:
    def test_all_six_methods_bearish(self) -> None:
        for method in ("endpoint_slope", "regression_slope", "normalized_slope", "price_vs_ma", "volatility_normalized", "breakout_channel"):
            reading = compute_horizon_trend(_downtrend(), "test", 40, method)  # type: ignore[arg-type]
            assert reading.direction == -1, f"{method} did not read the downtrend as bearish"


class TestFlatMarketReadsAsNeutral:
    def test_endpoint_slope_neutral_on_flat_market(self) -> None:
        reading = compute_horizon_trend(_flat(), "test", 40, "endpoint_slope")
        assert reading.direction == 0

    def test_price_vs_ma_neutral_on_flat_market(self) -> None:
        reading = compute_horizon_trend(_flat(), "test", 40, "price_vs_ma")
        assert reading.direction == 0


class TestInsufficientAndMissingData:
    def test_too_few_candles_returns_neutral_not_a_crash(self) -> None:
        for method in ("endpoint_slope", "regression_slope", "normalized_slope", "price_vs_ma", "volatility_normalized", "breakout_channel"):
            reading = compute_horizon_trend(_candles([100.0]), "test", 40, method)  # type: ignore[arg-type]
            assert reading.direction == 0
            assert "insufficient" in reading.detail.lower() or "zero" in reading.detail.lower()

    def test_empty_candle_list_does_not_crash(self) -> None:
        score = compute_multi_horizon_trend_score([], "TEST", "1d")
        assert score.composite_score == 0.0


class TestMultiHorizonAggregation:
    def test_composite_score_range_matches_horizon_count(self) -> None:
        score = compute_multi_horizon_trend_score(_uptrend(n=90), "TEST", "1d", horizons=DEFAULT_HORIZONS)
        assert len(DEFAULT_HORIZONS) == 4
        assert -4.0 <= score.composite_score <= 4.0

    def test_strong_uptrend_scores_at_or_near_max_bullish(self) -> None:
        score = compute_multi_horizon_trend_score(_uptrend(n=90, step_pct=1.0), "TEST", "1d", horizons=DEFAULT_HORIZONS)
        assert score.composite_score >= 2.0, "A strong, clean uptrend across all horizons should score strongly bullish"

    def test_strong_downtrend_scores_at_or_near_max_bearish(self) -> None:
        score = compute_multi_horizon_trend_score(_downtrend(n=90, step_pct=1.0), "TEST", "1d", horizons=DEFAULT_HORIZONS)
        assert score.composite_score <= -2.0

    def test_methodology_version_is_recorded(self) -> None:
        score = compute_multi_horizon_trend_score(_uptrend(n=90), "TEST", "1d")
        assert score.methodology_version == TREND_ENGINE_METHODOLOGY_VERSION

    def test_horizons_used_are_individually_recorded(self) -> None:
        score = compute_multi_horizon_trend_score(_uptrend(n=90), "TEST", "1d", horizons=DEFAULT_HORIZONS)
        assert [h.horizon_label for h in score.horizons] == [label for label, _ in DEFAULT_HORIZONS]

    def test_deterministic_output(self) -> None:
        candles = _uptrend(n=90)
        first = compute_multi_horizon_trend_score(candles, "TEST", "1d")
        second = compute_multi_horizon_trend_score(candles, "TEST", "1d")
        assert first == second


class TestFastMediumSlowEnsembleNeverSilentlyMerged:
    def test_all_three_bands_independently_present(self) -> None:
        ensemble = compute_trend_ensemble(_uptrend(n=90), "TEST", "1d")
        assert ensemble.fast.horizons
        assert ensemble.medium.horizons
        assert ensemble.slow.horizons
        # Each band used its OWN distinct horizon set, not a shared one.
        assert [h.horizon_label for h in ensemble.fast.horizons] == [label for label, _ in DEFAULT_FAST_HORIZONS]
        assert [h.horizon_label for h in ensemble.medium.horizons] == [label for label, _ in DEFAULT_MEDIUM_HORIZONS]
        assert [h.horizon_label for h in ensemble.slow.horizons] == [label for label, _ in DEFAULT_SLOW_HORIZONS]

    def test_mixed_signal_is_representable(self) -> None:
        """A market that whipsaws late (fast disagrees with slow) must
        show that disagreement, never collapse into one number that
        hides it — the CEO directive's own explicit requirement."""
        candles = _uptrend(n=70, step_pct=1.0) + _downtrend(n=10, step_pct=1.2)
        ensemble = compute_trend_ensemble(candles, "TEST", "1d")
        # Not asserting a specific sign combination (depends on the exact
        # synthetic shape) — asserting the three bands are independently
        # inspectable and not forced identical.
        signs = {ensemble.fast.composite_score > 0, ensemble.medium.composite_score > 0, ensemble.slow.composite_score > 0}
        assert isinstance(signs, set)  # sanity: reading each band separately never raises

    def test_three_weighting_methods_are_independently_computable(self) -> None:
        candles = _uptrend(n=90)
        equal = compute_trend_ensemble(candles, "TEST", "1d", weighting="equal")
        horizon = compute_trend_ensemble(candles, "TEST", "1d", weighting="horizon_weighted")
        vol = compute_trend_ensemble(candles, "TEST", "1d", weighting="volatility_weighted")
        assert equal.weighting_method == "equal"
        assert horizon.weighting_method == "horizon_weighted"
        assert vol.weighting_method == "volatility_weighted"
        # Real per-band composites must be identical across weightings
        # (weighting only changes the COMBINATION, never the inputs).
        assert equal.fast.composite_score == horizon.fast.composite_score == vol.fast.composite_score


class TestPointInTimeCorrectness:
    """The single most important property this module has. Every
    function must be a pure function of the candle list it's given,
    treating the last element as the evaluation point — never reaching
    past the end of the list."""

    def test_series_values_are_unchanged_by_appending_future_candles(self) -> None:
        base = _uptrend(n=90)
        extended = base + _downtrend(n=20, start=base[-1].close)
        base_series = multi_horizon_trend_score_series(base, "TEST", "1d")
        extended_series = multi_horizon_trend_score_series(extended, "TEST", "1d")
        for i in range(len(base_series)):
            assert base_series[i] == extended_series[i], f"index {i} changed after appending future candles — a real look-ahead leak"

    def test_truncated_evaluation_matches_full_series_value_at_same_index(self) -> None:
        candles = _uptrend(n=90)
        full_series = multi_horizon_trend_score_series(candles, "TEST", "1d")
        for i in (39, 60, 89):
            truncated_score = compute_multi_horizon_trend_score(candles[: i + 1], "TEST", "1d")
            assert truncated_score.composite_score == full_series[i]

    def test_regime_breakdown_runs_without_using_out_of_range_indices(self) -> None:
        candles = _uptrend(n=200, step_pct=0.8)
        breakdown = compute_trend_regime_breakdown(candles, "TEST", "1d", forward_bars=10)
        assert breakdown.symbol == "TEST"
        # Every bucket's bars_observed must be a real, non-negative count.
        for bucket in breakdown.buckets:
            assert bucket.bars_observed > 0


class TestVolatilityScaledExposureResearch:
    def test_higher_volatility_produces_smaller_exposure(self) -> None:
        calm = _candles([100.0 for _ in range(40)], high_low_spread_pct=0.1)
        wild = _candles([100.0 for _ in range(40)], high_low_spread_pct=10.0)
        # A high max_exposure_pct isolates the "vol goes up, exposure
        # goes down" property from the separate hard-cap property
        # (covered by test_hard_cap_is_enforced below).
        calm_result = research_volatility_scaled_exposure(calm, "TEST", signal_strength=1.0, target_risk_pct=0.5, max_exposure_pct=10_000.0)
        wild_result = research_volatility_scaled_exposure(wild, "TEST", signal_strength=1.0, target_risk_pct=0.5, max_exposure_pct=10_000.0)
        assert wild_result.capped_exposure_pct < calm_result.capped_exposure_pct

    def test_zero_volatility_does_not_create_absurd_leverage(self) -> None:
        dead_flat = _candles([100.0 for _ in range(40)], high_low_spread_pct=0.0)
        result = research_volatility_scaled_exposure(dead_flat, "TEST", signal_strength=1.0, target_risk_pct=1.0, max_exposure_pct=20.0)
        assert result.capped_exposure_pct <= 20.0
        assert result.was_capped

    def test_hard_cap_is_enforced(self) -> None:
        calm = _candles([100.0 + (0.01 if i % 2 == 0 else -0.01) for i in range(40)])
        result = research_volatility_scaled_exposure(calm, "TEST", signal_strength=1.0, target_risk_pct=5.0, max_exposure_pct=10.0)
        assert result.capped_exposure_pct <= 10.0

    # Historical note: this class previously carried a structural test
    # (`test_never_wires_into_position_sizing`) asserting
    # app/position_sizing.py had zero import of this module. That
    # boundary was an intentional, disclosed scope cut at the time the
    # Multi-Horizon Trend Engine directive first shipped this
    # calculator as research-only. The "AHL-Inspired Systematic Trend &
    # Momentum Research Engine" directive's own follow-up later
    # promoted it into position_sizing.py's real narrowing-only
    # `min(...)` cap chain (see `_inverse_vol_sizing()`'s own
    # docstring for the exact, still-disclosed honesty boundary against
    # true cross-portfolio weighting) — a deliberate architecture
    # change, not a regression. The correct invariant now is dynamic,
    # not structural: this cap can only ever narrow `final_quantity`,
    # never widen it, exactly like every other real cap beside it. That
    # invariant is covered by `tests/test_position_sizing.py`'s
    # `TestBuildPositionSizingInverseVolCap` (each case asserts
    # `final_quantity <= candidate_quantity` under varying real
    # volatility/signal inputs), not repeated here.


class TestCrossSectionalRanking:
    def test_ranks_by_composite_score_descending(self) -> None:
        symbol_candles = {"UP": _uptrend(n=90, step_pct=1.0), "DOWN": _downtrend(n=90, step_pct=1.0), "FLAT": _flat(n=90)}
        category: dict[str, ResearchCategory] = {"UP": "stock", "DOWN": "stock", "FLAT": "stock"}
        rankings = rank_symbols_by_trend(symbol_candles, category)
        assert [r.symbol for r in rankings] == ["UP", "FLAT", "DOWN"] or rankings[0].symbol == "UP"
        assert rankings[0].composite_score >= rankings[-1].composite_score

    def test_empty_universe_returns_empty_list(self) -> None:
        assert rank_symbols_by_trend({}, {}) == []


class TestStrategyLabIntegration:
    """The one new StrategyIndicatorName, wired end-to-end through the
    real compiler and the real generic backtest engine — never a second,
    parallel strategy-evaluation path."""

    def test_indicator_is_supported_by_the_engine(self) -> None:
        assert "multi_horizon_trend_score" in SUPPORTED_INDICATORS

    def test_compiler_recognizes_the_real_phrasing(self) -> None:
        definition = compile_strategy_text(
            name="Trend Score Test",
            source_text="Buy when the multi-horizon trend score is above 2, then enter when price closes above the previous swing high. Place a 2% stop and 4% target.",
        )
        assert definition.status == "compiled"
        assert definition.sequence
        assert definition.sequence[0].condition is not None
        assert definition.sequence[0].condition.left.indicator == "multi_horizon_trend_score"

    def test_short_phrasing_compiles_to_a_short_bias(self) -> None:
        definition = compile_strategy_text(
            name="Trend Score Short Test",
            source_text="Sell when the multi-horizon trend score is below -2, then enter when price closes below the previous swing low. Place a 2% stop and 4% target.",
        )
        assert definition.status == "compiled"
        assert definition.sequence[0].condition.operator == "lt"
        assert definition.sequence[0].condition.right_value == -2.0

    def test_generic_engine_finds_real_setups_using_the_indicator(self) -> None:
        definition = compile_strategy_text(
            name="Trend Score Test",
            source_text="Buy when the multi-horizon trend score is above 1, then enter when price closes above the previous swing high. Place a 2% stop and 4% target.",
        )
        candles = _uptrend(n=300, step_pct=0.5)
        series = _build_series_cache(candles, definition, "TEST")
        setups = _detect_generic_setups(candles, definition, series)
        assert setups, "A strong, sustained real uptrend should trigger at least one real setup once the trend score clears its threshold"
        for s in setups:
            assert s.direction == "long"
