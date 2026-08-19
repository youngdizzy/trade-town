"""app/leakage_audit.py — CEO directive "Professional Quant Trading Firm
— Quant Intelligence + Market Analysis Completion Phase (Next Research +
Validation Pass)," item 7: a real, structural look-ahead-bias audit for
app/strategy_engine.py's generic setup detector.

RESEARCH FIRST. This codebase's bar-by-bar engines were already built
carefully to avoid look-ahead (entry always fills at the bar AFTER
confirmation, never the confirmation bar's own close — see app/
ema_pullback_research.py's and app/strategy_engine.py's own module
docstrings), but until this module, nothing PROVED that carefulness
structurally; it was a design intention checked by code review, not by a
test that could catch a future regression.

THE METHOD: TRUNCATE AND RE-DETECT. For every real setup
`_detect_generic_setups()` finds against the FULL candle series, this
module re-runs the exact same detector against the series truncated to
end exactly at that setup's own entry bar (`candles[: entry_index + 1]`
— everything up to and including the bar whose OPEN price fills the
trade, nothing after). If the same setup (same direction, same entry
index, same entry price) is NOT found identically against the truncated
series, that is real, structural proof the original detection depended
on a candle that would not have existed yet at the moment the trade was
supposedly taken — a genuine look-ahead violation, not a suspicion.

WHY THIS WORKS AS A REAL TEST, NOT A TAUTOLOGY. `_detect_generic_setups`
is deterministic and stateless per call — it has no way to "know" it is
being re-run on a truncated series unless it genuinely used data beyond
the truncation point. `tests/test_leakage_audit.py` proves this
methodology itself is sound (not just trivially always passing) by
running it against a DELIBERATELY BROKEN detector that peeks one real
bar into the future — the audit correctly reports a violation for that
broken detector, and reports none for the real one.

`find_first_look_ahead_violation`'s `detect`/`build_series` parameters
default to the real production functions but are real, first-class
inputs specifically so a test can substitute a deliberately-broken
implementation without needing a second copy of this module's own
truncate-and-compare logic.
"""
from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone

from app.market_data import Candle, market_data_provider
from app.schemas import CompiledStrategyDefinition, LookAheadAuditResult, LookAheadViolation
from app.strategy_engine import DEFAULT_CANDLES_PER_SYMBOL, DEFAULT_TIMEFRAME, _build_series_cache, _detect_generic_setups, _GenericSetup, _SeriesCache, _unsupported_indicators
from app.watchlist import SEED_SYMBOLS

DetectFn = Callable[[list[Candle], CompiledStrategyDefinition, _SeriesCache], list[_GenericSetup]]
BuildSeriesFn = Callable[[list[Candle], CompiledStrategyDefinition], _SeriesCache]


def find_first_look_ahead_violation(
    definition: CompiledStrategyDefinition,
    candles: list[Candle],
    *,
    detect: DetectFn = _detect_generic_setups,
    build_series: BuildSeriesFn = _build_series_cache,
) -> list[LookAheadViolation]:
    """Real truncate-and-re-detect audit — see this module's own
    docstring. Returns every real violation found (never stops at the
    first one), so a caller can see the full real extent of a leak."""
    full_series = build_series(candles, definition)
    full_setups = detect(candles, definition, full_series)
    violations: list[LookAheadViolation] = []
    for setup in full_setups:
        truncated_candles = candles[: setup.entry_index + 1]
        truncated_series = build_series(truncated_candles, definition)
        truncated_setups = detect(truncated_candles, definition, truncated_series)
        match = any(s.direction == setup.direction and s.entry_index == setup.entry_index and s.entry_price == setup.entry_price for s in truncated_setups)
        if not match:
            entry_candle = candles[setup.entry_index]
            violations.append(
                LookAheadViolation(
                    entryIndex=setup.entry_index,
                    entryTimestamp=entry_candle.timestamp,
                    direction=setup.direction,
                    detail=(
                        f"A real {setup.direction} setup detected against the full series (entry at {entry_candle.timestamp}, "
                        f"price {setup.entry_price}) could not be reproduced using only candles up to and including that same entry bar — "
                        "detection depended on a real candle that would not have existed yet at trade time."
                    ),
                )
            )
    return violations


def audit_definition_for_look_ahead(
    definition: CompiledStrategyDefinition,
    *,
    symbols: list[str] | None = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    candles_per_symbol: int = DEFAULT_CANDLES_PER_SYMBOL,
) -> LookAheadAuditResult:
    """The one real entry point for auditing a compiled definition end to
    end against real (mock) candle history, one symbol at a time.
    Refuses exactly when `run_compiled_strategy_backtest()` would."""
    now_iso = datetime.now(timezone.utc).isoformat()
    result_id = f"leakage-audit-{definition.id}"

    def _refusal(reason: str) -> LookAheadAuditResult:
        return LookAheadAuditResult(id=result_id, definitionId=definition.id, definitionVersion=definition.version, setupsChecked=0, violations=[], verdict="insufficient_data", detail=reason, generatedAt=now_iso)

    if definition.status != "compiled":
        return _refusal(f"This definition is not backtestable: status={definition.status!r}. {definition.detail}")
    unsupported = _unsupported_indicators(definition)
    if unsupported:
        return _refusal(f"This engine's current v1 scope cannot resolve indicator(s) {sorted(unsupported)} — a real, disclosed coverage gap, not a fabricated result.")

    resolved_symbols = symbols if symbols is not None else [s for s, _name, _cat in SEED_SYMBOLS]
    all_violations: list[LookAheadViolation] = []
    setups_checked = 0
    for symbol in resolved_symbols:
        candles = market_data_provider.get_candles(symbol, timeframe, candles_per_symbol)
        series = _build_series_cache(candles, definition)
        setups_checked += len(_detect_generic_setups(candles, definition, series))
        all_violations += find_first_look_ahead_violation(definition, candles)

    if setups_checked == 0:
        verdict = "insufficient_data"
        detail = "No real setups were found against this real candle history — nothing to audit yet."
    elif all_violations:
        verdict = "violations_found"
        detail = f"{len(all_violations)} of {setups_checked} real setup(s) could not be reproduced from a truncated series — a genuine look-ahead dependency, not a suspicion."
    else:
        verdict = "clean"
        detail = f"All {setups_checked} real setup(s) found against the full series were independently reproduced using only candles up to and including their own entry bar — no real look-ahead dependency found."

    return LookAheadAuditResult(id=result_id, definitionId=definition.id, definitionVersion=definition.version, setupsChecked=setups_checked, violations=all_violations, verdict=verdict, detail=detail, generatedAt=now_iso)  # type: ignore[arg-type]
