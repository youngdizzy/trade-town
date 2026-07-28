"""Covers v0.7 Feature 34's Company Priorities: the real, already-existing
levers each priority biases (see nexus.py's own comment above
PRIORITY_KNOWLEDGE_MULTIPLIER for why these three and not the other four
named in the brief)."""
from __future__ import annotations

import random

from app.nexus import PRIORITY_RISK_TIGHTEN_FACTOR, _effective_risk_limits
from app.research import tick_research
from app.schemas import AgentId, ResearchItem, RiskLimits


def _research_item(agent_id: AgentId, confidence: float) -> ResearchItem:
    return ResearchItem(
        id=f"research-{agent_id}-1",
        title="test research",
        symbol="AAPL",
        category="stock",  # type: ignore[arg-type]
        priority="normal",
        status="in_progress",
        assignedAgent=agent_id,
        summary="in progress",
        confidence=confidence,
        createdAt="2026-01-01T00:00:00+00:00",
        updatedAt="2026-01-01T00:00:00+00:00",
    )


class TestEffectiveRiskLimits:
    def test_balanced_priority_leaves_the_players_own_limits_untouched(self) -> None:
        limits = RiskLimits()
        assert _effective_risk_limits(limits, "balanced") is limits

    def test_learning_and_research_priorities_do_not_touch_risk_limits(self) -> None:
        limits = RiskLimits()
        assert _effective_risk_limits(limits, "learning") is limits
        assert _effective_risk_limits(limits, "research") is limits

    def test_risk_reduction_tightens_every_boundary_by_the_real_factor(self) -> None:
        limits = RiskLimits()
        tightened = _effective_risk_limits(limits, "risk_reduction")
        factor = PRIORITY_RISK_TIGHTEN_FACTOR
        assert tightened.max_position_pct == round(limits.max_position_pct * factor, 2)
        assert tightened.max_daily_loss_pct == round(limits.max_daily_loss_pct * factor, 2)
        assert tightened.max_drawdown_pct == round(limits.max_drawdown_pct * factor, 2)
        assert tightened.max_sector_concentration_pct == round(limits.max_sector_concentration_pct * factor, 2)
        assert tightened.risk_per_trade_pct == round(limits.risk_per_trade_pct * factor, 2)
        assert tightened.max_open_positions == max(1, round(limits.max_open_positions * factor))

    def test_risk_reduction_never_tightens_open_positions_below_one(self) -> None:
        limits = RiskLimits(maxOpenPositions=1)
        tightened = _effective_risk_limits(limits, "risk_reduction")
        assert tightened.max_open_positions == 1

    def test_does_not_mutate_the_players_stored_limits(self) -> None:
        limits = RiskLimits()
        _effective_risk_limits(limits, "risk_reduction")
        assert limits.max_position_pct == RiskLimits().max_position_pct


class TestResearchSpeedMultiplier:
    def test_default_multiplier_matches_unscaled_behaviour(self) -> None:
        random.seed(42)
        baseline_research, _ = tick_research([_research_item("scout", 50.0)])
        random.seed(42)
        explicit_research, _ = tick_research([_research_item("scout", 50.0)], speed_multiplier=1.0)
        assert baseline_research[0].confidence == explicit_research[0].confidence

    def test_higher_multiplier_gains_more_confidence_per_tick(self) -> None:
        random.seed(7)
        slow, _ = tick_research([_research_item("scout", 50.0)], speed_multiplier=1.0)
        random.seed(7)
        fast, _ = tick_research([_research_item("scout", 50.0)], speed_multiplier=1.5)
        assert fast[0].confidence > slow[0].confidence

    def test_multiplier_never_pushes_confidence_past_complete(self) -> None:
        random.seed(1)
        research, completed = tick_research([_research_item("scout", 99.0)], speed_multiplier=1.5)
        assert all(item.confidence <= 100.0 for item in research)
        assert completed and completed[0].confidence == 100.0
