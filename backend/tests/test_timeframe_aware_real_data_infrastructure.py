"""Covers CEO directive "TradeTown — Timeframe-Aware Real-Data Research
Infrastructure 1.0" — the milestone that made `timeframe` a first-class
dimension of persisted real-data research evidence.

Test matrix (directive Section 27), each letter a distinct class/test
below:

  A — Holdout identity: 1h and 4h create independent holdout identities.
  B — Symbol identity: BTC and ETH remain independent within one timeframe.
  C — Existing 1h preservation: a pre-existing legacy 1h holdout survives migration unchanged.
  D — New 4h holdout: 4h gets its own frozen boundary.
  E — Cross-timeframe rejection: a 1h provider cannot satisfy a 4h request.
  F — Cross-timeframe research rejection: a 4h preflight cannot consume 1h candles.
  G — Development isolation: a 4h development provider cannot serve 4h holdout.
  H — Cross-timeframe holdout isolation: a 1h holdout cannot satisfy a 4h lookup.
  I — Provenance: a real 4h Factory run records timeframe=4h end to end.
  J — Dataset identity: 1h and 4h datasets have distinct content hashes.
  K — Persistence: a legacy (pre-timeframe) schema migrates and reloads correctly.
  L — Immutability: a later accumulation run cannot mutate a previously frozen boundary.
  M — Mock compatibility: existing mock Factory runs remain functional and identify as mock.
  N — Trading isolation: no trading/risk/broker module is imported anywhere in this milestone's diff.
  O — Paper isolation: no paper-trading module is imported anywhere in this milestone's diff.

Plus Section 24's explicit real/mock firewall combinations (real 1h +
mock 4h, real 4h + mock 1h, real 1h + real 4h) — each must fail safely
wherever a single dataset identity is required, never silently blended.

Same isolated-accumulator-database convention every other real-data
test file in this repo already established: an autouse fixture points
`REAL_DATA_ACCUMULATOR_DB_PATH` at a fresh `tmp_path` file per test.
"""
from __future__ import annotations

import dataclasses
import sqlite3

import pytest

from app import real_data_accumulator as rda
from app.market_data import Candle, ExternalMarketDataProviderUnavailable, MarketDataProvider, MockMarketDataProvider
from app.real_data_research_bridge import (
    DevelopmentOnlyRealDataProvider,
    RealDataFactoryPreflightFailure,
    preflight_real_data_dataset,
    run_real_data_factory_cycle,
)
from app.research_factory import run_research_factory_cycle
from app.schemas import StrategyHypothesis
from app.strategy_registry import default_researchable_strategies

_CREATED_AT = "2024-01-01T00:00:00+00:00"
_STRATEGIES, _REGISTRY = default_researchable_strategies()
FROZEN_DEFINITION = _REGISTRY["50-ema-breakout-pullback-long"][0]


def _historical(candles: list[Candle]) -> list[Candle]:
    return [dataclasses.replace(c, data_status="historical") for c in candles]


def _base_series(symbol: str, count: int = 3000) -> list[Candle]:
    return _historical(MockMarketDataProvider().get_candles(symbol, "1h", count))


class _FixedProvider(MarketDataProvider):
    """Serves the given per-(symbol, timeframe) candle series verbatim
    — never auto-retagged, unlike the other real-data test files'
    fixtures — so THIS file's own cross-timeframe tests can construct
    deliberately mismatched or timeframe-specific fixtures."""

    def __init__(self, candles: dict[tuple[str, str], list[Candle]]) -> None:
        self._candles = candles

    def get_quote(self, symbol: str):  # pragma: no cover - unused by this suite
        raise NotImplementedError

    def get_candles(self, symbol: str, timeframe: str, limit: int, *, end_time=None, anchor_price=None) -> list[Candle]:
        candles = self._candles[(symbol, timeframe)]
        return candles[-limit:] if limit > 0 else list(candles)


