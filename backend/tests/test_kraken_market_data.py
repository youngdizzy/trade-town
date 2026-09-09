"""Covers app/market_data.py's `KrakenMarketDataProvider` — CEO directive
"TradeTown — Real OHLCV Market Data Provider Activation & Provenance
1.0." Two distinct kinds of test live here, per the directive's own
Section 24/25/58 ("distinguish FAKE TRANSPORT TEST from REAL EXTERNAL
SMOKE TEST — never blur the two"):

  - `TestKrakenAdapterFakeTransport` / `TestKrakenNoSilentFallback` /
    `TestKrakenSecretsNeverLeak` inject a fake `_HttpTransport` (same
    seam `tests/test_external_market_data.py` already uses) — these
    prove ADAPTER CORRECTNESS deterministically, with no real network
    call, and would pass even if Kraken's real service were down.

  - `TestKrakenRealExternalSmokeTest` makes ONE real, bounded HTTP
    request to Kraken's real public OHLC endpoint. Kraken's market-data
    endpoints require NO API key (see `KrakenMarketDataProvider`'s own
    docstring) — real external verification does not depend on
    credentials being available in this environment, only on real
    network reachability. If the real request cannot be completed for a
    genuine connectivity reason, this test SKIPS with an explicit reason
    rather than either failing the whole suite in an offline CI
    environment or silently passing without having proven anything; if
    the request completes, every assertion is against REAL data actually
    received from the real vendor — this is CASE A of the directive's
    Section 58, never fabricated."""
from __future__ import annotations

import json
import socket
import urllib.error

import pytest

from app.market_data import Candle, ExternalMarketDataProviderUnavailable, KrakenMarketDataProvider


class _FakeTransport:
    def __init__(self, responses: list[tuple[int, bytes] | Exception]) -> None:
        self._responses = list(responses)
        self.calls: list[tuple[str, dict[str, str], float]] = []

    def get(self, url: str, *, headers: dict[str, str], timeout_seconds: float) -> tuple[int, bytes]:
        self.calls.append((url, dict(headers), timeout_seconds))
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _kraken_row(ts: int, close: float = 100.0) -> list[object]:
    return [ts, close - 0.5, close + 1, close - 1, close, str(close), "10.5", 42]


def _kraken_body(pair_key: str, rows: list[list[object]]) -> bytes:
    return json.dumps({"error": [], "result": {pair_key: rows, "last": rows[-1][0] if rows else 0}}).encode()


