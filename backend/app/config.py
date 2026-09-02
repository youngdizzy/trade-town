"""Runtime configuration read from environment variables. No secrets are hardcoded."""
from __future__ import annotations

import os
from dataclasses import dataclass, field


def _split_csv(value: str) -> list[str]:
    return [origin.strip() for origin in value.split(",") if origin.strip()]


# CEO directive "Paper Burn-in Test-Isolation Hardening" — named so
# app/routers/health.py's is_default_dev_save check and Settings.database_url's
# own default below can never silently drift apart (one hardcoded string
# repeated in two places was exactly the kind of thing that would make a
# future refactor quietly break the safety check this constant exists for).
DEFAULT_DATABASE_URL = "sqlite:///./data/tradetown.db"


@dataclass(frozen=True)
class Settings:
    database_url: str = field(default_factory=lambda: os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL))
    cors_origins: list[str] = field(
        default_factory=lambda: _split_csv(
            os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:4173")
        )
    )
    tick_interval_seconds: float = field(default_factory=lambda: float(os.getenv("TICK_INTERVAL_SECONDS", "2.0")))
    game_minutes_per_tick: int = field(default_factory=lambda: int(os.getenv("GAME_MINUTES_PER_TICK", "5")))
    persist_interval_ticks: int = field(default_factory=lambda: int(os.getenv("PERSIST_INTERVAL_TICKS", "15")))
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8000")))


settings = Settings()
