from __future__ import annotations

from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class PaginatedResult(Generic[T]):
    """Paginated query result with metadata.

    Used by repository and service layers to return paginated lists.
    """

    items: list[T]
    total: int
    limit: int
    offset: int

    @property
    def has_more(self) -> bool:
        """Return True if there are more items beyond the current page."""
        return self.offset + len(self.items) < self.total
