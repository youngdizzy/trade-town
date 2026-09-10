"""Append-only agent-access audit log — the AUTHORITATIVE compliance record
for this boundary.

WHY THIS IS NOT TradeTown's AuditEntry. Verified at HEAD 39bfe9e:
backend/app/schemas.py's AuditEntry is a CEO-facing, in-world, department-
scoped narrative record with no field for an actor, a credential, a tool, a
latency or a digest — and, decisively, it lives INSIDE GameSaveState, so a
save-slot switch would wipe it and every row would pollute game state with
machine telemetry. A machine-access log must outlive run switches and must
never touch game state. That is why this is a separate store, and it is the
only new store this milestone creates.

WHY NOT OpenClaw's ledger. OpenClaw's own documentation states "Absence of a
row proves nothing" and "It is not a lossless compliance archive", with a
30-day / 100,000-row bound. It is correlated telemetry, not the record of
authority. This table is.

APPEND-ONLY. There is no UPDATE and no DELETE path in this module, and the
table is guarded by SQLite triggers that raise on either.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS agent_access_audit (
    event_id            TEXT PRIMARY KEY,
    timestamp           TEXT NOT NULL,
    sim_minutes         INTEGER,
    external_agent_id   TEXT NOT NULL,
    credential_id       TEXT NOT NULL,
    mission_id          TEXT,
    run_id              TEXT,
    tool                TEXT NOT NULL,
    contract_version    TEXT NOT NULL,
    request_metadata    TEXT NOT NULL,
    scope_evaluated     TEXT NOT NULL,
    result_status       TEXT NOT NULL,
    error_code          TEXT,
    result_count        INTEGER,
    data_category       TEXT,
    latency_ms          INTEGER NOT NULL,
    request_digest      TEXT NOT NULL,
    result_digest       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_mission ON agent_access_audit(mission_id);
CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON agent_access_audit(timestamp);

CREATE TRIGGER IF NOT EXISTS agent_access_audit_no_update
BEFORE UPDATE ON agent_access_audit
BEGIN
    SELECT RAISE(ABORT, 'agent_access_audit is append-only');
END;

CREATE TRIGGER IF NOT EXISTS agent_access_audit_no_delete
BEFORE DELETE ON agent_access_audit
BEGIN
    SELECT RAISE(ABORT, 'agent_access_audit is append-only');
END;
"""


def digest(value: Any) -> str:
    """SHA-256 over a canonical JSON encoding.

    Digests give tamper-evidence and reproducibility without storing
    potentially large or sensitive bodies in the ledger."""
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def describe_request(args: dict[str, Any]) -> dict[str, Any]:
    """Field NAMES and value SHAPES only — never free-text argument bodies.

    A research `query` or a mission `objective` can carry arbitrary agent-
    supplied text; recording its type and length is enough to investigate an
    incident without copying attacker-controlled prose into the ledger."""
    described: dict[str, Any] = {}
    for key, value in sorted(args.items()):
        if isinstance(value, bool):
            described[key] = {"type": "bool", "value": value}
        elif isinstance(value, int):
            described[key] = {"type": "int", "value": value}
        elif isinstance(value, str):
            described[key] = {"type": "str", "length": len(value)}
        elif isinstance(value, (list, tuple)):
            described[key] = {"type": "list", "length": len(value)}
        elif value is None:
            described[key] = {"type": "null"}
        else:
            described[key] = {"type": type(value).__name__}
    return described


@dataclass(frozen=True)
class AuditRow:
    external_agent_id: str
    credential_id: str
    tool: str
    contract_version: str
    request_metadata: dict[str, Any]
    scope_evaluated: dict[str, Any]
    result_status: str
    latency_ms: int
    request_digest: str
    result_digest: str
    mission_id: str | None = None
    run_id: str | None = None
    sim_minutes: int | None = None
    error_code: str | None = None
    result_count: int | None = None
    data_category: str | None = None


class AuditLog:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        if db_path != ":memory:":
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def append(self, row: AuditRow) -> str:
        """Write one row and commit. Raises on failure so the caller can fail
        the request closed — an unrecorded read must not be served."""
        event_id = str(uuid.uuid4())
        self._conn.execute(
            """
            INSERT INTO agent_access_audit (
                event_id, timestamp, sim_minutes, external_agent_id, credential_id,
                mission_id, run_id, tool, contract_version, request_metadata,
                scope_evaluated, result_status, error_code, result_count,
                data_category, latency_ms, request_digest, result_digest
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                event_id,
                datetime.now(timezone.utc).isoformat(),
                row.sim_minutes,
                row.external_agent_id,
                row.credential_id,
                row.mission_id,
                row.run_id,
                row.tool,
                row.contract_version,
                json.dumps(row.request_metadata, sort_keys=True),
                json.dumps(row.scope_evaluated, sort_keys=True),
                row.result_status,
                row.error_code,
                row.result_count,
                row.data_category,
                row.latency_ms,
                row.request_digest,
                row.result_digest,
            ),
        )
        self._conn.commit()
        return event_id

    def count(self) -> int:
        cursor = self._conn.execute("SELECT COUNT(*) FROM agent_access_audit")
        return int(cursor.fetchone()[0])

    def rows(self) -> list[sqlite3.Row]:
        self._conn.row_factory = sqlite3.Row
        return list(self._conn.execute("SELECT * FROM agent_access_audit ORDER BY timestamp"))

    def close(self) -> None:
        self._conn.close()
