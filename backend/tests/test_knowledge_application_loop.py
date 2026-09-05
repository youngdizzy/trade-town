"""Covers CEO directive "TradeTown — Knowledge Application Loop 1.0" —
closing the previously write-only KNOWLEDGE_APPLIED half of the
knowledge-sharing lifecycle: real retrieval (app/institutional_memory.py's
canonical retrieve_relevant_memory(), now routed through by
app/devils_advocate.py instead of a crude title match), real, id-linked
application (app/knowledge_sharing.py's
record_knowledge_application_from_challenge()), real outcome grading
against real subsequent evidence (grade_knowledge_applications()), and
the one new InstitutionalMemoryStatus transition this evidence finally
justifies (apply_contradiction_evidence(), gated by
lessons_needing_contradiction_flag()'s conservative, disclosed
threshold). Every fixture is built through real production functions
(promote_case_study(), generate_challenge_report()) wherever practical,
never a hand-built shortcut that could silently test a different rule
than the one actually shipped.
"""
from __future__ import annotations

import json

from app.collaboration_intelligence import build_collaboration_case_summary
from app.devils_advocate import generate_challenge_report
from app.institutional_memory import apply_contradiction_evidence, promote_case_study, promote_risk_event, retrieve_relevant_memory
from app.knowledge_sharing import grade_knowledge_applications, lessons_needing_contradiction_flag
from app.market_data import MockMarketDataProvider
from app.nexus import tick as nexus_tick
from app.schemas import (
    AnalystVote,
    CaseStudy,
    ChallengeReport,
    ConfidenceFactor,
    DecisionConfidence,
    ExecutiveMeetingLogEntry,
    DepartmentOpinion,
    InstitutionalMemoryEntry,
    KnowledgeEvent,
    PaperTradeJournalEntry,
    RiskWarning,
    TimeState,
    TradeDecision,
    TradeProposal,
)
from app.state import default_state

_CREATED_AT = "2026-01-01T00:00:00+00:00"


def _case_study(*, case_id: str = "case-1", title: str = "Broke below support too early", symbol: str = "NEXA", pnl: float = -5.0) -> CaseStudy:
    return CaseStudy(
        id=case_id,
        category="acted_too_quickly",  # type: ignore[arg-type]
        title=title,
        symbol=symbol,
        decisionId="decision-src",
        timeline=[],
        background="test background",
        decisionProcess="test process",
        departmentOpinions=[],
        missedInformation="test missed info",
        lessonsLearned="Wait for confirmation before acting on a single signal.",
        recommendedImprovements="test improvement",
        relatedPrinciples=[],
        tradePnlPct=pnl,
        simDay=1,
        createdAt=_CREATED_AT,
    )


def _proposal(symbol: str = "NEXA", *, proposal_id: str = "proposal-1") -> TradeProposal:
    vote = AnalystVote(role="technical", agentId="echo", choice="buy", reasoning="test", evidence=["real evidence"])
    return TradeProposal(
        id=proposal_id,
        symbol=symbol,
        category="stock",
        quantity=10.0,
        price=100.0,
        confidence=80.0,
        analystVotes=[vote],
        overallRecommendation="buy",
        researchSummary="test research summary",
        riskSummary=f"{symbol} is within all configured risk limits.",
        confidenceEngine=DecisionConfidence(score=80.0, tier="strong", summary="test", factors=[ConfidenceFactor(name="agreement", score=80.0, weight=1.0, detail="test")]),
        createdAt=_CREATED_AT,
        createdSimMinutes=0,
    )


def _decision(*, decision_id: str, outcome: str) -> TradeDecision:
    return TradeDecision(
        id=decision_id,
        symbol="NEXA",
        outcome=outcome,  # type: ignore[arg-type]
        votes=[],
        researchSummary="x",
        technicalSummary="x",
        fundamentalSummary="x",
        riskSummary="x",
        supportingAgents=[],
        opposingAgents=[],
        confidence=60.0,
        finalReasoning="x",
        createdAt=_CREATED_AT,
    )


