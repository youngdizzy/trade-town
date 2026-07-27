"""Covers app/trade_notifications.py — v0.6.2 Phase 10. This module only
tracks which real closed trades' outcome popups have been acknowledged;
the popup content itself is a direct read of the real PaperTrade, not
duplicated or fabricated here.
"""
from __future__ import annotations

from app.trade_notifications import MAX_VIEWED_IDS, mark_viewed


def test_mark_viewed_adds_a_new_id():
    result = mark_viewed([], "trade-1")
    assert result == ["trade-1"]


def test_mark_viewed_does_not_duplicate_an_existing_id():
    result = mark_viewed(["trade-1"], "trade-1")
    assert result == ["trade-1"]


def test_mark_viewed_caps_at_max_viewed_ids_oldest_first():
    ids = [f"trade-{i}" for i in range(MAX_VIEWED_IDS)]
    result = mark_viewed(ids, "trade-new")
    assert len(result) == MAX_VIEWED_IDS
    assert result[-1] == "trade-new"
    assert "trade-0" not in result  # oldest evicted
