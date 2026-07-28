"""Covers app/coach.py's v0.7 Feature 18 additions — the mistake/strength
patterns that need a CeoDecisionRecord joined against the TradeDecision
that produced it (by decision_id), not just a closed PaperTrade alone.
Every pattern here must trace back to a real "this decision went against
a specific analyst's real vote, and its real linked trade actually lost
(or won)" join — never a guess about an unrealized outcome.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.coach import _common_mistakes, _override_mistakes, _strengths, generate_report
from app.portfolio import default_portfolio
from app.schemas import CeoDecisionRecord, CompanyScore, PaperTrade, TimeState, TradeDecision


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _decision(decision_id: str, *, supporting: list[str], opposing: list[str]) -> TradeDecision:
    return TradeDecision(
        id=decision_id,
        symbol="NEXA",
        outcome="trade",
        votes=[],
        researchSummary="test",
        technicalSummary="test",
        fundamentalSummary="test",
        riskSummary="test",
        supportingAgents=supporting,  # type: ignore[arg-type]
        opposingAgents=opposing,  # type: ignore[arg-type]
        confidence=80.0,
        finalReasoning="test",
        orderId=None,
        createdAt=_now_iso(),
    )


def _ceo_record(decision_id: str, *, outcome: str) -> CeoDecisionRecord:
    return CeoDecisionRecord(
        id=f"ceo-{decision_id}",
        proposalId=f"proposal-{decision_id}",
        symbol="NEXA",
        category="stock",
        aiRecommendation="buy",
        ceoDecision="buy",
        agreedWithAi=True,
        decisionId=decision_id,
        outcome=outcome,  # type: ignore[arg-type]
        createdAt=_now_iso(),
    )


def _trade(decision_id: str, *, pnl: float, duration_minutes: int = 60) -> PaperTrade:
    return PaperTrade(
        id=f"trade-{decision_id}",
        symbol="NEXA",
        side="buy",
        quantity=10,
        entryPrice=100.0,
        exitPrice=100.0 + pnl / 10,
        pnl=pnl,
        pnlPct=pnl,
        durationMinutes=duration_minutes,
        confidence=80.0,
        reason="test",
        marketConditions="test",
        decisionId=decision_id,
        openedAt=_now_iso(),
        closedAt=_now_iso(),
        openedSimMinutes=0,
        closedSimMinutes=duration_minutes,
    )


class TestOverrideMistakes:
    def test_losing_trade_that_overrode_risk_manager_is_flagged(self) -> None:
        decision = _decision("d1", supporting=["echo"], opposing=["sentinel"])
        record = _ceo_record("d1", outcome="incorrect")
        mistakes = _override_mistakes([record], [decision])
        assert any("Sentinel" in m for m in mistakes)

    def test_losing_trade_that_went_against_trend_is_flagged(self) -> None:
        decision = _decision("d1", supporting=["sentinel"], opposing=["echo"])
        record = _ceo_record("d1", outcome="incorrect")
        mistakes = _override_mistakes([record], [decision])
        assert any("Echo" in m for m in mistakes)

    def test_winning_trade_that_overrode_risk_manager_is_not_flagged(self) -> None:
        decision = _decision("d1", supporting=["echo"], opposing=["sentinel"])
        record = _ceo_record("d1", outcome="correct")
        mistakes = _override_mistakes([record], [decision])
        assert mistakes == []

    def test_pending_decision_is_not_flagged(self) -> None:
        decision = _decision("d1", supporting=[], opposing=["sentinel"])
        record = _ceo_record("d1", outcome="pending")
        mistakes = _override_mistakes([record], [decision])
        assert mistakes == []

    def test_agreement_with_risk_and_trend_is_not_flagged(self) -> None:
        decision = _decision("d1", supporting=["echo", "sentinel"], opposing=[])
        record = _ceo_record("d1", outcome="incorrect")
        mistakes = _override_mistakes([record], [decision])
        assert mistakes == []


class TestCommonMistakesIncludesOverrides:
    def test_common_mistakes_surfaces_a_real_risk_override(self) -> None:
        portfolio = default_portfolio()
        decision = _decision("d1", supporting=["echo"], opposing=["sentinel"])
        record = _ceo_record("d1", outcome="incorrect")
        mistakes = _common_mistakes(portfolio, [record], [decision])
        assert any("Sentinel" in m for m in mistakes)


class TestStrengths:
    def test_high_win_rate_over_enough_trades_is_a_strength(self) -> None:
        portfolio = default_portfolio()
        wins = [_trade(f"w{i}", pnl=50.0) for i in range(4)]
        losses = [_trade("l1", pnl=-10.0)]
        portfolio = portfolio.model_copy(update={"trade_history": [*wins, *losses]})
        strengths = _strengths(portfolio, [], win_rate_value=80.0)
        assert any("Win rate" in s for s in strengths)

    def test_too_few_trades_does_not_claim_consistent_discipline(self) -> None:
        portfolio = default_portfolio()
        portfolio = portfolio.model_copy(update={"trade_history": [_trade("w1", pnl=50.0)]})
        strengths = _strengths(portfolio, [], win_rate_value=100.0)
        assert not any("Win rate" in s for s in strengths)

    def test_patient_win_is_a_strength(self) -> None:
        portfolio = default_portfolio()
        portfolio = portfolio.model_copy(update={"trade_history": [_trade("w1", pnl=50.0, duration_minutes=300)]})
        strengths = _strengths(portfolio, [], win_rate_value=100.0)
        assert any("patience" in s for s in strengths)

    def test_trend_aligned_win_is_a_strength(self) -> None:
        portfolio = default_portfolio()
        trade = _trade("w1", pnl=50.0, duration_minutes=30)
        portfolio = portfolio.model_copy(update={"trade_history": [trade]})
        decision = _decision("w1", supporting=["echo"], opposing=[])
        strengths = _strengths(portfolio, [decision], win_rate_value=100.0)
        assert any("trend recognition" in s for s in strengths)

    def test_no_trades_yields_fallback_strength(self) -> None:
        portfolio = default_portfolio()
        strengths = _strengths(portfolio, [], win_rate_value=0.0)
        assert strengths == ["No standout strengths flagged yet — keep trading to build a track record."]


class TestGenerateReport:
    def test_report_carries_strengths_and_override_mistakes(self) -> None:
        portfolio = default_portfolio()
        losing_trade = _trade("d1", pnl=-50.0)
        portfolio = portfolio.model_copy(update={"trade_history": [losing_trade], "loss_count": 1})
        decision = _decision("d1", supporting=["echo"], opposing=["sentinel"])
        record = _ceo_record("d1", outcome="incorrect")

        report = generate_report(
            "weekly",
            research=[],
            portfolio=portfolio,
            company_score=CompanyScore(
                overall=50.0,
                researchQuality=50.0,
                decisionQuality=50.0,
                riskManagement=50.0,
                paperTradingPerformance=50.0,
                teamCoordination=50.0,
                knowledgeGrowth=50.0,
                simulationSuccess=50.0,
                updatedAt=_now_iso(),
            ),
            researcher_ids=("scout", "nova"),
            new_time=TimeState(day=1, hour=18, minute=0),
            ceo_decisions=[record],
            decisions=[decision],
        )
        assert any("Sentinel" in m for m in report.common_mistakes)
        assert isinstance(report.strengths, list)
        assert len(report.strengths) >= 1
