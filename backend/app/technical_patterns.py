"""CEO directive "Professional Trading Firm — Market-Analysis Knowledge
+ Session Intelligence Expansion," Phases 1-2 — real pattern detection
extending, never duplicating, `app/market_intelligence.py`'s existing
real swing-structure/session engine.

RESEARCH FIRST (per the directive's own mandatory rule): `app/
market_intelligence.py` already has real local-extrema swing detection
(`_find_swings()`) and a real Break of Structure read
(`compute_market_structure()`), and a real session-boundary function
(`_session_for_hour()`, backing `compute_session()`). This module
imports and reuses both directly rather than re-implementing swing or
session detection a second time — every function below is either new
(Fair Value Gaps, candlestick patterns, session-range/retest tracking,
Fibonacci levels, the order-block proxy) or a thin, additive label on
top of the existing real swing sequence (HH/HL/LH/LL).

WHAT'S REAL: every pattern below is a standard, named, geometrically-
checkable definition applied directly to real (mock) `Candle` data.
Naming a pattern is never a claim about what happens next — see each
function's own docstring for its exact real definition and this
module's own `_DISCLOSED_PROXY_NOTE` for the one genuinely ambiguous
concept (order blocks) this module takes a disclosed, named stance on.

WHAT THIS MODULE DOES NOT DO: none of these reads are wired into
`app/research.py`'s confidence gauge or any live trade decision — see
`app/technical_indicators.py`'s own module docstring for the identical
reasoning (no hypothesis-testing pipeline exists yet to validate a new
concept's inclusion in a real decision, per this directive's own Phase
7). These are real, computed, inspectable evidence values only.
"""
from __future__ import annotations

from datetime import datetime

from app.market_data import Candle
from app.market_intelligence import SWING_LOOKBACK, _find_swings, _session_for_hour, compute_market_structure
from app.schemas import (
    CandlestickPattern,
    CandlestickPatternRead,
    FairValueGap,
    FairValueGapRead,
    FibonacciLevel,
    FibonacciRead,
    OrderBlockRead,
    SessionRangeRead,
    SwingStructureLabel,
    SwingStructureRead,
    TradingSession,
)

# Standard, named Fibonacci retracement ratios — real, well-known
# numbers, never asserted here as reliably reactive (see FibonacciRead's
# own schema docstring and the Academy lesson backing this function).
FIBONACCI_RETRACEMENT_RATIOS: tuple[float, ...] = (0.236, 0.382, 0.5, 0.618, 0.786)
FIBONACCI_EXTENSION_RATIOS: tuple[float, ...] = (1.272, 1.618)

_DISCLOSED_PROXY_NOTE = (
    "One specific, named, checkable definition of a real order block used here: the last opposite-direction "
    "candle immediately before a real Break of Structure. Professional usage of this term varies — this is not a "
    "claim of institutional order-flow data this codebase does not have."
)


def label_swing_structure(symbol: str, candles: list[Candle]) -> SwingStructureRead:
    """Chronologically merges the real swing highs/lows `_find_swings()`
    already detects into the classic HH/HL/LH/LL sequence — each label
    is real relative to its own immediately preceding same-type swing."""
    if len(candles) < SWING_LOOKBACK * 2 + 2:
        return SwingStructureRead(symbol=symbol, labels=[], detail="Not enough real candle history yet to label swing structure.")
    highs_idx, lows_idx = _find_swings(candles)
    tagged: list[tuple[int, str, float]] = [(i, "high", p) for i, p in highs_idx] + [(i, "low", p) for i, p in lows_idx]
    tagged.sort(key=lambda t: t[0])

    labels: list[SwingStructureLabel] = []
    last_high: float | None = None
    last_low: float | None = None
    for _, kind, price in tagged:
        if kind == "high":
            if last_high is not None:
                labels.append("higher_high" if price > last_high else "lower_high")
            last_high = price
        else:
            if last_low is not None:
                labels.append("higher_low" if price > last_low else "lower_low")
            last_low = price

    detail = f"{len(labels)} real labeled transition(s) over {len(highs_idx)} swing high(s)/{len(lows_idx)} swing low(s)." if labels else "Not enough consecutive same-type swings yet to label a real transition."
    return SwingStructureRead(symbol=symbol, labels=labels, detail=detail)


