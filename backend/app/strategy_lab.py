"""app/strategy_lab.py — v0.7 Feature 52 (Part 1), the Strategy Validation
Laboratory.

GOAL (from the brief): "No strategy should ever be traded simply because
an employee believes it works." This module is the enrichment layer on
top of app/sandbox.py's already-real 8-stage gated pipeline (Idea ->
Research -> Historical Backtest -> Market Simulation -> Paper Trading ->
Limited Live Capital -> Company Review -> Approved) — see sandbox.py's
own module docstring for that pipeline's honesty boundary. Researched
first: this codebase already had almost every real building block the
brief's longer pipeline (Monte Carlo / Market Regime / Liquidity /
Risk / 9-department Executive Review / Founder Approval) asks for, just
not assembled into named, reported-on artifacts.

  Monte Carlo Testing        - a real trade-sequence bootstrap over the
                                strategy's own aggregated win rate and
                                average win/loss sizes (app/simulation.py's
                                own real SimulationResult fields) as the
                                generating probabilities, the exact same
                                "real derived inputs, never fabricated
                                statistics" bootstrap pattern
                                app/whatif.py's own Monte Carlo engine
                                already established for a different scope
                                (price-path resampling, not trade-sequence
                                resampling — this is a new, small, purpose-
                                built bootstrap, not a second copy of
                                whatif.py's _simulate()).
  Market Regime Testing      - reuses Feature 51's real 13-way
                                MarketIntelligenceRegime by grouping it
                                through the exact same
                                app/market_intelligence.py's own real
                                regime->TestScenario keyword mapping
                                compute_strategy_match() already uses —
                                SimulationResult is only ever tagged at
                                the coarser 7-way TestScenario grain, so
                                results are honestly bucketed at that
                                grain and each bucket is labeled with
                                which of the 13 real regimes it covers,
                                never independently tested 13 ways.
  Liquidity Validation        - reuses app/market_intelligence.py's real
                                compute_liquidity()/compute_market_structure()
                                against the strategy's own watched
                                symbols, as-is — no new liquidity math,
                                and no claim beyond what those functions
                                already claim (real equal-high/low
                                clustering + a real sweep pattern, never
                                real resting stop-order locations or
                                institutional order flow).
  Risk Analysis (a real,
  standalone gate)            - Guardian's own real average-drawdown
                                threshold (sandbox.py's RISK_MAX_AVG_DRAWDOWN)
                                now also gates market_simulation ->
                                paper_trading directly (see
                                evaluate_risk_gate() below, wired into
                                sandbox.begin_paper_trial()), honoring the
                                brief's stage order (Risk Analysis before
                                Paper Trading) — the existing five-
                                reviewer StrategyReview at Company Review
                                still runs its own richer risk verdict
                                too; this doesn't replace that, it adds
                                an earlier real checkpoint.
  Executive Review (9 depts)  - reuses the exact same nine real
                                department seats as Feature 50's
                                ExecutiveDepartmentRole (see
                                app/executive_intelligence.py's own
                                _ALL_DEPARTMENT_ROLES) — Strategy-scoped
                                instead of TradeProposal-scoped, with a
                                richer evidence/concerns/suggested-
                                improvements field set per the brief. The
                                brief's ninth seat, "Brain Room," is not a
                                distinct department anywhere in this
                                codebase (see ExecutiveIntelPanel.tsx's
                                own real/cut note) — reuses the same
                                devils_advocate seat every other 9-role
                                read in this codebase already does.
  Founder Approval             - a new mode of the exact same real
                                threshold-based approval pattern
                                app/founders.py's generate_breakthrough_review()
                                already established for Black Box
                                Projects, applied to a Strategy instead.
  Confidence Score              - a real composite built entirely from
                                the artifacts above — never independently
                                estimated. Computed fresh on request, not
                                persisted (same reasoning as
                                ExecutiveRecommendation/WhatIfSimulation:
                                every input already lives somewhere
                                permanent).
  Strategy Report (the
  brief's "professional
  report")                     - StrategyDossier assembles the real
                                artifacts above for one strategy; it is
                                not a second copy of their data.

Explicitly NOT built here, and why:
  A true "Probability Of Ruin" over infinite samples - only ever a real
                                share of this run's own N_PATHS simulated
                                paths that breached RUIN_DRAWDOWN_PCT,
                                clearly labeled as such (see
                                StrategyMonteCarloResult's own docstring).
  Real institutional liquidity /
  retail stop clusters / market
  maker behavior                - inherited directly from
                                app/market_intelligence.py's own honesty
                                boundary; not re-litigated here.
  A second backtest/Monte Carlo
  engine                        - would repeat the exact "redundant re-
                                measurement" trap app/sandbox.py's own
                                docstring already warns against; this
                                module's bootstrap reuses SimulationResult's
                                real generating statistics, never re-rolls
                                its own independent backtest.
"""
from __future__ import annotations

import hashlib
import random
from datetime import datetime, timezone

from app.market_data import Candle, MarketDataProvider
from app.market_intelligence import _REGIME_TO_SCENARIO_KEYWORD, compute_liquidity, compute_market_structure
from app.sandbox import RISK_MAX_AVG_DRAWDOWN, STRATEGY_DEVILS_ADVOCATES, stage_index
from app.schemas import (
    AgentId,
    CoachReport,
    CostSensitivityResult,
    ExecutiveDepartmentRole,
    ExecutiveStance,
    ExperimentTier,
    FailedStrategyArchiveEntry,
    LookAheadAuditResult,
    MarketIntelligenceRegime,
    MarketIntelligenceState,
    ModelValidationReport,
    ResearchItem,
    SimulationResult,
    Strategy,
    StrategyCertification,
    StrategyCertificationRequirement,
    StrategyConfidenceScore,
    StrategyDepartmentOpinion,
    StrategyDossier,
    StrategyExecutiveAction,
    StrategyExecutiveDashboard,
    StrategyExecutiveDashboardEntry,
    StrategyExecutiveReview,
    StrategyFounderApproval,
    StrategyHallOfFameEntry,
    StrategyHealthAssessment,
    StrategyHealthStatus,
    StrategyHealthTrend,
    StrategyLiquidityValidation,
    StrategyMonteCarloResult,
    StrategyRegimeBucketPerformance,
    StrategyRegimeTestReport,
    StrategyReport,
    StrategyReview,
    TestScenario,
    WalkForwardValidationResult,
    WatchlistEntry,
)

MAX_STRATEGY_MONTE_CARLO_RESULTS = 40
MAX_STRATEGY_REGIME_TESTS = 40
MAX_STRATEGY_LIQUIDITY_VALIDATIONS = 40
MAX_STRATEGY_EXECUTIVE_REVIEWS = 40
MAX_STRATEGY_FOUNDER_APPROVALS = 40
MAX_STRATEGY_HEALTH_ASSESSMENTS = 40
MAX_STRATEGY_HALL_OF_FAME = 40
MAX_STRATEGY_FAILED_ARCHIVE = 40

MONTE_CARLO_PATHS = 200
RUIN_DRAWDOWN_PCT = 50.0  # a real, named "the strategy is effectively dead" bar for this bootstrap's own paths

FOUNDER_APPROVAL_CONFIDENCE_THRESHOLD = 60.0

# v0.7 Feature 52 (Part 2) — Strategy Health's own recent-vs-lifetime
# window and status thresholds. Reuses sandbox.py's real
# RISK_MAX_AVG_DRAWDOWN for the "critical" bar rather than inventing a
# second drawdown threshold.
HEALTH_RECENT_WINDOW = 3
HEALTH_RETIRE_CANDIDATE_WIN_RATE = 30.0
HEALTH_RETIRE_CANDIDATE_RETURN_PCT = -10.0
HEALTH_CRITICAL_WIN_RATE = 40.0
HEALTH_DECLINING_RETURN_DELTA = -5.0
HEALTH_NEEDS_REVIEW_WIN_RATE = 50.0
HEALTH_EXCELLENT_WIN_RATE = 65.0
HEALTH_EXCELLENT_MAX_DRAWDOWN = 10.0
HEALTH_HEALTHY_WIN_RATE = 55.0
HEALTH_HEALTHY_RETURN_DELTA = -2.0

# v0.7 Feature 52 (Part 2) — Strategy Hall of Fame's own real, strict
# induction bar: only ever checked at the moment of a real CEO retirement
# decision (see generate_strategy_retirement_outcome() below), never
# evaluated speculatively on an active strategy.
HALL_OF_FAME_MIN_TRADE_COUNT = 30
HALL_OF_FAME_MIN_WIN_RATE = 55.0
HALL_OF_FAME_MIN_PROFIT_FACTOR = 1.5
HALL_OF_FAME_MAX_AVG_DRAWDOWN = RISK_MAX_AVG_DRAWDOWN

# v0.7 Feature 53 — Company Certification. A real, checkable bar —
# deliberately looser than the Hall of Fame's own bar above, since
# certification gates the *earlier* Limited Live Capital stage, not a
# lifetime achievement judged at retirement.
CERTIFICATION_MIN_TRADE_COUNT = 20
CERTIFICATION_MAX_RUIN_PCT = 15.0
CERTIFICATION_MAX_WORST_CASE_DRAWDOWN_PCT = 30.0
CERTIFICATION_MIN_STRESS_RETURN_PCT = -50.0

# Trading Psychology & Discipline, Piece B — the Statistical Evidence
# Gate on Strategy Retirement (Design Bible Chapter 62 addendum). Real,
# disclosed, and deliberately looser than Certification's own
# CERTIFICATION_MIN_TRADE_COUNT above (retiring a strategy is not the
# same trust-earning bar as certifying it for live capital) — just
# enough real evidence to say a "not enough data yet" conclusion is
# honestly impossible to reach.
MIN_RETIREMENT_TRADE_COUNT = 10

