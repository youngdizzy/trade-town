"""Covers app/successes.py — v0.7 Feature 42, the Library of Successes half
of the Decision Replay Center's "Successes" lesson type. Every category
must trace to one real, checkable signal on the linked DisciplineReview —
this file checks each fires exactly when its real trigger condition holds
and not otherwise, mirroring test_mistakes.py's structure for the loss side.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.discipline import generate_discipline_review
from app.schemas import AgentVote, ConfidenceFactor, Debate, DebateTurn, DecisionConfidence, PaperTrade, TradeDecision
from app.successes import generate_success_studies, record_success_studies


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _confidence_engine(*, score: float = 60.0, research_score: float = 60.0, exposure_score: float = 60.0) -> DecisionConfidence:
    return DecisionConfidence(
        score=score,
        tier="good",
        summary="test summary",
        factors=[
            ConfidenceFactor(name="Research Confidence", score=research_score, weight=0.15, detail="test"),
            ConfidenceFactor(name="Portfolio Exposure", score=exposure_score, weight=0.05, detail="test"),
        ],
    )


def _decision(
    *,
    votes: list[AgentVote] | None = None,
    supporting: list[str] | None = None,
    opposing: list[str] | None = None,
    confidence_engine: DecisionConfidence | None = None,
) -> TradeDecision:
    return TradeDecision(
        id="decision-proposal-1",
        symbol="NEXA",
        outcome="trade",
        votes=votes or [AgentVote(agentId="echo", choice="buy", reason="trend confirmed")],  # type: ignore[arg-type]
        researchSummary="test research summary",
        technicalSummary="test technical summary",
        fundamentalSummary="test fundamental summary",
        riskSummary="test risk summary",
        supportingAgents=supporting or ["echo"],  # type: ignore[arg-type]
        opposingAgents=opposing or [],  # type: ignore[arg-type]
        confidence=80.0,
        finalReasoning="CEO approved BUY on NEXA.",
        orderId="pos-1",
        confidenceEngine=confidence_engine or _confidence_engine(),
        createdAt=_now_iso(),
    )


def _debate_turn(agent_id: str, role: str, stance: str) -> DebateTurn:
    return DebateTurn(agentId=agent_id, role=role, stance=stance, text="test turn text")  # type: ignore[arg-type]


def _debate(turns: list[DebateTurn], final: str = "buy") -> Debate:
    return Debate(id="debate-proposal-1", proposalId="proposal-1", symbol="NEXA", turns=turns, finalRecommendation=final, finalSummary="test summary", createdAt=_now_iso())  # type: ignore[arg-type]


def _trade(*, side: str = "buy", duration_minutes: int = 240, pnl: float = 50.0, pnl_pct: float = 2.0, decision_id: str = "decision-proposal-1") -> PaperTrade:
    return PaperTrade(
        id="trade-1",
        symbol="NEXA",
        side=side,  # type: ignore[arg-type]
        quantity=10.0,
        entryPrice=100.0,
        exitPrice=102.0,
        pnl=pnl,
        pnlPct=pnl_pct,
        durationMinutes=duration_minutes,
        confidence=80.0,
        reason="test reason",
        marketConditions="test market conditions",
        decisionId=decision_id,
        openedAt=_now_iso(),
        closedAt=_now_iso(),
    )


def _review(decision: TradeDecision, debate: Debate | None, trade: PaperTrade):
    return generate_discipline_review(
        decision, debate, hold_duration_minutes=trade.duration_minutes, pnl=trade.pnl, pnl_pct=trade.pnl_pct, review_id="discipline-1", sim_day=1, created_at=_now_iso()
    )


# PATIENCE_TARGET_MINUTES is 240 per discipline.py (patience_score hits
# 100 exactly at the target) — see discipline.py for the constant.
PATIENT_HOLD_MINUTES = 240


class TestDetectCategories:
    def test_disciplined_process_fires_when_score_is_70_or_above_and_the_trade_won(self) -> None:
        decision = _decision(confidence_engine=_confidence_engine(score=60.0, research_score=90.0, exposure_score=90.0))
        debate = _debate([_debate_turn("echo", "technical", "opening"), _debate_turn("scout", "news", "challenge"), _debate_turn("nova", "macro", "support")])
        trade = _trade(duration_minutes=PATIENT_HOLD_MINUTES)
        studies = generate_success_studies(decision, debate, trade, _review(decision, debate, trade), id_prefix="case-1")
        assert any(s.category == "disciplined_process" for s in studies)

    def test_disciplined_process_does_not_fire_when_score_is_below_70(self) -> None:
        decision = _decision(votes=[AgentVote(agentId="echo", choice="buy", reason="test")], confidence_engine=_confidence_engine(score=60.0, research_score=20.0, exposure_score=20.0))  # type: ignore[arg-type]
        trade = _trade(duration_minutes=30)
        studies = generate_success_studies(decision, None, trade, _review(decision, None, trade), id_prefix="case-2")
        assert not any(s.category == "disciplined_process" for s in studies)

    def test_rigorous_cross_examination_fires_with_real_cross_exam_turns_beyond_openings(self) -> None:
        decision = _decision(confidence_engine=_confidence_engine(score=60.0, research_score=90.0, exposure_score=90.0))
        debate = _debate([_debate_turn("echo", "technical", "opening"), _debate_turn("scout", "news", "challenge"), _debate_turn("nova", "macro", "support")])
        trade = _trade(duration_minutes=300)
        studies = generate_success_studies(decision, debate, trade, _review(decision, debate, trade), id_prefix="case-3")
        assert any(s.category == "rigorous_cross_examination" for s in studies)

    def test_rigorous_cross_examination_does_not_fire_with_no_debate(self) -> None:
        decision = _decision(confidence_engine=_confidence_engine(score=90.0, research_score=90.0, exposure_score=90.0))
        trade = _trade(duration_minutes=300)
        studies = generate_success_studies(decision, None, trade, _review(decision, None, trade), id_prefix="case-4")
        assert not any(s.category == "rigorous_cross_examination" for s in studies)

    def test_patient_execution_fires_at_or_past_the_patient_hold_target(self) -> None:
        decision = _decision(confidence_engine=_confidence_engine(score=60.0, research_score=90.0, exposure_score=90.0))
        trade = _trade(duration_minutes=PATIENT_HOLD_MINUTES)
        studies = generate_success_studies(decision, None, trade, _review(decision, None, trade), id_prefix="case-5")
        assert any(s.category == "patient_execution" for s in studies)

    def test_patient_execution_does_not_fire_on_a_quick_close(self) -> None:
        decision = _decision(confidence_engine=_confidence_engine(score=60.0, research_score=90.0, exposure_score=90.0))
        trade = _trade(duration_minutes=30)
        studies = generate_success_studies(decision, None, trade, _review(decision, None, trade), id_prefix="case-6")
        assert not any(s.category == "patient_execution" for s in studies)

    def test_a_weak_process_win_produces_no_success_studies(self) -> None:
        decision = _decision(votes=[AgentVote(agentId="echo", choice="buy", reason="test")], confidence_engine=_confidence_engine(score=60.0, research_score=20.0, exposure_score=20.0))  # type: ignore[arg-type]
        trade = _trade(duration_minutes=10)
        studies = generate_success_studies(decision, None, trade, _review(decision, None, trade), id_prefix="case-7")
        assert studies == []


class TestSuccessStudyContent:
    def test_department_opinions_are_the_real_vote_reasons(self) -> None:
        decision = _decision(votes=[AgentVote(agentId="echo", choice="buy", reason="a specific real reason")])  # type: ignore[arg-type]
        trade = _trade(duration_minutes=PATIENT_HOLD_MINUTES)
        studies = generate_success_studies(decision, None, trade, _review(decision, None, trade), id_prefix="case-8")
        assert any("a specific real reason" in s.department_opinions[0] for s in studies)

    def test_timeline_uses_the_real_decision_and_trade_timestamps(self) -> None:
        decision = _decision()
        trade = _trade(duration_minutes=PATIENT_HOLD_MINUTES)
        studies = generate_success_studies(decision, None, trade, _review(decision, None, trade), id_prefix="case-9")
        timeline = studies[0].timeline
        assert timeline[0].timestamp == decision.created_at
        assert timeline[1].timestamp == trade.opened_at
        assert timeline[2].timestamp == trade.closed_at

    def test_related_principles_are_non_empty_and_real(self) -> None:
        decision = _decision()
        trade = _trade(duration_minutes=PATIENT_HOLD_MINUTES)
        studies = generate_success_studies(decision, None, trade, _review(decision, None, trade), id_prefix="case-10")
        assert all(s.related_principles for s in studies)


class TestRecordSuccessStudies:
    def test_caps_at_max_success_studies(self) -> None:
        decision = _decision()
        trade = _trade(duration_minutes=PATIENT_HOLD_MINUTES)
        studies: list = []
        for i in range(70):
            new = generate_success_studies(decision, None, trade, _review(decision, None, trade), id_prefix=f"case-{i}")
            studies = record_success_studies(studies, new)
        assert len(studies) == 60