def detect_fair_value_gaps(symbol: str, candles: list[Candle]) -> FairValueGapRead:
    """A real, standard 3-candle Fair Value Gap: candle[i-2].high below
    candle[i].low (bullish — price displaced up through this zone
    without a full real trade there) or the mirror bearish case.
    `filled` is real: checked against every later candle's own real
    high/low."""
    if len(candles) < 3:
        return FairValueGapRead(symbol=symbol, gaps=[], detail="Not enough real candle history yet to detect a Fair Value Gap.")
    gaps: list[FairValueGap] = []
    for i in range(2, len(candles)):
        first, middle, third = candles[i - 2], candles[i - 1], candles[i]
        if first.high < third.low:
            gap_low, gap_high = first.high, third.low
            filled = any(c.low <= gap_low for c in candles[i + 1 :])
            gaps.append(FairValueGap(direction="bullish", gapHigh=round(gap_high, 4), gapLow=round(gap_low, 4), timestamp=middle.timestamp, filled=filled))
        elif first.low > third.high:
            gap_low, gap_high = third.high, first.low
            filled = any(c.high >= gap_high for c in candles[i + 1 :])
            gaps.append(FairValueGap(direction="bearish", gapHigh=round(gap_high, 4), gapLow=round(gap_low, 4), timestamp=middle.timestamp, filled=filled))
    detail = f"{len(gaps)} real Fair Value Gap(s) over {len(candles)} candles ({sum(1 for g in gaps if not g.filled)} still unfilled)."
    return FairValueGapRead(symbol=symbol, gaps=gaps[-10:], detail=detail)


def _body(c: Candle) -> float:
    return abs(c.close - c.open)


def _range(c: Candle) -> float:
    return c.high - c.low


def detect_candlestick_patterns(symbol: str, candles: list[Candle]) -> CandlestickPatternRead:
    """Four real, standard, purely geometric candlestick definitions —
    see each check's own comment for the exact real rule. Never a claim
    about what happens next; see CandlestickPatternRead's own schema
    docstring."""
    if len(candles) < 2:
        return CandlestickPatternRead(symbol=symbol, patterns=[], detail="Not enough real candle history yet to detect a candlestick pattern.")
    patterns: list[CandlestickPattern] = []
    for i in range(1, len(candles)):
        prev, cur = candles[i - 1], candles[i]
        # Engulfing: the real body of `cur` fully contains the real body
        # of `prev`, opposite direction.
        prev_bullish, cur_bullish = prev.close > prev.open, cur.close > cur.open
        if cur_bullish and not prev_bullish and cur.close >= prev.open and cur.open <= prev.close and _body(cur) > 0:
            patterns.append(CandlestickPattern(pattern="bullish_engulfing", timestamp=cur.timestamp, detail=f"{symbol} real bullish body fully covers the prior real bearish body."))
        elif not cur_bullish and prev_bullish and cur.open >= prev.close and cur.close <= prev.open and _body(cur) > 0:
            patterns.append(CandlestickPattern(pattern="bearish_engulfing", timestamp=cur.timestamp, detail=f"{symbol} real bearish body fully covers the prior real bullish body."))

        rng = _range(cur)
        if rng <= 0:
            continue
        body = _body(cur)
        upper_wick = cur.high - max(cur.open, cur.close)
        lower_wick = min(cur.open, cur.close) - cur.low
        # Hammer/shooting star are checked first: both require a real,
        # LOPSIDED wick (one side dominant, the other short) regardless
        # of how small the body is relative to the full range -- a real
        # hammer's defining trait is exactly a tiny body with a long
        # wick, which would otherwise also satisfy doji's own looser
        # "small body" check below. Doji instead requires roughly
        # balanced (or absent) wicks on both sides.
        if lower_wick >= body * 2 and upper_wick <= body * 0.5:
            patterns.append(CandlestickPattern(pattern="hammer", timestamp=cur.timestamp, detail=f"{symbol} real lower wick is {lower_wick / max(body, 0.0001):.1f}x the real body."))
        elif upper_wick >= body * 2 and lower_wick <= body * 0.5:
            patterns.append(CandlestickPattern(pattern="shooting_star", timestamp=cur.timestamp, detail=f"{symbol} real upper wick is {upper_wick / max(body, 0.0001):.1f}x the real body."))
        # Doji: real body under 10% of the real full range -- open and
        # close land almost exactly together.
        elif body / rng < 0.1:
            patterns.append(CandlestickPattern(pattern="doji", timestamp=cur.timestamp, detail=f"{symbol} real body is {body / rng * 100:.0f}% of its own real range."))

    detail = f"{len(patterns)} real candlestick pattern(s) detected over {len(candles)} candles."
    return CandlestickPatternRead(symbol=symbol, patterns=patterns[-10:], detail=detail)


