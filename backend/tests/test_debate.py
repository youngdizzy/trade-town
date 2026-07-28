"""Covers app/debate.py — v0.7 Feature 17, the AI Debate Room. Every
turn's substance must trace back to a real AnalystVote's own reasoning/
evidence; only the challenge/support framing is generated.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.debate import generate_debate
from app.schemas import AnalystVote, ConfidenceFactor, DecisionConfidence, TradeProposal


def _vote(role: str, agent_id: str, choice: str, reasoning: str = "test reasoning") -> AnalystVote:
    return AnalystVote(role=role, agentId=agent_id, choice=choice, reasoning=reasoning, evidence=["real evidence line"])  # type: ignore[arg-type]


def _six_votes(choices: dict[str, str]) -> list[AnalystVote]:
    role_to_agent = {"technical": "echo", "news": "scout", "macro": "nova", "risk": "sentinel", "sentiment": "pulse", "execution": "atlas"}
    return [_vote(role, agent, choices.get(role, "wait"), reasoning=f"{role} reasoning") for role, agent in role_to_agent.items()]


def _proposal(votes: list[AnalystVote], overall: str = "buy") -> TradeProposal:
    return TradeProposal(
        id="proposal-1",
        symbol="NEXA",
        category="stock",
        quantity=10.0,
        price=100.0,
        confidence=90.0,
        analystVotes=votes,
        overallRecommendation=overall,  # type: ignore[arg-type]
        researchSummary="test research summary",
        riskSummary="test risk summary",
        confidenceEngine=DecisionConfidence(score=80.0, tier="strong", summary="Strong Setup (80/100).", factors=[ConfidenceFactor(name="test", score=80.0, weight=1.0, detail="test")]),
        createdAt=datetime.now(timezone.utc).isoformat(),
        createdSimMinutes=0,
    )


class TestGenerateDebate:
    def test_one_opening_turn_per_analyst_carries_real_reasoning_and_evidence(self) -> None:
        votes = _six_votes({r: "buy" for r in ["technical", "news", "macro", "risk", "sentiment", "execution"]})
        proposal = _proposal(votes)
        debate = generate_debate(proposal)
        opening = [t for t in debate.turns if t.stance == "opening"]
        assert len(opening) == 6
        for turn, vote in zip(opening, votes):
            assert turn.agent_id == vote.agent_id
            assert vote.reasoning in turn.text
            assert vote.evidence[0] in turn.text

    def test_unanimous_agreement_produces_only_support_turns(self) -> None:
        votes = _six_votes({r: "buy" for r in ["technical", "news", "macro", "risk", "sentiment", "execution"]})
        proposal = _proposal(votes)
        debate = generate_debate(proposal)
        cross = [t for t in debate.turns if t.stance != "opening"]
        assert len(cross) == 6
        assert all(t.stance == "support" for t in cross)

    def test_disagreement_produces_a_challenge_turn(self) -> None:
        votes = _six_votes({"technical": "sell", "news": "buy", "macro": "buy", "risk": "buy", "sentiment": "buy", "execution": "buy"})
        proposal = _proposal(votes)
        debate = generate_debate(proposal)
        technical_cross = next(t for t in debate.turns if t.stance != "opening" and t.role == "technical")
        assert technical_cross.stance == "challenge"
        assert technical_cross.responding_to is not None

    def test_challenge_text_includes_the_challenger_own_real_reasoning(self) -> None:
        votes = _six_votes({"technical": "sell", "news": "buy", "macro": "buy", "risk": "buy", "sentiment": "buy", "execution": "buy"})
        proposal = _proposal(votes)
        debate = generate_debate(proposal)
        technical_cross = next(t for t in debate.turns if t.stance != "opening" and t.role == "technical")
        assert "technical reasoning" in technical_cross.text

    def test_final_recommendation_and_summary_reflect_the_real_proposal(self) -> None:
        votes = _six_votes({r: "sell" for r in ["technical", "news", "macro", "risk", "sentiment", "execution"]})
        proposal = _proposal(votes, overall="sell")
        debate = generate_debate(proposal)
        assert debate.final_recommendation == "sell"
        assert "SELL" in debate.final_summary
        assert proposal.symbol in debate.final_summary
        assert proposal.confidence_engine.summary in debate.final_summary

    def test_debate_links_back_to_its_proposal(self) -> None:
        votes = _six_votes({r: "buy" for r in ["technical", "news", "macro", "risk", "sentiment", "execution"]})
        proposal = _proposal(votes)
        debate = generate_debate(proposal)
        assert debate.proposal_id == proposal.id
        assert debate.symbol == proposal.symbol

    def test_regenerating_keeps_real_content_but_gets_a_new_id(self) -> None:
        votes = _six_votes({r: "buy" for r in ["technical", "news", "macro", "risk", "sentiment", "execution"]})
        proposal = _proposal(votes)
        first = generate_debate(proposal)
        second = generate_debate(proposal)
        assert first.id != second.id
        assert first.final_recommendation == second.final_recommendation == "buy"
