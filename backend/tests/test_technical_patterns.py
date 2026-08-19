"""Covers app/technical_patterns.py — CEO directive "Professional
Trading Firm — Market-Analysis Knowledge + Session Intelligence
Expansion," Phases 1-2. Every function must degrade to an honest
"not enough data" read below its own real minimum, and every detected
pattern must match its own disclosed, geometric definition exactly.
"""
from __future__ import annotations

from app.market_data import Candle
from app.technical_patterns import (
    MIN_TOUCHES_FOR_LEVEL,
    compute_fibonacci_levels,
    compute_session_range,
    detect_candlestick_patterns,
    detect_chart_patterns,
    detect_fair_value_gaps,
    detect_order_block,
    detect_support_resistance_levels,
    label_swing_structure,
)


def _candle(*, o: float, h: float, low: float, c: float, hour: int = 0, i: int = 0, volume: float = 100.0) -> Candle:
    return Candle(symbol="TEST", timeframe="1h", timestamp=f"2024-01-01T{hour:02d}:{i:02d}:00+00:00", open=o, high=h, low=low, close=c, volume=volume, data_status="simulated")


def _flat(price: float, n: int, *, start_hour: int = 0) -> list[Candle]:
    return [_candle(o=price, h=price + 0.1, low=price - 0.1, c=price, hour=(start_hour + i // 60) % 24, i=i % 60) for i in range(n)]


class TestLabelSwingStructure:
    def test_not_enough_candles_reads_no_labels(self) -> None:
        read = label_swing_structure("TEST", _flat(100.0, 3))
        assert read.labels == []

    def test_a_real_rising_sequence_of_swing_highs_labels_higher_high(self) -> None:
        # Two real swing highs, second above the first -- SWING_LOOKBACK=3
        # needs 3 candles on each side of a local extremum.
        candles: list[Candle] = []
        for i, price in enumerate([100, 99, 98, 105, 98, 99, 100, 99, 98, 110, 98, 99, 100]):
            candles.append(_candle(o=price, h=price + 1, low=price - 1, c=price, i=i))
        read = label_swing_structure("TEST", candles)
        assert "higher_high" in read.labels


class TestDetectFairValueGaps:
    def test_not_enough_candles_reads_no_gaps(self) -> None:
        read = detect_fair_value_gaps("TEST", _flat(100.0, 2))
        assert read.gaps == []

    def test_a_real_bullish_gap_is_detected(self) -> None:
        candles = [
            _candle(o=100, h=101, low=99, c=100.5, i=0),  # candle1 high=101
            _candle(o=105, h=106, low=104, c=105.5, i=1),  # displacement
            _candle(o=108, h=109, low=107, c=108.5, i=2),  # candle3 low=107 > candle1 high=101
        ]
        read = detect_fair_value_gaps("TEST", candles)
        assert len(read.gaps) == 1
        assert read.gaps[0].direction == "bullish"
        assert read.gaps[0].gap_low == 101.0
        assert read.gaps[0].gap_high == 107.0

    def test_a_later_candle_trading_back_into_the_gap_marks_it_filled(self) -> None:
        candles = [
            _candle(o=100, h=101, low=99, c=100.5, i=0),
            _candle(o=105, h=106, low=104, c=105.5, i=1),
            _candle(o=108, h=109, low=107, c=108.5, i=2),
            _candle(o=103, h=104, low=100, c=103, i=3),  # trades back down through the gap
        ]
        read = detect_fair_value_gaps("TEST", candles)
        assert read.gaps[0].filled is True

    def test_no_real_gap_when_ranges_overlap(self) -> None:
        candles = [
            _candle(o=100, h=101, low=99, c=100.5, i=0),
            _candle(o=100.5, h=101, low=100, c=100.8, i=1),
            _candle(o=100.5, h=101, low=100, c=100.6, i=2),  # low overlaps candle1's high
        ]
        read = detect_fair_value_gaps("TEST", candles)
        assert read.gaps == []


class TestDetectCandlestickPatterns:
    def test_a_real_bullish_engulfing_pair_is_detected(self) -> None:
        candles = [
            _candle(o=105, h=106, low=99, c=100, i=0),  # bearish, body 100-105
            _candle(o=99, h=110, low=98, c=106, i=1),  # bullish, body 99-106 covers 100-105
        ]
        read = detect_candlestick_patterns("TEST", candles)
        assert any(p.pattern == "bullish_engulfing" for p in read.patterns)

    def test_a_real_doji_is_detected(self) -> None:
        candles = [
            _candle(o=100, h=100.5, low=99.5, c=100, i=0),
            _candle(o=100.0, h=105, low=95, c=100.05, i=1),  # tiny body, wide range
        ]
        read = detect_candlestick_patterns("TEST", candles)
        assert any(p.pattern == "doji" for p in read.patterns)

    def test_a_real_hammer_is_detected(self) -> None:
        candles = [
            _candle(o=100, h=100.5, low=99.5, c=100, i=0),
            _candle(o=100, h=100.5, low=90, c=100.4, i=1),  # long lower wick, tiny body near top
        ]
        read = detect_candlestick_patterns("TEST", candles)
        assert any(p.pattern == "hammer" for p in read.patterns)

    def test_a_real_shooting_star_is_detected(self) -> None:
        candles = [
            _candle(o=100, h=100.5, low=99.5, c=100, i=0),
            _candle(o=100, h=110, low=99.9, c=100.4, i=1),  # long upper wick, tiny lower wick, small body near bottom
        ]
        read = detect_candlestick_patterns("TEST", candles)
        assert any(p.pattern == "shooting_star" for p in read.patterns)

    def test_a_plain_trending_candle_produces_no_false_pattern(self) -> None:
        candles = [
            _candle(o=100, h=102, low=99, c=101.5, i=0),
            _candle(o=101.5, h=104, low=101, c=103.5, i=1),  # ordinary bullish candle, no real pattern shape
        ]
        read = detect_candlestick_patterns("TEST", candles)
        assert read.patterns == []


class TestComputeSessionRange:
    def test_no_candles_in_the_session_window_reads_zero_range(self) -> None:
        candles = [_candle(o=100, h=101, low=99, c=100, hour=10, i=0)]  # london hour
        read = compute_session_range("TEST", candles, "asian")
        assert read.range_high == 0.0
        assert read.range_low == 0.0

    def test_real_high_low_computed_only_from_that_sessions_own_candles(self) -> None:
        candles = [
            _candle(o=100, h=105, low=95, c=100, hour=2, i=0),  # asian
            _candle(o=100, h=200, low=1, c=100, hour=10, i=0),  # london -- must NOT pollute asian's range
        ]
        read = compute_session_range("TEST", candles, "asian")
        assert read.range_high == 105.0
        assert read.range_low == 95.0

    def test_a_later_candle_trading_into_the_range_marks_it_retested(self) -> None:
        candles = [
            _candle(o=100, h=105, low=95, c=100, hour=2, i=0),  # asian range 95-105
            _candle(o=100, h=102, low=98, c=100, hour=10, i=0),  # london, trades inside 95-105
        ]
        read = compute_session_range("TEST", candles, "asian")
        assert read.retested is True

    def test_no_later_candle_trading_into_the_range_reads_not_retested(self) -> None:
        candles = [
            _candle(o=100, h=105, low=95, c=100, hour=2, i=0),  # asian range 95-105
            _candle(o=200, h=210, low=195, c=200, hour=10, i=0),  # london, far away
        ]
        read = compute_session_range("TEST", candles, "asian")
        assert read.retested is False


class TestComputeFibonacciLevels:
    def test_not_enough_swing_history_reads_no_levels(self) -> None:
        read = compute_fibonacci_levels("TEST", _flat(100.0, 3))
        assert read.levels == []

    def test_real_levels_fall_strictly_between_the_real_swing_range(self) -> None:
        candles: list[Candle] = []
        for i, price in enumerate([100, 99, 98, 105, 98, 99, 100, 99, 98, 90, 98, 99, 100]):
            candles.append(_candle(o=price, h=price + 1, low=price - 1, c=price, i=i))
        read = compute_fibonacci_levels("TEST", candles)
        if read.levels:
            retracement_levels = [lv for lv in read.levels if lv.ratio <= 1.0]
            for lv in retracement_levels:
                assert min(read.swing_low, read.swing_high) <= lv.price <= max(read.swing_low, read.swing_high)


class TestDetectOrderBlock:
    def test_no_break_of_structure_reads_none_direction(self) -> None:
        read = detect_order_block("TEST", _flat(100.0, 5))
        assert read.direction == "none"
        assert read.price_high is None


class TestDetectSupportResistanceLevels:
    def test_not_enough_candles_reads_no_levels(self) -> None:
        read = detect_support_resistance_levels("TEST", _flat(100.0, 5))
        assert read.levels == []

    def test_a_real_repeated_swing_low_clusters_into_a_real_support_level(self) -> None:
        prices = [110, 108, 104, 100, 104, 108, 112, 108, 104, 100, 104, 108, 112, 108, 104, 100, 104, 108, 110]
        candles = [_candle(o=p, h=p + 1, low=p - 1, c=p, i=i) for i, p in enumerate(prices)]
        read = detect_support_resistance_levels("TEST", candles)
        support = next((lv for lv in read.levels if lv.role == "support"), None)
        assert support is not None
        assert support.touches >= MIN_TOUCHES_FOR_LEVEL
        assert support.price == 99.0

    def test_a_single_unconfirmed_swing_never_becomes_a_level(self) -> None:
        # A real, but non-repeating, swing sequence -- no two swings land
        # within the real clustering tolerance of each other.
        prices = [100, 99, 98, 150, 98, 99, 100, 99, 98, 210, 98, 99, 100]
        candles = [_candle(o=p, h=p + 1, low=p - 1, c=p, i=i) for i, p in enumerate(prices)]
        read = detect_support_resistance_levels("TEST", candles)
        assert all(lv.touches >= MIN_TOUCHES_FOR_LEVEL for lv in read.levels)

    def test_role_is_mechanical_relative_to_the_real_current_close(self) -> None:
        prices = [110, 108, 104, 100, 104, 108, 112, 108, 104, 100, 104, 108, 112, 108, 104, 100, 104, 108, 110]
        candles = [_candle(o=p, h=p + 1, low=p - 1, c=p, i=i) for i, p in enumerate(prices)]
        read = detect_support_resistance_levels("TEST", candles)
        current_close = candles[-1].close
        for lv in read.levels:
            if lv.price < current_close:
                assert lv.role == "support"
            elif lv.price > current_close:
                assert lv.role == "resistance"


def _ohlc(rows: list[tuple[float, float, float, float]]) -> list[Candle]:
    return [_candle(o=o, h=h, low=lo, c=c, i=i) for i, (o, h, lo, c) in enumerate(rows)]


# Hand-verified fixtures (see the CEO directive "Next Research +
# Validation Pass" implementation notes) — each was traced against
# app.market_intelligence._find_swings()'s own real output and the
# detector's own real formulas before being encoded here, not derived by
# running the function against itself.
_DOUBLE_TOP_ROWS: list[tuple[float, float, float, float]] = [
    (100, 101, 99, 100), (99, 100, 98, 99), (98, 99, 97, 98),
    (105, 106, 104, 105),  # swing high #1
    (98, 99, 97, 98), (97, 98, 96, 97), (96, 97, 90, 90.5),
    (91, 92, 89, 90),  # swing low (neckline)
    (92, 93, 91, 92), (95, 96, 94, 95), (98, 99, 97, 98),
    (105.2, 106.2, 104.2, 105.2),  # swing high #2, ~0.19% from #1
    (98, 99, 97, 98), (97, 98, 96, 97), (96, 97, 95, 96),
    (89, 90, 85, 86),  # real close below the neckline -- confirmation
    (85, 86, 84, 85), (84, 85, 83, 84),
]

_DOUBLE_BOTTOM_ROWS: list[tuple[float, float, float, float]] = [
    (100, 101, 99, 100), (99, 100, 98, 99), (98, 99, 97, 98),
    (95, 96, 94, 95),  # swing low #1
    (98, 99, 97, 98), (99, 100, 98, 99), (103, 110, 102, 109.5),
    (108, 109, 107, 108),  # swing high (neckline)
    (107, 108, 106, 107), (104, 105, 103, 104), (98, 99, 97, 98),
    (95.19, 96.19, 94.19, 95.19),  # swing low #2, ~0.2% from #1
    (98, 99, 97, 98), (99, 100, 98, 99), (100, 101, 99, 100),
    (108, 112, 107, 111),  # real close above the neckline -- confirmation
    (112, 113, 111, 112), (113, 114, 112, 113),
]

_TRENDLINE_BREAK_ROWS: list[tuple[float, float, float, float]] = [
    (100, 105, 99, 104), (99, 104, 98, 103), (98, 103, 97, 102),
    (95, 100, 90, 96),  # swing low #1 (low=90)
    (98, 103, 97, 102), (99, 104, 98, 103), (100, 105, 99, 104),
    (98, 103, 95, 99),  # swing low #2 (low=95, a real rising line)
    (99, 104, 98, 103), (100, 109, 99, 104), (101, 110, 100, 105),
    (98, 103, 80, 81),  # real close well below the extrapolated line
    (79, 80, 78, 79), (78, 79, 77, 78),
]


class TestDetectChartPatterns:
    def test_not_enough_candles_reads_no_patterns(self) -> None:
        read = detect_chart_patterns("TEST", _ohlc(_DOUBLE_TOP_ROWS[:3]))
        assert read.patterns == []

    def test_a_real_confirmed_double_top(self) -> None:
        read = detect_chart_patterns("TEST", _ohlc(_DOUBLE_TOP_ROWS))
        assert len(read.patterns) == 1
        p = read.patterns[0]
        assert p.pattern_type == "double_top"
        assert p.direction == "bearish"
        assert p.price_low == 89.0
        assert p.price_high == 106.2
        assert p.confidence_pct == 87.4  # 0.19% price gap vs the 1.5% tolerance -> 100*(1-0.19/1.5)

    def test_a_real_confirmed_double_bottom(self) -> None:
        read = detect_chart_patterns("TEST", _ohlc(_DOUBLE_BOTTOM_ROWS))
        assert len(read.patterns) == 1
        p = read.patterns[0]
        assert p.pattern_type == "double_bottom"
        assert p.direction == "bullish"
        assert p.price_low == 94.0
        assert p.price_high == 110.0

    def test_an_unconfirmed_shape_is_never_reported(self) -> None:
        # The same real double-top geometry, truncated right after the
        # second swing high forms -- no later real close has broken the
        # neckline yet, so this must NOT be reported as a pattern (never
        # a still-forming, outcome-unknown shape).
        read = detect_chart_patterns("TEST", _ohlc(_DOUBLE_TOP_ROWS[:12]))
        assert read.patterns == []

    def test_a_real_confirmed_trendline_break(self) -> None:
        read = detect_chart_patterns("TEST", _ohlc(_TRENDLINE_BREAK_ROWS))
        breaks = [p for p in read.patterns if p.pattern_type == "trendline_break_down"]
        assert len(breaks) == 1
        p = breaks[0]
        assert p.direction == "bearish"
        assert p.price_low == 81.0
        assert p.price_high == 95.0
        assert p.confidence_pct == 50.0  # exactly the 2 defining points, no extra real touch

    def test_confidence_is_bounded_zero_to_one_hundred_across_every_detected_pattern(self) -> None:
        for rows in (_DOUBLE_TOP_ROWS, _DOUBLE_BOTTOM_ROWS, _TRENDLINE_BREAK_ROWS):
            read = detect_chart_patterns("TEST", _ohlc(rows))
            for p in read.patterns:
                assert 0.0 <= p.confidence_pct <= 100.0

    def test_every_pattern_carries_the_real_symbol_and_timeframe(self) -> None:
        read = detect_chart_patterns("NEXA", _ohlc(_DOUBLE_TOP_ROWS), timeframe="4h")
        for p in read.patterns:
            assert p.symbol == "NEXA"
            assert p.timeframe == "4h"
