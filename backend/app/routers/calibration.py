"""Signal Calibration endpoints (v0.6.2 Phase 7) — see
app/signal_calibration.py for the grading rubric and why it never looks
at future price. GET issues a fresh challenge (held server-side,
transient, never in the save); POST grades a pending one and persists
the resulting progress + any energy reward, the same "a graded attempt is
a meaningful event" reasoning already applied to energy spends.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict, Field

from app.persistence import persist_modules
from app.schemas import AgentEnergy, SignalCalibrationState, SignalChallenge, SignalChoice
from app.signal_calibration import MAX_LEVEL, MIN_LEVEL, generate_challenge
from app.market_data import market_data_provider
from app.state import game_state

router = APIRouter(prefix="/api/calibration", tags=["calibration"])


class SubmitCalibrationRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    challenge_id: str = Field(alias="challengeId")
    choice: SignalChoice


class SubmitCalibrationResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    signal_calibration: SignalCalibrationState = Field(alias="signalCalibration")
    agent_energy: AgentEnergy = Field(alias="agentEnergy")


@router.get("/challenge", response_model=SignalChallenge)
async def get_challenge(level: int = Query(1, ge=MIN_LEVEL, le=MAX_LEVEL)) -> SignalChallenge:
    state = await game_state.snapshot()
    try:
        return generate_challenge(level, market_data_provider, state.watchlist, state.risk_warnings, state.research)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None


@router.post("/submit", response_model=SubmitCalibrationResponse)
async def submit_challenge(payload: SubmitCalibrationRequest) -> SubmitCalibrationResponse:
    state, error = await game_state.submit_signal_calibration(payload.challenge_id, payload.choice)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_modules(state)
    return SubmitCalibrationResponse(signalCalibration=state.signal_calibration, agentEnergy=state.agent_energy)
