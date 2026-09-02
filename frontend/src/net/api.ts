import type {
  Account,
  AccountType,
  AgentEnergy,
  AgentId,
  AgentStrategySurvivalScore,
  AgentTradingStatusRead,
  AgentVoteAccuracyScore,
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
  ChallengerComparison,
  ChampionChallengerFamilyRead,
  ChampionRecord,
  CeoOverrideEvaluation,
  CeoOverrideGovernanceSummary,
  CompiledStrategyBacktestResult,
  CompiledStrategyDefinition,
  ContinuousImprovementSummary,
  CostSensitivityResult,
  LookAheadAuditResult,
  ParameterSensitivityResult,
  QuantResearchExperiment,
  QuantResearchExperimentSimilarity,
  RegisterResearchableStrategyResult,
  DataQualityReport,
  ResearchCategory,
  ResearchExperimentRecord,
  StrategyMatch,
  StrategyTournamentResult,
  SubmitQuantResearchExperimentResult,
  SurvivorshipBiasRead,
  WalkForwardValidationResult,
  ControlEffectivenessSummary,
  ClientSaveSnapshot,
  ComplianceIncident,
  ComplianceIncidentSummary,
  ComplianceOverview,
  DataProvenanceReport,
  Debate,
  DefensiveModeState,
  EducationLesson,
  EducationProgress,
  EmaPullbackResearchResult,
  EvidenceConfluenceRead,
  ExitEfficiencySummary,
  EmergencyStopState,
  EvaluationPolicyComparisonReport,
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
  IncidentRootCause,
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
  PortfolioRiskSnapshot,
  PortfolioScenarioResult,
  PortfolioStressTestResult,
  PortfolioMarginalRiskDecision,
  PretradeRiskDecision,
  ProjectedLossPath,
  PropFirmStatus,
  QuestionOfTheDay,
  RuleEvaluationResult,
  RuleType,
  RunSummary,
  SaveResponse,
  SavingsRuleType,
  SignalCalibrationState,
  SignalChallenge,
  SignalChoice,
  BacktestSession,
  CandidacyBinning,
  ConfidenceTier,
  ConstitutionState,
  FactoryRunRecord,
  FactoryStatsRead,
  FailedStrategyArchiveEntry,
  FailureModeCount,
  FamilyResearchStats,
  KnowledgeQualityScore,
  ResearchDiscoveryCycleRecord,
  StrategyFamily,
  LessonEvidenceSummary,
  ResearchLessonRecord,
  ResearchLoopIterationRecord,
  StrategyHypothesis,
  MarketIntelligenceRegime,
  ModelValidationReport,
  MonteCarloReliabilityAssessment,
  ProcessAdherenceRead,
  ProcessAdherenceSummaryRead,
  RegimePerformanceSummary,
  RegimeReconciliation,
  SessionPerformanceSummary,
  SessionRangeRead,
  SessionRegimeEvidenceSummary,
  PortfolioMonteCarloResult,
  RecoveryFactorRead,
  RestrictionScope,
  RiskLimits,
  SimilarTradesSummary,
  TradingRestriction,
  StrategyCapitalAllocationSummary,
  StrategyDegradationSummary,
  StrategyLiveVsBacktestSummary,
  StrategyPerformanceSummary,
  StrategySessionPerformanceSummary,
  StrategyTradingDiagnosticSummary,
  SymbolPerformanceSummary,
  SymbolTrendRanking,
  VolumeConfirmationRead,
  TechnicalAnalysisRead,
  ConfluenceRead,
  TradeAttributionSummary,
  UnattributedTradeMonitor,
  TradeStrategyRuleSnapshot,
  TrendDefinitionMethod,
  TrendEnsembleReading,
  TrendRegimeBreakdown,
  TrendWeightingMethod,
  TradePipelineHealthSnapshot,
  BrierCalibrationSummary,
  AgentBrierCalibration,
  OpportunityFeed,
  WatchlistEligibilitySummary,
  TradingSession,
  Strategy,
  StrategyCertification,
  StrategyComplexityScore,
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
  SelfImprovementProposal,
  ExecutiveLearningSummary,
  CompanyEvolutionScore,
  CompanyEvolutionWindow,
  LossWinClassificationRead,
  VisionBoardState,
  VisionPriorityCategory,
  VisionObjectiveCategory,
  VisionSelfCorrectionNote,
  BoardRoster,
  SituationRoomState,
  TravelModeState,
  TravelModeSettings,
  TravelModeBriefing,
  TreasuryState,
  Weekday,
  WhatIfSimulation,
  ExternalMarketDataStatus,
  HoldoutEvaluationResult,
  PortfolioResearchReport,
  EvidenceQualityReport,
  LineageIntegrityIssue,
  SniperCandidate,
  SniperEngineStatusRead,
  SniperLead,
  SniperLesson,
  SniperLiveArmingStatus,
  SniperPosition,
  SniperRiskState,
  SniperTrade,
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
  // CEO directive "Proper Multi-Run / Save Isolation System".
  listRuns: () => request<RunSummary[]>("/runs"),
  getActiveRun: () => request<RunSummary | null>("/runs/active"),
  createRun: (displayName?: string) =>
    request<GameSaveState>("/runs", {
      method: "POST",
      body: JSON.stringify({ displayName: displayName ?? null }),
    }),
  activateRun: (runId: string) => request<GameSaveState>(`/runs/${encodeURIComponent(runId)}/activate`, { method: "POST" }),
  getCandles: (symbol: string, timeframe: string, limit = 150) =>
    request<Candle[]>(`/market/candles?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}&limit=${limit}`),
  getTimeframes: () => request<string[]>("/market/timeframes"),
  getRegimeReconciliation: () => request<RegimeReconciliation>("/market/regime-reconciliation"),
  // CEO directive "Session Trading Education & Agent Training". Read-only,
  // computed fresh per request.
  getSessionRegimeEvidence: () => request<SessionRegimeEvidenceSummary>("/market/session-evidence"),
  // CEO directive "Professional Trading Firm — Market-Analysis Knowledge
  // + Session Intelligence Expansion," Phases 1-4. Read-only, computed
  // fresh per request — see backend/app/technical_analysis.py /
  // technical_patterns.py.
  getTechnicalAnalysis: (symbol: string, timeframe = "1h", limit = 100) =>
    request<TechnicalAnalysisRead>(
      `/market/technical-analysis?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}&limit=${limit}`
    ),
  getSessionRange: (symbol: string, session: TradingSession, timeframe = "1h", limit = 100) =>
    request<SessionRangeRead>(
      `/market/session-range?symbol=${encodeURIComponent(symbol)}&session=${encodeURIComponent(session)}&timeframe=${encodeURIComponent(timeframe)}&limit=${limit}`
    ),
  // CEO directive "Professional Quant Trading Firm — Quant Intelligence
  // + Market Analysis Completion Phase," Phase D. Read-only, computed
  // fresh per request — see backend/app/evidence_confluence.py.
  getEvidenceConfluence: (symbol: string, timeframe = "1h", limit = 100) =>
    request<EvidenceConfluenceRead>(
      `/market/evidence-confluence?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}&limit=${limit}`
    ),
  // CEO directive "AHL-Inspired Systematic Trend & Momentum Research
  // Engine." Read-only research evidence, computed fresh per request —
  // see backend/app/trend_engine.py. Never a trading signal API.
  getTrendEngineReading: (symbol: string, timeframe = "1h", limit = 200, method: TrendDefinitionMethod = "endpoint_slope", weighting: TrendWeightingMethod = "equal") =>
    request<TrendEnsembleReading>(
      `/market/trend-engine?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}&limit=${limit}&method=${encodeURIComponent(method)}&weighting=${encodeURIComponent(weighting)}`
    ),
  getTrendEngineCrossSectional: (timeframe = "1h", limit = 200, method: TrendDefinitionMethod = "endpoint_slope") =>
    request<SymbolTrendRanking[]>(`/market/trend-engine/cross-sectional?timeframe=${encodeURIComponent(timeframe)}&limit=${limit}&method=${encodeURIComponent(method)}`),
  getTrendEngineRegimeBreakdown: (symbol: string, timeframe = "1h", method: TrendDefinitionMethod = "endpoint_slope", forwardBars = 10) =>
    request<TrendRegimeBreakdown>(
      `/market/trend-engine/regime-breakdown?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}&method=${encodeURIComponent(method)}&forward_bars=${forwardBars}`
    ),
  // CEO directive "Professional Quant Trading Core," Phase B's last P2
  // item — the Asset Discovery Engine (backend/app/asset_discovery.py).
  getAssetDiscovery: (timeframe = "1d", limit = 200, method: TrendDefinitionMethod = "endpoint_slope", topN = 10) =>
    request<SymbolTrendRanking[]>(`/market/asset-discovery?timeframe=${encodeURIComponent(timeframe)}&limit=${limit}&method=${encodeURIComponent(method)}&topN=${topN}`),
  // CEO directive "AHL-Inspired Systematic Trend & Momentum Research
  // Engine," Phase 7 — the Volume Confirmation Engine.
  getVolumeConfirmation: (symbol: string, timeframe = "1h", limit = 100, period = 20) =>
    request<VolumeConfirmationRead | null>(`/market/volume-confirmation?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}&limit=${limit}&period=${period}`),
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
  // CEO directive "Professional Trading Firm Transformation" — Post-
  // Trade Review, Exit Efficiency. Read-only, computed fresh per request.
  getExitEfficiency: () => request<ExitEfficiencySummary>("/trades/exit-efficiency"),
  // CEO directive "Next Professional Trading Firm Phase," Priority 2 —
  // Unified P&L Reporting, scoped to symbol-level attribution this
  // pass. Read-only, computed fresh per request.
  getPerformanceBySymbol: () => request<SymbolPerformanceSummary>("/trades/performance-by-symbol"),
  // CEO directive "Next Phase: Professional Trading Firm Intelligence,"
  // Phase 3 — real session/regime P&L via the real Decision Vault join.
  // Read-only, computed fresh per request.
  getPerformanceBySession: () => request<SessionPerformanceSummary>("/trades/performance-by-session"),
  // CEO directive "Professional Quant Firm Phase 41-45," Critical Task
  // #0 — diagnostic-only trade-flow funnel telemetry. Read-only,
  // computed fresh per request; never gates or scores anything.
  getPipelineHealth: () => request<TradePipelineHealthSnapshot>("/trades/pipeline-health"),
  // CEO directive "Professional Quant Trading Core," Rule 25/26 — the
  // CEO Opportunity Feed. Read-only, computed fresh per request; never
  // gates or scores anything.
  getOpportunityFeed: () => request<OpportunityFeed>("/trades/opportunity-feed"),
  // CEO directive "Professional Quant Trading Core," Phase B P2 item —
  // see backend/app/watchlist_eligibility.py's own module docstring.
  getWatchlistEligibility: () => request<WatchlistEligibilitySummary>("/trades/watchlist-eligibility"),
  // CEO directive "Professional Quant Trading Core," Phase B P2 item —
  // see backend/app/prediction_tracking.py's compute_brier_calibration().
  getBrierCalibration: () => request<BrierCalibrationSummary>("/predictions/calibration/brier"),
  // CEO directive "Professional Quant Portfolio Intelligence + Alpha
  // Research Engine," Phase 7 — the same real Brier methodology broken
  // out per real named agent. See backend/app/prediction_tracking.py's
  // compute_agent_brier_calibration().
  getAgentBrierCalibration: () => request<AgentBrierCalibration[]>("/predictions/calibration/brier/by-agent"),
  // CEO directive "Command Center + Professional Quant Trading Firm
  // Upgrade," Phase 2 — every real agent's current trading-relevant
  // state. Read-only, computed fresh per request; not WS-broadcast.
  getAgentTradingStatus: () => request<AgentTradingStatusRead[]>("/agents/trading-status"),
  getPerformanceByRegime: () => request<RegimePerformanceSummary>("/trades/performance-by-regime"),
  // CEO directive "Live Trade → Strategy Provenance," Phase 4 — real
  // strategy-grouped P&L via the real Decision Vault join. Read-only,
  // computed fresh per request.
  getPerformanceByStrategy: () => request<StrategyPerformanceSummary>("/trades/performance-by-strategy"),
  // CEO directive "Live Trade → Strategy Provenance," Phase 6 — the
  // real strategy×session axis. Read-only, computed fresh per request.
  getPerformanceByStrategySession: () => request<StrategySessionPerformanceSummary>("/trades/performance-by-strategy-session"),
  // CEO directive "Live Trade → Strategy Provenance," Phase 5 — does a
  // strategy's real live performance match its own real backtest
  // evidence? Read-only, computed fresh per request.
  getStrategyLiveVsBacktest: () => request<StrategyLiveVsBacktestSummary>("/trades/strategy-live-vs-backtest"),
  // CEO directive "Portfolio Construction, Capital Allocation & Execution
  // Realism," Phase 5 — an informational evidence roster for the CEO's
  // own manual allocatedCapital decision, never a system-generated
  // ranking. Read-only, computed fresh per request.
  getStrategyCapitalAllocation: () => request<StrategyCapitalAllocationSummary>("/trades/strategy-capital-allocation"),
  // CEO directive "Portfolio Construction, Capital Allocation & Execution
  // Realism," Phase 6 — normal variation vs. a real, evidence-backed
  // degradation warning. Read-only, computed fresh per request.
  getStrategyDegradation: () => request<StrategyDegradationSummary>("/trades/strategy-degradation"),
  // CEO directive "Live Trade → Strategy Provenance," Phase 9 — "why
  // isn't this strategy trading live?" per strategy, diagnostic only.
  // Read-only, computed fresh per request.
  getStrategyTradingDiagnostics: () => request<StrategyTradingDiagnosticSummary>("/trades/strategy-trading-diagnostics"),
  // CEO directive "Next Professional Trading Firm Phase," Priority 5 —
  // Research Data Integrity. Read-only; the candle row re-checks the
  // real provider live on every request.
  getDataProvenance: () => request<DataProvenanceReport>("/market/data-provenance"),
  // CEO directive "Next Phase: Professional Trading Firm Intelligence,"
  // Phase 1 — real per-trade agent-contribution evidence, never a
  // numeric P&L credit split. Read-only, computed fresh per request.
  getTradeAttribution: () => request<TradeAttributionSummary>("/trades/attribution"),
  // CEO directive "Complete Trade Provenance," Part 17 — a dedicated,
  // visible data-quality diagnostic for strategy attribution coverage.
  // Read-only, computed fresh per request.
  getUnattributedTradeMonitor: () => request<UnattributedTradeMonitor>("/trades/unattributed-monitor"),
  // CEO directive "Complete Trade Provenance," Part 2 — one real trade's
  // exact compiled rule snapshot, joined from the CeoDecisionRecord it
  // resolved to at decision time. Read-only, computed fresh per request.
  getTradeStrategyRuleSnapshot: (tradeId: string) => request<TradeStrategyRuleSnapshot>(`/trades/${tradeId}/strategy-rule-snapshot`),
  // CEO directive "Live Trade -> Strategy Provenance" — `strategyId` is
  // an optional real Strategy Lab strategy the CEO explicitly selected
  // for this decision, stored on the resulting CeoDecisionRecord (see
  // backend/app/state.py's submit_ceo_decision).
  submitCeoDecision: (proposalId: string, choice: AnalystChoice, delegated = false, overrideReason?: string, strategyId?: string) =>
    request<{
      tradeProposals: TradeProposal[];
      ceoDecisions: CeoDecisionRecord[];
      decisions: TradeDecision[];
      paperPortfolio: PaperPortfolio;
      gatekeeperRejections: GatekeeperRejection[];
    }>("/executive/decide", {
      method: "POST",
      body: JSON.stringify({ proposalId, choice, delegated, overrideReason: overrideReason ?? null, strategyId: strategyId ?? null }),
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
  // CEO directive "Professional Trading Firm — Market-Analysis Knowledge
  // + Session Intelligence Expansion," Phase 6 — the Confluence Engine.
  getConfluence: (proposalId: string) => request<ConfluenceRead>(`/executive/confluence?proposalId=${encodeURIComponent(proposalId)}`),
  // Trading Psychology & Discipline, Piece C — the Process Adherence Score.
  getProcessAdherence: (decisionId: string) => request<ProcessAdherenceRead>(`/executive/decisions/${encodeURIComponent(decisionId)}/process-adherence`),
  getProcessAdherenceSummary: () => request<ProcessAdherenceSummaryRead>("/executive/process-adherence-summary"),
  // Design Bible Chapter 70 Part 2 — Executive Accuracy Score.
  getExecutiveAccuracy: () => request<ExecutiveAccuracyScore[]>("/executive/accuracy"),
  // CEO directive "Professional Quant Trading Core," Phase B's per-agent
  // learning follow-up — the same accuracy read per individual agent.
  getAgentVoteAccuracy: () => request<AgentVoteAccuracyScore[]>("/executive/agent-accuracy"),
  // CEO directive "Professional Quant Portfolio Intelligence + Alpha
  // Research Engine," Phase 6 (Agent Talent System) — the same real
  // evidence-floor read one level up, over real Strategy outcomes.
  getAgentStrategySurvival: () => request<AgentStrategySurvivalScore[]>("/sandbox/agent-survival"),
  // Design Bible Chapter 70 Part 3 — Weighted Executive Decision Engine.
  // `profile` optionally previews a profile without persisting it.
  getWeightedDecision: (proposalId: string, profile?: WeightProfile) =>
    request<WeightedExecutiveRecommendation>(
      `/executive/weighted-decision?proposalId=${encodeURIComponent(proposalId)}${profile ? `&profile=${encodeURIComponent(profile)}` : ""}`,
    ),
  getKnowledgeGraph: () => request<KnowledgeGraph>("/knowledge-graph"),
  // Quantitative Research & Intelligence System, Piece 7 (Forge, the
  // Quant Developer) — a real, standing pipeline-reliability fact,
  // computed fresh on every call, same as getKnowledgeGraph above.
  getMonteCarloReliability: () => request<MonteCarloReliabilityAssessment>("/quant-developer/monte-carlo-reliability"),
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
  // CEO directive "Features 31-35," Feature 31 — the Compliance
  // Incident Resolution Engine's real, persisted case list and its
  // lifecycle mutations (backend/app/routers/audit.py's new
  // /incidents/cases endpoints, distinct from the ephemeral /incidents
  // filter above).
  getComplianceIncidentCases: () => request<ComplianceIncident[]>("/audit/incidents/cases"),
  getComplianceIncidentSummary: () => request<ComplianceIncidentSummary>("/audit/incidents/summary"),
  startInvestigatingIncident: (incidentId: string, owner: AgentId) =>
    request<ComplianceIncident>(`/audit/incidents/${encodeURIComponent(incidentId)}/investigate`, {
      method: "POST",
      body: JSON.stringify({ owner }),
    }),
  beginIncidentRemediation: (incidentId: string, remediationPlan: string, deadlineSimDay: number) =>
    request<ComplianceIncident>(`/audit/incidents/${encodeURIComponent(incidentId)}/remediate`, {
      method: "POST",
      body: JSON.stringify({ remediationPlan, deadlineSimDay }),
    }),
  addIncidentEvidence: (incidentId: string, note: string) =>
    request<ComplianceIncident>(`/audit/incidents/${encodeURIComponent(incidentId)}/evidence`, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),
  submitIncidentForVerification: (incidentId: string) =>
    request<ComplianceIncident>(`/audit/incidents/${encodeURIComponent(incidentId)}/submit-verification`, { method: "POST" }),
  failIncidentVerification: (incidentId: string, note: string) =>
    request<ComplianceIncident>(`/audit/incidents/${encodeURIComponent(incidentId)}/fail-verification`, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),
  verifyAndResolveIncident: (incidentId: string, verifier: AgentId, rootCause: IncidentRootCause, correctiveAction: string) =>
    request<ComplianceIncident>(`/audit/incidents/${encodeURIComponent(incidentId)}/resolve`, {
      method: "POST",
      body: JSON.stringify({ verifier, rootCause, correctiveAction }),
    }),
  reopenIncident: (incidentId: string, note: string) =>
    request<ComplianceIncident>(`/audit/incidents/${encodeURIComponent(incidentId)}/reopen`, {
      method: "POST",
      body: JSON.stringify({ note }),
    }),
  // CEO directive "Features 31-35," Feature 32 — CEO Override
  // Governance's real, persisted override-evaluation list and its one
  // real mutation (a reviewer's note).
  getCeoOverrideEvaluations: () => request<CeoOverrideEvaluation[]>("/audit/overrides/evaluations"),
  getCeoOverrideGovernanceSummary: () => request<CeoOverrideGovernanceSummary>("/audit/overrides/summary"),
  addCeoOverrideReview: (evaluationId: string, reviewer: AgentId, note: string) =>
    request<CeoOverrideEvaluation>(`/audit/overrides/${encodeURIComponent(evaluationId)}/review`, {
      method: "POST",
      body: JSON.stringify({ reviewer, note }),
    }),
  // CEO directive "Features 31-35," Feature 34 — Compliance Control
  // Effectiveness. Read-only, computed fresh per request.
  getControlEffectiveness: () => request<ControlEffectivenessSummary>("/audit/controls/effectiveness"),
  // CEO directive "Features 31-35," Feature 35 — the Continuous
  // Compliance Improvement Loop. Read-only, computed fresh per request.
  getContinuousImprovement: () => request<ContinuousImprovementSummary>("/audit/continuous-improvement"),
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
  setAdaptiveRecommendationsEnabled: (enabled: boolean) =>
    request<TradingModeState>("/trading-modes/adaptive-recommendations-enabled", {
      method: "POST",
      body: JSON.stringify({ enabled }),
    }),
  getRecoveryBriefings: () => request<RecoveryBriefing[]>("/trading-modes/recovery-briefings"),
  // Design Bible Chapter 74 — Continuous Learning & Self-Improvement
  // System (CLSIS, Part 1) and the Institutional Evolution Engine (Part
  // 2). selfImprovementProposals/evolutionReports are already live via
  // the WS tick broadcast (gameStore) — these are the genuine on-demand
  // reads/actions: Executive Learning Summary and the Company Evolution
  // Score have no WS-broadcast field, and decide/implement are real CEO
  // actions.
  decideSelfImprovementProposal: (proposalId: string, approve: boolean, ceoNote?: string) =>
    request<SelfImprovementProposal[]>("/self-improvement/proposals/decide", {
      method: "POST",
      body: JSON.stringify({ proposalId, approve, ceoNote: ceoNote ?? null }),
    }),
  markSelfImprovementProposalImplemented: (proposalId: string, implementationNote?: string) =>
    request<SelfImprovementProposal[]>("/self-improvement/proposals/implement", {
      method: "POST",
      body: JSON.stringify({ proposalId, implementationNote: implementationNote ?? null }),
    }),
  getExecutiveLearningSummary: (agentId: AgentId) => request<ExecutiveLearningSummary>(`/self-improvement/executive-learning/${agentId}`),
  getCompanyEvolutionScore: (window: CompanyEvolutionWindow) => request<CompanyEvolutionScore>(`/self-improvement/evolution-score/${window}`),
  getLossWinClassification: () => request<LossWinClassificationRead>("/self-improvement/loss-win-classification"),
  // Design Bible Chapter 74.5 — CEO Vision Board & Strategic Alignment
  // Engine. visionBoard is already live via the WS tick broadcast — the
  // mutations below are real CEO actions; the Self-Correction Note has
  // no WS-broadcast field (computed fresh per request). Goal/
  // constitution-amendment alignment lookups exist at the API layer
  // (backend/app/routers/vision_board.py) but have no UI surface yet —
  // they belong more naturally on the Goals/Constitution panels
  // themselves, out of scope for this chapter's own panel.
  setVisionBoardMission: (mission: string | null) =>
    request<VisionBoardState>("/vision-board/mission", { method: "POST", body: JSON.stringify({ mission }) }),
  setVisionBoardIdentityNote: (identityNote: string | null) =>
    request<VisionBoardState>("/vision-board/identity-note", { method: "POST", body: JSON.stringify({ identityNote }) }),
  setVisionBoardPriorities: (priorities: VisionPriorityCategory[]) =>
    request<VisionBoardState>("/vision-board/priorities", { method: "POST", body: JSON.stringify({ priorities }) }),
  addVisionBoardObjective: (text: string, category: VisionObjectiveCategory) =>
    request<VisionBoardState>("/vision-board/objectives", { method: "POST", body: JSON.stringify({ text, category }) }),
  removeVisionBoardObjective: (objectiveId: string) =>
    request<VisionBoardState>(`/vision-board/objectives/${encodeURIComponent(objectiveId)}`, { method: "DELETE" }),
  getVisionSelfCorrectionNote: () => request<VisionSelfCorrectionNote>("/vision-board/self-correction"),
  // Design Bible Chapter 70 Part 1 — Executive Board & CEO Intelligence
  // System. boardRoster has no WS-broadcast field (computed fresh per
  // request, same on-demand pattern as the Adaptive Mode recommendation
  // above) — fetched here instead. boardReports IS already live via the
  // WS tick broadcast (gameStore).
  getBoardRoster: () => request<BoardRoster>("/board/roster"),
  // Design Bible Chapter 73.5 — Mobile Command Center & Remote
  // Operations. situationRoom has no WS-broadcast field (computed
  // fresh per request, same on-demand pattern as the Adaptive Mode
  // recommendation above) — fetched here instead. travelMode/
  // travelModeBriefings ARE already live via the WS tick broadcast
  // (gameStore); activate/deactivate/settings below are the real CEO
  // actions.
  getSituationRoom: () => request<SituationRoomState>("/situation-room"),
  activateTravelMode: () => request<TravelModeState>("/travel-mode/activate", { method: "POST" }),
  deactivateTravelMode: () => request<TravelModeBriefing>("/travel-mode/deactivate", { method: "POST" }),
  updateTravelModeSettings: (settings: Partial<TravelModeSettings>) =>
    request<TravelModeState>("/travel-mode/settings", { method: "PATCH", body: JSON.stringify(settings) }),
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
  // Prop-Firm Risk Intelligence Addendum, Piece 10a — evaluation cost /
  // funded-stage / payout tracking.
  configureEvaluationTracking: (accountId: string, evaluationCost: number | null, payoutEligibilityMinProfitPct: number | null) =>
    request<{ accounts: Account[] }>("/accounts/evaluation/configure", {
      method: "POST",
      body: JSON.stringify({ accountId, evaluationCost, payoutEligibilityMinProfitPct }),
    }),
  markAccountFunded: (accountId: string) =>
    request<{ accounts: Account[] }>("/accounts/evaluation/mark-funded", {
      method: "POST",
      body: JSON.stringify({ accountId }),
    }),
  recordAccountPayout: (accountId: string, amount: number) =>
    request<{ accounts: Account[] }>("/accounts/evaluation/record-payout", {
      method: "POST",
      body: JSON.stringify({ accountId, amount }),
    }),
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
    // v0.7 Quantitative Research & Intelligence System, Piece 4 — this
    // is also the one real moment Meridian/CIO's independent, advisory-
    // only ModelValidationReport is filed.
    request<{
      strategies: Strategy[];
      strategyReviews: StrategyReview[];
      strategyExecutiveReviews: StrategyExecutiveReview[];
      strategyFounderApprovals: StrategyFounderApproval[];
      strategyModelValidation: ModelValidationReport | null;
    }>("/sandbox/request-review", {
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
  // CEO directive "Professional Trading Firm — Market-Analysis Knowledge
  // + Session Intelligence Expansion," Phase 15. Read-only, computed
  // fresh every call — see backend/app/ema_pullback_research.py.
  getEmaPullbackResearch: (candlesPerSymbol?: number) =>
    request<EmaPullbackResearchResult>(`/sandbox/ema-pullback-research${candlesPerSymbol ? `?candlesPerSymbol=${candlesPerSymbol}` : ""}`),
  // CEO directive "Professional Quant Trading Firm — Quant Intelligence
  // + Market Analysis Completion Phase," Phase F. Stateless — computed
  // fresh every call, nothing persisted — see
  // backend/app/strategy_compiler.py / backend/app/strategy_engine.py.
  compileStrategy: (name: string, sourceText: string, timeframe = "1h") =>
    request<CompiledStrategyDefinition>("/sandbox/compile-strategy", {
      method: "POST",
      body: JSON.stringify({ name, sourceText, timeframe }),
    }),
  backtestCompiledStrategy: (definition: CompiledStrategyDefinition, candlesPerSymbol?: number) =>
    request<CompiledStrategyBacktestResult>(`/sandbox/backtest-compiled-strategy${candlesPerSymbol ? `?candlesPerSymbol=${candlesPerSymbol}` : ""}`, {
      method: "POST",
      body: JSON.stringify(definition),
    }),
  // CEO directive "...Quant Intelligence + Market Analysis Completion
  // Phase (Next Research + Validation Pass)." Read-only, computed fresh
  // per request — see the matching backend module's own docstring for
  // each endpoint's real methodology.
  walkForwardValidation: (definition: CompiledStrategyDefinition, candlesPerSymbol?: number, windowBars?: number) =>
    request<WalkForwardValidationResult>(
      `/sandbox/walk-forward-validation?${[candlesPerSymbol ? `candlesPerSymbol=${candlesPerSymbol}` : "", windowBars ? `windowBars=${windowBars}` : ""].filter(Boolean).join("&")}`,
      { method: "POST", body: JSON.stringify(definition) }
    ),
  parameterSensitivity: (definition: CompiledStrategyDefinition, candlesPerSymbol?: number) =>
    request<ParameterSensitivityResult>(`/sandbox/parameter-sensitivity${candlesPerSymbol ? `?candlesPerSymbol=${candlesPerSymbol}` : ""}`, {
      method: "POST",
      body: JSON.stringify(definition),
    }),
  costSensitivity: (definition: CompiledStrategyDefinition, candlesPerSymbol?: number) =>
    request<CostSensitivityResult>(`/sandbox/cost-sensitivity${candlesPerSymbol ? `?candlesPerSymbol=${candlesPerSymbol}` : ""}`, {
      method: "POST",
      body: JSON.stringify(definition),
    }),
  lookAheadAudit: (definition: CompiledStrategyDefinition, candlesPerSymbol?: number) =>
    request<LookAheadAuditResult>(`/sandbox/look-ahead-audit${candlesPerSymbol ? `?candlesPerSymbol=${candlesPerSymbol}` : ""}`, {
      method: "POST",
      body: JSON.stringify(definition),
    }),
  // CEO directive "TradeTown — 11/10 Strategy Factory + Ruthless
  // Backtesting Engine," Section 13 — a real structural complexity
  // count, no market data needed. Also packaged into
  // runResearchExperiment()'s own record below.
  complexityScore: (definition: CompiledStrategyDefinition) =>
    request<StrategyComplexityScore>("/sandbox/complexity-score", { method: "POST", body: JSON.stringify(definition) }),
  runResearchExperiment: (definition: CompiledStrategyDefinition, candlesPerSymbol?: number) =>
    request<ResearchExperimentRecord>(`/sandbox/research-experiment${candlesPerSymbol ? `?candlesPerSymbol=${candlesPerSymbol}` : ""}`, {
      method: "POST",
      body: JSON.stringify(definition),
    }),
  // CEO directive "Professional Quant Firm Phase," Feature 37 — real,
  // persisted strategy version history. See
  // backend/app/strategy_registry.py.
  registerStrategyVersion: (name: string, sourceText: string, timeframe = "1h") =>
    request<CompiledStrategyDefinition>("/sandbox/register-strategy-version", {
      method: "POST",
      body: JSON.stringify({ name, sourceText, timeframe }),
    }),
  getStrategyVersions: (name: string) => request<CompiledStrategyDefinition[]>(`/sandbox/strategy-versions?name=${encodeURIComponent(name)}`),
  // CEO directive "TradeTown — 11/10 Self-Improving Quant Agent
  // System," Section 1 (Champion vs Challenger). See
  // backend/app/champion_challenger.py.
  compareChampionChallenger: (
    championDefinition: CompiledStrategyDefinition,
    challengerDefinition: CompiledStrategyDefinition,
    strategyFamily: string,
    hypothesis: string,
    proposedBy: AgentId,
    symbols?: string[]
  ) =>
    request<ChallengerComparison>("/sandbox/champion-challenger/compare", {
      method: "POST",
      body: JSON.stringify({ championDefinition, challengerDefinition, strategyFamily, hypothesis, proposedBy, symbols }),
    }),
  promoteChallenger: (comparisonId: string, promotedBy: AgentId, reasoning: string) =>
    request<ChampionRecord>("/sandbox/champion-challenger/promote", {
      method: "POST",
      body: JSON.stringify({ comparisonId, promotedBy, reasoning }),
    }),
  getChampionChallengerFamily: (strategyFamily: string) =>
    request<ChampionChallengerFamilyRead>(`/sandbox/champion-challenger/${encodeURIComponent(strategyFamily)}`),
  // CEO directive "TradeTown — Statistical Validation + Research
  // Failure Taxonomy," Part 2 (Failure Clustering). See
  // backend/app/failure_taxonomy.py's compute_top_failure_modes().
  getTopFailureModes: () => request<FailureModeCount[]>("/sandbox/failure-modes"),
  // CEO directive "TradeTown — Next Major Implementation Pass, Phase
  // 4-6: Self-Improving Strategy Factory + Validation Funnel." See
  // backend/app/research_loop.py.
  runResearchLoopIteration: (hypothesis: StrategyHypothesis, definition: CompiledStrategyDefinition, symbols?: string[]) =>
    request<ResearchLoopIterationRecord>("/sandbox/research-loop/run", {
      method: "POST",
      body: JSON.stringify({ hypothesis, definition, symbols }),
    }),
  getResearchLoopIterations: (strategyFamily?: string, candidacy?: CandidacyBinning) => {
    const params = new URLSearchParams();
    if (strategyFamily) params.set("strategyFamily", strategyFamily);
    if (candidacy) params.set("candidacy", candidacy);
    const qs = params.toString();
    return request<ResearchLoopIterationRecord[]>(`/sandbox/research-loop/iterations${qs ? `?${qs}` : ""}`);
  },
  getResearchLoopLessons: (strategyFamily?: string) =>
    request<ResearchLessonRecord[]>(`/sandbox/research-loop/lessons${strategyFamily ? `?strategyFamily=${encodeURIComponent(strategyFamily)}` : ""}`),
  getResearchLoopLessonEvidence: (strategyFamily?: string) =>
    request<LessonEvidenceSummary[]>(`/sandbox/research-loop/lessons/evidence${strategyFamily ? `?strategyFamily=${encodeURIComponent(strategyFamily)}` : ""}`),
  // CEO directive "TradeTown — Phase 7: Autonomous Strategy Evolution
  // Engine." See backend/app/research_factory.py.
  runResearchFactoryRun: (
    hypothesis: StrategyHypothesis,
    definition: CompiledStrategyDefinition,
    options?: {
      maxGenerations?: number;
      maxTotalBacktests?: number;
      symbols?: string[];
      // CEO directive "Phase 9: Full Autonomous Quant Research Factory,"
      // Phase 5 — omit to use this codebase's own real, richer
      // defaults (MAX_CHILDREN_PER_PARENT/MAX_RUNTIME_SECONDS).
      maxChildrenPerParent?: number;
      maxRuntimeSeconds?: number;
    }
  ) =>
    request<FactoryRunRecord>("/sandbox/research-factory/run", {
      method: "POST",
      body: JSON.stringify({
        hypothesis,
        definition,
        maxGenerations: options?.maxGenerations,
        maxTotalBacktests: options?.maxTotalBacktests,
        symbols: options?.symbols,
        maxChildrenPerParent: options?.maxChildrenPerParent,
        maxRuntimeSeconds: options?.maxRuntimeSeconds,
      }),
    }),
  getResearchFactoryRuns: (strategyFamily?: string) =>
    request<FactoryRunRecord[]>(`/sandbox/research-factory/runs${strategyFamily ? `?strategyFamily=${encodeURIComponent(strategyFamily)}` : ""}`),
  getResearchFactoryRunDetail: (runId: string) => request<FactoryRunRecord>(`/sandbox/research-factory/runs/${encodeURIComponent(runId)}`),
  getResearchFactoryLineage: (strategyFamily: string) =>
    request<ResearchLoopIterationRecord[]>(`/sandbox/research-factory/lineage/${encodeURIComponent(strategyFamily)}`),
  getResearchFactoryStats: () => request<FactoryStatsRead>("/sandbox/research-factory/stats"),
  // CEO directive "TradeTown — Phase 10: Real Data + True Holdout +
  // Portfolio Intelligence." See backend/app/routers/sandbox.py's own
  // docstrings on each endpoint for the exact real behavior/honesty
  // boundary.
  getExternalMarketDataStatus: () => request<ExternalMarketDataStatus>("/sandbox/external-market-data/status"),
  evaluateHoldout: (definition: CompiledStrategyDefinition, symbol?: string, timeframe?: string, candlesPerSymbol?: number) =>
    request<HoldoutEvaluationResult>("/sandbox/holdout/evaluate", {
      method: "POST",
      body: JSON.stringify({ definition, symbol, timeframe, candlesPerSymbol }),
    }),
  analyzePortfolio: (definitions: CompiledStrategyDefinition[], symbols?: string[], timeframe?: string, candlesPerSymbol?: number) =>
    request<PortfolioResearchReport>("/sandbox/portfolio-analyst/analyze", {
      method: "POST",
      body: JSON.stringify({ definitions, symbols, timeframe, candlesPerSymbol }),
    }),
  getEvidenceQuality: (definition: CompiledStrategyDefinition, symbols?: string[], timeframe?: string, candlesPerSymbol?: number) =>
    request<EvidenceQualityReport>("/sandbox/evidence-quality", {
      method: "POST",
      body: JSON.stringify({ definition, symbols, timeframe, candlesPerSymbol }),
    }),
  checkLineage: (runId: string) => request<LineageIntegrityIssue[]>(`/sandbox/lineage/check?runId=${encodeURIComponent(runId)}`),
  // CEO directive "TradeTown — Phase 8: Autonomous Strategy Discovery +
  // Adversarial Research Engine." See backend/app/research_discovery.py.
  runResearchDiscoveryCycle: (
    conceptName: string,
    populationSize: number,
    seed: string,
    proposedBy: AgentId,
    options?: { families?: StrategyFamily[]; symbols?: string[] }
  ) =>
    request<ResearchDiscoveryCycleRecord>("/sandbox/research-discovery/run", {
      method: "POST",
      body: JSON.stringify({
        conceptName,
        populationSize,
        seed,
        proposedBy,
        families: options?.families,
        symbols: options?.symbols,
      }),
    }),
  getResearchDiscoveryCycles: () => request<ResearchDiscoveryCycleRecord[]>("/sandbox/research-discovery/cycles"),
  getResearchDiscoveryCycleDetail: (cycleId: string) => request<ResearchDiscoveryCycleRecord>(`/sandbox/research-discovery/cycles/${encodeURIComponent(cycleId)}`),
  getResearchDiscoveryFamilyStats: () => request<FamilyResearchStats[]>("/sandbox/research-discovery/families"),
  getResearchDiscoverySupportedFamilies: () => request<{ supported: StrategyFamily[]; unsupported: Record<string, string> }>("/sandbox/research-discovery/supported-families"),
  // CEO directive "Strategy Intelligence + Live Strategy Attribution,"
  // Phase 1 — the real Strategy Lab <-> CompiledStrategyDefinition
  // identity bridge. See backend/app/strategy_registry.py's
  // register_researchable_strategy().
  registerResearchableStrategy: (name: string, description: string, sourceText: string, timeframe = "1h", focusCategory: ResearchCategory = "stock") =>
    request<RegisterResearchableStrategyResult>("/sandbox/register-researchable-strategy", {
      method: "POST",
      body: JSON.stringify({ name, description, sourceText, timeframe, focusCategory }),
    }),
  // CEO directive "Strategy Intelligence + Live Strategy Attribution,"
  // Phase 11 — "TODAY: strategies currently eligible/blocked," computed
  // fresh against the always-current live regime, never the once-daily
  // MarketIntelligenceReport's own stale copy.
  getLiveStrategyEligibility: () => request<StrategyMatch>("/sandbox/live-strategy-eligibility"),
  // CEO directive "Professional Quant Firm Phase," Feature 36 — the
  // Quant Research Lab's real, persisted, searchable experiment record.
  // See backend/app/quant_research_lab.py.
  // expectedMechanism/falsificationCriteria are required (CEO directive
  // "Quant Research Factory / Strategy Discovery Engine," Phase 1) —
  // real discipline on every new filing, not free-text padding.
  submitQuantResearchExperiment: (definition: CompiledStrategyDefinition, hypothesis: string, researcherAgentId: AgentId, expectedMechanism: string, falsificationCriteria: string) =>
    request<SubmitQuantResearchExperimentResult>("/sandbox/quant-research-lab/experiments", {
      method: "POST",
      body: JSON.stringify({ definition, hypothesis, researcherAgentId, expectedMechanism, falsificationCriteria }),
    }),
  searchQuantResearchExperiments: (filters: { symbol?: string; definitionId?: string; timeframe?: string; agentId?: string; outcome?: string } = {}) => {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(filters)) if (value) query.set(key, value);
    const suffix = query.toString();
    return request<QuantResearchExperiment[]>(`/sandbox/quant-research-lab/experiments${suffix ? `?${suffix}` : ""}`);
  },
  checkSimilarQuantResearchExperiments: (hypothesis: string, definitionId: string, timeframe: string) =>
    request<QuantResearchExperimentSimilarity[]>(
      `/sandbox/quant-research-lab/similar?${new URLSearchParams({ hypothesis, definitionId, timeframe }).toString()}`
    ),
  // CEO directive "Professional Quant Firm Phase," Feature 40 — the
  // Quant Strategy Tournament. See backend/app/strategy_tournament.py.
  runStrategyTournament: (definitions: CompiledStrategyDefinition[]) =>
    request<StrategyTournamentResult>("/sandbox/strategy-tournament", {
      method: "POST",
      body: JSON.stringify({ definitions }),
    }),
  getSurvivorshipBias: (symbol: string) => request<SurvivorshipBiasRead>(`/sandbox/survivorship-bias?symbol=${encodeURIComponent(symbol)}`),
  // CEO directive "Phase 9: Real Market Data + Evidence Integrity
  // Foundation," Section 3. See backend/app/data_quality.py.
  getDataQuality: (symbol: string, timeframe: string, candlesPerSymbol?: number) =>
    request<DataQualityReport>(
      `/sandbox/data-quality?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}${candlesPerSymbol ? `&candlesPerSymbol=${candlesPerSymbol}` : ""}`,
    ),
  // v0.7 Feature 53 — Company Certification. Read-only, computed fresh
  // every call — `certified` is always a live read of current real
  // state (see StrategyCertification's own docstring in types.ts).
  getSandboxCertification: (strategyId: string) => request<StrategyCertification>(`/sandbox/certification?strategyId=${encodeURIComponent(strategyId)}`),
  // v0.7 Quantitative Research & Intelligence System, Piece 4 —
  // Meridian/CIO's most recent independent validation report for this
  // strategy. Read-only, computed fresh every call; null if the
  // strategy has never been through Company Review yet.
  getSandboxModelValidation: (strategyId: string) => request<ModelValidationReport | null>(`/sandbox/model-validation?strategyId=${encodeURIComponent(strategyId)}`),
  // Prop-Firm Risk Intelligence Addendum, Requirements 21/22/23/25
  // (Piece 10) — a real, on-demand Monte Carlo comparison of four named
  // evaluation-stage risk policies. Read-only, computed fresh every
  // call, never auto-generated in the background; null if the strategy
  // has no completed simulation runs yet.
  getEvaluationPolicyComparison: (strategyId: string, accountId?: string) => {
    const query = new URLSearchParams({ strategyId });
    if (accountId) query.set("accountId", accountId);
    return request<EvaluationPolicyComparisonReport | null>(`/sandbox/evaluation-policy-comparison?${query.toString()}`);
  },
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
      // CEO directive "Portfolio Construction, Capital Allocation &
      // Execution Realism," Phase 4 — a real CEO-configurable cap on
      // statistically correlated open positions (see
      // backend/app/schemas.py's RiskLimits.max_correlated_positions).
      maxCorrelatedPositions: number;
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
  // Prop-Firm Risk Intelligence Addendum, Piece 11a — a real,
  // deterministic forward projection, not a probability.
  getProjectedLoss: (n: number) => request<ProjectedLossPath>(`/risk-limits/projected-loss?n=${encodeURIComponent(n)}`),
  // CEO directive "Portfolio Risk Engine + Firm-Wide Risk Governance."
  // Read-only, computed fresh per request — see backend/app/
  // portfolio_risk.py. Never a trading-decision API on its own; the
  // real enforcement path is app/gatekeeper.py's existing vote pipeline.
  getPortfolioRiskSnapshot: () => request<PortfolioRiskSnapshot>("/risk-limits/portfolio-snapshot"),
  getPretradeRiskDecision: (symbol: string, proposedValue: number) =>
    request<PretradeRiskDecision>(`/risk-limits/pretrade-decision?symbol=${encodeURIComponent(symbol)}&proposed_value=${encodeURIComponent(proposedValue)}`),
  // CEO directive "Portfolio Risk Engine + Cross-Trade Capital
  // Allocation" — the real Marginal Risk Test (before/after portfolio
  // simulation). See backend/app/portfolio_risk.py.
  getMarginalPortfolioRiskDecision: (symbol: string, proposedValue: number) =>
    request<PortfolioMarginalRiskDecision>(`/risk-limits/marginal-decision?symbol=${encodeURIComponent(symbol)}&proposed_value=${encodeURIComponent(proposedValue)}`),
  // CEO directive "Layered Kill Switches" — one layer below the
  // firm-wide Emergency Stop. See backend/app/trading_restrictions.py.
  getTradingRestrictions: () => request<{ tradingRestrictions: TradingRestriction[] }>("/trading-restrictions"),
  activateTradingRestriction: (scope: RestrictionScope, target: string, reason: string) =>
    request<{ tradingRestrictions: TradingRestriction[] }>("/trading-restrictions/activate", {
      method: "POST",
      body: JSON.stringify({ scope, target, reason }),
    }),
  liftTradingRestriction: (restrictionId: string, reason: string) =>
    request<{ tradingRestrictions: TradingRestriction[] }>(`/trading-restrictions/${encodeURIComponent(restrictionId)}/lift`, {
      method: "POST",
      body: JSON.stringify({ reason }),
    }),
  // CEO directive "Portfolio Risk Engine + Firm-Wide Risk Governance,"
  // final follow-up. Read-only, computed fresh per request — see
  // backend/app/portfolio_monte_carlo.py. null when there isn't enough
  // real closed-trade history yet.
  getPortfolioMonteCarlo: () => request<PortfolioMonteCarloResult | null>("/risk-limits/portfolio-monte-carlo"),
  // CEO directive "Professional Quant Trading Core," Phase B P2 item —
  // see backend/app/analytics.py's compute_recovery_factor().
  getRecoveryFactor: () => request<RecoveryFactorRead>("/risk-limits/recovery-factor"),
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

  // CEO directive "TradeTown — Memecoin Sniper Agent." Paper-only,
  // simulated data throughout — see backend/app/memecoin_sniper.py's
  // own module docstring.
  getSniperStatus: () => request<SniperEngineStatusRead>("/sniper/status"),
  getSniperCandidates: (limit = 30) => request<SniperCandidate[]>(`/sniper/candidates?limit=${limit}`),
  getSniperPositions: (openOnly = false) => request<SniperPosition[]>(`/sniper/positions${openOnly ? "?openOnly=true" : ""}`),
  getSniperTrades: (limit = 100) => request<SniperTrade[]>(`/sniper/trades?limit=${limit}`),
  getSniperLeads: () => request<SniperLead[]>("/sniper/leads"),
  getSniperLessons: () => request<SniperLesson[]>("/sniper/lessons"),
  getSniperRisk: () => request<SniperRiskState>("/sniper/risk"),
  getSniperLiveArming: () => request<SniperLiveArmingStatus>("/sniper/live-arming"),
  updateSniperEngine: (payload: { status?: string; mode?: string; turbo?: boolean; copyTradingEnabled?: boolean }) =>
    request<SniperEngineStatusRead>("/sniper/engine", { method: "POST", body: JSON.stringify(payload) }),
  closeSniperPosition: (positionId: string) => request<SniperTrade>(`/sniper/positions/${encodeURIComponent(positionId)}/close`, { method: "POST" }),
};
