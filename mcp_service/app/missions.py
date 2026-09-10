"""Mission records and their FROZEN evidence manifests.

DECISION B-2, option (B): the mission carries a self-contained evidence
manifest. No AIEvidencePacket store is created anywhere.

WHY. Verified at HEAD 39bfe9e: backend/app/schemas.py has no
`list[AIEvidencePacket]` field and no packet table. A packet is built
transiently by app/ai_context_builder.py, used for citation validation inside
one call (app/ai_reasoning.py:278 — `valid_ids = {item.id for item in
packet.items}`), and then discarded; only `AIReasoningResult.evidence_packet_id`
survives, as a dangling reference. A mission that referenced a stored packet
would be referencing something that does not exist.

WHAT FROZEN MEANS. The manifest is written once, at mission issuance, and is
the complete, closed universe of citable evidence for that mission. There is
no update path in this module, no MCP tool that accepts manifest input, and a
SQLite trigger that aborts any UPDATE or DELETE. External agents can read a
manifest and cite it; they can never create, extend or modify evidence.

HONEST TRADE. Freezing means a long mission reasons over a snapshot and can
go stale relative to live state. That is the correct trade: it is exactly the
property that makes citations verifiable and hindsight leaks detectable, and
it matches the anti-lookahead discipline this codebase already defends
(commits 9e59f8f, a21b17c, 6691048, 922ee3f).
"""
from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from app.errors import BoundaryError

CONTRACT_VERSION = "v0"
MANIFEST_VERSION = "v0"

# Reuses backend/app/schemas.py::AIEvidenceKind verbatim.
EvidenceKind = Literal["fact", "historical", "knowledge", "unknown"]
# Reuses backend/app/schemas.py::DataCategory verbatim (lowercase).
DataCategory = Literal["real", "synthetic", "simulated", "user_provided", "unavailable"]

VALID_EVIDENCE_KINDS = frozenset({"fact", "historical", "knowledge", "unknown"})
VALID_DATA_CATEGORIES = frozenset({"real", "synthetic", "simulated", "user_provided", "unavailable"})

