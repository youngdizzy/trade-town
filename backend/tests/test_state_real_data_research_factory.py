"""Covers app/state.py::GameState.submit_real_data_research_factory_run()
— CEO directive "TradeTown — Real-Data Strategy Factory Integration &
Holdout Enforcement 1.0." Same isolated-accumulator-database convention
tests/test_real_data_research_bridge.py already established; these
tests focus specifically on the GameState wiring: a preflight failure
must leave `self.data` byte-for-byte unchanged, and a completed run
must merge through the exact same `_merge_factory_run_result()` path
`submit_research_factory_run()` already uses — never duplicating a
pre-existing iteration/lesson (the double-counting bug caught and fixed
during this milestone's own implementation)."""
from __future__ import annotations

import asyncio
import dataclasses

import pytest

from app import real_data_accumulator as rda
from app.market_data import Candle, MockMarketDataProvider
from app.real_data_research_bridge import RealDataFactoryRunOutcome
from app.schemas import StrategyHypothesis
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
    for why: `_seed_accumulator()` below now accumulates both "1h" and
    "4h" per symbol, and every test in this file exercises GameState
    wiring that applies identically regardless of timeframe."""

    def __init__(self, candles_by_symbol: dict[str, list[Candle]]) -> None:
        self._candles_by_symbol = candles_by_symbol

    def get_quote(self, symbol: str):  # pragma: no cover - unused by this suite
        raise NotImplementedError

    def get_candles(self, symbol: str, timeframe: str, limit: int, *, end_time=None, anchor_price=None) -> list[Candle]:
        candles = self._candles_by_symbol[symbol]
        windowed = candles[-limit:] if limit > 0 else list(candles)
        # Retag both timeframe AND symbol to what was actually
        # requested — see test_real_data_accumulator.py's identical
        # fixture for why: `_provider(btc)` reuses BTC-tagged Candle
        # objects for the "ETH-USD" key too, which a real
        # `symbol_mismatch` check now fails closed on.
        return [dataclasses.replace(c, timeframe=timeframe, symbol=symbol) for c in windowed]


def _provider(btc: list[Candle], eth: list[Candle] | None = None) -> _FixedProvider:
    return _FixedProvider({"BTC-USD": btc, "ETH-USD": eth if eth is not None else btc})


def _seed_accumulator(symbol: str = "BTC-USD") -> None:
    base = _base_series(symbol)
    result = rda.run_accumulation_cycle(provider=_provider(base))
    assert result["status"] == "success"


def _hypothesis(**overrides: object) -> StrategyHypothesis:
    base: dict[str, object] = dict(
        id="hyp-real-data-seed", hypothesis="Trend continuation after a confirmed breakout.", marketMechanism="Momentum continuation",
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


def test_preflight_failure_leaves_state_byte_for_byte_unchanged() -> None:
    async def _run() -> None:
        state = GameState()
        before = state.data
        definition = _frozen_definition()
        updated, outcome = await state.submit_real_data_research_factory_run(_hypothesis(), definition, symbol="BTC-USD", max_generations=1)
        assert isinstance(outcome, RealDataFactoryRunOutcome)
        assert outcome.status == "preflight_failed"
        assert outcome.reason == "REAL_DATA_UNAVAILABLE"
        assert updated is before
        assert state.data is before
        assert state.data.factory_runs == []
        assert state.data.research_iterations == []
        assert state.data.research_lessons == []

    asyncio.run(_run())


def test_completed_run_merges_exactly_like_the_mock_path() -> None:
    async def _run() -> None:
        _seed_accumulator()
        state = GameState()
        definition = _frozen_definition()
        updated, outcome = await state.submit_real_data_research_factory_run(
            _hypothesis(), definition, symbol="BTC-USD", max_generations=1, max_total_backtests=2
        )
        assert outcome.status == "completed"
        assert outcome.run is not None
        assert outcome.run.id in [r.id for r in updated.factory_runs]
        assert outcome.run.id in [r.id for r in state.data.factory_runs]
        # No double-counting regression: exactly as many iterations/lessons
        # were merged as this one run itself produced — never the whole
        # snapshot re-appended a second time.
        assert len(state.data.research_iterations) == len(outcome.new_iterations or [])
        assert len(state.data.research_lessons) == len(outcome.new_lessons or [])
        assert outcome.provenance is not None
        assert outcome.provenance.data_status == "real"

    asyncio.run(_run())


def test_two_sequential_runs_never_duplicate_prior_iterations() -> None:
    async def _run() -> None:
        _seed_accumulator()
        state = GameState()
        definition = _frozen_definition()
        _updated1, outcome1 = await state.submit_real_data_research_factory_run(
            _hypothesis(), definition, symbol="BTC-USD", max_generations=1, max_total_backtests=2
        )
        assert outcome1.status == "completed"
        count_after_first = len(state.data.research_iterations)

        _updated2, outcome2 = await state.submit_real_data_research_factory_run(
            _hypothesis(id="hyp-real-data-seed-2"), definition, symbol="BTC-USD", max_generations=1, max_total_backtests=2
        )
        assert outcome2.status == "completed"
        count_after_second = len(state.data.research_iterations)
        assert count_after_second == count_after_first + len(outcome2.new_iterations or [])

    asyncio.run(_run())


def test_mixed_provenance_preflight_failure_also_leaves_state_unchanged() -> None:
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
        assert updated is before
        assert state.data is before

    asyncio.run(_run())