# Design Bible Chapter 62 — Experiment Tiering. Real, but honestly
# arbitrary thresholds (the same "conservative but arbitrary" resolution
# app/schemas.py's own RiskLimits docstring already uses for its default
# values) over the strategy's own real Monte Carlo magnitude — how big a
# swing this strategy represents, upside or downside, not a fabricated
# risk score.
EXPERIMENT_TIER_MODERATE_PCT = 10.0
EXPERIMENT_TIER_MAJOR_PCT = 25.0
EXPERIMENT_TIER_TRANSFORMATIONAL_PCT = 50.0

# Reverse of app/market_intelligence.py's real regime->scenario mapping —
# which of the 13 real MarketIntelligenceRegime values each real
# TestScenario bucket honestly covers.
_SCENARIO_TO_REGIMES: dict[str, list[MarketIntelligenceRegime]] = {}
for _regime, _keyword in _REGIME_TO_SCENARIO_KEYWORD.items():
    _SCENARIO_TO_REGIMES.setdefault(_keyword, []).append(_regime)

_KEYWORD_TO_SCENARIO: dict[str, TestScenario] = {
    "bull": "bull",
    "bear": "bear",
    "sideways": "sideways",
    "high volatility": "high_volatility",
    "low volatility": "low_volatility",
}

