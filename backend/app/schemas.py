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
    "ExecutiveBoardroomScene",
]

# v0.7 Feature 24 — Meridian, the Chief Investment Officer, is the tenth
# agent. Unlike every other agent, the CIO never votes on a trade or
# generates a research signal (see app/executive.py) — it only reviews
# already-real state (see app/executive_review.py).
# v0.7 Feature 32 — Sage, the Socratic Mentor, is the eleventh agent. Like
# the CIO, Sage never trades, votes, or generates a signal — it only asks
# questions (see app/mentor.py).
# v0.7 Feature 39 — "keystone"/"compass" are the two Original Founders
# (app/founders.py). Added as real AgentIds the same proven way "cio"/
# "sage" were (Features 24/32): they get a real schedule, mood/energy,
# and campus presence, and simply never route through a trading task —
# never a second, parallel character system.
# v0.7 — "quant" is the Chief Quantitative Strategist, the fourteenth
# agent (app/black_box.py). Leads every Black Box Research Project and
# works out of the Simulation Lab — no new physical scene was built for
# a "Quant Lab"; that room is real content layered onto the existing
# backtesting room (see black_box.py's module docstring for the full
# list of what this feature extends rather than duplicates).
AgentId = Literal["scout", "atlas", "echo", "nova", "scribe", "coach", "sentinel", "pulse", "guardian", "cio", "sage", "keystone", "compass", "quant"]
AGENT_IDS: tuple[AgentId, ...] = ("scout", "atlas", "echo", "nova", "scribe", "coach", "sentinel", "pulse", "guardian", "cio", "sage", "keystone", "compass", "quant")

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
    "executive-boardroom",
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
    # v0.7 Feature 25 — a completed Academy knowledge project or a
    # knowledge-tier advancement (app/academy.py, app/academy_research.py).
    "academy",
    # v0.7 Feature 25 — a real mentorship session between two agents (see
    # app/academy.py's module docstring for why "seniority" here is
    # grounded in real knowledge points, not a fabricated status).
    "mentorship",
    # v0.7 Feature 24 — the CIO's own Monthly Executive Review (see
    # app/executive_review.py) — distinct from "coach_review" so it's
    # never misattributed to Coach.
    "executive",
    # v0.7 Feature 26 — a Discipline Chamber review of one closed trade's
    # decision process (see app/discipline.py).
    "discipline",
    # v0.7 Feature 27 — a Library of Mistakes case study (see
    # app/mistakes.py).
    "case_study",
    # v0.7 Feature 29 — a completed Reasoning Lab challenge (see
    # app/reasoning_lab.py).
    "reasoning_challenge",
    # v0.7 Feature 30 — a weekly/monthly Reflection Session (see
    # app/wisdom.py).
    "reflection",
]

# --- v0.5: paper trading, simulation, coaching, and scoring ---------------
OrderSide = Literal["buy", "sell"]
OrderStatus = Literal["open", "filled", "closed", "cancelled"]
SimulationStatus = Literal["queued", "running", "completed", "failed"]

# v0.7 Feature 45 — the Research Sandbox. Reuses the exact same 5 regime
# names market_environment.py already computes live (bull/bear/sideways/
# high_volatility/low_volatility) as backtest scenario presets, plus
# "historical" (the pre-Feature-45 default/neutral run) and "custom" (a
# CEO-tunable bias — see app/sandbox.py). "Earnings weeks" and "economic
# news" from the brief's longer example list are deliberately not
# included: no earnings calendar or economic-event data source exists
# anywhere in this codebase (see app/calendar.py's own real/cut boundary)
# — see app/sandbox.py's module docstring.
TestScenario = Literal["historical", "bull", "bear", "sideways", "high_volatility", "low_volatility", "custom"]

# v0.7 Feature 45 — the Research Sandbox pipeline. Strategies cannot skip
# stages (see app/sandbox.py); each transition requires a real, checkable
# gate to clear.
StrategyStage = Literal[
    "idea",
    "research",
    "historical_backtest",
    "market_simulation",
    "paper_trading",
    "limited_live_capital",
    "company_review",
    "approved",
]
HallOfFameCategory = Literal[
    "best_strategy",
    "best_simulation",
    "best_research",
    "top_agent",
    "best_month",
    "winning_streak",
    "lowest_drawdown",
    "highest_confidence_accuracy",
    # v0.7 — Museum of Discoveries. Extends the Hall of Fame's own
    # "permanent, never-evicted record" mechanism (see hall_of_fame.py's
    # module docstring) rather than building a second, parallel
    # permanent-record system; only HallOfFameEntry.discovery_timeline/
    # supporting_evidence/company_impact are ever populated for this
    # category (see app/black_box.py).
    "breakthrough",
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


# v0.7 Feature 21 — Company Operating Modes.
#   learning  — every proposal waits for the CEO (the pre-Feature-21
#               default behavior, unchanged).
#   assisted  — routine (non-significant) proposals auto-resolve using
#               the desk's own real recommendation; only a "significant"
#               one (see app/executive.py's is_significant_proposal)
#               still surfaces to the player.
#   executive — every proposal auto-resolves; the player reviews reports
#               (Decisions/Company Health) rather than individual trades.
OperatingMode = Literal["learning", "assisted", "executive"]

# v0.7 Feature 34 — Company Priorities. "Balanced" is the neutral default
# (unchanged behavior); the other three each bias exactly one real,
# already-existing lever — see nexus.py's tick() for where each is
# actually applied. "Expansion," "Efficiency," and "Innovation" (also
# named in the brief) have no real, distinct lever anywhere in this
# codebase to attach to — biasing them would mean either faking a new
# system or silently reusing another priority's real effect under a
# different label, so they're not offered.
CompanyPriority = Literal["balanced", "learning", "research", "risk_reduction"]

# v0.7 Feature 34 — CEO time controls. "hours" advances a bounded custom
# number of real hours; the other three jump to the next occurrence of an
# already-real cadence boundary nexus.py's own tick() already checks for
# (see app/state.py's GameState.advance_time()).
TimeAdvanceTarget = Literal["workday_end", "week_end", "month_end", "hours"]

# v0.7 Feature 37 — the Work Mode System. "work" (the default — unchanged
# behavior from every prior version) is indefinite, continuous operation;
# "rest" is the CEO-triggered wind-down — see nexus.py's tick() for
# exactly which real systems each mode gates. Persistent until the CEO
# changes it, never an automatic timer.
WorkMode = Literal["work", "rest"]


class SettingsState(CamelModel):
    music_volume: float = Field(alias="musicVolume")
    sfx_volume: float = Field(alias="sfxVolume")
    autosave_interval_sec: int = Field(alias="autosaveIntervalSec")
    show_fps: bool = Field(alias="showFps")
    # Client-authoritative (the player's own preference, same as every
    # other field on this model), merged into server state via
    # apply_client_save the same way showFps/musicVolume already are.
    operating_mode: OperatingMode = Field(default="learning", alias="operatingMode")
    # v0.7 Feature 34 — same client-authoritative mechanism as
    # operating_mode above.
    company_priority: CompanyPriority = Field(default="balanced", alias="companyPriority")
    # v0.7 Feature 37 — same client-authoritative mechanism as
    # operating_mode/company_priority above.
    work_mode: WorkMode = Field(default="work", alias="workMode")


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


SignalChoice = Literal["enter", "wait", "avoid"]


class SignalChallenge(CamelModel):
    """A generated Signal Calibration round (v0.6.2 Phase 7) — see
    app/signal_calibration.py. Never part of GameSaveState: it's
    regenerable practice content built fresh from real live candles/risk/
    research data, not game progress. Held server-side in an in-memory
    pending-challenge store between GET .../challenge and POST .../submit
    (the same "transient, not save data" treatment market_data.py's
    candles already get), not persisted or broadcast over the WS."""

    id: str
    level: int
    symbol: str
    timeframe: str
    candles: list[Candle]
    prompt: str
    # Plain-English readouts of the real signals this level reveals (e.g.
    # "Recent trend: +2.3% over the sample", "Active HIGH risk warning on
    # AAPL") — never an invented feed; see _factors() in
    # signal_calibration.py for exactly what backs each line.
    factors: list[str]
    created_at: str = Field(alias="createdAt")


class SignalCalibrationAttempt(CamelModel):
    """One graded Signal Calibration round. `correct_choice` is a
    deterministic function of the real trend/volatility/risk/research
    signals available at challenge time (see
    signal_calibration._disciplined_choice) — never of what price did
    next — so grading rewards reading the same information a real trader
    had, not predicting the future."""

    id: str
    level: int
    symbol: str
    choice: SignalChoice
    correct_choice: SignalChoice = Field(alias="correctChoice")
    correct: bool
    energy_awarded: float = Field(alias="energyAwarded")
    rubric_notes: str = Field(alias="rubricNotes")
    created_at: str = Field(alias="createdAt")


class SignalCalibrationState(CamelModel):
    """Persisted Signal Calibration progress — real progression, unlike
    the SignalChallenge itself. `unlocked_level` only advances after a
    streak of correct answers at the current level (see
    signal_calibration.UNLOCK_STREAK), so it can't be inflated by
    grinding easy attempts at a level already mastered."""

    unlocked_level: int = Field(default=1, alias="unlockedLevel")
    attempts: list[SignalCalibrationAttempt] = Field(default_factory=list)
    correct_count: int = Field(default=0, alias="correctCount")
    total_count: int = Field(default=0, alias="totalCount")


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


class StrategyStageEvent(CamelModel):
    """One real transition in a Strategy's Research Sandbox pipeline —
    see app/sandbox.py's module docstring for exactly what gates each
    stage."""

    id: str
    stage: StrategyStage
    detail: str
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


class Strategy(CamelModel):
    id: str
    name: str
    description: str
    created_by: AgentId = Field(alias="createdBy")
    focus_category: ResearchCategory = Field(alias="focusCategory")
    created_at: str = Field(alias="createdAt")
    # v0.7 Feature 45 — the Research Sandbox. Every Strategy starts as an
    # "idea" and only ever advances forward through stage_history's real,
    # gated transitions — see app/sandbox.py.
    stage: StrategyStage = "idea"
    stage_history: list[StrategyStageEvent] = Field(default_factory=list, alias="stageHistory")
    # A real, CEO-chosen authorization ceiling set on entering
    # limited_live_capital (POST /api/sandbox/begin-limited-live) — see
    # app/sandbox.py's module docstring for why this is a tracked
    # commitment number, not fabricated live P&L attribution.
    allocated_capital: float = Field(default=0.0, alias="allocatedCapital")


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
    # v0.7 Feature 45 — which Testing Environment this run exercises the
    # strategy against. Defaults to "historical" so every pre-Feature-45
    # (and every still-automatic per-tick) session keeps its old meaning.
    scenario: TestScenario = "historical"
    # Only meaningful when scenario == "custom" — the CEO's own real,
    # chosen bias numbers (POST /api/sandbox/backtest), applied
    # deterministically to the placeholder engine's win/loss ranges (see
    # app/simulation.py's _scenario_ranges()). 0.0/1.0 are neutral
    # defaults matching "historical" until the CEO picks something else.
    custom_return_bias_pct: float = Field(default=0.0, alias="customReturnBiasPct")
    custom_volatility_bias: float = Field(default=1.0, alias="customVolatilityBias")


class SimulationResult(CamelModel):
    """sharpe_ratio/sortino_ratio are explicitly placeholder formulas
    (see app/simulation.py) — real risk-adjusted-return math needs a
    real historical data source, which v0.5 does not have (see
    app/market_data.py). v0.7 Feature 45 adds win_count/loss_count/
    avg_win_pct/avg_loss_pct as the placeholder engine's own real
    generating inputs (total_return_pct is now derived FROM them, not
    the reverse — see app/simulation.py), so expected_value_pct/
    profit_factor/risk_reward_ratio below are real, internally-consistent
    derivations of this run's own numbers, never independently invented."""

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
    # v0.7 Feature 45 — the Research Sandbox's fuller metrics set.
    scenario: TestScenario = "historical"
    win_count: int = Field(default=0, alias="winCount")
    loss_count: int = Field(default=0, alias="lossCount")
    avg_win_pct: float = Field(default=0.0, alias="avgWinPct")
    avg_loss_pct: float = Field(default=0.0, alias="avgLossPct")
    expected_value_pct: float = Field(default=0.0, alias="expectedValuePct")
    profit_factor: float = Field(default=0.0, alias="profitFactor")
    risk_reward_ratio: float = Field(default=0.0, alias="riskRewardRatio")


# v0.7 Feature 45 — auto-generated whenever a SimulationResult completes
# (see app/sandbox.py's generate_strategy_report), the same templated-
# framing-over-real-numbers discipline as app/mistakes.py/successes.py.
class StrategyReport(CamelModel):
    id: str
    strategy_id: str = Field(alias="strategyId")
    strategy_name: str = Field(alias="strategyName")
    source_result_id: str = Field(alias="sourceResultId")
    scenario: TestScenario
    executive_summary: str = Field(alias="executiveSummary")
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)
    failure_conditions: list[str] = Field(default_factory=list, alias="failureConditions")
    best_market_environment: str = Field(alias="bestMarketEnvironment")
    recommended_improvements: list[str] = Field(default_factory=list, alias="recommendedImprovements")
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


