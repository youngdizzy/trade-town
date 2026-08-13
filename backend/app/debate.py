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


def _cross_examination(votes: list[AnalystVote], overall_recommendation: str) -> list[DebateTurn]:
    """One real challenge-or-support turn per analyst, judged against
    that analyst's own real relationship to the desk's actual final
    call — not "does any disagreement exist anywhere on the desk."

    The previous version gave an analyst a "challenge" turn the moment
    it found *any* other analyst who disagreed with *that analyst*,
    checked before ever looking for agreement. With six independent
    analysts, some pairwise disagreement is almost always present, so
    in practice every analyst got "challenge" on nearly every debate —
    including the ones who actually agreed with the desk's own final
    recommendation and with each other. "Support" turns only ever
    appeared on the rare debate where all six voted identically. That
    collapsed Team Chemistry (app/company_health.py's _team_chemistry)
    into "unanimous vs. not," the exact false binary the CEO's Company
    Health directive named as the anti-pattern to avoid.

    Fixed: each analyst's stance reflects whether *their own* vote
    matches the desk's real overall_recommendation. An analyst voting
    with the desk backs it up (support); an analyst voting against it
    is the one actually raising a real objection (challenge). A 4-2
    split now produces 4 support turns and 2 challenge turns instead of
    6 challenge turns — the minority's real dissent is preserved
    without mislabeling the majority's real agreement as conflict."""
    turns: list[DebateTurn] = []
    for vote in votes:
        others = [v for v in votes if v.agent_id != vote.agent_id]
        if vote.choice != overall_recommendation:
            # A real disagreement with the desk's actual call. Point at
            # another analyst who did side with the final recommendation
            # (the real position being challenged), falling back to any
            # other analyst if the whole desk somehow overrode this vote
            # alone.
            target = next((o for o in others if o.choice == overall_recommendation), others[0] if others else None)
            opener = random.choice(_CHALLENGE_OPENERS).format(other=_ROLE_LABEL[target.role] if target else "the desk")
            turns.append(DebateTurn(agentId=vote.agent_id, role=vote.role, stance="challenge", respondingTo=target.agent_id if target else None, text=f"{opener} {vote.reasoning}"))
        else:
            # Backing the desk's real call. Credit another analyst who
            # also voted for it where one exists (a genuine ally), else
            # this is the lone supporter and there is no one real to
            # name.
            ally = next((o for o in others if o.choice == overall_recommendation), None)
            opener = random.choice(_SUPPORT_OPENERS).format(other=_ROLE_LABEL[ally.role] if ally else "the desk")
            turns.append(DebateTurn(agentId=vote.agent_id, role=vote.role, stance="support", respondingTo=ally.agent_id if ally else None, text=f"{opener} {vote.reasoning}"))
    return turns


def generate_debate(proposal: TradeProposal) -> Debate:
    """A fresh Debate over `proposal`'s already-real analyst votes.
    Calling this again for the same proposal ("request another debate")
    reshuffles which real challenge/support opener each analyst gets —
    the underlying evidence and final recommendation never change,
    since neither is invented per-call."""
    opening = [_opening_turn(v) for v in proposal.analyst_votes]
    cross = _cross_examination(proposal.analyst_votes, proposal.overall_recommendation)
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
