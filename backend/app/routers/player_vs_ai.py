"""Player vs AI endpoints (v0.6.2 Phase 8) — see app/player_vs_ai.py for
the eligibility rule (only decisions with a real, already-closed trade
outcome) and grading logic. GET issues a fresh prompt (held server-side,
transient, never in the save); POST grades a pending one and persists the
resulting round, the same "a graded round is a meaningful event"
reasoning already applied to Signal Calibration and Agent Energy.
"""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.persistence import persist_save
from app.schemas import PlayerVsAiPrompt, PlayerVsAiState, SignalChoice
from app.state import game_state

router = APIRouter(prefix="/api/player-vs-ai", tags=["player-vs-ai"])


class SubmitPlayerVsAiRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    prompt_id: str = Field(alias="promptId")
    choice: SignalChoice


class SubmitPlayerVsAiResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    player_vs_ai: PlayerVsAiState = Field(alias="playerVsAi")


@router.get("/prompt", response_model=PlayerVsAiPrompt)
async def get_prompt() -> PlayerVsAiPrompt:
    prompt, error = await game_state.generate_player_vs_ai_prompt()
    if error is not None or prompt is None:
        raise HTTPException(status_code=400, detail=error or "No prompt available.")
    return prompt


@router.post("/submit", response_model=SubmitPlayerVsAiResponse)
async def submit_prompt(payload: SubmitPlayerVsAiRequest) -> SubmitPlayerVsAiResponse:
    state, error = await game_state.submit_player_vs_ai(payload.prompt_id, payload.choice)
    if error is not None:
        raise HTTPException(status_code=400, detail=error)
    persist_save(state)
    return SubmitPlayerVsAiResponse(playerVsAi=state.player_vs_ai)
