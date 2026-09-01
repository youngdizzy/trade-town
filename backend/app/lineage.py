"""app/lineage.py — CEO directive "TradeTown — Phase 10: Real Data +
True Holdout + Portfolio Intelligence," Section H (Lineage).

A real, structural check over an already-real `list[FactoryCandidateRecord]`
(app/research_factory.py already threads `parentCandidateId`/`lineageId`/
`generation` through every candidate — this module invents no new
lineage field, it only VERIFIES the existing ones are internally
consistent). `check_lineage_integrity()` flags — never silently ignores,
never invents a relationship that isn't there — two real, disclosed
failure modes: a `parentCandidateId` pointing at an id absent from the
same candidate list (a real lineage break), and a candidate whose
`generation` doesn't equal its own real parent's `generation + 1` (this
codebase's own real, established convention — see
`app/research_factory.py`'s own module docstring — every child is
exactly one generation ahead of its real parent, never invented as
"probably fine")."""
from __future__ import annotations

from app.schemas import FactoryCandidateRecord, LineageIntegrityIssue


def check_lineage_integrity(candidates: list[FactoryCandidateRecord]) -> list[LineageIntegrityIssue]:
    """Pure, real, structural check — computes no new evidence, reads
    only the already-real `id`/`parentCandidateId`/`generation` fields
    every `FactoryCandidateRecord` already carries. An empty result IS a
    real, honest "no break found," never assumed without checking."""
    by_id = {candidate.id: candidate for candidate in candidates}
    issues: list[LineageIntegrityIssue] = []
    for candidate in candidates:
        if candidate.parent_candidate_id is None:
            continue  # a real, valid root — generation 0 has no parent by definition.
        parent = by_id.get(candidate.parent_candidate_id)
        if parent is None:
            issues.append(
                LineageIntegrityIssue(
                    candidateId=candidate.id,
                    issue=f"parentCandidateId {candidate.parent_candidate_id!r} was not found among the {len(candidates)} real candidates checked — a genuine lineage break, never silently assumed to be fine.",
                )
            )
            continue
        if candidate.generation != parent.generation + 1:
            issues.append(
                LineageIntegrityIssue(
                    candidateId=candidate.id,
                    issue=f"generation {candidate.generation} does not equal its real parent {parent.id!r}'s own generation ({parent.generation}) + 1 — a real, structural inconsistency in this lineage.",
                )
            )
    return issues
