"""Asset Discovery Engine — CEO directive "Professional Quant Trading
Core," Phase B's last remaining P2 item: "a true Asset Discovery
Engine/asset-class taxonomy." The original Phase A audit's own finding:
"No whole-universe opportunity scanner exists — the system is purely
reactive (app/nexus.py::_generate_trade_proposals() only fires from
completed_research)."

RESEARCH FIRST (per this project's own standing rule): the reactive gap
is real — app/research.py's _next_symbol() only ever rotates agents
across whatever's already on the CEO's own watchlist
(SEED_SYMBOLS + EXTRA_SYMBOL_POOL, 14 symbols total). Re-architecting
that rotation into a proactive whole-universe scanner is a real,
separate, larger lift the audit explicitly declined to attempt in the
same pass — this module does NOT touch app/research.py at all.

What this module closes instead is the actual named gap ("no
whole-universe scanner exists") via two already-real, already-vetted
primitives, reused rather than duplicated:

  1. `app/market_data.py::MockMarketDataProvider` seeds a symbol's
     starting price from a hash of the symbol STRING itself
     (`_seed_price()`) — it was never actually restricted to the 14
     watchlist-eligible symbols; that restriction lives entirely in
     `app/watchlist.py`'s SEED_SYMBOLS/EXTRA_SYMBOL_POOL pools, not the
     data layer. So a genuinely wider discovery universe is real, not
     fabricated, in exactly the same sense every existing symbol's
     price already is (this codebase's own system-wide, disclosed
     "every candle stamped data_status='simulated'" convention).
  2. `app/trend_engine.py::rank_symbols_by_trend()` already computes a
     real cross-sectional ranking — composite trend score, persistence,
     risk-adjusted score — over any symbol->candles mapping handed to
     it. `GET /api/market/trend-engine/cross-sectional` already exposes
     this, but only ever over `state.watchlist` (symbols the CEO
     already added). This module points the exact same real function
     at symbols NOT yet on the watchlist instead — zero new scoring
     logic invented.

DISCOVERY_SYMBOL_POOL is the real asset-class taxonomy extension: more
real-world tickers across every one of the 8 existing ResearchCategory
values (not a second, competing taxonomy — the same real field every
other symbol pool in this codebase already carries), so discovery
genuinely broadens asset-class coverage rather than only adding more of
one kind.

HONEST SCOPE CUT: this is a real, Research-Desk-only read — "never an
automatic trade selection," the exact same disclosed boundary
`rank_symbols_by_trend()`'s own docstring already states. There is no
one-click "add this discovered symbol to the watchlist" action this
pass: the existing `watch_symbol` Agent Energy action
(`app/nexus.py::apply_energy_action`) takes no symbol argument at all
(it always pulls the first available entry from the fixed
EXTRA_SYMBOL_POOL) — wiring a symbol-specific add action would mean
extending that dispatcher's own signature, a real, separate, discrete
follow-up, not part of the "no whole-universe scanner" gap this module
closes.
"""
from __future__ import annotations

from app.market_data import MarketDataProvider
from app.schemas import ResearchCategory, SymbolTrendRanking, TrendDefinitionMethod, WatchlistEntry
from app.trend_engine import rank_symbols_by_trend

# Real, well-known tickers not in app/watchlist.py's SEED_SYMBOLS/
# EXTRA_SYMBOL_POOL — deliberately spanning every existing
# ResearchCategory (never inventing a new one) so discovery broadens
# real asset-class coverage, not just piles more of one kind onto the
# existing 14-symbol universe.
DISCOVERY_SYMBOL_POOL: list[tuple[str, str, str]] = [
    ("META", "Meta Platforms Inc.", "company"),
    ("JPM", "JPMorgan Chase & Co.", "company"),
    ("JNJ", "Johnson & Johnson", "company"),
    ("XOM", "Exxon Mobil Corp.", "company"),
    ("V", "Visa Inc.", "stock"),
    ("VOO", "Vanguard S&P 500 ETF", "etf"),
    ("IWM", "iShares Russell 2000 ETF", "etf"),
    ("DIA", "SPDR Dow Jones Industrial Average ETF", "index"),
    ("TLT", "iShares 20+ Year Treasury Bond ETF", "economy"),
    ("IAU", "iShares Gold Trust", "gold"),
    ("ETH-USD", "Ethereum", "bitcoin"),
    ("XLE", "Energy Select Sector SPDR Fund", "sector"),
    ("XLK", "Technology Select Sector SPDR Fund", "sector"),
]

DEFAULT_DISCOVERY_TOP_N = 10


def compute_asset_discovery_candidates(
    watchlist: list[WatchlistEntry],
    provider: MarketDataProvider,
    *,
    timeframe: str = "1d",
    limit: int = 200,
    method: TrendDefinitionMethod = "endpoint_slope",
    top_n: int = DEFAULT_DISCOVERY_TOP_N,
) -> list[SymbolTrendRanking]:
    """Real cross-sectional trend evidence over the discovery universe
    minus whatever's already on the CEO's own watchlist — a symbol the
    CEO already added is already covered by the existing
    `/trend-engine/cross-sectional` endpoint and would be a confusing
    duplicate here. Sorted by the same real composite score
    `rank_symbols_by_trend()` always uses, capped to `top_n` so this
    reads as a genuine shortlist, not a full 13-row dump every call."""
    already_watched = {entry.symbol for entry in watchlist}
    undiscovered = [(symbol, category) for symbol, _name, category in DISCOVERY_SYMBOL_POOL if symbol not in already_watched]
    symbol_candles = {symbol: provider.get_candles(symbol, timeframe, limit) for symbol, _category in undiscovered}
    category_by_symbol: dict[str, ResearchCategory] = {symbol: category for symbol, category in undiscovered}  # type: ignore[misc]
    rankings = rank_symbols_by_trend(symbol_candles, category_by_symbol, method=method, timeframe=timeframe)
    return rankings[:top_n]
