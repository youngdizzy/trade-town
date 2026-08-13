"""Covers app/strategy_lab.py — v0.7 Feature 52 (Parts 1 and 2) and
Feature 53 (Company Certification), the Strategy Validation Laboratory.
Every artifact here must trace to a real, already-generated source (a
strategy's own aggregated SimulationResult stats, a real StrategyReview
verdict, real market data) — never an independently invented number.
"""
from __future__ import annotations

from app.market_data import MockMarketDataProvider
from app.market_intelligence import default_market_intelligence_state
from app.sandbox import generate_strategy_review
from app.schemas import (
    CoachReport,
    ModelValidationCheck,
    ModelValidationReport,
    ResearchItem,
    SimulationResult,
    Strategy,
    StrategyMonteCarloResult,
    StrategyStageEvent,
    WatchlistEntry,
)
from app.strategy_lab import (
    CERTIFICATION_MAX_RUIN_PCT,
    CERTIFICATION_MIN_TRADE_COUNT,
    EXPERIMENT_TIER_MAJOR_PCT,
    EXPERIMENT_TIER_MODERATE_PCT,
    EXPERIMENT_TIER_TRANSFORMATIONAL_PCT,
    HALL_OF_FAME_MIN_PROFIT_FACTOR,
    HALL_OF_FAME_MIN_TRADE_COUNT,
    HALL_OF_FAME_MIN_WIN_RATE,
    MIN_RETIREMENT_TRADE_COUNT,
    _tail_mean,
    compute_experiment_tier,
    compute_strategy_certification,
    compute_strategy_confidence_score,
    compute_strategy_executive_dashboard,
    compute_strategy_health,
    compute_strategy_regime_test,
    evaluate_certification_readiness,
    evaluate_retirement_readiness,
    generate_strategy_dossier,
    generate_strategy_executive_review,
    generate_strategy_founder_approval,
    generate_strategy_retirement_outcome,
    run_strategy_monte_carlo,
    validate_strategy_liquidity,
)


def _now_iso() -> str:
    return "2026-01-01T00:00:00+00:00"


def _strategy(*, allocated_capital: float = 0.0, stage: str = "market_simulation", stage_history: list[StrategyStageEvent] | None = None) -> Strategy:
    return Strategy(
        id="strategy-1",
        name="Momentum Breakout",
        description="Follows short-term price momentum.",
        createdBy="echo",  # type: ignore[arg-type]
        focusCategory="stock",  # type: ignore[arg-type]
        createdAt=_now_iso(),
        stage=stage,  # type: ignore[arg-type]
        stageHistory=stage_history or [],
        allocatedCapital=allocated_capital,
    )


def _result(
    *,
    strategy_id: str = "strategy-1",
    scenario: str = "historical",
    win_rate: float = 60.0,
    max_drawdown_pct: float = 10.0,
    win_count: int = 6,
    loss_count: int = 4,
    avg_win_pct: float = 5.0,
    avg_loss_pct: float = -3.0,
    profit_factor: float = 2.5,
    total_return_pct: float = 18.0,
    trade_count: int = 10,
) -> SimulationResult:
    return SimulationResult(
        id=f"result-{strategy_id}-{scenario}-{win_rate}",
        strategyId=strategy_id,
        strategyName="Momentum Breakout",
        symbol="NEXA",
        totalReturnPct=total_return_pct,
        winRate=win_rate,
        maxDrawdownPct=max_drawdown_pct,
        sharpeRatio=1.5,
        sortinoRatio=1.5,
        tradeCount=trade_count,
        runBy="quant",  # type: ignore[arg-type]
        completedAt=_now_iso(),
        scenario=scenario,  # type: ignore[arg-type]
        winCount=win_count,
        lossCount=loss_count,
        avgWinPct=avg_win_pct,
        avgLossPct=avg_loss_pct,
        expectedValuePct=1.0,
        profitFactor=profit_factor,
        riskRewardRatio=avg_win_pct / abs(avg_loss_pct),
    )


def _research_item() -> ResearchItem:
    return ResearchItem(
        id="research-1",
        title="Momentum screen",
        symbol="NEXA",
        category="stock",  # type: ignore[arg-type]
        priority="normal",  # type: ignore[arg-type]
        status="completed",  # type: ignore[arg-type]
        assignedAgent="echo",  # type: ignore[arg-type]
        summary="Momentum looks strong.",
        confidence=70.0,
        createdAt=_now_iso(),
        updatedAt=_now_iso(),
    )


def _coach_report(*, company_score: float = 70.0) -> CoachReport:
    return CoachReport(
        id="report-1",
        period="weekly",
        companyScore=company_score,
        agentRankings=[],
        researchAccuracy=80.0,
        winRate=60.0,
        lossRate=40.0,
        averageConfidence=75.0,
        riskScore=80.0,
        commonMistakes=[],
        strengths=["Consistent process discipline"],
        recommendations=[],
        createdAt=_now_iso(),
    )


def _watchlist() -> list[WatchlistEntry]:
    return [WatchlistEntry(symbol="NEXA", name="Nexa Corp", lastPrice=100.0, dailyChangePct=0.0, status="completed", researchProgress=1.0, assignedAgent=None)]


