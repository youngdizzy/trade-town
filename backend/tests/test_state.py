"""Covers GameState.apply_client_save() — v0.7 Save Architecture Redesign.
Pins the exact contract this whole redesign depends on: only
player/settings/dialogue_history are ever taken from a client save
request, and MAX_DIALOGUE_HISTORY still truncates server-side regardless
of what a (possibly stale, un-updated) client sends. Each test builds its
own GameState() rather than importing the process-wide app.state.game_state
singleton, so runs stay isolated (same convention as test_time_advance.py).
"""
from __future__ import annotations

import asyncio

from app.schemas import AnalystVote, ClientSaveRequest, DecisionConfidence, DialogueHistoryEntry, EntityTransform, SettingsState, SimulationResult, Strategy, StrategyReport, TierAllocationLimits, TradeProposal
from app.strategy_lab import MIN_RETIREMENT_TRADE_COUNT
from app.strategy_registry import _ema_pullback_source_text
from app.state import MAX_DIALOGUE_HISTORY, GameState


def _pending_proposal() -> TradeProposal:
    return TradeProposal(
        id="proposal-1",
        symbol="NEXA",
        category="stock",
        quantity=1.0,
        price=100.0,
        confidence=96.0,
        analystVotes=[AnalystVote(role="risk", agentId="sentinel", choice="buy", reasoning="Position sized within limits.", evidence=["Real risk read"])],  # type: ignore[arg-type]
        overallRecommendation="buy",
        researchSummary="Nova's research backs this setup with a completed research item.",
        riskSummary="Within all configured risk limits.",
        confidenceEngine=DecisionConfidence(score=96.0, tier="elite", summary="A well-supported setup.", factors=[]),  # type: ignore[arg-type]
        createdAt="2026-01-01T00:00:00+00:00",
        createdSimMinutes=0,
    )


def _client_request(*, x: float = 999.0, dialogue_lines: int = 0) -> ClientSaveRequest:
    return ClientSaveRequest(
        player=EntityTransform(scene="BrainRoomScene", x=x, y=42.0, facing="up"),
        settings=SettingsState(
            musicVolume=0.1,
            sfxVolume=0.2,
            autosaveIntervalSec=30,
            showFps=True,
            operatingMode="executive",
            companyPriority="research",
            workMode="rest",
        ),
        dialogueHistory=[
            DialogueHistoryEntry(id=f"line-{i}", speaker="sage", line=f"line {i}", timestamp="2026-01-01T00:00:00+00:00") for i in range(dialogue_lines)
        ],
    )


class TestApplyClientSave:
    def test_player_settings_and_dialogue_history_come_from_the_client(self) -> None:
        state = GameState()
        saved = asyncio.run(state.apply_client_save(_client_request(x=123.0, dialogue_lines=2)))
        assert saved.player.x == 123.0
        assert saved.player.scene == "BrainRoomScene"
        assert saved.settings.operating_mode == "executive"
        assert saved.settings.work_mode == "rest"
        assert len(saved.dialogue_history) == 2

    def test_everything_else_stays_server_authoritative_and_untouched_by_the_request(self) -> None:
        state = GameState()
        before = state.data
        saved = asyncio.run(state.apply_client_save(_client_request()))
        # ClientSaveRequest structurally cannot carry agents/research/decisions/
        # etc. at all — this asserts the real server-authoritative data (whatever
        # GameState started with) survives the call completely unchanged.
        assert saved.agents == before.agents
        assert saved.research == before.research
        assert saved.trade_proposals == before.trade_proposals
        assert saved.time == before.time

    def test_dialogue_history_is_truncated_to_the_same_server_side_cap(self) -> None:
        state = GameState()
        saved = asyncio.run(state.apply_client_save(_client_request(dialogue_lines=MAX_DIALOGUE_HISTORY + 25)))
        assert len(saved.dialogue_history) == MAX_DIALOGUE_HISTORY
        # The most RECENT lines survive, not the oldest — a save should never
        # silently drop what the player just said in favor of ancient history.
        assert saved.dialogue_history[-1].line == f"line {MAX_DIALOGUE_HISTORY + 25 - 1}"

    def test_updated_at_advances_on_every_call(self) -> None:
        state = GameState()
        before = state.data.updated_at
        saved = asyncio.run(state.apply_client_save(_client_request()))
        assert saved.updated_at != before


