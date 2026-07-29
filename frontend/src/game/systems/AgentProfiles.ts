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
  cio: {
    id: "cio",
    name: "Meridian",
    occupation: "Chief Investment Officer",
    personality: "Calm, professional, and educational. Reviews every department's work rather than trading itself.",
    homeLocation: "executive-boardroom",
    tint: 0xd4af37,
    spriteId: "characters/player/player-meridian",
    badge: "\u{1F454}",
    wanderRadius: 16,
    idlePauseChance: 0.7,
  },
  sage: {
    id: "sage",
    name: "Sage",
    occupation: "Socratic Mentor",
    personality: "Calm and unhurried. Answers every question with a better one. Never tells anyone what to think.",
    homeLocation: "brain-room",
    tint: 0x9b7fd4,
    spriteId: "characters/player/player-sage",
    badge: "\u{1F9E0}",
    wanderRadius: 20,
    idlePauseChance: 0.75,
  },
  // v0.7 Feature 39 — the Original Founders. See backend/app/founders.py's
  // module docstring for why they never trade or earn Academy Knowledge.
  keystone: {
    id: "keystone",
    name: "Keystone",
    occupation: "Chief Risk Architect",
    personality: "Calm, patient, and immovable. Speaks rarely — when he does, the floor goes quiet.",
    homeLocation: "trading-floor",
    tint: 0x8c7a5c,
    spriteId: "characters/player/player-keystone",
    badge: "\u{1F3DB}\u{FE0F}",
    wanderRadius: 15,
    idlePauseChance: 0.8,
  },
  compass: {
    id: "compass",
    name: "Compass",
    occupation: "Chief Learning Architect",
    personality: "Endlessly curious. Treats every mistake as unfinished research.",
    homeLocation: "brain-room",
    tint: 0x3fbfa0,
    spriteId: "characters/player/player-compass",
    badge: "\u{1F9ED}",
    wanderRadius: 35,
    idlePauseChance: 0.3,
  },
  // v0.7 — the Chief Quantitative Strategist, leads every Black Box
  // Research Project (see backend/app/black_box.py). Works out of the
  // Simulation Lab — no new physical scene was built for a "Quant Lab".
  quant: {
    id: "quant",
    name: "Vector",
    occupation: "Chief Quantitative Strategist",
    personality: "Extremely analytical, patient, and precise. Trusts evidence over emotion — every claim has to survive being checked.",
    homeLocation: "simulation-lab",
    tint: 0x9aa5b1,
    spriteId: "characters/player/player-quant",
    badge: "\u{1F9EE}",
    wanderRadius: 18,
    idlePauseChance: 0.65,
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
  "executive-boardroom": "ExecutiveBoardroomScene",
};
