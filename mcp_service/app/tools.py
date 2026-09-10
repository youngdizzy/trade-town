"""The five read-only MCP tools.

Every tool runs the same fixed policy chain before it reads anything:

    1. mission exists                -> NOT_FOUND
    2. mission belongs to this agent -> FORBIDDEN
    3. mission not expired           -> EXPIRED
    4. tool in mission.allowed_tools -> FORBIDDEN   (deny by default)
    5. TradeTown's active run == mission.run_id -> RUN_MISMATCH
    6. per-tool scope checks         -> OUT_OF_SCOPE
    7. read
    8. audit row written BEFORE the result is returned; a failed audit write
       fails the call closed.

MUTATION-FREE BY CONSTRUCTION. This module imports exactly one outbound
capability — TradeTownReadClient — whose only request method is GET against a
fixed path allowlist. There is no code path from any tool to a write, and no
tool accepts a path, filename, SQL fragment, module name, or any other
identifier that selects code rather than data.

AGENT INPUT IS DATA, NEVER INSTRUCTION. Every string an agent supplies is
validated against a closed set or a strict pattern and then passed as a query
parameter value. Nothing is interpolated into an identifier, evaluated, or
matched against an action vocabulary.
"""
from __future__ import annotations

import json
import re
import time
from datetime import datetime, timezone
from typing import Any

from app.audit import AuditLog, AuditRow, describe_request, digest
from app.config import Settings
from app.errors import BoundaryError
from app.missions import CONTRACT_VERSION, Mission, MissionStore
from app.tradetown_client import TradeTownReadClient

MAX_RESPONSE_BYTES = 256 * 1024
SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9.\-]{1,24}$")
MISSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,128}$")

MARKET_DATA_MAX_LIMIT = 500
RESEARCH_MAX_LIMIT = 50
MEMORY_MAX_LIMIT = 50
FINDINGS_MAX_LIMIT = 25


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _validate_mission_id(mission_id: str) -> str:
    if not MISSION_ID_PATTERN.match(mission_id or ""):
        raise BoundaryError("INVALID_ARGUMENT", "missionId must match ^[A-Za-z0-9_-]{1,128}$")
    return mission_id


def _validate_symbol(symbol: str) -> str:
    if not SYMBOL_PATTERN.match(symbol or ""):
        raise BoundaryError("INVALID_ARGUMENT", "symbol must match ^[A-Za-z0-9.-]{1,24}$")
    return symbol


def _bounded_limit(value: int | None, default: int, maximum: int) -> int:
    if value is None:
        return default
    if not isinstance(value, int) or isinstance(value, bool):
        raise BoundaryError("INVALID_ARGUMENT", "limit must be an integer")
    if value < 1 or value > maximum:
        raise BoundaryError("INVALID_ARGUMENT", f"limit must be between 1 and {maximum}")
    return value


