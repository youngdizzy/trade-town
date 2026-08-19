"""Covers app/control_effectiveness.py — CEO directive "Features 31-35:
Compliance, Governance & Continuous Improvement System," Feature 34
(Compliance Control Effectiveness). A control that has never once failed
a decision must read NOT_YET_TESTED, never a fabricated "effective";
outcomes must only be attributed to a control when it was the SOLE
failing check for that decision, never guessed at across multiple
simultaneously-failing checks; and a control's history must genuinely
split into an earlier/later half before CONTROL REGRESSION is flagged.
"""
from __future__ import annotations

from app.control_effectiveness import (
    MIN_CONTROL_SAMPLE_FOR_VERDICT,
    compute_control_effectiveness,
)
from app.schemas import GatekeeperCheck, GatekeeperRejection, GatekeeperVerdict, TradeDecision


def _check(control_id: str, passed: bool, label: str = "x") -> GatekeeperCheck:
    return GatekeeperCheck(id=control_id, label=label, passed=passed, detail="detail")


def _decision(
    decision_id: str,
    checks: list[GatekeeperCheck],
    *,
    created_at: str = "2026-01-01T00:00:00+00:00",
) -> TradeDecision:
    approved = all(c.passed for c in checks)
    return TradeDecision(
        id=decision_id,
        symbol="NEXA",
        outcome="trade" if approved else "no_trade",
        researchSummary="x",
        technicalSummary="x",
        fundamentalSummary="x",
        riskSummary="x",
        confidence=70.0,
        finalReasoning="x",
        gatekeeperVerdict=GatekeeperVerdict(approved=approved, checks=checks, summary="x", createdAt=created_at),
        createdAt=created_at,
    )


def _rejection(
    decision_id: str,
    *,
    outcome: str = "pending",
    rejected_sim_minutes: int = 0,
    resolved_at: str | None = None,
) -> GatekeeperRejection:
    return GatekeeperRejection(
        id=f"gkreject-{decision_id}",
        proposalId=f"proposal-{decision_id}",
        symbol="NEXA",
        ceoChoice="buy",
        reasons=["x"],
        priceAtRejection=100.0,
        rejectedSimMinutes=rejected_sim_minutes,
        outcome=outcome,  # type: ignore[arg-type]
        createdAt="2026-01-01T00:00:00+00:00",
        resolvedAt=resolved_at,
    )


class TestNotYetTested:
    def test_a_control_that_never_failed_reads_not_yet_tested_not_effective(self) -> None:
        decisions = [_decision("d1", [_check("confidence", True), _check("agreement", True)])]
        summary = compute_control_effectiveness(decisions, [])
        confidence = next(c for c in summary.controls if c.control_id == "confidence")
        assert confidence.effectiveness_state == "not_yet_tested"
        assert confidence.triggered_count == 1
        assert confidence.failed_count == 0

    def test_a_control_never_evaluated_by_any_decision_also_reads_not_yet_tested(self) -> None:
        decisions = [_decision("d1", [_check("agreement", True)])]
        summary = compute_control_effectiveness(decisions, [])
        confidence = next(c for c in summary.controls if c.control_id == "confidence")
        assert confidence.effectiveness_state == "not_yet_tested"
        assert confidence.triggered_count == 0


class TestSoleReasonAttribution:
    def test_a_sole_failing_check_confirmed_would_have_lost_counts_as_prevented(self) -> None:
        decisions = [_decision("d1", [_check("confidence", False), _check("agreement", True)])]
        rejections = [_rejection("d1", outcome="would_have_lost", resolved_at="2026-01-02T00:00:00+00:00")]
        summary = compute_control_effectiveness(decisions, rejections)
        confidence = next(c for c in summary.controls if c.control_id == "confidence")
        assert confidence.sole_reason_rejection_count == 1
        assert confidence.confirmed_prevented_count == 1
        assert confidence.confirmed_false_positive_count == 0
        assert confidence.ambiguous_attribution_count == 0

    def test_a_sole_failing_check_confirmed_would_have_won_counts_as_false_positive(self) -> None:
        decisions = [_decision("d1", [_check("confidence", False), _check("agreement", True)])]
        rejections = [_rejection("d1", outcome="would_have_won", resolved_at="2026-01-02T00:00:00+00:00")]
        summary = compute_control_effectiveness(decisions, rejections)
        confidence = next(c for c in summary.controls if c.control_id == "confidence")
        assert confidence.confirmed_false_positive_count == 1
        assert confidence.confirmed_prevented_count == 0

    def test_a_still_pending_rejection_is_not_confirmed_either_way(self) -> None:
        decisions = [_decision("d1", [_check("confidence", False), _check("agreement", True)])]
        rejections = [_rejection("d1", outcome="pending")]
        summary = compute_control_effectiveness(decisions, rejections)
        confidence = next(c for c in summary.controls if c.control_id == "confidence")
        assert confidence.pending_evaluation_count == 1
        assert confidence.confirmed_prevented_count == 0
        assert confidence.confirmed_false_positive_count == 0

    def test_a_missing_rejection_record_is_also_treated_as_not_yet_confirmed(self) -> None:
        decisions = [_decision("d1", [_check("confidence", False), _check("agreement", True)])]
        summary = compute_control_effectiveness(decisions, [])
        confidence = next(c for c in summary.controls if c.control_id == "confidence")
        assert confidence.pending_evaluation_count == 1

    def test_two_checks_failing_together_is_never_attributed_to_either_one(self) -> None:
        decisions = [_decision("d1", [_check("confidence", False), _check("agreement", False)])]
        rejections = [_rejection("d1", outcome="would_have_lost", resolved_at="2026-01-02T00:00:00+00:00")]
        summary = compute_control_effectiveness(decisions, rejections)
        confidence = next(c for c in summary.controls if c.control_id == "confidence")
        agreement = next(c for c in summary.controls if c.control_id == "agreement")
        assert confidence.ambiguous_attribution_count == 1
        assert agreement.ambiguous_attribution_count == 1
        assert confidence.confirmed_prevented_count == 0
        assert confidence.sole_reason_rejection_count == 0


