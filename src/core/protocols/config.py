"""Configuration service protocol.

All modules receive configuration through this protocol interface.
The concrete ConfigService is created once in the composition root.
"""

from __future__ import annotations

from typing import Any, Protocol


class ConfigProtocol(Protocol):
    """Protocol for the configuration service. Injected into all modules.

    Provides dot-notation access to nested configuration values.
    Example: config.get("database.host") or config.require("auth.jwt_secret")
    """

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by dot-notation key.

        Args:
            key: Dot-separated path into the config tree (e.g., "database.host").
            default: Value to return if key is not found.

        Returns:
            The config value, or the default if not found.
        """
        ...

    def require(self, key: str) -> Any:
        """Get a configuration value, raising if not found.

        Args:
            key: Dot-separated path into the config tree.

        Returns:
            The config value.

        Raises:
            KeyError: If the key does not exist in the configuration.
        """
        ...
