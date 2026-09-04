"""MarketIntelligence — v0.7 Feature 51, the Market Intelligence Department
("the company's eyes").

GOAL (from the brief): before any department searches for trades, the
company must first understand the environment it is operating in. This
module is that understanding layer — computed fresh every tick from real
data, read by the Trade Gatekeeper and every new TradeProposal (see
app/gatekeeper.py / app/executive.py), and folded into the Executive
Intelligence Network as a ninth real department (see
app/executive_intelligence.py) so "every department receives Market
Intelligence before deciding" is true by construction, not by rewiring
eight separate modules.

PROBABILITY FIRST RULE (from the brief): this module never predicts
future price movement. Every read below describes the CURRENT state of
real (mock) OHLCV data, or compares it against this same company's own
past reports — never a forecast.

THE HONESTY BOUNDARY — what's real here, and what deliberately is not:

Real, computed from real (mock) OHLCV Candle data (app/market_data.py's
MockMarketDataProvider) using standard, documented technical-analysis
formulas — genuine data, genuine math, just not a live paid feed:
  - Regime classification (13-way; see MarketIntelligenceRegime) —
    trend/volatility/volume-ratio thresholds applied to the same real
    trend_pct()/volatility_pct() helpers app/signal_calibration.py and
    app/player_vs_ai.py already use.
  - Market Structure — real local-extrema swing-high/low detection and
    the standard real definition of a Break of Structure.
  - Liquidity zones — real equal-high/equal-low price clustering from
    real swing points, and a real, standard "sweep" pattern (a candle
    wick pierces a recorded zone and closes back inside it).
  - Volatility Engine — current/historical/session volatility, all real
    volatility_pct() readings over different real candle sub-windows.
  - Session Intelligence — computed from real wall-clock UTC time (the
    same convention Candle.timestamp already uses, not TradeTown's
    simulated clock — see market_data.py's own docstring for why),
    classified against real, DST-aware NYSE/LSE/TSE exchange hours via
    Python's stdlib `zoneinfo` (CEO directive "Complete Trade
    Provenance," Part 4 — see compute_session()'s own docstring for why
    this now deliberately differs from the still-fixed-UTC
    `_session_for_hour()` backtesting uses). No exchange holiday
    calendar exists — a holiday is honestly misclassified as a normal
    trading day, an explicit, documented simplification.
  - Momentum — real rate-of-change comparison across two real candle
    sub-windows.
  - Strategy Matching — real cross-reference against app/sandbox.py's own
    StrategyReport.best_market_environment field (only ever recommends a
    strategy with real positive evidence in a matching scenario, never a
    strategy with no track record).
  - Learning Loop — a real, checkable comparison of yesterday's report
    against app/market_environment.py's own real regime timeline and real
    PaperTrade close outcomes for that same day.

Explicitly NAMED PROXIES — a real, computable signal used as a stand-in
for something this codebase has no real data source for, always labeled
as such wherever it's read (never presented as verified knowledge):
  - Institutional Activity — a real volume-vs-price-move divergence
    ("absorption") reading. This is NOT real institutional order flow,
    Level 2 data, or dark-pool prints — this codebase's MarketDataProvider
    exposes no order book at all (see market_data.py), and none is
    fabricated.
  - Accumulation / Distribution regimes — a real flat-price-plus-rising-
    or-fading-volume proxy read, not a confirmed Wyckoff volume-at-price
    analysis.
  - News Risk — the real COUNT of `market`-category NewsItem records
    currently on file. NewsItem (app/schemas.py) has no per-symbol
    linkage and no real economic-calendar timing — this is a company-wide
    "how much market news is currently circulating" proxy, not a real
    per-symbol event-risk or earnings-calendar read (the same honest gap
    app/sandbox.py's own "Testing Environments" cut already documents).

Explicitly NOT built, because no real data source exists anywhere in this
codebase and none is invented: real institutional positioning, real
resting stop-order locations ("retail stop clusters" in the literal
sense — this module's LiquidityZone is a probable price-action zone, not
a real order-book read), real dark-pool/Level 2 data, and any real
economic calendar. See app/confidence.py's own module docstring for the
same honesty boundary already established for an overlapping list of
factors it deliberately does not compute.
"""
from __future__ import annotations

from datetime import datetime
from datetime import time as dtime
from datetime import timezone
from statistics import mean
from typing import Literal
from zoneinfo import ZoneInfo

from app.market_data import Candle, MarketDataProvider, trend_pct, volatility_pct
from app.schemas import (
    ExecutiveAction,
    InstitutionalActivityRead,
    LiquidityRead,
    LiquidityZone,
    MultiTimeframeLiquidityRead,
    MarketDebate,
    MarketEnvironmentEntry,
    MarketEnvironmentRegime,
    MarketIntelligenceLearningEntry,
    MarketIntelligenceRegime,
    MarketIntelligenceReport,
    MarketIntelligenceState,
    MarketQualityScore,
    MarketQualityTier,
    MarketStructureRead,
    MomentumRead,
    NewsItem,
    NewsRiskRead,
    PaperTrade,
    SessionRead,
    Strategy,
    StrategyMatch,
    StrategyReport,
    TradingSession,
    VolatilityRead,
    WatchlistEntry,
)

CANDLE_TIMEFRAME = "1h"
# More history than app/executive.py's own PROPOSAL_CANDLE_COUNT (30) —
# swing/structure detection needs enough bars on each side of a candidate
# swing point to be meaningful, on top of the recent/historical
# sub-windows volatility/momentum compare against.
CANDLE_WINDOW = 40
RECENT_WINDOW = 10
SWING_LOOKBACK = 3
LIQUIDITY_CLUSTER_TOLERANCE_PCT = 0.3

