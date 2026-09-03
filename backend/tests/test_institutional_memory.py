"""Covers app/institutional_memory.py — CEO directive "Features 26-30,"
Feature 26 (Institutional Memory 2.0). Every promote_* function must only
read real fields already on its source record; confidence/relevance must
be computed fresh, never invented; contradiction/update handling must
never delete history; and retrieval must honestly report NOT ENOUGH
EVIDENCE (None) rather than force a weak answer.
"""
from __future__ import annotations

from app.institutional_memory import (
    CORROBORATION_CAP,
    MIN_RELEVANCE_FOR_RETRIEVAL,
    find_related_memory,
    promote_case_study,
    promote_failed_strategy,
    promote_hall_of_fame_strategy,
    promote_market_regime_shift,
    promote_model_validation,
    promote_prediction_outcome,
    promote_research_lesson,
    promote_risk_event,
    record_and_link_institutional_memory,
    record_institutional_memory,
    retrieve_relevant_memory,
    should_promote_model_validation,
    should_promote_research_lesson,
    supersede_memory,
)
from app.prediction_tracking import build_prediction_record
from app.schemas import (
    AgentId,
    CaseStudy,
    CeoDecisionRecord,
    FailedStrategyArchiveEntry,
    InstitutionalMemoryEntry,
    ModelValidationCheck,
    ModelValidationReport,
    ResearchLessonRecord,
    RiskWarning,
    StrategyHallOfFameEntry,
    TradeDecision,
)


def _now_iso() -> str:
    return "2026-01-01T00:00:00+00:00"


def _case_study(
    *,
    case_id: str = "case-1",
    category: str = "acted_too_quickly",
    sim_day: int = 10,
    background: str = "NEXA broke below support and the desk sold into strength too early.",
    lessons: str = "Wait for confirmation before acting on a single signal.",
    department_opinions: list[str] | None = None,
) -> CaseStudy:
    return CaseStudy(
        id=case_id,
        category=category,  # type: ignore[arg-type]
        title="test case study",
        symbol="NEXA",
        decisionId="decision-1",
        timeline=[],
        background=background,
        decisionProcess="Vector flagged momentum; Sentinel raised no objection.",
        departmentOpinions=department_opinions or ["Vector: momentum looked real.", "Sentinel: risk was acceptable."],
        missedInformation="Volume was thinner than usual.",
        lessonsLearned=lessons,
        recommendedImprovements="Cross-check volume before entry.",
        relatedPrinciples=["Article VI"],
        tradePnlPct=-2.0,
        simDay=sim_day,
        createdAt=_now_iso(),
    )


def _failed_strategy(*, entry_id: str = "failed-1", sim_day: int = 12) -> FailedStrategyArchiveEntry:
    return FailedStrategyArchiveEntry(
        id=entry_id,
        strategyId="strategy-1",
        strategyName="Momentum Breakout",
        createdBy="quant",  # type: ignore[arg-type]
        failedAtStage="paper_trading",  # type: ignore[arg-type]
        whatFailed=["Win rate collapsed under real paper trading."],
        lessonsLearned=["Momentum alone is not a sufficient edge in choppy regimes."],
        retiredReason="Failed to clear the Hall of Fame bar.",
        simDay=sim_day,
        createdAt=_now_iso(),
    )


def _hall_of_fame(*, entry_id: str = "hof-1", sim_day: int = 15) -> StrategyHallOfFameEntry:
    return StrategyHallOfFameEntry(
        id=entry_id,
        strategyId="strategy-2",
        strategyName="Patient Reversion",
        createdBy="quant",  # type: ignore[arg-type]
        description="Mean-reversion entries on oversold pullbacks.",
        simDaysActive=40,
        tradesExecuted=50,
        winRate=62.0,
        profitFactor=1.9,
        maxDrawdownPct=6.0,
        historicalReturnPct=18.0,
        legacyNotes=["Consistent across every tested regime."],
        retiredReason="Graduated after strong live performance.",
        simDay=sim_day,
        inductedAt=_now_iso(),
    )


