import type { AgentId, AgentLocation, SceneId } from "@/types";
import { DOORS, HEIGHT_PX, WIDTH_PX } from "@/game/scenes/LobbyScene";
import { LOCATIONS_TO_AGENTS } from "@/game/systems/Schedule";

/**
 * v0.7 Feature 38 — the Company Campus Map. See CampusMap.tsx's own
 * module docstring for the full scope note on what's real here versus
 * the brief's fictional 17-building blueprint. Every building below is
 * a real door in the real LobbyScene (imported directly from `DOORS`,
 * never a second, hand-authored copy of those coordinates that could
 * drift from the real Lobby layout) plus the Lobby courtyard itself.
 */
export type CampusBuildingCategory = "research" | "trading" | "leadership" | "housing" | "entertainment" | "operations";

export interface CampusBuilding {
  sceneId: SceneId;
  /** The real AgentLocation agents report being at when here — null for
   * the two player-only rooms (CEO Office, Market Observatory) no
   * agent's real schedule ever routes them through. */
  location: AgentLocation | null;
  label: string;
  purpose: string;
  category: CampusBuildingCategory;
  x: number;
  y: number;
}

const PURPOSE: Record<SceneId, string> = {
  LobbyScene: "The town square — where idle agents rest and everyone passes through on their way elsewhere.",
  ScoutOfficeScene: "Scout's market-scanning desk — the company's first read on breaking news.",
  BrainRoomScene: "Mission Control — the live research queue, watchlist, and market clock.",
  CeoOfficeScene: "The CEO's own office.",
  MeetingRoomScene: "Where the team gathers for real, spontaneously-called meetings.",
  BreakRoomScene: "Off-hours home base — where agents wind down, relax, and sleep.",
  SimulationLabScene: "Strategy backtesting against seeded historical scenarios.",
  HallOfFameScene: "Celebrates the company's best real trades, streaks, and research.",
  ExecutiveBoardroomScene: "Meridian's monthly Executive Review of company performance.",
  TradingFloorScene: "Where paper trades are opened, managed, and closed.",
  PerformanceCenterScene: "Performance snapshots and Coach's reports across every real period.",
  MarketObservatoryScene: "Live candlestick charts and the company's tracked watchlist.",
  MainMenuScene: "",
};

const CATEGORY: Record<SceneId, CampusBuildingCategory> = {
  LobbyScene: "operations",
  ScoutOfficeScene: "research",
  BrainRoomScene: "research",
  CeoOfficeScene: "leadership",
  MeetingRoomScene: "leadership",
  BreakRoomScene: "housing",
  SimulationLabScene: "research",
  HallOfFameScene: "entertainment",
  ExecutiveBoardroomScene: "leadership",
  TradingFloorScene: "trading",
  PerformanceCenterScene: "operations",
  MarketObservatoryScene: "research",
  MainMenuScene: "operations",
};

const SCENE_TO_LOCATION: Partial<Record<SceneId, AgentLocation>> = {
  LobbyScene: "lobby",
  ScoutOfficeScene: "scout-office",
  BrainRoomScene: "brain-room",
  MeetingRoomScene: "meeting-room",
  BreakRoomScene: "break-room",
  SimulationLabScene: "simulation-lab",
  HallOfFameScene: "hall-of-fame",
  ExecutiveBoardroomScene: "executive-boardroom",
  TradingFloorScene: "trading-floor",
  PerformanceCenterScene: "performance-center",
};

// The Lobby courtyard itself isn't a door — its real position is the
// same default spawn point LobbyScene.ts's own create() falls back to
// (WIDTH_PX / 2, HEIGHT_PX - 4 tiles), not a hand-picked map coordinate.
const LOBBY_X = WIDTH_PX / 2;
const LOBBY_Y = HEIGHT_PX - 16 * 4;

export const CAMPUS_BUILDINGS: CampusBuilding[] = [
  { sceneId: "LobbyScene", location: "lobby", label: "Town Square", purpose: PURPOSE.LobbyScene, category: CATEGORY.LobbyScene, x: LOBBY_X, y: LOBBY_Y },
  ...DOORS.map((door) => ({
    sceneId: door.target,
    location: SCENE_TO_LOCATION[door.target] ?? null,
    label: door.label,
    purpose: PURPOSE[door.target],
    category: CATEGORY[door.target],
    x: door.x,
    y: door.y,
  })),
];

export const MAP_WIDTH_PX = WIDTH_PX;
export const MAP_HEIGHT_PX = HEIGHT_PX;

export function relatedDepartments(location: AgentLocation | null): AgentId[] {
  if (location === null) return [];
  return LOCATIONS_TO_AGENTS[location] ?? [];
}

export const CATEGORY_LABEL: Record<CampusBuildingCategory, string> = {
  research: "Research",
  trading: "Trading",
  leadership: "Leadership",
  housing: "Housing",
  entertainment: "Entertainment",
  operations: "Operations",
};
