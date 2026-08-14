"""Covers app/failure_review.py — CEO directive "Features 26-30," Feature
30 (Agent Debate + Failure Review Board), the final stage of the
26->27->28->29->30 learning loop. classify_failure() must pick exactly
one real, evidence-backed FailureReason per closed, losing trade,
following a fixed precedence order, and must never fabricate a cause
when no real signal fires.
"""
from __future__ import annotations

from app.failure_review import (
    MAX_FAILURE_CLASSIFICATIONS,
    classify_failure,
    record_failure_classification,
    should_promote_failure_classification,
)
from app.schemas import (
    AgentId,
    CaseStudy,
    DisciplineFactor,
    DisciplineReview,
    FailureClassification,
    MarketIntelligenceLearningEntry,
    PaperTrade,
    PostDecisionReview,
    TradeDecision,
)


def _now_iso() -> str:
    return "2026-01-01T00:00:00+00:00"


def _decision(*, decision_id: str = "decision-1", supporting: list[AgentId] | None = None) -> TradeDecision:
    return TradeDecision(
        id=decision_id,
        symbol="NEXA",
        outcome="trade",
        researchSummary="test",
        technicalSummary="test",
        fundamentalSummary="test",
        riskSummary="test",
        supportingAgents=supporting if supporting is not None else ["scout", "atlas"],
        opposingAgents=[],
        confidence=80.0,
        finalReasoning="test",
        orderId="pos-1",
        createdAt=_now_iso(),
    )


def _trade(
    *,
    trade_id: str = "trade-1",
    decision_id: str = "decision-1",
    pnl_pct: float = -5.0,
    duration_minutes: int = 60,
    trading_style: str | None = None,
    opened_sim_minutes: int = 0,
    closed_sim_minutes: int = 60,
) -> PaperTrade:
    return PaperTrade(
        id=trade_id,
        symbol="NEXA",
        side="buy",  # type: ignore[arg-type]
        quantity=10.0,
        entryPrice=100.0,
        exitPrice=95.0,
        pnl=pnl_pct,
        pnlPct=pnl_pct,
        durationMinutes=duration_minutes,
        confidence=80.0,
        reason="test",
        marketConditions="test",
        supportingAgents=["scout", "atlas"],
        openedAt=_now_iso(),
        closedAt=_now_iso(),
        openedSimMinutes=opened_sim_minutes,
        closedSimMinutes=closed_sim_minutes,
        decisionId=decision_id,
        tradingStyle=trading_style,  # type: ignore[arg-type]
    )


def _discipline_review(*, position_sizing_score: float = 80.0, tier: str = "adequate", score: float = 60.0) -> DisciplineReview:
    return DisciplineReview(
        id="discipline-1",
        decisionId="decision-1",
        symbol="NEXA",
        score=score,
        tier=tier,  # type: ignore[arg-type]
        factors=[
            DisciplineFactor(id="position_sizing_discipline", name="Position Sizing Discipline", score=position_sizing_score, weight=0.15, detail="test detail"),
        ],
        summary="test summary",
        postDecisionReview=PostDecisionReview(),
        outcome="loss",
        tradePnlPct=-5.0,
        holdDurationMinutes=60,
        simDay=3,
        createdAt=_now_iso(),
    )


def _case_study(*, category: str, study_id: str = "case-1") -> CaseStudy:
    return CaseStudy(
        id=study_id,
        category=category,  # type: ignore[arg-type]
        title="Test Case Study",
        symbol="NEXA",
        decisionId="decision-1",
        background="test background",
        decisionProcess="test decision process",
        missedInformation="test missed info",
        lessonsLearned="test lessons",
        recommendedImprovements="test improvements",
        tradePnlPct=-5.0,
        simDay=3,
        createdAt=_now_iso(),
    )


def _learning_entry(*, for_sim_day: int, regime_consistent: bool | None) -> MarketIntelligenceLearningEntry:
    return MarketIntelligenceLearningEntry(
        id=f"mil-{for_sim_day}",
        forSimDay=for_sim_day,
        predictedRegime="strong_bull_trend",  # type: ignore[arg-type]
        predictedQualityTier="good",  # type: ignore[arg-type]
        actualEnvironmentRegime="bear",  # type: ignore[arg-type]
        regimeConsistent=regime_consistent,
        tradesClosedThatDay=1,
        tradesWinRatePct=0.0,
        lesson="test lesson",
        createdAt=_now_iso(),
    )


