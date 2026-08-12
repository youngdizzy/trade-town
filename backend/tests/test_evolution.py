"""Covers app/evolution.py — Design Bible Chapter 74 Part 2, the
Institutional Evolution Engine. The Company Evolution Score must be a
disclosed, unweighted mean of five real, period-scoped factors — never
a re-read of CompanyHealth/CompanyScore.
"""
from __future__ import annotations

from app.evolution import (
    KNOWLEDGE_GROWTH_CAP,
    LEARNING_VOLUME_CAP,
    STRATEGY_MATURATION_CAP,
    compute_company_evolution_score,
    generate_institutional_evolution_report,
    record_evolution_report,
)
from app.schemas import (
    CaseStudy,
    CoachReport,
    ConstitutionAmendment,
    ExecutiveReview,
    FailedStrategyArchiveEntry,
    FoundationalMentorProgress,
    InstitutionalEvolutionReport,
    SelfImprovementProposal,
    StrategicReview,
    StrategyHallOfFameEntry,
)


def _case_study(cs_id: str, sim_day: int, pnl_pct: float = -2.0) -> CaseStudy:
    return CaseStudy(
        id=cs_id,
        category="overconfidence",  # type: ignore[arg-type]
        title=f"Case {cs_id}",
        symbol="AAPL",
        decisionId=f"decision-{cs_id}",
        background="test",
        decisionProcess="test",
        missedInformation="test",
        lessonsLearned="test",
        recommendedImprovements="test",
        tradePnlPct=pnl_pct,
        simDay=sim_day,
        createdAt="2026-01-01T00:00:00+00:00",
    )


def _proposal(p_id: str, sim_day: int, status: str = "pending") -> SelfImprovementProposal:
    return SelfImprovementProposal(
        id=p_id,
        category="risk_rule",  # type: ignore[arg-type]
        title="test",
        reasoning="test",
        evidence=[],
        benefits=[],
        risks=[],
        estimatedComplexity="small",  # type: ignore[arg-type]
        priority="low",  # type: ignore[arg-type]
        confidence=50.0,
        status=status,  # type: ignore[arg-type]
        simDay=sim_day,
        createdAt="2026-01-01T00:00:00+00:00",
    )


def _hof_entry(entry_id: str, sim_day: int) -> StrategyHallOfFameEntry:
    return StrategyHallOfFameEntry(
        id=entry_id,
        strategyId=f"strategy-{entry_id}",
        strategyName="Test Strategy",
        createdBy="quant",  # type: ignore[arg-type]
        description="test",
        simDaysActive=30,
        tradesExecuted=40,
        winRate=60.0,
        profitFactor=1.8,
        maxDrawdownPct=5.0,
        historicalReturnPct=12.0,
        retiredReason="test",
        simDay=sim_day,
        inductedAt="2026-01-01T00:00:00+00:00",
    )


def _failed_archive_entry(entry_id: str, sim_day: int) -> FailedStrategyArchiveEntry:
    return FailedStrategyArchiveEntry(
        id=entry_id,
        strategyId=f"strategy-{entry_id}",
        strategyName="Test Strategy",
        createdBy="quant",  # type: ignore[arg-type]
        failedAtStage="paper_trading",  # type: ignore[arg-type]
        whatFailed=["test"],
        lessonsLearned=["test"],
        retiredReason="test",
        simDay=sim_day,
        createdAt="2026-01-01T00:00:00+00:00",
    )


def _amendment(a_id: str, sim_day: int, ceo_decision: str = "approved") -> ConstitutionAmendment:
    return ConstitutionAmendment(
        id=a_id,
        proposedTitle="test",
        proposedText="test",
        status="approved",  # type: ignore[arg-type]
        ceoDecision=ceo_decision,  # type: ignore[arg-type]
        simDay=sim_day,
        createdAt="2026-01-01T00:00:00+00:00",
    )


