"""Covers app/agent_trading_status.py — CEO directive "Command Center +
Professional Quant Trading Firm Upgrade," Phase 2 (AI Desk / Agent
Decision Explainability). Every status must be grounded in a real,
already-existing signal — never a fabricated narrative or "next
condition" prediction this codebase has no real mechanism to compute.
"""
from __future__ import annotations

from app.agent_trading_status import compute_agent_trading_status
from app.schemas import AnalystVote, EmergencyStopState, ResearchItem, TradeProposal


def _vote(*, agent_id: str = "sentinel", choice: str = "buy", reasoning: str = "Within limits.") -> AnalystVote:
    return AnalystVote(role="risk", agentId=agent_id, choice=choice, reasoning=reasoning, evidence=["real evidence"])  # type: ignore[arg-type]


def _proposal(*, proposal_id: str = "proposal-1", symbol: str = "NEXA", votes: list[AnalystVote]) -> TradeProposal:
    return TradeProposal.model_construct(id=proposal_id, symbol=symbol, analyst_votes=votes)  # type: ignore[call-arg]


def _research_item(*, agent_id: str = "scout", status: str = "in_progress", symbol: str | None = "NEXA") -> ResearchItem:
    return ResearchItem.model_construct(  # type: ignore[call-arg]
        id="research-1", title="Real research", symbol=symbol, category="stock", priority="normal",
        status=status, assigned_agent=agent_id, summary="Real research summary.", confidence=70.0,
    )


class TestComputeAgentTradingStatus:
    def test_emergency_stop_overrides_everything_for_every_agent(self) -> None:
        proposal = _proposal(votes=[_vote(agent_id="sentinel")])
        read = compute_agent_trading_status(
            "sentinel", trade_proposals=[proposal], research=[], emergency_stop=EmergencyStopState(active=True)
        )
        assert read.status == "risk_blocked"
        assert read.agent_id == "sentinel"

    def test_a_real_live_vote_on_a_pending_proposal_reads_waiting(self) -> None:
        vote = _vote(agent_id="sentinel", choice="buy", reasoning="Real risk reasoning text.")
        proposal = _proposal(symbol="NEXA", votes=[vote])
        read = compute_agent_trading_status(
            "sentinel", trade_proposals=[proposal], research=[], emergency_stop=EmergencyStopState()
        )
        assert read.status == "waiting"
        assert read.symbol == "NEXA"
        assert read.proposal_id == "proposal-1"
        assert read.detail == "Real risk reasoning text."

    def test_only_the_matching_agents_own_vote_is_ever_cited(self) -> None:
        proposal = _proposal(votes=[_vote(agent_id="sentinel", reasoning="Sentinel's real reasoning.")])
        read = compute_agent_trading_status(
            "pulse", trade_proposals=[proposal], research=[], emergency_stop=EmergencyStopState()
        )
        assert read.status != "waiting"

    def test_a_researcher_with_active_research_reads_scanning(self) -> None:
        item = _research_item(agent_id="scout", status="in_progress", symbol="ZEN")
        read = compute_agent_trading_status(
            "scout", trade_proposals=[], research=[item], emergency_stop=EmergencyStopState()
        )
        assert read.status == "scanning"
        assert read.symbol == "ZEN"
        assert read.research_category == "stock"

    def test_a_queued_research_item_also_reads_scanning(self) -> None:
        item = _research_item(agent_id="atlas", status="queued")
        read = compute_agent_trading_status(
            "atlas", trade_proposals=[], research=[item], emergency_stop=EmergencyStopState()
        )
        assert read.status == "scanning"

    def test_a_researcher_with_no_real_assignment_reads_idle_never_fabricated(self) -> None:
        read = compute_agent_trading_status(
            "nova", trade_proposals=[], research=[], emergency_stop=EmergencyStopState()
        )
        assert read.status == "idle"

    def test_research_assigned_to_a_different_agent_is_never_attributed(self) -> None:
        item = _research_item(agent_id="scout")
        read = compute_agent_trading_status(
            "atlas", trade_proposals=[], research=[item], emergency_stop=EmergencyStopState()
        )
        assert read.status != "scanning"

    def test_sentinel_with_no_pending_proposal_reads_idle_not_not_trading_role(self) -> None:
        read = compute_agent_trading_status(
            "sentinel", trade_proposals=[], research=[], emergency_stop=EmergencyStopState()
        )
        assert read.status == "idle"

    def test_pulse_with_no_pending_proposal_reads_idle(self) -> None:
        read = compute_agent_trading_status(
            "pulse", trade_proposals=[], research=[], emergency_stop=EmergencyStopState()
        )
        assert read.status == "idle"

    def test_a_structurally_non_trading_agent_reads_not_trading_role_honestly(self) -> None:
        for agent_id in ("guardian", "keystone", "cio", "coach", "sage", "compass", "scribe", "quant", "forge"):
            read = compute_agent_trading_status(
                agent_id, trade_proposals=[], research=[], emergency_stop=EmergencyStopState()  # type: ignore[arg-type]
            )
            assert read.status == "not_trading_role", agent_id

    def test_every_real_agent_produces_a_read_with_no_crash(self) -> None:
        from app.schemas import AGENT_IDS

        for agent_id in AGENT_IDS:
            read = compute_agent_trading_status(
                agent_id, trade_proposals=[], research=[], emergency_stop=EmergencyStopState()
            )
            assert read.agent_id == agent_id
            assert read.headline
            assert read.detail

    def test_session_is_always_a_real_computed_read(self) -> None:
        read = compute_agent_trading_status(
            "scribe", trade_proposals=[], research=[], emergency_stop=EmergencyStopState()
        )
        assert read.session.current
        assert read.session.detail
