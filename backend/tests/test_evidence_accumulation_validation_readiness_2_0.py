"""Covers CEO directive "TradeTown — Real-Data Evidence Accumulation &
Validation Readiness 2.0" — an evidence-integrity and validation-
readiness milestone, explicitly NOT a new trading system.

Phase 0 forensic audit of the existing pipeline (built across two prior
milestones — "Real-Data Research Universe Expansion 2.0" and
"Timeframe-Aware Real-Data Research Infrastructure 1.0") found the vast
majority of this directive's required invariants already structurally
guaranteed and already tested elsewhere in this repo. This file covers
only the genuine gaps that audit identified:

  - Nonfinite (NaN/Infinity) candle values were never rejected anywhere
    in the real accumulation path — every existing `<=`/`<`/`>` check in
    `app/data_quality.py::validate_candle_series()` is silently `False`
    for NaN, and Python's own `json` module accepts the non-standard
    `NaN`/`Infinity` literals by default, so this is a genuinely
    reachable malformed-provider-response shape.
  - `validate_candle_series()` itself was wired ONLY into the mock
    research path (`app/routers/sandbox.py`), never into
    `app/real_data_accumulator.py::run_accumulation_cycle()` — so the
    real Kraken path had no defense-in-depth against malformed data
    beyond what the provider's own parser already checks.
  - Symbol-level partial-failure isolation (one symbol's provider
    failure must not corrupt or block another symbol's already-
    persisted data) was exercised only at the TIMEFRAME level elsewhere
    (`tests/test_timeframe_aware_real_data_infrastructure.py`'s
    `TestF_CrossTimeframeResearchRejection`), never at the symbol level.
  - "A failed run leaves previously-persisted evidence untouched" was
    implied by several other tests but never asserted BYTE-IDENTICAL
    before/after a second run whose provider fails outright.
  - The distinction between the FROZEN holdout boundary's dataset hash
    (must never change) and the development dataset's own FRESH content
    hash (legitimately changes as new real candles accumulate) was
    never directly tested — only the frozen boundary's own immutability
    was.
  - Factory reproducibility (same fixed inputs -> same outputs) and
    historical `FactoryRunRecord` immutability across a GROWING dataset
    (not merely an unchanged one, as
    `tests/test_factory_run_provenance.py::test_H_provenance_survives_subsequent_runs`
    already covers) were never directly exercised end-to-end.

Same isolated-accumulator-database convention every other real-data
test file in this repo already established.
"""
from __future__ import annotations

import dataclasses
import math
import sqlite3
from datetime import datetime, timedelta

import pytest

from app import real_data_accumulator as rda
from app.market_data import Candle, ExternalMarketDataProviderUnavailable, MarketDataProvider, MockMarketDataProvider
from app.real_data_research_bridge import RealDataFactoryPreflightFailure, preflight_real_data_dataset, run_real_data_factory_cycle
from app.schemas import StrategyHypothesis
from app.strategy_registry import default_researchable_strategies

_CREATED_AT = "2024-01-01T00:00:00+00:00"
_STRATEGIES, _REGISTRY = default_researchable_strategies()
FROZEN_DEFINITION = _REGISTRY["50-ema-breakout-pullback-long"][0]


def _historical(candles: list[Candle]) -> list[Candle]:
    return [dataclasses.replace(c, data_status="historical") for c in candles]


def _base_series(symbol: str, count: int = 3000) -> list[Candle]:
    return _historical(MockMarketDataProvider().get_candles(symbol, "1h", count))


def _extend(base: list[Candle], extra_bars: int) -> list[Candle]:
    last = base[-1]
    last_ts = datetime.fromisoformat(last.timestamp)
    price = last.close
    extension = [
        Candle(symbol=last.symbol, timeframe=last.timeframe, timestamp=(last_ts + timedelta(hours=i)).isoformat(), open=price, high=price + 1.0, low=price - 1.0, close=price, volume=100.0, data_status="historical")
        for i in range(1, extra_bars + 1)
    ]
    return [*base, *extension]


class _FixedProvider(MarketDataProvider):
    """Serves a pre-set candle list per symbol, retagged to whatever
    (symbol, timeframe) is actually requested — same convention every
    other real-data test file in this repo already established."""

    def __init__(self, candles_by_symbol: dict[str, list[Candle]]) -> None:
        self._candles_by_symbol = candles_by_symbol

    def get_quote(self, symbol: str):  # pragma: no cover - unused by this suite
        raise NotImplementedError

    def get_candles(self, symbol: str, timeframe: str, limit: int, *, end_time=None, anchor_price=None) -> list[Candle]:
        candles = self._candles_by_symbol[symbol]
        windowed = candles[-limit:] if limit > 0 else list(candles)
        return [dataclasses.replace(c, timeframe=timeframe, symbol=symbol) for c in windowed]