class TestClassifyFailureProcessViolation:
    def test_day_trade_held_past_bar_is_process_violation(self) -> None:
        decision = _decision()
        trade = _trade(trading_style="day", duration_minutes=1500, closed_sim_minutes=1500)
        review = _discipline_review()
        result = classify_failure(decision, trade, review, [], [], classification_id="f-1", sim_day=3, created_at=_now_iso())
        assert result.reason == "process_violation"
        assert "1500" in result.evidence

    def test_compliant_day_trade_is_not_process_violation(self) -> None:
        decision = _decision()
        trade = _trade(trading_style="day", duration_minutes=100, closed_sim_minutes=100)
        review = _discipline_review()
        result = classify_failure(decision, trade, review, [], [], classification_id="f-1", sim_day=3, created_at=_now_iso())
        assert result.reason != "process_violation"


class TestClassifyFailureRiskManagement:
    def test_weak_position_sizing_factor_is_risk_management_failure(self) -> None:
        decision = _decision()
        trade = _trade()
        review = _discipline_review(position_sizing_score=30.0)
        result = classify_failure(decision, trade, review, [], [], classification_id="f-1", sim_day=3, created_at=_now_iso())
        assert result.reason == "risk_management_failure"

    def test_strong_position_sizing_factor_is_not_risk_management_failure(self) -> None:
        decision = _decision()
        trade = _trade()
        review = _discipline_review(position_sizing_score=90.0)
        result = classify_failure(decision, trade, review, [], [], classification_id="f-1", sim_day=3, created_at=_now_iso())
        assert result.reason != "risk_management_failure"


class TestClassifyFailureInformationGap:
    def test_incomplete_research_case_study_is_information_gap(self) -> None:
        decision = _decision()
        trade = _trade()
        review = _discipline_review()
        study = _case_study(category="incomplete_research")
        result = classify_failure(decision, trade, review, [study], [], classification_id="f-1", sim_day=3, created_at=_now_iso())
        assert result.reason == "information_gap"
        assert result.evidence == study.missed_information


class TestClassifyFailureMarketRegimeMisread:
    def test_regime_inconsistent_entry_in_hold_window_is_regime_misread(self) -> None:
        decision = _decision()
        trade = _trade(opened_sim_minutes=0, closed_sim_minutes=1500)  # day 0 -> day 1
        review = _discipline_review()
        entry = _learning_entry(for_sim_day=1, regime_consistent=False)
        result = classify_failure(decision, trade, review, [], [entry], classification_id="f-1", sim_day=3, created_at=_now_iso())
        assert result.reason == "market_regime_misread"

    def test_regime_consistent_entry_does_not_trigger(self) -> None:
        decision = _decision()
        trade = _trade(opened_sim_minutes=0, closed_sim_minutes=1500)
        review = _discipline_review()
        entry = _learning_entry(for_sim_day=1, regime_consistent=True)
        result = classify_failure(decision, trade, review, [], [entry], classification_id="f-1", sim_day=3, created_at=_now_iso())
        assert result.reason != "market_regime_misread"

    def test_entry_outside_hold_window_is_ignored(self) -> None:
        decision = _decision()
        trade = _trade(opened_sim_minutes=0, closed_sim_minutes=60)  # day 0 only
        review = _discipline_review()
        entry = _learning_entry(for_sim_day=5, regime_consistent=False)
        result = classify_failure(decision, trade, review, [], [entry], classification_id="f-1", sim_day=3, created_at=_now_iso())
        assert result.reason != "market_regime_misread"


class TestClassifyFailurePoorExecution:
    def test_acted_too_quickly_is_poor_execution(self) -> None:
        decision = _decision()
        trade = _trade()
        review = _discipline_review()
        study = _case_study(category="acted_too_quickly")
        result = classify_failure(decision, trade, review, [study], [], classification_id="f-1", sim_day=3, created_at=_now_iso())
        assert result.reason == "poor_execution"

    def test_ignored_dissent_is_poor_execution(self) -> None:
        decision = _decision()
        trade = _trade()
        review = _discipline_review()
        study = _case_study(category="ignored_dissent")
        result = classify_failure(decision, trade, review, [study], [], classification_id="f-1", sim_day=3, created_at=_now_iso())
        assert result.reason == "poor_execution"


