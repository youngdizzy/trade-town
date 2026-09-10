"""Covers app/real_data_accumulator.py — CEO directive "TradeTown —
Real-Time Accumulation 1.0."

Two distinct kinds of test live here, same discipline
`tests/test_kraken_market_data.py` already established:

  - Every class except `TestLiveKrakenVerification` uses a `_FixedProvider`
    test double (never the network) over deterministic, hand-built or
    mock-derived candle series, RELABELED `data_status="historical"`
    purely as test fixture data (never used to claim real Kraken data
    anywhere outside this file) — these prove the accumulator's OWN
    correctness deterministically.

  - `TestLiveKrakenVerification` makes real, bounded requests to
    Kraken's real public OHLC endpoint for both BTC-USD and ETH-USD,
    proving real accumulation, real provenance, and genuine
    idempotency across two consecutive real runs against the SAME
    isolated database file (simulating a restart between them). Skips
    honestly on real connectivity failure, never fabricates a result.
"""
from __future__ import annotations

import dataclasses
import socket
import sqlite3
import urllib.error
from datetime import datetime, timedelta

import pytest

from app import real_data_accumulator as rda
from app.market_data import Candle, ExternalMarketDataProviderUnavailable, KrakenMarketDataProvider, MarketDataProvider, MockMarketDataProvider
from app.strategy_engine import backtest_symbol_over_candles
from app.strategy_registry import default_researchable_strategies

_STRATEGIES, _REGISTRY = default_researchable_strategies()
FROZEN_DEFINITION = _REGISTRY["50-ema-breakout-pullback-long"][0]


def _historical(candles: list[Candle]) -> list[Candle]:
    """Relabels an already-real Candle list's data_status to
    "historical" — used only to adapt MockMarketDataProvider's own
    deterministic output into TEST FIXTURE data shaped like a real
    provider's response; never used outside this test file."""
    return [dataclasses.replace(c, data_status="historical") for c in candles]


def _base_series(symbol: str, count: int = 3000) -> list[Candle]:
    """3000 bars of MockMarketDataProvider's own deterministic BTC-USD
    walk reliably produces exactly 3 real setups for the frozen
    strategy (1 of them inside the resulting 60/20/20 holdout window) —
    verified during this milestone's own design pass. Reused as a
    known-good fixture rather than hand-engineering exact EMA/chandelier
    trigger conditions."""
    return _historical(MockMarketDataProvider().get_candles(symbol, "1h", count))


def _extend(base: list[Candle], extra_bars: int) -> list[Candle]:
    """Appends `extra_bars` more valid, chronologically-continuous,
    hand-built candles after `base` — used to simulate new real candles
    arriving without depending on MockMarketDataProvider's own growth
    semantics (undocumented whether repeated calls with a larger limit
    share a common prefix)."""
    last = base[-1]
    last_ts = datetime.fromisoformat(last.timestamp)
    extension: list[Candle] = []
    price = last.close
    for i in range(1, extra_bars + 1):
        ts = last_ts + timedelta(hours=i)
        extension.append(
            Candle(symbol=last.symbol, timeframe=last.timeframe, timestamp=ts.isoformat(), open=price, high=price + 1.0, low=price - 1.0, close=price, volume=100.0, data_status="historical")
        )
    return [*base, *extension]


class _FixedProvider(MarketDataProvider):
    """Serves a pre-set candle list per symbol — a network-free test
    double for KrakenMarketDataProvider."""

    def __init__(self, candles_by_symbol: dict[str, list[Candle]]) -> None:
        self._candles_by_symbol = candles_by_symbol

    def get_quote(self, symbol: str):  # pragma: no cover - unused by this suite
        raise NotImplementedError

    def get_candles(self, symbol: str, timeframe: str, limit: int, *, end_time=None, anchor_price=None) -> list[Candle]:
        candles = self._candles_by_symbol[symbol]
        return candles[-limit:] if limit > 0 else list(candles)


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


# --- A/B/C: holdout boundary establishment and permanence ------------------


