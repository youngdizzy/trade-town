"""Covers app/strategy_compiler.py — CEO directive "Professional Quant
Trading Firm — Quant Intelligence + Market Analysis Completion Phase,"
Phase F. The compiler must never silently invent a threshold: every
test here checks either a real, correct structured translation of known
vocabulary, or a real, honest "ambiguous"/"invalid" refusal.
"""
from __future__ import annotations

from app.strategy_compiler import compile_strategy_text

_CEO_EXAMPLE_TEXT = (
    "Buy when price closes above the 50 EMA, then wait for at least two bearish candles, "
    "then enter when price closes above the previous swing high. Place the stop at the "
    "Chandelier Stop and target 2R."
)


class TestCompilesTheCeoWorkedExample:
    def test_status_compiled(self) -> None:
        result = compile_strategy_text(name="50 EMA Pullback", source_text=_CEO_EXAMPLE_TEXT)
        assert result.status == "compiled"
        assert result.ambiguities == []

    def test_real_trigger_step(self) -> None:
        result = compile_strategy_text(name="50 EMA Pullback", source_text=_CEO_EXAMPLE_TEXT)
        trigger = next(s for s in result.sequence if s.step_type == "trigger")
        assert trigger.condition is not None
        assert trigger.condition.left.indicator == "price_close"
        assert trigger.condition.operator == "crosses_above"
        assert trigger.condition.right_indicator is not None
        assert trigger.condition.right_indicator.indicator == "ema"
        assert trigger.condition.right_indicator.period == 50

    def test_real_requirement_step(self) -> None:
        result = compile_strategy_text(name="50 EMA Pullback", source_text=_CEO_EXAMPLE_TEXT)
        requirement = next(s for s in result.sequence if s.step_type == "requirement")
        assert requirement.min_consecutive_bars == 2
        assert requirement.candle_direction == "bearish"

    def test_real_entry_step(self) -> None:
        result = compile_strategy_text(name="50 EMA Pullback", source_text=_CEO_EXAMPLE_TEXT)
        assert any(s.step_type == "entry" for s in result.sequence)

    def test_real_chandelier_stop_with_standard_defaults(self) -> None:
        result = compile_strategy_text(name="50 EMA Pullback", source_text=_CEO_EXAMPLE_TEXT)
        assert result.stop is not None
        assert result.stop.method == "chandelier"
        assert result.stop.atr_period == 22
        assert result.stop.atr_multiplier == 3.0

    def test_real_r_multiple_target(self) -> None:
        result = compile_strategy_text(name="50 EMA Pullback", source_text=_CEO_EXAMPLE_TEXT)
        assert result.target is not None
        assert result.target.method == "r_multiple"
        assert result.target.value == 2.0

    def test_deterministic_same_text_same_output(self) -> None:
        a = compile_strategy_text(name="A", source_text=_CEO_EXAMPLE_TEXT)
        b = compile_strategy_text(name="A", source_text=_CEO_EXAMPLE_TEXT)
        assert a.sequence == b.sequence
        assert a.stop == b.stop
        assert a.target == b.target
        assert a.status == b.status


class TestShortMirror:
    def test_short_trigger_and_entry(self) -> None:
        text = (
            "Sell when price closes below the 50 EMA, then wait for at least two bullish candles, "
            "then enter when price closes below the previous swing low. Place the stop at the "
            "Chandelier Stop and target 2R."
        )
        result = compile_strategy_text(name="Short EMA Pullback", source_text=text)
        assert result.status == "compiled"
        trigger = next(s for s in result.sequence if s.step_type == "trigger")
        assert trigger.condition is not None
        assert trigger.condition.operator == "crosses_below"
        requirement = next(s for s in result.sequence if s.step_type == "requirement")
        assert requirement.candle_direction == "bullish"


