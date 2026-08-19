/** Shared domain types used across the game layer, UI layer, and network layer.
 * Mirrors backend/app/schemas.py — keep the two in sync when either changes. */

export type Direction = "up" | "down" | "left" | "right";

export type SceneId =
  | "MainMenuScene"
  | "LobbyScene"
  | "ScoutOfficeScene"
  | "CeoOfficeScene"
  | "BrainRoomScene"
  | "MeetingRoomScene"
  | "BreakRoomScene"
  | "SimulationLabScene"
  | "HallOfFameScene"
  | "PerformanceCenterScene"
  | "TradingFloorScene"
  | "MarketObservatoryScene"
  | "ExecutiveBoardroomScene";

// v0.7 Feature 24 — Meridian, the Chief Investment Officer, is the tenth
// agent. Unlike every other agent, the CIO never votes on a trade or
// generates a research signal — it only reviews already-real state.
// v0.7 Feature 39 — Keystone and Compass, the Original Founders, are the
// twelfth and thirteenth. Neither ever trades or earns Academy Knowledge
// Points — see backend/app/founders.py's module docstring.
// v0.7 — Vector, the Chief Quantitative Strategist, is the fourteenth.
// Leads every Black Box Research Project (see backend/app/black_box.py).
export type AgentId = "scout" | "atlas" | "echo" | "nova" | "scribe" | "coach" | "sentinel" | "pulse" | "guardian" | "cio" | "sage" | "keystone" | "compass" | "quant" | "forge";
export const AGENT_IDS: readonly AgentId[] = ["scout", "atlas", "echo", "nova", "scribe", "coach", "sentinel", "pulse", "guardian", "cio", "sage", "keystone", "compass", "quant"];

/** Every room an agent's schedule (or a meeting/break override) can place them in. */
export type AgentLocation =
  | "scout-office"
  | "brain-room"
  | "meeting-room"
  | "break-room"
  | "lobby"
  | "simulation-lab"
  | "hall-of-fame"
  | "performance-center"
  | "trading-floor"
  | "executive-boardroom";

export type TaskStatus = "pending" | "working" | "completed" | "failed";
export type TaskPriority = "low" | "normal" | "high";
export type TaskCategory =
  | "research"
  | "review"
  | "meeting"
  | "watchlist_update"
  | "news_scan"
  | "chart_analysis"
  | "documentation"
  | "coaching"
  | "simulation"
  | "paper_trading"
  | "analytics"
  | "risk_management"
  | "market_scanning"
  | "voting"
  | "trading";
export type NewsCategory = "company" | "discovery" | "market";

/** The eight research topics named in the v0.3 brief. */
export type ResearchCategory = "stock" | "etf" | "index" | "economy" | "gold" | "bitcoin" | "company" | "sector";
export type ResearchStatus = "queued" | "in_progress" | "completed";
export type MemoryCategory =
  | "research"
  | "meeting"
  | "whiteboard"
  | "event"
  | "discussion"
  | "discovery"
  | "future_trade"
  | "lesson"
  | "mistake"
  | "strategy"
  | "coach_review"
  | "simulation"
  | "paper_trade"
  | "alert"
  | "vote"
  | "decision"
  | "order"
  // v0.7 Feature 25 — a completed Academy knowledge project or a
  // knowledge-tier advancement.
  | "academy"
  // v0.7 Feature 25 — a real mentorship session between two agents.
  | "mentorship"
  // v0.7 Feature 24 — the CIO's own Monthly Executive Review.
  | "executive";

export type OrderSide = "buy" | "sell";
export type OrderStatus = "open" | "filled" | "closed" | "cancelled";
export type OrderType = "market" | "limit" | "stop" | "take_profit" | "stop_loss";
export type AlertType = "gap_up" | "gap_down" | "breakout" | "volume_spike" | "high_volatility";
export type AlertSeverity = "info" | "warning" | "critical";

// Design Bible Chapter 67 (TTOS) Part 3 — Smart Notification priority
// tiers. Derived from real fields this codebase already tags events
// with (RiskWarning.severity, save:failed, Emergency Stop activation),
// never invented — see CyberNotifications.tsx's own doc comment for
// exactly which real source maps to which tier.
export type NotificationTier = "critical" | "high" | "normal";

/** One entry in the CEO's real notification history (gameStore's
 * `alertHistory`), viewable in the Executive Alert Center
 * (AlertCenter.tsx) — every toast CyberNotifications.tsx ever shows is
 * also recorded here, so nothing the CEO glimpses and misses is lost. */
export interface AlertEntry {
  id: string;
  tier: NotificationTier;
  title: string;
  body: string;
  createdAt: string;
}
export type VoteChoice = "buy" | "sell" | "hold" | "risk_too_high" | "position_too_large";
export type DecisionOutcome = "trade" | "no_trade";
export type SimulationStatus = "queued" | "running" | "completed";
export type HallOfFameCategory =
  | "best_research"
  | "best_strategy"
  | "best_simulation"
  | "lowest_drawdown"
  | "winning_streak"
  | "highest_confidence_accuracy"
  | "best_month"
  | "top_agent"
  // v0.7 — Museum of Discoveries. Only HallOfFameEntry's
  // discoveryTimeline/supportingEvidence/companyImpact are ever
  // populated for this category (see backend/app/black_box.py).
  | "breakthrough";
export type PerformancePeriod = "daily" | "weekly" | "monthly" | "all_time";
export type ReportPeriod = "weekly" | "monthly";

export interface Vector2 {
  x: number;
  y: number;
}

export interface EntityTransform extends Vector2 {
  scene: SceneId;
  facing: Direction;
}

export interface DialogueHistoryEntry {
  id: string;
  speaker: AgentId | "player";
  line: string;
  timestamp: string; // ISO string
}

export interface MemoryEntry {
  id: string;
  summary: string;
  day: number;
  hour: number;
}

/** A temporary location override (meeting or break) that takes priority over an agent's normal schedule. */
export interface AgentOverride {
  location: AgentLocation;
  reason: "meeting" | "break";
  remainingMinutes: number;
}

export interface AgentState {
  transform: EntityTransform;
  location: AgentLocation;
  currentTask: string;
  mood: number; // 0-100
  energy: number; // 0-100
  memory: MemoryEntry[];
  override: AgentOverride | null;
}

export interface Task {
  id: string;
  owner: AgentId;
  category: TaskCategory;
  priority: TaskPriority;
  description: string;
  status: TaskStatus;
  createdAt: string;
  completedAt: string | null;
}

export interface NewsItem {
  id: string;
  headline: string;
  category: NewsCategory;
  timestamp: string;
}

export interface DiscussionMessage {
  id: string;
  speaker: AgentId;
  line: string;
  timestamp: string;
}

export interface MeetingState {
  active: boolean;
  participants: AgentId[];
  discussion: DiscussionMessage[];
}

/** One topic in the rotating research queue (see backend/app/research.py) — each research-capable agent (everyone but Scribe) always has exactly one "in_progress" at a time. */
export interface ResearchItem {
  id: string;
  title: string;
  symbol: string | null;
  category: ResearchCategory;
  priority: TaskPriority;
  status: ResearchStatus;
  assignedAgent: AgentId;
  summary: string;
  confidence: number; // 0-100
  createdAt: string;
  updatedAt: string;
}

export interface WatchlistEntry {
  symbol: string;
  name: string;
  lastPrice: number;
  dailyChangePct: number;
  status: ResearchStatus;
  researchProgress: number; // 0-100
  assignedAgent: AgentId | null;
}

// v0.6.2 Market Data Abstraction. Mirrors backend/app/schemas.py's Candle —
// never part of GameSaveState (chart data is regenerable from the
// provider on demand, not game progress), fetched on its own from
// GET /api/market/candles instead of riding along on save/load or the
// WebSocket state broadcast.
export type DataStatus = "live" | "delayed" | "historical" | "simulated" | "stale" | "error" | "no_data";
export type Timeframe = "1m" | "5m" | "15m" | "1h" | "4h" | "1d";

export interface Candle {
  symbol: string;
  timeframe: string;
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  dataStatus: DataStatus;
}

// v0.6.2 Agent Energy — a company-wide spendable resource distinct from
// AgentState.energy (each agent's individual fatigue/rest level). Spent on
// research_boost / extra_simulation / watch_symbol via POST /api/energy/spend.
export interface AgentEnergy {
  current: number;
  cap: number;
  updatedAt: string;
}

// v0.6.2 Signal Calibration mini-game — see backend/app/signal_calibration.py.
// SignalChallenge is never part of GameSaveState (regenerable practice
// content); only SignalCalibrationState (progress) is persisted.
export type SignalChoice = "enter" | "wait" | "avoid";

export interface SignalChallenge {
  id: string;
  level: number;
  symbol: string;
  timeframe: string;
  candles: Candle[];
  prompt: string;
  factors: string[];
  createdAt: string;
}

export interface SignalCalibrationAttempt {
  id: string;
  level: number;
  symbol: string;
  choice: SignalChoice;
  correctChoice: SignalChoice;
  correct: boolean;
  energyAwarded: number;
  rubricNotes: string;
  createdAt: string;
}

export interface SignalCalibrationState {
  unlockedLevel: number;
  attempts: SignalCalibrationAttempt[];
  correctCount: number;
  totalCount: number;
}

// v0.6.2 Player vs AI — see backend/app/player_vs_ai.py. Only decisions
// that led to a trade with a real, already-closed outcome are eligible,
// so grading is always against a real realized P&L, never a guess.
export type MarketRegime = "trending_up" | "trending_down" | "ranging";

export interface PlayerVsAiPrompt {
  id: string;
  decisionId: string;
  symbol: string;
  category: ResearchCategory;
  researchSummary: string;
  technicalSummary: string;
  riskSummary: string;
  confidence: number;
  regime: MarketRegime;
  createdAt: string;
}

export interface PlayerVsAiRound {
  id: string;
  decisionId: string;
  symbol: string;
  category: ResearchCategory;
  regime: MarketRegime;
  playerChoice: SignalChoice;
  aiChoice: SignalChoice;
  realizedPnlPct: number;
  groundTruthChoice: SignalChoice;
  playerCorrect: boolean;
  aiCorrect: boolean;
  createdAt: string;
}

export interface PlayerVsAiState {
  rounds: PlayerVsAiRound[];
  playerCorrectCount: number;
  aiCorrectCount: number;
  totalCount: number;
}

// v0.6.2 Trading Education — see backend/app/education.py. EducationLesson
// is static curriculum content, fetched once (never part of GameSaveState
// or the WS broadcast); only EducationProgress persists as real progress.
export type EducationTopic =
  | "candlesticks"
  | "wicks"
  | "trends"
  | "support_resistance"
  | "enter_wait_avoid"
  | "stop_loss"
  | "take_profit"
  | "risk_reward"
  | "position_sizing"
  | "no_trade_ok"
  // v0.7 Feature 49 (Phase 2) — the Liquidity/Market Structure module.
  | "liquidity_basics"
  | "swing_structure"
  | "equal_highs_lows"
  | "liquidity_sweeps"
  | "inducement"
  | "structure_shifts"
  | "premium_discount"
  | "order_flow_intro";

export interface EducationLesson {
  id: EducationTopic;
  order: number;
  title: string;
  simpleExplanation: string;
  visualExampleNote: string;
  deeperExplanation: string;
  quizQuestion: string;
  quizOptions: string[];
}

export interface EducationProgress {
  viewedLessonIds: string[];
  completedLessonIds: string[];
  quizAttempts: number;
  correctQuizAttempts: number;
}

export interface MeetingMinutes {
  id: string;
  day: number;
  hour: number;
  minute: number;
  participants: AgentId[];
  summary: string;
  discussion: DiscussionMessage[];
}

/** One entry in CompanyMemory — TradeTown's searchable long-term log (see backend/app/memory.py). */
export interface MemoryRecord {
  id: string;
  category: MemoryCategory;
  title: string;
  body: string;
  timestamp: string;
}

/** A paper order — simulated only, never sent to a real brokerage. `price` means
 * different things per `orderType`: ignored for "market"; the limit/target price
 * for "limit"/"take_profit"; the trigger price for "stop"/"stop_loss".
 * `linkedPositionId` is set for an exit order attached to an existing position. */
export interface PaperOrder {
  id: string;
  symbol: string;
  side: OrderSide;
  orderType: OrderType;
  quantity: number;
  price: number;
  status: OrderStatus;
  placedBy: AgentId;
  reason: string;
  confidence: number;
  linkedPositionId: string | null;
  filledPrice: number | null;
  filledAt: string | null;
  createdAt: string;
}

export interface PaperPosition {
  id: string;
  symbol: string;
  side: OrderSide;
  quantity: number;
  entryPrice: number;
  currentPrice: number;
  unrealizedPnl: number;
  unrealizedPnlPct: number;
  openedBy: AgentId;
  confidence: number;
  openedAt: string;
  /** Simulated-clock minutes-since-epoch (day*1440 + hour*60 + minute) at open time. */
  openedSimMinutes: number;
  /** Quantitative Research & Intelligence System, Piece 5 (Execution
   * Quant) — the real dollar transaction cost charged at entry (a flat,
   * disclosed basis-points constant, see backend/app/portfolio.py's
   * TRANSACTION_COST_BPS/module docstring — never derived from real
   * spread/order-book data, which this codebase does not have). 0.0 for
   * any position opened before this piece. */
  entryCostUsd: number;
  /** CEO directive "Next Professional Trading Firm Phase," Priority 1
   * (Execution Realism) — the real slippage, in basis points, applied
   * to this position's fill price at entry. Derived from that tick's
   * real MarketIntelligenceState (see backend/app/execution_quality.py)
   * — never fabricated or random. 0.0 for any entry filled without a
   * MarketIntelligenceState in scope. */
  entrySlippageBps: number;
  /** CEO Company Health + Live Market Realism directive, Feature 24 —
   * MAE (Maximum Adverse Excursion) / MFE (Maximum Favorable
   * Excursion): a real running watermark of the worst/best
   * unrealizedPnlPct this position has actually shown since it opened,
   * updated every tick from the same real live prices unrealizedPnl
   * already reads. Both start at 0.0 and only ever move toward their
   * own real extreme. */
  maePct: number;
  mfePct: number;
}

/** One closed paper position — the Learning System's "training data" record (v0.5 brief Feature 5). */
export interface PaperTrade {
  id: string;
  symbol: string;
  side: OrderSide;
  quantity: number;
  entryPrice: number;
  exitPrice: number;
  pnl: number;
  pnlPct: number;
  durationMinutes: number;
  confidence: number;
  reason: string;
  marketConditions: string;
  supportingAgents: AgentId[];
  opposingAgents: AgentId[];
  coachReview: string | null;
  lessonsLearned: string | null;
  /** Links back to the TradeDecision that approved the order behind this trade —
   * best-effort attribution, not always resolvable (see backend/app/nexus.py). */
  decisionId: string | null;
  /** Always a fixed placeholder — TradeTown has no chart-rendering pipeline. */
  screenshot: string | null;
  openedAt: string;
  closedAt: string;
  /** Simulated-clock minutes-since-epoch (day*1440 + hour*60 + minute) — same convention as PaperPosition.openedSimMinutes. `closedSimMinutes` is always `openedSimMinutes + durationMinutes`. Added in v0.6.1 so monthly P&L can bucket by TradeTown's in-game calendar instead of real wall-clock time (openedAt/closedAt above remain real timestamps, kept only for audit/display). */
  openedSimMinutes: number;
  closedSimMinutes: number;
  /** Quantitative Research & Intelligence System, Piece 5 (Execution
   * Quant) — the real combined round-trip transaction cost (entry +
   * exit) already subtracted from `pnl` above; kept here purely for
   * audit visibility. 0.0 for any trade closed before this piece. */
  transactionCostUsd: number;
  /** CEO directive "Next Professional Trading Firm Phase," Priority 1
   * (Execution Realism) — real slippage in basis points, applied at
   * entry (carried over from the position this trade closed) and at
   * exit. Distinct from transactionCostUsd above (a flat commission/
   * spread proxy) — slippage instead varies tick-to-tick with that
   * tick's own real market-quality/liquidity read. 0.0 for any fill
   * without a MarketIntelligenceState in scope. */
  entrySlippageBps: number;
  exitSlippageBps: number;
  /** Prop-Firm Risk Intelligence Addendum, Piece 10b — real distance to
   * the primary portfolio's own drawdown ceiling (RiskLimits.
   * maxDrawdownPct — a self-chosen ceiling, not a true externally-
   * imposed boundary; see AccountRiskBudgetStatus for the one real
   * externally-configurable boundary this codebase has), snapshotted
   * before and after this trade. null when this trade closed without a
   * real RiskLimits in scope — never a fabricated value. */
  distanceToDrawdownCeilingBeforePct: number | null;
  distanceToDrawdownCeilingAfterPct: number | null;
  /** CEO Company Health + Live Market Realism directive, Feature 24 —
   * carried over from the PaperPosition this trade closed. See
   * PaperPosition.maePct/mfePct above for the full explanation. 0.0 for
   * any trade closed before this piece. */
  maePct: number;
  mfePct: number;
}

// CEO directive "Professional Trading Firm Transformation" — Post-Trade
// Review, Exit Efficiency (see backend/app/exit_efficiency.py). A real,
// continuous read of where a trade closed within its OWN observed
// high/low range — 100 means it closed at the best point ever reached,
// 0 means the worst. Distinct from and never touching the Discipline
// Chamber's outcome-blind process score or the Failure Review Board's
// WHY-the-thesis-failed classification above.
export type ExitEfficiencyState = "efficient_exit" | "average_exit" | "poor_exit" | "not_enough_data";

export interface TradeExitEfficiency {
  tradeId: string;
  symbol: string;
  pnlPct: number;
  maePct: number;
  mfePct: number;
  capturePct: number | null;
  evidenceState: ExitEfficiencyState;
  simDay: number;
}

export interface ExitEfficiencySummary {
  reads: TradeExitEfficiency[];
  avgCapturePct: number | null;
  efficientExitCount: number;
  averageExitCount: number;
  poorExitCount: number;
  notEnoughDataCount: number;
  updatedAt: string;
}

// CEO directive "Next Professional Trading Firm Phase," Priority 2 —
// Unified Professional P&L/Performance Reporting, scoped this pass to
// real, unambiguous SYMBOL-level attribution (see
// backend/app/performance_attribution.py's module docstring for why
// agent- and strategy-level breakdowns are deliberately not built yet).
export type SymbolPerformanceEvidenceState = "sufficient_evidence" | "not_enough_data";

export interface SymbolPerformanceRead {
  symbol: string;
  tradeCount: number;
  winCount: number;
  lossCount: number;
  winRatePct: number;
  totalPnl: number;
  avgPnlPct: number;
  /** null when this symbol has no winning (or no losing) trades yet — never a fabricated 0. */
  avgWinnerPct: number | null;
  avgLoserPct: number | null;
  /** Standard win-rate/avg-win/avg-loss decomposition — algebraically the same as avgPnlPct
   * under this same win/loss partition, shown separately because the decomposition itself is
   * diagnostic. null below tradeCount's disclosed minimum sample (see evidenceState). */
  expectancyPct: number | null;
  /** Gross profit / gross loss. null — a real "undefined," not a fabricated infinity — when
   * this symbol has zero losing trades yet. */
  profitFactor: number | null;
  avgMaePct: number;
  avgMfePct: number;
  bestTradePnlPct: number;
  worstTradePnlPct: number;
  evidenceState: SymbolPerformanceEvidenceState;
}

/** `reads` sorted by totalPnl descending — the most profitable symbol first. */
export interface SymbolPerformanceSummary {
  reads: SymbolPerformanceRead[];
  updatedAt: string;
}

// CEO directive "Next Phase: Professional Trading Firm Intelligence,"
// Phase 3 — Session + Market Regime P&L. Same 12-metric shape as
// SymbolPerformanceRead above, joined via the real Decision Vault (a
// trade with no matching vault entry is excluded and counted in
// tradesExcludedNoVaultEntry, never fabricated into a bucket).
export interface SessionPerformanceRead {
  session: TradingSession;
  tradeCount: number;
  winCount: number;
  lossCount: number;
  winRatePct: number;
  totalPnl: number;
  avgPnlPct: number;
  avgWinnerPct: number | null;
  avgLoserPct: number | null;
  expectancyPct: number | null;
  profitFactor: number | null;
  avgMaePct: number;
  avgMfePct: number;
  bestTradePnlPct: number;
  worstTradePnlPct: number;
  evidenceState: SymbolPerformanceEvidenceState;
}

export interface SessionPerformanceSummary {
  reads: SessionPerformanceRead[];
  tradesExcludedNoVaultEntry: number;
  updatedAt: string;
}

export interface RegimePerformanceRead {
  regime: MarketIntelligenceRegime;
  tradeCount: number;
  winCount: number;
  lossCount: number;
  winRatePct: number;
  totalPnl: number;
  avgPnlPct: number;
  avgWinnerPct: number | null;
  avgLoserPct: number | null;
  expectancyPct: number | null;
  profitFactor: number | null;
  avgMaePct: number;
  avgMfePct: number;
  bestTradePnlPct: number;
  worstTradePnlPct: number;
  evidenceState: SymbolPerformanceEvidenceState;
}

export interface RegimePerformanceSummary {
  reads: RegimePerformanceRead[];
  tradesExcludedNoVaultEntry: number;
  updatedAt: string;
}

