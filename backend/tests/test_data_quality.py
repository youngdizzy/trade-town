"""Covers app/data_quality.py — CEO directive "Phase 9 / Real Market
Data + Evidence Integrity Foundation," Data Quality Gate section."""
from __future__ import annotations

from app.data_quality import validate_candle_series
from app.market_data import Candle


def _candle(ts: str, close: float = 100.0, symbol: str = "AAPL", timeframe: str = "1h", volume: float = 1000.0, high: float | None = None, low: float | None = None) -> Candle:
    return Candle(symbol=symbol, timeframe=timeframe, timestamp=ts, open=close, high=high if high is not None else close + 1, low=low if low is not None else close - 1, close=close, volume=volume, data_status="simulated")


def _clean_series(n: int = 40) -> list[Candle]:
    return [_candle(ts=f"2024-01-{(d % 28) + 1:02d}T{(d % 24):02d}:00:00+00:00", close=100.0 + d) for d in range(n)]


class TestValidateCandleSeries:
    def test_clean_series_of_sufficient_length_is_valid(self) -> None:
        candles = [_candle(ts=f"2024-01-01T{h:02d}:00:00+00:00") for h in range(0, 24)] + [_candle(ts=f"2024-01-02T{h:02d}:00:00+00:00") for h in range(0, 10)]
        report = validate_candle_series(candles, symbol="AAPL", timeframe="1h")
        assert report.data_valid is True
        assert report.issues == []
        assert report.candle_count == len(candles)

    def test_too_few_candles_flags_insufficient_history(self) -> None:
        candles = [_candle(ts="2024-01-01T00:00:00+00:00")]
        report = validate_candle_series(candles, symbol="AAPL", timeframe="1h", min_candles=30)
        assert report.data_valid is False
        assert any(i.code == "insufficient_history" for i in report.issues)

    def test_out_of_order_timestamp_detected(self) -> None:
        candles = _clean_series()
        candles[5], candles[6] = candles[6], candles[5]
        report = validate_candle_series(candles, symbol="AAPL", timeframe="1h")
        assert any(i.code == "timestamp_out_of_order" for i in report.issues)

    def test_duplicate_timestamp_detected(self) -> None:
        candles = _clean_series()
        candles[3] = _candle(ts=candles[2].timestamp)
        report = validate_candle_series(candles, symbol="AAPL", timeframe="1h")
        assert any(i.code == "duplicate_timestamp" for i in report.issues)

    def test_missing_bar_gap_detected(self) -> None:
        candles = [_candle(ts="2024-01-01T00:00:00+00:00"), _candle(ts="2024-01-01T01:00:00+00:00"), _candle(ts="2024-01-01T05:00:00+00:00")]
        candles += [_candle(ts=f"2024-01-01T{h:02d}:00:00+00:00") for h in range(6, 35)]
        report = validate_candle_series(candles, symbol="AAPL", timeframe="1h")
        assert any(i.code == "missing_bars" for i in report.issues)

    def test_impossible_ohlc_detected(self) -> None:
        candles = _clean_series()
        candles[2] = Candle(symbol="AAPL", timeframe="1h", timestamp=candles[2].timestamp, open=100.0, high=90.0, low=95.0, close=100.0, volume=1000.0, data_status="simulated")
        report = validate_candle_series(candles, symbol="AAPL", timeframe="1h")
        assert any(i.code == "impossible_ohlc" for i in report.issues)

    def test_non_positive_price_detected(self) -> None:
        candles = _clean_series()
        candles[1] = Candle(symbol="AAPL", timeframe="1h", timestamp=candles[1].timestamp, open=0.0, high=1.0, low=0.0, close=0.0, volume=1000.0, data_status="simulated")
        report = validate_candle_series(candles, symbol="AAPL", timeframe="1h")
        assert any(i.code == "non_positive_price" for i in report.issues)

    def test_negative_volume_detected(self) -> None:
        candles = _clean_series()
        candles[1] = _candle(ts=candles[1].timestamp, volume=-5.0)
        report = validate_candle_series(candles, symbol="AAPL", timeframe="1h")
        assert any(i.code == "negative_volume" for i in report.issues)

    def test_symbol_mismatch_detected(self) -> None:
        candles = _clean_series()
        candles[1] = _candle(ts=candles[1].timestamp, symbol="MSFT")
        report = validate_candle_series(candles, symbol="AAPL", timeframe="1h")
        assert any(i.code == "symbol_mismatch" for i in report.issues)

    def test_timeframe_mismatch_detected(self) -> None:
        candles = _clean_series()
        candles[1] = _candle(ts=candles[1].timestamp, timeframe="5m")
        report = validate_candle_series(candles, symbol="AAPL", timeframe="1h")
        assert any(i.code == "timeframe_mismatch" for i in report.issues)

    def test_unsupported_timeframe_flags_mismatch(self) -> None:
        report = validate_candle_series(_clean_series(), symbol="AAPL", timeframe="7x")
        assert any(i.code == "timeframe_mismatch" for i in report.issues)

    def test_timezone_naive_timestamp_detected(self) -> None:
        candles = _clean_series()
        candles[1] = _candle(ts="2024-01-01T00:00:00")
        report = validate_candle_series(candles, symbol="AAPL", timeframe="1h")
        assert any(i.code == "timezone_invalid" for i in report.issues)

    def test_unparseable_timestamp_detected(self) -> None:
        candles = _clean_series()
        candles[1] = _candle(ts="not-a-timestamp")
        report = validate_candle_series(candles, symbol="AAPL", timeframe="1h")
        assert any(i.code == "timezone_invalid" for i in report.issues)

    def test_empty_series_is_invalid_via_insufficient_history_only(self) -> None:
        report = validate_candle_series([], symbol="AAPL", timeframe="1h")
        assert report.data_valid is False
        assert [i.code for i in report.issues] == ["insufficient_history"]
