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

from app.academy import (
    ACADEMY_PROJECT_POINTS,
    MEETING_ATTENDANCE_POINTS,
    RESEARCH_COMPLETION_POINTS,
    award_points,
    compute_academy_state,
    default_agent_knowledge,
    maybe_run_mentorship,
    record_learning_event,
)
from app.academy_research import MAX_ACADEMY_LIBRARY, default_academy_projects, tick_academy_projects
from app.agent_energy import RESEARCH_BOOST_AMOUNT, regen_daily, spend
from app.agents import AGENT_PROFILES, LOCATION_TO_SCENE, all_agent_ids
from app.analytics import compute_performance_snapshot, confidence_accuracy, max_drawdown_pct, period_profit_dollars, record_snapshot
from app.behavioral_risk import compute_behavioral_check
from app.black_box import archive_project, default_black_box_state, generate_project_challenge, record_review as record_breakthrough_review, tick_black_box_daily
from app.broker import execution_provider
from app.calendar import compute_system_events
from app.capital_priority import cash_reserve_breached, priority_score, rank_trade_proposals
from app.coach import generate_report as generate_coach_report
from app.coach import record_report as record_coach_report_entry
from app.company_dna import ACADEMY_COMPLETION_NUDGE, BLACK_BOX_BREAKTHROUGH_NUDGE, FOUNDER_RETIREMENT_NUDGE, SUCCESS_STUDY_NUDGE, compute_company_dna, nudge_legacy
from app.company_health import compute_company_health, diff_company_health
from app.company_score import compute_company_score
from app.config import settings
from app.constitution import MISTAKE_ARTICLE_MAP, cite_article
from app.debate import generate_debate
from app.decision_vault import build_vault_entry, record_vault_entry
from app.devils_advocate import MAX_CHALLENGE_REPORTS, generate_challenge_report
from app.discipline import generate_discipline_review, record_review as record_discipline_review_entry
from app.discussion import generate_discussion
from app.executive import (
    MAX_CEO_DECISIONS,
    MAX_PENDING_PROPOSALS,
    expire_stale_proposals,
    generate_proposal,
    grade_ceo_decisions,
    is_significant_proposal,
    resolve_proposal,
)
from app.executive_intelligence import (
    compute_agent_vote_accuracy,
    compute_executive_accuracy_scores,
    compute_executive_recommendation,
    generate_department_opinions,
    generate_meeting_log_entry,
    generate_weekly_self_evaluations,
    record_meeting_log_entry,
    record_self_evaluations,
)
from app.weighted_decisions import compute_weighted_recommendation
from app.black_swan import (
    activate_defensive_mode,
    compute_black_swan_intelligence,
    compute_institutional_survival_score,
    deactivate_defensive_mode,
    generate_black_swan_report,
    generate_crisis_briefing,
    note_defensive_mode_peak_tier,
    record_black_swan_event,
    record_black_swan_report,
    tier_meets_or_exceeds,
)
from app.economic_intelligence import (
    compute_economic_intelligence,
    generate_economic_intelligence_report,
    record_economic_intelligence_report,
)
from app.executive_review import generate_executive_review, record_review
from app.board import generate_board_report, record_board_report
from app.founders import compute_founder_state, generate_breakthrough_review, generate_council_session, generate_founder_log_entry, record_council_session, record_founder_log
from app.goals import generate_strategic_review, record_strategic_review, tick_goals
from app.foundational_mentors import tick_employee_progress
from app.emergency_stop import activate_emergency_stop
from app.gatekeeper import MIN_CONFIDENCE as GATEKEEPER_MIN_CONFIDENCE, grade_gatekeeper_rejections
from app.trading_restrictions import find_blocking_restriction
from app.hall_of_fame import evaluate_hall_of_fame
from app.innovation import compute_innovation_state
from app.journal import stamp_journal_entry
from app.market_data import market_data_provider
from app.market_debate import generate_market_debate
from app.market_environment import tick_market_environment
from app.market_intelligence import (
    compute_market_intelligence_state,
    compute_strategy_match,
    filter_environment_entries_for_day,
    filter_trades_for_day,
    generate_learning_entry,
    generate_market_intelligence_report,
    record_learning_entry,
    record_market_intelligence_report,
)
from app.memory import MAX_MEMORY_RECORDS, record
from app.mentor import compute_mentor_state, compute_thinking_profiles, generate_question_of_the_day, record_question
from app.performance_review import compute_agent_performance_review, latest_review_for_agent, record_agent_performance_review
from app.skill_progression import compute_agent_skill_profile, latest_skill_profile_for_agent, record_agent_skill_profile
from app.prediction_tracking import MAX_PREDICTION_RECORDS, build_prediction_record, grade_predictions, should_promote_prediction_outcome
from app.failure_review import classify_failure, record_failure_classification, should_promote_failure_classification
from app.audit_log import compute_audit_log
from app.compliance_incidents import sync_incidents_from_audit_log
from app.override_governance import sync_override_evaluations, refresh_override_outcomes
from app.institutional_memory import (
    promote_case_study,
    promote_failure_classification,
    promote_market_regime_shift,
    promote_prediction_outcome,
    promote_risk_event,
    record_institutional_memory,
)
from app.mistakes import generate_case_studies, record_case_studies
from app.opportunity_gatekeeper import build_opportunity_rejection, evaluate_opportunity, grade_opportunity_rejections
from app.successes import generate_success_studies, record_success_studies
from app.self_improvement import maybe_propose_recurring_mistake, maybe_propose_reinforce_success_pattern, record_self_improvement_proposal
from app.evolution import compute_company_evolution_score, generate_institutional_evolution_report, record_evolution_report
from app.vision_board import compute_self_improvement_proposal_alignment
from app.talent import generate_talent_reports, record_talent_reports
from app.paper_trading import tick_paper_trading
from app.portfolio import sim_minutes
from app.portfolio_intelligence import compute_portfolio_intelligence, count_correlated_positions
from app.paper_trade_journal import build_journal_entry
from app.position_sizing import build_position_sizing
from app.reasoning_lab import compute_reasoning_lab_state, generate_challenge, record_challenge
from app.research import RESEARCHER_IDS, default_research, tick_research
from app.risk_engine import compute_daily_objective_status, compute_risk_budget_status, evaluate_guardian_exposure, evaluate_sentinel_risk, monitor_portfolio, portfolio_equity, recommended_quantity
from app.risk_contract import apply_risk_contract_scaling, evaluate_risk_contract_scaling, get_active_risk_contract
from app.sandbox import apply_review_decision, cap_strategy_reports, cap_strategy_reviews, generate_strategy_report, maybe_advance_after_research, maybe_advance_after_result
from app.strategy_drift import evaluate_strategy_drift
from app.strategy_health import evaluate_health_transition
from app.strategy_lab import (
    cap_strategy_health_assessments,
    cap_strategy_liquidity_validations,
    cap_strategy_monte_carlo_results,
    cap_strategy_regime_tests,
    compute_strategy_health,
    compute_strategy_regime_test,
    run_strategy_monte_carlo,
    validate_strategy_liquidity,
)
from app.trading_modes import (
    MAX_RECOVERY_BRIEFINGS,
    apply_circuit_breaker_tightening,
    assign_trading_style,
    build_circuit_breaker_tier_memory,
    circuit_breaker_confidence_bonus,
    compute_daily_circuit_breaker,
    compute_losing_streak,
    flatten_day_positions,
    generate_recovery_briefing,
)
from app.travel_mode import (
    apply_travel_mode_tightening,
    activate_travel_mode as _activate_travel_mode,
    should_auto_activate,
    travel_mode_confidence_bonus,
)
from app.memecoin_sniper import tick_sniper_engine
from app.scanner import tick_scanner
from app.schedule import ScheduleBlock, block_for_hour
from app.treasury import apply_monthly_savings_rules, record_monthly_report
from app.scribe import (
    FUTURE_TRADE_CONFIDENCE_THRESHOLD,
    build_minutes,
    record_academy_project,
    record_case_study,
    record_ceo_decision,
    record_coach_report,
    record_discipline_review,
    record_executive_review,
    record_hall_of_fame_entry,
    record_knowledge_tier_up,
    record_meeting,
    record_mentorship_session,
    record_paper_trade,
    record_reasoning_challenge,
    record_reflection_session,
    record_research_completions,
    record_scanner_alert,
    record_simulation_result,
)
from app.schemas import (
    AcademyProject,
    AgentId,
    AgentKnowledgeState,
    AgentVoteAccuracyScore,
    AgentOverride,
    AgentPerformanceReview,
    AgentSkillProfile,
    AgentState,
    BlackBoxState,
    CalendarState,
    CaseStudy,
    ComplianceIncident,
    CeoDecisionRecord,
    CeoOverrideEvaluation,
    PredictionRecord,
    ChallengeReport,
    BlackSwanEventRecord,
    BlackSwanReport,
    BoardReport,
    CoachReport,
    InstitutionalEvolutionReport,
    SelfImprovementProposal,
    CompanyPriority,
    Debate,
    DecisionVaultEntry,
    DefensiveModeState,
    DepartmentSelfEvaluation,
    DisciplineReview,
    DriftCategory,
    DriftEvent,
    DriftSeverity,
    EconomicIntelligenceReport,
    EntityTransform,
    ExecutiveDepartmentRole,
    ExecutiveMeetingLogEntry,
    ExecutiveReview,
    FailureClassification,
    FounderCouncilSession,
    FounderId,
    FounderLogEntry,
    GameSaveState,
    GatekeeperRejection,
    Goal,
    HallOfFameEntry,
    InnovationState,
    InstitutionalMemoryEntry,
    LearningEvent,
    MarketEnvironmentRegime,
    MarketIntelligenceLearningEntry,
    MarketIntelligenceReport,
    MarketIntelligenceState,
    MemoryEntry,
    MemoryRecord,
    MeetingMinutes,
    MeetingState,
    NewsItem,
    OpportunityRejection,
    PaperPortfolio,
    PaperTrade,
    PaperTradeJournalEntry,
    QuestionOfTheDay,
    ReasoningChallenge,
    ReflectionCadence,
    ReflectionSession,
    ResearchItem,
    RiskLimits,
    StrategicReview,
    StrategyHealthState,
    RiskWarning,
    ScannerAlert,
    TalentReport,
    TalentState,
    Task,
    TaskCategory,
    TaskPriority,
    ThinkingProfile,
    TimeState,
    TradeDecision,
    TradeProposal,
    DailyCircuitBreakerRead,
    LosingStreakRead,
    TradingModeState,
    TradingRestriction,
    TreasuryState,
    WarRoomSession,
    WeightProfile,
    WisdomState,
)
from app.simulation import default_strategies, queue_backtest_now, tick_simulation_lab
from app.war_room import PROPOSAL_CANDLE_COUNT as WAR_ROOM_CANDLE_COUNT
from app.war_room import PROPOSAL_TIMEFRAME as WAR_ROOM_TIMEFRAME
from app.war_room import build_war_room_session, compare_scenario_to_outcome, record_war_room_session
from app.watchlist import SYMBOL_CATEGORY, add_symbol_to_watchlist, default_watchlist, tick_watchlist
from app.wisdom import compute_wisdom_score, generate_reflection_session
from app.wisdom import record_session as record_reflection_session_entry

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
# CEO directive "...then Paper-Trade Journal + Drift Detection + Strategy
# Health State Machine" — one PaperTradeJournalEntry per closed trade,
# same real, permanent, ever-growing category and magnitude as
# MAX_DECISIONS above.
MAX_PAPER_TRADE_JOURNAL = 200
# Real per-(strategy, category) drift events, persisted only on an
# actual severity change (see app/strategy_drift.py) — never one row
# per tick, so this stays a meaningful timeline the same way
# MAX_MARKET_ENVIRONMENT_HISTORY's regime-change timeline does.
MAX_DRIFT_EVENTS = 200
# v0.7 Feature 17 — one Debate generated per new TradeProposal (see
# generate_debate below); capped the same way every other per-proposal
# record here is.
MAX_DEBATES = 60
# v0.7 Feature 20 — one GatekeeperRejection per trade the Gatekeeper
# vetoes (see app/state.py's submit_ceo_decision); capped the same way
# every other per-proposal record here is.
MAX_GATEKEEPER_REJECTIONS = 100
# v0.7 Chapter 58 — one OpportunityRejection per candidate the
# Opportunity Gatekeeper rejects before it ever became a real
# TradeProposal (see app/opportunity_gatekeeper.py); capped the same
# way every other per-proposal record here is.
MAX_OPPORTUNITY_REJECTIONS = 100
# v0.7 Feature 22 — one MarketEnvironmentEntry per real regime change
# (see app/market_environment.py) — a meaningful timeline stays small on
# its own, but still capped like every other history list here.
MAX_MARKET_ENVIRONMENT_HISTORY = 100
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
# v0.7 Feature 32 — "every in-game morning at 8:00 AM" (the brief's own
# wording), on the same exact-minute trigger shape as EVENING_REVIEW_HOUR
# above.
MORNING_QOTD_HOUR = 8
WEEKLY_INTERVAL_DAYS = 7
MONTHLY_INTERVAL_DAYS = 30
# Design Bible Chapter 70 Part 1 — the Board Report's own Quarterly
# cadence, the identical day % N shape WEEKLY/MONTHLY_INTERVAL_DAYS
# above already use.
QUARTERLY_INTERVAL_DAYS = 90
# Design Bible Chapter 74 Part 1 — the Academy Integration hook's one
# real, small points nudge per supporting agent when a CaseStudy/
# SuccessStudy is filed (see app/self_improvement.py's module docstring
# for why this is the one honest hook, not generated lesson content).
ACADEMY_CASE_STUDY_NUDGE = 1.0
# v0.7 Feature 25 — how often to check whether a real mentorship pairing
# qualifies (see app/academy.py's maybe_run_mentorship). Checked on the
# same evening cadence as everything else above, but only every 3 days —
# the gap between two agents' real knowledge points moves slowly, so
# checking every tick would either never fire or fire every tick once
# the gap crosses threshold, neither of which reads as a real "session".
MENTORSHIP_CHECK_INTERVAL_DAYS = 3
# v0.7 Feature 29 — how often the company runs a Reasoning Lab challenge
# from its most recent real AI Debate. Checked on the same evening
# cadence, more often than mentorship since "departments regularly
# participate" is the brief's own framing and a fresh real Debate is
# usually available well within this window.
REASONING_CHALLENGE_INTERVAL_DAYS = 2
# v0.7 Feature 39 — the Original Founders. A distinct hour from
# MORNING_QOTD_HOUR so a Founder's real log entry is never mistaken for
# Sage's own QuestionOfTheDay mechanic — a separate, alternating-by-day
# real reaction, not a shared one.
FOUNDER_LOG_HOUR = 10

# v0.7 Feature 34 — Company Priorities. Real, fixed multipliers applied
# to already-existing levers (see _effective_risk_limits() and the three
# award_points() call sites / the tick_research() call below) — never a
# new invented mechanic, just an existing one turned up or down.
PRIORITY_KNOWLEDGE_MULTIPLIER = 1.5  # "learning"
PRIORITY_RESEARCH_SPEED_MULTIPLIER = 1.5  # "research"
PRIORITY_RISK_TIGHTEN_FACTOR = 0.8  # "risk_reduction"


def _effective_risk_limits(limits: RiskLimits, priority: CompanyPriority) -> RiskLimits:
    """A derived, tightened copy used only at the points Sentinel/Guardian
    actually evaluate a trade candidate — never mutates or persists over
    the player's own configured RiskLimits (`state.risk_limits` itself is
    returned unchanged at the bottom of tick())."""
    if priority != "risk_reduction":
        return limits
    factor = PRIORITY_RISK_TIGHTEN_FACTOR
    return limits.model_copy(
        update={
            "max_position_pct": round(limits.max_position_pct * factor, 2),
            "max_daily_loss_pct": round(limits.max_daily_loss_pct * factor, 2),
            "max_drawdown_pct": round(limits.max_drawdown_pct * factor, 2),
            "max_open_positions": max(1, round(limits.max_open_positions * factor)),
            "max_sector_concentration_pct": round(limits.max_sector_concentration_pct * factor, 2),
            "risk_per_trade_pct": round(limits.risk_per_trade_pct * factor, 2),
        }
    )


MARKET_HEADLINES = [
    "Markets drift sideways in a quiet overnight session",
    "Analysts split on next move as volume thins",
    "Sector rotation continues into a second week",
    "Volatility index ticks lower for a third straight day",
    "Traders await fresh catalysts amid a slow news cycle",
]

# v0.7 Feature 22 — Market Environment Simulation's one real "the News
# desk reacts to conditions" hookup: the random per-tick market headline
# (see the random.random() < 0.04 roll below) is now chosen from the
# real *current* MarketEnvironmentRegime's own pool instead of one
# shared list, so the newspaper's flavor headlines stay consistent with
# whatever regime app/market_environment.py actually computed this tick
# — a real, deterministic dependency on the regime, not a fabricated
# "event." Sideways reuses MARKET_HEADLINES verbatim (the original pool
# was already written in a sideways/uncertain voice).
MARKET_HEADLINES_BY_REGIME: dict[str, list[str]] = {
    "bull": [
        "Broad rally extends as buyers keep stepping in on dips",
        "Risk appetite climbs; growth names lead the advance",
        "Another green session as momentum builds across sectors",
        "Bulls in control as indices push toward recent highs",
        "Optimism spreads through the desk as gains broaden out",
    ],
    "bear": [
        "Selling pressure persists as buyers stay on the sidelines",
        "Markets extend their slide on renewed growth concerns",
        "Red across the board as risk-off sentiment takes hold",
        "Bears keep the upper hand through another rough session",
        "Defensive positioning grows as the drawdown deepens",
    ],
    "sideways": MARKET_HEADLINES,
    "high_volatility": [
        "Wild swings dominate trading as volatility spikes",
        "Whipsaw price action leaves the desk on edge",
        "Sharp intraday reversals as uncertainty grips the tape",
        "Volatility index jumps as traders brace for more chop",
        "Erratic moves in both directions keep risk desks busy",
    ],
    "low_volatility": [
        "A notably quiet tape as ranges compress further",
        "Volatility index grinds to multi-week lows",
        "Trading desks report unusually calm conditions",
        "Narrow ranges persist as the market digests recent moves",
        "Low volume, low volatility — a holding-pattern session",
    ],
}

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
    "cio": "review",
    "sage": "coaching",
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


