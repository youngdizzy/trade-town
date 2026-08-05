"""In-memory authoritative game state, shared across all connected clients.

TradeTown is single-tenant (one company, one save slot) — this is
intentionally a process-wide singleton rather than per-session state.
Agent/task/whiteboard/meeting orchestration itself lives in nexus.py; this
module just owns the lock-guarded snapshot and the game clock.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Callable

from app import education, nexus, player_vs_ai, signal_calibration, trade_notifications
from app.academy import compute_academy_state, default_agent_knowledge
from app.agents import AGENT_PROFILES, all_agent_ids
from app.black_box import archive_project, default_black_box_state, mark_breakthrough_viewed
from app.config import settings
from app.mentor import compute_mentor_state, compute_thinking_profiles, generate_question_of_the_day, submit_response
from app.calendar import create_player_event, default_calendar, delete_player_event
from app.treasury import create_rule, default_treasury, deposit, pause_all_rules, toggle_rule, withdraw
from app.reasoning_lab import compute_reasoning_lab_state
from app.wisdom import compute_wisdom_score
from app.academy_research import default_academy_projects
from app.agent_energy import default_agent_energy
from app.company_dna import STRATEGY_HALL_OF_FAME_NUDGE, compute_company_dna, nudge_legacy
from app.company_health import compute_company_health
from app.company_score import compute_company_score
from app.constitution import decide_amendment, default_constitution, generate_coach_evaluation, generate_employee_votes, generate_founder_debate, propose_amendment, ratify_amendment
from app.debate import generate_debate
from app.devils_advocate import MAX_CHALLENGE_REPORTS, generate_challenge_report
from app.executive import MAX_CEO_DECISIONS, MAX_PROPOSAL_HOLDS, AnalystChoice, hold_proposal, resolve_proposal
from app.executive_intelligence import generate_meeting_log_entry, record_meeting_log_entry
from app.innovation import compute_innovation_state
from app.market_data import market_data_provider
from app.market_environment import default_market_environment
from app.market_intelligence import compute_market_intelligence_state
from app.nexus import MAX_DEBATES, MAX_DECISIONS, MAX_GATEKEEPER_REJECTIONS
from app.portfolio import default_portfolio, sim_minutes
from app.portfolio_intelligence import compute_portfolio_intelligence
from app.research import RESEARCHER_IDS, default_research
from app.risk_engine import compute_daily_objective_status, default_risk_limits
from app.sandbox import apply_review_decision, begin_company_review, begin_limited_live, begin_paper_trial, generate_strategy_review
from app.sandbox import retire_strategy as retire_strategy_stage
from app.scribe import record_ceo_decision, record_proposal_hold, record_strategy_failed_archive_entry, record_strategy_hall_of_fame_entry
from app.schemas import (
    AgentId,
    BlackBoxPriority,
    BlackBoxProject,
    ClientSaveRequest,
    EducationProgress,
    EntityTransform,
    FounderState,
    FoundationalMentorId,
    FoundationalResourceType,
    GameSaveState,
    GatekeeperRejection,
    HoldReason,
    MeetingState,
    NewsItem,
    PlayerEventCategory,
    PlayerVsAiPrompt,
    PlayerVsAiState,
    SavingsRuleType,
    SettingsState,
    SignalCalibrationState,
    SignalChoice,
    Strategy,
    TalentState,
    TestScenario,
    TierAllocationLimits,
    TimeAdvanceTarget,
    TimeState,
)
from app.foundational_mentors import (
    add_custom_lesson as add_custom_academy_lesson_entry,
    add_custom_mentor as add_custom_academy_mentor_entry,
    add_resource as add_foundational_mentor_resource_entry,
    approve_graduation as approve_foundational_mentor_graduation,
    default_foundational_mentor_state,
    downgrade_certification,
    grade_ceo_lesson_quiz,
    mark_ceo_lesson_viewed,
    pause_company_training,
    promote_certification,
    repeat_mentor_company_wide,
    reset_certification_progress,
    resume_company_training,
    revoke_certification,
    set_active_mentor,
    skip_to_next_mentor,
)
from app.simulation import default_strategies, queue_backtest_now
from app.strategy_lab import (
    cap_strategy_executive_reviews,
    cap_strategy_failed_archive,
    cap_strategy_founder_approvals,
    cap_strategy_hall_of_fame,
    evaluate_certification_readiness,
    generate_strategy_executive_review,
    generate_strategy_founder_approval,
    generate_strategy_retirement_outcome,
)
from app.talent import mark_talent_report_viewed
from app.watchlist import default_watchlist

MAX_DIALOGUE_HISTORY = 200
MAX_BLACK_BOX_FUNDING_PER_CALL = 5000.0
MAX_BLACK_BOX_NOTES = 20
# v0.7 Feature 34 — CEO time controls. MAX_FAST_FORWARD_HOURS bounds the
# custom "hours" target; MAX_FAST_FORWARD_TICKS is a hard safety ceiling
# on week_end/month_end (worst case ~2016/~8640 real ticks at the default
# 5-minute step — see GameState.advance_time()) so a bug in the stop
# predicate can never spin the loop forever.
MAX_FAST_FORWARD_HOURS = 72
MAX_FAST_FORWARD_TICKS = 10_000


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_state() -> GameSaveState:
    agents = nexus.default_agents()
    watchlist = default_watchlist()
    signal_calibration_state = SignalCalibrationState()
    education_progress = education.default_education_progress()
    agent_knowledge = default_agent_knowledge()
    seed_research = default_research()
    # v0.7 Feature 50 (Part 2/3) — computed once here so both
    # companyHealth (its institutionalMemory/talentDevelopment executive
    # metrics) and their own top-level fields below reuse the exact same
    # fresh-game default rather than two independently-invented ones.
    default_wisdom_state = compute_wisdom_score(
        discipline_reviews=[],
        case_studies=[],
        reasoning_challenges=[],
        research=seed_research,
        trade_history=[],
        gatekeeper_rejections=[],
        memory=[],
    )
    default_foundational_mentors = default_foundational_mentor_state()
    return GameSaveState(
        player=EntityTransform(scene="LobbyScene", x=160, y=220, facing="down"),
        agents=agents,
        tasks=[],
        whiteboards={},
        meeting=MeetingState(),
        news=[],
        research=seed_research,
        watchlist=watchlist,
        memory=[],
        meetingMinutes=[],
        time=TimeState(day=1, hour=8, minute=0),
        settings=SettingsState(musicVolume=0.5, sfxVolume=0.7, autosaveIntervalSec=60, showFps=False, operatingMode="learning"),
        dialogueHistory=[],
        paperPortfolio=default_portfolio(),
        strategies=default_strategies(),
        backtestSessions=[],
        simulationResults=[],
        strategyReports=[],
        strategyReviews=[],
        strategyMonteCarloResults=[],
        strategyRegimeTests=[],
        strategyLiquidityValidations=[],
        strategyExecutiveReviews=[],
        strategyFounderApprovals=[],
        strategyHealthAssessments=[],
        strategyHallOfFame=[],
        strategyFailedArchive=[],
        hallOfFame=[],
        coachReports=[],
        companyScore=compute_company_score([], default_portfolio(), [], [], []),
        performanceSnapshots=[],
        agentEnergy=default_agent_energy(),
        signalCalibration=signal_calibration_state,
        playerVsAi=PlayerVsAiState(),
        education=education_progress,
        viewedTradeNotificationIds=[],
        tradeProposals=[],
        ceoDecisions=[],
        debates=[],
        gatekeeperRejections=[],
        opportunityRejections=[],
        marketEnvironment=default_market_environment(),
        marketIntelligence=compute_market_intelligence_state(watchlist, [], [], market_data_provider),
        marketIntelligenceReports=[],
        marketIntelligenceLearning=[],
        companyHealth=compute_company_health(
            agents=agents,
            research=[],
            portfolio=default_portfolio(),
            risk_warnings=[],
            agent_energy=default_agent_energy(),
            hall_of_fame=[],
            signal_calibration=signal_calibration_state,
            watchlist=watchlist,
            education=education_progress,
            debates=[],
            decisions=[],
            meeting_log=[],
            self_evaluations=[],
            wisdom_state=default_wisdom_state,
            innovation_state={},
            foundational_mentor_state=default_foundational_mentors,
            founder_council_sessions=[],
            gatekeeper_rejections=[],
        ),
        companyDna=compute_company_dna([], [], []),
        dailyObjectiveStatus=compute_daily_objective_status(default_risk_limits(), default_portfolio(), 1),
        executiveReviews=[],
        academyProjects=default_academy_projects(),
        academyCompletedProjects=[],
        agentKnowledge=agent_knowledge,
        academyState=compute_academy_state(agent_knowledge, 0),
        disciplineReviews=[],
        caseStudies=[],
        reasoningChallenges=[],
        reasoningLabState=compute_reasoning_lab_state(0),
        reflectionSessions=[],
        wisdomState=default_wisdom_state,
        questionArchive=[
            generate_question_of_the_day(
                sim_day=1,
                question_id="qotd-1",
                created_at=_now_iso(),
                case_studies=[],
                reasoning_challenges=[],
                research=seed_research,
                reflection_sessions=[],
                risk_warnings=[],
                executive_reviews=[],
            )
        ],
        thinkingProfiles=compute_thinking_profiles(
            all_agent_ids(),
            discipline_reviews=[],
            reasoning_challenges=[],
            reflection_sessions=[],
            agent_knowledge=agent_knowledge,
            updated_at=_now_iso(),
        ),
        mentorState=compute_mentor_state(1, _now_iso()),
        foundationalMentorState=default_foundational_mentors,
        founderState=FounderState(updatedAt=_now_iso()),
        challengeReports=[],
        innovationState={},
        treasury=default_treasury(_now_iso()),
        calendar=default_calendar(_now_iso()),
        blackBox=default_black_box_state(),
        talent=TalentState(reports=[], viewedReportIds=[], updatedAt=_now_iso()),
        constitution=default_constitution(),
        warRoomSessions=[],
        portfolioIntelligence=compute_portfolio_intelligence(default_portfolio(), market_data_provider, pending_proposal_count=0),
        updatedAt=_now_iso(),
    )


class GameState:
    """Thread-safe (via asyncio.Lock) holder for the single authoritative save."""

    def __init__(self) -> None:
        self.data: GameSaveState = default_state()
        self.lock = asyncio.Lock()

    async def apply_client_save(self, incoming: ClientSaveRequest) -> GameSaveState:
        """Merge a client-submitted save. Player position/settings/dialogue come from
        the client; agents/tasks/whiteboards/meeting/news/time stay server-authoritative
        (NEXUS's tick loop owns them) — see ClientSaveRequest's own docstring for why
        the request body is deliberately this narrow rather than a full GameSaveState."""
        async with self.lock:
            self.data = self.data.model_copy(
                update={
                    "player": incoming.player,
                    "settings": incoming.settings,
                    "dialogue_history": incoming.dialogue_history[-MAX_DIALOGUE_HISTORY:],
                    "updated_at": _now_iso(),
                }
            )
            return self.data

    async def load_from(self, saved: GameSaveState) -> None:
        async with self.lock:
            self.data = nexus.register_agents(saved)

    async def snapshot(self) -> GameSaveState:
        async with self.lock:
            return self.data

    async def spend_agent_energy(self, action: str, research_id: str | None) -> tuple[GameSaveState, str | None]:
        """One Agent Energy spend, applied atomically under the same lock
        tick() uses. Returns (state, error) — error is None on success."""
        async with self.lock:
            self.data, error = nexus.apply_energy_action(self.data, action, research_id)
            return self.data, error

    async def submit_signal_calibration(self, challenge_id: str, choice: SignalChoice) -> tuple[GameSaveState, str | None]:
        """Grades a pending Signal Calibration challenge under the same
        lock every other state mutation uses, so a submit can never race a
        concurrent tick()/save. Returns (state, error)."""
        async with self.lock:
            new_calibration, new_energy, error = signal_calibration.grade_submission(
                self.data.signal_calibration, self.data.agent_energy, challenge_id, choice
            )
            if error is None:
                self.data = self.data.model_copy(update={"signal_calibration": new_calibration, "agent_energy": new_energy})
            return self.data, error

    async def generate_player_vs_ai_prompt(self) -> tuple[PlayerVsAiPrompt | None, str | None]:
        """Read-only aside from the transient pending-prompt store (see
        player_vs_ai.py) — still taken under the lock so it reads a
        consistent snapshot of decisions/trade history/research rather
        than one torn by a concurrent tick()."""
        async with self.lock:
            used_decision_ids = {r.decision_id for r in self.data.player_vs_ai.rounds}
            try:
                prompt = player_vs_ai.generate_prompt(
                    self.data.decisions, self.data.paper_portfolio.trade_history, self.data.research, market_data_provider, used_decision_ids
                )
                return prompt, None
            except ValueError as exc:
                return None, str(exc)

    async def submit_player_vs_ai(self, prompt_id: str, choice: SignalChoice) -> tuple[GameSaveState, str | None]:
        """Grades a pending Player vs AI round under the same lock every
        other state mutation uses. Returns (state, error)."""
        async with self.lock:
            new_player_vs_ai, error = player_vs_ai.grade_submission(self.data.player_vs_ai, prompt_id, choice)
            if error is None:
                self.data = self.data.model_copy(update={"player_vs_ai": new_player_vs_ai})
            return self.data, error

    async def submit_qotd_response(self, question_id: str, response: str) -> tuple[GameSaveState, str | None]:
        """Stores the player's free-text QuestionOfTheDay answer, under
        the same lock every other state mutation uses. Never graded —
        see app/mentor.py's module docstring."""
        async with self.lock:
            new_archive, error = submit_response(self.data.question_archive, question_id, response, responded_at=_now_iso())
            if error is None:
                self.data = self.data.model_copy(update={"question_archive": new_archive})
            return self.data, error

    async def view_ceo_academy_lesson(self, mentor_id: FoundationalMentorId, lesson_id: str) -> GameSaveState:
        """The CEO's own optional Learning Mode — never touches real
        employee progress. See app/foundational_mentors.py's module
        docstring."""
        async with self.lock:
            new_state = mark_ceo_lesson_viewed(self.data.foundational_mentor_state, mentor_id, lesson_id)
            self.data = self.data.model_copy(update={"foundational_mentor_state": new_state})
            return self.data

    async def grade_ceo_academy_quiz(self, mentor_id: FoundationalMentorId, lesson_id: str, selected_index: int) -> tuple[GameSaveState, bool, int, str] | None:
        async with self.lock:
            result = grade_ceo_lesson_quiz(self.data.foundational_mentor_state, mentor_id, lesson_id, selected_index)
            if result is None:
                return None
            new_state, correct, correct_index, correct_option = result
            self.data = self.data.model_copy(update={"foundational_mentor_state": new_state})
            return self.data, correct, correct_index, correct_option

    async def approve_academy_graduation(self, agent_id: AgentId, mentor_id: FoundationalMentorId) -> tuple[GameSaveState, bool, str | None]:
        """The real Graduation Queue's Approve button — a real CEO
        action, not automatic (see module docstring)."""
        async with self.lock:
            new_state, company_graduated, error = approve_foundational_mentor_graduation(self.data.foundational_mentor_state, agent_id, mentor_id, sim_day=self.data.time.day)
            if error is None:
                self.data = self.data.model_copy(update={"foundational_mentor_state": new_state})
            return self.data, company_graduated, error

    async def downgrade_academy_certification(self, agent_id: AgentId, mentor_id: FoundationalMentorId, reason: str) -> tuple[GameSaveState, str | None]:
        """Certification Management's Downgrade action — Active -> Suspended."""
        async with self.lock:
            new_state, error = downgrade_certification(self.data.foundational_mentor_state, agent_id, mentor_id, reason=reason, sim_day=self.data.time.day)
            if error is None:
                self.data = self.data.model_copy(update={"foundational_mentor_state": new_state})
            return self.data, error

    async def promote_academy_certification(self, agent_id: AgentId, mentor_id: FoundationalMentorId, reason: str | None) -> tuple[GameSaveState, str | None]:
        """Certification Management's Promote action — Suspended -> Active,
        only "eligible" (offered) while suspended."""
        async with self.lock:
            new_state, error = promote_certification(self.data.foundational_mentor_state, agent_id, mentor_id, sim_day=self.data.time.day, reason=reason)
            if error is None:
                self.data = self.data.model_copy(update={"foundational_mentor_state": new_state})
            return self.data, error

    async def revoke_academy_certification(self, agent_id: AgentId, mentor_id: FoundationalMentorId, reason: str) -> tuple[GameSaveState, str | None]:
        """Certification Management's Revoke action — a real CEO action,
        the mirror image of approve_academy_graduation above. Also
        appends a real Newspaper "company"-category news item — this
        codebase's real analog to an Executive Log — recording exactly
        which certification was revoked, by whom, and why, matching the
        brief's requested "Day N / X's Y Certification revoked by CEO. /
        Reason: ..." format."""
        async with self.lock:
            mentor_label = next((m.track_label for m in self.data.foundational_mentor_state.mentors if m.id == mentor_id), mentor_id)
            new_state, error = revoke_certification(self.data.foundational_mentor_state, agent_id, mentor_id, reason=reason, sim_day=self.data.time.day)
            if error is not None:
                return self.data, error
            agent_name = AGENT_PROFILES[agent_id].name if agent_id in AGENT_PROFILES else agent_id
            headline = f"Day {self.data.time.day} — {agent_name}'s {mentor_label} Certification revoked by CEO. Reason: {reason.strip()}"
            news_item = NewsItem(id=f"news-cert-revoke-{agent_id}-{mentor_id}-{self.data.time.day}-{len(self.data.news)}", headline=headline, category="company", timestamp=_now_iso())
            self.data = self.data.model_copy(update={"foundational_mentor_state": new_state, "news": [*self.data.news, news_item]})
            return self.data, None

    async def reset_academy_certification_progress(self, agent_id: AgentId, mentor_id: FoundationalMentorId) -> tuple[GameSaveState, str | None]:
        """Certification Management's Reset Progress action — only
        offered on an already-revoked certification (see
        reset_certification_progress's own docstring)."""
        async with self.lock:
            new_state, error = reset_certification_progress(self.data.foundational_mentor_state, agent_id, mentor_id, sim_day=self.data.time.day)
            if error is None:
                self.data = self.data.model_copy(update={"foundational_mentor_state": new_state})
            return self.data, error

    async def pause_academy_training(self) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            new_state, error = pause_company_training(self.data.foundational_mentor_state)
            if error is None:
                self.data = self.data.model_copy(update={"foundational_mentor_state": new_state})
            return self.data, error

    async def resume_academy_training(self) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            new_state, error = resume_company_training(self.data.foundational_mentor_state)
            if error is None:
                self.data = self.data.model_copy(update={"foundational_mentor_state": new_state})
            return self.data, error

    async def skip_academy_to_next_mentor(self) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            new_state, error = skip_to_next_mentor(self.data.foundational_mentor_state)
            if error is None:
                self.data = self.data.model_copy(update={"foundational_mentor_state": new_state})
            return self.data, error

    async def repeat_academy_mentor(self, mentor_id: FoundationalMentorId) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            new_state, error = repeat_mentor_company_wide(self.data.foundational_mentor_state, mentor_id)
            if error is None:
                self.data = self.data.model_copy(update={"foundational_mentor_state": new_state})
            return self.data, error

    async def add_foundational_mentor_resource(
        self, mentor_id: FoundationalMentorId, *, title: str, url: str | None, resource_type: FoundationalResourceType
    ) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            new_state, error = add_foundational_mentor_resource_entry(self.data.foundational_mentor_state, mentor_id, title=title, url=url, resource_type=resource_type)
            if error is None:
                self.data = self.data.model_copy(update={"foundational_mentor_state": new_state})
            return self.data, error

    async def add_custom_academy_mentor(self, *, name: str, track_label: str, focus_areas: list[str]) -> tuple[GameSaveState, str | None, str | None]:
        """The Mentor Lab's real "Add New Mentor" action. Returns
        (state, new_mentor_id, error)."""
        async with self.lock:
            new_state, mentor_id, error = add_custom_academy_mentor_entry(self.data.foundational_mentor_state, name=name, track_label=track_label, focus_areas=focus_areas)
            if error is None:
                self.data = self.data.model_copy(update={"foundational_mentor_state": new_state})
            return self.data, mentor_id, error

    async def add_custom_academy_lesson(
        self,
        mentor_id: FoundationalMentorId,
        *,
        title: str,
        simple_explanation: str,
        deeper_explanation: str,
        quiz_question: str,
        quiz_options: list[str],
        correct_index: int,
    ) -> tuple[GameSaveState, str | None]:
        """The Mentor Lab's real "Build Academy Curriculum" action — a
        CEO-authored lesson for any mentor track."""
        async with self.lock:
            new_state, error = add_custom_academy_lesson_entry(
                self.data.foundational_mentor_state,
                mentor_id,
                title=title,
                simple_explanation=simple_explanation,
                deeper_explanation=deeper_explanation,
                quiz_question=quiz_question,
                quiz_options=quiz_options,
                correct_index=correct_index,
            )
            if error is None:
                self.data = self.data.model_copy(update={"foundational_mentor_state": new_state})
            return self.data, error

    async def set_active_academy_mentor(self, mentor_id: FoundationalMentorId) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            new_state, error = set_active_mentor(self.data.foundational_mentor_state, mentor_id)
            if error is None:
                self.data = self.data.model_copy(update={"foundational_mentor_state": new_state})
            return self.data, error

    async def update_risk_limits(
        self,
        *,
        daily_profit_target_pct: float | None = None,
        max_daily_loss_pct: float | None = None,
        max_trades_per_day: int | None = None,
        risk_per_trade_pct: float | None = None,
        max_open_positions: int | None = None,
        max_weekly_deployment_pct: float | None = None,
        portfolio_heat_cap_pct: float | None = None,
        clear_portfolio_heat_cap: bool = False,
        cash_reserve_pct: float | None = None,
        tier_allocation: TierAllocationLimits | None = None,
        min_trade_quality_score: float | None = None,
        min_expected_value_pct: float | None = None,
        min_priority_score: float | None = None,
        capital_reserve_pct: float | None = None,
        min_similar_matches: int | None = None,
        mistake_warning_share_pct: float | None = None,
        max_decision_vault_entries: int | None = None,
        max_memory_records: int | None = None,
        max_limited_live_capital: float | None = None,
    ) -> tuple[GameSaveState, str | None]:
        """v0.7 Feature 49 — the CEO's Daily Trading Objectives — extended
        by v0.7 Chapter 57 with four of the six new Position Sizing
        controls (`scaling_aggressiveness_pct`/`emergency_reduction_
        heat_pct` are not writable here — see app/position_sizing.py's
        own honesty boundary; those two fields have no real consumer
        until Position Scaling/Reduction on already-open positions is
        built, and a control that changes a number nothing reads would
        be a placeholder), by v0.7 Chapter 58 with the Opportunity
        Gatekeeper's two new controls (`min_trade_quality_score`,
        `min_expected_value_pct` — see app/opportunity_gatekeeper.py),
        by v0.7 Chapter 59 with the Capital Priority & Opportunity
        Cost Engine's two new controls (`min_priority_score`,
        `capital_reserve_pct` — see app/capital_priority.py), and by
        v0.7 Chapter 61 with the Knowledge Graph & Company Memory
        Engine's Pattern Detection Sensitivity controls
        (`min_similar_matches`, `mistake_warning_share_pct` — see
        app/decision_vault.py's Similarity Engine) and its Knowledge
        Retention Rules control, both slices (`max_decision_vault_entries`
        — see app/decision_vault.py's record_vault_entry;
        `max_memory_records` — see app/memory.py's record(), threaded
        through every app/scribe.py wrapper), and by v0.7 Design Bible
        Chapter 62 with the Innovation Lab's Innovation Budget control
        (`max_limited_live_capital` — see app/sandbox.py's
        begin_limited_live()).
        Every field is optional so a single call can update just one
        limit; each provided value is validated before being merged into
        the real RiskLimits object app/risk_engine.py,
        app/position_sizing.py, and app/opportunity_gatekeeper.py already
        enforce every tick — no separate "pending CEO settings" object,
        the change takes effect on the very next generated trade
        proposal. `clear_portfolio_heat_cap` is a separate explicit flag
        (not just passing `None`) so "field omitted" and "CEO wants to
        disable the cap" are distinguishable — the same ambiguity
        `float | None` alone can't resolve."""
        async with self.lock:
            updates: dict[str, float | int | TierAllocationLimits | None] = {}
            if daily_profit_target_pct is not None:
                if daily_profit_target_pct <= 0:
                    return self.data, "Daily profit target must be a positive percentage."
                updates["daily_profit_target_pct"] = daily_profit_target_pct
            if max_daily_loss_pct is not None:
                if max_daily_loss_pct <= 0:
                    return self.data, "Daily maximum loss must be a positive percentage."
                updates["max_daily_loss_pct"] = max_daily_loss_pct
            if max_trades_per_day is not None:
                if max_trades_per_day <= 0:
                    return self.data, "Maximum trades per day must be a positive whole number."
                updates["max_trades_per_day"] = max_trades_per_day
            if risk_per_trade_pct is not None:
                if risk_per_trade_pct <= 0:
                    return self.data, "Maximum risk per trade must be a positive percentage."
                updates["risk_per_trade_pct"] = risk_per_trade_pct
            if max_open_positions is not None:
                if max_open_positions <= 0:
                    return self.data, "Maximum open positions must be a positive whole number."
                updates["max_open_positions"] = max_open_positions
            if max_weekly_deployment_pct is not None:
                if max_weekly_deployment_pct <= 0:
                    return self.data, "Maximum weekly deployment must be a positive percentage."
                updates["max_weekly_deployment_pct"] = max_weekly_deployment_pct
            if clear_portfolio_heat_cap:
                updates["portfolio_heat_cap_pct"] = None
            elif portfolio_heat_cap_pct is not None:
                if portfolio_heat_cap_pct <= 0:
                    return self.data, "Portfolio Heat cap must be a positive percentage."
                updates["portfolio_heat_cap_pct"] = portfolio_heat_cap_pct
            if cash_reserve_pct is not None:
                if cash_reserve_pct < 0 or cash_reserve_pct >= 100:
                    return self.data, "Cash reserve must be a percentage from 0 up to (not including) 100."
                updates["cash_reserve_pct"] = cash_reserve_pct
            if tier_allocation is not None:
                if min(tier_allocation.tier1_pct, tier_allocation.tier2_pct, tier_allocation.tier3_pct, tier_allocation.tier4_pct) <= 0:
                    return self.data, "Every Position Tier allocation must be a positive percentage."
                updates["tier_allocation"] = tier_allocation
            if min_trade_quality_score is not None:
                if min_trade_quality_score < 0 or min_trade_quality_score > 100:
                    return self.data, "Minimum Trade Quality Score must be a percentage from 0 to 100."
                updates["min_trade_quality_score"] = min_trade_quality_score
            if min_expected_value_pct is not None:
                updates["min_expected_value_pct"] = min_expected_value_pct
            if min_priority_score is not None:
                if min_priority_score < 0 or min_priority_score > 100:
                    return self.data, "Minimum Priority Score must be a percentage from 0 to 100."
                updates["min_priority_score"] = min_priority_score
            if capital_reserve_pct is not None:
                if capital_reserve_pct < 0 or capital_reserve_pct >= 100:
                    return self.data, "Capital Reserve must be a percentage from 0 up to (not including) 100."
                updates["capital_reserve_pct"] = capital_reserve_pct
            if min_similar_matches is not None:
                if min_similar_matches < 1:
                    return self.data, "Minimum Similar Matches must be at least 1."
                updates["min_similar_matches"] = min_similar_matches
            if mistake_warning_share_pct is not None:
                if mistake_warning_share_pct <= 0 or mistake_warning_share_pct > 100:
                    return self.data, "Mistake Warning Share must be a percentage from 0 (exclusive) to 100."
                updates["mistake_warning_share_pct"] = mistake_warning_share_pct
            if max_decision_vault_entries is not None:
                if max_decision_vault_entries < 1:
                    return self.data, "Maximum Decision Vault Entries must be at least 1."
                updates["max_decision_vault_entries"] = max_decision_vault_entries
            if max_memory_records is not None:
                if max_memory_records < 1:
                    return self.data, "Maximum Memory Records must be at least 1."
                updates["max_memory_records"] = max_memory_records
            if max_limited_live_capital is not None:
                if max_limited_live_capital <= 0:
                    return self.data, "Maximum Limited Live Capital must be a positive amount."
                updates["max_limited_live_capital"] = max_limited_live_capital
            if not updates:
                return self.data, "No risk limit changes were provided."
            new_limits = self.data.risk_limits.model_copy(update=updates)
            self.data = self.data.model_copy(update={"risk_limits": new_limits})
            return self.data, None

    async def deposit_treasury(self, amount: float) -> tuple[GameSaveState, str | None]:
        """CEO-initiated Operating Capital -> Treasury transfer, under the
        same lock every other state mutation uses. Returns (state, error)."""
        async with self.lock:
            time = self.data.time
            transaction_id = f"treasury-deposit-{time.day}-{time.hour}-{time.minute}-{len(self.data.treasury.transactions)}"
            new_treasury, new_portfolio, error = deposit(self.data.treasury, self.data.paper_portfolio, amount, sim_day=time.day, now_iso=_now_iso(), transaction_id=transaction_id)
            if error is None:
                self.data = self.data.model_copy(update={"treasury": new_treasury, "paper_portfolio": new_portfolio})
            return self.data, error

    async def withdraw_treasury(self, amount: float) -> tuple[GameSaveState, str | None]:
        """CEO-initiated Treasury -> Operating Capital transfer, under the
        same lock every other state mutation uses. Returns (state, error)."""
        async with self.lock:
            time = self.data.time
            transaction_id = f"treasury-withdraw-{time.day}-{time.hour}-{time.minute}-{len(self.data.treasury.transactions)}"
            new_treasury, new_portfolio, error = withdraw(self.data.treasury, self.data.paper_portfolio, amount, sim_day=time.day, now_iso=_now_iso(), transaction_id=transaction_id)
            if error is None:
                self.data = self.data.model_copy(update={"treasury": new_treasury, "paper_portfolio": new_portfolio})
            return self.data, error

    async def create_savings_rule(self, rule_type: SavingsRuleType, percent: float, reserve_target: float | None) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            time = self.data.time
            rule_id = f"savings-rule-{time.day}-{time.hour}-{time.minute}-{len(self.data.treasury.savings_rules)}"
            new_treasury, error = create_rule(self.data.treasury, rule_type, percent=percent, reserve_target=reserve_target, now_iso=_now_iso(), rule_id=rule_id)
            if error is None:
                self.data = self.data.model_copy(update={"treasury": new_treasury})
            return self.data, error

    async def toggle_savings_rule(self, rule_id: str, active: bool) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            new_treasury, error = toggle_rule(self.data.treasury, rule_id, active, now_iso=_now_iso())
            if error is None:
                self.data = self.data.model_copy(update={"treasury": new_treasury})
            return self.data, error

    async def pause_all_savings_rules(self) -> GameSaveState:
        async with self.lock:
            self.data = self.data.model_copy(update={"treasury": pause_all_rules(self.data.treasury, now_iso=_now_iso())})
            return self.data

    async def _update_black_box_project(self, mutate: Callable[[BlackBoxProject], BlackBoxProject | None], *, no_project_error: str) -> tuple[GameSaveState, str | None]:
        """Shared lock/validate/persist plumbing for every CEO Research
        Dashboard control below — each one only needs to say how the
        active project changes."""
        async with self.lock:
            active = self.data.black_box.active
            if active is None:
                return self.data, no_project_error
            updated = mutate(active)
            if updated is None:
                return self.data, "That action isn't valid for the current project."
            new_black_box = self.data.black_box.model_copy(update={"active": updated.model_copy(update={"updated_at": _now_iso()}), "updated_at": _now_iso()})
            self.data = self.data.model_copy(update={"black_box": new_black_box})
            return self.data, None

    async def fund_black_box_project(self, amount: float) -> tuple[GameSaveState, str | None]:
        """CEO-initiated Black Box funding — see app/black_box.py's module
        docstring for why this is a standalone project budget number
        rather than drawn from app/treasury.py's Treasury balance (which
        that module's own docstring documents as touched only by its own
        three explicit CEO actions)."""
        if amount <= 0:
            return self.data, "Funding amount must be positive."
        if amount > MAX_BLACK_BOX_FUNDING_PER_CALL:
            return self.data, f"Can't add more than ${MAX_BLACK_BOX_FUNDING_PER_CALL:,.0f} in a single funding action."
        return await self._update_black_box_project(
            lambda p: p.model_copy(update={"budget": round(p.budget + amount, 2)}), no_project_error="No Black Box project is currently active."
        )

    async def set_black_box_paused(self, paused: bool) -> tuple[GameSaveState, str | None]:
        def mutate(p: BlackBoxProject) -> BlackBoxProject | None:
            if p.status not in ("active", "paused"):
                return None
            return p.model_copy(update={"status": "paused" if paused else "active"})

        return await self._update_black_box_project(mutate, no_project_error="No Black Box project is currently active.")

    async def cancel_black_box_project(self) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            active = self.data.black_box.active
            if active is None:
                return self.data, "No Black Box project is currently active."
            cancelled = active.model_copy(
                update={"status": "failed", "completed_at": _now_iso(), "research_notes": [*active.research_notes, "Cancelled by the CEO before completion."]}
            )
            new_black_box = archive_project(self.data.black_box, cancelled)
            self.data = self.data.model_copy(update={"black_box": new_black_box})
            return self.data, None

    async def set_black_box_priority(self, priority: BlackBoxPriority) -> tuple[GameSaveState, str | None]:
        return await self._update_black_box_project(
            lambda p: p.model_copy(update={"priority": priority}), no_project_error="No Black Box project is currently active."
        )

    async def add_black_box_note(self, note: str) -> tuple[GameSaveState, str | None]:
        stripped = note.strip()
        if not stripped:
            return self.data, "A research note can't be empty."

        def mutate(p: BlackBoxProject) -> BlackBoxProject:
            notes = [*p.research_notes, stripped]
            if len(notes) > MAX_BLACK_BOX_NOTES:
                del notes[: len(notes) - MAX_BLACK_BOX_NOTES]
            return p.model_copy(update={"research_notes": notes})

        return await self._update_black_box_project(mutate, no_project_error="No Black Box project is currently active.")

    async def reassign_black_box_specialist(self, agent_id: AgentId, new_agent_id: AgentId) -> tuple[GameSaveState, str | None]:
        def mutate(p: BlackBoxProject) -> BlackBoxProject | None:
            if agent_id == "quant" or not any(m.agent_id == agent_id for m in p.team):
                return None
            team = [m.model_copy(update={"agent_id": new_agent_id}) if m.agent_id == agent_id else m for m in p.team]
            return p.model_copy(update={"team": team})

        return await self._update_black_box_project(mutate, no_project_error="No Black Box project is currently active.")

    async def ack_breakthrough(self, review_id: str) -> list[str]:
        """Marks one Eureka! Breakthrough cinematic as shown/dismissed —
        the same real "seen" tracking pattern ack_trade_notification
        already established, applied to app/black_box.py's reviews."""
        async with self.lock:
            updated = mark_breakthrough_viewed(self.data.black_box.viewed_breakthrough_ids, review_id)
            if updated is not self.data.black_box.viewed_breakthrough_ids:
                self.data = self.data.model_copy(update={"black_box": self.data.black_box.model_copy(update={"viewed_breakthrough_ids": updated})})
            return self.data.black_box.viewed_breakthrough_ids

    async def ack_talent_report(self, report_id: str) -> list[str]:
        """The Talent Discovery System's only real CEO action beyond
        acknowledging/ignoring a report — the same "seen" tracking
        pattern ack_breakthrough already established, applied to
        app/talent.py's reports. See talent.py's module docstring for
        why no role-change action exists to offer here."""
        async with self.lock:
            updated = mark_talent_report_viewed(self.data.talent.viewed_report_ids, report_id)
            if updated is not self.data.talent.viewed_report_ids:
                self.data = self.data.model_copy(update={"talent": self.data.talent.model_copy(update={"viewed_report_ids": updated})})
            return self.data.talent.viewed_report_ids

    def _find_strategy(self, strategy_id: str) -> Strategy | None:
        return next((s for s in self.data.strategies if s.id == strategy_id), None)

    async def queue_sandbox_backtest(self, strategy_id: str, scenario: TestScenario, custom_return_bias_pct: float, custom_volatility_bias: float) -> tuple[GameSaveState, str | None]:
        """v0.7 Feature 45 — the Research Sandbox's CEO-triggered
        POST /api/sandbox/backtest. Queues a real BacktestSession for one
        specific strategy against one specific Testing Environment — the
        same real engine app/simulation.py's automatic per-tick queueing
        already uses, just CEO-directed instead of random."""
        async with self.lock:
            strategy = self._find_strategy(strategy_id)
            if strategy is None:
                return self.data, "No strategy found with that id."
            if not self.data.watchlist:
                return self.data, "No symbols on the watchlist to test against yet."
            sessions = queue_backtest_now(
                list(self.data.backtest_sessions),
                self.data.strategies,
                self.data.watchlist,
                RESEARCHER_IDS,
                self.data.time,
                strategy=strategy,
                scenario=scenario,
                custom_return_bias_pct=custom_return_bias_pct,
                custom_volatility_bias=custom_volatility_bias,
            )
            if sessions is None:
                return self.data, "The Sandbox is already running the maximum number of concurrent backtests — wait for one to finish."
            self.data = self.data.model_copy(update={"backtest_sessions": sessions})
            return self.data, None

    async def begin_strategy_paper_trial(self, strategy_id: str) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            strategy = self._find_strategy(strategy_id)
            if strategy is None:
                return self.data, "No strategy found with that id."
            updated, error = begin_paper_trial(strategy, self.data.simulation_results, self.data.time.day)
            if error is not None or updated is None:
                return self.data, error
            strategies = [updated if s.id == strategy_id else s for s in self.data.strategies]
            self.data = self.data.model_copy(update={"strategies": strategies})
            return self.data, None

    async def begin_strategy_limited_live(self, strategy_id: str, amount: float) -> tuple[GameSaveState, str | None]:
        """v0.7 Feature 53 — Company Certification. Before any strategy
        may commit real allocated capital, it must clear the real,
        enforced readiness subset of the Certification checklist (see
        app/strategy_lab.py's evaluate_certification_readiness() for
        exactly which of the brief's thirteen requirements are honestly
        checkable this early in the pipeline). v0.7 Design Bible
        Chapter 62's Innovation Budget CEO control — the CEO's real,
        current `RiskLimits.maxLimitedLiveCapital` gates the ceiling
        here, defaulting to the exact prior fixed constant."""
        async with self.lock:
            strategy = self._find_strategy(strategy_id)
            if strategy is None:
                return self.data, "No strategy found with that id."
            monte_carlo = next((r for r in reversed(self.data.strategy_monte_carlo_results) if r.strategy_id == strategy_id), None)
            regime_test = next((r for r in reversed(self.data.strategy_regime_tests) if r.strategy_id == strategy_id), None)
            ready, readiness_detail = evaluate_certification_readiness(strategy, self.data.simulation_results, monte_carlo, regime_test)
            if not ready:
                return self.data, readiness_detail
            updated, error = begin_limited_live(strategy, amount, self.data.time.day, max_capital=self.data.risk_limits.max_limited_live_capital)
            if error is not None or updated is None:
                return self.data, error
            strategies = [updated if s.id == strategy_id else s for s in self.data.strategies]
            self.data = self.data.model_copy(update={"strategies": strategies})
            return self.data, None

    async def request_strategy_company_review(self, strategy_id: str) -> tuple[GameSaveState, str | None]:
        """Advances the strategy into "company_review" and files its real
        StrategyReview in one CEO action — see app/sandbox.py's
        generate_strategy_review() for exactly how each of the five real
        reviewer verdicts is computed. v0.7 Feature 52 (Part 1) also files
        the richer 9-department StrategyExecutiveReview and the Founder
        Council's real StrategyFounderApproval in the same action —
        Company Review, Executive Review, and Founder Approval are one
        real CEO-triggered moment, not three separate requests."""
        async with self.lock:
            strategy = self._find_strategy(strategy_id)
            if strategy is None:
                return self.data, "No strategy found with that id."
            updated, error = begin_company_review(strategy, self.data.time.day)
            if error is not None or updated is None:
                return self.data, error
            existing_count = sum(1 for r in self.data.strategy_reviews if r.strategy_id == strategy_id)
            review = generate_strategy_review(updated, self.data.simulation_results, self.data.research, existing_count, sim_day=self.data.time.day)
            monte_carlo = next((r for r in reversed(self.data.strategy_monte_carlo_results) if r.strategy_id == strategy_id), None)
            regime_test = next((r for r in reversed(self.data.strategy_regime_tests) if r.strategy_id == strategy_id), None)
            existing_exec_count = sum(1 for r in self.data.strategy_executive_reviews if r.strategy_id == strategy_id)
            executive_review = generate_strategy_executive_review(
                updated, review, self.data.research, self.data.coach_reports, monte_carlo, regime_test, self.data.market_intelligence, existing_exec_count, sim_day=self.data.time.day
            )
            founder_approval = generate_strategy_founder_approval(updated, executive_review, sim_day=self.data.time.day)
            strategies = [updated if s.id == strategy_id else s for s in self.data.strategies]
            strategy_reviews = [*self.data.strategy_reviews, review]
            strategy_executive_reviews = cap_strategy_executive_reviews([*self.data.strategy_executive_reviews, executive_review])
            strategy_founder_approvals = cap_strategy_founder_approvals([*self.data.strategy_founder_approvals, founder_approval])
            self.data = self.data.model_copy(
                update={
                    "strategies": strategies,
                    "strategy_reviews": strategy_reviews,
                    "strategy_executive_reviews": strategy_executive_reviews,
                    "strategy_founder_approvals": strategy_founder_approvals,
                }
            )
            return self.data, None

    async def decide_strategy_review(self, review_id: str, approve: bool) -> tuple[GameSaveState, str | None]:
        """The Company Review stage's real manual CEO call — Learning
        Mode always requires this; Assisted/Executive Mode auto-resolve
        instead (see app/nexus.py's tick())."""
        async with self.lock:
            review = next((r for r in self.data.strategy_reviews if r.id == review_id), None)
            if review is None:
                return self.data, "No Company Review found with that id."
            if review.ceo_decision != "pending":
                return self.data, "That Company Review has already been decided."
            strategy = self._find_strategy(review.strategy_id)
            if strategy is None:
                return self.data, "No strategy found for that review."
            updated_strategy = apply_review_decision(strategy, review, approve, self.data.time.day)
            strategies = [updated_strategy if s.id == strategy.id else s for s in self.data.strategies]
            reviews = [r.model_copy(update={"ceo_decision": "approved" if approve else "rejected", "resolved_by": "ceo"}) if r.id == review_id else r for r in self.data.strategy_reviews]
            self.data = self.data.model_copy(update={"strategies": strategies, "strategy_reviews": reviews})
            return self.data, None

    async def retire_strategy(self, strategy_id: str, reason: str) -> tuple[GameSaveState, str | None]:
        """v0.7 Feature 52 (Part 2) — the only real way a strategy's stage
        ever reaches "retired" (see app/sandbox.py's retire_strategy()).
        Files exactly one of a real StrategyHallOfFameEntry or a real
        FailedStrategyArchiveEntry in the same CEO action (see
        app/strategy_lab.py's generate_strategy_retirement_outcome()) —
        only a Hall of Fame induction also nudges Company DNA's real
        research_rigor Legacy trait (see app/company_dna.py's own module
        docstring for why this is the one Legacy nudge fired here rather
        than from nexus.py's tick loop). v0.7 Design Bible Chapter 62's
        Knowledge Integration — every retirement also files a real
        MemoryRecord under the "strategy" category (see app/scribe.py's
        record_strategy_hall_of_fame_entry/record_strategy_failed_archive_entry),
        a real MemoryCategory this codebase declared long ago but never
        actually populated until now."""
        async with self.lock:
            strategy = self._find_strategy(strategy_id)
            if strategy is None:
                return self.data, "No strategy found with that id."
            reason = reason.strip()
            if not reason:
                return self.data, "Retiring a strategy needs a real reason."
            latest_review = next((r for r in reversed(self.data.strategy_reviews) if r.strategy_id == strategy_id), None)
            latest_executive_review = next((r for r in reversed(self.data.strategy_executive_reviews) if r.strategy_id == strategy_id), None)
            latest_founder_approval = next((a for a in reversed(self.data.strategy_founder_approvals) if a.strategy_id == strategy_id), None)
            hall_of_fame_entry, failed_archive_entry = generate_strategy_retirement_outcome(
                strategy, self.data.simulation_results, latest_review, latest_executive_review, latest_founder_approval, reason, sim_day=self.data.time.day
            )
            retired_strategy, error = retire_strategy_stage(strategy, reason, self.data.time.day)
            if error is not None or retired_strategy is None:
                return self.data, error
            strategies = [retired_strategy if s.id == strategy_id else s for s in self.data.strategies]
            memory = list(self.data.memory)
            update: dict[str, object] = {"strategies": strategies}
            if hall_of_fame_entry is not None:
                update["strategy_hall_of_fame"] = cap_strategy_hall_of_fame([*self.data.strategy_hall_of_fame, hall_of_fame_entry])
                update["company_dna_legacy"] = nudge_legacy(dict(self.data.company_dna_legacy), "research_rigor", STRATEGY_HALL_OF_FAME_NUDGE)
                record_strategy_hall_of_fame_entry(memory, hall_of_fame_entry, max_records=self.data.risk_limits.max_memory_records)
            else:
                assert failed_archive_entry is not None
                update["strategy_failed_archive"] = cap_strategy_failed_archive([*self.data.strategy_failed_archive, failed_archive_entry])
                record_strategy_failed_archive_entry(memory, failed_archive_entry, max_records=self.data.risk_limits.max_memory_records)
            update["memory"] = memory
            self.data = self.data.model_copy(update=update)
            return self.data, None

    async def propose_constitution_amendment(self, title: str, text: str) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            title = title.strip()
            text = text.strip()
            if not title or not text:
                return self.data, "An Amendment needs both a real title and real text."
            if any(a.proposed_title.strip().lower() == title.lower() for a in self.data.constitution.amendments if a.ceo_decision == "pending"):
                return self.data, "An amendment with that title is already pending."
            amendment = propose_amendment(title, text, self.data.time.day)
            constitution = self.data.constitution.model_copy(update={"amendments": [*self.data.constitution.amendments, amendment], "updated_at": _now_iso()})
            self.data = self.data.model_copy(update={"constitution": constitution})
            return self.data, None

    async def advance_constitution_amendment(self, amendment_id: str) -> tuple[GameSaveState, str | None]:
        """Runs the Founder debate, Coach evaluation, and employee vote in
        one real step — unlike the Research Sandbox's stages, nothing
        here needs real elapsed time to gather more evidence; every part
        is a real, immediate computation over the amendment's own
        already-proposed text (see app/constitution.py's module
        docstring)."""
        async with self.lock:
            amendment = next((a for a in self.data.constitution.amendments if a.id == amendment_id), None)
            if amendment is None:
                return self.data, "No amendment found with that id."
            if amendment.status != "proposed":
                return self.data, "That amendment has already been debated."
            founder_verdicts = generate_founder_debate(amendment, self.data.constitution.articles)
            coach_evaluation = generate_coach_evaluation(amendment, self.data.company_health)
            employee_votes = generate_employee_votes(amendment, founder_verdicts, all_agent_ids())
            updated = amendment.model_copy(update={"status": "voted", "founder_verdicts": founder_verdicts, "coach_evaluation": coach_evaluation, "employee_votes": employee_votes})
            amendments = [updated if a.id == amendment_id else a for a in self.data.constitution.amendments]
            constitution = self.data.constitution.model_copy(update={"amendments": amendments, "updated_at": _now_iso()})
            self.data = self.data.model_copy(update={"constitution": constitution})
            return self.data, None

    async def decide_constitution_amendment(self, amendment_id: str, approve: bool) -> tuple[GameSaveState, str | None]:
        """The CEO's own real, manual, final call — deliberately never
        auto-resolved by Automation Mode (see app/constitution.py's
        module docstring)."""
        async with self.lock:
            amendment = next((a for a in self.data.constitution.amendments if a.id == amendment_id), None)
            if amendment is None:
                return self.data, "No amendment found with that id."
            if amendment.status != "voted":
                return self.data, "That amendment hasn't been debated and voted on yet."
            decided = decide_amendment(amendment, approve, self.data.time.day)
            articles = self.data.constitution.articles
            if approve:
                articles, decided = ratify_amendment(articles, decided, self.data.time.day)
            amendments = [decided if a.id == amendment_id else a for a in self.data.constitution.amendments]
            constitution = self.data.constitution.model_copy(update={"articles": articles, "amendments": amendments, "updated_at": _now_iso()})
            self.data = self.data.model_copy(update={"constitution": constitution})
            return self.data, None

    async def create_calendar_event(self, category: PlayerEventCategory, title: str, day: int, hour: int, minute: int) -> tuple[GameSaveState, str | None]:
        """CEO-scheduled custom calendar entry — informational only, the
        same "no fabricated mechanical effect" boundary calendar.py's own
        module docstring documents. Under the same lock every other state
        mutation uses."""
        async with self.lock:
            time = self.data.time
            event_id = f"calendar-player-{time.day}-{time.hour}-{time.minute}-{len(self.data.calendar.player_events)}"
            new_events, error = create_player_event(
                self.data.calendar.player_events, category=category, title=title, day=day, hour=hour, minute=minute, now=time, now_iso=_now_iso(), event_id=event_id
            )
            if error is None:
                self.data = self.data.model_copy(update={"calendar": self.data.calendar.model_copy(update={"player_events": new_events, "updated_at": _now_iso()})})
            return self.data, error

    async def delete_calendar_event(self, event_id: str) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            new_events, error = delete_player_event(self.data.calendar.player_events, event_id)
            if error is None:
                self.data = self.data.model_copy(update={"calendar": self.data.calendar.model_copy(update={"player_events": new_events, "updated_at": _now_iso()})})
            return self.data, error

    async def mark_lesson_viewed(self, lesson_id: str) -> EducationProgress:
        async with self.lock:
            new_progress = education.mark_viewed(self.data.education, lesson_id)
            if new_progress is not self.data.education:
                self.data = self.data.model_copy(update={"education": new_progress})
            return self.data.education

    async def submit_education_quiz(self, lesson_id: str, selected_index: int) -> tuple[EducationProgress, bool, int, str] | None:
        async with self.lock:
            result = education.grade_quiz(self.data.education, lesson_id, selected_index)
            if result is None:
                return None
            new_progress, correct, correct_index, correct_option = result
            self.data = self.data.model_copy(update={"education": new_progress})
            return new_progress, correct, correct_index, correct_option

    async def ack_trade_notification(self, trade_id: str) -> list[str]:
        """Marks one real closed trade's outcome popup as shown/dismissed
        — persisted so it never re-shows after a refresh or restart."""
        async with self.lock:
            updated = trade_notifications.mark_viewed(self.data.viewed_trade_notification_ids, trade_id)
            if updated is not self.data.viewed_trade_notification_ids:
                self.data = self.data.model_copy(update={"viewed_trade_notification_ids": updated})
            return self.data.viewed_trade_notification_ids

    async def submit_ceo_decision(self, proposal_id: str, choice: AnalystChoice) -> tuple[GameSaveState, str | None]:
        """Feature 12 — the CEO's (the player's) real buy/sell/wait call on
        a pending TradeProposal, applied under the same lock every other
        state mutation uses. Returns (state, error) — error is None on
        success. Resolves and removes the proposal immediately (unlike a
        broker order, this is a live player action, not a tick-driven
        fill) and appends both the resulting TradeDecision and
        CeoDecisionRecord, capped the same way tick()'s own decisions
        list is."""
        async with self.lock:
            proposal = next((p for p in self.data.trade_proposals if p.id == proposal_id), None)
            if proposal is None:
                return self.data, f"No pending trade proposal with id {proposal_id!r}."

            watchlist_item = next((w for w in self.data.watchlist if w.symbol == proposal.symbol), None)
            current_price = watchlist_item.last_price if watchlist_item else None
            now_sim_minutes = sim_minutes(self.data.time)
            # v0.7 Feature 17 — the most recently generated debate for this
            # proposal (regenerate_debate can append more than one), fed
            # into the Gatekeeper's own debate-outcome check below.
            debate = next((d for d in reversed(self.data.debates) if d.proposal_id == proposal_id), None)

            portfolio, decision, ceo_record = resolve_proposal(
                proposal,
                choice,
                portfolio=self.data.paper_portfolio,
                risk_limits=self.data.risk_limits,
                current_price=current_price,
                now_sim_minutes=now_sim_minutes,
                market_intelligence=self.data.market_intelligence,
                debate=debate,
                risk_warnings=self.data.risk_warnings,
            )

            memory = list(self.data.memory)
            record_ceo_decision(memory, decision)

            decisions = [*self.data.decisions, decision]
            if len(decisions) > MAX_DECISIONS:
                del decisions[: len(decisions) - MAX_DECISIONS]

            # v0.7 Feature 50 (Part 2/3) — the Executive Meeting Log's
            # real permanent record of this same decision, reusing the
            # already-computed TradeDecision (its decisionGrade included)
            # rather than a second parallel synthesis.
            challenge_report = next((c for c in reversed(self.data.challenge_reports) if c.proposal_id == proposal_id), None)
            meeting_log = record_meeting_log_entry(
                list(self.data.executive_meeting_log),
                generate_meeting_log_entry(
                    proposal, decision, ceo_record.ceo_decision, challenge_report, self.data.coach_reports, self.data.market_intelligence, sim_day=self.data.time.day, resolved_by="ceo"
                ),
            )

            ceo_decisions = [*self.data.ceo_decisions, ceo_record]
            if len(ceo_decisions) > MAX_CEO_DECISIONS:
                del ceo_decisions[: len(ceo_decisions) - MAX_CEO_DECISIONS]

            gatekeeper_rejections = list(self.data.gatekeeper_rejections)
            verdict = decision.gatekeeper_verdict
            if verdict is not None and not verdict.approved and current_price is not None:
                # v0.7 Feature 20 — the trade never executed, so there's no
                # P&L to grade; tracked instead for the self-evaluation's
                # "would it have worked?" read (see grade_gatekeeper_rejections).
                gatekeeper_rejections.append(
                    GatekeeperRejection(
                        id=f"gkreject-{decision.id}",
                        proposalId=proposal.id,
                        symbol=proposal.symbol,
                        ceoChoice=choice,
                        reasons=[f"{c.label}: {c.detail}" for c in verdict.checks if not c.passed],
                        priceAtRejection=current_price,
                        rejectedSimMinutes=now_sim_minutes,
                        createdAt=_now_iso(),
                    )
                )
                if len(gatekeeper_rejections) > MAX_GATEKEEPER_REJECTIONS:
                    del gatekeeper_rejections[: len(gatekeeper_rejections) - MAX_GATEKEEPER_REJECTIONS]

            self.data = self.data.model_copy(
                update={
                    "trade_proposals": [p for p in self.data.trade_proposals if p.id != proposal_id],
                    "paper_portfolio": portfolio,
                    "decisions": decisions,
                    "ceo_decisions": ceo_decisions,
                    "gatekeeper_rejections": gatekeeper_rejections,
                    "memory": memory,
                    "executive_meeting_log": meeting_log,
                    "updated_at": _now_iso(),
                }
            )
            return self.data, None

    async def regenerate_debate(self, proposal_id: str) -> tuple[GameSaveState, str | None]:
        """v0.7 Feature 17 — "request another debate": re-runs the same
        real analyst votes already on the pending proposal through a
        fresh generate_debate() call, appended (not replacing) so the
        prior debate stays reviewable in the Command Center's stored
        history too. Only valid for a proposal that's still pending —
        once the CEO decides, the proposal itself is gone."""
        async with self.lock:
            proposal = next((p for p in self.data.trade_proposals if p.id == proposal_id), None)
            if proposal is None:
                return self.data, f"No pending trade proposal with id {proposal_id!r}."

            debates = [*self.data.debates, generate_debate(proposal)]
            if len(debates) > MAX_DEBATES:
                del debates[: len(debates) - MAX_DEBATES]

            self.data = self.data.model_copy(update={"debates": debates, "updated_at": _now_iso()})
            return self.data, None

    async def regenerate_challenge_report(self, proposal_id: str) -> tuple[GameSaveState, str | None]:
        """v0.7 Feature 41 — "request another review": a fresh Devil's
        Advocate pass over the same real signals, appended (not replacing)
        so the prior report stays reviewable too — the exact same
        reasoning as regenerate_debate above. The rotating assignment
        naturally advances to the next eligible employee since it's
        derived from the already-updated report count (see
        app/devils_advocate.py's module docstring)."""
        async with self.lock:
            proposal = next((p for p in self.data.trade_proposals if p.id == proposal_id), None)
            if proposal is None:
                return self.data, f"No pending trade proposal with id {proposal_id!r}."

            report = generate_challenge_report(
                proposal, provider=market_data_provider, case_studies=self.data.case_studies, existing_count=len(self.data.challenge_reports)
            )
            challenge_reports = [*self.data.challenge_reports, report]
            if len(challenge_reports) > MAX_CHALLENGE_REPORTS:
                del challenge_reports[: len(challenge_reports) - MAX_CHALLENGE_REPORTS]
            innovation_state = compute_innovation_state(challenge_reports)

            self.data = self.data.model_copy(
                update={"challenge_reports": challenge_reports, "innovation_state": innovation_state, "updated_at": _now_iso()}
            )
            return self.data, None

    async def hold_trade_proposal(self, proposal_id: str, reason: HoldReason) -> tuple[GameSaveState, str | None]:
        """v0.7 Feature 40.5 — "Request More Research" / "Delay Decision":
        real CEO actions distinct from buy/sell/wait. The proposal stays
        pending (see app/executive.py's hold_proposal()) — no
        TradeDecision/CeoDecisionRecord, since nothing has actually been
        decided. Capped at MAX_PROPOSAL_HOLDS; once exhausted the CEO
        must actually decide (or let it expire the normal way)."""
        async with self.lock:
            proposal = next((p for p in self.data.trade_proposals if p.id == proposal_id), None)
            if proposal is None:
                return self.data, f"No pending trade proposal with id {proposal_id!r}."

            held = hold_proposal(proposal, now_sim_minutes=sim_minutes(self.data.time))
            if held is None:
                return self.data, f"{proposal.symbol} has already been held the maximum {MAX_PROPOSAL_HOLDS} times — decide or let it expire."

            memory = list(self.data.memory)
            record_proposal_hold(memory, held, reason)

            self.data = self.data.model_copy(
                update={
                    "trade_proposals": [held if p.id == proposal_id else p for p in self.data.trade_proposals],
                    "memory": memory,
                    "updated_at": _now_iso(),
                }
            )
            return self.data, None

    def _advance_once(self, minutes: int) -> None:
        """Advance the game clock and run one NEXUS orchestration step.
        Assumes `self.lock` is already held — the shared inner step both
        `tick()` (one real-time step, called by the sim loop) and
        `advance_time()` (v0.7 Feature 34, many steps in a row under one
        lock acquisition) use, so a fast-forward burst is structurally
        identical to time actually passing faster, not a fake jump: every
        exact-minute cadence check in nexus.tick() (evening reports,
        the morning Question of the Day, ...) still fires correctly along
        the way."""
        time = self.data.time
        total_minutes = time.hour * 60 + time.minute + minutes
        day = time.day + total_minutes // (24 * 60)
        total_minutes %= 24 * 60
        hour, minute = divmod(total_minutes, 60)
        new_time = TimeState(day=day, hour=hour, minute=minute)
        self.data = nexus.tick(self.data, new_time, minutes)

    async def tick(self, minutes: int) -> GameSaveState:
        """Advance the game clock and run one NEXUS orchestration step. Called by the sim loop."""
        async with self.lock:
            self._advance_once(minutes)
            return self.data

    async def advance_time(self, target: TimeAdvanceTarget, hours: int | None) -> tuple[GameSaveState, str | None]:
        """v0.7 Feature 34 — CEO time controls (End Workday/Week/Month, or
        a bounded custom fast-forward). Loops `_advance_once()` in real
        `GAME_MINUTES_PER_TICK`-sized steps under a single lock
        acquisition until the target is reached, rather than jumping the
        clock directly to it — a direct jump could land off the exact
        minute nexus.tick()'s own cadence checks require (see
        EVENING_REVIEW_HOUR/MORNING_QOTD_HOUR's own "always divides 60
        evenly" comment), silently skipping a report/QOTD/reflection that
        should have fired along the way. Returns (state, error); error is
        None on success."""
        if target == "hours":
            if hours is None or hours <= 0:
                return self.data, "hours must be a positive number when target is 'hours'."
            if hours > MAX_FAST_FORWARD_HOURS:
                return self.data, f"Can't fast-forward more than {MAX_FAST_FORWARD_HOURS} hours at once."

        async with self.lock:
            step = settings.game_minutes_per_tick
            ticks = 0
            if target == "hours":
                assert hours is not None
                total_steps = (hours * 60) // step
                for _ in range(total_steps):
                    self._advance_once(step)
                    ticks += 1
            else:
                stop_hour = nexus.EVENING_REVIEW_HOUR
                if target == "workday_end":
                    stop_predicate = lambda t: t.hour == stop_hour and t.minute == 0  # noqa: E731
                elif target == "week_end":
                    stop_predicate = lambda t: t.hour == stop_hour and t.minute == 0 and t.day % nexus.WEEKLY_INTERVAL_DAYS == 0  # noqa: E731
                else:  # month_end
                    stop_predicate = lambda t: t.hour == stop_hour and t.minute == 0 and t.day % nexus.MONTHLY_INTERVAL_DAYS == 0  # noqa: E731
                # Always advances at least one step — calling this exactly
                # at the target minute (e.g. clicking "End Workday" right
                # at 20:00) must still jump forward to the *next*
                # occurrence, not no-op.
                while True:
                    self._advance_once(step)
                    ticks += 1
                    if stop_predicate(self.data.time) or ticks >= MAX_FAST_FORWARD_TICKS:
                        break
            return self.data, None


game_state = GameState()
