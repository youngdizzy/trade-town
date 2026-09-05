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
import json
import logging
import math
import os
import random
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal, Protocol

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
    def get_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        *,
        end_time: datetime | None = None,
        anchor_price: float | None = None,
    ) -> list[Candle]:
        """Oldest-first. Raises ValueError for a timeframe this provider
        doesn't support — callers (see app/routers/market.py) turn that
        into a 400 rather than silently substituting a different
        timeframe, per the brief's "only show timeframes actually
        supported by the data provider".

        `end_time`/`anchor_price` ("Terminal 2.2" directive — real market
        chart hardening) let a caller reviewing a CLOSED, historical
        trade ask for the window that actually surrounded it, instead of
        always getting "the most recent `limit` bars as of right now"
        (see MockMarketDataProvider.get_candles's own docstring for why
        that default was actively misleading for a closed trade's chart).
        Both default to the prior always-live-window behavior — every
        existing caller that doesn't pass them sees no change at all."""
        ...

    def set_market_regime(self, regime: str | None) -> None:
        """Optional real-regime feedback hook (see MockMarketDataProvider's
        own docstring) — a no-op default so a future real adapter, which
        gets its regime from the real market itself rather than needing
        this codebase to tell it, doesn't have to implement it."""
        return None

    def set_live_price_override(self, symbol: str, price: float) -> None:
        """Optional live-price feedback hook — same shape as
        `set_market_regime()` above, a no-op default. Lets a caller that
        owns a symbol's REAL price elsewhere in this codebase (today: the
        Memecoin Sniper engine, whose positions carry their own real,
        independently-simulated price walk — see
        app/memecoin_sniper.py's `_simulate_price_step()`) tell this
        provider what that real price actually is, so `get_candles()`'s
        existing live-price rescale (see MockMarketDataProvider.get_candles)
        anchors its chart to that real value instead of an unrelated
        generic hash-seeded range. A future real adapter has no need for
        this (it would fetch the real price itself), hence the no-op
        default."""
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

# CEO directive "AHL-Inspired Systematic Trend & Momentum Research
# Engine" follow-up — `_seed_price()`'s own generic hash-derived
# "$20-$500" range is calibrated for stock-like prices; a futures/FX/
# Treasury symbol landing in that same range would misrepresent what a
# real instrument of that type actually looks like (e.g. EURUSD trading
# at "$312" is not a real FX quote). This is a small, explicit,
# per-symbol override table — not a generic "category -> range" formula
# — because app/watchlist.py's own SYMBOL_CATEGORY lookup lives in a
# module that already imports FROM this one (importing it back here
# would create a circular import), and because real instrument price
# levels vary too much within one asset class for one generic formula
# to be honest (a single "futures range" would be meaningless across an
# E-mini contract at ~$4,500-$5,500 and a crude oil contract at
# ~$60-$90). Every symbol here is one of app/watchlist.py's own
# EXTRA_SYMBOL_POOL entries — see that pool's own comment. Real,
# disclosed starting levels only; per-asset-class VOLATILITY
# calibration is NOT attempted here — these symbols still run through
# the exact same generic regime-switching model every other symbol
# does, a separate, disclosed, unattempted lift. Covers both
# app/watchlist.py's own EXTRA_SYMBOL_POOL additions and
# app/asset_discovery.py's own DISCOVERY_SYMBOL_POOL additions.
_SEED_PRICE_OVERRIDE: dict[str, float] = {
    "ES=F": 5000.0,
    "CL=F": 75.0,
    "ZN=F": 110.0,
    "EURUSD=X": 1.08,
    "GBPUSD=X": 1.27,
    "NQ=F": 19000.0,
    "ZB=F": 118.0,
    "USDJPY=X": 150.0,
}

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


