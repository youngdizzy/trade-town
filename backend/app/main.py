from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db
from app.persistence import load_state, persist_modules
from app.routers import accounts, audit, black_box, black_swan, board, calendar, calibration, constitution, decision_vault, education, emergency, energy, executive, foundational_mentors, goals, health, knowledge_graph, market, mentor, player_vs_ai, risk, sandbox, save, self_improvement, situation_room, talent, time, trades, trading_modes, travel_mode, treasury, vision_board, ws
from app.sim import run_sim_loop
from app.state import game_state

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tradetown.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    existing = load_state()
    if existing is not None:
        await game_state.load_from(existing)
        logger.info("Loaded existing save (day %s, %02d:%02d)", existing.time.day, existing.time.hour, existing.time.minute)
    else:
        persist_modules(await game_state.snapshot())
        logger.info("No existing save found; persisted fresh default state.")

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
app.include_router(constitution.router)
app.include_router(risk.router)
app.include_router(foundational_mentors.router)
app.include_router(decision_vault.router)
app.include_router(goals.router)
app.include_router(emergency.router)
app.include_router(black_swan.router)
app.include_router(audit.router)
app.include_router(trading_modes.router)
app.include_router(situation_room.router)
app.include_router(travel_mode.router)
app.include_router(board.router)
app.include_router(self_improvement.router)
app.include_router(vision_board.router)
