"""Design Bible Chapter 73.5 — Mobile Command Center & Remote
Operations. See app/situation_room.py's module docstring for the full
honesty boundary. SituationRoomState is computed fresh per request,
never persisted — the same "cross-cutting, computed-fresh" convention
app/audit_log.py already established for a read-only aggregate.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.schemas import SituationRoomState
from app.situation_room import compute_situation_room
from app.state import game_state

router = APIRouter(prefix="/api/situation-room", tags=["situation-room"])


@router.get("", response_model=SituationRoomState)
async def get_situation_room() -> SituationRoomState:
    state = await game_state.snapshot()
    return compute_situation_room(
        company_health=state.company_health,
        portfolio=state.paper_portfolio,
        portfolio_intelligence=state.portfolio_intelligence,
        risk_limits=state.risk_limits,
        daily_circuit_breaker=state.daily_circuit_breaker,
        risk_warnings=state.risk_warnings,
        market_environment=state.market_environment,
        trading_mode_state=state.trading_modes,
        economic_intelligence=state.economic_intelligence,
        black_swan_tier=state.black_swan_intelligence.warning.tier,
        trade_proposals=state.trade_proposals,
        emergency_stop=state.emergency_stop,
        operating_mode=state.settings.operating_mode,
    )