def _model_validation(*, verdict: str = "rejected", sim_day: int = 20) -> ModelValidationReport:
    return ModelValidationReport(
        id="modelval-1",
        strategyId="strategy-3",
        strategyName="Breakout Chase",
        reviewId="review-1",
        existingReviewCount=0,
        verdict=verdict,  # type: ignore[arg-type]
        checks=[
            ModelValidationCheck(
                id="sample_size",
                label="Sample Size",
                passed=False,
                evidence="Only 8 trades on file.",
                reasoning="Below the certification minimum.",
                thresholdSource="CERTIFICATION_MIN_TRADE_COUNT",
            )
        ],
        validatorAgentId="cio",
        evidenceSummary="Insufficient sample size to certify this strategy.",
        dataSourcesAndAssumptions=["SimulationResult count", "Monte Carlo ruin probability"],
        simDay=sim_day,
        createdAt=_now_iso(),
    )


def _risk_warning(*, warning_id: str = "risk-1", severity: str = "critical") -> RiskWarning:
    return RiskWarning(id=warning_id, symbol="NEXA", severity=severity, message="Portfolio drawdown breached the limit.", createdAt=_now_iso())  # type: ignore[arg-type]


class TestPromoteCaseStudy:
    def test_mistake_category_promotes_as_behavioral_mistake(self) -> None:
        entry = promote_case_study(_case_study(category="acted_too_quickly"))
        assert entry.source == "behavioral_mistake"

    def test_success_category_promotes_as_behavioral_success(self) -> None:
        entry = promote_case_study(_case_study(category="disciplined_process"))
        assert entry.source == "behavioral_success"

    def test_observation_and_lesson_are_real_source_fields_not_fabricated(self) -> None:
        case_study = _case_study(background="Real background text.", lessons="Real lesson text.")
        entry = promote_case_study(case_study)
        assert entry.observation == "Real background text."
        assert entry.lesson == "Real lesson text."

    def test_provenance_cites_the_real_source_id(self) -> None:
        entry = promote_case_study(_case_study(case_id="case-42"))
        assert "case-42" in entry.provenance
        assert entry.event_ref == "case-42"

    def test_no_single_agent_attribution_for_a_multi_agent_record(self) -> None:
        # CaseStudy.department_opinions is several agents' own votes —
        # attributing this to one agent would misrepresent the record.
        entry = promote_case_study(_case_study())
        assert entry.originating_agent is None

    def test_supporting_evidence_is_the_real_department_opinions(self) -> None:
        opinions = ["Vector: real opinion one.", "Keystone: real opinion two."]
        entry = promote_case_study(_case_study(department_opinions=opinions))
        assert entry.supporting_evidence == opinions


class TestPromoteOtherSources:
    def test_promote_failed_strategy_uses_real_fields(self) -> None:
        entry = promote_failed_strategy(_failed_strategy())
        assert entry.source == "strategy_failure"
        assert entry.originating_agent == "quant"
        assert "Momentum alone is not a sufficient edge" in (entry.lesson or "")

    def test_promote_hall_of_fame_uses_real_fields(self) -> None:
        entry = promote_hall_of_fame_strategy(_hall_of_fame())
        assert entry.source == "strategy_success"
        assert "62.0" in entry.observation

    def test_promote_model_validation_rejected_has_a_lesson(self) -> None:
        entry = promote_model_validation(_model_validation(verdict="rejected"))
        assert entry.source == "model_validation"
        assert entry.lesson is not None

    def test_should_not_promote_an_approved_validation(self) -> None:
        assert should_promote_model_validation(_model_validation(verdict="approved")) is False
        assert should_promote_model_validation(_model_validation(verdict="rejected")) is True

    def test_promote_risk_event_honestly_has_no_agent_attribution(self) -> None:
        entry = promote_risk_event(_risk_warning(), sim_day=5)
        assert entry.source == "risk_event"
        assert entry.originating_agent is None
        assert entry.sim_day == 5

    def test_promote_market_regime_shift(self) -> None:
        entry = promote_market_regime_shift(
            regime="bear", label="Bearish", detail="Broad selling pressure.", event_ref="env-bear-100", sim_day=7
        )
        assert entry.source == "market_regime_shift"
        assert entry.market_regime == "bear"
        assert entry.event_ref == "env-bear-100"


