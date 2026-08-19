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
"""
from __future__ import annotations

import re

from app.schemas import AgentId, QuantResearchExperiment, QuantResearchExperimentSimilarity, QuantResearchOutcome, ResearchExperimentRecord

HYPOTHESIS_OVERLAP_THRESHOLD = 0.6
# Matches the same bounded-growth convention every other permanent,
# never-deleted archive in this codebase uses (app/strategy_lab.py's
# MAX_STRATEGY_HALL_OF_FAME/MAX_STRATEGY_FAILED_ARCHIVE = 40,
# app/hall_of_fame.py's MAX_HALL_OF_FAME = 40) — old records fall off
# the FRONT of the list (oldest first), never the newest, which is
# still an honest "never deleted merely because it looks bad" for any
# realistically-sized research program.
MAX_QUANT_RESEARCH_EXPERIMENTS = 100


def cap_quant_research_experiments(items: list[QuantResearchExperiment]) -> list[QuantResearchExperiment]:
    if len(items) > MAX_QUANT_RESEARCH_EXPERIMENTS:
        del items[: len(items) - MAX_QUANT_RESEARCH_EXPERIMENTS]
    return items


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
) -> QuantResearchExperiment:
    """The one real entry point for turning an already-real, already-
    computed `ResearchExperimentRecord` into a persistable
    `QuantResearchExperiment` — wraps `_classify_outcome()` so callers
    (app/state.py) never need this module's private classification
    function directly."""
    outcome, outcome_reason = _classify_outcome(record)
    return QuantResearchExperiment(
        id=experiment_id,
        hypothesis=hypothesis,
        researcherAgentId=researcher_agent_id,
        outcome=outcome,
        outcomeReason=outcome_reason,
        record=record,
        createdAt=created_at,
    )


def _normalized_words(text: str) -> set[str]:
    return {w for w in re.sub(r"[^a-z0-9\s]", " ", text.lower()).split() if len(w) > 2}


def _word_overlap_score(a: str, b: str) -> float:
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
        overlap = _word_overlap_score(hypothesis, experiment.hypothesis)
        if same_definition:
            matches.append(
                QuantResearchExperimentSimilarity(
                    experimentId=experiment.id,
                    hypothesis=experiment.hypothesis,
                    overlapScore=overlap,
                    reason=f"Same compiled strategy ({definition_id}) and timeframe ({timeframe}) already tested in experiment {experiment.id}.",
                )
            )
        elif overlap >= HYPOTHESIS_OVERLAP_THRESHOLD:
            matches.append(
                QuantResearchExperimentSimilarity(
                    experimentId=experiment.id,
                    hypothesis=experiment.hypothesis,
                    overlapScore=overlap,
                    reason=f"Hypothesis wording overlaps {overlap * 100:.0f}% (word-level, not semantic) with already-filed experiment {experiment.id}.",
                )
            )
    return matches
