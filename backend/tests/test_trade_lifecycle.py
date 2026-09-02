"""Covers app/trade_lifecycle.py — Canonical Trade Lifecycle 1.0."""
from __future__ import annotations

from app.schemas import (
    AnalystVote,
    CeoDecisionRecord,
    DecisionConfidence,
    FailureClassification,
    GatekeeperCheck,
    GatekeeperVerdict,
    InstitutionalMemoryEntry,
    PaperOrder,
    PaperPosition,
    PaperTrade,
    PaperTradeJournalEntry,
    PredictionRecord,
    RiskContractScalingRead,
    RiskDecision,
    TradeDecision,
    TradeProposal,
)
from app.state import default_state
from app.trade_lifecycle import build_trade_lifecycle_record, resolve_trade_root_id


def _scaling() -> RiskContractScalingRead:
    return RiskContractScalingRead(
        riskContractId="rc-1",
        riskContractVersion=1,
        drawdownPct=0.0,
        drawdownFactor=1.0,
        consecutiveLosses=0,
        losingStreakFactor=1.0,
        combinedFactor=1.0,
        baseRiskPerTradePct=2.0,
        approvedRiskPerTradePct=2.0,
        baseMaxPositionPct=10.0,
        approvedMaxPositionPct=10.0,
        killSwitchTriggered=False,
        detail="No scaling applied.",
    )


def _gatekeeper_approved() -> GatekeeperVerdict:
    return GatekeeperVerdict(
        approved=True,
        checks=[GatekeeperCheck(id="confidence", label="Confidence", passed=True, detail="72% >= 60%")],
        summary="All checks passed.",
        createdAt="2026-01-01T00:00:00+00:00",
    )


def _decision(**overrides: object) -> TradeDecision:
    base: dict[str, object] = dict(
        id="decision-p1",
        symbol="AAPL",
        outcome="trade",
        votes=[],
        researchSummary="Breakout setup.",
        technicalSummary="RSI confirms momentum.",
        fundamentalSummary="Research category: stock.",
        riskSummary="Within risk budget.",
        supportingAgents=["scout"],
        opposingAgents=[],
        confidence=72.0,
        finalReasoning="CEO approved BUY on AAPL.",
        orderId="pos-p1",
        gatekeeperVerdict=_gatekeeper_approved(),
        createdAt="2026-01-01T00:00:00+00:00",
    )
    base.update(overrides)
    return TradeDecision(**base)  # type: ignore[arg-type]


def _ceo_decision(**overrides: object) -> CeoDecisionRecord:
    base: dict[str, object] = dict(
        id="ceo-p1",
        proposalId="p1",
        symbol="AAPL",
        category="stock",
        aiRecommendation="buy",
        ceoDecision="buy",
        agreedWithAi=True,
        decisionId="decision-p1",
        outcome="pending",
        resolvedBy="ceo",
        createdAt="2026-01-01T00:00:00+00:00",
        resolvedAt="2026-01-01T00:00:00+00:00",
        strategyId="strategy-1",
        strategyCompiledDefinitionId="def-1",
        strategyCompiledDefinitionVersion=2,
    )
    base.update(overrides)
    return CeoDecisionRecord(**base)  # type: ignore[arg-type]


def _risk_decision() -> RiskDecision:
    return RiskDecision(
        id="riskdecision-decision-p1",
        createdAt="2026-01-01T00:00:00+00:00",
        proposalId="p1",
        decisionId="decision-p1",
        symbol="AAPL",
        scaling=_scaling(),
        requestedQuantity=2.0,
        approvedQuantity=2.0,
        rejected=False,
    )


def _position(**overrides: object) -> PaperPosition:
    base: dict[str, object] = dict(
        id="pos-p1",
        symbol="AAPL",
        side="buy",
        quantity=2.0,
        entryPrice=100.0,
        currentPrice=104.0,
        unrealizedPnl=8.0,
        unrealizedPnlPct=4.0,
        openedBy="scout",
        confidence=72.0,
        openedAt="2026-01-01T00:00:00+00:00",
        proposalId="p1",
        stopPrice=97.0,
        targetPrice=112.0,
        maePct=-0.5,
        mfePct=4.0,
    )
    base.update(overrides)
    return PaperPosition(**base)  # type: ignore[arg-type]