# v0.7 Feature 45 — the Company Review stage's five real reviewer
# verdicts (Quant/Risk Specialist/Technical Analyst/Fundamental Analyst/
# Devil's Advocate), each computed from that strategy's own real,
# aggregated SimulationResult and ResearchItem history — see
# app/sandbox.py's generate_strategy_review().
StrategyReviewerRole = Literal["quant", "risk", "technical", "fundamental", "devils_advocate"]
StrategyVerdict = Literal["pass", "concern", "fail"]


class StrategyReviewVerdict(CamelModel):
    reviewer_role: StrategyReviewerRole = Field(alias="reviewerRole")
    reviewer_agent: AgentId = Field(alias="reviewerAgent")
    verdict: StrategyVerdict
    summary: str


class StrategyReview(CamelModel):
    id: str
    strategy_id: str = Field(alias="strategyId")
    strategy_name: str = Field(alias="strategyName")
    verdicts: list[StrategyReviewVerdict]
    overall_verdict: StrategyVerdict = Field(alias="overallVerdict")
    ceo_decision: Literal["pending", "approved", "rejected"] = Field(default="pending", alias="ceoDecision")
    resolved_by: Literal["ceo", "auto"] | None = Field(default=None, alias="resolvedBy")
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


class HallOfFameEntry(CamelModel):
    id: str
    category: HallOfFameCategory
    title: str
    description: str
    agent_id: AgentId | None = Field(default=None, alias="agentId")
    value: float
    achieved_at: str = Field(alias="achievedAt")
    # v0.7 — Museum of Discoveries. Only ever populated for
    # category="breakthrough" (see app/black_box.py); every other
    # category leaves these at their honest empty default, since a
    # best-metric leaderboard entry has no real timeline/evidence/impact
    # to show.
    discovery_timeline: str | None = Field(default=None, alias="discoveryTimeline")
    supporting_evidence: list[str] = Field(default_factory=list, alias="supportingEvidence")
    company_impact: str | None = Field(default=None, alias="companyImpact")


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
    # v0.7 Feature 18 — the positive counterpart to common_mistakes, same
    # "real counted pattern, never filler" rule (see coach.py's _strengths).
    strengths: list[str] = Field(default_factory=list)
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
    outcome (v0.6 brief, Decision Voting + Explainable AI; resolved by
    the CEO since v0.6.3 — see app/executive.py). Stored forever
    (capped, like every other list here) so a past "why did/didn't we
    trade this" question always has an answer."""

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
    # v0.7 Feature 15 — the real Decision Confidence Engine reading at
    # the moment this decision was made, carried over from the
    # TradeProposal that produced it (see app/executive.py's
    # resolve_proposal) so Post-Trade Review can compare it against the
    # trade's real realized outcome even after the proposal itself is
    # gone. None only for decisions predating this field.
    confidence_engine: "DecisionConfidence | None" = Field(default=None, alias="confidenceEngine")
    # v0.7 Feature 20 — the Trade Gatekeeper's final-approval verdict
    # (see app/gatekeeper.py). Only ever set when the CEO chose buy/sell
    # (a WAIT never reaches the gatekeeper); None for decisions predating
    # this field. A rejected verdict here is exactly what makes
    # `order_id` None even though `ceo_choice` on the linked
    # CeoDecisionRecord was buy/sell, not wait.
    gatekeeper_verdict: "GatekeeperVerdict | None" = Field(default=None, alias="gatekeeperVerdict")
    created_at: str = Field(alias="createdAt")


# v0.6.2 Phase 8: Player vs AI. "regime" reuses the same trend/volatility
# read as Signal Calibration's level 3 (see market_data.trend_pct/
# volatility_pct) — a real, already-tested computation, not an invented
# second taxonomy. Only decisions that led to a trade with a real,
# already-closed outcome are eligible (see app/player_vs_ai.py) — that
# keeps grading unambiguous and honest, never assuming what an
# unrealized or never-placed trade "would have" done.
MarketRegime = Literal["trending_up", "trending_down", "ranging"]


class PlayerVsAiPrompt(CamelModel):
    """A pending Player vs AI round, shown before the AI's real call is
    revealed. Deliberately omits `votes`/`outcome`/`finalReasoning`/
    `orderId` from the underlying TradeDecision — including any of those
    would spoil the AI's actual answer. Includes only the same research/
    technical/risk summaries and confidence a human analyst would have
    had available before deciding. Never part of GameSaveState — see
    player_vs_ai.py's module docstring."""

    id: str
    decision_id: str = Field(alias="decisionId")
    symbol: str
    category: ResearchCategory
    research_summary: str = Field(alias="researchSummary")
    technical_summary: str = Field(alias="technicalSummary")
    risk_summary: str = Field(alias="riskSummary")
    confidence: float
    regime: MarketRegime
    created_at: str = Field(alias="createdAt")


class PlayerVsAiRound(CamelModel):
    """One graded round. `ai_choice` is always "enter" today — only
    decisions that led to a trade are eligible (see player_vs_ai.py) — the
    field stays generic for when "no_trade" decisions become gradeable
    too. `ground_truth_choice`/`ai_correct` are both derived from the
    linked trade's real realized P&L, never a guess about what an
    unrealized position might have done."""

    id: str
    decision_id: str = Field(alias="decisionId")
    symbol: str
    category: ResearchCategory
    regime: MarketRegime
    player_choice: SignalChoice = Field(alias="playerChoice")
    ai_choice: SignalChoice = Field(alias="aiChoice")
    realized_pnl_pct: float = Field(alias="realizedPnlPct")
    ground_truth_choice: SignalChoice = Field(alias="groundTruthChoice")
    player_correct: bool = Field(alias="playerCorrect")
    ai_correct: bool = Field(alias="aiCorrect")
    created_at: str = Field(alias="createdAt")


class PlayerVsAiState(CamelModel):
    rounds: list[PlayerVsAiRound] = Field(default_factory=list)
    player_correct_count: int = Field(default=0, alias="playerCorrectCount")
    ai_correct_count: int = Field(default=0, alias="aiCorrectCount")
    total_count: int = Field(default=0, alias="totalCount")


# v0.6.2 Phase 9: Trading Education. Ten topics, ordered as a real
# learning progression per the brief — see app/education.py for the
# actual curriculum text and quiz answer keys. `quiz_options` is the
# public shape (no answer key); grading happens server-side.
EducationTopic = Literal[
    "candlesticks",
    "wicks",
    "trends",
    "support_resistance",
    "enter_wait_avoid",
    "stop_loss",
    "take_profit",
    "risk_reward",
    "position_sizing",
    "no_trade_ok",
]


class EducationLesson(CamelModel):
    """One lesson's public content — what GET /api/education/lessons
    returns. Deliberately excludes the quiz's correct-answer index;
    grading happens server-side via POST /api/education/quiz so the
    answer never ships to the client."""

    id: EducationTopic
    order: int
    title: str
    simple_explanation: str = Field(alias="simpleExplanation")
    visual_example_note: str = Field(alias="visualExampleNote")
    deeper_explanation: str = Field(alias="deeperExplanation")
    quiz_question: str = Field(alias="quizQuestion")
    quiz_options: list[str] = Field(alias="quizOptions")


class EducationProgress(CamelModel):
    """Persisted — real progress through the curriculum, distinct from
    the lesson content itself (which is static and never part of the
    save; see education.py)."""

    viewed_lesson_ids: list[str] = Field(default_factory=list, alias="viewedLessonIds")
    completed_lesson_ids: list[str] = Field(default_factory=list, alias="completedLessonIds")
    quiz_attempts: int = Field(default=0, alias="quizAttempts")
    correct_quiz_attempts: int = Field(default=0, alias="correctQuizAttempts")


# Feature 12 — Executive Voting System (CEO Approval). Every research
# candidate that crosses the trade-confidence threshold now becomes a
# TradeProposal awaiting the player's (the CEO's) decision, instead of
# executing automatically. The six analyst seats are real existing
# TradeTown agents, never invented characters — see
# app/executive.py's ROLE_TO_AGENT for the mapping (technical=Echo,
# news=Scout, macro=Nova, risk=Sentinel, sentiment=Pulse, execution=Atlas).
AnalystRole = Literal["technical", "news", "macro", "risk", "sentiment", "execution"]
# Deliberately distinct from the existing VoteChoice (buy/sell/hold/...)
# used by TradeDecision/AgentVote — "wait" is the CEO-facing vocabulary
# this feature uses end to end; app/executive.py maps between the two at
# the one boundary where a CEO decision becomes a permanent TradeDecision.
AnalystChoice = Literal["buy", "sell", "wait"]

