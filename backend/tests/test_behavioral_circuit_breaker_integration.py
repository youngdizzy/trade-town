"""Real, end-to-end proof that the Behavioral Circuit Breaker
(app/behavioral_risk.py) actually gates a live trade through both real
paths a proposal can be resolved by: a genuine CEO click
(GameState.submit_ceo_decision) and an auto-resolution
(app/nexus.py's _apply_operating_mode, reached via GameState.advance_time
while Operating Mode is "executive"). Mirrors
test_defensive_mode_integration.py's pattern: real GameState-level
actions, not a unit-level mock, so a future regression on this exact
Gatekeeper wiring would be caught here.

The loss itself is seeded via the real app/portfolio.py
open_position()/close_position() functions — not a fabricated PaperTrade
literal — so the trade_history entry the Behavioral Circuit Breaker reads
is exactly what the real trading pipeline would have produced.
"""
from __future__ import annotations

import asyncio

from app.portfolio import close_position, open_position
from app.schemas import AnalystVote, ConfidenceFactor, DecisionConfidence, TimeState, TradeProposal
from app.state import GameState

ROLE_TO_AGENT = {"technical": "echo", "news": "scout", "macro": "nova", "risk": "sentinel", "sentiment": "pulse", "execution": "atlas"}


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _six_buy_votes() -> list[AnalystVote]:
    return [AnalystVote(role=role, agentId=agent, choice="buy", reasoning="test reasoning", evidence=["real evidence line"]) for role, agent in ROLE_TO_AGENT.items()]  # type: ignore[arg-type]


def _proposal(*, proposal_id: str, symbol: str, quantity: float, price: float = 100.0, created_sim_minutes: int) -> TradeProposal:
    return TradeProposal(
        id=proposal_id,
        symbol=symbol,
        category="stock",
        quantity=quantity,
        price=price,
        confidence=90.0,
        analystVotes=_six_buy_votes(),
        overallRecommendation="buy",
        researchSummary="test research summary",
        riskSummary="test risk summary",
        confidenceEngine=DecisionConfidence(score=90.0, tier="strong", summary="test", factors=[ConfidenceFactor(name="test", score=90.0, weight=1.0, detail="test")]),
        createdAt=_now_iso(),
        createdSimMinutes=created_sim_minutes,
    )


def _seed_real_loss(state: GameState, *, symbol: str, quantity: float, entry_price: float, exit_price: float, opened_sim_minutes: int, duration_minutes: int) -> int:
    """Opens and closes a real position via app/portfolio.py's own real
    functions — the exact same path a live trade takes — and returns the
    resulting trade's closed_sim_minutes."""
    portfolio = open_position(
        state.data.paper_portfolio,
        position_id=f"pos-loss-{symbol}",
        symbol=symbol,
        price=entry_price,
        opened_by="atlas",
        confidence=80.0,
        opened_sim_minutes=opened_sim_minutes,
        side="buy",
        quantity=quantity,
    )
    portfolio, trade = close_position(
        portfolio,
        position_id=f"pos-loss-{symbol}",
        exit_price=exit_price,
        duration_minutes=duration_minutes,
        reason="test loss",
        market_conditions="test conditions",
        supporting_agents=[],
        opposing_agents=[],
    )
    assert trade is not None
    assert trade.pnl < 0
    state.data = state.data.model_copy(update={"paper_portfolio": portfolio})
    return trade.closed_sim_minutes


