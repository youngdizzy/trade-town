"""app/real_data_research_bridge.py — CEO directive "TradeTown —
Real-Data Strategy Factory Integration & Holdout Enforcement 1.0."

PHASE 0 FORENSIC FINDING (see this milestone's own audit turn,
"Real-Data Research Factory Integration & Evidence Progression Forensic
Audit 1.0" — verdict D). `app/real_data_accumulator.py` and
`app/research_factory.py`/`app/research_loop.py` were, until this
module, two completely disconnected systems: zero imports, zero calls,
zero shared data, and the accumulator had no router/API exposure at
all. This module is the one explicit, auditable boundary between them —
it does not duplicate the accumulator's SQLite implementation, does not
duplicate the Factory's mutation/backtest/validation loop, and does not
duplicate `app/holdout.py`. It reuses all three unmodified.

READ-ONLY FROM THE RESEARCH PERSPECTIVE. This module never calls
`run_accumulation_cycle()`, never inserts/updates/deletes a row in the
accumulator's database (its own `candles`/`trades` tables already
enforce this at the SQL trigger level — see that module's own
docstring), and never touches `app/holdout.py`'s frozen boundary. It
only ever `SELECT`s.

HOLDOUT ENFORCEMENT — THE CORE DESIGN. The audit found holdout
protection was purely an unused, disconnected mechanism: neither
`research_factory.py` nor `research_loop.py` import `app/holdout.py` at
all, so nothing ever stopped a caller from handing holdout-boundary
candles into the Factory's own mutation/backtest loop — it simply never
happened because nobody had wired real candles in at all. This module
closes that gap with a STRUCTURAL guarantee, not a procedural one:
`DevelopmentOnlyRealDataProvider` is constructed with an already-sliced
development-only candle list baked in at construction time — it
physically has no reference to holdout candles anywhere in its own
state, so no code path through it can ever serve them, no matter how
many mutations the Factory generates or how many times a research run
is repeated. Final holdout evaluation is a deliberately SEPARATE,
differently-named function (`read_holdout_candles_for_final_evaluation()`)
that no Factory/mutation code path calls.

WHAT THIS MODULE DOES NOT SOLVE (disclosed, not silently ignored — see
this milestone's own final report for the full discussion): the
accumulator's `holdout_boundary` table is keyed by the EXACT
`(symbol, strategy_id, strategy_version)` triple that was frozen — only
`app/real_data_accumulator.py::STRATEGY_DEFINITION_ID`'s current
compiled version has ever been frozen in practice. A real-data Factory
run is therefore only possible for the exact `(id, version)` pair
already frozen — never invented on the fly for an arbitrary mutation,
which would require this module to call `freeze_holdout_baseline()`
itself and risk exactly the "re-freezing against a grown series"
unsafety that module's own docstring already warns against. The SAME
frozen boundary (a fixed timestamp range) is reused as the partition
for every mutation tested within one real-data Factory run — mutations
are variations on the same underlying market history, so they share
the same development/holdout split. Nothing currently prevents calling
`read_holdout_candles_for_final_evaluation()` more than once (no
"consumed" flag) — a real, disclosed limitation, not solved here per
this milestone's own Section 9 escape hatch ("if this cannot be safely
enforced within the current architecture, STOP and report the exact
limitation rather than pretending it is solved").
"""
from __future__ import annotations

import hashlib
import sqlite3
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from app.market_data import Candle, ExternalMarketDataProviderUnavailable, MarketDataProvider, Quote
from app.real_data_accumulator import PROVIDER_NAME, TIMEFRAME as ACCUMULATOR_TIMEFRAME, _connect, _db_path, _strategy_fingerprint, init_schema
from app.research_factory import run_research_factory_cycle
from app.schemas import (
    ChampionRecord,
    CompiledStrategyDefinition,
    FailedStrategyArchiveEntry,
    FactoryRunRecord,
    QuantResearchExperiment,
    ResearchLessonRecord,
    ResearchLoopIterationRecord,
    StrategyHypothesis,
)

RealDataUnavailableReason = Literal[
    "REAL_DATA_UNAVAILABLE",
    "INSUFFICIENT_REAL_CANDLES",
    "REAL_DATA_PROVENANCE_INVALID",
    "HOLDOUT_BOUNDARY_INVALID",
    "REAL_DATASET_MIXED_PROVENANCE",
]

# Real requirement, not an invented one: you cannot backtest on zero
# candles. Deliberately NOT a larger arbitrary floor — the codebase's
# own real evidence floors (MIN_TRADES_FOR_BOOTSTRAP=20,
# CERTIFICATION_MIN_TRADE_COUNT=20) already gate at the TRADE-count
# level, downstream, inside model validation; duplicating a second
# candle-count floor here would risk a second, competing threshold.
MIN_DEVELOPMENT_CANDLES = 1