def _rest_block(agent_id: AgentId, new_time: TimeState) -> ScheduleBlock:
    """v0.7 Feature 37 — Rest Mode. Maps the real current clock onto the
    same real 10-hour off-hours span Feature 35 already authored per
    agent (20:00-24:00 wind-down/evening activity, 0:00-6:00 sleep) via a
    repeating cycle, so a CEO-triggered rest period shows genuine
    variety — wind-down, then evening activity, then sleep, then wind-down
    again — using only real, already-written per-agent content. This is a
    pure function of the real clock, not new per-agent state: no field
    tracks "how long has this agent been resting," since the mapping
    itself already repeats every 10 in-game hours."""
    minute_of_day = new_time.hour * 60 + new_time.minute
    cycle_minute = minute_of_day % 600
    rest_hour = 20 + cycle_minute // 60 if cycle_minute < 240 else (cycle_minute - 240) // 60
    return block_for_hour(agent_id, rest_hour)


def _effective_block(agent_id: AgentId, new_time: TimeState, resting: bool) -> ScheduleBlock:
    return _rest_block(agent_id, new_time) if resting else block_for_hour(agent_id, new_time.hour)


def _tick_agent(
    agent_id: AgentId,
    agent: AgentState,
    new_time: TimeState,
    minutes: int,
    tasks: list[Task],
    resting: bool = False,
) -> AgentState:
    override_reason: str | None = None

    if agent.override is not None:
        remaining = agent.override.remaining_minutes - minutes
        if remaining <= 0:
            bonus = BREAK_ENERGY_BONUS if agent.override.reason == "break" else 0
            block = _effective_block(agent_id, new_time, resting)
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
        block = _effective_block(agent_id, new_time, resting)
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
    resting: bool = False,
    max_memory_records: int = MAX_MEMORY_RECORDS,
) -> tuple[dict[AgentId, AgentState], MeetingState]:
    if meeting.active:
        still_meeting = [aid for aid in meeting.participants if (override := agents[aid].override) is not None and override.reason == "meeting"]
        if not still_meeting:
            minutes = build_minutes(meeting.participants, meeting.discussion, research, new_time)
            meeting_minutes.append(minutes)
            if len(meeting_minutes) > MAX_MEETING_MINUTES:
                del meeting_minutes[: len(meeting_minutes) - MAX_MEETING_MINUTES]
            record_meeting(memory, minutes, max_records=max_memory_records)
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

    # v0.7 Feature 37 — Rest Mode: "employees stop starting new work,"
    # but a meeting already under way (handled above) still finishes
    # naturally rather than being cut off mid-conversation.
    if resting:
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


