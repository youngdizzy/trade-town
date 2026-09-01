"""app/portfolio_analyst.py — CEO directive "TradeTown — Phase 10: Real
Data + True Holdout + Portfolio Intelligence," Sections C/D (Portfolio
Analyst / Portfolio Risk Testing).

RESEARCH FIRST. This is a RESEARCH CANDIDATE cross-strategy analyst —
comparing multiple BACKTESTED (never live/paper) strategies against each
other, a domain `app/portfolio_intelligence.py` (LIVE/PAPER open
positions) and `app/strategy_tournament.py::_assess_pair_correlations()`
(walk-forward-window expectancy correlation, explicitly disclosed as NOT
a portfolio backtest) both come close to but do not cover — confirmed by
a real repo-wide recon: zero existing "combined drawdown across multiple
candidates" computation anywhere in this codebase before this module.

NEVER A SECOND BACKTEST ENGINE. Every real number below is either a
direct read of a candidate's own already-computed
`CompiledStrategyBacktestResult.trades` (the real per-trade sequence
already exposed for exactly this kind of reuse — see that field's own
docstring), or the output of an ALREADY-REAL, ALREADY-TESTED function
called on the concatenated real trade list of the candidates being
compared: `app/backtest_primitives.py::aggregate_bucket()` for combined
expectancy/drawdown/profit-factor, and
`app/adversarial_research.py::run_worst_period_attack()` for the
combined worst contiguous period. Correlation reuses
`app/portfolio_intelligence.py::pearson_correlation()` directly — the
same real function `strategy_tournament.py` already established as this
codebase's one authoritative correlation implementation.

THE "PAIRED DAY" METHODOLOGY, DISCLOSED. Two candidates' own real trades
happen at different timestamps (different entries), so their raw
per-trade R-multiple sequences cannot be directly index-aligned. This
module buckets each candidate's real closed trades by real calendar day
(UTC date of `entryTimestamp`) and sums `rMultipleRealized` per day —
the same real "paired-day" methodology
`app/performance_attribution.py::compute_strategy_live_correlation()`
already established for LIVE strategies, applied here to research
candidates' own backtested trades. Correlation is computed only over
days both candidates actually traded (real shared evidence), `None`
below `MIN_PAIRED_DAYS_FOR_CORRELATION` — never a fabricated `0.0`.

RESEARCH INFORMATION ONLY — NEVER A PROMOTION AUTHORITY. Nothing in this
module is imported by `app/champion_challenger.py`, `app/strategy_lab.py`'s
Certification/Hall-of-Fame functions, or any risk gate — proven by
`tests/test_portfolio_analyst.py::TestNeverAPromotionAuthority`'s own
real source-inspection test, the same discipline already applied to the
Research Council and the holdout module. `recommendation` is a real,
disclosed, priority-ordered classification over the real metrics above
— never a fabricated single "portfolio score."
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.adversarial_research import run_worst_period_attack
from app.backtest_primitives import aggregate_bucket
from app.portfolio_intelligence import pearson_correlation
from app.schemas import (
    EmaPullbackStatsBucket,
    EmaPullbackTradeRecord,
    FailureCode,
    PortfolioMarginalContribution,
    PortfolioPairCorrelation,
    PortfolioRecommendation,
    PortfolioResearchReport,
)

# Section C — real, disclosed, one-reasonable-convention thresholds
# (same honesty idiom every other per-module threshold in this codebase
# already uses — not derived from any formal study).
MIN_PAIRED_DAYS_FOR_CORRELATION = 10
MIN_COMBINED_TRADES_FOR_RECOMMENDATION = 60
HIGH_CORRELATION_THRESHOLD = 0.6
LOW_CORRELATION_THRESHOLD = 0.2
# Section D.1/C.15 — the worst STRESS_FRACTION of shared trading days
# (by combined daily return) define "under stress" for the real
# stress-correlation read.
STRESS_FRACTION = 0.2


def _daily_return_series(trades: list[EmaPullbackTradeRecord]) -> dict[str, float]:
    """Real, per-UTC-day sum of `rMultipleRealized` for closed trades —
    see this module's own docstring for why this is the real, disclosed
    "paired day" methodology."""
    buckets: dict[str, float] = {}
    for trade in trades:
        if trade.outcome == "open":
            continue
        date = trade.entry_timestamp[:10]
        buckets[date] = buckets.get(date, 0.0) + trade.r_multiple_realized
    return buckets


def compute_pair_correlation(candidate_id_a: str, trades_a: list[EmaPullbackTradeRecord], candidate_id_b: str, trades_b: list[EmaPullbackTradeRecord]) -> PortfolioPairCorrelation:
    """The one real pairwise correlation, plus a real "under stress"
    read (Section C.15/D.1): the SAME correlation, recomputed only over
    the worst `STRESS_FRACTION` of shared days by combined daily return
    — a real, disclosed proxy for "do these strategies move together
    specifically when things are bad," not merely on an average day."""
    daily_a = _daily_return_series(trades_a)
    daily_b = _daily_return_series(trades_b)
    shared_dates = sorted(set(daily_a) & set(daily_b))
    if len(shared_dates) < MIN_PAIRED_DAYS_FOR_CORRELATION:
        return PortfolioPairCorrelation(candidateIdA=candidate_id_a, candidateIdB=candidate_id_b, pairedDayCount=len(shared_dates), correlation=None, stressCorrelation=None)

    a_values = [daily_a[d] for d in shared_dates]
    b_values = [daily_b[d] for d in shared_dates]
    correlation = round(pearson_correlation(a_values, b_values), 4)

    combined_by_date = sorted(shared_dates, key=lambda d: daily_a[d] + daily_b[d])
    stress_count = max(MIN_PAIRED_DAYS_FOR_CORRELATION, round(len(shared_dates) * STRESS_FRACTION))
    stress_dates = combined_by_date[:stress_count]
    stress_correlation: float | None = None
    if len(stress_dates) >= MIN_PAIRED_DAYS_FOR_CORRELATION:
        stress_correlation = round(pearson_correlation([daily_a[d] for d in stress_dates], [daily_b[d] for d in stress_dates]), 4)

    return PortfolioPairCorrelation(candidateIdA=candidate_id_a, candidateIdB=candidate_id_b, pairedDayCount=len(shared_dates), correlation=correlation, stressCorrelation=stress_correlation)