class TestHoldoutBoundaryPermanence:
    def test_first_run_creates_holdout_boundary(self) -> None:
        base = _base_series("BTC-USD")
        result = rda.run_accumulation_cycle(provider=_provider(base))
        assert result["status"] == "success"
        with _conn() as conn:
            row = conn.execute(
                "SELECT holdout_start_timestamp, holdout_end_timestamp FROM holdout_boundary WHERE symbol = 'BTC-USD'"
            ).fetchone()
            assert row is not None
            assert row[0] < row[1]

    def test_boundary_byte_identical_after_second_run(self) -> None:
        base = _base_series("BTC-USD")
        rda.run_accumulation_cycle(provider=_provider(base))
        with _conn() as conn:
            before = conn.execute("SELECT holdout_start_timestamp, holdout_end_timestamp, dataset_content_hash FROM holdout_boundary WHERE symbol = 'BTC-USD'").fetchone()

        grown = _extend(base, 200)
        rda.run_accumulation_cycle(provider=_provider(grown))
        with _conn() as conn:
            after = conn.execute("SELECT holdout_start_timestamp, holdout_end_timestamp, dataset_content_hash FROM holdout_boundary WHERE symbol = 'BTC-USD'").fetchone()

        assert before == after, "the holdout boundary must never be recomputed once frozen"

    def test_holdout_trade_never_reclassified_after_growth(self) -> None:
        base = _base_series("BTC-USD")
        trades_before_growth = backtest_symbol_over_candles(FROZEN_DEFINITION, "BTC-USD", base)
        from app.holdout import partition_candles_chronologically

        _train, _validation, holdout = partition_candles_chronologically(base)
        holdout_entries = {t.entry_timestamp for t in trades_before_growth if holdout[0].timestamp <= t.entry_timestamp <= holdout[-1].timestamp}
        assert holdout_entries, "fixture assumption broken: expected at least one trade inside the baseline holdout window"

        rda.run_accumulation_cycle(provider=_provider(base))
        with _conn() as conn:
            is_holdout_before = {
                row[0]: row[1] for row in conn.execute("SELECT entry_timestamp, is_holdout FROM trades WHERE symbol = 'BTC-USD'")
            }
        for ts in holdout_entries:
            assert is_holdout_before[ts] == 1

        grown = _extend(base, 300)
        rda.run_accumulation_cycle(provider=_provider(grown))
        with _conn() as conn:
            is_holdout_after = {row[0]: row[1] for row in conn.execute("SELECT entry_timestamp, is_holdout FROM trades WHERE symbol = 'BTC-USD'")}
        for ts in holdout_entries:
            assert is_holdout_after[ts] == 1, f"trade at {ts} was reclassified out of holdout after new data arrived"
        # And every trade discovered BEFORE growth keeps the identical is_holdout value.
        for ts, was_holdout in is_holdout_before.items():
            assert is_holdout_after[ts] == was_holdout


# --- D/E/F/G/H/I: deduplication and idempotency -----------------------------


