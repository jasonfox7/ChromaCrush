"""Shared PasswordStore implementations for CLI commands.

Two variants are provided:

- ``CLIPasswordStore`` — queries the ``PlayerModel`` table directly.
  Used by auth and match CLI commands that need real password operations.

- ``StubPasswordStore`` — no-op implementation for CLI commands that
  require ``AuthService`` but never exercise password operations
  (e.g. events commands).
"""

from __future__ import annotations

from uuid import UUID


class CLIPasswordStore:
    """PasswordStore that queries PlayerModel.password_hash via SQLAlchemy."""

    def __init__(self, data_ctx: object) -> None:
        self._data_ctx = data_ctx

    async def get_password_hash(self, player_id: UUID) -> str | None:
        from sqlalchemy import select

        from src.data.models.player import PlayerModel

        async with self._data_ctx.session() as session:
            stmt = select(PlayerModel.password_hash).where(PlayerModel.id == player_id)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()

    async def set_password_hash(self, player_id: UUID, password_hash: str) -> None:
        from sqlalchemy import update

        from src.data.models.player import PlayerModel

        async with self._data_ctx.session() as session:
            stmt = (
                update(PlayerModel)
                .where(PlayerModel.id == player_id)
                .values(password_hash=password_hash)
            )
            await session.execute(stmt)


class StubPasswordStore:
    """No-op PasswordStore for CLI commands that don't need password operations."""

    def __init__(self, data_ctx: object) -> None:
        self._data_ctx = data_ctx

    async def get_password_hash(self, player_id: UUID) -> str | None:
        return None

    async def set_password_hash(self, player_id: UUID, password_hash: str) -> None:
        pass