class TestComputeCompanyEvolutionScore:
    def test_all_zero_with_no_activity(self) -> None:
        score = compute_company_evolution_score(
            window="monthly",
            current_sim_day=30,
            case_studies=[],
            self_improvement_proposals=[],
            mentor_progress={},
            strategy_hall_of_fame=[],
            strategy_failed_archive=[],
            constitution_amendments=[],
        )
        assert score.overall == 0.0
        assert score.learning_volume == 0.0
        assert score.proposal_execution == 0.0
        assert score.knowledge_growth == 0.0
        assert score.strategy_maturation == 0.0
        assert score.governance_evolution == 0.0

    def test_learning_volume_is_capped_at_100(self) -> None:
        case_studies = [_case_study(f"cs{i}", sim_day=10) for i in range(int(LEARNING_VOLUME_CAP) * 3)]
        score = compute_company_evolution_score(
            window="monthly",
            current_sim_day=30,
            case_studies=case_studies,
            self_improvement_proposals=[],
            mentor_progress={},
            strategy_hall_of_fame=[],
            strategy_failed_archive=[],
            constitution_amendments=[],
        )
        assert score.learning_volume == 100.0

    def test_case_studies_outside_the_window_are_excluded(self) -> None:
        case_studies = [_case_study("old", sim_day=1)]
        score = compute_company_evolution_score(
            window="monthly",
            current_sim_day=100,
            case_studies=case_studies,
            self_improvement_proposals=[],
            mentor_progress={},
            strategy_hall_of_fame=[],
            strategy_failed_archive=[],
            constitution_amendments=[],
        )
        assert score.learning_volume == 0.0

    def test_proposal_execution_rate(self) -> None:
        proposals = [
            _proposal("p1", sim_day=10, status="approved"),
            _proposal("p2", sim_day=10, status="implemented"),
            _proposal("p3", sim_day=10, status="rejected"),
            _proposal("p4", sim_day=10, status="pending"),
        ]
        score = compute_company_evolution_score(
            window="monthly",
            current_sim_day=30,
            case_studies=[],
            self_improvement_proposals=proposals,
            mentor_progress={},
            strategy_hall_of_fame=[],
            strategy_failed_archive=[],
            constitution_amendments=[],
        )
        assert score.proposal_execution == 50.0

    def test_knowledge_growth_counts_real_graduations_in_period(self) -> None:
        mentor_progress = {
            "quant": {
                "tjr": FoundationalMentorProgress(mentorId="tjr", graduationStatus="graduated", graduatedSimDay=15),  # type: ignore[arg-type]
            }
        }
        score = compute_company_evolution_score(
            window="monthly",
            current_sim_day=30,
            case_studies=[],
            self_improvement_proposals=[],
            mentor_progress=mentor_progress,
            strategy_hall_of_fame=[],
            strategy_failed_archive=[],
            constitution_amendments=[],
        )
        assert score.knowledge_growth == round(min(100.0, 1 / KNOWLEDGE_GROWTH_CAP * 100.0), 1)

    def test_strategy_maturation_is_hall_of_fame_minus_failed_archive_floored_at_zero(self) -> None:
        score = compute_company_evolution_score(
            window="monthly",
            current_sim_day=30,
            case_studies=[],
            self_improvement_proposals=[],
            mentor_progress={},
            strategy_hall_of_fame=[],
            strategy_failed_archive=[_failed_archive_entry(f"fa{i}", sim_day=10) for i in range(5)],
            constitution_amendments=[],
        )
        assert score.strategy_maturation == 0.0

    def test_strategy_maturation_rewards_net_positive_hall_of_fame(self) -> None:
        score = compute_company_evolution_score(
            window="monthly",
            current_sim_day=30,
            case_studies=[],
            self_improvement_proposals=[],
            mentor_progress={},
            strategy_hall_of_fame=[_hof_entry(f"h{i}", sim_day=10) for i in range(STRATEGY_MATURATION_CAP)],
            strategy_failed_archive=[],
            constitution_amendments=[],
        )
        assert score.strategy_maturation == 100.0

    def test_governance_evolution_is_binary_on_a_ratified_amendment(self) -> None:
        score = compute_company_evolution_score(
            window="monthly",
            current_sim_day=30,
            case_studies=[],
            self_improvement_proposals=[],
            mentor_progress={},
            strategy_hall_of_fame=[],
            strategy_failed_archive=[],
            constitution_amendments=[_amendment("a1", sim_day=10)],
        )
        assert score.governance_evolution == 100.0

    def test_pending_amendment_does_not_count_as_governance_evolution(self) -> None:
        score = compute_company_evolution_score(
            window="monthly",
            current_sim_day=30,
            case_studies=[],
            self_improvement_proposals=[],
            mentor_progress={},
            strategy_hall_of_fame=[],
            strategy_failed_archive=[],
            constitution_amendments=[_amendment("a1", sim_day=10, ceo_decision="pending")],
        )
        assert score.governance_evolution == 0.0

    def test_overall_is_the_plain_mean_of_the_five_factors(self) -> None:
        score = compute_company_evolution_score(
            window="monthly",
            current_sim_day=30,
            case_studies=[_case_study(f"cs{i}", sim_day=10) for i in range(int(LEARNING_VOLUME_CAP))],
            self_improvement_proposals=[],
            mentor_progress={},
            strategy_hall_of_fame=[],
            strategy_failed_archive=[],
            constitution_amendments=[_amendment("a1", sim_day=10)],
        )
        expected = round((100.0 + 0.0 + 0.0 + 0.0 + 100.0) / 5, 1)
        assert score.overall == expected

    def test_different_windows_use_different_lookback(self) -> None:
        case_studies = [_case_study("old", sim_day=50)]
        monthly = compute_company_evolution_score(
            window="monthly",
            current_sim_day=100,
            case_studies=case_studies,
            self_improvement_proposals=[],
            mentor_progress={},
            strategy_hall_of_fame=[],
            strategy_failed_archive=[],
            constitution_amendments=[],
        )
        yearly = compute_company_evolution_score(
            window="yearly",
            current_sim_day=100,
            case_studies=case_studies,
            self_improvement_proposals=[],
            mentor_progress={},
            strategy_hall_of_fame=[],
            strategy_failed_archive=[],
            constitution_amendments=[],
        )
        assert monthly.learning_volume == 0.0
        assert yearly.learning_volume > 0.0


