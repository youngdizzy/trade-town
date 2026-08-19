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