# v0.7 Feature 49 — Daily Trading Objectives. The first real CEO write
# path for RiskLimits.
class TestUpdateRiskLimits:
    def test_updates_only_the_provided_fields(self) -> None:
        state = GameState()
        before = state.data.risk_limits
        saved, error = asyncio.run(state.update_risk_limits(daily_profit_target_pct=5.0))
        assert error is None
        assert saved.risk_limits.daily_profit_target_pct == 5.0
        assert saved.risk_limits.max_daily_loss_pct == before.max_daily_loss_pct
        assert saved.risk_limits.max_trades_per_day == before.max_trades_per_day

    def test_updates_weekly_and_monthly_loss_limits(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(max_weekly_loss_pct=8.0, max_monthly_loss_pct=12.0))
        assert error is None
        assert saved.risk_limits.max_weekly_loss_pct == 8.0
        assert saved.risk_limits.max_monthly_loss_pct == 12.0

    def test_rejects_non_positive_weekly_loss_limit(self) -> None:
        state = GameState()
        before = state.data.risk_limits
        saved, error = asyncio.run(state.update_risk_limits(max_weekly_loss_pct=0.0))
        assert error is not None
        assert saved.risk_limits.max_weekly_loss_pct == before.max_weekly_loss_pct

    def test_rejects_non_positive_monthly_loss_limit(self) -> None:
        state = GameState()
        before = state.data.risk_limits
        saved, error = asyncio.run(state.update_risk_limits(max_monthly_loss_pct=0.0))
        assert error is not None
        assert saved.risk_limits.max_monthly_loss_pct == before.max_monthly_loss_pct

    def test_updates_all_five_fields_at_once(self) -> None:
        state = GameState()
        saved, error = asyncio.run(
            state.update_risk_limits(daily_profit_target_pct=4.0, max_daily_loss_pct=6.0, max_trades_per_day=3, risk_per_trade_pct=1.5, max_open_positions=5)
        )
        assert error is None
        assert saved.risk_limits.daily_profit_target_pct == 4.0
        assert saved.risk_limits.max_daily_loss_pct == 6.0
        assert saved.risk_limits.max_trades_per_day == 3
        assert saved.risk_limits.risk_per_trade_pct == 1.5
        assert saved.risk_limits.max_open_positions == 5

    def test_rejects_a_non_positive_value(self) -> None:
        state = GameState()
        before = state.data.risk_limits
        saved, error = asyncio.run(state.update_risk_limits(max_trades_per_day=0))
        assert error is not None
        assert saved.risk_limits == before

    def test_rejects_a_call_with_no_fields(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits())
        assert error == "No risk limit changes were provided."
        assert saved is state.data

    # v0.7 Chapter 57 — four of the engine's six new CEO controls.
    def test_updates_max_weekly_deployment_pct(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(max_weekly_deployment_pct=25.0))
        assert error is None
        assert saved.risk_limits.max_weekly_deployment_pct == 25.0

    def test_rejects_non_positive_max_weekly_deployment_pct(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(max_weekly_deployment_pct=0.0))
        assert error is not None
        assert saved.risk_limits.max_weekly_deployment_pct != 0.0

    def test_sets_portfolio_heat_cap_pct(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(portfolio_heat_cap_pct=40.0))
        assert error is None
        assert saved.risk_limits.portfolio_heat_cap_pct == 40.0

    def test_clear_portfolio_heat_cap_flag_disables_it(self) -> None:
        state = GameState()
        saved, _ = asyncio.run(state.update_risk_limits(portfolio_heat_cap_pct=40.0))
        assert saved.risk_limits.portfolio_heat_cap_pct == 40.0
        saved, error = asyncio.run(state.update_risk_limits(clear_portfolio_heat_cap=True))
        assert error is None
        assert saved.risk_limits.portfolio_heat_cap_pct is None

    def test_clear_flag_wins_even_if_a_value_is_also_provided(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(portfolio_heat_cap_pct=40.0, clear_portfolio_heat_cap=True))
        assert error is None
        assert saved.risk_limits.portfolio_heat_cap_pct is None

    def test_rejects_non_positive_portfolio_heat_cap_pct(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(portfolio_heat_cap_pct=0.0))
        assert error is not None
        assert saved.risk_limits.portfolio_heat_cap_pct is None

    def test_updates_cash_reserve_pct(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(cash_reserve_pct=15.0))
        assert error is None
        assert saved.risk_limits.cash_reserve_pct == 15.0

    def test_rejects_cash_reserve_pct_of_100_or_more(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(cash_reserve_pct=100.0))
        assert error is not None
        assert saved.risk_limits.cash_reserve_pct != 100.0

    def test_accepts_cash_reserve_pct_of_zero(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(cash_reserve_pct=0.0))
        assert error is None
        assert saved.risk_limits.cash_reserve_pct == 0.0

    def test_updates_tier_allocation(self) -> None:
        state = GameState()
        new_allocation = TierAllocationLimits(tier1Pct=3.0, tier2Pct=6.0, tier3Pct=9.0, tier4Pct=12.0)
        saved, error = asyncio.run(state.update_risk_limits(tier_allocation=new_allocation))
        assert error is None
        assert saved.risk_limits.tier_allocation == new_allocation

    def test_rejects_tier_allocation_with_a_non_positive_tier(self) -> None:
        state = GameState()
        bad_allocation = TierAllocationLimits(tier1Pct=2.0, tier2Pct=0.0, tier3Pct=8.0, tier4Pct=10.0)
        saved, error = asyncio.run(state.update_risk_limits(tier_allocation=bad_allocation))
        assert error is not None
        assert saved.risk_limits.tier_allocation != bad_allocation

    # v0.7 Chapter 58 — the Opportunity Gatekeeper's two new CEO controls.
    def test_updates_min_trade_quality_score(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(min_trade_quality_score=80.0))
        assert error is None
        assert saved.risk_limits.min_trade_quality_score == 80.0

    def test_rejects_min_trade_quality_score_below_zero(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(min_trade_quality_score=-1.0))
        assert error is not None
        assert saved.risk_limits.min_trade_quality_score != -1.0

    def test_rejects_min_trade_quality_score_above_100(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(min_trade_quality_score=101.0))
        assert error is not None
        assert saved.risk_limits.min_trade_quality_score != 101.0

    def test_accepts_min_trade_quality_score_boundaries(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(min_trade_quality_score=0.0))
        assert error is None
        assert saved.risk_limits.min_trade_quality_score == 0.0
        saved, error = asyncio.run(state.update_risk_limits(min_trade_quality_score=100.0))
        assert error is None
        assert saved.risk_limits.min_trade_quality_score == 100.0

    def test_updates_min_expected_value_pct(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(min_expected_value_pct=0.5))
        assert error is None
        assert saved.risk_limits.min_expected_value_pct == 0.5

    def test_allows_a_negative_min_expected_value_pct_to_relax_the_gate(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(min_expected_value_pct=-1.0))
        assert error is None
        assert saved.risk_limits.min_expected_value_pct == -1.0

    # v0.7 Chapter 59 — the Capital Priority & Opportunity Cost Engine's
    # two new CEO controls.
    def test_updates_min_priority_score(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(min_priority_score=65.0))
        assert error is None
        assert saved.risk_limits.min_priority_score == 65.0

    def test_rejects_min_priority_score_below_zero(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(min_priority_score=-1.0))
        assert error is not None
        assert saved.risk_limits.min_priority_score != -1.0

    def test_rejects_min_priority_score_above_100(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(min_priority_score=101.0))
        assert error is not None
        assert saved.risk_limits.min_priority_score != 101.0

    def test_accepts_min_priority_score_boundaries(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(min_priority_score=0.0))
        assert error is None
        assert saved.risk_limits.min_priority_score == 0.0
        saved, error = asyncio.run(state.update_risk_limits(min_priority_score=100.0))
        assert error is None
        assert saved.risk_limits.min_priority_score == 100.0

    def test_updates_capital_reserve_pct(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(capital_reserve_pct=25.0))
        assert error is None
        assert saved.risk_limits.capital_reserve_pct == 25.0

    def test_rejects_capital_reserve_pct_below_zero(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(capital_reserve_pct=-1.0))
        assert error is not None
        assert saved.risk_limits.capital_reserve_pct != -1.0

    def test_rejects_capital_reserve_pct_at_or_above_100(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(capital_reserve_pct=100.0))
        assert error is not None
        assert saved.risk_limits.capital_reserve_pct != 100.0

    # v0.7 Chapter 61 — the Knowledge Graph & Company Memory Engine's
    # Pattern Detection Sensitivity controls.
    def test_updates_min_similar_matches(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(min_similar_matches=5))
        assert error is None
        assert saved.risk_limits.min_similar_matches == 5

    def test_rejects_min_similar_matches_below_one(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(min_similar_matches=0))
        assert error is not None
        assert saved.risk_limits.min_similar_matches != 0

    def test_updates_mistake_warning_share_pct(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(mistake_warning_share_pct=15.0))
        assert error is None
        assert saved.risk_limits.mistake_warning_share_pct == 15.0

    def test_rejects_mistake_warning_share_pct_at_zero(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(mistake_warning_share_pct=0.0))
        assert error is not None
        assert saved.risk_limits.mistake_warning_share_pct != 0.0

    def test_rejects_mistake_warning_share_pct_above_100(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(mistake_warning_share_pct=101.0))
        assert error is not None
        assert saved.risk_limits.mistake_warning_share_pct != 101.0

    # v0.7 Chapter 61 — the Knowledge Retention Rules CEO control's
    # Decision Vault slice.
    def test_updates_max_decision_vault_entries(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(max_decision_vault_entries=50))
        assert error is None
        assert saved.risk_limits.max_decision_vault_entries == 50

    def test_rejects_max_decision_vault_entries_below_one(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(max_decision_vault_entries=0))
        assert error is not None
        assert saved.risk_limits.max_decision_vault_entries != 0

    def test_updates_max_memory_records(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(max_memory_records=50))
        assert error is None
        assert saved.risk_limits.max_memory_records == 50

    def test_rejects_max_memory_records_below_one(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(max_memory_records=0))
        assert error is not None
        assert saved.risk_limits.max_memory_records != 0

    # v0.7 Design Bible Chapter 62 — the Innovation Lab's Innovation
    # Budget CEO control.
    def test_updates_max_limited_live_capital(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(max_limited_live_capital=5000.0))
        assert error is None
        assert saved.risk_limits.max_limited_live_capital == 5000.0

    def test_rejects_max_limited_live_capital_at_or_below_zero(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(max_limited_live_capital=0.0))
        assert error is not None
        assert saved.risk_limits.max_limited_live_capital != 0.0

    # v0.7 Design Bible Chapter 63 — Company Health tier thresholds.
    def test_updates_a_single_company_health_threshold(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(company_health_excellent_threshold=90.0))
        assert error is None
        assert saved.risk_limits.company_health_excellent_threshold == 90.0
        # Every other threshold is untouched, still real defaults.
        assert saved.risk_limits.company_health_good_threshold == 70.0

    def test_rejects_a_threshold_outside_zero_to_one_hundred(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.update_risk_limits(company_health_stable_threshold=101.0))
        assert error is not None
        assert saved.risk_limits.company_health_stable_threshold != 101.0

    def test_rejects_thresholds_that_would_break_descending_order(self) -> None:
        state = GameState()
        # Raising Needs Attention above the real Stable default (50.0)
        # without also raising Stable would collapse the ordering.
        saved, error = asyncio.run(state.update_risk_limits(company_health_needs_attention_threshold=60.0))
        assert error is not None
        assert saved.risk_limits.company_health_needs_attention_threshold != 60.0

    def test_accepts_a_full_consistent_reordering_in_one_call(self) -> None:
        state = GameState()
        saved, error = asyncio.run(
            state.update_risk_limits(
                company_health_excellent_threshold=95.0,
                company_health_good_threshold=80.0,
                company_health_stable_threshold=60.0,
                company_health_needs_attention_threshold=40.0,
            )
        )
        assert error is None
        assert saved.risk_limits.company_health_excellent_threshold == 95.0
        assert saved.risk_limits.company_health_needs_attention_threshold == 40.0

    def test_extra_fields_on_the_wire_are_ignored_not_rejected(self) -> None:
        """ClientSaveRequest inherits CamelModel's default extra="ignore", so
        an older client still POSTing a full legacy GameSaveState-shaped body
        stays accepted — see docs/API.md's POST /api/save section."""
        payload = ClientSaveRequest.model_validate(
            {
                "player": {"scene": "LobbyScene", "x": 1.0, "y": 2.0, "facing": "down"},
                "settings": SettingsState(
                    musicVolume=0.5,
                    sfxVolume=0.5,
                    autosaveIntervalSec=60,
                    showFps=False,
                ).model_dump(by_alias=True),
                "dialogueHistory": [],
                "agents": {"echo": {"fabricated": "should be ignored, not rejected"}},
                "decisions": ["fabricated", "should be ignored"],
            }
        )
        assert payload.player.scene == "LobbyScene"