def _provider(btc: list[Candle], eth: list[Candle] | None = None) -> _FixedProvider:
    return _FixedProvider({"BTC-USD": btc, "ETH-USD": eth if eth is not None else btc})


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch: pytest.MonkeyPatch):
    db_path = str(tmp_path / "accum.db")
    monkeypatch.setenv("REAL_DATA_ACCUMULATOR_DB_PATH", db_path)
    yield db_path


def _conn() -> sqlite3.Connection:
    conn = rda._connect()
    rda.init_schema(conn)
    return conn


def _hypothesis(**overrides: object) -> StrategyHypothesis:
    base: dict[str, object] = dict(
        id="hyp-evidence-readiness-seed", hypothesis="Trend continuation after a confirmed breakout.", marketMechanism="Momentum continuation",
        expectedEdge="Positive expectancy in trending regimes", invalidationConditions="Flat/negative walk-forward expectancy",
        symbolUniverse=["BTC-USD"], timeframe="1h", entryConditions="x", exitConditions="x", stopLossLogic="x",
        takeProfitLogic="x", positionSizingLogic="x", riskConstraints="x", proposedBy="quant", createdAt=_CREATED_AT,
    )
    base.update(overrides)
    return StrategyHypothesis(**base)  # type: ignore[arg-type]


