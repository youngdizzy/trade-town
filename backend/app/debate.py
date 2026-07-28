"""AiDebate — v0.7 Feature 17, the AI Debate Room.

Every "agent" in the debate is one of the six real analyst seats
Executive Voting already built (app/executive.py's generate_analyst_votes:
technical/Echo, news/Scout, macro/Nova, risk/Sentinel, sentiment/Pulse,
execution/Atlas). The v0.7 brief's cast list also names a "Portfolio
Manager" and a "Strategy Analyst" — this codebase has no independent real
signal for either (Atlas's execution vote already *is* the desk's
portfolio-level synthesis, and there is no separate strategy-analyst
computation anywhere), so those two are not invented as distinct
participants; Atlas is labelled "Portfolio Manager" below since that's
the closest real analogue to what its vote already does.

The debate's substance is never fabricated: every turn's text is the
same real AnalystVote.reasoning/evidence Executive Voting already shows
the player, just given a real cross-examination framing when two
analysts' real votes disagree — a templated opening sentence, not new
invented evidence. This is the same "deterministic-but-varied templated
framing over real state" convention app/discussion.py already
established for the Meeting Room's chatter.
"""
from __future__ import annotations

import random
from datetime import datetime, timezone

from app.schemas import AnalystVote, Debate, DebateTurn, TradeProposal

_ROLE_LABEL: dict[str, str] = {
    "technical": "the Technical Analyst",
    "news": "the News Analyst",
    "macro": "the Macro Analyst",
    "risk": "the Risk Manager",
    "sentiment": "the Sentiment Analyst",
    "execution": "the Portfolio Manager",
}

_CHALLENGE_OPENERS: list[str] = [
    "I have to push back on {other}'s read here —",
    "Not so fast — {other} may be missing something:",
    "I'd flag a real concern with {other}'s position.",
]
_SUPPORT_OPENERS: list[str] = [
    "I'll back up {other} on this one —",
    "{other} is right, and here's a second read that agrees:",
    "Adding to {other}'s point —",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _opening_turn(vote: AnalystVote) -> DebateTurn:
    text = f"{vote.reasoning} ({'; '.join(vote.evidence)})" if vote.evidence else vote.reasoning
    return DebateTurn(agentId=vote.agent_id, role=vote.role, stance="opening", respondingTo=None, text=text)


def _cross_examination(votes: list[AnalystVote]) -> list[DebateTurn]:
    """One real challenge-or-support turn per analyst — the first real
    disagreement it finds among the others (or, absent one, the first
    real agreement) — rather than every pairwise combination, which
    would balloon into an unreadable wall of near-duplicate text for a
    six-seat desk."""
    turns: list[DebateTurn] = []
    for vote in votes:
        others = [v for v in votes if v.agent_id != vote.agent_id]
        disagreement = next((o for o in others if o.choice != vote.choice), None)
        if disagreement is not None:
            opener = random.choice(_CHALLENGE_OPENERS).format(other=_ROLE_LABEL[disagreement.role])
            turns.append(DebateTurn(agentId=vote.agent_id, role=vote.role, stance="challenge", respondingTo=disagreement.agent_id, text=f"{opener} {vote.reasoning}"))
            continue
        agreement = next((o for o in others if o.choice == vote.choice), None)
        if agreement is not None:
            opener = random.choice(_SUPPORT_OPENERS).format(other=_ROLE_LABEL[agreement.role])
            turns.append(DebateTurn(agentId=vote.agent_id, role=vote.role, stance="support", respondingTo=agreement.agent_id, text=f"{opener} {vote.reasoning}"))
    return turns


def generate_debate(proposal: TradeProposal) -> Debate:
    """A fresh Debate over `proposal`'s already-real analyst votes.
    Calling this again for the same proposal ("request another debate")
    reshuffles which real challenge/support opener each analyst gets —
    the underlying evidence and final recommendation never change,
    since neither is invented per-call."""
    opening = [_opening_turn(v) for v in proposal.analyst_votes]
    cross = _cross_examination(proposal.analyst_votes)
    summary = (
        f"After {len(proposal.analyst_votes)} independent reads, the desk recommends "
        f"{proposal.overall_recommendation.upper()} on {proposal.symbol}. {proposal.confidence_engine.summary}"
    )
    return Debate(
        id=f"debate-{proposal.id}-{int(datetime.now(timezone.utc).timestamp() * 1000)}-{random.randint(1000, 9999)}",
        proposalId=proposal.id,
        symbol=proposal.symbol,
        turns=[*opening, *cross],
        finalRecommendation=proposal.overall_recommendation,
        finalSummary=summary,
        createdAt=_now_iso(),
    )
