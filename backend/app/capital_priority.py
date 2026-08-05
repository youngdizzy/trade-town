"""app/capital_priority.py — Capital Priority & Opportunity Cost Engine
(v0.7 Design Bible Chapter 59).

GOAL (from the chapter): "Good trades deserve consideration. Great
trades deserve capital." Chapter 58's Opportunity Gatekeeper already
decides which candidates earn a TradeProposal at all; once approved,
this engine decides the ORDER capital is offered to them — highest
quality first, never first-come-first-served.

REUSES, DOES NOT DUPLICATE. `app/war_room.py`'s `DecisionScoreBreakdown.
overall` is already, factor-for-factor, the same real composite the
brief's own "Priority Score" describes (Expected Value, Evidence, Risk,
Portfolio Compatibility, Market Quality, Liquidity...). Inventing a
second composite from the same underlying signals would be exactly the
duplication this codebase's own convention forbids (see Chapters 57 and
58's own precedent). This module reuses `decisionScore.overall` directly
as the real Priority Score — it never computes a competing number.

WHAT'S GENUINELY NEW HERE: sorting the pending queue by that reused
score (`rank_trade_proposals`), and a real, additive capital-reserve
check (`cash_reserve_breached`) that respects the CEO's own voluntary
`RiskLimits.capitalReservePct` — separate from, and layered on top of,
Chapter 57's existing hard `cashReservePct` floor in
`app/position_sizing.py` (that one Position Sizing never spends into;
this one is the CEO's own choice to hold back even more when few
high-quality opportunities exist).

HONESTY BOUNDARY: Replacement Analysis against already-open positions is
explicitly Chapter 60's job, not this module's — this queue only ever
contains pending, not-yet-capitalized proposals.
"""
from __future__ import annotations

from app.risk_engine import portfolio_equity
from app.schemas import PaperPortfolio, RiskLimits, TradeProposal, WarRoomSession


def priority_score(proposal: TradeProposal, war_room_sessions: list[WarRoomSession]) -> float | None:
    """The real Priority Score for one proposal — its own WarRoomSession's
    already-computed `decisionScore.overall`, matched by `proposalId` the
    same way `app/nexus.py`'s outcome-comparison lookup already does.
    None only for a proposal with no linked session at all (shouldn't
    happen for any proposal that reached `trade_proposals` — every one is
    appended alongside its own `record_war_room_session` call — kept
    honest rather than assumed)."""
    session = next((s for s in war_room_sessions if s.proposal_id == proposal.id), None)
    return session.decision_score.overall if session is not None else None


def rank_trade_proposals(trade_proposals: list[TradeProposal], war_room_sessions: list[WarRoomSession]) -> list[TradeProposal]:
    """Closes the exact gap Chapter 58's own Implementation Notes flagged
    as unbuilt: the pending queue sorted by Priority Score, highest
    first, instead of arrival order. A proposal with no linked session
    (see `priority_score`) sorts last rather than crashing or being
    dropped. `sorted` is stable, so equal-scoring proposals keep their
    relative arrival order."""
    scored = [(p, priority_score(p, war_room_sessions)) for p in trade_proposals]
    scored.sort(key=lambda item: item[1] if item[1] is not None else -1.0, reverse=True)
    return [p for p, _ in scored]


def cash_reserve_breached(portfolio: PaperPortfolio, risk_limits: RiskLimits) -> bool:
    """True once cash as a % of equity has fallen to (or below) the
    CEO's own voluntary `capitalReservePct` target — "holding cash is an
    intelligent allocation decision," made real by simply respecting a
    higher CEO-chosen number. `capitalReservePct` defaults to 0, which
    never breaches (opt-in only — this is additive to, never a
    replacement for, Chapter 57's own hard `cashReservePct` floor, which
    stays enforced by `app/position_sizing.py` regardless of this
    engine)."""
    if risk_limits.capital_reserve_pct <= 0:
        return False
    equity = portfolio_equity(portfolio)
    if equity <= 0:
        return False
    cash_pct = portfolio.cash_balance / equity * 100
    return cash_pct <= risk_limits.capital_reserve_pct
