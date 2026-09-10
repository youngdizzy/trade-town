"""Static bearer authentication for the MCP boundary.

PLACEMENT. This runs as pure ASGI middleware wrapping the MCP application, so
it executes before the MCP transport parses a request and therefore before any
tool function can be reached. There is no code path from an unauthenticated
request to a tool.

v0 LIMITATION, ACCEPTED AND DOCUMENTED: rotation is restart-based. Changing
MCP_BEARER_TOKEN requires restarting the service; there is no online rotation
and no credential expiry independent of a mission's own `expiresAt`.
"""
from __future__ import annotations

import hmac
import json
from collections.abc import Awaitable, Callable
from typing import Any

from app.errors import BoundaryError

_UNAUTHENTICATED = BoundaryError("UNAUTHENTICATED", "missing or invalid bearer credential")


def extract_bearer(headers: list[tuple[bytes, bytes]]) -> str | None:
    """Pull the bearer value out of raw ASGI headers, or None."""
    for key, value in headers:
        if key.lower() != b"authorization":
            continue
        try:
            decoded = value.decode("latin-1").strip()
        except UnicodeDecodeError:
            return None
        scheme, _, token = decoded.partition(" ")
        if scheme.lower() != "bearer":
            return None
        return token.strip() or None
    return None


def verify_bearer(presented: str | None, expected: str) -> bool:
    """Constant-time comparison.

    `hmac.compare_digest` is used so a wrong credential takes the same time to
    reject regardless of how many leading characters were correct."""
    if not presented:
        return False
    return hmac.compare_digest(presented.encode("utf-8"), expected.encode("utf-8"))


class BearerAuthMiddleware:
    """ASGI middleware enforcing the static bearer credential.

    Deliberately pure ASGI rather than a Starlette BaseHTTPMiddleware: it
    wraps the application returned by MCPServer.streamable_http_app(), so
    nothing inside the MCP machinery runs until authentication has passed."""

    def __init__(
        self,
        app: Callable[..., Awaitable[None]],
        *,
        expected_token: str,
        on_denied: Callable[[str], None] | None = None,
        exempt_paths: frozenset[str] = frozenset({"/healthz"}),
    ) -> None:
        self._app = app
        self._expected_token = expected_token
        self._on_denied = on_denied
        self._exempt_paths = exempt_paths

    async def __call__(self, scope: dict[str, Any], receive: Any, send: Any) -> None:
        if scope.get("type") != "http":
            # Non-HTTP scopes (lifespan) are passed through untouched; they
            # carry no external request and cannot reach a tool.
            await self._app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in self._exempt_paths:
            await self._app(scope, receive, send)
            return

        presented = extract_bearer(scope.get("headers") or [])
        if not verify_bearer(presented, self._expected_token):
            if self._on_denied is not None:
                self._on_denied(path)
            await self._send_error(send)
            return

        await self._app(scope, receive, send)

    @staticmethod
    async def _send_error(send: Any) -> None:
        body = json.dumps(_UNAUTHENTICATED.to_payload()).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": _UNAUTHENTICATED.status,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode("ascii")),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
