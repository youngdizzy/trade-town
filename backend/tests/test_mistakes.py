"""Covers app/mistakes.py — v0.7 Feature 27, the Library of Mistakes.
Every CaseStudyCategory must trace to one real, checkable signal on the
linked TradeDecision/Debate/PaperTrade; this file checks each category
fires exactly when its real trigger condition holds and not otherwise.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.discipline import generate_discipline_review
from app.mistakes import generate_case_studies, record_case_studies
from app.schemas import AgentVote, ConfidenceFactor, Debate, DebateTurn, DecisionConfidence, PaperTrade, TradeDecision


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


def _trade(*, side: str = "buy", duration_minutes: int = 240, pnl: float = -50.0, pnl_pct: float = -2.0, decision_id: str = "decision-proposal-1") -> PaperTrade:
    return PaperTrade(
        id="trade-1",
        symbol="NEXA",
        side=side,  # type: ignore[arg-type]
        quantity=10.0,
        entryPrice=100.0,
        exitPrice=98.0,
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


class TestDetectCategories:
    def test_overconfidence_fires_when_the_setup_scored_80_plus_and_lost(self) -> None:
        decision = _decision(confidence_engine=_confidence_engine(score=85.0, research_score=90.0, exposure_score=90.0))
        debate = _debate([_debate_turn("echo", "technical", "opening"), _debate_turn("scout", "news", "challenge")])
        trade = _trade(duration_minutes=300)
        studies = generate_case_studies(decision, debate, trade, _review(decision, debate, trade), id_prefix="case-1")
        assert any(s.category == "overconfidence" for s in studies)

    def test_no_overconfidence_case_study_when_the_setup_scored_below_80(self) -> None:
        decision = _decision(confidence_engine=_confidence_engine(score=60.0, research_score=90.0, exposure_score=90.0))
        debate = _debate([_debate_turn("echo", "technical", "opening"), _debate_turn("scout", "news", "challenge")])
        trade = _trade(duration_minutes=300)
        studies = generate_case_studies(decision, debate, trade, _review(decision, debate, trade), id_prefix="case-2")
        assert not any(s.category == "overconfidence" for s in studies)

    def test_incomplete_research_fires_when_research_confidence_factor_is_below_50(self) -> None:
        decision = _decision(confidence_engine=_confidence_engine(score=60.0, research_score=30.0, exposure_score=90.0))
        debate = _debate([_debate_turn("echo", "technical", "opening"), _debate_turn("scout", "news", "challenge")])
        trade = _trade(duration_minutes=300)
        studies = generate_case_studies(decision, debate, trade, _review(decision, debate, trade), id_prefix="case-3")
        assert any(s.category == "incomplete_research" for s in studies)

    def test_unchallenged_assumptions_fires_with_no_debate_at_all(self) -> None:
        decision = _decision(confidence_engine=_confidence_engine(score=60.0, research_score=90.0, exposure_score=90.0))
        trade = _trade(duration_minutes=300)
        studies = generate_case_studies(decision, None, trade, _review(decision, None, trade), id_prefix="case-4")
        assert any(s.category == "unchallenged_assumptions" for s in studies)

    def test_unchallenged_assumptions_does_not_fire_when_a_real_challenge_turn_exists(self) -> None:
        decision = _decision(confidence_engine=_confidence_engine(score=60.0, research_score=90.0, exposure_score=90.0))
        debate = _debate([_debate_turn("echo", "technical", "opening"), _debate_turn("scout", "news", "challenge")])
        trade = _trade(duration_minutes=300)
        studies = generate_case_studies(decision, debate, trade, _review(decision, debate, trade), id_prefix="case-5")
        assert not any(s.category == "unchallenged_assumptions" for s in studies)

    def test_acted_too_quickly_fires_under_the_quick_close_threshold(self) -> None:
        decision = _decision(confidence_engine=_confidence_engine(score=60.0, research_score=90.0, exposure_score=90.0))
        debate = _debate([_debate_turn("echo", "technical", "opening"), _debate_turn("scout", "news", "challenge")])
        trade = _trade(duration_minutes=60)
        studies = generate_case_studies(decision, debate, trade, _review(decision, debate, trade), id_prefix="case-6")
        assert any(s.category == "acted_too_quickly" for s in studies)

    def test_ignored_dissent_fires_when_the_debates_own_synthesis_disagreed_with_the_real_executed_side(self) -> None:
        decision = _decision(confidence_engine=_confidence_engine(score=60.0, research_score=90.0, exposure_score=90.0))
        debate = _debate([_debate_turn("echo", "technical", "opening"), _debate_turn("scout", "news", "challenge")], final="sell")
        trade = _trade(side="buy", duration_minutes=300)
        studies = generate_case_studies(decision, debate, trade, _review(decision, debate, trade), id_prefix="case-7")
        assert any(s.category == "ignored_dissent" for s in studies)

    def test_confirmation_bias_fires_when_echo_or_scout_dissent_was_overridden(self) -> None:
        decision = _decision(opposing=["echo"], confidence_engine=_confidence_engine(score=60.0, research_score=90.0, exposure_score=90.0))
        debate = _debate([_debate_turn("echo", "technical", "opening"), _debate_turn("scout", "news", "challenge")])
        trade = _trade(duration_minutes=300)
        studies = generate_case_studies(decision, debate, trade, _review(decision, debate, trade), id_prefix="case-8")
        assert any(s.category == "confirmation_bias" for s in studies)

    def test_a_clean_process_produces_no_case_studies_even_on_a_loss(self) -> None:
        decision = _decision(confidence_engine=_confidence_engine(score=60.0, research_score=90.0, exposure_score=90.0))
        debate = _debate([_debate_turn("echo", "technical", "opening"), _debate_turn("scout", "news", "challenge")], final="buy")
        trade = _trade(side="buy", duration_minutes=300)
        studies = generate_case_studies(decision, debate, trade, _review(decision, debate, trade), id_prefix="case-9")
        assert studies == []


class TestCaseStudyContent:
    def test_department_opinions_are_the_real_vote_reasons(self) -> None:
        decision = _decision(votes=[AgentVote(agentId="echo", choice="buy", reason="a specific real reason")])  # type: ignore[arg-type]
        trade = _trade(duration_minutes=60)
        studies = generate_case_studies(decision, None, trade, _review(decision, None, trade), id_prefix="case-10")
        assert any("a specific real reason" in s.department_opinions[0] for s in studies)

    def test_timeline_uses_the_real_decision_and_trade_timestamps(self) -> None:
        decision = _decision()
        trade = _trade(duration_minutes=60)
        studies = generate_case_studies(decision, None, trade, _review(decision, None, trade), id_prefix="case-11")
        timeline = studies[0].timeline
        assert timeline[0].timestamp == decision.created_at
        assert timeline[1].timestamp == trade.opened_at
        assert timeline[2].timestamp == trade.closed_at

    def test_related_principles_are_non_empty_and_real(self) -> None:
        decision = _decision()
        trade = _trade(duration_minutes=60)
        studies = generate_case_studies(decision, None, trade, _review(decision, None, trade), id_prefix="case-12")
        assert all(s.related_principles for s in studies)


class TestRecordCaseStudies:
    def test_caps_at_max_case_studies(self) -> None:
        decision = _decision()
        trade = _trade(duration_minutes=60)
        studies: list = []
        for i in range(70):
            new = generate_case_studies(decision, None, trade, _review(decision, None, trade), id_prefix=f"case-{i}")
            studies = record_case_studies(studies, new)
        assert len(studies) == 60
