"""Covers app/paper_readiness.py — CEO directive "TradeTown — Paper-Trading
Readiness + Professional Strategy Validation Hardening," Section 1."""
from __future__ import annotations

import inspect

from app.evidence_quality import build_evidence_quality_report
from app.paper_readiness import evaluate_paper_readiness
from app.schemas import (
    BenchmarkComparison,
    BuyAndHoldBaseline,
    CompiledStrategyBacktestResult,
    CostSensitivityResult,
    DataPartitionSummary,
    EmaPullbackStatsBucket,
    EvidenceQualityReport,
    HoldoutValidationReport,
    LookAheadAuditResult,
    OverfittingDiagnosis,
    ParameterSensitivityAxisResult,
    ParameterSensitivityResult,
    ResearchExperimentRecord,
    StrategyComplexityScore,
    WalkForwardSymbolResult,
    WalkForwardValidationResult,
)

_CREATED_AT = "2024-01-01T00:00:00+00:00"
_TEXT = "Buy when price closes above the 50 EMA, then enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R."


def _bucket(**overrides: object) -> EmaPullbackStatsBucket:
    base: dict[str, object] = dict(
        label="overall", tradeCount=120, winCount=70, lossCount=50, openCount=0,
        winRatePct=58.3, avgWinR=1.5, avgLossR=-0.9, expectancyR=0.45, profitFactor=1.8,
        maxDrawdownR=-3.0, largestWinR=2.0, largestLossR=-1.0, verdict="enough_evidence", detail="x",
    )
    base.update(overrides)
    return EmaPullbackStatsBucket(**base)  # type: ignore[arg-type]


def _record(
    *,
    overall: EmaPullbackStatsBucket | None = None,
    walk_forward_verdict: str = "stable",
    cost_verdict: str = "cost_resilient",
    parameter_verdict: str = "robust",
    lookahead_verdict: str = "clean",
) -> ResearchExperimentRecord:
    bucket = overall or _bucket()
    backtest = CompiledStrategyBacktestResult(
        id="bt-1", definitionId="def-1", definitionVersion=1, symbolsTested=["AAPL"], timeframe="1h", candlesPerSymbol=6000,
        overall=bucket, sessionBreakdown=[], instrumentBreakdown=[bucket.model_copy(update={"label": "AAPL"})],
        regimeTrendBreakdown=[], regimeVolatilityBreakdown=[], modelValidation=None, monteCarlo=None, dataHonestyNote="x", generatedAt=_CREATED_AT,
    )
    walk_forward = WalkForwardValidationResult(
        id="wf-1", definitionId="def-1", definitionVersion=1, windowBars=1000,
        symbols=[WalkForwardSymbolResult(symbol="AAPL", windows=[], positiveWindowCount=0, negativeWindowCount=0, evaluatedWindowCount=0, detail="x")],
        verdict=walk_forward_verdict, detail="x", dataHonestyNote="x", generatedAt=_CREATED_AT,  # type: ignore[arg-type]
    )
    cost_sensitivity = CostSensitivityResult(
        id="cs-1", definitionId="def-1", definitionVersion=1, scenarios=[], verdict=cost_verdict, detail="x", dataHonestyNote="x", generatedAt=_CREATED_AT,  # type: ignore[arg-type]
    )
    empty_axis = ParameterSensitivityAxisResult(parameter="stop", sweepable=True, baseValue=1.0, points=[], detail="x")
    parameter_sensitivity = ParameterSensitivityResult(
        id="ps-1", definitionId="def-1", definitionVersion=1, stopAxis=empty_axis, targetAxis=empty_axis, verdict=parameter_verdict, detail="x", multipleTestingNote="x", dataHonestyNote="x", generatedAt=_CREATED_AT,  # type: ignore[arg-type]
    )
    look_ahead = LookAheadAuditResult(id="la-1", definitionId="def-1", definitionVersion=1, setupsChecked=10, violations=[], verdict=lookahead_verdict, detail="x", generatedAt=_CREATED_AT)  # type: ignore[arg-type]
    complexity = StrategyComplexityScore(definitionId="def-1", definitionVersion=1, stepCount=3, conditionCount=1, distinctIndicatorCount=2, parameterCount=5, complexityScore=11, band="moderate", detail="x", generatedAt=_CREATED_AT)  # type: ignore[arg-type]
    overfitting = OverfittingDiagnosis(verdict="pending_validation", detail="x", walkForwardVerdict=walk_forward_verdict, parameterSensitivityVerdict=parameter_verdict, costSensitivityVerdict=cost_verdict)  # type: ignore[arg-type]
    return ResearchExperimentRecord(
        id="exp-1", definitionId="def-1", definitionName="Test Strategy", definitionVersion=1, sourceText=_TEXT,
        symbolsTested=["AAPL"], timeframe="1h", candlesPerSymbol=6000, backtest=backtest, walkForward=walk_forward,
        parameterSensitivity=parameter_sensitivity, costSensitivity=cost_sensitivity, lookAheadAudit=look_ahead,
        complexity=complexity, overfittingDiagnosis=overfitting, conclusion="x",
        buyAndHoldBaseline=[BuyAndHoldBaseline(symbol="AAPL", startPrice=100.0, endPrice=110.0, returnPct=10.0, candleCount=6000)],
        dataHonestyNote="x", generatedAt=_CREATED_AT,
    )


