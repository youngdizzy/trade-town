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
  ConstitutionState,
  DailyObjectiveStatus,
  Debate,
  DepartmentSelfEvaluation,
  DisciplineReview,
  ExecutiveMeetingLogEntry,
  ExecutiveReview,
  FounderState,
  FoundationalMentorState,
  GatekeeperRejection,
  HallOfFameEntry,
  InnovationState,
  MarketEnvironmentState,
  MarketIntelligenceLearningEntry,
  MarketIntelligenceReport,
  MarketIntelligenceState,
  MeetingMinutes,
  MeetingState,
  MemoryRecord,
  MentorState,
  NewsItem,
  PaperPortfolio,
  PerformanceSnapshot,
  QuestionOfTheDay,
  ResearchItem,
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
  StrategyReport,
  StrategyReview,
  TalentState,
  Task,
  ThinkingProfile,
  TimeState,
  TradeDecision,
  TradeProposal,
  TreasuryState,
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
  marketIntelligence: MarketIntelligenceState;
  marketIntelligenceReports: MarketIntelligenceReport[];
  marketIntelligenceLearning: MarketIntelligenceLearningEntry[];
  companyHealth: CompanyHealth;
  companyDna: CompanyDNA;
  dailyObjectiveStatus: DailyObjectiveStatus;
  executiveReviews: ExecutiveReview[];
  academyProjects: AcademyProject[];
  academyCompletedProjects: AcademyProject[];
  agentKnowledge: Record<AgentId, AgentKnowledgeState>;
  academyState: AcademyState;
  disciplineReviews: DisciplineReview[];
  caseStudies: CaseStudy[];
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
    strategyReports: [],
    strategyReviews: [],
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
      dailyProfitTargetPct: 3,
      maxTradesPerDay: 6,
    },
    riskWarnings: [],
    scannerAlerts: [],
    decisions: [],
    tradeProposals: [],
    ceoDecisions: [],
    debates: [],
    challengeReports: [],
    innovationState: {} as Record<AgentId, InnovationState>,
    gatekeeperRejections: [],
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
      officeExpansion: 0,
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
    },
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
    executiveReviews: [],
    academyProjects: [],
    academyCompletedProjects: [],
    agentKnowledge: {} as Record<AgentId, AgentKnowledgeState>,
    academyState: { level: 1, levelLabel: "Training Room", totalPoints: 0, completedProjectCount: 0, updatedAt: new Date().toISOString() },
    disciplineReviews: [],
    caseStudies: [],
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
    foundationalMentorState: { mentors: [], progress: {}, ceoProgress: {}, activeMentorId: null, roadmapOrder: [], customLessonAnswers: {}, updatedAt: new Date().toISOString() },
    founderState: { retired: false, retiredAt: null, log: [], councilSessions: [], updatedAt: new Date().toISOString() },
    treasury: { balance: 0, lifetimeDeposits: 0, largestBalance: 0, transactions: [], savingsRules: [], monthlyReports: [], updatedAt: new Date().toISOString() },
    calendar: { systemEvents: [], playerEvents: [], updatedAt: new Date().toISOString() },
    blackBox: { active: null, archive: [], reviews: [], viewedBreakthroughIds: [], updatedAt: new Date().toISOString() },
    agentEnergy: { current: 100, cap: 100, updatedAt: new Date().toISOString() },
    signalCalibration: { unlockedLevel: 1, attempts: [], correctCount: 0, totalCount: 0 },
    playerVsAi: { rounds: [], playerCorrectCount: 0, aiCorrectCount: 0, totalCount: 0 },
    education: { viewedLessonIds: [], completedLessonIds: [], quizAttempts: 0, correctQuizAttempts: 0 },
    viewedTradeNotificationIds: [],
    settings: { musicVolume: 0.5, sfxVolume: 0.7, autosaveIntervalSec: 60, showFps: false, operatingMode: "learning", companyPriority: "balanced", workMode: "work", ceoAcademyLearningMode: false },
    dialogue: { open: false, speaker: "", lines: [], index: 0 },
    paused: false,
    settingsOpen: false,
    newspaperOpen: false,
    companyMemoryOpen: false,
    coachDashboardOpen: false,
    brainRoomHudOpen: false,
    commandCenterOpen: false,
    commandCenterMode: "quick",
    campusMapOpen: false,
    breakthroughOpen: false,
    executiveVotingOpen: false,
    executiveVotingProposalId: null,
    pendingInspectDecision: null,
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
    const OVERLAY_KEYS = ["newspaperOpen", "companyMemoryOpen", "coachDashboardOpen", "brainRoomHudOpen", "commandCenterOpen", "campusMapOpen", "breakthroughOpen"] as const;
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
    EventBus.on("simulation:updated", ({ sessions, results }) => this.set({ backtestSessions: sessions, simulationResults: results }));
    EventBus.on("hallOfFame:updated", (hallOfFame) => this.set({ hallOfFame }));
    EventBus.on("coachReports:updated", (coachReports) => this.set({ coachReports }));
    EventBus.on("companyScore:updated", (companyScore) => this.set({ companyScore }));
    EventBus.on("performanceSnapshots:updated", (performanceSnapshots) => this.set({ performanceSnapshots }));
    EventBus.on("riskLimits:updated", (riskLimits) => this.set({ riskLimits }));
    EventBus.on("riskWarnings:updated", (riskWarnings) => this.set({ riskWarnings }));
    EventBus.on("scannerAlerts:updated", (scannerAlerts) => this.set({ scannerAlerts }));
    EventBus.on("decisions:updated", (decisions) => this.set({ decisions }));
    EventBus.on("tradeProposals:updated", (tradeProposals) => this.set({ tradeProposals }));
    EventBus.on("ceoDecisions:updated", (ceoDecisions) => this.set({ ceoDecisions }));
    EventBus.on("debates:updated", (debates) => this.set({ debates }));
    EventBus.on("challengeReports:updated", (challengeReports) => this.set({ challengeReports }));
    EventBus.on("innovationState:updated", (innovationState) => this.set({ innovationState }));
    EventBus.on("gatekeeperRejections:updated", (gatekeeperRejections) => this.set({ gatekeeperRejections }));
    EventBus.on("marketEnvironment:updated", (marketEnvironment) => this.set({ marketEnvironment }));
    EventBus.on("marketIntelligence:updated", (marketIntelligence) => this.set({ marketIntelligence }));
    EventBus.on("marketIntelligenceReports:updated", (marketIntelligenceReports) => this.set({ marketIntelligenceReports }));
    EventBus.on("marketIntelligenceLearning:updated", (marketIntelligenceLearning) => this.set({ marketIntelligenceLearning }));
    EventBus.on("companyHealth:updated", (companyHealth) => this.set({ companyHealth }));
    EventBus.on("companyDna:updated", (companyDna) => this.set({ companyDna }));
    EventBus.on("dailyObjectiveStatus:updated", (dailyObjectiveStatus) => this.set({ dailyObjectiveStatus }));
    EventBus.on("executiveReviews:updated", (executiveReviews) => this.set({ executiveReviews }));
    EventBus.on("academyProjects:updated", (academyProjects) => this.set({ academyProjects }));
    EventBus.on("academyCompletedProjects:updated", (academyCompletedProjects) => this.set({ academyCompletedProjects }));
    EventBus.on("agentKnowledge:updated", (agentKnowledge) => this.set({ agentKnowledge }));
    EventBus.on("academyState:updated", (academyState) => this.set({ academyState }));
    EventBus.on("disciplineReviews:updated", (disciplineReviews) => this.set({ disciplineReviews }));
    EventBus.on("caseStudies:updated", (caseStudies) => this.set({ caseStudies }));
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
}

export const gameStore = new GameStore();
