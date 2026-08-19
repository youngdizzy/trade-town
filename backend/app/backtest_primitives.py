"""app/backtest_primitives.py — the one authoritative implementation of
the real, direction-agnostic, strategy-agnostic backtest mechanics every
bar-by-bar rule replay in this codebase needs: a real Chandelier Stop
placement and a real forward-walk exit simulation.

Extracted from app/ema_pullback_research.py (CEO directive "Professional
Trading Firm — Market-Analysis Knowledge + Session Intelligence
Expansion," Phase 15) so that module and app/strategy_engine.py (CEO
directive "Professional Quant Trading Firm — Quant Intelligence + Market
Analysis Completion Phase," Phase F's generic compiled-strategy backtest
runner) share the exact same math rather than each keeping its own
private copy — per that later directive's own Absolute Rule #1 ("there
must be one authoritative implementation for each responsibility").
app/ema_pullback_research.py's own hand-built rule-detection state
machine (_detect_setups) is NOT here — that is genuinely specific to
that one strategy's own rules, not a shared primitive.
"""
from __future__ import annotations

from dataclasses import dataclass
from statistics import median

from app.market_data import Candle
from app.schemas import EmaPullbackRegimeTrend, EmaPullbackRegimeVolatility, EmaPullbackStatsBucket, EmaPullbackTradeOutcome, EmaPullbackTradeRecord

DEFAULT_MIN_TRADES_FOR_BUCKET_VERDICT = 10


def atr_at(atr_series_values: list[float], period: int, index: int) -> float | None:
    """Looks up the real ATR value "as of" real candle `index`, given a
    series already computed by app/technical_indicators.py's
    `atr_series(candles, period)` — see that function's own docstring
    for the exact index alignment this reverses."""
    k = index - period
    return atr_series_values[k] if 0 <= k < len(atr_series_values) else None


def ema_at(ema_series_values: list[float], period: int, index: int) -> float | None:
    """Looks up the real EMA value "as of" real candle `index`, given a
    series already computed by app/technical_indicators.py's
    `ema_series(candles, period)`. A different alignment than `atr_at`
    above — `ema_series()`'s first real value represents candle index
    `period - 1` (its real SMA seed), one earlier than `atr_series()`'s
    first value (candle index `period`, its first full true-range
    window)."""
    k = index - period + 1
    return ema_series_values[k] if 0 <= k < len(ema_series_values) else None


def regime_trend_at(ema_series_values: list[float], ema_period: int, index: int, *, slope_lookback: int, slope_threshold_pct: float) -> EmaPullbackRegimeTrend:
    """A real, disclosed, SIMPLER PROXY for a symbol's trend regime at a
    given historical bar — real EMA slope over `slope_lookback` real
    bars, `slope_threshold_pct` a real, disclosed research threshold for
    what counts as "trending" vs. "ranging." Extracted from app/
    ema_pullback_research.py's original hand-built version (CEO
    directive "Market-Analysis Knowledge + Session Intelligence
    Expansion," Phase 15) so every caller needing this same real proxy
    shares one implementation — see that module's own module docstring
    for the full ARCHITECTURALLY BLOCKED reasoning this proxy exists to
    honestly stand in for (the live 13-way `MarketIntelligenceRegime`
    classifier needs cross-symbol state no historical replay has access
    to)."""
    now = ema_at(ema_series_values, ema_period, index - 1)
    then = ema_at(ema_series_values, ema_period, index - 1 - slope_lookback)
    if now is None or then is None or then == 0:
        return "ranging"
    pct_change = (now - then) / abs(then) * 100
    if pct_change > slope_threshold_pct:
        return "trending_up"
    if pct_change < -slope_threshold_pct:
        return "trending_down"
    return "ranging"