def _journal_entry(*, proposal_id: str, pnl: float) -> PaperTradeJournalEntry:
    return PaperTradeJournalEntry(
        id=f"journal-{proposal_id}",
        createdAt=_CREATED_AT,
        tradeId=f"trade-{proposal_id}",
        decisionId=f"decision-{proposal_id}",
        proposalId=proposal_id,
        symbol="NEXA",
        side="buy",
        quantity=2.0,
        entryPrice=100.0,
        exitPrice=100.0 + pnl,
        pnl=pnl,
        pnlPct=pnl,
        maePct=-1.0,
        mfePct=abs(pnl) + 1.0,
        durationMinutes=30,
        openedAt=_CREATED_AT,
        closedAt=_CREATED_AT,
    )


def _pending_applied_event(*, lesson_id: str, context_ref: str, event_id: str = "ke-applied-1") -> KnowledgeEvent:
    return KnowledgeEvent(
        id=event_id,
        type="knowledge_applied",
        lessonId=lesson_id,
        agentId="coach",
        simDay=1,
        detail="test application",
        createdAt=_CREATED_AT,
        contextRef=context_ref,
        applicationStatus="pending",
    )


class TestRetrieveRelevantMemorySymbolFilter:
    def test_symbol_filter_excludes_a_different_symbols_entry(self) -> None:
        memory = [promote_case_study(_case_study(symbol="NEXA"))]
        assert retrieve_relevant_memory(memory, current_sim_day=10, symbol="OTHR") is None

    def test_symbol_filter_returns_the_matching_entry(self) -> None:
        entry = promote_case_study(_case_study(symbol="NEXA"))
        result = retrieve_relevant_memory([entry], current_sim_day=1, symbol="NEXA")
        assert result is not None
        assert result.id == entry.id

    def test_a_symbol_agnostic_entry_is_excluded_from_a_symbol_scoped_query(self) -> None:
        warning = RiskWarning(id="risk-agnostic", symbol="NEXA", severity="critical", message="test", createdAt=_CREATED_AT)  # type: ignore[arg-type]
        entry = promote_risk_event(warning, sim_day=1).model_copy(update={"symbol": None})
        assert retrieve_relevant_memory([entry], current_sim_day=1, symbol="NEXA") is None

    def test_omitting_symbol_reproduces_prior_unfiltered_behavior(self) -> None:
        entry = promote_case_study(_case_study(symbol="NEXA"))
        assert retrieve_relevant_memory([entry], current_sim_day=1) is not None


class TestGenerateChallengeReportRetrieval:
    def test_no_institutional_memory_yields_no_retrieval(self) -> None:
        report = generate_challenge_report(_proposal(), provider=MockMarketDataProvider(), case_studies=[], existing_count=0)
        assert report.retrieved_memory_id is None

    def test_a_real_matching_memory_is_retrieved_and_linked(self) -> None:
        entry = promote_case_study(_case_study(symbol="NEXA"))
        report = generate_challenge_report(
            _proposal(symbol="NEXA"), provider=MockMarketDataProvider(), case_studies=[], existing_count=0,
            institutional_memory=[entry], current_sim_day=1,
        )
        assert report.retrieved_memory_id == entry.id

    def test_retrieval_works_for_a_non_case_study_source_too(self) -> None:
        """The real capability upgrade over the old CaseStudy-title-only
        mechanism: ANY real memory source type can now be retrieved and
        cited, not just behavioral_mistake/success from a CaseStudy."""
        warning = RiskWarning(id="risk-1", symbol="NEXA", severity="critical", message="Portfolio concentration exceeds the configured limit.", createdAt=_CREATED_AT)  # type: ignore[arg-type]
        entry = promote_risk_event(warning, sim_day=1)
        report = generate_challenge_report(
            _proposal(symbol="NEXA"), provider=MockMarketDataProvider(), case_studies=[], existing_count=0,
            institutional_memory=[entry], current_sim_day=1,
        )
        assert report.retrieved_memory_id == entry.id

    def test_a_different_symbols_memory_is_not_retrieved(self) -> None:
        entry = promote_case_study(_case_study(symbol="OTHR"))
        report = generate_challenge_report(
            _proposal(symbol="NEXA"), provider=MockMarketDataProvider(), case_studies=[], existing_count=0,
            institutional_memory=[entry], current_sim_day=10,
        )
        assert report.retrieved_memory_id is None

    def test_historical_comparisons_field_is_unaffected_by_retrieval(self) -> None:
        """Part XVI's own preservation rule: historical_comparisons keeps
        its exact prior real-CaseStudy-title-list behavior, unchanged."""
        case_study = _case_study(symbol="NEXA", title="NEXA mistake")
        entry = promote_case_study(case_study)
        report = generate_challenge_report(
            _proposal(symbol="NEXA"), provider=MockMarketDataProvider(), case_studies=[case_study], existing_count=0,
            institutional_memory=[entry], current_sim_day=1,
        )
        assert report.historical_comparisons == ["NEXA mistake"]
        assert report.retrieved_memory_id == entry.id


