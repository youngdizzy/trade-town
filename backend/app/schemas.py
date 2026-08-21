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
AgentId = Literal[
    "scout",
    "atlas",
    "echo",
    "nova",
    "scribe",
    "coach",
    "sentinel",
    "pulse",
    "guardian",
    "cio",
    "sage",
    "keystone",
    "compass",
    "quant",
    "forge",
]
AGENT_IDS: tuple[AgentId, ...] = (
    "scout",
    "atlas",
    "echo",
    "nova",
    "scribe",
    "coach",
    "sentinel",
    "pulse",
    "guardian",
    "cio",
    "sage",
    "keystone",
    "compass",
    "quant",
    "forge",
)

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
ResearchCategory = Literal[
    "stock", "etf", "index", "economy", "gold", "bitcoin", "company", "sector"
]
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
    # Design Bible Chapter 67 (TTOS) Part 3 — a CEO-triggered Emergency
    # Stop activation or resume (see app/emergency_stop.py).
    "emergency",
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
TestScenario = Literal[
    "historical",
    "bull",
    "bear",
    "sideways",
    "high_volatility",
    "low_volatility",
    "custom",
]

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
    # v0.7 Feature 52 (Part 2) — the only terminal stage, reachable from
    # any prior stage via a real, deliberate CEO action (never automatic
    # — see app/sandbox.py's retire_strategy()). Placed last in
    # app/sandbox.py's own STAGE_ORDER so it always compares as "furthest
    # along," making every other stage-gated advance function a safe
    # no-op once a strategy is retired, rather than a special case.
    "retired",
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
DataStatus = Literal[
    "live", "delayed", "historical", "simulated", "stale", "error", "no_data"
]


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
    company_priority: CompanyPriority = Field(
        default="balanced", alias="companyPriority"
    )
    # v0.7 Feature 37 — same client-authoritative mechanism as
    # operating_mode/company_priority above.
    work_mode: WorkMode = Field(default="work", alias="workMode")
    # v0.7 Feature 49 (Phase 3 revision) — off by default. Employee
    # agents always auto-progress through the Foundational Mentor
    # Program regardless of this setting; it only gates whether the CEO
    # may ALSO voluntarily take the same lessons personally (never
    # required — see app/foundational_mentors.py's module docstring).
    ceo_academy_learning_mode: bool = Field(
        default=False, alias="ceoAcademyLearningMode"
    )
    # Design Bible Chapter 70 Part 3 — Weighted Executive Decision Engine.
    # Same client-authoritative mechanism as operating_mode/
    # company_priority above — no dedicated persistence endpoint needed.
    active_weight_profile: WeightProfile = Field(
        default="balanced_institutional", alias="activeWeightProfile"
    )
    # Only read when active_weight_profile == "custom" — a CEO-authored
    # multiplier per department, default 1.0 (neutral) for any role not
    # present. See app/weighted_decisions.py.
    custom_department_weights: dict[ExecutiveDepartmentRole, float] = Field(
        default_factory=dict, alias="customDepartmentWeights"
    )


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
    # Design Bible Chapter 75 — the real per-position tag Day Trading
    # Mode's own end-of-day flattening checks. None for any position
    # opened before this chapter (or via the currently-inert
    # PaperOrder/tick_broker path — see app/trading_modes.py's module
    # docstring) — never backfilled or guessed.
    trading_style: "TradingStyle | None" = Field(default=None, alias="tradingStyle")
    # Quantitative Research & Intelligence System, Piece 5 (Execution
    # Quant) — the real dollar transaction cost app/portfolio.py's
    # open_position() charged at entry (TRANSACTION_COST_BPS of
    # notional), carried on the position so close_position() can fold it
    # into the trade's net pnl. Defaults to 0.0 so a position opened
    # before this piece still validates during load.
    entry_cost_usd: float = Field(default=0.0, alias="entryCostUsd")
    # CEO directive "Next Professional Trading Firm Phase," Priority 1
    # (Execution Realism, app/execution_quality.py) — the real slippage,
    # in basis points, actually applied to this position's fill price at
    # entry. Derived from this tick's own real MarketIntelligenceState
    # (MarketQualityScore.score + this symbol's own LiquidityRead, when
    # available) — never a fabricated or random number, and 0.0 for any
    # entry where no MarketIntelligenceState was supplied (a test
    # fixture, or a position opened before this piece existed).
    entry_slippage_bps: float = Field(default=0.0, alias="entrySlippageBps")
    # CEO Company Health + Live Market Realism directive, Feature 24 —
    # MAE (Maximum Adverse Excursion) / MFE (Maximum Favorable
    # Excursion), the worst and best unrealized_pnl_pct this position
    # has actually shown since it opened. A real running watermark,
    # updated every tick in app/portfolio.py's mark_to_market() from the
    # same real live prices unrealized_pnl_pct already reads — never a
    # retroactively regenerated candle series, and never fabricated:
    # both start at 0.0 (a fresh position has shown no movement yet) and
    # only ever move toward their own real extreme. Defaults to 0.0 so a
    # position opened before this piece still validates during load.
    mae_pct: float = Field(default=0.0, alias="maePct")
    mfe_pct: float = Field(default=0.0, alias="mfePct")
    # CEO directive "Portfolio Construction, Capital Allocation & Execution
    # Realism" — the live analogue of DecisionVaultEntry.strategy_id /
    # CeoDecisionRecord.strategy_id (which only ever populate at trade
    # CLOSE, via the Decision Vault join). This is the same real,
    # CEO-explicit selection, applied the instant this position actually
    # opens — set in app/state.py's submit_ceo_decision() by patching the
    # freshly-opened position with .model_copy() strictly AFTER
    # resolve_proposal() returns, the identical "never alter what the
    # trade itself does" pattern already used for CeoDecisionRecord.
    # None whenever the CEO didn't select one (the honest majority) — this
    # is what makes real, live, strategy-scoped exposure/risk-budget reads
    # possible for OPEN positions, closing a gap the prior directive's own
    # audit confirmed: "an open PaperPosition cannot be attributed to a
    # strategy at all today."
    strategy_id: str | None = Field(default=None, alias="strategyId")


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
    supporting_agents: list[AgentId] = Field(
        default_factory=list, alias="supportingAgents"
    )
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
    # Design Bible Chapter 75 — carried over from the PaperPosition this
    # trade closed (app/portfolio.py's close_position() copies it
    # automatically). None for any trade closed before this chapter.
    trading_style: "TradingStyle | None" = Field(default=None, alias="tradingStyle")
    # Quantitative Research & Intelligence System, Piece 5 (Execution
    # Quant) — the real combined round-trip transaction cost (entry +
    # exit, app/portfolio.py's TRANSACTION_COST_BPS) already subtracted
    # from this trade's pnl above; kept here as its own field purely for
    # audit visibility, not a separate deduction. Defaults to 0.0 so a
    # trade closed before this piece still validates during load.
    transaction_cost_usd: float = Field(default=0.0, alias="transactionCostUsd")
    # CEO directive "Next Professional Trading Firm Phase," Priority 1
    # (Execution Realism, app/execution_quality.py) — the real slippage,
    # in basis points, actually applied at entry (carried over from the
    # PaperPosition this trade closed) and at exit (applied fresh by
    # close_position()'s own caller at the moment of close). Both 0.0 for
    # any fill where no MarketIntelligenceState was supplied. Distinct
    # from transaction_cost_usd above (a flat commission/spread proxy) —
    # slippage instead varies tick-to-tick with this tick's own real
    # market-quality/liquidity read, never a flat constant.
    entry_slippage_bps: float = Field(default=0.0, alias="entrySlippageBps")
    exit_slippage_bps: float = Field(default=0.0, alias="exitSlippageBps")
    # Prop-Firm Risk Intelligence Addendum, Piece 10b, Requirement 24 —
    # "distance to failure boundary before/after trade." Named
    # deliberately "drawdown ceiling," not "failure boundary": this is
    # the primary portfolio's own RiskLimits.max_drawdown_pct — a
    # self-chosen ceiling with no external authority behind it (see
    # RiskBudgetStatus's own docstring), the same honest distinction
    # Piece 11's AccountRiskBudgetStatus already draws for a real
    # Account's true externally-configurable boundary. None only when
    # close_position() was called without a real RiskLimits in scope
    # (a trade closed before this piece, or a test fixture that never
    # supplied one) — never a fabricated value standing in for it.
    distance_to_drawdown_ceiling_before_pct: float | None = Field(default=None, alias="distanceToDrawdownCeilingBeforePct")
    distance_to_drawdown_ceiling_after_pct: float | None = Field(default=None, alias="distanceToDrawdownCeilingAfterPct")
    # CEO Company Health + Live Market Realism directive, Feature 24 —
    # carried over from the PaperPosition this trade closed
    # (app/portfolio.py's close_position() copies it automatically, same
    # pattern as trading_style above). See PaperPosition.mae_pct/mfe_pct
    # for the full real-watermark explanation. Defaults to 0.0 so a
    # trade closed before this piece still validates during load.
    mae_pct: float = Field(default=0.0, alias="maePct")
    mfe_pct: float = Field(default=0.0, alias="mfePct")


# CEO directive "Professional Trading Firm Transformation" — Post-Trade
# Review, Exit Efficiency (app/exit_efficiency.py). RESEARCH FINDING:
# `PaperTrade.maePct`/`mfePct` (Feature 24, above) already carry a real
# running watermark of the worst/best paper P&L% a closed position ever
# saw — computed live in app/portfolio.py's mark_to_market(), never a
# retroactive reconstruction. That real data was never read by any
# post-trade review module (Discipline Chamber, mistakes.py/successes.py,
# app/failure_review.py) until now. This is a genuinely new, third axis
# — distinct from Discipline's outcome-blind PROCESS score and
# failure_review.py's WHY-the-thesis-failed classification — answering
# "how well was the EXIT managed relative to the trade's own real price
# path," for both wins and losses alike. Purely additive: computed fresh
# per request, no new GameSaveState field, and never reads or changes
# any existing score/classification.
ExitEfficiencyState = Literal["efficient_exit", "average_exit", "poor_exit", "not_enough_data"]


class TradeExitEfficiency(CamelModel):
    """One real closed trade's exit-efficiency read. `capturePct` is the
    real, continuous "Edge Ratio" professional traders already use —
    where, within this trade's OWN real observed high-low range
    (`maePct` to `mfePct`), it actually closed: 100 means it closed at
    the best point ever seen, 0 means it closed at the worst point ever
    seen, 50 means it closed exactly in the middle. Works identically
    for a win or a loss — a losing trade that recovered most of the way
    from its own worst drawdown before closing reads a real, honest
    capturePct just like a winning trade that gave back most of its
    peak gain does. `None` (state `not_enough_data`) only when
    `maePct == mfePct == 0.0` — genuinely ambiguous between "this trade
    never really moved" and "this trade closed before the codebase ever
    tracked a watermark on it" (both default to the same 0.0/0.0), never
    guessed at either way."""

    trade_id: str = Field(alias="tradeId")
    symbol: str
    pnl_pct: float = Field(alias="pnlPct")
    mae_pct: float = Field(alias="maePct")
    mfe_pct: float = Field(alias="mfePct")
    capture_pct: float | None = Field(default=None, alias="capturePct")
    state: ExitEfficiencyState = Field(alias="evidenceState")
    sim_day: int = Field(alias="simDay")


class ExitEfficiencySummary(CamelModel):
    """The real, disclosed aggregate — every count a direct tally over
    `reads`, `avgCapturePct` computed only over trades with a real,
    non-ambiguous `capturePct`, never a fabricated company-wide average
    that silently drops the ambiguous trades without disclosing it."""

    reads: list[TradeExitEfficiency]
    avg_capture_pct: float | None = Field(default=None, alias="avgCapturePct")
    efficient_exit_count: int = Field(alias="efficientExitCount")
    average_exit_count: int = Field(alias="averageExitCount")
    poor_exit_count: int = Field(alias="poorExitCount")
    not_enough_data_count: int = Field(alias="notEnoughDataCount")
    updated_at: str = Field(alias="updatedAt")


# CEO directive "Next Professional Trading Firm Phase," Priority 2 —
# Unified Professional P&L/Performance Reporting (app/performance_
# attribution.py). RESEARCH FINDING: no symbol-level P&L aggregation
# existed anywhere in this codebase before this piece — `PerformancePanel
# .tsx`'s "All-Time Trade Journal" already computes win rate/avg win/avg
# loss, but only across the WHOLE trade history, never broken out per
# symbol. Scoped to SYMBOL only this pass — real, unambiguous, 100%
# real-data coverage (every PaperTrade already carries its own real
# `symbol`). AGENT-level attribution is deliberately NOT built here: a
# trade can carry multiple `supportingAgents`/`opposingAgents`, and
# there is no existing, CEO-authorized rule for how to split credit
# across them — inventing one unilaterally would be a fabricated
# convention dressed up as a real metric. STRATEGY-level remains
# blocked (`DecisionVaultEntry.strategyId` is always `None` on a live
# Trading Floor trade — already disclosed in the Session Trading
# Education work). See CHANGELOG.md for the full reasoning on both.
SymbolPerformanceEvidenceState = Literal["sufficient_evidence", "not_enough_data"]


class SymbolPerformanceRead(CamelModel):
    """One symbol's real, computed-fresh performance record over
    `state.paper_portfolio.trade_history`. `expectancy_pct` is the
    standard win-rate/avg-win/avg-loss decomposition — algebraically
    identical to `avg_pnl_pct` under this same win/loss partition (see
    test_performance_attribution.py), exposed separately because
    professional traders read the decomposition itself (win rate vs.
    win/loss size asymmetry) as diagnostic, not because it's a second,
    independently-derived number. `profit_factor` (gross profit / gross
    loss) is `None`, not a fabricated infinity, when there are zero
    losing trades to divide by — a real "undefined" state, not a
    missing one. Both `expectancy_pct` and `profit_factor` are `None`
    below `MIN_SYMBOL_SAMPLE_FOR_VERDICT` trades (`evidenceState` is
    then `not_enough_data`) — raw counts/totalPnl still show, since
    those are real regardless of sample size, only the derived ratios
    are withheld."""

    symbol: str
    trade_count: int = Field(alias="tradeCount")
    win_count: int = Field(alias="winCount")
    loss_count: int = Field(alias="lossCount")
    win_rate_pct: float = Field(alias="winRatePct")
    total_pnl: float = Field(alias="totalPnl")
    avg_pnl_pct: float = Field(alias="avgPnlPct")
    avg_winner_pct: float | None = Field(default=None, alias="avgWinnerPct")
    avg_loser_pct: float | None = Field(default=None, alias="avgLoserPct")
    expectancy_pct: float | None = Field(default=None, alias="expectancyPct")
    profit_factor: float | None = Field(default=None, alias="profitFactor")
    avg_mae_pct: float = Field(alias="avgMaePct")
    avg_mfe_pct: float = Field(alias="avgMfePct")
    best_trade_pnl_pct: float = Field(alias="bestTradePnlPct")
    worst_trade_pnl_pct: float = Field(alias="worstTradePnlPct")
    evidence_state: SymbolPerformanceEvidenceState = Field(alias="evidenceState")


class SymbolPerformanceSummary(CamelModel):
    """`reads` sorted by `total_pnl` descending — the most profitable
    symbol first, directly answering "what is making money?"."""

    reads: list[SymbolPerformanceRead]
    updated_at: str = Field(alias="updatedAt")


# CEO directive "Next Phase: Professional Trading Firm Intelligence,"
# Phase 3 — Session + Market Regime P&L. Now honestly buildable because
# Phase 2 (app/nexus.py) closed the one real Decision Vault coverage gap
# (day-end flattened closes) — SESSION/MARKET REGIME context lives only
# on `DecisionVaultEntry`, joined here by `trade_id`, never fabricated
# for a trade with no matching vault entry (see `trades_excluded_no_
# vault_entry` below). Same 12-metric shape as `SymbolPerformanceRead`
# above (win rate, expectancy, profit factor, avg winner/loser, avg
# MAE/MFE, best/worst trade) — duplicated as its own schema rather than
# a shared base class so the already-shipped `SymbolPerformanceRead`
# stays completely untouched by this addition.
class SessionPerformanceRead(CamelModel):
    session: TradingSession
    trade_count: int = Field(alias="tradeCount")
    win_count: int = Field(alias="winCount")
    loss_count: int = Field(alias="lossCount")
    win_rate_pct: float = Field(alias="winRatePct")
    total_pnl: float = Field(alias="totalPnl")
    avg_pnl_pct: float = Field(alias="avgPnlPct")
    avg_winner_pct: float | None = Field(default=None, alias="avgWinnerPct")
    avg_loser_pct: float | None = Field(default=None, alias="avgLoserPct")
    expectancy_pct: float | None = Field(default=None, alias="expectancyPct")
    profit_factor: float | None = Field(default=None, alias="profitFactor")
    avg_mae_pct: float = Field(alias="avgMaePct")
    avg_mfe_pct: float = Field(alias="avgMfePct")
    best_trade_pnl_pct: float = Field(alias="bestTradePnlPct")
    worst_trade_pnl_pct: float = Field(alias="worstTradePnlPct")
    evidence_state: SymbolPerformanceEvidenceState = Field(alias="evidenceState")


class SessionPerformanceSummary(CamelModel):
    """`reads` sorted by `total_pnl` descending. `trades_excluded_no_
    vault_entry` is a real, disclosed count — never silently dropped —
    of closed trades with no matching `DecisionVaultEntry` to read
    session context from (see this schema group's own comment above for
    why that can still happen occasionally)."""

    reads: list[SessionPerformanceRead]
    trades_excluded_no_vault_entry: int = Field(alias="tradesExcludedNoVaultEntry")
    updated_at: str = Field(alias="updatedAt")


class RegimePerformanceRead(CamelModel):
    regime: MarketIntelligenceRegime
    trade_count: int = Field(alias="tradeCount")
    win_count: int = Field(alias="winCount")
    loss_count: int = Field(alias="lossCount")
    win_rate_pct: float = Field(alias="winRatePct")
    total_pnl: float = Field(alias="totalPnl")
    avg_pnl_pct: float = Field(alias="avgPnlPct")
    avg_winner_pct: float | None = Field(default=None, alias="avgWinnerPct")
    avg_loser_pct: float | None = Field(default=None, alias="avgLoserPct")
    expectancy_pct: float | None = Field(default=None, alias="expectancyPct")
    profit_factor: float | None = Field(default=None, alias="profitFactor")
    avg_mae_pct: float = Field(alias="avgMaePct")
    avg_mfe_pct: float = Field(alias="avgMfePct")
    best_trade_pnl_pct: float = Field(alias="bestTradePnlPct")
    worst_trade_pnl_pct: float = Field(alias="worstTradePnlPct")
    evidence_state: SymbolPerformanceEvidenceState = Field(alias="evidenceState")


class RegimePerformanceSummary(CamelModel):
    reads: list[RegimePerformanceRead]
    trades_excluded_no_vault_entry: int = Field(alias="tradesExcludedNoVaultEntry")
    updated_at: str = Field(alias="updatedAt")


# CEO directive "Live Trade → Strategy Provenance," Phase 4 — Strategy
# Exposure. This module's own SESSION/REGIME section above was written
# blocked on exactly this axis ("STRATEGY: DecisionVaultEntry.strategy_id
# is always None on a live Trading Floor trade") — that gap is now
# closed by the same directive's Phase 2 work, so this is the honest
# unlock, not a new mechanism. Same 12-metric shape as SymbolPerformanceRead
# above, keyed by strategy_id instead — grouped ONLY over trades whose
# strategy_id is real (DecisionVaultEntry.strategy_id is not None, i.e.
# strategyProvenanceState == "known"; see app/trade_attribution.py). A
# trade with no matching vault entry at all is disclosed separately from
# one with a vault entry but no CEO-selected strategy — "unavailable" and
# "unknown" are different, both real, provenance states, and collapsing
# them into one exclusion count would erase that distinction.
class StrategyPerformanceRead(CamelModel):
    strategy_id: str = Field(alias="strategyId")
    trade_count: int = Field(alias="tradeCount")
    win_count: int = Field(alias="winCount")
    loss_count: int = Field(alias="lossCount")
    win_rate_pct: float = Field(alias="winRatePct")
    total_pnl: float = Field(alias="totalPnl")
    avg_pnl_pct: float = Field(alias="avgPnlPct")
    avg_winner_pct: float | None = Field(default=None, alias="avgWinnerPct")
    avg_loser_pct: float | None = Field(default=None, alias="avgLoserPct")
    expectancy_pct: float | None = Field(default=None, alias="expectancyPct")
    profit_factor: float | None = Field(default=None, alias="profitFactor")
    avg_mae_pct: float = Field(alias="avgMaePct")
    avg_mfe_pct: float = Field(alias="avgMfePct")
    best_trade_pnl_pct: float = Field(alias="bestTradePnlPct")
    worst_trade_pnl_pct: float = Field(alias="worstTradePnlPct")
    evidence_state: SymbolPerformanceEvidenceState = Field(alias="evidenceState")


class StrategyPerformanceSummary(CamelModel):
    """`reads` sorted by `total_pnl` descending, one entry per real
    strategy id a CEO has actually selected at decision time at least
    once. `trades_excluded_no_strategy_selected` counts real closed
    trades with a real matching Decision Vault entry where the CEO
    simply never picked a strategy (`strategyProvenanceState ==
    "unknown"` — the honest majority of trades, especially before this
    feature existed). `trades_excluded_no_vault_entry` counts trades
    with no matching vault entry at all (`"unavailable"`), the same
    disclosed eviction edge case every other performance-by-* summary
    already reports. Neither count is ever folded into the other."""

    reads: list[StrategyPerformanceRead]
    trades_excluded_no_strategy_selected: int = Field(alias="tradesExcludedNoStrategySelected")
    trades_excluded_no_vault_entry: int = Field(alias="tradesExcludedNoVaultEntry")
    updated_at: str = Field(alias="updatedAt")


# CEO directive "Live Trade → Strategy Provenance," Phase 6 — the same
# Strategy Exposure axis above, cross-cut by session. Two independent
# real join keys on the SAME DecisionVaultEntry (strategy_id, session),
# never a fabricated third dimension.
class StrategySessionPerformanceRead(CamelModel):
    strategy_id: str = Field(alias="strategyId")
    session: TradingSession
    trade_count: int = Field(alias="tradeCount")
    win_count: int = Field(alias="winCount")
    loss_count: int = Field(alias="lossCount")
    win_rate_pct: float = Field(alias="winRatePct")
    total_pnl: float = Field(alias="totalPnl")
    avg_pnl_pct: float = Field(alias="avgPnlPct")
    avg_winner_pct: float | None = Field(default=None, alias="avgWinnerPct")
    avg_loser_pct: float | None = Field(default=None, alias="avgLoserPct")
    expectancy_pct: float | None = Field(default=None, alias="expectancyPct")
    profit_factor: float | None = Field(default=None, alias="profitFactor")
    avg_mae_pct: float = Field(alias="avgMaePct")
    avg_mfe_pct: float = Field(alias="avgMfePct")
    best_trade_pnl_pct: float = Field(alias="bestTradePnlPct")
    worst_trade_pnl_pct: float = Field(alias="worstTradePnlPct")
    evidence_state: SymbolPerformanceEvidenceState = Field(alias="evidenceState")


class StrategySessionPerformanceSummary(CamelModel):
    """`reads` sorted by `total_pnl` descending. Same two exclusion
    reasons as `StrategyPerformanceSummary` — never folded together."""

    reads: list[StrategySessionPerformanceRead]
    trades_excluded_no_strategy_selected: int = Field(alias="tradesExcludedNoStrategySelected")
    trades_excluded_no_vault_entry: int = Field(alias="tradesExcludedNoVaultEntry")
    updated_at: str = Field(alias="updatedAt")


# CEO directive "Live Trade → Strategy Provenance," Phase 5 — does a
# strategy's real LIVE (known-provenance) performance actually match
# what its own real backtest evidence (StrategyHealthAssessment, Feature
# 52 Part 2 — a recent-vs-lifetime SimulationResult trend read) claimed?
# Compares win_rate_pct only — the one metric both sides express on the
# identical 0-100 real percentage scale. Deliberately does NOT compare
# expectancy: the live side is in real dollars-of-percent-return
# (avg_pnl_pct) while the backtest side is in R-multiples
# (EmaPullbackStatsBucket.expectancy_r) — different units entirely, and
# forcing them onto one number would be a fabricated equivalence, not a
# real comparison.
StrategyLiveVsBacktestVerdict = Literal[
    "consistent_with_backtest",
    "diverging_from_backtest",
    "not_enough_live_data",
    "no_backtest_health_on_record",
]


class StrategyLiveVsBacktestRead(CamelModel):
    strategy_id: str = Field(alias="strategyId")
    live_win_rate_pct: float = Field(alias="liveWinRatePct")
    live_trade_count: int = Field(alias="liveTradeCount")
    # None only when no real StrategyHealthAssessment has ever been
    # generated for this strategy (no completed Market Simulation run
    # yet) — never a fabricated placeholder number.
    backtest_recent_win_rate_pct: float | None = Field(default=None, alias="backtestRecentWinRatePct")
    backtest_recent_sample_size: int | None = Field(default=None, alias="backtestRecentSampleSize")
    win_rate_delta_pct: float | None = Field(default=None, alias="winRateDeltaPct")
    verdict: StrategyLiveVsBacktestVerdict
    detail: str


class StrategyLiveVsBacktestSummary(CamelModel):
    reads: list[StrategyLiveVsBacktestRead]
    updated_at: str = Field(alias="updatedAt")


# CEO directive "Portfolio Construction, Capital Allocation & Execution
# Realism," Phase 5 — strategies compete for capital based on evidence,
# never on win rate alone and never auto-allocated to whichever most
# recently profited (see app/performance_attribution.py's
# compute_strategy_capital_allocation_evidence() for the full real-vs-
# disclosed-gap accounting). "no_live_trades_yet" is a third, distinct
# evidence state alongside the module's existing sufficient/not-enough
# pair — a Strategy the CEO has never actually traded still belongs on
# this roster (its real allocatedCapital is still a real number), but
# every derived metric below must stay None rather than pretend zero
# trades produced a real read.
StrategyAllocationEvidenceState = Literal["sufficient_evidence", "not_enough_data", "no_live_trades_yet"]


class StrategyCapitalAllocationRead(CamelModel):
    """One row per real Strategy in the roster (`state.strategies`),
    joining only already-computed, already-real sources — never a new
    statistical calculation duplicating `_group_metrics()`. `allocated_
    capital` is the CEO's own existing manual ceiling (Strategy.
    allocatedCapital); everything else here is informational evidence
    to help that manual decision, never a system-computed replacement
    for it. `live_drawdown_usd` and `live_return_volatility_pct` are the
    two genuinely new real reads this phase adds — see this row's
    sibling module for exactly how each is computed and why the
    remaining two directive-named dimensions (robustness, portfolio
    correlation) are disclosed gaps instead of fabricated numbers."""

    strategy_id: str = Field(alias="strategyId")
    strategy_name: str = Field(alias="strategyName")
    stage: StrategyStage
    allocated_capital: float = Field(alias="allocatedCapital")
    evidence_state: StrategyAllocationEvidenceState = Field(alias="evidenceState")
    trade_count: int = Field(alias="tradeCount")
    win_rate_pct: float | None = Field(default=None, alias="winRatePct")
    expectancy_pct: float | None = Field(default=None, alias="expectancyPct")
    profit_factor: float | None = Field(default=None, alias="profitFactor")
    # Real peak-to-trough drawdown of this strategy's own cumulative
    # realized P&L, ordered by real closed_at — in dollars, never a
    # percentage, because strategies share one account's capital and
    # have no isolated sub-account equity base a percentage could
    # honestly be measured against.
    live_drawdown_usd: float | None = Field(default=None, alias="liveDrawdownUsd")
    # Real sample standard deviation of this strategy's own per-trade
    # pnl_pct — a return-volatility read, distinct from (and never
    # confused with) the ATR/price-volatility concept
    # position_sizing.py's VolatilitySizingRead already covers.
    live_return_volatility_pct: float | None = Field(default=None, alias="liveReturnVolatilityPct")
    avg_entry_slippage_bps: float | None = Field(default=None, alias="avgEntrySlippageBps")
    avg_exit_slippage_bps: float | None = Field(default=None, alias="avgExitSlippageBps")
    session_reads: list[StrategySessionPerformanceRead] = Field(default_factory=list, alias="sessionReads")
    current_exposure_value: float = Field(default=0.0, alias="currentExposureValue")
    current_exposure_pct_of_equity: float = Field(default=0.0, alias="currentExposurePctOfEquity")
    robustness_note: str = Field(alias="robustnessNote")
    correlation_note: str = Field(alias="correlationNote")


class StrategyCapitalAllocationSummary(CamelModel):
    """`reads` sorted by `allocated_capital` descending — the CEO's own
    existing real capital commitment, never a system-generated
    performance ranking. This view is deliberately never sorted by
    expectancy, win rate, or recent P&L, so its own row order can't be
    mistaken for an auto-allocation recommendation."""

    reads: list[StrategyCapitalAllocationRead]
    min_sample_for_evidence: int = Field(alias="minSampleForEvidence")
    updated_at: str = Field(alias="updatedAt")


# CEO directive "Portfolio Construction, Capital Allocation & Execution
# Realism," Phase 6 — strategy degradation, distinguishing normal
# variation from a real, evidence-backed warning sign. Never auto-
# retires anything on a tiny sample (see app/performance_attribution.py's
# compute_strategy_degradation() for exactly which real signal each
# level requires and every disclosed, arbitrary threshold chosen).
StrategyDegradationLevel = Literal["normal_variation", "possible_degradation", "critical_degradation", "not_enough_data"]


class StrategyDegradationRead(CamelModel):
    """One row per real Strategy with enough live trade history to say
    anything. `signals` names exactly which real, cited condition(s)
    fired — never a black-box score. Every recent/lifetime metric pair
    reuses an already-computed source (`_group_metrics()`,
    `_live_return_volatility_pct()`, `_avg_slippage_bps()`,
    `_live_drawdown_usd()` — see compute_strategy_capital_allocation_
    evidence() for the first four) computed twice, once over the
    strategy's own most recent trades and once over its full lifetime —
    never a new statistic. `recent_invalidation_count` is the one
    genuinely new real read this phase adds: how many of the strategy's
    own recent trades were classified `reason == "bad_thesis"` by the
    real, already-existing Discipline Chamber failure review
    (app/failure_review.py's classify_failure(), filed for every real
    closed losing trade) — a real "this strategy's thesis was wrong
    again" signal, not a fabricated one."""

    strategy_id: str = Field(alias="strategyId")
    strategy_name: str = Field(alias="strategyName")
    level: StrategyDegradationLevel
    signals: list[str]
    recent_trade_count: int = Field(alias="recentTradeCount")
    lifetime_trade_count: int = Field(alias="lifetimeTradeCount")
    recent_expectancy_pct: float | None = Field(default=None, alias="recentExpectancyPct")
    lifetime_expectancy_pct: float | None = Field(default=None, alias="lifetimeExpectancyPct")
    recent_return_volatility_pct: float | None = Field(default=None, alias="recentReturnVolatilityPct")
    lifetime_return_volatility_pct: float | None = Field(default=None, alias="lifetimeReturnVolatilityPct")
    # Entry-side slippage only (the same side the degradation signal
    # compares) — exit-side is computed for symmetry with Phase 5's
    # avgExitSlippageBps but not separately tracked here.
    recent_avg_slippage_bps: float | None = Field(default=None, alias="recentAvgSlippageBps")
    lifetime_avg_slippage_bps: float | None = Field(default=None, alias="lifetimeAvgSlippageBps")
    recent_drawdown_usd: float | None = Field(default=None, alias="recentDrawdownUsd")
    consecutive_losses: int = Field(alias="consecutiveLosses")
    recent_invalidation_count: int = Field(alias="recentInvalidationCount")


class StrategyDegradationSummary(CamelModel):
    reads: list[StrategyDegradationRead]
    recent_window_size: int = Field(alias="recentWindowSize")
    min_sample_for_verdict: int = Field(alias="minSampleForVerdict")
    updated_at: str = Field(alias="updatedAt")


# CEO directive "Next Professional Trading Firm Phase," Priority 5 —
# Research Data Integrity (app/data_provenance.py). Distinct from, and
# reusing rather than duplicating, `DataStatus` above (which already
# tags an individual `Candle`'s own live/delayed/historical/simulated/
# stale/error/no_data read) — `DataCategory` classifies a whole
# SUBSYSTEM's data source, the coarser question this directive actually
# asks ("what category did this research result come from"). RESEARCH
# FINDING that shaped this scope: `app/research.py`'s confidence gauge
# and `app/simulation.py`'s backtest metrics both never call
# `MarketDataProvider.get_candles()` at all — a per-`ResearchItem`/
# `SimulationResult` provenance field would therefore be fabricated if
# it claimed any candle-derived category, so this ships as one honest,
# whole-codebase audit report instead of a per-item field grafted onto
# systems that don't touch real (or simulated) price data in the first
# place.
DataCategory = Literal["real", "synthetic", "simulated", "user_provided", "unavailable"]


class DataSourceRead(CamelModel):
    """One named subsystem's real, disclosed data category.
    `reproducible` / `coverage_pct` are `None` when not meaningfully
    applicable to that subsystem (e.g. a `synthetic` source has no
    "coverage" of a price series that was never fetched)."""

    subsystem: str
    category: DataCategory
    detail: str
    reproducible: bool | None = None
    coverage_pct: float | None = Field(default=None, alias="coveragePct")


class DataProvenanceReport(CamelModel):
    """The whole-codebase audit: every named subsystem that could
    plausibly back a trading decision, and which of REAL/SYNTHETIC/
    SIMULATED/USER_PROVIDED/UNAVAILABLE its actual data source is.
    `sources` is a fixed architectural enumeration (this codebase's
    module boundaries, not live game state), except the "Live Quotes &
    Candles" row's `coveragePct`/`category`, which are live-measured
    against the currently-configured `MarketDataProvider` on every
    request — never a hardcoded assumption about what the provider
    would return."""

    sources: list[DataSourceRead]
    updated_at: str = Field(alias="updatedAt")


# CEO directive "Next Phase: Professional Trading Firm Intelligence,"
# Phase 1 — Symbol -> Agent Attribution (app/trade_attribution.py).
# RESEARCH FINDING that shaped this scope: no P&L credit-splitting
# methodology exists anywhere in this codebase, and the directive itself
# explicitly forbids inventing one unilaterally ("do not arbitrarily
# assign 100% credit to the agent that clicked BUY/SELL... surface that
# a CEO credit-split rule is required instead of silently inventing
# one"). What this module builds instead, per the directive's own
# fallback instruction ("preserve the original attribution evidence so
# that attribution can be audited later"): a real, non-fabricated
# per-trade EVIDENCE record — which agent/role voted what, whether that
# vote matched the side actually traded, real risk/CEO-override
# provenance, and the trade's real execution/P&L — joined entirely from
# data this codebase already permanently stores (TradeDecision.votes,
# CeoDecisionRecord, PaperTrade). No numeric P&L-per-agent split is
# computed or implied anywhere in this record.
class AgentContributionRead(CamelModel):
    """One analyst's real, permanently-recorded vote on this trade's
    original proposal, reconstructed from `TradeDecision.votes` (role
    inferred via the fixed `ROLE_TO_AGENT` mapping in app/executive.py
    — the same six real seats Executive Voting already uses)."""

    agent_id: AgentId = Field(alias="agentId")
    role: AnalystRole
    choice: VoteChoice
    reason: str
    agreed_with_side_traded: bool = Field(alias="agreedWithSideTraded")


TradeAttributionEvidenceState = Literal["full_evidence", "no_decision_on_record"]

# CEO directive "Live Trade -> Strategy Provenance" — the real,
# three-way status this codebase can honestly distinguish for a closed
# trade's strategy attribution (see app/trade_attribution.py's own
# compute_trade_attribution() for exactly how each is derived):
#   - "known": a real matching CeoDecisionRecord exists AND the CEO
#     explicitly selected a real strategy at the moment of deciding.
#   - "unknown": a real matching CeoDecisionRecord exists, but no
#     strategy was ever selected for it — true for every trade before
#     this feature existed, and for every trade where the CEO simply
#     didn't pick one. NOT a fabricated middle state — it means exactly
#     what the CEO's own real record says (nothing).
#   - "unavailable": no matching CeoDecisionRecord/TradeDecision can be
#     found at all (evicted from the capped decisions/ceoDecisions
#     lists — the same disclosed edge case `evidence_state`'s own
#     "no_decision_on_record" already covers).
TradeStrategyProvenanceState = Literal["known", "unknown", "unavailable"]


class TradeAttributionRecord(CamelModel):
    """One closed trade's real, auditable evidence trail. `evidenceState`
    is `no_decision_on_record` (contributions/ceo fields empty/None)
    only when `PaperTrade.decisionId` never resolved to a real
    `TradeDecision` — never fabricated to fill the gap. `credit_split_
    note` is a fixed, honest disclosure — see this module's own
    docstring for why no numeric split exists. `strategyProvenanceState`
    is the strongest honest claim this codebase's architecture can
    support for strategy attribution — see `TradeStrategyProvenanceState`
    above for exactly what each value means and why there is no
    fabricated "the strategy caused this trade" state."""

    trade_id: str = Field(alias="tradeId")
    decision_id: str | None = Field(default=None, alias="decisionId")
    symbol: str
    contributions: list[AgentContributionRead] = Field(default_factory=list)
    supporting_agents: list[AgentId] = Field(default_factory=list, alias="supportingAgents")
    opposing_agents: list[AgentId] = Field(default_factory=list, alias="opposingAgents")
    ceo_choice: AnalystChoice | None = Field(default=None, alias="ceoChoice")
    ceo_overrode_the_desk: bool | None = Field(default=None, alias="ceoOverrodeTheDesk")
    gatekeeper_approved: bool | None = Field(default=None, alias="gatekeeperApproved")
    entry_slippage_bps: float = Field(alias="entrySlippageBps")
    exit_slippage_bps: float = Field(alias="exitSlippageBps")
    transaction_cost_usd: float = Field(alias="transactionCostUsd")
    pnl: float
    pnl_pct: float = Field(alias="pnlPct")
    evidence_state: TradeAttributionEvidenceState = Field(alias="evidenceState")
    credit_split_note: str = Field(alias="creditSplitNote")
    strategy_id: str | None = Field(default=None, alias="strategyId")
    strategy_provenance_state: TradeStrategyProvenanceState = Field(alias="strategyProvenanceState")


class TradeAttributionSummary(CamelModel):
    records: list[TradeAttributionRecord]
    updated_at: str = Field(alias="updatedAt")


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


# Design Bible Chapter 69 Part 1 — Multi-Account & Fund Management
# System. `PaperPortfolio` above (the company's one trading account) and
# `TreasuryState` (the CEO's own isolated capital) were this chapter's
# real precedent for genuine capital-pool isolation; `Account` below is
# the honest generalization of that same pattern to more than two pools.
AccountType = Literal["personal", "ira", "business", "prop_firm", "family"]


class Account(CamelModel):
    """One real, isolated capital pool beyond the company's primary
    PaperPortfolio — its own cash, positions, trade history (embedding a
    real PaperPortfolio rather than duplicating its fields, so every
    existing function that already operates on a PaperPortfolio, like
    app/risk_engine.py's portfolio_equity(), works on an Account's
    portfolio for free), and its own editable RiskLimits profile.

    Honest scope for this pass (see app/accounts.py's module docstring):
    a real, CEO-manageable capital ledger — create an account, allocate/
    deallocate real capital between it and the Treasury, track its own
    equity over time. Live trading execution (new TradeProposals opening
    positions IN a specific non-primary account) is not wired yet — that
    would mean parameterizing the entire trading pipeline (proposals,
    the Trade Gatekeeper, Sentinel/Guardian) by account, a materially
    larger change than this pass makes, and named honestly in this
    chapter's Future Expansion rather than silently assumed."""

    id: str
    name: str
    account_type: AccountType = Field(alias="accountType")
    portfolio: PaperPortfolio
    risk_limits: RiskLimits = Field(alias="riskLimits")
    created_at: str = Field(alias="createdAt")
    # Design Bible Chapter 69 Part 2 — Prop Firm Rule Engine. Real,
    # optional fields every account carries (not prop-firm-exclusive —
    # a Business or Family account could set a challenge window too),
    # left unset (None) for accounts that never configure them, never
    # defaulted to a fabricated value. `peak_equity` starts equal to the
    # account's own starting balance and only ever moves up (see
    # app/prop_firm.py's update_peak_equity()) — the real high-water
    # mark a trailing-drawdown check trails from, grep-confirmed absent
    # anywhere in this codebase before this field existed.
    peak_equity: float = Field(alias="peakEquity")
    trailing_drawdown_limit_pct: float | None = Field(default=None, alias="trailingDrawdownLimitPct")
    consistency_limit_pct: float | None = Field(default=None, alias="consistencyLimitPct")
    challenge_start_sim_day: int | None = Field(default=None, alias="challengeStartSimDay")
    challenge_duration_days: int | None = Field(default=None, alias="challengeDurationDays")
    challenge_profit_target_pct: float | None = Field(default=None, alias="challengeProfitTargetPct")
    # Design Bible Chapter 69 Part 3 — Institutional Rule Engine. This
    # account's own real Custom Rules, evaluated by the one centralized
    # app/rule_engine.py rather than a second, account-specific
    # enforcement path — see that module's own docstring.
    custom_rules: list[Rule] = Field(default_factory=list, alias="customRules")
    # Prop-Firm Risk Intelligence Addendum, Piece 10a, Requirement 24 —
    # real, CEO-recorded evaluation-cost / funded-stage / payout data.
    # Every field is optional/defaulted so an account created before this
    # piece still validates during load; none is ever auto-derived from a
    # probability model (that's Piece 10's job) — these are only ever
    # set by an explicit CEO action (app/accounts.py's
    # configure_evaluation_tracking/mark_account_funded/record_account_payout).
    evaluation_cost: float | None = Field(default=None, alias="evaluationCost")
    funded_stage_reached: bool = Field(default=False, alias="fundedStageReached")
    funded_at_sim_day: int | None = Field(default=None, alias="fundedAtSimDay")
    payout_eligibility_min_profit_pct: float | None = Field(default=None, alias="payoutEligibilityMinProfitPct")
    total_payouts_received: float = Field(default=0.0, alias="totalPayoutsReceived")


# Design Bible Chapter 69 Part 2 — the Weekday-Aware Time System. Real,
# derived infrastructure, not a Prop Firm-specific add-on (see
# app/prop_firm.py's weekday_for()): TimeState.day is grep-confirmed to
# have no epoch/calendar anchor anywhere in this codebase before this —
# day 1 is defined as a Monday, a real, documented, deterministic choice,
# never a stored/driftable field.
Weekday = Literal["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


class TrailingDrawdownStatus(CamelModel):
    """A real, second, genuinely new computation alongside RiskLimits.
    maxDrawdownPct's existing real check — that one compares current
    equity to the account's starting balance (fixed floor); this one
    compares current equity to the account's own peak_equity (a moving
    high-water mark), the defining feature of a real trailing-drawdown
    rule the brief asked for and this codebase never had."""

    peak_equity: float = Field(alias="peakEquity")
    current_equity: float = Field(alias="currentEquity")
    drawdown_pct: float = Field(alias="drawdownPct")
    limit_pct: float | None = Field(alias="limitPct")
    breached: bool


class ConsistencyStatus(CamelModel):
    """Compares one closed trading day's real P&L against the challenge
    window's own real cumulative P&L (both derived from the account's
    real PaperTrade history, never fabricated) — the "no single day >X%
    of total profit" shape most real prop firms use, and which this
    codebase never had any comparison for before this."""

    applicable: bool
    cumulative_profit: float = Field(alias="cumulativeProfit")
    largest_single_day_profit: float = Field(alias="largestSingleDayProfit")
    largest_single_day_share_pct: float = Field(alias="largestSingleDaySharePct")
    limit_pct: float | None = Field(alias="limitPct")
    breached: bool


class ScalingMilestoneStatus(CamelModel):
    """A real, computed growth-tier read off the account's own real
    equity vs. its own starting balance — no funded-account
    growth-stage concept existed anywhere in this codebase before this."""

    current_tier: int = Field(alias="currentTier")
    equity_growth_pct: float = Field(alias="equityGrowthPct")
    next_tier_growth_threshold_pct: float | None = Field(alias="nextTierGrowthThresholdPct")


class ChallengeProgressStatus(CamelModel):
    """Real only once the CEO has actually configured a challenge window
    on this account (challenge_start_sim_day set) — `applicable=False`
    otherwise, never a fabricated progress reading for an account that
    was never given a challenge to track."""

    applicable: bool
    started_sim_day: int | None = Field(alias="startedSimDay")
    duration_days: int | None = Field(alias="durationDays")
    days_elapsed: int = Field(alias="daysElapsed")
    days_remaining: int | None = Field(alias="daysRemaining")
    profit_pct: float = Field(alias="profitPct")
    target_pct: float | None = Field(alias="targetPct")
    on_pace: bool | None = Field(alias="onPace")


# Design Bible Chapter 69 Part 2 — Prop Firm Compliance Score. This
# codebase's own "no black-box composite" convention (Chapter 66's own
# Decision Logic section) means every input is published, not hidden —
# see app/prop_firm.py's compute_compliance_score() for the exact,
# equal-weighted formula (never a hidden blend, same convention
# CompanyHealth.overall already established).
class PropFirmComplianceScore(CamelModel):
    overall: float
    drawdown_safety: float = Field(alias="drawdownSafety")
    consistency: float
    rule_compliance: float = Field(alias="ruleCompliance")
    risk_exposure: float = Field(alias="riskExposure")
    capital_preservation: float = Field(alias="capitalPreservation")


class PropFirmStatus(CamelModel):
    """The combined, computed-fresh (never persisted — same convention
    as ExecutiveRecommendation/WhatIfSimulation) real read behind the
    brief's own Prop Firm Dashboard, for one account."""

    account_id: str = Field(alias="accountId")
    weekday: Weekday
    trailing_drawdown: TrailingDrawdownStatus = Field(alias="trailingDrawdown")
    consistency: ConsistencyStatus
    scaling: ScalingMilestoneStatus
    challenge: ChallengeProgressStatus
    compliance_score: PropFirmComplianceScore = Field(alias="complianceScore")
    # Prop-Firm Risk Intelligence Addendum, Piece 11 — risk measured
    # against this account's real failure boundary, not notional size.
    risk_budget: "AccountRiskBudgetStatus" = Field(alias="riskBudget")
    # Prop-Firm Risk Intelligence Addendum, Piece 10a — evaluation cost,
    # funded-stage, and payout tracking.
    evaluation_tracking: "EvaluationTrackingStatus" = Field(alias="evaluationTracking")
    # The Leverage System (addendum item 3) has no real foundation to
    # extend — this codebase is a 100%-cash, long-only paper account
    # with no margin field anywhere (confirmed by Chapter 68's own
    # research). Stated honestly here rather than fabricating a number.
    leverage_note: str = Field(alias="leverageNote")


# Design Bible Chapter 69 Part 3 — Institutional Rule Engine (IRE).
# Grep-confirmed before this: no Rule/RuleProfile/RuleEngine class
# existed anywhere in this codebase. Deliberately a closed, named set of
# rule types rather than a free-text DSL or natural-language parser —
# the honest scope this Design Bible's own research settled on: real,
# CEO-authored, data-driven rules (no code change needed to add one),
# while preserving the same transparent, individually-inspectable check
# per rule the existing hardcoded RiskLimits checks already have (this
# codebase's "no black-box composite" convention, restated once more
# here because it's the one principle a rule engine must not break).
# `trailing_drawdown_pct`/`consistency_pct` reuse Part 2's own real
# app/prop_firm.py computations; `no_trading_on_weekday` reuses Part 2's
# own real weekday_for() — never a second, competing computation.
RuleType = Literal[
    "max_daily_loss_pct",
    "max_drawdown_pct",
    "max_position_pct",
    "max_open_positions",
    "max_risk_per_trade_pct",
    "trailing_drawdown_pct",
    "consistency_pct",
    "no_trading_on_weekday",
]


class Rule(CamelModel):
    """One real, structured, CEO-authored rule — the honest shape of
    this codebase's Custom Rule Builder (see app/rule_engine.py's module
    docstring for exactly which of the brief's six named examples this
    does and doesn't cover). `limit` is unused (0) for
    `no_trading_on_weekday`, which instead reads `weekday`; every other
    rule type reads `limit` and ignores `weekday`."""

    id: str
    rule_type: RuleType = Field(alias="ruleType")
    label: str
    limit: float = 0.0
    weekday: Weekday | None = None
    enabled: bool = True


class RuleCheckResult(CamelModel):
    rule_id: str = Field(alias="ruleId")
    label: str
    passed: bool
    detail: str
    # Real only when a check actually fails — a static, per-rule-type
    # corrective-action template (see app/rule_engine.py's
    # CORRECTIVE_ACTIONS), never a fabricated AI-generated suggestion.
    corrective_action: str | None = Field(default=None, alias="correctiveAction")


class RuleEvaluationResult(CamelModel):
    """The Institutional Rule Engine's real, computed-fresh (never
    persisted — same convention as ExecutiveRecommendation/WhatIf)
    output for one account: every enabled custom rule, checked
    individually and transparently, never combined into a hidden
    composite pass/fail."""

    account_id: str = Field(alias="accountId")
    sim_day: int = Field(alias="simDay")
    checks: list[RuleCheckResult] = Field(default_factory=list)
    all_passed: bool = Field(alias="allPassed")


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
    stage_history: list[StrategyStageEvent] = Field(
        default_factory=list, alias="stageHistory"
    )
    # A real, CEO-chosen authorization ceiling set on entering
    # limited_live_capital (POST /api/sandbox/begin-limited-live) — see
    # app/sandbox.py's module docstring for why this is a tracked
    # commitment number, not fabricated live P&L attribution.
    allocated_capital: float = Field(default=0.0, alias="allocatedCapital")
    # CEO directive "Strategy Intelligence + Live Strategy Attribution" —
    # closes a real identity split this repo's own architecture audit
    # surfaced: the stage-gated `Strategy` (this class — dossier/
    # certification/health-tracked) and the rule-bearing
    # `CompiledStrategyDefinition` (app/strategy_compiler.py's real,
    # deterministic trigger/requirement/entry/stop/target sequence) were
    # two disconnected identity spaces — a `Strategy` had no way to say
    # which compiled rules, if any, it actually represents. `None` means
    # exactly what it always meant before this field existed: this
    # Strategy has no represented executable logic yet (true for the
    # four original seed strategies, which are real tracked ideas with a
    # focus category but no compiled trigger/entry/stop/target sequence
    # backing them). See app/strategy_registry.py's
    # register_researchable_strategy() for the one real way this field
    # gets set — never a caller-supplied arbitrary string.
    compiled_definition_id: str | None = Field(default=None, alias="compiledDefinitionId")


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
    """This class has two real producers with two different honesty
    stories for sharpe_ratio/sortino_ratio. `app/simulation.py`'s RNG-only
    Monte Carlo engine has no real per-trade return sequence at all, so
    its sharpe_ratio/sortino_ratio remain an explicitly disclosed
    placeholder return-to-drawdown ratio — real risk-adjusted-return math
    needs a real historical data source that engine does not have (see
    app/market_data.py). `app/strategy_engine.py`'s compiled-strategy
    backtest (CEO directive "Professional Quant Firm Phase," Feature 38)
    DOES have a real per-symbol closed-trade R-multiple sequence, so its
    sharpe_ratio/sortino_ratio here are real — reused directly from
    `app/backtest_primitives.py`'s `aggregate_bucket()` (the one
    authoritative bucket-statistics implementation, same formulas as
    `app/analytics.py`), falling back to 0.0 only in the honest
    zero-variance edge case (every closed trade realized the identical
    R-multiple), never a fabricated nonzero figure. v0.7 Feature 45 adds
    win_count/loss_count/avg_win_pct/avg_loss_pct as the placeholder
    engine's own real generating inputs (total_return_pct is now derived
    FROM them, not the reverse — see app/simulation.py), so
    expected_value_pct/profit_factor/risk_reward_ratio below are real,
    internally-consistent derivations of this run's own numbers, never
    independently invented."""

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
    failure_conditions: list[str] = Field(
        default_factory=list, alias="failureConditions"
    )
    best_market_environment: str = Field(alias="bestMarketEnvironment")
    recommended_improvements: list[str] = Field(
        default_factory=list, alias="recommendedImprovements"
    )
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


# v0.7 Feature 45 — the Company Review stage's five real reviewer
# verdicts (Quant/Risk Specialist/Technical Analyst/Fundamental Analyst/
# Devil's Advocate), each computed from that strategy's own real,
# aggregated SimulationResult and ResearchItem history — see
# app/sandbox.py's generate_strategy_review().
StrategyReviewerRole = Literal[
    "quant", "risk", "technical", "fundamental", "devils_advocate"
]
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
    ceo_decision: Literal["pending", "approved", "rejected"] = Field(
        default="pending", alias="ceoDecision"
    )
    resolved_by: Literal["ceo", "auto"] | None = Field(default=None, alias="resolvedBy")
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


# v0.7 — Quantitative Research & Intelligence System, Piece 4: the Model
# Validator (Meridian/CIO). See app/model_validation.py's module
# docstring for the full honesty boundary. Every check below reuses data
# a different real system already computed (Monte Carlo bootstrap,
# regime test, liquidity validation, expectancy) against an existing,
# already-load-bearing threshold — never a new fabricated statistic.
ModelValidationVerdict = Literal[
    "approved", "rejected", "needs_more_evidence", "not_validatable"
]


class ModelValidationCheck(CamelModel):
    """`passed=None` means this check could not be evaluated yet (e.g.
    the underlying artifact — Monte Carlo/regime test/liquidity
    validation — doesn't exist for this strategy yet) — never silently
    coerced to pass or fail. `threshold_source` always cites exactly
    which existing constant/pattern this check reused; it is never
    blank, since Piece 4 introduces no new numeric bar of its own."""

    id: str
    label: str
    passed: bool | None
    evidence: str
    reasoning: str
    threshold_source: str = Field(alias="thresholdSource")


class ModelValidationReport(CamelModel):
    """Meridian/CIO's independent validation sign-off for one Company
    Review cycle (see app/model_validation.py). Advisory-only: nothing
    in app/sandbox.py's apply_review_decision()/begin_company_review()
    control flow reads `verdict` — it is generated and surfaced purely
    for CEO visibility alongside the matching StrategyReview. This
    codebase has no strategy version-number concept, so
    `existing_review_count` (the same count that already drives that
    cycle's Devil's Advocate rotation assignment) is the honest
    substitute audit-trail/reproducibility field, not a fabricated
    version number."""

    id: str
    strategy_id: str = Field(alias="strategyId")
    strategy_name: str = Field(alias="strategyName")
    review_id: str = Field(alias="reviewId")
    existing_review_count: int = Field(alias="existingReviewCount")
    verdict: ModelValidationVerdict
    checks: list[ModelValidationCheck]
    validator_agent_id: Literal["cio"] = Field(
        default="cio", alias="validatorAgentId"
    )
    evidence_summary: str = Field(alias="evidenceSummary")
    # Plain statement of what real data each check drew on and, just as
    # importantly, what this report does NOT independently establish —
    # Meridian reviews and challenges the same computed evidence
    # Vector's research and Sentinel/Guardian/Keystone's risk review also
    # draw on; it does not re-derive statistics from a separate raw-data
    # pipeline (none exists). The independence that's real here is
    # organizational/decision independence, not statistical
    # independence — see app/model_validation.py's module docstring.
    data_sources_and_assumptions: list[str] = Field(
        default_factory=list, alias="dataSourcesAndAssumptions"
    )
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
    supporting_evidence: list[str] = Field(
        default_factory=list, alias="supportingEvidence"
    )
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
    agent_rankings: list[AgentScore] = Field(
        default_factory=list, alias="agentRankings"
    )
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
    """sharpe_ratio/sortino_ratio (Quantitative Research & Intelligence
    System, Piece 3) are REAL statistics — mean/population-stdev and
    mean/downside-deviation over PaperPortfolio.trade_history's own
    real, sequential per-trade pnl_pct returns (see
    app/analytics.py's compute_performance_snapshot()) — not the
    fabricated formula SimulationResult's own same-named fields still
    use. Two disclosed simplifications, not fabrications: risk-free
    rate assumed 0 (no bond/cash-yield concept exists in this
    codebase), and these are per-trade ratios, not annualized (trades
    close at irregular sim-minute intervals, so there is no real
    fixed-period return series to normalize against)."""

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


class TierAllocationLimits(CamelModel):
    """The CEO's own per-tier ceiling, each a % of equity — real caps
    app/position_sizing.py's tier assignment must respect alongside the
    existing max_position_pct/risk_per_trade_pct ceiling (the smaller of
    the two always wins, the same convention recommended_quantity()
    already established). Defaults are conservative but arbitrary, the
    same honest note RiskLimits' own docstring already makes."""

    tier1_pct: float = Field(default=2.0, alias="tier1Pct")
    tier2_pct: float = Field(default=5.0, alias="tier2Pct")
    tier3_pct: float = Field(default=8.0, alias="tier3Pct")
    tier4_pct: float = Field(default=10.0, alias="tier4Pct")


class RiskLimits(CamelModel):
    """Sentinel's configurable risk boundaries (v0.6 brief, Risk Engine).
    Defaults are conservative but arbitrary — there's no real capital or
    regulatory requirement behind them, they exist purely to give Sentinel
    something concrete to check a trade candidate against."""

    max_position_pct: float = Field(default=10.0, alias="maxPositionPct")
    max_daily_loss_pct: float = Field(default=5.0, alias="maxDailyLossPct")
    max_drawdown_pct: float = Field(default=20.0, alias="maxDrawdownPct")
    max_open_positions: int = Field(default=8, alias="maxOpenPositions")
    max_sector_concentration_pct: float = Field(
        default=30.0, alias="maxSectorConcentrationPct"
    )
    # CEO directive "Portfolio Construction, Capital Allocation &
    # Execution Realism," Phase 4 — promotes app/gatekeeper.py's
    # previously-hardcoded MAX_CORRELATED_POSITIONS (always 2) to a real
    # CEO-configurable limit, a gap that codebase's own opportunity_
    # gatekeeper.py module docstring already named. Default of 2
    # preserves today's real behavior exactly — this is a promotion, not
    # a silent behavior change. Consumed by TWO real, complementary
    # checks: app/gatekeeper.py's existing category-co-occurrence read
    # (post-CEO-decision) and app/opportunity_gatekeeper.py's new real
    # Pearson-correlation-based read (pre-proposal) — the same one real
    # threshold, two already-real detection methods at the two stages
    # this pipeline already has, never a second competing limit.
    max_correlated_positions: int = Field(default=2, alias="maxCorrelatedPositions")
    risk_per_trade_pct: float = Field(default=2.0, alias="riskPerTradePct")
    # v0.7 Feature 49 — Professional Day Trading Program's Daily Trading
    # Objectives. `max_daily_loss_pct` above already existed; these two
    # are new. Both are enforced the same way as every other limit here
    # (app/risk_engine.py's evaluate_sentinel_risk) — never a separate
    # mechanism.
    daily_profit_target_pct: float = Field(default=3.0, alias="dailyProfitTargetPct")
    max_trades_per_day: int = Field(default=6, alias="maxTradesPerDay")
    # Design Bible Chapter 67 (TTOS)'s Safety Settings — the second and
    # third real circuit breakers, enforced the exact same way as
    # max_daily_loss_pct above (app/risk_engine.py's
    # evaluate_sentinel_risk), just scoped to the current sim week/month
    # instead of the current sim day. Defaults sit between the daily
    # (5%) and lifetime drawdown (20%) limits — each wider scope allows
    # more cumulative loss before it fires, but still well inside the
    # lifetime cap.
    max_weekly_loss_pct: float = Field(default=10.0, alias="maxWeeklyLossPct")
    max_monthly_loss_pct: float = Field(default=15.0, alias="maxMonthlyLossPct")
    # v0.7 Chapter 57 — Institutional Position Sizing & Capital Deployment
    # Engine (app/position_sizing.py). All six new CEO controls that
    # engine's own Design Bible chapter asks for; every existing field
    # above stays exactly as-is, this engine only ever narrows what it's
    # already allowed to size, never widens it.
    max_weekly_deployment_pct: float = Field(
        default=15.0, alias="maxWeeklyDeploymentPct"
    )
    # None = no hard cap (today's behavior — Portfolio Heat stays a pure
    # reading, per Chapter 56's own honesty boundary). A real number is a
    # CEO-set, CEO-triggered ceiling, never a system-triggered one — see
    # app/position_sizing.py's module docstring for why that stays inside
    # the v0.8 stop condition.
    portfolio_heat_cap_pct: float | None = Field(
        default=None, alias="portfolioHeatCapPct"
    )
    cash_reserve_pct: float = Field(default=10.0, alias="cashReservePct")
    tier_allocation: TierAllocationLimits = Field(
        default_factory=TierAllocationLimits, alias="tierAllocation"
    )
    scaling_aggressiveness_pct: float = Field(
        default=100.0, alias="scalingAggressivenessPct"
    )
    emergency_reduction_heat_pct: float = Field(
        default=75.0, alias="emergencyReductionHeatPct"
    )
    # v0.7 Chapter 58 — Institutional Trade Filter & Opportunity
    # Gatekeeper (app/opportunity_gatekeeper.py). The two real CEO
    # controls that engine's own Design Bible chapter asks for; default
    # values match the fixed constants they replace (app/war_room.py's
    # own DECISION_SCORE_THRESHOLD stays exactly as-is for its existing
    # consumers — this is a genuinely separate, CEO-adjustable gate, not
    # a change to that constant's own semantics).
    min_trade_quality_score: float = Field(default=70.0, alias="minTradeQualityScore")
    min_expected_value_pct: float = Field(default=0.0, alias="minExpectedValuePct")
    # v0.7 Chapter 59 — Capital Priority & Opportunity Cost Engine
    # (app/capital_priority.py). Two real CEO controls that engine's own
    # Design Bible chapter asks for. Both default to 0 (no-op): unlike
    # Chapter 58's min_trade_quality_score, which matched an existing
    # fixed constant, neither of these replaces prior behavior — they're
    # opt-in floors the CEO raises above zero to actually engage them.
    min_priority_score: float = Field(default=0.0, alias="minPriorityScore")
    capital_reserve_pct: float = Field(default=0.0, alias="capitalReservePct")
    # v0.7 Design Bible Chapter 61 — Institutional Knowledge Graph &
    # Company Memory Engine's "Pattern Detection Sensitivity" CEO
    # control. Both defaults match the fixed constants they replace
    # (app/decision_vault.py's MIN_SIMILAR_MATCHES/MISTAKE_WARNING_SHARE)
    # so existing behavior is unchanged until the CEO adjusts them —
    # the same "default preserves prior behavior" pattern Chapter 58's
    # min_trade_quality_score already established.
    min_similar_matches: int = Field(default=3, alias="minSimilarMatches")
    mistake_warning_share_pct: float = Field(default=30.0, alias="mistakeWarningSharePct")
    # v0.7 Design Bible Chapter 61's "Knowledge Retention Rules" CEO
    # control, both slices. Both defaults match the fixed constants they
    # replace (app/decision_vault.py's MAX_DECISION_VAULT_ENTRIES,
    # app/memory.py's MAX_MEMORY_RECORDS) so existing behavior is
    # unchanged until the CEO adjusts them.
    max_decision_vault_entries: int = Field(default=200, alias="maxDecisionVaultEntries")
    max_memory_records: int = Field(default=200, alias="maxMemoryRecords")
    # v0.7 Design Bible Chapter 62's "Innovation Budget" CEO control
    # (Institutional Innovation Lab & Continuous Improvement Engine).
    # Default matches the fixed constant it replaces
    # (app/sandbox.py's MAX_LIMITED_LIVE_CAPITAL) so existing behavior is
    # unchanged until the CEO adjusts it.
    max_limited_live_capital: float = Field(default=2000.0, alias="maxLimitedLiveCapital")
    # v0.7 Design Bible Chapter 63 — Executive Performance & Company
    # Health Engine's "Company Health tier thresholds" CEO control. All
    # four defaults match the fixed constants they replace
    # (app/company_health.py's _TIER_THRESHOLDS) so existing behavior —
    # including the Founders' real "excellent" Legendary Status trigger
    # — is unchanged until the CEO adjusts them. Validated together (see
    # app/state.py's update_risk_limits) to always stay strictly
    # descending, since they classify the same score into one of four
    # tiers in order.
    company_health_excellent_threshold: float = Field(default=85.0, alias="companyHealthExcellentThreshold")
    company_health_good_threshold: float = Field(default=70.0, alias="companyHealthGoodThreshold")
    company_health_stable_threshold: float = Field(default=50.0, alias="companyHealthStableThreshold")
    company_health_needs_attention_threshold: float = Field(default=30.0, alias="companyHealthNeedsAttentionThreshold")


# CEO directive "Professional Quant Firm Phase 41-45" — Critical Task #0's
# No-Trade Reason Taxonomy. Every value below is grounded in one real,
# already-existing rejection point this codebase's own real trade-flow
# pipeline actually reaches (see app/no_trade_taxonomy.py's own module
# docstring for the full stage-by-stage citation) — never an invented
# category. Several of the directive's own example categories
# (SESSION_FILTER, MARKET_CLOSED, STALE_DATA, EXECUTION_REJECTION,
# ORDER_REJECTED, STRATEGY_DISABLED, AGENT_DISABLED, MODEL_UNCERTAINTY,
# INVALIDATED_SETUP, COOLDOWN as distinct from duplicate_signal) have NO
# real mechanism in this codebase (a 24/7 mock market has no real
# "closed" state; the live execution path fills instantly with no
# order-book rejection step — see app/broker.py's own disclosed
# "confirmed unused" status) and are deliberately NOT included here —
# see app/no_trade_taxonomy.py's module docstring for the full disclosed
# gap list rather than fabricating a code for something that can't
# actually happen yet.
NoTradeReasonCode = Literal[
    # Pre-proposal: app/nexus.py's _generate_trade_proposals()
    "no_signal",
    "duplicate_signal",
    "proposal_capacity",
    "data_unavailable",
    "position_sized_to_zero",
    # Opportunity Gatekeeper: app/opportunity_gatekeeper.py's evaluate_opportunity()
    "trade_quality_below_threshold",
    "expected_value_below_threshold",
    "market_quality_avoid_trading",
    "liquidity_confirmation_weak",
    # CEO directive "Command Center + Professional Quant Trading Firm
    # Upgrade" — session as a real, evidence-based live gating reason
    # (Phase 0 had named this an explicit, disclosed gap: "SESSION_FILTER
    # has no real mechanism"). This company's own real Session × Regime
    # win-rate evidence (app/session_evidence.py's
    # compute_session_regime_evidence(), already built for the Academy
    # curriculum) is now also consulted live, at the exact live
    # session+regime pairing app/market_intelligence.py's
    # MarketIntelligenceState already carries at proposal time — never a
    # forecast, only this company's own real closed-trade history.
    "session_regime_unfavorable_evidence",
    # CEO directive "Portfolio Construction, Capital Allocation &
    # Execution Realism," Phase 4 — a real, pre-proposal Pearson
    # correlation read (app/portfolio_intelligence.py's
    # count_correlated_positions()) against currently-held positions,
    # never the crude category-co-occurrence proxy app/gatekeeper.py's
    # own later-stage "gatekeeper_correlation" check still uses.
    "correlated_exposure_too_high",
    # Gatekeeper: app/gatekeeper.py's 11 real checks
    "gatekeeper_confidence",
    "gatekeeper_risk_manager",
    "gatekeeper_agreement",
    "gatekeeper_debate",
    "gatekeeper_exposure",
    "gatekeeper_correlation",
    "gatekeeper_risk_warning",
    "gatekeeper_market_intelligence",
    "gatekeeper_weighted_executive",
    "gatekeeper_behavioral",
    "gatekeeper_failure_boundary",
    # Risk engine: app/risk_engine.py's evaluate_sentinel_risk()/evaluate_guardian_exposure()
    "risk_equity_exhausted",
    "risk_daily_loss_limit",
    "risk_daily_profit_target",
    "risk_weekly_loss_limit",
    "risk_monthly_loss_limit",
    "risk_max_trades_per_day",
    "risk_lifetime_drawdown",
    "risk_max_open_positions",
    "risk_position_size_limit",
    "risk_concentration_limit",
    # Pipeline-level halts: app/nexus.py's block_new_proposals/force_manual_review
    "emergency_stop",
    "circuit_breaker",
    "losing_streak_pause",
    "defensive_mode",
    "force_manual_review",
    # Human/expiry
    "ceo_wait_decision",
    "proposal_expired",
    "ceo_approval_pending",
]


class RiskWarning(CamelModel):
    id: str
    symbol: str
    severity: AlertSeverity
    message: str
    created_at: str = Field(alias="createdAt")
    # CEO directive "Professional Quant Firm Phase 41-45," Critical Task
    # #0 — the real, structured reason code for this exact warning,
    # assigned at the same real branch that built `message` (see
    # app/risk_engine.py). `None` only for the rare pre-existing
    # RiskWarning construction sites this pass did not touch (e.g. a
    # future new check) — never a guessed/parsed-from-text code.
    code: NoTradeReasonCode | None = None


# Design Bible Chapter 67 (TTOS) Part 3 — a real, CEO-triggered halt,
# distinct from RiskLimits above (which are CEO-configured thresholds
# the risk/gatekeeper engines evaluate against) and distinct from
# Chapter 66's `pause_trading` (a computed signal, never CEO-triggerable
# — see app/nexus.py's _apply_operating_mode()). Deliberately minimal: a
# single boolean plus when it was activated, not a parallel "incident"
# object — the real incident record is the MemoryRecord this state
# transition writes (see app/emergency_stop.py), matching this
# codebase's "reuse, don't duplicate" convention rather than inventing a
# second persisted history of the same event.
class EmergencyStopState(CamelModel):
    active: bool = False
    activated_at: str | None = Field(default=None, alias="activatedAt")


# v0.7 Feature 49 — Professional Day Trading Program's Daily Trading
# Objectives. Computed fresh every tick from real PaperTrade history
# (app/risk_engine.py's compute_daily_objective_status), the same
# "derived, recomputed rather than persisted" convention CompanyHealth/
# CompanyDNA already use — never a second, possibly-stale copy of state
# the Gatekeeper's real check already tracks.
class DailyObjectiveStatus(CamelModel):
    sim_day: int = Field(alias="simDay")
    trades_today: int = Field(alias="tradesToday")
    realized_pnl_pct_today: float = Field(alias="realizedPnlPctToday")
    profit_target_reached: bool = Field(alias="profitTargetReached")
    max_loss_reached: bool = Field(alias="maxLossReached")
    max_trades_reached: bool = Field(alias="maxTradesReached")
    trading_halted: bool = Field(alias="tradingHalted")
    halt_reason: str | None = Field(default=None, alias="haltReason")
    updated_at: str = Field(alias="updatedAt")


class RiskBudgetStatus(CamelModel):
    """Prop-Firm Risk Intelligence Addendum, Piece 8 — "the system should
    understand the remaining permissible loss budget" (not just nominal
    account size), surfaced at trade-decision time. Every field here is a
    real value already computed elsewhere in this codebase — lifetime
    drawdown reuses the exact same `portfolio.total_pnl_pct` reading
    app/risk_engine.py's evaluate_sentinel_risk() already gates on;
    today's realized P&L reuses daily_realized_pnl_pct(); the two
    "remaining" fields are the one new arithmetic step (limit minus
    current usage, floored at 0) — packaging, not a new formula. This is
    advisory only: nothing here changes what Sentinel/Guardian/Gatekeeper
    actually enforce, which remains exactly as it was.

    HONEST BOUNDARY (Piece 11, Requirement 23): `max_drawdown_pct` here is
    the primary portfolio's own self-chosen ceiling (`RiskLimits`, a
    CEO-configurable setting with no external authority behind it — see
    RiskLimits's own docstring: "conservative but arbitrary"), not a true
    externally-imposed failure boundary the way a real prop-firm
    evaluation's trailing-drawdown rule is. See `AccountRiskBudgetStatus`
    below for the one place this codebase has a genuinely
    externally-configurable boundary (`Account.trailing_drawdown_limit_pct`)
    to measure risk against instead."""

    equity: float
    starting_balance: float = Field(alias="startingBalance")
    lifetime_drawdown_pct: float = Field(alias="lifetimeDrawdownPct")
    max_drawdown_pct: float = Field(alias="maxDrawdownPct")
    remaining_drawdown_budget_pct: float = Field(alias="remainingDrawdownBudgetPct")
    daily_loss_pct_today: float = Field(alias="dailyLossPctToday")
    max_daily_loss_pct: float = Field(alias="maxDailyLossPct")
    remaining_daily_loss_budget_pct: float = Field(alias="remainingDailyLossBudgetPct")
    daily_profit_pct_today: float = Field(alias="dailyProfitPctToday")
    daily_profit_target_pct: float = Field(alias="dailyProfitTargetPct")
    remaining_to_daily_profit_target_pct: float = Field(alias="remainingToDailyProfitTargetPct")
    trading_halted: bool = Field(alias="tradingHalted")
    halt_reason: str | None = Field(default=None, alias="haltReason")
    # Prop-Firm Risk Intelligence Addendum, Piece 11b — Requirement 24's
    # "number of trading days" data point: a real count of distinct sim
    # days with at least one real closed trade, reusing the exact
    # `closed_sim_minutes // 1440` day-bucketing convention
    # app/prop_firm.py's compute_consistency_status() already established.
    trading_days_count: int = Field(default=0, alias="tradingDaysCount")
    computed_at: str = Field(alias="computedAt")


class AccountRiskBudgetStatus(CamelModel):
    """Prop-Firm Risk Intelligence Addendum, Piece 11 — Requirement 23:
    "risk should be modeled relative to the account's actual failure
    boundary... do NOT treat account notional size as the primary
    definition of usable risk." Unlike `RiskBudgetStatus` above (the
    primary portfolio's self-chosen `RiskLimits.max_drawdown_pct`
    ceiling), `effective_failure_boundary_pct` here is the one real
    externally-configurable boundary an `Account` actually carries —
    `trailing_drawdown_limit_pct` (app/accounts.py's own
    `configure_prop_firm_rules`) — the number a real prop-firm challenge
    would actually disqualify the account for breaching, not a number
    the CEO merely chose as her own risk tolerance.

    Every field that cannot be honestly computed from real data is
    `None`; `not_trackable_reasons` names exactly which requested metric
    and why, each prefixed literally `NOT_TRACKABLE_YET:` (Requirement
    23's own words) rather than silently omitting the field or
    fabricating a number. `risk_per_trade_pct_of_boundary` is always one
    of these for any real `Account` today: no live trade execution
    routes to a secondary Account yet (app/accounts.py's own module
    docstring), so "risk per trade" is not a real, measured quantity for
    one — only a hypothetical could be computed, and this module never
    fabricates a hypothetical as if it were measured.

    "Probability of hitting the failure boundary" and "expected drawdown
    path" (also named in Requirement 23) are deliberately NOT included
    here — both require real forward simulation (Monte Carlo), which
    this status read (a real-time snapshot, the same shape as every
    other function in app/prop_firm.py) does not do. That is Piece 10's
    job (the evaluation-level risk-policy simulator), not a duplicate
    simulation bolted onto this snapshot."""

    account_id: str = Field(alias="accountId")
    equity: float
    starting_balance: float = Field(alias="startingBalance")
    effective_failure_boundary_pct: float | None = Field(default=None, alias="effectiveFailureBoundaryPct")
    current_distance_to_failure_pct: float | None = Field(default=None, alias="currentDistanceToFailurePct")
    remaining_drawdown_budget_pct: float | None = Field(default=None, alias="remainingDrawdownBudgetPct")
    risk_per_trade_pct_of_boundary: float | None = Field(default=None, alias="riskPerTradePctOfBoundary")
    not_trackable_reasons: list[str] = Field(default_factory=list, alias="notTrackableReasons")
    computed_at: str = Field(alias="computedAt")


class ProjectedLossPath(CamelModel):
    """Prop-Firm Risk Intelligence Addendum, Piece 11a — Requirement 23:
    "projected loss after N consecutive losses." A real, deterministic
    forward projection (not a probability — that needs real Monte Carlo,
    which is Piece 10's job), computed by compounding
    `RiskLimits.risk_per_trade_pct` against current equity `n` times —
    the exact same sizing math `recommended_quantity()` already uses,
    just applied forward instead of to one trade. `equity_path[0]` is
    today's real equity; `equity_path[i]` is projected equity after `i`
    consecutive losses. `assumption` states the one real simplification
    this makes explicitly, never silently."""

    starting_equity: float = Field(alias="startingEquity")
    equity_path: list[float] = Field(alias="equityPath")
    consecutive_losses: int = Field(alias="consecutiveLosses")
    risk_per_trade_pct: float = Field(alias="riskPerTradePct")
    projected_loss_pct: float = Field(alias="projectedLossPct")
    assumption: str
    computed_at: str = Field(alias="computedAt")


class EvaluationTrackingStatus(CamelModel):
    """Prop-Firm Risk Intelligence Addendum, Piece 10a — Requirement 24's
    evaluation-cost / funded-stage / payout data points. Every field
    here is either a real CEO-recorded number carried on the Account, or
    a real, directly-derived read off it (e.g. `days_to_fund`) — never a
    system-detected "you passed" judgment. Whether an account has
    reached the funded stage is deliberately left as an explicit CEO
    action (`app/accounts.py`'s `mark_account_funded()`), not an
    automatic pass/fail inferred from the challenge profit target —
    building an honest automatic pass/fail read is Piece 10's job (a
    real evaluation-policy simulator), not this piece's."""

    account_id: str = Field(alias="accountId")
    evaluation_cost: float | None = Field(alias="evaluationCost")
    funded_stage_reached: bool = Field(alias="fundedStageReached")
    funded_at_sim_day: int | None = Field(alias="fundedAtSimDay")
    # None when there's no real challenge_start_sim_day to measure from,
    # or the account hasn't been marked funded yet.
    days_to_fund: int | None = Field(alias="daysToFund")
    payout_eligibility_min_profit_pct: float | None = Field(alias="payoutEligibilityMinProfitPct")
    # None when no threshold is configured — never a fabricated "not
    # eligible" default for an account that was never given a threshold.
    payout_eligible: bool | None = Field(alias="payoutEligible")
    total_payouts_received: float = Field(alias="totalPayoutsReceived")
    computed_at: str = Field(alias="computedAt")


# Quantitative Research & Intelligence System, Requirements 21/22/23/25
# (Piece 10) — the evaluation-level risk-policy simulator. Every policy
# below is an explicit, disclosed HYPOTHESIS to be tested, never adopted
# as truth merely because it appears here (see app/evaluation_simulator.
# py's module docstring for the full disclosure of every assumption this
# makes). "failure_boundary_relative" sizes risk as a real fraction of
# the account's own real trailing-drawdown boundary when one is
# configured — the only policy that varies per-account rather than
# using a fixed risk_per_trade_pct.
EvaluationRiskPolicyId = Literal[
    "conservative", "moderate", "aggressive", "failure_boundary_relative"
]


class EvaluationPolicySimulationResult(CamelModel):
    """One risk policy's real Monte Carlo evaluation-simulation results —
    every field here is a real statistic computed from real simulated
    paths (see app/evaluation_simulator.py's simulate_evaluation_policy()),
    never a fabricated conclusion. Speed (expected_trades_to_pass /
    expected_trading_days_to_pass) is reported alongside failure and
    drawdown risk specifically so a reader can never read "fast" without
    also seeing "at what cost" — per Requirement 25, speed is an
    objective to weigh, never treated here as automatically good."""

    policy_id: EvaluationRiskPolicyId = Field(alias="policyId")
    label: str
    risk_per_trade_pct: float = Field(alias="riskPerTradePct")
    paths_simulated: int = Field(alias="pathsSimulated")
    probability_of_passing_pct: float = Field(alias="probabilityOfPassingPct")
    probability_of_failing_drawdown_pct: float = Field(alias="probabilityOfFailingDrawdownPct")
    probability_of_failing_time_expiry_pct: float = Field(alias="probabilityOfFailingTimeExpiryPct")
    # None when zero simulated paths passed — never a fabricated "0" or
    # infinity standing in for "no real passing paths to average."
    expected_trades_to_pass: float | None = Field(alias="expectedTradesToPass")
    expected_trading_days_to_pass: float | None = Field(alias="expectedTradingDaysToPass")
    expected_cost_to_pass: float | None = Field(alias="expectedCostToPass")
    median_max_drawdown_pct: float = Field(alias="medianMaxDrawdownPct")
    worst_case_max_drawdown_pct: float = Field(alias="worstCaseMaxDrawdownPct")
    probability_of_consecutive_loss_streak_pct: float = Field(alias="probabilityOfConsecutiveLossStreakPct")
    consecutive_loss_streak_threshold: int = Field(alias="consecutiveLossStreakThreshold")
    # A simple, disclosed research heuristic (probabilityOfPassingPct
    # divided by medianMaxDrawdownPct) — explicitly NOT presented as a
    # universal or validated risk-adjusted-return formula, only as one
    # comparative signal among the many fields on this object. See
    # Requirement 21's own text: "the system must not conclude that
    # aggressive risk is superior merely because it produces faster
    # passes" — this field is not the sole deciding number.
    risk_adjusted_outcome: float = Field(alias="riskAdjustedOutcome")
    # Requirement 21's "sensitivity to strategy quality" — the same
    # simulation rerun at a real, disclosed win-rate delta (see
    # STRATEGY_QUALITY_SENSITIVITY_DELTA_PP) to show how much the pass
    # probability actually depends on the input strategy being good.
    probability_of_passing_at_lower_quality_pct: float = Field(alias="probabilityOfPassingAtLowerQualityPct")
    probability_of_passing_at_higher_quality_pct: float = Field(alias="probabilityOfPassingAtHigherQualityPct")


class EvaluationPolicyComparisonReport(CamelModel):
    """Requirement 21's research question, answered honestly: "Which
    evaluation-stage risk policy produces the best probability-adjusted
    outcome for reaching and succeeding in the funded stage while
    controlling failure risk and evaluation cost?" This report compares
    real simulated policies side by side and explicitly refuses to
    declare a winner — `conclusion` states the comparative evidence in
    plain language, `assumptions` and `limitations` are never omitted or
    hidden, and no field here claims validated/production status for any
    policy. See app/evaluation_simulator.py's own docstring for the full
    honesty boundary, including what Requirement 21 asked for that this
    piece explicitly does NOT attempt (real per-regime sensitivity;
    downstream funded-stage performance, since Piece 10a's funded-stage
    tracking is CEO-recorded, not linked to simulated paths)."""

    id: str
    strategy_id: str = Field(alias="strategyId")
    strategy_name: str = Field(alias="strategyName")
    account_id: str | None = Field(alias="accountId")
    sample_trade_count: int = Field(alias="sampleTradeCount")
    profit_target_pct: float = Field(alias="profitTargetPct")
    drawdown_limit_pct: float = Field(alias="drawdownLimitPct")
    max_trades: int = Field(alias="maxTrades")
    research_question: str = Field(alias="researchQuestion")
    policies: list[EvaluationPolicySimulationResult]
    conclusion: str
    assumptions: list[str]
    limitations: list[str]
    sim_day: int = Field(alias="simDay")
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
    supporting_agents: list[AgentId] = Field(
        default_factory=list, alias="supportingAgents"
    )
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
    confidence_engine: "DecisionConfidence | None" = Field(
        default=None, alias="confidenceEngine"
    )
    # v0.7 Feature 20 — the Trade Gatekeeper's final-approval verdict
    # (see app/gatekeeper.py). Only ever set when the CEO chose buy/sell
    # (a WAIT never reaches the gatekeeper); None for decisions predating
    # this field. A rejected verdict here is exactly what makes
    # `order_id` None even though `ceo_choice` on the linked
    # CeoDecisionRecord was buy/sell, not wait.
    gatekeeper_verdict: "GatekeeperVerdict | None" = Field(
        default=None, alias="gatekeeperVerdict"
    )
    # v0.7 Feature 50 (Part 2/3) — the real process-quality Decision Grade
    # (see app/executive.py's compute_decision_grade), set at the moment
    # resolve_proposal() builds this record. None only for decisions that
    # predate this field.
    decision_grade: "DecisionGrade | None" = Field(default=None, alias="decisionGrade")
    decision_grade_score: float | None = Field(default=None, alias="decisionGradeScore")
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
    # v0.7 Feature 49 (Phase 2) — the Liquidity/Market Structure module,
    # orders 11-18. See app/education.py's module docstring for exactly
    # which of these point at a real TradeTown mechanic vs. are honestly
    # disclaimed as conceptual (no order-book/liquidity-pool data exists
    # anywhere in this codebase).
    "liquidity_basics",
    "swing_structure",
    "equal_highs_lows",
    "liquidity_sweeps",
    "inducement",
    "structure_shifts",
    "premium_discount",
    "order_flow_intro",
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
    completed_lesson_ids: list[str] = Field(
        default_factory=list, alias="completedLessonIds"
    )
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
    """One analyst's stance on a trade proposal, with real supporting
    evidence — never a bare choice with no backing. See app/executive.py
    for exactly what data backs each role's vote. NOT every role's vote
    is genuinely independent of the others — see
    app/signal_correlation.py's real, disclosed correlation map (the CEO
    directive "Market-Analysis Knowledge + Session Intelligence
    Expansion," Phase 6, Confluence Engine): news/macro are both driven
    by the same underlying research-item confidence value, and execution
    synthesizes the other five rather than adding new evidence."""

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
    # v0.7 Feature 51 — a one-line real citation of the Market Intelligence
    # Department's current regime/quality read at the moment this proposal
    # was generated (app/market_intelligence.py's MarketIntelligenceState),
    # so every proposal literally carries real market context per the
    # brief's own rule: "No department may recommend a trade without first
    # explaining the current market environment." Defaults to None only
    # for proposals that predate this feature (old saves).
    market_intelligence_summary: str | None = Field(
        default=None, alias="marketIntelligenceSummary"
    )
    # Design Bible Chapter 75 — assigned by app/trading_modes.py's
    # assign_trading_style() the moment this proposal enters
    # trade_proposals (app/nexus.py's tick()), never at construction
    # time here — see that module's own docstring for the deterministic
    # rotation formula. None only for a proposal predating this chapter.
    trading_style: "TradingStyle | None" = Field(default=None, alias="tradingStyle")


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
    historical_comparisons: list[str] = Field(
        default_factory=list, alias="historicalComparisons"
    )
    # One line drawn from the What-If Simulation Lab's own real worst
    # named scenario (app/whatif.py) — never the full simulation, which
    # this codebase has already been bitten once by persisting unbounded
    # computed data (see nexus.py's MAX_DECISIONS history).
    worst_case_scenario: str = Field(alias="worstCaseScenario")
    suggested_improvements: list[str] = Field(
        default_factory=list, alias="suggestedImprovements"
    )
    severity: ChallengeSeverity
    final_recommendation: str = Field(alias="finalRecommendation")
    # v0.7 Feature 47 — Company Operating System's "Real-Time Guidance":
    # real Constitution Article ids this report's own concern buckets map
    # to (see app/constitution.py's articles_for_challenge()), shown
    # inline on the report itself rather than only in the separate
    # enforcement log nexus.py already writes to ConstitutionState.
    cited_article_ids: list[str] = Field(default_factory=list, alias="citedArticleIds")
    created_at: str = Field(alias="createdAt")


# v0.7 Feature 50 — Executive Intelligence Network. Eight named
# "departments," each backed by a real, already-shipped system rather
# than a new one: research.py, the technical/research factors on
# DecisionConfidence (Quant), risk_engine.py + the real gatekeeper checks
# (Risk), the What-If Simulation Lab via ChallengeReport.worstCaseScenario
# (Simulation), DecisionConfidence itself (Decision Intelligence),
# coach.py's CoachReport (Coach), ChallengeReport.historicalComparisons
# (Founders — the real Library of Mistakes titles for this symbol), and
# ChallengeReport itself (Devil's Advocate). See
# app/executive_intelligence.py's module docstring for the full mapping.
# v0.7 Feature 51 adds "market_intelligence" as a ninth department — see
# app/executive_intelligence.py's module docstring for how it plugs into
# the same generic opinion/self-evaluation/meeting-log machinery the
# original eight already use, with zero changes needed to that machinery.
ExecutiveDepartmentRole = Literal[
    "research",
    "quant",
    "risk",
    "simulation",
    "decision_intelligence",
    "coach",
    "founders",
    "devils_advocate",
    "market_intelligence",
]
ExecutiveStance = Literal[
    "agree",
    "disagree",
    "request_more_research",
    "recommend_waiting",
    "recommend_position_change",
    "recommend_rejecting",
]
ExecutiveAction = Literal[
    "trade_normally",
    "reduce_risk",
    "wait",
    "research_more",
    "pause_trading",
    "focus_on_simulation",
]


class DepartmentOpinion(CamelModel):
    role: ExecutiveDepartmentRole
    department_label: str = Field(alias="departmentLabel")
    agent_id: AgentId | None = Field(default=None, alias="agentId")
    stance: ExecutiveStance
    summary: str
    confidence_pct: float = Field(alias="confidencePct")
    # Design Bible Chapter 70 Part 2 — Executive Consensus Meter.
    # Structured, real fields alongside the existing free-text `summary`
    # (kept for every existing consumer) — mirrors
    # StrategyDepartmentOpinion's own real evidence/concerns field
    # pattern (below) rather than inventing a second shape. Populated
    # from each department's own already-real inputs in
    # app/executive_intelligence.py; never fabricated.
    evidence: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    alternative: str | None = Field(default=None)


class ExecutiveRecommendation(CamelModel):
    """The Brain Room's real "combine every perspective" read for one
    pending TradeProposal — computed fresh on request, not persisted
    (same reasoning as WhatIfSimulation: no permanence requirement, and
    every input already lives somewhere permanent — the proposal, its
    ChallengeReport if one exists, the latest CoachReport)."""

    proposal_id: str = Field(alias="proposalId")
    action: ExecutiveAction
    confidence_pct: float = Field(alias="confidencePct")
    reason: str
    supporting: list[ExecutiveDepartmentRole] = Field(default_factory=list)
    opposing: list[ExecutiveDepartmentRole] = Field(default_factory=list)
    opinions: list[DepartmentOpinion] = Field(default_factory=list)
    generated_at: str = Field(alias="generatedAt")
    # Design Bible Chapter 70 Part 2 — Executive Consensus Meter.
    # `consensus_pct` is deliberately a different real number from
    # `confidence_pct` above: the share of departments that plainly
    # AGREE, vs. confidence_pct's average conviction across all of them
    # (a proposal every department "agrees" with at low confidence reads
    # high consensus / low confidence — a real, honest distinction the
    # brief's own example draws between the two numbers). See
    # compute_executive_recommendation() for the exact formula.
    consensus_pct: float = Field(default=0.0, alias="consensusPct")
    # A real, generated (never fabricated) paragraph naming every
    # opposing/hedging department and its own real reason — the
    # "why do executives disagree" the brief asks TradeTown to explain
    # automatically, built entirely from the opinions list above.
    disagreement_summary: str = Field(default="", alias="disagreementSummary")
    # Merged in by the /api/executive/intelligence router from the
    # already-real, already-separate What-If Simulation Lab
    # (app/whatif.py) — never recomputed here, and left None when no
    # real What-If read is available rather than fabricated. This is
    # the brief's Probability of Success / Estimated Return / Estimated
    # Risk row, honestly sourced from the one real system that already
    # computes those three numbers, not a new composite.
    probability_of_success_pct: float | None = Field(default=None, alias="probabilityOfSuccessPct")
    estimated_return_pct: float | None = Field(default=None, alias="estimatedReturnPct")
    estimated_risk_pct: float | None = Field(default=None, alias="estimatedRiskPct")


# v0.7 Feature 50 (Part 2/3) — a real, rule-based process-quality grade
# on every TradeDecision, standard academic scale. Never reads the
# trade's own P&L (see app/executive.py's compute_decision_grade — the
# same "process over outcome" convention app/discipline.py's Discipline
# Score already established), so it's available immediately at decision
# time, not just once a trade closes.
DecisionGrade = Literal[
    "A+", "A", "A-", "B+", "B", "B-", "C+", "C", "C-", "D+", "D", "F"
]


class ExecutiveMeetingLogEntry(CamelModel):
    """v0.7 Feature 50 (Part 2/3) — the Executive Meeting Log. The
    permanent record of one real Executive Intelligence Network
    synthesis: what each department said (the same DepartmentOpinion
    list Part 1's live panel shows), what the network recommended, what
    the CEO actually decided, and whether the two agreed. Generated once
    per real resolve_proposal() call — CEO-driven, auto-resolved, or
    stale-expired — never fabricated or backfilled for old decisions
    that predate this feature."""

    id: str
    proposal_id: str = Field(alias="proposalId")
    symbol: str
    sim_day: int = Field(alias="simDay")
    opinions: list[DepartmentOpinion] = Field(default_factory=list)
    recommended_action: ExecutiveAction = Field(alias="recommendedAction")
    recommendation_reason: str = Field(alias="recommendationReason")
    ceo_decision: AnalystChoice = Field(alias="ceoDecision")
    network_agreed: bool = Field(alias="networkAgreed")
    decision_grade: DecisionGrade = Field(alias="decisionGrade")
    decision_grade_score: float = Field(alias="decisionGradeScore")
    # "delegated" (Design Bible Chapter 70 Part 2) — the CEO explicitly
    # asked the Executive Intelligence Network's own recommendation to
    # decide, distinct from "auto" (a Company Operating Mode
    # auto-resolution the CEO never saw) and "ceo" (a hand-picked
    # buy/sell/wait). The trade itself executes identically either way —
    # only provenance changes.
    resolved_by: Literal["ceo", "auto", "delegated"] = Field(alias="resolvedBy")
    created_at: str = Field(alias="createdAt")


class DepartmentSelfEvaluation(CamelModel):
    """v0.7 Feature 50 (Part 2/3) — Weekly Self-Evaluation. Generated on
    the same real weekly cadence as app/wisdom.py's ReflectionSession
    (see nexus.py's WEEKLY_INTERVAL_DAYS), one per Executive Intelligence
    Network department, built entirely from that department's own real
    DepartmentOpinion entries logged to the Executive Meeting Log over
    the trailing 7 sim days — never a fabricated self-assessment."""

    id: str
    role: ExecutiveDepartmentRole
    department_label: str = Field(alias="departmentLabel")
    week_ending_sim_day: int = Field(alias="weekEndingSimDay")
    decisions_reviewed: int = Field(alias="decisionsReviewed")
    score: float
    summary: str
    strengths: list[str] = Field(default_factory=list)
    improvement_areas: list[str] = Field(default_factory=list, alias="improvementAreas")
    created_at: str = Field(alias="createdAt")


# Design Bible Chapter 70 Part 2 — Executive Accuracy Score. Deliberately
# narrower than the brief's own six named metrics (Prediction Accuracy,
# Risk Prevention Accuracy, Profit Contribution, Forecast Reliability,
# Decision Quality, Consistency): this codebase already has a standing,
# explicit refusal to fabricate what a hypothetical/never-taken trade
# "would have" done (see app/coach.py, app/player_vs_ai.py), so this
# score is computed ONLY over trades the CEO actually took and that have
# since closed with a real, known P&L (see
# compute_executive_accuracy_scores() in app/executive_intelligence.py)
# — never a counterfactual judgment about a trade that never happened.
#
# CEO directive "Features 31-35," Feature 33 — Executive Accuracy
# Evidence System. `accuracy_pct` is `None` (NOT_ENOUGH_EVIDENCE), never
# a fabricated `0.0`, when `decisions_tracked` is 0 — the exact bug the
# CEO's own brief named ("Research—0%... may mean no evaluated research
# decisions exist yet"). `evaluation_state` makes that distinction
# explicit for every caller rather than leaving each one to reinvent its
# own interpretation of a raw percentage — see
# compute_executive_accuracy_scores()'s own docstring for the exact,
# disclosed thresholds (reused from this codebase's own existing UI
# convention, not invented for this feature).
ExecutiveEvidenceState = Literal["pass", "fail", "inconclusive", "not_enough_evidence"]


class ExecutiveAccuracyScore(CamelModel):
    role: ExecutiveDepartmentRole
    department_label: str = Field(alias="departmentLabel")
    decisions_tracked: int = Field(alias="decisionsTracked")
    correct_count: int = Field(alias="correctCount")
    accuracy_pct: float | None = Field(default=None, alias="accuracyPct")
    evaluation_state: ExecutiveEvidenceState = Field(default="not_enough_evidence", alias="evaluationState")


# Design Bible Chapter 70 Part 3 — Weighted Executive Decision Engine
# (WEDE). Honest scope, stated here once rather than per-field below: of
# the brief's eight named weighting inputs, only two have a real,
# computable source in this codebase — Historical Accuracy
# (ExecutiveAccuracyScore, closed-trade-only) and Market Conditions
# (MarketEnvironmentRegime, Chapter 65). The other six (Prediction
# Quality, Current Expertise, Department Performance, Recent
# Reliability, Rule Compliance, Specialization) have no real per-
# department measure anywhere in this codebase and are not fabricated
# here — see app/weighted_decisions.py's module docstring for the full
# published formula.
WeightProfile = Literal[
    "equal_voting",
    "performance_weighted",
    "risk_first",
    "growth_first",
    "research_first",
    "capital_preservation",
    "balanced_institutional",
    "custom",
]


class DepartmentInfluence(CamelModel):
    """One department's real, fully-published weight for one decision —
    every multiplier that produced `final_weight` is itself a field
    here, never collapsed into an opaque number (this Design Bible's
    "no black-box composite" convention)."""

    role: ExecutiveDepartmentRole
    department_label: str = Field(alias="departmentLabel")
    accuracy_multiplier: float = Field(alias="accuracyMultiplier")
    market_multiplier: float = Field(alias="marketMultiplier")
    preset_multiplier: float = Field(alias="presetMultiplier")
    final_weight: float = Field(alias="finalWeight")
    reasoning: str


class WeightedExecutiveRecommendation(CamelModel):
    """The Weighted Executive Recommendation, always presented alongside
    the pre-existing Raw Vote (`ExecutiveRecommendation`), never in place
    of it — see app/weighted_decisions.py."""

    proposal_id: str = Field(alias="proposalId")
    profile: WeightProfile
    market_regime: MarketEnvironmentRegime = Field(alias="marketRegime")
    department_influences: list[DepartmentInfluence] = Field(alias="departmentInfluences")
    raw_action: ExecutiveAction = Field(alias="rawAction")
    weighted_action: ExecutiveAction = Field(alias="weightedAction")
    # Published per-action breakdown (sum of weight × confidence for every
    # department whose stance maps to that action, normalized to a 0-100
    # scale) — the exact number `weighted_action` was chosen from, not a
    # hidden intermediate.
    score_by_action: dict[str, float] = Field(alias="scoreByAction")
    agrees_with_raw: bool = Field(alias="agreesWithRaw")


# v0.7 Feature 51 — Market Intelligence Department, "the company's eyes."
# Every field below is computed from real data this codebase already has
# access to: the (mock) MarketDataProvider's real OHLCV Candle series
# (app/market_data.py) and real wall-clock time for session detection —
# see app/market_intelligence.py's module docstring for the full honesty
# boundary (what's real technical analysis over real synthesized price
# data vs. what has no real backing data anywhere in this codebase and is
# therefore explicitly NOT computed: true institutional order flow,
# Level 2/dark-pool data, real stop-order locations, or any economic
# calendar). Named distinctly from the existing `MarketRegime`
# (trending_up/trending_down/ranging, Player vs AI's per-symbol read) and
# `MarketEnvironmentRegime` (bull/bear/sideways/high_volatility/
# low_volatility, the simpler five-way whole-market classification Feature
# 22 already computes) — this is a richer, thirteen-way classification
# built from real per-symbol swing/volatility/volume structure, not a
# replacement for either existing one.
MarketIntelligenceRegime = Literal[
    "strong_bull_trend",
    "strong_bear_trend",
    "weak_uptrend",
    "weak_downtrend",
    "sideways_range",
    "expansion",
    "compression",
    "high_volatility",
    "low_volatility",
    "accumulation",
    "distribution",
    "liquidity_hunt",
    "transitional",
]

MarketQualityTier = Literal["excellent", "good", "average", "poor", "avoid_trading"]

# Fixed UTC windows — a documented simplification (no DST handling, no
# live timezone feed), computed from real wall-clock time the same way
# Candle.timestamp already is (app/market_data.py), not TradeTown's
# simulated clock: a "session" is about when real markets are open, not
# an in-game concept.
TradingSession = Literal[
    "asian",
    "london",
    "london_ny_overlap",
    "new_york",
    "ny_lunch_hour",
    "market_open",
    "market_close",
    "closed",
]

MarketDebateSpecialist = Literal[
    "liquidity", "price_action", "momentum", "quant", "risk"
]


class LiquidityZone(CamelModel):
    """One real equal-high/equal-low price cluster found in a symbol's
    own recent candle history — the standard price-action technique for
    naming a probable liquidity zone. `touches` is how many of the
    sampled swing points landed within the clustering tolerance of this
    price — never a claim about real resting stop orders, which this
    codebase has no data source for (see app/market_intelligence.py)."""

    kind: Literal["equal_highs", "equal_lows"]
    price: float
    touches: int


class LiquidityRead(CamelModel):
    """Real, per-symbol. `sweepDetected` is a real, checkable price-action
    pattern (a candle wick pierces a recorded LiquidityZone and closes
    back inside it) — the same definition price-action traders use on a
    real chart, computed here from real (mock) candle data, never from
    real order-book/order-flow data this codebase does not have."""

    symbol: str
    zones: list[LiquidityZone] = Field(default_factory=list)
    sweep_detected: bool = Field(alias="sweepDetected")
    sweep_direction: Literal["above_highs", "below_lows", "none"] = Field(
        alias="sweepDirection"
    )
    liquidity_score: float = Field(alias="liquidityScore")  # 0-100
    detail: str


class MarketStructureRead(CamelModel):
    """Real, per-symbol swing structure from the symbol's own recent
    candle history — swing highs/lows via real local-extrema detection,
    Break of Structure/Market Structure Shift via the standard real
    definition (a new swing high above the prior swing high in an
    uptrend, or the reverse)."""

    symbol: str
    swing_highs: list[float] = Field(default_factory=list, alias="swingHighs")
    swing_lows: list[float] = Field(default_factory=list, alias="swingLows")
    last_break_of_structure: Literal["bullish", "bearish", "none"] = Field(
        alias="lastBreakOfStructure"
    )
    structure_state: Literal[
        "trend_continuation",
        "trend_reversal",
        "consolidation",
        "expansion",
        "compression",
    ] = Field(alias="structureState")
    detail: str


# CEO directive "Professional Trading Firm — Market-Analysis Knowledge +
# Session Intelligence Expansion," Phases 1-2 (app/technical_patterns.py).
# All real, computed-fresh pattern reads over real (mock) candle data,
# extending — never duplicating — app/market_intelligence.py's existing
# real swing-detection (`compute_market_structure()`) and its module
# docstring's honesty conventions. None of these are wired into any live
# trade decision (see app/technical_patterns.py's own module docstring
# for why: a new pattern earns a place in a real decision only once the
# hypothesis-testing pipeline this whole directive demands exists, and it
# does not yet — see docs/Architecture.md's Phase 5-7 scoping).
SwingStructureLabel = Literal["higher_high", "higher_low", "lower_high", "lower_low"]


class SwingStructureRead(CamelModel):
    """The classic HH/HL/LH/LL sequence, chronologically merged from the
    real swing highs/lows `app/market_intelligence.py`'s own
    `_find_swings()` already detects (reused directly, not
    re-implemented) — each label real relative to its own immediately
    preceding same-type swing, never a fabricated trend call."""

    symbol: str
    labels: list[SwingStructureLabel] = Field(default_factory=list)
    detail: str


class FairValueGap(CamelModel):
    """One real 3-candle imbalance: `direction="bullish"` when candle 1's
    high sits below candle 3's low (a real, standard FVG definition —
    price traded through this zone without a full real trade on the
    middle candle), `"bearish"` the mirror case. `filled` is real and
    checkable — whether any later real candle's range has already traded
    back into `[gap_low, gap_high]`."""

    direction: Literal["bullish", "bearish"]
    gap_high: float = Field(alias="gapHigh")
    gap_low: float = Field(alias="gapLow")
    timestamp: str
    filled: bool


class FairValueGapRead(CamelModel):
    symbol: str
    gaps: list[FairValueGap] = Field(default_factory=list)
    detail: str


CandlestickPatternType = Literal["bullish_engulfing", "bearish_engulfing", "hammer", "shooting_star", "doji"]


class CandlestickPattern(CamelModel):
    """One real, geometrically-checkable candlestick pattern on one real
    candle (or real candle pair, for the two engulfing types) — see
    app/technical_patterns.py for each pattern's exact real definition.
    Naming a pattern here is never a claim it predicts the next move —
    see this read's own `detail` and the Academy lesson backing it for
    that honesty boundary."""

    pattern: CandlestickPatternType
    timestamp: str
    detail: str


class CandlestickPatternRead(CamelModel):
    symbol: str
    patterns: list[CandlestickPattern] = Field(default_factory=list)
    detail: str


ChartPatternType = Literal["double_top", "double_bottom", "trendline_break_up", "trendline_break_down"]


class ChartPattern(CamelModel):
    """CEO directive "Professional Quant Trading Firm — Quant Intelligence
    + Market Analysis Completion Phase (Next Research + Validation
    Pass)" — one real, objectively-detected structural chart pattern.
    Every field is a real, checkable fact about the exact real bars that
    produced it — `confidencePct` measures how cleanly THIS pattern's own
    real geometry matched its definition (price symmetry / retracement
    depth / trendline touch count), never a prediction that price will
    actually follow through. Only ever reported once real CONFIRMATION
    (a real close through the real neckline/trendline) has already
    happened — never a "forming" pattern whose outcome is still unknown,
    the same conservative, no-look-ahead boundary every other pattern in
    `app/technical_patterns.py` already holds to. See
    `app/technical_patterns.py::detect_chart_patterns()` for each
    pattern type's exact real definition."""

    pattern_id: str = Field(alias="patternId")
    pattern_type: ChartPatternType = Field(alias="patternType")
    direction: Literal["bullish", "bearish"]
    confidence_pct: float = Field(alias="confidencePct")
    price_low: float = Field(alias="priceLow")
    price_high: float = Field(alias="priceHigh")
    formed_at: str = Field(alias="formedAt")
    confirmed_at: str = Field(alias="confirmedAt")
    formation_detail: str = Field(alias="formationDetail")
    invalidation_detail: str = Field(alias="invalidationDetail")
    source: str
    timeframe: str
    symbol: str


class ChartPatternRead(CamelModel):
    symbol: str
    timeframe: str
    patterns: list[ChartPattern] = Field(default_factory=list)
    detail: str


class SessionRangeRead(CamelModel):
    """One real session's own real high/low over the candles that fell
    inside its real UTC window (the same `_session_for_hour()` boundaries
    `app/market_intelligence.py`'s `compute_session()` already uses,
    reused directly). `retested` is real and checkable — whether any
    later candle (outside that session's own window) traded back into
    `[range_low, range_high]`, the real, professional "does the prior
    session's range act as a reference level later" question — never
    asserted as reliably true, only reported as observed or not."""

    symbol: str
    session: TradingSession
    range_high: float = Field(alias="rangeHigh")
    range_low: float = Field(alias="rangeLow")
    retested: bool
    detail: str


class FibonacciLevel(CamelModel):
    ratio: float
    price: float


class FibonacciRead(CamelModel):
    """Real retracement/extension price LEVELS computed from the symbol's
    own most recent real swing high/low (reused from
    `app/market_intelligence.py`'s real swing detection) — never a claim
    that price will react at any of them. `detail` states this plainly;
    see the Academy lesson backing this read for the full "candidate
    area requiring confirmation, not a guaranteed level" framing this
    directive itself requires."""

    symbol: str
    swing_high: float = Field(alias="swingHigh")
    swing_low: float = Field(alias="swingLow")
    levels: list[FibonacciLevel] = Field(default_factory=list)
    detail: str


class OrderBlockRead(CamelModel):
    """A real, disclosed, ONE-SPECIFIC-DEFINITION proxy for an "order
    block" — professional usage of this term varies; this reads the last
    opposite-direction candle immediately before a real Break of
    Structure `app/market_intelligence.py`'s `compute_market_structure()`
    already detected (reused directly). `detail` discloses this is one
    named, checkable definition among several real ones in use, not a
    claim of institutional order-flow data this codebase does not have."""

    symbol: str
    direction: Literal["bullish", "bearish", "none"]
    price_high: float | None = Field(default=None, alias="priceHigh")
    price_low: float | None = Field(default=None, alias="priceLow")
    timestamp: str | None = None
    detail: str


# CEO directive "Professional Quant Trading Firm — Quant Intelligence +
# Market Analysis Completion Phase," Phase B — real, static support/
# resistance levels. Genuinely missing before this: app/confidence.py's
# own module docstring already disclosed support & resistance as
# deliberately left out (no computation existed anywhere in this
# codebase — confirmed by a full grep audit). Reuses
# app/market_intelligence.py's existing real swing-high/low detection
# (`_find_swings()`) directly rather than a second swing detector — a
# "level" here is a real cluster of >= MIN_TOUCHES_FOR_LEVEL swing
# prices within a real, disclosed price tolerance of each other, never
# a single, unconfirmed swing point.
class SupportResistanceLevel(CamelModel):
    price: float
    touches: int
    role: Literal["support", "resistance"]
    detail: str


class SupportResistanceRead(CamelModel):
    """`role` is real and mechanical — "support" when the real current
    close sits above the level, "resistance" when below — the same
    real, standard convention every price-action trader uses, never a
    claim that the level will actually hold. See
    app/technical_patterns.py::detect_support_resistance_levels()."""

    symbol: str
    levels: list[SupportResistanceLevel] = Field(default_factory=list)
    detail: str


# CEO directive "Professional Trading Firm — Market-Analysis Knowledge +
# Session Intelligence Expansion," Phase 6 — the Confluence Engine
# (app/signal_correlation.py). RESEARCH FINDING that shaped this: a full
# audit of app/voting.py's researcher_vote() found the "news" and
# "macro" analyst votes are BOTH driven by the identical underlying
# ResearchItem.confidence value via the same probabilistic mechanism —
# not two independent readings, the same single signal expressed twice
# — and the "execution" vote is a pure majority tally of the other five,
# contributing zero new evidence. This is a real correlation/redundancy
# finding, not an invented one — see app/signal_correlation.py's own
# module docstring for the full audit trail. Explicitly NOT the
# "Plan Adherence" confluence checklist app/process_adherence.py already
# disclosed as unbuildable (PLANNED vs. ACTUAL conditions) — this reads
# the CURRENT proposal's real evidence for genuine independence, never a
# plan-adherence audit.
class CorrelatedSignalPair(CamelModel):
    role_a: AnalystRole = Field(alias="roleA")
    role_b: AnalystRole = Field(alias="roleB")
    reason: str


class ConfluenceRead(CamelModel):
    """`naive_confirmation_count` is what a naive count would report
    (every vote agreeing with the desk's real overall direction).
    `independent_evidence_count` is the real, deduplicated count once
    correlated pairs are folded together and the non-independent
    execution-synthesis vote is excluded — never higher than
    `naive_confirmation_count`, and the gap between them is the real
    point of this read."""

    naive_confirmation_count: int = Field(alias="naiveConfirmationCount")
    independent_evidence_count: int = Field(alias="independentEvidenceCount")
    correlated_pairs: list[CorrelatedSignalPair] = Field(default_factory=list, alias="correlatedPairs")
    detail: str


# CEO directive "Professional Quant Trading Firm — Quant Intelligence +
# Market Analysis Completion Phase," Phase D — the evidence-family
# confluence layer over INDICATOR/PATTERN signals. Distinct from
# `ConfluenceRead` above (which operates on the six analyst VOTES) and
# from app/signal_correlation.py's own module docstring's own audit of
# THAT layer — this instead groups the raw technical-indicator/pattern
# signals app/technical_indicators.py and app/technical_patterns.py
# already compute into real evidence FAMILIES (trend/momentum/volume/
# liquidity/price-structure/pattern), so "EMA bullish + MACD bullish +
# Stochastic bullish" reads as ONE real momentum/trend family agreeing,
# never three independent confirmations. See app/evidence_confluence.py.
EvidenceFamily = Literal["trend", "momentum", "volume", "liquidity", "price_structure", "pattern", "levels"]
EvidenceDirection = Literal["bullish", "bearish", "neutral"]


class EvidenceSignal(CamelModel):
    """One real, individually-named signal read — never a bare
    'bullish'/'bearish' verdict with no disclosed source. `detail`
    always names the real convention behind the direction (e.g. "RSI
    read >55, a real, conventional bullish-leaning threshold — never
    asserted as a TradeTown-validated predictive edge"), the same
    disclosure discipline `app/technical_indicators.py`'s own `rsi()`
    docstring already established for its ">70 overbought" convention."""

    name: str
    family: EvidenceFamily
    direction: EvidenceDirection
    detail: str


class EvidenceFamilyRead(CamelModel):
    """One real evidence family's own net read across every real signal
    assigned to it. `net_direction` is `"neutral"` both when every real
    signal in the family reads neutral AND when the family's real
    signals genuinely disagree with each other (a real, disclosed
    "mixed" case is never silently resolved toward whichever direction
    has one more vote) — `detail` always distinguishes the two."""

    family: EvidenceFamily
    signals: list[EvidenceSignal] = Field(default_factory=list)
    net_direction: EvidenceDirection = Field(alias="netDirection")
    detail: str


class EvidenceConfluenceRead(CamelModel):
    """`raw_signal_count` is what a naive count would report (every real
    directional signal found, regardless of family). `independent_
    family_count` is the real, deduplicated count of DISTINCT evidence
    families whose own net direction agrees with the majority direction
    — never higher than the number of real families with any signal at
    all, and the gap between `raw_signal_count` and this number is the
    real point of this read, the same "quality of evidence, not
    quantity" discipline `app/signal_correlation.py` already established
    one layer up (over analyst votes rather than raw indicator/pattern
    signals)."""

    symbol: str
    families: list[EvidenceFamilyRead] = Field(default_factory=list)
    raw_signal_count: int = Field(alias="rawSignalCount")
    independent_family_count: int = Field(alias="independentFamilyCount")
    majority_direction: EvidenceDirection = Field(alias="majorityDirection")
    agreeing_families: list[EvidenceFamily] = Field(default_factory=list, alias="agreeingFamilies")
    detail: str


class TechnicalIndicatorsRead(CamelModel):
    """Real SMA/EMA/RSI/MACD/Stochastic/ATR/VWAP values computed fresh
    over a symbol's own real (mock) candle history
    (`app/technical_indicators.py`). Every field is `None`, never a
    fabricated value, whenever the candle history is below that
    indicator's own real minimum bar count. Informational only — see
    that module's own docstring for why none of these are wired into any
    live trading decision yet."""

    symbol: str
    sma20: float | None = None
    ema20: float | None = None
    rsi14: float | None = None
    macd_line: float | None = Field(default=None, alias="macdLine")
    macd_signal: float | None = Field(default=None, alias="macdSignal")
    macd_histogram: float | None = Field(default=None, alias="macdHistogram")
    stochastic_percent_k: float | None = Field(default=None, alias="stochasticPercentK")
    stochastic_percent_d: float | None = Field(default=None, alias="stochasticPercentD")
    atr14: float | None = None
    vwap: float | None = None
    parabolic_sar: float | None = Field(default=None, alias="parabolicSar")
    parabolic_sar_trend: Literal["up", "down"] | None = Field(default=None, alias="parabolicSarTrend")
    supertrend: float | None = None
    supertrend_trend: Literal["up", "down"] | None = Field(default=None, alias="supertrendTrend")
    detail: str


class TechnicalAnalysisRead(CamelModel):
    """One bundled "technical desk briefing" for a symbol — real
    indicator values (`app/technical_indicators.py`) alongside real
    pattern/structure reads (`app/technical_patterns.py`), computed
    fresh in a single call rather than requiring the frontend to fan out
    across many separate requests. Never persisted, never wired into any
    live trading decision — see each underlying module's own docstring."""

    symbol: str
    indicators: TechnicalIndicatorsRead
    swing_structure: SwingStructureRead = Field(alias="swingStructure")
    fair_value_gaps: FairValueGapRead = Field(alias="fairValueGaps")
    candlestick_patterns: CandlestickPatternRead = Field(alias="candlestickPatterns")
    fibonacci: FibonacciRead
    order_block: OrderBlockRead = Field(alias="orderBlock")
    support_resistance: SupportResistanceRead = Field(alias="supportResistance")
    chart_patterns: ChartPatternRead = Field(alias="chartPatterns")


class VolatilityRead(CamelModel):
    """All four numbers are real, derived from the same real
    app/market_data.py `volatility_pct()` helper app/signal_calibration.py
    and app/player_vs_ai.py already use — `expected_pct` is an honest
    trailing-average statistical projection, explicitly never a forecast
    of any specific future move (see the PROBABILITY FIRST rule in
    app/market_intelligence.py's module docstring)."""

    current_pct: float = Field(alias="currentPct")
    historical_avg_pct: float = Field(alias="historicalAvgPct")
    session_pct: float = Field(alias="sessionPct")
    percentile: (
        float  # 0-100, current vs. this same fetched window's own historical average
    )
    expected_pct: float = Field(alias="expectedPct")
    detail: str


class SessionRead(CamelModel):
    current: TradingSession
    label: str
    overlaps_active: list[str] = Field(default_factory=list, alias="overlapsActive")
    detail: str


class MomentumRead(CamelModel):
    roc_pct: float = Field(
        alias="rocPct"
    )  # rate of change over the current sampled window
    strength: Literal["accelerating", "steady", "decelerating", "exhausted"]
    detail: str


class InstitutionalActivityRead(CamelModel):
    """An explicit, named PROXY — never real order-flow or institutional
    footprint data, which this codebase has no source for. Real signal:
    volume well above a symbol's own trailing average alongside an
    unusually small price move for that volume ("absorption") is a
    standard real technical heuristic traders use as one input among many
    when guessing at large-participant activity on ordinary OHLCV data —
    it is not verified knowledge of who is actually trading."""

    volume_price_divergence_score: float = Field(
        alias="volumePriceDivergenceScore"
    )  # 0-100
    absorption_detected: bool = Field(alias="absorptionDetected")
    symbols_flagged: list[str] = Field(default_factory=list, alias="symbolsFlagged")
    detail: str


class NewsRiskRead(CamelModel):
    """A real, honest proxy: the count of real `market`-category NewsItem
    records currently on file (app/schemas.py's NewsItem has no per-symbol
    linkage — headlines are real but generic regime flavor text, see
    app/nexus.py's MARKET_HEADLINES_BY_REGIME) — not a real economic
    calendar or per-symbol event-risk read, which this codebase has no
    data source for (same honest gap app/sandbox.py's own "Testing
    Environments" cut already documents)."""

    active_market_news_count: int = Field(alias="activeMarketNewsCount")
    risk_level: Literal["low", "moderate", "elevated"] = Field(alias="riskLevel")
    detail: str


class MarketQualityScore(CamelModel):
    tier: MarketQualityTier
    score: float  # 0-100
    confidence_pct: float = Field(alias="confidencePct")
    reasoning: str
    evidence: list[str] = Field(default_factory=list)
    # An honest text comparison against this same company's own real
    # MarketIntelligenceReport history (never an external dataset) — see
    # app/market_intelligence.py's compute_historical_similarity().
    historical_similarity: str = Field(alias="historicalSimilarity")


class MarketIntelligenceState(CamelModel):
    """The department's always-current "eyes" — recomputed fresh every
    tick from real (mock) OHLCV data, the same "cheap, always current,
    never a stale second copy" convention app/company_health.py and
    app/market_environment.py already use. This is what a TradeProposal
    and the Trade Gatekeeper actually read (see app/executive.py/
    app/gatekeeper.py) — never the once-daily MarketIntelligenceReport
    below, which can be up to a day stale by the time a proposal fires."""

    regime: MarketIntelligenceRegime
    regime_label: str = Field(alias="regimeLabel")
    regime_detail: str = Field(alias="regimeDetail")
    quality: MarketQualityScore
    volatility: VolatilityRead
    session: SessionRead
    momentum: MomentumRead
    institutional_activity: InstitutionalActivityRead = Field(
        alias="institutionalActivity"
    )
    news_risk: NewsRiskRead = Field(alias="newsRisk")
    liquidity: list[LiquidityRead] = Field(default_factory=list)
    structure: list[MarketStructureRead] = Field(default_factory=list)
    updated_at: str = Field(alias="updatedAt")


class MarketDebateTurn(CamelModel):
    """One specialist's independent real read of the current
    MarketIntelligenceState — never a copy of another specialist's turn,
    and never a trade-specific opinion (contrast with app/debate.py's
    proposal-scoped AiDebate, which this is not a duplicate of — see
    app/market_debate.py's module docstring)."""

    specialist: MarketDebateSpecialist
    label: str
    observation: str
    confidence_pct: float = Field(alias="confidencePct")
    evidence: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    opportunities: list[str] = Field(default_factory=list)


class MarketDebate(CamelModel):
    id: str
    turns: list[MarketDebateTurn] = Field(default_factory=list)
    summary: str
    created_at: str = Field(alias="createdAt")


class StrategyMatch(CamelModel):
    """Real, evidence-backed: only ever names a Strategy that has at
    least one real StrategyReport on file whose own `bestMarketEnvironment`
    (app/sandbox.py) is consistent with today's regime — never a
    fabricated recommendation for a strategy with no track record."""

    recommended_strategy_ids: list[str] = Field(
        default_factory=list, alias="recommendedStrategyIds"
    )
    avoided_strategy_ids: list[str] = Field(
        default_factory=list, alias="avoidedStrategyIds"
    )
    recommended_risk_level: Literal["minimal", "reduced", "normal", "elevated"] = Field(
        alias="recommendedRiskLevel"
    )
    detail: str


# CEO directive "Live Trade → Strategy Provenance," Phase 9 — the one
# real gap `app/trade_pipeline_health.py`'s existing no-trade diagnostics
# never covers (confirmed by audit: zero references to "strategy"
# anywhere in that module). Every real strategy gets exactly one of
# these four honest, mutually-exclusive reasons, built entirely from two
# already-real, already-computed sources — StrategyMatch's own
# recommended/avoided regime-eligibility split (never re-derived) and
# the real live trade count from `compute_strategy_performance()`
# (Phase 4) — never a new "why" invented for this pass.
StrategyNoTradeReason = Literal[
    "trading_live",
    "blocked_by_regime_today",
    "eligible_but_never_selected",
    "no_backtest_evidence_yet",
]


class StrategyTradingDiagnosticRead(CamelModel):
    strategy_id: str = Field(alias="strategyId")
    strategy_name: str = Field(alias="strategyName")
    stage: StrategyStage
    live_trade_count: int = Field(alias="liveTradeCount")
    reason: StrategyNoTradeReason
    detail: str


class StrategyTradingDiagnosticSummary(CamelModel):
    reads: list[StrategyTradingDiagnosticRead]
    updated_at: str = Field(alias="updatedAt")


# --- v0.7 Feature 52 (Part 1) — the Strategy Validation Laboratory's
# extension of the Research Sandbox pipeline (app/sandbox.py). Every
# model below is real math over a strategy's own already-real
# SimulationResult/StrategyReview/ResearchItem history, or a direct reuse
# of Feature 51's real regime/liquidity engines — see app/strategy_lab.py's
# module docstring for the full honesty boundary (what's a real bootstrap
# over real generating inputs vs. a named proxy vs. explicitly not built).


class StrategyMonteCarloResult(CamelModel):
    """A real trade-sequence bootstrap: resamples win/loss draws using
    the strategy's own real, aggregated win rate and average win/loss
    sizes (from SimulationResult) as the generating probabilities — the
    same 'real derived inputs, not fabricated statistics' discipline
    app/simulation.py's own placeholder engine already established. See
    app/strategy_lab.py's run_strategy_monte_carlo().

    valueAtRisk95Pct/valueAtRisk99Pct/conditionalValueAtRisk95Pct/
    conditionalValueAtRisk99Pct (Quantitative Research & Intelligence
    System, Piece 3) are real percentile/tail-mean reads off this same
    bootstrap's own sorted final-return array — no new simulation, no
    new data source. VaR is the return level such that only 5%/1% of
    simulated paths did worse (signed: negative means a loss); CVaR
    (Expected Shortfall) is the mean return among exactly that worst
    5%/1% of paths, i.e. what to expect *given* you're in the tail, not
    just where the tail begins."""

    id: str
    strategy_id: str = Field(alias="strategyId")
    strategy_name: str = Field(alias="strategyName")
    paths_simulated: int = Field(alias="pathsSimulated")
    trades_per_path: int = Field(alias="tradesPerPath")
    source_win_rate: float = Field(alias="sourceWinRate")
    source_avg_win_pct: float = Field(alias="sourceAvgWinPct")
    source_avg_loss_pct: float = Field(alias="sourceAvgLossPct")
    median_return_pct: float = Field(alias="medianReturnPct")
    return_range_low_pct: float = Field(alias="returnRangeLowPct")
    return_range_high_pct: float = Field(alias="returnRangeHighPct")
    median_max_drawdown_pct: float = Field(alias="medianMaxDrawdownPct")
    worst_case_drawdown_pct: float = Field(alias="worstCaseDrawdownPct")
    probability_of_profit_pct: float = Field(alias="probabilityOfProfitPct")
    # "Probability Of Ruin" from the brief — a real share of the
    # simulated paths whose drawdown breached RUIN_DRAWDOWN_PCT, not a
    # true infinite-sample estimate; capitalSurvivalPct is its
    # complement, named to match the brief's own "Capital Survival" term.
    probability_of_ruin_pct: float = Field(alias="probabilityOfRuinPct")
    capital_survival_pct: float = Field(alias="capitalSurvivalPct")
    value_at_risk_95_pct: float = Field(alias="valueAtRisk95Pct")
    value_at_risk_99_pct: float = Field(alias="valueAtRisk99Pct")
    conditional_value_at_risk_95_pct: float = Field(alias="conditionalValueAtRisk95Pct")
    conditional_value_at_risk_99_pct: float = Field(alias="conditionalValueAtRisk99Pct")
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


# Quantitative Research & Intelligence System, Piece 7 — Forge, the
# Quant Developer. Distinct from Piece 4's ModelValidationReport
# (Meridian reviews the EVIDENCE a strategy's Monte Carlo run produced)
# — this audits the RELIABILITY OF THE TOOL that produced it: whether
# MONTE_CARLO_PATHS gives enough real samples in the 5%/1% tail for the
# VaR/CVaR statistics StrategyMonteCarloResult reports there to be
# statistically trustworthy, not just a share of paths that happen to
# breach a bar. See app/quant_developer.py's module docstring for the
# full derivation and the disclosed reliability threshold.
MonteCarloReliabilityVerdict = Literal["reliable", "marginal", "unreliable"]


class MonteCarloReliabilityAssessment(CamelModel):
    """A real, standing engineering fact about the Monte Carlo bootstrap
    pipeline itself (app/strategy_lab.py's run_strategy_monte_carlo()) —
    NOT a per-strategy finding, since every real run uses the identical
    global MONTE_CARLO_PATHS constant. Recomputed fresh on every read
    (never persisted or capped), the same "derived view over already-
    real data" convention app/knowledge_graph.py's own module docstring
    already established, and audited against every real
    StrategyMonteCarloResult currently on file rather than just restated
    from the constant, so a future drift between the documented constant
    and what a run actually used would be caught, not assumed away."""

    developer_agent_id: Literal["forge"] = Field(default="forge", alias="developerAgentId")
    paths_simulated: int = Field(alias="pathsSimulated")
    tail_sample_count_95_pct: int = Field(alias="tailSampleCount95Pct")
    tail_sample_count_99_pct: int = Field(alias="tailSampleCount99Pct")
    verdict_95_pct: MonteCarloReliabilityVerdict = Field(alias="verdict95Pct")
    verdict_99_pct: MonteCarloReliabilityVerdict = Field(alias="verdict99Pct")
    min_reliable_tail_samples: int = Field(alias="minReliableTailSamples")
    min_marginal_tail_samples: int = Field(alias="minMarginalTailSamples")
    recommended_paths_for_reliable_99_pct: int = Field(alias="recommendedPathsForReliable99Pct")
    real_results_audited: int = Field(alias="realResultsAudited")
    # False only if a real StrategyMonteCarloResult on file was found
    # using a DIFFERENT path count than the audited constant — an honest
    # drift flag, never fabricated.
    observed_path_counts_consistent: bool = Field(alias="observedPathCountsConsistent")
    reasoning: str
    threshold_source: str = Field(alias="thresholdSource")
    generated_at: str = Field(alias="generatedAt")


class StrategyRegimeBucketPerformance(CamelModel):
    """One real Testing Environment bucket (app/sandbox.py's TestScenario
    — the actual granularity SimulationResult is tagged at) labeled with
    which of Feature 51's 13 real MarketIntelligenceRegime values it
    covers, via the same real regime->scenario keyword mapping
    app/market_intelligence.py's compute_strategy_match() already uses —
    never a fabricated 13-way independently-tested breakdown."""

    scenario: TestScenario
    regimes: list[MarketIntelligenceRegime]
    tested: bool
    run_count: int = Field(alias="runCount")
    avg_return_pct: float = Field(alias="avgReturnPct")
    avg_win_rate: float = Field(alias="avgWinRate")
    verdict: Literal["strong", "neutral", "weak", "untested"]


class StrategyRegimeTestReport(CamelModel):
    id: str
    strategy_id: str = Field(alias="strategyId")
    strategy_name: str = Field(alias="strategyName")
    buckets: list[StrategyRegimeBucketPerformance]
    best_scenario: TestScenario | None = Field(default=None, alias="bestScenario")
    worst_scenario: TestScenario | None = Field(default=None, alias="worstScenario")
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


class StrategyLiquidityValidation(CamelModel):
    """Reuses Feature 51's real LiquidityRead/MarketStructureRead as-is
    against the strategy's own watched symbols — never claims more than
    those models already claim (real equal-high/low clustering + a real
    sweep-and-close-back pattern, not real resting stop-order locations
    or institutional order flow — see app/market_intelligence.py's own
    module docstring)."""

    id: str
    strategy_id: str = Field(alias="strategyId")
    strategy_name: str = Field(alias="strategyName")
    symbols_checked: list[str] = Field(default_factory=list, alias="symbolsChecked")
    liquidity_reads: list[LiquidityRead] = Field(
        default_factory=list, alias="liquidityReads"
    )
    structure_reads: list[MarketStructureRead] = Field(
        default_factory=list, alias="structureReads"
    )
    real_sweep_rate_pct: float = Field(alias="realSweepRatePct")
    verdict: Literal["favorable", "neutral", "unfavorable"]
    detail: str
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


# CEO directive "Professional Trading Firm — Market-Analysis Knowledge +
# Session Intelligence Expansion," Phase 15 — the 50 EMA breakout +
# pullback strategy, converted from CEO-supplied source material into a
# formal, reproducible research hypothesis (see app/ema_pullback_
# research.py's module docstring for the full rule definitions and the
# SOURCE CLAIM vs. TRADETOWN EVIDENCE distinction this whole schema
# family exists to keep honest). Every field here is a real, computed
# read over a real bar-by-bar rule replay against real (mock) OHLCV
# candle history — never fabricated, never asserted as validated merely
# because the source material claims the strategy works.
EmaPullbackTradeOutcome = Literal["win", "loss", "open"]
EmaPullbackRegimeTrend = Literal["trending_up", "trending_down", "ranging"]
EmaPullbackRegimeVolatility = Literal["high", "normal", "low"]


class EmaPullbackTradeRecord(CamelModel):
    """One real, individually-traceable simulated trade from the rule
    replay — never an aggregate statistic. `regimeTrend`/
    `regimeVolatility` are a self-contained proxy computed only from this
    same candle series (50 EMA slope; ATR vs. its own trailing median) —
    a deliberately simpler, disclosed stand-in for
    `app/market_intelligence.py`'s real 13-way MarketIntelligenceRegime
    classifier, which needs live, cross-symbol sweep/reversal state this
    historical replay has no access to (see the module docstring's own
    ARCHITECTURALLY BLOCKED note)."""

    symbol: str
    direction: Literal["long", "short"]
    entry_timestamp: str = Field(alias="entryTimestamp")
    entry_price: float = Field(alias="entryPrice")
    stop_price: float = Field(alias="stopPrice")
    target_price: float = Field(alias="targetPrice")
    exit_price: float | None = Field(default=None, alias="exitPrice")
    outcome: EmaPullbackTradeOutcome
    r_multiple_realized: float = Field(alias="rMultipleRealized")
    entry_session: TradingSession = Field(alias="entrySession")
    regime_trend: EmaPullbackRegimeTrend = Field(alias="regimeTrend")
    regime_volatility: EmaPullbackRegimeVolatility = Field(alias="regimeVolatility")
    breakout_candle_extended: bool = Field(alias="breakoutCandleExtended")
    breakout_candle_range_ratio: float = Field(alias="breakoutCandleRangeRatio")
    mae_r: float = Field(alias="maeR")
    mfe_r: float = Field(alias="mfeR")
    # CEO directive "Professional Quant Firm Phase," Feature 38 — the
    # real number of bars this trade's own forward walk covered before
    # its real exit (stop/target hit), or the full real path length
    # walked if it never closed within the caller's own max-hold-bars
    # policy ("open"). A real, bar-count unit — never wall-clock time,
    # since this is a historical bar-by-bar replay, not a live clock.
    bars_held: int = Field(alias="barsHeld")


class EmaPullbackStatsBucket(CamelModel):
    """One real, honestly-sized bucket of trades — used identically for
    the R-multiple sweep, the session/regime/instrument/breakout-size
    breakdowns, and the confirmed-vs-naive-baseline comparison, so every
    slice of this research reports the exact same fields the same way.
    `verdict` is `None` (never a forced call) below
    `MIN_TRADES_FOR_BUCKET_VERDICT`."""

    label: str
    trade_count: int = Field(alias="tradeCount")
    win_count: int = Field(alias="winCount")
    loss_count: int = Field(alias="lossCount")
    open_count: int = Field(alias="openCount")
    win_rate_pct: float | None = Field(default=None, alias="winRatePct")
    avg_win_r: float | None = Field(default=None, alias="avgWinR")
    avg_loss_r: float | None = Field(default=None, alias="avgLossR")
    expectancy_r: float | None = Field(default=None, alias="expectancyR")
    profit_factor: float | None = Field(default=None, alias="profitFactor")
    max_drawdown_r: float | None = Field(default=None, alias="maxDrawdownR")
    longest_losing_streak: int | None = Field(default=None, alias="longestLosingStreak")
    # CEO directive "Professional Quant Firm Phase," Feature 38 — real
    # additions to this one authoritative bucket shape, computed
    # identically everywhere it's used (app/backtest_primitives.py's
    # aggregate_bucket()). sharpeRatio/sortinoRatio reuse app/
    # analytics.py's own real, disclosed per-trade formulas (risk-free
    # rate assumed 0, never annualized — see that module's own
    # docstring) applied to this bucket's own real closed-trade
    # rMultipleRealized sequence. calmarRatio is this same codebase's
    # own real, disclosed, NOT-annualized analog (expectancy over max
    # drawdown, both in R) — never a claim of a real annualized
    # professional Calmar figure, which this bar-based (not calendar-
    # based) replay has no real way to compute honestly.
    longest_winning_streak: int | None = Field(default=None, alias="longestWinningStreak")
    largest_win_r: float | None = Field(default=None, alias="largestWinR")
    largest_loss_r: float | None = Field(default=None, alias="largestLossR")
    avg_holding_bars: float | None = Field(default=None, alias="avgHoldingBars")
    sharpe_ratio: float | None = Field(default=None, alias="sharpeRatio")
    sortino_ratio: float | None = Field(default=None, alias="sortinoRatio")
    calmar_ratio: float | None = Field(default=None, alias="calmarRatio")
    verdict: Literal["enough_evidence", "not_enough_evidence"] | None = None
    detail: str


class EmaPullbackSourceClaimComparison(CamelModel):
    """The CEO-supplied source material's own reported result, displayed
    ONLY as an external claim for comparison — never treated as
    TradeTown-validated evidence, and never used as an input to any
    computation in this module. See `SOURCE_CLAIM_NOTE` in
    app/ema_pullback_research.py."""

    source_claim_trade_count: int = Field(alias="sourceClaimTradeCount")
    source_claim_winners: int = Field(alias="sourceClaimWinners")
    source_claim_win_rate_pct: float = Field(alias="sourceClaimWinRatePct")
    tradetown_trade_count: int = Field(alias="tradetownTradeCount")
    tradetown_win_rate_pct: float | None = Field(default=None, alias="tradetownWinRatePct")
    detail: str


class EmaPullbackResearchResult(CamelModel):
    """The full research experiment result for one CEO-directed run —
    computed fresh on request, never persisted, never wired into any
    live trading decision, agent behavior, or the Gatekeeper/Risk
    Authority/Model Validator pipeline. `modelValidation`/`monteCarlo`
    reuse the existing Strategy Lab machinery unchanged (an ad hoc,
    non-persisted Strategy/SimulationResult pair built from this run's
    own real numbers is the only way they are invoked) — never a second,
    parallel validation or risk engine."""

    id: str
    hypothesis: str
    rules_disclosure: str = Field(alias="rulesDisclosure")
    symbols_tested: list[str] = Field(alias="symbolsTested")
    timeframe: str
    candles_per_symbol: int = Field(alias="candlesPerSymbol")
    reference_r_multiple: float = Field(alias="referenceRMultiple")
    r_multiple_sweep: list[EmaPullbackStatsBucket] = Field(default_factory=list, alias="rMultipleSweep")
    session_breakdown: list[EmaPullbackStatsBucket] = Field(default_factory=list, alias="sessionBreakdown")
    regime_trend_breakdown: list[EmaPullbackStatsBucket] = Field(default_factory=list, alias="regimeTrendBreakdown")
    regime_volatility_breakdown: list[EmaPullbackStatsBucket] = Field(default_factory=list, alias="regimeVolatilityBreakdown")
    instrument_breakdown: list[EmaPullbackStatsBucket] = Field(default_factory=list, alias="instrumentBreakdown")
    breakout_size_breakdown: list[EmaPullbackStatsBucket] = Field(default_factory=list, alias="breakoutSizeBreakdown")
    confirmed_vs_naive_baseline: list[EmaPullbackStatsBucket] = Field(default_factory=list, alias="confirmedVsNaiveBaseline")
    source_claim_comparison: EmaPullbackSourceClaimComparison = Field(alias="sourceClaimComparison")
    model_validation: ModelValidationReport | None = Field(default=None, alias="modelValidation")
    monte_carlo: StrategyMonteCarloResult | None = Field(default=None, alias="monteCarlo")
    data_honesty_note: str = Field(alias="dataHonestyNote")
    generated_at: str = Field(alias="generatedAt")


# CEO directive "Professional Quant Trading Firm — Quant Intelligence +
# Market Analysis Completion Phase," Phase F — the English-language
# strategy compiler. Every field here is a real, structured, versioned,
# reproducible representation — never a natural-language string treated
# as if it were precise. See app/strategy_compiler.py's module docstring
# for the full deterministic compilation approach (a real pattern-
# matcher against a disclosed known vocabulary, never an LLM guess) and
# app/strategy_engine.py for how a CompiledStrategyDefinition is
# actually replayed against real candle history.
StrategyIndicatorName = Literal[
    "price_close", "price_open", "price_high", "price_low", "sma", "ema", "rsi", "macd_line", "macd_signal", "macd_histogram", "stochastic_percent_k", "stochastic_percent_d", "atr", "vwap"
]


class StrategyIndicatorRef(CamelModel):
    """One real, computable value at a given bar — either a raw OHLC
    field or a named indicator from app/technical_indicators.py (the one
    authoritative implementation; this DSL never re-derives its own
    indicator math). `period` is required for every indicator except
    vwap and the raw price fields."""

    indicator: StrategyIndicatorName
    period: int | None = None


StrategyConditionOperator = Literal["gt", "gte", "lt", "lte", "eq", "crosses_above", "crosses_below"]


class StrategyCondition(CamelModel):
    """One real, evaluable boolean condition comparing a real indicator
    value against either another real indicator value or a literal
    threshold. `crosses_above`/`crosses_below` are real, checkable
    two-bar transitions (true only on the bar where the relationship
    just flipped), never a same-bar snapshot mislabeled as a cross."""

    id: str
    left: StrategyIndicatorRef
    operator: StrategyConditionOperator
    right_indicator: StrategyIndicatorRef | None = Field(default=None, alias="rightIndicator")
    right_value: float | None = Field(default=None, alias="rightValue")
    detail: str


StrategySequenceStepType = Literal["initial_state", "trigger", "requirement", "entry"]
CandleDirection = Literal["bullish", "bearish"]


class StrategySequenceStep(CamelModel):
    """One real, ordered step in the strategy's own real sequence — the
    literal state-machine shape the CEO's own worked example describes
    (INITIAL CONDITION -> TRIGGER -> PULLBACK -> ENTRY), not flattened
    into a single AND-of-conditions filter, which would silently discard
    the real sequential/stateful meaning of "wait for X, THEN Y."
    `requirement` steps (e.g. "at least two bearish candles") carry
    `min_consecutive_bars` + `candle_direction` rather than a
    `StrategyCondition`, since a consecutive-count requirement is a
    real, different shape of check than a same-bar comparison."""

    id: str
    step_type: StrategySequenceStepType = Field(alias="stepType")
    condition: StrategyCondition | None = None
    min_consecutive_bars: int | None = Field(default=None, alias="minConsecutiveBars")
    candle_direction: CandleDirection | None = Field(default=None, alias="candleDirection")
    detail: str


StrategyStopMethod = Literal["chandelier", "swing_level", "fixed_percent"]


class StrategyStopSpec(CamelModel):
    """A real, named, reproducible stop-placement method — never a bare
    number with no disclosed derivation. `chandelier` reuses the exact
    same real formula app/ema_pullback_research.py's own Chandelier Stop
    uses (`atr_period`/`atr_multiplier` params); `swing_level` places the
    stop at the real leg extreme the sequence's own trigger step
    established (no separate params needed); `fixed_percent` is a real,
    simple percent-of-entry-price distance, disclosed as the least
    market-structure-aware of the three."""

    method: StrategyStopMethod
    atr_period: int | None = Field(default=None, alias="atrPeriod")
    atr_multiplier: float | None = Field(default=None, alias="atrMultiplier")
    percent: float | None = None


StrategyTargetMethod = Literal["r_multiple", "fixed_percent"]


class StrategyTargetSpec(CamelModel):
    method: StrategyTargetMethod
    value: float


class StrategyAmbiguity(CamelModel):
    """One real, disclosed piece of source text this compiler
    deliberately refused to silently convert into an invented threshold
    — per the directive's own explicit rule: "the compiler must NOT
    silently invent arbitrary thresholds... mark the strategy as
    ambiguous... prevent a supposedly precise backtest until the
    ambiguity is resolved." `suggested_resolution` is a real, disclosed
    hint (e.g. "specify a numeric ATR multiple"), never an auto-applied
    default."""

    phrase: str
    context: str
    reason: str
    suggested_resolution: str | None = Field(default=None, alias="suggestedResolution")


CompiledStrategyStatus = Literal["compiled", "ambiguous", "invalid"]


class CompiledStrategyDefinition(CamelModel):
    """The one real, structured, versioned, reproducible representation
    a compiled strategy takes — deterministic, auditable, and directly
    backtestable by app/strategy_engine.py. `source_text` preserves the
    CEO's/agent's own original English exactly, so every compiled field
    below can be audited back against what was actually said.
    `status == "compiled"` is the only status app/strategy_engine.py
    will ever backtest — "ambiguous"/"invalid" definitions are real,
    disclosed, blocked states, never silently backtested with invented
    values filled in."""

    id: str
    name: str
    source_text: str = Field(alias="sourceText")
    version: int
    created_by: AgentId = Field(alias="createdBy")
    created_at: str = Field(alias="createdAt")
    timeframe: str
    sequence: list[StrategySequenceStep] = Field(default_factory=list)
    stop: StrategyStopSpec | None = None
    target: StrategyTargetSpec | None = None
    ambiguities: list[StrategyAmbiguity] = Field(default_factory=list)
    status: CompiledStrategyStatus
    detail: str


class CompileStrategyRequest(CamelModel):
    name: str
    source_text: str = Field(alias="sourceText")
    timeframe: str = "1h"
    # Compilation itself is stateless (computed fresh every call, the
    # same CAGS convention every other new read this codebase adds
    # follows) — this codebase does not yet persist compiled strategy
    # definitions. A caller re-compiling a strategy it already tracks
    # elsewhere (e.g. a future persistence layer) can pass the prior
    # version here to get a real, incremented `version` on the result;
    # omitted, a fresh compile always reads version 1.
    previous_version: int | None = Field(default=None, alias="previousVersion")


class CompiledStrategyBacktestResult(CamelModel):
    """A real bar-by-bar replay of one `CompiledStrategyDefinition`
    (status == "compiled" only) against real (mock) candle history —
    the same real per-symbol trade-record/bucket-aggregation shape
    app/ema_pullback_research.py already established, reused directly
    rather than re-invented, so every compiled strategy's results are
    directly comparable to that same reference strategy's own real
    numbers.

    CEO directive "Professional Quant Firm Phase" follow-up — every
    `EmaPullbackTradeRecord` already carries its own real, per-trade
    `regimeTrend`/`regimeVolatility` read (see that field's own
    docstring: a self-contained proxy computed only from data available
    up to the trade's own entry bar, never a look-ahead label), and
    `EmaPullbackResearchResult` (the reference 50 EMA strategy) already
    aggregates those into `regimeTrendBreakdown`/
    `regimeVolatilityBreakdown` — but this newer, general compiled-
    strategy engine never did, a real, disclosed gap. `regimeTrendBreakdown`/
    `regimeVolatilityBreakdown` below close it, aggregated identically to
    `sessionBreakdown`/`instrumentBreakdown` via the same
    `aggregate_bucket()`, from data this engine already computes — no new
    regime-detection logic, no new field on the trade record."""

    id: str
    definition_id: str = Field(alias="definitionId")
    definition_version: int = Field(alias="definitionVersion")
    symbols_tested: list[str] = Field(alias="symbolsTested")
    timeframe: str
    candles_per_symbol: int = Field(alias="candlesPerSymbol")
    overall: EmaPullbackStatsBucket
    session_breakdown: list[EmaPullbackStatsBucket] = Field(default_factory=list, alias="sessionBreakdown")
    instrument_breakdown: list[EmaPullbackStatsBucket] = Field(default_factory=list, alias="instrumentBreakdown")
    regime_trend_breakdown: list[EmaPullbackStatsBucket] = Field(default_factory=list, alias="regimeTrendBreakdown")
    regime_volatility_breakdown: list[EmaPullbackStatsBucket] = Field(default_factory=list, alias="regimeVolatilityBreakdown")
    model_validation: ModelValidationReport | None = Field(default=None, alias="modelValidation")
    monte_carlo: StrategyMonteCarloResult | None = Field(default=None, alias="monteCarlo")
    data_honesty_note: str = Field(alias="dataHonestyNote")
    generated_at: str = Field(alias="generatedAt")


class WalkForwardWindowResult(CamelModel):
    """One real, disjoint chronological slice of a symbol's own real
    candle series — the compiled definition is backtested against ONLY
    this window's own bars (see app/walk_forward.py's own module
    docstring for the structural no-look-ahead guarantee this gives)."""

    window_index: int = Field(alias="windowIndex")
    start_timestamp: str = Field(alias="startTimestamp")
    end_timestamp: str = Field(alias="endTimestamp")
    bucket: EmaPullbackStatsBucket


class WalkForwardSymbolResult(CamelModel):
    symbol: str
    windows: list[WalkForwardWindowResult] = Field(default_factory=list)
    positive_window_count: int = Field(alias="positiveWindowCount")
    negative_window_count: int = Field(alias="negativeWindowCount")
    evaluated_window_count: int = Field(alias="evaluatedWindowCount")
    detail: str


class WalkForwardValidationResult(CamelModel):
    """CEO directive "...Quant Intelligence + Market Analysis Completion
    Phase (Next Research + Validation Pass)," item 4 — genuine walk-
    forward validation: the SAME fixed compiled definition (no per-
    window parameter reselection — see app/walk_forward.py's own module
    docstring for that disclosed scope boundary) re-run independently
    against consecutive, non-overlapping real chronological windows of
    each symbol's own real candle series. `verdict` describes STABILITY
    (does the edge hold up window after window), never a claim of
    walk-forward OPTIMIZATION (see app/parameter_sensitivity.py for
    that separate, disjoint capability)."""

    id: str
    definition_id: str = Field(alias="definitionId")
    definition_version: int = Field(alias="definitionVersion")
    window_bars: int = Field(alias="windowBars")
    symbols: list[WalkForwardSymbolResult] = Field(default_factory=list)
    verdict: Literal["stable", "unstable", "insufficient_data"]
    detail: str
    data_honesty_note: str = Field(alias="dataHonestyNote")
    generated_at: str = Field(alias="generatedAt")


class ParameterSensitivityPoint(CamelModel):
    """One real, full-series backtest of the SAME compiled definition
    with exactly one stop/target parameter nudged to a neighboring real
    value — see app/parameter_sensitivity.py for the sweep methodology."""

    label: str
    value: float
    bucket: EmaPullbackStatsBucket


class ParameterSensitivityAxisResult(CamelModel):
    parameter: Literal["stop", "target"]
    sweepable: bool
    base_value: float | None = Field(default=None, alias="baseValue")
    points: list[ParameterSensitivityPoint] = Field(default_factory=list)
    detail: str


class ParameterSensitivityResult(CamelModel):
    """CEO directive "...Quant Intelligence + Market Analysis Completion
    Phase (Next Research + Validation Pass)," item 5 — real, one-
    parameter-at-a-time sensitivity over a compiled definition's own
    stop and target values (never a full grid search — see
    app/parameter_sensitivity.py's own module docstring for that
    disclosed methodology choice). `verdict` describes ROBUSTNESS (does
    the sign of the edge survive neighboring parameter choices), never a
    recommendation to adopt any specific point — this schema has no
    "best combination" field by design, per item 10's own warning
    against celebrating the best of many trials."""

    id: str
    definition_id: str = Field(alias="definitionId")
    definition_version: int = Field(alias="definitionVersion")
    stop_axis: ParameterSensitivityAxisResult | None = Field(default=None, alias="stopAxis")
    target_axis: ParameterSensitivityAxisResult | None = Field(default=None, alias="targetAxis")
    verdict: Literal["robust", "fragile", "insufficient_data"]
    detail: str
    multiple_testing_note: str = Field(alias="multipleTestingNote")
    data_honesty_note: str = Field(alias="dataHonestyNote")
    generated_at: str = Field(alias="generatedAt")


class CostSensitivityScenario(CamelModel):
    """One real cost scenario — the SAME real, already-closed trades a
    zero-friction backtest produced, with a real per-leg basis-point
    friction cost deducted from each trade's own realized R-multiple
    (never a re-run with different entries/exits — the setups themselves
    never change, only what they were really worth after real friction).
    See app/cost_sensitivity.py for where `cost_bps_per_leg` comes from."""

    label: str
    cost_bps_per_leg: float = Field(alias="costBpsPerLeg")
    bucket: EmaPullbackStatsBucket


class CostSensitivityResult(CamelModel):
    """CEO directive "...Quant Intelligence + Market Analysis Completion
    Phase (Next Research + Validation Pass)," item 6 — real transaction-
    cost/slippage sensitivity, reusing this codebase's OWN existing real
    cost constants (app/portfolio.py's `TRANSACTION_COST_BPS`, app/
    execution_quality.py's `BASE_SLIPPAGE_BPS`/`MAX_SLIPPAGE_BPS` — the
    same numbers live paper trading already charges on every fill) as
    the scenario ladder, never invented friction numbers."""

    id: str
    definition_id: str = Field(alias="definitionId")
    definition_version: int = Field(alias="definitionVersion")
    scenarios: list[CostSensitivityScenario] = Field(default_factory=list)
    verdict: Literal["cost_resilient", "cost_sensitive", "insufficient_data"]
    detail: str
    data_honesty_note: str = Field(alias="dataHonestyNote")
    generated_at: str = Field(alias="generatedAt")


class LookAheadViolation(CamelModel):
    """One real, concrete look-ahead finding — a real setup the full
    candle series found that could NOT be reproduced using only the
    candles available up to and including its own entry bar. See
    app/leakage_audit.py for the real truncate-and-re-detect
    methodology."""

    entry_index: int = Field(alias="entryIndex")
    entry_timestamp: str = Field(alias="entryTimestamp")
    direction: str
    detail: str


class LookAheadAuditResult(CamelModel):
    """CEO directive "...Quant Intelligence + Market Analysis Completion
    Phase (Next Research + Validation Pass)," item 7 — a real, structural
    look-ahead audit: every real setup a compiled definition's own
    generic detector finds against the full candle series is
    independently re-detected against a series TRUNCATED to end exactly
    at that setup's own entry bar. A setup that only appears with the
    full series and vanishes (or changes) once later candles are removed
    is real, structural proof of a future-data dependency — never a
    guess or a code-review claim."""

    id: str
    definition_id: str = Field(alias="definitionId")
    definition_version: int = Field(alias="definitionVersion")
    setups_checked: int = Field(alias="setupsChecked")
    violations: list[LookAheadViolation] = Field(default_factory=list)
    verdict: Literal["clean", "violations_found", "insufficient_data"]
    detail: str
    generated_at: str = Field(alias="generatedAt")


class SurvivorshipBiasRead(CamelModel):
    """CEO directive "...Quant Intelligence + Market Analysis Completion
    Phase (Next Research + Validation Pass)," item 8 — a real,
    disclosed data-availability interface for survivorship-bias
    checking, not a real check. See app/survivorship.py's own module
    docstring for exactly why this always reads `unavailable`: this
    codebase's research universe (app/watchlist.py's SEED_SYMBOLS/
    EXTRA_SYMBOL_POOL) is a fixed, static, always-present pool with no
    historical constituent or delisting data behind it — there is
    nothing yet for a real check to audit. Defined now so a future real
    historical-universe data source has a real, typed interface to
    plug into, rather than survivorship bias being silently ignored."""

    symbol: str
    status: Literal["unavailable"]
    detail: str


OverfittingVerdict = Literal[
    "robust", "fragile", "insufficient_data", "overfit_suspected", "oos_failure", "pending_validation"
]


class OverfittingDiagnosis(CamelModel):
    """CEO directive "Professional Quant Firm Phase," Feature 39 — a
    real, deterministic classification into the directive's own
    requested vocabulary (ROBUST / FRAGILE / INSUFFICIENT_DATA /
    OVERFIT_SUSPECTED / OOS_FAILURE / PENDING_VALIDATION), computed
    purely by re-reading three already-real, already-tested verdicts
    (`WalkForwardValidationResult.verdict`, `ParameterSensitivityResult.
    verdict`, `CostSensitivityResult.verdict`) — see app/
    overfitting_diagnostics.py for the exact, disclosed priority rule.
    This class introduces no new statistic of its own; it only relabels
    existing real evidence into one shared vocabulary so a CEO/agent
    never has to reconcile three differently-worded verdicts by hand."""

    verdict: OverfittingVerdict
    detail: str
    walk_forward_verdict: Literal["stable", "unstable", "insufficient_data"] = Field(alias="walkForwardVerdict")
    parameter_sensitivity_verdict: Literal["robust", "fragile", "insufficient_data"] = Field(alias="parameterSensitivityVerdict")
    cost_sensitivity_verdict: Literal["cost_resilient", "cost_sensitive", "insufficient_data"] = Field(alias="costSensitivityVerdict")


class BuyAndHoldBaseline(CamelModel):
    """CEO directive "Quant Research Factory / Strategy Discovery
    Engine," Phase 5 — one real symbol's buy-and-hold percent price
    return over a real (mock) candle window, computed purely from
    `app.market_data.market_data_provider.get_candles()`'s own real
    first-close/last-close prices. No strategy logic, no position
    sizing, no trades — the simplest possible honest baseline. See
    app/baseline_comparison.py for the real, disclosed reason this is
    never blended with a strategy's own R-multiple-based stats into one
    number."""

    symbol: str
    start_price: float = Field(alias="startPrice")
    end_price: float = Field(alias="endPrice")
    return_pct: float = Field(alias="returnPct")
    candle_count: int = Field(alias="candleCount")


class ResearchExperimentRecord(CamelModel):
    """CEO directive "...Quant Intelligence + Market Analysis Completion
    Phase (Next Research + Validation Pass)," item 11 — the Research
    Desk's one real, reproducible record of a full research pass over a
    compiled strategy: what was tested, on what data, using what
    assumptions, and why the resulting conclusion was reached. Every
    field below is a direct, unmodified result from an already-real,
    already-tested module (app/strategy_engine.py, app/walk_forward.py,
    app/parameter_sensitivity.py, app/cost_sensitivity.py, app/
    leakage_audit.py, app/model_validation.py via the backtest result's
    own `modelValidation`) — this schema orchestrates and packages,
    never recomputes. `conclusion` is a real, disclosed synthesis rule
    over those already-real verdicts (see app/research_experiment.py's
    own module docstring for the exact rule) — never a fabricated
    summary judgment. Computed fresh per request, never persisted — the
    same CAGS convention this whole directive family uses throughout."""

    id: str
    definition_id: str = Field(alias="definitionId")
    definition_name: str = Field(alias="definitionName")
    definition_version: int = Field(alias="definitionVersion")
    source_text: str = Field(alias="sourceText")
    symbols_tested: list[str] = Field(alias="symbolsTested")
    timeframe: str
    candles_per_symbol: int = Field(alias="candlesPerSymbol")
    backtest: CompiledStrategyBacktestResult
    walk_forward: WalkForwardValidationResult = Field(alias="walkForward")
    parameter_sensitivity: ParameterSensitivityResult = Field(alias="parameterSensitivity")
    cost_sensitivity: CostSensitivityResult = Field(alias="costSensitivity")
    look_ahead_audit: LookAheadAuditResult = Field(alias="lookAheadAudit")
    # CEO directive "Professional Quant Firm Phase," Feature 39 — the
    # unified overfitting-diagnostic classification (see
    # app/overfitting_diagnostics.py), packaged alongside `conclusion`
    # rather than replacing it: `conclusion` is this module's own
    # broader synthesis (it also weighs model validation and look-ahead
    # cleanliness); `overfitting_diagnosis` is narrowly the directive's
    # own requested generalization read (walk-forward + parameter +
    # cost sensitivity only).
    overfitting_diagnosis: OverfittingDiagnosis = Field(alias="overfittingDiagnosis")
    conclusion: str
    # CEO directive "Quant Research Factory / Strategy Discovery Engine,"
    # Phase 5 — a real, per-symbol buy-and-hold price-return baseline
    # over the exact same real (mock) candle window `backtest` above
    # already tested. See app/baseline_comparison.py's own module
    # docstring for why this is deliberately NOT blended into a single
    # "beat the market by X%" number with the strategy's own R-multiple
    # stats (different units) — its purpose is real regime context, not
    # a performance comparison. `default_factory=list` — an experiment
    # filed before this field existed reads an honestly empty list, not
    # a fabricated baseline.
    buy_and_hold_baseline: list[BuyAndHoldBaseline] = Field(default_factory=list, alias="buyAndHoldBaseline")
    data_honesty_note: str = Field(alias="dataHonestyNote")
    generated_at: str = Field(alias="generatedAt")


QuantResearchOutcome = Literal["promising", "rejected", "inconclusive"]


class QuantResearchExperiment(CamelModel):
    """CEO directive "Professional Quant Firm Phase," Feature 36 — the
    Quant Research Lab's one real, PERSISTED, searchable experiment
    record. Wraps an already-real `ResearchExperimentRecord` (this
    schema adds no new backtest math) with the hypothesis-driven
    metadata the directive asks for: a real testable hypothesis (free
    CEO/agent text, never a hard-coded conclusion — `record.conclusion`/
    `record.overfitting_diagnosis` are independently computed real
    evidence, checked against the hypothesis, not derived from it), the
    researcher who filed it, and a real, disclosed `outcome` derived
    from that already-real evidence (see app/quant_research_lab.py's
    `_classify_outcome()`).

    DEPARTURE FROM CAGS, DISCLOSED. Every other schema in this directive
    family (`ResearchExperimentRecord` included) is computed fresh per
    request and never persisted. Feature 36 explicitly requires
    "searchable" and duplicate-detection, which is meaningless without
    real storage — so this one schema deliberately departs from CAGS and
    follows this codebase's own established ever-growing,
    never-deleted precedent instead (`StrategyHallOfFameEntry`/
    `FailedStrategyArchiveEntry` below): every experiment, including a
    rejected one, stays permanently in `GameSaveState.
    quant_research_experiments` — matching the directive's own "failed
    research must produce searchable institutional knowledge, never
    deleted merely because it looks bad.\""""

    id: str
    hypothesis: str
    # CEO directive "Quant Research Factory / Strategy Discovery Engine,"
    # Phase 1 — the smallest real abstraction between a raw idea and a
    # compiled, testable strategy: WHY the researcher expects this to
    # work, and WHAT would prove them wrong. `market_scope`/`timeframe`
    # deliberately aren't duplicated here — `record.symbols_tested`/
    # `record.timeframe` already carry those, and re-stating them here
    # would be a second, driftable copy of the same real fields.
    # Entry/exit/risk "concepts" are likewise not separate free-text
    # fields — the moment a hypothesis compiles, `CompiledStrategyDefinition`
    # already makes those deterministic and real; echoing an informal
    # pre-compilation guess of the same thing would add no real signal.
    # `None` only for an experiment filed before this field existed —
    # never backfilled, never guessed.
    expected_mechanism: str | None = Field(default=None, alias="expectedMechanism")
    falsification_criteria: str | None = Field(default=None, alias="falsificationCriteria")
    researcher_agent_id: AgentId = Field(alias="researcherAgentId")
    outcome: QuantResearchOutcome
    outcome_reason: str = Field(alias="outcomeReason")
    record: ResearchExperimentRecord
    # CEO directive "Quant Research Factory / Strategy Discovery Engine,"
    # Phase 10 — real multiple-testing/research-selection-bias
    # visibility, never a fabricated statistical correction. This is a
    # real, counted total of how many experiments (including this one)
    # share this strategy's real `record.definitionName` at the moment
    # this one was filed — a real proxy for "how many times has this
    # basic idea been tried," the same real signal the directive's own
    # "track number of experiments/parameter search size" ask ultimately
    # wants. Deliberately NOT a p-value, false-discovery-rate, or
    # corrected significance level — no such statistic can be honestly
    # derived from this codebase's real backtest outputs (expectancy/
    # profit-factor/Sharpe over real trades, not hypothesis-test
    # p-values), and the directive's own rule is explicit: "do not claim
    # statistical significance unless the implemented method actually
    # supports it." `None` only for an experiment filed before this
    # field existed — the true historical count for those is genuinely
    # unknown, never guessed as 1.
    family_experiment_count: int | None = Field(default=None, alias="familyExperimentCount")
    created_at: str = Field(alias="createdAt")


class QuantResearchExperimentSimilarity(CamelModel):
    """One real, disclosed near-duplicate match against an already-
    persisted experiment — see app/quant_research_lab.py's
    `find_similar_experiments()` for the exact (simple, disclosed
    word-overlap) heuristic. Never a claim of semantic/NLP
    understanding of the hypothesis text.

    CEO directive "Quant Research Factory / Strategy Discovery Engine,"
    Phase 14/16 — `outcome`/`outcome_reason` are the matched
    experiment's own already-real, already-computed fields, copied
    here (never recomputed) so a CEO/agent sees not just "this looks
    similar" but "and it was already REJECTED, here's why" before
    spending real compute re-testing a known-failed idea — the
    directive's own "do not repeatedly rediscover the same failed
    idea." No automated hypothesis-generation loop exists in this
    codebase to attach memory-consultation to (every experiment is
    filed by explicit CEO/agent action, never auto-proposed) — this is
    the one honest, real point where prior research outcome feedback
    can reach whoever is about to file a new one."""

    experiment_id: str = Field(alias="experimentId")
    hypothesis: str
    overlap_score: float = Field(alias="overlapScore")
    reason: str
    outcome: QuantResearchOutcome
    outcome_reason: str = Field(alias="outcomeReason")


class SubmitQuantResearchExperimentResult(CamelModel):
    """The real response to filing a new Quant Research Lab experiment
    — the newly-persisted record plus any real near-duplicate prior
    experiments this codebase found (the directive's own "check before
    creating a new experiment whether an equivalent one exists"),
    surfaced for CEO/agent judgment rather than silently blocked."""

    experiment: QuantResearchExperiment
    similar_experiments: list[QuantResearchExperimentSimilarity] = Field(default_factory=list, alias="similarExperiments")


class StrategyTournamentEntry(CamelModel):
    """One real comparison row — every field a direct, unmodified read
    from that strategy's own `ResearchExperimentRecord` (see
    app/strategy_tournament.py). Never a fabricated composite score:
    app/strategy_tournament.py's ranking work happens entirely through
    named-slot superlatives (`StrategyTournamentResult`'s own
    `highest_*`/`lowest_*` fields) and staged elimination
    (`StrategyTournamentResult.rounds`), each citing one real, named
    dimension at a time — never a single blended number."""

    definition_id: str = Field(alias="definitionId")
    definition_name: str = Field(alias="definitionName")
    definition_version: int = Field(alias="definitionVersion")
    trade_count: int = Field(alias="tradeCount")
    win_rate_pct: float | None = Field(default=None, alias="winRatePct")
    expectancy_r: float | None = Field(default=None, alias="expectancyR")
    profit_factor: float | None = Field(default=None, alias="profitFactor")
    max_drawdown_r: float | None = Field(default=None, alias="maxDrawdownR")
    sharpe_ratio: float | None = Field(default=None, alias="sharpeRatio")
    sortino_ratio: float | None = Field(default=None, alias="sortinoRatio")
    calmar_ratio: float | None = Field(default=None, alias="calmarRatio")
    walk_forward_positive_window_pct: float | None = Field(default=None, alias="walkForwardPositiveWindowPct")
    walk_forward_verdict: Literal["stable", "unstable", "insufficient_data"] = Field(alias="walkForwardVerdict")
    parameter_sensitivity_verdict: Literal["robust", "fragile", "insufficient_data"] = Field(alias="parameterSensitivityVerdict")
    cost_sensitivity_verdict: Literal["cost_resilient", "cost_sensitive", "insufficient_data"] = Field(alias="costSensitivityVerdict")
    look_ahead_verdict: Literal["clean", "violations_found", "insufficient_data"] = Field(alias="lookAheadVerdict")
    model_validation_verdict: ModelValidationVerdict | None = Field(default=None, alias="modelValidationVerdict")
    overfitting_verdict: OverfittingVerdict = Field(alias="overfittingVerdict")
    # CEO directive "Professional Quant Firm Phase 41-45," Feature 43 —
    # Regime-Adaptive Strategy Selection. Real evidence already computed
    # by app/strategy_engine.py's regimeTrendBreakdown/
    # regimeVolatilityBreakdown (never re-derived): "regime_validated"
    # means at least one real regime bucket (trend or volatility) hit
    # the same enough_evidence sample-size bar every other verdict on
    # this entry uses AND showed a real positive expectancy in that
    # bucket. "no_validated_regime" means every regime bucket that
    # cleared the sample-size bar showed zero or negative expectancy —
    # a real, confirmed finding this module's Round 9 uses to eliminate
    # (see run_strategy_tournament's own docstring). "insufficient_data"
    # means no regime bucket ever cleared the sample-size bar — missing
    # evidence, never treated as negative evidence, and never
    # eliminated.
    regime_stability_verdict: Literal["regime_validated", "no_validated_regime", "insufficient_data"] = Field(alias="regimeStabilityVerdict")
    regime_stability_detail: str = Field(alias="regimeStabilityDetail")
    eliminated_at_round: int | None = Field(default=None, alias="eliminatedAtRound")
    elimination_reason: str | None = Field(default=None, alias="eliminationReason")


class StrategyTournamentRoundResult(CamelModel):
    """One real elimination round. `blocked=True` means this round's own
    FULL real gate (as the directive originally asked for it) cannot be
    evaluated because the underlying capability does not exist yet in
    this codebase (see app/strategy_tournament.py's own module docstring
    for exactly which round this applies to and why) — every entrant
    passes a blocked round automatically, and `detail` discloses the
    architectural gap rather than fabricating a result. Round 7 sets
    `blocked=True` alongside a real, partial signal
    (`StrategyTournamentResult.pairCorrelations`) — real return
    correlation is now computed, but a full portfolio-level backtest
    (shared capital, combined position sizing, simultaneous multi-
    strategy drawdown) still is not, so the round still never
    eliminates."""

    round_number: int = Field(alias="roundNumber")
    name: str
    description: str
    survivors: list[str] = Field(default_factory=list)
    eliminated: list[str] = Field(default_factory=list)
    blocked: bool = False
    detail: str


class StrategyPairCorrelation(CamelModel):
    """CEO directive "Professional Quant Firm Phase," Feature 40, Round
    7 follow-up — a REAL Pearson correlation coefficient (see
    app/portfolio_intelligence.py's `pearson_correlation()`, reused
    directly, never a second implementation) between two candidate
    strategies' own already-computed walk-forward window expectancy
    sequences for one shared symbol (the same window boundaries, since
    both were tested with the same symbols/timeframe/candlesPerSymbol/
    windowBars). `correlation` is `None` (never a fabricated `0.0`)
    below 3 real paired windows with evidence on both sides. This is a
    REAL, disclosed signal about how similarly two strategies' returns
    moved — high positive correlation suggests less real diversification
    benefit from running both — but it is explicitly NOT a full
    portfolio-level backtest: it does not model shared capital, combined
    position sizing, or simultaneous drawdown timing."""

    definition_id_a: str = Field(alias="definitionIdA")
    definition_id_b: str = Field(alias="definitionIdB")
    symbol: str
    correlation: float | None
    windows_compared: int = Field(alias="windowsCompared")
    detail: str


class StrategyTournamentResult(CamelModel):
    """CEO directive "Professional Quant Firm Phase," Feature 40 — the
    Quant Strategy Tournament. Computed fresh per request (CAGS — the
    same convention `ResearchExperimentRecord` uses; nothing here is
    persisted), by running every candidate `CompiledStrategyDefinition`
    through the already-real `run_research_experiment()` pipeline once
    each (see app/strategy_tournament.py) — no new backtest math, no
    second validation engine. `production_candidates` is a real, cited
    LABEL (every real round survived) for CEO visibility only — it is
    never an autonomous production promotion and never bypasses this
    codebase's own separate risk/governance approval flow."""

    id: str
    entries: list[StrategyTournamentEntry] = Field(default_factory=list)
    rounds: list[StrategyTournamentRoundResult] = Field(default_factory=list)
    pair_correlations: list[StrategyPairCorrelation] = Field(default_factory=list, alias="pairCorrelations")
    highest_expectancy: StrategyExecutiveDashboardEntry | None = Field(default=None, alias="highestExpectancy")
    highest_profit_factor: StrategyExecutiveDashboardEntry | None = Field(default=None, alias="highestProfitFactor")
    highest_sharpe_ratio: StrategyExecutiveDashboardEntry | None = Field(default=None, alias="highestSharpeRatio")
    lowest_max_drawdown: StrategyExecutiveDashboardEntry | None = Field(default=None, alias="lowestMaxDrawdown")
    most_walk_forward_stable: StrategyExecutiveDashboardEntry | None = Field(default=None, alias="mostWalkForwardStable")
    production_candidates: list[str] = Field(default_factory=list, alias="productionCandidates")
    data_honesty_note: str = Field(alias="dataHonestyNote")
    generated_at: str = Field(alias="generatedAt")


# Distinct from the trade-scoped ExecutiveAction (trade_normally/
# reduce_risk/wait/...) — a strategy graduating through the Validation
# Laboratory needs strategy-lifecycle actions, not single-trade ones.
StrategyExecutiveAction = Literal[
    "advance", "request_more_evidence", "hold_for_improvement", "reject"
]


class StrategyDepartmentOpinion(CamelModel):
    """Reuses the exact same 9 real department seats as Feature 50's
    ExecutiveDepartmentRole/DepartmentOpinion (app/executive_intelligence.py)
    — Strategy-scoped rather than TradeProposal-scoped, with a richer
    evidence/concerns/suggestedImprovements field set per the brief. The
    brief's 9th named seat, "Brain Room," is not a distinct department
    anywhere in this codebase (see ExecutiveIntelPanel.tsx's own real/cut
    note) — it reuses the same devils_advocate seat every other 9-role
    read in this codebase already does."""

    role: ExecutiveDepartmentRole
    department_label: str = Field(alias="departmentLabel")
    agent_id: AgentId | None = Field(default=None, alias="agentId")
    stance: ExecutiveStance
    confidence_pct: float = Field(alias="confidencePct")
    evidence: list[str] = Field(default_factory=list)
    concerns: list[str] = Field(default_factory=list)
    suggested_improvements: list[str] = Field(
        default_factory=list, alias="suggestedImprovements"
    )


class StrategyExecutiveReview(CamelModel):
    id: str
    strategy_id: str = Field(alias="strategyId")
    strategy_name: str = Field(alias="strategyName")
    opinions: list[StrategyDepartmentOpinion]
    overall_confidence_pct: float = Field(alias="overallConfidencePct")
    recommendation: StrategyExecutiveAction
    reason: str
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


class StrategyFounderApproval(CamelModel):
    """The Founder Council's real, checkable verdict on a strategy — a
    new mode of the same real threshold-based approval pattern
    app/founders.py's generate_breakthrough_review() already established
    for Black Box Projects, applied here to a Strategy instead."""

    id: str
    strategy_id: str = Field(alias="strategyId")
    strategy_name: str = Field(alias="strategyName")
    sim_day: int = Field(alias="simDay")
    evidence_summary: str = Field(alias="evidenceSummary")
    confidence_pct: float = Field(alias="confidencePct")
    verdict: Literal["approved", "rejected"]
    verdict_reason: str = Field(alias="verdictReason")
    created_at: str = Field(alias="createdAt")


class StrategyConfidenceScore(CamelModel):
    id: str
    strategy_id: str = Field(alias="strategyId")
    strategy_name: str = Field(alias="strategyName")
    overall_confidence_pct: float = Field(alias="overallConfidencePct")
    evidence: list[str] = Field(default_factory=list)
    known_strengths: list[str] = Field(default_factory=list, alias="knownStrengths")
    known_weaknesses: list[str] = Field(default_factory=list, alias="knownWeaknesses")
    risk_rating: Literal["low", "moderate", "elevated", "high"] = Field(
        alias="riskRating"
    )
    recommended_position_size_pct: float = Field(alias="recommendedPositionSizePct")
    recommended_market_conditions: list[str] = Field(
        default_factory=list, alias="recommendedMarketConditions"
    )
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


# Design Bible Chapter 62 — the Innovation Lab's Experiment
# Classification. A real read over the strategy's own Monte Carlo
# projections (see app/strategy_lab.py's compute_experiment_tier()) —
# only ever set once a real StrategyMonteCarloResult exists, never
# guessed beforehand.
ExperimentTier = Literal["minor", "moderate", "major", "transformational"]


class StrategyDossier(CamelModel):
    """The brief's 'professional Strategy Report' — an assembling read
    over every other real Feature 52 artifact for this strategy, never a
    second copy of their data. Generated fresh on request (see
    app/strategy_lab.py's generate_strategy_dossier()), the same
    'real inputs already live somewhere permanent, no new persistence
    needed' reasoning as ExecutiveRecommendation/WhatIfSimulation."""

    strategy_id: str = Field(alias="strategyId")
    strategy_name: str = Field(alias="strategyName")
    created_by: AgentId = Field(alias="createdBy")
    purpose: str
    stage: StrategyStage
    latest_report: StrategyReport | None = Field(default=None, alias="latestReport")
    latest_review: StrategyReview | None = Field(default=None, alias="latestReview")
    monte_carlo: StrategyMonteCarloResult | None = Field(
        default=None, alias="monteCarlo"
    )
    regime_test: StrategyRegimeTestReport | None = Field(
        default=None, alias="regimeTest"
    )
    liquidity_validation: StrategyLiquidityValidation | None = Field(
        default=None, alias="liquidityValidation"
    )
    executive_review: StrategyExecutiveReview | None = Field(
        default=None, alias="executiveReview"
    )
    founder_approval: StrategyFounderApproval | None = Field(
        default=None, alias="founderApproval"
    )
    confidence: StrategyConfidenceScore | None = None
    # Design Bible Chapter 62 — Experiment Tiering. Both None until a
    # real Monte Carlo result exists for this strategy.
    experiment_tier: ExperimentTier | None = Field(default=None, alias="experimentTier")
    experiment_tier_rationale: str | None = Field(default=None, alias="experimentTierRationale")
    generated_at: str = Field(alias="generatedAt")


StrategyHealthStatus = Literal[
    "excellent",
    "healthy",
    "stable",
    "needs_review",
    "declining",
    "critical",
    "retire_candidate",
]
StrategyHealthTrend = Literal["improving", "stable", "declining"]


class StrategyHealthAssessment(CamelModel):
    """v0.7 Feature 52 (Part 2) — a real recent-vs-lifetime trend read
    over a strategy's own SimulationResult history (see
    app/strategy_lab.py's compute_strategy_health()). Deliberately NOT
    the brief's literal 'Live Performance Monitor' — this codebase has no
    mechanism to attribute a live/paper trade back to a specific Strategy
    object (see app/sandbox.py's own module docstring), so this reads the
    real Market Simulation run history a strategy actually has, not
    fabricated live P&L."""

    id: str
    strategy_id: str = Field(alias="strategyId")
    strategy_name: str = Field(alias="strategyName")
    status: StrategyHealthStatus
    trend: StrategyHealthTrend
    recent_win_rate: float = Field(alias="recentWinRate")
    lifetime_win_rate: float = Field(alias="lifetimeWinRate")
    recent_avg_return_pct: float = Field(alias="recentAvgReturnPct")
    lifetime_avg_return_pct: float = Field(alias="lifetimeAvgReturnPct")
    recent_avg_drawdown_pct: float = Field(alias="recentAvgDrawdownPct")
    lifetime_avg_drawdown_pct: float = Field(alias="lifetimeAvgDrawdownPct")
    recent_sample_size: int = Field(alias="recentSampleSize")
    lifetime_sample_size: int = Field(alias="lifetimeSampleSize")
    reasoning: list[str] = Field(default_factory=list)
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


class StrategyHallOfFameEntry(CamelModel):
    """v0.7 Feature 52 (Part 2) — the brief's Strategy Hall of Fame:
    permanent, never evicted, only ever filed for a strategy that earned
    real, checkable induction criteria at the moment of its own
    retirement (see app/strategy_lab.py's
    generate_strategy_retirement_outcome()). 'Historical return'/'avg R'
    below are real SimulationResult aggregates, never fabricated live
    P&L — see StrategyHealthAssessment's own docstring for why."""

    id: str
    strategy_id: str = Field(alias="strategyId")
    strategy_name: str = Field(alias="strategyName")
    created_by: AgentId = Field(alias="createdBy")
    description: str
    sim_days_active: int = Field(alias="simDaysActive")
    trades_executed: int = Field(alias="tradesExecuted")
    win_rate: float = Field(alias="winRate")
    profit_factor: float = Field(alias="profitFactor")
    max_drawdown_pct: float = Field(alias="maxDrawdownPct")
    historical_return_pct: float = Field(alias="historicalReturnPct")
    legacy_notes: list[str] = Field(default_factory=list, alias="legacyNotes")
    retired_reason: str = Field(alias="retiredReason")
    sim_day: int = Field(alias="simDay")
    inducted_at: str = Field(alias="inductedAt")


class FailedStrategyArchiveEntry(CamelModel):
    """v0.7 Feature 52 (Part 2) — every strategy retirement that did not
    clear the real Hall of Fame bar (see app/strategy_lab.py's
    generate_strategy_retirement_outcome()) — never deleted, always kept
    as a real, citable lesson. 'What failed'/'lessons learned' are pulled
    from that strategy's own real StrategyReview verdicts and
    StrategyExecutiveReview concerns, never invented after the fact."""

    id: str
    strategy_id: str = Field(alias="strategyId")
    strategy_name: str = Field(alias="strategyName")
    created_by: AgentId = Field(alias="createdBy")
    failed_at_stage: StrategyStage = Field(alias="failedAtStage")
    what_failed: list[str] = Field(default_factory=list, alias="whatFailed")
    lessons_learned: list[str] = Field(default_factory=list, alias="lessonsLearned")
    retired_reason: str = Field(alias="retiredReason")
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


class StrategyExecutiveDashboardEntry(CamelModel):
    """One named slot on the Executive Dashboard (best/weakest/most
    improved/newest/highest confidence) — always cites the real strategy
    and metric_label that earned it the slot. metric_value is the real
    number behind every slot except "newest" (a date-based pick, not a
    magnitude), which always reports 0.0 here — the real date lives on
    the Strategy object's own createdAt."""

    strategy_id: str = Field(alias="strategyId")
    strategy_name: str = Field(alias="strategyName")
    metric_label: str = Field(alias="metricLabel")
    metric_value: float = Field(alias="metricValue")


class StrategyExecutiveDashboard(CamelModel):
    """v0.7 Feature 52 (Part 2) — the brief's Executive Dashboard.
    Computed fresh on request (see app/strategy_lab.py's
    compute_strategy_executive_dashboard()), the same 'every input
    already lives somewhere permanent' reasoning as StrategyDossier —
    never a second source of truth."""

    active_count: int = Field(alias="activeCount")
    in_development_count: int = Field(alias="inDevelopmentCount")
    in_validation_count: int = Field(alias="inValidationCount")
    paper_trading_count: int = Field(alias="paperTradingCount")
    approved_count: int = Field(alias="approvedCount")
    retired_count: int = Field(alias="retiredCount")
    hall_of_fame_count: int = Field(alias="hallOfFameCount")
    failed_archive_count: int = Field(alias="failedArchiveCount")
    best_strategy: StrategyExecutiveDashboardEntry | None = Field(
        default=None, alias="bestStrategy"
    )
    weakest_strategy: StrategyExecutiveDashboardEntry | None = Field(
        default=None, alias="weakestStrategy"
    )
    most_improved_strategy: StrategyExecutiveDashboardEntry | None = Field(
        default=None, alias="mostImprovedStrategy"
    )
    newest_strategy: StrategyExecutiveDashboardEntry | None = Field(
        default=None, alias="newestStrategy"
    )
    highest_confidence_strategy: StrategyExecutiveDashboardEntry | None = Field(
        default=None, alias="highestConfidenceStrategy"
    )
    generated_at: str = Field(alias="generatedAt")


class StrategyCertificationRequirement(CamelModel):
    id: str
    label: str
    met: bool
    detail: str


class StrategyCertification(CamelModel):
    """v0.7 Feature 53 — Company Certification: the brief's formal gate
    combining every already-real Feature 52 artifact into one explicit
    checklist, never a new measurement (see
    app/strategy_lab.py's compute_strategy_certification()). Two of the
    brief's thirteen requirements — Founder Approval and Final CEO
    Approval — can only ever be real once a strategy reaches Company
    Review (see app/sandbox.py's own pipeline order: paper_trading ->
    limited_live_capital -> company_review -> approved), so `certified`
    is only ever true at stage == "approved". Computed fresh on
    request — same 'every input already lives somewhere permanent'
    reasoning as StrategyDossier. 'Revocation' is real and automatic by
    construction: since every requirement is recomputed from the
    strategy's own real current state on every call, a strategy whose
    real StrategyHealthAssessment later degrades to "critical" or
    "retire_candidate" fails the Health Standing requirement and stops
    being certified the next time this is computed — no separate
    persisted "revoked" flag or event log needed."""

    strategy_id: str = Field(alias="strategyId")
    strategy_name: str = Field(alias="strategyName")
    certified: bool
    requirements: list[StrategyCertificationRequirement]
    generated_at: str = Field(alias="generatedAt")


class MarketIntelligenceReport(CamelModel):
    """The Executive Market Brief — one real, permanent snapshot per real
    in-game day (generated on the same evening cadence as CoachReport and
    the Executive Meeting Log's other daily/weekly cadences, see
    app/nexus.py), embedding that day's own real MarketIntelligenceState
    plus the day's real MarketDebate and StrategyMatch. `trade_recommendation`
    reuses the existing ExecutiveAction enum (app/executive_intelligence.py)
    rather than inventing a parallel one."""

    id: str
    sim_day: int = Field(alias="simDay")
    snapshot: MarketIntelligenceState
    debate: MarketDebate
    strategy_match: StrategyMatch = Field(alias="strategyMatch")
    trade_recommendation: ExecutiveAction = Field(alias="tradeRecommendation")
    confidence_pct: float = Field(alias="confidencePct")
    evidence: list[str] = Field(default_factory=list)
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
InnovationTierName = Literal[
    "research_contributor",
    "research_specialist",
    "innovation_leader",
    "chief_innovator",
    "legendary_innovator",
]


class InnovationState(CamelModel):
    agent_id: AgentId = Field(alias="agentId")
    points: float = 0.0
    tier: int = 0  # 0-4, index into app/innovation.py's tier tables
    tier_name: InnovationTierName = Field(
        default="research_contributor", alias="tierName"
    )


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
BlackBoxProjectStatus = Literal[
    "active", "paused", "under_review", "completed", "failed"
]
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
    viewed_breakthrough_ids: list[str] = Field(
        default_factory=list, alias="viewedBreakthroughIds"
    )
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
    # CEO directive "Professional Quant Firm Phase 41-45," Critical Task
    # #0 — real taxonomy code for this check (see NoTradeReasonCode's
    # own docstring), always the "gatekeeper_{id}" code at every real
    # app/gatekeeper.py construction site, even when passed=True (a
    # passed check has no bearing on the taxonomy; only a FAILED check's
    # code is ever actually read/aggregated). `None` only for the
    # synthetic/generic GatekeeperCheck fixtures a few other modules'
    # own tests build to exercise unrelated downstream logic (control
    # effectiveness, process adherence) against arbitrary check ids that
    # were never real Gatekeeper checks to begin with.
    code: NoTradeReasonCode | None = None


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
    # CEO directive "Professional Quant Firm Phase 41-45," Critical Task
    # #0 — same real reasons above, tagged with real taxonomy codes
    # (see NoTradeReasonCode's own docstring), one per `reasons` entry.
    reason_codes: list[NoTradeReasonCode] = Field(default_factory=list, alias="reasonCodes")
    price_at_rejection: float = Field(alias="priceAtRejection")
    rejected_sim_minutes: int = Field(alias="rejectedSimMinutes")
    outcome: GatekeeperOutcome = "pending"
    resolved_price_change_pct: float | None = Field(
        default=None, alias="resolvedPriceChangePct"
    )
    created_at: str = Field(alias="createdAt")
    resolved_at: str | None = Field(default=None, alias="resolvedAt")


# v0.7 Chapter 58 — Institutional Trade Filter & Opportunity Gatekeeper
# (app/opportunity_gatekeeper.py). A distinct, earlier-stage sibling to
# GatekeeperRejection above: this candidate never became a real
# TradeProposal the CEO could see, so there is no ceoChoice to record —
# wouldHaveRecommended is the six-agent desk's own overallRecommendation
# instead. Graded the exact same honest way (no order was ever placed —
# outcome resolves once OPPORTUNITY_EVAL_WINDOW_MINUTES of simulated
# time has passed, purely from the real difference between the symbol's
# watchlist price then and now).
class OpportunityRejection(CamelModel):
    id: str
    symbol: str
    would_have_recommended: AnalystChoice = Field(alias="wouldHaveRecommended")
    reasons: list[str] = Field(default_factory=list)
    # CEO directive "Professional Quant Firm Phase 41-45," Critical Task
    # #0 — the same real reasons above, tagged with real taxonomy codes
    # (see NoTradeReasonCode's own docstring), one per `reasons` entry,
    # same order.
    reason_codes: list[NoTradeReasonCode] = Field(default_factory=list, alias="reasonCodes")
    # The real Decision Score / Expected Value that failed the gate —
    # kept on the record itself so the rejection is self-explanatory
    # without needing to cross-reference a WarRoomSession that (by
    # design) was never permanently stored for a rejected candidate.
    decision_score_at_rejection: float = Field(alias="decisionScoreAtRejection")
    expected_value_at_rejection_pct: float = Field(alias="expectedValueAtRejectionPct")
    price_at_rejection: float = Field(alias="priceAtRejection")
    rejected_sim_minutes: int = Field(alias="rejectedSimMinutes")
    outcome: GatekeeperOutcome = "pending"
    resolved_price_change_pct: float | None = Field(
        default=None, alias="resolvedPriceChangePct"
    )
    created_at: str = Field(alias="createdAt")
    resolved_at: str | None = Field(default=None, alias="resolvedAt")


class NoTradeReasonCodeTally(CamelModel):
    """One real, counted taxonomy code — CEO directive "Professional
    Quant Firm Phase 41-45," Critical Task #0. `count` is a direct tally
    over the same real, already-persisted rejection records the rest of
    `TradePipelineHealthSnapshot` reads — never a fabricated estimate."""

    code: NoTradeReasonCode
    count: int


class TradePipelineHealthSnapshot(CamelModel):
    """CEO directive "Professional Quant Firm Phase 41-45," Critical
    Task #0's own explicitly-requested trade-flow diagnostic — real
    funnel counts computed fresh from `GameSaveState` (never persisted
    itself, the same CAGS convention this codebase's other on-demand
    reads use). This is DIAGNOSTIC TELEMETRY ONLY: nothing here gates,
    scores, or influences any real trading decision, and nothing in
    `app/trade_pipeline_health.py` was tuned to make these numbers look
    any particular way — see that module's own module docstring.

    HONESTY BOUNDARY: several of the underlying lists this reads are
    real, capped, ROTATING windows, not full-lifetime counters — see
    `data_honesty_note` for the exact caps in effect. This snapshot
    reports "what's currently retained," never a fabricated full-history
    total for a game session older than those caps."""

    completed_research_signals: int = Field(alias="completedResearchSignals")
    pending_proposals: int = Field(alias="pendingProposals")
    resolved_decisions: int = Field(alias="resolvedDecisions")
    trades_executed: int = Field(alias="tradesExecuted")
    no_trade_decisions: int = Field(alias="noTradeDecisions")
    opportunity_rejections: int = Field(alias="opportunityRejections")
    gatekeeper_rejections: int = Field(alias="gatekeeperRejections")
    reason_code_breakdown: list[NoTradeReasonCodeTally] = Field(default_factory=list, alias="reasonCodeBreakdown")
    data_honesty_note: str = Field(alias="dataHonestyNote")
    generated_at: str = Field(alias="generatedAt")


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
    # clicks (auto-resolution didn't exist yet). "delegated" (Design
    # Bible Chapter 70 Part 2) — the CEO explicitly asked the Executive
    # Intelligence Network's own recommendation to decide.
    resolved_by: Literal["ceo", "auto", "delegated"] = Field(default="ceo", alias="resolvedBy")
    created_at: str = Field(alias="createdAt")
    resolved_at: str | None = Field(default=None, alias="resolvedAt")
    # CEO directive "Features 31-35," Feature 32 — CEO Override
    # Governance. A genuinely new mechanism (POST /api/executive/decide
    # gained an optional `overrideReason` field), not a fabricated
    # backfill: `None` for every decision recorded before this field
    # existed, and for every decision where the CEO didn't type one, not
    # coerced to an empty string. Only meaningful when `agreed_with_ai`
    # is `False` — nothing reads it otherwise.
    override_reason: str | None = Field(default=None, alias="overrideReason")
    # CEO directive "Live Trade -> Strategy Provenance" -- the one real,
    # non-fabricated way this codebase can honestly link a live trade to
    # a Strategy Lab strategy: the CEO's own explicit selection at the
    # exact moment of deciding (POST /api/executive/decide gained an
    # optional `strategyId`), never inferred from eligibility or
    # backfilled onto past decisions. `None` for every decision recorded
    # before this field existed, and for every decision where the CEO
    # simply didn't pick one -- the overwhelming majority, honestly. Only
    # meaningful when `ceo_decision` is "buy"/"sell" (a "wait" never
    # executes a trade for any strategy to be attributed to). See
    # app/state.py's submit_ceo_decision() for the real-strategy-exists
    # validation before this is ever set, and app/decision_vault.py's
    # build_vault_entry() / app/trade_attribution.py's
    # compute_trade_attribution() for where it flows downstream.
    strategy_id: str | None = Field(default=None, alias="strategyId")


# CEO directive "Features 26-30," Feature 29 — Prediction -> Outcome
# Tracking (app/prediction_tracking.py). Not the same "Feature 29" as
# app/reasoning_lab.py's older v0.7 versioning-scheme tag (a real,
# unrelated, pre-existing naming collision between two independent
# numbering systems — see that module's own docstring; this directive's
# own 26-30 numbering is what's meant everywhere in this schema and its
# sibling module). `claim_type` is a single real value today
# ("trade_direction") — the one claim this codebase can honestly stake
# BEFORE its outcome is known and resolve later against a real,
# independent trade P&L, mirroring CeoDecisionRecord's own real
# pending -> resolved lifecycle above, generalized to a persisted,
# individually-addressable per-prediction record (which
# app/analytics.py's confidence_accuracy()/research_accuracy() — the
# existing aggregate calibration formulas Feature 27 already reuses —
# structurally cannot provide; see the module docstring for the full
# research finding on why this is additive, not a duplicate).
PredictionClaimType = Literal["trade_direction"]

# CEO directive "Features 26-30," Feature 30 (Agent Debate + Failure
# Review Board) — the real, post-hoc THESIS-FAILURE taxonomy, distinct
# from CaseStudyCategory's behavioral/process taxonomy (see
# app/failure_review.py's module docstring for the full research: a
# trade can be process-perfect and still have a wrong thesis, or vice
# versa, so this is a genuinely separate axis, not a duplicate). Seven
# named values, each backed by a real, already-computed signal this
# codebase reuses rather than recomputes — see app/failure_review.py's
# classify_failure() for exactly which real field backs each one.
# "external_shock" (a Black Swan event) was explicitly researched and
# cut: `CrisisBriefing` (see below) is "Never persisted as its own
# list" and has no `black_swan_event_id` link to any PaperTrade/
# TradeDecision, so there is no honest per-trade evidence to classify
# against — disclosed here rather than added as a permanently-dead
# enum value no real code path could ever produce.
FailureReason = Literal[
    "bad_thesis",
    "poor_execution",
    "risk_management_failure",
    "market_regime_misread",
    "information_gap",
    "process_violation",
    "unknown",
]


class PredictionRecord(CamelModel):
    """One real, individually-addressable prediction, staked before its
    outcome is knowable and resolved later purely from real, independent
    data. `confidence_pct` and `predicted_direction` are the exact real
    values already stamped on the originating `TradeDecision`/
    `CeoDecisionRecord` at decision time — nothing here is a new
    computation. `outcome` stays `"pending"` until a real closed
    `PaperTrade` matches this record's `decision_id` (the same real link
    `app/journal.py` already stamps onto every closed trade for
    `CeoDecisionRecord`'s own grading) — never resolved early, never
    resolved from data that predates `created_at`."""

    id: str
    decision_id: str = Field(alias="decisionId")
    symbol: str
    claim_type: PredictionClaimType = Field(alias="claimType")
    predicted_direction: Literal["buy", "sell"] = Field(alias="predictedDirection")
    confidence_pct: float = Field(alias="confidencePct")
    # The real supporting agents behind this trade decision (see
    # app/executive.py's resolve_proposal) — never a fabricated
    # per-agent confidence split; this is one real, shared claim
    # multiple agents' real votes actually backed.
    attributed_agents: list[AgentId] = Field(alias="attributedAgents")
    outcome: Literal["pending", "correct", "incorrect"] = "pending"
    resolved_trade_id: str | None = Field(default=None, alias="resolvedTradeId")
    resolved_pnl_pct: float | None = Field(default=None, alias="resolvedPnlPct")
    # Feature 30 feed-back integration — filled only when `outcome`
    # resolves to `"incorrect"`, from the real FailureClassification
    # filed for the same resolved trade (matched by `resolved_trade_id`,
    # see app/prediction_tracking.py's grade_predictions()). None for
    # every pending/correct prediction, and also None for an incorrect
    # one whose trade won no FailureClassification (a "wait"-turned-loss
    # edge case, or a trade that predates this feature) — never guessed.
    failure_reason: FailureReason | None = Field(default=None, alias="failureReason")
    sim_day: int = Field(alias="simDay")
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
MarketEnvironmentRegime = Literal[
    "bull", "bear", "sideways", "high_volatility", "low_volatility"
]


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


# v0.7 Design Bible Chapter 65 — Market Regime Detection & Adaptive
# Strategy Engine. "aligned" means app/market_intelligence.py's real
# 13-way regime falls within app/market_intelligence.py's own
# REGIME_CONSISTENCY_MAP entry for the current app/market_environment.py
# 5-way regime — the exact same real mapping the Learning Loop already
# uses to grade a prior day's regime call, reused directly here rather
# than a second, competing definition of "agreement."
RegimeAgreement = Literal["aligned", "diverging"]

# A real, transparent, three-way categorical read off MarketQualityScore
# alone (tier + confidence_pct) — never a numeric override of any
# CEO-configured RiskLimits field. See app/regime_reconciliation.py's
# compute_regime_reconciliation() for the exact, checkable rule.
RegimePosture = Literal["cautious", "normal", "opportunistic"]


class RegimeReconciliation(CamelModel):
    """The one real gap Chapter 65's own research found: two independent
    regime engines (app/market_environment.py's 5-way,
    app/market_intelligence.py's 13-way) exist, neither reads the other,
    and neither is reconciled anywhere in this codebase. This is a
    read-only, computed-fresh-per-request reconciliation — never a
    third, competing regime classifier, and never an automatic write to
    any real RiskLimits field (see that chapter's own Safety Systems
    section)."""

    environment_regime: MarketEnvironmentRegime = Field(alias="environmentRegime")
    environment_label: str = Field(alias="environmentLabel")
    intelligence_regime: MarketIntelligenceRegime = Field(alias="intelligenceRegime")
    intelligence_label: str = Field(alias="intelligenceLabel")
    quality_tier: MarketQualityTier = Field(alias="qualityTier")
    confidence_pct: float = Field(alias="confidencePct")
    agreement: RegimeAgreement
    posture: RegimePosture
    rationale: str


# v0.7 Feature 51 — the Market Intelligence Department's Learning Loop.
# Defined here (rather than alongside the rest of Feature 51's models
# above) because it directly references MarketEnvironmentRegime, and this
# file has no `from __future__ import annotations` — Pydantic evaluates
# annotations eagerly, so a forward reference to a not-yet-defined name
# would fail at import time.
class MarketIntelligenceLearningEntry(CamelModel):
    """The Learning Loop — generated the day AFTER `for_sim_day`, once
    that day's real outcomes are on record, comparing the prior day's
    real MarketIntelligenceReport against what actually happened: the
    real MarketEnvironmentRegime app/market_environment.py's own timeline
    recorded for that day (may be None if the regime never changed that
    day) and the real win rate of PaperTrades actually closed that day.
    Never a fabricated accuracy percentage — `regime_consistent` is a
    real, documented direction-only comparison (see
    app/market_intelligence.py's _REGIME_CONSISTENCY_MAP), and either
    outcome field can honestly be `None` when there is nothing real to
    compare against yet."""

    id: str
    for_sim_day: int = Field(alias="forSimDay")
    predicted_regime: MarketIntelligenceRegime = Field(alias="predictedRegime")
    predicted_quality_tier: MarketQualityTier = Field(alias="predictedQualityTier")
    actual_environment_regime: MarketEnvironmentRegime | None = Field(
        default=None, alias="actualEnvironmentRegime"
    )
    regime_consistent: bool | None = Field(default=None, alias="regimeConsistent")
    trades_closed_that_day: int = Field(alias="tradesClosedThatDay")
    trades_win_rate_pct: float | None = Field(default=None, alias="tradesWinRatePct")
    lesson: str
    created_at: str = Field(alias="createdAt")


# v0.7 Feature 23 — Company Health & Stability System. Ten real,
# documented sub-scores (see app/company_health.py for the exact formula
# behind each) — deliberately not the same list as v0.5's CompanyScore
# (research/decision/risk/paper-trading/teamwork/knowledge/simulation):
# this one asks "is the company healthy to keep operating," CompanyScore
# asks "is it performing well," and several factors overlap on purpose
# (e.g. Employee Morale reuses the same real agent-mood average
# CompanyScore's Team Coordination does) rather than inventing two
# divergent readings of the same underlying number.
CompanyHealthTier = Literal[
    "excellent", "good", "stable", "needs_attention", "critical"
]


# CEO directive "Command Center + Professional Quant Trading Firm
# Upgrade" — the Executive View's Problem/Cause/Severity/Action
# breakdown for a real weak Company Health sub-score. Extends (never
# replaces) the existing plain-string `recommendations` list below with
# real, evidence-grounded detail per weak area — see
# app/company_health.py's `_diagnose()` for exactly which real inputs
# each metric's `cause`/`action` text is grounded in (the same raw data
# `compute_company_health()` already reads to compute the score itself,
# never a second, independently-invented reading). `severity` reuses
# `CompanyHealthTier` rather than inventing a second banding taxonomy —
# a weak area's score is, by construction, already below "good," so only
# "stable"/"needs_attention"/"critical" ever actually appear here.
#
# Deliberately has NO `status` field, though the brief's own structure
# asks for one: no real remediation-tracking mechanism (has this been
# acknowledged, assigned, resolved?) exists anywhere in this codebase to
# report honestly — see app/company_health.py's own module docstring.
# Fabricating an always-"open" placeholder would be exactly the kind of
# invented precision this codebase's conventions bar.
class CompanyHealthWeakArea(CamelModel):
    metric: str
    label: str
    group: Literal["operational", "executive"]
    score: float
    severity: CompanyHealthTier
    problem: str
    cause: str
    action: str


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
    # CEO Company/Executive Health directive: renamed from
    # "officeExpansion" — the formula was always real watchlist growth
    # (extra symbols added beyond the 8 seed symbols), never a facility/
    # office-capability mechanic (this codebase has none — see
    # app/save_modules.py's own "No Buildings module" note). Same real
    # formula, honest name.
    market_coverage: float = Field(alias="marketCoverage")
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
    # CEO directive "Command Center + Professional Quant Trading Firm
    # Upgrade" — the same weak areas `recommendations` above already
    # identifies (unchanged, kept for backward compatibility), each now
    # also carrying a real Problem/Cause/Severity/Action breakdown — see
    # `CompanyHealthWeakArea`'s own docstring for why there is no
    # `status` field. Defaults to an empty list so a save from before
    # this field existed still validates.
    weak_areas: list[CompanyHealthWeakArea] = Field(default_factory=list, alias="weakAreas")
    updated_at: str = Field(alias="updatedAt")

    # v0.7 Feature 50 (Part 2/3) — the Company Health redesign. Ten new
    # Executive-tier dimensions, additive alongside the eleven Operational
    # ones above (never replacing them — see app/company_health.py's
    # module docstring for why: they're real and already working, and
    # this codebase's own "no duplicate systems" convention bars
    # replacing a real working formula with one that can't actually
    # improve on it). All ten default to 50.0 (neutral) so a save from
    # before this field existed still validates during load.
    decision_quality: float = Field(default=50.0, alias="decisionQuality")
    executive_alignment: float = Field(default=50.0, alias="executiveAlignment")
    risk_governance: float = Field(default=50.0, alias="riskGovernance")
    simulation_coverage: float = Field(default=50.0, alias="simulationCoverage")
    department_consensus: float = Field(default=50.0, alias="departmentConsensus")
    self_evaluation_health: float = Field(default=50.0, alias="selfEvaluationHealth")
    institutional_memory: float = Field(default=50.0, alias="institutionalMemory")
    innovation_velocity: float = Field(default=50.0, alias="innovationVelocity")
    talent_development: float = Field(default=50.0, alias="talentDevelopment")
    founder_oversight: float = Field(default=50.0, alias="founderOversight")
    # CEO directive "Features 31-35," Feature 35 — the Continuous
    # Compliance Improvement Loop's real Company Health connection: a
    # genuinely new eleventh Executive-tier dimension (never a rewrite of
    # `compute_compliance_score()` in app/audit_log.py, which stays
    # untouched — see app/company_health.py's `_compliance_health()` for
    # the real blend of incident resolution, remediation effectiveness,
    # and control effectiveness this reads). Defaults to 50.0 (neutral)
    # so a save from before this field existed still validates.
    compliance_health: float = Field(default=50.0, alias="complianceHealth")
    executive_overall: float = Field(default=50.0, alias="executiveOverall")
    executive_tier: CompanyHealthTier = Field(default="stable", alias="executiveTier")
    # The true redesigned headline number — an equal blend of the
    # original Operational overall and the new Executive overall, so
    # neither tier silently outweighs the other.
    combined_overall: float = Field(default=50.0, alias="combinedOverall")
    combined_tier: CompanyHealthTier = Field(default="stable", alias="combinedTier")


# CEO Company Health + Live Market Realism directive, Section 6 — the
# explicit before/after delta breakdown ("+2.4 Decision Quality, -0.8
# Efficiency...") the CEO asked to see, rather than Company Health only
# ever presenting itself as a single opaque snapshot. `group` distinguishes
# which of CompanyHealth's two already-real, already-equal-weighted tiers
# (see app/company_health.py's module docstring) a component belongs to —
# no new weighting scheme, just a label on the existing one.
CompanyHealthDeltaGroup = Literal["operational", "executive"]


class CompanyHealthComponentDelta(CamelModel):
    key: str
    label: str
    group: CompanyHealthDeltaGroup
    previous: float
    current: float
    delta: float


# One real diff between two already-computed CompanyHealth readings (see
# app/company_health.py's diff_company_health()) — never a fabricated
# "reason" or "evidence" string, since the only honest source for either
# would be re-deriving which of the many real inputs changed, which this
# module doesn't attempt. `components` holds only the entries that
# actually moved, sorted by magnitude, so a tick where nothing changed
# reports an empty list rather than eleven/ten zeroes.
class CompanyHealthDelta(CamelModel):
    previous_updated_at: str = Field(alias="previousUpdatedAt")
    current_updated_at: str = Field(alias="currentUpdatedAt")
    overall_delta: float = Field(alias="overallDelta")
    executive_overall_delta: float = Field(alias="executiveOverallDelta")
    combined_overall_delta: float = Field(alias="combinedOverallDelta")
    tier_changed: bool = Field(alias="tierChanged")
    executive_tier_changed: bool = Field(alias="executiveTierChanged")
    combined_tier_changed: bool = Field(alias="combinedTierChanged")
    components: list[CompanyHealthComponentDelta] = Field(default_factory=list)


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
    department_activity: list[DepartmentActivity] = Field(
        default_factory=list, alias="departmentActivity"
    )
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
    knowledge_connections: list[str] = Field(
        default_factory=list, alias="knowledgeConnections"
    )
    summary: str
    created_at: str = Field(alias="createdAt")


# Design Bible Chapter 70 Part 1 — Executive Board & CEO Intelligence
# System (app/board.py). BoardSeat/BoardRoster are computed fresh per
# request, never persisted — the same "always current" reasoning as
# CompanyHealth, since agent occupations rarely change and there is
# nothing here worth snapshotting. Only 11 of the brief's own 12 named
# seats are represented: the 12th is never named anywhere in the source
# brief itself, and is deliberately not invented — see the chapter's own
# Implementation Notes.
class BoardSeat(CamelModel):
    title: str
    agent_id: AgentId | None = Field(default=None, alias="agentId")
    agent_name: str | None = Field(default=None, alias="agentName")


class BoardRoster(CamelModel):
    seats: list[BoardSeat]
    generated_at: str = Field(alias="generatedAt")


# Design Bible Chapter 70 Part 1 — the Board Report, a real composition
# of already-real signals (never a duplicate computation) on three
# cadences: "daily" (the same is_evening-only gate Feature 51's Market
# Brief already established), "quarterly" (a new day % 90 == 0 gate,
# the same shape Weekly/Monthly already use), and "emergency" (fired
# once on a real edge-crossing — Emergency Stop activation or Black
# Swan tier crossing into red/critical — never every tick while the
# condition holds). Weekly/Monthly cadences are deliberately not built
# here — CoachReport and ExecutiveReview already cover them.
BoardReportCadence = Literal["daily", "quarterly", "emergency"]
BoardReportTrigger = Literal["emergency_stop", "black_swan_tier"]


class BoardReport(CamelModel):
    id: str
    cadence: BoardReportCadence
    trigger: BoardReportTrigger | None = Field(default=None, alias="trigger")
    department_activity: list[DepartmentActivity] = Field(
        default_factory=list, alias="departmentActivity"
    )
    problems: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    risk_assessment: str = Field(alias="riskAssessment")
    confidence_level: float = Field(alias="confidenceLevel")
    required_ceo_decisions: int = Field(alias="requiredCeoDecisions")
    summary: str
    sim_day: int = Field(alias="simDay")
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
KnowledgeLevel = Literal[
    "novice", "beginner", "intermediate", "advanced", "expert", "master", "mentor"
]


class AgentKnowledgeState(CamelModel):
    agent_id: AgentId = Field(alias="agentId")
    branch: str
    points: float
    tier: int
    level: KnowledgeLevel


# CEO Company Health + Live Market Realism directive, Section 3 — the
# five real, already-existing places app/academy.py's award_points()
# is called from: research completion, an Academy project finishing,
# meeting attendance, a mentorship bonus, and a supporting agent
# reflecting on a filed case study (Design Bible Chapter 74 Part 1's
# Academy Integration hook, app/nexus.py's ACADEMY_CASE_STUDY_NUDGE call
# sites) — never a sixth, invented source.
LearningEventSource = Literal["research_completion", "academy_project", "meeting_attendance", "mentorship", "case_study_reflection"]


# A formal, structured record of one real Knowledge-tier crossing,
# replacing the free-text-only app/scribe.py Memory entry as the
# queryable source of truth (that Memory entry is kept, unchanged, as
# the human-readable company-history version of the same real event —
# see app/scribe.py's record_knowledge_tier_up()). Every field is read
# directly off the real AgentKnowledgeState transition award_points()
# already computes — never a second, independently-invented reading,
# and never a fabricated "why" narrative: pointsAwarded/totalPoints
# already are the real evidence.
class LearningEvent(CamelModel):
    id: str
    agent_id: AgentId = Field(alias="agentId")
    skill_domain: str = Field(alias="skillDomain")
    previous_competency: int = Field(alias="previousCompetency")
    previous_level: KnowledgeLevel = Field(alias="previousLevel")
    new_competency: int = Field(alias="newCompetency")
    new_level: KnowledgeLevel = Field(alias="newLevel")
    source: LearningEventSource
    points_awarded: float = Field(alias="pointsAwarded")
    total_points: float = Field(alias="totalPoints")
    created_at: str = Field(alias="createdAt")


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
# v0.7 Design Bible Chapter 61 — three new real node types, each backed
# by an already-real, already-persisted object (DecisionVaultEntry,
# CaseStudy, Strategy) — see app/knowledge_graph.py's module docstring
# for exactly which real field backs each new node/edge.
KnowledgeNodeType = Literal[
    "agent",
    "branch",
    "research",
    "academy_project",
    "executive_review",
    "coach_report",
    "hall_of_fame",
    "trade",
    "case_study",
    "strategy",
    # Design Bible Chapter 72 — one real node per completed Defensive
    # Mode episode (app/black_swan.py's BlackSwanEventRecord).
    "black_swan_event",
    # Design Bible Chapter 74 Part 1 — one real node per daily
    # EconomicIntelligenceReport (app/economic_intelligence.py), the one
    # honestly-buildable Knowledge Graph gap Chapter 61's own
    # Implementation Notes named. "Indicator" nodes are cut — no
    # per-trade indicator linkage exists anywhere to build them from
    # real data rather than a guess.
    "economic_event",
    # CEO directive "Quant Research Factory / Strategy Discovery Engine,"
    # Phase 15 — one real node per persisted QuantResearchExperiment
    # (app/quant_research_lab.py). Closes the directive's own ask that
    # research-factory experiments be discoverable in the Knowledge
    # Graph like every other institutional record.
    "research_experiment",
]
KnowledgeEdgeRelation = Literal[
    "researched",
    "completed",
    "has_branch",
    "builds_on",
    "featured_in",
    "ranked_top_agent",
    "achieved",
    "documented_by",
    "same_symbol",
    "same_category",
    "created",
    # Design Bible Chapter 74 Part 1 — links an economic_event node to
    # any trade/case_study node recorded the same real simDay. A real,
    # checkable temporal proximity — never a claim that the event
    # caused the trade, the same non-causal honesty rule "same_symbol"/
    # "same_category" already hold themselves to.
    "same_day",
    # CEO directive "Quant Research Factory / Strategy Discovery Engine,"
    # Phase 15 — links a research_experiment node to a strategy node
    # sharing the same real compiled definition id
    # (Strategy.compiledDefinitionId == record.definitionId). A real,
    # direct ID match, never a fuzzy or causal claim.
    "tested",
]


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
    information_overlooked: list[str] = Field(
        default_factory=list, alias="informationOverlooked"
    )
    assumptions_incorrect: list[str] = Field(
        default_factory=list, alias="assumptionsIncorrect"
    )
    what_to_repeat: list[str] = Field(default_factory=list, alias="whatToRepeat")
    what_to_never_repeat: list[str] = Field(
        default_factory=list, alias="whatToNeverRepeat"
    )
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


# Trading Psychology & Discipline, Piece C — the Process Adherence Score
# (Design Bible Chapter 66 addendum). Explicitly NOT a Plan Adherence
# Engine: this codebase has no stop-loss/take-profit/entry-condition/
# exit-condition/confluence tracking anywhere (see app/gatekeeper.py's
# own module docstring), so those checks are honestly reported as
# "not_trackable_yet" — never scored as pass, never as fail, never
# silently omitted. Every "passed"/"failed" check below reuses data this
# codebase already computed for a different real reason (the Gatekeeper's
# own checks, the Discipline Chamber's own tier, the Trading Mode
# tagging Chapter 75 already enforces) — never a fabricated signal.
ProcessAdherenceCheckStatus = Literal["passed", "failed", "not_trackable_yet"]


class ProcessAdherenceCheck(CamelModel):
    id: str
    label: str
    status: ProcessAdherenceCheckStatus
    detail: str


class ProcessAdherenceRead(CamelModel):
    """`score_pct` is None whenever `verified_count` is 0 — there is
    nothing real to score from yet, and this must never be displayed as
    0% (a real failing grade) or omitted silently. `verified_count` =
    `passed_count` + `failed_count` (checks this architecture could
    actually evaluate); `not_trackable_count` is disclosed separately,
    never folded into either side of the score."""

    decision_id: str = Field(alias="decisionId")
    symbol: str
    score_pct: float | None = Field(default=None, alias="scorePct")
    verified_count: int = Field(alias="verifiedCount")
    passed_count: int = Field(alias="passedCount")
    failed_count: int = Field(alias="failedCount")
    not_trackable_count: int = Field(alias="notTrackableCount")
    checks: list[ProcessAdherenceCheck] = Field(default_factory=list)
    computed_at: str = Field(alias="computedAt")


# Trading Psychology & Discipline, Piece G — the one real company-wide
# aggregate over ProcessAdherenceRead this codebase had never needed
# before (every existing consumer reads a single decision's own real
# score by id — see DecisionDetail.tsx). `average_score_pct` is the mean
# of `scorePct` across only the reviewed decisions that had at least one
# verified check — never padded with a fabricated 0% or 100% for a
# decision with nothing to score, the same "None means nothing real to
# average" rule ProcessAdherenceRead.score_pct already follows.
class ProcessAdherenceSummaryRead(CamelModel):
    decisions_reviewed: int = Field(alias="decisionsReviewed")
    decisions_with_verified_checks: int = Field(alias="decisionsWithVerifiedChecks")
    average_score_pct: float | None = Field(default=None, alias="averageScorePct")
    computed_at: str = Field(alias="computedAt")


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
    department_opinions: list[str] = Field(
        default_factory=list, alias="departmentOpinions"
    )
    missed_information: str = Field(alias="missedInformation")
    lessons_learned: str = Field(alias="lessonsLearned")
    recommended_improvements: str = Field(alias="recommendedImprovements")
    # Real, already-configured company thresholds (RiskLimits, the Trade
    # Gatekeeper's own checks) — never invented aspirational principles.
    related_principles: list[str] = Field(
        default_factory=list, alias="relatedPrinciples"
    )
    trade_pnl_pct: float = Field(alias="tradePnlPct")
    # The real in-game day this case study was filed — see
    # DisciplineReview.sim_day above for why.
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


# CEO directive "Features 26-30," Feature 30 (Agent Debate + Failure
# Review Board) — the final stage of the 26->27->28->29->30 learning
# loop. Exactly one FailureClassification per real closed, losing trade
# (see app/failure_review.py's classify_failure(), called from the same
# nexus.py trade-close branch that already files this trade's
# CaseStudy(s) — never a second, independently-triggered pass). Answers
# a genuinely different question than CaseStudy: CaseStudy asks "what
# behavioral/process mistake occurred" (app/mistakes.py); this asks "why
# did the THESIS actually fail" — a well-disciplined process can still
# rest on a wrong thesis, and vice versa. `reason` is picked by a fixed,
# documented precedence over real, already-computed evidence (Discipline
# Chamber factors, Process Adherence's trading-mode check, this trade's
# own CaseStudy categories, the Market Intelligence Learning Loop) —
# never a fabricated root cause, and `"unknown"` is the honest result
# when nothing real fires rather than a guess.
class FailureClassification(CamelModel):
    id: str
    trade_id: str = Field(alias="tradeId")
    decision_id: str = Field(alias="decisionId")
    symbol: str
    reason: FailureReason
    evidence: str
    # The real supporting agents behind the failed decision (see
    # PredictionRecord.attributed_agents above for the same convention)
    # — never a fabricated per-agent apportionment of blame.
    attributed_agents: list[AgentId] = Field(alias="attributedAgents")
    trade_pnl_pct: float = Field(alias="tradePnlPct")
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


# Trading Psychology & Discipline, Piece D — Loss/Win Classification,
# formalized on top of the Discipline Chamber (Design Bible Chapter 74
# addendum). The one company-wide, real aggregate over every trade this
# Discipline Chamber has ever reviewed, cross-tabulating the same
# win/loss outcome DisciplineReview already computes against its own
# tier — so a good-process trade undone by real market variance and a
# weak-process trade that happened to win are named explicitly, never
# folded into a bare win rate. Computed fresh on demand from
# DisciplineReview/CaseStudy — never a sixth persisted copy of numbers
# those two already carry.
class DisciplineTierOutcomeCount(CamelModel):
    tier: DisciplineTier
    win_count: int = Field(alias="winCount")
    loss_count: int = Field(alias="lossCount")


class LossWinClassificationRead(CamelModel):
    """`aligned_count` = a good-tier (exemplary/sound) win, or a poor-tier
    (weak/reckless) loss — process and outcome agree. `unlucky_loss_count`
    = a good-tier trade that still lost (real market variance, not a
    process failure — see discipline.py's own `_summary()`).
    `lucky_win_count` = a poor-tier trade that still won (a warning, not a
    validation — same source). `misaligned_count` is their sum.
    `adequate`-tier trades count toward neither bucket — a genuine middle
    tier, not a strong signal either way. Every count always sums back to
    `total_reviewed` across (aligned + misaligned + adequate-tier)."""

    total_reviewed: int = Field(alias="totalReviewed")
    win_count: int = Field(alias="winCount")
    loss_count: int = Field(alias="lossCount")
    win_rate_pct: float | None = Field(default=None, alias="winRatePct")
    by_tier: list[DisciplineTierOutcomeCount] = Field(
        default_factory=list, alias="byTier"
    )
    aligned_count: int = Field(alias="alignedCount")
    misaligned_count: int = Field(alias="misalignedCount")
    unlucky_loss_count: int = Field(alias="unluckyLossCount")
    lucky_win_count: int = Field(alias="luckyWinCount")
    most_common_mistake_category: CaseStudyCategory | None = Field(
        default=None, alias="mostCommonMistakeCategory"
    )
    most_common_mistake_count: int = Field(default=0, alias="mostCommonMistakeCount")
    most_common_success_category: CaseStudyCategory | None = Field(
        default=None, alias="mostCommonSuccessCategory"
    )
    most_common_success_count: int = Field(default=0, alias="mostCommonSuccessCount")
    computed_at: str = Field(alias="computedAt")


# v0.7 — the Decision Memory System / Decision Vault. One permanent,
# immutable record per closed trade, JOINING every real artifact this
# codebase already generates for that trade (TradeDecision, PaperTrade,
# DisciplineReview, CaseStudy, ExecutiveMeetingLogEntry, CeoDecisionRecord)
# plus two genuinely new context snapshots computed fresh at the moment
# the trade closes: market regime and liquidity context. Both are
# honestly "as of trade close," not "as of the original decision," since
# neither is stamped onto anything at proposal time anywhere in this
# codebase — see app/decision_vault.py's module docstring for the full
# honesty boundary, including the fields the brief asked for that are
# deliberately NOT here (rMultiple — no stop-loss/initial-risk concept
# exists anywhere in this codebase's real risk engine; strategyId — no
# ordinary Trading Floor trade links to a Strategy object).
class SimilarTradeMatch(CamelModel):
    vault_entry_id: str = Field(alias="vaultEntryId")
    symbol: str
    sim_day: int = Field(alias="simDay")
    pnl_pct: float = Field(alias="pnlPct")
    decision_grade: DecisionGrade = Field(alias="decisionGrade")


class SimilarTradesSummary(CamelModel):
    """The Decision Memory System's Similarity Engine. Real, rule-based
    bucket matching over the Decision Vault (never a fabricated
    similarity score) — see find_similar_vault_entries()'s own docstring
    for the exact tiered matching rule and why."""

    match_count: int = Field(alias="matchCount")
    # Which real dimensions the match tier used — e.g. ["symbol",
    # "marketRegime", "confidenceTier"] — so the CEO can see exactly why
    # these trades were considered "similar," never a black box.
    matched_on: list[str] = Field(alias="matchedOn")
    win_rate_pct: float = Field(alias="winRatePct")
    avg_pnl_pct: float = Field(alias="avgPnlPct")
    worst_pnl_pct: float = Field(alias="worstPnlPct")
    best_regime: MarketIntelligenceRegime | None = Field(
        default=None, alias="bestRegime"
    )
    worst_regime: MarketIntelligenceRegime | None = Field(
        default=None, alias="worstRegime"
    )
    # Real: the most common CaseStudyCategory among the matched trades'
    # own linked case studies, only when it's a real mistake category
    # (never a success category) shared by at least MISTAKE_WARNING_SHARE
    # of matches — the Decision Memory System's "Mistake Prevention"
    # warning signal. None when no such pattern is real/significant.
    most_common_mistake_category: CaseStudyCategory | None = Field(
        default=None, alias="mostCommonMistakeCategory"
    )
    warning: str | None = None
    examples: list[SimilarTradeMatch] = Field(default_factory=list)


class DecisionVaultEntry(CamelModel):
    id: str
    trade_id: str = Field(alias="tradeId")
    decision_id: str = Field(alias="decisionId")
    symbol: str
    sim_day: int = Field(alias="simDay")
    session: TradingSession
    # CEO directive "Live Trade -> Strategy Provenance" -- real, but
    # only ever non-None when the CEO explicitly selected a real
    # Strategy Lab strategy at the moment of deciding this trade (see
    # CeoDecisionRecord.strategy_id, the one real source for this field
    # -- app/decision_vault.py's build_vault_entry() just carries it
    # through). None for every trade closed before this field existed,
    # and for every trade where the CEO didn't pick a strategy -- the
    # overwhelming majority, honestly disclosed, never backfilled.
    strategy_id: str | None = Field(default=None, alias="strategyId")
    market_regime: MarketIntelligenceRegime = Field(alias="marketRegime")
    market_regime_label: str = Field(alias="marketRegimeLabel")
    liquidity_context: LiquidityRead = Field(alias="liquidityContext")
    # A real sub-aggregate of DecisionConfidence's own evidence-oriented
    # factors (Technical Alignment, Research Confidence, News/Macro/
    # Sentiment), renormalized over just those three's own real weights
    # — see decision_vault.py's compute_evidence_score(). Deliberately
    # distinct from confidenceScore below (the full composite, which
    # also includes Multi-Agent Agreement/Risk Conditions/Portfolio
    # Exposure) so the two numbers mean genuinely different things.
    evidence_score: float = Field(alias="evidenceScore")
    confidence_score: float = Field(alias="confidenceScore")
    confidence_tier: ConfidenceTier = Field(alias="confidenceTier")
    # Real: the position_sizing_discipline DisciplineFactor's own score,
    # converted to a letter grade via the same GRADE_THRESHOLDS
    # app/executive.py's Decision Grade already uses.
    capital_allocation_grade: DecisionGrade = Field(alias="capitalAllocationGrade")
    decision_grade: DecisionGrade = Field(alias="decisionGrade")
    decision_grade_score: float = Field(alias="decisionGradeScore")
    discipline_tier: DisciplineTier = Field(alias="disciplineTier")
    discipline_score: float = Field(alias="disciplineScore")
    # Real: the patience DisciplineFactor's own score, same conversion.
    patience_grade: DecisionGrade = Field(alias="patienceGrade")
    position_size: float = Field(alias="positionSize")
    entry_price: float = Field(alias="entryPrice")
    exit_price: float = Field(alias="exitPrice")
    pnl: float
    pnl_pct: float = Field(alias="pnlPct")
    hold_duration_minutes: int = Field(alias="holdDurationMinutes")
    # Always None — no stop-loss/initial-risk basis exists anywhere in
    # this codebase's real risk engine (recommended_quantity() sizes
    # directly off equity%, never a stop distance) to honestly compute
    # an R-multiple from. Never backfilled with a fabricated value.
    r_multiple: float | None = Field(default=None, alias="rMultiple")
    # The real CaseStudy (mistake OR success) filed for this exact trade,
    # if any — mistakes.py/successes.py only ever file one per trade.
    case_study_id: str | None = Field(default=None, alias="caseStudyId")
    case_study_category: CaseStudyCategory | None = Field(
        default=None, alias="caseStudyCategory"
    )
    # ExecutiveMeetingLogEntry.recommendationReason for this trade's own
    # proposal, if a matching entry exists — real, never authored fresh.
    executive_notes: str | None = Field(default=None, alias="executiveNotes")
    lessons_learned: str = Field(alias="lessonsLearned")
    # Real: set only when a Company DNA Legacy nudge fired specifically
    # because of THIS trade's own success study (disciplined_process /
    # patient_execution) — see app/company_dna.py's nudge_legacy(). None
    # for the overwhelming majority of trades, which don't fire a nudge.
    company_dna_change: str | None = Field(default=None, alias="companyDnaChange")
    # Real: True only when a matching CeoDecisionRecord exists and
    # agreedWithAi is False (the CEO overrode the AI's recommendation).
    ceo_override: bool = Field(alias="ceoOverride")
    created_at: str = Field(alias="createdAt")


# CEO directive "Session Trading Education & Agent Training" — real
# SESSION × REGIME evidence (app/session_evidence.py), computed fresh
# over the already-real DecisionVaultEntry list above. Deliberately a
# two-axis read (session × regime → outcome), not the directive's own
# five-axis "session × regime × strategy × setup × outcome" framing —
# DecisionVaultEntry.strategyId is None on every real entry today and no
# "setup" taxonomy exists anywhere in this codebase, so those two axes
# are not honestly buildable from real data yet (see
# app/session_evidence.py's own module docstring for the full
# disclosure, never silently dropped).
SessionRegimeEvidenceState = Literal["favorable", "unfavorable", "mixed", "not_enough_evidence"]


class SessionRegimeEvidence(CamelModel):
    """One real (session, regime) pairing's outcome record, built purely
    from real closed `DecisionVaultEntry.pnlPct` values. `evidenceState`
    is `not_enough_evidence` below `MIN_SESSION_REGIME_SAMPLE` real
    observations — never a forced favorable/unfavorable read on a thin
    sample."""

    session: TradingSession
    regime: MarketIntelligenceRegime
    sample_size: int = Field(alias="sampleSize")
    win_count: int = Field(alias="winCount")
    loss_count: int = Field(alias="lossCount")
    win_rate_pct: float | None = Field(default=None, alias="winRatePct")
    avg_pnl_pct: float | None = Field(default=None, alias="avgPnlPct")
    evidence_state: SessionRegimeEvidenceState = Field(alias="evidenceState")


class SessionRegimeEvidenceSummary(CamelModel):
    """The real, disclosed aggregate — `buckets` only ever contains
    pairings this company has actually closed a real trade under; a
    pairing never seen simply never appears, rather than a fabricated
    zero-evidence row."""

    buckets: list[SessionRegimeEvidence]
    min_sample_size: int = Field(alias="minSampleSize")
    updated_at: str = Field(alias="updatedAt")


class TradeReportCard(CamelModel):
    """The Decision Memory System's Trade Report Card — a pure
    relabeling of a DecisionVaultEntry's own real fields into the
    brief's named grades, never a second measurement. See
    app/decision_vault.py's compute_trade_report_card(). Deliberately
    does NOT include a Psychology Grade the brief also named: no
    emotion/psychology signal exists anywhere (confirmed repeatedly
    elsewhere in this codebase, e.g. the Probability First Trading
    Philosophy's own "TradeTown honestly can't read literal emotion").

    CEO directive "Command Center + Professional Quant Trading Firm
    Upgrade" — Post-Trade Intelligence. Research first found this exact
    trade's post-trade evidence was real but split three ways
    (DecisionVaultEntry / TradeExitEfficiency / TradeAttributionRecord),
    with no single joined read — this closes that gap by extending the
    EXISTING Trade Report Card (never a new, competing "joined view"
    system) with the other two real sources, keyed by the same real
    `tradeId` every one of the three already carries. This also
    supplies a real Execution Grade proxy the original card explicitly
    said didn't exist yet: `entrySlippageBps`/`exitSlippageBps`/
    `transactionCostUsd` ARE a real order-execution-quality signal
    (app/trade_attribution.py), just not one this card had joined in
    before. `None` fields below mean the join genuinely found no
    matching real record — see `dataHonestyNote` for what remains a
    real, disclosed gap rather than a fabricated field (WHY this trade
    was exited, its SETUP taxonomy, and an EXPECTED-vs-ACTUAL comparison
    — none of these has a real mechanism anywhere in this codebase yet).

    CEO directive "Live Trade -> Strategy Provenance" adds
    `strategyId`/`strategyProvenanceState`, joined the same way from
    `TradeAttributionRecord` — real only when the CEO explicitly
    selected a strategy at decision time (see `CeoDecisionRecord.
    strategyId`), "unknown" otherwise (the honest majority), never
    inferred from eligibility or backfilled onto trades that predate
    this feature."""

    vault_entry_id: str = Field(alias="vaultEntryId")
    symbol: str
    evidence_score: float = Field(alias="evidenceScore")
    confidence_score: float = Field(alias="confidenceScore")
    capital_allocation_grade: DecisionGrade = Field(alias="capitalAllocationGrade")
    decision_grade: DecisionGrade = Field(alias="decisionGrade")
    discipline_grade: DisciplineTier = Field(alias="disciplineGrade")
    patience_grade: DecisionGrade = Field(alias="patienceGrade")
    # Deliberately the same value as decisionGrade, restated under the
    # brief's own name — see this class's own docstring for why a third,
    # separately-computed composite would be redundant-metric
    # proliferation this codebase's discipline avoids throughout.
    overall_trade_quality: DecisionGrade = Field(alias="overallTradeQuality")
    would_take_again: bool = Field(alias="wouldTakeAgain")
    recommendation: str
    # Real MAE/MFE/capture — joined from TradeExitEfficiency by tradeId.
    mae_pct: float | None = Field(default=None, alias="maePct")
    mfe_pct: float | None = Field(default=None, alias="mfePct")
    capture_pct: float | None = Field(default=None, alias="capturePct")
    exit_efficiency_state: ExitEfficiencyState | None = Field(default=None, alias="exitEfficiencyState")
    # Real execution-quality signal — joined from TradeAttributionRecord
    # by tradeId.
    entry_slippage_bps: float | None = Field(default=None, alias="entrySlippageBps")
    exit_slippage_bps: float | None = Field(default=None, alias="exitSlippageBps")
    transaction_cost_usd: float | None = Field(default=None, alias="transactionCostUsd")
    supporting_agents: list[AgentId] = Field(default_factory=list, alias="supportingAgents")
    opposing_agents: list[AgentId] = Field(default_factory=list, alias="opposingAgents")
    gatekeeper_approved: bool | None = Field(default=None, alias="gatekeeperApproved")
    # CEO directive "Live Trade -> Strategy Provenance" — joined from
    # TradeAttributionRecord by tradeId. "unavailable" (never a
    # fabricated "known") whenever the real matching PaperTrade this
    # vault entry cites is no longer in trade_history.
    strategy_id: str | None = Field(default=None, alias="strategyId")
    strategy_provenance_state: TradeStrategyProvenanceState = Field(alias="strategyProvenanceState")
    data_honesty_note: str = Field(alias="dataHonestyNote")


# v0.7 Design Bible Chapter 61's Knowledge Quality Score. Computed fresh
# per request (never persisted, never a second driftable copy — the same
# discipline app/knowledge_graph.py already follows), from three real,
# checkable signals over the Decision Vault's own Similarity Engine.
# Deliberately does NOT include the brief's Accuracy/Usefulness/
# Validation dimensions — no signal anywhere in this codebase measures
# those (see compute_knowledge_quality_score()'s own docstring for the
# full honesty boundary, including why "Pattern Frequency" below is a
# real proxy rather than a literal usage counter).
class KnowledgeQualityScore(CamelModel):
    vault_entry_id: str = Field(alias="vaultEntryId")
    matched_on: list[str] = Field(alias="matchedOn")
    historical_success_pct: float | None = Field(default=None, alias="historicalSuccessPct")
    pattern_frequency: int = Field(alias="patternFrequency")
    relevance_pct: float = Field(alias="relevancePct")
    overall_score: float = Field(alias="overallScore")


# CEO directive "Features 26-30: Agent Intelligence, Learning &
# Institutional Memory System" — Feature 26 (Institutional Memory 2.0),
# extended by Feature 29 (Prediction -> Outcome Tracking, see
# app/prediction_tracking.py) which added "prediction" below. See
# app/institutional_memory.py's module docstring for the full design
# rationale. Deliberately scoped to only the eight source kinds this
# codebase can honestly back today with a real originating record;
# "agent_debate"/"performance_review" (Features 30/27) are intentionally
# NOT added here — each is deferred until its own feature is actually
# built and can honestly promote into this sink, matching the CEO's own
# 26→27→28→29→30 pipeline order. This is a disclosed staging decision,
# not a silent gap.
InstitutionalMemorySource = Literal[
    "behavioral_mistake",
    "behavioral_success",
    "strategy_failure",
    "strategy_success",
    "model_validation",
    "risk_event",
    "market_regime_shift",
    "prediction",
    # Feature 30 — promoted from a FailureClassification whose reason is
    # not "unknown" (an unclassifiable trade has no real lesson to file
    # — see app/institutional_memory.py's should_promote_failure_
    # classification()).
    "failure_classification",
]

# "active" — the current, standing read. "superseded" — a newer entry
# now supersedes this one (an intentional update, not a contradiction);
# see supersede_memory(). "contradicted" — a newer observation disagreed
# with this one, and both are kept (see find_contradicting_or_related())
# rather than the newer one silently overwriting the older. "stale" —
# reserved for a future recency-based downgrade; nothing in this piece
# sets it automatically today (retrieve_relevant_memory() already
# demotes low-relevance active entries at read time instead), but the
# state exists so a later feature can mark an entry stale without a
# schema change.
InstitutionalMemoryStatus = Literal["active", "superseded", "contradicted", "stale"]


class InstitutionalMemoryEntry(CamelModel):
    """One durable, reusable lesson — never a raw copy of the event log
    (see app/scribe.py's MemoryRecord for that; this is a promotion
    layer on top of it, not a replacement). Deliberately separates three
    things a naive "memory" often conflates:

      observation   — what actually, verifiably happened (a real fact
                       drawn straight from the source record's own
                       fields, e.g. a CaseStudy's own missed_information,
                       a ModelValidationReport's own evidence_summary).
      interpretation — a plausible read of *why*, hedged, never a proven
                       causal claim (matches app/knowledge_graph.py's own
                       existing non-causal-edge discipline). None when
                       the source record has nothing to interpret from.
      lesson         — the actionable takeaway a future decision should
                       weigh. None when the source doesn't warrant one
                       (e.g. a routine "insufficient data" risk event).

    `confidence` reuses decision_vault.py's PATTERN_FREQUENCY_CAP-shaped
    formula (how many other memories from the same source/symbol/regime
    corroborate this one) — never an invented number. `relevance_pct`
    reuses compute_knowledge_quality_score()'s exact recency-decay
    formula verbatim. `provenance` is a plain-text citation of exactly
    which source record (`event_ref`) this entry was promoted from, so
    every memory is traceable back to real evidence, never asserted
    free-floating.

    Contradiction/update handling never overwrites history: an entry
    that's superseded or contradicted keeps its own row, with
    `supersedes_id`/`superseded_by_id` linking the chain — see
    supersede_memory()."""

    id: str
    source: InstitutionalMemorySource
    created_at: str = Field(alias="createdAt")
    sim_day: int = Field(alias="simDay")
    originating_agent: AgentId | None = Field(default=None, alias="originatingAgent")
    # id of the CaseStudy/FailedStrategyArchiveEntry/StrategyHallOfFameEntry/
    # ModelValidationReport/RiskWarning/MarketEnvironmentEntry this was
    # promoted from — the real audit-trail link.
    event_ref: str = Field(alias="eventRef")
    market_regime: MarketEnvironmentRegime | None = Field(default=None, alias="marketRegime")
    observation: str
    interpretation: str | None = None
    lesson: str | None = None
    confidence: float
    provenance: str
    relevance_pct: float = Field(alias="relevancePct")
    status: InstitutionalMemoryStatus = "active"
    supersedes_id: str | None = Field(default=None, alias="supersedesId")
    superseded_by_id: str | None = Field(default=None, alias="supersededById")
    supporting_evidence: list[str] = Field(default_factory=list, alias="supportingEvidence")


# v0.7 Feature 55 (the brief self-numbered it "Feature 54," already used
# above for the Decision Memory System — see app/war_room.py's module
# docstring for the collision note) — the Executive Decision Simulator's
# "Digital War Room." One permanent record per new TradeProposal, joining
# every department-level analysis this codebase already generates
# (DepartmentOpinion/ExecutiveRecommendation from app/executive_intelligence.py,
# WhatIfSimulation from app/whatif.py, SimilarTradesSummary from
# app/decision_vault.py) plus three genuinely new pieces: a combined
# Decision Score, an Expected Value read over the real 12-scenario
# simulation, and a real, signal-grounded Contingency Plan. See
# app/war_room.py's module docstring for the full honesty boundary,
# including why literal "R-Multiple" is deliberately not here (same gap
# DecisionVaultEntry.rMultiple already documents — no stop-loss/initial-
# risk concept exists anywhere in this codebase's real risk engine).
class ExpectedValueAnalysis(CamelModel):
    """A real, probability-weighted read over WhatIfSimulation's own 12
    real bootstrap scenarios — never a fabricated forecast. `edgePct` is
    the expected value above the organic, unbiased baseline scenario
    (the same "no scenario bias" resample WhatIfSimulation.baseline
    already is), so it isolates whatever real skew the scenario mix adds
    over doing nothing special. `riskToReward` is a real ratio of
    reward-range to typical-drawdown magnitude — deliberately labeled
    Risk-to-Reward, not "R-Multiple," since no stop-loss/initial-risk
    unit exists anywhere in this codebase to measure R against."""

    expected_value_pct: float = Field(alias="expectedValuePct")
    edge_pct: float = Field(alias="edgePct")
    risk_to_reward: float = Field(alias="riskToReward")
    positive_expectancy: bool = Field(alias="positiveExpectancy")
    detail: str


class ContingencyStep(CamelModel):
    """One real IF/THEN response, grounded in a real signal already
    computed for this symbol this tick (a liquidity sweep, an elevated
    news-risk read, a regime shift) — never an invented playbook item.
    `triggered` is a real, checkable read of whether that condition is
    true right now, not a hypothetical."""

    condition: str
    action: str
    triggered: bool


class DecisionScoreBreakdown(CamelModel):
    """Every sub-score here already exists as a real signal elsewhere in
    this codebase (see app/war_room.py's build_decision_score() for the
    exact source of each) — this class only combines them. Sub-scores
    with no real data available for this specific proposal (most often
    `strategyHealthScore` — no ordinary Trading Floor trade links back to
    a tested Strategy, see app/decision_vault.py's own established gap)
    are `null`, and the composite renormalizes over only the sub-scores
    that are actually real for this proposal, never substituting a
    fabricated placeholder."""

    evidence_score: float = Field(alias="evidenceScore")
    confidence_score: float = Field(alias="confidenceScore")
    risk_score: float = Field(alias="riskScore")
    expected_value_score: float = Field(alias="expectedValueScore")
    strategy_health_score: float | None = Field(
        default=None, alias="strategyHealthScore"
    )
    market_quality_score: float = Field(alias="marketQualityScore")
    liquidity_quality_score: float = Field(alias="liquidityQualityScore")
    portfolio_compatibility_score: float = Field(alias="portfolioCompatibilityScore")
    # CEO directive "Professional Quant Firm Phase 41-45" — "CONFLUENCE
    # QUALITY... prevent double-counting." A real, disclosed 0-100 read
    # of how many of app/evidence_confluence.py's 6 real DIRECTIONAL
    # evidence families (trend/momentum/volume/price_structure/
    # liquidity/pattern — `levels`/Fibonacci is informational-only,
    # never counted, matching that module's own established convention)
    # independently agree with this proposal's own direction — never a
    # naive raw-signal count (see EvidenceConfluenceRead.independent_
    # family_count vs. raw_signal_count). `None` only when this symbol's
    # own real candle history was unavailable for this tick.
    evidence_confluence_score: float | None = Field(default=None, alias="evidenceConfluenceScore")
    overall: float
    threshold: float
    passed: bool


class ScenarioOutcomeComparison(CamelModel):
    """Filled in once the linked trade actually closes (see app/nexus.py's
    closed-trade loop) — a real comparison of WhatIfSimulation's own
    stored predicted range for whichever scenario the real outcome fell
    closest to, against what actually happened. Never a claim that the
    scenario "predicted" the trade — see detail's own wording."""

    matched_scenario: ScenarioType = Field(alias="matchedScenario")
    matched_label: str = Field(alias="matchedLabel")
    predicted_range_low_pct: float = Field(alias="predictedRangeLowPct")
    predicted_range_high_pct: float = Field(alias="predictedRangeHighPct")
    actual_pnl_pct: float = Field(alias="actualPnlPct")
    within_predicted_range: bool = Field(alias="withinPredictedRange")
    detail: str


# v0.7 Chapter 57 — Institutional Position Sizing & Capital Deployment
# Engine (app/position_sizing.py). Four real tiers, ordered narrowest to
# widest allowed allocation — see that module's own docstring for the
# exact assignment rule and PortfolioIntelligenceState honesty boundary.
PositionTier = Literal["exploratory", "standard", "high_conviction", "institutional"]


# CEO directive "Portfolio Construction, Capital Allocation & Execution
# Realism," Phase 3 — "POSITION SIZE ~ RISK BUDGET / DISTANCE TO STOP."
# `available=False` (never a fabricated stop distance) when this symbol
# doesn't yet have enough real candle history for a real ATR read — see
# app/position_sizing.py's own module docstring for the exact ATR
# period/multiplier reused (the same real, already-established Chandelier
# Stop convention app/ema_pullback_research.py/app/strategy_engine.py's
# backtest engines already use, never a second, independently-tuned
# constant). `risk_budget_usd` is the same real dollar amount
# recommended_quantity()'s own risk_per_trade_pct ceiling already
# implies — reused, not a new risk parameter — so a strategy trading a
# volatile symbol gets a SMALLER quantity at the SAME dollar risk, never
# a larger one, per the directive's own explicit rule.
class VolatilitySizingRead(CamelModel):
    # `war_room_sessions` (a list — see app/persistence.py's own
    # _deep_merge_defaults docstring: "lists are taken wholesale... every
    # field added to a model that lives inside one of those lists must
    # have a default value") holds PositionSizingResult, so every field
    # here needs a real default for a save from before this feature
    # existed to still validate on load. `available=False` is the
    # honest one — a pre-existing WarRoomSession never had a real ATR
    # read computed for it, never fabricated retroactively.
    available: bool = False
    atr_value: float | None = Field(default=None, alias="atrValue")
    # 22 (not imported from app.ema_pullback_research.CHANDELIER_ATR_PERIOD
    # — schemas.py must not import that business-logic module, a real
    # circular-import risk) is only ever this migration-fallback
    # default; every real read uses the actual constant.
    atr_period: int = Field(default=22, alias="atrPeriod")
    stop_distance: float | None = Field(default=None, alias="stopDistance")
    risk_budget_usd: float | None = Field(default=None, alias="riskBudgetUsd")
    volatility_cap_quantity: float | None = Field(default=None, alias="volatilityCapQuantity")
    detail: str = "Not computed — this position sizing result predates real ATR-based volatility sizing."


class PositionSizingResult(CamelModel):
    """The Position Sizing Engine's real, logged justification for one
    proposal's final quantity — never a bare number with no trail (see
    app/position_sizing.py's module docstring). `final_quantity` is
    always <= `ceiling_quantity`: this engine only ever narrows what
    app/risk_engine.py's recommended_quantity() already allows, never
    widens it."""

    tier: PositionTier
    tier_label: str = Field(alias="tierLabel")
    sizing_score: float = Field(alias="sizingScore")
    ceiling_quantity: float = Field(alias="ceilingQuantity")
    tier_cap_quantity: float = Field(alias="tierCapQuantity")
    final_quantity: float = Field(alias="finalQuantity")
    capital_deployed_pct: float = Field(alias="capitalDeployedPct")
    weekly_deployment_pct: float = Field(alias="weeklyDeploymentPct")
    weekly_deployment_cap_pct: float = Field(alias="weeklyDeploymentCapPct")
    cash_reserve_ok: bool = Field(alias="cashReserveOk")
    portfolio_heat_cap_ok: bool = Field(alias="portfolioHeatCapOk")
    institutional_gates_passed: bool = Field(alias="institutionalGatesPassed")
    reduced_from_ceiling: bool = Field(alias="reducedFromCeiling")
    volatility_sizing: VolatilitySizingRead = Field(default_factory=VolatilitySizingRead, alias="volatilitySizing")
    detail: str


class WarRoomSession(CamelModel):
    id: str
    proposal_id: str = Field(alias="proposalId")
    symbol: str
    department_opinions: list[DepartmentOpinion] = Field(alias="departmentOpinions")
    recommendation: ExecutiveRecommendation
    scenario_simulation: WhatIfSimulation = Field(alias="scenarioSimulation")
    similar_trades: SimilarTradesSummary = Field(alias="similarTrades")
    expected_value: ExpectedValueAnalysis = Field(alias="expectedValue")
    decision_score: DecisionScoreBreakdown = Field(alias="decisionScore")
    contingency_plan: list[ContingencyStep] = Field(
        default_factory=list, alias="contingencyPlan"
    )
    # v0.7 Chapter 57 — filled in by app/nexus.py right after this session
    # is built, once a ceiling quantity and this session's own real
    # Expected Value/Decision Score exist to size against. Optional only
    # for the brief instant during construction before that step runs —
    # every session actually appended to war_room_sessions has this set.
    position_sizing: PositionSizingResult | None = Field(
        default=None, alias="positionSizing"
    )
    # Always True by construction, not a separate check: Evidence Score
    # is a strict renormalized subset average of Confidence Score's own
    # factors (see app/decision_vault.py's compute_evidence_score()), so
    # evidence can never exceed confidence structurally. Surfaced here
    # honestly as what it is — a standing invariant, not a check that can
    # meaningfully fail — rather than fabricating scenarios where it could.
    confidence_validated: bool = Field(alias="confidenceValidated")
    outcome_comparison: ScenarioOutcomeComparison | None = Field(
        default=None, alias="outcomeComparison"
    )
    # CEO directive "Professional Quant Firm Phase 41-45" — "CONFLUENCE
    # QUALITY... prevent double-counting." app/evidence_confluence.py's
    # real evidence-family read (real, existing, already-tested — see
    # that module's own docstring) was computed but never wired into any
    # live decision until now; connected here (not duplicated) so a CEO
    # can see the real family-level breakdown behind `decision_score.
    # evidence_confluence_score`, not just the summary number. `None`
    # only when this symbol's own real candle history was unavailable
    # for this tick (see app/war_room.py's build_war_room_session()).
    evidence_confluence: EvidenceConfluenceRead | None = Field(default=None, alias="evidenceConfluence")
    # CEO directive "Portfolio Construction, Capital Allocation &
    # Execution Realism," Phase 4 — the real, statistical Pearson-
    # correlation count (app/portfolio_intelligence.py's
    # count_correlated_positions(), distinct from the category-co-
    # occurrence read that already feeds this session's own
    # portfolio-compatibility score) was computed at proposal time to
    # decide the Opportunity Gatekeeper's approve/reject call, then
    # discarded for every APPROVED candidate — a real correlation-risk
    # read the CEO never actually got to see. Phase 9 closes that: now
    # persisted here too, so a "why this trade" view has the real number
    # instead of losing it once the gate passes. `None` only for a
    # session created before this field existed.
    statistical_correlated_positions: int | None = Field(default=None, alias="statisticalCorrelatedPositions")
    created_at: str = Field(alias="createdAt")


# v0.7 Feature 56 — Enterprise Portfolio Intelligence (app/portfolio_intelligence.py).
# Computed fresh every tick, the same "cheap to recompute, no permanence
# requirement" convention app/company_health.py and app/company_dna.py
# already use — never a persisted, driftable second copy of the
# portfolio's own real state. See app/portfolio_intelligence.py's module
# docstring for the full honesty boundary, including why "sector" is
# named "category" throughout (this codebase has no real sector taxonomy
# — see app/risk_engine.py's evaluate_guardian_exposure() for the
# identical, already-established honesty note) and why Portfolio Heat is
# a real warning signal, never an auto-corrective action (ROADMAP.md's
# own stop condition: "risk is measured and displayed, never auto-hedged
# or auto-corrected without the player").
class CategoryExposure(CamelModel):
    category: ResearchCategory
    position_count: int = Field(alias="positionCount")
    value: float
    pct_of_equity: float = Field(alias="pctOfEquity")


class CorrelationPair(CamelModel):
    """A real Pearson correlation coefficient computed from the two
    symbols' own real recent candle returns — never a fabricated
    relationship. Only surfaced when |correlation| clears
    CORRELATION_CLUSTER_THRESHOLD, so a portfolio with only loosely-
    related positions reports no pairs at all."""

    symbol_a: str = Field(alias="symbolA")
    symbol_b: str = Field(alias="symbolB")
    correlation: float
    direction: Literal["positive", "negative"]


class PortfolioHeat(CamelModel):
    total_capital_at_risk_pct: float = Field(alias="totalCapitalAtRiskPct")
    unrealized_drawdown_pct: float = Field(alias="unrealizedDrawdownPct")
    largest_position_pct: float = Field(alias="largestPositionPct")
    hottest_category: ResearchCategory | None = Field(
        default=None, alias="hottestCategory"
    )
    hottest_category_pct: float = Field(default=0.0, alias="hottestCategoryPct")
    tier: Literal["cool", "warm", "hot", "overheated"]


class CapitalEfficiency(CamelModel):
    """Real profit generated per dollar of capital committed, averaged
    over closed trades — capital_locked is each trade's own real
    entry_price * quantity, hold_time is its own real duration_minutes.
    A trade with no capital committed (shouldn't exist, guarded for
    completeness) is excluded rather than divided-by-zero."""

    profit_per_dollar: float = Field(alias="profitPerDollar")
    profit_per_dollar_hour: float = Field(alias="profitPerDollarHour")
    trades_measured: int = Field(alias="tradesMeasured")


# CEO directive "Portfolio Construction, Capital Allocation & Execution
# Realism" — the audit for this directive grep-confirmed zero matches
# for gross/net exposure anywhere in this codebase; every existing
# exposure read (category exposure, Guardian's per-symbol concentration)
# sums quantity*price regardless of side, so a $10k long and a $10k short
# in the same portfolio were indistinguishable from $20k of one-directional
# risk. Real, computed fresh from PaperPosition.side — no fabrication.
class ExposureSummary(CamelModel):
    long_value: float = Field(alias="longValue")
    short_value: float = Field(alias="shortValue")
    net_exposure: float = Field(alias="netExposure")
    gross_exposure: float = Field(alias="grossExposure")
    net_exposure_pct: float = Field(alias="netExposurePct")
    gross_exposure_pct: float = Field(alias="grossExposurePct")
    long_position_count: int = Field(alias="longPositionCount")
    short_position_count: int = Field(alias="shortPositionCount")


# CEO directive "Portfolio Construction, Capital Allocation & Execution
# Realism" — the live analogue of app/performance_attribution.py's
# compute_strategy_performance() (which only ever sees CLOSED trades).
# Groups currently-OPEN positions by their real, CEO-explicit
# PaperPosition.strategy_id (see that field's own schema docstring for
# how it gets set). `strategy_id: null` is its own real, honest bucket —
# every open position the CEO never attributed to a strategy — never
# folded into an attributed strategy's numbers.
class StrategyExposureRead(CamelModel):
    strategy_id: str | None = Field(alias="strategyId")
    position_count: int = Field(alias="positionCount")
    value: float
    pct_of_equity: float = Field(alias="pctOfEquity")
    long_value: float = Field(alias="longValue")
    short_value: float = Field(alias="shortValue")


class PortfolioIntelligence(CamelModel):
    equity: float
    cash_balance: float = Field(alias="cashBalance")
    cash_pct_of_equity: float = Field(alias="cashPctOfEquity")
    deployed_pct_of_equity: float = Field(alias="deployedPctOfEquity")
    category_exposure: list[CategoryExposure] = Field(
        default_factory=list, alias="categoryExposure"
    )
    correlation_pairs: list[CorrelationPair] = Field(
        default_factory=list, alias="correlationPairs"
    )
    heat: PortfolioHeat
    exposure: ExposureSummary
    strategy_exposure: list[StrategyExposureRead] = Field(
        default_factory=list, alias="strategyExposure"
    )
    capital_efficiency: CapitalEfficiency = Field(alias="capitalEfficiency")
    # A real, specific "what's the alternative" read — never generic
    # filler. See app/portfolio_intelligence.py's _opportunity_cost().
    opportunity_cost: str = Field(alias="opportunityCost")
    updated_at: str = Field(alias="updatedAt")


# Design Bible Chapter 71 — Economic Intelligence Center (app/economic_
# intelligence.py). See that module's own docstring for the full honesty
# boundary: this codebase has no real macroeconomic data source anywhere
# (no API keys, no live feed — app/market_data.py's own docstring already
# establishes this), so EIC is a real cross-signal SYNTHESIS layer over
# already-real state (MarketEnvironment's regime, MarketIntelligence's
# quality/news-risk reads, PortfolioIntelligence's correlation/category/
# heat reads) rather than a tracker of real central banks, real economic
# calendars, or real global events — none of which are fabricated here.
EconomicHealthTier = Literal["thriving", "stable", "cautious", "stressed", "critical"]


class EconomicSignalFactor(CamelModel):
    """One real, named, published-formula input into the Economic Health
    Score — never a blended/hidden number, the same "no black-box
    composite" convention CompanyHealth/PropFirmComplianceScore/
    WeightedExecutiveRecommendation already established."""

    name: str
    score: float  # 0-100, higher = healthier
    weight: float
    detail: str


class EconomicHealthScore(CamelModel):
    overall: float  # 0-100, a real weighted average of `factors` below
    tier: EconomicHealthTier
    factors: list[EconomicSignalFactor] = Field(default_factory=list)
    reasoning: str


class EconomicConfidenceRead(CamelModel):
    """The brief's own "Economic Confidence Engine" requirement: every
    macro conclusion ships with confidence, evidence quality, and named
    supporting/contradicting evidence rather than being presented as
    fact — the same convention app/confidence.py's DecisionConfidence
    already established for trade decisions, applied here to the
    company's own synthesized environment read."""

    confidence_pct: float = Field(alias="confidencePct")
    evidence_quality: Literal["thin", "moderate", "strong"] = Field(
        alias="evidenceQuality"
    )
    supporting_evidence: list[str] = Field(
        default_factory=list, alias="supportingEvidence"
    )
    contradicting_evidence: list[str] = Field(
        default_factory=list, alias="contradictingEvidence"
    )
    key_assumptions: list[str] = Field(default_factory=list, alias="keyAssumptions")
    alternative_outcome: str = Field(alias="alternativeOutcome")


class MarketNarrativeEntry(CamelModel):
    """A real, evidence-cited explanation — never "the Fed cut rates" (no
    real Fed data exists here), always a diff against this company's own
    last stored EconomicIntelligenceReport, naming the specific real
    signal(s) that actually moved. See economic_intelligence.py's
    generate_market_narrative()."""

    id: str
    headline: str
    body: str
    evidence: list[str] = Field(default_factory=list)
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


class EconomicIntelligenceState(CamelModel):
    """The always-current cross-signal read — recomputed fresh every
    tick from real already-computed state, same "cheap, never a stale
    second copy" convention as company_health/market_intelligence."""

    regime: MarketEnvironmentRegime
    regime_label: str = Field(alias="regimeLabel")
    market_quality_tier: MarketQualityTier = Field(alias="marketQualityTier")
    health: EconomicHealthScore
    confidence: EconomicConfidenceRead
    correlation_pairs: list[CorrelationPair] = Field(
        default_factory=list, alias="correlationPairs"
    )
    category_exposure: list[CategoryExposure] = Field(
        default_factory=list, alias="categoryExposure"
    )
    news_risk: NewsRiskRead = Field(alias="newsRisk")
    updated_at: str = Field(alias="updatedAt")


class EconomicIntelligenceReport(CamelModel):
    """One real, permanent snapshot per real in-game day (the Daily Macro
    Brief), generated on the same evening cadence as Market Intelligence's
    own Executive Market Brief — see app/nexus.py. Embeds that day's real
    EconomicIntelligenceState plus a real, diffed MarketNarrativeEntry."""

    id: str
    sim_day: int = Field(alias="simDay")
    snapshot: EconomicIntelligenceState
    narrative: MarketNarrativeEntry
    created_at: str = Field(alias="createdAt")


# Design Bible Chapter 72 — Black Swan Intelligence & Resilience System
# (app/black_swan.py). See that module's own docstring for the full
# honesty boundary: this codebase has no historical black-swan dataset,
# no real broker connection, and no macro/sector/credit data (Chapters
# 68/71 already established this), so BSIRS is a real STRESS-AND-
# RESILIENCE SYNTHESIS layer over already-real signals (Risk Engine's
# live warnings, Market Intelligence's quality/volatility/liquidity/news
# reads, Portfolio Intelligence's correlation/heat reads, Regime
# Reconciliation's aligned/diverging read, Economic Intelligence's health
# tier) rather than a tracker of real historical crises or a real broker
# health monitor, neither of which are fabricated here.
BlackSwanRiskTier = Literal["green", "yellow", "orange", "red", "critical"]


class BlackSwanSignalFactor(CamelModel):
    """One real, named, published-formula input into the Early Warning
    Score — never a blended/hidden number, the same "no black-box
    composite" convention EconomicSignalFactor/CompanyHealth already
    established. Higher score always means MORE stress, the opposite
    direction of EconomicSignalFactor's "higher = healthier"."""

    name: str
    score: float  # 0-100, higher = more stress
    weight: float
    detail: str


class EarlyWarningScore(CamelModel):
    overall: float  # 0-100, a real weighted average of `factors` below
    tier: BlackSwanRiskTier
    factors: list[BlackSwanSignalFactor] = Field(default_factory=list)
    reasoning: str


class BlackSwanConfidenceRead(CamelModel):
    """The brief's "always explain WHY the estimate changed" requirement,
    plus an honest confidence wrapper — same shape as Chapter 71's
    EconomicConfidenceRead, applied to a stress read instead of a
    favorability read."""

    confidence_pct: float = Field(alias="confidencePct")
    evidence_quality: Literal["thin", "moderate", "strong"] = Field(
        alias="evidenceQuality"
    )
    supporting_evidence: list[str] = Field(
        default_factory=list, alias="supportingEvidence"
    )
    contradicting_evidence: list[str] = Field(
        default_factory=list, alias="contradictingEvidence"
    )
    key_assumptions: list[str] = Field(default_factory=list, alias="keyAssumptions")
    alternative_outcome: str = Field(alias="alternativeOutcome")


class BlackSwanNarrativeEntry(CamelModel):
    """A real, evidence-cited explanation of what changed since the last
    stored BlackSwanReport — never an invented cause like "a banking
    crisis began." See app/black_swan.py's generate_black_swan_narrative()."""

    id: str
    headline: str
    body: str
    evidence: list[str] = Field(default_factory=list)
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


class BlackSwanIntelligenceState(CamelModel):
    """The always-current stress read — recomputed fresh every tick from
    real already-computed state, same convention as
    company_health/portfolio_intelligence/economic_intelligence."""

    warning: EarlyWarningScore
    confidence: BlackSwanConfidenceRead
    updated_at: str = Field(alias="updatedAt")


class BlackSwanReport(CamelModel):
    """One real, permanent snapshot per real in-game day (the Daily Black
    Swan Situation Report), same once-per-evening cadence as Chapter 71's
    own Daily Economic Intelligence Brief."""

    id: str
    sim_day: int = Field(alias="simDay")
    snapshot: BlackSwanIntelligenceState
    narrative: BlackSwanNarrativeEntry
    created_at: str = Field(alias="createdAt")


class DefensiveModeRecommendation(CamelModel):
    """One real, computed recommendation — never generic filler. `automatic`
    is true only for the two actions this codebase's own "never auto-
    correct a position without the player" principle (app/portfolio_
    intelligence.py) allows to actually apply while Defensive Mode is
    active: tightening RiskLimits and pausing new proposal generation.
    Every other recommendation (closing a position, raising cash) always
    requires the CEO to act manually through the existing controls."""

    action: str
    detail: str
    automatic: bool


class DefensiveModeState(CamelModel):
    """Design Bible Chapter 72 — CEO-controlled defensive posture. Mirrors
    app/emergency_stop.py's EmergencyStopState shape (active/activatedAt)
    but is a real, distinct, lighter mechanism: it tightens RiskLimits and
    pauses new AI-generated trade proposals, but — unlike Emergency
    Stop — never blocks the CEO's own manual trading."""

    active: bool = False
    trigger_tier: BlackSwanRiskTier = Field(default="red", alias="triggerTier")
    auto_trigger_enabled: bool = Field(default=False, alias="autoTriggerEnabled")
    activated_at: str | None = Field(default=None, alias="activatedAt")
    deactivated_at: str | None = Field(default=None, alias="deactivatedAt")
    activation_reason: str | None = Field(default=None, alias="activationReason")
    # A real snapshot of the CEO's global RiskLimits taken the moment
    # Defensive Mode activates, so deactivation can restore them exactly
    # — never a hardcoded "undo" that might not match what was active.
    prior_risk_limits: RiskLimits | None = Field(
        default=None, alias="priorRiskLimits"
    )
    equity_at_activation: float | None = Field(
        default=None, alias="equityAtActivation"
    )
    # Real sim-clock minutes (app/portfolio.py's sim_minutes()) at
    # activation, so a Post-Event Analysis's real duration is measured in
    # game time, the same unit every PaperTrade already uses, not wall
    # clock time.
    activated_sim_minutes: int | None = Field(
        default=None, alias="activatedSimMinutes"
    )
    peak_tier_this_episode: BlackSwanRiskTier | None = Field(
        default=None, alias="peakTierThisEpisode"
    )
    recommendations: list[DefensiveModeRecommendation] = Field(default_factory=list)


class StressTestLevelResult(CamelModel):
    shock_pct: float = Field(alias="shockPct")  # negative, e.g. -35.0
    resulting_equity: float = Field(alias="resultingEquity")
    resulting_drawdown_pct: float = Field(alias="resultingDrawdownPct")
    breaches_max_drawdown: bool = Field(alias="breachesMaxDrawdown")
    capital_survives: bool = Field(alias="capitalSurvives")
    # None when the portfolio has no positive trailing realized P&L to
    # project a recovery from — an honest cut, never a fabricated ETA.
    recovery_days_estimate: float | None = Field(
        default=None, alias="recoveryDaysEstimate"
    )
    recovery_note: str = Field(alias="recoveryNote")


class PortfolioStressTestResult(CamelModel):
    """The brief's -10/-20/-35/-50/-70% ladder, computed fresh on demand
    against any real portfolio (the primary one, or any Account's — see
    app/accounts.py). Never persisted, same "just as honest recomputed
    live" convention app/whatif.py already established."""

    account_id: str | None = Field(default=None, alias="accountId")
    account_label: str = Field(alias="accountLabel")
    starting_equity: float = Field(alias="startingEquity")
    # Real average LiquidityRead.liquidityScore across currently-held
    # symbols; None if nothing is held or no read is on file.
    held_position_liquidity_score: float | None = Field(
        default=None, alias="heldPositionLiquidityScore"
    )
    levels: list[StressTestLevelResult] = Field(default_factory=list)
    computed_at: str = Field(alias="computedAt")


# Four scenarios, each named for its real mechanism (reusing app/
# whatif.py's own volatility-scaled shock convention), never for a
# fabricated historical event. See app/black_swan.py's module docstring.
BlackSwanScenarioType = Literal[
    "flash_crash", "severe_selloff", "liquidity_freeze", "correlation_breakdown"
]


class PortfolioScenarioResult(CamelModel):
    scenario_type: BlackSwanScenarioType = Field(alias="scenarioType")
    label: str
    account_id: str | None = Field(default=None, alias="accountId")
    account_label: str = Field(alias="accountLabel")
    starting_equity: float = Field(alias="startingEquity")
    shocked_equity: float = Field(alias="shockedEquity")
    impact_pct: float = Field(alias="impactPct")
    impact_amount: float = Field(alias="impactAmount")
    category_impact: list[CategoryExposure] = Field(
        default_factory=list, alias="categoryImpact"
    )
    breaches_max_drawdown: bool = Field(alias="breachesMaxDrawdown")
    capital_survives: bool = Field(alias="capitalSurvives")
    detail: str
    computed_at: str = Field(alias="computedAt")


class PlaybookStep(CamelModel):
    label: str
    detail: str


class BlackSwanPlaybook(CamelModel):
    """One real, generically-named Elevated Risk Response Playbook —
    live-populated with today's actual Defensive Mode recommendations,
    never one of eight static documents for event types this codebase
    has no real signal for (Broker Failure, Cyberattack, Pandemic, ...).
    See app/black_swan.py's module docstring."""

    current_tier: BlackSwanRiskTier = Field(alias="currentTier")
    immediate_actions: list[PlaybookStep] = Field(
        default_factory=list, alias="immediateActions"
    )
    department_responsibilities: list[PlaybookStep] = Field(
        default_factory=list, alias="departmentResponsibilities"
    )
    ceo_checklist: list[PlaybookStep] = Field(default_factory=list, alias="ceoChecklist")
    recovery_plan: str = Field(alias="recoveryPlan")
    updated_at: str = Field(alias="updatedAt")


class BrokerResilienceRead(CamelModel):
    """The honest answer to the brief's Broker Resilience section:
    app/broker.py has no real broker connection to monitor (its own
    docstring: "no code path that reaches a real order-execution
    endpoint"). A live health score here would fabricate monitoring of a
    dependency that doesn't exist — this is a static, honest read
    instead."""

    status: Literal["simulated"] = "simulated"
    message: str = (
        "PaperBroker — 100% simulated execution. No real broker connection "
        "exists in this codebase, so there is nothing live to monitor."
    )


class CrisisBriefing(CamelModel):
    """The honest answer to the brief's "Automatically trigger emergency
    Executive Board meetings" — Chapter 70 Part 1 already confirmed no
    automatic meeting-trigger mechanism, and no general-purpose non-trade
    Decision Center, exists anywhere in this codebase. A CrisisBriefing is
    a real, structured situation report (reusing the exact real signals a
    meeting would need) rather than a fabricated vote. Never persisted as
    its own list — see app/black_swan.py's generate_crisis_briefing(),
    which writes it straight into CompanyMemory and the Knowledge Graph."""

    id: str
    sim_day: int = Field(alias="simDay")
    tier: BlackSwanRiskTier
    overall_score: float = Field(alias="overallScore")
    situation_summary: str = Field(alias="situationSummary")
    portfolio_equity: float = Field(alias="portfolioEquity")
    category_exposure: list[CategoryExposure] = Field(
        default_factory=list, alias="categoryExposure"
    )
    recommendations: list[DefensiveModeRecommendation] = Field(default_factory=list)
    created_at: str = Field(alias="createdAt")


# Design Bible Chapter 72 Part 2 — Institutional Survival Score. Reuses
# three of the Early Warning Score's own already-computed factors
# (Active Risk Warnings, Liquidity, Correlation Breakdown, inverted back
# to "how resilient" instead of "how stressed") rather than recomputing
# the same raw signals a second time. See app/black_swan.py's module
# docstring for the honesty boundary — "Leverage" and "Counterparty
# Risk" are cut outright (no margin or counterparty concept exists
# anywhere in this codebase), and no "Estimated Survival Probability" is
# fabricated (no historical base rate to calibrate one against).
InstitutionalSurvivalGrade = Literal["a_plus", "a", "b", "c", "d", "f"]


class SurvivalScoreFactor(CamelModel):
    """One real, named, published-formula input — never a blended/hidden
    number. Higher score always means MORE resilient, the same direction
    as EconomicSignalFactor (and the opposite of BlackSwanSignalFactor)."""

    name: str
    score: float  # 0-100, higher = more resilient
    weight: float
    detail: str


class InstitutionalSurvivalScore(CamelModel):
    """The always-current read — recomputed fresh every tick, same
    convention as company_health/black_swan_intelligence. No forecasted
    "survival probability" is attached — the score itself, and its named
    factors, are the honest answer to "how prepared is this company."""

    overall: float  # 0-100
    grade: InstitutionalSurvivalGrade
    factors: list[SurvivalScoreFactor] = Field(default_factory=list)
    primary_strengths: list[str] = Field(default_factory=list, alias="primaryStrengths")
    primary_weaknesses: list[str] = Field(default_factory=list, alias="primaryWeaknesses")
    # Real, specific, computed suggestions tied to the weakest factors —
    # never generic filler like "diversify more."
    top_improvements: list[str] = Field(default_factory=list, alias="topImprovements")
    reasoning: str
    updated_at: str = Field(alias="updatedAt")


class BlackSwanEventRecord(CamelModel):
    """Post-Event Analysis — one real, permanent record per completed
    Defensive Mode episode. `equity_change_pct` is real only when the
    episode was live (Defensive Mode was actually active); Stress Tests
    and Scenario Simulations never write one of these, since they are
    hypothetical reads, not real episodes."""

    id: str
    trigger_reason: str = Field(alias="triggerReason")
    peak_tier: BlackSwanRiskTier = Field(alias="peakTier")
    activated_at: str = Field(alias="activatedAt")
    deactivated_at: str = Field(alias="deactivatedAt")
    duration_sim_minutes: int = Field(alias="durationSimMinutes")
    equity_at_activation: float = Field(alias="equityAtActivation")
    equity_at_deactivation: float = Field(alias="equityAtDeactivation")
    equity_change_pct: float = Field(alias="equityChangePct")
    largest_contributing_factor: str = Field(alias="largestContributingFactor")
    # Real, distinct symbols held at the moment the episode ended — lets
    # the Knowledge Graph draw a real "same symbol" edge to any research
    # on file for that symbol, the same non-causal honesty rule Chapter
    # 61's own trade/research edges already use. Never a claim that this
    # episode was "caused by" or "about" any specific symbol.
    affected_symbols: list[str] = Field(default_factory=list, alias="affectedSymbols")
    lesson: str
    created_at: str = Field(alias="createdAt")


# Design Bible Chapter 73 — Compliance, Audit & Governance System
# (app/audit_log.py). Computed fresh per request from state this
# codebase already persists — never a second, parallel logging system,
# and never a new GameSaveState field. See that module's own docstring
# for the full honesty boundary: no per-event Broker/User/Software-
# Version fields (this codebase has one simulated broker, one player,
# and no historical version tag), no mutable incident-management
# workflow (every incident here is resolved-by-construction the instant
# it's recorded).
AuditEventCategory = Literal[
    "ceo_decision",
    "gatekeeper_rejection",
    "opportunity_rejection",
    "risk_warning",
    "discipline_review",
    "emergency_stop",
    "defensive_mode",
    "crisis_briefing",
    "rule_violation",
    # Design Bible Chapter 75 — a real Trading Mode change or Daily
    # Circuit Breaker tier change, both recorded as MemoryRecords by
    # app/trading_modes.py.
    "trading_mode_change",
    "circuit_breaker_tier",
    # Design Bible Chapter 73.5 — a real Travel Mode activation/
    # deactivation, recorded by app/travel_mode.py the same way Chapter
    # 75 records its own mode/tier changes.
    "travel_mode_change",
    # Design Bible Chapter 70 Part 1 — a real emergency Board Report
    # (app/board.py), fired on a real Emergency Stop activation or a
    # Black Swan tier crossing into red/critical.
    "board_report",
    # Design Bible Chapter 74 — a real Self-Improvement Proposal
    # generated (app/self_improvement.py) or an Institutional Evolution
    # Report filed (app/evolution.py).
    "self_improvement_proposal",
    "evolution_report",
]


class AuditEntry(CamelModel):
    """One real event, built from one real already-persisted record's own
    fields — never a templated narrative. `relatedId` links back to the
    real source record (a proposal id, a decision id, an account id) so
    the CEO can cross-reference the original, not just this summary."""

    id: str
    timestamp: str
    sim_day: int = Field(alias="simDay")
    category: AuditEventCategory
    severity: AlertSeverity
    department: str
    summary: str
    detail: str
    related_id: str | None = Field(default=None, alias="relatedId")


class GovernanceLayer(CamelModel):
    """One real, disclosed layer of the actual decision pipeline this
    codebase enforces every tick — never a new authority chain. `order`
    is the real position app/gatekeeper.py::evaluate_gatekeeper() checks
    it in; `wired` is false only for the Institutional Rule Engine, which
    is real but not yet routed into live trade execution for non-primary
    accounts (Chapter 69 Part 3's own documented gap)."""

    order: int
    name: str
    module: str
    description: str
    wired: bool


class ComplianceOverview(CamelModel):
    """The Compliance Dashboard's real aggregate — every number here is
    either a direct count over the real Audit Log or a value reused
    verbatim from an already-real computed source (Executive Accuracy,
    Defensive Mode status), never a new blended score beyond the one
    disclosed Compliance Score formula itself."""

    compliance_score: float = Field(alias="complianceScore")
    open_incident_count: int = Field(alias="openIncidentCount")
    critical_incident_count: int = Field(alias="criticalIncidentCount")
    total_audit_entries: int = Field(alias="totalAuditEntries")
    ceo_override_count: int = Field(alias="ceoOverrideCount")
    ceo_override_rate_pct: float = Field(alias="ceoOverrideRatePct")
    defensive_mode_active: bool = Field(alias="defensiveModeActive")
    emergency_stop_active: bool = Field(alias="emergencyStopActive")
    # Reused verbatim from Chapter 70 Part 2's own real, already-computed
    # per-department accuracy — never recomputed here.
    executive_accuracy: list[ExecutiveAccuracyScore] = Field(
        default_factory=list, alias="executiveAccuracy"
    )
    updated_at: str = Field(alias="updatedAt")


class CeoOverrideRecord(CamelModel):
    """One real CEO decision that disagreed with the AI's own
    recommendation — sourced directly from CeoDecisionRecord.agreedWithAi
    (Chapter 70 Part 2, real since that chapter), never a new tracking
    mechanism. `outcome` is the same real "pending"/"correct"/
    "incorrect"/"undecidable" grading that record already carries."""

    id: str
    proposal_id: str = Field(alias="proposalId")
    symbol: str
    ai_recommendation: AnalystChoice = Field(alias="aiRecommendation")
    ceo_decision: AnalystChoice = Field(alias="ceoDecision")
    outcome: Literal["pending", "correct", "incorrect", "undecidable"]
    created_at: str = Field(alias="createdAt")


# CEO directive "Features 31-35: Compliance, Governance & Continuous
# Improvement System," Feature 31 — the Compliance Incident Resolution
# Engine. Research finding, documented here per the directive's own
# "research first" rule: `app/audit_log.py`'s `compute_incidents()` is a
# PURE, EPHEMERAL FILTER over the Audit Log (severity != "info"),
# recomputed fresh on every `GET /api/audit/incidents` call, never
# persisted — the panel's own disclosed UI text says so directly:
# "There is no open/acknowledged/resolved workflow: incident resolution
# is not a real mechanic anywhere in this codebase today." That is the
# real, confirmed gap this schema closes — a genuine, persisted,
# stateful incident record, never a second audit log and never a
# duplicate detection mechanism (every ComplianceIncident is created
# FROM a real AuditEntry the existing `compute_audit_log()` already
# produces, matched 1:1 by `source_entry_id`, never independently
# detected a second way).
IncidentStatus = Literal[
    "open",
    "investigating",
    "remediation",
    "awaiting_verification",
    "resolved",
    "reopened",
]

# The real, ordered lifecycle the CEO's own brief specified. Enforced as
# an explicit allowed-transitions map (see app/compliance_incidents.py's
# ALLOWED_TRANSITIONS) — OPEN -> RESOLVED in one step is structurally
# impossible, never merely discouraged by convention.
IncidentRootCause = Literal[
    "process_failure",
    "control_failure",
    "data_failure",
    "model_failure",
    "human_error",
    "governance_failure",
    "communication_failure",
    "unknown",
]

IncidentVerificationStatus = Literal["not_verified", "verified", "verification_failed"]


class ComplianceIncident(CamelModel):
    """One real incident case, opened from a real Audit Log entry the
    instant it's created (never a fabricated backfill) and carried
    through a real, enforced lifecycle. `created_at`/`sim_day` are always
    the real source AuditEntry's own values — an incident's origin is
    never rewritten. `resolved_at`/`root_cause`/`corrective_action`/
    `verifier` stay `None` (UNKNOWN / NOT AVAILABLE, never a fabricated
    default) until a real `verify_and_resolve()` call sets them together,
    the one and only real path to `status="resolved"`. `reopened_count`
    and `status="reopened"` preserve history rather than rewriting it —
    a reopened incident's original `created_at`/`resolved_at` from its
    first resolution are never cleared, only superseded by the new
    lifecycle fields that follow."""

    id: str
    # The real AuditEntry.id this incident was opened from — the one
    # real link back to its originating record (a CeoDecisionRecord, a
    # GatekeeperRejection, a RiskWarning, a DisciplineReview, ...).
    source_entry_id: str = Field(alias="sourceEntryId")
    category: AuditEventCategory
    severity: AlertSeverity
    department: str
    summary: str
    detail: str
    related_id: str | None = Field(default=None, alias="relatedId")
    created_at: str = Field(alias="createdAt")
    sim_day: int = Field(alias="simDay")

    status: IncidentStatus = "open"
    owner: AgentId | None = Field(default=None)
    evidence: list[str] = Field(default_factory=list)
    remediation_plan: str | None = Field(default=None, alias="remediationPlan")
    # A real in-game-day SLA deadline, stamped only once remediation
    # actually begins (begin_remediation()) — never guessed at creation
    # time before anyone has assessed the real work involved.
    deadline_sim_day: int | None = Field(default=None, alias="deadlineSimDay")

    resolved_at: str | None = Field(default=None, alias="resolvedAt")
    resolution_sim_day: int | None = Field(default=None, alias="resolutionSimDay")
    verification_status: IncidentVerificationStatus = Field(default="not_verified", alias="verificationStatus")
    verifier: AgentId | None = Field(default=None)
    root_cause: IncidentRootCause | None = Field(default=None, alias="rootCause")
    corrective_action: str | None = Field(default=None, alias="correctiveAction")

    reopened_count: int = Field(default=0, alias="reopenedCount")
    updated_at: str = Field(alias="updatedAt")


# CEO directive "Features 31-35," Feature 31 — a real, disclosed
# aggregate over the persisted incident backlog. Every field here is
# either a direct count or a value computed by a named, documented
# function in app/compliance_incidents.py (never a second,
# independently-blended score). `average_resolution_sim_days` is `None`
# (NOT_ENOUGH_EVIDENCE) when nothing has ever been resolved through a
# real lifecycle yet — never a fabricated 0.
class ComplianceIncidentSummary(CamelModel):
    total_count: int = Field(alias="totalCount")
    open_count: int = Field(alias="openCount")
    resolved_count: int = Field(alias="resolvedCount")
    overdue_count: int = Field(alias="overdueCount")
    reopened_incident_count: int = Field(alias="reopenedIncidentCount")
    severity_weighted_backlog: float = Field(alias="severityWeightedBacklog")
    average_resolution_sim_days: float | None = Field(default=None, alias="averageResolutionSimDays")
    updated_at: str = Field(alias="updatedAt")


# CEO directive "Features 31-35," Feature 32 — CEO Override Governance
# (app/override_governance.py). RESEARCH FINDING, recorded here per the
# directive's own "research first" rule: `CeoDecisionRecord.outcome`
# already resolves overrides that produced a real trade exactly like any
# other decision ("pending" -> "correct"/"incorrect" once that trade
# closes, via `grade_ceo_decisions()`) — only an override that resolved
# to "wait" (no order placed) is `"undecidable"` forever. This module
# never re-grades that outcome a second way; it only adds a genuinely
# new axis alongside it: PROCESS QUALITY — was the override justified by
# the evidence that existed at the moment the CEO decided, evaluated
# from the real `ExecutiveMeetingLogEntry` for that same proposal
# (`opinions`, `decisionGradeScore`), never from the trade's own P&L.
# Process quality and outcome are computed, stored, and displayed as two
# separate fields — never collapsed into one score — so a correct
# process that lost money and a bad process that won are both shown
# honestly, per the directive's explicit "no hindsight-only evaluation"
# rule.
OverrideProcessQuality = Literal[
    "justified", "unjustified", "mixed", "not_enough_evidence"
]


class CeoOverrideEvaluation(CamelModel):
    """One real override — a `CeoDecisionRecord` where
    `agreed_with_ai=False` — carried alongside its own real process-
    quality read and its real (never re-derived) outcome. `evidence`
    below is drawn verbatim from the real `ExecutiveMeetingLogEntry`
    (department `evidence`/`concerns` for the departments that
    disagreed with the CEO's own eventual choice) — never a fabricated
    justification. `overrideReason` is `None` whenever the CEO didn't
    type one (see `CeoDecisionRecord.override_reason`'s own docstring)."""

    id: str
    decision_id: str = Field(alias="decisionId")
    proposal_id: str = Field(alias="proposalId")
    symbol: str
    created_at: str = Field(alias="createdAt")
    sim_day: int = Field(alias="simDay")
    original_recommendation: AnalystChoice = Field(alias="originalRecommendation")
    recommendation_source: Literal["executive_network"] = Field(default="executive_network", alias="recommendationSource")
    ceo_decision: AnalystChoice = Field(alias="ceoDecision")
    override_reason: str | None = Field(default=None, alias="overrideReason")
    # `None` when no ExecutiveMeetingLogEntry exists for this proposal
    # (an honest NOT_ENOUGH_EVIDENCE gap, never a fabricated confidence).
    original_confidence_pct: float | None = Field(default=None, alias="originalConfidencePct")
    original_decision_grade: DecisionGrade | None = Field(default=None, alias="originalDecisionGrade")
    original_decision_grade_score: float | None = Field(default=None, alias="originalDecisionGradeScore")
    risk_department_stance: ExecutiveStance | None = Field(default=None, alias="riskDepartmentStance")
    department_agreement_pct: float | None = Field(default=None, alias="departmentAgreementPct")
    # The real departments whose own `agree` stance was the one this
    # override went against — feeds CeoOverrideGovernanceSummary's
    # `departmentOverrideImpact` aggregate; never a full opinions dump.
    agreeing_departments: list[ExecutiveDepartmentRole] = Field(default_factory=list, alias="agreeingDepartments")
    evidence_at_decision_time: list[str] = Field(default_factory=list, alias="evidenceAtDecisionTime")
    process_quality: OverrideProcessQuality = Field(alias="processQuality")
    # Mirrors CeoDecisionRecord.outcome verbatim — never re-derived, and
    # refreshed every tick alongside it so this stays in sync when a
    # "pending" override's trade eventually closes.
    outcome: Literal["pending", "correct", "incorrect", "undecidable"]
    reviewer: AgentId | None = Field(default=None)
    review_note: str | None = Field(default=None, alias="reviewNote")
    reviewed_at: str | None = Field(default=None, alias="reviewedAt")
    updated_at: str = Field(alias="updatedAt")


class CeoOverrideGovernanceSummary(CamelModel):
    """The one real, disclosed aggregate over the override backlog.
    `overrideRatePct` is `None` (NOT_ENOUGH_EVIDENCE) when there are no
    real decisions to divide by, never a fabricated 0%. Department
    override-impact counts are real: for each real department role, how
    many times that department's own real `agree` stance on a proposal's
    recommended action was the one the CEO ultimately overrode —
    computed from real `ExecutiveMeetingLogEntry.opinions`, never
    invented."""

    total_override_count: int = Field(alias="totalOverrideCount")
    total_decision_count: int = Field(alias="totalDecisionCount")
    override_rate_pct: float | None = Field(default=None, alias="overrideRatePct")
    justified_count: int = Field(alias="justifiedCount")
    unjustified_count: int = Field(alias="unjustifiedCount")
    mixed_count: int = Field(alias="mixedCount")
    not_enough_evidence_count: int = Field(alias="notEnoughEvidenceCount")
    outcome_correct_count: int = Field(alias="outcomeCorrectCount")
    outcome_incorrect_count: int = Field(alias="outcomeIncorrectCount")
    outcome_pending_count: int = Field(alias="outcomePendingCount")
    outcome_undecidable_count: int = Field(alias="outcomeUndecidableCount")
    department_override_impact: dict[str, int] = Field(default_factory=dict, alias="departmentOverrideImpact")
    sample_size_sufficient: bool = Field(alias="sampleSizeSufficient")
    updated_at: str = Field(alias="updatedAt")


# CEO directive "Features 31-35," Feature 34 — Compliance Control
# Effectiveness (app/control_effectiveness.py). RESEARCH FINDING: every
# one of app/gatekeeper.py's 11 real checks already runs, unconditionally,
# on every real trade decision and is stored, per-decision, on
# `TradeDecision.gatekeeper_verdict.checks` — so `triggeredCount` here is
# never a fabricated "how often could this fire" estimate, it is a real
# count of every time this exact control actually ran. Distinguishing
# CONTROL EXISTS from CONTROL WORKS needs real proof a rejection was
# right or wrong; the only honest source for that is the already-real
# `GatekeeperRejection.outcome` grading (would_have_won/would_have_lost,
# resolved from real watchlist price movement — see
# grade_gatekeeper_rejections()). A rejection can fail more than one
# check at once (`approved = all(c.passed for c in checks)`), so an
# outcome can only be attributed to ONE specific control when that
# control was the SOLE failing check for that decision — every other
# case is counted as `ambiguousAttributionCount`, never guessed at.
GatekeeperControlEffectivenessState = Literal["effective", "ineffective", "mixed", "insufficient_data", "not_yet_tested"]


class ControlEffectivenessRecord(CamelModel):
    """One real Gatekeeper check's effectiveness record. `purpose` and
    `owner` are the check's own real, disclosed docstring/module —
    describing what the control already does, never inventing new
    behavior. `effectivenessState` is `not_yet_tested` when the control
    has never once failed a decision (CONTROL EXISTS, never yet had a
    chance to prove CONTROL WORKS — NO TRIGGERS is not FAILURE),
    `insufficient_data` when it has failed decisions but too few have a
    confirmed (non-pending, sole-reason) outcome yet to support any
    verdict, `mixed` when there IS enough confirmed evidence but the
    prevented-vs-false-positive split lands in the ambiguous middle band
    (real evidence that just doesn't clearly say "works" or "doesn't" —
    never collapsed into insufficient_data, which would misreport real
    mixed evidence as no evidence), and only `effective`/`ineffective`
    once `MIN_CONTROL_SAMPLE_FOR_VERDICT` confirmed, unambiguous outcomes
    exist and clearly clear one side of the threshold — the same
    evidence-floor pattern Feature 33's `MIN_ACCURACY_SAMPLE_FOR_VERDICT`
    already established. `controlRegression` is true only when an earlier half
    of this control's own confirmed history read `effective` and the
    more recent half now reads `ineffective` — a real, computed
    before/after split, never a hardcoded flag."""

    control_id: str = Field(alias="controlId")
    control_label: str = Field(alias="controlLabel")
    purpose: str
    owner: str
    triggered_count: int = Field(alias="triggeredCount")
    passed_count: int = Field(alias="passedCount")
    failed_count: int = Field(alias="failedCount")
    sole_reason_rejection_count: int = Field(alias="soleReasonRejectionCount")
    confirmed_prevented_count: int = Field(alias="confirmedPreventedCount")
    confirmed_false_positive_count: int = Field(alias="confirmedFalsePositiveCount")
    pending_evaluation_count: int = Field(alias="pendingEvaluationCount")
    ambiguous_attribution_count: int = Field(alias="ambiguousAttributionCount")
    effectiveness_state: GatekeeperControlEffectivenessState = Field(alias="effectivenessState")
    control_regression: bool = Field(default=False, alias="controlRegression")
    last_triggered_at: str | None = Field(default=None, alias="lastTriggeredAt")
    last_evaluated_at: str | None = Field(default=None, alias="lastEvaluatedAt")


class ControlEffectivenessSummary(CamelModel):
    """The Control Effectiveness Dashboard's real aggregate — a pure
    count over `controls`, never a second independently-computed
    number."""

    controls: list[ControlEffectivenessRecord]
    total_controls: int = Field(alias="totalControls")
    effective_count: int = Field(alias="effectiveCount")
    ineffective_count: int = Field(alias="ineffectiveCount")
    mixed_count: int = Field(alias="mixedCount")
    insufficient_data_count: int = Field(alias="insufficientDataCount")
    not_yet_tested_count: int = Field(alias="notYetTestedCount")
    regressed_control_count: int = Field(alias="regressedControlCount")
    updated_at: str = Field(alias="updatedAt")


# CEO directive "Features 31-35," Feature 35 — the Continuous Compliance
# Improvement Loop (app/continuous_improvement.py). Closes the loop:
# INCIDENT (Feature 31) -> ROOT CAUSE (real, CEO-recorded on
# `verify_and_resolve()`) -> REMEDIATION (the real `correctiveAction`
# text) -> MONITORING (a real, disclosed sim-day observation window) ->
# OUTCOME (did the same incident reopen, or the same root cause recur
# elsewhere) -> EFFECTIVENESS REVIEW (below) -> COMPANY HEALTH (a new
# real `complianceHealth` sub-score, Chapter 63's existing architecture
# — see app/company_health.py). Read-only, computed fresh per request
# over already-persisted `state.compliance_incidents` — no new
# GameSaveState field, the same original CAGS convention as Feature 34.
RemediationEffectivenessState = Literal["effective", "partially_effective", "ineffective", "not_enough_evidence"]


class RemediationEffectivenessRecord(CamelModel):
    """One real, ever-resolved `ComplianceIncident`'s remediation
    outcome. `reopenedCount > 0` is the strongest, most direct evidence a
    fix failed — a CEO explicitly reopened that exact case — and always
    reads `ineffective` regardless of the observation window below.
    Short of that, `recurrenceCount` counts OTHER real incidents sharing
    this one's exact (`rootCause`, `category`, `department`) signature
    that opened *after* this incident's own `resolutionSimDay` — the
    same underlying problem class showing up again elsewhere, even
    though this specific case never reopened, reads `partially_effective`
    rather than a flat `effective`. `not_enough_evidence` applies before
    `REMEDIATION_EVAL_WINDOW_SIM_DAYS` of real simulated time has passed
    since resolution — too soon to honestly claim a fix "held," the same
    NO-TRIGGERS-≠-FAILURE discipline Feature 34 already established for
    controls."""

    incident_id: str = Field(alias="incidentId")
    root_cause: IncidentRootCause = Field(alias="rootCause")
    corrective_action: str = Field(alias="correctiveAction")
    category: AuditEventCategory
    department: str
    resolved_at: str = Field(alias="resolvedAt")
    resolution_sim_day: int = Field(alias="resolutionSimDay")
    reopened_count: int = Field(alias="reopenedCount")
    recurrence_count: int = Field(alias="recurrenceCount")
    effectiveness_state: RemediationEffectivenessState = Field(alias="effectivenessState")


class RootCauseRecurrence(CamelModel):
    """Per-`rootCause` (not narrowed by category/department — the
    directive's own literal "same root cause repeatedly produces
    incidents" wording), a real count of every distinct incident this
    root cause has ever been recorded on, coarser and broader than
    `RemediationEffectivenessRecord.recurrenceCount`'s tighter
    same-signature match, and disclosed as such — a genuine second,
    coarser lens on the same real data, not a second independently
    invented number. `recurringFailure` is `true` once
    `RECURRING_FAILURE_MIN_COUNT` (= 2 — "recurring" honestly means
    "happened more than once," a structural count, not a statistical
    rate, so this floor is deliberately lower than the rate-verdict
    floors Features 33/34 use) real incidents share it."""

    root_cause: IncidentRootCause = Field(alias="rootCause")
    incident_count: int = Field(alias="incidentCount")
    recurring_failure: bool = Field(alias="recurringFailure")
    first_occurred_at: str = Field(alias="firstOccurredAt")
    last_occurred_at: str = Field(alias="lastOccurredAt")
    incident_ids: list[str] = Field(default_factory=list, alias="incidentIds")


class ContinuousImprovementSummary(CamelModel):
    """The Continuous Improvement loop's real aggregate — every count
    here is a direct tally over `remediations`/`rootCauseRecurrences`,
    never a second, independently-blended number."""

    remediations: list[RemediationEffectivenessRecord]
    root_cause_recurrences: list[RootCauseRecurrence] = Field(alias="rootCauseRecurrences")
    effective_count: int = Field(alias="effectiveCount")
    partially_effective_count: int = Field(alias="partiallyEffectiveCount")
    ineffective_count: int = Field(alias="ineffectiveCount")
    not_enough_evidence_count: int = Field(alias="notEnoughEvidenceCount")
    recurring_failure_count: int = Field(alias="recurringFailureCount")
    updated_at: str = Field(alias="updatedAt")


# Design Bible Chapter 75 — Company Trading Modes & Institutional Capital
# Protection (app/trading_modes.py). "day_trading"/"swing_trading"/
# "hybrid" are the CEO's real operating policy; TradingStyle is the
# per-trade tag that policy assigns (see TradingModeState.mode's own
# docstring for exactly how). Neither existed anywhere in this codebase
# before this chapter — confirmed by direct grep before writing it.
TradingMode = Literal["day_trading", "swing_trading", "hybrid"]
TradingStyle = Literal["day", "swing"]


class TradingModeState(CamelModel):
    """The CEO's real Trading Mode selection and every real, disclosed
    threshold this chapter's Circuit Breaker / Losing Streak Protection
    checks against. `rotation_counter` and `losing_streak_acknowledged`
    are internal bookkeeping (the hybrid tag rotation's own running
    counter, and whether the CEO already silenced the *current* losing
    streak) — real persisted state, not CEO-facing controls themselves."""

    mode: TradingMode = "swing_trading"
    hybrid_day_allocation_pct: float = Field(default=50.0, alias="hybridDayAllocationPct")
    changed_at: str = Field(alias="changedAt")
    previous_mode: TradingMode | None = Field(default=None, alias="previousMode")
    change_reason: str = Field(default="Default at company founding.", alias="changeReason")
    rotation_counter: int = Field(default=0, alias="rotationCounter")
    adaptive_recommendations_enabled: bool = Field(default=True, alias="adaptiveRecommendationsEnabled")
    # Daily Circuit Breaker thresholds — Tier 4 is deliberately NOT a
    # field here; it reuses RiskLimits.max_daily_loss_pct verbatim (see
    # this chapter's own Decision Logic) rather than a confusing second
    # daily-loss number.
    tier1_pct: float = Field(default=1.0, alias="tier1Pct")
    tier2_pct: float = Field(default=2.0, alias="tier2Pct")
    tier3_pct: float = Field(default=3.0, alias="tier3Pct")
    losing_streak_pause_count: int = Field(default=3, alias="losingStreakPauseCount")
    losing_streak_suspend_count: int = Field(default=5, alias="losingStreakSuspendCount")
    losing_streak_acknowledged: bool = Field(default=False, alias="losingStreakAcknowledged")
    # Behavioral Circuit Breaker (app/behavioral_risk.py) — the CEO's own
    # real, editable thresholds for the revenge-trading detector's timing
    # and self-relative sizing signals. Set via
    # POST /api/trading-modes/behavioral-circuit-breaker/thresholds.
    behavioral_cooldown_minutes: int = Field(default=60, alias="behavioralCooldownMinutes")
    behavioral_size_increase_threshold_pct: float = Field(default=50.0, alias="behavioralSizeIncreaseThresholdPct")


DailyCircuitBreakerTier = Literal["none", "tier1", "tier2", "tier3", "tier4"]


class DailyCircuitBreakerRead(CamelModel):
    """Computed fresh every tick from the same real daily P&L%
    `evaluate_sentinel_risk()` already tracks — never persisted as a
    second, driftable copy (the same convention `DailyObjectiveStatus`
    already established)."""

    tier: DailyCircuitBreakerTier
    daily_pnl_pct: float = Field(alias="dailyPnlPct")
    tier1_pct: float = Field(alias="tier1Pct")
    tier2_pct: float = Field(alias="tier2Pct")
    tier3_pct: float = Field(alias="tier3Pct")
    tier4_pct: float = Field(alias="tier4Pct")
    updated_at: str = Field(alias="updatedAt")


class LosingStreakRead(CamelModel):
    """Computed fresh every tick by walking `trade_history` backward from
    the most recent closed trade — never persisted as a second copy."""

    consecutive_losses: int = Field(alias="consecutiveLosses")
    pause_active: bool = Field(alias="pauseActive")
    pause_threshold: int = Field(alias="pauseThreshold")
    suspend_threshold: int = Field(alias="suspendThreshold")


# Behavioral Circuit Breaker — the revenge-trading detector
# (app/behavioral_risk.py), the tenth real Gatekeeper check
# (app/gatekeeper.py::_behavioral_check). `warning` is informational only
# and never blocks; only `triggered` fails the Gatekeeper check for the
# specific proposal being resolved. Ambient (no-candidate) reads can
# never reach `triggered` — see app/behavioral_risk.py's module
# docstring for why.
BehavioralCircuitBreakerStatus = Literal["clear", "warning", "triggered"]


class BehavioralCircuitBreakerRead(CamelModel):
    """Real, disclosed evidence for a single behavioral-risk read — either
    the per-proposal Gatekeeper check (a real `candidate` proposal was
    evaluated) or the ambient tick-level dashboard read (no candidate).
    `sameInstrument`/`sizeIncreasePct` are None whenever no real candidate
    was evaluated, or no candidate-independent baseline/comparison was
    possible — never a fabricated value standing in for "not evaluated."

    `sameDirection` (Piece 8b) is informational only — like
    `repeatedRapidReentryCount`, it never independently corroborates a
    `"triggered"` verdict on its own (a candidate defaults to the same
    side as almost any prior trade far too often by chance for that to
    be real evidence of revenge trading; see app/behavioral_risk.py's
    module docstring for why). `previousWinSymbol`/`previousWinPnl`/
    `minutesSinceWin`/`winSizeIncreasePct` (also Piece 8b) are the
    win-triggered-escalation read — populated only when the most recent
    closed trade was a real win, mutually exclusive with the
    `previousLoss*`/`sameInstrument`/`sizeIncreasePct` fields above,
    which populate only when it was a real loss.
    """

    status: BehavioralCircuitBreakerStatus
    reasons: list[str] = Field(default_factory=list)
    previous_loss_symbol: str | None = Field(default=None, alias="previousLossSymbol")
    previous_loss_pnl: float | None = Field(default=None, alias="previousLossPnl")
    minutes_since_loss: int | None = Field(default=None, alias="minutesSinceLoss")
    cooldown_minutes: int = Field(alias="cooldownMinutes")
    same_instrument: bool | None = Field(default=None, alias="sameInstrument")
    same_direction: bool | None = Field(default=None, alias="sameDirection")
    size_increase_pct: float | None = Field(default=None, alias="sizeIncreasePct")
    consecutive_losses: int = Field(alias="consecutiveLosses")
    # Prop-Firm Risk Intelligence Addendum, Piece 11b — Requirement 24's
    # "consecutive wins" data point, an exact mirror of consecutive_losses
    # above (app/trading_modes.py's compute_consecutive_wins()).
    consecutive_wins: int = Field(default=0, alias="consecutiveWins")
    repeated_rapid_reentry_count: int = Field(alias="repeatedRapidReentryCount")
    previous_win_symbol: str | None = Field(default=None, alias="previousWinSymbol")
    previous_win_pnl: float | None = Field(default=None, alias="previousWinPnl")
    minutes_since_win: int | None = Field(default=None, alias="minutesSinceWin")
    win_size_increase_pct: float | None = Field(default=None, alias="winSizeIncreasePct")
    computed_at: str = Field(alias="computedAt")


class AdaptiveModeRecommendation(CamelModel):
    """Read-only, exactly like Chapter 65's own `posture` field — never
    applied to `TradingModeState` automatically. `recommendedMode` is
    None when no real signal is strong enough to recommend a change, or
    when the real regime read calls for Chapter 72's Defensive Mode
    instead of a trading-style pick (see `note`)."""

    recommended_mode: TradingMode | None = Field(default=None, alias="recommendedMode")
    reasoning: str
    confidence_pct: float = Field(alias="confidencePct")
    note: str | None = None
    generated_at: str = Field(alias="generatedAt")


class TradingStylePerformance(CamelModel):
    """A real win-rate/P&L split over `PaperPortfolio.trade_history`,
    grouped by the `tradingStyle` tag this chapter assigns at proposal
    time. Never claims independent capital pools — see this chapter's
    own Ownership section for why that's explicitly out of scope."""

    style: TradingStyle
    trade_count: int = Field(alias="tradeCount")
    win_rate: float = Field(alias="winRate")
    total_pnl: float = Field(alias="totalPnl")
    avg_pnl_pct: float = Field(alias="avgPnlPct")


class TradingModeHealthAssessment(CamelModel):
    """Mirrors `StrategyHealthAssessment`'s own real 7-value
    `StrategyHealthStatus` vocabulary and threshold shape (see
    app/strategy_lab.py's `compute_strategy_health()`), computed over a
    trading style's own real `PaperTrade` history instead of a backtested
    Strategy's `SimulationResult` history — the same real formula,
    genuinely adapted to a different real input, never a second,
    differently-worded scale."""

    style: TradingStyle
    status: StrategyHealthStatus
    trend: StrategyHealthTrend
    recent_win_rate: float = Field(alias="recentWinRate")
    lifetime_win_rate: float = Field(alias="lifetimeWinRate")
    recent_avg_return_pct: float = Field(alias="recentAvgReturnPct")
    lifetime_avg_return_pct: float = Field(alias="lifetimeAvgReturnPct")
    recent_sample_size: int = Field(alias="recentSampleSize")
    lifetime_sample_size: int = Field(alias="lifetimeSampleSize")
    reasoning: list[str] = Field(default_factory=list)


class RecoveryBriefing(CamelModel):
    """Generated only when Emergency Stop activates *because of* this
    chapter's own Tier 4 Circuit Breaker or a losing-streak suspension —
    never for a CEO-manual stop, which already has its own real reason.
    Modeled on Chapter 72's `generate_crisis_briefing()` pattern: real
    recent stats, real links to Discipline Chamber reviews, never a
    regenerated copy of their content."""

    id: str
    trigger: Literal["circuit_breaker_tier4", "losing_streak"]
    summary: str
    recent_win_rate: float = Field(alias="recentWinRate")
    recent_avg_loss_pct: float = Field(alias="recentAvgLossPct")
    largest_loss_pct: float = Field(alias="largestLossPct")
    days_since_last_profitable_day: int | None = Field(default=None, alias="daysSinceLastProfitableDay")
    linked_discipline_review_ids: list[str] = Field(default_factory=list, alias="linkedDisciplineReviewIds")
    created_at: str = Field(alias="createdAt")


# Design Bible Chapter 73.5 — Mobile Command Center & Remote Operations
# (app/situation_room.py, app/travel_mode.py). See that chapter's own
# honesty boundary: this codebase has no accounts, push-notification,
# biometric, voice, wearable, or geolocation infrastructure — what's
# real is a single-screen aggregate over already-real state (eleven of
# its thirteen fields reused verbatim from an existing single computed
# source), a formalized four-tier priority ranking extending Chapter
# 67's existing three toast tiers, and a CEO-configurable Travel Mode
# posture that composes through the same derived-override seam Company
# Priority and Chapter 75's Daily Circuit Breaker already share.
SituationRoomSeverity = Literal["good", "caution", "elevated", "severe", "critical"]


class SituationRoomField(CamelModel):
    """One of the Situation Room's thirteen real fields — `value` is
    always a pre-formatted display string built from a real number or
    real enum already computed elsewhere, `band` is this chapter's own
    disclosed severity-band mapping (see app/situation_room.py's module
    docstring for the complete per-field threshold table), never a
    fabricated score."""

    label: str
    value: str
    band: SituationRoomSeverity
    detail: str


PriorityTier = Literal["critical", "high", "medium", "low"]


class PriorityItem(CamelModel):
    """One real, actionable item the CEO Priority Engine surfaced —
    `source` names the real backend signal it came from (never a
    synthetic "notification" with no underlying record) and `relatedId`
    links back to that record the same way `AuditEntry.relatedId`
    already does."""

    id: str
    tier: PriorityTier
    title: str
    detail: str
    source: str
    related_id: str | None = Field(default=None, alias="relatedId")


class SituationRoomState(CamelModel):
    """Computed fresh every request from state this game already
    persists — never a second, independently-tracked copy of Company
    Health, Portfolio Health, Market Regime, etc. The same "cheap,
    always current" convention Chapter 73's Compliance Overview already
    established for a cross-cutting aggregate."""

    company_health: SituationRoomField = Field(alias="companyHealth")
    portfolio_health: SituationRoomField = Field(alias="portfolioHealth")
    cash_position: SituationRoomField = Field(alias="cashPosition")
    open_risk: SituationRoomField = Field(alias="openRisk")
    market_regime: SituationRoomField = Field(alias="marketRegime")
    trading_mode: SituationRoomField = Field(alias="tradingMode")
    economic_health: SituationRoomField = Field(alias="economicHealth")
    black_swan_risk: SituationRoomField = Field(alias="blackSwanRisk")
    executive_consensus: SituationRoomField = Field(alias="executiveConsensus")
    pending_ceo_decisions: SituationRoomField = Field(alias="pendingCeoDecisions")
    broker_status: SituationRoomField = Field(alias="brokerStatus")
    automation_status: SituationRoomField = Field(alias="automationStatus")
    emergency_alerts: SituationRoomField = Field(alias="emergencyAlerts")
    priorities: list[PriorityItem] = Field(default_factory=list)
    generated_at: str = Field(alias="generatedAt")


TravelModeActivationSource = Literal["manual", "auto_inactivity"]
NotificationSensitivity = Literal["all", "high_and_above", "critical_only"]


class TravelModeSettings(CamelModel):
    """The CEO's own configuration, within a disclosed floor/ceiling —
    see this chapter's own Decision Logic for why these particular
    bounds (25%-75% of the account's normal limits, matching the
    conservative-but-arbitrary honesty note RiskLimits itself already
    carries)."""

    position_size_cap_pct: float = Field(default=50.0, alias="positionSizeCapPct")
    daily_risk_cap_pct: float = Field(default=50.0, alias="dailyRiskCapPct")
    notification_sensitivity: NotificationSensitivity = Field(default="high_and_above", alias="notificationSensitivity")
    auto_activate_enabled: bool = Field(default=False, alias="autoActivateEnabled")
    auto_activate_after_minutes: int = Field(default=120, alias="autoActivateAfterMinutes")


class TravelModeState(CamelModel):
    """Persisted CEO posture. `active` gates
    app/travel_mode.py::apply_travel_mode_tightening() inside
    app/nexus.py's _effective_risk_limits() — a derived override,
    exactly like Chapter 75's Circuit Breaker, never a mutation of the
    CEO's own persisted RiskLimits (contrast with Chapter 72's
    Defensive Mode, which does mutate-and-restore via `priorRiskLimits`
    — Travel Mode deliberately reuses the derived-override pattern
    instead, since `TravelModeState` itself is already real, persisted,
    CEO-owned state; a second RiskLimits snapshot underneath it would
    be a redundant, driftable copy — see the chapter's own Decision
    Logic for the full comparison of this codebase's exactly three
    tightening patterns)."""

    active: bool = False
    settings: TravelModeSettings = Field(default_factory=TravelModeSettings)
    activated_at: str | None = Field(default=None, alias="activatedAt")
    activation_source: TravelModeActivationSource | None = Field(default=None, alias="activationSource")
    deactivated_at: str | None = Field(default=None, alias="deactivatedAt")
    # Simulated-clock minutes-since-epoch, the same convention
    # PaperTrade.closed_sim_minutes/GatekeeperRejection.rejected_sim_minutes
    # already use — lets the Return-to-Operations briefing window its
    # real record search against TradeTown's in-game calendar rather
    # than real wall-clock time.
    activated_sim_minutes: int = Field(default=0, alias="activatedSimMinutes")
    # Internal bookkeeping (not a CEO-facing control) — bumped by
    # app/state.py whenever the CEO takes any real action on a pending
    # TradeProposal (decide/hold/modify). The one real, measurable
    # "how long has the CEO actually gone without touching a decision"
    # signal should_auto_activate() checks — never a calendar or
    # clock-time-of-day read, neither of which this codebase has.
    last_ceo_decision_sim_minutes: int = Field(default=0, alias="lastCeoDecisionSimMinutes")


class TravelModeBriefing(CamelModel):
    """The real Return-to-Full-Operations briefing, built from real
    records in the exact activation window — never a templated recap.
    Modeled directly on Chapter 72's Defensive Mode deactivation (its
    own real Post-Event Analysis) pattern."""

    id: str
    activated_at: str = Field(alias="activatedAt")
    deactivated_at: str = Field(alias="deactivatedAt")
    activation_source: TravelModeActivationSource = Field(alias="activationSource")
    decisions_resolved: int = Field(alias="decisionsResolved")
    gatekeeper_rejections: int = Field(alias="gatekeeperRejections")
    critical_risk_warnings: int = Field(alias="criticalRiskWarnings")
    circuit_breaker_tier_changes: int = Field(alias="circuitBreakerTierChanges")
    realized_pnl: float = Field(alias="realizedPnl")
    summary: str
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
    what_we_do_not_know: list[str] = Field(
        default_factory=list, alias="whatWeDoNotKnow"
    )
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
    important_questions: list[str] = Field(
        default_factory=list, alias="importantQuestions"
    )
    recommended_future_projects: list[str] = Field(
        default_factory=list, alias="recommendedFutureProjects"
    )
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
WisdomTier = Literal[
    "young_company",
    "developing_judgment",
    "institutional_memory",
    "seasoned_wisdom",
    "enduring_wisdom",
]


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


# CEO directive "Features 26-30," Feature 27 — Agent Performance Reviews.
# See app/performance_review.py's module docstring for the full research
# finding and design rationale. `AgentRoleClass` is this codebase's first
# machine-usable role taxonomy over AGENT_PROFILES (previously only
# free-text `occupation` strings existed) — used to interpret a missing
# dimension correctly (e.g. Sentinel having no decisionAccuracy data is
# expected, not a red flag) rather than to force every dimension to a
# number regardless of role.
AgentRoleClass = Literal["researcher", "risk", "quant", "leadership", "mentor_support"]

# CEO directive "Command Center + Professional Quant Trading Firm
# Upgrade" — Phase 2, AI Desk / Agent Decision Explainability. Every
# value here is grounded in a real, already-existing signal (see
# app/agent_trading_status.py's own module docstring for exactly which
# one, and the honest priority order used when more than one could
# apply): `waiting` — a real AnalystVote this agent cast is sitting on
# a currently pending TradeProposal. `scanning` — a real ResearchItem
# assigned to this agent (app/research.py's RESEARCHER_IDS) is queued
# or in progress. `idle` — this agent's real role IS trading-relevant
# (a researcher, or one of the six agents app/executive.py's vote
# generation can ever attribute a vote to) but nothing real is active
# right now. `risk_blocked` — Emergency Stop is currently active,
# company-wide, for every agent. `not_trading_role` — this agent's
# real function (see AGENT_PROFILES' own occupation string) never
# generates a live vote or research assignment in this codebase —
# stated as the honest truth about the role, never as a fabricated
# "waiting for a setup" narrative it has no real basis for.
AgentTradingStatus = Literal["waiting", "scanning", "idle", "risk_blocked", "not_trading_role"]


class AgentTradingStatusRead(CamelModel):
    """One agent's real, current trading-relevant state, computed fresh
    every call — never persisted, never a predicted "next condition"
    this codebase has no real mechanism to compute (see this
    directive's own worked example asking for one — `detail` below
    surfaces the real existing narrative text a "wait" vote or research
    summary already carries instead, which is the honest substitute)."""

    agent_id: AgentId = Field(alias="agentId")
    role_class: AgentRoleClass = Field(alias="roleClass")
    status: AgentTradingStatus
    headline: str
    detail: str
    symbol: str | None = None
    research_category: ResearchCategory | None = Field(default=None, alias="researchCategory")
    proposal_id: str | None = Field(default=None, alias="proposalId")
    session: SessionRead
    updated_at: str = Field(alias="updatedAt")


# Every dimension this codebase can honestly back today with real,
# already-computed or trivially-derived evidence. Deliberately excludes
# the CEO's "prediction accuracy"/"contribution to success or failure via
# debate" as SEPARATE dimensions beyond decision_accuracy/process_quality
# — those become real once Features 29 (Prediction Tracking) and 30
# (Debate + Failure Review) exist to honestly feed them; this is a
# disclosed staging decision, matching Feature 26's own.
PerformanceDimensionId = Literal[
    "process_quality",
    "risk_discipline",
    "decision_accuracy",
    "calibration",
    "collaboration",
    "learning_trend",
    "recurring_mistakes",
    "pnl_attribution",
]


class PerformanceDimension(CamelModel):
    """`value=None` means NOT_ENOUGH_EVIDENCE for this one dimension —
    never a fake neutral number. `sample_size` is always disclosed
    alongside `value` so a caller never has to guess how much evidence
    backs it (the same discipline app/process_adherence.py's
    ProcessAdherenceRead already established for its own nullable
    score_pct)."""

    id: PerformanceDimensionId
    label: str
    value: float | None
    sample_size: int = Field(alias="sampleSize")
    evidence: str


class AgentPerformanceReview(CamelModel):
    """One real, evidence-cited review of one agent over one real
    period — never a single blended "agent score." `process_quality_avg`/
    `outcome_quality_avg` are kept structurally separate (a good process
    that lost to real market variance never drags down process_quality;
    a lucky win from a weak process never inflates it), mirroring
    app/discipline.py's own process-score-never-sees-pnl discipline.
    Both are `None` when none of their contributing dimensions has real
    data yet — never averaged from a partial fake baseline. `role_class`
    lets a reader correctly interpret which dimensions are expected to
    be `None` for this agent's real role (e.g. Sentinel structurally
    never gets research assignments, so decisionAccuracy is honestly
    always NOT_ENOUGH_EVIDENCE for it — that's not a gap in the review,
    it's the truth about the role)."""

    id: str
    agent_id: AgentId = Field(alias="agentId")
    role_class: AgentRoleClass = Field(alias="roleClass")
    period_start_sim_day: int = Field(alias="periodStartSimDay")
    period_end_sim_day: int = Field(alias="periodEndSimDay")
    dimensions: list[PerformanceDimension]
    process_quality_avg: float | None = Field(default=None, alias="processQualityAvg")
    outcome_quality_avg: float | None = Field(default=None, alias="outcomeQualityAvg")
    # Sum of every dimension's own real sample_size — the review's total
    # real evidentiary weight, disclosed rather than hidden inside an
    # opaque composite.
    evidence_count: int = Field(alias="evidenceCount")
    # What share of the 8 real dimensions above actually had evidence
    # this period — a real coverage percentage, not a claim about how
    # GOOD the agent is.
    confidence_pct: float = Field(alias="confidencePct")
    trend: Literal["improving", "declining", "stable", "not_enough_history"]
    # The lowest-scoring measured dimension this period — the real hook
    # Feature 28 (Academy training recommendations) will read from once
    # it exists; None when no dimension has real data at all.
    weakest_dimension_id: PerformanceDimensionId | None = Field(default=None, alias="weakestDimensionId")
    status: Literal["evaluated", "not_enough_evidence"]
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


# CEO directive "Professional Quant Firm Phase 41-45," Feature 44 —
# Agent Learning must not cause data leakage. See
# app/performance_review.py's classify_review_data_splits() for the
# real, chronological, non-shuffled rule that assigns this — an
# evidence-MATURITY label (how many later, non-overlapping periods have
# since elapsed without this review being re-used), never a quality
# judgment. `live_paper` is this agent's single freshest review — an
# unconfirmed, still-fresh observation. `test` is the review
# immediately superseded by it — the first genuinely held-out period.
# `validation`/`training` are progressively older, more-corroborated
# evidence. This labeling is deliberately preventive, not a retrofit:
# nothing in this codebase today feeds AgentPerformanceReview back into
# any live weighting or promotion decision (verified — see that
# module's own docstring), so there is no existing leak to fix. It
# exists so a future evidence-based agent promotion/demotion system
# (this same directive family's own explicit ask) has a real,
# non-fabricated way to require review evidence to have aged past the
# freshest live_paper window before citing it as proof of durable
# improvement.
AgentReviewDataSplit = Literal["training", "validation", "test", "live_paper"]


class AgentPerformanceReviewHistoryEntry(CamelModel):
    """One stored `AgentPerformanceReview` paired with its current, freshly
    computed `AgentReviewDataSplit` — never stored on the review itself,
    since the classification is relative to how many later reviews now
    exist and must re-derive as new reviews accumulate (see
    classify_review_data_splits())."""

    review: AgentPerformanceReview
    data_split: AgentReviewDataSplit = Field(alias="dataSplit")


class MentorState(CamelModel):
    tier: int
    tier_label: str = Field(alias="tierLabel")
    questions_asked: int = Field(alias="questionsAsked")
    updated_at: str = Field(alias="updatedAt")


# v0.7 Feature 49 (Phase 3, revised) — the Foundational Mentor Program /
# Professional Academy (app/foundational_mentors.py). Real, named
# trading educators are used only as CEO-assigned track labels on a
# roadmap; every lesson's actual content is original TradeTown-authored
# material, never a claimed transcription of that person's real work
# (see the module docstring for the full attribution boundary).
# Distinct from the pre-existing MentorState/Sage mentor above — that's
# a single always-available Q&A advisor, this is a sequential
# lesson-and-quiz curriculum. As of the Phase 3 revision, the real
# STUDENTS are the employee agents (auto-progressing every tick), not
# the CEO — see foundational_mentors.py's module docstring for the full
# "employees are the students" redesign rationale. The CEO may still
# optionally take the same lessons personally via `ceo_progress` when
# Settings.ceoAcademyLearningMode is on, entirely separate from the real
# employee cohort's own progress.
#
# A plain `str`, not a `Literal`, as of the Mentor Lab revision: the CEO
# can now really add new mentor tracks in-product (see
# foundational_mentors.py's `add_custom_mentor`), so the set of valid
# ids is no longer fixed at code-authoring time. The original 6 named
# ids (`"tjr"`, `"al_brooks"`, ...) still exist as real string values —
# nothing about their content or behavior changed, only the type.
FoundationalMentorId = str
FoundationalMentorStatus = Literal["planned", "active", "paused", "graduated"]
FoundationalResourceType = Literal["video", "book", "article", "pdf", "note"]
# "pending_approval" is the real Graduation Queue gate: lessons+quiz are
# complete (a real, checkable signal) but the CEO hasn't clicked Approve
# yet — see foundational_mentors.py's approve_graduation().
FoundationalGraduationStatus = Literal["in_progress", "pending_approval", "graduated"]

# Certification Management (v0.7 quality-of-life fix). A permanent
# CertificationRecord's own real standing, independent of the raw
# lesson/quiz progress that earned it — see foundational_mentors.py's
# module docstring for the full lifecycle. "expired" is deliberately not
# included: it would need a real passage-of-time renewal/decay signal,
# which doesn't exist anywhere in this codebase yet — postponed to
# v1.0 (see docs/ROADMAP.md), not fabricated here.
CertificationStatus = Literal["active", "suspended", "revoked"]
CertificationHistoryAction = Literal[
    "earned", "suspended", "reinstated", "revoked", "progress_reset"
]


class FoundationalMentorLesson(CamelModel):
    """Public shape — deliberately has no answer key, mirroring
    EducationLesson's own public/hidden split for the same reason."""

    id: str
    order: int
    title: str
    simple_explanation: str = Field(alias="simpleExplanation")
    deeper_explanation: str = Field(alias="deeperExplanation")
    quiz_question: str = Field(alias="quizQuestion")
    quiz_options: list[str] = Field(alias="quizOptions")


class FoundationalMentorResource(CamelModel):
    """CEO-provided bookmark only — TradeTown never claims to have
    watched, read, parsed, or graded the linked material."""

    id: str
    title: str
    url: str | None = None
    resource_type: FoundationalResourceType = Field(alias="resourceType")
    added_at: str = Field(alias="addedAt")


class FoundationalMentorProfile(CamelModel):
    id: FoundationalMentorId
    name: str
    track_label: str = Field(alias="trackLabel")
    focus_areas: list[str] = Field(alias="focusAreas")
    content_note: str = Field(alias="contentNote")
    status: FoundationalMentorStatus
    lessons: list[FoundationalMentorLesson] = Field(default_factory=list)
    resources: list[FoundationalMentorResource] = Field(default_factory=list)
    # Company-wide graduation — set once every real student (see
    # STUDENT_AGENT_IDS) has an individually-approved graduation on this
    # track. None while the track is planned/active/paused.
    company_graduated_sim_day: int | None = Field(
        default=None, alias="companyGraduatedSimDay"
    )


class FoundationalMentorProgress(CamelModel):
    """One student's (an employee agent's, or the CEO's own optional
    Learning Mode progress) real progress on one mentor track."""

    mentor_id: FoundationalMentorId = Field(alias="mentorId")
    viewed_lesson_ids: list[str] = Field(default_factory=list, alias="viewedLessonIds")
    completed_lesson_ids: list[str] = Field(
        default_factory=list, alias="completedLessonIds"
    )
    # Real tick-accrued study progress (0-100) toward the current
    # in-flight (first not-yet-completed) lesson — the honest "how far
    # through this lesson" bar the Academy Dashboard shows per employee.
    current_lesson_study_pct: float = Field(default=0.0, alias="currentLessonStudyPct")
    quiz_attempts: int = Field(default=0, alias="quizAttempts")
    correct_quiz_attempts: int = Field(default=0, alias="correctQuizAttempts")
    # Resets to 0 on any correct answer — drives the Coach's real
    # "Repeat Lesson" / "One-on-One Coaching" recommendation escalation.
    consecutive_quiz_failures: int = Field(default=0, alias="consecutiveQuizFailures")
    graduation_status: FoundationalGraduationStatus = Field(
        default="in_progress", alias="graduationStatus"
    )
    graduated_sim_day: int | None = Field(default=None, alias="graduatedSimDay")
    # v0.7 Feature 50 addendum — "Revoke Graduation." Set by
    # revoke_certification() to a real, deterministic templated note
    # (never a fabricated free-form message); cleared automatically once
    # the employee re-graduates via approve_graduation().
    coach_note: str | None = Field(default=None, alias="coachNote")


class CertificationHistoryEntry(CamelModel):
    """One permanent, immutable audit line on a CertificationRecord —
    never edited or deleted, only ever appended to. `reason` is the
    CEO's own real typed text for a revoke/suspend action; None for
    "earned"/"reinstated"/"progress_reset", which don't require one."""

    id: str
    action: CertificationHistoryAction
    reason: str | None = None
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


class CertificationRecord(CamelModel):
    """A permanent record of one (agent, mentor track) certification's
    real lifecycle — earned, possibly suspended/reinstated, possibly
    revoked and re-earned, every transition kept in `history` forever.
    Independent of `FoundationalMentorProgress`, whose lesson/quiz
    counters do get reset by a revoke or a progress reset (see
    foundational_mentors.py's revoke_certification/
    reset_certification_progress) — this record is what survives that
    reset, so "View Certification History" always has a real answer."""

    id: str
    agent_id: AgentId = Field(alias="agentId")
    mentor_id: FoundationalMentorId = Field(alias="mentorId")
    mentor_name: str = Field(alias="mentorName")
    status: CertificationStatus
    updated_sim_day: int = Field(alias="updatedSimDay")
    history: list[CertificationHistoryEntry] = Field(default_factory=list)


# CEO directive "Features 26-30," Feature 28 — Academy + Skill
# Progression (the third stage of the 26->27->28->29->30 learning loop).
# See app/skill_progression.py's module docstring for the full research
# finding: this codebase already has a knowledge-points/tier system
# (app/academy.py) and a curriculum/certification delivery engine
# (app/foundational_mentors.py, immediately above), but no multi-domain,
# per-agent SKILL score anywhere. Each of the 11 domains named in the
# brief was checked individually against real, already-computed
# per-agent evidence; 6 of 11 have no real attribution mechanism today
# and are honestly NOT_TRACKABLE_YET rather than fabricated from an
# occupation label — see skill_progression.py's own per-domain evidence
# functions for exactly which is which and why.
SkillDomainId = Literal[
    "market_structure",
    "risk_management",
    "quant_research",
    "technical_fundamental_analysis",
    "execution",
    "statistical_reasoning",
    "regime_detection",
    "prediction_calibration",
    "communication",
    "collaboration",
    "research_quality",
]


class SkillAssessment(CamelModel):
    """One real, evidence-cited read of one agent's one skill domain for
    one real period. `value=None` means NOT_ENOUGH_EVIDENCE (a
    measurable domain with no real data yet this period) or
    NOT_TRACKABLE_YET (a domain with no attribution mechanism in this
    codebase at all) — `evidence` always states honestly which one and
    why, the same two-tier honesty shape as app/performance_review.py's
    PerformanceDimension. `trend` is this domain's own real
    improve/stagnate/regress read against the agent's previous real
    assessment of the same domain — never against a different domain or
    a fabricated baseline."""

    domain_id: SkillDomainId = Field(alias="domainId")
    label: str
    value: float | None
    sample_size: int = Field(alias="sampleSize")
    evidence: str
    trend: Literal["improving", "stagnant", "regressed", "not_enough_history"]


class AgentSkillProfile(CamelModel):
    """One real skill snapshot for one agent over one real period —
    mirrors AgentPerformanceReview's own per-period, evidence-cited
    shape. `recommended_domain_id`/`recommended_mentor_id` are the real
    closed-loop hook the CEO's own worked example asked for
    ("Performance Review flags a weak dimension -> Academy recommends
    training"): set only when the agent's latest
    AgentPerformanceReview.weakest_dimension_id maps to a skill domain
    this module can measure AND a real, content-backed Foundational
    Mentor track exists for it AND the agent hasn't already graduated
    that track — see skill_progression.py's
    SKILL_DOMAIN_RECOMMENDED_MENTOR for the exact, disclosed mapping.
    `None`/`None` with a stated reason when no real recommendation
    applies, never a forced default."""

    id: str
    agent_id: AgentId = Field(alias="agentId")
    period_start_sim_day: int = Field(alias="periodStartSimDay")
    period_end_sim_day: int = Field(alias="periodEndSimDay")
    assessments: list[SkillAssessment]
    recommended_domain_id: SkillDomainId | None = Field(default=None, alias="recommendedDomainId")
    recommended_mentor_id: FoundationalMentorId | None = Field(default=None, alias="recommendedMentorId")
    recommendation_reason: str | None = Field(default=None, alias="recommendationReason")
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


class FoundationalMentorState(CamelModel):
    mentors: list[FoundationalMentorProfile] = Field(default_factory=list)
    # Real per-employee progress — the actual students. Keyed by the
    # employee's own AgentId, then by mentor id (an employee keeps every
    # mentor's progress record permanently, including already-graduated
    # tracks).
    progress: dict[AgentId, dict[FoundationalMentorId, FoundationalMentorProgress]] = (
        Field(default_factory=dict)
    )
    # v0.7 Certification Management quality-of-life fix. The permanent
    # certification registry — one CertificationRecord per (agent,
    # mentor) pair that has ever been earned, surviving a revoke (unlike
    # `progress` above, which a revoke genuinely resets so the employee
    # can really repeat the track). This is the real, authoritative
    # source for "Current Certifications" (status active/suspended) and
    # "View Certification History" (the full permanent record) — see
    # foundational_mentors.py's Certification Management section.
    certifications: list[CertificationRecord] = Field(default_factory=list)
    # The CEO's own entirely separate, optional personal progress —
    # only reachable when Settings.ceoAcademyLearningMode is on. Same
    # shape as an employee's per-mentor progress dict, never mixed with
    # real employee records.
    ceo_progress: dict[FoundationalMentorId, FoundationalMentorProgress] = Field(
        default_factory=dict, alias="ceoProgress"
    )
    # Company-wide — "the Academy studies one mentor at a time" (every
    # employee works the same track; company_graduated_sim_day above
    # advances it once every student has an approved graduation).
    active_mentor_id: FoundationalMentorId | None = Field(
        default=None, alias="activeMentorId"
    )
    # The real sequential unlock order — persisted (not a hardcoded
    # module constant) specifically so the CEO can really append new
    # custom mentors to it via add_custom_mentor() and have them
    # eventually come up for company-wide study, same as the original 6.
    roadmap_order: list[FoundationalMentorId] = Field(
        default_factory=list, alias="roadmapOrder"
    )
    # Hidden answer keys for CEO-authored custom lessons (lesson id ->
    # correct option index) — the runtime equivalent of the built-in
    # curriculum's module-level `_LessonSpec.correct_index`, which can't
    # be used here since custom lesson content only exists at runtime.
    # `FoundationalMentorLesson`'s own public shape never carries this,
    # matching the built-in convention.
    custom_lesson_answers: dict[str, int] = Field(
        default_factory=dict, alias="customLessonAnswers"
    )
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
ConstitutionCitationSource = Literal[
    "case_study", "devils_advocate", "risk_department", "academy", "founders", "coach"
]


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
    redundant_with_article_id: str | None = Field(
        default=None, alias="redundantWithArticleId"
    )


class ConstitutionEmployeeVote(CamelModel):
    agent_id: AgentId = Field(alias="agentId")
    choice: Literal["support", "oppose", "abstain"]
    reason: str


class ConstitutionAmendment(CamelModel):
    id: str
    proposed_title: str = Field(alias="proposedTitle")
    proposed_text: str = Field(alias="proposedText")
    status: Literal["proposed", "debated", "evaluated", "voted", "approved", "rejected"]
    founder_verdicts: list[ConstitutionFounderVerdict] = Field(
        default_factory=list, alias="founderVerdicts"
    )
    coach_evaluation: str | None = Field(default=None, alias="coachEvaluation")
    employee_votes: list[ConstitutionEmployeeVote] = Field(
        default_factory=list, alias="employeeVotes"
    )
    ceo_decision: Literal["pending", "approved", "rejected"] = Field(
        default="pending", alias="ceoDecision"
    )
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
    independently-invented meeting transcript.

    CEO Company/Executive Health directive, Phase 4 — the three boolean
    flags below record whether each note actually references real
    company content that period (a real CoachReport strength/
    recommendation, a real Library-of-Mistakes case or Discipline
    Review, a real Reasoning Lab challenge or Reflection Chamber
    session) versus founders.py's own honest "nothing to review yet"
    fallback text. Default True — a save from before this field existed
    is not retroactively assumed to have been a placeholder-only
    session; see app/company_health.py's _founder_oversight()."""

    id: str
    sim_day: int = Field(alias="simDay")
    coach_highlight: str = Field(alias="coachHighlight")
    keystone_note: str = Field(alias="keystoneNote")
    compass_note: str = Field(alias="compassNote")
    coach_highlight_is_real: bool = Field(default=True, alias="coachHighlightIsReal")
    keystone_note_is_real: bool = Field(default=True, alias="keystoneNoteIsReal")
    compass_note_is_real: bool = Field(default=True, alias="compassNoteIsReal")
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
    council_sessions: list[FounderCouncilSession] = Field(
        default_factory=list, alias="councilSessions"
    )
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
    savings_rules: list[SmartSavingsRule] = Field(
        default_factory=list, alias="savingsRules"
    )
    monthly_reports: list[TreasuryMonthlyReport] = Field(
        default_factory=list, alias="monthlyReports"
    )
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
    system_events: list[CalendarEvent] = Field(
        default_factory=list, alias="systemEvents"
    )
    player_events: list[CalendarEvent] = Field(
        default_factory=list, alias="playerEvents"
    )
    updated_at: str = Field(alias="updatedAt")


# v0.7 Design Bible Chapter 64 — Executive Strategic Planning & Goal
# Management Engine (app/goals.py). Per that chapter's own Implementation
# Notes, this is deliberately the smallest real, independently-useful
# slice: a CEO-authored goal with one real progress metric, no ranking
# engine, no resource allocation, no milestones yet. A goal is always
# "reach at least targetValue" — every real metric this can track
# (Company Health, Company Score, portfolio return, Academy level) is a
# "higher is better" number, so a reduce-below-X goal type is not
# fabricated here; see app/goals.py's own module docstring.
GoalCategory = Literal["growth", "risk", "research", "trading", "operations"]

# Every value here maps to one already-real, already-computed number —
# see app/goals.py's resolve_metric_value(). No goal metric is invented;
# each is chosen because a genuine CEO-visible number already exists to
# track it against.
GoalMetric = Literal[
    "company_health_combined",
    "company_score_overall",
    "portfolio_return_pct",
    "academy_level",
]

GoalStatus = Literal["active", "completed", "cancelled", "expired"]


# v0.7 Design Bible Chapter 64 — Milestone Tracking, the "next honest
# slice" that chapter's own Implementation Notes named. A milestone is a
# real, fixed checkpoint on a goal's own real progress_pct (see
# app/goals.py's MILESTONE_THRESHOLDS) — never a second, independently
# invented tracking concept. `reached`/`reached_at` only ever go from
# unreached to reached, matching every other "a crossed milestone stays
# crossed" convention in this codebase (app/hall_of_fame.py,
# FounderState.retired, a Goal's own completed/expired status below).
class Milestone(CamelModel):
    id: str
    threshold_pct: float = Field(alias="thresholdPct")
    reached: bool = False
    reached_at: str | None = Field(default=None, alias="reachedAt")


class Goal(CamelModel):
    id: str
    title: str
    category: GoalCategory
    target_metric: GoalMetric = Field(alias="targetMetric")
    target_value: float = Field(alias="targetValue")
    # The real metric reading the last time this goal was recomputed
    # (every tick, alongside Company Health/Company Score — see
    # app/nexus.py's tick()). Never a fabricated forecast.
    current_value: float = Field(alias="currentValue")
    # 0-100, current_value as a % of target_value, clamped — an honest
    # "how far along" reading, not a time-based estimate.
    progress_pct: float = Field(alias="progressPct")
    created_sim_day: int = Field(alias="createdSimDay")
    # None = no deadline; the CEO's choice, not a required field.
    deadline_sim_day: int | None = Field(default=None, alias="deadlineSimDay")
    status: GoalStatus = "active"
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")
    completed_at: str | None = Field(default=None, alias="completedAt")
    # Real intermediate checkpoints on the way to target_value — see
    # app/goals.py's _build_milestones()/tick_goal(). Defaults to an
    # empty list so a save from before this field existed still
    # validates during load.
    milestones: list[Milestone] = Field(default_factory=list)
    # CEO Company Health + Live Market Realism directive, Section 13 —
    # a real "blockers" signal: consecutive real ticks (see
    # app/goals.py's GOAL_STALLED_THRESHOLD_TICKS) this goal has been
    # active with essentially zero real progress_pct movement. Resets to
    # 0 the moment real progress resumes — never a fabricated "reason"
    # string, just the honest count of stalled ticks itself. Defaults to
    # 0/False so a save from before these fields existed still validates
    # during load. `owner`/`supporting departments` from the CEO's
    # directive were explicitly cut, not silently dropped — see
    # app/goals.py's own module docstring for why no real per-goal
    # ownership/department-attribution mechanism exists in this
    # codebase today.
    stalled_ticks: int = Field(default=0, alias="stalledTicks")
    is_blocked: bool = Field(default=False, alias="isBlocked")


# v0.7 Design Bible Chapter 64 (third pass) — the Executive Priority
# Engine. A real, named formula over two real signals already on every
# Goal (progress_pct, deadline_sim_day) and the real current sim day —
# structurally distinct from Chapter 59's trade-proposal Priority Score
# (app/capital_priority.py), per this chapter's own Decision Logic
# section, since a goal and a trade proposal are different objects with
# different real signals available. Computed fresh per request, never
# persisted — see app/goals.py's compute_goal_priority().
class GoalPriority(CamelModel):
    goal_id: str = Field(alias="goalId")
    score: float
    remaining_pct: float = Field(alias="remainingPct")
    # None when the goal has no real deadline — an open-ended goal
    # carries no real time pressure to compute a days-remaining figure
    # from.
    days_remaining: int | None = Field(default=None, alias="daysRemaining")


class GoalAllocation(CamelModel):
    goal_id: str = Field(alias="goalId")
    score: float
    # A recommend-only share of executive attention, 0-100, normalized
    # across all active goals' real GoalPriority scores so they sum to
    # ~100 — never a claim about real capital movement (see
    # `app/goals.py`'s `compute_resource_allocation()` for why goals
    # have no real per-goal capital pool to allocate in the first
    # place).
    allocation_pct: float = Field(alias="allocationPct")


class StrategicReview(CamelModel):
    """v0.7 Design Bible Chapter 64 (fifth pass) — the Strategic Review
    Cycle. Mirrors Chapter 63's own monthly `ExecutiveReview` structure
    (see `app/executive_review.py`) but asks a different question: not
    "how is the company performing" but "how is CEO-authored goal
    progress moving." Every field here is real and derived directly
    from `Goal`/`Milestone`/`GoalPriority` — no fabricated numbers."""

    id: str
    created_at: str = Field(alias="createdAt")
    active_goal_count: int = Field(alias="activeGoalCount")
    # Real titles of goals that transitioned to `completed`/`expired`
    # since the previous review (by real `updatedAt`/`completedAt`
    # comparison) — capped the same way ExecutiveReview's own
    # `majorEvents` is, never every goal ever.
    completed_since_last_review: list[str] = Field(
        default_factory=list, alias="completedSinceLastReview"
    )
    expired_since_last_review: list[str] = Field(
        default_factory=list, alias="expiredSinceLastReview"
    )
    # Real count of Milestone objects across all goals whose real
    # `reachedAt` falls after the previous review.
    milestones_reached_since_last_review: int = Field(
        alias="milestonesReachedSinceLastReview"
    )
    # The single highest-urgency active goal this period, per the real
    # Executive Priority Engine (`compute_goal_priority()`) — None if no
    # active goal exists to prioritize.
    top_priority_goal_id: str | None = Field(default=None, alias="topPriorityGoalId")
    top_priority_score: float | None = Field(default=None, alias="topPriorityScore")
    summary: str


# Design Bible Chapter 74 Part 1 — Continuous Learning & Self-Improvement
# System (CLSIS), app/self_improvement.py. TradeTown may propose a
# company-level change to itself — never a trade, never a strategy
# (Chapter 62's sandbox.py/strategy_lab.py already owns strategy-level
# proposals) — grounded only in real, citable evidence. Every value here
# matches the brief's own eight named categories; three have a real,
# evidence-gated generator today ("risk_rule", "research_workflow", and
# — Trading Psychology & Discipline, Piece D — "knowledge_organization",
# triggered by a recurring win-side CaseStudy pattern, the loss side's
# own recurring_mistake trigger mirrored onto the opposite population).
# The same honesty posture Chapter 68 held for its own not-yet-real
# broker categories. See this chapter's own Deferred Features section
# for why the other five stay named but unbuilt.
SelfImprovementCategory = Literal[
    "risk_rule",
    "dashboard",
    "research_workflow",
    "position_sizing",
    "new_executive",
    "automation",
    "knowledge_organization",
    "ui",
]
SELF_IMPROVEMENT_CATEGORIES_WITH_REAL_GENERATOR: frozenset[SelfImprovementCategory] = (
    frozenset({"risk_rule", "research_workflow", "knowledge_organization"})
)
SelfImprovementStatus = Literal["pending", "approved", "rejected", "implemented"]
# Not a dollar figure — no real development-cost signal exists anywhere
# in this codebase to compute one honestly (see the chapter's own
# Ownership table).
SelfImprovementComplexity = Literal["small", "medium", "large"]
SelfImprovementPriority = Literal["low", "medium", "high"]


class SelfImprovementProposal(CamelModel):
    id: str
    category: SelfImprovementCategory
    title: str
    reasoning: str
    # Real source record ids (a CaseStudy id, a FailedStrategyArchiveEntry
    # id) — never an invented justification.
    evidence: list[str] = Field(default_factory=list)
    benefits: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    estimated_complexity: SelfImprovementComplexity = Field(alias="estimatedComplexity")
    priority: SelfImprovementPriority
    confidence: float
    status: SelfImprovementStatus = "pending"
    # CEO-manual resolution only — never automation-eligible, the same
    # restraint app/constitution.py's own Amendment flow holds itself to.
    ceo_note: str | None = Field(default=None, alias="ceoNote")
    # Reserved for Chapter 74.5's future Vision Alignment Engine — stays
    # null until that chapter wires it in. Declared now so the schema
    # doesn't need a breaking change later; does nothing yet.
    vision_alignment_score: float | None = Field(
        default=None, alias="visionAlignmentScore"
    )
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")
    decided_at: str | None = Field(default=None, alias="decidedAt")
    # The CEO's own real, manual record that they carried an approved
    # proposal out (e.g. "Tightened max_position_pct from 10% to 7%") —
    # never an automatic mutation of RiskLimits or anything else, since
    # this chapter's own honesty boundary has no single, well-defined
    # target field for a "risk_rule"/"research_workflow" proposal to
    # mutate. Matches this chapter's own established "CEO-manual
    # resolution only" restraint for the approve/reject step above.
    implementation_note: str | None = Field(default=None, alias="implementationNote")
    implemented_at: str | None = Field(default=None, alias="implementedAt")


# Design Bible Chapter 74 Part 1 — the Executive Learning Summary. Pure
# aggregation of four already-real per-agent systems (app/coach.py's
# AgentScore, app/mentor.py's ThinkingProfile, app/academy.py's
# AgentKnowledgeState, app/foundational_mentors.py's per-track
# progress) — computed fresh per request, like ThinkingProfile itself
# already is, never a fifth independently-stored copy of any of these
# numbers.
class ExecutiveLearningSummary(CamelModel):
    agent_id: AgentId = Field(alias="agentId")
    research_accuracy: float | None = Field(default=None, alias="researchAccuracy")
    confidence_calibration: float | None = Field(
        default=None, alias="confidenceCalibration"
    )
    thinking_profile: ThinkingProfile | None = Field(
        default=None, alias="thinkingProfile"
    )
    knowledge_points: float = Field(alias="knowledgePoints")
    knowledge_tier: int = Field(alias="knowledgeTier")
    knowledge_level: KnowledgeLevel = Field(alias="knowledgeLevel")
    # One entry per mentor track this agent has any real progress on —
    # (mentorId, graduationStatus) pairs, never a fabricated "training
    # recommendation" beyond what FoundationalMentorProgress already
    # tracks.
    mentor_tracks: list[str] = Field(default_factory=list, alias="mentorTracks")
    graduated_track_count: int = Field(default=0, alias="graduatedTrackCount")


# Design Bible Chapter 74 Part 2 — the Institutional Evolution Engine,
# app/evolution.py. Same underlying architecture as Part 1's CLSIS at a
# longer time horizon: company-wide/monthly rather than
# individual/event-level. Composes already-real monthly reports rather
# than competing with them — see the chapter's own cadence/focus table
# against BoardReport/StrategicReview/ExecutiveReview/CoachReport.
class CompanyEvolutionScore(CamelModel):
    """A disclosed, unweighted mean of five real, period-scoped counts
    or deltas — never a re-read of CompanyHealth's 21 sub-scores or
    CompanyScore's 7-metric mean (see this chapter's own Ownership
    table for why that would be duplication). Each factor is published
    alongside the overall score so the CEO can see exactly what moved
    it."""

    window: Literal["monthly", "quarterly", "yearly"]
    overall: float
    learning_volume: float = Field(alias="learningVolume")
    proposal_execution: float = Field(alias="proposalExecution")
    knowledge_growth: float = Field(alias="knowledgeGrowth")
    strategy_maturation: float = Field(alias="strategyMaturation")
    governance_evolution: float = Field(alias="governanceEvolution")
    period_start_sim_day: int = Field(alias="periodStartSimDay")
    period_end_sim_day: int = Field(alias="periodEndSimDay")
    computed_at: str = Field(alias="computedAt")


class InstitutionalEvolutionReport(CamelModel):
    id: str
    # Real ids of the period's own StrategicReview/ExecutiveReview/
    # CoachReport — composed by reference, never re-derived.
    strategic_review_id: str | None = Field(default=None, alias="strategicReviewId")
    executive_review_id: str | None = Field(default=None, alias="executiveReviewId")
    coach_report_id: str | None = Field(default=None, alias="coachReportId")
    top_case_study_ids: list[str] = Field(default_factory=list, alias="topCaseStudyIds")
    top_success_study_ids: list[str] = Field(
        default_factory=list, alias="topSuccessStudyIds"
    )
    proposals_generated: list[str] = Field(
        default_factory=list, alias="proposalsGenerated"
    )
    proposals_resolved: list[str] = Field(
        default_factory=list, alias="proposalsResolved"
    )
    evolution_score: CompanyEvolutionScore = Field(alias="evolutionScore")
    summary: str
    sim_day: int = Field(alias="simDay")
    created_at: str = Field(alias="createdAt")


# Design Bible Chapter 74.5 — the CEO Vision Board & Strategic Alignment
# Engine. The 5 real GoalCategory values plus one new value, `governance`,
# added specifically so ConstitutionAmendments (which have no GoalCategory
# of their own) have a real category to rank against — not because
# governance is a Goal concept.
VisionPriorityCategory = Literal[
    "growth", "risk", "research", "trading", "operations", "governance"
]

VisionObjectiveCategory = Literal[
    "trading_style", "expansion", "research_priority", "technology", "lifestyle", "other"
]


class VisionBoardObjective(CamelModel):
    """CEO-authored text with a category tag, nothing else — no progress
    bar, no percentage, no target value. The same honesty boundary
    app/goals.py's own 4-metric limit drew for itself, applied here to
    the objectives that fall outside even that limit (see the chapter's
    own Ownership table)."""

    id: str
    text: str
    category: VisionObjectiveCategory
    created_at: str = Field(alias="createdAt")


class VisionBoardState(CamelModel):
    """One real, permanent, CEO-mutated object — the same shape as
    RiskLimits/TradingModeState, not a growing log."""

    mission: str | None = None
    # A CEO-ranked ordering over VisionPriorityCategory — index 0 is
    # rank 1 (highest). No duplicate categories; enforced by
    # app/vision_board.py's update function, not the schema itself.
    priorities: list[VisionPriorityCategory] = Field(default_factory=list)
    objectives: list[VisionBoardObjective] = Field(default_factory=list)
    # Optional CEO annotation displayed next to app/company_dna.py's real
    # derived identity classification — never a competing
    # re-classification of it.
    identity_note: str | None = Field(default=None, alias="identityNote")
    updated_at: str = Field(alias="updatedAt")


class VisionAlignmentScore(CamelModel):
    """Output of compute_vision_alignment_score() — a real, disclosed,
    purely mechanical rank-based formula, never a fabricated 'does this
    feel aligned' read. Computed on-demand for goal/constitution_amendment;
    persisted on SelfImprovementProposal at generation time."""

    subject_type: Literal[
        "self_improvement_proposal", "goal", "constitution_amendment"
    ] = Field(alias="subjectType")
    subject_id: str = Field(alias="subjectId")
    score: float
    supporting_reasons: list[str] = Field(default_factory=list, alias="supportingReasons")
    conflicting_goals: list[str] = Field(default_factory=list, alias="conflictingGoals")
    confidence: float
    computed_at: str = Field(alias="computedAt")


class VisionSelfCorrectionNote(CamelModel):
    """The one real, narrow Self-Correction check: the CEO's own rank-1
    priority vs. the real Daily Circuit Breaker tier. Computed on-demand,
    not persisted — same convention Chapter 72's Early Warning Score uses
    for a live read with no history to keep."""

    triggered: bool
    message: str | None = None
    circuit_breaker_tier: DailyCircuitBreakerTier = Field(alias="circuitBreakerTier")
    computed_at: str = Field(alias="computedAt")


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
    meeting_minutes: list[MeetingMinutes] = Field(
        default_factory=list, alias="meetingMinutes"
    )
    paper_portfolio: PaperPortfolio = Field(alias="paperPortfolio")
    strategies: list[Strategy] = Field(default_factory=list)
    backtest_sessions: list[BacktestSession] = Field(
        default_factory=list, alias="backtestSessions"
    )
    simulation_results: list[SimulationResult] = Field(
        default_factory=list, alias="simulationResults"
    )
    strategy_reports: list[StrategyReport] = Field(
        default_factory=list, alias="strategyReports"
    )
    strategy_reviews: list[StrategyReview] = Field(
        default_factory=list, alias="strategyReviews"
    )
    # v0.7 — Quantitative Research & Intelligence System, Piece 4.
    # One real ModelValidationReport per request_strategy_company_review()
    # call (the same call that files a StrategyReview) — see
    # app/model_validation.py.
    strategy_model_validations: list[ModelValidationReport] = Field(
        default_factory=list, alias="strategyModelValidations"
    )
    # v0.7 Feature 52 (Part 1) — the Strategy Validation Laboratory's
    # extension of the Research Sandbox pipeline (app/strategy_lab.py).
    # One real permanent record per strategy per real trigger point —
    # nothing here is ever deleted, matching Part 2's own "strategies are
    # company assets" ethos even though Part 2's fuller library/versioning
    # is not yet built.
    strategy_monte_carlo_results: list[StrategyMonteCarloResult] = Field(
        default_factory=list, alias="strategyMonteCarloResults"
    )
    strategy_regime_tests: list[StrategyRegimeTestReport] = Field(
        default_factory=list, alias="strategyRegimeTests"
    )
    strategy_liquidity_validations: list[StrategyLiquidityValidation] = Field(
        default_factory=list, alias="strategyLiquidityValidations"
    )
    strategy_executive_reviews: list[StrategyExecutiveReview] = Field(
        default_factory=list, alias="strategyExecutiveReviews"
    )
    strategy_founder_approvals: list[StrategyFounderApproval] = Field(
        default_factory=list, alias="strategyFounderApprovals"
    )
    # v0.7 Feature 52 (Part 2) — "Living Strategies." strategy_health_assessments
    # is a real, recurring trend read (re-run alongside Part 1's own
    # per-completed-simulation artifacts). strategy_hall_of_fame/
    # strategy_failed_archive are permanent, one-entry-per-retirement
    # records — every real retire_strategy() CEO action files exactly one
    # of the two, never both, never neither (see app/strategy_lab.py's
    # generate_strategy_retirement_outcome()).
    strategy_health_assessments: list[StrategyHealthAssessment] = Field(
        default_factory=list, alias="strategyHealthAssessments"
    )
    strategy_hall_of_fame: list[StrategyHallOfFameEntry] = Field(
        default_factory=list, alias="strategyHallOfFame"
    )
    strategy_failed_archive: list[FailedStrategyArchiveEntry] = Field(
        default_factory=list, alias="strategyFailedArchive"
    )
    # CEO directive "Professional Quant Firm Phase," Feature 37 — real,
    # persisted CompiledStrategyDefinition version history, keyed by
    # that definition's own real slug id (app/strategy_compiler.py's
    # compile_strategy_text() computes the same id for the same name
    # every time). Append-only, matching strategy_hall_of_fame's own
    # "never silently overwrite" precedent — see app/strategy_registry.py.
    compiled_strategy_versions: dict[str, list[CompiledStrategyDefinition]] = Field(
        default_factory=dict, alias="compiledStrategyVersions"
    )
    # CEO directive "Professional Quant Firm Phase," Feature 36 — the
    # Quant Research Lab's permanent, ever-growing, never-deleted
    # experiment record (see app/quant_research_lab.py and
    # QuantResearchExperiment's own docstring for the disclosed
    # departure from this directive family's usual CAGS convention).
    quant_research_experiments: list[QuantResearchExperiment] = Field(
        default_factory=list, alias="quantResearchExperiments"
    )
    hall_of_fame: list[HallOfFameEntry] = Field(
        default_factory=list, alias="hallOfFame"
    )
    coach_reports: list[CoachReport] = Field(default_factory=list, alias="coachReports")
    company_score: CompanyScore = Field(alias="companyScore")
    performance_snapshots: list[PerformanceSnapshot] = Field(
        default_factory=list, alias="performanceSnapshots"
    )
    risk_limits: RiskLimits = Field(default_factory=RiskLimits, alias="riskLimits")
    risk_warnings: list[RiskWarning] = Field(default_factory=list, alias="riskWarnings")
    # Design Bible Chapter 67 (TTOS) Part 3.
    emergency_stop: EmergencyStopState = Field(default_factory=EmergencyStopState, alias="emergencyStop")
    scanner_alerts: list[ScannerAlert] = Field(
        default_factory=list, alias="scannerAlerts"
    )
    decisions: list[TradeDecision] = Field(default_factory=list)
    agent_energy: AgentEnergy = Field(alias="agentEnergy")
    signal_calibration: SignalCalibrationState = Field(
        default_factory=SignalCalibrationState, alias="signalCalibration"
    )
    player_vs_ai: PlayerVsAiState = Field(
        default_factory=PlayerVsAiState, alias="playerVsAi"
    )
    education: EducationProgress = Field(default_factory=EducationProgress)
    # v0.6.2 Phase 10: which PaperTrade ids have already had their trade
    # outcome popup shown/dismissed — see app/routers/trades.py. Persisted
    # so a refresh or Docker restart never re-shows a popup for a trade
    # the player already saw. Real progress, not regenerable — capped like
    # every other list here (see portfolio.py's own MAX_TRADE_HISTORY,
    # which this tracks against).
    viewed_trade_notification_ids: list[str] = Field(
        default_factory=list, alias="viewedTradeNotificationIds"
    )
    # Feature 12 — Executive Voting System. trade_proposals holds only
    # currently-pending proposals (removed the moment the CEO decides);
    # ceo_decisions is the permanent, capped history behind the CEO/AI
    # accuracy stats (see app/executive.py).
    trade_proposals: list[TradeProposal] = Field(
        default_factory=list, alias="tradeProposals"
    )
    ceo_decisions: list[CeoDecisionRecord] = Field(
        default_factory=list, alias="ceoDecisions"
    )
    # v0.7 Feature 17 — AI Debate Room. One Debate per proposal (with the
    # newest replacing prior ones for the same proposal if "request
    # another debate" was used), capped like every other list here.
    debates: list[Debate] = Field(default_factory=list)
    # v0.7 Feature 20 — Trade Gatekeeper. Every trade the gatekeeper
    # blocked, capped at MAX_GATEKEEPER_REJECTIONS like every other list
    # here; see app/gatekeeper.py.
    gatekeeper_rejections: list[GatekeeperRejection] = Field(
        default_factory=list, alias="gatekeeperRejections"
    )
    # v0.7 Chapter 58 — Institutional Trade Filter & Opportunity
    # Gatekeeper. Every candidate rejected BEFORE it ever became a real
    # TradeProposal, capped at MAX_OPPORTUNITY_REJECTIONS like every
    # other list here; see app/opportunity_gatekeeper.py. A distinct,
    # earlier-stage sibling to gatekeeper_rejections above, not a
    # replacement for it.
    opportunity_rejections: list[OpportunityRejection] = Field(
        default_factory=list, alias="opportunityRejections"
    )
    # v0.7 Feature 22 — Market Environment Simulation (app/market_environment.py).
    market_environment: MarketEnvironmentState = Field(alias="marketEnvironment")
    # v0.7 Feature 51 — Market Intelligence Department (app/market_intelligence.py).
    # `market_intelligence` is the always-current "eyes" reading, recomputed
    # fresh every tick like market_environment/company_health above.
    # `market_intelligence_reports` is the permanent once-daily Executive
    # Market Brief history, capped at MAX_MARKET_INTELLIGENCE_REPORTS.
    # `market_intelligence_learning` is the Learning Loop's own permanent
    # history, capped at MAX_MARKET_INTELLIGENCE_LEARNING.
    market_intelligence: MarketIntelligenceState = Field(alias="marketIntelligence")
    market_intelligence_reports: list[MarketIntelligenceReport] = Field(
        default_factory=list, alias="marketIntelligenceReports"
    )
    market_intelligence_learning: list[MarketIntelligenceLearningEntry] = Field(
        default_factory=list, alias="marketIntelligenceLearning"
    )
    # v0.7 Feature 23 — Company Health & Stability System (app/company_health.py).
    company_health: CompanyHealth = Field(alias="companyHealth")
    # CEO Company Health + Live Market Realism directive, Section 6 — the
    # real tick-over-tick delta breakdown between this reading and the
    # one before it (app/company_health.py's diff_company_health()). None
    # on the very first tick of a fresh game (no prior reading to diff
    # against yet).
    company_health_delta: CompanyHealthDelta | None = Field(default=None, alias="companyHealthDelta")
    # v0.7 Feature 43 — Company DNA (app/company_dna.py).
    company_dna: CompanyDNA = Field(alias="companyDna")
    # v0.7 Feature 48 — Legacy: a small, permanent, capped per-trait
    # delta (app/company_dna.py's nudge_legacy()), layered on top of
    # company_dna's own fresh historical-average score every time it's
    # recomputed, never mixed into the five traits' own formulas. Keyed
    # by trait id (e.g. "risk_appetite").
    company_dna_legacy: dict[str, float] = Field(
        default_factory=dict, alias="companyDnaLegacy"
    )
    # v0.7 Feature 49 — Daily Trading Objectives (app/risk_engine.py's
    # compute_daily_objective_status).
    daily_objective_status: DailyObjectiveStatus = Field(alias="dailyObjectiveStatus")
    # Prop-Firm Risk Intelligence Addendum, Piece 8 — remaining risk
    # budget (app/risk_engine.py's compute_risk_budget_status), the same
    # "derived, recomputed fresh every tick" convention as
    # daily_objective_status directly above.
    risk_budget_status: RiskBudgetStatus = Field(alias="riskBudgetStatus")
    # v0.7 Feature 24 — the CIO's Monthly Executive Review (app/executive_review.py).
    executive_reviews: list[ExecutiveReview] = Field(
        default_factory=list, alias="executiveReviews"
    )
    # Design Bible Chapter 70 Part 1 — the Board Report (app/board.py),
    # daily/quarterly/emergency cadence, capped the same way every other
    # daily-cadence report list is (see MAX_BOARD_REPORTS).
    board_reports: list[BoardReport] = Field(
        default_factory=list, alias="boardReports"
    )
    # v0.7 Feature 25 — AI Academy. `academy_projects` holds the one
    # currently-active knowledge project (company-wide, not per-agent);
    # `academy_completed_projects` is the permanent, capped Knowledge
    # Library (app/academy_research.py). `agent_knowledge` is every
    # agent's own real points/tier (app/academy.py); `academy_state` is
    # the company-wide progression level derived from both.
    academy_projects: list[AcademyProject] = Field(
        default_factory=list, alias="academyProjects"
    )
    academy_completed_projects: list[AcademyProject] = Field(
        default_factory=list, alias="academyCompletedProjects"
    )
    agent_knowledge: dict[AgentId, AgentKnowledgeState] = Field(
        default_factory=dict, alias="agentKnowledge"
    )
    academy_state: AcademyState = Field(alias="academyState")
    # v0.7 Feature 26 — the Discipline Chamber (app/discipline.py). One
    # capped, permanent DisciplineReview per closed paper trade.
    discipline_reviews: list[DisciplineReview] = Field(
        default_factory=list, alias="disciplineReviews"
    )
    # v0.7 Feature 27 — the Library of Mistakes (app/mistakes.py). One
    # capped, permanent CaseStudy per detected real process-gap mistake.
    case_studies: list[CaseStudy] = Field(default_factory=list, alias="caseStudies")
    # CEO directive "Features 26-30," Feature 26 — Institutional Memory
    # 2.0 (app/institutional_memory.py). One capped, permanent
    # InstitutionalMemoryEntry promoted from a real CaseStudy,
    # FailedStrategyArchiveEntry, StrategyHallOfFameEntry,
    # ModelValidationReport, RiskWarning, or market regime shift — see
    # that module's own docstring for the full promotion/contradiction/
    # relevance design. Distinct from case_studies above (this codebase's
    # own separately-numbered "Feature 26," the Library of Mistakes) —
    # the same kind of feature-number collision app/war_room.py's module
    # docstring already discloses for "Feature 54"/"Feature 55."
    institutional_memory: list[InstitutionalMemoryEntry] = Field(
        default_factory=list, alias="institutionalMemory"
    )
    # CEO Company Health + Live Market Realism directive, Section 3 —
    # one capped, permanent LearningEvent per real Knowledge-tier
    # crossing (see app/academy.py's award_points()).
    learning_events: list[LearningEvent] = Field(default_factory=list, alias="learningEvents")
    # v0.7 — the Decision Memory System's Decision Vault
    # (app/decision_vault.py). One capped, permanent DecisionVaultEntry
    # per closed paper trade, joining every real artifact already
    # generated for that trade — see DecisionVaultEntry's own doc
    # comment above for the exact honesty boundary.
    decision_vault: list[DecisionVaultEntry] = Field(
        default_factory=list, alias="decisionVault"
    )
    # v0.7 Feature 29 — the Reasoning Lab (app/reasoning_lab.py). One
    # capped, permanent ReasoningChallenge filed periodically from the
    # company's most recent real AI Debate; `reasoning_lab_state` is the
    # company-wide progression level derived from the challenge count.
    reasoning_challenges: list[ReasoningChallenge] = Field(
        default_factory=list, alias="reasoningChallenges"
    )
    reasoning_lab_state: ReasoningLabState = Field(alias="reasoningLabState")
    # v0.7 Feature 30 — the Reflection Chamber (app/wisdom.py). One
    # capped, permanent ReflectionSession per weekly/monthly cycle;
    # `wisdom_state` is the company-wide Wisdom Score, updated only when
    # a session is generated (see WisdomState's own docstring for why).
    reflection_sessions: list[ReflectionSession] = Field(
        default_factory=list, alias="reflectionSessions"
    )
    wisdom_state: WisdomState = Field(alias="wisdomState")
    # v0.7 Feature 32 — the Socratic Mentor (app/mentor.py). One capped,
    # permanent QuestionOfTheDay per in-game morning; `thinking_profiles`
    # is every agent's purely-computed readout; `mentor_state` is the
    # company-wide progression level derived from the archive's length.
    question_archive: list[QuestionOfTheDay] = Field(
        default_factory=list, alias="questionArchive"
    )
    thinking_profiles: dict[AgentId, ThinkingProfile] = Field(
        default_factory=dict, alias="thinkingProfiles"
    )
    mentor_state: MentorState = Field(alias="mentorState")
    # CEO directive "Features 26-30," Feature 27 — Agent Performance
    # Reviews (app/performance_review.py). One capped, permanent
    # AgentPerformanceReview per real agent per real weekly period —
    # see that module's own docstring for the full evidence/role-
    # awareness/process-vs-outcome design.
    agent_performance_reviews: list[AgentPerformanceReview] = Field(
        default_factory=list, alias="agentPerformanceReviews"
    )
    # CEO directive "Features 26-30," Feature 28 — Academy + Skill
    # Progression (app/skill_progression.py). One capped, permanent
    # AgentSkillProfile per real agent per real weekly period — see that
    # module's own docstring for the full evidence/NOT_TRACKABLE_YET/
    # training-recommendation design.
    agent_skill_profiles: list[AgentSkillProfile] = Field(
        default_factory=list, alias="agentSkillProfiles"
    )
    # CEO directive "Features 26-30," Feature 29 — Prediction -> Outcome
    # Tracking (app/prediction_tracking.py). One capped, permanent
    # PredictionRecord per real trade-direction claim staked before its
    # outcome was known.
    prediction_records: list[PredictionRecord] = Field(
        default_factory=list, alias="predictionRecords"
    )
    # CEO directive "Features 26-30," Feature 30 — the Failure Review
    # Board (app/failure_review.py). One capped, permanent
    # FailureClassification per real closed, losing trade.
    failure_classifications: list[FailureClassification] = Field(
        default_factory=list, alias="failureClassifications"
    )
    # CEO directive "Features 31-35: Compliance, Governance & Continuous
    # Improvement System," Feature 31 — the Compliance Incident
    # Resolution Engine (app/compliance_incidents.py).
    compliance_incidents: list[ComplianceIncident] = Field(
        default_factory=list, alias="complianceIncidents"
    )
    # CEO directive "Features 31-35," Feature 32 — CEO Override
    # Governance (app/override_governance.py).
    ceo_override_evaluations: list[CeoOverrideEvaluation] = Field(
        default_factory=list, alias="ceoOverrideEvaluations"
    )
    # v0.7 Feature 49 (Phase 3) — the Foundational Mentor Program
    # (app/foundational_mentors.py). See FoundationalMentorState's own
    # docstring for how this differs from mentor_state above.
    foundational_mentor_state: FoundationalMentorState = Field(
        alias="foundationalMentorState"
    )
    # v0.7 Feature 39 — the Original Founders (app/founders.py).
    founder_state: FounderState = Field(alias="founderState")
    # v0.7 Feature 41 — the Intelligent Devil's Advocate System. One
    # capped, permanent ChallengeReport per proposal (with the newest
    # replacing prior ones for the same proposal if "request another
    # review" was used), same convention as `debates` above.
    # `innovation_state` is every agent's own real points/tier earned
    # through their Devil's Advocate track record (app/innovation.py).
    challenge_reports: list[ChallengeReport] = Field(
        default_factory=list, alias="challengeReports"
    )
    innovation_state: dict[AgentId, InnovationState] = Field(
        default_factory=dict, alias="innovationState"
    )
    # v0.7 Feature 33 — the CEO Treasury (app/treasury.py). See
    # TreasuryState's own docstring for the structural "never touched by
    # any automatic system" guarantee.
    treasury: TreasuryState
    # v0.7 Feature 36 — the CEO Calendar (app/calendar.py).
    calendar: CalendarState
    # v0.7 — the Advanced Quantitative Research Division (app/black_box.py).
    black_box: BlackBoxState = Field(alias="blackBox")
    # v0.7 Feature 50 (Part 2/3) — the Executive Meeting Log and Weekly
    # Self-Evaluation. Both are real permanent history (grow, never
    # recomputed from scratch) — see app/executive_intelligence.py.
    executive_meeting_log: list[ExecutiveMeetingLogEntry] = Field(
        default_factory=list, alias="executiveMeetingLog"
    )
    department_self_evaluations: list[DepartmentSelfEvaluation] = Field(
        default_factory=list, alias="departmentSelfEvaluations"
    )
    # v0.7 Feature 44 — Talent Discovery System (app/talent.py).
    talent: TalentState = Field(alias="talent")
    # v0.7 Feature 46 — the Company Constitution (app/constitution.py).
    constitution: ConstitutionState = Field(alias="constitution")
    # v0.7 Feature 55 — the Executive Decision Simulator's Digital War
    # Room (app/war_room.py). One capped, permanent WarRoomSession per
    # new TradeProposal, same convention as `challenge_reports` above.
    war_room_sessions: list[WarRoomSession] = Field(
        default_factory=list, alias="warRoomSessions"
    )
    # v0.7 Feature 56 — Enterprise Portfolio Intelligence
    # (app/portfolio_intelligence.py). Recomputed fresh every tick from
    # the portfolio's own real current state, same convention as
    # `company_health`/`company_dna` — never a persisted, driftable copy.
    portfolio_intelligence: PortfolioIntelligence = Field(alias="portfolioIntelligence")
    # Design Bible Chapter 71 — Economic Intelligence Center
    # (app/economic_intelligence.py). `economic_intelligence` is the
    # always-current cross-signal read, recomputed fresh every tick like
    # `portfolio_intelligence` above. `economic_intelligence_reports` is
    # the permanent once-daily Economic Intelligence Brief history,
    # capped at MAX_ECONOMIC_INTELLIGENCE_REPORTS.
    economic_intelligence: EconomicIntelligenceState = Field(
        alias="economicIntelligence"
    )
    economic_intelligence_reports: list[EconomicIntelligenceReport] = Field(
        default_factory=list, alias="economicIntelligenceReports"
    )
    # Design Bible Chapter 72 — Black Swan Intelligence & Resilience
    # System (app/black_swan.py). `black_swan_intelligence` is the
    # always-current stress read, recomputed fresh every tick like
    # `economic_intelligence` above. `black_swan_reports` is the
    # permanent once-daily Situation Report history, capped at
    # MAX_BLACK_SWAN_REPORTS. `defensive_mode` is real, CEO-mutated
    # state (not recomputed). `black_swan_events` is the permanent
    # Post-Event Analysis history, capped at MAX_BLACK_SWAN_EVENTS.
    black_swan_intelligence: BlackSwanIntelligenceState = Field(
        alias="blackSwanIntelligence"
    )
    black_swan_reports: list[BlackSwanReport] = Field(
        default_factory=list, alias="blackSwanReports"
    )
    defensive_mode: DefensiveModeState = Field(
        default_factory=DefensiveModeState, alias="defensiveMode"
    )
    black_swan_events: list[BlackSwanEventRecord] = Field(
        default_factory=list, alias="blackSwanEvents"
    )
    # Design Bible Chapter 72 Part 2 — Institutional Survival Score.
    # Recomputed fresh every tick like black_swan_intelligence above.
    institutional_survival_score: InstitutionalSurvivalScore = Field(
        alias="institutionalSurvivalScore"
    )
    # Design Bible Chapter 75 — Company Trading Modes & Institutional
    # Capital Protection (app/trading_modes.py). trading_modes is the
    # CEO's own real selection/thresholds; daily_circuit_breaker and
    # losing_streak are recomputed fresh every tick exactly like
    # daily_objective_status above, never a second drifting copy.
    # recovery_briefings is a small, capped, append-only history —
    # see MAX_RECOVERY_BRIEFINGS.
    trading_modes: TradingModeState = Field(alias="tradingModes")
    daily_circuit_breaker: DailyCircuitBreakerRead = Field(
        alias="dailyCircuitBreaker"
    )
    losing_streak: LosingStreakRead = Field(alias="losingStreak")
    # Behavioral Circuit Breaker (app/behavioral_risk.py) — recomputed
    # fresh every tick exactly like daily_circuit_breaker/losing_streak
    # above, never a second drifting copy. This ambient read is capped at
    # "warning" (no candidate proposal to corroborate against); the real
    # "triggered" enforcement happens per-proposal inside the Gatekeeper
    # (app/gatekeeper.py::_behavioral_check), not here.
    behavioral_circuit_breaker: BehavioralCircuitBreakerRead = Field(alias="behavioralCircuitBreaker")
    recovery_briefings: list[RecoveryBriefing] = Field(
        default_factory=list, alias="recoveryBriefings"
    )
    # Design Bible Chapter 73.5 — Mobile Command Center & Remote
    # Operations (app/travel_mode.py). travel_mode is the CEO's own
    # real posture/settings (persisted, CEO-mutated, like
    # defensive_mode above); travel_mode_briefings is a small, capped,
    # append-only Return-to-Operations history — see
    # MAX_TRAVEL_MODE_BRIEFINGS.
    travel_mode: TravelModeState = Field(default_factory=TravelModeState, alias="travelMode")
    travel_mode_briefings: list[TravelModeBriefing] = Field(
        default_factory=list, alias="travelModeBriefings"
    )
    # v0.7 Design Bible Chapter 64 — CEO-authored company goals
    # (app/goals.py). Capped and append-only like every other real list
    # in this codebase — see MAX_GOALS.
    goals: list[Goal] = Field(default_factory=list)
    # v0.7 Design Bible Chapter 64 (fifth pass) — the Strategic Review
    # Cycle, generated on the same monthly cadence as Chapter 63's own
    # ExecutiveReview but over CEO-authored goals (app/goals.py). Capped
    # like every other periodic-report list — see MAX_STRATEGIC_REVIEWS.
    strategic_reviews: list[StrategicReview] = Field(
        default_factory=list, alias="strategicReviews"
    )
    # Design Bible Chapter 69 Part 1 — Multi-Account & Fund Management
    # System (app/accounts.py). Real, isolated capital pools beyond the
    # primary PaperPortfolio above; `active_account_id` is None when the
    # CEO is viewing the primary account (never a distinct Account
    # object of its own — see app/accounts.py's module docstring).
    accounts: list[Account] = Field(default_factory=list)
    active_account_id: str | None = Field(default=None, alias="activeAccountId")
    # Design Bible Chapter 74 Part 1 — Self-Improvement Proposals
    # (app/self_improvement.py). Capped and append-only like every other
    # real list in this codebase — see MAX_SELF_IMPROVEMENT_PROPOSALS.
    self_improvement_proposals: list[SelfImprovementProposal] = Field(
        default_factory=list, alias="selfImprovementProposals"
    )
    # Design Bible Chapter 74 Part 2 — the Institutional Evolution Engine
    # (app/evolution.py). Monthly cadence, capped the same way every
    # other monthly-cadence report list is (see MAX_EVOLUTION_REPORTS).
    evolution_reports: list[InstitutionalEvolutionReport] = Field(
        default_factory=list, alias="evolutionReports"
    )
    # Design Bible Chapter 74.5 — the CEO Vision Board & Strategic
    # Alignment Engine (app/vision_board.py). CEO-mutated singleton, the
    # same shape as RiskLimits/ConstitutionState.
    vision_board: VisionBoardState = Field(alias="visionBoard")
    time: TimeState
    settings: SettingsState
    dialogue_history: list[DialogueHistoryEntry] = Field(
        default_factory=list, alias="dialogueHistory"
    )
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
    dialogue_history: list[DialogueHistoryEntry] = Field(
        default_factory=list, alias="dialogueHistory"
    )


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
