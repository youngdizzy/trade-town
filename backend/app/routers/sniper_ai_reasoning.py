"""CEO directive "TradeTown — Memecoin Sniper AI 1.0" — the Memecoin
Sniper's own AI-reasoning HTTP surface, mirroring
`app/routers/ai_reasoning.py`'s exact conventions on a separate prefix so
the two domains' endpoints (and OpenAPI docs) are never conflated.

`POST /api/sniper/ai-reasoning/run` is the ONLY entry point that ever
triggers a real (or honestly-unavailable) provider call for this domain
— always human-triggered from this router; nothing in
`tick_sniper_engine()` calls this (Part XVI shadow-mode-first). It never
places an order, never alters `sniper_engine_config`/risk state, and
never writes institutional memory directly — see
`GameState.submit_sniper_ai_reasoning_request()`'s own docstring for the
full real guarantee.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.persistence import persist_modules
from app.schemas import AIReasoningResult
from app.sniper_ai_context import compare_sniper_ai_to_deterministic
from app.state import game_state

router = APIRouter(prefix="/api/sniper/ai-reasoning", tags=["sniper-ai-reasoning"])


@router.post("/run", response_model=AIReasoningResult)
async def run_sniper_ai_reasoning(candidate_id: str = Query(alias="candidateId")) -> AIReasoningResult:
    """Runs one real Sniper Analyst reasoning call against a real,
    currently-listed `SniperCandidate` (whether it was sniped, rejected,
    or is still on watch — Part V's "NO TRADE" case is a first-class
    input here, not a degraded one). Returns the full structured
    `AIReasoningResult` regardless of outcome, including an honest
    `provider_unavailable`/`provider_timeout`/`provider_error`/
    `invalid_output` status — never raises for those, since they are
    real, expected, disclosed outcomes. Raises 404 only when
    `candidate_id` doesn't match any real, currently-listed candidate."""
    try:
        state, result = await game_state.submit_sniper_ai_reasoning_request(candidate_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
    persist_modules(state)
    return result


@router.get("/results", response_model=list[AIReasoningResult])
async def list_sniper_ai_reasoning_results(mint: str | None = Query(default=None)) -> list[AIReasoningResult]:
    """The full, real, permanent Sniper AI reasoning history (`domain ==
    "memecoin_sniper"` only, filtered out of the SAME shared
    `ai_reasoning_results` list the equities layer also uses — no second,
    duplicated result list for this domain), optionally filtered to one
    real token `mint` (this domain's own real join key — see
    app/sniper_ai_context.py's own module docstring for why there is no
    separate `candidate_id` field to filter by instead)."""
    state = await game_state.snapshot()
    results = [r for r in state.ai_reasoning_results if r.domain == "memecoin_sniper"]
    if mint is not None:
        results = [r for r in results if r.proposal_id == mint]
    return results


@router.post("/refresh-outcomes", response_model=list[AIReasoningResult])
async def refresh_sniper_ai_reasoning_outcomes() -> list[AIReasoningResult]:
    """Grades every real, still-pending completed Sniper `AIReasoningResult`
    against this domain's own real position/trade evidence
    (`resolve_sniper_deterministic_outcome()`); never touches a result
    that isn't pending. Returns the full, refreshed Sniper-domain list."""
    state = await game_state.refresh_sniper_ai_reasoning_outcomes()
    persist_modules(state)
    return [r for r in state.ai_reasoning_results if r.domain == "memecoin_sniper"]


@router.get("/comparison")
async def sniper_ai_comparison(mint: str | None = Query(default=None)) -> dict[str, str]:
    """Part XVI/XVII — a real, computed-fresh (never persisted) AGREE/
    DISAGREE/PARTIAL/INCONCLUSIVE read per real Sniper AI reasoning
    result, keyed by that result's own real `id` — never a single
    aggregate score. See
    app/sniper_ai_context.py::compare_sniper_ai_to_deterministic()'s own
    docstring for exactly how each value is derived."""
    state = await game_state.snapshot()
    results = [r for r in state.ai_reasoning_results if r.domain == "memecoin_sniper"]
    if mint is not None:
        results = [r for r in results if r.proposal_id == mint]
    return {r.id: compare_sniper_ai_to_deterministic(r) for r in results}
