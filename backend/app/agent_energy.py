"""Agent Energy (v0.6.2 Phase 6) — player-spendable operational capacity.

Explicitly NOT a proxy for real computational/API cost — this backend has
no metered LLM calls or real market-data API budget to spend against
(see app/market_data.py's mock provider), so pretending "energy" tracks
CPU usage would be dishonest. Instead this is a transparent game-system
abstraction: a company-wide pool that regenerates over time (and, once
the Phase 7 Signal Calibration mini-game exists, from playing it) and
unlocks a small set of real actions when spent. Every action has a
genuine effect on real game state — nothing here is a number that goes
up or down for its own sake.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import AgentEnergy

DEFAULT_CAP = 100.0

# Regenerates once per in-game day (see nexus.py's `is_midnight` — applied
# there, not on a real-time timer, so it advances with the simulation the
# same way every other daily event already does) rather than continuously,
# so there's no incentive to sit and watch a real-time counter tick up —
# "do not make the system require endless grinding" (v0.6.2 brief).
REGEN_PER_DAY = 20.0

# What spending energy actually does, and what it costs. Each key is
# handled explicitly in app/routers/energy.py — deliberately a small,
# closed set rather than a generic "spend N energy for +N% on anything"
# lever, so every action stays auditable and tied to a real effect:
#   research_boost   - immediately advances one real in-progress
#                       ResearchItem's confidence (still capped at 100),
#                       i.e. "deeper market analysis / additional research".
#   extra_simulation  - queues one additional real Simulation Lab backtest
#                       session right now instead of waiting for the
#                       normal random per-tick chance, i.e. "simulations /
#                       strategy comparisons / backtesting".
#   watch_symbol      - adds one new real symbol to the watchlist, i.e.
#                       "monitoring additional assets".
ACTION_COSTS: dict[str, float] = {
    "research_boost": 15.0,
    "extra_simulation": 20.0,
    "watch_symbol": 10.0,
}

RESEARCH_BOOST_AMOUNT = 25.0


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_agent_energy() -> AgentEnergy:
    return AgentEnergy(current=DEFAULT_CAP, cap=DEFAULT_CAP, updatedAt=_now_iso())


def regen_daily(energy: AgentEnergy) -> AgentEnergy:
    current = min(energy.cap, energy.current + REGEN_PER_DAY)
    if current == energy.current:
        return energy
    return energy.model_copy(update={"current": current, "updated_at": _now_iso()})


def can_afford(energy: AgentEnergy, action: str) -> bool:
    cost = ACTION_COSTS.get(action)
    return cost is not None and energy.current >= cost


def spend(energy: AgentEnergy, action: str) -> AgentEnergy | None:
    """Returns None (spend nothing, change nothing) if the action is
    unknown or unaffordable — callers must treat that as a hard failure,
    never silently letting the balance go negative."""
    cost = ACTION_COSTS.get(action)
    if cost is None or energy.current < cost:
        return None
    return energy.model_copy(update={"current": energy.current - cost, "updated_at": _now_iso()})


def award(energy: AgentEnergy, amount: float) -> AgentEnergy:
    """The one non-spend way energy increases outside daily regen — a
    correct Signal Calibration round (app/signal_calibration.py) pays out
    real energy the same way a real trader's disciplined read of a setup
    would be worth something, capped at the same `cap` regen respects."""
    current = min(energy.cap, energy.current + amount)
    if current == energy.current:
        return energy
    return energy.model_copy(update={"current": current, "updated_at": _now_iso()})
