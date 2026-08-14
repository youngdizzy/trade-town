import type {
  AcademyProject,
  AcademyState,
  Account,
  AgentEnergy,
  AgentId,
  AgentKnowledgeState,
  AgentPerformanceReview,
  AgentSkillProfile,
  BacktestSession,
  BlackBoxState,
  BlackSwanEventRecord,
  BlackSwanIntelligenceState,
  BlackSwanReport,
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
  ExecutiveMeetingLogEntry,
  BoardReport,
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
  NewsItem,
  OpportunityRejection,
  PaperPortfolio,
  PerformanceSnapshot,
  PortfolioIntelligence,
  QuestionOfTheDay,
  ResearchItem,
  CalendarState,
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
  ScannerAlert,
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
import { EventBus } from "./EventBus";

interface NexusSnapshot {
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
  reflectionSessions: ReflectionSession[];
  wisdomState: WisdomState;
  questionArchive: QuestionOfTheDay[];
  thinkingProfiles: Record<AgentId, ThinkingProfile>;
  mentorState: MentorState;
  foundationalMentorState: FoundationalMentorState;
  founderState: FounderState;
  treasury: TreasuryState;
  accounts: Account[];
  activeAccountId: string | null;
  calendar: CalendarState;
  blackBox: BlackBoxState;
  agentEnergy: AgentEnergy;
  signalCalibration: SignalCalibrationState;
  playerVsAi: PlayerVsAiState;
  education: EducationProgress;
  viewedTradeNotificationIds: string[];
  executiveMeetingLog: ExecutiveMeetingLogEntry[];
  departmentSelfEvaluations: DepartmentSelfEvaluation[];
}

/**
 * Frontend mirror of the backend's NexusManager — holds the company-wide
 * state (tasks, whiteboards, meeting status, news feed, research queue,
 * watchlist, company memory, meeting minutes) that isn't tied to any
 * single agent. Diffs incoming server snapshots against the previous one
 * to emit the discrete events other systems (UI, dialogue) care about,
 * the same way NPCManager does per-agent.
 */
export class NexusManager {
  private static tasks: Task[] = [];
  private static whiteboards: Record<string, string> = {};
  private static meeting: MeetingState = { active: false, participants: [], discussion: [] };
  private static news: NewsItem[] = [];
  private static research: ResearchItem[] = [];
  private static watchlist: WatchlistEntry[] = [];
  private static memory: MemoryRecord[] = [];
  private static meetingMinutes: MeetingMinutes[] = [];
  private static paperPortfolio: PaperPortfolio = {
    cashBalance: 100_000,
    startingBalance: 100_000,
    positions: [],
    orders: [],
    tradeHistory: [],
    totalPnl: 0,
    totalPnlPct: 0,
    winCount: 0,
    lossCount: 0,
  };
  private static strategies: Strategy[] = [];
  private static backtestSessions: BacktestSession[] = [];
  private static simulationResults: SimulationResult[] = [];
  private static strategyReports: StrategyReport[] = [];
  private static strategyReviews: StrategyReview[] = [];
  private static strategyModelValidations: ModelValidationReport[] = [];
  private static strategyMonteCarloResults: StrategyMonteCarloResult[] = [];
  private static strategyRegimeTests: StrategyRegimeTestReport[] = [];
  private static strategyLiquidityValidations: StrategyLiquidityValidation[] = [];
  private static strategyExecutiveReviews: StrategyExecutiveReview[] = [];
  private static strategyFounderApprovals: StrategyFounderApproval[] = [];
  private static strategyHealthAssessments: StrategyHealthAssessment[] = [];
  private static strategyHallOfFame: StrategyHallOfFameEntry[] = [];
  private static strategyFailedArchive: FailedStrategyArchiveEntry[] = [];
  private static hallOfFame: HallOfFameEntry[] = [];
  private static coachReports: CoachReport[] = [];
  private static companyScore: CompanyScore = {
    overall: 50,
    researchQuality: 50,
    decisionQuality: 50,
    riskManagement: 50,
    paperTradingPerformance: 50,
    teamCoordination: 50,
    knowledgeGrowth: 0,
    simulationSuccess: 50,
    updatedAt: new Date().toISOString(),
  };
  private static performanceSnapshots: PerformanceSnapshot[] = [];
  private static riskLimits: RiskLimits = {
    maxPositionPct: 10,
    maxDailyLossPct: 5,
    maxWeeklyLossPct: 10,
    maxMonthlyLossPct: 15,
    maxDrawdownPct: 20,
    maxOpenPositions: 8,
    maxSectorConcentrationPct: 30,
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
  };
  private static riskWarnings: RiskWarning[] = [];
  private static emergencyStop: EmergencyStopState = { active: false, activatedAt: null };
  private static scannerAlerts: ScannerAlert[] = [];
  private static decisions: TradeDecision[] = [];
  private static tradeProposals: TradeProposal[] = [];
  private static ceoDecisions: CeoDecisionRecord[] = [];
  private static debates: Debate[] = [];
  private static challengeReports: ChallengeReport[] = [];
  private static innovationState: Record<AgentId, InnovationState> = {} as Record<AgentId, InnovationState>;
  private static gatekeeperRejections: GatekeeperRejection[] = [];
  private static opportunityRejections: OpportunityRejection[] = [];
  private static marketEnvironment: MarketEnvironmentState = {
    current: "sideways",
    label: "SIDEWAYS",
    detail: "No data yet.",
    changedSimMinutes: 0,
    updatedAt: new Date().toISOString(),
    timeline: [],
  };
  private static marketIntelligence: MarketIntelligenceState = {
    regime: "sideways_range",
    regimeLabel: "Sideways Range",
    regimeDetail: "No data yet.",
    quality: { tier: "average", score: 50, confidencePct: 40, reasoning: "No real candle data sampled yet.", evidence: [], historicalSimilarity: "No real prior daily reports yet." },
    volatility: { currentPct: 0, historicalAvgPct: 0, sessionPct: 0, percentile: 50, expectedPct: 0, detail: "No data yet." },
    session: { current: "closed", label: "Between Sessions", overlapsActive: [], detail: "No data yet." },
    momentum: { rocPct: 0, strength: "steady", detail: "No data yet." },
    institutionalActivity: { volumePriceDivergenceScore: 0, absorptionDetected: false, symbolsFlagged: [], detail: "No data yet." },
    newsRisk: { activeMarketNewsCount: 0, riskLevel: "low", detail: "No data yet." },
    liquidity: [],
    structure: [],
    updatedAt: new Date().toISOString(),
  };
  private static marketIntelligenceReports: MarketIntelligenceReport[] = [];
  private static marketIntelligenceLearning: MarketIntelligenceLearningEntry[] = [];
  private static companyHealth: CompanyHealth = {
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
    executiveOverall: 50,
    executiveTier: "stable",
    combinedOverall: 50,
    combinedTier: "stable",
  };
  private static companyHealthDelta: CompanyHealthDelta | null = null;
  private static companyDna: CompanyDNA = {
    traits: [],
    summary: "",
    identity: "Not Yet Established",
    sampleSize: 0,
    updatedAt: new Date().toISOString(),
  };
  private static dailyObjectiveStatus: DailyObjectiveStatus = {
    simDay: 0,
    tradesToday: 0,
    realizedPnlPctToday: 0,
    profitTargetReached: false,
    maxLossReached: false,
    maxTradesReached: false,
    tradingHalted: false,
    haltReason: null,
    updatedAt: new Date().toISOString(),
  };
  private static riskBudgetStatus: RiskBudgetStatus = {
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
  };
  private static executiveReviews: ExecutiveReview[] = [];
  private static boardReports: BoardReport[] = [];
  private static academyProjects: AcademyProject[] = [];
  private static goals: Goal[] = [];
  private static strategicReviews: StrategicReview[] = [];
  private static academyCompletedProjects: AcademyProject[] = [];
  private static agentKnowledge: Record<AgentId, AgentKnowledgeState> = {} as Record<AgentId, AgentKnowledgeState>;
  private static academyState: AcademyState = {
    level: 1,
    levelLabel: "Training Room",
    totalPoints: 0,
    completedProjectCount: 0,
    updatedAt: new Date().toISOString(),
  };
  private static disciplineReviews: DisciplineReview[] = [];
  private static caseStudies: CaseStudy[] = [];
  private static institutionalMemory: InstitutionalMemoryEntry[] = [];
  private static agentPerformanceReviews: AgentPerformanceReview[] = [];
  private static agentSkillProfiles: AgentSkillProfile[] = [];
  private static learningEvents: LearningEvent[] = [];
  private static decisionVault: DecisionVaultEntry[] = [];
  private static warRoomSessions: WarRoomSession[] = [];
  private static portfolioIntelligence: PortfolioIntelligence = {
    equity: 0,
    cashBalance: 0,
    cashPctOfEquity: 100,
    deployedPctOfEquity: 0,
    categoryExposure: [],
    correlationPairs: [],
    heat: { totalCapitalAtRiskPct: 0, unrealizedDrawdownPct: 0, largestPositionPct: 0, hottestCategory: null, hottestCategoryPct: 0, tier: "cool" },
    capitalEfficiency: { profitPerDollar: 0, profitPerDollarHour: 0, tradesMeasured: 0 },
    opportunityCost: "No data yet.",
    updatedAt: new Date().toISOString(),
  };
  private static economicIntelligence: EconomicIntelligenceState = {
    regime: "sideways",
    regimeLabel: "SIDEWAYS",
    marketQualityTier: "average",
    health: { overall: 50, tier: "cautious", factors: [], reasoning: "No data yet." },
    confidence: { confidencePct: 40, evidenceQuality: "thin", supportingEvidence: [], contradictingEvidence: [], keyAssumptions: [], alternativeOutcome: "No data yet." },
    correlationPairs: [],
    categoryExposure: [],
    newsRisk: { activeMarketNewsCount: 0, riskLevel: "low", detail: "No data yet." },
    updatedAt: new Date().toISOString(),
  };
  private static economicIntelligenceReports: EconomicIntelligenceReport[] = [];
  private static blackSwanIntelligence: BlackSwanIntelligenceState = {
    warning: { overall: 0, tier: "green", factors: [], reasoning: "No data yet." },
    confidence: { confidencePct: 50, evidenceQuality: "thin", supportingEvidence: [], contradictingEvidence: [], keyAssumptions: [], alternativeOutcome: "No data yet." },
    updatedAt: new Date().toISOString(),
  };
  private static blackSwanReports: BlackSwanReport[] = [];
  private static defensiveMode: DefensiveModeState = {
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
  };
  private static blackSwanEvents: BlackSwanEventRecord[] = [];
  private static institutionalSurvivalScore: InstitutionalSurvivalScore = {
    overall: 50,
    grade: "c",
    factors: [],
    primaryStrengths: [],
    primaryWeaknesses: [],
    topImprovements: [],
    reasoning: "No data yet.",
    updatedAt: new Date().toISOString(),
  };
  private static tradingModes: TradingModeState = {
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
  };
  private static dailyCircuitBreaker: DailyCircuitBreakerRead = { tier: "none", dailyPnlPct: 0, tier1Pct: 1, tier2Pct: 2, tier3Pct: 3, tier4Pct: 5, updatedAt: new Date().toISOString() };
  private static losingStreak: LosingStreakRead = { consecutiveLosses: 0, pauseActive: false, pauseThreshold: 3, suspendThreshold: 5 };
  private static behavioralCircuitBreaker: BehavioralCircuitBreakerRead = {
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
  };
  private static recoveryBriefings: RecoveryBriefing[] = [];
  private static selfImprovementProposals: SelfImprovementProposal[] = [];
  private static evolutionReports: InstitutionalEvolutionReport[] = [];
  private static visionBoard: VisionBoardState = {
    mission: null,
    priorities: [],
    objectives: [],
    identityNote: null,
    updatedAt: new Date().toISOString(),
  };
  private static travelMode: TravelModeState = {
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
  };
  private static travelModeBriefings: TravelModeBriefing[] = [];
  private static talent: TalentState = { reports: [], viewedReportIds: [], updatedAt: new Date().toISOString() };
  private static constitution: ConstitutionState = { articles: [], citations: [], amendments: [], updatedAt: new Date().toISOString() };
  private static reasoningChallenges: ReasoningChallenge[] = [];
  private static reasoningLabState: ReasoningLabState = {
    level: 1,
    levelLabel: "Foundations",
    completedChallengeCount: 0,
    updatedAt: new Date().toISOString(),
  };
  private static executiveMeetingLog: ExecutiveMeetingLogEntry[] = [];
  private static departmentSelfEvaluations: DepartmentSelfEvaluation[] = [];
  private static reflectionSessions: ReflectionSession[] = [];
  private static wisdomState: WisdomState = { score: 0, tier: "young_company", tierLabel: "Young Company", factors: [], updatedAt: new Date().toISOString() };
  private static questionArchive: QuestionOfTheDay[] = [];
  private static thinkingProfiles: Record<AgentId, ThinkingProfile> = {} as Record<AgentId, ThinkingProfile>;
  private static mentorState: MentorState = { tier: 0, tierLabel: "New Tradition", questionsAsked: 0, updatedAt: new Date().toISOString() };
  private static foundationalMentorState: FoundationalMentorState = { mentors: [], progress: {}, certifications: [], ceoProgress: {}, activeMentorId: null, roadmapOrder: [], customLessonAnswers: {}, updatedAt: new Date().toISOString() };
  private static founderState: FounderState = { retired: false, retiredAt: null, log: [], councilSessions: [], updatedAt: new Date().toISOString() };
  private static treasury: TreasuryState = { balance: 0, lifetimeDeposits: 0, largestBalance: 0, transactions: [], savingsRules: [], monthlyReports: [], updatedAt: new Date().toISOString() };
  // Design Bible Chapter 69 Part 1 — Multi-Account & Fund Management System.
  private static accounts: Account[] = [];
  private static activeAccountId: string | null = null;
  private static calendar: CalendarState = { systemEvents: [], playerEvents: [], updatedAt: new Date().toISOString() };
  private static blackBox: BlackBoxState = { active: null, archive: [], reviews: [], viewedBreakthroughIds: [], updatedAt: new Date().toISOString() };
  private static agentEnergy: AgentEnergy = { current: 100, cap: 100, updatedAt: new Date().toISOString() };
  private static signalCalibration: SignalCalibrationState = { unlockedLevel: 1, attempts: [], correctCount: 0, totalCount: 0 };
  private static playerVsAi: PlayerVsAiState = { rounds: [], playerCorrectCount: 0, aiCorrectCount: 0, totalCount: 0 };
  private static education: EducationProgress = { viewedLessonIds: [], completedLessonIds: [], quizAttempts: 0, correctQuizAttempts: 0 };
  private static viewedTradeNotificationIds: string[] = [];
  // The WebSocket connects at app boot (see GameCanvas.tsx), independent
  // of the title screen — so the very first applyServerUpdate() can carry
  // whatever proposals already existed server-side before this session
  // ever opened. Without this flag, that pre-existing backlog reads as
  // "just appeared" and auto-opens the Executive Voting popup over the
  // title screen itself — the same class of bug already caught and fixed
  // once for TradeOutcomePopup's own backlog handling (see CHANGELOG's
  // v0.6.2 Phase 10 entry). Sending tradeProposal:new is skipped for the
  // whole first snapshot; every proposal in it is "already there," not new.
  private static hydrated = false;

  static getTasks(): Task[] {
    return this.tasks;
  }

  static getWhiteboard(boardId: string): string {
    return this.whiteboards[boardId] ?? "";
  }

  static getAllWhiteboards(): Record<string, string> {
    return this.whiteboards;
  }

  static getMeeting(): MeetingState {
    return this.meeting;
  }

  static getNews(): NewsItem[] {
    return this.news;
  }

  static getResearch(): ResearchItem[] {
    return this.research;
  }

  static getWatchlist(): WatchlistEntry[] {
    return this.watchlist;
  }

  static getMemory(): MemoryRecord[] {
    return this.memory;
  }

  static getMeetingMinutes(): MeetingMinutes[] {
    return this.meetingMinutes;
  }

  static getPaperPortfolio(): PaperPortfolio {
    return this.paperPortfolio;
  }

  static getStrategies(): Strategy[] {
    return this.strategies;
  }

  static getBacktestSessions(): BacktestSession[] {
    return this.backtestSessions;
  }

  static getSimulationResults(): SimulationResult[] {
    return this.simulationResults;
  }

  static getStrategyReports(): StrategyReport[] {
    return this.strategyReports;
  }

  static getStrategyReviews(): StrategyReview[] {
    return this.strategyReviews;
  }

  static getStrategyModelValidations(): ModelValidationReport[] {
    return this.strategyModelValidations;
  }

  static getStrategyMonteCarloResults(): StrategyMonteCarloResult[] {
    return this.strategyMonteCarloResults;
  }

  static getStrategyRegimeTests(): StrategyRegimeTestReport[] {
    return this.strategyRegimeTests;
  }

  static getStrategyLiquidityValidations(): StrategyLiquidityValidation[] {
    return this.strategyLiquidityValidations;
  }

  static getStrategyExecutiveReviews(): StrategyExecutiveReview[] {
    return this.strategyExecutiveReviews;
  }

  static getStrategyFounderApprovals(): StrategyFounderApproval[] {
    return this.strategyFounderApprovals;
  }

  static getStrategyHealthAssessments(): StrategyHealthAssessment[] {
    return this.strategyHealthAssessments;
  }

  static getStrategyHallOfFame(): StrategyHallOfFameEntry[] {
    return this.strategyHallOfFame;
  }

  static getStrategyFailedArchive(): FailedStrategyArchiveEntry[] {
    return this.strategyFailedArchive;
  }

  /** Applies the immediate result of any /api/sandbox/* CEO action —
   * the same "don't wait for the next WS tick" pattern setPaperPortfolio
   * already uses, so a Sandbox click updates the UI right away. */
  static setSandboxState(strategies: Strategy[], strategyReviews: StrategyReview[]): void {
    this.strategies = strategies;
    this.strategyReviews = strategyReviews;
    EventBus.emit("strategies:updated", strategies);
    EventBus.emit("strategyReviews:updated", strategyReviews);
  }

  static setBacktestSessions(backtestSessions: BacktestSession[]): void {
    this.backtestSessions = backtestSessions;
    EventBus.emit("simulation:updated", { sessions: backtestSessions, results: this.simulationResults });
  }

  /** v0.7 Feature 52 (Part 1) — same immediate-response pattern as
   * setSandboxState, for /api/sandbox/request-review's richer response
   * (which also files a real StrategyExecutiveReview/StrategyFounderApproval
   * in the same CEO action).
   *
   * v0.7 Quantitative Research & Intelligence System, Piece 4 —
   * `modelValidation` is Meridian/CIO's independent, advisory-only
   * ModelValidationReport, filed in this same real CEO action. */
  static setStrategyExecutiveOutcome(
    strategies: Strategy[],
    strategyReviews: StrategyReview[],
    executiveReview: StrategyExecutiveReview | null,
    founderApproval: StrategyFounderApproval | null,
    modelValidation: ModelValidationReport | null = null,
  ): void {
    this.setSandboxState(strategies, strategyReviews);
    if (executiveReview) {
      this.strategyExecutiveReviews = [...this.strategyExecutiveReviews, executiveReview];
      EventBus.emit("strategyExecutiveReviews:updated", this.strategyExecutiveReviews);
    }
    if (founderApproval) {
      this.strategyFounderApprovals = [...this.strategyFounderApprovals, founderApproval];
      EventBus.emit("strategyFounderApprovals:updated", this.strategyFounderApprovals);
    }
    if (modelValidation) {
      this.strategyModelValidations = [...this.strategyModelValidations, modelValidation];
      EventBus.emit("strategyModelValidations:updated", this.strategyModelValidations);
    }
  }

  /** v0.7 Feature 52 (Part 2) — /api/sandbox/retire's real, terminal
   * outcome: exactly one of hallOfFameEntry/failedArchiveEntry is
   * non-null (see backend/app/strategy_lab.py's
   * generate_strategy_retirement_outcome()). */
  static setStrategyRetirementOutcome(strategies: Strategy[], hallOfFameEntry: StrategyHallOfFameEntry | null, failedArchiveEntry: FailedStrategyArchiveEntry | null): void {
    this.strategies = strategies;
    EventBus.emit("strategies:updated", strategies);
    if (hallOfFameEntry) {
      this.strategyHallOfFame = [...this.strategyHallOfFame, hallOfFameEntry];
      EventBus.emit("strategyHallOfFame:updated", this.strategyHallOfFame);
      EventBus.emit("strategyHallOfFame:entryAdded", hallOfFameEntry);
    }
    if (failedArchiveEntry) {
      this.strategyFailedArchive = [...this.strategyFailedArchive, failedArchiveEntry];
      EventBus.emit("strategyFailedArchive:updated", this.strategyFailedArchive);
      EventBus.emit("strategyFailedArchive:entryAdded", failedArchiveEntry);
    }
  }

  static getHallOfFame(): HallOfFameEntry[] {
    return this.hallOfFame;
  }

  static getCoachReports(): CoachReport[] {
    return this.coachReports;
  }

  static getCompanyScore(): CompanyScore {
    return this.companyScore;
  }

  static getMarketEnvironment(): MarketEnvironmentState {
    return this.marketEnvironment;
  }

  static getMarketIntelligence(): MarketIntelligenceState {
    return this.marketIntelligence;
  }

  static getMarketIntelligenceReports(): MarketIntelligenceReport[] {
    return this.marketIntelligenceReports;
  }

  static getMarketIntelligenceLearning(): MarketIntelligenceLearningEntry[] {
    return this.marketIntelligenceLearning;
  }

  static getCompanyHealth(): CompanyHealth {
    return this.companyHealth;
  }

  static getCompanyHealthDelta(): CompanyHealthDelta | null {
    return this.companyHealthDelta;
  }

  static getCompanyDna(): CompanyDNA {
    return this.companyDna;
  }

  static getDailyObjectiveStatus(): DailyObjectiveStatus {
    return this.dailyObjectiveStatus;
  }

  static getRiskBudgetStatus(): RiskBudgetStatus {
    return this.riskBudgetStatus;
  }

  static getExecutiveReviews(): ExecutiveReview[] {
    return this.executiveReviews;
  }

  static getBoardReports(): BoardReport[] {
    return this.boardReports;
  }

  static getAcademyProjects(): AcademyProject[] {
    return this.academyProjects;
  }

  static getGoals(): Goal[] {
    return this.goals;
  }

  static getStrategicReviews(): StrategicReview[] {
    return this.strategicReviews;
  }

  static getAcademyCompletedProjects(): AcademyProject[] {
    return this.academyCompletedProjects;
  }

  static getAgentKnowledge(): Record<AgentId, AgentKnowledgeState> {
    return this.agentKnowledge;
  }

  static getAcademyState(): AcademyState {
    return this.academyState;
  }

  static getDisciplineReviews(): DisciplineReview[] {
    return this.disciplineReviews;
  }

  static getCaseStudies(): CaseStudy[] {
    return this.caseStudies;
  }

  static getInstitutionalMemory(): InstitutionalMemoryEntry[] {
    return this.institutionalMemory;
  }

  static getAgentPerformanceReviews(): AgentPerformanceReview[] {
    return this.agentPerformanceReviews;
  }

  static getAgentSkillProfiles(): AgentSkillProfile[] {
    return this.agentSkillProfiles;
  }

  static getLearningEvents(): LearningEvent[] {
    return this.learningEvents;
  }

  static getDecisionVault(): DecisionVaultEntry[] {
    return this.decisionVault;
  }

  static getWarRoomSessions(): WarRoomSession[] {
    return this.warRoomSessions;
  }

  static getPortfolioIntelligence(): PortfolioIntelligence {
    return this.portfolioIntelligence;
  }

  static getEconomicIntelligence(): EconomicIntelligenceState {
    return this.economicIntelligence;
  }

  static getEconomicIntelligenceReports(): EconomicIntelligenceReport[] {
    return this.economicIntelligenceReports;
  }

  static getBlackSwanIntelligence(): BlackSwanIntelligenceState {
    return this.blackSwanIntelligence;
  }

  static getBlackSwanReports(): BlackSwanReport[] {
    return this.blackSwanReports;
  }

  static getDefensiveMode(): DefensiveModeState {
    return this.defensiveMode;
  }

  static getBlackSwanEvents(): BlackSwanEventRecord[] {
    return this.blackSwanEvents;
  }

  static getInstitutionalSurvivalScore(): InstitutionalSurvivalScore {
    return this.institutionalSurvivalScore;
  }

  static getTradingModes(): TradingModeState {
    return this.tradingModes;
  }

  static getDailyCircuitBreaker(): DailyCircuitBreakerRead {
    return this.dailyCircuitBreaker;
  }

  static getLosingStreak(): LosingStreakRead {
    return this.losingStreak;
  }

  static getBehavioralCircuitBreaker(): BehavioralCircuitBreakerRead {
    return this.behavioralCircuitBreaker;
  }

  static getRecoveryBriefings(): RecoveryBriefing[] {
    return this.recoveryBriefings;
  }

  static getSelfImprovementProposals(): SelfImprovementProposal[] {
    return this.selfImprovementProposals;
  }

  static getEvolutionReports(): InstitutionalEvolutionReport[] {
    return this.evolutionReports;
  }

  static getVisionBoard(): VisionBoardState {
    return this.visionBoard;
  }

  static getTravelMode(): TravelModeState {
    return this.travelMode;
  }

  static getTravelModeBriefings(): TravelModeBriefing[] {
    return this.travelModeBriefings;
  }

  static getTalent(): TalentState {
    return this.talent;
  }

  static getConstitution(): ConstitutionState {
    return this.constitution;
  }

  /** Applies the immediate result of any /api/constitution/* CEO action
   * — the same "don't wait for the next WS tick" pattern setSandboxState
   * already uses. */
  static setConstitution(constitution: ConstitutionState): void {
    this.constitution = constitution;
    EventBus.emit("constitution:updated", constitution);
  }

  /** Design Bible Chapter 74 Part 1 — applies the result of a real CEO
   * decide/implement action on a Self-Improvement Proposal immediately,
   * rather than waiting for the next WS tick. */
  static setSelfImprovementProposals(proposals: SelfImprovementProposal[]): void {
    this.selfImprovementProposals = proposals;
    EventBus.emit("selfImprovementProposals:updated", proposals);
  }

  /** Design Bible Chapter 74.5 — applies the result of a real CEO
   * mutation to the Vision Board immediately, rather than waiting for
   * the next WS tick. */
  static setVisionBoard(visionBoard: VisionBoardState): void {
    this.visionBoard = visionBoard;
    EventBus.emit("visionBoard:updated", visionBoard);
  }

  /** v0.7 Feature 49 — applies the result of POST /api/risk-limits, the
   * CEO's Daily Trading Objectives configuration. */
  static setRiskLimits(riskLimits: RiskLimits): void {
    this.riskLimits = riskLimits;
    EventBus.emit("riskLimits:updated", riskLimits);
  }

  /** Design Bible Chapter 64 — applies the result of POST /api/goals/create
   * or /api/goals/cancel. */
  static setGoals(goals: Goal[]): void {
    this.goals = goals;
    EventBus.emit("goals:updated", goals);
  }

  /** Applies the result of POST /api/talent/ack-report, the same "seen"
   * tracking pattern setViewedBreakthroughIds already uses. */
  static setViewedTalentReportIds(ids: string[]): void {
    this.talent = { ...this.talent, viewedReportIds: ids };
    EventBus.emit("talent:updated", this.talent);
  }

  static getReasoningChallenges(): ReasoningChallenge[] {
    return this.reasoningChallenges;
  }

  static getReasoningLabState(): ReasoningLabState {
    return this.reasoningLabState;
  }

  static getExecutiveMeetingLog(): ExecutiveMeetingLogEntry[] {
    return this.executiveMeetingLog;
  }

  static getDepartmentSelfEvaluations(): DepartmentSelfEvaluation[] {
    return this.departmentSelfEvaluations;
  }

  static getReflectionSessions(): ReflectionSession[] {
    return this.reflectionSessions;
  }

  static getWisdomState(): WisdomState {
    return this.wisdomState;
  }

  static getQuestionArchive(): QuestionOfTheDay[] {
    return this.questionArchive;
  }

  static getThinkingProfiles(): Record<AgentId, ThinkingProfile> {
    return this.thinkingProfiles;
  }

  static getMentorState(): MentorState {
    return this.mentorState;
  }

  static getFoundationalMentorState(): FoundationalMentorState {
    return this.foundationalMentorState;
  }

  static setFoundationalMentorState(foundationalMentorState: FoundationalMentorState): void {
    this.foundationalMentorState = foundationalMentorState;
    EventBus.emit("foundationalMentorState:updated", foundationalMentorState);
  }

  static getFounderState(): FounderState {
    return this.founderState;
  }

  static getTreasury(): TreasuryState {
    return this.treasury;
  }

  /** Applies the result of a direct POST /api/treasury/... call
   * immediately, the same reasoning as setEducation above. */
  static setTreasury(treasury: TreasuryState): void {
    this.treasury = treasury;
    EventBus.emit("treasury:updated", treasury);
  }

  static getAccounts(): Account[] {
    return this.accounts;
  }

  static getActiveAccountId(): string | null {
    return this.activeAccountId;
  }

  /** Applies the result of a direct POST /api/accounts/... call
   * immediately, the same reasoning as setTreasury above. */
  static setAccounts(accounts: Account[]): void {
    this.accounts = accounts;
    EventBus.emit("accounts:updated", accounts);
  }

  static setActiveAccountId(activeAccountId: string | null): void {
    this.activeAccountId = activeAccountId;
    EventBus.emit("activeAccount:updated", activeAccountId);
  }

  static getCalendar(): CalendarState {
    return this.calendar;
  }

  /** Applies the result of a direct POST /api/calendar/events/... call
   * immediately, the same reasoning as setTreasury above. */
  static setCalendar(calendar: CalendarState): void {
    this.calendar = calendar;
    EventBus.emit("calendar:updated", calendar);
  }

  static getBlackBox(): BlackBoxState {
    return this.blackBox;
  }

  /** Applies the result of a direct POST /api/black-box/... call
   * immediately, the same reasoning as setTreasury above. */
  static setBlackBox(blackBox: BlackBoxState): void {
    this.blackBox = blackBox;
    EventBus.emit("blackBox:updated", blackBox);
  }

  /** Applies the result of POST /api/black-box/ack-breakthrough, the same
   * "seen" tracking pattern setViewedTradeNotificationIds already uses. */
  static setViewedBreakthroughIds(ids: string[]): void {
    this.blackBox = { ...this.blackBox, viewedBreakthroughIds: ids };
    EventBus.emit("blackBox:updated", this.blackBox);
  }

  /** Applies the real Operating Capital change a Treasury deposit/withdraw
   * produces, the same reasoning as setTreasury above. */
  static setPaperPortfolio(paperPortfolio: PaperPortfolio): void {
    this.paperPortfolio = paperPortfolio;
    EventBus.emit("portfolio:updated", paperPortfolio);
  }

  static getPerformanceSnapshots(): PerformanceSnapshot[] {
    return this.performanceSnapshots;
  }

  static getRiskLimits(): RiskLimits {
    return this.riskLimits;
  }

  static getRiskWarnings(): RiskWarning[] {
    return this.riskWarnings;
  }

  /** Design Bible Chapter 67 (TTOS) Part 3 — applies the result of
   * POST /api/emergency-stop/activate or /resume immediately, the same
   * "don't wait for the next WS tick" pattern setRiskLimits above uses. */
  static setEmergencyStop(emergencyStop: EmergencyStopState): void {
    this.emergencyStop = emergencyStop;
    EventBus.emit("emergencyStop:updated", emergencyStop);
  }

  static getEmergencyStop(): EmergencyStopState {
    return this.emergencyStop;
  }

  static getScannerAlerts(): ScannerAlert[] {
    return this.scannerAlerts;
  }

  static getDecisions(): TradeDecision[] {
    return this.decisions;
  }

  static getTradeProposals(): TradeProposal[] {
    return this.tradeProposals;
  }

  static getCeoDecisions(): CeoDecisionRecord[] {
    return this.ceoDecisions;
  }

  static getDebates(): Debate[] {
    return this.debates;
  }

  /** Applies the result of a direct POST /api/executive/debate/regenerate
   * call immediately — same reasoning as setExecutiveDecisionResult below. */
  static setDebates(debates: Debate[]): void {
    this.debates = debates;
    EventBus.emit("debates:updated", debates);
  }

  static getChallengeReports(): ChallengeReport[] {
    return this.challengeReports;
  }

  static getInnovationState(): Record<AgentId, InnovationState> {
    return this.innovationState;
  }

  /** v0.7 Feature 41 — applies the result of a direct POST
   * /api/executive/challenge/regenerate call immediately, same reasoning
   * as setDebates above. innovationState is recomputed server-side from
   * challengeReports, so both always arrive together. */
  static setChallengeReports(challengeReports: ChallengeReport[], innovationState: Record<AgentId, InnovationState>): void {
    this.challengeReports = challengeReports;
    this.innovationState = innovationState;
    EventBus.emit("challengeReports:updated", challengeReports);
    EventBus.emit("innovationState:updated", innovationState);
  }

  /** v0.7 Feature 40.5 — applies the result of a direct POST
   * /api/executive/hold call immediately. Unlike setExecutiveDecisionResult,
   * a hold never resolves the proposal (see app/executive.py's
   * hold_proposal()), so only tradeProposals itself changes. */
  static setTradeProposals(tradeProposals: TradeProposal[]): void {
    this.tradeProposals = tradeProposals;
    EventBus.emit("tradeProposals:updated", tradeProposals);
  }

  static getGatekeeperRejections(): GatekeeperRejection[] {
    return this.gatekeeperRejections;
  }

  static getOpportunityRejections(): OpportunityRejection[] {
    return this.opportunityRejections;
  }

  /** Applies the result of a direct POST /api/executive/decide call
   * immediately, the same reasoning as setAgentEnergy below — no need to
   * wait for the next sim-tick WS broadcast to see the proposal resolved.
   * v0.7 Feature 20 — also carries any fresh GatekeeperRejection this
   * decision produced. */
  static setExecutiveDecisionResult(
    tradeProposals: TradeProposal[],
    ceoDecisions: CeoDecisionRecord[],
    decisions: TradeDecision[],
    paperPortfolio: PaperPortfolio,
    gatekeeperRejections: GatekeeperRejection[],
  ): void {
    this.tradeProposals = tradeProposals;
    this.ceoDecisions = ceoDecisions;
    this.decisions = decisions;
    this.paperPortfolio = paperPortfolio;
    this.gatekeeperRejections = gatekeeperRejections;
    EventBus.emit("tradeProposals:updated", tradeProposals);
    EventBus.emit("ceoDecisions:updated", ceoDecisions);
    EventBus.emit("portfolio:updated", paperPortfolio);
    EventBus.emit("gatekeeperRejections:updated", gatekeeperRejections);
  }

  static getAgentEnergy(): AgentEnergy {
    return this.agentEnergy;
  }

  /** Applies the result of a direct POST /api/energy/spend call immediately,
   * instead of waiting up to ~2s for the next sim-tick WS broadcast to catch
   * up — keeps the meter (and the next save snapshot) in sync right away. */
  static setAgentEnergy(agentEnergy: AgentEnergy): void {
    this.agentEnergy = agentEnergy;
    EventBus.emit("agentEnergy:updated", agentEnergy);
  }

  static getSignalCalibration(): SignalCalibrationState {
    return this.signalCalibration;
  }

  /** Applies the result of a direct POST /api/calibration/submit call
   * immediately, the same reasoning as setAgentEnergy above (grading also
   * updates agentEnergy on a correct answer — call setAgentEnergy too). */
  static setSignalCalibration(signalCalibration: SignalCalibrationState): void {
    this.signalCalibration = signalCalibration;
    EventBus.emit("signalCalibration:updated", signalCalibration);
  }

  static getPlayerVsAi(): PlayerVsAiState {
    return this.playerVsAi;
  }

  /** Applies the result of a direct POST /api/player-vs-ai/submit call
   * immediately, the same reasoning as setSignalCalibration above. */
  static setPlayerVsAi(playerVsAi: PlayerVsAiState): void {
    this.playerVsAi = playerVsAi;
    EventBus.emit("playerVsAi:updated", playerVsAi);
  }

  static getEducation(): EducationProgress {
    return this.education;
  }

  /** Applies the result of a direct POST /api/education/view or
   * .../quiz call immediately, the same reasoning as setPlayerVsAi above. */
  static setEducation(education: EducationProgress): void {
    this.education = education;
    EventBus.emit("education:updated", education);
  }

  /** Applies the result of a direct POST /api/mentor/qotd/respond call
   * immediately, the same reasoning as setEducation above — replaces the
   * single archive entry the player just answered. */
  static setQuestionOfTheDayResponse(question: QuestionOfTheDay): void {
    this.questionArchive = this.questionArchive.map((q) => (q.id === question.id ? question : q));
    EventBus.emit("questionArchive:updated", this.questionArchive);
  }

  static getViewedTradeNotificationIds(): string[] {
    return this.viewedTradeNotificationIds;
  }

  /** Applies the result of a direct POST /api/trades/ack call
   * immediately, the same reasoning as setEducation above. */
  static setViewedTradeNotificationIds(ids: string[]): void {
    this.viewedTradeNotificationIds = ids;
    EventBus.emit("tradeNotifications:updated", ids);
  }

  static applyServerUpdate(update: NexusSnapshot): void {
    for (const task of update.tasks) {
      const previous = this.tasks.find((t) => t.id === task.id);
      if (!previous) EventBus.emit("task:assigned", task);
      else if (previous.status !== "completed" && task.status === "completed") EventBus.emit("task:completed", task);
    }
    this.tasks = update.tasks;

    for (const [boardId, text] of Object.entries(update.whiteboards)) {
      if (this.whiteboards[boardId] !== text) EventBus.emit("whiteboard:updated", { boardId, text });
    }
    this.whiteboards = update.whiteboards;

    if (!this.meeting.active && update.meeting.active) EventBus.emit("meeting:started", update.meeting);
    else if (this.meeting.active && !update.meeting.active) EventBus.emit("meeting:ended", undefined);
    this.meeting = update.meeting;

    if (update.news.length !== this.news.length) EventBus.emit("news:updated", update.news);
    this.news = update.news;

    for (const item of update.research) {
      const previous = this.research.find((r) => r.id === item.id);
      if (previous && previous.status !== "completed" && item.status === "completed") {
        EventBus.emit("research:completed", item);
      }
    }
    if (update.research !== this.research) EventBus.emit("research:updated", update.research);
    this.research = update.research;

    if (update.watchlist !== this.watchlist) EventBus.emit("watchlist:updated", update.watchlist);
    this.watchlist = update.watchlist;

    if (update.memory.length !== this.memory.length) EventBus.emit("memory:updated", update.memory);
    this.memory = update.memory;

    if (update.meetingMinutes.length !== this.meetingMinutes.length) {
      const newest = update.meetingMinutes[update.meetingMinutes.length - 1];
      if (newest) EventBus.emit("meeting:minutesRecorded", newest);
    }
    this.meetingMinutes = update.meetingMinutes;

    if (update.paperPortfolio !== this.paperPortfolio) EventBus.emit("portfolio:updated", update.paperPortfolio);
    this.paperPortfolio = update.paperPortfolio;

    if (update.strategies !== this.strategies) EventBus.emit("strategies:updated", update.strategies);
    this.strategies = update.strategies;

    if (update.simulationResults.length !== this.simulationResults.length) {
      const newest = update.simulationResults[update.simulationResults.length - 1];
      if (newest) EventBus.emit("simulation:completed", newest);
    }
    if (update.backtestSessions !== this.backtestSessions || update.simulationResults !== this.simulationResults) {
      EventBus.emit("simulation:updated", { sessions: update.backtestSessions, results: update.simulationResults });
    }
    this.backtestSessions = update.backtestSessions;
    this.simulationResults = update.simulationResults;

    if (update.strategyReports.length !== this.strategyReports.length) EventBus.emit("strategyReports:updated", update.strategyReports);
    this.strategyReports = update.strategyReports;

    if (update.strategyReviews.length !== this.strategyReviews.length) EventBus.emit("strategyReviews:updated", update.strategyReviews);
    this.strategyReviews = update.strategyReviews;

    if (update.strategyModelValidations.length !== this.strategyModelValidations.length) EventBus.emit("strategyModelValidations:updated", update.strategyModelValidations);
    this.strategyModelValidations = update.strategyModelValidations;

    if (update.strategyMonteCarloResults.length !== this.strategyMonteCarloResults.length) EventBus.emit("strategyMonteCarloResults:updated", update.strategyMonteCarloResults);
    this.strategyMonteCarloResults = update.strategyMonteCarloResults;

    if (update.strategyRegimeTests.length !== this.strategyRegimeTests.length) EventBus.emit("strategyRegimeTests:updated", update.strategyRegimeTests);
    this.strategyRegimeTests = update.strategyRegimeTests;

    if (update.strategyLiquidityValidations.length !== this.strategyLiquidityValidations.length) EventBus.emit("strategyLiquidityValidations:updated", update.strategyLiquidityValidations);
    this.strategyLiquidityValidations = update.strategyLiquidityValidations;

    if (update.strategyExecutiveReviews.length !== this.strategyExecutiveReviews.length) EventBus.emit("strategyExecutiveReviews:updated", update.strategyExecutiveReviews);
    this.strategyExecutiveReviews = update.strategyExecutiveReviews;

    if (update.strategyFounderApprovals.length !== this.strategyFounderApprovals.length) EventBus.emit("strategyFounderApprovals:updated", update.strategyFounderApprovals);
    this.strategyFounderApprovals = update.strategyFounderApprovals;

    if (update.strategyHealthAssessments.length !== this.strategyHealthAssessments.length) EventBus.emit("strategyHealthAssessments:updated", update.strategyHealthAssessments);
    this.strategyHealthAssessments = update.strategyHealthAssessments;

    if (update.strategyHallOfFame.length !== this.strategyHallOfFame.length) {
      const newest = update.strategyHallOfFame[update.strategyHallOfFame.length - 1];
      if (newest) EventBus.emit("strategyHallOfFame:entryAdded", newest);
      EventBus.emit("strategyHallOfFame:updated", update.strategyHallOfFame);
    }
    this.strategyHallOfFame = update.strategyHallOfFame;

    if (update.strategyFailedArchive.length !== this.strategyFailedArchive.length) {
      const newest = update.strategyFailedArchive[update.strategyFailedArchive.length - 1];
      if (newest) EventBus.emit("strategyFailedArchive:entryAdded", newest);
      EventBus.emit("strategyFailedArchive:updated", update.strategyFailedArchive);
    }
    this.strategyFailedArchive = update.strategyFailedArchive;

    if (update.hallOfFame.length !== this.hallOfFame.length) {
      const newest = update.hallOfFame[update.hallOfFame.length - 1];
      if (newest) EventBus.emit("hallOfFame:entryAdded", newest);
      EventBus.emit("hallOfFame:updated", update.hallOfFame);
    }
    this.hallOfFame = update.hallOfFame;

    if (update.coachReports.length !== this.coachReports.length) {
      const newest = update.coachReports[update.coachReports.length - 1];
      this.coachReports = update.coachReports;
      if (newest) EventBus.emit("coach:reportReceived", newest);
      EventBus.emit("coachReports:updated", update.coachReports);
    } else {
      this.coachReports = update.coachReports;
    }

    if (update.companyScore !== this.companyScore) EventBus.emit("companyScore:updated", update.companyScore);
    this.companyScore = update.companyScore;

    if (update.performanceSnapshots !== this.performanceSnapshots) EventBus.emit("performanceSnapshots:updated", update.performanceSnapshots);
    this.performanceSnapshots = update.performanceSnapshots;

    if (update.riskLimits !== this.riskLimits) EventBus.emit("riskLimits:updated", update.riskLimits);
    this.riskLimits = update.riskLimits;

    if (update.riskWarnings !== this.riskWarnings) EventBus.emit("riskWarnings:updated", update.riskWarnings);
    this.riskWarnings = update.riskWarnings;

    if (update.emergencyStop !== this.emergencyStop) EventBus.emit("emergencyStop:updated", update.emergencyStop);
    this.emergencyStop = update.emergencyStop;

    if (update.scannerAlerts.length !== this.scannerAlerts.length) {
      const newest = update.scannerAlerts[update.scannerAlerts.length - 1];
      if (newest) EventBus.emit("scanner:alertDetected", newest);
      EventBus.emit("scannerAlerts:updated", update.scannerAlerts);
    }
    this.scannerAlerts = update.scannerAlerts;

    if (update.decisions.length !== this.decisions.length) {
      const newest = update.decisions[update.decisions.length - 1];
      if (newest) EventBus.emit("decision:made", newest);
      EventBus.emit("decisions:updated", update.decisions);
    }
    this.decisions = update.decisions;

    if (update.tradeProposals.length !== this.tradeProposals.length) {
      const newest = update.tradeProposals[update.tradeProposals.length - 1];
      if (this.hydrated && newest && update.tradeProposals.length > this.tradeProposals.length) EventBus.emit("tradeProposal:new", newest);
      EventBus.emit("tradeProposals:updated", update.tradeProposals);
    }
    this.tradeProposals = update.tradeProposals;
    this.hydrated = true;

    if (update.ceoDecisions.length !== this.ceoDecisions.length) EventBus.emit("ceoDecisions:updated", update.ceoDecisions);
    this.ceoDecisions = update.ceoDecisions;

    if (update.debates.length !== this.debates.length) EventBus.emit("debates:updated", update.debates);
    this.debates = update.debates;

    if (update.challengeReports.length !== this.challengeReports.length) EventBus.emit("challengeReports:updated", update.challengeReports);
    this.challengeReports = update.challengeReports;
    if (update.innovationState !== this.innovationState) EventBus.emit("innovationState:updated", update.innovationState);
    this.innovationState = update.innovationState;

    if (update.gatekeeperRejections.length !== this.gatekeeperRejections.length) {
      EventBus.emit("gatekeeperRejections:updated", update.gatekeeperRejections);
    }
    this.gatekeeperRejections = update.gatekeeperRejections;

    if (update.opportunityRejections.length !== this.opportunityRejections.length) {
      EventBus.emit("opportunityRejections:updated", update.opportunityRejections);
    }
    this.opportunityRejections = update.opportunityRejections;

    if (update.marketEnvironment !== this.marketEnvironment) EventBus.emit("marketEnvironment:updated", update.marketEnvironment);
    this.marketEnvironment = update.marketEnvironment;

    if (update.marketIntelligence !== this.marketIntelligence) EventBus.emit("marketIntelligence:updated", update.marketIntelligence);
    this.marketIntelligence = update.marketIntelligence;

    if (update.marketIntelligenceReports.length !== this.marketIntelligenceReports.length) {
      EventBus.emit("marketIntelligenceReports:updated", update.marketIntelligenceReports);
    }
    this.marketIntelligenceReports = update.marketIntelligenceReports;

    if (update.marketIntelligenceLearning.length !== this.marketIntelligenceLearning.length) {
      EventBus.emit("marketIntelligenceLearning:updated", update.marketIntelligenceLearning);
    }
    this.marketIntelligenceLearning = update.marketIntelligenceLearning;

    if (update.companyHealth !== this.companyHealth) EventBus.emit("companyHealth:updated", update.companyHealth);
    this.companyHealth = update.companyHealth;

    if (update.companyHealthDelta !== this.companyHealthDelta) EventBus.emit("companyHealthDelta:updated", update.companyHealthDelta);
    this.companyHealthDelta = update.companyHealthDelta;

    if (update.companyDna !== this.companyDna) EventBus.emit("companyDna:updated", update.companyDna);
    this.companyDna = update.companyDna;

    if (update.dailyObjectiveStatus !== this.dailyObjectiveStatus) EventBus.emit("dailyObjectiveStatus:updated", update.dailyObjectiveStatus);
    this.dailyObjectiveStatus = update.dailyObjectiveStatus;

    if (update.riskBudgetStatus !== this.riskBudgetStatus) EventBus.emit("riskBudgetStatus:updated", update.riskBudgetStatus);
    this.riskBudgetStatus = update.riskBudgetStatus;

    if (update.executiveReviews.length !== this.executiveReviews.length) EventBus.emit("executiveReviews:updated", update.executiveReviews);
    this.executiveReviews = update.executiveReviews;

    if (update.boardReports.length !== this.boardReports.length) EventBus.emit("boardReports:updated", update.boardReports);
    this.boardReports = update.boardReports;

    if (update.academyProjects !== this.academyProjects) EventBus.emit("academyProjects:updated", update.academyProjects);
    this.academyProjects = update.academyProjects;

    if (update.goals !== this.goals) EventBus.emit("goals:updated", update.goals);
    this.goals = update.goals;

    if (update.strategicReviews.length !== this.strategicReviews.length) EventBus.emit("strategicReviews:updated", update.strategicReviews);
    this.strategicReviews = update.strategicReviews;

    if (update.academyCompletedProjects.length !== this.academyCompletedProjects.length) {
      EventBus.emit("academyCompletedProjects:updated", update.academyCompletedProjects);
    }
    this.academyCompletedProjects = update.academyCompletedProjects;

    if (update.agentKnowledge !== this.agentKnowledge) EventBus.emit("agentKnowledge:updated", update.agentKnowledge);
    this.agentKnowledge = update.agentKnowledge;

    if (update.academyState !== this.academyState) EventBus.emit("academyState:updated", update.academyState);
    this.academyState = update.academyState;

    if (update.disciplineReviews.length !== this.disciplineReviews.length) {
      EventBus.emit("disciplineReviews:updated", update.disciplineReviews);
    }
    this.disciplineReviews = update.disciplineReviews;

    if (update.caseStudies.length !== this.caseStudies.length) EventBus.emit("caseStudies:updated", update.caseStudies);
    this.caseStudies = update.caseStudies;

    if (update.institutionalMemory.length !== this.institutionalMemory.length) {
      EventBus.emit("institutionalMemory:updated", update.institutionalMemory);
    }
    this.institutionalMemory = update.institutionalMemory;

    if (update.agentPerformanceReviews.length !== this.agentPerformanceReviews.length) {
      EventBus.emit("agentPerformanceReviews:updated", update.agentPerformanceReviews);
    }
    this.agentPerformanceReviews = update.agentPerformanceReviews;

    if (update.agentSkillProfiles.length !== this.agentSkillProfiles.length) {
      EventBus.emit("agentSkillProfiles:updated", update.agentSkillProfiles);
    }
    this.agentSkillProfiles = update.agentSkillProfiles;

    if (update.learningEvents.length !== this.learningEvents.length) EventBus.emit("learningEvents:updated", update.learningEvents);
    this.learningEvents = update.learningEvents;

    if (update.decisionVault.length !== this.decisionVault.length) EventBus.emit("decisionVault:updated", update.decisionVault);
    this.decisionVault = update.decisionVault;

    if (update.warRoomSessions.length !== this.warRoomSessions.length) EventBus.emit("warRoomSessions:updated", update.warRoomSessions);
    this.warRoomSessions = update.warRoomSessions;

    if (update.portfolioIntelligence !== this.portfolioIntelligence) EventBus.emit("portfolioIntelligence:updated", update.portfolioIntelligence);
    this.portfolioIntelligence = update.portfolioIntelligence;

    if (update.economicIntelligence !== this.economicIntelligence) EventBus.emit("economicIntelligence:updated", update.economicIntelligence);
    this.economicIntelligence = update.economicIntelligence;

    if (update.economicIntelligenceReports.length !== this.economicIntelligenceReports.length) {
      EventBus.emit("economicIntelligenceReports:updated", update.economicIntelligenceReports);
    }
    this.economicIntelligenceReports = update.economicIntelligenceReports;

    if (update.blackSwanIntelligence !== this.blackSwanIntelligence) EventBus.emit("blackSwanIntelligence:updated", update.blackSwanIntelligence);
    this.blackSwanIntelligence = update.blackSwanIntelligence;

    if (update.blackSwanReports.length !== this.blackSwanReports.length) {
      EventBus.emit("blackSwanReports:updated", update.blackSwanReports);
    }
    this.blackSwanReports = update.blackSwanReports;

    if (update.defensiveMode !== this.defensiveMode) EventBus.emit("defensiveMode:updated", update.defensiveMode);
    this.defensiveMode = update.defensiveMode;

    if (update.blackSwanEvents.length !== this.blackSwanEvents.length) {
      EventBus.emit("blackSwanEvents:updated", update.blackSwanEvents);
    }
    this.blackSwanEvents = update.blackSwanEvents;

    if (update.institutionalSurvivalScore !== this.institutionalSurvivalScore) {
      EventBus.emit("institutionalSurvivalScore:updated", update.institutionalSurvivalScore);
    }
    this.institutionalSurvivalScore = update.institutionalSurvivalScore;

    if (update.tradingModes !== this.tradingModes) EventBus.emit("tradingModes:updated", update.tradingModes);
    this.tradingModes = update.tradingModes;

    if (update.dailyCircuitBreaker !== this.dailyCircuitBreaker) EventBus.emit("dailyCircuitBreaker:updated", update.dailyCircuitBreaker);
    this.dailyCircuitBreaker = update.dailyCircuitBreaker;

    if (update.losingStreak !== this.losingStreak) EventBus.emit("losingStreak:updated", update.losingStreak);
    this.losingStreak = update.losingStreak;

    if (update.behavioralCircuitBreaker !== this.behavioralCircuitBreaker) {
      EventBus.emit("behavioralCircuitBreaker:updated", update.behavioralCircuitBreaker);
    }
    this.behavioralCircuitBreaker = update.behavioralCircuitBreaker;

    if (update.recoveryBriefings.length !== this.recoveryBriefings.length) {
      EventBus.emit("recoveryBriefings:updated", update.recoveryBriefings);
    }
    this.recoveryBriefings = update.recoveryBriefings;

    // Unlike recoveryBriefings/evolutionReports below (append-only logs,
    // where a length-diff is a real "did anything change" check), an
    // existing proposal's own status can mutate in place (CEO approve/
    // reject/mark-implemented) without the array's length changing — so
    // this always emits, the same convention tradingModes above already
    // uses for its own in-place-mutable object.
    if (update.selfImprovementProposals !== this.selfImprovementProposals) {
      EventBus.emit("selfImprovementProposals:updated", update.selfImprovementProposals);
    }
    this.selfImprovementProposals = update.selfImprovementProposals;

    if (update.evolutionReports.length !== this.evolutionReports.length) {
      EventBus.emit("evolutionReports:updated", update.evolutionReports);
    }
    this.evolutionReports = update.evolutionReports;

    if (update.visionBoard !== this.visionBoard) EventBus.emit("visionBoard:updated", update.visionBoard);
    this.visionBoard = update.visionBoard;

    if (update.travelMode !== this.travelMode) EventBus.emit("travelMode:updated", update.travelMode);
    this.travelMode = update.travelMode;

    if (update.travelModeBriefings.length !== this.travelModeBriefings.length) {
      EventBus.emit("travelModeBriefings:updated", update.travelModeBriefings);
    }
    this.travelModeBriefings = update.travelModeBriefings;

    if (update.talent !== this.talent) EventBus.emit("talent:updated", update.talent);
    this.talent = update.talent;

    if (update.constitution !== this.constitution) EventBus.emit("constitution:updated", update.constitution);
    this.constitution = update.constitution;

    if (update.reasoningChallenges.length !== this.reasoningChallenges.length) {
      EventBus.emit("reasoningChallenges:updated", update.reasoningChallenges);
    }
    this.reasoningChallenges = update.reasoningChallenges;

    if (update.reasoningLabState !== this.reasoningLabState) EventBus.emit("reasoningLabState:updated", update.reasoningLabState);
    this.reasoningLabState = update.reasoningLabState;

    if (update.executiveMeetingLog.length !== this.executiveMeetingLog.length) {
      EventBus.emit("executiveMeetingLog:updated", update.executiveMeetingLog);
    }
    this.executiveMeetingLog = update.executiveMeetingLog;

    if (update.departmentSelfEvaluations.length !== this.departmentSelfEvaluations.length) {
      EventBus.emit("departmentSelfEvaluations:updated", update.departmentSelfEvaluations);
    }
    this.departmentSelfEvaluations = update.departmentSelfEvaluations;

    if (update.reflectionSessions.length !== this.reflectionSessions.length) {
      EventBus.emit("reflectionSessions:updated", update.reflectionSessions);
    }
    this.reflectionSessions = update.reflectionSessions;

    if (update.wisdomState !== this.wisdomState) EventBus.emit("wisdomState:updated", update.wisdomState);
    this.wisdomState = update.wisdomState;

    if (update.questionArchive.length !== this.questionArchive.length) {
      EventBus.emit("questionArchive:updated", update.questionArchive);
    }
    this.questionArchive = update.questionArchive;

    if (update.thinkingProfiles !== this.thinkingProfiles) EventBus.emit("thinkingProfiles:updated", update.thinkingProfiles);
    this.thinkingProfiles = update.thinkingProfiles;

    if (update.mentorState !== this.mentorState) EventBus.emit("mentorState:updated", update.mentorState);
    this.mentorState = update.mentorState;

    if (update.foundationalMentorState !== this.foundationalMentorState) {
      EventBus.emit("foundationalMentorState:updated", update.foundationalMentorState);
    }
    this.foundationalMentorState = update.foundationalMentorState;

    if (update.founderState !== this.founderState) EventBus.emit("founderState:updated", update.founderState);
    this.founderState = update.founderState;

    if (update.treasury !== this.treasury) EventBus.emit("treasury:updated", update.treasury);
    this.treasury = update.treasury;

    if (update.accounts !== this.accounts) EventBus.emit("accounts:updated", update.accounts);
    this.accounts = update.accounts;

    if (update.activeAccountId !== this.activeAccountId) EventBus.emit("activeAccount:updated", update.activeAccountId);
    this.activeAccountId = update.activeAccountId;

    if (update.calendar !== this.calendar) EventBus.emit("calendar:updated", update.calendar);
    this.calendar = update.calendar;

    if (update.blackBox !== this.blackBox) EventBus.emit("blackBox:updated", update.blackBox);
    this.blackBox = update.blackBox;

    if (update.agentEnergy !== this.agentEnergy) EventBus.emit("agentEnergy:updated", update.agentEnergy);
    this.agentEnergy = update.agentEnergy;

    if (update.signalCalibration !== this.signalCalibration) EventBus.emit("signalCalibration:updated", update.signalCalibration);
    this.signalCalibration = update.signalCalibration;

    if (update.playerVsAi !== this.playerVsAi) EventBus.emit("playerVsAi:updated", update.playerVsAi);
    this.playerVsAi = update.playerVsAi;

    if (update.education !== this.education) EventBus.emit("education:updated", update.education);
    this.education = update.education;

    if (update.viewedTradeNotificationIds !== this.viewedTradeNotificationIds) EventBus.emit("tradeNotifications:updated", update.viewedTradeNotificationIds);
    this.viewedTradeNotificationIds = update.viewedTradeNotificationIds;
  }

  // v0.7 — Save Architecture Redesign Phase 2: GET /api/load now returns
  // only the core modules (backend/app/save_modules.py); the archive
  // modules (trade_history/knowledge_archive/academy — decisions, debates,
  // caseStudies, decisionVault, questionArchive, hallOfFame, academyCompletedProjects,
  // agentKnowledge, ...) come back as real empty arrays/dicts, not omitted
  // fields, so every plain assignment below stays valid with no optional
  // handling needed. Those fields get their real data moments later from
  // the WebSocket tick broadcast (net/socket.ts calls applyServerUpdate()
  // above, unconditionally, on every tick) — this method only runs once at
  // boot, so no panel is ever stuck showing an empty archive.
  static loadFromSave(save: NexusSnapshot): void {
    this.tasks = save.tasks;
    this.whiteboards = save.whiteboards;
    this.meeting = save.meeting;
    this.news = save.news;
    this.research = save.research;
    this.watchlist = save.watchlist;
    this.memory = save.memory;
    this.meetingMinutes = save.meetingMinutes;
    this.paperPortfolio = save.paperPortfolio;
    this.strategies = save.strategies;
    this.backtestSessions = save.backtestSessions;
    this.simulationResults = save.simulationResults;
    this.strategyReports = save.strategyReports;
    this.strategyReviews = save.strategyReviews;
    this.strategyModelValidations = save.strategyModelValidations;
    this.strategyMonteCarloResults = save.strategyMonteCarloResults;
    this.strategyRegimeTests = save.strategyRegimeTests;
    this.strategyLiquidityValidations = save.strategyLiquidityValidations;
    this.strategyExecutiveReviews = save.strategyExecutiveReviews;
    this.strategyFounderApprovals = save.strategyFounderApprovals;
    this.strategyHealthAssessments = save.strategyHealthAssessments;
    this.strategyHallOfFame = save.strategyHallOfFame;
    this.strategyFailedArchive = save.strategyFailedArchive;
    this.hallOfFame = save.hallOfFame;
    this.coachReports = save.coachReports;
    this.companyScore = save.companyScore;
    this.performanceSnapshots = save.performanceSnapshots;
    this.riskLimits = save.riskLimits;
    this.riskWarnings = save.riskWarnings;
    this.emergencyStop = save.emergencyStop;
    this.scannerAlerts = save.scannerAlerts;
    this.decisions = save.decisions;
    this.tradeProposals = save.tradeProposals;
    this.ceoDecisions = save.ceoDecisions;
    this.debates = save.debates;
    this.challengeReports = save.challengeReports;
    this.innovationState = save.innovationState;
    this.gatekeeperRejections = save.gatekeeperRejections;
    this.opportunityRejections = save.opportunityRejections;
    this.marketEnvironment = save.marketEnvironment;
    this.marketIntelligence = save.marketIntelligence;
    this.marketIntelligenceReports = save.marketIntelligenceReports;
    this.marketIntelligenceLearning = save.marketIntelligenceLearning;
    this.companyHealth = save.companyHealth;
    this.companyHealthDelta = save.companyHealthDelta ?? null;
    this.companyDna = save.companyDna;
    this.dailyObjectiveStatus = save.dailyObjectiveStatus;
    this.riskBudgetStatus = save.riskBudgetStatus;
    this.executiveReviews = save.executiveReviews;
    this.boardReports = save.boardReports;
    this.academyProjects = save.academyProjects;
    this.academyCompletedProjects = save.academyCompletedProjects;
    this.goals = save.goals;
    this.strategicReviews = save.strategicReviews;
    this.agentKnowledge = save.agentKnowledge;
    this.academyState = save.academyState;
    this.disciplineReviews = save.disciplineReviews;
    this.caseStudies = save.caseStudies;
    this.institutionalMemory = save.institutionalMemory ?? [];
    this.agentPerformanceReviews = save.agentPerformanceReviews ?? [];
    this.agentSkillProfiles = save.agentSkillProfiles ?? [];
    this.learningEvents = save.learningEvents;
    this.decisionVault = save.decisionVault;
    this.warRoomSessions = save.warRoomSessions;
    this.portfolioIntelligence = save.portfolioIntelligence;
    this.economicIntelligence = save.economicIntelligence;
    this.economicIntelligenceReports = save.economicIntelligenceReports;
    this.blackSwanIntelligence = save.blackSwanIntelligence;
    this.blackSwanReports = save.blackSwanReports;
    this.defensiveMode = save.defensiveMode;
    this.blackSwanEvents = save.blackSwanEvents;
    this.institutionalSurvivalScore = save.institutionalSurvivalScore;
    this.tradingModes = save.tradingModes;
    this.dailyCircuitBreaker = save.dailyCircuitBreaker;
    this.losingStreak = save.losingStreak;
    this.behavioralCircuitBreaker = save.behavioralCircuitBreaker;
    this.recoveryBriefings = save.recoveryBriefings;
    this.selfImprovementProposals = save.selfImprovementProposals;
    this.evolutionReports = save.evolutionReports;
    this.visionBoard = save.visionBoard;
    this.travelMode = save.travelMode;
    this.travelModeBriefings = save.travelModeBriefings;
    this.talent = save.talent;
    this.constitution = save.constitution;
    this.reasoningChallenges = save.reasoningChallenges;
    this.reasoningLabState = save.reasoningLabState;
    this.executiveMeetingLog = save.executiveMeetingLog;
    this.departmentSelfEvaluations = save.departmentSelfEvaluations;
    this.reflectionSessions = save.reflectionSessions;
    this.wisdomState = save.wisdomState;
    this.questionArchive = save.questionArchive;
    this.thinkingProfiles = save.thinkingProfiles;
    this.mentorState = save.mentorState;
    this.foundationalMentorState = save.foundationalMentorState;
    this.founderState = save.founderState;
    this.treasury = save.treasury;
    this.accounts = save.accounts;
    this.activeAccountId = save.activeAccountId;
    this.calendar = save.calendar;
    this.blackBox = save.blackBox;
    this.agentEnergy = save.agentEnergy;
    this.signalCalibration = save.signalCalibration;
    this.playerVsAi = save.playerVsAi;
    this.education = save.education;
    this.viewedTradeNotificationIds = save.viewedTradeNotificationIds;
    this.hydrated = true;
  }
}
