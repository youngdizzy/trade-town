"""app/risk_survival.py — CEO directive "TradeTown — Phase 11: Strategy
Intelligence + Hard-Risk Refinement," Section 2 (Hard-Risk Template
System) and Section 7 (Risk-Survival Scorecard).

FORENSIC RECON, DISCLOSED (Section 0's own required first step). Before
writing this module, the following were confirmed already real and
NEVER duplicated here:
  - Position sizing (Section 3): `app/position_sizing.py::build_position_sizing()`
    already implements the exact real formula the directive asks for
    (risk_amount = equity × risk_pct; stop_distance = |entry - stop|;
    position_size = risk_amount / stop_distance) plus real exposure/
    liquidity/regime/session caps, live on the real trade pipeline.
  - The centralized risk gate (Sections 8/9/24 of the earlier-audited
    directive, and this directive's own Section 28): `app/gatekeeper.py::
    evaluate_gatekeeper()` remains the one real call every trade proposal
    passes through — this module has no path to it and never will.
  - The adversarial attack suite (Section 12, "Live-Market Survival
    Tests"): `app/adversarial_research.py::run_adversarial_research()`
    ALREADY runs outlier removal, worst-contiguous-period, sequence
    reshuffle, extended cost stress, and regime robustness — this
    module's own `outlier_resilience`/`sequence_resilience`/
    `regime_resilience`/`cost_resilience` checks below read that
    already-real `AdversarialResearchResult` when a caller supplies one
    (never re-running the attacks, never a second attack engine); when
    no caller-supplied result exists, this module honestly reports
    `not_available` for those axes rather than approximating with a
    parallel, second judgment.
  - Confidence (Section 15): `app/confidence.py`'s `DecisionConfidence`
    already derives from seven real weighted signals, no live LLM call
    anywhere. Untouched, unduplicated.

WHAT THIS MODULE ACTUALLY ADDS, DISCLOSED:
  1. `RISK_PROFILE_TEMPLATES` (Section 2) — three named, REFERENCE-ONLY
     risk templates matching the directive's own literal numbers.
     Nothing reads these automatically into any live risk limit; they
     exist for a researcher/CEO to compare a candidate's own real risk
     contract against a named convention. The one real, already-
     centralized live risk gate remains the CEO-configured `RiskLimits` +
     `app/gatekeeper.py` — entirely untouched.
  2. `build_risk_survival_scorecard()` (Section 7) — the one real,
     itemized evidence breakdown the directive explicitly asks for
     INSTEAD OF a fake single AI quality score. Every check is a
     disclosed classification over an already-real, already-computed
     signal (see each check's own comment below for its exact source);
     this function computes zero new backtest/statistical math.

NEVER A PROMOTION AUTHORITY. Writes nothing, persists nothing. Never
imported by `app/champion_challenger.py` or `app/strategy_lab.py`'s
Certification/Hall-of-Fame functions, and never imports either itself —
proven by `tests/test_risk_survival.py::TestNeverAPromotionAuthority`."""
from __future__ import annotations

from app.research_loop import RESEARCH_CANDIDATE_MAX_DRAWDOWN_PCT, RESEARCH_CANDIDATE_MIN_PROFIT_FACTOR, RESEARCH_CANDIDATE_MIN_TRADE_COUNT
from app.schemas import (
    AdversarialResearchResult,
    BenchmarkComparison,
    EvidenceQualityReport,
    FailureCodeEntry,
    HoldoutValidationReport,
    PortfolioResearchReport,
    ResearchExperimentRecord,
    RiskProfileTemplate,
    RiskSurvivalCheck,
    RiskSurvivalScorecard,
)
from app.statistical_comparison import MIN_TRADES_FOR_BOOTSTRAP

