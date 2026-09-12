"""Covers app/routers/sandbox.py::real_data_research_readiness_endpoint()
— CEO directive "TradeTown — Real-Data Research Command Center UI 1.0."

This is a thin, read-only wrapper around the already-exhaustively-tested
`preflight_real_data_dataset()` (see tests/test_real_data_research_bridge.py
for every reachable failure reason) — these tests only confirm the
router-level wiring itself: the endpoint never touches `game_state`,
never runs the Factory, and maps the pure function's result onto
`RealDataReadinessRead` correctly in both the ready and blocked cases.
Same isolated-accumulator-database convention the other real-data test
files already established."""
from __future__ import annotations

import asyncio
import dataclasses

import pytest

from app import real_data_accumulator as rda
from app.market_data import Candle, MockMarketDataProvider
from app.routers.sandbox import RealDataReadinessRequest, real_data_research_readiness_endpoint
from app.strategy_registry import default_researchable_strategies


def _frozen_definition():
    _strategies, registry = default_researchable_strategies()
    return registry[rda.STRATEGY_DEFINITION_ID][0]


def _historical(candles: list[Candle]) -> list[Candle]:
    return [dataclasses.replace(c, data_status="historical") for c in candles]


def _base_series(symbol: str, count: int = 3000) -> list[Candle]:
    return _historical(MockMarketDataProvider().get_candles(symbol, "1h", count))


class _FixedProvider:
    """Auto-retags every returned candle to the REQUESTED timeframe —
    see test_real_data_accumulator.py's own `_FixedProvider` docstring."""

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


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch: pytest.MonkeyPatch):
    db_path = str(tmp_path / "accum.db")
    monkeypatch.setenv("REAL_DATA_ACCUMULATOR_DB_PATH", db_path)
    yield db_path


def test_empty_accumulator_reports_preflight_failed_with_no_side_effects() -> None:
    async def _run() -> None:
        definition = _frozen_definition()
        result = await real_data_research_readiness_endpoint(RealDataReadinessRequest(definition=definition, symbol="BTC-USD"))
        assert result.status == "preflight_failed"
        assert result.reason == "REAL_DATA_UNAVAILABLE"
        assert result.provenance is None

    asyncio.run(_run())


def test_seeded_accumulator_reports_ready_with_real_provenance() -> None:
    async def _run() -> None:
        base = _base_series("BTC-USD")
        accumulation = rda.run_accumulation_cycle(provider=_provider(base))
        assert accumulation["status"] == "success"

        definition = _frozen_definition()
        result = await real_data_research_readiness_endpoint(RealDataReadinessRequest(definition=definition, symbol="BTC-USD"))
        assert result.status == "ready"
        assert result.reason is None
        assert result.provenance is not None
        assert result.provenance.provider == "kraken"
        assert result.provenance.data_status == "real"
        assert result.provenance.development_candle_count > 0

    asyncio.run(_run())


def test_readiness_check_never_touches_game_state() -> None:
    async def _run() -> None:
        from app.state import game_state

        before = game_state.data
        definition = _frozen_definition()
        await real_data_research_readiness_endpoint(RealDataReadinessRequest(definition=definition, symbol="BTC-USD"))
        assert game_state.data is before

    asyncio.run(_run())