def _beats_benchmark() -> list[BenchmarkComparison]:
    return [
        BenchmarkComparison(
            symbol="AAPL", benchmarkReturnPct=5.0, strategyTotalReturnR=10.0, strategyEquityReturnApproxPct=20.0,
            excessReturnApproxPct=15.0, riskPerTradePctUsed=2.0, beatsBenchmark=True, approximationNote="x",
        )
    ]


def _evidence(*, state_inputs: dict[str, object] | None = None) -> EvidenceQualityReport:
    defaults: dict[str, object] = dict(
        definition_id="def-1", definition_version=1, data_provenance="simulated", data_quality_valid=True,
        point_in_time_verified=True, holdout_status=None, sample_size=120, external_provider_available=False,
        benchmark_available=True, adversarial_coverage=False, report_id="ev-1",
    )
    if state_inputs:
        defaults.update(state_inputs)
    return build_evidence_quality_report(**defaults)  # type: ignore[arg-type]


def _holdout(*, status: str = "valid") -> HoldoutValidationReport:
    partition = DataPartitionSummary(label="train", candleCount=100, startTimestamp=None, endTimestamp=None, contentHash="h")
    return HoldoutValidationReport(
        id="ho-1", definitionId="def-1", definitionVersion=1, datasetId="ds-1", datasetVersion="v1",
        train=partition, validation=partition.model_copy(update={"label": "validation"}), holdout=partition.model_copy(update={"label": "holdout"}),
        overlapDetected=False, leakageDetected=False, chronologicalOrderValid=True, freeze=None,
        status=status, detail="x", generatedAt=_CREATED_AT,  # type: ignore[arg-type]
    )