def _trade(**overrides: object) -> PaperTrade:
    base: dict[str, object] = dict(
        id="trade-pos-p1",
        symbol="AAPL",
        side="buy",
        quantity=2.0,
        entryPrice=100.0,
        exitPrice=108.0,
        pnl=16.0,
        pnlPct=8.0,
        durationMinutes=45,
        confidence=72.0,
        reason="Take-profit target reached.",
        marketConditions="Trending.",
        supportingAgents=["scout"],
        openedAt="2026-01-01T00:00:00+00:00",
        closedAt="2026-01-01T00:45:00+00:00",
        decisionId="decision-p1",
        proposalId="p1",
        stopPrice=97.0,
        targetPrice=112.0,
        maePct=-0.5,
        mfePct=9.0,
    )
    base.update(overrides)
    return PaperTrade(**base)  # type: ignore[arg-type]


def _stop_order(**overrides: object) -> PaperOrder:
    base: dict[str, object] = dict(
        id="order-stop-pos-p1",
        symbol="AAPL",
        side="sell",
        orderType="stop_loss",
        quantity=2.0,
        price=97.0,
        status="cancelled",
        placedBy="scout",
        reason="Protective stop for pos-p1.",
        confidence=72.0,
        linkedPositionId="pos-p1",
        createdAt="2026-01-01T00:00:00+00:00",
    )
    base.update(overrides)
    return PaperOrder(**base)  # type: ignore[arg-type]


def _target_order(**overrides: object) -> PaperOrder:
    base: dict[str, object] = dict(
        id="order-target-pos-p1",
        symbol="AAPL",
        side="sell",
        orderType="take_profit",
        quantity=2.0,
        price=112.0,
        status="filled",
        placedBy="scout",
        reason="Take-profit for pos-p1.",
        confidence=72.0,
        linkedPositionId="pos-p1",
        filledPrice=112.0,
        filledAt="2026-01-01T00:45:00+00:00",
        createdAt="2026-01-01T00:00:00+00:00",
    )
    base.update(overrides)
    return PaperOrder(**base)  # type: ignore[arg-type]


def _proposal(**overrides: object) -> TradeProposal:
    base: dict[str, object] = dict(
        id="p1",
        symbol="AAPL",
        category="stock",
        quantity=2.0,
        price=100.0,
        confidence=72.0,
        analystVotes=[AnalystVote(role="technical", agentId="scout", choice="buy", reasoning="Momentum confirmed.")],
        overallRecommendation="buy",
        researchSummary="Breakout setup.",
        riskSummary="Within risk budget.",
        confidenceEngine=DecisionConfidence(score=72.0, tier="moderate", summary="Solid confluence."),
        createdAt="2026-01-01T00:00:00+00:00",
        createdSimMinutes=0,
    )
    base.update(overrides)
    return TradeProposal(**base)  # type: ignore[arg-type]


def _prediction(**overrides: object) -> PredictionRecord:
    base: dict[str, object] = dict(
        id="prediction-decision-p1",
        decisionId="decision-p1",
        symbol="AAPL",
        claimType="trade_direction",
        predictedDirection="buy",
        confidencePct=72.0,
        attributedAgents=["scout"],
        outcome="correct",
        resolvedTradeId="trade-pos-p1",
        resolvedPnlPct=8.0,
        simDay=1,
        createdAt="2026-01-01T00:00:00+00:00",
        resolvedAt="2026-01-01T00:45:00+00:00",
    )
    base.update(overrides)
    return PredictionRecord(**base)  # type: ignore[arg-type]


def _failure(**overrides: object) -> FailureClassification:
    base: dict[str, object] = dict(
        id="failure-trade-pos-p1",
        tradeId="trade-pos-p1",
        decisionId="decision-p1",
        symbol="AAPL",
        reason="bad_thesis",
        evidence="Reversed against the entry thesis within the hour.",
        attributedAgents=["scout"],
        tradePnlPct=-4.0,
        simDay=1,
        createdAt="2026-01-01T00:45:00+00:00",
    )
    base.update(overrides)
    return FailureClassification(**base)  # type: ignore[arg-type]


