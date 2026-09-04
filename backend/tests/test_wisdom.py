"""Covers app/wisdom.py — v0.7 Feature 30, the Reflection Chamber. The
core rule under test throughout: Company Wisdom never reads pnl —
compute_wisdom_score()'s signature has no pnl/profit parameter at all —
only real process/behavior signals already computed elsewhere.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.wisdom import (
    compute_wisdom_score,
    generate_reflection_session,
)
from app.schemas import (
    AGENT_IDS,
    AgentVote,
    AuditEntry,
    CaseStudy,
    CeoDecisionRecord,
    Debate,
    DebateTurn,
    DecisionConfidence,
    DisciplineFactor,
    DisciplineReview,
    GatekeeperRejection,
    InstitutionalMemoryEntry,
    KnowledgeEvent,
    MemoryRecord,
    PaperTrade,
    PostDecisionReview,
    ResearchItem,
    TimeState,
    TradeDecision,
    WisdomState,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _factor(factor_id: str, score: float) -> DisciplineFactor:
    return DisciplineFactor(id=factor_id, name=factor_id.replace("_", " ").title(), score=score, weight=0.15, detail="test")  # type: ignore[arg-type]


def _review(*, score: float = 70.0, outcome: str = "win", factors: list[DisciplineFactor] | None = None) -> DisciplineReview:
    return DisciplineReview(
        id=f"discipline-test-{score}-{outcome}",
        decisionId="decision-1",
        symbol="NEXA",
        score=score,
        tier="sound",
        factors=factors or [_factor("cross_examination", 70.0), _factor("viewpoint_diversity", 70.0)],
        attendees=["echo"],  # type: ignore[arg-type]
        summary="test summary",
        postDecisionReview=PostDecisionReview(),
        outcome=outcome,  # type: ignore[arg-type]
        tradePnlPct=1.0 if outcome == "win" else -1.0,
        holdDurationMinutes=240,
        simDay=1,
        createdAt=_now_iso(),
    )


def _case_study(*, category: str = "overconfidence") -> CaseStudy:
    return CaseStudy(
        id=f"case-test-{category}-{_now_iso()}",
        category=category,  # type: ignore[arg-type]
        title="test title",
        symbol="NEXA",
        decisionId="decision-1",
        timeline=[],
        background="test background",
        decisionProcess="test process",
        departmentOpinions=[],
        missedInformation="test missed info",
        lessonsLearned="test lesson",
        recommendedImprovements="test improvement",
        relatedPrinciples=[],
        tradePnlPct=-1.0,
        simDay=1,
        createdAt=_now_iso(),
    )


def _research_item(*, status: str = "completed", confidence: float = 80.0) -> ResearchItem:
    return ResearchItem(
        id=f"research-test-{status}-{confidence}",
        title="test research",
        symbol="NEXA",
        category="stock",  # type: ignore[arg-type]
        priority="normal",  # type: ignore[arg-type]
        status=status,  # type: ignore[arg-type]
        assignedAgent="nova",  # type: ignore[arg-type]
        summary="test summary",
        confidence=confidence,
        createdAt=_now_iso(),
        updatedAt=_now_iso(),
    )


def _trade() -> PaperTrade:
    return PaperTrade(
        id="trade-1",
        symbol="NEXA",
        side="buy",  # type: ignore[arg-type]
        quantity=1.0,
        entryPrice=100.0,
        exitPrice=101.0,
        pnl=1.0,
        pnlPct=1.0,
        durationMinutes=240,
        confidence=80.0,
        reason="test",
        marketConditions="test",
        openedAt=_now_iso(),
        closedAt=_now_iso(),
    )


def _rejection() -> GatekeeperRejection:
    return GatekeeperRejection(
        id="rejection-1",
        proposalId="proposal-1",
        symbol="NEXA",
        ceoChoice="buy",  # type: ignore[arg-type]
        reasons=["test reason"],
        priceAtRejection=100.0,
        rejectedSimMinutes=100,
        createdAt=_now_iso(),
    )


def _memory(category: str) -> MemoryRecord:
    return MemoryRecord(id=f"memory-{category}-{_now_iso()}", category=category, title="test", body="test body", timestamp=_now_iso())  # type: ignore[arg-type]


def _empty_wisdom_score() -> WisdomState:
    return compute_wisdom_score(discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[], institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)


class TestComputeWisdomScore:
    def test_never_reads_pnl_identical_process_scores_identically_regardless_of_win_or_loss(self) -> None:
        win_review = _review(score=70.0, outcome="win")
        loss_review = _review(score=70.0, outcome="loss")
        win_state = compute_wisdom_score(discipline_reviews=[win_review], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[], institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        loss_state = compute_wisdom_score(discipline_reviews=[loss_review], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[], institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        assert win_state.score == loss_state.score

    def test_fresh_company_has_no_data_reads_as_a_low_early_tier(self) -> None:
        state = _empty_wisdom_score()
        assert state.tier in ("young_company", "developing_judgment")
        assert state.score < 50.0
        assert len(state.factors) == 8

    def test_eight_factors_equally_weighted(self) -> None:
        state = _empty_wisdom_score()
        for factor in state.factors:
            assert round(factor.weight, 3) == round(1.0 / 8, 3)

    def test_more_mentorship_memory_raises_share_knowledge_factor(self) -> None:
        no_mentorship = compute_wisdom_score(discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[], institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        with_mentorship = compute_wisdom_score(discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[_memory("mentorship"), _memory("mentorship")], institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        no_share = next(f for f in no_mentorship.factors if f.id == "share_knowledge")
        with_share = next(f for f in with_mentorship.factors if f.id == "share_knowledge")
        assert with_share.score > no_share.score

    def test_higher_gatekeeper_rejection_rate_lowers_follow_principles(self) -> None:
        clean = compute_wisdom_score(discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[_trade(), _trade()], gatekeeper_rejections=[], memory=[], institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        rejected = compute_wisdom_score(discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[_trade()], gatekeeper_rejections=[_rejection()], memory=[], institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        clean_factor = next(f for f in clean.factors if f.id == "follow_principles")
        rejected_factor = next(f for f in rejected.factors if f.id == "follow_principles")
        assert clean_factor.score > rejected_factor.score

    def test_diversified_case_study_categories_score_higher_on_avoid_repeating_mistakes(self) -> None:
        repeated = compute_wisdom_score(discipline_reviews=[], case_studies=[_case_study(category="overconfidence"), _case_study(category="overconfidence"), _case_study(category="overconfidence")], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[], institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        diversified = compute_wisdom_score(discipline_reviews=[], case_studies=[_case_study(category="overconfidence"), _case_study(category="acted_too_quickly"), _case_study(category="ignored_dissent")], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[], institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        repeated_factor = next(f for f in repeated.factors if f.id == "avoid_repeating_mistakes")
        diversified_factor = next(f for f in diversified.factors if f.id == "avoid_repeating_mistakes")
        assert diversified_factor.score > repeated_factor.score

    def test_completed_research_ratio_drives_complete_research_factor(self) -> None:
        state = compute_wisdom_score(discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[_research_item(status="completed"), _research_item(status="in_progress")], trade_history=[], gatekeeper_rejections=[], memory=[], institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        factor = next(f for f in state.factors if f.id == "complete_research")
        assert factor.score == 50.0

    def test_higher_cross_examination_scores_raise_improve_communication(self) -> None:
        weak = compute_wisdom_score(discipline_reviews=[_review(factors=[_factor("cross_examination", 20.0)])], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[], institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        strong = compute_wisdom_score(discipline_reviews=[_review(factors=[_factor("cross_examination", 90.0)])], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[], institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        weak_factor = next(f for f in weak.factors if f.id == "improve_communication")
        strong_factor = next(f for f in strong.factors if f.id == "improve_communication")
        assert strong_factor.score > weak_factor.score

    def test_higher_viewpoint_diversity_scores_raise_support_collaboration(self) -> None:
        weak = compute_wisdom_score(discipline_reviews=[_review(factors=[_factor("viewpoint_diversity", 20.0)])], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[], institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        strong = compute_wisdom_score(discipline_reviews=[_review(factors=[_factor("viewpoint_diversity", 90.0)])], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[], institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        weak_factor = next(f for f in weak.factors if f.id == "support_collaboration")
        strong_factor = next(f for f in strong.factors if f.id == "support_collaboration")
        assert strong_factor.score > weak_factor.score

    def test_more_documented_records_raise_document_lessons(self) -> None:
        few = compute_wisdom_score(discipline_reviews=[_review()], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[], institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        many = compute_wisdom_score(discipline_reviews=[_review(), _review(), _review()], case_studies=[_case_study(), _case_study()], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[], institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        few_factor = next(f for f in few.factors if f.id == "document_lessons")
        many_factor = next(f for f in many.factors if f.id == "document_lessons")
        assert many_factor.score > few_factor.score

    def test_improving_discipline_scores_over_time_raises_learn_from_experience(self) -> None:
        declining = [_review(score=90.0), _review(score=90.0), _review(score=40.0), _review(score=40.0)]
        improving = [_review(score=40.0), _review(score=40.0), _review(score=90.0), _review(score=90.0)]
        declining_state = compute_wisdom_score(discipline_reviews=declining, case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[], institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        improving_state = compute_wisdom_score(discipline_reviews=improving, case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[], institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        declining_factor = next(f for f in declining_state.factors if f.id == "learn_from_experience")
        improving_factor = next(f for f in improving_state.factors if f.id == "learn_from_experience")
        assert improving_factor.score > declining_factor.score


class TestGenerateReflectionSession:
    def test_every_real_agent_attends(self) -> None:
        session = generate_reflection_session(
            "weekly",
            discipline_reviews=[],
            case_studies=[],
            reasoning_challenges=[],
            research=[],
            news=[],
            risk_warnings=[],
            gatekeeper_rejections=[],
            executive_reviews=[],
            wisdom_state=_empty_wisdom_score(),
            new_time=TimeState(day=7, hour=20, minute=0),
        )
        # v0.7 Feature 39 — the Original Founders (keystone/compass) are
        # real agents too, and genuinely attend the Reflection Chamber
        # (see their own schedule.py entries) — the roster grew from 11
        # to len(AGENT_IDS), not a regression.
        assert len(session.attendees) == len(AGENT_IDS)
        assert len(session.questions) == 9

    def test_honest_defaults_with_no_history(self) -> None:
        session = generate_reflection_session(
            "monthly",
            discipline_reviews=[],
            case_studies=[],
            reasoning_challenges=[],
            research=[],
            news=[],
            risk_warnings=[],
            gatekeeper_rejections=[],
            executive_reviews=[],
            wisdom_state=_empty_wisdom_score(),
            new_time=TimeState(day=30, hour=20, minute=0),
        )
        surprise_answer = next(q.answer for q in session.questions if q.question == "What surprised us?")
        assert "No real mismatch" in surprise_answer
        assert session.cadence == "monthly"
        assert session.sim_day == 30

    def test_mismatch_review_surfaces_as_a_surprise(self) -> None:
        mismatch = _review(score=80.0, outcome="loss")
        session = generate_reflection_session(
            "weekly",
            discipline_reviews=[mismatch],
            case_studies=[],
            reasoning_challenges=[],
            research=[],
            news=[],
            risk_warnings=[],
            gatekeeper_rejections=[],
            executive_reviews=[],
            wisdom_state=_empty_wisdom_score(),
            new_time=TimeState(day=7, hour=20, minute=0),
        )
        surprise_answer = next(q.answer for q in session.questions if q.question == "What surprised us?")
        assert "NEXA" in surprise_answer

    def test_wisdom_score_on_the_session_matches_the_passed_in_state(self) -> None:
        state = compute_wisdom_score(discipline_reviews=[_review(score=90.0)], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[], institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        session = generate_reflection_session(
            "weekly",
            discipline_reviews=[_review(score=90.0)],
            case_studies=[],
            reasoning_challenges=[],
            research=[],
            news=[],
            risk_warnings=[],
            gatekeeper_rejections=[],
            executive_reviews=[],
            wisdom_state=state,
            new_time=TimeState(day=7, hour=20, minute=0),
        )
        assert session.wisdom_score == state.score

    def test_a_success_category_as_the_most_common_case_study_does_not_crash(self) -> None:
        """Regression test — case_studies is a real mixed list of both
        mistakes (app/mistakes.py) and successes (app/successes.py); a
        save whose most common real category happened to be a success
        one (e.g. "disciplined_process") used to raise a KeyError because
        the title lookup only covered the six mistake categories. See
        app/wisdom.py's _CATEGORY_TITLES fix."""
        success_studies = [_case_study(category="disciplined_process") for _ in range(3)]
        session = generate_reflection_session(
            "weekly",
            discipline_reviews=[],
            case_studies=success_studies,
            reasoning_challenges=[],
            research=[],
            news=[],
            risk_warnings=[],
            gatekeeper_rejections=[],
            executive_reviews=[],
            wisdom_state=_empty_wisdom_score(),
            new_time=TimeState(day=7, hour=20, minute=0),
        )
        patterns_answer = next(q.answer for q in session.questions if q.question == "What patterns are repeating?")
        assert "A Well-Disciplined Process" in patterns_answer


