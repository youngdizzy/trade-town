"""CEO directive "Features 26-30," Feature 26 — read-only endpoints over
Institutional Memory 2.0, mirroring routers/decision_vault.py's own
convention: `await game_state.snapshot()`, computed fresh every call,
nothing here mutates the save. The full list is already broadcast on
every WS tick (see app/ws_manager.py's `institutionalMemory` field) —
this router adds the one genuinely new query operation the broadcast
can't offer: "what's the single most relevant thing we know" for a given
source/regime, honestly returning null when there isn't enough evidence.
"""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.institutional_memory import retrieve_relevant_memory
from app.schemas import InstitutionalMemoryEntry, InstitutionalMemorySource, KnowledgeEvent, MarketEnvironmentRegime
from app.state import game_state

router = APIRouter(prefix="/api/institutional-memory", tags=["institutional-memory"])


@router.get("/retrieve", response_model=InstitutionalMemoryEntry | None)
async def retrieve(
    source: InstitutionalMemorySource | None = Query(default=None),
    market_regime: MarketEnvironmentRegime | None = Query(default=None, alias="marketRegime"),
    symbol: str | None = Query(default=None),
) -> InstitutionalMemoryEntry | None:
    """The single most relevant+corroborated active memory matching the
    query, or null — NOT ENOUGH EVIDENCE — when nothing qualifies. See
    retrieve_relevant_memory()'s own docstring for exactly how relevance
    and confidence are recomputed fresh for this call, never trusting a
    persisted, potentially stale value. `symbol` (CEO directive
    "TradeTown — Knowledge Application Loop 1.0") filters to memories
    whose own real source record actually carried that symbol — the same
    canonical retrieval app/devils_advocate.py now uses internally."""
    state = await game_state.snapshot()
    return retrieve_relevant_memory(
        state.institutional_memory, current_sim_day=state.time.day, source=source, market_regime=market_regime, symbol=symbol
    )


@router.get("/applications", response_model=list[KnowledgeEvent])
async def applications(lesson_id: str | None = Query(default=None, alias="lessonId")) -> list[KnowledgeEvent]:
    """CEO directive "TradeTown — Knowledge Application Loop 1.0" — every
    real `knowledge_applied` KnowledgeEvent, each carrying its own real
    `applicationStatus`/`outcome`/`outcomeRef` (see
    app/knowledge_sharing.py's grade_knowledge_applications()) — the read
    surface Part XX's future AI context builder, and today's UI, both
    need to answer "was this knowledge actually used, and did it help,"
    without re-deriving anything client-side. Read-only, computed fresh
    from the same real, already-persisted `knowledge_events` list the WS
    broadcast already carries in full; this endpoint exists only for the
    filtered, addressable query the broadcast can't offer."""
    state = await game_state.snapshot()
    events = [e for e in state.knowledge_events if e.type == "knowledge_applied"]
    if lesson_id is not None:
        events = [e for e in events if e.lesson_id == lesson_id]
    return events