def regime_volatility_at(atr_series_values: list[float], atr_period: int, index: int, *, median_lookback: int, high_ratio: float, low_ratio: float) -> EmaPullbackRegimeVolatility:
    """The volatility half of the same real, disclosed proxy — current
    real ATR vs. its own trailing real median over `median_lookback`
    bars. See `regime_trend_at()`'s own docstring for the full
    provenance and disclosed-proxy reasoning."""
    now = atr_at(atr_series_values, atr_period, index - 1)
    if now is None:
        return "normal"
    k = (index - 1) - atr_period
    window = atr_series_values[max(0, k - median_lookback + 1) : k + 1]
    if len(window) < 5:
        return "normal"
    baseline = median(window)
    if baseline <= 0:
        return "normal"
    ratio = now / baseline
    if ratio >= high_ratio:
        return "high"
    if ratio <= low_ratio:
        return "low"
    return "normal"


def breakout_candle_range_ratio(candles: list[Candle], confirmation_index: int, *, recent_range_lookback: int) -> float:
    """The real breakout confirmation candle's own range vs. the real
    average range of the `recent_range_lookback` bars immediately before
    it — a real, disclosed TAGGING-only measurement (per the CEO
    directive "Market-Analysis Knowledge + Session Intelligence
    Expansion," Phase 15's own explicit warning against hardcoding
    "3x or 4x" as universally invalid): never used to filter or
    invalidate a trade by itself. `1.0` (neutral) when there isn't
    enough real history yet to compute a real average."""
    window_start = max(0, confirmation_index - recent_range_lookback)
    window = candles[window_start:confirmation_index]
    if not window:
        return 1.0
    avg_range = sum(c.high - c.low for c in window) / len(window)
    if avg_range <= 0:
        return 1.0
    breakout_range = candles[confirmation_index].high - candles[confirmation_index].low
    return round(breakout_range / avg_range, 3)


def chandelier_stop(candles: list[Candle], atr_series_values: list[float], entry_index: int, direction: str, *, atr_period: int, atr_multiplier: float) -> float | None:
    """The real, standard Chuck LeBeau Chandelier Stop formula:
    `highest_high(atr_period bars before entry) - atr_multiplier *
    ATR(same window)` for a long (mirrored for a short). `None` (never a
    fabricated stop) when there isn't enough real ATR history yet at
    `entry_index`."""
    atr_value = atr_at(atr_series_values, atr_period, entry_index - 1)
    if atr_value is None:
        return None
    window = candles[max(0, entry_index - atr_period) : entry_index]
    if not window:
        return None
    if direction == "long":
        return round(max(c.high for c in window) - atr_multiplier * atr_value, 4)
    return round(min(c.low for c in window) + atr_multiplier * atr_value, 4)


@dataclass
class ExitResult:
    outcome: EmaPullbackTradeOutcome
    exit_price: float | None
    r_multiple_realized: float
    mae_r: float
    mfe_r: float


def simulate_exit(direction: str, entry_price: float, stop_price: float, target_price: float, path: list[Candle]) -> ExitResult:
    """A real forward walk of `path` (already bounded by the caller's
    own max-hold-bars policy): the stop and the target are each checked
    against every real bar's high/low. A bar that touches both is
    conservatively scored as the stop, never the more favorable outcome
    — the standard, disclosed conservative backtesting convention. A
    trade that touches neither anywhere in `path` reads `"open"` and is
    never fabricated into a forced win or loss."""
    risk = abs(entry_price - stop_price)
    if risk <= 0:
        return ExitResult(outcome="open", exit_price=None, r_multiple_realized=0.0, mae_r=0.0, mfe_r=0.0)
    mae = 0.0
    mfe = 0.0
    for bar in path:
        adverse = (entry_price - bar.low) if direction == "long" else (bar.high - entry_price)
        favorable = (bar.high - entry_price) if direction == "long" else (entry_price - bar.low)
        mae = max(mae, adverse)
        mfe = max(mfe, favorable)
        stop_hit = bar.low <= stop_price if direction == "long" else bar.high >= stop_price
        target_hit = bar.high >= target_price if direction == "long" else bar.low <= target_price
        if stop_hit:
            return ExitResult(outcome="loss", exit_price=stop_price, r_multiple_realized=-1.0, mae_r=round(mae / risk, 3), mfe_r=round(mfe / risk, 3))
        if target_hit:
            r = (target_price - entry_price) / risk if direction == "long" else (entry_price - target_price) / risk
            return ExitResult(outcome="win", exit_price=target_price, r_multiple_realized=round(r, 3), mae_r=round(mae / risk, 3), mfe_r=round(mfe / risk, 3))
    return ExitResult(outcome="open", exit_price=None, r_multiple_realized=0.0, mae_r=round(mae / risk, 3), mfe_r=round(mfe / risk, 3))


