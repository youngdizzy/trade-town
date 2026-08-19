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
    MAX_PROPOSAL_HOLDS,
    _execution_vote,
    _risk_vote,
    _sentiment_vote,
    _technical_vote,
    compute_decision_grade,
    expire_stale_proposals,
    generate_proposal,
    grade_ceo_decisions,
    hold_proposal,
    is_significant_proposal,
    resolve_proposal,
)
from app.gatekeeper import MIN_CONFIDENCE
from app.market_data import Candle, MockMarketDataProvider
from app.market_intelligence import default_market_intelligence_state
from app.portfolio import default_portfolio
from app.schemas import (
    AnalystVote,
    CeoDecisionRecord,
    ConfidenceFactor,
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
            market_intelligence=default_market_intelligence_state(),
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
            market_intelligence=default_market_intelligence_state(),
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
            proposal, "buy", portfolio=portfolio, risk_limits=RiskLimits(), current_price=100.0, now_sim_minutes=100, market_intelligence=default_market_intelligence_state()
        )
        assert len(new_portfolio.positions) == 1
        assert new_portfolio.positions[0].side == "buy"
        assert new_portfolio.positions[0].opened_sim_minutes == 100
        assert decision.outcome == "trade"
        assert decision.order_id == new_portfolio.positions[0].id
        assert decision.gatekeeper_verdict is not None and decision.gatekeeper_verdict.approved
        assert record.ceo_decision == "buy"
        assert record.outcome == "pending"
        assert record.resolved_by == "ceo"

    def test_resolved_by_defaults_to_ceo_but_can_be_tagged_auto(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """v0.7 Feature 21 — a mode auto-resolution passes resolved_by="auto"
        explicitly; every real player click via /api/executive/decide
        relies on the default, which must stay "ceo"."""
        monkeypatch.setattr("app.executive.evaluate_gatekeeper", self._stub_approved_verdict)
        proposal = self._proposal()
        portfolio = default_portfolio()
        _, _, auto_record = resolve_proposal(
            proposal, "buy", portfolio=portfolio, risk_limits=RiskLimits(), current_price=100.0, now_sim_minutes=100, market_intelligence=default_market_intelligence_state(), resolved_by="auto"
        )
        assert auto_record.resolved_by == "auto"

    def test_sell_opens_a_real_short_position(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.executive.evaluate_gatekeeper", self._stub_approved_verdict)
        proposal = self._proposal()
        portfolio = default_portfolio()
        new_portfolio, decision, record = resolve_proposal(
            proposal, "sell", portfolio=portfolio, risk_limits=RiskLimits(), current_price=100.0, now_sim_minutes=100, market_intelligence=default_market_intelligence_state()
        )
        assert len(new_portfolio.positions) == 1
        assert new_portfolio.positions[0].side == "sell"
        assert decision.outcome == "trade"
        assert record.ceo_decision == "sell"

    def test_a_buy_fills_with_real_slippage_worse_than_the_real_signal_price(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """CEO directive "Next Professional Trading Firm Phase," Priority
        1 (Execution Realism) — the CEO's own direct buy is a
        market-style instant fill, so it gets real, disclosed slippage
        via app/execution_quality.py just like a "market" order placed
        through app/broker.py does."""
        monkeypatch.setattr("app.executive.evaluate_gatekeeper", self._stub_approved_verdict)
        proposal = self._proposal()
        portfolio = default_portfolio()
        new_portfolio, _, _ = resolve_proposal(
            proposal, "buy", portfolio=portfolio, risk_limits=RiskLimits(), current_price=100.0, now_sim_minutes=100, market_intelligence=default_market_intelligence_state()
        )
        assert new_portfolio.positions[0].entry_price > 100.0
        assert new_portfolio.positions[0].entry_slippage_bps > 0.0

    def test_a_sell_fills_with_real_slippage_worse_than_the_real_signal_price(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.executive.evaluate_gatekeeper", self._stub_approved_verdict)
        proposal = self._proposal()
        portfolio = default_portfolio()
        new_portfolio, _, _ = resolve_proposal(
            proposal, "sell", portfolio=portfolio, risk_limits=RiskLimits(), current_price=100.0, now_sim_minutes=100, market_intelligence=default_market_intelligence_state()
        )
        assert new_portfolio.positions[0].entry_price < 100.0
        assert new_portfolio.positions[0].entry_slippage_bps > 0.0

    def test_wait_places_no_trade(self) -> None:
        proposal = self._proposal()
        portfolio = default_portfolio()
        new_portfolio, decision, record = resolve_proposal(
            proposal, "wait", portfolio=portfolio, risk_limits=RiskLimits(), current_price=100.0, now_sim_minutes=100, market_intelligence=default_market_intelligence_state()
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
            proposal, "buy", portfolio=portfolio, risk_limits=RiskLimits(), current_price=100.0, now_sim_minutes=100, market_intelligence=default_market_intelligence_state()
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
            forced_recommendation, "buy", portfolio=portfolio, risk_limits=RiskLimits(), current_price=100.0, now_sim_minutes=0, market_intelligence=default_market_intelligence_state()
        )
        assert agreeing.agreed_with_ai is True
        _, _, overriding = resolve_proposal(
            forced_recommendation, "sell", portfolio=portfolio, risk_limits=RiskLimits(), current_price=100.0, now_sim_minutes=0, market_intelligence=default_market_intelligence_state()
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


class TestHoldProposal:
    def _proposal(self, created_sim_minutes: int, hold_count: int = 0) -> TradeProposal:
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
            holdCount=hold_count,
        )

    def test_resets_the_expiry_clock(self) -> None:
        proposal = self._proposal(0)
        held = hold_proposal(proposal, now_sim_minutes=500)
        assert held is not None
        assert held.created_sim_minutes == 500

    def test_increments_hold_count(self) -> None:
        proposal = self._proposal(0, hold_count=0)
        held = hold_proposal(proposal, now_sim_minutes=100)
        assert held is not None
        assert held.hold_count == 1

    def test_never_resolves_to_a_decision(self) -> None:
        proposal = self._proposal(0)
        held = hold_proposal(proposal, now_sim_minutes=100)
        assert held is not None
        # Same real fields, still pending — nothing about the proposal's
        # own trade content changed, only its clock and hold count.
        assert held.symbol == proposal.symbol
        assert held.overall_recommendation == proposal.overall_recommendation

    def test_capped_at_max_holds(self) -> None:
        proposal = self._proposal(0, hold_count=MAX_PROPOSAL_HOLDS)
        held = hold_proposal(proposal, now_sim_minutes=100)
        assert held is None

    def test_allows_exactly_max_holds(self) -> None:
        proposal = self._proposal(0, hold_count=MAX_PROPOSAL_HOLDS - 1)
        held = hold_proposal(proposal, now_sim_minutes=100)
        assert held is not None
        assert held.hold_count == MAX_PROPOSAL_HOLDS


def test_max_pending_proposals_is_positive() -> None:
    assert MAX_PENDING_PROPOSALS > 0


class TestIsSignificantProposal:
    def _proposal(self, *, confidence_score: float = 90.0, overall: str = "buy", quantity: float = 1.0, price: float = 100.0, symbol: str = "NEXA") -> TradeProposal:
        return TradeProposal(
            id="proposal-1",
            symbol=symbol,
            category="stock",
            quantity=quantity,
            price=price,
            confidence=90.0,
            analystVotes=[],
            overallRecommendation=overall,  # type: ignore[arg-type]
            researchSummary="test",
            riskSummary="test",
            confidenceEngine=DecisionConfidence(score=confidence_score, tier="strong", summary="test", factors=[]),
            createdAt=_now_iso(),
            createdSimMinutes=0,
        )

    def test_wait_recommendation_is_never_significant(self) -> None:
        proposal = self._proposal(overall="wait", confidence_score=10.0)
        significant, reasons = is_significant_proposal(proposal, default_portfolio(), RiskLimits(), [])
        assert significant is False
        assert reasons == []

    def test_high_confidence_small_size_no_warnings_is_not_significant(self) -> None:
        proposal = self._proposal(confidence_score=95.0, quantity=1.0, price=10.0)
        significant, reasons = is_significant_proposal(proposal, default_portfolio(), RiskLimits(), [])
        assert significant is False
        assert reasons == []

    def test_low_confidence_is_significant(self) -> None:
        proposal = self._proposal(confidence_score=MIN_CONFIDENCE - 1)
        significant, reasons = is_significant_proposal(proposal, default_portfolio(), RiskLimits(), [])
        assert significant is True
        assert any("Confidence" in r for r in reasons)

    def test_active_critical_risk_warning_on_the_symbol_is_significant(self) -> None:
        proposal = self._proposal(confidence_score=95.0, symbol="NEXA")
        warning = RiskWarning(id="w1", symbol="NEXA", severity="critical", message="Too concentrated.", createdAt=_now_iso())
        significant, reasons = is_significant_proposal(proposal, default_portfolio(), RiskLimits(), [warning])
        assert significant is True
        assert any("risk warning" in r for r in reasons)

    def test_critical_warning_on_a_different_symbol_does_not_count(self) -> None:
        proposal = self._proposal(confidence_score=95.0, symbol="NEXA")
        warning = RiskWarning(id="w1", symbol="OTHER", severity="critical", message="Too concentrated.", createdAt=_now_iso())
        significant, reasons = is_significant_proposal(proposal, default_portfolio(), RiskLimits(), [warning])
        assert significant is False
        assert reasons == []

    def test_large_position_relative_to_equity_is_significant(self) -> None:
        # Default portfolio starts at $100,000 equity; maxPositionPct
        # defaults to 10 — a $20,000 notional (20%) is well above it.
        proposal = self._proposal(confidence_score=95.0, quantity=200.0, price=100.0)
        significant, reasons = is_significant_proposal(proposal, default_portfolio(), RiskLimits(), [])
        assert significant is True
        assert any("Position size" in r for r in reasons)

    def test_priority_score_below_ceo_floor_is_significant(self) -> None:
        # v0.7 Chapter 59 — a real, CEO-raised Minimum Priority Score.
        proposal = self._proposal(confidence_score=95.0, quantity=1.0, price=10.0)
        significant, reasons = is_significant_proposal(proposal, default_portfolio(), RiskLimits(minPriorityScore=70.0), [], 55.0)
        assert significant is True
        assert any("Priority Score" in r for r in reasons)

    def test_priority_score_at_or_above_ceo_floor_is_not_significant(self) -> None:
        proposal = self._proposal(confidence_score=95.0, quantity=1.0, price=10.0)
        significant, reasons = is_significant_proposal(proposal, default_portfolio(), RiskLimits(minPriorityScore=70.0), [], 70.0)
        assert significant is False
        assert reasons == []

    def test_default_priority_floor_of_zero_never_flags_a_real_score(self) -> None:
        proposal = self._proposal(confidence_score=95.0, quantity=1.0, price=10.0)
        significant, reasons = is_significant_proposal(proposal, default_portfolio(), RiskLimits(), [], 1.0)
        assert significant is False
        assert reasons == []

    def test_missing_priority_score_is_never_flagged(self) -> None:
        # No War Room session to look a score up from — is_significant_
        # proposal never fabricates one; the check simply doesn't run.
        proposal = self._proposal(confidence_score=95.0, quantity=1.0, price=10.0)
        significant, reasons = is_significant_proposal(proposal, default_portfolio(), RiskLimits(minPriorityScore=70.0), [], None)
        assert significant is False
        assert reasons == []


def _grade_proposal(*, score: float = 90.0, agreeing_votes: int = 6, total_votes: int = 6) -> TradeProposal:
    """v0.7 Feature 50 (Part 2/3) — a deterministic TradeProposal for
    compute_decision_grade, unlike generate_proposal's real randomized
    votes above."""
    votes = [AnalystVote(role="technical", agentId="echo", choice="buy", reasoning="x", evidence=["x"]) for _ in range(agreeing_votes)]  # type: ignore[arg-type]
    votes += [AnalystVote(role="risk", agentId="sentinel", choice="wait", reasoning="x", evidence=["x"]) for _ in range(total_votes - agreeing_votes)]  # type: ignore[arg-type]
    return TradeProposal(
        id="p1",
        symbol="NEXA",
        category="stock",
        quantity=1.0,
        price=100.0,
        confidence=score,
        analystVotes=votes,
        overallRecommendation="buy",
        researchSummary="x",
        riskSummary="x",
        confidenceEngine=DecisionConfidence(score=score, tier="strong", summary="x", factors=[ConfidenceFactor(name="technical", score=score, weight=1.0, detail="x")]),  # type: ignore[arg-type]
        createdAt=_now_iso(),
        createdSimMinutes=0,
    )


class TestComputeDecisionGrade:
    def test_perfect_confidence_full_agreement_approved_gatekeeper_is_a_plus(self) -> None:
        proposal = _grade_proposal(score=100.0, agreeing_votes=6, total_votes=6)
        verdict = GatekeeperVerdict(approved=True, checks=[], summary="x", createdAt=_now_iso())
        grade, score = compute_decision_grade(proposal, verdict)
        assert grade == "A+"
        assert score == 100.0

    def test_never_reads_the_trades_own_pnl(self) -> None:
        """Same inputs, same grade, regardless of anything trade-outcome
        related — compute_decision_grade takes no P&L parameter at all,
        so this is really just documenting the contract via a type-level
        check: the function signature itself has no such input."""
        proposal = _grade_proposal(score=80.0, agreeing_votes=4, total_votes=6)
        grade_a, score_a = compute_decision_grade(proposal, None)
        grade_b, score_b = compute_decision_grade(proposal, None)
        assert (grade_a, score_a) == (grade_b, score_b)

    def test_gatekeeper_rejection_pulls_the_grade_down(self) -> None:
        proposal = _grade_proposal(score=95.0, agreeing_votes=6, total_votes=6)
        approved = GatekeeperVerdict(approved=True, checks=[], summary="x", createdAt=_now_iso())
        rejected = GatekeeperVerdict(approved=False, checks=[], summary="x", createdAt=_now_iso())
        _, approved_score = compute_decision_grade(proposal, approved)
        _, rejected_score = compute_decision_grade(proposal, rejected)
        assert rejected_score < approved_score

    def test_no_gatekeeper_verdict_is_not_penalized(self) -> None:
        """A WAIT never reaches the Gatekeeper (see resolve_proposal) —
        None must score identically to an approved verdict, never like a
        rejected one."""
        proposal = _grade_proposal(score=95.0, agreeing_votes=6, total_votes=6)
        approved = GatekeeperVerdict(approved=True, checks=[], summary="x", createdAt=_now_iso())
        _, none_score = compute_decision_grade(proposal, None)
        _, approved_score = compute_decision_grade(proposal, approved)
        assert none_score == approved_score

    def test_low_confidence_weak_agreement_rejected_is_an_f(self) -> None:
        proposal = _grade_proposal(score=20.0, agreeing_votes=1, total_votes=6)
        rejected = GatekeeperVerdict(approved=False, checks=[], summary="x", createdAt=_now_iso())
        grade, _ = compute_decision_grade(proposal, rejected)
        assert grade == "F"

    def test_grade_letter_matches_the_composite_score_thresholds(self) -> None:
        # 50% confidence * 0.5 + 100% agreement * 0.25 + 100% gatekeeper
        # * 0.25 == 25 + 25 + 25 == 75, which is squarely a real "C".
        proposal = _grade_proposal(score=50.0, agreeing_votes=6, total_votes=6)
        approved = GatekeeperVerdict(approved=True, checks=[], summary="x", createdAt=_now_iso())
        grade, score = compute_decision_grade(proposal, approved)
        assert score == 75.0
        assert grade == "C"

    def test_resolve_proposal_attaches_a_real_grade_to_the_decision(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr("app.executive.evaluate_gatekeeper", TestResolveProposal._stub_approved_verdict)
        proposal = TestResolveProposal()._proposal()
        _, decision, _ = resolve_proposal(proposal, "buy", portfolio=default_portfolio(), risk_limits=RiskLimits(), current_price=100.0, now_sim_minutes=100, market_intelligence=default_market_intelligence_state())
        assert decision.decision_grade is not None
        assert decision.decision_grade_score is not None
        expected_grade, expected_score = compute_decision_grade(proposal, decision.gatekeeper_verdict)
        assert decision.decision_grade == expected_grade
        assert decision.decision_grade_score == expected_score