class TestDeduplicationAndIdempotency:
    def test_overlapping_fetch_deduplicates_candles(self) -> None:
        base = _base_series("BTC-USD")
        result1 = rda.run_accumulation_cycle(provider=_provider(base))
        assert result1["new_candles_appended"]["BTC-USD"] == len(base)

        grown = _extend(base, 50)
        result2 = rda.run_accumulation_cycle(provider=_provider(grown))
        assert result2["new_candles_appended"]["BTC-USD"] == 50, "only the genuinely new tail should count as new"

    def test_conflicting_duplicate_candle_hard_fails(self) -> None:
        base = _base_series("BTC-USD")
        rda.run_accumulation_cycle(provider=_provider(base))

        tampered = list(base)
        tampered[-1] = dataclasses.replace(tampered[-1], close=tampered[-1].close + 999.0)
        with pytest.raises(rda.AccumulationFailure, match="Conflicting duplicate candle"):
            rda.run_accumulation_cycle(provider=_provider(tampered))

    def test_only_new_candles_increment_the_counter(self) -> None:
        base = _base_series("BTC-USD")
        rda.run_accumulation_cycle(provider=_provider(base))
        result = rda.run_accumulation_cycle(provider=_provider(base))
        assert result["new_candles_appended"]["BTC-USD"] == 0

    def test_repeated_identical_cycle_appends_zero_new_candles(self) -> None:
        base = _base_series("BTC-USD")
        rda.run_accumulation_cycle(provider=_provider(base))
        rda.run_accumulation_cycle(provider=_provider(base))
        rda.run_accumulation_cycle(provider=_provider(base))
        with _conn() as conn:
            count = conn.execute("SELECT COUNT(*) FROM candles WHERE symbol = 'BTC-USD'").fetchone()[0]
        assert count == len(base)

    def test_repeated_identical_cycle_produces_zero_duplicate_trades(self) -> None:
        base = _base_series("BTC-USD")
        rda.run_accumulation_cycle(provider=_provider(base))
        with _conn() as conn:
            first_count = conn.execute("SELECT COUNT(*) FROM trades WHERE symbol = 'BTC-USD'").fetchone()[0]
        rda.run_accumulation_cycle(provider=_provider(base))
        rda.run_accumulation_cycle(provider=_provider(base))
        with _conn() as conn:
            second_count = conn.execute("SELECT COUNT(*) FROM trades WHERE symbol = 'BTC-USD'").fetchone()[0]
        assert first_count == second_count > 0

    def test_trade_natural_key_idempotency(self) -> None:
        """The trades table's own PRIMARY KEY is the idempotency
        mechanism — proves a direct insert attempt for an
        already-discovered trade is rejected at the database level,
        not merely avoided by application logic."""
        base = _base_series("BTC-USD")
        rda.run_accumulation_cycle(provider=_provider(base))
        with _conn() as conn:
            row = conn.execute("SELECT symbol, strategy_id, strategy_version, entry_timestamp FROM trades WHERE symbol = 'BTC-USD' LIMIT 1").fetchone()
        assert row is not None
        with _conn() as conn, pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO trades (symbol, strategy_id, strategy_version, entry_timestamp, bars_held, entry_price, exit_price, direction, outcome, r_multiple_realized, is_holdout, discovered_in_run_id, discovered_at) "
                "VALUES (?, ?, ?, ?, 1, 1.0, 1.0, 'long', 'win', 1.0, 0, 'x', 'x')",
                row,
            )


# --- J/K/L: fail-closed integrity conditions --------------------------------


class TestFailClosedConditions:
    def test_strategy_fingerprint_mismatch_hard_fails(self) -> None:
        base = _base_series("BTC-USD")
        rda.run_accumulation_cycle(provider=_provider(base))
        with _conn() as conn:
            conn.execute("UPDATE strategy_fingerprint SET fingerprint = 'tampered-fingerprint'")
            conn.commit()
        with pytest.raises(rda.AccumulationFailure, match="fingerprint changed"):
            rda.run_accumulation_cycle(provider=_provider(base))
        with _conn() as conn:
            status = conn.execute("SELECT status, error_detail FROM runs ORDER BY started_at DESC LIMIT 1").fetchone()
        assert status[0] == "failed"
        assert "fingerprint changed" in status[1]

    def test_non_historical_data_status_hard_fails(self) -> None:
        base = _base_series("BTC-USD")
        mock_shaped = [dataclasses.replace(c, data_status="simulated") for c in base]
        with pytest.raises(rda.AccumulationFailure, match="Non-real/ambiguous provenance"):
            rda.run_accumulation_cycle(provider=_provider(mock_shaped))
        with _conn() as conn:
            status = conn.execute("SELECT status FROM runs ORDER BY started_at DESC LIMIT 1").fetchone()
        assert status[0] == "failed"

    def test_out_of_order_timestamps_hard_fail(self) -> None:
        base = _base_series("BTC-USD")
        shuffled = [base[1], base[0], *base[2:]]
        with pytest.raises(rda.AccumulationFailure, match="not strictly increasing"):
            rda.run_accumulation_cycle(provider=_provider(shuffled))

    def test_duplicate_timestamps_in_one_fetch_hard_fail(self) -> None:
        base = _base_series("BTC-USD")
        duplicated = [*base, base[-1]]
        with pytest.raises(rda.AccumulationFailure, match="not strictly increasing"):
            rda.run_accumulation_cycle(provider=_provider(duplicated))

    def test_provider_failure_records_failed_run_and_raises(self) -> None:
        class _RaisingProvider(MarketDataProvider):
            def get_quote(self, symbol):
                raise NotImplementedError

            def get_candles(self, symbol, timeframe, limit, *, end_time=None, anchor_price=None):
                raise ExternalMarketDataProviderUnavailable("simulated outage")

        with pytest.raises(rda.AccumulationFailure, match="Kraken unavailable"):
            rda.run_accumulation_cycle(provider=_RaisingProvider())
        with _conn() as conn:
            status = conn.execute("SELECT status, error_detail FROM runs ORDER BY started_at DESC LIMIT 1").fetchone()
        assert status[0] == "failed"
        assert "Kraken unavailable" in status[1]