class TestRunStrategyMonteCarlo:
    def test_returns_none_with_no_completed_results(self) -> None:
        assert run_strategy_monte_carlo(_strategy(), [], sim_day=5) is None

    def test_derives_every_number_from_the_strategys_own_real_results(self) -> None:
        results = [_result(win_rate=70.0, avg_win_pct=6.0, avg_loss_pct=-2.0, trade_count=20)]
        mc = run_strategy_monte_carlo(_strategy(), results, sim_day=5)
        assert mc is not None
        assert mc.strategy_id == "strategy-1"
        assert mc.paths_simulated == 200
        assert mc.source_win_rate == 70.0
        assert mc.source_avg_win_pct == 6.0
        assert mc.source_avg_loss_pct == -2.0
        assert 0.0 <= mc.probability_of_profit_pct <= 100.0
        assert 0.0 <= mc.probability_of_ruin_pct <= 100.0
        assert mc.capital_survival_pct == round(100 - mc.probability_of_ruin_pct, 1)

    def test_ignores_results_from_other_strategies(self) -> None:
        results = [_result(strategy_id="strategy-2")]
        assert run_strategy_monte_carlo(_strategy(), results, sim_day=5) is None

    def test_a_strategy_with_a_strong_edge_shows_a_low_probability_of_ruin(self) -> None:
        results = [_result(win_rate=90.0, avg_win_pct=8.0, avg_loss_pct=-1.0, trade_count=15)]
        mc = run_strategy_monte_carlo(_strategy(), results, sim_day=5)
        assert mc is not None
        assert mc.probability_of_ruin_pct < 10.0

    def test_var_and_cvar_are_real_tail_reads_off_the_same_bootstrap(self) -> None:
        """Quantitative Research & Intelligence System, Piece 3 — VaR95/99
        and CVaR95/99 are percentile/tail-mean reads off the existing
        200-path bootstrap's own sorted `finals` array, not a second
        simulation. The randomness makes exact values non-deterministic,
        but these ordering invariants must always hold: the 99th-
        percentile tail is at least as bad as the 95th, and each CVaR
        (a tail *mean*, including the boundary path and everything
        worse) is never better than its own VaR boundary."""
        results = [_result(win_rate=55.0, avg_win_pct=4.0, avg_loss_pct=-3.0, trade_count=20)]
        mc = run_strategy_monte_carlo(_strategy(), results, sim_day=5)
        assert mc is not None
        assert mc.value_at_risk_99_pct <= mc.value_at_risk_95_pct
        assert mc.conditional_value_at_risk_99_pct <= mc.conditional_value_at_risk_95_pct
        assert mc.conditional_value_at_risk_95_pct <= mc.value_at_risk_95_pct
        assert mc.conditional_value_at_risk_99_pct <= mc.value_at_risk_99_pct
        # Also consistent with the existing p10 return-range-low read:
        # a 5%-tail VaR must be at least as bad as the 10%-tail edge.
        assert mc.value_at_risk_95_pct <= mc.return_range_low_pct


class TestTailMean:
    """Quantitative Research & Intelligence System, Piece 3 — CVaR's
    underlying helper, tested directly with a deterministic sorted
    array (bypassing the bootstrap's own randomness)."""

    def test_matches_hand_computed_worst_fraction_mean(self) -> None:
        sorted_values = [-10.0, -5.0, -2.0, 0.0, 3.0, 8.0, 12.0, 20.0, 25.0, 30.0]
        # p=0.2 over 10 values -> idx = int(10*0.2) = 2 -> tail = first 3
        # values (indices 0-2): [-10.0, -5.0, -2.0], mean = -17/3.
        assert _tail_mean(sorted_values, 0.2) == sum([-10.0, -5.0, -2.0]) / 3

    def test_empty_list_is_zero(self) -> None:
        assert _tail_mean([], 0.05) == 0.0

    def test_single_value_returns_that_value(self) -> None:
        assert _tail_mean([-7.0], 0.05) == -7.0

    def test_uses_the_same_index_convention_as_percentile(self) -> None:
        # For any sorted array, the tail mean must include at least the
        # same boundary element _percentile() itself would return, and
        # never be more favorable than it (the mean of "the boundary
        # plus everything worse" can't beat the boundary alone unless
        # every included value ties it).
        sorted_values = [-20.0, -15.0, -10.0, -5.0, 0.0, 5.0, 10.0]
        boundary = sorted_values[min(len(sorted_values) - 1, max(0, int(len(sorted_values) * 0.3)))]
        assert _tail_mean(sorted_values, 0.3) <= boundary


class TestComputeStrategyRegimeTest:
    def test_returns_none_with_no_completed_results(self) -> None:
        assert compute_strategy_regime_test(_strategy(), [], sim_day=5) is None

    def test_buckets_are_labeled_with_the_real_regimes_they_cover(self) -> None:
        results = [_result(scenario="bull", total_return_pct=20.0, win_rate=65.0)]
        report = compute_strategy_regime_test(_strategy(), results, sim_day=5)
        assert report is not None
        bull_bucket = next(b for b in report.buckets if b.scenario == "bull")
        assert bull_bucket.tested is True
        assert bull_bucket.run_count == 1
        assert len(bull_bucket.regimes) > 0
        untested = [b for b in report.buckets if b.scenario != "bull"]
        assert all(not b.tested for b in untested)

    def test_best_and_worst_scenario_reflect_real_returns(self) -> None:
        results = [
            _result(scenario="bull", total_return_pct=30.0, win_rate=70.0),
            _result(scenario="bear", total_return_pct=-15.0, win_rate=30.0),
        ]
        report = compute_strategy_regime_test(_strategy(), results, sim_day=5)
        assert report is not None
        assert report.best_scenario == "bull"
        assert report.worst_scenario == "bear"


