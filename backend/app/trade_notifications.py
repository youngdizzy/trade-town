"""Trade outcome notifications (v0.6.2 Phase 10) — tracks which real,
already-closed PaperTrade ids have had their outcome popup shown, so a
page refresh or Docker restart never re-shows one the player already
saw. Everything the popup itself displays (symbol, pnl, reason,
coach_review, lessons_learned) already exists on the real PaperTrade
record (see app/journal.py) — this module only tracks acknowledgement,
it doesn't compute or store any new trade data.

Win/loss/breakeven and the "thesis confirmed/invalidated/neutral"
classification are both a direct, honest read of the trade's own real
pnl sign — computed client-side from data already present, not
duplicated here as a second source of truth.
"""
from __future__ import annotations

# A little larger than portfolio.py's own MAX_TRADE_HISTORY (50), so a
# popup for any trade still present in history can always be recorded as
# viewed without evicting a still-relevant id.
MAX_VIEWED_IDS = 60


def mark_viewed(viewed_ids: list[str], trade_id: str) -> list[str]:
    if trade_id in viewed_ids:
        return viewed_ids
    updated = [*viewed_ids, trade_id]
    if len(updated) > MAX_VIEWED_IDS:
        del updated[: len(updated) - MAX_VIEWED_IDS]
    return updated
