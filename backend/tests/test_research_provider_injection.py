"""Covers app/research_experiment.py's new optional `market_data_provider`
parameter — CEO directive "TradeTown — Research Provider Injection 1.0."
This is the milestone that removes the architectural blocker the prior
"Real OHLCV Market Data Provider Activation & Provenance 1.0" milestone's
own audit found: every research module hardcoded the global mock
singleton at import scope, so a real `ExternalMarketDataProvider` (e.g.
`KrakenMarketDataProvider`) could never actually reach a backtest.

Four required proofs (directive Section 19):
  TEST A — default compatibility: no provider passed -> the existing
    global mock singleton is used, unchanged.
  TEST B — explicit injection: an explicit `FakeMarketDataProvider` is
    used instead of the global singleton.
  TEST C — identity propagation: the SAME provider instance reaches the
    actual downstream candle-consuming stage (never reconstructed).
  TEST D — no silent fallback: an explicit provider that raises
    `ExternalMarketDataProviderUnavailable` fails the whole research call
    with that same exception — never silently substitutes mock data.

`FakeMarketDataProvider` below is a deterministic, real
`MarketDataProvider` implementation (not a mock/patch of the abstract
class) — the same disclosed-fake-provider pattern
`tests/test_external_market_data.py` already established for
`_FakeTransport`, one level higher (a fake PROVIDER, not a fake HTTP
transport) since this milestone's boundary is the provider itself.
"""
from __future__ import annotations

from datetime import datetime

import pytest

import socket
import urllib.error

from app.market_data import Candle, ExternalMarketDataProviderUnavailable, KrakenMarketDataProvider, MarketDataProvider, Quote, market_data_provider as global_market_data_provider
from app.research_experiment import run_research_experiment
from app.strategy_compiler import compile_strategy_text

_CEO_TEXT = (
    "Buy when price closes above the 50 EMA, then wait for at least two bearish candles, "
    "then enter when price closes above the previous swing high. Place the stop at the "
    "Chandelier Stop and target 2R."
)


def _real_shaped_candle(index: int, close: float = 100.0) -> Candle:
    return Candle(symbol="BTC-USD", timeframe="1h", timestamp=f"2024-01-0{1 + index // 24}T{index % 24:02d}:00:00+00:00", open=close, high=close + 1, low=close - 1, close=close, volume=10.0, data_status="historical")


class FakeMarketDataProvider(MarketDataProvider):
    """A real, deterministic, non-mock `MarketDataProvider` — every
    candle it returns is tagged `data_status="historical"` (the real
    external-provider provenance, never `"simulated"`), so a test can
    prove real-shaped data actually flowed all the way through
    `run_research_experiment()` into `datasetMetadata.source`."""

    def __init__(self, candle_count: int = 300) -> None:
        self._candles = [_real_shaped_candle(i, close=100.0 + (i % 7)) for i in range(candle_count)]
        self.get_candles_call_count = 0
        self.calls: list[tuple[str, str, int]] = []

    def get_quote(self, symbol: str) -> Quote:
        raise NotImplementedError("not needed by any research module")

    def get_candles(self, symbol: str, timeframe: str, limit: int, *, end_time: datetime | None = None, anchor_price: float | None = None) -> list[Candle]:
        self.get_candles_call_count += 1
        self.calls.append((symbol, timeframe, limit))
        return list(self._candles[:limit])


class RaisingMarketDataProvider(MarketDataProvider):
    """Simulates an explicitly-injected real provider whose real HTTP
    request fails — the exact shape `KrakenMarketDataProvider` raises on
    a genuine failure (never a made-up exception type)."""

    def __init__(self) -> None:
        self.get_candles_call_count = 0

    def get_quote(self, symbol: str) -> Quote:
        raise ExternalMarketDataProviderUnavailable("fake unavailable provider — get_quote")

    def get_candles(self, symbol: str, timeframe: str, limit: int, *, end_time: datetime | None = None, anchor_price: float | None = None) -> list[Candle]:
        self.get_candles_call_count += 1
        raise ExternalMarketDataProviderUnavailable("fake unavailable provider — real network failure simulated")


