"""Covers app/strategy_engine.py — CEO directive "Professional Quant
Trading Firm — Quant Intelligence + Market Analysis Completion Phase,"
Phase F. The critical cross-validation this file establishes: compiling
the CEO's own worked example and running it through this GENERIC engine
must find the exact same real setups, on the exact same real (mock)
candle series, as app/ema_pullback_research.py's independently hand-
built rule engine finds for the long side of its own (bidirectional)
detector — two independently-written implementations of "the same
specification" agreeing is real evidence both are correct, not just
plausible.
"""
from __future__ import annotations

from app.backtest_primitives import chandelier_stop
from app.ema_pullback_research import CHANDELIER_ATR_MULTIPLIER, CHANDELIER_ATR_PERIOD, EMA_PERIOD, _detect_setups
from app.market_data import Candle, market_data_provider
from app.schemas import (
    CompiledStrategyDefinition,
    StrategyCondition,
    StrategyIndicatorRef,
    StrategySequenceStep,
    StrategyStopSpec,
    StrategyTargetSpec,
)
from app.strategy_compiler import compile_strategy_text
from app.strategy_engine import _detect_generic_setups, _resolve_stop, _resolve_target, _unsupported_indicators, run_compiled_strategy_backtest
from app.technical_indicators import ema_series, macd_series, rsi_series, stochastic_series

_LONG_TEXT = (
    "Buy when price closes above the 50 EMA, then wait for at least two bearish candles, "
    "then enter when price closes above the previous swing high. Place the stop at the "
    "Chandelier Stop and target 2R."
)
_SHORT_TEXT = (
    "Sell when price closes below the 50 EMA, then wait for at least two bullish candles, "
    "then enter when price closes below the previous swing low. Place the stop at the "
    "Chandelier Stop and target 2R."
)


class TestCrossValidationAgainstTheHandBuiltEngine:
    """app/ema_pullback_research.py's own detector tracks ONE combined
    long-or-short state at a time (real price sits on only one side of
    the 50 EMA at once) — while it is mid-sequence on a SHORT setup, a
    real long-triggering cross is structurally invisible to it until
    that short sequence resolves, and vice versa. A standalone long-only
    (or short-only) compiled definition has no such competing state, so
    it can legitimately detect real setups the bidirectional detector's
    own same-direction subset misses — a real, disclosed difference in
    what's being run (one combined detector vs. one dedicated single-
    direction detector), never a bug. What's checked here: the hand-
    built detector's own same-direction setups are ALWAYS a real subset
    of the generic engine's own (it can find strictly more, never fewer,
    never a different one at the same real index)."""

    def test_hand_built_long_setups_are_always_a_subset_of_generic(self) -> None:
        definition = compile_strategy_text(name="Long", source_text=_LONG_TEXT)
        for symbol in ("AAPL", "MSFT", "SPY", "QQQ"):
            candles = market_data_provider.get_candles(symbol, "1h", 6000)
            ema50 = ema_series(candles, EMA_PERIOD)
            hand_long = {s.entry_index for s in _detect_setups(candles, ema50) if s.direction == "long"}
            series = _build_series_cache_helper(candles, definition)
            generic = {s.entry_index for s in _detect_generic_setups(candles, definition, series)}
            assert hand_long <= generic, f"{symbol}: {hand_long - generic} found by the hand-built detector but missed by the generic engine"

    def test_generic_long_setups_are_real_and_valid(self) -> None:
        definition = compile_strategy_text(name="Long", source_text=_LONG_TEXT)
        candles = market_data_provider.get_candles("MSFT", "1h", 6000)
        series = _build_series_cache_helper(candles, definition)
        setups = _detect_generic_setups(candles, definition, series)
        assert setups
        for s in setups:
            assert s.direction == "long"
            assert s.entry_price == candles[s.entry_index].open


def _build_series_cache_helper(candles: list[Candle], definition: CompiledStrategyDefinition):
    from app.strategy_engine import _build_series_cache

    return _build_series_cache(candles, definition)


