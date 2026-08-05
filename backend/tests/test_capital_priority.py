"""Covers app/capital_priority.py — v0.7 Design Bible Chapter 59, the
Capital Priority & Opportunity Cost Engine. Every case here checks the
chapter's two real, new guarantees: the pending queue is ranked by the
same real Priority Score shown everywhere else (never a fabricated
second read), and the CEO's own voluntary capital reserve is genuinely
respected rather than decorative.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.capital_priority import cash_reserve_breached, priority_score, rank_trade_proposals
from app.market_data import Candle
from app.market_intelligence import default_market_intelligence_state
from app.portfolio import default_portfolio
from app.schemas import AnalystVote, ConfidenceFactor, DecisionConfidence, PaperPortfolio, PaperPosition, RiskLimits, TradeProposal, WarRoomSession
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


def _proposal(*, proposal_id: str = "proposal-1", symbol: str = "NEXA", overall: str = "buy") -> TradeProposal:
    return TradeProposal(
        id=proposal_id,
        symbol=symbol,
        category="stock",
        quantity=1.0,
        price=100.0,
        confidence=80.0,
        analystVotes=[AnalystVote(role="risk", agentId="sentinel", choice="buy", reasoning="Within limits.", evidence=["Real risk read"])],  # type: ignore[arg-type]
        overallRecommendation=overall,  # type: ignore[arg-type]
        researchSummary="Nova's research backs this setup.",
        riskSummary="Within all configured risk limits.",
        confidenceEngine=DecisionConfidence(score=80.0, tier="strong", summary="A well-supported setup.", factors=_DEFAULT_FACTORS),  # type: ignore[arg-type]
        createdAt=_now_iso(),
        createdSimMinutes=0,
    )


def _candles(symbol: str = "NEXA") -> list[Candle]:
    return [Candle(symbol=symbol, timeframe="1h", timestamp=f"2026-01-01T{i:02d}:00:00Z", open=100.0, high=101.0, low=99.0, close=100.0, volume=1000.0, data_status="simulated") for i in range(30)]


def _session(proposal: TradeProposal, *, overall: float) -> WarRoomSession:
    """A real, fully-assembled WarRoomSession (via the same
    build_war_room_session every proposal actually gets in app/nexus.py)
    with its decisionScore.overall pinned to a controlled test value —
    the honest way to test ranking without re-deriving the composite's
    real, many-factor computation in every test case."""
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
    )
    return base.model_copy(update={"decision_score": base.decision_score.model_copy(update={"overall": overall})})


def _portfolio(*, cash: float, position_value: float = 0.0) -> PaperPortfolio:
    """A portfolio with a controlled cash-vs-equity split. portfolio_equity()
    (app/risk_engine.py) is cash_balance plus every open position's
    quantity * current_price — so a single real open position of the
    requested value is the honest way to control equity independent of
    cash, rather than faking a second field portfolio_equity doesn't
    actually read."""
    positions = (
        []
        if position_value <= 0
        else [
            PaperPosition(
                id="pos-1",
                symbol="NEXA",
                side="buy",
                quantity=1.0,
                entryPrice=position_value,
                currentPrice=position_value,
                unrealizedPnl=0.0,
                unrealizedPnlPct=0.0,
                openedBy="atlas",
                confidence=80.0,
                openedAt=_now_iso(),
            )
        ]
    )
    return default_portfolio().model_copy(update={"cash_balance": cash, "positions": positions})


class TestPriorityScore:
    def test_returns_the_linked_sessions_overall_score(self) -> None:
        proposal = _proposal()
        session = _session(proposal, overall=77.0)
        assert priority_score(proposal, [session]) == 77.0

    def test_returns_none_when_no_session_is_linked(self) -> None:
        proposal = _proposal()
        assert priority_score(proposal, []) is None

    def test_matches_by_proposal_id_not_list_position(self) -> None:
        proposal_a = _proposal(proposal_id="proposal-a")
        proposal_b = _proposal(proposal_id="proposal-b")
        session_b = _session(proposal_b, overall=60.0)
        assert priority_score(proposal_a, [session_b]) is None
        assert priority_score(proposal_b, [session_b]) == 60.0


class TestRankTradeProposals:
    def test_sorts_highest_score_first(self) -> None:
        low = _proposal(proposal_id="low")
        high = _proposal(proposal_id="high")
        mid = _proposal(proposal_id="mid")
        sessions = [_session(low, overall=30.0), _session(high, overall=95.0), _session(mid, overall=60.0)]
        ranked = rank_trade_proposals([low, high, mid], sessions)
        assert [p.id for p in ranked] == ["high", "mid", "low"]

    def test_equal_scores_keep_arrival_order(self) -> None:
        first = _proposal(proposal_id="first")
        second = _proposal(proposal_id="second")
        sessions = [_session(first, overall=50.0), _session(second, overall=50.0)]
        ranked = rank_trade_proposals([first, second], sessions)
        assert [p.id for p in ranked] == ["first", "second"]

    def test_proposal_without_a_session_sorts_last(self) -> None:
        scored = _proposal(proposal_id="scored")
        unscored = _proposal(proposal_id="unscored")
        sessions = [_session(scored, overall=1.0)]
        ranked = rank_trade_proposals([unscored, scored], sessions)
        assert [p.id for p in ranked] == ["scored", "unscored"]

    def test_empty_queue_returns_empty_list(self) -> None:
        assert rank_trade_proposals([], []) == []


class TestCashReserveBreached:
    def test_default_capital_reserve_pct_never_breaches(self) -> None:
        portfolio = _portfolio(cash=80_000.0, position_value=20_000.0)
        assert cash_reserve_breached(portfolio, RiskLimits()) is False

    def test_false_when_cash_is_comfortably_above_the_reserve_target(self) -> None:
        # $50k cash on $100k equity = 50% cash, well above a 20% target.
        portfolio = _portfolio(cash=50_000.0, position_value=50_000.0)
        assert cash_reserve_breached(portfolio, RiskLimits(capitalReservePct=20.0)) is False

    def test_true_when_cash_pct_has_fallen_to_the_reserve_target(self) -> None:
        # $20k cash on $100k equity = exactly 20%.
        portfolio = _portfolio(cash=20_000.0, position_value=80_000.0)
        assert cash_reserve_breached(portfolio, RiskLimits(capitalReservePct=20.0)) is True

    def test_true_when_cash_pct_has_fallen_below_the_reserve_target(self) -> None:
        # $5k cash on $100k equity = 5%, below a 20% target.
        portfolio = _portfolio(cash=5_000.0, position_value=95_000.0)
        assert cash_reserve_breached(portfolio, RiskLimits(capitalReservePct=20.0)) is True

    def test_zero_equity_does_not_crash(self) -> None:
        portfolio = _portfolio(cash=0.0, position_value=0.0)
        assert cash_reserve_breached(portfolio, RiskLimits(capitalReservePct=20.0)) is False
