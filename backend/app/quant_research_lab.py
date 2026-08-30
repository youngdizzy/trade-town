"""app/quant_research_lab.py — CEO directive "Professional Quant Firm
Phase," Feature 36: the Quant Research Lab's real hypothesis
classification and duplicate-detection logic.

RESEARCH FIRST. app/research_experiment.py already computes a full,
real research pass (backtest, walk-forward, parameter sensitivity, cost
sensitivity, look-ahead audit, overfitting diagnosis) for a compiled
strategy — this module adds NO new backtest math. It exists purely to
(1) turn that real, already-computed evidence into the directive's own
requested `outcome` read (promising/rejected/inconclusive) and (2) give
a CEO/agent a real, honest way to check whether an equivalent experiment
already exists before spending more real compute on a duplicate one.

`_classify_outcome()` reuses `ResearchExperimentRecord.conclusion`/
`overfitting_diagnosis` exactly as `app/research_experiment.py`'s own
`_synthesize_conclusion()` already computed them — this function does
not re-derive evidence, it only relabels the same real conclusion into
the Research Lab's own three-way filing outcome.

`find_similar_experiments()` is a real, disclosed, SIMPLE heuristic —
normalized-word Jaccard overlap between hypothesis strings, combined
with an exact match on `definition_id` + `timeframe` (the same compiled
strategy re-tested is always flagged, regardless of hypothesis wording).
This is NOT a semantic/NLP similarity claim; `reason` always discloses
exactly which signal fired.

CEO directive "Quant Research Factory / Strategy Discovery Engine,"
Phase 14/16 — each match now also carries the matched experiment's own
real `outcome`/`outcomeReason`, so a CEO/agent filing new research sees
not just "this looks similar" but "and it was already REJECTED, here's
why" before spending real compute re-testing a known-failed idea. Real
data already computed for the matched experiment, never recomputed.

Same directive, Phase 10 — `count_experiments_for_family()` gives a
real multiple-testing/research-selection-bias signal: how many times
has this exact strategy name already been tested. Deliberately never a
p-value, false-discovery-rate, or corrected significance level — this
codebase's real backtest outputs (expectancy/profit-factor/Sharpe over
real trades) don't support deriving one honestly, and the directive's
own rule is explicit: never claim statistical significance an
implemented method doesn't actually support.

CEO directive "TradeTown — 11/10 Strategy Factory + Ruthless
Backtesting Engine," Section 12 (Multiple-Testing Penalty) —
`_research_integrity_flag()` turns that real count into one real,
disclosed `normal`/`overtested` flag at `OVERTESTED_FAMILY_THRESHOLD`,
promoted from what was previously only an ad-hoc, hardcoded `>= 5`
check inside `QuantResearchLabView.tsx` (frontend-only, invisible to
any other real consumer) into one single-sourced backend field every
consumer now reads identically. Advisory only in this pass: not wired
into `_classify_outcome()`'s real `outcome` verdict or any promotion
gate — "apply an appropriate... penalty" is the directive's own words,
and an honest penalty needs a real backtest-performance dimension to
discount, which this flag alone does not have; folding it into an
actual scoring penalty is real, tractable future work.
"""
from __future__ import annotations

import re

from app.schemas import (
    AgentId,
    QuantResearchExperiment,
    QuantResearchExperimentSimilarity,
    QuantResearchOutcome,
    ResearchExperimentRecord,
    ResearchIntegrityFlag,
    ResearchRelationship,
    SimilarFailedStrategyMatch,
)

HYPOTHESIS_OVERLAP_THRESHOLD = 0.6
# CEO directive "TradeTown — 11/10 Strategy Factory + Ruthless
# Backtesting Engine," Section 12 (Multiple-Testing Penalty) — a real,
# disclosed threshold, promoted from what was previously only a
# hardcoded `>= 5` check inside `QuantResearchLabView.tsx` (frontend-only,
# never available to any other consumer). One independently-chosen
# convention, not derived from any statistical study — the same
# "real, disclosed, simple threshold, never the only valid one" honesty
# idiom this codebase's other per-module thresholds already use.
OVERTESTED_FAMILY_THRESHOLD = 5
# Matches the same bounded-growth convention app/hall_of_fame.py's own
# MAX_HALL_OF_FAME = 40 still uses — old records fall off the FRONT of
# the list (oldest first), never the newest, which is still an honest
# "never deleted merely because it looks bad" for any realistically-
# sized research program. CEO directive "TradeTown — Research Engine
# Hardening + Self-Improvement Implementation Pass," Phase 14 —
# app/strategy_lab.py's own Hall of Fame/Failed Archive are
# deliberately uncapped now (their own schema docstrings' "permanent,
# never evicted" claim used to be contradicted by a real 40-entry FIFO
# cap; fixed by making it literally true rather than rewording the
# claim), so they're no longer this same example — quant research
# experiments stay a genuinely higher-frequency event (every research
# attempt, not just every retirement), so this list keeps its own real
# cap for now.
MAX_QUANT_RESEARCH_EXPERIMENTS = 100