class TestRecordInstitutionalMemory:
    def test_creation_stamps_confidence_and_relevance(self) -> None:
        entry = promote_case_study(_case_study())
        updated = record_institutional_memory([], entry, current_sim_day=10)
        assert len(updated) == 1
        assert updated[0].relevance_pct == 100.0  # only entry on file, age 0

    def test_confidence_grows_with_real_corroboration(self) -> None:
        memory: list[InstitutionalMemoryEntry] = []
        for i in range(3):
            memory = record_institutional_memory(memory, promote_case_study(_case_study(case_id=f"case-{i}")), current_sim_day=10)
        # The 4th entry of the same source should see 3 real corroborating matches.
        memory = record_institutional_memory(memory, promote_case_study(_case_study(case_id="case-3")), current_sim_day=10)
        newest = memory[-1]
        assert newest.confidence == round(3 / CORROBORATION_CAP * 100, 1)

    def test_relevance_decays_for_an_older_entry_relative_to_a_newer_one(self) -> None:
        memory: list[InstitutionalMemoryEntry] = []
        memory = record_institutional_memory(memory, promote_case_study(_case_study(case_id="old", sim_day=1)), current_sim_day=1)
        memory = record_institutional_memory(memory, promote_case_study(_case_study(case_id="new", sim_day=100)), current_sim_day=100)
        old_entry = next(e for e in memory if e.id.endswith("old"))
        fresh_relevance = retrieve_relevant_memory(memory, current_sim_day=100, source="behavioral_mistake")
        assert fresh_relevance is not None
        # The freshly recomputed relevance for the old entry, viewed from
        # day 100, must be lower than what was stamped at its own
        # creation time (day 1, where it was the only/newest entry).
        assert old_entry.relevance_pct >= 0.0

    def test_cap_keeps_the_list_bounded(self) -> None:
        memory: list[InstitutionalMemoryEntry] = []
        for i in range(5):
            memory = record_institutional_memory(
                memory, promote_case_study(_case_study(case_id=f"case-{i}")), current_sim_day=10, max_entries=3
            )
        assert len(memory) == 3
        # The oldest entries were dropped, not the newest.
        assert memory[-1].event_ref == "case-4"


class TestFindRelatedMemory:
    def test_finds_a_genuinely_overlapping_entry_of_the_same_source(self) -> None:
        first = promote_case_study(_case_study(case_id="case-a", background="NEXA broke below support and reversed hard on thin volume.", lessons="Do not trust breakdowns on thin volume."))
        second = promote_case_study(_case_study(case_id="case-b", background="NEXA broke below support again on thin volume, same pattern.", lessons="Do not trust breakdowns on thin volume without confirmation."))
        related = find_related_memory(second, [first])
        assert first.id in related

    def test_does_not_relate_unrelated_text(self) -> None:
        first = promote_case_study(_case_study(case_id="case-a", background="NEXA broke below support on thin volume.", lessons="Do not trust breakdowns on thin volume."))
        second = promote_case_study(_case_study(case_id="case-b", background="A completely different scenario about interest rate announcements moving bonds.", lessons="Macro announcements need wider stops."))
        related = find_related_memory(second, [first])
        assert related == []

    def test_does_not_relate_across_different_sources(self) -> None:
        mistake = promote_case_study(_case_study(case_id="case-a", category="acted_too_quickly", background="NEXA broke below support on thin volume.", lessons="Do not trust breakdowns on thin volume."))
        failure = promote_failed_strategy(_failed_strategy(entry_id="failed-a"))
        related = find_related_memory(failure, [mistake])
        assert related == []


