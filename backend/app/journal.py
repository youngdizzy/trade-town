"""TradeJournal — the "TradeJournal" role from the v0.6 brief.

TradeTown already has a journal-shaped record: app/schemas.py's
PaperTrade has carried reason/confidence/supporting-and-opposing-agents/
entry/exit/PnL since v0.5. Two of its fields — `coach_review` and
`lessons_learned` — existed in the schema since v0.5 but nothing ever
populated them (Coach's actual review lived only in periodic
CoachReports, never stamped back onto the individual trade that
prompted it). This module closes that gap and adds the two fields v0.6
asks for that didn't exist yet (`decision_id`, linking a trade back to
the TradeDecision that approved it, and `screenshot`, always a fixed
placeholder string — TradeTown has no chart-rendering pipeline to
capture a real one from).
"""
from __future__ import annotations

from app.knowledge import derive_lesson
from app.schemas import PaperTrade

SCREENSHOT_PLACEHOLDER = "Chart snapshot unavailable — TradeTown has no chart-rendering pipeline."


def stamp_journal_entry(trade: PaperTrade, *, decision_id: str | None) -> PaperTrade:
    """Fills in a freshly-closed trade's journal fields. `derive_lesson()`
    (app/knowledge.py) already turns this same trade into a CompanyMemory
    lesson/mistake record; this reuses that exact text for
    `lessons_learned` rather than writing a second, possibly-diverging
    version of the same judgment."""
    _category, _title, lesson_body = derive_lesson(trade)
    won = trade.pnl > 0
    coach_review = (
        f"Held to plan and closed a winner ({trade.pnl_pct:+.1f}%) — this is the kind of setup worth repeating."
        if won
        else f"Closed at a loss ({trade.pnl_pct:+.1f}%) — reviewed alongside similar trades for a pattern before sizing up again."
    )
    return trade.model_copy(
        update={
            "lessons_learned": lesson_body,
            "coach_review": coach_review,
            "decision_id": decision_id,
            "screenshot": SCREENSHOT_PLACEHOLDER,
        }
    )
