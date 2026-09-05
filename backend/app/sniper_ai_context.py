"""CEO directive "TradeTown — Memecoin Sniper AI 1.0" — the Memecoin
Sniper's own domain-specific AI Context Builder, reusing the SAME shared
`AIEvidencePacket`/`AIEvidenceItem`/`AIReasoningResult` architecture the
equities Researcher/Devil's Advocate reasoning already established
(app/ai_context_builder.py), not a second, parallel evidence system.

Phase 0 forensic finding, disclosed here because it shapes every evidence
item below: `SniperCandidate` carries no raw candle series at all — only
scalar snapshot fields (liquidity_usd/liquidity_trend, buy_pressure_pct,
momentum_pct, top10_concentration_pct, ...). Genuine higher-high/higher-
low market-structure analysis (the CEO directive's own Part IV wish list)
is therefore structurally impossible from this domain's real data — this
module NEVER fabricates it. Every "market structure" question the AI
might ask is answered `UNKNOWN`, honestly, via the fixed
`_MARKET_STRUCTURE_UNKNOWN` evidence item below, never invented from the
scalar fields that happen to be available.

Two more real, structural facts about this domain (not present in the
equities pipeline) drive this module's design:

  1. NO SIM-MINUTE CLOCK ON SNIPER RECORDS. SniperCandidate/Position/
     Trade all timestamp themselves with real wall-clock ISO strings
     (`_now_iso()`), not TradeTown's simulated calendar. But the whole
     game still ticks on ONE shared simulated clock (`GameSaveState.time`)
     that advances during the very same tick Sniper's own engine runs —
     so `knowledge_cutoff_sim_minutes` is reused verbatim (same field,
     same anti-lookahead contract, same units) by snapshotting that
     shared clock at the moment a Sniper reasoning request is made (see
     app/state.py's submit_sniper_ai_reasoning_request()) rather than
     inventing a second, wall-clock-based cutoff concept.
  2. NO CANDIDATE_ID FIELD ON SniperPosition/SniperTrade. This domain's
     own existing real join key across candidate -> position -> trade ->
     event is `mint` (a fresh, effectively-unique random string per
     candidate — see app/memecoin_sniper.py's `_fake_mint()`). This
     module reuses that exact existing key rather than adding a new field
     anywhere; `AIEvidencePacket.proposal_id`/`AIReasoningResult.proposal_id`
     carry the candidate's real `mint` for this domain (disclosed on both
     fields' own docstrings in app/schemas.py).
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from app.institutional_memory import retrieve_relevant_memory
from app.schemas import (
    AIEvidenceItem,
    AIEvidencePacket,
    AIReasoningResult,
    InstitutionalMemoryEntry,
    SniperCandidate,
    SniperPosition,
    SniperTrade,
)

CONTEXT_BUILDER_VERSION = "sniper-ai-context-builder-1.0"

# Part III/IV — real, fixed, disclosed limitations, mirroring
# app/ai_context_builder.py's own KNOWN_LIMITATIONS convention exactly,
# adapted to what this domain's real (simulated) data actually is and
# is not.
KNOWN_LIMITATIONS = [
    "Every token/liquidity/volume/momentum/social figure below is simulated (app/memecoin_sniper.py's own deterministic "
    "generator), not a real on-chain read — there is no real Solana RPC, Jupiter, or social-API connection in this environment.",
    "No raw candle series exists for Sniper tokens — only the scalar snapshot fields listed below. Higher-high/higher-low "
    "market-structure analysis is therefore UNKNOWN by construction, never inferred from the scalar fields alone.",
    "Whale/order-flow/order-book depth beyond the disclosed whale_signal_count is not available and is never represented "
    "here, even as an estimate.",
]

_MARKET_STRUCTURE_UNKNOWN = AIEvidenceItem(
    id="fact-market-structure",
    kind="unknown",
    label="Market structure (higher-highs/lows, breakout/breakdown, support/resistance)",
    detail="UNKNOWN — no candle series is stored for this token in this domain; only the scalar snapshot fields below exist.",
    asOfSimMinutes=0,  # overwritten with the real cutoff by build_sniper_evidence_packet() below.
)

_CREATOR_RISK_MANIPULATION_LABEL: dict[str, Literal["low", "medium", "high", "unknown"]] = {
    "confirmed": "high",
    "strong_signal": "medium",
    "weak_signal": "low",
    "unknown": "unknown",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _score_component_detail(candidate: SniperCandidate, name: str) -> str:
    """`SniperCandidate` itself carries no raw `momentum_pct` field (only
    `app/memecoin_sniper.py`'s internal, non-persisted `RawCandidate`
    does) — the real, disclosed value survives onto the persisted
    candidate only inside `score_components` (see `score_candidate()`'s
    own `SniperScoreComponent(name="momentum", rawValue=...)`). Reused
    here rather than re-deriving or approximating a second copy."""
    component = next((c for c in candidate.score_components if c.name == name), None)
    if component is None:
        return "UNKNOWN — no score component recorded."
    return f"{component.raw_value:+.1f}% (normalized {component.normalized_score:.0f}/100, weight {component.weight_pct:.0f}%) — {component.detail}"


def _manipulation_risk_label(candidate: SniperCandidate) -> Literal["low", "medium", "high", "unknown"]:
    """Part IV's own required LOW/MEDIUM/HIGH/UNKNOWN vocabulary — derived
    ONLY from the two real, disclosed signals this domain actually has
    (creator_risk, top10_concentration_pct), never a fabricated "whales
    are manipulating this" claim. The stricter of the two real reads
    wins (never averaged into a falsely reassuring middle)."""
    creator_label = _CREATOR_RISK_MANIPULATION_LABEL[candidate.creator_risk]
    if candidate.top10_concentration_pct > 75.0:
        concentration_label: Literal["low", "medium", "high", "unknown"] = "high"
    elif candidate.top10_concentration_pct > 45.0:
        concentration_label = "medium"
    else:
        concentration_label = "low"
    order: dict[str, int] = {"unknown": 0, "low": 1, "medium": 2, "high": 3}
    return creator_label if order[creator_label] >= order[concentration_label] else concentration_label


def build_sniper_evidence_packet(
    candidate: SniperCandidate,
    *,
    packet_id: str,
    task: str,
    cutoff_sim_minutes: int,
    institutional_memory: list[InstitutionalMemoryEntry],
    current_sim_day: int,
    position: SniperPosition | None = None,
    trade: SniperTrade | None = None,
) -> AIEvidencePacket:
    """The one real Memecoin Sniper evidence packet builder. Built once,
    from the SAME real `SniperCandidate` (plus, when they exist, the SAME
    real `SniperPosition`/`SniperTrade` for this candidate's `mint`) the
    deterministic engine already produced — never a second, parallel
    computation of any of these facts. `position`/`trade` are `None` for
    a candidate the deterministic engine never entered (a rejected/watch/
    qualified-but-blocked candidate) — Part V's own "NO TRADE" reasoning
    case is a first-class, fully-supported input shape here, not a
    degraded one."""
    items: list[AIEvidenceItem] = [
        AIEvidenceItem(id="fact-symbol", kind="fact", label="Token symbol", detail=f"{candidate.symbol} ({candidate.name})", asOfSimMinutes=cutoff_sim_minutes),
        AIEvidenceItem(id="fact-age", kind="fact", label="Token age at discovery", detail=f"{candidate.age_seconds:.0f} seconds", asOfSimMinutes=cutoff_sim_minutes),
        AIEvidenceItem(id="fact-price", kind="fact", label="Price (USD)", detail=f"{candidate.price_usd:.10f}", asOfSimMinutes=cutoff_sim_minutes),
        AIEvidenceItem(id="fact-market-cap", kind="fact", label="Market cap (USD)", detail=f"{candidate.market_cap_usd:,.0f}", asOfSimMinutes=cutoff_sim_minutes),
        AIEvidenceItem(
            id="fact-liquidity", kind="fact", label="Liquidity (OBSERVED, simulated)",
            detail=f"${candidate.liquidity_usd:,.0f}, trend: {candidate.liquidity_trend}", asOfSimMinutes=cutoff_sim_minutes,
        ),
        AIEvidenceItem(
            id="fact-buy-pressure", kind="fact", label="Buy pressure (last minute)",
            detail=f"{candidate.buy_count_1m} buys, {candidate.buy_pressure_pct:.1f}% buy pressure, {candidate.unique_buyers} unique buyers vs {candidate.unique_sellers} unique sellers",
            asOfSimMinutes=cutoff_sim_minutes,
        ),
        AIEvidenceItem(id="fact-momentum", kind="fact", label="Momentum", detail=_score_component_detail(candidate, "momentum"), asOfSimMinutes=cutoff_sim_minutes),
        AIEvidenceItem(
            id="fact-holder-concentration", kind="fact", label="Top-10 holder concentration",
            detail=f"{candidate.top10_concentration_pct:.1f}%", asOfSimMinutes=cutoff_sim_minutes,
        ),
        AIEvidenceItem(
            id="fact-safety", kind="fact", label="Safety firewall (deterministic)",
            detail=f"status={candidate.safety_status}; mint authority revoked={candidate.mint_authority_revoked}; freeze authority revoked={candidate.freeze_authority_revoked}; creator risk={candidate.creator_risk}",
            asOfSimMinutes=cutoff_sim_minutes,
        ),
        AIEvidenceItem(
            id="fact-manipulation-risk", kind="fact", label="Manipulation/rug risk (derived from creator risk + holder concentration only)",
            detail=_manipulation_risk_label(candidate), asOfSimMinutes=cutoff_sim_minutes,
        ),
        AIEvidenceItem(
            id="fact-whale-signals", kind="fact", label="Whale confirmation (simulated smart-money entries)",
            detail=f"{candidate.whale_signal_count} independent signal(s)", asOfSimMinutes=cutoff_sim_minutes,
        ),
        AIEvidenceItem(id="fact-social", kind="fact", label="Social momentum (simulated)", detail=f"{candidate.social_momentum_pct:+.1f}%", asOfSimMinutes=cutoff_sim_minutes),
        AIEvidenceItem(id="fact-slippage", kind="fact", label="Expected slippage", detail=f"{candidate.expected_slippage_pct:.1f}%", asOfSimMinutes=cutoff_sim_minutes),
        AIEvidenceItem(
            id="fact-deterministic-decision", kind="fact", label="Deterministic engine's own decision",
            detail=f"score={candidate.opportunity_score}, classification={candidate.classification}, timing={candidate.timing_state} — {candidate.decision_reason}",
            asOfSimMinutes=cutoff_sim_minutes,
        ),
        _MARKET_STRUCTURE_UNKNOWN.model_copy(update={"as_of_sim_minutes": cutoff_sim_minutes}),
    ]

    if position is not None or trade is not None:
        entry_price = trade.entry_price if trade is not None else position.entry_price  # type: ignore[union-attr]
        stop_price = trade.stop_price if trade is not None else position.stop_price  # type: ignore[union-attr]
        target_price = trade.target_price if trade is not None else position.target_price  # type: ignore[union-attr]
        items.append(
            AIEvidenceItem(
                id="fact-entry-risk", kind="fact", label="Deterministic entry/stop/target (already sized)",
                detail=f"entry={entry_price:.10f}, stop={stop_price:.10f}, target={target_price:.10f}",
                asOfSimMinutes=cutoff_sim_minutes,
            )
        )
    if trade is not None:
        # "Sniper AI Shadow Reasoning Burn-In 1.0" directive, Part XI/
        # XXVI — a real, previously-undetected hindsight-leak this pass's
        # own fresh audit caught: this domain has no sim-minute clock of
        # its own (see this module's own docstring), so `cutoff_sim_minutes`
        # is always effectively "now" (reasoning-REQUEST time), not the
        # candidate's own discovery/decision time. Because
        # `tick_sniper_engine()` can open AND close a trade within
        # seconds of discovery, a human clicking "Ask AI" even slightly
        # later could previously see this candidate's REAL, already-
        # resolved outcome (pnl_sol/r_multiple/exit_reason) fed straight
        # into the evidence the model uses to form its OWN recommendation
        # — trivially "predicting" an outcome it was just shown. The
        # deterministic-vs-AI comparison (compare_sniper_ai_to_deterministic,
        # resolve_sniper_deterministic_outcome) never needed this item at
        # all — both read real trade_history directly and independently
        # — so removing it costs zero real functionality while closing
        # the leak. The fact of closure is still disclosed (never hidden
        # that a resolution exists) but the actual outcome never is;
        # `AIReasoningResult.requested_after_outcome_known` (set by the
        # caller in app/state.py) is the honest, disclosed flag for
        # "this request happened after the real outcome already existed,"
        # for downstream evaluation to filter or label — never silently
        # baked into the reasoning itself.
        items.append(
            AIEvidenceItem(
                id="fact-trade-outcome", kind="unknown", label="Real trade outcome (closed)",
                detail="This candidate's position has already closed. The real outcome is deliberately withheld from this evidence packet to prevent hindsight bias in the recommendation below.",
                asOfSimMinutes=cutoff_sim_minutes,
            )
        )
    elif position is not None:
        items.append(
            AIEvidenceItem(
                id="fact-position-open", kind="fact", label="Real, still-open position",
                detail=f"current_price={position.current_price:.10f}, pnl_pct={position.pnl_pct:+.1f}%, hold_time_seconds={position.hold_time_seconds:.0f}",
                asOfSimMinutes=cutoff_sim_minutes,
            )
        )

    memory = retrieve_relevant_memory(institutional_memory, current_sim_day=current_sim_day, domain="memecoin_sniper", symbol=candidate.symbol)
    if memory is not None and memory.sim_day * 1440 <= cutoff_sim_minutes:
        detail = f"[{memory.status}] {memory.observation}"
        if memory.lesson:
            detail += f" Lesson: {memory.lesson}"
        items.append(AIEvidenceItem(id=f"knowledge-{memory.id}", kind="knowledge", label=f"Institutional memory ({memory.source})", detail=detail, asOfSimMinutes=memory.sim_day * 1440))

    return AIEvidencePacket(
        id=packet_id,
        task=task,
        agentRole="sniper_analyst",
        domain="memecoin_sniper",
        proposalId=candidate.mint,
        symbol=candidate.symbol,
        knowledgeCutoffSimMinutes=cutoff_sim_minutes,
        items=items,
        knownLimitations=list(KNOWN_LIMITATIONS),
        contextBuilderVersion=CONTEXT_BUILDER_VERSION,
        createdAt=_now_iso(),
    )


def deterministic_sniper_recommendation(mint: str, *, positions: list[SniperPosition], trade_history: list[SniperTrade]) -> Literal["buy", "wait"]:
    """Part XVI/XVII — the real deterministic outcome for this candidate,
    expressed honestly in `AnalystChoice`'s existing "buy"/"wait"
    vocabulary (this domain never shorts, so "sell" never applies):
    "buy" when the deterministic engine actually opened a real (paper)
    position for this mint at any point, "wait" otherwise. Because
    `tick_sniper_engine()` evaluates entry exactly once, at discovery, in
    the SAME tick a candidate is created (see app/memecoin_sniper.py's
    own module docstring), this is never a race — by the time any AI
    reasoning call can even be requested (always after discovery), the
    deterministic fate of a candidate is already permanent."""
    if any(t.mint == mint for t in trade_history) or any(p.mint == mint for p in positions):
        return "buy"
    return "wait"


def resolve_sniper_deterministic_outcome(
    mint: str, *, positions: list[SniperPosition], trade_history: list[SniperTrade]
) -> tuple[Literal["pending", "supported", "contradicted", "inconclusive"], str | None]:
    """Part XVIII — mirrors app/ai_context_builder.py's
    resolve_deterministic_outcome() exactly in spirit (grade against real
    subsequent evidence, never invent it), adapted to this domain's real
    join key (`mint`) and real trade shape. A closed `SniperTrade` grades
    by its own real `pnl_sol` sign. A still-OPEN `SniperPosition` is
    honestly `"pending"` — real further evidence (the eventual close) is
    still forthcoming. A candidate the deterministic engine never entered
    at all is `"inconclusive"`, not `"pending"`: `tick_sniper_engine()`
    only ever evaluates entry once, at discovery, so there is structurally
    no future tick that could still open a position for this mint — no
    further real evidence will ever exist for it, so treating it as
    "pending forever" would misrepresent a permanently closed question as
    an open one."""
    trade = next((t for t in trade_history if t.mint == mint), None)
    if trade is not None:
        if trade.pnl_sol > 0:
            return "supported", trade.id
        if trade.pnl_sol < 0:
            return "contradicted", trade.id
        return "inconclusive", trade.id
    position = next((p for p in positions if p.mint == mint and p.status == "open"), None)
    if position is not None:
        return "pending", position.id
    return "inconclusive", None


def compare_sniper_ai_to_deterministic(result: AIReasoningResult) -> Literal["agree", "disagree", "partial", "inconclusive"]:
    """Part XVI/XVII — a real, computed-fresh (never persisted — same
    convention as app/collaboration_intelligence.py's
    CollaborationCaseSummary) comparison between what the AI recommended
    and what the deterministic engine actually did for the SAME
    candidate (`result.deterministic_recommendation`, stamped at
    reasoning-request time by app/state.py). Never invents a verdict when
    the AI reasoning itself didn't complete."""
    if result.status != "completed" or result.recommendation is None or result.deterministic_recommendation is None:
        return "inconclusive"
    if result.recommendation == "research_more":
        return "partial"
    ai_wants_trade = result.recommendation == "buy"
    deterministic_traded = result.deterministic_recommendation == "buy"
    if ai_wants_trade == deterministic_traded:
        return "agree"
    return "disagree"
