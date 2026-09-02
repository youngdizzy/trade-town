"""app/research_pareto.py — CEO directive "TradeTown — Autonomous
Mutation Application + Pareto Survivor Engine": "Implement a robustness-
first Pareto selection system... A candidate should only dominate a
parent when it improves or preserves the important dimensions without
unacceptable regression elsewhere... Implement explicit Pareto dominance
rather than a single opaque 'AI score.'"

PHASE 0 FORENSIC RECON, SUMMARIZED. Tracing `app/research_factory.py`'s
real closed-loop mutation engine (already shipped in an earlier phase —
see that module's own docstring) found the ONE genuinely missing piece
this directive's title names: a real Pareto frontier. What already
existed was `app/research_fitness.py::rank_candidates()` — a real,
disclosed LEXICOGRAPHIC sort (drawdown, then profit factor, then
expectancy, then complexity) used to pick a single winner among sibling
mutation children. A lexicographic order is NOT a Pareto frontier: it
always produces one strict total ordering, so a sibling that is
materially better on one axis and only trivially worse on an earlier-
priority axis is still ranked below a sibling with no such trade-off —
exactly the kind of single-dimension domination this directive's
Section 6 forbids ("a strategy with $100k profit + 35% drawdown must NOT
beat $30k profit + 10% drawdown simply because the return is larger" is
the drawdown-first case `rank_candidates()` already gets right; the
directive additionally requires that when two candidates trade off
DIFFERENT axes against each other — e.g. A has better drawdown, B has
better cost resilience — neither is silently declared the winner without
disclosing that trade-off exists at all).

WHAT THIS MODULE ADDS, AND WHAT IT DELIBERATELY DOES NOT DUPLICATE. This
module computes NO new backtest math and NO new statistical test — every
dimension below is a direct read of an already-real, already-computed
field on a `FactoryCandidateRecord`: `iteration.scorecard` (the SAME
denormalized, already-real read `app/research_discovery.py`'s own family
statistics already use for identical cross-candidate comparisons) and
`adversarial_result` (`app/adversarial_research.py`). `app/research_
fitness.py::rank_candidates()` is NOT replaced — see `app/research_
factory.py`'s own updated docstring for exactly how the two now compose:
Pareto dominance decides who is even IN CONTENTION (the non-dominated
set); the existing, unmodified lexicographic comparator still breaks
ties among Pareto-equals, so a real, disclosed, deterministic single
choice is still always available when the factory needs to pick which
non-dominated candidate's mutation lineage continues.

THE REAL DOMINANCE RULE, DISCLOSED. Candidate A dominates candidate B
iff, over every dimension where BOTH have real, available evidence
(insufficient evidence on either side excludes that dimension from the
comparison entirely — Section 19's "insufficient evidence is not
failure" rule, contributing a tie rather than a fabricated advantage or
penalty), A is at least as good as B on every one of those dimensions,
AND strictly better on at least one. A and B are only ever compared when
they share the same real `dataProvenance` (Section 13) — comparing
simulated evidence against a different provenance would blend
incomparable evidence into one ranking, which this module never does; in
this codebase's current mock-only market-data environment every
candidate in one factory run shares the same provenance in practice, so
this guard is a real, disclosed safety rail rather than a live
differentiator today.

DIMENSIONS (Section 6's own "at minimum" list, each sourced from an
existing field — see `_axis_scores()` for the exact real source of
each): expectancy, max drawdown, profit factor, trade count (the real
evidence floor), walk-forward credibility, cost resilience, adversarial
robustness (extended cost-stress survival), outlier dependence, regime
robustness, benchmark relationship, and statistical evidence quality
(`StrategyScorecard.statistical_evidence_state`). A full pairwise
statistical significance test between every sibling (extending
`app/statistical_comparison.py`'s bootstrap, built today only for
champion-vs-challenger) is real, tractable future work — not attempted
this pass; trade count already stands in as this module's real,
disclosed evidence-quantity dimension, and `statistical_evidence_state`
carries whatever this codebase's own existing pipeline has already
concluded, never a new significance computation.

NEVER A FABRICATED SINGLE NUMBER. There is no `paretoScore` field
anywhere in this module or its schema (`app/schemas.py`'s
`ParetoFrontierEntry`) — only a real, disclosed, axis-by-axis comparison
and a plain-English `reason` citing the actual real values that decided
it, matching this codebase's own `describe_fitness_rank()` idiom.
"""
from __future__ import annotations

