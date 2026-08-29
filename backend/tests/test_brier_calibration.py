"""Covers app/prediction_tracking.py::compute_brier_calibration() — CEO
directive "Professional Quant Trading Core," Phase B P2 item. The real
Brier score is a standard proper scoring rule over the already-real
Prediction Records ledger — this suite verifies the score matches its
own textbook formula on hand-picked cases, never a fabricated number."""
from __future__ import annotations

import pytest

from app.prediction_tracking import (
    MIN_PREDICTIONS_FOR_BRIER_VERDICT,
    MIN_PREDICTIONS_FOR_BUCKET_VERDICT,
    compute_agent_brier_calibration,
    compute_brier_calibration,
)
from app.schemas import AGENT_IDS, AgentId, PredictionRecord


def _prediction(n: int, *, confidence_pct: float, outcome: str = "pending", attributed_agents: list[AgentId] | None = None) -> PredictionRecord:
    return PredictionRecord(
        id=f"prediction-{n}",
        decisionId=f"decision-{n}",
        symbol="NEXA",
        claimType="trade_direction",
        predictedDirection="buy",
        confidencePct=confidence_pct,
        attributedAgents=attributed_agents if attributed_agents is not None else ["scout"],
        outcome=outcome,  # type: ignore[arg-type]
        simDay=1,
        createdAt="2026-01-01T00:00:00+00:00",
    )


class TestComputeBrierCalibration:
    def test_below_minimum_resolved_count_is_not_enough_data(self) -> None:
        predictions = [_prediction(i, confidence_pct=80.0, outcome="correct") for i in range(MIN_PREDICTIONS_FOR_BRIER_VERDICT - 1)]
        result = compute_brier_calibration(predictions)
        assert result.evidence_state == "not_enough_data"
        assert result.brier_score is None
        assert result.resolved_prediction_count == MIN_PREDICTIONS_FOR_BRIER_VERDICT - 1

    def test_pending_predictions_are_excluded_from_the_resolved_count(self) -> None:
        pending = [_prediction(i, confidence_pct=80.0, outcome="pending") for i in range(20)]
        resolved = [_prediction(100 + i, confidence_pct=80.0, outcome="correct") for i in range(MIN_PREDICTIONS_FOR_BRIER_VERDICT)]
        result = compute_brier_calibration(pending + resolved)
        assert result.resolved_prediction_count == MIN_PREDICTIONS_FOR_BRIER_VERDICT

    def test_perfectly_calibrated_confident_correct_calls_score_near_zero(self) -> None:
        # 100% confidence, always correct -> (1.0 - 1.0)^2 = 0 for every one.
        predictions = [_prediction(i, confidence_pct=100.0, outcome="correct") for i in range(MIN_PREDICTIONS_FOR_BRIER_VERDICT)]
        result = compute_brier_calibration(predictions)
        assert result.evidence_state == "sufficient_evidence"
        assert result.brier_score == 0.0

    def test_confident_but_always_wrong_scores_near_one(self) -> None:
        # 100% confidence, always incorrect -> (1.0 - 0.0)^2 = 1 for every one.
        predictions = [_prediction(i, confidence_pct=100.0, outcome="incorrect") for i in range(MIN_PREDICTIONS_FOR_BRIER_VERDICT)]
        result = compute_brier_calibration(predictions)
        assert result.brier_score == 1.0

    def test_matches_the_real_textbook_formula_on_a_hand_computed_case(self) -> None:
        # Real hand-computed mix: (0.9-1)^2=.01, (0.5-0)^2=.25, (0.7-1)^2=.09, (0.6-0)^2=.36
        # mean = (.01+.25+.09+.36)/4 = 0.1775 -- repeated to clear the minimum sample size.
        base = [
            _prediction(1, confidence_pct=90.0, outcome="correct"),
            _prediction(2, confidence_pct=50.0, outcome="incorrect"),
            _prediction(3, confidence_pct=70.0, outcome="correct"),
            _prediction(4, confidence_pct=60.0, outcome="incorrect"),
        ]
        predictions = base * 3  # 12 real resolved predictions, same real distribution
        result = compute_brier_calibration(predictions)
        assert result.brier_score == 0.1775

    def test_a_constant_fifty_percent_forecaster_on_a_balanced_outcome_scores_a_quarter(self) -> None:
        half = MIN_PREDICTIONS_FOR_BRIER_VERDICT
        predictions = [_prediction(i, confidence_pct=50.0, outcome="correct") for i in range(half)] + [
            _prediction(100 + i, confidence_pct=50.0, outcome="incorrect") for i in range(half)
        ]
        result = compute_brier_calibration(predictions)
        assert result.brier_score == 0.25

    def test_bucket_below_minimum_sample_withholds_real_accuracy(self) -> None:
        predictions = [_prediction(i, confidence_pct=95.0, outcome="correct") for i in range(MIN_PREDICTIONS_FOR_BUCKET_VERDICT - 1)]
        # pad with an unrelated, well-sampled bucket to clear the overall minimum.
        padding = [_prediction(100 + i, confidence_pct=55.0, outcome="incorrect") for i in range(MIN_PREDICTIONS_FOR_BRIER_VERDICT)]
        result = compute_brier_calibration(predictions + padding)
        thin_bucket = next(b for b in result.buckets if b.range_low_pct == 90.0)
        assert thin_bucket.predicted_count == MIN_PREDICTIONS_FOR_BUCKET_VERDICT - 1
        assert thin_bucket.real_accuracy_pct is None

    def test_bucket_at_or_above_minimum_sample_reports_real_accuracy(self) -> None:
        predictions = [_prediction(i, confidence_pct=95.0, outcome="correct" if i % 2 == 0 else "incorrect") for i in range(MIN_PREDICTIONS_FOR_BRIER_VERDICT)]
        result = compute_brier_calibration(predictions)
        bucket = next(b for b in result.buckets if b.range_low_pct == 90.0)
        assert bucket.real_accuracy_pct == 50.0
        assert bucket.avg_stated_confidence_pct == 95.0

    def test_a_hundred_percent_confidence_prediction_lands_in_the_top_bucket(self) -> None:
        predictions = [_prediction(i, confidence_pct=100.0, outcome="correct") for i in range(MIN_PREDICTIONS_FOR_BRIER_VERDICT)]
        result = compute_brier_calibration(predictions)
        assert len(result.buckets) == 1
        assert result.buckets[0].range_low_pct == 90.0
        assert result.buckets[0].range_high_pct == 100.0

    def test_summary_discloses_the_real_score_and_sample_size(self) -> None:
        predictions = [_prediction(i, confidence_pct=100.0, outcome="correct") for i in range(MIN_PREDICTIONS_FOR_BRIER_VERDICT)]
        result = compute_brier_calibration(predictions)
        assert str(MIN_PREDICTIONS_FOR_BRIER_VERDICT) in result.summary
        assert "0.000" in result.summary


