"""Covers app/company_dna.py — v0.7 Feature 43, Company DNA. Every trait
reads a real signal off TradeDecision/PaperTrade/CeoDecisionRecord history;
this file checks each formula against hand-computed expectations and
confirms the honest "not enough history" neutral default with zero records.
"""
from __future__ import annotations

from app.company_dna import LEGACY_DELTA_CAP, classify_identity, compute_company_dna, nudge_legacy
from app.discipline import PATIENCE_TARGET_MINUTES
from app.schemas import AgentVote, CeoDecisionRecord, CompanyDnaTrait, ConfidenceFactor, DecisionConfidence, PaperTrade, TradeDecision


def _now_iso() -> str:
    return "2026-01-01T00:00:00+00:00"


def _confidence_engine(tier: str = "strong", score: float = 80.0) -> DecisionConfidence:
    return DecisionConfidence(score=score, tier=tier, summary="test", factors=[ConfidenceFactor(name="Research Confidence", score=score, weight=0.15, detail="test")])  # type: ignore[arg-type]


def _decision(*, outcome: str = "trade", votes: list[AgentVote] | None = None, confidence_engine: DecisionConfidence | None = None, decision_id: str = "decision-p1") -> TradeDecision:
    return TradeDecision(
        id=decision_id,
        symbol="AAPL",
        outcome=outcome,  # type: ignore[arg-type]
        votes=votes if votes is not None else [AgentVote(agentId="echo", choice="buy", reason="x")],  # type: ignore[arg-type]
        researchSummary="x",
        technicalSummary="x",
        fundamentalSummary="x",
        riskSummary="x",
        supportingAgents=["echo"],  # type: ignore[arg-type]
        opposingAgents=[],
        confidence=80.0,
        finalReasoning="x",
        orderId="order-1" if outcome == "trade" else None,
        confidenceEngine=confidence_engine,
        createdAt=_now_iso(),
    )


def _trade(*, duration_minutes: int = 240, decision_id: str = "decision-p1") -> PaperTrade:
    return PaperTrade(
        id="t1",
        symbol="AAPL",
        side="buy",  # type: ignore[arg-type]
        quantity=10.0,
        entryPrice=100.0,
        exitPrice=101.0,
        pnl=10.0,
        pnlPct=1.0,
        durationMinutes=duration_minutes,
        confidence=80.0,
        reason="x",
        marketConditions="x",
        decisionId=decision_id,
        openedAt=_now_iso(),
        closedAt=_now_iso(),
    )


def _ceo_decision(*, agreed: bool = True) -> CeoDecisionRecord:
    return CeoDecisionRecord(
        id="cr1",
        proposalId="p1",
        symbol="AAPL",
        category="stock",  # type: ignore[arg-type]
        aiRecommendation="buy",  # type: ignore[arg-type]
        ceoDecision="buy" if agreed else "sell",  # type: ignore[arg-type]
        agreedWithAi=agreed,
        decisionId="decision-p1",
        outcome="correct",  # type: ignore[arg-type]
        createdAt=_now_iso(),
    )


class TestEmptyHistory:
    def test_every_trait_reads_neutral_with_no_history(self) -> None:
        dna = compute_company_dna([], [], [])
        assert all(t.score == 50.0 for t in dna.traits)
        assert dna.sample_size == 0
        assert "not enough history" in dna.summary.lower()


class TestRiskAppetite:
    def test_all_strong_confidence_trades_score_low_appetite(self) -> None:
        dna = compute_company_dna([_decision(confidence_engine=_confidence_engine(tier="strong"))], [], [])
        risk = next(t for t in dna.traits if t.id == "risk_appetite")
        assert risk.score == 0.0

    def test_all_moderate_confidence_trades_score_high_appetite(self) -> None:
        dna = compute_company_dna([_decision(confidence_engine=_confidence_engine(tier="moderate"))], [], [])
        risk = next(t for t in dna.traits if t.id == "risk_appetite")
        assert risk.score == 100.0

    def test_no_trade_outcomes_are_excluded(self) -> None:
        dna = compute_company_dna([_decision(outcome="no_trade", confidence_engine=_confidence_engine(tier="moderate"))], [], [])
        risk = next(t for t in dna.traits if t.id == "risk_appetite")
        assert risk.score == 50.0


