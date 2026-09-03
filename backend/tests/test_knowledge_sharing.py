"""Covers app/knowledge_sharing.py — "TradeTown — Learning Organization
1.0." Every real KnowledgeEvent must be attributable to a real source
record, idempotent (replaying the same trigger never double-records),
and honest about when there is nothing real to report (no lesson text,
no citation, no relevant role class).
"""
from __future__ import annotations

from app.institutional_memory import promote_case_study, promote_risk_event
from app.knowledge_sharing import (
    lesson_confirmed_event,
    lesson_created_event,
    record_knowledge_application_from_challenge,
    record_knowledge_event,
    share_lesson_with_relevant_agents,
)
from app.schemas import CaseStudy, ChallengeReport, KnowledgeEvent, RiskWarning


def _now_iso() -> str:
    return "2026-01-01T00:00:00+00:00"


def _case_study(*, case_id: str = "case-1", title: str = "Broke below support too early") -> CaseStudy:
    return CaseStudy(
        id=case_id,
        category="acted_too_quickly",  # type: ignore[arg-type]
        title=title,
        symbol="NEXA",
        decisionId="decision-1",
        timeline=[],
        background="NEXA broke below support and the desk sold into strength too early.",
        decisionProcess="test process",
        departmentOpinions=[],
        missedInformation="test missed info",
        lessonsLearned="Wait for confirmation before acting on a single signal.",
        recommendedImprovements="test improvement",
        relatedPrinciples=[],
        tradePnlPct=-1.0,
        simDay=10,
        createdAt=_now_iso(),
    )


def _risk_warning(*, warning_id: str = "risk-1") -> RiskWarning:
    return RiskWarning(
        id=warning_id,
        symbol="NEXA",
        severity="critical",  # type: ignore[arg-type]
        message="Portfolio concentration exceeds the configured limit.",
        createdAt=_now_iso(),
    )


def _challenge_report(*, report_id: str = "challenge-1", historical_comparisons: list[str] | None = None, assigned_agent: str = "coach") -> ChallengeReport:
    return ChallengeReport(
        id=report_id,
        proposalId="proposal-1",
        symbol="NEXA",
        assignedAgent=assigned_agent,  # type: ignore[arg-type]
        tradeSummary="test summary",
        bullCase="test bull case",
        bearCase="test bear case",
        hiddenRisks=[],
        weakAssumptions=[],
        missingEvidence=[],
        historicalComparisons=historical_comparisons or [],
        worstCaseScenario="test worst case",
        suggestedImprovements=[],
        severity="minor",  # type: ignore[arg-type]
        finalRecommendation="test recommendation",
        createdAt=_now_iso(),
    )


class TestRecordKnowledgeEvent:
    def test_none_event_is_a_no_op(self) -> None:
        assert record_knowledge_event([], None) == []

    def test_appends_a_real_event(self) -> None:
        entry = promote_risk_event(_risk_warning(), sim_day=1)
        event = lesson_created_event(entry)
        updated = record_knowledge_event([], event)
        assert len(updated) == 1

    def test_replaying_the_same_trigger_is_idempotent(self) -> None:
        entry = promote_risk_event(_risk_warning(), sim_day=1)
        event = lesson_created_event(entry)
        once = record_knowledge_event([], event)
        twice = record_knowledge_event(once, event)
        assert len(twice) == 1

    def test_caps_at_max_entries(self) -> None:
        events: list[KnowledgeEvent] = []
        for i in range(5):
            entry = promote_risk_event(_risk_warning(warning_id=f"risk-{i}"), sim_day=1)
            event = lesson_created_event(entry)
            events = record_knowledge_event(events, event, max_entries=3)
        assert len(events) == 3


