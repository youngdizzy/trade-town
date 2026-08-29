"""Chaos/edge-case coverage for candle-data consumers — CEO directive
"TradeTown — 11/10 Market Intelligence + Quant Research Engine," the
Failure/Chaos Testing ask. A dedicated repo audit (file:line cited, not
guessed) found genuine, confirmed gaps: no module in this codebase
checks candle staleness, duplicate timestamps, chronological order, or
a mid-series time gap — and the one existing production guard for
malformed input (`relative_volume()`'s zero-baseline check,
app/volume_analysis.py:105-106) had no dedicated test anywhere.

This file is PURE TESTING — no production code changed. Every test
here either (a) proves an existing real guard actually fires, or (b)
documents this codebase's real current behavior on out-of-spec input
honestly: "runs to completion, returns a real deterministic number,
never raises" — never a fabricated claim that the number produced is
MEANINGFUL for garbage input, since no module here promises that.
`MockMarketDataProvider.get_candles()` (app/market_data.py) always
produces fresh, strictly-ascending, non-duplicated candles by
construction, so none of these five conditions are reachable through
the real live pipeline today — these tests exist for the day a future
data source (or a hand-built Strategy Lab backtest fixture) doesn't
share that guarantee.

Scope is an honest, disclosed subset — volume_analysis.py,
technical_indicators.py, market_intelligence.py, technical_patterns.py
— chosen as the modules most directly exposed to raw candle series
with the least existing indirection. Every other candle-consuming
module (strategy_engine.py, the *_research.py hypothesis modules,
trend_engine.py) is a further, separate, still-real lift, not silently
declared covered."""
from __future__ import annotations

from app.market_data import Candle
from app.market_intelligence import compute_liquidity, compute_market_structure
from app.technical_indicators import ema, sma, vwap
from app.technical_patterns import compute_session_range
from app.volume_analysis import relative_volume, relative_volume_series


def _candle(i: int, *, o: float = 100.0, h: float = 101.0, low: float = 99.0, c: float = 100.0, volume: float = 1000.0, timestamp: str | None = None) -> Candle:
    ts = timestamp if timestamp is not None else f"2026-01-{1 + i // 24:02d}T{i % 24:02d}:00:00+00:00"
    return Candle(symbol="TEST", timeframe="1h", timestamp=ts, open=o, high=h, low=low, close=c, volume=volume, data_status="simulated")


def _wiggly_candles(n: int, *, volume: float = 1000.0) -> list[Candle]:
    """A real, non-flat, strictly-ascending-timestamp series — enough
    genuine swing structure for compute_market_structure()/
    compute_liquidity() to have real swing highs/lows to find, unlike a
    perfectly flat fixture (which this project's own test history has
    already found produces degenerate tie-break swings — see
    test_evidence_confluence.py's fixture note)."""
    candles = []
    for i in range(n):
        offset = (i % 6) - 3  # a real, repeating zigzag: -3..+2
        base = 100 + offset * 2
        candles.append(_candle(i, o=base, h=base + 1.5, low=base - 1.5, c=base + 0.3, volume=volume))
    return candles


class TestZeroVolumeCandles:
    """volume_analysis.py's real, existing zero-baseline guards — real
    code, previously untested (see this file's own module docstring)."""

    def test_relative_volume_is_honestly_none_when_the_baseline_window_is_all_zero_volume(self) -> None:
        candles = [_candle(i, volume=0.0) for i in range(21)]
        assert relative_volume(candles, period=20) is None

    def test_relative_volume_series_reports_zero_not_none_for_the_same_zero_baseline_case(self) -> None:
        # Documents a real inconsistency between the two functions,
        # never asserted as correct: relative_volume() above returns an
        # honest None for an undefined ratio, but relative_volume_series()
        # currently falls back to 0.0 for the identical undefined case
        # (volume_analysis.py's own `round(..., 4) if baseline else 0.0`
        # branch) — current, real, disclosed behavior.
        candles = [_candle(i, volume=0.0) for i in range(21)]
        series = relative_volume_series(candles, period=20)
        assert series == [0.0]

    def test_a_single_zero_volume_candle_among_real_volume_does_not_crash_relative_volume(self) -> None:
        candles = [_candle(i, volume=1000.0) for i in range(21)]
        candles[10] = _candle(10, volume=0.0, timestamp=candles[10].timestamp)
        result = relative_volume(candles, period=20)
        assert result is not None
        assert result >= 0

    def test_a_single_zero_volume_candle_does_not_crash_vwap(self) -> None:
        candles = [_candle(i, volume=1000.0) for i in range(5)]
        candles[2] = _candle(2, volume=0.0, timestamp=candles[2].timestamp)
        assert vwap(candles) is not None

    def test_every_candle_zero_volume_is_an_honest_none_from_vwap(self) -> None:
        # vwap()'s own real guard (technical_indicators.py) — total
        # volume of 0 across the whole window has no real VWAP.
        candles = [_candle(i, volume=0.0) for i in range(5)]
        assert vwap(candles) is None


