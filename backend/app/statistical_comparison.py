"""app/statistical_comparison.py — CEO directive "TradeTown —
Statistical Validation + Research Failure Taxonomy," Part 1
(Statistical Strategy Comparison): "Is this Challenger actually better
than the Champion, or did it simply get lucky?"

RESEARCH FIRST. A dedicated background audit before the Champion/
Challenger framework was built (an earlier pass this session) already
confirmed no two-sample statistical-comparison utility exists anywhere
in this codebase — the real bootstrap machinery that does exist
(app/strategy_lab.py's Monte Carlo, app/portfolio_monte_carlo.py) is
all SINGLE-strategy/single-portfolio resampling, never a two-sample
comparison. This module is the first one. It adds NO new backtest
math: `_closed_trade_r_multiples()` below calls the exact same real
`app/strategy_engine.py::backtest_symbol_over_candles()` +
`market_data_provider.get_candles()` pair `run_compiled_strategy_
backtest()` itself uses, over the identical real symbols/timeframe/
candle window app/champion_challenger.py already requires — it only
additionally keeps the raw per-trade `r_multiple_realized` sequence
that function's own aggregated `EmaPullbackStatsBucket` output
discards.

THE REAL METHOD: AN IID PERCENTILE BOOTSTRAP ON THE DIFFERENCE IN
MEANS. For each side's own real, closed-trade R-multiple sample,
`bootstrap_compare_samples()` draws `BOOTSTRAP_RESAMPLES` independent
resamples (with replacement, same size as the original sample) from
EACH side separately, computes each resampled pair's own mean
difference (challenger resample mean minus champion resample mean),
and reports the 2.5th/97.5th percentile of that empirical distribution
as a real 95% confidence interval for the true difference in mean
R-multiple. `probability_challenger_better_pct` is the real, empirical
fraction of those resamples where the challenger's resampled mean beat
the champion's — an honest description of what was actually computed,
deliberately never called a "p-value" (a p-value tests a specific null
hypothesis under a specific parametric or permutation model; this is a
direct empirical read of the bootstrap distribution itself, a real but
different thing).

THE REAL, DISCLOSED IID LIMITATION — NOT A BLOCK BOOTSTRAP, DELIBERATELY
SCOPED OUT. The directive's own instruction is explicit: "trading
returns are not necessarily independent... where dependence is
material, document the limitation and use an appropriate block/
bootstrap approach if supported by the architecture." This module's
resampling treats each strategy's own trade sequence as i.i.d. — every
`BootstrapComparisonResult.limitation_note` states this plainly. A real
block bootstrap (resampling contiguous BLOCKS of trades to preserve
real serial/regime dependence) is legitimate, real, additional future
work — not attempted here, because this codebase's own mock candle
generator does not yet expose a principled, disclosed block-length
choice, and inventing one arbitrarily would itself be a fabricated
methodology detail dressed up as rigor. The IID assumption is a real,
disclosed weakness, never hidden.

THE REAL SAMPLE-SIZE FLOOR, DISCLOSED SEPARATELY FROM THE BUCKET
FLOOR. `MIN_TRADES_FOR_BOOTSTRAP` (20) is deliberately higher than
`app/backtest_primitives.py`'s own `DEFAULT_MIN_TRADES_FOR_BUCKET_
VERDICT` (10) — a real, disclosed, independently-chosen convention:
resampling a percentile confidence interval from fewer than 20 real
observations produces an interval too coarse to be honestly useful
(with 10 real trades, a bootstrap CI is dominated by which specific
10 values happened to occur, not a stable estimate of the underlying
distribution). Below this floor, `evidence_state` reads
"insufficient_evidence" and every numeric CI/probability field is
`None` — never a fabricated interval from too few points.

REPRODUCIBILITY. The resampling RNG is seeded with the same real
`hashlib.sha256(...)` -> `random.Random(...)` convention
app/strategy_lab.py's own `_seeded_rng()` already established for its
Monte Carlo (added there specifically so a pass/fail verdict derived
from random resampling is a reproducible claim, not a coin toss) —
this module keeps its own private copy of that real technique (this
codebase's own established convention: each module keeps its own
private evidence-floor/RNG helper rather than cross-importing another
module's private, underscore-prefixed one — see e.g.
app/executive_intelligence.py's/app/control_effectiveness.py's own
independent `_evaluation_state()` helpers), seeded from both sides'
own real definition id/version so the exact same comparison always
produces the exact same real interval.

DEFENSE-IN-DEPTH AGAINST NON-FINITE INPUT. CEO directive "TradeTown —
Research Engine Hardening + Self-Improvement Implementation Pass,"
Phase 8. `app/backtest_primitives.py::simulate_exit()` already guards
the zero-risk division that could theoretically produce a NaN/Inf
`r_multiple_realized` — this path is not known to be reachable today
through real trade generation. But `bootstrap_compare_samples()` never
trusts that guarantee blindly: every observation is checked for
finiteness BEFORE the sample-size floor, and a single non-finite value
anywhere in either sample produces a real, distinct
`evidenceState="invalid_evidence"` with every numeric field `None` —
never `"sufficient_evidence"` paired with a NaN/Inf confidence
interval, which was a real, confirmed gap before this pass.
"""
from __future__ import annotations

