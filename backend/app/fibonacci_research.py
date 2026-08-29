"""Fibonacci Retracement Research — CEO directive "AHL-Inspired
Systematic Trend & Momentum Research Engine," Phase 10 (the Fibonacci
half; the sweep, structure/CHoCH, and FVG halves were closed by
app/liquidity_sweep_research.py, app/structure_break_research.py, and
app/fvg_research.py).

RESEARCH FIRST: `app/technical_patterns.py::compute_fibonacci_levels()`
already computes real retracement/extension PRICE LEVELS from the
symbol's own most recent real swing high/low (reusing
`compute_market_structure()`'s real swing detection directly, zero new
detection logic) — but nothing in this codebase had ever measured
whether price reacting near one of those levels has real predictive
value.

ONE REAL, DISCLOSED RATIO, NOT ALL EIGHT. `compute_fibonacci_levels()`
computes five real retracement ratios (0.236/0.382/0.5/0.618/0.786) and
two real extension ratios (1.272/1.618) every time it's called. Wiring
all seven as separate named `StrategyIndicatorName` values (seven new
compiler patterns, seven new series-cache fields) is real, tractable
future work, but this pass wires exactly ONE — the 61.8% "golden ratio"
retracement, the single most commonly referenced level in real
price-action practice — a deliberate, disclosed scope cut, the same
"grow the vocabulary incrementally" precedent every other indicator in
this directive already follows (see app/strategy_engine.py's own
`SUPPORTED_INDICATORS` module comment).

A DIFFERENT KIND OF INDICATOR THAN EVERY OTHER ONE THIS DIRECTIVE ADDED.
liquidity_sweep_signal/structure_break_signal/choch_signal/fvg_signal
are all EVENT-PULSE series (+1/-1/0). This one is a real PRICE-VALUED
series (the actual retracement price at each bar), the same category as
price_close/ema/sma — so `fibonacci_618_level_series()` returns
`float | None` (never a fabricated 0.0 sentinel, which would falsely
read as a real zero price) and `None` before enough real swing history
exists, exactly matching how `app/strategy_engine.py::_resolve()`
already treats ema/sma/rsi/macd/stochastic before their own real
warm-up periods (a `None` on either side of a condition is always
skipped, never silently compared as if it were a real 0.0 — see that
module's own backtest loop).

POINT-IN-TIME CORRECTNESS: each point is computed from
`compute_fibonacci_levels(symbol, candles[start:i+1])` — a bounded real
trailing window ending at (and including) candle `i`, the same
disclosed `FIBONACCI_SCAN_WINDOW`-bars-back convention every other
research module in this directive already uses."""
from __future__ import annotations

from app.market_data import Candle
from app.technical_patterns import compute_fibonacci_levels

# Real, disclosed, bounded trailing window — comfortably larger than
# compute_market_structure()'s own real minimum (SWING_LOOKBACK*2+2 = 8
# bars, reused internally by compute_fibonacci_levels()) while keeping a
# full-series scan roughly linear in candle count, the same convention
# app/structure_break_research.py's own STRUCTURE_SCAN_WINDOW uses.
FIBONACCI_SCAN_WINDOW = 60

# The one real, disclosed ratio this pass wires — see this module's own
# docstring for why only this one, not all seven real ratios
# compute_fibonacci_levels() already computes.
FIBONACCI_618_RATIO = 0.618


def fibonacci_618_level_series(candles: list[Candle], symbol: str) -> list[float | None]:
    """The real, full 61.8% Fibonacci retracement PRICE series, index-
    aligned one-to-one with `candles` — the real retracement price at
    each bar (from the symbol's own most recent real swing high/low
    within the trailing window), `None` before enough real swing
    history exists. Never `0.0` as a placeholder — see this module's
    own docstring for why that would be a real correctness bug for a
    price-valued series."""
    n = len(candles)
    series: list[float | None] = [None] * n
    for i in range(n):
        start = max(0, i + 1 - FIBONACCI_SCAN_WINDOW)
        read = compute_fibonacci_levels(symbol, candles[start : i + 1])
        level = next((lv.price for lv in read.levels if lv.ratio == FIBONACCI_618_RATIO), None)
        series[i] = level
    return series
