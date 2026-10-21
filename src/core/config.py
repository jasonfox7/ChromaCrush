"""Configuration service.

Loads configuration from TOML files and environment variables, providing
dot-notation access to nested values. This is one of the few places in
the codebase that directly accesses ``os.environ`` -- all other code
receives configuration through the injected ``ConfigProtocol``.

Source priority (highest to lowest):
    1. Environment variables (SECTION_KEY or CHROMACRUSH_SECTION_KEY)
    2. Environment-specific TOML file (config/app.{environment}.toml)
    3. Base TOML file (config/app.toml)
    4. Hardcoded defaults in consuming code

Startup sequence:
    config = ConfigService.load("config/app.toml")
"""

from __future__ import annotations

import os
import tomllib
from copy import deepcopy
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


class ConfigService:
    """Hierarchical configuration backed by TOML files and env vars.

    Satisfies ``ConfigProtocol``. Created once in the composition root
    via the ``load`` classmethod; all other code receives it through
    ``__init__`` injection.
    """

    # Prefix checked for env var overrides (in addition to bare key).
    _ENV_PREFIX = "CHROMACRUSH_"

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @classmethod
    def load(cls, config_path: str = "config/app.toml") -> ConfigService:
        """Load configuration from disk and environment.

        Args:
            config_path: Path to the base TOML configuration file.

        Returns:
            A fully-resolved ConfigService instance.

        Raises:
            FileNotFoundError: If the base config file does not exist.
        """
        # 1. Load .env file for local development (no-op if missing).
        load_dotenv()

        # 2. Parse the base TOML file.
        path = Path(config_path)
        with open(path, "rb") as f:
            data: dict[str, Any] = tomllib.load(f)

        # 3. Determine the active environment.
        environment = os.environ.get(
            "APP_ENVIRONMENT",
            data.get("app", {}).get("environment", "development"),
        )
        # Store resolved environment back into the tree.
        data.setdefault("app", {})["environment"] = environment

        # 4. Deep-merge the environment-specific override file (if present).
        env_path = path.parent / f"app.{environment}.toml"
        if env_path.exists():
            with open(env_path, "rb") as f:
                env_data: dict[str, Any] = tomllib.load(f)
            data = cls._deep_merge(data, env_data)

        # 5. Apply environment variable overrides on top.
        data = cls._apply_env_overrides(data)

        return cls(data)

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve a value by dot-notation key.

        Args:
            key: Dot-separated path (e.g., "database.host").
            default: Returned when the key is absent.

        Returns:
            The resolved value, or *default* if not found.
        """
        return self._traverse(key, default=default, raise_missing=False)

    def require(self, key: str) -> Any:
        """Retrieve a value by dot-notation key, raising on absence.

        Args:
            key: Dot-separated path (e.g., "auth.jwt_secret").

        Returns:
            The resolved value.

        Raises:
            KeyError: If the key does not exist anywhere in the config tree.
        """
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

    @staticmethod
    def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Recursively merge *override* into a copy of *base*.

        Scalar values in *override* replace those in *base*. Nested dicts
        are merged recursively. The original dicts are never mutated.
        """
        merged = deepcopy(base)
        for key, value in override.items():
            if (
                key in merged
                and isinstance(merged[key], dict)
                and isinstance(value, dict)
            ):
                merged[key] = ConfigService._deep_merge(merged[key], value)
            else:
                merged[key] = deepcopy(value)
        return merged

    @classmethod
    def _apply_env_overrides(cls, data: dict[str, Any]) -> dict[str, Any]:
        """Override leaf values with matching environment variables.

        For every leaf key in the config tree the method checks for two
        env-var forms:

        * ``SECTION_KEY`` -- e.g., ``DATABASE_HOST``
        * ``CHROMACRUSH_SECTION_KEY`` -- e.g., ``CHROMACRUSH_DATABASE_HOST``

        The prefixed form takes priority over the bare form.

        Type coercion:
        * ``"true"`` / ``"false"`` (case-insensitive) -> bool
        * Strings that look like integers -> int
        * Strings that look like floats -> float
        * Everything else stays as str
        """
        result = deepcopy(data)
        cls._apply_env_recursive(result, prefix_parts=[])
        return result

    @classmethod
    def _apply_env_recursive(
        cls, node: dict[str, Any], prefix_parts: list[str]
    ) -> None:
        """Recursively walk *node* and apply env overrides in-place."""
        for key, value in list(node.items()):
            current_parts = prefix_parts + [key]
            if isinstance(value, dict):
                cls._apply_env_recursive(value, current_parts)
            else:
                env_key = "_".join(current_parts).upper()
                prefixed_env_key = cls._ENV_PREFIX + env_key

                # Prefixed form takes priority.
                env_value = os.environ.get(prefixed_env_key) or os.environ.get(env_key)
                if env_value is not None:
                    node[key] = cls._coerce_type(env_value, value)

    @staticmethod
    def _coerce_type(env_value: str, original: Any) -> Any:
        """Coerce an env-var string to the same type as *original*.

        Falls back to heuristic type detection when *original* is already
        a string or when the type is unknown.
        """
        # Match the type of the existing config value when possible.
        if isinstance(original, bool):
            return env_value.lower() in ("true", "1", "yes")
        if isinstance(original, int):
            try:
                return int(env_value)
            except ValueError:
                return env_value
        if isinstance(original, float):
            try:
                return float(env_value)
            except ValueError:
                return env_value

        # Heuristic coercion for string-typed originals or new keys.
        lower = env_value.lower()
        if lower in ("true", "false"):
            return lower == "true"
        try:
            return int(env_value)
        except ValueError:
            pass
        try:
            return float(env_value)
        except ValueError:
            pass
        return env_value
