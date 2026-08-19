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
    MIN_SYMBOL_SAMPLE_FOR_VERDICT,
    compute_regime_performance,
    compute_session_performance,
    compute_symbol_performance,
)
from app.schemas import DecisionVaultEntry, LiquidityRead, PaperTrade


def _trade(*, trade_id: str, symbol: str = "AAPL", pnl: float, pnl_pct: float, mae_pct: float = 0.0, mfe_pct: float = 0.0) -> PaperTrade:
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
        closedAt="2024-01-01T00:00:00+00:00",
        openedSimMinutes=0,
        closedSimMinutes=30,
        maePct=mae_pct,
        mfePct=mfe_pct,
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


def _vault_entry(*, trade_id: str, session: str = "new_york", market_regime: str = "sideways_range") -> DecisionVaultEntry:
    return DecisionVaultEntry(
        id=f"vault-{trade_id}",
        tradeId=trade_id,
        decisionId=f"decision-{trade_id}",
        symbol="AAPL",
        simDay=1,
        session=session,  # type: ignore[arg-type]
        strategyId=None,
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