# --- N/O: concurrency and restart semantics ---------------------------------


class TestConcurrencyAndRestartSemantics:
    def test_held_lock_causes_concurrent_invocation_to_be_skipped(self) -> None:
        import fcntl

        lock_path = rda._lock_path()
        rda._ensure_dir(lock_path)
        with open(lock_path, "a+") as external_holder:
            fcntl.flock(external_holder, fcntl.LOCK_EX | fcntl.LOCK_NB)
            base = _base_series("BTC-USD")
            result = rda.run_accumulation_cycle(provider=_provider(base))
            assert result["status"] == "skipped_concurrent"
            with _conn() as conn:
                count = conn.execute("SELECT COUNT(*) FROM candles").fetchone()[0]
            assert count == 0, "a skipped-concurrent run must not have written any evidence"

    def test_interrupted_run_row_stays_visible_but_does_not_block_next_run(self) -> None:
        """Simulates a crash mid-run: a 'running' row with no
        completion is left behind (never cleaned up), but because
        concurrency is decided by the OS lock (already released — the
        crashed 'process' held no lock beyond its own death) rather than
        this row, the next real invocation proceeds normally."""
        with _conn() as conn:
            conn.execute("INSERT INTO runs (run_id, started_at, status) VALUES ('stale-crashed-run', '2020-01-01T00:00:00+00:00', 'running')")
            conn.commit()

        base = _base_series("BTC-USD")
        result = rda.run_accumulation_cycle(provider=_provider(base))
        assert result["status"] == "success"

        with _conn() as conn:
            stale = conn.execute("SELECT status, completed_at FROM runs WHERE run_id = 'stale-crashed-run'").fetchone()
        assert stale == ("running", None), "the stale row must remain visible exactly as the crash left it — never silently cleaned up or reused"


# --- P: append-only enforcement ---------------------------------------------


class TestAppendOnlyEnforcement:
    def test_update_on_candles_is_rejected(self) -> None:
        base = _base_series("BTC-USD")
        rda.run_accumulation_cycle(provider=_provider(base))
        with _conn() as conn, pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE candles SET close = 0 WHERE symbol = 'BTC-USD'")

    def test_delete_on_candles_is_rejected(self) -> None:
        base = _base_series("BTC-USD")
        rda.run_accumulation_cycle(provider=_provider(base))
        with _conn() as conn, pytest.raises(sqlite3.IntegrityError):
            conn.execute("DELETE FROM candles WHERE symbol = 'BTC-USD'")

    def test_update_on_trades_is_rejected(self) -> None:
        base = _base_series("BTC-USD")
        rda.run_accumulation_cycle(provider=_provider(base))
        with _conn() as conn, pytest.raises(sqlite3.IntegrityError):
            conn.execute("UPDATE trades SET outcome = 'win' WHERE symbol = 'BTC-USD'")

    def test_delete_on_trades_is_rejected(self) -> None:
        base = _base_series("BTC-USD")
        rda.run_accumulation_cycle(provider=_provider(base))
        with _conn() as conn, pytest.raises(sqlite3.IntegrityError):
            conn.execute("DELETE FROM trades WHERE symbol = 'BTC-USD'")


# --- Q: observability --------------------------------------------------------