_DEPARTMENT_LABELS: dict[ExecutiveDepartmentRole, str] = {
    "research": "Research",
    "quant": "Quant",
    "risk": "Risk",
    "simulation": "Simulation",
    "decision_intelligence": "Decision Intelligence",
    "coach": "Coach",
    "founders": "Founders",
    "devils_advocate": "Devil's Advocate",
    "market_intelligence": "Market Intelligence",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    idx = min(len(sorted_values) - 1, max(0, int(len(sorted_values) * p)))
    return sorted_values[idx]


def _tail_mean(sorted_values: list[float], p: float) -> float:
    """Quantitative Research & Intelligence System, Piece 3 — Conditional
    Value at Risk (CVaR / Expected Shortfall): the mean of the worst
    p-fraction of `sorted_values` (ascending), using the exact same
    index convention _percentile() already uses. Answers "given a path
    lands in the worst p%, what's the average outcome" — a real
    tail-mean read, not a new bootstrap."""
    if not sorted_values:
        return 0.0
    idx = min(len(sorted_values) - 1, max(0, int(len(sorted_values) * p)))
    tail = sorted_values[: idx + 1]
    return sum(tail) / len(tail)


# ---------------------------------------------------------------------
# Monte Carlo Testing — a real trade-sequence bootstrap.
# ---------------------------------------------------------------------


def _seeded_rng(*parts: str) -> random.Random:
    """A deterministic RNG, seeded from real, stable identifiers — the
    same `hashlib.sha256(...)` -> `random.Random(int(...))` convention
    `app/market_data.py`'s own candle-history generator already uses.
    CEO directive "Professional Research → Certification → Paper →
    Capital Allocation Pipeline" — an audit found this module's Monte
    Carlo bootstrap used the bare, unseeded global `random` module, so
    re-running the exact same certification question against identical
    data could produce a different `probabilityOfRuinPct` — and
    therefore a different CERTIFIED/not-certified verdict — every time,
    since that figure is a hard pass/fail gate. Seeding it makes
    "certified" a real, reproducible claim instead of one that could
    flip on a coin toss."""
    digest = hashlib.sha256(":".join(parts).encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


def run_strategy_monte_carlo(strategy: Strategy, results: list[SimulationResult], *, sim_day: int) -> StrategyMonteCarloResult | None:
    """None when the strategy has no completed runs yet — nothing real
    to bootstrap from. Each simulated path draws `trade_count` win/loss
    outcomes using the strategy's own real, aggregated win rate as the
    probability, sized by its own real average win/loss percentages —
    every number driving the randomness is a real field already on
    SimulationResult, never independently invented. Seeded deterministically
    (see `_seeded_rng()`) from the strategy's own id and the real results
    on file, so the same real evidence always produces the same real
    distribution."""
    strategy_results = [r for r in results if r.strategy_id == strategy.id]
    if not strategy_results:
        return None

    win_rate = sum(r.win_rate for r in strategy_results) / len(strategy_results) / 100
    avg_win_pct = sum(r.avg_win_pct for r in strategy_results) / len(strategy_results)
    avg_loss_pct = sum(r.avg_loss_pct for r in strategy_results) / len(strategy_results)
    trades_per_path = max(1, round(sum(r.trade_count for r in strategy_results) / len(strategy_results)))
    rng = _seeded_rng(strategy.id, f"{win_rate:.6f}", f"{avg_win_pct:.6f}", f"{avg_loss_pct:.6f}", str(trades_per_path))

    finals: list[float] = []
    max_drawdowns: list[float] = []
    ruin_count = 0
    for _ in range(MONTE_CARLO_PATHS):
        cumulative = 0.0
        peak = 0.0
        max_drawdown = 0.0
        for _trade in range(trades_per_path):
            r = (avg_win_pct if rng.random() < win_rate else -avg_loss_pct) / 100
            cumulative = (1 + cumulative) * (1 + r) - 1
            peak = max(peak, cumulative)
            max_drawdown = min(max_drawdown, cumulative - peak)
        finals.append(cumulative)
        max_drawdowns.append(max_drawdown)
        if abs(max_drawdown) * 100 >= RUIN_DRAWDOWN_PCT:
            ruin_count += 1

    finals.sort()
    max_drawdowns.sort()
    probability_of_ruin = round(ruin_count / MONTE_CARLO_PATHS * 100, 1)

    return StrategyMonteCarloResult(
        id=f"montecarlo-{strategy.id}-{sim_day}",
        strategyId=strategy.id,
        strategyName=strategy.name,
        pathsSimulated=MONTE_CARLO_PATHS,
        tradesPerPath=trades_per_path,
        sourceWinRate=round(win_rate * 100, 1),
        sourceAvgWinPct=round(avg_win_pct, 2),
        sourceAvgLossPct=round(avg_loss_pct, 2),
        medianReturnPct=round(_percentile(finals, 0.50) * 100, 2),
        returnRangeLowPct=round(_percentile(finals, 0.10) * 100, 2),
        returnRangeHighPct=round(_percentile(finals, 0.90) * 100, 2),
        medianMaxDrawdownPct=round(abs(_percentile(max_drawdowns, 0.50)) * 100, 2),
        worstCaseDrawdownPct=round(abs(_percentile(max_drawdowns, 0.05)) * 100, 2),
        probabilityOfProfitPct=round(sum(1 for f in finals if f > 0) / len(finals) * 100, 1),
        probabilityOfRuinPct=probability_of_ruin,
        capitalSurvivalPct=round(100 - probability_of_ruin, 1),
        valueAtRisk95Pct=round(_percentile(finals, 0.05) * 100, 2),
        valueAtRisk99Pct=round(_percentile(finals, 0.01) * 100, 2),
        conditionalValueAtRisk95Pct=round(_tail_mean(finals, 0.05) * 100, 2),
        conditionalValueAtRisk99Pct=round(_tail_mean(finals, 0.01) * 100, 2),
        simDay=sim_day,
        createdAt=_now_iso(),
    )


def cap_strategy_monte_carlo_results(items: list[StrategyMonteCarloResult]) -> list[StrategyMonteCarloResult]:
    if len(items) > MAX_STRATEGY_MONTE_CARLO_RESULTS:
        del items[: len(items) - MAX_STRATEGY_MONTE_CARLO_RESULTS]
    return items


# ---------------------------------------------------------------------
# Market Regime Testing — bucketed at the real TestScenario grain,
# labeled with the real 13-way regimes each bucket covers.
# ---------------------------------------------------------------------


def compute_strategy_regime_test(strategy: Strategy, results: list[SimulationResult], *, sim_day: int) -> StrategyRegimeTestReport | None:
    strategy_results = [r for r in results if r.strategy_id == strategy.id]
    if not strategy_results:
        return None

    buckets: list[StrategyRegimeBucketPerformance] = []
    for keyword, regimes in _SCENARIO_TO_REGIMES.items():
        scenario = _KEYWORD_TO_SCENARIO[keyword]
        bucket_results = [r for r in strategy_results if r.scenario == scenario]
        if not bucket_results:
            buckets.append(StrategyRegimeBucketPerformance(scenario=scenario, regimes=regimes, tested=False, runCount=0, avgReturnPct=0.0, avgWinRate=0.0, verdict="untested"))
            continue
        avg_return = sum(r.total_return_pct for r in bucket_results) / len(bucket_results)
        avg_win_rate = sum(r.win_rate for r in bucket_results) / len(bucket_results)
        verdict: str = "strong" if avg_return > 0 and avg_win_rate >= 50.0 else "weak" if avg_return < 0 else "neutral"
        buckets.append(StrategyRegimeBucketPerformance(scenario=scenario, regimes=regimes, tested=True, runCount=len(bucket_results), avgReturnPct=round(avg_return, 2), avgWinRate=round(avg_win_rate, 1), verdict=verdict))  # type: ignore[arg-type]

    tested_buckets = [b for b in buckets if b.tested]
    best = max(tested_buckets, key=lambda b: b.avg_return_pct).scenario if tested_buckets else None
    worst = min(tested_buckets, key=lambda b: b.avg_return_pct).scenario if tested_buckets else None

    return StrategyRegimeTestReport(
        id=f"regimetest-{strategy.id}-{sim_day}",
        strategyId=strategy.id,
        strategyName=strategy.name,
        buckets=buckets,
        bestScenario=best,
        worstScenario=worst,
        simDay=sim_day,
        createdAt=_now_iso(),
    )


def cap_strategy_regime_tests(items: list[StrategyRegimeTestReport]) -> list[StrategyRegimeTestReport]:
    if len(items) > MAX_STRATEGY_REGIME_TESTS:
        del items[: len(items) - MAX_STRATEGY_REGIME_TESTS]
    return items


# ---------------------------------------------------------------------
# Liquidity Validation — reuses Feature 51's real liquidity/structure
# engine as-is against the strategy's own watched symbols.
# ---------------------------------------------------------------------


def validate_strategy_liquidity(strategy: Strategy, watchlist: list[WatchlistEntry], provider: MarketDataProvider, *, sim_day: int, candle_timeframe: str = "1h", candle_window: int = 40) -> StrategyLiquidityValidation | None:
    per_symbol_candles: dict[str, list[Candle]] = {}
    for entry in watchlist:
        try:
            candles = provider.get_candles(entry.symbol, candle_timeframe, candle_window)
        except ValueError:
            continue
        if candles:
            per_symbol_candles[entry.symbol] = candles
    if not per_symbol_candles:
        return None

    liquidity_reads = [compute_liquidity(symbol, candles) for symbol, candles in per_symbol_candles.items()]
    structure_reads = [compute_market_structure(symbol, candles) for symbol, candles in per_symbol_candles.items()]
    sweep_share = sum(1 for lr in liquidity_reads if lr.sweep_detected) / len(liquidity_reads)
    real_sweep_rate_pct = round(sweep_share * 100, 1)

    verdict: str
    if sweep_share >= 0.3:
        verdict = "favorable"
        detail = f"{real_sweep_rate_pct:.0f}% of {len(per_symbol_candles)} checked symbol(s) show a real, recent liquidity sweep — active liquidity conditions for a sweep-reliant strategy."
    elif sweep_share == 0.0:
        verdict = "unfavorable"
        detail = f"None of the {len(per_symbol_candles)} checked symbol(s) show a real recent liquidity sweep — thin conditions for a strategy that depends on one."
    else:
        verdict = "neutral"
        detail = f"{real_sweep_rate_pct:.0f}% of {len(per_symbol_candles)} checked symbol(s) show a real recent liquidity sweep — mixed conditions."

    return StrategyLiquidityValidation(
        id=f"liquidity-{strategy.id}-{sim_day}",
        strategyId=strategy.id,
        strategyName=strategy.name,
        symbolsChecked=sorted(per_symbol_candles.keys()),
        liquidityReads=liquidity_reads,
        structureReads=structure_reads,
        realSweepRatePct=real_sweep_rate_pct,
        verdict=verdict,  # type: ignore[arg-type]
        detail=detail,
        simDay=sim_day,
        createdAt=_now_iso(),
    )


def cap_strategy_liquidity_validations(items: list[StrategyLiquidityValidation]) -> list[StrategyLiquidityValidation]:
    if len(items) > MAX_STRATEGY_LIQUIDITY_VALIDATIONS:
        del items[: len(items) - MAX_STRATEGY_LIQUIDITY_VALIDATIONS]
    return items


# ---------------------------------------------------------------------
# Executive Review — the same real 9 department seats as Feature 50,
# Strategy-scoped, with evidence/concerns/suggested-improvements.
# ---------------------------------------------------------------------


def _research_department_opinion(strategy: Strategy, research_items: list[ResearchItem]) -> StrategyDepartmentOpinion:
    matches = [r for r in research_items if r.category == strategy.focus_category and r.status == "completed"]
    stance: ExecutiveStance = "agree" if matches else "request_more_research"
    return StrategyDepartmentOpinion(
        role="research",
        departmentLabel=_DEPARTMENT_LABELS["research"],
        stance=stance,
        confidencePct=70.0 if matches else 40.0,
        evidence=[f"{len(matches)} completed real research item(s) in {strategy.focus_category}."] if matches else [],
        concerns=[] if matches else [f"No completed research on record for {strategy.focus_category}."],
        suggestedImprovements=[] if matches else ["Complete at least one real research item in this strategy's own focus category before advancing."],
    )


def _quant_department_opinion(review: StrategyReview | None, monte_carlo: StrategyMonteCarloResult | None) -> StrategyDepartmentOpinion:
    quant_verdict = next((v for v in review.verdicts if v.reviewer_role == "quant"), None) if review else None
    evidence: list[str] = []
    concerns: list[str] = []
    confidence = 50.0
    stance: ExecutiveStance = "request_more_research"
    if quant_verdict:
        evidence.append(quant_verdict.summary)
        confidence = 75.0 if quant_verdict.verdict == "pass" else 40.0 if quant_verdict.verdict == "fail" else 55.0
        stance = "agree" if quant_verdict.verdict == "pass" else "disagree" if quant_verdict.verdict == "fail" else "request_more_research"
        if quant_verdict.verdict != "pass":
            concerns.append(quant_verdict.summary)
    if monte_carlo:
        evidence.append(f"Monte Carlo bootstrap ({monte_carlo.paths_simulated} paths): {monte_carlo.probability_of_profit_pct:.0f}% probability of profit, median return {monte_carlo.median_return_pct:+.1f}%.")
    return StrategyDepartmentOpinion(role="quant", departmentLabel=_DEPARTMENT_LABELS["quant"], agentId="quant", stance=stance, confidencePct=confidence, evidence=evidence, concerns=concerns, suggestedImprovements=[] if stance == "agree" else ["Run more Market Simulation scenarios to raise the sample size behind these statistics."])


def _risk_department_opinion(review: StrategyReview | None, monte_carlo: StrategyMonteCarloResult | None) -> StrategyDepartmentOpinion:
    risk_verdict = next((v for v in review.verdicts if v.reviewer_role == "risk"), None) if review else None
    evidence: list[str] = []
    concerns: list[str] = []
    confidence = 50.0
    stance: ExecutiveStance = "request_more_research"
    if risk_verdict:
        evidence.append(risk_verdict.summary)
        confidence = 75.0 if risk_verdict.verdict == "pass" else 30.0 if risk_verdict.verdict == "fail" else 50.0
        stance = "agree" if risk_verdict.verdict == "pass" else "recommend_rejecting" if risk_verdict.verdict == "fail" else "recommend_position_change"
        if risk_verdict.verdict != "pass":
            concerns.append(risk_verdict.summary)
    if monte_carlo:
        evidence.append(f"Bootstrap worst-case drawdown {monte_carlo.worst_case_drawdown_pct:.1f}%, {monte_carlo.probability_of_ruin_pct:.0f}% probability of ruin across {monte_carlo.paths_simulated} simulated paths.")
        if monte_carlo.probability_of_ruin_pct > 10.0:
            concerns.append(f"{monte_carlo.probability_of_ruin_pct:.0f}% of simulated paths breached a {RUIN_DRAWDOWN_PCT:.0f}% drawdown — real ruin risk at this position size.")
            stance = "recommend_position_change" if stance == "agree" else stance
    return StrategyDepartmentOpinion(role="risk", departmentLabel=_DEPARTMENT_LABELS["risk"], agentId="guardian", stance=stance, confidencePct=confidence, evidence=evidence, concerns=concerns, suggestedImprovements=[] if stance == "agree" else ["Reduce position sizing or tighten stops before more capital is committed."])


def _simulation_department_opinion(regime_test: StrategyRegimeTestReport | None) -> StrategyDepartmentOpinion:
    if regime_test is None:
        return StrategyDepartmentOpinion(role="simulation", departmentLabel=_DEPARTMENT_LABELS["simulation"], agentId="echo", stance="request_more_research", confidencePct=50.0, evidence=[], concerns=["No completed Market Simulation runs yet to bucket by Testing Environment."], suggestedImprovements=["Run at least one Market Simulation scenario before this stage can be evaluated."])
    tested = [b for b in regime_test.buckets if b.tested]
    strong = [b for b in tested if b.verdict == "strong"]
    weak = [b for b in tested if b.verdict == "weak"]
    stance: ExecutiveStance = "agree" if len(tested) >= 2 and not weak else "request_more_research" if len(tested) < 2 else "recommend_waiting"
    evidence = [f"Tested across {len(tested)} real Testing Environment(s) ({', '.join(b.scenario for b in tested)})."]
    if strong:
        evidence.append(f"Strong performance in: {', '.join(b.scenario for b in strong)}.")
    concerns = [f"Weak performance in: {', '.join(b.scenario for b in weak)}."] if weak else []
    return StrategyDepartmentOpinion(role="simulation", departmentLabel=_DEPARTMENT_LABELS["simulation"], agentId="echo", stance=stance, confidencePct=70.0 if stance == "agree" else 45.0, evidence=evidence, concerns=concerns, suggestedImprovements=[] if not weak else [f"Investigate why the {weak[0].scenario} environment underperforms before relying on this strategy there."])


def _decision_intelligence_department_opinion(review: StrategyReview | None, monte_carlo: StrategyMonteCarloResult | None) -> StrategyDepartmentOpinion:
    signals = [v.verdict == "pass" for v in review.verdicts] if review else []
    pass_rate = sum(signals) / len(signals) if signals else 0.0
    confidence = round(pass_rate * 100, 1) if signals else 50.0
    if monte_carlo:
        confidence = round((confidence + monte_carlo.probability_of_profit_pct) / 2, 1)
    stance: ExecutiveStance = "agree" if confidence >= 65 else "request_more_research" if confidence >= 45 else "disagree"
    return StrategyDepartmentOpinion(role="decision_intelligence", departmentLabel=_DEPARTMENT_LABELS["decision_intelligence"], stance=stance, confidencePct=confidence, evidence=[f"Composite real confidence across every completed validation stage so far: {confidence:.0f}/100."], concerns=[] if stance == "agree" else ["Composite confidence has not yet cleared a comfortable bar."], suggestedImprovements=[] if stance == "agree" else ["Complete more validation stages before this strategy earns a strong Decision Intelligence read."])


def _coach_department_opinion(coach_reports: list[CoachReport]) -> StrategyDepartmentOpinion:
    if not coach_reports:
        return StrategyDepartmentOpinion(role="coach", departmentLabel=_DEPARTMENT_LABELS["coach"], agentId="coach", stance="request_more_research", confidencePct=50.0, evidence=[], concerns=["No Coach report filed yet this game — too early for a real development read."], suggestedImprovements=[])
    latest = coach_reports[-1]
    stance: ExecutiveStance = "agree" if latest.company_score >= 60 else "request_more_research"
    return StrategyDepartmentOpinion(role="coach", departmentLabel=_DEPARTMENT_LABELS["coach"], agentId="coach", stance=stance, confidencePct=round(latest.company_score, 1), evidence=[f"Company Score {latest.company_score:.0f}/100 as of the last real Coach report."], concerns=list(latest.common_mistakes[:1]), suggestedImprovements=list(latest.recommendations[:1]))


def _founders_department_opinion(review: StrategyReview | None) -> StrategyDepartmentOpinion:
    concern_count = sum(1 for v in review.verdicts if v.verdict != "pass") if review else 0
    stance: ExecutiveStance = "agree" if concern_count == 0 and review else "recommend_waiting" if review else "request_more_research"
    evidence = [f"{len(review.verdicts) - concern_count} of {len(review.verdicts)} real reviewer verdict(s) passed clean."] if review else []
    concerns = [f"{concern_count} real reviewer verdict(s) raised a concern or fail."] if concern_count else []
    return StrategyDepartmentOpinion(role="founders", departmentLabel=_DEPARTMENT_LABELS["founders"], stance=stance, confidencePct=70.0 if stance == "agree" else 45.0, evidence=evidence, concerns=concerns, suggestedImprovements=[] if not concerns else ["Resolve the Company Review's own open concerns before requesting Founder Approval."])


def _devils_advocate_department_opinion(strategy: Strategy, monte_carlo: StrategyMonteCarloResult | None, existing_review_count: int) -> StrategyDepartmentOpinion:
    assigned: AgentId = STRATEGY_DEVILS_ADVOCATES[existing_review_count % len(STRATEGY_DEVILS_ADVOCATES)]
    if monte_carlo is None:
        return StrategyDepartmentOpinion(role="devils_advocate", departmentLabel=_DEPARTMENT_LABELS["devils_advocate"], agentId=assigned, stance="request_more_research", confidencePct=50.0, evidence=[], concerns=["No Monte Carlo bootstrap yet — nothing real to attack."], suggestedImprovements=[])
    weakness_found = monte_carlo.probability_of_ruin_pct > 5.0 or monte_carlo.return_range_low_pct < -20.0
    stance: ExecutiveStance = "recommend_rejecting" if monte_carlo.probability_of_ruin_pct > 15.0 else "recommend_waiting" if weakness_found else "agree"
    evidence = [f"{monte_carlo.paths_simulated}-path bootstrap: {monte_carlo.probability_of_ruin_pct:.0f}% probability of ruin, 10th-percentile return {monte_carlo.return_range_low_pct:+.1f}%."]
    concerns = [f"A real {monte_carlo.probability_of_ruin_pct:.0f}% of simulated paths breach a {RUIN_DRAWDOWN_PCT:.0f}% drawdown."] if weakness_found else []
    return StrategyDepartmentOpinion(role="devils_advocate", departmentLabel=_DEPARTMENT_LABELS["devils_advocate"], agentId=assigned, stance=stance, confidencePct=30.0 if stance == "recommend_rejecting" else 55.0 if stance == "recommend_waiting" else 75.0, evidence=evidence, concerns=concerns, suggestedImprovements=[] if not weakness_found else ["Reduce position size or tighten the strategy's own exit rules to cut worst-case drawdown."])


def _market_intelligence_department_opinion(market_intelligence: MarketIntelligenceState, regime_test: StrategyRegimeTestReport | None) -> StrategyDepartmentOpinion:
    quality = market_intelligence.quality
    stance_by_tier: dict[str, ExecutiveStance] = {"excellent": "agree", "good": "agree", "average": "request_more_research", "poor": "recommend_waiting", "avoid_trading": "recommend_rejecting"}
    stance = stance_by_tier[quality.tier]
    evidence = [f"{market_intelligence.regime_label} — {quality.reasoning}"]
    concerns: list[str] = []
    if regime_test is not None:
        keyword = _REGIME_TO_SCENARIO_KEYWORD[market_intelligence.regime]
        scenario = _KEYWORD_TO_SCENARIO[keyword]
        matched = next((b for b in regime_test.buckets if b.scenario == scenario), None)
        if matched and matched.tested:
            evidence.append(f"Today's real regime maps to a Testing Environment this strategy has been tested in: {matched.verdict} ({matched.avg_return_pct:+.1f}% avg return).")
            if matched.verdict == "weak":
                concerns.append(f"This strategy has real evidence of underperforming in today's regime ({scenario}).")
                stance = "recommend_waiting" if stance == "agree" else stance
        else:
            evidence.append("This strategy has not yet been tested under today's real regime bucket.")
    return StrategyDepartmentOpinion(role="market_intelligence", departmentLabel=_DEPARTMENT_LABELS["market_intelligence"], stance=stance, confidencePct=quality.confidence_pct, evidence=evidence, concerns=concerns, suggestedImprovements=[] if not concerns else ["Re-test this strategy under today's real Testing Environment before relying on it now."])


def generate_strategy_executive_review(
    strategy: Strategy,
    review: StrategyReview | None,
    research_items: list[ResearchItem],
    coach_reports: list[CoachReport],
    monte_carlo: StrategyMonteCarloResult | None,
    regime_test: StrategyRegimeTestReport | None,
    market_intelligence: MarketIntelligenceState,
    existing_review_count: int,
    *,
    sim_day: int,
) -> StrategyExecutiveReview:
    opinions = [
        _research_department_opinion(strategy, research_items),
        _quant_department_opinion(review, monte_carlo),
        _risk_department_opinion(review, monte_carlo),
        _simulation_department_opinion(regime_test),
        _decision_intelligence_department_opinion(review, monte_carlo),
        _coach_department_opinion(coach_reports),
        _founders_department_opinion(review),
        _devils_advocate_department_opinion(strategy, monte_carlo, existing_review_count),
        _market_intelligence_department_opinion(market_intelligence, regime_test),
    ]
    overall_confidence = round(sum(o.confidence_pct for o in opinions) / len(opinions), 1)
    rejecting = sum(1 for o in opinions if o.stance in ("disagree", "recommend_rejecting"))
    waiting = sum(1 for o in opinions if o.stance in ("recommend_waiting", "request_more_research", "recommend_position_change"))

    recommendation: StrategyExecutiveAction
    reason: str
    if rejecting >= 2:
        recommendation = "reject"
        reason = f"{rejecting} department(s) actively oppose this strategy — real, unresolved concerns."
    elif rejecting == 1:
        recommendation = "hold_for_improvement"
        reason = "One department opposes this strategy — resolve its real concern before advancing."
    elif waiting >= 4:
        recommendation = "request_more_evidence"
        reason = f"{waiting} department(s) want more real evidence before backing this strategy."
    else:
        recommendation = "advance"
        reason = "No department raised a concern serious enough to hold this strategy back."

    return StrategyExecutiveReview(
        id=f"strategyexec-{strategy.id}-{existing_review_count}",
        strategyId=strategy.id,
        strategyName=strategy.name,
        opinions=opinions,
        overallConfidencePct=overall_confidence,
        recommendation=recommendation,
        reason=reason,
        simDay=sim_day,
        createdAt=_now_iso(),
    )


def cap_strategy_executive_reviews(items: list[StrategyExecutiveReview]) -> list[StrategyExecutiveReview]:
    if len(items) > MAX_STRATEGY_EXECUTIVE_REVIEWS:
        del items[: len(items) - MAX_STRATEGY_EXECUTIVE_REVIEWS]
    return items


# ---------------------------------------------------------------------
# Founder Approval — a new mode of founders.py's real threshold pattern.
# ---------------------------------------------------------------------


def generate_strategy_founder_approval(strategy: Strategy, executive_review: StrategyExecutiveReview, *, sim_day: int) -> StrategyFounderApproval:
    approved = executive_review.recommendation == "advance" and executive_review.overall_confidence_pct >= FOUNDER_APPROVAL_CONFIDENCE_THRESHOLD
    if approved:
        verdict_reason = f'The Executive Review recommended "{executive_review.recommendation}" at {executive_review.overall_confidence_pct:.0f}/100 confidence — the Founder Council approves.'
    elif executive_review.recommendation != "advance":
        verdict_reason = f'The Executive Review\'s own recommendation was "{executive_review.recommendation.replace("_", " ")}", not advance — the Council is not willing to sign off yet.'
    else:
        verdict_reason = f"Confidence only reached {executive_review.overall_confidence_pct:.0f}/100, short of the Council's {FOUNDER_APPROVAL_CONFIDENCE_THRESHOLD:.0f} bar."

    return StrategyFounderApproval(
        id=f"founderapproval-{strategy.id}-{sim_day}",
        strategyId=strategy.id,
        strategyName=strategy.name,
        simDay=sim_day,
        evidenceSummary=executive_review.reason,
        confidencePct=executive_review.overall_confidence_pct,
        verdict="approved" if approved else "rejected",
        verdictReason=verdict_reason,
        createdAt=_now_iso(),
    )


def cap_strategy_founder_approvals(items: list[StrategyFounderApproval]) -> list[StrategyFounderApproval]:
    if len(items) > MAX_STRATEGY_FOUNDER_APPROVALS:
        del items[: len(items) - MAX_STRATEGY_FOUNDER_APPROVALS]
    return items


# ---------------------------------------------------------------------
# Confidence Score — computed fresh from the real artifacts above.
# ---------------------------------------------------------------------


def compute_strategy_confidence_score(
    strategy: Strategy,
    review: StrategyReview | None,
    monte_carlo: StrategyMonteCarloResult | None,
    regime_test: StrategyRegimeTestReport | None,
    executive_review: StrategyExecutiveReview | None,
    *,
    sim_day: int,
) -> StrategyConfidenceScore:
    parts = [v for v in (review.overall_verdict if review else None, executive_review.overall_confidence_pct if executive_review else None) if v is not None]
    confidence_inputs: list[float] = []
    if executive_review:
        confidence_inputs.append(executive_review.overall_confidence_pct)
    if monte_carlo:
        confidence_inputs.append(monte_carlo.probability_of_profit_pct)
    overall = round(sum(confidence_inputs) / len(confidence_inputs), 1) if confidence_inputs else 40.0

    evidence: list[str] = []
    strengths: list[str] = []
    weaknesses: list[str] = []
    if review:
        evidence.append(f"Company Review verdict: {review.overall_verdict}.")
        for v in review.verdicts:
            (strengths if v.verdict == "pass" else weaknesses).append(v.summary)
    if monte_carlo:
        evidence.append(f"Monte Carlo: {monte_carlo.probability_of_profit_pct:.0f}% probability of profit, {monte_carlo.probability_of_ruin_pct:.0f}% probability of ruin.")
        if monte_carlo.probability_of_ruin_pct <= 5.0:
            strengths.append(f"Low real probability of ruin ({monte_carlo.probability_of_ruin_pct:.0f}%) across {monte_carlo.paths_simulated} simulated paths.")
        else:
            weaknesses.append(f"Real probability of ruin ({monte_carlo.probability_of_ruin_pct:.0f}%) across {monte_carlo.paths_simulated} simulated paths.")
    if regime_test and regime_test.best_scenario:
        evidence.append(f"Best real Testing Environment on record: {regime_test.best_scenario}.")

    risk_rating: str
    if monte_carlo is None:
        risk_rating = "elevated"
    elif monte_carlo.probability_of_ruin_pct > 15.0:
        risk_rating = "high"
    elif monte_carlo.probability_of_ruin_pct > 5.0:
        risk_rating = "elevated"
    elif monte_carlo.probability_of_ruin_pct > 1.0:
        risk_rating = "moderate"
    else:
        risk_rating = "low"

    # A real, capped fraction of allocated capital scaled down as
    # real ruin risk rises — never a fixed number independent of the
    # strategy's own bootstrap results.
    position_size_scale = {"low": 1.0, "moderate": 0.75, "elevated": 0.5, "high": 0.25}[risk_rating]
    recommended_position_size_pct = round(10.0 * position_size_scale, 1)

    recommended_conditions = [f"{b.scenario} ({', '.join(b.regimes)})" for b in regime_test.buckets if b.tested and b.verdict == "strong"] if regime_test else []

    return StrategyConfidenceScore(
        id=f"confidence-{strategy.id}-{sim_day}",
        strategyId=strategy.id,
        strategyName=strategy.name,
        overallConfidencePct=overall,
        evidence=evidence or [f"Not enough real validation history yet — {len(parts)} real signal(s) on record."],
        knownStrengths=strengths or ["No standout strengths yet — results are still early."],
        knownWeaknesses=weaknesses or ["No significant weaknesses found yet."],
        riskRating=risk_rating,  # type: ignore[arg-type]
        recommendedPositionSizePct=recommended_position_size_pct,
        recommendedMarketConditions=recommended_conditions,
        simDay=sim_day,
        createdAt=_now_iso(),
    )


def compute_experiment_tier(monte_carlo: StrategyMonteCarloResult) -> tuple[ExperimentTier, str]:
    """Design Bible Chapter 62 — Experiment Classification. Real
    magnitude, not a fabricated risk score: the larger of the strategy's
    own projected upside (`medianReturnPct`) or realized downside
    (`worstCaseDrawdownPct`) from its own real Monte Carlo bootstrap,
    bucketed against EXPERIMENT_TIER_*_PCT. A strategy is only ever
    classified once it has a real Monte Carlo result to classify —
    callers never invoke this speculatively."""
    magnitude = max(abs(monte_carlo.median_return_pct), abs(monte_carlo.worst_case_drawdown_pct))
    if magnitude >= EXPERIMENT_TIER_TRANSFORMATIONAL_PCT:
        return "transformational", f"Projected magnitude of {magnitude:.1f}% (median return vs. worst-case drawdown) is large enough to meaningfully reshape company performance if deployed at scale."
    if magnitude >= EXPERIMENT_TIER_MAJOR_PCT:
        return "major", f"Projected magnitude of {magnitude:.1f}% represents a significant swing, upside or downside, for a single strategy."
    if magnitude >= EXPERIMENT_TIER_MODERATE_PCT:
        return "moderate", f"Projected magnitude of {magnitude:.1f}% is a real but contained swing."
    return "minor", f"Projected magnitude of {magnitude:.1f}% is small — a low-stakes, incremental experiment."


# ---------------------------------------------------------------------
# Strategy Dossier — the brief's "professional Strategy Report,"
# assembled from every real artifact above.
# ---------------------------------------------------------------------


def generate_strategy_dossier(
    strategy: Strategy,
    reports: list[StrategyReport],
    reviews: list[StrategyReview],
    monte_carlo_results: list[StrategyMonteCarloResult],
    regime_tests: list[StrategyRegimeTestReport],
    liquidity_validations: list[StrategyLiquidityValidation],
    executive_reviews: list[StrategyExecutiveReview],
    founder_approvals: list[StrategyFounderApproval],
) -> StrategyDossier:
    latest_report = next((r for r in reversed(reports) if r.strategy_id == strategy.id), None)
    latest_review = next((r for r in reversed(reviews) if r.strategy_id == strategy.id), None)
    monte_carlo = next((r for r in reversed(monte_carlo_results) if r.strategy_id == strategy.id), None)
    regime_test = next((r for r in reversed(regime_tests) if r.strategy_id == strategy.id), None)
    liquidity = next((r for r in reversed(liquidity_validations) if r.strategy_id == strategy.id), None)
    executive_review = next((r for r in reversed(executive_reviews) if r.strategy_id == strategy.id), None)
    founder_approval = next((r for r in reversed(founder_approvals) if r.strategy_id == strategy.id), None)
    confidence = (
        compute_strategy_confidence_score(strategy, latest_review, monte_carlo, regime_test, executive_review, sim_day=strategy.stage_history[-1].sim_day if strategy.stage_history else 0)
        if (latest_review or monte_carlo or executive_review)
        else None
    )
    experiment_tier, experiment_tier_rationale = compute_experiment_tier(monte_carlo) if monte_carlo is not None else (None, None)

    return StrategyDossier(
        strategyId=strategy.id,
        strategyName=strategy.name,
        createdBy=strategy.created_by,
        purpose=strategy.description,
        stage=strategy.stage,
        latestReport=latest_report,
        latestReview=latest_review,
        monteCarlo=monte_carlo,
        regimeTest=regime_test,
        liquidityValidation=liquidity,
        executiveReview=executive_review,
        founderApproval=founder_approval,
        confidence=confidence,
        experimentTier=experiment_tier,
        experimentTierRationale=experiment_tier_rationale,
        generatedAt=_now_iso(),
    )


# ---------------------------------------------------------------------
# v0.7 Feature 52 (Part 2) — "Living Strategies." Strategy Health is a
# real recent-vs-lifetime trend read; Hall of Fame / Failed Archive are
# the two permanent outcomes of a real CEO retirement decision; the
# Executive Dashboard is a computed aggregate over every artifact above.
# See this module's own module docstring's honesty boundary — none of
# this fabricates data app/sandbox.py's own docstring already explains
# this codebase cannot honestly attribute (live/paper trade attribution).
# ---------------------------------------------------------------------


def compute_strategy_health(strategy: Strategy, results: list[SimulationResult], *, sim_day: int) -> StrategyHealthAssessment | None:
    """None when the strategy has no completed runs yet — nothing real
    to compare. 'Recent' is this strategy's own last HEALTH_RECENT_WINDOW
    real SimulationResults; 'lifetime' is its full real history
    (including those same recent runs, so a young strategy's recent and
    lifetime reads are honestly identical rather than dividing an
    already-thin sample in two)."""
    strategy_results = [r for r in results if r.strategy_id == strategy.id]
    if not strategy_results:
        return None

    recent = strategy_results[-HEALTH_RECENT_WINDOW:]
    lifetime = strategy_results
    recent_win_rate = sum(r.win_rate for r in recent) / len(recent)
    lifetime_win_rate = sum(r.win_rate for r in lifetime) / len(lifetime)
    recent_avg_return = sum(r.total_return_pct for r in recent) / len(recent)
    lifetime_avg_return = sum(r.total_return_pct for r in lifetime) / len(lifetime)
    recent_avg_drawdown = sum(r.max_drawdown_pct for r in recent) / len(recent)
    lifetime_avg_drawdown = sum(r.max_drawdown_pct for r in lifetime) / len(lifetime)
    return_delta = recent_avg_return - lifetime_avg_return

    trend: StrategyHealthTrend = "improving" if return_delta > 1.0 else "declining" if return_delta < -1.0 else "stable"
    reasoning = [f"Recent {len(recent)}-run average return {recent_avg_return:+.1f}% vs. this strategy's own lifetime average {lifetime_avg_return:+.1f}% across {len(lifetime)} real run(s)."]

    status: StrategyHealthStatus
    if recent_win_rate < HEALTH_RETIRE_CANDIDATE_WIN_RATE or recent_avg_return <= HEALTH_RETIRE_CANDIDATE_RETURN_PCT:
        status = "retire_candidate"
        reasoning.append(f"Recent win rate {recent_win_rate:.0f}% / recent average return {recent_avg_return:+.1f}% is a real, serious warning sign.")
    elif recent_avg_drawdown > RISK_MAX_AVG_DRAWDOWN:
        status = "critical"
        reasoning.append(f"Recent average drawdown {recent_avg_drawdown:.1f}% exceeds the {RISK_MAX_AVG_DRAWDOWN:.0f}% comfort bar Risk already uses elsewhere in this pipeline.")
    elif recent_win_rate < HEALTH_CRITICAL_WIN_RATE:
        status = "critical"
        reasoning.append(f"Recent win rate {recent_win_rate:.0f}% is critically low.")
    elif return_delta < HEALTH_DECLINING_RETURN_DELTA:
        status = "declining"
        reasoning.append(f"Recent performance has fallen {abs(return_delta):.1f} points below this strategy's own lifetime average.")
    elif return_delta < 0.0 and recent_win_rate < HEALTH_NEEDS_REVIEW_WIN_RATE:
        status = "needs_review"
        reasoning.append("Recent performance is below this strategy's own lifetime average and its recent win rate has slipped under 50%.")
    elif recent_win_rate >= HEALTH_EXCELLENT_WIN_RATE and return_delta >= 0.0 and recent_avg_drawdown <= HEALTH_EXCELLENT_MAX_DRAWDOWN:
        status = "excellent"
        reasoning.append("Recent performance matches or beats this strategy's own lifetime average with a strong win rate and low drawdown.")
    elif recent_win_rate >= HEALTH_HEALTHY_WIN_RATE and return_delta >= HEALTH_HEALTHY_RETURN_DELTA:
        status = "healthy"
        reasoning.append("Recent performance is holding close to or above this strategy's own lifetime average.")
    else:
        status = "stable"
        reasoning.append("No strong real trend either way yet.")

    return StrategyHealthAssessment(
        id=f"health-{strategy.id}-{sim_day}",
        strategyId=strategy.id,
        strategyName=strategy.name,
        status=status,
        trend=trend,
        recentWinRate=round(recent_win_rate, 1),
        lifetimeWinRate=round(lifetime_win_rate, 1),
        recentAvgReturnPct=round(recent_avg_return, 2),
        lifetimeAvgReturnPct=round(lifetime_avg_return, 2),
        recentAvgDrawdownPct=round(recent_avg_drawdown, 2),
        lifetimeAvgDrawdownPct=round(lifetime_avg_drawdown, 2),
        recentSampleSize=len(recent),
        lifetimeSampleSize=len(lifetime),
        reasoning=reasoning,
        simDay=sim_day,
        createdAt=_now_iso(),
    )


def cap_strategy_health_assessments(items: list[StrategyHealthAssessment]) -> list[StrategyHealthAssessment]:
    if len(items) > MAX_STRATEGY_HEALTH_ASSESSMENTS:
        del items[: len(items) - MAX_STRATEGY_HEALTH_ASSESSMENTS]
    return items


def evaluate_retirement_readiness(strategy: Strategy, results: list[SimulationResult]) -> tuple[bool, str]:
    """Trading Psychology & Discipline, Piece B — the real, ENFORCED gate
    on app/sandbox.py's own retire_strategy(), the same "real, ENFORCED
    gate ... returning (bool, str)" pattern evaluate_certification_
    readiness() above already established for the Limited Live Capital
    stage. Closes a gap that function's own docstring in sandbox.py
    already named but never checked: retirement was "expected to cite
    that strategy's own real StrategyHealthAssessment... as the reason,"
    but nothing ever required any real evidence to exist first — a
    strategy could be retired after a single bad run, or none at all,
    the exact "strategy hopping" the CEO's own trading-psychology review
    warned against ("if evidence insufficient, keep current strategy and
    continue collecting data").

    Vacuously ready for a strategy still at "idea"/"research" — those
    stages have no real SimulationResult by construction (nothing has
    been tested yet), so there is no "thin evidence" to gate; abandoning
    a pure idea before ever running a backtest is always a legitimate,
    ungated CEO call, not a data-driven conclusion. Once a strategy has
    entered real empirical testing (historical_backtest or later,
    including a live "approved" strategy), retiring it requires the same
    real trade_count = sum(r.trade_count for r in strategy_results)
    computation evaluate_certification_readiness() already uses — never
    a second, differently-defined "sample size."""
    if stage_index(strategy.stage) < stage_index("historical_backtest"):
        return True, f'"{strategy.name}" has not entered real testing yet — no evidence bar applies to retiring an untested idea.'
    strategy_results = [r for r in results if r.strategy_id == strategy.id]
    trade_count = sum(r.trade_count for r in strategy_results)
    if trade_count < MIN_RETIREMENT_TRADE_COUNT:
        return False, (
            f'"{strategy.name}" has only {trade_count} real trade(s) on file across {len(strategy_results)} real run(s) '
            f"— at least {MIN_RETIREMENT_TRADE_COUNT} are needed before retiring it. A single bad run does not "
            f"invalidate a strategy; run more simulations first to gather real evidence."
        )
    return True, f'"{strategy.name}" has {trade_count} real trade(s) on file across {len(strategy_results)} real run(s) — enough real evidence to retire on.'


def generate_strategy_retirement_outcome(
    strategy: Strategy,
    results: list[SimulationResult],
    latest_review: StrategyReview | None,
    latest_executive_review: StrategyExecutiveReview | None,
    latest_founder_approval: StrategyFounderApproval | None,
    reason: str,
    *,
    sim_day: int,
    latest_model_validation: ModelValidationReport | None = None,
) -> tuple[StrategyHallOfFameEntry | None, FailedStrategyArchiveEntry | None]:
    """Every real retirement produces exactly one of the two permanent
    records below — never both, never neither. `strategy` is the
    strategy's state right before retirement (still carrying its real
    pre-retirement `stage`), since app/sandbox.py's retire_strategy()
    only returns the already-retired copy.

    Quantitative Research & Intelligence System, Piece 6 —
    `latest_model_validation` (Meridian/CIO's independent
    ModelValidationReport, Piece 4) is folded into the failed-archive
    path's own `what_failed`/`lessons_learned` below whenever one exists
    and its verdict isn't `approved`, so a real Model Validation
    rejection becomes real, permanent institutional knowledge (this
    entry is what app/scribe.py's record_strategy_failed_archive_entry()
    turns into a real MemoryRecord) instead of a report nobody
    remembers. Every string folded in is Meridian's own real
    `reasoning`/`evidence`/`evidence_summary` field, never paraphrased or
    invented. Optional and defaulted so every existing caller/test is
    unaffected when no validation report exists for this strategy yet."""
    strategy_results = [r for r in results if r.strategy_id == strategy.id]
    trade_count = sum(r.trade_count for r in strategy_results)
    win_rate = sum(r.win_rate for r in strategy_results) / len(strategy_results) if strategy_results else 0.0
    profit_factor = sum(r.profit_factor for r in strategy_results) / len(strategy_results) if strategy_results else 0.0
    avg_drawdown = sum(r.max_drawdown_pct for r in strategy_results) / len(strategy_results) if strategy_results else 100.0
    avg_return = sum(r.total_return_pct for r in strategy_results) / len(strategy_results) if strategy_results else 0.0
    sim_days_active = max(0, sim_day - strategy.stage_history[0].sim_day) if strategy.stage_history else 0

    qualifies_for_hall_of_fame = (
        strategy.stage == "approved"
        and trade_count >= HALL_OF_FAME_MIN_TRADE_COUNT
        and win_rate >= HALL_OF_FAME_MIN_WIN_RATE
        and profit_factor >= HALL_OF_FAME_MIN_PROFIT_FACTOR
        and avg_drawdown <= HALL_OF_FAME_MAX_AVG_DRAWDOWN
        and latest_founder_approval is not None
        and latest_founder_approval.verdict == "approved"
    )

    if qualifies_for_hall_of_fame:
        legacy_notes = ["Cleared every real validation stage in this pipeline and earned real Founder Approval before retirement."]
        if latest_executive_review is not None:
            legacy_notes.append(latest_executive_review.reason)
        entry = StrategyHallOfFameEntry(
            id=f"hof-strategy-{strategy.id}",
            strategyId=strategy.id,
            strategyName=strategy.name,
            createdBy=strategy.created_by,
            description=strategy.description,
            simDaysActive=sim_days_active,
            tradesExecuted=trade_count,
            winRate=round(win_rate, 1),
            profitFactor=round(profit_factor, 2),
            maxDrawdownPct=round(avg_drawdown, 2),
            historicalReturnPct=round(avg_return, 2),
            legacyNotes=legacy_notes,
            retiredReason=reason,
            simDay=sim_day,
            inductedAt=_now_iso(),
        )
        return entry, None

    what_failed = [v.summary for v in latest_review.verdicts if v.verdict != "pass"] if latest_review is not None else []
    lessons_learned: list[str] = []
    if latest_executive_review is not None:
        for opinion in latest_executive_review.opinions:
            lessons_learned.extend(opinion.concerns)
    if latest_model_validation is not None and latest_model_validation.verdict != "approved":
        what_failed.append(
            f"Independent Model Validation (Meridian/CIO): {latest_model_validation.verdict.replace('_', ' ')} — {latest_model_validation.evidence_summary}"
        )
        lessons_learned.extend(
            f"Model Validation — {check.label}: {check.reasoning}"
            for check in latest_model_validation.checks
            if check.passed is False
        )
    if not what_failed:
        what_failed = ["Retired before completing enough real validation stages to file specific findings."]
    if not lessons_learned:
        lessons_learned = ["No department ever filed a real concern against this strategy — it was retired for other reasons."]

    archive_entry = FailedStrategyArchiveEntry(
        id=f"failedarchive-{strategy.id}",
        strategyId=strategy.id,
        strategyName=strategy.name,
        createdBy=strategy.created_by,
        failedAtStage=strategy.stage,
        whatFailed=what_failed,
        lessonsLearned=lessons_learned,
        retiredReason=reason,
        simDay=sim_day,
        createdAt=_now_iso(),
    )
    return None, archive_entry


def cap_strategy_hall_of_fame(items: list[StrategyHallOfFameEntry]) -> list[StrategyHallOfFameEntry]:
    if len(items) > MAX_STRATEGY_HALL_OF_FAME:
        del items[: len(items) - MAX_STRATEGY_HALL_OF_FAME]
    return items


def cap_strategy_failed_archive(items: list[FailedStrategyArchiveEntry]) -> list[FailedStrategyArchiveEntry]:
    if len(items) > MAX_STRATEGY_FAILED_ARCHIVE:
        del items[: len(items) - MAX_STRATEGY_FAILED_ARCHIVE]
    return items


def compute_strategy_executive_dashboard(
    strategies: list[Strategy],
    results: list[SimulationResult],
    reviews: list[StrategyReview],
    monte_carlo_results: list[StrategyMonteCarloResult],
    regime_tests: list[StrategyRegimeTestReport],
    executive_reviews: list[StrategyExecutiveReview],
    hall_of_fame: list[StrategyHallOfFameEntry],
    failed_archive: list[FailedStrategyArchiveEntry],
    *,
    sim_day: int,
) -> StrategyExecutiveDashboard:
    """Real, computed-on-request aggregate — every count and named slot
    below reads already-real Strategy/SimulationResult/review history,
    never a second source of truth (same reasoning as
    generate_strategy_dossier())."""
    non_retired = [s for s in strategies if s.stage != "retired"]
    in_development: list[Strategy] = [s for s in non_retired if s.stage in ("idea", "research")]
    in_validation: list[Strategy] = [s for s in non_retired if s.stage in ("historical_backtest", "market_simulation", "limited_live_capital", "company_review")]
    paper_trading: list[Strategy] = [s for s in non_retired if s.stage == "paper_trading"]
    approved: list[Strategy] = [s for s in non_retired if s.stage == "approved"]
    retired: list[Strategy] = [s for s in strategies if s.stage == "retired"]

    def _avg_return(strategy: Strategy) -> float | None:
        strategy_results = [r for r in results if r.strategy_id == strategy.id]
        return sum(r.total_return_pct for r in strategy_results) / len(strategy_results) if strategy_results else None

    scored = [(s, v) for s in strategies for v in [_avg_return(s)] if v is not None]
    best_strategy = None
    weakest_strategy = None
    if scored:
        best_s, best_v = max(scored, key=lambda pair: pair[1])
        worst_s, worst_v = min(scored, key=lambda pair: pair[1])
        best_strategy = StrategyExecutiveDashboardEntry(strategyId=best_s.id, strategyName=best_s.name, metricLabel="Average real return", metricValue=round(best_v, 2))
        weakest_strategy = StrategyExecutiveDashboardEntry(strategyId=worst_s.id, strategyName=worst_s.name, metricLabel="Average real return", metricValue=round(worst_v, 2))

    most_improved: StrategyExecutiveDashboardEntry | None = None
    best_delta: float | None = None
    for s in strategies:
        health = compute_strategy_health(s, results, sim_day=sim_day)
        if health is None:
            continue
        delta = health.recent_avg_return_pct - health.lifetime_avg_return_pct
        if best_delta is None or delta > best_delta:
            best_delta = delta
            most_improved = StrategyExecutiveDashboardEntry(strategyId=s.id, strategyName=s.name, metricLabel="Recent vs. lifetime return delta", metricValue=round(delta, 2))

    newest_strategy = None
    if strategies:
        newest = max(strategies, key=lambda s: s.created_at)
        newest_strategy = StrategyExecutiveDashboardEntry(strategyId=newest.id, strategyName=newest.name, metricLabel="Most recently created", metricValue=0.0)

    highest_confidence: StrategyExecutiveDashboardEntry | None = None
    best_confidence: float | None = None
    for s in strategies:
        review = next((r for r in reversed(reviews) if r.strategy_id == s.id), None)
        monte_carlo = next((r for r in reversed(monte_carlo_results) if r.strategy_id == s.id), None)
        regime_test = next((r for r in reversed(regime_tests) if r.strategy_id == s.id), None)
        executive_review = next((r for r in reversed(executive_reviews) if r.strategy_id == s.id), None)
        if review is None and monte_carlo is None and executive_review is None:
            continue
        score = compute_strategy_confidence_score(s, review, monte_carlo, regime_test, executive_review, sim_day=sim_day)
        if best_confidence is None or score.overall_confidence_pct > best_confidence:
            best_confidence = score.overall_confidence_pct
            highest_confidence = StrategyExecutiveDashboardEntry(strategyId=s.id, strategyName=s.name, metricLabel="Confidence score", metricValue=score.overall_confidence_pct)

    return StrategyExecutiveDashboard(
        activeCount=len(non_retired),
        inDevelopmentCount=len(in_development),
        inValidationCount=len(in_validation),
        paperTradingCount=len(paper_trading),
        approvedCount=len(approved),
        retiredCount=len(retired),
        hallOfFameCount=len(hall_of_fame),
        failedArchiveCount=len(failed_archive),
        bestStrategy=best_strategy,
        weakestStrategy=weakest_strategy,
        mostImprovedStrategy=most_improved,
        newestStrategy=newest_strategy,
        highestConfidenceStrategy=highest_confidence,
        generatedAt=_now_iso(),
    )


# ---------------------------------------------------------------------
# v0.7 Feature 53 — Company Certification. A real, formal checklist
# combining every already-real Feature 52 artifact — never a new
# measurement. Two of the brief's thirteen requirements (Founder
# Approval, Final CEO Approval) can only ever be real once a strategy
# reaches Company Review — see app/sandbox.py's own pipeline order
# (paper_trading -> limited_live_capital -> company_review -> approved)
# — so full `certified` status is only ever True at stage == "approved".
# evaluate_certification_readiness() below is the real, ENFORCED subset
# of this same checklist (only the requirements achievable before
# Company Review) that gates begin_limited_live_capital itself — see
# app/state.py's begin_strategy_limited_live().
# ---------------------------------------------------------------------


def _department_approved(executive_review: StrategyExecutiveReview | None, role: ExecutiveDepartmentRole) -> tuple[bool, str]:
    if executive_review is None:
        return False, "No real Executive Review on file yet."
    opinion = next((o for o in executive_review.opinions if o.role == role), None)
    if opinion is None:
        return False, "No real opinion on file yet."
    return opinion.stance == "agree", f"Real stance: {opinion.stance.replace('_', ' ')}."


def compute_strategy_certification(
    strategy: Strategy,
    results: list[SimulationResult],
    review: StrategyReview | None,
    monte_carlo: StrategyMonteCarloResult | None,
    regime_test: StrategyRegimeTestReport | None,
    executive_review: StrategyExecutiveReview | None,
    founder_approval: StrategyFounderApproval | None,
    health: StrategyHealthAssessment | None,
    look_ahead_audit: LookAheadAuditResult | None = None,
    cost_sensitivity: CostSensitivityResult | None = None,
    walk_forward: WalkForwardValidationResult | None = None,
) -> StrategyCertification:
    """`certified` is recomputed fresh from the strategy's own real
    current state every call — so a real health decline after
    certification (StrategyHealthAssessment.status turning "critical"/
    "retire_candidate") automatically fails the Health Standing
    requirement the next time this runs. No separate persisted "revoked"
    flag or event log is needed for the brief's "may be revoked at any
    time" rule — see this function's own StrategyCertification docstring
    in app/schemas.py.

    CEO directive "Professional Research → Certification → Paper →
    Capital Allocation Pipeline" — a repo-wide audit found this
    function's original 13 requirements read EXCLUSIVELY from this
    module's own placeholder-RNG-backed simulation objects
    (`SimulationResult`/`StrategyMonteCarloResult`/
    `StrategyRegimeTestReport`), never from the genuinely rigorous,
    real bar-by-bar "Research Desk" validation modules
    (`app/leakage_audit.py`, `app/cost_sensitivity.py`,
    `app/walk_forward.py`) — meaning a strategy could reach
    `certified: true` having never once been checked for look-ahead
    bias, cost/slippage resilience, or genuine out-of-sample stability.
    `look_ahead_audit`/`cost_sensitivity`/`walk_forward` close that gap
    by adding three new requirements that read those SAME real modules'
    real output — never a second, parallel validation engine. All three
    are optional (default `None`) so every existing caller keeps working
    unchanged; a `None` value here means the check honestly wasn't run,
    and — per this directive's own "if not, FAIL, do not hide the
    failure" rule — that reads as `met=False`, never a silent pass.
    `strategy.compiled_definition_id` being `None` (a Strategy with no
    real compiled trading rules behind it yet — see that field's own
    docstring) gets its own honest detail message distinguishing "never
    checked" from "has nothing checkable yet." """
    strategy_results = [r for r in results if r.strategy_id == strategy.id]
    trade_count = sum(r.trade_count for r in strategy_results)
    expectancy = sum(r.expected_value_pct for r in strategy_results) / len(strategy_results) if strategy_results else 0.0
    tested_buckets = [b for b in regime_test.buckets if b.tested] if regime_test else []
    weak_buckets = [b for b in tested_buckets if b.verdict == "weak"]

    risk_ok, risk_detail = _department_approved(executive_review, "risk")
    market_intel_ok, market_intel_detail = _department_approved(executive_review, "market_intelligence")
    quant_ok, quant_detail = _department_approved(executive_review, "quant")
    simulation_ok, simulation_detail = _department_approved(executive_review, "simulation")
    decision_intel_ok, decision_intel_detail = _department_approved(executive_review, "decision_intelligence")

    requirements = [
        StrategyCertificationRequirement(
            id="sample_size",
            label="Minimum Validated Trade Sample Size",
            met=trade_count >= CERTIFICATION_MIN_TRADE_COUNT,
            detail=f"{trade_count} real trade(s) across {len(strategy_results)} real run(s) (needs ≥{CERTIFICATION_MIN_TRADE_COUNT}).",
        ),
        StrategyCertificationRequirement(
            id="expectancy",
            label="Positive Expectancy Over A Statistically Significant Sample",
            met=len(strategy_results) > 0 and expectancy > 0,
            detail=f"Real expected value {expectancy:+.2f}% per trade across {len(strategy_results)} real run(s)." if strategy_results else "No real runs on file yet.",
        ),
        StrategyCertificationRequirement(
            id="drawdown",
            label="Acceptable Maximum Drawdown",
            met=monte_carlo is not None and monte_carlo.worst_case_drawdown_pct <= CERTIFICATION_MAX_WORST_CASE_DRAWDOWN_PCT,
            detail=(
                f"Real worst-case (5th percentile) Monte Carlo drawdown {monte_carlo.worst_case_drawdown_pct:.1f}% (needs ≤{CERTIFICATION_MAX_WORST_CASE_DRAWDOWN_PCT:.0f}%)."
                if monte_carlo
                else "No real Monte Carlo run on file yet."
            ),
        ),
        StrategyCertificationRequirement(
            id="regime_consistency",
            label="Consistent Profitability Across Multiple Market Regimes",
            met=len(tested_buckets) >= 2 and not weak_buckets,
            detail=(f"Tested in {len(tested_buckets)} real Testing Environment(s), {len(weak_buckets)} weak." if regime_test else "No real Market Regime Testing on file yet."),
        ),
        StrategyCertificationRequirement(
            id="paper_trading",
            label="Successful Paper Trading Phase",
            met=stage_index(strategy.stage) >= stage_index("paper_trading"),
            detail=f"Currently at real pipeline stage: {strategy.stage.replace('_', ' ')}.",
        ),
        StrategyCertificationRequirement(
            id="monte_carlo",
            label="Successful Monte Carlo Testing",
            met=monte_carlo is not None and monte_carlo.probability_of_ruin_pct <= CERTIFICATION_MAX_RUIN_PCT,
            detail=(
                f"Real probability of ruin {monte_carlo.probability_of_ruin_pct:.1f}% across {monte_carlo.paths_simulated} simulated paths (needs ≤{CERTIFICATION_MAX_RUIN_PCT:.0f}%)."
                if monte_carlo
                else "No real Monte Carlo run on file yet."
            ),
        ),
        StrategyCertificationRequirement(
            id="stress_test",
            label="Successful Stress Testing",
            met=monte_carlo is not None and monte_carlo.return_range_low_pct > CERTIFICATION_MIN_STRESS_RETURN_PCT and not weak_buckets,
            detail=(
                f"Real 10th-percentile Monte Carlo return {monte_carlo.return_range_low_pct:+.1f}% with {len(weak_buckets)} weak real regime(s)."
                if monte_carlo
                else "No real Monte Carlo run on file yet — nothing real to stress-test."
            ),
        ),
        StrategyCertificationRequirement(id="risk_approval", label="Risk Department Approval", met=risk_ok, detail=risk_detail),
        StrategyCertificationRequirement(id="market_intelligence_approval", label="Market Intelligence Approval", met=market_intel_ok, detail=market_intel_detail),
        StrategyCertificationRequirement(id="quant_approval", label="Quant Department Approval", met=quant_ok, detail=quant_detail),
        StrategyCertificationRequirement(id="simulation_approval", label="Simulation Department Approval", met=simulation_ok, detail=simulation_detail),
        StrategyCertificationRequirement(id="decision_intelligence_approval", label="Decision Intelligence Approval", met=decision_intel_ok, detail=decision_intel_detail),
        StrategyCertificationRequirement(
            id="founder_approval",
            label="Founder Approval",
            met=founder_approval is not None and founder_approval.verdict == "approved",
            detail=founder_approval.verdict_reason if founder_approval else "No real Founder Approval on file yet.",
        ),
        StrategyCertificationRequirement(
            id="ceo_approval",
            label="Final CEO Approval",
            met=review is not None and review.ceo_decision == "approved",
            detail=(f"Real Company Review decision: {review.ceo_decision.replace('_', ' ')}." if review else "No real Company Review on file yet."),
        ),
        StrategyCertificationRequirement(
            id="health_standing",
            label="Health Standing Not Deteriorated",
            met=health is None or health.status not in ("critical", "retire_candidate"),
            detail=(f"Real current Strategy Health: {health.status.replace('_', ' ')}." if health else "No real Strategy Health assessment on file yet — treated as a pass by default."),
        ),
        StrategyCertificationRequirement(
            id="look_ahead_clear",
            label="No Look-Ahead / Data-Leakage Bias Detected",
            met=look_ahead_audit is not None and look_ahead_audit.verdict == "clean",
            detail=(
                f"Real structural look-ahead audit: {look_ahead_audit.setups_checked} real setup(s) checked against real candle history, {len(look_ahead_audit.violations)} violation(s) found — verdict {look_ahead_audit.verdict.replace('_', ' ')}."
                if look_ahead_audit is not None
                else ("No compiled trading rules exist yet to audit." if strategy.compiled_definition_id is None else "No real look-ahead audit on file yet.")
            ),
        ),
        StrategyCertificationRequirement(
            id="cost_sensitivity",
            label="Survives Realistic Transaction Costs",
            met=cost_sensitivity is not None and cost_sensitivity.verdict == "cost_resilient",
            detail=(
                f"Real cost/slippage sensitivity sweep verdict: {cost_sensitivity.verdict.replace('_', ' ')}."
                if cost_sensitivity is not None
                else ("No compiled trading rules exist yet to cost-test." if strategy.compiled_definition_id is None else "No real cost-sensitivity run on file yet.")
            ),
        ),
        StrategyCertificationRequirement(
            id="walk_forward_stable",
            label="Stable Across Genuine Walk-Forward Windows",
            met=walk_forward is not None and walk_forward.verdict == "stable",
            detail=(
                f"Real walk-forward validation verdict: {walk_forward.verdict.replace('_', ' ')} across {len(walk_forward.symbols)} real symbol(s)' own chronological windows."
                if walk_forward is not None
                else ("No compiled trading rules exist yet to walk-forward validate." if strategy.compiled_definition_id is None else "No real walk-forward run on file yet.")
            ),
        ),
    ]

    return StrategyCertification(
        strategyId=strategy.id,
        strategyName=strategy.name,
        certified=all(r.met for r in requirements),
        requirements=requirements,
        generatedAt=_now_iso(),
    )


def evaluate_certification_readiness(
    strategy: Strategy,
    results: list[SimulationResult],
    monte_carlo: StrategyMonteCarloResult | None,
    regime_test: StrategyRegimeTestReport | None,
    look_ahead_audit: LookAheadAuditResult | None = None,
    cost_sensitivity: CostSensitivityResult | None = None,
    walk_forward: WalkForwardValidationResult | None = None,
) -> tuple[bool, str]:
    """The real, ENFORCED gate on begin_limited_live_capital — the brief's
    'no strategy may trade live capital without Certification', narrowed
    to exactly the checklist items that can honestly exist this early in
    the real pipeline (Founder/CEO/Executive-Review approval only ever
    happen later, at Company Review — see this module's own section
    docstring above). Reuses the exact same real thresholds as
    compute_strategy_certification() rather than a second set of
    numbers.

    CEO directive "Professional Research → Certification → Paper →
    Capital Allocation Pipeline" — `look_ahead_audit`/`cost_sensitivity`/
    `walk_forward` (optional, default `None`) close the same real gap
    `compute_strategy_certification()`'s own docstring explains: before
    this, a strategy could reach live capital never having been checked
    for look-ahead bias, cost/slippage resilience, or genuine walk-
    forward stability. A `None` value (the check wasn't run, or the
    strategy has no `compiled_definition_id` yet) is a real failure
    here, exactly like every other missing-evidence case this function
    already treats as not-ready — never a silent pass."""
    strategy_results = [r for r in results if r.strategy_id == strategy.id]
    trade_count = sum(r.trade_count for r in strategy_results)
    expectancy = sum(r.expected_value_pct for r in strategy_results) / len(strategy_results) if strategy_results else 0.0
    tested_buckets = [b for b in regime_test.buckets if b.tested] if regime_test else []
    weak_buckets = [b for b in tested_buckets if b.verdict == "weak"]

    failures: list[str] = []
    if trade_count < CERTIFICATION_MIN_TRADE_COUNT:
        failures.append(f"only {trade_count} real trade(s) on file (needs ≥{CERTIFICATION_MIN_TRADE_COUNT})")
    if not strategy_results or expectancy <= 0:
        failures.append("no real positive expectancy on file yet")
    if monte_carlo is None:
        failures.append("no real Monte Carlo run on file yet")
    else:
        if monte_carlo.worst_case_drawdown_pct > CERTIFICATION_MAX_WORST_CASE_DRAWDOWN_PCT:
            failures.append(f"worst-case Monte Carlo drawdown {monte_carlo.worst_case_drawdown_pct:.1f}% exceeds {CERTIFICATION_MAX_WORST_CASE_DRAWDOWN_PCT:.0f}%")
        if monte_carlo.probability_of_ruin_pct > CERTIFICATION_MAX_RUIN_PCT:
            failures.append(f"probability of ruin {monte_carlo.probability_of_ruin_pct:.1f}% exceeds {CERTIFICATION_MAX_RUIN_PCT:.0f}%")
        if monte_carlo.return_range_low_pct <= CERTIFICATION_MIN_STRESS_RETURN_PCT:
            failures.append(f"stress-case (10th percentile) return {monte_carlo.return_range_low_pct:+.1f}% fails real stress testing")
    if len(tested_buckets) < 2:
        failures.append("tested in fewer than 2 real Testing Environments yet")
    elif weak_buckets:
        failures.append(f"{len(weak_buckets)} real regime bucket(s) show weak performance")
    if strategy.compiled_definition_id is None:
        failures.append("no compiled trading rules exist yet to run a real look-ahead/cost/walk-forward validation against")
    else:
        if look_ahead_audit is None:
            failures.append("no real look-ahead audit on file yet")
        elif look_ahead_audit.verdict != "clean":
            failures.append(f"look-ahead audit verdict is {look_ahead_audit.verdict.replace('_', ' ')}, not clean")
        if cost_sensitivity is None:
            failures.append("no real cost-sensitivity run on file yet")
        elif cost_sensitivity.verdict != "cost_resilient":
            failures.append(f"cost-sensitivity verdict is {cost_sensitivity.verdict.replace('_', ' ')}, not cost-resilient")
        if walk_forward is None:
            failures.append("no real walk-forward validation on file yet")
        elif walk_forward.verdict != "stable":
            failures.append(f"walk-forward verdict is {walk_forward.verdict.replace('_', ' ')}, not stable")

    if failures:
        return False, f'"{strategy.name}" is not yet Certification-ready for live capital: {"; ".join(failures)}.'
    return True, f'"{strategy.name}" clears every real Certification readiness check available at this stage.'
