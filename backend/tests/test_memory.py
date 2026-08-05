from __future__ import annotations

from app.memory import MAX_MEMORY_RECORDS, record
from app.schemas import MemoryRecord


class TestRecord:
    def test_caps_at_max_memory_records_oldest_evicted_first(self) -> None:
        memory: list[MemoryRecord] = []
        for i in range(MAX_MEMORY_RECORDS + 10):
            record(memory, "event", f"Event {i}", f"body {i}")
        assert len(memory) == MAX_MEMORY_RECORDS
        assert memory[-1].title == f"Event {MAX_MEMORY_RECORDS + 9}"
        assert memory[0].title == "Event 10"

    def test_ceo_configured_max_records_caps_at_a_lower_real_ceiling(self) -> None:
        memory: list[MemoryRecord] = []
        for i in range(15):
            record(memory, "event", f"Event {i}", f"body {i}", max_records=5)
        assert len(memory) == 5
        assert memory[-1].title == "Event 14"
        assert memory[0].title == "Event 10"

    def test_ceo_configured_max_records_allows_a_higher_real_ceiling(self) -> None:
        memory: list[MemoryRecord] = []
        for i in range(MAX_MEMORY_RECORDS + 10):
            record(memory, "event", f"Event {i}", f"body {i}", max_records=MAX_MEMORY_RECORDS + 5)
        assert len(memory) == MAX_MEMORY_RECORDS + 5
        assert memory[0].title == "Event 5"