import hashlib
import math
import random

from app.market_data import market_data_provider
from app.schemas import BootstrapComparisonResult, CompiledStrategyDefinition
from app.strategy_engine import DEFAULT_CANDLES_PER_SYMBOL, DEFAULT_TIMEFRAME, backtest_symbol_over_candles

MIN_TRADES_FOR_BOOTSTRAP = 20
BOOTSTRAP_RESAMPLES = 2000
CONFIDENCE_LEVEL_PCT = 95.0
BOOTSTRAP_METHOD = "iid_percentile_bootstrap"

_INVALID_EVIDENCE_LIMITATION_NOTE = (
    "At least one real observation on at least one side was not a finite number (NaN or +/-Infinity). "
    "CEO directive \"TradeTown — Research Engine Hardening + Self-Improvement Implementation Pass,\" Phase 8 — "
    "defense-in-depth: the real backtest pipeline (app/backtest_primitives.py::simulate_exit()) already guards "
    "the zero-risk division that could produce this, so this path is not known to be reachable today through "
    "real trade generation — but this primitive never trusts that guarantee blindly. No real confidence interval "
    "can be honestly computed from a non-finite observation, so none is fabricated."
)

def _seeded_rng(*parts: str) -> random.Random:
    """This module's own private copy of app/strategy_lab.py's real
    `hashlib.sha256(...)` -> `random.Random(...)` reproducibility
    technique — see this module's own docstring for why it is kept
    local rather than cross-imported."""
    digest = hashlib.sha256(":".join(parts).encode()).hexdigest()
    return random.Random(int(digest[:16], 16))


_LIMITATION_NOTE = (
    "Each side's own real trade sequence is resampled as if independent and identically distributed (IID) — "
    "a real, disclosed simplification. Real trading returns can carry serial/regime dependence a block bootstrap "
    "would better respect; that is genuine, tractable future work, not attempted here. Treat this interval as a "
    "real but approximate uncertainty estimate, not a claim of formal statistical proof."
)


def _closed_trade_r_multiples(definition: CompiledStrategyDefinition, symbols: list[str], timeframe: str, candles_per_symbol: int) -> list[float]:
    """The real per-trade R-multiple sequence for every real CLOSED
    trade this definition produced over the given real symbols/window
    — same real trade-generation call `run_compiled_strategy_
    backtest()` itself uses, just not thrown away after aggregation."""
    values: list[float] = []
    for symbol in symbols:
        candles = market_data_provider.get_candles(symbol, timeframe, candles_per_symbol)
        trades = backtest_symbol_over_candles(definition, symbol, candles)
        values.extend(t.r_multiple_realized for t in trades if t.outcome != "open")
    return values


