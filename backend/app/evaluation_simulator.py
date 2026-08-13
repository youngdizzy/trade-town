"""app/evaluation_simulator.py — Quantitative Research & Intelligence
System, Requirements 21/22/23/25 (Prop-Firm Risk Intelligence Addendum,
Piece 10).

ARCHITECTURAL PRINCIPLE (verbatim from the CEO's own directive): "No
Fast Pass policy becomes production behavior merely because the source
claims it works." This module treats the source video's "reach the
funded stage quickly" claim as a hypothesis TradeTown tests, never a
fact it hard-codes. It compares four named, explicitly labeled risk
policies via a real Monte Carlo evaluation-level race simulation — never
concludes that the fastest policy is best merely because it's fastest
(Requirement 25: speed is an objective to weigh, not a license to
gamble).

WHAT THIS MODULE REUSES, NOT DUPLICATES. `app/strategy_lab.py`'s
`run_strategy_monte_carlo()` already bootstraps a per-trade win/loss
sequence from a strategy's own real, aggregated `SimulationResult`
fields (`win_rate`, `avg_win_pct`, `avg_loss_pct`) — that per-trade
bootstrap shape (draw a random outcome, compound it into cumulative
equity) is the exact same generating idea this module reuses. What that
function does NOT have — and what this module adds, genuinely new — is
a day/trade-axis RACE CONDITION: does the path hit a profit target
before it hits a drawdown limit before it runs out of time? That
three-way race is a real evaluation, not a "does this look risky"
snapshot, and did not exist anywhere in this codebase before this
module (grep-confirmed: no "profit_target" vs "drawdown_limit" vs
"max_trades" race exists in `strategy_lab.py`, `simulation.py`, or
`whatif.py`).

EVERY NUMBER BELOW THAT ISN'T FROM REAL DATA IS AN EXPLICIT, DISCLOSED
ASSUMPTION, listed here once so no report has to re-derive what it
means:

- `BASELINE_RISK_PER_TRADE_PCT` (2.0) is `RiskLimits.risk_per_trade_pct`'s
  own real default (`app/schemas.py`). A `SimulationResult`'s
  `avg_win_pct`/`avg_loss_pct` are treated as having been generated
  under this baseline risk setting (this codebase doesn't track what
  risk-per-trade a given `SimulationResult` actually used), so scaling
  those per-trade returns to a different policy's `risk_per_trade_pct`
  is a real, stated LINEAR SCALING ASSUMPTION, not a fabricated
  distribution. `_scale_return()` implements this and only this.
- The four named policies (`RISK_POLICY_PER_TRADE_PCT`,
  `FAILURE_BOUNDARY_RISK_FRACTION`) are real numbers this module
  commits to testing, not numbers it presents as already validated —
  see each constant's own comment for its provenance. Per the CEO's own
  IMPLEMENTATION BOUNDARIES, this module never assumes any of them is
  universally optimal; `simulate_evaluation_policy()` runs each exactly
  the same way and lets the real simulated outcomes speak.
- `ASSUMED_TRADES_PER_DAY` (2.0) converts a simulated trade count into
  an implied day count. This codebase has no real historical
  "trades per calendar day" statistic for any strategy to derive this
  from — it's a plausible, disclosed single-cadence assumption, not
  fit to real data, and every report surfaces it explicitly.
- `DEFAULT_PROFIT_TARGET_PCT`/`DEFAULT_DRAWDOWN_LIMIT_PCT`/
  `DEFAULT_MAX_TRADES` are used only when the account being simulated
  against has no real `challenge_profit_target_pct`/
  `trailing_drawdown_limit_pct`/`challenge_duration_days` configured
  (`app/accounts.py`'s `configure_prop_firm_rules`) — real account
  configuration always takes priority when present.
- `EVALUATION_SIM_PATHS` (500) is this module's real, disclosed sample
  size — smaller than a production-grade Monte Carlo run, chosen so
  results compute inside a single request; every report exposes it
  plainly rather than implying a larger, more authoritative sample.

WHAT THIS MODULE DELIBERATELY DOES NOT ATTEMPT (real scope cuts, not
silent gaps): real per-regime sensitivity (`StrategyRegimeTestReport`'s
buckets track `avg_return_pct`, not the `win_rate`/`avg_win_pct`/
`avg_loss_pct` triplet this simulator needs — re-deriving those per
regime honestly would need real per-regime trade data this codebase
doesn't have yet); downstream funded-stage performance (Piece 10a's
`Account.funded_stage_reached` is a real, explicit CEO action, never
linked to a simulated path — connecting the two would mean claiming a
simulated evaluation outcome predicts a real funded account's real
future performance, which this module refuses to claim). Both are
disclosed in every `EvaluationPolicyComparisonReport.limitations` list,
not silently omitted.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timezone

from app.schemas import (
    Account,
    EvaluationPolicyComparisonReport,
    EvaluationPolicySimulationResult,
    EvaluationRiskPolicyId,
    SimulationResult,
    Strategy,
)

# See module docstring — RiskLimits.risk_per_trade_pct's own real default
# (app/schemas.py), used as the assumed baseline a SimulationResult's
# avg_win_pct/avg_loss_pct were generated under.
BASELINE_RISK_PER_TRADE_PCT = 2.0

# Four named, disclosed HYPOTHESES (Requirement 21) — never adopted as
# fact. "moderate" intentionally matches BASELINE_RISK_PER_TRADE_PCT
# (this codebase's own existing default); "conservative"/"aggressive"
# are real, symmetric-ish variants chosen to be comparable, not fit to
# any real data.
RISK_POLICY_PER_TRADE_PCT: dict[EvaluationRiskPolicyId, float] = {
    "conservative": 1.0,
    "moderate": 2.0,
    "aggressive": 3.0,
}

# The source video's own suggested range for risking a fraction of the
# account's failure boundary was "1/4-1/8" — the CEO's own
# IMPLEMENTATION BOUNDARIES explicitly forbid assuming that's
# universally optimal. This module tests exactly one point in that
# range (1/8, the more conservative end) as ONE hypothesis among four,
# not as an endorsed value — see EvaluationPolicySimulationResult's own
# docstring for how its results are reported without a declared winner.
FAILURE_BOUNDARY_RISK_FRACTION = 0.125

RISK_POLICY_LABEL: dict[EvaluationRiskPolicyId, str] = {
    "conservative": "Conservative (fixed risk/trade)",
    "moderate": "Moderate (fixed risk/trade, matches company default)",
    "aggressive": "Aggressive (fixed risk/trade)",
    "failure_boundary_relative": "Failure-Boundary-Relative (1/8 of real trailing-drawdown limit)",
}

# See module docstring for full provenance of every constant below.
ASSUMED_TRADES_PER_DAY = 2.0
DEFAULT_PROFIT_TARGET_PCT = 8.0
DEFAULT_DRAWDOWN_LIMIT_PCT = 10.0
DEFAULT_MAX_TRADES = 200
EVALUATION_SIM_PATHS = 500

# Mirrors TradingModeState.losing_streak_suspend_count's own real
# default (app/schemas.py) — the same real, already-CEO-meaningful
# consecutive-loss count reused here rather than a second, independently
# invented threshold.
CONSECUTIVE_LOSS_STREAK_THRESHOLD = 5

# Requirement 21's "sensitivity to strategy quality" — a real, disclosed
# win-rate delta (percentage points) the simulation is rerun at, not a
# claim about how much any real strategy's quality could actually drift.
STRATEGY_QUALITY_SENSITIVITY_DELTA_PP = 5.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _scale_return(pct: float, risk_per_trade_pct: float) -> float:
    """See module docstring's LINEAR SCALING ASSUMPTION. Scales a
    per-trade % return (assumed generated under BASELINE_RISK_PER_TRADE_PCT)
    linearly to a different risk_per_trade_pct."""
    if BASELINE_RISK_PER_TRADE_PCT <= 0:
        return pct
    return pct * (risk_per_trade_pct / BASELINE_RISK_PER_TRADE_PCT)


@dataclass
class _PathOutcome:
    result: str  # "passed" | "failed_drawdown" | "failed_time_expiry"
    trades: int
    max_drawdown_pct: float
    max_consecutive_losses: int


def _simulate_one_path(
    *,
    win_rate: float,
    scaled_win_pct: float,
    scaled_loss_pct: float,
    profit_target_pct: float,
    drawdown_limit_pct: float,
    max_trades: int,
) -> _PathOutcome:
    equity = 0.0
    peak = 0.0
    path_max_drawdown_pct = 0.0
    consecutive_losses = 0
    max_consecutive_losses = 0

    for trade_idx in range(1, max_trades + 1):
        is_win = random.random() < win_rate
        # avg_loss_pct on a real SimulationResult is already a negative
        # number (see app/simulation.py's own loss_range, e.g. (-10.0,
        # -1.5)) — applied directly here, never negated, so a loss trade
        # actually subtracts from equity.
        r = (scaled_win_pct if is_win else scaled_loss_pct) / 100
        equity = (1 + equity) * (1 + r) - 1
        peak = max(peak, equity)
        drawdown_pct = (peak - equity) * 100
        path_max_drawdown_pct = max(path_max_drawdown_pct, drawdown_pct)

        if is_win:
            consecutive_losses = 0
        else:
            consecutive_losses += 1
            max_consecutive_losses = max(max_consecutive_losses, consecutive_losses)

        if drawdown_pct >= drawdown_limit_pct:
            return _PathOutcome("failed_drawdown", trade_idx, path_max_drawdown_pct, max_consecutive_losses)
        if equity * 100 >= profit_target_pct:
            return _PathOutcome("passed", trade_idx, path_max_drawdown_pct, max_consecutive_losses)

    return _PathOutcome("failed_time_expiry", max_trades, path_max_drawdown_pct, max_consecutive_losses)


def _percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    idx = min(len(sorted_values) - 1, max(0, int(len(sorted_values) * p)))
    return sorted_values[idx]


def _run_paths(
    *,
    win_rate: float,
    avg_win_pct: float,
    avg_loss_pct: float,
    risk_per_trade_pct: float,
    profit_target_pct: float,
    drawdown_limit_pct: float,
    max_trades: int,
    paths: int,
) -> list[_PathOutcome]:
    scaled_win_pct = _scale_return(avg_win_pct, risk_per_trade_pct)
    scaled_loss_pct = _scale_return(avg_loss_pct, risk_per_trade_pct)
    return [
        _simulate_one_path(
            win_rate=win_rate,
            scaled_win_pct=scaled_win_pct,
            scaled_loss_pct=scaled_loss_pct,
            profit_target_pct=profit_target_pct,
            drawdown_limit_pct=drawdown_limit_pct,
            max_trades=max_trades,
        )
        for _ in range(paths)
    ]


def simulate_evaluation_policy(
    *,
    policy_id: EvaluationRiskPolicyId,
    risk_per_trade_pct: float,
    win_rate: float,
    avg_win_pct: float,
    avg_loss_pct: float,
    profit_target_pct: float,
    drawdown_limit_pct: float,
    max_trades: int,
    evaluation_cost: float | None,
    paths: int = EVALUATION_SIM_PATHS,
) -> EvaluationPolicySimulationResult:
    """A real Monte Carlo evaluation-level race simulation for one named
    risk policy — see module docstring for the full disclosure of every
    assumption this makes. `win_rate` is 0-1; every _pct parameter is a
    real percentage."""
    outcomes = _run_paths(
        win_rate=win_rate,
        avg_win_pct=avg_win_pct,
        avg_loss_pct=avg_loss_pct,
        risk_per_trade_pct=risk_per_trade_pct,
        profit_target_pct=profit_target_pct,
        drawdown_limit_pct=drawdown_limit_pct,
        max_trades=max_trades,
        paths=paths,
    )

    passed = [o for o in outcomes if o.result == "passed"]
    failed_drawdown = [o for o in outcomes if o.result == "failed_drawdown"]
    failed_time = [o for o in outcomes if o.result == "failed_time_expiry"]

    probability_of_passing_pct = round(len(passed) / len(outcomes) * 100, 1)
    probability_of_failing_drawdown_pct = round(len(failed_drawdown) / len(outcomes) * 100, 1)
    probability_of_failing_time_expiry_pct = round(len(failed_time) / len(outcomes) * 100, 1)

    expected_trades_to_pass = round(sum(o.trades for o in passed) / len(passed), 1) if passed else None
    expected_trading_days_to_pass = round(expected_trades_to_pass / ASSUMED_TRADES_PER_DAY, 1) if expected_trades_to_pass is not None else None
    expected_cost_to_pass = round(evaluation_cost / (len(passed) / len(outcomes)), 2) if evaluation_cost is not None and passed else None

    all_drawdowns = sorted(o.max_drawdown_pct for o in outcomes)
    median_max_drawdown_pct = round(_percentile(all_drawdowns, 0.50), 2)
    worst_case_max_drawdown_pct = round(_percentile(all_drawdowns, 0.95), 2)

    streak_count = sum(1 for o in outcomes if o.max_consecutive_losses >= CONSECUTIVE_LOSS_STREAK_THRESHOLD)
    probability_of_consecutive_loss_streak_pct = round(streak_count / len(outcomes) * 100, 1)

    risk_adjusted_outcome = round(probability_of_passing_pct / max(median_max_drawdown_pct, 0.01), 2)

    lower_outcomes = _run_paths(
        win_rate=max(0.0, win_rate - STRATEGY_QUALITY_SENSITIVITY_DELTA_PP / 100),
        avg_win_pct=avg_win_pct,
        avg_loss_pct=avg_loss_pct,
        risk_per_trade_pct=risk_per_trade_pct,
        profit_target_pct=profit_target_pct,
        drawdown_limit_pct=drawdown_limit_pct,
        max_trades=max_trades,
        paths=paths,
    )
    higher_outcomes = _run_paths(
        win_rate=min(1.0, win_rate + STRATEGY_QUALITY_SENSITIVITY_DELTA_PP / 100),
        avg_win_pct=avg_win_pct,
        avg_loss_pct=avg_loss_pct,
        risk_per_trade_pct=risk_per_trade_pct,
        profit_target_pct=profit_target_pct,
        drawdown_limit_pct=drawdown_limit_pct,
        max_trades=max_trades,
        paths=paths,
    )
    probability_of_passing_at_lower_quality_pct = round(sum(1 for o in lower_outcomes if o.result == "passed") / len(lower_outcomes) * 100, 1)
    probability_of_passing_at_higher_quality_pct = round(sum(1 for o in higher_outcomes if o.result == "passed") / len(higher_outcomes) * 100, 1)

    return EvaluationPolicySimulationResult(
        policyId=policy_id,
        label=RISK_POLICY_LABEL[policy_id],
        riskPerTradePct=risk_per_trade_pct,
        pathsSimulated=paths,
        probabilityOfPassingPct=probability_of_passing_pct,
        probabilityOfFailingDrawdownPct=probability_of_failing_drawdown_pct,
        probabilityOfFailingTimeExpiryPct=probability_of_failing_time_expiry_pct,
        expectedTradesToPass=expected_trades_to_pass,
        expectedTradingDaysToPass=expected_trading_days_to_pass,
        expectedCostToPass=expected_cost_to_pass,
        medianMaxDrawdownPct=median_max_drawdown_pct,
        worstCaseMaxDrawdownPct=worst_case_max_drawdown_pct,
        probabilityOfConsecutiveLossStreakPct=probability_of_consecutive_loss_streak_pct,
        consecutiveLossStreakThreshold=CONSECUTIVE_LOSS_STREAK_THRESHOLD,
        riskAdjustedOutcome=risk_adjusted_outcome,
        probabilityOfPassingAtLowerQualityPct=probability_of_passing_at_lower_quality_pct,
        probabilityOfPassingAtHigherQualityPct=probability_of_passing_at_higher_quality_pct,
    )


RESEARCH_QUESTION = "Which evaluation-stage risk policy produces the best probability-adjusted outcome for reaching and succeeding in the funded stage while controlling failure risk and evaluation cost?"


def compare_evaluation_policies(
    strategy: Strategy,
    results: list[SimulationResult],
    *,
    account: Account | None,
    sim_day: int,
) -> EvaluationPolicyComparisonReport | None:
    """None when the strategy has no completed simulation runs — nothing
    real to bootstrap from (same honesty boundary as
    run_strategy_monte_carlo()). Real account configuration
    (challenge_profit_target_pct/trailing_drawdown_limit_pct/
    challenge_duration_days) is used when present; otherwise the
    disclosed DEFAULT_* constants apply, and that fallback is stated in
    `assumptions`, never left implicit."""
    strategy_results = [r for r in results if r.strategy_id == strategy.id]
    if not strategy_results:
        return None

    win_rate = sum(r.win_rate for r in strategy_results) / len(strategy_results) / 100
    avg_win_pct = sum(r.avg_win_pct for r in strategy_results) / len(strategy_results)
    avg_loss_pct = sum(r.avg_loss_pct for r in strategy_results) / len(strategy_results)
    sample_trade_count = sum(r.trade_count for r in strategy_results)

    assumptions: list[str] = [
        f"avg_win_pct/avg_loss_pct are treated as generated under a {BASELINE_RISK_PER_TRADE_PCT}% baseline risk-per-trade (RiskLimits' own default) and scaled linearly to each policy's real risk_per_trade_pct — this codebase does not record what risk setting a SimulationResult actually used.",
        f"{ASSUMED_TRADES_PER_DAY} trades/day is a disclosed, honestly-arbitrary assumption used only to convert a simulated trade count into an implied day count.",
        f"Each policy is simulated across {EVALUATION_SIM_PATHS} real Monte Carlo paths — a real but modest sample size, disclosed on every result rather than presented as a larger, more authoritative one.",
        f"win_rate/avg_win_pct/avg_loss_pct are this strategy's own real, aggregated values across {len(strategy_results)} completed simulation run(s) totaling {sample_trade_count} real trades.",
    ]

    profit_target_pct = account.challenge_profit_target_pct if account is not None and account.challenge_profit_target_pct is not None else DEFAULT_PROFIT_TARGET_PCT
    if account is None or account.challenge_profit_target_pct is None:
        assumptions.append(f"No real account challenge_profit_target_pct was available — used the disclosed default of {DEFAULT_PROFIT_TARGET_PCT}%.")

    drawdown_limit_pct = account.trailing_drawdown_limit_pct if account is not None and account.trailing_drawdown_limit_pct is not None else DEFAULT_DRAWDOWN_LIMIT_PCT
    if account is None or account.trailing_drawdown_limit_pct is None:
        assumptions.append(f"No real account trailing_drawdown_limit_pct was available — used the disclosed default of {DEFAULT_DRAWDOWN_LIMIT_PCT}%.")

    if account is not None and account.challenge_duration_days is not None:
        max_trades = round(account.challenge_duration_days * ASSUMED_TRADES_PER_DAY)
    else:
        max_trades = DEFAULT_MAX_TRADES
        assumptions.append(f"No real account challenge_duration_days was available — used the disclosed default of {DEFAULT_MAX_TRADES} simulated trades as the time-expiry cap.")

    evaluation_cost = account.evaluation_cost if account is not None else None

    policies: list[EvaluationPolicySimulationResult] = []
    for policy_id, risk_pct in RISK_POLICY_PER_TRADE_PCT.items():
        policies.append(
            simulate_evaluation_policy(
                policy_id=policy_id,
                risk_per_trade_pct=risk_pct,
                win_rate=win_rate,
                avg_win_pct=avg_win_pct,
                avg_loss_pct=avg_loss_pct,
                profit_target_pct=profit_target_pct,
                drawdown_limit_pct=drawdown_limit_pct,
                max_trades=max_trades,
                evaluation_cost=evaluation_cost,
            )
        )

    limitations = [
        "Real per-regime sensitivity was not attempted: StrategyRegimeTestReport's buckets track avg_return_pct, not the win_rate/avg_win_pct/avg_loss_pct triplet this simulator needs, and this codebase has no real per-regime trade data to derive that triplet from honestly.",
        "Downstream funded-stage performance was not attempted: Piece 10a's Account.funded_stage_reached is a real, explicit CEO action, never linked to a simulated path — this report does not claim a simulated evaluation outcome predicts a real funded account's real future performance.",
        "This report does not declare a winning policy. Compare probabilityOfPassingPct, medianMaxDrawdownPct/worstCaseMaxDrawdownPct, expectedTradingDaysToPass, and riskAdjustedOutcome together — a faster policy with materially higher drawdown risk is not automatically better (Requirement 25).",
    ]

    if account is not None and account.trailing_drawdown_limit_pct is not None:
        boundary_risk_pct = round(account.trailing_drawdown_limit_pct * FAILURE_BOUNDARY_RISK_FRACTION, 3)
        policies.append(
            simulate_evaluation_policy(
                policy_id="failure_boundary_relative",
                risk_per_trade_pct=boundary_risk_pct,
                win_rate=win_rate,
                avg_win_pct=avg_win_pct,
                avg_loss_pct=avg_loss_pct,
                profit_target_pct=profit_target_pct,
                drawdown_limit_pct=drawdown_limit_pct,
                max_trades=max_trades,
                evaluation_cost=evaluation_cost,
            )
        )
    else:
        limitations.append(
            "NOT_TRACKABLE_YET: failure_boundary_relative policy — the account being compared against has no real trailing_drawdown_limit_pct configured, so there is no real boundary to size this policy's risk relative to."
        )

    return EvaluationPolicyComparisonReport(
        id=f"evalpolicy-{strategy.id}-{sim_day}",
        strategyId=strategy.id,
        strategyName=strategy.name,
        accountId=account.id if account is not None else None,
        sampleTradeCount=sample_trade_count,
        profitTargetPct=profit_target_pct,
        drawdownLimitPct=drawdown_limit_pct,
        maxTrades=max_trades,
        researchQuestion=RESEARCH_QUESTION,
        policies=policies,
        conclusion=(
            "Comparative evidence only — no policy is declared superior. Review each policy's real probability of "
            "passing alongside its real drawdown risk and expected speed before drawing any conclusion; a faster "
            "expected pass time at meaningfully higher drawdown/consecutive-loss-streak probability is evidence of "
            "elevated risk, not automatically a better policy (Requirement 25: speed is an objective to weigh, "
            "never a license to gamble)."
        ),
        assumptions=assumptions,
        limitations=limitations,
        simDay=sim_day,
        createdAt=_now_iso(),
    )
