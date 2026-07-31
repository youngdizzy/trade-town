import type {
  AgentEnergy,
  AgentId,
  AnalystChoice,
  BlackBoxPriority,
  BlackBoxState,
  CalendarState,
  Candle,
  CeoDecisionRecord,
  ChallengeReport,
  ClientSaveSnapshot,
  Debate,
  EducationLesson,
  EducationProgress,
  ExecutiveRecommendation,
  FoundationalMentorId,
  FoundationalMentorState,
  FoundationalResourceType,
  GameSaveState,
  HoldReason,
  GatekeeperRejection,
  InnovationState,
  KnowledgeGraph,
  PaperPortfolio,
  PlayerEventCategory,
  PlayerVsAiPrompt,
  PlayerVsAiState,
  QuestionOfTheDay,
  SaveResponse,
  SavingsRuleType,
  SignalCalibrationState,
  SignalChallenge,
  SignalChoice,
  BacktestSession,
  ConstitutionState,
  FailedStrategyArchiveEntry,
  RiskLimits,
  Strategy,
  StrategyDossier,
  StrategyExecutiveDashboard,
  StrategyExecutiveReview,
  StrategyFounderApproval,
  StrategyHallOfFameEntry,
  StrategyReview,
  TestScenario,
  TimeAdvanceTarget,
  TradeDecision,
  TradeProposal,
  TreasuryState,
  WhatIfSimulation,
} from "@/types";

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    let detail = body;
    try {
      const parsed = JSON.parse(body) as { detail?: string };
      if (parsed.detail) detail = parsed.detail;
    } catch {
      // body wasn't JSON (or had no `detail`) — fall back to the raw text above
    }
    throw new Error(detail || `[api] ${init?.method ?? "GET"} ${path} failed: ${res.status}`);
  }
  return (await res.json()) as T;
}

