"""Covers the real, tick-level enforcement of Black Swan Defensive
Mode's "Pause New Entries" recommendation (Design Bible Chapter 72).
`build_defensive_recommendations()` in app/black_swan.py has always
labeled this `automatic=True`, but nothing in app/nexus.py's tick()
actually gated new trade-proposal generation on `defensive_mode.active`
until this fix — confirmed missing by a live reproduction (activating
Defensive Mode then running a real tick still produced new proposals).
This file exercises the real end-to-end path (GameState.
activate_defensive_mode() -> GameState.advance_time(), the same two
real CEO-triggered actions a player would take), not a unit-level
mock, so a future regression on this exact gate would be caught here.
"""
from __future__ import annotations

import asyncio

from app.state import GameState


def test_defensive_mode_blocks_new_trade_proposal_generation() -> None:
    state = GameState()

    # Baseline: a fresh GameState, advanced one workday, reliably
    # generates at least one real trade proposal (proves this test can
    # actually detect a regression, rather than passing vacuously
    # because nothing was ever going to be proposed anyway).
    baseline, error = asyncio.run(state.advance_time("workday_end", None))
    assert error is None
    assert len(baseline.trade_proposals) > 0

    # The real CEO-triggered activation path — not a direct field flip.
    state2 = GameState()
    activated, error = asyncio.run(state2.activate_defensive_mode())
    assert error is None
    assert activated.defensive_mode.active is True

    after, error = asyncio.run(state2.advance_time("workday_end", None))
    assert error is None
    assert after.defensive_mode.active is True
    assert len(after.trade_proposals) == 0


def test_defensive_mode_deactivation_restores_new_proposal_generation() -> None:
    state = GameState()
    activated, error = asyncio.run(state.activate_defensive_mode())
    assert error is None
    assert activated.defensive_mode.active is True

    deactivated, error = asyncio.run(state.deactivate_defensive_mode())
    assert error is None
    assert deactivated.defensive_mode.active is False

    after, error = asyncio.run(state.advance_time("workday_end", None))
    assert error is None
    assert len(after.trade_proposals) > 0
