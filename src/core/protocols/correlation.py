"""Correlation ID context variable and protocol.

The correlation_id_var ContextVar is the async-safe mechanism for propagating
correlation IDs through the call stack. Middleware sets it at request entry;
logger and error service read it automatically.

Format: cc_{timestamp_hex}_{random_hex}
Example: cc_18d4f2a8_7b3e9c1d
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Protocol

# Context variable for async-safe correlation ID propagation.
# Set by middleware at request entry, read by logger and error service.
correlation_id_var: ContextVar[str | None] = ContextVar("correlation_id", default=None)


class CorrelationContextProtocol(Protocol):
    """Protocol for correlation ID management."""

    def get_id(self) -> str:
        """Get current correlation ID. Creates one if none exists."""
        ...

    def set_id(self, correlation_id: str) -> None:
        """Set correlation ID for current context."""
        ...

    def clear(self) -> None:
        """Clear correlation ID from context."""
        ...
