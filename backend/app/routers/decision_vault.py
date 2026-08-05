"""v0.7 (Feature 54 in commit history — see app/decision_vault.py's module
docstring for why the brief's own self-numbering, "Feature 53," collides
with the already-shipped Company Certification work and is not used here).
Read-only endpoints over the Decision Vault, mirroring
routers/sandbox.py's `/certification` convention: `await
game_state.snapshot()`, no lock, computed fresh every call — nothing here
mutates the save.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.decision_vault import compute_knowledge_quality_score, find_similar_vault_entries, compute_trade_report_card, summarize_similarity
from app.schemas import ConfidenceTier, KnowledgeQualityScore, MarketIntelligenceRegime, SimilarTradesSummary, TradeReportCard
from app.state import game_state

router = APIRouter(prefix="/api/decision-vault", tags=["decision-vault"])


@router.get("/report-card", response_model=TradeReportCard)
async def trade_report_card(vault_entry_id: str = Query(..., alias="vaultEntryId")) -> TradeReportCard:
    """The Decision Memory System's Trade Report Card — a pure relabeling
    of one DecisionVaultEntry's already-real fields (see
    compute_trade_report_card()'s own docstring for exactly which fields
    the brief asked for that are honestly excluded, e.g. Execution Grade
    and Psychology Grade)."""
    state = await game_state.snapshot()
    entry = next((e for e in state.decision_vault if e.id == vault_entry_id), None)
    if entry is None:
        raise HTTPException(status_code=404, detail="No Decision Vault entry found with that id.")
    return compute_trade_report_card(entry)


@router.get("/similar", response_model=SimilarTradesSummary)
async def similar_trades(
    symbol: str = Query(...),
    market_regime: MarketIntelligenceRegime = Query(..., alias="marketRegime"),
    confidence_tier: ConfidenceTier = Query(..., alias="confidenceTier"),
    exclude_id: str | None = Query(default=None, alias="excludeId"),
) -> SimilarTradesSummary:
    """The Decision Memory System's Similarity Engine — real, rule-based
    tiered bucket matching over the Decision Vault (see
    find_similar_vault_entries()'s own docstring for the exact tiers),
    never a fabricated similarity score. `excludeId` lets a just-closed
    trade's own vault entry compare itself against everything before it,
    rather than trivially matching itself."""
    state = await game_state.snapshot()
    matches, matched_on = find_similar_vault_entries(
        state.decision_vault,
        symbol=symbol,
        market_regime=market_regime,
        confidence_tier=confidence_tier,
        exclude_id=exclude_id,
    )
    return summarize_similarity(matches, matched_on)


@router.get("/quality-score", response_model=KnowledgeQualityScore)
async def quality_score(vault_entry_id: str = Query(..., alias="vaultEntryId")) -> KnowledgeQualityScore:
    """Design Bible Chapter 61's Knowledge Quality Score — see
    compute_knowledge_quality_score()'s own docstring for exactly which
    of the brief's named dimensions are real here and why the rest
    aren't fabricated."""
    state = await game_state.snapshot()
    entry = next((e for e in state.decision_vault if e.id == vault_entry_id), None)
    if entry is None:
        raise HTTPException(status_code=404, detail="No Decision Vault entry found with that id.")
    return compute_knowledge_quality_score(entry, state.decision_vault, state.time.day, min_matches=state.risk_limits.min_similar_matches)
