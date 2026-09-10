"""TradeTown Read-Only MCP Boundary 1.0 — the controlled internal read
surface for the external `tt-scout` agent.

WHAT THIS IS. Three read-only endpoints that serve ONLY records TradeTown
has explicitly approved for external-agent consumption. They exist so the
MCP service never receives unapproved data at all, rather than receiving
everything and filtering client-side: filtering is done by the authority
that owns the data. Same convention as routers/institutional_memory.py and
routers/decision_vault.py — `await game_state.snapshot()`, computed fresh
every call, nothing here mutates the save.

WHAT THIS IS NOT. Not a general query API, not a second read model, and not
reachable from the public internet. In the deployed topology the MCP service
talks to an internal nginx listener that forwards ONLY an exact allowlist of
GET paths (see frontend/deploy/nginx.conf's `server` block on port 8081);
it can never reach backend:8000 directly, and no non-GET method is forwarded
at all. See docs/SCOUT_READONLY_TOOL_CONTRACT_V0.md.

FAIL-CLOSED BY CONSTRUCTION. Every endpoint filters on
`approved_for_agent_read is True`. A save that predates the approval fields
deep-merges them to `False` (app/persistence.py::_deep_merge_defaults), so
the honest behavior on an un-seeded deployment is an EMPTY result set —
never "everything, because nothing is marked unapproved."

CUTOFF ENFORCEMENT IS NOT UNIFORM, AND SAYS SO. Every response carries a
real `cutoffEnforcement` string naming exactly which anchor was used:

  - InstitutionalMemoryEntry carries a real simulated-clock anchor of its
    own (`sim_day`), so both it AND the approval sim-minute are enforced.
    Day granularity is the finest this record honestly has.
  - ResearchItem carries NO simulated-clock field (only real wall-clock
    createdAt/updatedAt — verified at HEAD 39bfe9e), so the only honest
    anchor available is the sim-minute at which it was approved. That is a
    weaker guarantee than creation-time containment and is disclosed as
    exactly that, never silently presented as the same thing.

Adding a creation-time sim anchor to ResearchItem would mean changing how
research records are created (app/research.py), which is out of scope for
this milestone.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

from app import persistence
from app.portfolio import sim_minutes
from app.schemas import (
    AgentFindingsResponse,
    ApprovedMemoryRead,
    ApprovedMemoryResponse,
    ApprovedResearchRead,
    ApprovedResearchResponse,
    InstitutionalMemorySource,
    MarketEnvironmentRegime,
    ResearchCategory,
)
from app.state import game_state

router = APIRouter(prefix="/api/mcp-read", tags=["mcp-read"])

# Result caps. These match docs/SCOUT_READONLY_TOOL_CONTRACT_V0.md §15 so the
# boundary's own limits and TradeTown's own limits can never drift apart.
RESEARCH_MAX_LIMIT = 50
RESEARCH_DEFAULT_LIMIT = 20
MEMORY_MAX_LIMIT = 50
MEMORY_DEFAULT_LIMIT = 20
FINDINGS_MAX_LIMIT = 25
FINDINGS_DEFAULT_LIMIT = 10

MINUTES_PER_SIM_DAY = 1440

RESEARCH_CUTOFF_ENFORCEMENT = (
    "approval_sim_minutes_only: ResearchItem carries no creation-time "
    "simulated-clock field, so containment is proven against the sim-minute "
    "at which the record was approved for agent read, not its creation time"
)
MEMORY_CUTOFF_ENFORCEMENT = (
    "sim_day_and_approval_sim_minutes: both the record's own simulated-clock "
    "day anchor and its approval sim-minute must fall at or before the cutoff"
)
FINDINGS_CUTOFF_ENFORCEMENT = (
    "not_applicable: no external-agent findings exist in this codebase; "
    "in-game AIReasoningResult records are deliberately never projected here"
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _active_run_id() -> str:
    """The run every read below is served from. Returned on every response
    so the caller can bind a mission to a run and detect a mid-mission run
    switch (app/persistence.py's SLOT is a process global that
    GameState.switch_run()/create_run() can repoint at runtime)."""
    return persistence.get_active_slot()


def _validate_cutoff(knowledge_cutoff_sim_minutes: int) -> None:
    if knowledge_cutoff_sim_minutes < 0:
        raise HTTPException(status_code=400, detail="knowledgeCutoffSimMinutes must be >= 0")


@router.get("/approved-research", response_model=ApprovedResearchResponse)
async def approved_research(
    knowledge_cutoff_sim_minutes: int = Query(alias="knowledgeCutoffSimMinutes"),
    category: ResearchCategory | None = Query(default=None),
    symbol: str | None = Query(default=None),
    limit: int = Query(default=RESEARCH_DEFAULT_LIMIT, ge=1, le=RESEARCH_MAX_LIMIT),
) -> ApprovedResearchResponse:
    """Approved ResearchItems only, ordered `createdAt` descending then `id`
    ascending (a total order — never an unordered set). See this module's
    docstring for why the cutoff is enforced against approval time here."""
    _validate_cutoff(knowledge_cutoff_sim_minutes)
    state = await game_state.snapshot()

    matched = [
        item
        for item in state.research
        if item.approved_for_agent_read
        and item.approved_for_agent_read_at_sim_minutes is not None
        and item.approved_for_agent_read_at_sim_minutes <= knowledge_cutoff_sim_minutes
        and (category is None or item.category == category)
        and (symbol is None or item.symbol == symbol)
    ]
    # Total order: createdAt descending, then id ascending. Python's sort is
    # stable, so sorting by the ascending tiebreak first and the descending
    # primary second yields exactly that, with no reverse-order surprises on
    # the tiebreak.
    matched.sort(key=lambda item: item.id)
    matched.sort(key=lambda item: item.created_at, reverse=True)

    truncated = len(matched) > limit
    page = matched[:limit]
    return ApprovedResearchResponse(
        runId=_active_run_id(),
        dataCategory="simulated",
        resultCount=len(page),
        truncated=truncated,
        cutoffEnforcement=RESEARCH_CUTOFF_ENFORCEMENT,
        asOfSimMinutes=sim_minutes(state.time),
        retrievedAt=_now_iso(),
        results=[
            ApprovedResearchRead(
                id=item.id,
                title=item.title,
                category=item.category,
                symbol=item.symbol,
                summary=item.summary,
                confidence=item.confidence,
                createdAt=item.created_at,
                updatedAt=item.updated_at,
                approvedForAgentReadAt=item.approved_for_agent_read_at,
                approvedForAgentReadAtSimMinutes=item.approved_for_agent_read_at_sim_minutes,
                approvedForAgentReadBy=item.approved_for_agent_read_by,
            )
            for item in page
        ],
    )


@router.get("/approved-memory", response_model=ApprovedMemoryResponse)
async def approved_memory(
    knowledge_cutoff_sim_minutes: int = Query(alias="knowledgeCutoffSimMinutes"),
    source: InstitutionalMemorySource | None = Query(default=None),
    market_regime: MarketEnvironmentRegime | None = Query(default=None, alias="marketRegime"),
    symbol: str | None = Query(default=None),
    limit: int = Query(default=MEMORY_DEFAULT_LIMIT, ge=1, le=MEMORY_MAX_LIMIT),
) -> ApprovedMemoryResponse:
    """Approved InstitutionalMemoryEntries only, ordered `simDay` descending,
    then `confidence` descending, then `id` ascending.

    `originatingAgent` and `relevancePct` are deliberately NOT projected —
    see ApprovedMemoryRead's own allowlist comment in app/schemas.py.
    Superseded entries are included with their links intact."""
    _validate_cutoff(knowledge_cutoff_sim_minutes)
    state = await game_state.snapshot()

    cutoff_sim_day = knowledge_cutoff_sim_minutes // MINUTES_PER_SIM_DAY
    matched = [
        entry
        for entry in state.institutional_memory
        if entry.approved_for_agent_read
        and entry.approved_for_agent_read_at_sim_minutes is not None
        and entry.approved_for_agent_read_at_sim_minutes <= knowledge_cutoff_sim_minutes
        and entry.sim_day <= cutoff_sim_day
        and (source is None or entry.source == source)
        and (market_regime is None or entry.market_regime == market_regime)
        and (symbol is None or entry.symbol == symbol)
    ]
    matched.sort(key=lambda entry: entry.id)
    matched.sort(key=lambda entry: (entry.sim_day, entry.confidence), reverse=True)

    truncated = len(matched) > limit
    page = matched[:limit]
    return ApprovedMemoryResponse(
        runId=_active_run_id(),
        dataCategory="simulated",
        resultCount=len(page),
        truncated=truncated,
        cutoffEnforcement=MEMORY_CUTOFF_ENFORCEMENT,
        asOfSimMinutes=sim_minutes(state.time),
        retrievedAt=_now_iso(),
        results=[
            ApprovedMemoryRead(
                id=entry.id,
                source=entry.source,
                createdAt=entry.created_at,
                simDay=entry.sim_day,
                eventRef=entry.event_ref,
                marketRegime=entry.market_regime,
                symbol=entry.symbol,
                domain=entry.domain,
                observation=entry.observation,
                interpretation=entry.interpretation,
                lesson=entry.lesson,
                confidence=entry.confidence,
                provenance=entry.provenance,
                status=entry.status,
                supersedesId=entry.supersedes_id,
                supersededById=entry.superseded_by_id,
                approvedForAgentReadAt=entry.approved_for_agent_read_at,
                approvedForAgentReadAtSimMinutes=entry.approved_for_agent_read_at_sim_minutes,
                approvedForAgentReadBy=entry.approved_for_agent_read_by,
            )
            for entry in page
        ],
    )


@router.get("/agent-findings", response_model=AgentFindingsResponse)
async def agent_findings(
    external_agent_id: str = Query(alias="externalAgentId"),
    knowledge_cutoff_sim_minutes: int = Query(alias="knowledgeCutoffSimMinutes"),
    limit: int = Query(default=FINDINGS_DEFAULT_LIMIT, ge=1, le=FINDINGS_MAX_LIMIT),
) -> AgentFindingsResponse:
    """Prior findings produced by ONE external agent.

    HONEST v0 BEHAVIOR: this always returns an empty result set, because no
    external-agent finding can exist yet — submission is explicitly out of
    scope for this milestone, `AIReasoningRole` has no external-agent value,
    and `AIReasoningResult` has no `external_agent_id` field (all verified at
    HEAD 39bfe9e).

    The empty list is CORRECT, not unimplemented. Projecting this codebase's
    existing in-game `ai_reasoning_results` here would expose another agent's
    private reasoning (Nova's researcher runs, the Devil's Advocate's
    challenges) to an external agent — which the contract forbids outright as
    both a confidentiality breach and an anchoring hazard
    (docs/SCOUT_READONLY_TOOL_CONTRACT_V0.md §7.5). The endpoint exists now so
    the boundary's shape is fixed before anything can flow through it."""
    _validate_cutoff(knowledge_cutoff_sim_minutes)
    if not external_agent_id.strip():
        raise HTTPException(status_code=400, detail="externalAgentId must be a non-empty string")
    state = await game_state.snapshot()

    return AgentFindingsResponse(
        runId=_active_run_id(),
        dataCategory="unavailable",
        resultCount=0,
        truncated=False,
        cutoffEnforcement=FINDINGS_CUTOFF_ENFORCEMENT,
        asOfSimMinutes=sim_minutes(state.time),
        retrievedAt=_now_iso(),
        results=[],
    )
