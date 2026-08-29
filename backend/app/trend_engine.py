"""app/trend_engine.py — CEO directive "AHL-Inspired Systematic Trend &
Momentum Research Engine."

WHAT THIS IS. A reusable research module that measures directional
strength across multiple time horizons and multiple independent
mathematical definitions of "trend," combines them into an explicit,
versioned composite score, and — separately — researches an AHL-style
inverse-volatility exposure idea. Every function here is a REAL,
deterministic computation over the real (mock) candle history this
codebase already generates (app/market_data.py) — never a fabricated
number, never a hardcoded "this works."

WHAT THIS IS NOT. This module produces evidence/features, never a trade.
It never places an order, never sizes a live position, and never
overrides app/risk_engine.py, app/gatekeeper.py, or app/position_
sizing.py, which remain the sole real authority over whether and how
much to trade. `VolatilityScaledExposureResearch` below is explicitly a
RESEARCH comparison, not a live sizing input.

"AHL-INSPIRED," NOT "AHL." The multi-horizon scoring idea and the
inverse-volatility sizing idea are both modeled on publicly described
managed-futures / trend-following research themes (Man AHL's own public
explainer pages on momentum and volatility scaling — see this module's
own methodology-version docstrings for what's a genuine external idea
vs. this codebase's own disclosed simplification). This module makes NO
claim to reproduce AHL's actual proprietary methodology, and no claim
that any external firm's real historical results say anything about
whether this methodology would be profitable on TradeTown's own (mock)
data. Every claim this module or its callers make must come from a real
computation against real (mock) data run through this codebase's
existing validation pipeline (app/research_experiment.py,
app/walk_forward.py, app/cost_sensitivity.py, app/leakage_audit.py) —
never an assertion of profitability on its own.

POINT-IN-TIME CORRECTNESS — THE CENTRAL DISCIPLINE. Every function in
this module takes a `candles: list[Candle]` sample and treats its LAST
element as the evaluation point; nothing here ever looks past the end of
the list it was given. A caller building a full historical series (see
`multi_horizon_trend_score_series()`) is responsible for slicing
`candles[: i + 1]` for each index `i` — the module's own test suite
(test_trend_engine.py) includes an adversarial regression test proving
that appending future candles to the end of an already-computed series
never changes an earlier index's own already-computed reading.

MULTIPLE INDEPENDENT DEFINITIONS, NEVER SILENTLY MERGED. `endpoint_
slope`, `regression_slope`, `normalized_slope`, `price_vs_ma`,
`volatility_normalized`, and `breakout_channel` are six real,
independently-computable trend measurements. A caller must pick one; this
module never averages across methodologies behind the scenes — that
comparison is exactly what the Research Desk is for.

REUSE, NOT DUPLICATION. Moving averages reuse app/technical_
indicators.py's `sma_series()`/`ema_series()` (already cached, already
tested) — no indicator math is re-derived here. Regime bucketing reuses
app/backtest_primitives.py's `regime_trend_at()` — the exact same proxy
app/strategy_engine.py's own regime tagging already uses, not a second
classifier. Volatility reuses app/market_data.py's `volatility_pct()`
convention (average per-bar range as % of close) for consistency with
every other real volatility read in this codebase.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from app.backtest_primitives import regime_trend_at
from app.market_data import Candle, volatility_pct
from app.schemas import (
    EvidenceAlignment,
    HorizonTrendReading,
    MultiHorizonTrendScore,
    ResearchCategory,
    SignalState,
    SymbolTrendRanking,
    TrendDefinitionMethod,
    TrendEnsembleReading,
    TrendRegimeBreakdown,
    TrendRegimeBucket,
    TrendWeightingMethod,
    VolatilityScaledExposureResearch,
)
from app.technical_indicators import ema_series

# The one versioned aggregation rule this module ships today — a real,
# disclosed choice (equal-weight signed sum of each horizon's discrete
# +1/0/-1 direction), not the only mathematically valid one. A future
# methodology (e.g. continuous-weighted, volatility-adjusted per-horizon)
# must ship under a NEW version string so an old MultiHorizonTrendScore
# reading is never silently reinterpreted under different math.
TREND_ENGINE_METHODOLOGY_VERSION = "multi_horizon_v1"

# Default horizons, expressed in BARS, not calendar time — the labels
# below assume a daily-timeframe candle series (so "1_week" == 5 trading
# days); pass a different `horizons` list of (label, bar_count) pairs
# when using another timeframe. This mirrors the CEO's own worked
# example (1wk/2wk/1mo/2mo) without assuming it is the only valid choice
# — every research call can override it.
DEFAULT_HORIZONS: list[tuple[str, int]] = [("1_week", 5), ("2_week", 10), ("1_month", 20), ("2_month", 40)]
DEFAULT_FAST_HORIZONS: list[tuple[str, int]] = [("3_day", 3), ("5_day", 5)]
DEFAULT_MEDIUM_HORIZONS: list[tuple[str, int]] = [("10_day", 10), ("20_day", 20)]
DEFAULT_SLOW_HORIZONS: list[tuple[str, int]] = [("40_day", 40), ("60_day", 60)]

# A real, disclosed direction-noise threshold — the same role app/
# strategy_engine.py's own TREND_SLOPE_THRESHOLD_PCT already plays: below
# this magnitude, a raw reading is reported as direction 0 ("no real
# signal") rather than an arbitrary tiny positive/negative flip.
_DIRECTION_THRESHOLD_PCT = 0.15
_BREAKOUT_UPPER = 0.8
_BREAKOUT_LOWER = 0.2
# Phase 4's explicit requirement: volatility approaching zero must never
# create absurd leverage in the (research-only) volatility-scaled
# exposure calculation below.
_VOLATILITY_FLOOR_PCT = 0.05

# The one real, disclosed threshold this module uses to classify a
# composite score as "strong" — shared by `_signal_state_from_score()`
# (Phase 5/28/29's SignalState vocabulary) and
# `compute_trend_regime_breakdown()`'s own "strong signal" bucketing
# below, so both readings always agree on what "strong" means. Not the
# only valid threshold a researcher could choose.
_STRONG_SIGNAL_THRESHOLD = 2.0


def _direction_from_pct(value_pct: float) -> int:
    if value_pct > _DIRECTION_THRESHOLD_PCT:
        return 1
    if value_pct < -_DIRECTION_THRESHOLD_PCT:
        return -1
    return 0


def _log_returns(candles: list[Candle]) -> list[float]:
    out: list[float] = []
    for prev, cur in zip(candles, candles[1:]):
        if prev.close > 0 and cur.close > 0:
            out.append(math.log(cur.close / prev.close))
    return out


@dataclass
class _OlsResult:
    slope: float
    intercept: float
    residual_std: float


def _ols_slope(y: list[float]) -> _OlsResult | None:
    """Real, textbook closed-form ordinary-least-squares slope of `y`
    against x = 0..n-1 — no external stats library, just the standard
    covariance/variance formula, so this module has zero new
    dependencies. Returns None only when there's too little data or `x`
    has zero variance (can't happen here since x is always 0..n-1 with
    n>=2, kept as a defensive guard, not a real code path)."""
    n = len(y)
    if n < 2:
        return None
    mean_x = (n - 1) / 2
    mean_y = sum(y) / n
    var_x = sum((i - mean_x) ** 2 for i in range(n))
    if var_x == 0:
        return None
    cov_xy = sum((i - mean_x) * (y[i] - mean_y) for i in range(n))
    slope = cov_xy / var_x
    intercept = mean_y - slope * mean_x
    residuals = [y[i] - (intercept + slope * i) for i in range(n)]
    residual_std = math.sqrt(sum(r * r for r in residuals) / n)
    return _OlsResult(slope=slope, intercept=intercept, residual_std=residual_std)


def _endpoint_slope(candles: list[Candle], lookback_bars: int) -> tuple[float, int, str, bool]:
    window = candles[-lookback_bars:]
    if len(window) < 2 or window[0].close <= 0:
        return 0.0, 0, "Insufficient real history for this horizon.", False
    pct_per_bar = (window[-1].close - window[0].close) / window[0].close * 100 / (len(window) - 1)
    return pct_per_bar, _direction_from_pct(pct_per_bar), f"Endpoint slope: {pct_per_bar:+.3f}%/bar over {len(window)} real bars (first close {window[0].close:.2f} -> last close {window[-1].close:.2f}).", True


def _regression_slope(candles: list[Candle], lookback_bars: int) -> tuple[float, int, str, bool]:
    window = candles[-lookback_bars:]
    log_closes = [math.log(c.close) for c in window if c.close > 0]
    result = _ols_slope(log_closes)
    if result is None or len(log_closes) < 3:
        return 0.0, 0, "Insufficient real history for a real OLS regression on this horizon.", False
    pct_per_bar = result.slope * 100
    return pct_per_bar, _direction_from_pct(pct_per_bar), f"Real OLS slope of log(close) vs. bar index over {len(log_closes)} real bars: {pct_per_bar:+.3f}%/bar.", True


def _normalized_slope(candles: list[Candle], lookback_bars: int) -> tuple[float, int, str, bool]:
    window = candles[-lookback_bars:]
    log_closes = [math.log(c.close) for c in window if c.close > 0]
    result = _ols_slope(log_closes)
    if result is None or len(log_closes) < 3:
        return 0.0, 0, "Insufficient real history for a real OLS regression on this horizon.", False
    # A residual std of exactly (or near) zero means an almost perfectly
    # linear real trend, not "no data" — floored, never rejected, so a
    # textbook-clean trend correctly reads as a very strong signal
    # instead of "insufficient."
    residual_std = max(result.residual_std, 1e-6)
    t_like = result.slope / residual_std
    direction = 1 if t_like > _DIRECTION_THRESHOLD_PCT else (-1 if t_like < -_DIRECTION_THRESHOLD_PCT else 0)
    return t_like, direction, f"Real OLS slope ({result.slope * 100:+.3f}%/bar) divided by the regression's own real residual std ({residual_std:.6f}, floored) — a t-like statistic of how confidently linear this horizon's trend is: {t_like:+.3f}.", True


def _price_vs_ma(candles: list[Candle], lookback_bars: int) -> tuple[float, int, str, bool]:
    series = ema_series(candles, lookback_bars)
    if not series or candles[-1].close <= 0:
        return 0.0, 0, f"Insufficient real history for a real {lookback_bars}-period EMA.", False
    ma_value = series[-1]
    if ma_value <= 0:
        return 0.0, 0, "Real EMA value was non-positive; cannot compute a real % distance.", False
    pct = (candles[-1].close - ma_value) / ma_value * 100
    return pct, _direction_from_pct(pct), f"Real close ({candles[-1].close:.2f}) vs. real {lookback_bars}-period EMA ({ma_value:.2f}): {pct:+.3f}%.", True


def _volatility_normalized(candles: list[Candle], lookback_bars: int) -> tuple[float, int, str, bool]:
    window = candles[-lookback_bars:]
    if len(window) < 3 or window[0].close <= 0:
        return 0.0, 0, "Insufficient real history for a volatility-normalized read.", False
    return_pct = (window[-1].close - window[0].close) / window[0].close * 100
    vol_pct = max(volatility_pct(window), _VOLATILITY_FLOOR_PCT)
    ratio = return_pct / vol_pct
    return ratio, _direction_from_pct(ratio * _DIRECTION_THRESHOLD_PCT), f"Real return over horizon ({return_pct:+.3f}%) divided by real per-bar volatility ({vol_pct:.3f}%): a Sharpe-like ratio of {ratio:+.3f}.", True


def _breakout_channel(candles: list[Candle], lookback_bars: int) -> tuple[float, int, str, bool]:
    window = candles[-lookback_bars:]
    if len(window) < 2:
        return 0.5, 0, "Insufficient real history for a real breakout-channel read.", False
    channel_high = max(c.high for c in window)
    channel_low = min(c.low for c in window)
    if channel_high <= channel_low:
        return 0.5, 0, "Real channel had zero real range; cannot compute a real position.", False
    position = (window[-1].close - channel_low) / (channel_high - channel_low)
    direction = 1 if position >= _BREAKOUT_UPPER else (-1 if position <= _BREAKOUT_LOWER else 0)
    return position, direction, f"Real close sits at {position * 100:.1f}% of the real {len(window)}-bar high/low channel (low {channel_low:.2f}, high {channel_high:.2f}).", True


_METHOD_DISPATCH = {
    "endpoint_slope": _endpoint_slope,
    "regression_slope": _regression_slope,
    "normalized_slope": _normalized_slope,
    "price_vs_ma": _price_vs_ma,
    "volatility_normalized": _volatility_normalized,
    "breakout_channel": _breakout_channel,
}


def compute_horizon_trend(candles: list[Candle], horizon_label: str, lookback_bars: int, method: TrendDefinitionMethod) -> HorizonTrendReading:
    """One horizon's real, independent directional read. `candles`'s
    last element is always treated as the evaluation point — callers
    building a historical series must pass an already-truncated sample
    (see this module's own point-in-time-correctness discipline in the
    module docstring)."""
    raw_value, direction, detail, sufficient = _METHOD_DISPATCH[method](candles, lookback_bars)
    return HorizonTrendReading(horizonLabel=horizon_label, lookbackBars=lookback_bars, method=method, rawValue=round(raw_value, 6), direction=direction, detail=detail, dataQuality="ok" if sufficient else "insufficient_data")  # type: ignore[arg-type]


def _is_real_price(value: float) -> bool:
    """Mirrors app/volume_analysis.py's own `_is_real_volume()`
    convention for this module's real-valued price inputs — a plain
    `<= 0` guard alone never catches NaN (`float('nan') <= 0` is False
    in Python)."""
    return math.isfinite(value) and value > 0


def _candle_data_invalid_reason(candles: list[Candle]) -> str | None:
    """A real, upfront data-quality gate over the whole real candle
    sample passed to `compute_multi_horizon_trend_score()`, checked
    once before any per-horizon math runs — Phase 28's explicit "do not
    calculate a score on invalid data" requirement. Returns None when
    the sample is clean; otherwise a real, specific reason string. An
    EMPTY sample is deliberately NOT invalid here (that's the separate,
    already-handled `insufficient_data` state — see
    `_signal_state_from_score()`); this function only catches real
    corruption shapes (non-finite/non-positive OHLC, an impossible
    high/low ordering, non-increasing real timestamps), matching this
    codebase's own chaos-testing convention (relative-volume's own
    `_is_real_volume()` gate) rather than reinventing a general
    market-data validator — that remains app/market_data.py's own job
    for data it originates."""
    for c in candles:
        if not (_is_real_price(c.close) and _is_real_price(c.high) and _is_real_price(c.low) and _is_real_price(c.open)):
            return f"Non-finite or non-positive real OHLC price found at {c.timestamp} — real data corruption, not a research signal."
        if c.high < c.low:
            return f"Impossible real OHLC at {c.timestamp}: high ({c.high}) < low ({c.low})."
    for prev, cur in zip(candles, candles[1:]):
        if cur.timestamp <= prev.timestamp:
            return f"Non-increasing real timestamps ({prev.timestamp} -> {cur.timestamp}) — a duplicate or out-of-order real candle."
    return None


def _signal_state_from_score(composite_score: float, horizons: list[HorizonTrendReading]) -> tuple[SignalState, bool, str]:
    """The one real, disclosed rule mapping a composite score to the
    explicit qualitative vocabulary Phase 5/28/29 ask for.
    `eligible_for_trade` means only "this reading is backed by valid,
    sufficient real data" — see `SignalState`'s own docstring for why
    that is never a trade permission."""
    if not horizons or all(h.data_quality == "insufficient_data" for h in horizons):
        n = len(horizons)
        return "insufficient_data", False, (f"None of the {n} real horizons had enough real candle history to produce a directional read yet." if n else "No real horizons were evaluated (empty candle sample).")
    if composite_score >= _STRONG_SIGNAL_THRESHOLD:
        return "strong_long", True, f"Composite score {composite_score:+.1f} >= +{_STRONG_SIGNAL_THRESHOLD:.1f} — strong real directional agreement, long."
    if composite_score > 0:
        return "weak_long", True, f"Composite score {composite_score:+.1f} is positive but below the +{_STRONG_SIGNAL_THRESHOLD:.1f} strong threshold — weak real long evidence."
    if composite_score <= -_STRONG_SIGNAL_THRESHOLD:
        return "strong_short", True, f"Composite score {composite_score:+.1f} <= -{_STRONG_SIGNAL_THRESHOLD:.1f} — strong real directional agreement, short."
    if composite_score < 0:
        return "weak_short", True, f"Composite score {composite_score:+.1f} is negative but above the -{_STRONG_SIGNAL_THRESHOLD:.1f} strong threshold — weak real short evidence."
    return "neutral", True, "Composite score is exactly 0.0 — the real horizons disagree or show no net real directional evidence."


def compute_multi_horizon_trend_score(
    candles: list[Candle],
    symbol: str,
    timeframe: str,
    *,
    horizons: list[tuple[str, int]] | None = None,
    method: TrendDefinitionMethod = "endpoint_slope",
) -> MultiHorizonTrendScore:
    """The real, versioned composite: an equal-weight signed sum of each
    horizon's own real +1/0/-1 direction (see TREND_ENGINE_METHODOLOGY_
    VERSION's own docstring for why this specific aggregation, not a
    claim it's the only valid one). `evaluated_at_index`/`_timestamp`
    always describe the real last candle in the sample passed in."""
    resolved_horizons = horizons if horizons is not None else DEFAULT_HORIZONS
    last = candles[-1] if candles else None
    invalid_reason = _candle_data_invalid_reason(candles)
    if invalid_reason is not None:
        return MultiHorizonTrendScore(
            symbol=symbol,
            timeframe=timeframe,
            evaluatedAtIndex=len(candles) - 1,
            evaluatedAtTimestamp=last.timestamp if last else "",
            method=method,
            methodologyVersion=TREND_ENGINE_METHODOLOGY_VERSION,
            horizons=[],
            compositeScore=0.0,
            compositeScoreNormalized=0.0,
            aggregationDetail="Skipped: the real candle sample failed data-quality validation before any horizon math ran.",
            signalState="invalid_data",
            eligibleForTrade=False,
            reason=invalid_reason,
        )
    readings = [compute_horizon_trend(candles, label, lookback, method) for label, lookback in resolved_horizons]
    composite = float(sum(r.direction for r in readings))
    normalized = composite / len(readings) if readings else 0.0
    signal_state, eligible_for_trade, reason = _signal_state_from_score(composite, readings)
    return MultiHorizonTrendScore(
        symbol=symbol,
        timeframe=timeframe,
        evaluatedAtIndex=len(candles) - 1,
        evaluatedAtTimestamp=last.timestamp if last else "",
        method=method,
        methodologyVersion=TREND_ENGINE_METHODOLOGY_VERSION,
        horizons=readings,
        compositeScore=composite,
        compositeScoreNormalized=round(normalized, 4),
        aggregationDetail=f"Equal-weight signed sum of {len(readings)} real horizon directions ({', '.join(h for h, _ in resolved_horizons)}), method={method}, methodology={TREND_ENGINE_METHODOLOGY_VERSION}. Range: -{len(readings)}..+{len(readings)}.",
        signalState=signal_state,
        eligibleForTrade=eligible_for_trade,
        reason=reason,
    )


def multi_horizon_trend_score_series(
    candles: list[Candle],
    symbol: str,
    timeframe: str,
    *,
    horizons: list[tuple[str, int]] | None = None,
    method: TrendDefinitionMethod = "endpoint_slope",
) -> list[float]:
    """The full, real composite-score series — one value per candle from
    the point the longest horizon's own minimum bar count exists onward
    (0.0 before that, an honest "not enough history" placeholder, never
    a fabricated score). Built by truncating `candles[: i + 1]` at every
    index `i` — the same point-in-time discipline every other function
    here observes — so `app/strategy_engine.py`'s `_resolve()` can look
    this series up at an arbitrary historical backtest index exactly the
    way it already does for ema/sma/rsi series."""
    resolved_horizons = horizons if horizons is not None else DEFAULT_HORIZONS
    min_bars = max((lookback for _, lookback in resolved_horizons), default=1)
    series: list[float] = []
    for i in range(len(candles)):
        if i + 1 < min_bars:
            series.append(0.0)
            continue
        score = compute_multi_horizon_trend_score(candles[: i + 1], symbol, timeframe, horizons=resolved_horizons, method=method)
        series.append(score.composite_score)
    return series


_WEIGHTING_DISPATCH_LOOKBACK = {"horizon_weighted": lambda horizons: sum(lb for _, lb in horizons) / len(horizons)}


def _sign(x: float) -> int:
    return 1 if x > 0 else (-1 if x < 0 else 0)


def _evidence_alignment(fast: MultiHorizonTrendScore, medium: MultiHorizonTrendScore, slow: MultiHorizonTrendScore) -> tuple[EvidenceAlignment, str]:
    """Phase 4's explicit ALIGNED/MIXED/CONFLICTED ask — one real,
    disclosed rule for reading three independently-inspectable bands'
    own signs together, never a replacement for looking at
    fast/medium/slow individually (see `TrendEnsembleReading`'s own
    docstring). `aligned`: every band with real directional evidence
    agrees (including "no band shows any" — trivially non-conflicting).
    `mixed`: some bands show real directional evidence, others show
    none — partial, not full, agreement. `conflicted`: at least one band
    is net long and at least one is net short at the same time."""
    signs = {"fast": _sign(fast.composite_score), "medium": _sign(medium.composite_score), "slow": _sign(slow.composite_score)}
    non_neutral = {s for s in signs.values() if s != 0}
    summary = ", ".join(f"{name}={'+' if s > 0 else ('-' if s < 0 else '0')}" for name, s in signs.items())
    if not non_neutral:
        return "aligned", f"No band shows real directional evidence ({summary}) — trivially non-conflicting."
    if len(non_neutral) == 2:
        return "conflicted", f"Fast/Medium/Slow real evidence directly disagrees on direction ({summary})."
    if 0 in signs.values():
        return "mixed", f"Some bands show real directional evidence, others show none ({summary}) — partial, not full, agreement."
    return "aligned", f"Every band with real directional evidence agrees ({summary})."


def compute_trend_ensemble(
    candles: list[Candle],
    symbol: str,
    timeframe: str,
    *,
    fast_horizons: list[tuple[str, int]] | None = None,
    medium_horizons: list[tuple[str, int]] | None = None,
    slow_horizons: list[tuple[str, int]] | None = None,
    method: TrendDefinitionMethod = "endpoint_slope",
    weighting: TrendWeightingMethod = "equal",
) -> TrendEnsembleReading:
    """Fast/Medium/Slow shown DECOMPOSED — never collapsed into one
    mysterious score. `combined_score` is one additional, clearly-labeled
    view on top of the three independently-inspectable composites."""
    fast_h = fast_horizons if fast_horizons is not None else DEFAULT_FAST_HORIZONS
    medium_h = medium_horizons if medium_horizons is not None else DEFAULT_MEDIUM_HORIZONS
    slow_h = slow_horizons if slow_horizons is not None else DEFAULT_SLOW_HORIZONS

    fast = compute_multi_horizon_trend_score(candles, symbol, timeframe, horizons=fast_h, method=method)
    medium = compute_multi_horizon_trend_score(candles, symbol, timeframe, horizons=medium_h, method=method)
    slow = compute_multi_horizon_trend_score(candles, symbol, timeframe, horizons=slow_h, method=method)

    weights: list[float]
    if weighting == "equal":
        weights = [1 / 3, 1 / 3, 1 / 3]
        detail = "Equal weighting: (fast + medium + slow) / 3, each already normalized to -1..+1."
    elif weighting == "horizon_weighted":
        avg_lb = [
            _WEIGHTING_DISPATCH_LOOKBACK["horizon_weighted"](fast_h),
            _WEIGHTING_DISPATCH_LOOKBACK["horizon_weighted"](medium_h),
            _WEIGHTING_DISPATCH_LOOKBACK["horizon_weighted"](slow_h),
        ]
        total = sum(avg_lb)
        weights = [w / total for w in avg_lb] if total > 0 else [1 / 3, 1 / 3, 1 / 3]
        detail = f"Horizon-weighted: weight proportional to each group's own average real lookback ({avg_lb[0]:.1f}/{avg_lb[1]:.1f}/{avg_lb[2]:.1f} bars) — slower groups weighted more heavily, a real, disclosed research choice, not the only valid one."
    else:  # volatility_weighted
        vols = [max(volatility_pct(candles[-lb:]), _VOLATILITY_FLOOR_PCT) for lb in (fast_h[-1][1], medium_h[-1][1], slow_h[-1][1])]
        inv = [1 / v for v in vols]
        total_inv = sum(inv)
        weights = [w / total_inv for w in inv] if total_inv > 0 else [1 / 3, 1 / 3, 1 / 3]
        detail = f"Volatility-weighted: weight inversely proportional to each group's own real per-bar volatility over its slowest horizon ({vols[0]:.3f}%/{vols[1]:.3f}%/{vols[2]:.3f}% ) — steadier groups weighted more heavily."

    combined = weights[0] * fast.composite_score_normalized + weights[1] * medium.composite_score_normalized + weights[2] * slow.composite_score_normalized
    last = candles[-1] if candles else None
    alignment, alignment_detail = _evidence_alignment(fast, medium, slow)
    return TrendEnsembleReading(
        symbol=symbol,
        timeframe=timeframe,
        evaluatedAtIndex=len(candles) - 1,
        evaluatedAtTimestamp=last.timestamp if last else "",
        fast=fast,
        medium=medium,
        slow=slow,
        weightingMethod=weighting,
        combinedScore=round(combined, 4),
        combinedScoreDetail=detail,
        evidenceAlignment=alignment,
        evidenceAlignmentDetail=alignment_detail,
    )


def research_volatility_scaled_exposure(
    candles: list[Candle],
    symbol: str,
    signal_strength: float,
    *,
    target_risk_pct: float = 1.0,
    volatility_lookback_bars: int = 20,
    annualization_factor: float = 1.0,
    max_exposure_pct: float = 20.0,
) -> VolatilityScaledExposureResearch:
    """AHL-inspired inverse-volatility exposure RESEARCH — `exposure ~
    |signal_strength| * target_risk_pct / volatility`. This is a research
    candidate for comparison, never wired into app/position_sizing.py's
    real, authoritative sizing. `signal_strength` is expected to be a
    normalized composite score (e.g. `MultiHorizonTrendScore.
    composite_score_normalized`, already in -1..+1) but this function
    doesn't require that range — the caller decides what "signal
    strength" means for its own research question. A volatility floor
    (`_VOLATILITY_FLOOR_PCT`) and a hard `max_exposure_pct` cap both
    exist specifically so volatility approaching zero can never imply
    absurd leverage."""
    window = candles[-volatility_lookback_bars:]
    vol_pct = max(volatility_pct(window), _VOLATILITY_FLOOR_PCT) * math.sqrt(max(annualization_factor, 1e-9))
    raw_exposure_pct = abs(signal_strength) * target_risk_pct / vol_pct * 100
    capped_exposure_pct = min(raw_exposure_pct, max_exposure_pct)
    was_capped = capped_exposure_pct < raw_exposure_pct
    detail = (
        f"raw_exposure_pct = |{signal_strength:.3f}| * {target_risk_pct:.2f}% target risk / {vol_pct:.3f}% real volatility "
        f"(over the last {len(window)} real bars, annualization factor {annualization_factor:.2f}) = {raw_exposure_pct:.2f}%."
        + (f" Capped at the {max_exposure_pct:.1f}% hard research ceiling." if was_capped else " Not capped.")
    )
    return VolatilityScaledExposureResearch(
        symbol=symbol,
        signalStrength=signal_strength,
        volatilityEstimatePct=round(vol_pct, 4),
        volatilityLookbackBars=volatility_lookback_bars,
        targetRiskPct=target_risk_pct,
        annualizationFactor=annualization_factor,
        rawExposurePct=round(raw_exposure_pct, 4),
        cappedExposurePct=round(capped_exposure_pct, 4),
        wasCapped=was_capped,
        detail=detail,
    )


def _trend_persistence_bars(candles: list[Candle], symbol: str, timeframe: str, horizons: list[tuple[str, int]], method: TrendDefinitionMethod, max_lookback: int = 60) -> int:
    """How many of the most recent real bars the composite score's own
    sign has stayed the same — a real, computed persistence read, not
    a guess. Walks backward from the last bar only as far as
    `max_lookback` (a real cap to keep cross-sectional ranking cheap for
    large watchlists, disclosed, not silently unlimited)."""
    if len(candles) < 2:
        return 0
    current = compute_multi_horizon_trend_score(candles, symbol, timeframe, horizons=horizons, method=method)
    current_sign = 1 if current.composite_score > 0 else (-1 if current.composite_score < 0 else 0)
    if current_sign == 0:
        return 0
    persistence = 0
    for back in range(1, min(max_lookback, len(candles)) + 1):
        truncated = candles[: len(candles) - back + 1]
        if len(truncated) < 2:
            break
        score = compute_multi_horizon_trend_score(truncated, symbol, timeframe, horizons=horizons, method=method)
        sign = 1 if score.composite_score > 0 else (-1 if score.composite_score < 0 else 0)
        if sign != current_sign:
            break
        persistence += 1
    return persistence


def rank_symbols_by_trend(
    symbol_candles: dict[str, list[Candle]],
    symbol_category: dict[str, ResearchCategory],
    *,
    horizons: list[tuple[str, int]] | None = None,
    method: TrendDefinitionMethod = "endpoint_slope",
    timeframe: str = "1d",
) -> list[SymbolTrendRanking]:
    """Cross-sectional research evidence — "which symbols currently show
    the strongest, most persistent, best risk-adjusted trend agreement"
    — never an automatic trade selection. Sorted by real composite score,
    descending."""
    resolved_horizons = horizons if horizons is not None else DEFAULT_HORIZONS
    rankings: list[SymbolTrendRanking] = []
    for symbol, candles in symbol_candles.items():
        if len(candles) < 2:
            continue
        score = compute_multi_horizon_trend_score(candles, symbol, timeframe, horizons=resolved_horizons, method=method)
        persistence = _trend_persistence_bars(candles, symbol, timeframe, resolved_horizons, method)
        vol = max(volatility_pct(candles[-20:]), _VOLATILITY_FLOOR_PCT)
        risk_adjusted = score.composite_score_normalized / vol
        rankings.append(
            SymbolTrendRanking(
                symbol=symbol,
                category=symbol_category.get(symbol, "stock"),
                compositeScore=score.composite_score,
                trendPersistenceBars=persistence,
                volatilityPct=round(vol, 4),
                riskAdjustedScore=round(risk_adjusted, 4),
                signalState=score.signal_state,
            )
        )
    rankings.sort(key=lambda r: r.composite_score, reverse=True)
    return rankings


def compute_trend_regime_breakdown(
    candles: list[Candle],
    symbol: str,
    timeframe: str,
    *,
    horizons: list[tuple[str, int]] | None = None,
    method: TrendDefinitionMethod = "endpoint_slope",
    forward_bars: int = 10,
    regime_ema_period: int = 50,
    regime_slope_lookback: int = 20,
    regime_slope_threshold_pct: float = 0.5,
) -> TrendRegimeBreakdown:
    """Real, historical: for every bar where the real composite score
    reached a "strong" state (see `_STRONG_SIGNAL_THRESHOLD`),
    buckets the real forward return `forward_bars` later (signed so the
    signal's OWN claimed direction determines what counts as a "hit") by
    the real regime (`regime_trend_at()`, the exact same proxy app/
    strategy_engine.py's own regime tagging already uses) that was active
    AT signal time — never a future regime label. Small buckets are
    reported honestly, never hidden or extrapolated into a false
    confidence."""
    resolved_horizons = horizons if horizons is not None else DEFAULT_HORIZONS
    min_bars = max((lb for _, lb in resolved_horizons), default=1)
    ema_values = ema_series(candles, regime_ema_period)

    buckets: dict[str, list[float]] = {}
    for i in range(min_bars - 1, len(candles) - forward_bars):
        score = compute_multi_horizon_trend_score(candles[: i + 1], symbol, timeframe, horizons=resolved_horizons, method=method)
        if abs(score.composite_score) < _STRONG_SIGNAL_THRESHOLD:
            continue
        regime = regime_trend_at(ema_values, regime_ema_period, i, slope_lookback=regime_slope_lookback, slope_threshold_pct=regime_slope_threshold_pct)
        entry_close = candles[i].close
        future_close = candles[i + forward_bars].close
        if entry_close <= 0:
            continue
        raw_forward_return_pct = (future_close - entry_close) / entry_close * 100
        signed_forward_return_pct = raw_forward_return_pct if score.composite_score > 0 else -raw_forward_return_pct
        buckets.setdefault(regime, []).append(signed_forward_return_pct)

    bucket_reads: list[TrendRegimeBucket] = []
    for regime_key, returns in buckets.items():
        hit_rate = sum(1 for r in returns if r > 0) / len(returns) * 100
        mean_return = sum(returns) / len(returns)
        bucket_reads.append(
            TrendRegimeBucket(
                regime=regime_key,
                barsObserved=len(returns),
                meanForwardReturnPct=round(mean_return, 4),
                hitRatePct=round(hit_rate, 2),
                detail=f"{len(returns)} real strong-signal bars in the '{regime_key}' regime; mean signed {forward_bars}-bar forward return {mean_return:+.3f}%, hit rate {hit_rate:.1f}%.",
            )
        )
    bucket_reads.sort(key=lambda b: b.bars_observed, reverse=True)
    total_signals = sum(b.bars_observed for b in bucket_reads)
    detail = (
        f"{total_signals} real historical bars where the composite score reached |score| >= {_STRONG_SIGNAL_THRESHOLD:.0f} across {len(bucket_reads)} distinct regimes, "
        f"each evaluated using only data available at that bar (point-in-time correct)."
        if total_signals > 0
        else "No historical bar in this sample ever reached the strong-signal threshold — no regime breakdown evidence to report."
    )
    return TrendRegimeBreakdown(symbol=symbol, timeframe=timeframe, forwardBars=forward_bars, buckets=bucket_reads, detail=detail)
