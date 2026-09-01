"""Covers app/risk_survival.py — CEO directive "TradeTown — Phase 11:
Strategy Intelligence + Hard-Risk Refinement," Sections 2 and 7."""
from __future__ import annotations

import inspect

from app.evidence_quality import build_evidence_quality_report
from app.risk_survival import RISK_PROFILE_TEMPLATES, build_risk_survival_scorecard
from app.schemas import (
    AdversarialResearchResult,
    BenchmarkComparison,
    BuyAndHoldBaseline,
    CompiledStrategyBacktestResult,
    CostSensitivityResult,
    DataPartitionSummary,
    EmaPullbackStatsBucket,
    EvidenceQualityReport,
    ExtendedCostAttackResult,
    FailureCodeEntry,
    HoldoutValidationReport,
    LookAheadAuditResult,
    OutlierResilienceResult,
    OverfittingDiagnosis,
    ParameterSensitivityAxisResult,
    ParameterSensitivityResult,
    PortfolioResearchReport,
    RegimeRobustnessResult,
    ResearchExperimentRecord,
    SequenceRobustnessResult,
    StrategyComplexityScore,
    WalkForwardSymbolResult,
    WalkForwardValidationResult,
    WorstPeriodResult,
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


def _record(*, overall: EmaPullbackStatsBucket | None = None, walk_forward_verdict: str = "stable", cost_verdict: str = "cost_resilient") -> ResearchExperimentRecord:
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
        id="ps-1", definitionId="def-1", definitionVersion=1, stopAxis=empty_axis, targetAxis=empty_axis, verdict="robust", detail="x", multipleTestingNote="x", dataHonestyNote="x", generatedAt=_CREATED_AT,  # type: ignore[arg-type]
    )
    look_ahead = LookAheadAuditResult(id="la-1", definitionId="def-1", definitionVersion=1, setupsChecked=10, violations=[], verdict="clean", detail="x", generatedAt=_CREATED_AT)  # type: ignore[arg-type]
    complexity = StrategyComplexityScore(definitionId="def-1", definitionVersion=1, stepCount=3, conditionCount=1, distinctIndicatorCount=2, parameterCount=5, complexityScore=11, band="moderate", detail="x", generatedAt=_CREATED_AT)  # type: ignore[arg-type]
    overfitting = OverfittingDiagnosis(verdict="pending_validation", detail="x", walkForwardVerdict=walk_forward_verdict, parameterSensitivityVerdict="robust", costSensitivityVerdict=cost_verdict)  # type: ignore[arg-type]
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


def _adversarial(
    *,
    outlier_classification: str = "robust_to_outliers",
    regime_classification: str = "regime_robust",
    survives_beyond_stress: bool | None = True,
    baseline_dd: float | None = -2.0,
    worst_reshuffled_dd: float | None = -2.5,
) -> AdversarialResearchResult:
    return AdversarialResearchResult(
        id="adv-1", definitionId="def-1", definitionVersion=1,
        outlierResilience=OutlierResilienceResult(scenarios=[], classification=outlier_classification, detail="x"),  # type: ignore[arg-type]
        worstPeriod=WorstPeriodResult(windowTradeCount=5, windowStartTimestamp=None, windowEndTimestamp=None, windowCumulativeR=-1.0, detail="x"),
        sequenceRobustness=SequenceRobustnessResult(reshuffleCount=100, seed="s", baselineMaxDrawdownR=baseline_dd, worstReshuffledMaxDrawdownR=worst_reshuffled_dd, detail="x"),
        extendedCostAttack=ExtendedCostAttackResult(scenarios=[], survivesBeyondStress=survives_beyond_stress, detail="x"),
        regimeRobustness=RegimeRobustnessResult(classification=regime_classification, provenRegimes=[], fragileRegimes=[], detail="x"),  # type: ignore[arg-type]
        failureBoundaries=[], dataProvenance="simulated", generatedAt=_CREATED_AT,
    )


