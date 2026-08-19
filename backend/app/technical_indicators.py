"""CEO directive "Professional Trading Firm — Market-Analysis Knowledge
+ Session Intelligence Expansion," Phase 3 — real technical indicator
computation.

RESEARCH FIRST (per the directive's own mandatory rule): a full grep
audit of this codebase found zero existing RSI/MACD/Stochastic/moving-
average/VWAP/ATR computation anywhere — `app/confidence.py`'s own
module docstring already discloses that "support & resistance levels,
multi-timeframe agreement... liquidity quality" were deliberately left
out of the Decision Confidence Engine as unbuildable without fabricating
numbers; the same honesty boundary applies here. This module closes
exactly the "no real technical-indicator library exists" gap — nothing
more.

WHAT'S REAL: every function below is a standard, textbook formula
applied directly to real `app/market_data.py` `Candle` data (the same
real mock OHLCV series `app/market_intelligence.py`'s
`compute_market_structure()`/`compute_liquidity()` already read from).
No indicator here predicts a future price or trade outcome — each one
describes a real, checkable property of the candle series it was
computed from, exactly the same "process, not outcome" boundary
`app/confidence.py`'s own docstring already establishes.

WHAT'S DELIBERATELY NOT HERE: Parabolic SAR and SuperTrend (both real,
named, well-known indicators) are NOT computed here — both are more
implementation-sensitive than the others (SAR's iterative acceleration-
factor recurrence, SuperTrend's ATR-banded trend-flip logic), and adding
them without equal rigor to what's below would be exactly the "indicator
soup, added because the list asked for it" anti-pattern this same
directive explicitly warns against (see app/model_validation.py's new
anti-overfitting checks). Documented as real, named, un-implemented
research candidates in the Design Bible rather than half-built here.

WHAT THIS MODULE DOES NOT DO: none of these values are wired into
`app/research.py`'s confidence gauge, `app/confidence.py`'s Decision
Confidence Engine, or any live trade decision. Per this directive's own
Phase 7 ("only then determine whether the concept deserves inclusion in
a strategy"), a new technical concept earns a place in a real decision
only after the hypothesis-testing pipeline that would validate it exists
— that pipeline does not exist in this codebase yet (see
docs/Architecture.md's Phase 5-7 scoping). These are real, computed,
inspectable evidence values only, the same "real signal, not yet wired
into a decision" boundary `app/market_intelligence.py`'s own
`LiquidityRead`/`MarketStructureRead` already established before Feature
51 wired parts of them into department opinions.
"""
from __future__ import annotations

from app.market_data import Candle

MIN_CANDLES_FOR_INDICATORS = 2


def sma(candles: list[Candle], period: int) -> float | None:
    """Simple Moving Average of the last `period` closes. `None` (never
    a value computed from fewer bars than requested) when there isn't
    enough real history yet."""
    if period < 1 or len(candles) < period:
        return None
    window = candles[-period:]
    return round(sum(c.close for c in window) / period, 4)


def ema_series(candles: list[Candle], period: int) -> list[float]:
    """The real, full EMA series (one value per candle from the point a
    real seed average exists onward) — `ema()` below returns just its
    last value; the series itself is what divergence detection needs to
    compare against price's own swing points."""
    if period < 1 or len(candles) < period:
        return []
    closes = [c.close for c in candles]
    seed = sum(closes[:period]) / period
    multiplier = 2.0 / (period + 1)
    series = [seed]
    for close in closes[period:]:
        series.append((close - series[-1]) * multiplier + series[-1])
    return series


def ema(candles: list[Candle], period: int) -> float | None:
    """Exponential Moving Average — weights recent closes more heavily
    than `sma()`, the real, standard reason a trend-follower reaches for
    EMA over SMA. Seeded from a real SMA of the first `period` closes,
    the same standard convention every real EMA implementation uses."""
    series = ema_series(candles, period)
    return round(series[-1], 4) if series else None