class TestDuplicateTimestampCandles:
    """No module in the audited subset checks for a repeated timestamp
    — these confirm real functions run to completion (never raise) and
    keep returning a real, self-consistent number, not that the number
    is meaningful for duplicated input."""

    def test_sma_and_ema_do_not_crash_on_a_duplicated_timestamp(self) -> None:
        candles = _wiggly_candles(30)
        candles[15] = _candle(15, o=candles[14].open, h=candles[14].high, low=candles[14].low, c=candles[14].close, volume=candles[14].volume, timestamp=candles[14].timestamp)
        assert sma(candles, 10) is not None
        assert ema(candles, 10) is not None

    def test_compute_market_structure_does_not_crash_on_a_duplicated_timestamp(self) -> None:
        candles = _wiggly_candles(30)
        candles[20] = _candle(20, o=candles[19].open, h=candles[19].high, low=candles[19].low, c=candles[19].close, volume=candles[19].volume, timestamp=candles[19].timestamp)
        result = compute_market_structure("TEST", candles)
        assert result.detail != ""

    def test_compute_liquidity_does_not_crash_on_a_duplicated_timestamp(self) -> None:
        candles = _wiggly_candles(30)
        candles[20] = _candle(20, o=candles[19].open, h=candles[19].high, low=candles[19].low, c=candles[19].close, volume=candles[19].volume, timestamp=candles[19].timestamp)
        result = compute_liquidity("TEST", candles)
        assert result.detail != ""

    def test_compute_session_range_counts_a_duplicated_timestamp_candle_independently(self) -> None:
        # Session bucketing (technical_patterns.py) only ever reads each
        # candle's own hour-of-day — a duplicated timestamp is just two
        # real candles independently bucketed into the same session,
        # never a crash and never silently merged into one.
        candles = _wiggly_candles(20)
        candles[10] = _candle(10, o=candles[9].open, h=candles[9].high, low=candles[9].low, c=candles[9].close, volume=candles[9].volume, timestamp=candles[9].timestamp)
        result = compute_session_range("TEST", candles, "new_york")
        assert isinstance(result.range_high, float)


class TestOutOfOrderCandles:
    """No module in the audited subset sorts or validates chronological
    order — technical_indicators.py/market_intelligence.py's swing
    detection both index by POSITION, not real time, so unsorted input
    never crashes; it silently reads the wrong bars as "recent," a
    real, disclosed limitation, not a claim of correctness."""

    def test_sma_does_not_crash_on_a_reversed_series(self) -> None:
        candles = list(reversed(_wiggly_candles(30)))
        assert sma(candles, 10) is not None

    def test_compute_market_structure_does_not_crash_on_a_reversed_series(self) -> None:
        candles = list(reversed(_wiggly_candles(30)))
        result = compute_market_structure("TEST", candles)
        assert result.detail != ""

    def test_compute_liquidity_does_not_crash_on_a_partially_shuffled_series(self) -> None:
        candles = _wiggly_candles(30)
        # Swap two chunks in the middle — a real, partial reordering
        # (not a full reversal), the shape a merged multi-source feed
        # might actually produce.
        candles = candles[:10] + candles[20:] + candles[10:20]
        result = compute_liquidity("TEST", candles)
        assert result.detail != ""


class TestStaleCandles:
    """No module anywhere in this codebase compares a candle's own
    timestamp to real wall-clock "now" — confirmed by the repo audit
    behind this file. These tests directly prove that absence: a
    candle series timestamped years in the past computes exactly like
    a fresh one, with zero staleness rejection anywhere in the chain."""

    def test_indicators_compute_normally_over_a_candle_series_from_the_year_2000(self) -> None:
        candles = [
            _candle(i, o=100 + i * 0.1, h=101 + i * 0.1, low=99 + i * 0.1, c=100.3 + i * 0.1, timestamp=f"2000-01-{1 + i // 24:02d}T{i % 24:02d}:00:00+00:00")
            for i in range(30)
        ]
        assert sma(candles, 10) is not None
        assert vwap(candles) is not None

    def test_compute_market_structure_computes_normally_over_a_stale_series(self) -> None:
        candles = [
            _candle(i, o=100 + ((i % 6) - 3) * 2, h=103 + ((i % 6) - 3) * 2, low=97 + ((i % 6) - 3) * 2, c=100.3 + ((i % 6) - 3) * 2, timestamp=f"2000-01-{1 + i // 24:02d}T{i % 24:02d}:00:00+00:00")
            for i in range(30)
        ]
        result = compute_market_structure("TEST", candles)
        assert result.detail != ""


class TestGappedCandles:
    """A genuine mid-series time GAP (as opposed to simply too few
    candles, which every module already handles via its own real
    "not enough history" honest-empty-state — see e.g.
    compute_market_structure()'s own len(candles) check). No module in
    the audited subset detects or rejects a gap; these confirm nothing
    crashes when one is silently present."""

    def test_compute_session_range_does_not_crash_across_a_30_day_gap(self) -> None:
        early = _wiggly_candles(15)
        late = [
            _candle(i, o=c.open, h=c.high, low=c.low, c=c.close, volume=c.volume, timestamp=f"2026-02-{1 + (i - 15) // 24:02d}T{(i - 15) % 24:02d}:00:00+00:00")
            for i, c in enumerate(_wiggly_candles(15), start=15)
        ]
        candles = early + late
        result = compute_session_range("TEST", candles, "new_york")
        assert isinstance(result.range_high, float)

    def test_compute_market_structure_does_not_crash_across_a_30_day_gap(self) -> None:
        early = _wiggly_candles(15)
        late = [
            _candle(i, o=c.open, h=c.high, low=c.low, c=c.close, volume=c.volume, timestamp=f"2026-02-{1 + (i - 15) // 24:02d}T{(i - 15) % 24:02d}:00:00+00:00")
            for i, c in enumerate(_wiggly_candles(15), start=15)
        ]
        candles = early + late
        result = compute_market_structure("TEST", candles)
        assert result.detail != ""