class TestGenerateInstitutionalEvolutionReport:
    def test_composes_real_report_ids_and_top_studies(self) -> None:
        strategic_review = StrategicReview(
            id="sr1",
            createdAt="2026-01-01T00:00:00+00:00",
            activeGoalCount=2,
            completedSinceLastReview=[],
            expiredSinceLastReview=[],
            milestonesReachedSinceLastReview=0,
            summary="test",
        )
        executive_review = ExecutiveReview(
            id="er1",
            companyScore=80.0,
            companyScoreChange=2.0,
            companyHealthTier="stable",  # type: ignore[arg-type]
            departmentActivity=[],
            researchCompleted=5,
            knowledgeGained=3,
            lessonsCompleted=2,
            conflictsDetected=0,
            summary="test",
            createdAt="2026-01-01T00:00:00+00:00",
        )
        coach_report = CoachReport(
            id="cr1",
            period="monthly",  # type: ignore[arg-type]
            companyScore=80.0,
            agentRankings=[],
            researchAccuracy=70.0,
            winRate=60.0,
            lossRate=40.0,
            averageConfidence=70.0,
            riskScore=50.0,
            createdAt="2026-01-01T00:00:00+00:00",
        )
        case_studies = [_case_study("loss1", sim_day=10, pnl_pct=-5.0), _case_study("loss2", sim_day=10, pnl_pct=-1.0)]
        proposals = [_proposal("p1", sim_day=10, status="approved")]
        score = compute_company_evolution_score(
            window="monthly",
            current_sim_day=30,
            case_studies=case_studies,
            self_improvement_proposals=proposals,
            mentor_progress={},
            strategy_hall_of_fame=[],
            strategy_failed_archive=[],
            constitution_amendments=[],
        )

        report = generate_institutional_evolution_report(
            report_id="evo1",
            sim_day=30,
            strategic_reviews=[strategic_review],
            executive_reviews=[executive_review],
            coach_reports=[coach_report],
            case_studies=case_studies,
            self_improvement_proposals=proposals,
            evolution_score=score,
        )
        assert report.strategic_review_id == "sr1"
        assert report.executive_review_id == "er1"
        assert report.coach_report_id == "cr1"
        assert set(report.top_case_study_ids) == {"loss1", "loss2"}
        assert report.proposals_generated == ["p1"]
        assert report.proposals_resolved == ["p1"]

    def test_no_prior_reports_leaves_ids_none(self) -> None:
        score = compute_company_evolution_score(
            window="monthly",
            current_sim_day=30,
            case_studies=[],
            self_improvement_proposals=[],
            mentor_progress={},
            strategy_hall_of_fame=[],
            strategy_failed_archive=[],
            constitution_amendments=[],
        )
        report = generate_institutional_evolution_report(
            report_id="evo1",
            sim_day=30,
            strategic_reviews=[],
            executive_reviews=[],
            coach_reports=[],
            case_studies=[],
            self_improvement_proposals=[],
            evolution_score=score,
        )
        assert report.strategic_review_id is None
        assert report.executive_review_id is None
        assert report.coach_report_id is None


class TestRecordEvolutionReport:
    def test_appends_and_caps(self) -> None:
        reports: list[InstitutionalEvolutionReport] = []
        score = compute_company_evolution_score(
            window="monthly",
            current_sim_day=30,
            case_studies=[],
            self_improvement_proposals=[],
            mentor_progress={},
            strategy_hall_of_fame=[],
            strategy_failed_archive=[],
            constitution_amendments=[],
        )
        for i in range(25):
            report = generate_institutional_evolution_report(
                report_id=f"evo{i}",
                sim_day=30,
                strategic_reviews=[],
                executive_reviews=[],
                coach_reports=[],
                case_studies=[],
                self_improvement_proposals=[],
                evolution_score=score,
            )
            reports = record_evolution_report(reports, report)
        assert len(reports) == 20
        assert reports[-1].id == "evo24"
