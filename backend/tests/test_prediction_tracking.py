"""Covers app/prediction_tracking.py — CEO directive "Features 26-30,"
Feature 29 (Prediction -> Outcome Tracking). A prediction must only ever
be built from a real trade-causing decision (never a "wait"), must never
resolve early or from stale data, and only a real, notable miscalibration
should be promoted to Institutional Memory.
"""
from __future__ import annotations

from app.prediction_tracking import (
    HIGH_CONFIDENCE_MISS_THRESHOLD,
    build_prediction_record,
    grade_predictions,
    should_promote_prediction_outcome,
)
from app.schemas import AgentId, CeoDecisionRecord, PaperTrade, TradeDecision


def _now_iso() -> str:
    return "2026-01-01T00:00:00+00:00"


def _decision(*, decision_id: str = "decision-1", order_id: str | None = "pos-1", supporting_agents: list[AgentId] | None = None, confidence: float = 80.0) -> TradeDecision:
    return TradeDecision(
        id=decision_id,
        symbol="NEXA",
        outcome="trade" if order_id is not None else "no_trade",
        researchSummary="test",
        technicalSummary="test",
        fundamentalSummary="test",
        riskSummary="test",
        supportingAgents=supporting_agents if supporting_agents is not None else ["scout", "atlas"],
        opposingAgents=[],
        confidence=confidence,
        finalReasoning="test",
        orderId=order_id,
        createdAt=_now_iso(),
    )


def _ceo_record(*, decision_id: str = "decision-1", ceo_decision: str = "buy", outcome: str = "pending") -> CeoDecisionRecord:
    return CeoDecisionRecord(
        id=f"ceo-{decision_id}",
        proposalId="proposal-1",
        symbol="NEXA",
        category="stock",  # type: ignore[arg-type]
        aiRecommendation="buy",  # type: ignore[arg-type]
        ceoDecision=ceo_decision,  # type: ignore[arg-type]
        agreedWithAi=True,
        decisionId=decision_id,
        outcome=outcome,  # type: ignore[arg-type]
        createdAt=_now_iso(),
    )


def _trade(*, trade_id: str = "trade-1", decision_id: str = "decision-1", pnl: float = 5.0, pnl_pct: float = 2.0) -> PaperTrade:
    return PaperTrade(
        id=trade_id,
        symbol="NEXA",
        side="buy",  # type: ignore[arg-type]
        quantity=10.0,
        entryPrice=100.0,
        exitPrice=102.0,
        pnl=pnl,
        pnlPct=pnl_pct,
        durationMinutes=60,
        confidence=80.0,
        reason="test",
        marketConditions="test",
        supportingAgents=["scout", "atlas"],
        openedAt=_now_iso(),
        closedAt=_now_iso(),
        openedSimMinutes=0,
        closedSimMinutes=60,
        decisionId=decision_id,
    )


class TestBuildPredictionRecord:
    def test_no_order_id_means_no_real_claim(self) -> None:
        decision = _decision(order_id=None)
        record = _ceo_record(ceo_decision="wait", outcome="undecidable")
        assert build_prediction_record(decision, record, sim_day=3) is None

    def test_real_trade_builds_a_real_pending_prediction(self) -> None:
        decision = _decision(order_id="pos-1", supporting_agents=["scout", "atlas"], confidence=75.0)
        record = _ceo_record(ceo_decision="buy")
        prediction = build_prediction_record(decision, record, sim_day=3)
        assert prediction is not None
        assert prediction.decision_id == "decision-1"
        assert prediction.claim_type == "trade_direction"
        assert prediction.predicted_direction == "buy"
        assert prediction.confidence_pct == 75.0
        assert prediction.attributed_agents == ["scout", "atlas"]
        assert prediction.outcome == "pending"
        assert prediction.sim_day == 3

    def test_uses_the_final_ceo_decision_not_a_stale_choice(self) -> None:
        # resolve_proposal() can internally downgrade a real buy/sell to
        # "wait" when the position sizes to zero — the authoritative
        # final choice lives on the CeoDecisionRecord, never a caller's
        # earlier proposed choice.
        decision = _decision(order_id=None)
        record = _ceo_record(ceo_decision="wait")
        assert build_prediction_record(decision, record, sim_day=3) is None

    def test_sell_direction_is_tracked_too(self) -> None:
        decision = _decision(order_id="pos-1")
        record = _ceo_record(ceo_decision="sell")
        prediction = build_prediction_record(decision, record, sim_day=3)
        assert prediction is not None
        assert prediction.predicted_direction == "sell"


