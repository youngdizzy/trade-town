"""Volume Confirmation Engine — CEO directive "AHL-Inspired Systematic
Trend & Momentum Research Engine," Phase 7. That directive's own Phase
17 explicitly deferred this module in the first implementation pass
("do not fully build the volume/liquidity engine in this pass") — this
closes it.

RESEARCH FIRST (per this project's own standing rule): a full grep
audit found no shared relative-volume/volume-moving-average primitive
anywhere in this codebase. `app/market_intelligence.py` computes
relative volume TWICE, inline, with two different window definitions —
`_institutional_activity_read()` compares one bar's volume to the mean
of every PRIOR bar; the regime classifier's own `volume_trend` compares
a trailing 10-bar window to everything before it. Neither is a reusable
function, and neither is the standard, configurable "current volume vs.
its own N-period moving average" (RVOL) convention the directive's own
Phase 7 asks for ("Default: Volume MA = 20. But make the period
configurable."). This module is that one, real, reusable primitive —
following `app/technical_indicators.py`'s exact `sma`/`sma_series`
pattern (same file, same style, same `None`-below-minimum-history
convention) rather than inventing a third parallel volume convention.
The two existing inline calculations in market_intelligence.py are left
untouched: they serve their own already-real, already-tested purposes
(company-wide regime classification, single-symbol absorption
proxy) and migrating them is out of scope for this pass — but any NEW
per-symbol relative-volume need in this codebase should reach for this
module's functions, not a third inline copy.

WHAT'S REAL, PER `app/market_data.py::MockMarketDataProvider`'s OWN
GENERATOR (disclosed here, not fabricated around): a bar's volume is a
genuinely independent uniform draw every tick; a volume SPIKE only
becomes more LIKELY (never guaranteed, never deterministic) when the
same bar's price shock is large or the internal regime is "volatile"
(two small, hardcoded probability multipliers). So "does high relative
volume correlate with a big price move" is a real, non-circular
question this module's evidence can honestly answer yes to — but the
answer is bounded by exactly those two hand-tuned constants, never a
claim of emergent market microstructure. See
`compute_volume_confirmation()`'s own docstring for how this module
keeps OBSERVATION (the real numbers below), INTERPRETATION (nothing —
this module offers none), and TRADE SIGNAL (also nothing — that's the
separate, explicitly-tested hypothesis research this same directive
also asks for) apart, per the directive's own explicit three-way
distinction. This module never says "low volume = liquidity grab" or
similar — it only ever reports the real relative-volume number and the
real ATR-normalized price move alongside it.

Thresholds below (`VOLUME_CLIMAX_THRESHOLD` etc.) are real, disclosed,
round-number choices — the same "a chosen, published, inspectable
constant, not a fitted parameter" convention every other threshold in
this codebase already uses (e.g. `app/market_intelligence.py`'s
`EXPANSION_RATIO`/`LIQUIDITY_CLUSTER_TOLERANCE_PCT`) — never presented
as validated or optimal.
"""
from __future__ import annotations

import math

from app.market_data import Candle
from app.schemas import VolumeConfirmationRead, VolumeConfirmationState, VolumeState
from app.technical_indicators import atr

DEFAULT_VOLUME_MA_PERIOD = 20

# A bar's own relative volume vs. its trailing volume_sma — real,
# disclosed round-number bands, not fitted. >=3x average volume is a
# genuine outlier by any standard convention; <=0.5x is genuinely thin.
VOLUME_CLIMAX_THRESHOLD = 3.0
VOLUME_ELEVATED_THRESHOLD = 1.5
VOLUME_WEAK_THRESHOLD = 0.5

# How large a price move (in real ATR units) counts as a genuine
# "expansion" worth checking volume confirmation against — one full
# ATR is the same real magnitude `app/position_sizing.py`'s own
# chandelier-stop convention already treats as significant.
DEFAULT_EXPANSION_ATR_THRESHOLD = 1.0


def _is_real_volume(volume: float) -> bool:
    """CEO directive "TradeTown — 11/10 Next Engineering Pass," Phase
    3/4/7 — a real bar volume is a physical count of shares/contracts
    traded: it can never be negative, and it can never be NaN/infinite
    (this codebase's own mock provider never produces either — see
    `app/market_data.py::MockMarketDataProvider`). Neither
    `baseline == 0` (the pre-existing guard) nor Python's own `==`
    operator ever catches a NaN (`float('nan') == 0` is `False`, so a
    NaN baseline previously slipped through undetected and silently
    propagated as a NaN "relative volume" — a real gap this closes).
    Used to guard every real division `relative_volume()`/
    `relative_volume_series()` perform, never a validation layer for
    every function in this module (see their own docstrings for exactly
    which ones call this and why)."""
    return math.isfinite(volume) and volume >= 0