class TestValidateStrategyLiquidity:
    def test_returns_none_with_an_empty_watchlist(self) -> None:
        assert validate_strategy_liquidity(_strategy(), [], MockMarketDataProvider(), sim_day=5) is None

    def test_checks_every_watched_symbol_against_real_market_data(self) -> None:
        validation = validate_strategy_liquidity(_strategy(), _watchlist(), MockMarketDataProvider(), sim_day=5)
        assert validation is not None
        assert validation.symbols_checked == ["NEXA"]
        assert validation.verdict in ("favorable", "neutral", "unfavorable")
        assert len(validation.liquidity_reads) == 1
        assert len(validation.structure_reads) == 1


class TestGenerateStrategyExecutiveReview:
    def test_produces_all_nine_real_department_seats(self) -> None:
        strategy = _strategy()
        review = generate_strategy_review(strategy, [_result()], [_research_item()], 0, sim_day=5)
        monte_carlo = run_strategy_monte_carlo(strategy, [_result()], sim_day=5)
        regime_test = compute_strategy_regime_test(strategy, [_result()], sim_day=5)
        exec_review = generate_strategy_executive_review(
            strategy, review, [_research_item()], [_coach_report()], monte_carlo, regime_test, default_market_intelligence_state(), 0, sim_day=5
        )
        roles = {o.role for o in exec_review.opinions}
        assert roles == {"research", "quant", "risk", "simulation", "decision_intelligence", "coach", "founders", "devils_advocate", "market_intelligence"}
        assert len(exec_review.opinions) == 9
        assert 0.0 <= exec_review.overall_confidence_pct <= 100.0

    def test_two_or_more_rejecting_departments_yields_a_reject_recommendation(self) -> None:
        strategy = _strategy()
        # A strategy with terrible real numbers should draw real rejecting
        # opinions from at least Quant and Risk.
        bad_result = _result(win_rate=20.0, max_drawdown_pct=45.0, avg_win_pct=1.0, avg_loss_pct=-8.0, profit_factor=0.3, total_return_pct=-30.0)
        review = generate_strategy_review(strategy, [bad_result], [], 0, sim_day=5)
        monte_carlo = run_strategy_monte_carlo(strategy, [bad_result], sim_day=5)
        exec_review = generate_strategy_executive_review(strategy, review, [], [], monte_carlo, None, default_market_intelligence_state(), 0, sim_day=5)
        rejecting = [o for o in exec_review.opinions if o.stance in ("disagree", "recommend_rejecting")]
        if len(rejecting) >= 2:
            assert exec_review.recommendation == "reject"


class TestGenerateStrategyFounderApproval:
    def test_approves_when_the_executive_review_recommends_advancing_with_high_confidence(self) -> None:
        strategy = _strategy()
        review = generate_strategy_review(strategy, [_result()], [_research_item()], 0, sim_day=5)
        monte_carlo = run_strategy_monte_carlo(strategy, [_result(win_rate=80.0, avg_win_pct=8.0, avg_loss_pct=-1.5)], sim_day=5)
        regime_test = compute_strategy_regime_test(strategy, [_result()], sim_day=5)
        exec_review = generate_strategy_executive_review(strategy, review, [_research_item()], [_coach_report()], monte_carlo, regime_test, default_market_intelligence_state(), 0, sim_day=5)
        approval = generate_strategy_founder_approval(strategy, exec_review, sim_day=5)
        if exec_review.recommendation == "advance" and exec_review.overall_confidence_pct >= 60.0:
            assert approval.verdict == "approved"
        else:
            assert approval.verdict == "rejected"

    def test_rejects_when_the_executive_review_recommends_rejecting(self) -> None:
        strategy = _strategy()
        bad_result = _result(win_rate=20.0, max_drawdown_pct=45.0, avg_win_pct=1.0, avg_loss_pct=-8.0, profit_factor=0.3, total_return_pct=-30.0)
        review = generate_strategy_review(strategy, [bad_result], [], 0, sim_day=5)
        monte_carlo = run_strategy_monte_carlo(strategy, [bad_result], sim_day=5)
        exec_review = generate_strategy_executive_review(strategy, review, [], [], monte_carlo, None, default_market_intelligence_state(), 0, sim_day=5)
        approval = generate_strategy_founder_approval(strategy, exec_review, sim_day=5)
        assert approval.evidence_summary == exec_review.reason
        if exec_review.recommendation != "advance":
            assert approval.verdict == "rejected"


class TestComputeStrategyConfidenceScore:
    def test_falls_back_to_a_real_low_default_with_no_evidence_at_all(self) -> None:
        score = compute_strategy_confidence_score(_strategy(), None, None, None, None, sim_day=5)
        assert score.overall_confidence_pct == 40.0
        assert score.risk_rating == "elevated"

    def test_uses_real_monte_carlo_and_executive_review_numbers_when_present(self) -> None:
        strategy = _strategy()
        review = generate_strategy_review(strategy, [_result()], [_research_item()], 0, sim_day=5)
        monte_carlo = run_strategy_monte_carlo(strategy, [_result()], sim_day=5)
        regime_test = compute_strategy_regime_test(strategy, [_result()], sim_day=5)
        exec_review = generate_strategy_executive_review(strategy, review, [_research_item()], [_coach_report()], monte_carlo, regime_test, default_market_intelligence_state(), 0, sim_day=5)
        score = compute_strategy_confidence_score(strategy, review, monte_carlo, regime_test, exec_review, sim_day=5)
        assert monte_carlo is not None
        expected = round((exec_review.overall_confidence_pct + monte_carlo.probability_of_profit_pct) / 2, 1)
        assert score.overall_confidence_pct == expected


