"""API schema definitions.

Pydantic v2 models for request/response validation and serialization.
"""

from src.modules.api.schemas.common import (
    ApiResponse,
    BotHint,
    ErrorDetail,
    ResponseMeta,
)

__all__ = [
    "ApiResponse",
    "BotHint",
    "ErrorDetail",
    "ResponseMeta",
]