class TestLessonCreatedEvent:
    def test_no_event_for_an_entry_with_no_lesson(self) -> None:
        entry = promote_risk_event(_risk_warning(), sim_day=1).model_copy(update={"lesson": None})
        assert lesson_created_event(entry) is None

    def test_real_event_for_an_entry_with_a_lesson(self) -> None:
        entry = promote_case_study(_case_study())
        event = lesson_created_event(entry)
        assert event is not None
        assert event.type == "lesson_created"
        assert event.lesson_id == entry.id
        assert event.detail == entry.lesson


class TestLessonConfirmedEvent:
    def test_links_to_the_standing_entry_not_the_new_one(self) -> None:
        old_entry = promote_case_study(_case_study(case_id="case-old"))
        new_entry = promote_case_study(_case_study(case_id="case-new"))
        event = lesson_confirmed_event(new_entry, old_entry.id)
        assert event.type == "lesson_confirmed"
        assert event.lesson_id == old_entry.id


class TestShareLessonWithRelevantAgents:
    def test_no_sharing_for_an_entry_with_no_lesson(self) -> None:
        entry = promote_risk_event(_risk_warning(), sim_day=1).model_copy(update={"lesson": None})
        assert share_lesson_with_relevant_agents(entry) == []

    def test_shares_with_real_relevant_role_class_agents(self) -> None:
        entry = promote_case_study(_case_study())
        events = share_lesson_with_relevant_agents(entry)
        assert any(e.type == "lesson_shared" for e in events)
        received = [e for e in events if e.type == "knowledge_received"]
        assert len(received) > 0
        assert all(e.agent_id is not None for e in received)

    def test_originating_agent_never_receives_their_own_lesson(self) -> None:
        entry = promote_case_study(_case_study()).model_copy(update={"originating_agent": "sentinel"})
        events = share_lesson_with_relevant_agents(entry)
        received_agents = {e.agent_id for e in events if e.type == "knowledge_received"}
        assert "sentinel" not in received_agents

    def test_risk_event_routes_only_to_the_real_risk_role_class(self) -> None:
        entry = promote_risk_event(_risk_warning(), sim_day=1)
        events = share_lesson_with_relevant_agents(entry)
        received_agents = {e.agent_id for e in events if e.type == "knowledge_received"}
        assert received_agents == {"sentinel", "guardian", "keystone"}


class TestRecordKnowledgeApplicationFromChallenge:
    def test_no_event_when_nothing_was_cited(self) -> None:
        report = _challenge_report(historical_comparisons=[])
        assert record_knowledge_application_from_challenge(report, [], [], sim_day=10) is None

    def test_no_event_when_the_citation_does_not_resolve_to_a_real_promoted_entry(self) -> None:
        case_study = _case_study(case_id="case-1", title="Broke below support too early")
        report = _challenge_report(historical_comparisons=["Broke below support too early"])
        # institutional_memory deliberately empty — the citation exists in case_studies
        # but was never actually promoted into institutional memory.
        assert record_knowledge_application_from_challenge(report, [case_study], [], sim_day=10) is None

    def test_real_citation_resolves_to_knowledge_applied(self) -> None:
        case_study = _case_study(case_id="case-1", title="Broke below support too early")
        promoted = promote_case_study(case_study)
        report = _challenge_report(historical_comparisons=["Broke below support too early"], assigned_agent="coach")
        event = record_knowledge_application_from_challenge(report, [case_study], [promoted], sim_day=10)
        assert event is not None
        assert event.type == "knowledge_applied"
        assert event.lesson_id == promoted.id
        assert event.agent_id == "coach"

    def test_idempotent_on_the_same_challenge_report(self) -> None:
        case_study = _case_study(case_id="case-1", title="Broke below support too early")
        promoted = promote_case_study(case_study)
        report = _challenge_report(historical_comparisons=["Broke below support too early"])
        first = record_knowledge_application_from_challenge(report, [case_study], [promoted], sim_day=10)
        second = record_knowledge_application_from_challenge(report, [case_study], [promoted], sim_day=10)
        assert first is not None and second is not None
        assert first.id == second.id