# v0.7 Feature 40.5 — the Expert Consultation System's two real CEO
# actions beyond buy/sell/wait. Both do the same real thing (reset the
# proposal's own expiry clock — see app/executive.py's hold_proposal());
# the reason is kept distinct only for honest logging, never a different
# mechanism under the hood.
HoldReason = Literal["more_research", "delay"]


class AnalystVote(CamelModel):
    """One analyst's independent stance on a trade proposal, with real
    supporting evidence — never a bare choice with no backing. See
    app/executive.py for exactly what data backs each role's vote."""

    role: AnalystRole
    agent_id: AgentId = Field(alias="agentId")
    choice: AnalystChoice
    reasoning: str
    evidence: list[str] = Field(default_factory=list)


# v0.7 Feature 15 — Decision Confidence Engine. Never a prediction of
# outcome, only a measure of the current setup's evidence quality (see
# app/confidence.py's module docstring for exactly which factors are
# real and which named in the v0.7 brief have no real data source and
# are deliberately not computed).
ConfidenceTier = Literal["elite", "strong", "good", "moderate", "weak", "poor"]


class ConfidenceFactor(CamelModel):
    name: str
    score: float  # 0-100, this factor's own reading
    weight: float  # 0-1, this factor's share of the total score
    detail: str


class DecisionConfidence(CamelModel):
    score: float  # 0-100, weighted sum of factors
    tier: ConfidenceTier
    summary: str
    factors: list[ConfidenceFactor] = Field(default_factory=list)


class TradeProposal(CamelModel):
    """A trade candidate awaiting the CEO's decision — real, persisted
    game progress (not regenerable practice content), since losing a
    pending proposal on restart would be losing an actual unresolved
    business decision. Removed from the pending list the moment the CEO
    decides (see app/executive.py's resolve_proposal); the resulting
    TradeDecision is the permanent record of what happened."""

    id: str
    symbol: str
    category: ResearchCategory
    quantity: float
    price: float
    confidence: float
    analyst_votes: list[AnalystVote] = Field(alias="analystVotes")
    overall_recommendation: AnalystChoice = Field(alias="overallRecommendation")
    research_summary: str = Field(alias="researchSummary")
    risk_summary: str = Field(alias="riskSummary")
    confidence_engine: DecisionConfidence = Field(alias="confidenceEngine")
    created_at: str = Field(alias="createdAt")
    # Simulated-clock minutes-since-epoch at creation, the same
    # convention PaperPosition.opened_sim_minutes uses — lets stale
    # proposals expire against TradeTown's in-game calendar rather than
    # real wall-clock time (see app/executive.py's expire_stale_proposals).
    created_sim_minutes: int = Field(alias="createdSimMinutes")
    # v0.7 Feature 40.5 — how many times the CEO has held this proposal
    # (Request More Research / Delay Decision) instead of deciding.
    # Capped by app/executive.py's MAX_PROPOSAL_HOLDS so a proposal can't
    # be deferred forever.
    hold_count: int = Field(default=0, alias="holdCount")


# v0.7 Feature 17 — AI Debate Room. Every turn's substance is a real
# AnalystVote's own reasoning/evidence (see app/debate.py); only the
# opening/challenge/support framing is generated, never the underlying
# claim.
DebateStance = Literal["opening", "challenge", "support"]


class DebateTurn(CamelModel):
    agent_id: AgentId = Field(alias="agentId")
    role: AnalystRole
    stance: DebateStance
    # None for an opening statement; another participant's agentId for a
    # challenge/support turn.
    responding_to: AgentId | None = Field(default=None, alias="respondingTo")
    text: str


class Debate(CamelModel):
    """One full committee review of a TradeProposal — stored permanently
    (capped, like every other list here) so a past debate is always
    reviewable even after its proposal is long resolved. `proposalId`
    links back to the TradeProposal it reviewed; the debate itself never
    approves or rejects anything — that's still the CEO's real
    buy/sell/wait call via app/executive.py's resolve_proposal, subject
    to the Trade Gatekeeper's final approval (v0.7 Feature 20)."""

    id: str
    proposal_id: str = Field(alias="proposalId")
    symbol: str
    turns: list[DebateTurn] = Field(default_factory=list)
    final_recommendation: AnalystChoice = Field(alias="finalRecommendation")
    final_summary: str = Field(alias="finalSummary")
    created_at: str = Field(alias="createdAt")


# v0.7 Feature 41 — the Intelligent Devil's Advocate System. The AI
# Debate Room (Feature 17, above) already has every analyst who genuinely
# disagrees challenge the proposal — this is deliberately not a second
# copy of that. Instead it's a single structured artifact: one specific
# employee, temporarily assigned, whose real job is to actively try to
# break the trade thesis — built entirely from real signals already
# computed elsewhere (AnalystVote reasoning, DecisionConfidence factors,
# the proposal's own risk_summary, the What-If Simulation Lab's worst
# named scenario, past CaseStudy history for the same symbol) — never
# invented evidence. See app/devils_advocate.py.
ChallengeSeverity = Literal["none_found", "minor", "major"]


class ChallengeReport(CamelModel):
    id: str
    proposal_id: str = Field(alias="proposalId")
    symbol: str
    assigned_agent: AgentId = Field(alias="assignedAgent")
    trade_summary: str = Field(alias="tradeSummary")
    bull_case: str = Field(alias="bullCase")
    bear_case: str = Field(alias="bearCase")
    hidden_risks: list[str] = Field(default_factory=list, alias="hiddenRisks")
    weak_assumptions: list[str] = Field(default_factory=list, alias="weakAssumptions")
    missing_evidence: list[str] = Field(default_factory=list, alias="missingEvidence")
    # Titles of real past CaseStudies (Library of Mistakes) for this same
    # symbol, if any — an honest empty list otherwise, never a fabricated
    # "this looks like a past mistake."
    historical_comparisons: list[str] = Field(default_factory=list, alias="historicalComparisons")
    # One line drawn from the What-If Simulation Lab's own real worst
    # named scenario (app/whatif.py) — never the full simulation, which
    # this codebase has already been bitten once by persisting unbounded
    # computed data (see nexus.py's MAX_DECISIONS history).
    worst_case_scenario: str = Field(alias="worstCaseScenario")
    suggested_improvements: list[str] = Field(default_factory=list, alias="suggestedImprovements")
    severity: ChallengeSeverity
    final_recommendation: str = Field(alias="finalRecommendation")
    # v0.7 Feature 47 — Company Operating System's "Real-Time Guidance":
    # real Constitution Article ids this report's own concern buckets map
    # to (see app/constitution.py's articles_for_challenge()), shown
    # inline on the report itself rather than only in the separate
    # enforcement log nexus.py already writes to ConstitutionState.
    cited_article_ids: list[str] = Field(default_factory=list, alias="citedArticleIds")
    created_at: str = Field(alias="createdAt")


# v0.7 Feature 41 — Innovation Points. A second, deliberately narrow
# ladder alongside Academy's KnowledgeLevel (Feature 31): where Academy
# tracks general knowledge mastery, this tracks one specific real skill —
# the ability to find genuine weaknesses before capital is committed — so
# it is driven by exactly one real, new signal this same feature
# introduces: an agent's own record as a Devil's Advocate (see
# app/innovation.py). Re-awarding points for events Academy already
# scores (course completion, research, mentoring) would be double-
# counting the same real signal under two names — the exact duplication
# this session's convention exists to avoid — so those are deliberately
# not wired here.
InnovationTierName = Literal["research_contributor", "research_specialist", "innovation_leader", "chief_innovator", "legendary_innovator"]


class InnovationState(CamelModel):
    agent_id: AgentId = Field(alias="agentId")
    points: float = 0.0
    tier: int = 0  # 0-4, index into app/innovation.py's tier tables
    tier_name: InnovationTierName = Field(default="research_contributor", alias="tierName")


# v0.7 — the Advanced Quantitative Research Division (app/black_box.py).
# Black Box Research Projects are long-running (weeks of in-game time,
# not ticks) investigations the Quant leads. The catalog is the brief's
# own eleven named example projects, real hand-authored content like
# app/academy_research.py's own topic catalog — never fabricated per
# instance.
BlackBoxCategory = Literal[
    "new_trading_framework",
    "portfolio_allocation",
    "statistical_edge",
    "ai_communication",
    "risk_model",
    "decision_framework",
    "journaling_improvement",
    "automation_improvement",
    "market_regime_detection",
    "portfolio_optimization",
    "academy_improvement",
]
BlackBoxProjectStatus = Literal["active", "paused", "under_review", "completed", "failed"]
BlackBoxPriority = Literal["low", "normal", "high"]


class BlackBoxTeamMember(CamelModel):
    agent_id: AgentId = Field(alias="agentId")
    role: str


class BlackBoxProject(CamelModel):
    id: str
    category: BlackBoxCategory
    title: str
    objective: str
    status: BlackBoxProjectStatus
    priority: BlackBoxPriority = "normal"
    # Real, deterministic occupation-fit team formation (see
    # black_box.py's module docstring for why there's no fabricated
    # Skill/Experience/Workload score) — the Quant leads every project,
    # plus four real specialist seats matched to an existing agent's own
    # real occupation. No "AI Research Scientist" seat: no agent in this
    # roster maps to it, and this feature already adds one new agent
    # (the Quant) — a documented, explicit cut.
    team: list[BlackBoxTeamMember] = Field(default_factory=list)
    devils_advocate: AgentId = Field(alias="devilsAdvocate")
    progress: float = 0.0
    confidence_level: float = Field(default=50.0, alias="confidenceLevel")
    budget: float = 0.0
    obstacles: list[str] = Field(default_factory=list)
    research_notes: list[str] = Field(default_factory=list, alias="researchNotes")
    # The Quant's own running log — this doubles as the brief's "Research
    # Meetings" (brainstorming/whiteboard/strategy-review entries) rather
    # than a second, parallel meeting-transcript system alongside
    # app/discussion.py and app/debate.py's own real meeting generators.
    quant_journal: list[str] = Field(default_factory=list, alias="quantJournal")
    started_sim_day: int = Field(alias="startedSimDay")
    estimated_completion_sim_day: int = Field(alias="estimatedCompletionSimDay")
    completed_at: str | None = Field(default=None, alias="completedAt")
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")


