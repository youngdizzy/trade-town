"""The boundary's deterministic error vocabulary.

Every failure is fail-closed: no partial result, no substituted data, no
silent degradation. Codes and retryability match
docs/SCOUT_READONLY_TOOL_CONTRACT_V0.md §12.1.
"""
from __future__ import annotations

from dataclasses import dataclass

# code -> (http-equivalent status, retryable)
ERROR_CATALOG: dict[str, tuple[int, bool]] = {
    "INVALID_ARGUMENT": (400, False),
    "UNAUTHENTICATED": (401, False),
    "FORBIDDEN": (403, False),
    "NOT_FOUND": (404, False),
    "RUN_MISMATCH": (409, False),
    "EXPIRED": (410, False),
    "RESULT_TOO_LARGE": (413, False),
    "OUT_OF_SCOPE": (422, False),
    "RATE_LIMITED": (429, True),
    "UNAVAILABLE": (503, True),
    "TIMEOUT": (504, True),
}


@dataclass(frozen=True)
class BoundaryError(Exception):
    """A refusal with a machine-readable code.

    `message` is always secret-free: it is built from validated, non-secret
    values only, and every emission path additionally runs it through
    redaction.redact()."""

    code: str
    message: str

    def __post_init__(self) -> None:
        if self.code not in ERROR_CATALOG:
            raise ValueError(f"unknown boundary error code: {self.code}")

    @property
    def status(self) -> int:
        return ERROR_CATALOG[self.code][0]

    @property
    def retryable(self) -> bool:
        return ERROR_CATALOG[self.code][1]

    def to_payload(self) -> dict[str, object]:
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "retryable": self.retryable,
            }
        }

    def __str__(self) -> str:
        return f"{self.code}: {self.message}"
