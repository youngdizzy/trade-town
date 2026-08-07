"""Covers app/situation_room.py — Design Bible Chapter 73.5, Mobile
Command Center & Remote Operations. Confirmed by direct inspection
before this module was written: eleven of the Executive Situation
Room's thirteen fields already have exactly one real computed source
and are reused verbatim here — these tests check that reuse and the
disclosed severity-band mapping, never a fabricated score. Built off
app/state.py's own default_state() (the same real construction the
live game uses) rather than hand-assembling dozens of nested Pydantic
fixtures, since every field this module reads already has a real
default producer.
"""
from __future__ import annotations

from app.executive import AnalystChoice
from app.schemas import AnalystVote, DecisionConfidence, EmergencyStopState, GameSaveState, RiskWarning, TradeProposal
from app.situation_room import compute_situation_room, rank_priorities
from app.state import default_state


def _situation_room(state: GameSaveState):
    return compute_situation_room(
        company_health=state.company_health,
        portfolio=state.paper_portfolio,
        portfolio_intelligence=state.portfolio_intelligence,
        risk_limits=state.risk_limits,
        daily_circuit_breaker=state.daily_circuit_breaker,
        risk_warnings=state.risk_warnings,
        market_environment=state.market_environment,
        trading_mode_state=state.trading_modes,
        economic_intelligence=state.economic_intelligence,
        black_swan_tier=state.black_swan_intelligence.warning.tier,
        trade_proposals=state.trade_proposals,
        emergency_stop=state.emergency_stop,
        operating_mode=state.settings.operating_mode,
    )


def _proposal(*, symbol: str = "AAPL", created_sim_minutes: int = 1000, votes: list[AnalystVote] | None = None, overall: AnalystChoice = "buy") -> TradeProposal:
    return TradeProposal(
        id=f"proposal-{symbol}-{created_sim_minutes}",
        symbol=symbol,
        category="stock",
        quantity=10.0,
        price=100.0,
        confidence=75.0,
        analystVotes=votes if votes is not None else [],
        overallRecommendation=overall,
        researchSummary="x",
        riskSummary="x",
        confidenceEngine=DecisionConfidence(score=75.0, tier="good", summary="x"),
        createdAt="2026-01-01T00:00:00Z",
        createdSimMinutes=created_sim_minutes,
    )


def _vote(choice: AnalystChoice) -> AnalystVote:
    return AnalystVote(role="technical", agentId="echo", choice=choice, reasoning="x", evidence=[])


class TestReusedFieldsAreNeverRecomputed:
    def test_company_health_reads_the_real_composite_score_verbatim(self) -> None:
        state = default_state()
        room = _situation_room(state)
        assert room.company_health.value == f"{state.company_health.overall:.0f}/100"

    def test_portfolio_health_reads_the_real_heat_tier_verbatim(self) -> None:
        state = default_state()
        room = _situation_room(state)
        assert room.portfolio_health.value == state.portfolio_intelligence.heat.tier.title()

    def test_broker_status_is_always_the_honest_simulated_constant(self) -> None:
        state = default_state()
        room = _situation_room(state)
        assert room.broker_status.value == "SIMULATED"
        assert room.broker_status.band == "good"

    def test_automation_status_reads_the_real_operating_mode(self) -> None:
        state = default_state().model_copy(update={"settings": default_state().settings.model_copy(update={"operating_mode": "assisted"})})
        room = _situation_room(state)
        assert "Assisted" in room.automation_status.value


class TestEmergencyAlerts:
    def test_good_band_with_no_emergency_and_no_critical_warnings(self) -> None:
        state = default_state()
        room = _situation_room(state)
        assert room.emergency_alerts.band == "good"

    def test_critical_band_when_emergency_stop_is_active(self) -> None:
        state = default_state().model_copy(update={"emergency_stop": EmergencyStopState(active=True, activatedAt="2026-01-01T00:00:00Z")})
        room = _situation_room(state)
        assert room.emergency_alerts.band == "critical"
        assert room.automation_status.band == "critical"

    def test_critical_band_when_a_critical_risk_warning_is_on_file(self) -> None:
        warning = RiskWarning(id="w1", symbol="AAPL", severity="critical", message="x", createdAt="2026-01-01T00:00:00Z")
        state = default_state().model_copy(update={"risk_warnings": [warning]})
        room = _situation_room(state)
        assert room.emergency_alerts.band == "critical"

    def test_info_severity_warnings_do_not_trigger_critical(self) -> None:
        warning = RiskWarning(id="w1", symbol="AAPL", severity="info", message="x", createdAt="2026-01-01T00:00:00Z")
        state = default_state().model_copy(update={"risk_warnings": [warning]})
        room = _situation_room(state)
        assert room.emergency_alerts.band == "good"