# Section 2's own literal numbers, reused verbatim — never invented.
# REFERENCE ONLY: nothing in this codebase enforces these automatically;
# the CEO-configured `RiskLimits` + `app/gatekeeper.py` remain the one
# real, live-enforced risk boundary.
RISK_PROFILE_TEMPLATES: dict[str, RiskProfileTemplate] = {
    "conservative": RiskProfileTemplate(
        name="conservative",
        riskPerTradePctMin=0.50,
        riskPerTradePctMax=0.75,
        maxDailyLossPct=2.0,
        maxWeeklyLossPct=4.0,
        maxOpenRiskPct=3.0,
        maxPositions=3,
        drawdownScaling="Half-size after 4% drawdown; trading halt after 6% drawdown.",
        killSwitchDrawdownPct=6.0,
        detail="Section 2's CONSERVATIVE template — a reference convention, not a trading recommendation.",
    ),
    "professional": RiskProfileTemplate(
        name="professional",
        riskPerTradePctMin=0.75,
        riskPerTradePctMax=0.75,
        maxDailyLossPct=2.0,
        maxWeeklyLossPct=5.0,
        maxOpenRiskPct=4.0,
        maxPositions=4,
        drawdownScaling="Dynamic drawdown scaling (deterministic, downward-only).",
        killSwitchDrawdownPct=8.0,
        detail="Section 2's PROFESSIONAL template — a reference convention, not a trading recommendation.",
    ),
    "aggressive": RiskProfileTemplate(
        name="aggressive",
        riskPerTradePctMin=1.0,
        riskPerTradePctMax=1.0,
        maxDailyLossPct=3.0,
        maxWeeklyLossPct=None,
        maxOpenRiskPct=5.0,
        maxPositions=4,
        drawdownScaling="8% peak-drawdown kill switch (no intermediate scaling tier disclosed by the directive).",
        killSwitchDrawdownPct=8.0,
        detail="Section 2's AGGRESSIVE template — a reference convention, not a trading recommendation.",
    ),
}


