"""Error service protocol.

All modules create errors through this protocol interface.
The concrete ErrorService is created once in the composition root.
Errors are always raised by the caller: `raise self._errors.validation(...)`.
"""

from __future__ import annotations

from typing import Any, Protocol

from src.core.errors import AppError


class ErrorServiceProtocol(Protocol):
    """Protocol for the error service. Injected into all modules.

    Each factory method returns an AppError instance with the correct
    HTTP status code, error code, and structured context. The caller
    is responsible for raising the returned error.
    """

    def validation(
        self,
        message: str,
        code: str = "VALIDATION_INVALID_INPUT",
        **context: Any,
    ) -> AppError:
        """Create a validation error (400)."""
        ...

    def not_found(
        self,
        message: str,
        code: str = "NOT_FOUND_RESOURCE",
        **context: Any,
    ) -> AppError:
        """Create a not found error (404)."""
        ...

    def unauthorized(
        self,
        message: str,
        code: str = "AUTH_INVALID_CREDENTIALS",
        **context: Any,
    ) -> AppError:
        """Create an authentication error (401)."""
        ...

    def forbidden(
        self,
        message: str,
        code: str = "FORBIDDEN_ACCESS_DENIED",
        **context: Any,
    ) -> AppError:
        """Create an authorization error (403)."""
        ...

    def conflict(
        self,
        message: str,
        code: str = "CONFLICT_STATE",
        **context: Any,
    ) -> AppError:
        """Create a conflict error (409)."""
        ...

    def rate_limited(
        self,
        message: str,
        retry_after: int,
        code: str = "RATE_LIMIT_EXCEEDED",
        **context: Any,
    ) -> AppError:
        """Create a rate limit error (429)."""
        ...

    def internal(
        self,
        message: str,
        code: str = "INTERNAL_UNEXPECTED",
        **context: Any,
    ) -> AppError:
        """Create an internal error (500)."""
        ...