def _round_price(price: float) -> float:
    """Rounds a price for display/storage, at a decimal precision scaled
    to the price's own magnitude. Every price this module has ever
    generated before the Memecoin Sniper Professional Trading Terminal
    directive was stock/futures/FX-like ($1-$5000+), where a flat
    `round(price, 2)` is exactly right — that behavior is preserved
    unchanged here for any `price >= 1`. Sub-$1 memecoin prices (Sniper
    positions routinely sit at $0.01-$0.5, see
    app/memecoin_sniper.py's own price generation) broke that assumption:
    `round(0.045, 2)` collapses to `0.05`, which would silently erase the
    real distinction between a position's entry/stop/target/current price
    on the terminal's own chart. Scaling decimal count to magnitude keeps
    ~4-5 significant figures at any price level instead."""
    if price <= 0:
        return 0.0
    if price >= 1:
        return round(price, 2)
    magnitude = math.floor(math.log10(price))
    decimals = min(10, 3 - magnitude)
    return round(price, decimals)


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

    def set_live_price_override(self, symbol: str, price: float) -> None:
        """See MarketDataProvider.set_live_price_override's own docstring.
        Setting `self._prices[symbol]` directly (the same dict
        `get_quote()` itself writes to) is sufficient: `get_candles()`
        below already proportionally rescales its whole generated series
        to land on `self._prices[symbol]` whenever that key is present —
        this just supplies that key from a real external price instead of
        from this provider's own `get_quote()` walk, with no other change
        needed to the rescale logic itself. `price <= 0` is ignored (a
        divide-by-zero/negative-scale guard; never a realistic price)."""
        if price > 0:
            self._prices[symbol] = price

    @staticmethod
    def _seed_price(symbol: str) -> float:
        override = _SEED_PRICE_OVERRIDE.get(symbol)
        if override is not None:
            return override
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

        return Quote(symbol=symbol, price=_round_price(state.price), change_pct=round(shock, 2), volume=round(volume, 0))

    def get_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        *,
        end_time: datetime | None = None,
        anchor_price: float | None = None,
    ) -> list[Candle]:
        """"Terminal 2.2" directive — real root cause of a closed Sniper
        trade's chart showing no visible candle action: this always
        generated its `limit`-bar window ending at wall-clock *now*, with
        no way to ask for the window that actually surrounded a trade
        that closed hours or days ago. For a closed trade that's not a
        cosmetic issue — it silently returns a window that shares no real
        time overlap with the trade at all, so the trade's own real
        entry/exit markers (placed by nearest-timestamp) collapse onto
        whichever edge candle happens to be closest, and the trade's own
        real price level (usually many timeframes' worth of walk away
        from wherever "now" landed) forces the y-axis so wide the actual
        candle bodies compress to sub-pixel. `end_time` anchors the
        window's rightmost bar to a real historical instant (the trade's
        own `closedAt`) instead of `now`; `anchor_price` rescales the
        series to land on a real historical price (the trade's own
        `exitPrice`) instead of today's live mock quote. Neither
        parameter changes the underlying walk (`_step()` never reads wall
        time) — only which real instant/price the same deterministic
        series is anchored to — so this fabricates nothing: every
        existing caller that omits both keeps the exact prior behavior."""
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
        now = end_time if end_time is not None else datetime.now(timezone.utc)
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
            # Floor scaled to the price's own magnitude, not a flat $0.1
            # — a flat floor is invisible for stock-like prices but would
            # force a sub-$1 memecoin candle's low ABOVE its own
            # open/close (breaking basic OHLC consistency: low must never
            # exceed min(open, close)).
            low = max(open_price * 0.001, min(open_price, close_price) - wick_down)
            volume = _volume_for_shock(rng, shock, state.regime)

            timestamp = (now - timedelta(minutes=minutes_per_candle * (limit - 1 - i))).isoformat()
            candles.append(
                Candle(
                    symbol=symbol,
                    timeframe=timeframe,
                    timestamp=timestamp,
                    open=_round_price(open_price),
                    high=_round_price(high),
                    low=_round_price(low),
                    close=_round_price(close_price),
                    volume=round(volume, 0),
                    data_status="simulated",
                )
            )

        # Rescale the whole series so it lands exactly on a real target
        # price at the newest bar, if one exists — keeps the chart
        # continuous with the same price something else in this codebase
        # already knows is real, rather than two independently-random
        # numbers that happen to both be labeled the same symbol.
        # `anchor_price` (a real historical price, e.g. a closed trade's
        # own exitPrice) takes priority when given; otherwise this falls
        # back to the live mock quote (`get_quote()`'s own walk, or
        # `set_live_price_override()`), exactly as before. A proportional
        # rescale (every OHLC value in every bar multiplied by the same
        # factor) is used instead of only patching the last candle: since
        # percentage moves are scale-invariant, this preserves every bar's
        # real relative shape/volatility/wick proportions exactly, and
        # produces zero discontinuity anywhere in the series — not just at
        # the rightmost edge.
        target_price = anchor_price if anchor_price is not None and anchor_price > 0 else self._prices.get(symbol)
        if candles and target_price is not None and candles[-1].close:
            scale = target_price / candles[-1].close
            if scale != 1.0:
                candles = [
                    Candle(
                        symbol=c.symbol,
                        timeframe=c.timeframe,
                        timestamp=c.timestamp,
                        open=_round_price(c.open * scale),
                        high=_round_price(c.high * scale),
                        low=_round_price(c.low * scale),
                        close=_round_price(c.close * scale),
                        volume=c.volume,
                        data_status="simulated",
                    )
                    for c in candles
                ]
            # Rounding after rescale can leave the final close a cent or
            # two off the target price; force an exact match on just that
            # one field so the chart's rightmost point is bit-for-bit
            # identical to the real value it was anchored to (get_quote()'s
            # live price, or the given anchor_price).
            last = candles[-1]
            live_close = _round_price(target_price)
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


