"""CEO directive "Command Center + Professional Quant Trading Firm
Upgrade," Phase 2 — read-only endpoint over `app/agent_trading_status.py`.
Computed fresh every call from already-persisted state (the same
`await game_state.snapshot()` convention `app/routers/performance_
review.py`/`app/routers/trades.py` already use) — nothing here mutates
the save, and nothing here is broadcast over the WS tick (this is an
on-demand AI Desk read, not a per-tick field every scene needs).
"""
from __future__ import annotations

from fastapi import APIRouter

from app.agent_trading_status import compute_agent_trading_status
from app.schemas import AGENT_IDS, AgentTradingStatusRead
from app.state import game_state

router = APIRouter(prefix="/api/agents", tags=["agents"])


@router.get("/trading-status", response_model=list[AgentTradingStatusRead])
async def trading_status() -> list[AgentTradingStatusRead]:
    """Every real agent's current trading-relevant state — see
    app/agent_trading_status.py's own module docstring for exactly
    which real signal backs each one."""
    state = await game_state.snapshot()
    return [
        compute_agent_trading_status(
            agent_id,
            trade_proposals=state.trade_proposals,
            research=state.research,
            emergency_stop=state.emergency_stop,
        )
        for agent_id in AGENT_IDS
    ]
