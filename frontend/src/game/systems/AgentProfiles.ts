import type { AgentId, AgentLocation, SceneId } from "@/types";

export interface AgentProfile {
  id: AgentId;
  name: string;
  occupation: string;
  personality: string;
  homeLocation: AgentLocation;
  tint: number;
}

/** Static roster — mirrors backend/app/agents.py. Keep tints/homes in sync. */
export const AGENT_PROFILES: Record<AgentId, AgentProfile> = {
  scout: {
    id: "scout",
    name: "Scout",
    occupation: "Market Scanner",
    personality: "Curious. Always exploring.",
    homeLocation: "scout-office",
    tint: 0xbfe3ff,
  },
  atlas: {
    id: "atlas",
    name: "Atlas",
    occupation: "Strategy Lead",
    personality: "Calm. Strategic. Rarely speaks. Makes decisions.",
    homeLocation: "meeting-room",
    tint: 0xffd166,
  },
  echo: {
    id: "echo",
    name: "Echo",
    occupation: "Technical Analyst",
    personality: "Loves charts. Frequently studies monitors.",
    homeLocation: "brain-room",
    tint: 0xb388ff,
  },
  nova: {
    id: "nova",
    name: "Nova",
    occupation: "Research Analyst",
    personality: "Reads books. Studies reports.",
    homeLocation: "brain-room",
    tint: 0x8fe3b0,
  },
};

export const LOCATION_TO_SCENE: Record<AgentLocation, SceneId> = {
  "scout-office": "ScoutOfficeScene",
  "brain-room": "BrainRoomScene",
  "meeting-room": "MeetingRoomScene",
  "break-room": "BreakRoomScene",
  lobby: "LobbyScene",
};
