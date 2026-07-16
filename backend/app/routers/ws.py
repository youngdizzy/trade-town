from __future__ import annotations

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.state import game_state
from app.ws_manager import ws_manager

logger = logging.getLogger("tradetown.ws")
router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket) -> None:
    await ws_manager.connect(websocket)
    try:
        state = await game_state.snapshot()
        await websocket.send_text(
            json.dumps(
                {
                    "type": "state",
                    "time": state.time.model_dump(by_alias=True),
                    "scout": state.scout.model_dump(by_alias=True),
                }
            )
        )
        while True:
            # Clients don't need to send anything in v0.1; this just detects disconnects.
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(websocket)