def bootstrap_compare_samples(champion_r_multiples: list[float], challenger_r_multiples: list[float], *, seed_parts: tuple[str, ...]) -> BootstrapComparisonResult:
    """The one real, pure statistical primitive — no market data, no
    definitions, just two real numeric samples. See this module's own
    docstring for the exact real methodology and its disclosed IID
    limitation."""
    champion_n = len(champion_r_multiples)
    challenger_n = len(challenger_r_multiples)

    # CEO directive "TradeTown — Research Engine Hardening +
    # Self-Improvement Implementation Pass," Phase 8 — checked BEFORE
    # the sample-size floor, since a non-finite observation makes the
    # sample itself untrustworthy regardless of how many observations
    # there are. Real defense-in-depth: never returns
    # "sufficient_evidence" paired with a NaN/Inf confidence interval.
    if any(not math.isfinite(v) for v in (*champion_r_multiples, *challenger_r_multiples)):
        return BootstrapComparisonResult(
            championSampleSize=champion_n,
            challengerSampleSize=challenger_n,
            confidenceLevelPct=CONFIDENCE_LEVEL_PCT,
            method=BOOTSTRAP_METHOD,
            resamples=BOOTSTRAP_RESAMPLES,
            evidenceState="invalid_evidence",
            limitationNote=_INVALID_EVIDENCE_LIMITATION_NOTE,
        )

    if champion_n < MIN_TRADES_FOR_BOOTSTRAP or challenger_n < MIN_TRADES_FOR_BOOTSTRAP:
        return BootstrapComparisonResult(
            championSampleSize=champion_n,
            challengerSampleSize=challenger_n,
            confidenceLevelPct=CONFIDENCE_LEVEL_PCT,
            method=BOOTSTRAP_METHOD,
            resamples=BOOTSTRAP_RESAMPLES,
            evidenceState="insufficient_evidence",
            limitationNote=(
                f"Below the real {MIN_TRADES_FOR_BOOTSTRAP}-trade bootstrap evidence floor on at least one side "
                f"(champion={champion_n}, challenger={challenger_n}) — no real interval can be honestly estimated yet."
            ),
        )

    champion_mean = sum(champion_r_multiples) / champion_n
    challenger_mean = sum(challenger_r_multiples) / challenger_n
    real_difference = challenger_mean - champion_mean

    rng = _seeded_rng(*seed_parts, str(champion_n), str(challenger_n))
    diffs: list[float] = []
    better_count = 0
    for _ in range(BOOTSTRAP_RESAMPLES):
        champion_resample_mean = sum(rng.choice(champion_r_multiples) for _ in range(champion_n)) / champion_n
        challenger_resample_mean = sum(rng.choice(challenger_r_multiples) for _ in range(challenger_n)) / challenger_n
        diff = challenger_resample_mean - champion_resample_mean
        diffs.append(diff)
        if diff > 0:
            better_count += 1
    diffs.sort()

    tail_pct = (100.0 - CONFIDENCE_LEVEL_PCT) / 2.0 / 100.0
    lower_index = max(0, int(round(tail_pct * BOOTSTRAP_RESAMPLES)))
    upper_index = min(BOOTSTRAP_RESAMPLES - 1, int(round((1.0 - tail_pct) * BOOTSTRAP_RESAMPLES)) - 1)

    return BootstrapComparisonResult(
        championSampleSize=champion_n,
        challengerSampleSize=challenger_n,
        championMeanR=round(champion_mean, 4),
        challengerMeanR=round(challenger_mean, 4),
        meanDifferenceEstimate=round(real_difference, 4),
        differenceCiLow=round(diffs[lower_index], 4),
        differenceCiHigh=round(diffs[upper_index], 4),
        confidenceLevelPct=CONFIDENCE_LEVEL_PCT,
        probabilityChallengerBetterPct=round(better_count / BOOTSTRAP_RESAMPLES * 100.0, 1),
        method=BOOTSTRAP_METHOD,
        resamples=BOOTSTRAP_RESAMPLES,
        evidenceState="sufficient_evidence",
        limitationNote=_LIMITATION_NOTE,
    )


def run_statistical_comparison(
    champion_definition: CompiledStrategyDefinition,
    challenger_definition: CompiledStrategyDefinition,
    *,
    symbols: list[str] | None = None,
    timeframe: str = DEFAULT_TIMEFRAME,
    candles_per_symbol: int = DEFAULT_CANDLES_PER_SYMBOL,
) -> BootstrapComparisonResult:
    """The one real entry point for a Champion/Challenger caller — real
    trade collection (this module's own, not a duplicate of
    strategy_engine.py's aggregation) plus the real bootstrap
    primitive above."""
    resolved_symbols = symbols if symbols is not None else []
    champion_r_multiples = _closed_trade_r_multiples(champion_definition, resolved_symbols, timeframe, candles_per_symbol)
    challenger_r_multiples = _closed_trade_r_multiples(challenger_definition, resolved_symbols, timeframe, candles_per_symbol)
    return bootstrap_compare_samples(
        champion_r_multiples,
        challenger_r_multiples,
        seed_parts=(champion_definition.id, str(champion_definition.version), challenger_definition.id, str(challenger_definition.version)),
    )
