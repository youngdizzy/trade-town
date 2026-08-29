"""Fair Value Gap Research — CEO directive "AHL-Inspired Systematic
Trend & Momentum Research Engine," Phase 10 (the FVG half; the sweep and
structure/CHoCH halves were closed by app/liquidity_sweep_research.py
and app/structure_break_research.py).

RESEARCH FIRST: `app/technical_patterns.py::detect_fair_value_gaps()`
already has a real, standard 3-candle FVG detector (candle[i-2].high
below candle[i].low is a real bullish gap — price displaced through this
zone without a full real trade there — the mirror is bearish) — but
nothing in this codebase had ever measured whether a fresh FVG has real
predictive value. This module turns that existing detector into an
actually-testable hypothesis, the exact same real-detector-reuse pattern
`app/liquidity_sweep_research.py`/`app/structure_break_research.py`
already established — zero new gap-detection logic.

POINT-IN-TIME CORRECTNESS: `fvg_signal_series()` calls the real,
unmodified `detect_fair_value_gaps()` repeatedly over a bounded trailing
window ending at (and including) each real candle — the same real,
disclosed bounded-window convention every other event-signal module in
this directive already uses.

SIGNAL MEANING AND THE SAME REAL, DISCLOSED MECHANICAL SUBTLETY: `+1.0`
where the most recent real gap within the trailing window is bullish,
`-1.0` where bearish, `0.0` where none or not enough history yet. A real
FVG, once formed, stays visible (the signal holds its nonzero value)
across a real multi-bar streak as it slides through several successive
trailing windows — `app/strategy_compiler.py`'s own FVG trigger pattern
uses `crosses_above`/`crosses_below` (never a bare `gt`/`lt`), the same
one-shot convention every other event-signal trigger in this directive
already uses, for the same disclosed reason."""
from __future__ import annotations

from app.market_data import Candle
from app.technical_patterns import detect_fair_value_gaps

# Real, disclosed, bounded trailing window — comfortably larger than
# detect_fair_value_gaps()'s own real minimum (3 bars) while keeping a
# full-series scan roughly linear in candle count, the same convention
# app/structure_break_research.py's own STRUCTURE_SCAN_WINDOW uses.
FVG_SCAN_WINDOW = 60


def fvg_signal_series(candles: list[Candle], symbol: str) -> list[float]:
    """The real, full Fair Value Gap signal series, index-aligned
    one-to-one with `candles` — `+1.0` where the real, most recent Fair
    Value Gap (within the trailing window) is bullish, `-1.0` where
    it's bearish, `0.0` where none or not enough history yet. Same
    alignment convention `structure_break_signal_series()` already
    established."""
    n = len(candles)
    series = [0.0] * n
    for i in range(n):
        start = max(0, i + 1 - FVG_SCAN_WINDOW)
        read = detect_fair_value_gaps(symbol, candles[start : i + 1])
        if not read.gaps:
            continue
        latest = read.gaps[-1]
        series[i] = 1.0 if latest.direction == "bullish" else -1.0
    return series
