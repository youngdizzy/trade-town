import type { ScoutState, SettingsState, TimeState } from "@/types";
import { EventBus } from "@/game/systems/EventBus";

export interface DialogueUiState {
  open: boolean;
  speaker: string;
  lines: string[];
  index: number;
}

export interface SaveUiState {
  status: "idle" | "saving" | "saved" | "error";
  lastSavedAt: string | null;
  error: string | null;
}

export interface GameUiState {
  time: TimeState;
  scout: ScoutState | null;
  settings: SettingsState;
  dialogue: DialogueUiState;
  paused: boolean;
  settingsOpen: boolean;
  netConnected: boolean;
  save: SaveUiState;
  currentScene: string;
}

type Listener = () => void;

/**
 * Minimal external store (React 18 useSyncExternalStore pattern) that
 * mirrors EventBus game events into a plain object the React UI can read
 * reactively, without pulling in a state-management dependency for what is
 * fundamentally just "subscribe to a few events."
 */
class GameStore {
  private state: GameUiState = {
    time: { day: 1, hour: 8, minute: 0 },
    scout: null,
    settings: { musicVolume: 0.5, sfxVolume: 0.7, autosaveIntervalSec: 60, showFps: false },
    dialogue: { open: false, speaker: "", lines: [], index: 0 },
    paused: false,
    settingsOpen: false,
    netConnected: false,
    save: { status: "idle", lastSavedAt: null, error: null },
    currentScene: "MainMenuScene",
  };

  private listeners = new Set<Listener>();

  constructor() {
    EventBus.on("time:tick", (time) => this.set({ time }));
    EventBus.on("scout:updated", (scout) => this.set({ scout }));
    EventBus.on("settings:changed", (settings) => this.set({ settings }));
    EventBus.on("ui:pause", ({ paused }) => this.set({ paused }));
    EventBus.on("ui:settings", ({ open }) => this.set({ settingsOpen: open }));
    EventBus.on("net:status", ({ connected }) => this.set({ netConnected: connected }));
    EventBus.on("scene:ready", ({ scene }) => this.set({ currentScene: scene }));

    EventBus.on("dialogue:open", ({ lines, speaker }) => this.set({ dialogue: { open: true, speaker, lines, index: 0 } }));
    EventBus.on("dialogue:close", () => this.set({ dialogue: { open: false, speaker: "", lines: [], index: 0 } }));

    EventBus.on("save:started", () => this.set({ save: { status: "saving", lastSavedAt: this.state.save.lastSavedAt, error: null } }));
    EventBus.on("save:completed", ({ at }) => this.set({ save: { status: "saved", lastSavedAt: at, error: null } }));
    EventBus.on("save:failed", ({ error }) => this.set({ save: { status: "error", lastSavedAt: this.state.save.lastSavedAt, error } }));
  }

  private set(partial: Partial<GameUiState>): void {
    this.state = { ...this.state, ...partial };
    this.listeners.forEach((l) => l());
  }

  subscribe = (listener: Listener): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  getSnapshot = (): GameUiState => this.state;

  advanceDialogue(): void {
    const { dialogue } = this.state;
    if (!dialogue.open) return;
    const nextIndex = dialogue.index + 1;
    if (nextIndex >= dialogue.lines.length) {
      EventBus.emit("dialogue:close", undefined);
    } else {
      this.set({ dialogue: { ...dialogue, index: nextIndex } });
    }
  }
}

export const gameStore = new GameStore();
