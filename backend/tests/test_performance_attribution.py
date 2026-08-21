"""Covers app/performance_attribution.py — CEO directive "Next
Professional Trading Firm Phase," Priority 2 (Unified Professional P&L/
Performance Reporting), scoped this pass to real, unambiguous SYMBOL-
level attribution. win/loss uses the same `pnl > 0` / `pnl <= 0`
convention app/portfolio.py::close_position() already uses, so counts
here must always agree with the portfolio-wide ones for the same
trades.
"""
from __future__ import annotations

from app.performance_attribution import (
    CRITICAL_LOSS_STREAK,
    MIN_SYMBOL_SAMPLE_FOR_VERDICT,
    POSSIBLE_LOSS_STREAK,
    REPEATED_INVALIDATION_THRESHOLD,
    ROBUSTNESS_UNAVAILABLE_NOTE,
    WIN_RATE_DIVERGENCE_THRESHOLD_PCT,
    compute_regime_performance,
    compute_session_performance,
    compute_strategy_capital_allocation_evidence,
    compute_strategy_degradation,
    compute_strategy_live_vs_backtest,
    compute_strategy_performance,
    compute_strategy_session_performance,
    compute_symbol_performance,
)
from app.schemas import DecisionVaultEntry, FailureClassification, LiquidityRead, PaperTrade, Strategy, StrategyExposureRead, StrategyHealthAssessment, StrategySessionPerformanceSummary
from app.strategy_lab import HEALTH_RECENT_WINDOW


def _trade(
    *,
    trade_id: str,
    symbol: str = "AAPL",
    pnl: float,
    pnl_pct: float,
    mae_pct: float = 0.0,
    mfe_pct: float = 0.0,
    closed_at: str = "2024-01-01T00:00:00+00:00",
    entry_slippage_bps: float = 0.0,
    exit_slippage_bps: float = 0.0,
) -> PaperTrade:
    return PaperTrade(
        id=trade_id,
        symbol=symbol,
        side="buy",
        quantity=1.0,
        entryPrice=100.0,
        exitPrice=100.0 + pnl,
        pnl=pnl,
        pnlPct=pnl_pct,
        durationMinutes=30,
        confidence=80.0,
        reason="test",
        marketConditions="test",
        supportingAgents=["scout"],
        opposingAgents=[],
        openedAt="2024-01-01T00:00:00+00:00",
        closedAt=closed_at,
        openedSimMinutes=0,
        closedSimMinutes=30,
        maePct=mae_pct,
        mfePct=mfe_pct,
        entrySlippageBps=entry_slippage_bps,
        exitSlippageBps=exit_slippage_bps,
    )


def _strategy(*, strategy_id: str = "strategy-1", name: str = "Momentum Breakout", stage: str = "idea", allocated_capital: float = 0.0) -> Strategy:
    return Strategy(
        id=strategy_id,
        name=name,
        description="test strategy",
        createdBy="echo",  # type: ignore[arg-type]
        focusCategory="stock",  # type: ignore[arg-type]
        createdAt="2024-01-01T00:00:00+00:00",
        stage=stage,  # type: ignore[arg-type]
        allocatedCapital=allocated_capital,
    )


class TestComputeSymbolPerformance:
    def test_empty_trade_history_produces_no_reads(self) -> None:
        summary = compute_symbol_performance([])
        assert summary.reads == []

    def test_groups_by_symbol(self) -> None:
        trades = [
            _trade(trade_id="a", symbol="AAPL", pnl=10.0, pnl_pct=1.0),
            _trade(trade_id="b", symbol="MSFT", pnl=5.0, pnl_pct=0.5),
            _trade(trade_id="c", symbol="AAPL", pnl=-2.0, pnl_pct=-0.2),
        ]
        summary = compute_symbol_performance(trades)
        symbols = {r.symbol for r in summary.reads}
        assert symbols == {"AAPL", "MSFT"}
        aapl = next(r for r in summary.reads if r.symbol == "AAPL")
        assert aapl.trade_count == 2

    def test_reads_sorted_by_total_pnl_descending_most_profitable_first(self) -> None:
        trades = [
            _trade(trade_id="a", symbol="LOSER", pnl=-50.0, pnl_pct=-5.0),
            _trade(trade_id="b", symbol="WINNER", pnl=100.0, pnl_pct=10.0),
            _trade(trade_id="c", symbol="MIDDLE", pnl=10.0, pnl_pct=1.0),
        ]
        summary = compute_symbol_performance(trades)
        assert [r.symbol for r in summary.reads] == ["WINNER", "MIDDLE", "LOSER"]

    def test_win_loss_convention_matches_portfolio_close_position(self) -> None:
        # app/portfolio.py::close_position() counts a win as pnl > 0, a
        # loss as pnl <= 0 (including an exact breakeven) -- this module
        # must use the identical convention.
        trades = [
            _trade(trade_id="a", pnl=10.0, pnl_pct=1.0),  # win
            _trade(trade_id="b", pnl=0.0, pnl_pct=0.0),  # loss (breakeven counts as loss)
            _trade(trade_id="c", pnl=-5.0, pnl_pct=-0.5),  # loss
        ]
        summary = compute_symbol_performance(trades)
        read = summary.reads[0]
        assert read.win_count == 1
        assert read.loss_count == 2
        assert read.win_rate_pct == round(1 / 3 * 100, 1)

    def test_below_min_sample_withholds_expectancy_and_profit_factor(self) -> None:
        trades = [_trade(trade_id="a", pnl=10.0, pnl_pct=1.0)] * 1
        assert len(trades) < MIN_SYMBOL_SAMPLE_FOR_VERDICT
        summary = compute_symbol_performance(trades)
        read = summary.reads[0]
        assert read.evidence_state == "not_enough_data"
        assert read.expectancy_pct is None
        assert read.profit_factor is None
        # Raw counts/totalPnl are real regardless of sample size.
        assert read.trade_count == 1
        assert read.total_pnl == 10.0

    def test_at_min_sample_expectancy_matches_the_simple_average_pnl_pct(self) -> None:
        # expectancy_pct is the win-rate/avg-win/avg-loss decomposition;
        # under the SAME win/loss partition it must land exactly on the
        # simple average pnl_pct across all trades (see module
        # docstring for why this equivalence is expected, not a bug).
        trades = [
            _trade(trade_id="a", pnl=10.0, pnl_pct=4.0),
            _trade(trade_id="b", pnl=-5.0, pnl_pct=-2.0),
            _trade(trade_id="c", pnl=3.0, pnl_pct=1.0),
        ]
        summary = compute_symbol_performance(trades)
        read = summary.reads[0]
        assert read.evidence_state == "sufficient_evidence"
        expected_avg = round((4.0 - 2.0 + 1.0) / 3, 2)
        assert read.avg_pnl_pct == expected_avg
        assert read.expectancy_pct == expected_avg

    def test_profit_factor_is_gross_profit_over_gross_loss(self) -> None:
        trades = [
            _trade(trade_id="a", pnl=30.0, pnl_pct=3.0),
            _trade(trade_id="b", pnl=20.0, pnl_pct=2.0),
            _trade(trade_id="c", pnl=-10.0, pnl_pct=-1.0),
        ]
        summary = compute_symbol_performance(trades)
        read = summary.reads[0]
        assert read.profit_factor == round(50.0 / 10.0, 2)

    def test_profit_factor_is_none_not_infinity_with_zero_losses(self) -> None:
        trades = [
            _trade(trade_id="a", pnl=10.0, pnl_pct=1.0),
            _trade(trade_id="b", pnl=20.0, pnl_pct=2.0),
            _trade(trade_id="c", pnl=5.0, pnl_pct=0.5),
        ]
        summary = compute_symbol_performance(trades)
        read = summary.reads[0]
        assert read.evidence_state == "sufficient_evidence"
        assert read.profit_factor is None

    def test_avg_mae_mfe_are_real_averages_over_the_symbols_own_trades(self) -> None:
        trades = [
            _trade(trade_id="a", pnl=10.0, pnl_pct=1.0, mae_pct=-2.0, mfe_pct=3.0),
            _trade(trade_id="b", pnl=-5.0, pnl_pct=-0.5, mae_pct=-4.0, mfe_pct=1.0),
        ]
        summary = compute_symbol_performance(trades)
        read = summary.reads[0]
        assert read.avg_mae_pct == round((-2.0 + -4.0) / 2, 2)
        assert read.avg_mfe_pct == round((3.0 + 1.0) / 2, 2)

    def test_best_and_worst_trade_pnl_pct_are_real_extremes(self) -> None:
        trades = [
            _trade(trade_id="a", pnl=10.0, pnl_pct=5.0),
            _trade(trade_id="b", pnl=-5.0, pnl_pct=-3.0),
            _trade(trade_id="c", pnl=1.0, pnl_pct=0.5),
        ]
        summary = compute_symbol_performance(trades)
        read = summary.reads[0]
        assert read.best_trade_pnl_pct == 5.0
        assert read.worst_trade_pnl_pct == -3.0


