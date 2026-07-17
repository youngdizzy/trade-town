"""Static agent roster — the things about each agent that never change at
runtime (name, occupation, personality blurb, home office, sprite tint).
Dynamic per-agent state (mood, task, location, ...) lives in AgentState
(schemas.py) / GameState (state.py); this module is just their profile card.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.schemas import AGENT_IDS, AgentId, AgentLocation, SceneId


@dataclass(frozen=True)
class AgentProfile:
    id: AgentId
    name: str
    occupation: str
    personality: str
    home_location: AgentLocation
    tint: int  # hex color, matches the frontend AgentNPC sprite tint


AGENT_PROFILES: dict[AgentId, AgentProfile] = {
    "scout": AgentProfile(
        id="scout",
        name="Scout",
        occupation="Market Scanner",
        personality="Curious. Always exploring.",
        home_location="scout-office",
        tint=0xBFE3FF,
    ),
    "atlas": AgentProfile(
        id="atlas",
        name="Atlas",
        occupation="Strategy Lead",
        personality="Calm. Strategic. Rarely speaks. Makes decisions.",
        home_location="meeting-room",
        tint=0xFFD166,
    ),
    "echo": AgentProfile(
        id="echo",
        name="Echo",
        occupation="Technical Analyst",
        personality="Loves charts. Frequently studies monitors.",
        home_location="brain-room",
        tint=0xB388FF,
    ),
    "nova": AgentProfile(
        id="nova",
        name="Nova",
        occupation="Research Analyst",
        personality="Reads books. Studies reports.",
        home_location="brain-room",
        tint=0x8FE3B0,
    ),
}


def all_agent_ids() -> tuple[AgentId, ...]:
    return AGENT_IDS


LOCATION_TO_SCENE: dict[AgentLocation, SceneId] = {
    "scout-office": "ScoutOfficeScene",
    "brain-room": "BrainRoomScene",
    "meeting-room": "MeetingRoomScene",
    "break-room": "BreakRoomScene",
    "lobby": "LobbyScene",
}
