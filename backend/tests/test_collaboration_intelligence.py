"""Covers app/collaboration_intelligence.py — "TradeTown — Department
Debate & Collaboration Intelligence 1.0." Every real signal here reads
directly off already-real, already-permanent ExecutiveMeetingLogEntry/
ChallengeReport data — never a fabricated opinion, evidence bullet, or
disagreement. Confidence-number differences alone must never register
as disagreement; only real distinct ExecutiveStance values count.
"""
from __future__ import annotations

from app.collaboration_intelligence import (
    _evidence_overlap_pairs,
    average_collaboration_case_score,
    build_collaboration_case_summary,
    compute_collaboration_case_summaries,
)
from app.schemas import ChallengeReport, DepartmentOpinion, ExecutiveMeetingLogEntry


def _now_iso() -> str:
    return "2026-01-01T00:00:00+00:00"


def _opinion(
    *,
    role: str = "research",
    stance: str = "agree",
    confidence_pct: float = 80.0,
    evidence: list[str] | None = None,
) -> DepartmentOpinion:
    return DepartmentOpinion(
        role=role,  # type: ignore[arg-type]
        departmentLabel=role.title(),
        stance=stance,  # type: ignore[arg-type]
        summary="test summary",
        confidencePct=confidence_pct,
        evidence=evidence if evidence is not None else [],
        concerns=[],
        benefits=[],
    )


def _meeting_log_entry(
    *,
    proposal_id: str = "p1",
    opinions: list[DepartmentOpinion] | None = None,
    recommended_action: str = "trade_normally",
    ceo_decision: str = "buy",
    network_agreed: bool = True,
) -> ExecutiveMeetingLogEntry:
    return ExecutiveMeetingLogEntry(
        id=f"meeting-{proposal_id}",
        proposalId=proposal_id,
        symbol="NEXA",
        simDay=10,
        opinions=opinions if opinions is not None else [_opinion()],
        recommendedAction=recommended_action,  # type: ignore[arg-type]
        recommendationReason="test reason",
        ceoDecision=ceo_decision,  # type: ignore[arg-type]
        networkAgreed=network_agreed,
        decisionGrade="B",  # type: ignore[arg-type]
        decisionGradeScore=75.0,
        resolvedBy="ceo",  # type: ignore[arg-type]
        createdAt=_now_iso(),
    )


def _challenge_report(*, proposal_id: str = "p1", severity: str = "major") -> ChallengeReport:
    return ChallengeReport(
        id=f"challenge-{proposal_id}",
        proposalId=proposal_id,
        symbol="NEXA",
        assignedAgent="coach",  # type: ignore[arg-type]
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
        createdAt=_now_iso(),
    )


class TestEvidenceOverlapPairs:
    def test_real_shared_significant_words_across_departments_are_found(self) -> None:
        opinions = [
            _opinion(role="research", evidence=["liquidity expansion confirmed strongly"]),
            _opinion(role="quant", evidence=["liquidity expansion pattern historically confirmed"]),
        ]
        pairs = _evidence_overlap_pairs(opinions)
        assert ("research", "quant") in pairs

    def test_unrelated_evidence_is_not_falsely_linked(self) -> None:
        opinions = [
            _opinion(role="research", evidence=["liquidity expansion confirmed strongly"]),
            _opinion(role="risk", evidence=["earnings announcement scheduled tomorrow morning"]),
        ]
        assert _evidence_overlap_pairs(opinions) == []

    def test_same_role_is_never_paired_with_itself(self) -> None:
        # Two entries with the same role should never happen in real data
        # (one DepartmentOpinion per role), but the guard must hold anyway.
        opinions = [
            _opinion(role="research", evidence=["liquidity expansion confirmed strongly"]),
            _opinion(role="research", evidence=["liquidity expansion confirmed strongly"]),
        ]
        assert _evidence_overlap_pairs(opinions) == []

    def test_empty_evidence_contributes_no_pairs(self) -> None:
        opinions = [_opinion(role="research", evidence=[]), _opinion(role="quant", evidence=[])]
        assert _evidence_overlap_pairs(opinions) == []


