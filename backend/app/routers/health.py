from fastapi import APIRouter

from app.config import DEFAULT_DATABASE_URL, settings
from app.schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(isDefaultDevSave=settings.database_url == DEFAULT_DATABASE_URL)