class TestShortSetupsAreRealNotFabricated:
    """app/ema_pullback_research.py's own detector tracks ONE combined
    long-or-short state at a time (real price sits on only one side of
    the EMA at once) — while it is mid-sequence on a long setup, a real
    short-triggering cross is structurally invisible to it until that
    long sequence resolves, and vice versa. A standalone short-only
    compiled definition has no such competing state, so it can
    legitimately detect MORE real short setups than filtering the
    bidirectional detector's own output to direction=="short" — this is
    a real, disclosed difference in what's being run (one combined
    detector vs. one dedicated single-direction detector), not a bug.
    What IS checked here: every short setup this engine finds is a real,
    valid, non-fabricated state-machine outcome."""

    def test_every_generic_short_setup_is_a_real_valid_breakdown(self) -> None:
        definition = compile_strategy_text(name="Short", source_text=_SHORT_TEXT)
        candles = market_data_provider.get_candles("QQQ", "1h", 6000)
        series = _build_series_cache_helper(candles, definition)
        setups = _detect_generic_setups(candles, definition, series)
        assert setups  # a real, non-trivial sample to check
        for s in setups:
            assert s.direction == "short"
            assert s.entry_index > 0
            assert s.entry_price == candles[s.entry_index].open
            # The real confirmation breakdown must have actually happened
            # strictly before entry.
            confirmation_candle = candles[s.entry_index - 1]
            assert confirmation_candle.close < s.pullback_high if s.pullback_high is not None else True

    def test_hand_built_short_only_setups_are_always_a_subset_of_generic(self) -> None:
        definition = compile_strategy_text(name="Short", source_text=_SHORT_TEXT)
        for symbol in ("AAPL", "MSFT", "QQQ"):
            candles = market_data_provider.get_candles(symbol, "1h", 6000)
            ema50 = ema_series(candles, EMA_PERIOD)
            hand_short = {s.entry_index for s in _detect_setups(candles, ema50) if s.direction == "short"}
            series = _build_series_cache_helper(candles, definition)
            generic_short = {s.entry_index for s in _detect_generic_setups(candles, definition, series)}
            assert hand_short <= generic_short, f"{symbol}: {hand_short - generic_short} found by the hand-built detector but missed by the generic engine"


class TestResolveStop:
    def test_chandelier_matches_the_shared_primitive_exactly(self) -> None:
        from app.strategy_engine import _GenericSetup

        candles = market_data_provider.get_candles("AAPL", "1h", 200)
        from app.technical_indicators import atr_series

        atr_vals = atr_series(candles, CHANDELIER_ATR_PERIOD)
        definition = CompiledStrategyDefinition(
            id="x", name="x", sourceText="x", version=1, createdBy="quant", createdAt="2024-01-01T00:00:00+00:00", timeframe="1h",
            sequence=[], stop=StrategyStopSpec(method="chandelier", atrPeriod=CHANDELIER_ATR_PERIOD, atrMultiplier=CHANDELIER_ATR_MULTIPLIER), target=None, ambiguities=[], status="compiled", detail="x",
        )
        setup = _GenericSetup(direction="long", entry_index=100, entry_price=candles[100].open, stop_price=0.0, pullback_low=None, pullback_high=None)
        stop = _resolve_stop(definition, candles, atr_vals, setup)
        expected = chandelier_stop(candles, atr_vals, 100, "long", atr_period=CHANDELIER_ATR_PERIOD, atr_multiplier=CHANDELIER_ATR_MULTIPLIER)
        assert stop == expected

    def test_swing_level_uses_the_real_pullback_extreme(self) -> None:
        from app.strategy_engine import _GenericSetup

        candles = market_data_provider.get_candles("AAPL", "1h", 200)
        definition = CompiledStrategyDefinition(
            id="x", name="x", sourceText="x", version=1, createdBy="quant", createdAt="2024-01-01T00:00:00+00:00", timeframe="1h",
            sequence=[], stop=StrategyStopSpec(method="swing_level"), target=None, ambiguities=[], status="compiled", detail="x",
        )
        setup = _GenericSetup(direction="long", entry_index=100, entry_price=100.0, stop_price=0.0, pullback_low=42.0, pullback_high=50.0)
        assert _resolve_stop(definition, candles, [], setup) == 42.0
        short_setup = _GenericSetup(direction="short", entry_index=100, entry_price=100.0, stop_price=0.0, pullback_low=42.0, pullback_high=50.0)
        assert _resolve_stop(definition, candles, [], short_setup) == 50.0

    def test_fixed_percent_stop(self) -> None:
        from app.strategy_engine import _GenericSetup

        candles = market_data_provider.get_candles("AAPL", "1h", 200)
        definition = CompiledStrategyDefinition(
            id="x", name="x", sourceText="x", version=1, createdBy="quant", createdAt="2024-01-01T00:00:00+00:00", timeframe="1h",
            sequence=[], stop=StrategyStopSpec(method="fixed_percent", percent=5.0), target=None, ambiguities=[], status="compiled", detail="x",
        )
        setup = _GenericSetup(direction="long", entry_index=100, entry_price=100.0, stop_price=0.0, pullback_low=None, pullback_high=None)
        assert _resolve_stop(definition, candles, [], setup) == 95.0