def _run_kwargs(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = dict(
        compiled_strategy_registry={FROZEN_DEFINITION.id: [FROZEN_DEFINITION]},
        quant_research_experiments=[],
        research_iterations=[],
        research_lessons=[],
        failed_archive=[],
        champion_history=[],
        risk_per_trade_pct=2.0,
        run_id="evidence-readiness-test",
        created_at=_CREATED_AT,
        max_generations=1,
        max_total_backtests=2,
    )
    base.update(overrides)
    return base


# --- Nonfinite candle values are rejected at accumulation -------------------


class TestNonfiniteValueRejectedAtAccumulation:
    def test_nan_close_is_rejected_and_nothing_persists_for_that_leg(self) -> None:
        base = _base_series("BTC-USD")
        tampered = list(base)
        tampered[-1] = dataclasses.replace(tampered[-1], close=math.nan)
        with pytest.raises(rda.AccumulationFailure, match="nonfinite_value"):
            rda.run_accumulation_cycle(provider=_provider(tampered))
        with _conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM candles WHERE symbol='BTC-USD' AND timeframe='1h'").fetchone()[0]
        assert count == 0, "a candle series containing NaN must not partially persist"

    def test_infinite_volume_is_rejected(self) -> None:
        base = _base_series("BTC-USD")
        tampered = list(base)
        tampered[10] = dataclasses.replace(tampered[10], volume=math.inf)
        with pytest.raises(rda.AccumulationFailure, match="nonfinite_value"):
            rda.run_accumulation_cycle(provider=_provider(tampered))


# --- Symbol-level partial-failure isolation ----------------------------------


class TestSymbolLevelPartialFailureIsolation:
    def test_one_symbols_provider_failure_does_not_block_or_corrupt_the_others_data(self) -> None:
        """`run_accumulation_cycle()` processes SYMBOLS in order (BTC-USD
        before ETH-USD — see its own loop) with one transaction per
        (symbol, timeframe). A provider that fails outright for
        ETH-USD must still leave BTC-USD's already-committed data
        intact — the same per-(symbol, timeframe) transaction boundary
        already proven at the TIMEFRAME level
        (`tests/test_timeframe_aware_real_data_infrastructure.py::TestF_CrossTimeframeResearchRejection`),
        exercised here at the SYMBOL level instead."""
        btc = _base_series("BTC-USD")

        class _EthFailingProvider(MarketDataProvider):
            def get_quote(self, symbol: str):  # pragma: no cover
                raise NotImplementedError

            def get_candles(self, symbol: str, timeframe: str, limit: int, *, end_time=None, anchor_price=None) -> list[Candle]:
                if symbol == "ETH-USD":
                    raise ExternalMarketDataProviderUnavailable("simulated ETH-USD outage")
                candles = btc[-limit:] if limit > 0 else list(btc)
                return [dataclasses.replace(c, timeframe=timeframe, symbol=symbol) for c in candles]

        with pytest.raises(rda.AccumulationFailure, match="Kraken unavailable"):
            rda.run_accumulation_cycle(provider=_EthFailingProvider())

        with _conn() as conn:
            btc_1h = conn.execute("SELECT COUNT(*) FROM candles WHERE symbol='BTC-USD' AND timeframe='1h'").fetchone()[0]
            btc_4h = conn.execute("SELECT COUNT(*) FROM candles WHERE symbol='BTC-USD' AND timeframe='4h'").fetchone()[0]
            eth_any = conn.execute("SELECT COUNT(*) FROM candles WHERE symbol='ETH-USD'").fetchone()[0]
        assert btc_1h == len(btc), "BTC-USD's own committed transactions must survive ETH-USD's outright provider failure"
        assert btc_4h == len(btc)
        assert eth_any == 0, "ETH-USD never persisted anything, consistent with its provider failing on its very first request"


# --- A failed run leaves previously-persisted evidence byte-identical -------


class TestProviderFailurePreservesExistingEvidence:
    def test_second_runs_total_provider_outage_leaves_all_prior_rows_byte_identical(self) -> None:
        base = _base_series("BTC-USD")
        result1 = rda.run_accumulation_cycle(provider=_provider(base))
        assert result1["status"] == "success"

        with _conn() as conn:
            candles_before = conn.execute("SELECT * FROM candles ORDER BY symbol, timeframe, candle_timestamp").fetchall()
            boundary_before = conn.execute("SELECT * FROM holdout_boundary ORDER BY symbol, timeframe").fetchall()
            trades_before = conn.execute("SELECT * FROM trades ORDER BY symbol, timeframe, entry_timestamp").fetchall()

        class _TotalOutageProvider(MarketDataProvider):
            def get_quote(self, symbol: str):  # pragma: no cover
                raise NotImplementedError

            def get_candles(self, symbol: str, timeframe: str, limit: int, *, end_time=None, anchor_price=None) -> list[Candle]:
                raise ExternalMarketDataProviderUnavailable("simulated total outage — Kraken unreachable for every symbol/timeframe")

        with pytest.raises(rda.AccumulationFailure, match="Kraken unavailable"):
            rda.run_accumulation_cycle(provider=_TotalOutageProvider())

        with _conn() as conn:
            candles_after = conn.execute("SELECT * FROM candles ORDER BY symbol, timeframe, candle_timestamp").fetchall()
            boundary_after = conn.execute("SELECT * FROM holdout_boundary ORDER BY symbol, timeframe").fetchall()
            trades_after = conn.execute("SELECT * FROM trades ORDER BY symbol, timeframe, entry_timestamp").fetchall()

        assert candles_before == candles_after, "a total provider outage on a later run must not alter a single previously-persisted candle row"
        assert boundary_before == boundary_after
        assert trades_before == trades_after


# --- Legitimate development growth vs. the frozen holdout hash --------------


class TestDatasetHashLegitimateGrowthVsFrozenHoldout:
    def test_development_content_hash_changes_on_growth_while_holdout_boundary_is_untouched(self) -> None:
        base = _base_series("BTC-USD")
        result = rda.run_accumulation_cycle(provider=_provider(base))
        assert result["status"] == "success"

        preflight_before = preflight_real_data_dataset("BTC-USD", FROZEN_DEFINITION, timeframe="1h")
        assert not isinstance(preflight_before, RealDataFactoryPreflightFailure)
        _provider_before, provenance_before = preflight_before

        with _conn() as conn:
            frozen_before = conn.execute(
                "SELECT holdout_start_timestamp, holdout_end_timestamp, dataset_content_hash, frozen_at FROM holdout_boundary WHERE symbol='BTC-USD' AND timeframe='1h'"
            ).fetchone()

        grown = _extend(base, 400)
        result2 = rda.run_accumulation_cycle(provider=_provider(grown))
        assert result2["status"] == "success"

        preflight_after = preflight_real_data_dataset("BTC-USD", FROZEN_DEFINITION, timeframe="1h")
        assert not isinstance(preflight_after, RealDataFactoryPreflightFailure)
        _provider_after, provenance_after = preflight_after

        with _conn() as conn:
            frozen_after = conn.execute(
                "SELECT holdout_start_timestamp, holdout_end_timestamp, dataset_content_hash, frozen_at FROM holdout_boundary WHERE symbol='BTC-USD' AND timeframe='1h'"
            ).fetchone()

        # Legitimate evolution: the FRESH development-only content hash
        # (recomputed every preflight call over whatever development
        # candles exist right now) changes because real new candles
        # were genuinely appended.
        assert provenance_before.dataset_content_hash != provenance_after.dataset_content_hash
        assert provenance_after.development_candle_count > provenance_before.development_candle_count
        # Historical mutation would instead be the FROZEN holdout
        # boundary's own stored hash/timestamps changing — they must
        # not, no matter how much development data accumulates.
        assert frozen_before == frozen_after, "the frozen holdout boundary must never move or be recomputed as development data grows"
        assert provenance_before.holdout_start_timestamp == provenance_after.holdout_start_timestamp
        assert provenance_before.holdout_end_timestamp == provenance_after.holdout_end_timestamp
        assert provenance_before.holdout_boundary_frozen_at == provenance_after.holdout_boundary_frozen_at


# --- Factory reproducibility -------------------------------------------------


class TestFactoryReproducibility:
    def test_identical_inputs_against_an_unchanged_dataset_produce_identical_results(self) -> None:
        base = _base_series("BTC-USD")
        result = rda.run_accumulation_cycle(provider=_provider(base))
        assert result["status"] == "success"

        outcome1 = run_real_data_factory_cycle(_hypothesis(), FROZEN_DEFINITION, symbol="BTC-USD", timeframe="1h", **_run_kwargs())
        outcome2 = run_real_data_factory_cycle(_hypothesis(), FROZEN_DEFINITION, symbol="BTC-USD", timeframe="1h", **_run_kwargs())

        assert outcome1.status == outcome2.status == "completed"
        assert outcome1.provenance is not None and outcome2.provenance is not None
        assert outcome1.provenance == outcome2.provenance, "preflight over an unchanged dataset must be perfectly reproducible"
        assert outcome1.run is not None and outcome2.run is not None
        assert outcome1.run.candidates_generated == outcome2.run.candidates_generated
        assert len(outcome1.new_iterations or []) == len(outcome2.new_iterations or [])
        for iter1, iter2 in zip(outcome1.new_iterations or [], outcome2.new_iterations or []):
            exp1, exp2 = iter1.experiment, iter2.experiment
            assert exp1.backtest.trades == exp2.backtest.trades, "the same fixed real dataset must produce the identical trade sequence both times"
            assert exp1.conclusion == exp2.conclusion


# --- Historical FactoryRunRecord immutability across a GROWING dataset ------


class TestHistoricalFactoryRunImmutabilityAcrossGrowth:
    def test_a_prior_runs_provenance_and_run_record_do_not_mutate_when_the_dataset_later_grows(self) -> None:
        """`tests/test_factory_run_provenance.py::test_H_provenance_survives_subsequent_runs`
        already proves provenance survives a SECOND run against an
        UNCHANGED dataset. The genuine remaining gap: does a PRIOR run's
        own already-returned `RealDataFactoryRunOutcome` (a caller would
        have already stored `run`/`provenance` in history by the time
        more real data arrives) mutate when the underlying accumulator
        dataset GROWS afterward? It must not — these are plain
        `@dataclass(frozen=True)` value objects, never mutated in place,
        and this proves it end-to-end rather than merely by
        inspection."""
        base = _base_series("BTC-USD")
        rda.run_accumulation_cycle(provider=_provider(base))

        outcome1 = run_real_data_factory_cycle(_hypothesis(), FROZEN_DEFINITION, symbol="BTC-USD", timeframe="1h", **_run_kwargs(run_id="run-before-growth"))
        assert outcome1.status == "completed"
        assert outcome1.run is not None and outcome1.provenance is not None
        # `FactoryRunRecord` is a Pydantic `CamelModel`, not a stdlib
        # dataclass (only `RealDataResearchProvenance` is) — snapshot
        # each with the tool appropriate to its own type.
        run1_snapshot = outcome1.run.model_copy(deep=True)
        provenance1_snapshot = dataclasses.replace(outcome1.provenance)

        grown = _extend(base, 500)
        result2 = rda.run_accumulation_cycle(provider=_provider(grown))
        assert result2["status"] == "success"

        outcome2 = run_real_data_factory_cycle(_hypothesis(), FROZEN_DEFINITION, symbol="BTC-USD", timeframe="1h", **_run_kwargs(run_id="run-after-growth"))
        assert outcome2.status == "completed"
        assert outcome2.provenance is not None
        assert outcome2.provenance.development_candle_count > provenance1_snapshot.development_candle_count, "fixture assumption: growth must actually be visible to a later preflight"

        # The FIRST outcome's own objects, obtained BEFORE the dataset
        # grew, must still compare equal to the snapshot taken at that
        # time — nothing retroactively rewrote them.
        assert outcome1.run == run1_snapshot
        assert outcome1.provenance == provenance1_snapshot
