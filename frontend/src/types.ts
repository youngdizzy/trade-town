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
export type AgentId = "scout" | "atlas" | "echo" | "nova" | "scribe" | "coach" | "sentinel" | "pulse" | "guardian" | "cio" | "sage" | "keystone" | "compass";
export const AGENT_IDS: readonly AgentId[] = ["scout", "atlas", "echo", "nova", "scribe", "coach", "sentinel", "pulse", "guardian", "cio", "sage", "keystone", "compass"];

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
  | "top_agent";
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
  | "no_trade_ok";

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

export interface Strategy {
  id: string;
  name: string;
  description: string;
  createdBy: AgentId;
  focusCategory: ResearchCategory;
  createdAt: string;
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
}

export interface HallOfFameEntry {
  id: string;
  category: HallOfFameCategory;
  title: string;
  description: string;
  agentId: AgentId | null;
  value: number;
  achievedAt: string;
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
export interface RiskLimits {
  maxPositionPct: number;
  maxDailyLossPct: number;
  maxDrawdownPct: number;
  maxOpenPositions: number;
  maxSectorConcentrationPct: number;
  riskPerTradePct: number;
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
  createdAt: string;
}

// v0.6.3 Feature 12 — Executive Voting (CEO Approval). A research
// candidate crossing the trade-confidence threshold no longer executes
// automatically: it becomes a TradeProposal and waits for the CEO (the
// player) to cast the real buy/sell/wait call. See backend/app/executive.py.
export type AnalystRole = "technical" | "news" | "macro" | "risk" | "sentiment" | "execution";
export type AnalystChoice = "buy" | "sell" | "wait";

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
   * — neither was ever a real CEO decision. Defaults to "ceo" on records
   * predating this field, which were all real clicks. */
  resolvedBy: "ceo" | "auto";
  createdAt: string;
  resolvedAt: string | null;
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
  officeExpansion: number;
  educationProgress: number;
  recommendations: string[];
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

// v0.7 Feature 25.5 — Company Knowledge Graph (see
// backend/app/knowledge_graph.py). Computed fresh on every
// GET /api/knowledge-graph call, the same "expensive-ish to compute,
// cheap to re-derive, never persisted" convention WhatIfSimulation
// already uses — not part of GameSaveState.
export type KnowledgeNodeType = "agent" | "branch" | "research" | "academy_project" | "executive_review" | "coach_report" | "hall_of_fame";
export type KnowledgeEdgeRelation = "researched" | "completed" | "has_branch" | "builds_on" | "featured_in" | "ranked_top_agent" | "achieved";

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

// v0.7 Feature 27 — the Library of Mistakes (see backend/app/mistakes.py).
// A permanent CaseStudy is filed whenever a closed, losing trade's own
// DisciplineReview shows a specific real process gap — never merely
// "the trade lost" on its own.
export type CaseStudyCategory = "overconfidence" | "incomplete_research" | "unchallenged_assumptions" | "acted_too_quickly" | "ignored_dissent" | "confirmation_bias";

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

export interface MentorState {
  tier: number;
  tierLabel: string;
  questionsAsked: number;
  updatedAt: string;
}

// v0.7 Feature 39 — the Original Founders (see backend/app/founders.py's
// module docstring for why this is deliberately not a second Socratic-
// teaching mechanic competing with MentorState above).
export type FounderId = "keystone" | "compass";

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
  gatekeeperRejections: GatekeeperRejection[];
  marketEnvironment: MarketEnvironmentState;
  companyHealth: CompanyHealth;
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
  agentEnergy: AgentEnergy;
  signalCalibration: SignalCalibrationState;
  playerVsAi: PlayerVsAiState;
  education: EducationProgress;
  viewedTradeNotificationIds: string[];
  time: TimeState;
  settings: SettingsState;
  dialogueHistory: DialogueHistoryEntry[];
  updatedAt: string;
}

export function isDaytime(time: TimeState): boolean {
  return time.hour >= 6 && time.hour < 20;
}