class BreakthroughReview(CamelModel):
    """v0.7 — the Founder Council Review that gates whether a completed
    Black Box Project becomes an official Company Breakthrough. See
    app/founders.py's generate_breakthrough_review() — a new mode of the
    same FounderCouncilSession-generating manager Feature 39 already
    built, not a second, independently-invented Founder meeting type."""

    id: str
    project_id: str = Field(alias="projectId")
    project_title: str = Field(alias="projectTitle")
    sim_day: int = Field(alias="simDay")
    hypothesis: str
    evidence: list[str] = Field(default_factory=list)
    statistical_results: str = Field(alias="statisticalResults")
    risks: list[str] = Field(default_factory=list)
    limitations: str
    devils_advocate_case: str = Field(alias="devilsAdvocateCase")
    recommendation: str
    verdict: Literal["approved", "rejected"]
    verdict_reason: str = Field(alias="verdictReason")
    created_at: str = Field(alias="createdAt")


class BlackBoxState(CamelModel):
    # Exactly one active/paused/under_review project at a time — the same
    # "one company-wide project" convention app/academy_research.py
    # already established, now applied to the much longer-running Black
    # Box track.
    active: BlackBoxProject | None = None
    # Completed AND failed projects both live here, permanently — a
    # completed project already has its own Hall of Fame/Museum entry;
    # a failed one *is* the brief's "Research Archives" (never wasted,
    # revisitable) — no second, separate failed-research schema needed.
    archive: list[BlackBoxProject] = Field(default_factory=list)
    reviews: list[BreakthroughReview] = Field(default_factory=list)
    viewed_breakthrough_ids: list[str] = Field(default_factory=list, alias="viewedBreakthroughIds")
    updated_at: str = Field(alias="updatedAt")


# v0.7 Feature 20 — Trade Gatekeeper. Every check is real (see
# app/gatekeeper.py for exactly what each one reads); never a fabricated
# pass/fail. `GatekeeperRejection` tracks a *hypothetical* outcome for a
# trade that never actually executed — graded later against the
# symbol's own real subsequent watchlist price movement, the same
# "wait for real time to pass, then check real data" convention
# app/executive.py's grade_ceo_decisions already uses for real trades.
class GatekeeperCheck(CamelModel):
    id: str
    label: str
    passed: bool
    detail: str


class GatekeeperVerdict(CamelModel):
    approved: bool
    checks: list[GatekeeperCheck] = Field(default_factory=list)
    summary: str
    created_at: str = Field(alias="createdAt")


GatekeeperOutcome = Literal["pending", "would_have_won", "would_have_lost"]


class GatekeeperRejection(CamelModel):
    """One trade the Gatekeeper blocked, tracked for the spec's
    "would it have worked?" self-evaluation. No order was ever placed —
    `outcome` resolves once GATEKEEPER_EVAL_WINDOW_MINUTES of simulated
    time has passed, purely from the real difference between the
    symbol's watchlist price then and now, never a fabricated P&L."""

    id: str
    proposal_id: str = Field(alias="proposalId")
    symbol: str
    ceo_choice: AnalystChoice = Field(alias="ceoChoice")
    reasons: list[str] = Field(default_factory=list)
    price_at_rejection: float = Field(alias="priceAtRejection")
    rejected_sim_minutes: int = Field(alias="rejectedSimMinutes")
    outcome: GatekeeperOutcome = "pending"
    resolved_price_change_pct: float | None = Field(default=None, alias="resolvedPriceChangePct")
    created_at: str = Field(alias="createdAt")
    resolved_at: str | None = Field(default=None, alias="resolvedAt")


# v0.7 Feature 16 — What-If Simulation Lab. Computed on demand (never
# persisted — see app/whatif.py's module docstring for why) from the
# symbol's own real recent candles, so this is intentionally NOT part of
# GameSaveState/the WS broadcast the way Debate/DecisionConfidence are.
ScenarioType = Literal[
    "bullish_continuation",
    "bearish_reversal",
    "sideways_consolidation",
    "high_volatility",
    "low_volatility",
    "news_shock",
    "gap_up",
    "gap_down",
    "trend_failure",
    "breakout_confirmation",
    "liquidity_sweep",
    "flash_crash",
]


class ScenarioResult(CamelModel):
    """One scenario's simulated outcome distribution over the position's
    typical hold horizon — a bootstrap resample of the symbol's own real
    recent bar-to-bar returns, biased/scaled per scenario (see
    app/whatif.py). Never a prediction of what will happen, only what a
    resilience stress-test of "if this condition occurred" looks like."""

    scenario_type: ScenarioType = Field(alias="scenarioType")
    label: str
    reward_range_low_pct: float = Field(alias="rewardRangeLowPct")
    reward_range_high_pct: float = Field(alias="rewardRangeHighPct")
    most_likely_pct: float = Field(alias="mostLikelyPct")
    typical_drawdown_pct: float = Field(alias="typicalDrawdownPct")
    max_risk_pct: float = Field(alias="maxRiskPct")
    probability_of_profit_pct: float = Field(alias="probabilityOfProfitPct")
    invalidation: str


class WhatIfSimulation(CamelModel):
    symbol: str
    hold_bars: int = Field(alias="holdBars")
    scenarios: list[ScenarioResult] = Field(default_factory=list)
    # The organic, unbiased resample of the symbol's own real recent
    # returns — no scenario bias applied — used as the honest "most
    # likely outcome" baseline (see app/whatif.py's module docstring for
    # why no cross-scenario probability is invented).
    baseline: ScenarioResult
    best_case_scenario: ScenarioType = Field(alias="bestCaseScenario")
    worst_case_scenario: ScenarioType = Field(alias="worstCaseScenario")


class CeoDecisionRecord(CamelModel):
    """One resolved executive decision — the permanent record behind
    CEO Accuracy / AI Accuracy / Agreement Rate / Successful & Failed
    Overrides. `outcome` only ever resolves to "correct"/"incorrect" once
    a *real* trade the CEO's choice actually caused has closed with a
    real realized P&L (see app/executive.py's grade_ceo_decisions) —
    "undecidable" covers both a CEO "wait" (no trade was ever placed to
    grade) and an override where the CEO's choice differed from the AI's
    recommendation (so the AI's own recommendation has no real trade to
    test it against — a genuine, honest gap, not a guess dressed up as
    data)."""

    id: str
    proposal_id: str = Field(alias="proposalId")
    symbol: str
    category: ResearchCategory
    ai_recommendation: AnalystChoice = Field(alias="aiRecommendation")
    ceo_decision: AnalystChoice = Field(alias="ceoDecision")
    agreed_with_ai: bool = Field(alias="agreedWithAi")
    decision_id: str | None = Field(default=None, alias="decisionId")
    outcome: Literal["pending", "correct", "incorrect", "undecidable"] = "pending"
    # v0.7 Feature 21 — Company Operating Modes. "ceo" is a real player
    # click via POST /api/executive/decide; "auto" covers both a
    # Feature-21 mode auto-resolution and the pre-existing stale-proposal
    # expiry auto-wait (see app/executive.py's resolve_proposal and
    # app/nexus.py's expire_stale_proposals loop) — neither was ever a
    # real CEO decision, so this field is honest about it. Defaults to
    # "ceo" for records predating this field, which were all real CEO
    # clicks (auto-resolution didn't exist yet).
    resolved_by: Literal["ceo", "auto"] = Field(default="ceo", alias="resolvedBy")
    created_at: str = Field(alias="createdAt")
    resolved_at: str | None = Field(default=None, alias="resolvedAt")


# v0.7 Feature 22 — Market Environment Simulation. Every regime is
# computed server-side from the same real trend/volatility signals
# app/market_data.py already exposes (trend_pct/volatility_pct,
# aggregated across the live watchlist) — see app/market_environment.py.
# Never a per-render client guess: this is the one persisted, authoritative
# reading every surface (Command Center, Market Observatory) reads from.
# Named distinctly from the existing MarketRegime (trending_up/
# trending_down/ranging, Player vs AI's per-symbol regime read) — a
# different concept: this one is a whole-market, five-way classification
# including volatility, not a single symbol's trend direction.
MarketEnvironmentRegime = Literal["bull", "bear", "sideways", "high_volatility", "low_volatility"]


class MarketEnvironmentEntry(CamelModel):
    """One real regime *change* — the historical timeline only ever grows
    when the computed regime actually differs from the previous tick's,
    not once per tick (see app/market_environment.py's tick function),
    so this stays a meaningful timeline rather than a repetitive log."""

    id: str
    regime: MarketEnvironmentRegime
    label: str
    detail: str
    sim_minutes: int = Field(alias="simMinutes")
    created_at: str = Field(alias="createdAt")


class MarketEnvironmentState(CamelModel):
    current: MarketEnvironmentRegime
    label: str
    detail: str
    changed_sim_minutes: int = Field(alias="changedSimMinutes")
    updated_at: str = Field(alias="updatedAt")
    # Capped at MAX_MARKET_ENVIRONMENT_HISTORY (app/nexus.py), most recent last.
    timeline: list[MarketEnvironmentEntry] = Field(default_factory=list)


# v0.7 Feature 23 — Company Health & Stability System. Ten real,
# documented sub-scores (see app/company_health.py for the exact formula
# behind each) — deliberately not the same list as v0.5's CompanyScore
# (research/decision/risk/paper-trading/teamwork/knowledge/simulation):
# this one asks "is the company healthy to keep operating," CompanyScore
# asks "is it performing well," and several factors overlap on purpose
# (e.g. Employee Morale reuses the same real agent-mood average
# CompanyScore's Team Coordination does) rather than inventing two
# divergent readings of the same underlying number.
CompanyHealthTier = Literal["excellent", "good", "stable", "needs_attention", "critical"]


class CompanyHealth(CamelModel):
    overall: float
    tier: CompanyHealthTier
    operational_stability: float = Field(alias="operationalStability")
    department_efficiency: float = Field(alias="departmentEfficiency")
    employee_morale: float = Field(alias="employeeMorale")
    research_progress: float = Field(alias="researchProgress")
    capital_health: float = Field(alias="capitalHealth")
    resource_usage: float = Field(alias="resourceUsage")
    reputation: float
    technology_level: float = Field(alias="technologyLevel")
    office_expansion: float = Field(alias="officeExpansion")
    education_progress: float = Field(alias="educationProgress")
    # v0.7 Feature 43 — real support-vs-challenge ratio across recent AI
    # Debates (see app/company_health.py's _team_chemistry). Defaults to
    # 50.0 (neutral) so a save from before this field existed still
    # validates during load — see persistence.py's migration path.
    team_chemistry: float = Field(default=50.0, alias="teamChemistry")
    # The two (or more, on a tie) lowest-scoring areas, named in plain
    # language — never generic filler, always tied to the actual weakest
    # real sub-score this tick (see app/company_health.py).
    recommendations: list[str] = Field(default_factory=list)
    updated_at: str = Field(alias="updatedAt")


