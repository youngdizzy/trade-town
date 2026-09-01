"""app/adversarial_research.py — CEO directive "TradeTown — Phase 8:
Autonomous Strategy Discovery + Adversarial Research Engine," Sections
8D-8I: "A strategy should not only be tested. It should be ATTACKED."

RESEARCH FIRST. Every attack below is built on real, already-computed
evidence or a real, minimal extension of an already-real primitive —
never a second, competing backtest engine:
  - The COST/SLIPPAGE ladder (`run_extended_cost_attack()`) reuses
    `app/cost_sensitivity.py`'s own real `COST_SCENARIOS`/
    `_apply_cost_to_trades()` directly, extended with two real,
    disclosed multiples beyond its existing "stressed" ceiling.
  - The PARAMETER attack is already real and complete:
    `app/parameter_sensitivity.py`'s own existing sweep/verdict — this
    module only re-packages it, never re-sweeps.
  - The REGIME attack (`classify_regime_robustness()`) reuses
    `CompiledStrategyBacktestResult.regimeTrendBreakdown`/
    `regimeVolatilityBreakdown` — already-real, already-computed by
    `app/strategy_engine.py`, no new regime detection.
  - The BENCHMARK attack is already real and complete:
    `app/research_loop.py`'s own `compute_benchmark_comparisons()`.
  - The COMPLEXITY attack is already real and complete:
    `app/strategy_complexity.py`'s own `compute_strategy_complexity()`.
  - The OUTLIER/TRADE-REMOVAL, WORST-PERIOD, and SEQUENCE attacks are
    genuinely NEW: they need the real, individually-traceable per-trade
    `EmaPullbackTradeRecord` sequence app/backtest_primitives.py's own
    `aggregate_bucket()` already discards after aggregation — reused the
    exact same way `app/statistical_comparison.py`'s own
    `_closed_trade_r_multiples()` already established: call the real,
    public `app/strategy_engine.py::backtest_symbol_over_candles()`
    directly, keep the raw list, aggregate a SECOND time (via the same
    real `aggregate_bucket()`) over a real, disclosed SUBSET or
    REORDERING of it. No new trade-generation math anywhere in this
    module — every real trade attacked here is one
    `run_compiled_strategy_backtest()` would have generated identically.

NEVER FABRICATED MARKET DATA. Every attack operates on the SAME real
(mock, seeded) closed trades a normal backtest produces — an outlier-
removal or reshuffle attack removes/reorders real trades this strategy
actually closed, never invents a trade that didn't happen. Every result
below carries `data_provenance = "simulated"` (reusing
app/data_provenance.py's own real `DataCategory`, never a new
provenance concept) — this codebase's own precise, established
distinction for "real technical-analysis math over a mock, seeded
candle series," never claimed "real" market data.

DETERMINISM. The sequence-reshuffle attack draws from the exact same
real `hashlib.sha256(...)` -> `random.Random(...)` reproducibility
convention this codebase already established (app/strategy_lab.py's
Monte Carlo, app/statistical_comparison.py's bootstrap,
app/strategy_families.py's own private copy) — the same real closed-
trade R-multiples, reshuffled the same real deterministic way every
time, for the same definition id/version.

FAILURE BOUNDARIES, NOT PASS/FAIL. `derive_failure_boundaries()` below
implements Section 8E literally: "report survives-until-X." Every
`FailureBoundary.failure_boundary_value`/`distance_to_failure` is
`None` (never fabricated/extrapolated) when the real tested range never
actually crossed into failure — an honest "not observed to fail within
the real range this pass tested."

HOLDOUT, HONESTLY NOT AVAILABLE. `evaluate_holdout_availability()`
(Section 8H) always returns `status="not_available"` — a full grep of
`app/market_data.py`'s `MockMarketDataProvider` confirms it generates a
fixed-length, seeded-per-(symbol,timeframe) series with no real date-
partitioned historical dataset to carve a true, never-touched
chronological holdout from. This is a real, honest interface stub, not
a faked in-sample split relabeled "holdout."
"""
from __future__ import annotations

