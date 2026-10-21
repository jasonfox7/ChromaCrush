"""Global exception handler for the API.

Catches ``AppError`` instances raised by services and maps them to
structured HTTP responses. The error code prefix determines the HTTP
status code:

    VALIDATION_*  -> 400
    AUTH_*        -> 401
    FORBIDDEN_*   -> 403
    NOT_FOUND_*   -> 404
    CONFLICT_*    -> 409
    RATE_LIMIT_*  -> 429
    INTERNAL_*    -> 500

Unhandled exceptions are mapped to 500 with a generic error message.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, Request
from starlette.responses import JSONResponse

from src.core.errors import AppError

# Prefix -> HTTP status code mapping
_ERROR_PREFIX_TO_STATUS: dict[str, int] = {
    "VALIDATION": 400,
    "AUTH": 401,
    "FORBIDDEN": 403,
    "NOT_FOUND": 404,
    "CONFLICT": 409,
    "RATE_LIMIT": 429,
    "INTERNAL": 500,
}

_DEFAULT_HTTP_STATUS = 500


def register_error_handlers(app: FastAPI) -> None:
    """Register exception handlers on the FastAPI application.

    Args:
        app: The FastAPI application instance.
    """

    @app.exception_handler(AppError)
    async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
        """Map AppError to a structured JSON response.

        Args:
            request: The current HTTP request.
            exc: The application error.

        Returns:
            JSONResponse with the appropriate HTTP status code.
        """
        status_code = _resolve_status_code(exc.code)
        correlation_id = getattr(request.state, "correlation_id", exc.correlation_id)

        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.context if exc.context else None,
                },
                "meta": {
                    "correlation_id": correlation_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "version": "1.0",
                },
            },
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request,
        exc: Exception,
    ) -> JSONResponse:
        """Catch-all for unhandled exceptions.

        Args:
            request: The current HTTP request.
            exc: The unhandled exception.

        Returns:
            JSONResponse with 500 status and generic error message.
        """
        correlation_id = getattr(
            request.state,
            "correlation_id",
            "unknown",
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "error": {
                    "code": "INTERNAL_UNEXPECTED",
                    "message": "An unexpected error occurred",
                    "details": None,
                },
                "meta": {
                    "correlation_id": correlation_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "version": "1.0",
                },
            },
        )


def _resolve_status_code(error_code: str) -> int:
    """Map an error code prefix to an HTTP status code.

    Args:
        error_code: The full error code (e.g., "VALIDATION_OUT_OF_BOUNDS").

    Returns:
        HTTP status code integer.
    """
    for prefix, status in _ERROR_PREFIX_TO_STATUS.items():
        if error_code.startswith(prefix):
            return status
    return _DEFAULT_HTTP_STATUS