# v0.7 Feature 43 — Company DNA (app/company_dna.py). The one genuinely
# net-new concept the Executive Intelligence Dashboard brief asked for —
# everything else in its "Company Health" list already existed under a
# different name (see the module docstring). Five real, descriptive
# behavioral traits computed from the company's own historical decision/
# trade record — never predictive, never a personality quiz, just "here
# is what this company's real track record shows about how it behaves."
class CompanyDnaTrait(CamelModel):
    id: str
    name: str
    score: float
    detail: str


class CompanyDNA(CamelModel):
    traits: list[CompanyDnaTrait] = Field(default_factory=list)
    summary: str
    # v0.7 Feature 48 — a pure, deterministic label read off the five
    # traits above (see app/company_dna.py's classify_identity()). Zero
    # new data — just an honest name for a real combination of numbers.
    identity: str = "Not Yet Established"
    # How many real closed trades/graded decisions this reading is based
    # on — shown so a fresh company's DNA reads as "not enough history
    # yet" rather than a confident-looking guess from thin data.
    sample_size: int = Field(alias="sampleSize")
    updated_at: str = Field(alias="updatedAt")


# v0.7 Feature 24 — the CIO's Monthly Executive Review (app/executive_review.py).
# A fresh cumulative snapshot over each already-capped recent-history list
# (research/decisions/debates/news), same convention CoachReport already
# uses — not a precisely period-windowed query. `company_score_change` is
# the one true period-over-period figure, a real delta against the
# previous review's own stored score.
class DepartmentActivity(CamelModel):
    agent_id: AgentId = Field(alias="agentId")
    research_completed: int = Field(alias="researchCompleted")
    decisions_involved: int = Field(alias="decisionsInvolved")


class ExecutiveReview(CamelModel):
    id: str
    company_score: float = Field(alias="companyScore")
    company_score_change: float = Field(alias="companyScoreChange")
    company_health_tier: CompanyHealthTier = Field(alias="companyHealthTier")
    department_activity: list[DepartmentActivity] = Field(default_factory=list, alias="departmentActivity")
    research_completed: int = Field(alias="researchCompleted")
    # Count of Academy knowledge projects completed to date (capped
    # library) — see app/academy_research.py. Not a points total, to
    # avoid a second, confusing "knowledge score."
    knowledge_gained: int = Field(alias="knowledgeGained")
    lessons_completed: int = Field(alias="lessonsCompleted")
    major_events: list[str] = Field(default_factory=list, alias="majorEvents")
    conflicts_detected: int = Field(alias="conflictsDetected")
    # Real, specific "worth another look" items — a low-confidence
    # research item still stalled, or Company Health reading poorly —
    # the CIO's "asks difficult questions" / "requests more research".
    flags: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    # Framed from real, already-configured company state (RiskLimits, the
    # Academy's own next level) — never invented aspirational text.
    long_term_goals: list[str] = Field(default_factory=list, alias="longTermGoals")
    # v0.7 Feature 25.5 — real "this builds on that" callbacks, one per
    # research category / Academy topic with 2+ completed items, naming
    # the two real titles involved (see app/executive_review.py's
    # _knowledge_connections). Empty when nothing yet has a real
    # predecessor to reference.
    knowledge_connections: list[str] = Field(default_factory=list, alias="knowledgeConnections")
    summary: str
    created_at: str = Field(alias="createdAt")


# v0.7 Feature 25 — AI Academy & Knowledge Network (app/academy.py,
# app/academy_research.py). Every agent has one real Knowledge Branch and
# a points total that only grows from real completed work (a finished
# ResearchItem, a finished AcademyProject, meeting attendance) — see
# academy.py's module docstring, including its honest scope note on why
# "mentorship" here is grounded in real knowledge points rather than an
# invented seniority system.
AcademyTopic = Literal[
    "market_history",
    "trading_psychology",
    "economic_concepts",
    "visualization_tools",
    "decision_biases",
    "trading_philosophies",
]
AcademyProjectStatus = Literal["in_progress", "completed"]


class AcademyProject(CamelModel):
    id: str
    topic: AcademyTopic
    title: str
    assigned_agent: AgentId = Field(alias="assignedAgent")
    status: AcademyProjectStatus
    progress: float
    summary: str
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")


# v0.7 Feature 31 — the real 7-level Novice-to-Mentor progression scale
# an agent's own Knowledge Points (app/academy.py) map onto, replacing the
# old bare 0-3 `tier` number with an honest label — `tier` (0-6) is kept
# as the underlying int so existing ordering/threshold code and tests
# don't need to change shape, `level` is the same value's real name.
KnowledgeLevel = Literal["novice", "beginner", "intermediate", "advanced", "expert", "master", "mentor"]


class AgentKnowledgeState(CamelModel):
    agent_id: AgentId = Field(alias="agentId")
    branch: str
    points: float
    tier: int
    level: KnowledgeLevel


class AcademyState(CamelModel):
    level: int
    level_label: str = Field(alias="levelLabel")
    total_points: float = Field(alias="totalPoints")
    completed_project_count: int = Field(alias="completedProjectCount")
    updated_at: str = Field(alias="updatedAt")


# v0.7 Feature 25.5 — Company Knowledge Graph (app/knowledge_graph.py).
# Computed fresh on every GET /api/knowledge-graph request, the same
# "expensive-ish to compute, cheap to re-derive, never persisted"
# convention app/whatif.py already established — the underlying records
# (research/academy_completed_projects/executive_reviews/coach_reports/
# hall_of_fame/agent_knowledge) are already persisted and capped
# elsewhere, so this is a derived view, not a second store.
KnowledgeNodeType = Literal["agent", "branch", "research", "academy_project", "executive_review", "coach_report", "hall_of_fame"]
KnowledgeEdgeRelation = Literal["researched", "completed", "has_branch", "builds_on", "featured_in", "ranked_top_agent", "achieved"]


class KnowledgeNode(CamelModel):
    id: str
    type: KnowledgeNodeType
    label: str
    subtitle: str
    # ISO timestamp for timeline ordering; None for evergreen nodes
    # (agent, branch) that were never "completed" at a point in time.
    timestamp: str | None = None


class KnowledgeEdge(CamelModel):
    source: str
    target: str
    relation: KnowledgeEdgeRelation
    label: str


class KnowledgeGraph(CamelModel):
    nodes: list[KnowledgeNode] = Field(default_factory=list)
    edges: list[KnowledgeEdge] = Field(default_factory=list)
    generated_at: str = Field(alias="generatedAt")


# v0.7 Feature 26 — the Discipline Chamber (app/discipline.py). One
# DisciplineReview per closed paper trade, scoring the real DECISION
# PROCESS behind it — never the outcome. `score`/`factors` are computed
# entirely from data known at (or before) the moment the trade closed,
# excluding pnl; `outcome`/`tradePnlPct` are attached afterward purely so
# the player can see whether a good process and a good outcome actually
# lined up. See discipline.py's module docstring for exactly which real
# signal backs each factor and why several of the brief's ten named
# qualities (documentation, principles-followed-via-Gatekeeper) have no
# real discriminating signal in this codebase for the reviewed population
# and are deliberately not scored.
DisciplineFactorId = Literal[
    "research_depth",
    "viewpoint_diversity",
    "uncertainty_acknowledged",
    "cross_examination",
    "assumptions_challenged",
    "position_sizing_discipline",
    "patience",
]
DisciplineTier = Literal["exemplary", "sound", "adequate", "weak", "reckless"]


class DisciplineFactor(CamelModel):
    id: DisciplineFactorId
    name: str
    score: float  # 0-100, this factor's own reading
    weight: float  # 0-1, this factor's share of the total score
    detail: str


class PostDecisionReview(CamelModel):
    """Real answers to the brief's seven post-decision questions, each
    derived from this review's own real DisciplineFactor readings and the
    trade's real outcome — never invented commentary. Any list may be
    empty (e.g. `assumptionsIncorrect` has nothing to say about a winning
    trade — see discipline.py's _post_decision_review)."""

    what_we_did_well: list[str] = Field(default_factory=list, alias="whatWeDidWell")
    mistakes_made: list[str] = Field(default_factory=list, alias="mistakesMade")
    information_overlooked: list[str] = Field(default_factory=list, alias="informationOverlooked")
    assumptions_incorrect: list[str] = Field(default_factory=list, alias="assumptionsIncorrect")
    what_to_repeat: list[str] = Field(default_factory=list, alias="whatToRepeat")
    what_to_never_repeat: list[str] = Field(default_factory=list, alias="whatToNeverRepeat")
    how_to_improve: list[str] = Field(default_factory=list, alias="howToImprove")


class DisciplineReview(CamelModel):
    id: str
    decision_id: str = Field(alias="decisionId")
    symbol: str
    score: float
    tier: DisciplineTier
    factors: list[DisciplineFactor] = Field(default_factory=list)
    # Every real agent involved in this decision (supporting + opposing
    # analysts) — the honest stand-in for "every department attends,"
    # since this codebase has no separate meeting-attendance record for
    # a single trade decision.
    attendees: list[AgentId] = Field(default_factory=list)
    summary: str
    post_decision_review: PostDecisionReview = Field(alias="postDecisionReview")
    # The trade's real outcome, attached after scoring — never fed back
    # into `score`/`factors` above (see discipline.py's module docstring).
    outcome: Literal["win", "loss"]
    trade_pnl_pct: float = Field(alias="tradePnlPct")
    hold_duration_minutes: int = Field(alias="holdDurationMinutes")
    # The real in-game day this review was filed — TradeTown's own
    # simulated calendar (TimeState.day), not a real wall-clock date, so
    # NPCs can honestly say "three months ago" / "on Day 47" the way the
    # brief's own example does. `created_at` above remains the real ISO
    # timestamp, kept only for audit/display, same as every other *_at
    # field in this codebase.
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


