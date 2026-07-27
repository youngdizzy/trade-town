"""NexusManager — coordinates the AI company.

Responsibilities (per the v0.2 brief): register agents, assign tasks, track
progress, drive the office whiteboards, and call meetings / break-room
visits. v0.3 layers real-looking market intelligence on top (research
queue, watchlist, meeting discussions/minutes, company memory) without
executing any trade or calling a real market API — see app/market_data.py,
app/research.py, and docs/Architecture.md "Research & market intelligence
(v0.3)" for that boundary.

Design note: meetings and break-room visits are both implemented as the
same mechanism — a temporary `AgentOverride` on an agent's location that
takes priority over their normal schedule and expires after N game-minutes
(see AgentOverride in schemas.py). A "meeting" is just that override
applied to several agents at once. This avoids two parallel state machines
for what is structurally the same behavior.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone

from app.agents import AGENT_PROFILES, LOCATION_TO_SCENE, all_agent_ids
from app.analytics import compute_performance_snapshot, confidence_accuracy, record_snapshot
from app.broker import place_order, tick_broker
from app.coach import generate_report as generate_coach_report
from app.coach import record_report as record_coach_report_entry
from app.company_score import compute_company_score
from app.decision import decide_trade
from app.discussion import generate_discussion
from app.hall_of_fame import evaluate_hall_of_fame
from app.journal import stamp_journal_entry
from app.market_data import market_data_provider
from app.paper_trading import tick_paper_trading
from app.research import RESEARCHER_IDS, default_research, tick_research
from app.risk_engine import evaluate_guardian_exposure, evaluate_sentinel_risk, monitor_portfolio, recommended_quantity
from app.scanner import tick_scanner
from app.schedule import block_for_hour
from app.scribe import (
    FUTURE_TRADE_CONFIDENCE_THRESHOLD,
    build_minutes,
    record_coach_report,
    record_decision,
    record_hall_of_fame_entry,
    record_meeting,
    record_order_placed,
    record_paper_trade,
    record_research_completions,
    record_scanner_alert,
    record_simulation_result,
)
from app.schemas import (
    AgentId,
    AgentOverride,
    AgentState,
    CoachReport,
    EntityTransform,
    GameSaveState,
    MemoryEntry,
    MemoryRecord,
    MeetingMinutes,
    MeetingState,
    NewsItem,
    PaperPortfolio,
    PaperTrade,
    ResearchItem,
    RiskLimits,
    Task,
    TaskCategory,
    TaskPriority,
    TimeState,
    TradeDecision,
)
from app.simulation import default_strategies, tick_simulation_lab
from app.voting import collect_votes
from app.watchlist import default_watchlist, tick_watchlist

MAX_MEMORY = 50
MAX_TASKS = 60
MAX_MEETING_MINUTES = 20
# TradeDecision is one of the richest records in the whole save (a full
# vote breakdown across 4-6 agents plus several paragraphs of reasoning
# text, ~1.5KB each) and, unlike every other list this module produces,
# it had no cap at all until this constant was added — it grew by one
# entry every time research crossed the trade-candidate threshold, for
# as long as the process kept running, with nothing ever evicted. Over
# real deployment timescales (weeks of continuous uptime, not this
# session's test runs) that silently grew the save payload past nginx's
# default 1MB body-size limit, which is what actually caused reported
# "413 Request Entity Too Large" save failures — not an undersized
# limit. 200 keeps the Decisions/Opportunities tabs richly populated
# (far more headroom than MAX_TRADE_HISTORY's 50) while keeping this
# list's contribution to the save bounded at roughly 300KB.
MAX_DECISIONS = 200
# Per-category, not a single shared cap: discovery news fires far more
# often than market/company news (it's tied to every task-changing event
# across four agents, vs. a flat per-tick roll for market headlines), so a
# single shared cap would eventually let discovery evict every market
# headline during normal play, leaving the Market Status panel
# permanently empty. See _trim_news().
MAX_NEWS_PER_CATEGORY = 8

MEETING_CHANCE_PER_TICK = 0.03
MEETING_DURATION_MINUTES = 20
MEETING_MIN_ATTENDEES = 2

BREAK_ENERGY_THRESHOLD = 35
BREAK_CHANCE_PER_TICK = 0.10
BREAK_DURATION_MINUTES = 15
BREAK_ENERGY_BONUS = 20

RESTFUL_LOCATIONS = {"lobby", "break-room"}

# Evening review / weekly / monthly cadences (v0.5 brief, Feature 7).
# GAME_MINUTES_PER_TICK always divides 60 evenly (default 5), so every
# in-game day passes through hour==20, minute==0 exactly once — a simpler,
# more restart-safe trigger than diffing against the previous tick's time.
EVENING_REVIEW_HOUR = 20
WEEKLY_INTERVAL_DAYS = 7
MONTHLY_INTERVAL_DAYS = 30

MARKET_HEADLINES = [
    "Markets drift sideways in a quiet overnight session",
    "Analysts split on next move as volume thins",
    "Sector rotation continues into a second week",
    "Volatility index ticks lower for a third straight day",
    "Traders await fresh catalysts amid a slow news cycle",
]

# Keyword -> category, checked in order against the lowercased task label.
# Falls back to _DEFAULT_CATEGORY_BY_AGENT when nothing matches. This is a
# classification convenience over the existing free-text schedule labels
# (see schedule.py) rather than a second source of truth — the labels
# themselves are still what's shown to the player.
_TASK_CATEGORY_KEYWORDS: list[tuple[str, TaskCategory]] = [
    ("market news", "news_scan"),
    ("overnight charts", "news_scan"),
    ("after-hours signals", "news_scan"),
    ("technical patterns", "chart_analysis"),
    ("monitor feeds", "chart_analysis"),
    ("momentum indicators", "chart_analysis"),
    ("cross-checking scout's notes", "watchlist_update"),
    ("cross-referencing the archive", "watchlist_update"),
    ("research memo", "documentation"),
    ("logging research updates", "documentation"),
    ("filing yesterday's minutes", "documentation"),
    ("indexing", "documentation"),
    ("archiving", "documentation"),
    ("quarterly reports", "research"),
    ("research findings", "research"),
    ("overnight filings", "research"),
    ("archived reports", "research"),
    ("overnight logs", "research"),
    ("strategy", "review"),
    ("agent performance", "review"),
    ("decisions", "review"),
    ("priorities", "review"),
    ("reviewing the day", "review"),
    ("standing by", "review"),
    ("overnight positions", "review"),
    ("paper trades", "paper_trading"),
    ("confidence calibration", "analytics"),
    ("simulation results", "simulation"),
    ("performance review", "coaching"),
    ("drafting recommendations", "coaching"),
    ("observing research", "review"),
    ("risk exposure", "risk_management"),
    ("position sizing", "risk_management"),
    ("trade candidates", "voting"),
    ("risk limits", "risk_management"),
    ("day's approvals", "voting"),
    ("standing watch", "risk_management"),
    ("premarket movers", "market_scanning"),
    ("breakouts", "market_scanning"),
    ("volume spikes", "market_scanning"),
    ("scanner alerts", "market_scanning"),
    ("after-hours activity", "market_scanning"),
    ("day's alerts", "market_scanning"),
    ("overnight volatility", "market_scanning"),
    ("portfolio exposure", "risk_management"),
    ("concentration risk", "risk_management"),
    ("drawdown levels", "risk_management"),
    ("reviewing portfolio performance", "analytics"),
    ("risk reductions", "risk_management"),
    ("exposure report", "risk_management"),
]

_DEFAULT_CATEGORY_BY_AGENT: dict[AgentId, TaskCategory] = {
    "scout": "news_scan",
    "atlas": "review",
    "echo": "chart_analysis",
    "nova": "research",
    "scribe": "documentation",
    "coach": "coaching",
    "sentinel": "risk_management",
    "pulse": "market_scanning",
    "guardian": "risk_management",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _truncate(text: str, max_len: int) -> str:
    """The in-world whiteboard prop is a small fixed-size rectangle (see
    Whiteboard.ts) — long research titles/summaries need a hard cap or
    they overflow it, since Phaser's wordWrap only wraps width, not the
    box height."""
    return text if len(text) <= max_len else text[: max_len - 1].rstrip() + "…"


def _task_category(agent_id: AgentId, task_label: str, override_reason: str | None) -> TaskCategory:
    if override_reason == "meeting":
        return "meeting"
    label = task_label.lower()
    for needle, category in _TASK_CATEGORY_KEYWORDS:
        if needle in label:
            return category
    return _DEFAULT_CATEGORY_BY_AGENT.get(agent_id, "documentation")


def _task_priority(agent_id: AgentId, location: str) -> TaskPriority:
    if location in RESTFUL_LOCATIONS or location == "meeting-room":
        return "low" if location != "meeting-room" else "high"
    return "high" if agent_id == "atlas" else "normal"


def _override_task_label(reason: str) -> str:
    return "In a meeting" if reason == "meeting" else "Taking a break"


def _replace_working_task(
    tasks: list[Task],
    agent_id: AgentId,
    category: TaskCategory,
    priority: TaskPriority,
    description: str,
    now: str,
    day: int,
    hour: int,
    minute: int,
) -> None:
    """Marks the agent's previous in-flight task completed and starts a
    new one. Shared by _tick_agent (schedule-driven task changes) and
    _maybe_call_meeting (a meeting starting is also a task change) so the
    "complete the old one, start the new one" bookkeeping lives in one
    place.

    An agent's override can end (schedule-driven task change via
    _tick_agent) and that same agent can be drawn into a brand-new meeting
    (_maybe_call_meeting) within the same tick — both call this function
    for the same agent/day/hour/minute, which would otherwise produce two
    Task objects with an identical id (a real bug: React keys collided on
    e.g. "task-scribe-1-17-20"). Disambiguate with a numeric suffix on
    collision rather than changing the id format for the common case."""
    for existing in tasks:
        if existing.owner == agent_id and existing.status == "working":
            existing.status = "completed"
            existing.completed_at = now
    base_id = f"task-{agent_id}-{day}-{hour}-{minute}"
    existing_ids = {t.id for t in tasks}
    task_id = base_id
    suffix = 2
    while task_id in existing_ids:
        task_id = f"{base_id}-{suffix}"
        suffix += 1
    tasks.append(
        Task(
            id=task_id,
            owner=agent_id,
            category=category,
            priority=priority,
            description=description,
            status="working",
            createdAt=now,
            completedAt=None,
        )
    )


def _default_agent_state(agent_id: AgentId) -> AgentState:
    profile = AGENT_PROFILES[agent_id]
    block = block_for_hour(agent_id, 8)
    return AgentState(
        transform=EntityTransform(scene=LOCATION_TO_SCENE[profile.home_location], x=100, y=80, facing="down"),
        location=profile.home_location,
        currentTask=block.task,
        mood=65,
        energy=80,
        memory=[],
        override=None,
    )


def default_agents() -> dict[AgentId, AgentState]:
    return {agent_id: _default_agent_state(agent_id) for agent_id in all_agent_ids()}


def register_agents(state: GameSaveState) -> GameSaveState:
    """Ensures every known agent id has a state entry — self-healing for saves from an older roster."""
    agents = dict(state.agents)
    changed = False
    for agent_id in all_agent_ids():
        if agent_id not in agents:
            agents[agent_id] = _default_agent_state(agent_id)
            changed = True
    return state.model_copy(update={"agents": agents}) if changed else state


def _tick_agent(
    agent_id: AgentId,
    agent: AgentState,
    new_time: TimeState,
    minutes: int,
    tasks: list[Task],
) -> AgentState:
    override_reason: str | None = None

    if agent.override is not None:
        remaining = agent.override.remaining_minutes - minutes
        if remaining <= 0:
            bonus = BREAK_ENERGY_BONUS if agent.override.reason == "break" else 0
            block = block_for_hour(agent_id, new_time.hour)
            location, task_label = block.location, block.task
            energy = min(100.0, agent.energy + bonus)
            override = None
        else:
            location = agent.override.location
            task_label = _override_task_label(agent.override.reason)
            override_reason = agent.override.reason
            energy = agent.energy
            override = agent.override.model_copy(update={"remaining_minutes": remaining})
    else:
        block = block_for_hour(agent_id, new_time.hour)
        location, task_label = block.location, block.task
        energy = agent.energy
        override = None

        if energy < BREAK_ENERGY_THRESHOLD and random.random() < BREAK_CHANCE_PER_TICK:
            override = AgentOverride(location="break-room", reason="break", remainingMinutes=BREAK_DURATION_MINUTES)
            location, task_label = override.location, _override_task_label(override.reason)
            override_reason = "break"

    energy_delta = 3 if location in RESTFUL_LOCATIONS else -1.5
    energy = min(100.0, max(5.0, energy + energy_delta))
    mood = min(100.0, max(5.0, agent.mood + random.uniform(-2, 2.5)))

    task_changed = task_label != agent.current_task
    memory = agent.memory
    if task_changed:
        memory = [
            *agent.memory,
            MemoryEntry(id=f"{agent_id}-{new_time.day}-{new_time.hour}-{new_time.minute}", summary=f"Started: {task_label}", day=new_time.day, hour=new_time.hour),
        ][-MAX_MEMORY:]
        now = _now_iso()
        category = _task_category(agent_id, task_label, override_reason)
        _replace_working_task(tasks, agent_id, category, _task_priority(agent_id, location), task_label, now, new_time.day, new_time.hour, new_time.minute)

    return agent.model_copy(
        update={
            "transform": agent.transform.model_copy(update={"scene": LOCATION_TO_SCENE[location]}),
            "location": location,
            # "current_task", not the "currentTask" wire alias — model_copy(update=...)
            # does not resolve aliases (see the Gotcha note at the bottom of this file).
            # Using the alias here silently froze every agent's currentTask at whatever
            # _default_agent_state() set it to, forever, while location kept updating
            # normally — caught via a raw WS probe showing Atlas stuck on "Reviewing
            # overnight strategy" through location changes across break/meeting cycles.
            "current_task": task_label,
            "mood": mood,
            "energy": energy,
            "memory": memory,
            "override": override,
        }
    )


def _maybe_call_meeting(
    agents: dict[AgentId, AgentState],
    meeting: MeetingState,
    research: list[ResearchItem],
    new_time: TimeState,
    news: list[NewsItem],
    tasks: list[Task],
    memory: list[MemoryRecord],
    meeting_minutes: list[MeetingMinutes],
) -> tuple[dict[AgentId, AgentState], MeetingState]:
    if meeting.active:
        still_meeting = [aid for aid in meeting.participants if (override := agents[aid].override) is not None and override.reason == "meeting"]
        if not still_meeting:
            minutes = build_minutes(meeting.participants, meeting.discussion, research, new_time)
            meeting_minutes.append(minutes)
            if len(meeting_minutes) > MAX_MEETING_MINUTES:
                del meeting_minutes[: len(meeting_minutes) - MAX_MEETING_MINUTES]
            record_meeting(memory, minutes)
            news.append(
                NewsItem(
                    id=f"news-meeting-end-{new_time.day}-{new_time.hour}-{new_time.minute}",
                    headline="The team wrapped up its meeting in the Meeting Room.",
                    category="company",
                    timestamp=_now_iso(),
                )
            )
            return agents, MeetingState(active=False, participants=[], discussion=[])
        return agents, meeting

    if random.random() >= MEETING_CHANCE_PER_TICK:
        return agents, meeting

    available = [aid for aid in all_agent_ids() if agents[aid].override is None]
    if len(available) < MEETING_MIN_ATTENDEES:
        return agents, meeting

    attendees = available if len(available) <= 4 else random.sample(available, k=random.randint(MEETING_MIN_ATTENDEES, len(available)))
    now = _now_iso()
    updated = dict(agents)
    for aid in attendees:
        updated[aid] = agents[aid].model_copy(
            update={
                "override": AgentOverride(location="meeting-room", reason="meeting", remainingMinutes=MEETING_DURATION_MINUTES),
                "location": "meeting-room",
                "current_task": "In a meeting",  # field name, not the "currentTask" alias — see Gotcha note.
                "transform": agents[aid].transform.model_copy(update={"scene": "MeetingRoomScene"}),
            }
        )
        _replace_working_task(tasks, aid, "meeting", "high", "In a meeting", now, new_time.day, new_time.hour, new_time.minute)

    discussion = generate_discussion(list(attendees), research, new_time.day, new_time.hour, new_time.minute)
    news.append(
        NewsItem(
            id=f"news-meeting-start-{new_time.day}-{new_time.hour}-{new_time.minute}",
            headline=f"Meeting called in the Meeting Room ({', '.join(AGENT_PROFILES[a].name for a in attendees)}).",
            category="company",
            timestamp=_now_iso(),
        )
    )
    return updated, MeetingState(active=True, participants=list(attendees), discussion=discussion)


def _trim_decisions(decisions: list[TradeDecision]) -> None:
    """In-place, oldest-first eviction down to MAX_DECISIONS — the fix for
    the uncapped-growth bug described on MAX_DECISIONS' own comment.
    In-place (unlike _trim_news' return-a-new-list style) because callers
    already hold a `decisions` reference they keep using afterward via
    closure, matching how MAX_TRADE_HISTORY/MAX_ORDER_LOG are trimmed
    elsewhere in this codebase."""
    if len(decisions) > MAX_DECISIONS:
        del decisions[: len(decisions) - MAX_DECISIONS]


def _trim_news(news: list[NewsItem]) -> list[NewsItem]:
    """Keep the most recent MAX_NEWS_PER_CATEGORY items per category
    instead of one global cap on the combined list, so a burst of
    discovery news can't evict every market/company headline. Relative
    chronological order is preserved."""
    counts: dict[str, int] = {}
    keep: list[NewsItem] = []
    for item in reversed(news):
        counts[item.category] = counts.get(item.category, 0) + 1
        if counts[item.category] <= MAX_NEWS_PER_CATEGORY:
            keep.append(item)
    keep.reverse()
    return keep


def _evaluate_trade_candidates(
    portfolio: PaperPortfolio,
    completed_research: list[ResearchItem],
    prices: dict[str, float],
    risk_limits: RiskLimits,
) -> tuple[PaperPortfolio, list[TradeDecision]]:
    """The v0.6 Decision Voting pipeline: every research item that just
    crossed FUTURE_TRADE_CONFIDENCE_THRESHOLD becomes a trade candidate,
    voted on by the four researcher agents plus Sentinel and Guardian
    (app/voting.py), then ruled on by Atlas (app/decision.py). An
    approved candidate places a market order (app/broker.py) — it does
    not open a position directly; that only happens once the order fills
    on a future tick, same one-tick latency every order has."""
    decisions: list[TradeDecision] = []
    for item in completed_research:
        if item.confidence < FUTURE_TRADE_CONFIDENCE_THRESHOLD or not item.symbol:
            continue
        price = prices.get(item.symbol)
        if price is None or price <= 0:
            continue
        quantity = recommended_quantity(risk_limits, portfolio, price)
        if quantity <= 0:
            continue

        sentinel_warning = evaluate_sentinel_risk(risk_limits, portfolio, symbol=item.symbol, proposed_value=quantity * price)
        guardian_warning = evaluate_guardian_exposure(risk_limits, portfolio, symbol=item.symbol)
        votes = collect_votes(
            symbol=item.symbol,
            confidence=item.confidence,
            originating_agent=item.assigned_agent,
            researcher_ids=RESEARCHER_IDS,
            sentinel_warning=sentinel_warning,
            guardian_warning=guardian_warning,
        )
        risk_summary = (
            sentinel_warning.message
            if sentinel_warning
            else guardian_warning.message
            if guardian_warning
            else f"{item.symbol} is within all of Sentinel's and Guardian's configured risk limits."
        )
        decision = decide_trade(decision_id=f"decision-{item.id}", item=item, votes=votes, risk_summary=risk_summary)

        if decision.outcome == "trade":
            order_id = f"order-{item.id}"
            portfolio = place_order(
                portfolio,
                order_id=order_id,
                symbol=item.symbol,
                side="buy",
                order_type="market",
                quantity=quantity,
                price=price,
                placed_by="atlas",
                reason=decision.final_reasoning,
                confidence=item.confidence,
            )
            decision = decision.model_copy(update={"order_id": order_id})

        decisions.append(decision)

    return portfolio, decisions


def _journal_closed_trades(portfolio: PaperPortfolio, trades: list[PaperTrade], decisions: list[TradeDecision]) -> tuple[PaperPortfolio, list[PaperTrade]]:
    """Stamps every trade that closed this tick with its TradeJournal
    fields (app/journal.py) and writes the stamped version back into
    trade_history — close_position() (app/portfolio.py) already appended
    the unstamped trade there, so this replaces it in place rather than
    appending a second copy. `decision_id` is attributed by best-effort
    match: the most recent "trade" decision for the same symbol, since
    neither PaperOrder nor PaperPosition carries a decision id through to
    the eventual PaperTrade."""
    if not trades:
        return portfolio, []

    stamped_by_id: dict[str, PaperTrade] = {}
    stamped: list[PaperTrade] = []
    for trade in trades:
        decision_id = next((d.id for d in reversed(decisions) if d.symbol == trade.symbol and d.outcome == "trade"), None)
        journaled = stamp_journal_entry(trade, decision_id=decision_id)
        stamped_by_id[trade.id] = journaled
        stamped.append(journaled)

    history = [stamped_by_id.get(t.id, t) for t in portfolio.trade_history]
    return portfolio.model_copy(update={"trade_history": history}), stamped


def _update_whiteboards(agents: dict[AgentId, AgentState], meeting: MeetingState, research: list[ResearchItem]) -> dict[str, str]:
    working = sum(1 for a in agents.values() if a.location not in RESTFUL_LOCATIONS)
    active_by_agent = {item.assigned_agent: item for item in research if item.status == "in_progress"}
    latest_discovery = next((item.summary for item in research if item.status == "completed"), "No discoveries logged yet.")

    def board_text(agent_id: AgentId) -> str:
        item = active_by_agent.get(agent_id)
        if item is None:
            return _truncate(agents[agent_id].current_task, 26)
        # Two short lines, not three — the in-world whiteboard prop is a
        # small fixed-size rectangle (see Whiteboard.ts), and this text is
        # only the at-a-glance summary anyway; the full title/confidence
        # detail already lives in the Brain Room HUD's Research Queue.
        return f"{_truncate(item.title, 26)}\n{item.priority.capitalize()} priority · {item.confidence:.0f}%"

    return {
        "scout-office": board_text("scout"),
        "meeting-room": "Meeting in progress" if meeting.active else board_text("atlas"),
        "ceo-office": f"{working}/{len(agents)} agents working\n{_truncate(latest_discovery, 30)}",
    }


def tick(state: GameSaveState, new_time: TimeState, minutes: int) -> GameSaveState:
    state = register_agents(state)
    tasks = list(state.tasks)
    news = list(state.news)
    memory = list(state.memory)
    meeting_minutes = list(state.meeting_minutes)
    research = state.research or default_research()
    watchlist = state.watchlist or default_watchlist()
    paper_portfolio = state.paper_portfolio
    strategies = state.strategies or default_strategies()
    backtest_sessions = list(state.backtest_sessions)
    simulation_results = list(state.simulation_results)
    hall_of_fame = list(state.hall_of_fame)
    coach_reports = list(state.coach_reports)
    performance_snapshots = list(state.performance_snapshots)
    risk_limits = state.risk_limits
    scanner_alerts = list(state.scanner_alerts)
    decisions = list(state.decisions)

    agents = {aid: _tick_agent(aid, agent, new_time, minutes, tasks) for aid, agent in state.agents.items()}

    research, completed = tick_research(research)
    record_research_completions(memory, completed)
    for item in completed:
        news.append(
            NewsItem(
                id=f"news-research-{item.id}",
                headline=f"{AGENT_PROFILES[item.assigned_agent].name} completed research on {item.symbol}: {item.summary}",
                category="discovery",
                timestamp=_now_iso(),
            )
        )

    watchlist = tick_watchlist(watchlist, research, market_data_provider)
    prices = {w.symbol: w.last_price for w in watchlist}

    # --- v0.6: Pulse's market scanner --------------------------------------
    # Runs off this tick's freshest watchlist prices, same as everything
    # else below. Every alert is memory-worthy; only the sharper moves
    # (gaps/breakouts) are worth a news headline too.
    scanner_alerts, new_scanner_alerts = tick_scanner(scanner_alerts, watchlist, market_data_provider)
    for alert in new_scanner_alerts:
        record_scanner_alert(memory, alert)
        if alert.alert_type in ("gap_up", "gap_down", "breakout"):
            news.append(
                NewsItem(
                    id=f"news-alert-{alert.id}",
                    headline=f"Pulse: {alert.message}",
                    category="market",
                    timestamp=_now_iso(),
                )
            )

    # --- v0.6: PaperBroker fills orders placed on earlier ticks -----------
    # Runs before this tick's own decision/order-placement step below, so
    # a market order approved this tick is guaranteed one full tick of
    # latency before it can fill (see app/broker.py's place_order()).
    paper_portfolio, broker_closed_trades = tick_broker(paper_portfolio, prices, new_time)

    # --- v0.6: Guardian's standing risk watch ------------------------------
    # Reflects the current portfolio, not an accumulating log — refreshed
    # every tick like company_score already is below.
    risk_warnings = monitor_portfolio(risk_limits, paper_portfolio)

    # --- v0.6: Decision Voting on this tick's freshly completed research --
    # Every high-confidence completion is a trade candidate; approved
    # candidates place an order (not a position — see app/broker.py).
    paper_portfolio, new_decisions = _evaluate_trade_candidates(paper_portfolio, completed, prices, risk_limits)
    for decision in new_decisions:
        record_decision(memory, decision)
        if decision.order_id is not None:
            order = next((o for o in paper_portfolio.orders if o.id == decision.order_id), None)
            if order is not None:
                record_order_placed(memory, order)
        news.append(
            NewsItem(
                id=f"news-decision-{decision.id}",
                headline=f"Atlas's decision on {decision.symbol}: {'TRADE APPROVED' if decision.outcome == 'trade' else 'NO TRADE'} — {decision.final_reasoning}",
                category="company",
                timestamp=_now_iso(),
            )
        )
    decisions = [*decisions, *new_decisions]

    # --- v0.5: paper trading + simulation lab -----------------------------
    # Both run after research/watchlist so they see this tick's freshest
    # confidence/price data, and before the meeting call so a just-closed
    # trade or completed simulation can be discussed in a meeting the same
    # tick it happens (matching how research completions already work).
    paper_portfolio, closed_trades = tick_paper_trading(paper_portfolio, watchlist, all_agent_ids(), new_time)
    paper_portfolio, closed_trades = _journal_closed_trades(paper_portfolio, [*broker_closed_trades, *closed_trades], decisions)
    # Trimmed after _journal_closed_trades (not right after the append
    # above) so a trade closing this very tick can still look its
    # originating decision up by id before the oldest entries are evicted.
    _trim_decisions(decisions)
    for trade in closed_trades:
        record_paper_trade(memory, trade)
        outcome = "gained" if trade.pnl > 0 else "lost"
        news.append(
            NewsItem(
                id=f"news-trade-{trade.id}",
                headline=f"Paper trade closed: {trade.symbol} {outcome} {abs(trade.pnl_pct):.1f}% (simulated — no real capital involved).",
                category="company",
                timestamp=_now_iso(),
            )
        )

    backtest_sessions, simulation_results, newly_completed_sims = tick_simulation_lab(
        backtest_sessions, simulation_results, strategies, watchlist, RESEARCHER_IDS, new_time
    )
    for result in newly_completed_sims:
        record_simulation_result(memory, result)
        news.append(
            NewsItem(
                id=f"news-sim-{result.id}",
                headline=f"Simulation complete: \"{result.strategy_name}\" on {result.symbol} returned {result.total_return_pct:+.1f}% (simulated).",
                category="discovery",
                timestamp=_now_iso(),
            )
        )

    agents, meeting = _maybe_call_meeting(agents, state.meeting, research, new_time, news, tasks, memory, meeting_minutes)

    if random.random() < 0.04:
        news.append(
            NewsItem(
                id=f"news-market-{new_time.day}-{new_time.hour}-{new_time.minute}",
                headline=random.choice(MARKET_HEADLINES),
                category="market",
                timestamp=_now_iso(),
            )
        )

    # --- v0.5: coaching, scoring, and performance analytics ---------------
    # Company score is cheap to recompute and feeds the Brain Room HUD's
    # live-updating readout, so it's refreshed every tick like mood/energy
    # already are — not just on the evening/weekly/monthly cadences below.
    company_score = compute_company_score(research, paper_portfolio, memory, simulation_results, [a.mood for a in agents.values()])

    is_evening = new_time.hour == EVENING_REVIEW_HOUR and new_time.minute == 0
    is_midnight = new_time.hour == 0 and new_time.minute == 0
    latest_report: CoachReport | None = None

    if is_evening and new_time.day % WEEKLY_INTERVAL_DAYS == 0:
        latest_report = generate_coach_report("weekly", research, paper_portfolio, company_score, RESEARCHER_IDS, new_time)
        coach_reports = record_coach_report_entry(coach_reports, latest_report)
        record_coach_report(memory, latest_report)
        performance_snapshots = record_snapshot(performance_snapshots, compute_performance_snapshot("weekly", paper_portfolio, research, new_time))

    if is_evening and new_time.day % MONTHLY_INTERVAL_DAYS == 0:
        latest_report = generate_coach_report("monthly", research, paper_portfolio, company_score, RESEARCHER_IDS, new_time)
        coach_reports = record_coach_report_entry(coach_reports, latest_report)
        record_coach_report(memory, latest_report)
        performance_snapshots = record_snapshot(performance_snapshots, compute_performance_snapshot("monthly", paper_portfolio, research, new_time))

    if is_midnight:
        performance_snapshots = record_snapshot(performance_snapshots, compute_performance_snapshot("daily", paper_portfolio, research, new_time))
        performance_snapshots = record_snapshot(performance_snapshots, compute_performance_snapshot("all_time", paper_portfolio, research, new_time))

    hof_before = len(hall_of_fame)
    hall_of_fame = evaluate_hall_of_fame(
        hall_of_fame,
        completed_research=completed,
        completed_simulations=newly_completed_sims,
        all_trades=paper_portfolio.trade_history,
        coach_report=latest_report,
        confidence_accuracy_value=confidence_accuracy(paper_portfolio.trade_history) if paper_portfolio.trade_history else None,
        new_time=new_time,
    )
    for entry in hall_of_fame[hof_before:]:
        record_hall_of_fame_entry(memory, entry)

    return state.model_copy(
        update={
            # NOTE: model_copy(update=...) writes directly into the model's
            # __dict__ and does NOT resolve field aliases (unlike normal
            # construction/validation) — every key here must be the actual
            # Python field name, not its camelCase wire alias, or the
            # update silently no-ops (the field keeps its old value, no
            # error). "meeting_minutes" and "updated_at" below previously
            # used their aliases ("meetingMinutes"/"updatedAt") and never
            # actually updated as a result — the same class of bug bit
            # "current_task" once more after that (see docs/Architecture.md's
            # Gotcha section), so every v0.5 key below was checked against
            # schemas.py's real field names before being added here.
            "time": new_time,
            "agents": agents,
            "tasks": tasks[-MAX_TASKS:],
            "news": _trim_news(news),
            "research": research,
            "watchlist": watchlist,
            "memory": memory,
            "meeting_minutes": meeting_minutes,
            "meeting": meeting,
            "paper_portfolio": paper_portfolio,
            "strategies": strategies,
            "backtest_sessions": backtest_sessions,
            "simulation_results": simulation_results,
            "hall_of_fame": hall_of_fame,
            "coach_reports": coach_reports,
            "company_score": company_score,
            "performance_snapshots": performance_snapshots,
            "risk_limits": risk_limits,
            "risk_warnings": risk_warnings,
            "scanner_alerts": scanner_alerts,
            "decisions": decisions,
            "whiteboards": _update_whiteboards(agents, meeting, research),
            "updated_at": _now_iso(),
        }
    )
