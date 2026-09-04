""""TradeTown — Department Debate & Collaboration Intelligence 1.0" —
read-only endpoints, mirroring routers/institutional_memory.py's own
convention: `await game_state.snapshot()`, computed fresh every call,
nothing here mutates the save. Every `CollaborationCaseSummary` is built
straight from the real, already-permanent `executive_meeting_log`/
`challenge_reports` — this router adds no new persisted state.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.collaboration_intelligence import average_collaboration_case_score, compute_collaboration_case_summaries
from app.schemas import CollaborationCaseSummary
from app.state import game_state

router = APIRouter(prefix="/api/collaboration", tags=["collaboration"])


@router.get("/cases", response_model=list[CollaborationCaseSummary])
async def list_cases() -> list[CollaborationCaseSummary]:
    """Every real collaboration case on file, newest-decision-last (the
    same order `executive_meeting_log` itself is stored in) — an honest
    empty list, never a fabricated placeholder, when no proposal has
    been resolved yet."""
    state = await game_state.snapshot()
    return compute_collaboration_case_summaries(state.executive_meeting_log, state.challenge_reports)


@router.get("/score", response_model=float | None)
async def collaboration_score() -> float | None:
    """The same real average `app/wisdom.py::_support_collaboration()`
    falls back to — exposed directly so the CEO can see the exact
    number behind that factor's own real evidence line, not just infer
    it. `null` — NOT ENOUGH EVIDENCE — when no real collaboration case
    exists yet."""
    state = await game_state.snapshot()
    summaries = compute_collaboration_case_summaries(state.executive_meeting_log, state.challenge_reports)
    return average_collaboration_case_score(summaries)
