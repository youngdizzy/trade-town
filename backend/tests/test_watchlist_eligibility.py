"""Covers app/watchlist_eligibility.py — CEO directive "Professional
Quant Trading Core," Phase B P2 item. Every tier is a real
classification over app/performance_attribution.py's own real per-symbol
win-rate/expectancy (never a fabricated score), extended to cover the
full watchlist including symbols with zero real trades."""
from __future__ import annotations

from app.schemas import OpportunityRejection, PaperTrade, WatchlistEntry
from app.watchlist_eligibility import (
    CAUTIONARY_MAX_WIN_RATE_PCT,
    MIN_TRADES_FOR_TIER_VERDICT,
    PROVEN_MIN_WIN_RATE_PCT,
    compute_watchlist_eligibility,
)

_TRADE_DEFAULTS = {
    "id": "trade-x",
    "symbol": "AAPL",
    "side": "buy",
    "quantity": 1.0,
    "entryPrice": 100.0,
    "exitPrice": 100.0,
    "durationMinutes": 30,
    "confidence": 80.0,
    "reason": "test",
    "marketConditions": "test",
    "supportingAgents": ["scout"],
    "opposingAgents": [],
    "openedAt": "2024-01-01T00:00:00+00:00",
    "closedAt": "2024-01-01T00:00:00+00:00",
    "openedSimMinutes": 0,
}


def _trade(symbol: str, n: int, pnl: float) -> PaperTrade:
    return PaperTrade.model_validate({**_TRADE_DEFAULTS, "id": f"trade-{symbol}-{n}", "symbol": symbol, "pnl": pnl, "pnlPct": pnl})


def _entry(symbol: str) -> WatchlistEntry:
    return WatchlistEntry(symbol=symbol, name=symbol, lastPrice=100.0, dailyChangePct=0.0, status="queued", researchProgress=0.0, assignedAgent=None)


def _rejection(symbol: str, n: int) -> OpportunityRejection:
    return OpportunityRejection(
        id=f"rejection-{symbol}-{n}",
        symbol=symbol,
        wouldHaveRecommended="buy",
        reasons=["test reason"],
        reasonCodes=["trade_quality_below_threshold"],
        decisionScoreAtRejection=50.0,
        expectedValueAtRejectionPct=0.0,
        priceAtRejection=100.0,
        rejectedSimMinutes=0,
        createdAt="2024-01-01T00:00:00+00:00",
    )


class TestComputeWatchlistEligibility:
    def test_zero_trades_is_unproven(self) -> None:
        summary = compute_watchlist_eligibility([_entry("NEXA")], [], [])
        assert len(summary.reads) == 1
        read = summary.reads[0]
        assert read.tier == "unproven"
        assert read.trade_count == 0
        assert read.win_rate_pct is None

    def test_below_minimum_sample_is_developing(self) -> None:
        trades = [_trade("NEXA", i, 100.0) for i in range(MIN_TRADES_FOR_TIER_VERDICT - 1)]
        summary = compute_watchlist_eligibility([_entry("NEXA")], trades, [])
        read = summary.reads[0]
        assert read.tier == "developing"
        assert read.trade_count == MIN_TRADES_FOR_TIER_VERDICT - 1

    def test_strong_real_record_is_proven(self) -> None:
        # All winners -> 100% win rate, well above PROVEN_MIN_WIN_RATE_PCT, positive expectancy.
        trades = [_trade("NEXA", i, 100.0) for i in range(MIN_TRADES_FOR_TIER_VERDICT + 2)]
        summary = compute_watchlist_eligibility([_entry("NEXA")], trades, [])
        read = summary.reads[0]
        assert read.tier == "proven"
        assert read.win_rate_pct is not None and read.win_rate_pct >= PROVEN_MIN_WIN_RATE_PCT
        assert read.expectancy_pct is not None and read.expectancy_pct > 0

    def test_weak_real_record_is_cautionary(self) -> None:
        # All losers -> 0% win rate, well below CAUTIONARY_MAX_WIN_RATE_PCT, negative expectancy.
        trades = [_trade("NEXA", i, -100.0) for i in range(MIN_TRADES_FOR_TIER_VERDICT + 2)]
        summary = compute_watchlist_eligibility([_entry("NEXA")], trades, [])
        read = summary.reads[0]
        assert read.tier == "cautionary"
        assert read.win_rate_pct is not None and read.win_rate_pct < CAUTIONARY_MAX_WIN_RATE_PCT

    def test_mixed_real_record_between_the_two_bars_is_developing(self) -> None:
        # A real 50/50 split sits strictly between CAUTIONARY_MAX_WIN_RATE_PCT
        # (40) and PROVEN_MIN_WIN_RATE_PCT (55) — a genuinely mixed record.
        n = MIN_TRADES_FOR_TIER_VERDICT + 3
        trades = [_trade("NEXA", i, 100.0 if i % 2 == 0 else -100.0) for i in range(n)]
        summary = compute_watchlist_eligibility([_entry("NEXA")], trades, [])
        read = summary.reads[0]
        assert read.tier == "developing"

    def test_rejection_count_is_surfaced_but_never_alone_drives_cautionary(self) -> None:
        rejections = [_rejection("NEXA", i) for i in range(5)]
        summary = compute_watchlist_eligibility([_entry("NEXA")], [], rejections)
        read = summary.reads[0]
        assert read.rejection_count == 5
        assert read.tier == "unproven"  # zero real trades still wins the classification

    def test_every_watchlist_symbol_gets_a_read_even_with_no_trade_history(self) -> None:
        entries = [_entry("A"), _entry("B"), _entry("C")]
        summary = compute_watchlist_eligibility(entries, [], [])
        assert {r.symbol for r in summary.reads} == {"A", "B", "C"}
        assert all(r.tier == "unproven" for r in summary.reads)

    def test_symbols_are_classified_independently(self) -> None:
        winners = [_trade("WIN", i, 100.0) for i in range(MIN_TRADES_FOR_TIER_VERDICT + 2)]
        losers = [_trade("LOSE", i, -100.0) for i in range(MIN_TRADES_FOR_TIER_VERDICT + 2)]
        summary = compute_watchlist_eligibility([_entry("WIN"), _entry("LOSE"), _entry("UNTRADED")], winners + losers, [])
        by_symbol = {r.symbol: r for r in summary.reads}
        assert by_symbol["WIN"].tier == "proven"
        assert by_symbol["LOSE"].tier == "cautionary"
        assert by_symbol["UNTRADED"].tier == "unproven"

    def test_detail_cites_the_real_trade_count_and_win_rate(self) -> None:
        trades = [_trade("NEXA", i, 100.0) for i in range(MIN_TRADES_FOR_TIER_VERDICT + 2)]
        summary = compute_watchlist_eligibility([_entry("NEXA")], trades, [])
        detail = summary.reads[0].detail
        assert str(MIN_TRADES_FOR_TIER_VERDICT + 2) in detail
        assert "100" in detail  # 100% win rate