def volume_sma(candles: list[Candle], period: int = DEFAULT_VOLUME_MA_PERIOD) -> float | None:
    """Simple moving average of real bar volume over the last `period`
    candles — the volume equivalent of `technical_indicators.sma()`.
    `None` (never a value computed from fewer bars than requested) when
    there isn't enough real history yet."""
    if period < 1 or len(candles) < period:
        return None
    window = candles[-period:]
    return round(sum(c.volume for c in window) / period, 2)


def volume_sma_series(candles: list[Candle], period: int = DEFAULT_VOLUME_MA_PERIOD) -> list[float]:
    """The real, full volume-SMA series, one value per candle from the
    point a real `period`-bar window exists onward — same index
    alignment convention as `technical_indicators.sma_series()`."""
    if period < 1 or len(candles) < period:
        return []
    volumes = [c.volume for c in candles]
    return [round(sum(volumes[i - period + 1 : i + 1]) / period, 2) for i in range(period - 1, len(volumes))]


def relative_volume(candles: list[Candle], period: int = DEFAULT_VOLUME_MA_PERIOD) -> float | None:
    """The last candle's own real volume divided by the real volume-SMA
    of the `period` bars immediately BEFORE it (never including the bar
    itself in its own baseline — the standard RVOL convention). `None`
    below `period + 1` real bars of history, or whenever the baseline or
    the current bar's own volume is zero, negative, or non-finite (a
    real volume count can never legitimately be any of those three — see
    `_is_real_volume()`'s own docstring for why plain `baseline == 0`
    alone was never enough to catch a NaN baseline)."""
    if len(candles) < period + 1:
        return None
    current = candles[-1].volume
    baseline = volume_sma(candles[:-1], period)
    if baseline is None or not _is_real_volume(baseline) or baseline == 0 or not _is_real_volume(current):
        return None
    return round(current / baseline, 4)


def relative_volume_series(candles: list[Candle], period: int = DEFAULT_VOLUME_MA_PERIOD) -> list[float | None]:
    """The real, full relative-volume series — one value per candle from
    the point a real `period`-bar trailing baseline exists onward
    (index `period` of `candles`, since each value needs `period` PRIOR
    bars plus itself).

    CEO directive "TradeTown — 11/10 Next Engineering Pass" — this
    function previously fell back to a fabricated `0.0` at any index
    whose trailing baseline was `0` (an all-zero-volume window), while
    the single-value `relative_volume()` above returns an honest `None`
    for the identical undefined ratio. `0.0` there silently reads as a
    real, meaningful "no relative volume" data point rather than "this
    ratio is mathematically undefined" — a real correctness bug a
    downstream consumer (a chaos/backtest bar with a data gap, a halted
    session) could have silently misread as a genuine volume-weak
    signal. Fixed at the contract level, not patched around: the return
    type widens to `list[float | None]`, and every zero-baseline index
    now returns `None`, exactly mirroring `relative_volume()`'s own
    real contract — the same `list[float | None]` "undefined at this
    index, never a placeholder" convention
    `app/fibonacci_research.py::fibonacci_618_level_series()` already
    established for the analogous case (a genuinely undefined price
    level, never a fabricated `0.0`). `relative_volume_series(candles,
    period)[-1]` is guaranteed to equal `relative_volume(candles,
    period)` at every index, zero-baseline included — the same
    single-canonical-contract invariant this module's own test suite
    already asserted for the non-zero case. Also guards every index's
    own baseline and current-bar volume for finiteness/non-negativity
    (see `relative_volume()`'s own docstring and `_is_real_volume()` —
    the plain `if baseline` truthiness check alone never caught a NaN
    baseline, since `bool(float('nan'))` is `True` in Python)."""
    if len(candles) < period + 1:
        return []
    baselines = volume_sma_series(candles[:-1], period)
    series: list[float | None] = []
    for i, baseline in enumerate(baselines):
        current = candles[period + i].volume
        if not _is_real_volume(baseline) or baseline == 0 or not _is_real_volume(current):
            series.append(None)
        else:
            series.append(round(current / baseline, 4))
    return series


