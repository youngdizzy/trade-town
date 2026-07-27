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

from app.persistence import persist_save
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
    persist_save(await game_state.snapshot())
    return AckNotificationResponse(viewedTradeNotificationIds=viewed_ids)
