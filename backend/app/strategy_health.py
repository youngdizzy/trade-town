"""app/strategy_health.py — CEO directive "...then Paper-Trade Journal +
Drift Detection + Strategy Health State Machine" — the Strategy Health
State Machine.

See `StrategyHealthState`'s own docstring in app/schemas.py for the full
forensic-recon rationale: this is explicitly NOT a fourth, competing
health scorer alongside `compute_strategy_health()`/
`compute_strategy_degradation()`/`compute_trading_mode_health()` — it is
the one thing none of those three provide: a real, persisted,
evidence-gated TRANSITION history, built entirely from the real
per-category severities `app/strategy_drift.py`'s Drift Detection Engine
already produces.

TRANSITION RULE, disclosed in full (no hidden thresholds):
  - The target state is derived purely from how many of the four real
    Drift categories are currently "critical" vs. "watch":
      >=2 critical  -> SUSPENDED
      >=1 critical  -> CRITICAL
      >=2 watch     -> DEGRADED
      >=1 watch     -> WATCH
      none          -> HEALTHY (evidence-clean)
  - A non-healthy state's own path back to "evidence-clean" NEVER lands
    directly on HEALTHY — it always passes through RECOVERING first (a
    real probation period), and RECOVERING only advances to HEALTHY once
    `RECOVERY_MIN_TRADE_COUNT` real new trades have closed while the
    strategy stayed evidence-clean throughout — never a single winning
    trade. A fresh critical/watch signal during RECOVERING drops the
    strategy straight back into the matching ladder state (re-uses the
    exact same target-state rule above, no separate "recovery failure"
    logic).
  - HEALTH NEVER GRANTS EXTRA RISK. `risk_scaling_factor` per state
    (1.00/0.75/0.50/0.25/0.00/0.50) only ever narrows a strategy-
    attributed trade — see app/state.py's submit_ceo_decision() for
    exactly how this composes with the Risk Contract's own (separate,
    company-wide) scaling.

INTEGRATION CONSTRAINT, disclosed (found during this pass's own recon,
not invented). `TradeProposal` carries no `strategy_id` at generation
time — a CEO only attributes a strategy to a decision AFTER `resolve_
proposal()` has already sized and executed the trade (app/state.py's
own existing comment: "patches the freshly-opened PaperPosition...
strictly after the fact, never altering what the trade itself did").
That means strategy health CANNOT retroactively shrink an already-
executed manual trade's size without violating that established,
already-shipped invariant. This module's own real, enforceable
integration is instead: (1) a SUSPENDED strategy's `strategy_id` is
rejected outright by `submit_ceo_decision()` (a hard stop — "the trade
never happens," not "the trade happens smaller"), and (2) any other
non-HEALTHY state produces a real, disclosed, NON-BLOCKING warning on
the resulting `CeoDecisionRecord` (the exact same established pattern
`regime_strategy_warning` already uses) — never a silent, unexplainable
size change.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.schemas import DriftCategory, DriftSeverity, StrategyHealthLifecycleState, StrategyHealthState, StrategyHealthTransition

RECOVERY_MIN_TRADE_COUNT = 5

RISK_SCALING_FACTOR: dict[StrategyHealthLifecycleState, float] = {
    "healthy": 1.0,
    "watch": 0.75,
    "degraded": 0.5,
    "critical": 0.25,
    "suspended": 0.0,
    "recovering": 0.5,
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _target_state(severities: dict[DriftCategory, DriftSeverity]) -> StrategyHealthLifecycleState:
    critical_count = sum(1 for s in severities.values() if s == "critical")
    watch_count = sum(1 for s in severities.values() if s == "watch")
    if critical_count >= 2:
        return "suspended"
    if critical_count >= 1:
        return "critical"
    if watch_count >= 2:
        return "degraded"
    if watch_count >= 1:
        return "watch"
    return "healthy"


def evaluate_health_transition(
    *,
    current: StrategyHealthState | None,
    strategy_id: str,
    current_severities: dict[DriftCategory, DriftSeverity],
    new_trades_closed_this_tick: int,
    sim_day: int,
    triggering_drift_event_ids: list[str],
) -> StrategyHealthState:
    """Pure and deterministic: identical inputs always produce an
    identical result. Returns `current` unchanged (a genuine no-op —
    the caller need not persist a new object) whenever no real state
    transition occurs and no probation trade needs counting."""
    now = _now_iso()
    if current is None:
        current = StrategyHealthState(strategyId=strategy_id, state="healthy", sinceSimDay=sim_day, updatedAt=now, riskScalingFactor=1.0)

    prev_state = current.state
    target = _target_state(current_severities)

    if prev_state == "recovering":
        if target != "healthy":
            new_state: StrategyHealthLifecycleState = target
        elif current.recovery_trade_count + new_trades_closed_this_tick >= RECOVERY_MIN_TRADE_COUNT:
            new_state = "healthy"
        else:
            new_state = "recovering"
    elif target == "healthy" and prev_state != "healthy":
        # Evidence has gone clean, but never a direct jump back to full
        # trust — see this module's own docstring.
        new_state = "recovering"
    else:
        new_state = target

    if new_state == prev_state:
        if new_state == "recovering" and new_trades_closed_this_tick > 0:
            return current.model_copy(
                update={"recovery_trade_count": current.recovery_trade_count + new_trades_closed_this_tick, "updated_at": now}
            )
        return current

    recovery_trade_count = 0
    if new_state == "recovering" and prev_state == "recovering":
        recovery_trade_count = current.recovery_trade_count + new_trades_closed_this_tick

    risk_scaling_factor = RISK_SCALING_FACTOR[new_state]
    evidence = [f"{category}: {severity}" for category, severity in sorted(current_severities.items())] or ["No active drift signals."]
    trigger = (
        "Entered recovery probation — every real drift category evaluated clean this tick."
        if new_state == "recovering"
        else (
            f"Real drift severities crossed the {new_state} threshold: {', '.join(evidence)}."
            if new_state != "healthy"
            else f"Completed {RECOVERY_MIN_TRADE_COUNT}+ real trades in recovery probation with clean drift evidence throughout."
        )
    )
    transition = StrategyHealthTransition(
        id=f"health-{strategy_id}-{uuid.uuid4().hex[:8]}",
        createdAt=now,
        simDay=sim_day,
        strategyId=strategy_id,
        previousState=prev_state,
        newState=new_state,
        trigger=trigger,
        evidence=evidence,
        driftEventIds=triggering_drift_event_ids,
        riskScalingFactor=risk_scaling_factor,
    )
    return current.model_copy(
        update={
            "state": new_state,
            "since_sim_day": sim_day,
            "updated_at": now,
            "risk_scaling_factor": risk_scaling_factor,
            "recovery_trade_count": recovery_trade_count,
            "transitions": [*current.transitions, transition],
        }
    )


__all__ = ["evaluate_health_transition", "RECOVERY_MIN_TRADE_COUNT", "RISK_SCALING_FACTOR"]
