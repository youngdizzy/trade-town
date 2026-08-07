import type {
  Account,
  AccountType,
  AgentEnergy,
  AgentId,
  AlertSeverity,
  AnalystChoice,
  AuditEntry,
  AuditEventCategory,
  BlackBoxPriority,
  BlackBoxState,
  BlackSwanPlaybook,
  BlackSwanRiskTier,
  BlackSwanScenarioType,
  BrokerResilienceRead,
  CalendarState,
  Candle,
  CeoDecisionRecord,
  CeoOverrideRecord,
  ChallengeReport,
  ClientSaveSnapshot,
  ComplianceOverview,
  Debate,
  DefensiveModeState,
  EducationLesson,
  EducationProgress,
  EmergencyStopState,
  ExecutiveAccuracyScore,
  ExecutiveRecommendation,
  WeightedExecutiveRecommendation,
  WeightProfile,
  FoundationalMentorId,
  FoundationalMentorState,
  FoundationalResourceType,
  GameSaveState,
  Goal,
  GovernanceLayer,
  GoalAllocation,
  GoalCategory,
  GoalMetric,
  GoalPriority,
  HoldReason,
  GatekeeperRejection,
  InnovationState,
  KnowledgeGraph,
  PaperPortfolio,
  PlayerEventCategory,
  PlayerVsAiPrompt,
  PlayerVsAiState,
  PortfolioScenarioResult,
  PortfolioStressTestResult,
  PropFirmStatus,
  QuestionOfTheDay,
  RuleEvaluationResult,
  RuleType,
  SaveResponse,
  SavingsRuleType,
  SignalCalibrationState,
  SignalChallenge,
  SignalChoice,
  BacktestSession,
  ConfidenceTier,
  ConstitutionState,
  FailedStrategyArchiveEntry,
  KnowledgeQualityScore,
  MarketIntelligenceRegime,
  RegimeReconciliation,
  RiskLimits,
  SimilarTradesSummary,
  Strategy,
  StrategyCertification,
  StrategyDossier,
  StrategyExecutiveDashboard,
  TierAllocationLimits,
  StrategyExecutiveReview,
  StrategyFounderApproval,
  StrategyHallOfFameEntry,
  StrategyReview,
  TestScenario,
  TimeAdvanceTarget,
  TradeDecision,
  TradeProposal,
  TradeReportCard,
  TradingMode,
  TradingModeState,
  TradingModeHealthAssessment,
  TradingStylePerformance,
  LosingStreakRead,
  AdaptiveModeRecommendation,
  RecoveryBriefing,
  TreasuryState,
  Weekday,
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
  getRegimeReconciliation: () => request<RegimeReconciliation>("/market/regime-reconciliation"),
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
  submitCeoDecision: (proposalId: string, choice: AnalystChoice, delegated = false) =>
    request<{
      tradeProposals: TradeProposal[];
      ceoDecisions: CeoDecisionRecord[];
      decisions: TradeDecision[];
      paperPortfolio: PaperPortfolio;
      gatekeeperRejections: GatekeeperRejection[];
    }>("/executive/decide", {
      method: "POST",
      body: JSON.stringify({ proposalId, choice, delegated }),
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
  // Design Bible Chapter 70 Part 2 — "Modify" as a real CEO decision
  // action. Downsize-only; the proposal stays pending afterward.
  modifyProposal: (proposalId: string, quantity: number) =>
    request<{ tradeProposals: TradeProposal[] }>("/executive/modify", {
      method: "POST",
      body: JSON.stringify({ proposalId, quantity }),
    }),
  regenerateChallengeReport: (proposalId: string) =>
    request<{ challengeReports: ChallengeReport[]; innovationState: Record<AgentId, InnovationState> }>("/executive/challenge/regenerate", {
      method: "POST",
      body: JSON.stringify({ proposalId }),
    }),
  getWhatIfSimulation: (symbol: string) => request<WhatIfSimulation>(`/executive/whatif?symbol=${encodeURIComponent(symbol)}`),
  getExecutiveIntelligence: (proposalId: string) => request<ExecutiveRecommendation>(`/executive/intelligence?proposalId=${encodeURIComponent(proposalId)}`),
  // Design Bible Chapter 70 Part 2 — Executive Accuracy Score.
  getExecutiveAccuracy: () => request<ExecutiveAccuracyScore[]>("/executive/accuracy"),
  // Design Bible Chapter 70 Part 3 — Weighted Executive Decision Engine.
  // `profile` optionally previews a profile without persisting it.
  getWeightedDecision: (proposalId: string, profile?: WeightProfile) =>
    request<WeightedExecutiveRecommendation>(
      `/executive/weighted-decision?proposalId=${encodeURIComponent(proposalId)}${profile ? `&profile=${encodeURIComponent(profile)}` : ""}`,
    ),
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
  // Design Bible Chapter 67 (TTOS) Part 3 — the real Global Emergency Stop.
  activateEmergencyStop: () =>
    request<{ emergencyStop: EmergencyStopState }>("/emergency-stop/activate", { method: "POST" }),
  resumeTradingAfterEmergencyStop: () =>
    request<{ emergencyStop: EmergencyStopState }>("/emergency-stop/resume", { method: "POST" }),
  // Design Bible Chapter 72 — Black Swan Intelligence & Resilience
  // System. blackSwanIntelligence/blackSwanReports/defensiveMode/
  // blackSwanEvents/institutionalSurvivalScore are all already live via
  // the WS tick broadcast (see gameStore) — these are only the genuine
  // on-demand actions/reads.
  runBlackSwanStressTest: (accountId: string | null = null) =>
    request<PortfolioStressTestResult>("/black-swan/stress-test", {
      method: "POST",
      body: JSON.stringify({ accountId }),
    }),
  runBlackSwanScenario: (scenarioType: BlackSwanScenarioType, accountId: string | null = null) =>
    request<PortfolioScenarioResult>("/black-swan/scenario", {
      method: "POST",
      body: JSON.stringify({ scenarioType, accountId }),
    }),
  activateDefensiveMode: (reason?: string) =>
    request<{ defensiveMode: DefensiveModeState; riskLimits: RiskLimits }>("/black-swan/defensive-mode/activate", {
      method: "POST",
      body: JSON.stringify({ reason: reason ?? null }),
    }),
  deactivateDefensiveMode: () =>
    request<{ defensiveMode: DefensiveModeState; riskLimits: RiskLimits }>("/black-swan/defensive-mode/deactivate", { method: "POST" }),
  configureDefensiveMode: (triggerTier: BlackSwanRiskTier | null, autoTriggerEnabled: boolean | null) =>
    request<{ defensiveMode: DefensiveModeState; riskLimits: RiskLimits }>("/black-swan/defensive-mode/configure", {
      method: "POST",
      body: JSON.stringify({ triggerTier, autoTriggerEnabled }),
    }),
  getBlackSwanPlaybook: () => request<BlackSwanPlaybook>("/black-swan/playbook"),
  getBrokerResilience: () => request<BrokerResilienceRead>("/black-swan/broker-resilience"),
  // Design Bible Chapter 73 — Compliance, Audit & Governance System
  // (CAGS). A read-only synthesis layer with no WS-broadcast fields —
  // every one of these is a genuine on-demand fetch, never gameStore.
  getAuditLog: (params?: { category?: AuditEventCategory; severity?: AlertSeverity; search?: string; limit?: number }) => {
    const q = new URLSearchParams();
    if (params?.category) q.set("category", params.category);
    if (params?.severity) q.set("severity", params.severity);
    if (params?.search) q.set("search", params.search);
    if (params?.limit) q.set("limit", String(params.limit));
    const qs = q.toString();
    return request<AuditEntry[]>(`/audit/log${qs ? `?${qs}` : ""}`);
  },
  getAuditIncidents: () => request<AuditEntry[]>("/audit/incidents"),
  getGovernance: () => request<GovernanceLayer[]>("/audit/governance"),
  getComplianceOverview: () => request<ComplianceOverview>("/audit/overview"),
  getCeoOverrides: () => request<CeoOverrideRecord[]>("/audit/overrides"),
  // Design Bible Chapter 75 — Company Trading Modes & Institutional
  // Capital Protection. tradingModes/dailyCircuitBreaker/losingStreak/
  // recoveryBriefings are already live via the WS tick broadcast (see
  // gameStore) — these are the genuine on-demand reads/actions:
  // performance split, Trading Mode Health, and the Adaptive Mode
  // recommendation have no WS-broadcast field, and set/acknowledge are
  // real CEO actions.
  setTradingMode: (mode: TradingMode, hybridDayAllocationPct?: number) =>
    request<TradingModeState>("/trading-modes/set", {
      method: "POST",
      body: JSON.stringify({ mode, hybridDayAllocationPct: hybridDayAllocationPct ?? null }),
    }),
  acknowledgeLosingStreak: () => request<LosingStreakRead>("/trading-modes/losing-streak/acknowledge", { method: "POST" }),
  getTradingStylePerformance: () => request<TradingStylePerformance[]>("/trading-modes/performance"),
  getTradingModeHealth: () => request<TradingModeHealthAssessment[]>("/trading-modes/health"),
  getAdaptiveModeRecommendation: () => request<AdaptiveModeRecommendation>("/trading-modes/adaptive-recommendation"),
  getRecoveryBriefings: () => request<RecoveryBriefing[]>("/trading-modes/recovery-briefings"),
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
  // Design Bible Chapter 69 Part 1 — Multi-Account & Fund Management System.
  createAccount: (name: string, accountType: AccountType, startingBalance: number) =>
    request<{ accounts: Account[] }>("/accounts/create", {
      method: "POST",
      body: JSON.stringify({ name, accountType, startingBalance }),
    }),
  closeAccount: (accountId: string) =>
    request<{ accounts: Account[] }>("/accounts/close", {
      method: "POST",
      body: JSON.stringify({ accountId }),
    }),
  allocateAccountCapital: (accountId: string, amount: number) =>
    request<{ accounts: Account[]; treasury: TreasuryState }>("/accounts/allocate", {
      method: "POST",
      body: JSON.stringify({ accountId, amount }),
    }),
  deallocateAccountCapital: (accountId: string, amount: number) =>
    request<{ accounts: Account[]; treasury: TreasuryState }>("/accounts/deallocate", {
      method: "POST",
      body: JSON.stringify({ accountId, amount }),
    }),
  switchActiveAccount: (accountId: string | null) =>
    request<{ activeAccountId: string | null }>("/accounts/switch-active", {
      method: "POST",
      body: JSON.stringify({ accountId }),
    }),
  // Design Bible Chapter 69 Part 2 — Prop Firm Rule Engine.
  configurePropFirmRules: (
    accountId: string,
    rules: {
      trailingDrawdownLimitPct: number | null;
      consistencyLimitPct: number | null;
      challengeStartSimDay: number | null;
      challengeDurationDays: number | null;
      challengeProfitTargetPct: number | null;
    },
  ) =>
    request<{ accounts: Account[] }>("/accounts/prop-firm/configure", {
      method: "POST",
      body: JSON.stringify({ accountId, ...rules }),
    }),
  getPropFirmStatus: (accountId: string) => request<PropFirmStatus>(`/accounts/prop-firm/status?account_id=${encodeURIComponent(accountId)}`),
  // Design Bible Chapter 69 Part 3 — Institutional Rule Engine.
  addCustomRule: (accountId: string, ruleType: RuleType, label: string, limit: number, weekday: Weekday | null) =>
    request<{ accounts: Account[] }>("/accounts/rules/add", {
      method: "POST",
      body: JSON.stringify({ accountId, ruleType, label, limit, weekday }),
    }),
  removeCustomRule: (accountId: string, ruleId: string) =>
    request<{ accounts: Account[] }>("/accounts/rules/remove", {
      method: "POST",
      body: JSON.stringify({ accountId, ruleId }),
    }),
  toggleCustomRule: (accountId: string, ruleId: string, enabled: boolean) =>
    request<{ accounts: Account[] }>("/accounts/rules/toggle", {
      method: "POST",
      body: JSON.stringify({ accountId, ruleId, enabled }),
    }),
  evaluateAccountRules: (accountId: string) => request<RuleEvaluationResult>(`/accounts/rules/evaluate?account_id=${encodeURIComponent(accountId)}`),
  evaluateAndRecordAccountRules: (accountId: string) =>
    request<RuleEvaluationResult>("/accounts/rules/evaluate-and-record", {
      method: "POST",
      body: JSON.stringify({ accountId }),
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
  // v0.7 Feature 53 — Company Certification. Read-only, computed fresh
  // every call — `certified` is always a live read of current real
  // state (see StrategyCertification's own docstring in types.ts).
  getSandboxCertification: (strategyId: string) => request<StrategyCertification>(`/sandbox/certification?strategyId=${encodeURIComponent(strategyId)}`),
  // v0.7 Feature 54 (the brief self-numbered it "Feature 53," already
  // used above for Company Certification) — the Decision Memory
  // System. Both read-only, computed fresh every call, mirroring the
  // Sandbox certification/dossier convention exactly.
  getDecisionVaultReportCard: (vaultEntryId: string) => request<TradeReportCard>(`/decision-vault/report-card?vaultEntryId=${encodeURIComponent(vaultEntryId)}`),
  getDecisionVaultSimilar: (params: { symbol: string; marketRegime: MarketIntelligenceRegime; confidenceTier: ConfidenceTier; excludeId?: string }) => {
    const query = new URLSearchParams({ symbol: params.symbol, marketRegime: params.marketRegime, confidenceTier: params.confidenceTier });
    if (params.excludeId) query.set("excludeId", params.excludeId);
    return request<SimilarTradesSummary>(`/decision-vault/similar?${query.toString()}`);
  },
  // Design Bible Chapter 61 — Knowledge Quality Score. Same computed-
  // fresh, read-only convention as the two calls above.
  getDecisionVaultQualityScore: (vaultEntryId: string) => request<KnowledgeQualityScore>(`/decision-vault/quality-score?vaultEntryId=${encodeURIComponent(vaultEntryId)}`),
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
    updates: Partial<{
      dailyProfitTargetPct: number;
      maxDailyLossPct: number;
      // Design Bible Chapter 67 (TTOS) Safety Settings.
      maxWeeklyLossPct: number;
      maxMonthlyLossPct: number;
      maxTradesPerDay: number;
      riskPerTradePct: number;
      maxOpenPositions: number;
      // v0.7 Chapter 57 — four of the Position Sizing engine's six new
      // CEO controls. clearPortfolioHeatCap is the explicit way to set
      // portfolioHeatCapPct back to null (see backend/app/routers/risk.py).
      maxWeeklyDeploymentPct: number;
      portfolioHeatCapPct: number;
      clearPortfolioHeatCap: boolean;
      cashReservePct: number;
      tierAllocation: TierAllocationLimits;
      // v0.7 Chapter 58 — the Opportunity Gatekeeper's two new CEO controls.
      minTradeQualityScore: number;
      minExpectedValuePct: number;
      // v0.7 Chapter 59 — the Capital Priority & Opportunity Cost Engine's
      // two new CEO controls.
      minPriorityScore: number;
      capitalReservePct: number;
      // Design Bible Chapter 63 — Company Health tier thresholds. Always
      // stay strictly descending (Excellent > Good > Stable > Needs
      // Attention) — validated together server-side.
      companyHealthExcellentThreshold: number;
      companyHealthGoodThreshold: number;
      companyHealthStableThreshold: number;
      companyHealthNeedsAttentionThreshold: number;
    }>,
  ) =>
    request<{ riskLimits: RiskLimits }>("/risk-limits", {
      method: "POST",
      body: JSON.stringify(updates),
    }),
  // Design Bible Chapter 64 — the CEO's Goal creation/cancellation write
  // path. Real progress is never sent by the client; it's recomputed
  // server-side every tick (see backend/app/goals.py's tick_goals()).
  createGoal: (goal: { title: string; category: GoalCategory; targetMetric: GoalMetric; targetValue: number; deadlineSimDay?: number | null }) =>
    request<{ goals: Goal[] }>("/goals/create", {
      method: "POST",
      body: JSON.stringify(goal),
    }),
  cancelGoal: (goalId: string) =>
    request<{ goals: Goal[] }>("/goals/cancel", {
      method: "POST",
      body: JSON.stringify({ goalId }),
    }),
  getGoalPriorities: () => request<GoalPriority[]>("/goals/priorities"),
  getGoalAllocations: () => request<GoalAllocation[]>("/goals/allocations"),
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
  // Certification Management — full CEO controls over an earned
  // certification (Current Certifications panel). See
  // backend/app/foundational_mentors.py's "Certification Management"
  // section for the real active/suspended/revoked lifecycle.
  downgradeAcademyCertification: (agentId: AgentId, mentorId: FoundationalMentorId, reason: string) =>
    request<{ foundationalMentorState: FoundationalMentorState }>("/foundational-mentors/certification/downgrade", {
      method: "POST",
      body: JSON.stringify({ agentId, mentorId, reason }),
    }),
  promoteAcademyCertification: (agentId: AgentId, mentorId: FoundationalMentorId, reason: string | null) =>
    request<{ foundationalMentorState: FoundationalMentorState }>("/foundational-mentors/certification/promote", {
      method: "POST",
      body: JSON.stringify({ agentId, mentorId, reason }),
    }),
  revokeAcademyCertification: (agentId: AgentId, mentorId: FoundationalMentorId, reason: string) =>
    request<{ foundationalMentorState: FoundationalMentorState }>("/foundational-mentors/certification/revoke", {
      method: "POST",
      body: JSON.stringify({ agentId, mentorId, reason }),
    }),
  resetAcademyCertificationProgress: (agentId: AgentId, mentorId: FoundationalMentorId) =>
    request<{ foundationalMentorState: FoundationalMentorState }>("/foundational-mentors/certification/reset-progress", {
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
