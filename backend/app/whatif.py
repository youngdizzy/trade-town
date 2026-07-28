"""WhatIfSimulation — v0.7 Feature 16, the What-If Simulation Lab.

Stress-tests a trade candidate against a handful of plausible future
market conditions before the CEO decides — never a prediction of what
WILL happen, only how the position would likely fare IF each condition
occurred, the same "process, not outcome" boundary app/confidence.py
already draws for the Decision Confidence Engine.

Every simulated path is a bootstrap resample of the symbol's own real
recent bar-to-bar returns (the same Candle series app/executive.py's
technical vote already fetches) — real historical price behavior sets
the *scale* of every number here. Each scenario's drift bias and any
shock are expressed as a multiple of the symbol's own real measured
per-bar volatility (never an absolute invented percentage), with an
explicit, fixed direction baked into what each named scenario actually
means (`_SCENARIO_PARAMS`) — a "what if bullish continuation happened"
read is a genuine hypothetical, not just "the current trend continues"
(that's what `baseline` below already represents). The one exception is
`trend_failure`, which by definition fades whatever the symbol's real
current trend direction actually is, so its sign is resolved at request
time rather than fixed in the table. This is a simple historical/
bootstrap Monte Carlo, not a real options-pricing or regime-switching
model.

Computed fresh on every request rather than persisted: unlike a
TradeDecision or CeoDecisionRecord, a what-if read has no permanence
requirement in the v0.7 brief ("allow the player to inspect every
scenario" — not "store for later review," unlike Feature 17's Debate),
and this codebase has already been bitten once by an unbounded persisted
list bloating the save payload past nginx's body-size limit (see
nexus.py's MAX_DECISIONS comment) — no reason to risk that class of bug
for a read that's just as honest recomputed live.
"""
from __future__ import annotations

import random
import statistics

from app.market_data import Candle, trend_pct, volatility_pct
from app.schemas import ScenarioResult, ScenarioType, WhatIfSimulation

N_PATHS = 200
HOLD_BARS = 20

_SCENARIO_LABEL: dict[ScenarioType, str] = {
    "bullish_continuation": "Strong Bullish Continuation",
    "bearish_reversal": "Strong Bearish Reversal",
    "sideways_consolidation": "Sideways Consolidation",
    "high_volatility": "High Volatility",
    "low_volatility": "Low Volatility",
    "news_shock": "News Shock",
    "gap_up": "Gap Up",
    "gap_down": "Gap Down",
    "trend_failure": "Trend Failure",
    "breakout_confirmation": "Breakout Confirmation",
    "liquidity_sweep": "Liquidity Sweep",
    "flash_crash": "Flash Crash",
}

_SCENARIO_INVALIDATION: dict[ScenarioType, str] = {
    "bullish_continuation": "A close back below the sample's starting price invalidates this thesis.",
    "bearish_reversal": "A close back above the sample's starting price invalidates this thesis.",
    "sideways_consolidation": "A sustained break of the recent trading range invalidates this thesis.",
    "high_volatility": "A return to the recent average bar range invalidates this thesis.",
    "low_volatility": "A volatility spike well beyond the recent average invalidates this thesis.",
    "news_shock": "No headline-driven move materializes before the position closes.",
    "gap_up": "Price fails to open beyond the recent trading range.",
    "gap_down": "Price fails to open beyond the recent trading range.",
    "trend_failure": "The prior trend resumes instead of fading.",
    "breakout_confirmation": "Price closes back inside the pre-breakout range.",
    "liquidity_sweep": "No sharp spike-and-reversion move occurs.",
    "flash_crash": "No extreme single-bar move occurs.",
}

# (drift bias as a multiple of the symbol's own real per-bar volatility,
# volatility multiplier on that same real per-bar volatility, optional
# one-bar shock as a multiple of it too — applied at a random bar in the
# path). "news_shock" additionally randomizes the shock's sign per path,
# since a real headline's direction isn't something this codebase can
# forecast. `trend_failure`'s bias sign is resolved dynamically in
# run_whatif_simulation against the symbol's real current trend, not
# fixed here — everything else is a deliberate, direction-fixed
# hypothetical independent of current conditions.
_SCENARIO_PARAMS: dict[ScenarioType, tuple[float, float, float | None]] = {
    "bullish_continuation": (0.5, 1.0, None),
    "bearish_reversal": (-0.5, 1.0, None),
    "sideways_consolidation": (0.0, 0.4, None),
    "high_volatility": (0.0, 2.2, None),
    "low_volatility": (0.0, 0.4, None),
    "news_shock": (0.0, 1.0, 2.5),
    "gap_up": (0.2, 1.0, 2.0),
    "gap_down": (-0.2, 1.0, -2.0),
    "trend_failure": (-0.6, 1.3, None),
    "breakout_confirmation": (0.7, 1.2, 1.5),
    "liquidity_sweep": (0.0, 1.4, -2.0),
    "flash_crash": (0.0, 1.0, -4.0),
}