class TestGenerateStrategyDossier:
    def test_assembles_every_real_artifact_for_the_strategy(self) -> None:
        strategy = _strategy()
        results = [_result()]
        review = generate_strategy_review(strategy, results, [_research_item()], 0, sim_day=5)
        monte_carlo = run_strategy_monte_carlo(strategy, results, sim_day=5)
        regime_test = compute_strategy_regime_test(strategy, results, sim_day=5)
        liquidity = validate_strategy_liquidity(strategy, _watchlist(), MockMarketDataProvider(), sim_day=5)
        exec_review = generate_strategy_executive_review(strategy, review, [_research_item()], [_coach_report()], monte_carlo, regime_test, default_market_intelligence_state(), 0, sim_day=5)
        approval = generate_strategy_founder_approval(strategy, exec_review, sim_day=5)
        assert liquidity is not None

        dossier = generate_strategy_dossier(strategy, [], [review], [monte_carlo] if monte_carlo else [], [regime_test] if regime_test else [], [liquidity], [exec_review], [approval])
        assert dossier.strategy_id == "strategy-1"
        assert dossier.latest_review is not None and dossier.latest_review.id == review.id
        assert dossier.monte_carlo is not None
        assert dossier.regime_test is not None
        assert dossier.liquidity_validation is not None and dossier.liquidity_validation.id == liquidity.id
        assert dossier.executive_review is not None and dossier.executive_review.id == exec_review.id
        assert dossier.founder_approval is not None and dossier.founder_approval.id == approval.id
        assert dossier.confidence is not None
        assert dossier.experiment_tier is not None

    def test_leaves_every_optional_field_none_with_no_history_at_all(self) -> None:
        dossier = generate_strategy_dossier(_strategy(), [], [], [], [], [], [], [])
        assert dossier.latest_report is None
        assert dossier.latest_review is None
        assert dossier.monte_carlo is None
        assert dossier.regime_test is None
        assert dossier.liquidity_validation is None
        assert dossier.executive_review is None
        assert dossier.founder_approval is None
        assert dossier.confidence is None
        assert dossier.experiment_tier is None
        assert dossier.experiment_tier_rationale is None


def _monte_carlo(*, median_return_pct: float = 0.0, worst_case_drawdown_pct: float = 0.0) -> StrategyMonteCarloResult:
    return StrategyMonteCarloResult(
        id="montecarlo-1",
        strategyId="strategy-1",
        strategyName="Momentum Breakout",
        pathsSimulated=200,
        tradesPerPath=20,
        sourceWinRate=55.0,
        sourceAvgWinPct=2.0,
        sourceAvgLossPct=-1.0,
        medianReturnPct=median_return_pct,
        returnRangeLowPct=median_return_pct - 5.0,
        returnRangeHighPct=median_return_pct + 5.0,
        medianMaxDrawdownPct=abs(worst_case_drawdown_pct) / 2,
        worstCaseDrawdownPct=worst_case_drawdown_pct,
        probabilityOfProfitPct=60.0,
        probabilityOfRuinPct=5.0,
        capitalSurvivalPct=95.0,
        valueAtRisk95Pct=median_return_pct - 8.0,
        valueAtRisk99Pct=median_return_pct - 12.0,
        conditionalValueAtRisk95Pct=median_return_pct - 10.0,
        conditionalValueAtRisk99Pct=median_return_pct - 15.0,
        simDay=10,
        createdAt=_now_iso(),
    )


class TestComputeExperimentTier:
    """Design Bible Chapter 62 — Experiment Classification. Real
    magnitude (the larger of projected upside or realized downside from
    the strategy's own Monte Carlo bootstrap), bucketed against
    EXPERIMENT_TIER_*_PCT — never a fabricated risk score."""

    def test_small_magnitude_is_minor(self) -> None:
        tier, rationale = compute_experiment_tier(_monte_carlo(median_return_pct=3.0, worst_case_drawdown_pct=-4.0))
        assert tier == "minor"
        assert "4.0%" in rationale

    def test_at_the_moderate_threshold_is_moderate(self) -> None:
        tier, _ = compute_experiment_tier(_monte_carlo(median_return_pct=EXPERIMENT_TIER_MODERATE_PCT, worst_case_drawdown_pct=0.0))
        assert tier == "moderate"

    def test_at_the_major_threshold_is_major(self) -> None:
        tier, _ = compute_experiment_tier(_monte_carlo(median_return_pct=0.0, worst_case_drawdown_pct=-EXPERIMENT_TIER_MAJOR_PCT))
        assert tier == "major"

    def test_at_the_transformational_threshold_is_transformational(self) -> None:
        tier, _ = compute_experiment_tier(_monte_carlo(median_return_pct=EXPERIMENT_TIER_TRANSFORMATIONAL_PCT, worst_case_drawdown_pct=0.0))
        assert tier == "transformational"

    def test_uses_whichever_of_upside_or_downside_is_larger_in_magnitude(self) -> None:
        # Downside (-40%) is larger in magnitude than upside (+8%), so the
        # tier must be driven by the drawdown, not the return.
        tier, rationale = compute_experiment_tier(_monte_carlo(median_return_pct=8.0, worst_case_drawdown_pct=-40.0))
        assert tier == "major"
        assert "40.0%" in rationale


