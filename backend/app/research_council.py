"""app/research_council.py — CEO directive "TradeTown — Phase 9: Full
Autonomous Quant Research Factory," Phases 14-15 (Research Roles /
Research Council).

NO LLM, NO PERSONAS, NO INVENTED OPINIONS. This codebase runs no LLM at
runtime anywhere (see app/strategy_compiler.py's own module docstring
and app/debate.py/app/foundational_mentors.py's same discipline). A
"role" below is a deterministic Python function reading fields an
already-real, already-computed `ResearchLoopIterationRecord`/
`AdversarialResearchResult`/`StrategyComplexityScore` already carries —
never a second opinion invented on top of the same evidence, and never
a role disagreeing with the numbers it was just handed. Each
`ResearchCouncilFinding.evidence_references` names the exact real
field(s) that produced its `finding` text, so every claim is traceable
back to a number that already exists elsewhere in this same record.

WHY SEVEN ROLES, NOT EIGHT. The directive's own Phase 14 list includes
PORTFOLIO_ANALYST — but a single candidate's own iteration record
carries no real cross-strategy/portfolio-level evidence (that lives in
app/portfolio_intelligence.py, over live/paper positions this research
candidate has none of yet). Inventing a portfolio finding from data
this record doesn't have would be fabrication, not evidence-routing —
disclosed, not silently dropped: PORTFOLIO_ANALYST is NOT IMPLEMENTED
here for exactly that reason.

THE AGGREGATE RECOMMENDATION, DISCLOSED AND NEVER A GATE. `recommendation`
(CONTINUE/MUTATE/RETEST/ARCHIVE/INSUFFICIENT_EVIDENCE) is derived by one
fixed, real priority rule over the SAME `candidacy`/`scorecard`/
adversarial evidence `classify_candidacy()` and
`classify_research_scorecard()` already computed — this function makes
no new pass/fail judgment of its own, it only re-labels an
already-decided outcome into the directive's own requested vocabulary
for a human/agent reader. It is advisory-only: never imported by
`classify_candidacy()`, Champion/Challenger, Certification, or
Hall-of-Fame (see tests/test_research_council.py's own source-shape
proof), matching this codebase's own established `StrategyComplexityScore`/
`OverfittingDiagnosis` precedent — real, useful, structured evidence
that never becomes a second, competing gate.
"""
from __future__ import annotations

from typing import Literal

from app.schemas import (
    AdversarialResearchResult,
    ResearchCouncilFinding,
    ResearchCouncilRecommendation,
    ResearchCouncilReport,
    ResearchLoopIterationRecord,
)

# Mirrors app/research_loop.py's own RESEARCH_CANDIDATE_MIN_TRADE_COUNT
# — imported, never re-derived, so the Statistician's confidence read
# can never silently drift from the real gate it is describing.
from app.research_loop import RESEARCH_CANDIDATE_MIN_TRADE_COUNT


def _researcher_finding(iteration: ResearchLoopIterationRecord) -> ResearchCouncilFinding:
    return ResearchCouncilFinding(
        role="researcher",
        finding=f"Hypothesis: {iteration.hypothesis.hypothesis!r}. Research rationale: {iteration.hypothesis.research_rationale or 'none recorded'}.",
        evidenceReferences=["hypothesis.hypothesis", "hypothesis.researchRationale"],
        confidence="high" if iteration.hypothesis.research_rationale else "low",
    )


def _quant_finding(iteration: ResearchLoopIterationRecord) -> ResearchCouncilFinding:
    scorecard = iteration.scorecard
    edge = "no measurable edge yet (zero real closed trades)" if not scorecard.trade_count else (
        f"expectancy {scorecard.expectancy_r}R, profit factor {scorecard.profit_factor} over {scorecard.trade_count} real closed trades"
    )
    return ResearchCouncilFinding(
        role="quant",
        finding=f"Measurable edge: {edge}.",
        evidenceReferences=["scorecard.expectancyR", "scorecard.profitFactor", "scorecard.tradeCount"],
        confidence="high" if (scorecard.trade_count or 0) >= RESEARCH_CANDIDATE_MIN_TRADE_COUNT else "low",
    )


def _risk_manager_finding(iteration: ResearchLoopIterationRecord) -> ResearchCouncilFinding:
    dd = iteration.scorecard.max_drawdown_r
    finding = f"Real max drawdown observed: {dd}R." if dd is not None else "No real drawdown evidence yet (zero closed trades)."
    return ResearchCouncilFinding(
        role="risk_manager", finding=finding, evidenceReferences=["scorecard.maxDrawdownR"], confidence="high" if dd is not None else "low"
    )


def _adversarial_finding(adversarial: AdversarialResearchResult | None) -> ResearchCouncilFinding:
    if adversarial is None:
        return ResearchCouncilFinding(
            role="adversarial_researcher", finding="Not yet adversarially attacked.", evidenceReferences=[], confidence="low"
        )
    finding = (
        f"Outlier resilience: {adversarial.outlier_resilience.classification}. "
        f"Regime robustness: {adversarial.regime_robustness.classification}. "
        f"Survives extended cost attack: {adversarial.extended_cost_attack.survives_beyond_stress}."
    )
    return ResearchCouncilFinding(
        role="adversarial_researcher",
        finding=finding,
        evidenceReferences=["adversarialResult.outlierResilience.classification", "adversarialResult.regimeRobustness.classification", "adversarialResult.extendedCostAttack.survivesBeyondStress"],
        confidence="high",
    )


