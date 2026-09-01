"""CEO directive "Phase 9 / Real Market Data + Evidence Integrity
Foundation" — Feature Store section.

RESEARCH FIRST: this is METADATA only, never a second indicator
implementation and never a computed-value cache. Every real indicator
value a compiled strategy can reference already comes from exactly one
place — `app/technical_indicators.py` (raw OHLC fields, sma/ema/rsi/
macd/stochastic/atr/vwap) or one of the AHL-directive research wrappers
(`app/trend_engine.py`, `app/liquidity_sweep_research.py`,
`app/structure_break_research.py`, `app/fvg_research.py`,
`app/fibonacci_research.py`) — this module never re-derives any of that
math, it only names and versions what already exists so a research
record can disclose exactly which feature definitions backed it.

`FEATURE_REGISTRY` maps every `StrategyIndicatorName` (app/schemas.py)
to a real `FeatureDescriptor`. `feature_versions_for_definition()`
extracts the distinct indicator names a `CompiledStrategyDefinition`
actually references — the same real extraction
`app/strategy_complexity.py::compute_strategy_complexity()` already
performs over `condition.left`/`condition.right_indicator` — and
resolves each to its registry version string. Not imported from that
module because it exposes only a count, not the indicator set itself;
this is the same ~10-line structural walk, not a second implementation
of anything indicator-related.

VERSIONING HONESTY: a version bumps only when this module's own author
changes what a name *means* (a different lookback default, a different
smoothing method) — never automatically, never tied to dataset content.
Today every indicator is at its first version ("...-v1") because none
of these implementations have changed since they shipped."""
from __future__ import annotations

from app.schemas import CompiledStrategyDefinition, FeatureDescriptor