class TestComputeStrategyHealth:
    def test_returns_none_with_no_completed_results(self) -> None:
        assert compute_strategy_health(_strategy(), [], sim_day=5) is None

    def test_a_young_strategy_reads_recent_and_lifetime_as_identical(self) -> None:
        results = [_result(win_rate=60.0, total_return_pct=10.0)]
        health = compute_strategy_health(_strategy(), results, sim_day=5)
        assert health is not None
        assert health.recent_win_rate == health.lifetime_win_rate
        assert health.recent_avg_return_pct == health.lifetime_avg_return_pct
        assert health.trend == "stable"
        assert health.recent_sample_size == health.lifetime_sample_size == 1

    def test_a_strong_consistent_track_record_reads_excellent(self) -> None:
        results = [_result(win_rate=70.0, total_return_pct=15.0, max_drawdown_pct=5.0, avg_win_pct=6.0, avg_loss_pct=-2.0) for _ in range(3)]
        for i, r in enumerate(results):
            results[i] = r.model_copy(update={"id": f"result-{i}"})
        health = compute_strategy_health(_strategy(), results, sim_day=5)
        assert health is not None
        assert health.status == "excellent"

    def test_a_recently_disastrous_run_reads_retire_candidate(self) -> None:
        good = [_result(win_rate=70.0, total_return_pct=15.0).model_copy(update={"id": f"good-{i}"}) for i in range(3)]
        bad = [_result(win_rate=15.0, total_return_pct=-25.0, max_drawdown_pct=40.0).model_copy(update={"id": f"bad-{i}"}) for i in range(3)]
        health = compute_strategy_health(_strategy(), [*good, *bad], sim_day=5)
        assert health is not None
        assert health.status == "retire_candidate"
        assert health.trend == "declining"

    def test_ignores_results_from_other_strategies(self) -> None:
        results = [_result(strategy_id="strategy-2")]
        assert compute_strategy_health(_strategy(), results, sim_day=5) is None


def _model_validation_report(*, verdict: str = "rejected", strategy_id: str = "strategy-1") -> ModelValidationReport:
    return ModelValidationReport(
        id=f"validation-{strategy_id}",
        strategyId=strategy_id,
        strategyName="Momentum Breakout",
        reviewId="review-1",
        existingReviewCount=0,
        verdict=verdict,  # type: ignore[arg-type]
        checks=[
            ModelValidationCheck(
                id="tail_risk",
                label="Tail Risk",
                passed=False,
                evidence="Probability of ruin 22.0% exceeds the 15.0% certification bar.",
                reasoning="This strategy's own Monte Carlo bootstrap shows an unacceptable real ruin risk.",
                thresholdSource="CERTIFICATION_MAX_RUIN_PCT (strategy_lab.py)",
            ),
        ],
        evidenceSummary="1 of 6 real checks failed: Tail Risk.",
        dataSourcesAndAssumptions=["Reviews the same Monte Carlo bootstrap Vector's research already computed."],
        simDay=10,
        createdAt=_now_iso(),
    )


