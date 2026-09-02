"""Covers app/research_pareto.py — CEO directive "TradeTown — Autonomous
Mutation Application + Pareto Survivor Engine." `_BASE_EXPERIMENT` is one
real `ResearchExperimentRecord` (real compiler, real backtest against
mock candle data) reused as a schema-valid filler across every test
candidate — `app/research_pareto.py`'s own dominance rule reads
exclusively from `iteration.scorecard`/`adversarial_result` (never
`iteration.experiment` directly, see that module's own docstring), so
only `scorecard`/`adversarial_result` are varied per test to build
unambiguous, hand-controlled dominance scenarios.
"""
from __future__ import annotations

import inspect

from app.research_experiment import run_research_experiment
from app.research_pareto import compute_pareto_frontier
from app.schemas import (
    AdversarialResearchResult,
    ExtendedCostAttackResult,
    FactoryCandidateRecord,
    OutlierResilienceResult,
    RegimeRobustnessResult,
    ResearchBudgetStatus,
    ResearchLoopIterationRecord,
    SequenceRobustnessResult,
    StrategyHypothesis,
    StrategyScorecard,
    WorstPeriodResult,
)
from app.strategy_compiler import compile_strategy_text

_CREATED_AT = "2024-01-01T00:00:00+00:00"
_TEXT = "Buy when price closes above the 50 EMA. Enter when price closes above the previous swing high. Place the stop at the Chandelier Stop and target 2R."
_DEFINITION = compile_strategy_text(name="Pareto Test Strategy", source_text=_TEXT)
_BASE_EXPERIMENT = run_research_experiment(_DEFINITION, symbols=["AAPL"])


def _hypothesis() -> StrategyHypothesis:
    return StrategyHypothesis(
        id="hyp", hypothesis="x", marketMechanism="x", expectedEdge="x", invalidationConditions="x",
        symbolUniverse=["AAPL"], timeframe="1h", entryConditions="x", exitConditions="x", stopLossLogic="x",
        takeProfitLogic="x", positionSizingLogic="x", riskConstraints="x", proposedBy="quant", createdAt=_CREATED_AT,
    )


def _candidate(
    candidate_id: str,
    *,
    expectancy_r: float | None,
    max_drawdown_r: float | None,
    profit_factor: float | None,
    trade_count: int = 50,
    walk_forward_verdict: str | None = None,
    cost_sensitivity_verdict: str | None = None,
    regime_robustness_verdict: str | None = None,
    outlier_dependent: bool | None = None,
    survives_beyond_stress: bool | None = None,
    data_provenance: str = "simulated",
) -> FactoryCandidateRecord:
    scorecard = StrategyScorecard(
        tradeCount=trade_count, expectancyR=expectancy_r, maxDrawdownR=max_drawdown_r, profitFactor=profit_factor,
        walkForwardVerdict=walk_forward_verdict, costSensitivityVerdict=cost_sensitivity_verdict,
        regimeRobustnessVerdict=regime_robustness_verdict, outlierDependent=outlier_dependent,
    )
    iteration = ResearchLoopIterationRecord(
        id=f"{candidate_id}-iteration", strategyFamily="Pareto Test Strategy", hypothesis=_hypothesis(),
        experiment=_BASE_EXPERIMENT, scorecard=scorecard, candidacy="promising", candidacyReason="x",
        researchRelationship="novel",
        budget=ResearchBudgetStatus(strategyFamily="Pareto Test Strategy", experimentsAttempted=1, mutationsForThisParent=0, maxIterationsPerFamily=20, maxMutationsPerParent=5, stopped=False),
        createdAt=_CREATED_AT,
    )
    adversarial = AdversarialResearchResult(
        id=f"{candidate_id}-adversarial", definitionId=_DEFINITION.id, definitionVersion=_DEFINITION.version,
        outlierResilience=OutlierResilienceResult(scenarios=[], classification="insufficient_evidence", detail="x"),
        worstPeriod=WorstPeriodResult(windowTradeCount=0, detail="x"),
        sequenceRobustness=SequenceRobustnessResult(reshuffleCount=0, seed="x", detail="x"),
        extendedCostAttack=ExtendedCostAttackResult(scenarios=[], survivesBeyondStress=survives_beyond_stress, detail="x"),
        regimeRobustness=RegimeRobustnessResult(classification=regime_robustness_verdict or "regime_unknown", provenRegimes=[], fragileRegimes=[], detail="x"),  # type: ignore[arg-type]
        dataProvenance=data_provenance,  # type: ignore[arg-type]
        generatedAt=_CREATED_AT,
    )
    return FactoryCandidateRecord(
        id=candidate_id, runId="run-1", generation=1, parentCandidateId="parent", lineageId="run-1",
        strategyFamily="Pareto Test Strategy", definitionId=_DEFINITION.id, definitionVersion=_DEFINITION.version,
        hypothesis=_hypothesis(), lifecycleStage="candidate", compileStatus="compiled", compileDetail="x",
        iteration=iteration, survived=False, decisionReason="x", createdAt=_CREATED_AT, adversarialResult=adversarial,
    )


