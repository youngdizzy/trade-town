"""Pydantic models mirroring frontend/src/types.ts. Field aliases keep the wire format camelCase to match the TypeScript client.

v0.2 generalizes the single hardcoded "Scout" into a roster of agents
(AgentId / AgentState) driven by a shared NEXUS orchestrator — see
docs/Architecture.md "NEXUS & multi-agent model" for the full design.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Direction = Literal["up", "down", "left", "right"]
SceneId = Literal[
    "MainMenuScene",
    "LobbyScene",
    "ScoutOfficeScene",
    "CeoOfficeScene",
    "BrainRoomScene",
    "MeetingRoomScene",
    "BreakRoomScene",
]

AgentId = Literal["scout", "atlas", "echo", "nova"]
AGENT_IDS: tuple[AgentId, ...] = ("scout", "atlas", "echo", "nova")

# Every room an agent's schedule (or a meeting/break override) can place them in.
AgentLocation = Literal["scout-office", "brain-room", "meeting-room", "break-room", "lobby"]

TaskStatus = Literal["pending", "working", "completed", "failed"]
TaskPriority = Literal["low", "normal", "high"]
NewsCategory = Literal["company", "discovery", "market"]


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


class AgentOverride(CamelModel):
    """A temporary location override that takes precedence over an agent's
    normal schedule — how meetings and break-room visits are implemented,
    without needing separate meeting/break state machines per agent."""

    location: AgentLocation
    reason: Literal["meeting", "break"]
    remaining_minutes: int = Field(alias="remainingMinutes")


class AgentState(CamelModel):
    transform: EntityTransform
    location: AgentLocation
    current_task: str = Field(alias="currentTask")
    mood: float
    energy: float
    memory: list[MemoryEntry] = Field(default_factory=list)
    override: AgentOverride | None = None


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
    speaker: AgentId | Literal["player"]
    line: str
    timestamp: str


class Task(CamelModel):
    id: str
    owner: AgentId
    priority: TaskPriority
    description: str
    status: TaskStatus
    created_at: str = Field(alias="createdAt")
    completed_at: str | None = Field(default=None, alias="completedAt")


class NewsItem(CamelModel):
    id: str
    headline: str
    category: NewsCategory
    timestamp: str


class MeetingState(CamelModel):
    active: bool = False
    participants: list[AgentId] = Field(default_factory=list)


class GameSaveState(CamelModel):
    version: Literal["0.2"] = "0.2"
    player: EntityTransform
    agents: dict[AgentId, AgentState]
    tasks: list[Task] = Field(default_factory=list)
    whiteboards: dict[str, str] = Field(default_factory=dict)
    meeting: MeetingState = Field(default_factory=MeetingState)
    news: list[NewsItem] = Field(default_factory=list)
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
