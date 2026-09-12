"""app/real_data_accumulator.py — CEO directive "TradeTown — Real-Time
Accumulation 1.0."

RESEARCH FIRST. Phase 0's own audit (see this milestone's final report)
found no existing structure this could safely reuse for its two real
requirements — durable append-only storage for real external market
data, and a real-wall-clock-driven trigger:

  - `app/state.py`'s "Autonomous Research Orchestrator"
    (`maybe_orchestrate_research()`) is cadenced in SIMULATED days
    (`RESEARCH_CADENCE_SIM_DAYS`), ~150x accelerated relative to real
    time at this codebase's default tick settings, and its job is
    strategy MUTATION/discovery over mock data
    (`submit_research_factory_run()`) — reusing it would either mismatch
    real 1h Kraken candle boundaries or risk mutating the frozen
    strategy this module must never touch. Not reused.
  - `FactoryRunRecord`'s own "never mutated, never deleted" convention
    is real and worth following, but the CONTAINER it lives in
    (`GameSaveState`, persisted via `app/persistence.py`'s `SLOT`) is
    the wrong home for real external market data: a save-slot switch
    can repoint the process-wide `game_state` singleton at a different
    save entirely, which would corrupt or lose data that isn't actually
    game state. This is the identical reasoning "Read-Only MCP Boundary
    1.0" already applied to its own append-only audit log (isolated
    SQLite, deliberately not `AuditEntry`/`GameSaveState`) — reused
    here, not reinvented.

WHAT THIS MODULE DOES: an idempotent, safely-repeatable accumulation
cycle (`run_accumulation_cycle()`), backed by its own isolated SQLite
database (`data/real_data_accumulation.db`, in the SAME already-durable
`tradetown-data` volume `DATABASE_URL` already uses — zero Docker/Compose
changes needed for restart-durability). It is NOT wired into
`app/sim.py`'s live tick loop and does not add a scheduler of its own —
invoking it is left to an external real-wall-clock trigger (cron, or an
OpenClaw automation), exactly because no real-wall-clock scheduler
exists inside this codebase to hook into, and building an in-process one
would risk stalling the live game loop on a real network call. It is
safe to invoke repeatedly, including immediately after a missed
schedule or a process restart — it always fetches whatever real closed
candles Kraken currently serves and reconciles them against what is
already persisted, never fabricating a backfill.

REUSES, NEVER DUPLICATES: `app/market_data.py::KrakenMarketDataProvider`
(unmodified) for real candles; `app/strategy_engine.py::
backtest_symbol_over_candles()` (unmodified, the SAME function
`app/walk_forward.py`/`app/holdout.py` already rely on for their own
no-look-ahead guarantee) for trade discovery; `app/holdout.py::
partition_candles_chronologically()`/`validate_holdout()` (unmodified,
called exactly once per symbol, ever) for the initial holdout freeze.

HOLDOUT INTEGRITY. The existing holdout split is fraction-of-current-
length, not absolute-boundary — safe for a single, fixed snapshot (as
the prior two milestones used it), unsafe to replay against a growing
series (each replay would shift which candles are "the latest 20%,"
silently reclassifying previously-holdout candles as development
evidence the moment new data is appended). This module does NOT attempt
to make the holdout boundary evolve, and does not modify app/holdout.py
at all. It is frozen exactly ONCE per symbol
(`freeze_holdout_baseline()`), using the unmodified existing
partition/validate functions against whatever real window is available
at freeze time, and the resulting ABSOLUTE timestamp boundary is
persisted permanently in `holdout_boundary`. Every later accumulation
cycle classifies newly discovered trades against that persisted,
never-recomputed boundary via plain timestamp-string comparison —
`is_holdout=1` if the trade's entry timestamp falls inside it,
`is_holdout=0` otherwise. Holdout trades are tracked separately and are
NEVER counted toward the cumulative development-evidence sample size
this module reports toward the 20-trade floor — the same "holdout
reported separately, never blended into the primary verdict" convention
both prior real-data milestones already established.

CRASH/RESTART SAFETY — explicit transaction boundaries, not an assumed
"SQLite auto-commits everything." The `runs` row is inserted with
status='running' and committed immediately, before any symbol work
starts, so an interrupted run stays permanently visible in the audit
trail (never cleaned up, never reused to decide anything). Each symbol
then gets exactly one transaction: fetch -> append that symbol's new
candles -> discover and insert that symbol's new trades -> commit (or
full rollback on any exception inside it) — a crash loses at most one
symbol's still-uncommitted work for the CURRENT run; every previously
committed symbol, and every previously completed run, is untouched.
Concurrency is decided by a real OS advisory file lock
(`fcntl.flock(LOCK_EX | LOCK_NB)` on `data/real_data_accumulation.lock`),
never by the persisted 'running' row — a lock's liveness is tied to the
holding process by the OS itself, so it is released automatically on
crash/kill with no heartbeat or extra machinery required. This is
single-host locking (correct for this deployment: one VPS, one process
at a time), not a distributed lock — a real, disclosed scope limit, not
a silent gap.

FAIL-CLOSED. Every one of Phase 10's listed conditions raises
`AccumulationFailure` (recorded as a failed run row, never a silent
partial success): Kraken unavailable, malformed data, non-real
provenance, a conflicting duplicate candle (a previously-stored real
candle whose OHLCV differs from a newly fetched one for the identical
timestamp — an external data-integrity failure, never silently
overwritten), timestamps moving backward, a concurrent run already in
progress, or the frozen strategy's own fingerprint/version changing
unexpectedly between runs.

TIMEFRAME-AWARE PERSISTENCE — CEO directive "TradeTown — Timeframe-Aware
Real-Data Research Infrastructure 1.0." Until this pass, `TIMEFRAME` was
a single hardcoded `"1h"` module constant threaded through every table's
identity — `holdout_boundary`'s primary key was `(symbol, strategy_id,
strategy_version)` with no timeframe dimension at all, and `trades`'
primary key was `(symbol, strategy_id, strategy_version, entry_timestamp)`.
Both are genuinely unsafe to extend to a second timeframe as-is: a 4h
bar and a 1h bar routinely land on the IDENTICAL wall-clock timestamp
(every 4th 1h boundary is also a 4h boundary), so two DIFFERENT real
trades — one discovered from 1h candles, one from 4h candles, for the
same symbol/strategy — could collide on that same primary key and be
silently treated as the same row. `TIMEFRAME` is now `TIMEFRAMES`, a
small, explicit, deliberately-bounded tuple (`("1h", "4h")` — Section
10's own "smallest safe increment": the existing 1h evidence plus
exactly one new, live-verified-cleanest additional interval; 1m/5m/15m/
1d stay out of production accumulation until this architecture is
proven). `holdout_boundary` and `trades` both gain an explicit
`timeframe` column AS PART OF THEIR PRIMARY KEY, via `_migrate_legacy_
timeframe_columns()` below — a real, one-time, idempotent schema
migration, not a fresh design: any row either table held before this
migration was written EXCLUSIVELY by this module's own previously-
single-valued `TIMEFRAME = "1h"` constant (there has never been any
other code path, in this codebase's entire history, that writes to
either table), so backfilling `timeframe='1h'` for a pre-existing row
is a proven historical fact, never a guess. The legacy tables are
renamed (never dropped) so the migration is provably lossless and
auditable. `candles` already carried `timeframe` in its own primary key
from day one — genuinely unaffected. `strategy_fingerprint` is
DELIBERATELY left keyed on `(strategy_id, strategy_version)` alone:
strategy identity is what rules a definition compiles to, not what
dataset it is tested against — the identical frozen strategy is
evaluated at both 1h and 4h without becoming "a different strategy,"
exactly as Section 4/5 of the directive requires ("strategy identity !=
dataset/timeframe identity"). `_get_frozen_definition()` is therefore
UNCHANGED — one frozen definition serves every timeframe.

Every candle a real Kraken response returns for a requested timeframe
already carries that SAME timeframe on its own `Candle.timeframe`
field (see `KrakenMarketDataProvider._parse_kraken_response()`) — this
module additionally asserts that structural fact explicitly for every
fetched batch before persisting it (Section 8's hard invariant:
`dataset.timeframe == requested.timeframe` for every candle), so a
provider bug could never silently persist a mixed-timeframe dataset
under one label.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import sqlite3
import sys
import uuid
from contextlib import closing
from datetime import datetime, timezone

from app.holdout import freeze_strategy, partition_candles_chronologically, validate_holdout
from app.market_data import Candle, ExternalMarketDataProviderUnavailable, KrakenMarketDataProvider, MarketDataProvider
from app.schemas import CompiledStrategyDefinition
from app.strategy_engine import backtest_symbol_over_candles
from app.strategy_registry import default_researchable_strategies

DEFAULT_DB_PATH = "data/real_data_accumulation.db"
SYMBOLS = ("BTC-USD", "ETH-USD")
# Section 10 — deliberately the smallest safe increment: the existing,
# already-accumulated "1h" plus exactly one new, live-verified-cleanest
# additional interval. 1m/5m/15m/1d remain intentionally excluded from
# production accumulation until this timeframe-aware architecture is
# proven. Never expanded silently — see this module's own docstring.
TIMEFRAMES: tuple[str, ...] = ("1h", "4h")
# The one timeframe every row in `holdout_boundary`/`trades` was ever
# written under before this module became timeframe-aware — a proven
# historical fact (see `_migrate_legacy_timeframe_columns()`), not a
# default chosen for convenience.
_LEGACY_TIMEFRAME = "1h"
PROVIDER_NAME = "kraken"
STRATEGY_DEFINITION_ID = "50-ema-breakout-pullback-long"


class AccumulationFailure(Exception):
    """Every fail-closed condition this module detects raises this —
    never a silent partial success, never a fallback to mock data."""


def _db_path() -> str:
    return os.environ.get("REAL_DATA_ACCUMULATOR_DB_PATH", DEFAULT_DB_PATH)


def _lock_path() -> str:
    return _db_path() + ".lock"


def _ensure_dir(path: str) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)


def _connect() -> sqlite3.Connection:
    path = _db_path()
    _ensure_dir(path)
    conn = sqlite3.connect(path, timeout=30.0)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (table,)).fetchone() is not None


def _column_names(conn: sqlite3.Connection, table: str) -> set[str]:
    return {row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def _migrate_legacy_holdout_boundary(conn: sqlite3.Connection) -> None:
    """A no-op on a fresh database (the table doesn't exist yet — the
    `CREATE TABLE IF NOT EXISTS` below creates it with the new schema
    directly) and a no-op on an already-migrated one (the `timeframe`
    column already exists). Otherwise: renames the legacy table (never
    drops it — the migration must be provably lossless and auditable),
    creates the new-schema table, and copies every row across with
    `timeframe='1h'` explicitly backfilled — the one value every row
    this table has ever held was proven to have (see this module's own
    docstring)."""
    if not _table_exists(conn, "holdout_boundary") or "timeframe" in _column_names(conn, "holdout_boundary"):
        return
    conn.execute("ALTER TABLE holdout_boundary RENAME TO holdout_boundary_legacy_pre_timeframe")
    conn.execute(
        """
        CREATE TABLE holdout_boundary (
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            strategy_id TEXT NOT NULL,
            strategy_version INTEGER NOT NULL,
            holdout_start_timestamp TEXT NOT NULL,
            holdout_end_timestamp TEXT NOT NULL,
            frozen_at TEXT NOT NULL,
            dataset_content_hash TEXT NOT NULL,
            PRIMARY KEY (symbol, timeframe, strategy_id, strategy_version)
        )
        """
    )
    conn.execute(
        f"""
        INSERT INTO holdout_boundary
            (symbol, timeframe, strategy_id, strategy_version, holdout_start_timestamp, holdout_end_timestamp, frozen_at, dataset_content_hash)
        SELECT symbol, '{_LEGACY_TIMEFRAME}', strategy_id, strategy_version, holdout_start_timestamp, holdout_end_timestamp, frozen_at, dataset_content_hash
        FROM holdout_boundary_legacy_pre_timeframe
        """
    )
    conn.commit()


def _migrate_legacy_trades(conn: sqlite3.Connection) -> None:
    """Same treatment as `_migrate_legacy_holdout_boundary()` above, for
    `trades`' own primary key."""
    if not _table_exists(conn, "trades") or "timeframe" in _column_names(conn, "trades"):
        return
    conn.execute("ALTER TABLE trades RENAME TO trades_legacy_pre_timeframe")
    conn.execute(
        """
        CREATE TABLE trades (
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            strategy_id TEXT NOT NULL,
            strategy_version INTEGER NOT NULL,
            entry_timestamp TEXT NOT NULL,
            bars_held INTEGER NOT NULL,
            entry_price REAL NOT NULL,
            exit_price REAL,
            direction TEXT NOT NULL,
            outcome TEXT NOT NULL,
            r_multiple_realized REAL NOT NULL,
            is_holdout INTEGER NOT NULL,
            discovered_in_run_id TEXT NOT NULL,
            discovered_at TEXT NOT NULL,
            PRIMARY KEY (symbol, timeframe, strategy_id, strategy_version, entry_timestamp)
        )
        """
    )
    conn.execute(
        f"""
        INSERT INTO trades
            (symbol, timeframe, strategy_id, strategy_version, entry_timestamp, bars_held, entry_price, exit_price,
             direction, outcome, r_multiple_realized, is_holdout, discovered_in_run_id, discovered_at)
        SELECT symbol, '{_LEGACY_TIMEFRAME}', strategy_id, strategy_version, entry_timestamp, bars_held, entry_price, exit_price,
               direction, outcome, r_multiple_realized, is_holdout, discovered_in_run_id, discovered_at
        FROM trades_legacy_pre_timeframe
        """
    )
    conn.commit()


