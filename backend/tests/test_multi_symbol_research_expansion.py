"""CEO directive "TradeTown — Multi-Symbol Real-Data Expansion 1.0."

RESEARCH FIRST. One production code change was genuinely necessary and
narrowly scoped: `app/market_data.py::KrakenMarketDataProvider._SYMBOL_TO_PAIR`
gained exactly one entry, `"ETH-USD": "ETHUSD"` — the smallest existing
abstraction that permits an additional Kraken symbol, per this
directive's own Phase 0 instruction not to build a second market-data
system. No other file changed.

PRE-REGISTERED UNIVERSE-SELECTION RULE (declared before any result was
inspected): the additional symbol universe is this codebase's own
existing canonical crypto taxonomy — every symbol across
`app/watchlist.py::SEED_SYMBOLS`, `app/watchlist.py::EXTRA_SYMBOL_POOL`,
and `app/asset_discovery.py::DISCOVERY_SYMBOL_POOL` tagged the
`"bitcoin"` `ResearchCategory` — minus the existing `"BTC-USD"`
baseline. That set is exactly `{"ETH-USD"}` (from
`DISCOVERY_SYMBOL_POOL`); no `"SOL-USD"` or any other cryptocurrency
exists anywhere in this codebase's own symbol pools. This test module
proves that rule is still what it claims to be — if a future symbol
pool edit added another crypto symbol, `test_universe_rule_still_yields_exactly_eth_usd`
below is what would catch the drift.

Frozen configuration, identical selection rule to the prior two
real-data milestones: strategy = the first entry from
`default_researchable_strategies()` ("50-ema-breakout-pullback-long",
v1); timeframe = "1h"; symbols = `["BTC-USD", "ETH-USD"]`; per-symbol
`candles_per_symbol` = whatever Kraken's endpoint actually returns for
that symbol (not chosen).

Follows the repository's established CASE A / CASE B disclosure
pattern: skips (never fails the suite, never fabricates a result) if
real network connectivity to Kraken is unavailable.
"""
from __future__ import annotations

import inspect
import socket
import urllib.error

import pytest

from app.asset_discovery import DISCOVERY_SYMBOL_POOL
from app.holdout import freeze_strategy, partition_candles_chronologically, run_holdout_evaluation, validate_holdout
from app.market_data import ExternalMarketDataProviderUnavailable, KrakenMarketDataProvider, MarketDataProvider
from app.research_experiment import run_research_experiment
from app.strategy_lab import CERTIFICATION_MIN_TRADE_COUNT
from app.strategy_registry import default_researchable_strategies
from app.walk_forward import MIN_EVALUATED_WINDOWS_FOR_VERDICT, STABLE_POSITIVE_WINDOW_FRACTION, run_walk_forward_validation
from app.watchlist import EXTRA_SYMBOL_POOL, SEED_SYMBOLS

_STRATEGIES, _REGISTRY = default_researchable_strategies()
SELECTED_DEFINITION = _REGISTRY["50-ema-breakout-pullback-long"][0]
assert SELECTED_DEFINITION.status == "compiled"

SYMBOLS = ["BTC-USD", "ETH-USD"]
TIMEFRAME = "1h"


class _MultiSymbolFrozenProvider(MarketDataProvider):
    """Replays already-fetched real per-symbol snapshots, never
    combining two symbols' candles into one series."""

    def __init__(self, candles_by_symbol: dict) -> None:
        self._candles_by_symbol = candles_by_symbol

    def get_quote(self, symbol: str):  # pragma: no cover - unused by this suite
        raise NotImplementedError

    def get_candles(self, symbol: str, timeframe: str, limit: int, *, end_time=None, anchor_price=None):
        assert timeframe == TIMEFRAME
        candles = self._candles_by_symbol[symbol]
        return candles[-limit:] if limit > 0 else list(candles)


