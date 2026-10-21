"""Structured logging service.

Provides structured JSON (or human-readable text) logging to stdout/stderr.
The correlation ID is automatically injected from the ``correlation_id_var``
context variable so that every log entry can be traced back to its originating
request.

Startup sequence:
    logger = LogService(config)

Configuration keys:
    logging.level   -- minimum severity to emit (default "INFO")
    logging.format  -- "json" or "text" (default "json")
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from typing import Any, TextIO

from src.core.protocols.config import ConfigProtocol
from src.core.protocols.correlation import correlation_id_var


class LogService:
    """Structured logger satisfying ``LoggerProtocol``.

    Created once in the composition root; all other code receives it
    through ``__init__`` injection.
    """

    # Numeric severity levels, compatible with Python ``logging`` conventions.
    TRACE: int = 5
    DEBUG: int = 10
    INFO: int = 20
    WARN: int = 30
    ERROR: int = 40
    FATAL: int = 50

    LEVEL_MAP: dict[str, int] = {
        "TRACE": 5,
        "DEBUG": 10,
        "INFO": 20,
        "WARN": 30,
        "ERROR": 40,
        "FATAL": 50,
    }

    def __init__(self, config: ConfigProtocol) -> None:
        level_name: str = config.get("logging.level", "INFO")
        self._level: int = self.LEVEL_MAP.get(level_name.upper(), self.INFO)
        self._format: str = config.get("logging.format", "json")

    # ------------------------------------------------------------------
    # Public API (matches LoggerProtocol)
    # ------------------------------------------------------------------

    def trace(self, message: str, **context: object) -> None:
        """Log at TRACE level (step-by-step execution details)."""
        self._log(self.TRACE, "TRACE", message, **context)

    def debug(self, message: str, **context: object) -> None:
        """Log at DEBUG level (developer diagnostics)."""
        self._log(self.DEBUG, "DEBUG", message, **context)

    def info(self, message: str, **context: object) -> None:
        """Log at INFO level (normal operations)."""
        self._log(self.INFO, "INFO", message, **context)

    def warn(self, message: str, **context: object) -> None:
        """Log at WARN level (unexpected but recoverable)."""
        self._log(self.WARN, "WARN", message, **context)

    def error(self, message: str, **context: object) -> None:
        """Log at ERROR level (operation failed)."""
        self._log(self.ERROR, "ERROR", message, **context)

    def fatal(self, message: str, **context: object) -> None:
        """Log at FATAL level (unrecoverable failure)."""
        self._log(self.FATAL, "FATAL", message, **context)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _log(
        self, level: int, level_name: str, message: str, **context: object
    ) -> None:
        """Emit a log entry if *level* meets or exceeds the configured threshold."""
        if level < self._level:
            return

        correlation_id = correlation_id_var.get(None)

        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level_name,
            "message": message,
            "correlation_id": correlation_id,
        }
        # Merge caller context, coercing values to strings for safe
        # serialisation (complex objects, UUIDs, etc.).
        for key, value in context.items():
            entry[key] = _safe_str(value)

        # Route ERROR and above to stderr; everything else to stdout.
        dest: TextIO = sys.stderr if level >= self.ERROR else sys.stdout

        if self._format == "json":
            print(json.dumps(entry, default=str), file=dest, flush=True)
        else:
            ctx_str = (
                " ".join(f"{k}={v}" for k, v in context.items()) if context else ""
            )
            ts = entry["timestamp"]
            cid = f" cid={correlation_id}" if correlation_id else ""
            line = f"[{ts}] {level_name} {message}{cid} {ctx_str}".rstrip()
            print(line, file=dest, flush=True)


def _safe_str(value: object) -> str:
    """Convert *value* to a string, handling edge cases gracefully."""
    if isinstance(value, str):
        return value
    try:
        return str(value)
    except Exception:  # pragma: no cover
        return "<unserializable>"
