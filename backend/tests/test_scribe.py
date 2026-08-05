from __future__ import annotations

from app.memory import MAX_MEMORY_RECORDS
from app.schemas import MemoryRecord, ScannerAlert
from app.scribe import record_scanner_alert


def _alert(alert_id: str) -> ScannerAlert:
    return ScannerAlert(
        id=alert_id,
        symbol="NEXA",
        alertType="volume_spike",
        message="Unusual volume detected.",
        detectedBy="pulse",
        createdAt="2026-01-01T00:00:00+00:00",
    )


class TestRecordScannerAlertMaxRecordsPassthrough:
    """Every app/scribe.py wrapper threads its own max_records straight
    through to app/memory.py's record() — this is the representative
    check for Design Bible Chapter 61's max_memory_records CEO control,
    rather than repeating the same pass-through assertion for all 18
    wrappers, since they share the exact same one-line delegation."""

    def test_default_caps_at_max_memory_records(self) -> None:
        memory: list[MemoryRecord] = []
        for i in range(MAX_MEMORY_RECORDS + 5):
            record_scanner_alert(memory, _alert(f"alert-{i}"))
        assert len(memory) == MAX_MEMORY_RECORDS

    def test_ceo_configured_max_records_is_real_and_respected(self) -> None:
        memory: list[MemoryRecord] = []
        for i in range(10):
            record_scanner_alert(memory, _alert(f"alert-{i}"), max_records=3)
        assert len(memory) == 3