// CEO directive "Next Professional Trading Firm Phase," Priority 5 —
// Research Data Integrity. Distinct from DataStatus above (which tags
// one Candle's own live/delayed/historical/simulated/stale/error/
// no_data read) — DataCategory classifies a whole SUBSYSTEM's data
// source, the coarser question this directive asks.
export type DataCategory = "real" | "synthetic" | "simulated" | "user_provided" | "unavailable";

export interface DataSourceRead {
  subsystem: string;
  category: DataCategory;
  detail: string;
  /** null when not meaningfully applicable to this subsystem. */
  reproducible: boolean | null;
  coveragePct: number | null;
}

/** sources is a fixed architectural enumeration except the "Live Quotes & Candles" row,
 * whose coveragePct/category are live-measured against the real provider on every request. */
export interface DataProvenanceReport {
  sources: DataSourceRead[];
  updatedAt: string;
}

// CEO directive "Next Phase: Professional Trading Firm Intelligence,"
// Phase 1 — Symbol -> Agent Attribution. Preserves real per-agent
// evidence per trade (who advised what, whether it agreed with the side
// actually traded, real CEO-override/risk-approval provenance) — never
// a numeric P&L-per-agent credit split, since no CEO-authorized
// methodology for one exists (see backend/app/trade_attribution.py).
export interface AgentContributionRead {
  agentId: AgentId;
  role: AnalystRole;
  choice: VoteChoice;
  reason: string;
  agreedWithSideTraded: boolean;
}

export type TradeAttributionEvidenceState = "full_evidence" | "no_decision_on_record";

export interface TradeAttributionRecord {
  tradeId: string;
  decisionId: string | null;
  symbol: string;
  contributions: AgentContributionRead[];
  supportingAgents: AgentId[];
  opposingAgents: AgentId[];
  ceoChoice: AnalystChoice | null;
  ceoOverrodeTheDesk: boolean | null;
  gatekeeperApproved: boolean | null;
  entrySlippageBps: number;
  exitSlippageBps: number;
  transactionCostUsd: number;
  pnl: number;
  pnlPct: number;
  evidenceState: TradeAttributionEvidenceState;
  creditSplitNote: string;
}

export interface TradeAttributionSummary {
  records: TradeAttributionRecord[];
  updatedAt: string;
}

/** The company's one simulated trading account — entirely fictional. */
export interface PaperPortfolio {
  cashBalance: number;
  startingBalance: number;
  positions: PaperPosition[];
  orders: PaperOrder[];
  tradeHistory: PaperTrade[];
  totalPnl: number;
  totalPnlPct: number;
  winCount: number;
  lossCount: number;
}

// Design Bible Chapter 69 Part 1 — Multi-Account & Fund Management
// System. See backend/app/accounts.py's module docstring for the honest
// scope: a real, CEO-manageable capital ledger, not yet wired to live
// per-account trading execution.
export type AccountType = "personal" | "ira" | "business" | "prop_firm" | "family";

export const ACCOUNT_TYPE_LABEL: Record<AccountType, string> = {
  personal: "Personal Trading Account",
  ira: "IRA / Retirement Account",
  business: "Business Trading Account",
  prop_firm: "Prop Firm Challenge Account",
  family: "Family Trust Account",
};

export interface Account {
  id: string;
  name: string;
  accountType: AccountType;
  portfolio: PaperPortfolio;
  riskLimits: RiskLimits;
  createdAt: string;
  // Design Bible Chapter 69 Part 2 — Prop Firm Rule Engine.
  peakEquity: number;
  trailingDrawdownLimitPct: number | null;
  consistencyLimitPct: number | null;
  challengeStartSimDay: number | null;
  challengeDurationDays: number | null;
  challengeProfitTargetPct: number | null;
  // Design Bible Chapter 69 Part 3 — Institutional Rule Engine.
  customRules: Rule[];
  // Prop-Firm Risk Intelligence Addendum, Piece 10a — real,
  // CEO-recorded evaluation-cost / funded-stage / payout data. Never
  // auto-derived from a probability model — only ever set by an
  // explicit CEO action.
  evaluationCost: number | null;
  fundedStageReached: boolean;
  fundedAtSimDay: number | null;
  payoutEligibilityMinProfitPct: number | null;
  totalPayoutsReceived: number;
}

// Design Bible Chapter 69 Part 2 — the Weekday-Aware Time System. Real,
// derived infrastructure: day 1 is defined as a Monday (see
// backend/app/prop_firm.py's weekday_for()).
export type Weekday = "monday" | "tuesday" | "wednesday" | "thursday" | "friday" | "saturday" | "sunday";

export interface TrailingDrawdownStatus {
  peakEquity: number;
  currentEquity: number;
  drawdownPct: number;
  limitPct: number | null;
  breached: boolean;
}

export interface ConsistencyStatus {
  applicable: boolean;
  cumulativeProfit: number;
  largestSingleDayProfit: number;
  largestSingleDaySharePct: number;
  limitPct: number | null;
  breached: boolean;
}

export interface ScalingMilestoneStatus {
  currentTier: number;
  equityGrowthPct: number;
  nextTierGrowthThresholdPct: number | null;
}

export interface ChallengeProgressStatus {
  applicable: boolean;
  startedSimDay: number | null;
  durationDays: number | null;
  daysElapsed: number;
  daysRemaining: number | null;
  profitPct: number;
  targetPct: number | null;
  onPace: boolean | null;
}

export interface PropFirmComplianceScore {
  overall: number;
  drawdownSafety: number;
  consistency: number;
  ruleCompliance: number;
  riskExposure: number;
  capitalPreservation: number;
}

export interface PropFirmStatus {
  accountId: string;
  weekday: Weekday;
  trailingDrawdown: TrailingDrawdownStatus;
  consistency: ConsistencyStatus;
  scaling: ScalingMilestoneStatus;
  challenge: ChallengeProgressStatus;
  complianceScore: PropFirmComplianceScore;
  riskBudget: AccountRiskBudgetStatus;
  evaluationTracking: EvaluationTrackingStatus;
  leverageNote: string;
}

/** Prop-Firm Risk Intelligence Addendum, Piece 10a — evaluation cost,
 * funded-stage, and payout tracking. fundedStageReached is a real,
 * explicit CEO action (never a system-inferred pass/fail — that honest
 * judgment call is Piece 10's job, a real evaluation-policy simulator).
 * payoutEligible is null, not false, when no threshold was configured —
 * "not eligible" and "no threshold set" are different honest states. */
export interface EvaluationTrackingStatus {
  accountId: string;
  evaluationCost: number | null;
  fundedStageReached: boolean;
  fundedAtSimDay: number | null;
  daysToFund: number | null;
  payoutEligibilityMinProfitPct: number | null;
  payoutEligible: boolean | null;
  totalPayoutsReceived: number;
  computedAt: string;
}

// Design Bible Chapter 69 Part 3 — Institutional Rule Engine (IRE). A
// closed, named set of rule types (never a free-text DSL — no rule
// parser exists anywhere in this codebase) — see
// backend/app/rule_engine.py's module docstring for the honest scope.
export type RuleType =
  | "max_daily_loss_pct"
  | "max_drawdown_pct"
  | "max_position_pct"
  | "max_open_positions"
  | "max_risk_per_trade_pct"
  | "trailing_drawdown_pct"
  | "consistency_pct"
  | "no_trading_on_weekday";

export const RULE_TYPE_LABEL: Record<RuleType, string> = {
  max_daily_loss_pct: "Max Daily Loss",
  max_drawdown_pct: "Max Drawdown",
  max_position_pct: "Max Position Size",
  max_open_positions: "Max Open Positions",
  max_risk_per_trade_pct: "Max Risk Per Trade",
  trailing_drawdown_pct: "Trailing Drawdown",
  consistency_pct: "Consistency Limit",
  no_trading_on_weekday: "No Trading On Weekday",
};

export interface Rule {
  id: string;
  ruleType: RuleType;
  label: string;
  limit: number;
  weekday: Weekday | null;
  enabled: boolean;
}

export interface RuleCheckResult {
  ruleId: string;
  label: string;
  passed: boolean;
  detail: string;
  correctiveAction: string | null;
}

export interface RuleEvaluationResult {
  accountId: string;
  simDay: number;
  checks: RuleCheckResult[];
  allPassed: boolean;
}

// v0.7 Feature 45 — the Research Sandbox. TestScenario reuses the exact
// 5 regime names market_environment.py already computes live, plus
// "historical" (the pre-Feature-45 default) and "custom" (a CEO-tunable
// bias — see backend/app/sandbox.py's module docstring for why
// "earnings_weeks"/"economic_news" aren't included: no real data source).
export type TestScenario = "historical" | "bull" | "bear" | "sideways" | "high_volatility" | "low_volatility" | "custom";

// Strategies cannot skip stages — see backend/app/sandbox.py. "retired" is
// v0.7 Feature 52 (Part 2) — the only terminal stage, reachable from any
// prior stage via a real, deliberate CEO action (never automatic).
export type StrategyStage = "idea" | "research" | "historical_backtest" | "market_simulation" | "paper_trading" | "limited_live_capital" | "company_review" | "approved" | "retired";

export interface StrategyStageEvent {
  id: string;
  stage: StrategyStage;
  detail: string;
  simDay: number;
  createdAt: string;
}

export interface Strategy {
  id: string;
  name: string;
  description: string;
  createdBy: AgentId;
  focusCategory: ResearchCategory;
  createdAt: string;
  stage: StrategyStage;
  stageHistory: StrategyStageEvent[];
  allocatedCapital: number;
}

/** A strategy simulation in flight — queued or running in the Simulation Lab. */
export interface BacktestSession {
  id: string;
  strategyId: string;
  strategyName: string;
  symbol: string;
  status: SimulationStatus;
  progress: number;
  runBy: AgentId;
  queuedAt: string;
  startedAt: string | null;
  scenario: TestScenario;
  customReturnBiasPct: number;
  customVolatilityBias: number;
}

/** sharpeRatio/sortinoRatio are explicitly placeholder formulas — see backend/app/simulation.py. */
export interface SimulationResult {
  id: string;
  strategyId: string;
  strategyName: string;
  symbol: string;
  totalReturnPct: number;
  winRate: number;
  maxDrawdownPct: number;
  sharpeRatio: number;
  sortinoRatio: number;
  tradeCount: number;
  runBy: AgentId;
  completedAt: string;
  scenario: TestScenario;
  winCount: number;
  lossCount: number;
  avgWinPct: number;
  avgLossPct: number;
  expectedValuePct: number;
  profitFactor: number;
  riskRewardRatio: number;
}

// v0.7 Feature 45 — auto-generated whenever a SimulationResult completes.
export interface StrategyReport {
  id: string;
  strategyId: string;
  strategyName: string;
  sourceResultId: string;
  scenario: TestScenario;
  executiveSummary: string;
  strengths: string[];
  weaknesses: string[];
  failureConditions: string[];
  bestMarketEnvironment: string;
  recommendedImprovements: string[];
  simDay: number;
  createdAt: string;
}

export type StrategyReviewerRole = "quant" | "risk" | "technical" | "fundamental" | "devils_advocate";
export type StrategyVerdict = "pass" | "concern" | "fail";

export interface StrategyReviewVerdict {
  reviewerRole: StrategyReviewerRole;
  reviewerAgent: AgentId;
  verdict: StrategyVerdict;
  summary: string;
}

export interface StrategyReview {
  id: string;
  strategyId: string;
  strategyName: string;
  verdicts: StrategyReviewVerdict[];
  overallVerdict: StrategyVerdict;
  ceoDecision: "pending" | "approved" | "rejected";
  resolvedBy: "ceo" | "auto" | null;
  simDay: number;
  createdAt: string;
}

// v0.7 Feature 52 (Part 1) — the Strategy Validation Laboratory. See
// backend/app/strategy_lab.py's module docstring for the full honesty
// boundary each of these observes (never a second measurement engine,
// never fabricated statistics beyond a strategy's own real
// SimulationResult history).
export interface StrategyMonteCarloResult {
  id: string;
  strategyId: string;
  strategyName: string;
  pathsSimulated: number;
  tradesPerPath: number;
  sourceWinRate: number;
  sourceAvgWinPct: number;
  sourceAvgLossPct: number;
  medianReturnPct: number;
  returnRangeLowPct: number;
  returnRangeHighPct: number;
  medianMaxDrawdownPct: number;
  worstCaseDrawdownPct: number;
  probabilityOfProfitPct: number;
  /** A real share of this run's own paths that breached a named
   * drawdown bar — never a true infinite-sample probability of ruin. */
  probabilityOfRuinPct: number;
  capitalSurvivalPct: number;
  /** Quantitative Research & Intelligence System, Piece 3 — real
   * percentile/tail-mean reads off this same bootstrap's own sorted
   * final-return array (no new simulation). VaR = the return level such
   * that only 5%/1% of paths did worse (signed: negative = a loss); CVaR
   * (Expected Shortfall) = the mean return among exactly that worst
   * 5%/1% of paths — what to expect *given* you're in the tail. */
  valueAtRisk95Pct: number;
  valueAtRisk99Pct: number;
  conditionalValueAtRisk95Pct: number;
  conditionalValueAtRisk99Pct: number;
  simDay: number;
  createdAt: string;
}

/** Quantitative Research & Intelligence System, Piece 7 — Forge, the
 * Quant Developer. A real, standing engineering fact about the Monte
 * Carlo bootstrap pipeline itself (backend/app/strategy_lab.py's
 * MONTE_CARLO_PATHS, a fixed global constant) — NOT a per-strategy
 * finding, since every real run shares that same constant. Recomputed
 * fresh on every read, never persisted. Distinct from Meridian's
 * ModelValidationReport, which reviews a strategy's evidence, never
 * the sample-size adequacy of the tool that produced it. */
export type MonteCarloReliabilityVerdict = "reliable" | "marginal" | "unreliable";

export interface MonteCarloReliabilityAssessment {
  developerAgentId: "forge";
  pathsSimulated: number;
  tailSampleCount95Pct: number;
  tailSampleCount99Pct: number;
  verdict95Pct: MonteCarloReliabilityVerdict;
  verdict99Pct: MonteCarloReliabilityVerdict;
  minReliableTailSamples: number;
  minMarginalTailSamples: number;
  recommendedPathsForReliable99Pct: number;
  realResultsAudited: number;
  observedPathCountsConsistent: boolean;
  reasoning: string;
  thresholdSource: string;
  generatedAt: string;
}

/** SimulationResult is only ever tagged at the coarser 7-way TestScenario
 * grain — `regimes` honestly labels which of Feature 51's real 13-way
 * MarketIntelligenceRegimes this bucket covers, never claiming
 * independently-tested 13-way granularity. */
export interface StrategyRegimeBucketPerformance {
  scenario: TestScenario;
  regimes: MarketIntelligenceRegime[];
  tested: boolean;
  runCount: number;
  avgReturnPct: number;
  avgWinRate: number;
  verdict: "strong" | "weak" | "neutral" | "untested";
}

export interface StrategyRegimeTestReport {
  id: string;
  strategyId: string;
  strategyName: string;
  buckets: StrategyRegimeBucketPerformance[];
  bestScenario: TestScenario | null;
  worstScenario: TestScenario | null;
  simDay: number;
  createdAt: string;
}

/** Reuses Feature 51's real compute_liquidity()/compute_market_structure()
 * against the strategy's own watched symbols, as-is. */
export interface StrategyLiquidityValidation {
  id: string;
  strategyId: string;
  strategyName: string;
  symbolsChecked: string[];
  liquidityReads: LiquidityRead[];
  structureReads: MarketStructureRead[];
  realSweepRatePct: number;
  verdict: "favorable" | "neutral" | "unfavorable";
  detail: string;
  simDay: number;
  createdAt: string;
}

// v0.7 — Quantitative Research & Intelligence System, Piece 4: the
// Model Validator (Meridian/CIO). See backend/app/model_validation.py's
// module docstring for the full honesty boundary — every check reuses
// an existing, already-load-bearing Strategy Lab Certification-gate
// threshold (never a new invented number), and the whole report is
// advisory-only: nothing in the Company Review approve/reject flow
// reads `verdict`.
export type ModelValidationVerdict = "approved" | "rejected" | "needs_more_evidence" | "not_validatable";

export interface ModelValidationCheck {
  id: string;
  label: string;
  /** null means this check could not be evaluated yet (the underlying
   * artifact doesn't exist for this strategy yet) — never coerced to
   * true/false. */
  passed: boolean | null;
  evidence: string;
  reasoning: string;
  /** Always cites exactly which existing constant/pattern this check
   * reused — never blank, since Piece 4 introduces no new numeric bar. */
  thresholdSource: string;
}

export interface ModelValidationReport {
  id: string;
  strategyId: string;
  strategyName: string;
  reviewId: string;
  existingReviewCount: number;
  verdict: ModelValidationVerdict;
  checks: ModelValidationCheck[];
  validatorAgentId: "cio";
  evidenceSummary: string;
  /** What real data each check drew on, and what this report does NOT
   * independently establish — independence here is organizational/
   * decision independence, not statistical independence. */
  dataSourcesAndAssumptions: string[];
  simDay: number;
  createdAt: string;
}

// Deliberately distinct from the trade-scoped ExecutiveAction —
// strategy-lifecycle semantics differ from single-trade semantics.
export type StrategyExecutiveAction = "advance" | "request_more_evidence" | "hold_for_improvement" | "reject";

export interface StrategyDepartmentOpinion {
  role: ExecutiveDepartmentRole;
  departmentLabel: string;
  agentId: AgentId | null;
  stance: ExecutiveStance;
  confidencePct: number;
  evidence: string[];
  concerns: string[];
  suggestedImprovements: string[];
}

/** The brief's 9-department Executive Review — reuses the exact same
 * nine real department seats as Feature 50's ExecutiveDepartmentRole;
 * "Brain Room" reuses the same devils_advocate seat every other 9-role
 * read in this codebase already does. */
export interface StrategyExecutiveReview {
  id: string;
  strategyId: string;
  strategyName: string;
  opinions: StrategyDepartmentOpinion[];
  overallConfidencePct: number;
  recommendation: StrategyExecutiveAction;
  reason: string;
  simDay: number;
  createdAt: string;
}

/** A new mode of the same real threshold-based approval pattern
 * app/founders.py's generate_breakthrough_review() already established
 * for Black Box Projects, applied here to a Strategy. */
export interface StrategyFounderApproval {
  id: string;
  strategyId: string;
  strategyName: string;
  simDay: number;
  evidenceSummary: string;
  confidencePct: number;
  verdict: "approved" | "rejected";
  verdictReason: string;
  createdAt: string;
}

export interface StrategyConfidenceScore {
  id: string;
  strategyId: string;
  strategyName: string;
  overallConfidencePct: number;
  evidence: string[];
  knownStrengths: string[];
  knownWeaknesses: string[];
  riskRating: "low" | "moderate" | "elevated" | "high";
  recommendedPositionSizePct: number;
  recommendedMarketConditions: string[];
  simDay: number;
  createdAt: string;
}

/** The brief's auto-generated "professional Strategy Report" — an
 * assembling read over every other real Feature 52 artifact for this
 * strategy, computed fresh on request (GET /api/sandbox/dossier), never
 * a second copy of their data. */
// Design Bible Chapter 62 — the Innovation Lab's Experiment
// Classification. Real read over the strategy's own Monte Carlo
// projections — see backend/app/strategy_lab.py's
// compute_experiment_tier() for the exact magnitude thresholds.
export type ExperimentTier = "minor" | "moderate" | "major" | "transformational";

// Quantitative Research & Intelligence System, Requirements 21/22/23/25
// (Piece 10) — the evaluation-level risk-policy simulator. Every policy
// is an explicit, disclosed HYPOTHESIS, never adopted as truth merely
// because it's compared here.
export type EvaluationRiskPolicyId = "conservative" | "moderate" | "aggressive" | "failure_boundary_relative";

/** One risk policy's real Monte Carlo evaluation-simulation results.
 * Speed (expectedTradesToPass/expectedTradingDaysToPass) is reported
 * alongside failure and drawdown risk specifically so a reader can
 * never read "fast" without also seeing "at what cost" (Requirement
 * 25 — speed is an objective to weigh, never a license to gamble). */
export interface EvaluationPolicySimulationResult {
  policyId: EvaluationRiskPolicyId;
  label: string;
  riskPerTradePct: number;
  pathsSimulated: number;
  probabilityOfPassingPct: number;
  probabilityOfFailingDrawdownPct: number;
  probabilityOfFailingTimeExpiryPct: number;
  expectedTradesToPass: number | null;
  expectedTradingDaysToPass: number | null;
  expectedCostToPass: number | null;
  medianMaxDrawdownPct: number;
  worstCaseMaxDrawdownPct: number;
  probabilityOfConsecutiveLossStreakPct: number;
  consecutiveLossStreakThreshold: number;
  riskAdjustedOutcome: number;
  probabilityOfPassingAtLowerQualityPct: number;
  probabilityOfPassingAtHigherQualityPct: number;
}

/** Requirement 21's research question, answered honestly — this report
 * never declares a winning policy (see `conclusion`). See
 * `assumptions`/`limitations` for every disclosed number and scope
 * cut this comparison makes. */
export interface EvaluationPolicyComparisonReport {
  id: string;
  strategyId: string;
  strategyName: string;
  accountId: string | null;
  sampleTradeCount: number;
  profitTargetPct: number;
  drawdownLimitPct: number;
  maxTrades: number;
  researchQuestion: string;
  policies: EvaluationPolicySimulationResult[];
  conclusion: string;
  assumptions: string[];
  limitations: string[];
  simDay: number;
  createdAt: string;
}

