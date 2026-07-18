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
  | "PerformanceCenterScene";

export type AgentId = "scout" | "atlas" | "echo" | "nova" | "scribe" | "coach";
export const AGENT_IDS: readonly AgentId[] = ["scout", "atlas", "echo", "nova", "scribe", "coach"];

/** Every room an agent's schedule (or a meeting/break override) can place them in. */
export type AgentLocation =
  | "scout-office"
  | "brain-room"
  | "meeting-room"
  | "break-room"
  | "lobby"
  | "simulation-lab"
  | "hall-of-fame"
  | "performance-center";

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
  | "analytics";
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
  | "paper_trade";

export type OrderSide = "buy" | "sell";
export type OrderStatus = "open" | "filled" | "closed";
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

/** A paper order — simulated only, never sent to a real brokerage. */
export interface PaperOrder {
  id: string;
  symbol: string;
  side: OrderSide;
  quantity: number;
  price: number;
  status: OrderStatus;
  placedBy: AgentId;
  reason: string;
  confidence: number;
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
  openedAt: string;
  closedAt: string;
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
  version: "0.5";
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
  time: TimeState;
  settings: SettingsState;
  dialogueHistory: DialogueHistoryEntry[];
  updatedAt: string;
}

export function isDaytime(time: TimeState): boolean {
  return time.hour >= 6 && time.hour < 20;
}