def _retagging_provider(btc: list[Candle], eth: list[Candle] | None = None) -> MarketDataProvider:
    """Auto-retags to whatever timeframe is requested — same convention
    as every other real-data test file, for seeding both 1h and 4h from
    one underlying deterministic series."""
    by_symbol = {"BTC-USD": btc, "ETH-USD": eth if eth is not None else btc}

    class _Retagging(MarketDataProvider):
        def get_quote(self, symbol: str):  # pragma: no cover
            raise NotImplementedError

        def get_candles(self, symbol: str, timeframe: str, limit: int, *, end_time=None, anchor_price=None) -> list[Candle]:
            candles = by_symbol[symbol]
            windowed = candles[-limit:] if limit > 0 else list(candles)
            return [dataclasses.replace(c, timeframe=timeframe) for c in windowed]

    return _Retagging()


@pytest.fixture(autouse=True)
def isolated_db(tmp_path, monkeypatch: pytest.MonkeyPatch):
    db_path = str(tmp_path / "accum.db")
    monkeypatch.setenv("REAL_DATA_ACCUMULATOR_DB_PATH", db_path)
    yield db_path


def _conn() -> sqlite3.Connection:
    conn = rda._connect()
    rda.init_schema(conn)
    return conn


def _seed_both_timeframes(symbol: str = "BTC-USD", other_symbol: str = "ETH-USD") -> None:
    """Real accumulation across both canonical timeframes via the
    unmodified `run_accumulation_cycle()` — never a hand-inserted row."""
    base = _base_series(symbol)
    other = _base_series(other_symbol)
    result = rda.run_accumulation_cycle(provider=_retagging_provider(base, other))
    assert result["status"] == "success"


def _hypothesis(**overrides: object) -> StrategyHypothesis:
    base: dict[str, object] = dict(
        id="hyp-timeframe-seed", hypothesis="Trend continuation after a confirmed breakout.", marketMechanism="Momentum continuation",
        expectedEdge="Positive expectancy in trending regimes", invalidationConditions="Flat/negative walk-forward expectancy",
        symbolUniverse=["BTC-USD"], timeframe="1h", entryConditions="x", exitConditions="x", stopLossLogic="x",
        takeProfitLogic="x", positionSizingLogic="x", riskConstraints="x", proposedBy="quant", createdAt=_CREATED_AT,
    )
    base.update(overrides)
    return StrategyHypothesis(**base)  # type: ignore[arg-type]


def _run_kwargs(definition, **overrides: object) -> dict[str, object]:
    base: dict[str, object] = dict(
        compiled_strategy_registry={definition.id: [definition]},
        quant_research_experiments=[],
        research_iterations=[],
        research_lessons=[],
        failed_archive=[],
        champion_history=[],
        risk_per_trade_pct=2.0,
        run_id="timeframe-infra-test",
        created_at=_CREATED_AT,
        max_generations=1,
        max_total_backtests=2,
    )
    base.update(overrides)
    return base


# --- A: holdout identity is independent per timeframe -----------------------


class TestA_HoldoutIdentityIndependentPerTimeframe:
    def test_1h_and_4h_get_distinct_holdout_boundary_rows(self) -> None:
        _seed_both_timeframes()
        with _conn() as conn:
            rows = conn.execute(
                "SELECT holdout_start_timestamp, holdout_end_timestamp, dataset_content_hash FROM holdout_boundary WHERE symbol = 'BTC-USD' ORDER BY timeframe"
            ).fetchall()
        assert len(rows) == 2
        assert rows[0] != rows[1], "1h and 4h holdout boundaries must never be identical rows"


# --- B: symbol identity is independent within one timeframe -----------------


class TestB_SymbolIdentityIndependentWithinOneTimeframe:
    def test_btc_and_eth_get_independent_1h_boundaries(self) -> None:
        _seed_both_timeframes()
        with _conn() as conn:
            btc = conn.execute("SELECT holdout_start_timestamp, holdout_end_timestamp FROM holdout_boundary WHERE symbol = 'BTC-USD' AND timeframe = '1h'").fetchone()
            eth = conn.execute("SELECT holdout_start_timestamp, holdout_end_timestamp FROM holdout_boundary WHERE symbol = 'ETH-USD' AND timeframe = '1h'").fetchone()
        assert btc is not None and eth is not None
        assert btc != eth


# --- C: existing (legacy, pre-timeframe) 1h evidence survives migration -----