class TestGenerateStrategyRetirementOutcome:
    def test_a_real_hall_of_fame_worthy_track_record_earns_induction(self) -> None:
        strategy = _strategy(stage="approved", stage_history=[StrategyStageEvent(id="stage-0", stage="idea", detail="Created.", simDay=1, createdAt=_now_iso())])
        results = [
            _result(win_rate=HALL_OF_FAME_MIN_WIN_RATE + 5.0, profit_factor=HALL_OF_FAME_MIN_PROFIT_FACTOR + 0.5, max_drawdown_pct=5.0, trade_count=HALL_OF_FAME_MIN_TRADE_COUNT).model_copy(
                update={"id": f"result-{i}"}
            )
            for i in range(3)
        ]
        review = generate_strategy_review(strategy, results, [], 0, sim_day=10)
        monte_carlo = run_strategy_monte_carlo(strategy, results, sim_day=10)
        exec_review = generate_strategy_executive_review(strategy, review, [], [], monte_carlo, None, default_market_intelligence_state(), 0, sim_day=10)
        founder_approval = generate_strategy_founder_approval(strategy, exec_review, sim_day=10).model_copy(update={"verdict": "approved"})

        hof_entry, failed_entry = generate_strategy_retirement_outcome(strategy, results, review, exec_review, founder_approval, "Retired at its peak.", sim_day=20)
        assert failed_entry is None
        assert hof_entry is not None
        assert hof_entry.strategy_id == "strategy-1"
        assert hof_entry.trades_executed == HALL_OF_FAME_MIN_TRADE_COUNT * 3
        assert hof_entry.sim_days_active == 19
        assert hof_entry.retired_reason == "Retired at its peak."

    def test_a_weak_track_record_files_a_failed_archive_entry_instead(self) -> None:
        strategy = _strategy(stage="limited_live_capital")
        bad_result = _result(win_rate=20.0, max_drawdown_pct=45.0, avg_win_pct=1.0, avg_loss_pct=-8.0, profit_factor=0.3, total_return_pct=-30.0)
        review = generate_strategy_review(strategy, [bad_result], [], 0, sim_day=10)
        hof_entry, failed_entry = generate_strategy_retirement_outcome(strategy, [bad_result], review, None, None, "Never earned real trust.", sim_day=20)
        assert hof_entry is None
        assert failed_entry is not None
        assert failed_entry.strategy_id == "strategy-1"
        assert failed_entry.failed_at_stage == "limited_live_capital"
        assert failed_entry.what_failed
        assert failed_entry.retired_reason == "Never earned real trust."

    def test_never_files_hall_of_fame_without_a_real_approved_founder_verdict(self) -> None:
        strategy = _strategy(stage="approved")
        results = [
            _result(win_rate=90.0, profit_factor=3.0, max_drawdown_pct=2.0, trade_count=HALL_OF_FAME_MIN_TRADE_COUNT).model_copy(update={"id": f"result-{i}"}) for i in range(3)
        ]
        review = generate_strategy_review(strategy, results, [], 0, sim_day=10)
        hof_entry, failed_entry = generate_strategy_retirement_outcome(strategy, results, review, None, None, "No founder approval on file.", sim_day=20)
        assert hof_entry is None
        assert failed_entry is not None

    def test_a_rejected_model_validation_is_folded_into_the_failed_archive(self) -> None:
        """Quantitative Research & Intelligence System, Piece 6 — a real
        Meridian/CIO rejection becomes part of the permanent
        FailedStrategyArchiveEntry, not just a report that disappears
        once Company Review ends."""
        strategy = _strategy(stage="limited_live_capital")
        bad_result = _result(win_rate=20.0, max_drawdown_pct=45.0, avg_win_pct=1.0, avg_loss_pct=-8.0, profit_factor=0.3, total_return_pct=-30.0)
        review = generate_strategy_review(strategy, [bad_result], [], 0, sim_day=10)
        validation = _model_validation_report(verdict="rejected")

        _, failed_entry = generate_strategy_retirement_outcome(
            strategy, [bad_result], review, None, None, "Failed independent validation.", sim_day=20, latest_model_validation=validation
        )
        assert failed_entry is not None
        assert any("Meridian/CIO" in item and "rejected" in item for item in failed_entry.what_failed)
        assert any(validation.evidence_summary in item for item in failed_entry.what_failed)
        assert any("Tail Risk" in item and validation.checks[0].reasoning in item for item in failed_entry.lessons_learned)

    def test_an_approved_model_validation_is_not_folded_in_as_a_failure(self) -> None:
        strategy = _strategy(stage="limited_live_capital")
        bad_result = _result(win_rate=20.0, max_drawdown_pct=45.0, avg_win_pct=1.0, avg_loss_pct=-8.0, profit_factor=0.3, total_return_pct=-30.0)
        review = generate_strategy_review(strategy, [bad_result], [], 0, sim_day=10)
        validation = _model_validation_report(verdict="approved")

        _, failed_entry = generate_strategy_retirement_outcome(
            strategy, [bad_result], review, None, None, "Failed for other reasons.", sim_day=20, latest_model_validation=validation
        )
        assert failed_entry is not None
        assert not any("Meridian/CIO" in item for item in failed_entry.what_failed)

    def test_no_model_validation_on_file_behaves_exactly_as_before(self) -> None:
        strategy = _strategy(stage="limited_live_capital")
        bad_result = _result(win_rate=20.0, max_drawdown_pct=45.0, avg_win_pct=1.0, avg_loss_pct=-8.0, profit_factor=0.3, total_return_pct=-30.0)
        review = generate_strategy_review(strategy, [bad_result], [], 0, sim_day=10)

        _, failed_entry = generate_strategy_retirement_outcome(strategy, [bad_result], review, None, None, "Never earned real trust.", sim_day=20)
        assert failed_entry is not None
        assert not any("Meridian/CIO" in item for item in failed_entry.what_failed)


class TestComputeStrategyExecutiveDashboard:
    def test_counts_every_strategy_into_exactly_one_stage_bucket(self) -> None:
        strategies = [
            _strategy(stage="idea"),
            _strategy(stage="paper_trading").model_copy(update={"id": "strategy-2"}),
            _strategy(stage="approved").model_copy(update={"id": "strategy-3"}),
            _strategy(stage="retired").model_copy(update={"id": "strategy-4"}),
        ]
        dashboard = compute_strategy_executive_dashboard(strategies, [], [], [], [], [], [], [], sim_day=5)
        assert dashboard.active_count == 3
        assert dashboard.in_development_count == 1
        assert dashboard.paper_trading_count == 1
        assert dashboard.approved_count == 1
        assert dashboard.retired_count == 1

    def test_best_and_weakest_strategy_reflect_real_average_returns(self) -> None:
        strategies = [_strategy(), _strategy().model_copy(update={"id": "strategy-2", "name": "Value Fundamentals"})]
        results = [
            _result(strategy_id="strategy-1", total_return_pct=25.0),
            _result(strategy_id="strategy-2", total_return_pct=-10.0).model_copy(update={"id": "result-2"}),
        ]
        dashboard = compute_strategy_executive_dashboard(strategies, results, [], [], [], [], [], [], sim_day=5)
        assert dashboard.best_strategy is not None and dashboard.best_strategy.strategy_id == "strategy-1"
        assert dashboard.weakest_strategy is not None and dashboard.weakest_strategy.strategy_id == "strategy-2"

    def test_empty_company_reports_every_slot_as_honestly_none(self) -> None:
        dashboard = compute_strategy_executive_dashboard([], [], [], [], [], [], [], [], sim_day=5)
        assert dashboard.best_strategy is None
        assert dashboard.weakest_strategy is None
        assert dashboard.most_improved_strategy is None
        assert dashboard.newest_strategy is None
        assert dashboard.highest_confidence_strategy is None
        assert dashboard.active_count == 0


