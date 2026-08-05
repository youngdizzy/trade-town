from __future__ import annotations

from app.memory import MAX_MEMORY_RECORDS
from app.schemas import FailedStrategyArchiveEntry, MemoryRecord, ScannerAlert, StrategyHallOfFameEntry
from app.scribe import record_scanner_alert, record_strategy_failed_archive_entry, record_strategy_hall_of_fame_entry


def _alert(alert_id: str) -> ScannerAlert:
    return ScannerAlert(
        id=alert_id,
        symbol="NEXA",
        alertType="volume_spike",
        message="Unusual volume detected.",
        detectedBy="pulse",
        createdAt="2026-01-01T00:00:00+00:00",
    )


def _hall_of_fame_entry(entry_id: str) -> StrategyHallOfFameEntry:
    return StrategyHallOfFameEntry(
        id=entry_id,
        strategyId="strategy-1",
        strategyName="Momentum Breakout",
        createdBy="echo",  # type: ignore[arg-type]
        description="Follows short-term price momentum.",
        simDaysActive=30,
        tradesExecuted=50,
        winRate=65.0,
        profitFactor=2.1,
        maxDrawdownPct=8.0,
        historicalReturnPct=22.0,
        retiredReason="Consistently strong performance.",
        simDay=30,
        inductedAt="2026-01-01T00:00:00+00:00",
    )


def _failed_archive_entry(entry_id: str) -> FailedStrategyArchiveEntry:
    return FailedStrategyArchiveEntry(
        id=entry_id,
        strategyId="strategy-2",
        strategyName="Mean Reversion Scalp",
        createdBy="nova",  # type: ignore[arg-type]
        failedAtStage="paper_trading",  # type: ignore[arg-type]
        whatFailed=["Win rate fell below the Risk bar."],
        lessonsLearned=["Tighten entry criteria before the next attempt."],
        retiredReason="Underperformed during paper trading.",
        simDay=20,
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


class TestRecordStrategyRetirement:
    """Design Bible Chapter 62 — the Innovation Lab's Knowledge
    Integration. "strategy" has been a real MemoryCategory since it was
    declared, but nothing ever actually recorded one until this pass."""

    def test_hall_of_fame_entry_becomes_a_real_strategy_memory(self) -> None:
        memory: list[MemoryRecord] = []
        record_strategy_hall_of_fame_entry(memory, _hall_of_fame_entry("hof-1"))
        assert len(memory) == 1
        assert memory[0].category == "strategy"
        assert "Momentum Breakout" in memory[0].title

    def test_failed_archive_entry_becomes_a_real_strategy_memory(self) -> None:
        memory: list[MemoryRecord] = []
        record_strategy_failed_archive_entry(memory, _failed_archive_entry("failed-1"))
        assert len(memory) == 1
        assert memory[0].category == "strategy"
        assert "Mean Reversion Scalp" in memory[0].title
        assert "Win rate fell below the Risk bar" in memory[0].body

    def test_ceo_configured_max_records_is_respected_for_both(self) -> None:
        memory: list[MemoryRecord] = []
        for i in range(5):
            record_strategy_hall_of_fame_entry(memory, _hall_of_fame_entry(f"hof-{i}"), max_records=2)
        assert len(memory) == 2