def cap_quant_research_experiments(items: list[QuantResearchExperiment]) -> list[QuantResearchExperiment]:
    if len(items) > MAX_QUANT_RESEARCH_EXPERIMENTS:
        del items[: len(items) - MAX_QUANT_RESEARCH_EXPERIMENTS]
    return items


def count_experiments_for_family(existing: list[QuantResearchExperiment], *, definition_name: str) -> int:
    """CEO directive "Quant Research Factory / Strategy Discovery
    Engine," Phase 10 — a real count of every already-persisted
    experiment sharing this strategy's real `record.definitionName`,
    across every real compiled version/re-test — the real proxy for
    "how many times has this basic idea already been tried." Counts
    only what's currently retained in `existing` (bounded by
    `MAX_QUANT_RESEARCH_EXPERIMENTS`, oldest evicted first, same as
    every other capped archive in this codebase) — a real, honestly
    partial window, never a fabricated lifetime total."""
    return sum(1 for e in existing if e.record.definition_name == definition_name)


def _research_integrity_flag(family_experiment_count: int | None) -> ResearchIntegrityFlag | None:
    """CEO directive "TradeTown — 11/10 Strategy Factory + Ruthless
    Backtesting Engine," Section 12 — a real, disclosed derivation of
    `family_experiment_count`, `None` only when that count is itself
    unknown (never guessed as "normal")."""
    if family_experiment_count is None:
        return None
    return "overtested" if family_experiment_count >= OVERTESTED_FAMILY_THRESHOLD else "normal"


def _classify_outcome(record: ResearchExperimentRecord) -> tuple[QuantResearchOutcome, str]:
    """A real, deterministic three-way read of the same evidence
    `_synthesize_conclusion()` already produced — never a second,
    independent judgment call."""
    if record.conclusion.startswith("INVALID") or record.conclusion.startswith("REJECTED"):
        return "rejected", record.conclusion
    if record.conclusion.startswith("INSUFFICIENT EVIDENCE"):
        return "inconclusive", record.conclusion
    if record.conclusion.startswith("FRAGILE") or record.overfitting_diagnosis.verdict in ("overfit_suspected", "oos_failure"):
        return "inconclusive", f"{record.conclusion} Overfitting diagnosis: {record.overfitting_diagnosis.verdict}."
    return "promising", record.conclusion


def file_quant_research_experiment(
    record: ResearchExperimentRecord,
    *,
    experiment_id: str,
    hypothesis: str,
    researcher_agent_id: AgentId,
    created_at: str,
    expected_mechanism: str | None = None,
    falsification_criteria: str | None = None,
    existing: list[QuantResearchExperiment] | None = None,
) -> QuantResearchExperiment:
    """The one real entry point for turning an already-real, already-
    computed `ResearchExperimentRecord` into a persistable
    `QuantResearchExperiment` — wraps `_classify_outcome()` so callers
    (app/state.py) never need this module's private classification
    function directly. `expected_mechanism`/`falsification_criteria`
    default to `None` for any caller that hasn't been threaded through
    yet — never fabricated placeholder text.

    CEO directive "Quant Research Factory / Strategy Discovery Engine,"
    Phase 10 — `existing` (the already-persisted list, before this new
    experiment is added) is used to compute a real
    `family_experiment_count` via `count_experiments_for_family()`, +1
    for the experiment being filed right now. `None` (the default, for
    any caller that hasn't threaded the real list through) leaves the
    count honestly `None` rather than fabricating a 1."""
    outcome, outcome_reason = _classify_outcome(record)
    family_experiment_count = count_experiments_for_family(existing, definition_name=record.definition_name) + 1 if existing is not None else None
    return QuantResearchExperiment(
        id=experiment_id,
        hypothesis=hypothesis,
        expectedMechanism=expected_mechanism,
        falsificationCriteria=falsification_criteria,
        familyExperimentCount=family_experiment_count,
        researchIntegrityFlag=_research_integrity_flag(family_experiment_count),
        researcherAgentId=researcher_agent_id,
        outcome=outcome,
        outcomeReason=outcome_reason,
        record=record,
        createdAt=created_at,
    )


def _normalized_words(text: str) -> set[str]:
    return {w for w in re.sub(r"[^a-z0-9\s]", " ", text.lower()).split() if len(w) > 2}


