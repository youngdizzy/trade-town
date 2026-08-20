"""Covers app/trade_pipeline_health.py — CEO directive "Professional
Quant Firm Phase 41-45," Critical Task #0's real trade-flow diagnostic.
Every assertion checks a direct, honest funnel count over real,
already-persisted state — never a fabricated estimate.
"""
from __future__ import annotations

from app.schemas import GatekeeperRejection, OpportunityRejection, ResearchItem, TradeDecision
from app.state import default_state
from app.trade_pipeline_health import compute_trade_pipeline_health


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _research_item(status: str, symbol: str = "AAPL") -> ResearchItem:
    return ResearchItem(
        id=f"research-{symbol}-{status}",
        title="Test research",
        symbol=symbol,
        category="stock",
        priority="normal",
        status=status,  # type: ignore[arg-type]
        assignedAgent="nova",
        summary="test",
        confidence=100.0 if status == "completed" else 50.0,
        createdAt=_now_iso(),
        updatedAt=_now_iso(),
    )


def _decision(outcome: str) -> TradeDecision:
    return TradeDecision(
        id=f"decision-{outcome}-{_now_iso()}",
        symbol="AAPL",
        outcome=outcome,  # type: ignore[arg-type]
        votes=[],
        researchSummary="test",
        technicalSummary="test",
        fundamentalSummary="test",
        riskSummary="test",
        supportingAgents=[],
        opposingAgents=[],
        confidence=80.0,
        finalReasoning="test",
        createdAt=_now_iso(),
    )


def _opportunity_rejection(reason_codes: list[str]) -> OpportunityRejection:
    return OpportunityRejection(
        id=f"oppreject-{_now_iso()}",
        symbol="AAPL",
        wouldHaveRecommended="buy",  # type: ignore[arg-type]
        reasons=["test reason"] * len(reason_codes),
        reasonCodes=reason_codes,  # type: ignore[arg-type]
        decisionScoreAtRejection=60.0,
        expectedValueAtRejectionPct=-1.0,
        priceAtRejection=100.0,
        rejectedSimMinutes=0,
        createdAt=_now_iso(),
    )


def _gatekeeper_rejection(reason_codes: list[str]) -> GatekeeperRejection:
    return GatekeeperRejection(
        id=f"gkreject-{_now_iso()}",
        proposalId="proposal-1",
        symbol="AAPL",
        ceoChoice="buy",  # type: ignore[arg-type]
        reasons=["test reason"] * len(reason_codes),
        reasonCodes=reason_codes,  # type: ignore[arg-type]
        priceAtRejection=100.0,
        rejectedSimMinutes=0,
        createdAt=_now_iso(),
    )


class TestComputeTradePipelineHealth:
    def test_counts_completed_research_signals_only(self) -> None:
        state = default_state().model_copy(update={"research": [_research_item("completed"), _research_item("in_progress"), _research_item("completed", symbol="MSFT")]})
        snapshot = compute_trade_pipeline_health(state)
        assert snapshot.completed_research_signals == 2

    def test_counts_pending_proposals_directly(self) -> None:
        from app.executive import generate_proposal
        from app.market_data import MockMarketDataProvider
        from app.market_intelligence import default_market_intelligence_state
        from app.portfolio import default_portfolio
        from app.schemas import RiskLimits

        proposal = generate_proposal(
            _research_item("completed"),
            quantity=1.0,
            price=100.0,
            news=[],
            scanner_alerts=[],
            sentinel_warning=None,
            guardian_warning=None,
            provider=MockMarketDataProvider(),
            now_sim_minutes=0,
            portfolio=default_portfolio(),
            risk_limits=RiskLimits(),
            market_intelligence=default_market_intelligence_state(),
        )
        state = default_state().model_copy(update={"trade_proposals": [proposal]})
        snapshot = compute_trade_pipeline_health(state)
        assert snapshot.pending_proposals == 1

    def test_splits_resolved_decisions_into_trade_vs_no_trade(self) -> None:
        state = default_state().model_copy(update={"decisions": [_decision("trade"), _decision("trade"), _decision("no_trade")]})
        snapshot = compute_trade_pipeline_health(state)
        assert snapshot.resolved_decisions == 3
        assert snapshot.trades_executed == 2
        assert snapshot.no_trade_decisions == 1

    def test_counts_opportunity_and_gatekeeper_rejections(self) -> None:
        state = default_state().model_copy(
            update={
                "opportunity_rejections": [_opportunity_rejection(["trade_quality_below_threshold"])],
                "gatekeeper_rejections": [_gatekeeper_rejection(["gatekeeper_confidence"]), _gatekeeper_rejection(["gatekeeper_agreement"])],
            }
        )
        snapshot = compute_trade_pipeline_health(state)
        assert snapshot.opportunity_rejections == 1
        assert snapshot.gatekeeper_rejections == 2

    def test_reason_code_breakdown_tallies_across_both_rejection_sources_real_and_sorted_by_count(self) -> None:
        state = default_state().model_copy(
            update={
                "opportunity_rejections": [
                    _opportunity_rejection(["trade_quality_below_threshold", "liquidity_confirmation_weak"]),
                    _opportunity_rejection(["trade_quality_below_threshold"]),
                ],
                "gatekeeper_rejections": [_gatekeeper_rejection(["gatekeeper_confidence"])],
            }
        )
        snapshot = compute_trade_pipeline_health(state)
        by_code = {t.code: t.count for t in snapshot.reason_code_breakdown}
        assert by_code["trade_quality_below_threshold"] == 2
        assert by_code["liquidity_confirmation_weak"] == 1
        assert by_code["gatekeeper_confidence"] == 1
        # Sorted most-frequent-first — the real dominant reason must lead the list.
        assert snapshot.reason_code_breakdown[0].code == "trade_quality_below_threshold"

    def test_a_fresh_state_with_no_activity_reads_all_real_zeros_never_fabricated(self) -> None:
        state = default_state()
        snapshot = compute_trade_pipeline_health(state)
        assert snapshot.completed_research_signals == 0
        assert snapshot.resolved_decisions == 0
        assert snapshot.trades_executed == 0
        assert snapshot.no_trade_decisions == 0
        assert snapshot.opportunity_rejections == 0
        assert snapshot.gatekeeper_rejections == 0
        assert snapshot.reason_code_breakdown == []

    def test_data_honesty_note_discloses_the_real_caps(self) -> None:
        snapshot = compute_trade_pipeline_health(default_state())
        assert "capped" in snapshot.data_honesty_note.lower()
        assert "200" in snapshot.data_honesty_note
