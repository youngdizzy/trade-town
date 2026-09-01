"""Covers app/market_data.py's ExternalMarketDataProvider — CEO directive
"TradeTown — Phase 10: Real Data + True Holdout + Portfolio
Intelligence," Section A. No real network call is ever made — a fake
`_HttpTransport` is injected so retry/timeout/malformed-response logic
is exercised deterministically without a real vendor contract (this
environment has no real API credentials — see that class's own module
docstring)."""
from __future__ import annotations

import json

import pytest

from app.market_data import (
    Candle,
    ExternalMarketDataProvider,
    ExternalMarketDataProviderUnavailable,
    MarketDataProvider,
    MockMarketDataProvider,
    _redact,
)


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


def _candles_body(rows: list[dict[str, object]]) -> bytes:
    return json.dumps({"candles": rows}).encode()


def _valid_row(ts: str, close: float = 100.0) -> dict[str, object]:
    return {"timestamp": ts, "open": close, "high": close + 1, "low": close - 1, "close": close, "volume": 1000.0}


class TestSharedInterface:
    def test_external_and_mock_share_the_same_abstract_base(self) -> None:
        assert isinstance(ExternalMarketDataProvider(), MarketDataProvider)
        assert isinstance(MockMarketDataProvider(), MarketDataProvider)


class TestUnavailableStatus:
    def test_no_configuration_reports_unavailable(self) -> None:
        provider = ExternalMarketDataProvider(provider_name="", api_key="", base_url="")
        status = provider.status()
        assert status.available is False
        assert "EXTERNAL_MARKET_DATA_PROVIDER" in status.reason
        assert "EXTERNAL_MARKET_DATA_API_KEY" in status.reason
        assert "EXTERNAL_MARKET_DATA_BASE_URL" in status.reason

    def test_partial_configuration_still_unavailable(self) -> None:
        provider = ExternalMarketDataProvider(provider_name="polygon", api_key="", base_url="https://example.test")
        assert provider.is_available() is False

    def test_full_configuration_reports_available(self) -> None:
        provider = ExternalMarketDataProvider(provider_name="polygon", api_key="secret-key", base_url="https://example.test")
        assert provider.is_available() is True

    def test_get_candles_raises_when_unavailable_never_returns_mock_data(self) -> None:
        provider = ExternalMarketDataProvider(provider_name="", api_key="", base_url="")
        with pytest.raises(ExternalMarketDataProviderUnavailable):
            provider.get_candles("AAPL", "1h", 100)

    def test_get_quote_raises_when_unavailable(self) -> None:
        provider = ExternalMarketDataProvider(provider_name="", api_key="", base_url="")
        with pytest.raises(ExternalMarketDataProviderUnavailable):
            provider.get_quote("AAPL")


class TestNoSilentMockFallback:
    def test_unavailable_result_is_never_shaped_like_mock_candles(self) -> None:
        """A real, direct proof: catching the real exception never yields
        a real (or fake) list of Candle objects to fall back on silently."""
        provider = ExternalMarketDataProvider(provider_name="", api_key="", base_url="")
        try:
            result = provider.get_candles("AAPL", "1h", 10)
            raise AssertionError(f"expected ExternalMarketDataProviderUnavailable, got a real result: {result!r}")
        except ExternalMarketDataProviderUnavailable:
            pass  # honest — no candles were silently substituted


class TestRealHttpParsing:
    def _available_provider(self, transport: _FakeTransport) -> ExternalMarketDataProvider:
        return ExternalMarketDataProvider(provider_name="polygon", api_key="secret-key-123", base_url="https://example.test", max_retries=2, transport=transport)

    def test_successful_response_parses_real_candles(self) -> None:
        transport = _FakeTransport([(200, _candles_body([_valid_row("2024-01-01T00:00:00+00:00"), _valid_row("2024-01-01T01:00:00+00:00", close=101.0)]))])
        provider = self._available_provider(transport)
        candles = provider.get_candles("AAPL", "1h", 2)
        assert len(candles) == 2
        assert all(isinstance(c, Candle) for c in candles)
        assert all(c.data_status == "historical" for c in candles)
        assert candles[0].timestamp == "2024-01-01T00:00:00+00:00"  # preserved exactly, unnormalized

    def test_duplicate_timestamp_rejected(self) -> None:
        transport = _FakeTransport([(200, _candles_body([_valid_row("2024-01-01T00:00:00+00:00"), _valid_row("2024-01-01T00:00:00+00:00")]))])
        provider = self._available_provider(transport)
        with pytest.raises(ExternalMarketDataProviderUnavailable, match="Duplicate timestamp"):
            provider.get_candles("AAPL", "1h", 2)

    def test_out_of_order_timestamp_rejected(self) -> None:
        transport = _FakeTransport([(200, _candles_body([_valid_row("2024-01-02T00:00:00+00:00"), _valid_row("2024-01-01T00:00:00+00:00")]))])
        provider = self._available_provider(transport)
        with pytest.raises(ExternalMarketDataProviderUnavailable, match="precedes prior timestamp"):
            provider.get_candles("AAPL", "1h", 2)

    def test_impossible_ohlc_rejected(self) -> None:
        row = {"timestamp": "2024-01-01T00:00:00+00:00", "open": 100.0, "high": 90.0, "low": 95.0, "close": 100.0, "volume": 1000.0}
        transport = _FakeTransport([(200, _candles_body([row]))])
        provider = self._available_provider(transport)
        with pytest.raises(ExternalMarketDataProviderUnavailable, match="Impossible OHLC"):
            provider.get_candles("AAPL", "1h", 1)

    def test_malformed_json_rejected(self) -> None:
        transport = _FakeTransport([(200, b"not json")])
        provider = self._available_provider(transport)
        with pytest.raises(ExternalMarketDataProviderUnavailable, match="Malformed response"):
            provider.get_candles("AAPL", "1h", 1)

    def test_missing_field_rejected(self) -> None:
        transport = _FakeTransport([(200, _candles_body([{"timestamp": "2024-01-01T00:00:00+00:00", "open": 1.0}]))])
        provider = self._available_provider(transport)
        with pytest.raises(ExternalMarketDataProviderUnavailable, match="Malformed candle"):
            provider.get_candles("AAPL", "1h", 1)

    def test_unsupported_timeframe_raises_value_error_before_any_http_call(self) -> None:
        transport = _FakeTransport([])
        provider = self._available_provider(transport)
        with pytest.raises(ValueError):
            provider.get_candles("AAPL", "7x", 1)
        assert transport.calls == []