class TestGradeKnowledgeApplications:
    def test_no_matching_decision_yet_stays_pending(self) -> None:
        event = _pending_applied_event(lesson_id="im-1", context_ref="proposal-1")
        graded = grade_knowledge_applications(
            [event], institutional_memory=[], decisions=[], paper_trade_journal=[]
        )
        assert graded[0].application_status == "pending"
        assert graded[0].outcome is None

    def test_a_no_trade_decision_is_graded_inconclusive(self) -> None:
        event = _pending_applied_event(lesson_id="im-1", context_ref="proposal-1")
        decision = _decision(decision_id="decision-proposal-1", outcome="no_trade")
        graded = grade_knowledge_applications(
            [event], institutional_memory=[], decisions=[decision], paper_trade_journal=[]
        )
        assert graded[0].application_status == "evaluated"
        assert graded[0].outcome == "inconclusive"
        assert graded[0].outcome_ref == decision.id

    def test_a_placed_trade_with_no_closed_journal_entry_stays_pending(self) -> None:
        event = _pending_applied_event(lesson_id="im-1", context_ref="proposal-1")
        decision = _decision(decision_id="decision-proposal-1", outcome="trade")
        graded = grade_knowledge_applications(
            [event], institutional_memory=[], decisions=[decision], paper_trade_journal=[]
        )
        assert graded[0].application_status == "pending"

    def test_behavioral_mistake_supported_by_a_real_losing_trade(self) -> None:
        memory = promote_case_study(_case_study(case_id="case-1"))
        assert memory.source == "behavioral_mistake"
        event = _pending_applied_event(lesson_id=memory.id, context_ref="proposal-1")
        decision = _decision(decision_id="decision-proposal-1", outcome="trade")
        journal = _journal_entry(proposal_id="proposal-1", pnl=-3.0)
        graded = grade_knowledge_applications(
            [event], institutional_memory=[memory], decisions=[decision], paper_trade_journal=[journal]
        )
        assert graded[0].outcome == "supported"
        assert graded[0].outcome_ref == journal.id

    def test_behavioral_mistake_contradicted_by_a_real_winning_trade(self) -> None:
        memory = promote_case_study(_case_study(case_id="case-1"))
        event = _pending_applied_event(lesson_id=memory.id, context_ref="proposal-1")
        decision = _decision(decision_id="decision-proposal-1", outcome="trade")
        journal = _journal_entry(proposal_id="proposal-1", pnl=4.0)
        graded = grade_knowledge_applications(
            [event], institutional_memory=[memory], decisions=[decision], paper_trade_journal=[journal]
        )
        assert graded[0].outcome == "contradicted"

    def test_behavioral_success_supported_by_a_real_winning_trade(self) -> None:
        winning_case = _case_study(case_id="case-2").model_copy(update={"category": "disciplined_process"})
        memory = promote_case_study(winning_case)
        assert memory.source == "behavioral_success"
        event = _pending_applied_event(lesson_id=memory.id, context_ref="proposal-1")
        decision = _decision(decision_id="decision-proposal-1", outcome="trade")
        journal = _journal_entry(proposal_id="proposal-1", pnl=5.0)
        graded = grade_knowledge_applications(
            [event], institutional_memory=[memory], decisions=[decision], paper_trade_journal=[journal]
        )
        assert graded[0].outcome == "supported"

    def test_behavioral_success_contradicted_by_a_real_losing_trade(self) -> None:
        winning_case = _case_study(case_id="case-2").model_copy(update={"category": "disciplined_process"})
        memory = promote_case_study(winning_case)
        event = _pending_applied_event(lesson_id=memory.id, context_ref="proposal-1")
        decision = _decision(decision_id="decision-proposal-1", outcome="trade")
        journal = _journal_entry(proposal_id="proposal-1", pnl=-2.0)
        graded = grade_knowledge_applications(
            [event], institutional_memory=[memory], decisions=[decision], paper_trade_journal=[journal]
        )
        assert graded[0].outcome == "contradicted"

    def test_breakeven_trade_is_inconclusive_never_forced(self) -> None:
        memory = promote_case_study(_case_study(case_id="case-1"))
        event = _pending_applied_event(lesson_id=memory.id, context_ref="proposal-1")
        decision = _decision(decision_id="decision-proposal-1", outcome="trade")
        journal = _journal_entry(proposal_id="proposal-1", pnl=0.0)
        graded = grade_knowledge_applications(
            [event], institutional_memory=[memory], decisions=[decision], paper_trade_journal=[journal]
        )
        assert graded[0].outcome == "inconclusive"

    def test_a_non_behavioral_source_has_no_valence_rule_and_stays_inconclusive(self) -> None:
        warning = RiskWarning(id="risk-1", symbol="NEXA", severity="critical", message="test", createdAt=_CREATED_AT)  # type: ignore[arg-type]
        memory = promote_risk_event(warning, sim_day=1)
        event = _pending_applied_event(lesson_id=memory.id, context_ref="proposal-1")
        decision = _decision(decision_id="decision-proposal-1", outcome="trade")
        journal = _journal_entry(proposal_id="proposal-1", pnl=5.0)
        graded = grade_knowledge_applications(
            [event], institutional_memory=[memory], decisions=[decision], paper_trade_journal=[journal]
        )
        assert graded[0].outcome == "inconclusive"

    def test_already_evaluated_events_are_left_untouched(self) -> None:
        memory = promote_case_study(_case_study(case_id="case-1"))
        event = _pending_applied_event(lesson_id=memory.id, context_ref="proposal-1")
        decision = _decision(decision_id="decision-proposal-1", outcome="trade")
        journal = _journal_entry(proposal_id="proposal-1", pnl=-3.0)
        once = grade_knowledge_applications([event], institutional_memory=[memory], decisions=[decision], paper_trade_journal=[journal])
        twice = grade_knowledge_applications(once, institutional_memory=[memory], decisions=[decision], paper_trade_journal=[journal])
        assert once == twice

    def test_non_application_events_are_never_graded(self) -> None:
        event = KnowledgeEvent(id="ke-1", type="lesson_created", lessonId="im-1", agentId=None, simDay=1, detail="x", createdAt=_CREATED_AT)
        graded = grade_knowledge_applications([event], institutional_memory=[], decisions=[], paper_trade_journal=[])
        assert graded[0].application_status is None
        assert graded[0].outcome is None