class TestCreateGoal:
    """v0.7 Design Bible Chapter 64 — the CEO's Goal creation write path."""

    def test_creates_a_real_active_goal_with_computed_progress(self) -> None:
        state = GameState()
        saved, error = asyncio.run(
            state.create_goal(title="Grow the Company Score", category="growth", target_metric="company_score_overall", target_value=90.0, deadline_sim_day=None)
        )
        assert error is None
        assert len(saved.goals) == 1
        goal = saved.goals[0]
        assert goal.status == "active"
        assert goal.title == "Grow the Company Score"
        assert goal.target_value == 90.0
        # A fresh game's real Company Score is on record — progress is a
        # real computed number, never a placeholder.
        assert goal.current_value == saved.company_score.overall

    def test_rejects_an_empty_title(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.create_goal(title="   ", category="growth", target_metric="company_score_overall", target_value=90.0, deadline_sim_day=None))
        assert error is not None
        assert saved.goals == []

    def test_rejects_a_non_positive_target_value(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.create_goal(title="Bad Goal", category="growth", target_metric="company_score_overall", target_value=0.0, deadline_sim_day=None))
        assert error is not None
        assert saved.goals == []

    def test_rejects_a_deadline_that_is_not_in_the_future(self) -> None:
        state = GameState()
        current_day = state.data.time.day
        saved, error = asyncio.run(state.create_goal(title="Bad Deadline", category="growth", target_metric="company_score_overall", target_value=90.0, deadline_sim_day=current_day))
        assert error is not None
        assert saved.goals == []

    def test_second_goal_gets_a_distinct_id(self) -> None:
        state = GameState()
        asyncio.run(state.create_goal(title="First", category="growth", target_metric="company_score_overall", target_value=90.0, deadline_sim_day=None))
        saved, error = asyncio.run(state.create_goal(title="Second", category="research", target_metric="academy_level", target_value=5.0, deadline_sim_day=None))
        assert error is None
        assert len(saved.goals) == 2
        assert saved.goals[0].id != saved.goals[1].id