def _vault_entry(*, trade_id: str, session: str = "new_york", market_regime: str = "sideways_range", strategy_id: str | None = None) -> DecisionVaultEntry:
    return DecisionVaultEntry(
        id=f"vault-{trade_id}",
        tradeId=trade_id,
        decisionId=f"decision-{trade_id}",
        symbol="AAPL",
        simDay=1,
        session=session,  # type: ignore[arg-type]
        strategyId=strategy_id,
        marketRegime=market_regime,  # type: ignore[arg-type]
        marketRegimeLabel="test regime",
        liquidityContext=LiquidityRead(symbol="AAPL", zones=[], sweepDetected=False, sweepDirection="none", liquidityScore=50.0, detail="test"),
        evidenceScore=70.0,
        confidenceScore=70.0,
        confidenceTier="strong",  # type: ignore[arg-type]
        capitalAllocationGrade="B",  # type: ignore[arg-type]
        decisionGrade="B",  # type: ignore[arg-type]
        decisionGradeScore=80.0,
        disciplineTier="sound",  # type: ignore[arg-type]
        disciplineScore=75.0,
        patienceGrade="B",  # type: ignore[arg-type]
        positionSize=10.0,
        entryPrice=100.0,
        exitPrice=101.0,
        pnl=10.0,
        pnlPct=1.0,
        holdDurationMinutes=60,
        rMultiple=None,
        caseStudyId=None,
        caseStudyCategory=None,
        executiveNotes=None,
        lessonsLearned="test lesson",
        companyDnaChange=None,
        ceoOverride=False,
        createdAt="2024-01-01T00:00:00+00:00",
    )


class TestComputeSessionPerformance:
    """CEO directive "Next Phase: Professional Trading Firm Intelligence,"
    Phase 3 — joins the real Decision Vault for session context; a
    trade with no matching vault entry must be excluded and counted,
    never fabricated into a bucket."""

    def test_groups_by_session_via_the_real_vault_join(self) -> None:
        trades = [
            _trade(trade_id="a", pnl=10.0, pnl_pct=1.0),
            _trade(trade_id="b", pnl=5.0, pnl_pct=0.5),
        ]
        vault = [_vault_entry(trade_id="a", session="asian"), _vault_entry(trade_id="b", session="new_york")]
        summary = compute_session_performance(trades, vault)
        sessions = {r.session for r in summary.reads}
        assert sessions == {"asian", "new_york"}
        assert summary.trades_excluded_no_vault_entry == 0

    def test_a_trade_with_no_matching_vault_entry_is_excluded_and_counted(self) -> None:
        trades = [_trade(trade_id="a", pnl=10.0, pnl_pct=1.0), _trade(trade_id="orphan", pnl=5.0, pnl_pct=0.5)]
        vault = [_vault_entry(trade_id="a", session="asian")]
        summary = compute_session_performance(trades, vault)
        assert summary.trades_excluded_no_vault_entry == 1
        total_trades_in_reads = sum(r.trade_count for r in summary.reads)
        assert total_trades_in_reads == 1

    def test_empty_trade_history_produces_no_reads_and_no_exclusions(self) -> None:
        summary = compute_session_performance([], [])
        assert summary.reads == []
        assert summary.trades_excluded_no_vault_entry == 0

    def test_reads_sorted_by_total_pnl_descending(self) -> None:
        trades = [
            _trade(trade_id="a", pnl=-50.0, pnl_pct=-5.0),
            _trade(trade_id="b", pnl=100.0, pnl_pct=10.0),
        ]
        vault = [_vault_entry(trade_id="a", session="asian"), _vault_entry(trade_id="b", session="london")]
        summary = compute_session_performance(trades, vault)
        assert [r.session for r in summary.reads] == ["london", "asian"]


