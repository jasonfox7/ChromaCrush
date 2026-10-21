"""Logger service protocol.

All modules receive logging through this protocol interface.
The concrete LogService is created once in the composition root.
Correlation IDs are injected automatically by the implementation.
"""

from __future__ import annotations

from typing import Protocol


class LoggerProtocol(Protocol):
    """Protocol for the structured logger. Injected into all modules.

    All log methods accept a message string and arbitrary keyword context
    that will be included in the structured log output.
    """

    def trace(self, message: str, **context: object) -> None:
        """Log at TRACE level (step-by-step execution details)."""
        ...

    def debug(self, message: str, **context: object) -> None:
        """Log at DEBUG level (developer diagnostics)."""
        ...

    def info(self, message: str, **context: object) -> None:
        """Log at INFO level (normal operations)."""
        ...

    def warn(self, message: str, **context: object) -> None:
        """Log at WARN level (unexpected but recoverable)."""
        ...

    def error(self, message: str, **context: object) -> None:
        """Log at ERROR level (operation failed)."""
        ...

    def fatal(self, message: str, **context: object) -> None:
        """Log at FATAL level (unrecoverable failure)."""
        ...
