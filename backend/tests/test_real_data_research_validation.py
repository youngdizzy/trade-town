"""CEO directive "TradeTown — Real-Data Research Validation 1.0."

Zero production code was needed for this milestone — the prior "Research
Provider Injection 1.0" milestone's architecture already supports
everything required here. This file both (a) proves the required
invariants as pytest tests, and (b) IS the milestone's own reproducible
research artifact per that directive's own Phase 12 ("if persistence
would require disproportionate architectural work, keep the experiment
reproducible through a deterministic test/script and document the exact
command/configuration instead").

FROZEN EXPERIMENT CONFIGURATION (declared before any result was
examined — see the final forensic report's "Strategy Selection Rule"
and "Window Selection Rule" sections for the reasoning):

  STRATEGY: the FIRST strategy returned by
  `app/strategy_registry.py::default_researchable_strategies()` in that
  function's own fixed, pre-existing iteration order (Long before
  Short) — "50 EMA Breakout Pullback (Long)",
  id="50-ema-breakout-pullback-long", version=1. This is a real,
  already-existing, on-by-default, already-compiled strategy (wired
  into every fresh save via `app/state.py`'s `default_state()`) — not
  authored or tuned for this milestone.

  SYMBOLS: ["BTC-USD"] — the only symbol `KrakenMarketDataProvider`
  supports (a real, disclosed, pre-existing scope limit from the prior
  "Real OHLCV Provider Activation" milestone), and already a canonical
  TradeTown symbol (`app/watchlist.py::SEED_SYMBOLS`).

  TIMEFRAME: "1h" — the strategy's own registered timeframe, and
  `KrakenMarketDataProvider`'s cleanest supported mapping.

  CANDLES_PER_SYMBOL: 720 — determined during this milestone's own
  Phase 0 by an empirical, non-outcome-based infrastructure check: a
  real, bounded `KrakenMarketDataProvider().get_candles("BTC-USD",
  "1h", 100_000)` call (made BEFORE any strategy was run) returned
  exactly 720 real closed candles — Kraken's own real per-request cap
  for this interval (this codebase's own adapter implements no
  pagination, a disclosed, pre-existing limitation). 720 is used for
  BOTH the mock and real runs so the requested count is identical
  across both — the only intended difference between the two primary
  runs is the data provider itself.

Neither the strategy nor the window was chosen after looking at any
backtest result. See `RealDataResearchValidationTest.md` — no such file
exists; this docstring and the final forensic report ARE the record.
"""
from __future__ import annotations

import socket
import urllib.error
from datetime import datetime

import pytest

from app.market_data import Candle, ExternalMarketDataProviderUnavailable, KrakenMarketDataProvider, MarketDataProvider, Quote, market_data_provider as global_market_data_provider
from app.research_experiment import run_research_experiment
from app.strategy_registry import default_researchable_strategies

# --- Frozen configuration (see module docstring) --------------------------
_STRATEGIES, _REGISTRY = default_researchable_strategies()
SELECTED_DEFINITION = _REGISTRY["50-ema-breakout-pullback-long"][0]
assert SELECTED_DEFINITION.status == "compiled", "the selected strategy must already be compiled — never repaired or tuned for this milestone"

SYMBOLS = ["BTC-USD"]
TIMEFRAME = "1h"
CANDLES_PER_SYMBOL = 720


