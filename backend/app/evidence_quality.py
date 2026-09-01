"""app/evidence_quality.py — CEO directive "TradeTown — Phase 10: Real
Data + True Holdout + Portfolio Intelligence," Section E
(Data-Confidence-Aware Research).

PURE RELABELING, NO NEW EVIDENCE. Every field on `EvidenceQualityReport`
is a direct read of an already-real, already-computed signal:
`data_provenance`/`data_quality_valid`/`point_in_time_verified` come
straight from `ResearchExperimentRecord.datasetMetadata`/
`pointInTimeVerified` (Phase 9, unmodified); `holdout_status` from a
`HoldoutValidationReport` a caller already produced via app/holdout.py
(`None` when holdout was never attempted for this candidate — never
guessed); `external_provider_available` from
`app/market_data.py::ExternalMarketDataProvider.is_available()`;
`benchmark_available`/`sample_size` from the same `ResearchExperimentRecord`.
This module computes ZERO new backtest/statistical math — it only
classifies already-real signals into one real, disclosed evidence
STATE, matching the same honesty idiom `app/overfitting_diagnostics.py`/
`app/research_council.py` already established (a real relabeling layer,
never a second judgment).

THE STATE LADDER, DISCLOSED. `classify_evidence_state()` checks, in this
fixed priority order (highest real evidence bar first):
  1. `external_data_validated` — real external market data (`data_
     provenance == "real"`) AND a real, valid holdout evaluation.
  2. `holdout_validated` — a real, valid holdout evaluation exists,
     regardless of whether the underlying data was mock or real (a real,
     structural out-of-sample check is still real evidence even over
     simulated data — see app/holdout.py's own module docstring for why
     the SPLIT MECHANICS are honestly checkable independent of data
     source).
  3. `research_validated` — clears the real sample-size floor, real data
     quality, and real point-in-time checks, but no holdout was
     attempted (or it came back `"unavailable"`/`"invalid"`).
  4. `simulated_only` — real data exists but the provenance is
     `simulated`/`synthetic`/`unavailable` and the stronger bars above
     were not cleared.
  5. `insufficient_data` — the real sample-size floor was not met, or
     real data quality failed.

THESE ARE EVIDENCE STATES, NOT TRADING APPROVALS (Section E's own
explicit words). Nothing here is imported by
`app/champion_challenger.py`, `app/strategy_lab.py`'s Certification/
Hall-of-Fame functions, or any risk gate — proven by
`tests/test_evidence_quality.py::TestNeverAPromotionAuthority`."""
from __future__ import annotations

from datetime import datetime, timezone

from app.research_loop import RESEARCH_CANDIDATE_MIN_TRADE_COUNT
from app.schemas import DataCategory, EvidenceQualityReport, EvidenceState, HoldoutValidationStatus


def classify_evidence_state(
    *,
    data_provenance: DataCategory,
    data_quality_valid: bool | None,
    point_in_time_verified: bool | None,
    holdout_status: HoldoutValidationStatus | None,
    sample_size: int | None,
    min_trade_count: int = RESEARCH_CANDIDATE_MIN_TRADE_COUNT,
) -> tuple[EvidenceState, str]:
    """The one real, disclosed priority rule — see this module's own
    docstring for the exact ladder and why each rung requires what it
    requires."""
    if sample_size is None or sample_size < min_trade_count or data_quality_valid is False:
        return "insufficient_data", f"Real sample size {sample_size} is below the real {min_trade_count}-trade floor, or real data-quality checks failed — no stronger evidence state is honest yet."

    if holdout_status == "valid":
        if data_provenance == "real":
            return "external_data_validated", "Real external market data AND a real, valid, structurally leak-proof holdout evaluation — the strongest real evidence state this codebase can currently produce."
        return "holdout_validated", f"A real, valid, structurally leak-proof holdout evaluation exists, though the underlying candle data is {data_provenance!r}, not real historical market data — the SPLIT is real even though the market it was tested against is simulated."

    if data_quality_valid is True and point_in_time_verified is True:
        return "research_validated", "Clears the real sample-size floor, real data-quality checks, and the real point-in-time (no-look-ahead) audit — but no real holdout evaluation has been run yet."

    if data_provenance in ("simulated", "synthetic", "unavailable"):
        return "simulated_only", f"Real data exists ({sample_size} trades) but the underlying source is {data_provenance!r}, and the full real research-validation bar (data quality + point-in-time) was not cleared."

    return "research_validated", "Clears the real sample-size floor; data quality/point-in-time checks are not both confirmed positive, but provenance is not simulated/synthetic/unavailable."


def build_evidence_quality_report(
    *,
    definition_id: str,
    definition_version: int,
    data_provenance: DataCategory,
    data_quality_valid: bool | None,
    point_in_time_verified: bool | None,
    holdout_status: HoldoutValidationStatus | None,
    sample_size: int | None,
    external_provider_available: bool,
    benchmark_available: bool,
    adversarial_coverage: bool,
    report_id: str,
) -> EvidenceQualityReport:
    """The one real entry point. Pure function — computes no new
    evidence, only classifies the real signals passed in."""
    state, detail = classify_evidence_state(
        data_provenance=data_provenance,
        data_quality_valid=data_quality_valid,
        point_in_time_verified=point_in_time_verified,
        holdout_status=holdout_status,
        sample_size=sample_size,
    )
    return EvidenceQualityReport(
        id=report_id,
        definitionId=definition_id,
        definitionVersion=definition_version,
        dataProvenance=data_provenance,
        dataQualityValid=data_quality_valid,
        pointInTimeVerified=point_in_time_verified,
        holdoutStatus=holdout_status,
        sampleSize=sample_size,
        externalProviderAvailable=external_provider_available,
        benchmarkAvailable=benchmark_available,
        adversarialCoverage=adversarial_coverage,
        state=state,
        detail=detail,
        generatedAt=datetime.now(timezone.utc).isoformat(),
    )
