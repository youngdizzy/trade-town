"""CEO directive "Phase 9 / Real Market Data + Evidence Integrity
Foundation" — Data Quality Gate section.

RESEARCH FIRST: `app/leakage_audit.py` already proves POINT-IN-TIME
correctness (no look-ahead) via a real "truncate and re-detect"
methodology. That is a different question from DATA QUALITY (is this
candle series internally well-formed at all) — this module answers the
second question and never duplicates the first.

`validate_candle_series()` runs real structural checks against a
`list[Candle]` a caller has already retrieved (no fetch of its own, so
it never becomes a second data-retrieval path): timestamp ordering,
duplicate timestamps, gaps against the timeframe's expected bar
spacing, impossible OHLC relationships, non-positive prices, negative
volume, timeframe/symbol mismatches against what was requested,
insufficient history, and unparseable/timezone-naive timestamps.

Every check here is a real, mechanical, deterministic assertion over
the actual candle values passed in — never an ML/statistical "quality
score." `app/market_data.py`'s mock provider currently never produces
most of these defects by construction (it has no concept of a missing
bar — see `app/data_provenance.py`'s audit) — that is disclosed
honestly via `DataQualityReport.data_valid` being true today for mock
data, not hidden by skipping the checks."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.market_data import TIMEFRAMES, Candle
from app.schemas import CandleDataQualityIssue, DataQualityReport

#: Below this many candles, a research experiment's statistics are not
#: meaningfully backed by history regardless of what else is valid —
#: mirrors the order of magnitude already required elsewhere in this
#: codebase for a real statistical read (e.g. the ≥100 trade hard gate).
MIN_CANDLES_FOR_SUFFICIENT_HISTORY = 30

#: Bar-spacing gap tolerance as a fraction of the expected interval —
#: guards against float/rounding noise in timestamp math, not a real
#: allowance for missing bars.
_GAP_TOLERANCE = 0.01


def _parse_timestamp(raw: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError:
        return None
    return parsed


def validate_candle_series(
    candles: list[Candle],
    *,
    symbol: str,
    timeframe: str,
    min_candles: int = MIN_CANDLES_FOR_SUFFICIENT_HISTORY,
) -> DataQualityReport:
    issues: list[CandleDataQualityIssue] = []

    if len(candles) < min_candles:
        issues.append(
            CandleDataQualityIssue(
                code="insufficient_history",
                evidence=f"{len(candles)} candles retrieved, {min_candles} required for a valid read.",
            )
        )

    expected_minutes = TIMEFRAMES.get(timeframe)
    if expected_minutes is None:
        issues.append(CandleDataQualityIssue(code="timeframe_mismatch", evidence=f"Unsupported timeframe {timeframe!r}."))

    parsed_timestamps: list[datetime | None] = []
    seen_timestamps: set[str] = set()
    for index, candle in enumerate(candles):
        if candle.symbol != symbol:
            issues.append(
                CandleDataQualityIssue(
                    code="symbol_mismatch",
                    evidence=f"Candle at index {index} has symbol {candle.symbol!r}, expected {symbol!r}.",
                )
            )
        if expected_minutes is not None and candle.timeframe != timeframe:
            issues.append(
                CandleDataQualityIssue(
                    code="timeframe_mismatch",
                    evidence=f"Candle at index {index} has timeframe {candle.timeframe!r}, expected {timeframe!r}.",
                )
            )

        if candle.timestamp in seen_timestamps:
            issues.append(CandleDataQualityIssue(code="duplicate_timestamp", evidence=f"Timestamp {candle.timestamp!r} appears more than once."))
        seen_timestamps.add(candle.timestamp)

        parsed = _parse_timestamp(candle.timestamp)
        if parsed is None:
            issues.append(CandleDataQualityIssue(code="timezone_invalid", evidence=f"Candle at index {index} has an unparseable timestamp {candle.timestamp!r}."))
        elif parsed.tzinfo is None:
            issues.append(CandleDataQualityIssue(code="timezone_invalid", evidence=f"Candle at index {index} timestamp {candle.timestamp!r} carries no timezone offset."))
            # Excluded from ordering/gap comparisons below (mixing a
            # timezone-naive value with the timezone-aware rest of the
            # series would raise, not silently misorder) — already
            # flagged above, not silently dropped.
            parsed = None
        parsed_timestamps.append(parsed)

        if candle.open <= 0 or candle.high <= 0 or candle.low <= 0 or candle.close <= 0:
            issues.append(CandleDataQualityIssue(code="non_positive_price", evidence=f"Candle at index {index} has a non-positive OHLC value (o={candle.open}, h={candle.high}, l={candle.low}, c={candle.close})."))
        if candle.volume < 0:
            issues.append(CandleDataQualityIssue(code="negative_volume", evidence=f"Candle at index {index} has negative volume {candle.volume}."))
        if candle.high < candle.low or candle.high < candle.open or candle.high < candle.close or candle.low > candle.open or candle.low > candle.close:
            issues.append(
                CandleDataQualityIssue(
                    code="impossible_ohlc",
                    evidence=f"Candle at index {index} violates low<=open,close<=high (o={candle.open}, h={candle.high}, l={candle.low}, c={candle.close}).",
                )
            )

    ordered_timestamps = [t for t in parsed_timestamps if t is not None]
    for prev, curr in zip(ordered_timestamps, ordered_timestamps[1:]):
        if curr < prev:
            issues.append(CandleDataQualityIssue(code="timestamp_out_of_order", evidence=f"Timestamp {curr.isoformat()!r} precedes prior timestamp {prev.isoformat()!r}."))
            continue
        if expected_minutes is not None:
            actual_gap_minutes = (curr - prev).total_seconds() / 60.0
            if actual_gap_minutes > expected_minutes * (1 + _GAP_TOLERANCE):
                issues.append(
                    CandleDataQualityIssue(
                        code="missing_bars",
                        evidence=f"Gap of {actual_gap_minutes:.1f} minutes between {prev.isoformat()!r} and {curr.isoformat()!r} exceeds the expected {expected_minutes}-minute bar spacing.",
                    )
                )

    return DataQualityReport(
        id=f"quality-{uuid.uuid4().hex[:12]}",
        symbol=symbol,
        timeframe=timeframe,
        candleCount=len(candles),
        dataValid=len(issues) == 0,
        issues=issues,
        generatedAt=datetime.now(timezone.utc).isoformat(),
    )
