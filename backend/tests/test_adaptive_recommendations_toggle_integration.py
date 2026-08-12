"""Covers the real CEO on/off control over Adaptive Mode's recommendation
reads (Design Bible Chapter 75). `TradingModeState.adaptive_recommendations_
enabled` was a real, persisted field that nothing ever read — confirmed by
a live reproduction (toggling it off, then still receiving a live
recommendation from the GET /adaptive-recommendation endpoint's own logic).
This file exercises the real CEO-triggered path (GameState.
set_adaptive_recommendations_enabled(), the same method the router calls),
plus the router's own disabled/enabled branch, so a future regression on
this exact gate would be caught here.
"""
from __future__ import annotations

import asyncio

from app.routers.trading_modes import get_adaptive_mode_recommendation
from app.state import GameState, game_state


def test_set_adaptive_recommendations_enabled_persists_the_flag() -> None:
    state = GameState()
    assert state.data.trading_modes.adaptive_recommendations_enabled is True

    disabled = asyncio.run(state.set_adaptive_recommendations_enabled(False))
    assert disabled.trading_modes.adaptive_recommendations_enabled is False

    enabled = asyncio.run(state.set_adaptive_recommendations_enabled(True))
    assert enabled.trading_modes.adaptive_recommendations_enabled is True


def test_get_adaptive_recommendation_endpoint_respects_the_flag() -> None:
    """Exercises the real router function against the real global
    game_state singleton (restored to its prior value afterward so this
    test doesn't leak state into any test that runs after it)."""
    previous = game_state.data.trading_modes.adaptive_recommendations_enabled
    try:
        asyncio.run(game_state.set_adaptive_recommendations_enabled(False))
        disabled_rec = asyncio.run(get_adaptive_mode_recommendation())
        assert disabled_rec.recommended_mode is None
        assert "off" in disabled_rec.reasoning.lower()

        asyncio.run(game_state.set_adaptive_recommendations_enabled(True))
        enabled_rec = asyncio.run(get_adaptive_mode_recommendation())
        assert "off" not in enabled_rec.reasoning.lower()
    finally:
        asyncio.run(game_state.set_adaptive_recommendations_enabled(previous))