class TestLessonsNeedingContradictionFlag:
    def _graded(self, lesson_id: str, outcome: str, event_id: str) -> KnowledgeEvent:
        return _pending_applied_event(lesson_id=lesson_id, context_ref="p", event_id=event_id).model_copy(
            update={"application_status": "evaluated", "outcome": outcome, "outcomeRef": "x", "evaluatedAt": _CREATED_AT}
        )

    def test_a_single_contradiction_never_flags(self) -> None:
        events = [self._graded("im-1", "contradicted", "ke-1")]
        assert lessons_needing_contradiction_flag(events) == set()

    def test_two_contradictions_with_no_supports_flags(self) -> None:
        events = [self._graded("im-1", "contradicted", "ke-1"), self._graded("im-1", "contradicted", "ke-2")]
        assert lessons_needing_contradiction_flag(events) == {"im-1"}

    def test_equal_supports_and_contradictions_never_flags(self) -> None:
        events = [
            self._graded("im-1", "contradicted", "ke-1"),
            self._graded("im-1", "contradicted", "ke-2"),
            self._graded("im-1", "supported", "ke-3"),
            self._graded("im-1", "supported", "ke-4"),
        ]
        assert lessons_needing_contradiction_flag(events) == set()

    def test_net_negative_evidence_flags(self) -> None:
        events = [
            self._graded("im-1", "contradicted", "ke-1"),
            self._graded("im-1", "contradicted", "ke-2"),
            self._graded("im-1", "contradicted", "ke-3"),
            self._graded("im-1", "supported", "ke-4"),
        ]
        assert lessons_needing_contradiction_flag(events) == {"im-1"}

    def test_inconclusive_outcomes_never_count_either_way(self) -> None:
        events = [self._graded("im-1", "inconclusive", "ke-1"), self._graded("im-1", "inconclusive", "ke-2")]
        assert lessons_needing_contradiction_flag(events) == set()


