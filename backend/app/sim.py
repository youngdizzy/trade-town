"""Background simulation loop. Keeps Scout's schedule/mood/energy and the game
clock ticking forward continuously — including while no client is connected —
and broadcasts each tick to connected WebSocket clients so the office feels alive."""
from __future__ import annotations

import asyncio
import logging

from app.config import settings
from app.persistence import persist_save
from app.state import game_state
from app.ws_manager import ws_manager

logger = logging.getLogger("tradetown.sim")


async def run_sim_loop() -> None:
    tick_count = 0
    try:
        while True:
            await asyncio.sleep(settings.tick_interval_seconds)
            state = await game_state.tick(settings.game_minutes_per_tick)

            await ws_manager.broadcast(
                {
                    "type": "state",
                    "time": state.time.model_dump(by_alias=True),
                    "scout": state.scout.model_dump(by_alias=True),
                }
            )

            tick_count += 1
            if tick_count % settings.persist_interval_ticks == 0:
                persist_save(state)
    except asyncio.CancelledError:
        logger.info("Simulation loop cancelled; persisting final state.")
        persist_save(await game_state.snapshot())
        raise
