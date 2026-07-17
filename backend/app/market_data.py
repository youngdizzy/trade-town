"""Market data abstraction layer.

TradeTown v0.3 adds research on realistic-looking market symbols, but does
not call any real market data API and does not trade (see the v0.3 brief's
"STOP CONDITION" and app/research.py). This module exists so a *real*
provider can be dropped in later without touching anything that consumes
quotes (WatchlistManager/ResearchManager, see watchlist.py/research.py):
implement MarketDataProvider and wire it up in `_select_provider()` below.

`_select_provider()` picks the provider from the MARKET_DATA_PROVIDER env
var. Only "mock" is implemented in v0.3 — no real adapters ship yet, and
this repo holds no API keys — so any other value falls back to mock with a
warning rather than failing startup.
"""
from __future__ import annotations

import hashlib
import logging
import os
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass

logger = logging.getLogger("tradetown.market_data")


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: float
    change_pct: float


class MarketDataProvider(ABC):
    """Adapter interface. A real implementation (Polygon, Finnhub, Alpha
    Vantage, Yahoo Finance, Charles Schwab, ...) would wrap that vendor's
    HTTP client behind this same shape — WatchlistManager only ever calls
    `get_quotes()`, so nothing downstream needs to change when a real
    adapter replaces the mock."""

    @abstractmethod
    def get_quote(self, symbol: str) -> Quote: ...

    def get_quotes(self, symbols: list[str]) -> dict[str, Quote]:
        return {symbol: self.get_quote(symbol) for symbol in symbols}


class MockMarketDataProvider(MarketDataProvider):
    """Deterministic-seeded random walk, no network calls. Each symbol
    starts from a price derived from its own hash (so the starting point
    for a given symbol is stable across process restarts) and drifts by a
    small percentage on every call, so a live-watched watchlist sees
    prices move without ever hitting the network."""

    def __init__(self) -> None:
        self._prices: dict[str, float] = {}

    @staticmethod
    def _seed_price(symbol: str) -> float:
        digest = hashlib.sha256(symbol.encode()).hexdigest()
        return 20 + (int(digest[:8], 16) % 48000) / 100  # roughly $20-$500

    def get_quote(self, symbol: str) -> Quote:
        previous = self._prices.get(symbol, self._seed_price(symbol))
        change_pct = random.uniform(-1.5, 1.5)
        price = max(0.5, previous * (1 + change_pct / 100))
        self._prices[symbol] = price
        return Quote(symbol=symbol, price=round(price, 2), change_pct=round(change_pct, 2))


def _select_provider() -> MarketDataProvider:
    name = os.environ.get("MARKET_DATA_PROVIDER", "mock").strip().lower()
    if name not in ("", "mock"):
        logger.warning("MARKET_DATA_PROVIDER=%r has no real adapter in v0.3; falling back to mock data.", name)
    return MockMarketDataProvider()


market_data_provider: MarketDataProvider = _select_provider()
