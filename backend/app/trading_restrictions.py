"""CEO directive "Portfolio Risk Engine + Firm-Wide Risk Governance,"
follow-up — Layered Kill Switches.

That directive's own "Not built this pass" list named three granularity
layers below the existing firm-wide Emergency Stop (app/emergency_stop.py):
position/symbol, strategy, and agent/asset-class. A repo audit before
writing anything here found two of those three already real:

  - STRATEGY: `app/sandbox.py`'s `retire_strategy()` already moves a
    Strategy Lab strategy to the real, terminal "retired" `StrategyStage`
    (STRATEGY_STAGE's own last entry) — a real, CEO-triggered, permanent
    per-strategy kill switch. Building a second one here would duplicate
    it under a different name.
  - AGENT: a per-agent "mute" was considered and explicitly NOT built.
    `AnalystVote` always carries all six analyst roles' real votes — the
    Discipline Chamber (app/discipline.py) and the AI Debate Room
    (app/debate.py) both structurally depend on that invariant, so
    removing or blanking one agent's vote would either fabricate a
    placeholder vote or break those two real features. The one
    already-real per-agent lever this codebase has is
    `app/weighted_decisions.py`'s accuracy-based department weighting —
    a chronically-wrong department's real influence on the Weighted
    Executive Recommendation already shrinks on its own, continuously,
    from real accuracy evidence. A blunt on/off mute would either
    duplicate that existing, more honest mechanism or bypass it. Left
    genuinely unbuilt; documented, not fabricated.

That leaves SYMBOL and CATEGORY (asset-class, using this codebase's real
`ResearchCategory` taxonomy — stock/etf/index/economy/gold/bitcoin/
company/sector — the only asset-class-like grouping that actually exists
anywhere in this codebase) as the one genuinely missing, cleanly
enforceable layer. This module is that layer: a `TradingRestriction`
halts new position-opening (buy AND sell — a real full halt on its
target, matching `EmergencyStopState`'s own "no partial halt" choice) for
one symbol or one whole category, without touching the rest of the firm.

TWO REAL ENFORCEMENT POINTS (the same two-point pattern
app/emergency_stop.py's own module docstring already established):

  1. New proposal generation (app/nexus.py's `_generate_trade_proposals`)
     skips any research item whose symbol/category is currently
     restricted — the CEO never even sees a proposal for it.
  2. The Trade Gatekeeper (app/gatekeeper.py's `evaluate_gatekeeper`)
     carries a new `_trading_restriction_check` in its existing pure-AND
     checklist — defense in depth for a proposal that was already
     pending the instant a restriction activates.

Never a third, parallel risk-checking implementation: this module only
decides WHETHER a target is currently restricted; the real veto still
happens inside the one real enforcement path each call site already had.
Already-open positions are never force-closed, matching
`emergency_stop.py`'s identical choice for the same reason: yanking a
resting position mid-flight risks leaving the paper portfolio in a state
nothing in this codebase was built to reconcile.
"""
from __future__ import annotations

from app.schemas import RestrictionScope, ResearchCategory, TradingRestriction

# Disclosed, arbitrary cap — same convention as every other unbounded
# permanent event list in this codebase (MAX_MEMORY_RECORDS,
# MAX_RECOVERY_BRIEFINGS, ...). Restrictions are rare, deliberate CEO
# actions, so this ceiling is generous, not a real operational limit.
MAX_TRADING_RESTRICTIONS = 200


def active_restrictions(restrictions: list[TradingRestriction]) -> list[TradingRestriction]:
    return [r for r in restrictions if r.active]


def find_blocking_restriction(
    restrictions: list[TradingRestriction], *, symbol: str, category: ResearchCategory
) -> TradingRestriction | None:
    """The one real question both enforcement points ask: is this
    symbol, or its whole category, currently restricted? Symbol-scope
    restrictions are checked first purely so a symbol-specific reason
    surfaces over a broader category one when both happen to be active."""
    for restriction in active_restrictions(restrictions):
        if restriction.scope == "symbol" and restriction.target == symbol:
            return restriction
    for restriction in active_restrictions(restrictions):
        if restriction.scope == "category" and restriction.target == category:
            return restriction
    return None


def activate_trading_restriction(
    restrictions: list[TradingRestriction],
    *,
    scope: RestrictionScope,
    target: str,
    reason: str,
    now_iso: str,
) -> tuple[list[TradingRestriction], TradingRestriction | None, str | None]:
    """Returns (new_restrictions, the new restriction, error). Refuses a
    duplicate — an already-active restriction on the exact same
    (scope, target) — rather than silently stacking two rows that mean
    the same thing."""
    if not reason.strip():
        return restrictions, None, "A reason is required to activate a trading restriction."
    if any(r.active and r.scope == scope and r.target == target for r in restrictions):
        return restrictions, None, f"{target} already has an active {scope} restriction."
    restriction = TradingRestriction(
        id=f"restriction-{scope}-{target}-{now_iso}",
        scope=scope,
        target=target,
        reason=reason.strip(),
        active=True,
        activatedAt=now_iso,
    )
    updated = [*restrictions, restriction]
    if len(updated) > MAX_TRADING_RESTRICTIONS:
        updated = updated[-MAX_TRADING_RESTRICTIONS:]
    return updated, restriction, None


def lift_trading_restriction(
    restrictions: list[TradingRestriction], restriction_id: str, *, reason: str, now_iso: str
) -> tuple[list[TradingRestriction], TradingRestriction | None, str | None]:
    """Returns (new_restrictions, the lifted restriction, error)."""
    target_restriction = next((r for r in restrictions if r.id == restriction_id), None)
    if target_restriction is None:
        return restrictions, None, "No trading restriction with that id exists."
    if not target_restriction.active:
        return restrictions, None, "That trading restriction is already lifted."
    lifted = target_restriction.model_copy(
        update={"active": False, "lifted_at": now_iso, "lifted_reason": reason.strip() or "Lifted by the CEO."}
    )
    updated = [lifted if r.id == restriction_id else r for r in restrictions]
    return updated, lifted, None
