"""app/agent_trading_status.py — CEO directive "TradeTown — Command
Center + Professional Quant Trading Firm Upgrade," Phase 2 (AI Desk /
Agent Decision Explainability).

The directive's own worked example asks for a per-agent narrative —
status, reason, session, strategy, "next condition required" — built
from real evidence, never fabricated. Research first: this codebase
has no per-agent "why not trading right now" object anywhere (`app/
trade_pipeline_health.py`'s `NoTradeReasonCode` taxonomy is real but
aggregate — a code and a count, never attributed to one agent), and
`AgentState` (`app/schemas.py`) carries no trading-readiness field at
all. This module closes that gap using ONLY signals that already exist:

- A real live stance: `app/executive.py`'s `generate_analyst_votes()`
  is the only place in this codebase that ever attributes an
  `AnalystVote` to a specific `agent_id` — this module never re-derives
  or hardcodes which agent "should" vote on which role; it just scans
  every currently PENDING `TradeProposal.analyst_votes` for a real
  match. Only 6 of the 15 real agents (scout/atlas/echo/nova/sentinel/
  pulse) can ever appear here, by construction of that generator.
- A real active research assignment: `app/research.py`'s
  `RESEARCHER_IDS` (scout/atlas/echo/nova) is the only real source of
  per-agent `ResearchItem` assignment.
- The real, live Emergency Stop state.
- `AGENT_PROFILES`' own real `occupation` string, for the 9 agents
  (guardian/keystone/cio/coach/sage/compass/scribe/quant/forge) whose
  real role never generates a vote or research assignment at all —
  stated as the honest truth about the role (the exact same convention
  `app/performance_review.py`'s `AGENT_ROLE_CLASS` already established:
  "Sentinel structurally never gets research assignments... that's not
  a gap, it's the truth about the role").

NO "next condition required" PREDICTION. The directive's own worked
example asks for one; this codebase has no real mechanism that
forecasts what a symbol needs to do next (that would require the live
BOS/CHoCH/liquidity-sweep detectors app/market_intelligence.py and
app/technical_patterns.py already have to run continuously per symbol
per agent, which nothing in the live decision pipeline does today).
Rather than fabricate one, `detail` below surfaces the real existing
narrative text a "wait" `AnalystVote.reasoning` or a `ResearchItem.
summary` already carries — which, for a wait vote, already tends to
name what's currently missing (see `app/executive.py`'s own
`_technical_vote()`: "ranging ... no clear technical edge yet").
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.agents import AGENT_PROFILES
from app.market_intelligence import compute_session
from app.performance_review import AGENT_ROLE_CLASS
from app.research import RESEARCHER_IDS
from app.schemas import AgentId, AgentTradingStatusRead, EmergencyStopState, ResearchItem, TradeProposal


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def compute_agent_trading_status(
    agent_id: AgentId,
    *,
    trade_proposals: list[TradeProposal],
    research: list[ResearchItem],
    emergency_stop: EmergencyStopState,
) -> AgentTradingStatusRead:
    """One agent's real, current trading-relevant state — see this
    module's own docstring for the exact real signal behind each
    status and the priority order below (checked top to bottom; the
    first real match wins)."""
    role_class = AGENT_ROLE_CLASS[agent_id]
    session = compute_session(datetime.now(timezone.utc))

    if emergency_stop.active:
        return AgentTradingStatusRead(
            agentId=agent_id,
            roleClass=role_class,
            status="risk_blocked",
            headline="Emergency Stop is active — all new trading is halted company-wide.",
            detail="A real, active Emergency Stop (app/emergency_stop.py) blocks every agent from progressing toward a new trade right now, regardless of this agent's own real role.",
            session=session,
            updatedAt=_now_iso(),
        )

    for proposal in trade_proposals:
        vote = next((v for v in proposal.analyst_votes if v.agent_id == agent_id), None)
        if vote is not None:
            return AgentTradingStatusRead(
                agentId=agent_id,
                roleClass=role_class,
                status="waiting",
                headline=f"{vote.choice.upper()} stance on {proposal.symbol} — pending the CEO's real decision.",
                detail=vote.reasoning,
                symbol=proposal.symbol,
                proposalId=proposal.id,
                session=session,
                updatedAt=_now_iso(),
            )

    if agent_id in RESEARCHER_IDS:
        item = next((r for r in research if r.assigned_agent == agent_id and r.status in ("queued", "in_progress")), None)
        if item is not None:
            return AgentTradingStatusRead(
                agentId=agent_id,
                roleClass=role_class,
                status="scanning",
                headline=f"Researching {item.symbol or item.title} ({item.category.replace('_', ' ')}).",
                detail=item.summary,
                symbol=item.symbol,
                researchCategory=item.category,
                session=session,
                updatedAt=_now_iso(),
            )
        return AgentTradingStatusRead(
            agentId=agent_id,
            roleClass=role_class,
            status="idle",
            headline="No active research assignment right now.",
            detail=f"{AGENT_PROFILES[agent_id].name} is a real research-capable agent with no queued or in-progress ResearchItem at this moment — an honest gap in current work, not a missing feature.",
            session=session,
            updatedAt=_now_iso(),
        )

    # sentinel/pulse: real vote-capable roles (checked above via the
    # live-proposal scan) with no currently pending proposal to vote on.
    if agent_id in ("sentinel", "pulse"):
        return AgentTradingStatusRead(
            agentId=agent_id,
            roleClass=role_class,
            status="idle",
            headline="No pending trade proposal to weigh in on right now.",
            detail=f"{AGENT_PROFILES[agent_id].name} casts a real vote on every live TradeProposal (see app/executive.py) but none is currently pending.",
            session=session,
            updatedAt=_now_iso(),
        )

    profile = AGENT_PROFILES[agent_id]
    return AgentTradingStatusRead(
        agentId=agent_id,
        roleClass=role_class,
        status="not_trading_role",
        headline=f"{profile.occupation} — does not generate its own live trade vote or research assignment.",
        detail=f"{profile.name}'s real role in this codebase is {profile.occupation}. Unlike scout/atlas/echo/nova/sentinel/pulse, this agent never casts an AnalystVote or receives a ResearchItem assignment — that is the honest truth about the role, not a gap in this read.",
        session=session,
        updatedAt=_now_iso(),
    )
