"""Unit tests for ConfigService.

Verifies TOML loading, dot-notation access, defaults, and missing-key
behaviour using the real ConfigService against the project's
``config/app.toml``.
"""

from __future__ import annotations

import pytest

from src.core.config import ConfigService


class TestConfigLoad:
    """Tests for loading configuration from TOML files."""

    def test_load_from_toml(self) -> None:
        """ConfigService.load() reads config/app.toml successfully."""
        config = ConfigService.load("config/app.toml")
        assert config.get("app.name") == "ChromaCrush"

    def test_load_nonexistent_file_raises(self) -> None:
        """Loading a nonexistent TOML file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            ConfigService.load("config/does_not_exist.toml")


class TestGetWithDefault:
    """Tests for the get() method with default values."""

    def test_get_with_default_returns_fallback(self) -> None:
        """get() returns the default when the key is absent."""
        config = ConfigService.load("config/app.toml")
        assert config.get("nonexistent.key", "fallback") == "fallback"

    def test_get_with_default_none(self) -> None:
        """get() returns None by default when the key is absent."""
        config = ConfigService.load("config/app.toml")
        assert config.get("nonexistent.key") is None


class TestRequire:
    """Tests for the require() method."""

    def test_require_missing_key_raises(self) -> None:
        """require() raises KeyError for a missing key."""
        config = ConfigService.load("config/app.toml")
        with pytest.raises(KeyError, match="nonexistent"):
            config.require("nonexistent")

    def test_require_existing_key(self) -> None:
        """require() returns the value when the key exists."""
        config = ConfigService.load("config/app.toml")
        assert config.require("app.name") == "ChromaCrush"


class TestDotNotation:
    """Tests for dot-notation traversal of nested config values."""

    def test_dot_notation_access(self) -> None:
        """get() walks dot-separated paths into nested dicts."""
        config = ConfigService.load("config/app.toml")
        assert config.get("database.host") == "localhost"

    def test_nested_access(self) -> None:
        """Deeply nested values are accessible by dot notation."""
        config = ConfigService.load("config/app.toml")
        assert config.get("game.board_width") == 8
        assert config.get("game.board_height") == 8
        assert config.get("game.gem_types") == 6
        assert config.get("game.moves_per_match") == 20

    def test_section_returns_dict(self) -> None:
        """Accessing a section key returns the nested dict."""
        config = ConfigService.load("config/app.toml")
        database_section = config.get("database")
        assert isinstance(database_section, dict)
        assert "host" in database_section
        assert "port" in database_section