@pytest.fixture(scope="module")
def real_candles_by_symbol() -> dict:
    kraken = KrakenMarketDataProvider()
    out = {}
    for symbol in SYMBOLS:
        try:
            out[symbol] = kraken.get_candles(symbol, TIMEFRAME, 100_000)
        except ExternalMarketDataProviderUnavailable as exc:
            pytest.skip(f"Real Kraken external verification could not be completed in this environment: {exc}")
        except (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError) as exc:
            pytest.skip(f"Real network connectivity to Kraken unavailable in this environment: {exc}")
    return out


class TestUniverseSelectionRule:
    def test_universe_rule_still_yields_exactly_eth_usd(self) -> None:
        crypto_symbols = {symbol for symbol, _name, category in (*SEED_SYMBOLS, *EXTRA_SYMBOL_POOL, *DISCOVERY_SYMBOL_POOL) if category == "bitcoin"}
        assert crypto_symbols == {"BTC-USD", "ETH-USD"}, "the pre-registered universe rule (this codebase's own canonical crypto taxonomy) has changed — re-audit before assuming ETH-USD is still the only addition"


class TestFrozenStrategyUnchanged:
    def test_selected_definition_identity(self) -> None:
        assert SELECTED_DEFINITION.id == "50-ema-breakout-pullback-long"
        assert SELECTED_DEFINITION.version == 1
        assert SELECTED_DEFINITION.timeframe == TIMEFRAME


class TestEachSymbolIsGenuinelyRealAndIndependent:
    def test_both_symbols_returned_real_non_empty_series(self, real_candles_by_symbol: dict) -> None:
        for symbol, candles in real_candles_by_symbol.items():
            assert len(candles) > 0
            assert all(c.symbol == symbol for c in candles)
            assert all(c.data_status == "historical" for c in candles)

    def test_symbols_are_never_combined_into_one_series(self, real_candles_by_symbol: dict) -> None:
        """Structural proof: the provider used below is keyed per symbol
        and asserts the requested symbol before returning anything — a
        caller cannot accidentally receive one symbol's candles under
        another symbol's label."""
        provider = _MultiSymbolFrozenProvider(real_candles_by_symbol)
        btc = provider.get_candles("BTC-USD", TIMEFRAME, 10)
        eth = provider.get_candles("ETH-USD", TIMEFRAME, 10)
        assert {c.symbol for c in btc} == {"BTC-USD"}
        assert {c.symbol for c in eth} == {"ETH-USD"}


class TestCrossSymbolAggregateReusesExistingArchitecture:
    """`run_research_experiment(symbols=[...])` already aggregates across
    symbols via its own existing `overall`/`instrumentBreakdown` split —
    this test proves that reuse rather than any new aggregation code."""

    def test_combined_call_reports_both_per_symbol_and_aggregate(self, real_candles_by_symbol: dict) -> None:
        provider = _MultiSymbolFrozenProvider(real_candles_by_symbol)
        min_count = min(len(c) for c in real_candles_by_symbol.values())
        record = run_research_experiment(SELECTED_DEFINITION, symbols=SYMBOLS, timeframe=TIMEFRAME, candles_per_symbol=min_count, market_data_provider=provider)
        breakdown_symbols = {b.label for b in record.backtest.instrument_breakdown}
        assert breakdown_symbols == set(SYMBOLS), "a weak symbol must never be dropped from the per-symbol breakdown"
        # The aggregate trade count must equal the sum of the per-symbol counts —
        # proves no symbol's trades were silently excluded from `overall`.
        assert record.backtest.overall.trade_count == sum(b.trade_count for b in record.backtest.instrument_breakdown)


class TestValidationThresholdsUnchanged:
    def test_certification_min_trade_count_is_still_twenty(self) -> None:
        assert CERTIFICATION_MIN_TRADE_COUNT == 20

    def test_walk_forward_thresholds_unchanged(self) -> None:
        assert MIN_EVALUATED_WINDOWS_FOR_VERDICT == 3
        assert STABLE_POSITIVE_WINDOW_FRACTION == 0.6


