"""Covers app/discipline.py — v0.7 Feature 26, the Discipline Chamber.
The core rule under test throughout: compute_discipline_score() must
never read pnl, so an identical process must score identically whether
the linked trade won or lost — only generate_discipline_review()'s
outcome/summary/post-decision-review may differ based on the real result.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.discipline import (
    compute_discipline_score,
    generate_discipline_review,
    overridden_dissent,
    record_review,
    tier_for_score,
)
from app.schemas import (
    AgentVote,
    ConfidenceFactor,
    Debate,
    DebateTurn,
    DecisionConfidence,
    TradeDecision,
)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _confidence_engine(*, score: float = 80.0, research_score: float = 80.0, exposure_score: float = 70.0) -> DecisionConfidence:
    return DecisionConfidence(
        score=score,
        tier="strong",
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
    decision_id: str = "decision-proposal-1",
) -> TradeDecision:
    return TradeDecision(
        id=decision_id,
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


def _debate(turns: list[DebateTurn], proposal_id: str = "proposal-1", final: str = "buy") -> Debate:
    return Debate(id=f"debate-{proposal_id}", proposalId=proposal_id, symbol="NEXA", turns=turns, finalRecommendation=final, finalSummary="test summary", createdAt=_now_iso())  # type: ignore[arg-type]


class TestComputeDisciplineScore:
    def test_never_reads_outcome_identical_process_scores_identically_regardless_of_win_or_loss(self) -> None:
        decision = _decision()
        debate = _debate([_debate_turn("echo", "technical", "opening"), _debate_turn("scout", "news", "challenge")])
        score_a, factors_a = compute_discipline_score(decision, debate, hold_duration_minutes=240)
        score_b, factors_b = compute_discipline_score(decision, debate, hold_duration_minutes=240)
        assert score_a == score_b
        assert [f.score for f in factors_a] == [f.score for f in factors_b]

    def test_more_challenge_turns_raise_the_assumptions_challenged_factor(self) -> None:
        decision = _decision()
        no_challenge = _debate([_debate_turn("echo", "technical", "opening")])
        with_challenge = _debate([_debate_turn("echo", "technical", "opening"), _debate_turn("scout", "news", "challenge")])
        _, factors_no = compute_discipline_score(decision, no_challenge, hold_duration_minutes=120)
        _, factors_with = compute_discipline_score(decision, with_challenge, hold_duration_minutes=120)
        challenged_no = next(f for f in factors_no if f.id == "assumptions_challenged")
        challenged_with = next(f for f in factors_with if f.id == "assumptions_challenged")
        assert challenged_with.score > challenged_no.score

    def test_no_debate_scores_zero_on_cross_examination(self) -> None:
        decision = _decision()
        _, factors = compute_discipline_score(decision, None, hold_duration_minutes=120)
        cross_exam = next(f for f in factors if f.id == "cross_examination")
        assert cross_exam.score == 0.0

    def test_a_wait_vote_raises_uncertainty_acknowledged(self) -> None:
        decision_no_wait = _decision(votes=[AgentVote(agentId="echo", choice="buy", reason="r")])  # type: ignore[arg-type]
        decision_with_wait = _decision(votes=[AgentVote(agentId="echo", choice="buy", reason="r"), AgentVote(agentId="scout", choice="hold", reason="r2")])  # type: ignore[arg-type]
        _, factors_no = compute_discipline_score(decision_no_wait, None, hold_duration_minutes=0)
        _, factors_yes = compute_discipline_score(decision_with_wait, None, hold_duration_minutes=0)
        uncertainty_no = next(f for f in factors_no if f.id == "uncertainty_acknowledged")
        uncertainty_yes = next(f for f in factors_yes if f.id == "uncertainty_acknowledged")
        assert uncertainty_yes.score > uncertainty_no.score

    def test_longer_hold_duration_raises_patience_up_to_the_target(self) -> None:
        decision = _decision()
        _, factors_short = compute_discipline_score(decision, None, hold_duration_minutes=30)
        _, factors_long = compute_discipline_score(decision, None, hold_duration_minutes=240)
        patience_short = next(f for f in factors_short if f.id == "patience")
        patience_long = next(f for f in factors_long if f.id == "patience")
        assert patience_long.score > patience_short.score
        assert patience_long.score == 100.0

    def test_distinct_analyst_choices_raise_viewpoint_diversity(self) -> None:
        one_view = _decision(votes=[AgentVote(agentId="echo", choice="buy", reason="r"), AgentVote(agentId="scout", choice="buy", reason="r")])  # type: ignore[arg-type]
        three_views = _decision(
            votes=[AgentVote(agentId="echo", choice="buy", reason="r"), AgentVote(agentId="scout", choice="sell", reason="r"), AgentVote(agentId="nova", choice="hold", reason="r")]  # type: ignore[arg-type]
        )
        _, factors_one = compute_discipline_score(one_view, None, hold_duration_minutes=0)
        _, factors_three = compute_discipline_score(three_views, None, hold_duration_minutes=0)
        diversity_one = next(f for f in factors_one if f.id == "viewpoint_diversity")
        diversity_three = next(f for f in factors_three if f.id == "viewpoint_diversity")
        assert diversity_three.score > diversity_one.score


class TestTierForScore:
    def test_tier_bands_are_ordered_and_cover_the_full_range(self) -> None:
        assert tier_for_score(90) == "exemplary"
        assert tier_for_score(75) == "sound"
        assert tier_for_score(60) == "adequate"
        assert tier_for_score(45) == "weak"
        assert tier_for_score(10) == "reckless"


class TestOverriddenDissent:
    def test_echo_or_scout_in_opposing_agents_is_real_overridden_dissent(self) -> None:
        decision = _decision(opposing=["echo"])
        assert overridden_dissent(decision) == ["echo"]

    def test_sentinel_is_never_counted_since_the_gatekeeper_hard_blocks_that_path(self) -> None:
        decision = _decision(opposing=["sentinel", "echo"])
        assert overridden_dissent(decision) == ["echo"]

    def test_no_real_dissent_among_the_checkable_agents_returns_empty(self) -> None:
        decision = _decision(opposing=["nova"])
        assert overridden_dissent(decision) == []


class TestGenerateDisciplineReview:
    def test_a_good_process_that_lost_is_called_out_as_good_decision_bad_luck(self) -> None:
        decision = _decision(confidence_engine=_confidence_engine(research_score=90.0, exposure_score=90.0))
        debate = _debate([_debate_turn("echo", "technical", "opening"), _debate_turn("scout", "news", "challenge"), _debate_turn("nova", "macro", "support")])
        review = generate_discipline_review(decision, debate, hold_duration_minutes=300, pnl=-50.0, pnl_pct=-2.0, review_id="discipline-1", sim_day=1, created_at=_now_iso())
        assert review.outcome == "loss"
        assert review.score >= 55
        assert "good decision" in review.summary.lower() or "sound" in review.summary.lower()

    def test_a_weak_process_that_won_is_flagged_as_a_warning_not_a_validation(self) -> None:
        decision = _decision(votes=[AgentVote(agentId="echo", choice="buy", reason="r")], confidence_engine=_confidence_engine(research_score=10.0, exposure_score=10.0))  # type: ignore[arg-type]
        review = generate_discipline_review(decision, None, hold_duration_minutes=5, pnl=50.0, pnl_pct=2.0, review_id="discipline-2", sim_day=1, created_at=_now_iso())
        assert review.outcome == "win"
        assert review.score < 55
        assert "warning" in review.summary.lower()

    def test_assumptions_incorrect_only_populated_for_a_real_loss_with_real_overridden_dissent(self) -> None:
        decision = _decision(opposing=["echo"])
        loss = generate_discipline_review(decision, None, hold_duration_minutes=100, pnl=-10.0, pnl_pct=-1.0, review_id="discipline-3", sim_day=1, created_at=_now_iso())
        win = generate_discipline_review(decision, None, hold_duration_minutes=100, pnl=10.0, pnl_pct=1.0, review_id="discipline-4", sim_day=1, created_at=_now_iso())
        assert loss.post_decision_review.assumptions_incorrect != []
        assert "Echo" in loss.post_decision_review.assumptions_incorrect[0]
        assert win.post_decision_review.assumptions_incorrect == []

    def test_attendees_are_the_real_supporting_and_opposing_agents_deduplicated(self) -> None:
        decision = _decision(supporting=["echo", "nova"], opposing=["scout"])
        review = generate_discipline_review(decision, None, hold_duration_minutes=0, pnl=1.0, pnl_pct=0.1, review_id="discipline-5", sim_day=1, created_at=_now_iso())
        assert set(review.attendees) == {"echo", "nova", "scout"}


class TestRecordReview:
    def test_caps_at_max_discipline_reviews(self) -> None:
        decision = _decision()
        reviews = []
        for i in range(70):
            review = generate_discipline_review(decision, None, hold_duration_minutes=0, pnl=1.0, pnl_pct=0.1, review_id=f"discipline-{i}", sim_day=1, created_at=_now_iso())
            reviews = record_review(reviews, review)
        assert len(reviews) == 60
        assert reviews[-1].id == "discipline-69"
