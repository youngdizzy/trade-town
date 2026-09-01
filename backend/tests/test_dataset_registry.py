"""Covers app/dataset_registry.py — CEO directive "Phase 9 / Real Market
Data + Evidence Integrity Foundation," Dataset Versioning section."""
from __future__ import annotations

from app.dataset_registry import build_dataset_metadata
from app.market_data import Candle


def _candle(symbol: str = "AAPL", timeframe: str = "1h", ts: str = "2024-01-01T00:00:00+00:00", close: float = 100.0) -> Candle:
    return Candle(symbol=symbol, timeframe=timeframe, timestamp=ts, open=close, high=close + 1, low=close - 1, close=close, volume=1000.0, data_status="simulated")


class TestBuildDatasetMetadata:
    def test_full_coverage_no_missing_symbols(self) -> None:
        candles_by_symbol = {"AAPL": [_candle(ts=f"2024-01-{d:02d}T00:00:00+00:00") for d in range(1, 11)]}
        metadata = build_dataset_metadata(candles_by_symbol, symbols=["AAPL"], timeframe="1h", candles_per_symbol_requested=10)
        assert metadata.coverage_pct == 100.0
        assert metadata.missing_bar_symbols == []
        assert metadata.candles_per_symbol_retrieved == {"AAPL": 10}

    def test_partial_coverage_flags_missing_symbol(self) -> None:
        candles_by_symbol = {"AAPL": [_candle(ts=f"2024-01-{d:02d}T00:00:00+00:00") for d in range(1, 6)]}
        metadata = build_dataset_metadata(candles_by_symbol, symbols=["AAPL"], timeframe="1h", candles_per_symbol_requested=10)
        assert metadata.coverage_pct == 50.0
        assert metadata.missing_bar_symbols == ["AAPL"]

    def test_symbol_absent_entirely_counts_as_zero_retrieved(self) -> None:
        metadata = build_dataset_metadata({}, symbols=["AAPL"], timeframe="1h", candles_per_symbol_requested=10)
        assert metadata.candles_per_symbol_retrieved == {"AAPL": 0}
        assert metadata.coverage_pct == 0.0
        assert metadata.missing_bar_symbols == ["AAPL"]

    def test_source_and_category_are_honestly_mock_and_simulated(self) -> None:
        metadata = build_dataset_metadata({"AAPL": [_candle()]}, symbols=["AAPL"], timeframe="1h", candles_per_symbol_requested=1)
        assert metadata.source == "mock_provider"
        assert metadata.data_category == "simulated"

    def test_version_is_deterministic_for_identical_content(self) -> None:
        candles = [_candle(ts="2024-01-01T00:00:00+00:00", close=101.5)]
        m1 = build_dataset_metadata({"AAPL": candles}, symbols=["AAPL"], timeframe="1h", candles_per_symbol_requested=1)
        m2 = build_dataset_metadata({"AAPL": candles}, symbols=["AAPL"], timeframe="1h", candles_per_symbol_requested=1)
        assert m1.dataset_version == m2.dataset_version

    def test_version_changes_when_content_changes(self) -> None:
        m1 = build_dataset_metadata({"AAPL": [_candle(close=100.0)]}, symbols=["AAPL"], timeframe="1h", candles_per_symbol_requested=1)
        m2 = build_dataset_metadata({"AAPL": [_candle(close=200.0)]}, symbols=["AAPL"], timeframe="1h", candles_per_symbol_requested=1)
        assert m1.dataset_version != m2.dataset_version

    def test_dataset_id_reflects_shape_not_content(self) -> None:
        metadata = build_dataset_metadata({"AAPL": [_candle()]}, symbols=["AAPL"], timeframe="1h", candles_per_symbol_requested=50)
        assert metadata.dataset_id == "1h:AAPL:50"

    def test_zero_requested_symbols_has_zero_coverage_not_a_crash(self) -> None:
        metadata = build_dataset_metadata({}, symbols=[], timeframe="1h", candles_per_symbol_requested=10)
        assert metadata.coverage_pct == 0.0
        assert metadata.missing_bar_symbols == []