# CEO directive "Liquidity Context Improvement + Autonomous Company
# Readiness Audit 1.0," Objective A — a SHADOW-ONLY, higher-timeframe
# companion read for compute_liquidity() below. A dedicated Phase 0
# forensic audit for that directive found the real, structural reason
# production's own 1h/40-candle liquidity read lands near-zero for most
# candidates: `app/market_data.py::MockMarketDataProvider`'s own real
# regime-switching walk holds one internal regime (mean-reverting
# "range" segments especially, see that module's own
# _REGIME_MEAN_REVERSION) for 12-55 BARS regardless of timeframe — a
# 40-bar 1h window (40 real hours) frequently doesn't even span one full
# regime segment, so there is rarely enough real repeated-visits-to-a-
# level behavior for compute_liquidity()'s own real clustering logic to
# find. The SAME 12-55-bar regime duration, read on a 4h candle instead,
# spans 4x the real wall-clock time per bar — a materially better chance
# of a real mean-reverting segment showing up complete within a bounded
# candle count. This is a genuine, disclosed property of the underlying
# generator's own real mean-reversion structure, not a claim about real
# markets (this module has no live feed — see this module's own
# docstring) and not evidence the 1h read is wrong; it only means a
# COARSER real timeframe is a genuinely different, not merely noisier,
# observation of the SAME real (mock) price process.
MULTI_TIMEFRAME_LIQUIDITY_TIMEFRAME = "4h"
MULTI_TIMEFRAME_LIQUIDITY_CANDLE_COUNT = 30
# A level that clusters independently on BOTH the 1h and the 4h read is
# real cross-timeframe confirmation — the standard, honest technical-
# analysis concept of "higher-timeframe confluence," never a claim about
# real institutional order flow this codebase cannot observe (see
# LiquidityRead's own docstring for the same honesty boundary). Capped-
# bonus shape reused from "TradeTown — Department Debate & Collaboration
# Intelligence 1.0"'s own EVIDENCE_REUSE_BONUS_PER_PAIR/MAX_EVIDENCE_
# REUSE_BONUS precedent (app/collaboration_intelligence.py) rather than
# inventing a new weighting convention — fixed, predeclared BEFORE this
# shadow read was ever compared against a single real outcome (see
# app/opportunity_gate_calibration_experiment.py's own "NO SEARCH OVER
# WEIGHTS" discipline).
MULTI_TIMEFRAME_CONFIRMATION_BONUS_PER_ZONE = 10.0
MAX_MULTI_TIMEFRAME_CONFIRMATION_BONUS = 20.0

MAX_MARKET_INTELLIGENCE_REPORTS = 60
MAX_MARKET_INTELLIGENCE_LEARNING = 60

STRONG_TREND_PCT = 3.0
WEAK_TREND_PCT = 1.0
HIGH_VOL_PCT = 2.5
LOW_VOL_PCT = 0.6
EXPANSION_RATIO = 1.3
COMPRESSION_RATIO = 0.7
LIQUIDITY_HUNT_SHARE = 0.35
REVERSAL_SHARE = 0.5
VOLUME_TREND_UP = 1.15
VOLUME_TREND_DOWN = 0.87
# A documented "goldilocks" band — enough real movement to trade, not so
# much it's unmanageable. Not a claim about any specific symbol's ideal
# volatility, just this composite's own real, fixed reference point.
IDEAL_VOLATILITY_PCT = 1.5

_REGIME_LABEL: dict[MarketIntelligenceRegime, str] = {
    "strong_bull_trend": "Strong Bull Trend",
    "strong_bear_trend": "Strong Bear Trend",
    "weak_uptrend": "Weak Uptrend",
    "weak_downtrend": "Weak Downtrend",
    "sideways_range": "Sideways Range",
    "expansion": "Expansion",
    "compression": "Compression",
    "high_volatility": "High Volatility",
    "low_volatility": "Low Volatility",
    "accumulation": "Accumulation (volume proxy)",
    "distribution": "Distribution (volume proxy)",
    "liquidity_hunt": "Liquidity Hunt",
    "transitional": "Transitional Market",
}

_SESSION_LABEL: dict[TradingSession, str] = {
    "asian": "Asian Session",
    "london": "London Session",
    "london_ny_overlap": "London/New York Overlap",
    "ny_lunch_hour": "New York Lunch Hour",
    "new_york": "New York Session",
    "market_open": "US Market Open (first 30 min)",
    "market_close": "US Market Close (final 30 min)",
    "closed": "Between Sessions",
}

_SESSION_QUALITY: dict[TradingSession, float] = {
    "london_ny_overlap": 90.0,
    "market_open": 85.0,
    "london": 70.0,
    "new_york": 70.0,
    "market_close": 65.0,
    "asian": 45.0,
    "ny_lunch_hour": 35.0,
    "closed": 20.0,
}

_QUALITY_TIER_THRESHOLDS: tuple[tuple[float, MarketQualityTier], ...] = (
    (80.0, "excellent"),
    (65.0, "good"),
    (45.0, "average"),
    (25.0, "poor"),
    (0.0, "avoid_trading"),
)

# A real (if approximate) bridge to app/sandbox.py's existing five-scenario
# vocabulary — StrategyReport.best_market_environment is free text built
# from that same five-way TestScenario, so Strategy Matching cross-checks
# by keyword rather than inventing a second, parallel strategy-performance
# tracker.
_REGIME_TO_SCENARIO_KEYWORD: dict[MarketIntelligenceRegime, str] = {
    "strong_bull_trend": "bull",
    "weak_uptrend": "bull",
    "accumulation": "bull",
    "strong_bear_trend": "bear",
    "weak_downtrend": "bear",
    "distribution": "bear",
    "sideways_range": "sideways",
    "compression": "sideways",
    "transitional": "sideways",
    "high_volatility": "high volatility",
    "liquidity_hunt": "high volatility",
    "expansion": "high volatility",
    "low_volatility": "low volatility",
}

# The real, documented direction-only comparison against
# app/market_environment.py's simpler five-way regime — several of this
# module's thirteen regimes are honestly ambiguous against that coarser
# scale (e.g. "expansion" could resolve to a bull, bear, or high-vol
# environment), so those map to more than one acceptable real outcome
# rather than a fabricated single "correct" answer. Originally private
# to the Learning Loop below; promoted to public (v0.7 Design Bible
# Chapter 65) once app/regime_reconciliation.py needed the exact same
# real mapping to reconcile the two engines' regime reads — reused
# directly, never a second, competing map.
REGIME_CONSISTENCY_MAP: dict[MarketIntelligenceRegime, frozenset[MarketEnvironmentRegime]] = {
    "strong_bull_trend": frozenset({"bull"}),
    "weak_uptrend": frozenset({"bull"}),
    "accumulation": frozenset({"bull", "sideways"}),
    "strong_bear_trend": frozenset({"bear"}),
    "weak_downtrend": frozenset({"bear"}),
    "distribution": frozenset({"bear", "sideways"}),
    "sideways_range": frozenset({"sideways"}),
    "compression": frozenset({"sideways", "low_volatility"}),
    "transitional": frozenset({"sideways"}),
    "high_volatility": frozenset({"high_volatility"}),
    "liquidity_hunt": frozenset({"high_volatility", "sideways"}),
    "expansion": frozenset({"high_volatility", "bull", "bear"}),
    "low_volatility": frozenset({"low_volatility", "sideways"}),
}