class TestRetryAndRateLimit:
    def _available_provider(self, transport: _FakeTransport, max_retries: int = 2) -> ExternalMarketDataProvider:
        return ExternalMarketDataProvider(provider_name="polygon", api_key="secret-key-123", base_url="https://example.test", max_retries=max_retries, transport=transport)

    def test_5xx_is_retried_then_succeeds(self) -> None:
        transport = _FakeTransport([(503, b""), (200, _candles_body([_valid_row("2024-01-01T00:00:00+00:00")]))])
        provider = self._available_provider(transport)
        candles = provider.get_candles("AAPL", "1h", 1)
        assert len(candles) == 1
        assert len(transport.calls) == 2

    def test_5xx_exhausts_retries_and_raises(self) -> None:
        transport = _FakeTransport([(503, b""), (503, b""), (503, b"")])
        provider = self._available_provider(transport, max_retries=2)
        with pytest.raises(ExternalMarketDataProviderUnavailable):
            provider.get_candles("AAPL", "1h", 1)
        assert len(transport.calls) == 3

    def test_401_is_never_retried(self) -> None:
        transport = _FakeTransport([(401, b"")])
        provider = self._available_provider(transport, max_retries=3)
        with pytest.raises(ExternalMarketDataProviderUnavailable, match="Authentication rejected"):
            provider.get_candles("AAPL", "1h", 1)
        assert len(transport.calls) == 1

    def test_429_raises_immediately_never_retried(self) -> None:
        transport = _FakeTransport([(429, b"")])
        provider = self._available_provider(transport, max_retries=3)
        with pytest.raises(ExternalMarketDataProviderUnavailable, match="Rate limited"):
            provider.get_candles("AAPL", "1h", 1)
        assert len(transport.calls) == 1

    def test_timeout_is_retried(self) -> None:
        transport = _FakeTransport([TimeoutError("timed out"), (200, _candles_body([_valid_row("2024-01-01T00:00:00+00:00")]))])
        provider = self._available_provider(transport)
        candles = provider.get_candles("AAPL", "1h", 1)
        assert len(candles) == 1


class TestSecretsNeverLeak:
    def test_redact_replaces_every_occurrence(self) -> None:
        assert _redact("Bearer sk-secret123 failed for sk-secret123", "sk-secret123") == "Bearer [REDACTED] failed for [REDACTED]"

    def test_401_error_message_never_contains_the_api_key(self) -> None:
        api_key = "sk-super-secret-key-999"
        transport = _FakeTransport([(401, b"")])
        provider = ExternalMarketDataProvider(provider_name="polygon", api_key=api_key, base_url="https://example.test", transport=transport)
        with pytest.raises(ExternalMarketDataProviderUnavailable) as exc_info:
            provider.get_candles("AAPL", "1h", 1)
        assert api_key not in str(exc_info.value)

    def test_timeout_error_message_never_contains_the_api_key(self) -> None:
        api_key = "sk-super-secret-key-999"

        class _LeakyTimeoutTransport:
            def get(self, url: str, *, headers: dict[str, str], timeout_seconds: float) -> tuple[int, bytes]:
                raise TimeoutError(f"connection to {url} with key {api_key} timed out")

        provider = ExternalMarketDataProvider(provider_name="polygon", api_key=api_key, base_url="https://example.test", max_retries=0, transport=_LeakyTimeoutTransport())
        with pytest.raises(ExternalMarketDataProviderUnavailable) as exc_info:
            provider.get_candles("AAPL", "1h", 1)
        assert api_key not in str(exc_info.value)

    def test_status_reason_never_contains_the_api_key(self) -> None:
        api_key = "sk-super-secret-key-999"
        provider = ExternalMarketDataProvider(provider_name="polygon", api_key=api_key, base_url="")
        assert api_key not in provider.status().reason