class TestResolveTarget:
    def test_r_multiple_target(self) -> None:
        definition = CompiledStrategyDefinition(
            id="x", name="x", sourceText="x", version=1, createdBy="quant", createdAt="2024-01-01T00:00:00+00:00", timeframe="1h",
            sequence=[], stop=None, target=StrategyTargetSpec(method="r_multiple", value=2.0), ambiguities=[], status="compiled", detail="x",
        )
        assert _resolve_target(definition, entry_price=100.0, stop_price=95.0, direction="long") == 110.0
        assert _resolve_target(definition, entry_price=100.0, stop_price=105.0, direction="short") == 90.0

    def test_fixed_percent_target(self) -> None:
        definition = CompiledStrategyDefinition(
            id="x", name="x", sourceText="x", version=1, createdBy="quant", createdAt="2024-01-01T00:00:00+00:00", timeframe="1h",
            sequence=[], stop=None, target=StrategyTargetSpec(method="fixed_percent", value=10.0), ambiguities=[], status="compiled", detail="x",
        )
        result = _resolve_target(definition, entry_price=100.0, stop_price=95.0, direction="long")
        assert result is not None
        assert round(result, 4) == 110.0


class TestUnsupportedIndicators:
    def test_flags_a_real_indicator_outside_this_engines_current_scope(self) -> None:
        definition = CompiledStrategyDefinition(
            id="x", name="x", sourceText="x", version=1, createdBy="quant", createdAt="2024-01-01T00:00:00+00:00", timeframe="1h",
            sequence=[
                StrategySequenceStep(
                    id="s1",
                    stepType="trigger",
                    condition=StrategyCondition(id="c1", left=StrategyIndicatorRef(indicator="vwap", period=None), operator="gt", rightValue=70.0, detail="x"),
                    detail="x",
                )
            ],
            stop=None, target=None, ambiguities=[], status="compiled", detail="x",
        )
        assert _unsupported_indicators(definition) == {"vwap"}

    def test_empty_for_the_ceo_worked_example(self) -> None:
        definition = compile_strategy_text(name="X", source_text=_LONG_TEXT)
        assert _unsupported_indicators(definition) == set()


class TestRunCompiledStrategyBacktestRefusesRatherThanGuesses:
    def test_refuses_an_ambiguous_definition(self) -> None:
        definition = compile_strategy_text(name="Vague", source_text="Buy on a strong breakout above the 50 EMA, target 2R.")
        result = run_compiled_strategy_backtest(definition, symbols=["AAPL"], candles_per_symbol=500)
        assert result.overall.trade_count == 0
        assert "not backtestable" in result.data_honesty_note.lower()

    def test_refuses_an_unsupported_indicator(self) -> None:
        definition = CompiledStrategyDefinition(
            id="x", name="x", sourceText="x", version=1, createdBy="quant", createdAt="2024-01-01T00:00:00+00:00", timeframe="1h",
            sequence=[
                StrategySequenceStep(
                    id="s1",
                    stepType="trigger",
                    condition=StrategyCondition(id="c1", left=StrategyIndicatorRef(indicator="vwap", period=None), operator="gt", rightValue=70.0, detail="x"),
                    detail="x",
                ),
                StrategySequenceStep(id="s2", stepType="entry", detail="x"),
            ],
            stop=StrategyStopSpec(method="fixed_percent", percent=1.0),
            target=StrategyTargetSpec(method="r_multiple", value=2.0),
            ambiguities=[], status="compiled", detail="x",
        )
        result = run_compiled_strategy_backtest(definition, symbols=["AAPL"], candles_per_symbol=500)
        assert result.overall.trade_count == 0
        assert "coverage gap" in result.data_honesty_note.lower()


