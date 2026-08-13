"""Covers app/founders.py — v0.7 Feature 39, the Original Founders."""
from __future__ import annotations

from datetime import datetime, timezone

from app.founders import (
    FOUNDER_QUOTES,
    compute_founder_state,
    generate_council_session,
    generate_founder_log_entry,
    record_council_session,
    record_founder_log,
)
from app.schemas import (
    CaseStudy,
    CaseStudyTimelineEntry,
    CoachReport,
    DisciplineFactor,
    DisciplineReview,
    FounderState,
    PostDecisionReview,
    ReasoningChallenge,
    ReasoningContribution,
    ReasoningSolution,
    ReflectionSession,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _discipline_review(*, sim_day: int = 2) -> DisciplineReview:
    return DisciplineReview(
        id="review-1",
        decisionId="decision-1",
        symbol="NEXA",
        score=70.0,
        tier="sound",
        factors=[DisciplineFactor(id="research_depth", name="Research Depth", score=80.0, weight=0.2, detail="test")],
        attendees=["sentinel"],  # type: ignore[arg-type]
        summary="test summary",
        postDecisionReview=PostDecisionReview(),
        outcome="win",
        tradePnlPct=3.5,
        holdDurationMinutes=300,
        simDay=sim_day,
        createdAt=_now_iso(),
    )


def _case_study(*, sim_day: int = 3) -> CaseStudy:
    return CaseStudy(
        id="case-1",
        category="overconfidence",  # type: ignore[arg-type]
        title="Chased a rally on NEXA",
        symbol="NEXA",
        decisionId="decision-1",
        timeline=[CaseStudyTimelineEntry(label="Opened", timestamp=_now_iso())],
        background="test background",
        decisionProcess="test process",
        departmentOpinions=["echo: momentum looked strong"],
        missedInformation="test missed info",
        lessonsLearned="Don't chase strength without confirmation.",
        recommendedImprovements="test improvements",
        relatedPrinciples=["Max position size"],
        tradePnlPct=-4.2,
        simDay=sim_day,
        createdAt=_now_iso(),
    )


def _reasoning_challenge(*, sim_day: int = 2) -> ReasoningChallenge:
    return ReasoningChallenge(
        id="reasoning-1",
        category="finding_missing_information",  # type: ignore[arg-type]
        title="What we missed on NEXA",
        symbol="NEXA",
        decisionId="decision-1",
        contributions=[ReasoningContribution(agentId="echo", role="technical", stance="opening", contribution="test")],  # type: ignore[arg-type]
        solution=ReasoningSolution(whatWeKnow=[], whatWeDoNotKnow=[], assumptions=[], whyReasonable="test", confidence=80.0, whatCouldChangeOurConclusion="test"),
        reasoningLevel=1,
        simDay=sim_day,
        createdAt=_now_iso(),
    )


def _reflection_session(*, sim_day: int = 3, lessons_learned: list[str] | None = None) -> ReflectionSession:
    return ReflectionSession(
        id="reflection-1",
        cadence="weekly",
        attendees=["sage"],  # type: ignore[arg-type]
        questions=[],
        insights=[],
        keyDiscoveries=[],
        lessonsLearned=lessons_learned or [],
        importantQuestions=[],
        recommendedFutureProjects=[],
        wisdomScore=30.0,
        simDay=sim_day,
        createdAt=_now_iso(),
    )


def _coach_report(*, strengths: list[str] | None = None, recommendations: list[str] | None = None) -> CoachReport:
    return CoachReport(
        id="coach-1",
        period="monthly",  # type: ignore[arg-type]
        companyScore=60.0,
        agentRankings=[],
        researchAccuracy=50.0,
        winRate=50.0,
        lossRate=50.0,
        averageConfidence=50.0,
        riskScore=50.0,
        commonMistakes=[],
        strengths=strengths or [],
        recommendations=recommendations or [],
        createdAt=_now_iso(),
    )


class TestGenerateFounderLogEntry:
    def test_keystone_is_none_with_no_real_history(self) -> None:
        entry = generate_founder_log_entry(
            "keystone",
            sim_day=1,
            entry_id="founder-log-1",
            created_at=_now_iso(),
            discipline_reviews=[],
            case_studies=[],
            reasoning_challenges=[],
            reflection_sessions=[],
        )
        assert entry is None

    def test_compass_is_none_with_no_real_history(self) -> None:
        entry = generate_founder_log_entry(
            "compass",
            sim_day=1,
            entry_id="founder-log-1",
            created_at=_now_iso(),
            discipline_reviews=[],
            case_studies=[],
            reasoning_challenges=[],
            reflection_sessions=[],
        )
        assert entry is None

    def test_keystone_references_the_real_discipline_review(self) -> None:
        review = _discipline_review()
        entry = generate_founder_log_entry(
            "keystone",
            sim_day=5,
            entry_id="founder-log-5",
            created_at=_now_iso(),
            discipline_reviews=[review],
            case_studies=[],
            reasoning_challenges=[],
            reflection_sessions=[],
        )
        assert entry is not None
        assert entry.founder_id == "keystone"
        assert "NEXA" in entry.line
        assert entry.reference != ""

    def test_keystone_prefers_the_more_recent_case_study_over_an_older_review(self) -> None:
        review = _discipline_review(sim_day=2)
        case = _case_study(sim_day=9)
        entry = generate_founder_log_entry(
            "keystone",
            sim_day=10,
            entry_id="founder-log-10",
            created_at=_now_iso(),
            discipline_reviews=[review],
            case_studies=[case],
            reasoning_challenges=[],
            reflection_sessions=[],
        )
        assert entry is not None
        assert "Library of Mistakes" in entry.line

    def test_compass_references_the_real_reasoning_challenge(self) -> None:
        challenge = _reasoning_challenge()
        entry = generate_founder_log_entry(
            "compass",
            sim_day=5,
            entry_id="founder-log-5",
            created_at=_now_iso(),
            discipline_reviews=[],
            case_studies=[],
            reasoning_challenges=[challenge],
            reflection_sessions=[],
        )
        assert entry is not None
        assert entry.founder_id == "compass"
        assert "Reasoning Lab" in entry.line

    def test_compass_surfaces_a_real_lesson_from_the_reflection_session(self) -> None:
        session = _reflection_session(sim_day=9, lessons_learned=["Patience beats prediction."])
        entry = generate_founder_log_entry(
            "compass",
            sim_day=10,
            entry_id="founder-log-10",
            created_at=_now_iso(),
            discipline_reviews=[],
            case_studies=[],
            reasoning_challenges=[],
            reflection_sessions=[session],
        )
        assert entry is not None
        assert "Patience beats prediction." in entry.line

    def test_quote_cycles_deterministically_by_sim_day(self) -> None:
        challenge = _reasoning_challenge()
        first = generate_founder_log_entry(
            "compass", sim_day=1, entry_id="a", created_at=_now_iso(), discipline_reviews=[], case_studies=[], reasoning_challenges=[challenge], reflection_sessions=[]
        )
        again = generate_founder_log_entry(
            "compass", sim_day=1, entry_id="b", created_at=_now_iso(), discipline_reviews=[], case_studies=[], reasoning_challenges=[challenge], reflection_sessions=[]
        )
        assert first is not None and again is not None
        assert first.line == again.line
        quote = FOUNDER_QUOTES["compass"][1 % len(FOUNDER_QUOTES["compass"])]
        assert quote in first.line


class TestRecordFounderLog:
    def test_caps_at_max_entries(self) -> None:
        from app.founders import MAX_FOUNDER_LOG

        log: list = []
        for day in range(MAX_FOUNDER_LOG + 10):
            entry = generate_founder_log_entry(
                "keystone",
                sim_day=day,
                entry_id=f"founder-log-{day}",
                created_at=_now_iso(),
                discipline_reviews=[_discipline_review(sim_day=day)],
                case_studies=[],
                reasoning_challenges=[],
                reflection_sessions=[],
            )
            assert entry is not None
            log = record_founder_log(log, entry)
        assert len(log) == MAX_FOUNDER_LOG


class TestGenerateCouncilSession:
    def test_honest_defaults_with_no_history(self) -> None:
        session = generate_council_session(
            sim_day=30,
            session_id="council-30",
            created_at=_now_iso(),
            latest_coach_report=None,
            discipline_reviews=[],
            case_studies=[],
            reasoning_challenges=[],
            reflection_sessions=[],
        )
        assert "No Coach Report" in session.coach_highlight
        assert "Nothing to review" in session.keystone_note
        assert "Nothing new" in session.compass_note

    def test_real_content_when_history_exists(self) -> None:
        report = _coach_report(strengths=["Research accuracy held above 70% all month."])
        session = generate_council_session(
            sim_day=30,
            session_id="council-30",
            created_at=_now_iso(),
            latest_coach_report=report,
            discipline_reviews=[_discipline_review()],
            case_studies=[],
            reasoning_challenges=[_reasoning_challenge()],
            reflection_sessions=[],
        )
        assert session.coach_highlight == "Research accuracy held above 70% all month."
        assert "NEXA" in session.keystone_note
        assert "Reasoning Lab" in session.compass_note

    def test_falls_back_to_recommendation_when_no_strengths_recorded(self) -> None:
        report = _coach_report(recommendations=["Tighten position sizing on high-volatility symbols."])
        session = generate_council_session(
            sim_day=30, session_id="council-30", created_at=_now_iso(), latest_coach_report=report, discipline_reviews=[], case_studies=[], reasoning_challenges=[], reflection_sessions=[]
        )
        assert session.coach_highlight == "Tighten position sizing on high-volatility symbols."

    def test_is_real_flags_are_false_with_no_history(self) -> None:
        """CEO Company/Executive Health directive, Phase 4 — every note
        that fell back to founders.py's own honest placeholder text
        must record that real fact, not silently read as real."""
        session = generate_council_session(
            sim_day=30,
            session_id="council-30",
            created_at=_now_iso(),
            latest_coach_report=None,
            discipline_reviews=[],
            case_studies=[],
            reasoning_challenges=[],
            reflection_sessions=[],
        )
        assert session.coach_highlight_is_real is False
        assert session.keystone_note_is_real is False
        assert session.compass_note_is_real is False

    def test_is_real_flags_are_true_with_real_history(self) -> None:
        report = _coach_report(strengths=["Research accuracy held above 70% all month."])
        session = generate_council_session(
            sim_day=30,
            session_id="council-30",
            created_at=_now_iso(),
            latest_coach_report=report,
            discipline_reviews=[_discipline_review()],
            case_studies=[],
            reasoning_challenges=[_reasoning_challenge()],
            reflection_sessions=[],
        )
        assert session.coach_highlight_is_real is True
        assert session.keystone_note_is_real is True
        assert session.compass_note_is_real is True

    def test_coach_highlight_is_real_even_via_the_recommendation_fallback(self) -> None:
        """A real recommendation (not a strength) still counts as real
        content — only the truly generic "no standout pattern" text
        should read False."""
        report = _coach_report(recommendations=["Tighten position sizing on high-volatility symbols."])
        session = generate_council_session(
            sim_day=30, session_id="council-30", created_at=_now_iso(), latest_coach_report=report, discipline_reviews=[], case_studies=[], reasoning_challenges=[], reflection_sessions=[]
        )
        assert session.coach_highlight_is_real is True


class TestRecordCouncilSession:
    def test_caps_at_max_sessions(self) -> None:
        from app.founders import MAX_COUNCIL_SESSIONS

        sessions: list = []
        for day in range(MAX_COUNCIL_SESSIONS + 5):
            session = generate_council_session(
                sim_day=day, session_id=f"council-{day}", created_at=_now_iso(), latest_coach_report=None, discipline_reviews=[], case_studies=[], reasoning_challenges=[], reflection_sessions=[]
            )
            sessions = record_council_session(sessions, session)
        assert len(sessions) == MAX_COUNCIL_SESSIONS


class TestComputeFounderState:
    def test_stays_active_below_the_excellent_tier(self) -> None:
        previous = FounderState(updatedAt=_now_iso())
        updated = compute_founder_state(previous, company_health_tier="good", updated_at=_now_iso())
        assert updated.retired is False
        assert updated.retired_at is None

    def test_retires_permanently_the_first_time_health_reaches_excellent(self) -> None:
        previous = FounderState(updatedAt=_now_iso())
        retired_at = _now_iso()
        updated = compute_founder_state(previous, company_health_tier="excellent", updated_at=retired_at)
        assert updated.retired is True
        assert updated.retired_at == retired_at

    def test_never_un_retires_once_health_drops_again(self) -> None:
        previous = FounderState(retired=True, retiredAt="2026-01-01T00:00:00+00:00", updatedAt=_now_iso())
        updated = compute_founder_state(previous, company_health_tier="critical", updated_at=_now_iso())
        assert updated.retired is True
        assert updated.retired_at == "2026-01-01T00:00:00+00:00"