export interface StrategyDossier {
  strategyId: string;
  strategyName: string;
  createdBy: AgentId;
  purpose: string;
  stage: StrategyStage;
  latestReport: StrategyReport | null;
  latestReview: StrategyReview | null;
  monteCarlo: StrategyMonteCarloResult | null;
  regimeTest: StrategyRegimeTestReport | null;
  liquidityValidation: StrategyLiquidityValidation | null;
  executiveReview: StrategyExecutiveReview | null;
  founderApproval: StrategyFounderApproval | null;
  confidence: StrategyConfidenceScore | null;
  experimentTier: ExperimentTier | null;
  experimentTierRationale: string | null;
  generatedAt: string;
}

// v0.7 Feature 52 (Part 2) — "Living Strategies."
export type StrategyHealthStatus = "excellent" | "healthy" | "stable" | "needs_review" | "declining" | "critical" | "retire_candidate";
export type StrategyHealthTrend = "improving" | "stable" | "declining";

/** A real recent-vs-lifetime trend read over a strategy's own
 * SimulationResult history — deliberately NOT the brief's literal "Live
 * Performance Monitor": this codebase has no mechanism to attribute a
 * live/paper trade back to a specific Strategy object (see
 * backend/app/sandbox.py's module docstring), so this reads the real
 * Market Simulation run history a strategy actually has. */
export interface StrategyHealthAssessment {
  id: string;
  strategyId: string;
  strategyName: string;
  status: StrategyHealthStatus;
  trend: StrategyHealthTrend;
  recentWinRate: number;
  lifetimeWinRate: number;
  recentAvgReturnPct: number;
  lifetimeAvgReturnPct: number;
  recentAvgDrawdownPct: number;
  lifetimeAvgDrawdownPct: number;
  recentSampleSize: number;
  lifetimeSampleSize: number;
  reasoning: string[];
  simDay: number;
  createdAt: string;
}

/** Permanent, never evicted — only ever filed for a strategy that
 * cleared a real, strict induction bar at the moment of its own real
 * CEO-triggered retirement. */
export interface StrategyHallOfFameEntry {
  id: string;
  strategyId: string;
  strategyName: string;
  createdBy: AgentId;
  description: string;
  simDaysActive: number;
  tradesExecuted: number;
  winRate: number;
  profitFactor: number;
  maxDrawdownPct: number;
  historicalReturnPct: number;
  legacyNotes: string[];
  retiredReason: string;
  simDay: number;
  inductedAt: string;
}

/** Every retirement that doesn't clear the Hall of Fame bar — never
 * deleted, always kept as a real, citable lesson. */
export interface FailedStrategyArchiveEntry {
  id: string;
  strategyId: string;
  strategyName: string;
  createdBy: AgentId;
  failedAtStage: StrategyStage;
  whatFailed: string[];
  lessonsLearned: string[];
  retiredReason: string;
  simDay: number;
  createdAt: string;
}

/** One named slot on the Executive Dashboard — metricValue is always
 * 0.0 for "newest" (a date-based pick, not a magnitude). */
export interface StrategyExecutiveDashboardEntry {
  strategyId: string;
  strategyName: string;
  metricLabel: string;
  metricValue: number;
}

/** Computed fresh on request (GET /api/sandbox/dashboard) — every count
 * and named slot reads already-real Strategy/SimulationResult/review
 * history, never a second source of truth. */
export interface StrategyExecutiveDashboard {
  activeCount: number;
  inDevelopmentCount: number;
  inValidationCount: number;
  paperTradingCount: number;
  approvedCount: number;
  retiredCount: number;
  hallOfFameCount: number;
  failedArchiveCount: number;
  bestStrategy: StrategyExecutiveDashboardEntry | null;
  weakestStrategy: StrategyExecutiveDashboardEntry | null;
  mostImprovedStrategy: StrategyExecutiveDashboardEntry | null;
  newestStrategy: StrategyExecutiveDashboardEntry | null;
  highestConfidenceStrategy: StrategyExecutiveDashboardEntry | null;
  generatedAt: string;
}

export interface StrategyCertificationRequirement {
  id: string;
  label: string;
  met: boolean;
  detail: string;
}

/** v0.7 Feature 53 — Company Certification: a real 15-point checklist
 * combining every real Feature 52 artifact, never a new measurement.
 * `certified` is always a fresh read of the strategy's own real current
 * state, so a real Strategy Health decline automatically revokes it the
 * next time this is fetched — no separate "revoked" flag. See
 * backend/app/strategy_lab.py's compute_strategy_certification(). */
export interface StrategyCertification {
  strategyId: string;
  strategyName: string;
  certified: boolean;
  requirements: StrategyCertificationRequirement[];
  generatedAt: string;
}

export interface HallOfFameEntry {
  id: string;
  category: HallOfFameCategory;
  title: string;
  description: string;
  agentId: AgentId | null;
  value: number;
  achievedAt: string;
  // v0.7 — Museum of Discoveries fields, only populated for category="breakthrough".
  discoveryTimeline: string | null;
  supportingEvidence: string[];
  companyImpact: string | null;
}

/** One agent's row in Coach's rankings (v0.5 brief Feature 1). */
export interface AgentScore {
  agentId: AgentId;
  score: number;
  researchAccuracy: number;
  confidenceCalibration: number;
}

export interface CoachReport {
  id: string;
  period: ReportPeriod;
  companyScore: number;
  agentRankings: AgentScore[];
  researchAccuracy: number;
  winRate: number;
  lossRate: number;
  averageConfidence: number;
  riskScore: number;
  commonMistakes: string[];
  /** v0.7 Feature 18 — the positive counterpart to commonMistakes, same "real counted pattern" rule (see backend/app/coach.py's _strengths). */
  strengths: string[];
  recommendations: string[];
  createdAt: string;
}

/** The seven-metric company rating shown in the Brain Room (v0.5 brief Feature 6). */
export interface CompanyScore {
  overall: number;
  researchQuality: number;
  decisionQuality: number;
  riskManagement: number;
  paperTradingPerformance: number;
  teamCoordination: number;
  knowledgeGrowth: number;
  simulationSuccess: number;
  updatedAt: string;
}

/** sharpeRatio/sortinoRatio (Quantitative Research & Intelligence System,
 * Piece 3) are REAL statistics — mean/population-stdev and
 * mean/downside-deviation over PaperPortfolio.trade_history's own real,
 * sequential per-trade pnlPct returns (see backend/app/analytics.py's
 * compute_performance_snapshot()) — not the fabricated formula
 * SimulationResult's own same-named fields still use. Two disclosed
 * simplifications, not fabrications: risk-free rate assumed 0 (no
 * bond/cash-yield concept exists in this codebase), and these are
 * per-trade ratios, not annualized (trades close at irregular
 * sim-minute intervals, so there is no real fixed-period return series
 * to normalize against). */
export interface PerformanceSnapshot {
  period: PerformancePeriod;
  returnPct: number;
  winRate: number;
  maxDrawdownPct: number;
  sharpeRatio: number;
  sortinoRatio: number;
  avgHoldingMinutes: number;
  researchAccuracy: number;
  confidenceAccuracy: number;
  computedAt: string;
}

/** Sentinel's configurable risk boundaries (v0.6 brief, Risk Engine). */
// v0.7 Chapter 57 — the CEO's own per-tier ceiling, each a % of equity —
// real caps app/position_sizing.py's tier assignment must respect
// alongside the existing maxPositionPct/riskPerTradePct ceiling (the
// smaller of the two always wins).
export interface TierAllocationLimits {
  tier1Pct: number;
  tier2Pct: number;
  tier3Pct: number;
  tier4Pct: number;
}

export interface RiskLimits {
  maxPositionPct: number;
  maxDailyLossPct: number;
  maxDrawdownPct: number;
  maxOpenPositions: number;
  maxSectorConcentrationPct: number;
  riskPerTradePct: number;
  // v0.7 Feature 49 — Daily Trading Objectives. maxDailyLossPct above
  // already existed; these two are new.
  dailyProfitTargetPct: number;
  maxTradesPerDay: number;
  // Design Bible Chapter 67 (TTOS) Safety Settings — the same real
  // circuit breaker as maxDailyLossPct above, just scoped to the
  // current sim week/month (see backend/app/risk_engine.py's
  // weekly_realized_pnl_pct/monthly_realized_pnl_pct).
  maxWeeklyLossPct: number;
  maxMonthlyLossPct: number;
  // v0.7 Chapter 57 — Institutional Position Sizing & Capital Deployment
  // Engine (see backend/app/position_sizing.py). All six new CEO
  // controls that engine's own Design Bible chapter asks for; every
  // field above stays exactly as-is, this engine only ever narrows what
  // it's already allowed to size, never widens it.
  maxWeeklyDeploymentPct: number;
  // null = no hard cap (today's behavior — Portfolio Heat stays a pure
  // reading, never an auto-corrective action).
  portfolioHeatCapPct: number | null;
  cashReservePct: number;
  tierAllocation: TierAllocationLimits;
  scalingAggressivenessPct: number;
  emergencyReductionHeatPct: number;
  // v0.7 Chapter 58 — Institutional Trade Filter & Opportunity
  // Gatekeeper (see backend/app/opportunity_gatekeeper.py). Two real
  // CEO controls that engine reads. minTradeQualityScore's default
  // (70.0) matches war_room.py's own fixed DECISION_SCORE_THRESHOLD
  // value, but is a genuinely separate, independently-adjustable field.
  minTradeQualityScore: number;
  minExpectedValuePct: number;
  // v0.7 Chapter 59 — Capital Priority & Opportunity Cost Engine (see
  // backend/app/capital_priority.py). Both default to 0 — opt-in,
  // currently a no-op until the CEO raises them.
  minPriorityScore: number;
  capitalReservePct: number;
  // Design Bible Chapter 61 — Institutional Knowledge Graph & Company
  // Memory Engine. Pattern Detection Sensitivity (see
  // backend/app/decision_vault.py's Similarity Engine) and Knowledge
  // Retention Rules, both slices (see backend/app/decision_vault.py's
  // record_vault_entry and backend/app/memory.py's record()). All four
  // default to the exact fixed constants they replace.
  minSimilarMatches: number;
  mistakeWarningSharePct: number;
  maxDecisionVaultEntries: number;
  maxMemoryRecords: number;
  // Design Bible Chapter 62 — the Innovation Lab's Innovation Budget CEO
  // control (see backend/app/sandbox.py's begin_limited_live()).
  // Defaults to the exact fixed constant it replaces.
  maxLimitedLiveCapital: number;
  // Design Bible Chapter 63 — Company Health tier thresholds (see
  // backend/app/company_health.py's compute_company_health()). Defaults
  // to the exact fixed constants they replace (85/70/50/30). Always
  // stay strictly descending: Excellent > Good > Stable > Needs Attention.
  companyHealthExcellentThreshold: number;
  companyHealthGoodThreshold: number;
  companyHealthStableThreshold: number;
  companyHealthNeedsAttentionThreshold: number;
}

// Design Bible Chapter 67 (TTOS) Part 3 — the real Global Emergency Stop.
export interface EmergencyStopState {
  active: boolean;
  activatedAt: string | null;
}

// v0.7 Feature 49 — a real-time readout of today's real trading activity
// against the CEO's configured Daily Trading Objectives, computed fresh
// every tick (see backend/app/risk_engine.py's
// compute_daily_objective_status).
export interface DailyObjectiveStatus {
  simDay: number;
  tradesToday: number;
  realizedPnlPctToday: number;
  profitTargetReached: boolean;
  maxLossReached: boolean;
  maxTradesReached: boolean;
  tradingHalted: boolean;
  haltReason: string | null;
  updatedAt: string;
}

/** Prop-Firm Risk Intelligence Addendum, Piece 8 — "the system should
 * understand the remaining permissible loss budget" before a trade is
 * proposed, not just nominal account size. Every field is a real value
 * already computed elsewhere (lifetime drawdown reuses the same
 * portfolio.totalPnlPct evaluate_sentinel_risk already gates on; today's
 * P&L reuses dailyRealizedPnlPct) — the two "remaining" fields are the
 * one new arithmetic step (limit minus current usage, floored at 0).
 * Advisory only. */
export interface RiskBudgetStatus {
  equity: number;
  startingBalance: number;
  lifetimeDrawdownPct: number;
  maxDrawdownPct: number;
  remainingDrawdownBudgetPct: number;
  dailyLossPctToday: number;
  maxDailyLossPct: number;
  remainingDailyLossBudgetPct: number;
  dailyProfitPctToday: number;
  dailyProfitTargetPct: number;
  remainingToDailyProfitTargetPct: number;
  tradingHalted: boolean;
  haltReason: string | null;
  /** Piece 11b, Requirement 24 — distinct real sim days with at least
   * one closed trade, reusing the same day-bucketing convention
   * compute_consistency_status() already established. */
  tradingDaysCount: number;
  computedAt: string;
}

/** Prop-Firm Risk Intelligence Addendum, Piece 11 — Requirement 23: risk
 * measured against an Account's real failure boundary
 * (trailingDrawdownLimitPct), not notional account size. Any field that
 * can't be honestly computed is null, with the reason named in
 * notTrackableReasons (each prefixed "NOT_TRACKABLE_YET:"). */
export interface AccountRiskBudgetStatus {
  accountId: string;
  equity: number;
  startingBalance: number;
  effectiveFailureBoundaryPct: number | null;
  currentDistanceToFailurePct: number | null;
  remainingDrawdownBudgetPct: number | null;
  riskPerTradePctOfBoundary: number | null;
  notTrackableReasons: string[];
  computedAt: string;
}

/** Prop-Firm Risk Intelligence Addendum, Piece 11a — a real,
 * deterministic forward projection (compounding riskPerTradePct against
 * current equity), never a probability. See `assumption` for the one
 * real simplification this makes, stated explicitly. */
export interface ProjectedLossPath {
  startingEquity: number;
  equityPath: number[];
  consecutiveLosses: number;
  riskPerTradePct: number;
  projectedLossPct: number;
  assumption: string;
  computedAt: string;
}

export interface RiskWarning {
  id: string;
  symbol: string;
  severity: AlertSeverity;
  message: string;
  createdAt: string;
}

/** Pulse's output — see backend/app/scanner.py. */
export interface ScannerAlert {
  id: string;
  symbol: string;
  alertType: AlertType;
  message: string;
  detectedBy: AgentId;
  createdAt: string;
}

/** One agent's stance on a trade candidate — see backend/app/voting.py. */
export interface AgentVote {
  agentId: AgentId;
  choice: VoteChoice;
  reason: string;
}

// v0.7 Feature 15 — Decision Confidence Engine. Never predicts an
// outcome, only scores the quality of the current setup's real
// evidence — see backend/app/confidence.py for exactly which factors
// are real and which named in the v0.7 brief (support/resistance,
// multi-timeframe agreement, liquidity, historical setup matching)
// have no real data source in this codebase and are not computed.
export type ConfidenceTier = "elite" | "strong" | "good" | "moderate" | "weak" | "poor";

export interface ConfidenceFactor {
  name: string;
  score: number; // 0-100
  weight: number; // 0-1
  detail: string;
}

export interface DecisionConfidence {
  score: number; // 0-100
  tier: ConfidenceTier;
  summary: string;
  factors: ConfidenceFactor[];
}

export const CONFIDENCE_TIER_LABEL: Record<ConfidenceTier, string> = {
  elite: "Elite Setup",
  strong: "Strong Setup",
  good: "Good Setup",
  moderate: "Moderate",
  weak: "Weak",
  poor: "Poor",
};

/** The permanent, explainable-AI record of one trade candidate's outcome
 * (v0.6 brief, Decision Voting + Explainable AI; resolved by the CEO
 * since v0.6.3 — see backend/app/executive.py). */
// v0.7 Feature 50 (Part 2/3) — a real, weighted process-quality grade
// (never the trade's own P&L) on a standard 12-step academic scale. See
// backend/app/executive.py's compute_decision_grade.
export type DecisionGrade = "A+" | "A" | "A-" | "B+" | "B" | "B-" | "C+" | "C" | "C-" | "D+" | "D" | "F";

export interface TradeDecision {
  id: string;
  symbol: string;
  outcome: DecisionOutcome;
  votes: AgentVote[];
  researchSummary: string;
  technicalSummary: string;
  fundamentalSummary: string;
  riskSummary: string;
  supportingAgents: AgentId[];
  opposingAgents: AgentId[];
  confidence: number;
  finalReasoning: string;
  orderId: string | null;
  /** The real Decision Confidence Engine reading at the moment this
   * decision was made, carried over from the TradeProposal that
   * produced it — null only for decisions predating this field. */
  confidenceEngine: DecisionConfidence | null;
  /** v0.7 Feature 20 — the Trade Gatekeeper's final-approval verdict. Only
   * ever set when the CEO chose buy/sell (a WAIT never reaches the
   * gatekeeper); null for decisions predating this field. A rejected
   * verdict here is exactly what makes `orderId` null even though the
   * linked CeoDecisionRecord's `ceoDecision` was buy/sell, not wait. */
  gatekeeperVerdict: GatekeeperVerdict | null;
  /** v0.7 Feature 50 (Part 2/3) — null only for decisions predating this field. */
  decisionGrade: DecisionGrade | null;
  decisionGradeScore: number | null;
  createdAt: string;
}

// v0.6.3 Feature 12 — Executive Voting (CEO Approval). A research
// candidate crossing the trade-confidence threshold no longer executes
// automatically: it becomes a TradeProposal and waits for the CEO (the
// player) to cast the real buy/sell/wait call. See backend/app/executive.py.
export type AnalystRole = "technical" | "news" | "macro" | "risk" | "sentiment" | "execution";
export type AnalystChoice = "buy" | "sell" | "wait";

// v0.7 Feature 40.5 — the Expert Consultation System's two real CEO
// actions beyond buy/sell/wait. Both reset the same real expiry clock
// (see backend/app/executive.py's hold_proposal()); the reason is kept
// distinct only for honest logging.
export type HoldReason = "more_research" | "delay";

export const ROLE_TO_AGENT: Record<AnalystRole, AgentId> = {
  technical: "echo",
  news: "scout",
  macro: "nova",
  risk: "sentinel",
  sentiment: "pulse",
  execution: "atlas",
};

/** One analyst seat's independent vote, always backed by real evidence — see
 * backend/app/executive.py's generate_analyst_votes() for what each role reuses. */
export interface AnalystVote {
  role: AnalystRole;
  agentId: AgentId;
  choice: AnalystChoice;
  reasoning: string;
  evidence: string[];
}

/** A trade candidate awaiting the CEO's decision — not yet a trade. */
export interface TradeProposal {
  id: string;
  symbol: string;
  category: ResearchCategory;
  quantity: number;
  price: number;
  confidence: number;
  analystVotes: AnalystVote[];
  overallRecommendation: AnalystChoice;
  researchSummary: string;
  riskSummary: string;
  confidenceEngine: DecisionConfidence;
  createdAt: string;
  /** Simulated-clock minutes-since-epoch — expires after 3 in-game days unactioned. */
  createdSimMinutes: number;
  /** v0.7 Feature 40.5 — how many times the CEO has held this proposal
   * (Request More Research / Delay Decision) instead of deciding. Capped
   * at MAX_PROPOSAL_HOLDS (2) on the backend. */
  holdCount: number;
  /** v0.7 Feature 51 — a real one-line citation of the Market
   * Intelligence Department's regime/quality read at the moment this
   * proposal was generated. null only for proposals that predate this
   * feature. */
  marketIntelligenceSummary: string | null;
}

// v0.7 Feature 17 — AI Debate Room. Every turn's text is a real
// AnalystVote's own reasoning/evidence (see backend/app/debate.py);
// only the opening/challenge/support framing is generated.
export type DebateStance = "opening" | "challenge" | "support";

export interface DebateTurn {
  agentId: AgentId;
  role: AnalystRole;
  stance: DebateStance;
  respondingTo: AgentId | null;
  text: string;
}

/** One full committee review of a TradeProposal — stored permanently so a
 * past debate is always reviewable. Never itself approves/rejects a trade;
 * that's still the CEO's real buy/sell/wait call via /api/executive/decide,
 * subject to the Trade Gatekeeper's final approval (v0.7 Feature 20). */
export interface Debate {
  id: string;
  proposalId: string;
  symbol: string;
  turns: DebateTurn[];
  finalRecommendation: AnalystChoice;
  finalSummary: string;
  createdAt: string;
}

// v0.7 Feature 41 — the Intelligent Devil's Advocate System. Deliberately
// not a second copy of the AI Debate Room above (every analyst who
// disagrees already challenges there); this is a single structured
// report from one specific, rotating employee, built entirely from real
// signals already computed elsewhere — see backend/app/devils_advocate.py.
export type ChallengeSeverity = "none_found" | "minor" | "major";

export interface ChallengeReport {
  id: string;
  proposalId: string;
  symbol: string;
  assignedAgent: AgentId;
  tradeSummary: string;
  bullCase: string;
  bearCase: string;
  hiddenRisks: string[];
  weakAssumptions: string[];
  missingEvidence: string[];
  historicalComparisons: string[];
  worstCaseScenario: string;
  suggestedImprovements: string[];
  severity: ChallengeSeverity;
  finalRecommendation: string;
  // v0.7 Feature 47 — real Constitution Article ids this report's own
  // concern buckets map to (see backend/app/constitution.py's
  // articles_for_challenge()).
  citedArticleIds: string[];
  createdAt: string;
}

