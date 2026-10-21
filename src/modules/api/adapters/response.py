"""Response adapter for constructing standard API envelope responses.

All API responses -- success and error -- flow through this adapter to
ensure a consistent JSON structure with correlation ID and timestamp.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from src.modules.api.schemas.common import (
    ApiResponse,
    ErrorDetail,
    ResponseMeta,
)


class ResponseAdapter:
    """Adapts domain objects into the standard ApiResponse envelope."""

    def success(
        self,
        data: Any,
        correlation_id: str,
    ) -> dict[str, Any]:
        """Create a successful response envelope.

        Args:
            data: The payload to include in the response.
            correlation_id: Request trace identifier.

        Returns:
            Dict matching the ApiResponse schema.
        """
        response = ApiResponse(
            success=True,
            data=data,
            error=None,
            meta=ResponseMeta(
                correlation_id=correlation_id,
                timestamp=datetime.now(timezone.utc),
            ),
        )
        return response.model_dump(mode="json")

    def error(
        self,
        code: str,
        message: str,
        correlation_id: str,
        details: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create an error response envelope.

        Args:
            code: Machine-readable error code.
            message: Human-readable error description.
            correlation_id: Request trace identifier.
            details: Optional additional error context.

        Returns:
            Dict matching the ApiResponse schema with error detail.
        """
        response = ApiResponse(
            success=False,
            data=None,
            error=ErrorDetail(
                code=code,
                message=message,
                details=details,
            ),
            meta=ResponseMeta(
                correlation_id=correlation_id,
                timestamp=datetime.now(timezone.utc),
            ),
        )
        return response.model_dump(mode="json")
