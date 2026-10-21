"""Mock service implementations for unit testing.

These mocks satisfy the protocol interfaces without requiring real
database connections, Redis, or external services.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from src.core.errors import AppError
from src.core.protocols.logger import LoggerProtocol


class MockConfigService:
    """In-memory configuration mock satisfying ``ConfigProtocol``.

    Initialised with sensible defaults for all configuration sections.
    Pass *overrides* to replace or extend individual keys.

    Usage::

        config = MockConfigService({"game.board_width": 10})
        assert config.get("game.board_width") == 10
    """

    _DEFAULTS: dict[str, Any] = {
        "app": {
            "name": "ChromaCrush",
            "version": "0.1.0",
            "environment": "test",
            "debug": True,
        },
        "game": {
            "board_width": 8,
            "board_height": 8,
            "gem_types": 6,
            "moves_per_match": 20,
        },
        "logging": {
            "level": "DEBUG",
            "format": "text",
        },
        "database": {
            "host": "localhost",
            "port": 5432,
            "name": "chromacrush_test",
            "user": "chromacrush",
            "password": "",
            "pool_size": 2,
        },
        "redis": {
            "host": "localhost",
            "port": 6379,
            "key_prefix": "chromacrush_test:",
        },
        "auth": {
            "jwt_secret": "test-secret-key-for-unit-tests",
            "jwt_expiry_minutes": 60,
            "api_key_prefix": "cc_",
        },
        "matchmaking": {
            "elo_initial": 1000,
            "elo_k_factor": 32,
            "queue_max_size": 10000,
            "elo_range_initial": 50,
            "elo_range_max": 500,
            "elo_expansion_interval_seconds": 10,
            "elo_expansion_step": 50,
            "match_timeout_seconds": 300,
            "queue_poll_interval_ms": 500,
        },
        "energy": {
            "max_hearts": 5,
            "regen_interval_minutes": 30,
        },
        "websocket": {
            "enabled": True,
            "path": "/ws",
            "heartbeat_interval_seconds": 30,
            "connection_timeout_seconds": 60,
            "max_connections_per_player": 3,
            "max_message_size_bytes": 65536,
            "rate_limit_messages_per_second": 10,
        },
        "features": {
            "experimental_near_miss_tuning": {
                "enabled": False,
                "lifecycle": "experimental",
            },
            "vault_raids": {"enabled": True, "lifecycle": "stable"},
        },
    }

    def __init__(self, overrides: dict[str, Any] | None = None) -> None:
        import copy

        self._data: dict[str, Any] = copy.deepcopy(self._DEFAULTS)

        if overrides:
            for key, value in overrides.items():
                self._set_nested(key, value)

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value by dot-notation key."""
        return self._traverse(key, default=default, raise_missing=False)

    def require(self, key: str) -> Any:
        """Retrieve a value by dot-notation key, raising on absence."""
        return self._traverse(key, default=None, raise_missing=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _traverse(self, key: str, *, default: Any, raise_missing: bool) -> Any:
        """Walk the nested dict along a dot-separated path."""
        parts = key.split(".")
        node: Any = self._data
        for part in parts:
            if isinstance(node, dict) and part in node:
                node = node[part]
            elif raise_missing:
                raise KeyError(f"Required configuration key not found: {key!r}")
            else:
                return default
        return node

    def _set_nested(self, key: str, value: Any) -> None:
        """Set a value in the nested dict using dot-notation."""
        parts = key.split(".")
        node = self._data
        for part in parts[:-1]:
            if part not in node or not isinstance(node[part], dict):
                node[part] = {}
            node = node[part]
        node[parts[-1]] = value


class MockLogService:
    """In-memory logger mock satisfying ``LoggerProtocol``.

    Captures all log entries for assertion in tests.

    Usage::

        logger = MockLogService()
        logger.info("something happened", user_id="abc")
        logger.assert_logged("INFO", "something")
    """

    def __init__(self) -> None:
        self.entries: list[dict[str, Any]] = []

    def trace(self, message: str, **context: object) -> None:
        """Log at TRACE level."""
        self._record("TRACE", message, context)

    def debug(self, message: str, **context: object) -> None:
        """Log at DEBUG level."""
        self._record("DEBUG", message, context)

    def info(self, message: str, **context: object) -> None:
        """Log at INFO level."""
        self._record("INFO", message, context)

    def warn(self, message: str, **context: object) -> None:
        """Log at WARN level."""
        self._record("WARN", message, context)

    def error(self, message: str, **context: object) -> None:
        """Log at ERROR level."""
        self._record("ERROR", message, context)

    def fatal(self, message: str, **context: object) -> None:
        """Log at FATAL level."""
        self._record("FATAL", message, context)

    # ------------------------------------------------------------------
    # Test helpers
    # ------------------------------------------------------------------

    def assert_logged(self, level: str, message_contains: str) -> None:
        """Assert that at least one log entry matches *level* and contains *message_contains*.

        Raises:
            AssertionError: If no matching entry is found.
        """
        for entry in self.entries:
            if entry["level"] == level and message_contains in entry["message"]:
                return
        messages = [f"  [{e['level']}] {e['message']}" for e in self.entries]
        raise AssertionError(
            f"No log entry found with level={level!r} containing {message_contains!r}.\n"
            f"Recorded entries:\n" + "\n".join(messages)
        )

    def clear(self) -> None:
        """Clear all recorded entries."""
        self.entries.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _record(self, level: str, message: str, context: dict[str, object]) -> None:
        self.entries.append(
            {
                "level": level,
                "message": message,
                "context": context,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )


class MockErrorService:
    """Error factory mock satisfying ``ErrorServiceProtocol``.

    Creates real ``AppError`` instances with the same HTTP status codes
    as the production ``ErrorService``, but without live logging side
    effects (uses ``MockLogService`` by default).
    """

    def __init__(self, logger: LoggerProtocol | None = None) -> None:
        self._logger: LoggerProtocol = logger or MockLogService()

    def validation(
        self,
        message: str,
        code: str = "VALIDATION_INVALID_INPUT",
        **context: Any,
    ) -> AppError:
        """Create a validation error (HTTP 400)."""
        return self._create_error(code, message, http_status=400, **context)

    def not_found(
        self,
        message: str,
        code: str = "NOT_FOUND_RESOURCE",
        **context: Any,
    ) -> AppError:
        """Create a not-found error (HTTP 404)."""
        return self._create_error(code, message, http_status=404, **context)

    def unauthorized(
        self,
        message: str,
        code: str = "AUTH_INVALID_CREDENTIALS",
        **context: Any,
    ) -> AppError:
        """Create an authentication error (HTTP 401)."""
        return self._create_error(code, message, http_status=401, **context)

    def forbidden(
        self,
        message: str,
        code: str = "FORBIDDEN_ACCESS_DENIED",
        **context: Any,
    ) -> AppError:
        """Create an authorisation error (HTTP 403)."""
        return self._create_error(code, message, http_status=403, **context)

    def conflict(
        self,
        message: str,
        code: str = "CONFLICT_STATE",
        **context: Any,
    ) -> AppError:
        """Create a conflict error (HTTP 409)."""
        return self._create_error(code, message, http_status=409, **context)

    def rate_limited(
        self,
        message: str,
        retry_after: int,
        code: str = "RATE_LIMIT_EXCEEDED",
        **context: Any,
    ) -> AppError:
        """Create a rate-limit error (HTTP 429)."""
        return self._create_error(
            code, message, http_status=429, retry_after=retry_after, **context
        )

    def internal(
        self,
        message: str,
        code: str = "INTERNAL_UNEXPECTED",
        **context: Any,
    ) -> AppError:
        """Create an internal error (HTTP 500)."""
        return self._create_error(code, message, http_status=500, **context)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _create_error(
        self,
        code: str,
        message: str,
        *,
        http_status: int,
        **context: Any,
    ) -> AppError:
        """Build an ``AppError`` and log it via the injected logger."""
        correlation_id = str(uuid4())

        error = AppError(
            code=code,
            message=message,
            context=context,
            correlation_id=correlation_id,
            timestamp=datetime.now(timezone.utc),
            http_status=http_status,
        )

        self._logger.error(
            f"Error created: [{code}] {message}",
            error_code=code,
            correlation_id=correlation_id,
            http_status=http_status,
            **{k: str(v) for k, v in context.items()},
        )

        return error
