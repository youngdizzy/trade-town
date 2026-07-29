import Phaser from "phaser";
import type {
  AcademyProject,
  AcademyState,
  AgentEnergy,
  AgentId,
  AgentKnowledgeState,
  AgentState,
  BacktestSession,
  BlackBoxState,
  CalendarState,
  CeoDecisionRecord,
  CaseStudy,
  ChallengeReport,
  CoachReport,
  CompanyDNA,
  CompanyHealth,
  CompanyScore,
  Debate,
  DialogueHistoryEntry,
  DisciplineReview,
  ExecutiveReview,
  FounderState,
  GameSaveState,
  GatekeeperRejection,
  HallOfFameEntry,
  InnovationState,
  MarketEnvironmentState,
  MeetingMinutes,
  MeetingState,
  MemoryRecord,
  MentorState,
  NewsItem,
  PaperPortfolio,
  PerformanceSnapshot,
  QuestionOfTheDay,
  ResearchItem,
  TreasuryState,
  RiskLimits,
  EducationProgress,
  PlayerVsAiState,
  ReasoningChallenge,
  ReasoningLabState,
  ReflectionSession,
  RiskWarning,
  ScannerAlert,
  SceneId,
  SettingsState,
  SignalCalibrationState,
  SimulationResult,
  Strategy,
  StrategyReport,
  StrategyReview,
  TalentState,
  Task,
  ThinkingProfile,
  TimeState,
  TradeDecision,
  TradeProposal,
  WatchlistEntry,
  WisdomState,
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
  // v0.7 — Input Priority fix: "Press E to Talk" prompt. Emitted every
  // frame RoomScene.update() has a real nearestAgent() result and no
  // dialogue currently open; null the instant neither is true. See
  // InteractionPrompt.tsx.
  "interaction:available": { agentName: string } | null;
  "time:tick": TimeState;
  "settings:changed": SettingsState;
  "save:started": undefined;
  "save:completed": { at: string };
  "save:failed": { error: string };
  "load:completed": GameSaveState;
  "ui:pause": { paused: boolean };
  "ui:settings": { open: boolean };
  "ui:newspaper": { open: boolean };
  // v0.7 — Input Priority fix. Two independent overlay-driven signals,
  // split from one (see gameStore.ts's setOverlay()): "world:overlayOpen"
  // now only reflects the movement-blocking subset of overlays (excludes
  // the Command Center, whose backdrop isn't fully opaque), while
  // "world:interactionBlocked" reflects the full set, preserving the
  // original single-flag behavior for E-key interaction/agent updates/
  // door triggers. See GameManager.ts's worldActive vs movementActive.
  "world:overlayOpen": { open: boolean };
  "world:interactionBlocked": { blocked: boolean };
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
  "strategyReports:updated": StrategyReport[];
  "strategyReviews:updated": StrategyReview[];
  "hallOfFame:updated": HallOfFameEntry[];
  "hallOfFame:entryAdded": HallOfFameEntry;
  "coach:reportReceived": CoachReport;
  "coachReports:updated": CoachReport[];
  "companyScore:updated": CompanyScore;
  "performanceSnapshots:updated": PerformanceSnapshot[];
  "ui:coachDashboard": { open: boolean };
  "ui:brainRoomHud": { open: boolean };
  "ui:commandCenter": { open: boolean; mode?: "quick" | "full" };
  "ui:campusMap": { open: boolean };
  "ui:breakthrough": { open: boolean };
  "riskLimits:updated": RiskLimits;
  "riskWarnings:updated": RiskWarning[];
  "scannerAlerts:updated": ScannerAlert[];
  "scanner:alertDetected": ScannerAlert;
  "decisions:updated": TradeDecision[];
  "decision:made": TradeDecision;
  "agentEnergy:updated": AgentEnergy;
  "signalCalibration:updated": SignalCalibrationState;
  "playerVsAi:updated": PlayerVsAiState;
  "education:updated": EducationProgress;
  "tradeNotifications:updated": string[];
  "tradeProposals:updated": TradeProposal[];
  "tradeProposal:new": TradeProposal;
  "ceoDecisions:updated": CeoDecisionRecord[];
  "debates:updated": Debate[];
  "challengeReports:updated": ChallengeReport[];
  "innovationState:updated": Record<AgentId, InnovationState>;
  "gatekeeperRejections:updated": GatekeeperRejection[];
  "marketEnvironment:updated": MarketEnvironmentState;
  "companyHealth:updated": CompanyHealth;
  "companyDna:updated": CompanyDNA;
  "executiveReviews:updated": ExecutiveReview[];
  "academyProjects:updated": AcademyProject[];
  "academyCompletedProjects:updated": AcademyProject[];
  "agentKnowledge:updated": Record<AgentId, AgentKnowledgeState>;
  "academyState:updated": AcademyState;
  "disciplineReviews:updated": DisciplineReview[];
  "caseStudies:updated": CaseStudy[];
  "talent:updated": TalentState;
  "reasoningChallenges:updated": ReasoningChallenge[];
  "reasoningLabState:updated": ReasoningLabState;
  "reflectionSessions:updated": ReflectionSession[];
  "wisdomState:updated": WisdomState;
  "questionArchive:updated": QuestionOfTheDay[];
  "thinkingProfiles:updated": Record<AgentId, ThinkingProfile>;
  "mentorState:updated": MentorState;
  "founderState:updated": FounderState;
  "treasury:updated": TreasuryState;
  "calendar:updated": CalendarState;
  "blackBox:updated": BlackBoxState;
  "ui:executiveVoting": { open: boolean; proposalId?: string };
  // v0.7 Feature 19 — opens the Command Center on the Decisions tab for a
  // specific trade's decision; openDetail additionally auto-opens
  // DecisionDetail's full Post-Trade Review. `nonce` forces a fresh
  // effect trigger even if the same decisionId is requested twice in a row.
  "trade:inspect": { decisionId: string; openDetail: boolean; nonce: number };
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