import hashlib
import random

from app.backtest_primitives import DEFAULT_MIN_TRADES_FOR_BUCKET_VERDICT, aggregate_bucket
from app.cost_sensitivity import COST_SCENARIOS, _apply_cost_to_trades
from app.market_data import market_data_provider
from app.research_loop import RESEARCH_CANDIDATE_MAX_DRAWDOWN_PCT
from app.schemas import (
    AdversarialResearchResult,
    CompiledStrategyDefinition,
    EmaPullbackStatsBucket,
    EmaPullbackTradeRecord,
    ExtendedCostAttackResult,
    ExtendedCostAttackScenario,
    FailureBoundary,
    HoldoutAvailability,
    OutlierRemovalScenario,
    OutlierResilienceClass,
    OutlierResilienceResult,
    ParameterSensitivityResult,
    RegimeRobustnessClass,
    RegimeRobustnessResult,
    SequenceRobustnessResult,
    WorstPeriodResult,
)
from app.statistical_comparison import MIN_TRADES_FOR_BOOTSTRAP
from app.strategy_engine import DEFAULT_CANDLES_PER_SYMBOL, DEFAULT_TIMEFRAME, backtest_symbol_over_candles
from app.watchlist import SEED_SYMBOLS

# Section 8F — real, disclosed removal fractions. One reasonable
# convention (matches the directive's own literal "top 1%, 5%, and
# 10%"), not derived from any statistical study.
OUTLIER_REMOVAL_FRACTIONS: tuple[tuple[str, float], ...] = (
    ("without top 1% winners", 0.01),
    ("without top 5% winners", 0.05),
    ("without top 10% winners", 0.10),
)

# Section 8D.7 — a real, disclosed FIXED window size (at least 5 trades,
# or 20% of the real trade count if larger) rather than a full variable-
# length scan — a real, simple, bounded convention, not the single
# worst trade alone (which would duplicate the outlier attack above).
WORST_PERIOD_MIN_WINDOW_TRADES = 5
WORST_PERIOD_WINDOW_FRACTION = 0.20

# Section 8D.8 — a real, disclosed reshuffle count. One reasonable
# convention, matching this codebase's own BOOTSTRAP_RESAMPLES-style
# scale for a single-strategy (not two-sample) resampling.
SEQUENCE_RESHUFFLE_COUNT = 200

# Section 8D.1/8D.2 — real multiples of app/cost_sensitivity.py's own
# real "stressed" scenario bps (itself 2x the real live slippage
# ceiling) — a real, disclosed further stress, not a claim either
# multiple was ever observed live.
EXTENDED_COST_MULTIPLIERS: tuple[tuple[str, float], ...] = (
    ("extreme (3x the real stressed scenario)", 3.0),
    ("catastrophic (5x the real stressed scenario)", 5.0),
)