class TestComputeRegimePerformance:
    def test_groups_by_regime_via_the_real_vault_join(self) -> None:
        trades = [
            _trade(trade_id="a", pnl=10.0, pnl_pct=1.0),
            _trade(trade_id="b", pnl=5.0, pnl_pct=0.5),
        ]
        vault = [
            _vault_entry(trade_id="a", market_regime="strong_bull_trend"),
            _vault_entry(trade_id="b", market_regime="sideways_range"),
        ]
        summary = compute_regime_performance(trades, vault)
        regimes = {r.regime for r in summary.reads}
        assert regimes == {"strong_bull_trend", "sideways_range"}
        assert summary.trades_excluded_no_vault_entry == 0

    def test_a_trade_with_no_matching_vault_entry_is_excluded_and_counted(self) -> None:
        trades = [_trade(trade_id="a", pnl=10.0, pnl_pct=1.0), _trade(trade_id="orphan", pnl=5.0, pnl_pct=0.5)]
        vault = [_vault_entry(trade_id="a", market_regime="strong_bull_trend")]
        summary = compute_regime_performance(trades, vault)
        assert summary.trades_excluded_no_vault_entry == 1

    def test_below_min_sample_still_withholds_expectancy_and_profit_factor(self) -> None:
        trades = [_trade(trade_id="a", pnl=10.0, pnl_pct=1.0)]
        assert len(trades) < MIN_SYMBOL_SAMPLE_FOR_VERDICT
        vault = [_vault_entry(trade_id="a", market_regime="strong_bull_trend")]
        summary = compute_regime_performance(trades, vault)
        read = summary.reads[0]
        assert read.evidence_state == "not_enough_data"
        assert read.expectancy_pct is None
        assert read.profit_factor is None


class TestComputeStrategyPerformance:
    """CEO directive "Live Trade → Strategy Provenance," Phase 4 — the
    Strategy Exposure view. Only trades whose Decision Vault entry
    carries a real, CEO-selected strategy_id are grouped; every other
    trade is excluded under one of two distinct, honestly-separate
    reasons (see app/performance_attribution.py's own docstring)."""

    def test_groups_only_trades_with_a_real_ceo_selected_strategy_id(self) -> None:
        trades = [
            _trade(trade_id="a", pnl=10.0, pnl_pct=1.0),
            _trade(trade_id="b", pnl=5.0, pnl_pct=0.5),
        ]
        vault = [
            _vault_entry(trade_id="a", strategy_id="strategy-momentum"),
            _vault_entry(trade_id="b", strategy_id="strategy-value"),
        ]
        summary = compute_strategy_performance(trades, vault)
        strategy_ids = {r.strategy_id for r in summary.reads}
        assert strategy_ids == {"strategy-momentum", "strategy-value"}
        assert summary.trades_excluded_no_vault_entry == 0
        assert summary.trades_excluded_no_strategy_selected == 0

    def test_a_trade_with_a_vault_entry_but_no_strategy_selected_is_excluded_as_unknown(self) -> None:
        trades = [_trade(trade_id="a", pnl=10.0, pnl_pct=1.0)]
        vault = [_vault_entry(trade_id="a", strategy_id=None)]
        summary = compute_strategy_performance(trades, vault)
        assert summary.reads == []
        assert summary.trades_excluded_no_strategy_selected == 1
        assert summary.trades_excluded_no_vault_entry == 0

    def test_a_trade_with_no_matching_vault_entry_is_excluded_as_unavailable_not_unknown(self) -> None:
        trades = [_trade(trade_id="orphan", pnl=5.0, pnl_pct=0.5)]
        summary = compute_strategy_performance(trades, [])
        assert summary.reads == []
        assert summary.trades_excluded_no_vault_entry == 1
        assert summary.trades_excluded_no_strategy_selected == 0

    def test_the_two_exclusion_reasons_are_never_folded_together(self) -> None:
        trades = [
            _trade(trade_id="known", pnl=10.0, pnl_pct=1.0),
            _trade(trade_id="unknown", pnl=5.0, pnl_pct=0.5),
            _trade(trade_id="unavailable", pnl=-3.0, pnl_pct=-0.3),
        ]
        vault = [
            _vault_entry(trade_id="known", strategy_id="strategy-momentum"),
            _vault_entry(trade_id="unknown", strategy_id=None),
        ]
        summary = compute_strategy_performance(trades, vault)
        assert summary.trades_excluded_no_strategy_selected == 1
        assert summary.trades_excluded_no_vault_entry == 1
        assert sum(r.trade_count for r in summary.reads) == 1

    def test_empty_trade_history_produces_no_reads_and_no_exclusions(self) -> None:
        summary = compute_strategy_performance([], [])
        assert summary.reads == []
        assert summary.trades_excluded_no_strategy_selected == 0
        assert summary.trades_excluded_no_vault_entry == 0

    def test_reads_sorted_by_total_pnl_descending(self) -> None:
        trades = [
            _trade(trade_id="a", pnl=-50.0, pnl_pct=-5.0),
            _trade(trade_id="b", pnl=100.0, pnl_pct=10.0),
        ]
        vault = [
            _vault_entry(trade_id="a", strategy_id="strategy-loser"),
            _vault_entry(trade_id="b", strategy_id="strategy-winner"),
        ]
        summary = compute_strategy_performance(trades, vault)
        assert [r.strategy_id for r in summary.reads] == ["strategy-winner", "strategy-loser"]

    def test_below_min_sample_withholds_expectancy_and_profit_factor(self) -> None:
        trades = [_trade(trade_id="a", pnl=10.0, pnl_pct=1.0)]
        assert len(trades) < MIN_SYMBOL_SAMPLE_FOR_VERDICT
        vault = [_vault_entry(trade_id="a", strategy_id="strategy-momentum")]
        summary = compute_strategy_performance(trades, vault)
        read = summary.reads[0]
        assert read.evidence_state == "not_enough_data"
        assert read.expectancy_pct is None
        assert read.profit_factor is None