class TestCancelGoal:
    def test_cancels_a_real_active_goal(self) -> None:
        state = GameState()
        created, _ = asyncio.run(state.create_goal(title="Cancel Me", category="growth", target_metric="company_score_overall", target_value=90.0, deadline_sim_day=None))
        goal_id = created.goals[0].id
        saved, error = asyncio.run(state.cancel_goal(goal_id))
        assert error is None
        assert saved.goals[0].status == "cancelled"

    def test_rejects_an_unknown_goal_id(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.cancel_goal("no-such-goal"))
        assert error is not None
        assert saved.goals == []

    def test_rejects_cancelling_an_already_cancelled_goal(self) -> None:
        state = GameState()
        created, _ = asyncio.run(state.create_goal(title="Double Cancel", category="growth", target_metric="company_score_overall", target_value=90.0, deadline_sim_day=None))
        goal_id = created.goals[0].id
        asyncio.run(state.cancel_goal(goal_id))
        saved, error = asyncio.run(state.cancel_goal(goal_id))
        assert error is not None
        assert saved.goals[0].status == "cancelled"


class TestRetireStrategy:
    """Design Bible Chapter 62 — retirement now also files a real
    MemoryRecord under the "strategy" category (see app/scribe.py's
    record_strategy_hall_of_fame_entry/record_strategy_failed_archive_entry),
    alongside the pre-existing Company DNA nudge and Hall of
    Fame/Failed Archive filing."""

    def test_a_strategy_with_no_qualifying_history_is_archived_and_remembered(self) -> None:
        # No stage="approved", no simulation results, no founder approval
        # — guaranteed to miss the real Hall of Fame bar and land in the
        # Failed Archive instead (see generate_strategy_retirement_outcome()).
        state = GameState()
        strategy = Strategy(
            id="strategy-1",
            name="Momentum Breakout",
            description="Follows short-term price momentum.",
            createdBy="echo",  # type: ignore[arg-type]
            focusCategory="stock",  # type: ignore[arg-type]
            createdAt="2026-01-01T00:00:00+00:00",
            stage="research",  # type: ignore[arg-type]
            allocatedCapital=0.0,
        )
        state.data = state.data.model_copy(update={"strategies": [strategy]})

        saved, error = asyncio.run(state.retire_strategy("strategy-1", "Not showing promise."))

        assert error is None
        assert len(saved.strategy_failed_archive) == 1
        assert len(saved.strategy_hall_of_fame) == 0
        strategy_memories = [m for m in saved.memory if m.category == "strategy"]
        assert len(strategy_memories) == 1
        assert "Momentum Breakout" in strategy_memories[0].title

    def _strategy(self, *, stage: str = "market_simulation") -> Strategy:
        return Strategy(
            id="strategy-1",
            name="Momentum Breakout",
            description="Follows short-term price momentum.",
            createdBy="echo",  # type: ignore[arg-type]
            focusCategory="stock",  # type: ignore[arg-type]
            createdAt="2026-01-01T00:00:00+00:00",
            stage=stage,  # type: ignore[arg-type]
            allocatedCapital=0.0,
        )

    def _result(self, *, trade_count: int) -> SimulationResult:
        return SimulationResult(
            id="result-1",
            strategyId="strategy-1",
            strategyName="Momentum Breakout",
            symbol="NEXA",
            totalReturnPct=5.0,
            winRate=55.0,
            maxDrawdownPct=8.0,
            sharpeRatio=1.0,
            sortinoRatio=1.0,
            tradeCount=trade_count,
            runBy="quant",  # type: ignore[arg-type]
            completedAt="2026-01-01T00:00:00+00:00",
        )

    def test_statistical_evidence_gate_blocks_retirement_with_too_few_real_trades(self) -> None:
        """Trading Psychology & Discipline, Piece B — a strategy that has
        entered real empirical testing but has thin evidence on file
        must not be retirable on a whim."""
        state = GameState()
        strategy = self._strategy(stage="market_simulation")
        result = self._result(trade_count=MIN_RETIREMENT_TRADE_COUNT - 1)
        state.data = state.data.model_copy(update={"strategies": [strategy], "simulation_results": [result]})

        saved, error = asyncio.run(state.retire_strategy("strategy-1", "One bad run — cutting losses."))

        assert error is not None
        assert "does not invalidate a strategy" in error
        assert saved.strategies[0].stage == "market_simulation"

    def test_statistical_evidence_gate_allows_retirement_with_enough_real_trades(self) -> None:
        state = GameState()
        strategy = self._strategy(stage="market_simulation")
        result = self._result(trade_count=MIN_RETIREMENT_TRADE_COUNT)
        state.data = state.data.model_copy(update={"strategies": [strategy], "simulation_results": [result]})

        saved, error = asyncio.run(state.retire_strategy("strategy-1", "Consistent underperformance across a real sample."))

        assert error is None
        assert saved.strategies[0].stage == "retired"

    def test_statistical_evidence_gate_does_not_apply_to_an_untested_idea(self) -> None:
        state = GameState()
        strategy = self._strategy(stage="idea")
        state.data = state.data.model_copy(update={"strategies": [strategy]})

        saved, error = asyncio.run(state.retire_strategy("strategy-1", "Never worth building."))

        assert error is None
        assert saved.strategies[0].stage == "retired"

    def test_statistical_evidence_gate_still_applies_to_a_live_approved_strategy(self) -> None:
        state = GameState()
        strategy = self._strategy(stage="approved")
        result = self._result(trade_count=1)
        state.data = state.data.model_copy(update={"strategies": [strategy], "simulation_results": [result]})

        saved, error = asyncio.run(state.retire_strategy("strategy-1", "Had one bad day."))

        assert error is not None
        assert saved.strategies[0].stage == "approved"


