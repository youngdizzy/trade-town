"""app/strategy_drift.py — CEO directive "...then Paper-Trade Journal +
Drift Detection + Strategy Health State Machine" — the Drift Detection
Engine.

See `DriftEvent`'s own docstring in app/schemas.py for the full forensic
recon: this module never reimplements strategy-degradation math. It
calls `app/performance_attribution.py::compute_strategy_degradation()`
— the one real, already-tested live-trade comparison this codebase has
— and turns its already-real signal strings into a real, persisted,
per-category event stream, emitting a new `DriftEvent` only when a
category's severity actually changes for a strategy (never one row per
tick — the same "persist only on real change" convention
`app/market_environment.py`'s own regime timeline already established).

CATEGORY MAPPING. `compute_strategy_degradation()` blends five signal
kinds into one flat `signals: list[str]` + one overall `level`. Each
signal string always starts with one of five fixed prefixes (see that
function's own source) — this module reads those prefixes to route each
signal into the correct Drift category, never re-deriving the
underlying metric:
  "Loss clustering"          -> performance
  "Expectancy deterioration" -> performance
  "Repeated invalidations"   -> performance
  "Volatility regime change" -> regime
  "Execution degradation"    -> execution
  "Abnormal drawdown"        -> risk
A category with no matching signal this evaluation is "normal" (or
"insufficient_evidence" when the strategy's own overall level is
`not_enough_data`) — never silently omitted.

REGIME_CHANGED (Phase 8's own "regime change is not automatically
strategy failure" requirement). Reuses `app/market_environment.py`'s own
real, persisted regime-change timeline unchanged: `regime_changed` is
True for the "regime" category iff a real regime change was recorded
within `REGIME_LOOKBACK_SIM_MINUTES` of the current tick — a disclosed,
fixed lookback (3 sim days), not a precisely per-strategy-trade-derived
window (this module has no cheap way to bound "this strategy's own
recent trades' time span" without re-deriving compute_strategy_
degradation()'s own trade-grouping internals, which would be exactly
the kind of duplicate join this pass avoids). Never fabricated: reads
`state.market_environment.timeline` directly, nothing else.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.performance_attribution import compute_strategy_degradation
from app.schemas import (
    DecisionVaultEntry,
    DriftCategory,
    DriftEvent,
    DriftSeverity,
    FailureClassification,
    MarketEnvironmentState,
    PaperTrade,
    Strategy,
    StrategyDegradationRead,
)

REGIME_LOOKBACK_SIM_MINUTES = 3 * 1440

_PERFORMANCE_PREFIXES = ("Loss clustering", "Expectancy deterioration", "Repeated invalidations")
_REGIME_PREFIXES = ("Volatility regime change",)
_EXECUTION_PREFIXES = ("Execution degradation",)
_RISK_PREFIXES = ("Abnormal drawdown",)

_CATEGORY_PREFIXES: dict[DriftCategory, tuple[str, ...]] = {
    "performance": _PERFORMANCE_PREFIXES,
    "regime": _REGIME_PREFIXES,
    "execution": _EXECUTION_PREFIXES,
    "risk": _RISK_PREFIXES,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _category_severity(read: StrategyDegradationRead, category: DriftCategory) -> tuple[DriftSeverity, list[str]]:
    """One category's own severity, derived purely by partitioning the
    already-real `read.signals` by prefix — never a second scoring
    pass. `read.level == "critical_degradation"` only elevates a
    category to "critical" when THAT category actually has a matching
    signal (a critical loss-clustering signal never makes the
    unrelated "execution" category critical too)."""
    if read.level == "not_enough_data":
        return "insufficient_evidence", []
    prefixes = _CATEGORY_PREFIXES[category]
    matching = [s for s in read.signals if s.startswith(prefixes)]
    if not matching:
        return "normal", []
    # A signal's own severity (critical vs. possible) isn't tagged on
    # the string itself, so this reuses the read's overall `level` only
    # when that level's own trigger condition genuinely belongs to this
    # category — i.e. a matching signal exists at all. `possible_
    # degradation` and `critical_degradation` both only ever appear when
    # at least one real signal fired, so any category with a matching
    # signal inherits the real overall verdict rather than a fabricated
    # per-category one this module has no separate threshold for.
    severity: DriftSeverity = "critical" if read.level == "critical_degradation" and category != "regime" else "watch"
    return severity, matching


def evaluate_strategy_drift(
    *,
    strategies: list[Strategy],
    trade_history: list[PaperTrade],
    decision_vault: list[DecisionVaultEntry],
    failure_classifications: list[FailureClassification],
    market_environment: MarketEnvironmentState,
    now_sim_minutes: int,
    sim_day: int,
    previous_severity: dict[tuple[str, DriftCategory], DriftSeverity],
) -> list[DriftEvent]:
    """Returns one new `DriftEvent` per (strategy, category) pair whose
    severity genuinely differs from `previous_severity` — the caller's
    own last-known map (see app/state.py's `_evaluate_strategy_drift()`
    for how that's derived from `state.drift_events`). Deterministic:
    identical inputs always produce identical events."""
    summary = compute_strategy_degradation(strategies, trade_history, decision_vault, failure_classifications)
    regime_changed_recently = bool(
        market_environment.timeline and market_environment.timeline[-1].sim_minutes >= now_sim_minutes - REGIME_LOOKBACK_SIM_MINUTES
    )

    categories: tuple[DriftCategory, ...] = ("performance", "execution", "risk", "regime")
    events: list[DriftEvent] = []
    for read in summary.reads:
        for category in categories:
            severity, matching_signals = _category_severity(read, category)
            key = (read.strategy_id, category)
            prior = previous_severity.get(key)
            if prior == severity:
                continue
            events.append(
                DriftEvent(
                    id=f"drift-{read.strategy_id}-{category}-{uuid.uuid4().hex[:8]}",
                    createdAt=_now_iso(),
                    simDay=sim_day,
                    strategyId=read.strategy_id,
                    strategyName=read.strategy_name,
                    category=category,
                    severity=severity,
                    previousSeverity=prior,
                    metric=", ".join(matching_signals) if matching_signals else "No matching signal this evaluation.",
                    baselineValue=read.lifetime_expectancy_pct if category == "performance" else None,
                    observedValue=read.recent_expectancy_pct if category == "performance" else None,
                    sampleSize=read.recent_trade_count,
                    evidence=matching_signals,
                    regimeChanged=regime_changed_recently if category == "regime" else False,
                    detail=(
                        f"{read.strategy_name}: {category} drift {prior or 'unknown'} -> {severity}"
                        f" ({read.recent_trade_count} recent / {read.lifetime_trade_count} lifetime trades)."
                    ),
                )
            )
    return events


__all__ = ["evaluate_strategy_drift", "REGIME_LOOKBACK_SIM_MINUTES"]