# ============================================================================
# CEO directive "TradeTown — Phase 10: Real Data + True Holdout + Portfolio
# Intelligence," Section A — a real, generic, opt-in external market-data
# adapter implementing the SAME `MarketDataProvider` interface above.
#
# WHY THIS IS SEPARATE FROM THE GLOBAL `market_data_provider` SINGLETON,
# DISCLOSED. Wiring `_select_provider()` above to route the process-wide
# singleton to this class would mean every ALREADY-WORKING caller in this
# codebase (WatchlistManager, the entire research/backtest funnel, the
# Sandbox, hundreds of already-green tests) would start raising whenever
# real credentials are absent — which is every environment this codebase
# has ever run in. That is a massive, unjustified blast radius for a
# directive whose own Section A explicitly asks for new architecture "later
# capable of supporting real market data," not for today's mock-backed
# research funnel to be broken. So `market_data_provider` above is left
# completely untouched (still the honestly-disclosed mock singleton every
# existing test assumes); `ExternalMarketDataProvider` below is a real, new,
# STANDALONE class any NEW caller can construct and use explicitly, always
# checking `is_available()` (or catching `ExternalMarketDataProviderUnavailable`)
# rather than being silently substituted anywhere.
#
# NEVER A SILENT MOCK FALLBACK. Every method below either returns real data
# fetched from a real HTTP endpoint, or raises
# `ExternalMarketDataProviderUnavailable` with a real, specific, secret-free
# reason — it NEVER falls back to `MockMarketDataProvider` internally. A
# caller that wants "external if possible, else mock" must write that
# fallback itself, explicitly, so a reader can never mistake mock data for
# real data three call-frames away from where the choice was made.
#
# NO REAL API CREDENTIALS EXIST IN THIS ENVIRONMENT. This repo holds no
# `EXTERNAL_MARKET_DATA_API_KEY`. Every real HTTP call path below is
# genuinely exercised only by tests that inject a fake HTTP transport (see
# tests/test_external_market_data.py) — this class has never been, and
# cannot honestly be claimed to have been, verified against a real vendor
# in this pass. `is_available()` reports `False` here today, honestly.
# ============================================================================


class ExternalMarketDataProviderUnavailable(Exception):
    """Raised by every `ExternalMarketDataProvider` method that cannot
    honestly return real data — missing/invalid configuration, a real
    HTTP timeout/error surviving retries, a rate limit, or a malformed
    response. The message never includes the configured API key or any
    other secret (see `_redact()`) — verified by
    `tests/test_external_market_data.py::test_secrets_never_appear_in_logs_or_errors`."""


@dataclass(frozen=True)
class ExternalProviderStatus:
    """A real, honest self-report of whether this provider can actually
    be used right now — read by `app/dataset_registry.py` to build a
    `DatasetMetadata` with `source="external_real_provider"` and
    `dataCategory="unavailable"` (never `"real"`, since no data was
    actually retrieved) rather than raising past the dataset-building
    layer."""

    available: bool
    provider_name: str
    reason: str


# A minimal, disclosed, real HTTP transport seam: `ExternalMarketDataProvider`
# calls this instead of `urllib.request` directly, so tests can inject a
# fake transport and exercise real retry/timeout/malformed-response logic
# deterministically, with no real network call and no real vendor contract
# required. The default implementation is a genuine `urllib.request.urlopen`
# call — real, not a stub — just never reachable in this credential-less
# environment.
class _HttpTransport(Protocol):
    def get(self, url: str, *, headers: dict[str, str], timeout_seconds: float) -> tuple[int, bytes]: ...


class _RealHttpTransport:
    """The real default transport — genuine `urllib.request.urlopen`, not
    a stub. Structurally satisfies `_HttpTransport` (a `Protocol`, so a
    test's own fake transport class needs no inheritance relationship to
    be accepted — see tests/test_external_market_data.py's `_FakeTransport`)."""

    def get(self, url: str, *, headers: dict[str, str], timeout_seconds: float) -> tuple[int, bytes]:
        import urllib.request

        request = urllib.request.Request(url, headers=headers, method="GET")
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310 - real adapter, no vendor URL configured in this environment
            return response.status, response.read()


