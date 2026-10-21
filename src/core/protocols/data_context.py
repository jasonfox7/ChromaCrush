"""Data context protocol for ChromaCrush.

Provides async database session management. All data access flows through
the data context, which manages connection pooling and session lifecycle.
"""

from __future__ import annotations

from typing import AsyncContextManager, Protocol

from sqlalchemy.ext.asyncio import AsyncSession


class DataContextProtocol(Protocol):
    """Protocol for async database session management.

    The composition root creates a single DataContext at startup.
    Repositories receive it via __init__ injection.
    """

    def session(self) -> AsyncContextManager[AsyncSession]:
        """Get an async database session as a context manager.

        Usage:
            async with data_ctx.session() as session:
                result = await session.execute(query)

        The session is automatically committed on clean exit
        and rolled back on exception.
        """
        ...

    async def close(self) -> None:
        """Close the connection pool. Called during application shutdown."""
        ...