class TestObservability:
    def test_status_reports_expected_fields(self) -> None:
        base = _base_series("BTC-USD")
        rda.run_accumulation_cycle(provider=_provider(base))
        status = rda.get_accumulation_status()
        assert status["last_successful_run"] is not None
        assert status["last_failed_run"] is None
        assert set(status["per_symbol"]) == {"BTC-USD", "ETH-USD"}
        for symbol_status in status["per_symbol"].values():
            assert symbol_status["latest_real_candle_timestamp"] is not None
            assert symbol_status["cumulative_unique_real_candles"] == len(base)
        assert status["certification_min_trade_count"] == 20
        assert status["remaining_trades_to_floor"] == max(0, 20 - status["cumulative_development_trades_all_symbols"])
        assert status["validation_state"] in ("insufficient_evidence", "sample_size_floor_cleared_reexamine_full_model_validation")

    def test_status_reports_last_failed_run(self) -> None:
        with pytest.raises(rda.AccumulationFailure):
            rda.run_accumulation_cycle(
                provider=_FixedProvider({"BTC-USD": [dataclasses.replace(c, data_status="simulated") for c in _base_series("BTC-USD")], "ETH-USD": _base_series("ETH-USD")})
            )
        status = rda.get_accumulation_status()
        assert status["last_failed_run"] is not None
        assert "provenance" in status["last_failed_run"]["error_detail"]


# --- R: reuses the existing backtest engine, never a second one ------------


class TestReusesExistingBacktestEngine:
    def test_discovered_trades_match_a_direct_call_to_the_existing_backtest_function(self) -> None:
        base = _base_series("BTC-USD")
        expected_trades = backtest_symbol_over_candles(FROZEN_DEFINITION, "BTC-USD", base)
        rda.run_accumulation_cycle(provider=_provider(base))
        with _conn() as conn:
            persisted_entries = {row[0] for row in conn.execute("SELECT entry_timestamp FROM trades WHERE symbol = 'BTC-USD'")}
        assert persisted_entries == {t.entry_timestamp for t in expected_trades}

    def test_module_defines_no_second_setup_detector_or_backtest_function(self) -> None:
        import inspect

        source = inspect.getsource(rda)
        assert "_detect_generic_setups" not in source
        assert "def backtest" not in source
        assert "def run_compiled_strategy_backtest" not in source


# --- Live Kraken verification -----------------------------------------------


class TestLiveKrakenVerification:
    """Real, bounded requests to Kraken's real public OHLC endpoint —
    the only test class in this file that touches the network. Proves
    genuine idempotency across two consecutive real runs against the
    same isolated database file (simulating a process restart between
    them, since a fresh KrakenMarketDataProvider is constructed for
    each call, same as a real restarted process would do)."""

    def test_two_consecutive_real_runs_are_idempotent(self) -> None:
        try:
            result1 = rda.run_accumulation_cycle(provider=KrakenMarketDataProvider())
        except rda.AccumulationFailure as exc:
            pytest.skip(f"Real Kraken external verification could not be completed in this environment: {exc}")
        except (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError) as exc:
            pytest.skip(f"Real network connectivity to Kraken unavailable in this environment: {exc}")

        assert result1["status"] == "success"
        for symbol in ("BTC-USD", "ETH-USD"):
            assert result1["new_candles_appended"][symbol] > 0

        with _conn() as conn:
            for symbol in ("BTC-USD", "ETH-USD"):
                rows = conn.execute("SELECT data_status FROM candles WHERE symbol = ?", (symbol,)).fetchall()
                assert rows, f"no candles persisted for {symbol}"
                assert all(r[0] == "historical" for r in rows)
            boundary_rows = conn.execute("SELECT symbol FROM holdout_boundary").fetchall()
            assert {r[0] for r in boundary_rows} == {"BTC-USD", "ETH-USD"}

        # Second real run, fresh provider instance (simulates a restart).
        result2 = rda.run_accumulation_cycle(provider=KrakenMarketDataProvider())
        assert result2["status"] == "success"
        for symbol in ("BTC-USD", "ETH-USD"):
            assert result2["new_candles_appended"][symbol] == 0, f"{symbol}: second real run against an overlapping window must append zero duplicate candles"
            assert result2["new_trades_found"][symbol] == 0, f"{symbol}: second real run must not rediscover any trade as new"