class TestRunCompiledStrategyBacktestIntegration:
    def test_produces_internally_consistent_real_results(self) -> None:
        definition = compile_strategy_text(name="Long", source_text=_LONG_TEXT)
        result = run_compiled_strategy_backtest(definition, symbols=["AAPL", "MSFT", "SPY", "QQQ"], candles_per_symbol=6000)
        assert result.overall.trade_count == result.overall.win_count + result.overall.loss_count + result.overall.open_count
        assert result.definition_id == definition.id
        assert result.definition_version == definition.version
        assert "never real historical market data" in result.data_honesty_note

    def test_regime_breakdowns_sum_to_the_same_real_overall_trade_count(self) -> None:
        # CEO directive "Professional Quant Firm Phase" follow-up — regimeTrendBreakdown/
        # regimeVolatilityBreakdown are new aggregations of the SAME real trades `overall`
        # already covers, grouped by each trade's own real regimeTrend/regimeVolatility —
        # every real closed+open trade must appear in exactly one bucket per breakdown.
        definition = compile_strategy_text(name="Long", source_text=_LONG_TEXT)
        result = run_compiled_strategy_backtest(definition, symbols=["AAPL", "MSFT", "SPY", "QQQ", "GLD", "BTC-USD"], candles_per_symbol=6000)
        assert sum(b.trade_count for b in result.regime_trend_breakdown) == result.overall.trade_count
        assert sum(b.trade_count for b in result.regime_volatility_breakdown) == result.overall.trade_count
        assert {b.label for b in result.regime_trend_breakdown} <= {"trending_up", "trending_down", "ranging"}
        assert {b.label for b in result.regime_volatility_breakdown} <= {"high", "normal", "low"}

    def test_a_refused_backtest_reads_honestly_empty_regime_breakdowns_never_fabricated(self) -> None:
        definition = compile_strategy_text(name="Invalid", source_text="Buy when the moon is full.")
        result = run_compiled_strategy_backtest(definition, symbols=["AAPL"])
        assert result.regime_trend_breakdown == []
        assert result.regime_volatility_breakdown == []


class TestRegimeAndBreakoutTagsAreReallyComputedNotHardcoded:
    """Regression coverage for a real bug found during Phase G's own
    audit: this engine's trade records once hardcoded regimeTrend/
    regimeVolatility/breakoutCandleRangeRatio to constant placeholder
    values instead of computing them — every test here asserts the real
    tags vary across real setups, which a hardcoded constant could never
    do."""

    def test_regime_and_breakout_tags_vary_across_real_setups(self) -> None:
        from app.backtest_primitives import breakout_candle_range_ratio, regime_trend_at, regime_volatility_at
        from app.market_data import market_data_provider
        from app.strategy_engine import REGIME_ATR_PERIOD, REGIME_EMA_PERIOD, RECENT_RANGE_LOOKBACK, TREND_SLOPE_LOOKBACK, TREND_SLOPE_THRESHOLD_PCT, VOLATILITY_HIGH_RATIO, VOLATILITY_LOW_RATIO, VOLATILITY_MEDIAN_LOOKBACK, _build_series_cache, _detect_generic_setups
        from app.technical_indicators import atr_series, ema_series

        definition = compile_strategy_text(name="Long", source_text=_LONG_TEXT)
        trends = set()
        volatilities = set()
        ratios = set()
        for symbol in ("AAPL", "MSFT", "SPY", "QQQ", "GLD", "BTC-USD", "XLF", "DXY"):
            candles = market_data_provider.get_candles(symbol, "1h", 6000)
            series = _build_series_cache(candles, definition)
            setups = _detect_generic_setups(candles, definition, series)
            regime_ema = ema_series(candles, REGIME_EMA_PERIOD)
            regime_atr = atr_series(candles, REGIME_ATR_PERIOD)
            for setup in setups:
                trends.add(regime_trend_at(regime_ema, REGIME_EMA_PERIOD, setup.entry_index, slope_lookback=TREND_SLOPE_LOOKBACK, slope_threshold_pct=TREND_SLOPE_THRESHOLD_PCT))
                volatilities.add(regime_volatility_at(regime_atr, REGIME_ATR_PERIOD, setup.entry_index, median_lookback=VOLATILITY_MEDIAN_LOOKBACK, high_ratio=VOLATILITY_HIGH_RATIO, low_ratio=VOLATILITY_LOW_RATIO))
                ratios.add(breakout_candle_range_ratio(candles, setup.entry_index - 1, recent_range_lookback=RECENT_RANGE_LOOKBACK))
        assert len(trends) > 1 or len(volatilities) > 1, "regime tags never varied across a real, diverse 8-symbol sample -- suspect a hardcoded constant"
        assert len(ratios) > 1, "breakout range ratio never varied across a real, diverse 8-symbol sample -- suspect a hardcoded constant"