_QUALITY_TO_ACTION: dict[MarketQualityTier, ExecutiveAction] = {
    "excellent": "trade_normally",
    "good": "trade_normally",
    "average": "wait",
    "poor": "reduce_risk",
    "avoid_trading": "pause_trading",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _quality_tier(score: float) -> MarketQualityTier:
    return next(tier for threshold, tier in _QUALITY_TIER_THRESHOLDS if score >= threshold)


# ---------------------------------------------------------------------
# Session Intelligence.
#
# Two DELIBERATELY SEPARATE classifiers, not a duplication —
# CEO directive "Complete Trade Provenance," Part 4 research found no
# existing timezone/DST architecture anywhere in this codebase, and
# building one raised a real Absolute-Rule-#4 conflict ("do not change
# existing quality metrics/certification thresholds"): `_session_for_hour()`
# below also backs backtesting (app/strategy_engine.py, app/ema_pullback_
# research.py) and this module's own `_SESSION_QUALITY` session-quality
# table over BACKTEST candle history — changing its boundaries would
# retroactively shift already-certified strategies' historical session
# breakdowns and win rates, which the directive explicitly forbids.
#
# So `_session_for_hour()` stays completely UNCHANGED — every backtest/
# certification path keeps its exact prior boundaries — and
# `compute_session()` below is instead rebuilt on real, DST-aware
# exchange-hours classification for the LIVE-only path (the Gatekeeper,
# every fresh TradeProposal, and this directive's own Part 8
# decision-time snapshot). A live signal legitimately benefits from
# being more accurate; nothing here inflates any score, it only makes
# the live session read genuinely correct across DST transitions and
# weekends, where the fixed-UTC approximation was wrong.
# ---------------------------------------------------------------------


def _session_for_hour(hour: float) -> TradingSession:
    if 13.5 <= hour < 14.0:
        return "market_open"
    if 20.5 <= hour < 21.0:
        return "market_close"
    if 0.0 <= hour < 8.0:
        return "asian"
    if 8.0 <= hour < 13.0:
        return "london"
    if 13.0 <= hour < 16.0:
        return "london_ny_overlap"
    if 16.0 <= hour < 17.0:
        return "ny_lunch_hour"
    if 17.0 <= hour < 21.0:
        return "new_york"
    return "closed"


# Real, publicly documented exchange trading hours — not fabricated.
# Tokyo observes no DST (fixed UTC+9 year-round); New York/London shift
# with real US/UK daylight-saving transitions, which `zoneinfo` (the
# real IANA timezone database, stdlib since Python 3.9, no new
# dependency and no network call) applies correctly and automatically.
_NYSE_TZ = ZoneInfo("America/New_York")
_LSE_TZ = ZoneInfo("Europe/London")
_TSE_TZ = ZoneInfo("Asia/Tokyo")
_NYSE_OPEN = dtime(9, 30)
_NYSE_CLOSE = dtime(16, 0)
_NYSE_MARKET_OPEN_END = dtime(10, 0)
_NYSE_MARKET_CLOSE_START = dtime(15, 30)
_NYSE_LUNCH_START = dtime(12, 0)
_NYSE_LUNCH_END = dtime(13, 0)
_LSE_OPEN = dtime(8, 0)
_LSE_CLOSE = dtime(16, 30)
_TSE_OPEN = dtime(9, 0)
_TSE_CLOSE = dtime(15, 0)


def compute_session(now: datetime) -> SessionRead:
    """Real, DST-aware live session classification — see the module
    section header above for why this now deliberately differs from
    `_session_for_hour()`. Deliberately does NOT model exchange
    holidays (Christmas, Thanksgiving, etc.): this codebase has no real
    holiday-calendar data source, and fabricating one would violate
    this directive's own no-fabrication rule — a holiday is honestly
    misclassified as a normal trading day, a real, disclosed
    limitation, not silently hidden."""
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    ny = now.astimezone(_NYSE_TZ)
    london = now.astimezone(_LSE_TZ)
    tokyo = now.astimezone(_TSE_TZ)

    ny_open = ny.weekday() < 5 and _NYSE_OPEN <= ny.time() < _NYSE_CLOSE
    ny_market_open_window = ny.weekday() < 5 and _NYSE_OPEN <= ny.time() < _NYSE_MARKET_OPEN_END
    ny_market_close_window = ny.weekday() < 5 and _NYSE_MARKET_CLOSE_START <= ny.time() < _NYSE_CLOSE
    ny_lunch_window = ny.weekday() < 5 and _NYSE_LUNCH_START <= ny.time() < _NYSE_LUNCH_END
    london_open = london.weekday() < 5 and _LSE_OPEN <= london.time() < _LSE_CLOSE
    tokyo_open = tokyo.weekday() < 5 and _TSE_OPEN <= tokyo.time() < _TSE_CLOSE

    current: TradingSession
    if ny_market_open_window:
        current = "market_open"
    elif ny_market_close_window:
        current = "market_close"
    elif ny_open and london_open:
        current = "london_ny_overlap"
    elif ny_open and ny_lunch_window:
        current = "ny_lunch_hour"
    elif ny_open:
        current = "new_york"
    elif london_open:
        current = "london"
    elif tokyo_open:
        current = "asian"
    else:
        current = "closed"

    overlaps = ["london", "new_york"] if (london_open and ny_open) else []
    detail = (
        f"Real UTC time {now.strftime('%H:%M')} ({ny.strftime('%H:%M %Z')} New York / {london.strftime('%H:%M %Z')} London) "
        f"— {_SESSION_LABEL[current]} (real DST-aware exchange hours; no holiday calendar)."
    )

    # CEO directive "Complete Trade Provenance," Part 5 — Session
    # Context. Whichever real exchange governs `current` (NYSE for
    # every NYSE-family state, LSE for london, TSE for asian) has a
    # single, well-defined today's open/close in its own local time —
    # None only for "closed" (no governing exchange session active).
    started_at: str | None = None
    closes_at: str | None = None
    minutes_since_open: int | None = None
    minutes_until_close: int | None = None
    if current in ("market_open", "market_close", "london_ny_overlap", "ny_lunch_hour", "new_york"):
        local_now, open_time, close_time = ny, _NYSE_OPEN, _NYSE_CLOSE
    elif current == "london":
        local_now, open_time, close_time = london, _LSE_OPEN, _LSE_CLOSE
    elif current == "asian":
        local_now, open_time, close_time = tokyo, _TSE_OPEN, _TSE_CLOSE
    else:
        local_now = None
    if local_now is not None:
        session_open = local_now.replace(hour=open_time.hour, minute=open_time.minute, second=0, microsecond=0)
        session_close = local_now.replace(hour=close_time.hour, minute=close_time.minute, second=0, microsecond=0)
        started_at = session_open.astimezone(timezone.utc).isoformat()
        closes_at = session_close.astimezone(timezone.utc).isoformat()
        minutes_since_open = int((local_now - session_open).total_seconds() // 60)
        minutes_until_close = int((session_close - local_now).total_seconds() // 60)

    return SessionRead(
        current=current,
        label=_SESSION_LABEL[current],
        overlapsActive=overlaps,
        detail=detail,
        sessionStartedAt=started_at,
        sessionClosesAt=closes_at,
        minutesSinceSessionOpen=minutes_since_open,
        minutesUntilSessionClose=minutes_until_close,
    )


def _session_volatility(per_symbol_candles: dict[str, list[Candle]], session: TradingSession) -> float:
    session_candles: list[Candle] = []
    for candles in per_symbol_candles.values():
        for candle in candles:
            ts = datetime.fromisoformat(candle.timestamp)
            if _session_for_hour(ts.hour + ts.minute / 60.0) == session:
                session_candles.append(candle)
    return volatility_pct(session_candles) if session_candles else 0.0


def _volatility_percentile(current: float, historical_avg: float) -> float:
    if historical_avg <= 0:
        return 50.0
    ratio = current / historical_avg
    return max(0.0, min(100.0, 50.0 + (ratio - 1.0) * 50.0))


# ---------------------------------------------------------------------
# Market Structure — real local-extrema swing detection.
# ---------------------------------------------------------------------


def _find_swings(candles: list[Candle]) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    highs: list[tuple[int, float]] = []
    lows: list[tuple[int, float]] = []
    n = len(candles)
    for i in range(SWING_LOOKBACK, n - SWING_LOOKBACK):
        window = candles[i - SWING_LOOKBACK : i + SWING_LOOKBACK + 1]
        if candles[i].high == max(c.high for c in window):
            highs.append((i, candles[i].high))
        if candles[i].low == min(c.low for c in window):
            lows.append((i, candles[i].low))
    return highs, lows


def compute_market_structure(symbol: str, candles: list[Candle]) -> MarketStructureRead:
    if len(candles) < SWING_LOOKBACK * 2 + 2:
        return MarketStructureRead(symbol=symbol, swingHighs=[], swingLows=[], lastBreakOfStructure="none", structureState="consolidation", detail="Not enough real candle history yet to read structure.")

    highs_idx, lows_idx = _find_swings(candles)
    swing_highs = [p for _, p in highs_idx]
    swing_lows = [p for _, p in lows_idx]

    bos: Literal["bullish", "bearish", "none"] = "none"
    # The real candle index of the swing that produced `bos` — straight
    # from _find_swings()'s own (index, price) pair, never re-derived —
    # so the Live Desk chart can mark exactly where the break happened.
    bos_index: int | None = None
    if len(swing_highs) >= 2 and swing_highs[-1] > swing_highs[-2]:
        bos = "bullish"
        bos_index = highs_idx[-1][0]
    elif len(swing_lows) >= 2 and swing_lows[-1] < swing_lows[-2]:
        bos = "bearish"
        bos_index = lows_idx[-1][0]

    trend = trend_pct(candles)
    vol = volatility_pct(candles)
    recent_vol = volatility_pct(candles[-RECENT_WINDOW:])

    state: Literal["trend_continuation", "trend_reversal", "consolidation", "expansion", "compression"]
    if abs(trend) < WEAK_TREND_PCT and recent_vol < vol * COMPRESSION_RATIO:
        state = "compression"
    elif recent_vol > vol * EXPANSION_RATIO:
        state = "expansion"
    elif abs(trend) < WEAK_TREND_PCT:
        state = "consolidation"
    elif (bos == "bullish" and trend < 0) or (bos == "bearish" and trend > 0):
        state = "trend_reversal"
    else:
        state = "trend_continuation"

    # CEO directive "AHL-Inspired Systematic Trend & Momentum Research
    # Engine" Phase 10 — one real, specific, disclosed Change of
    # Character definition (see MarketStructureRead.change_of_character's
    # own docstring for why this exact one, not a claim of the only
    # valid one): the latest real BOS, but only when it disagrees with
    # the real net trend already computed above — the exact same
    # condition that already produces state == "trend_reversal".
    change_of_character: Literal["bullish", "bearish", "none"] = bos if state == "trend_reversal" else "none"

    detail = f"{len(swing_highs)} swing high(s), {len(swing_lows)} swing low(s) over the last {len(candles)} {CANDLE_TIMEFRAME} candles; {trend:+.2f}% net move."
    return MarketStructureRead(
        symbol=symbol,
        swingHighs=[round(p, 2) for p in swing_highs[-5:]],
        swingLows=[round(p, 2) for p in swing_lows[-5:]],
        lastBreakOfStructure=bos,
        lastBreakOfStructureTimestamp=candles[bos_index].timestamp if bos_index is not None else None,
        structureState=state,
        changeOfCharacter=change_of_character,
        detail=detail,
    )


# ---------------------------------------------------------------------
# Liquidity Intelligence — real equal-high/low clustering + sweep read.
# ---------------------------------------------------------------------


def _cluster_levels(points: list[float], tolerance_pct: float) -> list[tuple[float, int]]:
    if not points:
        return []
    ordered = sorted(points)
    clusters: list[list[float]] = [[ordered[0]]]
    for price in ordered[1:]:
        if abs(price - clusters[-1][-1]) / clusters[-1][-1] * 100 <= tolerance_pct:
            clusters[-1].append(price)
        else:
            clusters.append([price])
    return [(mean(c), len(c)) for c in clusters if len(c) >= 2]


def compute_liquidity(symbol: str, candles: list[Candle]) -> LiquidityRead:
    if len(candles) < SWING_LOOKBACK * 2 + 6:
        return LiquidityRead(symbol=symbol, zones=[], sweepDetected=False, sweepDirection="none", liquidityScore=50.0, detail="Not enough real candle history yet for a liquidity read.")

    history, recent = candles[:-5], candles[-5:]
    highs_idx, lows_idx = _find_swings(history)
    high_clusters = _cluster_levels([p for _, p in highs_idx], LIQUIDITY_CLUSTER_TOLERANCE_PCT)
    low_clusters = _cluster_levels([p for _, p in lows_idx], LIQUIDITY_CLUSTER_TOLERANCE_PCT)
    zones = [LiquidityZone(kind="equal_highs", price=round(p, 2), touches=t) for p, t in high_clusters] + [
        LiquidityZone(kind="equal_lows", price=round(p, 2), touches=t) for p, t in low_clusters
    ]

    sweep_detected = False
    sweep_direction: Literal["above_highs", "below_lows", "none"] = "none"
    # Straight from the candle object that actually triggered the sweep
    # check below — never re-derived — so the Live Desk chart can mark
    # exactly where it happened.
    sweep_timestamp: str | None = None
    for candle in recent:
        for price, _ in high_clusters:
            if candle.high > price * (1 + LIQUIDITY_CLUSTER_TOLERANCE_PCT / 100) and candle.close < price:
                sweep_detected, sweep_direction, sweep_timestamp = True, "above_highs", candle.timestamp
                break
        if sweep_detected:
            break
        for price, _ in low_clusters:
            if candle.low < price * (1 - LIQUIDITY_CLUSTER_TOLERANCE_PCT / 100) and candle.close > price:
                sweep_detected, sweep_direction, sweep_timestamp = True, "below_lows", candle.timestamp
                break
        if sweep_detected:
            break

    liquidity_score = min(100.0, len(zones) * 15.0 + (25.0 if sweep_detected else 0.0))
    if zones:
        detail = f"{len(zones)} real probable liquidity zone(s) found ({len(high_clusters)} equal-high, {len(low_clusters)} equal-low cluster(s))"
        detail += f"; a sweep {sweep_direction.replace('_', ' ')} was just detected." if sweep_detected else "."
    else:
        detail = "No real equal-high/equal-low clustering found in the sampled history."
    return LiquidityRead(
        symbol=symbol,
        zones=zones,
        sweepDetected=sweep_detected,
        sweepDirection=sweep_direction,
        sweepTimestamp=sweep_timestamp,
        liquidityScore=round(liquidity_score, 1),
        detail=detail,
    )


def _zone_confirmed_at_higher_timeframe(zone: LiquidityZone, higher_timeframe_zones: list[LiquidityZone]) -> bool:
    """A real zone is 'confirmed' only by a same-kind zone (equal-highs
    only confirms equal-highs) landing within the SAME real clustering
    tolerance compute_liquidity() itself already uses — never a new,
    looser tolerance invented for this shadow read."""
    return any(
        other.kind == zone.kind and abs(zone.price - other.price) / other.price * 100 <= LIQUIDITY_CLUSTER_TOLERANCE_PCT
        for other in higher_timeframe_zones
    )


def compute_multi_timeframe_liquidity(symbol: str, one_hour_candles: list[Candle], higher_timeframe_candles: list[Candle]) -> MultiTimeframeLiquidityRead:
    """CEO directive "Liquidity Context Improvement + Autonomous Company
    Readiness Audit 1.0," Objective A — SHADOW-ONLY. Reuses compute_liquidity()
    itself, unmodified, twice (once per real timeframe) — never a second
    clustering/swing implementation. Never replaces, mutates, or is read
    by the real production `liquidity_quality_score` this module's own
    compute_liquidity() already feeds into app/war_room.py's real
    DecisionScoreBreakdown — see app/opportunity_gate_calibration_
    experiment.py's own module docstring for where this shadow read is
    compared, never substituted, against the real Gatekeeper outcome.

    `blended_score` never LOWERS the real 1h score — it only ever ADDS a
    capped bonus when the SAME real price level independently clusters
    on the higher real timeframe too (genuine cross-timeframe
    confirmation, the standard technical-analysis concept — never a
    claim about real institutional order flow this codebase has no data
    source for, see LiquidityRead's own docstring for the same honesty
    boundary already established there)."""
    one_hour = compute_liquidity(symbol, one_hour_candles)
    higher_timeframe = compute_liquidity(symbol, higher_timeframe_candles)
    confirmed_zone_count = sum(1 for zone in one_hour.zones if _zone_confirmed_at_higher_timeframe(zone, higher_timeframe.zones))
    bonus = min(MAX_MULTI_TIMEFRAME_CONFIRMATION_BONUS, confirmed_zone_count * MULTI_TIMEFRAME_CONFIRMATION_BONUS_PER_ZONE)
    blended_score = round(min(100.0, one_hour.liquidity_score + bonus), 1)
    if confirmed_zone_count:
        detail = f"{confirmed_zone_count} of {len(one_hour.zones)} real 1h liquidity zone(s) also cluster independently on the real {MULTI_TIMEFRAME_LIQUIDITY_TIMEFRAME} read — cross-timeframe confirmed."
    else:
        detail = f"No real 1h liquidity zone was independently confirmed by the real {MULTI_TIMEFRAME_LIQUIDITY_TIMEFRAME} read."
    return MultiTimeframeLiquidityRead(
        symbol=symbol,
        oneHourLiquidityScore=one_hour.liquidity_score,
        higherTimeframeLiquidityScore=higher_timeframe.liquidity_score,
        higherTimeframe=MULTI_TIMEFRAME_LIQUIDITY_TIMEFRAME,
        confirmedZoneCount=confirmed_zone_count,
        blendedLiquidityScore=blended_score,
        detail=detail,
    )


# ---------------------------------------------------------------------
# Momentum, Institutional Activity (proxy), News Risk (proxy).
# ---------------------------------------------------------------------


def _momentum_read(per_symbol_candles: dict[str, list[Candle]]) -> MomentumRead:
    recent_rocs: list[float] = []
    prior_rocs: list[float] = []
    for candles in per_symbol_candles.values():
        if len(candles) < RECENT_WINDOW * 2:
            continue
        recent_rocs.append(trend_pct(candles[-RECENT_WINDOW:]))
        prior_rocs.append(trend_pct(candles[-RECENT_WINDOW * 2 : -RECENT_WINDOW]))

    if not recent_rocs:
        return MomentumRead(rocPct=0.0, strength="steady", detail="Not enough real candle history yet for a momentum read.")

    recent = mean(recent_rocs)
    prior = mean(prior_rocs) if prior_rocs else recent
    strength: Literal["accelerating", "steady", "decelerating", "exhausted"]
    if abs(prior) > 0.01 and (recent > 0) != (prior > 0) and abs(recent) > 0.3:
        strength = "exhausted"
    elif abs(recent) > abs(prior) * 1.2:
        strength = "accelerating"
    elif abs(recent) < abs(prior) * 0.8:
        strength = "decelerating"
    else:
        strength = "steady"
    detail = f"Aggregate rate of change {recent:+.2f}% over the most recent window vs {prior:+.2f}% over the prior one."
    return MomentumRead(rocPct=round(recent, 2), strength=strength, detail=detail)


def _institutional_activity_read(per_symbol_candles: dict[str, list[Candle]]) -> InstitutionalActivityRead:
    flagged: list[str] = []
    scores: list[float] = []
    for symbol, candles in per_symbol_candles.items():
        if len(candles) < RECENT_WINDOW + 1:
            continue
        historical_avg_volume = mean(c.volume for c in candles[:-1]) or 1.0
        last = candles[-1]
        volume_ratio = last.volume / historical_avg_volume
        move_pct = abs(last.close - last.open) / last.open * 100 if last.open else 0.0
        symbol_vol = volatility_pct(candles)
        absorption = volume_ratio >= 1.3 and move_pct < symbol_vol * 0.5
        scores.append(min(100.0, volume_ratio * 25.0) if absorption else min(60.0, volume_ratio * 15.0))
        if absorption:
            flagged.append(symbol)

    avg_score = mean(scores) if scores else 0.0
    detail = (
        f"{len(flagged)}/{len(per_symbol_candles)} tracked symbol(s) show high relative volume with a proportionally small "
        "price move — a real volume/price-divergence proxy, not verified order-flow data (see this module's docstring)."
    )
    return InstitutionalActivityRead(volumePriceDivergenceScore=round(avg_score, 1), absorptionDetected=bool(flagged), symbolsFlagged=flagged, detail=detail)


def compute_news_risk(news: list[NewsItem]) -> NewsRiskRead:
    count = sum(1 for n in news if n.category == "market")
    risk_level: Literal["low", "moderate", "elevated"] = "elevated" if count >= 6 else "moderate" if count >= 3 else "low"
    detail = f"{count} real market-category news item(s) currently on file — {risk_level} activity level (see this module's docstring: a company-wide news-volume proxy, not per-symbol event risk)."
    return NewsRiskRead(activeMarketNewsCount=count, riskLevel=risk_level, detail=detail)


# ---------------------------------------------------------------------
# Regime classification — ordered, documented thresholds.
# ---------------------------------------------------------------------


def _classify_regime(avg_trend: float, avg_abs_trend: float, avg_vol: float, vol_ratio: float, sweep_share: float, reversal_share: float, volume_trend: float) -> tuple[MarketIntelligenceRegime, str, str]:
    regime: MarketIntelligenceRegime
    if sweep_share >= LIQUIDITY_HUNT_SHARE:
        regime = "liquidity_hunt"
        detail = f"{sweep_share * 100:.0f}% of tracked symbols show a real liquidity sweep this tick."
    elif reversal_share >= REVERSAL_SHARE:
        regime = "transitional"
        detail = f"{reversal_share * 100:.0f}% of tracked symbols reversed direction within the sampled window."
    elif vol_ratio >= EXPANSION_RATIO:
        regime = "expansion"
        detail = f"Recent volatility is running {vol_ratio:.2f}x the trailing average — the range is widening."
    elif vol_ratio <= COMPRESSION_RATIO:
        regime = "compression"
        detail = f"Recent volatility is only {vol_ratio:.2f}x the trailing average — the range is tightening."
    elif avg_vol >= HIGH_VOL_PCT:
        regime = "high_volatility"
        detail = f"Average per-bar range is {avg_vol:.2f}%, above the {HIGH_VOL_PCT:.1f}% high-volatility bar."
    elif avg_vol <= LOW_VOL_PCT and avg_abs_trend < WEAK_TREND_PCT:
        regime = "low_volatility"
        detail = f"Average per-bar range is only {avg_vol:.2f}%, and the market isn't trending either."
    elif avg_trend >= STRONG_TREND_PCT:
        regime = "strong_bull_trend"
        detail = f"Average net move is {avg_trend:+.2f}% across tracked symbols."
    elif avg_trend <= -STRONG_TREND_PCT:
        regime = "strong_bear_trend"
        detail = f"Average net move is {avg_trend:+.2f}% across tracked symbols."
    elif avg_trend >= WEAK_TREND_PCT:
        regime = "weak_uptrend"
        detail = f"A modest {avg_trend:+.2f}% average net move — real, but not yet a strong uptrend."
    elif avg_trend <= -WEAK_TREND_PCT:
        regime = "weak_downtrend"
        detail = f"A modest {avg_trend:+.2f}% average net move — real, but not yet a strong downtrend."
    elif volume_trend >= VOLUME_TREND_UP:
        regime = "accumulation"
        detail = f"Price is flat ({avg_trend:+.2f}%) but volume is running {volume_trend:.2f}x its trailing average — a real accumulation-style volume proxy, not confirmed order flow."
    elif volume_trend <= VOLUME_TREND_DOWN:
        regime = "distribution"
        detail = f"Price is flat ({avg_trend:+.2f}%) but volume is fading to {volume_trend:.2f}x its trailing average — a real distribution-style volume proxy, not confirmed order flow."
    else:
        regime = "sideways_range"
        detail = f"No strong trend ({avg_trend:+.2f}%) and no volatility or volume extreme — an ordinary real range."
    return regime, _REGIME_LABEL[regime], detail


# ---------------------------------------------------------------------
# Market Quality Score.
# ---------------------------------------------------------------------


def compute_historical_similarity(regime: MarketIntelligenceRegime, history: list[MarketIntelligenceReport]) -> str:
    if not history:
        return "No real prior daily reports yet — this is the first real read to compare against."
    matches = sum(1 for report in history if report.snapshot.regime == regime)
    return f"This regime has occurred on {matches} of the last {len(history)} real recorded day(s)."


def compute_market_quality(
    regime: MarketIntelligenceRegime,
    volatility: VolatilityRead,
    session: SessionRead,
    sweep_share: float,
    news_risk: NewsRiskRead,
    structure_reads: list[MarketStructureRead],
    reports_history: list[MarketIntelligenceReport],
    *,
    data_symbol_count: int,
) -> MarketQualityScore:
    vol_component = max(0.0, 100.0 - abs(volatility.current_pct - IDEAL_VOLATILITY_PCT) * 25.0)
    clear_structure = sum(1 for s in structure_reads if s.structure_state in ("trend_continuation", "expansion"))
    structure_component = (clear_structure / len(structure_reads) * 100.0) if structure_reads else 50.0
    session_component = _SESSION_QUALITY.get(session.current, 50.0)
    liquidity_risk_component = max(0.0, 100.0 - sweep_share * 150.0)
    news_component = {"low": 90.0, "moderate": 60.0, "elevated": 30.0}[news_risk.risk_level]

    score = vol_component * 0.25 + structure_component * 0.25 + session_component * 0.2 + liquidity_risk_component * 0.15 + news_component * 0.15
    tier = _quality_tier(score)
    # Capped below 100 — never claims full certainty, per the module's
    # Probability First rule — and scales with how much real candle data
    # actually backed this read.
    confidence = round(min(90.0, 40.0 + data_symbol_count * 6.0), 1)
    evidence = [
        f"Volatility {volatility.current_pct:.2f}% vs a {IDEAL_VOLATILITY_PCT:.1f}% reference band ({vol_component:.0f}/100).",
        f"{clear_structure}/{len(structure_reads)} tracked symbol(s) show clear directional structure ({structure_component:.0f}/100).",
        f"{session.label} — real session liquidity read ({session_component:.0f}/100).",
        f"{sweep_share * 100:.0f}% of tracked symbols show a real liquidity sweep this tick ({liquidity_risk_component:.0f}/100).",
        f"{news_risk.active_market_news_count} active market-news item(s) — {news_risk.risk_level} ({news_component:.0f}/100).",
    ]
    reasoning = f"{tier.replace('_', ' ').title()} — composite {score:.0f}/100 from real volatility, structure clarity, session liquidity, liquidity-sweep risk, and news activity."
    similarity = compute_historical_similarity(regime, reports_history)
    return MarketQualityScore(tier=tier, score=round(score, 1), confidencePct=confidence, reasoning=reasoning, evidence=evidence, historicalSimilarity=similarity)


# ---------------------------------------------------------------------
# Strategy Matching.
# ---------------------------------------------------------------------


def compute_strategy_match(regime: MarketIntelligenceRegime, strategies: list[Strategy], reports: list[StrategyReport]) -> StrategyMatch:
    keyword = _REGIME_TO_SCENARIO_KEYWORD[regime]
    latest_report_by_strategy: dict[str, StrategyReport] = {}
    for report in reports:  # oldest-first, capped — later entries overwrite, so this ends up "latest per strategy"
        latest_report_by_strategy[report.strategy_id] = report

    recommended: list[str] = []
    avoided: list[str] = []
    for strategy in strategies:
        matched_report = latest_report_by_strategy.get(strategy.id)
        if matched_report is None or keyword not in matched_report.best_market_environment.lower():
            continue
        if matched_report.best_market_environment.lower().startswith("not yet"):
            avoided.append(strategy.id)
        else:
            recommended.append(strategy.id)

    risk_level: Literal["minimal", "reduced", "normal", "elevated"]
    if recommended:
        risk_level = "normal"
        detail = f"{len(recommended)} strateg{'y has' if len(recommended) == 1 else 'ies have'} real evidence of working under {keyword} conditions like today's."
    elif avoided:
        risk_level = "reduced"
        detail = f"{len(avoided)} strateg{'y' if len(avoided) == 1 else 'ies'} lost money the last time tested under {keyword} conditions — avoid until re-tested."
    else:
        risk_level = "normal"
        detail = "No strategy has been tested under today's specific conditions yet — no real match either way."

    return StrategyMatch(recommendedStrategyIds=recommended, avoidedStrategyIds=avoided, recommendedRiskLevel=risk_level, detail=detail)


# ---------------------------------------------------------------------
# Main orchestrator — the always-current state, recomputed every tick.
# ---------------------------------------------------------------------


def default_market_intelligence_state(*, now: datetime | None = None) -> MarketIntelligenceState:
    now = now or datetime.now(timezone.utc)
    quality = MarketQualityScore(tier="average", score=50.0, confidencePct=40.0, reasoning="No real candle data sampled yet.", evidence=[], historicalSimilarity="No real prior daily reports yet.")
    volatility = VolatilityRead(currentPct=0.0, historicalAvgPct=0.0, sessionPct=0.0, percentile=50.0, expectedPct=0.0, detail="No real candle data sampled yet.")
    momentum = MomentumRead(rocPct=0.0, strength="steady", detail="No real candle data sampled yet.")
    institutional = InstitutionalActivityRead(volumePriceDivergenceScore=0.0, absorptionDetected=False, symbolsFlagged=[], detail="No real candle data sampled yet.")
    return MarketIntelligenceState(
        regime="sideways_range",
        regimeLabel=_REGIME_LABEL["sideways_range"],
        regimeDetail="No watched symbols with real candle data yet.",
        quality=quality,
        volatility=volatility,
        session=compute_session(now),
        momentum=momentum,
        institutionalActivity=institutional,
        newsRisk=compute_news_risk([]),
        liquidity=[],
        structure=[],
        updatedAt=_now_iso(),
    )


def compute_market_intelligence_state(
    watchlist: list[WatchlistEntry],
    news: list[NewsItem],
    reports_history: list[MarketIntelligenceReport],
    provider: MarketDataProvider,
    *,
    now: datetime | None = None,
) -> MarketIntelligenceState:
    now = now or datetime.now(timezone.utc)
    per_symbol_candles: dict[str, list[Candle]] = {}
    for entry in watchlist:
        try:
            candles = provider.get_candles(entry.symbol, CANDLE_TIMEFRAME, CANDLE_WINDOW)
        except ValueError:
            continue
        if candles:
            per_symbol_candles[entry.symbol] = candles

    if not per_symbol_candles:
        state = default_market_intelligence_state(now=now)
        return state.model_copy(update={"news_risk": compute_news_risk(news)})

    structure_reads = [compute_market_structure(symbol, candles) for symbol, candles in per_symbol_candles.items()]
    liquidity_reads = [compute_liquidity(symbol, candles) for symbol, candles in per_symbol_candles.items()]

    trends = [trend_pct(c) for c in per_symbol_candles.values()]
    vols = [volatility_pct(c) for c in per_symbol_candles.values()]
    recent_vols = [volatility_pct(c[-RECENT_WINDOW:]) for c in per_symbol_candles.values()]
    avg_trend = mean(trends)
    avg_abs_trend = mean(abs(t) for t in trends)
    avg_vol = mean(vols)
    vol_ratio = mean((rv / v if v else 1.0) for rv, v in zip(recent_vols, vols))
    sweep_share = (sum(1 for lr in liquidity_reads if lr.sweep_detected) / len(liquidity_reads)) if liquidity_reads else 0.0

    long_enough = [c for c in per_symbol_candles.values() if len(c) >= 8]
    reversal_share = 0.0
    if long_enough:
        first_halves = [trend_pct(c[: len(c) // 2]) for c in long_enough]
        second_halves = [trend_pct(c[len(c) // 2 :]) for c in long_enough]
        reversals = sum(1 for a, b in zip(first_halves, second_halves) if abs(a) >= 0.5 and abs(b) >= 0.5 and (a > 0) != (b > 0))
        reversal_share = reversals / len(long_enough)

    volume_ratios: list[float] = []
    for candles in per_symbol_candles.values():
        if len(candles) < RECENT_WINDOW * 2:
            continue
        recent_avg = mean(c.volume for c in candles[-RECENT_WINDOW:])
        historical_avg = mean(c.volume for c in candles[:-RECENT_WINDOW]) or 1.0
        volume_ratios.append(recent_avg / historical_avg if historical_avg else 1.0)
    volume_trend = mean(volume_ratios) if volume_ratios else 1.0

    regime, regime_label, regime_detail = _classify_regime(avg_trend, avg_abs_trend, avg_vol, vol_ratio, sweep_share, reversal_share, volume_trend)

    session = compute_session(now)
    momentum = _momentum_read(per_symbol_candles)
    institutional = _institutional_activity_read(per_symbol_candles)
    news_risk = compute_news_risk(news)

    current_pct = mean(recent_vols)
    volatility = VolatilityRead(
        currentPct=round(current_pct, 2),
        historicalAvgPct=round(avg_vol, 2),
        sessionPct=round(_session_volatility(per_symbol_candles, session.current), 2),
        percentile=round(_volatility_percentile(current_pct, avg_vol), 1),
        expectedPct=round(avg_vol, 2),
        detail=f"Current {current_pct:.2f}% vs trailing average {avg_vol:.2f}% across {len(per_symbol_candles)} tracked symbol(s).",
    )

    quality = compute_market_quality(regime, volatility, session, sweep_share, news_risk, structure_reads, reports_history, data_symbol_count=len(per_symbol_candles))

    return MarketIntelligenceState(
        regime=regime,
        regimeLabel=regime_label,
        regimeDetail=regime_detail,
        quality=quality,
        volatility=volatility,
        session=session,
        momentum=momentum,
        institutionalActivity=institutional,
        newsRisk=news_risk,
        liquidity=liquidity_reads,
        structure=structure_reads,
        updatedAt=_now_iso(),
    )


# ---------------------------------------------------------------------
# Executive Market Brief — one real, permanent snapshot per real day.
# ---------------------------------------------------------------------


def generate_market_intelligence_report(state: MarketIntelligenceState, debate: MarketDebate, strategy_match: StrategyMatch, *, sim_day: int) -> MarketIntelligenceReport:
    return MarketIntelligenceReport(
        id=f"mireport-{sim_day}",
        simDay=sim_day,
        snapshot=state,
        debate=debate,
        strategyMatch=strategy_match,
        tradeRecommendation=_QUALITY_TO_ACTION[state.quality.tier],
        confidencePct=state.quality.confidence_pct,
        evidence=state.quality.evidence,
        createdAt=_now_iso(),
    )


def record_market_intelligence_report(history: list[MarketIntelligenceReport], report: MarketIntelligenceReport) -> list[MarketIntelligenceReport]:
    updated = [*history, report]
    if len(updated) > MAX_MARKET_INTELLIGENCE_REPORTS:
        del updated[: len(updated) - MAX_MARKET_INTELLIGENCE_REPORTS]
    return updated


# ---------------------------------------------------------------------
# Learning Loop.
# ---------------------------------------------------------------------


def filter_trades_for_day(trade_history: list[PaperTrade], sim_day: int) -> list[PaperTrade]:
    return [t for t in trade_history if t.closed_sim_minutes // 1440 == sim_day]


def filter_environment_entries_for_day(timeline: list[MarketEnvironmentEntry], sim_day: int) -> list[MarketEnvironmentEntry]:
    return [e for e in timeline if e.sim_minutes // 1440 == sim_day]


def generate_learning_entry(report: MarketIntelligenceReport, environment_entries_that_day: list[MarketEnvironmentEntry], trades_closed_that_day: list[PaperTrade]) -> MarketIntelligenceLearningEntry:
    actual = environment_entries_that_day[-1].regime if environment_entries_that_day else None
    consistent = (actual in REGIME_CONSISTENCY_MAP[report.snapshot.regime]) if actual is not None else None

    win_rate: float | None = None
    if trades_closed_that_day:
        wins = sum(1 for t in trades_closed_that_day if t.pnl > 0)
        win_rate = round(wins / len(trades_closed_that_day) * 100, 1)

    if consistent is None and win_rate is None:
        lesson = "No real regime change or closed trade was recorded that day — nothing real to compare this read against yet."
    elif consistent is False:
        lesson = f"The predicted {report.snapshot.regime.replace('_', ' ')} regime did not match the real {actual} environment recorded that day — worth revisiting the classification thresholds."
    elif win_rate is not None and win_rate < 40.0:
        lesson = f"Real trades closed that day won only {win_rate:.0f}% of the time despite a {report.snapshot.quality.tier.replace('_', ' ')} quality read — worth a closer look."
    else:
        lesson = "The read held up against what actually happened that day."

    return MarketIntelligenceLearningEntry(
        id=f"mi-learning-{report.sim_day}",
        forSimDay=report.sim_day,
        predictedRegime=report.snapshot.regime,
        predictedQualityTier=report.snapshot.quality.tier,
        actualEnvironmentRegime=actual,
        regimeConsistent=consistent,
        tradesClosedThatDay=len(trades_closed_that_day),
        tradesWinRatePct=win_rate,
        lesson=lesson,
        createdAt=_now_iso(),
    )


def record_learning_entry(history: list[MarketIntelligenceLearningEntry], entry: MarketIntelligenceLearningEntry) -> list[MarketIntelligenceLearningEntry]:
    updated = [*history, entry]
    if len(updated) > MAX_MARKET_INTELLIGENCE_LEARNING:
        del updated[: len(updated) - MAX_MARKET_INTELLIGENCE_LEARNING]
    return updated
