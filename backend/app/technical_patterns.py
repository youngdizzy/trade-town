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
from typing import Literal

from app.market_data import Candle
from app.market_intelligence import SWING_LOOKBACK, _find_swings, _session_for_hour, compute_market_structure
from app.schemas import (
    CandlestickPattern,
    CandlestickPatternRead,
    ChartPattern,
    ChartPatternRead,
    FairValueGap,
    FairValueGapRead,
    FibonacciLevel,
    FibonacciRead,
    OrderBlockRead,
    SessionRangeRead,
    SupportResistanceLevel,
    SupportResistanceRead,
    SwingStructureLabel,
    SwingStructureRead,
    TradingSession,
)

# Standard, named Fibonacci retracement ratios — real, well-known
# numbers, never asserted here as reliably reactive (see FibonacciRead's
# own schema docstring and the Academy lesson backing this function).
FIBONACCI_RETRACEMENT_RATIOS: tuple[float, ...] = (0.236, 0.382, 0.5, 0.618, 0.786)
FIBONACCI_EXTENSION_RATIOS: tuple[float, ...] = (1.272, 1.618)

# CEO directive "Professional Quant Trading Firm — Quant Intelligence +
# Market Analysis Completion Phase," Phase B — real, disclosed research
# assumptions for support/resistance clustering, no existing in-codebase
# precedent to cite (the same honesty standard app/model_validation.py's
# own new thresholds are held to).
LEVEL_CLUSTER_TOLERANCE_PCT = 0.5
MIN_TOUCHES_FOR_LEVEL = 2
MAX_LEVELS_RETURNED = 8

# Same directive's "Next Research + Validation Pass" — real, disclosed
# research assumptions for the double top/bottom and trendline-break
# chart-pattern detectors below. No existing in-codebase precedent to
# cite for any of these; held to the same explicit-and-testable standard
# every other threshold in this module already is.
DOUBLE_PATTERN_PRICE_TOLERANCE_PCT = 1.5
DOUBLE_PATTERN_MIN_RETRACEMENT_PCT = 1.0
TRENDLINE_TOUCH_TOLERANCE_PCT = 0.5
MAX_CHART_PATTERNS_RETURNED = 8

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


def detect_support_resistance_levels(symbol: str, candles: list[Candle]) -> SupportResistanceRead:
    """Real, static support/resistance levels: clusters the symbol's own
    real swing highs AND lows (reusing `app/market_intelligence.py`'s
    `_find_swings()` directly — the same real local-extrema detection
    `compute_market_structure()` already uses, never a second swing
    detector) into price bands within `LEVEL_CLUSTER_TOLERANCE_PCT` of
    each other. A band needs at least `MIN_TOUCHES_FOR_LEVEL` real swing
    points before it counts as a real level — a single, unconfirmed
    swing is never reported as "the" support/resistance. `role` is
    mechanical (support below the real current close, resistance above)
    — the same real, standard price-action convention every trader
    uses, never a claim the level will actually hold."""
    if len(candles) < SWING_LOOKBACK * 2 + 2:
        return SupportResistanceRead(symbol=symbol, levels=[], detail="Not enough real candle history yet to detect support/resistance levels.")
    highs, lows = _find_swings(candles)
    swing_prices = [price for _i, price in highs] + [price for _i, price in lows]
    if len(swing_prices) < MIN_TOUCHES_FOR_LEVEL:
        return SupportResistanceRead(symbol=symbol, levels=[], detail="Not enough real swing points yet to cluster into a level.")

    swing_prices.sort()
    clusters: list[list[float]] = [[swing_prices[0]]]
    for price in swing_prices[1:]:
        cluster_mean = sum(clusters[-1]) / len(clusters[-1])
        if cluster_mean > 0 and abs(price - cluster_mean) / cluster_mean * 100 <= LEVEL_CLUSTER_TOLERANCE_PCT:
            clusters[-1].append(price)
        else:
            clusters.append([price])

    current_close = candles[-1].close
    levels: list[SupportResistanceLevel] = []
    for cluster in clusters:
        if len(cluster) < MIN_TOUCHES_FOR_LEVEL:
            continue
        level_price = round(sum(cluster) / len(cluster), 4)
        role = "support" if current_close > level_price else "resistance"
        levels.append(
            SupportResistanceLevel(
                price=level_price,
                touches=len(cluster),
                role=role,  # type: ignore[arg-type]
                detail=f"Real cluster of {len(cluster)} swing point(s) within {LEVEL_CLUSTER_TOLERANCE_PCT:g}% of {level_price:.2f}, currently read as {role} (real close {current_close:.2f}).",
            )
        )

    levels.sort(key=lambda lv: lv.touches, reverse=True)
    levels = levels[:MAX_LEVELS_RETURNED]
    levels.sort(key=lambda lv: lv.price)

    detail = (
        f"{len(levels)} real level(s) found from {len(swing_prices)} real swing point(s), each requiring >= {MIN_TOUCHES_FOR_LEVEL} touches "
        f"within {LEVEL_CLUSTER_TOLERANCE_PCT:g}% of each other."
        if levels
        else f"{len(swing_prices)} real swing point(s) found, but none clustered into a real >= {MIN_TOUCHES_FOR_LEVEL}-touch level."
    )
    return SupportResistanceRead(symbol=symbol, levels=levels, detail=detail)