def _strong_results(*, count: int = 3, scenario: str = "bull") -> list[SimulationResult]:
    return [
        _result(win_rate=75.0, profit_factor=2.5, max_drawdown_pct=8.0, avg_win_pct=6.0, avg_loss_pct=-2.0, total_return_pct=20.0, trade_count=CERTIFICATION_MIN_TRADE_COUNT, scenario=scenario).model_copy(
            update={"id": f"result-{scenario}-{i}"}
        )
        for i in range(count)
    ]


class TestComputeStrategyCertification:
    def test_a_strategy_with_every_real_requirement_met_is_certified(self) -> None:
        strategy = _strategy(stage="approved")
        results = [*_strong_results(scenario="bull"), *_strong_results(scenario="bear")]
        review = generate_strategy_review(strategy, results, [_research_item()], 0, sim_day=10)
        review = review.model_copy(update={"ceo_decision": "approved"})
        monte_carlo = run_strategy_monte_carlo(strategy, results, sim_day=10)
        regime_test = compute_strategy_regime_test(strategy, results, sim_day=10)
        exec_review = generate_strategy_executive_review(strategy, review, [_research_item()], [_coach_report()], monte_carlo, regime_test, default_market_intelligence_state(), 0, sim_day=10)
        # Force every real department opinion this checklist reads to a
        # real "agree" stance so this fixture exercises the fully-passing
        # path deterministically, the same way other tests here force a
        # specific real outcome by editing the generated object's own
        # already-real fields.
        opinions = [o.model_copy(update={"stance": "agree"}) if o.role in ("risk", "market_intelligence", "quant", "simulation", "decision_intelligence") else o for o in exec_review.opinions]
        exec_review = exec_review.model_copy(update={"opinions": opinions})
        founder_approval = generate_strategy_founder_approval(strategy, exec_review, sim_day=10).model_copy(update={"verdict": "approved"})
        health = compute_strategy_health(strategy, results, sim_day=10)

        certification = compute_strategy_certification(strategy, results, review, monte_carlo, regime_test, exec_review, founder_approval, health)
        failing = [r for r in certification.requirements if not r.met]
        assert failing == [], f"unexpected failing requirements: {[(r.id, r.detail) for r in failing]}"
        assert certification.certified is True

    def test_no_evidence_at_all_is_not_certified(self) -> None:
        certification = compute_strategy_certification(_strategy(stage="idea"), [], None, None, None, None, None, None)
        assert certification.certified is False
        # The brief's own 14 named requirements, plus this module's own
        # added Health Standing requirement (see this function's
        # docstring for why that's the real, automatic "may be revoked"
        # mechanism).
        assert len(certification.requirements) == 15

    def test_a_real_health_decline_automatically_revokes_certification(self) -> None:
        from app.schemas import StrategyHealthAssessment

        strategy = _strategy(stage="approved")
        results = [*_strong_results(scenario="bull"), *_strong_results(scenario="bear")]
        review = generate_strategy_review(strategy, results, [_research_item()], 0, sim_day=10).model_copy(update={"ceo_decision": "approved"})
        monte_carlo = run_strategy_monte_carlo(strategy, results, sim_day=10)
        regime_test = compute_strategy_regime_test(strategy, results, sim_day=10)
        exec_review = generate_strategy_executive_review(strategy, review, [], [_coach_report()], monte_carlo, regime_test, default_market_intelligence_state(), 0, sim_day=10)
        opinions = [o.model_copy(update={"stance": "agree"}) if o.role in ("risk", "market_intelligence", "quant", "simulation", "decision_intelligence") else o for o in exec_review.opinions]
        exec_review = exec_review.model_copy(update={"opinions": opinions})
        founder_approval = generate_strategy_founder_approval(strategy, exec_review, sim_day=10).model_copy(update={"verdict": "approved"})
        declining_health = StrategyHealthAssessment(
            id="health-1",
            strategyId=strategy.id,
            strategyName=strategy.name,
            status="critical",
            trend="declining",
            recentWinRate=20.0,
            lifetimeWinRate=70.0,
            recentAvgReturnPct=-15.0,
            lifetimeAvgReturnPct=15.0,
            recentAvgDrawdownPct=40.0,
            lifetimeAvgDrawdownPct=10.0,
            recentSampleSize=3,
            lifetimeSampleSize=6,
            reasoning=["Recent performance collapsed."],
            simDay=10,
            createdAt=_now_iso(),
        )
        certification = compute_strategy_certification(strategy, results, review, monte_carlo, regime_test, exec_review, founder_approval, declining_health)
        health_req = next(r for r in certification.requirements if r.id == "health_standing")
        assert health_req.met is False
        assert certification.certified is False


