"""Pydantic models mirroring frontend/src/types.ts. Field aliases keep the wire format camelCase to match the TypeScript client.

v0.2 generalized the single hardcoded "Scout" into a roster of agents
(AgentId / AgentState) driven by a shared NEXUS orchestrator — see
docs/Architecture.md "NEXUS & multi-agent model" for the full design.

v0.3 adds a fifth agent (Scribe, the company historian) and a research
layer on top: a Watchlist of symbols, a rotating ResearchItem queue,
meeting Discussions/Minutes, and a searchable CompanyMemory log. None of
this executes trades or calls a real market data API — see
docs/Architecture.md "Research & market intelligence (v0.3)" and
app/market_data.py for the mock-data boundary.

v0.5 adds a sixth agent (Coach, Performance & Improvement) and a full
paper-trading/learning layer: a PaperPortfolio (fake balance, positions,
orders, closed-trade history), a Simulation Lab (Strategy /
BacktestSession / SimulationResult), a Hall of Fame, a CompanyScore, and
periodic CoachReports / PerformanceSnapshots. Every trade in this system
is simulated — see app/paper_trading.py's module docstring for the exact
boundary. Nothing in v0.5 connects to a real brokerage.

v0.6 adds three more agents (Sentinel/Risk Management, Pulse/Market
Scanner, Guardian/Portfolio Protection) and turns v0.5's threshold-only
paper trading into a full order book: PaperOrder gains order types
(market/limit/stop/take_profit/stop_loss); every trade candidate is now
voted on by the relevant agents (AgentVote) before Atlas's DecisionEngine
approves or rejects it, producing a permanent, explainable TradeDecision
report; RiskLimits/RiskWarning back Sentinel's ability to reject a trade;
ScannerAlert is Pulse's continuous watchlist-scanning output. Still
entirely simulated — see app/broker.py's module docstring for the same
boundary restated for v0.6's order book.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Direction = Literal["up", "down", "left", "right"]
SceneId = Literal[
    "MainMenuScene",
    "LobbyScene",
    "ScoutOfficeScene",
    "CeoOfficeScene",
    "BrainRoomScene",
    "MeetingRoomScene",
    "BreakRoomScene",
    "SimulationLabScene",
    "HallOfFameScene",
    "PerformanceCenterScene",
    "TradingFloorScene",
    "MarketObservatoryScene",
]

AgentId = Literal["scout", "atlas", "echo", "nova", "scribe", "coach", "sentinel", "pulse", "guardian"]
AGENT_IDS: tuple[AgentId, ...] = ("scout", "atlas", "echo", "nova", "scribe", "coach", "sentinel", "pulse", "guardian")

# Every room an agent's schedule (or a meeting/break override) can place them in.
AgentLocation = Literal[
    "scout-office",
    "brain-room",
    "meeting-room",
    "break-room",
    "lobby",
    "simulation-lab",
    "hall-of-fame",
    "performance-center",
    "trading-floor",
]

TaskStatus = Literal["pending", "working", "completed", "failed"]
TaskPriority = Literal["low", "normal", "high"]
TaskCategory = Literal[
    "research",
    "review",
    "meeting",
    "watchlist_update",
    "news_scan",
    "chart_analysis",
    "documentation",
    "coaching",
    "simulation",
    "paper_trading",
    "analytics",
    "risk_management",
    "market_scanning",
    "voting",
    "trading",
]
NewsCategory = Literal["company", "discovery", "market"]

# The eight research topics named in the v0.3 brief. "stock"/"company" both
# exist because a research item can be about a specific ticker (stock) or
# about the company behind it (company) — kept distinct since the brief
# lists them separately, even though in practice most seed items use "stock".
ResearchCategory = Literal["stock", "etf", "index", "economy", "gold", "bitcoin", "company", "sector"]
ResearchStatus = Literal["queued", "in_progress", "completed"]
MemoryCategory = Literal[
    "research",
    "meeting",
    "whiteboard",
    "event",
    "discussion",
    "discovery",
    "future_trade",
    "lesson",
    "mistake",
    "strategy",
    "coach_review",
    "simulation",
    "paper_trade",
    "alert",
    "vote",
    "decision",
    "order",
]

# --- v0.5: paper trading, simulation, coaching, and scoring ---------------
OrderSide = Literal["buy", "sell"]
OrderStatus = Literal["open", "filled", "closed", "cancelled"]
SimulationStatus = Literal["queued", "running", "completed", "failed"]
HallOfFameCategory = Literal[
    "best_strategy",
    "best_simulation",
    "best_research",
    "top_agent",
    "best_month",
    "winning_streak",
    "lowest_drawdown",
    "highest_confidence_accuracy",
]
PerformancePeriod = Literal["daily", "weekly", "monthly", "all_time"]
ReportPeriod = Literal["weekly", "monthly"]

# --- v0.6: paper broker order book, risk, scanning, and voting ------------
OrderType = Literal["market", "limit", "stop", "take_profit", "stop_loss"]
AlertType = Literal["gap_up", "gap_down", "breakout", "volume_spike", "high_volatility"]
AlertSeverity = Literal["info", "warning", "critical"]
VoteChoice = Literal["buy", "sell", "hold", "risk_too_high", "position_too_large"]
DecisionOutcome = Literal["trade", "no_trade"]

# --- v0.6.2: market data abstraction ---------------------------------------
# What a caller should tell the player about a batch of candles. Never
# collapse this to a boolean or omit it — simulated/historical data must
# never be presented as live (v0.6.2 brief). The mock provider
# (app/market_data.py) only ever produces "simulated"; the rest of the
# literal exists so a future real provider can express itself through
# this exact same Candle shape without anything downstream changing.
DataStatus = Literal["live", "delayed", "historical", "simulated", "stale", "error", "no_data"]


class CamelModel(BaseModel):
    model_config = ConfigDict(populate_by_name=True)


class EntityTransform(CamelModel):
    scene: SceneId
    x: float
    y: float
    facing: Direction


class MemoryEntry(CamelModel):
    id: str
    summary: str
    day: int
    hour: int


class AgentOverride(CamelModel):
    """A temporary location override that takes precedence over an agent's
    normal schedule — how meetings and break-room visits are implemented,
    without needing separate meeting/break state machines per agent."""

    location: AgentLocation
    reason: Literal["meeting", "break"]
    remaining_minutes: int = Field(alias="remainingMinutes")


class AgentState(CamelModel):
    transform: EntityTransform
    location: AgentLocation
    current_task: str = Field(alias="currentTask")
    mood: float
    energy: float
    memory: list[MemoryEntry] = Field(default_factory=list)
    override: AgentOverride | None = None


class TimeState(CamelModel):
    day: int
    hour: int
    minute: int


class SettingsState(CamelModel):
    music_volume: float = Field(alias="musicVolume")
    sfx_volume: float = Field(alias="sfxVolume")
    autosave_interval_sec: int = Field(alias="autosaveIntervalSec")
    show_fps: bool = Field(alias="showFps")


class DialogueHistoryEntry(CamelModel):
    id: str
    speaker: AgentId | Literal["player"]
    line: str
    timestamp: str


class Task(CamelModel):
    id: str
    owner: AgentId
    category: TaskCategory
    priority: TaskPriority
    description: str
    status: TaskStatus
    created_at: str = Field(alias="createdAt")
    completed_at: str | None = Field(default=None, alias="completedAt")


class NewsItem(CamelModel):
    id: str
    headline: str
    category: NewsCategory
    timestamp: str


class DiscussionMessage(CamelModel):
    id: str
    speaker: AgentId
    line: str
    timestamp: str


class MeetingState(CamelModel):
    active: bool = False
    participants: list[AgentId] = Field(default_factory=list)
    # Generated once when the meeting starts (see app/discussion.py) and
    # carried through to meeting-end, where Scribe turns it into minutes
    # (app/scribe.py) — cleared back to [] once the meeting wraps up.
    discussion: list[DiscussionMessage] = Field(default_factory=list)


class ResearchItem(CamelModel):
    """One topic in the rotating research queue. Each of the four
    research-capable agents (everyone but Scribe) always has exactly one
    ResearchItem "in_progress" — see app/research.py — so the queue length
    stays bounded rather than growing per research event."""

    id: str
    title: str
    symbol: str | None = None
    category: ResearchCategory
    priority: TaskPriority
    status: ResearchStatus
    assigned_agent: AgentId = Field(alias="assignedAgent")
    summary: str
    confidence: float
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")


class WatchlistEntry(CamelModel):
    symbol: str
    name: str
    last_price: float = Field(alias="lastPrice")
    daily_change_pct: float = Field(alias="dailyChangePct")
    status: ResearchStatus
    research_progress: float = Field(alias="researchProgress")
    assigned_agent: AgentId | None = Field(default=None, alias="assignedAgent")


class Candle(CamelModel):
    """The wire shape of app/market_data.py's Candle dataclass — a
    plain API response model, never stored in GameSaveState (chart data
    is regenerable from the provider on demand, not game progress; see
    v0.6.2's save-payload-size fix for why nothing regenerable belongs
    in the save)."""

    symbol: str
    timeframe: str
    timestamp: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    data_status: DataStatus = Field(alias="dataStatus")


class AgentEnergy(CamelModel):
    """Player-spendable operational capacity (v0.6.2 Phase 6) — a company-
    wide pool the player earns (passive regen; the Signal Calibration
    mini-game in Phase 7 tops it up further) and spends to unlock deeper
    analysis actions. Deliberately NOT the same field as AgentState.energy
    (each agent's own fatigue/rest level, unrelated concept, unrelated
    number) — see app/agent_energy.py's docstring for the full "what does
    spending this actually do" mapping. Every action it unlocks has a
    real effect on real data (boosts a real ResearchItem's confidence,
    queues a real backtest, adds a real watchlist symbol) — never just a
    number going up for its own sake."""

    current: float
    cap: float
    updated_at: str = Field(alias="updatedAt")


class MeetingMinutes(CamelModel):
    id: str
    day: int
    hour: int
    minute: int
    participants: list[AgentId]
    summary: str
    discussion: list[DiscussionMessage] = Field(default_factory=list)


class MemoryRecord(CamelModel):
    """One entry in CompanyMemory — TradeTown's searchable long-term log.
    `category` is what a search/filter UI groups by; `body` is always
    plain, human-readable text (no structured payload) so the same simple
    list-and-filter viewer works for every category without per-category
    UI branches."""

    id: str
    category: MemoryCategory
    title: str
    body: str
    timestamp: str


class PaperOrder(CamelModel):
    """A paper order — simulated only, never sent to a real brokerage.
    See app/broker.py's module docstring for the enforcement boundary.

    `price` means different things per `order_type`: ignored (fills at
    the current quote) for "market"; the limit/target price for "limit"
    and "take_profit" (buy fills at-or-below, sell fills at-or-above);
    the trigger price for "stop" and "stop_loss" (buy fills at-or-above,
    sell fills at-or-below) — see app/broker.py's `_fill_price()`.
    `linked_position_id` is set for a "take_profit"/"stop_loss" order
    attached to an existing open position (an exit order); unset for an
    entry order that will open a new position once filled."""

    id: str
    symbol: str
    side: OrderSide
    order_type: OrderType = Field(default="market", alias="orderType")
    quantity: float
    price: float
    status: OrderStatus
    placed_by: AgentId = Field(alias="placedBy")
    reason: str
    confidence: float
    linked_position_id: str | None = Field(default=None, alias="linkedPositionId")
    filled_price: float | None = Field(default=None, alias="filledPrice")
    filled_at: str | None = Field(default=None, alias="filledAt")
    created_at: str = Field(alias="createdAt")


class PaperPosition(CamelModel):
    id: str
    symbol: str
    side: OrderSide
    quantity: float
    entry_price: float = Field(alias="entryPrice")
    current_price: float = Field(alias="currentPrice")
    unrealized_pnl: float = Field(alias="unrealizedPnl")
    unrealized_pnl_pct: float = Field(alias="unrealizedPnlPct")
    opened_by: AgentId = Field(alias="openedBy")
    confidence: float
    opened_at: str = Field(alias="openedAt")
    # Simulated-clock minutes-since-epoch (day*1440 + hour*60 + minute) at
    # open time — hold duration is tracked against TradeTown's in-game
    # clock, not real wall-clock time, the same way research confidence
    # advances by tick count rather than elapsed real time (see
    # app/research.py). `opened_at` above is still a real ISO timestamp,
    # kept only for audit/display, same as every other *_at field.
    # Defaults to 0 (not required) so a save from before this field existed
    # (pre-v0.6.1) still validates during load — see persistence.py's
    # migration path, which relies on every field added after the initial
    # release having a safe default.
    opened_sim_minutes: int = Field(default=0, alias="openedSimMinutes")


class PaperTrade(CamelModel):
    """One closed paper position — a fully realized round trip. This is
    the Learning System's "training data" record (see the v0.5 brief's
    Feature 5): everything Coach and app/knowledge.py need to derive a
    lesson from a completed trade lives on this one model, so nothing
    downstream needs a second, parallel "trade history" shape."""

    id: str
    symbol: str
    side: OrderSide
    quantity: float
    entry_price: float = Field(alias="entryPrice")
    exit_price: float = Field(alias="exitPrice")
    pnl: float
    pnl_pct: float = Field(alias="pnlPct")
    duration_minutes: int = Field(alias="durationMinutes")
    confidence: float
    reason: str
    market_conditions: str = Field(alias="marketConditions")
    supporting_agents: list[AgentId] = Field(default_factory=list, alias="supportingAgents")
    opposing_agents: list[AgentId] = Field(default_factory=list, alias="opposingAgents")
    coach_review: str | None = Field(default=None, alias="coachReview")
    lessons_learned: str | None = Field(default=None, alias="lessonsLearned")
    # v0.6 Trading Journal fields — see app/journal.py. `screenshot` is
    # always a fixed placeholder string, never a real captured image;
    # TradeTown has no chart-rendering pipeline to capture from.
    decision_id: str | None = Field(default=None, alias="decisionId")
    screenshot: str | None = None
    opened_at: str = Field(alias="openedAt")
    closed_at: str = Field(alias="closedAt")
    # Simulated-clock minutes-since-epoch (day*1440 + hour*60 + minute), the
    # same convention PaperPosition.opened_sim_minutes uses (see its own
    # comment above) — added in v0.6.1 so the Command Center's monthly P&L
    # view can bucket closed trades into TradeTown's in-game calendar
    # rather than real wall-clock time. `closed_sim_minutes` is always
    # `opened_sim_minutes + duration_minutes` (app/portfolio.py's
    # close_position() derives it exactly that way, no separate clock
    # read needed). `opened_at`/`closed_at` above remain real ISO
    # timestamps, kept only for audit/display, same as every other *_at
    # field — real time and sim time both exist on this record because
    # they answer different questions (when did this happen in the real
    # world vs. where does it fall on the game's own calendar).
    # Both default to 0 (not required) so a closed-trade record saved
    # before this field existed (pre-v0.6.1) still validates during load —
    # see persistence.py's migration path.
    opened_sim_minutes: int = Field(default=0, alias="openedSimMinutes")
    closed_sim_minutes: int = Field(default=0, alias="closedSimMinutes")


class PaperPortfolio(CamelModel):
    """The company's one simulated trading account. Starting balance and
    every position/order/trade in it are fictional — see
    app/portfolio.py."""

    cash_balance: float = Field(alias="cashBalance")
    starting_balance: float = Field(alias="startingBalance")
    positions: list[PaperPosition] = Field(default_factory=list)
    orders: list[PaperOrder] = Field(default_factory=list)
    trade_history: list[PaperTrade] = Field(default_factory=list, alias="tradeHistory")
    total_pnl: float = Field(alias="totalPnl")
    total_pnl_pct: float = Field(alias="totalPnlPct")
    win_count: int = Field(alias="winCount")
    loss_count: int = Field(alias="lossCount")


class Strategy(CamelModel):
    id: str
    name: str
    description: str
    created_by: AgentId = Field(alias="createdBy")
    focus_category: ResearchCategory = Field(alias="focusCategory")
    created_at: str = Field(alias="createdAt")


class BacktestSession(CamelModel):
    """A strategy simulation in flight — queued or actively running in
    the Simulation Lab. Moves into a SimulationResult once complete (see
    app/simulation.py's tick_simulation_lab())."""

    id: str
    strategy_id: str = Field(alias="strategyId")
    strategy_name: str = Field(alias="strategyName")
    symbol: str
    status: SimulationStatus
    progress: float
    run_by: AgentId = Field(alias="runBy")
    queued_at: str = Field(alias="queuedAt")
    started_at: str | None = Field(default=None, alias="startedAt")


class SimulationResult(CamelModel):
    """sharpe_ratio/sortino_ratio are explicitly placeholder formulas
    (see app/simulation.py) — real risk-adjusted-return math needs a
    real historical data source, which v0.5 does not have (see
    app/market_data.py)."""

    id: str
    strategy_id: str = Field(alias="strategyId")
    strategy_name: str = Field(alias="strategyName")
    symbol: str
    total_return_pct: float = Field(alias="totalReturnPct")
    win_rate: float = Field(alias="winRate")
    max_drawdown_pct: float = Field(alias="maxDrawdownPct")
    sharpe_ratio: float = Field(alias="sharpeRatio")
    sortino_ratio: float = Field(alias="sortinoRatio")
    trade_count: int = Field(alias="tradeCount")
    run_by: AgentId = Field(alias="runBy")
    completed_at: str = Field(alias="completedAt")


class HallOfFameEntry(CamelModel):
    id: str
    category: HallOfFameCategory
    title: str
    description: str
    agent_id: AgentId | None = Field(default=None, alias="agentId")
    value: float
    achieved_at: str = Field(alias="achievedAt")


class AgentScore(CamelModel):
    """One agent's row in Coach's rankings (v0.5 brief, Feature 1)."""

    agent_id: AgentId = Field(alias="agentId")
    score: float
    research_accuracy: float = Field(alias="researchAccuracy")
    confidence_calibration: float = Field(alias="confidenceCalibration")


class CoachReport(CamelModel):
    id: str
    period: ReportPeriod
    company_score: float = Field(alias="companyScore")
    agent_rankings: list[AgentScore] = Field(default_factory=list, alias="agentRankings")
    research_accuracy: float = Field(alias="researchAccuracy")
    win_rate: float = Field(alias="winRate")
    loss_rate: float = Field(alias="lossRate")
    average_confidence: float = Field(alias="averageConfidence")
    risk_score: float = Field(alias="riskScore")
    common_mistakes: list[str] = Field(default_factory=list, alias="commonMistakes")
    recommendations: list[str] = Field(default_factory=list)
    created_at: str = Field(alias="createdAt")


class CompanyScore(CamelModel):
    """The seven-metric company rating shown in the Brain Room (v0.5
    brief, Feature 6). `overall` is a simple mean of the other six —
    see app/company_score.py for the exact, documented formula."""

    overall: float
    research_quality: float = Field(alias="researchQuality")
    decision_quality: float = Field(alias="decisionQuality")
    risk_management: float = Field(alias="riskManagement")
    paper_trading_performance: float = Field(alias="paperTradingPerformance")
    team_coordination: float = Field(alias="teamCoordination")
    knowledge_growth: float = Field(alias="knowledgeGrowth")
    simulation_success: float = Field(alias="simulationSuccess")
    updated_at: str = Field(alias="updatedAt")


class PerformanceSnapshot(CamelModel):
    period: PerformancePeriod
    return_pct: float = Field(alias="returnPct")
    win_rate: float = Field(alias="winRate")
    max_drawdown_pct: float = Field(alias="maxDrawdownPct")
    sharpe_ratio: float = Field(alias="sharpeRatio")
    sortino_ratio: float = Field(alias="sortinoRatio")
    avg_holding_minutes: float = Field(alias="avgHoldingMinutes")
    research_accuracy: float = Field(alias="researchAccuracy")
    confidence_accuracy: float = Field(alias="confidenceAccuracy")
    computed_at: str = Field(alias="computedAt")


class RiskLimits(CamelModel):
    """Sentinel's configurable risk boundaries (v0.6 brief, Risk Engine).
    Defaults are conservative but arbitrary — there's no real capital or
    regulatory requirement behind them, they exist purely to give Sentinel
    something concrete to check a trade candidate against."""

    max_position_pct: float = Field(default=10.0, alias="maxPositionPct")
    max_daily_loss_pct: float = Field(default=5.0, alias="maxDailyLossPct")
    max_drawdown_pct: float = Field(default=20.0, alias="maxDrawdownPct")
    max_open_positions: int = Field(default=8, alias="maxOpenPositions")
    max_sector_concentration_pct: float = Field(default=30.0, alias="maxSectorConcentrationPct")
    risk_per_trade_pct: float = Field(default=2.0, alias="riskPerTradePct")


class RiskWarning(CamelModel):
    id: str
    symbol: str
    severity: AlertSeverity
    message: str
    created_at: str = Field(alias="createdAt")


class ScannerAlert(CamelModel):
    """Pulse's output — see app/scanner.py. `detected_by` is always
    "pulse" today; the field exists so a future version could let other
    agents flag alerts too without a schema change."""

    id: str
    symbol: str
    alert_type: AlertType = Field(alias="alertType")
    message: str
    detected_by: AgentId = Field(alias="detectedBy")
    created_at: str = Field(alias="createdAt")


class AgentVote(CamelModel):
    """One agent's stance on a trade candidate — see app/voting.py."""

    agent_id: AgentId = Field(alias="agentId")
    choice: VoteChoice
    reason: str


class TradeDecision(CamelModel):
    """The permanent, explainable-AI record of one trade candidate's
    outcome (v0.6 brief, Decision Voting + Explainable AI) — see
    app/decision.py. Stored forever (capped, like every other list here)
    so a past "why did/didn't we trade this" question always has an
    answer."""

    id: str
    symbol: str
    outcome: DecisionOutcome
    votes: list[AgentVote] = Field(default_factory=list)
    research_summary: str = Field(alias="researchSummary")
    technical_summary: str = Field(alias="technicalSummary")
    fundamental_summary: str = Field(alias="fundamentalSummary")
    risk_summary: str = Field(alias="riskSummary")
    supporting_agents: list[AgentId] = Field(default_factory=list, alias="supportingAgents")
    opposing_agents: list[AgentId] = Field(default_factory=list, alias="opposingAgents")
    confidence: float
    final_reasoning: str = Field(alias="finalReasoning")
    order_id: str | None = Field(default=None, alias="orderId")
    created_at: str = Field(alias="createdAt")


class GameSaveState(CamelModel):
    version: Literal["0.6"] = "0.6"
    player: EntityTransform
    agents: dict[AgentId, AgentState]
    tasks: list[Task] = Field(default_factory=list)
    whiteboards: dict[str, str] = Field(default_factory=dict)
    meeting: MeetingState = Field(default_factory=MeetingState)
    news: list[NewsItem] = Field(default_factory=list)
    research: list[ResearchItem] = Field(default_factory=list)
    watchlist: list[WatchlistEntry] = Field(default_factory=list)
    memory: list[MemoryRecord] = Field(default_factory=list)
    meeting_minutes: list[MeetingMinutes] = Field(default_factory=list, alias="meetingMinutes")
    paper_portfolio: PaperPortfolio = Field(alias="paperPortfolio")
    strategies: list[Strategy] = Field(default_factory=list)
    backtest_sessions: list[BacktestSession] = Field(default_factory=list, alias="backtestSessions")
    simulation_results: list[SimulationResult] = Field(default_factory=list, alias="simulationResults")
    hall_of_fame: list[HallOfFameEntry] = Field(default_factory=list, alias="hallOfFame")
    coach_reports: list[CoachReport] = Field(default_factory=list, alias="coachReports")
    company_score: CompanyScore = Field(alias="companyScore")
    performance_snapshots: list[PerformanceSnapshot] = Field(default_factory=list, alias="performanceSnapshots")
    risk_limits: RiskLimits = Field(default_factory=RiskLimits, alias="riskLimits")
    risk_warnings: list[RiskWarning] = Field(default_factory=list, alias="riskWarnings")
    scanner_alerts: list[ScannerAlert] = Field(default_factory=list, alias="scannerAlerts")
    decisions: list[TradeDecision] = Field(default_factory=list)
    agent_energy: AgentEnergy = Field(alias="agentEnergy")
    time: TimeState
    settings: SettingsState
    dialogue_history: list[DialogueHistoryEntry] = Field(default_factory=list, alias="dialogueHistory")
    updated_at: str = Field(alias="updatedAt")


class SaveResponse(BaseModel):
    ok: Literal[True] = True
    updated_at: str = Field(alias="updatedAt", serialization_alias="updatedAt")

    model_config = ConfigDict(populate_by_name=True)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
