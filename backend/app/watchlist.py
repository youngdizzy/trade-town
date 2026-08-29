"""WatchlistManager — the symbols TradeTown is currently tracking.

Price data always comes from app.market_data's configured provider (mock
in v0.3 — see that module's docstring); this module never calls a network
API directly, so swapping the provider later doesn't touch this file.
"""
from __future__ import annotations

from app.market_data import MarketDataProvider
from app.schemas import ResearchCategory, ResearchItem, WatchlistEntry

# (symbol, display name, research category) — one per ResearchCategory in
# the v0.3 brief, and also the pool research.py rotates agents through.
SEED_SYMBOLS: list[tuple[str, str, str]] = [
    ("AAPL", "Apple Inc.", "company"),
    ("MSFT", "Microsoft Corp.", "stock"),
    ("SPY", "S&P 500 ETF Trust", "index"),
    ("QQQ", "Invesco QQQ Trust", "etf"),
    ("GLD", "SPDR Gold Shares", "gold"),
    ("BTC-USD", "Bitcoin", "bitcoin"),
    ("XLF", "Financial Sector SPDR", "sector"),
    ("DXY", "US Dollar Index", "economy"),
]

# A separate pool from SEED_SYMBOLS, only ever added to the watchlist via
# the Agent Energy "watch_symbol" spend (see app/agent_energy.py and
# app/nexus.py's apply_energy_action) — "monitoring additional assets"
# beyond the default eight. Genuinely monitored: tick_watchlist() below
# refreshes price/change for every symbol on the list, seed or added,
# every tick, the same way. Professional Quant Trading Core Phase A/C —
# these symbols now also reach research.py's rotation (see that
# module's own _next_symbol(), which draws from whatever's actually on
# the current watchlist rather than the fixed SEED_SYMBOLS constant),
# closing what used to be an honestly-disclosed gap: an added symbol
# got real live price tracking but never an assigned researcher, so it
# could never produce a ResearchItem or, downstream, a TradeProposal.
EXTRA_SYMBOL_POOL: list[tuple[str, str, str]] = [
    ("AMZN", "Amazon.com Inc.", "company"),
    ("GOOGL", "Alphabet Inc.", "company"),
    ("TSLA", "Tesla Inc.", "company"),
    ("NVDA", "NVIDIA Corp.", "company"),
    ("SLV", "iShares Silver Trust", "gold"),
    ("USO", "United States Oil Fund", "sector"),
    # CEO directive "AHL-Inspired Systematic Trend & Momentum Research
    # Engine" follow-up — a prior audit pass labeled futures/FX/Treasury
    # asset classes a hard blocker ("no data feeds exist"); re-audited
    # and found the opposite — every symbol on this pool already trades
    # on app/market_data.py's own fully synthetic (mock) process, so no
    # real feed was ever required for ANY category here. Yahoo-style
    # naming convention ("=F" futures, "=X" FX) so app/market_data.py's
    # own `_SEED_PRICE_OVERRIDE` can give each a realistic real starting
    # PRICE LEVEL (see that dict's own docstring) without needing a
    # category lookup (which would create a circular import back into
    # this module). Per-asset-class VOLATILITY calibration is NOT
    # attempted — a real, disclosed, separate lift.
    ("ES=F", "E-mini S&P 500 Futures", "futures"),
    ("CL=F", "Crude Oil Futures", "futures"),
    ("ZN=F", "10-Year T-Note Futures", "treasury"),
    ("EURUSD=X", "Euro / US Dollar", "fx"),
    ("GBPUSD=X", "British Pound / US Dollar", "fx"),
]

# Every symbol this codebase knows a category for, seed tier plus extra
# tier — the real pool research.py's rotation now draws from (filtered,
# per tick, down to whatever's actually on the current watchlist).
ALL_SYMBOL_POOL: list[tuple[str, str, str]] = [*SEED_SYMBOLS, *EXTRA_SYMBOL_POOL]

# v0.7 Feature 20 — the Trade Gatekeeper's "correlated positions" check
# needs a symbol -> category lookup; this is that same real mapping
# SEED_SYMBOLS/EXTRA_SYMBOL_POOL already define, not a second invented
# taxonomy. Covers EXTRA_SYMBOL_POOL too (not just SEED_SYMBOLS) so a
# correlation check against one of those symbols, once it can actually
# hold a position, isn't silently treated as "no category."
SYMBOL_CATEGORY: dict[str, ResearchCategory] = {symbol: category for symbol, _name, category in ALL_SYMBOL_POOL}  # type: ignore[misc]


def default_watchlist() -> list[WatchlistEntry]:
    return [
        WatchlistEntry(symbol=symbol, name=name, lastPrice=0.0, dailyChangePct=0.0, status="queued", researchProgress=0.0, assignedAgent=None)
        for symbol, name, _category in SEED_SYMBOLS
    ]


def add_symbol_to_watchlist(watchlist: list[WatchlistEntry], provider: MarketDataProvider) -> tuple[list[WatchlistEntry], str] | None:
    """Returns (new_watchlist, symbol_added) or None if every symbol in the
    pool is already being monitored."""
    already = {entry.symbol for entry in watchlist}
    candidates = [s for s in EXTRA_SYMBOL_POOL if s[0] not in already]
    if not candidates:
        return None
    symbol, name, _category = candidates[0]
    quote = provider.get_quote(symbol)
    entry = WatchlistEntry(
        symbol=symbol, name=name, lastPrice=quote.price, dailyChangePct=quote.change_pct, status="queued", researchProgress=0.0, assignedAgent=None
    )
    return [*watchlist, entry], symbol


def tick_watchlist(watchlist: list[WatchlistEntry], research: list[ResearchItem], provider: MarketDataProvider) -> list[WatchlistEntry]:
    """Refreshes prices from the market data provider and syncs each
    entry's status/progress/assignedAgent from whichever ResearchItem (if
    any) currently targets that symbol."""
    quotes = provider.get_quotes([entry.symbol for entry in watchlist])
    active_by_symbol = {item.symbol: item for item in research if item.symbol is not None}

    updated: list[WatchlistEntry] = []
    for entry in watchlist:
        quote = quotes[entry.symbol]
        item = active_by_symbol.get(entry.symbol)
        updated.append(
            entry.model_copy(
                update={
                    "last_price": quote.price,
                    "daily_change_pct": quote.change_pct,
                    "status": item.status if item else entry.status,
                    "research_progress": item.confidence if item else entry.research_progress,
                    "assigned_agent": item.assigned_agent if item else None,
                }
            )
        )
    return updated
