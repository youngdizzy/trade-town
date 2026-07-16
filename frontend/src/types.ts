/** Shared domain types used across the game layer, UI layer, and network layer. */

export type Direction = "up" | "down" | "left" | "right";

export type SceneId =
  | "MainMenuScene"
  | "LobbyScene"
  | "ScoutOfficeScene"
  | "CeoOfficeScene"
  | "BrainRoomScene";

/** Locations Scout's schedule can place him in. Mirrors backend `ScoutLocation`. */
export type ScoutLocation = "scout-office" | "brain-room" | "lobby";

export interface Vector2 {
  x: number;
  y: number;
}

export interface EntityTransform extends Vector2 {
  scene: SceneId;
  facing: Direction;
}

export interface DialogueHistoryEntry {
  id: string;
  speaker: "scout" | "player";
  line: string;
  timestamp: string; // ISO string
}

export interface MemoryEntry {
  id: string;
  summary: string;
  day: number;
  hour: number;
}

export interface ScoutState {
  transform: EntityTransform;
  location: ScoutLocation;
  currentTask: string;
  mood: number; // 0-100
  energy: number; // 0-100
  memory: MemoryEntry[];
}

export interface TimeState {
  day: number;
  hour: number; // 0-23
  minute: number; // 0-59
}

export interface SettingsState {
  musicVolume: number; // 0-1
  sfxVolume: number; // 0-1
  autosaveIntervalSec: number;
  showFps: boolean;
}

export interface GameSaveState {
  version: "0.1";
  player: EntityTransform;
  scout: ScoutState;
  time: TimeState;
  settings: SettingsState;
  dialogueHistory: DialogueHistoryEntry[];
  updatedAt: string;
}

export function isDaytime(time: TimeState): boolean {
  return time.hour >= 6 && time.hour < 20;
}
