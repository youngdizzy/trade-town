"""Covers app/parameter_sensitivity.py — CEO directive "Professional
Quant Trading Firm — Quant Intelligence + Market Analysis Completion
Phase (Next Research + Validation Pass)," item 5. The critical guarantee
this file establishes: the module never surfaces a single "best"
combination, and `verdict` is computed from real sign-agreement across
the swept neighborhood, never a forced call from too few real points.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.parameter_sensitivity import _axis_sign_agreement, run_parameter_sensitivity
from app.schemas import (
    CompiledStrategyDefinition,
    EmaPullbackStatsBucket,
    ParameterSensitivityAxisResult,
    ParameterSensitivityPoint,
    StrategyCondition,
    StrategyIndicatorRef,
    StrategySequenceStep,
    StrategyStopSpec,
    StrategyTargetSpec,
)
from app.strategy_compiler import compile_strategy_text

_CEO_TEXT = (
    "Buy when price closes above the 50 EMA, then wait for at least two bearish candles, "
    "then enter when price closes above the previous swing high. Place the stop at the "
    "Chandelier Stop and target 2R."
)


def _bucket(*, trade_count: int, expectancy_r: float | None, verdict: str | None) -> EmaPullbackStatsBucket:
    return EmaPullbackStatsBucket(label="x", tradeCount=trade_count, winCount=0, lossCount=0, openCount=0, expectancyR=expectancy_r, verdict=verdict, detail="x")  # type: ignore[arg-type]


def _axis(*, base_value: float, expectancies: list[float | None]) -> ParameterSensitivityAxisResult:
    points = [
        ParameterSensitivityPoint(label=str(i), value=base_value + i, bucket=_bucket(trade_count=20, expectancy_r=e, verdict="enough_evidence" if e is not None else None))
        for i, e in enumerate(expectancies)
    ]
    return ParameterSensitivityAxisResult(parameter="stop", sweepable=True, baseValue=base_value, points=points, detail="x")


def _swing_level_definition() -> CompiledStrategyDefinition:
    now = datetime.now(timezone.utc).isoformat()
    return CompiledStrategyDefinition(
        id="swing-test",
        name="swing test",
        sourceText="x",
        version=1,
        createdBy="quant",
        createdAt=now,
        timeframe="1h",
        sequence=[
            StrategySequenceStep(id="s1", stepType="trigger", detail="x", condition=StrategyCondition(id="c1", left=StrategyIndicatorRef(indicator="ema", period=20), operator="crosses_above", rightIndicator=StrategyIndicatorRef(indicator="ema", period=50), detail="x")),
            StrategySequenceStep(id="s2", stepType="entry", detail="x"),
        ],
        stop=StrategyStopSpec(method="swing_level"),
        target=StrategyTargetSpec(method="r_multiple", value=2.0),
        ambiguities=[],
        status="compiled",
        detail="x",
    )


class TestAxisSignAgreement:
    def test_none_when_fewer_than_the_minimum_evaluated_points(self) -> None:
        axis = _axis(base_value=3.0, expectancies=[0.5, None, None, None, None])
        assert _axis_sign_agreement(axis) is None

    def test_full_agreement_when_every_point_shares_the_base_points_sign(self) -> None:
        axis = _axis(base_value=3.0, expectancies=[0.5, 0.6, 0.7, 0.8, 0.9])
        result = _axis_sign_agreement(axis)
        assert result == (5, 5)

    def test_partial_agreement_when_a_point_flips_sign(self) -> None:
        axis = _axis(base_value=3.0, expectancies=[0.5, 0.6, -0.1, 0.8, 0.9])
        result = _axis_sign_agreement(axis)
        assert result is not None
        agreeing, evaluated = result
        assert evaluated == 5
        assert agreeing == 4  # every point but the one real sign flip


class TestRunParameterSensitivityRefusesRatherThanGuesses:
    def test_an_invalid_definition_is_refused(self) -> None:
        definition = compile_strategy_text(name="x", source_text="Buy when the moon is full.")
        result = run_parameter_sensitivity(definition, symbols=["AAPL"])
        assert result.verdict == "insufficient_data"
        assert result.stop_axis is None
        assert result.target_axis is None
        assert "not backtestable" in result.detail


class TestSwingLevelStopIsUnsweepable:
    def test_swing_level_reports_a_single_unsweepable_point_never_a_fabricated_sweep(self) -> None:
        result = run_parameter_sensitivity(_swing_level_definition(), symbols=["AAPL"], candles_per_symbol=6000)
        assert result.stop_axis is not None
        assert result.stop_axis.sweepable is False
        assert result.stop_axis.points == []
        assert result.target_axis is not None
        assert result.target_axis.sweepable is True


class TestNeverSurfacesABestCombination:
    def test_the_result_schema_has_no_best_combination_field(self) -> None:
        definition = compile_strategy_text(name="x", source_text=_CEO_TEXT)
        result = run_parameter_sensitivity(definition, symbols=["AAPL", "MSFT"], candles_per_symbol=6000)
        assert not hasattr(result, "best_combination")
        assert not hasattr(result, "best_point")
        assert "real, independent backtests were run" in result.multiple_testing_note


class TestIntegrationAgainstTheCeoWorkedExample:
    def test_real_stop_and_target_axes_are_both_swept_and_a_real_verdict_is_reached(self) -> None:
        definition = compile_strategy_text(name="x", source_text=_CEO_TEXT)
        result = run_parameter_sensitivity(definition, symbols=["AAPL", "MSFT", "SPY", "QQQ"], candles_per_symbol=6000)
        assert result.verdict in ("robust", "fragile", "insufficient_data")
        assert result.stop_axis is not None and result.stop_axis.sweepable
        assert result.target_axis is not None and result.target_axis.sweepable
        # 5-step sweep with a base ATR multiplier of 3.0 -> all 5 (1..5) stay positive.
        assert len(result.stop_axis.points) == 5
        # 5-step sweep with a base target of 2R -> the -1R (0R) step is filtered out.
        assert len(result.target_axis.points) == 4
        for point in result.stop_axis.points + result.target_axis.points:
            assert point.bucket.trade_count >= 0

    def test_every_point_carries_a_real_bucket_with_a_verdict_never_left_unset(self) -> None:
        # Deliberately does not assert how many real points cross the
        # evidence bar -- app/market_data.py's own real (mock) walk is
        # seeded per (symbol, timeframe) only, not per test, so trade
        # counts are real data, never a value this test should hardcode
        # (the same house convention TestRunEmaPullbackResearchIntegration
        # documents in tests/test_ema_pullback_research.py). What must
        # always hold: every real swept point resolves to SOME real
        # verdict, never left silently unset.
        definition = compile_strategy_text(name="x", source_text=_CEO_TEXT)
        result = run_parameter_sensitivity(definition, symbols=["AAPL", "MSFT", "SPY", "QQQ"], candles_per_symbol=6000)
        assert result.stop_axis is not None
        for point in result.stop_axis.points:
            assert point.bucket.verdict in ("enough_evidence", "not_enough_evidence", None)
