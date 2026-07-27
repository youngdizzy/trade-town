import type {
  AgentEnergy,
  AgentId,
  AgentState,
  BacktestSession,
  CoachReport,
  CompanyScore,
  HallOfFameEntry,
  MeetingMinutes,
  MeetingState,
  MemoryRecord,
  NewsItem,
  PaperPortfolio,
  PerformanceSnapshot,
  ResearchItem,
  RiskLimits,
  PlayerVsAiState,
  RiskWarning,
  ScannerAlert,
  SettingsState,
  SignalCalibrationState,
  SimulationResult,
  Strategy,
  Task,
  TimeState,
  TradeDecision,
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
  paperPortfolio: PaperPortfolio;
  strategies: Strategy[];
  backtestSessions: BacktestSession[];
  simulationResults: SimulationResult[];
  hallOfFame: HallOfFameEntry[];
  coachReports: CoachReport[];
  companyScore: CompanyScore;
  performanceSnapshots: PerformanceSnapshot[];
  riskLimits: RiskLimits;
  riskWarnings: RiskWarning[];
  scannerAlerts: ScannerAlert[];
  decisions: TradeDecision[];
  agentEnergy: AgentEnergy;
  signalCalibration: SignalCalibrationState;
  playerVsAi: PlayerVsAiState;
  settings: SettingsState;
  dialogue: DialogueUiState;
  paused: boolean;
  settingsOpen: boolean;
  newspaperOpen: boolean;
  companyMemoryOpen: boolean;
  coachDashboardOpen: boolean;
  brainRoomHudOpen: boolean;
  commandCenterOpen: boolean;
  commandCenterMode: "quick" | "full";
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
    paperPortfolio: {
      cashBalance: 100_000,
      startingBalance: 100_000,
      positions: [],
      orders: [],
      tradeHistory: [],
      totalPnl: 0,
      totalPnlPct: 0,
      winCount: 0,
      lossCount: 0,
    },
    strategies: [],
    backtestSessions: [],
    simulationResults: [],
    hallOfFame: [],
    coachReports: [],
    companyScore: {
      overall: 50,
      researchQuality: 50,
      decisionQuality: 50,
      riskManagement: 50,
      paperTradingPerformance: 50,
      teamCoordination: 50,
      knowledgeGrowth: 0,
      simulationSuccess: 50,
      updatedAt: new Date().toISOString(),
    },
    performanceSnapshots: [],
    riskLimits: {
      maxPositionPct: 10,
      maxDailyLossPct: 5,
      maxDrawdownPct: 20,
      maxOpenPositions: 8,
      maxSectorConcentrationPct: 30,
      riskPerTradePct: 2,
    },
    riskWarnings: [],
    scannerAlerts: [],
    decisions: [],
    agentEnergy: { current: 100, cap: 100, updatedAt: new Date().toISOString() },
    signalCalibration: { unlockedLevel: 1, attempts: [], correctCount: 0, totalCount: 0 },
    playerVsAi: { rounds: [], playerCorrectCount: 0, aiCorrectCount: 0, totalCount: 0 },
    settings: { musicVolume: 0.5, sfxVolume: 0.7, autosaveIntervalSec: 60, showFps: false },
    dialogue: { open: false, speaker: "", lines: [], index: 0 },
    paused: false,
    settingsOpen: false,
    newspaperOpen: false,
    companyMemoryOpen: false,
    coachDashboardOpen: false,
    brainRoomHudOpen: false,
    commandCenterOpen: false,
    commandCenterMode: "quick",
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
    // Newspaper, Company Memory, Coach Dashboard, and the Brain Room HUD
    // (openable from anywhere as a menu, not just while standing in Brain
    // Room — see BrainRoomHud.tsx) are all full-screen or panel
    // world-interaction overlays with independent open/close events and no
    // shared owner, so nothing previously stopped more than one being open
    // at once — closing whichever was on top (it renders last, so it's
    // visually on top; see App.tsx) would silently reveal another one
    // still open underneath. Opening any of them now closes the others,
    // and setOverlay also pauses the running scene for as long as any one
    // of them is open — without that, the player kept moving (invisibly,
    // since the overlay hides the world) behind a panel that only a mouse
    // click could close, which read as the game being stuck.
    const OVERLAY_KEYS = ["newspaperOpen", "companyMemoryOpen", "coachDashboardOpen", "brainRoomHudOpen", "commandCenterOpen"] as const;
    const setOverlay = (key: (typeof OVERLAY_KEYS)[number], open: boolean, extra?: Partial<GameUiState>): void => {
      const patch = Object.fromEntries(OVERLAY_KEYS.map((k) => [k, k === key ? open : open ? false : this.state[k]])) as Record<
        (typeof OVERLAY_KEYS)[number],
        boolean
      >;
      this.set({ ...patch, ...extra });
      const anyOpen = OVERLAY_KEYS.some((k) => this.state[k]);
      EventBus.emit("world:overlayOpen", { open: anyOpen });
    };
    EventBus.on("ui:newspaper", ({ open }) => setOverlay("newspaperOpen", open));
    EventBus.on("ui:companyMemory", ({ open }) => setOverlay("companyMemoryOpen", open));
    EventBus.on("ui:coachDashboard", ({ open }) => setOverlay("coachDashboardOpen", open));
    EventBus.on("ui:brainRoomHud", ({ open }) => setOverlay("brainRoomHudOpen", open));
    // Global Command Center (v0.6.1) — openable from anywhere via Tab or
    // the persistent corner button, in either "quick" (a fast-glance
    // status card) or "full" (tabbed terminal) mode. Mode is carried as
    // extra state alongside the same open/close + mutual-exclusion +
    // world-pause mechanism every other overlay already uses, rather than
    // a second event — expanding from Quick to Full re-fires this same
    // event with open:true again, just with a different mode.
    EventBus.on("ui:commandCenter", ({ open, mode }) =>
      setOverlay("commandCenterOpen", open, open ? { commandCenterMode: mode ?? this.state.commandCenterMode } : undefined),
    );
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
    EventBus.on("portfolio:updated", (paperPortfolio) => this.set({ paperPortfolio }));
    EventBus.on("strategies:updated", (strategies) => this.set({ strategies }));
    EventBus.on("simulation:updated", ({ sessions, results }) => this.set({ backtestSessions: sessions, simulationResults: results }));
    EventBus.on("hallOfFame:updated", (hallOfFame) => this.set({ hallOfFame }));
    EventBus.on("coachReports:updated", (coachReports) => this.set({ coachReports }));
    EventBus.on("companyScore:updated", (companyScore) => this.set({ companyScore }));
    EventBus.on("performanceSnapshots:updated", (performanceSnapshots) => this.set({ performanceSnapshots }));
    EventBus.on("riskLimits:updated", (riskLimits) => this.set({ riskLimits }));
    EventBus.on("riskWarnings:updated", (riskWarnings) => this.set({ riskWarnings }));
    EventBus.on("scannerAlerts:updated", (scannerAlerts) => this.set({ scannerAlerts }));
    EventBus.on("decisions:updated", (decisions) => this.set({ decisions }));
    EventBus.on("agentEnergy:updated", (agentEnergy) => this.set({ agentEnergy }));
    EventBus.on("signalCalibration:updated", (signalCalibration) => this.set({ signalCalibration }));
    EventBus.on("playerVsAi:updated", (playerVsAi) => this.set({ playerVsAi }));

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
