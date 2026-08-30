"""app/ema_pullback_research.py — CEO directive "Professional Trading
Firm — Market-Analysis Knowledge + Session Intelligence Expansion,"
Phase 15: the 50 EMA breakout + pullback strategy.

RESEARCH FIRST. A full grep audit of this codebase (see
docs/Architecture.md's "Phase 5-7" scoping under the prior "Next Phase:
Professional Trading Firm Intelligence" directive) found no Chandelier
Stop implementation, no bar-by-bar strategy rule engine, and no real
walk-forward/backtest pipeline anywhere — `app/simulation.py`'s own
`SimulationResult` generator is explicitly-placeholder RNG math (see
that module's docstring), never a real replay of real candle history.
This module is the first real, deterministic, bar-by-bar rule replay in
this codebase — built specifically for this one strategy, not a general
StrategyRuleEngine (that remains the larger, still-deferred Phase 5-7
undertaking; see docs/Architecture.md). `app/strategy_lab.py`'s existing
Monte Carlo bootstrap (`run_strategy_monte_carlo()`) and
`app/model_validation.py`'s existing validation report
(`generate_model_validation_report()`) are REUSED unchanged — this
module builds an ad hoc, non-persisted `Strategy`/`SimulationResult`
pair from its own real backtest numbers and hands them to that already-
real machinery rather than writing a second one.

THE SOURCE MATERIAL IS NOT TRADETOWN EVIDENCE. The CEO-supplied strategy
claims an approximate 65.6% win rate (21 winners / 32 trades) from one
educational example. `SOURCE_CLAIM_*` constants below exist ONLY to be
displayed alongside TradeTown's own independently-computed numbers in
`EmaPullbackSourceClaimComparison` — they are never read by any
computation in this module, and this module never asserts the strategy
is profitable, never guarantees a win rate, and never treats the
source's claimed backtest as proof of anything. Every number this module
reports is a real, bar-by-bar figure computed against this codebase's
own real (mock, procedurally-generated, seeded, reproducible) OHLCV
candle series (`app/market_data.py`) — never a real market, never
fabricated.

THE RULES, MADE MEASURABLE. The source material's own language
("looks like a strong pullback," "clean breakout") is exactly the
discretionary phrasing this directive forbids leaving un-converted. Real
operational definitions used below:

  Sustained side          "Price has been trading below/above the 50
                          EMA" is operationalized as at least
                          `MIN_BARS_ON_SIDE_BEFORE_CROSS` consecutive
                          real closes on that side immediately before
                          the cross bar — a real, disclosed threshold
                          standing in for the source's own vaguer
                          phrase, not an assumption the source endorses.
  EMA cross + confirm     A real close on the opposite side of the 50
                          EMA from the prior bar's close (rules 2-3 /
                          short mirror 2-3), checked directly against
                          the real `ema_series()` value at that bar.
  Pullback                At least `MIN_PULLBACK_CANDLES` (2) real,
                          strictly consecutive opposite-direction
                          candles (close < open for a long's pullback,
                          close > open for a short's). A single opposite
                          candle does NOT count as "the pullback" — the
                          leg keeps extending and TradeTown keeps
                          watching for a real 2+-candle pullback later
                          in the same leg, exactly the source's own "at
                          least two" wording.
  Confirmation level      The real high (long) / low (short) reached
                          during the leg from the EMA cross through the
                          bar immediately before the pullback began —
                          the literal "swing high/low immediately before
                          the pullback," not `app/market_intelligence.
                          py`'s more general 3-bar-lookback swing
                          definition (a different, disclosed, situation-
                          specific measurement, not a duplicate of it).
  Breakout confirmation   A real candle whose own close trades beyond
                          the confirmation level (`close > level` long /
                          `close < level` short) — the literal "body
                          must close above/below the level."
  Entry                   The REAL NEXT bar's open after the
                          confirmation candle closes — never the
                          confirmation candle's own close itself, which
                          would be look-ahead (you cannot know a bar
                          closed strongly beyond a level until it
                          finishes). A real, disclosed backtest execution
                          assumption; a live implementation entering
                          intrabar at/near that close would produce
                          different, not directly comparable, numbers.
  Invalidation A          Checked every bar from the moment a leg begins
                          until entry: if a real close crosses back
                          through the 50 EMA before the breakout
                          confirms, the whole state resets to idle — a
                          fresh EMA cross is required before any new
                          setup is considered. TradeTown never re-enters
                          later merely because price eventually reaches
                          the original confirmation level, exactly the
                          source's own explicit warning.
  Invalidation B          NOT a hard filter, per the directive's own
                          explicit warning against hardcoding "3x or 4x"
                          as universally invalid. Every breakout
                          candle's own real range is compared to the
                          real average range of the `RECENT_RANGE_
                          LOOKBACK` bars immediately before it;
                          `breakoutCandleExtended` is `True` when that
                          ratio reaches `EXTENDED_BREAKOUT_RANGE_RATIO`
                          — a real, disclosed, TAGGING-ONLY threshold.
                          `breakoutSizeBreakdown` then reports whether
                          extended-candle trades actually have different
                          real expectancy in this data, an empirical
                          question, never an assumed answer.
  Chandelier Stop         The real, standard Chuck LeBeau formula:
                          `highest_high(CHANDELIER_ATR_PERIOD bars
                          before entry) - CHANDELIER_ATR_MULTIPLIER *
                          ATR(same window)` for a long (mirrored for a
                          short) — both `CHANDELIER_ATR_PERIOD=22` and
                          `CHANDELIER_ATR_MULTIPLIER=3.0` are the
                          methodology's own standard, commonly-published
                          defaults, not TradeTown-invented numbers.
  R-multiple target       `entry_price +/- r_multiple * (entry_price -
                          stop_price)`, swept across `R_MULTIPLES_
                          TESTED` — the source's own ~2:1 target is
                          `REFERENCE_R_MULTIPLE`, tested here as ONE
                          candidate among several, never assumed optimal
                          in advance (per the directive's own explicit
                          instruction).
  Exit simulation         A real forward walk of up to `MAX_HOLD_BARS`
                          real bars from entry: the stop and the target
                          are each checked against every real bar's
                          high/low; if both are touched on the same bar
                          (a real gap-through), the stop is conservatively
                          assumed to have been hit first (the standard,
                          disclosed conservative backtesting convention
                          — never assumed to have hit the more favorable
                          outcome). A trade that touches neither within
                          `MAX_HOLD_BARS` is reported as `"open"` and
                          excluded from win/loss statistics — never
                          fabricated into a forced outcome.

REGIME/SESSION TAGGING — A DISCLOSED, SIMPLER PROXY, NOT A DUPLICATE.
`app/market_intelligence.py`'s real 13-way `MarketIntelligenceRegime`
classifier (`_classify_regime()`) needs live, cross-symbol sweep-share/
reversal-share/volume-trend inputs that only exist as this game's live,
per-tick state — there is no function anywhere in this codebase that
reconstructs those inputs at an arbitrary historical bar, and building
one is a real, separate undertaking this directive's own Rule 15 ("do
not start unrelated future pieces") argues against attempting inside
this pass. ARCHITECTURALLY BLOCKED for the full 13-way classifier at
historical points; NOT blocked for a real, simpler, self-contained
proxy computed only from each symbol's own candle series (50 EMA slope
for trend; ATR vs. its own trailing median for volatility) — see
`_regime_trend_at()`/`_regime_volatility_at()`. `entrySession` uses the
real, already-reused `_session_for_hour()` — no second session engine.

WHAT THIS MODULE DOES NOT DO. It never wires into `app/research.py`'s
confidence gauge, `app/confidence.py`, or any live trade decision — no
agent is forced to trade this strategy, and "no trade" (in this context,
"this research remains inconclusive") is a fully valid outcome, exactly
Phase 9's own rule. It never creates a second risk engine, never
bypasses the Trade Gatekeeper, and never bypasses Model Validation —
`generate_model_validation_report()`'s real, unmodified checks (now
including this same directive's own Phase 8 anti-overfitting checks)
independently challenge this run's own results. Live game state is
never touched: every `Strategy`/`SimulationResult` this module builds
is a local, non-persisted value, computed fresh on request, discarded
after the response — the same CAGS (Computed-Always, Grounded, Stateless)
convention this whole directive's earlier phases already established.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.backtest_primitives import aggregate_bucket, breakout_candle_range_ratio, chandelier_stop, ema_at, regime_trend_at, regime_volatility_at, simulate_exit
from app.market_data import Candle, market_data_provider
from app.market_intelligence import _session_for_hour
from app.model_validation import generate_model_validation_report
from app.schemas import (
    EmaPullbackResearchResult,
    EmaPullbackSourceClaimComparison,
    EmaPullbackTradeRecord,
    ModelValidationReport,
    SimulationResult,
    Strategy,
    StrategyMonteCarloResult,
)
from app.strategy_lab import run_strategy_monte_carlo
from app.technical_indicators import atr_series, ema_series
from app.watchlist import SEED_SYMBOLS

# ---------------------------------------------------------------------
# Disclosed research parameters. None of these are fitted to this data
# -- each is either a standard, published methodology default
# (Chandelier Stop) or a plain, disclosed operationalization of the
# source material's own English-language rules (see module docstring).
# ---------------------------------------------------------------------

EMA_PERIOD = 50
MIN_BARS_ON_SIDE_BEFORE_CROSS = 5
MIN_PULLBACK_CANDLES = 2
CHANDELIER_ATR_PERIOD = 22
CHANDELIER_ATR_MULTIPLIER = 3.0
GENERAL_ATR_PERIOD = 14
R_MULTIPLES_TESTED: tuple[float, ...] = (1.0, 1.5, 2.0, 2.5, 3.0)
REFERENCE_R_MULTIPLE = 2.0
DEFAULT_TIMEFRAME = "1h"
DEFAULT_CANDLES_PER_SYMBOL = 6000
MAX_HOLD_BARS = 150
RECENT_RANGE_LOOKBACK = 20
EXTENDED_BREAKOUT_RANGE_RATIO = 2.0
TREND_SLOPE_LOOKBACK = 20
TREND_SLOPE_THRESHOLD_PCT = 0.5
VOLATILITY_MEDIAN_LOOKBACK = 100
VOLATILITY_HIGH_RATIO = 1.3
VOLATILITY_LOW_RATIO = 0.7
MIN_TRADES_FOR_BUCKET_VERDICT = 10

SOURCE_CLAIM_TRADE_COUNT = 32
SOURCE_CLAIM_WINNERS = 21
SOURCE_CLAIM_WIN_RATE_PCT = round(SOURCE_CLAIM_WINNERS / SOURCE_CLAIM_TRADE_COUNT * 100, 1)
SOURCE_CLAIM_NOTE = (
    "The CEO-supplied source material reports approximately a 65.6% win rate (21 winners / 32 trades) from one "
    "educational example backtest. This is a SOURCE CLAIM, not TradeTown-validated evidence — it is never used as "
    "an input to any computation in this module. TradeTown's own real win rate at the same ~2R reference target, "
    "computed independently below, must never be assumed equal to it."
)
DATA_HONESTY_NOTE = (
    "Every candle in this run is app/market_data.py's own real, procedurally-generated (seeded, reproducible) mock "
    "OHLCV series — never real historical market data. All win/loss/expectancy/drawdown numbers below are real, "
    "computed bar-by-bar outcomes of this exact rule set replayed against that real (mock) series — never "
    "fabricated, never assumed. This is TradeTown's own internal evidence standard, not external market validation."
)

HYPOTHESIS = (
    "After a sustained period below/above the 50 EMA, a confirmed EMA breakout (close-confirmed) followed by a "
    "structured two-or-more-candle pullback and a body-close breakout of the pre-pullback swing level produces "
    "positive real expectancy in TradeTown's own (mock) candle history, at some tested R-multiple target, in at "
    "least some tested session/regime/instrument condition — to be confirmed or rejected by the real evidence "
    "below, never assumed true in advance."
)


@dataclass
class _Setup:
    direction: str  # "long" | "short"
    entry_index: int
    entry_price: float
    stop_price: float
    confirmation_index: int
    breakout_range_ratio: float
    breakout_extended: bool


def _hour_of(candle: Candle) -> float:
    ts = datetime.fromisoformat(candle.timestamp)
    return ts.hour + ts.minute / 60.0


def _detect_setups(candles: list[Candle], ema50: list[float]) -> list[_Setup]:
    """A single real forward pass implementing the state machine
    described in this module's own docstring. Long and short setups
    share one state machine, since real price sits on only one side of
    the 50 EMA at a time."""
    setups: list[_Setup] = []
    phase = "idle"  # idle -> pullback_wait -> in_pullback -> awaiting_breakout
    direction = ""
    leg_extreme = 0.0
    confirmation_level = 0.0
    pullback_count = 0

    for i in range(EMA_PERIOD, len(candles)):
        c = candles[i]
        ema_now = ema_at(ema50, EMA_PERIOD, i)
        ema_prev = ema_at(ema50, EMA_PERIOD, i - 1)
        if ema_now is None or ema_prev is None:
            continue

        if phase == "idle":
            crossed_up = candles[i - 1].close <= ema_prev and c.close > ema_now
            crossed_down = candles[i - 1].close >= ema_prev and c.close < ema_now
            # The real "sustained side" check: how many consecutive real
            # bars closed on the opposite side immediately before this
            # cross bar.
            prior_side_run = 0
            if crossed_up or crossed_down:
                j = i - 1
                target_below = crossed_up
                while j >= EMA_PERIOD:
                    ema_j = ema_at(ema50, EMA_PERIOD, j)
                    if ema_j is None:
                        break
                    on_side = candles[j].close < ema_j if target_below else candles[j].close > ema_j
                    if not on_side:
                        break
                    prior_side_run += 1
                    j -= 1
            if (crossed_up or crossed_down) and prior_side_run >= MIN_BARS_ON_SIDE_BEFORE_CROSS:
                direction = "long" if crossed_up else "short"
                phase = "pullback_wait"
                leg_extreme = c.high if direction == "long" else c.low
                pullback_count = 0
            continue

        # Invalidation A -- checked every bar once a leg is active.
        if (direction == "long" and c.close < ema_now) or (direction == "short" and c.close > ema_now):
            phase = "idle"
            direction = ""
            continue

        is_opposite = (c.close < c.open) if direction == "long" else (c.close > c.open)

        if phase == "pullback_wait":
            if is_opposite:
                phase = "in_pullback"
                pullback_count = 1
            else:
                leg_extreme = max(leg_extreme, c.high) if direction == "long" else min(leg_extreme, c.low)
            continue

        if phase == "in_pullback":
            if is_opposite:
                pullback_count += 1
                continue
            if pullback_count >= MIN_PULLBACK_CANDLES:
                confirmation_level = leg_extreme
                broke = c.close > confirmation_level if direction == "long" else c.close < confirmation_level
                if broke:
                    ratio = breakout_candle_range_ratio(candles, i, recent_range_lookback=RECENT_RANGE_LOOKBACK)
                    entry_index = i + 1
                    if entry_index < len(candles):
                        setups.append(
                            _Setup(
                                direction=direction,
                                entry_index=entry_index,
                                entry_price=candles[entry_index].open,
                                stop_price=0.0,  # filled in by the caller once ATR is available
                                confirmation_index=i,
                                breakout_range_ratio=ratio,
                                breakout_extended=ratio >= EXTENDED_BREAKOUT_RANGE_RATIO,
                            )
                        )
                    phase = "idle"
                    direction = ""
                else:
                    phase = "awaiting_breakout"
            else:
                # Fewer than the required opposite candles -- this dip
                # never became "the pullback"; keep extending the leg.
                phase = "pullback_wait"
                leg_extreme = max(leg_extreme, c.high) if direction == "long" else min(leg_extreme, c.low)
            continue

        if phase == "awaiting_breakout":
            broke = c.close > confirmation_level if direction == "long" else c.close < confirmation_level
            if broke:
                ratio = breakout_candle_range_ratio(candles, i, recent_range_lookback=RECENT_RANGE_LOOKBACK)
                entry_index = i + 1
                if entry_index < len(candles):
                    setups.append(
                        _Setup(
                            direction=direction,
                            entry_index=entry_index,
                            entry_price=candles[entry_index].open,
                            stop_price=0.0,
                            confirmation_index=i,
                            breakout_range_ratio=ratio,
                            breakout_extended=ratio >= EXTENDED_BREAKOUT_RANGE_RATIO,
                        )
                    )
                phase = "idle"
                direction = ""
            continue

    return setups


def _detect_naive_crosses(candles: list[Candle], ema50: list[float]) -> list[_Setup]:
    """The baseline this research compares against: enter immediately on
    a real, sustained-side-confirmed EMA cross, with no pullback/
    breakout confirmation requirement at all. Same Chandelier Stop, same
    R-multiple targets — isolates whether the pullback+breakout
    confirmation step adds real value over a naive cross entry."""
    setups: list[_Setup] = []
    bars_below = 0
    bars_above = 0
    for i in range(EMA_PERIOD, len(candles)):
        c = candles[i]
        ema_now = ema_at(ema50, EMA_PERIOD, i)
        ema_prev = ema_at(ema50, EMA_PERIOD, i - 1)
        if ema_now is None or ema_prev is None:
            continue
        crossed_up = candles[i - 1].close <= ema_prev and c.close > ema_now
        crossed_down = candles[i - 1].close >= ema_prev and c.close < ema_now
        if crossed_up or crossed_down:
            prior_run = bars_below if crossed_up else bars_above
            if prior_run >= MIN_BARS_ON_SIDE_BEFORE_CROSS:
                entry_index = i + 1
                if entry_index < len(candles):
                    setups.append(
                        _Setup(
                            direction="long" if crossed_up else "short",
                            entry_index=entry_index,
                            entry_price=candles[entry_index].open,
                            stop_price=0.0,
                            confirmation_index=i,
                            breakout_range_ratio=1.0,
                            breakout_extended=False,
                        )
                    )
        if c.close < ema_now:
            bars_below += 1
            bars_above = 0
        elif c.close > ema_now:
            bars_above += 1
            bars_below = 0
    return setups


def _build_trade_records(
    symbol: str,
    candles: list[Candle],
    setups: list[_Setup],
    ema50: list[float],
    atr_chandelier: list[float],
    atr_general: list[float],
    r_multiple: float,
) -> list[EmaPullbackTradeRecord]:
    records: list[EmaPullbackTradeRecord] = []
    for setup in setups:
        stop_price = chandelier_stop(candles, atr_chandelier, setup.entry_index, setup.direction, atr_period=CHANDELIER_ATR_PERIOD, atr_multiplier=CHANDELIER_ATR_MULTIPLIER)
        if stop_price is None:
            continue
        entry_price = setup.entry_price
        risk = abs(entry_price - stop_price)
        if risk <= 0:
            continue
        target_price = entry_price + r_multiple * risk if setup.direction == "long" else entry_price - r_multiple * risk
        path = candles[setup.entry_index + 1 : setup.entry_index + 1 + MAX_HOLD_BARS]
        exit_result = simulate_exit(setup.direction, entry_price, stop_price, target_price, path)
        entry_candle = candles[setup.entry_index]
        records.append(
            EmaPullbackTradeRecord(
                symbol=symbol,
                direction="long" if setup.direction == "long" else "short",  # type: ignore[arg-type]
                entryTimestamp=entry_candle.timestamp,
                entryPrice=entry_price,
                stopPrice=stop_price,
                targetPrice=round(target_price, 4),
                exitPrice=exit_result.exit_price,
                outcome=exit_result.outcome,
                rMultipleRealized=exit_result.r_multiple_realized,
                entrySession=_session_for_hour(_hour_of(entry_candle)),
                regimeTrend=regime_trend_at(ema50, EMA_PERIOD, setup.entry_index, slope_lookback=TREND_SLOPE_LOOKBACK, slope_threshold_pct=TREND_SLOPE_THRESHOLD_PCT),
                regimeVolatility=regime_volatility_at(atr_general, GENERAL_ATR_PERIOD, setup.entry_index, median_lookback=VOLATILITY_MEDIAN_LOOKBACK, high_ratio=VOLATILITY_HIGH_RATIO, low_ratio=VOLATILITY_LOW_RATIO),
                breakoutCandleExtended=setup.breakout_extended,
                breakoutCandleRangeRatio=setup.breakout_range_ratio,
                maeR=exit_result.mae_r,
                mfeR=exit_result.mfe_r,
                barsHeld=exit_result.bars_held,
            )
        )
    return records


def run_ema_pullback_research(
    *,
    symbols: list[str] | None = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    candles_per_symbol: int = DEFAULT_CANDLES_PER_SYMBOL,
    sim_day: int = 0,
) -> EmaPullbackResearchResult:
    """The full research experiment. `symbols` defaults to every real
    seed-watchlist symbol (real Instrument coverage, per the directive's
    own TEST VARIABLES list). Computed fresh on every call — nothing
    here is persisted or cached."""
    test_symbols = symbols if symbols is not None else [s for s, _name, _cat in SEED_SYMBOLS]

    all_trades_by_r: dict[float, list[EmaPullbackTradeRecord]] = {r: [] for r in R_MULTIPLES_TESTED}
    reference_trades: list[EmaPullbackTradeRecord] = []
    naive_trades: list[EmaPullbackTradeRecord] = []
    per_symbol_trade_counts: dict[str, int] = {}

    for symbol in test_symbols:
        candles = market_data_provider.get_candles(symbol, timeframe, candles_per_symbol)
        if len(candles) < EMA_PERIOD + MIN_BARS_ON_SIDE_BEFORE_CROSS + MAX_HOLD_BARS:
            continue
        ema50 = ema_series(candles, EMA_PERIOD)
        atr_chandelier = atr_series(candles, CHANDELIER_ATR_PERIOD)
        atr_general = atr_series(candles, GENERAL_ATR_PERIOD)

        setups = _detect_setups(candles, ema50)
        per_symbol_trade_counts[symbol] = len(setups)
        for r in R_MULTIPLES_TESTED:
            trades = _build_trade_records(symbol, candles, setups, ema50, atr_chandelier, atr_general, r)
            all_trades_by_r[r].extend(trades)
            if r == REFERENCE_R_MULTIPLE:
                reference_trades.extend(trades)

        naive_setups = _detect_naive_crosses(candles, ema50)
        naive_trades.extend(_build_trade_records(symbol, candles, naive_setups, ema50, atr_chandelier, atr_general, REFERENCE_R_MULTIPLE))

    r_multiple_sweep = [aggregate_bucket(f"{r:g}R", all_trades_by_r[r], min_trades_for_verdict=MIN_TRADES_FOR_BUCKET_VERDICT) for r in R_MULTIPLES_TESTED]

    session_buckets: dict[str, list[EmaPullbackTradeRecord]] = {}
    for t in reference_trades:
        session_buckets.setdefault(t.entry_session, []).append(t)
    session_breakdown = [aggregate_bucket(session, trades, min_trades_for_verdict=MIN_TRADES_FOR_BUCKET_VERDICT) for session, trades in sorted(session_buckets.items())]

    trend_buckets: dict[str, list[EmaPullbackTradeRecord]] = {}
    for t in reference_trades:
        trend_buckets.setdefault(t.regime_trend, []).append(t)
    regime_trend_breakdown = [aggregate_bucket(trend, trades, min_trades_for_verdict=MIN_TRADES_FOR_BUCKET_VERDICT) for trend, trades in sorted(trend_buckets.items())]

    vol_buckets: dict[str, list[EmaPullbackTradeRecord]] = {}
    for t in reference_trades:
        vol_buckets.setdefault(t.regime_volatility, []).append(t)
    regime_volatility_breakdown = [aggregate_bucket(vol, trades, min_trades_for_verdict=MIN_TRADES_FOR_BUCKET_VERDICT) for vol, trades in sorted(vol_buckets.items())]

    instrument_buckets: dict[str, list[EmaPullbackTradeRecord]] = {}
    for t in reference_trades:
        instrument_buckets.setdefault(t.symbol, []).append(t)
    instrument_breakdown = [aggregate_bucket(sym, trades, min_trades_for_verdict=MIN_TRADES_FOR_BUCKET_VERDICT) for sym, trades in sorted(instrument_buckets.items())]

    extended = [t for t in reference_trades if t.breakout_candle_extended]
    normal = [t for t in reference_trades if not t.breakout_candle_extended]
    breakout_size_breakdown = [
        aggregate_bucket(f"extended (range >= {EXTENDED_BREAKOUT_RANGE_RATIO:g}x recent avg)", extended, min_trades_for_verdict=MIN_TRADES_FOR_BUCKET_VERDICT),
        aggregate_bucket("normal", normal, min_trades_for_verdict=MIN_TRADES_FOR_BUCKET_VERDICT),
    ]

    confirmed_vs_naive_baseline = [
        aggregate_bucket("confirmed (pullback + breakout)", reference_trades, min_trades_for_verdict=MIN_TRADES_FOR_BUCKET_VERDICT),
        aggregate_bucket("naive (EMA cross only, no confirmation)", naive_trades, min_trades_for_verdict=MIN_TRADES_FOR_BUCKET_VERDICT),
    ]

    tradetown_bucket = aggregate_bucket("reference", reference_trades, min_trades_for_verdict=MIN_TRADES_FOR_BUCKET_VERDICT)
    closed_reference = [t for t in reference_trades if t.outcome != "open"]
    source_claim_comparison = EmaPullbackSourceClaimComparison(
        sourceClaimTradeCount=SOURCE_CLAIM_TRADE_COUNT,
        sourceClaimWinners=SOURCE_CLAIM_WINNERS,
        sourceClaimWinRatePct=SOURCE_CLAIM_WIN_RATE_PCT,
        tradetownTradeCount=len(closed_reference),
        tradetownWinRatePct=tradetown_bucket.win_rate_pct,
        detail=SOURCE_CLAIM_NOTE,
    )

    # Reuse the existing Strategy Lab machinery unchanged: an ad hoc,
    # non-persisted Strategy/SimulationResult pair built from this run's
    # own real numbers, one SimulationResult per symbol with a real
    # closed-trade sample at the reference R-multiple.
    now_iso = datetime.now(timezone.utc).isoformat()
    strategy = Strategy(
        id="research-ema50-pullback",
        name="50 EMA Breakout + Pullback (Research)",
        description="CEO directive Phase 15 research hypothesis — see app/ema_pullback_research.py.",
        createdBy="quant",
        focusCategory="stock",
        createdAt=now_iso,
    )
    simulation_results: list[SimulationResult] = []
    for symbol, trades in instrument_buckets.items():
        closed = [t for t in trades if t.outcome != "open"]
        if len(closed) < 2:
            continue
        wins = [t for t in closed if t.outcome == "win"]
        losses = [t for t in closed if t.outcome == "loss"]
        win_rate = len(wins) / len(closed) * 100
        avg_win_pct = (sum(t.r_multiple_realized for t in wins) / len(wins)) if wins else 0.0
        avg_loss_pct = (sum(abs(t.r_multiple_realized) for t in losses) / len(losses)) if losses else 0.0
        total_return_pct = sum(t.r_multiple_realized for t in closed)
        cumulative = 0.0
        peak = 0.0
        max_dd = 0.0
        for t in sorted(closed, key=lambda x: x.entry_timestamp):
            cumulative += t.r_multiple_realized
            peak = max(peak, cumulative)
            max_dd = min(max_dd, cumulative - peak)
        expected_value_pct = (len(wins) / len(closed)) * avg_win_pct - (len(losses) / len(closed)) * avg_loss_pct
        gross_win = sum(t.r_multiple_realized for t in wins)
        gross_loss = sum(abs(t.r_multiple_realized) for t in losses)
        profit_factor = (gross_win / gross_loss) if gross_loss > 0 else 0.0
        simulation_results.append(
            SimulationResult(
                id=f"research-ema50-pullback-{symbol}",
                strategyId=strategy.id,
                strategyName=strategy.name,
                symbol=symbol,
                totalReturnPct=round(total_return_pct, 2),
                winRate=round(win_rate, 1),
                maxDrawdownPct=round(abs(max_dd), 2),
                sharpeRatio=0.0,
                sortinoRatio=0.0,
                tradeCount=len(closed),
                runBy="quant",
                completedAt=now_iso,
                scenario="historical",
                winCount=len(wins),
                lossCount=len(losses),
                avgWinPct=round(avg_win_pct, 2),
                avgLossPct=round(avg_loss_pct, 2),
                expectedValuePct=round(expected_value_pct, 3),
                profitFactor=round(profit_factor, 3),
                riskRewardRatio=round(avg_win_pct / avg_loss_pct, 3) if avg_loss_pct > 0 else 0.0,
                dataProvenance="simulated",
            )
        )

    monte_carlo: StrategyMonteCarloResult | None = None
    model_validation: ModelValidationReport | None = None
    if simulation_results:
        monte_carlo = run_strategy_monte_carlo(strategy, simulation_results, sim_day=sim_day)
        model_validation = generate_model_validation_report(
            strategy,
            simulation_results,
            monte_carlo,
            None,  # No StrategyRegimeTestReport -- this module's own real session/regime breakdowns above cover that ground with a different, disclosed methodology; never fabricated to fit that shape.
            None,  # No StrategyLiquidityValidation -- out of this module's scope.
            review_id=f"research-ema50-pullback-{sim_day}",
            existing_review_count=0,
            sim_day=sim_day,
        )

    return EmaPullbackResearchResult(
        id=f"ema50-pullback-research-{sim_day}",
        hypothesis=HYPOTHESIS,
        rulesDisclosure=__doc__ or "",
        symbolsTested=test_symbols,
        timeframe=timeframe,
        candlesPerSymbol=candles_per_symbol,
        referenceRMultiple=REFERENCE_R_MULTIPLE,
        rMultipleSweep=r_multiple_sweep,
        sessionBreakdown=session_breakdown,
        regimeTrendBreakdown=regime_trend_breakdown,
        regimeVolatilityBreakdown=regime_volatility_breakdown,
        instrumentBreakdown=instrument_breakdown,
        breakoutSizeBreakdown=breakout_size_breakdown,
        confirmedVsNaiveBaseline=confirmed_vs_naive_baseline,
        sourceClaimComparison=source_claim_comparison,
        modelValidation=model_validation,
        monteCarlo=monte_carlo,
        dataHonestyNote=DATA_HONESTY_NOTE,
        generatedAt=now_iso,
    )
