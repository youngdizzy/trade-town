"""Covers app/research.py's rotation pool — Professional Quant Trading
Core Phase A/C closed a real, previously self-disclosed gap: research.py
used to rotate researchers through app/watchlist.py's fixed SEED_SYMBOLS
constant only, so a symbol added via the "watch_symbol" Agent Energy
spend (app/watchlist.py's EXTRA_SYMBOL_POOL) got real live price
tracking but could never be assigned a researcher — and therefore could
never produce a ResearchItem or, downstream, a TradeProposal. These
tests confirm the rotation now genuinely reflects whatever's on the
current watchlist, and that every existing caller that doesn't pass a
watchlist keeps the original SEED_SYMBOLS-only behavior unchanged."""
from __future__ import annotations

from app.research import RESEARCHER_IDS, default_research, tick_research
from app.schemas import ResearchItem
from app.watchlist import EXTRA_SYMBOL_POOL, SEED_SYMBOLS, WatchlistEntry, default_watchlist


def _watchlist_entry(symbol: str, name: str) -> WatchlistEntry:
    return WatchlistEntry(symbol=symbol, name=name, lastPrice=100.0, dailyChangePct=0.0, status="queued", researchProgress=0.0, assignedAgent=None)


def _completed_item(agent_id: str, symbol: str) -> ResearchItem:
    return ResearchItem(
        id=f"research-{agent_id}-{symbol}",
        title="test research",
        symbol=symbol,
        category="company",  # type: ignore[arg-type]
        priority="normal",
        status="completed",
        assignedAgent=agent_id,  # type: ignore[arg-type]
        summary="done",
        confidence=100.0,
        createdAt="2026-01-01T00:00:00+00:00",
        updatedAt="2026-01-01T00:00:00+00:00",
    )


class TestDefaultResearchWithoutWatchlist:
    def test_no_watchlist_argument_stays_seed_symbols_only(self) -> None:
        seed_symbols = {s[0] for s in SEED_SYMBOLS}
        items = default_research()
        assert all(item.symbol in seed_symbols for item in items)


class TestRotationDrawsFromTheRealWatchlist:
    def test_a_symbol_only_in_extra_pool_can_be_assigned_once_watchlisted(self) -> None:
        # AMZN is EXTRA_SYMBOL_POOL-only — not reachable via the old
        # SEED_SYMBOLS-only rotation.
        amzn = next(s for s in EXTRA_SYMBOL_POOL if s[0] == "AMZN")
        watchlist = [_watchlist_entry(amzn[0], amzn[1])]
        research: list[ResearchItem] = []

        # Every researcher must rotate onto AMZN — it's the only entry
        # on this watchlist, so if the rotation still only knew about
        # SEED_SYMBOLS this would KeyError or silently ignore watchlist.
        updated, _completed = tick_research(research, watchlist=watchlist)
        assert len(updated) == len(RESEARCHER_IDS)
        assert all(item.symbol == "AMZN" for item in updated)
        assert all(item.category == "company" for item in updated)

    def test_rotating_off_a_completed_item_stays_within_the_passed_watchlist(self) -> None:
        watchlist = [_watchlist_entry("NVDA", "NVIDIA Corp.")]
        completed = [_completed_item(agent_id, "NVDA") for agent_id in RESEARCHER_IDS]

        updated, just_completed = tick_research(completed, watchlist=watchlist)
        assert len(just_completed) == 0  # already completed on entry, nothing newly completes this tick
        in_progress = [item for item in updated if item.status == "in_progress"]
        assert all(item.symbol == "NVDA" for item in in_progress)

    def test_default_watchlist_behaves_the_same_as_no_watchlist(self) -> None:
        seed_symbols = {s[0] for s in SEED_SYMBOLS}
        updated, _completed = tick_research([], watchlist=default_watchlist())
        assert all(item.symbol in seed_symbols for item in updated)