def _generate_trade_proposals(
    trade_proposals: list[TradeProposal],
    completed_research: list[ResearchItem],
    prices: dict[str, float],
    risk_limits: RiskLimits,
    portfolio: PaperPortfolio,
    news: list[NewsItem],
    scanner_alerts: list[ScannerAlert],
    now_sim_minutes: int,
    market_intelligence: MarketIntelligenceState,
    agent_vote_accuracy: list[AgentVoteAccuracyScore],
    trading_restrictions: list[TradingRestriction] | None = None,
) -> list[TradeProposal]:
    """Feature 12 — the CEO Approval pipeline. Every research item that
    just crossed FUTURE_TRADE_CONFIDENCE_THRESHOLD becomes a TradeProposal
    (app/executive.py's generate_proposal(), six-agent analyst desk) and
    waits for the player's own buy/sell/wait call — it no longer
    auto-executes via a majority-vote decision. Skips a symbol that
    already has a pending proposal and stops once MAX_PENDING_PROPOSALS
    is reached, so a slow CEO doesn't get spammed with duplicates.

    `agent_vote_accuracy` (CEO directive "Professional Quant Trading
    Core," Phase B's per-agent learning follow-up) — the real, trailing
    per-agent directional accuracy computed once per tick from every
    already-resolved decision so far (app/executive_intelligence.py's
    compute_agent_vote_accuracy()), threaded straight through to
    generate_proposal() -> compute_confidence() so the Multi-Agent
    Agreement factor can weight each analyst's vote by their own real
    track record.

    `trading_restrictions` (CEO directive "Layered Kill Switches," see
    app/trading_restrictions.py) skips a research item whose symbol or
    whole category is currently restricted — the CEO never sees a
    proposal for it, the first of that module's two real enforcement
    points. `None`/empty behaves exactly as before this parameter
    existed."""
    pending_symbols = {p.symbol for p in trade_proposals}
    new_proposals: list[TradeProposal] = []
    for item in completed_research:
        if item.confidence < FUTURE_TRADE_CONFIDENCE_THRESHOLD or not item.symbol:
            continue
        if item.symbol in pending_symbols:
            continue
        if trading_restrictions and find_blocking_restriction(trading_restrictions, symbol=item.symbol, category=item.category):
            continue
        if len(trade_proposals) + len(new_proposals) >= MAX_PENDING_PROPOSALS:
            break
        price = prices.get(item.symbol)
        if price is None or price <= 0:
            continue
        quantity = recommended_quantity(risk_limits, portfolio, price)
        if quantity <= 0:
            continue

        sentinel_warning = evaluate_sentinel_risk(risk_limits, portfolio, symbol=item.symbol, proposed_value=quantity * price, sim_day=now_sim_minutes // 1440)
        guardian_warning = evaluate_guardian_exposure(risk_limits, portfolio, symbol=item.symbol)
        proposal = generate_proposal(
            item,
            quantity=quantity,
            price=price,
            news=news,
            scanner_alerts=scanner_alerts,
            sentinel_warning=sentinel_warning,
            guardian_warning=guardian_warning,
            provider=market_data_provider,
            now_sim_minutes=now_sim_minutes,
            portfolio=portfolio,
            risk_limits=risk_limits,
            market_intelligence=market_intelligence,
            agent_vote_accuracy=agent_vote_accuracy,
        )
        new_proposals.append(proposal)
        pending_symbols.add(item.symbol)

    return new_proposals


def _apply_operating_mode(
    operating_mode: str,
    trade_proposals: list[TradeProposal],
    debates: list[Debate],
    portfolio: PaperPortfolio,
    risk_limits: RiskLimits,
    risk_warnings: list[RiskWarning],
    prices: dict[str, float],
    now_sim_minutes: int,
    memory: list[MemoryRecord],
    decisions: list[TradeDecision],
    ceo_decisions: list[CeoDecisionRecord],
    prediction_records: list[PredictionRecord],
    gatekeeper_rejections: list[GatekeeperRejection],
    news: list[NewsItem],
    challenge_reports: list[ChallengeReport],
    coach_reports: list[CoachReport],
    meeting_log: list[ExecutiveMeetingLogEntry],
    decision_vault: list[DecisionVaultEntry],
    sim_day: int,
    market_intelligence: MarketIntelligenceState,
    war_room_sessions: list[WarRoomSession],
    market_environment_regime: MarketEnvironmentRegime,
    active_weight_profile: WeightProfile,
    custom_department_weights: dict[ExecutiveDepartmentRole, float],
    emergency_stop_active: bool = False,
    force_manual_review: bool = False,
    min_confidence_override: float | None = None,
    behavioral_cooldown_minutes: int | None = None,
    behavioral_size_increase_threshold_pct: float | None = None,
    trading_restrictions: list[TradingRestriction] | None = None,
) -> tuple[list[TradeProposal], PaperPortfolio, list[ExecutiveMeetingLogEntry]]:
    """v0.7 Feature 21 — Company Operating Modes. Learning Mode never
    calls this (every proposal stays pending, the pre-Feature-21
    default). Assisted Mode auto-resolves every non-"significant"
    proposal (see executive.is_significant_proposal) and leaves the rest
    pending for the CEO. Executive Mode auto-resolves nearly everything
    — "the player reviews reports, not individual trades" — except the
    same real safety constraints described below, which apply
    regardless of mode. Every auto-resolution is the exact same real
    resolve_proposal() call a genuine CEO click would make (Gatekeeper
    included), just tagged resolved_by="auto" for honest provenance —
    including the v0.7 Feature 50 Executive Meeting Log entry it now
    also generates, exactly like a real CEO decision does (see
    app/state.py's submit_ceo_decision).

    v0.7 Design Bible Chapter 59 — Capital Priority & Opportunity Cost
    Engine. `trade_proposals` arrives already ranked by Priority Score
    (see the caller's `rank_trade_proposals` call), so this loop works
    the queue top-down, honestly favoring higher-quality candidates when
    capital is limited rather than first-come-first-served. A proposal
    below the CEO's `minPriorityScore` floor is "significant" the same
    way a low-confidence one already is (Assisted Mode only — Executive
    Mode's whole point is auto-resolving everything not gated by a real
    safety constraint).

    Three real safety constraints apply in BOTH modes, never just a
    significance judgment, so none can be silently bypassed by
    choosing a more hands-off mode: once cash as a % of equity reaches
    the CEO's voluntary `capitalReservePct` reserve, further BUY
    proposals stay pending (mirroring Chapter 57's own hard
    `cashReservePct` floor, which likewise applies unconditionally); a
    real `pause_trading` recommendation (v0.7 Design Bible Chapter 66,
    AI Consensus Safety — 2+ departments actively oppose, or Market
    Intelligence reads avoid_trading — see
    app/executive_intelligence.py's compute_executive_recommendation())
    also keeps the proposal pending; and — Design Bible Chapter 67
    (TTOS) Part 3 — a CEO-triggered `emergency_stop_active` keeps every
    proposal pending, checked first since it's the CEO's own explicit
    override of every other signal here (see app/emergency_stop.py).
    All three are real, checkable facts, never a mode-dependent
    judgment call.

    `behavioral_cooldown_minutes`/`behavioral_size_increase_threshold_pct`
    — the CEO's own real Behavioral Circuit Breaker thresholds
    (TradingModeState), threaded straight through to every real
    resolve_proposal() call below so an auto-resolution is gated by
    exactly the same revenge-trading check a manual CEO click gets — no
    Operating Mode can bypass it (see app/gatekeeper.py's
    _behavioral_check, the Gatekeeper's own non-bypassable pure-AND)."""
    if operating_mode == "learning" or not trade_proposals:
        return trade_proposals, portfolio, meeting_log

    still_pending: list[TradeProposal] = []
    for proposal in trade_proposals:
        if emergency_stop_active:
            still_pending.append(proposal)
            continue

        # Design Bible Chapter 75 — Daily Circuit Breaker Tier 2+. Every
        # new proposal waits for manual CEO resolution regardless of
        # Operating Mode while a tier is active, the same real branch
        # this function already uses for Chapter 66's pause_trading.
        if force_manual_review:
            still_pending.append(proposal)
            continue

        score = priority_score(proposal, war_room_sessions)
        significant, reasons = is_significant_proposal(proposal, portfolio, risk_limits, risk_warnings, score)
        if operating_mode == "assisted" and significant:
            still_pending.append(proposal)
            continue

        if proposal.overall_recommendation == "buy" and cash_reserve_breached(portfolio, risk_limits):
            still_pending.append(proposal)
            continue

        # v0.7 Design Bible Chapter 66 — AI Consensus Safety. A real
        # pause_trading recommendation (2+ departments actively oppose,
        # or Market Intelligence reads avoid_trading — see
        # app/executive_intelligence.py's compute_executive_recommendation())
        # is a safety constraint, not a mode-dependent significance
        # judgment, so it applies in BOTH Assisted and Executive mode —
        # the same way the cash-reserve check above already does. This
        # closes the one real, precise gap Chapter 66's own research
        # found: the signal already existed (ExecutiveRecommendation.action),
        # nothing previously enforced it.
        # Design Bible Chapter 70 Part 3 addendum — the same real
        # Weighted Executive Decision Engine read app/state.py's
        # submit_ceo_decision computes for a manual CEO call, computed
        # here too so an auto-resolution (Assisted/Executive mode) is
        # gated by the exact same advisory-only Gatekeeper check — no
        # safety signal that applies to a CEO click should silently skip
        # an auto-resolution. Reuses the `opinions` this block already
        # had to compute for the pre-existing pause_trading check above,
        # rather than a second, redundant department-opinion pass.
        weighted_recommendation = None
        if proposal.overall_recommendation != "wait":
            pre_resolve_challenge_report = next((c for c in reversed(challenge_reports) if c.proposal_id == proposal.id), None)
            opinions = generate_department_opinions(proposal, pre_resolve_challenge_report, coach_reports, market_intelligence, decision_vault)
            raw_recommendation = compute_executive_recommendation(proposal, opinions)
            if raw_recommendation.action == "pause_trading":
                still_pending.append(proposal)
                continue
            accuracy_scores = compute_executive_accuracy_scores(meeting_log, ceo_decisions)
            weighted_recommendation = compute_weighted_recommendation(
                proposal.id,
                opinions,
                accuracy_scores,
                regime=market_environment_regime,
                profile=active_weight_profile,
                custom_weights=custom_department_weights,
                raw_action=raw_recommendation.action,
            )

        debate = next((d for d in reversed(debates) if d.proposal_id == proposal.id), None)
        portfolio, decision, record = resolve_proposal(
            proposal,
            proposal.overall_recommendation,
            portfolio=portfolio,
            risk_limits=risk_limits,
            current_price=prices.get(proposal.symbol),
            now_sim_minutes=now_sim_minutes,
            market_intelligence=market_intelligence,
            debate=debate,
            risk_warnings=risk_warnings,
            weighted_recommendation=weighted_recommendation,
            resolved_by="auto",
            min_confidence_override=min_confidence_override,
            behavioral_cooldown_minutes=behavioral_cooldown_minutes,
            behavioral_size_increase_threshold_pct=behavioral_size_increase_threshold_pct,
            trading_restrictions=trading_restrictions,
        )
        record_ceo_decision(memory, decision, max_records=risk_limits.max_memory_records)
        decisions.append(decision)
        ceo_decisions.append(record)
        new_prediction = build_prediction_record(decision, record, sim_day=sim_day)
        if new_prediction is not None:
            prediction_records.append(new_prediction)

        challenge_report = next((c for c in reversed(challenge_reports) if c.proposal_id == proposal.id), None)
        meeting_log = record_meeting_log_entry(
            meeting_log,
            generate_meeting_log_entry(proposal, decision, record.ceo_decision, challenge_report, coach_reports, market_intelligence, decision_vault, sim_day=sim_day, resolved_by="auto"),
        )

        verdict = decision.gatekeeper_verdict
        current_price = prices.get(proposal.symbol)
        if verdict is not None and not verdict.approved and current_price is not None:
            # v0.7 Feature 20 — same tracking a real player decision gets
            # (see app/state.py's submit_ceo_decision); an auto-resolved
            # trade can be vetoed exactly the same way.
            gatekeeper_rejections.append(
                GatekeeperRejection(
                    id=f"gkreject-{decision.id}",
                    proposalId=proposal.id,
                    symbol=proposal.symbol,
                    ceoChoice=proposal.overall_recommendation,
                    reasons=[f"{c.label}: {c.detail}" for c in verdict.checks if not c.passed],
                    reasonCodes=[c.code for c in verdict.checks if not c.passed and c.code is not None],
                    priceAtRejection=current_price,
                    rejectedSimMinutes=now_sim_minutes,
                    createdAt=_now_iso(),
                )
            )
            if len(gatekeeper_rejections) > MAX_GATEKEEPER_REJECTIONS:
                del gatekeeper_rejections[: len(gatekeeper_rejections) - MAX_GATEKEEPER_REJECTIONS]

        mode_label = "Executive Mode" if operating_mode == "executive" else "Assisted Mode"
        outcome_word = "approved" if decision.order_id is not None else "passed on"
        reason_text = f" ({'; '.join(reasons)})" if reasons else ""
        news.append(
            NewsItem(
                id=f"news-auto-decision-{decision.id}",
                headline=f"{mode_label}: the desk auto-{outcome_word} {proposal.overall_recommendation.upper()} on {proposal.symbol}{reason_text}.",
                category="company",
                timestamp=_now_iso(),
            )
        )

    return still_pending, portfolio, meeting_log


def _journal_closed_trades(portfolio: PaperPortfolio, trades: list[PaperTrade], decisions: list[TradeDecision]) -> tuple[PaperPortfolio, list[PaperTrade]]:
    """Stamps every trade that closed this tick with its TradeJournal
    fields (app/journal.py) and writes the stamped version back into
    trade_history — close_position() (app/portfolio.py) already appended
    the unstamped trade there, so this replaces it in place rather than
    appending a second copy. `decision_id` is derived deterministically
    from the trade's own real `proposal_id` (`f"decision-{proposal_id}"`,
    the same convention app/executive.py's resolve_proposal() uses to
    mint a TradeDecision.id from a TradeProposal.id) when the trade
    carries one. Falls back to the old best-effort match — the most
    recent "trade" decision for the same symbol — only for a trade with
    no `proposal_id` at all (opened through app/broker.py's manual-order
    fill path, which has no originating proposal, or closed before this
    field existed)."""
    if not trades:
        return portfolio, []

    stamped_by_id: dict[str, PaperTrade] = {}
    stamped: list[PaperTrade] = []
    for trade in trades:
        if trade.proposal_id is not None:
            decision_id: str | None = f"decision-{trade.proposal_id}"
        else:
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
    strategy_reports = list(state.strategy_reports)
    strategy_reviews = list(state.strategy_reviews)
    strategy_monte_carlo_results = list(state.strategy_monte_carlo_results)
    strategy_regime_tests = list(state.strategy_regime_tests)
    strategy_liquidity_validations = list(state.strategy_liquidity_validations)
    strategy_health_assessments = list(state.strategy_health_assessments)
    constitution_citations = list(state.constitution.citations)
    # v0.7 Feature 48 — Company DNA Legacy: a small, permanent, capped
    # per-trait delta nudged by real one-time/rare company events (see
    # app/company_dna.py's module docstring), layered on top of
    # company_dna's own fresh historical-average score every tick.
    company_dna_legacy = dict(state.company_dna_legacy)
    hall_of_fame = list(state.hall_of_fame)
    coach_reports = list(state.coach_reports)
    performance_snapshots = list(state.performance_snapshots)
    risk_limits = state.risk_limits
    company_priority: CompanyPriority = state.settings.company_priority
    # Design Bible Chapter 75 — Company Trading Modes & Institutional
    # Capital Protection (app/trading_modes.py).
    trading_mode_state: TradingModeState = state.trading_modes
    recovery_briefings = list(state.recovery_briefings)
    # Design Bible Chapter 73.5 — Mobile Command Center & Remote
    # Operations (app/travel_mode.py). Real, CEO-mutated posture — not
    # recomputed, same as trading_mode_state above.
    travel_mode = state.travel_mode
    emergency_stop = state.emergency_stop
    trading_restrictions = state.trading_restrictions
    is_new_sim_day = new_time.day != state.time.day
    # v0.7 Feature 37 — the Work Mode System. "rest" pauses new employee-
    # initiated work (research progress, new meetings, Academy training)
    # while every trading/risk system (paper_trading/broker/risk_engine/
    # scanner/gatekeeper) keeps running exactly as it always has, unaware
    # of work_mode entirely — see this module's own _rest_block() for how
    # resting agents' locations/tasks are computed.
    resting = state.settings.work_mode == "rest"
    effective_risk_limits = _effective_risk_limits(risk_limits, company_priority)
    knowledge_multiplier = PRIORITY_KNOWLEDGE_MULTIPLIER if company_priority == "learning" else 1.0
    research_speed_multiplier = PRIORITY_RESEARCH_SPEED_MULTIPLIER if company_priority == "research" else 1.0
    scanner_alerts = list(state.scanner_alerts)
    # CEO directive "TradeTown — Memecoin Sniper Agent." Paper-only,
    # simulated — see app/memecoin_sniper.py's own module docstring.
    sniper_candidates = list(state.sniper_candidates)
    sniper_positions = list(state.sniper_positions)
    sniper_trade_history = list(state.sniper_trade_history)
    sniper_leads = list(state.sniper_leads)
    sniper_lessons = list(state.sniper_lessons)
    sniper_risk_state = state.sniper_risk_state
    sniper_engine_config = state.sniper_engine_config
    decisions = list(state.decisions)
    trade_proposals = list(state.trade_proposals)
    ceo_decisions = list(state.ceo_decisions)
    paper_trade_journal: list[PaperTradeJournalEntry] = list(state.paper_trade_journal)
    drift_events: list[DriftEvent] = list(state.drift_events)
    strategy_health_states: dict[str, StrategyHealthState] = dict(state.strategy_health_states)
    # Real count of trades closed THIS tick, per attributed strategy —
    # the only real "new evidence" input app/strategy_health.py's
    # recovery-probation counter needs (see this tick's own drift/health
    # evaluation call, below the closed_trades loop).
    trades_closed_this_tick_by_strategy: dict[str, int] = {}
    # CEO directive "Features 26-30," Feature 29 — Prediction -> Outcome
    # Tracking (app/prediction_tracking.py).
    prediction_records: list[PredictionRecord] = list(state.prediction_records)
    debates: list[Debate] = list(state.debates)
    gatekeeper_rejections: list[GatekeeperRejection] = list(state.gatekeeper_rejections)
    opportunity_rejections: list[OpportunityRejection] = list(state.opportunity_rejections)
    agent_energy = state.agent_energy
    operating_mode = state.settings.operating_mode
    executive_reviews: list[ExecutiveReview] = list(state.executive_reviews)
    board_reports: list[BoardReport] = list(state.board_reports)
    academy_projects: list[AcademyProject] = state.academy_projects or default_academy_projects()
    academy_completed_projects: list[AcademyProject] = list(state.academy_completed_projects)
    # v0.7 Design Bible Chapter 64 — CEO-authored company goals.
    goals: list[Goal] = list(state.goals)
    # v0.7 Design Bible Chapter 64 (fifth pass) — the Strategic Review
    # Cycle's own real report history.
    strategic_reviews: list[StrategicReview] = list(state.strategic_reviews)
    agent_knowledge: dict[AgentId, AgentKnowledgeState] = state.agent_knowledge or default_agent_knowledge()
    discipline_reviews: list[DisciplineReview] = list(state.discipline_reviews)
    case_studies: list[CaseStudy] = list(state.case_studies)
    # CEO directive "Features 26-30," Feature 30 — the Failure Review
    # Board (app/failure_review.py).
    failure_classifications: list[FailureClassification] = list(state.failure_classifications)
    # CEO directive "Features 31-35," Feature 31 — the Compliance
    # Incident Resolution Engine (app/compliance_incidents.py). Synced
    # near the end of this tick, once every other list below has
    # reached its final value for the tick — see that sync call's own
    # comment further down.
    compliance_incidents: list[ComplianceIncident] = list(state.compliance_incidents)
    # CEO directive "Features 31-35," Feature 32 — CEO Override
    # Governance (app/override_governance.py). Synced/refreshed near the
    # end of this tick, same placement as compliance_incidents above.
    ceo_override_evaluations: list[CeoOverrideEvaluation] = list(state.ceo_override_evaluations)
    # CEO directive "Features 26-30," Feature 26 — Institutional Memory
    # 2.0 (app/institutional_memory.py).
    institutional_memory: list[InstitutionalMemoryEntry] = list(state.institutional_memory)
    # CEO Company Health + Live Market Realism directive, Section 3 —
    # one capped, permanent LearningEvent per real Knowledge-tier
    # crossing (see app/academy.py's award_points()).
    learning_events: list[LearningEvent] = list(state.learning_events)
    # CEO directive "Features 26-30," Feature 27 — Agent Performance
    # Reviews (app/performance_review.py).
    agent_performance_reviews: list[AgentPerformanceReview] = list(state.agent_performance_reviews)
    # CEO directive "Features 26-30," Feature 28 — Academy + Skill
    # Progression (app/skill_progression.py).
    agent_skill_profiles: list[AgentSkillProfile] = list(state.agent_skill_profiles)
    # Design Bible Chapter 74 — Self-Improvement Proposals and the
    # Institutional Evolution Engine (app/self_improvement.py,
    # app/evolution.py).
    self_improvement_proposals: list[SelfImprovementProposal] = list(state.self_improvement_proposals)
    evolution_reports: list[InstitutionalEvolutionReport] = list(state.evolution_reports)
    talent_reports: list[TalentReport] = list(state.talent.reports)
    challenge_reports: list[ChallengeReport] = list(state.challenge_reports)
    reasoning_challenges: list[ReasoningChallenge] = list(state.reasoning_challenges)
    reflection_sessions: list[ReflectionSession] = list(state.reflection_sessions)
    wisdom_state: WisdomState = state.wisdom_state
    question_archive: list[QuestionOfTheDay] = list(state.question_archive)
    founder_log: list[FounderLogEntry] = list(state.founder_state.log)
    founder_council_sessions: list[FounderCouncilSession] = list(state.founder_state.council_sessions)
    treasury: TreasuryState = state.treasury
    black_box: BlackBoxState = state.black_box or default_black_box_state()
    foundational_mentor_state = state.foundational_mentor_state
    # v0.7 Feature 50 (Part 2/3) — the Executive Meeting Log and Weekly
    # Self-Evaluation (app/executive_intelligence.py).
    meeting_log: list[ExecutiveMeetingLogEntry] = list(state.executive_meeting_log)
    self_evaluations: list[DepartmentSelfEvaluation] = list(state.department_self_evaluations)
    # v0.7 Feature 51 — Market Intelligence Department (app/market_intelligence.py).
    market_intelligence_reports: list[MarketIntelligenceReport] = list(state.market_intelligence_reports)
    market_intelligence_learning: list[MarketIntelligenceLearningEntry] = list(state.market_intelligence_learning)
    # Design Bible Chapter 71 — Economic Intelligence Center (app/economic_intelligence.py).
    economic_intelligence_reports: list[EconomicIntelligenceReport] = list(state.economic_intelligence_reports)
    # Design Bible Chapter 72 — Black Swan Intelligence & Resilience System (app/black_swan.py).
    black_swan_reports: list[BlackSwanReport] = list(state.black_swan_reports)
    black_swan_events: list[BlackSwanEventRecord] = list(state.black_swan_events)
    defensive_mode: DefensiveModeState = state.defensive_mode
    # v0.7 — the Decision Memory System's Decision Vault (app/decision_vault.py).
    decision_vault: list[DecisionVaultEntry] = list(state.decision_vault)
    # v0.7 Feature 55 — the Executive Decision Simulator's War Room (app/war_room.py).
    war_room_sessions: list[WarRoomSession] = list(state.war_room_sessions)

    agents = {aid: _tick_agent(aid, agent, new_time, minutes, tasks, resting=resting) for aid, agent in state.agents.items()}

    # v0.7 Feature 37 — Rest Mode pauses new research progress ("employees
    # stop starting new work"); already-completed items stay completed,
    # and whatever confidence an in-progress item had simply holds until
    # Work Mode resumes.
    research, completed = (research, []) if resting else tick_research(research, speed_multiplier=research_speed_multiplier, watchlist=watchlist)
    record_research_completions(memory, completed, max_records=effective_risk_limits.max_memory_records)
    for item in completed:
        news.append(
            NewsItem(
                id=f"news-research-{item.id}",
                headline=f"{AGENT_PROFILES[item.assigned_agent].name} completed research on {item.symbol}: {item.summary}",
                category="discovery",
                timestamp=_now_iso(),
            )
        )
        # v0.7 Feature 25 — every real completed research item earns the
        # assigned agent real Knowledge Points (app/academy.py).
        agent_knowledge, learning_event = award_points(
            agent_knowledge, item.assigned_agent, RESEARCH_COMPLETION_POINTS * knowledge_multiplier, source="research_completion"
        )
        if learning_event is not None:
            record_knowledge_tier_up(memory, learning_event, max_records=effective_risk_limits.max_memory_records)
            learning_events = record_learning_event(learning_events, learning_event)

    # v0.7 Feature 45 — the Research Sandbox. An "idea"-stage strategy
    # advances to "research" the moment real completed research backs its
    # own focus_category — checked every tick against the full research
    # list (not just what completed this tick), since a strategy can be
    # created after the qualifying research already landed.
    strategies = [maybe_advance_after_research(s, research, new_time.day) if s.stage == "idea" else s for s in strategies]

    # v0.7 Feature 25 — the Academy's one company-wide knowledge project,
    # advanced and rotated the same way research.py's own queue is.
    # v0.7 Feature 37 — Rest Mode pauses this too ("Training continues"
    # is a Work Mode-only bullet in the brief).
    academy_projects, newly_completed_project = (academy_projects, None) if resting else tick_academy_projects(academy_projects, len(academy_completed_projects))
    if newly_completed_project is not None:
        academy_completed_projects.append(newly_completed_project)
        if len(academy_completed_projects) > MAX_ACADEMY_LIBRARY:
            del academy_completed_projects[: len(academy_completed_projects) - MAX_ACADEMY_LIBRARY]
        record_academy_project(memory, newly_completed_project, max_records=effective_risk_limits.max_memory_records)
        agent_knowledge, learning_event = award_points(
            agent_knowledge, newly_completed_project.assigned_agent, ACADEMY_PROJECT_POINTS * knowledge_multiplier, source="academy_project"
        )
        if learning_event is not None:
            record_knowledge_tier_up(memory, learning_event, max_records=effective_risk_limits.max_memory_records)
            learning_events = record_learning_event(learning_events, learning_event)
        news.append(
            NewsItem(
                id=f"news-academy-{newly_completed_project.id}",
                headline=f'Academy: {AGENT_PROFILES[newly_completed_project.assigned_agent].name} completes "{newly_completed_project.title}" — knowledge library updated.',
                category="company",
                timestamp=_now_iso(),
            )
        )
        # v0.7 Feature 46 — "Academy explains it": a completed Academy
        # project is a direct, literal instance of Article VIII.
        constitution_citations = cite_article(constitution_citations, "VIII", "academy", f'"{newly_completed_project.title}" completed by {AGENT_PROFILES[newly_completed_project.assigned_agent].name}.', new_time.day)
        # v0.7 Feature 48 — a completed Academy project is real evidence
        # of institutional research effort: a small, permanent Legacy
        # nudge to Company DNA's Research Rigor.
        company_dna_legacy = nudge_legacy(company_dna_legacy, "research_rigor", ACADEMY_COMPLETION_NUDGE)

    # v0.7 Feature 49 (Phase 3 revision) — the Foundational Mentor
    # Program / Professional Academy. Employees are the real students —
    # see app/foundational_mentors.py's module docstring. Rest Mode
    # pauses this too, same reasoning as the Academy project tick above.
    if not resting:
        foundational_mentor_state, newly_pending_graduations = tick_employee_progress(foundational_mentor_state, discipline_reviews=discipline_reviews, sim_day=new_time.day)
        for agent_id in newly_pending_graduations:
            news.append(
                NewsItem(
                    id=f"news-academy-grad-pending-{agent_id}-{foundational_mentor_state.active_mentor_id}-{new_time.day}",
                    headline=f"Academy: {AGENT_PROFILES[agent_id].name} has completed the {foundational_mentor_state.active_mentor_id} track — awaiting CEO graduation approval.",
                    category="company",
                    timestamp=_now_iso(),
                )
            )

    watchlist = tick_watchlist(watchlist, research, market_data_provider)
    prices = {w.symbol: w.last_price for w in watchlist}

    # --- v0.7 Feature 51: Market Intelligence Department -------------------
    # Recomputed fresh every tick, before any proposal is generated below —
    # "the company's eyes," the same real-data-every-tick convention
    # market_environment/company_health already use. See
    # app/market_intelligence.py's module docstring for the full honesty
    # boundary (real technical analysis over real mock OHLCV data, named
    # proxies where this codebase has no real order-flow/news-calendar
    # source, nothing fabricated).
    market_intelligence = compute_market_intelligence_state(watchlist, news, market_intelligence_reports, market_data_provider)

    # --- v0.6: Pulse's market scanner --------------------------------------
    # Runs off this tick's freshest watchlist prices, same as everything
    # else below. Every alert is memory-worthy; only the sharper moves
    # (gaps/breakouts) are worth a news headline too.
    scanner_alerts, new_scanner_alerts = tick_scanner(scanner_alerts, watchlist, market_data_provider)
    for alert in new_scanner_alerts:
        record_scanner_alert(memory, alert, max_records=effective_risk_limits.max_memory_records)
        if alert.alert_type in ("gap_up", "gap_down", "breakout"):
            news.append(
                NewsItem(
                    id=f"news-alert-{alert.id}",
                    headline=f"Pulse: {alert.message}",
                    category="market",
                    timestamp=_now_iso(),
                )
            )

    # --- Memecoin Sniper specialist (paper-only, simulated) ---------------
    # Real, independent domain — see app/memecoin_sniper.py's own module
    # docstring for why every candidate/position/trade/lead this produces
    # is honestly labeled `dataProvenance: "simulated"`. Only mutates
    # state when the CEO has set the engine to "running"/"paused" via the
    # sniper API — "stopped" (the default) leaves every list untouched.
    sniper_tick_result = tick_sniper_engine(
        sniper_engine_config,
        sniper_risk_state,
        sniper_candidates,
        sniper_positions,
        sniper_trade_history,
        sniper_leads,
        sniper_lessons,
        tick_seconds=settings.tick_interval_seconds,
    )
    sniper_candidates = sniper_tick_result.candidates
    sniper_positions = sniper_tick_result.positions
    sniper_trade_history = sniper_tick_result.trade_history
    sniper_leads = sniper_tick_result.leads
    sniper_lessons = sniper_tick_result.lessons
    sniper_risk_state = sniper_tick_result.risk_state

    # --- v0.6: PaperBroker fills orders placed on earlier ticks -----------
    # Runs before this tick's own decision/order-placement step below, so
    # a market order approved this tick is guaranteed one full tick of
    # latency before it can fill (see app/broker.py's place_order()).
    paper_portfolio, broker_closed_trades = execution_provider.tick_broker(
        paper_portfolio, prices, new_time, effective_risk_limits, market_intelligence
    )

    # --- v0.6: Guardian's standing risk watch ------------------------------
    # Reflects the current portfolio, not an accumulating log — refreshed
    # every tick like company_score already is below.
    risk_warnings = monitor_portfolio(risk_limits, paper_portfolio)
    # v0.7 Feature 46 — "Risk Department enforces it": cite Article
    # I/VII the moment a genuinely NEW critical warning appears (not
    # already on the previous tick's watch), so this never fires on
    # every tick a warning happens to still be standing.
    previous_warning_ids = {w.id for w in state.risk_warnings}
    for warning in risk_warnings:
        if warning.severity == "critical" and warning.id not in previous_warning_ids:
            constitution_citations = cite_article(constitution_citations, "I", "risk_department", warning.message, new_time.day)
            constitution_citations = cite_article(constitution_citations, "VII", "risk_department", warning.message, new_time.day)
            # Feature 26 — only a genuinely NEW critical warning is
            # promoted, the same real "not already on the previous
            # tick's watch" gate as the Article citations right above,
            # so a standing warning that persists across many ticks
            # never floods institutional memory with duplicates.
            institutional_memory = record_institutional_memory(
                institutional_memory, promote_risk_event(warning, sim_day=new_time.day), current_sim_day=new_time.day
            )

    # --- v0.6.3 Feature 12: CEO Approval pipeline --------------------------
    # Every high-confidence research completion becomes a TradeProposal
    # awaiting the player's own buy/sell/wait call (app/executive.py) — it
    # no longer auto-executes via a majority-vote decision. A proposal the
    # CEO never acts on expires after PROPOSAL_EXPIRY_SIM_MINUTES and is
    # auto-resolved as an honest "wait" (still a real, permanent
    # TradeDecision — see resolve_proposal), not silently dropped.
    now_sim_minutes = sim_minutes(new_time)

    # --- v0.7 Feature 22: Market Environment Simulation --------------------
    # Recomputed every tick from this tick's freshest watchlist (the same
    # real signal every other live reading here already uses) — only
    # appends to the timeline, and only then publishes a real news
    # headline, on an actual regime change (see market_environment.py).
    market_environment, environment_changed = tick_market_environment(state.market_environment, watchlist, now_sim_minutes)
    if len(market_environment.timeline) > MAX_MARKET_ENVIRONMENT_HISTORY:
        market_environment = market_environment.model_copy(update={"timeline": market_environment.timeline[-MAX_MARKET_ENVIRONMENT_HISTORY:]})
    # CEO Company Health + Live Market Realism directive — the real,
    # already-computed regime feeds back into the same provider's own
    # price generation (see market_data.py's own docstring for the full
    # two-way coupling this is one half of). One-tick lag by
    # construction: this tick's regime was classified from watchlist
    # quotes already generated before this point, so it can only bias
    # the *next* real quote/candle generation, never retroactively
    # rewrite the quotes that produced it.
    market_data_provider.set_market_regime(market_environment.current)
    if environment_changed:
        news.append(
            NewsItem(
                id=f"news-environment-{market_environment.current}-{now_sim_minutes}",
                headline=f"Market conditions shift: the desk now reads {market_environment.label}. {market_environment.detail}",
                category="market",
                timestamp=_now_iso(),
            )
        )
        # Feature 26 — the same real regime-change entry the news
        # headline above was just built from, promoted into
        # institutional memory so a future decision can weigh "setups
        # from a different regime shouldn't be assumed reliable here."
        latest_regime_entry = market_environment.timeline[-1]
        institutional_memory = record_institutional_memory(
            institutional_memory,
            promote_market_regime_shift(
                regime=latest_regime_entry.regime,
                label=latest_regime_entry.label,
                detail=latest_regime_entry.detail,
                event_ref=latest_regime_entry.id,
                sim_day=new_time.day,
            ),
            current_sim_day=new_time.day,
        )

    # Design Bible Chapter 75 — Company Trading Modes & Institutional
    # Capital Protection. Day-position flattening runs once per real
    # sim-day rollover, before this tick's Circuit Breaker read (a
    # flattened position's realized P&L is part of *today's* real daily
    # number the breaker checks next).
    #
    # CEO directive "Next Phase: Professional Trading Firm Intelligence,"
    # Phase 2 (Decision Vault coverage expansion) — RESEARCH FINDING: a
    # flattened trade previously never reached _journal_closed_trades()
    # below (only the memory alert a few lines down read it), so it never
    # got a decision_id, a DisciplineReview, a CaseStudy, a Failure
    # Review classification, or a DecisionVaultEntry — every other real
    # close path (hold-duration, and the broker order-book path, which a
    # grep-confirmed audit found has zero live callers today) already
    # flowed through that pipeline. `flattened_trades` is now merged into
    # the same real closed-trade list a few lines below so a day-end
    # flatten gets the exact same real learning-loop treatment as every
    # other close — no new pipeline built, the existing one just wasn't
    # being fed this real data.
    flattened_trades: list[PaperTrade] = []
    if is_new_sim_day:
        paper_portfolio, flattened_trades = flatten_day_positions(
            paper_portfolio, prices, now_sim_minutes, effective_risk_limits, market_intelligence
        )
        if flattened_trades:
            record(
                memory,
                "alert",
                "Day Trading Mode — positions flattened",
                f"{len(flattened_trades)} open day-tagged position(s) force-closed at day-end per Day Trading discipline.",
                max_records=risk_limits.max_memory_records,
            )

    daily_circuit_breaker: DailyCircuitBreakerRead = compute_daily_circuit_breaker(risk_limits, trading_mode_state, paper_portfolio, new_time.day)
    circuit_breaker_memory = build_circuit_breaker_tier_memory(state.daily_circuit_breaker.tier, daily_circuit_breaker.tier, daily_circuit_breaker.daily_pnl_pct, _now_iso())
    if circuit_breaker_memory is not None:
        memory = [*memory, circuit_breaker_memory]
        if len(memory) > risk_limits.max_memory_records:
            del memory[: len(memory) - risk_limits.max_memory_records]
    effective_risk_limits = apply_circuit_breaker_tightening(effective_risk_limits, daily_circuit_breaker.tier)

    # Design Bible Chapter 73.5 — Travel Mode. Composes into the same
    # derived-override seam as the Circuit Breaker above (never a
    # fourth, independent tightening mechanic — see
    # app/travel_mode.py's module docstring). Inactivity-based
    # automatic activation is checked once per tick, off the real
    # last_ceo_decision_sim_minutes timestamp app/state.py bumps on
    # every real CEO action.
    if should_auto_activate(travel_mode, travel_mode.last_ceo_decision_sim_minutes, now_sim_minutes):
        travel_mode, travel_mode_memory = _activate_travel_mode(
            travel_mode, source="auto_inactivity", now_iso=_now_iso(), now_sim_minutes=now_sim_minutes
        )
        memory = [*memory, travel_mode_memory]
        if len(memory) > risk_limits.max_memory_records:
            del memory[: len(memory) - risk_limits.max_memory_records]
    effective_risk_limits = apply_travel_mode_tightening(effective_risk_limits, travel_mode)

    confidence_bonus = max(circuit_breaker_confidence_bonus(daily_circuit_breaker.tier), travel_mode_confidence_bonus(travel_mode))
    min_confidence_override = (GATEKEEPER_MIN_CONFIDENCE + confidence_bonus) if confidence_bonus > 0 else None
    force_manual_review = daily_circuit_breaker.tier in ("tier2", "tier3")
    block_new_proposals = daily_circuit_breaker.tier in ("tier3", "tier4")

    losing_streak: LosingStreakRead
    losing_streak, trading_mode_state = compute_losing_streak(trading_mode_state, paper_portfolio.trade_history)
    if losing_streak.pause_active:
        block_new_proposals = True

    # CEO directive "TradeTown — Persisted Risk Contract + Dynamic Risk
    # Scaling," Phase 3/4 — composes into the SAME real narrowing chain
    # as Company Priority/Circuit-Breaker/Travel-Mode above (never a
    # fourth, independent tightening mechanic, never a second gate).
    # Reads the SAME real app/analytics.py::max_drawdown_pct() figure
    # Sentinel/Guardian/the Gatekeeper's failure-boundary check already
    # use, and the SAME real compute_losing_streak() count just above —
    # never a second drawdown or streak computation. `active_risk_
    # contract` is guaranteed non-None by app/state.py's own
    # `_advance_once()` (which derives one before ever calling this
    # function) for every real tick; the defensive `is not None` guard
    # below only matters for a direct unit-test call to `tick()` that
    # skips that guarantee — never crashes, simply skips this one real
    # narrowing step, matching every other optional-evidence cap's own
    # fail-open convention in this codebase (app/position_sizing.py).
    active_risk_contract = get_active_risk_contract(state.risk_contracts)
    risk_contract_scaling = None
    if active_risk_contract is not None:
        live_drawdown_pct = max_drawdown_pct(paper_portfolio.trade_history, paper_portfolio.starting_balance, current_equity=portfolio_equity(paper_portfolio))
        risk_contract_scaling = evaluate_risk_contract_scaling(
            contract=active_risk_contract,
            drawdown_pct=live_drawdown_pct,
            consecutive_losses=losing_streak.consecutive_losses,
            base_risk_per_trade_pct=effective_risk_limits.risk_per_trade_pct,
            base_max_position_pct=effective_risk_limits.max_position_pct,
        )
        effective_risk_limits = apply_risk_contract_scaling(effective_risk_limits, scaling=risk_contract_scaling)
        if risk_contract_scaling.kill_switch_triggered:
            block_new_proposals = True

    # Behavioral Circuit Breaker (app/behavioral_risk.py) — the ambient,
    # tick-level dashboard read (no specific candidate proposal to
    # corroborate against yet, so this can never reach "triggered" —
    # only the real per-proposal Gatekeeper check below can). Never
    # blocks new proposal generation on its own; the real enforcement is
    # the Gatekeeper's tenth check (app/gatekeeper.py::_behavioral_check),
    # evaluated per-proposal inside resolve_proposal() above/below.
    behavioral_circuit_breaker = compute_behavioral_check(
        None, paper_portfolio.trade_history, now_sim_minutes, trading_mode_state.behavioral_cooldown_minutes, trading_mode_state.behavioral_size_increase_threshold_pct
    )

    # Design Bible Chapter 72 — Black Swan Intelligence & Resilience
    # System. Defensive Mode's own recommendation
    # (build_defensive_recommendations(), "Pause New Entries") has always
    # documented and UI-labeled this as automatic — this is the real
    # enforcement that claim was missing (confirmed absent by a live
    # reproduction: activating Defensive Mode and running a tick produced
    # new proposals anyway). Reads defensive_mode as it stood at the
    # start of this tick (state.defensive_mode, captured above) — the
    # same real, persisted CEO/auto-activated flag every other
    # defensive_mode read in this function already uses, never a second
    # copy.
    if defensive_mode.active:
        block_new_proposals = True

    trigger_emergency_stop = not emergency_stop.active and (
        daily_circuit_breaker.tier == "tier4" or losing_streak.consecutive_losses >= trading_mode_state.losing_streak_suspend_count
    )
    # Design Bible Chapter 70 Part 1 — the second of the two real
    # Emergency Board Meeting triggers this chapter's research
    # confirmed. company_health/black_swan_intelligence aren't computed
    # until later in this same tick, so only the trigger text is
    # captured here; the actual BoardReport is generated further down,
    # right alongside the Black Swan tier crossing's own emergency
    # report (see below).
    emergency_stop_board_trigger_detail: str | None = None
    if trigger_emergency_stop:
        trigger: str = "circuit_breaker_tier4" if daily_circuit_breaker.tier == "tier4" else "losing_streak"
        emergency_stop, _ = activate_emergency_stop(emergency_stop, now_iso=_now_iso())
        trigger_detail = (
            "the Daily Circuit Breaker reaching Tier 4" if trigger == "circuit_breaker_tier4" else f"{losing_streak.consecutive_losses} consecutive losing trades"
        )
        emergency_stop_board_trigger_detail = f"Emergency Stop activated — {trigger_detail}"
        record(
            memory,
            "emergency",
            "Emergency Stop activated",
            f"Automatically triggered by {trigger_detail} — not a CEO click. Research, monitoring, and dashboards continue; only the CEO can resume trading.",
            max_records=risk_limits.max_memory_records,
        )
        recovery_briefings = [
            *recovery_briefings,
            generate_recovery_briefing(trigger, paper_portfolio, discipline_reviews, new_time.day, f"recovery-{trigger}-{now_sim_minutes}"),
        ]
        if len(recovery_briefings) > MAX_RECOVERY_BRIEFINGS:
            del recovery_briefings[: len(recovery_briefings) - MAX_RECOVERY_BRIEFINGS]
        block_new_proposals = True

    # v0.7 Feature 34 — "risk_reduction" biases new-proposal sizing/vetting
    # toward the tightened effective_risk_limits; every other real reading
    # of risk_limits (Guardian's ambient risk_warnings, the RiskPanel
    # display) keeps showing the player's own actually-configured numbers,
    # never the priority-derived ones, so nothing displayed misattributes
    # a threshold the player didn't set.
    # Design Bible Chapter 67 (TTOS) Part 3 — Emergency Stop blocks new
    # trade proposal generation entirely (existing pending proposals are
    # handled by _apply_operating_mode()'s own emergency_stop_active
    # check below; research/monitoring above this line are untouched).
    # Design Bible Chapter 75 — the Daily Circuit Breaker's Tier 3/4 and
    # an active Losing Streak pause, and Chapter 72 — an active
    # Defensive Mode, block new proposal generation the
    # same real way.
    # CEO directive "Professional Quant Trading Core," Phase B's per-agent
    # learning follow-up — the real, trailing per-agent directional
    # accuracy computed fresh each tick from every already-resolved
    # decision so far (never this tick's own still-unresolved proposals,
    # so a decision's own outcome can never leak into its own weight —
    # the same causal ordering app/weighted_decisions.py's department-
    # level accuracy multiplier already relies on).
    agent_vote_accuracy = compute_agent_vote_accuracy(decisions, ceo_decisions)
    candidate_proposals = (
        []
        if (emergency_stop.active or block_new_proposals)
        else _generate_trade_proposals(
            trade_proposals,
            completed,
            prices,
            effective_risk_limits,
            paper_portfolio,
            news,
            scanner_alerts,
            now_sim_minutes,
            market_intelligence,
            agent_vote_accuracy,
            trading_restrictions,
        )
    )
    # v0.7 Design Bible Chapter 58 — the Institutional Trade Filter &
    # Opportunity Gatekeeper. Every candidate above is only a raw,
    # confidence-filtered TradeProposal so far — this loop builds its
    # full committee/War Room evaluation (unchanged from before this
    # chapter) and then decides, using that same real Decision Score and
    # Expected Value, whether it earns the right to become CEO-visible
    # at all. Rejected candidates never enter `trade_proposals`, never
    # get a Debate, and never keep a Challenge Report or WarRoomSession
    # on the permanent record — see app/opportunity_gatekeeper.py's own
    # module docstring for why the (already-computed) War Room session
    # is built before the gate runs rather than a second, lighter-weight
    # pre-check.
    new_proposals: list[TradeProposal] = []
    for proposal in candidate_proposals:
        # v0.7 Feature 41 — every candidate gets a Devil's Advocate
        # Challenge Report generated up front, the same "ready the
        # instant Executive Voting opens" convention Feature 17's Debate
        # below already establishes for approved candidates.
        new_challenge_report = generate_challenge_report(proposal, provider=market_data_provider, case_studies=case_studies, existing_count=len(challenge_reports))

        # v0.7 Feature 55 — the Executive Decision Simulator's Digital
        # War Room. Built eagerly for every candidate — joins the
        # department opinions network, the Devil's Advocate report just
        # generated above, a fresh 12-scenario simulation, and the
        # Similarity Engine's own real historical comparison into one
        # record. Its real decisionScore/expectedValue are exactly what
        # the Chapter 58 gate below decides on.
        category = SYMBOL_CATEGORY.get(proposal.symbol)
        correlated_open_positions = sum(1 for p in paper_portfolio.positions if SYMBOL_CATEGORY.get(p.symbol) == category) if category else 0
        # CEO directive "Portfolio Construction, Capital Allocation &
        # Execution Realism," Phase 4 — the real, statistical Pearson-
        # correlation read (distinct from the category-co-occurrence
        # count directly above), computed here since this is where
        # paper_portfolio/market_data_provider are both already in
        # scope, same convention correlated_open_positions itself
        # already uses.
        real_correlated_positions = count_correlated_positions(proposal.symbol, paper_portfolio, market_data_provider)
        try:
            war_room_candles = market_data_provider.get_candles(proposal.symbol, WAR_ROOM_TIMEFRAME, WAR_ROOM_CANDLE_COUNT)
        except ValueError:
            war_room_candles = []
        war_room_session = build_war_room_session(
            f"warroom-{proposal.id}",
            proposal,
            challenge_report=new_challenge_report,
            coach_reports=coach_reports,
            market_intelligence=market_intelligence,
            decision_vault=decision_vault,
            risk_warnings=risk_warnings,
            correlated_open_positions=correlated_open_positions,
            candles=war_room_candles,
            risk_limits=effective_risk_limits,
        )

        approved, reject_reasons, reject_reason_codes = evaluate_opportunity(
            decision_score=war_room_session.decision_score,
            expected_value=war_room_session.expected_value,
            market_intelligence=market_intelligence,
            risk_limits=effective_risk_limits,
            decision_vault=decision_vault,
            correlated_position_count=real_correlated_positions,
        )
        if not approved:
            opportunity_rejections.append(
                build_opportunity_rejection(
                    proposal,
                    decision_score=war_room_session.decision_score,
                    expected_value=war_room_session.expected_value,
                    reasons=reject_reasons,
                    reason_codes=reject_reason_codes,
                    price_at_rejection=prices.get(proposal.symbol) or proposal.price,
                    now_sim_minutes=now_sim_minutes,
                )
            )
            if len(opportunity_rejections) > MAX_OPPORTUNITY_REJECTIONS:
                del opportunity_rejections[: len(opportunity_rejections) - MAX_OPPORTUNITY_REJECTIONS]
            continue

        challenge_reports.append(new_challenge_report)
        # v0.7 Feature 46 — "Devil's Advocate references it": the whole
        # job of a ChallengeReport is challenging assumptions (Article
        # III); when it also finds real missing evidence, that's a
        # second, distinct real citation (Article IV). Only cited for
        # approved candidates — the CEO never sees a rejected one, so
        # there is nothing real to cite it against.
        constitution_citations = cite_article(constitution_citations, "III", "devils_advocate", f'Challenge report filed for {proposal.symbol} — attempting to break the trade thesis.', new_time.day)
        if new_challenge_report.missing_evidence:
            constitution_citations = cite_article(constitution_citations, "IV", "devils_advocate", f"{proposal.symbol}: {len(new_challenge_report.missing_evidence)} vote(s) with no supporting evidence on record.", new_time.day)

        # v0.7 Design Bible Chapter 57 — the Institutional Position
        # Sizing & Capital Deployment Engine. Runs the instant this
        # session's own Expected Value/Decision Score exist to size
        # against — `proposal.quantity` up to this point was
        # recommended_quantity()'s flat ceiling (see
        # _generate_trade_proposals() above); this narrows it (never
        # widens it) to the real, evidence-justified amount. Portfolio
        # Heat is deliberately this tick's entering `state.portfolio_
        # intelligence` (one tick stale — see build_position_sizing()'s
        # own docstring for why that's an accepted, documented tradeoff).
        position_sizing = build_position_sizing(
            proposal,
            ceiling_quantity=proposal.quantity,
            expected_value=war_room_session.expected_value,
            decision_score=war_room_session.decision_score,
            portfolio=paper_portfolio,
            portfolio_heat=state.portfolio_intelligence.heat,
            risk_limits=effective_risk_limits,
            risk_warnings=risk_warnings,
            sim_day=now_sim_minutes // 1440,
            provider=market_data_provider,
            session=market_intelligence.session.current,
            regime=market_intelligence.regime,
            decision_vault=decision_vault,
        )
        war_room_session = war_room_session.model_copy(update={"position_sizing": position_sizing, "statistical_correlated_positions": real_correlated_positions})
        # Design Bible Chapter 75 — every proposal that survives the
        # Opportunity Gatekeeper gets a real "day"/"swing" tag the moment
        # it becomes CEO-visible.
        trading_style, trading_mode_state = assign_trading_style(trading_mode_state)
        proposal = proposal.model_copy(update={"quantity": position_sizing.final_quantity, "trading_style": trading_style})
        new_proposals.append(proposal)

        war_room_sessions = record_war_room_session(war_room_sessions, war_room_session)

    trade_proposals = [*trade_proposals, *new_proposals]
    # v0.7 Design Bible Chapter 59 — Capital Priority & Opportunity Cost
    # Engine (app/capital_priority.py). Re-sorts the FULL pending queue
    # (not just this tick's new arrivals) by Priority Score every tick,
    # highest first — closes the exact gap Chapter 58's own
    # Implementation Notes flagged as unbuilt. Reuses
    # decisionScore.overall directly via each proposal's own
    # WarRoomSession; never a second, competing composite.
    trade_proposals = rank_trade_proposals(trade_proposals, war_room_sessions)
    # v0.7 Feature 17 — every approved proposal gets a full committee
    # debate (app/debate.py) generated up front, over the same real
    # analyst votes the proposal already carries, so it's ready the
    # instant the CEO opens Executive Voting rather than generated on
    # demand. Only for approved proposals — a rejected candidate never
    # reaches the CEO, so there is nothing for a debate to prepare for.
    debates = [*debates, *(generate_debate(p) for p in new_proposals)]
    if len(debates) > MAX_DEBATES:
        del debates[: len(debates) - MAX_DEBATES]
    if len(challenge_reports) > MAX_CHALLENGE_REPORTS:
        del challenge_reports[: len(challenge_reports) - MAX_CHALLENGE_REPORTS]
    for proposal in new_proposals:
        news.append(
            NewsItem(
                id=f"news-proposal-{proposal.id}",
                headline=f"New trade proposal on {proposal.symbol}: the desk recommends {proposal.overall_recommendation.upper()} — awaiting CEO approval.",
                category="company",
                timestamp=_now_iso(),
            )
        )

    # v0.7 Feature 21 — Company Operating Modes. No-op in Learning Mode
    # (the pre-Feature-21 default); Assisted/Executive sweep the full
    # pending list every tick, not just this tick's new arrivals, so
    # switching modes mid-game takes effect on the existing backlog too.
    trade_proposals, paper_portfolio, meeting_log = _apply_operating_mode(
        operating_mode,
        trade_proposals,
        debates,
        paper_portfolio,
        risk_limits,
        risk_warnings,
        prices,
        now_sim_minutes,
        memory,
        decisions,
        ceo_decisions,
        prediction_records,
        gatekeeper_rejections,
        news,
        challenge_reports,
        coach_reports,
        meeting_log,
        decision_vault,
        new_time.day,
        market_intelligence,
        war_room_sessions,
        market_environment.current,
        state.settings.active_weight_profile,
        state.settings.custom_department_weights,
        emergency_stop_active=emergency_stop.active,
        force_manual_review=force_manual_review,
        min_confidence_override=min_confidence_override,
        behavioral_cooldown_minutes=trading_mode_state.behavioral_cooldown_minutes,
        behavioral_size_increase_threshold_pct=trading_mode_state.behavioral_size_increase_threshold_pct,
        trading_restrictions=trading_restrictions,
    )

    trade_proposals, expired_proposals = expire_stale_proposals(trade_proposals, now_sim_minutes)
    for expired in expired_proposals:
        paper_portfolio, expired_decision, expired_record = resolve_proposal(
            expired,
            "wait",
            portfolio=paper_portfolio,
            risk_limits=risk_limits,
            current_price=prices.get(expired.symbol),
            now_sim_minutes=now_sim_minutes,
            market_intelligence=market_intelligence,
            resolved_by="auto",
        )
        record_ceo_decision(memory, expired_decision, max_records=effective_risk_limits.max_memory_records)
        decisions.append(expired_decision)
        ceo_decisions.append(expired_record)
        new_expired_prediction = build_prediction_record(expired_decision, expired_record, sim_day=new_time.day)
        if new_expired_prediction is not None:
            prediction_records.append(new_expired_prediction)
        expired_challenge_report = next((c for c in reversed(challenge_reports) if c.proposal_id == expired.id), None)
        meeting_log = record_meeting_log_entry(
            meeting_log,
            generate_meeting_log_entry(
                expired, expired_decision, expired_record.ceo_decision, expired_challenge_report, coach_reports, market_intelligence, decision_vault, sim_day=new_time.day, resolved_by="auto"
            ),
        )
        news.append(
            NewsItem(
                id=f"news-proposal-expired-{expired.id}",
                headline=f"Trade proposal on {expired.symbol} expired unactioned — recorded as WAIT.",
                category="company",
                timestamp=_now_iso(),
            )
        )

    # --- v0.5: paper trading + simulation lab -----------------------------
    # Both run after research/watchlist so they see this tick's freshest
    # confidence/price data, and before the meeting call so a just-closed
    # trade or completed simulation can be discussed in a meeting the same
    # tick it happens (matching how research completions already work).
    paper_portfolio, closed_trades = tick_paper_trading(
        paper_portfolio, watchlist, all_agent_ids(), new_time, effective_risk_limits, market_intelligence
    )
    paper_portfolio, closed_trades = _journal_closed_trades(paper_portfolio, [*broker_closed_trades, *closed_trades, *flattened_trades], decisions)
    # Trimmed after _journal_closed_trades (not right after the append
    # above) so a trade closing this very tick can still look its
    # originating decision up by id before the oldest entries are evicted.
    _trim_decisions(decisions)

    # grade_ceo_decisions runs after _journal_closed_trades so any trade
    # that closed this tick already has its decision_id stamped in
    # paper_portfolio.trade_history for a pending CeoDecisionRecord to
    # match against.
    ceo_decisions = grade_ceo_decisions(ceo_decisions, paper_portfolio.trade_history)
    if len(ceo_decisions) > MAX_CEO_DECISIONS:
        del ceo_decisions[: len(ceo_decisions) - MAX_CEO_DECISIONS]

    # v0.7 Feature 20 — resolves any Gatekeeper rejection whose real
    # evaluation window has elapsed, purely from the symbol's own real
    # subsequent watchlist price movement (see app/gatekeeper.py).
    gatekeeper_rejections = grade_gatekeeper_rejections(gatekeeper_rejections, watchlist, now_sim_minutes)
    if len(gatekeeper_rejections) > MAX_GATEKEEPER_REJECTIONS:
        del gatekeeper_rejections[: len(gatekeeper_rejections) - MAX_GATEKEEPER_REJECTIONS]
    # v0.7 Chapter 58 — the same real grading, applied to the earlier
    # pre-proposal rejection stage (see app/opportunity_gatekeeper.py).
    opportunity_rejections = grade_opportunity_rejections(opportunity_rejections, watchlist, now_sim_minutes)
    if len(opportunity_rejections) > MAX_OPPORTUNITY_REJECTIONS:
        del opportunity_rejections[: len(opportunity_rejections) - MAX_OPPORTUNITY_REJECTIONS]
    for trade in closed_trades:
        record_paper_trade(memory, trade, max_records=effective_risk_limits.max_memory_records)
        outcome = "gained" if trade.pnl > 0 else "lost"
        news.append(
            NewsItem(
                id=f"news-trade-{trade.id}",
                headline=f"Paper trade closed: {trade.symbol} {outcome} {abs(trade.pnl_pct):.1f}% (simulated — no real capital involved).",
                category="company",
                timestamp=_now_iso(),
            )
        )

        # v0.7 Feature 26 — the Discipline Chamber. One real DisciplineReview
        # per closed trade, scoring the decision PROCESS (never the pnl
        # above) — see app/discipline.py's module docstring. Only trades
        # with a real matched decision_id (every trade this codebase can
        # actually place) get reviewed; a trade closed before Feature 26
        # shipped, or with no decision_id match, has no process trail to
        # honestly score and is skipped rather than faked.
        decision = next((d for d in decisions if d.id == trade.decision_id), None) if trade.decision_id else None

        # CEO directive "...then Paper-Trade Journal + Drift Detection +
        # Strategy Health State Machine" — one real, permanent journal
        # entry per closed trade (see app/paper_trade_journal.py's
        # module docstring for why this is a joined-identity-plus-
        # snapshot record, never a duplicate of PaperTrade/
        # CeoDecisionRecord/RiskDecision's own already-real fields).
        ceo_record = next((c for c in ceo_decisions if c.decision_id == trade.decision_id), None) if trade.decision_id else None
        risk_decision = next((r for r in state.risk_decisions if r.decision_id == trade.decision_id), None) if trade.decision_id else None
        paper_trade_journal.append(build_journal_entry(trade, ceo_decision=ceo_record, risk_decision=risk_decision))
        if len(paper_trade_journal) > MAX_PAPER_TRADE_JOURNAL:
            del paper_trade_journal[: len(paper_trade_journal) - MAX_PAPER_TRADE_JOURNAL]
        if ceo_record is not None and ceo_record.strategy_id is not None:
            trades_closed_this_tick_by_strategy[ceo_record.strategy_id] = trades_closed_this_tick_by_strategy.get(ceo_record.strategy_id, 0) + 1

        if decision is not None:
            proposal_id = decision.id.removeprefix("decision-")
            debate = next((d for d in reversed(debates) if d.proposal_id == proposal_id), None)
            discipline_review = generate_discipline_review(
                decision,
                debate,
                hold_duration_minutes=trade.duration_minutes,
                pnl=trade.pnl,
                pnl_pct=trade.pnl_pct,
                review_id=f"discipline-{trade.id}",
                sim_day=new_time.day,
                created_at=_now_iso(),
            )
            discipline_reviews = record_discipline_review_entry(discipline_reviews, discipline_review)
            record_discipline_review(memory, discipline_review, max_records=effective_risk_limits.max_memory_records)
            trade_case_studies: list[CaseStudy] = []
            company_dna_change: str | None = None

            # v0.7 Feature 27 — the Library of Mistakes. Only a real loss
            # can produce a case study (see app/mistakes.py's module
            # docstring on why a well-disciplined process that loses to
            # real market variance is not a "mistake").
            if trade.pnl <= 0:
                new_case_studies = generate_case_studies(decision, debate, trade, discipline_review, id_prefix=f"case-{trade.id}")
                case_studies = record_case_studies(case_studies, new_case_studies)
                trade_case_studies = new_case_studies

                # CEO directive "Features 26-30," Feature 30 — the
                # Failure Review Board, the final stage of the
                # 26->27->28->29->30 learning loop. One real
                # FailureClassification per closed, losing trade, reusing
                # this trade's own just-filed CaseStudy(s) above plus the
                # real DisciplineReview and Market Intelligence Learning
                # Loop entries already computed this tick — see
                # app/failure_review.py for the full precedence order.
                failure_classification = classify_failure(
                    decision,
                    trade,
                    discipline_review,
                    new_case_studies,
                    market_intelligence_learning,
                    classification_id=f"failure-{trade.id}",
                    sim_day=new_time.day,
                    created_at=_now_iso(),
                )
                failure_classifications = record_failure_classification(failure_classifications, failure_classification)
                if should_promote_failure_classification(failure_classification):
                    institutional_memory = record_institutional_memory(
                        institutional_memory, promote_failure_classification(failure_classification), current_sim_day=new_time.day
                    )

                for case_study in new_case_studies:
                    record_case_study(memory, case_study, max_records=effective_risk_limits.max_memory_records)
                    institutional_memory = record_institutional_memory(
                        institutional_memory, promote_case_study(case_study), current_sim_day=new_time.day
                    )
                    news.append(
                        NewsItem(
                            id=f"news-case-study-{case_study.id}",
                            headline=f'New case study filed: "{case_study.title}" ({case_study.symbol}).',
                            category="company",
                            timestamp=_now_iso(),
                        )
                    )
                    # v0.7 Feature 46 — "Every mistake must teach something"
                    # (Article VI) is literally what a filed case study
                    # already does; the specific detected pattern also
                    # names whichever real Article it violates.
                    constitution_citations = cite_article(constitution_citations, "VI", "case_study", f'"{case_study.title}" ({case_study.symbol}) filed as a real case study.', new_time.day)
                    specific_article = MISTAKE_ARTICLE_MAP.get(case_study.category)
                    if specific_article:
                        constitution_citations = cite_article(constitution_citations, specific_article, "case_study", f'"{case_study.title}" — {case_study.category.replace("_", " ")}.', new_time.day)
                    # Design Bible Chapter 74 Part 1 — Academy Integration's
                    # one real, honest hook: no lesson content is
                    # generated (no LLM exists to write one), but the
                    # supporting agents nudge their own AgentKnowledgeState
                    # for having reflected on a real, filed mistake.
                    for supporting_agent in decision.supporting_agents:
                        agent_knowledge, learning_event = award_points(
                            agent_knowledge, supporting_agent, ACADEMY_CASE_STUDY_NUDGE, source="case_study_reflection"
                        )
                        if learning_event is not None:
                            record_knowledge_tier_up(memory, learning_event, max_records=effective_risk_limits.max_memory_records)
                            learning_events = record_learning_event(learning_events, learning_event)
                # Design Bible Chapter 74 Part 1 — the Recurring Mistake
                # Pattern generator, checked once per trade after that
                # trade's own case studies are already real and recorded.
                recurring_mistake_proposal = maybe_propose_recurring_mistake(
                    case_studies, self_improvement_proposals, sim_day=new_time.day
                )
                if recurring_mistake_proposal is not None:
                    # Design Bible Chapter 74.5 — the Vision Alignment
                    # Engine. Computed once, here, at generation time:
                    # Chapter 74 already reserved vision_alignment_score
                    # on SelfImprovementProposal for exactly this chapter
                    # to fill in.
                    alignment = compute_self_improvement_proposal_alignment(
                        recurring_mistake_proposal, state.vision_board
                    )
                    recurring_mistake_proposal = recurring_mistake_proposal.model_copy(
                        update={"vision_alignment_score": alignment.score}
                    )
                    self_improvement_proposals = record_self_improvement_proposal(
                        self_improvement_proposals, recurring_mistake_proposal
                    )
                    record(memory, "alert", "Self-Improvement Proposal filed", recurring_mistake_proposal.title, max_records=effective_risk_limits.max_memory_records)
            # v0.7 Feature 42 — the Library of Successes (app/successes.py),
            # the Decision Replay Center's "Successes" lesson type. Same
            # capped list/memory log as the Library of Mistakes above
            # (CaseStudy is one shared schema — see schemas.py's
            # SUCCESS_CASE_STUDY_CATEGORIES), only a real win can produce one.
            elif trade.pnl > 0:
                new_success_studies = generate_success_studies(decision, debate, trade, discipline_review, id_prefix=f"case-{trade.id}")
                case_studies = record_success_studies(case_studies, new_success_studies)
                trade_case_studies = new_success_studies
                for success_study in new_success_studies:
                    record_case_study(memory, success_study, max_records=effective_risk_limits.max_memory_records)
                    institutional_memory = record_institutional_memory(
                        institutional_memory, promote_case_study(success_study), current_sim_day=new_time.day
                    )
                    news.append(
                        NewsItem(
                            id=f"news-case-study-{success_study.id}",
                            headline=f'New case study filed: "{success_study.title}" ({success_study.symbol}).',
                            category="company",
                            timestamp=_now_iso(),
                        )
                    )
                    constitution_citations = cite_article(constitution_citations, "VI", "case_study", f'"{success_study.title}" ({success_study.symbol}) filed as a real case study.', new_time.day)
                    specific_article = MISTAKE_ARTICLE_MAP.get(success_study.category)
                    if specific_article:
                        constitution_citations = cite_article(constitution_citations, specific_article, "case_study", f'"{success_study.title}" — {success_study.category.replace("_", " ")}.', new_time.day)
                    # v0.7 Feature 48 — a filed success study records real
                    # behavior that just happened (never a prediction): a
                    # disciplined_process win is real evidence of lower
                    # risk-taking; a patient_execution win is real
                    # evidence of patience. Each gets one small, permanent
                    # Legacy nudge.
                    if success_study.category == "disciplined_process":
                        company_dna_legacy = nudge_legacy(company_dna_legacy, "risk_appetite", -SUCCESS_STUDY_NUDGE)
                        company_dna_change = f"Legacy risk_appetite nudged -{SUCCESS_STUDY_NUDGE} after a disciplined_process win on {trade.symbol}."
                    elif success_study.category == "patient_execution":
                        company_dna_legacy = nudge_legacy(company_dna_legacy, "patience", SUCCESS_STUDY_NUDGE)
                        company_dna_change = f"Legacy patience nudged +{SUCCESS_STUDY_NUDGE} after a patient_execution win on {trade.symbol}."
                    # Design Bible Chapter 74 Part 1 — same real Academy
                    # hook as the loss branch above.
                    for supporting_agent in decision.supporting_agents:
                        agent_knowledge, learning_event = award_points(
                            agent_knowledge, supporting_agent, ACADEMY_CASE_STUDY_NUDGE, source="case_study_reflection"
                        )
                        if learning_event is not None:
                            record_knowledge_tier_up(memory, learning_event, max_records=effective_risk_limits.max_memory_records)
                            learning_events = record_learning_event(learning_events, learning_event)
                # Trading Psychology & Discipline, Piece D — the Library
                # of Successes' own tie into CLSIS, checked once per trade
                # after that trade's own success studies are already real
                # and recorded, the exact mirror of the loss branch's own
                # recurring_mistake trigger above.
                reinforce_success_proposal = maybe_propose_reinforce_success_pattern(
                    case_studies, self_improvement_proposals, sim_day=new_time.day
                )
                if reinforce_success_proposal is not None:
                    alignment = compute_self_improvement_proposal_alignment(
                        reinforce_success_proposal, state.vision_board
                    )
                    reinforce_success_proposal = reinforce_success_proposal.model_copy(
                        update={"vision_alignment_score": alignment.score}
                    )
                    self_improvement_proposals = record_self_improvement_proposal(
                        self_improvement_proposals, reinforce_success_proposal
                    )
                    record(memory, "alert", "Self-Improvement Proposal filed", reinforce_success_proposal.title, max_records=effective_risk_limits.max_memory_records)

            # v0.7 — the Decision Memory System's Decision Vault
            # (app/decision_vault.py). One permanent record joining this
            # trade with everything already computed above for it —
            # market regime/liquidity are stamped fresh "as of trade
            # close" (see build_vault_entry's own docstring on why).
            meeting_log_entry = next((e for e in reversed(meeting_log) if e.proposal_id == proposal_id), None)
            ceo_decision = next((c for c in reversed(ceo_decisions) if c.decision_id == decision.id), None)
            vault_entry = build_vault_entry(
                entry_id=f"vault-{trade.id}",
                trade=trade,
                decision=decision,
                discipline_review=discipline_review,
                market_regime=market_intelligence.regime,
                market_regime_label=market_intelligence.regime_label,
                provider=market_data_provider,
                case_study=trade_case_studies[0] if trade_case_studies else None,
                meeting_log_entry=meeting_log_entry,
                ceo_decision=ceo_decision,
                company_dna_change=company_dna_change,
                sim_day=new_time.day,
            )
            decision_vault = record_vault_entry(
                decision_vault, vault_entry, max_entries=effective_risk_limits.max_decision_vault_entries
            )

            # v0.7 Feature 55 — the Executive Decision Simulator's War
            # Room. Once this trade's originating proposal's own
            # WarRoomSession is found, fill in a real predicted-vs-actual
            # scenario comparison against its already-stored
            # WhatIfSimulation (see compare_scenario_to_outcome's own
            # docstring — never a claim the scenario "predicted" this).
            war_room_index = next((i for i, s in enumerate(war_room_sessions) if s.proposal_id == proposal_id), None)
            if war_room_index is not None:
                session = war_room_sessions[war_room_index]
                comparison = compare_scenario_to_outcome(session.scenario_simulation, trade)
                war_room_sessions[war_room_index] = session.model_copy(update={"outcome_comparison": comparison})

    # CEO directive "...then Paper-Trade Journal + Drift Detection +
    # Strategy Health State Machine" — once per tick (never once per
    # trade): re-evaluates every real strategy's drift signals and, from
    # those, its health state. Deliberately placed AFTER the
    # closed_trades loop above so this tick's own new decision_vault/
    # failure_classifications entries (recorded inside that loop) are
    # already visible to compute_strategy_degradation() — the identical
    # "use this tick's freshest state" convention grade_ceo_decisions/
    # grade_predictions below already follow.
    previous_drift_severity: dict[tuple[str, DriftCategory], DriftSeverity] = {(e.strategy_id, e.category): e.severity for e in drift_events}
    new_drift_events = evaluate_strategy_drift(
        strategies=strategies,
        trade_history=paper_portfolio.trade_history,
        decision_vault=decision_vault,
        failure_classifications=failure_classifications,
        market_environment=market_environment,
        now_sim_minutes=now_sim_minutes,
        sim_day=new_time.day,
        previous_severity=previous_drift_severity,
    )
    if new_drift_events:
        drift_events = [*drift_events, *new_drift_events]
        if len(drift_events) > MAX_DRIFT_EVENTS:
            del drift_events[: len(drift_events) - MAX_DRIFT_EVENTS]

    current_drift_severity = dict(previous_drift_severity)
    new_events_by_strategy: dict[str, list[str]] = {}
    for event in new_drift_events:
        current_drift_severity[(event.strategy_id, event.category)] = event.severity
        new_events_by_strategy.setdefault(event.strategy_id, []).append(event.id)

    strategies_needing_health_check = {s.id for s in strategies} & (
        set(new_events_by_strategy) | set(strategy_health_states) | set(trades_closed_this_tick_by_strategy)
    )
    for strategy_id in strategies_needing_health_check:
        severities = {category: severity for (sid, category), severity in current_drift_severity.items() if sid == strategy_id}
        updated_health = evaluate_health_transition(
            current=strategy_health_states.get(strategy_id),
            strategy_id=strategy_id,
            current_severities=severities,
            new_trades_closed_this_tick=trades_closed_this_tick_by_strategy.get(strategy_id, 0),
            sim_day=new_time.day,
            triggering_drift_event_ids=new_events_by_strategy.get(strategy_id, []),
        )
        if updated_health is not strategy_health_states.get(strategy_id):
            strategy_health_states[strategy_id] = updated_health

    # CEO directive "Features 26-30," Feature 29 — the same real
    # decision_id match, run right alongside grade_ceo_decisions above.
    # Deliberately placed AFTER the closed_trades loop above (not
    # alongside grade_ceo_decisions before it): this tick's own real
    # FailureClassifications are only computed inside that loop, and
    # Feature 30's feed-back (failure_reason below) needs them available
    # for a prediction resolved on this very tick, not just a later one.
    # Any prediction newly resolved this tick and honestly notable (real
    # high confidence, resolved wrong) is promoted into Institutional
    # Memory (Feature 26) — never every resolved prediction, never a
    # re-promotion of one already filed in a prior tick.
    pending_prediction_ids = {p.id for p in prediction_records if p.outcome == "pending"}
    prediction_records = grade_predictions(prediction_records, paper_portfolio.trade_history, failure_classifications)
    if len(prediction_records) > MAX_PREDICTION_RECORDS:
        del prediction_records[: len(prediction_records) - MAX_PREDICTION_RECORDS]
    for prediction in prediction_records:
        if prediction.id in pending_prediction_ids and prediction.outcome != "pending" and should_promote_prediction_outcome(prediction):
            institutional_memory = record_institutional_memory(
                institutional_memory, promote_prediction_outcome(prediction), current_sim_day=new_time.day
            )

    backtest_sessions, simulation_results, newly_completed_sims = tick_simulation_lab(
        backtest_sessions, simulation_results, strategies, watchlist, RESEARCHER_IDS, new_time
    )
    for result in newly_completed_sims:
        record_simulation_result(memory, result, max_records=effective_risk_limits.max_memory_records)
        news.append(
            NewsItem(
                id=f"news-sim-{result.id}",
                headline=f"Simulation complete: \"{result.strategy_name}\" on {result.symbol} returned {result.total_return_pct:+.1f}% (simulated).",
                category="discovery",
                timestamp=_now_iso(),
            )
        )
        # v0.7 Feature 45 — the Research Sandbox. Every completed run
        # auto-generates a real StrategyReport and, if it's the strategy's
        # own qualifying evidence, advances that strategy's pipeline stage.
        matching_strategy = next((s for s in strategies if s.id == result.strategy_id), None)
        if matching_strategy is not None:
            strategy_report = generate_strategy_report(matching_strategy, result, sim_day=new_time.day)
            strategy_reports.append(strategy_report)
            cap_strategy_reports(strategy_reports)
            strategies = [maybe_advance_after_result(s, result, new_time.day) if s.id == result.strategy_id else s for s in strategies]
            news.append(
                NewsItem(
                    id=f"news-strategy-report-{strategy_report.id}",
                    headline=f'Strategy Report filed: "{matching_strategy.name}" ({result.scenario}) — {result.total_return_pct:+.1f}%.',
                    category="discovery",
                    timestamp=_now_iso(),
                )
            )
            # v0.7 Feature 52 (Part 1) — Strategy Validation Laboratory.
            # Every completed run also re-runs the strategy's own Monte
            # Carlo trade-sequence bootstrap, its regime-bucketed
            # performance table, and a real liquidity-conditions check
            # against the live watchlist — see app/strategy_lab.py's
            # module docstring for the honesty boundary each of these
            # observes.
            monte_carlo = run_strategy_monte_carlo(matching_strategy, simulation_results, sim_day=new_time.day)
            if monte_carlo is not None:
                strategy_monte_carlo_results.append(monte_carlo)
            regime_test = compute_strategy_regime_test(matching_strategy, simulation_results, sim_day=new_time.day)
            if regime_test is not None:
                strategy_regime_tests.append(regime_test)
            liquidity_validation = validate_strategy_liquidity(matching_strategy, watchlist, market_data_provider, sim_day=new_time.day)
            if liquidity_validation is not None:
                strategy_liquidity_validations.append(liquidity_validation)
            # v0.7 Feature 52 (Part 2) — Strategy Health's real
            # recent-vs-lifetime trend read, refreshed on the exact same
            # trigger as the three artifacts above.
            health = compute_strategy_health(matching_strategy, simulation_results, sim_day=new_time.day)
            if health is not None:
                strategy_health_assessments.append(health)

    cap_strategy_monte_carlo_results(strategy_monte_carlo_results)
    cap_strategy_regime_tests(strategy_regime_tests)
    cap_strategy_liquidity_validations(strategy_liquidity_validations)
    cap_strategy_health_assessments(strategy_health_assessments)

    # v0.7 Feature 45 — Automation Mode governs the Company Review stage's
    # final CEO call exactly the way _apply_operating_mode already governs
    # trade decisions: Learning Mode always waits for a real manual click
    # (POST /api/sandbox/decide); Executive Mode auto-resolves every
    # pending StrategyReview using its own real overall_verdict; Assisted
    # Mode only auto-resolves the unambiguous cases (pass/fail), leaving a
    # genuine "concern" verdict for real CEO judgment.
    for i, pending_review in enumerate(strategy_reviews):
        if pending_review.ceo_decision != "pending":
            continue
        if operating_mode == "learning":
            continue
        if operating_mode == "assisted" and pending_review.overall_verdict == "concern":
            continue
        approve = pending_review.overall_verdict == "pass"
        review_strategy = next((s for s in strategies if s.id == pending_review.strategy_id), None)
        if review_strategy is None:
            continue
        strategies = [apply_review_decision(s, pending_review, approve, new_time.day) if s.id == pending_review.strategy_id else s for s in strategies]
        strategy_reviews[i] = pending_review.model_copy(update={"ceo_decision": "approved" if approve else "rejected", "resolved_by": "auto"})
        mode_label = "Executive Mode" if operating_mode == "executive" else "Assisted Mode"
        news.append(
            NewsItem(
                id=f"news-strategy-review-{pending_review.id}",
                headline=f'{mode_label}: Company Review {"approved" if approve else "rejected"} "{review_strategy.name}" ({pending_review.overall_verdict}).',
                category="company",
                timestamp=_now_iso(),
            )
        )
    cap_strategy_reviews(strategy_reviews)

    mm_count_before_meeting = len(meeting_minutes)
    agents, meeting = _maybe_call_meeting(
        agents, state.meeting, research, new_time, news, tasks, memory, meeting_minutes, resting=resting, max_memory_records=effective_risk_limits.max_memory_records
    )
    # v0.7 Feature 25 — every agent who actually attended a real meeting
    # earns a small real Knowledge Points bonus (app/academy.py) —
    # "collaboration" grounded in the meeting system that already exists.
    if len(meeting_minutes) > mm_count_before_meeting:
        for attendee in meeting_minutes[-1].participants:
            agent_knowledge, learning_event = award_points(agent_knowledge, attendee, MEETING_ATTENDANCE_POINTS * knowledge_multiplier, source="meeting_attendance")
            if learning_event is not None:
                record_knowledge_tier_up(memory, learning_event, max_records=effective_risk_limits.max_memory_records)
                learning_events = record_learning_event(learning_events, learning_event)

    if random.random() < 0.04:
        news.append(
            NewsItem(
                id=f"news-market-{new_time.day}-{new_time.hour}-{new_time.minute}",
                headline=random.choice(MARKET_HEADLINES_BY_REGIME.get(market_environment.current, MARKET_HEADLINES)),
                category="market",
                timestamp=_now_iso(),
            )
        )

    # --- v0.5: coaching, scoring, and performance analytics ---------------
    # Company score is cheap to recompute and feeds the Brain Room HUD's
    # live-updating readout, so it's refreshed every tick like mood/energy
    # already are — not just on the evening/weekly/monthly cadences below.
    company_score = compute_company_score(research, paper_portfolio, memory, simulation_results, [a.mood for a in agents.values()])
    # v0.7 Feature 23 — Company Health & Stability System. Cheap to
    # recompute and refreshed every tick, same reasoning as company_score
    # above (it feeds a live-updating Command Center readout, not just a
    # periodic report).
    company_health = compute_company_health(
        agents=agents,
        research=research,
        portfolio=paper_portfolio,
        risk_warnings=risk_warnings,
        agent_energy=agent_energy,
        hall_of_fame=hall_of_fame,
        signal_calibration=state.signal_calibration,
        watchlist=watchlist,
        education=state.education,
        debates=debates,
        decisions=decisions,
        meeting_log=meeting_log,
        self_evaluations=self_evaluations,
        wisdom_state=wisdom_state,
        # v0.7 Feature 50 (Part 2/3) — a cheap, pure recompute (same
        # "cheap to recompute every tick" reasoning as this whole
        # function) rather than waiting for the tick's own later
        # innovation_state assignment below, which runs after this call.
        innovation_state=compute_innovation_state(challenge_reports),
        foundational_mentor_state=foundational_mentor_state,
        founder_council_sessions=founder_council_sessions,
        gatekeeper_rejections=gatekeeper_rejections,
        # CEO Company/Executive Health directive, Phase 3 — Talent
        # Development's own real post-graduation performance signal
        # reads the exact same real, already-in-scope discipline_reviews
        # list every other tick-time consumer here does.
        discipline_reviews=discipline_reviews,
        # CEO Company/Executive Health directive — Institutional Memory's
        # real per-agent Academy mastery signal, and Innovation
        # Velocity's real Strategy Lab pipeline-progress/measured-
        # improvement signals, all already in scope at this point in the
        # tick.
        agent_knowledge=agent_knowledge,
        strategies=strategies,
        strategy_health_assessments=strategy_health_assessments,
        # CEO directive "Features 31-35," Feature 35 — Compliance
        # Health's real evidence, already in scope at this point in the
        # tick (the same real `compliance_incidents`/`new_time.day`
        # every other tick-time consumer here already uses).
        compliance_incidents=compliance_incidents,
        current_sim_day=new_time.day,
        # v0.7 Design Bible Chapter 63 — CEO-configurable Company Health
        # tier thresholds, threaded the same way every other Chapter
        # 57-62 CEO control already is at this point in the tick.
        excellent_threshold=effective_risk_limits.company_health_excellent_threshold,
        good_threshold=effective_risk_limits.company_health_good_threshold,
        stable_threshold=effective_risk_limits.company_health_stable_threshold,
        needs_attention_threshold=effective_risk_limits.company_health_needs_attention_threshold,
    )
    # CEO Company Health + Live Market Realism directive, Section 6 — the
    # real tick-over-tick delta breakdown, diffed against `state.company_health`
    # (this tick's pre-update value, i.e. what the CEO last actually saw)
    # before it's replaced by the freshly computed `company_health` above.
    company_health_delta = diff_company_health(state.company_health, company_health)
    # v0.7 Feature 43 — Company DNA. Cheap to recompute (a handful of
    # linear scans over already-in-memory lists), same "always current"
    # reasoning as company_health above.
    company_dna = compute_company_dna(decisions, paper_portfolio.trade_history, ceo_decisions, legacy_deltas=company_dna_legacy)
    # v0.7 Feature 49 — Daily Trading Objectives. Real-time readout, same
    # "derived, recomputed fresh every tick" convention as company_dna
    # above.
    daily_objective_status = compute_daily_objective_status(risk_limits, paper_portfolio, new_time.day)
    # Prop-Firm Risk Intelligence Addendum, Piece 8 — remaining risk
    # budget. Same "derived, recomputed fresh every tick" convention as
    # daily_objective_status directly above.
    risk_budget_status = compute_risk_budget_status(risk_limits, paper_portfolio, new_time.day)
    # v0.7 Feature 25 — cheap to recompute every tick, same reasoning as
    # company_health above (feeds a live-updating Academy readout).
    academy_state = compute_academy_state(agent_knowledge, len(academy_completed_projects))
    # v0.7 Design Bible Chapter 64 — real progress against every active
    # CEO-authored goal, recomputed fresh every tick from the same real
    # readings already computed above (company_score, company_health,
    # academy_state) plus the current portfolio.
    goals = tick_goals(goals, company_health=company_health, company_score=company_score, portfolio=paper_portfolio, academy_state=academy_state, sim_day=new_time.day)
    # v0.7 Feature 56 — Enterprise Portfolio Intelligence. Cheap to
    # recompute every tick, same reasoning as company_health above.
    portfolio_intelligence = compute_portfolio_intelligence(paper_portfolio, market_data_provider, pending_proposal_count=len(trade_proposals))
    # Design Bible Chapter 71 — Economic Intelligence Center. The
    # always-current cross-signal synthesis (app/economic_intelligence.py),
    # cheap to recompute every tick over the three real reads already
    # computed above, same reasoning as company_health/portfolio_intelligence.
    economic_intelligence = compute_economic_intelligence(market_environment, market_intelligence, portfolio_intelligence)

    # Design Bible Chapter 72 — Black Swan Intelligence & Resilience
    # System. Cheap to recompute every tick over five real reads already
    # computed above (risk_warnings, market_intelligence, portfolio_
    # intelligence, market_environment, economic_intelligence), same
    # "always current" reasoning as company_health/portfolio_intelligence.
    previous_black_swan_tier = state.black_swan_intelligence.warning.tier
    black_swan_intelligence = compute_black_swan_intelligence(risk_warnings, market_intelligence, portfolio_intelligence, market_environment, economic_intelligence)

    if defensive_mode.active and defensive_mode.auto_trigger_enabled and not tier_meets_or_exceeds(black_swan_intelligence.warning.tier, defensive_mode.trigger_tier):
        defensive_mode, restored_limits, closed_event, _deactivate_error = deactivate_defensive_mode(
            defensive_mode, paper_portfolio, black_swan_intelligence.warning, now_iso=_now_iso(), now_sim_minutes=now_sim_minutes, event_id=f"bs-event-{new_time.day}-{now_sim_minutes}"
        )
        if restored_limits is not None:
            risk_limits = restored_limits
        if closed_event is not None:
            black_swan_events = record_black_swan_event(black_swan_events, closed_event)
            record(memory, "lesson", f"Defensive Mode episode ended — peaked at {closed_event.peak_tier.upper()}", closed_event.lesson, max_records=effective_risk_limits.max_memory_records)
    elif defensive_mode.active:
        defensive_mode = note_defensive_mode_peak_tier(defensive_mode, black_swan_intelligence.warning.tier)
    elif defensive_mode.auto_trigger_enabled and tier_meets_or_exceeds(black_swan_intelligence.warning.tier, defensive_mode.trigger_tier):
        defensive_mode, risk_limits, _activate_error = activate_defensive_mode(
            defensive_mode,
            risk_limits,
            paper_portfolio,
            black_swan_intelligence.warning.tier,
            reason=f"Auto-triggered: Risk Level reached {black_swan_intelligence.warning.tier.upper()} (configured trigger: {defensive_mode.trigger_tier.upper()}).",
            now_iso=_now_iso(),
            now_sim_minutes=now_sim_minutes,
        )

    # Design Bible Chapter 70 Part 1 — the Emergency Stop Board Report,
    # for the trigger captured earlier in this same tick (circuit
    # breaker Tier 4 or a losing-streak suspension) once company_health/
    # black_swan_intelligence above are finally available to compose it
    # from.
    if emergency_stop_board_trigger_detail is not None:
        emergency_stop_board_report = generate_board_report(
            cadence="emergency",
            trigger="emergency_stop",
            trigger_detail=emergency_stop_board_trigger_detail,
            research=research,
            decisions=decisions,
            agent_ids=all_agent_ids(),
            company_health=company_health,
            black_swan_tier=black_swan_intelligence.warning.tier,
            circuit_breaker_tier=daily_circuit_breaker.tier,
            pending_ceo_decisions=len(trade_proposals),
            sim_day=new_time.day,
            report_id=f"board-emergency-stop-{new_time.day}-{now_sim_minutes}",
            now_iso=_now_iso(),
        )
        board_reports = record_board_report(board_reports, emergency_stop_board_report)
        record(memory, "alert", "Emergency Board Report filed", emergency_stop_board_report.summary, max_records=effective_risk_limits.max_memory_records)

    # A real Crisis Briefing fires once, the moment the tier first
    # crosses into RED/CRITICAL — never every tick while it stays there.
    # Design Bible Chapter 70 Part 1 — this same crossing now also fires
    # a real emergency Board Report, one of the two real Emergency Board
    # Meeting triggers this chapter's own research confirmed (the other
    # is Emergency Stop activation, below). See app/black_swan.py's
    # module docstring for the Crisis Briefing itself.
    if tier_meets_or_exceeds(black_swan_intelligence.warning.tier, "red") and not tier_meets_or_exceeds(previous_black_swan_tier, "red"):
        briefing = generate_crisis_briefing(black_swan_intelligence, paper_portfolio, portfolio_intelligence, risk_limits, new_time.day, briefing_id=f"crisis-{new_time.day}-{now_sim_minutes}")
        record(memory, "alert", f"Crisis Briefing — Risk Level {briefing.tier.upper()}", briefing.situation_summary, max_records=effective_risk_limits.max_memory_records)
        emergency_board_report = generate_board_report(
            cadence="emergency",
            trigger="black_swan_tier",
            trigger_detail=f"Black Swan Risk crossing into {black_swan_intelligence.warning.tier.upper()}",
            research=research,
            decisions=decisions,
            agent_ids=all_agent_ids(),
            company_health=company_health,
            black_swan_tier=black_swan_intelligence.warning.tier,
            circuit_breaker_tier=daily_circuit_breaker.tier,
            pending_ceo_decisions=len(trade_proposals),
            sim_day=new_time.day,
            report_id=f"board-emergency-blackswan-{new_time.day}-{now_sim_minutes}",
            now_iso=_now_iso(),
        )
        board_reports = record_board_report(board_reports, emergency_board_report)
        record(memory, "alert", "Emergency Board Report filed", emergency_board_report.summary, max_records=effective_risk_limits.max_memory_records)

    # Design Bible Chapter 72 Part 2 — Institutional Survival Score.
    # Cheap to recompute every tick (reuses three of the Early Warning
    # Score's own factors above, plus a handful of real linear scans),
    # same "always current" reasoning as company_health above.
    institutional_survival_score = compute_institutional_survival_score(paper_portfolio, risk_limits, portfolio_intelligence, black_swan_intelligence, defensive_mode)

    is_evening = new_time.hour == EVENING_REVIEW_HOUR and new_time.minute == 0
    is_midnight = new_time.hour == 0 and new_time.minute == 0
    is_morning_qotd = new_time.hour == MORNING_QOTD_HOUR and new_time.minute == 0
    is_founder_log_hour = new_time.hour == FOUNDER_LOG_HOUR and new_time.minute == 0
    latest_report: CoachReport | None = None

    # v0.7 Feature 51 — the Market Intelligence Department's daily
    # Executive Market Brief. Gated on is_evening alone (every real day,
    # not a weekly/monthly modulo like the reports below) per the brief's
    # own "every day produce an Executive Market Brief" — snapshots
    # today's real MarketIntelligenceState plus a fresh Market Debate and
    # Strategy Match. The Learning Loop grades YESTERDAY's report the
    # moment a full day of real outcomes exists to compare it against,
    # never the same day's own not-yet-final numbers.
    if is_evening:
        market_intelligence_debate = generate_market_debate(market_intelligence, debate_id=f"midebate-{new_time.day}")
        market_intelligence_strategy_match = compute_strategy_match(market_intelligence.regime, strategies, strategy_reports)
        market_intelligence_report = generate_market_intelligence_report(market_intelligence, market_intelligence_debate, market_intelligence_strategy_match, sim_day=new_time.day)
        market_intelligence_reports = record_market_intelligence_report(market_intelligence_reports, market_intelligence_report)

        yesterday_sim_day = new_time.day - 1
        yesterday_report = next((r for r in reversed(market_intelligence_reports) if r.sim_day == yesterday_sim_day), None)
        already_graded = any(e.for_sim_day == yesterday_sim_day for e in market_intelligence_learning)
        if yesterday_report is not None and not already_graded:
            yesterday_environment_entries = filter_environment_entries_for_day(market_environment.timeline, yesterday_sim_day)
            yesterday_trades = filter_trades_for_day(paper_portfolio.trade_history, yesterday_sim_day)
            market_intelligence_learning = record_learning_entry(
                market_intelligence_learning, generate_learning_entry(yesterday_report, yesterday_environment_entries, yesterday_trades)
            )

        # Design Bible Chapter 71 — Economic Intelligence Center's Daily
        # Brief. Same is_evening/once-per-real-day cadence as the Market
        # Intelligence brief above; the narrative diffs against the most
        # recently stored EIC report (see economic_intelligence.py's
        # generate_market_narrative()), never the same day's own read.
        previous_eic_report = economic_intelligence_reports[-1] if economic_intelligence_reports else None
        economic_intelligence_report = generate_economic_intelligence_report(economic_intelligence, previous_eic_report, sim_day=new_time.day)
        economic_intelligence_reports = record_economic_intelligence_report(economic_intelligence_reports, economic_intelligence_report)

        # Design Bible Chapter 72 — the Daily Black Swan Situation
        # Report. Same once-per-real-evening cadence as the EIC brief
        # above; the narrative diffs against the most recently stored
        # BSIRS report (see app/black_swan.py's generate_black_swan_
        # narrative()), never the same day's own read.
        previous_bs_report = black_swan_reports[-1] if black_swan_reports else None
        black_swan_report = generate_black_swan_report(black_swan_intelligence, previous_bs_report, sim_day=new_time.day)
        black_swan_reports = record_black_swan_report(black_swan_reports, black_swan_report)

        # Design Bible Chapter 70 Part 1 — the Board Report's Daily
        # cadence, the same once-per-real-evening gate as the three
        # daily reports directly above. Weekly/Monthly cadences are
        # deliberately not built here — CoachReport/ExecutiveReview
        # already cover them (see app/board.py's module docstring).
        daily_board_report = generate_board_report(
            cadence="daily",
            trigger=None,
            trigger_detail=None,
            research=research,
            decisions=decisions,
            agent_ids=all_agent_ids(),
            company_health=company_health,
            black_swan_tier=black_swan_intelligence.warning.tier,
            circuit_breaker_tier=daily_circuit_breaker.tier,
            pending_ceo_decisions=len(trade_proposals),
            sim_day=new_time.day,
            report_id=f"board-daily-{new_time.day}",
            now_iso=_now_iso(),
        )
        board_reports = record_board_report(board_reports, daily_board_report)

    if is_evening and new_time.day % WEEKLY_INTERVAL_DAYS == 0:
        latest_report = generate_coach_report("weekly", research, paper_portfolio, company_score, RESEARCHER_IDS, new_time, ceo_decisions=ceo_decisions, decisions=decisions)
        coach_reports = record_coach_report_entry(coach_reports, latest_report)
        record_coach_report(memory, latest_report, max_records=effective_risk_limits.max_memory_records)
        performance_snapshots = record_snapshot(performance_snapshots, compute_performance_snapshot("weekly", paper_portfolio, research, new_time))
        # v0.7 Feature 46 — "Coach quotes it": the most recent real
        # CaseStudy on record names the specific Article this week's
        # commonMistakes actually trace back to.
        if latest_report.common_mistakes and case_studies:
            recent_category = case_studies[-1].category
            coach_article = MISTAKE_ARTICLE_MAP.get(recent_category)
            if coach_article:
                constitution_citations = cite_article(constitution_citations, coach_article, "coach", f"Weekly report cites {len(latest_report.common_mistakes)} common mistake(s), echoing the {recent_category.replace('_', ' ')} pattern.", new_time.day)

    if is_evening and new_time.day % MONTHLY_INTERVAL_DAYS == 0:
        latest_report = generate_coach_report("monthly", research, paper_portfolio, company_score, RESEARCHER_IDS, new_time, ceo_decisions=ceo_decisions, decisions=decisions)
        coach_reports = record_coach_report_entry(coach_reports, latest_report)
        record_coach_report(memory, latest_report, max_records=effective_risk_limits.max_memory_records)
        performance_snapshots = record_snapshot(performance_snapshots, compute_performance_snapshot("monthly", paper_portfolio, research, new_time))
        if latest_report.common_mistakes and case_studies:
            recent_category = case_studies[-1].category
            coach_article = MISTAKE_ARTICLE_MAP.get(recent_category)
            if coach_article:
                constitution_citations = cite_article(constitution_citations, coach_article, "coach", f"Monthly report cites {len(latest_report.common_mistakes)} common mistake(s), echoing the {recent_category.replace('_', ' ')} pattern.", new_time.day)

        # v0.7 Feature 33 — the CEO Treasury's Smart Savings Rules, on the
        # same monthly cadence, using the real dollar profit the
        # performance snapshot above was itself just computed from (see
        # analytics.period_profit_dollars). Only ever moves money the CEO
        # already explicitly authorized via an active rule — see
        # treasury.py's module docstring.
        monthly_profit_dollars = period_profit_dollars("monthly", paper_portfolio, new_time)
        treasury, paper_portfolio = apply_monthly_savings_rules(
            treasury, paper_portfolio, monthly_profit_dollars=monthly_profit_dollars, sim_day=new_time.day, now_iso=_now_iso(), id_prefix=f"treasury-auto-{new_time.day}"
        )
        treasury = record_monthly_report(treasury, month_ending_day=new_time.day, now_iso=_now_iso(), report_id=f"treasury-report-{new_time.day}")

        # v0.7 Feature 24 — the CIO's own Monthly Executive Review,
        # generated on the same monthly cadence as Coach's report above
        # but asking a different question (see app/executive_review.py).
        previous_score = executive_reviews[-1].company_score if executive_reviews else None
        review = generate_executive_review(
            research=research,
            decisions=decisions,
            debates=debates,
            news=news,
            company_score=company_score,
            previous_score=previous_score,
            company_health=company_health,
            risk_limits=risk_limits,
            academy_state=academy_state,
            completed_academy_projects=academy_completed_projects,
            lessons_completed=len(state.education.completed_lesson_ids),
            agent_ids=all_agent_ids(),
            new_time=new_time,
        )
        executive_reviews = record_review(executive_reviews, review)
        record_executive_review(memory, review, max_records=effective_risk_limits.max_memory_records)

        # v0.7 Design Bible Chapter 64 (fifth pass) — the Strategic
        # Review Cycle, generated on the same monthly cadence as the
        # Executive Review above but over CEO-authored goals (see
        # app/goals.py's module docstring).
        previous_strategic_review_created_at = strategic_reviews[-1].created_at if strategic_reviews else None
        strategic_review = generate_strategic_review(
            goals,
            sim_day=new_time.day,
            new_time=new_time,
            previous_review_created_at=previous_strategic_review_created_at,
        )
        strategic_reviews = record_strategic_review(strategic_reviews, strategic_review)

        # Design Bible Chapter 74 Part 2 — the Institutional Evolution
        # Engine's own monthly report, composing this same tick's
        # freshly-generated StrategicReview/ExecutiveReview/CoachReport
        # rather than a fourth independent monthly cadence — see the
        # Design Bible chapter's own cadence/focus table.
        evolution_score = compute_company_evolution_score(
            window="monthly",
            current_sim_day=new_time.day,
            case_studies=case_studies,
            self_improvement_proposals=self_improvement_proposals,
            mentor_progress=state.foundational_mentor_state.progress,
            strategy_hall_of_fame=state.strategy_hall_of_fame,
            strategy_failed_archive=state.strategy_failed_archive,
            constitution_amendments=state.constitution.amendments,
        )
        evolution_report = generate_institutional_evolution_report(
            report_id=f"evolution-{new_time.day}",
            sim_day=new_time.day,
            strategic_reviews=strategic_reviews,
            executive_reviews=executive_reviews,
            coach_reports=coach_reports,
            case_studies=case_studies,
            self_improvement_proposals=self_improvement_proposals,
            evolution_score=evolution_score,
        )
        evolution_reports = record_evolution_report(evolution_reports, evolution_report)
        record(memory, "alert", "Institutional Evolution Report filed", evolution_report.summary, max_records=effective_risk_limits.max_memory_records)

        # v0.7 Feature 39 — the Founder Council. Real monthly sit-down
        # between the Coach and both Founders, generated alongside the
        # monthly CoachReport above (`latest_report`) — see
        # app/founders.py's module docstring for why this never
        # duplicates Sage's own daily mechanic.
        council_session = generate_council_session(
            sim_day=new_time.day,
            session_id=f"council-{new_time.day}",
            created_at=_now_iso(),
            latest_coach_report=latest_report,
            discipline_reviews=discipline_reviews,
            case_studies=case_studies,
            reasoning_challenges=reasoning_challenges,
            reflection_sessions=reflection_sessions,
        )
        founder_council_sessions = record_council_session(founder_council_sessions, council_session)
        # v0.7 Feature 46 — "Founders teach it": Keystone (risk domain)
        # and Compass (learning domain) each reaffirm the Article closest
        # to their own real real domain at every monthly sit-down.
        constitution_citations = cite_article(constitution_citations, "VII", "founders", "Keystone's monthly Council commentary reaffirms real risk discipline.", new_time.day)
        constitution_citations = cite_article(constitution_citations, "VIII", "founders", "Compass's monthly Council commentary reaffirms continuous learning.", new_time.day)

    # Design Bible Chapter 70 Part 1 — the Board Report's Quarterly
    # cadence, the one genuinely missing cadence this chapter's own
    # research confirmed (Weekly/Monthly are already real via
    # CoachReport/ExecutiveReview above).
    if is_evening and new_time.day % QUARTERLY_INTERVAL_DAYS == 0:
        quarterly_board_report = generate_board_report(
            cadence="quarterly",
            trigger=None,
            trigger_detail=None,
            research=research,
            decisions=decisions,
            agent_ids=all_agent_ids(),
            company_health=company_health,
            black_swan_tier=black_swan_intelligence.warning.tier,
            circuit_breaker_tier=daily_circuit_breaker.tier,
            pending_ceo_decisions=len(trade_proposals),
            sim_day=new_time.day,
            report_id=f"board-quarterly-{new_time.day}",
            now_iso=_now_iso(),
        )
        board_reports = record_board_report(board_reports, quarterly_board_report)

    # v0.7 Feature 25 — a modest, honestly-grounded mentorship check (see
    # app/academy.py's module docstring). Checked far less often than
    # every tick since the real points gap it watches moves slowly.
    if is_evening and new_time.day % MENTORSHIP_CHECK_INTERVAL_DAYS == 0:
        agent_knowledge, pairing, mentorship_learning_event = maybe_run_mentorship(agent_knowledge)
        if pairing is not None:
            mentor_id, mentee_id = pairing
            record_mentorship_session(memory, agent_knowledge, mentor_id, mentee_id, max_records=effective_risk_limits.max_memory_records)
        # CEO Company Health + Live Market Realism directive, Section 3
        # — a real, pre-existing gap: a mentorship bonus crossing a real
        # tier threshold used to be silently discarded (only the
        # mentorship session itself was ever recorded, never a
        # resulting tier-up). Fixed alongside this Piece.
        if mentorship_learning_event is not None:
            record_knowledge_tier_up(memory, mentorship_learning_event, max_records=effective_risk_limits.max_memory_records)
            learning_events = record_learning_event(learning_events, mentorship_learning_event)

    # v0.7 Feature 29 — the Reasoning Lab. Files one real ReasoningChallenge
    # from the company's most recent real AI Debate + its linked
    # TradeDecision, on a fixed evening cadence — practicing the reasoning
    # process itself, decoupled from any trade outcome (see
    # app/reasoning_lab.py's module docstring). Skipped when there is no
    # real Debate yet, or when the most recent Debate was already used for
    # the last challenge filed — this module never re-practices the exact
    # same already-reasoned-through case just to hit the cadence.
    if is_evening and new_time.day % REASONING_CHALLENGE_INTERVAL_DAYS == 0 and debates:
        latest_debate = debates[-1]
        linked_decision = next((d for d in decisions if d.id == f"decision-{latest_debate.proposal_id}"), None)
        already_used = bool(reasoning_challenges) and reasoning_challenges[-1].decision_id == (linked_decision.id if linked_decision else None)
        if linked_decision is not None and not already_used:
            unlocked_level = compute_reasoning_lab_state(len(reasoning_challenges)).level
            challenge = generate_challenge(
                linked_decision,
                latest_debate,
                challenge_id=f"reasoning-{latest_debate.id}",
                unlocked_level=unlocked_level,
                sim_day=new_time.day,
                created_at=_now_iso(),
            )
            reasoning_challenges = record_challenge(reasoning_challenges, challenge)
            record_reasoning_challenge(memory, challenge, max_records=effective_risk_limits.max_memory_records)

    reasoning_lab_state = compute_reasoning_lab_state(len(reasoning_challenges))

    # v0.7 Feature 30 — the Reflection Chamber. A real ReflectionSession
    # every in-game week and month; the company's Wisdom Score is
    # recomputed only at these moments, never every tick — see
    # WisdomState's own docstring for why that's a deliberate design
    # choice, not a shortcut, and app/wisdom.py's module docstring for
    # exactly which real signal answers each of the brief's nine
    # questions.
    if is_evening and (new_time.day % WEEKLY_INTERVAL_DAYS == 0 or new_time.day % MONTHLY_INTERVAL_DAYS == 0):
        wisdom_state = compute_wisdom_score(
            discipline_reviews=discipline_reviews,
            case_studies=case_studies,
            reasoning_challenges=reasoning_challenges,
            research=research,
            trade_history=paper_portfolio.trade_history,
            gatekeeper_rejections=gatekeeper_rejections,
            memory=memory,
        )
        cadence: ReflectionCadence = "monthly" if new_time.day % MONTHLY_INTERVAL_DAYS == 0 else "weekly"
        reflection_session = generate_reflection_session(
            cadence,
            discipline_reviews=discipline_reviews,
            case_studies=case_studies,
            reasoning_challenges=reasoning_challenges,
            research=research,
            news=news,
            risk_warnings=risk_warnings,
            gatekeeper_rejections=gatekeeper_rejections,
            executive_reviews=executive_reviews,
            wisdom_state=wisdom_state,
            new_time=new_time,
        )
        reflection_sessions = record_reflection_session_entry(reflection_sessions, reflection_session)
        record_reflection_session(memory, reflection_session, max_records=effective_risk_limits.max_memory_records)

    # v0.7 Feature 50 (Part 2/3) — Weekly Self-Evaluation, one real entry
    # per Executive Intelligence Network department, built from that
    # department's own real Meeting Log opinions over the trailing week.
    # Deliberately gated on the weekly condition alone (not the combined
    # weekly-or-monthly one above) — this is always a 7-day window.
    if is_evening and new_time.day % WEEKLY_INTERVAL_DAYS == 0:
        new_self_evaluations = generate_weekly_self_evaluations(meeting_log, sim_day=new_time.day)
        self_evaluations = record_self_evaluations(self_evaluations, new_self_evaluations)

    # CEO directive "Features 26-30," Feature 27 — Agent Performance
    # Reviews, one real evidence-cited review per real agent per real
    # trailing week (same weekly cadence as Self-Evaluation above).
    if is_evening and new_time.day % WEEKLY_INTERVAL_DAYS == 0:
        review_period_start = max(1, new_time.day - WEEKLY_INTERVAL_DAYS + 1)
        for review_agent_id in all_agent_ids():
            new_review = compute_agent_performance_review(
                review_agent_id,
                discipline_reviews=discipline_reviews,
                research=research,
                trades=paper_portfolio.trade_history,
                decisions=decisions,
                case_studies=case_studies,
                reasoning_challenges=reasoning_challenges,
                reflection_sessions=reflection_sessions,
                agent_knowledge=agent_knowledge,
                learning_events=learning_events,
                failure_classifications=failure_classifications,
                period_start_sim_day=review_period_start,
                period_end_sim_day=new_time.day,
                sim_day=new_time.day,
                previous_review=latest_review_for_agent(agent_performance_reviews, review_agent_id),
            )
            agent_performance_reviews = record_agent_performance_review(agent_performance_reviews, new_review)

    # CEO directive "Features 26-30," Feature 28 — Academy + Skill
    # Progression, one real evidence-cited skill snapshot per real agent
    # per real trailing week (same weekly cadence as the Performance
    # Review loop above, and deliberately run right after it so each
    # skill snapshot can read that agent's freshly-computed
    # weakest_dimension_id as its own training-recommendation trigger —
    # the CEO's own "Review flags a weak dimension -> Academy recommends
    # training" closed loop).
    if is_evening and new_time.day % WEEKLY_INTERVAL_DAYS == 0:
        skill_period_start = max(1, new_time.day - WEEKLY_INTERVAL_DAYS + 1)
        for skill_agent_id in all_agent_ids():
            new_skill_profile = compute_agent_skill_profile(
                skill_agent_id,
                discipline_reviews=discipline_reviews,
                research=research,
                trades=paper_portfolio.trade_history,
                reasoning_challenges=reasoning_challenges,
                reflection_sessions=reflection_sessions,
                failure_classifications=failure_classifications,
                period_start_sim_day=skill_period_start,
                period_end_sim_day=new_time.day,
                sim_day=new_time.day,
                previous_profile=latest_skill_profile_for_agent(agent_skill_profiles, skill_agent_id),
                latest_review=latest_review_for_agent(agent_performance_reviews, skill_agent_id),
                foundational_mentor_state=foundational_mentor_state,
            )
            agent_skill_profiles = record_agent_skill_profile(agent_skill_profiles, new_skill_profile)

    # v0.7 Feature 32 — Sage publishes one QuestionOfTheDay every in-game
    # morning (see app/mentor.py's module docstring for why the question
    # itself is drawn from a fixed, hand-authored library rather than
    # claiming free-form generation).
    if is_morning_qotd:
        question = generate_question_of_the_day(
            sim_day=new_time.day,
            question_id=f"qotd-{new_time.day}",
            created_at=_now_iso(),
            case_studies=case_studies,
            reasoning_challenges=reasoning_challenges,
            research=research,
            reflection_sessions=reflection_sessions,
            risk_warnings=risk_warnings,
            executive_reviews=executive_reviews,
        )
        question_archive = record_question(question_archive, question)

    # v0.7 Feature 32 — cheap to recompute every tick, same reasoning as
    # academy_state/reasoning_lab_state above: it only re-scans already-
    # capped lists, so it stays real-time without needing its own cadence
    # gate.
    thinking_profiles: dict[AgentId, ThinkingProfile] = compute_thinking_profiles(
        all_agent_ids(),
        discipline_reviews=discipline_reviews,
        reasoning_challenges=reasoning_challenges,
        reflection_sessions=reflection_sessions,
        agent_knowledge=agent_knowledge,
        updated_at=_now_iso(),
    )
    mentor_state = compute_mentor_state(len(question_archive), _now_iso())

    # v0.7 Feature 44 — Talent Discovery System. Only ever files a new
    # report once an agent's real trait/score-history evidence clears
    # both thresholds — see app/talent.py's module docstring.
    new_talent_reports = generate_talent_reports(
        all_agent_ids(),
        thinking_profiles,
        coach_reports,
        {r.id for r in talent_reports},
        sim_day=new_time.day,
    )
    if new_talent_reports:
        talent_reports = record_talent_reports(talent_reports, new_talent_reports)
        for report in new_talent_reports:
            news.append(
                NewsItem(
                    id=f"news-talent-{report.id}",
                    headline=f'Talent Report filed: "{report.title}".',
                    category="company",
                    timestamp=_now_iso(),
                )
            )

    # v0.7 Feature 39 — one real Founder log entry per in-game day,
    # alternating Keystone/Compass by day parity so both appear roughly
    # equally without needing two separate generations. None is recorded
    # on a day where that Founder's own domain genuinely has nothing new
    # yet (see founders.py's own honest-empty-state handling).
    if is_founder_log_hour:
        speaking_founder: FounderId = "keystone" if new_time.day % 2 == 0 else "compass"
        founder_entry = generate_founder_log_entry(
            speaking_founder,
            sim_day=new_time.day,
            entry_id=f"founder-log-{new_time.day}",
            created_at=_now_iso(),
            discipline_reviews=discipline_reviews,
            case_studies=case_studies,
            reasoning_challenges=reasoning_challenges,
            reflection_sessions=reflection_sessions,
        )
        if founder_entry is not None:
            founder_log = record_founder_log(founder_log, founder_entry)

    # v0.7 Feature 39 — cheap to recompute every tick, same reasoning as
    # company_health above: `retired` only ever needs company_health's
    # own already-fresh tier.
    founder_state = compute_founder_state(state.founder_state, company_health_tier=company_health.tier, updated_at=_now_iso())
    founder_state = founder_state.model_copy(update={"log": founder_log, "council_sessions": founder_council_sessions})
    # v0.7 Feature 48 — Legacy: the Founders' one-time, permanent
    # "Legendary Status" retirement leaves a lasting mark on Company DNA.
    # Keystone (Chief Risk Architect) and Compass (Chief Learning
    # Architect) retire together, so both domains nudge at once.
    if founder_state.retired and not state.founder_state.retired:
        company_dna_legacy = nudge_legacy(company_dna_legacy, "risk_appetite", -FOUNDER_RETIREMENT_NUDGE)
        company_dna_legacy = nudge_legacy(company_dna_legacy, "research_rigor", FOUNDER_RETIREMENT_NUDGE)

    # v0.7 — the Advanced Quantitative Research Division. Progress
    # advances once per real in-game day (not per tick), the same
    # is_evening gate the weekly/monthly cadences below already use, so a
    # project genuinely takes weeks of in-game time to reach review — see
    # app/black_box.py's module docstring. Rest Mode pauses it, same
    # convention as research/Academy above.
    if is_evening and not resting:
        prior_innovation_state = compute_innovation_state(challenge_reports)
        black_box = tick_black_box_daily(black_box, sim_day=new_time.day, innovation_state=prior_innovation_state)
        if black_box.active is not None and black_box.active.status == "under_review":
            black_box_project = black_box.active
            project_challenge = generate_project_challenge(black_box_project, existing_count=len(challenge_reports))
            challenge_reports.append(project_challenge)
            if len(challenge_reports) > MAX_CHALLENGE_REPORTS:
                del challenge_reports[: len(challenge_reports) - MAX_CHALLENGE_REPORTS]

            breakthrough_review = generate_breakthrough_review(
                black_box_project,
                challenge=project_challenge,
                sim_day=new_time.day,
                review_id=f"breakthrough-{black_box_project.id}",
                created_at=_now_iso(),
            )
            black_box = record_breakthrough_review(black_box, breakthrough_review)

            if breakthrough_review.verdict == "approved":
                completed_project = black_box_project.model_copy(update={"status": "completed", "completed_at": _now_iso()})
                black_box = archive_project(black_box, completed_project)
                # v0.7 Feature 48 — a ratified Black Box breakthrough is
                # real evidence of deep, completed research effort: a
                # small, permanent Legacy nudge to Research Rigor.
                company_dna_legacy = nudge_legacy(company_dna_legacy, "research_rigor", BLACK_BOX_BREAKTHROUGH_NUDGE)
                hall_of_fame.append(
                    HallOfFameEntry(
                        id=f"hof-breakthrough-{black_box_project.id}",
                        category="breakthrough",
                        title=black_box_project.title,
                        description=black_box_project.objective,
                        agentId="quant",
                        value=black_box_project.confidence_level,
                        achievedAt=_now_iso(),
                        discoveryTimeline=f"Day {black_box_project.started_sim_day} – Day {new_time.day}",
                        supportingEvidence=black_box_project.quant_journal[-5:],
                        companyImpact=f"Filed as an official Company Breakthrough — the {black_box_project.category.replace('_', ' ')} research is now part of TradeTown's permanent record.",
                    )
                )
                news.append(
                    NewsItem(
                        id=f"news-breakthrough-{black_box_project.id}",
                        headline=f'🧠 Breakthrough: {AGENT_PROFILES["quant"].name} and the research team confirm "{black_box_project.title}" — company reputation grows.',
                        category="discovery",
                        timestamp=_now_iso(),
                    )
                )
            else:
                failed_project = black_box_project.model_copy(
                    update={
                        "status": "failed",
                        "completed_at": _now_iso(),
                        "research_notes": [*black_box_project.research_notes, breakthrough_review.verdict_reason],
                    }
                )
                black_box = archive_project(black_box, failed_project)

    # v0.7 Feature 41 — recomputed fresh every tick from challenge_reports,
    # same "pure function of already-persisted data" reasoning as
    # compute_academy_state; cheap since it's just a running sum over a
    # capped list.
    innovation_state: dict[AgentId, InnovationState] = compute_innovation_state(challenge_reports)

    if is_midnight:
        agent_energy = regen_daily(agent_energy)
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
        record_hall_of_fame_entry(memory, entry, max_records=effective_risk_limits.max_memory_records)

    # v0.7 Feature 36 — the CEO Calendar. system_events is recomputed
    # fresh every tick from real current data (cheap — see calendar.py's
    # own module docstring), the same "always current, never stale"
    # reasoning company_health/academy_state already use; player_events
    # is only ever touched by the explicit create/delete endpoints in
    # state.py, so it's carried through unchanged here.
    calendar_state = CalendarState(
        systemEvents=compute_system_events(
            now=new_time,
            now_iso=_now_iso(),
            research=research,
            debates=debates,
            decisions=decisions,
            reasoning_challenges=reasoning_challenges,
            agent_knowledge=agent_knowledge,
            research_speed_multiplier=research_speed_multiplier,
            game_minutes_per_tick=settings.game_minutes_per_tick,
        ),
        playerEvents=state.calendar.player_events,
        updatedAt=_now_iso(),
    )

    # CEO directive "Features 31-35: Compliance, Governance & Continuous
    # Improvement System," Feature 31 — sync real ComplianceIncidents
    # from this tick's own final Audit Log (app/audit_log.py's real,
    # already-built compute_audit_log(), never a second incident-
    # detection system). Placed here, immediately before the tick's
    # final return, so every list it reads (ceo_decisions,
    # gatekeeper_rejections, opportunity_rejections, risk_warnings,
    # discipline_reviews, memory, black_swan_events) has already reached
    # its fully-updated value for this tick — no incident-worthy event
    # from this tick is missed.
    audit_entries_for_incidents = compute_audit_log(
        ceo_decisions=ceo_decisions,
        gatekeeper_rejections=gatekeeper_rejections,
        opportunity_rejections=opportunity_rejections,
        risk_warnings=risk_warnings,
        discipline_reviews=discipline_reviews,
        memory=memory,
        black_swan_events=black_swan_events,
        accounts=state.accounts,
        current_sim_day=new_time.day,
    )
    compliance_incidents = sync_incidents_from_audit_log(compliance_incidents, audit_entries_for_incidents)

    # CEO directive "Features 31-35," Feature 32 — sync new
    # CeoOverrideEvaluations from this tick's own final ceo_decisions/
    # executive_meeting_log, then refresh outcome on any override whose
    # underlying trade closed this tick (grade_ceo_decisions() above
    # already updated ceo_decisions' own outcome field by this point).
    ceo_override_evaluations = sync_override_evaluations(ceo_override_evaluations, ceo_decisions, meeting_log)
    ceo_override_evaluations = refresh_override_outcomes(ceo_override_evaluations, ceo_decisions)

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
            "strategy_reports": strategy_reports,
            "strategy_reviews": strategy_reviews,
            "strategy_monte_carlo_results": strategy_monte_carlo_results,
            "strategy_regime_tests": strategy_regime_tests,
            "strategy_liquidity_validations": strategy_liquidity_validations,
            "strategy_health_assessments": strategy_health_assessments,
            "constitution": state.constitution.model_copy(update={"citations": constitution_citations, "updated_at": _now_iso()}),
            "hall_of_fame": hall_of_fame,
            "coach_reports": coach_reports,
            "company_score": company_score,
            "performance_snapshots": performance_snapshots,
            "risk_limits": risk_limits,
            "risk_warnings": risk_warnings,
            "scanner_alerts": scanner_alerts,
            "sniper_candidates": sniper_candidates,
            "sniper_positions": sniper_positions,
            "sniper_trade_history": sniper_trade_history,
            "sniper_leads": sniper_leads,
            "sniper_lessons": sniper_lessons,
            "sniper_risk_state": sniper_risk_state,
            "decisions": decisions,
            "trade_proposals": trade_proposals,
            "ceo_decisions": ceo_decisions,
            "paper_trade_journal": paper_trade_journal,
            "drift_events": drift_events,
            "strategy_health_states": strategy_health_states,
            "prediction_records": prediction_records,
            "debates": debates,
            "gatekeeper_rejections": gatekeeper_rejections,
            "opportunity_rejections": opportunity_rejections,
            "market_environment": market_environment,
            "market_intelligence": market_intelligence,
            "market_intelligence_reports": market_intelligence_reports,
            "market_intelligence_learning": market_intelligence_learning,
            "company_health": company_health,
            "company_health_delta": company_health_delta,
            "company_dna": company_dna,
            "daily_objective_status": daily_objective_status,
            "risk_budget_status": risk_budget_status,
            "company_dna_legacy": company_dna_legacy,
            "executive_reviews": executive_reviews,
            "board_reports": board_reports,
            "academy_projects": academy_projects,
            "academy_completed_projects": academy_completed_projects,
            "goals": goals,
            "strategic_reviews": strategic_reviews,
            "agent_knowledge": agent_knowledge,
            "academy_state": academy_state,
            "discipline_reviews": discipline_reviews,
            "case_studies": case_studies,
            "failure_classifications": failure_classifications,
            "compliance_incidents": compliance_incidents,
            "ceo_override_evaluations": ceo_override_evaluations,
            "institutional_memory": institutional_memory,
            "agent_performance_reviews": agent_performance_reviews,
            "agent_skill_profiles": agent_skill_profiles,
            "learning_events": learning_events,
            "self_improvement_proposals": self_improvement_proposals,
            "evolution_reports": evolution_reports,
            "decision_vault": decision_vault,
            "war_room_sessions": war_room_sessions,
            "portfolio_intelligence": portfolio_intelligence,
            "economic_intelligence": economic_intelligence,
            "economic_intelligence_reports": economic_intelligence_reports,
            "black_swan_intelligence": black_swan_intelligence,
            "black_swan_reports": black_swan_reports,
            "defensive_mode": defensive_mode,
            "black_swan_events": black_swan_events,
            "institutional_survival_score": institutional_survival_score,
            "trading_modes": trading_mode_state,
            "daily_circuit_breaker": daily_circuit_breaker,
            "losing_streak": losing_streak,
            "behavioral_circuit_breaker": behavioral_circuit_breaker,
            "recovery_briefings": recovery_briefings,
            "travel_mode": travel_mode,
            "emergency_stop": emergency_stop,
            "reasoning_challenges": reasoning_challenges,
            "reasoning_lab_state": reasoning_lab_state,
            "reflection_sessions": reflection_sessions,
            "wisdom_state": wisdom_state,
            "question_archive": question_archive,
            "thinking_profiles": thinking_profiles,
            "mentor_state": mentor_state,
            "foundational_mentor_state": foundational_mentor_state,
            "founder_state": founder_state,
            "challenge_reports": challenge_reports,
            "innovation_state": innovation_state,
            "treasury": treasury,
            "calendar": calendar_state,
            "black_box": black_box,
            "executive_meeting_log": meeting_log,
            "department_self_evaluations": self_evaluations,
            "talent": TalentState(reports=talent_reports, viewedReportIds=state.talent.viewed_report_ids, updatedAt=_now_iso()),
            "agent_energy": agent_energy,
            "whiteboards": _update_whiteboards(agents, meeting, research),
            "updated_at": _now_iso(),
        }
    )


