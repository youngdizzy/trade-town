"""Trade outcome notification acknowledgement (v0.6.2 Phase 10) — see
app/trade_notifications.py. The popup itself is built entirely from the
real PaperTrade already in paper_portfolio.trade_history (win/loss/
breakeven and thesis-confirmed/invalidated/neutral are both a direct
read of the trade's own pnl sign); this endpoint only records that the
player has seen it.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from app.exit_efficiency import compute_exit_efficiency
from app.performance_attribution import compute_symbol_performance
from app.persistence import persist_modules
from app.schemas import ExitEfficiencySummary, SymbolPerformanceSummary
from app.state import game_state

router = APIRouter(prefix="/api/trades", tags=["trades"])


class AckNotificationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    trade_id: str = Field(alias="tradeId")


class AckNotificationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    viewed_trade_notification_ids: list[str] = Field(alias="viewedTradeNotificationIds")


@router.post("/ack", response_model=AckNotificationResponse)
async def ack_notification(payload: AckNotificationRequest) -> AckNotificationResponse:
    viewed_ids = await game_state.ack_trade_notification(payload.trade_id)
    persist_modules(await game_state.snapshot())
    return AckNotificationResponse(viewedTradeNotificationIds=viewed_ids)


@router.get("/exit-efficiency", response_model=ExitEfficiencySummary)
async def get_exit_efficiency() -> ExitEfficiencySummary:
    """CEO directive "Professional Trading Firm Transformation" — Post-
    Trade Review, Exit Efficiency (see app/exit_efficiency.py). Read-
    only, computed fresh per request from the already-real
    `trade_history` — no new GameSaveState field."""
    state = await game_state.snapshot()
    return compute_exit_efficiency(state.paper_portfolio.trade_history)


@router.get("/performance-by-symbol", response_model=SymbolPerformanceSummary)
async def get_performance_by_symbol() -> SymbolPerformanceSummary:
    """CEO directive "Next Professional Trading Firm Phase," Priority 2
    (see app/performance_attribution.py). Read-only, computed fresh per
    request from the already-real `trade_history` — no new
    GameSaveState field."""
    state = await game_state.snapshot()
    return compute_symbol_performance(state.paper_portfolio.trade_history)
