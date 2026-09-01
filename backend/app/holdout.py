"""app/holdout.py — CEO directive "TradeTown — Phase 10: Real Data +
True Holdout + Portfolio Intelligence," Section B (True Holdout Data
Discipline).

RESEARCH FIRST. Phase 9's own `evaluate_holdout_availability()`
(app/adversarial_research.py) already disclosed the honest limitation
this module builds on top of, never contradicts: `MockMarketDataProvider`
has no independently-sourced, date-partitioned historical dataset — a
single `get_candles()` call returns ONE deterministic series for a given
`(symbol, timeframe)`. This module does NOT invent a second, fake data
source to get around that. What it DOES build is real: a genuine,
structurally-enforced TRAIN/VALIDATION/HOLDOUT chronological partition
of WHATEVER series a caller already fetched (mock today; a real,
external, date-ranged series later, unchanged code path — see
app/market_data.py's `ExternalMarketDataProvider`), plus a real
freeze/evaluation lifecycle that makes it structurally impossible for a
holdout result to influence mutation before that freeze.

WHY THIS IS A REAL, NOT A FAKE, "TRUE HOLDOUT." Three real, checkable
guarantees, not merely asserted in prose:
  1. THE SPLIT IS INDEX-BASED AND CHRONOLOGICAL, NEVER SHUFFLED.
     `partition_candles_chronologically()` slices ONE already-fetched,
     oldest-first candle list by position — train gets the earliest
     candles, validation the middle, holdout the LATEST — exactly once,
     deterministically, with zero randomness. A time-series holdout
     whose "future" bars leaked into "past" training would be
     meaningless; slicing by index on an already-ordered list makes
     that structurally impossible, not merely policy.
  2. THE BACKTEST ITSELF CANNOT SEE ACROSS THE PARTITION BOUNDARY.
     `run_holdout_evaluation()` calls
     `app/strategy_engine.py::backtest_symbol_over_candles()` — the
     SAME real function `app/walk_forward.py` already relies on for its
     own "a call with `candles[1000:2000]` can only ever resolve
     indicators using bars 1000-1999" no-look-ahead guarantee (see that
     function's own docstring) — passing ONLY the holdout slice. There
     is no code path anywhere in this module that hands the holdout
     slice to anything that also sees train/validation data.
  3. MUTATION NEVER SEES A HOLDOUT RESULT AT ALL, BY IMPORT SHAPE.
     Nothing in `app/research_factory.py` (mutation candidate
     construction, `retrieve_relevant_lessons()`, `generate_next_hypothesis()`)
     imports anything from this module — proven by
     `tests/test_holdout.py::TestNeverWiredIntoMutation`'s own real
     source-inspection test, the SAME discipline this codebase already
     uses to prove the Champion/Challenger and Research Council
     boundaries. Holdout evaluation is a separate, explicit, opt-in call
     (see `app/routers/sandbox.py`'s `/research-holdout/evaluate`
     endpoint) a CEO/agent makes AFTER deciding a candidate is worth
     freezing — never automatically invoked by the factory loop.

VALIDITY IS EARNED, NEVER ASSUMED. `validate_holdout()`'s `status` is
`"valid"` only when: every partition is non-empty, timestamps are
strictly chronological across partition boundaries (verified by REAL
comparison, not merely trusted from construction), no timestamp appears
in more than one partition, and a real `StrategyFreezeRecord` exists
naming the EXACT `(definition_id, definition_version)` under evaluation
— since `CompiledStrategyDefinition` is already immutable per version,
any real mutation after freeze produces a different version, which this
check catches automatically (Section K.16). `"unavailable"` (never
`"valid"`) is the honest default whenever data or a freeze is missing;
`"invalid"` is a real, disclosed structural failure. NEVER a fabricated
"valid" to make evidence look stronger than it is.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from app.backtest_primitives import aggregate_bucket
from app.data_quality import _parse_timestamp
from app.market_data import Candle
from app.schemas import (
    CompiledStrategyDefinition,
    DataPartitionSummary,
    EmaPullbackStatsBucket,
    HoldoutEvaluationResult,
    HoldoutValidationReport,
    StrategyFreezeRecord,
)
from app.strategy_engine import backtest_symbol_over_candles

# Section B — one real, disclosed, round convention (never derived from
# any study of this codebase's own strategies, same honesty idiom every
# other per-module threshold here already uses): the earliest 60% of an
# already-fetched series trains, the next 20% validates, and the FINAL
# 20% (chronologically latest — never touched until freeze) is held out.
DEFAULT_TRAIN_FRACTION = 0.6
DEFAULT_VALIDATION_FRACTION = 0.2


def partition_candles_chronologically(
    candles: list[Candle], *, train_fraction: float = DEFAULT_TRAIN_FRACTION, validation_fraction: float = DEFAULT_VALIDATION_FRACTION
) -> tuple[list[Candle], list[Candle], list[Candle]]:
    """The one real, deterministic split. `candles` must already be
    oldest-first (every real provider in this codebase — mock and
    external — returns candles in that order; see both classes' own
    docstrings). Never shuffles, never randomly samples — a real,
    positional slice of the real, already-ordered list, so train/
    validation/holdout are non-overlapping BY CONSTRUCTION (re-verified,
    never merely trusted, in `validate_holdout()` below)."""
    total = len(candles)
    train_end = round(total * train_fraction)
    validation_end = train_end + round(total * validation_fraction)
    return candles[:train_end], candles[train_end:validation_end], candles[validation_end:]


def _partition_summary(label: str, candles: list[Candle]) -> DataPartitionSummary:
    hasher = hashlib.sha256()
    for candle in candles:
        hasher.update(f"{candle.symbol}|{candle.timeframe}|{candle.timestamp}|{candle.open}|{candle.high}|{candle.low}|{candle.close}|{candle.volume}\n".encode("utf-8"))
    return DataPartitionSummary(
        label=label,  # type: ignore[arg-type]
        candleCount=len(candles),
        startTimestamp=candles[0].timestamp if candles else None,
        endTimestamp=candles[-1].timestamp if candles else None,
        contentHash=hasher.hexdigest()[:16],
    )


def freeze_strategy(
    definition: CompiledStrategyDefinition, *, dataset_version: str, feature_versions: list[str], frozen_at: str | None = None
) -> StrategyFreezeRecord:
    """The one real freeze event. Naming an already-immutable
    `(definition_id, definition_version)` pair — see this module's own
    docstring for why that alone is enough to make "mutated after
    freeze" automatically detectable rather than requiring a second
    mutability rule."""
    return StrategyFreezeRecord(
        id=f"freeze-{definition.id}-{definition.version}",
        definitionId=definition.id,
        definitionVersion=definition.version,
        frozenAt=frozen_at if frozen_at is not None else datetime.now(timezone.utc).isoformat(),
        datasetVersion=dataset_version,
        featureVersions=list(feature_versions),
    )


def validate_holdout(
    definition: CompiledStrategyDefinition,
    *,
    train: list[Candle],
    validation: list[Candle],
    holdout: list[Candle],
    dataset_id: str,
    dataset_version: str,
    freeze: StrategyFreezeRecord | None,
    report_id: str,
) -> HoldoutValidationReport:
    """The one real validity check. Priority order, each a REAL
    structural test over the actual candle content passed in — never
    assumed true from how the partitions were constructed:

    1. Any partition empty -> "unavailable" (no real evidence to
       evaluate at all).
    2. No `freeze` (or `freeze` names a DIFFERENT definition/version
       than `definition`, e.g. because a mutation ran after freezing a
       different version) -> "invalid" — Section K.16's own case.
    3. Real chronological-order check: every train timestamp must
       precede every validation timestamp, which must precede every
       holdout timestamp — computed via real `datetime` comparison
       (`app/data_quality.py`'s own `_parse_timestamp()`, reused, never
       re-derived), not merely trusted from construction.
    4. Real overlap/leakage check: no timestamp string may appear in
       more than one partition.

    Only when ALL of the above pass does `status` read `"valid"`."""
    train_summary = _partition_summary("train", train)
    validation_summary = _partition_summary("validation", validation)
    holdout_summary = _partition_summary("holdout", holdout)
    generated_at = datetime.now(timezone.utc).isoformat()

    def _report(*, overlap: bool, leakage: bool, chronological: bool, status: str, detail: str) -> HoldoutValidationReport:
        return HoldoutValidationReport(
            id=report_id,
            definitionId=definition.id,
            definitionVersion=definition.version,
            datasetId=dataset_id,
            datasetVersion=dataset_version,
            train=train_summary,
            validation=validation_summary,
            holdout=holdout_summary,
            overlapDetected=overlap,
            leakageDetected=leakage,
            chronologicalOrderValid=chronological,
            freeze=freeze,
            status=status,  # type: ignore[arg-type]
            detail=detail,
            generatedAt=generated_at,
        )

    if not train or not validation or not holdout:
        empty = [label for label, c in (("train", train), ("validation", validation), ("holdout", holdout)) if not c]
        return _report(overlap=False, leakage=False, chronological=False, status="unavailable", detail=f"Empty partition(s): {', '.join(empty)} — no real evidence to evaluate.")

    if freeze is None:
        return _report(overlap=False, leakage=False, chronological=False, status="invalid", detail="No real StrategyFreezeRecord — this definition has not been frozen; holdout evaluation is not yet meaningful.")
    if freeze.definition_id != definition.id or freeze.definition_version != definition.version:
        return _report(
            overlap=False,
            leakage=False,
            chronological=False,
            status="invalid",
            detail=f"Freeze names definition {freeze.definition_id!r} v{freeze.definition_version}, but this evaluation is for {definition.id!r} v{definition.version} — the strategy was mutated after freeze (Section K.16). Requires a new freeze and revalidation.",
        )

    all_timestamps = [c.timestamp for c in train] + [c.timestamp for c in validation] + [c.timestamp for c in holdout]
    leakage_detected = len(set(all_timestamps)) != len(all_timestamps)

    train_times = [t for t in (_parse_timestamp(c.timestamp) for c in train) if t is not None]
    validation_times = [t for t in (_parse_timestamp(c.timestamp) for c in validation) if t is not None]
    holdout_times = [t for t in (_parse_timestamp(c.timestamp) for c in holdout) if t is not None]
    chronological_order_valid = (
        len(train_times) == len(train)
        and len(validation_times) == len(validation)
        and len(holdout_times) == len(holdout)
        and max(train_times) <= min(validation_times)
        and max(validation_times) <= min(holdout_times)
    )
    overlap_detected = leakage_detected or not chronological_order_valid

    if overlap_detected:
        return _report(
            overlap=overlap_detected,
            leakage=leakage_detected,
            chronological=chronological_order_valid,
            status="invalid",
            detail="Real overlap/leakage detected between partitions — timestamps are not strictly chronological across train/validation/holdout, or a timestamp appears in more than one partition.",
        )

    return _report(
        overlap=False,
        leakage=False,
        chronological=True,
        status="valid",
        detail=f"Real, non-overlapping, strictly chronological partitions ({train_summary.candle_count}/{validation_summary.candle_count}/{holdout_summary.candle_count} candles), frozen at {freeze.frozen_at}.",
    )


def run_holdout_evaluation(
    definition: CompiledStrategyDefinition, symbol: str, *, report: HoldoutValidationReport, holdout_candles: list[Candle], result_id: str
) -> HoldoutEvaluationResult:
    """The one real holdout-only backtest — see this module's own
    docstring point 2 for why `backtest_symbol_over_candles()` called
    with ONLY `holdout_candles` cannot structurally see train/validation
    data. Refuses to backtest (returns `bucket=None`) whenever `report.status
    != "valid"` — an untrustworthy partition is never dressed up with a
    real-looking backtest number."""
    generated_at = datetime.now(timezone.utc).isoformat()
    if report.status != "valid":
        return HoldoutEvaluationResult(id=result_id, report=report, symbol=symbol, bucket=None, generatedAt=generated_at)
    trades = backtest_symbol_over_candles(definition, symbol, holdout_candles)
    bucket: EmaPullbackStatsBucket = aggregate_bucket("holdout", trades)
    return HoldoutEvaluationResult(id=result_id, report=report, symbol=symbol, bucket=bucket, generatedAt=generated_at)