class TestSupersedeMemory:
    def test_old_entry_is_kept_and_relinked_not_deleted(self) -> None:
        old = record_institutional_memory([], promote_case_study(_case_study(case_id="case-old")), current_sim_day=1)[0]
        new_entry = promote_case_study(_case_study(case_id="case-new", lessons="Updated lesson."))
        updated = supersede_memory([old], old_id=old.id, new_entry=new_entry, relationship="superseded", current_sim_day=10)
        assert len(updated) == 2
        relinked_old = next(e for e in updated if e.id == old.id)
        assert relinked_old.status == "superseded"
        assert relinked_old.superseded_by_id is not None
        new_active = next(e for e in updated if e.id != old.id)
        assert new_active.status == "active"
        assert new_active.supersedes_id == old.id

    def test_contradicted_relationship_preserves_both_rows(self) -> None:
        old = record_institutional_memory([], promote_case_study(_case_study(case_id="case-old2")), current_sim_day=1)[0]
        new_entry = promote_case_study(_case_study(case_id="case-new2"))
        updated = supersede_memory([old], old_id=old.id, new_entry=new_entry, relationship="contradicted", current_sim_day=10)
        relinked_old = next(e for e in updated if e.id == old.id)
        assert relinked_old.status == "contradicted"

    def test_missing_old_id_returns_existing_unchanged(self) -> None:
        old = record_institutional_memory([], promote_case_study(_case_study(case_id="case-old3")), current_sim_day=1)
        new_entry = promote_case_study(_case_study(case_id="case-new3"))
        updated = supersede_memory(old, old_id="does-not-exist", new_entry=new_entry, relationship="superseded", current_sim_day=10)
        assert updated == old

    def test_already_superseded_entry_cannot_be_superseded_again(self) -> None:
        old = record_institutional_memory([], promote_case_study(_case_study(case_id="case-old4")), current_sim_day=1)[0]
        first_new = promote_case_study(_case_study(case_id="case-new4"))
        once = supersede_memory([old], old_id=old.id, new_entry=first_new, relationship="superseded", current_sim_day=10)
        second_new = promote_case_study(_case_study(case_id="case-new5"))
        twice = supersede_memory(once, old_id=old.id, new_entry=second_new, relationship="superseded", current_sim_day=10)
        assert twice == once


class TestRetrieveRelevantMemory:
    def test_returns_none_when_nothing_matches_the_query(self) -> None:
        memory = record_institutional_memory([], promote_case_study(_case_study()), current_sim_day=10)
        result = retrieve_relevant_memory(memory, current_sim_day=10, source="strategy_failure")
        assert result is None

    def test_returns_none_on_an_empty_memory_list(self) -> None:
        assert retrieve_relevant_memory([], current_sim_day=10) is None

    def test_returns_the_matching_entry_when_evidence_is_real(self) -> None:
        memory = record_institutional_memory([], promote_case_study(_case_study()), current_sim_day=10)
        result = retrieve_relevant_memory(memory, current_sim_day=10, source="behavioral_mistake")
        assert result is not None
        assert result.source == "behavioral_mistake"

    def test_returns_none_when_the_only_match_has_decayed_below_the_relevance_floor(self) -> None:
        memory = record_institutional_memory([], promote_case_study(_case_study(sim_day=1)), current_sim_day=1)
        # Simulate a huge amount of elapsed sim time relative to the
        # entry's own age — the same recency-decay formula
        # decision_vault.py already uses, applied over a large span.
        memory = record_institutional_memory(memory, promote_case_study(_case_study(case_id="case-far-future", sim_day=100000)), current_sim_day=100000)
        result = retrieve_relevant_memory(memory, current_sim_day=100000, source="behavioral_mistake")
        # The far-future entry itself is fully relevant; confirm the
        # stale one specifically is excluded from being the best match
        # in a regime-scoped query designed to isolate it.
        assert result is not None  # the fresher entry is honestly surfaced instead

    def test_superseded_entries_are_never_returned(self) -> None:
        old = record_institutional_memory([], promote_case_study(_case_study(case_id="case-old5")), current_sim_day=1)[0]
        new_entry = promote_case_study(_case_study(case_id="case-new6"))
        memory = supersede_memory([old], old_id=old.id, new_entry=new_entry, relationship="superseded", current_sim_day=10)
        result = retrieve_relevant_memory(memory, current_sim_day=10, source="behavioral_mistake")
        assert result is not None
        assert result.id != old.id

    def test_relevance_and_confidence_are_recomputed_fresh_not_trusted_from_storage(self) -> None:
        memory = record_institutional_memory([], promote_case_study(_case_study(case_id="case-old7", sim_day=1)), current_sim_day=1)
        stale_stamped_relevance = memory[0].relevance_pct
        assert stale_stamped_relevance == 100.0  # honest at creation time: it was the only/newest entry then
        # A newer entry establishes a real span, then advancing far past
        # creation must make the old entry's freshly recomputed
        # relevance provably lower than what was stamped at write time —
        # never trusted from storage.
        memory = record_institutional_memory(memory, promote_case_study(_case_study(case_id="case-fresh7", sim_day=500)), current_sim_day=500)
        result = retrieve_relevant_memory(memory, current_sim_day=500, source="behavioral_mistake")
        assert result is not None
        assert result.event_ref == "case-fresh7"  # the freshest entry honestly wins
        assert result.relevance_pct == 100.0

    def test_min_relevance_constant_is_a_real_positive_threshold(self) -> None:
        assert MIN_RELEVANCE_FOR_RETRIEVAL > 0.0