class TestBuildCollaborationCaseSummary:
    def test_distinct_stance_count_reflects_real_stance_diversity_not_confidence(self) -> None:
        """Two departments with very different confidence_pct but the
        SAME real stance must never register as disagreement."""
        opinions = [
            _opinion(role="research", stance="agree", confidence_pct=95.0),
            _opinion(role="quant", stance="agree", confidence_pct=40.0),
        ]
        entry = _meeting_log_entry(opinions=opinions)
        summary = build_collaboration_case_summary(entry, None)
        assert summary.distinct_stance_count == 1

    def test_genuinely_different_stances_are_counted(self) -> None:
        opinions = [
            _opinion(role="research", stance="agree"),
            _opinion(role="risk", stance="recommend_position_change"),
            _opinion(role="devils_advocate", stance="recommend_rejecting"),
        ]
        entry = _meeting_log_entry(opinions=opinions)
        summary = build_collaboration_case_summary(entry, None)
        assert summary.distinct_stance_count == 3

    def test_no_challenge_report_reads_as_honest_none_not_heeded(self) -> None:
        entry = _meeting_log_entry()
        summary = build_collaboration_case_summary(entry, None)
        assert summary.challenge_severity is None
        assert summary.challenge_heeded is False

    def test_real_challenge_that_changed_the_recommendation_is_heeded(self) -> None:
        entry = _meeting_log_entry(recommended_action="reduce_risk")
        challenge = _challenge_report(severity="major")
        summary = build_collaboration_case_summary(entry, challenge)
        assert summary.challenge_severity == "major"
        assert summary.challenge_heeded is True

    def test_challenge_with_no_real_severity_is_never_heeded(self) -> None:
        entry = _meeting_log_entry(recommended_action="reduce_risk")
        challenge = _challenge_report(severity="none_found")
        summary = build_collaboration_case_summary(entry, challenge)
        assert summary.challenge_heeded is False

    def test_severe_challenge_that_did_not_change_the_recommendation_is_not_heeded(self) -> None:
        """A real severity flag alone isn't enough — the network's own
        synthesis must have actually departed from "trade_normally" for
        this to count as heeded, never inferred from severity alone."""
        entry = _meeting_log_entry(recommended_action="trade_normally")
        challenge = _challenge_report(severity="major")
        summary = build_collaboration_case_summary(entry, challenge)
        assert summary.challenge_heeded is False

    def test_empty_opinions_reads_as_an_honest_empty_case(self) -> None:
        entry = _meeting_log_entry(opinions=[])
        summary = build_collaboration_case_summary(entry, None)
        assert summary.department_count == 0
        assert summary.distinct_stance_count == 0
        assert "No department opinions" in summary.consensus_summary

    def test_consensus_summary_reuses_the_real_disagreement_narrative(self) -> None:
        opinions = [_opinion(role="research", stance="agree"), _opinion(role="risk", stance="recommend_position_change")]
        entry = _meeting_log_entry(opinions=opinions)
        summary = build_collaboration_case_summary(entry, None)
        assert "Risk" in summary.consensus_summary


class TestComputeCollaborationCaseSummaries:
    def test_joins_challenge_reports_by_proposal_id(self) -> None:
        entry = _meeting_log_entry(proposal_id="p1")
        other_entry = _meeting_log_entry(proposal_id="p2")
        challenge = _challenge_report(proposal_id="p1", severity="minor")
        summaries = compute_collaboration_case_summaries([entry, other_entry], [challenge])
        by_id = {s.proposal_id: s for s in summaries}
        assert by_id["p1"].challenge_severity == "minor"
        assert by_id["p2"].challenge_severity is None

    def test_empty_meeting_log_returns_empty_list(self) -> None:
        assert compute_collaboration_case_summaries([], []) == []


class TestAverageCollaborationCaseScore:
    def test_no_cases_returns_none_not_a_forced_answer(self) -> None:
        assert average_collaboration_case_score([]) is None

    def test_more_distinct_stances_raise_the_score(self) -> None:
        low = build_collaboration_case_summary(_meeting_log_entry(opinions=[_opinion(role="research", stance="agree"), _opinion(role="quant", stance="agree")]), None)
        high = build_collaboration_case_summary(
            _meeting_log_entry(
                opinions=[_opinion(role="research", stance="agree"), _opinion(role="risk", stance="recommend_position_change"), _opinion(role="devils_advocate", stance="recommend_rejecting")]
            ),
            None,
        )
        high_score = average_collaboration_case_score([high])
        low_score = average_collaboration_case_score([low])
        assert high_score is not None and low_score is not None
        assert high_score > low_score

    def test_real_evidence_reuse_raises_the_score(self) -> None:
        no_reuse = build_collaboration_case_summary(
            _meeting_log_entry(opinions=[_opinion(role="research", stance="agree", evidence=["alpha beta gamma"]), _opinion(role="quant", stance="agree", evidence=["delta epsilon zeta"])]), None
        )
        with_reuse = build_collaboration_case_summary(
            _meeting_log_entry(
                opinions=[_opinion(role="research", stance="agree", evidence=["liquidity expansion confirmed strongly"]), _opinion(role="quant", stance="agree", evidence=["liquidity expansion pattern historically confirmed"])]
            ),
            None,
        )
        with_reuse_score = average_collaboration_case_score([with_reuse])
        no_reuse_score = average_collaboration_case_score([no_reuse])
        assert with_reuse_score is not None and no_reuse_score is not None
        assert with_reuse_score > no_reuse_score

    def test_score_never_exceeds_100(self) -> None:
        opinions = [_opinion(role=r, stance=s, evidence=["liquidity expansion confirmed strongly historically"]) for r, s in [("research", "agree"), ("risk", "recommend_position_change"), ("quant", "recommend_waiting")]]
        summary = build_collaboration_case_summary(_meeting_log_entry(opinions=opinions), None)
        score = average_collaboration_case_score([summary])
        assert score is not None and score <= 100.0

    def test_empty_case_scores_zero_not_a_forced_high_default(self) -> None:
        summary = build_collaboration_case_summary(_meeting_log_entry(opinions=[]), None)
        assert average_collaboration_case_score([summary]) == 0.0