def _double_pattern_matches(symbol: str, candles: list[Candle], peaks: list[tuple[int, float]], troughs: list[tuple[int, float]], timeframe: str, *, kind: Literal["top", "bottom"]) -> list[ChartPattern]:
    """Shared real geometry for double top (`kind="top"`, `peaks` = real
    swing highs, `troughs` = real swing lows) and double bottom
    (`kind="bottom"`, the mirror). Only ADJACENT same-type swing points
    are ever paired — the standard, objective "two comparable swings with
    one real pullback between them" shape, never an arbitrary multi-hop
    search across the whole series. A pattern is only ever reported once
    real CONFIRMATION (a real close through the real intervening
    neckline) has already happened at a later real bar — never as a
    still-forming, outcome-unknown shape."""
    results: list[ChartPattern] = []
    for k in range(len(peaks) - 1):
        i1, p1 = peaks[k]
        i2, p2 = peaks[k + 1]
        between = [t for t in troughs if i1 < t[0] < i2]
        if not between:
            continue
        neckline_idx, neckline_price = (min(between, key=lambda t: t[1]) if kind == "top" else max(between, key=lambda t: t[1]))
        price_diff_pct = abs(p1 - p2) / ((p1 + p2) / 2) * 100 if (p1 + p2) else 100.0
        if price_diff_pct > DOUBLE_PATTERN_PRICE_TOLERANCE_PCT:
            continue
        reference = min(p1, p2) if kind == "top" else max(p1, p2)
        if reference == 0:
            continue
        retracement_pct = (reference - neckline_price) / reference * 100 if kind == "top" else (neckline_price - reference) / reference * 100
        if retracement_pct < DOUBLE_PATTERN_MIN_RETRACEMENT_PCT:
            continue
        confirm_index: int | None = None
        for j in range(i2 + 1, len(candles)):
            if kind == "top" and candles[j].close < neckline_price:
                confirm_index = j
                break
            if kind == "bottom" and candles[j].close > neckline_price:
                confirm_index = j
                break
        if confirm_index is None:
            continue
        confidence = round(max(0.0, min(100.0, 100.0 * (1 - price_diff_pct / DOUBLE_PATTERN_PRICE_TOLERANCE_PCT))), 1)
        direction: Literal["bullish", "bearish"] = "bearish" if kind == "top" else "bullish"
        pattern_type: Literal["double_top", "double_bottom"] = "double_top" if kind == "top" else "double_bottom"
        price_low = min(p1, p2, neckline_price)
        price_high = max(p1, p2, neckline_price)
        results.append(
            ChartPattern(
                patternId=f"{symbol}-{pattern_type}-{candles[i1].timestamp}-{candles[i2].timestamp}",
                patternType=pattern_type,
                direction=direction,
                confidencePct=confidence,
                priceLow=round(price_low, 4),
                priceHigh=round(price_high, 4),
                formedAt=candles[i2].timestamp,
                confirmedAt=candles[confirm_index].timestamp,
                formationDetail=(
                    f"Real {kind} swing points {p1:.2f} ({candles[i1].timestamp}) and {p2:.2f} ({candles[i2].timestamp}), "
                    f"{price_diff_pct:.2f}% apart (within the {DOUBLE_PATTERN_PRICE_TOLERANCE_PCT:g}% tolerance), with a real "
                    f"{retracement_pct:.2f}% intervening retracement to the {neckline_price:.2f} neckline."
                ),
                invalidationDetail=(
                    f"A real close back beyond {p2:.2f} before the neckline broke would have invalidated this setup instead; "
                    f"already confirmed by a real close through the {neckline_price:.2f} neckline at {candles[confirm_index].timestamp}."
                ),
                source="technical_patterns.detect_chart_patterns",
                timeframe=timeframe,
                symbol=symbol,
            )
        )
    return results


