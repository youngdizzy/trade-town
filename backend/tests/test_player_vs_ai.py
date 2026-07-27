"""Covers app/player_vs_ai.py — v0.6.2 Phase 8. Grading is always against
a real, already-realized P&L, never a guess about an unrealized or
never-placed trade — and never assumes the AI is automatically right.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.market_data import MockMarketDataProvider
from app.player_vs_ai import (
    _eligible_decisions,
    _pending,
    generate_prompt,
    grade_submission,
)
from app.schemas import PaperTrade, PlayerVsAiState, ResearchItem, TradeDecision


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _decision(id_: str, symbol: str, outcome: str = "trade") -> TradeDecision:
    return TradeDecision(
        id=id_,
        symbol=symbol,
        outcome=outcome,  # type: ignore[arg-type]
        votes=[],
        researchSummary="Real research summary.",
        technicalSummary="Real technical summary.",
        fundamentalSummary="Real fundamental summary.",
        riskSummary="Real risk summary.",
        supportingAgents=["atlas"],
        opposingAgents=[],
        confidence=72.0,
        finalReasoning="Atlas approved the trade.",
        orderId="order-1" if outcome == "trade" else None,
        createdAt=_now_iso(),
    )


def _closed_trade(decision_id: str, symbol: str, pnl: float, pnl_pct: float) -> PaperTrade:
    return PaperTrade(
        id=f"trade-{decision_id}",
        symbol=symbol,
        side="buy",
        quantity=10,
        entryPrice=100.0,
        exitPrice=100.0 + pnl / 10,
        pnl=pnl,
        pnlPct=pnl_pct,
        durationMinutes=120,
        confidence=72.0,
        reason="Real reason.",
        marketConditions="Real conditions.",
        decisionId=decision_id,
        openedAt=_now_iso(),
        closedAt=_now_iso(),
        openedSimMinutes=100,
        closedSimMinutes=220,
    )


def _research(symbol: str, category: str = "stock") -> ResearchItem:
    return ResearchItem(
        id=f"research-{symbol}",
        title=f"{symbol} research",
        symbol=symbol,
        category=category,  # type: ignore[arg-type]
        priority="normal",
        status="in_progress",
        assignedAgent="atlas",
        summary="Real summary.",
        confidence=60.0,
        createdAt=_now_iso(),
        updatedAt=_now_iso(),
    )


def test_eligible_decisions_requires_a_real_closed_trade():
    decision = _decision("d1", "AAPL")
    trade = _closed_trade("d1", "AAPL", pnl=50.0, pnl_pct=5.0)
    eligible = _eligible_decisions([decision], [trade], set())
    assert eligible == [(decision, trade)]


def test_eligible_decisions_excludes_no_trade_outcomes():
    decision = _decision("d2", "MSFT", outcome="no_trade")
    eligible = _eligible_decisions([decision], [], set())
    assert eligible == []


def test_eligible_decisions_excludes_open_positions_with_no_closed_trade():
    decision = _decision("d3", "SPY")
    eligible = _eligible_decisions([decision], [], set())
    assert eligible == []


def test_eligible_decisions_excludes_already_used_decision_ids():
    decision = _decision("d4", "QQQ")
    trade = _closed_trade("d4", "QQQ", pnl=10.0, pnl_pct=1.0)
    eligible = _eligible_decisions([decision], [trade], {"d4"})
    assert eligible == []


def test_generate_prompt_raises_when_nothing_is_eligible():
    provider = MockMarketDataProvider()
    try:
        generate_prompt([], [], [], provider, set())
        raised = False
    except ValueError:
        raised = True
    assert raised


def test_generate_prompt_never_leaks_ground_truth_fields():
    provider = MockMarketDataProvider()
    decision = _decision("d5", "AAPL")
    trade = _closed_trade("d5", "AAPL", pnl=25.0, pnl_pct=2.5)
    prompt = generate_prompt([decision], [trade], [_research("AAPL")], provider, set())
    assert prompt.symbol == "AAPL"
    assert not hasattr(prompt, "outcome")
    assert not hasattr(prompt, "votes")
    assert not hasattr(prompt, "final_reasoning")
    assert not hasattr(prompt, "finalReasoning")
    assert prompt.id in _pending


def test_grade_submission_correct_entry_marks_both_player_and_ai_correct_on_a_winner():
    provider = MockMarketDataProvider()
    decision = _decision("d6", "AAPL")
    trade = _closed_trade("d6", "AAPL", pnl=100.0, pnl_pct=10.0)
    prompt = generate_prompt([decision], [trade], [_research("AAPL")], provider, set())

    state = PlayerVsAiState()
    new_state, error = grade_submission(state, prompt.id, "enter")
    assert error is None
    round_ = new_state.rounds[-1]
    assert round_.ground_truth_choice == "enter"
    assert round_.player_correct is True
    assert round_.ai_correct is True
    assert new_state.player_correct_count == 1
    assert new_state.ai_correct_count == 1
    assert new_state.total_count == 1


def test_grade_submission_a_losing_ai_trade_marks_ai_wrong_never_assumed_right():
    provider = MockMarketDataProvider()
    decision = _decision("d7", "MSFT")
    trade = _closed_trade("d7", "MSFT", pnl=-40.0, pnl_pct=-4.0)
    prompt = generate_prompt([decision], [trade], [_research("MSFT")], provider, set())

    state = PlayerVsAiState()
    # Player wisely avoided it — should be marked correct even though the
    # AI (which did enter) is marked wrong.
    new_state, error = grade_submission(state, prompt.id, "avoid")
    assert error is None
    round_ = new_state.rounds[-1]
    assert round_.ground_truth_choice == "avoid"
    assert round_.ai_correct is False
    assert round_.player_correct is True


def test_grade_submission_wait_is_graded_the_same_as_avoid_against_a_loser():
    provider = MockMarketDataProvider()
    decision = _decision("d8", "GLD")
    trade = _closed_trade("d8", "GLD", pnl=-20.0, pnl_pct=-2.0)
    prompt = generate_prompt([decision], [trade], [_research("GLD")], provider, set())

    state = PlayerVsAiState()
    new_state, _ = grade_submission(state, prompt.id, "wait")
    assert new_state.rounds[-1].player_correct is True


def test_grade_submission_unknown_prompt_id_changes_nothing():
    state = PlayerVsAiState()
    new_state, error = grade_submission(state, "not-a-real-id", "enter")
    assert error is not None
    assert new_state == state


def test_grade_submission_consumes_the_pending_prompt_once():
    provider = MockMarketDataProvider()
    decision = _decision("d9", "QQQ")
    trade = _closed_trade("d9", "QQQ", pnl=15.0, pnl_pct=1.5)
    prompt = generate_prompt([decision], [trade], [_research("QQQ")], provider, set())

    state = PlayerVsAiState()
    grade_submission(state, prompt.id, "enter")
    assert prompt.id not in _pending
    _, error = grade_submission(state, prompt.id, "enter")
    assert error is not None


def test_generate_prompt_excludes_symbols_already_used_for_a_round():
    provider = MockMarketDataProvider()
    decision = _decision("d10", "AAPL")
    trade = _closed_trade("d10", "AAPL", pnl=5.0, pnl_pct=0.5)
    # Only one eligible decision exists, and it's marked already-used —
    # nothing left to offer.
    try:
        generate_prompt([decision], [trade], [_research("AAPL")], provider, {"d10"})
        raised = False
    except ValueError:
        raised = True
    assert raised
