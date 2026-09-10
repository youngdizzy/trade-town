"""MCP server wiring — the only module that touches the MCP SDK.

Everything with logic in it (tools.py, missions.py, audit.py, auth.py) is
plain Python and is unit-tested without the SDK. This module is deliberately
thin: it registers five tools, builds the SDK's Starlette app, and wraps that
app in bearer authentication.

AUTH RUNS FIRST, STRUCTURALLY. BearerAuthMiddleware wraps the application
returned by MCPServer.streamable_http_app(), so an unauthenticated request is
rejected before the MCP transport parses it and therefore before any tool
function exists in the call stack.

NOT PUBLISHED. docker-compose.yml gives this service no host port. Connecting
it to OpenClaw is a separate, later milestone.
"""
from __future__ import annotations

import logging
from typing import Any

from mcp.server import MCPServer

from app.auth import BearerAuthMiddleware
from app.audit import AuditLog
from app.config import Settings, load_settings
from app.errors import BoundaryError
from app.missions import MissionStore
from app.redaction import redact, register_secret
from app.tools import Boundary
from app.tradetown_client import TradeTownReadClient

logger = logging.getLogger("tradetown.mcp")

SERVER_NAME = "tradetown-readonly"
SERVER_VERSION = "1.0.0"

# Tool descriptions are fixed text. They are NEVER built from TradeTown data
# or from agent input — the same rule backend/app/ai_reasoning.py states for
# its own system prompts.
TOOL_DESCRIPTIONS = {
    "tt_get_mission": (
        "Read-only. Return the current mission assignment, its frozen evidence "
        "manifest, its knowledge cutoff, and its prohibited actions."
    ),
    "tt_read_market_data": (
        "Read-only. Return OHLCV candles for one symbol inside the mission's "
        "market universe, preserving each candle's own data-status provenance. "
        "Market data in this deployment is simulated, not real."
    ),
    "tt_search_approved_research": (
        "Read-only. Search research records TradeTown has explicitly approved "
        "for external-agent reading. Unapproved research is never returned."
    ),
    "tt_read_institutional_memory": (
        "Read-only. Read the approved slice of TradeTown institutional memory "
        "within the mission's topic scope."
    ),
    "tt_list_prior_findings": (
        "Read-only. List this agent's own prior findings for continuity and "
        "calibration. Never returns another agent's reasoning."
    ),
}


def build_boundary(settings: Settings) -> Boundary:
    register_secret(settings.bearer_token)
    return Boundary(
        settings=settings,
        client=TradeTownReadClient(
            settings.tradetown_read_base_url, timeout_seconds=settings.request_timeout_seconds
        ),
        missions=MissionStore(settings.db_path),
        audit_log=AuditLog(settings.db_path),
    )


def build_server(boundary: Boundary) -> MCPServer:
    server: MCPServer = MCPServer(name=SERVER_NAME, version=SERVER_VERSION)

    async def _call(tool: str, args: dict[str, Any]) -> dict[str, Any]:
        try:
            return await boundary.invoke(tool, args)
        except BoundaryError as err:
            # Errors are returned as structured data, never raised as opaque
            # tracebacks, and always pass through redaction first.
            logger.info("mcp tool refused: %s", redact(str(err)))
            return BoundaryError(err.code, redact(err.message)).to_payload()

    @server.tool(name="tt_get_mission", description=TOOL_DESCRIPTIONS["tt_get_mission"])
    async def tt_get_mission(missionId: str) -> dict[str, Any]:  # noqa: N803 - MCP wire name
        return await _call("tt_get_mission", {"missionId": missionId})

    @server.tool(name="tt_read_market_data", description=TOOL_DESCRIPTIONS["tt_read_market_data"])
    async def tt_read_market_data(  # noqa: N803 - MCP wire names
        missionId: str, symbol: str, timeframe: str, limit: int | None = None
    ) -> dict[str, Any]:
        return await _call(
            "tt_read_market_data",
            {"missionId": missionId, "symbol": symbol, "timeframe": timeframe, "limit": limit},
        )

    @server.tool(
        name="tt_search_approved_research", description=TOOL_DESCRIPTIONS["tt_search_approved_research"]
    )
    async def tt_search_approved_research(  # noqa: N803
        missionId: str, query: str, symbol: str | None = None, limit: int | None = None
    ) -> dict[str, Any]:
        return await _call(
            "tt_search_approved_research",
            {"missionId": missionId, "query": query, "symbol": symbol, "limit": limit},
        )

    @server.tool(
        name="tt_read_institutional_memory",
        description=TOOL_DESCRIPTIONS["tt_read_institutional_memory"],
    )
    async def tt_read_institutional_memory(  # noqa: N803
        missionId: str,
        topics: list[str] | None = None,
        source: str | None = None,
        marketRegime: str | None = None,
        symbol: str | None = None,
        limit: int | None = None,
    ) -> dict[str, Any]:
        return await _call(
            "tt_read_institutional_memory",
            {
                "missionId": missionId,
                "topics": topics,
                "source": source,
                "marketRegime": marketRegime,
                "symbol": symbol,
                "limit": limit,
            },
        )

    @server.tool(name="tt_list_prior_findings", description=TOOL_DESCRIPTIONS["tt_list_prior_findings"])
    async def tt_list_prior_findings(missionId: str, limit: int | None = None) -> dict[str, Any]:  # noqa: N803
        return await _call("tt_list_prior_findings", {"missionId": missionId, "limit": limit})

    return server


def build_app(settings: Settings | None = None) -> Any:
    resolved = settings or load_settings()
    boundary = build_boundary(resolved)
    server = build_server(boundary)
    inner = server.streamable_http_app(host=resolved.host)
    return BearerAuthMiddleware(inner, expected_token=resolved.bearer_token)


def main() -> None:
    import uvicorn

    logging.basicConfig(level=logging.INFO)
    resolved = load_settings()
    register_secret(resolved.bearer_token)
    logger.info(
        "MCP boundary starting: agent=%s read_base=%s credential=%s",
        resolved.external_agent_id,
        resolved.tradetown_read_base_url,
        resolved.credential_id,  # digest reference, never the credential
    )
    uvicorn.run(build_app(resolved), host=resolved.host, port=resolved.port, log_level="info")


if __name__ == "__main__":
    main()
