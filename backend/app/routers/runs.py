"""CEO directive "Proper Multi-Run / Save Isolation System" — the real
run-management endpoints. See app/persistence.py's own module docstring
for the underlying design (every save table already had a real, indexed
`slot` column; this just exposes real control over it) and
app/state.py's `switch_run()`/`create_run()` for the actual
lock-guarded, race-safe implementation.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app import persistence
from app.schemas import CreateRunRequest, GameSaveState, RunSummary
from app.state import game_state

router = APIRouter(prefix="/api/runs", tags=["runs"])


@router.get("", response_model=list[RunSummary])
async def list_runs() -> list[RunSummary]:
    """Every real, registered run, most-recently-played first. Read-only
    — never touches which run is actually active/ticking."""
    return persistence.list_runs()


@router.get("/active", response_model=RunSummary | None)
async def active_run() -> RunSummary | None:
    """Which run is currently loaded into the live, ticking singleton —
    the one real source of truth (see app/persistence.py's
    get_active_slot()), for a client that wants to display it without
    fetching the full save. None only if the active slot somehow isn't a
    registered run yet (a genuinely fresh deployment mid-first-boot)."""
    active_slot = persistence.get_active_slot()
    for run in persistence.list_runs():
        if run.run_id == active_slot:
            return run
    return None


@router.post("", response_model=GameSaveState)
async def create_run(payload: CreateRunRequest) -> GameSaveState:
    """Creates a brand-new run, initialized via the exact same
    default_state() every fresh deployment already uses, and switches
    the live singleton to it. The run being left behind is persisted
    first and otherwise untouched — never reset, overwritten, or
    reinitialized."""
    display_name = payload.display_name.strip() if payload.display_name and payload.display_name.strip() else "New Run"
    state, _run_id = await game_state.create_run(display_name)
    return state


@router.post("/{run_id}/activate", response_model=GameSaveState)
async def activate_run(run_id: str) -> GameSaveState:
    """Switches the live singleton to an already-registered run. 404s
    (no mutation of any kind — the active run stays exactly what it was)
    if `run_id` doesn't name a real, registered run."""
    try:
        return await game_state.switch_run(run_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from None