def apply_energy_action(state: GameSaveState, action: str, research_id: str | None) -> tuple[GameSaveState, str | None]:
    """One Agent Energy spend (v0.6.2 Phase 6 — see app/agent_energy.py's
    ACTION_COSTS) applied atomically: either the energy is spent AND the
    real effect happens, or neither does. Returns (new_state, error) —
    error is None on success. Called from app/routers/energy.py under
    game_state's lock, same as tick()."""
    energy = spend(state.agent_energy, action)
    if energy is None:
        return state, f"Insufficient Agent Energy for {action!r}, or that action doesn't exist."

    if action == "research_boost":
        if research_id is None:
            return state, "research_boost requires a researchId."
        target = next((r for r in state.research if r.id == research_id and r.status == "in_progress"), None)
        if target is None:
            return state, "That research item isn't currently in progress (already completed, or an unknown id)."
        boosted = target.model_copy(update={"confidence": min(100.0, target.confidence + RESEARCH_BOOST_AMOUNT), "updated_at": _now_iso()})
        research = [boosted if r.id == research_id else r for r in state.research]
        return state.model_copy(update={"research": research, "agent_energy": energy}), None

    if action == "extra_simulation":
        sessions = queue_backtest_now(list(state.backtest_sessions), state.strategies, state.watchlist, RESEARCHER_IDS, state.time)
        if sessions is None:
            return state, "The Simulation Lab is already running at capacity — try again once a session finishes."
        return state.model_copy(update={"backtest_sessions": sessions, "agent_energy": energy}), None

    if action == "watch_symbol":
        result = add_symbol_to_watchlist(state.watchlist, market_data_provider)
        if result is None:
            return state, "Every available symbol is already being monitored."
        watchlist, _symbol = result
        return state.model_copy(update={"watchlist": watchlist, "agent_energy": energy}), None

    return state, f"Unknown action {action!r}."
