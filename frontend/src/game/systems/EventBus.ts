import Phaser from "phaser";
import type {
  AgentId,
  AgentState,
  BacktestSession,
  CoachReport,
  CompanyScore,
  DialogueHistoryEntry,
  GameSaveState,
  HallOfFameEntry,
  MeetingMinutes,
  MeetingState,
  MemoryRecord,
  NewsItem,
  PaperPortfolio,
  PerformanceSnapshot,
  ResearchItem,
  RiskLimits,
  RiskWarning,
  ScannerAlert,
  SceneId,
  SettingsState,
  SimulationResult,
  Strategy,
  Task,
  TimeState,
  TradeDecision,
  WatchlistEntry,
} from "@/types";

/** Every event the game emits, keyed by name, with its payload type. */
export interface GameEvents {
  "scene:ready": { scene: string };
  "scene:transition": { to: string };
  "player:move": { x: number; y: number };
  "room:entered": { scene: SceneId };
  "room:left": { scene: SceneId };
  "agent:updated": { id: AgentId; state: AgentState };
  "agent:interact": { id: AgentId; transform: AgentState["transform"] };
  "dialogue:open": { lines: string[]; speaker: string };
  "dialogue:line": DialogueHistoryEntry;
  "dialogue:close": undefined;
  "time:tick": TimeState;
  "settings:changed": SettingsState;
  "save:started": undefined;
  "save:completed": { at: string };
  "save:failed": { error: string };
  "load:completed": GameSaveState;
  "ui:pause": { paused: boolean };
  "ui:settings": { open: boolean };
  "ui:newspaper": { open: boolean };
  "world:overlayOpen": { open: boolean };
  "net:status": { connected: boolean };
  "task:assigned": Task;
  "task:completed": Task;
  "whiteboard:updated": { boardId: string; text: string };
  "meeting:started": MeetingState;
  "meeting:ended": undefined;
  "meeting:minutesRecorded": MeetingMinutes;
  "news:updated": NewsItem[];
  "research:updated": ResearchItem[];
  "research:completed": ResearchItem;
  "watchlist:updated": WatchlistEntry[];
  "memory:updated": MemoryRecord[];
  "ui:companyMemory": { open: boolean };
  "portfolio:updated": PaperPortfolio;
  "strategies:updated": Strategy[];
  "simulation:updated": { sessions: BacktestSession[]; results: SimulationResult[] };
  "simulation:completed": SimulationResult;
  "hallOfFame:updated": HallOfFameEntry[];
  "hallOfFame:entryAdded": HallOfFameEntry;
  "coach:reportReceived": CoachReport;
  "coachReports:updated": CoachReport[];
  "companyScore:updated": CompanyScore;
  "performanceSnapshots:updated": PerformanceSnapshot[];
  "ui:coachDashboard": { open: boolean };
  "ui:brainRoomHud": { open: boolean };
  "ui:commandCenter": { open: boolean; mode?: "quick" | "full" };
  "riskLimits:updated": RiskLimits;
  "riskWarnings:updated": RiskWarning[];
  "scannerAlerts:updated": ScannerAlert[];
  "scanner:alertDetected": ScannerAlert;
  "decisions:updated": TradeDecision[];
  "decision:made": TradeDecision;
}

type Handler<K extends keyof GameEvents> = (payload: GameEvents[K]) => void;

/**
 * Central pub/sub bus decoupling Phaser scenes, React UI, and the network
 * layer. Built on Phaser's EventEmitter since Phaser is already a
 * dependency; used as a plain singleton so React code doesn't need to know
 * about the Phaser.Game instance to listen for game events.
 */
class TypedEventBus {
  private emitter = new Phaser.Events.EventEmitter();

  on<K extends keyof GameEvents>(event: K, handler: Handler<K>): () => void {
    this.emitter.on(event, handler as (...args: unknown[]) => void);
    return () => this.emitter.off(event, handler as (...args: unknown[]) => void);
  }

  once<K extends keyof GameEvents>(event: K, handler: Handler<K>): void {
    this.emitter.once(event, handler as (...args: unknown[]) => void);
  }

  off<K extends keyof GameEvents>(event: K, handler: Handler<K>): void {
    this.emitter.off(event, handler as (...args: unknown[]) => void);
  }

  emit<K extends keyof GameEvents>(event: K, payload: GameEvents[K]): void {
    this.emitter.emit(event, payload);
  }

  removeAllListeners(): void {
    this.emitter.removeAllListeners();
  }
}

export const EventBus = new TypedEventBus();