// v0.7 Feature 50 (Part 1) — the Executive Intelligence Network. A pure
// synthesis/presentation layer over 8 already-real departments (never a
// new computation engine of its own) — see
// backend/app/executive_intelligence.py's module docstring. Computed
// fresh on request, like WhatIfSimulation, never persisted.
// v0.7 Feature 51 adds "market_intelligence" as a real ninth department —
// see backend/app/executive_intelligence.py's module docstring for how it
// plugs into the same generic opinion/self-evaluation/meeting-log
// machinery the original eight already use.
export type ExecutiveDepartmentRole =
  | "research"
  | "quant"
  | "risk"
  | "simulation"
  | "decision_intelligence"
  | "coach"
  | "founders"
  | "devils_advocate"
  | "market_intelligence";

export type ExecutiveStance =
  | "agree"
  | "disagree"
  | "request_more_research"
  | "recommend_waiting"
  | "recommend_position_change"
  | "recommend_rejecting";

export type ExecutiveAction = "trade_normally" | "reduce_risk" | "wait" | "research_more" | "pause_trading" | "focus_on_simulation";

export interface DepartmentOpinion {
  role: ExecutiveDepartmentRole;
  departmentLabel: string;
  agentId: AgentId | null;
  stance: ExecutiveStance;
  summary: string;
  confidencePct: number;
  // Design Bible Chapter 70 Part 2 — Executive Consensus Meter.
  evidence: string[];
  concerns: string[];
  benefits: string[];
  alternative: string | null;
}

export interface ExecutiveRecommendation {
  proposalId: string;
  action: ExecutiveAction;
  confidencePct: number;
  reason: string;
  supporting: ExecutiveDepartmentRole[];
  opposing: ExecutiveDepartmentRole[];
  opinions: DepartmentOpinion[];
  generatedAt: string;
  // Design Bible Chapter 70 Part 2 — Executive Consensus Meter.
  consensusPct: number;
  disagreementSummary: string;
  probabilityOfSuccessPct: number | null;
  estimatedReturnPct: number | null;
  estimatedRiskPct: number | null;
}

// Design Bible Chapter 70 Part 2 — Executive Accuracy Score. Scored only
// over trades actually taken and since closed with a real outcome; see
// backend/app/executive_intelligence.py's compute_executive_accuracy_scores.
// CEO directive "Features 31-35," Feature 33 — Executive Accuracy
// Evidence System. `accuracyPct` is `null` (NOT_ENOUGH_EVIDENCE), never
// a fabricated 0, when `decisionsTracked` is 0 (or below the backend's
// disclosed minimum sample floor — see `evaluationState`).
export type ExecutiveEvidenceState = "pass" | "fail" | "inconclusive" | "not_enough_evidence";

export interface ExecutiveAccuracyScore {
  role: ExecutiveDepartmentRole;
  departmentLabel: string;
  decisionsTracked: number;
  correctCount: number;
  accuracyPct: number | null;
  evaluationState: ExecutiveEvidenceState;
}

export const EXECUTIVE_DEPARTMENT_LABEL: Record<ExecutiveDepartmentRole, string> = {
  research: "Research",
  quant: "Quant",
  risk: "Risk",
  simulation: "Simulation",
  decision_intelligence: "Decision Intelligence",
  coach: "Coach",
  founders: "Founders",
  devils_advocate: "Devil's Advocate",
  market_intelligence: "Market Intelligence",
};

export const EXECUTIVE_ACTION_LABEL: Record<ExecutiveAction, string> = {
  trade_normally: "Trade Normally",
  reduce_risk: "Reduce Risk",
  wait: "Wait",
  research_more: "Research More",
  pause_trading: "Pause Trading",
  focus_on_simulation: "Focus On Simulation",
};

export const EXECUTIVE_STANCE_LABEL: Record<ExecutiveStance, string> = {
  agree: "Agree",
  disagree: "Disagree",
  request_more_research: "Request More Research",
  recommend_waiting: "Recommend Waiting",
  recommend_position_change: "Recommend Position Change",
  recommend_rejecting: "Recommend Rejecting",
};

// Design Bible Chapter 70 Part 3 — Weighted Executive Decision Engine
// (WEDE). Honest scope: only two of the brief's eight named weighting
// inputs have a real, computable source (Historical Accuracy, Market
// Conditions) — see backend/app/weighted_decisions.py's module
// docstring for the full boundary.
export type WeightProfile =
  | "equal_voting"
  | "performance_weighted"
  | "risk_first"
  | "growth_first"
  | "research_first"
  | "capital_preservation"
  | "balanced_institutional"
  | "custom";

export const WEIGHT_PROFILE_LABEL: Record<WeightProfile, string> = {
  equal_voting: "Equal Voting",
  performance_weighted: "Performance Weighted",
  risk_first: "Risk First",
  growth_first: "Growth First",
  research_first: "Research First",
  capital_preservation: "Capital Preservation",
  balanced_institutional: "Balanced Institutional",
  custom: "Custom CEO Profile",
};

export interface DepartmentInfluence {
  role: ExecutiveDepartmentRole;
  departmentLabel: string;
  accuracyMultiplier: number;
  marketMultiplier: number;
  presetMultiplier: number;
  finalWeight: number;
  reasoning: string;
}

export interface WeightedExecutiveRecommendation {
  proposalId: string;
  profile: WeightProfile;
  marketRegime: MarketEnvironmentRegime;
  departmentInfluences: DepartmentInfluence[];
  rawAction: ExecutiveAction;
  weightedAction: ExecutiveAction;
  scoreByAction: Record<string, number>;
  agreesWithRaw: boolean;
}

// v0.7 Feature 50 (Part 2/3) — the Executive Meeting Log. Makes Part 1's
// ephemeral synthesis permanent: one real entry per actual
// resolve_proposal() call. See backend/app/executive_intelligence.py.
export interface ExecutiveMeetingLogEntry {
  id: string;
  proposalId: string;
  symbol: string;
  simDay: number;
  opinions: DepartmentOpinion[];
  recommendedAction: ExecutiveAction;
  recommendationReason: string;
  ceoDecision: AnalystChoice;
  networkAgreed: boolean;
  decisionGrade: DecisionGrade;
  decisionGradeScore: number;
  resolvedBy: "ceo" | "auto" | "delegated";
  createdAt: string;
}

// v0.7 Feature 50 (Part 2/3) — Weekly Self-Evaluation. One real entry
// per department per in-game week, built entirely from that
// department's own real Meeting Log opinions over the trailing week.
export interface DepartmentSelfEvaluation {
  id: string;
  role: ExecutiveDepartmentRole;
  departmentLabel: string;
  weekEndingSimDay: number;
  decisionsReviewed: number;
  score: number;
  summary: string;
  strengths: string[];
  improvementAreas: string[];
  createdAt: string;
}

// v0.7 Feature 51 — Market Intelligence Department, "the company's
// eyes." Every field traces back to real (mock) OHLCV candle data or
// real wall-clock time — see backend/app/market_intelligence.py's
// module docstring for the full honesty boundary: real technical
// analysis over real synthesized price data, named PROXIES
// (institutionalActivity, newsRisk, the accumulation/distribution
// regimes) where this codebase has no real order-flow/economic-calendar
// source, nothing fabricated. Named distinctly from the existing
// MarketRegime (per-symbol trending_up/trending_down/ranging) and
// MarketEnvironmentRegime (the simpler whole-market five-way
// classification, Feature 22) — this is a richer thirteen-way real
// classification, not a replacement for either.
export type MarketIntelligenceRegime =
  | "strong_bull_trend"
  | "strong_bear_trend"
  | "weak_uptrend"
  | "weak_downtrend"
  | "sideways_range"
  | "expansion"
  | "compression"
  | "high_volatility"
  | "low_volatility"
  | "accumulation"
  | "distribution"
  | "liquidity_hunt"
  | "transitional";

export type MarketQualityTier = "excellent" | "good" | "average" | "poor" | "avoid_trading";

// Fixed UTC windows — a documented simplification (no DST handling) —
// computed from real wall-clock time, not TradeTown's simulated clock.
export type TradingSession = "asian" | "london" | "london_ny_overlap" | "ny_lunch_hour" | "new_york" | "market_open" | "market_close" | "closed";

export type MarketDebateSpecialist = "liquidity" | "price_action" | "momentum" | "quant" | "risk";

/** One real equal-high/equal-low price cluster found in a symbol's own
 * recent candle history — a probable liquidity zone, never a claim
 * about real resting stop orders (this codebase has no order-book data). */
export interface LiquidityZone {
  kind: "equal_highs" | "equal_lows";
  price: number;
  touches: number;
}

export interface LiquidityRead {
  symbol: string;
  zones: LiquidityZone[];
  sweepDetected: boolean;
  sweepDirection: "above_highs" | "below_lows" | "none";
  liquidityScore: number;
  detail: string;
}

export interface MarketStructureRead {
  symbol: string;
  swingHighs: number[];
  swingLows: number[];
  lastBreakOfStructure: "bullish" | "bearish" | "none";
  structureState: "trend_continuation" | "trend_reversal" | "consolidation" | "expansion" | "compression";
  detail: string;
}

export interface VolatilityRead {
  currentPct: number;
  historicalAvgPct: number;
  sessionPct: number;
  percentile: number;
  expectedPct: number;
  detail: string;
}

export interface SessionRead {
  current: TradingSession;
  label: string;
  overlapsActive: string[];
  detail: string;
}

export interface MomentumRead {
  rocPct: number;
  strength: "accelerating" | "steady" | "decelerating" | "exhausted";
  detail: string;
}

/** An explicit, named PROXY — never real order-flow data. See
 * backend/app/market_intelligence.py's module docstring. */
export interface InstitutionalActivityRead {
  volumePriceDivergenceScore: number;
  absorptionDetected: boolean;
  symbolsFlagged: string[];
  detail: string;
}

/** A real, honest proxy: the count of real market-category NewsItems on
 * file, not a real economic calendar (this codebase has no per-symbol
 * news linkage or event-timing data source). */
export interface NewsRiskRead {
  activeMarketNewsCount: number;
  riskLevel: "low" | "moderate" | "elevated";
  detail: string;
}

export interface MarketQualityScore {
  tier: MarketQualityTier;
  score: number;
  confidencePct: number;
  reasoning: string;
  evidence: string[];
  historicalSimilarity: string;
}

/** The department's always-current "eyes" — recomputed fresh every
 * tick. This is what every new TradeProposal and the Trade Gatekeeper
 * actually read — never the once-daily MarketIntelligenceReport below,
 * which can be up to a day stale by the time a proposal fires. */
export interface MarketIntelligenceState {
  regime: MarketIntelligenceRegime;
  regimeLabel: string;
  regimeDetail: string;
  quality: MarketQualityScore;
  volatility: VolatilityRead;
  session: SessionRead;
  momentum: MomentumRead;
  institutionalActivity: InstitutionalActivityRead;
  newsRisk: NewsRiskRead;
  liquidity: LiquidityRead[];
  structure: MarketStructureRead[];
  updatedAt: string;
}

/** One specialist's independent real read of the current
 * MarketIntelligenceState — distinct from the proposal-scoped AiDebate
 * (Feature 17) and the Executive Intelligence Network's own portfolio-
 * level Risk department. See backend/app/market_debate.py. */
export interface MarketDebateTurn {
  specialist: MarketDebateSpecialist;
  label: string;
  observation: string;
  confidencePct: number;
  evidence: string[];
  risks: string[];
  opportunities: string[];
}

export interface MarketDebate {
  id: string;
  turns: MarketDebateTurn[];
  summary: string;
  createdAt: string;
}

/** Real, evidence-backed: only ever names a Strategy with a real
 * StrategyReport on file whose own bestMarketEnvironment is consistent
 * with today's regime. */
export interface StrategyMatch {
  recommendedStrategyIds: string[];
  avoidedStrategyIds: string[];
  recommendedRiskLevel: "minimal" | "reduced" | "normal" | "elevated";
  detail: string;
}

/** The Executive Market Brief — one real, permanent snapshot per real
 * in-game evening, embedding that day's own real MarketIntelligenceState
 * plus a fresh MarketDebate and StrategyMatch. */
export interface MarketIntelligenceReport {
  id: string;
  simDay: number;
  snapshot: MarketIntelligenceState;
  debate: MarketDebate;
  strategyMatch: StrategyMatch;
  tradeRecommendation: ExecutiveAction;
  confidencePct: number;
  evidence: string[];
  createdAt: string;
}

/** The Learning Loop — generated the day AFTER forSimDay, comparing the
 * prior day's real report against what actually happened. Either
 * comparison field is honestly null when nothing real exists yet to
 * compare against — never a fabricated accuracy percentage. */
export interface MarketIntelligenceLearningEntry {
  id: string;
  forSimDay: number;
  predictedRegime: MarketIntelligenceRegime;
  predictedQualityTier: MarketQualityTier;
  actualEnvironmentRegime: MarketEnvironmentRegime | null;
  regimeConsistent: boolean | null;
  tradesClosedThatDay: number;
  tradesWinRatePct: number | null;
  lesson: string;
  createdAt: string;
}

// v0.7 Feature 41 — Innovation Points. A second, deliberately narrow
// ladder alongside Career Level (Feature 40) — where that tracks general
// knowledge mastery, this tracks one specific real skill: an agent's own
// record as a Devil's Advocate (see backend/app/innovation.py).
export type InnovationTierName = "research_contributor" | "research_specialist" | "innovation_leader" | "chief_innovator" | "legendary_innovator";

export interface InnovationState {
  agentId: AgentId;
  points: number;
  tier: number;
  tierName: InnovationTierName;
}

// v0.7 — the Advanced Quantitative Research Division (see
// backend/app/black_box.py's module docstring for what this extends vs.
// builds new: the Devil's Advocate/Innovation Points/backtesting engine/
// Founder Council/Museum of Discoveries pieces all reuse existing systems
// above rather than duplicating them).
export type BlackBoxCategory =
  | "new_trading_framework"
  | "portfolio_allocation"
  | "statistical_edge"
  | "ai_communication"
  | "risk_model"
  | "decision_framework"
  | "journaling_improvement"
  | "automation_improvement"
  | "market_regime_detection"
  | "portfolio_optimization"
  | "academy_improvement";
export type BlackBoxProjectStatus = "active" | "paused" | "under_review" | "completed" | "failed";
export type BlackBoxPriority = "low" | "normal" | "high";

export interface BlackBoxTeamMember {
  agentId: AgentId;
  role: string;
}

