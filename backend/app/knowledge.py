"""KnowledgeManager — turns a closed paper trade into a distilled lesson
or mistake, and provides the "searchable knowledge base" view over
CompanyMemory called for in the v0.5 brief's Feature 9.

This module never writes to CompanyMemory itself — app/scribe.py remains
the sole write gateway (see app/memory.py's module docstring), the same
"one writer, many readers/derivers" shape research.py/discussion.py
already follow for Scribe. knowledge.py only derives text; scribe.py
decides to record it.
"""
from __future__ import annotations

from app.memory import search as memory_search
from app.schemas import MemoryCategory, MemoryRecord, PaperTrade

# Categories that represent distilled knowledge rather than a raw
# activity log — the subset CompanyMemory's viewer can filter to when the
# player wants "what has TradeTown learned" rather than "what happened."
KNOWLEDGE_CATEGORIES: tuple[MemoryCategory, ...] = ("lesson", "mistake", "strategy", "coach_review")


def derive_lesson(trade: PaperTrade) -> tuple[MemoryCategory, str, str]:
    """Returns (category, title, body) for a closed paper trade — a
    winning trade becomes a "lesson", a losing one a "mistake". Pure text
    derivation; the caller (app/scribe.py) decides whether/how to record
    it."""
    won = trade.pnl > 0
    category: MemoryCategory = "lesson" if won else "mistake"
    verb = "gained" if won else "lost"
    title = f"{'Lesson' if won else 'Mistake'}: {trade.symbol} {trade.side}"
    outcome = "The thesis held." if won else "The thesis did not hold — reassess similar setups before sizing up again."
    body = (
        f"{trade.symbol} {verb} {abs(trade.pnl_pct):.1f}% over a {trade.duration_minutes}-minute simulated hold "
        f"(opened at {trade.confidence:.0f}% confidence). {trade.market_conditions} {outcome}"
    )
    return category, title, body


def search_knowledge(memory: list[MemoryRecord], query: str = "") -> list[MemoryRecord]:
    """Scopes CompanyMemory's existing search() to the knowledge
    categories only — everything is still stored in the one CompanyMemory
    list (see app/memory.py); this is a filtered view, not a second
    store."""
    results: list[MemoryRecord] = []
    for category in KNOWLEDGE_CATEGORIES:
        results.extend(memory_search(memory, query, category))
    results.sort(key=lambda r: r.timestamp, reverse=True)
    return results
