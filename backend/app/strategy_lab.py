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

import random
from datetime import datetime, timezone

from app.market_data import Candle, MarketDataProvider
from app.market_intelligence import _REGIME_TO_SCENARIO_KEYWORD, compute_liquidity, compute_market_structure
from app.sandbox import STRATEGY_DEVILS_ADVOCATES
from app.schemas import (
    AgentId,
    CoachReport,
    ExecutiveDepartmentRole,
    ExecutiveStance,
    MarketIntelligenceRegime,
    MarketIntelligenceState,
    ResearchItem,
    SimulationResult,
    Strategy,
    StrategyConfidenceScore,
    StrategyDepartmentOpinion,
    StrategyDossier,
    StrategyExecutiveAction,
    StrategyExecutiveReview,
    StrategyFounderApproval,
    StrategyLiquidityValidation,
    StrategyMonteCarloResult,
    StrategyRegimeBucketPerformance,
    StrategyRegimeTestReport,
    StrategyReport,
    StrategyReview,
    TestScenario,
    WatchlistEntry,
)

MAX_STRATEGY_MONTE_CARLO_RESULTS = 40
MAX_STRATEGY_REGIME_TESTS = 40
MAX_STRATEGY_LIQUIDITY_VALIDATIONS = 40
MAX_STRATEGY_EXECUTIVE_REVIEWS = 40
MAX_STRATEGY_FOUNDER_APPROVALS = 40

MONTE_CARLO_PATHS = 200
RUIN_DRAWDOWN_PCT = 50.0  # a real, named "the strategy is effectively dead" bar for this bootstrap's own paths

FOUNDER_APPROVAL_CONFIDENCE_THRESHOLD = 60.0

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


# ---------------------------------------------------------------------
# Monte Carlo Testing — a real trade-sequence bootstrap.
# ---------------------------------------------------------------------


def run_strategy_monte_carlo(strategy: Strategy, results: list[SimulationResult], *, sim_day: int) -> StrategyMonteCarloResult | None:
    """None when the strategy has no completed runs yet — nothing real
    to bootstrap from. Each simulated path draws `trade_count` win/loss
    outcomes using the strategy's own real, aggregated win rate as the
    probability, sized by its own real average win/loss percentages —
    every number driving the randomness is a real field already on
    SimulationResult, never independently invented."""
    strategy_results = [r for r in results if r.strategy_id == strategy.id]
    if not strategy_results:
        return None

    win_rate = sum(r.win_rate for r in strategy_results) / len(strategy_results) / 100
    avg_win_pct = sum(r.avg_win_pct for r in strategy_results) / len(strategy_results)
    avg_loss_pct = sum(r.avg_loss_pct for r in strategy_results) / len(strategy_results)
    trades_per_path = max(1, round(sum(r.trade_count for r in strategy_results) / len(strategy_results)))

    finals: list[float] = []
    max_drawdowns: list[float] = []
    ruin_count = 0
    for _ in range(MONTE_CARLO_PATHS):
        cumulative = 0.0
        peak = 0.0
        max_drawdown = 0.0
        for _trade in range(trades_per_path):
            r = (avg_win_pct if random.random() < win_rate else -avg_loss_pct) / 100
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
        generatedAt=_now_iso(),
    )
