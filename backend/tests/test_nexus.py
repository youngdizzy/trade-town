"""Covers app/nexus.py's decision-log cap — added for v0.6.2's save-payload
fix. `decisions` was the one list in the whole save schema with no upper
bound (see MAX_DECISIONS' own comment in nexus.py for the full story): it
grew by one ~1.5KB record every time research crossed the trade-candidate
threshold, for as long as the process stayed up, with nothing ever
evicted — which is what silently grew real deployments' save payloads
past nginx's default 1MB limit and caused the reported 413 errors.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.market_intelligence import default_market_intelligence_state
from app.nexus import MAX_DECISIONS, _apply_operating_mode, _trim_decisions
from app.portfolio import default_portfolio
from app.schemas import AnalystVote, ConfidenceFactor, DecisionConfidence, RiskLimits, TradeDecision, TradeProposal


def _decision(n: int) -> TradeDecision:
    return TradeDecision(
        id=f"decision-{n}",
        symbol="AAPL",
        outcome="trade",
        votes=[],
        researchSummary="x",
        technicalSummary="x",
        fundamentalSummary="x",
        riskSummary="x",
        supportingAgents=[],
        opposingAgents=[],
        confidence=90.0,
        finalReasoning="x",
        createdAt="2026-01-01T00:00:00+00:00",
    )


def test_trim_decisions_is_a_noop_under_the_cap():
    decisions = [_decision(i) for i in range(MAX_DECISIONS - 1)]
    _trim_decisions(decisions)
    assert len(decisions) == MAX_DECISIONS - 1


def test_trim_decisions_evicts_oldest_first_down_to_the_cap():
    decisions = [_decision(i) for i in range(MAX_DECISIONS + 50)]
    _trim_decisions(decisions)
    assert len(decisions) == MAX_DECISIONS
    # The oldest 50 (ids 0..49) were evicted; the most recent MAX_DECISIONS survive.
    assert decisions[0].id == "decision-50"
    assert decisions[-1].id == f"decision-{MAX_DECISIONS + 49}"


def test_decisions_never_grow_unbounded_across_many_ticks():
    """Simulates the real failure mode: repeated appends across many
    ticks, as nexus.tick() does every sim tick a trade candidate
    resolves, with the same trim call applied after each one."""
    decisions: list[TradeDecision] = []
    for tick in range(MAX_DECISIONS * 3):
        decisions.append(_decision(tick))
        _trim_decisions(decisions)
        assert len(decisions) <= MAX_DECISIONS
    assert len(decisions) == MAX_DECISIONS


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


_DEFAULT_FACTORS = [
    ConfidenceFactor(name="agreement", score=90.0, weight=0.30, detail="d"),
    ConfidenceFactor(name="technical", score=80.0, weight=0.20, detail="d"),
    ConfidenceFactor(name="risk", score=85.0, weight=0.20, detail="d"),
    ConfidenceFactor(name="research", score=80.0, weight=0.15, detail="d"),
    ConfidenceFactor(name="sentiment", score=75.0, weight=0.10, detail="d"),
    ConfidenceFactor(name="exposure", score=90.0, weight=0.05, detail="d"),
]


def _proposal() -> TradeProposal:
    # tier="elite"/score=96 with no active risk/confidence concerns is
    # not "significant" per app/executive.py's is_significant_proposal
    # — the same real, otherwise-auto-resolving proposal used in
    # test_executive_intelligence.py's own "trade_normally" case.
    return TradeProposal(
        id="proposal-1",
        symbol="NEXA",
        category="stock",
        quantity=1.0,
        price=100.0,
        confidence=96.0,
        analystVotes=[AnalystVote(role="risk", agentId="sentinel", choice="buy", reasoning="Position sized within limits.", evidence=["Real risk read"])],  # type: ignore[arg-type]
        overallRecommendation="buy",
        researchSummary="Nova's research backs this setup with a completed research item.",
        riskSummary="Within all configured risk limits.",
        confidenceEngine=DecisionConfidence(score=96.0, tier="elite", summary="A well-supported setup.", factors=_DEFAULT_FACTORS),  # type: ignore[arg-type]
        createdAt=_now_iso(),
        createdSimMinutes=0,
    )


class TestApplyOperatingModePauseTrading:
    """v0.7 Design Bible Chapter 66 — AI Consensus Safety. Closes the one
    real, precise gap that chapter's own research found: the
    pause_trading signal (app/executive_intelligence.py's
    compute_executive_recommendation()) already existed, but nothing
    enforced it before this."""

    def _call(self, *, operating_mode: str, market_intelligence):
        return _apply_operating_mode(
            operating_mode,
            [_proposal()],
            [],  # debates
            default_portfolio(),
            RiskLimits(),
            [],  # risk_warnings
            {"NEXA": 100.0},  # prices
            0,  # now_sim_minutes
            [],  # memory
            [],  # decisions
            [],  # ceo_decisions
            [],  # gatekeeper_rejections
            [],  # news
            [],  # challenge_reports
            [],  # coach_reports
            [],  # meeting_log
            1,  # sim_day
            market_intelligence,
            [],  # war_room_sessions
        )

    def test_avoid_trading_regime_keeps_an_otherwise_non_significant_proposal_pending_in_assisted_mode(self) -> None:
        avoid_trading_mi = default_market_intelligence_state()
        avoid_trading_mi = avoid_trading_mi.model_copy(update={"quality": avoid_trading_mi.quality.model_copy(update={"tier": "avoid_trading"})})
        remaining, _, _ = self._call(operating_mode="assisted", market_intelligence=avoid_trading_mi)
        assert [p.id for p in remaining] == ["proposal-1"]

    def test_avoid_trading_regime_keeps_the_same_proposal_pending_even_in_executive_mode(self) -> None:
        # The real behavioral change this pass makes: previously Executive
        # Mode auto-resolved everything not flagged "significant" — a
        # real pause_trading recommendation is a safety constraint, not a
        # significance judgment, so it now applies here too.
        avoid_trading_mi = default_market_intelligence_state()
        avoid_trading_mi = avoid_trading_mi.model_copy(update={"quality": avoid_trading_mi.quality.model_copy(update={"tier": "avoid_trading"})})
        remaining, _, _ = self._call(operating_mode="executive", market_intelligence=avoid_trading_mi)
        assert [p.id for p in remaining] == ["proposal-1"]

    def test_a_normal_regime_still_auto_resolves_in_executive_mode(self) -> None:
        # Control: confirms the new gate is regime-specific, not a
        # blanket block on every proposal.
        remaining, _, _ = self._call(operating_mode="executive", market_intelligence=default_market_intelligence_state())
        assert remaining == []


class TestApplyOperatingModeEmergencyStop:
    """Design Bible Chapter 67 (TTOS) Part 3 — a CEO-triggered Emergency
    Stop keeps every pending proposal pending, in both Assisted and
    Executive mode, checked before every other significance/safety
    check (see app/emergency_stop.py)."""

    def _call(self, *, operating_mode: str, emergency_stop_active: bool):
        return _apply_operating_mode(
            operating_mode,
            [_proposal()],
            [],  # debates
            default_portfolio(),
            RiskLimits(),
            [],  # risk_warnings
            {"NEXA": 100.0},  # prices
            0,  # now_sim_minutes
            [],  # memory
            [],  # decisions
            [],  # ceo_decisions
            [],  # gatekeeper_rejections
            [],  # news
            [],  # challenge_reports
            [],  # coach_reports
            [],  # meeting_log
            1,  # sim_day
            default_market_intelligence_state(),
            [],  # war_room_sessions
            emergency_stop_active=emergency_stop_active,
        )

    def test_emergency_stop_keeps_an_otherwise_non_significant_proposal_pending_in_assisted_mode(self) -> None:
        remaining, _, _ = self._call(operating_mode="assisted", emergency_stop_active=True)
        assert [p.id for p in remaining] == ["proposal-1"]

    def test_emergency_stop_keeps_the_same_proposal_pending_even_in_executive_mode(self) -> None:
        remaining, _, _ = self._call(operating_mode="executive", emergency_stop_active=True)
        assert [p.id for p in remaining] == ["proposal-1"]

    def test_inactive_emergency_stop_still_auto_resolves_normally_in_executive_mode(self) -> None:
        # Control: confirms the new gate only fires when actually active.
        remaining, _, _ = self._call(operating_mode="executive", emergency_stop_active=False)
        assert remaining == []
