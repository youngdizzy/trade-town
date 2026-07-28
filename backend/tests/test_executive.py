"""Covers app/executive.py — v0.6.3 Feature 12, the CEO Approval pipeline.
Every analyst vote must trace back to a real signal (trend/volatility,
researcher-vote convention, a real RiskWarning, a real ScannerAlert) —
never a bare opinion — and grading a CEO decision must never fabricate an
outcome for a trade that was never actually placed.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.executive import (
    MAX_PENDING_PROPOSALS,
    _execution_vote,
    _risk_vote,
    _sentiment_vote,
    _technical_vote,
    expire_stale_proposals,
    generate_proposal,
    grade_ceo_decisions,
    resolve_proposal,
)
from app.market_data import Candle, MockMarketDataProvider
from app.portfolio import default_portfolio
from app.schemas import (
    AnalystVote,
    CeoDecisionRecord,
    DecisionConfidence,
    GatekeeperVerdict,
    PaperTrade,
    RiskLimits,
    RiskWarning,
    ResearchItem,
    ScannerAlert,
    TradeProposal,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _research_item(symbol: str = "NEXA", confidence: float = 90.0) -> ResearchItem:
    return ResearchItem(
        id="research-1",
        title="NEXA breakout setup",
        symbol=symbol,
        category="stock",
        priority="high",
        status="completed",
        assignedAgent="nova",
        summary="NEXA is showing a real breakout pattern.",
        confidence=confidence,
        createdAt=_now_iso(),
        updatedAt=_now_iso(),
    )


def _uptrend_candles() -> list[Candle]:
    return [
        Candle(symbol="NEXA", timeframe="1h", timestamp=f"t{i}", open=100 + i, high=101 + i, low=99 + i, close=100 + i, volume=1000, data_status="simulated")
        for i in range(30)
    ]


def _flat_candles() -> list[Candle]:
    return [
        Candle(symbol="NEXA", timeframe="1h", timestamp=f"t{i}", open=100, high=100.2, low=99.8, close=100, volume=1000, data_status="simulated")
        for i in range(30)
    ]


def _vote(role: str, choice: str) -> AnalystVote:
    return AnalystVote(role=role, agentId="echo", choice=choice, reasoning="test", evidence=["test"])  # type: ignore[arg-type]


class TestTechnicalVote:
    def test_uptrend_votes_buy(self) -> None:
        vote = _technical_vote(_research_item(), _uptrend_candles())
        assert vote.choice == "buy"
        assert vote.role == "technical"
        assert vote.agent_id == "echo"

    def test_flat_market_votes_wait(self) -> None:
        vote = _technical_vote(_research_item(), _flat_candles())
        assert vote.choice == "wait"


class TestSentimentVote:
    def test_no_alerts_waits(self) -> None:
        vote = _sentiment_vote("NEXA", [])
        assert vote.choice == "wait"

    def test_gap_up_votes_buy(self) -> None:
        alert = ScannerAlert(id="a1", symbol="NEXA", alertType="gap_up", message="NEXA gapped up.", detectedBy="pulse", createdAt=_now_iso())
        vote = _sentiment_vote("NEXA", [alert])
        assert vote.choice == "buy"

    def test_gap_down_votes_sell(self) -> None:
        alert = ScannerAlert(id="a1", symbol="NEXA", alertType="gap_down", message="NEXA gapped down.", detectedBy="pulse", createdAt=_now_iso())
        vote = _sentiment_vote("NEXA", [alert])
        assert vote.choice == "sell"


class TestRiskVote:
    def test_no_warning_votes_buy(self) -> None:
        vote = _risk_vote("NEXA", None, None)
        assert vote.choice == "buy"

    def test_warning_votes_wait(self) -> None:
        warning = RiskWarning(id="w1", symbol="NEXA", severity="warning", message="Too risky.", createdAt=_now_iso())
        vote = _risk_vote("NEXA", warning, None)
        assert vote.choice == "wait"


class TestExecutionVote:
    def test_majority_buy(self) -> None:
        votes = [_vote("technical", "buy"), _vote("news", "buy"), _vote("macro", "sell"), _vote("risk", "buy"), _vote("sentiment", "wait")]
        execution, overall = _execution_vote(votes)
        assert overall == "buy"
        assert execution.choice == "buy"
        assert execution.role == "execution"

    def test_buy_sell_tie_breaks_to_wait(self) -> None:
        votes = [_vote("technical", "buy"), _vote("news", "sell"), _vote("macro", "wait")]
        _, overall = _execution_vote(votes)
        assert overall == "wait"

    def test_all_wait(self) -> None:
        votes = [_vote("technical", "wait"), _vote("news", "wait")]
        _, overall = _execution_vote(votes)
        assert overall == "wait"


class TestGenerateProposal:
    def test_generates_six_votes_with_overall_recommendation(self) -> None:
        item = _research_item()
        provider = MockMarketDataProvider()
        proposal = generate_proposal(
            item,
            quantity=10.0,
            price=100.0,
            news=[],
            scanner_alerts=[],
            sentinel_warning=None,
            guardian_warning=None,
            provider=provider,
            now_sim_minutes=1440,
            portfolio=default_portfolio(),
            risk_limits=RiskLimits(),
        )
        assert proposal.symbol == "NEXA"
        assert len(proposal.analyst_votes) == 6
        roles = {v.role for v in proposal.analyst_votes}
        assert roles == {"technical", "news", "macro", "risk", "sentiment", "execution"}
        assert proposal.overall_recommendation in ("buy", "sell", "wait")
        assert proposal.created_sim_minutes == 1440


class TestResolveProposal:
    def _proposal(self) -> TradeProposal:
        item = _research_item()
        provider = MockMarketDataProvider()
        return generate_proposal(
            item,
            quantity=10.0,
            price=100.0,
            news=[],
            scanner_alerts=[],
            sentinel_warning=None,
            guardian_warning=None,
            provider=provider,
            now_sim_minutes=0,
            portfolio=default_portfolio(),
            risk_limits=RiskLimits(),
        )

    @staticmethod
    def _stub_approved_verdict(*_args: object, **_kwargs: object) -> GatekeeperVerdict:
        """These two tests exercise resolve_proposal's own order-placement
        mechanics (Feature 12), not the Gatekeeper's approve/reject logic
        (Feature 20, covered in its own test_gatekeeper.py) — the desk's
        analyst votes are genuinely randomized (see voting.py's
        researcher_vote), so without stubbing this out an unlucky roll
        would make the Gatekeeper reject and these assertions flaky."""
        return GatekeeperVerdict(approved=True, checks=[], summary="APPROVED — stubbed for this test.", createdAt=_now_iso())

    def test_buy_opens_a_real_long_position(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.executive.evaluate_gatekeeper", self._stub_approved_verdict)
        proposal = self._proposal()
        portfolio = default_portfolio()
        new_portfolio, decision, record = resolve_proposal(
            proposal, "buy", portfolio=portfolio, risk_limits=RiskLimits(), current_price=100.0, now_sim_minutes=100
        )
        assert len(new_portfolio.positions) == 1
        assert new_portfolio.positions[0].side == "buy"
        assert new_portfolio.positions[0].opened_sim_minutes == 100
        assert decision.outcome == "trade"
        assert decision.order_id == new_portfolio.positions[0].id
        assert decision.gatekeeper_verdict is not None and decision.gatekeeper_verdict.approved
        assert record.ceo_decision == "buy"
        assert record.outcome == "pending"

    def test_sell_opens_a_real_short_position(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.executive.evaluate_gatekeeper", self._stub_approved_verdict)
        proposal = self._proposal()
        portfolio = default_portfolio()
        new_portfolio, decision, record = resolve_proposal(
            proposal, "sell", portfolio=portfolio, risk_limits=RiskLimits(), current_price=100.0, now_sim_minutes=100
        )
        assert len(new_portfolio.positions) == 1
        assert new_portfolio.positions[0].side == "sell"
        assert decision.outcome == "trade"
        assert record.ceo_decision == "sell"

    def test_wait_places_no_trade(self) -> None:
        proposal = self._proposal()
        portfolio = default_portfolio()
        new_portfolio, decision, record = resolve_proposal(
            proposal, "wait", portfolio=portfolio, risk_limits=RiskLimits(), current_price=100.0, now_sim_minutes=100
        )
        assert new_portfolio.positions == []
        assert decision.outcome == "no_trade"
        assert decision.order_id is None
        assert record.outcome == "undecidable"

    def test_zero_quantity_falls_back_to_wait(self) -> None:
        proposal = self._proposal()
        # Drain the portfolio so recommended_quantity() computes zero.
        portfolio = default_portfolio().model_copy(update={"cash_balance": 0.0})
        new_portfolio, decision, record = resolve_proposal(
            proposal, "buy", portfolio=portfolio, risk_limits=RiskLimits(), current_price=100.0, now_sim_minutes=100
        )
        assert new_portfolio.positions == []
        assert decision.outcome == "no_trade"
        assert record.ceo_decision == "wait"
        assert record.outcome == "undecidable"

    def test_agreed_with_ai_flag(self) -> None:
        proposal = self._proposal()
        portfolio = default_portfolio()
        forced_recommendation = proposal.model_copy(update={"overall_recommendation": "buy"})
        _, _, agreeing = resolve_proposal(
            forced_recommendation, "buy", portfolio=portfolio, risk_limits=RiskLimits(), current_price=100.0, now_sim_minutes=0
        )
        assert agreeing.agreed_with_ai is True
        _, _, overriding = resolve_proposal(
            forced_recommendation, "sell", portfolio=portfolio, risk_limits=RiskLimits(), current_price=100.0, now_sim_minutes=0
        )
        assert overriding.agreed_with_ai is False


class TestGradeCeoDecisions:
    def _pending_record(self, decision_id: str) -> CeoDecisionRecord:
        return CeoDecisionRecord(
            id=f"ceo-{decision_id}",
            proposalId=f"proposal-{decision_id}",
            symbol="NEXA",
            category="stock",
            aiRecommendation="buy",
            ceoDecision="buy",
            agreedWithAi=True,
            decisionId=decision_id,
            outcome="pending",
            createdAt=_now_iso(),
        )

    def _closed_trade(self, decision_id: str, pnl: float) -> PaperTrade:
        return PaperTrade(
            id=f"trade-{decision_id}",
            symbol="NEXA",
            side="buy",
            quantity=10,
            entryPrice=100.0,
            exitPrice=100.0 + pnl / 10,
            pnl=pnl,
            pnlPct=pnl,
            durationMinutes=60,
            confidence=90.0,
            reason="test",
            marketConditions="test",
            decisionId=decision_id,
            openedAt=_now_iso(),
            closedAt=_now_iso(),
            openedSimMinutes=0,
            closedSimMinutes=60,
        )

    def test_winning_trade_grades_correct(self) -> None:
        record = self._pending_record("decision-1")
        trade = self._closed_trade("decision-1", pnl=50.0)
        graded = grade_ceo_decisions([record], [trade])
        assert graded[0].outcome == "correct"
        assert graded[0].resolved_at is not None

    def test_losing_trade_grades_incorrect(self) -> None:
        record = self._pending_record("decision-1")
        trade = self._closed_trade("decision-1", pnl=-50.0)
        graded = grade_ceo_decisions([record], [trade])
        assert graded[0].outcome == "incorrect"

    def test_no_matching_trade_stays_pending(self) -> None:
        record = self._pending_record("decision-1")
        graded = grade_ceo_decisions([record], [])
        assert graded[0].outcome == "pending"

    def test_already_resolved_untouched(self) -> None:
        record = self._pending_record("decision-1").model_copy(update={"outcome": "undecidable"})
        trade = self._closed_trade("decision-1", pnl=50.0)
        graded = grade_ceo_decisions([record], [trade])
        assert graded[0].outcome == "undecidable"


class TestExpireStaleProposals:
    def _proposal(self, created_sim_minutes: int) -> TradeProposal:
        return TradeProposal(
            id="proposal-1",
            symbol="NEXA",
            category="stock",
            quantity=10.0,
            price=100.0,
            confidence=90.0,
            analystVotes=[],
            overallRecommendation="buy",
            researchSummary="test",
            riskSummary="test",
            confidenceEngine=DecisionConfidence(score=50.0, tier="moderate", summary="test", factors=[]),
            createdAt=_now_iso(),
            createdSimMinutes=created_sim_minutes,
        )

    def test_not_yet_expired(self) -> None:
        proposal = self._proposal(0)
        keep, expired = expire_stale_proposals([proposal], now_sim_minutes=100)
        assert keep == [proposal]
        assert expired == []

    def test_expired_after_threshold(self) -> None:
        proposal = self._proposal(0)
        keep, expired = expire_stale_proposals([proposal], now_sim_minutes=3 * 1440)
        assert keep == []
        assert expired == [proposal]


def test_max_pending_proposals_is_positive() -> None:
    assert MAX_PENDING_PROPOSALS > 0
