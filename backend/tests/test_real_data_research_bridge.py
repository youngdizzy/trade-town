"""Covers app/real_data_research_bridge.py — CEO directive "TradeTown —
Real-Data Strategy Factory Integration & Holdout Enforcement 1.0."

Same isolated-database convention `tests/test_real_data_accumulator.py`
already established: an autouse fixture points
`REAL_DATA_ACCUMULATOR_DB_PATH` at a fresh `tmp_path` file per test, and
`run_accumulation_cycle()` (unmodified) is used to build a real,
frozen-holdout accumulator fixture via a network-free `_FixedProvider`
test double — never the real network, never a second, hand-rolled
accumulator schema. Every test below exercises the real
`preflight_real_data_dataset()`/`run_real_data_factory_cycle()` entry
points directly; nothing here mocks the bridge module itself.
"""
from __future__ import annotations

import dataclasses
from contextlib import closing

import pytest

from app import real_data_accumulator as rda
from app.market_data import Candle, MockMarketDataProvider
from app.real_data_research_bridge import (
    DevelopmentOnlyRealDataProvider,
    RealDataFactoryPreflightFailure,
    preflight_real_data_dataset,
    read_holdout_candles_for_final_evaluation,
    run_real_data_factory_cycle,
)
from app.research_factory import run_research_factory_cycle
from app.schemas import StrategyHypothesis
from app.strategy_registry import default_researchable_strategies

_CREATED_AT = "2024-01-01T00:00:00+00:00"


def _frozen_definition():
    _strategies, registry = default_researchable_strategies()
    return registry[rda.STRATEGY_DEFINITION_ID][0]


def _historical(candles: list[Candle]) -> list[Candle]:
    """Same relabeling convention as test_real_data_accumulator.py's own
    `_historical()` — adapts `MockMarketDataProvider`'s deterministic
    output into TEST FIXTURE data shaped like a real provider's
    response; never used outside this test file to claim real data."""
    return [dataclasses.replace(c, data_status="historical") for c in candles]


def _base_series(symbol: str, count: int = 3000) -> list[Candle]:
    return _historical(MockMarketDataProvider().get_candles(symbol, "1h", count))


class _FixedProvider:
    """Network-free test double for `KrakenMarketDataProvider`, same
    shape as test_real_data_accumulator.py's own — a real
    `app.market_data.MarketDataProvider` is not subclassed here because
    `run_accumulation_cycle()` only calls `get_candles()`. Auto-retags
    every returned candle to the REQUESTED timeframe (same rationale as
    test_real_data_accumulator.py's own `_FixedProvider` — see that
    module's docstring): `_seed_accumulator()` below now accumulates
    both "1h" and "4h" per symbol, and every test in this file is
    exercising bridge-level mechanics that apply identically regardless
    of timeframe."""

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


def _seed_accumulator(symbol: str = "BTC-USD") -> None:
    """Real accumulation + real holdout freeze via the unmodified
    `run_accumulation_cycle()` — never a hand-inserted row bypassing the
    accumulator's own real logic."""
    base = _base_series(symbol)
    result = rda.run_accumulation_cycle(provider=_provider(base))
    assert result["status"] == "success"


def _run_kwargs(definition, **overrides: object) -> dict[str, object]:
    base: dict[str, object] = dict(
        compiled_strategy_registry={definition.id: [definition]},
        quant_research_experiments=[],
        research_iterations=[],
        research_lessons=[],
        failed_archive=[],
        champion_history=[],
        risk_per_trade_pct=2.0,
        run_id="real-data-factory-run-test",
        created_at=_CREATED_AT,
        max_generations=1,
        max_total_backtests=2,
    )
    base.update(overrides)
    return base


# --- Test A: accumulated real data reaches the Factory ---------------------