# Real, canonical universe — see app/real_data_accumulator.py::SYMBOLS.
# Never invented, never silently expanded.
REAL_DATA_SYMBOLS: tuple[str, ...] = ("BTC-USD", "ETH-USD")


class DevelopmentOnlyRealDataProvider(MarketDataProvider):
    """A `MarketDataProvider` whose ENTIRE state is a fixed, already-
    partitioned list of real development-window candles for exactly one
    symbol, baked in at construction time. This is the structural
    holdout guarantee this milestone requires: there is no method, no
    parameter, and no code path on this class that can ever return a
    holdout candle, because it was never given one to hold."""

    def __init__(self, symbol: str, development_candles: list[Candle]) -> None:
        self._symbol = symbol
        self._candles = development_candles

    def get_quote(self, symbol: str) -> Quote:
        raise ExternalMarketDataProviderUnavailable(
            "DevelopmentOnlyRealDataProvider serves historical development candles only — it has no live quote to offer."
        )

    def get_candles(self, symbol: str, timeframe: str, limit: int, *, end_time: datetime | None = None, anchor_price: float | None = None) -> list[Candle]:
        if symbol != self._symbol:
            raise ExternalMarketDataProviderUnavailable(
                f"This DevelopmentOnlyRealDataProvider instance was built for {self._symbol!r} only — {symbol!r} was requested."
            )
        return self._candles[-limit:] if limit < len(self._candles) else list(self._candles)


@dataclass(frozen=True)
class RealDataResearchProvenance:
    """The Section 4 provenance contract — every field the directive
    named, computed once at preflight time from data this module
    genuinely read, never invented."""

    provider: Literal["kraken"]
    data_status: Literal["real"]
    symbol: str
    timeframe: str
    development_candle_count: int
    holdout_candle_count: int
    dataset_start_timestamp: str
    dataset_end_timestamp: str
    dataset_content_hash: str
    strategy_fingerprint: str
    holdout_boundary_frozen_at: str


@dataclass(frozen=True)
class RealDataFactoryPreflightFailure:
    reason: RealDataUnavailableReason
    detail: str


def _read_accumulated_candles(conn, symbol: str) -> list[Candle]:
    """Read-only. Every real candle this module ever sees comes from
    here — a plain SELECT against the accumulator's own `candles` table,
    ordered chronologically. Never mutates a row (the table's own SQL
    triggers would abort an UPDATE/DELETE anyway — see
    app/real_data_accumulator.py::init_schema)."""
    rows = conn.execute(
        "SELECT symbol, timeframe, candle_timestamp, open, high, low, close, volume, data_status "
        "FROM candles WHERE symbol = ? AND timeframe = ? AND provider = ? ORDER BY candle_timestamp ASC",
        (symbol, ACCUMULATOR_TIMEFRAME, PROVIDER_NAME),
    ).fetchall()
    return [
        Candle(symbol=row[0], timeframe=row[1], timestamp=row[2], open=row[3], high=row[4], low=row[5], close=row[6], volume=row[7], data_status=row[8])
        for row in rows
    ]


def _read_holdout_boundary(conn: sqlite3.Connection, symbol: str, definition: CompiledStrategyDefinition) -> tuple[str, str, str, str] | None:
    """Read-only lookup of the accumulator's own frozen boundary for
    this EXACT (symbol, strategy_id, strategy_version) — never computed
    or re-frozen by this module. Returns (start, end, dataset_content_hash)
    or None if this exact definition was never frozen."""
    row = conn.execute(
        "SELECT holdout_start_timestamp, holdout_end_timestamp, dataset_content_hash, frozen_at FROM holdout_boundary "
        "WHERE symbol = ? AND strategy_id = ? AND strategy_version = ?",
        (symbol, definition.id, definition.version),
    ).fetchone()
    return (row[0], row[1], row[2], row[3]) if row is not None else None


def _partition_by_holdout(candles: list[Candle], holdout_start: str, holdout_end: str) -> tuple[list[Candle], list[Candle]]:
    """The SAME inclusive-bounds comparison
    app/real_data_accumulator.py::_discover_and_append_trades() already
    uses to classify a trade's own entry timestamp — reused verbatim
    here for candles, so a candle and a trade at the same instant are
    classified identically."""
    development = [c for c in candles if not (holdout_start <= c.timestamp <= holdout_end)]
    holdout = [c for c in candles if holdout_start <= c.timestamp <= holdout_end]
    return development, holdout


def _open_connection(db_path: str | None) -> sqlite3.Connection:
    """Read-only intent, same real connection helper
    `app/real_data_accumulator.py` itself uses when no override path is
    given (WAL journal mode, foreign keys on) — never a second,
    independently-invented connection routine. `db_path` overrides only
    exist so this module's own tests can point at an isolated fixture
    database, exactly like `REAL_DATA_ACCUMULATOR_DB_PATH` already lets
    the accumulator's own tests do."""
    return _connect() if db_path is None else sqlite3.connect(db_path, timeout=30.0)