def _spy_on_global_mock(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, int]]:
    """Wraps the REAL global mock singleton's own `get_candles` (the
    same object every existing caller already uses) so a test can prove
    it either WAS or WAS NOT touched during a given call — never
    replacing it with an unrelated fake."""
    calls: list[tuple[str, str, int]] = []
    original = global_market_data_provider.get_candles

    def _spy(symbol: str, timeframe: str, limit: int, **kwargs: object) -> list[Candle]:
        calls.append((symbol, timeframe, limit))
        return original(symbol, timeframe, limit, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(global_market_data_provider, "get_candles", _spy)
    return calls


class TestDefaultCompatibility:
    """TEST A — an old caller with no provider argument must keep using
    the existing global mock singleton, unchanged."""

    def test_no_provider_argument_uses_the_real_global_mock_singleton(self, monkeypatch: pytest.MonkeyPatch) -> None:
        calls = _spy_on_global_mock(monkeypatch)
        definition = compile_strategy_text(name="x", source_text=_CEO_TEXT)
        record = run_research_experiment(definition, symbols=["AAPL"], candles_per_symbol=200)
        assert len(calls) > 0, "the real global mock singleton must have been called at least once"
        assert record.dataset_metadata.source == "mock_provider"
        assert record.dataset_metadata.data_category == "simulated"
        assert "mock OHLCV" in record.data_honesty_note

    def test_default_path_dataset_metadata_is_byte_identical_in_shape_to_pre_injection_behavior(self) -> None:
        """No exact-output regression fixture existed before this
        milestone (see tests/test_research_experiment.py's own house
        convention of never asserting a specific backtest outcome) —
        this proves the SHAPE/CONTRACT is unchanged: same dataset id
        convention, same symbol list, same requested candle count."""
        definition = compile_strategy_text(name="x", source_text=_CEO_TEXT)
        record = run_research_experiment(definition, symbols=["AAPL", "MSFT"], candles_per_symbol=200)
        assert record.dataset_metadata.dataset_id == "1h:AAPL,MSFT:200"
        assert record.symbols_tested == ["AAPL", "MSFT"]


class TestExplicitInjection:
    """TEST B — an explicitly supplied provider must be used instead of
    the global mock singleton."""

    def test_explicit_provider_is_used_and_the_global_mock_is_never_touched(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_calls = _spy_on_global_mock(monkeypatch)
        fake = FakeMarketDataProvider()
        definition = compile_strategy_text(name="x", source_text=_CEO_TEXT)
        record = run_research_experiment(definition, symbols=["BTC-USD"], candles_per_symbol=200, market_data_provider=fake)
        assert fake.get_candles_call_count > 0
        assert mock_calls == [], "the global mock singleton must never be called when an explicit provider is supplied"
        assert record.dataset_metadata.source == "external_real_provider"
        assert record.dataset_metadata.data_category == "real"
        assert "external_real_provider" in record.data_honesty_note
        assert "mock" not in record.data_honesty_note.lower()


class TestIdentityPropagation:
    """TEST C — the SAME provider instance (never an equivalent second
    object) must reach the actual downstream candle consumers."""

    def test_the_same_fake_instance_serves_every_research_axis(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_calls = _spy_on_global_mock(monkeypatch)
        fake = FakeMarketDataProvider(candle_count=400)
        definition = compile_strategy_text(name="x", source_text=_CEO_TEXT)
        run_research_experiment(definition, symbols=["BTC-USD"], candles_per_symbol=400, market_data_provider=fake)
        # Six research axes plus the top-level dataset-metadata fetch —
        # every one of them must have reached THIS object (proven by its
        # own call counter incrementing, not a freshly-constructed
        # equivalent instance, which would have a counter of 0).
        assert fake.get_candles_call_count >= 6
        assert mock_calls == []
        assert all(timeframe == "1h" for _symbol, timeframe, _limit in fake.calls)
        assert all(symbol == "BTC-USD" for symbol, _timeframe, _limit in fake.calls)

    def test_parameter_sensitivity_sweep_points_also_reach_the_same_injected_instance(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Parameter sensitivity runs several extra, independent
        backtests (one per swept stop/target point) — every one of them
        must also reach the SAME injected instance, not silently fall
        back to the global default inside that nested call path."""
        mock_calls = _spy_on_global_mock(monkeypatch)
        fake = FakeMarketDataProvider(candle_count=400)
        definition = compile_strategy_text(name="x", source_text=_CEO_TEXT)
        from app.parameter_sensitivity import run_parameter_sensitivity

        run_parameter_sensitivity(definition, symbols=["BTC-USD"], candles_per_symbol=400, market_data_provider=fake)
        assert fake.get_candles_call_count > 1  # more than one sweep point was actually backtested
        assert mock_calls == []


class TestNoSilentFallback:
    """TEST D — an explicitly injected provider that fails must fail the
    whole research call with its own real exception — never silently
    substitute mock data."""

    def test_a_raising_provider_fails_the_whole_experiment_never_falls_back_to_mock(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_calls = _spy_on_global_mock(monkeypatch)
        raising = RaisingMarketDataProvider()
        definition = compile_strategy_text(name="x", source_text=_CEO_TEXT)
        with pytest.raises(ExternalMarketDataProviderUnavailable):
            run_research_experiment(definition, symbols=["BTC-USD"], candles_per_symbol=200, market_data_provider=raising)
        assert raising.get_candles_call_count > 0, "the raising provider must actually have been invoked, not skipped"
        assert mock_calls == [], "a provider failure must never trigger a silent fallback to the global mock singleton"

    def test_a_raising_provider_also_fails_the_lower_level_backtest_directly(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_calls = _spy_on_global_mock(monkeypatch)
        raising = RaisingMarketDataProvider()
        definition = compile_strategy_text(name="x", source_text=_CEO_TEXT)
        from app.strategy_engine import run_compiled_strategy_backtest

        with pytest.raises(ExternalMarketDataProviderUnavailable):
            run_compiled_strategy_backtest(definition, symbols=["BTC-USD"], candles_per_symbol=200, market_data_provider=raising)
        assert mock_calls == []


class TestRealExternalResearchSmokeTest:
    """Directive Section 13/31 — ONE bounded, real integration proof that
    `run_research_experiment(..., market_data_provider=KrakenMarketDataProvider())`
    can actually reach the injected real provider. Same CASE A/CASE B
    honesty standard as Directive 1's own
    `tests/test_kraken_market_data.py::TestKrakenRealExternalSmokeTest`:
    skips (never fails the suite, never fabricates a result) if real
    network connectivity to Kraken is unavailable in this environment."""

    def test_one_bounded_real_experiment_against_real_kraken_btc_usd_data(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_calls = _spy_on_global_mock(monkeypatch)
        kraken = KrakenMarketDataProvider(max_retries=1, timeout_seconds=8.0)
        definition = compile_strategy_text(name="x", source_text=_CEO_TEXT)

        try:
            record = run_research_experiment(definition, symbols=["BTC-USD"], candles_per_symbol=60, market_data_provider=kraken)
        except ExternalMarketDataProviderUnavailable as exc:
            pytest.skip(f"Real Kraken external verification could not be completed in this environment: {exc}")
        except (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError) as exc:
            pytest.skip(f"Real network connectivity to Kraken unavailable in this environment: {exc}")

        # Real provider explicitly supplied, real HTTP request succeeded,
        # research actually consumed the injected data, provenance
        # remained external_real_provider, and the global mock singleton
        # was never touched — the exact chain the directive's Section 31
        # requires proof of.
        assert record.dataset_metadata.source == "external_real_provider"
        assert record.dataset_metadata.data_category == "real"
        assert "external_real_provider" in record.data_honesty_note
        assert mock_calls == []
        # No trading consequence: this function's own signature takes
        # only a `definition` — there is no GameState/portfolio/broker
        # argument anywhere in this call for a trade, order, or fill to
        # be recorded into; ResearchExperimentRecord is a pure, unpersisted
        # return value.
        assert record.definition_id == definition.id