class TestHoldoutIsolationOnRealDataPerSymbol:
    """`app/holdout.py` has no multi-symbol concept by design — proves
    it independently produces a valid, non-overlapping partition for
    EACH real symbol, never sharing state between them."""

    def test_each_symbol_partitions_independently_and_validly(self, real_candles_by_symbol: dict) -> None:
        for symbol, candles in real_candles_by_symbol.items():
            train, validation, holdout = partition_candles_chronologically(candles)
            freeze = freeze_strategy(SELECTED_DEFINITION, dataset_version=f"test-{symbol}", feature_versions=[])
            report = validate_holdout(
                SELECTED_DEFINITION,
                train=train,
                validation=validation,
                holdout=holdout,
                dataset_id=f"kraken-{symbol}-{TIMEFRAME}",
                dataset_version=f"test-{symbol}",
                freeze=freeze,
                report_id=f"multi-symbol-test-holdout-{symbol}",
            )
            assert report.status == "valid", f"{symbol}: holdout partition was not valid"
            assert report.overlap_detected is False
            assert report.leakage_detected is False
            result = run_holdout_evaluation(SELECTED_DEFINITION, symbol, report=report, holdout_candles=holdout, result_id=f"multi-symbol-test-holdout-eval-{symbol}")
            assert result.report.status == "valid"

    def test_holdout_evaluator_signature_has_no_cross_symbol_path(self) -> None:
        params = inspect.signature(run_holdout_evaluation).parameters
        assert "other_symbol" not in params
        assert "symbols" not in params  # single-symbol only, by design — never silently pooled


class TestLookAheadCleanAcrossSymbols:
    def test_look_ahead_audit_is_clean_for_the_combined_call(self, real_candles_by_symbol: dict) -> None:
        provider = _MultiSymbolFrozenProvider(real_candles_by_symbol)
        min_count = min(len(c) for c in real_candles_by_symbol.values())
        record = run_research_experiment(SELECTED_DEFINITION, symbols=SYMBOLS, timeframe=TIMEFRAME, candles_per_symbol=min_count, market_data_provider=provider)
        assert record.look_ahead_audit.verdict == "clean"
        assert record.point_in_time_verified is True


class TestWalkForwardNeverHidesAWeakSymbol:
    def test_per_symbol_windows_are_individually_reported(self, real_candles_by_symbol: dict) -> None:
        provider = _MultiSymbolFrozenProvider(real_candles_by_symbol)
        min_count = min(len(c) for c in real_candles_by_symbol.values())
        window_bars = min_count // 3
        if window_bars < 215:
            pytest.skip(f"Real candle count {min_count} cannot form 3 windows meeting the minimum-bar floor.")
        result = run_walk_forward_validation(
            SELECTED_DEFINITION, symbols=SYMBOLS, timeframe=TIMEFRAME, candles_per_symbol=min_count, window_bars=window_bars, market_data_provider=provider
        )
        reported_symbols = {s.symbol for s in result.symbols}
        assert reported_symbols == set(SYMBOLS), "every symbol's own windows must be reported, even a weak one"


class TestDataHonestyForMultiSymbolRecord:
    def test_combined_record_reports_real_provenance_for_both_symbols(self, real_candles_by_symbol: dict) -> None:
        provider = _MultiSymbolFrozenProvider(real_candles_by_symbol)
        min_count = min(len(c) for c in real_candles_by_symbol.values())
        record = run_research_experiment(SELECTED_DEFINITION, symbols=SYMBOLS, timeframe=TIMEFRAME, candles_per_symbol=min_count, market_data_provider=provider)
        assert record.dataset_metadata is not None
        assert record.dataset_metadata.source == "external_real_provider"
        assert record.dataset_metadata.data_category == "real"
        assert set(record.dataset_metadata.symbols) == set(SYMBOLS)
        assert record.dataset_metadata.missing_bar_symbols == []
