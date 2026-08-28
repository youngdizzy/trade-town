"""CEO directive "Features 26-30," Feature 29 — read-only endpoints over
Prediction Records, mirroring routers/performance_review.py's own
convention: `await game_state.snapshot()`, computed fresh every call,
nothing here mutates the save. The full list is already broadcast on
every WS tick (see app/ws_manager.py's `predictionRecords` field) — this
router adds the one genuinely new query the broadcast can't offer
cheaply on the frontend: "what's this one agent's own recent prediction
track record."
"""
from __future__ import annotations

from fastapi import APIRouter, Path

from app.prediction_tracking import compute_brier_calibration
from app.schemas import AgentId, BrierCalibrationSummary, PredictionRecord
from app.state import game_state

router = APIRouter(prefix="/api/predictions", tags=["predictions"])


@router.get("/{agent_id}", response_model=list[PredictionRecord])
async def predictions_for_agent(agent_id: AgentId = Path(...)) -> list[PredictionRecord]:
    """Every real PredictionRecord this agent is a real supporting agent
    on, oldest first — pending and resolved both included so the CEO can
    see the full track record, not just resolved ones."""
    state = await game_state.snapshot()
    return [p for p in state.prediction_records if agent_id in p.attributed_agents]


@router.get("/calibration/brier", response_model=BrierCalibrationSummary)
async def brier_calibration() -> BrierCalibrationSummary:
    """CEO directive "Professional Quant Trading Core," Phase B P2 item
    — a real Brier-score calibration read over the same Prediction
    Records ledger above. See app/prediction_tracking.py's
    compute_brier_calibration() for the full methodology. Computed
    fresh per request; no new GameSaveState field, nothing here gates
    or scores anything."""
    state = await game_state.snapshot()
    return compute_brier_calibration(state.prediction_records)