class TestActivateAndResumeEmergencyStop:
    """Design Bible Chapter 67 (TTOS) Part 3 — the CEO's real Global
    Emergency Stop."""

    def test_activate_sets_active_and_records_a_real_memory_entry(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.activate_emergency_stop())
        assert error is None
        assert saved.emergency_stop.active is True
        assert saved.emergency_stop.activated_at is not None
        emergency_memories = [m for m in saved.memory if m.category == "emergency"]
        assert len(emergency_memories) == 1
        assert "activated" in emergency_memories[0].title.lower()

    def test_activating_twice_is_rejected(self) -> None:
        state = GameState()
        asyncio.run(state.activate_emergency_stop())
        saved, error = asyncio.run(state.activate_emergency_stop())
        assert error is not None
        assert saved.emergency_stop.active is True

    def test_resume_clears_active_and_records_a_real_memory_entry(self) -> None:
        state = GameState()
        asyncio.run(state.activate_emergency_stop())
        saved, error = asyncio.run(state.resume_trading())
        assert error is None
        assert saved.emergency_stop.active is False
        assert saved.emergency_stop.activated_at is None
        emergency_memories = [m for m in saved.memory if m.category == "emergency"]
        assert len(emergency_memories) == 2  # activation + resume

    def test_resuming_when_not_active_is_rejected(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.resume_trading())
        assert error is not None
        assert saved.emergency_stop.active is False


