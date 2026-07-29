"""Covers app/innovation.py — v0.7 Feature 41, Innovation Points. A pure
function of the real ChallengeReport history; never incrementally
mutated state, so it can never drift from the reports it's derived from.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.innovation import TIER_THRESHOLDS, compute_innovation_state
from app.schemas import ChallengeReport


def _report(agent_id: str, severity: str, report_id: str = "r1") -> ChallengeReport:
    return ChallengeReport(
        id=report_id,
        proposalId="proposal-1",
        symbol="NEXA",
        assignedAgent=agent_id,  # type: ignore[arg-type]
        tradeSummary="test summary",
        bullCase="test bull case",
        bearCase="test bear case",
        hiddenRisks=[],
        weakAssumptions=[],
        missingEvidence=[],
        historicalComparisons=[],
        worstCaseScenario="test worst case",
        suggestedImprovements=[],
        severity=severity,  # type: ignore[arg-type]
        finalRecommendation="test recommendation",
        createdAt=datetime.now(timezone.utc).isoformat(),
    )


class TestComputeInnovationState:
    def test_no_reports_yields_empty_state(self) -> None:
        assert compute_innovation_state([]) == {}

    def test_none_found_still_awards_partial_points(self) -> None:
        state = compute_innovation_state([_report("sage", "none_found")])
        assert state["sage"].points > 0
        assert state["sage"].tier == 0
        assert state["sage"].tier_name == "research_contributor"

    def test_points_accumulate_per_agent_across_reports(self) -> None:
        reports = [_report("sage", "minor", "r1"), _report("sage", "minor", "r2")]
        state = compute_innovation_state(reports)
        single = compute_innovation_state([_report("sage", "minor", "r1")])
        assert state["sage"].points == single["sage"].points * 2

    def test_major_severity_awards_more_points_than_minor_or_none_found(self) -> None:
        major = compute_innovation_state([_report("sage", "major")])["sage"].points
        minor = compute_innovation_state([_report("sage", "minor")])["sage"].points
        none_found = compute_innovation_state([_report("sage", "none_found")])["sage"].points
        assert major > minor > none_found

    def test_different_agents_tracked_independently(self) -> None:
        state = compute_innovation_state([_report("sage", "major", "r1"), _report("coach", "minor", "r2")])
        assert set(state.keys()) == {"sage", "coach"}
        assert state["sage"].points != state["coach"].points

    def test_tier_advances_at_each_real_threshold(self) -> None:
        # MAJOR_POINTS is 3.0/report; TIER_THRESHOLDS = (3.0, 8.0, 18.0,
        # 35.0), so these report counts land just at/past each threshold.
        assert TIER_THRESHOLDS == (3.0, 8.0, 18.0, 35.0)
        counts_to_expected_tier = {1: 1, 3: 2, 6: 3, 12: 4}
        for report_count, expected_tier in counts_to_expected_tier.items():
            reports = [_report("sage", "major", f"r{i}") for i in range(report_count)]
            state = compute_innovation_state(reports)
            assert state["sage"].tier == expected_tier

    def test_tier_name_matches_tier_index(self) -> None:
        expected = ["research_contributor", "research_specialist", "innovation_leader", "chief_innovator", "legendary_innovator"]
        for report_count in (0, 1, 3, 6, 12):
            reports = [_report("sage", "major", f"r{i}") for i in range(report_count + 1)]
            state = compute_innovation_state(reports)
            assert state["sage"].tier_name == expected[state["sage"].tier]
