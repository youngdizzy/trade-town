"""Design Bible Chapter 67 (TTOS) Part 3 — the real Global Emergency
Stop. Research before this was built (see docs/DesignBible/volumes/
09-departments/chapter-67-tradetown-operating-system.md's Implementation
Notes) confirmed nothing like this existed anywhere in this codebase:
Chapter 66's `pause_trading` is a real, but automatic-only, signal —
never CEO-triggerable. This module is the CEO-triggerable counterpart.

Scope, deliberately smaller than the brief's own "Cancel pending orders"
line: activating Emergency Stop blocks new trade proposal generation
(app/nexus.py's `tick()`), blocks every pending proposal from
auto-resolving in Assisted/Executive mode (app/nexus.py's
`_apply_operating_mode()`, the exact same "hard block regardless of
mode" pattern Chapter 66's `pause_trading` check already established),
and blocks the CEO's own manual buy/sell decision
(app/state.py's `submit_ceo_decision()` — a "wait"/hold decision is
still allowed, since declining a trade is never itself a safety risk).
Already-pending proposals are left pending, not auto-cancelled — the
same choice `pause_trading` already made, and safer than force-resolving
them to a decision the CEO didn't actually make. Already-placed broker
orders are not force-closed: `tick_broker()` keeps settling whatever was
already in flight before the stop, since yanking a resting fill
mid-flight risks leaving the paper portfolio in a state nothing in this
codebase was built to reconcile. Research, monitoring, dashboards, and
notifications are untouched — nothing here reads or writes `work_mode`.
"""
from __future__ import annotations

from app.schemas import EmergencyStopState


def activate_emergency_stop(state: EmergencyStopState, *, now_iso: str) -> tuple[EmergencyStopState, str | None]:
    if state.active:
        return state, "Emergency Stop is already active."
    return EmergencyStopState(active=True, activatedAt=now_iso), None


def resume_trading(state: EmergencyStopState) -> tuple[EmergencyStopState, str | None]:
    if not state.active:
        return state, "Emergency Stop is not active."
    return EmergencyStopState(active=False, activatedAt=None), None