def _bar_returns(candles: list[Candle]) -> list[float]:
    """Real close-to-close fractional returns from the actual candle
    series — the pool every simulated path resamples from."""
    returns: list[float] = []
    for prev, cur in zip(candles, candles[1:]):
        if prev.close > 0:
            returns.append((cur.close - prev.close) / prev.close)
    return returns


def _percentile(sorted_values: list[float], p: float) -> float:
    if not sorted_values:
        return 0.0
    idx = min(len(sorted_values) - 1, max(0, int(len(sorted_values) * p)))
    return sorted_values[idx]


def _simulate(scenario: ScenarioType, label: str, returns: list[float], bias_per_bar: float, vol_mult: float, shock: float | None) -> ScenarioResult:
    finals: list[float] = []
    max_drawdowns: list[float] = []
    for _ in range(N_PATHS):
        shock_bar = random.randrange(HOLD_BARS) if shock is not None else -1
        cumulative = 0.0
        peak = 0.0
        max_drawdown = 0.0
        for bar in range(HOLD_BARS):
            r = random.choice(returns) * vol_mult + bias_per_bar
            if bar == shock_bar and shock is not None:
                r += shock * random.choice((-1, 1)) if scenario == "news_shock" else shock
            cumulative = (1 + cumulative) * (1 + r) - 1
            peak = max(peak, cumulative)
            max_drawdown = min(max_drawdown, cumulative - peak)
        finals.append(cumulative)
        max_drawdowns.append(max_drawdown)

    finals.sort()
    max_drawdowns.sort()

    return ScenarioResult(
        scenarioType=scenario,
        label=label,
        rewardRangeLowPct=round(_percentile(finals, 0.10) * 100, 2),
        rewardRangeHighPct=round(_percentile(finals, 0.90) * 100, 2),
        mostLikelyPct=round(_percentile(finals, 0.50) * 100, 2),
        typicalDrawdownPct=round(statistics.mean(max_drawdowns) * 100, 2),
        maxRiskPct=round(_percentile(max_drawdowns, 0.05) * 100, 2),
        probabilityOfProfitPct=round(sum(1 for f in finals if f > 0) / len(finals) * 100, 1),
        invalidation=_SCENARIO_INVALIDATION.get(scenario, ""),
    )


def run_whatif_simulation(symbol: str, candles: list[Candle]) -> WhatIfSimulation:
    returns = _bar_returns(candles) or [0.0]
    trend = trend_pct(candles)
    trend_sign = 1.0 if trend >= 0 else -1.0
    real_drift_per_bar = (trend / 100) / max(len(candles) - 1, 1)
    vol_per_bar = volatility_pct(candles) / 100

    scenarios: list[ScenarioResult] = []
    for scenario, (bias_units, vol_mult, shock_units) in _SCENARIO_PARAMS.items():
        if scenario == "trend_failure":
            bias_units = bias_units * trend_sign
        bias_per_bar = bias_units * vol_per_bar
        shock = shock_units * vol_per_bar if shock_units is not None else None
        scenarios.append(_simulate(scenario, _SCENARIO_LABEL[scenario], returns, bias_per_bar, vol_mult, shock))

    # The organic, unbiased case: the symbol's own real measured trend and
    # volatility, resampled with no scenario override at all — the honest
    # "most likely outcome" baseline (see the module docstring for why no
    # cross-scenario probability is invented instead).
    baseline = _simulate("bullish_continuation", "Baseline (No Scenario Bias)", returns, real_drift_per_bar, 1.0, None)

    best_case = max(scenarios, key=lambda s: s.reward_range_high_pct)
    worst_case = min(scenarios, key=lambda s: s.reward_range_low_pct)

    return WhatIfSimulation(
        symbol=symbol,
        holdBars=HOLD_BARS,
        scenarios=scenarios,
        baseline=baseline,
        bestCaseScenario=best_case.scenario_type,
        worstCaseScenario=worst_case.scenario_type,
    )
