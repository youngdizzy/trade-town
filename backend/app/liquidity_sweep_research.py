"""Liquidity Sweep Research — CEO directive "AHL-Inspired Systematic
Trend & Momentum Research Engine," Phase 8. That directive's own Phase
17 explicitly deferred this ("do not fully build the volume/liquidity
engine in this pass") — this closes the statistical-research half of it.

RESEARCH FIRST: `app/market_intelligence.py::compute_liquidity()` already
has a real, tested sweep DETECTOR (a candle wick pierces a clustered
equal-high/equal-low zone and closes back inside it) — but nothing in
this codebase has ever measured whether that detector has any real
predictive value. Per the directive's own explicit instruction ("do NOT
assume every sweep is a trade... measure frequency/win rate/expectancy"),
this module turns the existing detector into a real, backtestable
hypothesis rather than inventing a second, parallel sweep-detection
formula.

REUSE, NOT DUPLICATION: `liquidity_sweep_signal_series()` below calls
the real, unmodified `compute_liquidity()` repeatedly over a bounded
trailing window — zero new sweep-detection logic. The resulting series
is registered as a new `StrategyIndicatorName`
(`"liquidity_sweep_signal"`, see app/schemas.py) exactly the same way
CEO directive "AHL-Inspired..." Phase 1's `multi_horizon_trend_score`
was — so the hypothesis "does price reverse after a liquidity sweep"
compiles through the real `app/strategy_compiler.py` and runs through
the real `run_research_experiment()` pipeline (walk-forward, cost
sensitivity, parameter sensitivity, look-ahead audit, overfitting
diagnosis, baseline comparison), never a second, bespoke validation
path.

POINT-IN-TIME CORRECTNESS: each point in the series is computed from
`compute_liquidity(symbol, candles[start:i+1])` — a bounded, real
trailing window ending at (and including) candle `i`, never any bar
after it. The window is capped at `LIQUIDITY_SWEEP_SCAN_WINDOW` bars
(not the whole history up to `i`) purely for performance — this mirrors
how a real-time system would only ever look back so far anyway, and is
disclosed here rather than silently assumed; bounded to a fixed window,
scanning every single bar stays roughly linear in candle count (no
quadratic blowup), so every bar is checked — nothing is skipped.

SIGNAL MEANING AND A REAL, DISCLOSED MECHANICAL SUBTLETY: `+1.0` at a
bar where a real `below_lows` sweep is detectable (the classic
bullish-reversal reading — price swept below a liquidity pool and
reclaimed it); `-1.0` for a real `above_highs` sweep (bearish reading);
`0.0` everywhere else. This is a plain OBSERVATION/EVENT label, never an
interpretation of intent ("manipulation," "stop hunt by market makers")
— the directive's own explicit OBSERVATION/INTERPRETATION/TRADE SIGNAL
boundary. Because `compute_liquidity()`'s own real detection logic
checks whether the sweep candle falls within its last 5 "recent" bars,
a single real sweep event stays visible (the signal holds its nonzero
value) for a real multi-bar STREAK, not always a clean single-bar
pulse, as the sweep candle slides through several successive trailing
windows — `app/strategy_compiler.py`'s own liquidity-sweep trigger
pattern deliberately uses `crosses_above`/`crosses_below` (never a bare
`gt`/`lt` threshold) for exactly this reason, so a compiled strategy
fires once, on the real bar the streak begins, not once per bar of the
whole streak."""
from __future__ import annotations

from app.market_data import Candle
from app.market_intelligence import compute_liquidity

# Bounded trailing window per point-in-time liquidity read — real,
# disclosed, chosen to comfortably hold several real swing-point
# clusters (app/market_intelligence.py's own SWING_LOOKBACK=3 needs
# only 12 bars minimum) while keeping the full-series scan roughly
# linear rather than quadratic in candle count.
LIQUIDITY_SWEEP_SCAN_WINDOW = 60

def liquidity_sweep_signal_series(candles: list[Candle], symbol: str) -> list[float]:
    """The real, full liquidity-sweep signal series, index-aligned
    one-to-one with `candles` (a real value, `0.0` where no sweep is
    detectable, at every index) — the same alignment convention
    `app/trend_engine.py::multi_horizon_trend_score_series()` already
    established for `app/strategy_engine.py`'s `_resolve()` to look up
    directly with no offset math. Every bar is checked (a bounded
    trailing window keeps this roughly linear in candle count, so
    there's no need to skip bars for performance) — see this module's
    own docstring for why a real sweep event can legitimately hold its
    nonzero value across several consecutive bars, not just one."""
    n = len(candles)
    series = [0.0] * n
    for i in range(n):
        start = max(0, i + 1 - LIQUIDITY_SWEEP_SCAN_WINDOW)
        read = compute_liquidity(symbol, candles[start : i + 1])
        if read.sweep_direction == "below_lows":
            series[i] = 1.0
        elif read.sweep_direction == "above_highs":
            series[i] = -1.0
    return series