def word_overlap_score(a: str, b: str) -> float:
    """A real, disclosed, simple word-level Jaccard overlap — never a
    claim of semantic/NLP understanding. Made public (not `_`-prefixed)
    by CEO directive "TradeTown — Research Engine Hardening +
    Self-Improvement Implementation Pass," Phase 3, so
    app/failure_taxonomy.py::find_similar_failed_strategies() can reuse
    the exact same real technique against the Failed Strategy Archive
    rather than maintaining a second, drift-prone copy — a deliberate
    departure from this codebase's usual "each module keeps its own
    private RNG/evidence-floor helper" convention, which exists for
    reproducibility-methodology reasons that don't apply to a pure,
    stateless text-similarity utility like this one."""
    words_a, words_b = _normalized_words(a), _normalized_words(b)
    if not words_a or not words_b:
        return 0.0
    intersection = words_a & words_b
    union = words_a | words_b
    return round(len(intersection) / len(union), 3) if union else 0.0


def find_similar_experiments(existing: list[QuantResearchExperiment], *, hypothesis: str, definition_id: str, timeframe: str) -> list[QuantResearchExperimentSimilarity]:
    """The one real entry point — checked before filing a new experiment
    (the directive's own "check before creating a new experiment whether
    an equivalent one exists"). Returns every real match found, most
    recent first; an empty list is itself a real, honest result (no
    equivalent experiment on file), never fabricated as "clear"."""
    matches: list[QuantResearchExperimentSimilarity] = []
    for experiment in reversed(existing):
        same_definition = experiment.record.definition_id == definition_id and experiment.record.timeframe == timeframe
        overlap = word_overlap_score(hypothesis, experiment.hypothesis)
        if same_definition:
            matches.append(
                QuantResearchExperimentSimilarity(
                    experimentId=experiment.id,
                    hypothesis=experiment.hypothesis,
                    overlapScore=overlap,
                    reason=f"Same compiled strategy ({definition_id}) and timeframe ({timeframe}) already tested in experiment {experiment.id}.",
                    outcome=experiment.outcome,
                    outcomeReason=experiment.outcome_reason,
                )
            )
        elif overlap >= HYPOTHESIS_OVERLAP_THRESHOLD:
            matches.append(
                QuantResearchExperimentSimilarity(
                    experimentId=experiment.id,
                    hypothesis=experiment.hypothesis,
                    overlapScore=overlap,
                    reason=f"Hypothesis wording overlaps {overlap * 100:.0f}% (word-level, not semantic) with already-filed experiment {experiment.id}.",
                    outcome=experiment.outcome,
                    outcomeReason=experiment.outcome_reason,
                )
            )
    return matches


# CEO directive "TradeTown — Research Engine Hardening +
# Self-Improvement Implementation Pass," Phase 3 — a real, disclosed
# "how similar counts as basically the same idea" bar, distinct from
# (and higher than) HYPOTHESIS_OVERLAP_THRESHOLD above. One reasonable
# convention, not derived from any statistical study.
NEAR_DUPLICATE_OVERLAP_THRESHOLD = 0.85


def classify_research_relationship(
    similar_experiments: list[QuantResearchExperimentSimilarity],
    similar_failed_strategies: list[SimilarFailedStrategyMatch],
) -> ResearchRelationship:
    """CEO directive "TradeTown — Research Engine Hardening +
    Self-Improvement Implementation Pass," Phase 3 — "classify the
    relationship: NOVEL / SIMILAR_SUCCESS / SIMILAR_FAILURE /
    NEAR_DUPLICATE / CONTRADICTORY_EVIDENCE." A real, disclosed
    combination of the two real similarity searches this codebase now
    runs before every new Quant Research Lab filing
    (find_similar_experiments() above, and
    app/failure_taxonomy.py::find_similar_failed_strategies()) — never
    a third search, never a fabricated relationship. Purely
    informational: the caller (app/state.py::submit_quant_research_
    experiment()) always files the new experiment regardless of what
    this returns — "do NOT automatically reject a strategy merely
    because something similar failed" is the directive's own explicit
    instruction."""
    max_overlap = max(
        (m.overlap_score for m in similar_experiments),
        default=0.0,
    )
    max_overlap = max(max_overlap, max((m.overlap_score for m in similar_failed_strategies), default=0.0))
    if max_overlap >= NEAR_DUPLICATE_OVERLAP_THRESHOLD:
        return "near_duplicate"

    has_failure_evidence = len(similar_failed_strategies) > 0 or any(m.outcome == "rejected" for m in similar_experiments)
    has_success_evidence = any(m.outcome == "promising" for m in similar_experiments)

    if has_failure_evidence and has_success_evidence:
        return "contradictory_evidence"
    if has_failure_evidence:
        return "similar_failure"
    if has_success_evidence:
        return "similar_success"
    return "novel"
