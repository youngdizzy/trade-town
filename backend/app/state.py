"""In-memory authoritative game state, shared across all connected clients.

TradeTown is single-tenant (one company, one save slot) — this is
intentionally a process-wide singleton rather than per-session state.
Agent/task/whiteboard/meeting orchestration itself lives in nexus.py; this
module just owns the lock-guarded snapshot and the game clock.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from app import education, nexus, player_vs_ai, signal_calibration, trade_notifications
from app.academy import compute_academy_state, default_agent_knowledge
from app.reasoning_lab import compute_reasoning_lab_state
from app.academy_research import default_academy_projects
from app.agent_energy import default_agent_energy
from app.company_health import compute_company_health
from app.company_score import compute_company_score
from app.debate import generate_debate
from app.executive import MAX_CEO_DECISIONS, AnalystChoice, resolve_proposal
from app.market_data import market_data_provider
from app.market_environment import default_market_environment
from app.nexus import MAX_DEBATES, MAX_DECISIONS, MAX_GATEKEEPER_REJECTIONS
from app.portfolio import default_portfolio, sim_minutes
from app.research import default_research
from app.scribe import record_ceo_decision
from app.schemas import (
    EducationProgress,
    EntityTransform,
    GameSaveState,
    GatekeeperRejection,
    MeetingState,
    PlayerVsAiPrompt,
    PlayerVsAiState,
    SettingsState,
    SignalCalibrationState,
    SignalChoice,
    TimeState,
)
from app.simulation import default_strategies
from app.watchlist import default_watchlist

MAX_DIALOGUE_HISTORY = 200


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def default_state() -> GameSaveState:
    agents = nexus.default_agents()
    watchlist = default_watchlist()
    signal_calibration_state = SignalCalibrationState()
    education_progress = education.default_education_progress()
    agent_knowledge = default_agent_knowledge()
    return GameSaveState(
        player=EntityTransform(scene="LobbyScene", x=160, y=220, facing="down"),
        agents=agents,
        tasks=[],
        whiteboards={},
        meeting=MeetingState(),
        news=[],
        research=default_research(),
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
        marketEnvironment=default_market_environment(),
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
        ),
        executiveReviews=[],
        academyProjects=default_academy_projects(),
        academyCompletedProjects=[],
        agentKnowledge=agent_knowledge,
        academyState=compute_academy_state(agent_knowledge, 0),
        disciplineReviews=[],
        caseStudies=[],
        reasoningChallenges=[],
        reasoningLabState=compute_reasoning_lab_state(0),
        updatedAt=_now_iso(),
    )


class GameState:
    """Thread-safe (via asyncio.Lock) holder for the single authoritative save."""

    def __init__(self) -> None:
        self.data: GameSaveState = default_state()
        self.lock = asyncio.Lock()

    async def apply_client_save(self, incoming: GameSaveState) -> GameSaveState:
        """Merge a client-submitted save. Player position/settings/dialogue come from
        the client; agents/tasks/whiteboards/meeting/news/time stay server-authoritative
        (NEXUS's tick loop owns them)."""
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
                debate=debate,
                risk_warnings=self.data.risk_warnings,
            )

            memory = list(self.data.memory)
            record_ceo_decision(memory, decision)

            decisions = [*self.data.decisions, decision]
            if len(decisions) > MAX_DECISIONS:
                del decisions[: len(decisions) - MAX_DECISIONS]

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

    async def tick(self, minutes: int) -> GameSaveState:
        """Advance the game clock and run one NEXUS orchestration step. Called by the sim loop."""
        async with self.lock:
            time = self.data.time
            total_minutes = time.hour * 60 + time.minute + minutes
            day = time.day + total_minutes // (24 * 60)
            total_minutes %= 24 * 60
            hour, minute = divmod(total_minutes, 60)
            new_time = TimeState(day=day, hour=hour, minute=minute)

            self.data = nexus.tick(self.data, new_time, minutes)
            return self.data


game_state = GameState()
