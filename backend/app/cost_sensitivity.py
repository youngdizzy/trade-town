"""app/cost_sensitivity.py — CEO directive "Professional Quant Trading
Firm — Quant Intelligence + Market Analysis Completion Phase (Next
Research + Validation Pass)," item 6: real transaction-cost/slippage
sensitivity for a compiled strategy's own backtest.

RESEARCH FIRST. A full audit of the real execution-cost machinery found
it genuinely real but genuinely DISCONNECTED from every bar-by-bar
research backtest in this codebase — Category C, not a gap to build from
scratch. `app/portfolio.py`'s `TRANSACTION_COST_BPS` (a real, flat,
disclosed 5.0 bps per fill) is deducted from the cash ledger on every
REAL LIVE fill (`open_position()`/`close_position()`), and
`app/execution_quality.py`'s `compute_slippage_bps()`/`apply_slippage()`
similarly slips every real live market/stop fill. Neither is ever
consulted by `app/backtest_primitives.py::simulate_exit()` — a
backtest's stop/target fills land at the EXACT real stop/target price,
zero friction, every time. This module closes exactly that gap for
research, reusing the SAME real cost/slippage constants live trading
already charges rather than inventing a second, parallel cost model.

ONE AUTHORITATIVE COST MODEL, REUSED NOT REINVENTED. `COST_SCENARIOS`
below is built directly from `app/portfolio.py`'s `TRANSACTION_COST_BPS`
and `app/execution_quality.py`'s `BASE_SLIPPAGE_BPS`/`MAX_SLIPPAGE_BPS`
— the exact same numbers, not a second set of research-only constants.
"base" (0 bps) is this engine's own existing default (what every prior
backtest in this codebase has implicitly assumed); "low"/"moderate"/
"high" interpolate real friction between the codebase's own real best-
case and worst-case live slippage; "stressed" doubles the worst real
disclosed ceiling — a real, disclosed stress multiplier, not a claim
this exact number was ever observed live.

HOW COST IS APPLIED: the real, already-closed trades a zero-friction
backtest produced are NEVER re-simulated with different entries/exits —
the setups themselves are unaffected by cost (a cost model has no way to
predict a different bar's own real high/low). Instead, each trade's own
real, already-known entry price and risk (|entry - stop|) are used to
convert a real round-trip basis-point friction cost (entry leg + exit
leg, the same "pays it twice" convention `TRANSACTION_COST_BPS`'s own
docstring already establishes) into R-multiple terms, deducted from that
trade's own realized R. An OPEN trade (no real exit price yet) is left
untouched — this module never fabricates a cost against an outcome that
never resolved.

`verdict` is real and disclosed: `cost_resilient` when the "base" (zero-
friction) scenario's own real expectancy sign survives all the way to
the "stressed" scenario; `cost_sensitive` when it flips to zero or
negative anywhere along the ladder — an honest, structural analog to
this same directive's own "COST-SENSITIVE" verdict vocabulary (see
app/model_validation.py's own module docstring for that framing).
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.backtest_primitives import aggregate_bucket
from app.execution_quality import BASE_SLIPPAGE_BPS, MAX_SLIPPAGE_BPS
from app.market_data import market_data_provider
from app.portfolio import TRANSACTION_COST_BPS
from app.schemas import CompiledStrategyDefinition, CostSensitivityResult, CostSensitivityScenario, EmaPullbackTradeRecord
from app.strategy_engine import DEFAULT_CANDLES_PER_SYMBOL, DEFAULT_TIMEFRAME, _unsupported_indicators, backtest_symbol_over_candles
from app.watchlist import SEED_SYMBOLS

# Every value here is derived directly from this codebase's own existing,
# already-real cost/slippage constants — see this module's own docstring.
COST_SCENARIOS: tuple[tuple[str, float], ...] = (
    ("base (zero friction — every prior backtest engine's own implicit assumption)", 0.0),
    ("low (real transaction cost + real best-case live slippage)", TRANSACTION_COST_BPS + BASE_SLIPPAGE_BPS),
    ("moderate (real transaction cost + the midpoint of the real live slippage range)", TRANSACTION_COST_BPS + (BASE_SLIPPAGE_BPS + MAX_SLIPPAGE_BPS) / 2),
    ("high (real transaction cost + the real live slippage ceiling)", TRANSACTION_COST_BPS + MAX_SLIPPAGE_BPS),
    ("stressed (2x the real live slippage ceiling — a disclosed stress multiplier, not an observed live number)", 2 * (TRANSACTION_COST_BPS + MAX_SLIPPAGE_BPS)),
)


def _apply_cost_to_trades(trades: list[EmaPullbackTradeRecord], cost_bps_per_leg: float) -> list[EmaPullbackTradeRecord]:
    if cost_bps_per_leg <= 0:
        return trades
    adjusted: list[EmaPullbackTradeRecord] = []
    for t in trades:
        if t.outcome == "open" or t.exit_price is None:
            adjusted.append(t)
            continue
        risk = abs(t.entry_price - t.stop_price)
        if risk <= 0:
            adjusted.append(t)
            continue
        # Round trip: entry leg + exit leg, the same "pays it twice"
        # convention app/portfolio.py's own TRANSACTION_COST_BPS already
        # established.
        cost_in_price_terms = t.entry_price * (cost_bps_per_leg / 10_000) * 2
        cost_in_r = cost_in_price_terms / risk
        adjusted.append(t.model_copy(update={"r_multiple_realized": round(t.r_multiple_realized - cost_in_r, 4)}))
    return adjusted


def run_cost_sensitivity(
    definition: CompiledStrategyDefinition,
    *,
    symbols: list[str] | None = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    candles_per_symbol: int = DEFAULT_CANDLES_PER_SYMBOL,
) -> CostSensitivityResult:
    """The one real entry point. Refuses exactly when
    `run_compiled_strategy_backtest()` would."""
    now_iso = datetime.now(timezone.utc).isoformat()
    result_id = f"cost-sensitivity-{definition.id}"

    def _refusal(reason: str) -> CostSensitivityResult:
        return CostSensitivityResult(id=result_id, definitionId=definition.id, definitionVersion=definition.version, scenarios=[], verdict="insufficient_data", detail=reason, dataHonestyNote="No real trades were available to cost-adjust.", generatedAt=now_iso)

    if definition.status != "compiled":
        return _refusal(f"This definition is not backtestable: status={definition.status!r}. {definition.detail}")
    unsupported = _unsupported_indicators(definition)
    if unsupported:
        return _refusal(f"This engine's current v1 scope cannot resolve indicator(s) {sorted(unsupported)} — a real, disclosed coverage gap, not a fabricated result.")

    resolved_symbols = symbols if symbols is not None else [s for s, _name, _cat in SEED_SYMBOLS]
    raw_trades: list[EmaPullbackTradeRecord] = []
    for symbol in resolved_symbols:
        candles = market_data_provider.get_candles(symbol, timeframe, candles_per_symbol)
        raw_trades += backtest_symbol_over_candles(definition, symbol, candles)

    if not raw_trades:
        return _refusal("No real trades were generated by this definition against the requested real candle history — nothing to cost-adjust.")

    scenarios: list[CostSensitivityScenario] = []
    for label, bps in COST_SCENARIOS:
        adjusted = _apply_cost_to_trades(raw_trades, bps)
        bucket = aggregate_bucket(label, adjusted)
        scenarios.append(CostSensitivityScenario(label=label, costBpsPerLeg=round(bps, 3), bucket=bucket))

    base_bucket = scenarios[0].bucket
    stressed_bucket = scenarios[-1].bucket
    if base_bucket.verdict != "enough_evidence" or base_bucket.expectancy_r is None:
        verdict = "insufficient_data"
        detail = f"The zero-friction base scenario itself has too few real closed trades ({base_bucket.trade_count}) for a bucket-level verdict — cannot yet read real cost sensitivity."
    elif base_bucket.expectancy_r <= 0:
        verdict = "insufficient_data"
        detail = "The zero-friction base scenario is not itself profitable — cost sensitivity is only a meaningful question once there is a real edge to erode."
    elif stressed_bucket.expectancy_r is not None and stressed_bucket.expectancy_r > 0:
        verdict = "cost_resilient"
        detail = (
            f"Real expectancy stays positive ({stressed_bucket.expectancy_r:+.2f}R) even under the stressed friction scenario "
            f"({scenarios[-1].cost_bps_per_leg:g} bps/leg) — this edge is not merely an artifact of this engine's own zero-friction assumption."
        )
    else:
        verdict = "cost_sensitive"
        flip_scenario = next((s for s in scenarios if s.bucket.expectancy_r is not None and s.bucket.expectancy_r <= 0), scenarios[-1])
        detail = (
            f"Real expectancy turns zero or negative at the '{flip_scenario.label}' scenario ({flip_scenario.cost_bps_per_leg:g} bps/leg) — "
            f"this edge (base expectancy {base_bucket.expectancy_r:+.2f}R) may only exist because this engine's own zero-friction assumption "
            "understates real trading costs."
        )

    return CostSensitivityResult(
        id=result_id,
        definitionId=definition.id,
        definitionVersion=definition.version,
        scenarios=scenarios,
        verdict=verdict,  # type: ignore[arg-type]
        detail=detail,
        dataHonestyNote=(
            "Every scenario replays the exact same real, already-closed trades the zero-friction backtest produced — only the real "
            "round-trip basis-point cost deducted from each trade's own realized R changes between scenarios, never the entries/exits "
            "themselves. Cost figures are this codebase's own existing real app/portfolio.py TRANSACTION_COST_BPS and "
            "app/execution_quality.py BASE_SLIPPAGE_BPS/MAX_SLIPPAGE_BPS constants — the same numbers live paper trading already charges."
        ),
        generatedAt=now_iso,
    )