def _trendline_break_matches(symbol: str, candles: list[Candle], swing_points: list[tuple[int, float]], timeframe: str, *, direction: Literal["up", "down"]) -> list[ChartPattern]:
    """Real 2-point trendlines through ADJACENT same-type swings —
    `direction="up"` connects consecutive real higher swing lows (a
    rising support line), `direction="down"` connects consecutive real
    lower swing highs (a falling resistance line). A pattern is only
    reported once a later real candle's own close crosses the real
    extrapolated line value — never a still-forming line whose break is
    only assumed. `confidencePct` rewards real additional swing points
    that independently touch the same line within tolerance — a genuine,
    disclosed, mechanical proxy for "more confirmed trendline," never a
    fabricated strength score."""
    results: list[ChartPattern] = []
    for k in range(len(swing_points) - 1):
        i1, p1 = swing_points[k]
        i2, p2 = swing_points[k + 1]
        if direction == "up" and p2 <= p1:
            continue
        if direction == "down" and p2 >= p1:
            continue
        slope = (p2 - p1) / (i2 - i1)

        def line_value(idx: int, *, _i1: int = i1, _p1: float = p1, _slope: float = slope) -> float:
            return _p1 + _slope * (idx - _i1)

        confirm_index: int | None = None
        for j in range(i2 + 1, len(candles)):
            line_at_j = line_value(j)
            if direction == "up" and candles[j].close < line_at_j:
                confirm_index = j
                break
            if direction == "down" and candles[j].close > line_at_j:
                confirm_index = j
                break
        if confirm_index is None:
            continue
        touches = 2
        for idx, price in swing_points:
            if idx in (i1, i2) or not (i1 < idx < confirm_index):
                continue
            line_at_idx = line_value(idx)
            if line_at_idx != 0 and abs(price - line_at_idx) / abs(line_at_idx) * 100 <= TRENDLINE_TOUCH_TOLERANCE_PCT:
                touches += 1
        confidence = round(min(95.0, 50.0 + (touches - 2) * 15.0), 1)
        pattern_type: Literal["trendline_break_down", "trendline_break_up"] = "trendline_break_down" if direction == "up" else "trendline_break_up"
        result_direction: Literal["bullish", "bearish"] = "bearish" if direction == "up" else "bullish"
        confirm_price = candles[confirm_index].close
        price_low = min(p1, p2, confirm_price)
        price_high = max(p1, p2, confirm_price)
        results.append(
            ChartPattern(
                patternId=f"{symbol}-{pattern_type}-{candles[i1].timestamp}-{candles[confirm_index].timestamp}",
                patternType=pattern_type,
                direction=result_direction,
                confidencePct=confidence,
                priceLow=round(price_low, 4),
                priceHigh=round(price_high, 4),
                formedAt=candles[i2].timestamp,
                confirmedAt=candles[confirm_index].timestamp,
                formationDetail=(
                    f"Real {'rising support' if direction == 'up' else 'falling resistance'} trendline through swing points "
                    f"{p1:.2f} ({candles[i1].timestamp}) and {p2:.2f} ({candles[i2].timestamp}), {touches} real touch(es) "
                    f"within {TRENDLINE_TOUCH_TOLERANCE_PCT:g}% of the extrapolated line."
                ),
                invalidationDetail=(
                    f"Already confirmed by a real close ({confirm_price:.2f}) crossing the extrapolated trendline "
                    f"({line_value(confirm_index):.2f}) at {candles[confirm_index].timestamp}."
                ),
                source="technical_patterns.detect_chart_patterns",
                timeframe=timeframe,
                symbol=symbol,
            )
        )
    return results


def detect_chart_patterns(symbol: str, candles: list[Candle], timeframe: str = "1h") -> ChartPatternRead:
    """CEO directive "Professional Quant Trading Firm — Quant Intelligence
    + Market Analysis Completion Phase (Next Research + Validation
    Pass)" — a bounded, objectively-defined subset of chart-pattern
    geometry: double top, double bottom, and trendline breaks (both
    directions). Reuses the same real `_find_swings()` local-extrema
    detection every other pattern in this module already reuses — no
    second swing detector. DELIBERATELY NOT HERE: head & shoulders,
    triangles, wedges, rectangles, and channels — each needs a real
    multi-point geometric fit (3+ independently-constrained points, not
    the 2-3 point shapes below), a materially larger undertaking judged
    out of scope for this pass rather than attempted and left unreliable
    (see docs/Architecture.md for the full disclosed scope cut)."""
    if len(candles) < SWING_LOOKBACK * 2 + 2:
        return ChartPatternRead(symbol=symbol, timeframe=timeframe, patterns=[], detail="Not enough real candle history yet to detect a chart pattern.")

    highs_idx, lows_idx = _find_swings(candles)
    patterns: list[ChartPattern] = []
    patterns += _double_pattern_matches(symbol, candles, highs_idx, lows_idx, timeframe, kind="top")
    patterns += _double_pattern_matches(symbol, candles, lows_idx, highs_idx, timeframe, kind="bottom")
    patterns += _trendline_break_matches(symbol, candles, lows_idx, timeframe, direction="up")
    patterns += _trendline_break_matches(symbol, candles, highs_idx, timeframe, direction="down")
    patterns.sort(key=lambda p: p.confirmed_at)
    patterns = patterns[-MAX_CHART_PATTERNS_RETURNED:]

    detail = (
        f"{len(patterns)} real confirmed chart pattern(s) over {len(candles)} candles (double top/bottom + trendline break only — "
        "head & shoulders/triangles/wedges/rectangles/channels are a disclosed, out-of-scope gap, not silently absent)."
        if patterns
        else "No real confirmed double top/bottom or trendline break pattern found in this candle window."
    )
    return ChartPatternRead(symbol=symbol, timeframe=timeframe, patterns=patterns, detail=detail)
