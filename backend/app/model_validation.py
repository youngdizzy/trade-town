"""app/model_validation.py — Quantitative Research & Intelligence System,
Piece 4: the Model Validator (Meridian/CIO). Also houses Piece 2 (Walk-
Forward / Temporal-Split Validation), added as a sixth check inside the
same report rather than a standalone module — see THE TEMPORAL-
STABILITY CHECK section below for why.

THE ROLE, AS THE CEO SPECIFIED IT: a genuinely independent validation
authority for the Strategy Lab pipeline (app/sandbox.py, app/
strategy_lab.py) — not a second Risk Quant, not a second Gatekeeper, and
not a rename of an existing seat. "A model should not become an
approved production strategy merely because the Research Quant created
it." Meridian owns this sign-off. Vector (Chief Quantitative Strategist)
remains research; Sentinel/Guardian/Keystone remain risk; Meridian
(CIO) validates — that three-way separation is the point.

THE INDEPENDENCE THIS MODULE ACTUALLY CLAIMS: organizational/decision
independence, not statistical independence. Meridian does not re-derive
these numbers from a separate raw-data pipeline — none exists in this
codebase. Every check below reads the exact same real, already-computed
evidence Vector's research and the risk seats' own review also draw on
(the Monte Carlo bootstrap, the regime test, the liquidity validation,
the aggregated expectancy). What is real and independent is that
Meridian did not author the strategy or its risk read, and — via
`exclude_cio` below — does not simultaneously sit as that strategy's own
rotating Devil's Advocate for the same review cycle. Each
ModelValidationReport's own `data_sources_and_assumptions` field states
this plainly so the CEO can see exactly what was, and was not,
independently established.

THRESHOLD PROVENANCE: every numeric bar used below is a cited reuse of
an existing, already-load-bearing constant from app/strategy_lab.py's
own Certification gate (`compute_strategy_certification`/
`evaluate_certification_readiness`) — never a new number invented for
this module:
  - Sample size    -> CERTIFICATION_MIN_TRADE_COUNT (strategy_lab.py)
  - Regime breadth -> the exact "len(tested) >= 2 and not weak_buckets"
                       pattern strategy_lab.py's own certification
                       "regime_consistency" requirement already uses.
  - Tail risk      -> CERTIFICATION_MAX_RUIN_PCT (strategy_lab.py) — the
                       one ruin-related number in that file already used
                       as an actual pass/fail *gate* at the Certification
                       stage, not the softer 5.0/10.0 numbers used
                       elsewhere for Devil's Advocate/Company-Review
                       "concern" framing only.
  - Liquidity      -> no numeric threshold at all — reuses
                       StrategyLiquidityValidation.verdict as-is.
  - Expectancy     -> "expectancy > 0", the same formula and bar
                       strategy_lab.py's own certification/readiness
                       gates already use.
  - Temporal
    stability      -> two reused pieces, no new number: (1) "list order
                       = chronological order" — the same convention
                       strategy_lab.py's own compute_strategy_health()
                       already relies on for its recent-vs-lifetime read
                       (SimulationResult has no sim_day of its own; the
                       codebase already treats append order as time
                       order); (2) the same "expectancy > 0" bar above,
                       applied independently to each half of a
                       chronological split instead of once to the whole
                       sample.
If a future check ever needs a threshold with no existing numeric
precedent, it must be documented here as a configurable research
assumption, not presented as an established statistical fact. The
temporal-stability check above is the one exception worth naming
explicitly: its *shape* (splitting a strategy's own run history into an
earlier and later half) has no prior precedent to reuse — see THE
TEMPORAL-STABILITY CHECK section below for the honest boundary this
requires.

THE TEMPORAL-STABILITY CHECK (Piece 2 — Walk-Forward / Temporal-Split
Validation): a genuine walk-forward test needs real, sequential,
unseen-at-the-time historical price data to hold out a true
out-of-sample window — app/simulation.py's own module docstring already
discloses this codebase has no real historical MarketDataProvider, so
that cannot be honestly built here. What *can* be built honestly: this
strategy's own real `SimulationResult` history, split at its
chronological midpoint (earlier half vs. later half, by list order —
see above), checking whether real expectancy holds positive in *both*
halves rather than only in the whole-sample average. This surfaces a
real, different failure mode than `_expectancy_check` above: a strategy
whose early results were strong but whose more recent results have
turned negative (or vice versa — an unproven recent turnaround) can
still average out to a positive whole-sample expectancy that
`_expectancy_check` alone would pass. This is a disjoint-split analog to
walk-forward validation, not a claim of true sequential in-sample/
out-of-sample testing against unseen future data — the check's own
`reasoning` string says so.

LIFECYCLE / STATELESSNESS: `generate_strategy_review()` (app/sandbox.py)
has exactly one real call site in this codebase —
NexusManager.request_strategy_company_review() in app/state.py — which
computes `existing_review_count` fresh, per-strategy, inside one
lock-guarded action and appends the result immutably. A "validation
cycle" is exactly one such call. generate_model_validation_report()
below is a pure function of its arguments: nothing here is cached or
mutated, so DA-exclusion (passed through to
app/sandbox.py's generate_strategy_review(exclude_cio=True) at that same
call site) can never leak state across strategies, persist past the
call that set it, or shift the base Devil's Advocate rotation formula.

ADVISORY-ONLY: nothing in app/sandbox.py's apply_review_decision()/
begin_company_review() control flow reads ModelValidationReport.verdict.
This module produces a real, honest, four-state read for CEO visibility
— it does not gate Company Review, the Gatekeeper, Risk Authority, or
any Circuit Breaker. Promotion to a blocking gate is a documented future
decision (see this piece's Design Bible section), never a hardcoded
timer.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import (
    ModelValidationCheck,
    ModelValidationReport,
    ModelValidationVerdict,
    SimulationResult,
    Strategy,
    StrategyLiquidityValidation,
    StrategyMonteCarloResult,
    StrategyRegimeTestReport,
)
from app.strategy_lab import (
    CERTIFICATION_MAX_RUIN_PCT,
    CERTIFICATION_MIN_TRADE_COUNT,
)

MAX_STRATEGY_MODEL_VALIDATIONS = 30


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sample_size_check(strategy_results: list[SimulationResult]) -> ModelValidationCheck:
    trade_count = sum(r.trade_count for r in strategy_results)
    passed = trade_count >= CERTIFICATION_MIN_TRADE_COUNT if strategy_results else None
    return ModelValidationCheck(
        id="sample_size",
        label="Minimum Validated Trade Sample Size",
        passed=passed,
        evidence=f"{trade_count} real trade(s) across {len(strategy_results)} real run(s) on file." if strategy_results else "No real SimulationResults on file for this strategy yet.",
        reasoning=f"Needs ≥{CERTIFICATION_MIN_TRADE_COUNT} real trades before Meridian will trust the sample size — the same bar the Strategy Lab's own Certification gate already enforces." if strategy_results else "Cannot evaluate sample size with zero real runs on file.",
        thresholdSource="app/strategy_lab.py CERTIFICATION_MIN_TRADE_COUNT (reused, not new)",
    )


def _regime_breadth_check(regime_test: StrategyRegimeTestReport | None) -> ModelValidationCheck:
    if regime_test is None:
        return ModelValidationCheck(
            id="regime_breadth",
            label="Consistent Profitability Across Multiple Market Regimes",
            passed=None,
            evidence="No real Market Regime Testing on file yet for this strategy.",
            reasoning="Cannot evaluate regime breadth without a real StrategyRegimeTestReport.",
            thresholdSource="app/strategy_lab.py's certification 'regime_consistency' requirement (reused, not new)",
        )
    tested = [b for b in regime_test.buckets if b.tested]
    weak = [b for b in tested if b.verdict == "weak"]
    passed = len(tested) >= 2 and not weak
    return ModelValidationCheck(
        id="regime_breadth",
        label="Consistent Profitability Across Multiple Market Regimes",
        passed=passed,
        evidence=f"Tested across {len(tested)} real Testing Environment(s){', ' + str(len(weak)) + ' weak' if weak else ''}.",
        reasoning="Needs ≥2 real tested regimes with no weak bucket — a single favorable window is not evidence of robustness." if not passed else "Tested across multiple real regimes with no weak performance on file.",
        thresholdSource="app/strategy_lab.py's certification 'regime_consistency' requirement: len(tested) >= 2 and not weak_buckets (reused, not new)",
    )


def _tail_risk_check(monte_carlo: StrategyMonteCarloResult | None) -> ModelValidationCheck:
    if monte_carlo is None:
        return ModelValidationCheck(
            id="tail_risk",
            label="Acceptable Tail Risk (Monte Carlo Probability of Ruin)",
            passed=None,
            evidence="No real Monte Carlo bootstrap on file yet for this strategy.",
            reasoning="Cannot evaluate tail risk without a real StrategyMonteCarloResult.",
            thresholdSource="app/strategy_lab.py CERTIFICATION_MAX_RUIN_PCT (reused, not new)",
        )
    passed = monte_carlo.probability_of_ruin_pct <= CERTIFICATION_MAX_RUIN_PCT
    return ModelValidationCheck(
        id="tail_risk",
        label="Acceptable Tail Risk (Monte Carlo Probability of Ruin)",
        passed=passed,
        evidence=f"Real probability of ruin {monte_carlo.probability_of_ruin_pct:.1f}% across {monte_carlo.paths_simulated} real simulated paths (needs ≤{CERTIFICATION_MAX_RUIN_PCT:.0f}%).",
        reasoning="Within the same real ruin-probability bar the Strategy Lab's own Certification gate enforces." if passed else "Exceeds the Certification gate's own real ruin-probability bar — real ruin risk at this position size.",
        thresholdSource="app/strategy_lab.py CERTIFICATION_MAX_RUIN_PCT (reused, not new)",
    )


def _liquidity_check(liquidity: StrategyLiquidityValidation | None) -> ModelValidationCheck:
    if liquidity is None:
        return ModelValidationCheck(
            id="liquidity_realism",
            label="Liquidity Conditions Support This Strategy's Watched Symbols",
            passed=None,
            evidence="No real liquidity validation on file yet for this strategy.",
            reasoning="Cannot evaluate liquidity realism without a real StrategyLiquidityValidation.",
            thresholdSource="No new threshold — reuses StrategyLiquidityValidation.verdict as-is",
        )
    passed = liquidity.verdict != "unfavorable"
    return ModelValidationCheck(
        id="liquidity_realism",
        label="Liquidity Conditions Support This Strategy's Watched Symbols",
        passed=passed,
        evidence=f"Real liquidity verdict: {liquidity.verdict} ({liquidity.detail})",
        reasoning="Reuses Feature 51's real liquidity/market-structure read as-is — no new number invented." if passed else "The strategy's own watched-symbol liquidity read is unfavorable — real execution conditions may not support this strategy as modeled.",
        thresholdSource="No new threshold — reuses StrategyLiquidityValidation.verdict as-is",
    )


def _expectancy_check(strategy_results: list[SimulationResult]) -> ModelValidationCheck:
    if not strategy_results:
        return ModelValidationCheck(
            id="expectancy",
            label="Positive Expectancy Over A Real Sample",
            passed=None,
            evidence="No real runs on file yet.",
            reasoning="Cannot evaluate expectancy with zero real runs on file.",
            thresholdSource="app/strategy_lab.py's certification 'expectancy' requirement: expectancy > 0 (reused, not new)",
        )
    expectancy = sum(r.expected_value_pct for r in strategy_results) / len(strategy_results)
    passed = expectancy > 0
    return ModelValidationCheck(
        id="expectancy",
        label="Positive Expectancy Over A Real Sample",
        passed=passed,
        evidence=f"Real expected value {expectancy:+.2f}% per trade across {len(strategy_results)} real run(s).",
        reasoning="Positive real expectancy across the strategy's own real runs." if passed else "Real expectancy is not positive — the same bar the Strategy Lab's own Certification gate enforces.",
        thresholdSource="app/strategy_lab.py's certification 'expectancy' requirement: expectancy > 0 (reused, not new)",
    )


def _temporal_stability_check(strategy_results: list[SimulationResult]) -> ModelValidationCheck:
    """Piece 2 — Walk-Forward / Temporal-Split Validation, as an honest
    analog (see the module docstring's THE TEMPORAL-STABILITY CHECK
    section): splits `strategy_results` at its chronological midpoint —
    by list order, the same convention app/strategy_lab.py's
    compute_strategy_health() already relies on — and checks that real
    expectancy holds positive in both the earlier and later half, not
    just in the whole-sample average."""
    if len(strategy_results) < 2:
        return ModelValidationCheck(
            id="temporal_stability",
            label="Edge Stability Across This Strategy's Own Run History (Walk-Forward Analog)",
            passed=None,
            evidence=f"Only {len(strategy_results)} real run(s) on file — at least 2 are needed to split into an earlier and later half.",
            reasoning="Cannot evaluate temporal stability without at least two real completed runs to compare chronologically.",
            thresholdSource="app/strategy_lab.py's own 'list order = chronological order' convention for SimulationResult, already used by compute_strategy_health() (reused, not new)",
        )
    midpoint = len(strategy_results) // 2
    earlier = strategy_results[:midpoint]
    later = strategy_results[midpoint:]
    earlier_trade_count = sum(r.trade_count for r in earlier)
    later_trade_count = sum(r.trade_count for r in later)
    if earlier_trade_count < CERTIFICATION_MIN_TRADE_COUNT or later_trade_count < CERTIFICATION_MIN_TRADE_COUNT:
        return ModelValidationCheck(
            id="temporal_stability",
            label="Edge Stability Across This Strategy's Own Run History (Walk-Forward Analog)",
            passed=None,
            evidence=f"Earlier half: {earlier_trade_count} real trade(s) across {len(earlier)} run(s). Later half: {later_trade_count} real trade(s) across {len(later)} run(s).",
            reasoning=f"Each half needs ≥{CERTIFICATION_MIN_TRADE_COUNT} real trades (the same Certification-gate sample-size bar) before a chronological split is statistically meaningful.",
            thresholdSource="app/strategy_lab.py CERTIFICATION_MIN_TRADE_COUNT, applied independently to each half (reused, not new)",
        )
    earlier_expectancy = sum(r.expected_value_pct for r in earlier) / len(earlier)
    later_expectancy = sum(r.expected_value_pct for r in later) / len(later)
    passed = earlier_expectancy > 0 and later_expectancy > 0
    return ModelValidationCheck(
        id="temporal_stability",
        label="Edge Stability Across This Strategy's Own Run History (Walk-Forward Analog)",
        passed=passed,
        evidence=f"Earlier-half expectancy {earlier_expectancy:+.2f}% per trade ({len(earlier)} run(s)); later-half expectancy {later_expectancy:+.2f}% per trade ({len(later)} run(s)).",
        reasoning=(
            "The real edge holds in both the earlier and later half of this strategy's own tested history — not just an early lucky stretch or an unproven recent turnaround. A disjoint-split analog to walk-forward validation, not a claim of true out-of-sample testing against unseen future data."
            if passed
            else "The real edge does not hold across both halves of this strategy's own tested history — a whole-sample average can mask a strategy that only worked early on, or only recently."
        ),
        thresholdSource="app/strategy_lab.py's certification 'expectancy' requirement: expectancy > 0, applied independently to each half (reused, not new)",
    )


def _compute_verdict(checks: list[ModelValidationCheck], strategy_results: list[SimulationResult]) -> ModelValidationVerdict:
    if not strategy_results:
        return "not_validatable"
    evaluated = [c for c in checks if c.passed is not None]
    if not evaluated:
        return "not_validatable"
    if any(c.passed is None for c in checks):
        # A clear failure among the checks we *could* evaluate is still a
        # real rejection even if other checks remain unevaluated — missing
        # evidence never launders a real, already-established failure.
        if any(c.passed is False for c in evaluated):
            return "rejected"
        return "needs_more_evidence"
    if all(c.passed for c in checks):
        return "approved"
    return "rejected"


def generate_model_validation_report(
    strategy: Strategy,
    results: list[SimulationResult],
    monte_carlo: StrategyMonteCarloResult | None,
    regime_test: StrategyRegimeTestReport | None,
    liquidity: StrategyLiquidityValidation | None,
    review_id: str,
    existing_review_count: int,
    *,
    sim_day: int,
) -> ModelValidationReport:
    strategy_results = [r for r in results if r.strategy_id == strategy.id]
    checks = [
        _sample_size_check(strategy_results),
        _regime_breadth_check(regime_test),
        _tail_risk_check(monte_carlo),
        _liquidity_check(liquidity),
        _expectancy_check(strategy_results),
        _temporal_stability_check(strategy_results),
    ]
    verdict = _compute_verdict(checks, strategy_results)
    passed_count = sum(1 for c in checks if c.passed is True)
    failed_count = sum(1 for c in checks if c.passed is False)
    not_evaluable_count = sum(1 for c in checks if c.passed is None)
    evidence_summary = f"{passed_count} of {len(checks)} real checks passed, {failed_count} failed, {not_evaluable_count} not yet evaluable — verdict: {verdict}."
    data_sources_and_assumptions = [
        "This report reuses already-computed evidence (Monte Carlo bootstrap, regime test, liquidity validation, real trade/expectancy history) rather than re-deriving statistics from raw data — no separate raw-data pipeline exists in this codebase.",
        "Every numeric threshold used is a cited reuse of an existing Strategy Lab Certification-gate constant; see each check's own thresholdSource.",
        "Independence here is organizational/decision independence (Meridian did not author this strategy's research or risk read, and is excluded from serving as this same cycle's Devil's Advocate) — not a claim of statistical independence from the underlying data.",
        "Advisory-only: this verdict does not gate Company Review, the Gatekeeper, Risk Authority, or any Circuit Breaker.",
    ]
    return ModelValidationReport(
        id=f"model-validation-{strategy.id}-{existing_review_count}",
        strategyId=strategy.id,
        strategyName=strategy.name,
        reviewId=review_id,
        existingReviewCount=existing_review_count,
        verdict=verdict,
        checks=checks,
        validatorAgentId="cio",
        evidenceSummary=evidence_summary,
        dataSourcesAndAssumptions=data_sources_and_assumptions,
        simDay=sim_day,
        createdAt=_now_iso(),
    )


def cap_strategy_model_validations(items: list[ModelValidationReport]) -> list[ModelValidationReport]:
    if len(items) > MAX_STRATEGY_MODEL_VALIDATIONS:
        del items[: len(items) - MAX_STRATEGY_MODEL_VALIDATIONS]
    return items