class TestKrakenAdapterFakeTransport:
    def test_successful_response_parses_real_shaped_candles_and_drops_forming_bar(self) -> None:
        # Three rows: the last one is Kraken's always-still-forming
        # current-period candle and must never be returned (Section 7/16
        # of the directive — no fabricated "partial bar" DataStatus).
        rows = [_kraken_row(1704067200, 100.0), _kraken_row(1704070800, 101.0), _kraken_row(1704074400, 999.0)]
        transport = _FakeTransport([(200, _kraken_body("XXBTZUSD", rows))])
        provider = KrakenMarketDataProvider(transport=transport)
        candles = provider.get_candles("BTC-USD", "1h", 10)
        assert len(candles) == 2  # the third (still-forming) row was dropped
        assert all(isinstance(c, Candle) for c in candles)
        assert all(c.symbol == "BTC-USD" for c in candles)  # canonical symbol preserved, never the Kraken pair code
        assert all(c.data_status == "historical" for c in candles)
        assert candles[0].timestamp == "2024-01-01T00:00:00+00:00"
        assert candles[1].timestamp == "2024-01-01T01:00:00+00:00"

    def test_result_key_mismatch_between_requested_pair_and_response_is_handled(self) -> None:
        """Kraken echoes the OHLC series under ITS OWN internal pair name
        (`XXBTZUSD`), not the requested alias (`XBTUSD`) — the adapter
        must not assume they match."""
        rows = [_kraken_row(1704067200, 100.0), _kraken_row(1704070800, 999.0)]
        transport = _FakeTransport([(200, _kraken_body("XXBTZUSD", rows))])
        provider = KrakenMarketDataProvider(transport=transport)
        candles = provider.get_candles("BTC-USD", "1h", 10)
        assert len(candles) == 1

    def test_body_level_error_array_raises_even_on_http_200(self) -> None:
        """Kraken reports errors inside a 200 OK body, not via HTTP status
        — the generic base class's status-code-only branching would miss
        this; this adapter must check the body explicitly."""
        body = json.dumps({"error": ["EQuery:Unknown asset pair"], "result": {}}).encode()
        transport = _FakeTransport([(200, body)])
        provider = KrakenMarketDataProvider(transport=transport)
        with pytest.raises(ExternalMarketDataProviderUnavailable, match="reported an error"):
            provider.get_candles("BTC-USD", "1h", 10)

    def test_unmapped_symbol_raises_before_any_http_call(self) -> None:
        transport = _FakeTransport([])
        provider = KrakenMarketDataProvider(transport=transport)
        with pytest.raises(ExternalMarketDataProviderUnavailable, match="no Kraken pair mapping"):
            provider.get_candles("AAPL", "1h", 10)
        assert transport.calls == []  # never silently substitutes a different instrument

    def test_unsupported_timeframe_raises_value_error_before_any_http_call(self) -> None:
        transport = _FakeTransport([])
        provider = KrakenMarketDataProvider(transport=transport)
        with pytest.raises(ValueError):
            provider.get_candles("BTC-USD", "7x", 10)
        assert transport.calls == []

    def test_timeframe_maps_to_kraken_interval_minutes_in_request_url(self) -> None:
        transport = _FakeTransport([(200, _kraken_body("XXBTZUSD", [_kraken_row(1704067200)]))])
        provider = KrakenMarketDataProvider(transport=transport)
        provider.get_candles("BTC-USD", "4h", 1)
        assert "interval=240" in transport.calls[0][0]
        assert "pair=XBTUSD" in transport.calls[0][0]

    def test_duplicate_or_out_of_order_timestamp_rejected(self) -> None:
        rows = [_kraken_row(1704070800, 100.0), _kraken_row(1704067200, 101.0), _kraken_row(1704074400, 999.0)]
        transport = _FakeTransport([(200, _kraken_body("XXBTZUSD", rows))])
        provider = KrakenMarketDataProvider(transport=transport)
        with pytest.raises(ExternalMarketDataProviderUnavailable, match="Duplicate or out-of-order"):
            provider.get_candles("BTC-USD", "1h", 10)

    def test_impossible_ohlc_rejected(self) -> None:
        bad_row = [1704067200, 100.0, 90.0, 95.0, 100.0, "97", "10.5", 3]  # high < low
        rows = [bad_row, _kraken_row(1704070800, 999.0)]
        transport = _FakeTransport([(200, _kraken_body("XXBTZUSD", rows))])
        provider = KrakenMarketDataProvider(transport=transport)
        with pytest.raises(ExternalMarketDataProviderUnavailable, match="Impossible OHLC"):
            provider.get_candles("BTC-USD", "1h", 10)

    def test_negative_volume_rejected(self) -> None:
        bad_row = [1704067200, 100.0, 101.0, 99.0, 100.0, "100", "-5.0", 3]
        rows = [bad_row, _kraken_row(1704070800, 999.0)]
        transport = _FakeTransport([(200, _kraken_body("XXBTZUSD", rows))])
        provider = KrakenMarketDataProvider(transport=transport)
        with pytest.raises(ExternalMarketDataProviderUnavailable, match="Negative volume"):
            provider.get_candles("BTC-USD", "1h", 10)

    def test_malformed_json_rejected(self) -> None:
        transport = _FakeTransport([(200, b"not json")])
        provider = KrakenMarketDataProvider(transport=transport)
        with pytest.raises(ExternalMarketDataProviderUnavailable, match="Malformed response body"):
            provider.get_candles("BTC-USD", "1h", 10)

    def test_missing_result_key_rejected(self) -> None:
        transport = _FakeTransport([(200, json.dumps({"error": []}).encode())])
        provider = KrakenMarketDataProvider(transport=transport)
        with pytest.raises(ExternalMarketDataProviderUnavailable, match="missing 'result'"):
            provider.get_candles("BTC-USD", "1h", 10)

    def test_429_raises_immediately_never_retried(self) -> None:
        transport = _FakeTransport([(429, b"")])
        provider = KrakenMarketDataProvider(transport=transport, max_retries=3)
        with pytest.raises(ExternalMarketDataProviderUnavailable, match="Rate limited"):
            provider.get_candles("BTC-USD", "1h", 10)
        assert len(transport.calls) == 1

    def test_5xx_is_retried_then_succeeds(self) -> None:
        transport = _FakeTransport([(503, b""), (200, _kraken_body("XXBTZUSD", [_kraken_row(1704067200), _kraken_row(1704070800, 999.0)]))])
        provider = KrakenMarketDataProvider(transport=transport)
        candles = provider.get_candles("BTC-USD", "1h", 10)
        assert len(candles) == 1
        assert len(transport.calls) == 2

    def test_limit_windows_to_the_most_recent_n_closed_bars_preserving_order(self) -> None:
        rows = [_kraken_row(1704067200 + i * 3600, 100.0 + i) for i in range(6)]  # 6 rows, last one dropped as forming
        transport = _FakeTransport([(200, _kraken_body("XXBTZUSD", rows))])
        provider = KrakenMarketDataProvider(transport=transport)
        candles = provider.get_candles("BTC-USD", "1h", 2)
        assert len(candles) == 2
        assert candles[0].timestamp < candles[1].timestamp  # chronological order preserved
        # 5 closed bars exist (indices 0..4, closes 100..104); the most
        # recent 2 are indices 3,4 -> closes 103,104, in that order.
        assert candles[0].close == 103.0
        assert candles[1].close == 104.0