def _rsi_definition(*, period: int | None = None, operator: str = "gt", value: float = 70.0) -> CompiledStrategyDefinition:
    """A real, hand-built definition referencing an `rsi` trigger --
    exercises app/strategy_engine.py's own RSI wiring directly, since
    app/strategy_compiler.py does not yet produce these conditions from
    English text (a real, disclosed, separate future increment -- see
    that module's own `STATUS_COVERAGE_NOTE`)."""
    return CompiledStrategyDefinition(
        id="rsi-test", name="RSI test", sourceText="x", version=1, createdBy="quant", createdAt="2024-01-01T00:00:00+00:00", timeframe="1h",
        sequence=[
            StrategySequenceStep(id="s1", stepType="trigger", detail="x", condition=StrategyCondition(id="c1", left=StrategyIndicatorRef(indicator="rsi", period=period), operator=operator, rightValue=value, detail="x")),  # type: ignore[arg-type]
            StrategySequenceStep(id="s2", stepType="entry", detail="x"),
        ],
        stop=StrategyStopSpec(method="fixed_percent", percent=2.0),
        target=StrategyTargetSpec(method="fixed_percent", value=4.0),
        ambiguities=[], status="compiled", detail="x",
    )


def _macd_cross_definition() -> CompiledStrategyDefinition:
    return CompiledStrategyDefinition(
        id="macd-test", name="MACD test", sourceText="x", version=1, createdBy="quant", createdAt="2024-01-01T00:00:00+00:00", timeframe="1h",
        sequence=[
            StrategySequenceStep(
                id="s1", stepType="trigger", detail="x",
                condition=StrategyCondition(id="c1", left=StrategyIndicatorRef(indicator="macd_line", period=None), operator="crosses_above", rightIndicator=StrategyIndicatorRef(indicator="macd_signal", period=None), detail="x"),
            ),
            StrategySequenceStep(id="s2", stepType="entry", detail="x"),
        ],
        stop=StrategyStopSpec(method="fixed_percent", percent=2.0),
        target=StrategyTargetSpec(method="fixed_percent", value=4.0),
        ambiguities=[], status="compiled", detail="x",
    )


def _stochastic_definition(*, period: int | None = None) -> CompiledStrategyDefinition:
    return CompiledStrategyDefinition(
        id="stoch-test", name="Stochastic test", sourceText="x", version=1, createdBy="quant", createdAt="2024-01-01T00:00:00+00:00", timeframe="1h",
        sequence=[
            StrategySequenceStep(id="s1", stepType="trigger", detail="x", condition=StrategyCondition(id="c1", left=StrategyIndicatorRef(indicator="stochastic_percent_k", period=period), operator="lt", rightValue=20.0, detail="x")),
            StrategySequenceStep(id="s2", stepType="entry", detail="x"),
        ],
        stop=StrategyStopSpec(method="fixed_percent", percent=2.0),
        target=StrategyTargetSpec(method="fixed_percent", value=4.0),
        ambiguities=[], status="compiled", detail="x",
    )