# v0.7 Feature 27 — the Library of Mistakes (app/mistakes.py). A
# permanent CaseStudy is filed whenever a closed, losing trade's own
# DisciplineReview shows a specific real process gap — never merely
# "the trade lost" on its own (a well-disciplined process that loses to
# real market variance is not a mistake — see discipline.py). Every field
# below is built from real structured data (the linked TradeDecision/
# PaperTrade/Debate), template sentences filling in real values, never a
# fabricated narrative — the same convention app/academy_research.py and
# app/executive_review.py already established.
CaseStudyCategory = Literal[
    "overconfidence",
    "incomplete_research",
    "unchallenged_assumptions",
    "acted_too_quickly",
    "ignored_dissent",
    "confirmation_bias",
    # v0.7 Feature 42 — the Decision Replay Center's "Successes" lesson
    # type (app/successes.py). Each mirrors one of the six mistake
    # categories above with its real trigger signal inverted, but only
    # three have a clean, crisp inversion — the other three mistake
    # signals ("incomplete_research", "ignored_dissent",
    # "confirmation_bias") describe a specific failure with no equally
    # crisp opposite (e.g. "research was NOT incomplete" is just the
    # normal case, not a distinguishable success story) and are
    # deliberately not mirrored, rather than padded out to match the
    # count on the mistake side.
    "disciplined_process",
    "rigorous_cross_examination",
    "patient_execution",
]
# The subset of CaseStudyCategory that CaseStudy.category can hold for a
# WIN (see app/successes.py) — every other category is loss-only (see
# app/mistakes.py). Shared here so both modules and any UI/test code read
# the same one true partition instead of maintaining two lists that could
# drift apart.
SUCCESS_CASE_STUDY_CATEGORIES: frozenset[CaseStudyCategory] = frozenset(
    {"disciplined_process", "rigorous_cross_examination", "patient_execution"}
)


class CaseStudyTimelineEntry(CamelModel):
    label: str
    timestamp: str


class CaseStudy(CamelModel):
    id: str
    category: CaseStudyCategory
    title: str
    symbol: str
    decision_id: str = Field(alias="decisionId")
    timeline: list[CaseStudyTimelineEntry] = Field(default_factory=list)
    background: str
    decision_process: str = Field(alias="decisionProcess")
    # Each entry is one real analyst's own real vote reasoning — never
    # invented dialogue.
    department_opinions: list[str] = Field(default_factory=list, alias="departmentOpinions")
    missed_information: str = Field(alias="missedInformation")
    lessons_learned: str = Field(alias="lessonsLearned")
    recommended_improvements: str = Field(alias="recommendedImprovements")
    # Real, already-configured company thresholds (RiskLimits, the Trade
    # Gatekeeper's own checks) — never invented aspirational principles.
    related_principles: list[str] = Field(default_factory=list, alias="relatedPrinciples")
    trade_pnl_pct: float = Field(alias="tradePnlPct")
    # The real in-game day this case study was filed — see
    # DisciplineReview.sim_day above for why.
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


# v0.7 Feature 29 — the Reasoning Lab (app/reasoning_lab.py). A permanent
# ReasoningChallenge is filed periodically from the company's most recent
# real AI Debate + its linked TradeDecision — practicing the REASONING
# itself, never a trade outcome (no pnl is ever read by this module,
# structurally, the same "process not outcome" guarantee
# app/discipline.py established). Nine categories were named in the
# brief; two have no real, checkable signal anywhere in this codebase
# ("Detecting Logical Fallacies" and "Building Better Questions" would
# require actual fallacy/question-quality detection this system doesn't
# do) and are deliberately not scored — see reasoning_lab.py's module
# docstring for exactly which real signal backs each of the seven kept
# categories.
ReasoningChallengeCategory = Literal[
    "finding_missing_information",
    "identifying_weak_evidence",
    "recognizing_contradictory_data",
    "separating_facts_from_assumptions",
    "evaluating_multiple_hypotheses",
    "comparing_competing_explanations",
    "improving_communication",
]


class ReasoningContribution(CamelModel):
    """One real analyst's real turn in the underlying AI Debate, reframed
    as this challenge's "departments collaborate" record — never invented
    dialogue. `stance` mirrors DebateTurn's own opening/challenge/support
    framing, the real, already-existing analogue of the brief's "Research
    asks Risk," "News challenges assumptions" collaboration."""

    agent_id: AgentId = Field(alias="agentId")
    role: AnalystRole
    stance: DebateStance
    contribution: str


class ReasoningSolution(CamelModel):
    """The brief's six required "Explain Your Thinking" fields, each
    filled from this challenge's own real Decision Confidence Engine
    factors and TradeDecision fields — never invented commentary. See
    reasoning_lab.py's _solution()."""

    what_we_know: list[str] = Field(default_factory=list, alias="whatWeKnow")
    what_we_do_not_know: list[str] = Field(default_factory=list, alias="whatWeDoNotKnow")
    assumptions: list[str] = Field(default_factory=list)
    why_reasonable: str = Field(alias="whyReasonable")
    confidence: float
    what_could_change_our_conclusion: str = Field(alias="whatCouldChangeOurConclusion")


class ReasoningChallenge(CamelModel):
    id: str
    category: ReasoningChallengeCategory
    title: str
    symbol: str
    decision_id: str = Field(alias="decisionId")
    contributions: list[ReasoningContribution] = Field(default_factory=list)
    solution: ReasoningSolution
    # The company's own Reasoning Level (see ReasoningLabState) at the
    # moment this challenge was generated — advanced categories are only
    # ever detected once the level that unlocks them has been reached
    # (see reasoning_lab.py's _LEVEL_FOR_CATEGORY), so this also records
    # exactly why this particular category could appear.
    reasoning_level: int = Field(alias="reasoningLevel")
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


class ReasoningLabState(CamelModel):
    """Company-wide reasoning progression — mirrors AcademyState's exact
    shape/convention: a real, monotonic completed-count gates a level
    number and label; unlocking "advanced challenges" (see
    reasoning_lab.py) is real, but new art/seminar content per level is
    an explicit scope cut, the same boundary AcademyState already
    established."""

    level: int
    level_label: str = Field(alias="levelLabel")
    completed_challenge_count: int = Field(alias="completedChallengeCount")
    updated_at: str = Field(alias="updatedAt")


# v0.7 Feature 30 — the Reflection Chamber (app/wisdom.py). Every
# in-game week and month the company holds a real ReflectionSession —
# generated fresh from data this codebase already computes elsewhere
# (DisciplineReview/CaseStudy/ReasoningChallenge/ResearchItem/
# GatekeeperRejection), never a fabricated meeting transcript. See
# wisdom.py's module docstring for exactly which real signal answers
# each of the brief's nine reflection questions and backs each of the
# eight real Company Wisdom factors.
ReflectionCadence = Literal["weekly", "monthly"]


class ReflectionQuestion(CamelModel):
    question: str
    answer: str


class ReflectionInsight(CamelModel):
    """One real department's real contribution to a session — the
    honest version of the brief's "Research explains a discovery, Risk
    explains concerns" cross-department sharing: real text from a real
    agent's own real recent output, never invented dialogue between
    fixed department roles that don't exist in this codebase."""

    agent_id: AgentId = Field(alias="agentId")
    insight: str


class ReflectionSession(CamelModel):
    id: str
    cadence: ReflectionCadence
    # Every real agent "attends" — this codebase has no separate
    # meeting-attendance record for company-wide sessions, the same
    # honest stand-in DisciplineReview.attendees already uses.
    attendees: list[AgentId] = Field(default_factory=list)
    questions: list[ReflectionQuestion] = Field(default_factory=list)
    insights: list[ReflectionInsight] = Field(default_factory=list)
    key_discoveries: list[str] = Field(default_factory=list, alias="keyDiscoveries")
    lessons_learned: list[str] = Field(default_factory=list, alias="lessonsLearned")
    important_questions: list[str] = Field(default_factory=list, alias="importantQuestions")
    recommended_future_projects: list[str] = Field(default_factory=list, alias="recommendedFutureProjects")
    # The real Company Wisdom Score at the moment this session closed —
    # see WisdomState below; never a trade-pnl-derived number.
    wisdom_score: float = Field(alias="wisdomScore")
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


# Never profit-based — see wisdom.py's module docstring for exactly
# which already-real signal backs each factor. Deliberately hard to
# max: an equal, unweighted mean of eight independent real behaviors,
# several of which (avoiding repeated mistakes, following the
# Gatekeeper's own principles) the company will realistically never
# score a clean 100 on.
WisdomFactorId = Literal[
    "learn_from_experience",
    "share_knowledge",
    "follow_principles",
    "improve_communication",
    "document_lessons",
    "avoid_repeating_mistakes",
    "complete_research",
    "support_collaboration",
]
WisdomTier = Literal["young_company", "developing_judgment", "institutional_memory", "seasoned_wisdom", "enduring_wisdom"]


class WisdomFactor(CamelModel):
    id: WisdomFactorId
    name: str
    score: float  # 0-100, this factor's own reading
    weight: float  # 0-1, this factor's share of the total score
    detail: str


class WisdomState(CamelModel):
    """Recomputed only when a ReflectionSession is generated (weekly/
    monthly), not every tick — a deliberate design choice, not a
    performance shortcut, so the score reads as genuinely slow-moving
    the way the brief asks, rather than jittering tick to tick."""

    score: float
    tier: WisdomTier
    tier_label: str = Field(alias="tierLabel")
    factors: list[WisdomFactor] = Field(default_factory=list)
    updated_at: str = Field(alias="updatedAt")


# v0.7 Feature 32 — Sage, the Socratic Mentor (app/mentor.py). Every
# in-game morning, one QuestionOfTheDay is drawn (deterministically, by
# sim day) from a small hand-authored QUESTION_LIBRARY — the honest
# version of "the Mentor publishes a question": there is no free-form
# question-generation capability in this codebase, so the library is
# real, curated content (the same convention DialogueManager's own
# flavor lines already use) rather than a fabricated claim that the AI
# is composing new questions daily. `related_reference` is at most ONE
# honest pointer into content this codebase already has for real
# (a Reasoning Lab challenge, a Library of Mistakes case study, ...) —
# never fabricated per-department "answers." See app/mentor.py's module
# docstring for exactly which brief sub-features (a separate weekly
# "Mentor Session," a graded "Daily Thinking Bonus," "Connected
# Constitution Articles") have no real backing and were cut.
QuestionCategory = Literal[
    "critical_thinking",
    "decision_making",
    "communication",
    "leadership",
    "psychology",
    "risk_awareness",
    "research",
    "reflection",
    "logic",
    "teamwork",
]


class QuestionOfTheDay(CamelModel):
    id: str
    category: QuestionCategory
    question: str
    related_reference: str | None = Field(default=None, alias="relatedReference")
    player_response: str | None = Field(default=None, alias="playerResponse")
    player_responded_at: str | None = Field(default=None, alias="playerRespondedAt")
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


# Every trait is one distinct real, already-computed signal — never a
# second independent measurement of a signal ThinkingProfile itself
# already scores under a different name (DisciplineReview's own
# "Patience" factor is deliberately NOT re-surfaced here for exactly
# that reason). "Communication" and "Adaptability" were both named in
# the brief but have no real, per-agent discriminating signal anywhere
# in this codebase and are cut — see app/mentor.py.
ThinkingTraitId = Literal[
    "curiosity",
    "evidence_quality",
    "open_mindedness",
    "humility",
    "reasoning",
    "collaboration",
]


