"""app/sniper_strategy_performance.py — CEO directive "TradeTown —
Sniper Per-Strategy Performance Observability 1.0."

FORENSIC FINDING THIS MODULE ACTS ON. `GameSaveState.sniper_trade_
history` (`list[SniperTrade]`) is already the one authoritative,
persisted closed-trade journal for Memecoin Sniper — every entry is
created exclusively by `app/memecoin_sniper.py::close_position()` at
the moment a position closes, and already carries its own real,
immutable, at-creation-time `strategy_id`/`strategy_name`/
`strategy_version_id`/`strategy_version_status` (copied forward from
the `SniperPosition` being closed — see that function's own docstring).
There is no ambiguity to resolve and no join to perform: unlike the
equities side's `compute_strategy_performance()`
(`app/performance_attribution.py`), which has to join `PaperTrade`
against `DecisionVaultEntry` because equities strategy attribution can
be genuinely missing (a CEO who never selected a strategy at decision
time), a `SniperTrade` always has SOME real `strategy_id` — the field
has a real default (`SNIPER_STRATEGY_ID`) precisely because Sniper had
exactly one strategy before its own registry existed, and a trade
closed back then genuinely was produced by that one implementation.
This module is therefore pure aggregation over an already-complete
join, not a second attribution system.

WHY A SEPARATE MODULE FROM app/performance_attribution.py (DUPLICATION
AUDIT). That module's entire type surface — `PaperTrade`,
`DecisionVaultEntry`, `Strategy`, `TradingSession`,
`MarketIntelligenceRegime` — is equities-only; Sniper's `SniperTrade`/
`SniperStrategyDefinition` share no base type or field shape with any
of them (different units — SOL, not USD; no `pnl_pct` field at all; no
decision-vault concept). Forcing this aggregation through that module
would mean fabricating equities-shaped inputs for a domain that has
none. `app/sniper_strategy_registry.py` was deliberately kept
METADATA + GOVERNANCE only (its own docstring's explicit scope) —
performance observability is a third, distinct concern and does not
belong there either.

METRIC CONVENTIONS, established once here and reused for every
strategy: WIN = `pnl_sol > 0`; LOSS = `pnl_sol <= 0` (break-even counts
as a loss) — the exact same boundary `app/portfolio.py::
close_position()`/`app/performance_attribution.py` already use
codebase-wide, reused for consistency rather than inventing a third
convention for a third domain. Unlike that equities module, this one
does NOT withhold `observed_expectancy_per_closed_trade_sol`/
`average_realized_pnl_sol` below a minimum sample size — this
directive's own explicit instruction is to expose `closed_trade_count`
prominently so a caller can judge sample-size reliability itself,
never to gate the metric behind an invented evidence threshold. Zero
closed trades produces `None` (never a fabricated `0%`/`$0`) for every
rate/average field — `total_realized_pnl_sol` alone is a genuine `0.0`
at zero trades (the sum of an empty set), never `None`.

SCOPE. Pure, read-only, deterministic aggregation: no persistence, no
mutation of any `SniperTrade`/`SniperStrategyDefinition`, no
randomness, no network calls, no LLM calls. This module never touches
`SniperRiskState`, never calls `evaluate_entry_firewall()`, never
changes a strategy's `status`, and its output is never read by
`tick_sniper_engine()`, `strategy_accepts_candidate()`, or any AI
reasoning module — see this directive's own "performance observability
must never become an alternate control path" rule. It answers "what
happened," never "what TradeTown should do about it."
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

from app.schemas import (
    SniperStrategyDefinition,
    SniperStrategyPerformanceRead,
    SniperStrategyPerformanceSummary,
    SniperStrategyProvenance,
    SniperStrategyStatus,
    SniperTrade,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mean(values: list[float]) -> float:
    return round(sum(values) / len(values), 6)


def _build_read(strategy_id: str, trades: list[SniperTrade], registered: SniperStrategyDefinition | None) -> SniperStrategyPerformanceRead:
    """One strategy's row. `trades` is already this id's own real,
    filtered, de-duplicated closed-trade slice — this function never
    looks at any other strategy's trades and never reads current
    market/risk state."""
    name: str
    family: str | None
    provenance: SniperStrategyProvenance | None
    status: SniperStrategyStatus | None
    if registered is not None:
        name, family, provenance, status = registered.name, registered.family, registered.provenance, registered.status
    else:
        # A real, if defensive, case: no delete/de-registration
        # mechanism exists on this registry today, so this branch is
        # currently unreachable in production — but the report must
        # not silently erase a historical strategy's performance if
        # one is ever removed from the registry in the future. Reads
        # the name straight off the trades' own real, already-persisted
        # `strategy_name` (the chronologically most recent trade —
        # `trade_history` is append-in-order, never reordered) rather
        # than fabricating an "Unknown Strategy" placeholder when real
        # data already answers the question.
        name = trades[-1].strategy_name if trades else strategy_id
        family = None
        provenance = None
        status = None

    # Section 9's own explicit rule — never collapse different
    # historical versions of the same strategy id into "whatever the
    # registry says today." Every distinct version this id's own real
    # trades were actually produced under, made visible, sorted for a
    # stable order.
    versions = sorted({t.strategy_version_id for t in trades if t.strategy_version_id is not None})

    winners = [t for t in trades if t.pnl_sol > 0]
    losers = [t for t in trades if t.pnl_sol <= 0]
    trade_count = len(trades)
    win_count = len(winners)
    loss_count = len(losers)

    win_rate_pct = round(win_count / trade_count * 100.0, 1) if trade_count else None
    total_pnl = round(sum(t.pnl_sol for t in trades), 6)
    average_pnl = round(total_pnl / trade_count, 6) if trade_count else None
    average_winner = _mean([t.pnl_sol for t in winners]) if winners else None
    average_loser = _mean([t.pnl_sol for t in losers]) if losers else None

    expectancy: float | None = None
    if trade_count:
        win_share = win_count / trade_count
        loss_share = loss_count / trade_count
        expectancy = round(win_share * (average_winner or 0.0) + loss_share * (average_loser or 0.0), 6)

    return SniperStrategyPerformanceRead(
        strategyId=strategy_id,
        name=name,
        family=family,
        provenance=provenance,
        isRegistered=registered is not None,
        status=status,
        distinctStrategyVersionsObserved=versions,
        closedTradeCount=trade_count,
        winCount=win_count,
        lossCount=loss_count,
        winRatePct=win_rate_pct,
        totalRealizedPnlSol=total_pnl,
        averageRealizedPnlSol=average_pnl,
        averageWinningTradeSol=average_winner,
        averageLosingTradeSol=average_loser,
        observedExpectancyPerClosedTradeSol=expectancy,
    )


def compute_sniper_strategy_performance(
    trade_history: list[SniperTrade],
    strategies: list[SniperStrategyDefinition],
) -> SniperStrategyPerformanceSummary:
    """The one real, canonical aggregation entry point. `trade_history`
    is the caller's real, persisted `GameSaveState.sniper_trade_history`
    (already bounded to the most recent `MAX_TRADE_HISTORY` closed
    trades by `tick_sniper_engine()` — see `SniperStrategyPerformance
    Summary.closed_trades_considered`'s own docstring for why this
    report is honestly a window, not a guaranteed lifetime total).
    `strategies` is the caller's real, persisted registry — every
    registered id gets a row even with zero trades (Section 7's own
    "zero evidence, not measured zero" rule), and every id actually
    OBSERVED in `trade_history` gets a row even if it is no longer
    registered (Section 22).

    Deterministic and side-effect-free: the same two inputs always
    produce the same `reads` (only `generated_at` varies, and it is
    never used as a computation input)."""
    seen_ids: set[str] = set()
    deduped: list[SniperTrade] = []
    for trade in trade_history:
        if trade.id in seen_ids:
            continue
        seen_ids.add(trade.id)
        deduped.append(trade)

    valid_trades: list[SniperTrade] = []
    excluded_malformed = 0
    for trade in deduped:
        if not math.isfinite(trade.pnl_sol):
            excluded_malformed += 1
            continue
        valid_trades.append(trade)

    by_strategy_id: dict[str, list[SniperTrade]] = {}
    for trade in valid_trades:
        by_strategy_id.setdefault(trade.strategy_id, []).append(trade)

    registry_by_id = {s.id: s for s in strategies}
    all_ids = sorted(set(registry_by_id) | set(by_strategy_id))

    reads = [_build_read(strategy_id, by_strategy_id.get(strategy_id, []), registry_by_id.get(strategy_id)) for strategy_id in all_ids]

    return SniperStrategyPerformanceSummary(
        reads=reads,
        tradesExcludedMalformed=excluded_malformed,
        closedTradesConsidered=len(valid_trades),
        generatedAt=_now_iso(),
    )
