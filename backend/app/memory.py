"""CompanyMemory — TradeTown's searchable long-term log.

Every manager that produces something worth remembering (research
completions, meeting minutes, discoveries, ...) appends through
`record()` rather than building MemoryRecord objects itself, so the id
format and the history cap live in exactly one place. `record()` mutates
`memory` in place, matching how `tasks`/`news` are already threaded
through app/nexus.py's tick — callers don't need to rebind the list.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import MemoryCategory, MemoryRecord

MAX_MEMORY_RECORDS = 200


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def record(
    memory: list[MemoryRecord], category: MemoryCategory, title: str, body: str, max_records: int = MAX_MEMORY_RECORDS
) -> None:
    now = _now_iso()
    memory.append(MemoryRecord(id=f"memory-{category}-{now}", category=category, title=title, body=body, timestamp=now))
    if len(memory) > max_records:
        del memory[: len(memory) - max_records]


def search(memory: list[MemoryRecord], query: str = "", category: MemoryCategory | None = None) -> list[MemoryRecord]:
    """Filters an already-loaded memory list. Exposed as a plain function
    (rather than a REST endpoint) because the frontend currently filters
    the WS-synced memory list client-side — this exists mainly so a
    future search endpoint has an obvious, already-tested place to call
    into rather than reimplementing the filter."""
    results = memory
    if category is not None:
        results = [m for m in results if m.category == category]
    if query:
        needle = query.lower()
        results = [m for m in results if needle in m.title.lower() or needle in m.body.lower()]
    return results
