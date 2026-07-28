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
    "scribe": AgentProfile(
        id="scribe",
        name="Scribe",
        occupation="Company Historian",
        personality="Meticulous. Quiet. Writes everything down.",
        home_location="brain-room",
        tint=0xD98FB3,
    ),
    "coach": AgentProfile(
        id="coach",
        name="Coach",
        occupation="Performance & Improvement",
        personality="Encouraging but exacting. Asks more questions than it answers.",
        home_location="performance-center",
        tint=0xFF8C61,
    ),
    "sentinel": AgentProfile(
        id="sentinel",
        name="Sentinel",
        occupation="Risk Management",
        personality="Unflinching. Says no more often than yes, and never apologizes for it.",
        home_location="trading-floor",
        tint=0xFF5C5C,
    ),
    "pulse": AgentProfile(
        id="pulse",
        name="Pulse",
        occupation="Market Scanner",
        personality="Restless. Always watching every ticker at once.",
        home_location="trading-floor",
        tint=0x5CE1FF,
    ),
    "guardian": AgentProfile(
        id="guardian",
        name="Guardian",
        occupation="Portfolio Protection",
        personality="Steady and watchful. Speaks up the moment exposure looks lopsided.",
        home_location="trading-floor",
        tint=0x4A90D9,
    ),
    "cio": AgentProfile(
        id="cio",
        name="Meridian",
        occupation="Chief Investment Officer",
        personality="Calm, professional, and educational. Reviews every department's work rather than trading itself.",
        home_location="executive-boardroom",
        tint=0xD4AF37,
    ),
    "sage": AgentProfile(
        id="sage",
        name="Sage",
        occupation="Socratic Mentor",
        personality="Calm and unhurried. Answers every question with a better one. Never tells anyone what to think.",
        home_location="brain-room",
        tint=0x9B7FD4,
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
    "simulation-lab": "SimulationLabScene",
    "hall-of-fame": "HallOfFameScene",
    "performance-center": "PerformanceCenterScene",
    "trading-floor": "TradingFloorScene",
    "executive-boardroom": "ExecutiveBoardroomScene",
}