from app.schemas import FactoryCandidateRecord, ParetoDimensionValue, ParetoFrontierEntry, ParetoStatus

# Real, disclosed ladders for the categorical/verdict-shaped dimensions
# below — lower rank = better. Any real value NOT listed here (including
# an explicit "insufficient_data"/"regime_unknown"/`None`) is treated as
# UNKNOWN/NEUTRAL by `_axis_scores()`, never mapped into this ladder —
# see that function's own handling.
_WALK_FORWARD_RANK: dict[str, int] = {"stable": 0, "unstable": 2}
_COST_RANK: dict[str, int] = {"cost_resilient": 0, "cost_sensitive": 2}
_REGIME_RANK: dict[str, int] = {"regime_robust": 0, "regime_specialist": 1, "regime_fragile": 2}
_OUTLIER_RANK: dict[bool, int] = {False: 0, True: 2}
_ADVERSARIAL_RANK: dict[bool, int] = {True: 0, False: 2}
# `StrategyScorecard.statistical_evidence_state` mirrors app/evidence_
# quality.py's own real `EvidenceState` ladder — reused verbatim, never
# re-derived or re-ordered independently of that module's own real
# priority.
_EVIDENCE_RANK: dict[str, int] = {
    "external_data_validated": 0,
    "holdout_validated": 0,
    "research_validated": 1,
    "simulated_only": 1,
    "insufficient_data": 2,
}

# (dimension key, human-readable label) — iteration order here is also
# the real, disclosed order `ParetoFrontierEntry.dimensions` is reported
# in, so a reader always sees the same axes in the same order.
_DIMENSION_LABELS: tuple[tuple[str, str], ...] = (
    ("expectancy_r", "Expectancy"),
    ("max_drawdown_r", "Max drawdown"),
    ("profit_factor", "Profit factor"),
    ("trade_count", "Trade count (evidence floor)"),
    ("walk_forward", "Walk-forward credibility"),
    ("cost_resilience", "Cost resilience"),
    ("adversarial_robustness", "Adversarial robustness (extended cost stress)"),
    ("outlier_dependence", "Outlier dependence"),
    ("regime_robustness", "Regime robustness"),
    ("benchmark_relationship", "Benchmark relationship"),
    ("statistical_evidence", "Statistical evidence quality"),
)


def _axis_scores(candidate: FactoryCandidateRecord) -> dict[str, tuple[float | None, str]]:
    """Real per-axis `(comparable_score, display_value)` for one
    candidate. `comparable_score` is always normalized LOWER-IS-BETTER
    so `_dominates()` below is one uniform rule regardless of each real
    axis's own natural direction; `None` is a real, disclosed "no
    evidence on this axis" — see this module's own docstring for why
    that contributes a tie, never a fabricated penalty."""
    scores: dict[str, tuple[float | None, str]] = {key: (None, "no evidence") for key, _ in _DIMENSION_LABELS}
    if candidate.iteration is None:
        return scores
    scorecard = candidate.iteration.scorecard

    def numeric(key: str, raw: float | int | None, *, higher_is_better: bool, fmt: str) -> None:
        if raw is None:
            return
        value = float(raw)
        scores[key] = (-value if higher_is_better else value, fmt.format(value))

    def ranked(key: str, raw_display: str | None, ladder: dict[str, int]) -> None:
        if raw_display is None:
            return
        rank = ladder.get(raw_display)
        scores[key] = (float(rank) if rank is not None else None, raw_display)

    numeric("expectancy_r", scorecard.expectancy_r, higher_is_better=True, fmt="{:.3f}R")
    numeric("max_drawdown_r", (abs(scorecard.max_drawdown_r) if scorecard.max_drawdown_r is not None else None), higher_is_better=False, fmt="{:.2f}R")
    numeric("profit_factor", scorecard.profit_factor, higher_is_better=True, fmt="{:.2f}")
    numeric("trade_count", scorecard.trade_count, higher_is_better=True, fmt="{:.0f} trades")
    numeric("benchmark_relationship", scorecard.excess_return_approx_pct, higher_is_better=True, fmt="{:+.2f}% excess (approx)")
    ranked("walk_forward", scorecard.walk_forward_verdict, _WALK_FORWARD_RANK)
    ranked("cost_resilience", scorecard.cost_sensitivity_verdict, _COST_RANK)
    ranked("regime_robustness", scorecard.regime_robustness_verdict, _REGIME_RANK)
    ranked("statistical_evidence", scorecard.statistical_evidence_state, _EVIDENCE_RANK)
    if scorecard.outlier_dependent is not None:
        rank = _OUTLIER_RANK[scorecard.outlier_dependent]
        scores["outlier_dependence"] = (float(rank), "outlier_dependent" if scorecard.outlier_dependent else "not_outlier_dependent")
    if candidate.adversarial_result is not None:
        survives = candidate.adversarial_result.extended_cost_attack.survives_beyond_stress
        if survives is not None:
            rank = _ADVERSARIAL_RANK[survives]
            scores["adversarial_robustness"] = (float(rank), "survives_beyond_stress" if survives else "fails_beyond_stress")
    return scores


