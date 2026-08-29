"""Structure Confirmation Research — CEO directive "AHL-Inspired
Systematic Trend & Momentum Research Engine," Phase 10. That directive's
own Phase 17 explicitly deferred this ("do not fully build the
volume/liquidity engine in this pass") — this closes the Break-of-
Structure half of it, using the exact same real-detector-reuse pattern
`app/liquidity_sweep_research.py` already established for sweeps.

RESEARCH FIRST: `app/market_intelligence.py::compute_market_structure()`
already has a real Break of Structure (BOS) read (the standard
definition: the latest confirmed swing high above the prior one is
bullish BOS, the mirror for lows is bearish) — but, same as the
liquidity-sweep detector before this module, nothing had ever measured
whether a fresh BOS has real predictive value. This module turns that
existing read into an actually-testable hypothesis via the exact same
`StrategyIndicatorName` mechanism `liquidity_sweep_signal` already
established — zero new structure-detection logic.

CHANGE OF CHARACTER (CHoCH), CLOSED IN A LATER PASS: the directive's own
Phase 10 also asks for CHoCH as a distinct researchable event. This
module originally refused to invent a definition ("there is no single
universally-agreed one"). A later re-audit found `compute_market_
structure()` already computes both halves of one real, specific,
defensible definition — the latest real BOS, but only when it disagrees
with the real net trend over the sample — and now exposes it as
`MarketStructureRead.change_of_character`, disclosed explicitly as ONE
real choice, never claimed as the only valid one (see that field's own
docstring in app/schemas.py). `change_of_character_signal_series()`
below reuses the exact same bounded-window scanning pattern as
`structure_break_signal_series()` — zero new detection logic.

POINT-IN-TIME CORRECTNESS: `structure_break_signal_series()` calls
`compute_market_structure()` on a bounded trailing window ending at
(and including) each real candle — the same real, disclosed
`STRUCTURE_SCAN_WINDOW`-bars-back boundary
`app/liquidity_sweep_research.py`'s own module docstring already
justifies for `compute_liquidity()`. A real BOS state, once formed, can
persist unchanged across many subsequent bars until the next opposing
swing appears (a real structural property of the underlying detector,
not a bug here) — `app/strategy_compiler.py`'s own structure-break
trigger pattern uses `crosses_above`/`crosses_below`, the same one-shot
convention the liquidity-sweep trigger already uses, for the same
disclosed reason."""
from __future__ import annotations

from app.market_data import Candle
from app.market_intelligence import compute_market_structure

# Real, disclosed, bounded trailing window — comfortably larger than
# compute_market_structure()'s own real minimum (SWING_LOOKBACK*2+2 = 8
# bars) while keeping a full-series scan roughly linear in candle count.
STRUCTURE_SCAN_WINDOW = 60


def structure_break_signal_series(candles: list[Candle], symbol: str) -> list[float]:
    """The real, full structure-break signal series, index-aligned
    one-to-one with `candles` — `+1.0` where the real, most recent
    confirmed Break of Structure (within the trailing window) is
    bullish, `-1.0` where it's bearish, `0.0` where none or not enough
    history yet. Same alignment convention
    `app/liquidity_sweep_research.py::liquidity_sweep_signal_series()`
    already established."""
    n = len(candles)
    series = [0.0] * n
    for i in range(n):
        start = max(0, i + 1 - STRUCTURE_SCAN_WINDOW)
        read = compute_market_structure(symbol, candles[start : i + 1])
        if read.last_break_of_structure == "bullish":
            series[i] = 1.0
        elif read.last_break_of_structure == "bearish":
            series[i] = -1.0
    return series


def change_of_character_signal_series(candles: list[Candle], symbol: str) -> list[float]:
    """The real, full Change of Character signal series, index-aligned
    one-to-one with `candles` — `+1.0` where the real, most recent
    confirmed CHoCH (within the trailing window) is bullish, `-1.0`
    where it's bearish, `0.0` where none or not enough history yet.
    Reuses `compute_market_structure()`'s own real
    `change_of_character` field (see its docstring for the exact,
    disclosed definition) over the same bounded trailing window
    `structure_break_signal_series()` above already uses — zero new
    detection logic."""
    n = len(candles)
    series = [0.0] * n
    for i in range(n):
        start = max(0, i + 1 - STRUCTURE_SCAN_WINDOW)
        read = compute_market_structure(symbol, candles[start : i + 1])
        if read.change_of_character == "bullish":
            series[i] = 1.0
        elif read.change_of_character == "bearish":
            series[i] = -1.0
    return series