export interface BlackBoxProject {
  id: string;
  category: BlackBoxCategory;
  title: string;
  objective: string;
  status: BlackBoxProjectStatus;
  priority: BlackBoxPriority;
  team: BlackBoxTeamMember[];
  devilsAdvocate: AgentId;
  progress: number;
  confidenceLevel: number;
  budget: number;
  obstacles: string[];
  researchNotes: string[];
  quantJournal: string[];
  startedSimDay: number;
  estimatedCompletionSimDay: number;
  completedAt: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface BreakthroughReview {
  id: string;
  projectId: string;
  projectTitle: string;
  simDay: number;
  hypothesis: string;
  evidence: string[];
  statisticalResults: string;
  risks: string[];
  limitations: string;
  devilsAdvocateCase: string;
  recommendation: string;
  verdict: "approved" | "rejected";
  verdictReason: string;
  createdAt: string;
}

export interface BlackBoxState {
  active: BlackBoxProject | null;
  archive: BlackBoxProject[];
  reviews: BreakthroughReview[];
  viewedBreakthroughIds: string[];
  updatedAt: string;
}

// v0.7 Feature 20 — Trade Gatekeeper. Every check is real (see
// backend/app/gatekeeper.py for exactly what each one reads); never a
// fabricated pass/fail. GatekeeperRejection tracks a *hypothetical*
// outcome for a trade that never actually executed — graded later
// against the symbol's own real subsequent watchlist price movement.
export interface GatekeeperCheck {
  id: string;
  label: string;
  passed: boolean;
  detail: string;
}

export interface GatekeeperVerdict {
  approved: boolean;
  checks: GatekeeperCheck[];
  summary: string;
  createdAt: string;
}

export type GatekeeperOutcome = "pending" | "would_have_won" | "would_have_lost";

/** One trade the Gatekeeper blocked. No order was ever placed — `outcome`
 * resolves once the real evaluation window has passed, purely from the
 * real difference between the symbol's watchlist price then and now,
 * never a fabricated P&L. */
export interface GatekeeperRejection {
  id: string;
  proposalId: string;
  symbol: string;
  ceoChoice: AnalystChoice;
  reasons: string[];
  priceAtRejection: number;
  rejectedSimMinutes: number;
  outcome: GatekeeperOutcome;
  resolvedPriceChangePct: number | null;
  createdAt: string;
  resolvedAt: string | null;
}

/** v0.7 Chapter 58 — Institutional Trade Filter & Opportunity
 * Gatekeeper. A distinct, EARLIER-stage sibling to GatekeeperRejection
 * above: this candidate never became a real TradeProposal the CEO could
 * see, so there is no ceoChoice to record — wouldHaveRecommended is the
 * six-agent desk's own overallRecommendation instead. Graded the same
 * honest way, except a "wait" recommendation has no real direction to
 * grade against and stays "pending" forever. */
export interface OpportunityRejection {
  id: string;
  symbol: string;
  wouldHaveRecommended: AnalystChoice;
  reasons: string[];
  decisionScoreAtRejection: number;
  expectedValueAtRejectionPct: number;
  priceAtRejection: number;
  rejectedSimMinutes: number;
  outcome: GatekeeperOutcome;
  resolvedPriceChangePct: number | null;
  createdAt: string;
  resolvedAt: string | null;
}

// v0.7 Feature 16 — What-If Simulation Lab. Fetched on demand from
// GET /api/executive/whatif (never persisted/broadcast — see
// backend/app/whatif.py's module docstring for why).
export type ScenarioType =
  | "bullish_continuation"
  | "bearish_reversal"
  | "sideways_consolidation"
  | "high_volatility"
  | "low_volatility"
  | "news_shock"
  | "gap_up"
  | "gap_down"
  | "trend_failure"
  | "breakout_confirmation"
  | "liquidity_sweep"
  | "flash_crash";

/** One scenario's simulated outcome distribution — a bootstrap resample of
 * the symbol's own real recent bar-to-bar returns, biased/scaled per
 * scenario. Never a prediction of what will happen, only a resilience
 * stress-test of "if this condition occurred." */
export interface ScenarioResult {
  scenarioType: ScenarioType;
  label: string;
  rewardRangeLowPct: number;
  rewardRangeHighPct: number;
  mostLikelyPct: number;
  typicalDrawdownPct: number;
  maxRiskPct: number;
  probabilityOfProfitPct: number;
  invalidation: string;
}

export interface WhatIfSimulation {
  symbol: string;
  holdBars: number;
  scenarios: ScenarioResult[];
  /** The organic, unbiased resample of the symbol's own real recent returns — no scenario bias applied. */
  baseline: ScenarioResult;
  bestCaseScenario: ScenarioType;
  worstCaseScenario: ScenarioType;
}

/** The permanent record of one CEO decision, graded once (and only once) a
 * real trade it caused actually closes — an override's "AI accuracy" is
 * left "undecidable" rather than guessed, since no counterfactual trade
 * was ever placed to test it. */
export interface CeoDecisionRecord {
  id: string;
  proposalId: string;
  symbol: string;
  category: ResearchCategory;
  aiRecommendation: AnalystChoice;
  ceoDecision: AnalystChoice;
  agreedWithAi: boolean;
  decisionId: string | null;
  outcome: "pending" | "correct" | "incorrect" | "undecidable";
  /** v0.7 Feature 21 — "ceo" is a real player click via
   * /api/executive/decide; "auto" is a Company Operating Mode
   * auto-resolution or a stale-proposal expiry (see backend/app/nexus.py)
   * — neither was ever a real CEO decision. "delegated" (Design Bible
   * Chapter 70 Part 2) is a real player click that explicitly asked the
   * Executive Intelligence Network's own recommendation to decide.
   * Defaults to "ceo" on records predating this field, which were all
   * real clicks. */
  resolvedBy: "ceo" | "auto" | "delegated";
  createdAt: string;
  resolvedAt: string | null;
}

// CEO directive "Features 26-30," Feature 29 — Prediction -> Outcome
// Tracking (backend/app/prediction_tracking.py). Not the same "Feature
// 29" as the older v0.7-numbering-scheme Reasoning Lab (an unrelated,
// disclosed naming collision — see that module's own docstring). One
// real, individually-addressable prediction per real trade-causing
// decision, staked before its outcome was known and resolved later
// purely from real, independent trade data.
export type PredictionClaimType = "trade_direction";

// CEO directive "Features 26-30," Feature 30 — the Failure Review
// Board (backend/app/failure_review.py). The real, post-hoc
// THESIS-FAILURE taxonomy, distinct from CaseStudyCategory's
// behavioral/process taxonomy: a trade can be process-perfect and
// still have a wrong thesis, or vice versa. "external_shock" was
// researched and explicitly cut (no per-trade-linkable Black Swan
// event record exists) rather than shipped as a permanently-dead
// value.
export type FailureReason =
  | "bad_thesis"
  | "poor_execution"
  | "risk_management_failure"
  | "market_regime_misread"
  | "information_gap"
  | "process_violation"
  | "unknown";

export interface PredictionRecord {
  id: string;
  decisionId: string;
  symbol: string;
  claimType: PredictionClaimType;
  predictedDirection: "buy" | "sell";
  confidencePct: number;
  attributedAgents: AgentId[];
  outcome: "pending" | "correct" | "incorrect";
  resolvedTradeId: string | null;
  resolvedPnlPct: number | null;
  /** CEO directive Feature 30 feed-back — filled only when `outcome`
   * resolves "incorrect", from the real FailureClassification filed
   * for the same trade. Null for pending/correct predictions. */
  failureReason: FailureReason | null;
  simDay: number;
  createdAt: string;
  resolvedAt: string | null;
}

// CEO directive "Features 26-30," Feature 30 — one real
// FailureClassification per closed, losing trade (backend/app/
// failure_review.py's classify_failure()).
export interface FailureClassification {
  id: string;
  tradeId: string;
  decisionId: string;
  symbol: string;
  reason: FailureReason;
  evidence: string;
  attributedAgents: AgentId[];
  tradePnlPct: number;
  simDay: number;
  createdAt: string;
}

export interface TimeState {
  day: number;
  hour: number; // 0-23
  minute: number; // 0-59
}

// v0.7 Feature 21 — Company Operating Modes.
//   learning  — every proposal waits for the CEO (unchanged default).
//   assisted  — routine proposals auto-resolve; only a "significant" one
//               (see backend/app/executive.py's is_significant_proposal)
//               still surfaces to the player.
//   executive — every proposal auto-resolves; the player reviews reports
//               (Decisions / Company Health) instead of individual trades.
export type OperatingMode = "learning" | "assisted" | "executive";

// v0.7 Feature 34 — Company Priorities. "balanced" is the neutral
// default; the other three each bias exactly one real, already-existing
// lever (see backend/app/nexus.py's tick() for where each is applied).
export type CompanyPriority = "balanced" | "learning" | "research" | "risk_reduction";

// v0.7 Feature 37 — the Work Mode System. "work" (the default —
// unchanged behavior from every prior version) is indefinite, continuous
// operation; "rest" is the CEO-triggered wind-down. Persistent until the
// CEO changes it, never an automatic timer.
export type WorkMode = "work" | "rest";

export interface SettingsState {
  musicVolume: number; // 0-1
  sfxVolume: number; // 0-1
  autosaveIntervalSec: number;
  showFps: boolean;
  operatingMode: OperatingMode;
  companyPriority: CompanyPriority;
  workMode: WorkMode;
  // v0.7 Feature 49 (Phase 3 revision) — off by default. Employees
  // always auto-progress through the Academy regardless; this only
  // gates whether the CEO may ALSO voluntarily take the same lessons
  // personally. See FoundationalMentorState's own doc comment above.
  ceoAcademyLearningMode: boolean;
  // Design Bible Chapter 70 Part 3 — Weighted Executive Decision Engine.
  // Same client-authoritative mechanism as operatingMode/companyPriority
  // above — changed locally, persisted on the next save.
  activeWeightProfile: WeightProfile;
  // Only read when activeWeightProfile === "custom".
  customDepartmentWeights: Partial<Record<ExecutiveDepartmentRole, number>>;
}

// v0.7 Feature 34 — CEO time controls (POST /api/time/advance).
export type TimeAdvanceTarget = "workday_end" | "week_end" | "month_end" | "hours";

// v0.7 Feature 22 — Market Environment Simulation. Every regime is
// computed server-side from real WatchlistEntry.dailyChangePct values
// (see backend/app/market_environment.py) — never a client-side guess.
export type MarketEnvironmentRegime = "bull" | "bear" | "sideways" | "high_volatility" | "low_volatility";

/** One real regime *change* — the timeline only grows when the computed
 * regime actually differs from the previous tick's, not once per tick. */
export interface MarketEnvironmentEntry {
  id: string;
  regime: MarketEnvironmentRegime;
  label: string;
  detail: string;
  simMinutes: number;
  createdAt: string;
}

export interface MarketEnvironmentState {
  current: MarketEnvironmentRegime;
  label: string;
  detail: string;
  changedSimMinutes: number;
  updatedAt: string;
  timeline: MarketEnvironmentEntry[];
}

// Design Bible Chapter 65 — Market Regime Detection & Adaptive Strategy
// Engine. Reconciles the two real regime engines above/below
// (MarketEnvironmentState's 5-way, MarketIntelligenceState's 13-way)
// into one CEO-facing read, plus a read-only posture recommendation —
// never an automatic change to any real risk limit (see
// backend/app/regime_reconciliation.py). Computed fresh per request,
// never persisted.
export type RegimeAgreement = "aligned" | "diverging";
export type RegimePosture = "cautious" | "normal" | "opportunistic";

export interface RegimeReconciliation {
  environmentRegime: MarketEnvironmentRegime;
  environmentLabel: string;
  intelligenceRegime: MarketIntelligenceRegime;
  intelligenceLabel: string;
  qualityTier: MarketQualityTier;
  confidencePct: number;
  agreement: RegimeAgreement;
  posture: RegimePosture;
  rationale: string;
}

// CEO directive "Session Trading Education & Agent Training" — real
// SESSION x REGIME evidence over this company's own closed trades (see
// backend/app/session_evidence.py). Computed fresh per request from the
// already-real Decision Vault — never a second persisted copy.
// Deliberately a two-axis read (session x regime -> outcome), not a
// five-axis session x regime x strategy x setup x outcome read — no
// "setup" taxonomy and no real strategy attribution exists on live
// decisions yet (DecisionVaultEntry.strategyId is always null today).
export type SessionRegimeEvidenceState = "favorable" | "unfavorable" | "mixed" | "not_enough_evidence";

export interface SessionRegimeEvidence {
  session: TradingSession;
  regime: MarketIntelligenceRegime;
  sampleSize: number;
  winCount: number;
  lossCount: number;
  winRatePct: number | null;
  avgPnlPct: number | null;
  evidenceState: SessionRegimeEvidenceState;
}

export interface SessionRegimeEvidenceSummary {
  buckets: SessionRegimeEvidence[];
  minSampleSize: number;
  updatedAt: string;
}

// v0.7 Feature 23 — Company Health & Stability System. Ten real,
// documented sub-scores (see backend/app/company_health.py) — a
// different question from v0.5's CompanyScore ("is the company healthy
// to keep operating" vs. "is it performing well"); several factors
// deliberately reuse the same underlying real signal an existing
// CompanyScore metric already reads.
export type CompanyHealthTier = "excellent" | "good" | "stable" | "needs_attention" | "critical";

export interface CompanyHealth {
  overall: number;
  tier: CompanyHealthTier;
  operationalStability: number;
  departmentEfficiency: number;
  employeeMorale: number;
  researchProgress: number;
  capitalHealth: number;
  resourceUsage: number;
  reputation: number;
  technologyLevel: number;
  /** CEO Company/Executive Health directive: renamed from
   * "officeExpansion" — real watchlist growth beyond the seed symbols,
   * never a facility/office-capability mechanic. Same real formula. */
  marketCoverage: number;
  educationProgress: number;
  /** v0.7 Feature 43 — real support-vs-challenge ratio across recent AI
   * Debates (see backend/app/company_health.py's _team_chemistry). */
  teamChemistry: number;
  recommendations: string[];
  updatedAt: string;

