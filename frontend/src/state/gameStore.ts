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
  AlertEntry,
  AgentState,
  BacktestSession,
  BlackBoxState,
  BlackSwanEventRecord,
  BlackSwanIntelligenceState,
  BlackSwanReport,
  CalendarState,
  CaseStudy,
  InstitutionalMemoryEntry,
  CeoDecisionRecord,
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
  DisciplineReview,
  EconomicIntelligenceReport,
  EconomicIntelligenceState,
  EmergencyStopState,
  BoardReport,
  ExecutiveMeetingLogEntry,
  ExecutiveReview,
  FounderState,
  Goal,
  FoundationalMentorState,
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
  ModelValidationReport,
  NewsItem,
  OpportunityRejection,
  PaperPortfolio,
  PerformanceSnapshot,
  PortfolioIntelligence,
  QuestionOfTheDay,
  ResearchItem,
  RiskBudgetStatus,
  RiskLimits,
  EducationProgress,
  PlayerVsAiState,
  ReasoningChallenge,
  ReasoningLabState,
  ReflectionSession,
  RiskWarning,
  ScannerAlert,
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
  StrategicReview,
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
  TreasuryState,
  WarRoomSession,
  WatchlistEntry,
  WisdomState,
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
  strategyReports: StrategyReport[];
  strategyReviews: StrategyReview[];
  strategyModelValidations: ModelValidationReport[];
  strategyMonteCarloResults: StrategyMonteCarloResult[];
  strategyRegimeTests: StrategyRegimeTestReport[];
  strategyLiquidityValidations: StrategyLiquidityValidation[];
  strategyExecutiveReviews: StrategyExecutiveReview[];
  strategyFounderApprovals: StrategyFounderApproval[];
  strategyHealthAssessments: StrategyHealthAssessment[];
  strategyHallOfFame: StrategyHallOfFameEntry[];
  strategyFailedArchive: FailedStrategyArchiveEntry[];
  hallOfFame: HallOfFameEntry[];
  coachReports: CoachReport[];
  companyScore: CompanyScore;
  performanceSnapshots: PerformanceSnapshot[];
  riskLimits: RiskLimits;
  riskWarnings: RiskWarning[];
  emergencyStop: EmergencyStopState;
  scannerAlerts: ScannerAlert[];
  decisions: TradeDecision[];
  tradeProposals: TradeProposal[];
  ceoDecisions: CeoDecisionRecord[];
  debates: Debate[];
  challengeReports: ChallengeReport[];
  innovationState: Record<AgentId, InnovationState>;
  gatekeeperRejections: GatekeeperRejection[];
  opportunityRejections: OpportunityRejection[];
  marketEnvironment: MarketEnvironmentState;
  marketIntelligence: MarketIntelligenceState;
  marketIntelligenceReports: MarketIntelligenceReport[];
  marketIntelligenceLearning: MarketIntelligenceLearningEntry[];
  companyHealth: CompanyHealth;
  companyHealthDelta: CompanyHealthDelta | null;
  companyDna: CompanyDNA;
  dailyObjectiveStatus: DailyObjectiveStatus;
  riskBudgetStatus: RiskBudgetStatus;
  executiveReviews: ExecutiveReview[];
  boardReports: BoardReport[];
  academyProjects: AcademyProject[];
  academyCompletedProjects: AcademyProject[];
  goals: Goal[];
  strategicReviews: StrategicReview[];
  agentKnowledge: Record<AgentId, AgentKnowledgeState>;
  academyState: AcademyState;
  disciplineReviews: DisciplineReview[];
  caseStudies: CaseStudy[];
  institutionalMemory: InstitutionalMemoryEntry[];
  agentPerformanceReviews: AgentPerformanceReview[];
  agentSkillProfiles: AgentSkillProfile[];
  predictionRecords: PredictionRecord[];
  failureClassifications: FailureClassification[];
  learningEvents: LearningEvent[];
  decisionVault: DecisionVaultEntry[];
  warRoomSessions: WarRoomSession[];
  portfolioIntelligence: PortfolioIntelligence;
  economicIntelligence: EconomicIntelligenceState;
  economicIntelligenceReports: EconomicIntelligenceReport[];
  blackSwanIntelligence: BlackSwanIntelligenceState;
  blackSwanReports: BlackSwanReport[];
  defensiveMode: DefensiveModeState;
  blackSwanEvents: BlackSwanEventRecord[];
  institutionalSurvivalScore: InstitutionalSurvivalScore;
  tradingModes: TradingModeState;
  dailyCircuitBreaker: DailyCircuitBreakerRead;
  losingStreak: LosingStreakRead;
  behavioralCircuitBreaker: BehavioralCircuitBreakerRead;
  recoveryBriefings: RecoveryBriefing[];
  selfImprovementProposals: SelfImprovementProposal[];
  evolutionReports: InstitutionalEvolutionReport[];
  visionBoard: VisionBoardState;
  travelMode: TravelModeState;
  travelModeBriefings: TravelModeBriefing[];
  talent: TalentState;
  constitution: ConstitutionState;
  reasoningChallenges: ReasoningChallenge[];
  reasoningLabState: ReasoningLabState;
  executiveMeetingLog: ExecutiveMeetingLogEntry[];
  departmentSelfEvaluations: DepartmentSelfEvaluation[];
  reflectionSessions: ReflectionSession[];
  wisdomState: WisdomState;
  questionArchive: QuestionOfTheDay[];
  thinkingProfiles: Record<AgentId, ThinkingProfile>;
  mentorState: MentorState;
  foundationalMentorState: FoundationalMentorState;
  founderState: FounderState;
  treasury: TreasuryState;
  // Design Bible Chapter 69 Part 1 — Multi-Account & Fund Management System.
  accounts: Account[];
  activeAccountId: string | null;
  calendar: CalendarState;
  blackBox: BlackBoxState;
  agentEnergy: AgentEnergy;
  signalCalibration: SignalCalibrationState;
  playerVsAi: PlayerVsAiState;
  education: EducationProgress;
  viewedTradeNotificationIds: string[];
  settings: SettingsState;
  dialogue: DialogueUiState;
  paused: boolean;
  settingsOpen: boolean;
  newspaperOpen: boolean;
  companyMemoryOpen: boolean;
  /** Design Bible Chapter 67 (TTOS) Part 3 — the Executive Alert Center. */
  alertCenterOpen: boolean;
  coachDashboardOpen: boolean;
  brainRoomHudOpen: boolean;
  commandCenterOpen: boolean;
  commandCenterMode: "quick" | "full";
  campusMapOpen: boolean;
  /** v0.7 — the Eureka! Breakthrough cinematic (see BreakthroughMoment.tsx).
   * A true full-block overlay like Newspaper/Company Memory — unlike the
   * Command Center, nothing behind it should keep moving during a
   * breakthrough moment. */
  breakthroughOpen: boolean;
  executiveVotingOpen: boolean;
  executiveVotingProposalId: string | null;
  /** v0.7 Feature 19 — the Premium Trade Outcome Banner's "View Trade" /
   * "Analyze" buttons request the Command Center jump to a specific
   * decision; FullCommandCenter consumes and clears this. */
  pendingInspectDecision: { decisionId: string; openDetail: boolean; nonce: number } | null;
  /** Design Bible Chapter 67 (TTOS) Part 3 — the Quick Action Dock's
   * quick-jump buttons request the Command Center jump to a specific
   * tab; FullCommandCenter consumes and clears this. */
  pendingCommandCenterTab: string | null;
  /** Design Bible Chapter 67 (TTOS) Part 3 — the CEO's real notification
   * history, viewable in the Executive Alert Center. Every toast
   * CyberNotifications.tsx ever shows is also recorded here (newest
   * first, capped at MAX_ALERT_HISTORY). */
  alertHistory: AlertEntry[];
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
// Design Bible Chapter 67 (TTOS) Part 3 — the Executive Alert Center's
// retention cap, the same "cap the UI list, never the real underlying
// data" convention this codebase already uses elsewhere (e.g.
// maxDecisionVaultEntries, maxMemoryRecords).
const MAX_ALERT_HISTORY = 200;

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
    strategyReports: [],
    strategyReviews: [],
    strategyModelValidations: [],
    strategyMonteCarloResults: [],
    strategyRegimeTests: [],
    strategyLiquidityValidations: [],
    strategyExecutiveReviews: [],
    strategyFounderApprovals: [],
    strategyHealthAssessments: [],
    strategyHallOfFame: [],
    strategyFailedArchive: [],
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
      maxWeeklyLossPct: 10,
      maxMonthlyLossPct: 15,
      maxDrawdownPct: 20,
      maxOpenPositions: 8,
      maxSectorConcentrationPct: 30,
      maxCorrelatedPositions: 2,
      riskPerTradePct: 2,
      dailyProfitTargetPct: 3,
      maxTradesPerDay: 6,
      maxWeeklyDeploymentPct: 15,
      portfolioHeatCapPct: null,
      cashReservePct: 10,
      tierAllocation: { tier1Pct: 2, tier2Pct: 5, tier3Pct: 8, tier4Pct: 10 },
      scalingAggressivenessPct: 100,
      emergencyReductionHeatPct: 75,
      minTradeQualityScore: 70,
      minExpectedValuePct: 0,
      minPriorityScore: 0,
      capitalReservePct: 0,
      minSimilarMatches: 3,
      mistakeWarningSharePct: 30,
      maxDecisionVaultEntries: 200,
      maxMemoryRecords: 200,
      maxLimitedLiveCapital: 2000,
      companyHealthExcellentThreshold: 85,
      companyHealthGoodThreshold: 70,
      companyHealthStableThreshold: 50,
      companyHealthNeedsAttentionThreshold: 30,
    },
    riskWarnings: [],
    emergencyStop: { active: false, activatedAt: null },
    scannerAlerts: [],
    decisions: [],
    tradeProposals: [],
    ceoDecisions: [],
    debates: [],
    challengeReports: [],
    innovationState: {} as Record<AgentId, InnovationState>,
    gatekeeperRejections: [],
    opportunityRejections: [],
    marketEnvironment: {
      current: "sideways",
      label: "SIDEWAYS",
      detail: "No data yet.",
      changedSimMinutes: 0,
      updatedAt: new Date().toISOString(),
      timeline: [],
    },
    marketIntelligence: {
      regime: "sideways_range",
      regimeLabel: "Sideways Range",
      regimeDetail: "No data yet.",
      quality: {
        tier: "average",
        score: 50,
        confidencePct: 40,
        reasoning: "No real candle data sampled yet.",
        evidence: [],
        historicalSimilarity: "No real prior daily reports yet.",
      },
      volatility: { currentPct: 0, historicalAvgPct: 0, sessionPct: 0, percentile: 50, expectedPct: 0, detail: "No data yet." },
      session: { current: "closed", label: "Between Sessions", overlapsActive: [], detail: "No data yet." },
      momentum: { rocPct: 0, strength: "steady", detail: "No data yet." },
      institutionalActivity: { volumePriceDivergenceScore: 0, absorptionDetected: false, symbolsFlagged: [], detail: "No data yet." },
      newsRisk: { activeMarketNewsCount: 0, riskLevel: "low", detail: "No data yet." },
      liquidity: [],
      structure: [],
      updatedAt: new Date().toISOString(),
    },
    marketIntelligenceReports: [],
    marketIntelligenceLearning: [],
    companyHealth: {
      overall: 50,
      tier: "stable",
      operationalStability: 50,
      departmentEfficiency: 50,
      employeeMorale: 50,
      researchProgress: 50,
      capitalHealth: 50,
      resourceUsage: 50,
      reputation: 0,
      technologyLevel: 0,
      marketCoverage: 0,
      educationProgress: 0,
      teamChemistry: 50,
      recommendations: [],
      weakAreas: [],
      updatedAt: new Date().toISOString(),
      decisionQuality: 50,
      executiveAlignment: 50,
      riskGovernance: 50,
      simulationCoverage: 0,
      departmentConsensus: 50,
      selfEvaluationHealth: 50,
      institutionalMemory: 50,
      innovationVelocity: 0,
      talentDevelopment: 0,
      founderOversight: 0,
      complianceHealth: 50,
      executiveOverall: 50,
      executiveTier: "stable",
      combinedOverall: 50,
      combinedTier: "stable",
    },
    companyHealthDelta: null,
    companyDna: {
      traits: [],
      summary: "",
      identity: "Not Yet Established",
      sampleSize: 0,
      updatedAt: new Date().toISOString(),
    },
    dailyObjectiveStatus: {
      simDay: 0,
      tradesToday: 0,
      realizedPnlPctToday: 0,
      profitTargetReached: false,
      maxLossReached: false,
      maxTradesReached: false,
      tradingHalted: false,
      haltReason: null,
      updatedAt: new Date().toISOString(),
    },
    riskBudgetStatus: {
      equity: 100_000,
      startingBalance: 100_000,
      lifetimeDrawdownPct: 0,
      maxDrawdownPct: 20,
      remainingDrawdownBudgetPct: 20,
      dailyLossPctToday: 0,
      maxDailyLossPct: 5,
      remainingDailyLossBudgetPct: 5,
      dailyProfitPctToday: 0,
      dailyProfitTargetPct: 3,
      remainingToDailyProfitTargetPct: 3,
      tradingHalted: false,
      haltReason: null,
      tradingDaysCount: 0,
      computedAt: new Date().toISOString(),
    },
    executiveReviews: [],
    boardReports: [],
    academyProjects: [],
    goals: [],
    strategicReviews: [],
    academyCompletedProjects: [],
    agentKnowledge: {} as Record<AgentId, AgentKnowledgeState>,
    academyState: { level: 1, levelLabel: "Training Room", totalPoints: 0, completedProjectCount: 0, updatedAt: new Date().toISOString() },
    disciplineReviews: [],
    caseStudies: [],
    institutionalMemory: [],
    agentPerformanceReviews: [],
    agentSkillProfiles: [],
    predictionRecords: [],
    failureClassifications: [],
    learningEvents: [],
    decisionVault: [],
    warRoomSessions: [],
    portfolioIntelligence: {
      equity: 0,
      cashBalance: 0,
      cashPctOfEquity: 100,
      deployedPctOfEquity: 0,
      categoryExposure: [],
      correlationPairs: [],
      correlatedClusters: [],
      heat: { totalCapitalAtRiskPct: 0, unrealizedDrawdownPct: 0, largestPositionPct: 0, hottestCategory: null, hottestCategoryPct: 0, tier: "cool", estimatedCapitalAtRiskPct: 0, capitalAtRiskDetail: "" },
      exposure: { longValue: 0, shortValue: 0, netExposure: 0, grossExposure: 0, netExposurePct: 0, grossExposurePct: 0, longPositionCount: 0, shortPositionCount: 0 },
      strategyExposure: [],
      agentExposure: [],
      capitalEfficiency: { profitPerDollar: 0, profitPerDollarHour: 0, tradesMeasured: 0 },
      opportunityCost: "No data yet.",
      updatedAt: new Date().toISOString(),
    },
    economicIntelligence: {
      regime: "sideways",
      regimeLabel: "SIDEWAYS",
      marketQualityTier: "average",
      health: { overall: 50, tier: "cautious", factors: [], reasoning: "No data yet." },
      confidence: { confidencePct: 40, evidenceQuality: "thin", supportingEvidence: [], contradictingEvidence: [], keyAssumptions: [], alternativeOutcome: "No data yet." },
      correlationPairs: [],
      categoryExposure: [],
      newsRisk: { activeMarketNewsCount: 0, riskLevel: "low", detail: "No data yet." },
      updatedAt: new Date().toISOString(),
    },
    economicIntelligenceReports: [],
    blackSwanIntelligence: {
      warning: { overall: 0, tier: "green", factors: [], reasoning: "No data yet." },
      confidence: { confidencePct: 50, evidenceQuality: "thin", supportingEvidence: [], contradictingEvidence: [], keyAssumptions: [], alternativeOutcome: "No data yet." },
      updatedAt: new Date().toISOString(),
    },
    blackSwanReports: [],
    defensiveMode: {
      active: false,
      triggerTier: "red",
      autoTriggerEnabled: false,
      activatedAt: null,
      deactivatedAt: null,
      activationReason: null,
      priorRiskLimits: null,
      equityAtActivation: null,
      peakTierThisEpisode: null,
      activatedSimMinutes: null,
      recommendations: [],
    },
    blackSwanEvents: [],
    institutionalSurvivalScore: {
      overall: 50,
      grade: "c",
      factors: [],
      primaryStrengths: [],
      primaryWeaknesses: [],
      topImprovements: [],
      reasoning: "No data yet.",
      updatedAt: new Date().toISOString(),
    },
    tradingModes: {
      mode: "swing_trading",
      hybridDayAllocationPct: 50,
      changedAt: new Date().toISOString(),
      previousMode: null,
      changeReason: "Default at company founding.",
      rotationCounter: 0,
      adaptiveRecommendationsEnabled: true,
      tier1Pct: 1,
      tier2Pct: 2,
      tier3Pct: 3,
      losingStreakPauseCount: 3,
      losingStreakSuspendCount: 5,
      losingStreakAcknowledged: false,
      behavioralCooldownMinutes: 60,
      behavioralSizeIncreaseThresholdPct: 50,
    },
    dailyCircuitBreaker: { tier: "none", dailyPnlPct: 0, tier1Pct: 1, tier2Pct: 2, tier3Pct: 3, tier4Pct: 5, updatedAt: new Date().toISOString() },
    losingStreak: { consecutiveLosses: 0, pauseActive: false, pauseThreshold: 3, suspendThreshold: 5 },
    behavioralCircuitBreaker: {
      status: "clear",
      reasons: [],
      previousLossSymbol: null,
      previousLossPnl: null,
      minutesSinceLoss: null,
      cooldownMinutes: 60,
      sameInstrument: null,
      sameDirection: null,
      sizeIncreasePct: null,
      consecutiveLosses: 0,
      consecutiveWins: 0,
      repeatedRapidReentryCount: 0,
      previousWinSymbol: null,
      previousWinPnl: null,
      minutesSinceWin: null,
      winSizeIncreasePct: null,
      computedAt: new Date().toISOString(),
    },
    recoveryBriefings: [],
    selfImprovementProposals: [],
    evolutionReports: [],
    visionBoard: { mission: null, priorities: [], objectives: [], identityNote: null, updatedAt: new Date().toISOString() },
    travelMode: {
      active: false,
      settings: {
        positionSizeCapPct: 50,
        dailyRiskCapPct: 50,
        notificationSensitivity: "high_and_above",
        autoActivateEnabled: false,
        autoActivateAfterMinutes: 120,
      },
      activatedAt: null,
      activationSource: null,
      deactivatedAt: null,
      activatedSimMinutes: 0,
      lastCeoDecisionSimMinutes: 0,
    },
    travelModeBriefings: [],
    talent: { reports: [], viewedReportIds: [], updatedAt: new Date().toISOString() },
    constitution: { articles: [], citations: [], amendments: [], updatedAt: new Date().toISOString() },
    reasoningChallenges: [],
    reasoningLabState: { level: 1, levelLabel: "Foundations", completedChallengeCount: 0, updatedAt: new Date().toISOString() },
    executiveMeetingLog: [],
    departmentSelfEvaluations: [],
    reflectionSessions: [],
    wisdomState: { score: 0, tier: "young_company", tierLabel: "Young Company", factors: [], updatedAt: new Date().toISOString() },
    questionArchive: [],
    thinkingProfiles: {} as Record<AgentId, ThinkingProfile>,
    mentorState: { tier: 0, tierLabel: "New Tradition", questionsAsked: 0, updatedAt: new Date().toISOString() },
    foundationalMentorState: { mentors: [], progress: {}, certifications: [], ceoProgress: {}, activeMentorId: null, roadmapOrder: [], customLessonAnswers: {}, updatedAt: new Date().toISOString() },
    founderState: { retired: false, retiredAt: null, log: [], councilSessions: [], updatedAt: new Date().toISOString() },
    treasury: { balance: 0, lifetimeDeposits: 0, largestBalance: 0, transactions: [], savingsRules: [], monthlyReports: [], updatedAt: new Date().toISOString() },
    accounts: [],
    activeAccountId: null,
    calendar: { systemEvents: [], playerEvents: [], updatedAt: new Date().toISOString() },
    blackBox: { active: null, archive: [], reviews: [], viewedBreakthroughIds: [], updatedAt: new Date().toISOString() },
    agentEnergy: { current: 100, cap: 100, updatedAt: new Date().toISOString() },
    signalCalibration: { unlockedLevel: 1, attempts: [], correctCount: 0, totalCount: 0 },
    playerVsAi: { rounds: [], playerCorrectCount: 0, aiCorrectCount: 0, totalCount: 0 },
    education: { viewedLessonIds: [], completedLessonIds: [], quizAttempts: 0, correctQuizAttempts: 0 },
    viewedTradeNotificationIds: [],
    settings: {
      musicVolume: 0.5,
      sfxVolume: 0.7,
      autosaveIntervalSec: 60,
      showFps: false,
      operatingMode: "learning",
      companyPriority: "balanced",
      workMode: "work",
      ceoAcademyLearningMode: false,
      activeWeightProfile: "balanced_institutional",
      customDepartmentWeights: {},
    },
    dialogue: { open: false, speaker: "", lines: [], index: 0 },
    paused: false,
    settingsOpen: false,
    newspaperOpen: false,
    companyMemoryOpen: false,
    alertCenterOpen: false,
    coachDashboardOpen: false,
    brainRoomHudOpen: false,
    commandCenterOpen: false,
    commandCenterMode: "quick",
    campusMapOpen: false,
    breakthroughOpen: false,
    executiveVotingOpen: false,
    executiveVotingProposalId: null,
    pendingInspectDecision: null,
    pendingCommandCenterTab: null,
    alertHistory: [],
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
    const OVERLAY_KEYS = ["newspaperOpen", "companyMemoryOpen", "alertCenterOpen", "coachDashboardOpen", "brainRoomHudOpen", "commandCenterOpen", "campusMapOpen", "breakthroughOpen"] as const;
    // v0.7 — Input Priority fix: the Command Center is intentionally
    // excluded from the movement-blocking subset. Its own backdrop
    // (bg-black/70 backdrop-blur-sm — see CommandCenter.tsx) isn't fully
    // opaque, so the player stays visible walking around behind it;
    // GameManager.movementActive lets WASD keep moving them unless a text
    // field inside it has focus. Every other overlay here keeps blocking
    // movement exactly as before — the reported bug was specifically
    // about the Command Center/Mentor Tab, not Newspaper/Company Memory/
    // Coach Dashboard/Brain Room HUD/Campus Map.
    const MOVEMENT_BLOCKING_KEYS = OVERLAY_KEYS.filter((k) => k !== "commandCenterOpen");
    const setOverlay = (key: (typeof OVERLAY_KEYS)[number], open: boolean, extra?: Partial<GameUiState>): void => {
      const patch = Object.fromEntries(OVERLAY_KEYS.map((k) => [k, k === key ? open : open ? false : this.state[k]])) as Record<
        (typeof OVERLAY_KEYS)[number],
        boolean
      >;
      this.set({ ...patch, ...extra });
      // Two independent signals — see EventBus.ts's own comment on why
      // these split from one "world:overlayOpen" flag.
      EventBus.emit("world:overlayOpen", { open: MOVEMENT_BLOCKING_KEYS.some((k) => this.state[k]) });
      EventBus.emit("world:interactionBlocked", { blocked: OVERLAY_KEYS.some((k) => this.state[k]) });
    };
    EventBus.on("ui:newspaper", ({ open }) => setOverlay("newspaperOpen", open));
    EventBus.on("ui:companyMemory", ({ open }) => setOverlay("companyMemoryOpen", open));
    EventBus.on("ui:alertCenter", ({ open }) => setOverlay("alertCenterOpen", open));
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
    // v0.7 Feature 38 — the Company Campus Map. Same mutual-exclusion +
    // world-pause overlay mechanism as every other full-screen overlay.
    EventBus.on("ui:campusMap", ({ open }) => setOverlay("campusMapOpen", open));
    // v0.7 — the Eureka! Breakthrough cinematic. Same mutual-exclusion +
    // world-pause mechanism as every other full-screen overlay.
    EventBus.on("ui:breakthrough", ({ open }) => setOverlay("breakthroughOpen", open));
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
    EventBus.on("strategyReports:updated", (strategyReports) => this.set({ strategyReports }));
    EventBus.on("strategyReviews:updated", (strategyReviews) => this.set({ strategyReviews }));
    EventBus.on("strategyModelValidations:updated", (strategyModelValidations) => this.set({ strategyModelValidations }));
    EventBus.on("simulation:updated", ({ sessions, results }) => this.set({ backtestSessions: sessions, simulationResults: results }));
    EventBus.on("strategyMonteCarloResults:updated", (strategyMonteCarloResults) => this.set({ strategyMonteCarloResults }));
    EventBus.on("strategyRegimeTests:updated", (strategyRegimeTests) => this.set({ strategyRegimeTests }));
    EventBus.on("strategyLiquidityValidations:updated", (strategyLiquidityValidations) => this.set({ strategyLiquidityValidations }));
    EventBus.on("strategyExecutiveReviews:updated", (strategyExecutiveReviews) => this.set({ strategyExecutiveReviews }));
    EventBus.on("strategyFounderApprovals:updated", (strategyFounderApprovals) => this.set({ strategyFounderApprovals }));
    EventBus.on("strategyHealthAssessments:updated", (strategyHealthAssessments) => this.set({ strategyHealthAssessments }));
    EventBus.on("strategyHallOfFame:updated", (strategyHallOfFame) => this.set({ strategyHallOfFame }));
    EventBus.on("strategyFailedArchive:updated", (strategyFailedArchive) => this.set({ strategyFailedArchive }));
    EventBus.on("hallOfFame:updated", (hallOfFame) => this.set({ hallOfFame }));
    EventBus.on("coachReports:updated", (coachReports) => this.set({ coachReports }));
    EventBus.on("companyScore:updated", (companyScore) => this.set({ companyScore }));
    EventBus.on("performanceSnapshots:updated", (performanceSnapshots) => this.set({ performanceSnapshots }));
    EventBus.on("riskLimits:updated", (riskLimits) => this.set({ riskLimits }));
    EventBus.on("riskWarnings:updated", (riskWarnings) => this.set({ riskWarnings }));
    EventBus.on("emergencyStop:updated", (emergencyStop) => this.set({ emergencyStop }));
    EventBus.on("scannerAlerts:updated", (scannerAlerts) => this.set({ scannerAlerts }));
    EventBus.on("decisions:updated", (decisions) => this.set({ decisions }));
    EventBus.on("tradeProposals:updated", (tradeProposals) => this.set({ tradeProposals }));
    EventBus.on("ceoDecisions:updated", (ceoDecisions) => this.set({ ceoDecisions }));
    EventBus.on("debates:updated", (debates) => this.set({ debates }));
    EventBus.on("challengeReports:updated", (challengeReports) => this.set({ challengeReports }));
    EventBus.on("innovationState:updated", (innovationState) => this.set({ innovationState }));
    EventBus.on("gatekeeperRejections:updated", (gatekeeperRejections) => this.set({ gatekeeperRejections }));
    EventBus.on("opportunityRejections:updated", (opportunityRejections) => this.set({ opportunityRejections }));
    EventBus.on("marketEnvironment:updated", (marketEnvironment) => this.set({ marketEnvironment }));
    EventBus.on("marketIntelligence:updated", (marketIntelligence) => this.set({ marketIntelligence }));
    EventBus.on("marketIntelligenceReports:updated", (marketIntelligenceReports) => this.set({ marketIntelligenceReports }));
    EventBus.on("marketIntelligenceLearning:updated", (marketIntelligenceLearning) => this.set({ marketIntelligenceLearning }));
    EventBus.on("companyHealth:updated", (companyHealth) => this.set({ companyHealth }));
    EventBus.on("companyHealthDelta:updated", (companyHealthDelta) => this.set({ companyHealthDelta }));
    EventBus.on("companyDna:updated", (companyDna) => this.set({ companyDna }));
    EventBus.on("dailyObjectiveStatus:updated", (dailyObjectiveStatus) => this.set({ dailyObjectiveStatus }));
    EventBus.on("riskBudgetStatus:updated", (riskBudgetStatus) => this.set({ riskBudgetStatus }));
    EventBus.on("executiveReviews:updated", (executiveReviews) => this.set({ executiveReviews }));
    EventBus.on("boardReports:updated", (boardReports) => this.set({ boardReports }));
    EventBus.on("academyProjects:updated", (academyProjects) => this.set({ academyProjects }));
    EventBus.on("goals:updated", (goals) => this.set({ goals }));
    EventBus.on("strategicReviews:updated", (strategicReviews) => this.set({ strategicReviews }));
    EventBus.on("academyCompletedProjects:updated", (academyCompletedProjects) => this.set({ academyCompletedProjects }));
    EventBus.on("agentKnowledge:updated", (agentKnowledge) => this.set({ agentKnowledge }));
    EventBus.on("academyState:updated", (academyState) => this.set({ academyState }));
    EventBus.on("disciplineReviews:updated", (disciplineReviews) => this.set({ disciplineReviews }));
    EventBus.on("caseStudies:updated", (caseStudies) => this.set({ caseStudies }));
    EventBus.on("institutionalMemory:updated", (institutionalMemory) => this.set({ institutionalMemory }));
    EventBus.on("agentPerformanceReviews:updated", (agentPerformanceReviews) => this.set({ agentPerformanceReviews }));
    EventBus.on("agentSkillProfiles:updated", (agentSkillProfiles) => this.set({ agentSkillProfiles }));
    EventBus.on("predictionRecords:updated", (predictionRecords) => this.set({ predictionRecords }));
    EventBus.on("failureClassifications:updated", (failureClassifications) => this.set({ failureClassifications }));
    EventBus.on("learningEvents:updated", (learningEvents) => this.set({ learningEvents }));
    EventBus.on("decisionVault:updated", (decisionVault) => this.set({ decisionVault }));
    EventBus.on("warRoomSessions:updated", (warRoomSessions) => this.set({ warRoomSessions }));
    EventBus.on("portfolioIntelligence:updated", (portfolioIntelligence) => this.set({ portfolioIntelligence }));
    EventBus.on("economicIntelligence:updated", (economicIntelligence) => this.set({ economicIntelligence }));
    EventBus.on("economicIntelligenceReports:updated", (economicIntelligenceReports) => this.set({ economicIntelligenceReports }));
    EventBus.on("blackSwanIntelligence:updated", (blackSwanIntelligence) => this.set({ blackSwanIntelligence }));
    EventBus.on("blackSwanReports:updated", (blackSwanReports) => this.set({ blackSwanReports }));
    EventBus.on("defensiveMode:updated", (defensiveMode) => this.set({ defensiveMode }));
    EventBus.on("blackSwanEvents:updated", (blackSwanEvents) => this.set({ blackSwanEvents }));
    EventBus.on("institutionalSurvivalScore:updated", (institutionalSurvivalScore) => this.set({ institutionalSurvivalScore }));
    EventBus.on("tradingModes:updated", (tradingModes) => this.set({ tradingModes }));
    EventBus.on("dailyCircuitBreaker:updated", (dailyCircuitBreaker) => this.set({ dailyCircuitBreaker }));
    EventBus.on("losingStreak:updated", (losingStreak) => this.set({ losingStreak }));
    EventBus.on("behavioralCircuitBreaker:updated", (behavioralCircuitBreaker) => this.set({ behavioralCircuitBreaker }));
    EventBus.on("recoveryBriefings:updated", (recoveryBriefings) => this.set({ recoveryBriefings }));
    EventBus.on("selfImprovementProposals:updated", (selfImprovementProposals) => this.set({ selfImprovementProposals }));
    EventBus.on("evolutionReports:updated", (evolutionReports) => this.set({ evolutionReports }));
    EventBus.on("visionBoard:updated", (visionBoard) => this.set({ visionBoard }));
    EventBus.on("travelMode:updated", (travelMode) => this.set({ travelMode }));
    EventBus.on("travelModeBriefings:updated", (travelModeBriefings) => this.set({ travelModeBriefings }));
    EventBus.on("talent:updated", (talent) => this.set({ talent }));
    EventBus.on("constitution:updated", (constitution) => this.set({ constitution }));
    EventBus.on("reasoningChallenges:updated", (reasoningChallenges) => this.set({ reasoningChallenges }));
    EventBus.on("reasoningLabState:updated", (reasoningLabState) => this.set({ reasoningLabState }));
    EventBus.on("executiveMeetingLog:updated", (executiveMeetingLog) => this.set({ executiveMeetingLog }));
    EventBus.on("departmentSelfEvaluations:updated", (departmentSelfEvaluations) => this.set({ departmentSelfEvaluations }));
    EventBus.on("reflectionSessions:updated", (reflectionSessions) => this.set({ reflectionSessions }));
    EventBus.on("wisdomState:updated", (wisdomState) => this.set({ wisdomState }));
    EventBus.on("questionArchive:updated", (questionArchive) => this.set({ questionArchive }));
    EventBus.on("thinkingProfiles:updated", (thinkingProfiles) => this.set({ thinkingProfiles }));
    EventBus.on("mentorState:updated", (mentorState) => this.set({ mentorState }));
    EventBus.on("foundationalMentorState:updated", (foundationalMentorState) => this.set({ foundationalMentorState }));
    EventBus.on("founderState:updated", (founderState) => this.set({ founderState }));
    EventBus.on("treasury:updated", (treasury) => this.set({ treasury }));
    EventBus.on("accounts:updated", (accounts) => this.set({ accounts }));
    EventBus.on("activeAccount:updated", (activeAccountId) => this.set({ activeAccountId }));
    EventBus.on("calendar:updated", (calendar) => this.set({ calendar }));
    EventBus.on("blackBox:updated", (blackBox) => this.set({ blackBox }));
    EventBus.on("ui:executiveVoting", ({ open, proposalId }) =>
      this.set({ executiveVotingOpen: open, executiveVotingProposalId: open ? (proposalId ?? this.state.executiveVotingProposalId) : null }),
    );
    // A freshly-generated proposal opens the Executive Voting window on
    // its own (per the spec: "Each proposal opens an Executive Voting
    // window") unless the CEO already has one open — never yank an
    // in-progress review away to show a different proposal.
    EventBus.on("tradeProposal:new", (proposal) => {
      if (this.state.executiveVotingOpen) return;
      this.set({ executiveVotingOpen: true, executiveVotingProposalId: proposal.id });
    });
    // v0.7 Feature 19 — the trade outcome banner's View Trade/Analyze
    // buttons jump straight to the Command Center's Decisions tab.
    EventBus.on("trade:inspect", (payload) => {
      this.set({ pendingInspectDecision: payload, commandCenterOpen: true, commandCenterMode: "full" });
      // Command Center only — see setOverlay()'s own comment on why it's
      // excluded from the movement-blocking signal.
      EventBus.emit("world:interactionBlocked", { blocked: true });
    });
    // Design Bible Chapter 67 (TTOS) Part 3 — the Quick Action Dock's
    // quick-jump buttons, same "request a jump, FullCommandCenter
    // consumes and clears it" pattern trade:inspect above already uses.
    EventBus.on("ui:commandCenterJump", ({ tab }) => {
      this.set({ pendingCommandCenterTab: tab, commandCenterOpen: true, commandCenterMode: "full" });
      EventBus.emit("world:interactionBlocked", { blocked: true });
    });
    EventBus.on("agentEnergy:updated", (agentEnergy) => this.set({ agentEnergy }));
    EventBus.on("signalCalibration:updated", (signalCalibration) => this.set({ signalCalibration }));
    EventBus.on("playerVsAi:updated", (playerVsAi) => this.set({ playerVsAi }));
    EventBus.on("education:updated", (education) => this.set({ education }));
    EventBus.on("tradeNotifications:updated", (viewedTradeNotificationIds) => this.set({ viewedTradeNotificationIds }));

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

  /** FullCommandCenter calls this once it has acted on a pendingInspectDecision request. */
  clearPendingInspectDecision(): void {
    this.set({ pendingInspectDecision: null });
  }

  /** FullCommandCenter calls this once it has acted on a pendingCommandCenterTab request. */
  clearPendingCommandCenterTab(): void {
    this.set({ pendingCommandCenterTab: null });
  }

  /** Design Bible Chapter 67 (TTOS) Part 3 — records one real
   * notification into the CEO's alert history (newest first, capped).
   * CyberNotifications.tsx calls this every time it shows a toast, so
   * the Executive Alert Center's history is never missing anything the
   * CEO glimpsed and dismissed. */
  pushAlert(tier: AlertEntry["tier"], title: string, body: string): void {
    const entry: AlertEntry = { id: `alert-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`, tier, title, body, createdAt: new Date().toISOString() };
    this.set({ alertHistory: [entry, ...this.state.alertHistory].slice(0, MAX_ALERT_HISTORY) });
  }
}

export const gameStore = new GameStore();
