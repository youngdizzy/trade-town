"""Forge — Quant Developer (Quantitative Research & Intelligence System,
Piece 7). See app/quant_developer.py's module docstring for what this
endpoint audits vs. what the other four quant roles already own.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.quant_developer import assess_monte_carlo_reliability
from app.schemas import MonteCarloReliabilityAssessment
from app.state import game_state

router = APIRouter(prefix="/api/quant-developer", tags=["quant-developer"])


@router.get("/monte-carlo-reliability", response_model=MonteCarloReliabilityAssessment)
async def monte_carlo_reliability() -> MonteCarloReliabilityAssessment:
    """Read-only and computed fresh on every call (see
    app/quant_developer.py's module docstring for why this is a
    standing pipeline fact, not a per-strategy artifact, and therefore
    never persisted). No game-state lock needed — nothing here mutates
    the save, only reads the current real Monte Carlo result list."""
    state = await game_state.snapshot()
    return assess_monte_carlo_reliability(state.strategy_monte_carlo_results)
