from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db
from app.persistence import DEFAULT_SLOT, ensure_default_run_registered, get_active_run_id, load_state, persist_modules, register_run, set_active_slot
from app.routers import accounts, agent_trading_status, audit, black_box, black_swan, board, calendar, calibration, constitution, decision_vault, education, emergency, energy, executive, failure_review, foundational_mentors, goals, health, institutional_memory, knowledge_graph, market, mentor, performance_review, player_vs_ai, prediction_tracking, quant_developer, risk, runs, sandbox, save, self_improvement, situation_room, skill_progression, sniper, talent, time, trades, trading_modes, trading_restrictions, travel_mode, treasury, vision_board, ws
from app.sim import run_sim_loop
from app.state import game_state

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tradetown.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    # CEO directive "Proper Multi-Run / Save Isolation System" — registers
    # a pre-existing single-slot save as a real run named "Original Run"
    # exactly once (idempotent no-op on every later boot), then resolves
    # which real, persisted run should actually load this boot (the same
    # one active when the process last shut down, never silently reverting
    # to DEFAULT_SLOT — see get_active_run_id()'s own docstring).
    ensure_default_run_registered()
    active_run_id = get_active_run_id()
    set_active_slot(active_run_id)
    existing = load_state()
    if existing is not None:
        await game_state.load_from(existing)
        logger.info("Loaded existing save (day %s, %02d:%02d)", existing.time.day, existing.time.hour, existing.time.minute)
    else:
        persist_modules(await game_state.snapshot())
        logger.info("No existing save found; persisted fresh default state.")
        # Safety net: the resolved active slot had no data (a genuinely
        # fresh deployment, or an ActiveRun pointer naming a slot that was
        # never actually registered) — register it now so it's a real,
        # discoverable run rather than an invisible orphan slot.
        register_run(active_run_id, "Original Run" if active_run_id == DEFAULT_SLOT else "Recovered Run")

    sim_task = asyncio.create_task(run_sim_loop())
    app.state.sim_task = sim_task

    yield

    sim_task.cancel()
    try:
        await sim_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="TradeTown API", version="0.6.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, prefix="/api")
app.include_router(agent_trading_status.router)
app.include_router(save.router)
app.include_router(ws.router)
app.include_router(market.router)
app.include_router(energy.router)
app.include_router(calibration.router)
app.include_router(player_vs_ai.router)
app.include_router(education.router)
app.include_router(trades.router)
app.include_router(executive.router)
app.include_router(knowledge_graph.router)
app.include_router(mentor.router)
app.include_router(treasury.router)
app.include_router(accounts.router)
app.include_router(calendar.router)
app.include_router(time.router)
app.include_router(black_box.router)
app.include_router(talent.router)
app.include_router(sandbox.router)
app.include_router(quant_developer.router)
app.include_router(constitution.router)
app.include_router(risk.router)
app.include_router(risk.risk_contracts_router)
app.include_router(sniper.router)
app.include_router(foundational_mentors.router)
app.include_router(decision_vault.router)
app.include_router(institutional_memory.router)
app.include_router(performance_review.router)
app.include_router(skill_progression.router)
app.include_router(prediction_tracking.router)
app.include_router(failure_review.router)
app.include_router(goals.router)
app.include_router(emergency.router)
app.include_router(black_swan.router)
app.include_router(audit.router)
app.include_router(trading_modes.router)
app.include_router(trading_restrictions.router)
app.include_router(situation_room.router)
app.include_router(travel_mode.router)
app.include_router(board.router)
app.include_router(self_improvement.router)
app.include_router(vision_board.router)
app.include_router(runs.router)
