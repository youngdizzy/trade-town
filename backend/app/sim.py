"""Background simulation loop. Keeps every agent's schedule/mood/energy and the
game clock ticking forward continuously — including while no client is
connected — and broadcasts each tick to connected WebSocket clients so the
office feels alive."""
from __future__ import annotations

import asyncio
import logging

from app.config import settings
from app.persistence import persist_modules
from app.state import game_state
from app.ws_manager import build_state_message, ws_manager

logger = logging.getLogger("tradetown.sim")


async def run_sim_loop() -> None:
    tick_count = 0
    last_day = game_state.data.time.day
    last_trade_count = len(game_state.data.paper_portfolio.trade_history)
    try:
        while True:
            await asyncio.sleep(settings.tick_interval_seconds)
            state = await game_state.tick(settings.game_minutes_per_tick)
            await ws_manager.broadcast(build_state_message(state))

            tick_count += 1
            trade_count = len(state.paper_portfolio.trade_history)
            # Two save strategies, not one: a periodic safety-net cadence
            # (PERSIST_INTERVAL_TICKS, ~30s by default) for the ordinary
            # slow drift of agent mood/energy/research, PLUS an immediate
            # persist right when something a player would actually miss
            # happens — a new in-game day starting, or a trade closing
            # (realized P&L changing). Checking for those two conditions
            # is cheap (an int compare and a list length compare) so this
            # never turns into a save-every-tick storm the way eagerly
            # persisting on every mood/energy tick would.
            day_advanced = state.time.day != last_day
            trade_closed = trade_count != last_trade_count
            if day_advanced or trade_closed or tick_count % settings.persist_interval_ticks == 0:
                persist_modules(state)
            last_day = state.time.day
            last_trade_count = trade_count
    except asyncio.CancelledError:
        logger.info("Simulation loop cancelled; persisting final state.")
        persist_modules(await game_state.snapshot())
        raise
