"""app/parameter_sensitivity.py — CEO directive "Professional Quant
Trading Firm — Quant Intelligence + Market Analysis Completion Phase
(Next Research + Validation Pass)," item 5: real parameter-sensitivity /
robustness testing over a compiled strategy's own stop and target
parameters.

RESEARCH FIRST: grep confirmed zero existing "parameter_sensitivity" /
"parameter sensitivity" hits anywhere in this codebase before this
module — a genuinely missing capability, not a duplicate.

ONE AUTHORITATIVE IMPLEMENTATION: every point in the sweep is a real,
full-series backtest via app/strategy_engine.py's own
`run_compiled_strategy_backtest()` — the exact same pipeline the
flagship compile-and-backtest endpoint already uses, just handed a
definition with one stop or target field nudged to a real neighboring
value. Never a second backtest engine.

METHODOLOGY, DISCLOSED: ONE-PARAMETER-AT-A-TIME sensitivity, not a full
grid search. Each of the definition's own real stop and target values is
swept independently (holding the other fixed at the definition's own
stated value) across `SWEEP_STEPS` — five real points: -2, -1, 0
(the base), +1, +2 real units in that parameter's own native scale (ATR
multiplier / percent points / R-multiple). A full cross-product grid
(stop x target) would multiply the real trial count and correspondingly
worsen the exact multiple-testing risk this same directive's item 10
warns about, for real information this one-at-a-time sweep already
answers just as honestly: does the base parameter sit inside a real
robust neighborhood, or right on the edge of one.

A `swing_level` stop has no free numeric parameter (it is pinned to the
real pullback swing price, not a chosen constant) — reported as
`sweepable=False` with a single, unsweepable point, never a fabricated
sweep.

NEVER RECOMMENDS A "BEST" COMBINATION. `ParameterSensitivityResult` has
no such field by design. `verdict` (`robust`/`fragile`/
`insufficient_data`) describes whether the real sign of expectancy
mostly agrees across the swept neighborhood, never which single point
performed best — the exact anti-pattern item 10 names ("test hundreds of
strategies/parameters and then celebrate the best result"). A real,
disclosed `multiple_testing_note` on every result states the real number
of trials run and cautions against reading the peak of the grid as
validated.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import CompiledStrategyDefinition, ParameterSensitivityAxisResult, ParameterSensitivityPoint, ParameterSensitivityResult
from app.strategy_engine import DEFAULT_CANDLES_PER_SYMBOL, DEFAULT_TIMEFRAME, _unsupported_indicators, run_compiled_strategy_backtest

SWEEP_STEPS: tuple[float, ...] = (-2.0, -1.0, 0.0, 1.0, 2.0)
MIN_EVALUATED_POINTS_FOR_VERDICT = 3
ROBUST_SIGN_AGREEMENT_FRACTION = 0.6

DATA_HONESTY_NOTE = (
    "Every real point below is a full, independent, real (mock) candle-history backtest — never an interpolation "
    "or estimate between points."
)


def _stop_points(definition: CompiledStrategyDefinition, *, timeframe: str, candles_per_symbol: int, symbols: list[str] | None) -> ParameterSensitivityAxisResult:
    stop = definition.stop
    if stop is None or stop.method == "swing_level" or (stop.method == "chandelier" and stop.atr_multiplier is None) or (stop.method == "fixed_percent" and stop.percent is None):
        return ParameterSensitivityAxisResult(parameter="stop", sweepable=False, points=[], detail="This definition's stop has no free numeric parameter to sweep (swing_level is pinned to the real pullback swing price, not a chosen constant).")

    base = stop.atr_multiplier if stop.method == "chandelier" else stop.percent
    assert base is not None
    points: list[ParameterSensitivityPoint] = []
    for step in SWEEP_STEPS:
        value = round(base + step, 3)
        if value <= 0:
            continue
        if stop.method == "chandelier":
            swept_stop = stop.model_copy(update={"atr_multiplier": value})
            label = f"ATR x {value:g}"
        else:
            swept_stop = stop.model_copy(update={"percent": value})
            label = f"{value:g}%"
        swept_definition = definition.model_copy(update={"stop": swept_stop})
        result = run_compiled_strategy_backtest(swept_definition, symbols=symbols, timeframe=timeframe, candles_per_symbol=candles_per_symbol)
        points.append(ParameterSensitivityPoint(label=label, value=value, bucket=result.overall))
    detail = f"{len(points)} real point(s) swept around the definition's own stated stop value ({base:g})."
    return ParameterSensitivityAxisResult(parameter="stop", sweepable=True, baseValue=base, points=points, detail=detail)


def _target_points(definition: CompiledStrategyDefinition, *, timeframe: str, candles_per_symbol: int, symbols: list[str] | None) -> ParameterSensitivityAxisResult:
    target = definition.target
    if target is None:
        return ParameterSensitivityAxisResult(parameter="target", sweepable=False, points=[], detail="This definition has no target to sweep.")

    base = target.value
    points: list[ParameterSensitivityPoint] = []
    for step in SWEEP_STEPS:
        value = round(base + step, 3)
        if value <= 0:
            continue
        swept_target = target.model_copy(update={"value": value})
        swept_definition = definition.model_copy(update={"target": swept_target})
        result = run_compiled_strategy_backtest(swept_definition, symbols=symbols, timeframe=timeframe, candles_per_symbol=candles_per_symbol)
        label = f"{value:g}R" if target.method == "r_multiple" else f"{value:g}%"
        points.append(ParameterSensitivityPoint(label=label, value=value, bucket=result.overall))
    detail = f"{len(points)} real point(s) swept around the definition's own stated target value ({base:g})."
    return ParameterSensitivityAxisResult(parameter="target", sweepable=True, baseValue=base, points=points, detail=detail)


def _axis_sign_agreement(axis: ParameterSensitivityAxisResult) -> tuple[int, int] | None:
    """Returns `(agreeing, evaluated)` real point counts, or `None` if
    this axis has fewer than `MIN_EVALUATED_POINTS_FOR_VERDICT` real
    points with enough closed trades for their own bucket-level verdict.
    A real "base point" reference is whichever evaluated point sits
    closest to the axis's own real base value (the base value itself,
    when it was itself evaluated)."""
    evaluated = [p for p in axis.points if p.bucket.verdict == "enough_evidence" and p.bucket.expectancy_r is not None]
    if len(evaluated) < MIN_EVALUATED_POINTS_FOR_VERDICT:
        return None
    reference = min(evaluated, key=lambda p: abs(p.value - (axis.base_value or p.value)))
    assert reference.bucket.expectancy_r is not None
    reference_sign = reference.bucket.expectancy_r > 0
    agreeing = sum(1 for p in evaluated if p.bucket.expectancy_r is not None and (p.bucket.expectancy_r > 0) == reference_sign)
    return agreeing, len(evaluated)


def run_parameter_sensitivity(
    definition: CompiledStrategyDefinition,
    *,
    symbols: list[str] | None = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    candles_per_symbol: int = DEFAULT_CANDLES_PER_SYMBOL,
) -> ParameterSensitivityResult:
    """The one real entry point. Refuses exactly when
    `run_compiled_strategy_backtest()` would — an unresolved definition
    or an unsupported indicator — never a silently-guessed sweep."""
    now_iso = datetime.now(timezone.utc).isoformat()
    result_id = f"param-sensitivity-{definition.id}"

    def _refusal(reason: str) -> ParameterSensitivityResult:
        return ParameterSensitivityResult(
            id=result_id,
            definitionId=definition.id,
            definitionVersion=definition.version,
            stopAxis=None,
            targetAxis=None,
            verdict="insufficient_data",
            detail=reason,
            multipleTestingNote="No real trials were run.",
            dataHonestyNote=DATA_HONESTY_NOTE,
            generatedAt=now_iso,
        )

    if definition.status != "compiled":
        return _refusal(f"This definition is not backtestable: status={definition.status!r}. {definition.detail}")
    unsupported = _unsupported_indicators(definition)
    if unsupported:
        return _refusal(f"This engine's current v1 scope cannot resolve indicator(s) {sorted(unsupported)} — a real, disclosed coverage gap, not a fabricated result.")

    stop_axis = _stop_points(definition, timeframe=timeframe, candles_per_symbol=candles_per_symbol, symbols=symbols)
    target_axis = _target_points(definition, timeframe=timeframe, candles_per_symbol=candles_per_symbol, symbols=symbols)
    total_trials = len(stop_axis.points) + len(target_axis.points)

    stop_agreement = _axis_sign_agreement(stop_axis)
    target_agreement = _axis_sign_agreement(target_axis)
    axis_reads = [a for a in (stop_agreement, target_agreement) if a is not None]

    if not axis_reads:
        verdict = "insufficient_data"
        detail = (
            f"Neither axis had at least {MIN_EVALUATED_POINTS_FOR_VERDICT} real swept point(s) with enough closed trades for a "
            "bucket-level verdict — cannot yet read a real robust vs. fragile region."
        )
    else:
        fractions = [agreeing / evaluated for agreeing, evaluated in axis_reads]
        if all(f >= ROBUST_SIGN_AGREEMENT_FRACTION for f in fractions):
            verdict = "robust"
            detail = (
                f"Every real evaluated axis keeps the same expectancy sign across at least {ROBUST_SIGN_AGREEMENT_FRACTION * 100:g}% of its "
                "own swept neighborhood — this edge does not depend on one narrowly-tuned parameter value."
            )
        else:
            verdict = "fragile"
            worst = min(fractions)
            detail = (
                f"At least one real axis only keeps the same expectancy sign across {worst * 100:.0f}% of its own swept neighborhood — "
                f"below the {ROBUST_SIGN_AGREEMENT_FRACTION * 100:g}% bar. This edge may depend on a narrowly-tuned parameter value rather "
                "than a genuinely robust region."
            )

    multiple_testing_note = (
        f"{total_trials} real, independent backtests were run across both axes to build this sweep. Sweeping more combinations always "
        "raises the real chance some single point looks good by chance alone — read the grid's own overall trend (the verdict above), "
        "never any one point's own best result, as validated evidence."
    )

    return ParameterSensitivityResult(
        id=result_id,
        definitionId=definition.id,
        definitionVersion=definition.version,
        stopAxis=stop_axis,
        targetAxis=target_axis,
        verdict=verdict,  # type: ignore[arg-type]
        detail=detail,
        multipleTestingNote=multiple_testing_note,
        dataHonestyNote=DATA_HONESTY_NOTE,
        generatedAt=now_iso,
    )
