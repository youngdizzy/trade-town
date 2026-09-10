"""Runtime configuration for the MCP boundary service.

SECRETS DISCIPLINE — mirrors backend/app/ai_provider.py's own stated rule:
the bearer credential is read once, server-side, from os.environ. It is never
logged, never included in any tool result, never returned by any endpoint,
never written to the audit database, and never placed in a config file. The
only thing that ever leaves this module is `credential_id` — a truncated
SHA-256 digest used purely to correlate audit rows to a credential.

FAIL-CLOSED STARTUP: an absent or blank MCP_BEARER_TOKEN raises at import
time. The service refuses to start rather than running without auth.
"""
from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass, field

BEARER_TOKEN_ENV_VAR = "MCP_BEARER_TOKEN"
MIN_TOKEN_LENGTH = 32


class ConfigurationError(RuntimeError):
    """Raised for a configuration state that must stop the process."""


def _require_token() -> str:
    raw = os.environ.get(BEARER_TOKEN_ENV_VAR, "").strip()
    if not raw:
        raise ConfigurationError(
            f"{BEARER_TOKEN_ENV_VAR} is not set. The MCP boundary refuses to start "
            "without a bearer credential. Generate one with: openssl rand -hex 32"
        )
    if len(raw) < MIN_TOKEN_LENGTH:
        raise ConfigurationError(
            f"{BEARER_TOKEN_ENV_VAR} must be at least {MIN_TOKEN_LENGTH} characters. "
            "Generate one with: openssl rand -hex 32"
        )
    return raw


def credential_id_for(token: str) -> str:
    """A stable, non-reversible reference to a credential, for audit rows.

    Truncated to 16 hex chars: enough to correlate rows for one credential,
    far too little to brute-force the credential back out of an exported
    audit log."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:16]


@dataclass(frozen=True)
class Settings:
    # The ONLY TradeTown address this service is given. In the deployed
    # topology this is the frontend nginx GET-allowlist listener, never
    # backend:8000 — see docker-compose.yml and frontend/deploy/nginx.conf.
    tradetown_read_base_url: str = field(
        default_factory=lambda: os.environ.get("TRADETOWN_READ_BASE_URL", "http://frontend:8081").rstrip("/")
    )
    bearer_token: str = field(default_factory=_require_token)
    external_agent_id: str = field(default_factory=lambda: os.environ.get("MCP_EXTERNAL_AGENT_ID", "tt-scout"))
    db_path: str = field(default_factory=lambda: os.environ.get("MCP_DB_PATH", "/data/mcp_boundary.db"))
    host: str = field(default_factory=lambda: os.environ.get("MCP_HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.environ.get("MCP_PORT", "8090")))
    request_timeout_seconds: float = field(
        default_factory=lambda: float(os.environ.get("MCP_REQUEST_TIMEOUT_SECONDS", "10.0"))
    )

    @property
    def credential_id(self) -> str:
        return credential_id_for(self.bearer_token)

    def guard_not_pointed_at_backend(self) -> None:
        """Refuse a base URL that names the backend directly.

        Pointing this service at backend:8000 would hand it network reach to
        every one of the backend's 135 mutation endpoints. The nginx
        allowlist is the boundary; bypassing it is a configuration error, not
        a deployment preference."""
        lowered = self.tradetown_read_base_url.lower()
        if "backend:8000" in lowered or lowered.endswith(":8000"):
            raise ConfigurationError(
                "TRADETOWN_READ_BASE_URL points at the TradeTown backend directly. "
                "The MCP service must talk only to the internal nginx GET-allowlist "
                "listener (default http://frontend:8081), which forwards an exact "
                "allowlist of GET paths and rejects everything else."
            )


def load_settings() -> Settings:
    settings = Settings()
    settings.guard_not_pointed_at_backend()
    return settings
