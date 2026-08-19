"""app/survivorship.py — CEO directive "Professional Quant Trading Firm
— Quant Intelligence + Market Analysis Completion Phase (Next Research +
Validation Pass)," item 8: survivorship-bias checking.

RESEARCH FIRST, AND AN HONEST CONCLUSION: this codebase's entire research
universe (app/watchlist.py's `SEED_SYMBOLS` — eight fixed instruments —
plus `EXTRA_SYMBOL_POOL`, six more a player can add) is a static Python
list, present in full from the very first tick of every game and never
removed from, renamed, or replaced. There is no delisting concept, no
index-reconstitution history, no point-in-time membership record, and no
data source anywhere in this codebase that could honestly answer "was
symbol X part of the tradable universe on date Y." Every real candle
this codebase ever produces (`app/market_data.py`'s `MockMarketDataProvider`)
is a deterministic procedural walk for whichever symbol was asked for —
it has no concept of "this symbol didn't exist yet" or "this symbol was
removed from the index" either.

PER THIS DIRECTIVE'S OWN EXPLICIT FALLBACK ("If the required historical
data does not exist, DO NOT fabricate it. Instead: document the
limitation, create the correct data interface/schema, add tests for the
expected behavior, clearly mark the capability as unavailable until real
data exists."): this module does exactly that and nothing more.
`check_survivorship_bias()` always returns `status="unavailable"` with a
real, disclosed reason — never a fabricated "no bias detected" or a
guessed historical membership record. `SurvivorshipBiasRead` (app/
schemas.py) is the real, typed interface a future real historical-
universe data source (a point-in-time index-constituent feed, a
delisting record) could be wired into without changing any caller's own
shape — but no such source exists in this codebase today, and this
module does not pretend otherwise.
"""
from __future__ import annotations

from app.schemas import SurvivorshipBiasRead

_UNAVAILABLE_REASON = (
    "Survivorship-bias checking is unavailable: this codebase's research universe (app/watchlist.py's SEED_SYMBOLS/"
    "EXTRA_SYMBOL_POOL) is a fixed, static, always-present pool with no historical constituent or delisting data "
    "behind it, and app/market_data.py's mock candle provider has no concept of a symbol not existing yet or being "
    "removed. There is genuinely nothing for a real check to audit yet — this is a disclosed data limitation, not a "
    "computed 'no bias found' result."
)


def check_survivorship_bias(symbol: str) -> SurvivorshipBiasRead:
    """The one real entry point — always `unavailable`, with a real,
    disclosed reason. `symbol` is accepted (and echoed back) even for an
    unknown symbol, since the honest answer is identical either way:
    there is no historical universe-membership data to check against,
    known symbol or not."""
    return SurvivorshipBiasRead(symbol=symbol.upper(), status="unavailable", detail=_UNAVAILABLE_REASON)