class TestApplyContradictionEvidence:
    def test_flips_an_active_entry(self) -> None:
        entry = promote_case_study(_case_study())
        updated = apply_contradiction_evidence([entry], memory_id=entry.id)
        assert updated[0].status == "contradicted"

    def test_never_deletes_or_rewrites_observation_text(self) -> None:
        entry = promote_case_study(_case_study())
        updated = apply_contradiction_evidence([entry], memory_id=entry.id)
        assert updated[0].observation == entry.observation
        assert updated[0].lesson == entry.lesson
        assert len(updated) == 1

    def test_a_missing_id_is_a_no_op(self) -> None:
        entry = promote_case_study(_case_study())
        updated = apply_contradiction_evidence([entry], memory_id="does-not-exist")
        assert updated == [entry]

    def test_an_already_superseded_entry_is_never_re_flagged(self) -> None:
        entry = promote_case_study(_case_study()).model_copy(update={"status": "superseded"})
        updated = apply_contradiction_evidence([entry], memory_id=entry.id)
        assert updated[0].status == "superseded"

    def test_once_contradicted_retrieval_no_longer_surfaces_it(self) -> None:
        entry = promote_case_study(_case_study(symbol="NEXA"))
        updated = apply_contradiction_evidence([entry], memory_id=entry.id)
        assert retrieve_relevant_memory(updated, current_sim_day=10, symbol="NEXA") is None


class TestCollaborationLinkage:
    def _meeting_log_entry(self, *, proposal_id: str = "proposal-1") -> ExecutiveMeetingLogEntry:
        opinion = DepartmentOpinion(
            role="research", departmentLabel="Research", agentId="scout", stance="agree", summary="x", confidencePct=80.0, evidence=["x"], concerns=[], benefits=["x"]  # type: ignore[arg-type]
        )
        return ExecutiveMeetingLogEntry(
            id=f"meeting-{proposal_id}", proposalId=proposal_id, symbol="NEXA", simDay=1, opinions=[opinion],
            recommendedAction="trade_normally", recommendationReason="x", ceoDecision="buy", networkAgreed=True,  # type: ignore[arg-type]
            decisionGrade="B", decisionGradeScore=75.0, resolvedBy="ceo", createdAt=_CREATED_AT,  # type: ignore[arg-type]
        )

    def test_true_when_the_challenge_report_retrieved_real_memory(self) -> None:
        report = generate_challenge_report(
            _proposal(symbol="NEXA"), provider=MockMarketDataProvider(), case_studies=[], existing_count=0,
            institutional_memory=[promote_case_study(_case_study(symbol="NEXA"))], current_sim_day=1,
        )
        summary = build_collaboration_case_summary(self._meeting_log_entry(), report)
        assert summary.knowledge_applied is True

    def test_false_when_nothing_was_retrieved(self) -> None:
        report = generate_challenge_report(_proposal(symbol="NEXA"), provider=MockMarketDataProvider(), case_studies=[], existing_count=0)
        summary = build_collaboration_case_summary(self._meeting_log_entry(), report)
        assert summary.knowledge_applied is False

    def test_false_when_there_is_no_challenge_report_at_all(self) -> None:
        summary = build_collaboration_case_summary(self._meeting_log_entry(), None)
        assert summary.knowledge_applied is False


