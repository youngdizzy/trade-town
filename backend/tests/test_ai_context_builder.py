"""Covers app/ai_context_builder.py — CEO directive "TradeTown — True AI
Agent Reasoning Foundation 1.0," Part IV/V/VI/XXXVIII. Confirms:
(1) every fact item traces to a real TradeProposal/MarketIntelligenceState
field; (2) anti-lookahead: an institutional memory promoted AFTER the
proposal's own `created_sim_minutes` is never included, no matter how
relevant `retrieve_relevant_memory()` would otherwise rank it;
(3) `resolve_deterministic_outcome()`'s four real branches (pending/
inconclusive/supported/contradicted), mirroring (not duplicating)
app/knowledge_sharing.py's own real decision/journal-entry lookup
convention.
"""
from __future__ import annotations

from app.ai_context_builder import CONTEXT_BUILDER_VERSION, KNOWN_LIMITATIONS, build_evidence_packet_for_proposal, resolve_deterministic_outcome
from app.market_intelligence import compute_market_intelligence_state
from app.market_data import market_data_provider
from app.schemas import (
    AnalystVote,
    ConfidenceFactor,
    DecisionConfidence,
    InstitutionalMemoryEntry,
    KnowledgeEvent,
    PaperTradeJournalEntry,
    TradeDecision,
    TradeProposal,
)
from app.watchlist import default_watchlist

_CREATED_AT = "2026-01-01T00:00:00+00:00"


def _market_intelligence():
    return compute_market_intelligence_state(default_watchlist(), [], [], market_data_provider)


def _proposal(*, proposal_id: str = "proposal-1", created_sim_minutes: int = 1440) -> TradeProposal:
    vote = AnalystVote(role="technical", agentId="echo", choice="buy", reasoning="test reasoning", evidence=["real evidence"])
    return TradeProposal(
        id=proposal_id,
        symbol="NEXA",
        category="stock",
        quantity=10.0,
        price=100.0,
        confidence=80.0,
        analystVotes=[vote],
        overallRecommendation="buy",
        researchSummary="test research summary",
        riskSummary="NEXA is within all configured risk limits.",
        confidenceEngine=DecisionConfidence(score=80.0, tier="strong", summary="test", factors=[ConfidenceFactor(name="agreement", score=80.0, weight=1.0, detail="test")]),
        createdAt=_CREATED_AT,
        createdSimMinutes=created_sim_minutes,
    )


def _memory(*, sim_day: int, symbol: str | None = "NEXA", entry_id: str = "im-1") -> InstitutionalMemoryEntry:
    return InstitutionalMemoryEntry(
        id=entry_id,
        source="risk_event",
        createdAt=_CREATED_AT,
        simDay=sim_day,
        eventRef="event-1",
        observation="A real observed event.",
        lesson="A real, actionable lesson.",
        confidence=70.0,
        provenance="test provenance",
        relevancePct=90.0,
        symbol=symbol,
    )


def test_evidence_items_trace_to_real_proposal_fields() -> None:
    proposal = _proposal()
    packet = build_evidence_packet_for_proposal(
        proposal, packet_id="pkt-1", task="Evaluate NEXA", agent_role="researcher",
        market_intelligence=_market_intelligence(), institutional_memory=[], knowledge_events=[],
    )
    assert packet.context_builder_version == CONTEXT_BUILDER_VERSION
    assert packet.known_limitations == KNOWN_LIMITATIONS
    by_id = {item.id: item for item in packet.items}
    assert by_id["fact-symbol"].detail == "NEXA"
    assert by_id["fact-price"].detail == "100.0000"
    assert by_id["fact-desk-recommendation"].detail == "buy"
    assert by_id["fact-vote-technical"].detail == "buy: test reasoning"
    assert all(item.kind == "fact" for item in packet.items)


def test_knowledge_cutoff_matches_proposal_creation() -> None:
    proposal = _proposal(created_sim_minutes=2880)
    packet = build_evidence_packet_for_proposal(
        proposal, packet_id="pkt-1", task="Evaluate NEXA", agent_role="researcher",
        market_intelligence=_market_intelligence(), institutional_memory=[], knowledge_events=[],
    )
    assert packet.knowledge_cutoff_sim_minutes == 2880
    assert all(item.as_of_sim_minutes <= 2880 for item in packet.items)


def test_memory_before_cutoff_is_included() -> None:
    # `created_sim_minutes=60` keeps the proposal on sim day 0, same day as
    # the memory below — retrieve_relevant_memory()'s own recency-decay
    # formula scores a same-day memory at 100% relevance (see
    # app/institutional_memory.py's _compute_relevance_pct()), well above
    # MIN_RELEVANCE_FOR_RETRIEVAL, so this test isolates the cutoff check
    # itself rather than an unrelated relevance-decay threshold.
    proposal = _proposal(created_sim_minutes=60)
    memory = _memory(sim_day=0)  # sim_day 0 -> 0 minutes, before the 60-minute cutoff
    packet = build_evidence_packet_for_proposal(
        proposal, packet_id="pkt-1", task="Evaluate NEXA", agent_role="researcher",
        market_intelligence=_market_intelligence(), institutional_memory=[memory], knowledge_events=[],
    )
    knowledge_items = [item for item in packet.items if item.kind == "knowledge"]
    assert len(knowledge_items) == 1
    assert knowledge_items[0].id == "knowledge-im-1"
    assert knowledge_items[0].as_of_sim_minutes == 0