def rsi(candles: list[Candle], period: int = 14) -> float | None:
    """Relative Strength Index — a real, bounded [0, 100] momentum
    oscillator: the ratio of average gains to average losses over
    `period` real bars, standard Wilder smoothing. Reads >70 as
    conventionally "overbought," <30 as "overextended sold off" — real,
    named conventions this function does not itself assert as
    predictive; see the Academy lesson this function backs for that
    honesty boundary."""
    if len(candles) < period + 1:
        return None
    closes = [c.close for c in candles]
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(0.0, d) for d in deltas]
    losses = [max(0.0, -d) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for gain, loss in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
    if avg_gain == 0 and avg_loss == 0:
        # A genuinely flat real series (no price movement at all) --
        # RS is undefined (0/0), and the real, standard convention reads
        # this as neutral, not overbought.
        return 50.0
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return round(100.0 - (100.0 / (1.0 + rs)), 2)


def macd(candles: list[Candle], fast: int = 12, slow: int = 26, signal: int = 9) -> tuple[float, float, float] | None:
    """Moving Average Convergence/Divergence — returns (macd_line,
    signal_line, histogram), the three real, standard MACD outputs.
    `macd_line` is the fast EMA minus the slow EMA (a real trend/momentum
    blend); `signal_line` is an EMA of `macd_line` itself; `histogram` is
    their real difference, the conventional "momentum accelerating vs.
    decelerating" read. `None` below the real minimum bar count all
    three EMAs need."""
    if len(candles) < slow + signal:
        return None
    fast_series = ema_series(candles, fast)
    slow_series = ema_series(candles, slow)
    # Align both series to their shared, real overlapping window — the
    # slow series starts later (needs more seed bars), so only the tail
    # the fast series also covers is comparable.
    offset = len(fast_series) - len(slow_series)
    if offset < 0:
        return None
    aligned_fast = fast_series[offset:]
    macd_line_series = [f - s for f, s in zip(aligned_fast, slow_series)]
    if len(macd_line_series) < signal:
        return None
    seed = sum(macd_line_series[:signal]) / signal
    multiplier = 2.0 / (signal + 1)
    signal_series = [seed]
    for value in macd_line_series[signal:]:
        signal_series.append((value - signal_series[-1]) * multiplier + signal_series[-1])
    macd_value = macd_line_series[-1]
    signal_value = signal_series[-1]
    return round(macd_value, 4), round(signal_value, 4), round(macd_value - signal_value, 4)


def stochastic(candles: list[Candle], period: int = 14, smoothing: int = 3) -> tuple[float, float] | None:
    """Stochastic Oscillator — returns (percent_k, percent_d), both real,
    bounded [0, 100] reads of where the latest close sits within the
    real high-low range of the last `period` bars. `percent_d` is a real
    `smoothing`-period SMA of `percent_k`, the conventional signal line."""
    if len(candles) < period + smoothing - 1:
        return None
    k_values: list[float] = []
    for i in range(period - 1, len(candles)):
        window = candles[i - period + 1 : i + 1]
        highest = max(c.high for c in window)
        lowest = min(c.low for c in window)
        close = candles[i].close
        k = 50.0 if highest == lowest else (close - lowest) / (highest - lowest) * 100.0
        k_values.append(k)
    if len(k_values) < smoothing:
        return None
    percent_k = k_values[-1]
    percent_d = sum(k_values[-smoothing:]) / smoothing
    return round(percent_k, 2), round(percent_d, 2)


def atr(candles: list[Candle], period: int = 14) -> float | None:
    """Average True Range — a real, standard volatility magnitude read
    (the real average of each bar's true range: the largest of
    high-low, |high-prev_close|, |low-prev_close|). Not directional —
    never says which way price is likely to move, only how much it has
    real recently been moving, the same honest boundary
    `app/market_intelligence.py`'s `VolatilityRead` already keeps for its
    own, differently-computed volatility read."""
    if len(candles) < period + 1:
        return None
    true_ranges: list[float] = []
    for i in range(1, len(candles)):
        high, low, prev_close = candles[i].high, candles[i].low, candles[i - 1].close
        true_ranges.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    window = true_ranges[-period:]
    return round(sum(window) / period, 4)


def vwap(candles: list[Candle]) -> float | None:
    """Volume-Weighted Average Price over the full real candle window
    supplied — the real, standard typical-price-times-volume sum divided
    by total real volume. Institutional/intraday traders read VWAP as a
    real fair-value reference for the session; this function computes it
    over whatever window is passed in (a caller wanting a session-scoped
    VWAP passes only that session's real candles — see
    app/technical_patterns.py's session-range functions for how that
    window gets selected)."""
    if not candles:
        return None
    total_volume = sum(c.volume for c in candles)
    if total_volume <= 0:
        return None
    typical_price_volume = sum((c.high + c.low + c.close) / 3.0 * c.volume for c in candles)
    return round(typical_price_volume / total_volume, 4)
