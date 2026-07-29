"""Covers app/company_dna.py — v0.7 Feature 43, Company DNA. Every trait
reads a real signal off TradeDecision/PaperTrade/CeoDecisionRecord history;
this file checks each formula against hand-computed expectations and
confirms the honest "not enough history" neutral default with zero records.
"""
from __future__ import annotations

from app.company_dna import compute_company_dna
from app.discipline import PATIENCE_TARGET_MINUTES
from app.schemas import AgentVote, CeoDecisionRecord, ConfidenceFactor, DecisionConfidence, PaperTrade, TradeDecision


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