class TestComputeStrategySessionPerformance:
    """CEO directive "Live Trade → Strategy Provenance," Phase 6 — the
    real strategy×session axis. Same real Decision Vault join, grouped
    on the (strategy_id, session) pair."""

    def test_groups_by_the_strategy_session_pair(self) -> None:
        trades = [
            _trade(trade_id="a", pnl=10.0, pnl_pct=1.0),
            _trade(trade_id="b", pnl=5.0, pnl_pct=0.5),
            _trade(trade_id="c", pnl=-2.0, pnl_pct=-0.2),
        ]
        vault = [
            _vault_entry(trade_id="a", strategy_id="strategy-momentum", session="asian"),
            _vault_entry(trade_id="b", strategy_id="strategy-momentum", session="new_york"),
            _vault_entry(trade_id="c", strategy_id="strategy-value", session="asian"),
        ]
        summary = compute_strategy_session_performance(trades, vault)
        pairs = {(r.strategy_id, r.session) for r in summary.reads}
        assert pairs == {("strategy-momentum", "asian"), ("strategy-momentum", "new_york"), ("strategy-value", "asian")}
        momentum_asian = next(r for r in summary.reads if r.strategy_id == "strategy-momentum" and r.session == "asian")
        assert momentum_asian.trade_count == 1

    def test_a_trade_with_no_strategy_selected_is_excluded_as_unknown(self) -> None:
        trades = [_trade(trade_id="a", pnl=10.0, pnl_pct=1.0)]
        vault = [_vault_entry(trade_id="a", strategy_id=None, session="asian")]
        summary = compute_strategy_session_performance(trades, vault)
        assert summary.reads == []
        assert summary.trades_excluded_no_strategy_selected == 1
        assert summary.trades_excluded_no_vault_entry == 0

    def test_a_trade_with_no_matching_vault_entry_is_excluded_as_unavailable(self) -> None:
        trades = [_trade(trade_id="orphan", pnl=5.0, pnl_pct=0.5)]
        summary = compute_strategy_session_performance(trades, [])
        assert summary.reads == []
        assert summary.trades_excluded_no_vault_entry == 1

    def test_empty_trade_history_produces_no_reads_and_no_exclusions(self) -> None:
        summary = compute_strategy_session_performance([], [])
        assert summary.reads == []
        assert summary.trades_excluded_no_strategy_selected == 0
        assert summary.trades_excluded_no_vault_entry == 0

    def test_reads_sorted_by_total_pnl_descending(self) -> None:
        trades = [
            _trade(trade_id="a", pnl=-50.0, pnl_pct=-5.0),
            _trade(trade_id="b", pnl=100.0, pnl_pct=10.0),
        ]
        vault = [
            _vault_entry(trade_id="a", strategy_id="strategy-loser", session="asian"),
            _vault_entry(trade_id="b", strategy_id="strategy-winner", session="london"),
        ]
        summary = compute_strategy_session_performance(trades, vault)
        assert [(r.strategy_id, r.session) for r in summary.reads] == [("strategy-winner", "london"), ("strategy-loser", "asian")]


def _health(*, strategy_id: str, recent_win_rate: float, recent_sample_size: int = 5) -> StrategyHealthAssessment:
    return StrategyHealthAssessment(
        id=f"health-{strategy_id}",
        strategyId=strategy_id,
        strategyName="test strategy",
        status="stable",  # type: ignore[arg-type]
        trend="stable",  # type: ignore[arg-type]
        recentWinRate=recent_win_rate,
        lifetimeWinRate=recent_win_rate,
        recentAvgReturnPct=1.0,
        lifetimeAvgReturnPct=1.0,
        recentAvgDrawdownPct=5.0,
        lifetimeAvgDrawdownPct=5.0,
        recentSampleSize=recent_sample_size,
        lifetimeSampleSize=recent_sample_size,
        simDay=1,
        createdAt="2024-01-01T00:00:00+00:00",
    )


class TestComputeStrategyLiveVsBacktest:
    """CEO directive "Live Trade → Strategy Provenance," Phase 5 — real
    live-vs-backtest win-rate comparison, joining two already-real
    sources (compute_strategy_performance()'s own output and a real
    StrategyHealthAssessment list) — never recomputing either."""

    def _live(self, *, strategy_id: str, trade_count: int, win_rate_pct: float) -> object:
        # MIN_SYMBOL_SAMPLE_FOR_VERDICT-safe: build enough real trades,
        # with exactly the requested win rate, to drive compute_strategy_performance().
        wins = round(trade_count * win_rate_pct / 100)
        losses = trade_count - wins
        trades = [_trade(trade_id=f"{strategy_id}-w{i}", pnl=10.0, pnl_pct=1.0) for i in range(wins)]
        trades += [_trade(trade_id=f"{strategy_id}-l{i}", pnl=-5.0, pnl_pct=-0.5) for i in range(losses)]
        vault = [_vault_entry(trade_id=t.id, strategy_id=strategy_id) for t in trades]
        return compute_strategy_performance(trades, vault)

    def test_no_health_assessment_on_record_reads_that_verdict(self) -> None:
        live = self._live(strategy_id="strategy-momentum", trade_count=5, win_rate_pct=60.0)
        summary = compute_strategy_live_vs_backtest(live, [])
        read = summary.reads[0]
        assert read.verdict == "no_backtest_health_on_record"
        assert read.backtest_recent_win_rate_pct is None
        assert read.win_rate_delta_pct is None

    def test_below_min_live_sample_reads_not_enough_live_data(self) -> None:
        live = self._live(strategy_id="strategy-momentum", trade_count=1, win_rate_pct=100.0)
        assert live.reads[0].trade_count < MIN_SYMBOL_SAMPLE_FOR_VERDICT
        health = [_health(strategy_id="strategy-momentum", recent_win_rate=55.0)]
        summary = compute_strategy_live_vs_backtest(live, health)
        read = summary.reads[0]
        assert read.verdict == "not_enough_live_data"
        # Real backtest numbers still show even though no verdict is drawn.
        assert read.backtest_recent_win_rate_pct == 55.0

    def test_a_small_win_rate_gap_reads_consistent_with_backtest(self) -> None:
        live = self._live(strategy_id="strategy-momentum", trade_count=5, win_rate_pct=60.0)
        health = [_health(strategy_id="strategy-momentum", recent_win_rate=60.0 + WIN_RATE_DIVERGENCE_THRESHOLD_PCT - 1)]
        summary = compute_strategy_live_vs_backtest(live, health)
        read = summary.reads[0]
        assert read.verdict == "consistent_with_backtest"

    def test_a_wide_win_rate_gap_reads_diverging_from_backtest(self) -> None:
        live = self._live(strategy_id="strategy-momentum", trade_count=5, win_rate_pct=60.0)
        health = [_health(strategy_id="strategy-momentum", recent_win_rate=60.0 + WIN_RATE_DIVERGENCE_THRESHOLD_PCT + 1)]
        summary = compute_strategy_live_vs_backtest(live, health)
        read = summary.reads[0]
        assert read.verdict == "diverging_from_backtest"
        assert read.win_rate_delta_pct is not None
        assert read.win_rate_delta_pct < 0

    def test_the_latest_health_assessment_per_strategy_wins(self) -> None:
        live = self._live(strategy_id="strategy-momentum", trade_count=5, win_rate_pct=60.0)
        health = [
            _health(strategy_id="strategy-momentum", recent_win_rate=10.0),  # stale, chronologically first
            _health(strategy_id="strategy-momentum", recent_win_rate=60.0),  # latest — should win
        ]
        summary = compute_strategy_live_vs_backtest(live, health)
        read = summary.reads[0]
        assert read.backtest_recent_win_rate_pct == 60.0
        assert read.verdict == "consistent_with_backtest"

    def test_empty_live_performance_produces_no_reads(self) -> None:
        from app.schemas import StrategyPerformanceSummary

        summary = compute_strategy_live_vs_backtest(StrategyPerformanceSummary(reads=[], tradesExcludedNoStrategySelected=0, tradesExcludedNoVaultEntry=0, updatedAt="2024-01-01T00:00:00+00:00"), [])
        assert summary.reads == []


