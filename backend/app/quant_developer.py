"""Forge — Quantitative Research & Intelligence System, Piece 7. The
Quant Developer.

The other four real quant roles this system built are about the
strategies themselves: Vector (Chief Quant) researches whether a
strategy has real edge; Meridian (Model Validator, app/model_validation.py)
independently reviews whether the evidence behind that edge is sound;
Sentinel/Guardian/Keystone manage risk. None of them ever ask a
different, genuinely engineering-shaped question: is the TOOL that
produced this evidence itself reliable?

app/strategy_lab.py's run_strategy_monte_carlo() bootstraps exactly
MONTE_CARLO_PATHS (200) simulated trade sequences per run — a fixed,
global constant, not something that varies per strategy. Every real
StrategyMonteCarloResult on file reports VaR95/VaR99/CVaR95/CVaR99 —
percentile and tail-mean reads off that same 200-path array (Piece 3).
The 5% tail of 200 paths is 10 real samples; the 1% tail is 2. A
99th-percentile statistic estimated from 2 real data points is not a
reliable read no matter how sound the strategy's underlying edge is —
this is a real, checkable statistical-adequacy problem, not a
fabricated one, and none of the other four quant roles ever look at it:
Meridian reviews the STRATEGY's tail risk (an existing check already
gates on probability_of_ruin_pct), never whether the SAMPLE SIZE behind
that read is adequate for the specific percentile being reported.

MIN_RELIABLE_TAIL_SAMPLES/MIN_MARGINAL_TAIL_SAMPLES below are the one
piece of this whole Quantitative Research & Intelligence System with no
existing in-codebase precedent to cite — no prior piece needed a
"how many tail observations are enough" bar. 20/10 are disclosed here
as a deliberately chosen, configurable research assumption (a common
rule of thumb in bootstrap/tail-risk estimation literature: under
~10 tail observations, a percentile read is dominated by single-point
noise; ~20+ is a conventional floor for treating it as directionally
stable) — not a fact this codebase measured, and the assessment's own
`reasoning`/`threshold_source` fields say so explicitly, following the
exact same disclosure discipline every other new threshold in this
system used (see app/model_validation.py's own threshold-provenance
table).

This assessment is a standing fact about the PIPELINE, not a
per-strategy artifact — every real run uses the identical global
MONTE_CARLO_PATHS, so recomputing per strategy would just repeat the
same verdict. It is recomputed fresh on every read (never persisted or
capped) and cross-checked against every real StrategyMonteCarloResult
currently on file, so a future drift between the documented constant
and what a run actually used is caught, not assumed."""
from __future__ import annotations

from datetime import datetime, timezone

from app.schemas import MonteCarloReliabilityAssessment, MonteCarloReliabilityVerdict, StrategyMonteCarloResult
from app.strategy_lab import MONTE_CARLO_PATHS

MIN_RELIABLE_TAIL_SAMPLES = 20
MIN_MARGINAL_TAIL_SAMPLES = 10


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _verdict(tail_samples: int) -> MonteCarloReliabilityVerdict:
    if tail_samples >= MIN_RELIABLE_TAIL_SAMPLES:
        return "reliable"
    if tail_samples >= MIN_MARGINAL_TAIL_SAMPLES:
        return "marginal"
    return "unreliable"


def assess_monte_carlo_reliability(
    monte_carlo_results: list[StrategyMonteCarloResult],
) -> MonteCarloReliabilityAssessment:
    tail_95 = int(MONTE_CARLO_PATHS * 0.05)
    tail_99 = int(MONTE_CARLO_PATHS * 0.01)
    verdict_95 = _verdict(tail_95)
    verdict_99 = _verdict(tail_99)
    recommended_paths_for_99 = int(MIN_RELIABLE_TAIL_SAMPLES / 0.01)

    observed_path_counts = {r.paths_simulated for r in monte_carlo_results}
    consistent = observed_path_counts.issubset({MONTE_CARLO_PATHS})

    reasoning = (
        f"MONTE_CARLO_PATHS is fixed at {MONTE_CARLO_PATHS} real simulated paths per run. "
        f"That gives {tail_95} real samples in the 5% tail (VaR95/CVaR95 read as '{verdict_95}') and "
        f"{tail_99} real samples in the 1% tail (VaR99/CVaR99 read as '{verdict_99}'). "
        f"A 99th-percentile statistic estimated from only {tail_99} real data points is dominated by "
        f"single-point noise, regardless of how sound the underlying strategy's edge is. "
        f"Reaching {MIN_RELIABLE_TAIL_SAMPLES} real 1%-tail samples (this system's own reliability floor) "
        f"would need {recommended_paths_for_99} simulated paths per run, not {MONTE_CARLO_PATHS}."
    )
    if not consistent:
        observed = ", ".join(str(c) for c in sorted(observed_path_counts))
        reasoning += (
            f" Also flagging a real inconsistency: at least one StrategyMonteCarloResult on file used a "
            f"different path count ({observed}) than the currently audited constant — this reliability "
            f"read no longer matches every real result in the company."
        )

    return MonteCarloReliabilityAssessment(
        pathsSimulated=MONTE_CARLO_PATHS,
        tailSampleCount95Pct=tail_95,
        tailSampleCount99Pct=tail_99,
        verdict95Pct=verdict_95,
        verdict99Pct=verdict_99,
        minReliableTailSamples=MIN_RELIABLE_TAIL_SAMPLES,
        minMarginalTailSamples=MIN_MARGINAL_TAIL_SAMPLES,
        recommendedPathsForReliable99Pct=recommended_paths_for_99,
        realResultsAudited=len(monte_carlo_results),
        observedPathCountsConsistent=consistent,
        reasoning=reasoning,
        thresholdSource=(
            f"MIN_RELIABLE_TAIL_SAMPLES={MIN_RELIABLE_TAIL_SAMPLES}/MIN_MARGINAL_TAIL_SAMPLES="
            f"{MIN_MARGINAL_TAIL_SAMPLES} (app/quant_developer.py) — a disclosed, deliberately chosen "
            f"bootstrap/tail-risk-estimation rule of thumb, not an existing in-codebase constant; see "
            f"this module's own docstring for why no prior piece established one."
        ),
        generatedAt=_now_iso(),
    )
