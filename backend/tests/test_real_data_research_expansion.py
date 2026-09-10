"""CEO directive "TradeTown — Real-Data Research Expansion 1.0."

RESEARCH FIRST. Zero production code changes were needed for this
milestone. Two things were audited and found already correct: (1) the
`dataHonestyNote` mock/real discrepancy the directive asked to re-check
was already fixed by "Research Provider Injection 1.0" (see
`app/research_experiment.py`'s own `data_honesty_note` branch on
`dataset_metadata.source`) — re-verified here, not re-fixed; (2) whether
`KrakenMarketDataProvider` could be extended with pagination to reach
materially older history. It cannot, and this is a real, verified
external limitation, not a code gap: Kraken's public `/0/public/OHLC`
endpoint's `since` parameter only narrows the window toward "now" when it
is recent enough to fit inside the endpoint's own ~720-candle-per-request
cap; setting `since` to any older timestamp (verified live against a
`since` value from January 2020) returns the exact same most-recent
~30-day window as no `since` at all. There is no cursor this endpoint
honors that walks backward into deeper history. `KrakenMarketDataProvider.
get_candles()` already (correctly) documents and discards `end_time` for
exactly this reason — implementing pagination around it would not unlock
any real additional history, so none was added.

WHAT THIS MODULE ADDS: the existing, previously-real-data-untested
`app/holdout.py` machinery (chronological train/validation/holdout
partition, freeze record, structural overlap/leakage check) exercised
against REAL Kraken candles for the first time — proving it produces a
genuinely `"valid"` partition against a real (not mock) dataset, not just
against `MockMarketDataProvider`'s synthetic series as its own existing
test suite already covers. Also exercises `app/walk_forward.py` with a
`window_bars` value sized to the real ~720-candle ceiling (the existing
default, `DEFAULT_WINDOW_BARS=1000`, mathematically cannot produce even
one window against this little real history) — a real, pre-declared
research-configuration choice, never a validation THRESHOLD change
(`MIN_EVALUATED_WINDOWS_FOR_VERDICT`/`STABLE_POSITIVE_WINDOW_FRACTION`
are untouched).

FROZEN CONFIGURATION (identical selection rule to "Real-Data Research
Validation 1.0", declared before any result was inspected): strategy =
the first entry from `default_researchable_strategies()`
("50-ema-breakout-pullback-long", v1); symbol = `["BTC-USD"]` (the only
symbol `KrakenMarketDataProvider` maps); timeframe = `"1h"`;
`candles_per_symbol` = whatever Kraken's endpoint actually returns
(verified ~720 closed candles — this module's own Phase 2 forensic
finding above, not a chosen number). `window_bars` for the custom
walk-forward run = `candle_count // 3`, the largest equal split giving
>= `MIN_EVALUATED_WINDOWS_FOR_VERDICT` (3) windows while still meeting
`app/strategy_engine.py`'s own minimum-bar floor
(`MIN_BARS_ON_SIDE_BEFORE_CROSS + MAX_HOLD_BARS + 60`) — a fixed rule,
not chosen after seeing any window's own trades.

Follows the repository's established CASE A / CASE B disclosure pattern:
skips (never fails the suite, never fabricates a result) if real network
connectivity to Kraken is unavailable in this environment.
"""
from __future__ import annotations

import socket
import urllib.error

import pytest

from app.holdout import freeze_strategy, partition_candles_chronologically, run_holdout_evaluation, validate_holdout
from app.market_data import ExternalMarketDataProviderUnavailable, KrakenMarketDataProvider, MarketDataProvider
from app.strategy_engine import MAX_HOLD_BARS, MIN_BARS_ON_SIDE_BEFORE_CROSS
from app.strategy_registry import default_researchable_strategies
from app.walk_forward import run_walk_forward_validation

_STRATEGIES, _REGISTRY = default_researchable_strategies()
SELECTED_DEFINITION = _REGISTRY["50-ema-breakout-pullback-long"][0]
assert SELECTED_DEFINITION.status == "compiled", "the selected strategy must already be compiled — never repaired or tuned for this milestone"

SYMBOL = "BTC-USD"
TIMEFRAME = "1h"
MIN_BARS_FLOOR = MIN_BARS_ON_SIDE_BEFORE_CROSS + MAX_HOLD_BARS + 60


