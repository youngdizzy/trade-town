"""Covers app/process_adherence.py — Trading Psychology & Discipline,
Piece C: the Process Adherence Score. Every case here traces to the
CEO's own review: score ONLY from what this architecture can actually
verify; stop-loss/take-profit/entry-condition/exit-condition/confluence
must always report `not_trackable_yet` — never pass, never fail, never
silently omitted; the score must never imply full plan adherence was
measured.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.process_adherence import DAY_TRADING_MAX_HOLD_MINUTES, compute_process_adherence
from app.schemas import (
    AgentVote,
    ConfidenceFactor,
    DecisionConfidence,
    DisciplineFactor,
    DisciplineReview,
    GatekeeperCheck,
    GatekeeperVerdict,
    PaperTrade,
    PostDecisionReview,
    TradeDecision,
)

_NOT_TRACKABLE_IDS = {"stop_loss_placement", "take_profit_placement", "entry_condition_match", "exit_condition_match", "confluence_requirements"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _check(check_id: str, passed: bool, label: str = "") -> GatekeeperCheck:
    return GatekeeperCheck(id=check_id, label=label or check_id, passed=passed, detail=f"test detail for {check_id}")


def _verdict(checks: list[GatekeeperCheck]) -> GatekeeperVerdict:
    approved = all(c.passed for c in checks)
    return GatekeeperVerdict(approved=approved, checks=checks, summary="test summary", createdAt=_now_iso())


def _decision(*, decision_id: str = "decision-1", gatekeeper_verdict: GatekeeperVerdict | None = None) -> TradeDecision:
    return TradeDecision(
        id=decision_id,
        symbol="NEXA",
        outcome="trade",
        votes=[AgentVote(agentId="echo", choice="buy", reason="trend confirmed")],  # type: ignore[arg-type]
        researchSummary="test research summary",
        technicalSummary="test technical summary",
        fundamentalSummary="test fundamental summary",
        riskSummary="test risk summary",
        supportingAgents=["echo"],  # type: ignore[arg-type]
        opposingAgents=[],  # type: ignore[arg-type]
        confidence=80.0,
        finalReasoning="CEO approved BUY on NEXA.",
        orderId="pos-1" if gatekeeper_verdict is None or gatekeeper_verdict.approved else None,
        confidenceEngine=DecisionConfidence(score=80.0, tier="strong", summary="test", factors=[ConfidenceFactor(name="Research Confidence", score=80.0, weight=0.15, detail="test")]),
        gatekeeperVerdict=gatekeeper_verdict,
        createdAt=_now_iso(),
    )


def _wait_decision(*, decision_id: str = "decision-wait") -> TradeDecision:
    return TradeDecision(
        id=decision_id,
        symbol="NEXA",
        outcome="no_trade",
        votes=[AgentVote(agentId="echo", choice="hold", reason="no edge")],  # type: ignore[arg-type]
        researchSummary="test research summary",
        technicalSummary="test technical summary",
        fundamentalSummary="test fundamental summary",
        riskSummary="test risk summary",
        supportingAgents=[],  # type: ignore[arg-type]
        opposingAgents=[],  # type: ignore[arg-type]
        confidence=50.0,
        finalReasoning="CEO chose to WAIT.",
        orderId=None,
        confidenceEngine=None,
        gatekeeperVerdict=None,
        createdAt=_now_iso(),
    )


def _trade(*, decision_id: str = "decision-1", trading_style: str | None = "day", duration_minutes: int = 60) -> PaperTrade:
    return PaperTrade(
        id="trade-1",
        symbol="NEXA",
        side="buy",
        quantity=10.0,
        entryPrice=100.0,
        exitPrice=110.0,
        pnl=100.0,
        pnlPct=10.0,
        durationMinutes=duration_minutes,
        confidence=80.0,
        reason="test reason",
        marketConditions="test conditions",
        decisionId=decision_id,
        openedAt=_now_iso(),
        closedAt=_now_iso(),
        tradingStyle=trading_style,  # type: ignore[arg-type]
    )


def _discipline_review(*, decision_id: str = "decision-1", tier: str = "sound", score: float = 75.0) -> DisciplineReview:
    return DisciplineReview(
        id="review-1",
        decisionId=decision_id,
        symbol="NEXA",
        score=score,
        tier=tier,  # type: ignore[arg-type]
        factors=[DisciplineFactor(id="research_depth", name="Research Depth", score=80.0, weight=0.2, detail="test")],
        attendees=["echo"],  # type: ignore[arg-type]
        summary="test summary",
        postDecisionReview=PostDecisionReview(),
        outcome="win",
        tradePnlPct=10.0,
        holdDurationMinutes=60,
        simDay=1,
        createdAt=_now_iso(),
    )


class TestComputeProcessAdherence:
    def test_all_pass(self) -> None:
        verdict = _verdict([_check("confidence", True), _check("risk_manager", True)])
        decision = _decision(gatekeeper_verdict=verdict)
        trade = _trade(trading_style="day", duration_minutes=60)
        review = _discipline_review(tier="exemplary")
        read = compute_process_adherence(decision, trade, review)

        assert read.failed_count == 0
        assert read.passed_count == read.verified_count
        assert read.score_pct == 100.0

    def test_one_fails(self) -> None:
        verdict = _verdict([_check("confidence", True), _check("risk_manager", False)])
        decision = _decision(gatekeeper_verdict=verdict)
        trade = _trade()
        review = _discipline_review(tier="sound")
        read = compute_process_adherence(decision, trade, review)

        assert read.failed_count == 1
        failed_ids = [c.id for c in read.checks if c.status == "failed"]
        assert failed_ids == ["gatekeeper_risk_manager"]

    def test_multiple_fail(self) -> None:
        verdict = _verdict([_check("confidence", False), _check("risk_manager", False), _check("exposure", True)])
        decision = _decision(gatekeeper_verdict=verdict)
        trade = _trade(trading_style="day", duration_minutes=DAY_TRADING_MAX_HOLD_MINUTES + 100)
        review = _discipline_review(tier="reckless", score=20.0)
        read = compute_process_adherence(decision, trade, review)

        assert read.failed_count == 4  # 2 gatekeeper + discipline + trading mode
        assert read.score_pct is not None
        assert read.score_pct < 50.0

    def test_stop_loss_take_profit_entry_exit_confluence_are_always_not_trackable(self) -> None:
        verdict = _verdict([_check("confidence", True)])
        decision = _decision(gatekeeper_verdict=verdict)
        read = compute_process_adherence(decision, None, None)

        not_trackable_ids = {c.id for c in read.checks if c.status == "not_trackable_yet"}
        assert _NOT_TRACKABLE_IDS.issubset(not_trackable_ids)
        for check in read.checks:
            if check.id in _NOT_TRACKABLE_IDS:
                assert check.status == "not_trackable_yet"
                assert "future execution/order-plan infrastructure" in check.detail
        # Never scored as pass or fail — confirm they never contribute to verified_count.
        assert read.not_trackable_count >= len(_NOT_TRACKABLE_IDS)

    def test_mixed_pass_fail_and_not_trackable(self) -> None:
        verdict = _verdict([_check("confidence", True), _check("risk_manager", False)])
        decision = _decision(gatekeeper_verdict=verdict)
        # No trade, no discipline review yet — those two checks become not_trackable_yet.
        read = compute_process_adherence(decision, None, None)

        statuses = {c.status for c in read.checks}
        assert statuses == {"passed", "failed", "not_trackable_yet"}
        assert read.verified_count == 2
        assert read.passed_count == 1
        assert read.failed_count == 1
        assert read.score_pct == 50.0

    def test_trading_mode_mismatch_day_trade_held_past_the_same_day_bar_fails(self) -> None:
        verdict = _verdict([_check("confidence", True)])
        decision = _decision(gatekeeper_verdict=verdict)
        trade = _trade(trading_style="day", duration_minutes=DAY_TRADING_MAX_HOLD_MINUTES + 1)
        read = compute_process_adherence(decision, trade, None)

        mode_check = next(c for c in read.checks if c.id == "trading_mode_compliance")
        assert mode_check.status == "failed"
        assert "Day Trading" in mode_check.detail

    def test_trading_mode_swing_trade_never_fails_on_duration(self) -> None:
        verdict = _verdict([_check("confidence", True)])
        decision = _decision(gatekeeper_verdict=verdict)
        trade = _trade(trading_style="swing", duration_minutes=100_000)
        read = compute_process_adherence(decision, trade, None)

        mode_check = next(c for c in read.checks if c.id == "trading_mode_compliance")
        assert mode_check.status == "passed"

    def test_trading_mode_day_trade_within_bar_passes(self) -> None:
        verdict = _verdict([_check("confidence", True)])
        decision = _decision(gatekeeper_verdict=verdict)
        trade = _trade(trading_style="day", duration_minutes=DAY_TRADING_MAX_HOLD_MINUTES)
        read = compute_process_adherence(decision, trade, None)

        mode_check = next(c for c in read.checks if c.id == "trading_mode_compliance")
        assert mode_check.status == "passed"

    def test_trading_mode_untagged_trade_is_not_trackable(self) -> None:
        verdict = _verdict([_check("confidence", True)])
        decision = _decision(gatekeeper_verdict=verdict)
        trade = _trade(trading_style=None)
        read = compute_process_adherence(decision, trade, None)

        mode_check = next(c for c in read.checks if c.id == "trading_mode_compliance")
        assert mode_check.status == "not_trackable_yet"

    def test_risk_limit_violation_shows_as_a_failed_gatekeeper_check(self) -> None:
        verdict = _verdict([_check("confidence", True), _check("exposure", False, "Portfolio Exposure"), _check("correlation", False, "Correlated Positions")])
        decision = _decision(gatekeeper_verdict=verdict)
        read = compute_process_adherence(decision, None, None)

        risk_checks = [c for c in read.checks if c.id in ("gatekeeper_exposure", "gatekeeper_correlation")]
        assert len(risk_checks) == 2
        assert all(c.status == "failed" for c in risk_checks)

    def test_gatekeeper_failure_rejected_decision_shows_the_specific_failed_checks(self) -> None:
        verdict = _verdict([_check("confidence", False), _check("risk_manager", True)])
        decision = _decision(gatekeeper_verdict=verdict)
        assert decision.order_id is None  # rejected — no trade ever opened
        read = compute_process_adherence(decision, None, None)

        confidence_check = next(c for c in read.checks if c.id == "gatekeeper_confidence")
        assert confidence_check.status == "failed"

    def test_no_verified_checks_available_a_wait_decision_scores_none(self) -> None:
        decision = _wait_decision()
        read = compute_process_adherence(decision, None, None)

        assert read.verified_count == 0
        assert read.passed_count == 0
        assert read.failed_count == 0
        assert read.score_pct is None
        assert all(c.status == "not_trackable_yet" for c in read.checks)

    def test_score_never_folds_not_trackable_into_either_side(self) -> None:
        verdict = _verdict([_check("confidence", True)])
        decision = _decision(gatekeeper_verdict=verdict)
        read = compute_process_adherence(decision, None, None)

        # 1 gatekeeper pass, discipline+trading-mode not-trackable, 5 static not-trackable.
        assert read.passed_count == 1
        assert read.failed_count == 0
        assert read.verified_count == 1
        assert read.not_trackable_count == 7
        assert read.score_pct == 100.0

    def test_gatekeeper_none_reports_not_applicable_never_omitted(self) -> None:
        decision = _wait_decision()
        read = compute_process_adherence(decision, None, None)
        gatekeeper_check = next(c for c in read.checks if c.id == "gatekeeper_verdict")
        assert gatekeeper_check.status == "not_trackable_yet"

    def test_discipline_review_weak_or_reckless_tier_fails(self) -> None:
        verdict = _verdict([_check("confidence", True)])
        decision = _decision(gatekeeper_verdict=verdict)
        weak_review = _discipline_review(tier="weak", score=45.0)
        read = compute_process_adherence(decision, None, weak_review)
        discipline_check = next(c for c in read.checks if c.id == "discipline_process_quality")
        assert discipline_check.status == "failed"

    def test_discipline_review_adequate_tier_passes(self) -> None:
        verdict = _verdict([_check("confidence", True)])
        decision = _decision(gatekeeper_verdict=verdict)
        review = _discipline_review(tier="adequate", score=58.0)
        read = compute_process_adherence(decision, None, review)
        discipline_check = next(c for c in read.checks if c.id == "discipline_process_quality")
        assert discipline_check.status == "passed"

    def test_result_is_stamped_with_the_real_decision_id_and_symbol(self) -> None:
        decision = _decision(decision_id="decision-xyz")
        read = compute_process_adherence(decision, None, None)
        assert read.decision_id == "decision-xyz"
        assert read.symbol == "NEXA"