class ThinkingTrait(CamelModel):
    id: ThinkingTraitId
    name: str
    score: float
    detail: str


class ThinkingProfile(CamelModel):
    """Purely computed from existing real signals, recomputed fresh each
    tick the same as AcademyState/ReasoningLabState — cheap, since it
    only re-scans already-capped lists, and honest, since the underlying
    data itself only changes a few times a day."""

    agent_id: AgentId = Field(alias="agentId")
    traits: list[ThinkingTrait] = Field(default_factory=list)
    updated_at: str = Field(alias="updatedAt")


class MentorState(CamelModel):
    tier: int
    tier_label: str = Field(alias="tierLabel")
    questions_asked: int = Field(alias="questionsAsked")
    updated_at: str = Field(alias="updatedAt")


# v0.7 Feature 44 — the Talent Discovery System (app/talent.py). A real,
# evidence-based "Discovery Event" — every field traces back to an
# agent's own real ThinkingProfile trait and real CoachReport score
# history, never a fabricated pattern. "Suggested Focus" deliberately
# replaces the brief's "Suggested Career Path": no agent's real
# occupation ever changes anywhere in this codebase (see talent.py's
# module docstring), so a literal career-path recommendation would
# imply a mechanic that doesn't exist.
class TalentReport(CamelModel):
    id: str
    agent_id: AgentId = Field(alias="agentId")
    trait_id: str = Field(alias="traitId")
    trait_name: str = Field(alias="traitName")
    title: str
    narrative: str
    evidence: list[str] = Field(default_factory=list)
    examples: list[str] = Field(default_factory=list)
    current_score: float = Field(alias="currentScore")
    # How many recent CoachReports this discovery's "consistent pattern"
    # check was based on — real, bounded evidence, never an unfulfillable
    # claim about calendar days this codebase doesn't track per agent.
    sample_size: int = Field(alias="sampleSize")
    suggested_focus: str = Field(alias="suggestedFocus")
    expected_benefits: str = Field(alias="expectedBenefits")
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


class TalentState(CamelModel):
    reports: list[TalentReport] = Field(default_factory=list)
    viewed_report_ids: list[str] = Field(default_factory=list, alias="viewedReportIds")
    updated_at: str = Field(alias="updatedAt")


# v0.7 Feature 46 — the Company Constitution. Article ids are plain
# strings ("I".."VIII" seeded, "IX"+ for CEO amendments) rather than a
# fixed Literal, since the Articles are the one piece of company state
# that can genuinely grow — see app/constitution.py's module docstring.
class ConstitutionArticle(CamelModel):
    id: str
    title: str
    text: str
    ratified_sim_day: int = Field(alias="ratifiedSimDay")
    created_at: str = Field(alias="createdAt")


# v0.7 Feature 46 — "Live Enforcement." A permanent, real log of every
# actual moment some other real system's own event invoked a specific
# Article — never a fabricated quote attributed to nobody.
ConstitutionCitationSource = Literal["case_study", "devils_advocate", "risk_department", "academy", "founders", "coach"]


class ConstitutionCitation(CamelModel):
    id: str
    article_id: str = Field(alias="articleId")
    source: ConstitutionCitationSource
    detail: str
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


class ConstitutionFounderVerdict(CamelModel):
    founder_id: FounderId = Field(alias="founderId")
    verdict: str
    redundant_with_article_id: str | None = Field(default=None, alias="redundantWithArticleId")


class ConstitutionEmployeeVote(CamelModel):
    agent_id: AgentId = Field(alias="agentId")
    choice: Literal["support", "oppose", "abstain"]
    reason: str


class ConstitutionAmendment(CamelModel):
    id: str
    proposed_title: str = Field(alias="proposedTitle")
    proposed_text: str = Field(alias="proposedText")
    status: Literal["proposed", "debated", "evaluated", "voted", "approved", "rejected"]
    founder_verdicts: list[ConstitutionFounderVerdict] = Field(default_factory=list, alias="founderVerdicts")
    coach_evaluation: str | None = Field(default=None, alias="coachEvaluation")
    employee_votes: list[ConstitutionEmployeeVote] = Field(default_factory=list, alias="employeeVotes")
    ceo_decision: Literal["pending", "approved", "rejected"] = Field(default="pending", alias="ceoDecision")
    ratified_article_id: str | None = Field(default=None, alias="ratifiedArticleId")
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


class ConstitutionState(CamelModel):
    articles: list[ConstitutionArticle] = Field(default_factory=list)
    citations: list[ConstitutionCitation] = Field(default_factory=list)
    amendments: list[ConstitutionAmendment] = Field(default_factory=list)
    updated_at: str = Field(alias="updatedAt")


# v0.7 Feature 39 — the Original Founders (app/founders.py). Only
# "keystone"/"compass" can ever be a founder_id — everyone else stays a
# normal employee, never blurring who is a Founder vs. an ordinary agent.
FounderId = Literal["keystone", "compass"]


class FounderLogEntry(CamelModel):
    """One real dialogue line reacting to a real event in that Founder's
    own domain (Keystone: DisciplineReview/CaseStudy; Compass:
    ReasoningChallenge/ReflectionSession) — see founders.py's
    `_domain_reference` for how the reference is chosen. Never a
    fabricated free-form conversation."""

    id: str
    founder_id: FounderId = Field(alias="founderId")
    line: str
    reference: str
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


class FounderCouncilSession(CamelModel):
    """v0.7 Feature 39 — the Founder Council. A real monthly sit-down
    between the Coach and both Founders, generated alongside the
    existing monthly CoachReport (see founders.py) — never a duplicate,
    independently-invented meeting transcript."""

    id: str
    sim_day: int = Field(alias="simDay")
    coach_highlight: str = Field(alias="coachHighlight")
    keystone_note: str = Field(alias="keystoneNote")
    compass_note: str = Field(alias="compassNote")
    created_at: str = Field(alias="createdAt")


class FounderState(CamelModel):
    """`retired` flips permanently to True the first time
    CompanyHealth.tier reaches "excellent" — see founders.py's
    `compute_founder_state`. Never reverts if health later dips, the
    same "a crossed milestone stays crossed" convention app/hall_of_fame.py
    already established. The Founders keep their existing schedule,
    personality, and dialogue unchanged after retirement — see
    founders.py's own module docstring."""

    retired: bool = False
    retired_at: str | None = Field(default=None, alias="retiredAt")
    log: list[FounderLogEntry] = Field(default_factory=list)
    council_sessions: list[FounderCouncilSession] = Field(default_factory=list, alias="councilSessions")
    updated_at: str = Field(alias="updatedAt")


# v0.7 Feature 33 — the CEO Treasury (app/treasury.py). A second account,
# structurally isolated from PaperPortfolio.cash_balance ("Operating
# Capital"): every function in treasury.py that moves money takes an
# explicit CEO-initiated amount as its own parameter — no automatic
# system (paper_trading.py, broker.py, risk_engine.py, research.py, ...)
# ever reads or writes `treasury.balance`, the same "never receives the
# thing it must never touch" structural guarantee discipline.py already
# established for pnl. The one deliberate exception is Smart Savings
# Rules — real, but only because the CEO explicitly configured and can
# pause them (the brief's own "Pause all automatic transfers"), never a
# system acting on Treasury funds without prior authorization.
TreasuryTransactionKind = Literal["deposit", "withdrawal", "auto_save"]


class TreasuryTransaction(CamelModel):
    id: str
    kind: TreasuryTransactionKind
    amount: float
    balance_after: float = Field(alias="balanceAfter")
    note: str
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


# The brief names three example rules ("save 5% of monthly profit," "save
# 10% after profitable months," "transfer excess operating cash above a
# chosen reserve"). The first two are the same real mechanic — saving a
# percentage of monthly profit only makes sense, and only ever fires,
# when that profit is positive — so they're one rule type here rather
# than two independently-fabricated ones that would behave identically;
# see treasury.py's module docstring.
SavingsRuleType = Literal["percent_of_monthly_profit", "excess_above_reserve"]


class SmartSavingsRule(CamelModel):
    id: str
    rule_type: SavingsRuleType = Field(alias="ruleType")
    # Meaning depends on rule_type: the save percentage for
    # percent_of_monthly_profit (unused, 0, for excess_above_reserve).
    percent: float
    # The reserve threshold for excess_above_reserve (unused, null, for
    # percent_of_monthly_profit).
    reserve_target: float | None = Field(default=None, alias="reserveTarget")
    active: bool = True
    created_at: str = Field(alias="createdAt")


class TreasuryMonthlyReport(CamelModel):
    id: str
    month_ending_day: int = Field(alias="monthEndingDay")
    deposits: float
    withdrawals: float
    auto_saved: float = Field(alias="autoSaved")
    ending_balance: float = Field(alias="endingBalance")
    created_at: str = Field(alias="createdAt")


class TreasuryState(CamelModel):
    balance: float = 0.0
    lifetime_deposits: float = Field(default=0.0, alias="lifetimeDeposits")
    largest_balance: float = Field(default=0.0, alias="largestBalance")
    # Capped, permanent — also doubles as the brief's "Savings Growth
    # Timeline" (each entry's balanceAfter plotted over time) rather than
    # a second, redundant stored series of the same real numbers.
    transactions: list[TreasuryTransaction] = Field(default_factory=list)
    savings_rules: list[SmartSavingsRule] = Field(default_factory=list, alias="savingsRules")
    monthly_reports: list[TreasuryMonthlyReport] = Field(default_factory=list, alias="monthlyReports")
    updated_at: str = Field(alias="updatedAt")


# v0.7 Feature 36 — the CEO Calendar & Company Schedule. One shared event
# shape for both real system-computed cadence events and player-created
# custom events — see app/calendar.py's module docstring for exactly
# which of the brief's calendar categories are real here and which are
# explicitly cut.
CalendarEventCategory = Literal[
    "morning_briefing",
    "weekly_coach_report",
    "monthly_coach_report",
    "weekly_reflection",
    "monthly_reflection",
    "monthly_executive_review",
    "monthly_treasury_report",
    "reasoning_challenge_window",
    "mentorship_window",
    "company_anniversary",
    "research_deadline",
    "emergency_meeting",
    "company_holiday",
    "extra_training_day",
    "research_marathon",
    "hackathon",
    "strategy_day",
    "celebration",
    "town_hall",
    "other",
]

# The closed set of categories POST /api/calendar/events/create accepts —
# the brief's own eight named examples plus a free-form "other".
PlayerEventCategory = Literal[
    "emergency_meeting",
    "company_holiday",
    "extra_training_day",
    "research_marathon",
    "hackathon",
    "strategy_day",
    "celebration",
    "town_hall",
    "other",
]


