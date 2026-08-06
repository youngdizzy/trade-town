from __future__ import annotations

import json
from typing import Any

from fastapi import WebSocket

from app.schemas import GameSaveState


def build_state_message(state: GameSaveState) -> dict[str, Any]:
    """Shared WS payload shape used both for the initial snapshot on connect and every sim tick."""
    return {
        "type": "state",
        "time": state.time.model_dump(by_alias=True),
        "agents": {aid: agent.model_dump(by_alias=True) for aid, agent in state.agents.items()},
        "tasks": [t.model_dump(by_alias=True) for t in state.tasks[-20:]],
        "whiteboards": state.whiteboards,
        "meeting": state.meeting.model_dump(by_alias=True),
        # state.news is already bounded per-category by nexus._trim_news()
        # (see MAX_NEWS_PER_CATEGORY) — re-slicing to a flat "last 10" here
        # would undo that balance, since discovery news fires far more
        # often than market/company news and would crowd the rarer
        # categories back out of the window. Send the whole (already
        # small) list instead.
        "news": [n.model_dump(by_alias=True) for n in state.news],
        "research": [r.model_dump(by_alias=True) for r in state.research],
        "watchlist": [w.model_dump(by_alias=True) for w in state.watchlist],
        # Already capped at MAX_MEMORY_RECORDS / MAX_MEETING_MINUTES in
        # nexus.py — same reasoning as `news` above, send as-is.
        "memory": [m.model_dump(by_alias=True) for m in state.memory],
        "meetingMinutes": [m.model_dump(by_alias=True) for m in state.meeting_minutes],
        # v0.5 — already capped in their respective managers (portfolio.py's
        # MAX_TRADE_HISTORY, simulation.py's MAX_SIMULATION_RESULTS, etc.),
        # send as-is like the other pre-bounded lists above.
        "paperPortfolio": state.paper_portfolio.model_dump(by_alias=True),
        "strategies": [s.model_dump(by_alias=True) for s in state.strategies],
        "backtestSessions": [b.model_dump(by_alias=True) for b in state.backtest_sessions],
        "simulationResults": [r.model_dump(by_alias=True) for r in state.simulation_results],
        "strategyReports": [r.model_dump(by_alias=True) for r in state.strategy_reports],
        "strategyReviews": [r.model_dump(by_alias=True) for r in state.strategy_reviews],
        # v0.7 Feature 52 (Part 1) — Strategy Validation Laboratory.
        # Already capped in strategy_lab.py's own cap_* helpers, send as-is
        # like the other pre-bounded lists above.
        "strategyMonteCarloResults": [r.model_dump(by_alias=True) for r in state.strategy_monte_carlo_results],
        "strategyRegimeTests": [r.model_dump(by_alias=True) for r in state.strategy_regime_tests],
        "strategyLiquidityValidations": [r.model_dump(by_alias=True) for r in state.strategy_liquidity_validations],
        "strategyExecutiveReviews": [r.model_dump(by_alias=True) for r in state.strategy_executive_reviews],
        "strategyFounderApprovals": [r.model_dump(by_alias=True) for r in state.strategy_founder_approvals],
        # v0.7 Feature 52 (Part 2) — Living Strategies. strategyHallOfFame/
        # strategyFailedArchive are permanent, one-per-retirement records;
        # strategyHealthAssessments is already capped like the Part 1
        # lists above.
        "strategyHealthAssessments": [r.model_dump(by_alias=True) for r in state.strategy_health_assessments],
        "strategyHallOfFame": [r.model_dump(by_alias=True) for r in state.strategy_hall_of_fame],
        "strategyFailedArchive": [r.model_dump(by_alias=True) for r in state.strategy_failed_archive],
        "hallOfFame": [h.model_dump(by_alias=True) for h in state.hall_of_fame],
        "coachReports": [c.model_dump(by_alias=True) for c in state.coach_reports],
        "companyScore": state.company_score.model_dump(by_alias=True),
        "performanceSnapshots": [p.model_dump(by_alias=True) for p in state.performance_snapshots],
        # v0.6 — riskLimits is a single live config object (not a log);
        # riskWarnings reflects Guardian's *current* standing watch,
        # refreshed every tick, not an accumulating history — see
        # nexus.py's tick(). scannerAlerts/decisions are already capped/
        # append-only in their own managers, sent as-is like the other
        # pre-bounded lists above.
        "riskLimits": state.risk_limits.model_dump(by_alias=True),
        "riskWarnings": [w.model_dump(by_alias=True) for w in state.risk_warnings],
        # Design Bible Chapter 67 (TTOS) Part 3.
        "emergencyStop": state.emergency_stop.model_dump(by_alias=True),
        "scannerAlerts": [a.model_dump(by_alias=True) for a in state.scanner_alerts],
        "decisions": [d.model_dump(by_alias=True) for d in state.decisions],
        "agentEnergy": state.agent_energy.model_dump(by_alias=True),
        # Progress only (unlockedLevel/attempts/counts) — the pending
        # SignalChallenge itself is transient and never broadcast (see
        # signal_calibration.py's module docstring).
        "signalCalibration": state.signal_calibration.model_dump(by_alias=True),
        # Progress only — the pending PlayerVsAiPrompt itself is transient
        # and never broadcast (see player_vs_ai.py's module docstring).
        "playerVsAi": state.player_vs_ai.model_dump(by_alias=True),
        # Progress only — the static lesson curriculum itself is never
        # broadcast, fetched once via GET /api/education/lessons instead
        # (see education.py's module docstring).
        "education": state.education.model_dump(by_alias=True),
        "viewedTradeNotificationIds": state.viewed_trade_notification_ids,
        # v0.6.3 Feature 12 — tradeProposals are the small, capped
        # (MAX_PENDING_PROPOSALS) pending queue; ceoDecisions is already
        # capped (MAX_CEO_DECISIONS) like decisions above, sent as-is.
        "tradeProposals": [p.model_dump(by_alias=True) for p in state.trade_proposals],
        "ceoDecisions": [c.model_dump(by_alias=True) for c in state.ceo_decisions],
        # v0.7 Feature 17 — already capped (MAX_DEBATES) like ceoDecisions above.
        "debates": [d.model_dump(by_alias=True) for d in state.debates],
        # v0.7 Feature 20 — already capped (MAX_GATEKEEPER_REJECTIONS) like debates above.
        "gatekeeperRejections": [r.model_dump(by_alias=True) for r in state.gatekeeper_rejections],
        # v0.7 Chapter 58 — already capped (MAX_OPPORTUNITY_REJECTIONS) like gatekeeperRejections above.
        "opportunityRejections": [r.model_dump(by_alias=True) for r in state.opportunity_rejections],
        # v0.7 Feature 22 — a single live reading (not a log); its own
        # timeline is already capped (MAX_MARKET_ENVIRONMENT_HISTORY).
        "marketEnvironment": state.market_environment.model_dump(by_alias=True),
        # v0.7 Feature 51 — a single live reading (not a log), recomputed
        # every tick like marketEnvironment above. marketIntelligenceReports/
        # marketIntelligenceLearning are the permanent, capped daily
        # histories (MAX_MARKET_INTELLIGENCE_REPORTS/_LEARNING).
        "marketIntelligence": state.market_intelligence.model_dump(by_alias=True),
        "marketIntelligenceReports": [r.model_dump(by_alias=True) for r in state.market_intelligence_reports],
        "marketIntelligenceLearning": [e.model_dump(by_alias=True) for e in state.market_intelligence_learning],
        # v0.7 Feature 23 — recomputed every tick like companyScore above.
        "companyHealth": state.company_health.model_dump(by_alias=True),
        "companyDna": state.company_dna.model_dump(by_alias=True),
        "dailyObjectiveStatus": state.daily_objective_status.model_dump(by_alias=True),
        # v0.7 Feature 24 — already capped (MAX_EXECUTIVE_REVIEWS) like coachReports above.
        "executiveReviews": [r.model_dump(by_alias=True) for r in state.executive_reviews],
        # v0.7 Feature 25 — academyProjects holds the one active project
        # (small); academyCompletedProjects is already capped
        # (MAX_ACADEMY_LIBRARY), the permanent Knowledge Library.
        "academyProjects": [p.model_dump(by_alias=True) for p in state.academy_projects],
        "academyCompletedProjects": [p.model_dump(by_alias=True) for p in state.academy_completed_projects],
        # Design Bible Chapter 64 — CEO-authored company goals
        # (app/goals.py), recomputed every tick alongside companyHealth/
        # companyScore above.
        "goals": [g.model_dump(by_alias=True) for g in state.goals],
        "strategicReviews": [r.model_dump(by_alias=True) for r in state.strategic_reviews],
        "agentKnowledge": {aid: k.model_dump(by_alias=True) for aid, k in state.agent_knowledge.items()},
        "academyState": state.academy_state.model_dump(by_alias=True),
        "disciplineReviews": [r.model_dump(by_alias=True) for r in state.discipline_reviews],
        "caseStudies": [c.model_dump(by_alias=True) for c in state.case_studies],
        "decisionVault": [v.model_dump(by_alias=True) for v in state.decision_vault],
        # v0.7 Feature 55 — already capped (MAX_WAR_ROOM_SESSIONS) like decisionVault above.
        "warRoomSessions": [w.model_dump(by_alias=True) for w in state.war_room_sessions],
        # v0.7 Feature 56 — recomputed every tick like companyHealth above.
        "portfolioIntelligence": state.portfolio_intelligence.model_dump(by_alias=True),
        # Design Bible Chapter 71 — recomputed every tick like
        # portfolioIntelligence above; economicIntelligenceReports is the
        # permanent, capped daily history (MAX_ECONOMIC_INTELLIGENCE_REPORTS).
        "economicIntelligence": state.economic_intelligence.model_dump(by_alias=True),
        "economicIntelligenceReports": [r.model_dump(by_alias=True) for r in state.economic_intelligence_reports],
        "talent": state.talent.model_dump(by_alias=True),
        "reasoningChallenges": [r.model_dump(by_alias=True) for r in state.reasoning_challenges],
        "reasoningLabState": state.reasoning_lab_state.model_dump(by_alias=True),
        "reflectionSessions": [r.model_dump(by_alias=True) for r in state.reflection_sessions],
        "wisdomState": state.wisdom_state.model_dump(by_alias=True),
        # v0.7 Feature 32 — already capped (MAX_QUESTION_ARCHIVE) like
        # academyCompletedProjects above; thinkingProfiles/mentorState are
        # recomputed every tick like agentKnowledge/academyState above.
        "questionArchive": [q.model_dump(by_alias=True) for q in state.question_archive],
        "thinkingProfiles": {aid: p.model_dump(by_alias=True) for aid, p in state.thinking_profiles.items()},
        "mentorState": state.mentor_state.model_dump(by_alias=True),
        # v0.7 Feature 49 (Phase 3) — the Foundational Mentor Program.
        # Unlike mentorState above, this is real mutated progress, not
        # recomputed each tick — see save_modules.py's comment on why it
        # lives in the `training` module.
        "foundationalMentorState": state.foundational_mentor_state.model_dump(by_alias=True),
        # v0.7 Feature 39 — the Original Founders. log/councilSessions are
        # already capped (MAX_FOUNDER_LOG/MAX_COUNCIL_SESSIONS) like
        # questionArchive above.
        "founderState": state.founder_state.model_dump(by_alias=True),
        "constitution": state.constitution.model_dump(by_alias=True),
        # v0.7 Feature 41 — the Intelligent Devil's Advocate System.
        # challengeReports is already capped (MAX_CHALLENGE_REPORTS) like
        # questionArchive above; innovationState is recomputed every tick
        # like agentKnowledge/academyState above.
        "challengeReports": [r.model_dump(by_alias=True) for r in state.challenge_reports],
        "innovationState": {aid: s.model_dump(by_alias=True) for aid, s in state.innovation_state.items()},
        # v0.7 Feature 33 — already capped (MAX_TREASURY_TRANSACTIONS/
        # MAX_TREASURY_MONTHLY_REPORTS) like questionArchive above.
        "treasury": state.treasury.model_dump(by_alias=True),
        # Design Bible Chapter 69 Part 1 — Multi-Account & Fund Management.
        # BUG FIX: these two fields existed on GameSaveState and were
        # already consumed by the frontend's WS message type/NexusManager
        # (see frontend/src/net/socket.ts, applyServerUpdate) but were
        # never actually included in this broadcast payload — every tick
        # silently overwrote the client's real `accounts` with
        # `undefined`, crashing TreasuryPanel's AccountsSection
        # (`accounts.length` on undefined) the moment any tick landed
        # after the initial GET /api/load. REST responses from the
        # account endpoints (create/allocate/deallocate/close/switch)
        # always returned the real list, which is why the panel could
        # briefly look correct immediately after an action, only to go
        # blank again on the very next tick.
        "accounts": [a.model_dump(by_alias=True) for a in state.accounts],
        "activeAccountId": state.active_account_id,
        "calendar": state.calendar.model_dump(by_alias=True),
        # v0.7 — the Advanced Quantitative Research Division. archive/reviews
        # are already capped (MAX_ARCHIVE/MAX_REVIEWS) like questionArchive above.
        "blackBox": state.black_box.model_dump(by_alias=True),
        # v0.7 Feature 50 (Part 2/3) — already capped (MAX_MEETING_LOG_ENTRIES/
        # MAX_SELF_EVAL_HISTORY) like questionArchive above.
        "executiveMeetingLog": [e.model_dump(by_alias=True) for e in state.executive_meeting_log],
        "departmentSelfEvaluations": [e.model_dump(by_alias=True) for e in state.department_self_evaluations],
    }


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self._connections.discard(websocket)

    async def broadcast(self, message: dict[str, Any]) -> None:
        if not self._connections:
            return
        payload = json.dumps(message)
        dead: list[WebSocket] = []
        for connection in self._connections:
            try:
                await connection.send_text(payload)
            except Exception:
                dead.append(connection)
        for connection in dead:
            self.disconnect(connection)

    @property
    def active_count(self) -> int:
        return len(self._connections)


ws_manager = ConnectionManager()