def _detect_simultaneous_drawdown(candidate_trades: dict[str, list[EmaPullbackTradeRecord]]) -> bool:
    """Section D.2 — real detection of whether two or more candidates'
    OWN real worst contiguous period (`run_worst_period_attack()`,
    reused directly) overlaps in real chronological time. `True` only
    when at least one real pair's own worst-period windows genuinely
    intersect — never inferred from correlation alone."""
    windows: list[tuple[str, str]] = []
    for trades in candidate_trades.values():
        closed = [t for t in trades if t.outcome != "open"]
        result = run_worst_period_attack(closed)
        if result.window_start_timestamp is not None and result.window_end_timestamp is not None:
            windows.append((result.window_start_timestamp, result.window_end_timestamp))
    for i in range(len(windows)):
        for j in range(i + 1, len(windows)):
            a_start, a_end = windows[i]
            b_start, b_end = windows[j]
            if a_start <= b_end and b_start <= a_end:
                return True
    return False


def _marginal_contributions(candidate_trades: dict[str, list[EmaPullbackTradeRecord]], all_trades: list[EmaPullbackTradeRecord]) -> list[PortfolioMarginalContribution]:
    """Section D.5 — the real strategy-removal test."""
    with_bucket = aggregate_bucket("combined", all_trades)
    contributions: list[PortfolioMarginalContribution] = []
    for candidate_id, trades in candidate_trades.items():
        remaining = [t for t in all_trades if t not in trades]
        without_bucket = aggregate_bucket("without", remaining)
        contributions.append(
            PortfolioMarginalContribution(
                candidateId=candidate_id,
                expectancyRWith=with_bucket.expectancy_r,
                expectancyRWithout=without_bucket.expectancy_r,
                maxDrawdownRWith=with_bucket.max_drawdown_r,
                maxDrawdownRWithout=without_bucket.max_drawdown_r,
            )
        )
    return contributions


def _concentration_pct(candidate_trades: dict[str, list[EmaPullbackTradeRecord]]) -> float | None:
    """Section C.14 — the real share of combined POSITIVE return
    contributed by the single largest-contributing candidate. `None`
    when combined return is not positive (concentration of a loss is
    not a meaningful real percentage)."""
    totals = {cid: sum(t.r_multiple_realized for t in trades if t.outcome != "open") for cid, trades in candidate_trades.items()}
    positive_total = sum(v for v in totals.values() if v > 0)
    if positive_total <= 0:
        return None
    largest = max((v for v in totals.values() if v > 0), default=0.0)
    return round(largest / positive_total * 100, 1)