class CalendarEvent(CamelModel):
    id: str
    source: Literal["system", "player"]
    category: CalendarEventCategory
    title: str
    detail: str = ""
    day: int
    hour: int
    minute: int = 0
    # Only meaningful for the nearest reasoning_challenge_window/
    # mentorship_window entry — a live, honestly-computed "would this
    # actually fire right now" check against real current data, not a
    # prediction about a day that hasn't arrived yet. None everywhere
    # else, including every player event.
    eligible: bool | None = None
    created_at: str = Field(alias="createdAt")


class CalendarState(CamelModel):
    # Recomputed fresh every tick from real current data — the same
    # "cheap, always current" reasoning company_health/academy_state
    # already use — so system_events is never persisted stale.
    system_events: list[CalendarEvent] = Field(default_factory=list, alias="systemEvents")
    player_events: list[CalendarEvent] = Field(default_factory=list, alias="playerEvents")
    updated_at: str = Field(alias="updatedAt")


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
    strategy_reports: list[StrategyReport] = Field(default_factory=list, alias="strategyReports")
    strategy_reviews: list[StrategyReview] = Field(default_factory=list, alias="strategyReviews")
    hall_of_fame: list[HallOfFameEntry] = Field(default_factory=list, alias="hallOfFame")
    coach_reports: list[CoachReport] = Field(default_factory=list, alias="coachReports")
    company_score: CompanyScore = Field(alias="companyScore")
    performance_snapshots: list[PerformanceSnapshot] = Field(default_factory=list, alias="performanceSnapshots")
    risk_limits: RiskLimits = Field(default_factory=RiskLimits, alias="riskLimits")
    risk_warnings: list[RiskWarning] = Field(default_factory=list, alias="riskWarnings")
    scanner_alerts: list[ScannerAlert] = Field(default_factory=list, alias="scannerAlerts")
    decisions: list[TradeDecision] = Field(default_factory=list)
    agent_energy: AgentEnergy = Field(alias="agentEnergy")
    signal_calibration: SignalCalibrationState = Field(default_factory=SignalCalibrationState, alias="signalCalibration")
    player_vs_ai: PlayerVsAiState = Field(default_factory=PlayerVsAiState, alias="playerVsAi")
    education: EducationProgress = Field(default_factory=EducationProgress)
    # v0.6.2 Phase 10: which PaperTrade ids have already had their trade
    # outcome popup shown/dismissed — see app/routers/trades.py. Persisted
    # so a refresh or Docker restart never re-shows a popup for a trade
    # the player already saw. Real progress, not regenerable — capped like
    # every other list here (see portfolio.py's own MAX_TRADE_HISTORY,
    # which this tracks against).
    viewed_trade_notification_ids: list[str] = Field(default_factory=list, alias="viewedTradeNotificationIds")
    # Feature 12 — Executive Voting System. trade_proposals holds only
    # currently-pending proposals (removed the moment the CEO decides);
    # ceo_decisions is the permanent, capped history behind the CEO/AI
    # accuracy stats (see app/executive.py).
    trade_proposals: list[TradeProposal] = Field(default_factory=list, alias="tradeProposals")
    ceo_decisions: list[CeoDecisionRecord] = Field(default_factory=list, alias="ceoDecisions")
    # v0.7 Feature 17 — AI Debate Room. One Debate per proposal (with the
    # newest replacing prior ones for the same proposal if "request
    # another debate" was used), capped like every other list here.
    debates: list[Debate] = Field(default_factory=list)
    # v0.7 Feature 20 — Trade Gatekeeper. Every trade the gatekeeper
    # blocked, capped at MAX_GATEKEEPER_REJECTIONS like every other list
    # here; see app/gatekeeper.py.
    gatekeeper_rejections: list[GatekeeperRejection] = Field(default_factory=list, alias="gatekeeperRejections")
    # v0.7 Feature 22 — Market Environment Simulation (app/market_environment.py).
    market_environment: MarketEnvironmentState = Field(alias="marketEnvironment")
    # v0.7 Feature 23 — Company Health & Stability System (app/company_health.py).
    company_health: CompanyHealth = Field(alias="companyHealth")
    # v0.7 Feature 43 — Company DNA (app/company_dna.py).
    company_dna: CompanyDNA = Field(alias="companyDna")
    # v0.7 Feature 48 — Legacy: a small, permanent, capped per-trait
    # delta (app/company_dna.py's nudge_legacy()), layered on top of
    # company_dna's own fresh historical-average score every time it's
    # recomputed, never mixed into the five traits' own formulas. Keyed
    # by trait id (e.g. "risk_appetite").
    company_dna_legacy: dict[str, float] = Field(default_factory=dict, alias="companyDnaLegacy")
    # v0.7 Feature 24 — the CIO's Monthly Executive Review (app/executive_review.py).
    executive_reviews: list[ExecutiveReview] = Field(default_factory=list, alias="executiveReviews")
    # v0.7 Feature 25 — AI Academy. `academy_projects` holds the one
    # currently-active knowledge project (company-wide, not per-agent);
    # `academy_completed_projects` is the permanent, capped Knowledge
    # Library (app/academy_research.py). `agent_knowledge` is every
    # agent's own real points/tier (app/academy.py); `academy_state` is
    # the company-wide progression level derived from both.
    academy_projects: list[AcademyProject] = Field(default_factory=list, alias="academyProjects")
    academy_completed_projects: list[AcademyProject] = Field(default_factory=list, alias="academyCompletedProjects")
    agent_knowledge: dict[AgentId, AgentKnowledgeState] = Field(default_factory=dict, alias="agentKnowledge")
    academy_state: AcademyState = Field(alias="academyState")
    # v0.7 Feature 26 — the Discipline Chamber (app/discipline.py). One
    # capped, permanent DisciplineReview per closed paper trade.
    discipline_reviews: list[DisciplineReview] = Field(default_factory=list, alias="disciplineReviews")
    # v0.7 Feature 27 — the Library of Mistakes (app/mistakes.py). One
    # capped, permanent CaseStudy per detected real process-gap mistake.
    case_studies: list[CaseStudy] = Field(default_factory=list, alias="caseStudies")
    # v0.7 Feature 29 — the Reasoning Lab (app/reasoning_lab.py). One
    # capped, permanent ReasoningChallenge filed periodically from the
    # company's most recent real AI Debate; `reasoning_lab_state` is the
    # company-wide progression level derived from the challenge count.
    reasoning_challenges: list[ReasoningChallenge] = Field(default_factory=list, alias="reasoningChallenges")
    reasoning_lab_state: ReasoningLabState = Field(alias="reasoningLabState")
    # v0.7 Feature 30 — the Reflection Chamber (app/wisdom.py). One
    # capped, permanent ReflectionSession per weekly/monthly cycle;
    # `wisdom_state` is the company-wide Wisdom Score, updated only when
    # a session is generated (see WisdomState's own docstring for why).
    reflection_sessions: list[ReflectionSession] = Field(default_factory=list, alias="reflectionSessions")
    wisdom_state: WisdomState = Field(alias="wisdomState")
    # v0.7 Feature 32 — the Socratic Mentor (app/mentor.py). One capped,
    # permanent QuestionOfTheDay per in-game morning; `thinking_profiles`
    # is every agent's purely-computed readout; `mentor_state` is the
    # company-wide progression level derived from the archive's length.
    question_archive: list[QuestionOfTheDay] = Field(default_factory=list, alias="questionArchive")
    thinking_profiles: dict[AgentId, ThinkingProfile] = Field(default_factory=dict, alias="thinkingProfiles")
    mentor_state: MentorState = Field(alias="mentorState")
    # v0.7 Feature 39 — the Original Founders (app/founders.py).
    founder_state: FounderState = Field(alias="founderState")
    # v0.7 Feature 41 — the Intelligent Devil's Advocate System. One
    # capped, permanent ChallengeReport per proposal (with the newest
    # replacing prior ones for the same proposal if "request another
    # review" was used), same convention as `debates` above.
    # `innovation_state` is every agent's own real points/tier earned
    # through their Devil's Advocate track record (app/innovation.py).
    challenge_reports: list[ChallengeReport] = Field(default_factory=list, alias="challengeReports")
    innovation_state: dict[AgentId, InnovationState] = Field(default_factory=dict, alias="innovationState")
    # v0.7 Feature 33 — the CEO Treasury (app/treasury.py). See
    # TreasuryState's own docstring for the structural "never touched by
    # any automatic system" guarantee.
    treasury: TreasuryState
    # v0.7 Feature 36 — the CEO Calendar (app/calendar.py).
    calendar: CalendarState
    # v0.7 — the Advanced Quantitative Research Division (app/black_box.py).
    black_box: BlackBoxState = Field(alias="blackBox")
    # v0.7 Feature 44 — Talent Discovery System (app/talent.py).
    talent: TalentState = Field(alias="talent")
    # v0.7 Feature 46 — the Company Constitution (app/constitution.py).
    constitution: ConstitutionState = Field(alias="constitution")
    time: TimeState
    settings: SettingsState
    dialogue_history: list[DialogueHistoryEntry] = Field(default_factory=list, alias="dialogueHistory")
    updated_at: str = Field(alias="updatedAt")


# v0.7 — Save Architecture Redesign. `apply_client_save` (app/state.py)
# has only ever read three fields off the client's save POST —
# `player`, `settings`, `dialogue_history` — because everything else in
# GameSaveState is already server-authoritative, produced continuously
# by the tick loop (app/nexus.py) and living in GameState.data. Sending
# the rest was pure waste: real, measured, ~840KB of it, discarded by
# the server on every autosave, which is what pushed the request body
# past nginx's default 1MB limit (HTTP 413) as the simulation's history
# grew. `ClientSaveRequest` is the honest shape of what the client
# actually owns — inherits CamelModel's default `extra="ignore"`, so an
# un-updated client still sending a full legacy GameSaveState body stays
# accepted without error, just with the extra fields silently unused
# exactly as they already were.
class ClientSaveRequest(CamelModel):
    player: EntityTransform
    settings: SettingsState
    dialogue_history: list[DialogueHistoryEntry] = Field(default_factory=list, alias="dialogueHistory")


class ModuleWriteResult(CamelModel):
    name: str
    ok: bool
    bytes_written: int = Field(default=0, alias="bytesWritten")
    error: str | None = None


class SaveResponse(BaseModel):
    ok: Literal[True] = True
    updated_at: str = Field(alias="updatedAt", serialization_alias="updatedAt")
    # v0.7 — Save Architecture Redesign Phase 2 populates this with one
    # entry per persisted module; empty until then (Phase 1 alone has
    # nothing module-shaped yet to report).
    modules: list[ModuleWriteResult] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True)


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
