"""Background simulation loop. Keeps every agent's schedule/mood/energy and the
game clock ticking forward continuously — including while no client is
connected — and broadcasts each tick to connected WebSocket clients so the
office feels alive."""
from __future__ import annotations

import asyncio
import logging

from app.config import settings
from app.persistence import persist_save
from app.state import game_state
from app.ws_manager import build_state_message, ws_manager

logger = logging.getLogger("tradetown.sim")


async def run_sim_loop() -> None:
    tick_count = 0
    try:
        while True:
            await asyncio.sleep(settings.tick_interval_seconds)
            state = await game_state.tick(settings.game_minutes_per_tick)
            await ws_manager.broadcast(build_state_message(state))

            tick_count += 1
            if tick_count % settings.persist_interval_ticks == 0:
                persist_save(state)
    except asyncio.CancelledError:
        logger.info("Simulation loop cancelled; persisting final state.")
        persist_save(await game_state.snapshot())
        raise