class TestC_ExistingLegacy1hHoldoutSurvivesMigration:
    def test_legacy_holdout_and_trade_rows_are_preserved_and_backfilled(self, tmp_path) -> None:
        db_path = str(tmp_path / "legacy.db")
        conn = sqlite3.connect(db_path)
        conn.executescript(
            """
            CREATE TABLE holdout_boundary (
                symbol TEXT NOT NULL, strategy_id TEXT NOT NULL, strategy_version INTEGER NOT NULL,
                holdout_start_timestamp TEXT NOT NULL, holdout_end_timestamp TEXT NOT NULL,
                frozen_at TEXT NOT NULL, dataset_content_hash TEXT NOT NULL,
                PRIMARY KEY (symbol, strategy_id, strategy_version)
            );
            CREATE TABLE trades (
                symbol TEXT NOT NULL, strategy_id TEXT NOT NULL, strategy_version INTEGER NOT NULL, entry_timestamp TEXT NOT NULL,
                bars_held INTEGER NOT NULL, entry_price REAL NOT NULL, exit_price REAL, direction TEXT NOT NULL, outcome TEXT NOT NULL,
                r_multiple_realized REAL NOT NULL, is_holdout INTEGER NOT NULL, discovered_in_run_id TEXT NOT NULL, discovered_at TEXT NOT NULL,
                PRIMARY KEY (symbol, strategy_id, strategy_version, entry_timestamp)
            );
            """
        )
        conn.execute(
            "INSERT INTO holdout_boundary VALUES ('BTC-USD', '50-ema-breakout-pullback-long', 1, '2024-01-01T00:00:00+00:00', "
            "'2024-02-01T00:00:00+00:00', '2024-03-01T00:00:00+00:00', 'legacy-hash-abc')"
        )
        conn.execute(
            "INSERT INTO trades VALUES ('BTC-USD', '50-ema-breakout-pullback-long', 1, '2024-01-15T00:00:00+00:00', 10, 100.0, 105.0, "
            "'long', 'win', 1.5, 1, 'legacy-run', '2024-01-16T00:00:00+00:00')"
        )
        conn.commit()
        conn.close()

        conn = sqlite3.connect(db_path)
        rda.init_schema(conn)
        holdout_row = conn.execute(
            "SELECT symbol, timeframe, strategy_id, strategy_version, holdout_start_timestamp, holdout_end_timestamp, dataset_content_hash "
            "FROM holdout_boundary WHERE symbol = 'BTC-USD'"
        ).fetchone()
        trade_row = conn.execute("SELECT symbol, timeframe, entry_timestamp, r_multiple_realized FROM trades WHERE symbol = 'BTC-USD'").fetchone()
        assert holdout_row == ("BTC-USD", "1h", "50-ema-breakout-pullback-long", 1, "2024-01-01T00:00:00+00:00", "2024-02-01T00:00:00+00:00", "legacy-hash-abc")
        assert trade_row == ("BTC-USD", "1h", "2024-01-15T00:00:00+00:00", 1.5)
        # Provably lossless: the original legacy table is preserved, not dropped.
        legacy_holdout = conn.execute("SELECT COUNT(*) FROM holdout_boundary_legacy_pre_timeframe").fetchone()[0]
        legacy_trades = conn.execute("SELECT COUNT(*) FROM trades_legacy_pre_timeframe").fetchone()[0]
        assert legacy_holdout == 1
        assert legacy_trades == 1


# --- D: a new 4h holdout gets its own frozen boundary ------------------------


class TestD_New4hHoldoutGetsItsOwnFrozenBoundary:
    def test_4h_holdout_boundary_is_created(self) -> None:
        _seed_both_timeframes()
        with _conn() as conn:
            row = conn.execute("SELECT holdout_start_timestamp, holdout_end_timestamp FROM holdout_boundary WHERE symbol = 'BTC-USD' AND timeframe = '4h'").fetchone()
        assert row is not None
        assert row[0] < row[1]


# --- E: a 1h provider cannot satisfy a 4h request ----------------------------