_EMPTY_SESSIONS = StrategySessionPerformanceSummary(reads=[], tradesExcludedNoStrategySelected=0, tradesExcludedNoVaultEntry=0, updatedAt="2024-01-01T00:00:00+00:00")


class TestComputeStrategyCapitalAllocationEvidence:
    """CEO directive "Portfolio Construction, Capital Allocation &
    Execution Realism," Phase 5 — an informational evidence roster,
    never a system-generated ranking. Joins only already-real,
    already-computed sources plus the two genuinely new real reads
    (live drawdown, live return volatility) this phase adds."""

    def test_empty_roster_produces_no_reads(self) -> None:
        summary = compute_strategy_capital_allocation_evidence([], [], [], _EMPTY_SESSIONS, [])
        assert summary.reads == []
        assert summary.min_sample_for_evidence == MIN_SYMBOL_SAMPLE_FOR_VERDICT

    def test_a_strategy_with_zero_live_trades_gets_a_row_with_every_derived_metric_none(self) -> None:
        strategy = _strategy(strategy_id="strategy-1", allocated_capital=5000.0)
        summary = compute_strategy_capital_allocation_evidence([strategy], [], [], _EMPTY_SESSIONS, [])
        read = summary.reads[0]
        assert read.evidence_state == "no_live_trades_yet"
        assert read.trade_count == 0
        assert read.allocated_capital == 5000.0
        assert read.win_rate_pct is None
        assert read.expectancy_pct is None
        assert read.profit_factor is None
        assert read.live_drawdown_usd is None
        assert read.live_return_volatility_pct is None
        assert read.avg_entry_slippage_bps is None
        assert read.robustness_note == ROBUSTNESS_UNAVAILABLE_NOTE

    def test_below_min_sample_withholds_drawdown_and_volatility_but_keeps_win_rate(self) -> None:
        strategy = _strategy(strategy_id="strategy-1")
        trades = [_trade(trade_id="a", pnl=10.0, pnl_pct=1.0)]
        vault = [_vault_entry(trade_id="a", strategy_id="strategy-1")]
        summary = compute_strategy_capital_allocation_evidence([strategy], trades, vault, _EMPTY_SESSIONS, [])
        read = summary.reads[0]
        assert read.evidence_state == "not_enough_data"
        assert read.trade_count == 1
        assert read.win_rate_pct == 100.0
        assert read.expectancy_pct is None  # same MIN_SYMBOL_SAMPLE_FOR_VERDICT gate as _group_metrics()
        assert read.live_drawdown_usd is None
        assert read.live_return_volatility_pct is None

    def test_real_peak_to_trough_drawdown_computed_in_chronological_order_not_insertion_order(self) -> None:
        strategy = _strategy(strategy_id="strategy-1")
        # Deliberately inserted out of chronological order — closed_at
        # ordering must still win: +100 (day1) -> -40 (day2, peak 100 ->
        # trough 60, drawdown 40) -> +10 (day3, still below the day1 peak).
        trades = [
            _trade(trade_id="c", pnl=10.0, pnl_pct=1.0, closed_at="2024-01-03T00:00:00+00:00"),
            _trade(trade_id="a", pnl=100.0, pnl_pct=10.0, closed_at="2024-01-01T00:00:00+00:00"),
            _trade(trade_id="b", pnl=-40.0, pnl_pct=-4.0, closed_at="2024-01-02T00:00:00+00:00"),
        ]
        vault = [_vault_entry(trade_id=t.id, strategy_id="strategy-1") for t in trades]
        summary = compute_strategy_capital_allocation_evidence([strategy], trades, vault, _EMPTY_SESSIONS, [])
        read = summary.reads[0]
        assert read.live_drawdown_usd == 40.0

    def test_real_return_volatility_matches_population_stdev_of_pnl_pct(self) -> None:
        strategy = _strategy(strategy_id="strategy-1")
        trades = [
            _trade(trade_id="a", pnl=40.0, pnl_pct=4.0, closed_at="2024-01-01T00:00:00+00:00"),
            _trade(trade_id="b", pnl=-20.0, pnl_pct=-2.0, closed_at="2024-01-02T00:00:00+00:00"),
            _trade(trade_id="c", pnl=10.0, pnl_pct=1.0, closed_at="2024-01-03T00:00:00+00:00"),
        ]
        vault = [_vault_entry(trade_id=t.id, strategy_id="strategy-1") for t in trades]
        summary = compute_strategy_capital_allocation_evidence([strategy], trades, vault, _EMPTY_SESSIONS, [])
        read = summary.reads[0]
        # mean=1.0, population variance=((4-1)^2+(-2-1)^2+(1-1)^2)/3=6.0, stdev=sqrt(6)~=2.449...
        assert read.live_return_volatility_pct == 2.45

    def test_avg_entry_and_exit_slippage_bps_aggregated_per_strategy(self) -> None:
        strategy = _strategy(strategy_id="strategy-1")
        trades = [
            _trade(trade_id="a", pnl=1.0, pnl_pct=0.1, entry_slippage_bps=10.0, exit_slippage_bps=5.0),
            _trade(trade_id="b", pnl=1.0, pnl_pct=0.1, entry_slippage_bps=20.0, exit_slippage_bps=15.0),
            _trade(trade_id="c", pnl=1.0, pnl_pct=0.1, entry_slippage_bps=30.0, exit_slippage_bps=25.0),
        ]
        vault = [_vault_entry(trade_id=t.id, strategy_id="strategy-1") for t in trades]
        summary = compute_strategy_capital_allocation_evidence([strategy], trades, vault, _EMPTY_SESSIONS, [])
        read = summary.reads[0]
        assert read.avg_entry_slippage_bps == 20.0
        assert read.avg_exit_slippage_bps == 15.0

    def test_a_strategy_never_traded_by_another_strategys_trades_stays_at_zero_exposure(self) -> None:
        strategy_a = _strategy(strategy_id="strategy-a")
        strategy_b = _strategy(strategy_id="strategy-b", name="Other")
        trades = [_trade(trade_id="x", pnl=10.0, pnl_pct=1.0)]
        vault = [_vault_entry(trade_id="x", strategy_id="strategy-a")]
        summary = compute_strategy_capital_allocation_evidence([strategy_a, strategy_b], trades, vault, _EMPTY_SESSIONS, [])
        b_read = next(r for r in summary.reads if r.strategy_id == "strategy-b")
        assert b_read.evidence_state == "no_live_trades_yet"
        assert b_read.current_exposure_value == 0.0

    def test_current_exposure_joined_from_strategy_exposure_reads(self) -> None:
        strategy = _strategy(strategy_id="strategy-1")
        exposure = [StrategyExposureRead(strategyId="strategy-1", positionCount=2, value=1500.0, pctOfEquity=15.0, longValue=1500.0, shortValue=0.0)]
        summary = compute_strategy_capital_allocation_evidence([strategy], [], [], _EMPTY_SESSIONS, exposure)
        read = summary.reads[0]
        assert read.current_exposure_value == 1500.0
        assert read.current_exposure_pct_of_equity == 15.0
        assert "1,500" in read.correlation_note
        assert "return-correlation-between-strategies" in read.correlation_note

    def test_reads_sorted_by_allocated_capital_descending_never_by_a_performance_metric(self) -> None:
        strategies = [
            _strategy(strategy_id="low-capital-high-winrate", allocated_capital=100.0),
            _strategy(strategy_id="high-capital-no-trades", allocated_capital=9000.0),
        ]
        trades = [_trade(trade_id="a", pnl=10.0, pnl_pct=1.0)] * 5
        # give the low-capital strategy a perfect win rate — sort order must still be by capital, not this.
        vault = [_vault_entry(trade_id=t.id, strategy_id="low-capital-high-winrate") for t in trades]
        summary = compute_strategy_capital_allocation_evidence(strategies, trades, vault, _EMPTY_SESSIONS, [])
        assert [r.strategy_id for r in summary.reads] == ["high-capital-no-trades", "low-capital-high-winrate"]

    def test_session_reads_filtered_to_only_this_strategys_own_rows(self) -> None:
        from app.schemas import StrategySessionPerformanceRead

        strategy = _strategy(strategy_id="strategy-1")
        sessions = StrategySessionPerformanceSummary(
            reads=[
                StrategySessionPerformanceRead(
                    strategyId="strategy-1", session="new_york", tradeCount=3, winCount=2, lossCount=1, winRatePct=66.7,
                    totalPnl=10.0, avgPnlPct=1.0, avgWinnerPct=5.0, avgLoserPct=-2.0, expectancyPct=1.0, profitFactor=2.0,
                    avgMaePct=0.0, avgMfePct=0.0, bestTradePnlPct=5.0, worstTradePnlPct=-2.0, evidenceState="sufficient_evidence",
                ),
                StrategySessionPerformanceRead(
                    strategyId="strategy-other", session="london", tradeCount=3, winCount=2, lossCount=1, winRatePct=66.7,
                    totalPnl=10.0, avgPnlPct=1.0, avgWinnerPct=5.0, avgLoserPct=-2.0, expectancyPct=1.0, profitFactor=2.0,
                    avgMaePct=0.0, avgMfePct=0.0, bestTradePnlPct=5.0, worstTradePnlPct=-2.0, evidenceState="sufficient_evidence",
                ),
            ],
            tradesExcludedNoStrategySelected=0,
            tradesExcludedNoVaultEntry=0,
            updatedAt="2024-01-01T00:00:00+00:00",
        )
        summary = compute_strategy_capital_allocation_evidence([strategy], [], [], sessions, [])
        read = summary.reads[0]
        assert len(read.session_reads) == 1
        assert read.session_reads[0].session == "new_york"


