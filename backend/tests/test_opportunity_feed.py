"""Covers app/opportunity_feed.py — CEO directive "Professional Quant
Trading Core," Rule 25/26's CEO Opportunity Feed. Every assertion checks
that a bucket surfaces exactly the real, already-computed evidence it
claims to (a proposal's real linked Priority Score, a rejection's own
real reasons, in-progress research's honest lack of a score) — never a
fabricated number for a candidate that was never actually evaluated.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.market_data import Candle
from app.market_intelligence import default_market_intelligence_state
from app.opportunity_feed import compute_opportunity_feed
from app.schemas import AnalystVote, ConfidenceFactor, DecisionConfidence, OpportunityRejection, ResearchItem, RiskLimits, TradeProposal
from app.state import default_state
from app.war_room import build_war_room_session


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_DEFAULT_FACTORS = [
    ConfidenceFactor(name="Multi-Agent Agreement", score=80.0, weight=0.30, detail="d"),
    ConfidenceFactor(name="Technical Alignment", score=80.0, weight=0.20, detail="d"),
    ConfidenceFactor(name="Risk Conditions", score=80.0, weight=0.20, detail="d"),
    ConfidenceFactor(name="Research Confidence", score=80.0, weight=0.15, detail="d"),
    ConfidenceFactor(name="News, Macro & Sentiment", score=80.0, weight=0.10, detail="d"),
    ConfidenceFactor(name="Portfolio Exposure", score=80.0, weight=0.05, detail="d"),
]


def _proposal(*, proposal_id: str = "proposal-1", symbol: str = "AAPL", created_sim_minutes: int = 100) -> TradeProposal:
    return TradeProposal(
        id=proposal_id,
        symbol=symbol,
        category="company",  # type: ignore[arg-type]
        quantity=1.0,
        price=100.0,
        confidence=80.0,
        analystVotes=[AnalystVote(role="risk", agentId="sentinel", choice="buy", reasoning="Within limits.", evidence=["Real risk read"])],  # type: ignore[arg-type]
        overallRecommendation="buy",  # type: ignore[arg-type]
        researchSummary="Nova's research backs this setup.",
        riskSummary="Within all configured risk limits.",
        confidenceEngine=DecisionConfidence(score=80.0, tier="strong", summary="A well-supported setup.", factors=_DEFAULT_FACTORS),  # type: ignore[arg-type]
        createdAt=_now_iso(),
        createdSimMinutes=created_sim_minutes,
    )


def _candles(symbol: str) -> list[Candle]:
    return [
        Candle(symbol=symbol, timeframe="1h", timestamp=f"2026-01-01T{i:02d}:00:00Z", open=100.0, high=101.0, low=99.0, close=100.0, volume=1000.0, data_status="simulated")
        for i in range(30)
    ]


def _session(proposal: TradeProposal, *, overall: float, ev_pct: float):
    base = build_war_room_session(
        f"warroom-{proposal.id}",
        proposal,
        challenge_report=None,
        coach_reports=[],
        market_intelligence=default_market_intelligence_state(),
        decision_vault=[],
        risk_warnings=[],
        correlated_open_positions=0,
        candles=_candles(proposal.symbol),
        risk_limits=RiskLimits(),
    )
    return base.model_copy(
        update={
            "decision_score": base.decision_score.model_copy(update={"overall": overall}),
            "expected_value": base.expected_value.model_copy(update={"expected_value_pct": ev_pct}),
        }
    )


def _research_item(status: str, symbol: str = "MSFT", confidence: float = 40.0) -> ResearchItem:
    return ResearchItem(
        id=f"research-{symbol}-{status}",
        title="Test research",
        symbol=symbol,
        category="stock",  # type: ignore[arg-type]
        priority="normal",
        status=status,  # type: ignore[arg-type]
        assignedAgent="nova",  # type: ignore[arg-type]
        summary="Checking momentum.",
        confidence=confidence,
        createdAt=_now_iso(),
        updatedAt=_now_iso(),
    )


def _opportunity_rejection(*, symbol: str = "GLD", rejected_sim_minutes: int, decision_score: float = 55.0) -> OpportunityRejection:
    return OpportunityRejection(
        id=f"oppreject-{symbol}-{rejected_sim_minutes}",
        symbol=symbol,
        wouldHaveRecommended="buy",  # type: ignore[arg-type]
        reasons=["Trade Quality Score below the 70.0 threshold."],
        reasonCodes=["trade_quality_below_threshold"],  # type: ignore[arg-type]
        decisionScoreAtRejection=decision_score,
        expectedValueAtRejectionPct=-0.5,
        priceAtRejection=100.0,
        rejectedSimMinutes=rejected_sim_minutes,
        createdAt=_now_iso(),
    )


class TestBestOpportunities:
    def test_a_pending_proposal_with_a_linked_session_carries_its_real_score(self) -> None:
        proposal = _proposal()
        session = _session(proposal, overall=82.0, ev_pct=3.5)
        state = default_state().model_copy(update={"trade_proposals": [proposal], "war_room_sessions": [session]})
        feed = compute_opportunity_feed(state)
        assert len(feed.best_opportunities) == 1
        entry = feed.best_opportunities[0]
        assert entry.symbol == "AAPL"
        assert entry.status == "eligible"
        assert entry.decision_score == 82.0
        assert entry.expected_value_pct == 3.5
        assert entry.as_of_sim_minutes == 100

    def test_a_proposal_with_no_linked_session_has_no_fabricated_score(self) -> None:
        proposal = _proposal()
        state = default_state().model_copy(update={"trade_proposals": [proposal], "war_room_sessions": []})
        feed = compute_opportunity_feed(state)
        entry = feed.best_opportunities[0]
        assert entry.decision_score is None
        assert entry.expected_value_pct is None

    def test_preserves_the_already_ranked_arrival_order(self) -> None:
        # trade_proposals arrives already ranked by nexus.py's own
        # rank_trade_proposals() — this module must not re-sort it by
        # something else and silently disagree with the CEO's real queue order.
        low = _proposal(proposal_id="low", symbol="MSFT")
        high = _proposal(proposal_id="high", symbol="AAPL")
        state = default_state().model_copy(update={"trade_proposals": [high, low]})
        feed = compute_opportunity_feed(state)
        assert [e.id for e in feed.best_opportunities] == ["high", "low"]


class TestWatchlist:
    def test_only_in_progress_research_appears_never_completed(self) -> None:
        state = default_state().model_copy(update={"research": [_research_item("in_progress", "MSFT"), _research_item("completed", "GOOGL")]})
        feed = compute_opportunity_feed(state)
        assert [e.symbol for e in feed.watchlist] == ["MSFT"]

    def test_watchlist_entries_carry_no_fabricated_score(self) -> None:
        state = default_state().model_copy(update={"research": [_research_item("in_progress")]})
        feed = compute_opportunity_feed(state)
        entry = feed.watchlist[0]
        assert entry.status == "insufficient_evidence"
        assert entry.decision_score is None
        assert entry.expected_value_pct is None
        assert entry.as_of_sim_minutes is None

    def test_sorted_by_confidence_so_far_highest_first(self) -> None:
        state = default_state().model_copy(
            update={"research": [_research_item("in_progress", "MSFT", confidence=20.0), _research_item("in_progress", "GOOGL", confidence=90.0)]}
        )
        feed = compute_opportunity_feed(state)
        assert [e.symbol for e in feed.watchlist] == ["GOOGL", "MSFT"]


class TestAvoid:
    def test_carries_the_rejections_own_real_reasons_and_score(self) -> None:
        rejection = _opportunity_rejection(rejected_sim_minutes=500, decision_score=42.0)
        state = default_state().model_copy(update={"opportunity_rejections": [rejection]})
        feed = compute_opportunity_feed(state)
        entry = feed.avoid[0]
        assert entry.status == "not_eligible"
        assert entry.decision_score == 42.0
        assert entry.reasons == rejection.reasons
        assert entry.headline == rejection.reasons[0]

    def test_most_recent_rejection_first(self) -> None:
        old = _opportunity_rejection(symbol="AAPL", rejected_sim_minutes=100)
        new = _opportunity_rejection(symbol="MSFT", rejected_sim_minutes=900)
        state = default_state().model_copy(update={"opportunity_rejections": [old, new]})
        feed = compute_opportunity_feed(state)
        assert [e.symbol for e in feed.avoid] == ["MSFT", "AAPL"]

    def test_caps_at_the_max_avoid_entries(self) -> None:
        rejections = [_opportunity_rejection(symbol="AAPL", rejected_sim_minutes=i) for i in range(20)]
        state = default_state().model_copy(update={"opportunity_rejections": rejections})
        feed = compute_opportunity_feed(state)
        assert len(feed.avoid) == 10

    def test_real_symbol_category_lookup_not_a_fabricated_default(self) -> None:
        rejection = _opportunity_rejection(symbol="GLD", rejected_sim_minutes=1)
        state = default_state().model_copy(update={"opportunity_rejections": [rejection]})
        feed = compute_opportunity_feed(state)
        assert feed.avoid[0].category == "gold"


class TestFreshState:
    def test_empty_state_returns_empty_buckets_not_a_crash(self) -> None:
        feed = compute_opportunity_feed(default_state())
        assert feed.best_opportunities == []
        assert feed.avoid == []
        # default_state() seeds 4 in-progress research items (one per researcher).
        assert len(feed.watchlist) == 4

    def test_data_honesty_note_discloses_the_scope_boundary(self) -> None:
        feed = compute_opportunity_feed(default_state())
        assert "not" in feed.data_honesty_note.lower()
        assert "whole-universe" in feed.data_honesty_note.lower()
