"""Covers app/exit_efficiency.py — CEO directive "Professional Trading
Firm Transformation," Post-Trade Review, Exit Efficiency. A trade whose
mae/mfe watermark was never really tracked (both default to 0.0) must
read NOT_ENOUGH_DATA, never a fabricated 50%; the capture-percent
formula must honestly cover wins and losses alike from the trade's own
real observed range, never a hardcoded win/loss branch.
"""
from __future__ import annotations

from app.exit_efficiency import compute_exit_efficiency
from app.schemas import PaperTrade


def _trade(*, trade_id: str = "t1", pnl_pct: float, mae_pct: float, mfe_pct: float, closed_sim_minutes: int = 1450) -> PaperTrade:
    return PaperTrade(
        id=trade_id,
        symbol="AAPL",
        side="buy",
        quantity=1.0,
        entryPrice=100.0,
        exitPrice=100.0 + pnl_pct,
        pnl=pnl_pct,
        pnlPct=pnl_pct,
        durationMinutes=30,
        confidence=80.0,
        reason="test",
        marketConditions="test",
        supportingAgents=["scout"],
        opposingAgents=[],
        openedAt="2024-01-01T00:00:00+00:00",
        closedAt="2024-01-01T00:00:00+00:00",
        openedSimMinutes=closed_sim_minutes - 30,
        closedSimMinutes=closed_sim_minutes,
        maePct=mae_pct,
        mfePct=mfe_pct,
    )


class TestComputeExitEfficiency:
    def test_empty_trade_history_produces_no_reads(self) -> None:
        summary = compute_exit_efficiency([])
        assert summary.reads == []
        assert summary.avg_capture_pct is None

    def test_untracked_watermark_reads_not_enough_data(self) -> None:
        trade = _trade(pnl_pct=1.5, mae_pct=0.0, mfe_pct=0.0)
        summary = compute_exit_efficiency([trade])
        assert summary.reads[0].capture_pct is None
        assert summary.reads[0].state == "not_enough_data"
        assert summary.not_enough_data_count == 1
        assert summary.avg_capture_pct is None

    def test_closing_at_the_best_point_ever_reached_reads_efficient_exit(self) -> None:
        # pnl_pct equals mfe_pct exactly -> capture_pct == 100
        trade = _trade(pnl_pct=3.0, mae_pct=-1.0, mfe_pct=3.0)
        summary = compute_exit_efficiency([trade])
        assert summary.reads[0].capture_pct == 100.0
        assert summary.reads[0].state == "efficient_exit"

    def test_closing_at_the_worst_point_ever_reached_reads_poor_exit(self) -> None:
        # pnl_pct equals mae_pct exactly -> capture_pct == 0
        trade = _trade(pnl_pct=-2.0, mae_pct=-2.0, mfe_pct=4.0)
        summary = compute_exit_efficiency([trade])
        assert summary.reads[0].capture_pct == 0.0
        assert summary.reads[0].state == "poor_exit"

    def test_closing_in_the_middle_of_its_own_range_reads_average_exit(self) -> None:
        trade = _trade(pnl_pct=1.0, mae_pct=-1.0, mfe_pct=3.0)
        summary = compute_exit_efficiency([trade])
        assert summary.reads[0].capture_pct == 50.0
        assert summary.reads[0].state == "average_exit"

    def test_a_losing_trade_that_recovered_most_of_the_way_reads_a_real_high_capture(self) -> None:
        # Closed at -0.5% after being down as much as -5% -- a real
        # partial recovery, not a win, but a genuinely well-managed exit.
        trade = _trade(pnl_pct=-0.5, mae_pct=-5.0, mfe_pct=0.0)
        summary = compute_exit_efficiency([trade])
        assert summary.reads[0].capture_pct == 90.0
        assert summary.reads[0].state == "efficient_exit"

    def test_a_winning_trade_that_gave_back_most_of_its_peak_gain_reads_poor_exit(self) -> None:
        # Peaked at +8%, closed at only +1% -- still a win, but most of
        # the favorable move was given back before exiting.
        trade = _trade(pnl_pct=1.0, mae_pct=0.0, mfe_pct=8.0)
        summary = compute_exit_efficiency([trade])
        assert summary.reads[0].capture_pct == 12.5
        assert summary.reads[0].state == "poor_exit"

    def test_summary_counts_and_average_match_the_underlying_reads(self) -> None:
        trades = [
            _trade(trade_id="a", pnl_pct=3.0, mae_pct=-1.0, mfe_pct=3.0),  # efficient (100)
            _trade(trade_id="b", pnl_pct=-2.0, mae_pct=-2.0, mfe_pct=4.0),  # poor (0)
            _trade(trade_id="c", pnl_pct=0.0, mae_pct=0.0, mfe_pct=0.0),  # not enough data
        ]
        summary = compute_exit_efficiency(trades)
        assert summary.efficient_exit_count == 1
        assert summary.poor_exit_count == 1
        assert summary.not_enough_data_count == 1
        assert summary.average_exit_count == 0
        assert summary.avg_capture_pct == 50.0  # average of the two scored reads (100 and 0)

    def test_sim_day_derived_from_closed_sim_minutes(self) -> None:
        trade = _trade(pnl_pct=1.0, mae_pct=-1.0, mfe_pct=2.0, closed_sim_minutes=1440 * 3 + 100)
        summary = compute_exit_efficiency([trade])
        assert summary.reads[0].sim_day == 3