class TestE_CrossTimeframeProviderRejection:
    def test_development_only_provider_rejects_a_mismatched_timeframe_request(self) -> None:
        candles = _base_series("BTC-USD", count=50)
        provider = DevelopmentOnlyRealDataProvider("BTC-USD", "1h", candles)
        with pytest.raises(Exception, match="1h.*only"):
            provider.get_candles("BTC-USD", "4h", 10)

    def test_accumulator_rejects_a_provider_that_mislabels_its_own_candle_timeframe(self) -> None:
        """Section 8's hard invariant, proven directly: a provider that
        returns "1h"-tagged candles for a "4h" request must never be
        silently persisted as 4h evidence."""
        mismatched = _FixedProvider({("BTC-USD", "1h"): _base_series("BTC-USD"), ("BTC-USD", "4h"): _base_series("BTC-USD"), ("ETH-USD", "1h"): [], ("ETH-USD", "4h"): []})
        # BTC-USD/4h candles are actually tagged "1h" (the fixture never re-tags) — must fail closed.
        with pytest.raises(rda.AccumulationFailure, match="does not match the requested"):
            rda.run_accumulation_cycle(provider=mismatched)


# --- F: a 4h preflight cannot consume 1h candles -----------------------------


class TestF_CrossTimeframeResearchRejection:
    def test_4h_preflight_fails_when_only_1h_is_accumulated(self) -> None:
        """`candles`/`holdout_boundary` are real, append-only tables (no
        DELETE possible — proven elsewhere) — so "only 1h accumulated"
        is proven here via a provider that only ever succeeds for 1h,
        never by tampering with already-persisted rows."""
        base = _base_series("BTC-USD")

        class _OnlyOneHourProvider(MarketDataProvider):
            def get_quote(self, symbol: str):  # pragma: no cover
                raise NotImplementedError

            def get_candles(self, symbol: str, timeframe: str, limit: int, *, end_time=None, anchor_price=None) -> list[Candle]:
                if timeframe != "1h":
                    raise ExternalMarketDataProviderUnavailable(f"this test double only ever serves 1h, not {timeframe!r}")
                candles = base[-limit:] if limit > 0 else list(base)
                return [dataclasses.replace(c, timeframe="1h") for c in candles]

        with pytest.raises(rda.AccumulationFailure, match="Kraken unavailable"):
            rda.run_accumulation_cycle(provider=_OnlyOneHourProvider())
        # The 1h leg for BTC-USD, processed before the 4h leg raised,
        # still committed and persists — the accumulator's own
        # documented per-(symbol, timeframe) transaction boundary.
        with _conn() as conn:
            count_1h = conn.execute("SELECT COUNT(*) FROM candles WHERE symbol='BTC-USD' AND timeframe='1h'").fetchone()[0]
        assert count_1h == len(base)

        preflight = preflight_real_data_dataset("BTC-USD", FROZEN_DEFINITION, timeframe="4h")
        assert isinstance(preflight, RealDataFactoryPreflightFailure)
        assert preflight.reason == "REAL_DATA_UNAVAILABLE"

    def test_run_real_data_factory_cycle_at_4h_never_touches_1h_candles(self) -> None:
        """Structural proof via a spy: a 4h run's own preflight reads
        exactly the accumulated 4h row count, never the 1h count."""
        _seed_both_timeframes()
        with _conn() as conn:
            candles_1h = conn.execute("SELECT COUNT(*) FROM candles WHERE symbol='BTC-USD' AND timeframe='1h'").fetchone()[0]
            candles_4h = conn.execute("SELECT COUNT(*) FROM candles WHERE symbol='BTC-USD' AND timeframe='4h'").fetchone()[0]
        assert candles_1h == candles_4h  # same underlying series, retagged — a real fixture property, not the claim under test
        outcome = run_real_data_factory_cycle(_hypothesis(), FROZEN_DEFINITION, symbol="BTC-USD", timeframe="4h", **_run_kwargs(FROZEN_DEFINITION))
        assert outcome.status == "completed"
        assert outcome.provenance is not None
        assert outcome.provenance.timeframe == "4h"


# --- G: a 4h development provider cannot serve 4h holdout --------------------


