"""Covers app/opportunity_gatekeeper.py — v0.7 Chapter 58, the
Institutional Trade Filter & Opportunity Gatekeeper. Every case here
checks the one real guarantee the chapter makes: a candidate is
rejected only for a real, named reason (bad Market Quality, insufficient
Expected Value, or a Trade Quality Score below the CEO's own
configured minimum) — never a silent or fabricated cut — and every
rejection is graded the same honest way app/gatekeeper.py's own
GatekeeperRejection already is.
"""
from __future__ import annotations

from app.executive import generate_proposal
from app.market_data import MockMarketDataProvider
from app.market_intelligence import default_market_intelligence_state
from app.opportunity_gatekeeper import (
    OPPORTUNITY_EVAL_WINDOW_MINUTES,
    build_opportunity_rejection,
    evaluate_opportunity,
    grade_opportunity_rejections,
)
from app.portfolio import default_portfolio
from app.schemas import (
    DecisionScoreBreakdown,
    DecisionVaultEntry,
    ExpectedValueAnalysis,
    LiquidityRead,
    MarketQualityScore,
    OpportunityRejection,
    ResearchItem,
    RiskLimits,
    SessionRead,
    WatchlistEntry,
)


def _now_iso() -> str:
    from datetime import datetime, timezone

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