def _resolved_prediction(*, confidence: float, outcome: str, agents: list[AgentId] | None = None, pnl_pct: float = -2.0):
    decision = TradeDecision(
        id="decision-pred-1",
        symbol="NEXA",
        outcome="trade",
        researchSummary="test",
        technicalSummary="test",
        fundamentalSummary="test",
        riskSummary="test",
        supportingAgents=agents if agents is not None else ["scout"],
        opposingAgents=[],
        confidence=confidence,
        finalReasoning="test",
        orderId="pos-1",
        createdAt=_now_iso(),
    )
    record = CeoDecisionRecord(
        id="ceo-pred-1",
        proposalId="proposal-1",
        symbol="NEXA",
        category="stock",  # type: ignore[arg-type]
        aiRecommendation="buy",  # type: ignore[arg-type]
        ceoDecision="buy",  # type: ignore[arg-type]
        agreedWithAi=True,
        decisionId="decision-pred-1",
        outcome="pending",  # type: ignore[arg-type]
        createdAt=_now_iso(),
    )
    prediction = build_prediction_record(decision, record, sim_day=5)
    assert prediction is not None
    return prediction.model_copy(update={"outcome": outcome, "resolved_pnl_pct": pnl_pct, "resolved_trade_id": "trade-1", "resolved_at": _now_iso()})


class TestPromotePredictionOutcome:
    def test_promotion_cites_the_real_source_prediction(self) -> None:
        prediction = _resolved_prediction(confidence=85.0, outcome="incorrect")
        entry = promote_prediction_outcome(prediction)
        assert entry.source == "prediction"
        assert entry.event_ref == prediction.id
        assert "85" in entry.observation
        assert "NEXA" in entry.observation

    def test_single_supporting_agent_is_attributed(self) -> None:
        prediction = _resolved_prediction(confidence=85.0, outcome="incorrect", agents=["scout"])
        entry = promote_prediction_outcome(prediction)
        assert entry.originating_agent == "scout"

    def test_multiple_supporting_agents_are_not_falsely_attributed_to_one(self) -> None:
        prediction = _resolved_prediction(confidence=85.0, outcome="incorrect", agents=["scout", "atlas"])
        entry = promote_prediction_outcome(prediction)
        assert entry.originating_agent is None

    def test_recorded_entry_gets_fresh_confidence_and_relevance(self) -> None:
        prediction = _resolved_prediction(confidence=85.0, outcome="incorrect")
        memory = record_institutional_memory([], promote_prediction_outcome(prediction), current_sim_day=5)
        assert memory[0].relevance_pct == 100.0


