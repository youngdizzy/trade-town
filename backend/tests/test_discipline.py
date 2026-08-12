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
    compute_loss_win_classification,
    generate_discipline_review,
    overridden_dissent,
    record_review,
    tier_for_score,
)
from app.schemas import (
    AgentVote,
    CaseStudy,
    ConfidenceFactor,
    DisciplineReview,
    PostDecisionReview,
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


def _review(*, tier: str, outcome: str, review_id: str = "discipline-1") -> DisciplineReview:
    return DisciplineReview(
        id=review_id,
        decisionId=f"decision-{review_id}",
        symbol="NEXA",
        score=90.0 if tier == "exemplary" else 75.0 if tier == "sound" else 60.0 if tier == "adequate" else 45.0 if tier == "weak" else 20.0,
        tier=tier,  # type: ignore[arg-type]
        summary="test summary",
        postDecisionReview=PostDecisionReview(),
        outcome=outcome,  # type: ignore[arg-type]
        tradePnlPct=1.0 if outcome == "win" else -1.0,
        holdDurationMinutes=100,
        simDay=1,
        createdAt=_now_iso(),
    )


def _case_study(*, category: str, study_id: str = "case-1") -> CaseStudy:
    return CaseStudy(
        id=study_id,
        category=category,  # type: ignore[arg-type]
        title="Test Case Study",
        symbol="NEXA",
        decisionId=f"decision-{study_id}",
        background="test background",
        decisionProcess="test decision process",
        missedInformation="test missed info",
        lessonsLearned="test lessons",
        recommendedImprovements="test improvements",
        tradePnlPct=1.0,
        simDay=1,
        createdAt=_now_iso(),
    )


class TestComputeLossWinClassification:
    def test_empty_input_reports_zero_and_none_never_a_fabricated_rate(self) -> None:
        result = compute_loss_win_classification([], [])
        assert result.total_reviewed == 0
        assert result.win_count == 0
        assert result.loss_count == 0
        assert result.win_rate_pct is None
        assert result.aligned_count == 0
        assert result.misaligned_count == 0
        assert result.most_common_mistake_category is None
        assert result.most_common_success_category is None

    def test_win_rate_and_counts_are_correct(self) -> None:
        reviews = [
            _review(tier="sound", outcome="win", review_id="d1"),
            _review(tier="sound", outcome="win", review_id="d2"),
            _review(tier="weak", outcome="loss", review_id="d3"),
            _review(tier="weak", outcome="loss", review_id="d4"),
        ]
        result = compute_loss_win_classification(reviews, [])
        assert result.total_reviewed == 4
        assert result.win_count == 2
        assert result.loss_count == 2
        assert result.win_rate_pct == 50.0

    def test_good_tier_win_and_poor_tier_loss_are_aligned(self) -> None:
        reviews = [
            _review(tier="exemplary", outcome="win", review_id="d1"),
            _review(tier="sound", outcome="win", review_id="d2"),
            _review(tier="weak", outcome="loss", review_id="d3"),
            _review(tier="reckless", outcome="loss", review_id="d4"),
        ]
        result = compute_loss_win_classification(reviews, [])
        assert result.aligned_count == 4
        assert result.misaligned_count == 0
        assert result.unlucky_loss_count == 0
        assert result.lucky_win_count == 0

    def test_good_tier_loss_is_an_unlucky_loss_not_a_process_failure(self) -> None:
        reviews = [_review(tier="sound", outcome="loss", review_id="d1")]
        result = compute_loss_win_classification(reviews, [])
        assert result.unlucky_loss_count == 1
        assert result.lucky_win_count == 0
        assert result.misaligned_count == 1
        assert result.aligned_count == 0

    def test_poor_tier_win_is_a_lucky_win_not_a_validation(self) -> None:
        reviews = [_review(tier="weak", outcome="win", review_id="d1")]
        result = compute_loss_win_classification(reviews, [])
        assert result.lucky_win_count == 1
        assert result.unlucky_loss_count == 0
        assert result.misaligned_count == 1
        assert result.aligned_count == 0

    def test_adequate_tier_counts_toward_neither_aligned_nor_misaligned(self) -> None:
        reviews = [
            _review(tier="adequate", outcome="win", review_id="d1"),
            _review(tier="adequate", outcome="loss", review_id="d2"),
        ]
        result = compute_loss_win_classification(reviews, [])
        assert result.aligned_count == 0
        assert result.misaligned_count == 0
        assert result.total_reviewed == 2

    def test_by_tier_breakdown_covers_all_five_tiers_and_sums_correctly(self) -> None:
        reviews = [
            _review(tier="exemplary", outcome="win", review_id="d1"),
            _review(tier="sound", outcome="loss", review_id="d2"),
            _review(tier="adequate", outcome="win", review_id="d3"),
            _review(tier="weak", outcome="win", review_id="d4"),
            _review(tier="reckless", outcome="loss", review_id="d5"),
        ]
        result = compute_loss_win_classification(reviews, [])
        assert {row.tier for row in result.by_tier} == {"exemplary", "sound", "adequate", "weak", "reckless"}
        exemplary_row = next(row for row in result.by_tier if row.tier == "exemplary")
        assert exemplary_row.win_count == 1
        assert exemplary_row.loss_count == 0
        total_from_tiers = sum(row.win_count + row.loss_count for row in result.by_tier)
        assert total_from_tiers == result.total_reviewed

    def test_most_common_mistake_and_success_category_are_derived_separately(self) -> None:
        case_studies = [
            _case_study(category="overconfidence", study_id="c1"),
            _case_study(category="overconfidence", study_id="c2"),
            _case_study(category="acted_too_quickly", study_id="c3"),
            _case_study(category="disciplined_process", study_id="c4"),
            _case_study(category="disciplined_process", study_id="c5"),
            _case_study(category="disciplined_process", study_id="c6"),
            _case_study(category="patient_execution", study_id="c7"),
        ]
        result = compute_loss_win_classification([], case_studies)
        assert result.most_common_mistake_category == "overconfidence"
        assert result.most_common_mistake_count == 2
        assert result.most_common_success_category == "disciplined_process"
        assert result.most_common_success_count == 3

    def test_no_case_studies_reports_none_for_both_categories_never_fabricated(self) -> None:
        result = compute_loss_win_classification([_review(tier="sound", outcome="win")], [])
        assert result.most_common_mistake_category is None
        assert result.most_common_success_category is None