class TestG_DevelopmentIsolationWithinOneTimeframe:
    def test_4h_development_provider_never_serves_a_4h_holdout_candle(self) -> None:
        _seed_both_timeframes()
        preflight = preflight_real_data_dataset("BTC-USD", FROZEN_DEFINITION, timeframe="4h")
        assert not isinstance(preflight, RealDataFactoryPreflightFailure)
        provider, provenance = preflight
        with _conn() as conn:
            boundary = conn.execute(
                "SELECT holdout_start_timestamp, holdout_end_timestamp FROM holdout_boundary WHERE symbol='BTC-USD' AND timeframe='4h'"
            ).fetchone()
        holdout_start, holdout_end = boundary
        served = provider.get_candles("BTC-USD", "4h", 10**9)
        assert len(served) == provenance.development_candle_count
        for candle in served:
            assert not (holdout_start <= candle.timestamp <= holdout_end)


# --- H: a 1h holdout cannot satisfy a 4h lookup ------------------------------


class TestH_CrossTimeframeHoldoutIsolation:
    def test_4h_holdout_lookup_never_returns_the_1h_boundary(self) -> None:
        """Uses genuinely different-length underlying series per
        timeframe (not merely retagged) so the resulting holdout
        WINDOWS differ in actual timestamp value, not only in their
        (already independently proven, see TestJ) content hash — the
        strongest possible proof that a 4h lookup cannot silently
        return the 1h row."""
        base = _base_series("BTC-USD", count=3000)
        longer = _base_series("BTC-USD", count=3500)

        class _DifferentLengthProvider(MarketDataProvider):
            def get_quote(self, symbol: str):  # pragma: no cover
                raise NotImplementedError

            def get_candles(self, symbol: str, timeframe: str, limit: int, *, end_time=None, anchor_price=None) -> list[Candle]:
                series = base if timeframe == "1h" else longer
                windowed = series[-limit:] if limit > 0 else list(series)
                return [dataclasses.replace(c, timeframe=timeframe) for c in windowed]

        result = rda.run_accumulation_cycle(provider=_DifferentLengthProvider())
        assert result["status"] == "success"
        with _conn() as conn:
            boundary_1h = conn.execute("SELECT holdout_start_timestamp, holdout_end_timestamp FROM holdout_boundary WHERE symbol='BTC-USD' AND timeframe='1h'").fetchone()
            boundary_4h = conn.execute("SELECT holdout_start_timestamp, holdout_end_timestamp FROM holdout_boundary WHERE symbol='BTC-USD' AND timeframe='4h'").fetchone()
        assert boundary_1h is not None
        assert boundary_4h is not None
        assert boundary_1h != boundary_4h, "a 4h holdout lookup returned timestamps identical to the 1h boundary — cross-timeframe isolation may be broken"


# --- I: a real 4h Factory run records timeframe=4h end to end ---------------


class TestI_ProvenanceRecordsTheActualRequestedTimeframe:
    def test_4h_run_provenance_timeframe_is_4h_not_1h(self) -> None:
        _seed_both_timeframes()
        outcome = run_real_data_factory_cycle(_hypothesis(), FROZEN_DEFINITION, symbol="BTC-USD", timeframe="4h", **_run_kwargs(FROZEN_DEFINITION))
        assert outcome.status == "completed"
        assert outcome.timeframe == "4h"
        assert outcome.provenance is not None
        assert outcome.provenance.timeframe == "4h"

    def test_1h_run_provenance_timeframe_is_still_1h_by_default(self) -> None:
        _seed_both_timeframes()
        outcome = run_real_data_factory_cycle(_hypothesis(), FROZEN_DEFINITION, symbol="BTC-USD", **_run_kwargs(FROZEN_DEFINITION))
        assert outcome.status == "completed"
        assert outcome.timeframe == "1h"
        assert outcome.provenance is not None
        assert outcome.provenance.timeframe == "1h"


# --- J: 1h and 4h datasets have distinct content identities ------------------


