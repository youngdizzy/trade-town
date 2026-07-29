import type {
  AcademyProject,
  AcademyState,
  AgentEnergy,
  AgentId,
  AgentKnowledgeState,
  BacktestSession,
  BlackBoxState,
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
  CalendarState,
  TreasuryState,
  RiskLimits,
  EducationProgress,
  PlayerVsAiState,
  ReasoningChallenge,
  ReasoningLabState,
  ReflectionSession,
  RiskWarning,
  ScannerAlert,
  SignalCalibrationState,
  SimulationResult,
  Strategy,
  Task,
  ThinkingProfile,
  TradeDecision,
  TradeProposal,
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
    maxDrawdownPct: 20,
    maxOpenPositions: 8,
    maxSectorConcentrationPct: 30,
    riskPerTradePct: 2,
  };
  private static riskWarnings: RiskWarning[] = [];
  private static scannerAlerts: ScannerAlert[] = [];
  private static decisions: TradeDecision[] = [];
  private static tradeProposals: TradeProposal[] = [];
  private static ceoDecisions: CeoDecisionRecord[] = [];
  private static debates: Debate[] = [];
  private static challengeReports: ChallengeReport[] = [];
  private static innovationState: Record<AgentId, InnovationState> = {} as Record<AgentId, InnovationState>;
  private static gatekeeperRejections: GatekeeperRejection[] = [];
  private static marketEnvironment: MarketEnvironmentState = {
    current: "sideways",
    label: "SIDEWAYS",
    detail: "No data yet.",
    changedSimMinutes: 0,
    updatedAt: new Date().toISOString(),
    timeline: [],
  };
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
    officeExpansion: 0,
    educationProgress: 0,
    teamChemistry: 50,
    recommendations: [],
    updatedAt: new Date().toISOString(),
  };
  private static companyDna: CompanyDNA = {
    traits: [],
    summary: "",
    sampleSize: 0,
    updatedAt: new Date().toISOString(),
  };
  private static executiveReviews: ExecutiveReview[] = [];
  private static academyProjects: AcademyProject[] = [];
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
  private static reasoningChallenges: ReasoningChallenge[] = [];
  private static reasoningLabState: ReasoningLabState = {
    level: 1,
    levelLabel: "Foundations",
    completedChallengeCount: 0,
    updatedAt: new Date().toISOString(),
  };
  private static reflectionSessions: ReflectionSession[] = [];
  private static wisdomState: WisdomState = { score: 0, tier: "young_company", tierLabel: "Young Company", factors: [], updatedAt: new Date().toISOString() };
  private static questionArchive: QuestionOfTheDay[] = [];
  private static thinkingProfiles: Record<AgentId, ThinkingProfile> = {} as Record<AgentId, ThinkingProfile>;
  private static mentorState: MentorState = { tier: 0, tierLabel: "New Tradition", questionsAsked: 0, updatedAt: new Date().toISOString() };
  private static founderState: FounderState = { retired: false, retiredAt: null, log: [], councilSessions: [], updatedAt: new Date().toISOString() };
  private static treasury: TreasuryState = { balance: 0, lifetimeDeposits: 0, largestBalance: 0, transactions: [], savingsRules: [], monthlyReports: [], updatedAt: new Date().toISOString() };
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

  static getCompanyHealth(): CompanyHealth {
    return this.companyHealth;
  }

  static getCompanyDna(): CompanyDNA {
    return this.companyDna;
  }

  static getExecutiveReviews(): ExecutiveReview[] {
    return this.executiveReviews;
  }

  static getAcademyProjects(): AcademyProject[] {
    return this.academyProjects;
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

  static getReasoningChallenges(): ReasoningChallenge[] {
    return this.reasoningChallenges;
  }

  static getReasoningLabState(): ReasoningLabState {
    return this.reasoningLabState;
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

    if (update.marketEnvironment !== this.marketEnvironment) EventBus.emit("marketEnvironment:updated", update.marketEnvironment);
    this.marketEnvironment = update.marketEnvironment;

    if (update.companyHealth !== this.companyHealth) EventBus.emit("companyHealth:updated", update.companyHealth);
    this.companyHealth = update.companyHealth;

    if (update.companyDna !== this.companyDna) EventBus.emit("companyDna:updated", update.companyDna);
    this.companyDna = update.companyDna;

    if (update.executiveReviews.length !== this.executiveReviews.length) EventBus.emit("executiveReviews:updated", update.executiveReviews);
    this.executiveReviews = update.executiveReviews;

    if (update.academyProjects !== this.academyProjects) EventBus.emit("academyProjects:updated", update.academyProjects);
    this.academyProjects = update.academyProjects;

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

    if (update.reasoningChallenges.length !== this.reasoningChallenges.length) {
      EventBus.emit("reasoningChallenges:updated", update.reasoningChallenges);
    }
    this.reasoningChallenges = update.reasoningChallenges;

    if (update.reasoningLabState !== this.reasoningLabState) EventBus.emit("reasoningLabState:updated", update.reasoningLabState);
    this.reasoningLabState = update.reasoningLabState;

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

    if (update.founderState !== this.founderState) EventBus.emit("founderState:updated", update.founderState);
    this.founderState = update.founderState;

    if (update.treasury !== this.treasury) EventBus.emit("treasury:updated", update.treasury);
    this.treasury = update.treasury;

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
  // caseStudies, questionArchive, hallOfFame, academyCompletedProjects,
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
    this.hallOfFame = save.hallOfFame;
    this.coachReports = save.coachReports;
    this.companyScore = save.companyScore;
    this.performanceSnapshots = save.performanceSnapshots;
    this.riskLimits = save.riskLimits;
    this.riskWarnings = save.riskWarnings;
    this.scannerAlerts = save.scannerAlerts;
    this.decisions = save.decisions;
    this.tradeProposals = save.tradeProposals;
    this.ceoDecisions = save.ceoDecisions;
    this.debates = save.debates;
    this.challengeReports = save.challengeReports;
    this.innovationState = save.innovationState;
    this.gatekeeperRejections = save.gatekeeperRejections;
    this.marketEnvironment = save.marketEnvironment;
    this.companyHealth = save.companyHealth;
    this.companyDna = save.companyDna;
    this.executiveReviews = save.executiveReviews;
    this.academyProjects = save.academyProjects;
    this.academyCompletedProjects = save.academyCompletedProjects;
    this.agentKnowledge = save.agentKnowledge;
    this.academyState = save.academyState;
    this.disciplineReviews = save.disciplineReviews;
    this.caseStudies = save.caseStudies;
    this.reasoningChallenges = save.reasoningChallenges;
    this.reasoningLabState = save.reasoningLabState;
    this.reflectionSessions = save.reflectionSessions;
    this.wisdomState = save.wisdomState;
    this.questionArchive = save.questionArchive;
    this.thinkingProfiles = save.thinkingProfiles;
    this.mentorState = save.mentorState;
    this.founderState = save.founderState;
    this.treasury = save.treasury;
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
