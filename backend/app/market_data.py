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

CEO Company Health + Live Market Realism directive — the mock generator
was, until this pass, an independent uniform-random draw per bar: no
volatility clustering, no trend persistence, no mean reversion, and no
link to the real regime app/market_environment.py already computes from
this same provider's own quote walk. `_generate_walk()` below replaces
that with a real regime-switching stochastic process (an internal
trend_up/trend_down/range/volatile state machine with realistic segment
lengths), a GARCH(1,1)-style volatility recurrence (today's volatility
depends on yesterday's realized shock and volatility, not an independent
draw — real clustering), and an AR(1) momentum term (today's drift
partially carries over yesterday's realized move — real trend
persistence), plus mean reversion whose strength depends on the current
internal regime (strong while "range", weak while trending). This is a
disclosed simplification, not a real calibrated financial model — the
constants below are chosen to *look and behave* like a real market
(volatility clustering, momentum, consolidation, breakouts), not fit to
any real historical distribution, since this codebase has no real market
data to fit to.

Two-way regime coupling: `set_market_regime()` receives the real,
already-computed `MarketEnvironmentState.current` once per tick (see
app/nexus.py) and biases which internal regime this generator favors
next — for `get_quote()`'s live walk on every call, and for
`get_candles()`'s freshly-regenerated series only on its most recent
`RECENT_REGIME_BIAS_WINDOW` bars (the "right edge" of the chart, i.e.
what the market is doing *right now* — see that constant's own docstring
for why the older portion of a regenerated series is deliberately left
unbiased). Price already drives the real regime classification
(app/market_environment.py's `evaluate_market_environment()`, unchanged);
this is the other real direction of that same real feedback loop —
never a fabricated third regime reading, and never forcing an outcome:
the external regime only re-weights which internal regime gets picked, so per-symbol
variation still exists inside one real aggregate regime.
"""
from __future__ import annotations

import hashlib
import logging
import math
import os
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

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

    def set_market_regime(self, regime: str | None) -> None:
        """Optional real-regime feedback hook (see MockMarketDataProvider's
        own docstring) — a no-op default so a future real adapter, which
        gets its regime from the real market itself rather than needing
        this codebase to tell it, doesn't have to implement it."""
        return None


NORMAL_VOLUME_RANGE = (100_000.0, 800_000.0)
VOLUME_SPIKE_CHANCE = 0.08
VOLUME_SPIKE_MULTIPLIER_RANGE = (3.0, 6.0)

InternalRegime = Literal["trend_up", "trend_down", "range", "volatile"]
_INTERNAL_REGIMES: tuple[InternalRegime, ...] = ("trend_up", "trend_down", "range", "volatile")

# Per-bar drift (mean %, std %) at a 1-hour-equivalent baseline; scaled by
# real timeframe granularity in `_generate_walk()` via `time_scale`.
_REGIME_DRIFT_PCT: dict[InternalRegime, tuple[float, float]] = {
    "trend_up": (0.18, 0.12),
    "trend_down": (-0.18, 0.12),
    "range": (0.0, 0.05),
    "volatile": (0.0, 0.10),
}
_REGIME_VOL_MULTIPLIER: dict[InternalRegime, float] = {"trend_up": 1.0, "trend_down": 1.0, "range": 0.55, "volatile": 2.4}
_REGIME_MEAN_REVERSION: dict[InternalRegime, float] = {"trend_up": 0.015, "trend_down": 0.015, "range": 0.12, "volatile": 0.02}
# How many bars one internal regime segment lasts before the generator
# re-rolls — real consolidation/trend runs, not a bar-by-bar coin flip.
_REGIME_DURATION_BARS = (12, 55)

# Real aggregate-regime -> internal-regime bias weights. Never a forced
# outcome (every internal regime keeps nonzero weight even under a
# strong external bias), so per-symbol variation is preserved.
_EXTERNAL_REGIME_WEIGHTS: dict[str, dict[InternalRegime, float]] = {
    "bull": {"trend_up": 0.50, "trend_down": 0.05, "range": 0.30, "volatile": 0.15},
    "bear": {"trend_up": 0.05, "trend_down": 0.50, "range": 0.30, "volatile": 0.15},
    "high_volatility": {"trend_up": 0.20, "trend_down": 0.20, "range": 0.10, "volatile": 0.50},
    "low_volatility": {"trend_up": 0.15, "trend_down": 0.15, "range": 0.60, "volatile": 0.10},
    "sideways": {"trend_up": 0.15, "trend_down": 0.15, "range": 0.55, "volatile": 0.15},
}
_NEUTRAL_REGIME_WEIGHTS: dict[InternalRegime, float] = {"trend_up": 0.25, "trend_down": 0.25, "range": 0.35, "volatile": 0.15}

# `get_candles()` regenerates its whole requested series fresh on every
# call (see `test_historical_candles_are_stable_across_repeated_calls`
# — a chart the player reopens must not reshuffle its own history), so
# the real external regime can only honestly bias bars that represent
# "recent/current" market behavior, not bars deep in an already-settled
# history — biasing the whole series would mean a regime flip elsewhere
# in the game silently rewrites yesterday's candles, which is not how a
# real market's history works. Only the newest RECENT_REGIME_BIAS_WINDOW
# bars (the chart's right edge) read the live external bias; everything
# before that uses the symbol's own internal, seed-deterministic regime
# sequence.
RECENT_REGIME_BIAS_WINDOW = 20

# GARCH(1,1)-style volatility clustering: variance_t = omega + alpha *
# shock_{t-1}^2 + beta * variance_{t-1}. Game-flavor constants (alpha +
# beta < 1 for stationarity), not fit to any real historical series —
# this codebase has none to fit to.
_GARCH_OMEGA = 0.00015
_GARCH_ALPHA = 0.12
_GARCH_BETA = 0.82
_VOL_FLOOR = 0.15
_VOL_CEILING = 6.0

# AR(1) momentum persistence — today's drift term partially carries over
# yesterday's realized shock, so moves aren't independent draws.
_DRIFT_DECAY = 0.80
_MEAN_ANCHOR_SMOOTHING = 0.04


def _pick_regime(rng: random.Random, weights: dict[InternalRegime, float]) -> InternalRegime:
    total = sum(weights.values())
    roll = rng.uniform(0.0, total)
    upto = 0.0
    for regime in _INTERNAL_REGIMES:
        upto += weights.get(regime, 0.0)
        if roll <= upto:
            return regime
    return _INTERNAL_REGIMES[-1]


@dataclass
class _WalkState:
    """The real, evolving state one regime-switching price process needs
    to carry between steps — shared shape for both get_quote()'s
    persistent per-symbol live walk and get_candles()'s per-call
    regenerated series."""

    price: float
    anchor: float = 0.0
    vol: float = 1.0
    drift: float = 0.0
    prev_shock: float = 0.0
    regime: InternalRegime = "range"
    regime_bars_left: int = 0

    def __post_init__(self) -> None:
        if self.anchor == 0.0:
            self.anchor = self.price


def _step(state: _WalkState, rng: random.Random, *, time_scale: float, external_regime: str | None, apply_bias: bool) -> float:
    """Advances `state` by exactly one bar in place and returns the
    realized %% shock for that bar — the one real step function shared
    by the live quote walk and the historical series generator, so both
    exhibit the identical real volatility-clustering/momentum/mean-
    reversion/regime-switching behavior rather than two divergent
    implementations of "realistic-looking noise"."""
    if state.regime_bars_left <= 0:
        weights = _EXTERNAL_REGIME_WEIGHTS.get(external_regime or "", _NEUTRAL_REGIME_WEIGHTS) if (apply_bias and external_regime) else _NEUTRAL_REGIME_WEIGHTS
        state.regime = _pick_regime(rng, weights)
        state.regime_bars_left = rng.randint(*_REGIME_DURATION_BARS)

    variance = _GARCH_OMEGA + _GARCH_ALPHA * (state.prev_shock**2) + _GARCH_BETA * (state.vol**2)
    state.vol = max(_VOL_FLOOR, min(_VOL_CEILING, math.sqrt(variance)))

    mean, std = _REGIME_DRIFT_PCT[state.regime]
    regime_vol = std * _REGIME_VOL_MULTIPLIER[state.regime] * state.vol * time_scale

    state.drift = _DRIFT_DECAY * state.drift + (1 - _DRIFT_DECAY) * state.prev_shock
    reversion = -_REGIME_MEAN_REVERSION[state.regime] * ((state.price - state.anchor) / state.anchor * 100) if state.anchor else 0.0

    shock = rng.gauss(mean * time_scale, max(0.01, regime_vol)) + state.drift * 0.3 + reversion
    new_price = max(0.5, state.price * (1 + shock / 100))

    state.anchor = state.anchor * (1 - _MEAN_ANCHOR_SMOOTHING) + new_price * _MEAN_ANCHOR_SMOOTHING
    state.prev_shock = shock
    state.price = new_price
    state.regime_bars_left -= 1
    return shock


def _volume_for_shock(rng: random.Random, shock_pct: float, regime: InternalRegime) -> float:
    base_volume = rng.uniform(*NORMAL_VOLUME_RANGE)
    spike_chance = VOLUME_SPIKE_CHANCE * (2.2 if abs(shock_pct) > 1.0 else 1.0) * (1.6 if regime == "volatile" else 1.0)
    if rng.random() < spike_chance:
        base_volume *= rng.uniform(*VOLUME_SPIKE_MULTIPLIER_RANGE)
    return base_volume


class MockMarketDataProvider(MarketDataProvider):
    """A real regime-switching stochastic process (volatility clustering
    + momentum persistence + mean reversion + internal regime-switching,
    see this module's own docstring), no network calls. Each symbol
    starts from a price derived from its own hash (so the starting point
    for a given symbol is stable across process restarts)."""

    def __init__(self) -> None:
        self._prices: dict[str, float] = {}
        self._quote_states: dict[str, _WalkState] = {}
        # `random.Random()` with no seed — genuinely non-deterministic
        # across process runs, the same intentional live-quote behavior
        # the prior shared-`random`-module implementation already had.
        self._quote_rng = random.Random()
        self._current_external_regime: str | None = None

    def set_market_regime(self, regime: str | None) -> None:
        """CEO Company Health + Live Market Realism directive — see this
        module's own docstring for the full real two-way coupling this
        enables. Called once per tick from app/nexus.py with the real,
        already-computed `MarketEnvironmentState.current`."""
        self._current_external_regime = regime

    @staticmethod
    def _seed_price(symbol: str) -> float:
        digest = hashlib.sha256(symbol.encode()).hexdigest()
        return 20 + (int(digest[:8], 16) % 48000) / 100  # roughly $20-$500

    def get_quote(self, symbol: str) -> Quote:
        state = self._quote_states.get(symbol)
        if state is None:
            state = _WalkState(price=self._seed_price(symbol))
            self._quote_states[symbol] = state

        shock = _step(state, self._quote_rng, time_scale=1.0, external_regime=self._current_external_regime, apply_bias=True)
        volume = _volume_for_shock(self._quote_rng, shock, state.regime)
        self._prices[symbol] = state.price

        return Quote(symbol=symbol, price=round(state.price, 2), change_pct=round(shock, 2), volume=round(volume, 0))

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

        # Always starts from the symbol's fixed original seed price, not
        # the live get_quote() price — the walk below is a deterministic
        # `limit`-bar simulation *forward* from that anchor, so anchoring
        # its starting point to the live price would only place the live
        # price `limit` steps in the past, leaving the *newest* (rightmost)
        # bar exactly as far from reality as before. Continuity with the
        # live price is instead restored after the loop by proportionally
        # rescaling the whole series (see below) — that preserves every
        # bar's real relative shape/volatility (percentage moves are
        # scale-invariant) while landing exactly on the live price.
        state = _WalkState(price=self._seed_price(symbol))
        time_scale = math.sqrt(max(1.0, minutes_per_candle) / 60.0)
        now = datetime.now(timezone.utc)
        candles: list[Candle] = []
        for i in range(limit):
            open_price = state.price
            apply_bias = i >= limit - RECENT_REGIME_BIAS_WINDOW
            shock = _step(state, rng, time_scale=time_scale, external_regime=self._current_external_regime, apply_bias=apply_bias)
            close_price = state.price

            wick_scale = abs(shock) / 100 * open_price + 0.001 * open_price
            wick_up = abs(rng.gauss(0, wick_scale * 0.6))
            wick_down = abs(rng.gauss(0, wick_scale * 0.6))
            high = max(open_price, close_price) + wick_up
            low = max(0.1, min(open_price, close_price) - wick_down)
            volume = _volume_for_shock(rng, shock, state.regime)

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

        # Rescale the whole series so it lands exactly on get_quote()'s
        # live mock price at the newest bar, if one exists — keeps the
        # chart continuous with the same price the watchlist/opportunity
        # cards are showing, rather than two independently-random numbers
        # that happen to both be labeled the same symbol. A proportional
        # rescale (every OHLC value in every bar multiplied by the same
        # factor) is used instead of only patching the last candle: since
        # percentage moves are scale-invariant, this preserves every bar's
        # real relative shape/volatility/wick proportions exactly, and
        # produces zero discontinuity anywhere in the series — not just at
        # the rightmost edge.
        if candles and symbol in self._prices and candles[-1].close:
            scale = self._prices[symbol] / candles[-1].close
            if scale != 1.0:
                candles = [
                    Candle(
                        symbol=c.symbol,
                        timeframe=c.timeframe,
                        timestamp=c.timestamp,
                        open=round(c.open * scale, 2),
                        high=round(c.high * scale, 2),
                        low=round(c.low * scale, 2),
                        close=round(c.close * scale, 2),
                        volume=c.volume,
                        data_status="simulated",
                    )
                    for c in candles
                ]
            # Rounding after rescale can leave the final close a cent or
            # two off the live price; force an exact match on just that
            # one field so the chart's rightmost point is bit-for-bit
            # identical to what get_quote() reports elsewhere in the UI.
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
