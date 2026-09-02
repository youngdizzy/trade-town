"""CEO directive "TradeTown — Memecoin Sniper Agent." Paper-only,
simulated data throughout — see app/memecoin_sniper.py's own module
docstring for the full honesty boundary."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from app.memecoin_sniper import build_engine_status_read
from app.persistence import persist_modules
from app.schemas import (
    SniperCandidate,
    SniperEngineStatusRead,
    SniperEvent,
    SniperLead,
    SniperLesson,
    SniperLiveArmingStatus,
    SniperPosition,
    SniperRiskState,
    SniperTrade,
)
from app.state import game_state

router = APIRouter(prefix="/api/sniper", tags=["sniper"])


def _today_start_iso() -> str:
    now = datetime.now(timezone.utc)
    return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()


@router.get("/status", response_model=SniperEngineStatusRead)
async def sniper_status() -> SniperEngineStatusRead:
    state = await game_state.snapshot()
    return build_engine_status_read(state.sniper_engine_config, state.sniper_risk_state, state.sniper_positions, state.sniper_trade_history, today_start_iso=_today_start_iso())


@router.get("/candidates", response_model=list[SniperCandidate])
async def sniper_candidates(limit: int = Query(default=30, ge=1, le=60)) -> list[SniperCandidate]:
    state = await game_state.snapshot()
    return state.sniper_candidates[:limit]


@router.get("/positions", response_model=list[SniperPosition])
async def sniper_positions(open_only: bool = Query(default=False, alias="openOnly")) -> list[SniperPosition]:
    state = await game_state.snapshot()
    if open_only:
        return [p for p in state.sniper_positions if p.status == "open"]
    return state.sniper_positions


@router.get("/trades", response_model=list[SniperTrade])
async def sniper_trades(limit: int = Query(default=100, ge=1, le=500)) -> list[SniperTrade]:
    state = await game_state.snapshot()
    return list(reversed(state.sniper_trade_history))[:limit]


@router.get("/events", response_model=list[SniperEvent])
async def sniper_events(mint: str | None = Query(default=None), limit: int = Query(default=50, ge=1, le=300)) -> list[SniperEvent]:
    """Professional Trading Terminal directive, Part VII — the real,
    persisted event timeline (see SniperEvent's own docstring). Newest
    first; `mint` filters to one token's own history (used by the
    terminal's focused-trade timeline)."""
    state = await game_state.snapshot()
    events = state.sniper_events
    if mint is not None:
        events = [e for e in events if e.mint == mint]
    return list(reversed(events))[:limit]


@router.get("/leads", response_model=list[SniperLead])
async def sniper_leads() -> list[SniperLead]:
    state = await game_state.snapshot()
    return state.sniper_leads


@router.get("/lessons", response_model=list[SniperLesson])
async def sniper_lessons() -> list[SniperLesson]:
    state = await game_state.snapshot()
    return state.sniper_lessons


@router.get("/risk", response_model=SniperRiskState)
async def sniper_risk() -> SniperRiskState:
    state = await game_state.snapshot()
    return state.sniper_risk_state


@router.get("/live-arming", response_model=SniperLiveArmingStatus)
async def sniper_live_arming() -> SniperLiveArmingStatus:
    """Section 23/24 — always honestly `armed: false` in this
    environment. See app/memecoin_sniper.py::evaluate_live_arming()."""
    from app.memecoin_sniper import evaluate_live_arming

    return evaluate_live_arming()


class UpdateSniperEngineRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: str | None = None
    mode: str | None = None
    turbo: bool | None = None
    copy_trading_enabled: bool | None = None


@router.post("/engine", response_model=SniperEngineStatusRead)
async def update_sniper_engine(payload: UpdateSniperEngineRequest) -> SniperEngineStatusRead:
    """The CEO's real engine control surface (start/stop/pause, turbo,
    copy-trading toggle). `mode="live"` is always rejected — see
    `GameState.update_sniper_engine_config()`'s own docstring for why."""
    state, error = await game_state.update_sniper_engine_config(
        status=payload.status, mode=payload.mode, turbo=payload.turbo, copy_trading_enabled=payload.copy_trading_enabled
    )
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return build_engine_status_read(state.sniper_engine_config, state.sniper_risk_state, state.sniper_positions, state.sniper_trade_history, today_start_iso=_today_start_iso())


@router.post("/positions/{position_id}/close", response_model=SniperTrade)
async def close_sniper_position(position_id: str) -> SniperTrade:
    """Section 18's manual exit path — closes at the position's own
    real, already-simulated current price."""
    state, trade, error = await game_state.close_sniper_position(position_id, reason="manual_exit")
    if error is not None:
        raise HTTPException(status_code=404, detail=error)
    persist_modules(state)
    assert trade is not None
    return trade
