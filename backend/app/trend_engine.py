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
    HorizonTrendReading,
    MultiHorizonTrendScore,
    ResearchCategory,
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


def _endpoint_slope(candles: list[Candle], lookback_bars: int) -> tuple[float, int, str]:
    window = candles[-lookback_bars:]
    if len(window) < 2 or window[0].close <= 0:
        return 0.0, 0, "Insufficient real history for this horizon."
    pct_per_bar = (window[-1].close - window[0].close) / window[0].close * 100 / (len(window) - 1)
    return pct_per_bar, _direction_from_pct(pct_per_bar), f"Endpoint slope: {pct_per_bar:+.3f}%/bar over {len(window)} real bars (first close {window[0].close:.2f} -> last close {window[-1].close:.2f})."


def _regression_slope(candles: list[Candle], lookback_bars: int) -> tuple[float, int, str]:
    window = candles[-lookback_bars:]
    log_closes = [math.log(c.close) for c in window if c.close > 0]
    result = _ols_slope(log_closes)
    if result is None or len(log_closes) < 3:
        return 0.0, 0, "Insufficient real history for a real OLS regression on this horizon."
    pct_per_bar = result.slope * 100
    return pct_per_bar, _direction_from_pct(pct_per_bar), f"Real OLS slope of log(close) vs. bar index over {len(log_closes)} real bars: {pct_per_bar:+.3f}%/bar."


def _normalized_slope(candles: list[Candle], lookback_bars: int) -> tuple[float, int, str]:
    window = candles[-lookback_bars:]
    log_closes = [math.log(c.close) for c in window if c.close > 0]
    result = _ols_slope(log_closes)
    if result is None or len(log_closes) < 3:
        return 0.0, 0, "Insufficient real history for a real OLS regression on this horizon."
    # A residual std of exactly (or near) zero means an almost perfectly
    # linear real trend, not "no data" — floored, never rejected, so a
    # textbook-clean trend correctly reads as a very strong signal
    # instead of "insufficient."
    residual_std = max(result.residual_std, 1e-6)
    t_like = result.slope / residual_std
    direction = 1 if t_like > _DIRECTION_THRESHOLD_PCT else (-1 if t_like < -_DIRECTION_THRESHOLD_PCT else 0)
    return t_like, direction, f"Real OLS slope ({result.slope * 100:+.3f}%/bar) divided by the regression's own real residual std ({residual_std:.6f}, floored) — a t-like statistic of how confidently linear this horizon's trend is: {t_like:+.3f}."


def _price_vs_ma(candles: list[Candle], lookback_bars: int) -> tuple[float, int, str]:
    series = ema_series(candles, lookback_bars)
    if not series or candles[-1].close <= 0:
        return 0.0, 0, f"Insufficient real history for a real {lookback_bars}-period EMA."
    ma_value = series[-1]
    if ma_value <= 0:
        return 0.0, 0, "Real EMA value was non-positive; cannot compute a real % distance."
    pct = (candles[-1].close - ma_value) / ma_value * 100
    return pct, _direction_from_pct(pct), f"Real close ({candles[-1].close:.2f}) vs. real {lookback_bars}-period EMA ({ma_value:.2f}): {pct:+.3f}%."


def _volatility_normalized(candles: list[Candle], lookback_bars: int) -> tuple[float, int, str]:
    window = candles[-lookback_bars:]
    if len(window) < 3 or window[0].close <= 0:
        return 0.0, 0, "Insufficient real history for a volatility-normalized read."
    return_pct = (window[-1].close - window[0].close) / window[0].close * 100
    vol_pct = max(volatility_pct(window), _VOLATILITY_FLOOR_PCT)
    ratio = return_pct / vol_pct
    return ratio, _direction_from_pct(ratio * _DIRECTION_THRESHOLD_PCT), f"Real return over horizon ({return_pct:+.3f}%) divided by real per-bar volatility ({vol_pct:.3f}%): a Sharpe-like ratio of {ratio:+.3f}."


def _breakout_channel(candles: list[Candle], lookback_bars: int) -> tuple[float, int, str]:
    window = candles[-lookback_bars:]
    if len(window) < 2:
        return 0.5, 0, "Insufficient real history for a real breakout-channel read."
    channel_high = max(c.high for c in window)
    channel_low = min(c.low for c in window)
    if channel_high <= channel_low:
        return 0.5, 0, "Real channel had zero real range; cannot compute a real position."
    position = (window[-1].close - channel_low) / (channel_high - channel_low)
    direction = 1 if position >= _BREAKOUT_UPPER else (-1 if position <= _BREAKOUT_LOWER else 0)
    return position, direction, f"Real close sits at {position * 100:.1f}% of the real {len(window)}-bar high/low channel (low {channel_low:.2f}, high {channel_high:.2f})."


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
    raw_value, direction, detail = _METHOD_DISPATCH[method](candles, lookback_bars)
    return HorizonTrendReading(horizonLabel=horizon_label, lookbackBars=lookback_bars, method=method, rawValue=round(raw_value, 6), direction=direction, detail=detail)  # type: ignore[arg-type]


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
    readings = [compute_horizon_trend(candles, label, lookback, method) for label, lookback in resolved_horizons]
    composite = float(sum(r.direction for r in readings))
    normalized = composite / len(readings) if readings else 0.0
    last = candles[-1] if candles else None
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
            )
        )
    rankings.sort(key=lambda r: r.composite_score, reverse=True)
    return rankings


# Only bucket a "strong" signal state (matches the CEO worked example's
# own +-2/+-4 language for "moderate"/"strongest") — a composite near
# zero is a real no-signal state, not evidence either way, and including
# it would dilute the regime-conditional hit-rate read with noise.
_REGIME_BREAKDOWN_STRONG_THRESHOLD = 2.0


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
    reached a "strong" state (see `_REGIME_BREAKDOWN_STRONG_THRESHOLD`),
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
        if abs(score.composite_score) < _REGIME_BREAKDOWN_STRONG_THRESHOLD:
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
        f"{total_signals} real historical bars where the composite score reached |score| >= {_REGIME_BREAKDOWN_STRONG_THRESHOLD:.0f} across {len(bucket_reads)} distinct regimes, "
        f"each evaluated using only data available at that bar (point-in-time correct)."
        if total_signals > 0
        else "No historical bar in this sample ever reached the strong-signal threshold — no regime breakdown evidence to report."
    )
    return TrendRegimeBreakdown(symbol=symbol, timeframe=timeframe, forwardBars=forward_bars, buckets=bucket_reads, detail=detail)