class TestAmbiguousPhrasesAreNeverSilentlyConverted:
    def test_strong_breakout_is_flagged(self) -> None:
        result = compile_strategy_text(name="Vague", source_text="Buy on a strong breakout above the 50 EMA, target 2R.")
        assert result.status == "ambiguous"
        assert any("strong breakout" in a.phrase for a in result.ambiguities)

    def test_significant_volume_is_flagged(self) -> None:
        result = compile_strategy_text(name="Vague2", source_text="Buy above the 50 EMA with significant volume, target 2R.")
        assert result.status == "ambiguous"
        assert any("significant volume" in a.phrase for a in result.ambiguities)

    def test_ambiguous_strategies_are_never_marked_compiled(self) -> None:
        result = compile_strategy_text(name="Vague3", source_text="Buy near support with a clean pullback, target 2R.")
        assert result.status != "compiled"


class TestUnrecognizedTextIsNeverGuessed:
    def test_moon_phase_strategy_is_invalid_not_fabricated(self) -> None:
        result = compile_strategy_text(name="Moon", source_text="Buy gold when the moon is full.")
        assert result.status == "invalid"
        assert result.stop is None
        assert result.target is None
        assert result.sequence == []

    def test_empty_text_is_invalid(self) -> None:
        result = compile_strategy_text(name="Empty", source_text="")
        assert result.status == "invalid"


class TestVersioning:
    def test_defaults_to_version_one(self) -> None:
        result = compile_strategy_text(name="V", source_text=_CEO_EXAMPLE_TEXT)
        assert result.version == 1

    def test_previous_version_increments(self) -> None:
        result = compile_strategy_text(name="V", source_text=_CEO_EXAMPLE_TEXT, previous_version=3)
        assert result.version == 4


class TestSourceTextIsPreservedExactly:
    def test_source_text_round_trips_verbatim(self) -> None:
        result = compile_strategy_text(name="Audit", source_text=_CEO_EXAMPLE_TEXT)
        assert result.source_text == _CEO_EXAMPLE_TEXT


