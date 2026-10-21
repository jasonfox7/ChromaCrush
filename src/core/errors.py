"""Application error base class.

All application errors are instances of AppError. Errors carry structured
context for logging and API responses, including a correlation ID for
request tracing.

Usage:
    Errors are created through the ErrorService (never constructed directly
    in module code) and raised by the caller:

        raise self._errors.validation(
            "Position out of bounds",
            code="VALIDATION_OUT_OF_BOUNDS",
            position=move.from_pos,
        )
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


@dataclass
class AppError(Exception):
    """Base error type for all application errors.

    Contains structured context for logging and API responses.
    Always created through ErrorService factory methods.

    Attributes:
        code: Machine-readable error code (e.g., "VALIDATION_OUT_OF_BOUNDS").
        message: Human-readable error description.
        context: Structured key-value pairs for debugging.
        correlation_id: Request trace identifier.
        timestamp: UTC timestamp when the error was created.
        http_status: HTTP status code for API responses.
    """

    code: str
    message: str
    context: dict[str, Any] = field(default_factory=dict)
    correlation_id: str = field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    http_status: int = 500

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"

    def __repr__(self) -> str:
        return (
            f"AppError(code={self.code!r}, message={self.message!r}, "
            f"http_status={self.http_status}, correlation_id={self.correlation_id!r})"
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize for API error response.

        Returns:
            Dict matching the ErrorResponse schema defined in
            interface-contracts.md Section 3.5.
        """
        return {
            "error": {
                "code": self.code,
                "message": self.message,
                "correlation_id": self.correlation_id,
                "timestamp": self.timestamp.isoformat(),
            }
        }
