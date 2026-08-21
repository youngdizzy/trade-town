import Phaser from "phaser";
import type {
  AcademyProject,
  AcademyState,
  Account,
  AgentEnergy,
  AgentId,
  AgentKnowledgeState,
  AgentPerformanceReview,
  AgentSkillProfile,
  PredictionRecord,
  FailureClassification,
  AgentState,
  BacktestSession,
  BlackBoxState,
  BlackSwanEventRecord,
  BlackSwanIntelligenceState,
  BlackSwanReport,
  CalendarState,
  CeoDecisionRecord,
  CaseStudy,
  InstitutionalMemoryEntry,
  ChallengeReport,
  CoachReport,
  CompanyDNA,
  CompanyHealth,
  CompanyHealthDelta,
  CompanyScore,
  ConstitutionState,
  DailyObjectiveStatus,
  Debate,
  DecisionVaultEntry,
  DefensiveModeState,
  DepartmentSelfEvaluation,
  DialogueHistoryEntry,
  DisciplineReview,
  EconomicIntelligenceReport,
  BoardReport,
  EconomicIntelligenceState,
  EmergencyStopState,
  ExecutiveMeetingLogEntry,
  ExecutiveReview,
  FounderState,
  Goal,
  StrategicReview,
  FoundationalMentorState,
  GameSaveState,
  GatekeeperRejection,
  HallOfFameEntry,
  InnovationState,
  InstitutionalSurvivalScore,
  LearningEvent,
  MarketEnvironmentState,
  MarketIntelligenceLearningEntry,
  MarketIntelligenceReport,
  MarketIntelligenceState,
  MeetingMinutes,
  MeetingState,
  MemoryRecord,
  MentorState,
  NewsItem,
  OpportunityRejection,
  PaperPortfolio,
  PerformanceSnapshot,
  PortfolioIntelligence,
  QuestionOfTheDay,
  ResearchItem,
  TreasuryState,
  RiskBudgetStatus,
  RiskLimits,
  EducationProgress,
  ModelValidationReport,
  PlayerVsAiState,
  ReasoningChallenge,
  ReasoningLabState,
  ReflectionSession,
  RiskWarning,
  RunSummary,
  ScannerAlert,
  SceneId,
  SettingsState,
  SignalCalibrationState,
  SimulationResult,
  Strategy,
  StrategyExecutiveReview,
  StrategyFounderApproval,
  StrategyHallOfFameEntry,
  StrategyHealthAssessment,
  StrategyLiquidityValidation,
  StrategyMonteCarloResult,
  StrategyRegimeTestReport,
  StrategyReport,
  StrategyReview,
  FailedStrategyArchiveEntry,
  TalentState,
  Task,
  ThinkingProfile,
  TimeState,
  TradeDecision,
  TradeProposal,
  TradingModeState,
  BehavioralCircuitBreakerRead,
  DailyCircuitBreakerRead,
  LosingStreakRead,
  RecoveryBriefing,
  SelfImprovementProposal,
  InstitutionalEvolutionReport,
  VisionBoardState,
  TravelModeState,
  TravelModeBriefing,
  WarRoomSession,
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
  // Design Bible Chapter 67 (TTOS) Part 3 — the Executive Alert Center.
  "ui:alertCenter": { open: boolean };
  "portfolio:updated": PaperPortfolio;
  "strategies:updated": Strategy[];
  "simulation:updated": { sessions: BacktestSession[]; results: SimulationResult[] };
  "simulation:completed": SimulationResult;
  "strategyReports:updated": StrategyReport[];
  "strategyReviews:updated": StrategyReview[];
  // v0.7 Quantitative Research & Intelligence System, Piece 4 —
  // Meridian/CIO's independent, advisory-only ModelValidationReport.
  "strategyModelValidations:updated": ModelValidationReport[];
  // v0.7 Feature 52 (Part 1/2) — the Strategy Validation Laboratory.
  "strategyMonteCarloResults:updated": StrategyMonteCarloResult[];
  "strategyRegimeTests:updated": StrategyRegimeTestReport[];
  "strategyLiquidityValidations:updated": StrategyLiquidityValidation[];
  "strategyExecutiveReviews:updated": StrategyExecutiveReview[];
  "strategyFounderApprovals:updated": StrategyFounderApproval[];
  "strategyHealthAssessments:updated": StrategyHealthAssessment[];
  "strategyHallOfFame:updated": StrategyHallOfFameEntry[];
  "strategyHallOfFame:entryAdded": StrategyHallOfFameEntry;
  "strategyFailedArchive:updated": FailedStrategyArchiveEntry[];
  "strategyFailedArchive:entryAdded": FailedStrategyArchiveEntry;
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
  // Design Bible Chapter 73.5 — a real, touch-accessible way to open the
  // Command Palette that doesn't depend on the Cmd+K/Ctrl+K shortcut
  // (BottomToolbar's Search button emits this).
  "ui:commandPalette": { open: boolean };
  "ui:breakthrough": { open: boolean };
  "ui:emergencyStopConfirm": { pending: "activate" | "resume" | null };
  // CEO directive "Proper Multi-Run / Save Isolation System" — "New Game"
  // now really does create a separate, independently-persisted run (see
  // POST /api/runs), so this confirms the player actually wants to leave
  // whichever run is currently active rather than warning about a reset
  // that no longer (and never actually did) happen. MainMenuScene emits
  // this with the currently-active run's real day before creating a new
  // one; null closes the dialog without a result (e.g. component
  // unmount). NewGameConfirm.tsx owns rendering; MainMenuScene listens
  // once for "ui:newGameConfirmResult" to learn what the player chose.
  "ui:newGameConfirm": { day: number } | null;
  "ui:newGameConfirmResult": { confirmed: boolean };
  // "Continue" with more than one real, persisted run shows a picker
  // instead of silently loading one — RunPicker.tsx owns rendering;
  // MainMenuScene listens once for "ui:runPickerResult" ({ runId: null }
  // means the player closed the picker without choosing).
  "ui:runPicker": { runs: RunSummary[] } | null;
  "ui:runPickerResult": { runId: string | null };
  // Design Bible Chapter 67 (TTOS) Part 3 — the Quick Action Dock's
  // quick-jump buttons. `tab` is a bare string (not FullCommandCenter's
  // own `Tab` union) to avoid a circular import — FullCommandCenter
  // already imports EventBus, so EventBus can't import a type back from
  // it. FullCommandCenter validates the string against its real TABS
  // list before acting on it.
  "ui:commandCenterJump": { tab: string };
  "riskLimits:updated": RiskLimits;
  "riskWarnings:updated": RiskWarning[];
  "emergencyStop:updated": EmergencyStopState;
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
  "opportunityRejections:updated": OpportunityRejection[];
  "marketEnvironment:updated": MarketEnvironmentState;
  "marketIntelligence:updated": MarketIntelligenceState;
  "marketIntelligenceReports:updated": MarketIntelligenceReport[];
  "marketIntelligenceLearning:updated": MarketIntelligenceLearningEntry[];
  "companyHealth:updated": CompanyHealth;
  "companyHealthDelta:updated": CompanyHealthDelta | null;
  "companyDna:updated": CompanyDNA;
  "dailyObjectiveStatus:updated": DailyObjectiveStatus;
  "riskBudgetStatus:updated": RiskBudgetStatus;
  "executiveReviews:updated": ExecutiveReview[];
  "boardReports:updated": BoardReport[];
  "academyProjects:updated": AcademyProject[];
  "academyCompletedProjects:updated": AcademyProject[];
  "goals:updated": Goal[];
  "strategicReviews:updated": StrategicReview[];
  "agentKnowledge:updated": Record<AgentId, AgentKnowledgeState>;
  "academyState:updated": AcademyState;
  "disciplineReviews:updated": DisciplineReview[];
  "caseStudies:updated": CaseStudy[];
  "institutionalMemory:updated": InstitutionalMemoryEntry[];
  "agentPerformanceReviews:updated": AgentPerformanceReview[];
  "agentSkillProfiles:updated": AgentSkillProfile[];
  "predictionRecords:updated": PredictionRecord[];
  "failureClassifications:updated": FailureClassification[];
  "learningEvents:updated": LearningEvent[];
  "decisionVault:updated": DecisionVaultEntry[];
  "warRoomSessions:updated": WarRoomSession[];
  "portfolioIntelligence:updated": PortfolioIntelligence;
  "economicIntelligence:updated": EconomicIntelligenceState;
  "economicIntelligenceReports:updated": EconomicIntelligenceReport[];
  "blackSwanIntelligence:updated": BlackSwanIntelligenceState;
  "blackSwanReports:updated": BlackSwanReport[];
  "defensiveMode:updated": DefensiveModeState;
  "blackSwanEvents:updated": BlackSwanEventRecord[];
  "institutionalSurvivalScore:updated": InstitutionalSurvivalScore;
  "tradingModes:updated": TradingModeState;
  "dailyCircuitBreaker:updated": DailyCircuitBreakerRead;
  "losingStreak:updated": LosingStreakRead;
  "behavioralCircuitBreaker:updated": BehavioralCircuitBreakerRead;
  "recoveryBriefings:updated": RecoveryBriefing[];
  "selfImprovementProposals:updated": SelfImprovementProposal[];
  "evolutionReports:updated": InstitutionalEvolutionReport[];
  "visionBoard:updated": VisionBoardState;
  "travelMode:updated": TravelModeState;
  "travelModeBriefings:updated": TravelModeBriefing[];
  "talent:updated": TalentState;
  "constitution:updated": ConstitutionState;
  "reasoningChallenges:updated": ReasoningChallenge[];
  "reasoningLabState:updated": ReasoningLabState;
  "executiveMeetingLog:updated": ExecutiveMeetingLogEntry[];
  "departmentSelfEvaluations:updated": DepartmentSelfEvaluation[];
  "reflectionSessions:updated": ReflectionSession[];
  "wisdomState:updated": WisdomState;
  "questionArchive:updated": QuestionOfTheDay[];
  "thinkingProfiles:updated": Record<AgentId, ThinkingProfile>;
  "mentorState:updated": MentorState;
  "foundationalMentorState:updated": FoundationalMentorState;
  "founderState:updated": FounderState;
  "treasury:updated": TreasuryState;
  // Design Bible Chapter 69 Part 1 — Multi-Account & Fund Management
  // System.
  "accounts:updated": Account[];
  "activeAccount:updated": string | null;
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
