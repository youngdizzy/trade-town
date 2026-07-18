from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db
from app.persistence import load_save, persist_save
from app.routers import health, save, ws
from app.sim import run_sim_loop
from app.state import game_state

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tradetown.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    existing = load_save()
    if existing is not None:
        await game_state.load_from(existing)
        logger.info("Loaded existing save (day %s, %02d:%02d)", existing.time.day, existing.time.hour, existing.time.minute)
    else:
        persist_save(await game_state.snapshot())
        logger.info("No existing save found; persisted fresh default state.")

    sim_task = asyncio.create_task(run_sim_loop())
    app.state.sim_task = sim_task

    yield

    sim_task.cancel()
    try:
        await sim_task
    except asyncio.CancelledError:
        pass


app = FastAPI(title="TradeTown API", version="0.5.0", lifespan=lifespan)

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
