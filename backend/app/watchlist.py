"""WatchlistManager — the symbols TradeTown is currently tracking.

Price data always comes from app.market_data's configured provider (mock
in v0.3 — see that module's docstring); this module never calls a network
API directly, so swapping the provider later doesn't touch this file.
"""
from __future__ import annotations

from app.market_data import MarketDataProvider
from app.schemas import ResearchItem, WatchlistEntry

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


def default_watchlist() -> list[WatchlistEntry]:
    return [
        WatchlistEntry(symbol=symbol, name=name, lastPrice=0.0, dailyChangePct=0.0, status="queued", researchProgress=0.0, assignedAgent=None)
        for symbol, name, _category in SEED_SYMBOLS
    ]


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