def _memory_entry(**overrides: object) -> InstitutionalMemoryEntry:
    base: dict[str, object] = dict(
        id="memory-1",
        source="prediction",
        createdAt="2026-01-01T00:45:00+00:00",
        simDay=1,
        eventRef="prediction-decision-p1",
        observation="A high-confidence BUY prediction resolved correctly.",
        confidence=60.0,
        provenance="Promoted from PredictionRecord prediction-decision-p1.",
        relevancePct=100.0,
    )
    base.update(overrides)
    return InstitutionalMemoryEntry(**base)  # type: ignore[arg-type]


def test_resolve_trade_root_id_not_found_returns_none() -> None:
    state = default_state()
    assert resolve_trade_root_id(state, "nope") is None


def test_resolve_trade_root_id_matches_via_position_trade_decision_or_journal() -> None:
    state = default_state().model_copy(
        update={
            "ceo_decisions": [_ceo_decision()],
            "paper_portfolio": default_state().paper_portfolio.model_copy(update={"positions": [_position()]}),
        }
    )
    assert resolve_trade_root_id(state, "pos-p1") == "p1"
    assert resolve_trade_root_id(state, "ceo-p1") == "p1"
    assert resolve_trade_root_id(state, "p1") == "p1"


def test_build_trade_lifecycle_record_returns_none_for_unknown_key() -> None:
    state = default_state()
    assert build_trade_lifecycle_record(state, "nope") is None


def test_open_position_lifecycle_is_traced_end_to_end() -> None:
    state = default_state().model_copy(
        update={
            "ceo_decisions": [_ceo_decision()],
            "decisions": [_decision()],
            "risk_decisions": [_risk_decision()],
            "paper_portfolio": default_state().paper_portfolio.model_copy(
                update={"positions": [_position()], "orders": [_stop_order(status="open"), _target_order(status="open", filledPrice=None, filledAt=None)]}
            ),
        }
    )
    record = build_trade_lifecycle_record(state, "pos-p1")
    assert record is not None
    assert record.trade_root_id == "p1"
    assert record.symbol == "AAPL"
    assert record.status == "open"
    assert record.position is not None and record.position.id == "pos-p1"
    assert record.trade is None
    assert len(record.linked_orders) == 2
    assert {o.order_type for o in record.linked_orders} == {"stop_loss", "take_profit"}

    stage_by_id = {s.stage: s for s in record.stages}
    assert stage_by_id["decision"].available is True
    assert stage_by_id["strategy_identity"].available is True
    assert stage_by_id["strategy_identity"].ref_id == "strategy-1"
    assert stage_by_id["order_submitted"].available is True
    assert "Approved" in stage_by_id["order_submitted"].note
    assert stage_by_id["position_open"].available is True
    assert stage_by_id["position_active"].available is True
    assert stage_by_id["closed"].available is False
    assert stage_by_id["exit"].available is False


def test_closed_trade_lifecycle_joins_journal_prediction_failure_and_memory() -> None:
    state = default_state().model_copy(
        update={
            "ceo_decisions": [_ceo_decision()],
            "decisions": [_decision()],
            "risk_decisions": [_risk_decision()],
            "paper_portfolio": default_state().paper_portfolio.model_copy(
                update={"trade_history": [_trade()], "orders": [_stop_order(status="cancelled"), _target_order(status="filled")]}
            ),
            "paper_trade_journal": [
                PaperTradeJournalEntry(
                    id="journal-trade-pos-p1",
                    createdAt="2026-01-01T00:45:00+00:00",
                    tradeId="trade-pos-p1",
                    decisionId="decision-p1",
                    proposalId="p1",
                    symbol="AAPL",
                    side="buy",
                    quantity=2.0,
                    entryPrice=100.0,
                    exitPrice=108.0,
                    pnl=16.0,
                    pnlPct=8.0,
                    maePct=-0.5,
                    mfePct=9.0,
                    durationMinutes=45,
                    openedAt="2026-01-01T00:00:00+00:00",
                    closedAt="2026-01-01T00:45:00+00:00",
                )
            ],
            "prediction_records": [_prediction()],
            "institutional_memory": [_memory_entry()],
        }
    )
    record = build_trade_lifecycle_record(state, "trade-pos-p1")
    assert record is not None
    assert record.status == "closed"
    assert record.trade is not None and record.trade.id == "trade-pos-p1"
    assert record.position is None
    assert record.journal_entry is not None and record.journal_entry.id == "journal-trade-pos-p1"
    assert record.prediction is not None and record.prediction.outcome == "correct"
    assert len(record.institutional_memory) == 1
    # Linked orders still resolve for a closed trade via the trade's own
    # deterministic position_id, even though the PaperPosition itself is gone.
    assert len(record.linked_orders) == 2

    stage_by_id = {s.stage: s for s in record.stages}
    assert stage_by_id["closed"].available is True
    assert stage_by_id["exit"].available is True
    assert "stop/target PaperOrder" in stage_by_id["exit"].note
    assert stage_by_id["outcome_recorded"].available is True
    assert stage_by_id["trade_finalized"].available is True
    assert stage_by_id["trade_finalized"].ref_id == "memory-1"