def _proposal():  # type: ignore[no-untyped-def]
    provider = MockMarketDataProvider()
    return generate_proposal(
        _research_item(),
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


def _decision_score(overall: float) -> DecisionScoreBreakdown:
    return DecisionScoreBreakdown(
        overall=overall,
        passed=overall >= 92.0,
        threshold=70.0,
        evidenceScore=overall,
        confidenceScore=overall,
        expectedValueScore=overall,
        riskScore=overall,
        marketQualityScore=overall,
        liquidityQualityScore=overall,
        portfolioCompatibilityScore=overall,
    )


def _expected_value(pct: float) -> ExpectedValueAnalysis:
    return ExpectedValueAnalysis(
        expectedValuePct=pct,
        edgePct=pct,
        riskToReward=2.0,
        positiveExpectancy=pct > 0,
        detail="test",
    )


def _market_intelligence(*, tier: str = "average", score: float = 50.0, session: str = "new_york", regime: str = "sideways_range"):  # type: ignore[no-untyped-def]
    quality = MarketQualityScore(tier=tier, score=score, confidencePct=50.0, reasoning="Test market quality.", evidence=[], historicalSimilarity="n/a")  # type: ignore[arg-type]
    session_read = SessionRead(current=session, label="Test Session", overlapsActive=[], detail="test")  # type: ignore[arg-type]
    return default_market_intelligence_state().model_copy(update={"quality": quality, "session": session_read, "regime": regime})


def _vault_entry(*, entry_id: str, session: str = "new_york", market_regime: str = "sideways_range", pnl_pct: float = 1.0) -> DecisionVaultEntry:
    return DecisionVaultEntry(
        id=entry_id,
        tradeId=f"trade-{entry_id}",
        decisionId=f"decision-{entry_id}",
        symbol="NEXA",
        simDay=1,
        session=session,  # type: ignore[arg-type]
        strategyId=None,
        marketRegime=market_regime,  # type: ignore[arg-type]
        marketRegimeLabel="test regime",
        liquidityContext=LiquidityRead(symbol="NEXA", zones=[], sweepDetected=False, sweepDirection="none", liquidityScore=50.0, detail="test"),
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
        exitPrice=100.0 + pnl_pct,
        pnl=pnl_pct * 10.0,
        pnlPct=pnl_pct,
        holdDurationMinutes=60,
        rMultiple=None,
        caseStudyId=None,
        caseStudyCategory=None,
        executiveNotes=None,
        lessonsLearned="test lesson",
        companyDnaChange=None,
        ceoOverride=False,
        createdAt=_now_iso(),
    )


def _rejection(
    *,
    symbol: str = "AAPL",
    would_have_recommended: str = "buy",
    rejected_sim_minutes: int = 0,
    price_at_rejection: float = 100.0,
    outcome: str = "pending",
) -> OpportunityRejection:
    return OpportunityRejection(
        id=f"oppreject-{symbol}-{rejected_sim_minutes}",
        symbol=symbol,
        wouldHaveRecommended=would_have_recommended,  # type: ignore[arg-type]
        reasons=["test reason"],
        reasonCodes=["trade_quality_below_threshold"],
        decisionScoreAtRejection=60.0,
        expectedValueAtRejectionPct=-1.0,
        priceAtRejection=price_at_rejection,
        rejectedSimMinutes=rejected_sim_minutes,
        outcome=outcome,  # type: ignore[arg-type]
        createdAt=_now_iso(),
    )


class TestEvaluateOpportunity:
    def test_approves_when_every_real_check_clears(self) -> None:
        approved, reasons, codes = evaluate_opportunity(
            decision_score=_decision_score(85.0),
            expected_value=_expected_value(1.0),
            market_intelligence=_market_intelligence(tier="good", score=80.0),
            risk_limits=RiskLimits(),
        )
        assert approved is True
        assert reasons == []
        assert codes == []

    def test_rejects_on_avoid_trading_market_quality(self) -> None:
        approved, reasons, codes = evaluate_opportunity(
            decision_score=_decision_score(85.0),
            expected_value=_expected_value(1.0),
            market_intelligence=_market_intelligence(tier="avoid_trading", score=10.0),
            risk_limits=RiskLimits(),
        )
        assert approved is False
        assert any("avoid trading" in r for r in reasons)
        assert codes == ["market_quality_avoid_trading"]

    def test_rejects_below_minimum_expected_value(self) -> None:
        approved, reasons, codes = evaluate_opportunity(
            decision_score=_decision_score(85.0),
            expected_value=_expected_value(-0.5),
            market_intelligence=_market_intelligence(),
            risk_limits=RiskLimits(),
        )
        assert approved is False
        assert any("Expected Value" in r for r in reasons)
        assert codes == ["expected_value_below_threshold"]

    def test_rejects_below_minimum_trade_quality_score(self) -> None:
        approved, reasons, codes = evaluate_opportunity(
            decision_score=_decision_score(50.0),
            expected_value=_expected_value(1.0),
            market_intelligence=_market_intelligence(),
            risk_limits=RiskLimits(),
        )
        assert approved is False
        assert any("Trade Quality Score" in r for r in reasons)
        assert codes == ["trade_quality_below_threshold"]

    def test_multiple_failures_are_all_named(self) -> None:
        approved, reasons, codes = evaluate_opportunity(
            decision_score=_decision_score(40.0),
            expected_value=_expected_value(-2.0),
            market_intelligence=_market_intelligence(tier="avoid_trading", score=5.0),
            risk_limits=RiskLimits(),
        )
        assert approved is False
        assert len(reasons) == 3
        assert len(codes) == 3

    def test_ceo_configured_threshold_is_real_and_respected(self) -> None:
        # A score that would pass the default 70-point bar is rejected
        # once the CEO raises the bar — proves the threshold is a real,
        # consulted CEO control, not a hardcoded stand-in.
        approved, _, _ = evaluate_opportunity(
            decision_score=_decision_score(75.0),
            expected_value=_expected_value(1.0),
            market_intelligence=_market_intelligence(),
            risk_limits=RiskLimits(minTradeQualityScore=80.0),
        )
        assert approved is False

    def test_ceo_can_relax_the_expected_value_floor_to_admit_a_marginal_candidate(self) -> None:
        approved, _, _ = evaluate_opportunity(
            decision_score=_decision_score(85.0),
            expected_value=_expected_value(-0.5),
            market_intelligence=_market_intelligence(),
            risk_limits=RiskLimits(minExpectedValuePct=-1.0),
        )
        assert approved is True

    def test_dominant_liquidity_drag_is_named_with_its_own_real_code(self) -> None:
        # Every sub-score is 60 except liquidity, which is 10 — the real minimum, below
        # LIQUIDITY_DOMINANT_DRAG_THRESHOLD — so the rejection must name it specifically.
        decision_score = _decision_score(60.0).model_copy(update={"liquidity_quality_score": 10.0, "overall": 55.0})
        approved, reasons, codes = evaluate_opportunity(
            decision_score=decision_score,
            expected_value=_expected_value(1.0),
            market_intelligence=_market_intelligence(),
            risk_limits=RiskLimits(),
        )
        assert approved is False
        assert "trade_quality_below_threshold" in codes
        assert "liquidity_confirmation_weak" in codes
        assert any("Liquidity confirmation reads 10" in r for r in reasons)

    def test_a_non_liquidity_dominant_drag_never_gets_the_liquidity_code(self) -> None:
        # Liquidity is fine (80); risk is the real minimum (10) — must never mislabel this
        # as a liquidity finding just because it's the only one this module explicitly names.
        decision_score = _decision_score(60.0).model_copy(update={"liquidity_quality_score": 80.0, "risk_score": 10.0, "overall": 55.0})
        approved, reasons, codes = evaluate_opportunity(
            decision_score=decision_score,
            expected_value=_expected_value(1.0),
            market_intelligence=_market_intelligence(),
            risk_limits=RiskLimits(),
        )
        assert approved is False
        assert "liquidity_confirmation_weak" not in codes
        assert not any("Liquidity confirmation" in r for r in reasons)

    def test_no_decision_vault_passed_never_triggers_the_session_regime_check(self) -> None:
        # Backward-compatible default: omitting decision_vault entirely
        # (every call site above this class does) must behave exactly as
        # before this check existed.
        approved, reasons, codes = evaluate_opportunity(
            decision_score=_decision_score(85.0),
            expected_value=_expected_value(1.0),
            market_intelligence=_market_intelligence(tier="good", score=80.0),
            risk_limits=RiskLimits(),
        )
        assert approved is True
        assert "session_regime_unfavorable_evidence" not in codes

    def test_rejects_on_real_unfavorable_session_regime_evidence(self) -> None:
        # Five real closed trades, all losses, under the exact live
        # (session, regime) pairing — a real 0% win rate at the evidence
        # floor, not a fabricated forecast.
        vault = [_vault_entry(entry_id=f"e{i}", session="new_york", market_regime="sideways_range", pnl_pct=-1.0) for i in range(5)]
        approved, reasons, codes = evaluate_opportunity(
            decision_score=_decision_score(85.0),
            expected_value=_expected_value(1.0),
            market_intelligence=_market_intelligence(tier="good", score=80.0, session="new_york", regime="sideways_range"),
            risk_limits=RiskLimits(),
            decision_vault=vault,
        )
        assert approved is False
        assert codes == ["session_regime_unfavorable_evidence"]
        assert any("real 0% win rate" in r for r in reasons)

    def test_below_evidence_floor_stays_silent_even_with_all_losses(self) -> None:
        # Only 4 real closed trades — below MIN_SESSION_REGIME_SAMPLE (5)
        # — must never force a read on a thin sample.
        vault = [_vault_entry(entry_id=f"e{i}", session="new_york", market_regime="sideways_range", pnl_pct=-1.0) for i in range(4)]
        approved, reasons, codes = evaluate_opportunity(
            decision_score=_decision_score(85.0),
            expected_value=_expected_value(1.0),
            market_intelligence=_market_intelligence(tier="good", score=80.0, session="new_york", regime="sideways_range"),
            risk_limits=RiskLimits(),
            decision_vault=vault,
        )
        assert approved is True
        assert codes == []

    def test_favorable_evidence_is_never_rejected(self) -> None:
        vault = [_vault_entry(entry_id=f"e{i}", session="new_york", market_regime="sideways_range", pnl_pct=1.0) for i in range(5)]
        approved, reasons, codes = evaluate_opportunity(
            decision_score=_decision_score(85.0),
            expected_value=_expected_value(1.0),
            market_intelligence=_market_intelligence(tier="good", score=80.0, session="new_york", regime="sideways_range"),
            risk_limits=RiskLimits(),
            decision_vault=vault,
        )
        assert approved is True
        assert codes == []

    def test_unfavorable_evidence_under_a_different_session_regime_pairing_never_applies(self) -> None:
        # Real unfavorable evidence exists — but for "asian" + "sideways_range",
        # not the live "new_york" + "sideways_range" pairing being evaluated.
        vault = [_vault_entry(entry_id=f"e{i}", session="asian", market_regime="sideways_range", pnl_pct=-1.0) for i in range(5)]
        approved, reasons, codes = evaluate_opportunity(
            decision_score=_decision_score(85.0),
            expected_value=_expected_value(1.0),
            market_intelligence=_market_intelligence(tier="good", score=80.0, session="new_york", regime="sideways_range"),
            risk_limits=RiskLimits(),
            decision_vault=vault,
        )
        assert approved is True
        assert codes == []


class TestCorrelatedExposureCheck:
    """CEO directive "Portfolio Construction, Capital Allocation &
    Execution Realism," Phase 4 — real, pre-proposal Pearson correlation
    gate. `correlated_position_count` is the caller's own already-
    computed real read (app/portfolio_intelligence.py's
    count_correlated_positions()) — this function only ever compares it
    against risk_limits.max_correlated_positions."""

    def test_none_means_the_caller_didnt_compute_one_never_treated_as_zero(self) -> None:
        approved, reasons, codes = evaluate_opportunity(
            decision_score=_decision_score(85.0),
            expected_value=_expected_value(1.0),
            market_intelligence=_market_intelligence(tier="good", score=80.0),
            risk_limits=RiskLimits(maxCorrelatedPositions=0),
            correlated_position_count=None,
        )
        assert approved is True
        assert "correlated_exposure_too_high" not in codes

    def test_within_the_real_configured_limit_passes(self) -> None:
        approved, reasons, codes = evaluate_opportunity(
            decision_score=_decision_score(85.0),
            expected_value=_expected_value(1.0),
            market_intelligence=_market_intelligence(tier="good", score=80.0),
            risk_limits=RiskLimits(maxCorrelatedPositions=2),
            correlated_position_count=2,
        )
        assert approved is True
        assert codes == []

    def test_beyond_the_real_configured_limit_rejects_and_names_it(self) -> None:
        approved, reasons, codes = evaluate_opportunity(
            decision_score=_decision_score(85.0),
            expected_value=_expected_value(1.0),
            market_intelligence=_market_intelligence(tier="good", score=80.0),
            risk_limits=RiskLimits(maxCorrelatedPositions=2),
            correlated_position_count=3,
        )
        assert approved is False
        assert codes == ["correlated_exposure_too_high"]
        assert any("3 currently-held position" in r for r in reasons)

    def test_a_ceo_configured_higher_limit_widens_what_passes(self) -> None:
        approved, reasons, codes = evaluate_opportunity(
            decision_score=_decision_score(85.0),
            expected_value=_expected_value(1.0),
            market_intelligence=_market_intelligence(tier="good", score=80.0),
            risk_limits=RiskLimits(maxCorrelatedPositions=10),
            correlated_position_count=3,
        )
        assert approved is True
        assert codes == []

    def test_zero_correlated_positions_never_falsely_rejects(self) -> None:
        approved, reasons, codes = evaluate_opportunity(
            decision_score=_decision_score(85.0),
            expected_value=_expected_value(1.0),
            market_intelligence=_market_intelligence(tier="good", score=80.0),
            risk_limits=RiskLimits(),
            correlated_position_count=0,
        )
        assert approved is True
        assert codes == []


class TestBuildOpportunityRejection:
    def test_maps_real_fields_from_the_candidate(self) -> None:
        proposal = _proposal()
        rejection = build_opportunity_rejection(
            proposal,
            decision_score=_decision_score(55.0),
            expected_value=_expected_value(-1.0),
            reasons=["Trade Quality Score 55/100 is below the required 70 minimum."],
            reason_codes=["trade_quality_below_threshold"],
            price_at_rejection=123.45,
            now_sim_minutes=500,
        )
        assert rejection.symbol == proposal.symbol
        assert rejection.would_have_recommended == proposal.overall_recommendation
        assert rejection.decision_score_at_rejection == 55.0
        assert rejection.expected_value_at_rejection_pct == -1.0
        assert rejection.price_at_rejection == 123.45
        assert rejection.rejected_sim_minutes == 500
        assert rejection.outcome == "pending"
        assert rejection.resolved_at is None
        assert rejection.reason_codes == ["trade_quality_below_threshold"]


class TestGradeOpportunityRejections:
    def test_leaves_recent_rejections_pending(self) -> None:
        rejections = [_rejection(rejected_sim_minutes=100)]
        graded = grade_opportunity_rejections(rejections, watchlist=[WatchlistEntry(symbol="AAPL", name="Apple", lastPrice=110.0, dailyChangePct=1.0, status="completed", researchProgress=0.0)], now_sim_minutes=150)
        assert graded[0].outcome == "pending"

    def test_grades_a_buy_direction_that_would_have_won(self) -> None:
        rejections = [_rejection(symbol="AAPL", would_have_recommended="buy", price_at_rejection=100.0, rejected_sim_minutes=0)]
        watchlist = [WatchlistEntry(symbol="AAPL", name="Apple", lastPrice=110.0, dailyChangePct=1.0, status="completed", researchProgress=0.0)]
        graded = grade_opportunity_rejections(rejections, watchlist, now_sim_minutes=OPPORTUNITY_EVAL_WINDOW_MINUTES)
        assert graded[0].outcome == "would_have_won"
        assert graded[0].resolved_price_change_pct == 10.0
        assert graded[0].resolved_at is not None

    def test_grades_a_buy_direction_that_would_have_lost(self) -> None:
        rejections = [_rejection(symbol="AAPL", would_have_recommended="buy", price_at_rejection=100.0, rejected_sim_minutes=0)]
        watchlist = [WatchlistEntry(symbol="AAPL", name="Apple", lastPrice=90.0, dailyChangePct=-1.0, status="completed", researchProgress=0.0)]
        graded = grade_opportunity_rejections(rejections, watchlist, now_sim_minutes=OPPORTUNITY_EVAL_WINDOW_MINUTES)
        assert graded[0].outcome == "would_have_lost"

    def test_grades_a_sell_direction_inverted(self) -> None:
        rejections = [_rejection(symbol="AAPL", would_have_recommended="sell", price_at_rejection=100.0, rejected_sim_minutes=0)]
        watchlist = [WatchlistEntry(symbol="AAPL", name="Apple", lastPrice=90.0, dailyChangePct=-1.0, status="completed", researchProgress=0.0)]
        graded = grade_opportunity_rejections(rejections, watchlist, now_sim_minutes=OPPORTUNITY_EVAL_WINDOW_MINUTES)
        assert graded[0].outcome == "would_have_won"

    def test_wait_direction_is_never_graded(self) -> None:
        rejections = [_rejection(symbol="AAPL", would_have_recommended="wait", price_at_rejection=100.0, rejected_sim_minutes=0)]
        watchlist = [WatchlistEntry(symbol="AAPL", name="Apple", lastPrice=200.0, dailyChangePct=100.0, status="completed", researchProgress=0.0)]
        graded = grade_opportunity_rejections(rejections, watchlist, now_sim_minutes=OPPORTUNITY_EVAL_WINDOW_MINUTES * 10)
        assert graded[0].outcome == "pending"

    def test_missing_watchlist_price_stays_pending(self) -> None:
        rejections = [_rejection(symbol="ZZZZ", rejected_sim_minutes=0)]
        graded = grade_opportunity_rejections(rejections, watchlist=[], now_sim_minutes=OPPORTUNITY_EVAL_WINDOW_MINUTES)
        assert graded[0].outcome == "pending"

    def test_already_resolved_rejection_is_untouched(self) -> None:
        rejections = [_rejection(symbol="AAPL", rejected_sim_minutes=0, outcome="would_have_won")]
        watchlist = [WatchlistEntry(symbol="AAPL", name="Apple", lastPrice=50.0, dailyChangePct=-10.0, status="completed", researchProgress=0.0)]
        graded = grade_opportunity_rejections(rejections, watchlist, now_sim_minutes=OPPORTUNITY_EVAL_WINDOW_MINUTES * 5)
        assert graded[0].outcome == "would_have_won"
        assert graded[0].resolved_price_change_pct is None

    def test_empty_list_returns_empty_list(self) -> None:
        assert grade_opportunity_rejections([], [], now_sim_minutes=0) == []
