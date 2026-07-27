"""Covers app/agent_energy.py and app/nexus.py's apply_energy_action —
added for v0.6.2 Phase 6. Every action must have a real, verifiable
effect on real game state, never just a number changing.
"""
from __future__ import annotations

from app.agent_energy import ACTION_COSTS, DEFAULT_CAP, REGEN_PER_DAY, can_afford, default_agent_energy, regen_daily, spend
from app.nexus import apply_energy_action
from app.research import default_research
from app.state import default_state


def test_default_agent_energy_starts_at_cap():
    energy = default_agent_energy()
    assert energy.current == DEFAULT_CAP
    assert energy.cap == DEFAULT_CAP


def test_regen_daily_adds_and_caps():
    energy = default_agent_energy().model_copy(update={"current": 90.0})
    regened = regen_daily(energy)
    assert regened.current == DEFAULT_CAP  # 90 + 20 caps at 100, doesn't overshoot

    energy2 = default_agent_energy().model_copy(update={"current": 10.0})
    regened2 = regen_daily(energy2)
    assert regened2.current == 10.0 + REGEN_PER_DAY


def test_spend_rejects_unaffordable_and_unknown_actions():
    poor = default_agent_energy().model_copy(update={"current": 5.0})
    assert spend(poor, "research_boost") is None  # costs 15, only have 5
    assert spend(default_agent_energy(), "not_a_real_action") is None


def test_spend_deducts_the_exact_cost():
    energy = default_agent_energy()
    spent = spend(energy, "watch_symbol")
    assert spent is not None
    assert spent.current == DEFAULT_CAP - ACTION_COSTS["watch_symbol"]


def test_can_afford_matches_spend():
    poor = default_agent_energy().model_copy(update={"current": 5.0})
    assert can_afford(poor, "research_boost") is False
    assert can_afford(default_agent_energy(), "research_boost") is True


def test_apply_energy_action_research_boost_advances_real_research_confidence():
    state = default_state()
    target = next(r for r in state.research if r.status == "in_progress")
    before_confidence = target.confidence

    new_state, error = apply_energy_action(state, "research_boost", target.id)
    assert error is None
    boosted = next(r for r in new_state.research if r.id == target.id)
    assert boosted.confidence > before_confidence
    assert new_state.agent_energy.current == state.agent_energy.current - ACTION_COSTS["research_boost"]


def test_apply_energy_action_research_boost_rejects_missing_id():
    state = default_state()
    new_state, error = apply_energy_action(state, "research_boost", None)
    assert error is not None
    assert new_state.agent_energy.current == state.agent_energy.current  # nothing spent


def test_apply_energy_action_research_boost_rejects_completed_research():
    state = default_state()
    completed_item = default_research()[0].model_copy(update={"status": "completed"})
    state = state.model_copy(update={"research": [completed_item]})

    new_state, error = apply_energy_action(state, "research_boost", completed_item.id)
    assert error is not None
    assert new_state.agent_energy.current == state.agent_energy.current


def test_apply_energy_action_extra_simulation_queues_a_real_backtest_session():
    state = default_state()
    assert state.backtest_sessions == []

    new_state, error = apply_energy_action(state, "extra_simulation", None)
    assert error is None
    assert len(new_state.backtest_sessions) == 1
    assert new_state.agent_energy.current == state.agent_energy.current - ACTION_COSTS["extra_simulation"]


def test_apply_energy_action_watch_symbol_adds_a_real_watchlist_entry():
    state = default_state()
    before_symbols = {w.symbol for w in state.watchlist}

    new_state, error = apply_energy_action(state, "watch_symbol", None)
    assert error is None
    after_symbols = {w.symbol for w in new_state.watchlist}
    assert len(after_symbols) == len(before_symbols) + 1
    assert new_state.agent_energy.current == state.agent_energy.current - ACTION_COSTS["watch_symbol"]


def test_apply_energy_action_insufficient_energy_changes_nothing():
    state = default_state()
    poor_state = state.model_copy(update={"agent_energy": state.agent_energy.model_copy(update={"current": 1.0})})

    new_state, error = apply_energy_action(poor_state, "extra_simulation", None)
    assert error is not None
    assert new_state.backtest_sessions == poor_state.backtest_sessions
    assert new_state.agent_energy.current == 1.0