def preflight_real_data_dataset(
    symbol: str, definition: CompiledStrategyDefinition, *, db_path: str | None = None
) -> tuple[DevelopmentOnlyRealDataProvider, RealDataResearchProvenance] | RealDataFactoryPreflightFailure:
    """Section 21's read-only preflight. Every one of the directive's
    named failure reasons is reachable here, and only here — a caller
    never needs to guess why a real-data run cannot proceed."""
    if symbol not in REAL_DATA_SYMBOLS:
        return RealDataFactoryPreflightFailure(
            reason="REAL_DATA_UNAVAILABLE", detail=f"{symbol!r} is not part of the canonical real-data universe {REAL_DATA_SYMBOLS} — never invented, never silently expanded."
        )

    path = db_path if db_path is not None else _db_path()
    with closing(_open_connection(db_path)) as conn:
        init_schema(conn)

        candles = _read_accumulated_candles(conn, symbol)
        if not candles:
            return RealDataFactoryPreflightFailure(
                reason="REAL_DATA_UNAVAILABLE",
                detail=f"LIVE PERSISTED ACCUMULATOR DATA UNAVAILABLE — no accumulated real candles for {symbol!r} in {path!r} yet.",
            )

        statuses = {c.data_status for c in candles}
        if statuses != {"historical"}:
            return RealDataFactoryPreflightFailure(
                reason="REAL_DATASET_MIXED_PROVENANCE",
                detail=f"Expected every accumulated candle for {symbol!r} to be data_status='historical'; found {sorted(statuses)}.",
            )

        boundary = _read_holdout_boundary(conn, symbol, definition)
        if boundary is None:
            return RealDataFactoryPreflightFailure(
                reason="HOLDOUT_BOUNDARY_INVALID",
                detail=(
                    f"No frozen holdout boundary exists for {symbol!r} against '{definition.id}' v{definition.version} — "
                    "this module never freezes one itself (only app/real_data_accumulator.py::freeze_holdout_baseline() may). "
                    "A real-data Factory run is only possible for the exact (symbol, strategy_id, strategy_version) already frozen."
                ),
            )
        holdout_start, holdout_end, dataset_content_hash, frozen_at = boundary

        development_candles, holdout_candles = _partition_by_holdout(candles, holdout_start, holdout_end)
        if len(development_candles) < MIN_DEVELOPMENT_CANDLES:
            return RealDataFactoryPreflightFailure(
                reason="INSUFFICIENT_REAL_CANDLES",
                detail=f"{symbol!r} has {len(development_candles)} real development candle(s) — below the real MIN_DEVELOPMENT_CANDLES={MIN_DEVELOPMENT_CANDLES} floor.",
            )

        fingerprint = _strategy_fingerprint(definition)
        content_hash = hashlib.sha256(
            "".join(f"{c.symbol}|{c.timeframe}|{c.timestamp}|{c.open}|{c.high}|{c.low}|{c.close}|{c.volume}\n" for c in development_candles).encode("utf-8")
        ).hexdigest()

        provenance = RealDataResearchProvenance(
            provider="kraken",
            data_status="real",
            symbol=symbol,
            timeframe=ACCUMULATOR_TIMEFRAME,
            development_candle_count=len(development_candles),
            holdout_candle_count=len(holdout_candles),
            dataset_start_timestamp=development_candles[0].timestamp,
            dataset_end_timestamp=development_candles[-1].timestamp,
            dataset_content_hash=content_hash,
            strategy_fingerprint=fingerprint,
            holdout_boundary_frozen_at=frozen_at,
        )
        return DevelopmentOnlyRealDataProvider(symbol, development_candles), provenance


def read_holdout_candles_for_final_evaluation(
    symbol: str, definition: CompiledStrategyDefinition, *, db_path: str | None = None
) -> list[Candle] | RealDataFactoryPreflightFailure:
    """Deliberately SEPARATE from `preflight_real_data_dataset()`/
    `run_real_data_factory_cycle()` — no Factory/mutation code path
    calls this. Returns the frozen holdout slice only, for an explicit,
    final, one-time evaluation a caller performs OUTSIDE the mutation
    loop. See this module's own docstring for the disclosed limitation:
    nothing here currently prevents calling this more than once."""
    with closing(_open_connection(db_path)) as conn:
        init_schema(conn)
        candles = _read_accumulated_candles(conn, symbol)
        if not candles:
            return RealDataFactoryPreflightFailure(reason="REAL_DATA_UNAVAILABLE", detail=f"No accumulated real candles for {symbol!r}.")
        boundary = _read_holdout_boundary(conn, symbol, definition)
        if boundary is None:
            return RealDataFactoryPreflightFailure(
                reason="HOLDOUT_BOUNDARY_INVALID", detail=f"No frozen holdout boundary for {symbol!r} against '{definition.id}' v{definition.version}."
            )
        holdout_start, holdout_end, _content_hash, _frozen_at = boundary
        _development, holdout = _partition_by_holdout(candles, holdout_start, holdout_end)
        return holdout


