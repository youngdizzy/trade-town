"""Covers app/reasoning_lab.py — v0.7 Feature 29, the Reasoning Lab.

Like test_discipline.py, this module never gives generate_challenge()
any pnl/outcome to read — there is no parameter for it — so these tests
focus on: which real category a given real Debate/TradeDecision shape
maps to, that harder categories stay locked below their required
Reasoning Level, and that Level/history bookkeeping behaves.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.reasoning_lab import (
    MAX_REASONING_CHALLENGES,
    compute_reasoning_lab_state,
    generate_challenge,
    record_challenge,
)
from app.schemas import (
    AgentVote,
    ConfidenceFactor,
    Debate,
    DebateTurn,
    DecisionConfidence,
    ReasoningChallenge,
    TradeDecision,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _confidence_engine(*, score: float = 80.0, research_score: float = 80.0) -> DecisionConfidence:
    return DecisionConfidence(
        score=score,
        tier="strong",
        summary="test summary",
        factors=[
            ConfidenceFactor(name="Research Confidence", score=research_score, weight=0.15, detail="research detail"),
            ConfidenceFactor(name="Portfolio Exposure", score=70.0, weight=0.05, detail="exposure detail"),
        ],
    )


def _decision(
    *,
    votes: list[AgentVote] | None = None,
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
        supportingAgents=["echo"],  # type: ignore[arg-type]
        opposingAgents=opposing or [],  # type: ignore[arg-type]
        confidence=80.0,
        finalReasoning="CEO approved BUY on NEXA.",
        orderId="pos-1",
        confidenceEngine=confidence_engine or _confidence_engine(),
        createdAt=_now_iso(),
    )


def _turn(agent_id: str, role: str, stance: str, *, text: str = "reasoning with evidence (source: research memo)") -> DebateTurn:
    return DebateTurn(agentId=agent_id, role=role, stance=stance, text=text)  # type: ignore[arg-type]


def _debate(turns: list[DebateTurn]) -> Debate:
    return Debate(id="debate-proposal-1", proposalId="proposal-1", symbol="NEXA", turns=turns, finalRecommendation="buy", finalSummary="test summary", createdAt=_now_iso())  # type: ignore[arg-type]


def _challenge(decision: TradeDecision, debate: Debate | None, *, unlocked_level: int = 1) -> ReasoningChallenge:
    return generate_challenge(decision, debate, challenge_id="reasoning-test", unlocked_level=unlocked_level, sim_day=1, created_at=_now_iso())


class TestComputeReasoningLabState:
    def test_zero_completed_is_level_one_foundations(self) -> None:
        state = compute_reasoning_lab_state(0)
        assert state.level == 1
        assert state.level_label == "Foundations"
        assert state.completed_challenge_count == 0

    def test_crossing_five_advances_to_applied_reasoning(self) -> None:
        assert compute_reasoning_lab_state(4).level == 1
        assert compute_reasoning_lab_state(5).level == 2
        assert compute_reasoning_lab_state(5).level_label == "Applied Reasoning"

    def test_crossing_twelve_advances_to_advanced_reasoning(self) -> None:
        assert compute_reasoning_lab_state(11).level == 2
        assert compute_reasoning_lab_state(12).level == 3
        assert compute_reasoning_lab_state(12).level_label == "Advanced Reasoning"


class TestDetectCategory:
    def test_no_debate_no_signal_falls_back_to_improving_communication(self) -> None:
        decision = _decision()
        challenge = _challenge(decision, None, unlocked_level=1)
        assert challenge.category == "improving_communication"

    def test_two_distinct_vote_choices_evaluates_multiple_hypotheses(self) -> None:
        decision = _decision(votes=[AgentVote(agentId="echo", choice="buy", reason="r"), AgentVote(agentId="scout", choice="sell", reason="r2")])  # type: ignore[arg-type]
        challenge = _challenge(decision, None, unlocked_level=1)
        assert challenge.category == "evaluating_multiple_hypotheses"

    def test_low_research_confidence_finds_missing_information(self) -> None:
        decision = _decision(confidence_engine=_confidence_engine(research_score=30.0))
        challenge = _challenge(decision, None, unlocked_level=1)
        assert challenge.category == "finding_missing_information"

    def test_weak_evidence_locked_below_level_two_falls_back(self) -> None:
        decision = _decision()
        debate = _debate([_turn("echo", "technical", "opening", text="no real backing here")])
        challenge = _challenge(decision, debate, unlocked_level=1)
        assert challenge.category != "identifying_weak_evidence"

    def test_weak_evidence_detected_once_level_two_unlocked(self) -> None:
        decision = _decision()
        debate = _debate([_turn("echo", "technical", "opening", text="no real backing here")])
        challenge = _challenge(decision, debate, unlocked_level=2)
        assert challenge.category == "identifying_weak_evidence"

    def test_challenge_turns_locked_below_level_two_falls_back(self) -> None:
        decision = _decision()
        debate = _debate([_turn("echo", "technical", "opening"), _turn("scout", "news", "challenge")])
        challenge = _challenge(decision, debate, unlocked_level=1)
        assert challenge.category != "separating_facts_from_assumptions"

    def test_challenge_turns_detected_once_level_two_unlocked(self) -> None:
        decision = _decision()
        debate = _debate([_turn("echo", "technical", "opening"), _turn("scout", "news", "challenge")])
        challenge = _challenge(decision, debate, unlocked_level=2)
        assert challenge.category == "separating_facts_from_assumptions"

    def test_three_distinct_choices_locked_below_level_three(self) -> None:
        decision = _decision(
            votes=[
                AgentVote(agentId="echo", choice="buy", reason="r1"),  # type: ignore[arg-type]
                AgentVote(agentId="scout", choice="sell", reason="r2"),  # type: ignore[arg-type]
                AgentVote(agentId="nova", choice="hold", reason="r3"),  # type: ignore[arg-type]
            ]
        )
        challenge = _challenge(decision, None, unlocked_level=2)
        assert challenge.category != "recognizing_contradictory_data"

    def test_three_distinct_choices_detected_once_level_three_unlocked(self) -> None:
        decision = _decision(
            votes=[
                AgentVote(agentId="echo", choice="buy", reason="r1"),  # type: ignore[arg-type]
                AgentVote(agentId="scout", choice="sell", reason="r2"),  # type: ignore[arg-type]
                AgentVote(agentId="nova", choice="hold", reason="r3"),  # type: ignore[arg-type]
            ]
        )
        challenge = _challenge(decision, None, unlocked_level=3)
        assert challenge.category == "recognizing_contradictory_data"

    def test_two_distinct_support_agents_compares_competing_explanations_once_unlocked(self) -> None:
        decision = _decision()
        debate = _debate([_turn("echo", "technical", "support"), _turn("scout", "news", "support")])
        challenge = _challenge(decision, debate, unlocked_level=3)
        assert challenge.category == "comparing_competing_explanations"

    def test_priority_favors_more_specific_signal_over_missing_information(self) -> None:
        # Both a real challenge-turn signal and low research confidence are
        # present; separating_facts_from_assumptions is checked first.
        decision = _decision(confidence_engine=_confidence_engine(research_score=10.0))
        debate = _debate([_turn("echo", "technical", "opening"), _turn("scout", "news", "challenge")])
        challenge = _challenge(decision, debate, unlocked_level=3)
        assert challenge.category == "separating_facts_from_assumptions"


class TestSolutionAndContributions:
    def test_contributions_mirror_real_debate_turns(self) -> None:
        decision = _decision()
        debate = _debate([_turn("echo", "technical", "opening", text="turn one"), _turn("scout", "news", "challenge", text="turn two")])
        challenge = _challenge(decision, debate)
        assert [c.contribution for c in challenge.contributions] == ["turn one", "turn two"]
        assert [c.agent_id for c in challenge.contributions] == ["echo", "scout"]

    def test_no_debate_means_no_contributions(self) -> None:
        decision = _decision()
        challenge = _challenge(decision, None)
        assert challenge.contributions == []

    def test_solution_confidence_matches_confidence_engine_score(self) -> None:
        decision = _decision(confidence_engine=_confidence_engine(score=91.0))
        challenge = _challenge(decision, None)
        assert challenge.solution.confidence == 91.0

    def test_solution_assumptions_reflect_real_opposing_vote_reasons(self) -> None:
        decision = _decision(
            votes=[AgentVote(agentId="echo", choice="buy", reason="momentum confirmed"), AgentVote(agentId="scout", choice="sell", reason="headline risk")],  # type: ignore[arg-type]
            opposing=["scout"],
        )
        challenge = _challenge(decision, None)
        assert challenge.solution.assumptions == ["headline risk"]

    def test_no_opposing_votes_gives_an_honest_fallback_assumption(self) -> None:
        decision = _decision()
        challenge = _challenge(decision, None)
        assert "No analyst dissented" in challenge.solution.assumptions[0]

    def test_solution_why_reasonable_is_the_real_final_reasoning(self) -> None:
        decision = _decision()
        challenge = _challenge(decision, None)
        assert challenge.solution.why_reasonable == decision.final_reasoning


class TestRecordChallenge:
    def test_caps_at_max_reasoning_challenges(self) -> None:
        decision = _decision()
        challenges: list[ReasoningChallenge] = []
        for i in range(MAX_REASONING_CHALLENGES + 10):
            challenge = generate_challenge(decision, None, challenge_id=f"reasoning-{i}", unlocked_level=1, sim_day=1, created_at=_now_iso())
            challenges = record_challenge(challenges, challenge)
        assert len(challenges) == MAX_REASONING_CHALLENGES
        assert challenges[-1].id == f"reasoning-{MAX_REASONING_CHALLENGES + 9}"
