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
  CaseStudy,
  CeoDecisionRecord,
  ChallengeReport,
  CoachReport,
  CompanyDNA,
  CompanyHealth,
  CompanyScore,
  Debate,
  DisciplineReview,
  ExecutiveReview,
  FounderState,
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
  EducationProgress,
  PlayerVsAiState,
  ReasoningChallenge,
  ReasoningLabState,
  ReflectionSession,
  RiskLimits,
  RiskWarning,
  ScannerAlert,
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
      hallOfFame: HallOfFameEntry[];
      coachReports: CoachReport[];
      companyScore: CompanyScore;
      performanceSnapshots: PerformanceSnapshot[];
      riskLimits: RiskLimits;
      riskWarnings: RiskWarning[];
      scannerAlerts: ScannerAlert[];
      decisions: TradeDecision[];
      tradeProposals: TradeProposal[];
      ceoDecisions: CeoDecisionRecord[];
      debates: Debate[];
      challengeReports: ChallengeReport[];
      innovationState: Record<AgentId, InnovationState>;
      gatekeeperRejections: GatekeeperRejection[];
      marketEnvironment: MarketEnvironmentState;
      companyHealth: CompanyHealth;
      companyDna: CompanyDNA;
      executiveReviews: ExecutiveReview[];
      academyProjects: AcademyProject[];
      academyCompletedProjects: AcademyProject[];
      agentKnowledge: Record<AgentId, AgentKnowledgeState>;
      academyState: AcademyState;
      disciplineReviews: DisciplineReview[];
      caseStudies: CaseStudy[];
      talent: TalentState;
      reasoningChallenges: ReasoningChallenge[];
      reasoningLabState: ReasoningLabState;
      reflectionSessions: ReflectionSession[];
      wisdomState: WisdomState;
      questionArchive: QuestionOfTheDay[];
      thinkingProfiles: Record<AgentId, ThinkingProfile>;
      mentorState: MentorState;
      founderState: FounderState;
      treasury: TreasuryState;
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
            hallOfFame: msg.hallOfFame,
            coachReports: msg.coachReports,
            companyScore: msg.companyScore,
            performanceSnapshots: msg.performanceSnapshots,
            riskLimits: msg.riskLimits,
            riskWarnings: msg.riskWarnings,
            scannerAlerts: msg.scannerAlerts,
            decisions: msg.decisions,
            tradeProposals: msg.tradeProposals,
            ceoDecisions: msg.ceoDecisions,
            debates: msg.debates,
            challengeReports: msg.challengeReports,
            innovationState: msg.innovationState,
            gatekeeperRejections: msg.gatekeeperRejections,
            marketEnvironment: msg.marketEnvironment,
            companyHealth: msg.companyHealth,
            companyDna: msg.companyDna,
            executiveReviews: msg.executiveReviews,
            academyProjects: msg.academyProjects,
            academyCompletedProjects: msg.academyCompletedProjects,
            agentKnowledge: msg.agentKnowledge,
            academyState: msg.academyState,
            disciplineReviews: msg.disciplineReviews,
            caseStudies: msg.caseStudies,
            talent: msg.talent,
            reasoningChallenges: msg.reasoningChallenges,
            reasoningLabState: msg.reasoningLabState,
            reflectionSessions: msg.reflectionSessions,
            wisdomState: msg.wisdomState,
            questionArchive: msg.questionArchive,
            thinkingProfiles: msg.thinkingProfiles,
            mentorState: msg.mentorState,
            founderState: msg.founderState,
            treasury: msg.treasury,
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