def _regime_analyst_finding(iteration: ResearchLoopIterationRecord, adversarial: AdversarialResearchResult | None) -> ResearchCouncilFinding:
    if adversarial is not None:
        return ResearchCouncilFinding(
            role="regime_analyst",
            finding=f"Real regime robustness classification: {adversarial.regime_robustness.classification}. {adversarial.regime_robustness.detail}",
            evidenceReferences=["adversarialResult.regimeRobustness.classification", "adversarialResult.regimeRobustness.detail"],
            confidence="high",
        )
    verdict = iteration.scorecard.regime_robustness_verdict
    return ResearchCouncilFinding(
        role="regime_analyst",
        finding=f"Real regime-breakdown verdict from the base funnel: {verdict or 'not available'}.",
        evidenceReferences=["scorecard.regimeRobustnessVerdict"],
        confidence="medium" if verdict else "low",
    )


def _statistician_finding(iteration: ResearchLoopIterationRecord) -> ResearchCouncilFinding:
    trade_count = iteration.scorecard.trade_count or 0
    confidence: Literal["high", "medium", "low"]
    if trade_count >= RESEARCH_CANDIDATE_MIN_TRADE_COUNT:
        finding = f"{trade_count} real closed trades clears the real {RESEARCH_CANDIDATE_MIN_TRADE_COUNT}-trade evidence floor."
        confidence = "high"
    else:
        finding = f"Only {trade_count} real closed trades — below the real {RESEARCH_CANDIDATE_MIN_TRADE_COUNT}-trade evidence floor; any strong claim is premature."
        confidence = "low"
    return ResearchCouncilFinding(role="statistician", finding=finding, evidenceReferences=["scorecard.tradeCount"], confidence=confidence)


def _reviewer_finding(iteration: ResearchLoopIterationRecord) -> ResearchCouncilFinding:
    return ResearchCouncilFinding(
        role="reviewer",
        finding=f"Real candidacy classification: {iteration.candidacy!r} — {iteration.candidacy_reason}",
        evidenceReferences=["candidacy", "candidacyReason"],
        confidence="high",
    )


def _derive_recommendation(iteration: ResearchLoopIterationRecord, adversarial: AdversarialResearchResult | None) -> tuple[ResearchCouncilRecommendation, str]:
    """One fixed, real priority order over the SAME already-decided
    `candidacy` this council never re-judges — see this module's own
    docstring."""
    if iteration.candidacy == "insufficient_evidence":
        return "insufficient_evidence", "Real candidacy is 'insufficient_evidence' — below the evidence floor for any stronger recommendation."
    if iteration.candidacy in ("rejected", "overfit", "benchmark_failed", "risk_failed", "duplicate"):
        return "archive", f"Real candidacy '{iteration.candidacy}' already fails the research-candidate gate — this lineage should be archived, not retested blindly."
    if iteration.candidacy == "accepted":
        if adversarial is not None and (
            adversarial.outlier_resilience.classification == "highly_outlier_dependent"
            or adversarial.regime_robustness.classification == "regime_fragile"
            or adversarial.extended_cost_attack.survives_beyond_stress is False
        ):
            return "retest", "Clears the base research-candidate gate, but a real adversarial attack found a fragility — worth a real retest under those specific conditions before treating this as final."
        return "continue", "Clears the real research-candidate gate on every axis this council read — continue toward a real Champion/Challenger submission."
    # candidacy == "promising"
    if iteration.mutation is not None and iteration.mutation.observed_failure_codes:
        return "mutate", f"Promising but not yet accepted — a real diagnosed failure code ({iteration.mutation.observed_failure_codes[0]}) has a real bounded mutation to try next."
    return "retest", "Promising but not yet accepted, and no real diagnosed failure code with a bounded mutation exists — worth a real retest (e.g. more symbols/candles) before concluding further."


def convene_research_council(
    iteration: ResearchLoopIterationRecord,
    *,
    report_id: str,
    candidate_id: str,
    generated_at: str,
    adversarial_result: AdversarialResearchResult | None = None,
) -> ResearchCouncilReport:
    """The one real entry point. Pure function — reads `iteration`
    (and, when available, `adversarial_result`) and returns a
    `ResearchCouncilReport`; computes no new backtest/adversarial math
    of its own."""
    findings = [
        _researcher_finding(iteration),
        _quant_finding(iteration),
        _risk_manager_finding(iteration),
        _adversarial_finding(adversarial_result),
        _regime_analyst_finding(iteration, adversarial_result),
        _statistician_finding(iteration),
        _reviewer_finding(iteration),
    ]
    recommendation, recommendation_reason = _derive_recommendation(iteration, adversarial_result)
    return ResearchCouncilReport(
        id=report_id,
        candidateId=candidate_id,
        findings=findings,
        recommendation=recommendation,
        recommendationReason=recommendation_reason,
        generatedAt=generated_at,
    )