class TestAccumulatedDataReachesFactory:
    def test_development_candle_count_matches_accumulator_exactly(self) -> None:
        _seed_accumulator()
        definition = _frozen_definition()
        with closing(rda._connect()) as conn:
            rda.init_schema(conn)
            all_candles = conn.execute(
                "SELECT candle_timestamp FROM candles WHERE symbol=? AND timeframe=? AND provider=?", ("BTC-USD", "1h", rda.PROVIDER_NAME)
            ).fetchall()
            boundary = conn.execute(
                "SELECT holdout_start_timestamp, holdout_end_timestamp FROM holdout_boundary WHERE symbol=? AND timeframe=? AND strategy_id=? AND strategy_version=?",
                ("BTC-USD", "1h", definition.id, definition.version),
            ).fetchone()
        holdout_start, holdout_end = boundary
        expected_development = sum(1 for (ts,) in all_candles if not (holdout_start <= ts <= holdout_end))

        outcome = run_real_data_factory_cycle(_hypothesis(), definition, symbol="BTC-USD", **_run_kwargs(definition))
        assert outcome.status == "completed"
        assert outcome.provenance is not None
        assert outcome.provenance.development_candle_count == expected_development
        assert outcome.provenance.provider == "kraken"
        assert outcome.provenance.data_status == "real"
        # The real Factory run itself actually tested exactly this many
        # real candles — not a mock default, not an invented number.
        assert outcome.new_iterations
        assert outcome.new_iterations[0].experiment.candles_per_symbol == expected_development


# --- Test B: provenance survives ---------------------------------------


class TestProvenanceSurvives:
    def test_provenance_fields_are_internally_consistent(self) -> None:
        _seed_accumulator()
        definition = _frozen_definition()
        preflight = preflight_real_data_dataset("BTC-USD", definition)
        assert not isinstance(preflight, RealDataFactoryPreflightFailure)
        provider, provenance = preflight

        with closing(rda._connect()) as conn:
            rda.init_schema(conn)
            total = conn.execute(
                "SELECT COUNT(*) FROM candles WHERE symbol=? AND timeframe=? AND provider=?", ("BTC-USD", "1h", rda.PROVIDER_NAME)
            ).fetchone()[0]

        assert provenance.development_candle_count + provenance.holdout_candle_count == total
        development_candles = provider.get_candles("BTC-USD", "1h", 10**9)
        assert provenance.dataset_start_timestamp == development_candles[0].timestamp
        assert provenance.dataset_end_timestamp == development_candles[-1].timestamp
        assert provenance.strategy_fingerprint == rda._strategy_fingerprint(definition)


# --- Test C: mock/real mixing fails -----------------------------------


class TestMixedProvenanceFailsClosed:
    def test_a_single_non_historical_row_blocks_the_whole_dataset(self) -> None:
        _seed_accumulator()
        definition = _frozen_definition()
        with closing(rda._connect()) as conn:
            rda.init_schema(conn)
            conn.execute(
                "INSERT INTO candles (symbol, timeframe, provider, candle_timestamp, fetch_timestamp, open, high, low, close, volume, data_status) "
                "VALUES ('BTC-USD', ?, ?, '1999-01-01T00:00:00+00:00', '2024-01-01T00:00:00+00:00', 1, 1, 1, 1, 1, 'simulated')",
                ("1h", rda.PROVIDER_NAME),
            )
            conn.commit()

        outcome = run_real_data_factory_cycle(_hypothesis(), definition, symbol="BTC-USD", **_run_kwargs(definition))
        assert outcome.status == "preflight_failed"
        assert outcome.reason == "REAL_DATASET_MIXED_PROVENANCE"
        assert outcome.run is None
        assert outcome.new_iterations is None
        assert outcome.provenance is None


# --- Test F (directive Section 23): fingerprint mismatch fails closed ------