class TestCeoClickPath:
    """GameState.submit_ceo_decision — a real CEO click."""

    def test_same_instrument_oversized_reentry_within_cooldown_is_rejected(self) -> None:
        state = GameState()
        state.data = state.data.model_copy(update={"time": TimeState(day=0, hour=0, minute=0)})
        closed_sim_minutes = _seed_real_loss(state, symbol="AAPL", quantity=10.0, entry_price=100.0, exit_price=90.0, opened_sim_minutes=0, duration_minutes=10)
        # 20 minutes after the loss — within the default 60-minute cooldown.
        state.data = state.data.model_copy(update={"time": TimeState(day=0, hour=0, minute=closed_sim_minutes + 20)})

        proposal = _proposal(proposal_id="prop-revenge", symbol="AAPL", quantity=100.0, created_sim_minutes=closed_sim_minutes + 20)
        state.data = state.data.model_copy(update={"trade_proposals": [*state.data.trade_proposals, proposal]})

        after, error = asyncio.run(state.submit_ceo_decision("prop-revenge", "buy"))
        assert error is None

        decision = next(d for d in after.decisions if d.id == "decision-prop-revenge")
        assert decision.order_id is None, "A behaviorally-triggered proposal must not open a real position."
        assert decision.gatekeeper_verdict is not None
        assert decision.gatekeeper_verdict.approved is False
        behavioral_check = next(c for c in decision.gatekeeper_verdict.checks if c.id == "behavioral")
        assert behavioral_check.passed is False

        rejection = next((r for r in after.gatekeeper_rejections if r.proposal_id == "prop-revenge"), None)
        assert rejection is not None
        assert any("Behavioral Circuit Breaker" in reason for reason in rejection.reasons)

    def test_legitimate_different_symbol_normal_size_reentry_is_not_behaviorally_rejected(self) -> None:
        state = GameState()
        state.data = state.data.model_copy(update={"time": TimeState(day=0, hour=0, minute=0)})
        closed_sim_minutes = _seed_real_loss(state, symbol="AAPL", quantity=10.0, entry_price=100.0, exit_price=90.0, opened_sim_minutes=0, duration_minutes=10)
        state.data = state.data.model_copy(update={"time": TimeState(day=0, hour=0, minute=closed_sim_minutes + 20)})

        proposal = _proposal(proposal_id="prop-legit", symbol="MSFT", quantity=10.0, created_sim_minutes=closed_sim_minutes + 20)
        state.data = state.data.model_copy(update={"trade_proposals": [*state.data.trade_proposals, proposal]})

        after, error = asyncio.run(state.submit_ceo_decision("prop-legit", "buy"))
        assert error is None

        decision = next(d for d in after.decisions if d.id == "decision-prop-legit")
        assert decision.gatekeeper_verdict is not None
        behavioral_check = next(c for c in decision.gatekeeper_verdict.checks if c.id == "behavioral")
        assert behavioral_check.passed is True
        assert decision.gatekeeper_verdict.approved is True
        assert decision.order_id is not None


class TestAutoResolutionPath:
    """app/nexus.py's _apply_operating_mode, reached via a real tick
    (GameState.advance_time) while Operating Mode is "executive" — proves
    the Behavioral Circuit Breaker cannot be bypassed by choosing a more
    hands-off Operating Mode."""

    def test_auto_resolution_rejects_the_same_revenge_shaped_proposal(self) -> None:
        state = GameState()
        state.data = state.data.model_copy(update={"time": TimeState(day=0, hour=0, minute=0), "settings": state.data.settings.model_copy(update={"operating_mode": "executive"})})
        closed_sim_minutes = _seed_real_loss(state, symbol="AAPL", quantity=10.0, entry_price=100.0, exit_price=90.0, opened_sim_minutes=0, duration_minutes=10)
        state.data = state.data.model_copy(update={"time": TimeState(day=0, hour=0, minute=closed_sim_minutes + 20)})

        proposal = _proposal(proposal_id="prop-auto-revenge", symbol="AAPL", quantity=100.0, created_sim_minutes=closed_sim_minutes + 20)
        state.data = state.data.model_copy(update={"trade_proposals": [*state.data.trade_proposals, proposal]})

        after, error = asyncio.run(state.advance_time("hours", 1))
        assert error is None

        decision = next((d for d in after.decisions if d.id == "decision-prop-auto-revenge"), None)
        assert decision is not None, "The auto-resolution sweep should have resolved this pending proposal."
        assert decision.order_id is None
        assert decision.gatekeeper_verdict is not None
        assert decision.gatekeeper_verdict.approved is False
        behavioral_check = next(c for c in decision.gatekeeper_verdict.checks if c.id == "behavioral")
        assert behavioral_check.passed is False

        ceo_record = next(r for r in after.ceo_decisions if r.proposal_id == "prop-auto-revenge")
        assert ceo_record.resolved_by == "auto"
