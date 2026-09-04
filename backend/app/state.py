"""In-memory authoritative game state, shared across all connected clients.

TradeTown is single-tenant (one company actively ticking at a time) — this
is intentionally a process-wide singleton rather than per-session state.
Agent/task/whiteboard/meeting orchestration itself lives in nexus.py; this
module just owns the lock-guarded snapshot and the game clock.

CEO directive "Proper Multi-Run / Save Isolation System" — the backend can
now persist multiple independent runs (see app/persistence.py's real,
indexed `slot` column on every save table), but only ONE run is ever
actively ticking in this singleton at a time, exactly like before; a
run that isn't the active one is simply dormant (not ticking) until
switched back to, the same real-world behavior any single-save-slot idle
game already has. `switch_run()`/`create_run()` below are the only two
places that change WHICH run this singleton holds — both run their
entire persist-old/load-new sequence inside `self.lock`, the same lock
`tick()` already uses, so a concurrent tick can never interleave mid-switch
and write one run's data into another's slot."""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from typing import Callable, Literal

from app import education, nexus, player_vs_ai, signal_calibration, trade_notifications
from app.academy import compute_academy_state, default_agent_knowledge
from app.agents import AGENT_PROFILES, all_agent_ids
from app.analytics import max_drawdown_pct
from app.behavioral_risk import default_behavioral_circuit_breaker
from app.black_box import archive_project, default_black_box_state, mark_breakthrough_viewed
from app.config import settings
from app.mentor import compute_mentor_state, compute_thinking_profiles, generate_question_of_the_day, submit_response
from app.calendar import create_player_event, default_calendar, delete_player_event
from app.accounts import add_custom_rule as add_custom_rule_fn
from app.accounts import allocate_capital as allocate_capital_fn
from app.accounts import close_account as close_account_fn
from app.accounts import configure_evaluation_tracking as configure_evaluation_tracking_fn
from app.accounts import configure_prop_firm_rules as configure_prop_firm_rules_fn
from app.accounts import create_account as create_account_fn
from app.accounts import deallocate_capital as deallocate_capital_fn
from app.accounts import mark_account_funded as mark_account_funded_fn
from app.accounts import record_account_payout as record_account_payout_fn
from app.accounts import remove_custom_rule as remove_custom_rule_fn
from app.accounts import toggle_custom_rule as toggle_custom_rule_fn
from app.rule_engine import evaluate_rules
from app.treasury import create_rule, default_treasury, deposit, pause_all_rules, toggle_rule, withdraw
from app.reasoning_lab import compute_reasoning_lab_state
from app.wisdom import compute_wisdom_score
from app.academy_research import default_academy_projects
from app.agent_energy import default_agent_energy
from app.company_dna import STRATEGY_HALL_OF_FAME_NUDGE, compute_company_dna, nudge_legacy
from app.board import generate_board_report, record_board_report
from app.company_health import compute_company_health
from app.company_score import compute_company_score
from app.constitution import decide_amendment, default_constitution, generate_coach_evaluation, generate_employee_votes, generate_founder_debate, propose_amendment, ratify_amendment
from app.debate import generate_debate
from app.devils_advocate import MAX_CHALLENGE_REPORTS, generate_challenge_report
from app.emergency_stop import activate_emergency_stop as _activate_emergency_stop
from app.emergency_stop import resume_trading as _resume_trading
from app.trading_restrictions import activate_trading_restriction as _activate_trading_restriction
from app.trading_restrictions import lift_trading_restriction as _lift_trading_restriction
from app.executive import MAX_CEO_DECISIONS, MAX_PROPOSAL_HOLDS, AnalystChoice, hold_proposal, modify_proposal, resolve_proposal
from app.prediction_tracking import MAX_PREDICTION_RECORDS, build_prediction_record
from app.executive_intelligence import (
    compute_executive_accuracy_scores,
    compute_executive_recommendation,
    generate_department_opinions,
    generate_meeting_log_entry,
    record_meeting_log_entry,
)
from app.goals import cancel_goal as cancel_goal_entry
from app.goals import create_goal, record_goal, resolve_metric_value, validate_target_value
from app.innovation import compute_innovation_state
from app.weighted_decisions import compute_weighted_recommendation
from app.black_swan import activate_defensive_mode as _activate_defensive_mode
from app.black_swan import compute_black_swan_intelligence
from app.black_swan import compute_institutional_survival_score
from app.black_swan import deactivate_defensive_mode as _deactivate_defensive_mode
from app.black_swan import record_black_swan_event
from app.gatekeeper import MIN_CONFIDENCE as GATEKEEPER_MIN_CONFIDENCE
from app.trading_modes import (
    acknowledge_losing_streak,
    change_trading_mode,
    circuit_breaker_confidence_bonus,
    compute_consecutive_losses,
    default_daily_circuit_breaker,
    default_losing_streak,
    default_trading_mode_state,
)
from app.travel_mode import (
    MAX_TRAVEL_MODE_BRIEFINGS,
    activate_travel_mode as _activate_travel_mode,
    deactivate_travel_mode as _deactivate_travel_mode,
    generate_travel_mode_briefing,
    travel_mode_confidence_bonus,
    update_travel_mode_settings as _update_travel_mode_settings,
)
from app.economic_intelligence import compute_economic_intelligence
from app.memory import record
from app.market_data import market_data_provider
from app.market_environment import default_market_environment
from app.market_intelligence import compute_market_intelligence_state, compute_strategy_match
from app.nexus import MAX_DEBATES, MAX_DECISIONS, MAX_GATEKEEPER_REJECTIONS, MAX_SNIPER_EVENTS
from app.paper_trade_journal import add_ceo_note
from app.portfolio import default_portfolio, sim_minutes
from app.portfolio_intelligence import compute_portfolio_intelligence
from app.research import RESEARCHER_IDS, default_research
from app.risk_engine import compute_daily_objective_status, compute_risk_budget_status, default_risk_limits, portfolio_equity
from app.sandbox import apply_review_decision, begin_company_review, begin_limited_live, begin_paper_trial, generate_strategy_review
from app.sandbox import retire_strategy as retire_strategy_stage
from app.scribe import record_ceo_decision, record_emergency_stop_event, record_proposal_hold, record_proposal_modify, record_rule_violation, record_strategy_failed_archive_entry, record_strategy_hall_of_fame_entry, record_trading_restriction_event
from app.self_improvement import decide_self_improvement_proposal, mark_self_improvement_proposal_implemented, maybe_propose_retirement_cluster, record_self_improvement_proposal
from app.vision_board import (
    add_vision_objective,
    compute_self_improvement_proposal_alignment,
    default_vision_board,
    remove_vision_objective,
    set_vision_identity_note,
    set_vision_mission,
    set_vision_priorities,
)
from app.schemas import (
    AccountType,
    AgentId,
    RuleType,
    Weekday,
    BlackBoxPriority,
    BlackBoxProject,
    BlackSwanRiskTier,
    ChallengerComparison,
    ChampionRecord,
    FactoryRunRecord,
    ResearchDiscoveryCycleRecord,
    ResearchLoopIterationRecord,
    ResearchOrchestratorStatus,
    StrategyHypothesis,
    ClientSaveRequest,
    CompiledStrategyDefinition,
    DefensiveModeState,
    EducationProgress,
    EntityTransform,
    FounderState,
    FoundationalMentorId,
    IncidentRootCause,
    FoundationalResourceType,
    GameSaveState,
    GatekeeperRejection,
    GoalCategory,
    GoalMetric,
    HoldReason,
    InstitutionalMemoryEntry,
    KnowledgeEvent,
    MeetingState,
    NewsItem,
    PaperTradeJournalEntry,
    PlayerEventCategory,
    PlayerVsAiPrompt,
    PlayerVsAiState,
    ResearchCategory,
    RiskContract,
    RiskContractScalingPolicy,
    RiskContractScalingRead,
    RiskContractValidationResult,
    RiskDecision,
    RiskLimits,
    SavingsRuleType,
    SettingsState,
    SignalCalibrationState,
    SignalChoice,
    SniperTrade,
    SniperWallet,
    Strategy,
    SubmitQuantResearchExperimentResult,
    TalentState,
    TestScenario,
    TierAllocationLimits,
    TimeAdvanceTarget,
    TimeState,
    TradingMode,
    RestrictionScope,
)
from app.autonomous_promotion import apply_autonomous_promotions
from app.champion_challenger import compare_champion_challenger, promote_challenger
from app.failure_taxonomy import find_similar_failed_strategies
from app.quant_research_lab import cap_quant_research_experiments, classify_research_relationship, file_quant_research_experiment, find_similar_experiments
from app.research_experiment import run_research_experiment
from app.research_loop import generate_research_lesson, run_research_loop_iteration
from app.research_factory import (
    MAX_CHILDREN_PER_PARENT,
    MAX_GENERATIONS_PER_FACTORY_RUN,
    MAX_RUNTIME_SECONDS,
    MAX_TOTAL_BACKTESTS_PER_FACTORY_RUN,
    run_research_factory_cycle,
)
from app.research_discovery import run_research_discovery_cycle
from app.research_orchestrator import ResearchOrchestratorDecision, ResearchOrchestratorOutcome, ResearchOrchestratorSeed, decide_research_orchestration
from app.strategy_families import SUPPORTED_FAMILIES
from app.strategy_engine import DEFAULT_CANDLES_PER_SYMBOL, DEFAULT_TIMEFRAME
from app.strategy_compiler import strategy_definition_slug
from app.risk_contract import (
    MAX_RISK_DECISIONS,
    activate_risk_contract as _activate_risk_contract,
    apply_active_risk_contract,
    archive_risk_contract as _archive_risk_contract,
    build_risk_decision,
    create_draft_risk_contract as _create_draft_risk_contract,
    get_active_risk_contract,
    mark_validated as _mark_validated_risk_contract,
    validate_risk_contract,
)
from app.strategy_registry import default_researchable_strategies, register_researchable_strategy, register_strategy_version
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
    evaluate_retirement_readiness,
    generate_strategy_executive_review,
    generate_strategy_founder_approval,
    generate_strategy_retirement_outcome,
)
from app.cost_sensitivity import run_cost_sensitivity
from app.leakage_audit import audit_definition_for_look_ahead
from app.walk_forward import run_walk_forward_validation
from app.compliance_incidents import (
    add_evidence,
    begin_remediation,
    fail_verification,
    reopen,
    start_investigating,
    submit_for_verification,
    verify_and_resolve,
)
from app.override_governance import add_override_review
from app.institutional_memory import (
    promote_failed_strategy,
    promote_hall_of_fame_strategy,
    promote_model_validation,
    promote_research_lesson,
    record_and_link_institutional_memory,
    should_promote_model_validation,
    should_promote_research_lesson,
)
from app.knowledge_sharing import (
    lesson_confirmed_event,
    lesson_created_event,
    record_knowledge_event,
    share_lesson_with_relevant_agents,
)
from app.model_validation import cap_strategy_model_validations, generate_model_validation_report
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


def _promote_and_share_lesson(
    institutional_memory: list[InstitutionalMemoryEntry],
    knowledge_events: list[KnowledgeEvent],
    promoted_entry: InstitutionalMemoryEntry,
    *,
    sim_day: int,
) -> tuple[list[InstitutionalMemoryEntry], list[KnowledgeEvent]]:
    """"TradeTown — Learning Organization 1.0" — the same real gateway
    app/nexus.py's own _promote_and_share_lesson() uses for its
    tick-driven promotions, mirrored here for state.py's own
    request-driven promotions (Model Validation, Strategy Hall of Fame,
    Failed Strategy Archive, Research Lesson) so every institutional-
    memory write in this codebase goes through the same one real
    confirm/share step rather than two competing implementations."""
    institutional_memory, linked_id = record_and_link_institutional_memory(
        institutional_memory, promoted_entry, current_sim_day=sim_day
    )
    if linked_id is not None:
        knowledge_events = record_knowledge_event(knowledge_events, lesson_confirmed_event(promoted_entry, linked_id))
    else:
        knowledge_events = record_knowledge_event(knowledge_events, lesson_created_event(promoted_entry))
        for share_event in share_lesson_with_relevant_agents(promoted_entry):
            knowledge_events = record_knowledge_event(knowledge_events, share_event)
    return institutional_memory, knowledge_events


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
        institutional_memory=[],
        knowledge_events=[],
        audit_entries=[],
        decisions=[],
        ceo_decisions=[],
        debates=[],
        collaboration_case_score=None,
    )
    default_foundational_mentors = default_foundational_mentor_state()
    # CEO directive "Strategy Intelligence + Live Strategy Attribution,"
    # Phase 13 — the 50 EMA breakout/pullback strategy's real Strategy
    # Lab citizenship, on by default for every new game alongside the
    # four original seed strategies (see app/strategy_registry.py's
    # default_researchable_strategies()). Computed once here so the
    # `strategies=`/`compiledStrategyVersions=` fields below and this
    # same function's later compute_company_health() call all reuse the
    # identical real list/registry rather than independently-generated
    # copies.
    researchable_strategies, researchable_strategy_versions = default_researchable_strategies()
    seed_strategies = [*default_strategies(), *researchable_strategies]
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
        strategies=seed_strategies,
        compiledStrategyVersions=researchable_strategy_versions,
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
        opportunityShadowCaptures=[],
        multiTimeframeLiquidityCaptures=[],
        championLiveSignalCaptures=[],
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
            discipline_reviews=[],
            agent_knowledge=agent_knowledge,
            strategies=seed_strategies,
            strategy_health_assessments=[],
            compliance_incidents=[],
            current_sim_day=1,
        ),
        companyDna=compute_company_dna([], [], []),
        dailyObjectiveStatus=compute_daily_objective_status(default_risk_limits(), default_portfolio(), 1),
        riskBudgetStatus=compute_risk_budget_status(default_risk_limits(), default_portfolio(), 1),
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
        visionBoard=default_vision_board(),
        warRoomSessions=[],
        portfolioIntelligence=compute_portfolio_intelligence(default_portfolio(), market_data_provider, pending_proposal_count=0),
        economicIntelligence=compute_economic_intelligence(
            default_market_environment(),
            compute_market_intelligence_state(watchlist, [], [], market_data_provider),
            compute_portfolio_intelligence(default_portfolio(), market_data_provider, pending_proposal_count=0),
        ),
        economicIntelligenceReports=[],
        blackSwanIntelligence=compute_black_swan_intelligence(
            [],
            compute_market_intelligence_state(watchlist, [], [], market_data_provider),
            compute_portfolio_intelligence(default_portfolio(), market_data_provider, pending_proposal_count=0),
            default_market_environment(),
            compute_economic_intelligence(
                default_market_environment(),
                compute_market_intelligence_state(watchlist, [], [], market_data_provider),
                compute_portfolio_intelligence(default_portfolio(), market_data_provider, pending_proposal_count=0),
            ),
        ),
        blackSwanReports=[],
        defensiveMode=DefensiveModeState(),
        blackSwanEvents=[],
        institutionalSurvivalScore=compute_institutional_survival_score(
            default_portfolio(),
            default_risk_limits(),
            compute_portfolio_intelligence(default_portfolio(), market_data_provider, pending_proposal_count=0),
            compute_black_swan_intelligence(
                [],
                compute_market_intelligence_state(watchlist, [], [], market_data_provider),
                compute_portfolio_intelligence(default_portfolio(), market_data_provider, pending_proposal_count=0),
                default_market_environment(),
                compute_economic_intelligence(
                    default_market_environment(),
                    compute_market_intelligence_state(watchlist, [], [], market_data_provider),
                    compute_portfolio_intelligence(default_portfolio(), market_data_provider, pending_proposal_count=0),
                ),
            ),
            DefensiveModeState(),
        ),
        tradingModes=default_trading_mode_state(_now_iso()),
        dailyCircuitBreaker=default_daily_circuit_breaker(),
        losingStreak=default_losing_streak(),
        behavioralCircuitBreaker=default_behavioral_circuit_breaker(),
        recoveryBriefings=[],
        updatedAt=_now_iso(),
    )


