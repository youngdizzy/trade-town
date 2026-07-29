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
    CaseStudy,
    DisciplineFactor,
    DisciplineReview,
    GatekeeperRejection,
    MemoryRecord,
    PaperTrade,
    PostDecisionReview,
    ResearchItem,
    TimeState,
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
    return compute_wisdom_score(discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[])


class TestComputeWisdomScore:
    def test_never_reads_pnl_identical_process_scores_identically_regardless_of_win_or_loss(self) -> None:
        win_review = _review(score=70.0, outcome="win")
        loss_review = _review(score=70.0, outcome="loss")
        win_state = compute_wisdom_score(discipline_reviews=[win_review], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[])
        loss_state = compute_wisdom_score(discipline_reviews=[loss_review], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[])
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
        no_mentorship = compute_wisdom_score(discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[])
        with_mentorship = compute_wisdom_score(discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[_memory("mentorship"), _memory("mentorship")])
        no_share = next(f for f in no_mentorship.factors if f.id == "share_knowledge")
        with_share = next(f for f in with_mentorship.factors if f.id == "share_knowledge")
        assert with_share.score > no_share.score

    def test_higher_gatekeeper_rejection_rate_lowers_follow_principles(self) -> None:
        clean = compute_wisdom_score(discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[_trade(), _trade()], gatekeeper_rejections=[], memory=[])
        rejected = compute_wisdom_score(discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[], trade_history=[_trade()], gatekeeper_rejections=[_rejection()], memory=[])
        clean_factor = next(f for f in clean.factors if f.id == "follow_principles")
        rejected_factor = next(f for f in rejected.factors if f.id == "follow_principles")
        assert clean_factor.score > rejected_factor.score

    def test_diversified_case_study_categories_score_higher_on_avoid_repeating_mistakes(self) -> None:
        repeated = compute_wisdom_score(discipline_reviews=[], case_studies=[_case_study(category="overconfidence"), _case_study(category="overconfidence"), _case_study(category="overconfidence")], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[])
        diversified = compute_wisdom_score(discipline_reviews=[], case_studies=[_case_study(category="overconfidence"), _case_study(category="acted_too_quickly"), _case_study(category="ignored_dissent")], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[])
        repeated_factor = next(f for f in repeated.factors if f.id == "avoid_repeating_mistakes")
        diversified_factor = next(f for f in diversified.factors if f.id == "avoid_repeating_mistakes")
        assert diversified_factor.score > repeated_factor.score

    def test_completed_research_ratio_drives_complete_research_factor(self) -> None:
        state = compute_wisdom_score(discipline_reviews=[], case_studies=[], reasoning_challenges=[], research=[_research_item(status="completed"), _research_item(status="in_progress")], trade_history=[], gatekeeper_rejections=[], memory=[])
        factor = next(f for f in state.factors if f.id == "complete_research")
        assert factor.score == 50.0

    def test_higher_cross_examination_scores_raise_improve_communication(self) -> None:
        weak = compute_wisdom_score(discipline_reviews=[_review(factors=[_factor("cross_examination", 20.0)])], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[])
        strong = compute_wisdom_score(discipline_reviews=[_review(factors=[_factor("cross_examination", 90.0)])], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[])
        weak_factor = next(f for f in weak.factors if f.id == "improve_communication")
        strong_factor = next(f for f in strong.factors if f.id == "improve_communication")
        assert strong_factor.score > weak_factor.score

    def test_higher_viewpoint_diversity_scores_raise_support_collaboration(self) -> None:
        weak = compute_wisdom_score(discipline_reviews=[_review(factors=[_factor("viewpoint_diversity", 20.0)])], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[])
        strong = compute_wisdom_score(discipline_reviews=[_review(factors=[_factor("viewpoint_diversity", 90.0)])], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[])
        weak_factor = next(f for f in weak.factors if f.id == "support_collaboration")
        strong_factor = next(f for f in strong.factors if f.id == "support_collaboration")
        assert strong_factor.score > weak_factor.score

    def test_more_documented_records_raise_document_lessons(self) -> None:
        few = compute_wisdom_score(discipline_reviews=[_review()], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[])
        many = compute_wisdom_score(discipline_reviews=[_review(), _review(), _review()], case_studies=[_case_study(), _case_study()], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[])
        few_factor = next(f for f in few.factors if f.id == "document_lessons")
        many_factor = next(f for f in many.factors if f.id == "document_lessons")
        assert many_factor.score > few_factor.score

    def test_improving_discipline_scores_over_time_raises_learn_from_experience(self) -> None:
        declining = [_review(score=90.0), _review(score=90.0), _review(score=40.0), _review(score=40.0)]
        improving = [_review(score=40.0), _review(score=40.0), _review(score=90.0), _review(score=90.0)]
        declining_state = compute_wisdom_score(discipline_reviews=declining, case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[])
        improving_state = compute_wisdom_score(discipline_reviews=improving, case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[])
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
        state = compute_wisdom_score(discipline_reviews=[_review(score=90.0)], case_studies=[], reasoning_challenges=[], research=[], trade_history=[], gatekeeper_rejections=[], memory=[])
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
