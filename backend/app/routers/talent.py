"""The Talent Discovery System (v0.7 Feature 44). See app/talent.py's
module docstring for what this feature builds vs. deliberately cuts.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from app.persistence import persist_modules
from app.state import game_state

router = APIRouter(prefix="/api/talent", tags=["talent"])


class AckTalentReportRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    report_id: str = Field(alias="reportId")


class AckTalentReportResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    viewed_report_ids: list[str] = Field(alias="viewedReportIds")


@router.post("/ack-report", response_model=AckTalentReportResponse)
async def ack_talent_report(payload: AckTalentReportRequest) -> AckTalentReportResponse:
    viewed_ids = await game_state.ack_talent_report(payload.report_id)
    persist_modules(await game_state.snapshot())
    return AckTalentReportResponse(viewedReportIds=viewed_ids)
