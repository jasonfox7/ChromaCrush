"""Common API schemas used across all endpoint groups.

Defines the standard response envelope, error detail structure, response
metadata, and bot hint model. All responses are wrapped in ApiResponse[T].

Uses Pydantic v2 patterns (model_config = ConfigDict).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ResponseMeta(BaseModel):
    """Metadata included in every API response."""

    model_config = ConfigDict(frozen=True)

    correlation_id: str
    timestamp: datetime
    version: str = "1.0"


class ErrorDetail(BaseModel):
    """Structured error information for failed requests."""

    model_config = ConfigDict(frozen=True)

    code: str
    message: str
    details: dict[str, Any] | None = None


class BotHint(BaseModel):
    """Bot-specific hints included in match-related responses.

    Only populated when the request is authenticated via API key
    and the ``api.bot_hints_enabled`` config flag is true.
    """

    model_config = ConfigDict(frozen=True)

    recommended_action: str | None = None
    urgency: str | None = None  # "low", "medium", "high", "critical"
    context: dict[str, Any] | None = None


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response envelope wrapping all endpoints.

    Every response -- success or error -- uses this envelope to provide
    a consistent structure for both human and bot clients.
    """

    model_config = ConfigDict(from_attributes=True)

    success: bool
    data: T | None = None
    error: ErrorDetail | None = None
    meta: ResponseMeta
