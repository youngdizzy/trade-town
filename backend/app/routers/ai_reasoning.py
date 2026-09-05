"""CEO directive "TradeTown — True AI Agent Reasoning Foundation 1.0" — the
one real HTTP surface for the new AI reasoning layer.

`POST /api/ai-reasoning/run` is the ONLY entry point that ever triggers a
real (or honestly-unavailable) provider call — always human-triggered from
this router today (Part XXVIII shadow-mode-first: nothing in `nexus.py`'s
own autonomous tick loop calls this). It never places an order, never
resolves a proposal, and never writes institutional memory; see
`GameState.submit_ai_reasoning_request()`'s own docstring for the full real
guarantee.

`GET /api/ai-reasoning/results` is a read-only, computed-fresh-from-save
listing (same convention as `routers/institutional_memory.py`), optionally
filtered to one proposal. `POST /api/ai-reasoning/refresh-outcomes`
triggers the one real, additive shadow-grading pass
(`GameState.refresh_ai_reasoning_outcomes()`) — never invents an outcome
for a proposal that has no real decision/journal entry yet.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.persistence import persist_modules
from app.schemas import AIReasoningResult, AIReasoningRole
from app.state import game_state

router = APIRouter(prefix="/api/ai-reasoning", tags=["ai-reasoning"])


@router.post("/run", response_model=AIReasoningResult)
async def run_ai_reasoning(proposal_id: str = Query(alias="proposalId"), role: AIReasoningRole = Query(default="researcher")) -> AIReasoningResult:
    """Runs one real Researcher or Devil's Advocate reasoning call against
    a real, currently-pending `TradeProposal`. Returns the full structured
    `AIReasoningResult` regardless of outcome — including an honest
    `provider_unavailable`/`provider_timeout`/`provider_error`/
    `invalid_output` status when the real call didn't produce a usable
    result; this endpoint never raises for those cases, since they are
    real, expected, disclosed outcomes, not server errors. Raises 404 only
    when `proposal_id` doesn't match any real, currently-pending
    proposal."""
    try:
        state, result = await game_state.submit_ai_reasoning_request(proposal_id, role=role)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    persist_modules(state)
    return result


@router.get("/results", response_model=list[AIReasoningResult])
async def list_ai_reasoning_results(proposal_id: str | None = Query(default=None, alias="proposalId")) -> list[AIReasoningResult]:
    """The full, real, permanent equities AI reasoning history
    (`domain == "equities"` only — CEO directive "TradeTown — Memecoin
    Sniper AI 1.0" added a second domain onto the SAME shared
    `ai_reasoning_results` list; see `routers/sniper_ai_reasoning.py`'s
    own `/results` for that domain's equivalent read), optionally
    filtered to one real proposal. Read-only, computed fresh."""
    state = await game_state.snapshot()
    results = [r for r in state.ai_reasoning_results if r.domain == "equities"]
    if proposal_id is not None:
        results = [r for r in results if r.proposal_id == proposal_id]
    return results


@router.post("/refresh-outcomes", response_model=list[AIReasoningResult])
async def refresh_ai_reasoning_outcomes() -> list[AIReasoningResult]:
    """Grades every real, still-pending equities `AIReasoningResult`
    against the same real decision/journal-entry evidence the Knowledge
    Application Loop already uses (`resolve_deterministic_outcome()`);
    never touches a result that isn't pending, and never touches a
    non-equities-domain result (see `refresh_sniper_ai_reasoning_outcomes()`
    for that domain's own pass over the SAME shared list). Returns the
    full, refreshed equities-domain list."""
    state = await game_state.refresh_ai_reasoning_outcomes()
    persist_modules(state)
    return [r for r in state.ai_reasoning_results if r.domain == "equities"]
