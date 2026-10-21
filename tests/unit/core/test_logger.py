"""Unit tests for LogService.

Verifies structured JSON and text output, level filtering, correlation
ID injection, and context propagation.
"""

from __future__ import annotations

import json

from src.core.logger import LogService
from src.core.protocols.correlation import correlation_id_var
from tests.mocks.services import MockConfigService


class TestJsonFormat:
    """Tests for JSON-formatted log output."""

    def test_log_at_info_level(self, capsys: object) -> None:
        """INFO log produces JSON with message, level, and timestamp."""
        config = MockConfigService({"logging.level": "INFO", "logging.format": "json"})
        logger = LogService(config)

        logger.info("server started", port=8080)

        captured = capsys.readouterr()  # type: ignore[attr-defined]
        entry = json.loads(captured.out.strip())

        assert entry["message"] == "server started"
        assert entry["level"] == "INFO"
        assert "timestamp" in entry
        assert entry["port"] == "8080"

    def test_context_included(self, capsys: object) -> None:
        """Extra keyword arguments appear in the JSON output."""
        config = MockConfigService({"logging.level": "DEBUG", "logging.format": "json"})
        logger = LogService(config)

        logger.debug("processing request", user_id="abc", action="login")

        captured = capsys.readouterr()  # type: ignore[attr-defined]
        entry = json.loads(captured.out.strip())

        assert entry["user_id"] == "abc"
        assert entry["action"] == "login"

    def test_correlation_id_included(self, capsys: object) -> None:
        """When correlation_id_var is set, it appears in the log entry."""
        config = MockConfigService({"logging.level": "DEBUG", "logging.format": "json"})
        logger = LogService(config)

        token = correlation_id_var.set("cc_test_12345")
        try:
            logger.info("traced operation")
            captured = capsys.readouterr()  # type: ignore[attr-defined]
            entry = json.loads(captured.out.strip())
            assert entry["correlation_id"] == "cc_test_12345"
        finally:
            correlation_id_var.reset(token)

    def test_correlation_id_none_when_unset(self, capsys: object) -> None:
        """When no correlation ID is set, the field is null."""
        config = MockConfigService({"logging.level": "DEBUG", "logging.format": "json"})
        logger = LogService(config)

        # Ensure no correlation ID is set.
        token = correlation_id_var.set(None)
        try:
            logger.info("no trace")
            captured = capsys.readouterr()  # type: ignore[attr-defined]
            entry = json.loads(captured.out.strip())
            assert entry["correlation_id"] is None
        finally:
            correlation_id_var.reset(token)


class TestLevelFiltering:
    """Tests for log level threshold behaviour."""

    def test_log_below_threshold_suppressed(self, capsys: object) -> None:
        """Messages below the configured level produce no output."""
        config = MockConfigService({"logging.level": "WARN", "logging.format": "json"})
        logger = LogService(config)

        logger.info("should not appear")

        captured = capsys.readouterr()  # type: ignore[attr-defined]
        assert captured.out == ""
        assert captured.err == ""

    def test_log_at_threshold_emitted(self, capsys: object) -> None:
        """Messages at exactly the configured level are emitted."""
        config = MockConfigService({"logging.level": "WARN", "logging.format": "json"})
        logger = LogService(config)

        logger.warn("warning message")

        captured = capsys.readouterr()  # type: ignore[attr-defined]
        assert captured.out.strip() != ""
        entry = json.loads(captured.out.strip())
        assert entry["level"] == "WARN"

    def test_error_goes_to_stderr(self, capsys: object) -> None:
        """ERROR-level messages go to stderr, not stdout."""
        config = MockConfigService({"logging.level": "DEBUG", "logging.format": "json"})
        logger = LogService(config)

        logger.error("something broke")

        captured = capsys.readouterr()  # type: ignore[attr-defined]
        assert captured.out == ""
        assert captured.err.strip() != ""
        entry = json.loads(captured.err.strip())
        assert entry["level"] == "ERROR"


class TestTextFormat:
    """Tests for human-readable text output."""

    def test_text_format(self, capsys: object) -> None:
        """Text format produces a non-JSON, human-readable line."""
        config = MockConfigService({"logging.level": "INFO", "logging.format": "text"})
        logger = LogService(config)

        logger.info("ready")

        captured = capsys.readouterr()  # type: ignore[attr-defined]
        line = captured.out.strip()

        # Text output should NOT be valid JSON.
        is_json = True
        try:
            json.loads(line)
        except json.JSONDecodeError:
            is_json = False
        assert not is_json, "Expected non-JSON text output, but got valid JSON"

        assert "INFO" in line
        assert "ready" in line

    def test_text_format_with_context(self, capsys: object) -> None:
        """Text format includes key=value context pairs."""
        config = MockConfigService({"logging.level": "DEBUG", "logging.format": "text"})
        logger = LogService(config)

        logger.debug("processing", count=42)

        captured = capsys.readouterr()  # type: ignore[attr-defined]
        line = captured.out.strip()
        assert "count=42" in line