class GameState:
    """Thread-safe (via asyncio.Lock) holder for the single authoritative save."""

    def __init__(self) -> None:
        self.data: GameSaveState = default_state()
        self.lock = asyncio.Lock()
        # CEO directive "TradeTown — Autonomous Research Orchestrator
        # 1.0" — in-memory-only runtime state for the orchestrator's own
        # concurrency guard (Part VII) and bounded-retry cadence tracker
        # (Part XII). Deliberately NOT part of GameSaveState/persisted:
        # it resets to a clean "nothing in flight" state on every
        # restart, which is exactly the crash-safe behavior Part X asks
        # for — there is no persisted "stuck FACTORY_RUNNING" state to
        # ever get stuck in. See app/research_orchestrator.py's own
        # module docstring for the full real methodology.
        self._research_orchestrator_task: asyncio.Task[None] | None = None
        self._research_orchestrator_last_attempt_sim_day: int | None = None
        self._research_orchestrator_last_decision: ResearchOrchestratorDecision | None = None
        self._research_orchestrator_last_outcome: ResearchOrchestratorOutcome | None = None

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

    async def persist_now(self) -> None:
        """Persists `self.data` to whichever slot is currently active,
        atomically with respect to `tick()`/`switch_run()`/`create_run()`
        (same lock). Exists specifically so app/sim.py's tick loop can
        persist without the gap a bare `persist_modules(state)` call
        after an `await` (the WS broadcast) would otherwise leave open —
        see app/persistence.py's own module docstring for why every OTHER
        existing `persist_modules(state)` call site elsewhere in this
        codebase doesn't need this (no `await` sits between their own
        locked mutation and their own persist call, so they're already
        atomic without it)."""
        from app import persistence

        async with self.lock:
            persistence.persist_modules(self.data)

    async def switch_run(self, run_id: str) -> GameSaveState:
        """CEO directive "Proper Multi-Run / Save Isolation System" —
        switches this singleton to an already-registered run. Persists
        whatever run is currently active FIRST (so nothing generated
        since its last periodic persist is lost), then loads the target
        run — all inside one lock acquisition, so a concurrent tick can
        never see the active-slot pointer change mid-operation. Fails
        safely (raises, active slot reverted) rather than leaving the
        pointer aimed at a run that doesn't actually have data."""
        from app import persistence

        async with self.lock:
            previous_slot = persistence.get_active_slot()
            persistence.persist_modules(self.data)
            persistence.set_active_slot(run_id)
            target = persistence.load_state()
            if target is None:
                persistence.set_active_slot(previous_slot)
                raise ValueError(f"No run found with id {run_id!r}")
            persistence.set_active_run_pointer(run_id)
            persistence.touch_run_last_played(run_id)
            self.data = nexus.register_agents(target)
            return self.data

    async def create_run(self, display_name: str) -> tuple[GameSaveState, str]:
        """CEO directive "Proper Multi-Run / Save Isolation System" — the
        one real way a brand-new run comes into existence. Persists
        whatever run is currently active first (same reasoning as
        switch_run()), then generates a real unique run id, initializes
        it via the exact same default_state() every fresh deployment
        already uses (never a second, parallel "new game" initialization
        path), persists it, registers it, and makes it the active run —
        all inside one lock acquisition. The run being left behind is
        never reset, overwritten, or touched beyond that one persist."""
        from app import persistence

        async with self.lock:
            persistence.persist_modules(self.data)
            new_run_id = persistence.generate_run_id()
            persistence.set_active_slot(new_run_id)
            fresh = default_state()
            persistence.persist_modules(fresh)
            persistence.register_run(new_run_id, display_name)
            persistence.set_active_run_pointer(new_run_id)
            self.data = fresh
            return self.data, new_run_id

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
        max_weekly_loss_pct: float | None = None,
        max_monthly_loss_pct: float | None = None,
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
        company_health_excellent_threshold: float | None = None,
        company_health_good_threshold: float | None = None,
        company_health_stable_threshold: float | None = None,
        company_health_needs_attention_threshold: float | None = None,
    ) -> tuple[GameSaveState, str | None]:
        """v0.7 Feature 49 — the CEO's Daily Trading Objectives — extended
        by Design Bible Chapter 67 (TTOS)'s Safety Settings with the
        weekly/monthly circuit breakers (`max_weekly_loss_pct`,
        `max_monthly_loss_pct` — see app/risk_engine.py's
        evaluate_sentinel_risk), by v0.7 Chapter 57 with four of the six
        new Position Sizing
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
            if max_weekly_loss_pct is not None:
                if max_weekly_loss_pct <= 0:
                    return self.data, "Weekly maximum loss must be a positive percentage."
                updates["max_weekly_loss_pct"] = max_weekly_loss_pct
            if max_monthly_loss_pct is not None:
                if max_monthly_loss_pct <= 0:
                    return self.data, "Monthly maximum loss must be a positive percentage."
                updates["max_monthly_loss_pct"] = max_monthly_loss_pct
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
            if company_health_excellent_threshold is not None:
                if company_health_excellent_threshold < 0 or company_health_excellent_threshold > 100:
                    return self.data, "Company Health Excellent threshold must be a score from 0 to 100."
                updates["company_health_excellent_threshold"] = company_health_excellent_threshold
            if company_health_good_threshold is not None:
                if company_health_good_threshold < 0 or company_health_good_threshold > 100:
                    return self.data, "Company Health Good threshold must be a score from 0 to 100."
                updates["company_health_good_threshold"] = company_health_good_threshold
            if company_health_stable_threshold is not None:
                if company_health_stable_threshold < 0 or company_health_stable_threshold > 100:
                    return self.data, "Company Health Stable threshold must be a score from 0 to 100."
                updates["company_health_stable_threshold"] = company_health_stable_threshold
            if company_health_needs_attention_threshold is not None:
                if company_health_needs_attention_threshold < 0 or company_health_needs_attention_threshold > 100:
                    return self.data, "Company Health Needs Attention threshold must be a score from 0 to 100."
                updates["company_health_needs_attention_threshold"] = company_health_needs_attention_threshold
            if not updates:
                return self.data, "No risk limit changes were provided."
            new_limits = self.data.risk_limits.model_copy(update=updates)
            # v0.7 Design Bible Chapter 63 — the four Company Health tier
            # thresholds classify the same score into one of four tiers in
            # order, so they must stay strictly descending regardless of
            # which subset of them this call actually changed (checked
            # against the fully-merged candidate, not just the fields this
            # call touched, the same way tier_allocation's own four-way
            # check above validates the whole object at once).
            if not (
                new_limits.company_health_excellent_threshold
                > new_limits.company_health_good_threshold
                > new_limits.company_health_stable_threshold
                > new_limits.company_health_needs_attention_threshold
            ):
                return self.data, "Company Health tier thresholds must stay in strictly descending order: Excellent > Good > Stable > Needs Attention."
            self.data = self.data.model_copy(update={"risk_limits": new_limits})
            return self.data, None

    @staticmethod
    def _derive_active_risk_contract(state: GameSaveState) -> tuple[GameSaveState, RiskContract]:
        """CEO directive "TradeTown — Persisted Risk Contract + Dynamic
        Risk Scaling," Phase 12 (fail-closed without breaking every
        pre-existing save) — the synchronous derivation core shared by
        `ensure_active_risk_contract()` below (acquires its own lock,
        for external/API callers) and `_advance_once()` (already
        running under `self.lock` — must never acquire it a second
        time, `asyncio.Lock` is not reentrant). Idempotent: returns
        `state` unchanged plus the existing active contract when one
        already exists; otherwise derives and persists a real v1
        `RiskContract` from the CEO's own actual, already-configured
        `risk_limits` — never a fabricated configuration."""
        existing = get_active_risk_contract(state.risk_contracts)
        if existing is not None:
            return state, existing
        now = _now_iso()
        contract_id = f"risk-contract-{uuid.uuid4().hex[:12]}"
        draft = _create_draft_risk_contract(
            history=state.risk_contracts,
            contract_id=contract_id,
            limits=state.risk_limits,
            created_by="system",
            reason="Auto-derived from the CEO's existing risk configuration — the first Risk Contract this company ever had.",
            created_at=now,
            detail="Auto-created v1 — a real 1:1 snapshot of the already-configured RiskLimits, never fabricated numbers.",
        )
        validated = _mark_validated_risk_contract(draft, now_iso=now)
        active, updated_history = _activate_risk_contract([*state.risk_contracts, validated], contract_id, now_iso=now)
        return state.model_copy(update={"risk_contracts": updated_history}), active

    async def ensure_active_risk_contract(self) -> RiskContract:
        """Lazily derives and persists a real v1 `RiskContract` the
        first time one is needed — see `_derive_active_risk_contract()`
        above for the real derivation rule. Idempotent: a second call
        when an active contract already exists returns it unchanged,
        never creates a second version. Safe to call from read paths
        (GET endpoints) — the fast path (an active contract already
        exists) never touches the lock."""
        existing = get_active_risk_contract(self.data.risk_contracts)
        if existing is not None:
            return existing
        async with self.lock:
            self.data, active = self._derive_active_risk_contract(self.data)
            return active

    async def create_draft_risk_contract(
        self, *, limits: RiskLimits, scaling_policy: RiskContractScalingPolicy | None, reason: str, created_by: str
    ) -> tuple[GameSaveState, RiskContract | None, str | None]:
        """Phase 1/2 — a real new DRAFT version, based on the CEO's own
        supplied `limits`/`scaling_policy` (never a caller-supplied
        version number — see `next_version_number()`). Never itself
        becomes ACTIVE — a draft must be separately validated then
        activated (see the two methods below), matching the directive's
        own explicit `DRAFT -> VALIDATED -> ACTIVE` lifecycle."""
        if not reason.strip():
            return self.data, None, "A reason is required when drafting a new risk contract."
        async with self.lock:
            contract_id = f"risk-contract-{uuid.uuid4().hex[:12]}"
            draft = _create_draft_risk_contract(
                history=self.data.risk_contracts,
                contract_id=contract_id,
                limits=limits,
                created_by=created_by,
                reason=reason,
                created_at=_now_iso(),
                scaling_policy=scaling_policy,
            )
            self.data = self.data.model_copy(update={"risk_contracts": [*self.data.risk_contracts, draft]})
            return self.data, draft, None

    async def validate_draft_risk_contract(self, contract_id: str) -> tuple[GameSaveState, RiskContractValidationResult | None, str | None]:
        """Phase 2 — runs real structural + policy validation
        (`app/risk_contract.py::validate_risk_contract()`). On a real
        pass, persists the transition to `validated` (the only status
        `activate_risk_contract()` below will accept). On a real
        failure, the draft is left untouched (still `draft`) and every
        real issue is returned — never a silent partial validation."""
        async with self.lock:
            target = next((c for c in self.data.risk_contracts if c.id == contract_id), None)
            if target is None:
                return self.data, None, f"No risk contract with id {contract_id!r} exists."
            if target.status != "draft":
                return self.data, None, f"Risk contract {contract_id} is not a draft (status={target.status!r}) — only a draft can be (re-)validated."
            result = validate_risk_contract(target)
            if not result.valid:
                return self.data, result, f"Risk contract {contract_id} failed validation: {'; '.join(i.message for i in result.issues)}"
            validated = _mark_validated_risk_contract(target, now_iso=_now_iso())
            updated_history = [validated if c.id == contract_id else c for c in self.data.risk_contracts]
            self.data = self.data.model_copy(update={"risk_contracts": updated_history})
            return self.data, result, None

    async def activate_risk_contract(self, contract_id: str) -> tuple[GameSaveState, RiskContract | None, str | None]:
        """Phase 1 — the one real ACTIVE-producing step. Requires the
        named contract to already be `validated`. Supersedes whatever
        contract is currently active in the SAME real, atomic update —
        never a moment with two simultaneously-active contracts, and no
        historical trade/decision that already referenced the previous
        version's `id`/`version` is ever rewritten."""
        async with self.lock:
            try:
                active, updated_history = _activate_risk_contract(self.data.risk_contracts, contract_id, now_iso=_now_iso())
            except ValueError as exc:
                return self.data, None, str(exc)
            self.data = self.data.model_copy(update={"risk_contracts": updated_history})
            return self.data, active, None

    async def archive_risk_contract(self, contract_id: str) -> tuple[GameSaveState, str | None]:
        """Real, disclosed terminal transition — reachable from any
        non-active state (an active contract must be superseded by
        activating its replacement first)."""
        async with self.lock:
            try:
                updated_history = _archive_risk_contract(self.data.risk_contracts, contract_id, now_iso=_now_iso())
            except ValueError as exc:
                return self.data, str(exc)
            self.data = self.data.model_copy(update={"risk_contracts": updated_history})
            return self.data, None

    async def record_risk_decision(self, decision: RiskDecision) -> GameSaveState:
        """Phase 4/5 — appends one real, permanent audit record (see
        `RiskDecision`'s own schema docstring). Never mutates or
        deletes an existing entry — this is historical evidence, same
        discipline as `decisions`/`ceo_decisions`."""
        async with self.lock:
            self.data = self.data.model_copy(update={"risk_decisions": [*self.data.risk_decisions, decision]})
            return self.data

    async def add_paper_trade_journal_note(self, entry_id: str, *, text: str) -> tuple[GameSaveState, PaperTradeJournalEntry | None, str | None]:
        """CEO directive "...then Paper-Trade Journal + Drift Detection +
        Strategy Health State Machine" — the one genuinely mutable-after-
        the-fact field on a journal entry (see `PaperTradeJournalEntry`'s
        own schema docstring for why): appends, never edits or removes,
        an existing note."""
        if not text.strip():
            return self.data, None, "Note text cannot be empty."
        async with self.lock:
            index = next((i for i, e in enumerate(self.data.paper_trade_journal) if e.id == entry_id), None)
            if index is None:
                return self.data, None, f"No paper trade journal entry with id {entry_id!r}."
            updated_entry = add_ceo_note(self.data.paper_trade_journal[index], text=text)
            journal = [*self.data.paper_trade_journal]
            journal[index] = updated_entry
            self.data = self.data.model_copy(update={"paper_trade_journal": journal})
            return self.data, updated_entry, None

    async def update_sniper_engine_config(
        self,
        *,
        status: str | None = None,
        mode: str | None = None,
        turbo: bool | None = None,
        copy_trading_enabled: bool | None = None,
    ) -> tuple[GameSaveState, str | None]:
        """CEO directive "TradeTown — Memecoin Sniper Agent," Section 23 —
        the CEO's real engine control surface. `mode="live"` is always
        rejected: `app/memecoin_sniper.py::evaluate_live_arming()` always
        reports blocked in this environment (no real Solana RPC/Jupiter/
        wallet credentials configured — see that function's own real,
        named reasons), so accepting the write here would create a
        config the engine could never honestly honor."""
        async with self.lock:
            updates: dict[str, object] = {}
            if status is not None:
                if status not in ("stopped", "running", "paused"):
                    return self.data, f"Invalid engine status {status!r} — must be stopped, running, or paused."
                updates["status"] = status
            if mode is not None:
                if mode == "live":
                    return self.data, "Live trading is blocked in this environment — no real Solana RPC/Jupiter/wallet credentials are configured. See GET /api/sniper/live-arming for the exact real reasons."
                if mode != "dry_run":
                    return self.data, f"Invalid engine mode {mode!r} — must be dry_run (live is blocked; see GET /api/sniper/live-arming)."
                updates["mode"] = mode
            if turbo is not None:
                updates["turbo"] = turbo
            if copy_trading_enabled is not None:
                updates["copy_trading_enabled"] = copy_trading_enabled
            if not updates:
                return self.data, None
            new_config = self.data.sniper_engine_config.model_copy(update=updates)
            self.data = self.data.model_copy(update={"sniper_engine_config": new_config})
            return self.data, None

    async def close_sniper_position(self, position_id: str, *, reason: str = "manual_exit") -> tuple[GameSaveState, SniperTrade | None, str | None]:
        """Section 18's manual exit path. Closes at the position's own
        real, already-simulated `current_price` — never a fabricated
        fill price. Returns `(state, trade_or_none, error)`."""
        from app.memecoin_sniper import close_position, update_risk_state_after_trade
        from app.schemas import SniperEvent

        async with self.lock:
            positions = list(self.data.sniper_positions)
            index = next((i for i, p in enumerate(positions) if p.id == position_id and p.status == "open"), None)
            if index is None:
                return self.data, None, f"No open sniper position with id {position_id!r}."
            now = datetime.now(timezone.utc).isoformat()
            closed_position, trade = close_position(positions[index], positions[index].current_price, reason, now)  # type: ignore[arg-type]
            positions[index] = closed_position
            trade_history = [*self.data.sniper_trade_history, trade]
            risk_state = update_risk_state_after_trade(self.data.sniper_risk_state, trade, now)
            # Real per-position risk (open_risk_sol) must drop immediately
            # when a position closes manually, not just at the next tick —
            # same real recompute app/memecoin_sniper.py's tick loop does.
            risk_state = risk_state.model_copy(update={"open_risk_sol": round(sum(p.risk_sol for p in positions if p.status == "open"), 6)})
            # Professional Trading Terminal directive, Part VII — the
            # manual-exit path bypasses tick_sniper_engine() entirely, so
            # it needs its own real event, same shape as the tick loop's
            # own "exit" events (see SniperEvent's own docstring).
            events = [
                *self.data.sniper_events,
                SniperEvent(id=f"evt-{trade.id}", timestamp=now, type="manual_exit", mint=trade.mint, symbol=trade.symbol, detail=f"{reason} — {trade.pnl_sol:+.4f} SOL ({trade.r_multiple:+.2f}R)"),
            ][-MAX_SNIPER_EVENTS:]
            self.data = self.data.model_copy(
                update={"sniper_positions": positions, "sniper_trade_history": trade_history, "sniper_risk_state": risk_state, "sniper_events": events}
            )
            return self.data, trade, None

    async def add_sniper_wallet(self, *, label: str, public_address: str, network: str) -> tuple[GameSaveState, SniperWallet | None, str | None]:
        """"Terminal 2.1" directive, Phase 5 — real wallet METADATA only
        (see `SniperWallet`'s own docstring for why no secret field
        exists anywhere on this model). The first wallet added becomes
        active automatically; later ones stay inactive until
        `set_active_sniper_wallet()` is called explicitly."""
        label = label.strip()
        public_address = public_address.strip()
        network = network.strip()
        if not label:
            return self.data, None, "A wallet label is required."
        if not public_address:
            return self.data, None, "A public address is required."
        if not network:
            return self.data, None, "A network is required."
        async with self.lock:
            wallets = list(self.data.sniper_wallets)
            wallet = SniperWallet(
                id=f"wallet-{uuid.uuid4().hex[:10]}",
                label=label,
                publicAddress=public_address,
                network=network,
                isActive=len(wallets) == 0,
                addedAt=datetime.now(timezone.utc).isoformat(),
            )
            wallets.append(wallet)
            self.data = self.data.model_copy(update={"sniper_wallets": wallets})
            return self.data, wallet, None

    async def remove_sniper_wallet(self, wallet_id: str) -> tuple[GameSaveState, str | None]:
        """Removes wallet METADATA only. Never touches
        `sniper_positions`/`sniper_trade_history` — paper trades in this
        codebase never route through a wallet at all (there is no real
        execution path that could have referenced one), so there is no
        historical trade identity to preserve or break here; that
        real architectural fact is the actual reason removal is safe,
        not an unverified assumption."""
        async with self.lock:
            wallets = list(self.data.sniper_wallets)
            index = next((i for i, w in enumerate(wallets) if w.id == wallet_id), None)
            if index is None:
                return self.data, f"No wallet with id {wallet_id!r}."
            removed_was_active = wallets[index].is_active
            del wallets[index]
            if removed_was_active and wallets:
                wallets[0] = wallets[0].model_copy(update={"is_active": True})
            self.data = self.data.model_copy(update={"sniper_wallets": wallets})
            return self.data, None

    async def set_active_sniper_wallet(self, wallet_id: str) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            wallets = list(self.data.sniper_wallets)
            if not any(w.id == wallet_id for w in wallets):
                return self.data, f"No wallet with id {wallet_id!r}."
            wallets = [w.model_copy(update={"is_active": w.id == wallet_id}) for w in wallets]
            self.data = self.data.model_copy(update={"sniper_wallets": wallets})
            return self.data, None

    async def activate_emergency_stop(self) -> tuple[GameSaveState, str | None]:
        """Design Bible Chapter 67 (TTOS) Part 3 — the CEO's real Global
        Emergency Stop. See app/emergency_stop.py's module docstring for
        exactly what this does and does not block. Design Bible Chapter
        70 Part 1 — a manual (CEO-clicked) activation is a real
        Emergency Board Meeting trigger, the same as the two automatic
        ones app/nexus.py's own tick() already fires this exact report
        for (circuit breaker Tier 4 / losing streak, and a Black Swan
        tier crossing)."""
        async with self.lock:
            new_state, error = _activate_emergency_stop(self.data.emergency_stop, now_iso=_now_iso())
            if error is not None:
                return self.data, error
            memory = list(self.data.memory)
            record_emergency_stop_event(memory, activated=True, max_records=self.data.risk_limits.max_memory_records)
            now_iso = _now_iso()
            board_report = generate_board_report(
                cadence="emergency",
                trigger="emergency_stop",
                trigger_detail="Emergency Stop activated — CEO manual",
                research=self.data.research,
                decisions=self.data.decisions,
                agent_ids=all_agent_ids(),
                company_health=self.data.company_health,
                black_swan_tier=self.data.black_swan_intelligence.warning.tier,
                circuit_breaker_tier=self.data.daily_circuit_breaker.tier,
                pending_ceo_decisions=len(self.data.trade_proposals),
                sim_day=self.data.time.day,
                report_id=f"board-emergency-stop-manual-{self.data.time.day}-{self.data.time.hour}-{self.data.time.minute}",
                now_iso=now_iso,
            )
            board_reports = record_board_report(list(self.data.board_reports), board_report)
            record(memory, "alert", "Emergency Board Report filed", board_report.summary, max_records=self.data.risk_limits.max_memory_records)
            self.data = self.data.model_copy(update={"emergency_stop": new_state, "memory": memory, "board_reports": board_reports})
            return self.data, None

    async def resume_trading(self) -> tuple[GameSaveState, str | None]:
        """Design Bible Chapter 67 (TTOS) Part 3 — only the CEO can resume
        trading after an Emergency Stop; there is no automatic timeout."""
        async with self.lock:
            new_state, error = _resume_trading(self.data.emergency_stop)
            if error is not None:
                return self.data, error
            memory = list(self.data.memory)
            record_emergency_stop_event(memory, activated=False, max_records=self.data.risk_limits.max_memory_records)
            self.data = self.data.model_copy(update={"emergency_stop": new_state, "memory": memory})
            return self.data, None

    async def activate_trading_restriction(
        self, *, scope: RestrictionScope, target: str, reason: str
    ) -> tuple[GameSaveState, str | None]:
        """CEO directive "Layered Kill Switches" — see
        app/trading_restrictions.py's module docstring for exactly what
        this does and does not block, and why it's scoped to
        symbol/category rather than duplicating the firm-wide Emergency
        Stop above."""
        async with self.lock:
            new_restrictions, restriction, error = _activate_trading_restriction(
                self.data.trading_restrictions, scope=scope, target=target, reason=reason, now_iso=_now_iso()
            )
            if error is not None or restriction is None:
                return self.data, error
            memory = list(self.data.memory)
            record_trading_restriction_event(memory, scope=scope, target=target, reason=restriction.reason, lifted=False, max_records=self.data.risk_limits.max_memory_records)
            self.data = self.data.model_copy(update={"trading_restrictions": new_restrictions, "memory": memory})
            return self.data, None

    async def lift_trading_restriction(self, restriction_id: str, *, reason: str = "") -> tuple[GameSaveState, str | None]:
        """Only the CEO can lift a restriction; there is no automatic
        timeout, the same real precedent app/emergency_stop.py's own
        resume_trading() already established."""
        async with self.lock:
            new_restrictions, lifted, error = _lift_trading_restriction(
                self.data.trading_restrictions, restriction_id, reason=reason, now_iso=_now_iso()
            )
            if error is not None or lifted is None:
                return self.data, error
            memory = list(self.data.memory)
            record_trading_restriction_event(memory, scope=lifted.scope, target=lifted.target, reason=lifted.lifted_reason or "", lifted=True, max_records=self.data.risk_limits.max_memory_records)
            self.data = self.data.model_copy(update={"trading_restrictions": new_restrictions, "memory": memory})
            return self.data, None

    async def set_trading_mode(self, *, mode: TradingMode, hybrid_day_allocation_pct: float | None) -> tuple[GameSaveState, str | None]:
        """Design Bible Chapter 75 — the CEO's real Trading Mode change.
        Blocked while Emergency Stop is active, the same real precedent
        every other CEO trading control in this codebase already
        follows — a mode change mid-halt has nothing real to act on."""
        async with self.lock:
            if self.data.emergency_stop.active:
                return self.data, "Trading is halted — Emergency Stop is active. Resume trading first."
            new_state, memory_entry = change_trading_mode(
                self.data.trading_modes, new_mode=mode, hybrid_day_allocation_pct=hybrid_day_allocation_pct, now_iso=_now_iso()
            )
            memory = [*self.data.memory, memory_entry]
            if len(memory) > self.data.risk_limits.max_memory_records:
                del memory[: len(memory) - self.data.risk_limits.max_memory_records]
            self.data = self.data.model_copy(update={"trading_modes": new_state, "memory": memory})
            return self.data, None

    async def set_adaptive_recommendations_enabled(self, enabled: bool) -> GameSaveState:
        """Design Bible Chapter 75 — the CEO's real on/off control over
        Adaptive Mode's recommendation reads. No safety property depends
        on this: `compute_adaptive_mode_recommendation()` never writes
        to any state (see its own docstring), so this is purely a CEO
        display preference, not gated on Emergency Stop the way an
        actual trading control is."""
        async with self.lock:
            new_trading_modes = self.data.trading_modes.model_copy(update={"adaptive_recommendations_enabled": enabled})
            self.data = self.data.model_copy(update={"trading_modes": new_trading_modes})
            return self.data

    async def set_behavioral_thresholds(self, *, cooldown_minutes: int, size_increase_threshold_pct: float) -> tuple[GameSaveState, str | None]:
        """The CEO's real, editable Behavioral Circuit Breaker thresholds
        (Design Bible Chapter 66 addendum, app/behavioral_risk.py) — a
        display/config preference, not gated on Emergency Stop, mirroring
        set_adaptive_recommendations_enabled above. Rejects non-positive
        values rather than silently accepting a threshold that would make
        the check meaningless (e.g. a 0-minute cooldown or 0% size
        threshold)."""
        if cooldown_minutes <= 0 or size_increase_threshold_pct <= 0:
            return self.data, "Cooldown minutes and size increase threshold must both be positive."
        async with self.lock:
            new_trading_modes = self.data.trading_modes.model_copy(
                update={"behavioral_cooldown_minutes": cooldown_minutes, "behavioral_size_increase_threshold_pct": size_increase_threshold_pct}
            )
            self.data = self.data.model_copy(update={"trading_modes": new_trading_modes})
            return self.data, None

    async def acknowledge_losing_streak(self) -> tuple[GameSaveState, str | None]:
        """Design Bible Chapter 75 — the CEO's real, explicit clear of
        the current losing-streak pause. Only meaningful while the pause
        is actually active; a no-op error otherwise, matching this
        codebase's other action-not-applicable error precedents."""
        async with self.lock:
            if not self.data.losing_streak.pause_active:
                return self.data, "There is no active losing-streak pause to acknowledge."
            new_state = acknowledge_losing_streak(self.data.trading_modes)
            self.data = self.data.model_copy(update={"trading_modes": new_state, "losing_streak": self.data.losing_streak.model_copy(update={"pause_active": False})})
            return self.data, None

    async def activate_travel_mode(self) -> tuple[GameSaveState, str | None]:
        """Design Bible Chapter 73.5 — the CEO's real, manual Travel Mode
        activation. Automatic (inactivity-based) activation is a
        separate real path — see app/nexus.py's tick() call into
        app/travel_mode.py's should_auto_activate()."""
        async with self.lock:
            if self.data.travel_mode.active:
                return self.data, "Travel Mode is already active."
            new_state, memory_entry = _activate_travel_mode(
                self.data.travel_mode, source="manual", now_iso=_now_iso(), now_sim_minutes=sim_minutes(self.data.time)
            )
            memory = [*self.data.memory, memory_entry]
            if len(memory) > self.data.risk_limits.max_memory_records:
                del memory[: len(memory) - self.data.risk_limits.max_memory_records]
            self.data = self.data.model_copy(update={"travel_mode": new_state, "memory": memory})
            return self.data, None

    async def deactivate_travel_mode(self) -> tuple[GameSaveState, str | None]:
        """Design Bible Chapter 73.5 — the CEO's real return-to-full-
        operations. Generates a real Return-to-Operations briefing from
        records inside the exact activation window before clearing the
        posture — see app/travel_mode.py's generate_travel_mode_briefing()."""
        async with self.lock:
            if not self.data.travel_mode.active:
                return self.data, "Travel Mode is not currently active."
            now_iso = _now_iso()
            now_sim = sim_minutes(self.data.time)
            briefing = generate_travel_mode_briefing(
                self.data.travel_mode,
                now_sim_minutes=now_sim,
                now_iso=now_iso,
                memory=self.data.memory,
                ceo_decisions=self.data.ceo_decisions,
                gatekeeper_rejections=self.data.gatekeeper_rejections,
                risk_warnings=self.data.risk_warnings,
                portfolio=self.data.paper_portfolio,
                briefing_id=f"travel-mode-{self.data.time.day}-{now_sim}",
            )
            new_state, memory_entry = _deactivate_travel_mode(self.data.travel_mode, now_iso=now_iso)
            memory = [*self.data.memory, memory_entry]
            if len(memory) > self.data.risk_limits.max_memory_records:
                del memory[: len(memory) - self.data.risk_limits.max_memory_records]
            briefings = [*self.data.travel_mode_briefings, briefing]
            if len(briefings) > MAX_TRAVEL_MODE_BRIEFINGS:
                del briefings[: len(briefings) - MAX_TRAVEL_MODE_BRIEFINGS]
            self.data = self.data.model_copy(update={"travel_mode": new_state, "memory": memory, "travel_mode_briefings": briefings})
            return self.data, None

    async def update_travel_mode_settings(self, update: dict[str, object]) -> tuple[GameSaveState, str | None]:
        """Design Bible Chapter 73.5 — the CEO's real settings PATCH.
        Values are clamped to their disclosed floor/ceiling by
        app/travel_mode.py's own update_travel_mode_settings(), never
        trusted verbatim from the client."""
        async with self.lock:
            if not update:
                return self.data, None
            new_state = _update_travel_mode_settings(self.data.travel_mode, update)
            self.data = self.data.model_copy(update={"travel_mode": new_state})
            return self.data, None

    async def configure_defensive_mode(self, *, trigger_tier: BlackSwanRiskTier | None, auto_trigger_enabled: bool | None) -> tuple[GameSaveState, str | None]:
        """Design Bible Chapter 72 — the CEO's own Defensive Mode
        trigger configuration. Purely a settings change; never activates
        or deactivates Defensive Mode itself (see activate/deactivate_
        defensive_mode below)."""
        async with self.lock:
            update: dict[str, object] = {}
            if trigger_tier is not None:
                update["trigger_tier"] = trigger_tier
            if auto_trigger_enabled is not None:
                update["auto_trigger_enabled"] = auto_trigger_enabled
            if not update:
                return self.data, None
            new_defensive_mode = self.data.defensive_mode.model_copy(update=update)
            self.data = self.data.model_copy(update={"defensive_mode": new_defensive_mode})
            return self.data, None

    async def activate_defensive_mode(self, *, reason: str = "Manually activated by the CEO.") -> tuple[GameSaveState, str | None]:
        """Design Bible Chapter 72 — a CEO-triggered (or, if configured,
        auto-triggered by app/nexus.py's tick()) defensive posture:
        tightens real RiskLimits and pauses new AI-generated trade
        proposals. Never touches an open position — see
        app/black_swan.py's module docstring."""
        async with self.lock:
            new_defensive_mode, new_limits, error = _activate_defensive_mode(
                self.data.defensive_mode,
                self.data.risk_limits,
                self.data.paper_portfolio,
                self.data.black_swan_intelligence.warning.tier,
                reason=reason,
                now_iso=_now_iso(),
                now_sim_minutes=sim_minutes(self.data.time),
            )
            if error is not None:
                return self.data, error
            self.data = self.data.model_copy(update={"defensive_mode": new_defensive_mode, "risk_limits": new_limits})
            return self.data, None

    async def deactivate_defensive_mode(self) -> tuple[GameSaveState, str | None]:
        """Design Bible Chapter 72 — restores the CEO's own pre-episode
        RiskLimits exactly (from the real snapshot taken at activation)
        and writes one permanent Post-Event Analysis record."""
        async with self.lock:
            new_defensive_mode, restored_limits, event, error = _deactivate_defensive_mode(
                self.data.defensive_mode,
                self.data.paper_portfolio,
                self.data.black_swan_intelligence.warning,
                now_iso=_now_iso(),
                now_sim_minutes=sim_minutes(self.data.time),
                event_id=f"bs-event-{self.data.time.day}-{sim_minutes(self.data.time)}",
            )
            if error is not None:
                return self.data, error
            update: dict[str, object] = {"defensive_mode": new_defensive_mode}
            if restored_limits is not None:
                update["risk_limits"] = restored_limits
            memory = list(self.data.memory)
            black_swan_events = list(self.data.black_swan_events)
            if event is not None:
                black_swan_events = record_black_swan_event(black_swan_events, event)
                record(memory, "lesson", f"Defensive Mode episode ended — peaked at {event.peak_tier.upper()}", event.lesson, max_records=self.data.risk_limits.max_memory_records)
                update["black_swan_events"] = black_swan_events
                update["memory"] = memory
            self.data = self.data.model_copy(update=update)
            return self.data, None

    async def create_goal(
        self,
        *,
        title: str,
        category: GoalCategory,
        target_metric: GoalMetric,
        target_value: float,
        deadline_sim_day: int | None,
    ) -> tuple[GameSaveState, str | None]:
        """v0.7 Design Bible Chapter 64 — the CEO authors a goal naming one
        real metric and a target. Validated the same way every other CEO
        write path in this class is (return (state, error), never raise);
        the goal's own `currentValue`/`progressPct` are computed once here
        from the company's real current state, then kept fresh every tick
        by `app/nexus.py`'s own `tick_goals()` call."""
        async with self.lock:
            title = title.strip()
            if not title:
                return self.data, "Goal title cannot be empty."
            if len(title) > 120:
                return self.data, "Goal title must be 120 characters or fewer."
            value_error = validate_target_value(target_metric, target_value)
            if value_error is not None:
                return self.data, value_error
            if deadline_sim_day is not None and deadline_sim_day <= self.data.time.day:
                return self.data, "Goal deadline must be a future simulation day."
            current_value = resolve_metric_value(
                target_metric,
                company_health=self.data.company_health,
                company_score=self.data.company_score,
                portfolio=self.data.paper_portfolio,
                academy_state=self.data.academy_state,
            )
            time = self.data.time
            goal_id = f"goal-{time.day}-{time.hour}-{time.minute}-{len(self.data.goals)}"
            goal = create_goal(
                goal_id=goal_id,
                title=title,
                category=category,
                target_metric=target_metric,
                target_value=target_value,
                deadline_sim_day=deadline_sim_day,
                created_sim_day=time.day,
                current_value=current_value,
            )
            self.data = self.data.model_copy(update={"goals": record_goal(self.data.goals, goal)})
            return self.data, None

    async def cancel_goal(self, goal_id: str) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            existing = next((g for g in self.data.goals if g.id == goal_id), None)
            if existing is None:
                return self.data, "No goal found with that id."
            if existing.status != "active":
                return self.data, "Only an active goal can be cancelled."
            self.data = self.data.model_copy(update={"goals": cancel_goal_entry(self.data.goals, goal_id)})
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

    async def create_account(self, name: str, account_type: AccountType, starting_balance: float) -> tuple[GameSaveState, str | None]:
        """Design Bible Chapter 69 Part 1 — a new, real, isolated
        sub-account, funded up front from a CEO-chosen starting balance
        (the CEO's own choice, not drawn from the Treasury automatically
        — see allocate_account_capital below for real, explicit
        Treasury-to-account transfers after creation)."""
        async with self.lock:
            account_id = f"account-{len(self.data.accounts)}-{_now_iso()}"
            accounts, error = create_account_fn(
                self.data.accounts,
                name=name,
                account_type=account_type,
                starting_balance=starting_balance,
                base_risk_limits=self.data.risk_limits,
                account_id=account_id,
                now_iso=_now_iso(),
            )
            if error is None:
                self.data = self.data.model_copy(update={"accounts": accounts})
            return self.data, error

    async def close_account(self, account_id: str) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            accounts, error = close_account_fn(self.data.accounts, account_id)
            if error is None:
                active = self.data.active_account_id
                self.data = self.data.model_copy(
                    update={"accounts": accounts, "active_account_id": None if active == account_id else active}
                )
            return self.data, error

    async def allocate_account_capital(self, account_id: str, amount: float) -> tuple[GameSaveState, str | None]:
        """Treasury -> a chosen account, under the same lock every other
        state mutation uses."""
        async with self.lock:
            time = self.data.time
            transaction_id = f"account-allocate-{account_id}-{time.day}-{time.hour}-{time.minute}-{len(self.data.treasury.transactions)}"
            accounts, treasury, error = allocate_capital_fn(
                self.data.accounts, self.data.treasury, account_id, amount, sim_day=time.day, now_iso=_now_iso(), transaction_id=transaction_id
            )
            if error is None:
                self.data = self.data.model_copy(update={"accounts": accounts, "treasury": treasury})
            return self.data, error

    async def deallocate_account_capital(self, account_id: str, amount: float) -> tuple[GameSaveState, str | None]:
        """A chosen account -> Treasury, under the same lock every other
        state mutation uses."""
        async with self.lock:
            time = self.data.time
            transaction_id = f"account-deallocate-{account_id}-{time.day}-{time.hour}-{time.minute}-{len(self.data.treasury.transactions)}"
            accounts, treasury, error = deallocate_capital_fn(
                self.data.accounts, self.data.treasury, account_id, amount, sim_day=time.day, now_iso=_now_iso(), transaction_id=transaction_id
            )
            if error is None:
                self.data = self.data.model_copy(update={"accounts": accounts, "treasury": treasury})
            return self.data, error

    async def configure_prop_firm_rules(
        self,
        account_id: str,
        *,
        trailing_drawdown_limit_pct: float | None,
        consistency_limit_pct: float | None,
        challenge_start_sim_day: int | None,
        challenge_duration_days: int | None,
        challenge_profit_target_pct: float | None,
    ) -> tuple[GameSaveState, str | None]:
        """Design Bible Chapter 69 Part 2 — a real CEO control configuring
        an account's Trailing Drawdown / Consistency / Challenge Window
        rules, under the same lock every other state mutation uses."""
        async with self.lock:
            accounts, error = configure_prop_firm_rules_fn(
                self.data.accounts,
                account_id,
                trailing_drawdown_limit_pct=trailing_drawdown_limit_pct,
                consistency_limit_pct=consistency_limit_pct,
                challenge_start_sim_day=challenge_start_sim_day,
                challenge_duration_days=challenge_duration_days,
                challenge_profit_target_pct=challenge_profit_target_pct,
            )
            if error is None:
                self.data = self.data.model_copy(update={"accounts": accounts})
            return self.data, error

    async def configure_evaluation_tracking(
        self,
        account_id: str,
        *,
        evaluation_cost: float | None,
        payout_eligibility_min_profit_pct: float | None,
    ) -> tuple[GameSaveState, str | None]:
        """Prop-Firm Risk Intelligence Addendum, Piece 10a — a real CEO
        control configuring an account's evaluation cost and payout
        eligibility threshold, under the same lock every other state
        mutation uses."""
        async with self.lock:
            accounts, error = configure_evaluation_tracking_fn(
                self.data.accounts,
                account_id,
                evaluation_cost=evaluation_cost,
                payout_eligibility_min_profit_pct=payout_eligibility_min_profit_pct,
            )
            if error is None:
                self.data = self.data.model_copy(update={"accounts": accounts})
            return self.data, error

    async def mark_account_funded(self, account_id: str) -> tuple[GameSaveState, str | None]:
        """Prop-Firm Risk Intelligence Addendum, Piece 10a — a real,
        explicit CEO action, never a system-inferred pass/fail."""
        async with self.lock:
            time = self.data.time
            accounts, error = mark_account_funded_fn(self.data.accounts, account_id, sim_day=time.day)
            if error is None:
                self.data = self.data.model_copy(update={"accounts": accounts})
            return self.data, error

    async def record_account_payout(self, account_id: str, amount: float) -> tuple[GameSaveState, str | None]:
        """Prop-Firm Risk Intelligence Addendum, Piece 10a — a real,
        CEO-recorded payout amount added to this account's permanent
        running total."""
        async with self.lock:
            accounts, error = record_account_payout_fn(self.data.accounts, account_id, amount=amount)
            if error is None:
                self.data = self.data.model_copy(update={"accounts": accounts})
            return self.data, error

    async def switch_active_account(self, account_id: str | None) -> tuple[GameSaveState, str | None]:
        """Design Bible Chapter 69 Part 1 — Account Switching. `None`
        means the primary PaperPortfolio; any other value must be a real
        account id. Purely a CEO-facing viewing preference — never
        changes which capital pool a trade executes against (see
        app/accounts.py's module docstring on live-trading scope)."""
        async with self.lock:
            if account_id is not None and not any(a.id == account_id for a in self.data.accounts):
                return self.data, f"No account with id {account_id!r}."
            self.data = self.data.model_copy(update={"active_account_id": account_id})
            return self.data, None

    async def add_custom_rule(self, account_id: str, *, rule_type: RuleType, label: str, limit: float, weekday: Weekday | None) -> tuple[GameSaveState, str | None]:
        """Design Bible Chapter 69 Part 3 — Custom Rule Builder. Real,
        structured rule authored by the CEO, added to one account's own
        rule list — no code change required to add a *rule*, only to add
        a new *rule type* (see app/rule_engine.py's module docstring for
        the honest boundary that draws)."""
        async with self.lock:
            rule_id = f"rule-{account_id}-{len(next((a.custom_rules for a in self.data.accounts if a.id == account_id), []))}-{_now_iso()}"
            accounts, error = add_custom_rule_fn(self.data.accounts, account_id, rule_type=rule_type, label=label, limit=limit, weekday=weekday, rule_id=rule_id)
            if error is None:
                self.data = self.data.model_copy(update={"accounts": accounts})
            return self.data, error

    async def remove_custom_rule(self, account_id: str, rule_id: str) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            accounts, error = remove_custom_rule_fn(self.data.accounts, account_id, rule_id)
            if error is None:
                self.data = self.data.model_copy(update={"accounts": accounts})
            return self.data, error

    async def toggle_custom_rule(self, account_id: str, rule_id: str, enabled: bool) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            accounts, error = toggle_custom_rule_fn(self.data.accounts, account_id, rule_id, enabled)
            if error is None:
                self.data = self.data.model_copy(update={"accounts": accounts})
            return self.data, error

    async def evaluate_account_rules(self, account_id: str) -> tuple[GameSaveState, str | None]:
        """Design Bible Chapter 69 Part 3 — the Institutional Rule
        Engine's one centralized evaluator (app/rule_engine.py),
        applied under the same lock every other state mutation uses so
        a real violation's Company Memory record (three of the brief's
        own four required behaviors on a rule failure: block, explain,
        record — see that module's own docstring) is written
        atomically with everything else. Read access to the result
        itself is via GET /api/accounts/rules/evaluate (no lock
        needed); this locked version exists so the CEO can trigger a
        real, permanently-recorded evaluation on demand."""
        async with self.lock:
            account = next((a for a in self.data.accounts if a.id == account_id), None)
            if account is None:
                return self.data, f"No account with id {account_id!r}."
            result = evaluate_rules(account, sim_day=self.data.time.day)
            memory = list(self.data.memory)
            record_rule_violation(memory, account.name, result)
            self.data = self.data.model_copy(update={"memory": memory})
            return self.data, None

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
            # CEO directive "Professional Research → Certification → Paper
            # → Capital Allocation Pipeline" — before granting real
            # allocated capital, also require the same real Research Desk
            # validation (look-ahead audit, cost-sensitivity, walk-forward)
            # the Sandbox's own on-demand endpoints already compute —
            # closes the gap where a strategy could reach live capital
            # having never been checked for look-ahead bias or cost
            # resilience. See evaluate_certification_readiness()'s own
            # docstring for why a missing compiled_definition_id is an
            # honest failure here, not a silent pass.
            look_ahead_audit = None
            cost_sensitivity_result = None
            walk_forward_result = None
            if strategy.compiled_definition_id is not None:
                versions = self.data.compiled_strategy_versions.get(strategy.compiled_definition_id, [])
                definition = versions[-1] if versions else None
                if definition is not None:
                    look_ahead_audit = audit_definition_for_look_ahead(definition)
                    cost_sensitivity_result = run_cost_sensitivity(definition)
                    walk_forward_result = run_walk_forward_validation(definition)
            ready, readiness_detail = evaluate_certification_readiness(
                strategy, self.data.simulation_results, monte_carlo, regime_test, look_ahead_audit, cost_sensitivity_result, walk_forward_result
            )
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
        real CEO-triggered moment, not three separate requests.

        v0.7 Quantitative Research & Intelligence System, Piece 4: this
        is also the one real call site that files Meridian/CIO's
        independent ModelValidationReport (app/model_validation.py),
        advisory-only — it never affects the stage transition below.
        Because this is the only place a ModelValidationReport is ever
        generated, `exclude_cio=True` is always passed to
        generate_strategy_review() here: Meridian is always acting as
        validator for this exact cycle, so it can never also serve as
        this same cycle's rotating Devil's Advocate. See
        app/model_validation.py's module docstring for why this is
        provably stateless (a pure function of existing_count, never a
        persisted flag)."""
        async with self.lock:
            strategy = self._find_strategy(strategy_id)
            if strategy is None:
                return self.data, "No strategy found with that id."
            updated, error = begin_company_review(strategy, self.data.time.day)
            if error is not None or updated is None:
                return self.data, error
            existing_count = sum(1 for r in self.data.strategy_reviews if r.strategy_id == strategy_id)
            review = generate_strategy_review(updated, self.data.simulation_results, self.data.research, existing_count, sim_day=self.data.time.day, exclude_cio=True)
            monte_carlo = next((r for r in reversed(self.data.strategy_monte_carlo_results) if r.strategy_id == strategy_id), None)
            regime_test = next((r for r in reversed(self.data.strategy_regime_tests) if r.strategy_id == strategy_id), None)
            liquidity_validation = next((r for r in reversed(self.data.strategy_liquidity_validations) if r.strategy_id == strategy_id), None)
            model_validation = generate_model_validation_report(
                updated, self.data.simulation_results, monte_carlo, regime_test, liquidity_validation, review.id, existing_count, sim_day=self.data.time.day
            )
            existing_exec_count = sum(1 for r in self.data.strategy_executive_reviews if r.strategy_id == strategy_id)
            executive_review = generate_strategy_executive_review(
                updated, review, self.data.research, self.data.coach_reports, monte_carlo, regime_test, self.data.market_intelligence, existing_exec_count, sim_day=self.data.time.day
            )
            founder_approval = generate_strategy_founder_approval(updated, executive_review, sim_day=self.data.time.day)
            strategies = [updated if s.id == strategy_id else s for s in self.data.strategies]
            strategy_reviews = [*self.data.strategy_reviews, review]
            strategy_model_validations = cap_strategy_model_validations([*self.data.strategy_model_validations, model_validation])
            strategy_executive_reviews = cap_strategy_executive_reviews([*self.data.strategy_executive_reviews, executive_review])
            strategy_founder_approvals = cap_strategy_founder_approvals([*self.data.strategy_founder_approvals, founder_approval])
            update: dict[str, object] = {
                "strategies": strategies,
                "strategy_reviews": strategy_reviews,
                "strategy_model_validations": strategy_model_validations,
                "strategy_executive_reviews": strategy_executive_reviews,
                "strategy_founder_approvals": strategy_founder_approvals,
            }
            # Feature 26 — only a non-"approved" verdict is a real
            # lesson worth promoting (see should_promote_model_
            # validation()); a routine approval is the expected outcome
            # of Meridian's process working normally, not a finding.
            if should_promote_model_validation(model_validation):
                update["institutional_memory"], update["knowledge_events"] = _promote_and_share_lesson(
                    self.data.institutional_memory, self.data.knowledge_events, promote_model_validation(model_validation), sim_day=self.data.time.day
                )
            self.data = self.data.model_copy(update=update)
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
        Trading Psychology & Discipline, Piece B — gated first by the
        real Statistical Evidence Gate (app/strategy_lab.py's
        evaluate_retirement_readiness()): a strategy that has entered
        real empirical testing must have a real minimum trade sample on
        file before it can be retired, so a strategy is never abandoned
        purely on impulse or a single bad run. Files exactly one of a
        real StrategyHallOfFameEntry or a real
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
        actually populated until now. Quantitative Research &
        Intelligence System, Piece 6 — the failed-archive path also
        folds in this strategy's own latest real ModelValidationReport
        (Piece 4), if one exists and isn't `approved`, so a real
        Meridian/CIO rejection becomes part of the same permanent
        record instead of being forgotten once Company Review ends."""
        async with self.lock:
            strategy = self._find_strategy(strategy_id)
            if strategy is None:
                return self.data, "No strategy found with that id."
            reason = reason.strip()
            if not reason:
                return self.data, "Retiring a strategy needs a real reason."
            # Trading Psychology & Discipline, Piece B — the Statistical
            # Evidence Gate on Strategy Retirement (Design Bible Chapter
            # 62 addendum). Blocks retirement only when the strategy has
            # entered real empirical testing but doesn't yet have enough
            # real evidence on file — never blocks the CEO's own real
            # decision once that evidence bar is real.
            ready, readiness_detail = evaluate_retirement_readiness(strategy, self.data.simulation_results)
            if not ready:
                return self.data, readiness_detail
            latest_review = next((r for r in reversed(self.data.strategy_reviews) if r.strategy_id == strategy_id), None)
            latest_executive_review = next((r for r in reversed(self.data.strategy_executive_reviews) if r.strategy_id == strategy_id), None)
            latest_founder_approval = next((a for a in reversed(self.data.strategy_founder_approvals) if a.strategy_id == strategy_id), None)
            # Quantitative Research & Intelligence System, Piece 6 — the
            # same real "latest record for this strategy" pattern as the
            # three lookups above, so a real Model Validation rejection
            # (Piece 4) becomes part of the permanent failed-archive
            # record instead of being forgotten once Company Review ends.
            latest_model_validation = next((m for m in reversed(self.data.strategy_model_validations) if m.strategy_id == strategy_id), None)
            hall_of_fame_entry, failed_archive_entry = generate_strategy_retirement_outcome(
                strategy,
                self.data.simulation_results,
                latest_review,
                latest_executive_review,
                latest_founder_approval,
                reason,
                sim_day=self.data.time.day,
                latest_model_validation=latest_model_validation,
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
                update["institutional_memory"], update["knowledge_events"] = _promote_and_share_lesson(
                    self.data.institutional_memory, self.data.knowledge_events, promote_hall_of_fame_strategy(hall_of_fame_entry), sim_day=self.data.time.day
                )
            else:
                assert failed_archive_entry is not None
                new_failed_archive = cap_strategy_failed_archive([*self.data.strategy_failed_archive, failed_archive_entry])
                update["strategy_failed_archive"] = new_failed_archive
                record_strategy_failed_archive_entry(memory, failed_archive_entry, max_records=self.data.risk_limits.max_memory_records)
                update["institutional_memory"], update["knowledge_events"] = _promote_and_share_lesson(
                    self.data.institutional_memory, self.data.knowledge_events, promote_failed_strategy(failed_archive_entry), sim_day=self.data.time.day
                )
                # Design Bible Chapter 74 Part 1 — the Strategy Retirement
                # Cluster generator, checked at the one real place a
                # retirement happens (a real CEO/player action, not
                # tick-driven — see app/strategy_lab.py's own module
                # docstring on why strategy retirement is never automatic).
                retirement_cluster_proposal = maybe_propose_retirement_cluster(
                    new_failed_archive, self.data.self_improvement_proposals, sim_day=self.data.time.day
                )
                if retirement_cluster_proposal is not None:
                    # Design Bible Chapter 74.5 — the Vision Alignment
                    # Engine, computed once at generation time (the field
                    # Chapter 74 reserved on SelfImprovementProposal for
                    # exactly this chapter to fill in).
                    alignment = compute_self_improvement_proposal_alignment(
                        retirement_cluster_proposal, self.data.vision_board
                    )
                    retirement_cluster_proposal = retirement_cluster_proposal.model_copy(
                        update={"vision_alignment_score": alignment.score}
                    )
                    update["self_improvement_proposals"] = record_self_improvement_proposal(
                        self.data.self_improvement_proposals, retirement_cluster_proposal
                    )
                    record(memory, "alert", "Self-Improvement Proposal filed", retirement_cluster_proposal.title, max_records=self.data.risk_limits.max_memory_records)
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

    async def decide_self_improvement_proposal(
        self, proposal_id: str, approve: bool, ceo_note: str | None
    ) -> tuple[GameSaveState, str | None]:
        """Design Bible Chapter 74 Part 1 — the CEO's own real, manual,
        final call on a Self-Improvement Proposal, never auto-resolved
        by Automation Mode, the same restraint decide_constitution_amendment
        above already holds itself to."""
        async with self.lock:
            proposal = next((p for p in self.data.self_improvement_proposals if p.id == proposal_id), None)
            if proposal is None:
                return self.data, "No self-improvement proposal found with that id."
            if proposal.status != "pending":
                return self.data, "That proposal has already been decided."
            proposals = decide_self_improvement_proposal(
                self.data.self_improvement_proposals, proposal_id, approve=approve, ceo_note=ceo_note
            )
            self.data = self.data.model_copy(update={"self_improvement_proposals": proposals})
            return self.data, None

    async def mark_self_improvement_proposal_implemented(
        self, proposal_id: str, implementation_note: str | None
    ) -> tuple[GameSaveState, str | None]:
        """Design Bible Chapter 74 Part 1 — the CEO's own real, manual
        record that an approved Self-Improvement Proposal was actually
        carried out. Never auto-triggered by approval itself (see
        app/self_improvement.py's own docstring for why no automatic
        mutation exists for this)."""
        async with self.lock:
            proposal = next((p for p in self.data.self_improvement_proposals if p.id == proposal_id), None)
            if proposal is None:
                return self.data, "No self-improvement proposal found with that id."
            if proposal.status != "approved":
                return self.data, "Only an approved proposal can be marked implemented."
            proposals = mark_self_improvement_proposal_implemented(
                self.data.self_improvement_proposals, proposal_id, implementation_note=implementation_note
            )
            self.data = self.data.model_copy(update={"self_improvement_proposals": proposals})
            return self.data, None

    async def set_vision_board_mission(self, mission: str | None) -> GameSaveState:
        """Design Bible Chapter 74.5 — the CEO Vision Board. CEO-mutated
        only, the same restraint every other CEO-authored singleton in
        this codebase (RiskLimits, ConstitutionState) holds itself to."""
        async with self.lock:
            board = set_vision_mission(self.data.vision_board, mission.strip() if mission else None)
            self.data = self.data.model_copy(update={"vision_board": board})
            return self.data

    async def set_vision_board_identity_note(self, identity_note: str | None) -> GameSaveState:
        async with self.lock:
            board = set_vision_identity_note(
                self.data.vision_board, identity_note.strip() if identity_note else None
            )
            self.data = self.data.model_copy(update={"vision_board": board})
            return self.data

    async def set_vision_board_priorities(self, priorities: list[str]) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            board, error = set_vision_priorities(self.data.vision_board, priorities)
            if error is not None:
                return self.data, error
            self.data = self.data.model_copy(update={"vision_board": board})
            return self.data, None

    async def add_vision_board_objective(self, text: str, category: str) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            board, error = add_vision_objective(self.data.vision_board, text, category)
            if error is not None:
                return self.data, error
            self.data = self.data.model_copy(update={"vision_board": board})
            return self.data, None

    async def remove_vision_board_objective(self, objective_id: str) -> GameSaveState:
        async with self.lock:
            board = remove_vision_objective(self.data.vision_board, objective_id)
            self.data = self.data.model_copy(update={"vision_board": board})
            return self.data

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

    async def submit_ceo_decision(
        self,
        proposal_id: str,
        choice: AnalystChoice,
        *,
        delegated: bool = False,
        override_reason: str | None = None,
        strategy_id: str | None = None,
    ) -> tuple[GameSaveState, str | None]:
        """Feature 12 — the CEO's (the player's) real buy/sell/wait call on
        a pending TradeProposal, applied under the same lock every other
        state mutation uses. Returns (state, error) — error is None on
        success. Resolves and removes the proposal immediately (unlike a
        broker order, this is a live player action, not a tick-driven
        fill) and appends both the resulting TradeDecision and
        CeoDecisionRecord, capped the same way tick()'s own decisions
        list is.

        `delegated` (Design Bible Chapter 70 Part 2) — the CEO explicitly
        clicked "Delegate to the Executive Board" rather than hand-picking
        `choice`; the caller (see routers/executive.py) is responsible for
        deriving `choice` from the Executive Intelligence Network's own
        real recommendation before calling this. The trade itself executes
        identically either way — this only changes what gets recorded
        about who decided it (resolved_by="delegated" instead of "ceo").

        `override_reason` (CEO directive "Features 31-35," Feature 32) —
        an optional real reason the CEO typed for this decision. Only
        ever stored on the resulting CeoDecisionRecord when this decision
        actually is an override (`choice != proposal.overall_recommendation`)
        — silently ignored otherwise rather than stored where it means
        nothing.

        `strategy_id` (CEO directive "Live Trade -> Strategy Provenance")
        — an optional real Strategy Lab strategy id the CEO explicitly
        selected for this decision, the one genuine, non-fabricated way
        this codebase can link a live trade back to a Strategy (see
        app/schemas.py's CeoDecisionRecord.strategy_id for the full
        honesty boundary). Validated against `self.data.strategies` —
        an id that doesn't match any real strategy is a real caller
        error (400), never silently dropped or silently accepted.
        Ignored (never stored) for a "wait" — there is no trade for any
        strategy to be attributed to."""
        async with self.lock:
            proposal = next((p for p in self.data.trade_proposals if p.id == proposal_id), None)
            if proposal is None:
                return self.data, f"No pending trade proposal with id {proposal_id!r}."
            if strategy_id is not None and not any(s.id == strategy_id for s in self.data.strategies):
                return self.data, f"No real Strategy Lab strategy with id {strategy_id!r}."
            # CEO directive "...then Paper-Trade Journal + Drift Detection
            # + Strategy Health State Machine," Phase 10 — "health reduces
            # risk, never grants extra." A SUSPENDED strategy's own real,
            # persisted risk_scaling_factor is 0.0 — the honest floor is a
            # hard stop, not a trade sized down to zero (TradeProposal
            # carries no strategy_id at generation time, so this is the
            # one real, enforceable point this codebase has to act on it;
            # see app/strategy_health.py's own module docstring for the
            # full disclosed integration-constraint reasoning).
            if strategy_id is not None and choice in ("buy", "sell"):
                health = self.data.strategy_health_states.get(strategy_id)
                if health is not None and health.state == "suspended":
                    return self.data, f"Strategy {strategy_id!r} is SUSPENDED (evidence-based drift, risk scaling 0.0) — cannot be attributed to a new trade until it recovers."
            # Design Bible Chapter 67 (TTOS) Part 3 — Emergency Stop blocks
            # every trade execution, including the CEO's own manual call;
            # "wait" (declining the trade) is still allowed since it never
            # executes anything. See app/emergency_stop.py's module
            # docstring for the full enforcement boundary.
            if self.data.emergency_stop.active and choice != "wait":
                return self.data, "Trading is halted — Emergency Stop is active. Resume trading first."

            watchlist_item = next((w for w in self.data.watchlist if w.symbol == proposal.symbol), None)
            current_price = watchlist_item.last_price if watchlist_item else None
            now_sim_minutes = sim_minutes(self.data.time)
            # v0.7 Feature 17 — the most recently generated debate for this
            # proposal (regenerate_debate can append more than one), fed
            # into the Gatekeeper's own debate-outcome check below.
            debate = next((d for d in reversed(self.data.debates) if d.proposal_id == proposal_id), None)
            resolved_by: Literal["ceo", "auto", "delegated"] = "delegated" if delegated else "ceo"

            # Design Bible Chapter 70 Part 3 addendum — "Research →
            # Executive Board Recommendation → Weighted Executive Decision
            # Engine → Trade Gatekeeper." Computed here (not inside
            # resolve_proposal itself) because the department opinions,
            # accuracy scores, and active Weight Profile all live in real
            # state only this call site has in scope; passed straight
            # through as one more advisory-only Gatekeeper check — see
            # app/gatekeeper.py's _weighted_executive_check for the exact
            # authority boundary. Skipped for a real "wait" (nothing for
            # the Gatekeeper to evaluate — resolve_proposal never calls it).
            weighted_recommendation = None
            if choice in ("buy", "sell"):
                challenge_report_for_opinions = next((c for c in reversed(self.data.challenge_reports) if c.proposal_id == proposal_id), None)
                opinions = generate_department_opinions(proposal, challenge_report_for_opinions, self.data.coach_reports, self.data.market_intelligence, self.data.decision_vault)
                raw_recommendation = compute_executive_recommendation(proposal, opinions)
                accuracy_scores = compute_executive_accuracy_scores(self.data.executive_meeting_log, self.data.ceo_decisions)
                weighted_recommendation = compute_weighted_recommendation(
                    proposal.id,
                    opinions,
                    accuracy_scores,
                    regime=self.data.market_environment.current,
                    profile=self.data.settings.active_weight_profile,
                    custom_weights=self.data.settings.custom_department_weights,
                    raw_action=raw_recommendation.action,
                )

            # Design Bible Chapter 75 — the Daily Circuit Breaker's real,
            # disclosed confidence bonus applies to a manual CEO decision
            # exactly like an auto-resolution (see app/nexus.py's
            # _apply_operating_mode) — the same Gatekeeper bar for
            # whoever resolves the proposal, not a mode-dependent one.
            # Design Bible Chapter 73.5 — Travel Mode's own real bonus
            # composes via max(), never adds on top of the Circuit
            # Breaker's (see app/travel_mode.py's module docstring).
            confidence_bonus = max(
                circuit_breaker_confidence_bonus(self.data.daily_circuit_breaker.tier),
                travel_mode_confidence_bonus(self.data.travel_mode),
            )
            min_confidence_override = (GATEKEEPER_MIN_CONFIDENCE + confidence_bonus) if confidence_bonus > 0 else None

            # CEO directive "Risk Contract Enforcement + Dynamic Risk
            # Scaling 1.0" — resolve the REAL, CURRENT (never stale)
            # RiskContract-scaled risk_limits BEFORE resolve_proposal()
            # ever sizes this trade, closing the exact asymmetry this
            # feature's own prior implementation had already found and
            # disclosed here: a proposal's quantity was scaled at
            # creation time (app/position_sizing.py, fed this tick's
            # effective_risk_limits in app/nexus.py), but re-deciding it
            # at THIS call site always recomputed resolve_proposal()'s
            # own sizing ceiling from the CEO's raw, unscaled risk_limits
            # — so a drawdown/losing-streak state (including the
            # contract's own kill switch) that worsened between proposal
            # creation and this decision never actually reduced or
            # blocked the trade. See app/risk_contract.py's
            # apply_active_risk_contract() for the full rationale — the
            # SAME function app/nexus.py's tick() now uses for proposal
            # generation, so this decision can never see contract
            # scaling more permissive than what governed the proposal's
            # own creation.
            #
            # `_derive_active_risk_contract()` guarantees a real,
            # persisted v1 contract exists (auto-derived from the CEO's
            # own already-configured risk_limits the first time one is
            # needed — never fabricated numbers) before the scaling
            # lookup below ever runs, mirroring `_advance_once()`'s own
            # identical guarantee for every tick. The `active_risk_
            # contract is None` branch is therefore unreachable in real
            # production use; it is kept as a genuine FAIL-CLOSED guard
            # (never fail-open) because this is a real order-placing
            # decision, not a mere display/proposal-generation read —
            # Non-Negotiable Principle 11/12.
            risk_limits_for_decision = self.data.risk_limits
            active_risk_contract: RiskContract | None = None
            risk_contract_scaling: RiskContractScalingRead | None = None
            if choice in ("buy", "sell"):
                self.data, _ = self._derive_active_risk_contract(self.data)
                pre_decision_portfolio = self.data.paper_portfolio
                live_drawdown_pct = max_drawdown_pct(
                    pre_decision_portfolio.trade_history,
                    pre_decision_portfolio.starting_balance,
                    current_equity=portfolio_equity(pre_decision_portfolio),
                )
                consecutive_losses = compute_consecutive_losses(pre_decision_portfolio.trade_history)
                risk_limits_for_decision, active_risk_contract, risk_contract_scaling = apply_active_risk_contract(
                    self.data.risk_limits,
                    risk_contracts=self.data.risk_contracts,
                    drawdown_pct=live_drawdown_pct,
                    consecutive_losses=consecutive_losses,
                )
                if active_risk_contract is None:
                    return self.data, "No active Risk Contract could be determined for this decision — failing closed rather than sizing this trade on unscaled risk limits."

            portfolio, decision, ceo_record = resolve_proposal(
                proposal,
                choice,
                portfolio=self.data.paper_portfolio,
                risk_limits=risk_limits_for_decision,
                current_price=current_price,
                now_sim_minutes=now_sim_minutes,
                market_intelligence=self.data.market_intelligence,
                debate=debate,
                risk_warnings=self.data.risk_warnings,
                resolved_by=resolved_by,
                weighted_recommendation=weighted_recommendation,
                min_confidence_override=min_confidence_override,
                behavioral_cooldown_minutes=self.data.trading_modes.behavioral_cooldown_minutes,
                behavioral_size_increase_threshold_pct=self.data.trading_modes.behavioral_size_increase_threshold_pct,
                trading_restrictions=self.data.trading_restrictions,
            )

            if override_reason and not ceo_record.agreed_with_ai:
                ceo_record = ceo_record.model_copy(update={"override_reason": override_reason})
            if strategy_id is not None and choice in ("buy", "sell"):
                ceo_record = ceo_record.model_copy(update={"strategy_id": strategy_id})
                # CEO directive "Complete Trade Provenance," Part 2 —
                # Strategy Rule Snapshot. Real, already-immutable history
                # already exists for CompiledStrategyDefinition
                # (app/strategy_registry.py's Feature 37, append-only,
                # never overwritten) — this just reads the CURRENT
                # (latest-appended = highest .version) entry for the
                # selected Strategy's own compiled_definition_id, at the
                # exact instant of this decision, and snapshots that
                # (id, version) pair. A later edit to the strategy
                # appends a NEW entry to the same list — this trade's
                # snapshot keeps pointing at the version that was real
                # when the trade was actually decided. Both stay None
                # when the Strategy has no compiled_definition_id yet
                # (a real "idea"-stage strategy with no represented
                # rules) — never fabricated.
                selected_strategy = next((s for s in self.data.strategies if s.id == strategy_id), None)
                compiled_definition_id = selected_strategy.compiled_definition_id if selected_strategy else None
                compiled_definition_version = None
                if compiled_definition_id is not None:
                    versions = self.data.compiled_strategy_versions.get(compiled_definition_id)
                    if versions:
                        compiled_definition_version = versions[-1].version
                ceo_record = ceo_record.model_copy(
                    update={
                        "strategy_compiled_definition_id": compiled_definition_id,
                        "strategy_compiled_definition_version": compiled_definition_version,
                    }
                )
                # CEO directive "Portfolio Construction, Capital Allocation
                # & Execution Realism" — the live analogue of the line
                # above: patches the freshly-opened PaperPosition (real
                # position id "pos-{proposal.id}", the exact same
                # deterministic id resolve_proposal() itself constructs)
                # with the same real strategy_id, strictly after the fact,
                # never altering what the trade itself did. No-ops
                # honestly if the position doesn't exist (Gatekeeper veto,
                # or sized to zero) — nothing to attribute.
                position_id = f"pos-{proposal.id}"
                positions = [p.model_copy(update={"strategy_id": strategy_id}) if p.id == position_id else p for p in portfolio.positions]
                portfolio = portfolio.model_copy(update={"positions": positions})

                # CEO directive "TradeTown — 11/10 Market Intelligence +
                # Quant Research Engine" — a real, non-blocking regime-
                # gated strategy warning. Recomputed fresh here, the same
                # on-demand pattern app/trade_pipeline_health.py's
                # diagnose_strategy_trading_pipeline() already uses (no
                # precomputed StrategyMatch lives on the live, per-tick
                # MarketIntelligenceState — only on the once-daily
                # MarketIntelligenceReport, which can be stale by the
                # time a real decision happens). Never blocks this trade,
                # never overrides the CEO, purely disclosed on the
                # permanent record for later review (Discipline/Decision
                # Vault).
                regime_match = compute_strategy_match(self.data.market_intelligence.regime, self.data.strategies, self.data.strategy_reports)
                if strategy_id in regime_match.avoided_strategy_ids:
                    ceo_record = ceo_record.model_copy(update={"regime_strategy_warning": regime_match.detail})

                # CEO directive "...then Paper-Trade Journal + Drift
                # Detection + Strategy Health State Machine," Phase 10 —
                # the exact same real, non-blocking disclosure pattern as
                # regime_match above. SUSPENDED already returned a hard
                # 400 earlier in this method, so only WATCH/DEGRADED/
                # CRITICAL/RECOVERING ever reach here.
                strategy_health = self.data.strategy_health_states.get(strategy_id)
                if strategy_health is not None and strategy_health.state != "healthy":
                    ceo_record = ceo_record.model_copy(
                        update={
                            "strategy_health_warning": (
                                f"Strategy health is {strategy_health.state.upper()} "
                                f"(risk scaling {strategy_health.risk_scaling_factor:g}x if new sizing could reflect it — "
                                "see app/strategy_health.py's own disclosed integration constraint)."
                            )
                        }
                    )

            # CEO directive "TradeTown — Persisted Risk Contract + Dynamic
            # Risk Scaling," Phase 4/5 — a real, persisted RiskDecision
            # audit record naming exactly which RiskContract version
            # governed this CEO decision's sizing/gatekeeper read — the
            # highest-value, most directly CEO-attributable "why was my
            # trade sized this way" record. Only recorded for a real
            # buy/sell — a "wait" never reaches sizing/the Gatekeeper, so
            # there is no real risk decision to audit.
            #
            # CEO directive "Auto-Resolution Risk Decision Audit Trail
            # 1.0" — this used to be an inline block computing the
            # RiskDecision directly; it's now app/risk_contract.py's own
            # build_risk_decision(), the ONE authoritative computation
            # this path and app/nexus.py's auto-resolution path both call
            # — never two competing implementations. Reuses
            # `active_risk_contract`/`risk_contract_scaling`, already
            # computed once above BEFORE resolve_proposal() ran (the same
            # real values that actually governed this decision's sizing).
            risk_decisions = list(self.data.risk_decisions)
            new_risk_decision = build_risk_decision(
                proposal, choice, decision, portfolio, active_risk_contract=active_risk_contract, risk_contract_scaling=risk_contract_scaling
            )
            if new_risk_decision is not None:
                risk_decisions.append(new_risk_decision)
                if len(risk_decisions) > MAX_RISK_DECISIONS:
                    del risk_decisions[: len(risk_decisions) - MAX_RISK_DECISIONS]

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
                    proposal,
                    decision,
                    ceo_record.ceo_decision,
                    challenge_report,
                    self.data.coach_reports,
                    self.data.market_intelligence,
                    self.data.decision_vault,
                    sim_day=self.data.time.day,
                    resolved_by=resolved_by,
                ),
            )

            ceo_decisions = [*self.data.ceo_decisions, ceo_record]
            if len(ceo_decisions) > MAX_CEO_DECISIONS:
                del ceo_decisions[: len(ceo_decisions) - MAX_CEO_DECISIONS]

            prediction_records = list(self.data.prediction_records)
            new_prediction = build_prediction_record(decision, ceo_record, sim_day=self.data.time.day)
            if new_prediction is not None:
                prediction_records.append(new_prediction)
                if len(prediction_records) > MAX_PREDICTION_RECORDS:
                    del prediction_records[: len(prediction_records) - MAX_PREDICTION_RECORDS]

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
                        reasonCodes=[c.code for c in verdict.checks if not c.passed and c.code is not None],
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
                    "prediction_records": prediction_records,
                    "gatekeeper_rejections": gatekeeper_rejections,
                    "risk_decisions": risk_decisions,
                    "memory": memory,
                    "executive_meeting_log": meeting_log,
                    # Design Bible Chapter 73.5 — real CEO activity, resets
                    # Travel Mode's inactivity-based auto-activation clock.
                    "travel_mode": self.data.travel_mode.model_copy(update={"last_ceo_decision_sim_minutes": now_sim_minutes}),
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
                    # Design Bible Chapter 73.5 — real CEO activity, resets
                    # Travel Mode's inactivity-based auto-activation clock.
                    "travel_mode": self.data.travel_mode.model_copy(update={"last_ceo_decision_sim_minutes": sim_minutes(self.data.time)}),
                    "updated_at": _now_iso(),
                }
            )
            return self.data, None

    async def modify_trade_proposal(self, proposal_id: str, new_quantity: float) -> tuple[GameSaveState, str | None]:
        """Design Bible Chapter 70 Part 2 — "Modify" as a real CEO
        decision action, distinct from buy/sell/wait/hold. Downsize-only
        (see app/executive.py's modify_proposal()) — the proposal stays
        pending afterward, same as hold_trade_proposal above: Modify
        resizes the trade, it doesn't decide it."""
        async with self.lock:
            proposal = next((p for p in self.data.trade_proposals if p.id == proposal_id), None)
            if proposal is None:
                return self.data, f"No pending trade proposal with id {proposal_id!r}."

            old_quantity = proposal.quantity
            modified = modify_proposal(proposal, new_quantity)
            if modified is None:
                return self.data, f"Invalid resize — quantity must be greater than 0 and no larger than the proposal's own {old_quantity:.2f}-share ceiling."

            memory = list(self.data.memory)
            record_proposal_modify(memory, modified, old_quantity)

            self.data = self.data.model_copy(
                update={
                    "trade_proposals": [modified if p.id == proposal_id else p for p in self.data.trade_proposals],
                    "memory": memory,
                    # Design Bible Chapter 73.5 — real CEO activity, resets
                    # Travel Mode's inactivity-based auto-activation clock.
                    "travel_mode": self.data.travel_mode.model_copy(update={"last_ceo_decision_sim_minutes": sim_minutes(self.data.time)}),
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
        # CEO directive "TradeTown — Persisted Risk Contract + Dynamic
        # Risk Scaling," Phase 12 — guarantee a real active RiskContract
        # exists before nexus.tick() ever runs, so its own dynamic
        # scaling step (app/risk_contract.py) always has one to read.
        # Already running under self.lock (see this method's own
        # docstring) — calls the sync derivation core directly rather
        # than the async ensure_active_risk_contract() wrapper, which
        # would deadlock trying to acquire the same non-reentrant lock.
        self.data, _active_risk_contract = self._derive_active_risk_contract(self.data)
        self.data = nexus.tick(self.data, new_time, minutes)

    # CEO directive "Features 31-35: Compliance, Governance & Continuous
    # Improvement System," Feature 31 — the Compliance Incident
    # Resolution Engine's real lifecycle mutations. Every method below
    # follows hold_trade_proposal()/modify_trade_proposal()'s own exact
    # pattern: locate the real incident, call the pure transition
    # function in app/compliance_incidents.py, return the same
    # "None means invalid transition, tell the caller" contract those
    # methods already established — never a silent no-op, never a
    # forced transition.
    async def start_investigating_incident(self, incident_id: str, owner: AgentId) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            incident = next((i for i in self.data.compliance_incidents if i.id == incident_id), None)
            if incident is None:
                return self.data, f"No compliance incident with id {incident_id!r}."
            updated = start_investigating(incident, owner=owner)
            if updated is None:
                return self.data, f"Incident {incident_id!r} is {incident.status!r} — cannot start investigating from that status."
            self.data = self.data.model_copy(
                update={"compliance_incidents": [updated if i.id == incident_id else i for i in self.data.compliance_incidents]}
            )
            return self.data, None

    async def begin_incident_remediation(
        self, incident_id: str, remediation_plan: str, deadline_sim_day: int
    ) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            incident = next((i for i in self.data.compliance_incidents if i.id == incident_id), None)
            if incident is None:
                return self.data, f"No compliance incident with id {incident_id!r}."
            updated = begin_remediation(incident, remediation_plan=remediation_plan, deadline_sim_day=deadline_sim_day)
            if updated is None:
                return self.data, f"Incident {incident_id!r} is {incident.status!r} — cannot begin remediation from that status."
            self.data = self.data.model_copy(
                update={"compliance_incidents": [updated if i.id == incident_id else i for i in self.data.compliance_incidents]}
            )
            return self.data, None

    async def add_incident_evidence(self, incident_id: str, note: str) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            incident = next((i for i in self.data.compliance_incidents if i.id == incident_id), None)
            if incident is None:
                return self.data, f"No compliance incident with id {incident_id!r}."
            updated = add_evidence(incident, note=note)
            self.data = self.data.model_copy(
                update={"compliance_incidents": [updated if i.id == incident_id else i for i in self.data.compliance_incidents]}
            )
            return self.data, None

    async def submit_incident_for_verification(self, incident_id: str) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            incident = next((i for i in self.data.compliance_incidents if i.id == incident_id), None)
            if incident is None:
                return self.data, f"No compliance incident with id {incident_id!r}."
            updated = submit_for_verification(incident)
            if updated is None:
                return self.data, f"Incident {incident_id!r} is {incident.status!r} — cannot submit for verification from that status."
            self.data = self.data.model_copy(
                update={"compliance_incidents": [updated if i.id == incident_id else i for i in self.data.compliance_incidents]}
            )
            return self.data, None

    async def fail_incident_verification(self, incident_id: str, note: str) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            incident = next((i for i in self.data.compliance_incidents if i.id == incident_id), None)
            if incident is None:
                return self.data, f"No compliance incident with id {incident_id!r}."
            updated = fail_verification(incident, note=note)
            if updated is None:
                return self.data, f"Incident {incident_id!r} is {incident.status!r} — verification can only fail from awaiting_verification."
            self.data = self.data.model_copy(
                update={"compliance_incidents": [updated if i.id == incident_id else i for i in self.data.compliance_incidents]}
            )
            return self.data, None

    async def verify_and_resolve_incident(
        self, incident_id: str, verifier: AgentId, root_cause: IncidentRootCause, corrective_action: str
    ) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            incident = next((i for i in self.data.compliance_incidents if i.id == incident_id), None)
            if incident is None:
                return self.data, f"No compliance incident with id {incident_id!r}."
            updated = verify_and_resolve(
                incident,
                verifier=verifier,
                root_cause=root_cause,
                corrective_action=corrective_action,
                sim_day=self.data.time.day,
            )
            if updated is None:
                return self.data, f"Incident {incident_id!r} is {incident.status!r} — can only resolve from awaiting_verification."
            self.data = self.data.model_copy(
                update={"compliance_incidents": [updated if i.id == incident_id else i for i in self.data.compliance_incidents]}
            )
            return self.data, None

    async def reopen_incident(self, incident_id: str, note: str) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            incident = next((i for i in self.data.compliance_incidents if i.id == incident_id), None)
            if incident is None:
                return self.data, f"No compliance incident with id {incident_id!r}."
            updated = reopen(incident, note=note)
            if updated is None:
                return self.data, f"Incident {incident_id!r} is {incident.status!r} — can only reopen a resolved incident."
            self.data = self.data.model_copy(
                update={"compliance_incidents": [updated if i.id == incident_id else i for i in self.data.compliance_incidents]}
            )
            return self.data, None

    # CEO directive "Features 31-35," Feature 32 — CEO Override
    # Governance's one real mutation: a reviewer's note on an existing
    # CeoOverrideEvaluation. Never gates or changes processQuality/outcome
    # (see app/override_governance.py's add_override_review()).
    async def add_override_review(self, evaluation_id: str, reviewer: AgentId, note: str) -> tuple[GameSaveState, str | None]:
        async with self.lock:
            evaluation = next((e for e in self.data.ceo_override_evaluations if e.id == evaluation_id), None)
            if evaluation is None:
                return self.data, f"No CEO override evaluation with id {evaluation_id!r}."
            updated = add_override_review(evaluation, reviewer=reviewer, note=note)
            self.data = self.data.model_copy(
                update={
                    "ceo_override_evaluations": [
                        updated if e.id == evaluation_id else e for e in self.data.ceo_override_evaluations
                    ]
                }
            )
            return self.data, None

    async def register_compiled_strategy_version(
        self, *, name: str, source_text: str, timeframe: str = "1h", created_by: AgentId = "quant"
    ) -> tuple[GameSaveState, CompiledStrategyDefinition]:
        """CEO directive "Professional Quant Firm Phase," Feature 37 —
        real, persisted `CompiledStrategyDefinition` version history
        (see app/strategy_registry.py). Under the same lock every other
        state mutation uses; the real next version number is derived
        from this strategy's own persisted history, never a
        caller-supplied guess."""
        async with self.lock:
            new_definition, updated_registry = register_strategy_version(
                self.data.compiled_strategy_versions, name=name, source_text=source_text, timeframe=timeframe, created_by=created_by
            )
            self.data = self.data.model_copy(update={"compiled_strategy_versions": updated_registry})
            return self.data, new_definition

    async def register_researchable_strategy(
        self,
        *,
        name: str,
        description: str,
        source_text: str,
        timeframe: str = "1h",
        created_by: AgentId = "quant",
        focus_category: ResearchCategory = "stock",
    ) -> tuple[GameSaveState, CompiledStrategyDefinition, Strategy | None]:
        """CEO directive "Strategy Intelligence + Live Strategy
        Attribution" — the real Strategy Lab <-> CompiledStrategyDefinition
        identity bridge (see app/strategy_registry.py's
        register_researchable_strategy() for the full real logic). Under
        the same lock every other state mutation uses; raises
        ValueError (the router translates this to a 400) if a Strategy
        with this exact real name/slug already exists — this is only
        for genuinely NEW Strategy Lab strategies."""
        async with self.lock:
            new_definition, new_strategy, updated_registry = register_researchable_strategy(
                self.data.compiled_strategy_versions,
                self.data.strategies,
                name=name,
                description=description,
                source_text=source_text,
                timeframe=timeframe,
                created_by=created_by,
                focus_category=focus_category,
            )
            updates: dict[str, object] = {"compiled_strategy_versions": updated_registry}
            if new_strategy is not None:
                updates["strategies"] = [*self.data.strategies, new_strategy]
            self.data = self.data.model_copy(update=updates)
            return self.data, new_definition, new_strategy

    async def submit_quant_research_experiment(
        self,
        definition: CompiledStrategyDefinition,
        *,
        hypothesis: str,
        researcher_agent_id: AgentId,
        symbols: list[str] | None = None,
        timeframe: str | None = None,
        candles_per_symbol: int | None = None,
        expected_mechanism: str | None = None,
        falsification_criteria: str | None = None,
    ) -> tuple[GameSaveState, SubmitQuantResearchExperimentResult]:
        """CEO directive "Professional Quant Firm Phase," Feature 36 —
        the Quant Research Lab's real, persisted experiment filing.
        Runs the already-real app/research_experiment.py pipeline once
        (no duplicate backtest math), checks it against every
        already-persisted experiment for a real near-duplicate (app/
        quant_research_lab.py's find_similar_experiments()), then
        permanently appends the new record — matching this codebase's
        own ever-growing, never-deleted archive convention. Under the
        same lock every other state mutation uses.

        CEO directive "Quant Research Factory / Strategy Discovery
        Engine," Phase 1 — `expected_mechanism`/`falsification_criteria`
        default to `None` here too (any caller that hasn't been
        threaded through this new field yet); the real API route
        (`app/routers/sandbox.py`) requires both on every new filing."""
        resolved_timeframe = timeframe if timeframe is not None else DEFAULT_TIMEFRAME
        resolved_candles = candles_per_symbol if candles_per_symbol is not None else DEFAULT_CANDLES_PER_SYMBOL
        record = run_research_experiment(definition, symbols=symbols, timeframe=resolved_timeframe, candles_per_symbol=resolved_candles)

        async with self.lock:
            similar = find_similar_experiments(self.data.quant_research_experiments, hypothesis=hypothesis, definition_id=definition.id, timeframe=resolved_timeframe)
            # CEO directive "TradeTown — Research Engine Hardening +
            # Self-Improvement Implementation Pass," Phase 3 — the same
            # real memory consultation, extended to the permanent Failed
            # Strategy Archive (previously never searched at all).
            # Purely informational: never blocks the filing below.
            similar_failed = find_similar_failed_strategies(self.data.strategy_failed_archive, hypothesis=hypothesis, strategy_name=definition.name)
            relationship = classify_research_relationship(similar, similar_failed)
            experiment_id = f"experiment-{definition.id}-{definition.version}-{len(self.data.quant_research_experiments)}"
            experiment = file_quant_research_experiment(
                record,
                experiment_id=experiment_id,
                hypothesis=hypothesis,
                researcher_agent_id=researcher_agent_id,
                created_at=_now_iso(),
                expected_mechanism=expected_mechanism,
                falsification_criteria=falsification_criteria,
                existing=self.data.quant_research_experiments,
            )
            updated = cap_quant_research_experiments([*self.data.quant_research_experiments, experiment])
            self.data = self.data.model_copy(update={"quant_research_experiments": updated})
            return self.data, SubmitQuantResearchExperimentResult(
                experiment=experiment,
                similarExperiments=similar,
                similarFailedStrategies=similar_failed,
                researchRelationship=relationship,
            )

    async def submit_champion_challenger_comparison(
        self,
        champion_definition: CompiledStrategyDefinition,
        challenger_definition: CompiledStrategyDefinition,
        *,
        strategy_family: str,
        hypothesis: str,
        proposed_by: AgentId,
        symbols: list[str] | None = None,
        timeframe: str | None = None,
        candles_per_symbol: int | None = None,
    ) -> tuple[GameSaveState, ChallengerComparison]:
        """CEO directive "TradeTown — 11/10 Self-Improving Quant Agent
        System," Section 1 — real, permanently-persisted Champion vs
        Challenger comparisons (see app/champion_challenger.py). Both
        real backtests run OUTSIDE the lock (same convention
        submit_quant_research_experiment() above already established);
        only the append is under the shared lock. Never mutates
        champion_history — see promote_champion_challenger() below."""
        resolved_timeframe = timeframe if timeframe is not None else DEFAULT_TIMEFRAME
        resolved_candles = candles_per_symbol if candles_per_symbol is not None else DEFAULT_CANDLES_PER_SYMBOL
        # A uuid suffix (app/persistence.py's own established convention for a
        # run-scoped id), not a list-length counter — the real backtest below
        # runs outside the lock, so a length snapshotted beforehand could
        # collide with a concurrent request's id by the time either appends.
        comparison_id = f"comparison-{challenger_definition.id}-{challenger_definition.version}-{uuid.uuid4().hex[:12]}"
        async with self.lock:
            # A real snapshot of the multiple-testing archive as of the START of this
            # comparison — the slow real backtest below runs outside the lock, so any
            # experiment filed concurrently during it is honestly not reflected in this
            # one comparison's own count, same real limitation any point-in-time count has.
            quant_research_experiments = self.data.quant_research_experiments
        comparison = compare_champion_challenger(
            champion_definition,
            challenger_definition,
            strategy_family=strategy_family,
            hypothesis=hypothesis,
            proposed_by=proposed_by,
            comparison_id=comparison_id,
            generated_at=_now_iso(),
            symbols=symbols,
            timeframe=resolved_timeframe,
            candles_per_symbol=resolved_candles,
            quant_research_experiments=quant_research_experiments,
        )
        async with self.lock:
            updated = [*self.data.challenger_comparisons, comparison]
            # CEO directive "TradeTown — Autonomous Quant Company 2.0,"
            # Phase 5 — the ONE real trigger point where a NEW,
            # potentially-promotable ChallengerComparison can appear
            # (compare_champion_challenger() is never called from
            # anywhere else — see app/autonomous_promotion.py's own
            # module docstring for why this event-driven point, not a
            # tick()-based sweep, is the correct real hook). Sweeps every
            # real pending comparison, not just this new one, so an
            # older comparison that was created before this directive
            # shipped and never got a human click is honestly evaluated
            # too, exactly once (find_promotable_comparisons() itself is
            # idempotent — see its own docstring).
            updated_champion_history, _ = apply_autonomous_promotions(updated, self.data.champion_history)
            self.data = self.data.model_copy(update={"challenger_comparisons": updated, "champion_history": updated_champion_history})
            return self.data, comparison

    async def promote_champion_challenger(self, *, comparison_id: str, promoted_by: AgentId, reasoning: str) -> tuple[GameSaveState, ChampionRecord]:
        """Same directive, Section 1 — the one real, explicit action
        that changes the current champion for a strategy family. Raises
        ValueError (surfaced by the router as a 400) when the named
        comparison doesn't exist or its own real verdict was not
        "challenger_recommended" — see app/champion_challenger.py's
        promote_challenger()."""
        async with self.lock:
            comparison = next((c for c in self.data.challenger_comparisons if c.id == comparison_id), None)
            if comparison is None:
                raise ValueError(f"No real ChallengerComparison found with id '{comparison_id}'.")
            # CEO directive "TradeTown — Autonomous Quant Company 2.0,"
            # Phase 19 (duplicate promotion must fail closed) — this
            # comparison may already have been promoted automatically
            # (see app/autonomous_promotion.py, wired into this same
            # comparison's own creation above) or by an earlier real
            # human click; either way, promoting the SAME real
            # comparison twice would create two ChampionRecords for one
            # real evidence gate having already passed once, which is
            # never honest history. Real, existing linkage
            # (ChampionRecord.source_comparison_id), never a new flag.
            already_promoted = next((r for r in self.data.champion_history if r.source_comparison_id == comparison_id), None)
            if already_promoted is not None:
                raise ValueError(
                    f"Comparison '{comparison_id}' was already promoted (see ChampionRecord '{already_promoted.id}', by '{already_promoted.promoted_by}')."
                )
            record = promote_challenger(
                comparison,
                promoted_by=promoted_by,
                reasoning=reasoning,
                record_id=f"champion-{comparison.strategy_family}-{len(self.data.champion_history)}",
                promoted_at=_now_iso(),
            )
            updated = [*self.data.champion_history, record]
            self.data = self.data.model_copy(update={"champion_history": updated})
            return self.data, record

    async def submit_research_loop_iteration(
        self,
        hypothesis: StrategyHypothesis,
        definition: CompiledStrategyDefinition,
        *,
        symbols: list[str] | None = None,
        timeframe: str | None = None,
        candles_per_symbol: int | None = None,
    ) -> tuple[GameSaveState, ResearchLoopIterationRecord]:
        """CEO directive "TradeTown — Next Major Implementation Pass,
        Phase 4-6: Self-Improving Strategy Factory + Validation
        Funnel" — see app/research_loop.py's own module docstring for
        the full real architecture. Both real snapshots (the archives
        `run_research_loop_iteration()` reads for memory/budget/tuning
        context) are taken under the lock BEFORE the slow real backtest
        runs outside it, same real convention
        submit_champion_challenger_comparison() above already
        established, for the identical real reason (a length/count
        snapshotted after slow work could be stale by the time this
        iteration's own append lands). Permanently persists both a
        `ResearchLoopIterationRecord` and a real, templated
        `ResearchLessonRecord` — never mutates any existing gate's own
        state (Certification/Hall-of-Fame/Champion-Challenger)."""
        resolved_timeframe = timeframe if timeframe is not None else DEFAULT_TIMEFRAME
        resolved_candles = candles_per_symbol if candles_per_symbol is not None else DEFAULT_CANDLES_PER_SYMBOL
        iteration_id = f"research-loop-{definition.id}-{definition.version}-{uuid.uuid4().hex[:12]}"
        mutation_id = f"mutation-{definition.id}-{definition.version}-{uuid.uuid4().hex[:12]}"
        async with self.lock:
            quant_research_experiments = self.data.quant_research_experiments
            research_iterations = self.data.research_iterations
            failed_archive = self.data.strategy_failed_archive
            risk_per_trade_pct = self.data.risk_limits.risk_per_trade_pct
        iteration = run_research_loop_iteration(
            hypothesis,
            definition,
            quant_research_experiments=quant_research_experiments,
            research_iterations=research_iterations,
            failed_archive=failed_archive,
            risk_per_trade_pct=risk_per_trade_pct,
            iteration_id=iteration_id,
            mutation_id=mutation_id,
            created_at=_now_iso(),
            symbols=symbols,
            timeframe=resolved_timeframe,
            candles_per_symbol=resolved_candles,
        )
        lesson = generate_research_lesson(
            lesson_id=f"lesson-{iteration.id}",
            strategy_family=iteration.strategy_family,
            definition_id=definition.id,
            definition_version=definition.version,
            iteration_id=iteration.id,
            parent_definition_id=hypothesis.parent_definition_id,
            mutation_id=(iteration.mutation.id if iteration.mutation is not None else None),
            hypothesis=hypothesis.hypothesis,
            candidacy=iteration.candidacy,
            candidacy_reason=iteration.candidacy_reason,
            scorecard=iteration.scorecard,
            trade_count=iteration.scorecard.trade_count or 0,
            created_at=iteration.created_at,
            failure_codes=[fc.code for fc in iteration.failure_codes],
        )
        async with self.lock:
            updated_iterations = [*self.data.research_iterations, iteration]
            updated_lessons = [*self.data.research_lessons, lesson]
            update: dict[str, object] = {"research_iterations": updated_iterations, "research_lessons": updated_lessons}
            if should_promote_research_lesson(lesson):
                update["institutional_memory"], update["knowledge_events"] = _promote_and_share_lesson(
                    self.data.institutional_memory,
                    self.data.knowledge_events,
                    promote_research_lesson(lesson, sim_day=self.data.time.day),
                    sim_day=self.data.time.day,
                )
            self.data = self.data.model_copy(update=update)
            return self.data, iteration

    async def submit_research_factory_run(
        self,
        hypothesis: StrategyHypothesis,
        definition: CompiledStrategyDefinition,
        *,
        max_generations: int | None = None,
        max_total_backtests: int | None = None,
        symbols: list[str] | None = None,
        timeframe: str | None = None,
        candles_per_symbol: int | None = None,
        max_children_per_parent: int | None = None,
        max_runtime_seconds: int | None = None,
    ) -> tuple[GameSaveState, FactoryRunRecord]:
        """CEO directive "TradeTown — Phase 7: Autonomous Strategy
        Evolution Engine" — see app/research_factory.py's own module
        docstring for the full real architecture. Runs the potentially
        slow, real, multi-generation loop OUTSIDE the lock (same
        real convention submit_research_loop_iteration() above already
        established, for the identical real reason). Concurrency-safe
        by construction: only the NEW iterations/lessons this run itself
        produced (never the whole stale snapshot the loop started from)
        are appended onto whatever `research_iterations`/
        `research_lessons` look like at the FINAL lock acquisition, and
        only this ONE strategy family's own updated version history is
        merged back into `compiled_strategy_versions` — a concurrent
        write to a different family, or a new iteration/lesson filed by
        another request while this run was in flight, is never lost."""
        resolved_timeframe = timeframe if timeframe is not None else DEFAULT_TIMEFRAME
        resolved_candles = candles_per_symbol if candles_per_symbol is not None else DEFAULT_CANDLES_PER_SYMBOL
        run_id = f"factory-run-{definition.id}-{definition.version}-{uuid.uuid4().hex[:12]}"
        async with self.lock:
            quant_research_experiments = self.data.quant_research_experiments
            research_iterations_snapshot = self.data.research_iterations
            research_lessons_snapshot = self.data.research_lessons
            failed_archive = self.data.strategy_failed_archive
            champion_history = self.data.champion_history
            risk_per_trade_pct = self.data.risk_limits.risk_per_trade_pct
            registry_snapshot = self.data.compiled_strategy_versions
            started_sim_day = self.data.time.day
        resolved_max_generations = max_generations if max_generations is not None else MAX_GENERATIONS_PER_FACTORY_RUN
        resolved_max_total_backtests = max_total_backtests if max_total_backtests is not None else MAX_TOTAL_BACKTESTS_PER_FACTORY_RUN
        # CEO directive "TradeTown — Phase 9: Full Autonomous Quant
        # Research Factory," Phase 5 — every NEW live factory run
        # started through this real entry point defaults to the richer,
        # tree-shaped branching behavior (module constants, not the
        # pure function's own conservative default of 1/0, which exists
        # solely so every pre-existing direct caller/test of
        # run_research_factory_cycle() is unaffected).
        resolved_max_children_per_parent = max_children_per_parent if max_children_per_parent is not None else MAX_CHILDREN_PER_PARENT
        resolved_max_runtime_seconds = max_runtime_seconds if max_runtime_seconds is not None else MAX_RUNTIME_SECONDS
        run_record, updated_registry, all_iterations, all_lessons = run_research_factory_cycle(
            hypothesis,
            definition,
            compiled_strategy_registry=registry_snapshot,
            quant_research_experiments=quant_research_experiments,
            research_iterations=research_iterations_snapshot,
            research_lessons=research_lessons_snapshot,
            failed_archive=failed_archive,
            champion_history=champion_history,
            risk_per_trade_pct=risk_per_trade_pct,
            run_id=run_id,
            created_at=_now_iso(),
            max_generations=resolved_max_generations,
            max_total_backtests=resolved_max_total_backtests,
            symbols=symbols,
            timeframe=resolved_timeframe,
            candles_per_symbol=resolved_candles,
            max_children_per_parent=resolved_max_children_per_parent,
            max_runtime_seconds=resolved_max_runtime_seconds,
        )
        # CEO directive "TradeTown — Autonomous Research Orchestrator
        # 1.0" — real simulation-time cadence field, populated the exact
        # same way regardless of whether a human or the new orchestrator
        # triggered this run.
        run_record = run_record.model_copy(update={"sim_day": started_sim_day})
        new_iterations = all_iterations[len(research_iterations_snapshot):]
        new_lessons = all_lessons[len(research_lessons_snapshot):]
        family_slug = strategy_definition_slug(definition.name)
        async with self.lock:
            updated_iterations = [*self.data.research_iterations, *new_iterations]
            updated_lessons = [*self.data.research_lessons, *new_lessons]
            updated_full_registry = {**self.data.compiled_strategy_versions, family_slug: updated_registry.get(family_slug, [])}
            updated_runs = [*self.data.factory_runs, run_record]
            updated_institutional_memory = self.data.institutional_memory
            updated_knowledge_events = self.data.knowledge_events
            for new_lesson in new_lessons:
                if should_promote_research_lesson(new_lesson):
                    updated_institutional_memory, updated_knowledge_events = _promote_and_share_lesson(
                        updated_institutional_memory,
                        updated_knowledge_events,
                        promote_research_lesson(new_lesson, sim_day=self.data.time.day),
                        sim_day=self.data.time.day,
                    )
            self.data = self.data.model_copy(
                update={
                    "research_iterations": updated_iterations,
                    "research_lessons": updated_lessons,
                    "compiled_strategy_versions": updated_full_registry,
                    "factory_runs": updated_runs,
                    "institutional_memory": updated_institutional_memory,
                    "knowledge_events": updated_knowledge_events,
                }
            )
            return self.data, run_record

    async def submit_research_discovery_cycle(
        self,
        *,
        concept_name: str,
        population_size: int,
        seed: str,
        proposed_by: AgentId,
        families: tuple[str, ...] | None = None,
        symbols: list[str] | None = None,
        timeframe: str | None = None,
        candles_per_symbol: int | None = None,
    ) -> tuple[GameSaveState, ResearchDiscoveryCycleRecord]:
        """CEO directive "TradeTown — Phase 8: Autonomous Strategy
        Discovery + Adversarial Research Engine" — see
        app/research_discovery.py's own module docstring for the full
        real architecture. Runs the potentially slow, real,
        population-generation + adversarial-attack loop OUTSIDE the
        lock (same real convention submit_research_factory_run() above
        already established). Concurrency-safe by construction: only
        the NEW iterations/lessons this cycle itself produced are
        appended, and only the specific strategy slugs this cycle
        actually compiled are merged back into
        `compiled_strategy_versions` — generalizing the same single-
        slug merge submit_research_factory_run() already established to
        the real, multiple, independently-named strategies one
        discovery cycle produces."""
        resolved_timeframe = timeframe if timeframe is not None else DEFAULT_TIMEFRAME
        resolved_candles = candles_per_symbol if candles_per_symbol is not None else DEFAULT_CANDLES_PER_SYMBOL
        resolved_families = tuple(families) if families else SUPPORTED_FAMILIES
        cycle_id = f"discovery-cycle-{strategy_definition_slug(concept_name)}-{uuid.uuid4().hex[:12]}"
        async with self.lock:
            quant_research_experiments = self.data.quant_research_experiments
            research_iterations_snapshot = self.data.research_iterations
            research_lessons_snapshot = self.data.research_lessons
            failed_archive = self.data.strategy_failed_archive
            champion_history = self.data.champion_history
            risk_per_trade_pct = self.data.risk_limits.risk_per_trade_pct
            registry_snapshot = self.data.compiled_strategy_versions
            existing_candidates = [c for cycle in self.data.discovery_cycles for c in cycle.candidates]
        record, updated_registry, all_iterations, all_lessons = run_research_discovery_cycle(
            concept_name=concept_name,
            population_size=population_size,
            seed=seed,
            compiled_strategy_registry=registry_snapshot,
            quant_research_experiments=quant_research_experiments,
            research_iterations=research_iterations_snapshot,
            research_lessons=research_lessons_snapshot,
            failed_archive=failed_archive,
            champion_history=champion_history,
            existing_candidates=existing_candidates,
            risk_per_trade_pct=risk_per_trade_pct,
            cycle_id=cycle_id,
            created_at=_now_iso(),
            proposed_by=proposed_by,
            families=resolved_families,  # type: ignore[arg-type]
            symbols=symbols,
            timeframe=resolved_timeframe,
            candles_per_symbol=resolved_candles,
        )
        new_iterations = all_iterations[len(research_iterations_snapshot):]
        new_lessons = all_lessons[len(research_lessons_snapshot):]
        changed_slugs = {slug for slug, versions in updated_registry.items() if registry_snapshot.get(slug) != versions}
        async with self.lock:
            updated_iterations = [*self.data.research_iterations, *new_iterations]
            updated_lessons = [*self.data.research_lessons, *new_lessons]
            updated_full_registry = {**self.data.compiled_strategy_versions, **{slug: updated_registry[slug] for slug in changed_slugs}}
            updated_cycles = [*self.data.discovery_cycles, record]
            updated_institutional_memory = self.data.institutional_memory
            updated_knowledge_events = self.data.knowledge_events
            for new_lesson in new_lessons:
                if should_promote_research_lesson(new_lesson):
                    updated_institutional_memory, updated_knowledge_events = _promote_and_share_lesson(
                        updated_institutional_memory,
                        updated_knowledge_events,
                        promote_research_lesson(new_lesson, sim_day=self.data.time.day),
                        sim_day=self.data.time.day,
                    )
            self.data = self.data.model_copy(
                update={
                    "research_iterations": updated_iterations,
                    "research_lessons": updated_lessons,
                    "compiled_strategy_versions": updated_full_registry,
                    "discovery_cycles": updated_cycles,
                    "institutional_memory": updated_institutional_memory,
                    "knowledge_events": updated_knowledge_events,
                }
            )
            return self.data, record

    async def tick(self, minutes: int) -> GameSaveState:
        """Advance the game clock and run one NEXUS orchestration step. Called by the sim loop."""
        async with self.lock:
            self._advance_once(minutes)
            return self.data

    async def maybe_orchestrate_research(self) -> ResearchOrchestratorDecision:
        """CEO directive "TradeTown — Autonomous Research Orchestrator
        1.0" — called by app/sim.py's real background sim loop once per
        real-time tick, AFTER `tick()` above has already returned and
        released `self.lock`. Deliberately never called from inside
        `_advance_once()`/`tick()`'s own lock: a factory cycle can take
        up to `MAX_RUNTIME_SECONDS` (300) real seconds, and awaiting
        that under `self.lock` would freeze every other read/write in
        the whole simulation for up to five real minutes (Part
        XXVII/XXVIII). The decision itself
        (`decide_research_orchestration()`, `app/research_orchestrator.py`)
        is pure and cheap; only a state snapshot is taken under the
        lock. If due, this schedules the existing, unmodified
        `submit_research_factory_run()` as a background task and
        returns immediately — never blocks the caller."""
        async with self.lock:
            state_snapshot = self.data
        factory_currently_running = self._research_orchestrator_task is not None and not self._research_orchestrator_task.done()
        decision = decide_research_orchestration(
            state_snapshot,
            factory_currently_running=factory_currently_running,
            last_orchestrator_attempt_sim_day=self._research_orchestrator_last_attempt_sim_day,
        )
        self._research_orchestrator_last_decision = decision
        if decision.should_run and decision.seed is not None:
            # Part XII (bounded retry) — recorded the moment an attempt
            # STARTS, regardless of eventual success/failure, so a
            # persistently-failing seed cannot retry every tick; only
            # once per RESEARCH_CADENCE_SIM_DAYS, same as a real success.
            self._research_orchestrator_last_attempt_sim_day = decision.sim_day
            self._research_orchestrator_task = asyncio.create_task(self._run_orchestrated_research_cycle(decision.seed))
        return decision

    async def _run_orchestrated_research_cycle(self, seed: ResearchOrchestratorSeed) -> None:
        """Runs the exact same, unmodified `submit_research_factory_run()`
        a human `POST /research-factory/run` call already uses (Part XX
        — no second research engine). Part XI: a real failure here is
        captured as real evidence and logged, never silently swallowed
        and never recorded as a fabricated success; `asyncio.create_task()`
        already isolates this coroutine's own exceptions from
        app/sim.py's run_sim_loop(), so this method's own try/except
        exists only to turn that isolation into real, inspectable
        outcome telemetry (`GameState._research_orchestrator_last_outcome`)
        instead of a bare, unretrieved-task-exception log line."""
        logger = logging.getLogger("tradetown.research_orchestrator")
        try:
            _state, run_record = await self.submit_research_factory_run(seed.hypothesis, seed.definition)
            self._research_orchestrator_last_outcome = ResearchOrchestratorOutcome(
                triggered_at=_now_iso(), strategy_family=seed.strategy_family, succeeded=True, factory_run_id=run_record.id, detail=None
            )
        except Exception as exc:
            logger.exception("Autonomous research orchestrator: factory cycle for %r failed", seed.strategy_family)
            self._research_orchestrator_last_outcome = ResearchOrchestratorOutcome(
                triggered_at=_now_iso(), strategy_family=seed.strategy_family, succeeded=False, factory_run_id=None, detail=str(exc)
            )

    async def describe_research_orchestrator_status(self) -> ResearchOrchestratorStatus:
        """Read-only — computes the SAME real decision
        `maybe_orchestrate_research()` would make right now, without
        triggering anything, plus the live process's own in-memory
        outcome telemetry. See `ResearchOrchestratorStatus`'s own
        docstring (app/schemas.py) for exactly which fields are
        state-derived vs. in-memory-only."""
        async with self.lock:
            state_snapshot = self.data
        factory_currently_running = self._research_orchestrator_task is not None and not self._research_orchestrator_task.done()
        decision = decide_research_orchestration(
            state_snapshot,
            factory_currently_running=factory_currently_running,
            last_orchestrator_attempt_sim_day=self._research_orchestrator_last_attempt_sim_day,
        )
        next_eligible_sim_day = None if decision.last_factory_run_sim_day is None else decision.last_factory_run_sim_day + decision.research_cadence_sim_days
        outcome = self._research_orchestrator_last_outcome
        return ResearchOrchestratorStatus(
            evaluatedAt=_now_iso(),
            simDay=decision.sim_day,
            researchCadenceSimDays=decision.research_cadence_sim_days,
            lastFactoryRunSimDay=decision.last_factory_run_sim_day,
            nextEligibleSimDay=next_eligible_sim_day,
            factoryCurrentlyRunning=factory_currently_running,
            wouldRunNow=decision.should_run,
            reason=decision.reason,
            seedStrategyFamily=decision.seed.strategy_family if decision.seed is not None else None,
            lastOutcomeTriggeredAt=outcome.triggered_at if outcome is not None else None,
            lastOutcomeStrategyFamily=outcome.strategy_family if outcome is not None else None,
            lastOutcomeSucceeded=outcome.succeeded if outcome is not None else None,
            lastOutcomeFactoryRunId=outcome.factory_run_id if outcome is not None else None,
            lastOutcomeDetail=outcome.detail if outcome is not None else None,
        )

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
