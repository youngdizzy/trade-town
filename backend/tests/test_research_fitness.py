"""Covers app/research_fitness.py — CEO directive "TradeTown — Phase 9:
Full Autonomous Quant Research Factory," Phase 6 (Robustness-First
Fitness). Hand-built fixtures give exact control over each real axis
(drawdown/profit factor/expectancy/complexity) so the directive's own
explicit rule ("a strategy with $100k profit + 35% drawdown must NOT
beat $30k profit + 10% drawdown") can be tested precisely.
`FactoryCandidateRecord`/`ResearchLoopIterationRecord`/
`ResearchExperimentRecord`/`CompiledStrategyBacktestResult` are built via
`model_construct()` (skips validation) since only the specific fields
`research_fitness.py` actually reads matter here — every OTHER real
integration test in this suite (test_research_factory_branching.py)
already exercises the real, fully-validated end-to-end shape.
"""
from __future__ import annotations

from app.research_fitness import describe_fitness_rank, rank_candidates
from app.schemas import (
    CompiledStrategyBacktestResult,
    EmaPullbackStatsBucket,
    FactoryCandidateRecord,
    ResearchExperimentRecord,
    ResearchLoopIterationRecord,
    StrategyComplexityScore,
    StrategyHypothesis,
)

_CREATED_AT = "2024-01-01T00:00:00+00:00"


def _hypothesis() -> StrategyHypothesis:
    return StrategyHypothesis(
        id="hyp", hypothesis="x", marketMechanism="x", expectedEdge="x", invalidationConditions="x", symbolUniverse=["AAPL"],
        timeframe="1h", entryConditions="x", exitConditions="x", stopLossLogic="x", takeProfitLogic="x",
        positionSizingLogic="x", riskConstraints="x", proposedBy="quant", createdAt=_CREATED_AT,
    )


def _bucket(*, trade_count: int, max_drawdown_r: float | None, profit_factor: float | None, expectancy_r: float | None) -> EmaPullbackStatsBucket:
    return EmaPullbackStatsBucket(
        label="overall", tradeCount=trade_count, winCount=0, lossCount=0, openCount=0,
        maxDrawdownR=max_drawdown_r, profitFactor=profit_factor, expectancyR=expectancy_r, detail="x",
    )


def _complexity(score: int) -> StrategyComplexityScore:
    return StrategyComplexityScore(
        definitionId="d", definitionVersion=1, stepCount=1, conditionCount=1, distinctIndicatorCount=1,
        parameterCount=score, complexityScore=score, band="simple", detail="x", generatedAt=_CREATED_AT,
    )


def _candidate(
    *,
    candidate_id: str,
    lifecycle_stage: str = "candidate",
    compile_status: str = "compiled",
    trade_count: int = 100,
    max_drawdown_r: float | None = -3.0,
    profit_factor: float | None = 1.5,
    expectancy_r: float | None = 0.3,
    complexity_score: int = 5,
) -> FactoryCandidateRecord:
    bucket = _bucket(trade_count=trade_count, max_drawdown_r=max_drawdown_r, profit_factor=profit_factor, expectancy_r=expectancy_r)
    backtest = CompiledStrategyBacktestResult.model_construct(overall=bucket)
    complexity = _complexity(complexity_score)
    experiment = ResearchExperimentRecord.model_construct(backtest=backtest, complexity=complexity)
    iteration = ResearchLoopIterationRecord.model_construct(experiment=experiment) if compile_status == "compiled" else None
    return FactoryCandidateRecord.model_construct(
        id=candidate_id,
        run_id="run",
        generation=1,
        parent_candidate_id="parent",
        lineage_id="run",
        strategy_family="Fam",
        definition_id=candidate_id,
        definition_version=1,
        hypothesis=_hypothesis(),
        lifecycle_stage=lifecycle_stage,
        compile_status=compile_status,
        compile_detail="x",
        iteration=iteration,
        mutation_candidate=None,
        survived=lifecycle_stage == "survivor",
        decision_reason="x",
        created_at=_CREATED_AT,
        research_family=None,
        candidate_seed=None,
        discovery_reason=None,
        duplicate_of_candidate_id=None,
        adversarial_result=None,
        scorecard_classification=None,
        sibling_rank=None,
        fitness_rationale=None,
        research_council=None,
    )