def test_closed_trade_with_no_linked_protective_order_fill_discloses_direct_close() -> None:
    state = default_state().model_copy(
        update={
            "paper_portfolio": default_state().paper_portfolio.model_copy(
                update={"trade_history": [_trade(reason="Hold duration expired — random close.")]}
            ),
        }
    )
    record = build_trade_lifecycle_record(state, "trade-pos-p1")
    assert record is not None
    stage_by_id = {s.stage: s for s in record.stages}
    assert "direct close_position() call" in stage_by_id["exit"].note


def test_rejected_decision_has_no_position_or_trade_but_is_traced() -> None:
    rejected_verdict = GatekeeperVerdict(
        approved=False,
        checks=[GatekeeperCheck(id="confidence", label="Confidence", passed=False, detail="55% < 60% minimum.")],
        summary="Confidence: 55% < 60% minimum.",
        createdAt="2026-01-01T00:00:00+00:00",
    )
    state = default_state().model_copy(
        update={
            "ceo_decisions": [_ceo_decision(outcome="undecidable")],
            "decisions": [_decision(orderId=None, outcome="no_trade", gatekeeperVerdict=rejected_verdict)],
        }
    )
    record = build_trade_lifecycle_record(state, "ceo-p1")
    assert record is not None
    assert record.status == "rejected"
    assert record.position is None
    assert record.trade is None

    stage_by_id = {s.stage: s for s in record.stages}
    assert stage_by_id["order_submitted"].available is True
    assert "Rejected" in stage_by_id["order_submitted"].note
    assert stage_by_id["position_open"].available is False
    assert stage_by_id["fill"].available is False


def test_no_strategy_selected_is_disclosed_not_fabricated() -> None:
    state = default_state().model_copy(
        update={
            "ceo_decisions": [_ceo_decision(strategyId=None, strategyCompiledDefinitionId=None, strategyCompiledDefinitionVersion=None)],
            "decisions": [_decision()],
        }
    )
    record = build_trade_lifecycle_record(state, "ceo-p1")
    assert record is not None
    stage_by_id = {s.stage: s for s in record.stages}
    assert stage_by_id["strategy_identity"].available is False
    assert "honest majority" in stage_by_id["strategy_identity"].note


def test_pending_proposal_with_no_decision_yet_is_traced_as_pending() -> None:
    state = default_state().model_copy(update={"trade_proposals": [_proposal()]})
    record = build_trade_lifecycle_record(state, "p1")
    assert record is not None
    assert record.status == "pending"
    assert record.proposal is not None
    stage_by_id = {s.stage: s for s in record.stages}
    assert stage_by_id["signal"].available is True
    assert stage_by_id["decision"].available is False


def test_no_institutional_memory_promotion_is_disclosed_not_fabricated() -> None:
    state = default_state().model_copy(
        update={
            "paper_portfolio": default_state().paper_portfolio.model_copy(update={"trade_history": [_trade()]}),
        }
    )
    record = build_trade_lifecycle_record(state, "trade-pos-p1")
    assert record is not None
    stage_by_id = {s.stage: s for s in record.stages}
    assert stage_by_id["trade_finalized"].available is False
    assert "did not clear any real promotion gate" in stage_by_id["trade_finalized"].note