FEATURE_REGISTRY: dict[str, FeatureDescriptor] = {
    "price_close": FeatureDescriptor(
        name="price_close", version="raw-ohlc-v1", sourceFields=["close"],
        lookbackBars=0, warmupBars=0, timestampSemantics="bar_close",
        provenance="app/market_data.py Candle.close (raw field, no derived computation).",
    ),
    "price_open": FeatureDescriptor(
        name="price_open", version="raw-ohlc-v1", sourceFields=["open"],
        lookbackBars=0, warmupBars=0, timestampSemantics="bar_open",
        provenance="app/market_data.py Candle.open (raw field, no derived computation).",
    ),
    "price_high": FeatureDescriptor(
        name="price_high", version="raw-ohlc-v1", sourceFields=["high"],
        lookbackBars=0, warmupBars=0, timestampSemantics="bar_range",
        provenance="app/market_data.py Candle.high (raw field, no derived computation).",
    ),
    "price_low": FeatureDescriptor(
        name="price_low", version="raw-ohlc-v1", sourceFields=["low"],
        lookbackBars=0, warmupBars=0, timestampSemantics="bar_range",
        provenance="app/market_data.py Candle.low (raw field, no derived computation).",
    ),
    "sma": FeatureDescriptor(
        name="sma", version="sma-v1", sourceFields=["close"],
        warmupBars=None, timestampSemantics="bar_close",
        provenance="app/technical_indicators.py::sma_series() — simple moving average of close.",
    ),
    "ema": FeatureDescriptor(
        name="ema", version="ema-v1", sourceFields=["close"],
        warmupBars=None, timestampSemantics="bar_close",
        provenance="app/technical_indicators.py::ema_series() — exponential moving average of close.",
    ),
    "rsi": FeatureDescriptor(
        name="rsi", version="rsi-v1", sourceFields=["close"],
        warmupBars=None, timestampSemantics="bar_close",
        provenance="app/technical_indicators.py::rsi_series() — Wilder-smoothed RSI of close.",
    ),
    "macd_line": FeatureDescriptor(
        name="macd_line", version="macd-v1", sourceFields=["close"],
        warmupBars=None, timestampSemantics="bar_close",
        provenance="app/technical_indicators.py::macd_series() — MACD line (fast EMA - slow EMA).",
    ),
    "macd_signal": FeatureDescriptor(
        name="macd_signal", version="macd-v1", sourceFields=["close"],
        warmupBars=None, timestampSemantics="bar_close",
        provenance="app/technical_indicators.py::macd_series() — signal line (EMA of MACD line).",
    ),
    "macd_histogram": FeatureDescriptor(
        name="macd_histogram", version="macd-v1", sourceFields=["close"],
        warmupBars=None, timestampSemantics="bar_close",
        provenance="app/technical_indicators.py::macd_series() — histogram (MACD line - signal line).",
    ),
    "stochastic_percent_k": FeatureDescriptor(
        name="stochastic_percent_k", version="stochastic-v1", sourceFields=["high", "low", "close"],
        warmupBars=None, timestampSemantics="bar_close",
        provenance="app/technical_indicators.py::stochastic_series() — %K.",
    ),
    "stochastic_percent_d": FeatureDescriptor(
        name="stochastic_percent_d", version="stochastic-v1", sourceFields=["high", "low", "close"],
        warmupBars=None, timestampSemantics="bar_close",
        provenance="app/technical_indicators.py::stochastic_series() — %D (smoothed %K).",
    ),
    "atr": FeatureDescriptor(
        name="atr", version="atr-v1", sourceFields=["high", "low", "close"],
        warmupBars=None, timestampSemantics="bar_close",
        provenance="app/technical_indicators.py::atr_series() — Wilder-smoothed average true range.",
    ),
    "vwap": FeatureDescriptor(
        name="vwap", version="vwap-v1", sourceFields=["high", "low", "close", "volume"],
        lookbackBars=None, warmupBars=0, timestampSemantics="bar_close",
        provenance="app/technical_indicators.py::vwap() — cumulative volume-weighted average price.",
    ),
    "multi_horizon_trend_score": FeatureDescriptor(
        name="multi_horizon_trend_score", version="multi_horizon_v1", sourceFields=["close"],
        warmupBars=None, timestampSemantics="bar_close",
        provenance="app/trend_engine.py — equal-weight signed sum of real per-horizon directions (TREND_ENGINE_METHODOLOGY_VERSION).",
    ),
    "liquidity_sweep_signal": FeatureDescriptor(
        name="liquidity_sweep_signal", version="event-signal-v1", sourceFields=["high", "low", "close"],
        warmupBars=None, timestampSemantics="bar_close",
        provenance="app/liquidity_sweep_research.py::liquidity_sweep_signal_series() wrapping app/market_intelligence.py::compute_liquidity().",
    ),
    "structure_break_signal": FeatureDescriptor(
        name="structure_break_signal", version="event-signal-v1", sourceFields=["high", "low", "close"],
        warmupBars=None, timestampSemantics="bar_close",
        provenance="app/structure_break_research.py wrapping app/market_intelligence.py::compute_market_structure() (Break of Structure).",
    ),
    "choch_signal": FeatureDescriptor(
        name="choch_signal", version="event-signal-v1", sourceFields=["high", "low", "close"],
        warmupBars=None, timestampSemantics="bar_close",
        provenance="app/structure_break_research.py::change_of_character_signal_series() wrapping compute_market_structure().",
    ),
    "fvg_signal": FeatureDescriptor(
        name="fvg_signal", version="event-signal-v1", sourceFields=["high", "low", "close"],
        warmupBars=None, timestampSemantics="bar_close",
        provenance="app/fvg_research.py::fvg_signal_series() wrapping app/technical_patterns.py::detect_fair_value_gaps().",
    ),
    "fibonacci_618_level": FeatureDescriptor(
        name="fibonacci_618_level", version="fib-618-v1", sourceFields=["high", "low", "close"],
        warmupBars=None, timestampSemantics="bar_close",
        provenance="app/fibonacci_research.py::fibonacci_618_level_series() wrapping app/technical_patterns.py::compute_fibonacci_levels().",
    ),
}


def _distinct_indicator_names(definition: CompiledStrategyDefinition) -> set[str]:
    """Same real extraction as app/strategy_complexity.py::
    compute_strategy_complexity() — condition.left/right_indicator
    across every sequence step's own condition (including all_of) —
    reused as a small, disclosed structural walk rather than importing
    that module's count-only result."""
    indicators: set[str] = set()
    for step in definition.sequence:
        conditions = []
        if step.condition is not None:
            conditions.append(step.condition)
        if step.all_of:
            conditions.extend(step.all_of)
        for condition in conditions:
            indicators.add(condition.left.indicator)
            if condition.right_indicator is not None:
                indicators.add(condition.right_indicator.indicator)
    return indicators


def feature_versions_for_definition(definition: CompiledStrategyDefinition) -> list[str]:
    """Real `FeatureDescriptor.version` strings for every distinct
    indicator `definition`'s own compiled sequence actually references
    — sorted for a stable, comparable output. An indicator name absent
    from `FEATURE_REGISTRY` (should not happen — every `StrategyIndicatorName`
    literal has an entry above) is skipped rather than raising, since this
    is disclosure metadata, never a gate."""
    names = _distinct_indicator_names(definition)
    versions = {FEATURE_REGISTRY[name].version for name in names if name in FEATURE_REGISTRY}
    return sorted(versions)