def test_memory_promoted_after_cutoff_is_never_leaked_in() -> None:
    proposal = _proposal(created_sim_minutes=60)  # sim day 0
    memory = _memory(sim_day=5)  # sim day 5 -> 7200 minutes, AFTER the cutoff
    packet = build_evidence_packet_for_proposal(
        proposal, packet_id="pkt-1", task="Evaluate NEXA", agent_role="researcher",
        market_intelligence=_market_intelligence(), institutional_memory=[memory], knowledge_events=[],
    )
    assert not [item for item in packet.items if item.kind == "knowledge"]


def test_memory_application_summary_is_included_when_graded_events_exist() -> None:
    proposal = _proposal(created_sim_minutes=60)
    memory = _memory(sim_day=0)
    events = [
        KnowledgeEvent(id="ke-1", type="knowledge_applied", lessonId="im-1", agentId="nova", simDay=0, detail="x", createdAt=_CREATED_AT, applicationStatus="evaluated", outcome="supported"),
        KnowledgeEvent(id="ke-2", type="knowledge_applied", lessonId="im-1", agentId="nova", simDay=0, detail="x", createdAt=_CREATED_AT, applicationStatus="evaluated", outcome="contradicted"),
    ]
    packet = build_evidence_packet_for_proposal(
        proposal, packet_id="pkt-1", task="Evaluate NEXA", agent_role="researcher",
        market_intelligence=_market_intelligence(), institutional_memory=[memory], knowledge_events=events,
    )
    knowledge_item = next(item for item in packet.items if item.kind == "knowledge")
    assert "1 supported" in knowledge_item.detail
    assert "1 contradicted" in knowledge_item.detail


def _decision(*, decision_id: str, outcome: str) -> TradeDecision:
    return TradeDecision(
        id=decision_id, symbol="NEXA", outcome=outcome, votes=[], researchSummary="x", technicalSummary="x",  # type: ignore[arg-type]
        fundamentalSummary="x", riskSummary="x", supportingAgents=[], opposingAgents=[], confidence=60.0,
        finalReasoning="x", createdAt=_CREATED_AT,
    )


def _journal_entry(*, proposal_id: str, pnl: float) -> PaperTradeJournalEntry:
    return PaperTradeJournalEntry(
        id=f"journal-{proposal_id}", createdAt=_CREATED_AT, tradeId=f"trade-{proposal_id}", decisionId=f"decision-{proposal_id}",
        proposalId=proposal_id, symbol="NEXA", side="buy", quantity=2.0, entryPrice=100.0, exitPrice=100.0 + pnl,
        pnl=pnl, pnlPct=pnl, maePct=-1.0, mfePct=abs(pnl) + 1.0, durationMinutes=30, openedAt=_CREATED_AT, closedAt=_CREATED_AT,
    )


def test_resolve_deterministic_outcome_pending_with_no_decision() -> None:
    outcome, ref = resolve_deterministic_outcome("proposal-1", decisions=[], paper_trade_journal=[])
    assert outcome == "pending"
    assert ref is None


def test_resolve_deterministic_outcome_inconclusive_for_no_trade_decision() -> None:
    decision = _decision(decision_id="decision-proposal-1", outcome="no_trade")
    outcome, ref = resolve_deterministic_outcome("proposal-1", decisions=[decision], paper_trade_journal=[])
    assert outcome == "inconclusive"
    assert ref == decision.id


def test_resolve_deterministic_outcome_pending_when_trade_decision_has_no_journal_entry_yet() -> None:
    decision = _decision(decision_id="decision-proposal-1", outcome="trade")
    outcome, ref = resolve_deterministic_outcome("proposal-1", decisions=[decision], paper_trade_journal=[])
    assert outcome == "pending"
    assert ref is None


def test_resolve_deterministic_outcome_supported_for_positive_pnl() -> None:
    decision = _decision(decision_id="decision-proposal-1", outcome="trade")
    journal = _journal_entry(proposal_id="proposal-1", pnl=25.0)
    outcome, ref = resolve_deterministic_outcome("proposal-1", decisions=[decision], paper_trade_journal=[journal])
    assert outcome == "supported"
    assert ref == journal.id


def test_resolve_deterministic_outcome_contradicted_for_negative_pnl() -> None:
    decision = _decision(decision_id="decision-proposal-1", outcome="trade")
    journal = _journal_entry(proposal_id="proposal-1", pnl=-10.0)
    outcome, ref = resolve_deterministic_outcome("proposal-1", decisions=[decision], paper_trade_journal=[journal])
    assert outcome == "contradicted"
    assert ref == journal.id


def test_resolve_deterministic_outcome_inconclusive_for_zero_pnl() -> None:
    decision = _decision(decision_id="decision-proposal-1", outcome="trade")
    journal = _journal_entry(proposal_id="proposal-1", pnl=0.0)
    outcome, ref = resolve_deterministic_outcome("proposal-1", decisions=[decision], paper_trade_journal=[journal])
    assert outcome == "inconclusive"
    assert ref == journal.id
