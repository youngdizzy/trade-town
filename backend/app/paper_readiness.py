"""app/paper_readiness.py — CEO directive "TradeTown — Paper-Trading
Readiness + Professional Strategy Validation Hardening," Section 1
(Paper-Trading Readiness Gate), Section 2 (Evidence Quality Hierarchy),
and Section 3 (Paper-Trading Data Provenance).

DO NOT REBUILD, DO NOT DUPLICATE. This module invents no new backtest,
statistical, or evidence computation. It combines two already-real,
already-tested judgments into one disclosed readiness verdict:

  1. `app/research_loop.py::classify_candidacy()` — the existing
     research-candidacy classification (trade count, expectancy, profit
     factor, drawdown, walk-forward, cost sensitivity, parameter
     sensitivity, outlier dependence, regime failure, benchmark
     comparison, duplicate/tuning exposure — all real, already-computed
     axes over a `ResearchExperimentRecord`). This module calls the
     SAME function every other candidacy read already calls.
  2. `EvidenceQualityReport.state` (Phase 10, app/evidence_quality.py)
     — the real REAL/SIMULATED/SYNTHETIC/UNAVAILABLE provenance ladder.

WHY A SEPARATE GATE, DISCLOSED. `classify_candidacy()`'s own docstring
is explicit that it is "purely informational triage... nothing here
ever gates Certification/Hall-of-Fame/Champion-Challenger" — it never
checks data provenance at all, so a strategy backed entirely by
`SimulationResult` (this codebase's original RNG-based Sandbox
simulation — see app/simulation.py's own docstring: "sharpeRatio/
sortinoRatio are explicitly placeholder formulas") could in principle
read as "accepted" candidacy while never having been evaluated against
this codebase's REAL evidence pipeline at all. This module closes that
exact gap: `evaluate_paper_readiness()` accepts ONLY a real
`ResearchExperimentRecord` (never a `SimulationResult` — there is no
code path here that could accept one) and additionally requires
`EvidenceQualityReport.state` to have cleared the real simulated-only
floor, so a candidate can never become `"paper_ready"` on RNG-only
evidence alone, satisfying this directive's own Acceptance Criterion A.

NEVER A PROMOTION AUTHORITY. This module writes nothing, persists
nothing, and is never imported by `app/champion_challenger.py` or
`app/strategy_lab.py`'s Certification/Hall-of-Fame functions — proven
by `tests/test_paper_readiness.py::TestNeverAPromotionAuthority`, the
same source-inspection discipline this session's Portfolio Analyst and
Evidence Quality modules already established. `PAPER_READY` is a
research-readiness classification, not a live-trading promotion, and
this module has no path to Champion/Challenger, Certification, or order
execution.

WHAT THIS MODULE DELIBERATELY DOES NOT BUILD, DISCLOSED (see the CEO
directive's own Section 41/"DO NOT OVERBUILD" and this session's
forensic report for the full list): no persisted PaperTradeRecord
journal, no paper-vs-backtest drift detection, no strategy health state
machine, no autonomous mutation-application engine. Those are real,
separate, substantially larger systems this pass does not attempt —
this module is deliberately scoped to the one bounded, well-specified,
immediately reusable piece: the readiness VERDICT itself."""
from __future__ import annotations

from app.research_loop import classify_candidacy, derive_research_failure_codes
from app.schemas import (
    BenchmarkComparison,
    EvidenceQualityReport,
    HoldoutValidationReport,
    PaperReadinessCheck,
    PaperReadinessReport,
    PaperReadinessStatus,
    ResearchExperimentRecord,
)

# Section 2 — the real, disclosed evidence-quality floor a candidate
# must clear to ever become paper-ready. Both states describe evidence
# that never cleared this codebase's own real research-validation bar
# (see app/evidence_quality.py's own docstring for the exact ladder) —
# neither is "RNG-only" in isolation, but both are real states that
# must never be silently treated as sufficient for paper trading.
_BLOCKING_EVIDENCE_STATES: frozenset[str] = frozenset({"insufficient_data", "simulated_only"})


def evaluate_paper_readiness(
    record: ResearchExperimentRecord,
    *,
    evidence_quality: EvidenceQualityReport,
    outlier_dependent: bool | None,
    benchmark_comparisons: list[BenchmarkComparison],
    research_relationship: str,
    research_family_experiment_count: int | None,
    tuning_version: int,
    holdout: HoldoutValidationReport | None,
    report_id: str,
    generated_at: str,
) -> PaperReadinessReport:
    """The one real entry point. Reuses `derive_research_failure_codes()`/
    `classify_candidacy()` verbatim (same real inputs every existing
    caller of those functions already supplies) rather than
    recomputing any of their real math."""
    failure_codes = derive_research_failure_codes(
        record,
        outlier_dependent=outlier_dependent,
        benchmark_comparisons=benchmark_comparisons,
        research_relationship=research_relationship,
        research_family_experiment_count=research_family_experiment_count,
        tuning_version=tuning_version,
    )
    candidacy, candidacy_reason = classify_candidacy(
        trade_count=record.backtest.overall.trade_count,
        failure_codes=failure_codes,
        research_relationship=research_relationship,
        benchmark_comparisons=benchmark_comparisons,
    )

    checks: list[PaperReadinessCheck] = [
        PaperReadinessCheck(
            name="research_candidacy",
            status="pass" if candidacy == "accepted" else ("insufficient_evidence" if candidacy == "insufficient_evidence" else "fail"),
            detail=f"{candidacy}: {candidacy_reason}",
        ),
        PaperReadinessCheck(
            name="evidence_quality_state",
            status="fail" if evidence_quality.state in _BLOCKING_EVIDENCE_STATES else "pass",
            detail=f"{evidence_quality.state}: {evidence_quality.detail}",
        ),
    ]
    if holdout is None:
        checks.append(
            PaperReadinessCheck(
                name="holdout_validation",
                status="not_available",
                detail=(
                    "No holdout evaluation was supplied for this definition. Holdout is disclosed context here, not a "
                    "mandatory readiness axis in this environment — see app/holdout.py's own module docstring: no real "
                    "pre-partitioned historical dataset exists here, so requiring a real holdout pass would make "
                    "PAPER_READY permanently unreachable rather than honestly reflect this environment's real limits."
                ),
            )
        )
    else:
        checks.append(
            PaperReadinessCheck(
                name="holdout_validation",
                status="pass" if holdout.status == "valid" else ("insufficient_evidence" if holdout.status == "unavailable" else "fail"),
                detail=f"{holdout.status}: {holdout.detail}",
            )
        )

    blocking = [c for c in checks if c.status in ("fail", "insufficient_evidence")]
    status: PaperReadinessStatus = "not_ready" if blocking else "paper_ready"
    if status == "paper_ready":
        detail = (
            "Every mandatory readiness check passed — research candidacy is accepted, and evidence quality clears the "
            "real simulated-only floor. This verdict is research-readiness only; it does not promote this strategy to "
            "Champion/Challenger, Certification, or any live/paper execution path."
        )
    else:
        names = ", ".join(c.name for c in blocking)
        detail = f"Not paper-ready — blocked by: {names}."

    return PaperReadinessReport(
        id=report_id,
        definitionId=record.definition_id,
        definitionVersion=record.definition_version,
        status=status,
        checks=checks,
        candidacy=candidacy,
        evidenceState=evidence_quality.state,
        holdoutStatus=holdout.status if holdout is not None else None,
        detail=detail,
        generatedAt=generated_at,
    )