class _FrozenSnapshotProvider(MarketDataProvider):
    """Replays one already-fetched real candle list for every call in a
    test, so a test that calls the pipeline more than once (walk-forward
    plus holdout) reads the exact same immutable real snapshot rather
    than risking a second, slightly different live fetch mid-test."""

    def __init__(self, candles: list) -> None:
        self._candles = candles

    def get_quote(self, symbol: str):  # pragma: no cover - unused by this suite
        raise NotImplementedError

    def get_candles(self, symbol: str, timeframe: str, limit: int, *, end_time=None, anchor_price=None):
        assert symbol == SYMBOL
        assert timeframe == TIMEFRAME
        return self._candles[-limit:] if limit > 0 else list(self._candles)


@pytest.fixture(scope="module")
def real_candles() -> list:
    kraken = KrakenMarketDataProvider()
    try:
        return kraken.get_candles(SYMBOL, TIMEFRAME, 100_000)
    except ExternalMarketDataProviderUnavailable as exc:
        pytest.skip(f"Real Kraken external verification could not be completed in this environment: {exc}")
    except (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError) as exc:
        pytest.skip(f"Real network connectivity to Kraken unavailable in this environment: {exc}")
    raise AssertionError("unreachable — pytest.skip() always raises")


class TestKrakenHasNoDeeperHistoryViaSince:
    """Live-verifies this module's own Phase 2 forensic finding: `since`
    does not page backward into history older than the endpoint's own
    recent-window cap. If Kraken's public API ever changes this, this
    test — not a comment — is what will catch it."""

    def test_a_since_value_from_2020_returns_the_same_recent_window_as_no_since(self, real_candles: list) -> None:
        import json
        import urllib.request

        url = "https://api.kraken.com/0/public/OHLC?pair=XBTUSD&interval=60&since=1577836800"
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                payload = json.loads(resp.read())
        except (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError) as exc:
            pytest.skip(f"Real network connectivity to Kraken unavailable in this environment: {exc}")
        result = payload["result"]
        key = next(k for k in result if k != "last")
        rows = result[key]
        oldest_ts_via_since = rows[0][0]
        # The oldest row returned even with an ancient `since` must still land
        # within the same real ~30-day ceiling this fixture's own candles span
        # — i.e. it is NOT ~6 years older than the most recent real candle.
        from datetime import datetime, timezone

        oldest_via_since_dt = datetime.fromtimestamp(oldest_ts_via_since, tz=timezone.utc)
        newest_real_dt = real_candles[-1].timestamp
        assert (
            oldest_via_since_dt.year >= int(newest_real_dt[:4]) - 1
        ), "Kraken's public OHLC endpoint appears to now support deeper history via `since` — re-audit before assuming the ~720-candle ceiling still holds."


class TestRealHistoricalDepthCeiling:
    def test_kraken_returns_at_most_the_documented_recent_window(self, real_candles: list) -> None:
        assert 0 < len(real_candles) <= 1000, "a materially larger response would mean the ~720-candle ceiling this milestone found no longer holds"

    def test_real_candles_are_strictly_chronological_and_closed(self, real_candles: list) -> None:
        timestamps = [c.timestamp for c in real_candles]
        assert timestamps == sorted(timestamps)
        assert len(set(timestamps)) == len(timestamps)
        for c in real_candles:
            assert c.data_status == "historical"  # never the still-forming bar


class TestFrozenStrategyUnchangedAcrossThisModule:
    def test_selected_definition_identity(self) -> None:
        assert SELECTED_DEFINITION.id == "50-ema-breakout-pullback-long"
        assert SELECTED_DEFINITION.version == 1
        assert SELECTED_DEFINITION.timeframe == TIMEFRAME