class TestPendingCeoDecisions:
    def test_counts_the_real_pending_proposal_list_length(self) -> None:
        state = default_state().model_copy(update={"trade_proposals": [_proposal(symbol="AAPL"), _proposal(symbol="MSFT", created_sim_minutes=900)]})
        room = _situation_room(state)
        assert room.pending_ceo_decisions.value == "2"

    def test_zero_pending_is_the_good_band(self) -> None:
        state = default_state().model_copy(update={"trade_proposals": []})
        room = _situation_room(state)
        assert room.pending_ceo_decisions.band == "good"

    def test_many_pending_escalates_the_band(self) -> None:
        proposals = [_proposal(symbol=f"SYM{i}", created_sim_minutes=1000 - i) for i in range(8)]
        state = default_state().model_copy(update={"trade_proposals": proposals})
        room = _situation_room(state)
        assert room.pending_ceo_decisions.band == "critical"


class TestExecutiveConsensus:
    def test_no_pending_proposal_reads_as_good_with_an_honest_label(self) -> None:
        state = default_state().model_copy(update={"trade_proposals": []})
        room = _situation_room(state)
        assert room.executive_consensus.value == "No pending proposal"
        assert room.executive_consensus.band == "good"

    def test_full_agreement_across_votes_reads_one_hundred_percent(self) -> None:
        votes = [_vote("buy"), _vote("buy"), _vote("buy")]
        state = default_state().model_copy(update={"trade_proposals": [_proposal(votes=votes, overall="buy")]})
        room = _situation_room(state)
        assert room.executive_consensus.value == "100% agreement"
        assert room.executive_consensus.band == "good"

    def test_uses_the_most_recently_created_pending_proposal(self) -> None:
        older = _proposal(symbol="OLD", created_sim_minutes=100, votes=[_vote("buy")], overall="buy")
        newer = _proposal(symbol="NEW", created_sim_minutes=999, votes=[_vote("buy"), _vote("sell")], overall="buy")
        state = default_state().model_copy(update={"trade_proposals": [older, newer]})
        room = _situation_room(state)
        assert room.executive_consensus.value == "50% agreement"

    def test_split_votes_lower_the_band(self) -> None:
        votes = [_vote("buy"), _vote("sell"), _vote("sell"), _vote("sell")]
        state = default_state().model_copy(update={"trade_proposals": [_proposal(votes=votes, overall="buy")]})
        room = _situation_room(state)
        assert room.executive_consensus.value == "25% agreement"
        assert room.executive_consensus.band in ("severe", "critical")


class TestPriorityEngine:
    def test_emergency_stop_is_always_critical_and_ranked_first(self) -> None:
        state = default_state().model_copy(update={"emergency_stop": EmergencyStopState(active=True, activatedAt="2026-01-01T00:00:00Z")})
        room = _situation_room(state)
        assert room.priorities[0].source == "emergency_stop"
        assert room.priorities[0].tier == "critical"

    def test_critical_risk_warning_becomes_a_critical_priority(self) -> None:
        warning = RiskWarning(id="w1", symbol="AAPL", severity="critical", message="danger", createdAt="2026-01-01T00:00:00Z")
        state = default_state().model_copy(update={"risk_warnings": [warning]})
        room = _situation_room(state)
        critical_items = [p for p in room.priorities if p.tier == "critical" and p.source == "risk_warning"]
        assert len(critical_items) == 1
        assert critical_items[0].related_id == "w1"

    def test_pending_proposal_is_a_real_priority_item(self) -> None:
        state = default_state().model_copy(update={"trade_proposals": [_proposal(symbol="AAPL")]})
        room = _situation_room(state)
        proposal_items = [p for p in room.priorities if p.source == "pending_decision"]
        assert len(proposal_items) == 1
        assert proposal_items[0].related_id == "proposal-AAPL-1000"

    def test_items_are_sorted_critical_first(self) -> None:
        state = default_state().model_copy(
            update={
                "emergency_stop": EmergencyStopState(active=True, activatedAt="2026-01-01T00:00:00Z"),
                "trade_proposals": [_proposal(symbol="AAPL")],
            }
        )
        room = _situation_room(state)
        tier_rank = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        ranks = [tier_rank[p.tier] for p in room.priorities]
        assert ranks == sorted(ranks)

    def test_no_signals_produces_no_priority_items(self) -> None:
        state = default_state()
        priorities = rank_priorities(
            emergency_stop=state.emergency_stop,
            risk_warnings=[],
            black_swan_tier="green",
            trade_proposals=[],
            daily_circuit_breaker=state.daily_circuit_breaker,
            economic_band="good",
        )
        assert priorities == []
