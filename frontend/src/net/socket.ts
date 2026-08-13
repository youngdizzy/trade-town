import type {
  AcademyProject,
  AcademyState,
  Account,
  AgentEnergy,
  AgentId,
  AgentKnowledgeState,
  AgentState,
  BacktestSession,
  BlackBoxState,
  BlackSwanEventRecord,
  BlackSwanIntelligenceState,
  BlackSwanReport,
  CalendarState,
  CaseStudy,
  CeoDecisionRecord,
  ChallengeReport,
  CoachReport,
  CompanyDNA,
  CompanyHealth,
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
  EducationProgress,
  PlayerVsAiState,
  ModelValidationReport,
  ReasoningChallenge,
  ReasoningLabState,
  ReflectionSession,
  RiskBudgetStatus,
  RiskLimits,
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
import { EventBus } from "@/game/systems/EventBus";
import { TimeManager } from "@/game/systems/TimeManager";
import { NPCManager } from "@/game/systems/NPCManager";
import { NexusManager } from "@/game/systems/NexusManager";

type ServerMessage =
  | {
      type: "state";
      time: TimeState;
      agents: Record<AgentId, AgentState>;
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
      executiveMeetingLog: ExecutiveMeetingLogEntry[];
      departmentSelfEvaluations: DepartmentSelfEvaluation[];
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
    }
  | { type: "pong" };

function resolveWsUrl(): string {
  if (import.meta.env.VITE_WS_URL) return import.meta.env.VITE_WS_URL;
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${window.location.host}/ws`;
}

/**
 * Maintains a live WebSocket connection to the backend simulation loop.
 * The backend keeps ticking Scout's research/schedule even when no client
 * is connected; this socket is what makes the office feel "alive" by
 * streaming those updates instead of requiring the client to poll.
 * Falls back to local simulation (NPCManager/TimeManager offline mode) if
 * the connection can't be established, with exponential backoff retries.
 */
export class GameSocket {
  private ws: WebSocket | null = null;
  private reconnectAttempt = 0;
  private reconnectTimer: number | null = null;
  private closedByClient = false;

  connect(): void {
    this.closedByClient = false;
    this.open();
  }

  disconnect(): void {
    this.closedByClient = true;
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.ws?.close();
    this.ws = null;
  }

  private open(): void {
    const url = resolveWsUrl();
    const ws = new WebSocket(url);
    this.ws = ws;

    ws.onopen = () => {
      this.reconnectAttempt = 0;
      EventBus.emit("net:status", { connected: true });
      TimeManager.stopLocalFallback();
      NPCManager.stopOfflineFallback();
    };

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data as string) as ServerMessage;
        if (msg.type === "state") {
          TimeManager.setFromServer(msg.time);
          NPCManager.applyServerUpdate(msg.agents);
          NexusManager.applyServerUpdate({
            tasks: msg.tasks,
            whiteboards: msg.whiteboards,
            meeting: msg.meeting,
            news: msg.news,
            research: msg.research,
            watchlist: msg.watchlist,
            memory: msg.memory,
            meetingMinutes: msg.meetingMinutes,
            paperPortfolio: msg.paperPortfolio,
            strategies: msg.strategies,
            backtestSessions: msg.backtestSessions,
            simulationResults: msg.simulationResults,
            strategyReports: msg.strategyReports,
            strategyReviews: msg.strategyReviews,
            strategyModelValidations: msg.strategyModelValidations,
            strategyMonteCarloResults: msg.strategyMonteCarloResults,
            strategyRegimeTests: msg.strategyRegimeTests,
            strategyLiquidityValidations: msg.strategyLiquidityValidations,
            strategyExecutiveReviews: msg.strategyExecutiveReviews,
            strategyFounderApprovals: msg.strategyFounderApprovals,
            strategyHealthAssessments: msg.strategyHealthAssessments,
            strategyHallOfFame: msg.strategyHallOfFame,
            strategyFailedArchive: msg.strategyFailedArchive,
            hallOfFame: msg.hallOfFame,
            coachReports: msg.coachReports,
            companyScore: msg.companyScore,
            performanceSnapshots: msg.performanceSnapshots,
            riskLimits: msg.riskLimits,
            riskWarnings: msg.riskWarnings,
            emergencyStop: msg.emergencyStop,
            scannerAlerts: msg.scannerAlerts,
            decisions: msg.decisions,
            tradeProposals: msg.tradeProposals,
            ceoDecisions: msg.ceoDecisions,
            debates: msg.debates,
            challengeReports: msg.challengeReports,
            innovationState: msg.innovationState,
            gatekeeperRejections: msg.gatekeeperRejections,
            opportunityRejections: msg.opportunityRejections,
            marketEnvironment: msg.marketEnvironment,
            marketIntelligence: msg.marketIntelligence,
            marketIntelligenceReports: msg.marketIntelligenceReports,
            marketIntelligenceLearning: msg.marketIntelligenceLearning,
            companyHealth: msg.companyHealth,
            companyDna: msg.companyDna,
            dailyObjectiveStatus: msg.dailyObjectiveStatus,
            riskBudgetStatus: msg.riskBudgetStatus,
            executiveReviews: msg.executiveReviews,
            boardReports: msg.boardReports,
            academyProjects: msg.academyProjects,
            academyCompletedProjects: msg.academyCompletedProjects,
            goals: msg.goals,
            strategicReviews: msg.strategicReviews,
            agentKnowledge: msg.agentKnowledge,
            academyState: msg.academyState,
            disciplineReviews: msg.disciplineReviews,
            caseStudies: msg.caseStudies,
            decisionVault: msg.decisionVault,
            warRoomSessions: msg.warRoomSessions,
            portfolioIntelligence: msg.portfolioIntelligence,
            economicIntelligence: msg.economicIntelligence,
            economicIntelligenceReports: msg.economicIntelligenceReports,
            blackSwanIntelligence: msg.blackSwanIntelligence,
            blackSwanReports: msg.blackSwanReports,
            defensiveMode: msg.defensiveMode,
            blackSwanEvents: msg.blackSwanEvents,
            institutionalSurvivalScore: msg.institutionalSurvivalScore,
            tradingModes: msg.tradingModes,
            dailyCircuitBreaker: msg.dailyCircuitBreaker,
            losingStreak: msg.losingStreak,
            behavioralCircuitBreaker: msg.behavioralCircuitBreaker,
            recoveryBriefings: msg.recoveryBriefings,
            selfImprovementProposals: msg.selfImprovementProposals,
            evolutionReports: msg.evolutionReports,
            visionBoard: msg.visionBoard,
            travelMode: msg.travelMode,
            travelModeBriefings: msg.travelModeBriefings,
            talent: msg.talent,
            constitution: msg.constitution,
            reasoningChallenges: msg.reasoningChallenges,
            reasoningLabState: msg.reasoningLabState,
            reflectionSessions: msg.reflectionSessions,
            wisdomState: msg.wisdomState,
            executiveMeetingLog: msg.executiveMeetingLog,
            departmentSelfEvaluations: msg.departmentSelfEvaluations,
            questionArchive: msg.questionArchive,
            thinkingProfiles: msg.thinkingProfiles,
            mentorState: msg.mentorState,
            foundationalMentorState: msg.foundationalMentorState,
            founderState: msg.founderState,
            treasury: msg.treasury,
            accounts: msg.accounts,
            activeAccountId: msg.activeAccountId,
            calendar: msg.calendar,
            blackBox: msg.blackBox,
            agentEnergy: msg.agentEnergy,
            signalCalibration: msg.signalCalibration,
            playerVsAi: msg.playerVsAi,
            education: msg.education,
            viewedTradeNotificationIds: msg.viewedTradeNotificationIds,
          });
        }
      } catch (err) {
        console.warn("[GameSocket] Failed to parse message", err);
      }
    };

    ws.onclose = () => {
      EventBus.emit("net:status", { connected: false });
      TimeManager.startLocalFallback();
      NPCManager.startOfflineFallback(() => TimeManager.current);
      if (!this.closedByClient) this.scheduleReconnect();
    };

    ws.onerror = () => {
      ws.close();
    };
  }

  private scheduleReconnect(): void {
    this.reconnectAttempt += 1;
    const delay = Math.min(1000 * 2 ** this.reconnectAttempt, 15000);
    this.reconnectTimer = window.setTimeout(() => this.open(), delay);
  }
}

export const gameSocket = new GameSocket();
