"""ResearchManager — the rotating research queue.

Every research-capable agent (everyone except Scribe, who records rather
than researches — see app/scribe.py) always has exactly one ResearchItem
"in_progress" at a time. When it completes, that agent immediately rotates
onto a new symbol. This keeps the queue's size bounded — one active item
per agent plus a capped per-agent history — instead of growing without
limit as research happens tick after tick.

Confidence is a plain 0-100 gauge that climbs a random amount each tick
while an item is active; it is not derived from any real analysis (there
is no real market connection in v0.3 — see app/market_data.py).
"""
from __future__ import annotations

import random
from datetime import datetime, timezone

from app.agents import AGENT_PROFILES
from app.schemas import AgentId, ResearchCategory, ResearchItem, WatchlistEntry
from app.watchlist import SEED_SYMBOLS, SYMBOL_CATEGORY

MAX_RESEARCH_HISTORY_PER_AGENT = 24

# Scribe records the company's work rather than producing its own research.
RESEARCHER_IDS: tuple[AgentId, ...] = ("scout", "atlas", "echo", "nova")

CONFIDENCE_COMPLETE = 100.0
CONFIDENCE_GAIN_RANGE = (2.0, 6.0)

_RESEARCH_TITLE_BY_AGENT: dict[AgentId, str] = {
    "scout": "Scanning news flow on {name}",
    "atlas": "Weighing strategic exposure to {name}",
    "echo": "Charting {name} technicals",
    "nova": "Reviewing {name} fundamentals",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _rotation_pool(watchlist: list[WatchlistEntry] | None) -> list[tuple[str, str, ResearchCategory]]:
    """The symbols research.py's rotation may pick from this tick.
    Professional Quant Trading Core Phase A/C: this now reflects the
    CEO's actual current watchlist (SEED_SYMBOLS plus anything added via
    the "watch_symbol" Agent Energy spend — app/watchlist.py's
    EXTRA_SYMBOL_POOL), not just the fixed SEED_SYMBOLS constant — an
    added symbol used to get real live price tracking (tick_watchlist())
    but could never be assigned a researcher, so it could never produce
    a ResearchItem or, downstream, a TradeProposal. `watchlist=None`
    (every existing caller/test that doesn't pass one) keeps the
    original SEED_SYMBOLS-only behavior exactly as before."""
    if watchlist is None:
        return SEED_SYMBOLS  # type: ignore[return-value]
    pool = [(entry.symbol, entry.name, SYMBOL_CATEGORY[entry.symbol]) for entry in watchlist if entry.symbol in SYMBOL_CATEGORY]
    return pool or SEED_SYMBOLS  # type: ignore[return-value]


def _next_symbol(in_use: set[str], watchlist: list[WatchlistEntry] | None = None) -> tuple[str, str, ResearchCategory]:
    """Prefers a symbol nobody else is currently researching, so the team
    naturally spreads across the watchlist instead of piling onto one
    name — falls back to the full pool once everything is taken."""
    pool = _rotation_pool(watchlist)
    free = [s for s in pool if s[0] not in in_use]
    symbol, name, category = random.choice(free or pool)
    return symbol, name, category  # type: ignore[return-value]


def _new_item(agent_id: AgentId, symbol: str, name: str, category: ResearchCategory) -> ResearchItem:
    now = _now_iso()
    return ResearchItem(
        id=f"research-{agent_id}-{symbol}-{now}",
        title=_RESEARCH_TITLE_BY_AGENT[agent_id].format(name=name),
        symbol=symbol,
        category=category,
        priority="normal",
        status="in_progress",
        assignedAgent=agent_id,
        summary=f"{AGENT_PROFILES[agent_id].name} is getting started on {name}.",
        confidence=round(random.uniform(5, 15), 1),
        createdAt=now,
        updatedAt=now,
    )


def default_research(watchlist: list[WatchlistEntry] | None = None) -> list[ResearchItem]:
    """Gives every research-capable agent an initial in-progress topic so
    the Brain Room's Research Queue is never empty on a fresh game."""
    in_use: set[str] = set()
    items: list[ResearchItem] = []
    for agent_id in RESEARCHER_IDS:
        symbol, name, category = _next_symbol(in_use, watchlist)
        in_use.add(symbol)
        items.append(_new_item(agent_id, symbol, name, category))
    return items


def tick_research(
    research: list[ResearchItem], *, speed_multiplier: float = 1.0, watchlist: list[WatchlistEntry] | None = None
) -> tuple[list[ResearchItem], list[ResearchItem]]:
    """Advances each researcher's active item and rotates a finished one
    out for a new topic. Returns `(full_list, just_completed)` — the
    caller (nexus.py, via scribe.py) turns completions into news/memory
    records; this module only owns the queue's own state transitions.
    `speed_multiplier` is v0.7 Feature 34's "research" Company Priority
    (see nexus.py) scaling the real per-tick confidence gain — 1.0 (the
    default) leaves every other caller, including every existing test,
    unaffected."""
    by_agent: dict[AgentId, list[ResearchItem]] = {}
    for item in research:
        by_agent.setdefault(item.assigned_agent, []).append(item)

    in_use = {item.symbol for item in research if item.status == "in_progress" and item.symbol}
    updated: list[ResearchItem] = []
    history: list[ResearchItem] = []
    completed: list[ResearchItem] = []

    for agent_id in RESEARCHER_IDS:
        agent_items = by_agent.get(agent_id, [])
        current = next((item for item in agent_items if item.status == "in_progress"), None)
        agent_history = [item for item in agent_items if item.status != "in_progress"]

        if current is None:
            symbol, name, category = _next_symbol(in_use, watchlist)
            in_use.add(symbol)
            current = _new_item(agent_id, symbol, name, category)
        else:
            confidence = min(CONFIDENCE_COMPLETE, current.confidence + random.uniform(*CONFIDENCE_GAIN_RANGE) * speed_multiplier)
            current = current.model_copy(update={"confidence": round(confidence, 1), "updated_at": _now_iso()})

            if current.confidence >= CONFIDENCE_COMPLETE:
                current = current.model_copy(
                    update={"status": "completed", "summary": f"{AGENT_PROFILES[agent_id].name} wrapped up research on {current.symbol}."}
                )
                completed.append(current)
                agent_history = ([current] + agent_history)[:MAX_RESEARCH_HISTORY_PER_AGENT]
                in_use.discard(current.symbol or "")
                symbol, name, category = _next_symbol(in_use, watchlist)
                in_use.add(symbol)
                current = _new_item(agent_id, symbol, name, category)

        updated.append(current)
        history.extend(agent_history)

    return updated + history, completed
