"""DecisionEngine — the "DecisionEngine" role from the v0.6 brief: Atlas's
final call on a trade candidate, given every vote app/voting.py collected,
producing the permanent, explainable TradeDecision report the brief's
"Explainable AI" feature calls for.

Rule: any hard-reject vote (Sentinel's "risk_too_high" or Guardian's
"position_too_large") blocks the trade outright, regardless of how many
researcher agents voted buy — risk/exposure vetoes are absolute, not
just one vote among many, matching how Sentinel/Guardian are described
in the brief ("Sentinel can reject trades"). Absent a hard reject, a
simple majority of "buy" votes among all votes cast approves the trade.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.agents import AGENT_PROFILES
from app.schemas import AgentId, AgentVote, DecisionOutcome, ResearchItem, TradeDecision

HARD_REJECT_CHOICES = ("risk_too_high", "position_too_large")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _summaries(item: ResearchItem) -> tuple[str, str, str]:
    """Research/technical/fundamental summaries for the explainable
    report. TradeTown doesn't run separate technical/fundamental
    analysis passes (see app/research.py — one confidence-weighted
    research item per symbol, not three parallel disciplines), so the
    technical/fundamental summaries are framed as "what this research
    item implies" for each lens rather than citing analysis that was
    never actually run — an honest placeholder, not a fabricated one."""
    research_summary = f"{item.title} — {item.summary}"
    technical_summary = f"No dedicated technical analysis pass exists yet; research confidence stands at {item.confidence:.0f}%."
    fundamental_summary = f"No dedicated fundamental analysis pass exists yet; category classified as {item.category}."
    return research_summary, technical_summary, fundamental_summary


def decide_trade(
    *,
    decision_id: str,
    item: ResearchItem,
    votes: list[AgentVote],
    risk_summary: str,
) -> TradeDecision:
    hard_rejects = [v for v in votes if v.choice in HARD_REJECT_CHOICES]
    buy_votes = [v for v in votes if v.choice == "buy"]

    outcome: DecisionOutcome
    if hard_rejects:
        outcome = "no_trade"
        blockers = ", ".join(AGENT_PROFILES[v.agent_id].name for v in hard_rejects)
        reasons = "; ".join(v.reason for v in hard_rejects)
        final_reasoning = f"Blocked by {blockers}: {reasons}"
    elif len(buy_votes) * 2 >= len(votes):
        outcome = "trade"
        final_reasoning = f"{len(buy_votes)} of {len(votes)} votes in favor — Atlas approves the trade on {item.symbol}."
    else:
        outcome = "no_trade"
        final_reasoning = f"Only {len(buy_votes)} of {len(votes)} votes in favor — Atlas holds off on {item.symbol} pending more consensus."

    supporting: list[AgentId] = [v.agent_id for v in votes if v.choice == "buy"]
    opposing: list[AgentId] = [v.agent_id for v in votes if v.choice != "buy"]
    research_summary, technical_summary, fundamental_summary = _summaries(item)

    return TradeDecision(
        id=decision_id,
        symbol=item.symbol or "UNKNOWN",
        outcome=outcome,
        votes=votes,
        researchSummary=research_summary,
        technicalSummary=technical_summary,
        fundamentalSummary=fundamental_summary,
        riskSummary=risk_summary,
        supportingAgents=supporting,
        opposingAgents=opposing,
        confidence=item.confidence,
        finalReasoning=final_reasoning,
        orderId=None,
        createdAt=_now_iso(),
    )
