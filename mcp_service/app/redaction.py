"""Secret redaction, matching backend/app/market_data.py::_redact()'s rule
verbatim: full replacement, never a partial mask like "sk-***1234" that
itself leaks length and prefix information.

Every log line and every error message this service emits passes through
`redact()` before it can reach a sink.
"""
from __future__ import annotations

REDACTED = "[REDACTED]"

_registered_secrets: list[str] = []


def register_secret(secret: str) -> None:
    """Register a value that must never appear in any emitted string."""
    if secret and secret not in _registered_secrets:
        _registered_secrets.append(secret)


def redact(text: str, *extra_secrets: str) -> str:
    redacted = text
    for secret in (*_registered_secrets, *extra_secrets):
        if secret:
            redacted = redacted.replace(secret, REDACTED)
    return redacted


def clear_registered_secrets() -> None:
    """Test-only helper; never called by the service itself."""
    _registered_secrets.clear()
