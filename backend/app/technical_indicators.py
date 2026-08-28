"""CEO directive "Professional Trading Firm — Market-Analysis Knowledge
+ Session Intelligence Expansion," Phase 3 — real technical indicator
computation.

RESEARCH FIRST (per the directive's own mandatory rule): a full grep
audit of this codebase found zero existing RSI/MACD/Stochastic/moving-
average/VWAP/ATR computation anywhere — `app/confidence.py`'s own
module docstring already discloses that "support & resistance levels,
liquidity quality" (and, at the time this module was written,
multi-timeframe agreement — since closed, see CEO directive
"Professional Quant Trading Core," Phase B and app/multi_timeframe.py)
were deliberately left out of the Decision Confidence Engine as
unbuildable without fabricating numbers; the same honesty boundary
applies here. This module closes exactly the "no real technical-
indicator library exists" gap — nothing more.

WHAT'S REAL: every function below is a standard, textbook formula
applied directly to real `app/market_data.py` `Candle` data (the same
real mock OHLCV series `app/market_intelligence.py`'s
`compute_market_structure()`/`compute_liquidity()` already read from).
No indicator here predicts a future price or trade outcome — each one
describes a real, checkable property of the candle series it was
computed from, exactly the same "process, not outcome" boundary
`app/confidence.py`'s own docstring already establishes.

CEO directive "Professional Quant Trading Firm — Quant Intelligence +
Market Analysis Completion Phase (Next Research + Validation Pass)":
Parabolic SAR and SuperTrend, deliberately left out above, are now
implemented below with the same rigor as every other indicator in this
module — standard, textbook iterative formulas (SAR's real acceleration-
factor recurrence; SuperTrend's real ATR-banded trend-flip logic), both
deterministic and reproducible from the same real candle series. Neither
is treated as a standalone trading signal here — see each function's own
docstring, and app/evidence_confluence.py's own docstring for why both
join the existing `trend` evidence family rather than becoming a new one
(they are trend-following/trailing-stop indicators highly correlated
with the EMA/SMA trend reads already in that family — counting them as
independent evidence would be exactly the double-counting this same
directive's own confluence rules forbid).

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


def sma_series(candles: list[Candle], period: int) -> list[float]:
    """The real, full SMA series (one value per candle from the point a
    real `period`-bar window exists onward) — `sma()` above returns just
    its last value. Same index alignment as `ema_series()` below
    (`sma_series(candles, period)[0]` is the real SMA "as of" candle
    index `period - 1`) since both are windowed averages seeded from the
    same first `period` closes."""
    if period < 1 or len(candles) < period:
        return []
    closes = [c.close for c in candles]
    return [round(sum(closes[i - period + 1 : i + 1]) / period, 4) for i in range(period - 1, len(closes))]


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


def rsi_series(candles: list[Candle], period: int = 14) -> list[float]:
    """The real, full RSI series (one value per candle from the point a
    real `period`-bar Wilder-smoothed window exists onward) — `rsi()`
    above returns just its last value. Same index alignment as
    `atr_series()` (`rsi_series(candles, period)[0]` is the real RSI "as
    of" candle index `period`, one bar later than `ema_series()`'s own
    seed point, since RSI's first real gain/loss needs one prior close
    the same way ATR's first true range does) — `app/backtest_
    primitives.py`'s `atr_at()` is reused directly to look this series
    up at an arbitrary historical index, never a second lookup formula.
    `rsi_series(candles, period)[-1] == rsi(candles, period)` for the
    same inputs — same real Wilder-smoothing formula, computed at every
    window instead of only the last."""
    if len(candles) < period + 1:
        return []
    closes = [c.close for c in candles]
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(0.0, d) for d in deltas]
    losses = [max(0.0, -d) for d in deltas]
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    def _rsi_value(avg_gain: float, avg_loss: float) -> float:
        if avg_gain == 0 and avg_loss == 0:
            return 50.0
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return round(100.0 - (100.0 / (1.0 + rs)), 2)

    series = [_rsi_value(avg_gain, avg_loss)]
    for gain, loss in zip(gains[period:], losses[period:]):
        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period
        series.append(_rsi_value(avg_gain, avg_loss))
    return series


def macd_series(candles: list[Candle], fast: int = 12, slow: int = 26, signal: int = 9) -> list[tuple[float, float, float]]:
    """The real, full MACD series (one `(macd_line, signal_line,
    histogram)` triple per candle from the point a real signal-line
    window exists onward) — `macd()` below returns just its last triple.
    Uses the exact same real `ema_series()` alignment `macd()` already
    relies on, computed at every historical window instead of only the
    latest. `macd_series(candles, ...)[-1] == macd(candles, ...)` for
    the same inputs."""
    if len(candles) < slow + signal:
        return []
    fast_series = ema_series(candles, fast)
    slow_series = ema_series(candles, slow)
    offset = len(fast_series) - len(slow_series)
    if offset < 0:
        return []
    aligned_fast = fast_series[offset:]
    macd_line_series = [f - s for f, s in zip(aligned_fast, slow_series)]
    if len(macd_line_series) < signal:
        return []
    seed = sum(macd_line_series[:signal]) / signal
    multiplier = 2.0 / (signal + 1)
    signal_series = [seed]
    for value in macd_line_series[signal:]:
        signal_series.append((value - signal_series[-1]) * multiplier + signal_series[-1])
    return [(round(macd_line_series[k + signal - 1], 4), round(sig, 4), round(macd_line_series[k + signal - 1] - sig, 4)) for k, sig in enumerate(signal_series)]


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


def stochastic_series(candles: list[Candle], period: int = 14, smoothing: int = 3) -> list[tuple[float, float]]:
    """The real, full Stochastic series (one `(percent_k, percent_d)`
    pair per candle from the point a real smoothed window exists onward)
    — `stochastic()` above returns just its last pair. Same real
    high-low-range-position formula, computed at every historical window
    instead of only the latest.
    `stochastic_series(candles, ...)[-1] == stochastic(candles, ...)`
    for the same inputs."""
    if len(candles) < period + smoothing - 1:
        return []
    k_values: list[float] = []
    for i in range(period - 1, len(candles)):
        window = candles[i - period + 1 : i + 1]
        highest = max(c.high for c in window)
        lowest = min(c.low for c in window)
        close = candles[i].close
        k = 50.0 if highest == lowest else (close - lowest) / (highest - lowest) * 100.0
        k_values.append(k)
    if len(k_values) < smoothing:
        return []
    return [(round(k_values[i], 2), round(sum(k_values[i - smoothing + 1 : i + 1]) / smoothing, 2)) for i in range(smoothing - 1, len(k_values))]


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


def atr_series(candles: list[Candle], period: int = 14) -> list[float]:
    """The real, full ATR series (one value per candle from the point a
    real `period`-bar true-range window exists onward) — `atr()` above
    returns just its last value; a real backtest that needs a volatility
    read AT EVERY historical bar (e.g. a Chandelier Stop, computed at
    each real trade's own entry bar, never with knowledge of bars after
    it) needs the series itself. `atr_series(candles, period)[-1] ==
    atr(candles, period)` for the same inputs — same real formula, just
    computed at every window instead of only the last one."""
    if len(candles) < period + 1:
        return []
    true_ranges: list[float] = []
    for i in range(1, len(candles)):
        high, low, prev_close = candles[i].high, candles[i].low, candles[i - 1].close
        true_ranges.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))
    return [round(sum(true_ranges[i - period : i]) / period, 4) for i in range(period, len(true_ranges) + 1)]


def parabolic_sar_series(candles: list[Candle], *, af_start: float = 0.02, af_step: float = 0.02, af_max: float = 0.2) -> list[tuple[float, str]]:
    """The real, full Parabolic SAR series — Wellesley Wilder's standard
    iterative recurrence, one `(sar_value, trend)` pair per candle from
    index 1 onward (index 0 has no prior bar to seed a starting trend
    from). `trend` is `"up"` while price trades above its own real SAR
    dot, `"down"` while below — never a third state, since SAR is always
    on one side of price by construction.

    The real recurrence: `sar[i] = sar[i-1] + af * (ep - sar[i-1])`,
    where `ep` (extreme point) is the highest high (uptrend) or lowest
    low (downtrend) reached so far in the CURRENT trend leg, and `af`
    (acceleration factor) starts at `af_start`, increases by `af_step`
    every time a new real extreme point is made, capped at `af_max` —
    all three real, standard, disclosed defaults (0.02/0.02/0.2), never
    TradeTown-fitted. The real "SAR cannot penetrate the last two real
    bars' own range" clamp is enforced every bar (an uptrend's SAR is
    capped at the lower of the last two real lows; a downtrend's SAR is
    floored at the higher of the last two real highs) — the standard
    real safeguard against SAR jumping inside price action it hasn't
    actually reached yet. A real close beyond the current SAR dot flips
    the trend: the new SAR becomes the old extreme point, AF resets to
    `af_start`, and a fresh extreme point starts accumulating from the
    flip bar's own real high/low — never carrying stale state across the
    flip."""
    if len(candles) < 2:
        return []
    trend = "up" if candles[1].close >= candles[0].close else "down"
    ep = candles[0].high if trend == "up" else candles[0].low
    sar = candles[0].low if trend == "up" else candles[0].high
    af = af_start
    series: list[tuple[float, str]] = []
    for i in range(1, len(candles)):
        cur = candles[i]
        prev_two = candles[max(0, i - 2) : i]
        next_sar = sar + af * (ep - sar)
        if trend == "up":
            if prev_two:
                next_sar = min(next_sar, *(c.low for c in prev_two))
            if cur.low < next_sar:
                trend = "down"
                next_sar = ep
                ep = cur.low
                af = af_start
            elif cur.high > ep:
                ep = cur.high
                af = min(af + af_step, af_max)
        else:
            if prev_two:
                next_sar = max(next_sar, *(c.high for c in prev_two))
            if cur.high > next_sar:
                trend = "up"
                next_sar = ep
                ep = cur.high
                af = af_start
            elif cur.low < ep:
                ep = cur.low
                af = min(af + af_step, af_max)
        sar = next_sar
        series.append((round(sar, 4), trend))
    return series


def parabolic_sar(candles: list[Candle], *, af_start: float = 0.02, af_step: float = 0.02, af_max: float = 0.2) -> tuple[float, str] | None:
    """The latest real `(sar_value, trend)` pair — see
    `parabolic_sar_series()` for the full real recurrence."""
    series = parabolic_sar_series(candles, af_start=af_start, af_step=af_step, af_max=af_max)
    return series[-1] if series else None


def supertrend_series(candles: list[Candle], *, period: int = 10, multiplier: float = 3.0) -> list[tuple[float, str]]:
    """The real, full SuperTrend series — one `(supertrend_value, trend)`
    pair per candle from the point a real `period`-bar ATR window exists
    onward. The real, standard band recurrence: `basic_upper[i] =
    (high[i]+low[i])/2 + multiplier * ATR[i]` (mirrored for
    `basic_lower`), then each band only ever tightens toward price — a
    real `final_upper[i]` only drops below `final_upper[i-1]` when the
    real basic upper band itself is lower OR the prior real close already
    broke above it (never loosens back away from price once tightened,
    the standard real SuperTrend "sticky band" rule, mirrored for
    `final_lower`). The real trend flips exactly when a real close
    crosses the currently-active band; the line itself is always
    `final_lower` while up-trending, `final_upper` while down-trending.
    `period`/`multiplier` (10/3.0) are the methodology's own commonly-
    published defaults, not TradeTown-fitted numbers."""
    atr_values = atr_series(candles, period)
    if not atr_values:
        return []
    offset = len(candles) - len(atr_values)
    final_upper = 0.0
    final_lower = 0.0
    trend = "up"
    series: list[tuple[float, str]] = []
    for k, atr_value in enumerate(atr_values):
        i = k + offset
        cur = candles[i]
        mid = (cur.high + cur.low) / 2.0
        basic_upper = mid + multiplier * atr_value
        basic_lower = mid - multiplier * atr_value
        if k == 0:
            final_upper = basic_upper
            final_lower = basic_lower
            trend = "up" if cur.close >= final_lower else "down"
        else:
            prev_close = candles[i - 1].close
            final_upper = basic_upper if (basic_upper < final_upper or prev_close > final_upper) else final_upper
            final_lower = basic_lower if (basic_lower > final_lower or prev_close < final_lower) else final_lower
            if trend == "up":
                if cur.close < final_lower:
                    trend = "down"
            else:
                if cur.close > final_upper:
                    trend = "up"
        line = final_lower if trend == "up" else final_upper
        series.append((round(line, 4), trend))
    return series


def supertrend(candles: list[Candle], *, period: int = 10, multiplier: float = 3.0) -> tuple[float, str] | None:
    """The latest real `(supertrend_value, trend)` pair — see
    `supertrend_series()` for the full real recurrence."""
    series = supertrend_series(candles, period=period, multiplier=multiplier)
    return series[-1] if series else None


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