def aggregate_bucket(label: str, trades: list[EmaPullbackTradeRecord], *, min_trades_for_verdict: int = DEFAULT_MIN_TRADES_FOR_BUCKET_VERDICT) -> EmaPullbackStatsBucket:
    """The one real, honest aggregation of a bucket of real trade
    records into win rate / expectancy / profit factor / max drawdown /
    longest losing streak — every field `None` (never a fabricated
    value) when there are zero real closed trades in the bucket, and
    `verdict` honestly `"not_enough_evidence"` below `min_trades_for_
    verdict` rather than a forced call either way."""
    closed = [t for t in trades if t.outcome != "open"]
    wins = [t for t in closed if t.outcome == "win"]
    losses = [t for t in closed if t.outcome == "loss"]
    open_trades = [t for t in trades if t.outcome == "open"]
    trade_count = len(trades)
    if not closed:
        return EmaPullbackStatsBucket(
            label=label,
            tradeCount=trade_count,
            winCount=0,
            lossCount=0,
            openCount=len(open_trades),
            detail=f"No real closed trades in this bucket ({trade_count} total, {len(open_trades)} still open at the end of the tested history).",
        )
    win_rate_pct = round(len(wins) / len(closed) * 100, 1)
    avg_win_r = round(sum(t.r_multiple_realized for t in wins) / len(wins), 3) if wins else 0.0
    avg_loss_r = round(sum(abs(t.r_multiple_realized) for t in losses) / len(losses), 3) if losses else 0.0
    expectancy_r = round((len(wins) / len(closed)) * avg_win_r - (len(losses) / len(closed)) * avg_loss_r, 3)
    gross_win = sum(t.r_multiple_realized for t in wins)
    gross_loss = sum(abs(t.r_multiple_realized) for t in losses)
    profit_factor = round(gross_win / gross_loss, 3) if gross_loss > 0 else (round(gross_win, 3) if gross_win > 0 else 0.0)

    cumulative = 0.0
    peak = 0.0
    max_drawdown = 0.0
    longest_streak = 0
    current_streak = 0
    for t in sorted(closed, key=lambda x: x.entry_timestamp):
        cumulative += t.r_multiple_realized
        peak = max(peak, cumulative)
        max_drawdown = min(max_drawdown, cumulative - peak)
        if t.outcome == "loss":
            current_streak += 1
            longest_streak = max(longest_streak, current_streak)
        else:
            current_streak = 0

    verdict: str | None = "enough_evidence" if len(closed) >= min_trades_for_verdict else "not_enough_evidence"
    detail = (
        f"{len(closed)} real closed trade(s) ({len(wins)} win, {len(losses)} loss, {len(open_trades)} still open) — "
        f"win rate {win_rate_pct}%, expectancy {expectancy_r:+.2f}R."
    )
    if verdict == "not_enough_evidence":
        detail += f" Below the {min_trades_for_verdict}-trade bar this module uses for a bucket-level read — treat as a preliminary signal only."

    return EmaPullbackStatsBucket(
        label=label,
        tradeCount=trade_count,
        winCount=len(wins),
        lossCount=len(losses),
        openCount=len(open_trades),
        winRatePct=win_rate_pct,
        avgWinR=avg_win_r,
        avgLossR=avg_loss_r,
        expectancyR=expectancy_r,
        profitFactor=profit_factor,
        maxDrawdownR=round(abs(max_drawdown), 3),
        longestLosingStreak=longest_streak,
        verdict=verdict,  # type: ignore[arg-type]
        detail=detail,
    )
