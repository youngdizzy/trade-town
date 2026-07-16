"""Pydantic models mirroring frontend/src/types.ts. Field aliases keep the wire format camelCase to match the TypeScript client."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Direction = Literal["up", "down", "left", "right"]
SceneId = Literal["MainMenuScene", "LobbyScene", "ScoutOfficeScene", "CeoOfficeScene", "BrainRoomScene"]
ScoutLocation = Literal["scout-office", "brain-room", "lobby"]


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class EntityTransform(CamelModel):
    scene: SceneId
    x: float
    y: float
    facing: Direction


class MemoryEntry(CamelModel):
    id: str
    summary: str
    day: int
    hour: int


class ScoutState(CamelModel):
    transform: EntityTransform
    location: ScoutLocation
    current_task: str = Field(alias="currentTask")
    mood: float
    energy: float
    memory: list[MemoryEntry] = Field(default_factory=list)


class TimeState(CamelModel):
    day: int
    hour: int
    minute: int


class SettingsState(CamelModel):
    music_volume: float = Field(alias="musicVolume")
    sfx_volume: float = Field(alias="sfxVolume")
    autosave_interval_sec: int = Field(alias="autosaveIntervalSec")
    show_fps: bool = Field(alias="showFps")


class DialogueHistoryEntry(CamelModel):
    id: str
    speaker: Literal["scout", "player"]
    line: str
    timestamp: str


class GameSaveState(CamelModel):
    version: Literal["0.1"] = "0.1"
    player: EntityTransform
    scout: ScoutState
    time: TimeState
    settings: SettingsState
    dialogue_history: list[DialogueHistoryEntry] = Field(default_factory=list, alias="dialogueHistory")
    updated_at: str = Field(alias="updatedAt")


class SaveResponse(BaseModel):
    ok: Literal[True] = True
    updated_at: str = Field(alias="updatedAt", serialization_alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
