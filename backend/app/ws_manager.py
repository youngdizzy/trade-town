from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket

from app.schemas import GameSaveState


def build_state_message(state: GameSaveState) -> dict[str, Any]:
    """Shared WS payload shape used both for the initial snapshot on connect and every sim tick."""
    return {
        "type": "state",
        "time": state.time.model_dump(by_alias=True),
        "agents": {aid: agent.model_dump(by_alias=True) for aid, agent in state.agents.items()},
        "tasks": [t.model_dump(by_alias=True) for t in state.tasks[-20:]],
        "whiteboards": state.whiteboards,
        "meeting": state.meeting.model_dump(by_alias=True),
        # state.news is already bounded per-category by nexus._trim_news()
        # (see MAX_NEWS_PER_CATEGORY) — re-slicing to a flat "last 10" here
        # would undo that balance, since discovery news fires far more
        # often than market/company news and would crowd the rarer
        # categories back out of the window. Send the whole (already
        # small) list instead.
        "news": [n.model_dump(by_alias=True) for n in state.news],
        "research": [r.model_dump(by_alias=True) for r in state.research],
        "watchlist": [w.model_dump(by_alias=True) for w in state.watchlist],
        # Already capped at MAX_MEMORY_RECORDS / MAX_MEETING_MINUTES in
        # nexus.py — same reasoning as `news` above, send as-is.
        "memory": [m.model_dump(by_alias=True) for m in state.memory],
        "meetingMinutes": [m.model_dump(by_alias=True) for m in state.meeting_minutes],
    }


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        if not self._connections:
            return
        payload = json.dumps(message)
        dead: list[WebSocket] = []
        for connection in self._connections:
            try:
                await connection.send_text(payload)
            except Exception:
                dead.append(connection)
        for connection in dead:
            self.disconnect(connection)

    @property
    def active_count(self) -> int:
        return len(self._connections)


ws_manager = ConnectionManager()
