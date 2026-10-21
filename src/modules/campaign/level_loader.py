"""Load and cache campaign level definitions from JSON.

Loaded once at service init. Provides level lookup by number.
"""

from __future__ import annotations

import json
from pathlib import Path

# Default path relative to project root.
_DEFAULT_LEVELS_PATH = (
    Path(__file__).resolve().parents[3] / "config" / "campaign_levels.json"
)


class LevelLoader:
    """In-memory cache of campaign level definitions.

    Args:
        path: Path to campaign_levels.json. Uses default if None.
    """

    def __init__(self, path: str | Path | None = None) -> None:
        levels_path = Path(path) if path else _DEFAULT_LEVELS_PATH

        with open(levels_path, encoding="utf-8") as f:
            raw: list[dict] = json.load(f)

        # Index by level number for O(1) lookup.
        self._levels: dict[int, dict] = {lvl["level"]: lvl for lvl in raw}

    def get(self, level_number: int) -> dict | None:
        """Get a level definition by number.

        Returns:
            Level dict or None if not found.
        """
        return self._levels.get(level_number)

    @property
    def max_level(self) -> int:
        """Highest level number available."""
        return max(self._levels.keys()) if self._levels else 0

    @property
    def count(self) -> int:
        """Total number of levels."""
        return len(self._levels)