class TestEvaluationStates:
    def test_below_min_sample_stays_insufficient_data(self) -> None:
        decisions = [
            _decision(f"d{i}", [_check("confidence", False), _check("agreement", True)])
            for i in range(MIN_CONTROL_SAMPLE_FOR_VERDICT - 1)
        ]
        rejections = [
            _rejection(f"d{i}", outcome="would_have_lost", resolved_at="2026-01-02T00:00:00+00:00")
            for i in range(MIN_CONTROL_SAMPLE_FOR_VERDICT - 1)
        ]
        summary = compute_control_effectiveness(decisions, rejections)
        confidence = next(c for c in summary.controls if c.control_id == "confidence")
        assert confidence.effectiveness_state == "insufficient_data"

    def test_high_prevented_rate_at_min_sample_reads_effective(self) -> None:
        decisions = [
            _decision(f"d{i}", [_check("confidence", False), _check("agreement", True)])
            for i in range(MIN_CONTROL_SAMPLE_FOR_VERDICT)
        ]
        rejections = [
            _rejection(f"d{i}", outcome="would_have_lost", resolved_at="2026-01-02T00:00:00+00:00")
            for i in range(MIN_CONTROL_SAMPLE_FOR_VERDICT)
        ]
        summary = compute_control_effectiveness(decisions, rejections)
        confidence = next(c for c in summary.controls if c.control_id == "confidence")
        assert confidence.effectiveness_state == "effective"

    def test_low_prevented_rate_reads_ineffective(self) -> None:
        decisions = [
            _decision(f"d{i}", [_check("confidence", False), _check("agreement", True)])
            for i in range(5)
        ]
        rejections = [
            _rejection(f"d{i}", outcome="would_have_won", resolved_at="2026-01-02T00:00:00+00:00")
            for i in range(5)
        ]
        summary = compute_control_effectiveness(decisions, rejections)
        confidence = next(c for c in summary.controls if c.control_id == "confidence")
        assert confidence.effectiveness_state == "ineffective"

    def test_mid_prevented_rate_reads_mixed_not_insufficient_data(self) -> None:
        outcomes = ["would_have_lost", "would_have_lost", "would_have_won", "would_have_won", "would_have_won"]
        decisions = [_decision(f"d{i}", [_check("confidence", False), _check("agreement", True)]) for i in range(5)]
        rejections = [
            _rejection(f"d{i}", outcome=outcomes[i], resolved_at="2026-01-02T00:00:00+00:00") for i in range(5)
        ]
        summary = compute_control_effectiveness(decisions, rejections)
        confidence = next(c for c in summary.controls if c.control_id == "confidence")
        assert confidence.effectiveness_state == "mixed"


class TestControlRegression:
    def test_effective_then_ineffective_flags_regression(self) -> None:
        n = MIN_CONTROL_SAMPLE_FOR_VERDICT
        decisions = []
        rejections = []
        for i in range(n):
            day = f"2026-01-{i + 1:02d}T00:00:00+00:00"
            decisions.append(_decision(f"early{i}", [_check("confidence", False), _check("agreement", True)], created_at=day))
            rejections.append(_rejection(f"early{i}", outcome="would_have_lost", resolved_at=day))
        for i in range(n):
            day = f"2026-02-{i + 1:02d}T00:00:00+00:00"
            decisions.append(_decision(f"late{i}", [_check("confidence", False), _check("agreement", True)], created_at=day))
            rejections.append(_rejection(f"late{i}", outcome="would_have_won", resolved_at=day))
        summary = compute_control_effectiveness(decisions, rejections)
        confidence = next(c for c in summary.controls if c.control_id == "confidence")
        assert confidence.control_regression is True
        assert summary.regressed_control_count == 1

    def test_consistently_effective_never_flags_regression(self) -> None:
        n = MIN_CONTROL_SAMPLE_FOR_VERDICT * 2
        decisions = []
        rejections = []
        for i in range(n):
            day = f"2026-01-{i + 1:02d}T00:00:00+00:00"
            decisions.append(_decision(f"d{i}", [_check("confidence", False), _check("agreement", True)], created_at=day))
            rejections.append(_rejection(f"d{i}", outcome="would_have_lost", resolved_at=day))
        summary = compute_control_effectiveness(decisions, rejections)
        confidence = next(c for c in summary.controls if c.control_id == "confidence")
        assert confidence.control_regression is False


class TestSummaryAggregates:
    def test_summary_counts_match_control_states(self) -> None:
        decisions = [_decision("d1", [_check("confidence", True), _check("agreement", True)])]
        summary = compute_control_effectiveness(decisions, [])
        assert summary.total_controls == 11
        assert summary.not_yet_tested_count == 11
        assert summary.effective_count == 0
        assert summary.ineffective_count == 0
        assert summary.mixed_count == 0
        assert summary.insufficient_data_count == 0

    def test_decisions_without_a_gatekeeper_verdict_are_ignored(self) -> None:
        decision = TradeDecision(
            id="d1",
            symbol="NEXA",
            outcome="no_trade",
            researchSummary="x",
            technicalSummary="x",
            fundamentalSummary="x",
            riskSummary="x",
            confidence=70.0,
            finalReasoning="x",
            createdAt="2026-01-01T00:00:00+00:00",
        )
        summary = compute_control_effectiveness([decision], [])
        assert all(c.triggered_count == 0 for c in summary.controls)
        assert summary.not_yet_tested_count == 11