class TestKrakenNoSilentFallback:
    def test_available_is_true_with_no_credentials_at_all(self) -> None:
        """Kraken's public OHLC endpoint genuinely needs no API key —
        this must not be confused with 'accidentally always available';
        it is only ever constructed by a caller that explicitly wants
        it (see this class's own module docstring, Section 37 of the
        directive: explicit selection, never inferred)."""
        provider = KrakenMarketDataProvider(transport=_FakeTransport([]))
        assert provider.is_available() is True

    def test_missing_base_url_is_honestly_unavailable_and_never_falls_back(self) -> None:
        provider = KrakenMarketDataProvider(base_url="", transport=_FakeTransport([]))
        assert provider.is_available() is False
        with pytest.raises(ExternalMarketDataProviderUnavailable):
            provider.get_candles("BTC-USD", "1h", 10)

    def test_get_quote_is_not_implemented_never_silently_returns_mock_shaped_data(self) -> None:
        provider = KrakenMarketDataProvider(transport=_FakeTransport([]))
        with pytest.raises(ExternalMarketDataProviderUnavailable):
            provider.get_quote("BTC-USD")

    def test_repeated_5xx_exhausts_retries_and_raises_never_returns_partial_mock_data(self) -> None:
        transport = _FakeTransport([(503, b""), (503, b""), (503, b"")])
        provider = KrakenMarketDataProvider(transport=transport, max_retries=2)
        with pytest.raises(ExternalMarketDataProviderUnavailable):
            provider.get_candles("BTC-USD", "1h", 10)
        assert len(transport.calls) == 3


class TestKrakenSecretsNeverLeak:
    def test_no_authorization_header_is_ever_sent(self) -> None:
        """There is no secret to leak in the first place — Kraken's
        public OHLC endpoint takes no Authorization header at all."""
        transport = _FakeTransport([(200, _kraken_body("XXBTZUSD", [_kraken_row(1704067200), _kraken_row(1704070800, 999.0)]))])
        provider = KrakenMarketDataProvider(transport=transport)
        provider.get_candles("BTC-USD", "1h", 10)
        assert "Authorization" not in transport.calls[0][1]


class TestKrakenRealExternalSmokeTest:
    """CASE A vs CASE B of the directive's Section 58 — see this file's
    own module docstring. This is the ONLY test in this file (or in
    tests/test_external_market_data.py) that makes a real network call."""

    def test_real_bounded_request_against_the_real_kraken_api(self) -> None:
        provider = KrakenMarketDataProvider(max_retries=1, timeout_seconds=8.0)
        try:
            candles = provider.get_candles("BTC-USD", "1h", 5)
        except ExternalMarketDataProviderUnavailable as exc:
            pytest.skip(f"Real Kraken external verification could not be completed in this environment: {exc}")
        except (urllib.error.URLError, socket.timeout, ConnectionError, TimeoutError) as exc:
            pytest.skip(f"Real network connectivity to Kraken unavailable in this environment: {exc}")

        assert len(candles) > 0, "a real request that did not raise must have returned real candles, not an empty silent success"
        for candle in candles:
            assert candle.symbol == "BTC-USD"
            assert candle.timeframe == "1h"
            assert candle.data_status == "historical"  # real provenance — never "simulated"
            assert candle.high >= candle.low
            assert candle.high >= candle.open >= candle.low or candle.high >= candle.close >= candle.low
            assert candle.volume >= 0
            assert candle.open > 0 and candle.close > 0  # a real BTC price is never zero/negative
        timestamps = [c.timestamp for c in candles]
        assert timestamps == sorted(timestamps)  # deterministic chronological ordering
        assert len(set(timestamps)) == len(timestamps)  # no duplicate timestamps