class TestGradePredictions:
    def test_no_matching_trade_stays_pending(self) -> None:
        decision = _decision()
        record = _ceo_record()
        prediction = build_prediction_record(decision, record, sim_day=3)
        assert prediction is not None
        graded = grade_predictions([prediction], [])
        assert graded[0].outcome == "pending"

    def test_matching_winning_trade_resolves_correct(self) -> None:
        decision = _decision()
        record = _ceo_record()
        prediction = build_prediction_record(decision, record, sim_day=3)
        assert prediction is not None
        trade = _trade(pnl=10.0, pnl_pct=5.0)
        graded = grade_predictions([prediction], [trade])
        assert graded[0].outcome == "correct"
        assert graded[0].resolved_trade_id == "trade-1"
        assert graded[0].resolved_pnl_pct == 5.0
        assert graded[0].resolved_at is not None

    def test_matching_losing_trade_resolves_incorrect(self) -> None:
        decision = _decision()
        record = _ceo_record()
        prediction = build_prediction_record(decision, record, sim_day=3)
        assert prediction is not None
        trade = _trade(pnl=-10.0, pnl_pct=-5.0)
        graded = grade_predictions([prediction], [trade])
        assert graded[0].outcome == "incorrect"

    def test_already_resolved_prediction_is_never_regraded(self) -> None:
        decision = _decision()
        record = _ceo_record()
        prediction = build_prediction_record(decision, record, sim_day=3)
        assert prediction is not None
        trade = _trade(pnl=10.0, pnl_pct=5.0)
        once = grade_predictions([prediction], [trade])
        # A second real closed trade sharing the same decision_id
        # (shouldn't happen in practice, but proves the guard) must never
        # overwrite an already-resolved record.
        different_trade = _trade(trade_id="trade-2", pnl=-99.0, pnl_pct=-99.0)
        twice = grade_predictions(once, [trade, different_trade])
        assert twice[0].outcome == "correct"
        assert twice[0].resolved_pnl_pct == 5.0

    def test_unrelated_trade_with_a_different_decision_id_is_ignored(self) -> None:
        decision = _decision()
        record = _ceo_record()
        prediction = build_prediction_record(decision, record, sim_day=3)
        assert prediction is not None
        unrelated = _trade(trade_id="trade-2", decision_id="decision-2")
        graded = grade_predictions([prediction], [unrelated])
        assert graded[0].outcome == "pending"


class TestShouldPromotePredictionOutcome:
    def test_high_confidence_miss_is_notable(self) -> None:
        decision = _decision(confidence=HIGH_CONFIDENCE_MISS_THRESHOLD)
        record = _ceo_record()
        prediction = build_prediction_record(decision, record, sim_day=3)
        assert prediction is not None
        graded = grade_predictions([prediction], [_trade(pnl=-5.0, pnl_pct=-2.0)])
        assert should_promote_prediction_outcome(graded[0]) is True

    def test_low_confidence_miss_is_not_notable(self) -> None:
        decision = _decision(confidence=20.0)
        record = _ceo_record()
        prediction = build_prediction_record(decision, record, sim_day=3)
        assert prediction is not None
        graded = grade_predictions([prediction], [_trade(pnl=-5.0, pnl_pct=-2.0)])
        assert should_promote_prediction_outcome(graded[0]) is False

    def test_high_confidence_correct_call_is_not_notable(self) -> None:
        decision = _decision(confidence=90.0)
        record = _ceo_record()
        prediction = build_prediction_record(decision, record, sim_day=3)
        assert prediction is not None
        graded = grade_predictions([prediction], [_trade(pnl=5.0, pnl_pct=2.0)])
        assert should_promote_prediction_outcome(graded[0]) is False

    def test_pending_prediction_is_never_notable(self) -> None:
        decision = _decision(confidence=95.0)
        record = _ceo_record()
        prediction = build_prediction_record(decision, record, sim_day=3)
        assert prediction is not None
        assert should_promote_prediction_outcome(prediction) is False