class TestRankCandidatesRobustnessFirst:
    def test_directives_own_example_shallow_drawdown_beats_high_return(self) -> None:
        """The directive's own explicit example: $100k profit + 35%
        drawdown must NOT beat $30k profit + 10% drawdown. In this
        engine's own real R-multiple units: a candidate with a huge
        expectancy but severe drawdown must rank BELOW a candidate with
        modest expectancy and shallow drawdown."""
        high_return_high_drawdown = _candidate(candidate_id="high-return", max_drawdown_r=-35.0, profit_factor=3.0, expectancy_r=5.0)
        low_return_low_drawdown = _candidate(candidate_id="low-return", max_drawdown_r=-10.0, profit_factor=1.3, expectancy_r=0.5)
        ranked = rank_candidates([high_return_high_drawdown, low_return_low_drawdown])
        assert ranked[0].id == "low-return"
        assert ranked[1].id == "high-return"

    def test_drawdown_checked_before_profit_factor(self) -> None:
        lower_dd_lower_pf = _candidate(candidate_id="a", max_drawdown_r=-2.0, profit_factor=1.1, expectancy_r=0.1)
        higher_dd_higher_pf = _candidate(candidate_id="b", max_drawdown_r=-5.0, profit_factor=5.0, expectancy_r=2.0)
        ranked = rank_candidates([higher_dd_higher_pf, lower_dd_lower_pf])
        assert ranked[0].id == "a"

    def test_profit_factor_tie_break_when_drawdown_equal(self) -> None:
        lower_pf = _candidate(candidate_id="a", max_drawdown_r=-2.0, profit_factor=1.1, expectancy_r=0.3)
        higher_pf = _candidate(candidate_id="b", max_drawdown_r=-2.0, profit_factor=2.0, expectancy_r=0.3)
        ranked = rank_candidates([lower_pf, higher_pf])
        assert ranked[0].id == "b"

    def test_complexity_is_the_final_tie_break(self) -> None:
        simple = _candidate(candidate_id="simple", max_drawdown_r=-2.0, profit_factor=1.5, expectancy_r=0.3, complexity_score=3)
        complex_ = _candidate(candidate_id="complex", max_drawdown_r=-2.0, profit_factor=1.5, expectancy_r=0.3, complexity_score=14)
        ranked = rank_candidates([complex_, simple])
        assert ranked[0].id == "simple"

    def test_lifecycle_stage_beats_every_other_axis(self) -> None:
        survivor_worse_numbers = _candidate(candidate_id="survivor", lifecycle_stage="survivor", max_drawdown_r=-9.0, profit_factor=1.05, expectancy_r=0.01)
        rejected_better_numbers = _candidate(candidate_id="rejected", lifecycle_stage="rejected", max_drawdown_r=-1.0, profit_factor=5.0, expectancy_r=3.0)
        ranked = rank_candidates([rejected_better_numbers, survivor_worse_numbers])
        assert ranked[0].id == "survivor"

    def test_compile_rejected_ranks_last(self) -> None:
        compiled = _candidate(candidate_id="compiled")
        rejected = _candidate(candidate_id="rejected", lifecycle_stage="compile_rejected", compile_status="invalid")
        ranked = rank_candidates([rejected, compiled])
        assert ranked[-1].id == "rejected"

    def test_zero_trades_ranks_below_any_real_evidence(self) -> None:
        no_evidence = _candidate(candidate_id="empty", trade_count=0, max_drawdown_r=None, profit_factor=None, expectancy_r=None)
        has_evidence = _candidate(candidate_id="real", max_drawdown_r=-9.0, profit_factor=1.01, expectancy_r=0.01)
        ranked = rank_candidates([no_evidence, has_evidence])
        assert ranked[0].id == "real"

    def test_stable_sort_preserves_order_on_full_tie(self) -> None:
        a = _candidate(candidate_id="a")
        b = _candidate(candidate_id="b")
        ranked = rank_candidates([a, b])
        assert [c.id for c in ranked] == ["a", "b"]


class TestDescribeFitnessRank:
    def test_cites_real_values(self) -> None:
        candidate = _candidate(candidate_id="x", max_drawdown_r=-4.5, profit_factor=1.75, expectancy_r=0.42, complexity_score=7)
        text = describe_fitness_rank(candidate, rank=1, total_siblings=3)
        assert "1/3" in text
        assert "4.5" in text or "-4.5" in text
        assert "1.75" in text
        assert "0.42" in text
        assert "7" in text

    def test_compile_rejected_text(self) -> None:
        candidate = _candidate(candidate_id="x", lifecycle_stage="compile_rejected", compile_status="invalid")
        text = describe_fitness_rank(candidate, rank=2, total_siblings=2)
        assert "never reached a real backtest" in text

    def test_zero_trades_text(self) -> None:
        candidate = _candidate(candidate_id="x", trade_count=0, max_drawdown_r=None, profit_factor=None, expectancy_r=None)
        text = describe_fitness_rank(candidate, rank=1, total_siblings=1)
        assert "zero closed trades" in text
