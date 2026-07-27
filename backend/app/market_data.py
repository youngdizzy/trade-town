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
from datetime import datetime, timedelta, timezone

from app.schemas import DataStatus

logger = logging.getLogger("tradetown.market_data")

# (label, minutes per candle). Ordered coarsest-informative-first for
# UI display purposes; TIMEFRAMES (the dict form) is what code should
# actually index into.
TIMEFRAME_ORDER: list[str] = ["1m", "5m", "15m", "1h", "4h", "1d"]
TIMEFRAMES: dict[str, int] = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: float
    change_pct: float
    # Added in v0.6 for app/scanner.py's volume-spike detection — a real
    # provider naturally exposes this alongside price; the mock below
    # synthesizes a plausible value since there's no real feed.
    volume: float = 0.0


@dataclass(frozen=True)
class Candle:
    """One OHLC bar, normalized the same way regardless of which
    provider produced it — see the v0.6.2 brief's "Market Data
    Abstraction" section. `timestamp` is a real ISO-8601 wall-clock
    time (not a simulated-clock value — see app/schemas.py's PaperTrade
    for why this codebase keeps those two concepts distinct), because a
    chart's x-axis is about *when this data point represents*, not
    TradeTown's in-game calendar."""

    symbol: str
    timeframe: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    data_status: DataStatus


def trend_pct(candles: list[Candle]) -> float:
    """% change from the sample's first close to its last — a real,
    unambiguous technical signal shared by both app/signal_calibration.py
    and app/player_vs_ai.py so they read "trend" the same way rather
    than each rolling a slightly different definition."""
    if len(candles) < 2 or candles[0].close == 0:
        return 0.0
    return (candles[-1].close - candles[0].close) / candles[0].close * 100


def volatility_pct(candles: list[Candle]) -> float:
    """Average per-bar (high-low) range as a % of close — a simple, real
    stand-in for realized volatility, computed only from the visible
    sample. Shared by signal_calibration.py and player_vs_ai.py."""
    if not candles:
        return 0.0
    ranges = [(c.high - c.low) / c.close * 100 for c in candles if c.close]
    return sum(ranges) / len(ranges) if ranges else 0.0


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

    @abstractmethod
    def get_candles(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        """Oldest-first. Raises ValueError for a timeframe this provider
        doesn't support — callers (see app/routers/market.py) turn that
        into a 400 rather than silently substituting a different
        timeframe, per the brief's "only show timeframes actually
        supported by the data provider"."""
        ...


NORMAL_VOLUME_RANGE = (100_000.0, 800_000.0)
VOLUME_SPIKE_CHANCE = 0.08
VOLUME_SPIKE_MULTIPLIER_RANGE = (3.0, 6.0)


class MockMarketDataProvider(MarketDataProvider):
    """Deterministic-seeded random walk, no network calls. Each symbol
    starts from a price derived from its own hash (so the starting point
    for a given symbol is stable across process restarts) and drifts by a
    small percentage on every call, so a live-watched watchlist sees
    prices move without ever hitting the network. Volume is a plain
    random baseline that occasionally spikes (VOLUME_SPIKE_CHANCE),
    biased slightly toward spiking alongside a larger price move so
    app/scanner.py's volume-spike and breakout signals correlate the way
    a real market's would, without needing real trade-tape data."""

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

        volume = random.uniform(*NORMAL_VOLUME_RANGE)
        spike_chance = VOLUME_SPIKE_CHANCE * (2.0 if abs(change_pct) > 1.0 else 1.0)
        if random.random() < spike_chance:
            volume *= random.uniform(*VOLUME_SPIKE_MULTIPLIER_RANGE)

        return Quote(symbol=symbol, price=round(price, 2), change_pct=round(change_pct, 2), volume=round(volume, 0))

    def get_candles(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        if timeframe not in TIMEFRAMES:
            raise ValueError(f"Unsupported timeframe {timeframe!r}; supported: {TIMEFRAME_ORDER}")
        minutes_per_candle = TIMEFRAMES[timeframe]

        # A dedicated RNG instance (not the shared `random` module) seeded
        # from (symbol, timeframe) only — deliberately NOT from wall-clock
        # time — so the historical portion of the series is stable across
        # repeated fetches (a chart the player reopens shouldn't reshuffle
        # its own history), while still being a different, independent
        # walk per symbol and per timeframe.
        seed_digest = hashlib.sha256(f"{symbol}:{timeframe}".encode()).hexdigest()
        rng = random.Random(int(seed_digest[:16], 16))

        price = self._seed_price(symbol)
        now = datetime.now(timezone.utc)
        candles: list[Candle] = []
        for i in range(limit):
            open_price = price
            move_pct = rng.uniform(-1.2, 1.2)
            close_price = max(0.5, open_price * (1 + move_pct / 100))
            wick_up = abs(rng.uniform(0, 0.6)) / 100 * open_price
            wick_down = abs(rng.uniform(0, 0.6)) / 100 * open_price
            high = max(open_price, close_price) + wick_up
            low = max(0.1, min(open_price, close_price) - wick_down)
            volume = rng.uniform(*NORMAL_VOLUME_RANGE)
            timestamp = (now - timedelta(minutes=minutes_per_candle * (limit - 1 - i))).isoformat()
            candles.append(
                Candle(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=timestamp,
                    open=round(open_price, 2),
                    high=round(high, 2),
                    low=round(low, 2),
                    close=round(close_price, 2),
                    volume=round(volume, 0),
                    data_status="simulated",
                )
            )
            price = close_price

        # The most recent bar's close tracks whatever get_quote() has
        # already established as this symbol's live mock price, if any —
        # keeps the chart's rightmost candle roughly consistent with the
        # same price the watchlist/opportunity cards are showing, rather
        # than two independently-random numbers that happen to both be
        # labeled the same symbol.
        if candles and symbol in self._prices:
            last = candles[-1]
            live_close = round(self._prices[symbol], 2)
            candles[-1] = Candle(
                symbol=last.symbol,
                timeframe=last.timeframe,
                timestamp=last.timestamp,
                open=last.open,
                high=max(last.high, live_close),
                low=min(last.low, live_close),
                close=live_close,
                volume=last.volume,
                data_status="simulated",
            )
        return candles


def _select_provider() -> MarketDataProvider:
    name = os.environ.get("MARKET_DATA_PROVIDER", "mock").strip().lower()
    if name not in ("", "mock"):
        logger.warning("MARKET_DATA_PROVIDER=%r has no real adapter in v0.3; falling back to mock data.", name)
    return MockMarketDataProvider()


market_data_provider: MarketDataProvider = _select_provider()
