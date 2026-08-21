"""Covers app/trade_pipeline_health.py — CEO directive "Professional
Quant Firm Phase 41-45," Critical Task #0's real trade-flow diagnostic.
Every assertion checks a direct, honest funnel count over real,
already-persisted state — never a fabricated estimate.
"""
from __future__ import annotations

from app.schemas import DecisionVaultEntry, GatekeeperRejection, LiquidityRead, OpportunityRejection, PaperTrade, ResearchItem, StrategyReport, TradeDecision
from app.state import default_state
from app.trade_pipeline_health import compute_strategy_trading_diagnostics, compute_trade_pipeline_health


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


def _paper_trade(trade_id: str) -> PaperTrade:
    return PaperTrade(
        id=trade_id,
        symbol="AAPL",
        side="buy",
        quantity=1.0,
        entryPrice=100.0,
        exitPrice=105.0,
        pnl=5.0,
        pnlPct=5.0,
        durationMinutes=30,
        confidence=80.0,
        reason="test",
        marketConditions="test",
        supportingAgents=["scout"],
        opposingAgents=[],
        openedAt="2024-01-01T00:00:00+00:00",
        closedAt="2024-01-01T00:00:00+00:00",
        openedSimMinutes=0,
        closedSimMinutes=30,
        decisionId=f"decision-{trade_id}",
    )


def _vault_entry(*, trade_id: str, strategy_id: str | None) -> DecisionVaultEntry:
    return DecisionVaultEntry(
        id=f"vault-{trade_id}",
        tradeId=trade_id,
        decisionId=f"decision-{trade_id}",
        symbol="AAPL",
        simDay=1,
        session="new_york",  # type: ignore[arg-type]
        strategyId=strategy_id,
        marketRegime="sideways_range",  # type: ignore[arg-type]
        marketRegimeLabel="test regime",
        liquidityContext=LiquidityRead(symbol="AAPL", zones=[], sweepDetected=False, sweepDirection="none", liquidityScore=50.0, detail="test"),
        evidenceScore=70.0,
        confidenceScore=70.0,
        confidenceTier="strong",  # type: ignore[arg-type]
        capitalAllocationGrade="B",  # type: ignore[arg-type]
        decisionGrade="B",  # type: ignore[arg-type]
        decisionGradeScore=80.0,
        disciplineTier="sound",  # type: ignore[arg-type]
        disciplineScore=75.0,
        patienceGrade="B",  # type: ignore[arg-type]
        positionSize=10.0,
        entryPrice=100.0,
        exitPrice=105.0,
        pnl=5.0,
        pnlPct=5.0,
        holdDurationMinutes=30,
        rMultiple=None,
        caseStudyId=None,
        caseStudyCategory=None,
        executiveNotes=None,
        lessonsLearned="test lesson",
        companyDnaChange=None,
        ceoOverride=False,
        createdAt="2024-01-01T00:00:00+00:00",
    )


def _strategy_report(*, strategy_id: str, best_market_environment: str) -> StrategyReport:
    return StrategyReport(
        id=f"report-{strategy_id}",
        strategyId=strategy_id,
        strategyName="test strategy",
        sourceResultId=f"result-{strategy_id}",
        scenario="historical",  # type: ignore[arg-type]
        executiveSummary="test",
        bestMarketEnvironment=best_market_environment,
        simDay=1,
        createdAt="2024-01-01T00:00:00+00:00",
    )


class TestComputeStrategyTradingDiagnostics:
    """CEO directive "Live Trade → Strategy Provenance," Phase 9 — the
    real strategy-specific gap `TestComputeTradePipelineHealth` above
    never covers. `default_state()` seeds 6 real strategies (4 default +
    2 real 50 EMA researchable strategies — see app/strategy_registry.py)
    with regime "weak_uptrend" (app/state.py's default_state(), keyword "bull" per
    app/market_intelligence.py's _REGIME_TO_SCENARIO_KEYWORD)."""

    def test_every_real_strategy_gets_exactly_one_diagnostic_read(self) -> None:
        state = default_state()
        summary = compute_strategy_trading_diagnostics(state)
        assert len(summary.reads) == len(state.strategies)
        assert {r.strategy_id for r in summary.reads} == {s.id for s in state.strategies}

    def test_a_strategy_with_no_report_and_no_live_trades_reads_no_backtest_evidence_yet(self) -> None:
        state = default_state()
        summary = compute_strategy_trading_diagnostics(state)
        momentum = next(r for r in summary.reads if r.strategy_id == "strategy-momentum")
        assert momentum.reason == "no_backtest_evidence_yet"
        assert momentum.live_trade_count == 0

    def test_a_strategy_with_a_real_live_trade_reads_trading_live(self) -> None:
        state = default_state().model_copy(
            update={
                "paper_portfolio": default_state().paper_portfolio.model_copy(update={"trade_history": [_paper_trade("t1")]}),
                "decision_vault": [_vault_entry(trade_id="t1", strategy_id="strategy-momentum")],
            }
        )
        summary = compute_strategy_trading_diagnostics(state)
        momentum = next(r for r in summary.reads if r.strategy_id == "strategy-momentum")
        assert momentum.reason == "trading_live"
        assert momentum.live_trade_count == 1

    def test_a_strategy_avoided_by_todays_regime_reads_blocked_by_regime_today(self) -> None:
        state = default_state().model_copy(
            update={"strategy_reports": [_strategy_report(strategy_id="strategy-value", best_market_environment="Not yet tested favorably in bull markets — lost money")]}
        )
        summary = compute_strategy_trading_diagnostics(state)
        value = next(r for r in summary.reads if r.strategy_id == "strategy-value")
        assert value.reason == "blocked_by_regime_today"
        assert value.live_trade_count == 0

    def test_a_strategy_recommended_by_todays_regime_with_no_live_trades_reads_eligible_but_never_selected(self) -> None:
        state = default_state().model_copy(update={"strategy_reports": [_strategy_report(strategy_id="strategy-macro", best_market_environment="Works well in bull markets")]})
        summary = compute_strategy_trading_diagnostics(state)
        macro = next(r for r in summary.reads if r.strategy_id == "strategy-macro")
        assert macro.reason == "eligible_but_never_selected"

    def test_a_live_trade_takes_priority_over_regime_eligibility(self) -> None:
        # A strategy that's both regime-recommended AND has a real live
        # trade reads "trading_live" — the strongest, most concrete real
        # fact always wins over an eligibility read.
        state = default_state().model_copy(
            update={
                "paper_portfolio": default_state().paper_portfolio.model_copy(update={"trade_history": [_paper_trade("t1")]}),
                "decision_vault": [_vault_entry(trade_id="t1", strategy_id="strategy-macro")],
                "strategy_reports": [_strategy_report(strategy_id="strategy-macro", best_market_environment="Works well in bull markets")],
            }
        )
        summary = compute_strategy_trading_diagnostics(state)
        macro = next(r for r in summary.reads if r.strategy_id == "strategy-macro")
        assert macro.reason == "trading_live"