class Boundary:
    """Holds the boundary's collaborators and enforces the policy chain."""

    def __init__(
        self,
        *,
        settings: Settings,
        client: TradeTownReadClient,
        missions: MissionStore,
        audit_log: AuditLog,
    ) -> None:
        self._settings = settings
        self._client = client
        self._missions = missions
        self._audit = audit_log

    # ---------------------------------------------------------------- policy

    async def _authorize(self, tool: str, mission_id: str) -> tuple[Mission, str]:
        """Steps 1-5. Returns the mission and TradeTown's active run id."""
        _validate_mission_id(mission_id)
        mission = self._missions.get(mission_id)

        if mission.external_agent_id != self._settings.external_agent_id:
            # Do not disclose that the mission exists for another agent.
            raise BoundaryError("NOT_FOUND", f"no such mission: {mission_id}")

        if mission.is_expired():
            raise BoundaryError("EXPIRED", f"mission {mission_id} expired at {mission.expires_at}")

        if tool not in mission.allowed_tools:
            raise BoundaryError("FORBIDDEN", f"tool {tool} is not granted by mission {mission_id}")

        active_run = await self._client.active_run_id()
        if active_run != mission.run_id:
            raise BoundaryError(
                "RUN_MISMATCH",
                f"mission {mission_id} is bound to run {mission.run_id} but TradeTown's "
                f"active run is {active_run}; refusing to read another save's data",
            )

        return mission, active_run

    async def invoke(self, tool: str, args: dict[str, Any]) -> dict[str, Any]:
        """Run one tool end to end, auditing before returning."""
        started = time.perf_counter()
        mission_id = str(args.get("missionId", ""))
        run_id: str | None = None
        mission: Mission | None = None
        scope: dict[str, Any] = {}
        try:
            mission, run_id = await self._authorize(tool, mission_id)
            scope = {
                "toolGranted": True,
                "runBound": True,
                "cutoffSimMinutes": mission.knowledge_cutoff_sim_minutes,
            }
            handler = getattr(self, f"_{tool}")
            result = await handler(mission, args)
            self._assert_size(result)
            self._write_audit(
                tool=tool,
                args=args,
                mission=mission,
                run_id=run_id,
                scope=scope,
                status="ok",
                error_code=None,
                result=result,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
            return result
        except BoundaryError as err:
            self._write_audit(
                tool=tool,
                args=args,
                mission=mission,
                run_id=run_id,
                scope=scope or {"denied": err.code},
                status="denied" if err.status in (401, 403, 404, 409, 410, 422) else "error",
                error_code=err.code,
                result=None,
                latency_ms=int((time.perf_counter() - started) * 1000),
            )
            raise

    def _assert_size(self, result: dict[str, Any]) -> None:
        encoded = json.dumps(result, default=str).encode("utf-8")
        if len(encoded) > MAX_RESPONSE_BYTES:
            raise BoundaryError(
                "RESULT_TOO_LARGE",
                f"result is {len(encoded)} bytes, over the {MAX_RESPONSE_BYTES}-byte cap; "
                "narrow the request rather than receiving a truncated answer",
            )

    def _write_audit(
        self,
        *,
        tool: str,
        args: dict[str, Any],
        mission: Mission | None,
        run_id: str | None,
        scope: dict[str, Any],
        status: str,
        error_code: str | None,
        result: dict[str, Any] | None,
        latency_ms: int,
    ) -> None:
        """A failed audit write raises, which fails the call closed — an
        unrecorded read is never served."""
        self._audit.append(
            AuditRow(
                external_agent_id=self._settings.external_agent_id,
                credential_id=self._settings.credential_id,
                tool=tool,
                contract_version=CONTRACT_VERSION,
                request_metadata=describe_request(args),
                scope_evaluated=scope,
                result_status=status,
                error_code=error_code,
                result_count=(result or {}).get("resultCount") if result else None,
                data_category=(result or {}).get("dataCategory") if result else None,
                latency_ms=latency_ms,
                request_digest=digest(describe_request(args)),
                result_digest=digest(result),
                mission_id=mission.mission_id if mission else (args.get("missionId") or None),
                run_id=run_id,
                sim_minutes=(result or {}).get("asOfSimMinutes") if result else None,
            )
        )

    # ----------------------------------------------------------------- tools

    async def _tt_get_mission(self, mission: Mission, args: dict[str, Any]) -> dict[str, Any]:
        payload = mission.to_public_dict()
        payload.update(
            {
                "dataCategory": "simulated",
                "resultCount": 1,
                "retrievedAt": _now_iso(),
                "asOfSimMinutes": mission.knowledge_cutoff_sim_minutes,
            }
        )
        return payload

    async def _tt_read_market_data(self, mission: Mission, args: dict[str, Any]) -> dict[str, Any]:
        symbol = _validate_symbol(str(args.get("symbol", "")))
        if symbol not in mission.market_universe:
            raise BoundaryError(
                "OUT_OF_SCOPE", f"symbol {symbol} is not in this mission's market universe"
            )
        timeframe = str(args.get("timeframe", ""))
        if not timeframe:
            raise BoundaryError("INVALID_ARGUMENT", "timeframe is required")

        supported = await self._client.get_json("/api/market/timeframes")
        if timeframe not in supported:
            raise BoundaryError(
                "INVALID_ARGUMENT",
                f"unsupported timeframe {timeframe}; supported: {', '.join(map(str, supported))}",
            )

        limit = _bounded_limit(args.get("limit"), 100, MARKET_DATA_MAX_LIMIT)
        candles = await self._client.get_json(
            "/api/market/candles", {"symbol": symbol, "timeframe": timeframe, "limit": limit}
        )
        provenance = await self._client.get_json("/api/market/data-provenance")

        # Provenance is preserved, never upgraded. Each candle keeps its own
        # dataStatus from the provider; the envelope reports the honest
        # source category. This codebase's process-wide provider is the mock
        # generator (backend/app/market_data.py::_select_provider), so
        # claiming "real" here would be a fabrication.
        statuses = sorted({str(c.get("dataStatus")) for c in candles}) if candles else []
        return {
            "contractVersion": CONTRACT_VERSION,
            "simulationContext": mission.simulation_context,
            "runId": mission.run_id,
            "symbol": symbol,
            "timeframe": timeframe,
            "candles": candles,
            "candleCount": len(candles),
            "requestedLimit": limit,
            "complete": len(candles) >= limit,
            "candleDataStatuses": statuses,
            "dataCategory": self._market_data_category(provenance),
            "dataProvenanceSources": provenance.get("sources", []) if isinstance(provenance, dict) else [],
            "knowledgeCutoffSimMinutes": mission.knowledge_cutoff_sim_minutes,
            "asOfSimMinutes": mission.knowledge_cutoff_sim_minutes,
            "resultCount": len(candles),
            "retrievedAt": _now_iso(),
        }

    @staticmethod
    def _market_data_category(provenance: Any) -> str:
        """Read the honest category off TradeTown's own DataProvenanceReport.

        Never defaults to "real". If the report cannot be read or does not
        name a quotes/candles subsystem, the answer is "unavailable" — an
        honest unknown, not an optimistic guess."""
        if not isinstance(provenance, dict):
            return "unavailable"
        for source in provenance.get("sources", []):
            if not isinstance(source, dict):
                continue
            subsystem = str(source.get("subsystem", "")).lower()
            if "quote" in subsystem or "candle" in subsystem:
                return str(source.get("category", "unavailable"))
        return "unavailable"

    async def _tt_search_approved_research(self, mission: Mission, args: dict[str, Any]) -> dict[str, Any]:
        query = str(args.get("query", ""))
        if not 1 <= len(query) <= 256:
            raise BoundaryError("INVALID_ARGUMENT", "query must be 1..256 characters")
        symbol = args.get("symbol")
        if symbol is not None:
            symbol = _validate_symbol(str(symbol))
            if symbol not in mission.market_universe:
                raise BoundaryError("OUT_OF_SCOPE", f"symbol {symbol} is not in this mission's universe")
        limit = _bounded_limit(args.get("limit"), 20, RESEARCH_MAX_LIMIT)

        payload = await self._client.get_json(
            "/api/mcp-read/approved-research",
            {
                "knowledgeCutoffSimMinutes": mission.knowledge_cutoff_sim_minutes,
                "symbol": symbol,
                "limit": limit,
            },
        )
        # `query` is a data-side filter applied to already-approved,
        # already-cutoff-filtered records. It is a substring match over
        # allowlisted text fields — never interpolated into an identifier.
        needle = query.lower()
        results = [
            item
            for item in payload.get("results", [])
            if needle in str(item.get("title", "")).lower() or needle in str(item.get("summary", "")).lower()
        ]
        payload["results"] = results
        payload["resultCount"] = len(results)
        payload["queryApplied"] = "substring match over title and summary"
        return payload

    async def _tt_read_institutional_memory(self, mission: Mission, args: dict[str, Any]) -> dict[str, Any]:
        topics = args.get("topics") or []
        if not isinstance(topics, list):
            raise BoundaryError("INVALID_ARGUMENT", "topics must be a list of strings")
        out_of_scope = [t for t in topics if t not in mission.topic_scope]
        if out_of_scope:
            raise BoundaryError(
                "OUT_OF_SCOPE", f"topics outside this mission's scope: {', '.join(map(str, out_of_scope))}"
            )
        symbol = args.get("symbol")
        if symbol is not None:
            symbol = _validate_symbol(str(symbol))
        limit = _bounded_limit(args.get("limit"), 20, MEMORY_MAX_LIMIT)

        return await self._client.get_json(
            "/api/mcp-read/approved-memory",
            {
                "knowledgeCutoffSimMinutes": mission.knowledge_cutoff_sim_minutes,
                "source": args.get("source"),
                "marketRegime": args.get("marketRegime"),
                "symbol": symbol,
                "limit": limit,
            },
        )

    async def _tt_list_prior_findings(self, mission: Mission, args: dict[str, Any]) -> dict[str, Any]:
        """Scope is derived from the credential, never from a caller-supplied
        identity — there is deliberately no agentId parameter."""
        limit = _bounded_limit(args.get("limit"), 10, FINDINGS_MAX_LIMIT)
        return await self._client.get_json(
            "/api/mcp-read/agent-findings",
            {
                "externalAgentId": self._settings.external_agent_id,
                "knowledgeCutoffSimMinutes": mission.knowledge_cutoff_sim_minutes,
                "limit": limit,
            },
        )