def compute_session_range(symbol: str, candles: list[Candle], session: TradingSession) -> SessionRangeRead:
    """This session's own real high/low, from the real candles whose own
    real timestamp falls inside `session`'s real UTC window (reused
    `_session_for_hour()` boundaries) — and whether any later candle
    (outside that window) has already traded back into that range."""
    session_candles: list[Candle] = []
    other_candles: list[Candle] = []
    for c in candles:
        ts = datetime.fromisoformat(c.timestamp)
        hour = ts.hour + ts.minute / 60.0
        (session_candles if _session_for_hour(hour) == session else other_candles).append(c)

    if not session_candles:
        return SessionRangeRead(symbol=symbol, session=session, rangeHigh=0.0, rangeLow=0.0, retested=False, detail=f"No real candles fell inside the {session} window yet.")

    range_high = max(c.high for c in session_candles)
    range_low = min(c.low for c in session_candles)
    retested = any(c.low <= range_high and c.high >= range_low for c in other_candles)
    detail = f"{symbol}'s real {session} range: {range_low:.2f}-{range_high:.2f} over {len(session_candles)} candle(s)." + (" Retested by a later real candle." if retested else " Not yet retested by a later real candle.")
    return SessionRangeRead(symbol=symbol, session=session, rangeHigh=round(range_high, 4), rangeLow=round(range_low, 4), retested=retested, detail=detail)


def compute_fibonacci_levels(symbol: str, candles: list[Candle]) -> FibonacciRead:
    """Real retracement/extension price levels from the symbol's own
    most recent real swing high/low (the same swings
    `compute_market_structure()` already detects, reused directly).
    `detail` states plainly these are candidate areas, never guaranteed
    reaction levels — see FibonacciRead's own schema docstring."""
    structure = compute_market_structure(symbol, candles)
    if not structure.swing_highs or not structure.swing_lows:
        return FibonacciRead(symbol=symbol, swingHigh=0.0, swingLow=0.0, levels=[], detail="Not enough real swing history yet to compute Fibonacci levels.")
    swing_high, swing_low = structure.swing_highs[-1], structure.swing_lows[-1]
    span = swing_high - swing_low
    levels: list[FibonacciLevel] = [FibonacciLevel(ratio=r, price=round(swing_high - span * r, 4)) for r in FIBONACCI_RETRACEMENT_RATIOS]
    levels += [FibonacciLevel(ratio=r, price=round(swing_high + span * (r - 1.0), 4)) for r in FIBONACCI_EXTENSION_RATIOS]
    detail = f"{symbol}'s real most recent swing range {swing_low:.2f}-{swing_high:.2f} — candidate areas requiring real confirmation, never a guaranteed reaction level."
    return FibonacciRead(symbol=symbol, swingHigh=round(swing_high, 4), swingLow=round(swing_low, 4), levels=levels, detail=detail)


def detect_order_block(symbol: str, candles: list[Candle]) -> OrderBlockRead:
    """Reuses `compute_market_structure()`'s real Break of Structure read
    directly; if one exists, reports the last opposite-direction real
    candle immediately before it — one specific, disclosed, named
    definition, not a claim of real order-flow data. See
    `_DISCLOSED_PROXY_NOTE`."""
    structure = compute_market_structure(symbol, candles)
    if structure.last_break_of_structure == "none" or len(candles) < 2:
        return OrderBlockRead(symbol=symbol, direction="none", detail=_DISCLOSED_PROXY_NOTE)
    # A bullish BOS means the desk should look at the last real bearish
    # candle before the break broke it (and the mirror for bearish).
    want_bullish_candle = structure.last_break_of_structure == "bearish"
    for c in reversed(candles[:-1]):
        is_bullish = c.close > c.open
        if is_bullish == want_bullish_candle:
            return OrderBlockRead(
                symbol=symbol,
                direction=structure.last_break_of_structure,
                priceHigh=round(c.high, 4),
                priceLow=round(c.low, 4),
                timestamp=c.timestamp,
                detail=_DISCLOSED_PROXY_NOTE,
            )
    return OrderBlockRead(symbol=symbol, direction="none", detail=_DISCLOSED_PROXY_NOTE)