def dollar_volume(candles: list[Candle]) -> float | None:
    """The last real candle's own dollar volume (`volume * close`) — a
    real, trivial derived read from data this codebase already tracks
    per-candle (see `Candle.volume` in app/market_data.py), never a
    claim of real order-flow or notional turnover beyond that. `None`
    (never a fabricated 0.0) with no real candle history at all."""
    if not candles:
        return None
    last = candles[-1]
    return round(last.volume * last.close, 2)


def dollar_volume_sma(candles: list[Candle], period: int = DEFAULT_VOLUME_MA_PERIOD) -> float | None:
    """Simple moving average of real per-candle dollar volume over the
    last `period` candles — the dollar-volume equivalent of
    `volume_sma()` above, same `None`-below-minimum-history convention."""
    if period < 1 or len(candles) < period:
        return None
    window = candles[-period:]
    return round(sum(c.volume * c.close for c in window) / period, 2)


def classify_volume_state(rvol: float) -> VolumeState:
    if rvol >= VOLUME_CLIMAX_THRESHOLD:
        return "climax"
    if rvol >= VOLUME_ELEVATED_THRESHOLD:
        return "elevated"
    if rvol <= VOLUME_WEAK_THRESHOLD:
        return "weak"
    return "normal"


def compute_volume_confirmation(
    candles: list[Candle],
    symbol: str,
    *,
    period: int = DEFAULT_VOLUME_MA_PERIOD,
    atr_period: int = 14,
    expansion_atr_threshold: float = DEFAULT_EXPANSION_ATR_THRESHOLD,
) -> VolumeConfirmationRead | None:
    """The directive's own worked example, made real: "Price fell 2.1
    ATR while volume remained 0.96x its 20-period average." Combines
    `relative_volume()` with the most recent candle's own real
    close-to-close move, expressed in real ATR units (sign-preserved:
    positive = up move) so the reader can compare price magnitude and
    volume on the same real, unitless scale.

    `confirmation_state` is a plain categorical LABEL of the two real
    numbers above it, nothing more:
      - `confirmed_move`: a real expansion-sized move (>=
        `expansion_atr_threshold` ATR) with elevated-or-climax relative
        volume alongside it.
      - `unconfirmed_move`: the same real expansion-sized move, but
        relative volume was only normal or weak — a real, checkable
        divergence, never itself labeled a reversal signal or a
        "manipulation."
      - `abnormal_volume_quiet_price`: climax relative volume with no
        real expansion-sized move.
      - `normal`: neither condition met.
    Returns `None` when there isn't enough real candle history for
    either the relative-volume or the ATR read (never a fabricated
    partial answer)."""
    rvol = relative_volume(candles, period)
    atr_value = atr(candles, atr_period)
    if rvol is None or atr_value is None or atr_value == 0 or len(candles) < 2:
        return None

    last = candles[-1]
    prev_close = candles[-2].close
    price_move_atr = round((last.close - prev_close) / atr_value, 4)
    volume_state = classify_volume_state(rvol)

    is_expansion = abs(price_move_atr) >= expansion_atr_threshold
    confirmation_state: VolumeConfirmationState
    if is_expansion and volume_state in ("elevated", "climax"):
        confirmation_state = "confirmed_move"
        detail = f"Price moved {price_move_atr:+.2f} ATR while volume ran {rvol:.2f}x its {period}-period average — a real expansion with volume confirmation."
    elif is_expansion:
        confirmation_state = "unconfirmed_move"
        direction = "fell" if price_move_atr < 0 else "rose"
        detail = f"Price {direction} {abs(price_move_atr):.2f} ATR while volume remained {rvol:.2f}x its {period}-period average — the move is not volume-confirmed."
    elif volume_state == "climax":
        confirmation_state = "abnormal_volume_quiet_price"
        detail = f"Volume ran {rvol:.2f}x its {period}-period average while price moved only {price_move_atr:+.2f} ATR — abnormal volume without a proportional price move."
    else:
        confirmation_state = "normal"
        detail = f"Price moved {price_move_atr:+.2f} ATR on {rvol:.2f}x average volume — nothing notable by this module's own disclosed thresholds."

    return VolumeConfirmationRead(
        symbol=symbol,
        relativeVolume=rvol,
        volumeState=volume_state,
        priceMoveAtr=price_move_atr,
        confirmationState=confirmation_state,
        dollarVolume=dollar_volume(candles) or 0.0,
        dollarVolumeSma=dollar_volume_sma(candles, period),
        detail=detail,
    )
