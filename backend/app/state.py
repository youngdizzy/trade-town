"""In-memory authoritative game state, shared across all connected clients.

TradeTown is single-tenant (one company, one save slot) — this is
intentionally a process-wide singleton rather than per-session state.
Agent/task/whiteboard/meeting orchestration itself lives in nexus.py; this
module just owns the lock-guarded snapshot and the game clock.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app import nexus, signal_calibration
from app.agent_energy import default_agent_energy
from app.company_score import compute_company_score
from app.portfolio import default_portfolio
from app.research import default_research
from app.schemas import EntityTransform, GameSaveState, MeetingState, SettingsState, SignalCalibrationState, SignalChoice, TimeState
from app.simulation import default_strategies
from app.watchlist import default_watchlist

MAX_DIALOGUE_HISTORY = 200


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_state() -> GameSaveState:
    return GameSaveState(
        player=EntityTransform(scene="LobbyScene", x=160, y=220, facing="down"),
        agents=nexus.default_agents(),
        tasks=[],
        whiteboards={},
        meeting=MeetingState(),
        news=[],
        research=default_research(),
        watchlist=default_watchlist(),
        memory=[],
        meetingMinutes=[],
        time=TimeState(day=1, hour=8, minute=0),
        settings=SettingsState(musicVolume=0.5, sfxVolume=0.7, autosaveIntervalSec=60, showFps=False),
        dialogueHistory=[],
        paperPortfolio=default_portfolio(),
        strategies=default_strategies(),
        backtestSessions=[],
        simulationResults=[],
        hallOfFame=[],
        coachReports=[],
        companyScore=compute_company_score([], default_portfolio(), [], [], []),
        performanceSnapshots=[],
        agentEnergy=default_agent_energy(),
        signalCalibration=SignalCalibrationState(),
        updatedAt=_now_iso(),
    )


class GameState:
    """Thread-safe (via asyncio.Lock) holder for the single authoritative save."""

    def __init__(self) -> None:
        self.data: GameSaveState = default_state()
        self.lock = asyncio.Lock()

    async def apply_client_save(self, incoming: GameSaveState) -> GameSaveState:
        """Merge a client-submitted save. Player position/settings/dialogue come from
        the client; agents/tasks/whiteboards/meeting/news/time stay server-authoritative
        (NEXUS's tick loop owns them)."""
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
            self.data = nexus.register_agents(saved)

    async def snapshot(self) -> GameSaveState:
        async with self.lock:
            return self.data

    async def spend_agent_energy(self, action: str, research_id: str | None) -> tuple[GameSaveState, str | None]:
        """One Agent Energy spend, applied atomically under the same lock
        tick() uses. Returns (state, error) — error is None on success."""
        async with self.lock:
            self.data, error = nexus.apply_energy_action(self.data, action, research_id)
            return self.data, error

    async def submit_signal_calibration(self, challenge_id: str, choice: SignalChoice) -> tuple[GameSaveState, str | None]:
        """Grades a pending Signal Calibration challenge under the same
        lock every other state mutation uses, so a submit can never race a
        concurrent tick()/save. Returns (state, error)."""
        async with self.lock:
            new_calibration, new_energy, error = signal_calibration.grade_submission(
                self.data.signal_calibration, self.data.agent_energy, challenge_id, choice
            )
            if error is None:
                self.data = self.data.model_copy(update={"signal_calibration": new_calibration, "agent_energy": new_energy})
            return self.data, error

    async def tick(self, minutes: int) -> GameSaveState:
        """Advance the game clock and run one NEXUS orchestration step. Called by the sim loop."""
        async with self.lock:
            time = self.data.time
            total_minutes = time.hour * 60 + time.minute + minutes
            day = time.day + total_minutes // (24 * 60)
            total_minutes %= 24 * 60
            hour, minute = divmod(total_minutes, 60)
            new_time = TimeState(day=day, hour=hour, minute=minute)

            self.data = nexus.tick(self.data, new_time, minutes)
            return self.data


game_state = GameState()