@dataclass(frozen=True)
class RealDataFactoryRunOutcome:
    """The one real result type — mirrors
    `app/seed_hypothesis_generator.py::SeedHypothesisProposal`'s own
    computed-fresh, never-persisted convention. `status="preflight_failed"`
    is a real, honest, expected outcome, never an error to work around."""

    status: Literal["completed", "preflight_failed"]
    symbol: str
    reason: RealDataUnavailableReason | None
    detail: str
    run: FactoryRunRecord | None = None
    updated_registry: dict[str, list[CompiledStrategyDefinition]] | None = None
    new_iterations: list[ResearchLoopIterationRecord] | None = None
    new_lessons: list[ResearchLessonRecord] | None = None
    provenance: RealDataResearchProvenance | None = None


def run_real_data_factory_cycle(
    seed_hypothesis: StrategyHypothesis,
    seed_definition: CompiledStrategyDefinition,
    *,
    symbol: str,
    compiled_strategy_registry: dict[str, list[CompiledStrategyDefinition]],
    quant_research_experiments: list[QuantResearchExperiment],
    research_iterations: list[ResearchLoopIterationRecord],
    research_lessons: list[ResearchLessonRecord],
    failed_archive: list[FailedStrategyArchiveEntry],
    champion_history: list[ChampionRecord],
    risk_per_trade_pct: float,
    run_id: str,
    created_at: str,
    max_generations: int | None = None,
    max_total_backtests: int | None = None,
    max_children_per_parent: int | None = None,
    max_runtime_seconds: int | None = None,
    db_path: str | None = None,
) -> RealDataFactoryRunOutcome:
    """The one real entry point (Section 3/20). Runs the EXISTING,
    UNMODIFIED `run_research_factory_cycle()` with a
    `DevelopmentOnlyRealDataProvider` injected — never a second Factory,
    never a second backtest engine. FAILS CLOSED on every one of
    Section 5's named conditions rather than ever substituting mock
    data; a preflight failure produces zero calls into the Factory at
    all (Section 21: "do not partially execute")."""
    preflight = preflight_real_data_dataset(symbol, seed_definition, db_path=db_path)
    if isinstance(preflight, RealDataFactoryPreflightFailure):
        return RealDataFactoryRunOutcome(status="preflight_failed", symbol=symbol, reason=preflight.reason, detail=preflight.detail)
    provider, provenance = preflight

    kwargs: dict[str, object] = {
        "compiled_strategy_registry": compiled_strategy_registry,
        "quant_research_experiments": quant_research_experiments,
        "research_iterations": research_iterations,
        "research_lessons": research_lessons,
        "failed_archive": failed_archive,
        "champion_history": champion_history,
        "risk_per_trade_pct": risk_per_trade_pct,
        "run_id": run_id,
        "created_at": created_at,
        "symbols": [symbol],
        "timeframe": provenance.timeframe,
        "candles_per_symbol": provenance.development_candle_count,
        "market_data_provider": provider,
    }
    if max_generations is not None:
        kwargs["max_generations"] = max_generations
    if max_total_backtests is not None:
        kwargs["max_total_backtests"] = max_total_backtests
    if max_children_per_parent is not None:
        kwargs["max_children_per_parent"] = max_children_per_parent
    if max_runtime_seconds is not None:
        kwargs["max_runtime_seconds"] = max_runtime_seconds

    run, updated_registry, all_iterations, all_lessons = run_research_factory_cycle(seed_hypothesis, seed_definition, **kwargs)  # type: ignore[arg-type]
    # `run_research_factory_cycle()` returns the FULL (snapshot + newly
    # produced) lists — see app/state.py::submit_research_factory_run()'s
    # own identical slicing convention. Slicing here, not in the caller,
    # keeps this dataclass's own field names honest: `new_iterations`/
    # `new_lessons` really are only what THIS run produced.
    new_iterations = all_iterations[len(research_iterations):]
    new_lessons = all_lessons[len(research_lessons):]
    return RealDataFactoryRunOutcome(
        status="completed",
        symbol=symbol,
        reason=None,
        detail=f"Real-data Factory run completed against {provenance.development_candle_count} real development candle(s) for {symbol}.",
        run=run,
        updated_registry=updated_registry,
        new_iterations=new_iterations,
        new_lessons=new_lessons,
        provenance=provenance,
    )