class TestActivateAndLiftTradingRestriction:
    """CEO directive "Layered Kill Switches" — the scoped granularity
    layer below the firm-wide Emergency Stop above (see
    app/trading_restrictions.py's module docstring)."""

    def test_activate_creates_a_real_restriction_and_records_a_real_memory_entry(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.activate_trading_restriction(scope="symbol", target="NEXA", reason="Suspicious pattern."))
        assert error is None
        assert len(saved.trading_restrictions) == 1
        assert saved.trading_restrictions[0].active is True
        assert saved.trading_restrictions[0].target == "NEXA"
        alert_memories = [m for m in saved.memory if m.title == "Trading Restriction activated"]
        assert len(alert_memories) == 1

    def test_activating_a_duplicate_is_rejected(self) -> None:
        state = GameState()
        asyncio.run(state.activate_trading_restriction(scope="symbol", target="NEXA", reason="first"))
        saved, error = asyncio.run(state.activate_trading_restriction(scope="symbol", target="NEXA", reason="second"))
        assert error is not None
        assert len(saved.trading_restrictions) == 1

    def test_lift_clears_active_and_records_a_real_memory_entry(self) -> None:
        state = GameState()
        activated, _ = asyncio.run(state.activate_trading_restriction(scope="category", target="bitcoin", reason="volatility spike"))
        restriction_id = activated.trading_restrictions[0].id
        saved, error = asyncio.run(state.lift_trading_restriction(restriction_id, reason="calmed down"))
        assert error is None
        assert saved.trading_restrictions[0].active is False
        assert saved.trading_restrictions[0].lifted_reason == "calmed down"
        lift_memories = [m for m in saved.memory if m.title == "Trading Restriction lifted"]
        assert len(lift_memories) == 1

    def test_lifting_an_unknown_id_is_rejected(self) -> None:
        state = GameState()
        saved, error = asyncio.run(state.lift_trading_restriction("no-such-id", reason=""))
        assert error is not None
        assert saved.trading_restrictions == []


class TestSubmitCeoDecisionEmergencyStopGuard:
    """Design Bible Chapter 67 (TTOS) Part 3 — Emergency Stop blocks the
    CEO's own manual buy/sell call too, not just automation; declining a
    trade ("wait") is still allowed."""

    def _state_with_pending_proposal(self) -> GameState:
        state = GameState()
        state.data = state.data.model_copy(update={"trade_proposals": [_pending_proposal()]})
        return state

    def test_buy_is_rejected_while_emergency_stop_is_active(self) -> None:
        state = self._state_with_pending_proposal()
        asyncio.run(state.activate_emergency_stop())
        saved, error = asyncio.run(state.submit_ceo_decision("proposal-1", "buy"))
        assert error is not None
        assert "halted" in error.lower()
        # The proposal is untouched — still pending, not resolved.
        assert [p.id for p in saved.trade_proposals] == ["proposal-1"]

    def test_wait_is_still_allowed_while_emergency_stop_is_active(self) -> None:
        state = self._state_with_pending_proposal()
        asyncio.run(state.activate_emergency_stop())
        saved, error = asyncio.run(state.submit_ceo_decision("proposal-1", "wait"))
        assert error is None
        assert saved.trade_proposals == []

    def test_buy_resolves_normally_once_emergency_stop_is_not_active(self) -> None:
        state = self._state_with_pending_proposal()
        saved, error = asyncio.run(state.submit_ceo_decision("proposal-1", "buy"))
        assert error is None
        assert saved.trade_proposals == []


