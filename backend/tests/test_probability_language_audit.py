"""Covers app/probability_language.py — Trading Psychology & Discipline,
Piece E. Runs find_certainty_violations()/audit_model() against REAL
generated output (DisciplineReview, CaseStudy mistake/success, Debate) —
not source code — so a future template that drifts into certainty-of-
outcome language fails this suite immediately. Fixtures mirror the
existing patterns already established in test_discipline.py/
test_mistakes.py/test_successes.py/test_debate.py.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.debate import generate_debate
from app.discipline import generate_discipline_review
from app.mistakes import generate_case_studies
from app.probability_language import (
    BANNED_CERTAINTY_PHRASES,
    audit_model,
    find_certainty_violations,
)
from app.schemas import (
    AgentVote,
    AnalystVote,
    ConfidenceFactor,
    Debate,
    DebateTurn,
    DecisionConfidence,
    PaperTrade,
    TradeDecision,
    TradeProposal,
)
from app.successes import generate_success_studies


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _confidence_engine(*, score: float = 85.0, research_score: float = 90.0, exposure_score: float = 90.0) -> DecisionConfidence:
    return DecisionConfidence(
        score=score,
        tier="strong",
        summary="Strong Setup (85/100).",
        factors=[
            ConfidenceFactor(name="Research Confidence", score=research_score, weight=0.15, detail="test"),
            ConfidenceFactor(name="Portfolio Exposure", score=exposure_score, weight=0.05, detail="test"),
        ],
    )


def _decision() -> TradeDecision:
    return TradeDecision(
        id="decision-proposal-1",
        symbol="NEXA",
        outcome="trade",
        votes=[AgentVote(agentId="echo", choice="buy", reason="trend confirmed")],  # type: ignore[arg-type]
        researchSummary="test research summary",
        technicalSummary="test technical summary",
        fundamentalSummary="test fundamental summary",
        riskSummary="test risk summary",
        supportingAgents=["echo"],  # type: ignore[arg-type]
        opposingAgents=[],  # type: ignore[arg-type]
        confidence=80.0,
        finalReasoning="CEO approved BUY on NEXA.",
        orderId="pos-1",
        confidenceEngine=_confidence_engine(),
        createdAt=_now_iso(),
    )


def _debate_turn(agent_id: str, role: str, stance: str) -> DebateTurn:
    return DebateTurn(agentId=agent_id, role=role, stance=stance, text="test turn text")  # type: ignore[arg-type]


def _decision_debate() -> Debate:
    return Debate(
        id="debate-proposal-1",
        proposalId="proposal-1",
        symbol="NEXA",
        turns=[_debate_turn("echo", "technical", "opening"), _debate_turn("scout", "news", "challenge")],
        finalRecommendation="buy",  # type: ignore[arg-type]
        finalSummary="test summary",
        createdAt=_now_iso(),
    )


def _trade(*, pnl: float, pnl_pct: float) -> PaperTrade:
    return PaperTrade(
        id="trade-1",
        symbol="NEXA",
        side="buy",  # type: ignore[arg-type]
        quantity=10.0,
        entryPrice=100.0,
        exitPrice=98.0,
        pnl=pnl,
        pnlPct=pnl_pct,
        durationMinutes=300,
        confidence=80.0,
        reason="test reason",
        marketConditions="test market conditions",
        decisionId="decision-proposal-1",
        openedAt=_now_iso(),
        closedAt=_now_iso(),
    )


def _analyst_vote(role: str, agent_id: str, choice: str, reasoning: str) -> AnalystVote:
    return AnalystVote(role=role, agentId=agent_id, choice=choice, reasoning=reasoning, evidence=["real evidence line"])  # type: ignore[arg-type]


def _six_votes() -> list[AnalystVote]:
    role_to_agent = {"technical": "echo", "news": "scout", "macro": "nova", "risk": "sentinel", "sentiment": "pulse", "execution": "atlas"}
    return [_analyst_vote(role, agent, "buy", reasoning=f"{role} desk reasoning: evidence favors the setup, not a certainty.") for role, agent in role_to_agent.items()]


def _proposal() -> TradeProposal:
    return TradeProposal(
        id="proposal-1",
        symbol="NEXA",
        category="stock",
        quantity=10.0,
        price=100.0,
        confidence=90.0,
        analystVotes=_six_votes(),
        overallRecommendation="buy",  # type: ignore[arg-type]
        researchSummary="test research summary",
        riskSummary="test risk summary",
        confidenceEngine=_confidence_engine(),
        createdAt=_now_iso(),
        createdSimMinutes=0,
    )


class TestFindCertaintyViolations:
    def test_clean_text_has_no_violations(self) -> None:
        assert find_certainty_violations("The setup scored 85/100 — a likely edge, not a guarantee.") == []

    def test_hedged_negated_guarantee_language_is_not_flagged(self) -> None:
        # This codebase's own correct usage — "not a guarantee" must never
        # false-positive, since a bare-word ban would flag exactly the
        # probability-first phrasing this module exists to protect.
        assert find_certainty_violations("An estimate, not a guarantee.") == []
        assert find_certainty_violations("A probable zone is not a guarantee price ever reaches it.") == []

    def test_a_genuine_certainty_phrase_is_flagged(self) -> None:
        assert "sure thing" in find_certainty_violations("This is a sure thing.")

    def test_every_banned_phrase_is_individually_detectable(self) -> None:
        for phrase in BANNED_CERTAINTY_PHRASES:
            # Some banned phrases legitimately overlap as substrings
            # (e.g. "...this guaranteed to win..." also contains "is
            # guaranteed to") — both are genuine hits on real certainty
            # language, so assert containment rather than an exact single-
            # element match.
            assert phrase in find_certainty_violations(f"The desk covers this: {phrase}, today.")


class TestAuditModelAgainstRealGeneratedOutput:
    """The permanent regression guard: runs the checker against REAL
    output from this codebase's real generators, not synthetic text."""

    def test_discipline_review_is_clean(self) -> None:
        decision = _decision()
        debate = _decision_debate()
        review = generate_discipline_review(decision, debate, hold_duration_minutes=300, pnl=-50.0, pnl_pct=-2.0, review_id="discipline-1", sim_day=1, created_at=_now_iso())
        assert audit_model(review) == {}

    def test_discipline_review_win_case_is_clean(self) -> None:
        decision = _decision()
        debate = _decision_debate()
        review = generate_discipline_review(decision, debate, hold_duration_minutes=300, pnl=50.0, pnl_pct=2.0, review_id="discipline-2", sim_day=1, created_at=_now_iso())
        assert audit_model(review) == {}

    def test_mistake_case_studies_are_clean(self) -> None:
        decision = _decision()
        debate = _decision_debate()
        trade = _trade(pnl=-50.0, pnl_pct=-2.0)
        review = generate_discipline_review(decision, debate, hold_duration_minutes=trade.duration_minutes, pnl=trade.pnl, pnl_pct=trade.pnl_pct, review_id="discipline-3", sim_day=1, created_at=_now_iso())
        studies = generate_case_studies(decision, debate, trade, review, id_prefix="case-1")
        assert studies, "fixture must actually trigger at least one real mistake category"
        for study in studies:
            assert audit_model(study) == {}

    def test_success_case_studies_are_clean(self) -> None:
        decision = _decision()
        debate = _decision_debate()
        trade = _trade(pnl=50.0, pnl_pct=2.0)
        review = generate_discipline_review(decision, debate, hold_duration_minutes=trade.duration_minutes, pnl=trade.pnl, pnl_pct=trade.pnl_pct, review_id="discipline-4", sim_day=1, created_at=_now_iso())
        studies = generate_success_studies(decision, debate, trade, review, id_prefix="case-2")
        assert studies, "fixture must actually trigger at least one real success category"
        for study in studies:
            assert audit_model(study) == {}

    def test_ai_debate_is_clean(self) -> None:
        proposal = _proposal()
        debate = generate_debate(proposal)
        assert audit_model(debate) == {}

    def test_audit_model_actually_catches_a_planted_violation(self) -> None:
        # Proves the checker itself works end-to-end against a real
        # schema object, not just against bare strings — plant a real
        # violation into a real TradeDecision field and confirm it's
        # caught, so a silently-broken checker can't hide behind five
        # passing "is clean" tests above.
        decision = _decision().model_copy(update={"final_reasoning": "This is a guaranteed win, a sure thing."})
        violations = audit_model(decision)
        assert violations != {}
        assert any("sure thing" in hits for hits in violations.values())
