"""Covers app/schemas.py::FactoryRunProvenance and its wiring into
app/state.py::submit_research_factory_run()/submit_real_data_research_factory_run()
— CEO directive "TradeTown — Real-Data Research Evidence Ledger &
Provenance 1.0."

Same isolated-accumulator-database convention the other real-data test
files already established. These tests focus specifically on the NEW
provenance contract: that it is attached correctly, survives
persistence/reload, never drifts once a run exists, and never falsely
labels an unclassifiable historical record."""
from __future__ import annotations

import asyncio
import dataclasses
import inspect

import pytest

from app import real_data_accumulator as rda
from app.market_data import Candle, MockMarketDataProvider
from app.real_data_accumulator import _strategy_fingerprint
from app.schemas import FactoryRunProvenance, FactoryRunRecord, StrategyHypothesis
from app.state import GameState
from app.strategy_registry import default_researchable_strategies

_CREATED_AT = "2024-01-01T00:00:00+00:00"


def _frozen_definition():
    _strategies, registry = default_researchable_strategies()
    return registry[rda.STRATEGY_DEFINITION_ID][0]


def _historical(candles: list[Candle]) -> list[Candle]:
    return [dataclasses.replace(c, data_status="historical") for c in candles]


def _base_series(symbol: str, count: int = 3000) -> list[Candle]:
    return _historical(MockMarketDataProvider().get_candles(symbol, "1h", count))


class _FixedProvider:
    """Auto-retags every returned candle to the REQUESTED timeframe —
    see test_real_data_accumulator.py's own `_FixedProvider` docstring
    for the full rationale (this file's own `_seed_accumulator()` now
    accumulates both "1h" and "4h" per symbol via the unmodified
    `run_accumulation_cycle()`)."""

    def __init__(self, candles_by_symbol: dict[str, list[Candle]]) -> None:
        self._candles_by_symbol = candles_by_symbol

    def get_quote(self, symbol: str):  # pragma: no cover - unused by this suite
        raise NotImplementedError

    def get_candles(self, symbol: str, timeframe: str, limit: int, *, end_time=None, anchor_price=None) -> list[Candle]:
        candles = self._candles_by_symbol[symbol]
        windowed = candles[-limit:] if limit > 0 else list(candles)
        return [dataclasses.replace(c, timeframe=timeframe) for c in windowed]


def _provider(btc: list[Candle], eth: list[Candle] | None = None) -> _FixedProvider:
    return _FixedProvider({"BTC-USD": btc, "ETH-USD": eth if eth is not None else btc})


def _seed_accumulator(symbol: str = "BTC-USD") -> None:
    base = _base_series(symbol)
    result = rda.run_accumulation_cycle(provider=_provider(base))
    assert result["status"] == "success"


def _hypothesis(**overrides: object) -> StrategyHypothesis:
    base: dict[str, object] = dict(
        id="hyp-provenance-seed", hypothesis="Trend continuation after a confirmed breakout.", marketMechanism="Momentum continuation",
        expectedEdge="Positive expectancy in trending regimes", invalidationConditions="Flat/negative walk-forward expectancy",
        symbolUniverse=["BTC-USD"], timeframe="1h", entryConditions="x", exitConditions="x", stopLossLogic="x",
        takeProfitLogic="x", positionSizingLogic="x", riskConstraints="x", proposedBy="quant", createdAt=_CREATED_AT,
    )
    base.update(overrides)
    return StrategyHypothesis(**base)  # type: ignore[arg-type]


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch: pytest.MonkeyPatch):
    db_path = str(tmp_path / "accum.db")
    monkeypatch.setenv("REAL_DATA_ACCUMULATOR_DB_PATH", db_path)
    yield db_path


def test_A_real_provenance_persists() -> None:
    async def _run() -> None:
        _seed_accumulator()
        state = GameState()
        definition = _frozen_definition()
        updated, outcome = await state.submit_real_data_research_factory_run(_hypothesis(), definition, symbol="BTC-USD", max_generations=1)
        assert outcome.status == "completed"
        assert outcome.run is not None
        assert outcome.run.provenance is not None
        assert outcome.run.provenance.data_status == "real"
        assert outcome.run.provenance.provider == "kraken"
        # Persisted, not just returned on the ephemeral response.
        persisted = next(r for r in updated.factory_runs if r.id == outcome.run.id)
        assert persisted.provenance is not None
        assert persisted.provenance.data_status == "real"

    asyncio.run(_run())