class TestRsiStochasticMacdTriggers:
    """CEO directive "...Quant Intelligence + Market Analysis Completion
    Phase (Next Research + Validation Pass)" -- the real, disclosed
    MOMENTUM-reading convention for RSI/Stochastic thresholds (see this
    module's own docstring): "above N" always compiles to a real long-
    biased trigger, "below N" to short. Never the mean-reversion
    reading."""

    def test_rsi_above_threshold_compiles_to_a_real_long_trigger(self) -> None:
        text = "Buy when RSI is above 70, then enter when price closes above the previous swing high. Place a 2% stop and 4% target."
        result = compile_strategy_text(name="X", source_text=text)
        assert result.status == "compiled"
        trigger = next(s for s in result.sequence if s.step_type == "trigger")
        assert trigger.condition is not None
        assert trigger.condition.left.indicator == "rsi"
        assert trigger.condition.left.period == 14
        assert trigger.condition.operator == "gt"
        assert trigger.condition.right_value == 70.0

    def test_rsi_below_threshold_with_an_explicit_period_compiles_correctly(self) -> None:
        text = "Sell when the 21 RSI is below 25, then enter when price closes below the previous swing low. Place a 2% stop and 4% target."
        result = compile_strategy_text(name="X", source_text=text)
        assert result.status == "compiled"
        trigger = next(s for s in result.sequence if s.step_type == "trigger")
        assert trigger.condition is not None
        assert trigger.condition.left.period == 21
        assert trigger.condition.operator == "lt"
        assert trigger.condition.right_value == 25.0

    def test_a_mean_reversion_phrased_rsi_strategy_is_ambiguous_not_silently_miscompiled(self) -> None:
        # "RSI below 30, buy" is the mean-reversion reading -- the
        # trigger's own real short-biased direction (below N -> short)
        # genuinely contradicts the entry's own stated long direction
        # (closes above the swing high). This compiler refuses rather
        # than guessing which reading was intended.
        text = "Buy when RSI is below 30, then enter when price closes above the previous swing high. Place a 2% stop and 4% target."
        result = compile_strategy_text(name="X", source_text=text)
        assert result.status == "ambiguous"
        assert any("contradicts" in a.reason for a in result.ambiguities)

    def test_stochastic_threshold_compiles_with_the_stated_period(self) -> None:
        text = "Buy when the 14 Stochastic is above 80, then enter when price closes above the previous swing high. Place a 2% stop and 4% target."
        result = compile_strategy_text(name="X", source_text=text)
        assert result.status == "compiled"
        trigger = next(s for s in result.sequence if s.step_type == "trigger")
        assert trigger.condition is not None
        assert trigger.condition.left.indicator == "stochastic_percent_k"
        assert trigger.condition.left.period == 14
        assert trigger.condition.operator == "gt"

    def test_stochastic_without_a_stated_period_defaults_to_fourteen(self) -> None:
        text = "Sell when Stochastic is below 20, then enter when price closes below the previous swing low. Place a 2% stop and 4% target."
        result = compile_strategy_text(name="X", source_text=text)
        assert result.status == "compiled"
        trigger = next(s for s in result.sequence if s.step_type == "trigger")
        assert trigger.condition is not None
        assert trigger.condition.left.period == 14

    def test_macd_cross_above_signal_compiles_to_a_real_long_crossing_trigger(self) -> None:
        text = "Buy when MACD crosses above the signal line, then enter when price closes above the previous swing high. Place a 2% stop and 4% target."
        result = compile_strategy_text(name="X", source_text=text)
        assert result.status == "compiled"
        trigger = next(s for s in result.sequence if s.step_type == "trigger")
        assert trigger.condition is not None
        assert trigger.condition.left.indicator == "macd_line"
        assert trigger.condition.operator == "crosses_above"
        assert trigger.condition.right_indicator is not None
        assert trigger.condition.right_indicator.indicator == "macd_signal"

    def test_macd_line_crosses_below_signal_compiles_to_a_real_short_crossing_trigger(self) -> None:
        text = "Sell when MACD line crosses below signal, then enter when price closes below the previous swing low. Place a 2% stop and 4% target."
        result = compile_strategy_text(name="X", source_text=text)
        assert result.status == "compiled"
        trigger = next(s for s in result.sequence if s.step_type == "trigger")
        assert trigger.condition is not None
        assert trigger.condition.operator == "crosses_below"

    def test_at_most_one_trigger_is_recognized_ema_takes_priority_over_rsi(self) -> None:
        # A real text that could match BOTH the EMA pattern and the RSI
        # pattern -- the EMA/SMA pattern's own real priority (checked
        # first) wins; this compiler never tries to combine two trigger
        # types into one sequence.
        text = "Buy when price closes above the 50 EMA and RSI is above 70, then enter when price closes above the previous swing high. Place a 2% stop and 4% target."
        result = compile_strategy_text(name="X", source_text=text)
        triggers = [s for s in result.sequence if s.step_type == "trigger"]
        assert len(triggers) == 1
        assert triggers[0].condition is not None
        assert triggers[0].condition.left.indicator == "price_close"
        assert triggers[0].condition.right_indicator is not None
        assert triggers[0].condition.right_indicator.indicator == "ema"


class TestLiquiditySweepTrigger:
    """CEO directive "AHL-Inspired Systematic Trend & Momentum Research
    Engine," Phase 8 — the real liquidity_sweep_signal indicator's own
    compiler pattern."""

    def test_bullish_sweep_compiles_to_a_real_long_crossing_trigger(self) -> None:
        text = "Buy when a bullish liquidity sweep occurs, then enter when price closes above the previous swing high. Place a 2% stop and 4% target."
        result = compile_strategy_text(name="X", source_text=text)
        assert result.status == "compiled"
        trigger = next(s for s in result.sequence if s.step_type == "trigger")
        assert trigger.condition is not None
        assert trigger.condition.left.indicator == "liquidity_sweep_signal"
        assert trigger.condition.operator == "crosses_above"
        assert trigger.condition.right_value == 0.0

    def test_bearish_sweep_compiles_to_a_real_short_crossing_trigger(self) -> None:
        text = "Sell when a bearish liquidity sweep occurs, then enter when price closes below the previous swing low. Place a 2% stop and 4% target."
        result = compile_strategy_text(name="X", source_text=text)
        assert result.status == "compiled"
        trigger = next(s for s in result.sequence if s.step_type == "trigger")
        assert trigger.condition is not None
        assert trigger.condition.left.indicator == "liquidity_sweep_signal"
        assert trigger.condition.operator == "crosses_below"
        assert trigger.condition.right_value == 0.0


