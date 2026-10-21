"""Integration tests for ad-free status and bot earnings flows.

Validates AdService ad-free management and BotEarningsService balance/sync
using real PostgreSQL and Redis.
"""

from __future__ import annotations

import pytest

from src.core.errors import AppError
from src.core.types.game import PlayerId
from src.core.types.player import PlayerType
from src.modules.ads.types import AdFreeReason

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_player(factory, username="alice", player_type=PlayerType.HUMAN):
    p = await factory.player_service.create_player(
        username=username,
        player_type=player_type,
    )
    return PlayerId(p.id)


# ---------------------------------------------------------------------------
# Ad-Free Status Tests
# ---------------------------------------------------------------------------


class TestAdFreeStatus:
    """Tests for AdService ad-free status management."""

    async def test_check_ad_free_status_default_false(self, factory):
        """New player is not ad-free by default."""
        player_id = await _create_player(factory)

        status = await factory.ad_service.check_ad_free_status(player_id)

        assert status.is_ad_free is False
        assert status.player_id == player_id

    async def test_grant_ad_free_status_happy_path(self, factory):
        """Granting ad-free status sets is_ad_free to True."""
        player_id = await _create_player(factory)

        result = await factory.ad_service.grant_ad_free_status(
            player_id,
            reason=AdFreeReason.PURCHASE,
        )

        assert result.is_ad_free is True
        assert result.player_id == player_id

        # Verify it persists
        check = await factory.ad_service.check_ad_free_status(player_id)
        assert check.is_ad_free is True

    async def test_grant_ad_free_with_duration(self, factory):
        """Granting ad-free with duration_days sets expiry."""
        player_id = await _create_player(factory)

        result = await factory.ad_service.grant_ad_free_status(
            player_id,
            reason=AdFreeReason.TRIAL,
            duration_days=30,
        )

        assert result.is_ad_free is True
        assert result.expires_at is not None

    async def test_check_ad_free_player_not_found(self, factory):
        """Checking ad-free for nonexistent player raises NOT_FOUND_PLAYER."""
        from uuid import UUID

        fake_id = PlayerId(UUID("00000000-0000-0000-0000-000000000099"))

        with pytest.raises(AppError) as exc_info:
            await factory.ad_service.check_ad_free_status(fake_id)

        assert "NOT_FOUND" in exc_info.value.code


# ---------------------------------------------------------------------------
# Bot Earnings Tests
# ---------------------------------------------------------------------------


class TestBotEarnings:
    """Tests for BotEarningsService balance and sync."""

    async def test_bot_earnings_balance_zero_initially(self, factory):
        """New bot has zero earnings balance."""
        bot_id = await _create_player(
            factory,
            username="testbot",
            player_type=PlayerType.BOT,
        )

        balance = await factory.bot_earnings_service.get_earnings_balance(bot_id)

        assert balance.bot_player_id == bot_id
        assert balance.total_earned_cents == 0
        assert balance.available_balance_cents == 0

    async def test_sync_attributions_for_bot(self, factory):
        """Syncing attributions for a bot with no ad data returns empty sync."""
        bot_id = await _create_player(
            factory,
            username="testbot",
            player_type=PlayerType.BOT,
        )

        result = await factory.bot_earnings_service.sync_attributions(bot_id)

        assert result.bot_player_id == bot_id
        assert result.new_attributions == 0
        assert result.new_earnings_cents == 0

    async def test_sync_attributions_human_raises(self, factory):
        """Syncing attributions for a human player raises error."""
        human_id = await _create_player(factory, username="human_player")

        with pytest.raises(AppError) as exc_info:
            await factory.bot_earnings_service.sync_attributions(human_id)

        assert "BOT" in exc_info.value.code or "VALIDATION" in exc_info.value.code