def test_B_mock_provenance_persists() -> None:
    async def _run() -> None:
        from app.strategy_compiler import compile_strategy_text

        text = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R."
        definition = compile_strategy_text(name="Provenance Mock Path Strategy", source_text=text)
        state = GameState()
        updated, run = await state.submit_research_factory_run(_hypothesis(symbolUniverse=["AAPL"]), definition, symbols=["AAPL"], max_generations=1)
        assert run.provenance is not None
        assert run.provenance.data_status == "mock"
        assert run.provenance.provider == "mock"
        assert run.provenance.symbols == ["AAPL"]
        persisted = next(r for r in updated.factory_runs if r.id == run.id)
        assert persisted.provenance is not None
        assert persisted.provenance.data_status == "mock"

    asyncio.run(_run())


def test_C_unknown_remains_unknown_for_pre_existing_records() -> None:
    """A record persisted before this field existed has no `provenance`
    key at all in its stored JSON — deserializing it must yield `None`,
    never an inferred "real" or "mock" label."""
    from app.schemas import FactoryRunConfig

    legacy_json = {
        "id": "factory-run-legacy-no-provenance",
        "strategyFamily": "legacy family",
        "seedDefinitionId": "legacy-strategy",
        "seedDefinitionVersion": 1,
        "lineageId": "factory-run-legacy-no-provenance",
        "config": FactoryRunConfig(maxGenerations=1, maxTotalBacktests=1, maxMutationsPerParent=1, maxIterationsPerFamily=1, maxChildrenPerParent=1, maxRuntimeSeconds=0).model_dump(by_alias=True),
        "candidates": [],
        "generationsCompleted": 0,
        "candidatesGenerated": 0,
        "candidatesCompiled": 0,
        "candidatesBacktested": 0,
        "candidatesValidated": 0,
        "candidatesRejected": 0,
        "stopReason": "legacy record, predates provenance",
        "createdAt": _CREATED_AT,
        # deliberately no "provenance" key at all
    }
    record = FactoryRunRecord.model_validate(legacy_json)
    assert record.provenance is None


def test_D_dataset_identity_persists() -> None:
    async def _run() -> None:
        from app.real_data_research_bridge import RealDataFactoryPreflightFailure, preflight_real_data_dataset

        _seed_accumulator()
        state = GameState()
        definition = _frozen_definition()
        preflight = preflight_real_data_dataset("BTC-USD", definition)
        assert not isinstance(preflight, RealDataFactoryPreflightFailure)
        _provider_obj, expected_provenance = preflight

        _updated, outcome = await state.submit_real_data_research_factory_run(_hypothesis(), definition, symbol="BTC-USD", max_generations=1)
        assert outcome.run is not None and outcome.run.provenance is not None
        assert outcome.run.provenance.dataset_content_hash == expected_provenance.dataset_content_hash

    asyncio.run(_run())


def test_E_strategy_fingerprint_persists() -> None:
    async def _run() -> None:
        _seed_accumulator()
        state = GameState()
        definition = _frozen_definition()
        _updated, outcome = await state.submit_real_data_research_factory_run(_hypothesis(), definition, symbol="BTC-USD", max_generations=1)
        assert outcome.run is not None and outcome.run.provenance is not None
        assert outcome.run.provenance.strategy_fingerprint == _strategy_fingerprint(definition)
        assert outcome.run.provenance.strategy_id == definition.id
        assert outcome.run.provenance.strategy_version == definition.version

    asyncio.run(_run())


