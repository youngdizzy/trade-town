"""Covers app/portfolio_analyst.py — CEO directive "TradeTown — Phase
10: Real Data + True Holdout + Portfolio Intelligence," Sections C/D.
Hand-built `EmaPullbackTradeRecord` fixtures (same real, valid-field
convention tests/test_adversarial_research.py already established) give
exact control over correlation/overlap/redundancy scenarios."""
from __future__ import annotations

import inspect
from typing import Literal

from app.portfolio_analyst import MIN_PAIRED_DAYS_FOR_CORRELATION, analyze_portfolio, compute_pair_correlation
from app.schemas import EmaPullbackTradeRecord


def _trade(*, index: int, r: float, day_offset: int = 0, symbol: str = "AAPL", direction: Literal["long", "short"] = "long") -> EmaPullbackTradeRecord:
    outcome: Literal["win", "loss"] = "win" if r >= 0 else "loss"
    return EmaPullbackTradeRecord(
        symbol=symbol,
        direction=direction,
        entryTimestamp=f"2024-{1 + day_offset // 28:02d}-{1 + day_offset % 28:02d}T10:00:00+00:00",
        entryPrice=100.0,
        stopPrice=95.0,
        targetPrice=110.0,
        exitPrice=100.0 + r * 5,
        outcome=outcome,
        rMultipleRealized=r,
        entrySession="new_york",
        regimeTrend="trending_up",
        regimeVolatility="normal",
        breakoutCandleExtended=False,
        breakoutCandleRangeRatio=1.0,
        maeR=min(0.0, r),
        mfeR=max(0.0, r),
        barsHeld=10,
    )


def _identical_trades(n: int) -> list[EmaPullbackTradeRecord]:
    return [_trade(index=i, r=1.0 if i % 3 != 0 else -1.0, day_offset=i) for i in range(n)]


def _inverse_trades(n: int) -> list[EmaPullbackTradeRecord]:
    return [_trade(index=i, r=-1.0 if i % 3 != 0 else 1.0, day_offset=i) for i in range(n)]


class TestComputePairCorrelation:
    def test_below_evidence_floor_is_none(self) -> None:
        a = [_trade(index=0, r=1.0, day_offset=0)]
        b = [_trade(index=0, r=1.0, day_offset=0)]
        result = compute_pair_correlation("a", a, "b", b)
        assert result.correlation is None
        assert result.stress_correlation is None

    def test_identical_daily_returns_are_perfectly_correlated(self) -> None:
        a = _identical_trades(30)
        b = _identical_trades(30)
        result = compute_pair_correlation("a", a, "b", b)
        assert result.correlation is not None
        assert result.correlation > 0.99

    def test_inverse_daily_returns_are_negatively_correlated(self) -> None:
        a = _identical_trades(30)
        b = _inverse_trades(30)
        result = compute_pair_correlation("a", a, "b", b)
        assert result.correlation is not None
        assert result.correlation < -0.5

    def test_paired_day_count_only_counts_shared_days(self) -> None:
        a = [_trade(index=i, r=1.0, day_offset=i) for i in range(20)]
        b = [_trade(index=i, r=1.0, day_offset=i + 10) for i in range(20)]  # only days 10-19 overlap
        result = compute_pair_correlation("a", a, "b", b)
        assert result.paired_day_count == 10


class TestAnalyzePortfolio:
    def test_insufficient_evidence_below_trade_floor(self) -> None:
        candidate_trades = {"a": [_trade(index=0, r=1.0, day_offset=0)], "b": [_trade(index=0, r=1.0, day_offset=0)]}
        report = analyze_portfolio(candidate_trades, candidate_failure_codes={}, report_id="r1")
        assert report.recommendation == "insufficient_evidence"

    def test_highly_correlated_identical_strategies_are_high_redundancy(self) -> None:
        candidate_trades = {"a": _identical_trades(80), "b": _identical_trades(80)}
        report = analyze_portfolio(candidate_trades, candidate_failure_codes={}, report_id="r2")
        assert report.recommendation == "high_redundancy"

    def test_anti_correlated_strategies_are_diversifying_or_robust(self) -> None:
        candidate_trades = {"a": _identical_trades(80), "b": _inverse_trades(80)}
        report = analyze_portfolio(candidate_trades, candidate_failure_codes={}, report_id="r3")
        assert report.recommendation in ("diversifying", "portfolio_robust")

    def test_combined_bucket_uses_real_aggregate_bucket_over_all_trades(self) -> None:
        candidate_trades = {"a": _identical_trades(40), "b": _inverse_trades(40)}
        report = analyze_portfolio(candidate_trades, candidate_failure_codes={}, report_id="r4")
        assert report.combined_bucket.trade_count == 80

    def test_shared_failure_modes_is_a_real_intersection(self) -> None:
        candidate_trades = {"a": _identical_trades(80), "b": _identical_trades(80)}
        codes = {"a": ["excessive_drawdown", "cost_sensitivity"], "b": ["excessive_drawdown", "outlier_dependent"]}
        report = analyze_portfolio(candidate_trades, candidate_failure_codes=codes, report_id="r5")  # type: ignore[arg-type]
        assert report.shared_failure_modes == ["excessive_drawdown"]

    def test_marginal_contributions_cover_every_candidate(self) -> None:
        candidate_trades = {"a": _identical_trades(40), "b": _inverse_trades(40)}
        report = analyze_portfolio(candidate_trades, candidate_failure_codes={}, report_id="r6")
        assert {mc.candidate_id for mc in report.marginal_contributions} == {"a", "b"}

    def test_single_candidate_produces_no_pair_correlations(self) -> None:
        candidate_trades = {"a": _identical_trades(80)}
        report = analyze_portfolio(candidate_trades, candidate_failure_codes={}, report_id="r7")
        assert report.pair_correlations == []
        assert report.recommendation == "insufficient_evidence"

    def test_min_paired_days_constant_is_real_and_positive(self) -> None:
        assert MIN_PAIRED_DAYS_FOR_CORRELATION > 0


class TestNeverAPromotionAuthority:
    """Section C/J — proven by real module-source inspection, matching
    this codebase's own established Champion/Challenger/Council-boundary
    discipline."""

    def test_champion_challenger_never_imports_portfolio_analyst(self) -> None:
        import app.champion_challenger as champion_challenger_module

        source = inspect.getsource(champion_challenger_module)
        assert "portfolio_analyst" not in source

    def test_strategy_lab_never_imports_portfolio_analyst(self) -> None:
        import app.strategy_lab as strategy_lab_module

        source = inspect.getsource(strategy_lab_module)
        assert "portfolio_analyst" not in source

    def test_research_loop_never_imports_portfolio_analyst(self) -> None:
        import app.research_loop as research_loop_module

        source = inspect.getsource(research_loop_module)
        assert "portfolio_analyst" not in source
