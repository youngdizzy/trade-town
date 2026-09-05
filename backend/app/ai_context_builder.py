"""CEO directive "TradeTown — True AI Agent Reasoning Foundation 1.0" —
the AI Context Builder (Part IV/V). The one real, pure function set
responsible for selecting VERIFIED TradeTown evidence into a bounded,
structured `AIEvidencePacket` — the ONLY thing a reasoning call is ever
allowed to see. No reasoning call receives raw, uncontrolled access to
`GameSaveState`.

Every item this module produces is one of exactly two kinds (Part IV):

  fact       — a real, already-computed TradeTown number/state, drawn
               straight from a real schema field (a TradeProposal's own
               price/confidence, MarketIntelligenceState's own regime/
               quality/volatility read). Never rounded, hedged, or
               editorialized.
  knowledge  — a real, already-promoted InstitutionalMemoryEntry,
               labeled with its own real status (active/superseded/
               contradicted/stale) and, when real graded
               KnowledgeEvent evidence exists for it, a real supported/
               contradicted summary (app/knowledge_sharing.py's
               grade_knowledge_applications()) — never a bare "this is
               true" claim.

("historical" is reserved in the schema's own literal for a future,
richer case-study-level citation this milestone does not yet populate —
disclosed, not silently dropped.) "inference" is deliberately never
produced here: manufacturing one would be indistinguishable from telling
the model what to conclude, which is exactly what Part IV forbids. The
model itself is the only place an inference may originate (see
app/ai_reasoning.py's AIReasoningResult.assumptions/unknowns).

Anti-lookahead (Part VI): every item's `as_of_sim_minutes` is checked
against the packet's own `knowledge_cutoff_sim_minutes` — an institutional
memory entry promoted AFTER the cutoff is never included, regardless of
how relevant `retrieve_relevant_memory()` would otherwise rank it. This is
enforced structurally in this module, not left to the caller's
discipline, so a future replay of an OLDER proposal can never leak later
evidence into its reconstructed context.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from app.institutional_memory import retrieve_relevant_memory
from app.schemas import (
    AIEvidenceItem,
    AIEvidencePacket,
    AIReasoningRole,
    InstitutionalMemoryEntry,
    KnowledgeEvent,
    MarketIntelligenceState,
    PaperTradeJournalEntry,
    TradeDecision,
    TradeProposal,
)

CONTEXT_BUILDER_VERSION = "ai-context-builder-1.0"

# Part IV/VI — real, fixed, disclosed limitations of what this packet can
# honestly represent. Never fabricated per-call; the same real disclosure
# every packet carries, reusing this codebase's own existing honesty
# boundaries (app/market_data.py's MockMarketDataProvider docstring,
# app/market_intelligence.py's own "named proxies, never invented" rule)
# rather than inventing new language.
KNOWN_LIMITATIONS = [
    "Market data is simulated (MockMarketDataProvider) — not a live feed. Any price/volume/volatility fact below is real TradeTown state, but not real-world market data.",
    "Real-time order-flow, whale positioning, and off-chain intent are not available in this codebase and are never represented here, even as an estimate.",
    "News headlines and sentiment reads are template-generated, regime-conditioned flavor text (app/nexus.py), not live news — never cited as a market fact.",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _memory_application_summary(entry: InstitutionalMemoryEntry, knowledge_events: list[KnowledgeEvent]) -> str | None:
    """Real, disclosed application evidence for this one memory, if any
    real graded `knowledge_applied` events exist for it (see
    app/knowledge_sharing.py's own grading). Returns None — not a forced
    weak answer — when nothing has ever been graded against this memory."""
    graded = [e for e in knowledge_events if e.type == "knowledge_applied" and e.lesson_id == entry.id and e.application_status == "evaluated"]
    if not graded:
        return None
    supported = sum(1 for e in graded if e.outcome == "supported")
    contradicted = sum(1 for e in graded if e.outcome == "contradicted")
    inconclusive = sum(1 for e in graded if e.outcome == "inconclusive")
    parts = []
    if supported:
        parts.append(f"{supported} supported")
    if contradicted:
        parts.append(f"{contradicted} contradicted")
    if inconclusive:
        parts.append(f"{inconclusive} inconclusive")
    return f"Real prior application evidence: {', '.join(parts)}."


def build_evidence_packet_for_proposal(
    proposal: TradeProposal,
    *,
    packet_id: str,
    task: str,
    agent_role: AIReasoningRole,
    market_intelligence: MarketIntelligenceState,
    institutional_memory: list[InstitutionalMemoryEntry],
    knowledge_events: list[KnowledgeEvent],
) -> AIEvidencePacket:
    """The one real evidence packet builder this milestone ships. Built
    once, from the SAME real `TradeProposal`/`MarketIntelligenceState`/
    `institutional_memory`/`knowledge_events` the deterministic pipeline
    already uses for this exact candidate — never a second, parallel
    computation of any of these facts."""
    cutoff = proposal.created_sim_minutes
    items: list[AIEvidenceItem] = [
        AIEvidenceItem(id="fact-symbol", kind="fact", label="Symbol", detail=proposal.symbol, asOfSimMinutes=cutoff),
        AIEvidenceItem(id="fact-price", kind="fact", label="Proposal price", detail=f"{proposal.price:.4f}", asOfSimMinutes=cutoff),
        AIEvidenceItem(id="fact-quantity", kind="fact", label="Proposed quantity", detail=f"{proposal.quantity:.4f}", asOfSimMinutes=cutoff),
        AIEvidenceItem(
            id="fact-desk-confidence", kind="fact", label="Desk confidence (heuristic engine)",
            detail=f"{proposal.confidence_engine.score:.0f}/100 ({proposal.confidence_engine.tier}) — {proposal.confidence_engine.summary}",
            asOfSimMinutes=cutoff,
        ),
        AIEvidenceItem(
            id="fact-desk-recommendation", kind="fact", label="Desk overall recommendation (heuristic)",
            detail=proposal.overall_recommendation, asOfSimMinutes=cutoff,
        ),
        AIEvidenceItem(id="fact-risk-summary", kind="fact", label="Risk summary", detail=proposal.risk_summary, asOfSimMinutes=cutoff),
        AIEvidenceItem(
            id="fact-market-regime", kind="fact", label="Market regime",
            detail=f"{market_intelligence.regime_label} — {market_intelligence.regime_detail}", asOfSimMinutes=cutoff,
        ),
        AIEvidenceItem(
            id="fact-market-quality", kind="fact", label="Market quality",
            detail=f"{market_intelligence.quality.tier} ({market_intelligence.quality.score:.0f}/100, {market_intelligence.quality.confidence_pct:.0f}% confidence)",
            asOfSimMinutes=cutoff,
        ),
    ]
    for vote in proposal.analyst_votes:
        items.append(
            AIEvidenceItem(
                id=f"fact-vote-{vote.role}", kind="fact", label=f"{vote.role.title()} analyst vote",
                detail=f"{vote.choice}: {vote.reasoning}", asOfSimMinutes=cutoff,
            )
        )

    memory = retrieve_relevant_memory(institutional_memory, current_sim_day=cutoff // 1440, symbol=proposal.symbol)
    if memory is not None and memory.sim_day * 1440 <= cutoff:
        application_summary = _memory_application_summary(memory, knowledge_events)
        detail = f"[{memory.status}] {memory.observation}"
        if memory.lesson:
            detail += f" Lesson: {memory.lesson}"
        if application_summary:
            detail += f" {application_summary}"
        items.append(
            AIEvidenceItem(id=f"knowledge-{memory.id}", kind="knowledge", label=f"Institutional memory ({memory.source})", detail=detail, asOfSimMinutes=memory.sim_day * 1440)
        )

    return AIEvidencePacket(
        id=packet_id,
        task=task,
        agentRole=agent_role,
        proposalId=proposal.id,
        symbol=proposal.symbol,
        knowledgeCutoffSimMinutes=cutoff,
        items=items,
        knownLimitations=list(KNOWN_LIMITATIONS),
        contextBuilderVersion=CONTEXT_BUILDER_VERSION,
        createdAt=_now_iso(),
    )


def resolve_deterministic_outcome(
    proposal_id: str, *, decisions: list[TradeDecision], paper_trade_journal: list[PaperTradeJournalEntry]
) -> tuple[Literal["pending", "supported", "contradicted", "inconclusive"], str | None]:
    """CEO directive Part XXXVIII — mirrors the exact same real
    decision/journal-entry lookup convention app/knowledge_sharing.py's
    grade_knowledge_applications() already established for grading a
    `knowledge_applied` event (the same `f"decision-{id}"` id convention,
    the same real P&L-sign read), applied here to an `AIReasoningResult`
    instead — a distinct data shape, so a thin, dedicated function is
    used rather than force-fitting `KnowledgeEvent`'s own shape onto AI
    results. Returns (`outcome`, `outcome_ref`) where outcome is
    "pending" (no real decision yet, or a real order still open) or a
    real graded value."""
    decision = next((d for d in decisions if d.id == f"decision-{proposal_id}"), None)
    if decision is None:
        return "pending", None
    if decision.outcome == "no_trade":
        return "inconclusive", decision.id
    journal_entry = next((j for j in paper_trade_journal if j.proposal_id == proposal_id), None)
    if journal_entry is None:
        return "pending", None
    return ("supported" if journal_entry.pnl > 0 else "contradicted" if journal_entry.pnl < 0 else "inconclusive"), journal_entry.id
