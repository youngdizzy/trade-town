"""app/strategy_complexity.py — CEO directive "TradeTown — 11/10
Strategy Factory + Ruthless Backtesting Engine," Section 13
(Simplicity/Complexity Score): "Give every strategy a complexity
score... Prefer strategies with HIGH ROBUSTNESS, LOW COMPLEXITY when
performance is otherwise comparable."

RESEARCH FIRST. A grep audit of this codebase's strategy-research
modules (app/strategy_engine.py, app/walk_forward.py, app/
parameter_sensitivity.py, app/cost_sensitivity.py, app/leakage_audit.py,
app/strategy_lab.py, app/strategy_tournament.py) found real coverage of
every OTHER axis the directive's own 30-section scope asks for
(backtest, walk-forward, cost sensitivity, regime testing, Monte Carlo,
look-ahead audit, benchmark comparison, a 9-stage gate, a Hall of
Fame/Failed Archive) — but no structural complexity count anywhere.
This module closes exactly that one gap, nothing else.

THE REAL COUNT, NOT A JUDGMENT. `CompiledStrategyDefinition` (app/
strategy_compiler.py) is already a fully structured rule set — this
module counts its own real, already-present pieces:
  - `step_count`      — real entries in `definition.sequence`.
  - `condition_count` — real, individually-evaluable `StrategyCondition`
                         instances, including every condition inside a
                         `trigger` step's `all_of` list (a real
                         AND-combination of N conditions is N real
                         conditions, not 1).
  - `distinct_indicator_count` — the real, deduplicated set of
                         `StrategyIndicatorName`s referenced across
                         every condition's `left`/`right_indicator`,
                         deduplicated by indicator TYPE only (e.g. an
                         "ema" trigger crossing a second, differently-
                         parametrized "ema" still counts as one
                         distinct indicator type) — a real, disclosed
                         choice that keeps this count answering "how
                         many different KINDS of technical analysis
                         does this strategy draw on," a separate
                         question from how many specific periods were
                         tuned, which `parameter_count` below already
                         counts on its own.
  - `parameter_count` — real numeric knobs a researcher could have
                         tuned: every condition's indicator `period`(s),
                         every condition's literal `right_value`, every
                         `requirement` step's `min_consecutive_bars`,
                         and the stop/target spec's own real numeric
                         fields (`atr_period`/`atr_multiplier`/`percent`
                         for whichever stop method is set; `target.value`
                         if a target is set).

Nothing here is a subjective "this strategy sounds complicated"
judgment, and nothing here inspects a strategy's own backtest
performance — nothing here even needs candle data. A minimal strategy
(one trigger, one entry, no requirement, a `swing_level` stop with no
extra params) and a large one (a five-step sequence, a multi-condition
`all_of` trigger, several tuned periods, an ATR stop with both
`atr_period` and `atr_multiplier` set) are told apart purely by their
own real structure.

`band` IS ONE DISCLOSED CONVENTION, NOT THE ONLY VALID ONE. The
threshold constants below (`COMPLEXITY_SIMPLE_MAX`/
`COMPLEXITY_MODERATE_MAX`) are real, round, disclosed numbers chosen
for this module, not tuned to any particular strategy already in this
codebase's own default library and not derived from any statistical
study — the same "real, disclosed, simple formula, never the only
valid one" honesty idiom this codebase's other per-module thresholds
(`MIN_ACCURACY_SAMPLE_FOR_VERDICT`, `HALL_OF_FAME_MIN_TRADE_COUNT`,
etc.) already use.

ADVISORY ONLY. This score is packaged into `ResearchExperimentRecord`
(see app/research_experiment.py) for a CEO/agent to read alongside
every other real research axis. It is NOT wired into
`_synthesize_conclusion()`'s pass/fail rule, the Gatekeeper, the
sandbox stage machine, or `strategy_tournament.py`'s ranking — the
directive's own Section 5 draws a clear line between "hard performance
gates" (which this is explicitly not one of) and complexity, which its
own Section 13 frames as a tie-breaker ("when performance is otherwise
comparable"), not a gate. Wiring it into an actual tie-breaking rule is
real, tractable future work, deliberately not attempted in this pass.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import CompiledStrategyDefinition, StrategyComplexityBand, StrategyComplexityScore

# See this module's own docstring for why these are one real, disclosed
# convention among several valid ones, not derived from any study of
# this codebase's own strategies.
COMPLEXITY_SIMPLE_MAX = 6
COMPLEXITY_MODERATE_MAX = 12


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_strategy_complexity(definition: CompiledStrategyDefinition) -> StrategyComplexityScore:
    """Pure structural count over `definition` — no candle data, no
    backtest, no market state. See this module's own docstring for
    exactly what each count means and why `complexity_score` is a
    simple, disclosed sum rather than a weighted/fitted formula."""
    conditions = []
    for step in definition.sequence:
        if step.condition is not None:
            conditions.append(step.condition)
        if step.all_of:
            conditions.extend(step.all_of)

    indicators: set[str] = set()
    parameter_count = 0
    for condition in conditions:
        indicators.add(condition.left.indicator)
        if condition.left.period is not None:
            parameter_count += 1
        if condition.right_indicator is not None:
            indicators.add(condition.right_indicator.indicator)
            if condition.right_indicator.period is not None:
                parameter_count += 1
        if condition.right_value is not None:
            parameter_count += 1

    for step in definition.sequence:
        if step.min_consecutive_bars is not None:
            parameter_count += 1

    if definition.stop is not None:
        parameter_count += sum(1 for v in (definition.stop.atr_period, definition.stop.atr_multiplier, definition.stop.percent) if v is not None)
    if definition.target is not None:
        parameter_count += 1

    step_count = len(definition.sequence)
    condition_count = len(conditions)
    distinct_indicator_count = len(indicators)
    complexity_score = step_count + condition_count + distinct_indicator_count + parameter_count

    band: StrategyComplexityBand
    if complexity_score <= COMPLEXITY_SIMPLE_MAX:
        band = "simple"
    elif complexity_score <= COMPLEXITY_MODERATE_MAX:
        band = "moderate"
    else:
        band = "complex"

    detail = (
        f"{step_count} sequence step(s), {condition_count} real condition(s) referencing {distinct_indicator_count} "
        f"distinct indicator(s), {parameter_count} tunable numeric parameter(s) -- complexity score {complexity_score} ({band})."
    )

    return StrategyComplexityScore(
        definitionId=definition.id,
        definitionVersion=definition.version,
        stepCount=step_count,
        conditionCount=condition_count,
        distinctIndicatorCount=distinct_indicator_count,
        parameterCount=parameter_count,
        complexityScore=complexity_score,
        band=band,
        detail=detail,
        generatedAt=_now_iso(),
    )
