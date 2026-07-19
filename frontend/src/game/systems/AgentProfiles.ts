import type { AgentId, AgentLocation, SceneId } from "@/types";

export interface AgentProfile {
  id: AgentId;
  name: string;
  occupation: string;
  personality: string;
  homeLocation: AgentLocation;
  tint: number;
  /** Manifest asset id for this agent's sprite sheet — a palette-swapped
   *  variant of characters/player/player.png (see animation-config.json's
   *  "_comment_agent_variants") with hair/shirt/pants recolored to match
   *  this agent's identity. Not the player's own sheet; PlayerController
   *  still uses characters/player/player directly. */
  spriteId: string;
  /** Small always-visible glyph rendered above the NPC's head — lets you
   *  tell agents apart at a glance in rooms where several cluster together
   *  (Brain Room, Meeting Room), without waiting for the proximity-gated
   *  name tag. Frontend-only, no backend equivalent. */
  badge: string;
  /** Max wander distance (px) from home spawn, and the chance (0-1) of
   *  pausing instead of picking a new wander target — both drawn from the
   *  agent's personality blurb so idle movement itself reads as
   *  distinct per agent, not just color. See AgentNPC.pickNewTarget(). */
  wanderRadius: number;
  idlePauseChance: number;
}

/** Static roster — mirrors backend/app/agents.py. Keep tints/homes in sync
 *  (badge/wanderRadius/idlePauseChance are cosmetic/frontend-only). */
export const AGENT_PROFILES: Record<AgentId, AgentProfile> = {
  scout: {
    id: "scout",
    name: "Scout",
    occupation: "Market Scanner",
    personality: "Curious. Always exploring.",
    homeLocation: "scout-office",
    tint: 0xbfe3ff,
    spriteId: "characters/player/player-scout",
    badge: "\u{1F50D}",
    wanderRadius: 60,
    idlePauseChance: 0.15,
  },
  atlas: {
    id: "atlas",
    name: "Atlas",
    occupation: "Strategy Lead",
    personality: "Calm. Strategic. Rarely speaks. Makes decisions.",
    homeLocation: "meeting-room",
    tint: 0xffd166,
    spriteId: "characters/player/player-atlas",
    badge: "♟",
    wanderRadius: 18,
    idlePauseChance: 0.7,
  },
  echo: {
    id: "echo",
    name: "Echo",
    occupation: "Technical Analyst",
    personality: "Loves charts. Frequently studies monitors.",
    homeLocation: "brain-room",
    tint: 0xb388ff,
    spriteId: "characters/player/player-echo",
    badge: "\u{1F4C8}",
    wanderRadius: 30,
    idlePauseChance: 0.5,
  },
  nova: {
    id: "nova",
    name: "Nova",
    occupation: "Research Analyst",
    personality: "Reads books. Studies reports.",
    homeLocation: "brain-room",
    tint: 0x8fe3b0,
    spriteId: "characters/player/player-nova",
    badge: "\u{1F4DA}",
    wanderRadius: 25,
    idlePauseChance: 0.55,
  },
  scribe: {
    id: "scribe",
    name: "Scribe",
    occupation: "Company Historian",
    personality: "Meticulous. Quiet. Writes everything down.",
    homeLocation: "brain-room",
    tint: 0xd98fb3,
    spriteId: "characters/player/player-scribe",
    badge: "\u{1F4DC}",
    wanderRadius: 15,
    idlePauseChance: 0.75,
  },
  coach: {
    id: "coach",
    name: "Coach",
    occupation: "Performance & Improvement",
    personality: "Encouraging but exacting. Asks more questions than it answers.",
    homeLocation: "performance-center",
    tint: 0xff8c61,
    spriteId: "characters/player/player-coach",
    badge: "\u{1F3C6}",
    wanderRadius: 22,
    idlePauseChance: 0.4,
  },
  sentinel: {
    id: "sentinel",
    name: "Sentinel",
    occupation: "Risk Management",
    personality: "Unflinching. Says no more often than yes, and never apologizes for it.",
    homeLocation: "trading-floor",
    tint: 0xff5c5c,
    spriteId: "characters/player/player-sentinel",
    badge: "\u{1F6E1}",
    wanderRadius: 20,
    idlePauseChance: 0.6,
  },
  pulse: {
    id: "pulse",
    name: "Pulse",
    occupation: "Market Scanner",
    personality: "Restless. Always watching every ticker at once.",
    homeLocation: "trading-floor",
    tint: 0x5ce1ff,
    spriteId: "characters/player/player-pulse",
    badge: "\u{1F4E1}",
    wanderRadius: 45,
    idlePauseChance: 0.1,
  },
  guardian: {
    id: "guardian",
    name: "Guardian",
    occupation: "Portfolio Protection",
    personality: "Steady and watchful. Speaks up the moment exposure looks lopsided.",
    homeLocation: "trading-floor",
    tint: 0x4a90d9,
    spriteId: "characters/player/player-guardian",
    badge: "\u{1F6E1}\u{FE0F}",
    wanderRadius: 25,
    idlePauseChance: 0.5,
  },
};

export const LOCATION_TO_SCENE: Record<AgentLocation, SceneId> = {
  "scout-office": "ScoutOfficeScene",
  "brain-room": "BrainRoomScene",
  "meeting-room": "MeetingRoomScene",
  "break-room": "BreakRoomScene",
  lobby: "LobbyScene",
  "simulation-lab": "SimulationLabScene",
  "hall-of-fame": "HallOfFameScene",
  "performance-center": "PerformanceCenterScene",
  "trading-floor": "TradingFloorScene",
};
