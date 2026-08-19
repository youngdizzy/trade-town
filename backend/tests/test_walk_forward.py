"""Covers app/walk_forward.py — CEO directive "Professional Quant
Trading Firm — Quant Intelligence + Market Analysis Completion Phase
(Next Research + Validation Pass)," item 4. The critical guarantee this
file establishes: windows are real, disjoint, non-overlapping
chronological slices of the same real candle series, and the verdict
computation never forces a call from too few real evaluated windows.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.backtest_primitives import aggregate_bucket
from app.market_data import market_data_provider
from app.schemas import CompiledStrategyDefinition, StrategyCondition, StrategyIndicatorRef, StrategySequenceStep, StrategyStopSpec, StrategyTargetSpec
from app.strategy_compiler import compile_strategy_text
from app.strategy_engine import DEFAULT_TIMEFRAME, backtest_symbol_over_candles
from app.walk_forward import MIN_EVALUATED_WINDOWS_FOR_VERDICT, run_walk_forward_validation

_CEO_TEXT = (
    "Buy when price closes above the 50 EMA, then wait for at least two bearish candles, "
    "then enter when price closes above the previous swing high. Place the stop at the "
    "Chandelier Stop and target 2R."
)


def _invalid_definition() -> CompiledStrategyDefinition:
    return compile_strategy_text(name="Nonsense", source_text="Buy when the moon is full and Mercury is in retrograde.")


def _unsupported_indicator_definition() -> CompiledStrategyDefinition:
    now = datetime.now(timezone.utc).isoformat()
    return CompiledStrategyDefinition(
        id="vwap-test",
        name="VWAP test",
        sourceText="x",
        version=1,
        createdBy="quant",
        createdAt=now,
        timeframe="1h",
        sequence=[
            StrategySequenceStep(id="s1", stepType="trigger", detail="x", condition=StrategyCondition(id="c1", left=StrategyIndicatorRef(indicator="vwap", period=None), operator="gt", rightValue=70.0, detail="x")),
            StrategySequenceStep(id="s2", stepType="entry", detail="x"),
        ],
        stop=StrategyStopSpec(method="fixed_percent", percent=1.0),
        target=StrategyTargetSpec(method="fixed_percent", value=2.0),
        ambiguities=[],
        status="compiled",
        detail="x",
    )


def _high_frequency_definition() -> CompiledStrategyDefinition:
    """A real, deliberately high-setup-frequency definition (a bare fast/
    slow EMA cross, no pullback requirement) — used only to exercise the
    "stable"/"unstable" verdict paths, which the CEO's own real 50 EMA
    pullback example is too sparse (by real design) to ever reach at any
    reasonable window size. Constructed directly rather than compiled,
    the same pattern app/tests/test_strategy_engine.py's own
    TestUnsupportedIndicators/TestRunCompiledStrategyBacktestRefuses...
    classes already use for a hand-built `CompiledStrategyDefinition`."""
    now = datetime.now(timezone.utc).isoformat()
    return CompiledStrategyDefinition(
        id="hf-test",
        name="HF test",
        sourceText="x",
        version=1,
        createdBy="quant",
        createdAt=now,
        timeframe="1h",
        sequence=[
            StrategySequenceStep(
                id="s1",
                stepType="trigger",
                detail="x",
                condition=StrategyCondition(id="c1", left=StrategyIndicatorRef(indicator="ema", period=5), operator="crosses_above", rightIndicator=StrategyIndicatorRef(indicator="ema", period=20), detail="x"),
            ),
            StrategySequenceStep(id="s2", stepType="entry", detail="x"),
        ],
        stop=StrategyStopSpec(method="fixed_percent", percent=1.0),
        target=StrategyTargetSpec(method="fixed_percent", value=2.0),
        ambiguities=[],
        status="compiled",
        detail="x",
    )


class TestRefusesRatherThanGuesses:
    def test_an_invalid_definition_is_refused(self) -> None:
        result = run_walk_forward_validation(_invalid_definition(), symbols=["AAPL"])
        assert result.verdict == "insufficient_data"
        assert result.symbols == []
        assert "not backtestable" in result.detail

    def test_an_unsupported_indicator_is_refused(self) -> None:
        result = run_walk_forward_validation(_unsupported_indicator_definition(), symbols=["AAPL"])
        assert result.symbols == []
        assert "cannot resolve indicator" in result.detail

    def test_a_window_too_small_to_ever_produce_a_setup_is_refused(self) -> None:
        result = run_walk_forward_validation(compile_strategy_text(name="x", source_text=_CEO_TEXT), symbols=["AAPL"], window_bars=10)
        assert result.symbols == []
        assert "too small" in result.detail


class TestWindowsAreRealDisjointChronologicalSlices:
    def test_windows_are_consecutive_and_non_overlapping(self) -> None:
        definition = _high_frequency_definition()
        result = run_walk_forward_validation(definition, symbols=["AAPL"], candles_per_symbol=6000, window_bars=1500)
        symbol_result = result.symbols[0]
        assert len(symbol_result.windows) == 4  # 6000 // 1500, no trailing partial window
        # Consecutive windows must never overlap in real time -- each
        # window's own start must be strictly after the previous window's
        # own end.
        for earlier, later in zip(symbol_result.windows, symbol_result.windows[1:]):
            assert earlier.end_timestamp < later.start_timestamp

    def test_a_trailing_partial_window_is_dropped_not_tested_as_if_full(self) -> None:
        definition = _high_frequency_definition()
        result = run_walk_forward_validation(definition, symbols=["AAPL"], candles_per_symbol=6000, window_bars=1700)
        # 6000 // 1700 == 3 full windows; the remaining 900 real bars are
        # never backtested as a real, comparable fourth window.
        assert len(result.symbols[0].windows) == 3


class TestVerdictComputation:
    def test_insufficient_data_when_too_few_windows_have_enough_real_trades(self) -> None:
        # The CEO's own real 50 EMA pullback example is, by real honest
        # design, a rare-setup strategy -- at any reasonable window size
        # it never crosses the 10-closed-trade bucket-verdict bar per
        # window, so this must read insufficient_data, never a forced
        # stable/unstable call from noise.
        result = run_walk_forward_validation(compile_strategy_text(name="x", source_text=_CEO_TEXT), symbols=["AAPL", "MSFT"], candles_per_symbol=6000, window_bars=1500)
        assert result.verdict == "insufficient_data"
        assert str(MIN_EVALUATED_WINDOWS_FOR_VERDICT) in result.detail

    def test_a_real_high_frequency_definition_reaches_a_real_stable_or_unstable_verdict(self) -> None:
        definition = _high_frequency_definition()
        result = run_walk_forward_validation(definition, symbols=["AAPL", "MSFT"], candles_per_symbol=6000, window_bars=1500)
        assert result.verdict in ("stable", "unstable")
        total_evaluated = sum(s.evaluated_window_count for s in result.symbols)
        assert total_evaluated >= MIN_EVALUATED_WINDOWS_FOR_VERDICT

    def test_every_window_is_returned_even_when_the_overall_verdict_is_unstable_or_stable(self) -> None:
        # The verdict must never hide any individual real window's own
        # numbers -- every window backtested is always present in the
        # result, whatever the aggregate verdict reads.
        definition = _high_frequency_definition()
        result = run_walk_forward_validation(definition, symbols=["AAPL", "MSFT"], candles_per_symbol=6000, window_bars=1500)
        for symbol_result in result.symbols:
            assert len(symbol_result.windows) == 4


class TestNoLookAheadAcrossWindows:
    def test_backtesting_only_the_first_window_never_sees_or_is_affected_by_later_windows(self) -> None:
        # A real structural check, not just a code-review claim: slicing
        # the SAME real candle series (one single get_candles() fetch --
        # never a second, separately-requested fetch, which
        # app/market_data.py's own live-quote-continuity rescale can
        # legitimately shape differently at a different `limit`) down to
        # just its first `window_bars` real bars and backtesting THAT
        # slice directly must produce the exact same bucket as the full
        # multi-window run's own first window -- proving window 1's own
        # real trades never depended on anything in window 2+.
        definition = _high_frequency_definition()
        window_bars = 1500
        full_result = run_walk_forward_validation(definition, symbols=["AAPL"], candles_per_symbol=6000, window_bars=window_bars)

        full_candles = market_data_provider.get_candles("AAPL", DEFAULT_TIMEFRAME, 6000)
        isolated_trades = backtest_symbol_over_candles(definition, "AAPL", full_candles[:window_bars])
        isolated_bucket = aggregate_bucket("window_1", isolated_trades)

        assert full_result.symbols[0].windows[0].bucket.trade_count == isolated_bucket.trade_count
        assert full_result.symbols[0].windows[0].bucket.expectancy_r == isolated_bucket.expectancy_r
