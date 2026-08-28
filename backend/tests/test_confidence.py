"""Covers app/confidence.py — v0.7 Feature 15, the Decision Confidence
Engine. Every factor must trace back to a real AnalystVote, the real
research confidence, real portfolio exposure, or (CEO directive
"Professional Quant Trading Core," Phase B) real higher-timeframe trend
confirmation — never an invented number for a factor this codebase has
no real data for (support/resistance, liquidity, historical setups).
"""
from __future__ import annotations

from app.confidence import compute_confidence, tier_for_score
from app.portfolio import default_portfolio
from app.schemas import AnalystVote, MultiTimeframeConfirmation, PaperPosition, RiskLimits


def _vote(role: str, agent_id: str, choice: str) -> AnalystVote:
    return AnalystVote(role=role, agentId=agent_id, choice=choice, reasoning="test reasoning", evidence=["test evidence"])  # type: ignore[arg-type]


def _six_votes(choices: dict[str, str]) -> list[AnalystVote]:
    role_to_agent = {"technical": "echo", "news": "scout", "macro": "nova", "risk": "sentinel", "sentiment": "pulse", "execution": "atlas"}
    return [_vote(role, agent, choices.get(role, "wait")) for role, agent in role_to_agent.items()]


def _mtf(agreement_score: float = 50.0) -> MultiTimeframeConfirmation:
    return MultiTimeframeConfirmation(readings=[], agreementScore=agreement_score, summary="test summary")


class TestTierForScore:
    def test_boundaries(self) -> None:
        assert tier_for_score(100) == "elite"
        assert tier_for_score(95) == "elite"
        assert tier_for_score(94.9) == "strong"
        assert tier_for_score(85) == "strong"
        assert tier_for_score(84.9) == "good"
        assert tier_for_score(70) == "good"
        assert tier_for_score(69.9) == "moderate"
        assert tier_for_score(55) == "moderate"
        assert tier_for_score(54.9) == "weak"
        assert tier_for_score(40) == "weak"
        assert tier_for_score(39.9) == "poor"
        assert tier_for_score(0) == "poor"


class TestComputeConfidence:
    def test_unanimous_agreement_clean_risk_scores_high(self) -> None:
        votes = _six_votes({r: "buy" for r in ["technical", "news", "macro", "risk", "sentiment", "execution"]})
        result = compute_confidence(votes, "buy", research_confidence=95.0, portfolio=default_portfolio(), risk_limits=RiskLimits(), multi_timeframe=_mtf(100.0))
        assert result.score >= 85
        assert result.tier in ("elite", "strong")
        assert len(result.factors) == 7
        assert all(0 <= f.score <= 100 for f in result.factors)

    def test_disagreement_and_risk_warning_scores_low(self) -> None:
        votes = _six_votes({"technical": "sell", "news": "sell", "macro": "wait", "risk": "wait", "sentiment": "sell", "execution": "wait"})
        result = compute_confidence(votes, "buy", research_confidence=40.0, portfolio=default_portfolio(), risk_limits=RiskLimits(), multi_timeframe=_mtf(0.0))
        assert result.score < 55
        assert result.tier in ("weak", "poor", "moderate")

    def test_weights_sum_to_one(self) -> None:
        votes = _six_votes({r: "buy" for r in ["technical", "news", "macro", "risk", "sentiment", "execution"]})
        result = compute_confidence(votes, "buy", research_confidence=100.0, portfolio=default_portfolio(), risk_limits=RiskLimits(), multi_timeframe=_mtf())
        assert abs(sum(f.weight for f in result.factors) - 1.0) < 1e-9

    def test_high_exposure_lowers_score(self) -> None:
        votes = _six_votes({r: "buy" for r in ["technical", "news", "macro", "risk", "sentiment", "execution"]})
        limits = RiskLimits(maxOpenPositions=2)
        crowded = default_portfolio().model_copy(
            update={
                "positions": [
                    PaperPosition(
                        id=f"pos-{i}",
                        symbol="AAPL",
                        side="buy",
                        quantity=1.0,
                        entryPrice=100.0,
                        currentPrice=100.0,
                        unrealizedPnl=0.0,
                        unrealizedPnlPct=0.0,
                        openedBy="atlas",
                        confidence=90.0,
                        openedAt="2026-01-01T00:00:00+00:00",
                        openedSimMinutes=0,
                    )
                    for i in range(2)
                ]
            }
        )
        roomy = compute_confidence(votes, "buy", research_confidence=90.0, portfolio=default_portfolio(), risk_limits=limits, multi_timeframe=_mtf())
        crowded_result = compute_confidence(votes, "buy", research_confidence=90.0, portfolio=crowded, risk_limits=limits, multi_timeframe=_mtf())
        assert crowded_result.score < roomy.score

    def test_missing_role_treated_as_wait(self) -> None:
        votes = [_vote("technical", "echo", "buy")]
        result = compute_confidence(votes, "buy", research_confidence=80.0, portfolio=default_portfolio(), risk_limits=RiskLimits(), multi_timeframe=_mtf())
        assert 0 <= result.score <= 100
        risk_factor = next(f for f in result.factors if f.name == "Risk Conditions")
        assert risk_factor.score == 35.0  # missing risk vote -> "wait" default


class TestMultiTimeframeConfirmationFactor:
    """CEO directive "Professional Quant Trading Core," Phase B — the
    new 7th factor is a real pass-through of the caller's own
    MultiTimeframeConfirmation.agreement_score, never recomputed here."""

    def _result(self, agreement_score: float):
        votes = _six_votes({r: "buy" for r in ["technical", "news", "macro", "risk", "sentiment", "execution"]})
        return compute_confidence(votes, "buy", research_confidence=80.0, portfolio=default_portfolio(), risk_limits=RiskLimits(), multi_timeframe=_mtf(agreement_score))

    def test_factor_score_matches_the_real_agreement_score(self) -> None:
        result = self._result(75.0)
        factor = next(f for f in result.factors if f.name == "Multi-Timeframe Confirmation")
        assert factor.score == 75.0
        assert factor.weight == 0.15

    def test_full_confirmation_raises_the_overall_score_over_zero_confirmation(self) -> None:
        confirmed = self._result(100.0)
        unconfirmed = self._result(0.0)
        assert confirmed.score > unconfirmed.score

    def test_summary_is_carried_through_as_the_factor_detail(self) -> None:
        mtf = MultiTimeframeConfirmation(readings=[], agreementScore=50.0, summary="a specific real summary")
        votes = _six_votes({r: "buy" for r in ["technical", "news", "macro", "risk", "sentiment", "execution"]})
        result = compute_confidence(votes, "buy", research_confidence=80.0, portfolio=default_portfolio(), risk_limits=RiskLimits(), multi_timeframe=mtf)
        factor = next(f for f in result.factors if f.name == "Multi-Timeframe Confirmation")
        assert factor.detail == "a specific real summary"