class TestEvaluatePaperReadiness:
    def test_clean_evidence_and_accepted_candidacy_is_paper_ready(self) -> None:
        report = evaluate_paper_readiness(
            _record(), evidence_quality=_evidence(), outlier_dependent=False, benchmark_comparisons=_beats_benchmark(),
            research_relationship="novel", research_family_experiment_count=1, tuning_version=1, holdout=None,
            report_id="pr-1", generated_at=_CREATED_AT,
        )
        assert report.status == "paper_ready"
        assert report.candidacy == "accepted"

    def test_rejected_candidacy_blocks_readiness(self) -> None:
        report = evaluate_paper_readiness(
            _record(overall=_bucket(expectancyR=-0.2)), evidence_quality=_evidence(), outlier_dependent=False,
            benchmark_comparisons=_beats_benchmark(), research_relationship="novel", research_family_experiment_count=1,
            tuning_version=1, holdout=None, report_id="pr-2", generated_at=_CREATED_AT,
        )
        assert report.status == "not_ready"
        assert report.candidacy != "accepted"

    def test_insufficient_trades_blocks_readiness(self) -> None:
        report = evaluate_paper_readiness(
            _record(overall=_bucket(tradeCount=5)), evidence_quality=_evidence(state_inputs={"sample_size": 5}),
            outlier_dependent=False, benchmark_comparisons=_beats_benchmark(), research_relationship="novel",
            research_family_experiment_count=1, tuning_version=1, holdout=None, report_id="pr-3", generated_at=_CREATED_AT,
        )
        assert report.status == "not_ready"

    def test_rng_only_simulated_only_evidence_can_never_be_paper_ready(self) -> None:
        """Acceptance Criterion A — a strategy with strong RNG-only evidence CANNOT become PAPER_READY."""
        weak_evidence = _evidence(state_inputs={"point_in_time_verified": False})
        assert weak_evidence.state == "simulated_only"
        report = evaluate_paper_readiness(
            _record(), evidence_quality=weak_evidence, outlier_dependent=False, benchmark_comparisons=_beats_benchmark(),
            research_relationship="novel", research_family_experiment_count=1, tuning_version=1, holdout=None,
            report_id="pr-4", generated_at=_CREATED_AT,
        )
        assert report.status == "not_ready"
        assert any(c.name == "evidence_quality_state" and c.status == "fail" for c in report.checks)

    def test_insufficient_data_evidence_state_blocks_readiness(self) -> None:
        weak_evidence = _evidence(state_inputs={"sample_size": 1})
        assert weak_evidence.state == "insufficient_data"
        report = evaluate_paper_readiness(
            _record(), evidence_quality=weak_evidence, outlier_dependent=False, benchmark_comparisons=_beats_benchmark(),
            research_relationship="novel", research_family_experiment_count=1, tuning_version=1, holdout=None,
            report_id="pr-5", generated_at=_CREATED_AT,
        )
        assert report.status == "not_ready"

    def test_failed_walk_forward_blocks_readiness(self) -> None:
        report = evaluate_paper_readiness(
            _record(walk_forward_verdict="unstable"), evidence_quality=_evidence(), outlier_dependent=False,
            benchmark_comparisons=_beats_benchmark(), research_relationship="novel", research_family_experiment_count=1,
            tuning_version=1, holdout=None, report_id="pr-6", generated_at=_CREATED_AT,
        )
        assert report.status == "not_ready"

    def test_cost_sensitive_blocks_readiness(self) -> None:
        report = evaluate_paper_readiness(
            _record(cost_verdict="cost_sensitive"), evidence_quality=_evidence(), outlier_dependent=False,
            benchmark_comparisons=_beats_benchmark(), research_relationship="novel", research_family_experiment_count=1,
            tuning_version=1, holdout=None, report_id="pr-7", generated_at=_CREATED_AT,
        )
        assert report.status == "not_ready"

    def test_no_holdout_supplied_is_not_available_and_never_blocks_by_itself(self) -> None:
        report = evaluate_paper_readiness(
            _record(), evidence_quality=_evidence(), outlier_dependent=False, benchmark_comparisons=_beats_benchmark(),
            research_relationship="novel", research_family_experiment_count=1, tuning_version=1, holdout=None,
            report_id="pr-8", generated_at=_CREATED_AT,
        )
        holdout_check = next(c for c in report.checks if c.name == "holdout_validation")
        assert holdout_check.status == "not_available"
        assert report.status == "paper_ready"

    def test_valid_holdout_is_a_pass_and_still_allows_readiness(self) -> None:
        report = evaluate_paper_readiness(
            _record(), evidence_quality=_evidence(), outlier_dependent=False, benchmark_comparisons=_beats_benchmark(),
            research_relationship="novel", research_family_experiment_count=1, tuning_version=1, holdout=_holdout(status="valid"),
            report_id="pr-9", generated_at=_CREATED_AT,
        )
        holdout_check = next(c for c in report.checks if c.name == "holdout_validation")
        assert holdout_check.status == "pass"
        assert report.status == "paper_ready"
        assert report.holdout_status == "valid"

    def test_invalid_holdout_blocks_readiness_even_with_clean_candidacy(self) -> None:
        report = evaluate_paper_readiness(
            _record(), evidence_quality=_evidence(), outlier_dependent=False, benchmark_comparisons=_beats_benchmark(),
            research_relationship="novel", research_family_experiment_count=1, tuning_version=1, holdout=_holdout(status="invalid"),
            report_id="pr-10", generated_at=_CREATED_AT,
        )
        assert report.status == "not_ready"

    def test_never_silently_upgrades_a_blocking_check_to_pass(self) -> None:
        report = evaluate_paper_readiness(
            _record(overall=_bucket(expectancyR=-0.2)), evidence_quality=_evidence(state_inputs={"sample_size": 1}),
            outlier_dependent=False, benchmark_comparisons=_beats_benchmark(), research_relationship="novel",
            research_family_experiment_count=1, tuning_version=1, holdout=_holdout(status="invalid"),
            report_id="pr-11", generated_at=_CREATED_AT,
        )
        assert report.status == "not_ready"
        blocking_names = {c.name for c in report.checks if c.status in ("fail", "insufficient_evidence")}
        assert "research_candidacy" in blocking_names
        assert "holdout_validation" in blocking_names


class TestNeverAPromotionAuthority:
    """Proven by real module-source inspection, matching this codebase's
    own established Champion/Challenger-boundary discipline."""

    def test_champion_challenger_never_imports_paper_readiness(self) -> None:
        import app.champion_challenger as champion_challenger_module

        source = inspect.getsource(champion_challenger_module)
        assert "paper_readiness" not in source

    def test_strategy_lab_never_imports_paper_readiness(self) -> None:
        import app.strategy_lab as strategy_lab_module

        source = inspect.getsource(strategy_lab_module)
        assert "paper_readiness" not in source

    def test_paper_readiness_never_imports_champion_challenger_or_order_execution(self) -> None:
        import app.paper_readiness as paper_readiness_module

        source = inspect.getsource(paper_readiness_module)
        assert "import app.champion_challenger" not in source
        assert "from app.champion_challenger" not in source
        assert "import app.broker" not in source
        assert "place_order" not in source
