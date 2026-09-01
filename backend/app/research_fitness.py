"""app/research_fitness.py — CEO directive "TradeTown — Phase 9: Full
Autonomous Quant Research Factory," Phase 6 (Robustness-First Fitness):
"DO NOT rank strategies primarily by raw profit... A strategy with
$100k profit + 35% drawdown must NOT beat $30k profit + 10% drawdown
simply because the return is larger."

RESEARCH FIRST. This module computes NO new backtest math — every axis
below is a direct read of an already-real, already-computed field:
`iteration.experiment.backtest.overall` (app/backtest_primitives.py's
`aggregate_bucket()`), `iteration.experiment.complexity`
(app/strategy_complexity.py). Its only job is ORDERING a set of sibling
`FactoryCandidateRecord`s (real mutation children of the same parent —
see app/research_factory.py's own multi-child branching) so the factory
can pick which one continues the lineage, without that choice ever
being driven primarily by raw return.

THE REAL, DISCLOSED RULE — A SORT KEY, NEVER A BLACK-BOX SCORE. Every
axis below is independently inspectable in `describe_fitness_rank()`'s
own real text, in this fixed priority order:

  1. LIFECYCLE TIER — a real survivor/candidate always outranks a
     rejected/compile-rejected sibling; this is the existing, unmodified
     `classify_candidacy()`/`derive_lifecycle_stage()` gate, never
     re-decided here.
  2. EVIDENCE FLOOR — a sibling with zero real closed trades ranks below
     every sibling with at least one, regardless of any other axis (an
     empty bucket has no real robustness to compare).
  3. DRAWDOWN SEVERITY (smaller real `|maxDrawdownR|` wins) — the
     directive's own explicit example: this axis is checked BEFORE
     profit factor or expectancy, so a deep-drawdown/high-return sibling
     never beats a shallow-drawdown/lower-return one on this rule alone.
  4. PROFIT FACTOR (higher wins) — real, already-computed.
  5. EXPECTANCY (higher wins) — real, already-computed.
  6. COMPLEXITY (lower `complexityScore` wins) — Phase 12's own explicit
     tie-breaker, reusing app/strategy_complexity.py's already-real
     count, never re-derived.

Ties propagate to the next axis exactly as listed; two siblings that
are identical on every axis above stay tied (Python's stable sort
preserves their original generation order in that case — never an
arbitrary coin flip).

NEVER a fabricated single number. There is no `fitnessScore` field
anywhere in this module or its schema — only a real, disclosed,
axis-by-axis ORDERING and a plain-English explanation citing the exact
real values that decided it (`describe_fitness_rank()`), matching
Section 20's "no meaningless AI score" rule this codebase already
applies to `ResearchScorecardClassification`/`OverfittingDiagnosis`.
"""
from __future__ import annotations

from app.schemas import CandidateLifecycleStage, FactoryCandidateRecord

# Lower = better. `survivor`/`challenger_eligible` are the real terminal
# "cleared everything" states; `candidate` cleared the base funnel but
# not every research-candidate requirement; `backtested`/`generated`
# are real transitional states this codebase's own
# `derive_lifecycle_stage()` never actually produces as a candidate's
# FINAL stage (see that function's own docstring) but are handled here
# defensively rather than assumed unreachable; `duplicate_pruned`/
# `rejected` are real, disclosed failures; `compile_rejected` is worst
# — it never even reached a real backtest.
_LIFECYCLE_RANK: dict[CandidateLifecycleStage, int] = {
    "survivor": 0,
    "challenger_eligible": 0,
    "candidate": 1,
    "adversarial_tested": 1,
    "backtested": 2,
    "generated": 2,
    "rejected": 3,
    "duplicate_pruned": 3,
    "compile_rejected": 4,
}


def _fitness_key(candidate: FactoryCandidateRecord) -> tuple[int, int, float, float, float, int]:
    lifecycle_rank = _LIFECYCLE_RANK.get(candidate.lifecycle_stage, 3)
    if candidate.iteration is None:
        return (lifecycle_rank, 1, float("inf"), 0.0, float("-inf"), 0)
    bucket = candidate.iteration.experiment.backtest.overall
    has_no_evidence = 1 if bucket.trade_count == 0 else 0
    drawdown_severity = abs(bucket.max_drawdown_r) if bucket.max_drawdown_r is not None else float("inf")
    profit_factor = bucket.profit_factor if bucket.profit_factor is not None else 0.0
    expectancy_r = bucket.expectancy_r if bucket.expectancy_r is not None else float("-inf")
    complexity_score = candidate.iteration.experiment.complexity.complexity_score
    return (lifecycle_rank, has_no_evidence, drawdown_severity, -profit_factor, -expectancy_r, complexity_score)


def rank_candidates(candidates: list[FactoryCandidateRecord]) -> list[FactoryCandidateRecord]:
    """Best-first. A pure, deterministic sort — see this module's own
    docstring for the exact fixed axis order. Stable: candidates tied on
    every real axis keep their original relative order."""
    return sorted(candidates, key=_fitness_key)


def describe_fitness_rank(candidate: FactoryCandidateRecord, *, rank: int, total_siblings: int) -> str:
    """Real, human-readable explanation of exactly why `candidate`
    landed at `rank` (1-indexed, 1 = best) among `total_siblings` real
    mutation children of the same parent — cites the exact real values
    `rank_candidates()` compared, never a vague "AI judged this best.\""""
    if candidate.iteration is None:
        return f"Rank {rank}/{total_siblings}: never reached a real backtest (compile_status={candidate.compile_status!r}) — ranked below every sibling that did."
    bucket = candidate.iteration.experiment.backtest.overall
    if bucket.trade_count == 0:
        return f"Rank {rank}/{total_siblings}: real backtest produced zero closed trades — no real evidence to rank on any robustness axis."
    complexity = candidate.iteration.experiment.complexity.complexity_score
    return (
        f"Rank {rank}/{total_siblings}: real drawdown {bucket.max_drawdown_r:.2f}R, "
        f"profit factor {bucket.profit_factor if bucket.profit_factor is not None else 'N/A'}, "
        f"expectancy {bucket.expectancy_r if bucket.expectancy_r is not None else 'N/A'}R, "
        f"complexity score {complexity} — ranked by drawdown severity first, then profit factor, then expectancy, "
        "then complexity as the final tie-break (never by raw return)."
    )
