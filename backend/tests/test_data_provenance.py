"""Covers app/data_provenance.py — CEO directive "Next Professional
Trading Firm Phase," Priority 5 (Research Data Integrity). The one
live-measured row (candles) must actually re-check the real provider's
requested-vs-delivered count on every call, never assert a hardcoded
100%; every other row is a fixed, disclosed architectural fact, never a
per-request-varying claim.
"""
from __future__ import annotations

from app.data_provenance import SAMPLE_CANDLE_REQUEST, compute_data_provenance_report
from app.market_data import Candle, MarketDataProvider
from app.schemas import WatchlistEntry


class _FullCoverageProvider(MarketDataProvider):
    def get_quote(self, symbol: str):  # noqa: ANN201 - not exercised by this module
        raise NotImplementedError

    def get_candles(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        return [
            Candle(symbol=symbol, timeframe=timeframe, timestamp="2024-01-01T00:00:00+00:00", open=1, high=1, low=1, close=1, volume=1, data_status="simulated")
            for _ in range(limit)
        ]


class _PartialCoverageProvider(MarketDataProvider):
    def get_quote(self, symbol: str):  # noqa: ANN201
        raise NotImplementedError

    def get_candles(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        delivered = max(0, limit - 5)
        return [
            Candle(symbol=symbol, timeframe=timeframe, timestamp="2024-01-01T00:00:00+00:00", open=1, high=1, low=1, close=1, volume=1, data_status="simulated")
            for _ in range(delivered)
        ]


class _ErroringProvider(MarketDataProvider):
    def get_quote(self, symbol: str):  # noqa: ANN201
        raise NotImplementedError

    def get_candles(self, symbol: str, timeframe: str, limit: int) -> list[Candle]:
        raise ValueError("unsupported timeframe")


def _watchlist(symbol: str = "AAPL") -> list[WatchlistEntry]:
    return [WatchlistEntry(symbol=symbol, name=symbol, lastPrice=100.0, dailyChangePct=0.0, status="queued", researchProgress=0.0, assignedAgent=None)]


class TestComputeDataProvenanceReport:
    def test_full_coverage_provider_reads_simulated_with_100pct_live_measured_coverage(self) -> None:
        report = compute_data_provenance_report(_watchlist(), _FullCoverageProvider())
        candle_row = next(r for r in report.sources if r.subsystem.startswith("Live Quotes"))
        assert candle_row.category == "simulated"
        assert candle_row.coverage_pct == 100.0
        assert candle_row.reproducible is True

    def test_partial_coverage_is_a_real_live_measured_percentage_not_a_hardcoded_100(self) -> None:
        report = compute_data_provenance_report(_watchlist(), _PartialCoverageProvider())
        candle_row = next(r for r in report.sources if r.subsystem.startswith("Live Quotes"))
        expected = round((SAMPLE_CANDLE_REQUEST - 5) / SAMPLE_CANDLE_REQUEST * 100.0, 1)
        assert candle_row.coverage_pct == expected

    def test_erroring_provider_reads_unavailable_not_a_crash(self) -> None:
        report = compute_data_provenance_report(_watchlist(), _ErroringProvider())
        candle_row = next(r for r in report.sources if r.subsystem.startswith("Live Quotes"))
        assert candle_row.category == "unavailable"
        assert candle_row.coverage_pct == 0.0

    def test_empty_watchlist_falls_back_to_a_real_sample_symbol(self) -> None:
        report = compute_data_provenance_report([], _FullCoverageProvider())
        candle_row = next(r for r in report.sources if r.subsystem.startswith("Live Quotes"))
        assert candle_row.category == "simulated"

    def test_research_desk_and_sandbox_backtests_read_synthetic_never_simulated(self) -> None:
        # Neither app/research.py nor app/simulation.py ever calls
        # get_candles() -- claiming "simulated" (candle-derived) for
        # either would be fabricated.
        report = compute_data_provenance_report(_watchlist(), _FullCoverageProvider())
        research_row = next(r for r in report.sources if "Research Desk" in r.subsystem)
        sandbox_row = next(r for r in report.sources if "Sandbox Backtests" in r.subsystem)
        assert research_row.category == "synthetic"
        assert sandbox_row.category == "synthetic"

    def test_real_market_data_and_user_provided_data_are_both_honestly_unavailable(self) -> None:
        report = compute_data_provenance_report(_watchlist(), _FullCoverageProvider())
        real_row = next(r for r in report.sources if r.subsystem.startswith("Real market data"))
        user_row = next(r for r in report.sources if r.subsystem.startswith("User-provided"))
        assert real_row.category == "unavailable"
        assert user_row.category == "unavailable"

    def test_every_source_has_a_real_nonempty_detail_string(self) -> None:
        report = compute_data_provenance_report(_watchlist(), _FullCoverageProvider())
        for source in report.sources:
            assert len(source.detail) > 20