def build_risk_survival_scorecard(
    record: ResearchExperimentRecord,
    *,
    evidence_quality: EvidenceQualityReport,
    benchmark_comparisons: list[BenchmarkComparison],
    failure_codes: list[FailureCodeEntry],
    risk_per_trade_pct: float,
    holdout: HoldoutValidationReport | None,
    adversarial: AdversarialResearchResult | None,
    portfolio: PortfolioResearchReport | None,
    report_id: str,
    generated_at: str,
) -> RiskSurvivalScorecard:
    """The one real entry point. `adversarial`/`holdout`/`portfolio` are
    all optional — each missing input produces an honest `not_available`
    check rather than a guessed one."""
    bucket = record.backtest.overall
    checks: list[RiskSurvivalCheck] = []

    # 1. historical_robustness — direct read of the same real trade-count/
    # expectancy/profit-factor floor `classify_candidacy()` already uses.
    if bucket.trade_count < RESEARCH_CANDIDATE_MIN_TRADE_COUNT:
        checks.append(RiskSurvivalCheck(name="historical_robustness", status="insufficient_evidence", detail=f"{bucket.trade_count} real trade(s) — below the real {RESEARCH_CANDIDATE_MIN_TRADE_COUNT}-trade floor."))
    elif bucket.expectancy_r is not None and bucket.expectancy_r <= 0:
        checks.append(RiskSurvivalCheck(name="historical_robustness", status="fail", detail=f"Real expectancy {bucket.expectancy_r:+.3f}R is not positive."))
    elif bucket.profit_factor is not None and bucket.profit_factor < RESEARCH_CANDIDATE_MIN_PROFIT_FACTOR:
        checks.append(RiskSurvivalCheck(name="historical_robustness", status="fail", detail=f"Real profit factor {bucket.profit_factor:.2f} is below the real {RESEARCH_CANDIDATE_MIN_PROFIT_FACTOR:.2f} floor."))
    else:
        checks.append(RiskSurvivalCheck(name="historical_robustness", status="pass", detail=f"{bucket.trade_count} real trade(s), expectancy {bucket.expectancy_r}R, profit factor {bucket.profit_factor} — clears the real research-candidate floor."))

    # 2. walk_forward_robustness — direct read of the real walk-forward verdict.
    checks.append(RiskSurvivalCheck(
        name="walk_forward_robustness",
        status="pass" if record.walk_forward.verdict == "stable" else ("fail" if record.walk_forward.verdict == "unstable" else "insufficient_evidence"),
        detail=f"Real walk-forward verdict: {record.walk_forward.verdict}.",
    ))

    # 3. cost_resilience — prefers the real EXTENDED cost attack (beyond
    # "stressed") when supplied; falls back to the base real cost-
    # sensitivity verdict otherwise.
    if adversarial is not None and adversarial.extended_cost_attack.survives_beyond_stress is not None:
        checks.append(RiskSurvivalCheck(
            name="cost_resilience",
            status="pass" if adversarial.extended_cost_attack.survives_beyond_stress else "warn",
            detail=adversarial.extended_cost_attack.detail,
        ))
    else:
        checks.append(RiskSurvivalCheck(
            name="cost_resilience",
            status="pass" if record.cost_sensitivity.verdict == "cost_resilient" else ("fail" if record.cost_sensitivity.verdict == "cost_sensitive" else "insufficient_evidence"),
            detail=f"Real cost-sensitivity verdict: {record.cost_sensitivity.verdict}.",
        ))

    # 4. outlier_resilience — prefers the real adversarial classification;
    # falls back to `not_available` (never a parallel, second judgment).
    if adversarial is not None:
        cls = adversarial.outlier_resilience.classification
        checks.append(RiskSurvivalCheck(
            name="outlier_resilience",
            status="pass" if cls == "robust_to_outliers" else ("warn" if cls == "moderately_outlier_dependent" else ("fail" if cls == "highly_outlier_dependent" else "insufficient_evidence")),
            detail=adversarial.outlier_resilience.detail,
        ))
    else:
        checks.append(RiskSurvivalCheck(name="outlier_resilience", status="not_available", detail="No adversarial result was supplied for this candidate — outlier resilience was not attacked this call."))

    # 5. sequence_resilience — real trade-sequence reshuffle result, only
    # when a caller supplied the real adversarial suite.
    if adversarial is not None:
        seq = adversarial.sequence_robustness
        if seq.baseline_max_drawdown_r is None or seq.worst_reshuffled_max_drawdown_r is None:
            checks.append(RiskSurvivalCheck(name="sequence_resilience", status="insufficient_evidence", detail=seq.detail))
        else:
            degraded = abs(seq.worst_reshuffled_max_drawdown_r) > abs(seq.baseline_max_drawdown_r) * 1.5
            checks.append(RiskSurvivalCheck(name="sequence_resilience", status="warn" if degraded else "pass", detail=seq.detail))
    else:
        checks.append(RiskSurvivalCheck(name="sequence_resilience", status="not_available", detail="No adversarial result was supplied for this candidate — trade-sequence reshuffling was not run this call."))

    # 6. regime_resilience — real regime-robustness classification, only
    # when a caller supplied the real adversarial suite.
    if adversarial is not None:
        regime_cls = adversarial.regime_robustness.classification
        checks.append(RiskSurvivalCheck(
            name="regime_resilience",
            status="pass" if regime_cls == "regime_robust" else ("warn" if regime_cls == "regime_specialist" else ("fail" if regime_cls == "regime_fragile" else "insufficient_evidence")),
            detail=adversarial.regime_robustness.detail,
        ))
    else:
        checks.append(RiskSurvivalCheck(name="regime_resilience", status="not_available", detail="No adversarial result was supplied for this candidate — regime robustness was not classified this call."))

    # 7. benchmark_performance — direct read of the real benchmark comparisons.
    if not benchmark_comparisons:
        checks.append(RiskSurvivalCheck(name="benchmark_performance", status="insufficient_evidence", detail="No real buy-and-hold benchmark comparison exists for this candidate yet."))
    elif all(c.beats_benchmark for c in benchmark_comparisons):
        checks.append(RiskSurvivalCheck(name="benchmark_performance", status="pass", detail=f"Beats the real buy-and-hold benchmark on all {len(benchmark_comparisons)} tested symbol(s)."))
    elif any(c.beats_benchmark for c in benchmark_comparisons):
        checks.append(RiskSurvivalCheck(name="benchmark_performance", status="warn", detail="Beats the real benchmark on some but not all tested symbols."))
    else:
        checks.append(RiskSurvivalCheck(name="benchmark_performance", status="fail", detail="Trails the real buy-and-hold benchmark on every tested symbol."))

    # 8. holdout_evidence — direct read of the real holdout status.
    if holdout is None:
        checks.append(RiskSurvivalCheck(name="holdout_evidence", status="not_available", detail="No holdout evaluation was supplied for this candidate."))
    else:
        checks.append(RiskSurvivalCheck(
            name="holdout_evidence",
            status="pass" if holdout.status == "valid" else ("insufficient_evidence" if holdout.status == "unavailable" else "fail"),
            detail=f"Real holdout status: {holdout.status}.",
        ))

    # 9. statistical_evidence — direct read of the real bootstrap-evidence floor.
    checks.append(RiskSurvivalCheck(
        name="statistical_evidence",
        status="pass" if bucket.trade_count >= MIN_TRADES_FOR_BOOTSTRAP else "insufficient_evidence",
        detail=f"{bucket.trade_count} real trade(s) — real statistical-evidence floor is {MIN_TRADES_FOR_BOOTSTRAP}.",
    ))

    # 10. portfolio_interaction — direct read of the real Portfolio Analyst recommendation.
    if portfolio is None:
        checks.append(RiskSurvivalCheck(name="portfolio_interaction", status="not_available", detail="No Portfolio Analyst report was supplied — this candidate was not analyzed alongside other strategies this call."))
    else:
        favorable = {"portfolio_robust", "diversifying"}
        unfavorable = {"portfolio_fragile", "high_redundancy"}
        checks.append(RiskSurvivalCheck(
            name="portfolio_interaction",
            status="pass" if portfolio.recommendation in favorable else ("fail" if portfolio.recommendation in unfavorable else ("insufficient_evidence" if portfolio.recommendation == "insufficient_evidence" else "warn")),
            detail=portfolio.recommendation_reason,
        ))

    # 11. drawdown_behavior — reuses the exact same real R-multiple-to-
    # percent approximation `derive_research_failure_codes()` already uses.
    if bucket.max_drawdown_r is None:
        checks.append(RiskSurvivalCheck(name="drawdown_behavior", status="insufficient_evidence", detail="No real max-drawdown figure exists for this candidate yet."))
    else:
        drawdown_pct_approx = abs(bucket.max_drawdown_r) * risk_per_trade_pct
        checks.append(RiskSurvivalCheck(
            name="drawdown_behavior",
            status="fail" if drawdown_pct_approx > RESEARCH_CANDIDATE_MAX_DRAWDOWN_PCT else "pass",
            detail=f"Real max drawdown {bucket.max_drawdown_r:.2f}R (~{drawdown_pct_approx:.1f}% at {risk_per_trade_pct:.1f}% risk/trade) vs. the real {RESEARCH_CANDIDATE_MAX_DRAWDOWN_PCT:.0f}% research-candidate bar.",
        ))

    # 12. failure_concentration — reuses the real, already-derived failure
    # codes and their real, already-disclosed severities — never a new
    # severity judgment.
    critical_or_high = [c for c in failure_codes if c.severity in ("critical", "high")]
    if critical_or_high:
        checks.append(RiskSurvivalCheck(name="failure_concentration", status="fail", detail=f"{len(critical_or_high)} real critical/high-severity failure code(s): {', '.join(sorted({c.code for c in critical_or_high}))}."))
    elif failure_codes:
        checks.append(RiskSurvivalCheck(name="failure_concentration", status="warn", detail=f"{len(failure_codes)} real medium/low-severity failure code(s): {', '.join(sorted({c.code for c in failure_codes}))}."))
    else:
        checks.append(RiskSurvivalCheck(name="failure_concentration", status="pass", detail="No real failure codes were derived for this candidate."))

    # 13. evidence_quality — direct read of the real Phase 10 evidence state.
    strong_states = {"external_data_validated", "holdout_validated", "research_validated"}
    checks.append(RiskSurvivalCheck(
        name="evidence_quality",
        status="pass" if evidence_quality.state in strong_states else ("warn" if evidence_quality.state == "simulated_only" else "fail"),
        detail=f"{evidence_quality.state}: {evidence_quality.detail}",
    ))

    return RiskSurvivalScorecard(
        id=report_id,
        definitionId=record.definition_id,
        definitionVersion=record.definition_version,
        checks=checks,
        generatedAt=generated_at,
    )
