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
  | "MarketObservatoryScene";

export type AgentId = "scout" | "atlas" | "echo" | "nova" | "scribe" | "coach" | "sentinel" | "pulse" | "guardian";
export const AGENT_IDS: readonly AgentId[] = ["scout", "atlas", "echo", "nova", "scribe", "coach", "sentinel", "pulse", "guardian"];

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
  | "trading-floor";

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
  | "order";

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
  createdAt: string;
  resolvedAt: string | null;
}

export interface TimeState {
  day: number;
  hour: number; // 0-23
  minute: number; // 0-59
}

export interface SettingsState {
  musicVolume: number; // 0-1
  sfxVolume: number; // 0-1
  autosaveIntervalSec: number;
  showFps: boolean;
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