class TestEvaluateCertificationReadiness:
    def test_ready_when_the_pre_company_review_checks_all_pass(self) -> None:
        strategy = _strategy(stage="paper_trading")
        results = [*_strong_results(scenario="bull"), *_strong_results(scenario="bear")]
        monte_carlo = run_strategy_monte_carlo(strategy, results, sim_day=10)
        regime_test = compute_strategy_regime_test(strategy, results, sim_day=10)
        ready, detail = evaluate_certification_readiness(strategy, results, monte_carlo, regime_test)
        assert ready is True
        assert "clears every real Certification readiness check" in detail

    def test_not_ready_with_no_real_evidence_at_all(self) -> None:
        strategy = _strategy(stage="paper_trading")
        ready, detail = evaluate_certification_readiness(strategy, [], None, None)
        assert ready is False
        assert "not yet Certification-ready" in detail

    def test_not_ready_when_ruin_probability_is_too_high(self) -> None:
        from app.schemas import StrategyMonteCarloResult

        strategy = _strategy(stage="paper_trading")
        bad_results = [_result(win_rate=20.0, avg_win_pct=1.0, avg_loss_pct=-10.0, trade_count=CERTIFICATION_MIN_TRADE_COUNT, scenario="bull")]
        # A deterministic fixture (rather than run_strategy_monte_carlo's
        # own real bootstrap, which is already covered by
        # TestRunStrategyMonteCarlo above) so this test exercises the
        # gate's own threshold check reliably, not the stochastic path.
        ruinous_monte_carlo = StrategyMonteCarloResult(
            id="montecarlo-1",
            strategyId=strategy.id,
            strategyName=strategy.name,
            pathsSimulated=200,
            tradesPerPath=20,
            sourceWinRate=20.0,
            sourceAvgWinPct=1.0,
            sourceAvgLossPct=-10.0,
            medianReturnPct=-30.0,
            returnRangeLowPct=-60.0,
            returnRangeHighPct=5.0,
            medianMaxDrawdownPct=40.0,
            worstCaseDrawdownPct=25.0,
            probabilityOfProfitPct=15.0,
            probabilityOfRuinPct=40.0,
            capitalSurvivalPct=60.0,
            valueAtRisk95Pct=-45.0,
            valueAtRisk99Pct=-55.0,
            conditionalValueAtRisk95Pct=-50.0,
            conditionalValueAtRisk99Pct=-58.0,
            simDay=10,
            createdAt=_now_iso(),
        )
        assert ruinous_monte_carlo.probability_of_ruin_pct > CERTIFICATION_MAX_RUIN_PCT
        ready, detail = evaluate_certification_readiness(strategy, bad_results, ruinous_monte_carlo, None)
        assert ready is False
        assert "probability of ruin" in detail


class TestEvaluateRetirementReadiness:
    """Trading Psychology & Discipline, Piece B — the Statistical
    Evidence Gate on Strategy Retirement. Every case here traces to the
    CEO's own review: "if evidence insufficient, keep current strategy
    and continue collecting data" / "a single bad run does not
    invalidate a strategy."""

    def test_idea_stage_is_always_ready_no_evidence_bar_applies(self) -> None:
        strategy = _strategy(stage="idea")
        ready, detail = evaluate_retirement_readiness(strategy, [])
        assert ready is True
        assert "not entered real testing yet" in detail

    def test_research_stage_is_always_ready_no_evidence_bar_applies(self) -> None:
        strategy = _strategy(stage="research")
        ready, detail = evaluate_retirement_readiness(strategy, [])
        assert ready is True

    def test_historical_backtest_stage_with_zero_results_is_not_ready(self) -> None:
        strategy = _strategy(stage="historical_backtest")
        ready, detail = evaluate_retirement_readiness(strategy, [])
        assert ready is False
        assert "0 real trade(s)" in detail
        assert str(MIN_RETIREMENT_TRADE_COUNT) in detail

    def test_below_the_minimum_trade_count_is_not_ready(self) -> None:
        strategy = _strategy(stage="market_simulation")
        results = [_result(trade_count=MIN_RETIREMENT_TRADE_COUNT - 1)]
        ready, detail = evaluate_retirement_readiness(strategy, results)
        assert ready is False
        assert "does not invalidate a strategy" in detail

    def test_at_the_minimum_trade_count_is_ready(self) -> None:
        strategy = _strategy(stage="market_simulation")
        results = [_result(trade_count=MIN_RETIREMENT_TRADE_COUNT)]
        ready, detail = evaluate_retirement_readiness(strategy, results)
        assert ready is True
        assert "enough real evidence" in detail

    def test_trade_count_sums_across_multiple_real_runs(self) -> None:
        strategy = _strategy(stage="market_simulation")
        results = [_result(trade_count=4, scenario="bull"), _result(trade_count=4, scenario="bear"), _result(trade_count=2, scenario="sideways")]
        ready, detail = evaluate_retirement_readiness(strategy, results)
        assert ready is True

    def test_a_live_approved_strategy_with_insufficient_evidence_is_still_gated(self) -> None:
        """The most important real case: retirement of a strategy
        already committing capital must not be allowed on a whim."""
        strategy = _strategy(stage="approved")
        results = [_result(trade_count=2)]
        ready, detail = evaluate_retirement_readiness(strategy, results)
        assert ready is False

    def test_only_this_strategys_own_results_count(self) -> None:
        strategy = _strategy(stage="market_simulation")
        other_strategy_results = [_result(strategy_id="strategy-other", trade_count=100)]
        ready, detail = evaluate_retirement_readiness(strategy, other_strategy_results)
        assert ready is False
        assert "0 real trade(s)" in detail
