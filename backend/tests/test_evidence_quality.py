"""Covers app/evidence_quality.py — CEO directive "TradeTown — Phase 10:
Real Data + True Holdout + Portfolio Intelligence," Section E."""
from __future__ import annotations

import inspect

from app.evidence_quality import build_evidence_quality_report, classify_evidence_state
from app.research_loop import RESEARCH_CANDIDATE_MIN_TRADE_COUNT


class TestClassifyEvidenceState:
    def test_below_sample_floor_is_insufficient_data(self) -> None:
        state, _detail = classify_evidence_state(
            data_provenance="simulated", data_quality_valid=True, point_in_time_verified=True, holdout_status=None, sample_size=5
        )
        assert state == "insufficient_data"

    def test_none_sample_size_is_insufficient_data(self) -> None:
        state, _detail = classify_evidence_state(
            data_provenance="simulated", data_quality_valid=True, point_in_time_verified=True, holdout_status=None, sample_size=None
        )
        assert state == "insufficient_data"

    def test_failed_data_quality_is_insufficient_data_even_with_enough_trades(self) -> None:
        state, _detail = classify_evidence_state(
            data_provenance="simulated", data_quality_valid=False, point_in_time_verified=True, holdout_status=None, sample_size=1000
        )
        assert state == "insufficient_data"

    def test_valid_holdout_over_simulated_data_is_holdout_validated_not_external(self) -> None:
        state, detail = classify_evidence_state(
            data_provenance="simulated", data_quality_valid=True, point_in_time_verified=True, holdout_status="valid", sample_size=RESEARCH_CANDIDATE_MIN_TRADE_COUNT
        )
        assert state == "holdout_validated"
        assert "simulated" in detail

    def test_valid_holdout_over_real_data_is_external_data_validated(self) -> None:
        state, _detail = classify_evidence_state(
            data_provenance="real", data_quality_valid=True, point_in_time_verified=True, holdout_status="valid", sample_size=RESEARCH_CANDIDATE_MIN_TRADE_COUNT
        )
        assert state == "external_data_validated"

    def test_invalid_holdout_never_reaches_holdout_validated(self) -> None:
        state, _detail = classify_evidence_state(
            data_provenance="simulated", data_quality_valid=True, point_in_time_verified=True, holdout_status="invalid", sample_size=RESEARCH_CANDIDATE_MIN_TRADE_COUNT
        )
        assert state != "holdout_validated"
        assert state != "external_data_validated"

    def test_unavailable_holdout_falls_through_to_research_validated(self) -> None:
        state, _detail = classify_evidence_state(
            data_provenance="simulated", data_quality_valid=True, point_in_time_verified=True, holdout_status="unavailable", sample_size=RESEARCH_CANDIDATE_MIN_TRADE_COUNT
        )
        assert state == "research_validated"

    def test_clean_research_funnel_no_holdout_is_research_validated(self) -> None:
        state, _detail = classify_evidence_state(
            data_provenance="simulated", data_quality_valid=True, point_in_time_verified=True, holdout_status=None, sample_size=RESEARCH_CANDIDATE_MIN_TRADE_COUNT
        )
        assert state == "research_validated"

    def test_unclean_funnel_with_simulated_data_is_simulated_only(self) -> None:
        state, _detail = classify_evidence_state(
            data_provenance="simulated", data_quality_valid=True, point_in_time_verified=False, holdout_status=None, sample_size=RESEARCH_CANDIDATE_MIN_TRADE_COUNT
        )
        assert state == "simulated_only"

    def test_state_never_fabricates_external_validation_without_a_valid_holdout(self) -> None:
        state, _detail = classify_evidence_state(
            data_provenance="real", data_quality_valid=True, point_in_time_verified=True, holdout_status=None, sample_size=RESEARCH_CANDIDATE_MIN_TRADE_COUNT
        )
        assert state != "external_data_validated"


class TestBuildEvidenceQualityReport:
    def test_report_carries_every_real_input_field_unmodified(self) -> None:
        report = build_evidence_quality_report(
            definition_id="d1",
            definition_version=1,
            data_provenance="simulated",
            data_quality_valid=True,
            point_in_time_verified=True,
            holdout_status="valid",
            sample_size=150,
            external_provider_available=False,
            benchmark_available=True,
            adversarial_coverage=True,
            report_id="eq-1",
        )
        assert report.data_provenance == "simulated"
        assert report.sample_size == 150
        assert report.external_provider_available is False
        assert report.state == "holdout_validated"


class TestNeverAPromotionAuthority:
    def test_champion_challenger_never_imports_evidence_quality(self) -> None:
        import app.champion_challenger as champion_challenger_module

        source = inspect.getsource(champion_challenger_module)
        assert "evidence_quality" not in source

    def test_strategy_lab_never_imports_evidence_quality(self) -> None:
        import app.strategy_lab as strategy_lab_module

        source = inspect.getsource(strategy_lab_module)
        assert "evidence_quality" not in source
