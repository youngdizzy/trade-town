"""app/opportunity_feed.py — CEO directive "Professional Quant Trading
Core," Rule 25 (progressive-disclosure CEO view) / Rule 26 (CEO
Opportunity Feed: "BEST CURRENT OPPORTUNITIES / WATCHLIST / AVOID").

RESEARCH FIRST. A Phase A audit of this codebase found the scoring and
evidence a CEO Opportunity Feed needs already computed live every tick,
with zero UI/API surface anywhere:
  - `app/opportunity_gatekeeper.py`'s `evaluate_opportunity()` already
    approves or rejects every trade candidate with a real Decision
    Score (`app/war_room.py::build_decision_score()`) and Expected
    Value (`ExpectedValueAnalysis`) — approved candidates become
    `TradeProposal`s (already ranked by real Priority Score, see
    `app/capital_priority.py::rank_trade_proposals`); rejected ones
    become `OpportunityRejection` records carrying their own real
    score/reasons, but the only existing consumer
    (`RiskPanel.tsx`'s pipeline-health funnel) shows just a bare count.
  - `app/research.py`'s in-progress `ResearchItem`s are a real,
    already-tracked "still being evaluated, no verdict yet" set.

This module adds NO new scoring, NO new gate, and NO new persisted
state — it is a pure, CAGS (computed-at-get-time) read that ranks and
surfaces evidence three already-real systems produce, the same
convention `app/trade_pipeline_health.py` already established for its
own diagnostics.

HONEST SCOPE BOUNDARY: this is NOT a whole-universe proactive scanner.
`app/nexus.py`'s `_generate_trade_proposals()` is, and remains, purely
reactive — it only turns `completed_research` into candidates; building
a true "scan every watchlist symbol every tick and rank it" engine
would mean re-architecting `app/research.py`'s reactive rotation, which
is out of scope for this pass (a real, disclosed gap, not silently
fixed by this module). What this feed DOES do honestly: it ranks and
surfaces every real candidate/rejection/in-progress-research record
that already exists at read time — nothing here fabricates a score for
a symbol nobody has actually researched.

Every OpportunityFeedEntry.status is real, not aspirational:
  - "eligible" — a pending TradeProposal, which by construction already
    cleared `evaluate_opportunity()`'s real gate.
  - "insufficient_evidence" — research still `in_progress`; there is
    genuinely no verdict yet, so no score is attached.
  - "not_eligible" — a real OpportunityRejection, carrying its own real
    reasons/decision score/EV at the moment it was rejected.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.capital_priority import priority_score
from app.schemas import GameSaveState, OpportunityFeed, OpportunityFeedEntry, OpportunityRejection, ResearchItem, TradeProposal, WarRoomSession
from app.watchlist import SYMBOL_CATEGORY

MAX_WATCHLIST_ENTRIES = 8
MAX_AVOID_ENTRIES = 10

DATA_HONESTY_NOTE = (
    "BEST CURRENT OPPORTUNITIES is the CEO's real pending proposal queue, already ranked by real Priority Score. "
    "WATCHLIST is real research still in progress — genuinely no verdict yet, so no score is shown. AVOID is the "
    "most recent real rejected candidates, each with its own real reasons. This is NOT a whole-universe proactive "
    "scan — only symbols that already have a real candidate, rejection, or in-progress research record appear here; "
    "a symbol with none of those simply has no opinion to report, and is not listed as if it did."
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _best_opportunity_entries(trade_proposals: list[TradeProposal], war_room_sessions: list[WarRoomSession]) -> list[OpportunityFeedEntry]:
    """`trade_proposals` arrives already ranked best-first — see
    `app/nexus.py`'s own `rank_trade_proposals()` call in `tick()` —
    this only formats each one, it does not re-rank."""
    entries: list[OpportunityFeedEntry] = []
    for proposal in trade_proposals:
        session = next((s for s in war_room_sessions if s.proposal_id == proposal.id), None)
        entries.append(
            OpportunityFeedEntry(
                id=proposal.id,
                symbol=proposal.symbol,
                category=proposal.category,
                status="eligible",
                headline=proposal.research_summary,
                decisionScore=priority_score(proposal, war_room_sessions),
                expectedValuePct=session.expected_value.expected_value_pct if session is not None else None,
                confidence=proposal.confidence,
                asOfSimMinutes=proposal.created_sim_minutes,
            )
        )
    return entries


def _watchlist_entries(research: list[ResearchItem]) -> list[OpportunityFeedEntry]:
    """Research still in_progress — genuinely no trade verdict exists
    yet for these, so decisionScore/expectedValuePct stay None rather
    than borrowing a number from anywhere else."""
    in_progress = [item for item in research if item.status == "in_progress" and item.symbol is not None]
    # Highest-confidence-so-far first — a real, honest "closest to a
    # conclusion" ordering, never presented as a trade score.
    in_progress.sort(key=lambda item: item.confidence, reverse=True)
    entries = [
        OpportunityFeedEntry(
            id=item.id,
            symbol=item.symbol or "",
            category=item.category,
            status="insufficient_evidence",
            headline=item.summary,
            confidence=item.confidence,
        )
        for item in in_progress[:MAX_WATCHLIST_ENTRIES]
    ]
    return entries


def _avoid_entries(opportunity_rejections: list[OpportunityRejection]) -> list[OpportunityFeedEntry]:
    """Most recent rejections first, each with its own real reasons —
    never re-scored, never re-labeled from what the gate actually said
    at rejection time, even if it later resolved `would_have_won`."""
    recent = sorted(opportunity_rejections, key=lambda r: r.rejected_sim_minutes, reverse=True)[:MAX_AVOID_ENTRIES]
    return [
        OpportunityFeedEntry(
            id=rejection.id,
            symbol=rejection.symbol,
            # OpportunityRejection doesn't carry its own category field —
            # this is the real symbol -> category lookup (app/watchlist.py's
            # SYMBOL_CATEGORY, now covering EXTRA_SYMBOL_POOL too), not a
            # fabricated value. Every symbol that can reach a rejection
            # came from the watchlist, so this should always resolve; the
            # "stock" fallback is defensive only, for a symbol no longer
            # on any known pool.
            category=SYMBOL_CATEGORY.get(rejection.symbol, "stock"),
            status="not_eligible",
            headline=rejection.reasons[0] if rejection.reasons else "Rejected by the opportunity gate.",
            decisionScore=rejection.decision_score_at_rejection,
            expectedValuePct=rejection.expected_value_at_rejection_pct,
            reasons=rejection.reasons,
            asOfSimMinutes=rejection.rejected_sim_minutes,
        )
        for rejection in recent
    ]


def compute_opportunity_feed(state: GameSaveState) -> OpportunityFeed:
    """The one real entry point. Pure read over already-persisted real
    state — see this module's own docstring for the exact honesty
    boundary on each bucket."""
    return OpportunityFeed(
        bestOpportunities=_best_opportunity_entries(state.trade_proposals, state.war_room_sessions),
        watchlist=_watchlist_entries(state.research),
        avoid=_avoid_entries(state.opportunity_rejections),
        dataHonestyNote=DATA_HONESTY_NOTE,
        computedAt=_now_iso(),
    )
