"""CEO directive "TradeTown — True AI Agent Reasoning Foundation 1.0" — the
one real, minimal AI provider abstraction. This module has never existed in
this codebase before this directive; Phase 0's own forensic audit confirmed
zero LLM/HTTP-client infrastructure existed anywhere: no httpx/requests in
requirements.txt, no ANTHROPIC_API_KEY/OPENAI_API_KEY (or equivalent) in this
process's own environment, no provider fields in app/config.py.

Design principle (Part II/III of the directive): this is the smallest safe
interface that can honestly support both real states —

  a genuine model call, when real credentials genuinely exist in this
  process's own environment, and
  an honest "provider_unavailable" result when they don't —

and NEVER a fabricated successful response in either case. `get_ai_provider()`
is the one real factory every caller uses; it returns `UnavailableAIProvider`
unless `TRADETOWN_AI_PROVIDER_API_KEY` is genuinely set, so the default,
credential-free behavior in this (and any) environment without that secret
configured is always the honest unavailable path — never a crash, never a
silent fake success.

Secrets discipline (Part III): the API key is read once, server-side, from
`os.environ` — never logged, never included in any `AIReasoningResult` field,
never returned by any API response, never persisted to `GameSaveState`. The
frontend has no code path that could ever receive it (see
app/routers/ai_reasoning.py — no endpoint echoes back anything from the
request headers/config)."""
from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Literal, Protocol

import httpx

# CEO directive's own naming choice, deliberately prefixed TRADETOWN_ rather
# than a bare ANTHROPIC_API_KEY: this key configures TradeTown's OWN in-game
# AI reasoning feature, a decision distinct from (and unrelated to) whatever
# API credentials might otherwise exist in a deployment environment for
# unrelated purposes — never assumed to be the same secret.
AI_PROVIDER_API_KEY_ENV_VAR = "TRADETOWN_AI_PROVIDER_API_KEY"
AI_MODEL_ENV_VAR = "TRADETOWN_AI_MODEL"
DEFAULT_MODEL = "claude-sonnet-4-5"

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_VERSION = "2023-06-01"
REQUEST_TIMEOUT_SECONDS = 30.0
MAX_OUTPUT_TOKENS = 2000


@dataclass(frozen=True)
class ProviderCallResult:
    """The real, raw outcome of one provider call attempt — deliberately
    UNvalidated/UNparsed (see app/ai_reasoning.py for the structured-output
    validation layer, which is a separate, later step). `status == "ok"`
    is the only state where `raw_text` is ever non-None; every other status
    is an honest, disclosed failure to reach a real answer."""

    status: Literal["ok", "unavailable", "timeout", "error"]
    provider: str
    model: str | None
    raw_text: str | None
    input_tokens: int | None
    output_tokens: int | None
    latency_ms: float
    detail: str | None


class AIProvider(Protocol):
    """The one real interface every concrete provider (and every test
    fake) implements. Intentionally minimal — `system_prompt` (the fixed,
    trusted instruction text) and `user_content` (the untrusted/structured
    evidence, always passed as DATA — see app/ai_reasoning.py's own
    Part XI prompt-injection defense) are kept as two separate parameters
    specifically so a concrete implementation can never accidentally
    concatenate untrusted content into the trusted instruction channel."""

    provider_name: str

    async def call(self, *, system_prompt: str, user_content: str) -> ProviderCallResult: ...


class UnavailableAIProvider:
    """The honest default whenever no real credentials are configured.
    Never attempts a network call, never raises — every caller downstream
    already has to handle a real 'unavailable' outcome, so this is not a
    degraded special case, it is the same real contract every provider
    honors."""

    provider_name = "unavailable"

    async def call(self, *, system_prompt: str, user_content: str) -> ProviderCallResult:
        return ProviderCallResult(
            status="unavailable",
            provider=self.provider_name,
            model=None,
            raw_text=None,
            input_tokens=None,
            output_tokens=None,
            latency_ms=0.0,
            detail=f"No AI provider credentials configured in this environment ({AI_PROVIDER_API_KEY_ENV_VAR} unset).",
        )


class AnthropicAIProvider:
    """A real, minimal Anthropic Messages API client. Only ever
    constructed by `get_ai_provider()` when a real API key is genuinely
    present — never constructed speculatively, never with a fabricated
    key. Reads no other TradeTown state; takes no lock; never touches
    `GameSaveState` directly (app/ai_reasoning.py/app/state.py own that
    boundary)."""

    provider_name = "anthropic"

    def __init__(self, *, api_key: str, model: str) -> None:
        self._api_key = api_key
        self._model = model

    async def call(self, *, system_prompt: str, user_content: str) -> ProviderCallResult:
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
                response = await client.post(
                    ANTHROPIC_API_URL,
                    headers={
                        "x-api-key": self._api_key,
                        "anthropic-version": ANTHROPIC_API_VERSION,
                        "content-type": "application/json",
                    },
                    json={
                        "model": self._model,
                        "max_tokens": MAX_OUTPUT_TOKENS,
                        "system": system_prompt,
                        "messages": [{"role": "user", "content": user_content}],
                    },
                )
        except httpx.TimeoutException:
            return ProviderCallResult(
                status="timeout", provider=self.provider_name, model=self._model, raw_text=None,
                input_tokens=None, output_tokens=None, latency_ms=(time.monotonic() - start) * 1000,
                detail="Provider request timed out.",
            )
        except httpx.HTTPError as exc:
            return ProviderCallResult(
                status="error", provider=self.provider_name, model=self._model, raw_text=None,
                input_tokens=None, output_tokens=None, latency_ms=(time.monotonic() - start) * 1000,
                detail=f"Provider request failed: {exc}",
            )
        latency_ms = (time.monotonic() - start) * 1000
        if response.status_code != 200:
            return ProviderCallResult(
                status="error", provider=self.provider_name, model=self._model, raw_text=None,
                input_tokens=None, output_tokens=None, latency_ms=latency_ms,
                detail=f"Provider returned HTTP {response.status_code}: {response.text[:500]}",
            )
        body = response.json()
        text_blocks = [block.get("text", "") for block in body.get("content", []) if block.get("type") == "text"]
        usage = body.get("usage", {})
        return ProviderCallResult(
            status="ok",
            provider=self.provider_name,
            model=body.get("model", self._model),
            raw_text="".join(text_blocks),
            input_tokens=usage.get("input_tokens"),
            output_tokens=usage.get("output_tokens"),
            latency_ms=latency_ms,
            detail=None,
        )


def get_ai_provider() -> AIProvider:
    """The one real factory. Returns `UnavailableAIProvider` unless a
    real key is genuinely present in this process's own environment —
    never a fabricated available provider, never a crash when the key is
    absent (the honest, expected case in this environment today)."""
    api_key = os.environ.get(AI_PROVIDER_API_KEY_ENV_VAR)
    if not api_key:
        return UnavailableAIProvider()
    model = os.environ.get(AI_MODEL_ENV_VAR) or DEFAULT_MODEL
    return AnthropicAIProvider(api_key=api_key, model=model)