def _classify_recommendation(
    pair_correlations: list[PortfolioPairCorrelation], combined_bucket: EmaPullbackStatsBucket, individual_buckets: list[EmaPullbackStatsBucket], simultaneous_drawdown_detected: bool
) -> tuple[PortfolioRecommendation, str]:
    """Section C's one real, disclosed priority rule — never a
    fabricated single score. Checked in this fixed order:

    1. Not enough real combined evidence -> `insufficient_evidence`.
    2. Combined drawdown WORSE than every individual candidate's own
       drawdown (a real, direct sign of correlated tail risk) ->
       `portfolio_fragile`.
    3. High average real pairwise correlation -> `high_redundancy`.
    4. Low average real correlation AND combined drawdown no worse than
       the worst individual -> `portfolio_robust`.
    5. Low average real correlation alone -> `diversifying`.
    6. Otherwise -> `mixed`."""
    real_correlations = [pc.correlation for pc in pair_correlations if pc.correlation is not None]
    if not real_correlations or combined_bucket.trade_count < MIN_COMBINED_TRADES_FOR_RECOMMENDATION:
        return "insufficient_evidence", f"Only {combined_bucket.trade_count} real combined trades (or too few real paired days) — below the real {MIN_COMBINED_TRADES_FOR_RECOMMENDATION}-trade floor for a portfolio-level classification."

    avg_correlation = sum(real_correlations) / len(real_correlations)
    individual_drawdowns = [b.max_drawdown_r for b in individual_buckets if b.max_drawdown_r is not None]
    worst_individual_drawdown = min(individual_drawdowns) if individual_drawdowns else None

    if simultaneous_drawdown_detected and worst_individual_drawdown is not None and combined_bucket.max_drawdown_r is not None and combined_bucket.max_drawdown_r < worst_individual_drawdown:
        return "portfolio_fragile", f"Combined real drawdown {combined_bucket.max_drawdown_r}R is WORSE than the worst individual candidate's own {worst_individual_drawdown}R, and their own real worst-period windows overlap in time — correlated tail risk, not real diversification."
    if avg_correlation >= HIGH_CORRELATION_THRESHOLD:
        return "high_redundancy", f"Average real pairwise correlation {avg_correlation:.2f} across {len(real_correlations)} real candidate pair(s) — these candidates behave too similarly to count as independent bets."
    if avg_correlation <= LOW_CORRELATION_THRESHOLD and worst_individual_drawdown is not None and combined_bucket.max_drawdown_r is not None and combined_bucket.max_drawdown_r >= worst_individual_drawdown:
        return "portfolio_robust", f"Average real pairwise correlation {avg_correlation:.2f}, and combined real drawdown {combined_bucket.max_drawdown_r}R is no worse than the worst individual candidate's own {worst_individual_drawdown}R."
    if avg_correlation <= LOW_CORRELATION_THRESHOLD:
        return "diversifying", f"Average real pairwise correlation {avg_correlation:.2f} is low, though combined drawdown evidence is not yet conclusively better than the worst individual candidate."
    return "mixed", f"Average real pairwise correlation {avg_correlation:.2f} is neither clearly high nor low — evidence does not yet support a stronger classification."


def analyze_portfolio(candidate_trades: dict[str, list[EmaPullbackTradeRecord]], *, candidate_failure_codes: dict[str, list[FailureCode]], report_id: str) -> PortfolioResearchReport:
    """The one real entry point. `candidate_trades` maps a candidate id
    to its own real `CompiledStrategyBacktestResult.trades` (or
    `iteration.experiment.backtest.trades`); `candidate_failure_codes`
    maps a candidate id to its own real, already-diagnosed
    `FailureCode`s. Computes no new backtest math — every real number
    is either a direct read or a call to an already-real, already-tested
    function (see this module's own docstring)."""
    candidate_ids = sorted(candidate_trades.keys())
    generated_at = datetime.now(timezone.utc).isoformat()

    pair_correlations = [
        compute_pair_correlation(candidate_ids[i], candidate_trades[candidate_ids[i]], candidate_ids[j], candidate_trades[candidate_ids[j]])
        for i in range(len(candidate_ids))
        for j in range(i + 1, len(candidate_ids))
    ]

    all_trades = sorted((t for trades in candidate_trades.values() for t in trades), key=lambda t: t.entry_timestamp)
    combined_bucket = aggregate_bucket("combined", all_trades)
    worst_combined_period = run_worst_period_attack([t for t in all_trades if t.outcome != "open"])
    individual_buckets = [aggregate_bucket(cid, candidate_trades[cid]) for cid in candidate_ids]
    simultaneous_drawdown_detected = _detect_simultaneous_drawdown(candidate_trades)
    marginal_contributions = _marginal_contributions(candidate_trades, all_trades)
    concentration_pct = _concentration_pct(candidate_trades)

    shared_failure_modes: list[FailureCode] = []
    if candidate_failure_codes:
        code_sets = [set(codes) for codes in candidate_failure_codes.values()]
        shared = set.intersection(*code_sets) if code_sets else set()
        shared_failure_modes = sorted(shared)

    real_pair_count = sum(1 for pc in pair_correlations if pc.correlation is not None)
    if not pair_correlations:
        evidence_confidence: str = "low"
    elif real_pair_count == len(pair_correlations) and combined_bucket.trade_count >= MIN_COMBINED_TRADES_FOR_RECOMMENDATION * 2:
        evidence_confidence = "high"
    elif real_pair_count > 0:
        evidence_confidence = "medium"
    else:
        evidence_confidence = "low"

    recommendation, recommendation_reason = _classify_recommendation(pair_correlations, combined_bucket, individual_buckets, simultaneous_drawdown_detected)

    return PortfolioResearchReport(
        id=report_id,
        candidateIds=candidate_ids,
        pairCorrelations=pair_correlations,
        combinedBucket=combined_bucket,
        worstCombinedPeriod=worst_combined_period,
        marginalContributions=marginal_contributions,
        simultaneousDrawdownDetected=simultaneous_drawdown_detected,
        sharedFailureModes=shared_failure_modes,
        concentrationPct=concentration_pct,
        evidenceConfidence=evidence_confidence,  # type: ignore[arg-type]
        recommendation=recommendation,
        recommendationReason=recommendation_reason,
        generatedAt=generated_at,
    )
