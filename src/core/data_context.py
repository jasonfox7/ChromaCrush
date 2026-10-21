"""Async database session management with PostgreSQL and Redis.

Created once in the composition root via async factory method.
All repositories receive this through ``__init__`` injection.

Startup:
    data_ctx = await DataContext.create(config, logger, errors)

Shutdown:
    await data_ctx.close()

Configuration keys (from ``config/app.toml``):
    database.host, database.port, database.name, database.user,
    database.password, database.pool_size, redis.host, redis.port
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

if TYPE_CHECKING:
    from redis.asyncio import Redis

    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol


class DataContext:
    """Async database session and Redis client manager.

    Satisfies ``DataContextProtocol``. Created once in the composition root
    via the ``create`` async classmethod; all repositories receive it through
    ``__init__`` injection.
    """

    def __init__(
        self,
        engine: AsyncEngine,
        session_factory: async_sessionmaker[AsyncSession],
        redis_client: Redis,
        logger: LoggerProtocol,
    ) -> None:
        self._engine = engine
        self._session_factory = session_factory
        self._redis_client = redis_client
        self._logger = logger

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    async def create(
        cls,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
    ) -> DataContext:
        """Create a fully-initialised DataContext.

        Reads connection parameters from the injected ``ConfigProtocol``,
        creates the SQLAlchemy async engine + session factory and a Redis
        client.

        Args:
            config: Application configuration (``ConfigProtocol``).
            logger: Structured logger (``LoggerProtocol``).
            errors: Error factory (``ErrorServiceProtocol``).

        Returns:
            A ready-to-use ``DataContext`` instance.
        """
        import redis.asyncio as aioredis

        # ---- PostgreSQL ------------------------------------------------
        db_host: str = config.get("database.host", "localhost")
        db_port: int = config.get("database.port", 5432)
        db_name: str = config.get("database.name", "chromacrush")
        db_user: str = config.get("database.user", "chromacrush")
        db_password: str = config.get("database.password", "")
        db_pool_size: int = config.get("database.pool_size", 5)

        database_url = (
            f"postgresql+asyncpg://{db_user}:{db_password}"
            f"@{db_host}:{db_port}/{db_name}"
        )

        engine = create_async_engine(
            database_url,
            pool_size=db_pool_size,
            echo=False,
        )

        session_factory = async_sessionmaker(
            bind=engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

        logger.info(
            "PostgreSQL connection pool created",
            host=db_host,
            port=db_port,
            database=db_name,
            pool_size=db_pool_size,
        )

        # ---- Redis -----------------------------------------------------
        redis_host: str = config.get("redis.host", "localhost")
        redis_port: int = config.get("redis.port", 6379)

        redis_url = f"redis://{redis_host}:{redis_port}"
        redis_client: Redis = aioredis.Redis.from_url(
            redis_url,
            decode_responses=True,
        )

        logger.info(
            "Redis client created",
            host=redis_host,
            port=redis_port,
        )

        return cls(engine, session_factory, redis_client, logger)

    # ------------------------------------------------------------------
    # Public API (matches DataContextProtocol)
    # ------------------------------------------------------------------

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        """Get an async database session as a context manager.

        The session is automatically committed on clean exit and rolled back
        on exception. It is always closed when the context manager exits.

        Usage::

            async with data_ctx.session() as session:
                result = await session.execute(query)
        """
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    @property
    def redis(self) -> Redis:
        """Return the Redis client for cache and queue operations."""
        return self._redis_client

    async def close(self) -> None:
        """Dispose of the engine pool and close the Redis connection.

        Called during application shutdown.
        """
        self._logger.info("Closing data context connections")
        await self._engine.dispose()
        await self._redis_client.aclose()
        self._logger.info("Data context connections closed")