def _failure_classification(*, trade_id: str, reason: str = "bad_thesis") -> FailureClassification:
    return FailureClassification(
        id=f"fc-{trade_id}",
        tradeId=trade_id,
        decisionId=f"decision-{trade_id}",
        symbol="AAPL",
        reason=reason,  # type: ignore[arg-type]
        evidence="test",
        attributedAgents=["scout"],  # type: ignore[list-item]
        tradePnlPct=-1.0,
        simDay=1,
        createdAt="2024-01-01T00:00:00+00:00",
    )


class TestComputeStrategyDegradation:
    """CEO directive "Portfolio Construction, Capital Allocation &
    Execution Realism," Phase 6 — normal variation vs. a real,
    evidence-backed degradation warning. Every scenario below is
    constructed so exactly one real trigger condition fires (except
    where noted), proving each signal independently."""

    def test_empty_roster_produces_no_reads(self) -> None:
        summary = compute_strategy_degradation([], [], [], [])
        assert summary.reads == []
        assert summary.recent_window_size == HEALTH_RECENT_WINDOW
        assert summary.min_sample_for_verdict == MIN_SYMBOL_SAMPLE_FOR_VERDICT

    def test_below_min_sample_reads_not_enough_data(self) -> None:
        strategy = _strategy(strategy_id="s1")
        trades = [_trade(trade_id="a", pnl=10.0, pnl_pct=1.0)]
        vault = [_vault_entry(trade_id="a", strategy_id="s1")]
        summary = compute_strategy_degradation([strategy], trades, vault, [])
        read = summary.reads[0]
        assert read.level == "not_enough_data"
        assert read.signals == []

    def test_consistent_wins_read_normal_variation(self) -> None:
        strategy = _strategy(strategy_id="s1")
        trades = [_trade(trade_id=f"t{i}", pnl=10.0, pnl_pct=1.0, closed_at=f"2024-01-0{i+1}T00:00:00+00:00") for i in range(3)]
        vault = [_vault_entry(trade_id=t.id, strategy_id="s1") for t in trades]
        summary = compute_strategy_degradation([strategy], trades, vault, [])
        read = summary.reads[0]
        assert read.level == "normal_variation"
        assert read.signals == []

    def test_four_consecutive_losses_reads_critical_loss_clustering(self) -> None:
        strategy = _strategy(strategy_id="s1")
        trades = [_trade(trade_id=f"t{i}", pnl=-1.0, pnl_pct=-1.0, closed_at=f"2024-01-0{i+1}T00:00:00+00:00") for i in range(CRITICAL_LOSS_STREAK)]
        vault = [_vault_entry(trade_id=t.id, strategy_id="s1") for t in trades]
        summary = compute_strategy_degradation([strategy], trades, vault, [])
        read = summary.reads[0]
        assert read.level == "critical_degradation"
        assert read.consecutive_losses == CRITICAL_LOSS_STREAK
        assert any(s.startswith("Loss clustering") for s in read.signals)

    def test_three_consecutive_losses_reads_possible_loss_clustering(self) -> None:
        strategy = _strategy(strategy_id="s1")
        trades = [_trade(trade_id=f"t{i}", pnl=-1.0, pnl_pct=-1.0, closed_at=f"2024-01-0{i+1}T00:00:00+00:00") for i in range(POSSIBLE_LOSS_STREAK)]
        vault = [_vault_entry(trade_id=t.id, strategy_id="s1") for t in trades]
        summary = compute_strategy_degradation([strategy], trades, vault, [])
        read = summary.reads[0]
        assert read.level == "possible_degradation"
        assert read.consecutive_losses == POSSIBLE_LOSS_STREAK
        assert any(s.startswith("Loss clustering") for s in read.signals)

    def test_a_win_breaking_the_streak_resets_the_consecutive_loss_count(self) -> None:
        strategy = _strategy(strategy_id="s1")
        trades = [
            _trade(trade_id="loss1", pnl=-1.0, pnl_pct=-1.0, closed_at="2024-01-01T00:00:00+00:00"),
            _trade(trade_id="win", pnl=10.0, pnl_pct=1.0, closed_at="2024-01-02T00:00:00+00:00"),
            _trade(trade_id="loss2", pnl=-1.0, pnl_pct=-1.0, closed_at="2024-01-03T00:00:00+00:00"),
        ]
        vault = [_vault_entry(trade_id=t.id, strategy_id="s1") for t in trades]
        summary = compute_strategy_degradation([strategy], trades, vault, [])
        read = summary.reads[0]
        # Only the trailing loss counts — the win in the middle breaks the streak.
        assert read.consecutive_losses == 1

    def test_expectancy_sign_flip_reads_critical(self) -> None:
        strategy = _strategy(strategy_id="s1")
        old_wins = [_trade(trade_id=f"old{i}", pnl=20.0, pnl_pct=20.0, closed_at=f"2024-01-0{i+1}T00:00:00+00:00") for i in range(3)]
        recent_losses = [_trade(trade_id=f"recent{i}", pnl=-1.0, pnl_pct=-1.0, closed_at=f"2024-01-0{i+4}T00:00:00+00:00") for i in range(3)]
        trades = old_wins + recent_losses
        vault = [_vault_entry(trade_id=t.id, strategy_id="s1") for t in trades]
        summary = compute_strategy_degradation([strategy], trades, vault, [])
        read = summary.reads[0]
        assert read.level == "critical_degradation"
        assert read.recent_expectancy_pct is not None and read.recent_expectancy_pct < 0
        assert read.lifetime_expectancy_pct is not None and read.lifetime_expectancy_pct >= 0
        assert any(s.startswith("Expectancy deterioration") and "flipped negative" in s for s in read.signals)

    def test_expectancy_drop_without_sign_flip_reads_possible(self) -> None:
        strategy = _strategy(strategy_id="s1")
        old_wins = [_trade(trade_id=f"old{i}", pnl=20.0, pnl_pct=20.0, closed_at=f"2024-01-0{i+1}T00:00:00+00:00") for i in range(3)]
        recent_small_wins = [_trade(trade_id=f"recent{i}", pnl=10.0, pnl_pct=1.0, closed_at=f"2024-01-0{i+4}T00:00:00+00:00") for i in range(3)]
        trades = old_wins + recent_small_wins
        vault = [_vault_entry(trade_id=t.id, strategy_id="s1") for t in trades]
        summary = compute_strategy_degradation([strategy], trades, vault, [])
        read = summary.reads[0]
        assert read.level == "possible_degradation"
        assert read.recent_expectancy_pct is not None and read.recent_expectancy_pct >= 0
        assert any(s.startswith("Expectancy deterioration") and "flipped negative" not in s for s in read.signals)

    def test_a_sudden_volatility_spike_reads_possible(self) -> None:
        strategy = _strategy(strategy_id="s1")
        calm = [_trade(trade_id=f"calm{i}", pnl=10.0, pnl_pct=1.0, closed_at=f"2024-01-{i+1:02d}T00:00:00+00:00") for i in range(10)]
        wild = [
            _trade(trade_id="wild0", pnl=10.0, pnl_pct=1.0, closed_at="2024-01-11T00:00:00+00:00"),
            _trade(trade_id="wild1", pnl=100.0, pnl_pct=10.0, closed_at="2024-01-12T00:00:00+00:00"),
            _trade(trade_id="wild2", pnl=-80.0, pnl_pct=-8.0, closed_at="2024-01-13T00:00:00+00:00"),
        ]
        trades = calm + wild
        vault = [_vault_entry(trade_id=t.id, strategy_id="s1") for t in trades]
        summary = compute_strategy_degradation([strategy], trades, vault, [])
        read = summary.reads[0]
        assert read.recent_return_volatility_pct is not None and read.lifetime_return_volatility_pct is not None
        assert read.recent_return_volatility_pct > read.lifetime_return_volatility_pct
        assert any(s.startswith("Volatility regime change") for s in read.signals)

    def test_execution_degradation_reads_possible(self) -> None:
        strategy = _strategy(strategy_id="s1")
        old = [_trade(trade_id=f"old{i}", pnl=10.0, pnl_pct=1.0, entry_slippage_bps=1.0, closed_at=f"2024-01-0{i+1}T00:00:00+00:00") for i in range(2)]
        recent = [_trade(trade_id=f"recent{i}", pnl=10.0, pnl_pct=1.0, entry_slippage_bps=40.0, closed_at=f"2024-01-0{i+3}T00:00:00+00:00") for i in range(3)]
        trades = old + recent
        vault = [_vault_entry(trade_id=t.id, strategy_id="s1") for t in trades]
        summary = compute_strategy_degradation([strategy], trades, vault, [])
        read = summary.reads[0]
        assert read.level == "possible_degradation"
        assert read.recent_avg_slippage_bps == 40.0
        assert any(s.startswith("Execution degradation") for s in read.signals)

    def test_a_moderate_recent_drawdown_reads_possible(self) -> None:
        strategy = _strategy(strategy_id="s1")
        trades = [
            _trade(trade_id="small_loss", pnl=-2.0, pnl_pct=-0.2, closed_at="2024-01-01T00:00:00+00:00"),
            _trade(trade_id="win", pnl=50.0, pnl_pct=5.0, closed_at="2024-01-02T00:00:00+00:00"),
            _trade(trade_id="big_loss1", pnl=-20.0, pnl_pct=-2.0, closed_at="2024-01-03T00:00:00+00:00"),
            _trade(trade_id="big_loss2", pnl=-20.0, pnl_pct=-2.0, closed_at="2024-01-04T00:00:00+00:00"),
            _trade(trade_id="big_loss3", pnl=-20.0, pnl_pct=-2.0, closed_at="2024-01-05T00:00:00+00:00"),
        ]
        vault = [_vault_entry(trade_id=t.id, strategy_id="s1") for t in trades]
        summary = compute_strategy_degradation([strategy], trades, vault, [])
        read = summary.reads[0]
        assert read.level in ("possible_degradation", "critical_degradation")
        assert any(s.startswith("Abnormal drawdown") for s in read.signals)

    def test_a_severe_recent_drawdown_reads_critical(self) -> None:
        strategy = _strategy(strategy_id="s1")
        tiny_losses = [_trade(trade_id=f"tiny{i}", pnl=-1.0, pnl_pct=-0.1, closed_at=f"2024-01-{i+1:02d}T00:00:00+00:00") for i in range(10)]
        big_losses = [
            _trade(trade_id="big0", pnl=-50.0, pnl_pct=-5.0, closed_at="2024-01-11T00:00:00+00:00"),
            _trade(trade_id="big1", pnl=-50.0, pnl_pct=-5.0, closed_at="2024-01-12T00:00:00+00:00"),
            _trade(trade_id="big2", pnl=-50.0, pnl_pct=-5.0, closed_at="2024-01-13T00:00:00+00:00"),
        ]
        trades = tiny_losses + big_losses
        vault = [_vault_entry(trade_id=t.id, strategy_id="s1") for t in trades]
        summary = compute_strategy_degradation([strategy], trades, vault, [])
        read = summary.reads[0]
        assert read.level == "critical_degradation"
        assert any(s.startswith("Abnormal drawdown") for s in read.signals)

    def test_repeated_invalidations_reads_critical(self) -> None:
        strategy = _strategy(strategy_id="s1")
        trades = [_trade(trade_id=f"t{i}", pnl=-1.0, pnl_pct=-1.0, closed_at=f"2024-01-0{i+1}T00:00:00+00:00") for i in range(3)]
        vault = [_vault_entry(trade_id=t.id, strategy_id="s1") for t in trades]
        failures = [_failure_classification(trade_id="t0"), _failure_classification(trade_id="t1")]
        summary = compute_strategy_degradation([strategy], trades, vault, failures)
        read = summary.reads[0]
        assert read.recent_invalidation_count == REPEATED_INVALIDATION_THRESHOLD
        assert read.level == "critical_degradation"
        assert any(s.startswith("Repeated invalidations") for s in read.signals)

    def test_a_single_invalidation_below_threshold_does_not_trigger(self) -> None:
        strategy = _strategy(strategy_id="s1")
        trades = [_trade(trade_id=f"t{i}", pnl=10.0, pnl_pct=1.0, closed_at=f"2024-01-0{i+1}T00:00:00+00:00") for i in range(3)]
        vault = [_vault_entry(trade_id=t.id, strategy_id="s1") for t in trades]
        failures = [_failure_classification(trade_id="t0")]
        summary = compute_strategy_degradation([strategy], trades, vault, failures)
        read = summary.reads[0]
        assert read.recent_invalidation_count == 1
        assert not any(s.startswith("Repeated invalidations") for s in read.signals)

    def test_a_failure_classification_with_a_different_reason_is_not_counted_as_an_invalidation(self) -> None:
        strategy = _strategy(strategy_id="s1")
        trades = [_trade(trade_id=f"t{i}", pnl=-1.0, pnl_pct=-1.0, closed_at=f"2024-01-0{i+1}T00:00:00+00:00") for i in range(3)]
        vault = [_vault_entry(trade_id=t.id, strategy_id="s1") for t in trades]
        failures = [_failure_classification(trade_id="t0", reason="poor_execution"), _failure_classification(trade_id="t1", reason="process_violation")]
        summary = compute_strategy_degradation([strategy], trades, vault, failures)
        read = summary.reads[0]
        assert read.recent_invalidation_count == 0