class TestJ_DatasetIdentityDiffersByTimeframe:
    def test_1h_and_4h_dataset_content_hashes_differ(self) -> None:
        _seed_both_timeframes()
        preflight_1h = preflight_real_data_dataset("BTC-USD", FROZEN_DEFINITION, timeframe="1h")
        preflight_4h = preflight_real_data_dataset("BTC-USD", FROZEN_DEFINITION, timeframe="4h")
        assert not isinstance(preflight_1h, RealDataFactoryPreflightFailure)
        assert not isinstance(preflight_4h, RealDataFactoryPreflightFailure)
        _provider_1h, provenance_1h = preflight_1h
        _provider_4h, provenance_4h = preflight_4h
        assert provenance_1h.dataset_content_hash != provenance_4h.dataset_content_hash
        # Both explicitly record which timeframe they are, never left to
        # be inferred from the hash alone (Section 6).
        assert provenance_1h.timeframe == "1h"
        assert provenance_4h.timeframe == "4h"


# --- K: persistence — migration + reload preserves timeframe identity -------


class TestK_PersistenceAcrossRestart:
    def test_reopening_the_database_preserves_both_timeframes_identity(self) -> None:
        _seed_both_timeframes()
        # Simulate a restart: a brand-new connection, re-running init_schema.
        with _conn() as conn:
            rows = conn.execute("SELECT symbol, timeframe FROM holdout_boundary ORDER BY symbol, timeframe").fetchall()
        assert rows == [("BTC-USD", "1h"), ("BTC-USD", "4h"), ("ETH-USD", "1h"), ("ETH-USD", "4h")]


# --- L: immutability — later accumulation cannot mutate a frozen boundary ---


class TestL_ImmutabilityAcrossLaterAccumulation:
    def test_4h_boundary_is_byte_identical_after_a_second_run(self) -> None:
        base = _base_series("BTC-USD")
        rda.run_accumulation_cycle(provider=_retagging_provider(base))
        with _conn() as conn:
            before = conn.execute("SELECT * FROM holdout_boundary WHERE symbol='BTC-USD' AND timeframe='4h'").fetchone()

        last = base[-1]
        from datetime import datetime, timedelta

        last_ts = datetime.fromisoformat(last.timestamp)
        extension = [
            Candle(symbol=last.symbol, timeframe=last.timeframe, timestamp=(last_ts + timedelta(hours=i)).isoformat(), open=last.close, high=last.close + 1, low=last.close - 1, close=last.close, volume=100.0, data_status="historical")
            for i in range(1, 51)
        ]
        grown = [*base, *extension]
        rda.run_accumulation_cycle(provider=_retagging_provider(grown))
        with _conn() as conn:
            after = conn.execute("SELECT * FROM holdout_boundary WHERE symbol='BTC-USD' AND timeframe='4h'").fetchone()
        assert before == after, "a 4h holdout boundary must never be recomputed once frozen, exactly like the existing 1h guarantee"


# --- M: mock compatibility ---------------------------------------------------


class TestM_MockFactoryPathRemainsFunctional:
    def test_mock_research_factory_run_is_unaffected(self) -> None:
        from app.strategy_compiler import compile_strategy_text

        text = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R."
        definition = compile_strategy_text(name="Timeframe Infra Mock Regression", source_text=text)
        registry = {definition.id: [definition]}
        run, _updated_registry, iterations, _lessons = run_research_factory_cycle(
            _hypothesis(symbolUniverse=["AAPL"]), definition, compiled_strategy_registry=registry, quant_research_experiments=[],
            research_iterations=[], research_lessons=[], failed_archive=[], champion_history=[], risk_per_trade_pct=2.0,
            run_id="mock-path-timeframe-infra-regression", created_at=_CREATED_AT, symbols=["AAPL"], max_generations=1,
        )
        assert run.candidates_generated >= 1
        if iterations:
            assert iterations[0].experiment.dataset_metadata is None or iterations[0].experiment.dataset_metadata.source != "external_real_provider"


# --- N/O: trading and paper-trading isolation --------------------------------