class TestPatience:
    def test_average_hold_at_target_scores_100(self) -> None:
        dna = compute_company_dna([], [_trade(duration_minutes=PATIENCE_TARGET_MINUTES)], [])
        patience = next(t for t in dna.traits if t.id == "patience")
        assert patience.score == 100.0

    def test_average_hold_below_target_scores_proportionally(self) -> None:
        dna = compute_company_dna([], [_trade(duration_minutes=PATIENCE_TARGET_MINUTES // 2)], [])
        patience = next(t for t in dna.traits if t.id == "patience")
        assert patience.score == 50.0

    def test_average_hold_beyond_target_caps_at_100(self) -> None:
        dna = compute_company_dna([], [_trade(duration_minutes=PATIENCE_TARGET_MINUTES * 3)], [])
        patience = next(t for t in dna.traits if t.id == "patience")
        assert patience.score == 100.0


class TestContrarianTendency:
    def test_all_overrides_score_100(self) -> None:
        dna = compute_company_dna([], [], [_ceo_decision(agreed=False)])
        trait = next(t for t in dna.traits if t.id == "contrarian_tendency")
        assert trait.score == 100.0

    def test_all_agreements_score_0(self) -> None:
        dna = compute_company_dna([], [], [_ceo_decision(agreed=True)])
        trait = next(t for t in dna.traits if t.id == "contrarian_tendency")
        assert trait.score == 0.0


class TestResearchRigor:
    def test_averages_the_real_confidence_engine_score(self) -> None:
        dna = compute_company_dna([_decision(confidence_engine=_confidence_engine(score=90.0)), _decision(confidence_engine=_confidence_engine(score=70.0))], [], [])
        trait = next(t for t in dna.traits if t.id == "research_rigor")
        assert trait.score == 80.0

    def test_decisions_without_a_confidence_engine_are_excluded(self) -> None:
        dna = compute_company_dna([_decision(confidence_engine=None)], [], [])
        trait = next(t for t in dna.traits if t.id == "research_rigor")
        assert trait.score == 50.0


class TestCollaborationStyle:
    def test_all_unanimous_votes_score_0(self) -> None:
        dna = compute_company_dna([_decision(votes=[AgentVote(agentId="echo", choice="buy", reason="x")])], [], [])  # type: ignore[arg-type]
        trait = next(t for t in dna.traits if t.id == "collaboration_style")
        assert trait.score == 0.0

    def test_diverse_votes_score_100(self) -> None:
        votes = [AgentVote(agentId="echo", choice="buy", reason="x"), AgentVote(agentId="scout", choice="sell", reason="x")]  # type: ignore[arg-type]
        dna = compute_company_dna([_decision(votes=votes)], [], [])
        trait = next(t for t in dna.traits if t.id == "collaboration_style")
        assert trait.score == 100.0


class TestSummaryAndSampleSize:
    def test_summary_names_the_real_highest_and_lowest_traits(self) -> None:
        dna = compute_company_dna([_decision(confidence_engine=_confidence_engine(tier="moderate"))], [], [_ceo_decision(agreed=True)])
        assert any(t.name in dna.summary for t in dna.traits)

    def test_sample_size_is_the_largest_contributing_count(self) -> None:
        decisions = [_decision(confidence_engine=_confidence_engine()), _decision(confidence_engine=_confidence_engine(), decision_id="decision-p2")]
        dna = compute_company_dna(decisions, [], [])
        assert dna.sample_size == 2


# v0.7 Feature 48 — Company Identity: a pure, deterministic label read
# off the five real trait scores.
class TestClassifyIdentity:
    def _traits(self, **scores: float) -> list[CompanyDnaTrait]:
        defaults = {"risk_appetite": 50.0, "patience": 50.0, "contrarian_tendency": 50.0, "research_rigor": 50.0, "collaboration_style": 50.0}
        defaults.update(scores)
        return [CompanyDnaTrait(id=tid, name=tid, score=score, detail="test") for tid, score in defaults.items()]

    def test_zero_sample_size_is_not_yet_established(self) -> None:
        assert classify_identity(self._traits(), 0) == "Not Yet Established"

    def test_low_risk_high_patience_is_ultra_conservative(self) -> None:
        assert classify_identity(self._traits(risk_appetite=20.0, patience=65.0), 5) == "Ultra Conservative"

    def test_high_research_rigor_is_research_driven(self) -> None:
        assert classify_identity(self._traits(risk_appetite=50.0, research_rigor=80.0), 5) == "Research Driven"

    def test_high_patience_moderate_risk_is_highly_disciplined(self) -> None:
        assert classify_identity(self._traits(risk_appetite=35.0, patience=75.0), 5) == "Highly Disciplined"

    def test_high_contrarian_tendency_is_independent_thinker(self) -> None:
        assert classify_identity(self._traits(contrarian_tendency=70.0), 5) == "Independent Thinker"

    def test_high_collaboration_is_collaborative_culture(self) -> None:
        assert classify_identity(self._traits(collaboration_style=75.0), 5) == "Collaborative Culture"

    def test_high_risk_appetite_alone_is_aggressive_risk_taker(self) -> None:
        assert classify_identity(self._traits(risk_appetite=70.0), 5) == "Aggressive Risk-Taker"

    def test_all_neutral_scores_is_balanced_operator(self) -> None:
        assert classify_identity(self._traits(), 5) == "Balanced Operator"


# v0.7 Feature 48 — Legacy: a small, permanent, capped per-trait delta.
class TestNudgeLegacy:
    def test_adds_a_real_delta(self) -> None:
        deltas = nudge_legacy({}, "research_rigor", 2.0)
        assert deltas["research_rigor"] == 2.0

    def test_accumulates_across_multiple_nudges(self) -> None:
        deltas = nudge_legacy({}, "research_rigor", 2.0)
        deltas = nudge_legacy(deltas, "research_rigor", 2.0)
        assert deltas["research_rigor"] == 4.0

    def test_caps_at_the_max_in_either_direction(self) -> None:
        deltas: dict[str, float] = {}
        for _ in range(20):
            deltas = nudge_legacy(deltas, "risk_appetite", -5.0)
        assert deltas["risk_appetite"] == -LEGACY_DELTA_CAP

    def test_does_not_mutate_the_input_dict(self) -> None:
        original = {"research_rigor": 1.0}
        nudge_legacy(original, "research_rigor", 2.0)
        assert original == {"research_rigor": 1.0}


class TestComputeCompanyDnaWithLegacy:
    def test_legacy_delta_is_added_on_top_of_the_base_score(self) -> None:
        without = compute_company_dna([_decision(confidence_engine=_confidence_engine())], [], [])
        with_legacy = compute_company_dna([_decision(confidence_engine=_confidence_engine())], [], [], legacy_deltas={"research_rigor": 5.0})
        base = next(t for t in without.traits if t.id == "research_rigor").score
        nudged = next(t for t in with_legacy.traits if t.id == "research_rigor").score
        assert nudged == base + 5.0

    def test_legacy_delta_clamps_to_the_valid_range(self) -> None:
        dna = compute_company_dna([_decision(confidence_engine=_confidence_engine(tier="strong", score=99.0))], [], [], legacy_deltas={"research_rigor": 50.0})
        trait = next(t for t in dna.traits if t.id == "research_rigor")
        assert trait.score == 100.0

    def test_identity_is_included_and_deterministic(self) -> None:
        dna = compute_company_dna([_decision(confidence_engine=_confidence_engine(tier="moderate"))], [], [_ceo_decision(agreed=True)])
        assert dna.identity == classify_identity(dna.traits, dna.sample_size)