class TestStructureBreakTrigger:
    """CEO directive "AHL-Inspired Systematic Trend & Momentum Research
    Engine," Phase 10 — the real structure_break_signal indicator's own
    compiler pattern."""

    def test_bullish_break_compiles_to_a_real_long_crossing_trigger(self) -> None:
        text = "Buy when a bullish break of structure occurs, then enter when price closes above the previous swing high. Place a 2% stop and 4% target."
        result = compile_strategy_text(name="X", source_text=text)
        assert result.status == "compiled"
        trigger = next(s for s in result.sequence if s.step_type == "trigger")
        assert trigger.condition is not None
        assert trigger.condition.left.indicator == "structure_break_signal"
        assert trigger.condition.operator == "crosses_above"
        assert trigger.condition.right_value == 0.0

    def test_bearish_break_compiles_to_a_real_short_crossing_trigger(self) -> None:
        text = "Sell when a bearish break of structure occurs, then enter when price closes below the previous swing low. Place a 2% stop and 4% target."
        result = compile_strategy_text(name="X", source_text=text)
        assert result.status == "compiled"
        trigger = next(s for s in result.sequence if s.step_type == "trigger")
        assert trigger.condition is not None
        assert trigger.condition.left.indicator == "structure_break_signal"
        assert trigger.condition.operator == "crosses_below"
        assert trigger.condition.right_value == 0.0


class TestChangeOfCharacterTrigger:
    """CEO directive "AHL-Inspired Systematic Trend & Momentum Research
    Engine," Phase 10 — the real choch_signal indicator's own compiler
    pattern, closing a prior pass's explicit hard-blocker (see
    app/structure_break_research.py's own historical docstring note on
    why CHoCH was originally refused)."""

    def test_bullish_choch_compiles_to_a_real_long_crossing_trigger(self) -> None:
        text = "Buy when a bullish change of character occurs, then enter when price closes above the previous swing high. Place a 2% stop and 4% target."
        result = compile_strategy_text(name="X", source_text=text)
        assert result.status == "compiled"
        trigger = next(s for s in result.sequence if s.step_type == "trigger")
        assert trigger.condition is not None
        assert trigger.condition.left.indicator == "choch_signal"
        assert trigger.condition.operator == "crosses_above"
        assert trigger.condition.right_value == 0.0

    def test_bearish_choch_compiles_to_a_real_short_crossing_trigger(self) -> None:
        text = "Sell when a bearish change of character occurs, then enter when price closes below the previous swing low. Place a 2% stop and 4% target."
        result = compile_strategy_text(name="X", source_text=text)
        assert result.status == "compiled"
        trigger = next(s for s in result.sequence if s.step_type == "trigger")
        assert trigger.condition is not None
        assert trigger.condition.left.indicator == "choch_signal"
        assert trigger.condition.operator == "crosses_below"
        assert trigger.condition.right_value == 0.0


class TestFvgTrigger:
    """CEO directive "AHL-Inspired Systematic Trend & Momentum Research
    Engine," Phase 10 — the real fvg_signal indicator's own compiler
    pattern."""

    def test_bullish_fvg_compiles_to_a_real_long_crossing_trigger(self) -> None:
        text = "Buy when a bullish fair value gap forms, then enter when price closes above the previous swing high. Place a 2% stop and 4% target."
        result = compile_strategy_text(name="X", source_text=text)
        assert result.status == "compiled"
        trigger = next(s for s in result.sequence if s.step_type == "trigger")
        assert trigger.condition is not None
        assert trigger.condition.left.indicator == "fvg_signal"
        assert trigger.condition.operator == "crosses_above"
        assert trigger.condition.right_value == 0.0

    def test_bearish_fvg_compiles_to_a_real_short_crossing_trigger(self) -> None:
        text = "Sell when a bearish fair value gap forms, then enter when price closes below the previous swing low. Place a 2% stop and 4% target."
        result = compile_strategy_text(name="X", source_text=text)
        assert result.status == "compiled"
        trigger = next(s for s in result.sequence if s.step_type == "trigger")
        assert trigger.condition is not None
        assert trigger.condition.left.indicator == "fvg_signal"
        assert trigger.condition.operator == "crosses_below"
        assert trigger.condition.right_value == 0.0


