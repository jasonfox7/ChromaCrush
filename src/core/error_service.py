"""Error factory service.

Creates structured ``AppError`` instances for every error category defined
in the error taxonomy (interface-contracts.md Section 2). Each factory
method:

* Sets the correct HTTP status code.
* Captures the current correlation ID from the context variable.
* Logs the error at ERROR level through the injected logger.

Startup sequence:
    errors = ErrorService(logger)

Usage in modules:
    raise self._errors.validation(
        "Positions must be adjacent",
        code="VALIDATION_POSITIONS_NOT_ADJACENT",
        from_pos=move.from_pos,
        to_pos=move.to_pos,
    )
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.core.errors import AppError
from src.core.protocols.correlation import correlation_id_var
from src.core.protocols.logger import LoggerProtocol


class ErrorService:
    """Error factory satisfying ``ErrorServiceProtocol``.

    Created once in the composition root; all other code receives it
    through ``__init__`` injection.
    """

    def __init__(self, logger: LoggerProtocol) -> None:
        self._logger = logger

    # ------------------------------------------------------------------
    # Public factory methods
    # ------------------------------------------------------------------

    def validation(
        self,
        message: str,
        code: str = "VALIDATION_INVALID_INPUT",
        **context: Any,
    ) -> AppError:
        """Create a validation error (HTTP 400).

        Args:
            message: Human-readable description of what went wrong.
            code: Machine-readable error code from the taxonomy.
            **context: Arbitrary key-value pairs for debugging.
        """
        return self._create_error(code, message, http_status=400, **context)

    def not_found(
        self,
        message: str,
        code: str = "NOT_FOUND_RESOURCE",
        **context: Any,
    ) -> AppError:
        """Create a not-found error (HTTP 404).

        Args:
            message: Human-readable description.
            code: Machine-readable error code from the taxonomy.
            **context: Arbitrary key-value pairs for debugging.
        """
        return self._create_error(code, message, http_status=404, **context)

    def unauthorized(
        self,
        message: str,
        code: str = "AUTH_INVALID_CREDENTIALS",
        **context: Any,
    ) -> AppError:
        """Create an authentication error (HTTP 401).

        Args:
            message: Human-readable description.
            code: Machine-readable error code from the taxonomy.
            **context: Arbitrary key-value pairs for debugging.
        """
        return self._create_error(code, message, http_status=401, **context)

    def forbidden(
        self,
        message: str,
        code: str = "FORBIDDEN_ACCESS_DENIED",
        **context: Any,
    ) -> AppError:
        """Create an authorisation error (HTTP 403).

        Args:
            message: Human-readable description.
            code: Machine-readable error code from the taxonomy.
            **context: Arbitrary key-value pairs for debugging.
        """
        return self._create_error(code, message, http_status=403, **context)

    def conflict(
        self,
        message: str,
        code: str = "CONFLICT_STATE",
        **context: Any,
    ) -> AppError:
        """Create a conflict error (HTTP 409).

        Args:
            message: Human-readable description.
            code: Machine-readable error code from the taxonomy.
            **context: Arbitrary key-value pairs for debugging.
        """
        return self._create_error(code, message, http_status=409, **context)

    def rate_limited(
        self,
        message: str,
        retry_after: int,
        code: str = "RATE_LIMIT_EXCEEDED",
        **context: Any,
    ) -> AppError:
        """Create a rate-limit error (HTTP 429).

        Args:
            message: Human-readable description.
            retry_after: Seconds the caller should wait before retrying.
            code: Machine-readable error code from the taxonomy.
            **context: Arbitrary key-value pairs for debugging.
        """
        return self._create_error(
            code, message, http_status=429, retry_after=retry_after, **context
        )

    def internal(
        self,
        message: str,
        code: str = "INTERNAL_UNEXPECTED",
        **context: Any,
    ) -> AppError:
        """Create an internal error (HTTP 500).

        Args:
            message: Human-readable description.
            code: Machine-readable error code from the taxonomy.
            **context: Arbitrary key-value pairs for debugging.
        """
        return self._create_error(code, message, http_status=500, **context)

    # ------------------------------------------------------------------
    # Internal helper
    # ------------------------------------------------------------------

    def _create_error(
        self,
        code: str,
        message: str,
        *,
        http_status: int,
        **context: Any,
    ) -> AppError:
        """Build an ``AppError`` and log it.

        The correlation ID is read from the async-safe context variable.
        If no correlation ID is set (e.g., during startup), a fresh UUID
        is generated.
        """
        correlation_id = correlation_id_var.get(None) or str(uuid4())

        error = AppError(
            code=code,
            message=message,
            context=context,
            correlation_id=correlation_id,
            timestamp=datetime.now(timezone.utc),
            http_status=http_status,
        )

        # Log at ERROR level with full context.
        self._logger.error(
            f"Error created: [{code}] {message}",
            error_code=code,
            correlation_id=correlation_id,
            http_status=http_status,
            **{k: str(v) for k, v in context.items()},
        )

        return error
