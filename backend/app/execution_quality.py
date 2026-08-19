"""CEO directive "Next Professional Trading Firm Phase," Priority 1 —
Execution Realism.

RESEARCH FIRST (per the directive's own mandatory rule): a full audit of
app/broker.py and app/portfolio.py found a real 1-tick order-placement
latency (app/broker.py's place_order()/tick_broker()) and a real flat
transaction-cost model (app/portfolio.py's TRANSACTION_COST_BPS) already
in place, but NO slippage anywhere — every fill (a market order, a
triggered stop/stop-loss, the CEO's own direct buy/sell via
app/executive.py's resolve_proposal(), the hold-duration auto-close in
app/paper_trading.py, and the day-end flatten in app/trading_modes.py)
executes at EXACTLY the observed signal price, every time, regardless of
how thin or volatile the market actually was that tick. This module
closes exactly that gap, and only that gap.

WHAT THIS DELIBERATELY DOES NOT MODEL (explicitly out of scope, not a
fabrication gap papered over): partial fills, order-book depth, and
gap-through behavior are NOT modeled — this codebase has no
order-book-depth or tick-by-tick intra-candle gap data to honestly
derive them from (the same boundary app/portfolio.py's
TRANSACTION_COST_BPS docstring already draws for transaction cost).
Limit and take-profit orders are NOT slipped — a limit order's whole
definition is "this price or better," so leaving them exact fill IS the
realistic behavior, not a missing feature. Only genuinely uncertain
fills — market orders, and stop/stop-loss orders once triggered (which
behave as market orders from that point on, in every real market) — get
slippage applied.

THE MODEL: SIGNAL PRICE (the price the caller already had) -> a real,
disclosed, formula-based slippage rate in basis points, driven ONLY by
this tick's own already-real MarketIntelligenceState — never a new
random number, never fabricated order-flow data:

  - `market_intelligence.quality.score` (0-100, already a real composite
    of volatility deviation, structure clarity, session liquidity,
    liquidity-sweep risk, and news activity — see
    app/market_intelligence.py's compute_market_quality()) drives the
    baseline: worse conditions, more slippage.
  - This symbol's own real `LiquidityRead.liquidity_score` (0-100, from
    `market_intelligence.liquidity`), when a read exists for it, refines
    the baseline with the specific instrument's own liquidity-zone/
    sweep read instead of only the whole-watchlist composite.

Slippage is always adverse to the trader (a buy fills higher, a sell
fills lower) — deliberate: real market microstructure very rarely gives
a participant a *better* price than displayed, and modeling favorable
slippage would be its own kind of fabrication.

CONSISTENT WITH EXISTING PRECEDENT: this is the same "disclosed,
formula-based simplification, never derived from real bid-ask spread or
order-book depth because this codebase has neither" standard
TRANSACTION_COST_BPS already established (see app/portfolio.py's module
docstring) — just now varying tick-to-tick with real, already-computed
market conditions instead of staying a flat constant.
"""
from __future__ import annotations

from app.schemas import MarketIntelligenceState, OrderSide

# Baseline slippage at the best realistic simulated conditions (a
# MarketQualityScore of 100 and, if a per-symbol LiquidityRead exists, a
# liquidity_score of 100 too) — still nonzero, because even a "perfect"
# real market has some real friction.
BASE_SLIPPAGE_BPS = 2.0

# Slippage ceiling at the worst realistic simulated conditions (a
# MarketQualityScore of 0 and, if available, a liquidity_score of 0) — a
# deliberately bounded worst case, not an unbounded blowup.
MAX_SLIPPAGE_BPS = 20.0


def compute_slippage_bps(market_intelligence: MarketIntelligenceState, symbol: str) -> float:
    """The real, disclosed slippage rate for a fill on `symbol` on this
    tick. See module docstring for the two real inputs and why nothing
    here is fabricated."""
    quality_penalty = max(0.0, min(1.0, (100.0 - market_intelligence.quality.score) / 100.0))
    liquidity_read = next((read for read in market_intelligence.liquidity if read.symbol == symbol), None)
    liquidity_penalty = (
        max(0.0, min(1.0, (100.0 - liquidity_read.liquidity_score) / 100.0))
        if liquidity_read is not None
        else quality_penalty
    )
    combined_penalty = (quality_penalty + liquidity_penalty) / 2.0
    return round(BASE_SLIPPAGE_BPS + combined_penalty * (MAX_SLIPPAGE_BPS - BASE_SLIPPAGE_BPS), 2)


def apply_slippage(
    price: float,
    *,
    action_side: OrderSide,
    market_intelligence: MarketIntelligenceState | None,
    symbol: str,
) -> tuple[float, float]:
    """Returns `(fill_price, slippage_bps_applied)`. `action_side` is the
    real transactional side of THIS fill — "buy" for opening a long or
    covering a short, "sell" for opening a short or closing a long —
    always adverse regardless of which side the underlying position is
    on. `market_intelligence` is optional (None from a test fixture, or
    any caller that hasn't been threaded through yet) — slippage_bps is
    then honestly 0.0, never guessed."""
    if market_intelligence is None or price <= 0:
        return price, 0.0
    slippage_bps = compute_slippage_bps(market_intelligence, symbol)
    slippage_factor = slippage_bps / 10_000.0
    fill_price = price * (1 + slippage_factor) if action_side == "buy" else price * (1 - slippage_factor)
    return round(fill_price, 4), slippage_bps