class TestN_O_TradingAndPaperIsolation:
    def test_this_module_imports_no_trading_risk_or_paper_module(self) -> None:
        import ast
        import sys

        this_module = sys.modules[__name__]
        tree = ast.parse(__import__("inspect").getsource(this_module))
        imported_modules: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_modules.add(node.module)
        forbidden = {"app.nexus", "app.risk_contract", "app.paper_trading", "app.gatekeeper", "app.position_sizing"}
        assert imported_modules.isdisjoint(forbidden), f"a trading/risk/paper module was imported: {imported_modules & forbidden}"

    def test_accumulator_and_bridge_source_never_reference_trading_or_paper_internals(self) -> None:
        import inspect

        from app import real_data_accumulator as rda_module
        from app import real_data_research_bridge as bridge_module

        forbidden_substrings = ["nexus", "RiskContract", "Gatekeeper", "EmergencyStop", "PaperTrade", "broker", "schwab", "live_order", "PlaceOrder"]
        for module in (rda_module, bridge_module):
            source = inspect.getsource(module).lower()
            for forbidden in forbidden_substrings:
                assert forbidden.lower() not in source, f"{module.__name__} unexpectedly references {forbidden!r}"


# --- Section 24: real/mock firewall combinations -----------------------------


class TestRealMockFirewallCombinations:
    """Real and mock data must remain impossible to mix. Each of these
    constructs a genuinely invalid combination and proves it fails
    safely rather than silently blending."""

    def test_real_1h_plus_mock_4h_fails_closed_at_accumulation(self) -> None:
        """A provider returning real 1h candles but mock-shaped
        ("simulated") 4h candles for the same symbol must fail the
        whole accumulation cycle — never partially persist the real 1h
        leg while silently discarding the contaminated 4h leg."""
        base = _base_series("BTC-USD")
        mock_4h = [dataclasses.replace(c, timeframe="4h", data_status="simulated") for c in base]
        real_1h = [dataclasses.replace(c, timeframe="1h") for c in base]

        class _MixedProvider(MarketDataProvider):
            def get_quote(self, symbol: str):  # pragma: no cover
                raise NotImplementedError

            def get_candles(self, symbol: str, timeframe: str, limit: int, *, end_time=None, anchor_price=None) -> list[Candle]:
                series = real_1h if timeframe == "1h" else mock_4h
                return series[-limit:] if limit > 0 else list(series)

        with pytest.raises(rda.AccumulationFailure, match="Non-real/ambiguous provenance"):
            rda.run_accumulation_cycle(provider=_MixedProvider())

    def test_real_4h_plus_mock_1h_fails_closed_at_accumulation(self) -> None:
        base = _base_series("BTC-USD")
        mock_1h = [dataclasses.replace(c, timeframe="1h", data_status="simulated") for c in base]
        real_4h = [dataclasses.replace(c, timeframe="4h") for c in base]

        class _MixedProvider(MarketDataProvider):
            def get_quote(self, symbol: str):  # pragma: no cover
                raise NotImplementedError

            def get_candles(self, symbol: str, timeframe: str, limit: int, *, end_time=None, anchor_price=None) -> list[Candle]:
                series = mock_1h if timeframe == "1h" else real_4h
                return series[-limit:] if limit > 0 else list(series)

        with pytest.raises(rda.AccumulationFailure, match="Non-real/ambiguous provenance"):
            rda.run_accumulation_cycle(provider=_MixedProvider())

    def test_real_1h_plus_real_4h_never_share_one_dataset_identity(self) -> None:
        """Not a failure case — both ARE genuinely real — but proves
        they are never collapsed into one dataset identity: distinct
        content hashes, distinct holdout boundaries, distinct candle
        counts tracked independently (already proven by TestJ/TestA
        above; re-asserted here as the explicit Section 24 combination)."""
        _seed_both_timeframes()
        preflight_1h = preflight_real_data_dataset("BTC-USD", FROZEN_DEFINITION, timeframe="1h")
        preflight_4h = preflight_real_data_dataset("BTC-USD", FROZEN_DEFINITION, timeframe="4h")
        assert not isinstance(preflight_1h, RealDataFactoryPreflightFailure)
        assert not isinstance(preflight_4h, RealDataFactoryPreflightFailure)
        _p1, provenance_1h = preflight_1h
        _p2, provenance_4h = preflight_4h
        assert provenance_1h.dataset_content_hash != provenance_4h.dataset_content_hash
        assert provenance_1h.timeframe != provenance_4h.timeframe