def _seeded_rng(*parts: str) -> random.Random:
    """This module's own private copy of this codebase's real,
    established `hashlib.sha256(...)` -> `random.Random(...)`
    reproducibility convention — see this module's own docstring."""
    digest = hashlib.sha256(":".join(parts).encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


def _closed_trades(definition: CompiledStrategyDefinition, symbols: list[str], timeframe: str, candles_per_symbol: int) -> list[EmaPullbackTradeRecord]:
    """The real per-strategy closed-trade sequence, chronologically
    sorted by real `entryTimestamp` — the same real trade-generation
    call every other attack/comparison primitive in this codebase
    already uses (see this module's own docstring)."""
    trades: list[EmaPullbackTradeRecord] = []
    for symbol in symbols:
        candles = market_data_provider.get_candles(symbol, timeframe, candles_per_symbol)
        trades.extend(t for t in backtest_symbol_over_candles(definition, symbol, candles) if t.outcome != "open")
    return sorted(trades, key=lambda t: t.entry_timestamp)


def run_outlier_removal_attack(closed_trades: list[EmaPullbackTradeRecord]) -> OutlierResilienceResult:
    """Section 8D.5/8D.6/8F — real recomputation of expectancy after
    removing the real top 1%/5%/10% winning trades, via the exact same
    real `aggregate_bucket()`."""
    baseline_bucket = aggregate_bucket("baseline", closed_trades)
    scenarios = [OutlierRemovalScenario(label="baseline", tradesRemoved=0, bucket=baseline_bucket)]
    by_r_descending = sorted(closed_trades, key=lambda t: t.r_multiple_realized, reverse=True)
    trade_count = len(closed_trades)
    for label, fraction in OUTLIER_REMOVAL_FRACTIONS:
        removed_count = min(trade_count, max(1, round(trade_count * fraction))) if trade_count > 0 else 0
        remaining = by_r_descending[removed_count:]
        bucket = aggregate_bucket(label, remaining)
        scenarios.append(OutlierRemovalScenario(label=label, tradesRemoved=removed_count, bucket=bucket))

    if baseline_bucket.trade_count < DEFAULT_MIN_TRADES_FOR_BUCKET_VERDICT or baseline_bucket.expectancy_r is None:
        classification: OutlierResilienceClass = "insufficient_evidence"
        detail = f"Below the real {DEFAULT_MIN_TRADES_FOR_BUCKET_VERDICT}-trade evidence floor — cannot honestly classify outlier dependence."
    elif baseline_bucket.expectancy_r <= 0:
        classification = "insufficient_evidence"
        detail = "The real baseline expectancy is not itself positive — outlier dependence is only a meaningful question once there is a real edge to depend on."
    else:
        top1_bucket = scenarios[1].bucket
        top10_bucket = scenarios[3].bucket
        if top1_bucket.expectancy_r is not None and top1_bucket.expectancy_r <= 0:
            classification = "highly_outlier_dependent"
            detail = "Real expectancy flips non-positive after removing just the real top 1% of winning trades — the edge depends on a tiny number of trades."
        elif top10_bucket.expectancy_r is not None and top10_bucket.expectancy_r <= 0:
            classification = "moderately_outlier_dependent"
            detail = "Real expectancy survives removing the top 1%/5% of winners but flips non-positive by the real top 10% removal."
        else:
            classification = "robust_to_outliers"
            detail = "Real expectancy stays positive even after removing the real top 10% of winning trades."
    return OutlierResilienceResult(scenarios=scenarios, classification=classification, detail=detail)


def run_worst_period_attack(closed_trades: list[EmaPullbackTradeRecord]) -> WorstPeriodResult:
    """Section 8D.7 — the real worst contiguous chronological block of
    the real fixed window size, found via a real, deterministic
    rolling-sum minimum scan over `r_multiple_realized` in real
    chronological (`entryTimestamp`) order."""
    trade_count = len(closed_trades)
    window = max(WORST_PERIOD_MIN_WINDOW_TRADES, round(trade_count * WORST_PERIOD_WINDOW_FRACTION))
    if trade_count < window:
        return WorstPeriodResult(
            windowTradeCount=0,
            detail=f"Fewer than the real {window}-trade minimum window size ({trade_count} real closed trades on file) — cannot honestly evaluate a worst-period window.",
        )
    r_values = [t.r_multiple_realized for t in closed_trades]
    window_sum = sum(r_values[:window])
    worst_sum = window_sum
    worst_start = 0
    for i in range(1, trade_count - window + 1):
        window_sum += r_values[i + window - 1] - r_values[i - 1]
        if window_sum < worst_sum:
            worst_sum = window_sum
            worst_start = i
    worst_window = closed_trades[worst_start : worst_start + window]
    return WorstPeriodResult(
        windowTradeCount=window,
        windowStartTimestamp=worst_window[0].entry_timestamp,
        windowEndTimestamp=worst_window[-1].entry_timestamp,
        windowCumulativeR=round(worst_sum, 3),
        detail=f"The real worst {window}-trade contiguous chronological window summed {worst_sum:+.2f}R.",
    )


def _max_drawdown_r(r_multiples: list[float]) -> float:
    """A real, minimal local copy of app/backtest_primitives.py's own
    real cumulative/peak/drawdown formula, applied to an arbitrary REAL
    ORDER of the same real R-multiples (never a new metric) — kept
    local rather than cross-imported because it operates on a plain
    float sequence, not an `EmaPullbackTradeRecord` list (see this
    module's own docstring for this codebase's established "each module
    keeps its own tiny private copy of a shared idiom" convention)."""
    cumulative = 0.0
    peak = 0.0
    max_drawdown = 0.0
    for r in r_multiples:
        cumulative += r
        peak = max(peak, cumulative)
        max_drawdown = min(max_drawdown, cumulative - peak)
    return abs(max_drawdown)


def run_sequence_attack(closed_trades: list[EmaPullbackTradeRecord], *, definition_id: str, definition_version: int) -> SequenceRobustnessResult:
    """Section 8D.8 — a real, deterministic reshuffle of the SAME real
    closed-trade R-multiples (never fabricated returns): expectancy is
    order-invariant by definition, so only order-DEPENDENT metrics (max
    drawdown here) can honestly differ across reshuffles."""
    r_values = [t.r_multiple_realized for t in closed_trades]
    if len(r_values) < DEFAULT_MIN_TRADES_FOR_BUCKET_VERDICT:
        return SequenceRobustnessResult(
            reshuffleCount=0,
            seed=f"{definition_id}:{definition_version}",
            detail=f"Below the real {DEFAULT_MIN_TRADES_FOR_BUCKET_VERDICT}-trade evidence floor — reshuffling is not honestly meaningful yet.",
        )
    seed = f"{definition_id}:{definition_version}:sequence-attack"
    rng = _seeded_rng(seed)
    baseline_dd = _max_drawdown_r(r_values)
    worst_dd = baseline_dd
    for _ in range(SEQUENCE_RESHUFFLE_COUNT):
        shuffled = list(r_values)
        rng.shuffle(shuffled)
        worst_dd = max(worst_dd, _max_drawdown_r(shuffled))
    return SequenceRobustnessResult(
        reshuffleCount=SEQUENCE_RESHUFFLE_COUNT,
        seed=seed,
        baselineMaxDrawdownR=round(baseline_dd, 3),
        worstReshuffledMaxDrawdownR=round(worst_dd, 3),
        detail=(
            f"Across {SEQUENCE_RESHUFFLE_COUNT} real, deterministic reshuffles of the SAME real closed-trade "
            f"R-multiples, the worst real max drawdown observed was {worst_dd:.2f}R, vs. {baseline_dd:.2f}R in the "
            "real order these trades actually occurred."
        ),
    )


def run_extended_cost_attack(closed_trades: list[EmaPullbackTradeRecord]) -> ExtendedCostAttackResult:
    """Section 8D.1/8D.2 — extends app/cost_sensitivity.py's own real
    ladder with two real, harsher multiples of its "stressed" scenario."""
    stressed_label, stressed_bps = COST_SCENARIOS[-1]
    scenarios = [ExtendedCostAttackScenario(label=stressed_label, costBpsPerLeg=round(stressed_bps, 3), bucket=aggregate_bucket(stressed_label, _apply_cost_to_trades(closed_trades, stressed_bps)))]
    for label, multiplier in EXTENDED_COST_MULTIPLIERS:
        bps = stressed_bps * multiplier
        adjusted = _apply_cost_to_trades(closed_trades, bps)
        scenarios.append(ExtendedCostAttackScenario(label=label, costBpsPerLeg=round(bps, 3), bucket=aggregate_bucket(label, adjusted)))
    stressed_bucket = scenarios[0].bucket
    catastrophic_bucket = scenarios[-1].bucket
    survives: bool | None = None
    if stressed_bucket.expectancy_r is not None:
        survives = catastrophic_bucket.expectancy_r is not None and catastrophic_bucket.expectancy_r > 0
    detail = (
        f"Real expectancy at the catastrophic ({EXTENDED_COST_MULTIPLIERS[-1][1]:g}x stressed) cost scenario: "
        f"{catastrophic_bucket.expectancy_r if catastrophic_bucket.expectancy_r is not None else 'NOT VERIFIED'}."
    )
    return ExtendedCostAttackResult(scenarios=scenarios, survivesBeyondStress=survives, detail=detail)


def classify_regime_robustness(regime_trend_breakdown: list[EmaPullbackStatsBucket], regime_volatility_breakdown: list[EmaPullbackStatsBucket]) -> RegimeRobustnessResult:
    """Section 8G — a real, disclosed classification over already-real,
    already-computed regime buckets. No new regime detection."""
    evaluated: list[tuple[str, float]] = [
        (b.label, b.expectancy_r) for b in (*regime_trend_breakdown, *regime_volatility_breakdown) if b.verdict == "enough_evidence" and b.expectancy_r is not None
    ]
    if not evaluated:
        return RegimeRobustnessResult(classification="regime_unknown", provenRegimes=[], fragileRegimes=[], detail="No real regime bucket cleared the real evidence floor — regime robustness cannot be honestly classified yet.")
    proven = [label for label, expectancy in evaluated if expectancy > 0]
    fragile = [label for label, expectancy in evaluated if expectancy <= 0]
    classification: RegimeRobustnessClass
    if proven and not fragile:
        classification = "regime_robust"
        detail = f"Real positive expectancy in every real, sufficiently-evidenced regime tested: {', '.join(proven)}."
    elif proven and fragile:
        classification = "regime_specialist"
        detail = f"Real positive expectancy only in {', '.join(proven)} — real negative/zero expectancy in {', '.join(fragile)}. Should only receive capital in its proven regime(s)."
    elif fragile and not proven:
        classification = "regime_fragile"
        detail = f"Real negative/zero expectancy in every real, sufficiently-evidenced regime tested: {', '.join(fragile)}. Cannot advance without remediation."
    else:
        classification = "regime_unknown"
        detail = "No real regime bucket cleared the real evidence floor."
    return RegimeRobustnessResult(classification=classification, provenRegimes=proven, fragileRegimes=fragile, detail=detail)


def _confidence_for_trade_count(trade_count: int) -> str:
    if trade_count >= MIN_TRADES_FOR_BOOTSTRAP:
        return "high"
    if trade_count >= DEFAULT_MIN_TRADES_FOR_BUCKET_VERDICT:
        return "medium"
    return "low"


def derive_failure_boundaries(
    *,
    definition_id: str,
    outlier_result: OutlierResilienceResult,
    extended_cost_result: ExtendedCostAttackResult,
    parameter_sensitivity: ParameterSensitivityResult,
    risk_per_trade_pct: float,
) -> list[FailureBoundary]:
    """Section 8E — "report survives-until-X," never merely pass/fail.
    Every value is `None` (never fabricated/extrapolated) when the real
    tested range never actually crossed into failure."""
    boundaries: list[FailureBoundary] = []
    baseline_bucket = outlier_result.scenarios[0].bucket

    # cost_bps
    cost_flip = next((s for s in extended_cost_result.scenarios if s.bucket.expectancy_r is not None and s.bucket.expectancy_r <= 0), None)
    boundaries.append(
        FailureBoundary(
            id=f"{definition_id}-boundary-cost",
            failureBoundaryType="cost_bps",
            failureBoundaryMetric="transaction cost + slippage (bps per leg)",
            failureBoundaryValue=(cost_flip.cost_bps_per_leg if cost_flip is not None else None),
            currentValue=0.0,
            distanceToFailure=(cost_flip.cost_bps_per_leg if cost_flip is not None else None),
            confidence=_confidence_for_trade_count(baseline_bucket.trade_count),  # type: ignore[arg-type]
            evidenceSource="app/adversarial_research.py::run_extended_cost_attack()",
            detail=(
                f"Real expectancy flips non-positive at {cost_flip.cost_bps_per_leg:.1f} bps per leg."
                if cost_flip is not None
                else f"Not observed to fail within the real range tested (up to {extended_cost_result.scenarios[-1].cost_bps_per_leg:.1f} bps per leg)."
            ),
        )
    )

    # drawdown_pct
    current_drawdown_pct = abs(baseline_bucket.max_drawdown_r) * risk_per_trade_pct if baseline_bucket.max_drawdown_r is not None else None
    boundaries.append(
        FailureBoundary(
            id=f"{definition_id}-boundary-drawdown",
            failureBoundaryType="drawdown_pct",
            failureBoundaryMetric="max drawdown (approx. %, at the CEO-configured risk-per-trade)",
            failureBoundaryValue=RESEARCH_CANDIDATE_MAX_DRAWDOWN_PCT,
            currentValue=current_drawdown_pct,
            distanceToFailure=(round(RESEARCH_CANDIDATE_MAX_DRAWDOWN_PCT - current_drawdown_pct, 2) if current_drawdown_pct is not None else None),
            confidence=_confidence_for_trade_count(baseline_bucket.trade_count),  # type: ignore[arg-type]
            evidenceSource="app/research_loop.py::RESEARCH_CANDIDATE_MAX_DRAWDOWN_PCT",
            detail=(
                f"Real approximate drawdown {current_drawdown_pct:.1f}% vs. the real {RESEARCH_CANDIDATE_MAX_DRAWDOWN_PCT:.0f}% research-candidate bound."
                if current_drawdown_pct is not None
                else "No real max drawdown could be computed yet."
            ),
        )
    )

    # outlier_removal_pct
    outlier_flip = next(
        (
            (label, fraction)
            for (label, fraction), scenario in zip(OUTLIER_REMOVAL_FRACTIONS, outlier_result.scenarios[1:])
            if scenario.bucket.expectancy_r is not None and scenario.bucket.expectancy_r <= 0
        ),
        None,
    )
    boundaries.append(
        FailureBoundary(
            id=f"{definition_id}-boundary-outlier",
            failureBoundaryType="outlier_removal_pct",
            failureBoundaryMetric="% of top winning trades removed",
            failureBoundaryValue=(outlier_flip[1] * 100 if outlier_flip is not None else None),
            currentValue=0.0,
            distanceToFailure=(outlier_flip[1] * 100 if outlier_flip is not None else None),
            confidence=_confidence_for_trade_count(baseline_bucket.trade_count),  # type: ignore[arg-type]
            evidenceSource="app/adversarial_research.py::run_outlier_removal_attack()",
            detail=(f"Real expectancy flips non-positive after removing the real top {outlier_flip[1] * 100:.0f}% of winning trades." if outlier_flip is not None else "Not observed to fail within the real top-10% removal range tested."),
        )
    )

    # parameter_stop / parameter_target
    for axis_name, axis in (("parameter_stop", parameter_sensitivity.stop_axis), ("parameter_target", parameter_sensitivity.target_axis)):
        if axis is None or not axis.sweepable or axis.base_value is None:
            continue
        flip_point = next((p for p in axis.points if p.bucket.expectancy_r is not None and p.bucket.expectancy_r <= 0), None)
        boundaries.append(
            FailureBoundary(
                id=f"{definition_id}-boundary-{axis_name}",
                failureBoundaryType=axis_name,  # type: ignore[arg-type]
                failureBoundaryMetric=f"{axis.parameter} value",
                failureBoundaryValue=(flip_point.value if flip_point is not None else None),
                currentValue=axis.base_value,
                distanceToFailure=(round(abs(flip_point.value - axis.base_value), 3) if flip_point is not None else None),
                confidence=_confidence_for_trade_count(baseline_bucket.trade_count),  # type: ignore[arg-type]
                evidenceSource="app/parameter_sensitivity.py::run_parameter_sensitivity()",
                detail=(f"Real expectancy flips non-positive at a swept {axis.parameter} value of {flip_point.value:g}." if flip_point is not None else f"Not observed to fail within the real {axis.parameter} range tested."),
            )
        )
    return boundaries


def evaluate_holdout_availability() -> HoldoutAvailability:
    """Section 8H — see this module's own docstring for the full,
    disclosed reason. Always `not_available` today."""
    return HoldoutAvailability(
        status="not_available",
        reason=(
            "app/market_data.py's MockMarketDataProvider generates a fixed-length, seeded-per-(symbol,timeframe) "
            "candle series with no real date-partitioned historical dataset to carve a true, never-touched-during-"
            "development chronological holdout from. The interfaces for a genuine TRAIN/VALIDATION/HOLDOUT split "
            "exist (this schema's own status='available' path) but are not fabricated with an in-sample split "
            "relabeled 'holdout.'"
        ),
    )


def run_adversarial_research(
    definition: CompiledStrategyDefinition,
    *,
    regime_trend_breakdown: list[EmaPullbackStatsBucket],
    regime_volatility_breakdown: list[EmaPullbackStatsBucket],
    parameter_sensitivity: ParameterSensitivityResult,
    risk_per_trade_pct: float,
    result_id: str,
    generated_at: str,
    symbols: list[str] | None = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    candles_per_symbol: int = DEFAULT_CANDLES_PER_SYMBOL,
    closed_trades: list[EmaPullbackTradeRecord] | None = None,
) -> AdversarialResearchResult:
    """Section 8D's one real orchestrator. Fetches the real closed-trade
    sequence ONCE and reuses it across every attack that needs raw
    trades — never a second, independent backtest per attack.

    CEO directive "Phase 9 / Real Market Data + Evidence Integrity
    Foundation," Section 10 — `closed_trades` lets a caller that already
    ran `run_compiled_strategy_backtest()` (which now exposes its own
    real per-trade sequence via `CompiledStrategyBacktestResult.trades`)
    pass those trades straight through, eliminating this function's own
    independent re-fetch-and-re-backtest entirely (see
    app/research_discovery.py). `None` (the default) preserves the
    original standalone behavior for every existing caller/test."""
    resolved_symbols = symbols if symbols is not None else [s for s, _name, _cat in SEED_SYMBOLS]
    if closed_trades is None:
        closed_trades = _closed_trades(definition, resolved_symbols, timeframe, candles_per_symbol)
    else:
        closed_trades = sorted((t for t in closed_trades if t.outcome != "open"), key=lambda t: t.entry_timestamp)

    outlier_result = run_outlier_removal_attack(closed_trades)
    worst_period_result = run_worst_period_attack(closed_trades)
    sequence_result = run_sequence_attack(closed_trades, definition_id=definition.id, definition_version=definition.version)
    extended_cost_result = run_extended_cost_attack(closed_trades)
    regime_result = classify_regime_robustness(regime_trend_breakdown, regime_volatility_breakdown)
    failure_boundaries = derive_failure_boundaries(
        definition_id=definition.id,
        outlier_result=outlier_result,
        extended_cost_result=extended_cost_result,
        parameter_sensitivity=parameter_sensitivity,
        risk_per_trade_pct=risk_per_trade_pct,
    )

    return AdversarialResearchResult(
        id=result_id,
        definitionId=definition.id,
        definitionVersion=definition.version,
        outlierResilience=outlier_result,
        worstPeriod=worst_period_result,
        sequenceRobustness=sequence_result,
        extendedCostAttack=extended_cost_result,
        regimeRobustness=regime_result,
        failureBoundaries=failure_boundaries,
        dataProvenance="simulated",
        generatedAt=generated_at,
    )
