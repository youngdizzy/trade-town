"""Covers app/lineage.py — CEO directive "TradeTown — Phase 10: Real
Data + True Holdout + Portfolio Intelligence," Section H."""
from __future__ import annotations

from app.lineage import check_lineage_integrity
from app.schemas import FactoryCandidateRecord


def _candidate(*, candidate_id: str, parent_id: str | None, generation: int) -> FactoryCandidateRecord:
    return FactoryCandidateRecord.model_construct(id=candidate_id, parent_candidate_id=parent_id, generation=generation)


class TestCheckLineageIntegrity:
    def test_clean_chain_has_no_issues(self) -> None:
        candidates = [
            _candidate(candidate_id="c0", parent_id=None, generation=0),
            _candidate(candidate_id="c1", parent_id="c0", generation=1),
            _candidate(candidate_id="c2", parent_id="c1", generation=2),
        ]
        assert check_lineage_integrity(candidates) == []

    def test_missing_parent_is_flagged(self) -> None:
        candidates = [_candidate(candidate_id="c1", parent_id="c0-missing", generation=1)]
        issues = check_lineage_integrity(candidates)
        assert len(issues) == 1
        assert issues[0].candidate_id == "c1"
        assert "not found" in issues[0].issue

    def test_generation_gap_is_flagged(self) -> None:
        candidates = [
            _candidate(candidate_id="c0", parent_id=None, generation=0),
            _candidate(candidate_id="c2", parent_id="c0", generation=2),  # should be generation 1
        ]
        issues = check_lineage_integrity(candidates)
        assert len(issues) == 1
        assert issues[0].candidate_id == "c2"

    def test_siblings_sharing_a_parent_are_valid(self) -> None:
        candidates = [
            _candidate(candidate_id="c0", parent_id=None, generation=0),
            _candidate(candidate_id="c1a", parent_id="c0", generation=1),
            _candidate(candidate_id="c1b", parent_id="c0", generation=1),
        ]
        assert check_lineage_integrity(candidates) == []

    def test_empty_list_has_no_issues(self) -> None:
        assert check_lineage_integrity([]) == []

    def test_root_with_no_parent_never_flagged(self) -> None:
        candidates = [_candidate(candidate_id="c0", parent_id=None, generation=0)]
        assert check_lineage_integrity(candidates) == []
