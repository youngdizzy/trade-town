from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, HTTPException

from app.persistence import persist_modules
from app.save_modules import ARCHIVE_MODULES, CORE_MODULES, assemble_state, split_state
from app.schemas import ClientSaveRequest, GameSaveState, SaveResponse
from app.state import game_state

router = APIRouter(prefix="/api", tags=["save"])


@router.get("/load", response_model=GameSaveState)
async def load_game() -> GameSaveState:
    """v0.7 Save Architecture Redesign Phase 2 — returns only the core
    modules (see app/save_modules.py): company/employees/settings/world/
    research/training/founders/derived. The archive modules (trade_history/
    knowledge_archive/academy — real historical logs that only grow) come
    back empty here, not omitted or fabricated — assemble_state() fills
    them with the same defaults a fresh game legitimately starts with. Real
    archive data is available via GET /api/load/archive/{module} below, and
    every Command Center panel that displays it hydrates live from the
    WebSocket tick broadcast within moments of connecting regardless (see
    ws_manager.py, unchanged) — so no panel is ever left showing stale or
    missing data because of what this endpoint left out."""
    snapshot = await game_state.snapshot()
    core_only = {module: data for module, data in split_state(snapshot).items() if module in CORE_MODULES}
    return assemble_state(core_only)


@router.get("/load/archive/{module}")
async def load_archive_module(module: str) -> dict[str, Any]:
    """Fetches one archive module's real data on demand (see GET /load's
    own docstring for why it's excluded from the normal load response).
    Returns the module's fields as a plain alias-keyed dict, the same shape
    they'd have inside a full GameSaveState — e.g. `trade_history` returns
    `{"decisions": [...], "ceoDecisions": [...], ...}`."""
    if module not in ARCHIVE_MODULES:
        raise HTTPException(status_code=404, detail=f"Unknown archive module {module!r}. Valid modules: {sorted(ARCHIVE_MODULES)}")
    snapshot = await game_state.snapshot()
    return split_state(snapshot)[module]


@router.post("/save", response_model=SaveResponse)
async def save_game(payload: ClientSaveRequest) -> SaveResponse:
    """v0.7 Save Architecture Redesign — payload is deliberately narrow (see
    ClientSaveRequest's own docstring): the client only ever owns player
    position, settings, and dialogue history, and used to send the entire
    ~840KB GameSaveState for the server to discard everything else from."""
    state = await game_state.apply_client_save(payload)
    modules = persist_modules(state)
    return SaveResponse(updatedAt=datetime.now(timezone.utc).isoformat(), modules=modules)