class TestPersistenceRoundTrip:
    def test_knowledge_event_application_fields_survive_json_round_trip(self) -> None:
        event = _pending_applied_event(lesson_id="im-1", context_ref="proposal-1").model_copy(
            update={"application_status": "evaluated", "outcome": "supported", "outcome_ref": "journal-1", "evaluated_at": _CREATED_AT}
        )
        restored = KnowledgeEvent.model_validate_json(event.model_dump_json(by_alias=True))
        assert restored == event

    def test_an_old_knowledge_event_payload_with_no_application_fields_loads_with_honest_defaults(self) -> None:
        old_payload = {
            "id": "ke-old-1", "type": "lesson_created", "lessonId": "im-1", "agentId": None,
            "simDay": 1, "detail": "x", "createdAt": _CREATED_AT,
        }
        restored = KnowledgeEvent.model_validate(old_payload)
        assert restored.context_ref is None
        assert restored.application_status is None
        assert restored.outcome is None
        assert restored.outcome_ref is None
        assert restored.evaluated_at is None

    def test_an_old_challenge_report_payload_with_no_retrieved_memory_id_loads_honestly(self) -> None:
        old_payload = json.loads(
            _challenge_report_json_without_retrieval()
        )
        restored = ChallengeReport.model_validate(old_payload)
        assert restored.retrieved_memory_id is None

    def test_an_old_institutional_memory_entry_with_no_symbol_loads_honestly(self) -> None:
        entry = promote_case_study(_case_study(symbol="NEXA"))
        payload = entry.model_dump(by_alias=True)
        del payload["symbol"]
        restored = InstitutionalMemoryEntry.model_validate(payload)
        assert restored.symbol is None


def _challenge_report_json_without_retrieval() -> str:
    return json.dumps(
        {
            "id": "challenge-old-1", "proposalId": "proposal-1", "symbol": "NEXA", "assignedAgent": "coach",
            "tradeSummary": "x", "bullCase": "x", "bearCase": "x", "hiddenRisks": [], "weakAssumptions": [],
            "missingEvidence": [], "historicalComparisons": [], "worstCaseScenario": "x", "suggestedImprovements": [],
            "severity": "minor", "finalRecommendation": "x", "citedArticleIds": [], "createdAt": _CREATED_AT,
        }
    )


class TestNexusTickWiring:
    def test_grading_runs_inside_a_real_tick_and_updates_institutional_memory_status(self) -> None:
        """End-to-end through the real, unmodified nexus.tick() wiring:
        a pre-existing pending knowledge_applied event, a resolved
        no_trade decision, and enough repeated contradicting evidence
        already on record must, in one real tick, both grade the new
        event AND (via lessons_needing_contradiction_flag()) flip the
        targeted memory to "contradicted" if warranted."""
        memory = promote_case_study(_case_study(case_id="case-1", symbol="NEXA"))
        already_contradicted_once = _pending_applied_event(lesson_id=memory.id, context_ref="proposal-old", event_id="ke-old").model_copy(
            update={"application_status": "evaluated", "outcome": "contradicted", "outcomeRef": "journal-old", "evaluatedAt": _CREATED_AT}
        )
        pending_event = _pending_applied_event(lesson_id=memory.id, context_ref="proposal-new", event_id="ke-new")
        decision = _decision(decision_id="decision-proposal-new", outcome="trade")
        journal = _journal_entry(proposal_id="proposal-new", pnl=6.0)  # contradicts a behavioral_mistake memory

        state = default_state().model_copy(
            update={
                "institutional_memory": [memory],
                "knowledge_events": [already_contradicted_once, pending_event],
                "decisions": [decision],
                "paper_trade_journal": [journal],
            }
        )
        result = nexus_tick(state, TimeState(day=2, hour=0, minute=0), 5)

        new_event = next(e for e in result.knowledge_events if e.id == "ke-new")
        assert new_event.application_status == "evaluated"
        assert new_event.outcome == "contradicted"

        updated_memory = next(m for m in result.institutional_memory if m.id == memory.id)
        assert updated_memory.status == "contradicted"

    def test_no_pending_applications_is_a_safe_no_op(self) -> None:
        state = default_state()
        result = nexus_tick(state, TimeState(day=2, hour=0, minute=0), 5)
        assert isinstance(result.knowledge_events, list)