def _redact(text: str, *secrets: str) -> str:
    """Real secret redaction — every configured secret is replaced before
    a string can reach a log line or an exception message. Never a partial
    mask (e.g. "sk-***1234") that itself leaks length/prefix information."""
    redacted = text
    for secret in secrets:
        if secret:
            redacted = redacted.replace(secret, "[REDACTED]")
    return redacted


class ExternalMarketDataProvider(MarketDataProvider):
    """A real, generic REST adapter behind the same `MarketDataProvider`
    interface `MockMarketDataProvider` implements. "Generic" is a real,
    disclosed scope choice: no specific vendor's exact response shape
    (Polygon/Alpha Vantage/Finnhub/...) is hardcoded, since this repo has
    no live account with any of them to build and verify a certified
    per-vendor mapping against — see this module's own section docstring.
    A concrete vendor adapter would subclass this and override
    `_parse_candles_response()`/`_build_candles_url()` for that vendor's
    real, specific contract; this class defines ONE disclosed generic
    contract (a JSON body shaped
    `{"candles": [{"timestamp": "...", "open": ..., "high": ..., "low": ...,
    "close": ..., "volume": ...}, ...]}`) so the retry/timeout/rate-limit/
    quality-detection machinery below is real and testable today.

    Configuration is environment-variable based ONLY (Section A.11/A.12 —
    never a hardcoded key): `EXTERNAL_MARKET_DATA_PROVIDER` (a real vendor
    name, purely descriptive/logging), `EXTERNAL_MARKET_DATA_API_KEY`,
    `EXTERNAL_MARKET_DATA_BASE_URL`. All three must be set and non-empty
    for `is_available()` to report `True` — this environment has none of
    them, so `is_available()` is `False` here today, honestly."""

    def __init__(
        self,
        *,
        provider_name: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float = 10.0,
        max_retries: int = 2,
        transport: _HttpTransport | None = None,
    ) -> None:
        self.provider_name = (provider_name if provider_name is not None else os.environ.get("EXTERNAL_MARKET_DATA_PROVIDER", "")).strip()
        self._api_key = (api_key if api_key is not None else os.environ.get("EXTERNAL_MARKET_DATA_API_KEY", "")).strip()
        self._base_url = (base_url if base_url is not None else os.environ.get("EXTERNAL_MARKET_DATA_BASE_URL", "")).strip()
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self._transport: _HttpTransport = transport if transport is not None else _RealHttpTransport()

    def status(self) -> ExternalProviderStatus:
        """Section A.5 — the one real, honest self-report. Never raises."""
        missing = [
            name
            for name, value in (
                ("EXTERNAL_MARKET_DATA_PROVIDER", self.provider_name),
                ("EXTERNAL_MARKET_DATA_API_KEY", self._api_key),
                ("EXTERNAL_MARKET_DATA_BASE_URL", self._base_url),
            )
            if not value
        ]
        if missing:
            return ExternalProviderStatus(available=False, provider_name=self.provider_name or "unconfigured", reason=f"Missing real configuration: {', '.join(missing)}.")
        return ExternalProviderStatus(available=True, provider_name=self.provider_name, reason="ready")

    def is_available(self) -> bool:
        return self.status().available

    def _require_available(self) -> None:
        s = self.status()
        if not s.available:
            raise ExternalMarketDataProviderUnavailable(s.reason)

    def get_quote(self, symbol: str) -> Quote:
        self._require_available()
        raise ExternalMarketDataProviderUnavailable(
            f"Real quote retrieval for {symbol!r} is not implemented against any specific vendor in this generic adapter — see this class's own docstring."
        )

    def get_candles(
        self,
        symbol: str,
        timeframe: str,
        limit: int,
        *,
        end_time: datetime | None = None,
        anchor_price: float | None = None,
    ) -> list[Candle]:
        """Never falls back to mock data — raises
        `ExternalMarketDataProviderUnavailable` on missing configuration,
        an exhausted-retry transport failure, a rate limit, or a
        malformed/incomplete response, always with a real, specific,
        secret-free reason. `end_time`/`anchor_price` exist only to
        satisfy MarketDataProvider's shared interface (see that class's
        docstring) — a real vendor adapter would fetch its own genuine
        historical window/price rather than needing either hint, so both
        are accepted and ignored here rather than implemented."""
        del end_time, anchor_price
        if timeframe not in TIMEFRAMES:
            raise ValueError(f"Unsupported timeframe {timeframe!r}; supported: {TIMEFRAME_ORDER}")
        self._require_available()

        url = f"{self._base_url}/candles?symbol={symbol}&timeframe={timeframe}&limit={limit}"
        headers = {"Authorization": f"Bearer {self._api_key}", "Accept": "application/json"}

        last_error: str | None = None
        for attempt in range(self.max_retries + 1):
            try:
                status_code, body = self._transport.get(url, headers=headers, timeout_seconds=self.timeout_seconds)
            except TimeoutError as exc:
                last_error = f"Timeout after {self.timeout_seconds:g}s (attempt {attempt + 1}/{self.max_retries + 1}): {_redact(str(exc), self._api_key)}"
                continue  # Section A.15 — retry only on a transient failure, never on a real rejection.
            except OSError as exc:
                last_error = f"Transport error (attempt {attempt + 1}/{self.max_retries + 1}): {_redact(str(exc), self._api_key)}"
                continue

            if status_code == 429:
                raise ExternalMarketDataProviderUnavailable(f"Rate limited by {self.provider_name!r} (HTTP 429).")
            if status_code in (401, 403):
                # Section A.12/A.13 — never retry an auth rejection (would
                # just spend the caller's real rate-limit budget for
                # nothing), and never echo the key that was rejected.
                raise ExternalMarketDataProviderUnavailable(f"Authentication rejected by {self.provider_name!r} (HTTP {status_code}).")
            if status_code >= 500:
                last_error = f"Server error HTTP {status_code} (attempt {attempt + 1}/{self.max_retries + 1})."
                continue
            if status_code != 200:
                raise ExternalMarketDataProviderUnavailable(f"Unexpected HTTP {status_code} from {self.provider_name!r}.")

            return self._parse_candles_response(body, symbol=symbol, timeframe=timeframe, limit=limit)

        raise ExternalMarketDataProviderUnavailable(last_error or "Real retrieval failed for an undisclosed reason.")

    def _parse_candles_response(self, body: bytes, *, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        """Section A.20-A.23 — parses this adapter's disclosed generic
        JSON contract, preserving each raw timestamp exactly as received
        before any normalization, and detects (never silently accepts)
        duplicate timestamps, out-of-order timestamps, and impossible
        OHLC relationships. Section A.9 — never interpolates a missing
        candle; a short response is honestly returned short, and Section
        A.17's "incomplete response" detection is the caller's own
        `app/data_quality.py::validate_candle_series()` (already real,
        already tested, never duplicated here)."""
        try:
            payload = json.loads(body)
            raw_candles = payload["candles"]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise ExternalMarketDataProviderUnavailable(f"Malformed response body from {self.provider_name!r}: {exc}") from None

        candles: list[Candle] = []
        seen_timestamps: set[str] = set()
        previous_timestamp: str | None = None
        for index, raw in enumerate(raw_candles):
            try:
                raw_timestamp = str(raw["timestamp"])  # preserved exactly as received — no normalization yet
                open_price, high, low, close = (float(raw["open"]), float(raw["high"]), float(raw["low"]), float(raw["close"]))
                volume = float(raw.get("volume", 0.0))
            except (KeyError, TypeError, ValueError) as exc:
                raise ExternalMarketDataProviderUnavailable(f"Malformed candle at index {index} from {self.provider_name!r}: {exc}") from None
            if raw_timestamp in seen_timestamps:
                raise ExternalMarketDataProviderUnavailable(f"Duplicate timestamp {raw_timestamp!r} at index {index} from {self.provider_name!r}.")
            if previous_timestamp is not None and raw_timestamp < previous_timestamp:
                raise ExternalMarketDataProviderUnavailable(f"Timestamp {raw_timestamp!r} at index {index} precedes prior timestamp {previous_timestamp!r} from {self.provider_name!r}.")
            if high < low or high < open_price or high < close or low > open_price or low > close:
                raise ExternalMarketDataProviderUnavailable(f"Impossible OHLC relationship at index {index} from {self.provider_name!r} (o={open_price}, h={high}, l={low}, c={close}).")
            seen_timestamps.add(raw_timestamp)
            previous_timestamp = raw_timestamp
            candles.append(
                Candle(symbol=symbol, timeframe=timeframe, timestamp=raw_timestamp, open=open_price, high=high, low=low, close=close, volume=volume, data_status="historical")
            )
        return candles


def get_external_market_data_provider() -> ExternalMarketDataProvider:
    """The one real, opt-in construction point for new code that wants to
    attempt real external data (e.g. app/dataset_registry.py) — reads
    configuration from the real environment variables fresh on every
    call, never cached at import time, so a test can monkeypatch
    `os.environ` per-test without import-order effects."""
    return ExternalMarketDataProvider()