export const api = {
  loadGame: () => request<GameSaveState>("/load"),
  // v0.7 — Save Architecture Redesign. Only the fields the client
  // actually owns (see types.ts's ClientSaveSnapshot) — the backend has
  // only ever read these three fields off a save POST.
  saveGame: (snapshot: ClientSaveSnapshot) =>
    request<SaveResponse>("/save", {
      method: "POST",
      body: JSON.stringify(snapshot),
    }),
  health: () => request<{ status: string }>("/health"),
  getCandles: (symbol: string, timeframe: string, limit = 150) =>
    request<Candle[]>(`/market/candles?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}&limit=${limit}`),
  getTimeframes: () => request<string[]>("/market/timeframes"),
  spendEnergy: (action: string, researchId?: string) =>
    request<{ agentEnergy: AgentEnergy }>("/energy/spend", {
      method: "POST",
      body: JSON.stringify({ action, researchId: researchId ?? null }),
    }),
  getCalibrationChallenge: (level: number) => request<SignalChallenge>(`/calibration/challenge?level=${level}`),
  submitCalibrationChoice: (challengeId: string, choice: SignalChoice) =>
    request<{ signalCalibration: SignalCalibrationState; agentEnergy: AgentEnergy }>("/calibration/submit", {
      method: "POST",
      body: JSON.stringify({ challengeId, choice }),
    }),
  getPlayerVsAiPrompt: () => request<PlayerVsAiPrompt>("/player-vs-ai/prompt"),
  submitPlayerVsAiChoice: (promptId: string, choice: SignalChoice) =>
    request<{ playerVsAi: PlayerVsAiState }>("/player-vs-ai/submit", {
      method: "POST",
      body: JSON.stringify({ promptId, choice }),
    }),
  getLessons: () => request<EducationLesson[]>("/education/lessons"),
  markLessonViewed: (lessonId: string) =>
    request<{ education: EducationProgress }>("/education/view", {
      method: "POST",
      body: JSON.stringify({ lessonId }),
    }),
  submitQuiz: (lessonId: string, selectedIndex: number) =>
    request<{ correct: boolean; correctIndex: number; correctOption: string; education: EducationProgress }>("/education/quiz", {
      method: "POST",
      body: JSON.stringify({ lessonId, selectedIndex }),
    }),
  ackTradeNotification: (tradeId: string) =>
    request<{ viewedTradeNotificationIds: string[] }>("/trades/ack", {
      method: "POST",
      body: JSON.stringify({ tradeId }),
    }),
  submitCeoDecision: (proposalId: string, choice: AnalystChoice) =>
    request<{
      tradeProposals: TradeProposal[];
      ceoDecisions: CeoDecisionRecord[];
      decisions: TradeDecision[];
      paperPortfolio: PaperPortfolio;
      gatekeeperRejections: GatekeeperRejection[];
    }>("/executive/decide", {
      method: "POST",
      body: JSON.stringify({ proposalId, choice }),
    }),
  regenerateDebate: (proposalId: string) =>
    request<{ debates: Debate[] }>("/executive/debate/regenerate", {
      method: "POST",
      body: JSON.stringify({ proposalId }),
    }),
  holdProposal: (proposalId: string, reason: HoldReason) =>
    request<{ tradeProposals: TradeProposal[] }>("/executive/hold", {
      method: "POST",
      body: JSON.stringify({ proposalId, reason }),
    }),
  regenerateChallengeReport: (proposalId: string) =>
    request<{ challengeReports: ChallengeReport[]; innovationState: Record<AgentId, InnovationState> }>("/executive/challenge/regenerate", {
      method: "POST",
      body: JSON.stringify({ proposalId }),
    }),
  getWhatIfSimulation: (symbol: string) => request<WhatIfSimulation>(`/executive/whatif?symbol=${encodeURIComponent(symbol)}`),
  getExecutiveIntelligence: (proposalId: string) => request<ExecutiveRecommendation>(`/executive/intelligence?proposalId=${encodeURIComponent(proposalId)}`),
  getKnowledgeGraph: () => request<KnowledgeGraph>("/knowledge-graph"),
  submitQotdResponse: (questionId: string, response: string) =>
    request<{ question: QuestionOfTheDay }>("/mentor/qotd/respond", {
      method: "POST",
      body: JSON.stringify({ questionId, response }),
    }),
  depositTreasury: (amount: number) =>
    request<{ treasury: TreasuryState; paperPortfolio: PaperPortfolio }>("/treasury/deposit", {
      method: "POST",
      body: JSON.stringify({ amount }),
    }),
  withdrawTreasury: (amount: number) =>
    request<{ treasury: TreasuryState; paperPortfolio: PaperPortfolio }>("/treasury/withdraw", {
      method: "POST",
      body: JSON.stringify({ amount }),
    }),
  createSavingsRule: (ruleType: SavingsRuleType, percent: number, reserveTarget: number | null) =>
    request<{ treasury: TreasuryState }>("/treasury/rules/create", {
      method: "POST",
      body: JSON.stringify({ ruleType, percent, reserveTarget }),
    }),
  toggleSavingsRule: (ruleId: string, active: boolean) =>
    request<{ treasury: TreasuryState }>("/treasury/rules/toggle", {
      method: "POST",
      body: JSON.stringify({ ruleId, active }),
    }),
  pauseAllSavingsRules: () =>
    request<{ treasury: TreasuryState }>("/treasury/rules/pause-all", {
      method: "POST",
      body: JSON.stringify({}),
    }),
  advanceTime: (target: TimeAdvanceTarget, hours?: number) =>
    request<GameSaveState>("/time/advance", {
      method: "POST",
      body: JSON.stringify({ target, hours: hours ?? null }),
    }),
  createCalendarEvent: (category: PlayerEventCategory, title: string, day: number, hour: number, minute: number) =>
    request<{ calendar: CalendarState }>("/calendar/events/create", {
      method: "POST",
      body: JSON.stringify({ category, title, day, hour, minute }),
    }),
  deleteCalendarEvent: (eventId: string) =>
    request<{ calendar: CalendarState }>("/calendar/events/delete", {
      method: "POST",
      body: JSON.stringify({ eventId }),
    }),
  fundBlackBoxProject: (amount: number) =>
    request<{ blackBox: BlackBoxState }>("/black-box/fund", {
      method: "POST",
      body: JSON.stringify({ amount }),
    }),
  pauseBlackBoxProject: () =>
    request<{ blackBox: BlackBoxState }>("/black-box/pause", { method: "POST" }),
  resumeBlackBoxProject: () =>
    request<{ blackBox: BlackBoxState }>("/black-box/resume", { method: "POST" }),
  cancelBlackBoxProject: () =>
    request<{ blackBox: BlackBoxState }>("/black-box/cancel", { method: "POST" }),
  setBlackBoxPriority: (priority: BlackBoxPriority) =>
    request<{ blackBox: BlackBoxState }>("/black-box/priority", {
      method: "POST",
      body: JSON.stringify({ priority }),
    }),
  addBlackBoxNote: (note: string) =>
    request<{ blackBox: BlackBoxState }>("/black-box/notes", {
      method: "POST",
      body: JSON.stringify({ note }),
    }),
  reassignBlackBoxSpecialist: (agentId: AgentId, newAgentId: AgentId) =>
    request<{ blackBox: BlackBoxState }>("/black-box/reassign", {
      method: "POST",
      body: JSON.stringify({ agentId, newAgentId }),
    }),
  ackBreakthrough: (reviewId: string) =>
    request<{ viewedBreakthroughIds: string[] }>("/black-box/ack-breakthrough", {
      method: "POST",
      body: JSON.stringify({ reviewId }),
    }),
  ackTalentReport: (reportId: string) =>
    request<{ viewedReportIds: string[] }>("/talent/ack-report", {
      method: "POST",
      body: JSON.stringify({ reportId }),
    }),
  queueSandboxBacktest: (strategyId: string, scenario: TestScenario, customReturnBiasPct = 0, customVolatilityBias = 1) =>
    request<{ backtestSessions: BacktestSession[] }>("/sandbox/backtest", {
      method: "POST",
      body: JSON.stringify({ strategyId, scenario, customReturnBiasPct, customVolatilityBias }),
    }),
  beginSandboxPaperTrial: (strategyId: string) =>
    request<{ strategies: Strategy[]; strategyReviews: StrategyReview[] }>("/sandbox/begin-paper-trial", {
      method: "POST",
      body: JSON.stringify({ strategyId }),
    }),
  beginSandboxLimitedLive: (strategyId: string, amount: number) =>
    request<{ strategies: Strategy[]; strategyReviews: StrategyReview[] }>("/sandbox/begin-limited-live", {
      method: "POST",
      body: JSON.stringify({ strategyId, amount }),
    }),
  requestSandboxCompanyReview: (strategyId: string) =>
    // v0.7 Feature 52 (Part 1) — this same CEO action also files the
    // richer 9-department StrategyExecutiveReview and the Founder
    // Council's real StrategyFounderApproval (see backend/app/state.py's
    // request_strategy_company_review()); at most one of each comes
    // back, since it's this one strategy's own new review moment.
    request<{ strategies: Strategy[]; strategyReviews: StrategyReview[]; strategyExecutiveReviews: StrategyExecutiveReview[]; strategyFounderApprovals: StrategyFounderApproval[] }>("/sandbox/request-review", {
      method: "POST",
      body: JSON.stringify({ strategyId }),
    }),
  decideSandboxReview: (reviewId: string, approve: boolean) =>
    request<{ strategies: Strategy[]; strategyReviews: StrategyReview[] }>("/sandbox/decide", {
      method: "POST",
      body: JSON.stringify({ reviewId, approve }),
    }),
  // v0.7 Feature 52 (Part 2) — the only real way a strategy's stage
  // ever reaches "retired". Exactly one of strategyHallOfFameEntry/
  // strategyFailedArchiveEntry comes back non-null.
  retireSandboxStrategy: (strategyId: string, reason: string) =>
    request<{ strategies: Strategy[]; strategyReviews: StrategyReview[]; strategyHallOfFameEntry: StrategyHallOfFameEntry | null; strategyFailedArchiveEntry: FailedStrategyArchiveEntry | null }>("/sandbox/retire", {
      method: "POST",
      body: JSON.stringify({ strategyId, reason }),
    }),
  // v0.7 Feature 52 (Part 1) — the brief's auto-generated "professional
  // Strategy Report." Read-only, computed fresh every call.
  getSandboxDossier: (strategyId: string) => request<StrategyDossier>(`/sandbox/dossier?strategyId=${encodeURIComponent(strategyId)}`),
  // v0.7 Feature 52 (Part 2) — the brief's Executive Dashboard. Read-only,
  // computed fresh every call.
  getSandboxDashboard: () => request<StrategyExecutiveDashboard>("/sandbox/dashboard"),
  proposeConstitutionAmendment: (title: string, text: string) =>
    request<{ constitution: ConstitutionState }>("/constitution/propose", {
      method: "POST",
      body: JSON.stringify({ title, text }),
    }),
  advanceConstitutionAmendment: (amendmentId: string) =>
    request<{ constitution: ConstitutionState }>("/constitution/advance", {
      method: "POST",
      body: JSON.stringify({ amendmentId }),
    }),
  decideConstitutionAmendment: (amendmentId: string, approve: boolean) =>
    request<{ constitution: ConstitutionState }>("/constitution/decide", {
      method: "POST",
      body: JSON.stringify({ amendmentId, approve }),
    }),
  updateRiskLimits: (
    updates: Partial<{ dailyProfitTargetPct: number; maxDailyLossPct: number; maxTradesPerDay: number; riskPerTradePct: number; maxOpenPositions: number }>,
  ) =>
    request<{ riskLimits: RiskLimits }>("/risk-limits", {
      method: "POST",
      body: JSON.stringify(updates),
    }),
  // The CEO's own entirely optional personal Learning Mode — never
  // touches real employee progress. See FoundationalMentorState's own
  // doc comment in types.ts.
  ceoViewAcademyLesson: (mentorId: FoundationalMentorId, lessonId: string) =>
    request<{ foundationalMentorState: FoundationalMentorState }>("/foundational-mentors/ceo/view", {
      method: "POST",
      body: JSON.stringify({ mentorId, lessonId }),
    }),
  ceoSubmitAcademyQuiz: (mentorId: FoundationalMentorId, lessonId: string, selectedIndex: number) =>
    request<{ foundationalMentorState: FoundationalMentorState; correct: boolean; correctIndex: number; correctOption: string }>("/foundational-mentors/ceo/quiz", {
      method: "POST",
      body: JSON.stringify({ mentorId, lessonId, selectedIndex }),
    }),
  // Real CEO management actions over the real employee cohort.
  approveAcademyGraduation: (agentId: AgentId, mentorId: FoundationalMentorId) =>
    request<{ foundationalMentorState: FoundationalMentorState; companyGraduated: boolean }>("/foundational-mentors/approve-graduation", {
      method: "POST",
      body: JSON.stringify({ agentId, mentorId }),
    }),
  revokeAcademyGraduation: (agentId: AgentId, mentorId: FoundationalMentorId) =>
    request<{ foundationalMentorState: FoundationalMentorState }>("/foundational-mentors/revoke-graduation", {
      method: "POST",
      body: JSON.stringify({ agentId, mentorId }),
    }),
  pauseAcademyTraining: () =>
    request<{ foundationalMentorState: FoundationalMentorState }>("/foundational-mentors/pause", { method: "POST" }),
  resumeAcademyTraining: () =>
    request<{ foundationalMentorState: FoundationalMentorState }>("/foundational-mentors/resume", { method: "POST" }),
  skipAcademyToNextMentor: () =>
    request<{ foundationalMentorState: FoundationalMentorState }>("/foundational-mentors/skip", { method: "POST" }),
  repeatAcademyMentor: (mentorId: FoundationalMentorId) =>
    request<{ foundationalMentorState: FoundationalMentorState }>("/foundational-mentors/repeat", {
      method: "POST",
      body: JSON.stringify({ mentorId }),
    }),
  addFoundationalMentorResource: (mentorId: FoundationalMentorId, title: string, url: string | null, resourceType: FoundationalResourceType) =>
    request<{ foundationalMentorState: FoundationalMentorState }>("/foundational-mentors/resource", {
      method: "POST",
      body: JSON.stringify({ mentorId, title, url, resourceType }),
    }),
  // Mentor Lab: real, in-product Foundational Mentor Library expansion.
  addAcademyMentor: (name: string, trackLabel: string, focusAreas: string[]) =>
    request<{ foundationalMentorState: FoundationalMentorState; mentorId: string }>("/foundational-mentors/add-mentor", {
      method: "POST",
      body: JSON.stringify({ name, trackLabel, focusAreas }),
    }),
  addAcademyLesson: (
    mentorId: FoundationalMentorId,
    title: string,
    simpleExplanation: string,
    deeperExplanation: string,
    quizQuestion: string,
    quizOptions: string[],
    correctIndex: number,
  ) =>
    request<{ foundationalMentorState: FoundationalMentorState }>("/foundational-mentors/add-lesson", {
      method: "POST",
      body: JSON.stringify({ mentorId, title, simpleExplanation, deeperExplanation, quizQuestion, quizOptions, correctIndex }),
    }),
  setActiveAcademyMentor: (mentorId: FoundationalMentorId) =>
    request<{ foundationalMentorState: FoundationalMentorState }>("/foundational-mentors/set-active", {
      method: "POST",
      body: JSON.stringify({ mentorId }),
    }),
};