class TestSubmitCeoDecisionStrategyProvenance:
    """CEO directive "Live Trade -> Strategy Provenance" — the one real,
    non-fabricated way this codebase can link a live trade back to a
    Strategy Lab strategy: the CEO's own explicit selection at decision
    time, validated against the real strategy roster."""

    def _state_with_pending_proposal(self) -> GameState:
        state = GameState()
        state.data = state.data.model_copy(update={"trade_proposals": [_pending_proposal()]})
        return state

    def test_a_real_strategy_id_is_stored_on_the_ceo_decision_record(self) -> None:
        state = self._state_with_pending_proposal()
        real_strategy_id = state.data.strategies[0].id
        saved, error = asyncio.run(state.submit_ceo_decision("proposal-1", "buy", strategy_id=real_strategy_id))
        assert error is None
        assert saved.ceo_decisions[-1].strategy_id == real_strategy_id

    def test_an_unknown_strategy_id_is_rejected_with_a_real_error(self) -> None:
        state = self._state_with_pending_proposal()
        saved, error = asyncio.run(state.submit_ceo_decision("proposal-1", "buy", strategy_id="not-a-real-strategy"))
        assert error is not None
        assert "no real strategy lab strategy" in error.lower()
        # Rejected before any mutation — the proposal is still pending.
        assert [p.id for p in saved.trade_proposals] == ["proposal-1"]

    def test_no_strategy_id_leaves_the_field_none(self) -> None:
        state = self._state_with_pending_proposal()
        saved, error = asyncio.run(state.submit_ceo_decision("proposal-1", "buy"))
        assert error is None
        assert saved.ceo_decisions[-1].strategy_id is None

    def test_a_real_strategy_id_is_ignored_on_wait_since_no_trade_exists_to_attribute(self) -> None:
        state = self._state_with_pending_proposal()
        real_strategy_id = state.data.strategies[0].id
        saved, error = asyncio.run(state.submit_ceo_decision("proposal-1", "wait", strategy_id=real_strategy_id))
        assert error is None
        assert saved.ceo_decisions[-1].strategy_id is None

    def test_a_seeded_50_ema_strategy_id_is_a_real_valid_choice(self) -> None:
        state = self._state_with_pending_proposal()
        saved, error = asyncio.run(state.submit_ceo_decision("proposal-1", "buy", strategy_id="50-ema-breakout-pullback-long"))
        assert error is None
        assert saved.ceo_decisions[-1].strategy_id == "50-ema-breakout-pullback-long"

    def test_a_real_strategy_id_is_also_attached_to_the_freshly_opened_live_position(self) -> None:
        # CEO directive "Portfolio Construction, Capital Allocation &
        # Execution Realism" — the live analogue of the CeoDecisionRecord
        # assertion above: PaperPosition.strategy_id makes real,
        # strategy-scoped OPEN exposure possible, not just post-close
        # attribution.
        state = self._state_with_pending_proposal()
        real_strategy_id = state.data.strategies[0].id
        saved, error = asyncio.run(state.submit_ceo_decision("proposal-1", "buy", strategy_id=real_strategy_id))
        assert error is None
        assert len(saved.paper_portfolio.positions) == 1
        assert saved.paper_portfolio.positions[0].strategy_id == real_strategy_id

    def test_no_strategy_id_leaves_the_opened_positions_strategy_id_none(self) -> None:
        state = self._state_with_pending_proposal()
        saved, error = asyncio.run(state.submit_ceo_decision("proposal-1", "buy"))
        assert error is None
        assert len(saved.paper_portfolio.positions) == 1
        assert saved.paper_portfolio.positions[0].strategy_id is None


class TestSubmitCeoDecisionRegimeStrategyWarning:
    """CEO directive "TradeTown — 11/10 Market Intelligence + Quant
    Research Engine" — a real, non-blocking regime-gated strategy
    warning. compute_strategy_match()'s avoided_strategy_ids is real,
    evidence-backed (a StrategyReport whose own bestMarketEnvironment
    says a strategy lost money under today's regime); this only checks
    that selecting such a strategy records the warning and never blocks
    the trade."""

    def _state_with_pending_proposal(self) -> GameState:
        state = GameState()
        state.data = state.data.model_copy(update={"trade_proposals": [_pending_proposal()]})
        return state

    def _avoided_report(self, strategy_id: str) -> StrategyReport:
        # Default fresh-GameState regime is "weak_uptrend" -> keyword
        # "bull" (see app/market_intelligence.py's
        # _REGIME_TO_SCENARIO_KEYWORD) -- "Not yet Bull" both starts
        # with "not yet" and contains "bull", satisfying
        # compute_strategy_match()'s real avoided-strategy condition.
        return StrategyReport(
            id=f"report-{strategy_id}",
            strategyId=strategy_id,  # type: ignore[call-arg]
            strategyName="test strategy",  # type: ignore[call-arg]
            sourceResultId="result-1",  # type: ignore[call-arg]
            scenario="bull",  # type: ignore[arg-type]
            executiveSummary="d",  # type: ignore[call-arg]
            strengths=[],
            weaknesses=[],
            failureConditions=[],  # type: ignore[call-arg]
            bestMarketEnvironment="Not yet Bull — this run lost money under this scenario.",  # type: ignore[call-arg]
            recommendedImprovements=[],  # type: ignore[call-arg]
            simDay=1,  # type: ignore[call-arg]
            createdAt="2026-01-01T00:00:00+00:00",  # type: ignore[call-arg]
        )

    def test_a_strategy_the_company_avoided_under_todays_regime_records_a_real_warning(self) -> None:
        state = self._state_with_pending_proposal()
        real_strategy_id = state.data.strategies[0].id
        state.data = state.data.model_copy(update={"strategy_reports": [self._avoided_report(real_strategy_id)]})
        saved, error = asyncio.run(state.submit_ceo_decision("proposal-1", "buy", strategy_id=real_strategy_id))
        assert error is None
        # Never blocked -- the trade still executed.
        assert len(saved.paper_portfolio.positions) == 1
        assert saved.ceo_decisions[-1].regime_strategy_warning is not None
        assert "bull" in saved.ceo_decisions[-1].regime_strategy_warning.lower()

    def test_a_strategy_with_no_avoided_evidence_leaves_the_warning_none(self) -> None:
        state = self._state_with_pending_proposal()
        real_strategy_id = state.data.strategies[0].id
        saved, error = asyncio.run(state.submit_ceo_decision("proposal-1", "buy", strategy_id=real_strategy_id))
        assert error is None
        assert saved.ceo_decisions[-1].regime_strategy_warning is None

    def test_no_strategy_selected_leaves_the_warning_none_even_with_avoided_evidence_on_file(self) -> None:
        state = self._state_with_pending_proposal()
        real_strategy_id = state.data.strategies[0].id
        state.data = state.data.model_copy(update={"strategy_reports": [self._avoided_report(real_strategy_id)]})
        saved, error = asyncio.run(state.submit_ceo_decision("proposal-1", "buy"))
        assert error is None
        assert saved.ceo_decisions[-1].regime_strategy_warning is None