class TestClassifyFailureBadThesis:
    def test_unchallenged_assumptions_is_bad_thesis(self) -> None:
        decision = _decision()
        trade = _trade()
        review = _discipline_review()
        study = _case_study(category="unchallenged_assumptions")
        result = classify_failure(decision, trade, review, [study], [], classification_id="f-1", sim_day=3, created_at=_now_iso())
        assert result.reason == "bad_thesis"

    def test_overconfidence_is_bad_thesis(self) -> None:
        decision = _decision()
        trade = _trade()
        review = _discipline_review()
        study = _case_study(category="overconfidence")
        result = classify_failure(decision, trade, review, [study], [], classification_id="f-1", sim_day=3, created_at=_now_iso())
        assert result.reason == "bad_thesis"

    def test_confirmation_bias_is_bad_thesis(self) -> None:
        decision = _decision()
        trade = _trade()
        review = _discipline_review()
        study = _case_study(category="confirmation_bias")
        result = classify_failure(decision, trade, review, [study], [], classification_id="f-1", sim_day=3, created_at=_now_iso())
        assert result.reason == "bad_thesis"


class TestClassifyFailureUnknown:
    def test_no_real_signal_is_unknown_never_a_guess(self) -> None:
        decision = _decision()
        trade = _trade()
        review = _discipline_review(position_sizing_score=90.0)
        result = classify_failure(decision, trade, review, [], [], classification_id="f-1", sim_day=3, created_at=_now_iso())
        assert result.reason == "unknown"
        assert "Unknown" in result.evidence


class TestClassifyFailurePrecedence:
    def test_process_violation_takes_precedence_over_information_gap(self) -> None:
        decision = _decision()
        trade = _trade(trading_style="day", duration_minutes=1500, closed_sim_minutes=1500)
        review = _discipline_review(position_sizing_score=30.0)
        study = _case_study(category="incomplete_research")
        result = classify_failure(decision, trade, review, [study], [], classification_id="f-1", sim_day=3, created_at=_now_iso())
        assert result.reason == "process_violation"

    def test_information_gap_takes_precedence_over_bad_thesis(self) -> None:
        decision = _decision()
        trade = _trade()
        review = _discipline_review()
        info_study = _case_study(category="incomplete_research", study_id="case-1")
        thesis_study = _case_study(category="overconfidence", study_id="case-2")
        result = classify_failure(decision, trade, review, [info_study, thesis_study], [], classification_id="f-1", sim_day=3, created_at=_now_iso())
        assert result.reason == "information_gap"


class TestClassifyFailureAttribution:
    def test_attributed_agents_are_the_real_supporting_agents(self) -> None:
        decision = _decision(supporting=["echo", "nova"])
        trade = _trade()
        review = _discipline_review()
        result = classify_failure(decision, trade, review, [], [], classification_id="f-1", sim_day=3, created_at=_now_iso())
        assert result.attributed_agents == ["echo", "nova"]
        assert result.trade_id == trade.id
        assert result.decision_id == decision.id
        assert result.symbol == decision.symbol


class TestShouldPromoteFailureClassification:
    def test_named_reason_is_promotable(self) -> None:
        classification = FailureClassification(
            id="f-1", tradeId="trade-1", decisionId="decision-1", symbol="NEXA",
            reason="bad_thesis", evidence="test", attributedAgents=["scout"], tradePnlPct=-5.0, simDay=3, createdAt=_now_iso(),
        )
        assert should_promote_failure_classification(classification) is True

    def test_unknown_is_not_promotable(self) -> None:
        classification = FailureClassification(
            id="f-1", tradeId="trade-1", decisionId="decision-1", symbol="NEXA",
            reason="unknown", evidence="test", attributedAgents=["scout"], tradePnlPct=-5.0, simDay=3, createdAt=_now_iso(),
        )
        assert should_promote_failure_classification(classification) is False


class TestRecordFailureClassification:
    def test_caps_at_max_failure_classifications(self) -> None:
        classifications: list[FailureClassification] = []
        for i in range(MAX_FAILURE_CLASSIFICATIONS + 10):
            classification = FailureClassification(
                id=f"f-{i}", tradeId=f"trade-{i}", decisionId="decision-1", symbol="NEXA",
                reason="unknown", evidence="test", attributedAgents=["scout"], tradePnlPct=-5.0, simDay=3, createdAt=_now_iso(),
            )
            classifications = record_failure_classification(classifications, classification)
        assert len(classifications) == MAX_FAILURE_CLASSIFICATIONS
        assert classifications[-1].id == f"f-{MAX_FAILURE_CLASSIFICATIONS + 9}"