def _portfolio(recommendation: str = "portfolio_robust") -> PortfolioResearchReport:
    bucket = _bucket()
    return PortfolioResearchReport(
        id="pf-1", candidateIds=["def-1-v1", "def-2-v1"], pairCorrelations=[], combinedBucket=bucket,
        worstCombinedPeriod=WorstPeriodResult(windowTradeCount=5, windowStartTimestamp=None, windowEndTimestamp=None, windowCumulativeR=-1.0, detail="x"),
        marginalContributions=[], simultaneousDrawdownDetected=False, sharedFailureModes=[], concentrationPct=50.0,
        evidenceConfidence="high", recommendation=recommendation, recommendationReason="x", generatedAt=_CREATED_AT,  # type: ignore[arg-type]
    )


class TestRiskProfileTemplates:
    def test_all_three_templates_exist_with_the_directives_own_numbers(self) -> None:
        assert set(RISK_PROFILE_TEMPLATES.keys()) == {"conservative", "professional", "aggressive"}
        conservative = RISK_PROFILE_TEMPLATES["conservative"]
        assert conservative.risk_per_trade_pct_min == 0.50
        assert conservative.risk_per_trade_pct_max == 0.75
        assert conservative.max_daily_loss_pct == 2.0
        assert conservative.kill_switch_drawdown_pct == 6.0
        aggressive = RISK_PROFILE_TEMPLATES["aggressive"]
        assert aggressive.risk_per_trade_pct_max == 1.0
        assert aggressive.kill_switch_drawdown_pct == 8.0


