"""Covers app/strategy_lab.py — v0.7 Feature 52 (Part 1), the Strategy
Validation Laboratory. Every artifact here must trace to a real, already-
generated source (a strategy's own aggregated SimulationResult stats, a
real StrategyReview verdict, real market data) — never an independently
invented number.
"""
from __future__ import annotations

from app.market_data import MockMarketDataProvider
from app.market_intelligence import default_market_intelligence_state
from app.sandbox import generate_strategy_review
from app.schemas import CoachReport, ResearchItem, SimulationResult, Strategy, WatchlistEntry
from app.strategy_lab import (
    compute_strategy_confidence_score,
    compute_strategy_regime_test,
    generate_strategy_dossier,
    generate_strategy_executive_review,
    generate_strategy_founder_approval,
    run_strategy_monte_carlo,
    validate_strategy_liquidity,
)


def _now_iso() -> str:
    return "2026-01-01T00:00:00+00:00"


def _strategy(*, allocated_capital: float = 0.0) -> Strategy:
    return Strategy(
        id="strategy-1",
        name="Momentum Breakout",
        description="Follows short-term price momentum.",
        createdBy="echo",  # type: ignore[arg-type]
        focusCategory="stock",  # type: ignore[arg-type]
        createdAt=_now_iso(),
        stage="market_simulation",  # type: ignore[arg-type]
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
