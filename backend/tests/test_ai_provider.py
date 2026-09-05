"""Covers app/ai_provider.py — CEO directive "TradeTown — True AI Agent
Reasoning Foundation 1.0," Part II/III. Confirms: (1) the honest default
with no credentials configured is `UnavailableAIProvider`, never a crash
and never a fabricated success; (2) a real key genuinely present in the
environment produces a real `AnthropicAIProvider`; (3) that provider's
actual HTTP call correctly maps a 200 response, a non-200 response, a
timeout, and a transport error onto the four real `ProviderCallResult`
statuses — using `httpx.MockTransport` so no real network call is ever
made; (4) the API key never appears anywhere in a `ProviderCallResult`.
"""
from __future__ import annotations

import asyncio

import httpx
import pytest

from app.ai_provider import (
    AI_MODEL_ENV_VAR,
    AI_PROVIDER_API_KEY_ENV_VAR,
    AnthropicAIProvider,
    UnavailableAIProvider,
    get_ai_provider,
)


def test_get_ai_provider_is_unavailable_when_no_key_is_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(AI_PROVIDER_API_KEY_ENV_VAR, raising=False)
    provider = get_ai_provider()
    assert isinstance(provider, UnavailableAIProvider)
    assert provider.provider_name == "unavailable"


def test_get_ai_provider_returns_real_provider_when_key_is_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(AI_PROVIDER_API_KEY_ENV_VAR, "test-key-do-not-use")
    provider = get_ai_provider()
    assert isinstance(provider, AnthropicAIProvider)
    assert provider.provider_name == "anthropic"


def test_get_ai_provider_uses_configured_model_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(AI_PROVIDER_API_KEY_ENV_VAR, "test-key-do-not-use")
    monkeypatch.setenv(AI_MODEL_ENV_VAR, "claude-custom-model")
    provider = get_ai_provider()
    assert isinstance(provider, AnthropicAIProvider)
    assert provider._model == "claude-custom-model"


def test_unavailable_provider_never_calls_network_and_reports_honestly() -> None:
    async def _run() -> None:
        provider = UnavailableAIProvider()
        result = await provider.call(system_prompt="sys", user_content="data")
        assert result.status == "unavailable"
        assert result.raw_text is None
        assert AI_PROVIDER_API_KEY_ENV_VAR in (result.detail or "")

    asyncio.run(_run())


def _provider_with_transport(monkeypatch: pytest.MonkeyPatch, handler: httpx.MockTransport, *, api_key: str = "secret-test-key-xyz") -> AnthropicAIProvider:
    real_async_client = httpx.AsyncClient

    def _patched_client(*args: object, **kwargs: object) -> httpx.AsyncClient:
        kwargs["transport"] = handler
        return real_async_client(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(httpx, "AsyncClient", _patched_client)
    return AnthropicAIProvider(api_key=api_key, model="claude-test-model")


def test_anthropic_provider_ok_response_is_parsed(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["x-api-key"] == "secret-test-key-xyz"
        return httpx.Response(200, json={"model": "claude-test-model", "content": [{"type": "text", "text": "hello world"}], "usage": {"input_tokens": 12, "output_tokens": 3}})

    provider = _provider_with_transport(monkeypatch, httpx.MockTransport(handler))
    result = asyncio.run(provider.call(system_prompt="sys", user_content="data"))
    assert result.status == "ok"
    assert result.raw_text == "hello world"
    assert result.input_tokens == 12
    assert result.output_tokens == 3
    assert "secret-test-key-xyz" not in repr(result)


def test_anthropic_provider_non_200_is_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, text="unauthorized")

    provider = _provider_with_transport(monkeypatch, httpx.MockTransport(handler))
    result = asyncio.run(provider.call(system_prompt="sys", user_content="data"))
    assert result.status == "error"
    assert result.raw_text is None
    assert "401" in (result.detail or "")


def test_anthropic_provider_timeout_is_reported_honestly(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("timed out", request=request)

    provider = _provider_with_transport(monkeypatch, httpx.MockTransport(handler))
    result = asyncio.run(provider.call(system_prompt="sys", user_content="data"))
    assert result.status == "timeout"
    assert result.raw_text is None


def test_anthropic_provider_transport_error_is_reported_honestly(monkeypatch: pytest.MonkeyPatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    provider = _provider_with_transport(monkeypatch, httpx.MockTransport(handler))
    result = asyncio.run(provider.call(system_prompt="sys", user_content="data"))
    assert result.status == "error"
    assert result.raw_text is None
