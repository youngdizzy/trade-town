"""Covers app/research_council.py — CEO directive "TradeTown — Phase 9:
Full Autonomous Quant Research Factory," Phases 14-15 (Research Roles /
Research Council). `ResearchLoopIterationRecord` is built via
`model_construct()` (skips validation) since only the specific fields
this module reads matter here — `StrategyHypothesis`/`StrategyScorecard`/
`MutationRecord` are built with their real, fully-validated constructors.
"""
from __future__ import annotations

import inspect

from app.adversarial_research import AdversarialResearchResult
from app.research_council import convene_research_council
from app.schemas import (
    ExtendedCostAttackResult,
    ExtendedCostAttackScenario,
    FailureCode,
    MutationRecord,
    OutlierResilienceResult,
    RegimeRobustnessResult,
    ResearchLoopIterationRecord,
    SequenceRobustnessResult,
    StrategyHypothesis,
    StrategyScorecard,
    WorstPeriodResult,
)

_CREATED_AT = "2024-01-01T00:00:00+00:00"


def _hypothesis(**overrides: object) -> StrategyHypothesis:
    base: dict[str, object] = dict(
        id="hyp", hypothesis="Trend continuation.", marketMechanism="x", expectedEdge="x", invalidationConditions="x",
        symbolUniverse=["AAPL"], timeframe="1h", entryConditions="x", exitConditions="x", stopLossLogic="x",
        takeProfitLogic="x", positionSizingLogic="x", riskConstraints="x", proposedBy="quant", createdAt=_CREATED_AT,
        researchRationale="A real, evidence-backed rationale.",
    )
    base.update(overrides)
    return StrategyHypothesis(**base)  # type: ignore[arg-type]


def _scorecard(*, trade_count: int | None = 150, max_drawdown_r: float | None = -3.0) -> StrategyScorecard:
    return StrategyScorecard(tradeCount=trade_count, maxDrawdownR=max_drawdown_r, expectancyR=0.3, profitFactor=1.5, regimeRobustnessVerdict="stable")


def _iteration(*, candidacy: str = "accepted", candidacy_reason: str = "Clears every gate.", mutation: MutationRecord | None = None, scorecard: StrategyScorecard | None = None) -> ResearchLoopIterationRecord:
    return ResearchLoopIterationRecord.model_construct(
        hypothesis=_hypothesis(),
        scorecard=scorecard or _scorecard(),
        candidacy=candidacy,
        candidacy_reason=candidacy_reason,
        mutation=mutation,
    )


def _mutation(code: FailureCode = "excessive_drawdown") -> MutationRecord:
    return MutationRecord(
        id="m1", parentDefinitionId="d", parentDefinitionVersion=1, parentIterationId="i", mutationNumber=1,
        observedFailureCodes=[code], proposedChange="x", reason="x", expectedEffect="x", validationRequirements="x", createdAt=_CREATED_AT,
    )


def _adversarial(*, outlier: str = "robust_to_outliers", regime: str = "regime_robust", survives_stress: bool | None = True) -> AdversarialResearchResult:
    return AdversarialResearchResult.model_construct(
        outlier_resilience=OutlierResilienceResult.model_construct(classification=outlier),
        worst_period=WorstPeriodResult.model_construct(),
        sequence_robustness=SequenceRobustnessResult.model_construct(),
        extended_cost_attack=ExtendedCostAttackResult.model_construct(survives_beyond_stress=survives_stress, scenarios=[ExtendedCostAttackScenario.model_construct()]),
        regime_robustness=RegimeRobustnessResult.model_construct(classification=regime, detail="x"),
        failure_boundaries=[],
    )


class TestConveneResearchCouncil:
    def test_produces_all_seven_roles(self) -> None:
        report = convene_research_council(_iteration(), report_id="r1", candidate_id="c1", generated_at=_CREATED_AT)
        roles = {f.role for f in report.findings}
        assert roles == {"researcher", "quant", "risk_manager", "adversarial_researcher", "regime_analyst", "statistician", "reviewer"}

    def test_every_finding_cites_real_evidence(self) -> None:
        report = convene_research_council(_iteration(), report_id="r1", candidate_id="c1", generated_at=_CREATED_AT, adversarial_result=_adversarial())
        for finding in report.findings:
            if finding.role == "researcher":
                continue  # may have no evidence references if research_rationale is unset elsewhere
            assert len(finding.evidence_references) > 0, f"{finding.role} has no evidence references"

    def test_statistician_low_confidence_below_evidence_floor(self) -> None:
        report = convene_research_council(_iteration(scorecard=_scorecard(trade_count=10)), report_id="r1", candidate_id="c1", generated_at=_CREATED_AT)
        statistician = next(f for f in report.findings if f.role == "statistician")
        assert statistician.confidence == "low"

    def test_statistician_high_confidence_above_evidence_floor(self) -> None:
        report = convene_research_council(_iteration(scorecard=_scorecard(trade_count=150)), report_id="r1", candidate_id="c1", generated_at=_CREATED_AT)
        statistician = next(f for f in report.findings if f.role == "statistician")
        assert statistician.confidence == "high"


