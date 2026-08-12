"""Covers app/self_improvement.py — Design Bible Chapter 74 Part 1, the
Continuous Learning & Self-Improvement System (CLSIS). Every proposal
must trace to real, citable evidence — never a fabricated trigger.
"""
from __future__ import annotations

from app.schemas import (
    AgentKnowledgeState,
    AgentScore,
    CaseStudy,
    CoachReport,
    FailedStrategyArchiveEntry,
    FoundationalMentorProgress,
    SelfImprovementProposal,
    ThinkingProfile,
    ThinkingTrait,
)
from app.self_improvement import (
    RECURRING_MISTAKE_THRESHOLD,
    RECURRING_MISTAKE_WINDOW,
    RETIREMENT_CLUSTER_THRESHOLD,
    compute_executive_learning_summary,
    decide_self_improvement_proposal,
    maybe_propose_recurring_mistake,
    maybe_propose_retirement_cluster,
    record_self_improvement_proposal,
)


def _case_study(cs_id: str, category: str = "overconfidence") -> CaseStudy:
    return CaseStudy(
        id=cs_id,
        category=category,  # type: ignore[arg-type]
        title="Test Case Study",
        symbol="AAPL",
        decisionId=f"decision-{cs_id}",
        background="test",
        decisionProcess="test",
        missedInformation="test",
        lessonsLearned="test",
        recommendedImprovements="test",
        tradePnlPct=-2.0,
        simDay=1,
        createdAt="2026-01-01T00:00:00+00:00",
    )


def _failed_archive_entry(entry_id: str) -> FailedStrategyArchiveEntry:
    return FailedStrategyArchiveEntry(
        id=entry_id,
        strategyId=f"strategy-{entry_id}",
        strategyName="Test Strategy",
        createdBy="quant",
        failedAtStage="paper_trading",  # type: ignore[arg-type]
        whatFailed=["test"],
        lessonsLearned=["test"],
        retiredReason="test",
        simDay=1,
        createdAt="2026-01-01T00:00:00+00:00",
    )


class TestMaybeProposeRecurringMistake:
    def test_no_proposal_below_threshold(self) -> None:
        case_studies = [_case_study(f"cs{i}") for i in range(RECURRING_MISTAKE_THRESHOLD - 1)]
        assert maybe_propose_recurring_mistake(case_studies, [], sim_day=10) is None

    def test_proposal_fires_at_threshold(self) -> None:
        case_studies = [_case_study(f"cs{i}") for i in range(RECURRING_MISTAKE_THRESHOLD)]
        proposal = maybe_propose_recurring_mistake(case_studies, [], sim_day=10)
        assert proposal is not None
        assert proposal.category == "risk_rule"
        assert proposal.evidence == [cs.id for cs in case_studies]
        assert proposal.sim_day == 10

    def test_success_categories_never_trigger_a_risk_rule_proposal(self) -> None:
        case_studies = [_case_study(f"cs{i}", category="disciplined_process") for i in range(5)]
        assert maybe_propose_recurring_mistake(case_studies, [], sim_day=10) is None

    def test_only_the_most_recent_window_is_considered(self) -> None:
        old = [_case_study(f"old{i}", category="overconfidence") for i in range(RECURRING_MISTAKE_THRESHOLD)]
        # Exactly WINDOW filler items of a different category — the
        # recent-window slice is then exactly this filler, fully
        # excluding the aged-out overconfidence cluster.
        filler = [_case_study(f"filler{i}", category="incomplete_research") for i in range(RECURRING_MISTAKE_WINDOW)]
        case_studies = old + filler
        proposal = maybe_propose_recurring_mistake(case_studies, [], sim_day=10)
        assert proposal is not None
        assert all(cs.id not in proposal.evidence for cs in old)
        assert "incomplete research" in proposal.title

    def test_already_cited_evidence_does_not_refire(self) -> None:
        case_studies = [_case_study(f"cs{i}") for i in range(RECURRING_MISTAKE_THRESHOLD)]
        first = maybe_propose_recurring_mistake(case_studies, [], sim_day=10)
        assert first is not None
        second = maybe_propose_recurring_mistake(case_studies, [first], sim_day=10)
        assert second is None

    def test_a_new_case_study_after_a_resolved_proposal_can_refire(self) -> None:
        case_studies = [_case_study(f"cs{i}") for i in range(RECURRING_MISTAKE_THRESHOLD)]
        first = maybe_propose_recurring_mistake(case_studies, [], sim_day=10)
        assert first is not None
        case_studies.append(_case_study("cs-new"))
        second = maybe_propose_recurring_mistake(case_studies, [first], sim_day=11)
        assert second is not None
        assert second.id != first.id