def _data_provenance(candidate: FactoryCandidateRecord) -> str | None:
    return candidate.adversarial_result.data_provenance if candidate.adversarial_result is not None else None


def _dominates(a_scores: dict[str, tuple[float | None, str]], b_scores: dict[str, tuple[float | None, str]]) -> tuple[bool, list[str]]:
    """Real dominance check — returns `(dominates, winning_dimensions)`.
    `winning_dimensions` names every real axis where `a` was strictly
    better, for a disclosed, non-opaque reason string."""
    at_least_as_good_everywhere = True
    winning_dimensions: list[str] = []
    for key, _ in _DIMENSION_LABELS:
        a_val, _ = a_scores[key]
        b_val, _ = b_scores[key]
        if a_val is None or b_val is None:
            continue
        if a_val > b_val:
            at_least_as_good_everywhere = False
            break
        if a_val < b_val:
            winning_dimensions.append(key)
    if not at_least_as_good_everywhere or not winning_dimensions:
        return False, []
    return True, winning_dimensions


def compute_pareto_frontier(candidates: list[FactoryCandidateRecord]) -> dict[str, ParetoFrontierEntry]:
    """Real Pareto frontier over `candidates` — only candidates with a
    real `iteration` (i.e. an actual backtest, never a compile_rejected
    or duplicate_pruned record with no evidence to compare) get an
    entry; every other candidate is simply absent from the returned dict
    (its own `pareto_status` stays `None` — an honest "not enough
    evidence to place on any frontier," never a default "dominated").
    Comparisons only ever happen between candidates sharing the same
    real `dataProvenance` — see this module's own docstring."""
    pool = [c for c in candidates if c.iteration is not None]
    scores_by_id = {c.id: _axis_scores(c) for c in pool}
    provenance_by_id = {c.id: _data_provenance(c) for c in pool}
    labels = dict(_DIMENSION_LABELS)

    entries: dict[str, ParetoFrontierEntry] = {}
    for candidate in pool:
        dominated_by: list[str] = []
        dominance_reasons: dict[str, list[str]] = {}
        for other in pool:
            if other.id == candidate.id:
                continue
            if provenance_by_id[candidate.id] != provenance_by_id[other.id]:
                continue
            dominates, winning_dims = _dominates(scores_by_id[other.id], scores_by_id[candidate.id])
            if dominates:
                dominated_by.append(other.id)
                dominance_reasons[other.id] = winning_dims

        dims = [
            ParetoDimensionValue(dimension=labels[key], displayValue=display, available=(value is not None))
            for key, (value, display) in scores_by_id[candidate.id].items()
        ]
        if dominated_by:
            first = dominated_by[0]
            axis_names = ", ".join(labels[d] for d in dominance_reasons[first])
            reason = f"Dominated by candidate '{first}' (at least as good on every comparable dimension, strictly better on: {axis_names})."
            if len(dominated_by) > 1:
                reason += f" Also dominated by {len(dominated_by) - 1} other real candidate(s)."
            status: ParetoStatus = "dominated"
        else:
            reason = "Non-dominated — no other real candidate in this comparison pool is at least as good on every comparable dimension while strictly better on one."
            status = "non_dominated"

        entries[candidate.id] = ParetoFrontierEntry(candidateId=candidate.id, paretoStatus=status, dominatedBy=dominated_by, dimensions=dims, reason=reason)
    return entries