  // v0.7 Feature 50 (Part 2/3) — the Company Health redesign. Ten more
  // real Executive-tier dimensions, additive alongside the eleven
  // Operational ones above (overall/tier are unchanged) — see
  // backend/app/company_health.py's module docstring.
  decisionQuality: number;
  executiveAlignment: number;
  riskGovernance: number;
  simulationCoverage: number;
  departmentConsensus: number;
  selfEvaluationHealth: number;
  institutionalMemory: number;
  innovationVelocity: number;
  talentDevelopment: number;
  founderOversight: number;
  /** CEO directive "Features 31-35," Feature 35 — a real blend of
   * incident resolution, remediation effectiveness (Feature 35), and
   * control effectiveness (Feature 34). Never a rewrite of the separate
   * Compliance Score formula (backend/app/audit_log.py), which stays
   * untouched. */
  complianceHealth: number;
  executiveOverall: number;
  executiveTier: CompanyHealthTier;
  /** An equal blend of `overall` and `executiveOverall` — the true
   * redesigned headline number. */
  combinedOverall: number;
  combinedTier: CompanyHealthTier;
}

// CEO Company Health + Live Market Realism directive, Section 6 — the
// explicit before/after delta breakdown (see
// backend/app/company_health.py's diff_company_health()). `group`
// distinguishes CompanyHealth's two already-real, already-equal-weighted
// tiers; never a new weighting scheme, just a label on the existing one.
export type CompanyHealthDeltaGroup = "operational" | "executive";

export interface CompanyHealthComponentDelta {
  key: string;
  label: string;
  group: CompanyHealthDeltaGroup;
  previous: number;
  current: number;
  delta: number;
}

/** One real diff between two already-computed CompanyHealth readings —
 * never a fabricated "reason"/"evidence" string. `components` holds only
 * entries that actually moved, sorted by magnitude. */
export interface CompanyHealthDelta {
  previousUpdatedAt: string;
  currentUpdatedAt: string;
  overallDelta: number;
  executiveOverallDelta: number;
  combinedOverallDelta: number;
  tierChanged: boolean;
  executiveTierChanged: boolean;
  combinedTierChanged: boolean;
  components: CompanyHealthComponentDelta[];
}

// v0.7 Feature 43 — Company DNA (see backend/app/company_dna.py). The one
// genuinely net-new concept the Executive Intelligence Dashboard brief
// asked for; five real, descriptive behavioral traits read off the
// company's own historical decision/trade record.
export interface CompanyDnaTrait {
  id: string;
  name: string;
  score: number;
  detail: string;
}

export interface CompanyDNA {
  traits: CompanyDnaTrait[];
  summary: string;
  // v0.7 Feature 48 — a pure, deterministic label read off the five
  // traits above (see backend/app/company_dna.py's classify_identity()).
  identity: string;
  sampleSize: number;
  updatedAt: string;
}

// v0.7 Feature 24 — the CIO's Monthly Executive Review (see
// backend/app/executive_review.py). A fresh cumulative snapshot over
// each already-capped recent-history list, same convention CoachReport
// already uses — companyScoreChange is the one true period-over-period
// figure, a real delta against the previous review's own stored score.
export interface DepartmentActivity {
  agentId: AgentId;
  researchCompleted: number;
  decisionsInvolved: number;
}

export interface ExecutiveReview {
  id: string;
  companyScore: number;
  companyScoreChange: number;
  companyHealthTier: CompanyHealthTier;
  departmentActivity: DepartmentActivity[];
  researchCompleted: number;
  knowledgeGained: number;
  lessonsCompleted: number;
  majorEvents: string[];
  conflictsDetected: number;
  flags: string[];
  recommendations: string[];
  longTermGoals: string[];
  /** v0.7 Feature 25.5 — real "this builds on that" callbacks, one per
   * research category / Academy topic with 2+ completed items, naming the
   * two real titles involved. Empty when nothing yet has a real
   * predecessor to reference. */
  knowledgeConnections: string[];
  summary: string;
  createdAt: string;
}

// Design Bible Chapter 70 Part 1 — Executive Board & CEO Intelligence
// System (see backend/app/board.py). BoardSeat/BoardRoster have no
// WS-broadcast field (computed fresh per request, the same on-demand
// pattern Chapter 73's CompliancePanel already established) — fetched
// via net/api.ts instead. boardReports IS a real, live WS-broadcast
// field (gameStore), the same convention executiveReviews above uses.
export interface BoardSeat {
  title: string;
  agentId: AgentId | null;
  agentName: string | null;
}

export interface BoardRoster {
  seats: BoardSeat[];
  generatedAt: string;
}

export type BoardReportCadence = "daily" | "quarterly" | "emergency";
export type BoardReportTrigger = "emergency_stop" | "black_swan_tier";

export interface BoardReport {
  id: string;
  cadence: BoardReportCadence;
  trigger: BoardReportTrigger | null;
  departmentActivity: DepartmentActivity[];
  problems: string[];
  recommendations: string[];
  riskAssessment: string;
  confidenceLevel: number;
  requiredCeoDecisions: number;
  summary: string;
  simDay: number;
  createdAt: string;
}

// Design Bible Chapter 64 — Executive Strategic Planning & Goal
// Management Engine (see backend/app/goals.py). Deliberately the
// smallest real slice: a CEO-authored goal against one real,
// already-computed metric. No Executive Priority Engine, Resource
// Allocation, or Milestone Tracking yet — see that chapter's own
// Implementation Notes for the honest scope cut.
export type GoalCategory = "growth" | "risk" | "research" | "trading" | "operations";
export type GoalMetric = "company_health_combined" | "company_score_overall" | "portfolio_return_pct" | "academy_level";
export type GoalStatus = "active" | "completed" | "cancelled" | "expired";

export const GOAL_METRIC_LABEL: Record<GoalMetric, string> = {
  company_health_combined: "Company Health (Combined)",
  company_score_overall: "Company Score",
  portfolio_return_pct: "Portfolio Return %",
  academy_level: "Academy Level",
};

export const GOAL_CATEGORY_LABEL: Record<GoalCategory, string> = {
  growth: "Growth",
  risk: "Risk",
  research: "Research",
  trading: "Trading",
  operations: "Operations",
};

// Design Bible Chapter 64 (second pass) — Milestone Tracking. Real,
// fixed checkpoints (25/50/75%) on a Goal's own real progress — see
// backend/app/goals.py's MILESTONE_THRESHOLDS. reached/reachedAt only
// ever go from unreached to reached (a crossed milestone stays crossed).
export interface Milestone {
  id: string;
  thresholdPct: number;
  reached: boolean;
  reachedAt: string | null;
}

export interface Goal {
  id: string;
  title: string;
  category: GoalCategory;
  targetMetric: GoalMetric;
  targetValue: number;
  currentValue: number;
  progressPct: number;
  createdSimDay: number;
  deadlineSimDay: number | null;
  status: GoalStatus;
  createdAt: string;
  updatedAt: string;
  completedAt: string | null;
  milestones: Milestone[];
  /** CEO Company Health + Live Market Realism directive, Section 13 —
   * real consecutive-tick stall count; isBlocked flips true once it
   * crosses the real threshold (see backend/app/goals.py's
   * GOAL_STALLED_THRESHOLD_TICKS). Never a fabricated reason string. */
  stalledTicks: number;
  isBlocked: boolean;
}

// Design Bible Chapter 64 (third pass) — the Executive Priority Engine.
// A real, named formula over two real signals every Goal already
// carries (see backend/app/goals.py's compute_goal_priority()) —
// structurally distinct from Chapter 59's trade-proposal Priority
// Score, never a reuse of it. Computed fresh per request, never
// persisted.
export interface GoalPriority {
  goalId: string;
  score: number;
  remainingPct: number;
  daysRemaining: number | null;
}

// Design Bible Chapter 64 (fourth pass) — Resource Allocation. A
// recommend-only share of executive ATTENTION across active goals,
// normalized from the same real GoalPriority scores above so it sums
// to ~100% — never a claim about real capital movement (see
// backend/app/goals.py's compute_resource_allocation()). Computed
// fresh per request, never persisted.
export interface GoalAllocation {
  goalId: string;
  score: number;
  allocationPct: number;
}

// Design Bible Chapter 64 (fifth pass) — the Strategic Review Cycle.
// Mirrors ExecutiveReview's own monthly structure but over CEO-authored
// goals (see backend/app/goals.py's generate_strategic_review()). Every
// field is a real derivation from Goal/Milestone/GoalPriority state.
export interface StrategicReview {
  id: string;
  createdAt: string;
  activeGoalCount: number;
  completedSinceLastReview: string[];
  expiredSinceLastReview: string[];
  milestonesReachedSinceLastReview: number;
  topPriorityGoalId: string | null;
  topPriorityScore: number | null;
  summary: string;
}

// v0.7 Feature 25 — AI Academy & Knowledge Network (see
// backend/app/academy.py, backend/app/academy_research.py).
export type AcademyTopic = "market_history" | "trading_psychology" | "economic_concepts" | "visualization_tools" | "decision_biases" | "trading_philosophies";
export type AcademyProjectStatus = "in_progress" | "completed";

export interface AcademyProject {
  id: string;
  topic: AcademyTopic;
  title: string;
  assignedAgent: AgentId;
  status: AcademyProjectStatus;
  progress: number;
  summary: string;
  createdAt: string;
  updatedAt: string;
}

// v0.7 Feature 31 — the same real points, a real seven-level name.
export type KnowledgeLevel = "novice" | "beginner" | "intermediate" | "advanced" | "expert" | "master" | "mentor";

export interface AgentKnowledgeState {
  agentId: AgentId;
  branch: string;
  points: number;
  tier: number;
  level: KnowledgeLevel;
}

export interface AcademyState {
  level: number;
  levelLabel: string;
  totalPoints: number;
  completedProjectCount: number;
  updatedAt: string;
}

// CEO Company Health + Live Market Realism directive, Section 3 — the
// five real, already-existing places backend/app/academy.py's
// award_points() is called from.
export type LearningEventSource = "research_completion" | "academy_project" | "meeting_attendance" | "mentorship" | "case_study_reflection";

// A formal, structured record of one real Knowledge-tier crossing,
// mirroring backend/app/schemas.py's LearningEvent. Every field is real,
// read directly off the AgentKnowledgeState transition award_points()
// computed — never a fabricated "why" narrative.
export interface LearningEvent {
  id: string;
  agentId: AgentId;
  skillDomain: string;
  previousCompetency: number;
  previousLevel: KnowledgeLevel;
  newCompetency: number;
  newLevel: KnowledgeLevel;
  source: LearningEventSource;
  pointsAwarded: number;
  totalPoints: number;
  createdAt: string;
}

// v0.7 Feature 25.5 — Company Knowledge Graph (see
// backend/app/knowledge_graph.py). Computed fresh on every
// GET /api/knowledge-graph call, the same "expensive-ish to compute,
// cheap to re-derive, never persisted" convention WhatIfSimulation
// already uses — not part of GameSaveState.
// v0.7 Design Bible Chapter 61 — three new node types (trade, case_study,
// strategy) and four new edge relations, each backed by an already-real
// object (DecisionVaultEntry, CaseStudy, Strategy) — see
// backend/app/knowledge_graph.py's module docstring.
export type KnowledgeNodeType =
  | "agent"
  | "branch"
  | "research"
  | "academy_project"
  | "executive_review"
  | "coach_report"
  | "hall_of_fame"
  | "trade"
  | "case_study"
  | "strategy";
export type KnowledgeEdgeRelation =
  | "researched"
  | "completed"
  | "has_branch"
  | "builds_on"
  | "featured_in"
  | "ranked_top_agent"
  | "achieved"
  | "documented_by"
  | "same_symbol"
  | "same_category"
  | "created";

export interface KnowledgeNode {
  id: string;
  type: KnowledgeNodeType;
  label: string;
  subtitle: string;
  /** ISO timestamp for timeline ordering; null for evergreen nodes
   * (agent, branch) that were never "completed" at a point in time. */
  timestamp: string | null;
}

export interface KnowledgeEdge {
  source: string;
  target: string;
  relation: KnowledgeEdgeRelation;
  label: string;
}

export interface KnowledgeGraph {
  nodes: KnowledgeNode[];
  edges: KnowledgeEdge[];
  generatedAt: string;
}

// v0.7 Feature 26 — the Discipline Chamber (see backend/app/discipline.py).
// One real DisciplineReview per closed paper trade, scoring the decision
// PROCESS — never the outcome. `score`/`factors` never depend on
// `outcome`/`tradePnlPct`, which are attached afterward purely so the
// player can see whether a good process and a good outcome lined up.
export type DisciplineFactorId = "research_depth" | "viewpoint_diversity" | "uncertainty_acknowledged" | "cross_examination" | "assumptions_challenged" | "position_sizing_discipline" | "patience";
export type DisciplineTier = "exemplary" | "sound" | "adequate" | "weak" | "reckless";

export interface DisciplineFactor {
  id: DisciplineFactorId;
  name: string;
  score: number;
  weight: number;
  detail: string;
}

export interface PostDecisionReview {
  whatWeDidWell: string[];
  mistakesMade: string[];
  informationOverlooked: string[];
  assumptionsIncorrect: string[];
  whatToRepeat: string[];
  whatToNeverRepeat: string[];
  howToImprove: string[];
}

export interface DisciplineReview {
  id: string;
  decisionId: string;
  symbol: string;
  score: number;
  tier: DisciplineTier;
  factors: DisciplineFactor[];
  attendees: AgentId[];
  summary: string;
  postDecisionReview: PostDecisionReview;
  outcome: "win" | "loss";
  tradePnlPct: number;
  holdDurationMinutes: number;
  /** The real in-game day this review was filed (TimeState.day) — not a
   * real wall-clock date — so NPCs can honestly reference "Day X." */
  simDay: number;
  createdAt: string;
}

// Trading Psychology & Discipline, Piece C — the Process Adherence
// Score (see backend/app/process_adherence.py). Explicitly NOT a Plan
// Adherence Engine: stop-loss/take-profit/entry-condition/exit-
// condition/confluence checks always report "not_trackable_yet" —
// never "passed", never "failed", never omitted. `scorePct` is null
// whenever `verifiedCount` is 0 — never render that as 0%.
export type ProcessAdherenceCheckStatus = "passed" | "failed" | "not_trackable_yet";

export interface ProcessAdherenceCheck {
  id: string;
  label: string;
  status: ProcessAdherenceCheckStatus;
  detail: string;
}

export interface ProcessAdherenceRead {
  decisionId: string;
  symbol: string;
  scorePct: number | null;
  verifiedCount: number;
  passedCount: number;
  failedCount: number;
  notTrackableCount: number;
  checks: ProcessAdherenceCheck[];
  computedAt: string;
}

// Trading Psychology & Discipline, Piece G — the one company-wide
// aggregate over ProcessAdherenceRead (every other consumer reads a
// single decision's own score by id — see DecisionDetail.tsx).
export interface ProcessAdherenceSummaryRead {
  decisionsReviewed: number;
  decisionsWithVerifiedChecks: number;
  averageScorePct: number | null;
  computedAt: string;
}

// v0.7 Feature 27 — the Library of Mistakes (see backend/app/mistakes.py).
// A permanent CaseStudy is filed whenever a closed, losing trade's own
// DisciplineReview shows a specific real process gap — never merely
// "the trade lost" on its own.
// v0.7 Feature 42 — the last three are the Decision Replay Center's
// "Successes" half (see backend/app/successes.py), each the crisp
// inversion of one of the first six's real trigger signal. See
// SUCCESS_CASE_STUDY_CATEGORIES below for the exact partition.
export type CaseStudyCategory =
  | "overconfidence"
  | "incomplete_research"
  | "unchallenged_assumptions"
  | "acted_too_quickly"
  | "ignored_dissent"
  | "confirmation_bias"
  | "disciplined_process"
  | "rigorous_cross_examination"
  | "patient_execution";

export const SUCCESS_CASE_STUDY_CATEGORIES: ReadonlySet<CaseStudyCategory> = new Set([
  "disciplined_process",
  "rigorous_cross_examination",
  "patient_execution",
]);

export interface CaseStudyTimelineEntry {
  label: string;
  timestamp: string;
}

export interface CaseStudy {
  id: string;
  category: CaseStudyCategory;
  title: string;
  symbol: string;
  decisionId: string;
  timeline: CaseStudyTimelineEntry[];
  background: string;
  decisionProcess: string;
  departmentOpinions: string[];
  missedInformation: string;
  lessonsLearned: string;
  recommendedImprovements: string;
  relatedPrinciples: string[];
  tradePnlPct: number;
  /** The real in-game day this case study was filed — see
   * DisciplineReview.simDay above for why. */
  simDay: number;
  createdAt: string;
}

export type InstitutionalMemorySource =
  | "behavioral_mistake"
  | "behavioral_success"
  | "strategy_failure"
  | "strategy_success"
  | "model_validation"
  | "risk_event"
  | "market_regime_shift";

export type InstitutionalMemoryStatus = "active" | "superseded" | "contradicted" | "stale";

/** CEO directive "Features 26-30," Feature 26 — Institutional Memory
 * 2.0 (backend/app/institutional_memory.py). A promoted, reusable
 * lesson — never a raw copy of the event log — separating observation
 * (real fact) from interpretation (hedged) from lesson (actionable);
 * either of the latter two may be null when the source has nothing
 * honest to offer. A superseded/contradicted entry is never deleted —
 * see supersededById/supersedesId. */
export interface InstitutionalMemoryEntry {
  id: string;
  source: InstitutionalMemorySource;
  createdAt: string;
  simDay: number;
  originatingAgent: AgentId | null;
  eventRef: string;
  marketRegime: MarketEnvironmentRegime | null;
  observation: string;
  interpretation: string | null;
  lesson: string | null;
  confidence: number;
  provenance: string;
  relevancePct: number;
  status: InstitutionalMemoryStatus;
  supersedesId: string | null;
  supersededById: string | null;
  supportingEvidence: string[];
}

/** v0.7 Feature 54 (the brief self-numbered it "Feature 53," already used
 * in this codebase's history for Company Certification) — the Decision
 * Memory System's Decision Vault. One permanent record per closed trade,
 * joining every real artifact already generated for it — see
 * backend/app/decision_vault.py's module docstring for the full honesty
 * boundary, including which brief-requested fields are deliberately not
 * here (rMultiple, strategyId on ordinary trades). marketRegime/
 * liquidityContext are "as of trade close," not "as of the original
 * decision" — nothing in this codebase stamps either onto a proposal at
 * decision time. */
export interface DecisionVaultEntry {
  id: string;
  tradeId: string;
  decisionId: string;
  symbol: string;
  simDay: number;
  session: TradingSession;
  strategyId: string | null;
  marketRegime: MarketIntelligenceRegime;
  marketRegimeLabel: string;
  liquidityContext: LiquidityRead;
  evidenceScore: number;
  confidenceScore: number;
  confidenceTier: ConfidenceTier;
  capitalAllocationGrade: DecisionGrade;
  decisionGrade: DecisionGrade;
  decisionGradeScore: number;
  disciplineTier: DisciplineTier;
  disciplineScore: number;
  patienceGrade: DecisionGrade;
  positionSize: number;
  entryPrice: number;
  exitPrice: number;
  pnl: number;
  pnlPct: number;
  holdDurationMinutes: number;
  /** Always null — no stop-loss/initial-risk concept exists anywhere in
   * this codebase's real risk engine (see backend/app/risk_engine.py's
   * recommended_quantity()), so R-Multiple can't be honestly computed. */
  rMultiple: number | null;
  caseStudyId: string | null;
  caseStudyCategory: CaseStudyCategory | null;
  executiveNotes: string | null;
  lessonsLearned: string;
  companyDnaChange: string | null;
  ceoOverride: boolean;
  createdAt: string;
}

/** A pure relabeling of one DecisionVaultEntry's own real fields — see
 * backend/app/decision_vault.py's compute_trade_report_card() for why
 * Execution Grade/Psychology Grade aren't here (no real signal anywhere
 * measures either), and why overallTradeQuality is deliberately the
 * same value as decisionGrade rather than a third invented composite. */
export interface TradeReportCard {
  vaultEntryId: string;
  symbol: string;
  evidenceScore: number;
  confidenceScore: number;
  capitalAllocationGrade: DecisionGrade;
  decisionGrade: DecisionGrade;
  disciplineGrade: DisciplineTier;
  patienceGrade: DecisionGrade;
  overallTradeQuality: DecisionGrade;
  wouldTakeAgain: boolean;
  recommendation: string;
}

export interface SimilarTradeMatch {
  vaultEntryId: string;
  symbol: string;
  simDay: number;
  pnlPct: number;
  decisionGrade: DecisionGrade;
}

/** The Decision Memory System's Similarity Engine — real, rule-based
 * tiered bucket matching over the Decision Vault (never a fabricated
 * similarity score). `matchedOn` names exactly which real dimensions
 * produced the match, so it's never a black box. See
 * backend/app/decision_vault.py's find_similar_vault_entries(). */
export interface SimilarTradesSummary {
  matchCount: number;
  matchedOn: string[];
  winRatePct: number;
  avgPnlPct: number;
  worstPnlPct: number;
  bestRegime: MarketIntelligenceRegime | null;
  worstRegime: MarketIntelligenceRegime | null;
  mostCommonMistakeCategory: CaseStudyCategory | null;
  warning: string | null;
  examples: SimilarTradeMatch[];
}

/** Design Bible Chapter 61's Knowledge Quality Score. Computed fresh per
 * request (never persisted) from three real signals over the Similarity
 * Engine — see backend/app/decision_vault.py's
 * compute_knowledge_quality_score() for the full honesty boundary,
 * including why patternFrequency is a real proxy, not a literal usage
 * counter, and why the brief's Accuracy/Usefulness/Validation dimensions
 * aren't here at all. */
export interface KnowledgeQualityScore {
  vaultEntryId: string;
  matchedOn: string[];
  historicalSuccessPct: number | null;
  patternFrequency: number;
  relevancePct: number;
  overallScore: number;
}

/** v0.7 Feature 55 (the brief self-numbered it "Feature 54," already used
 * above for the Decision Memory System) — the Executive Decision
 * Simulator's War Room. A real, probability-weighted read over
 * WhatIfSimulation's own 12 real scenarios, never a fabricated forecast.
 * riskToReward is deliberately labeled that, not "R-Multiple" — no
 * stop-loss/initial-risk unit exists anywhere in this codebase to
 * measure R against (see DecisionVaultEntry.rMultiple above). */
export interface ExpectedValueAnalysis {
  expectedValuePct: number;
  edgePct: number;
  riskToReward: number;
  positiveExpectancy: boolean;
  detail: string;
}

/** One real IF/THEN contingency step, tied to a real signal already
 * computed for this symbol this tick — never an invented playbook.
 * `triggered` reports whether that condition is true right now. */
export interface ContingencyStep {
  condition: string;
  action: string;
  triggered: boolean;
}

/** A composite over 7 real sub-scores (strategyHealthScore is always
 * null for an ordinary Trading Floor proposal — no proposal links back
 * to a tested Strategy), checked against the same 70-point "good
 * decision" bar app/discipline.py's tier_for_score() already uses.
 * `passed` is a real, visible flag the CEO sees — never an automatic
 * veto (see backend/app/war_room.py's module docstring). */
export interface DecisionScoreBreakdown {
  evidenceScore: number;
  confidenceScore: number;
  riskScore: number;
  expectedValueScore: number;
  strategyHealthScore: number | null;
  marketQualityScore: number;
  liquidityQualityScore: number;
  portfolioCompatibilityScore: number;
  overall: number;
  threshold: number;
  passed: boolean;
}

/** Filled in once a WarRoomSession's linked trade actually closes — the
 * real scenario whose predicted range midpoint sits closest to what
 * actually happened, and whether the real outcome landed inside that
 * scenario's own predicted range. Never a claim the scenario "predicted"
 * the trade, only an honest after-the-fact comparison. */
export interface ScenarioOutcomeComparison {
  matchedScenario: ScenarioType;
  matchedLabel: string;
  predictedRangeLowPct: number;
  predictedRangeHighPct: number;
  actualPnlPct: number;
  withinPredictedRange: boolean;
  detail: string;
}

/** One permanent record per new TradeProposal, joining every real
 * artifact already generated for it — department opinions, the
 * executive recommendation, the What-If simulation, the Decision
 * Vault's similarity summary, expected value, decision score, and
 * contingency plan. Built eagerly the instant the proposal is created
 * (see backend/app/war_room.py's build_war_room_session()), the same
 * convention Debate/ChallengeReport already use. */
export interface WarRoomSession {
  id: string;
  proposalId: string;
  symbol: string;
  departmentOpinions: DepartmentOpinion[];
  recommendation: ExecutiveRecommendation;
  scenarioSimulation: WhatIfSimulation;
  similarTrades: SimilarTradesSummary;
  expectedValue: ExpectedValueAnalysis;
  decisionScore: DecisionScoreBreakdown;
  contingencyPlan: ContingencyStep[];
  /** Always true by construction — see backend/app/war_room.py's
   * evidence_never_exceeds_confidence(). Computed, not hardcoded, so a
   * future change that ever broke the invariant would show up honestly. */
  confidenceValidated: boolean;
  outcomeComparison: ScenarioOutcomeComparison | null;
  createdAt: string;
  /** v0.7 Chapter 57 — null only for sessions saved before this field
   * existed (pre-Chapter 57), never for a real session created after. */
  positionSizing: PositionSizingResult | null;
}

/** v0.7 Chapter 57 — Institutional Position Sizing & Capital Deployment
 * Engine. Four gates, each combining the Sizing Score (this session's own
 * decisionScore.overall, reused directly rather than a second composite)
 * with real portfolio-health/expected-value context — never Sizing Score
 * alone. Institutional additionally requires decisionScore.passed, real
 * positive expected value, cool Portfolio Heat, and no active critical
 * risk warning for the symbol. */
export type PositionTier = "exploratory" | "standard" | "high_conviction" | "institutional";

/** The engine's real, logged justification for one proposal's final
 * quantity — never a bare number with no trail. finalQuantity is always
 * <= ceilingQuantity: this engine only ever narrows what
 * backend/app/risk_engine.py's recommended_quantity() already allows,
 * never widens it (see backend/app/position_sizing.py's module
 * docstring). */
export interface PositionSizingResult {
  tier: PositionTier;
  tierLabel: string;
  sizingScore: number;
  ceilingQuantity: number;
  tierCapQuantity: number;
  finalQuantity: number;
  capitalDeployedPct: number;
  weeklyDeploymentPct: number;
  weeklyDeploymentCapPct: number;
  cashReserveOk: boolean;
  portfolioHeatCapOk: boolean;
  institutionalGatesPassed: boolean;
  reducedFromCeiling: boolean;
  detail: string;
}

/** v0.7 Feature 56 — Enterprise Portfolio Intelligence. "Category" is
 * this codebase's honest stand-in for "sector" — there is no real
 * sector taxonomy, only each symbol's ResearchCategory (see
 * backend/app/watchlist.py's SYMBOL_CATEGORY). */
export interface CategoryExposure {
  category: ResearchCategory;
  positionCount: number;
  value: number;
  pctOfEquity: number;
}

/** A real Pearson correlation coefficient between two currently-held
 * symbols' own recent candle-to-candle returns — never an invented
 * relationship. Only reported once |correlation| clears a real
 * threshold, so a portfolio of genuinely unrelated positions reports
 * none (see backend/app/portfolio_intelligence.py's
 * CORRELATION_CLUSTER_THRESHOLD). */
export interface CorrelationPair {
  symbolA: string;
  symbolB: string;
  correlation: number;
  direction: "positive" | "negative";
}

/** A real, visible READING across four tiers — never an automatic
 * corrective action (docs/ROADMAP.md's own v0.8 stop condition: "risk is
 * measured and displayed, never auto-hedged or auto-corrected without
 * the player"). Nothing reads this and places, closes, or resizes an
 * order. */
export interface PortfolioHeat {
  totalCapitalAtRiskPct: number;
  unrealizedDrawdownPct: number;
  largestPositionPct: number;
  hottestCategory: ResearchCategory | null;
  hottestCategoryPct: number;
  tier: "cool" | "warm" | "hot" | "overheated";
}

/** Real profit-per-dollar / profit-per-dollar-hour, averaged only over
 * actually-closed trades — never a forward-looking prediction. */
export interface CapitalEfficiency {
  profitPerDollar: number;
  profitPerDollarHour: number;
  tradesMeasured: number;
}

/** Recomputed fresh every tick, the same "cheap, always current, never a
 * stale second copy" convention companyHealth/marketIntelligence already
 * use. See backend/app/portfolio_intelligence.py's module docstring for
 * the full honesty boundary, including why Max Drawdown is deliberately
 * not duplicated here (see PerformanceSnapshot.maxDrawdownPct instead). */
export interface PortfolioIntelligence {
  equity: number;
  cashBalance: number;
  cashPctOfEquity: number;
  deployedPctOfEquity: number;
  categoryExposure: CategoryExposure[];
  correlationPairs: CorrelationPair[];
  heat: PortfolioHeat;
  capitalEfficiency: CapitalEfficiency;
  opportunityCost: string;
  updatedAt: string;
}

// Design Bible Chapter 71 — Economic Intelligence Center
// (backend/app/economic_intelligence.py). This codebase has no real
// macroeconomic data source anywhere (no API keys, no live feed) — EIC
// is a real cross-signal SYNTHESIS layer over already-real state
// (MarketEnvironment's regime, MarketIntelligence's quality/news-risk,
// PortfolioIntelligence's correlation/category/heat), never a tracker of
// real central banks, real economic calendars, or real global events.
export type EconomicHealthTier = "thriving" | "stable" | "cautious" | "stressed" | "critical";

/** One real, named, published-formula input — never a blended/hidden
 * number (this Design Bible's "no black-box composite" convention). */
export interface EconomicSignalFactor {
  name: string;
  score: number; // 0-100, higher = healthier
  weight: number;
  detail: string;
}

export interface EconomicHealthScore {
  overall: number; // 0-100
  tier: EconomicHealthTier;
  factors: EconomicSignalFactor[];
  reasoning: string;
}

/** Never presents the health read as fact — confidence, evidence
 * quality, and named supporting/contradicting evidence, the same
 * convention DecisionConfidence already established for trade decisions. */
export interface EconomicConfidenceRead {
  confidencePct: number;
  evidenceQuality: "thin" | "moderate" | "strong";
  supportingEvidence: string[];
  contradictingEvidence: string[];
  keyAssumptions: string[];
  alternativeOutcome: string;
}

/** A real, evidence-cited explanation — never invented causality like
 * "the Fed cut rates" (no real Fed data exists here). Always a diff
 * against the company's own last stored EconomicIntelligenceReport. */
export interface MarketNarrativeEntry {
  id: string;
  headline: string;
  body: string;
  evidence: string[];
  simDay: number;
  createdAt: string;
}

/** The always-current cross-signal read — recomputed fresh every tick,
 * same "cheap, never a stale second copy" convention as
 * companyHealth/marketIntelligence/portfolioIntelligence. */
export interface EconomicIntelligenceState {
  regime: MarketEnvironmentRegime;
  regimeLabel: string;
  marketQualityTier: MarketQualityTier;
  health: EconomicHealthScore;
  confidence: EconomicConfidenceRead;
  correlationPairs: CorrelationPair[];
  categoryExposure: CategoryExposure[];
  newsRisk: NewsRiskRead;
  updatedAt: string;
}

/** One real, permanent snapshot per real in-game day (the Daily
 * Economic Intelligence Brief), same cadence as MarketIntelligenceReport. */
export interface EconomicIntelligenceReport {
  id: string;
  simDay: number;
  snapshot: EconomicIntelligenceState;
  narrative: MarketNarrativeEntry;
  createdAt: string;
}

// Design Bible Chapter 72 — Black Swan Intelligence & Resilience System
// (backend/app/black_swan.py). This codebase has no historical
// black-swan dataset, no real broker connection, and no macro/sector/
// credit data — BSIRS is a real stress-and-resilience SYNTHESIS layer
// over already-real signals, never a tracker of real historical crises
// or a real broker health monitor.
export type BlackSwanRiskTier = "green" | "yellow" | "orange" | "red" | "critical";

/** Higher score always means MORE stress — the opposite direction of
 * EconomicSignalFactor's "higher = healthier". */
export interface BlackSwanSignalFactor {
  name: string;
  score: number; // 0-100, higher = more stress
  weight: number;
  detail: string;
}

export interface EarlyWarningScore {
  overall: number; // 0-100
  tier: BlackSwanRiskTier;
  factors: BlackSwanSignalFactor[];
  reasoning: string;
}

export interface BlackSwanConfidenceRead {
  confidencePct: number;
  evidenceQuality: "thin" | "moderate" | "strong";
  supportingEvidence: string[];
  contradictingEvidence: string[];
  keyAssumptions: string[];
  alternativeOutcome: string;
}

export interface BlackSwanNarrativeEntry {
  id: string;
  headline: string;
  body: string;
  evidence: string[];
  simDay: number;
  createdAt: string;
}

/** The always-current stress read — recomputed fresh every tick, same
 * convention as companyHealth/portfolioIntelligence/economicIntelligence. */
export interface BlackSwanIntelligenceState {
  warning: EarlyWarningScore;
  confidence: BlackSwanConfidenceRead;
  updatedAt: string;
}

export interface BlackSwanReport {
  id: string;
  simDay: number;
  snapshot: BlackSwanIntelligenceState;
  narrative: BlackSwanNarrativeEntry;
  createdAt: string;
}

/** `automatic` is true only for the two actions this codebase's own
 * "never auto-correct a position without the player" principle allows
 * to actually apply while Defensive Mode is active: tightening
 * RiskLimits and pausing new proposal generation. Every other
 * recommendation (closing a position, raising cash) always requires
 * the CEO to act manually. */
export interface DefensiveModeRecommendation {
  action: string;
  detail: string;
  automatic: boolean;
}

export interface DefensiveModeState {
  active: boolean;
  triggerTier: BlackSwanRiskTier;
  autoTriggerEnabled: boolean;
  activatedAt: string | null;
  deactivatedAt: string | null;
  activationReason: string | null;
  priorRiskLimits: RiskLimits | null;
  equityAtActivation: number | null;
  peakTierThisEpisode: BlackSwanRiskTier | null;
  activatedSimMinutes: number | null;
  recommendations: DefensiveModeRecommendation[];
}

export interface StressTestLevelResult {
  shockPct: number;
  resultingEquity: number;
  resultingDrawdownPct: number;
  breachesMaxDrawdown: boolean;
  capitalSurvives: boolean;
  recoveryDaysEstimate: number | null;
  recoveryNote: string;
}

export interface PortfolioStressTestResult {
  accountId: string | null;
  accountLabel: string;
  startingEquity: number;
  heldPositionLiquidityScore: number | null;
  levels: StressTestLevelResult[];
  computedAt: string;
}

export type BlackSwanScenarioType = "flash_crash" | "severe_selloff" | "liquidity_freeze" | "correlation_breakdown";

export interface PortfolioScenarioResult {
  scenarioType: BlackSwanScenarioType;
  label: string;
  accountId: string | null;
  accountLabel: string;
  startingEquity: number;
  shockedEquity: number;
  impactPct: number;
  impactAmount: number;
  categoryImpact: CategoryExposure[];
  breachesMaxDrawdown: boolean;
  capitalSurvives: boolean;
  detail: string;
  computedAt: string;
}

export interface PlaybookStep {
  label: string;
  detail: string;
}

/** One real, generically-named Elevated Risk Response Playbook —
 * live-populated with today's actual Defensive Mode recommendations,
 * never one of eight fabricated event-specific documents. */
export interface BlackSwanPlaybook {
  currentTier: BlackSwanRiskTier;
  immediateActions: PlaybookStep[];
  departmentResponsibilities: PlaybookStep[];
  ceoChecklist: PlaybookStep[];
  recoveryPlan: string;
  updatedAt: string;
}

/** Honestly static — no real broker connection exists in this codebase
 * to monitor, so this is never a live health score. */
export interface BrokerResilienceRead {
  status: "simulated";
  message: string;
}

export interface BlackSwanEventRecord {
  id: string;
  triggerReason: string;
  peakTier: BlackSwanRiskTier;
  activatedAt: string;
  deactivatedAt: string;
  durationSimMinutes: number;
  equityAtActivation: number;
  equityAtDeactivation: number;
  equityChangePct: number;
  largestContributingFactor: string;
  affectedSymbols: string[];
  lesson: string;
  createdAt: string;
}

// Design Bible Chapter 72 Part 2 — Institutional Survival Score. Reuses
// three of the Early Warning Score's own already-computed factors
// (inverted back to "how resilient" instead of "how stressed"). No
// "Leverage"/"Counterparty Risk" input and no "Estimated Survival
// Probability" — see backend/app/black_swan.py's module docstring.
export type InstitutionalSurvivalGrade = "a_plus" | "a" | "b" | "c" | "d" | "f";

/** Higher score always means MORE resilient — the same direction as
 * EconomicSignalFactor (opposite of BlackSwanSignalFactor). */
export interface SurvivalScoreFactor {
  name: string;
  score: number; // 0-100, higher = more resilient
  weight: number;
  detail: string;
}

export interface InstitutionalSurvivalScore {
  overall: number; // 0-100
  grade: InstitutionalSurvivalGrade;
  factors: SurvivalScoreFactor[];
  primaryStrengths: string[];
  primaryWeaknesses: string[];
  topImprovements: string[];
  reasoning: string;
  updatedAt: string;
}

// Design Bible Chapter 73 — Compliance, Audit & Governance System (CAGS).
// A read-only synthesis layer, fetched on demand via app/net/api.ts —
// unlike every other feature above, CAGS adds NO GameSaveState fields
// and is NOT part of the WS broadcast or gameStore; see
// backend/app/audit_log.py's module docstring for the full honesty
// boundary (no per-event Broker/User/Software-Version fields, no
// mutable Incident workflow, no Institutional Time Machine replay).
export type AuditEventCategory =
  | "ceo_decision"
  | "gatekeeper_rejection"
  | "opportunity_rejection"
  | "risk_warning"
  | "discipline_review"
  | "emergency_stop"
  | "defensive_mode"
  | "crisis_briefing"
  | "rule_violation";

export interface AuditEntry {
  id: string;
  timestamp: string;
  simDay: number;
  category: AuditEventCategory;
  severity: AlertSeverity;
  department: string;
  summary: string;
  detail: string;
  relatedId: string | null;
}

/** One real, disclosed layer of the actual decision pipeline this
 * codebase enforces every tick — `order` is the real position
 * app/gatekeeper.py::evaluate_gatekeeper() checks it in; `wired` is
 * false only for the Institutional Rule Engine (Chapter 69 Part 3's
 * own documented gap: real, but not yet routed into live trade
 * execution for non-primary accounts). */
export interface GovernanceLayer {
  order: number;
  name: string;
  module: string;
  description: string;
  wired: boolean;
}

export interface ComplianceOverview {
  complianceScore: number;
  openIncidentCount: number;
  criticalIncidentCount: number;
  totalAuditEntries: number;
  ceoOverrideCount: number;
  ceoOverrideRatePct: number;
  defensiveModeActive: boolean;
  emergencyStopActive: boolean;
  executiveAccuracy: ExecutiveAccuracyScore[];
  updatedAt: string;
}

export interface CeoOverrideRecord {
  id: string;
  proposalId: string;
  symbol: string;
  aiRecommendation: AnalystChoice;
  ceoDecision: AnalystChoice;
  outcome: "pending" | "correct" | "incorrect" | "undecidable";
  createdAt: string;
}

// CEO directive "Features 31-35: Compliance, Governance & Continuous
// Improvement System," Feature 31 — the Compliance Incident Resolution
// Engine (backend/app/compliance_incidents.py). Unlike the rest of CAGS
// above, ComplianceIncident IS persisted (GameSaveState.complianceIncidents)
// and mutable via the lifecycle endpoints below — still fetched on demand,
// not part of the WS broadcast/gameStore (a 500-entry backlog has no
// reason to ride every tick).
export type IncidentStatus = "open" | "investigating" | "remediation" | "awaiting_verification" | "resolved" | "reopened";

export type IncidentRootCause =
  | "process_failure"
  | "control_failure"
  | "data_failure"
  | "model_failure"
  | "human_error"
  | "governance_failure"
  | "communication_failure"
  | "unknown";

export type IncidentVerificationStatus = "not_verified" | "verified" | "verification_failed";

export interface ComplianceIncident {
  id: string;
  sourceEntryId: string;
  category: AuditEventCategory;
  severity: AlertSeverity;
  department: string;
  summary: string;
  detail: string;
  relatedId: string | null;
  createdAt: string;
  simDay: number;
  status: IncidentStatus;
  owner: AgentId | null;
  evidence: string[];
  remediationPlan: string | null;
  deadlineSimDay: number | null;
  resolvedAt: string | null;
  resolutionSimDay: number | null;
  verificationStatus: IncidentVerificationStatus;
  verifier: AgentId | null;
  rootCause: IncidentRootCause | null;
  correctiveAction: string | null;
  reopenedCount: number;
  updatedAt: string;
}

export interface ComplianceIncidentSummary {
  totalCount: number;
  openCount: number;
  resolvedCount: number;
  overdueCount: number;
  reopenedIncidentCount: number;
  severityWeightedBacklog: number;
  averageResolutionSimDays: number | null;
  updatedAt: string;
}

// CEO directive "Features 31-35," Feature 32 — CEO Override Governance
// (backend/app/override_governance.py). Persisted (GameSaveState.ceoOverrideEvaluations),
// still fetched on demand — same convention as ComplianceIncident above.
export type OverrideProcessQuality = "justified" | "unjustified" | "mixed" | "not_enough_evidence";

export interface CeoOverrideEvaluation {
  id: string;
  decisionId: string;
  proposalId: string;
  symbol: string;
  createdAt: string;
  simDay: number;
  originalRecommendation: AnalystChoice;
  recommendationSource: "executive_network";
  ceoDecision: AnalystChoice;
  overrideReason: string | null;
  originalConfidencePct: number | null;
  originalDecisionGrade: DecisionGrade | null;
  originalDecisionGradeScore: number | null;
  riskDepartmentStance: ExecutiveStance | null;
  departmentAgreementPct: number | null;
  agreeingDepartments: ExecutiveDepartmentRole[];
  evidenceAtDecisionTime: string[];
  processQuality: OverrideProcessQuality;
  outcome: "pending" | "correct" | "incorrect" | "undecidable";
  reviewer: AgentId | null;
  reviewNote: string | null;
  reviewedAt: string | null;
  updatedAt: string;
}

export interface CeoOverrideGovernanceSummary {
  totalOverrideCount: number;
  totalDecisionCount: number;
  overrideRatePct: number | null;
  justifiedCount: number;
  unjustifiedCount: number;
  mixedCount: number;
  notEnoughEvidenceCount: number;
  outcomeCorrectCount: number;
  outcomeIncorrectCount: number;
  outcomePendingCount: number;
  outcomeUndecidableCount: number;
  departmentOverrideImpact: Record<string, number>;
  sampleSizeSufficient: boolean;
  updatedAt: string;
}

// CEO directive "Features 31-35," Feature 34 — Compliance Control
// Effectiveness (see backend/app/control_effectiveness.py). Read-only,
// fetched on demand — no WS-broadcast field backs it, the same CAGS
// convention as CeoOverrideGovernanceSummary above.
export type GatekeeperControlEffectivenessState = "effective" | "ineffective" | "mixed" | "insufficient_data" | "not_yet_tested";

export interface ControlEffectivenessRecord {
  controlId: string;
  controlLabel: string;
  purpose: string;
  owner: string;
  triggeredCount: number;
  passedCount: number;
  failedCount: number;
  soleReasonRejectionCount: number;
  confirmedPreventedCount: number;
  confirmedFalsePositiveCount: number;
  pendingEvaluationCount: number;
  ambiguousAttributionCount: number;
  effectivenessState: GatekeeperControlEffectivenessState;
  controlRegression: boolean;
  lastTriggeredAt: string | null;
  lastEvaluatedAt: string | null;
}

export interface ControlEffectivenessSummary {
  controls: ControlEffectivenessRecord[];
  totalControls: number;
  effectiveCount: number;
  ineffectiveCount: number;
  mixedCount: number;
  insufficientDataCount: number;
  notYetTestedCount: number;
  regressedControlCount: number;
  updatedAt: string;
}

// CEO directive "Features 31-35," Feature 35 — the Continuous
// Compliance Improvement Loop (see backend/app/continuous_improvement.py).
// Read-only, fetched on demand — no WS-broadcast field, the same CAGS
// convention as ControlEffectivenessSummary above.
export type RemediationEffectivenessState = "effective" | "partially_effective" | "ineffective" | "not_enough_evidence";

export interface RemediationEffectivenessRecord {
  incidentId: string;
  rootCause: IncidentRootCause;
  correctiveAction: string;
  category: AuditEventCategory;
  department: string;
  resolvedAt: string;
  resolutionSimDay: number;
  reopenedCount: number;
  recurrenceCount: number;
  effectivenessState: RemediationEffectivenessState;
}

export interface RootCauseRecurrence {
  rootCause: IncidentRootCause;
  incidentCount: number;
  recurringFailure: boolean;
  firstOccurredAt: string;
  lastOccurredAt: string;
  incidentIds: string[];
}

export interface ContinuousImprovementSummary {
  remediations: RemediationEffectivenessRecord[];
  rootCauseRecurrences: RootCauseRecurrence[];
  effectiveCount: number;
  partiallyEffectiveCount: number;
  ineffectiveCount: number;
  notEnoughEvidenceCount: number;
  recurringFailureCount: number;
  updatedAt: string;
}

// Design Bible Chapter 75 — Company Trading Modes & Institutional
// Capital Protection (see backend/app/trading_modes.py). tradingModes/
// dailyCircuitBreaker/losingStreak/recoveryBriefings are real, part of
// the WS tick broadcast (gameStore) — unlike Chapter 73's CAGS.
// Performance split, Trading Mode Health, and the Adaptive Mode
// recommendation are fetched on demand via net/api.ts instead (no
// WS-broadcast field backs them — the same on-demand pattern CAGS
// established), so their types live only where api.ts imports them.
export type TradingMode = "day_trading" | "swing_trading" | "hybrid";
export type TradingStyle = "day" | "swing";

export interface TradingModeState {
  mode: TradingMode;
  hybridDayAllocationPct: number;
  changedAt: string;
  previousMode: TradingMode | null;
  changeReason: string;
  rotationCounter: number;
  adaptiveRecommendationsEnabled: boolean;
  tier1Pct: number;
  tier2Pct: number;
  tier3Pct: number;
  losingStreakPauseCount: number;
  losingStreakSuspendCount: number;
  losingStreakAcknowledged: boolean;
  // Behavioral Circuit Breaker (backend/app/behavioral_risk.py) — the
  // CEO's own real, editable thresholds for the revenge-trading
  // detector's timing and self-relative sizing signals.
  behavioralCooldownMinutes: number;
  behavioralSizeIncreaseThresholdPct: number;
}

export type DailyCircuitBreakerTier = "none" | "tier1" | "tier2" | "tier3" | "tier4";

export interface DailyCircuitBreakerRead {
  tier: DailyCircuitBreakerTier;
  dailyPnlPct: number;
  tier1Pct: number;
  tier2Pct: number;
  tier3Pct: number;
  tier4Pct: number;
  updatedAt: string;
}

export interface LosingStreakRead {
  consecutiveLosses: number;
  pauseActive: boolean;
  pauseThreshold: number;
  suspendThreshold: number;
}

// Behavioral Circuit Breaker — the revenge-trading detector, the tenth
// real Gatekeeper check (backend/app/gatekeeper.py::_behavioral_check).
// "warning" is informational only and never blocks; only "triggered"
// fails the Gatekeeper check for the specific proposal being resolved.
// This system detects observable behavioral risk. It does not claim to
// detect human emotion.
export type BehavioralCircuitBreakerStatus = "clear" | "warning" | "triggered";

export interface BehavioralCircuitBreakerRead {
  status: BehavioralCircuitBreakerStatus;
  reasons: string[];
  previousLossSymbol: string | null;
  previousLossPnl: number | null;
  minutesSinceLoss: number | null;
  cooldownMinutes: number;
  sameInstrument: boolean | null;
  /** Piece 8b — informational only, never independently corroborates a
   * "triggered" verdict (see backend/app/behavioral_risk.py's docstring). */
  sameDirection: boolean | null;
  sizeIncreasePct: number | null;
  consecutiveLosses: number;
  /** Piece 11b, Requirement 24 — exact mirror of consecutiveLosses,
   * walking backward until a real loss (pnl <= 0) or history ends. */
  consecutiveWins: number;
  repeatedRapidReentryCount: number;
  /** Piece 8b — win-triggered escalation. Populated only when the most
   * recent closed trade was a real win; mutually exclusive with the
   * previousLoss / sameInstrument / sizeIncreasePct fields above. Can
   * only ever accompany status "clear" or "warning", never "triggered". */
  previousWinSymbol: string | null;
  previousWinPnl: number | null;
  minutesSinceWin: number | null;
  winSizeIncreasePct: number | null;
  computedAt: string;
}

export interface RecoveryBriefing {
  id: string;
  trigger: "circuit_breaker_tier4" | "losing_streak";
  summary: string;
  recentWinRate: number;
  recentAvgLossPct: number;
  largestLossPct: number;
  daysSinceLastProfitableDay: number | null;
  linkedDisciplineReviewIds: string[];
  createdAt: string;
}

export interface AdaptiveModeRecommendation {
  recommendedMode: TradingMode | null;
  reasoning: string;
  confidencePct: number;
  note: string | null;
  generatedAt: string;
}

export interface TradingStylePerformance {
  style: TradingStyle;
  tradeCount: number;
  winRate: number;
  totalPnl: number;
  avgPnlPct: number;
}

export interface TradingModeHealthAssessment {
  style: TradingStyle;
  status: StrategyHealthStatus;
  trend: StrategyHealthTrend;
  recentWinRate: number;
  lifetimeWinRate: number;
  recentAvgReturnPct: number;
  lifetimeAvgReturnPct: number;
  recentSampleSize: number;
  lifetimeSampleSize: number;
  reasoning: string[];
}

// Design Bible Chapter 74 — Continuous Learning & Self-Improvement
// System (CLSIS, Part 1) and the Institutional Evolution Engine (Part
// 2) (see backend/app/self_improvement.py and backend/app/evolution.py).
// selfImprovementProposals/evolutionReports are real, part of the WS
// tick broadcast (gameStore) — the same convention tradingModes above
// established. Executive Learning Summary and the Company Evolution
// Score have no WS-broadcast field and are fetched on demand instead.
export type SelfImprovementCategory =
  | "risk_rule"
  | "dashboard"
  | "research_workflow"
  | "position_sizing"
  | "new_executive"
  | "automation"
  | "knowledge_organization"
  | "ui";
export type SelfImprovementStatus = "pending" | "approved" | "rejected" | "implemented";
export type SelfImprovementComplexity = "small" | "medium" | "large";
export type SelfImprovementPriority = "low" | "medium" | "high";

export interface SelfImprovementProposal {
  id: string;
  category: SelfImprovementCategory;
  title: string;
  reasoning: string;
  evidence: string[];
  benefits: string[];
  risks: string[];
  estimatedComplexity: SelfImprovementComplexity;
  priority: SelfImprovementPriority;
  confidence: number;
  status: SelfImprovementStatus;
  ceoNote: string | null;
  visionAlignmentScore: number | null;
  implementationNote: string | null;
  implementedAt: string | null;
  simDay: number;
  createdAt: string;
  decidedAt: string | null;
}

export interface ExecutiveLearningSummary {
  agentId: AgentId;
  researchAccuracy: number | null;
  confidenceCalibration: number | null;
  thinkingProfile: ThinkingProfile | null;
  knowledgePoints: number;
  knowledgeTier: number;
  knowledgeLevel: string;
  mentorTracks: string[];
  graduatedTrackCount: number;
}

export type CompanyEvolutionWindow = "monthly" | "quarterly" | "yearly";

export interface CompanyEvolutionScore {
  window: CompanyEvolutionWindow;
  overall: number;
  learningVolume: number;
  proposalExecution: number;
  knowledgeGrowth: number;
  strategyMaturation: number;
  governanceEvolution: number;
  periodStartSimDay: number;
  periodEndSimDay: number;
  computedAt: string;
}

export interface InstitutionalEvolutionReport {
  id: string;
  strategicReviewId: string | null;
  executiveReviewId: string | null;
  coachReportId: string | null;
  topCaseStudyIds: string[];
  topSuccessStudyIds: string[];
  proposalsGenerated: string[];
  proposalsResolved: string[];
  evolutionScore: CompanyEvolutionScore;
  summary: string;
  simDay: number;
  createdAt: string;
}

// Trading Psychology & Discipline, Piece D — Loss/Win Classification,
// formalized on top of the Discipline Chamber (Design Bible Chapter 74
// addendum). Fetched on demand (GET /api/self-improvement/loss-win-
// classification), the same convention CompanyEvolutionScore above uses
// — no WS-broadcast field, computed fresh from DisciplineReview/
// CaseStudy every call.
export interface DisciplineTierOutcomeCount {
  tier: DisciplineTier;
  winCount: number;
  lossCount: number;
}

export interface LossWinClassificationRead {
  totalReviewed: number;
  winCount: number;
  lossCount: number;
  winRatePct: number | null;
  byTier: DisciplineTierOutcomeCount[];
  alignedCount: number;
  misalignedCount: number;
  unluckyLossCount: number;
  luckyWinCount: number;
  mostCommonMistakeCategory: CaseStudyCategory | null;
  mostCommonMistakeCount: number;
  mostCommonSuccessCategory: CaseStudyCategory | null;
  mostCommonSuccessCount: number;
  computedAt: string;
}

// Design Bible Chapter 74.5 — CEO Vision Board & Strategic Alignment
// Engine (see backend/app/vision_board.py). visionBoard is real, part
// of the WS tick broadcast — the same convention tradingModes/
// selfImprovementProposals above established. Alignment lookups and the
// Self-Correction Note have no WS-broadcast field and are fetched on
// demand instead.
export type VisionPriorityCategory = "growth" | "risk" | "research" | "trading" | "operations" | "governance";
export type VisionObjectiveCategory = "trading_style" | "expansion" | "research_priority" | "technology" | "lifestyle" | "other";

export interface VisionBoardObjective {
  id: string;
  text: string;
  category: VisionObjectiveCategory;
  createdAt: string;
}

export interface VisionBoardState {
  mission: string | null;
  priorities: VisionPriorityCategory[];
  objectives: VisionBoardObjective[];
  identityNote: string | null;
  updatedAt: string;
}

export interface VisionAlignmentScore {
  subjectType: "self_improvement_proposal" | "goal" | "constitution_amendment";
  subjectId: string;
  score: number;
  supportingReasons: string[];
  conflictingGoals: string[];
  confidence: number;
  computedAt: string;
}

export interface VisionSelfCorrectionNote {
  triggered: boolean;
  message: string | null;
  circuitBreakerTier: DailyCircuitBreakerTier;
  computedAt: string;
}

// Design Bible Chapter 73.5 — Mobile Command Center & Remote Operations
// (see backend/app/situation_room.py, backend/app/travel_mode.py).
// situationRoom has no WS-broadcast field (computed fresh per request,
// the same on-demand pattern Chapter 75's Adaptive Mode recommendation
// already established) — fetched via net/api.ts instead. travelMode/
// travelModeBriefings ARE real, part of the WS tick broadcast
// (gameStore), the same convention tradingModes/recoveryBriefings above
// already use.
export type SituationRoomSeverity = "good" | "caution" | "elevated" | "severe" | "critical";

export interface SituationRoomField {
  label: string;
  value: string;
  band: SituationRoomSeverity;
  detail: string;
}

export type PriorityTier = "critical" | "high" | "medium" | "low";

export interface PriorityItem {
  id: string;
  tier: PriorityTier;
  title: string;
  detail: string;
  source: string;
  relatedId: string | null;
}

export interface SituationRoomState {
  companyHealth: SituationRoomField;
  portfolioHealth: SituationRoomField;
  cashPosition: SituationRoomField;
  openRisk: SituationRoomField;
  marketRegime: SituationRoomField;
  tradingMode: SituationRoomField;
  economicHealth: SituationRoomField;
  blackSwanRisk: SituationRoomField;
  executiveConsensus: SituationRoomField;
  pendingCeoDecisions: SituationRoomField;
  brokerStatus: SituationRoomField;
  automationStatus: SituationRoomField;
  emergencyAlerts: SituationRoomField;
  priorities: PriorityItem[];
  generatedAt: string;
}

export type TravelModeActivationSource = "manual" | "auto_inactivity";
export type NotificationSensitivity = "all" | "high_and_above" | "critical_only";

export interface TravelModeSettings {
  positionSizeCapPct: number;
  dailyRiskCapPct: number;
  notificationSensitivity: NotificationSensitivity;
  autoActivateEnabled: boolean;
  autoActivateAfterMinutes: number;
}

export interface TravelModeState {
  active: boolean;
  settings: TravelModeSettings;
  activatedAt: string | null;
  activationSource: TravelModeActivationSource | null;
  deactivatedAt: string | null;
  activatedSimMinutes: number;
  lastCeoDecisionSimMinutes: number;
}

export interface TravelModeBriefing {
  id: string;
  activatedAt: string;
  deactivatedAt: string;
  activationSource: TravelModeActivationSource;
  decisionsResolved: number;
  gatekeeperRejections: number;
  criticalRiskWarnings: number;
  circuitBreakerTierChanges: number;
  realizedPnl: number;
  summary: string;
  createdAt: string;
}

// v0.7 Feature 29 — the Reasoning Lab (see backend/app/reasoning_lab.py).
// A permanent ReasoningChallenge is filed periodically from the
// company's most recent real AI Debate + its linked TradeDecision —
// practicing the reasoning process itself, decoupled from any trade
// outcome. Seven honest categories out of the brief's nine; "Detecting
// Logical Fallacies" and "Building Better Questions" have no real
// checkable signal in this codebase and are deliberately not built.
export type ReasoningChallengeCategory =
  | "finding_missing_information"
  | "identifying_weak_evidence"
  | "recognizing_contradictory_data"
  | "separating_facts_from_assumptions"
  | "evaluating_multiple_hypotheses"
  | "comparing_competing_explanations"
  | "improving_communication";

export interface ReasoningContribution {
  agentId: AgentId;
  role: AnalystRole;
  stance: DebateStance;
  contribution: string;
}

export interface ReasoningSolution {
  whatWeKnow: string[];
  whatWeDoNotKnow: string[];
  assumptions: string[];
  whyReasonable: string;
  confidence: number;
  whatCouldChangeOurConclusion: string;
}

export interface ReasoningChallenge {
  id: string;
  category: ReasoningChallengeCategory;
  title: string;
  symbol: string;
  decisionId: string;
  contributions: ReasoningContribution[];
  solution: ReasoningSolution;
  /** The company's own Reasoning Level at the moment this challenge was
   * generated — advanced categories only ever appear once the level
   * that unlocks them has been reached. */
  reasoningLevel: number;
  /** The real in-game day this challenge was filed — see
   * DisciplineReview.simDay above for why. */
  simDay: number;
  createdAt: string;
}

export interface ReasoningLabState {
  level: number;
  levelLabel: string;
  completedChallengeCount: number;
  updatedAt: string;
}

// v0.7 Feature 30 — the Reflection Chamber (see backend/app/wisdom.py).
// A real ReflectionSession every in-game week and month, generated
// fresh from data already computed elsewhere — never a fabricated
// meeting transcript. The Company Wisdom Score is never profit-based.
export type ReflectionCadence = "weekly" | "monthly";

export interface ReflectionQuestion {
  question: string;
  answer: string;
}

export interface ReflectionInsight {
  agentId: AgentId;
  insight: string;
}

export interface ReflectionSession {
  id: string;
  cadence: ReflectionCadence;
  attendees: AgentId[];
  questions: ReflectionQuestion[];
  insights: ReflectionInsight[];
  keyDiscoveries: string[];
  lessonsLearned: string[];
  importantQuestions: string[];
  recommendedFutureProjects: string[];
  wisdomScore: number;
  simDay: number;
  createdAt: string;
}

export type WisdomFactorId = "learn_from_experience" | "share_knowledge" | "follow_principles" | "improve_communication" | "document_lessons" | "avoid_repeating_mistakes" | "complete_research" | "support_collaboration";
export type WisdomTier = "young_company" | "developing_judgment" | "institutional_memory" | "seasoned_wisdom" | "enduring_wisdom";

export interface WisdomFactor {
  id: WisdomFactorId;
  name: string;
  score: number;
  weight: number;
  detail: string;
}

export interface WisdomState {
  score: number;
  tier: WisdomTier;
  tierLabel: string;
  factors: WisdomFactor[];
  updatedAt: string;
}

// v0.7 Feature 32 — Sage, the Socratic Mentor (see backend/app/mentor.py).
// One QuestionOfTheDay every in-game morning, drawn from a small
// hand-authored library (real curated content, not a fabricated claim
// of free-form generation); `relatedReference` is at most one honest
// pointer into real existing company content, never a fabricated
// per-department "answer." ThinkingProfile is purely computed from
// signals this codebase already tracks elsewhere.
export type QuestionCategory = "critical_thinking" | "decision_making" | "communication" | "leadership" | "psychology" | "risk_awareness" | "research" | "reflection" | "logic" | "teamwork";

export interface QuestionOfTheDay {
  id: string;
  category: QuestionCategory;
  question: string;
  relatedReference: string | null;
  playerResponse: string | null;
  playerRespondedAt: string | null;
  simDay: number;
  createdAt: string;
}

export type ThinkingTraitId = "curiosity" | "evidence_quality" | "open_mindedness" | "humility" | "reasoning" | "collaboration";

export interface ThinkingTrait {
  id: ThinkingTraitId;
  name: string;
  score: number;
  detail: string;
}

export interface ThinkingProfile {
  agentId: AgentId;
  traits: ThinkingTrait[];
  updatedAt: string;
}

export type AgentRoleClass = "researcher" | "risk" | "quant" | "leadership" | "mentor_support";

export type PerformanceDimensionId =
  | "process_quality"
  | "risk_discipline"
  | "decision_accuracy"
  | "calibration"
  | "collaboration"
  | "learning_trend"
  | "recurring_mistakes"
  | "pnl_attribution";

/** `value === null` means NOT_ENOUGH_EVIDENCE for this one dimension —
 * never a fake neutral number. `sampleSize` is always disclosed
 * alongside `value`. */
export interface PerformanceDimension {
  id: PerformanceDimensionId;
  label: string;
  value: number | null;
  sampleSize: number;
  evidence: string;
}

/** CEO directive "Features 26-30," Feature 27 — Agent Performance
 * Reviews (backend/app/performance_review.py). One real, evidence-
 * cited review per agent per real weekly period — never a single
 * blended "agent score." `processQualityAvg`/`outcomeQualityAvg` stay
 * structurally separate; both may be null when no contributing
 * dimension has real data yet. */
export interface AgentPerformanceReview {
  id: string;
  agentId: AgentId;
  roleClass: AgentRoleClass;
  periodStartSimDay: number;
  periodEndSimDay: number;
  dimensions: PerformanceDimension[];
  processQualityAvg: number | null;
  outcomeQualityAvg: number | null;
  evidenceCount: number;
  confidencePct: number;
  trend: "improving" | "declining" | "stable" | "not_enough_history";
  weakestDimensionId: PerformanceDimensionId | null;
  status: "evaluated" | "not_enough_evidence";
  simDay: number;
  createdAt: string;
}

export interface MentorState {
  tier: number;
  tierLabel: string;
  questionsAsked: number;
  updatedAt: string;
}

// CEO directive "Features 26-30," Feature 28 — Academy + Skill
// Progression (backend/app/skill_progression.py). 11 named domains; 6
// are honestly NOT_TRACKABLE_YET (value always null) because no
// per-agent attribution mechanism exists for them today — see that
// module's own docstring for exactly which and why.
export type SkillDomainId =
  | "market_structure"
  | "risk_management"
  | "quant_research"
  | "technical_fundamental_analysis"
  | "execution"
  | "statistical_reasoning"
  | "regime_detection"
  | "prediction_calibration"
  | "communication"
  | "collaboration"
  | "research_quality";

/** `value === null` means NOT_ENOUGH_EVIDENCE (measurable domain, no
 * data yet this period) or NOT_TRACKABLE_YET (no attribution mechanism
 * exists at all) — `evidence` always states honestly which. `trend` is
 * this domain's own real improve/stagnate/regress read against the
 * agent's own previous assessment of the SAME domain. */
export interface SkillAssessment {
  domainId: SkillDomainId;
  label: string;
  value: number | null;
  sampleSize: number;
  evidence: string;
  trend: "improving" | "stagnant" | "regressed" | "not_enough_history";
}

/** One real skill snapshot for one agent over one real period.
 * `recommendedDomainId`/`recommendedMentorId` are the real closed-loop
 * hook the CEO's own worked example asked for — set only when the
 * agent's latest Agent Performance Review's weakest dimension maps to a
 * measurable skill domain with a real, content-backed Foundational
 * Mentor track the agent hasn't already graduated. */
export interface AgentSkillProfile {
  id: string;
  agentId: AgentId;
  periodStartSimDay: number;
  periodEndSimDay: number;
  assessments: SkillAssessment[];
  recommendedDomainId: SkillDomainId | null;
  recommendedMentorId: string | null;
  recommendationReason: string | null;
  simDay: number;
  createdAt: string;
}

// v0.7 Feature 49 (Phase 3, revised) — the Foundational Mentor Program /
// Professional Academy (see backend/app/foundational_mentors.py's
// module docstring for the full content-attribution boundary and the
// "employees are the students" redesign rationale). Real named trading
// educators are used only as CEO-assigned track labels; every lesson's
// actual content is original TradeTown-authored material. Distinct from
// MentorState (Sage) above — that's a single always-available Q&A
// advisor, this is a sequential lesson-and-quiz curriculum with a
// roadmap of tracks. Real EMPLOYEES (STUDENT_AGENT_IDS in derive.ts)
// auto-progress through the company's one active mentor every real
// tick; `progress` below is keyed by employee AgentId. `ceoProgress` is
// the CEO's own entirely separate, optional personal learning bucket.
// A plain string, not a union, as of the Mentor Lab revision: the CEO
// can now really add new mentor tracks in-product (see
// backend/app/foundational_mentors.py's add_custom_mentor). The
// original 6 named ids ("tjr", "al_brooks", ...) still exist as real
// string values — nothing about their content changed, only the type.
export type FoundationalMentorId = string;
export type FoundationalMentorStatus = "planned" | "active" | "paused" | "graduated";
export type FoundationalResourceType = "video" | "book" | "article" | "pdf" | "note";
export type FoundationalGraduationStatus = "in_progress" | "pending_approval" | "graduated";

export interface FoundationalMentorLesson {
  id: string;
  order: number;
  title: string;
  simpleExplanation: string;
  deeperExplanation: string;
  quizQuestion: string;
  quizOptions: string[];
}

export interface FoundationalMentorResource {
  id: string;
  title: string;
  url: string | null;
  resourceType: FoundationalResourceType;
  addedAt: string;
}

export interface FoundationalMentorProfile {
  id: FoundationalMentorId;
  name: string;
  trackLabel: string;
  focusAreas: string[];
  contentNote: string;
  status: FoundationalMentorStatus;
  lessons: FoundationalMentorLesson[];
  resources: FoundationalMentorResource[];
  companyGraduatedSimDay: number | null;
}

export interface FoundationalMentorProgress {
  mentorId: FoundationalMentorId;
  viewedLessonIds: string[];
  completedLessonIds: string[];
  currentLessonStudyPct: number;
  quizAttempts: number;
  correctQuizAttempts: number;
  consecutiveQuizFailures: number;
  graduationStatus: FoundationalGraduationStatus;
  graduatedSimDay: number | null;
  coachNote: string | null;
}

// Certification Management (quality-of-life fix) — a real, independent,
// permanent registry, never derived from FoundationalMentorProgress
// (which a revoke genuinely resets) and never deleted. "expired" is
// deliberately not a status: it would need a real time-based renewal/
// decay signal, which doesn't exist anywhere in this codebase —
// postponed to v1.0 (see docs/ROADMAP.md). See backend/app/schemas.py's
// CertificationStatus doc comment.
export type CertificationStatus = "active" | "suspended" | "revoked";
export type CertificationHistoryAction = "earned" | "suspended" | "reinstated" | "revoked" | "progress_reset";

export interface CertificationHistoryEntry {
  id: string;
  action: CertificationHistoryAction;
  reason: string | null;
  simDay: number;
  createdAt: string;
}

export interface CertificationRecord {
  id: string;
  agentId: AgentId;
  mentorId: FoundationalMentorId;
  mentorName: string;
  status: CertificationStatus;
  updatedSimDay: number;
  history: CertificationHistoryEntry[];
}

export interface FoundationalMentorState {
  mentors: FoundationalMentorProfile[];
  progress: Partial<Record<AgentId, Partial<Record<FoundationalMentorId, FoundationalMentorProgress>>>>;
  // The real, permanent Certification Management registry — see
  // CertificationRecord's own doc comment above.
  certifications: CertificationRecord[];
  ceoProgress: Partial<Record<FoundationalMentorId, FoundationalMentorProgress>>;
  activeMentorId: FoundationalMentorId | null;
  // The real, persisted sequential unlock order — the CEO's own
  // add-mentor action appends to this (see MentorLabPanel.tsx).
  roadmapOrder: FoundationalMentorId[];
  // Hidden answer keys for CEO-authored custom lessons — server-
  // internal bookkeeping (grade_ceo_lesson_quiz), never read directly
  // by the UI (the CEO's own quiz still goes through the API, never
  // grades client-side).
  customLessonAnswers: Record<string, number>;
  updatedAt: string;
}

// v0.7 Feature 44 — the Talent Discovery System (see
// backend/app/talent.py's module docstring). A real, evidence-based
// "Discovery Event" — every field traces back to an agent's own real
// ThinkingProfile trait and real CoachReport score history. "Suggested
// Focus" deliberately replaces the brief's "Suggested Career Path": no
// agent's real occupation ever changes anywhere in this codebase, so a
// literal career-path recommendation would imply a mechanic that
// doesn't exist.
export interface TalentReport {
  id: string;
  agentId: AgentId;
  traitId: string;
  traitName: string;
  title: string;
  narrative: string;
  evidence: string[];
  examples: string[];
  currentScore: number;
  sampleSize: number;
  suggestedFocus: string;
  expectedBenefits: string;
  simDay: number;
  createdAt: string;
}

export interface TalentState {
  reports: TalentReport[];
  viewedReportIds: string[];
  updatedAt: string;
}

// v0.7 Feature 39 — the Original Founders (see backend/app/founders.py's
// module docstring for why this is deliberately not a second Socratic-
// teaching mechanic competing with MentorState above).
export type FounderId = "keystone" | "compass";

// v0.7 Feature 46 — the Company Constitution. See
// backend/app/constitution.py's module docstring for the full research
// rationale, the real "Live Enforcement" citation hooks, and exactly how
// the amendment pipeline (Founder debate -> Coach evaluation -> Employee
// vote -> CEO ratification) is a real, checkable computation rather than
// a fabricated debate transcript.
export interface ConstitutionArticle {
  id: string;
  title: string;
  text: string;
  ratifiedSimDay: number;
  createdAt: string;
}

export type ConstitutionCitationSource = "case_study" | "devils_advocate" | "risk_department" | "academy" | "founders" | "coach";

export interface ConstitutionCitation {
  id: string;
  articleId: string;
  source: ConstitutionCitationSource;
  detail: string;
  simDay: number;
  createdAt: string;
}

export interface ConstitutionFounderVerdict {
  founderId: FounderId;
  verdict: string;
  redundantWithArticleId: string | null;
}

export interface ConstitutionEmployeeVote {
  agentId: AgentId;
  choice: "support" | "oppose" | "abstain";
  reason: string;
}

export interface ConstitutionAmendment {
  id: string;
  proposedTitle: string;
  proposedText: string;
  status: "proposed" | "debated" | "evaluated" | "voted" | "approved" | "rejected";
  founderVerdicts: ConstitutionFounderVerdict[];
  coachEvaluation: string | null;
  employeeVotes: ConstitutionEmployeeVote[];
  ceoDecision: "pending" | "approved" | "rejected";
  ratifiedArticleId: string | null;
  simDay: number;
  createdAt: string;
}

export interface ConstitutionState {
  articles: ConstitutionArticle[];
  citations: ConstitutionCitation[];
  amendments: ConstitutionAmendment[];
  updatedAt: string;
}

export interface FounderLogEntry {
  id: string;
  founderId: FounderId;
  line: string;
  reference: string;
  simDay: number;
  createdAt: string;
}

export interface FounderCouncilSession {
  id: string;
  simDay: number;
  coachHighlight: string;
  keystoneNote: string;
  compassNote: string;
  createdAt: string;
}

export interface FounderState {
  retired: boolean;
  retiredAt: string | null;
  log: FounderLogEntry[];
  councilSessions: FounderCouncilSession[];
  updatedAt: string;
}

// v0.7 Feature 33 — the CEO Treasury (see backend/app/treasury.py's
// module docstring for the structural "never touched automatically"
// guarantee).
export type TreasuryTransactionKind = "deposit" | "withdrawal" | "auto_save";

export interface TreasuryTransaction {
  id: string;
  kind: TreasuryTransactionKind;
  amount: number;
  balanceAfter: number;
  note: string;
  simDay: number;
  createdAt: string;
}

export type SavingsRuleType = "percent_of_monthly_profit" | "excess_above_reserve";

export interface SmartSavingsRule {
  id: string;
  ruleType: SavingsRuleType;
  percent: number;
  reserveTarget: number | null;
  active: boolean;
  createdAt: string;
}

export interface TreasuryMonthlyReport {
  id: string;
  monthEndingDay: number;
  deposits: number;
  withdrawals: number;
  autoSaved: number;
  endingBalance: number;
  createdAt: string;
}

export interface TreasuryState {
  balance: number;
  lifetimeDeposits: number;
  largestBalance: number;
  transactions: TreasuryTransaction[];
  savingsRules: SmartSavingsRule[];
  monthlyReports: TreasuryMonthlyReport[];
  updatedAt: string;
}

// v0.7 Feature 36 — the CEO Calendar & Company Schedule (see
// backend/app/calendar.py's module docstring for exactly which of the
// brief's calendar categories are real here and which are explicitly cut).
export type CalendarEventCategory =
  | "morning_briefing"
  | "weekly_coach_report"
  | "monthly_coach_report"
  | "weekly_reflection"
  | "monthly_reflection"
  | "monthly_executive_review"
  | "monthly_treasury_report"
  | "reasoning_challenge_window"
  | "mentorship_window"
  | "company_anniversary"
  | "research_deadline"
  | "emergency_meeting"
  | "company_holiday"
  | "extra_training_day"
  | "research_marathon"
  | "hackathon"
  | "strategy_day"
  | "celebration"
  | "town_hall"
  | "other";

export type PlayerEventCategory =
  | "emergency_meeting"
  | "company_holiday"
  | "extra_training_day"
  | "research_marathon"
  | "hackathon"
  | "strategy_day"
  | "celebration"
  | "town_hall"
  | "other";

export interface CalendarEvent {
  id: string;
  source: "system" | "player";
  category: CalendarEventCategory;
  title: string;
  detail: string;
  day: number;
  hour: number;
  minute: number;
  eligible: boolean | null;
  createdAt: string;
}

export interface CalendarState {
  systemEvents: CalendarEvent[];
  playerEvents: CalendarEvent[];
  updatedAt: string;
}

export interface GameSaveState {
  version: "0.6";
  player: EntityTransform;
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
  // v0.7 Quantitative Research & Intelligence System, Piece 4 —
  // Meridian/CIO's independent, advisory-only ModelValidationReport.
  strategyModelValidations: ModelValidationReport[];
  // v0.7 Feature 52 (Part 1/2) — the Strategy Validation Laboratory.
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
  /** v0.7 Feature 51 — the always-current "eyes," recomputed every tick.
   * marketIntelligenceReports/marketIntelligenceLearning are the
   * permanent, capped daily histories. */
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
  // CEO directive "Features 26-30," Feature 26 — Institutional Memory 2.0.
  institutionalMemory: InstitutionalMemoryEntry[];
  // CEO directive "Features 26-30," Feature 27 — Agent Performance Reviews.
  agentPerformanceReviews: AgentPerformanceReview[];
  // CEO directive "Features 26-30," Feature 28 — Academy + Skill Progression.
  agentSkillProfiles: AgentSkillProfile[];
  // CEO directive "Features 26-30," Feature 29 — Prediction -> Outcome Tracking.
  predictionRecords: PredictionRecord[];
  // CEO directive "Features 26-30," Feature 30 — the Failure Review Board.
  failureClassifications: FailureClassification[];
  // CEO Company Health + Live Market Realism directive, Section 3 — one
  // capped, permanent LearningEvent per real Knowledge-tier crossing.
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
  time: TimeState;
  settings: SettingsState;
  dialogueHistory: DialogueHistoryEntry[];
  updatedAt: string;
  executiveMeetingLog: ExecutiveMeetingLogEntry[];
  departmentSelfEvaluations: DepartmentSelfEvaluation[];
}

// v0.7 — Save Architecture Redesign. The only fields the client actually
// owns (see backend/app/schemas.py's ClientSaveRequest docstring for why
// this replaced sending the full GameSaveState on every save).
export interface ClientSaveSnapshot {
  player: EntityTransform;
  settings: SettingsState;
  dialogueHistory: DialogueHistoryEntry[];
}

export interface ModuleWriteResult {
  name: string;
  ok: boolean;
  bytesWritten: number;
  error: string | null;
}

export interface SaveResponse {
  ok: true;
  updatedAt: string;
  modules: ModuleWriteResult[];
}

export function isDaytime(time: TimeState): boolean {
  return time.hour >= 6 && time.hour < 20;
}