# v0 permits only these tools. A mission naming anything else is rejected at
# issuance rather than at call time.
KNOWN_TOOLS = frozenset(
    {
        "tt_get_mission",
        "tt_read_market_data",
        "tt_search_approved_research",
        "tt_read_institutional_memory",
        "tt_list_prior_findings",
    }
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS missions (
    mission_id                     TEXT PRIMARY KEY,
    external_agent_id              TEXT NOT NULL,
    run_id                         TEXT NOT NULL,
    objective                      TEXT NOT NULL,
    requested_output_type          TEXT NOT NULL,
    topic_scope                    TEXT NOT NULL,
    market_universe                TEXT NOT NULL,
    allowed_tools                  TEXT NOT NULL,
    knowledge_cutoff_sim_minutes   INTEGER NOT NULL,
    data_freshness_max_age_sim_minutes INTEGER NOT NULL,
    created_at                     TEXT NOT NULL,
    created_at_sim_minutes         INTEGER NOT NULL,
    expires_at                     TEXT NOT NULL,
    max_tool_calls                 INTEGER NOT NULL,
    max_mission_lifetime_seconds   INTEGER NOT NULL,
    simulation_context             TEXT NOT NULL,
    data_provenance_summary        TEXT NOT NULL,
    prohibited_actions             TEXT NOT NULL,
    manifest                       TEXT NOT NULL,
    contract_version               TEXT NOT NULL
);

CREATE TRIGGER IF NOT EXISTS missions_no_update
BEFORE UPDATE ON missions
BEGIN
    SELECT RAISE(ABORT, 'missions are frozen at issuance');
END;

CREATE TRIGGER IF NOT EXISTS missions_no_delete
BEFORE DELETE ON missions
BEGIN
    SELECT RAISE(ABORT, 'missions are frozen at issuance');
END;
"""


@dataclass(frozen=True)
class EvidenceItem:
    """One citable item. `evidence_item_id` is the ONLY handle an agent may
    cite back — the same rule backend/app/schemas.py::AIEvidenceItem states
    for its own `id`."""

    evidence_item_id: str
    kind: EvidenceKind
    label: str
    detail: str
    as_of_sim_minutes: int
    source_kind: str
    source_ref: str
    data_category: DataCategory


@dataclass(frozen=True)
class EvidenceManifest:
    manifest_id: str
    frozen_at: str
    frozen_at_sim_minutes: int
    knowledge_cutoff_sim_minutes: int
    context_builder_version: str
    known_limitations: list[str] = field(default_factory=list)
    items: list[EvidenceItem] = field(default_factory=list)
    manifest_version: str = MANIFEST_VERSION

    def valid_ids(self) -> set[str]:
        return {item.evidence_item_id for item in self.items}

    def validate_citations(self, cited: list[str]) -> list[str]:
        """Return the sorted set of invalid citations.

        Identical algorithm to backend/app/ai_reasoning.py:283, applied
        against the frozen manifest instead of a transient packet."""
        valid = self.valid_ids()
        return sorted({cid for cid in cited if cid not in valid})


@dataclass(frozen=True)
class Mission:
    mission_id: str
    external_agent_id: str
    run_id: str
    objective: str
    requested_output_type: str
    topic_scope: list[str]
    market_universe: list[str]
    allowed_tools: list[str]
    knowledge_cutoff_sim_minutes: int
    data_freshness_max_age_sim_minutes: int
    created_at: str
    created_at_sim_minutes: int
    expires_at: str
    max_tool_calls: int
    max_mission_lifetime_seconds: int
    simulation_context: str
    data_provenance_summary: list[str]
    prohibited_actions: list[str]
    manifest: EvidenceManifest
    contract_version: str = CONTRACT_VERSION

    def is_expired(self, now: datetime | None = None) -> bool:
        moment = now or datetime.now(timezone.utc)
        return moment >= datetime.fromisoformat(self.expires_at)

    def to_public_dict(self) -> dict[str, Any]:
        """The camelCase shape returned by tt_get_mission."""
        return {
            "contractVersion": self.contract_version,
            "missionId": self.mission_id,
            "externalAgentId": self.external_agent_id,
            "runId": self.run_id,
            "objective": self.objective,
            "requestedOutputType": self.requested_output_type,
            "topicScope": list(self.topic_scope),
            "marketUniverse": list(self.market_universe),
            "allowedTools": list(self.allowed_tools),
            "knowledgeCutoffSimMinutes": self.knowledge_cutoff_sim_minutes,
            "dataFreshnessMaxAgeSimMinutes": self.data_freshness_max_age_sim_minutes,
            "createdAt": self.created_at,
            "createdAtSimMinutes": self.created_at_sim_minutes,
            "expiresAt": self.expires_at,
            "maxToolCalls": self.max_tool_calls,
            "maxMissionLifetimeSeconds": self.max_mission_lifetime_seconds,
            "simulationContext": self.simulation_context,
            "dataProvenanceSummary": list(self.data_provenance_summary),
            "prohibitedActions": list(self.prohibited_actions),
            "evidenceManifest": {
                "manifestId": self.manifest.manifest_id,
                "manifestVersion": self.manifest.manifest_version,
                "frozenAt": self.manifest.frozen_at,
                "frozenAtSimMinutes": self.manifest.frozen_at_sim_minutes,
                "knowledgeCutoffSimMinutes": self.manifest.knowledge_cutoff_sim_minutes,
                "contextBuilderVersion": self.manifest.context_builder_version,
                "knownLimitations": list(self.manifest.known_limitations),
                "items": [
                    {
                        "evidenceItemId": item.evidence_item_id,
                        "kind": item.kind,
                        "label": item.label,
                        "detail": item.detail,
                        "asOfSimMinutes": item.as_of_sim_minutes,
                        "sourceKind": item.source_kind,
                        "sourceRef": item.source_ref,
                        "dataCategory": item.data_category,
                    }
                    for item in self.manifest.items
                ],
            },
        }


def validate_manifest(manifest: EvidenceManifest) -> None:
    """Enforce the manifest invariants at freeze time.

    The cutoff invariant is the anti-lookahead boundary: no item may be
    as-of a moment later than the mission's own knowledge cutoff. This is
    the same rule backend/app/schemas.py::AIEvidencePacket states for its
    own items, enforced here at the only moment it can be enforced."""
    seen: set[str] = set()
    for item in manifest.items:
        if not item.evidence_item_id.strip():
            raise BoundaryError("INVALID_ARGUMENT", "evidence item id must be non-empty")
        if item.evidence_item_id in seen:
            raise BoundaryError("INVALID_ARGUMENT", f"duplicate evidence item id: {item.evidence_item_id}")
        seen.add(item.evidence_item_id)
        if item.kind not in VALID_EVIDENCE_KINDS:
            raise BoundaryError("INVALID_ARGUMENT", f"unknown evidence kind: {item.kind}")
        if item.data_category not in VALID_DATA_CATEGORIES:
            raise BoundaryError("INVALID_ARGUMENT", f"unknown data category: {item.data_category}")
        if item.as_of_sim_minutes > manifest.knowledge_cutoff_sim_minutes:
            raise BoundaryError(
                "INVALID_ARGUMENT",
                f"evidence item {item.evidence_item_id} is as-of "
                f"{item.as_of_sim_minutes}, later than the manifest knowledge cutoff "
                f"{manifest.knowledge_cutoff_sim_minutes}",
            )


def validate_mission(mission: Mission) -> None:
    if not mission.mission_id.strip():
        raise BoundaryError("INVALID_ARGUMENT", "missionId must be non-empty")
    unknown = sorted(set(mission.allowed_tools) - KNOWN_TOOLS)
    if unknown:
        raise BoundaryError("INVALID_ARGUMENT", f"unknown tools in allowedTools: {', '.join(unknown)}")
    if mission.manifest.knowledge_cutoff_sim_minutes != mission.knowledge_cutoff_sim_minutes:
        raise BoundaryError(
            "INVALID_ARGUMENT",
            "manifest knowledgeCutoffSimMinutes must equal the mission's own cutoff",
        )
    if mission.simulation_context != "paper_simulated":
        raise BoundaryError(
            "INVALID_ARGUMENT",
            "simulationContext must be 'paper_simulated' — this codebase has no live mode",
        )
    validate_manifest(mission.manifest)


class MissionStore:
    def __init__(self, db_path: str) -> None:
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def issue(self, mission: Mission) -> None:
        """Write a mission once. Issuance is TradeTown-side; no MCP tool
        reaches this method."""
        validate_mission(mission)
        try:
            self._conn.execute(
                """
                INSERT INTO missions (
                    mission_id, external_agent_id, run_id, objective,
                    requested_output_type, topic_scope, market_universe,
                    allowed_tools, knowledge_cutoff_sim_minutes,
                    data_freshness_max_age_sim_minutes, created_at,
                    created_at_sim_minutes, expires_at, max_tool_calls,
                    max_mission_lifetime_seconds, simulation_context,
                    data_provenance_summary, prohibited_actions, manifest,
                    contract_version
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    mission.mission_id,
                    mission.external_agent_id,
                    mission.run_id,
                    mission.objective,
                    mission.requested_output_type,
                    json.dumps(mission.topic_scope),
                    json.dumps(mission.market_universe),
                    json.dumps(mission.allowed_tools),
                    mission.knowledge_cutoff_sim_minutes,
                    mission.data_freshness_max_age_sim_minutes,
                    mission.created_at,
                    mission.created_at_sim_minutes,
                    mission.expires_at,
                    mission.max_tool_calls,
                    mission.max_mission_lifetime_seconds,
                    mission.simulation_context,
                    json.dumps(mission.data_provenance_summary),
                    json.dumps(mission.prohibited_actions),
                    json.dumps(
                        {
                            "manifestId": mission.manifest.manifest_id,
                            "manifestVersion": mission.manifest.manifest_version,
                            "frozenAt": mission.manifest.frozen_at,
                            "frozenAtSimMinutes": mission.manifest.frozen_at_sim_minutes,
                            "knowledgeCutoffSimMinutes": mission.manifest.knowledge_cutoff_sim_minutes,
                            "contextBuilderVersion": mission.manifest.context_builder_version,
                            "knownLimitations": mission.manifest.known_limitations,
                            "items": [asdict(item) for item in mission.manifest.items],
                        }
                    ),
                    mission.contract_version,
                ),
            )
            self._conn.commit()
        except sqlite3.IntegrityError as exc:
            raise BoundaryError("INVALID_ARGUMENT", f"mission already exists: {mission.mission_id}") from exc

    def get(self, mission_id: str) -> Mission:
        row = self._conn.execute("SELECT * FROM missions WHERE mission_id = ?", (mission_id,)).fetchone()
        if row is None:
            raise BoundaryError("NOT_FOUND", f"no such mission: {mission_id}")
        raw_manifest = json.loads(row["manifest"])
        manifest = EvidenceManifest(
            manifest_id=raw_manifest["manifestId"],
            manifest_version=raw_manifest["manifestVersion"],
            frozen_at=raw_manifest["frozenAt"],
            frozen_at_sim_minutes=raw_manifest["frozenAtSimMinutes"],
            knowledge_cutoff_sim_minutes=raw_manifest["knowledgeCutoffSimMinutes"],
            context_builder_version=raw_manifest["contextBuilderVersion"],
            known_limitations=list(raw_manifest["knownLimitations"]),
            items=[EvidenceItem(**item) for item in raw_manifest["items"]],
        )
        return Mission(
            mission_id=row["mission_id"],
            external_agent_id=row["external_agent_id"],
            run_id=row["run_id"],
            objective=row["objective"],
            requested_output_type=row["requested_output_type"],
            topic_scope=json.loads(row["topic_scope"]),
            market_universe=json.loads(row["market_universe"]),
            allowed_tools=json.loads(row["allowed_tools"]),
            knowledge_cutoff_sim_minutes=row["knowledge_cutoff_sim_minutes"],
            data_freshness_max_age_sim_minutes=row["data_freshness_max_age_sim_minutes"],
            created_at=row["created_at"],
            created_at_sim_minutes=row["created_at_sim_minutes"],
            expires_at=row["expires_at"],
            max_tool_calls=row["max_tool_calls"],
            max_mission_lifetime_seconds=row["max_mission_lifetime_seconds"],
            simulation_context=row["simulation_context"],
            data_provenance_summary=json.loads(row["data_provenance_summary"]),
            prohibited_actions=json.loads(row["prohibited_actions"]),
            manifest=manifest,
            contract_version=row["contract_version"],
        )

    def close(self) -> None:
        self._conn.close()