def _migrate_legacy_timeframe_columns(conn: sqlite3.Connection) -> None:
    """One-time, idempotent schema migration — see this module's own
    docstring for the full "why." Must run BEFORE the `CREATE TABLE IF
    NOT EXISTS` statements in `init_schema()`, since it needs the OLD
    table (if any) still present under its original name to detect and
    migrate it."""
    _migrate_legacy_holdout_boundary(conn)
    _migrate_legacy_trades(conn)


def init_schema(conn: sqlite3.Connection) -> None:
    _migrate_legacy_timeframe_columns(conn)
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS candles (
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            provider TEXT NOT NULL,
            candle_timestamp TEXT NOT NULL,
            fetch_timestamp TEXT NOT NULL,
            open REAL NOT NULL,
            high REAL NOT NULL,
            low REAL NOT NULL,
            close REAL NOT NULL,
            volume REAL NOT NULL,
            data_status TEXT NOT NULL,
            PRIMARY KEY (symbol, timeframe, provider, candle_timestamp)
        );

        CREATE TABLE IF NOT EXISTS trades (
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            strategy_id TEXT NOT NULL,
            strategy_version INTEGER NOT NULL,
            entry_timestamp TEXT NOT NULL,
            bars_held INTEGER NOT NULL,
            entry_price REAL NOT NULL,
            exit_price REAL,
            direction TEXT NOT NULL,
            outcome TEXT NOT NULL,
            r_multiple_realized REAL NOT NULL,
            is_holdout INTEGER NOT NULL,
            discovered_in_run_id TEXT NOT NULL,
            discovered_at TEXT NOT NULL,
            -- Section 3/4/7 — timeframe joins the identity: a 4h bar and
            -- a 1h bar routinely share the identical wall-clock
            -- timestamp (every 4th 1h boundary is also a 4h boundary),
            -- so two real, DIFFERENT trades discovered from different
            -- timeframes' candles must never collide on this key.
            PRIMARY KEY (symbol, timeframe, strategy_id, strategy_version, entry_timestamp)
        );

        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            status TEXT NOT NULL,
            strategy_id TEXT,
            strategy_version INTEGER,
            strategy_fingerprint TEXT,
            symbols_processed TEXT,
            new_candles_appended TEXT,
            new_trades_found TEXT,
            error_detail TEXT
        );

        CREATE TABLE IF NOT EXISTS holdout_boundary (
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            strategy_id TEXT NOT NULL,
            strategy_version INTEGER NOT NULL,
            holdout_start_timestamp TEXT NOT NULL,
            holdout_end_timestamp TEXT NOT NULL,
            frozen_at TEXT NOT NULL,
            dataset_content_hash TEXT NOT NULL,
            -- Section 13 — BTC/1h/strategyX and BTC/4h/strategyX (and
            -- likewise BTC/4h vs ETH/4h) must freeze fully independent
            -- boundaries; a strategy's own identity is unaffected by
            -- which timeframe it is being evaluated against (Section
            -- 4/5 — strategy identity != dataset/timeframe identity),
            -- so `strategy_fingerprint` below is deliberately NOT keyed
            -- on timeframe while this table explicitly is.
            PRIMARY KEY (symbol, timeframe, strategy_id, strategy_version)
        );

        CREATE TABLE IF NOT EXISTS strategy_fingerprint (
            strategy_id TEXT NOT NULL,
            strategy_version INTEGER NOT NULL,
            fingerprint TEXT NOT NULL,
            first_recorded_at TEXT NOT NULL,
            PRIMARY KEY (strategy_id, strategy_version)
        );

        -- Immutability guards, the same pattern "Read-Only MCP Boundary
        -- 1.0" already established for its own append-only audit log:
        -- a real candle or trade row must never be UPDATEd or DELETEd,
        -- only inserted (and de-duplicated via its own PRIMARY KEY).
        CREATE TRIGGER IF NOT EXISTS candles_no_update
        BEFORE UPDATE ON candles BEGIN
            SELECT RAISE(ABORT, 'candles is append-only: rows may never be updated');
        END;
        CREATE TRIGGER IF NOT EXISTS candles_no_delete
        BEFORE DELETE ON candles BEGIN
            SELECT RAISE(ABORT, 'candles is append-only: rows may never be deleted');
        END;
        CREATE TRIGGER IF NOT EXISTS trades_no_update
        BEFORE UPDATE ON trades BEGIN
            SELECT RAISE(ABORT, 'trades is append-only: rows may never be updated');
        END;
        CREATE TRIGGER IF NOT EXISTS trades_no_delete
        BEFORE DELETE ON trades BEGIN
            SELECT RAISE(ABORT, 'trades is append-only: rows may never be deleted');
        END;
        """
    )
    conn.commit()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _strategy_fingerprint(definition: CompiledStrategyDefinition) -> str:
    identity = {"id": definition.id, "version": definition.version, "status": definition.status, "timeframe": definition.timeframe, "source_text": definition.source_text}
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode("utf-8")).hexdigest()


def _get_frozen_definition() -> CompiledStrategyDefinition:
    _strategies, registry = default_researchable_strategies()
    return registry[STRATEGY_DEFINITION_ID][0]


def _check_strategy_fingerprint(conn: sqlite3.Connection, definition: CompiledStrategyDefinition, fingerprint: str) -> None:
    row = conn.execute(
        "SELECT fingerprint FROM strategy_fingerprint WHERE strategy_id = ? AND strategy_version = ?", (definition.id, definition.version)
    ).fetchone()
    if row is None:
        conn.execute(
            "INSERT INTO strategy_fingerprint (strategy_id, strategy_version, fingerprint, first_recorded_at) VALUES (?, ?, ?, ?)",
            (definition.id, definition.version, fingerprint, _now_iso()),
        )
        conn.commit()
        return
    (recorded_fingerprint,) = row
    if recorded_fingerprint != fingerprint:
        raise AccumulationFailure(
            f"Strategy fingerprint changed for {definition.id!r} v{definition.version} — was {recorded_fingerprint[:16]}..., now {fingerprint[:16]}... "
            "This module refuses to accumulate evidence for a strategy that mutated mid-accumulation."
        )


def _append_candles(conn: sqlite3.Connection, symbol: str, timeframe: str, candles: list[Candle]) -> int:
    """Inserts each real candle, deduplicated by its own PRIMARY KEY.
    A candle already on file with IDENTICAL OHLCV is silently skipped
    (the same real observation, re-seen because Kraken's window
    overlaps). A candle already on file with DIFFERENT OHLCV for the
    SAME timestamp is a genuine data-integrity failure — raised, never
    silently overwritten. `candles` table has always been keyed on
    `timeframe` (unlike `trades`/`holdout_boundary` — see this module's
    own docstring), so a 1h and a 4h candle at the same timestamp were
    always independent rows here; no migration was needed for this
    table. Caller owns the transaction."""
    fetch_timestamp = _now_iso()
    new_count = 0
    for candle in candles:
        existing = conn.execute(
            "SELECT open, high, low, close, volume, data_status FROM candles WHERE symbol = ? AND timeframe = ? AND provider = ? AND candle_timestamp = ?",
            (symbol, timeframe, PROVIDER_NAME, candle.timestamp),
        ).fetchone()
        if existing is not None:
            incoming = (candle.open, candle.high, candle.low, candle.close, candle.volume, candle.data_status)
            if tuple(existing) != incoming:
                raise AccumulationFailure(
                    f"Conflicting duplicate candle for {symbol} at {timeframe} {candle.timestamp}: stored={tuple(existing)} incoming={incoming}. "
                    "Treating this as a data-integrity failure rather than silently replacing the stored observation."
                )
            continue
        conn.execute(
            "INSERT INTO candles (symbol, timeframe, provider, candle_timestamp, fetch_timestamp, open, high, low, close, volume, data_status) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (symbol, timeframe, PROVIDER_NAME, candle.timestamp, fetch_timestamp, candle.open, candle.high, candle.low, candle.close, candle.volume, candle.data_status),
        )
        new_count += 1
    return new_count


def freeze_holdout_baseline(conn: sqlite3.Connection, symbol: str, timeframe: str, definition: CompiledStrategyDefinition, candles: list[Candle]) -> None:
    """One-time-per-(symbol, timeframe) holdout designation, reusing the
    EXISTING, UNCHANGED `partition_candles_chronologically()`/
    `validate_holdout()`. A no-op if this exact (symbol, timeframe,
    strategy_id, strategy_version) already has a frozen boundary on
    file — never called a second time against a grown series (see this
    module's own docstring for why that would be unsafe). Section 13 —
    BTC/1h and BTC/4h freeze fully independent boundaries because
    `timeframe` is now part of `holdout_boundary`'s own primary key; the
    strategy's own identity (`definition.id`/`.version`) is unaffected
    by which timeframe it is evaluated against. Caller owns the
    transaction."""
    existing = conn.execute(
        "SELECT 1 FROM holdout_boundary WHERE symbol = ? AND timeframe = ? AND strategy_id = ? AND strategy_version = ?",
        (symbol, timeframe, definition.id, definition.version),
    ).fetchone()
    if existing is not None:
        return
    train, validation, holdout = partition_candles_chronologically(candles)
    content_hash = hashlib.sha256("".join(f"{c.symbol}|{c.timeframe}|{c.timestamp}|{c.open}|{c.high}|{c.low}|{c.close}|{c.volume}\n" for c in candles).encode("utf-8")).hexdigest()
    freeze = freeze_strategy(definition, dataset_version=content_hash, feature_versions=[])
    report = validate_holdout(
        definition,
        train=train,
        validation=validation,
        holdout=holdout,
        dataset_id=f"kraken-{symbol}-{timeframe}-baseline",
        dataset_version=content_hash,
        freeze=freeze,
        report_id=f"real-time-accumulation-baseline-{symbol}-{timeframe}",
    )
    if report.status != "valid" or not holdout:
        raise AccumulationFailure(f"Could not establish a valid holdout baseline for {symbol} at {timeframe}: {report.status} — {report.detail}")
    conn.execute(
        "INSERT INTO holdout_boundary (symbol, timeframe, strategy_id, strategy_version, holdout_start_timestamp, holdout_end_timestamp, frozen_at, dataset_content_hash) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (symbol, timeframe, definition.id, definition.version, holdout[0].timestamp, holdout[-1].timestamp, _now_iso(), content_hash),
    )


def _holdout_bounds(conn: sqlite3.Connection, symbol: str, timeframe: str, definition: CompiledStrategyDefinition) -> tuple[str, str] | None:
    row = conn.execute(
        "SELECT holdout_start_timestamp, holdout_end_timestamp FROM holdout_boundary WHERE symbol = ? AND timeframe = ? AND strategy_id = ? AND strategy_version = ?",
        (symbol, timeframe, definition.id, definition.version),
    ).fetchone()
    return (row[0], row[1]) if row is not None else None


def _discover_and_append_trades(conn: sqlite3.Connection, run_id: str, symbol: str, timeframe: str, definition: CompiledStrategyDefinition, candles: list[Candle]) -> int:
    """Re-runs the SAME, unmodified `backtest_symbol_over_candles()`
    over the full currently-available real window (needed for correct
    50-EMA/chandelier-stop warmup — never a second backtest engine) and
    inserts every discovered trade — already-seen trades are naturally
    de-duplicated by the `trades` table's own PRIMARY KEY (symbol,
    timeframe, strategy_id, strategy_version, entry_timestamp), never
    counted twice across overlapping fetches, and never colliding with
    a DIFFERENT timeframe's trade that happens to share the same real
    wall-clock entry instant (Section 3 — a 4h bar and a 1h bar
    routinely land on the identical timestamp). Caller owns the
    transaction."""
    trades = backtest_symbol_over_candles(definition, symbol, candles)
    bounds = _holdout_bounds(conn, symbol, timeframe, definition)
    new_count = 0
    discovered_at = _now_iso()
    for trade in trades:
        is_holdout = 1 if bounds is not None and bounds[0] <= trade.entry_timestamp <= bounds[1] else 0
        existing = conn.execute(
            "SELECT 1 FROM trades WHERE symbol = ? AND timeframe = ? AND strategy_id = ? AND strategy_version = ? AND entry_timestamp = ?",
            (symbol, timeframe, definition.id, definition.version, trade.entry_timestamp),
        ).fetchone()
        if existing is not None:
            continue
        conn.execute(
            "INSERT INTO trades (symbol, timeframe, strategy_id, strategy_version, entry_timestamp, bars_held, entry_price, exit_price, direction, outcome, r_multiple_realized, is_holdout, discovered_in_run_id, discovered_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                symbol,
                timeframe,
                definition.id,
                definition.version,
                trade.entry_timestamp,
                trade.bars_held,
                trade.entry_price,
                trade.exit_price,
                trade.direction,
                trade.outcome,
                trade.r_multiple_realized,
                is_holdout,
                run_id,
                discovered_at,
            ),
        )
        new_count += 1
    return new_count


def _acquire_lock() -> object | None:
    """Real OS advisory lock — released automatically by the kernel if
    this process crashes or is killed, no heartbeat required. Returns
    the open lock-file handle (caller must keep it open and later call
    `_release_lock`) or None if another process genuinely holds it
    right now."""
    path = _lock_path()
    _ensure_dir(path)
    handle = open(path, "a+")  # noqa: SIM115 - lifetime is the whole run, released explicitly below
    try:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        handle.close()
        return None
    return handle


def _release_lock(handle: object) -> None:
    fcntl.flock(handle, fcntl.LOCK_UN)  # type: ignore[arg-type]
    handle.close()  # type: ignore[attr-defined]


def run_accumulation_cycle(*, provider: MarketDataProvider | None = None) -> dict:
    """The one real entry point. Safe to call repeatedly, including
    immediately after a missed schedule or a process restart — always
    reconciles against whatever is already persisted, never fabricates
    a backfill. Returns the completed (or skipped) run's own summary
    dict."""
    provider = provider if provider is not None else KrakenMarketDataProvider()
    run_id = str(uuid.uuid4())
    started_at = _now_iso()

    lock_handle = _acquire_lock()
    if lock_handle is None:
        with closing(_connect()) as conn:
            init_schema(conn)
            conn.execute(
                "INSERT INTO runs (run_id, started_at, completed_at, status, error_detail) VALUES (?, ?, ?, 'skipped_concurrent', ?)",
                (run_id, started_at, _now_iso(), "another process currently holds the accumulation lock"),
            )
            conn.commit()
        return {"run_id": run_id, "status": "skipped_concurrent"}

    try:
        with closing(_connect()) as conn:
            init_schema(conn)
            conn.execute("INSERT INTO runs (run_id, started_at, status) VALUES (?, ?, 'running')", (run_id, started_at))
            conn.commit()

            try:
                definition = _get_frozen_definition()
                fingerprint = _strategy_fingerprint(definition)
                _check_strategy_fingerprint(conn, definition, fingerprint)

                # Section 7/10 — each (symbol, timeframe) pair is its own
                # independent dataset; BTC/1h, BTC/4h, ETH/1h, ETH/4h are
                # four fully separate accumulation targets sharing only
                # the one frozen strategy identity above. Nested by
                # symbol then timeframe (never flattened into a single
                # string key) so every existing caller reading
                # `result["new_candles_appended"][symbol]` gets an
                # explicit, per-timeframe breakdown rather than a
                # silently blended total.
                new_candles_by_symbol: dict[str, dict[str, int]] = {}
                new_trades_by_symbol: dict[str, dict[str, int]] = {}
                for symbol in SYMBOLS:
                    new_candles_by_symbol[symbol] = {}
                    new_trades_by_symbol[symbol] = {}
                    for timeframe in TIMEFRAMES:
                        try:
                            candles = provider.get_candles(symbol, timeframe, 100_000)
                        except ExternalMarketDataProviderUnavailable as exc:
                            raise AccumulationFailure(f"Kraken unavailable for {symbol} at {timeframe}: {exc}") from exc
                        if not candles:
                            raise AccumulationFailure(
                                f"Kraken returned zero real candles for {symbol} at {timeframe} — refusing to proceed rather than treating this as a valid empty accumulation."
                            )
                        if any(c.data_status != "historical" for c in candles):
                            raise AccumulationFailure(f"Non-real/ambiguous provenance for {symbol} at {timeframe}: expected every candle data_status='historical'.")
                        # Section 8's hard invariant: dataset.timeframe ==
                        # requested.timeframe for every candle returned.
                        # A provider bug could otherwise silently persist
                        # a mixed-timeframe dataset under one label.
                        if any(c.timeframe != timeframe for c in candles):
                            raise AccumulationFailure(
                                f"Provider returned a candle whose own timeframe does not match the requested {timeframe!r} for {symbol} — "
                                "refusing to persist a mixed-timeframe dataset."
                            )
                        timestamps = [c.timestamp for c in candles]
                        if timestamps != sorted(timestamps) or len(set(timestamps)) != len(timestamps):
                            raise AccumulationFailure(
                                f"Timestamps not strictly increasing/unique for {symbol} at {timeframe} — refusing to persist out-of-order or duplicate real data."
                            )

                        # One transaction per (symbol, timeframe): candles
                        # and the trades discovered from them commit
                        # together, or neither does.
                        with conn:
                            freeze_holdout_baseline(conn, symbol, timeframe, definition, candles)
                            new_candles_by_symbol[symbol][timeframe] = _append_candles(conn, symbol, timeframe, candles)
                            new_trades_by_symbol[symbol][timeframe] = _discover_and_append_trades(conn, run_id, symbol, timeframe, definition, candles)

                conn.execute(
                    "UPDATE runs SET completed_at = ?, status = 'success', strategy_id = ?, strategy_version = ?, strategy_fingerprint = ?, symbols_processed = ?, new_candles_appended = ?, new_trades_found = ? WHERE run_id = ?",
                    (_now_iso(), definition.id, definition.version, fingerprint, json.dumps(list(SYMBOLS)), json.dumps(new_candles_by_symbol), json.dumps(new_trades_by_symbol), run_id),
                )
                conn.commit()
                return {"run_id": run_id, "status": "success", "new_candles_appended": new_candles_by_symbol, "new_trades_found": new_trades_by_symbol}
            except AccumulationFailure as exc:
                conn.execute("UPDATE runs SET completed_at = ?, status = 'failed', error_detail = ? WHERE run_id = ?", (_now_iso(), str(exc), run_id))
                conn.commit()
                raise
    finally:
        _release_lock(lock_handle)


def get_accumulation_status() -> dict:
    """Read-only observability — Phase 9. No new frontend page and no
    new API route: a pure function, queried directly by tests and by
    this milestone's own live verification. A future caller that wants
    this over HTTP can wrap it in one router line without touching this
    module.

    CEO directive "TradeTown — Timeframe-Aware Real-Data Research
    Infrastructure 1.0," Section 21 — "do not compare 50 trades on 1h
    directly with 50 trades on 4h as if they were interchangeable
    evidence." The prior `per_symbol` shape (one blended trade count per
    symbol, one shared `cumulative_development_trades_all_symbols`
    total) would silently pool development-evidence counts ACROSS
    timeframes into one number — exactly the conflation this directive
    forbids. Replaced with `per_dataset`: one entry per (symbol,
    timeframe) — each an independent research environment with its OWN
    trade counts and its OWN 20-trade-floor verdict, never blended with
    any other timeframe's or symbol's evidence."""
    from app.strategy_lab import CERTIFICATION_MIN_TRADE_COUNT

    with closing(_connect()) as conn:
        init_schema(conn)
        last_success = conn.execute("SELECT run_id, completed_at FROM runs WHERE status = 'success' ORDER BY completed_at DESC LIMIT 1").fetchone()
        last_failure = conn.execute("SELECT run_id, completed_at, error_detail FROM runs WHERE status = 'failed' ORDER BY completed_at DESC LIMIT 1").fetchone()

        per_dataset: list[dict] = []
        for symbol in SYMBOLS:
            for timeframe in TIMEFRAMES:
                latest_candle = conn.execute(
                    "SELECT MAX(candle_timestamp) FROM candles WHERE symbol = ? AND timeframe = ? AND provider = ?", (symbol, timeframe, PROVIDER_NAME)
                ).fetchone()[0]
                candle_count = conn.execute(
                    "SELECT COUNT(*) FROM candles WHERE symbol = ? AND timeframe = ? AND provider = ?", (symbol, timeframe, PROVIDER_NAME)
                ).fetchone()[0]
                dev_trade_count = conn.execute(
                    "SELECT COUNT(*) FROM trades WHERE symbol = ? AND timeframe = ? AND is_holdout = 0", (symbol, timeframe)
                ).fetchone()[0]
                holdout_trade_count = conn.execute(
                    "SELECT COUNT(*) FROM trades WHERE symbol = ? AND timeframe = ? AND is_holdout = 1", (symbol, timeframe)
                ).fetchone()[0]
                per_dataset.append(
                    {
                        "symbol": symbol,
                        "timeframe": timeframe,
                        "latest_real_candle_timestamp": latest_candle,
                        "cumulative_unique_real_candles": candle_count,
                        "cumulative_unique_development_trades": dev_trade_count,
                        "cumulative_unique_holdout_trades": holdout_trade_count,
                        "certification_min_trade_count": CERTIFICATION_MIN_TRADE_COUNT,
                        "remaining_trades_to_floor": max(0, CERTIFICATION_MIN_TRADE_COUNT - dev_trade_count),
                        "validation_state": (
                            "insufficient_evidence" if dev_trade_count < CERTIFICATION_MIN_TRADE_COUNT else "sample_size_floor_cleared_reexamine_full_model_validation"
                        ),
                    }
                )

        return {
            "last_successful_run": {"run_id": last_success[0], "completed_at": last_success[1]} if last_success else None,
            "last_failed_run": {"run_id": last_failure[0], "completed_at": last_failure[1], "error_detail": last_failure[2]} if last_failure else None,
            "per_dataset": per_dataset,
        }


if __name__ == "__main__":
    result = run_accumulation_cycle()
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["status"] in ("success", "skipped_concurrent") else 1)