class TestFingerprintMismatchFailsClosed:
    def test_same_id_and_version_but_different_rules_is_rejected(self) -> None:
        """The holdout boundary lookup keys on (symbol, strategy_id,
        strategy_version) alone — a caller supplying a definition that
        shares that identity but carries DIFFERENT actual rules
        (different source_text, hence a different real fingerprint)
        must never silently inherit a holdout boundary frozen for the
        real accumulated strategy."""
        _seed_accumulator()
        frozen = _frozen_definition()
        mismatched = frozen.model_copy(update={"source_text": frozen.source_text + " (a materially different rule set)"})
        assert rda._strategy_fingerprint(mismatched) != rda._strategy_fingerprint(frozen)

        outcome = run_real_data_factory_cycle(_hypothesis(), mismatched, symbol="BTC-USD", **_run_kwargs(mismatched))
        assert outcome.status == "preflight_failed"
        assert outcome.reason == "REAL_DATA_PROVENANCE_INVALID"
        assert outcome.run is None
        assert outcome.new_iterations is None
        assert outcome.provenance is None

    def test_an_id_version_pair_the_accumulator_never_recorded_a_fingerprint_for_is_rejected(self) -> None:
        """Defense in depth: even if a holdout_boundary row somehow
        existed with no matching strategy_fingerprint row (never
        possible via the real accumulator's own freeze path, which
        always records both together), this must fail closed rather
        than silently trusting an unverifiable identity."""
        _seed_accumulator()
        frozen = _frozen_definition()
        with closing(rda._connect()) as conn:
            rda.init_schema(conn)
            conn.execute("DELETE FROM strategy_fingerprint WHERE strategy_id = ? AND strategy_version = ?", (frozen.id, frozen.version))
            conn.commit()

        outcome = run_real_data_factory_cycle(_hypothesis(), frozen, symbol="BTC-USD", **_run_kwargs(frozen))
        assert outcome.status == "preflight_failed"
        assert outcome.reason == "REAL_DATA_PROVENANCE_INVALID"


# --- Test D: real-unavailable never falls back to mock ------------------


class TestRealUnavailableNeverFallsBackToMock:
    def test_empty_accumulator_makes_zero_calls_into_the_factory(self, monkeypatch: pytest.MonkeyPatch) -> None:
        definition = _frozen_definition()
        calls: list[object] = []

        def _spy(*args: object, **kwargs: object):
            calls.append((args, kwargs))
            return run_research_factory_cycle(*args, **kwargs)  # pragma: no cover - never reached

        monkeypatch.setattr("app.real_data_research_bridge.run_research_factory_cycle", _spy)
        outcome = run_real_data_factory_cycle(_hypothesis(), definition, symbol="BTC-USD", **_run_kwargs(definition))
        assert outcome.status == "preflight_failed"
        assert outcome.reason == "REAL_DATA_UNAVAILABLE"
        assert calls == []  # never substituted mock data by falling through to the real Factory


# --- Test E: holdout structurally cannot enter development optimization ----


class TestHoldoutStructurallyExcluded:
    def test_provider_never_serves_a_holdout_candle(self) -> None:
        _seed_accumulator()
        definition = _frozen_definition()
        preflight = preflight_real_data_dataset("BTC-USD", definition)
        assert not isinstance(preflight, RealDataFactoryPreflightFailure)
        provider, provenance = preflight
        assert isinstance(provider, DevelopmentOnlyRealDataProvider)

        with closing(rda._connect()) as conn:
            rda.init_schema(conn)
            boundary = conn.execute(
                "SELECT holdout_start_timestamp, holdout_end_timestamp FROM holdout_boundary WHERE symbol=? AND timeframe=? AND strategy_id=? AND strategy_version=?",
                ("BTC-USD", "1h", definition.id, definition.version),
            ).fetchone()
        holdout_start, holdout_end = boundary

        served = provider.get_candles("BTC-USD", "1h", 10**9)
        assert len(served) == provenance.development_candle_count
        for candle in served:
            assert not (holdout_start <= candle.timestamp <= holdout_end)

        # Even a small `limit` slices from the tail of the ALREADY
        # holdout-free development list — never reaches into holdout.
        small_slice = provider.get_candles("BTC-USD", "1h", 5)
        assert len(small_slice) == 5
        for candle in small_slice:
            assert not (holdout_start <= candle.timestamp <= holdout_end)