class TestBuildRiskSurvivalScorecard:
    def _names(self, checks: list[object]) -> dict[str, str]:
        return {c.name: c.status for c in checks}  # type: ignore[attr-defined]

    def test_clean_evidence_produces_all_pass_checks_where_data_exists(self) -> None:
        scorecard = build_risk_survival_scorecard(
            _record(), evidence_quality=_evidence(), benchmark_comparisons=_beats_benchmark(), failure_codes=[],
            risk_per_trade_pct=2.0, holdout=_holdout(status="valid"), adversarial=_adversarial(), portfolio=_portfolio(),
            report_id="rs-1", generated_at=_CREATED_AT,
        )
        statuses = self._names(scorecard.checks)  # type: ignore[arg-type]
        assert statuses["historical_robustness"] == "pass"
        assert statuses["walk_forward_robustness"] == "pass"
        assert statuses["cost_resilience"] == "pass"
        assert statuses["outlier_resilience"] == "pass"
        assert statuses["regime_resilience"] == "pass"
        assert statuses["benchmark_performance"] == "pass"
        assert statuses["holdout_evidence"] == "pass"
        assert statuses["statistical_evidence"] == "pass"
        assert statuses["portfolio_interaction"] == "pass"
        assert statuses["drawdown_behavior"] == "pass"
        assert statuses["failure_concentration"] == "pass"

    def test_missing_optional_inputs_are_honestly_not_available_never_a_pass(self) -> None:
        scorecard = build_risk_survival_scorecard(
            _record(), evidence_quality=_evidence(), benchmark_comparisons=_beats_benchmark(), failure_codes=[],
            risk_per_trade_pct=2.0, holdout=None, adversarial=None, portfolio=None,
            report_id="rs-2", generated_at=_CREATED_AT,
        )
        statuses = self._names(scorecard.checks)  # type: ignore[arg-type]
        assert statuses["holdout_evidence"] == "not_available"
        assert statuses["outlier_resilience"] == "not_available"
        assert statuses["sequence_resilience"] == "not_available"
        assert statuses["regime_resilience"] == "not_available"
        assert statuses["portfolio_interaction"] == "not_available"

    def test_negative_expectancy_fails_historical_robustness(self) -> None:
        scorecard = build_risk_survival_scorecard(
            _record(overall=_bucket(expectancyR=-0.2)), evidence_quality=_evidence(), benchmark_comparisons=_beats_benchmark(),
            failure_codes=[], risk_per_trade_pct=2.0, holdout=None, adversarial=None, portfolio=None,
            report_id="rs-3", generated_at=_CREATED_AT,
        )
        statuses = self._names(scorecard.checks)  # type: ignore[arg-type]
        assert statuses["historical_robustness"] == "fail"

    def test_below_trade_floor_is_insufficient_evidence_not_fail(self) -> None:
        scorecard = build_risk_survival_scorecard(
            _record(overall=_bucket(tradeCount=5)), evidence_quality=_evidence(), benchmark_comparisons=_beats_benchmark(),
            failure_codes=[], risk_per_trade_pct=2.0, holdout=None, adversarial=None, portfolio=None,
            report_id="rs-4", generated_at=_CREATED_AT,
        )
        statuses = self._names(scorecard.checks)  # type: ignore[arg-type]
        assert statuses["historical_robustness"] == "insufficient_evidence"

    def test_highly_outlier_dependent_adversarial_result_fails_that_check(self) -> None:
        scorecard = build_risk_survival_scorecard(
            _record(), evidence_quality=_evidence(), benchmark_comparisons=_beats_benchmark(), failure_codes=[],
            risk_per_trade_pct=2.0, holdout=None, adversarial=_adversarial(outlier_classification="highly_outlier_dependent"), portfolio=None,
            report_id="rs-5", generated_at=_CREATED_AT,
        )
        statuses = self._names(scorecard.checks)  # type: ignore[arg-type]
        assert statuses["outlier_resilience"] == "fail"

    def test_regime_fragile_adversarial_result_fails_that_check(self) -> None:
        scorecard = build_risk_survival_scorecard(
            _record(), evidence_quality=_evidence(), benchmark_comparisons=_beats_benchmark(), failure_codes=[],
            risk_per_trade_pct=2.0, holdout=None, adversarial=_adversarial(regime_classification="regime_fragile"), portfolio=None,
            report_id="rs-6", generated_at=_CREATED_AT,
        )
        statuses = self._names(scorecard.checks)  # type: ignore[arg-type]
        assert statuses["regime_resilience"] == "fail"

    def test_degraded_sequence_reshuffle_warns(self) -> None:
        scorecard = build_risk_survival_scorecard(
            _record(), evidence_quality=_evidence(), benchmark_comparisons=_beats_benchmark(), failure_codes=[],
            risk_per_trade_pct=2.0, holdout=None, adversarial=_adversarial(baseline_dd=-1.0, worst_reshuffled_dd=-5.0), portfolio=None,
            report_id="rs-7", generated_at=_CREATED_AT,
        )
        statuses = self._names(scorecard.checks)  # type: ignore[arg-type]
        assert statuses["sequence_resilience"] == "warn"

    def test_invalid_holdout_fails_that_check(self) -> None:
        scorecard = build_risk_survival_scorecard(
            _record(), evidence_quality=_evidence(), benchmark_comparisons=_beats_benchmark(), failure_codes=[],
            risk_per_trade_pct=2.0, holdout=_holdout(status="invalid"), adversarial=None, portfolio=None,
            report_id="rs-8", generated_at=_CREATED_AT,
        )
        statuses = self._names(scorecard.checks)  # type: ignore[arg-type]
        assert statuses["holdout_evidence"] == "fail"

    def test_high_redundancy_portfolio_fails_portfolio_interaction(self) -> None:
        scorecard = build_risk_survival_scorecard(
            _record(), evidence_quality=_evidence(), benchmark_comparisons=_beats_benchmark(), failure_codes=[],
            risk_per_trade_pct=2.0, holdout=None, adversarial=None, portfolio=_portfolio(recommendation="high_redundancy"),
            report_id="rs-9", generated_at=_CREATED_AT,
        )
        statuses = self._names(scorecard.checks)  # type: ignore[arg-type]
        assert statuses["portfolio_interaction"] == "fail"

    def test_critical_failure_code_fails_failure_concentration(self) -> None:
        critical = FailureCodeEntry(code="lookahead_detected", category="data_failure", severity="critical", evidence="x")  # type: ignore[arg-type]
        scorecard = build_risk_survival_scorecard(
            _record(), evidence_quality=_evidence(), benchmark_comparisons=_beats_benchmark(), failure_codes=[critical],
            risk_per_trade_pct=2.0, holdout=None, adversarial=None, portfolio=None,
            report_id="rs-10", generated_at=_CREATED_AT,
        )
        statuses = self._names(scorecard.checks)  # type: ignore[arg-type]
        assert statuses["failure_concentration"] == "fail"

    def test_excessive_drawdown_fails_drawdown_behavior(self) -> None:
        scorecard = build_risk_survival_scorecard(
            _record(overall=_bucket(maxDrawdownR=-20.0)), evidence_quality=_evidence(), benchmark_comparisons=_beats_benchmark(),
            failure_codes=[], risk_per_trade_pct=2.0, holdout=None, adversarial=None, portfolio=None,
            report_id="rs-11", generated_at=_CREATED_AT,
        )
        statuses = self._names(scorecard.checks)  # type: ignore[arg-type]
        assert statuses["drawdown_behavior"] == "fail"

    def test_simulated_only_evidence_state_warns_not_fails(self) -> None:
        scorecard = build_risk_survival_scorecard(
            _record(), evidence_quality=_evidence(state_inputs={"point_in_time_verified": False}), benchmark_comparisons=_beats_benchmark(),
            failure_codes=[], risk_per_trade_pct=2.0, holdout=None, adversarial=None, portfolio=None,
            report_id="rs-12", generated_at=_CREATED_AT,
        )
        statuses = self._names(scorecard.checks)  # type: ignore[arg-type]
        assert statuses["evidence_quality"] == "warn"

    def test_insufficient_data_evidence_state_fails(self) -> None:
        scorecard = build_risk_survival_scorecard(
            _record(), evidence_quality=_evidence(state_inputs={"sample_size": 1}), benchmark_comparisons=_beats_benchmark(),
            failure_codes=[], risk_per_trade_pct=2.0, holdout=None, adversarial=None, portfolio=None,
            report_id="rs-13", generated_at=_CREATED_AT,
        )
        statuses = self._names(scorecard.checks)  # type: ignore[arg-type]
        assert statuses["evidence_quality"] == "fail"

    def test_never_fabricates_a_single_collapsed_score(self) -> None:
        scorecard = build_risk_survival_scorecard(
            _record(), evidence_quality=_evidence(), benchmark_comparisons=_beats_benchmark(), failure_codes=[],
            risk_per_trade_pct=2.0, holdout=None, adversarial=None, portfolio=None,
            report_id="rs-14", generated_at=_CREATED_AT,
        )
        assert not hasattr(scorecard, "score")
        assert not hasattr(scorecard, "confidence")
        assert len(scorecard.checks) == 13


class TestNeverAPromotionAuthority:
    def test_champion_challenger_never_imports_risk_survival(self) -> None:
        import app.champion_challenger as champion_challenger_module

        source = inspect.getsource(champion_challenger_module)
        assert "risk_survival" not in source

    def test_strategy_lab_never_imports_risk_survival(self) -> None:
        import app.strategy_lab as strategy_lab_module

        source = inspect.getsource(strategy_lab_module)
        assert "risk_survival" not in source

    def test_risk_survival_never_imports_champion_challenger_or_order_execution(self) -> None:
        import app.risk_survival as risk_survival_module

        source = inspect.getsource(risk_survival_module)
        assert "import app.champion_challenger" not in source
        assert "from app.champion_challenger" not in source
        assert "import app.broker" not in source
        assert "place_order" not in source
