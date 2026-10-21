"""Unit tests for AppError and ErrorService.

Verifies error construction, serialisation, HTTP status codes, and
logger interaction.
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.core.errors import AppError
from src.core.error_service import ErrorService
from tests.mocks.services import MockLogService


class TestAppError:
    """Tests for the AppError dataclass."""

    def test_app_error_to_dict(self) -> None:
        """to_dict() returns the expected error response structure."""
        error = AppError(
            code="VALIDATION_INVALID_INPUT",
            message="Username too short",
            context={"min_length": 3},
            correlation_id="cc_test_abc",
            timestamp=datetime(2026, 2, 5, 12, 0, 0, tzinfo=timezone.utc),
            http_status=400,
        )

        result = error.to_dict()

        assert "error" in result
        assert result["error"]["code"] == "VALIDATION_INVALID_INPUT"
        assert result["error"]["message"] == "Username too short"
        assert result["error"]["correlation_id"] == "cc_test_abc"
        assert "2026-02-05" in result["error"]["timestamp"]

    def test_app_error_str(self) -> None:
        """str(error) returns '[CODE] message' format."""
        error = AppError(
            code="NOT_FOUND_RESOURCE",
            message="Player not found",
        )

        assert str(error) == "[NOT_FOUND_RESOURCE] Player not found"

    def test_app_error_repr(self) -> None:
        """repr(error) includes code, message, status, and correlation_id."""
        error = AppError(
            code="CONFLICT_STATE",
            message="Match already started",
            http_status=409,
            correlation_id="cc_repr_test",
        )

        r = repr(error)
        assert "CONFLICT_STATE" in r
        assert "Match already started" in r
        assert "409" in r
        assert "cc_repr_test" in r

    def test_app_error_is_exception(self) -> None:
        """AppError is a proper Exception subclass and can be raised/caught."""
        error = AppError(code="TEST", message="test error")
        try:
            raise error
        except AppError as caught:
            assert caught.code == "TEST"
        except Exception:
            raise AssertionError("AppError should be caught as AppError")


class TestErrorService:
    """Tests for the ErrorService factory methods."""

    def test_error_service_validation(self) -> None:
        """validation() returns an AppError with http_status=400."""
        logger = MockLogService()
        svc = ErrorService(logger)

        error = svc.validation("bad input")

        assert isinstance(error, AppError)
        assert error.http_status == 400
        assert error.code == "VALIDATION_INVALID_INPUT"
        assert error.message == "bad input"

    def test_error_service_not_found(self) -> None:
        """not_found() returns an AppError with http_status=404."""
        logger = MockLogService()
        svc = ErrorService(logger)

        error = svc.not_found("Player not found")

        assert error.http_status == 404
        assert error.code == "NOT_FOUND_RESOURCE"

    def test_error_service_unauthorized(self) -> None:
        """unauthorized() returns an AppError with http_status=401."""
        logger = MockLogService()
        svc = ErrorService(logger)

        error = svc.unauthorized("Invalid token")

        assert error.http_status == 401
        assert error.code == "AUTH_INVALID_CREDENTIALS"

    def test_error_service_forbidden(self) -> None:
        """forbidden() returns an AppError with http_status=403."""
        logger = MockLogService()
        svc = ErrorService(logger)

        error = svc.forbidden("Access denied")

        assert error.http_status == 403
        assert error.code == "FORBIDDEN_ACCESS_DENIED"

    def test_error_service_conflict(self) -> None:
        """conflict() returns an AppError with http_status=409."""
        logger = MockLogService()
        svc = ErrorService(logger)

        error = svc.conflict("Already exists")

        assert error.http_status == 409
        assert error.code == "CONFLICT_STATE"

    def test_error_service_rate_limited(self) -> None:
        """rate_limited() returns an AppError with http_status=429 and retry_after in context."""
        logger = MockLogService()
        svc = ErrorService(logger)

        error = svc.rate_limited("Too many requests", retry_after=60)

        assert error.http_status == 429
        assert error.code == "RATE_LIMIT_EXCEEDED"
        assert error.context["retry_after"] == 60

    def test_error_service_internal(self) -> None:
        """internal() returns an AppError with http_status=500."""
        logger = MockLogService()
        svc = ErrorService(logger)

        error = svc.internal("Unexpected failure")

        assert error.http_status == 500
        assert error.code == "INTERNAL_UNEXPECTED"

    def test_error_service_logs_error(self) -> None:
        """Each factory method logs at ERROR level via the injected logger."""
        logger = MockLogService()
        svc = ErrorService(logger)

        svc.validation("test logging")

        logger.assert_logged("ERROR", "VALIDATION_INVALID_INPUT")

    def test_error_service_custom_code(self) -> None:
        """Factory methods accept a custom error code."""
        logger = MockLogService()
        svc = ErrorService(logger)

        error = svc.validation(
            "Positions must be adjacent",
            code="VALIDATION_POSITIONS_NOT_ADJACENT",
        )

        assert error.code == "VALIDATION_POSITIONS_NOT_ADJACENT"

    def test_error_service_context_passed_through(self) -> None:
        """Extra kwargs are stored in the error's context dict."""
        logger = MockLogService()
        svc = ErrorService(logger)

        error = svc.not_found(
            "Player not found",
            player_id="abc-123",
        )

        assert error.context["player_id"] == "abc-123"

    def test_error_service_correlation_id_set(self) -> None:
        """Errors always have a non-empty correlation ID."""
        logger = MockLogService()
        svc = ErrorService(logger)

        error = svc.internal("test")

        assert error.correlation_id is not None
        assert len(error.correlation_id) > 0
