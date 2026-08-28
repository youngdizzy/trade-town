"""Covers app/asset_discovery.py — CEO directive "Professional Quant
Trading Core," Phase B's last P2 item, the Asset Discovery Engine.
Every candidate must come from a real MockMarketDataProvider candle
series via the real, already-tested rank_symbols_by_trend() — never a
fabricated score — and a symbol already on the watchlist must never be
"discovered" again.
"""
from __future__ import annotations

from app.asset_discovery import DISCOVERY_SYMBOL_POOL, compute_asset_discovery_candidates
from app.market_data import MockMarketDataProvider
from app.schemas import WatchlistEntry
from app.watchlist import ALL_SYMBOL_POOL, default_watchlist


def _entry(symbol: str) -> WatchlistEntry:
    return WatchlistEntry(symbol=symbol, name=symbol, lastPrice=100.0, dailyChangePct=0.0, status="queued", researchProgress=0.0, assignedAgent=None)


class TestComputeAssetDiscoveryCandidates:
    def test_returns_real_rankings_from_the_discovery_pool(self) -> None:
        rankings = compute_asset_discovery_candidates([], MockMarketDataProvider())
        assert len(rankings) > 0
        discovery_symbols = {s for s, _n, _c in DISCOVERY_SYMBOL_POOL}
        assert all(r.symbol in discovery_symbols for r in rankings)

    def test_never_discovers_a_symbol_already_on_the_watchlist(self) -> None:
        already_watched = [_entry(symbol) for symbol, _name, _category in DISCOVERY_SYMBOL_POOL[:3]]
        rankings = compute_asset_discovery_candidates(already_watched, MockMarketDataProvider())
        watched_symbols = {e.symbol for e in already_watched}
        assert not any(r.symbol in watched_symbols for r in rankings)

    def test_discovery_pool_never_overlaps_the_existing_watchlist_universe(self) -> None:
        # A real, disclosed guarantee this module's own docstring makes:
        # discovery only ever adds NEW coverage, never a symbol the CEO
        # could already track via the existing watch_symbol action.
        existing_symbols = {symbol for symbol, _name, _category in ALL_SYMBOL_POOL}
        discovery_symbols = {symbol for symbol, _name, _category in DISCOVERY_SYMBOL_POOL}
        assert existing_symbols.isdisjoint(discovery_symbols)

    def test_discovery_pool_spans_every_research_category(self) -> None:
        from app.schemas import ResearchCategory

        categories_in_pool = {category for _symbol, _name, category in DISCOVERY_SYMBOL_POOL}
        all_categories = set(ResearchCategory.__args__)  # type: ignore[attr-defined]
        assert categories_in_pool == all_categories

    def test_respects_top_n(self) -> None:
        rankings = compute_asset_discovery_candidates([], MockMarketDataProvider(), top_n=2)
        assert len(rankings) == 2

    def test_default_seed_watchlist_still_returns_the_full_pool(self) -> None:
        # default_watchlist() only ever contains SEED_SYMBOLS, which are
        # entirely disjoint from DISCOVERY_SYMBOL_POOL (proven above), so
        # a fresh game's watchlist excludes nothing from discovery.
        rankings = compute_asset_discovery_candidates(default_watchlist(), MockMarketDataProvider(), top_n=50)
        assert len(rankings) == len(DISCOVERY_SYMBOL_POOL)

    def test_sorted_by_real_composite_score_descending(self) -> None:
        rankings = compute_asset_discovery_candidates([], MockMarketDataProvider(), top_n=50)
        scores = [r.composite_score for r in rankings]
        assert scores == sorted(scores, reverse=True)

    def test_empty_when_every_discovery_symbol_is_already_watched(self) -> None:
        all_watched = [_entry(symbol) for symbol, _name, _category in DISCOVERY_SYMBOL_POOL]
        rankings = compute_asset_discovery_candidates(all_watched, MockMarketDataProvider())
        assert rankings == []

    def test_categories_match_the_real_pool_definition(self) -> None:
        rankings = compute_asset_discovery_candidates([], MockMarketDataProvider(), top_n=50)
        category_by_symbol = {symbol: category for symbol, _name, category in DISCOVERY_SYMBOL_POOL}
        for ranking in rankings:
            assert ranking.category == category_by_symbol[ranking.symbol]