class TestHoldoutIsolationOnRealData:
    """`app/holdout.py` had only ever been exercised against
    `MockMarketDataProvider`'s synthetic series before this milestone.
    Proves the identical machinery produces a genuinely valid,
    non-overlapping, chronological partition against REAL Kraken data."""

    def test_partition_is_valid_and_non_overlapping(self, real_candles: list) -> None:
        train, validation, holdout = partition_candles_chronologically(real_candles)
        assert len(train) + len(validation) + len(holdout) == len(real_candles)
        freeze = freeze_strategy(SELECTED_DEFINITION, dataset_version="test-run", feature_versions=[])
        report = validate_holdout(
            SELECTED_DEFINITION,
            train=train,
            validation=validation,
            holdout=holdout,
            dataset_id="kraken-btc-usd-1h-expansion-test",
            dataset_version="test-run",
            freeze=freeze,
            report_id="expansion-test-holdout",
        )
        assert report.status == "valid"
        assert report.overlap_detected is False
        assert report.leakage_detected is False
        assert report.chronological_order_valid is True

    def test_holdout_only_backtest_never_sees_train_or_validation_candles(self, real_candles: list) -> None:
        train, validation, holdout = partition_candles_chronologically(real_candles)
        freeze = freeze_strategy(SELECTED_DEFINITION, dataset_version="test-run", feature_versions=[])
        report = validate_holdout(
            SELECTED_DEFINITION,
            train=train,
            validation=validation,
            holdout=holdout,
            dataset_id="kraken-btc-usd-1h-expansion-test",
            dataset_version="test-run",
            freeze=freeze,
            report_id="expansion-test-holdout-2",
        )
        result = run_holdout_evaluation(SELECTED_DEFINITION, SYMBOL, report=report, holdout_candles=holdout, result_id="expansion-test-holdout-eval")
        # Structural proof, not a behavioral one: the holdout evaluator's own
        # signature takes only the already-sliced holdout list — there is no
        # path for it to reach train/validation candles even if it wanted to.
        import inspect

        assert "train" not in inspect.signature(run_holdout_evaluation).parameters
        assert "validation" not in inspect.signature(run_holdout_evaluation).parameters
        assert result.report.status == "valid"


class TestCustomSizedWalkForwardOnRealData:
    """`DEFAULT_WINDOW_BARS=1000` mathematically cannot produce a single
    window against ~720 real candles. Runs the same, unmodified
    `run_walk_forward_validation()` with a `window_bars` value sized to
    the real data actually available — a research-configuration choice
    declared by a fixed rule, not a validation threshold change."""

    def test_default_window_bars_is_structurally_insufficient_for_the_real_ceiling(self, real_candles: list) -> None:
        provider = _FrozenSnapshotProvider(real_candles)
        result = run_walk_forward_validation(SELECTED_DEFINITION, symbols=[SYMBOL], timeframe=TIMEFRAME, candles_per_symbol=len(real_candles), market_data_provider=provider)
        assert result.verdict == "insufficient_data"

    def test_window_bars_sized_to_real_ceiling_produces_windows(self, real_candles: list) -> None:
        provider = _FrozenSnapshotProvider(real_candles)
        window_bars = len(real_candles) // 3
        if window_bars < MIN_BARS_FLOOR:
            pytest.skip(f"Real candle count {len(real_candles)} cannot form 3 windows meeting the {MIN_BARS_FLOOR}-bar floor.")
        result = run_walk_forward_validation(
            SELECTED_DEFINITION, symbols=[SYMBOL], timeframe=TIMEFRAME, candles_per_symbol=len(real_candles), window_bars=window_bars, market_data_provider=provider
        )
        symbol_result = result.symbols[0]
        assert len(symbol_result.windows) == 3
        # Real, disjoint, chronological windows — never sharing state.
        for earlier, later in zip(symbol_result.windows, symbol_result.windows[1:]):
            assert earlier.end_timestamp < later.start_timestamp


class TestDataHonestyNoteAlreadyCorrect:
    """Re-verifies the discrepancy this milestone's directive asked to
    check for (`data_honesty_note` claiming mock during a real-data run)
    no longer exists — already fixed by "Research Provider Injection
    1.0"; this test proves it, rather than re-fixing something already
    fixed."""

    def test_real_provider_yields_real_data_honesty_note(self, real_candles: list) -> None:
        from app.research_experiment import run_research_experiment

        provider = _FrozenSnapshotProvider(real_candles)
        record = run_research_experiment(SELECTED_DEFINITION, symbols=[SYMBOL], timeframe=TIMEFRAME, candles_per_symbol=len(real_candles), market_data_provider=provider)
        assert record.dataset_metadata is not None
        assert record.dataset_metadata.source == "external_real_provider"
        assert record.dataset_metadata.data_category == "real"
        assert "real" in record.data_honesty_note.lower()
        assert "never real historical market data" not in record.data_honesty_note
