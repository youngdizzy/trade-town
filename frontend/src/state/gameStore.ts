import type {
  AgentId,
  AgentState,
  MeetingMinutes,
  MeetingState,
  MemoryRecord,
  NewsItem,
  ResearchItem,
  SettingsState,
  Task,
  TimeState,
  WatchlistEntry,
} from "@/types";
import { EventBus } from "@/game/systems/EventBus";
import { NPCManager } from "@/game/systems/NPCManager";
import { NexusManager } from "@/game/systems/NexusManager";

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
  agents: Record<AgentId, AgentState> | null;
  tasks: Task[];
  whiteboards: Record<string, string>;
  meeting: MeetingState;
  news: NewsItem[];
  research: ResearchItem[];
  watchlist: WatchlistEntry[];
  memory: MemoryRecord[];
  meetingMinutes: MeetingMinutes[];
  settings: SettingsState;
  dialogue: DialogueUiState;
  paused: boolean;
  settingsOpen: boolean;
  newspaperOpen: boolean;
  companyMemoryOpen: boolean;
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
    agents: null,
    tasks: [],
    whiteboards: {},
    meeting: { active: false, participants: [], discussion: [] },
    news: [],
    research: [],
    watchlist: [],
    memory: [],
    meetingMinutes: [],
    settings: { musicVolume: 0.5, sfxVolume: 0.7, autosaveIntervalSec: 60, showFps: false },
    dialogue: { open: false, speaker: "", lines: [], index: 0 },
    paused: false,
    settingsOpen: false,
    newspaperOpen: false,
    companyMemoryOpen: false,
    netConnected: false,
    save: { status: "idle", lastSavedAt: null, error: null },
    currentScene: "MainMenuScene",
  };

  private listeners = new Set<Listener>();

  constructor() {
    EventBus.on("time:tick", (time) => this.set({ time }));
    EventBus.on("agent:updated", () => this.set({ agents: NPCManager.getAllAgents() }));
    EventBus.on("settings:changed", (settings) => this.set({ settings }));
    EventBus.on("ui:pause", ({ paused }) => this.set({ paused }));
    EventBus.on("ui:settings", ({ open }) => this.set({ settingsOpen: open }));
    // Newspaper and Company Memory are both full-screen world-interaction
    // overlays with independent open/close events and no shared owner, so
    // nothing previously stopped both being open at once — closing
    // whichever one was on top (it renders last, so it's visually on top;
    // see App.tsx) would silently reveal the other one still open
    // underneath. Opening either now closes the other.
    EventBus.on("ui:newspaper", ({ open }) => this.set({ newspaperOpen: open, companyMemoryOpen: open ? false : this.state.companyMemoryOpen }));
    EventBus.on("ui:companyMemory", ({ open }) => this.set({ companyMemoryOpen: open, newspaperOpen: open ? false : this.state.newspaperOpen }));
    EventBus.on("net:status", ({ connected }) => this.set({ netConnected: connected }));
    EventBus.on("scene:ready", ({ scene }) => this.set({ currentScene: scene }));

    EventBus.on("dialogue:open", ({ lines, speaker }) => this.set({ dialogue: { open: true, speaker, lines, index: 0 } }));
    EventBus.on("dialogue:close", () => this.set({ dialogue: { open: false, speaker: "", lines: [], index: 0 } }));

    EventBus.on("task:assigned", () => this.set({ tasks: NexusManager.getTasks() }));
    EventBus.on("task:completed", () => this.set({ tasks: NexusManager.getTasks() }));
    EventBus.on("whiteboard:updated", ({ boardId, text }) => this.set({ whiteboards: { ...this.state.whiteboards, [boardId]: text } }));
    EventBus.on("meeting:started", (meeting) => this.set({ meeting }));
    EventBus.on("meeting:ended", () => this.set({ meeting: { active: false, participants: [], discussion: [] } }));
    EventBus.on("meeting:minutesRecorded", () => this.set({ meetingMinutes: NexusManager.getMeetingMinutes() }));
    EventBus.on("news:updated", (news) => this.set({ news }));
    EventBus.on("research:updated", (research) => this.set({ research }));
    EventBus.on("watchlist:updated", (watchlist) => this.set({ watchlist }));
    EventBus.on("memory:updated", (memory) => this.set({ memory }));

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