class TestMaybeProposeRetirementCluster:
    def test_no_proposal_below_threshold(self) -> None:
        entries = [_failed_archive_entry(f"fa{i}") for i in range(RETIREMENT_CLUSTER_THRESHOLD - 1)]
        assert maybe_propose_retirement_cluster(entries, [], sim_day=10) is None

    def test_proposal_fires_at_threshold(self) -> None:
        entries = [_failed_archive_entry(f"fa{i}") for i in range(RETIREMENT_CLUSTER_THRESHOLD)]
        proposal = maybe_propose_retirement_cluster(entries, [], sim_day=10)
        assert proposal is not None
        assert proposal.category == "research_workflow"
        assert proposal.evidence == [e.id for e in entries]

    def test_already_cited_evidence_does_not_refire(self) -> None:
        entries = [_failed_archive_entry(f"fa{i}") for i in range(RETIREMENT_CLUSTER_THRESHOLD)]
        first = maybe_propose_retirement_cluster(entries, [], sim_day=10)
        assert first is not None
        second = maybe_propose_retirement_cluster(entries, [first], sim_day=10)
        assert second is None


class TestRecordSelfImprovementProposal:
    def test_appends_and_caps(self) -> None:
        proposals: list[SelfImprovementProposal] = []
        for i in range(50):
            proposal = SelfImprovementProposal(
                id=f"p{i}",
                category="risk_rule",  # type: ignore[arg-type]
                title="test",
                reasoning="test",
                evidence=[],
                benefits=[],
                risks=[],
                estimatedComplexity="small",  # type: ignore[arg-type]
                priority="low",  # type: ignore[arg-type]
                confidence=50.0,
                simDay=1,
                createdAt="2026-01-01T00:00:00+00:00",
            )
            proposals = record_self_improvement_proposal(proposals, proposal)
        assert len(proposals) == 40
        assert proposals[-1].id == "p49"


class TestDecideSelfImprovementProposal:
    def _pending(self) -> SelfImprovementProposal:
        return SelfImprovementProposal(
            id="p1",
            category="risk_rule",  # type: ignore[arg-type]
            title="test",
            reasoning="test",
            evidence=[],
            benefits=[],
            risks=[],
            estimatedComplexity="small",  # type: ignore[arg-type]
            priority="low",  # type: ignore[arg-type]
            confidence=50.0,
            simDay=1,
            createdAt="2026-01-01T00:00:00+00:00",
        )

    def test_approve_sets_status_and_note(self) -> None:
        updated = decide_self_improvement_proposal([self._pending()], "p1", approve=True, ceo_note="good idea")
        assert updated[0].status == "approved"
        assert updated[0].ceo_note == "good idea"
        assert updated[0].decided_at is not None

    def test_reject_sets_status(self) -> None:
        updated = decide_self_improvement_proposal([self._pending()], "p1", approve=False, ceo_note=None)
        assert updated[0].status == "rejected"

    def test_unknown_id_is_a_noop(self) -> None:
        pending = self._pending()
        updated = decide_self_improvement_proposal([pending], "does-not-exist", approve=True, ceo_note=None)
        assert updated[0].status == "pending"


class TestComputeExecutiveLearningSummary:
    def test_composes_all_four_real_sources(self) -> None:
        coach_report = CoachReport(
            id="cr1",
            period="monthly",  # type: ignore[arg-type]
            companyScore=80.0,
            agentRankings=[AgentScore(agentId="quant", score=90.0, researchAccuracy=75.0, confidenceCalibration=60.0)],  # type: ignore[arg-type]
            researchAccuracy=75.0,
            winRate=60.0,
            lossRate=40.0,
            averageConfidence=70.0,
            riskScore=50.0,
            createdAt="2026-01-01T00:00:00+00:00",
        )
        thinking_profiles = {"quant": _thinking_profile("quant")}
        agent_knowledge = {"quant": AgentKnowledgeState(agentId="quant", branch="Quantitative Analysis", points=120.0, tier=2, level="intermediate")}  # type: ignore[arg-type]
        mentor_progress = {
            "tjr": FoundationalMentorProgress(mentorId="tjr", graduationStatus="graduated", graduatedSimDay=5)  # type: ignore[arg-type]
        }

        summary = compute_executive_learning_summary(
            "quant",
            coach_reports=[coach_report],
            thinking_profiles=thinking_profiles,
            agent_knowledge=agent_knowledge,
            mentor_progress=mentor_progress,
        )
        assert summary.research_accuracy == 75.0
        assert summary.confidence_calibration == 60.0
        assert summary.thinking_profile is not None
        assert summary.knowledge_points == 120.0
        assert summary.knowledge_tier == 2
        assert summary.mentor_tracks == ["tjr"]
        assert summary.graduated_track_count == 1

    def test_missing_agent_data_produces_honest_defaults(self) -> None:
        summary = compute_executive_learning_summary(
            "quant",
            coach_reports=[],
            thinking_profiles={},
            agent_knowledge={},
            mentor_progress={},
        )
        assert summary.research_accuracy is None
        assert summary.confidence_calibration is None
        assert summary.thinking_profile is None
        assert summary.knowledge_points == 0.0
        assert summary.mentor_tracks == []
        assert summary.graduated_track_count == 0


def _thinking_profile(agent_id: str) -> ThinkingProfile:
    return ThinkingProfile(
        agentId=agent_id,  # type: ignore[arg-type]
        traits=[ThinkingTrait(id="curiosity", name="Curiosity", score=70.0, detail="test")],  # type: ignore[arg-type]
        updatedAt="2026-01-01T00:00:00+00:00",
    )
