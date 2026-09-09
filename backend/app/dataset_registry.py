"""CEO directive "Phase 9 / Real Market Data + Evidence Integrity
Foundation" — Dataset Versioning + Data Provenance sections.

RESEARCH FIRST: `app/market_data.py`'s `MockMarketDataProvider` is still
every EXISTING research consumer's only actual `MarketDataProvider`
(app/strategy_engine.py, app/walk_forward.py, app/parameter_sensitivity.py,
app/cost_sensitivity.py, app/leakage_audit.py, and app/baseline_comparison.py
all still hardcode the global mock singleton — no research module accepts
an injectable provider yet, a real, disclosed, separately-scoped gap; see
CEO directive "Real OHLCV Market Data Provider Activation & Provenance
1.0"'s final report). What it adds is real, structural: given a concrete
set of symbols/timeframe/candle-count actually retrieved from whatever
provider a caller used, compute a `DatasetMetadata` record that
*content-hashes the real retrieved OHLCV data* rather than fabricating a
version string or a fake growth counter.

PROVENANCE IS DERIVED FROM THE ACTUAL CANDLES, NOT ASSUMED.
`_resolve_source_and_category()` used to unconditionally return
`"mock_provider"`/`"simulated"` because no real adapter existed in this
codebase at all. That is no longer true (see
`app/market_data.py::KrakenMarketDataProvider`) — this function now
classifies `source`/`data_category` from the real `Candle.data_status`
values a caller's candles actually carry, so a future caller that
retrieves real external candles gets an honest `"external_real_provider"`/
`"real"` record instead of a stale, hardcoded mock label. See that
function's own docstring for the exact classification rule.

Honesty disclosure on `dataset_version`: because `MockMarketDataProvider.
get_candles()` is deterministically seeded from `(symbol, timeframe)`
only — never wall-clock time (confirmed in market_data.py) — the same
`(symbols, timeframe, candles_per_symbol)` combination will hash to the
same `dataset_version` every time it is retrieved today. That is not a
bug being hidden; it is the correct, disclosed consequence of the mock
provider's determinism. The version is still a REAL SHA-256 of REAL
retrieved content (not a constant baked into this file) — it will
change the moment a real, non-deterministic provider is plugged in via
`MARKET_DATA_PROVIDER`, or if the mock's own generation logic changes.

DO NOT: this module never fetches data itself beyond what a caller
already retrieved (no second candle-fetch path — callers pass in the
already-fetched `dict[str, list[Candle]]`), never invents a "real"
data_category for mock data, and never silently substitutes fewer
candles without recording it in `missing_bar_symbols`/`coverage_pct`.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone

from app.market_data import Candle
from app.schemas import DataCategory, DatasetMetadata, DatasetSource

#: `app/market_data.py`'s mock provider never applies a corporate-
#: action adjustment (splits/dividends) — it has no such concept. A
#: real adapter would report its actual policy ("split_dividend_adjusted",
#: "raw", ...) here instead.
_MOCK_ADJUSTMENT_POLICY = "none_mock_data_has_no_corporate_actions"


#: `Candle.data_status` values a real external provider (e.g.
#: `KrakenMarketDataProvider`, added by CEO directive "Real OHLCV Market
#: Data Provider Activation & Provenance 1.0") actually produces — never
#: `MockMarketDataProvider`, which only ever produces `"simulated"`.
_REAL_DATA_STATUSES = frozenset({"historical", "live", "delayed"})


def _resolve_source_and_category(candles_by_symbol: dict[str, list[Candle]]) -> tuple[DatasetSource, DataCategory]:
    """Classifies the ACTUAL candles a caller retrieved, rather than
    assuming mock unconditionally (the previous, now-stale behavior, from
    before this codebase had any real adapter — see `KrakenMarketDataProvider`
    in app/market_data.py). This is the one narrow provenance-boundary fix
    CEO directive "Real OHLCV Market Data Provider Activation &
    Provenance 1.0" requires: a research artifact built from real candles
    must not be silently mislabeled `"mock_provider"`/`"simulated"` (see
    that directive's Section 27/40 — "could a future consumer mistake
    real/synthetic data for the other?").

    Every distinct `data_status` seen across every symbol is collected.
    Real-only -> `"external_real_provider"`/`"real"`. Mock-only (or no
    candles at all, preserving the pre-existing default for that edge
    case) -> `"mock_provider"`/`"simulated"`. A MIX of real and mock
    statuses in one call is a genuine caller anomaly (this milestone does
    not enable multi-provider blending) — never blessed as `"real"`;
    reported as `"mock_provider"`/`"unavailable"` rather than fabricating
    a confident answer either way."""
    statuses: set[str] = {candle.data_status for candles in candles_by_symbol.values() for candle in candles}
    if not statuses:
        return "mock_provider", "simulated"
    has_real = bool(statuses & _REAL_DATA_STATUSES)
    has_mock = "simulated" in statuses
    if has_real and not has_mock:
        return "external_real_provider", "real"
    if has_mock and not has_real:
        return "mock_provider", "simulated"
    return "mock_provider", "unavailable"


def build_dataset_metadata(
    candles_by_symbol: dict[str, list[Candle]],
    *,
    symbols: list[str],
    timeframe: str,
    candles_per_symbol_requested: int,
) -> DatasetMetadata:
    """Build a real `DatasetMetadata` record from candles a caller has
    already fetched (never fetches on its own — see module docstring).

    `dataset_id` is a stable identifier for the (symbols, timeframe)
    *shape* of the request; `dataset_version` is a content hash of the
    actual retrieved OHLCV values, so it changes if and only if the
    underlying data changes (see the honesty disclosure above for why
    it is a stable constant against today's deterministic mock)."""
    source, data_category = _resolve_source_and_category(candles_by_symbol)

    candles_per_symbol_retrieved: dict[str, int] = {}
    missing_bar_symbols: list[str] = []
    hasher = hashlib.sha256()
    for symbol in symbols:
        candles = candles_by_symbol.get(symbol, [])
        candles_per_symbol_retrieved[symbol] = len(candles)
        if len(candles) < candles_per_symbol_requested:
            missing_bar_symbols.append(symbol)
        for candle in candles:
            hasher.update(
                f"{candle.symbol}|{candle.timeframe}|{candle.timestamp}|"
                f"{candle.open}|{candle.high}|{candle.low}|{candle.close}|"
                f"{candle.volume}|{candle.data_status}\n".encode("utf-8")
            )

    total_requested = candles_per_symbol_requested * len(symbols)
    total_retrieved = sum(candles_per_symbol_retrieved.values())
    coverage_pct = (total_retrieved / total_requested * 100.0) if total_requested > 0 else 0.0

    dataset_id = f"{timeframe}:{','.join(sorted(symbols))}:{candles_per_symbol_requested}"
    dataset_version = hasher.hexdigest()[:16]

    return DatasetMetadata(
        datasetId=dataset_id,
        datasetVersion=dataset_version,
        source=source,
        dataCategory=data_category,
        symbols=list(symbols),
        timeframe=timeframe,
        candlesPerSymbolRequested=candles_per_symbol_requested,
        candlesPerSymbolRetrieved=candles_per_symbol_retrieved,
        coveragePct=round(coverage_pct, 2),
        missingBarSymbols=missing_bar_symbols,
        adjustmentPolicy=_MOCK_ADJUSTMENT_POLICY,
        retrievedAt=datetime.now(timezone.utc).isoformat(),
        # CEO directive "Phase 9: Full Autonomous Quant Research
        # Factory," Phase 1 — this mock provider has no real
        # date-partitioned historical dataset to carve a genuine
        # train/validation/test/holdout split from (see DataSplit's own
        # docstring in schemas.py). Explicit, not relying on the
        # schema's own default, so this honesty is visible here too.
        dataSplit="unavailable",
    )