# --- Test F: holdout provenance survives partition ------------------------


class TestHoldoutPartitionIntegrity:
    def test_holdout_read_is_disjoint_from_development_and_matches_count(self) -> None:
        _seed_accumulator()
        definition = _frozen_definition()
        preflight = preflight_real_data_dataset("BTC-USD", definition)
        assert not isinstance(preflight, RealDataFactoryPreflightFailure)
        provider, provenance = preflight
        development = provider.get_candles("BTC-USD", "1h", 10**9)

        holdout = read_holdout_candles_for_final_evaluation("BTC-USD", definition)
        assert not isinstance(holdout, RealDataFactoryPreflightFailure)
        assert len(holdout) == provenance.holdout_candle_count
        development_timestamps = {c.timestamp for c in development}
        holdout_timestamps = {c.timestamp for c in holdout}
        assert development_timestamps.isdisjoint(holdout_timestamps)


# --- Test G: model validation sees real provenance -------------------------


class TestModelValidationSeesRealProvenance:
    def test_resulting_experiment_is_tagged_external_real_provider(self) -> None:
        _seed_accumulator()
        definition = _frozen_definition()
        outcome = run_real_data_factory_cycle(_hypothesis(), definition, symbol="BTC-USD", **_run_kwargs(definition))
        assert outcome.status == "completed"
        assert outcome.new_iterations
        experiment = outcome.new_iterations[0].experiment
        assert experiment.dataset_metadata is not None
        assert experiment.dataset_metadata.source == "external_real_provider"
        assert "real historical market data" in experiment.data_honesty_note


# --- Test H: empty accumulator produces an honest, distinguishable blocked shape ---


class TestEmptyAccumulatorHonestBlockedStatus:
    def test_blocked_outcome_is_shaped_as_a_non_result_not_a_fabricated_success(self) -> None:
        definition = _frozen_definition()
        outcome = run_real_data_factory_cycle(_hypothesis(), definition, symbol="BTC-USD", **_run_kwargs(definition))
        assert outcome.status == "preflight_failed"
        assert outcome.reason == "REAL_DATA_UNAVAILABLE"
        assert "UNAVAILABLE" in outcome.detail
        assert outcome.run is None
        assert outcome.updated_registry is None
        assert outcome.new_iterations is None
        assert outcome.new_lessons is None
        assert outcome.provenance is None


# --- Test I: the existing mock Factory path is unchanged --------------------


class TestExistingMockFactoryPathUnchanged:
    def test_omitting_market_data_provider_still_uses_the_mock_provider(self) -> None:
        from app.strategy_compiler import compile_strategy_text

        text = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R."
        definition = compile_strategy_text(name="Mock Path Regression Strategy", source_text=text)
        registry = {definition.id: [definition]}
        run, _updated_registry, iterations, lessons = run_research_factory_cycle(
            _hypothesis(symbolUniverse=["AAPL"]), definition, compiled_strategy_registry=registry, quant_research_experiments=[],
            research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
            run_id="mock-path-regression", created_at=_CREATED_AT, symbols=["AAPL"], max_generations=1,
        )
        assert run.candidates_generated >= 1
        if iterations:
            assert iterations[0].experiment.dataset_metadata is None or iterations[0].experiment.dataset_metadata.source != "external_real_provider"


# --- Test J: the trading firewall is untouched ------------------------------


class TestTradingFirewallUntouched:
    def test_bridge_module_never_references_trading_or_risk_internals(self) -> None:
        import inspect

        from app import real_data_research_bridge as bridge

        source = inspect.getsource(bridge)
        forbidden_substrings = ["nexus", "RiskContract", "Gatekeeper", "EmergencyStop", "broker", "schwab", "live_order", "PlaceOrder"]
        lowered = source.lower()
        for forbidden in forbidden_substrings:
            assert forbidden.lower() not in lowered, f"real_data_research_bridge.py unexpectedly references {forbidden!r}"
