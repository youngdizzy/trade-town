"""CEO directive "Professional Quant Trading Core," Phase B — the P2
item explicitly deferred as a "genuine architectural lift": Multi-
Timeframe Confirmation.

THE GAP, CONFIRMED BY THREE INDEPENDENT MODULE DOCSTRINGS (per the
original Phase A audit): `app/executive.py`'s `PROPOSAL_TIMEFRAME`
("1h") is the ONLY timeframe ever fetched anywhere in this codebase for
a trading decision — duplicated as the same constant across
`black_swan.py`/`decision_vault.py`/`devils_advocate.py`/`executive.py`/
`portfolio_intelligence.py`/`war_room.py` (the same "small, stable
constant duplicated across a module boundary" precedent this codebase
already uses elsewhere, not a bug). `app/confidence.py`'s own docstring
explicitly named this exact gap: "multi-timeframe agreement (only one
timeframe — PROPOSAL_TIMEFRAME — is ever fetched)." `app/gatekeeper.py`'s
own docstring names it too, in its list of brief-requested checks with
"no real data source in this codebase."

WHY THIS IS NOW BUILDABLE (it wasn't fabricated data before, and still
isn't): `app/market_data.py`'s provider already synthesizes real candles
at every timeframe in `TIMEFRAME_ORDER`
(`1m`/`5m`/`15m`/`1h`/`4h`/`1d`) — confirmed via `TIMEFRAMES`'s own
minutes-per-candle mapping — it was simply never CALLED with anything
but `"1h"` for a trading decision. This module is the first real
consumer of a second and third real timeframe for that purpose.

REAL REUSE, NOT A NEW TREND-DETECTION METHOD: every per-timeframe
direction read below is `app/trend_engine.py`'s own real, already-tested
`compute_horizon_trend()` — the same "endpoint slope" methodology
`app/executive.py`'s `_technical_vote()` already uses (via
`trend_pct()`), just generalized to a timeframe other than 1h. Never a
second, parallel trend-detection algorithm invented for this feature.

WHAT "CONFIRMATION" MEANS HERE: not "do N arbitrary timeframes agree
with each other" — a real, actionable multi-timeframe read asks whether
HIGHER timeframes support the trade direction the desk is ABOUT to take.
`compute_multi_timeframe_confirmation()` therefore takes the desk's own
real `overall` buy/sell/wait call and measures what real share of the
evaluated higher timeframes' own trend direction agrees with it — the
standard technical-analysis sense of "higher-timeframe confirmation,"
not a symmetric consensus vote. `CONFIRMATION_TIMEFRAMES` deliberately
excludes `"1h"` itself: that timeframe's own real read is already the
existing Technical Alignment factor (`_technical_vote()`); re-including
it here would double-count the same real signal under a second name
rather than adding a genuinely new one.

HONEST NEUTRAL, NEVER FABRICATED AGREEMENT: a "wait" call has no real
direction to confirm against (`agreement_score = 50.0`, disclosed as
neutral in `summary`); a timeframe with too little real candle history
is excluded from the agreement count rather than silently counted as
disagreeing or agreeing — see `MultiTimeframeConfirmation`'s own
docstring in app/schemas.py.
"""
from __future__ import annotations

from app.market_data import MarketDataProvider
from app.schemas import AnalystChoice, MultiTimeframeConfirmation, TimeframeTrendReading
from app.trend_engine import compute_horizon_trend

# The two real timeframes above the existing 1h execution read — a
# real, disclosed, arbitrary choice (the same "conservative but
# arbitrary" resolution convention this codebase's own RiskLimits
# defaults already use), not the only defensible set. Matches
# app/market_data.py's own real TIMEFRAME_ORDER.
CONFIRMATION_TIMEFRAMES: tuple[str, ...] = ("4h", "1d")
CONFIRMATION_LOOKBACK_BARS = 20
# Matches app/executive.py's PROPOSAL_CANDLE_COUNT convention — enough
# real bars for a 20-bar lookback with room to spare.
CONFIRMATION_CANDLE_COUNT = 30


def compute_multi_timeframe_confirmation(provider: MarketDataProvider, symbol: str, overall: AnalystChoice) -> MultiTimeframeConfirmation:
    readings: list[TimeframeTrendReading] = []
    for timeframe in CONFIRMATION_TIMEFRAMES:
        candles = provider.get_candles(symbol, timeframe, CONFIRMATION_CANDLE_COUNT)
        horizon = compute_horizon_trend(candles, timeframe, CONFIRMATION_LOOKBACK_BARS, "endpoint_slope")
        readings.append(TimeframeTrendReading(timeframe=timeframe, direction=horizon.direction, detail=horizon.detail))

    if overall == "wait":
        return MultiTimeframeConfirmation(
            readings=readings,
            agreementScore=50.0,
            summary="The desk's own call is WAIT — no real trade direction to confirm against yet.",
        )

    target_direction = 1 if overall == "buy" else -1
    evaluated = [r for r in readings if r.direction != 0]
    insufficient_count = len(readings) - len(evaluated)
    if not evaluated:
        return MultiTimeframeConfirmation(
            readings=readings,
            agreementScore=50.0,
            summary=f"Not enough real candle history on any higher timeframe yet ({', '.join(CONFIRMATION_TIMEFRAMES)}) — treated as neutral, never fabricated confirmation.",
        )

    confirming = sum(1 for r in evaluated if r.direction == target_direction)
    agreement_score = round(confirming / len(evaluated) * 100, 1)
    insufficient_note = f" ({insufficient_count} had insufficient real history)" if insufficient_count else ""
    summary = f"{confirming}/{len(evaluated)} higher timeframes confirm the desk's {overall.upper()} direction{insufficient_note}."
    return MultiTimeframeConfirmation(readings=readings, agreementScore=agreement_score, summary=summary)
