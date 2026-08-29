"""Covers app/strategy_complexity.py — CEO directive "TradeTown —
11/10 Strategy Factory + Ruthless Backtesting Engine," Section 13
(Simplicity/Complexity Score). Every count here is a real structural
property of a hand-built CompiledStrategyDefinition — never a
judgment call — so these tests prove the count matches the definition's
own real shape, not a fabricated number.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import (
    CompiledStrategyDefinition,
    StrategyCondition,
    StrategyIndicatorRef,
    StrategySequenceStep,
    StrategyStopSpec,
    StrategyTargetSpec,
)
from app.strategy_complexity import COMPLEXITY_MODERATE_MAX, COMPLEXITY_SIMPLE_MAX, compute_strategy_complexity


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _base_definition(**overrides: object) -> CompiledStrategyDefinition:
    fields: dict[str, object] = dict(
        id="def-1",
        name="Test Strategy",
        sourceText="x",
        version=1,
        createdBy="quant",
        createdAt=_now_iso(),
        timeframe="1h",
        sequence=[],
        stop=None,
        target=None,
        ambiguities=[],
        status="compiled",
        detail="x",
    )
    fields.update(overrides)
    return CompiledStrategyDefinition(**fields)  # type: ignore[arg-type]


# The real, exhaustive StrategyIndicatorName vocabulary (app/schemas.py) —
# used to build distinct-indicator fixtures without inventing fake names.
_REAL_INDICATOR_NAMES = [
    "price_close",
    "price_open",
    "price_high",
    "price_low",
    "sma",
    "ema",
    "rsi",
    "macd_line",
    "macd_signal",
    "macd_histogram",
    "stochastic_percent_k",
    "stochastic_percent_d",
    "atr",
    "vwap",
    "multi_horizon_trend_score",
    "liquidity_sweep_signal",
    "structure_break_signal",
    "choch_signal",
    "fvg_signal",
]


def _condition(*, indicator: str = "ema", period: int | None = 20, right_indicator: str | None = None, right_period: int | None = None, right_value: float | None = None) -> StrategyCondition:
    return StrategyCondition(
        id="c1",
        left=StrategyIndicatorRef(indicator=indicator, period=period),  # type: ignore[arg-type]
        operator="gt",
        rightIndicator=StrategyIndicatorRef(indicator=right_indicator, period=right_period) if right_indicator else None,  # type: ignore[arg-type]
        rightValue=right_value,
        detail="x",
    )


class TestComputeStrategyComplexity:
    def test_a_minimal_two_step_strategy_with_no_stop_or_target(self) -> None:
        definition = _base_definition(
            sequence=[
                StrategySequenceStep(id="s1", stepType="trigger", detail="x", condition=_condition()),
                StrategySequenceStep(id="s2", stepType="entry", detail="x"),
            ],
        )
        score = compute_strategy_complexity(definition)
        assert score.step_count == 2
        assert score.condition_count == 1
        assert score.distinct_indicator_count == 1
        # One real tunable parameter: the trigger condition's own period.
        assert score.parameter_count == 1
        assert score.complexity_score == 2 + 1 + 1 + 1
        assert score.band == "simple"

    def test_identical_indicator_type_with_two_different_periods_counts_as_one_distinct_indicator(self) -> None:
        definition = _base_definition(
            sequence=[
                StrategySequenceStep(
                    id="s1",
                    stepType="trigger",
                    detail="x",
                    condition=_condition(indicator="ema", period=20, right_indicator="ema", right_period=50),
                ),
            ],
        )
        score = compute_strategy_complexity(definition)
        assert score.distinct_indicator_count == 1
        # Both real periods (20 and 50) still count as two real tunable parameters.
        assert score.parameter_count == 2

    def test_two_different_indicator_types_count_as_two_distinct_indicators(self) -> None:
        definition = _base_definition(
            sequence=[
                StrategySequenceStep(id="s1", stepType="trigger", detail="x", condition=_condition(indicator="ema", right_indicator="rsi", right_period=14)),
            ],
        )
        score = compute_strategy_complexity(definition)
        assert score.distinct_indicator_count == 2

    def test_an_all_of_trigger_counts_every_real_condition_inside_it(self) -> None:
        definition = _base_definition(
            sequence=[
                StrategySequenceStep(
                    id="s1",
                    stepType="trigger",
                    detail="x",
                    allOf=[_condition(indicator="ema"), _condition(indicator="rsi", period=14), _condition(indicator="atr", period=None)],
                ),
            ],
        )
        score = compute_strategy_complexity(definition)
        assert score.condition_count == 3
        assert score.distinct_indicator_count == 3

    def test_a_requirement_steps_min_consecutive_bars_is_a_real_tunable_parameter(self) -> None:
        definition = _base_definition(
            sequence=[
                StrategySequenceStep(id="s1", stepType="requirement", detail="x", minConsecutiveBars=2, candleDirection="bearish"),
            ],
        )
        score = compute_strategy_complexity(definition)
        assert score.condition_count == 0
        assert score.parameter_count == 1

    def test_a_right_value_literal_threshold_is_a_real_tunable_parameter(self) -> None:
        definition = _base_definition(
            sequence=[
                StrategySequenceStep(id="s1", stepType="trigger", detail="x", condition=_condition(indicator="rsi", period=14, right_value=70.0)),
            ],
        )
        score = compute_strategy_complexity(definition)
        # The condition's own period plus the literal threshold: two real parameters.
        assert score.parameter_count == 2

    def test_a_chandelier_stop_with_both_params_set_counts_both_as_real_parameters(self) -> None:
        definition = _base_definition(stop=StrategyStopSpec(method="chandelier", atrPeriod=14, atrMultiplier=3.0))
        score = compute_strategy_complexity(definition)
        assert score.parameter_count == 2

    def test_a_swing_level_stop_with_no_params_adds_no_parameters(self) -> None:
        definition = _base_definition(stop=StrategyStopSpec(method="swing_level"))
        score = compute_strategy_complexity(definition)
        assert score.parameter_count == 0

    def test_a_target_spec_always_counts_as_one_real_parameter(self) -> None:
        definition = _base_definition(target=StrategyTargetSpec(method="r_multiple", value=2.0))
        score = compute_strategy_complexity(definition)
        assert score.parameter_count == 1

    def test_an_empty_sequence_with_no_stop_or_target_is_the_real_zero_floor(self) -> None:
        definition = _base_definition()
        score = compute_strategy_complexity(definition)
        assert score.step_count == 0
        assert score.condition_count == 0
        assert score.distinct_indicator_count == 0
        assert score.parameter_count == 0
        assert score.complexity_score == 0
        assert score.band == "simple"

    def test_band_boundaries_are_the_real_disclosed_thresholds(self) -> None:
        # Build a strategy whose score lands exactly on the simple/moderate boundary.
        n = min(COMPLEXITY_SIMPLE_MAX, len(_REAL_INDICATOR_NAMES))
        conditions = [_condition(indicator=_REAL_INDICATOR_NAMES[i], period=None) for i in range(n)]
        definition = _base_definition(sequence=[StrategySequenceStep(id="s1", stepType="trigger", detail="x", allOf=conditions)])
        score = compute_strategy_complexity(definition)
        # step_count=1, condition_count=n, distinct_indicator_count=n, parameter_count=0
        assert score.complexity_score == 1 + n + n

    def test_a_large_strategy_reads_the_complex_band(self) -> None:
        conditions = [_condition(indicator=_REAL_INDICATOR_NAMES[i % len(_REAL_INDICATOR_NAMES)], period=i + 1) for i in range(COMPLEXITY_MODERATE_MAX + 5)]
        definition = _base_definition(sequence=[StrategySequenceStep(id="s1", stepType="trigger", detail="x", allOf=conditions)])
        score = compute_strategy_complexity(definition)
        assert score.band == "complex"

    def test_definition_id_and_version_are_carried_through_verbatim(self) -> None:
        definition = _base_definition(id="my-def", version=7)
        score = compute_strategy_complexity(definition)
        assert score.definition_id == "my-def"
        assert score.definition_version == 7