class TestFibonacci618Trigger:
    """CEO directive "AHL-Inspired Systematic Trend & Momentum Research
    Engine," Phase 10 — the real fibonacci_618_level indicator's own
    compiler pattern. Unlike every other new trigger this directive
    added, this one compares two real indicators (price_close vs the
    real Fibonacci level), reusing the exact same crossing mechanism the
    MACD line/signal-line pattern already established."""

    def test_price_above_fib_level_compiles_to_a_real_long_crossing_trigger(self) -> None:
        text = "Buy when price closes above the 61.8% Fibonacci retracement level, then enter when price closes above the previous swing high. Place a 2% stop and 4% target."
        result = compile_strategy_text(name="X", source_text=text)
        assert result.status == "compiled"
        trigger = next(s for s in result.sequence if s.step_type == "trigger")
        assert trigger.condition is not None
        assert trigger.condition.left.indicator == "price_close"
        assert trigger.condition.operator == "crosses_above"
        assert trigger.condition.right_indicator is not None
        assert trigger.condition.right_indicator.indicator == "fibonacci_618_level"

    def test_price_below_fib_level_compiles_to_a_real_short_crossing_trigger(self) -> None:
        text = "Sell when price closes below the 61.8% Fibonacci retracement level, then enter when price closes below the previous swing low. Place a 2% stop and 4% target."
        result = compile_strategy_text(name="X", source_text=text)
        assert result.status == "compiled"
        trigger = next(s for s in result.sequence if s.step_type == "trigger")
        assert trigger.condition is not None
        assert trigger.condition.left.indicator == "price_close"
        assert trigger.condition.operator == "crosses_below"
        assert trigger.condition.right_indicator is not None
        assert trigger.condition.right_indicator.indicator == "fibonacci_618_level"


class TestSweepFvgComboTrigger:
    """CEO directive "AHL-Inspired Systematic Trend & Momentum Research
    Engine," Phase 9 — the sweep+FVG combo hypothesis, closing a prior
    audit pass's finding that "combining sweep+displacement+FVG as one
    simultaneous multi-condition trigger... needs a moderate schema
    extension." No real "displacement" leg is included — no such
    detector exists anywhere in this codebase (a real, disclosed scope
    cut, not a fabricated third condition)."""

    def test_bullish_combo_compiles_to_a_real_two_condition_all_of_trigger(self) -> None:
        text = "Buy when a bullish liquidity sweep and a bullish fair value gap both occur, then enter when price closes above the previous swing high. Place a 2% stop and 4% target."
        result = compile_strategy_text(name="X", source_text=text)
        assert result.status == "compiled"
        trigger = next(s for s in result.sequence if s.step_type == "trigger")
        assert trigger.condition is None
        assert trigger.all_of is not None
        assert len(trigger.all_of) == 2
        indicators = {c.left.indicator for c in trigger.all_of}
        assert indicators == {"liquidity_sweep_signal", "fvg_signal"}
        assert all(c.operator == "crosses_above" for c in trigger.all_of)
        assert all(c.right_value == 0.0 for c in trigger.all_of)

    def test_bearish_combo_compiles_to_a_real_two_condition_all_of_trigger(self) -> None:
        text = "Sell when a bearish liquidity sweep and a bearish fair value gap both occur, then enter when price closes below the previous swing low. Place a 2% stop and 4% target."
        result = compile_strategy_text(name="X", source_text=text)
        assert result.status == "compiled"
        trigger = next(s for s in result.sequence if s.step_type == "trigger")
        assert trigger.condition is None
        assert trigger.all_of is not None
        assert len(trigger.all_of) == 2
        assert all(c.operator == "crosses_below" for c in trigger.all_of)

    def test_mismatched_direction_does_not_compile_as_a_combo(self) -> None:
        # A real, self-contradictory request ("bullish sweep and bearish
        # FVG") — the \1 backreference deliberately does not match this,
        # so it falls through to "no recognizable trigger" rather than
        # silently picking one side.
        text = "Buy when a bullish liquidity sweep and a bearish fair value gap both occur, then enter when price closes above the previous swing high. Place a 2% stop and 4% target."
        result = compile_strategy_text(name="X", source_text=text)
        assert result.status != "compiled"