class TestComputeAgentBrierCalibration:
    """CEO directive "Professional Quant Portfolio Intelligence + Alpha
    Research Engine," Phase 7 — the exact same real Brier methodology,
    broken out per real named agent via PredictionRecord.attributedAgents."""

    def test_returns_one_entry_per_real_agent_id(self) -> None:
        result = compute_agent_brier_calibration([])
        assert {r.agent_id for r in result} == set(AGENT_IDS)

    def test_an_agent_with_no_attributed_predictions_reads_not_enough_data(self) -> None:
        predictions = [_prediction(i, confidence_pct=90.0, outcome="correct", attributed_agents=["scout"]) for i in range(MIN_PREDICTIONS_FOR_BRIER_VERDICT)]
        result = compute_agent_brier_calibration(predictions)
        atlas = next(r for r in result if r.agent_id == "atlas")
        assert atlas.calibration.evidence_state == "not_enough_data"
        assert atlas.calibration.resolved_prediction_count == 0

    def test_an_overconfident_agent_is_isolated_from_a_well_calibrated_one(self) -> None:
        # Scout: 100% confidence, always correct -> real Brier 0.0.
        scout_predictions = [_prediction(i, confidence_pct=100.0, outcome="correct", attributed_agents=["scout"]) for i in range(MIN_PREDICTIONS_FOR_BRIER_VERDICT)]
        # Atlas: 90% confidence, always wrong -> real Brier (0.9-0)^2 = 0.81, a genuinely
        # overconfident real track record — exactly the case the directive names.
        atlas_predictions = [
            _prediction(100 + i, confidence_pct=90.0, outcome="incorrect", attributed_agents=["atlas"]) for i in range(MIN_PREDICTIONS_FOR_BRIER_VERDICT)
        ]
        result = compute_agent_brier_calibration(scout_predictions + atlas_predictions)
        scout = next(r for r in result if r.agent_id == "scout")
        atlas = next(r for r in result if r.agent_id == "atlas")
        assert scout.calibration.brier_score == 0.0
        assert atlas.calibration.brier_score == pytest.approx(0.81)
        # Neither agent's real read was diluted by the other's real predictions.
        assert scout.calibration.resolved_prediction_count == MIN_PREDICTIONS_FOR_BRIER_VERDICT
        assert atlas.calibration.resolved_prediction_count == MIN_PREDICTIONS_FOR_BRIER_VERDICT

    def test_a_jointly_attributed_prediction_counts_toward_every_real_attributed_agent(self) -> None:
        # A real decision multiple agents jointly supported — each
        # agent's own calibration read honestly includes it, no
        # fabricated split.
        joint = [_prediction(i, confidence_pct=80.0, outcome="correct", attributed_agents=["scout", "atlas"]) for i in range(MIN_PREDICTIONS_FOR_BRIER_VERDICT)]
        result = compute_agent_brier_calibration(joint)
        scout = next(r for r in result if r.agent_id == "scout")
        atlas = next(r for r in result if r.agent_id == "atlas")
        assert scout.calibration.resolved_prediction_count == MIN_PREDICTIONS_FOR_BRIER_VERDICT
        assert atlas.calibration.resolved_prediction_count == MIN_PREDICTIONS_FOR_BRIER_VERDICT
        assert scout.calibration.brier_score == atlas.calibration.brier_score
