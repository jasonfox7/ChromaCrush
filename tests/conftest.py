"""Root test configuration and shared fixtures.

Provides mock services that match the protocol interfaces for use in
unit tests. All mocks follow the testing-standards.md guidance.
"""

from __future__ import annotations

import pytest

from tests.mocks.services import MockConfigService, MockErrorService, MockLogService


@pytest.fixture
def mock_config() -> MockConfigService:
    """Provide a MockConfigService with reasonable defaults.

    Override individual keys via the *overrides* parameter::

        def test_custom(mock_config):
            custom = MockConfigService({"game.board_width": 10})
    """
    return MockConfigService()


@pytest.fixture
def mock_logger() -> MockLogService:
    """Provide a MockLogService that records all log entries."""
    return MockLogService()


@pytest.fixture
def mock_errors(mock_logger: MockLogService) -> MockErrorService:
    """Provide a MockErrorService backed by the mock logger."""
    return MockErrorService(mock_logger)
