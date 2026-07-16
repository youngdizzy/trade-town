"""In-memory authoritative game state, shared across all connected clients.

TradeTown v0.1 is single-tenant (one company, one save slot) — this is
intentionally a process-wide singleton rather than per-session state.
"""
from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone

from app.schedule import block_for_hour
from app.schemas import (
    EntityTransform,
    GameSaveState,
    MemoryEntry,
    ScoutState,
    SettingsState,
    TimeState,
)

MAX_DIALOGUE_HISTORY = 200
MAX_SCOUT_MEMORY = 50


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_state() -> GameSaveState:
    return GameSaveState(
        version="0.1",
        player=EntityTransform(scene="LobbyScene", x=160, y=220, facing="down"),
        scout=ScoutState(
            transform=EntityTransform(scene="ScoutOfficeScene", x=128, y=96, facing="down"),
            location="scout-office",
            currentTask="Scanning market news",
            mood=65,
            energy=80,
            memory=[],
        ),
        time=TimeState(day=1, hour=8, minute=0),
        settings=SettingsState(musicVolume=0.5, sfxVolume=0.7, autosaveIntervalSec=60, showFps=False),
        dialogueHistory=[],
        updatedAt=_now_iso(),
    )


class GameState:
    """Thread-safe (via asyncio.Lock) holder for the single authoritative save."""

    def __init__(self) -> None:
        self.data: GameSaveState = default_state()
        self.lock = asyncio.Lock()

    async def apply_client_save(self, incoming: GameSaveState) -> GameSaveState:
        """Merge a client-submitted save. Player position/settings/dialogue come from
        the client; scout + time stay server-authoritative (the sim loop owns them)."""
        async with self.lock:
            self.data = self.data.model_copy(
                update={
                    "player": incoming.player,
                    "settings": incoming.settings,
                    "dialogue_history": incoming.dialogue_history[-MAX_DIALOGUE_HISTORY:],
                    "updated_at": _now_iso(),
                }
            )
            return self.data

    async def load_from(self, saved: GameSaveState) -> None:
        async with self.lock:
            self.data = saved

    async def snapshot(self) -> GameSaveState:
        async with self.lock:
            return self.data

    async def tick(self, minutes: int) -> GameSaveState:
        """Advance the game clock and update Scout's schedule/mood/energy. Called by the sim loop."""
        async with self.lock:
            time = self.data.time
            total_minutes = time.hour * 60 + time.minute + minutes
            day = time.day + total_minutes // (24 * 60)
            total_minutes %= 24 * 60
            hour, minute = divmod(total_minutes, 60)
            new_time = TimeState(day=day, hour=hour, minute=minute)

            block = block_for_hour(hour)
            scout = self.data.scout
            task_changed = scout.current_task != block.task

            energy_delta = 3 if block.task == "Resting" else -1.5
            mood_delta = random.uniform(-2, 2.5)
            new_energy = min(100.0, max(5.0, scout.energy + energy_delta))
            new_mood = min(100.0, max(5.0, scout.mood + mood_delta))

            memory = scout.memory
            if task_changed:
                memory = [
                    *scout.memory,
                    MemoryEntry(
                        id=f"{day}-{hour}-{minute}",
                        summary=f"Started: {block.task}",
                        day=day,
                        hour=hour,
                    ),
                ][-MAX_SCOUT_MEMORY:]

            new_scout = scout.model_copy(
                update={
                    "location": block.location,
                    "current_task": block.task,
                    "mood": new_mood,
                    "energy": new_energy,
                    "memory": memory,
                }
            )

            self.data = self.data.model_copy(update={"time": new_time, "scout": new_scout, "updated_at": _now_iso()})
            return self.data


game_state = GameState()
