"""app/strategy_engine.py — CEO directive "Professional Quant Trading
Firm — Quant Intelligence + Market Analysis Completion Phase," Phase F:
the generic backtest runner for a `CompiledStrategyDefinition`
(app/strategy_compiler.py).

WHAT THIS GENERALIZES, AND WHAT IT DOESN'T. app/ema_pullback_
research.py's own hand-built `_detect_setups()` implements exactly one
real strategy's exact rule shape in hardcoded Python control flow. This
module lifts that same real shape — trigger -> optional pullback-style
requirement -> entry, then a real Chandelier/swing/percent stop and a
real R-multiple/percent target — into a GENERIC interpreter driven by a
`CompiledStrategyDefinition`'s own structured fields, so any strategy
app/strategy_compiler.py can compile into that same shape is directly
backtestable without new Python code being written for it. This is a
disclosed, honest v1 scope, not a claim of full generality: an
arbitrary sequence topology (multiple chained requirements, nested
conditions, pattern-based conditions referencing app/technical_
patterns.py) is real, tractable future work, not attempted here — see
`SUPPORTED_INDICATORS` below for exactly which `StrategyIndicatorName`
values this engine can resolve today (only the ones app/strategy_
compiler.py's current vocabulary can ever produce: price fields, ema,
sma). A definition referencing an indicator outside that set is refused
up front with a clear, honest reason — never silently run with a
partially-broken interpretation.

ONE AUTHORITATIVE IMPLEMENTATION. This module reuses
app/backtest_primitives.py's `chandelier_stop()`/`simulate_exit()`/
`aggregate_bucket()` — the exact same real math app/ema_pullback_
research.py's own hand-built engine uses — never a second copy. It also
reuses app/technical_indicators.py's `ema_series()`/`sma_series()` for
every indicator value it resolves; no indicator math is re-derived here.

NEVER BACKTESTS AN UNRESOLVED DEFINITION. `status != "compiled"` (an
ambiguous or invalid `CompiledStrategyDefinition`) is refused outright —
this module never fills in a guessed value to make an incomplete
definition "runnable."

Same non-negotiables as every other real backtest in this codebase:
never wired into any live trading decision, never bypasses the
Gatekeeper/Risk Authority, never a second risk or validation engine
(reuses app/strategy_lab.py's Monte Carlo bootstrap and
app/model_validation.py's validation report exactly as app/ema_
pullback_research.py already does), and "no trade" / "this definition
cannot yet be backtested" remain fully valid, honestly reported outcomes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from app.backtest_primitives import aggregate_bucket, breakout_candle_range_ratio, chandelier_stop, ema_at, regime_trend_at, regime_volatility_at, simulate_exit
from app.market_data import Candle, market_data_provider
from app.market_intelligence import _session_for_hour
from app.model_validation import generate_model_validation_report
from app.schemas import (
    CompiledStrategyBacktestResult,
    CompiledStrategyDefinition,
    EmaPullbackTradeRecord,
    ModelValidationReport,
    SimulationResult,
    Strategy,
    StrategyIndicatorRef,
    StrategyMonteCarloResult,
)
from app.strategy_lab import run_strategy_monte_carlo
from app.technical_indicators import atr_series, ema_series, sma_series
from app.watchlist import SEED_SYMBOLS

# The only StrategyIndicatorName values app/strategy_compiler.py's
# current vocabulary can ever produce — see that module's own
# `STATUS_COVERAGE_NOTE`. Growing this set is real, tractable future
# work paired with growing the compiler's own recognized phrasing.
SUPPORTED_INDICATORS = frozenset({"price_close", "price_open", "price_high", "price_low", "ema", "sma"})

DEFAULT_TIMEFRAME = "1h"
DEFAULT_CANDLES_PER_SYMBOL = 6000
MAX_HOLD_BARS = 150
MIN_BARS_ON_SIDE_BEFORE_CROSS = 5

# The same disclosed regime-proxy and breakout-size-tagging defaults
# app/ema_pullback_research.py's own module docstring already discloses
# and justifies — reused here (via app/backtest_primitives.py's shared
# regime_trend_at()/regime_volatility_at()/breakout_candle_range_ratio())
# rather than re-derived, so every compiled strategy this engine
# backtests is tagged by the exact same real, disclosed proxy.
REGIME_EMA_PERIOD = 50
REGIME_ATR_PERIOD = 14
TREND_SLOPE_LOOKBACK = 20
TREND_SLOPE_THRESHOLD_PCT = 0.5
VOLATILITY_MEDIAN_LOOKBACK = 100
VOLATILITY_HIGH_RATIO = 1.3
VOLATILITY_LOW_RATIO = 0.7
RECENT_RANGE_LOOKBACK = 20
EXTENDED_BREAKOUT_RANGE_RATIO = 2.0


def _unsupported_indicators(definition: CompiledStrategyDefinition) -> set[str]:
    found: set[str] = set()
    for step in definition.sequence:
        if step.condition is None:
            continue
        for ref in (step.condition.left, step.condition.right_indicator):
            if ref is not None and ref.indicator not in SUPPORTED_INDICATORS:
                found.add(ref.indicator)
    return found


@dataclass
class _SeriesCache:
    ema: dict[int, list[float]]
    sma: dict[int, list[float]]


def _build_series_cache(candles: list[Candle], definition: CompiledStrategyDefinition) -> _SeriesCache:
    ema_periods: set[int] = set()
    sma_periods: set[int] = set()
    for step in definition.sequence:
        if step.condition is None:
            continue
        for ref in (step.condition.left, step.condition.right_indicator):
            if ref is None or ref.period is None:
                continue
            if ref.indicator == "ema":
                ema_periods.add(ref.period)
            elif ref.indicator == "sma":
                sma_periods.add(ref.period)
    # A chandelier stop's own ATR series is a real volatility read, not
    # an EMA/SMA period — computed separately in the caller, not cached
    # here.
    return _SeriesCache(
        ema={p: ema_series(candles, p) for p in ema_periods},
        sma={p: sma_series(candles, p) for p in sma_periods},
    )


def _resolve(ref: StrategyIndicatorRef, candles: list[Candle], series: _SeriesCache, index: int) -> float | None:
    if ref.indicator == "price_close":
        return candles[index].close
    if ref.indicator == "price_open":
        return candles[index].open
    if ref.indicator == "price_high":
        return candles[index].high
    if ref.indicator == "price_low":
        return candles[index].low
    if ref.indicator == "ema" and ref.period is not None:
        return ema_at(series.ema.get(ref.period, []), ref.period, index)
    if ref.indicator == "sma" and ref.period is not None:
        return ema_at(series.sma.get(ref.period, []), ref.period, index)
    return None


def _resolve_right(ref_indicator: StrategyIndicatorRef | None, ref_value: float | None, candles: list[Candle], series: _SeriesCache, index: int) -> float | None:
    if ref_indicator is not None:
        return _resolve(ref_indicator, candles, series, index)
    return ref_value


def _compare(left: float, operator: str, right: float) -> bool:
    if operator == "gt":
        return left > right
    if operator == "gte":
        return left >= right
    if operator == "lt":
        return left < right
    if operator == "lte":
        return left <= right
    if operator == "eq":
        return left == right
    raise ValueError(f"_compare does not handle real crossing operators ({operator}) — use _crossed instead")


@dataclass
class _GenericSetup:
    direction: str  # "long" | "short"
    entry_index: int
    entry_price: float
    stop_price: float
    pullback_low: float | None
    pullback_high: float | None


def _detect_generic_setups(candles: list[Candle], definition: CompiledStrategyDefinition, series: _SeriesCache) -> list[_GenericSetup]:
    """Real, generic interpretation of the exact trigger -> optional
    requirement -> entry shape app/strategy_compiler.py's current
    vocabulary produces — see this module's own docstring for why this
    is a disclosed v1 scope, not a fully arbitrary sequence executor."""
    trigger_step = next((s for s in definition.sequence if s.step_type == "trigger"), None)
    requirement_step = next((s for s in definition.sequence if s.step_type == "requirement"), None)
    entry_step = next((s for s in definition.sequence if s.step_type == "entry"), None)
    if trigger_step is None or trigger_step.condition is None or entry_step is None:
        return []

    condition = trigger_step.condition
    setups: list[_GenericSetup] = []
    phase = "idle"  # idle -> pullback_wait -> in_pullback -> awaiting_breakout
    direction = ""
    leg_extreme = 0.0
    pullback_low = 0.0
    pullback_high = 0.0
    confirmation_level = 0.0
    pullback_count = 0
    min_start = max((ref.period or 0) for ref in (condition.left, condition.right_indicator) if ref is not None) if any(r is not None for r in (condition.left, condition.right_indicator)) else 0

    for i in range(min_start, len(candles)):
        if i == 0:
            continue
        left_now = _resolve(condition.left, candles, series, i)
        left_prev = _resolve(condition.left, candles, series, i - 1)
        right_now = _resolve_right(condition.right_indicator, condition.right_value, candles, series, i)
        right_prev = _resolve_right(condition.right_indicator, condition.right_value, candles, series, i - 1)
        if left_now is None or left_prev is None or right_now is None or right_prev is None:
            continue

        if phase == "idle":
            if condition.operator in ("crosses_above", "crosses_below"):
                crossed_up = left_prev <= right_prev and left_now > right_now
                crossed_down = left_prev >= right_prev and left_now < right_now
                wants_up = condition.operator == "crosses_above"
                triggered = crossed_up if wants_up else crossed_down
            elif condition.operator in ("gt", "gte", "lt", "lte"):
                # A real, direct threshold trigger (e.g. a future compiler
                # vocabulary addition like "RSI above 70") — fires the
                # instant the comparison is true, no crossing/continuity
                # semantics needed since there is no "sustained side" to
                # define for a bare threshold.
                wants_up = condition.operator in ("gt", "gte")
                triggered = _compare(left_now, condition.operator, right_now)
            else:
                triggered = False
                wants_up = True
            if triggered:
                prior_run = 0
                j = i - 1
                while j >= 0:
                    left_j = _resolve(condition.left, candles, series, j)
                    right_j = _resolve_right(condition.right_indicator, condition.right_value, candles, series, j)
                    if left_j is None or right_j is None:
                        break
                    on_side = (left_j < right_j) if wants_up else (left_j > right_j)
                    if not on_side:
                        break
                    prior_run += 1
                    j -= 1
                if prior_run >= MIN_BARS_ON_SIDE_BEFORE_CROSS:
                    direction = "long" if wants_up else "short"
                    c = candles[i]
                    leg_extreme = c.high if direction == "long" else c.low
                    pullback_low = c.low
                    pullback_high = c.high
                    pullback_count = 0
                    phase = "pullback_wait" if requirement_step is not None else "awaiting_breakout"
                    confirmation_level = leg_extreme
            continue

        c = candles[i]
        left_now_check = _resolve(condition.left, candles, series, i)
        right_now_check = _resolve_right(condition.right_indicator, condition.right_value, candles, series, i)
        if left_now_check is not None and right_now_check is not None:
            invalidated = (left_now_check < right_now_check) if direction == "long" else (left_now_check > right_now_check)
            if invalidated:
                phase = "idle"
                direction = ""
                continue

        if phase == "pullback_wait" and requirement_step is not None:
            is_opposite = (c.close < c.open) if requirement_step.candle_direction == "bearish" else (c.close > c.open)
            expected_opposite = requirement_step.candle_direction == ("bearish" if direction == "long" else "bullish")
            is_pullback_candle = is_opposite if expected_opposite else False
            if is_pullback_candle:
                phase = "in_pullback"
                pullback_count = 1
                pullback_low = c.low
                pullback_high = c.high
            else:
                leg_extreme = max(leg_extreme, c.high) if direction == "long" else min(leg_extreme, c.low)
            continue

        if phase == "in_pullback" and requirement_step is not None:
            is_opposite = (c.close < c.open) if requirement_step.candle_direction == "bearish" else (c.close > c.open)
            if is_opposite:
                pullback_count += 1
                pullback_low = min(pullback_low, c.low)
                pullback_high = max(pullback_high, c.high)
                continue
            min_bars = requirement_step.min_consecutive_bars or 1
            if pullback_count >= min_bars:
                confirmation_level = leg_extreme
                broke = c.close > confirmation_level if direction == "long" else c.close < confirmation_level
                if broke:
                    entry_index = i + 1
                    if entry_index < len(candles):
                        setups.append(
                            _GenericSetup(
                                direction=direction,
                                entry_index=entry_index,
                                entry_price=candles[entry_index].open,
                                stop_price=0.0,
                                pullback_low=pullback_low,
                                pullback_high=pullback_high,
                            )
                        )
                    phase = "idle"
                    direction = ""
                else:
                    phase = "awaiting_breakout"
            else:
                phase = "pullback_wait"
                leg_extreme = max(leg_extreme, c.high) if direction == "long" else min(leg_extreme, c.low)
            continue

        if phase == "awaiting_breakout":
            broke = c.close > confirmation_level if direction == "long" else c.close < confirmation_level
            if broke:
                entry_index = i + 1
                if entry_index < len(candles):
                    setups.append(
                        _GenericSetup(
                            direction=direction,
                            entry_index=entry_index,
                            entry_price=candles[entry_index].open,
                            stop_price=0.0,
                            pullback_low=pullback_low if requirement_step is not None else None,
                            pullback_high=pullback_high if requirement_step is not None else None,
                        )
                    )
                phase = "idle"
                direction = ""
            continue

    return setups


def _resolve_stop(definition: CompiledStrategyDefinition, candles: list[Candle], atr_series_values: list[float], setup: _GenericSetup) -> float | None:
    stop = definition.stop
    if stop is None:
        return None
    if stop.method == "chandelier":
        if stop.atr_period is None or stop.atr_multiplier is None:
            return None
        return chandelier_stop(candles, atr_series_values, setup.entry_index, setup.direction, atr_period=stop.atr_period, atr_multiplier=stop.atr_multiplier)
    if stop.method == "swing_level":
        if setup.pullback_low is None or setup.pullback_high is None:
            return None
        return setup.pullback_low if setup.direction == "long" else setup.pullback_high
    if stop.method == "fixed_percent" and stop.percent is not None:
        entry = setup.entry_price
        return round(entry * (1 - stop.percent / 100) if setup.direction == "long" else entry * (1 + stop.percent / 100), 4)
    return None


def _resolve_target(definition: CompiledStrategyDefinition, entry_price: float, stop_price: float, direction: str) -> float | None:
    target = definition.target
    if target is None:
        return None
    risk = abs(entry_price - stop_price)
    if target.method == "r_multiple":
        return round(entry_price + target.value * risk if direction == "long" else entry_price - target.value * risk, 4)
    if target.method == "fixed_percent":
        return round(entry_price * (1 + target.value / 100) if direction == "long" else entry_price * (1 - target.value / 100), 4)
    return None


def backtest_symbol_over_candles(definition: CompiledStrategyDefinition, symbol: str, candles: list[Candle]) -> list[EmaPullbackTradeRecord]:
    """The real per-symbol backtest core, extracted so
    `run_compiled_strategy_backtest()` below and
    `app/walk_forward.py`'s real windowed validation can share the exact
    same setup-detection -> stop/target-resolution -> exit-simulation ->
    trade-record pipeline against WHATEVER real candle slice is passed
    in — never a second copy. `app/walk_forward.py` calls this once per
    real, disjoint chronological window (a plain sub-slice of the full
    real series); this function itself has no notion of "windows," which
    is exactly what makes the no-look-ahead guarantee across windows
    structural rather than something a caller has to get right by
    convention: a call with `candles[1000:2000]` can only ever resolve
    indicators and detect setups using bars 1000-1999, full stop."""
    if len(candles) < MIN_BARS_ON_SIDE_BEFORE_CROSS + MAX_HOLD_BARS + 60:
        return []
    series = _build_series_cache(candles, definition)
    setups = _detect_generic_setups(candles, definition, series)

    atr_series_values: list[float] = []
    if definition.stop is not None and definition.stop.method == "chandelier" and definition.stop.atr_period is not None:
        atr_series_values = atr_series(candles, definition.stop.atr_period)

    regime_ema_values = ema_series(candles, REGIME_EMA_PERIOD)
    regime_atr_values = atr_series(candles, REGIME_ATR_PERIOD)

    trades: list[EmaPullbackTradeRecord] = []
    for setup in setups:
        stop_price = _resolve_stop(definition, candles, atr_series_values, setup)
        if stop_price is None:
            continue
        target_price = _resolve_target(definition, setup.entry_price, stop_price, setup.direction)
        if target_price is None:
            continue
        risk = abs(setup.entry_price - stop_price)
        if risk <= 0:
            continue
        path = candles[setup.entry_index + 1 : setup.entry_index + 1 + MAX_HOLD_BARS]
        exit_result = simulate_exit(setup.direction, setup.entry_price, stop_price, target_price, path)
        entry_candle = candles[setup.entry_index]
        ts = datetime.fromisoformat(entry_candle.timestamp)
        confirmation_index = setup.entry_index - 1
        range_ratio = breakout_candle_range_ratio(candles, confirmation_index, recent_range_lookback=RECENT_RANGE_LOOKBACK)
        trades.append(
            EmaPullbackTradeRecord(
                symbol=symbol,
                direction="long" if setup.direction == "long" else "short",  # type: ignore[arg-type]
                entryTimestamp=entry_candle.timestamp,
                entryPrice=setup.entry_price,
                stopPrice=stop_price,
                targetPrice=round(target_price, 4),
                exitPrice=exit_result.exit_price,
                outcome=exit_result.outcome,
                rMultipleRealized=exit_result.r_multiple_realized,
                entrySession=_session_for_hour(ts.hour + ts.minute / 60.0),
                regimeTrend=regime_trend_at(regime_ema_values, REGIME_EMA_PERIOD, setup.entry_index, slope_lookback=TREND_SLOPE_LOOKBACK, slope_threshold_pct=TREND_SLOPE_THRESHOLD_PCT),
                regimeVolatility=regime_volatility_at(regime_atr_values, REGIME_ATR_PERIOD, setup.entry_index, median_lookback=VOLATILITY_MEDIAN_LOOKBACK, high_ratio=VOLATILITY_HIGH_RATIO, low_ratio=VOLATILITY_LOW_RATIO),
                breakoutCandleExtended=range_ratio >= EXTENDED_BREAKOUT_RANGE_RATIO,
                breakoutCandleRangeRatio=range_ratio,
                maeR=exit_result.mae_r,
                mfeR=exit_result.mfe_r,
            )
        )
    return trades


def run_compiled_strategy_backtest(
    definition: CompiledStrategyDefinition,
    *,
    symbols: list[str] | None = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    candles_per_symbol: int = DEFAULT_CANDLES_PER_SYMBOL,
    sim_day: int = 0,
) -> CompiledStrategyBacktestResult:
    """The one real entry point. Refuses (with a clear, honest reason
    surfaced in `detail`) rather than silently guessing whenever
    `definition.status != "compiled"` or the definition references an
    indicator this engine's current v1 scope cannot resolve."""
    now_iso = datetime.now(timezone.utc).isoformat()
    test_symbols = symbols if symbols is not None else [s for s, _name, _cat in SEED_SYMBOLS]
    unsupported = _unsupported_indicators(definition)

    def _refusal(reason: str) -> CompiledStrategyBacktestResult:
        empty = aggregate_bucket("overall", [])
        return CompiledStrategyBacktestResult(
            id=f"compiled-backtest-{definition.id}-{sim_day}",
            definitionId=definition.id,
            definitionVersion=definition.version,
            symbolsTested=test_symbols,
            timeframe=timeframe,
            candlesPerSymbol=candles_per_symbol,
            overall=empty,
            dataHonestyNote=reason,
            generatedAt=now_iso,
        )

    if definition.status != "compiled":
        return _refusal(f"This definition is not backtestable: status={definition.status!r}. {definition.detail}")
    if unsupported:
        return _refusal(f"This engine's current v1 scope cannot resolve indicator(s) {sorted(unsupported)} — a real, disclosed coverage gap, not a fabricated result.")

    all_trades: list[EmaPullbackTradeRecord] = []
    instrument_buckets: dict[str, list[EmaPullbackTradeRecord]] = {}
    session_buckets: dict[str, list[EmaPullbackTradeRecord]] = {}

    for symbol in test_symbols:
        candles = market_data_provider.get_candles(symbol, timeframe, candles_per_symbol)
        trades = backtest_symbol_over_candles(definition, symbol, candles)
        for record in trades:
            all_trades.append(record)
            instrument_buckets.setdefault(symbol, []).append(record)
            session_buckets.setdefault(record.entry_session, []).append(record)

    overall = aggregate_bucket("overall", all_trades)
    instrument_breakdown = [aggregate_bucket(sym, trades) for sym, trades in sorted(instrument_buckets.items())]
    session_breakdown = [aggregate_bucket(session, trades) for session, trades in sorted(session_buckets.items())]

    strategy = Strategy(
        id=f"compiled-{definition.id}",
        name=definition.name,
        description=f"Compiled from English source text — see app/strategy_compiler.py. {definition.detail}",
        createdBy=definition.created_by,
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
                id=f"compiled-{definition.id}-{symbol}",
                strategyId=strategy.id,
                strategyName=strategy.name,
                symbol=symbol,
                totalReturnPct=round(total_return_pct, 2),
                winRate=round(win_rate, 1),
                maxDrawdownPct=round(abs(max_dd), 2),
                sharpeRatio=0.0,
                sortinoRatio=0.0,
                tradeCount=len(closed),
                runBy=definition.created_by,
                completedAt=now_iso,
                scenario="historical",
                winCount=len(wins),
                lossCount=len(losses),
                avgWinPct=round(avg_win_pct, 2),
                avgLossPct=round(avg_loss_pct, 2),
                expectedValuePct=round(expected_value_pct, 3),
                profitFactor=round(profit_factor, 3),
                riskRewardRatio=round(avg_win_pct / avg_loss_pct, 3) if avg_loss_pct > 0 else 0.0,
            )
        )

    monte_carlo: StrategyMonteCarloResult | None = None
    model_validation: ModelValidationReport | None = None
    if simulation_results:
        monte_carlo = run_strategy_monte_carlo(strategy, simulation_results, sim_day=sim_day)
        model_validation = generate_model_validation_report(
            strategy, simulation_results, monte_carlo, None, None, review_id=f"compiled-{definition.id}-{sim_day}", existing_review_count=0, sim_day=sim_day
        )

    return CompiledStrategyBacktestResult(
        id=f"compiled-backtest-{definition.id}-{sim_day}",
        definitionId=definition.id,
        definitionVersion=definition.version,
        symbolsTested=test_symbols,
        timeframe=timeframe,
        candlesPerSymbol=candles_per_symbol,
        overall=overall,
        sessionBreakdown=session_breakdown,
        instrumentBreakdown=instrument_breakdown,
        modelValidation=model_validation,
        monteCarlo=monte_carlo,
        dataHonestyNote=(
            "Every candle in this run is app/market_data.py's own real, procedurally-generated (seeded, "
            "reproducible) mock OHLCV series — never real historical market data. All win/loss/expectancy "
            "numbers below are real, computed bar-by-bar outcomes of this exact compiled definition replayed "
            "against that real (mock) series — never fabricated, never assumed."
        ),
        generatedAt=now_iso,
    )
