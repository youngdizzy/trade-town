"""Background simulation loop. Keeps every agent's schedule/mood/energy and the
game clock ticking forward continuously — including while no client is
connected — and broadcasts each tick to connected WebSocket clients so the
office feels alive."""
from __future__ import annotations

import asyncio
import logging

from app.config import settings
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
            # CEO directive "TradeTown — Autonomous Research Orchestrator
            # 1.0" — the real autonomous research heartbeat. Cheap on
            # every tick that isn't due (a handful of int/date compares);
            # when due, schedules the existing research_factory.py cycle
            # as its own background task rather than awaiting it here,
            # so a research cycle (up to 5 real minutes) never delays
            # this loop's own persistence/broadcast cadence.
            await game_state.maybe_orchestrate_research()

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
            #
            # CEO directive "Proper Multi-Run / Save Isolation System" —
            # this now runs BEFORE the WS broadcast below (previously
            # after) and through game_state.persist_now() (previously a
            # bare persist_modules(state) call) specifically because a
            # concurrent run switch could otherwise land in the gap an
            # `await` on the broadcast leaves open, and a bare
            # persist_modules(state) call after that gap would persist
            # this (now-stale) run's data into whatever run just became
            # active — persist_now() re-reads self.data fresh under the
            # same lock switch_run()/create_run() use, so it's always
            # provably writing the run that's actually active right now.
            day_advanced = state.time.day != last_day
            trade_closed = trade_count != last_trade_count
            if day_advanced or trade_closed or tick_count % settings.persist_interval_ticks == 0:
                await game_state.persist_now()
            last_day = state.time.day
            last_trade_count = trade_count

            await ws_manager.broadcast(build_state_message(state))
    except asyncio.CancelledError:
        logger.info("Simulation loop cancelled; persisting final state.")
        await game_state.persist_now()
        raise