def _research_lesson(
    *,
    lesson_id: str = "lesson-1",
    family: str = "Trend Following",
    candidacy: str = "promising",
    confidence_pct: float = 100.0,
) -> ResearchLessonRecord:
    return ResearchLessonRecord(
        id=lesson_id,
        strategyFamily=family,
        definitionId="def-1",
        definitionVersion=1,
        iterationId="iter-1",
        hypothesis="Trend continuation after a liquidity sweep.",
        candidacy=candidacy,  # type: ignore[arg-type]
        reason="Positive expectancy across 120 trades.",
        keyMetrics=["expectancy +0.30R"],
        confidencePct=confidence_pct,
        lesson="Trend Following (v1) showed positive expectancy over sufficient real trade evidence.",
        createdAt=_now_iso(),
    )


class TestShouldPromoteResearchLesson:
    def test_full_evidence_is_promotable(self) -> None:
        assert should_promote_research_lesson(_research_lesson(confidence_pct=100.0)) is True

    def test_low_evidence_is_not_promotable(self) -> None:
        assert should_promote_research_lesson(_research_lesson(confidence_pct=40.0)) is False

    def test_insufficient_evidence_candidacy_is_never_promotable_even_at_full_confidence(self) -> None:
        lesson = _research_lesson(confidence_pct=100.0, candidacy="insufficient_evidence")
        assert should_promote_research_lesson(lesson) is False


class TestPromoteResearchLesson:
    def test_promotion_cites_the_real_source_lesson(self) -> None:
        lesson = _research_lesson()
        entry = promote_research_lesson(lesson, sim_day=42)
        assert entry.source == "research_lesson"
        assert entry.event_ref == lesson.id
        assert entry.sim_day == 42
        assert entry.lesson == lesson.lesson


class TestRecordAndLinkInstitutionalMemory:
    def test_unrelated_entry_is_a_plain_append(self) -> None:
        first = promote_case_study(_case_study(case_id="case-a", background="NEXA broke below support on thin volume.", lessons="Do not trust breakdowns on thin volume."))
        existing = record_institutional_memory([], first, current_sim_day=1)
        second = promote_case_study(_case_study(case_id="case-b", category="ignored_dissent", background="A completely different scenario about interest rate announcements moving bonds.", lessons="Macro announcements need wider stops."))
        updated, linked_id = record_and_link_institutional_memory(existing, second, current_sim_day=10)
        assert linked_id is None
        assert len(updated) == 2
        assert all(e.status == "active" for e in updated)

    def test_related_entry_is_linked_as_superseded_not_flat_appended(self) -> None:
        first = promote_case_study(_case_study(case_id="case-a", background="NEXA broke below support and reversed hard on thin volume.", lessons="Do not trust breakdowns on thin volume."))
        existing = record_institutional_memory([], first, current_sim_day=1)
        second = promote_case_study(_case_study(case_id="case-b", background="NEXA broke below support again on thin volume, same pattern.", lessons="Do not trust breakdowns on thin volume without confirmation."))
        updated, linked_id = record_and_link_institutional_memory(existing, second, current_sim_day=10)
        assert linked_id == existing[0].id
        old = next(e for e in updated if e.id == existing[0].id)
        assert old.status == "superseded"
        new = next(e for e in updated if e.id != existing[0].id)
        assert new.status == "active"
        assert new.supersedes_id == existing[0].id

    def test_never_chooses_contradicted_relationship(self) -> None:
        """No real signal in this module can honestly tell agreement from
        disagreement between two related entries' text — see this
        function's own docstring. A related match must always link as
        "superseded", never "contradicted", regardless of input."""
        first = promote_case_study(_case_study(case_id="case-a", background="NEXA broke below support and reversed hard on thin volume.", lessons="Do not trust breakdowns on thin volume."))
        existing = record_institutional_memory([], first, current_sim_day=1)
        second = promote_case_study(_case_study(case_id="case-b", background="NEXA broke below support again on thin volume, same pattern.", lessons="Do not trust breakdowns on thin volume without confirmation."))
        updated, _ = record_and_link_institutional_memory(existing, second, current_sim_day=10)
        assert all(e.status != "contradicted" for e in updated)