class TestSubmitCeoDecisionStrategyRuleSnapshot:
    """CEO directive "Complete Trade Provenance," Part 2 — Strategy Rule
    Snapshot. Extends the CeoDecisionRecord.strategy_id mechanism above
    with the exact real, immutable CompiledStrategyDefinition (id +
    version) that was active the instant the CEO picked that strategy —
    read from the real, append-only compiled_strategy_versions history,
    never a new versioning mechanism."""

    def _state_with_pending_proposal(self) -> GameState:
        state = GameState()
        state.data = state.data.model_copy(update={"trade_proposals": [_pending_proposal()]})
        return state

    def test_a_strategy_with_compiled_rules_snapshots_the_current_definition_and_version(self) -> None:
        state = self._state_with_pending_proposal()
        saved, error = asyncio.run(state.submit_ceo_decision("proposal-1", "buy", strategy_id="50-ema-breakout-pullback-long"))
        assert error is None
        record = saved.ceo_decisions[-1]
        assert record.strategy_compiled_definition_id == "50-ema-breakout-pullback-long"
        assert record.strategy_compiled_definition_version == 1

    def test_an_idea_stage_strategy_with_no_compiled_rules_leaves_the_snapshot_none(self) -> None:
        state = self._state_with_pending_proposal()
        idea_stage_strategy_id = state.data.strategies[0].id
        assert state.data.strategies[0].compiled_definition_id is None  # real precondition, not assumed
        saved, error = asyncio.run(state.submit_ceo_decision("proposal-1", "buy", strategy_id=idea_stage_strategy_id))
        assert error is None
        record = saved.ceo_decisions[-1]
        assert record.strategy_compiled_definition_id is None
        assert record.strategy_compiled_definition_version is None

    def test_no_strategy_id_leaves_the_snapshot_none(self) -> None:
        state = self._state_with_pending_proposal()
        saved, error = asyncio.run(state.submit_ceo_decision("proposal-1", "buy"))
        assert error is None
        record = saved.ceo_decisions[-1]
        assert record.strategy_compiled_definition_id is None
        assert record.strategy_compiled_definition_version is None

    def test_wait_ignores_the_snapshot_since_no_trade_exists_to_attribute(self) -> None:
        state = self._state_with_pending_proposal()
        saved, error = asyncio.run(state.submit_ceo_decision("proposal-1", "wait", strategy_id="50-ema-breakout-pullback-long"))
        assert error is None
        record = saved.ceo_decisions[-1]
        assert record.strategy_compiled_definition_id is None
        assert record.strategy_compiled_definition_version is None

    def test_snapshot_captures_the_version_current_at_decision_time_not_a_later_edit(self) -> None:
        # The core Part 2 requirement: "If the strategy later becomes EMA
        # 55, the old trade must still reference the rules that actually
        # generated it." Bump the real strategy to version 2 BEFORE
        # deciding, then bump it again AFTER — the already-recorded
        # decision must keep pointing at version 2, never silently
        # follow the pointer to version 3.
        state = self._state_with_pending_proposal()
        text = _ema_pullback_source_text(direction="long")
        asyncio.run(state.register_compiled_strategy_version(name="50 EMA Breakout Pullback (Long)", source_text=text))
        saved, error = asyncio.run(state.submit_ceo_decision("proposal-1", "buy", strategy_id="50-ema-breakout-pullback-long"))
        assert error is None
        record = saved.ceo_decisions[-1]
        assert record.strategy_compiled_definition_id == "50-ema-breakout-pullback-long"
        assert record.strategy_compiled_definition_version == 2

        # A further edit after the decision must not retroactively move
        # this already-recorded snapshot.
        asyncio.run(state.register_compiled_strategy_version(name="50 EMA Breakout Pullback (Long)", source_text=text))
        assert state.data.ceo_decisions[-1].strategy_compiled_definition_version == 2
        assert len(state.data.compiled_strategy_versions["50-ema-breakout-pullback-long"]) == 3