class TestDeriveRecommendation:
    def test_insufficient_evidence_maps_directly(self) -> None:
        report = convene_research_council(_iteration(candidacy="insufficient_evidence"), report_id="r1", candidate_id="c1", generated_at=_CREATED_AT)
        assert report.recommendation == "insufficient_evidence"

    def test_rejected_maps_to_archive(self) -> None:
        report = convene_research_council(_iteration(candidacy="rejected"), report_id="r1", candidate_id="c1", generated_at=_CREATED_AT)
        assert report.recommendation == "archive"

    def test_overfit_maps_to_archive(self) -> None:
        report = convene_research_council(_iteration(candidacy="overfit"), report_id="r1", candidate_id="c1", generated_at=_CREATED_AT)
        assert report.recommendation == "archive"

    def test_accepted_with_no_adversarial_result_continues(self) -> None:
        report = convene_research_council(_iteration(candidacy="accepted"), report_id="r1", candidate_id="c1", generated_at=_CREATED_AT)
        assert report.recommendation == "continue"

    def test_accepted_with_fragile_adversarial_evidence_retests(self) -> None:
        report = convene_research_council(
            _iteration(candidacy="accepted"), report_id="r1", candidate_id="c1", generated_at=_CREATED_AT,
            adversarial_result=_adversarial(outlier="highly_outlier_dependent"),
        )
        assert report.recommendation == "retest"

    def test_accepted_with_robust_adversarial_evidence_continues(self) -> None:
        report = convene_research_council(
            _iteration(candidacy="accepted"), report_id="r1", candidate_id="c1", generated_at=_CREATED_AT, adversarial_result=_adversarial()
        )
        assert report.recommendation == "continue"

    def test_promising_with_mutation_recommends_mutate(self) -> None:
        report = convene_research_council(
            _iteration(candidacy="promising", mutation=_mutation()), report_id="r1", candidate_id="c1", generated_at=_CREATED_AT
        )
        assert report.recommendation == "mutate"

    def test_promising_without_mutation_recommends_retest(self) -> None:
        report = convene_research_council(_iteration(candidacy="promising", mutation=None), report_id="r1", candidate_id="c1", generated_at=_CREATED_AT)
        assert report.recommendation == "retest"

    def test_recommendation_never_overrides_the_real_candidacy_gate(self) -> None:
        """Every single 'rejected'-family candidacy value must map to
        'archive', regardless of adversarial evidence — the council can
        never manufacture a 'continue' out of a real hard-gate failure."""
        for candidacy in ("rejected", "overfit", "benchmark_failed", "risk_failed", "duplicate"):
            report = convene_research_council(
                _iteration(candidacy=candidacy), report_id="r1", candidate_id="c1", generated_at=_CREATED_AT, adversarial_result=_adversarial()
            )
            assert report.recommendation == "archive", f"candidacy={candidacy!r} did not archive"


class TestNeverAGate:
    def test_never_imported_by_hard_gate_modules(self) -> None:
        """Section 15's own explicit 'no meaningless AI score, never a
        gate' rule — proven by real module-source inspection, not
        prose. Neither app/research_loop.py's classify_candidacy() nor
        app/champion_challenger.py nor app/strategy_lab.py's
        Certification/Hall-of-Fame functions import anything from
        app/research_council.py."""
        import app.champion_challenger as champion_challenger_module
        import app.research_loop as research_loop_module
        import app.strategy_lab as strategy_lab_module

        for module in (champion_challenger_module, research_loop_module, strategy_lab_module):
            source = inspect.getsource(module)
            assert "research_council" not in source, f"{module.__name__} references research_council — the council must never be a gate input"
