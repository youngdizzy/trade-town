"""Covers app/nexus.py's decision-log cap — added for v0.6.2's save-payload
fix. `decisions` was the one list in the whole save schema with no upper
bound (see MAX_DECISIONS' own comment in nexus.py for the full story): it
grew by one ~1.5KB record every time research crossed the trade-candidate
threshold, for as long as the process stayed up, with nothing ever
evicted — which is what silently grew real deployments' save payloads
past nginx's default 1MB limit and caused the reported 413 errors.
"""
from __future__ import annotations

from app.nexus import MAX_DECISIONS, _trim_decisions
from app.schemas import TradeDecision


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
