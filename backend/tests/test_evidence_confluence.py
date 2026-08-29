"""Covers app/evidence_confluence.py — CEO directive "Professional Quant
Trading Firm — Quant Intelligence + Market Analysis Completion Phase,"
Phase D. The whole point of this module is that `raw_signal_count` can
diverge sharply from `independent_family_count` when multiple real
signals share the same underlying evidence family — every test here
checks that divergence is computed honestly, never a bare signal count.
"""
from __future__ import annotations

from app.evidence_confluence import assess_evidence_confluence, classify_confluence
from app.market_data import Candle


def _candle(i: int, o: float, h: float, low: float, c: float, volume: float = 1000.0) -> Candle:
    return Candle(symbol="TEST", timeframe="1h", timestamp=f"2024-01-{1 + i // 24:02d}T{i % 24:02d}:00:00+00:00", open=o, high=h, low=low, close=c, volume=volume, data_status="simulated")


def _uptrend_candles(n: int = 60) -> list[Candle]:
    return [_candle(i, 100 + i * 0.5, 100 + i * 0.5 + 1, 100 + i * 0.5 - 1, 100 + i * 0.5 + 0.4) for i in range(n)]


class TestNoRealDataYieldsHonestEmptyRead:
    def test_empty_candles(self) -> None:
        result = assess_evidence_confluence("TEST", [])
        assert result.raw_signal_count == 0
        assert result.independent_family_count == 0
        assert result.families == []

    def test_too_little_history_still_returns_a_real_partial_read(self) -> None:
        result = assess_evidence_confluence("TEST", [_candle(0, 100, 101, 99, 100)])
        # No fabricated signals below any indicator's own real minimum.
        assert result.raw_signal_count == 0


class TestRawCountVsIndependentCount:
    def test_a_sustained_uptrend_shows_the_real_trend_momentum_redundancy(self) -> None:
        candles = _uptrend_candles(60)
        result = assess_evidence_confluence("TEST", candles)
        assert result.majority_direction == "bullish"
        # The whole point: raw_signal_count (individual signals) must be
        # >= independent_family_count (distinct families) whenever more
        # than one signal shares a family — never the reverse.
        assert result.raw_signal_count >= result.independent_family_count

    def test_trend_family_groups_ema_sma_sar_and_supertrend_together(self) -> None:
        candles = _uptrend_candles(60)
        result = assess_evidence_confluence("TEST", candles)
        trend_family = next((f for f in result.families if f.family == "trend"), None)
        assert trend_family is not None
        # price_vs_ema20, price_vs_sma20, parabolic_sar, supertrend -- four
        # real, individually-computed signals, all one real family (CEO
        # directive "Next Research + Validation Pass": SAR/SuperTrend join
        # the existing trend family rather than becoming a new one).
        assert {s.name for s in trend_family.signals} == {"price_vs_ema20", "price_vs_sma20", "parabolic_sar", "supertrend"}
        assert trend_family.net_direction == "bullish"

    def test_levels_family_never_counted_toward_independent_count(self) -> None:
        candles = _uptrend_candles(60)
        result = assess_evidence_confluence("TEST", candles)
        assert "levels" not in result.agreeing_families


class TestFamilyNetDirectionHandlesRealDisagreement:
    def test_a_family_with_conflicting_signals_reads_neutral_not_a_forced_majority(self) -> None:
        # A choppy series should produce at least one family whose own
        # real signals disagree with each other.
        candles = [_candle(i, 100, 101, 99, 100 + (1 if i % 2 == 0 else -1)) for i in range(60)]
        result = assess_evidence_confluence("TEST", candles)
        for family in result.families:
            directions = {s.direction for s in family.signals if s.direction != "neutral"}
            if len(directions) > 1:
                assert family.net_direction == "neutral"


class TestDetailDisclosesTheGap:
    def test_detail_names_the_real_gap_when_one_exists(self) -> None:
        candles = _uptrend_candles(60)
        result = assess_evidence_confluence("TEST", candles)
        if result.raw_signal_count != result.independent_family_count:
            assert "distinct evidence" in result.detail

    def test_detail_confirms_full_independence_when_no_gap_exists(self) -> None:
        result = assess_evidence_confluence("TEST", [])
        assert "No real directional signals" in result.detail


class TestClassifyConfluence:
    """CEO directive "TradeTown — 11/10 Market Intelligence + Quant
    Research Engine," Phase 7 — the explicit supporting/conflicting/
    neutral/missing taxonomy, a pure reclassification of an already-
    computed EvidenceConfluenceRead against one target direction. Zero
    new signal computation — every case here checks the reclassification
    logic only."""

    def test_families_that_agree_with_the_target_direction_are_supporting(self) -> None:
        candles = _uptrend_candles(60)
        confluence = assess_evidence_confluence("TEST", candles)
        result = classify_confluence(confluence, "bullish")
        assert set(result.supporting) == {"trend", "momentum", "volume"}
        assert result.conflicting == []

    def test_the_same_families_read_as_conflicting_against_the_opposite_direction(self) -> None:
        candles = _uptrend_candles(60)
        confluence = assess_evidence_confluence("TEST", candles)
        result = classify_confluence(confluence, "bearish")
        assert set(result.conflicting) == {"trend", "momentum", "volume"}
        assert result.supporting == []

    def test_a_family_with_zero_real_signals_is_missing_not_silently_neutral(self) -> None:
        # A smooth uptrend never produces a real liquidity sweep, price-
        # structure break, or candlestick pattern -- those three real
        # families genuinely have no signal at all this tick, a distinct
        # state from "checked and found neutral."
        candles = _uptrend_candles(60)
        confluence = assess_evidence_confluence("TEST", candles)
        result = classify_confluence(confluence, "bullish")
        assert set(result.missing) == {"liquidity", "price_structure", "pattern"}
        assert not (set(result.missing) & set(result.neutral))

    def test_levels_family_is_never_classified_at_all(self) -> None:
        candles = _uptrend_candles(60)
        confluence = assess_evidence_confluence("TEST", candles)
        result = classify_confluence(confluence, "bullish")
        all_classified = set(result.supporting) | set(result.conflicting) | set(result.neutral) | set(result.missing)
        assert "levels" not in all_classified

    def test_every_directional_family_lands_in_exactly_one_bucket(self) -> None:
        candles = _uptrend_candles(60)
        confluence = assess_evidence_confluence("TEST", candles)
        result = classify_confluence(confluence, "bullish")
        buckets = [result.supporting, result.conflicting, result.neutral, result.missing]
        total = sum(len(b) for b in buckets)
        assert total == 6  # the six real directional families, no double-counting, none dropped

    def test_no_real_data_reports_every_directional_family_as_missing(self) -> None:
        confluence = assess_evidence_confluence("TEST", [])
        result = classify_confluence(confluence, "bullish")
        assert len(result.missing) == 6
        assert result.supporting == [] and result.conflicting == [] and result.neutral == []