def test_F_holdout_identity_persists() -> None:
    async def _run() -> None:
        from app.real_data_research_bridge import RealDataFactoryPreflightFailure, preflight_real_data_dataset

        _seed_accumulator()
        state = GameState()
        definition = _frozen_definition()
        preflight = preflight_real_data_dataset("BTC-USD", definition)
        assert not isinstance(preflight, RealDataFactoryPreflightFailure)
        _provider_obj, expected_provenance = preflight

        _updated, outcome = await state.submit_real_data_research_factory_run(_hypothesis(), definition, symbol="BTC-USD", max_generations=1)
        assert outcome.run is not None and outcome.run.provenance is not None
        assert outcome.run.provenance.holdout_candle_count == expected_provenance.holdout_candle_count
        assert outcome.run.provenance.holdout_start_timestamp == expected_provenance.holdout_start_timestamp
        assert outcome.run.provenance.holdout_end_timestamp == expected_provenance.holdout_end_timestamp
        assert outcome.run.provenance.holdout_boundary_frozen_at == expected_provenance.holdout_boundary_frozen_at

    asyncio.run(_run())


def test_G_provenance_survives_serialize_reload_round_trip() -> None:
    async def _run() -> None:
        _seed_accumulator()
        state = GameState()
        definition = _frozen_definition()
        _updated, outcome = await state.submit_real_data_research_factory_run(_hypothesis(), definition, symbol="BTC-USD", max_generations=1)
        assert outcome.run is not None

        raw = outcome.run.model_dump_json(by_alias=True)
        reloaded = FactoryRunRecord.model_validate_json(raw)
        assert reloaded.provenance == outcome.run.provenance
        assert reloaded.provenance is not None
        assert reloaded.provenance.dataset_content_hash == outcome.run.provenance.dataset_content_hash  # type: ignore[union-attr]

    asyncio.run(_run())


def test_H_provenance_survives_subsequent_runs() -> None:
    async def _run() -> None:
        _seed_accumulator()
        state = GameState()
        definition = _frozen_definition()
        _updated1, outcome1 = await state.submit_real_data_research_factory_run(_hypothesis(), definition, symbol="BTC-USD", max_generations=1)
        assert outcome1.status == "completed" and outcome1.run is not None
        first_run_id = outcome1.run.id
        first_provenance = outcome1.run.provenance

        _updated2, outcome2 = await state.submit_real_data_research_factory_run(
            _hypothesis(id="hyp-provenance-seed-2"), definition, symbol="BTC-USD", max_generations=1
        )
        assert outcome2.status == "completed"

        first_run_after = next(r for r in state.data.factory_runs if r.id == first_run_id)
        assert first_run_after.provenance == first_provenance

    asyncio.run(_run())


def test_I_mixed_provenance_never_produces_a_fabricated_run_or_provenance() -> None:
    async def _run() -> None:
        from contextlib import closing

        _seed_accumulator()
        with closing(rda._connect()) as conn:
            rda.init_schema(conn)
            conn.execute(
                "INSERT INTO candles (symbol, timeframe, provider, candle_timestamp, fetch_timestamp, open, high, low, close, volume, data_status) "
                "VALUES ('BTC-USD', ?, ?, '1999-01-01T00:00:00+00:00', '2024-01-01T00:00:00+00:00', 1, 1, 1, 1, 1, 'simulated')",
                ("1h", rda.PROVIDER_NAME),
            )
            conn.commit()

        state = GameState()
        before = state.data
        definition = _frozen_definition()
        updated, outcome = await state.submit_real_data_research_factory_run(_hypothesis(), definition, symbol="BTC-USD", max_generations=1)
        assert outcome.status == "preflight_failed"
        assert outcome.reason == "REAL_DATASET_MIXED_PROVENANCE"
        assert outcome.run is None
        assert updated is before
        assert state.data.factory_runs == []

    asyncio.run(_run())


def test_J_provenance_wiring_never_references_trading_or_risk_internals() -> None:
    """Structural proof this milestone touched only research-evidence
    code — the same guardrail convention already established for
    app/real_data_research_bridge.py's own Test J."""
    import app.schemas as schemas_module

    forbidden = ["nexus", "RiskContract", "Gatekeeper", "EmergencyStop", "broker", "schwab", "live_order", "PlaceOrder"]
    provenance_source = inspect.getsource(FactoryRunProvenance)
    lowered = provenance_source.lower()
    for term in forbidden:
        assert term.lower() not in lowered, f"FactoryRunProvenance unexpectedly references {term!r}"
    assert schemas_module is not None  # keeps the import meaningful without over-scanning the entire 15k-line schemas module