def _institutional_memory_entry(
    *,
    entry_id: str = "im-1",
    source: str = "risk_event",
    lesson: str | None = "A real, documented lesson.",
) -> InstitutionalMemoryEntry:
    return InstitutionalMemoryEntry(
        id=entry_id,
        source=source,  # type: ignore[arg-type]
        createdAt=_now_iso(),
        simDay=1,
        eventRef="event-1",
        observation="A real observed event.",
        lesson=lesson,
        confidence=50.0,
        provenance="test provenance",
        relevancePct=50.0,
    )


def _knowledge_event(
    *,
    event_id: str = "ke-1",
    event_type: str = "lesson_shared",
    lesson_id: str = "im-1",
    agent_id: str | None = "nova",
) -> KnowledgeEvent:
    return KnowledgeEvent(
        id=event_id,
        type=event_type,  # type: ignore[arg-type]
        lessonId=lesson_id,
        agentId=agent_id,  # type: ignore[arg-type]
        simDay=1,
        detail="test detail",
        createdAt=_now_iso(),
    )


def _audit_entry(*, entry_id: str = "audit-1") -> AuditEntry:
    return AuditEntry(
        id=entry_id,
        timestamp=_now_iso(),
        simDay=1,
        category="gatekeeper_rejection",  # type: ignore[arg-type]
        severity="warning",  # type: ignore[arg-type]
        department="Trade Gatekeeper",
        summary="test summary",
        detail="test detail",
    )


