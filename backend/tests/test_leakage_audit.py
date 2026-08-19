"""Covers app/leakage_audit.py — CEO directive "Professional Quant
Trading Firm — Quant Intelligence + Market Analysis Completion Phase
(Next Research + Validation Pass)," item 7. The critical guarantee this
file establishes: the audit methodology itself is proven sound by
running it against a DELIBERATELY BROKEN detector that peeks one real
bar into the future — the audit must catch that real, injected leak, not
just trivially pass every time.
"""
from __future__ import annotations

from app.leakage_audit import audit_definition_for_look_ahead, find_first_look_ahead_violation
from app.market_data import Candle, market_data_provider
from app.schemas import CompiledStrategyDefinition
from app.strategy_compiler import compile_strategy_text
from app.strategy_engine import _build_series_cache, _detect_generic_setups, _GenericSetup, _SeriesCache

_CEO_TEXT = (
    "Buy when price closes above the 50 EMA, then wait for at least two bearish candles, "
    "then enter when price closes above the previous swing high. Place the stop at the "
    "Chandelier Stop and target 2R."
)


def _leaky_detect(candles: list[Candle], definition: CompiledStrategyDefinition, series: _SeriesCache) -> list[_GenericSetup]:
    """A deliberately BROKEN detector, injected only for this test: it
    reports one real setup at the second-to-last real bar of whatever
    series it's handed, but only when the series is at least
    `_LEAK_MIN_LENGTH` bars long — a real, direct future-data dependency
    (a truncated series shorter than the full one will never see this
    setup, exactly the real leak this audit exists to catch)."""
    if len(candles) < _LEAK_MIN_LENGTH:
        return []
    entry_index = len(candles) - 2
    return [_GenericSetup(direction="long", entry_index=entry_index, entry_price=candles[entry_index].open, stop_price=0.0, pullback_low=None, pullback_high=None)]


_LEAK_MIN_LENGTH = 50


def _clean_detect(candles: list[Candle], definition: CompiledStrategyDefinition, series: _SeriesCache) -> list[_GenericSetup]:
    """A deliberately CLEAN toy detector: always reports the exact same
    real setup at a fixed early bar, regardless of how much later real
    history exists — the real audit must find zero violations against
    this one, proving it does not fire false positives on a genuinely
    leak-free detector."""
    if len(candles) < 6:
        return []
    return [_GenericSetup(direction="long", entry_index=5, entry_price=candles[5].open, stop_price=0.0, pullback_low=None, pullback_high=None)]


class TestFindFirstLookAheadViolationCatchesARealInjectedLeak:
    def test_a_detector_that_peeks_at_the_future_end_of_the_series_is_caught(self) -> None:
        definition = compile_strategy_text(name="x", source_text=_CEO_TEXT)
        candles = market_data_provider.get_candles("AAPL", "1h", 200)
        violations = find_first_look_ahead_violation(definition, candles, detect=_leaky_detect, build_series=_build_series_cache)
        assert len(violations) == 1
        assert violations[0].direction == "long"

    def test_a_genuinely_clean_toy_detector_produces_zero_false_positives(self) -> None:
        definition = compile_strategy_text(name="x", source_text=_CEO_TEXT)
        candles = market_data_provider.get_candles("AAPL", "1h", 200)
        violations = find_first_look_ahead_violation(definition, candles, detect=_clean_detect, build_series=_build_series_cache)
        assert violations == []

    def test_the_real_production_detector_is_genuinely_clean_on_a_real_sample(self) -> None:
        definition = compile_strategy_text(name="x", source_text=_CEO_TEXT)
        candles = market_data_provider.get_candles("AAPL", "1h", 6000)
        violations = find_first_look_ahead_violation(definition, candles, detect=_detect_generic_setups, build_series=_build_series_cache)
        assert violations == []


class TestAuditDefinitionForLookAheadRefusesRatherThanGuesses:
    def test_an_invalid_definition_is_refused(self) -> None:
        definition = compile_strategy_text(name="x", source_text="Buy when the moon is full.")
        result = audit_definition_for_look_ahead(definition, symbols=["AAPL"])
        assert result.verdict == "insufficient_data"
        assert result.setups_checked == 0


class TestAuditDefinitionForLookAheadIntegration:
    def test_the_real_50_ema_pullback_definition_audits_clean(self) -> None:
        definition = compile_strategy_text(name="x", source_text=_CEO_TEXT)
        result = audit_definition_for_look_ahead(definition, symbols=["AAPL", "MSFT"], candles_per_symbol=6000)
        assert result.verdict in ("clean", "insufficient_data")
        assert result.violations == []
