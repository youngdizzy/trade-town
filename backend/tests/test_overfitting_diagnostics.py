"""Covers app/overfitting_diagnostics.py — CEO directive "Professional
Quant Firm Phase," Feature 39's real, deterministic relabeling of three
already-real verdicts into the directive's own requested vocabulary.
"""
from __future__ import annotations

from app.overfitting_diagnostics import classify_overfitting_risk
from app.schemas import CostSensitivityResult, ParameterSensitivityResult, WalkForwardValidationResult


def _walk_forward(verdict: str) -> WalkForwardValidationResult:
    return WalkForwardValidationResult(
        id="wf-1", definitionId="def-1", definitionVersion=1, windowBars=500, symbols=[],
        verdict=verdict, detail="d", dataHonestyNote="n", generatedAt="2024-01-01T00:00:00+00:00",  # type: ignore[arg-type]
    )


def _parameter_sensitivity(verdict: str) -> ParameterSensitivityResult:
    return ParameterSensitivityResult(
        id="ps-1", definitionId="def-1", definitionVersion=1, stopAxis=None, targetAxis=None,
        verdict=verdict, detail="d", multipleTestingNote="n", dataHonestyNote="n", generatedAt="2024-01-01T00:00:00+00:00",  # type: ignore[arg-type]
    )


def _cost_sensitivity(verdict: str) -> CostSensitivityResult:
    return CostSensitivityResult(
        id="cs-1", definitionId="def-1", definitionVersion=1, scenarios=[],
        verdict=verdict, detail="d", dataHonestyNote="n", generatedAt="2024-01-01T00:00:00+00:00",  # type: ignore[arg-type]
    )


class TestClassifyOverfittingRisk:
    def test_unstable_walk_forward_reads_oos_failure_regardless_of_other_axes(self) -> None:
        diagnosis = classify_overfitting_risk(_walk_forward("unstable"), _parameter_sensitivity("robust"), _cost_sensitivity("cost_resilient"))
        assert diagnosis.verdict == "oos_failure"

    def test_fragile_parameter_sensitivity_with_stable_walk_forward_reads_overfit_suspected(self) -> None:
        diagnosis = classify_overfitting_risk(_walk_forward("stable"), _parameter_sensitivity("fragile"), _cost_sensitivity("cost_resilient"))
        assert diagnosis.verdict == "overfit_suspected"

    def test_cost_sensitive_with_stable_walk_forward_reads_overfit_suspected(self) -> None:
        diagnosis = classify_overfitting_risk(_walk_forward("stable"), _parameter_sensitivity("robust"), _cost_sensitivity("cost_sensitive"))
        assert diagnosis.verdict == "overfit_suspected"

    def test_all_three_insufficient_data_reads_insufficient_data(self) -> None:
        diagnosis = classify_overfitting_risk(_walk_forward("insufficient_data"), _parameter_sensitivity("insufficient_data"), _cost_sensitivity("insufficient_data"))
        assert diagnosis.verdict == "insufficient_data"

    def test_one_axis_insufficient_data_with_favorable_others_reads_pending_validation(self) -> None:
        diagnosis = classify_overfitting_risk(_walk_forward("stable"), _parameter_sensitivity("robust"), _cost_sensitivity("insufficient_data"))
        assert diagnosis.verdict == "pending_validation"
        assert "cost sensitivity" in diagnosis.detail

    def test_every_axis_favorable_reads_robust(self) -> None:
        diagnosis = classify_overfitting_risk(_walk_forward("stable"), _parameter_sensitivity("robust"), _cost_sensitivity("cost_resilient"))
        assert diagnosis.verdict == "robust"

    def test_oos_failure_takes_priority_over_insufficient_data_on_other_axes(self) -> None:
        # An unstable walk-forward result is real, disqualifying evidence on its own —
        # missing data elsewhere must never soften or hide it.
        diagnosis = classify_overfitting_risk(_walk_forward("unstable"), _parameter_sensitivity("insufficient_data"), _cost_sensitivity("insufficient_data"))
        assert diagnosis.verdict == "oos_failure"

    def test_the_result_always_cites_the_real_underlying_verdicts_it_was_built_from(self) -> None:
        diagnosis = classify_overfitting_risk(_walk_forward("stable"), _parameter_sensitivity("robust"), _cost_sensitivity("cost_resilient"))
        assert diagnosis.walk_forward_verdict == "stable"
        assert diagnosis.parameter_sensitivity_verdict == "robust"
        assert diagnosis.cost_sensitivity_verdict == "cost_resilient"
