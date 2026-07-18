"""VotingManager — the "VotingManager" role from the v0.6 brief. Collects
a vote from every relevant agent on a trade candidate: each researcher
agent's stance (templated from their own research confidence, not a real
model call — the same "deterministic but varied" convention
app/discussion.py already established for meeting dialogue), plus
Sentinel's risk-approval vote and Guardian's exposure vote, both backed
by app/risk_engine.py's evaluations rather than invented here.

This module only ever produces votes; app/decision.py is the only
consumer that turns a set of votes into a trade/no-trade outcome.
"""
from __future__ import annotations

import random

from app.schemas import AgentId, AgentVote, RiskWarning, VoteChoice

# Above this confidence, a non-originating researcher is likely (but not
# certain) to agree — below it, more likely to hold or dissent. Mirrors
# the same "confidence drives behavior, with randomness" shape
# app/research.py's confidence gain already uses, rather than a fixed
# rule that would make every vote at a given confidence identical.
AGREEMENT_CONFIDENCE_THRESHOLD = 80.0
AGREEMENT_CHANCE_ABOVE_THRESHOLD = 0.7
AGREEMENT_CHANCE_BELOW_THRESHOLD = 0.35


def _researcher_vote(agent_id: AgentId, *, originated: bool, confidence: float, symbol: str) -> AgentVote:
    if originated:
        return AgentVote(agentId=agent_id, choice="buy", reason=f"Originated this research on {symbol} at {confidence:.0f}% confidence.")

    chance = AGREEMENT_CHANCE_ABOVE_THRESHOLD if confidence >= AGREEMENT_CONFIDENCE_THRESHOLD else AGREEMENT_CHANCE_BELOW_THRESHOLD
    roll = random.random()
    choice: VoteChoice
    if roll < chance:
        choice = "buy"
        reason = f"{confidence:.0f}% confidence on {symbol} is convincing enough to support."
    elif roll < chance + (1 - chance) / 2:
        choice = "hold"
        reason = f"{symbol} at {confidence:.0f}% confidence isn't quite enough to commit either way yet."
    else:
        choice = "sell"
        reason = f"Not convinced by {symbol} at {confidence:.0f}% confidence — would rather stay out."
    return AgentVote(agentId=agent_id, choice=choice, reason=reason)


def collect_votes(
    *,
    symbol: str,
    confidence: float,
    originating_agent: AgentId,
    researcher_ids: tuple[AgentId, ...],
    sentinel_warning: RiskWarning | None,
    guardian_warning: RiskWarning | None,
) -> list[AgentVote]:
    """One round of voting on a trade candidate. `sentinel_warning` /
    `guardian_warning` are pre-computed by app/risk_engine.py's
    evaluate_sentinel_risk()/evaluate_guardian_exposure() — this
    function only translates them into votes, it doesn't re-derive the
    risk judgment itself."""
    votes = [
        _researcher_vote(agent_id, originated=(agent_id == originating_agent), confidence=confidence, symbol=symbol)
        for agent_id in researcher_ids
    ]

    votes.append(
        AgentVote(
            agentId="sentinel",
            choice="risk_too_high" if sentinel_warning else "buy",
            reason=sentinel_warning.message if sentinel_warning else f"{symbol} is within configured risk limits.",
        )
    )
    votes.append(
        AgentVote(
            agentId="guardian",
            choice="position_too_large" if guardian_warning else "buy",
            reason=guardian_warning.message if guardian_warning else f"Portfolio exposure to {symbol} is acceptable.",
        )
    )
    return votes