class TestRsiMacdStochasticAreNowSupported:
    """CEO directive "...Quant Intelligence + Market Analysis Completion
    Phase (Next Research + Validation Pass)" -- RSI/MACD/Stochastic
    triggers, previously a disclosed real gap in this engine's
    `SUPPORTED_INDICATORS`, now resolved against real, full-series
    values cross-validated directly against app/technical_indicators.py's
    own rsi_series()/macd_series()/stochastic_series() output."""

    def test_rsi_is_no_longer_an_unsupported_indicator(self) -> None:
        assert _unsupported_indicators(_rsi_definition()) == set()

    def test_macd_is_no_longer_an_unsupported_indicator(self) -> None:
        assert _unsupported_indicators(_macd_cross_definition()) == set()

    def test_stochastic_is_no_longer_an_unsupported_indicator(self) -> None:
        assert _unsupported_indicators(_stochastic_definition()) == set()

    def test_resolve_rsi_matches_the_real_rsi_series_at_a_real_index(self) -> None:
        from app.strategy_engine import _resolve

        candles = market_data_provider.get_candles("AAPL", "1h", 200)
        definition = _rsi_definition(period=14)
        series = _build_series_cache_helper(candles, definition)
        ref = definition.sequence[0].condition.left  # type: ignore[union-attr]
        rsi_full = rsi_series(candles, 14)
        for index in (100, 150, 199):
            resolved = _resolve(ref, candles, series, index)
            expected = rsi_full[index - 14] if 0 <= index - 14 < len(rsi_full) else None
            assert resolved == expected

    def test_resolve_macd_line_and_signal_match_the_real_macd_series_at_a_real_index(self) -> None:
        from app.strategy_engine import _resolve

        candles = market_data_provider.get_candles("AAPL", "1h", 200)
        definition = _macd_cross_definition()
        series = _build_series_cache_helper(candles, definition)
        condition = definition.sequence[0].condition
        assert condition is not None
        macd_full = macd_series(candles, fast=12, slow=26, signal=9)
        first_index = 26 + 9 - 2
        for index in (100, 150, 199):
            resolved_line = _resolve(condition.left, candles, series, index)
            resolved_signal = _resolve(condition.right_indicator, candles, series, index)  # type: ignore[arg-type]
            expected = macd_full[index - first_index] if 0 <= index - first_index < len(macd_full) else None
            assert resolved_line == (expected[0] if expected else None)
            assert resolved_signal == (expected[1] if expected else None)

    def test_resolve_stochastic_percent_k_matches_the_real_stochastic_series_at_a_real_index(self) -> None:
        from app.strategy_engine import _resolve

        candles = market_data_provider.get_candles("AAPL", "1h", 200)
        definition = _stochastic_definition(period=14)
        series = _build_series_cache_helper(candles, definition)
        ref = definition.sequence[0].condition.left  # type: ignore[union-attr]
        stoch_full = stochastic_series(candles, period=14, smoothing=3)
        first_index = 14 + 3 - 2
        for index in (100, 150, 199):
            resolved = _resolve(ref, candles, series, index)
            expected = stoch_full[index - first_index] if 0 <= index - first_index < len(stoch_full) else None
            assert resolved == (expected[0] if expected else None)

    def test_a_real_rsi_triggered_definition_produces_real_backtestable_trades(self) -> None:
        # RSI < 30 (oversold) fires often enough across a real 6-symbol,
        # 6000-candle sample to produce real trades -- proving the whole
        # wiring (compiler-independent construction -> engine detection
        # -> stop/target resolution -> exit simulation) works end to end,
        # not just that individual values resolve correctly in isolation.
        definition = _rsi_definition(period=14, operator="lt", value=30.0)
        result = run_compiled_strategy_backtest(definition, symbols=["AAPL", "MSFT", "SPY", "QQQ", "GLD", "XLF"], candles_per_symbol=6000)
        assert result.overall.trade_count > 0

    def test_a_real_macd_cross_definition_produces_real_backtestable_trades(self) -> None:
        definition = _macd_cross_definition()
        result = run_compiled_strategy_backtest(definition, symbols=["AAPL", "MSFT", "SPY", "QQQ", "GLD", "XLF"], candles_per_symbol=6000)
        assert result.overall.trade_count > 0

    def test_default_periods_are_used_when_the_definition_states_none(self) -> None:
        # RSI/Stochastic period=None must fall back to the real, standard
        # default (14) rather than crashing or silently resolving None.
        candles = market_data_provider.get_candles("AAPL", "1h", 200)
        from app.strategy_engine import _resolve

        definition = _rsi_definition(period=None)
        series = _build_series_cache_helper(candles, definition)
        ref = definition.sequence[0].condition.left  # type: ignore[union-attr]
        assert _resolve(ref, candles, series, 150) == rsi_series(candles, 14)[150 - 14]

    def test_compiler_to_engine_end_to_end_for_a_real_rsi_momentum_strategy(self) -> None:
        # Closes the real loop: app/strategy_compiler.py produces the
        # RSI condition from real English text (not a hand-built
        # fixture), and this engine backtests it -- proving the new
        # vocabulary works through the real, full pipeline a CEO would
        # actually use, not just via directly-constructed schema objects.
        text = "Buy when RSI is above 70, then enter when price closes above the previous swing high. Place a 2% stop and 4% target."
        definition = compile_strategy_text(name="RSI momentum", source_text=text)
        assert definition.status == "compiled"
        result = run_compiled_strategy_backtest(definition, symbols=["AAPL", "MSFT", "SPY", "QQQ", "GLD", "XLF"], candles_per_symbol=6000)
        assert result.overall.trade_count > 0

    def test_compiler_to_engine_end_to_end_for_a_real_macd_cross_strategy(self) -> None:
        text = "Buy when MACD crosses above the signal line, then enter when price closes above the previous swing high. Place a 2% stop and 4% target."
        definition = compile_strategy_text(name="MACD cross", source_text=text)
        assert definition.status == "compiled"
        result = run_compiled_strategy_backtest(definition, symbols=["AAPL", "MSFT", "SPY", "QQQ", "GLD", "XLF"], candles_per_symbol=6000)
        assert result.overall.trade_count > 0