def _spy_on_global_mock(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str, int]]:
    calls: list[tuple[str, str, int]] = []
    original = global_market_data_provider.get_candles

    def _spy(symbol: str, timeframe: str, limit: int, **kwargs: object) -> list[Candle]:
        calls.append((symbol, timeframe, limit))
        return original(symbol, timeframe, limit, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(global_market_data_provider, "get_candles", _spy)
    return calls


class TestFrozenStrategySelection:
    """The strategy identity used by every test/experiment below is a
    real, pre-existing, on-by-default strategy — never authored for
    this milestone, never modified, never parameter-tuned."""

    def test_selected_definition_is_the_real_pre_existing_seed_strategy(self) -> None:
        assert SELECTED_DEFINITION.id == "50-ema-breakout-pullback-long"
        assert SELECTED_DEFINITION.version == 1
        assert SELECTED_DEFINITION.timeframe == "1h"
        assert "chandelier stop" in SELECTED_DEFINITION.source_text.lower()

    def test_selection_rule_is_the_seed_functions_own_fixed_order_first_entry(self) -> None:
        """`default_researchable_strategies()` registers Long before
        Short in its own source-code tuple order (see
        app/strategy_registry.py) — the pre-declared, deterministic,
        outcome-independent tie-breaker this milestone used."""
        assert _STRATEGIES[0].compiled_definition_id == "50-ema-breakout-pullback-long"


class TestMockBaselineExperiment:
    """No network required — always runs."""

    def test_mock_experiment_reports_mock_provenance(self) -> None:
        record = run_research_experiment(SELECTED_DEFINITION, symbols=SYMBOLS, timeframe=TIMEFRAME, candles_per_symbol=CANDLES_PER_SYMBOL)
        assert record.dataset_metadata is not None
        assert record.dataset_metadata.source == "mock_provider"
        assert record.dataset_metadata.data_category == "simulated"
        assert record.dataset_metadata.candles_per_symbol_requested == CANDLES_PER_SYMBOL
        assert record.dataset_metadata.candles_per_symbol_retrieved == {"BTC-USD": CANDLES_PER_SYMBOL}
        assert record.symbols_tested == SYMBOLS
        assert record.timeframe == TIMEFRAME
        assert record.candles_per_symbol == CANDLES_PER_SYMBOL
        assert record.definition_id == SELECTED_DEFINITION.id
        assert record.definition_version == SELECTED_DEFINITION.version


class TestNoSilentFallbackForThisExactConfiguration:
    """Re-proves the injection milestone's own no-fallback guarantee,
    scoped to this milestone's exact frozen strategy/configuration
    rather than a generic fixture — no network required."""

    def test_a_raising_provider_fails_this_exact_experiment_never_falls_back(self, monkeypatch: pytest.MonkeyPatch) -> None:
        mock_calls = _spy_on_global_mock(monkeypatch)

        class _Raising(MarketDataProvider):
            def get_quote(self, symbol: str) -> Quote:
                raise ExternalMarketDataProviderUnavailable("fake")

            def get_candles(self, symbol: str, timeframe: str, limit: int, *, end_time: datetime | None = None, anchor_price: float | None = None) -> list[Candle]:
                raise ExternalMarketDataProviderUnavailable("fake unavailable provider for this exact frozen configuration")

        with pytest.raises(ExternalMarketDataProviderUnavailable):
            run_research_experiment(SELECTED_DEFINITION, symbols=SYMBOLS, timeframe=TIMEFRAME, candles_per_symbol=CANDLES_PER_SYMBOL, market_data_provider=_Raising())
        assert mock_calls == []


class TestRealDataResearchValidation:
    """The milestone's own real, bounded, deliberate research execution.
    Follows the repository's established CASE A / CASE B disclosure
    pattern: skips (never fails the suite, never fabricates a result)
    if real network connectivity to Kraken is unavailable."""

    @pytest.fixture(scope="class")
    def real_and_mock_records(self, request: pytest.FixtureRequest) -> tuple[object, object, int]:
        mp = pytest.MonkeyPatch()
        mock_calls = _spy_on_global_mock(mp)
        request.addfinalizer(mp.undo)
        try:
            real_record = run_research_experiment(
                SELECTED_DEFINITION, symbols=SYMBOLS, timeframe=TIMEFRAME, candles_per_symbol=CANDLES_PER_SYMBOL, market_data_provider=KrakenMarketDataProvider()
            )
        except ExternalMarketDataProviderUnavailable as exc:
            pytest.skip(f"Real Kraken external verification could not be completed in this environment: {exc}")
        except (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError) as exc:
            pytest.skip(f"Real network connectivity to Kraken unavailable in this environment: {exc}")
        # Snapshot the mock-call count immediately after the REAL run,
        # before the deliberate mock baseline run below (which legitimately
        # DOES call the mock singleton) — this is the number that must be 0.
        mock_calls_during_real_run = len(mock_calls)
        mock_record = run_research_experiment(SELECTED_DEFINITION, symbols=SYMBOLS, timeframe=TIMEFRAME, candles_per_symbol=CANDLES_PER_SYMBOL)
        return real_record, mock_record, mock_calls_during_real_run

    def test_same_configuration_across_both_runs(self, real_and_mock_records: tuple) -> None:  # type: ignore[type-arg]
        real_record, mock_record, _ = real_and_mock_records
        assert real_record.definition_id == mock_record.definition_id == SELECTED_DEFINITION.id
        assert real_record.definition_version == mock_record.definition_version == SELECTED_DEFINITION.version
        assert real_record.symbols_tested == mock_record.symbols_tested == SYMBOLS
        assert real_record.timeframe == mock_record.timeframe == TIMEFRAME
        assert real_record.candles_per_symbol == mock_record.candles_per_symbol == CANDLES_PER_SYMBOL

    def test_real_experiment_reports_real_provenance(self, real_and_mock_records: tuple) -> None:  # type: ignore[type-arg]
        real_record, _mock_record, _ = real_and_mock_records
        assert real_record.dataset_metadata.source == "external_real_provider"
        assert real_record.dataset_metadata.data_category == "real"
        assert "external_real_provider" in real_record.data_honesty_note
        assert "mock" not in real_record.data_honesty_note.lower()

    def test_real_window_bounds_are_honest_never_fabricated(self, real_and_mock_records: tuple) -> None:  # type: ignore[type-arg]
        real_record, _mock_record, _ = real_and_mock_records
        dm = real_record.dataset_metadata
        assert dm.candles_per_symbol_requested == CANDLES_PER_SYMBOL
        retrieved = dm.candles_per_symbol_retrieved["BTC-USD"]
        assert 0 < retrieved <= CANDLES_PER_SYMBOL  # never claims more than a real request could return
        assert dm.coverage_pct == round(retrieved / CANDLES_PER_SYMBOL * 100.0, 2)
        if retrieved < CANDLES_PER_SYMBOL:
            assert "BTC-USD" in dm.missing_bar_symbols  # a genuine shortfall must be disclosed, never hidden
        else:
            assert dm.missing_bar_symbols == []

    def test_real_data_actually_reached_the_experiment_mock_never_touched(self, real_and_mock_records: tuple) -> None:  # type: ignore[type-arg]
        real_record, _mock_record, mock_calls_during_real_run = real_and_mock_records
        assert real_record.backtest is not None
        assert real_record.symbols_tested == ["BTC-USD"]
        assert mock_calls_during_real_run == 0, "the global mock singleton must never be called while resolving the real-provider experiment"

    def test_neither_run_was_fed_into_any_trading_construct(self, real_and_mock_records: tuple) -> None:  # type: ignore[type-arg]
        """Structural proof, not a behavioral one: `run_research_experiment()`'s
        own signature takes only a strategy definition and research
        parameters — there is no GameState/portfolio/broker argument
        anywhere in this call for a trade, order, fill, or position to
        be written into."""
        import inspect

        sig = inspect.signature(run_research_experiment)
        for forbidden in ("state", "portfolio", "broker", "gatekeeper", "risk_contract"):
            assert forbidden not in sig.parameters
