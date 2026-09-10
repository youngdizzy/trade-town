"""GET-only, path-allowlisted HTTP client for TradeTown.

TWO INDEPENDENT LAYERS, DELIBERATELY REDUNDANT.

  1. NETWORK (the real boundary). In the deployed topology this client's base
     URL is the frontend nginx GET-allowlist listener on port 8081, which
     forwards an exact allowlist of GET paths and answers everything else with
     403 — including every non-GET method, via `limit_except GET`. A bug or a
     full compromise inside this service still cannot reach a mutation
     endpoint, because nginx will not forward the request.

  2. APPLICATION (this module). There is no method parameter anywhere in this
     class. The only verb it can emit is GET, and the path is checked against
     ALLOWED_PATHS before the request is built. This layer exists so that a
     misconfiguration of layer 1 is not a single point of failure.

The backend exposes 135 POST/PUT/PATCH/DELETE endpoints. Neither layer is
optional.

NO SILENT FALLBACK. Every method either returns real data fetched from the
configured source, or raises a BoundaryError with a specific, secret-free
reason. It never substitutes mock data, never invents a value, and never
downgrades an error into an empty success — mirroring
backend/app/market_data.py::ExternalMarketDataProvider's own stated rule.
"""
from __future__ import annotations

from typing import Any, Mapping
from urllib.parse import urlencode

import httpx2

from app.errors import BoundaryError
from app.redaction import redact

# Exact paths this service may request. Mirrors the nginx allowlist in
# frontend/deploy/nginx.conf. Adding a path here without adding it there (or
# vice versa) is a review failure; the test suite asserts the two agree.
ALLOWED_PATHS = frozenset(
    {
        "/api/health",
        "/api/runs/active",
        "/api/market/timeframes",
        "/api/market/candles",
        "/api/market/data-provenance",
        "/api/mcp-read/approved-research",
        "/api/mcp-read/approved-memory",
        "/api/mcp-read/agent-findings",
    }
)


class TradeTownReadClient:
    def __init__(self, base_url: str, *, timeout_seconds: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout_seconds

    async def get_json(self, path: str, params: Mapping[str, Any] | None = None) -> Any:
        """The ONLY request method on this class. There is no post/put/patch/
        delete, and no `method` argument — by construction, not by policy."""
        if path not in ALLOWED_PATHS:
            raise BoundaryError("FORBIDDEN", f"path is not in the MCP read allowlist: {path}")

        query = {k: v for k, v in (params or {}).items() if v is not None}
        url = f"{self._base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query, doseq=True)}"

        try:
            async with httpx2.AsyncClient(timeout=self._timeout) as client:
                response = await client.get(url)
        except httpx2.TimeoutException as exc:
            raise BoundaryError(
                "TIMEOUT", f"TradeTown read timed out after {self._timeout:g}s: {redact(str(exc))}"
            ) from None
        except Exception as exc:  # transport-level failure
            raise BoundaryError(
                "UNAVAILABLE", f"TradeTown read transport error: {redact(type(exc).__name__)}"
            ) from None

        if response.status_code == 403:
            raise BoundaryError("FORBIDDEN", f"TradeTown read allowlist rejected: {path}")
        if response.status_code == 404:
            raise BoundaryError("NOT_FOUND", f"TradeTown has no such read surface: {path}")
        if response.status_code == 400:
            raise BoundaryError("INVALID_ARGUMENT", f"TradeTown rejected the read arguments for {path}")
        if response.status_code >= 500:
            raise BoundaryError("UNAVAILABLE", f"TradeTown read failed upstream ({response.status_code})")
        if response.status_code != 200:
            raise BoundaryError("UNAVAILABLE", f"unexpected TradeTown read status {response.status_code}")

        try:
            return response.json()
        except Exception:
            raise BoundaryError("UNAVAILABLE", f"TradeTown returned a non-JSON body for {path}") from None

    async def active_run_id(self) -> str:
        """The run currently loaded into TradeTown's live singleton.

        Used for run binding on every call. Returns the run id or raises;
        never guesses, and never treats an unknown run as a match."""
        payload = await self.get_json("/api/runs/active")
        if not isinstance(payload, dict) or not payload.get("runId"):
            raise BoundaryError(
                "UNAVAILABLE",
                "TradeTown did not report an active run; refusing to serve a read that "
                "cannot be bound to a save slot",
            )
        return str(payload["runId"])