class TestShareKnowledgeReusesRealKnowledgeEvents:
    def test_lesson_shared_events_raise_the_factor_even_without_mentorship(self) -> None:
        without = compute_wisdom_score(discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[], institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        with_shared = compute_wisdom_score(discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[], institutional_memory=[], knowledge_events=[_knowledge_event(event_type="lesson_shared")], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        without_factor = next(f for f in without.factors if f.id == "share_knowledge")
        with_factor = next(f for f in with_shared.factors if f.id == "share_knowledge")
        assert with_factor.score > without_factor.score

    def test_knowledge_received_events_alone_do_not_double_count(self) -> None:
        """One lesson_shared act fans out into several knowledge_received
        events (one per recipient) — those must not each add their own
        weight, or a widely-shared lesson would be worth more than a
        narrowly-shared one for no real reason."""
        shared_only = compute_wisdom_score(discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[], institutional_memory=[], knowledge_events=[_knowledge_event(event_id="ke-1", event_type="lesson_shared")], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        shared_and_received = compute_wisdom_score(
            discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[],
            institutional_memory=[],
            knowledge_events=[
                _knowledge_event(event_id="ke-1", event_type="lesson_shared"),
                _knowledge_event(event_id="ke-2", event_type="knowledge_received", agent_id="scout"),
                _knowledge_event(event_id="ke-3", event_type="knowledge_received", agent_id="atlas"),
            ],
            audit_entries=[],
            decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        shared_only_factor = next(f for f in shared_only.factors if f.id == "share_knowledge")
        shared_and_received_factor = next(f for f in shared_and_received.factors if f.id == "share_knowledge")
        assert shared_only_factor.score == shared_and_received_factor.score


class TestFollowPrinciplesFallsBackToRealComplianceScore:
    def test_no_trades_yet_uses_the_real_audit_log_compliance_score_not_a_bare_default(self) -> None:
        no_incidents = compute_wisdom_score(discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[], institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        with_incidents = compute_wisdom_score(discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[], institutional_memory=[], knowledge_events=[], audit_entries=[_audit_entry(entry_id="a1"), _audit_entry(entry_id="a2")], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        no_incidents_factor = next(f for f in no_incidents.factors if f.id == "follow_principles")
        with_incidents_factor = next(f for f in with_incidents.factors if f.id == "follow_principles")
        assert no_incidents_factor.score == 100.0
        assert with_incidents_factor.score < no_incidents_factor.score

    def test_once_real_trade_history_exists_the_original_ratio_takes_over_unchanged(self) -> None:
        """Audit-log evidence must never override the real ratio once
        real trade/rejection history exists — it's only a fallback for
        the "nothing has happened yet" case."""
        state = compute_wisdom_score(
            discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[_trade()], gatekeeper_rejections=[],
            memory=[], institutional_memory=[], knowledge_events=[],
            audit_entries=[_audit_entry(entry_id="a1"), _audit_entry(entry_id="a2"), _audit_entry(entry_id="a3")],
            decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        factor = next(f for f in state.factors if f.id == "follow_principles")
        assert factor.score == 100.0


class TestDocumentLessonsReusesInstitutionalMemory:
    def test_documented_institutional_memory_lessons_raise_the_factor(self) -> None:
        without = compute_wisdom_score(discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[], institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        with_lessons = compute_wisdom_score(
            discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[],
            institutional_memory=[_institutional_memory_entry(entry_id="im-1"), _institutional_memory_entry(entry_id="im-2")],
            knowledge_events=[], audit_entries=[],
            decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        without_factor = next(f for f in without.factors if f.id == "document_lessons")
        with_factor = next(f for f in with_lessons.factors if f.id == "document_lessons")
        assert with_factor.score > without_factor.score

    def test_entries_without_a_real_lesson_are_not_counted(self) -> None:
        state = compute_wisdom_score(
            discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[],
            institutional_memory=[_institutional_memory_entry(entry_id="im-1", lesson=None)],
            knowledge_events=[], audit_entries=[],
            decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        factor = next(f for f in state.factors if f.id == "document_lessons")
        assert factor.score == 0.0


class TestAvoidRepeatingMistakesReusesLessonConfirmedEvents:
    def test_no_case_studies_and_no_confirmations_reads_as_the_disclosed_baseline(self) -> None:
        state = compute_wisdom_score(discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[], institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        factor = next(f for f in state.factors if f.id == "avoid_repeating_mistakes")
        assert factor.score == 50.0

    def test_a_confirmed_mistake_pattern_lowers_the_factor_below_the_baseline(self) -> None:
        mistake_entry = _institutional_memory_entry(entry_id="im-mistake", source="behavioral_mistake")
        state = compute_wisdom_score(
            discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[],
            institutional_memory=[mistake_entry],
            knowledge_events=[_knowledge_event(event_type="lesson_confirmed", lesson_id="im-mistake")],
            audit_entries=[],
            decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        factor = next(f for f in state.factors if f.id == "avoid_repeating_mistakes")
        assert factor.score < 50.0

    def test_a_confirmation_of_a_non_mistake_lesson_does_not_lower_the_factor(self) -> None:
        success_entry = _institutional_memory_entry(entry_id="im-success", source="behavioral_success")
        state = compute_wisdom_score(
            discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[],
            institutional_memory=[success_entry],
            knowledge_events=[_knowledge_event(event_type="lesson_confirmed", lesson_id="im-success")],
            audit_entries=[],
            decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        factor = next(f for f in state.factors if f.id == "avoid_repeating_mistakes")
        assert factor.score == 50.0

    def test_once_real_case_studies_exist_the_original_diversity_formula_takes_over_unchanged(self) -> None:
        """Real lesson_confirmed evidence must never override the
        original category-diversity formula once real case studies
        exist — it's only a fallback for the "no case studies yet" case."""
        mistake_entry = _institutional_memory_entry(entry_id="im-mistake", source="behavioral_mistake")
        case_studies = [_case_study(category="overconfidence"), _case_study(category="acted_too_quickly"), _case_study(category="ignored_dissent")]
        state = compute_wisdom_score(
            discipline_reviews=[], case_studies=case_studies,
            reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[],
            institutional_memory=[mistake_entry],
            knowledge_events=[_knowledge_event(event_type="lesson_confirmed", lesson_id="im-mistake")],
            audit_entries=[],
            decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        factor = next(f for f in state.factors if f.id == "avoid_repeating_mistakes")
        # Real category-diversity formula (unchanged): 1/3 dominant share → 100 - 33.3.
        assert round(factor.score, 1) == round(100.0 - (1 / 3) * 100.0, 1)


def _confidence_engine(*, score: float = 80.0) -> DecisionConfidence:
    return DecisionConfidence(score=score, tier="strong", summary="test summary", factors=[])


def _decision(*, votes: list[AgentVote] | None = None, decision_id: str = "decision-1", decision_grade_score: float | None = None) -> TradeDecision:
    return TradeDecision(
        id=decision_id,
        symbol="NEXA",
        outcome="trade",
        votes=votes or [AgentVote(agentId="echo", choice="buy", reason="trend confirmed")],  # type: ignore[arg-type]
        researchSummary="test research summary",
        technicalSummary="test technical summary",
        fundamentalSummary="test fundamental summary",
        riskSummary="test risk summary",
        supportingAgents=["echo"],  # type: ignore[arg-type]
        opposingAgents=[],
        confidence=80.0,
        finalReasoning="CEO approved BUY on NEXA.",
        orderId="pos-1",
        confidenceEngine=_confidence_engine(),
        decisionGradeScore=decision_grade_score,
        createdAt=_now_iso(),
    )


def _ceo_decision(*, decision_id: str, proposal_id: str) -> CeoDecisionRecord:
    return CeoDecisionRecord(
        id=f"ceo-{proposal_id}",
        proposalId=proposal_id,
        symbol="NEXA",
        category="stock",  # type: ignore[arg-type]
        aiRecommendation="buy",  # type: ignore[arg-type]
        ceoDecision="buy",  # type: ignore[arg-type]
        agreedWithAi=True,
        decisionId=decision_id,
        outcome="pending",
        resolvedBy="ceo",  # type: ignore[arg-type]
        createdAt=_now_iso(),
    )


def _debate_turn(agent_id: str, stance: str) -> DebateTurn:
    return DebateTurn(agentId=agent_id, role="technical", stance=stance, text="test turn text")  # type: ignore[arg-type]


def _debate(turns: list[DebateTurn], proposal_id: str) -> Debate:
    return Debate(id=f"debate-{proposal_id}", proposalId=proposal_id, symbol="NEXA", turns=turns, finalRecommendation="buy", finalSummary="test summary", createdAt=_now_iso())  # type: ignore[arg-type]


class TestLearnFromExperienceFallsBackToDecisionGradeTrend:
    def test_fewer_than_four_decisions_reads_as_the_disclosed_baseline(self) -> None:
        state = compute_wisdom_score(
            discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[],
            institutional_memory=[], knowledge_events=[], audit_entries=[],
            decisions=[_decision(decision_id="d1", decision_grade_score=90.0)], ceo_decisions=[], debates=[], collaboration_case_score=None)
        factor = next(f for f in state.factors if f.id == "learn_from_experience")
        assert factor.score == 30.0

    def test_improving_decision_grade_scores_over_time_raises_the_factor(self) -> None:
        declining = [_decision(decision_id=f"d{i}", decision_grade_score=s) for i, s in enumerate([90.0, 90.0, 40.0, 40.0])]
        improving = [_decision(decision_id=f"d{i}", decision_grade_score=s) for i, s in enumerate([40.0, 40.0, 90.0, 90.0])]
        declining_state = compute_wisdom_score(
            discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[],
            institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=declining, ceo_decisions=[], debates=[], collaboration_case_score=None)
        improving_state = compute_wisdom_score(
            discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[],
            institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=improving, ceo_decisions=[], debates=[], collaboration_case_score=None)
        declining_factor = next(f for f in declining_state.factors if f.id == "learn_from_experience")
        improving_factor = next(f for f in improving_state.factors if f.id == "learn_from_experience")
        assert improving_factor.score > declining_factor.score

    def test_once_real_discipline_reviews_exist_the_original_trend_formula_takes_over_unchanged(self) -> None:
        """Real decision-grade evidence must never override the original
        DisciplineReview trend once >=4 real reviews exist — it's only a
        fallback for "not enough closed-trade evidence yet"."""
        declining_reviews = [_review(score=90.0), _review(score=90.0), _review(score=40.0), _review(score=40.0)]
        state = compute_wisdom_score(
            discipline_reviews=declining_reviews, case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[],
            institutional_memory=[], knowledge_events=[], audit_entries=[],
            decisions=[_decision(decision_id=f"d{i}", decision_grade_score=90.0) for i in range(4)], ceo_decisions=[], debates=[], collaboration_case_score=None)
        factor = next(f for f in state.factors if f.id == "learn_from_experience")
        assert factor.score < 50.0


class TestImproveCommunicationFallsBackToDecisionTimeCrossExamination:
    def test_no_discipline_reviews_and_no_decisions_reads_as_the_disclosed_baseline(self) -> None:
        state = compute_wisdom_score(
            discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[],
            institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        factor = next(f for f in state.factors if f.id == "improve_communication")
        assert factor.score == 30.0

    def test_real_cross_examination_turns_beyond_opening_statements_raise_the_factor(self) -> None:
        votes = [AgentVote(agentId="echo", choice="buy", reason="x"), AgentVote(agentId="scout", choice="sell", reason="y")]  # type: ignore[arg-type]
        decision = _decision(decision_id="d1", votes=votes)
        ceo_decision = _ceo_decision(decision_id="d1", proposal_id="p1")
        no_debate_state = compute_wisdom_score(
            discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[],
            institutional_memory=[], knowledge_events=[], audit_entries=[],
            decisions=[decision], ceo_decisions=[ceo_decision], debates=[], collaboration_case_score=None)
        rich_debate = _debate([_debate_turn("echo", "opening"), _debate_turn("scout", "opening"), _debate_turn("echo", "support"), _debate_turn("scout", "challenge")], proposal_id="p1")
        with_debate_state = compute_wisdom_score(
            discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[],
            institutional_memory=[], knowledge_events=[], audit_entries=[],
            decisions=[decision], ceo_decisions=[ceo_decision], debates=[rich_debate], collaboration_case_score=None)
        no_debate_factor = next(f for f in no_debate_state.factors if f.id == "improve_communication")
        with_debate_factor = next(f for f in with_debate_state.factors if f.id == "improve_communication")
        assert with_debate_factor.score > no_debate_factor.score

    def test_once_real_discipline_reviews_exist_the_original_average_takes_over_unchanged(self) -> None:
        weak_review = _review(factors=[_factor("cross_examination", 20.0)])
        votes = [AgentVote(agentId="echo", choice="buy", reason="x"), AgentVote(agentId="scout", choice="sell", reason="y")]  # type: ignore[arg-type]
        rich_debate = _debate([_debate_turn("echo", "opening"), _debate_turn("scout", "opening"), _debate_turn("echo", "support"), _debate_turn("scout", "challenge")], proposal_id="p1")
        state = compute_wisdom_score(
            discipline_reviews=[weak_review], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[],
            institutional_memory=[], knowledge_events=[], audit_entries=[],
            decisions=[_decision(decision_id="d1", votes=votes)], ceo_decisions=[_ceo_decision(decision_id="d1", proposal_id="p1")], debates=[rich_debate], collaboration_case_score=None)
        factor = next(f for f in state.factors if f.id == "improve_communication")
        assert factor.score == 20.0


class TestSupportCollaborationFallsBackToDecisionTimeViewpointDiversity:
    def test_no_discipline_reviews_and_no_decisions_reads_as_the_disclosed_baseline(self) -> None:
        state = compute_wisdom_score(
            discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[],
            institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=[], ceo_decisions=[], debates=[], collaboration_case_score=None)
        factor = next(f for f in state.factors if f.id == "support_collaboration")
        assert factor.score == 30.0

    def test_more_distinct_real_vote_choices_raise_the_factor(self) -> None:
        uniform_votes = [AgentVote(agentId="echo", choice="buy", reason="x"), AgentVote(agentId="scout", choice="buy", reason="y")]  # type: ignore[arg-type]
        diverse_votes = [AgentVote(agentId="echo", choice="buy", reason="x"), AgentVote(agentId="scout", choice="sell", reason="y"), AgentVote(agentId="nova", choice="hold", reason="z")]  # type: ignore[arg-type]
        uniform_state = compute_wisdom_score(
            discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[],
            institutional_memory=[], knowledge_events=[], audit_entries=[],
            decisions=[_decision(decision_id="d1", votes=uniform_votes)], ceo_decisions=[], debates=[], collaboration_case_score=None)
        diverse_state = compute_wisdom_score(
            discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[],
            institutional_memory=[], knowledge_events=[], audit_entries=[],
            decisions=[_decision(decision_id="d1", votes=diverse_votes)], ceo_decisions=[], debates=[], collaboration_case_score=None)
        uniform_factor = next(f for f in uniform_state.factors if f.id == "support_collaboration")
        diverse_factor = next(f for f in diverse_state.factors if f.id == "support_collaboration")
        assert diverse_factor.score > uniform_factor.score

    def test_once_real_discipline_reviews_exist_the_original_average_takes_over_unchanged(self) -> None:
        weak_review = _review(factors=[_factor("viewpoint_diversity", 20.0)])
        diverse_votes = [AgentVote(agentId="echo", choice="buy", reason="x"), AgentVote(agentId="scout", choice="sell", reason="y"), AgentVote(agentId="nova", choice="hold", reason="z")]  # type: ignore[arg-type]
        state = compute_wisdom_score(
            discipline_reviews=[weak_review], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[],
            institutional_memory=[], knowledge_events=[], audit_entries=[],
            decisions=[_decision(decision_id="d1", votes=diverse_votes)], ceo_decisions=[], debates=[], collaboration_case_score=None)
        factor = next(f for f in state.factors if f.id == "support_collaboration")
        assert factor.score == 20.0
        assert factor.score != 50.0


class TestSupportCollaborationPrefersCollaborationCaseScoreOverAnalystVoteFallback:
    """"TradeTown — Department Debate & Collaboration Intelligence 1.0"
    layered a richer, department-level fallback (real collaboration-case
    evidence) above the prior milestone's decision-time analyst-vote
    fallback — both are available at the same real gate (a resolved
    decision), so the richer one must win whenever it exists."""

    def test_real_collaboration_case_score_wins_over_analyst_vote_fallback(self) -> None:
        diverse_votes = [AgentVote(agentId="echo", choice="buy", reason="x"), AgentVote(agentId="scout", choice="sell", reason="y"), AgentVote(agentId="nova", choice="hold", reason="z")]  # type: ignore[arg-type]
        state = compute_wisdom_score(
            discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[],
            institutional_memory=[], knowledge_events=[], audit_entries=[],
            decisions=[_decision(decision_id="d1", votes=diverse_votes)], ceo_decisions=[], debates=[],
            collaboration_case_score=42.0,
        )
        factor = next(f for f in state.factors if f.id == "support_collaboration")
        assert factor.score == 42.0

    def test_falls_back_to_analyst_vote_signal_when_no_collaboration_case_exists_yet(self) -> None:
        diverse_votes = [AgentVote(agentId="echo", choice="buy", reason="x"), AgentVote(agentId="scout", choice="sell", reason="y"), AgentVote(agentId="nova", choice="hold", reason="z")]  # type: ignore[arg-type]
        state = compute_wisdom_score(
            discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[],
            institutional_memory=[], knowledge_events=[], audit_entries=[],
            decisions=[_decision(decision_id="d1", votes=diverse_votes)], ceo_decisions=[], debates=[],
            collaboration_case_score=None,
        )
        factor = next(f for f in state.factors if f.id == "support_collaboration")
        assert factor.score == 100.0  # the analyst-vote fallback's own 3-distinct-choices tier

    def test_real_discipline_review_average_still_wins_over_collaboration_case_score(self) -> None:
        weak_review = _review(factors=[_factor("viewpoint_diversity", 20.0)])
        state = compute_wisdom_score(
            discipline_reviews=[weak_review], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[],
            institutional_memory=[], knowledge_events=[], audit_entries=[], decisions=[], ceo_decisions=[], debates=[],
            collaboration_case_score=90.0,
        )
        factor = next(f for f in state.factors if f.id == "support_collaboration")
        assert factor.score == 20.0