def _no_evidence_candidate(candidate_id: str) -> FactoryCandidateRecord:
    return FactoryCandidateRecord(
        id=candidate_id, runId="run-1", generation=1, parentCandidateId=None, lineageId="run-1",
        strategyFamily="Pareto Test Strategy", definitionId=_DEFINITION.id, definitionVersion=_DEFINITION.version,
        hypothesis=_hypothesis(), lifecycleStage="compile_rejected", compileStatus="invalid", compileDetail="x",
        iteration=None, survived=False, decisionReason="x", createdAt=_CREATED_AT,
    )


class TestComputeParetoFrontierDominance:
    def test_same_return_worse_drawdown_loses(self) -> None:
        """The directive's own headline principle, applied correctly
        under REAL multi-dimensional Pareto semantics: raw return alone
        never wins — a candidate with the SAME expectancy but a
        catastrophic drawdown and a worse profit factor is strictly
        worse and must lose. (A candidate with a genuinely HIGHER return
        purchased at a genuinely worse drawdown is instead a real
        trade-off — see `test_genuine_tradeoff_is_non_dominated_on_both_
        sides` below — dominance is never claimed across an actual
        trade-off, only when one candidate concedes nothing.)"""
        high_drawdown = _candidate("hot", expectancy_r=0.5, max_drawdown_r=-12.0, profit_factor=1.1)
        stable_same_return = _candidate("stable", expectancy_r=0.5, max_drawdown_r=-2.0, profit_factor=1.4)
        frontier = compute_pareto_frontier([high_drawdown, stable_same_return])
        assert frontier["hot"].pareto_status == "dominated"
        assert frontier["hot"].dominated_by == ["stable"]
        assert frontier["stable"].pareto_status == "non_dominated"

    def test_low_return_low_drawdown_survives(self) -> None:
        stable = _candidate("stable", expectancy_r=0.1, max_drawdown_r=-1.0, profit_factor=1.05, trade_count=100)
        aggressive = _candidate("aggressive", expectancy_r=0.5, max_drawdown_r=-8.0, profit_factor=1.3, trade_count=100)
        frontier = compute_pareto_frontier([stable, aggressive])
        assert frontier["stable"].pareto_status == "non_dominated"

    def test_genuine_tradeoff_is_non_dominated_on_both_sides(self) -> None:
        """A better on drawdown, B better on profit factor — neither
        dominates; both are real, disclosed frontier members."""
        a = _candidate("a", expectancy_r=0.3, max_drawdown_r=-2.0, profit_factor=1.1)
        b = _candidate("b", expectancy_r=0.3, max_drawdown_r=-4.0, profit_factor=1.8)
        frontier = compute_pareto_frontier([a, b])
        assert frontier["a"].pareto_status == "non_dominated"
        assert frontier["b"].pareto_status == "non_dominated"
        assert frontier["a"].dominated_by == []
        assert frontier["b"].dominated_by == []

    def test_strictly_worse_on_every_axis_is_dominated(self) -> None:
        worse = _candidate("worse", expectancy_r=0.1, max_drawdown_r=-5.0, profit_factor=1.0, trade_count=20)
        better = _candidate("better", expectancy_r=0.4, max_drawdown_r=-2.0, profit_factor=1.5, trade_count=80)
        frontier = compute_pareto_frontier([worse, better])
        assert frontier["worse"].pareto_status == "dominated"
        assert frontier["better"].pareto_status == "non_dominated"
        assert "better" in frontier["worse"].reason

    def test_identical_candidates_are_both_non_dominated(self) -> None:
        a = _candidate("a", expectancy_r=0.3, max_drawdown_r=-2.0, profit_factor=1.2)
        b = _candidate("b", expectancy_r=0.3, max_drawdown_r=-2.0, profit_factor=1.2)
        frontier = compute_pareto_frontier([a, b])
        assert frontier["a"].pareto_status == "non_dominated"
        assert frontier["b"].pareto_status == "non_dominated"

    def test_walk_forward_and_cost_resilience_axes_participate_in_dominance(self) -> None:
        unstable = _candidate("unstable", expectancy_r=0.3, max_drawdown_r=-2.0, profit_factor=1.2, walk_forward_verdict="unstable", cost_sensitivity_verdict="cost_sensitive")
        stable = _candidate("stable", expectancy_r=0.3, max_drawdown_r=-2.0, profit_factor=1.2, walk_forward_verdict="stable", cost_sensitivity_verdict="cost_resilient")
        frontier = compute_pareto_frontier([unstable, stable])
        assert frontier["unstable"].pareto_status == "dominated"
        assert frontier["stable"].pareto_status == "non_dominated"

    def test_insufficient_evidence_axis_never_causes_automatic_loss(self) -> None:
        """Section 19 — a candidate with no walk-forward verdict at all
        must not be penalized on that axis relative to one that has a
        real 'unstable' verdict; missing data is a tie, not a loss."""
        no_wf_data = _candidate("no_wf", expectancy_r=0.3, max_drawdown_r=-2.0, profit_factor=1.2, walk_forward_verdict=None)
        real_unstable = _candidate("real_unstable", expectancy_r=0.3, max_drawdown_r=-2.0, profit_factor=1.2, walk_forward_verdict="unstable")
        frontier = compute_pareto_frontier([no_wf_data, real_unstable])
        # no_wf_data ties real_unstable on every other axis and the
        # walk_forward axis is excluded (one side has no evidence) — so
        # neither strictly beats the other; both are non-dominated.
        assert frontier["no_wf"].pareto_status == "non_dominated"

    def test_candidates_with_no_real_backtest_get_no_frontier_entry(self) -> None:
        no_evidence = _no_evidence_candidate("rejected")
        real = _candidate("real", expectancy_r=0.3, max_drawdown_r=-2.0, profit_factor=1.2)
        frontier = compute_pareto_frontier([no_evidence, real])
        assert "rejected" not in frontier
        assert "real" in frontier
        assert frontier["real"].pareto_status == "non_dominated"

    def test_empty_input_returns_empty_frontier(self) -> None:
        assert compute_pareto_frontier([]) == {}

    def test_single_candidate_is_always_non_dominated(self) -> None:
        solo = _candidate("solo", expectancy_r=0.3, max_drawdown_r=-2.0, profit_factor=1.2)
        frontier = compute_pareto_frontier([solo])
        assert frontier["solo"].pareto_status == "non_dominated"
        assert frontier["solo"].dominated_by == []

    def test_dominated_by_multiple_real_candidates(self) -> None:
        worst = _candidate("worst", expectancy_r=0.05, max_drawdown_r=-9.0, profit_factor=0.9, trade_count=15)
        mid = _candidate("mid", expectancy_r=0.3, max_drawdown_r=-3.0, profit_factor=1.3, trade_count=50)
        best = _candidate("best", expectancy_r=0.5, max_drawdown_r=-1.0, profit_factor=1.8, trade_count=90)
        frontier = compute_pareto_frontier([worst, mid, best])
        assert frontier["worst"].pareto_status == "dominated"
        assert set(frontier["worst"].dominated_by) == {"mid", "best"}
        assert frontier["mid"].pareto_status == "dominated"
        assert frontier["mid"].dominated_by == ["best"]
        assert frontier["best"].pareto_status == "non_dominated"

    def test_dimensions_are_disclosed_never_a_single_score(self) -> None:
        a = _candidate("a", expectancy_r=0.3, max_drawdown_r=-2.0, profit_factor=1.2)
        b = _candidate("b", expectancy_r=0.1, max_drawdown_r=-5.0, profit_factor=0.9)
        frontier = compute_pareto_frontier([a, b])
        assert len(frontier["a"].dimensions) >= 8  # every real axis this module tracks, not a collapsed number
        labels = {d.dimension for d in frontier["a"].dimensions}
        assert "Expectancy" in labels
        assert "Max drawdown" in labels
        assert "Profit factor" in labels
        # No field named anything like a fabricated single score exists
        # on the schema at all — see app/schemas.py's own ParetoFrontierEntry.
        assert not hasattr(frontier["a"], "pareto_score")
        assert not hasattr(frontier["a"], "fitness_score")

    def test_different_provenance_never_compared(self) -> None:
        """Section 13 — evidence with different provenance is never
        silently blended into one ranking."""
        simulated = _candidate("sim", expectancy_r=0.5, max_drawdown_r=-1.0, profit_factor=1.8, data_provenance="simulated")
        real = _candidate("real_data", expectancy_r=0.1, max_drawdown_r=-5.0, profit_factor=0.9, data_provenance="real")
        frontier = compute_pareto_frontier([simulated, real])
        # `real_data` is strictly worse on every axis, but different
        # provenance means it is never actually compared against `sim`.
        assert frontier["real_data"].pareto_status == "non_dominated"
        assert frontier["sim"].pareto_status == "non_dominated"


class TestResearchParetoModuleBoundary:
    """Proven by real module-source inspection, matching this codebase's
    own established Champion/Challenger/holdout-boundary discipline —
    never a bare textual assertion, always import-shape. This module
    reads only `app.schemas` (comparison logic over already-computed
    fields) — it structurally cannot promote anything, place a trade, or
    touch any live/risk state."""

    def test_only_imports_schemas(self) -> None:
        import app.research_pareto as module

        source = inspect.getsource(module)
        import_lines = [line for line in source.splitlines() if line.startswith("from app.") or line.startswith("import app.")]
        assert import_lines == ["from app.schemas import FactoryCandidateRecord, ParetoDimensionValue, ParetoFrontierEntry, ParetoStatus"]

    def test_never_references_promotion_execution_or_risk_authorities(self) -> None:
        import app.research_pareto as module

        source = inspect.getsource(module)
        for forbidden in ("compare_champion_challenger", "promote_challenger", "qualifies_for_hall_of_fame", "evaluate_certification_readiness", "gatekeeper", "emergency_stop", "paper_broker", "place_order", "execute_trade"):
            assert forbidden not in source, f"app/research_pareto.py unexpectedly references {forbidden!r}"
