"""Integration tests for purchase flow.

Validates PaymentService product listing, purchase status, and ad-free
conflict detection using real PostgreSQL and Redis.
"""

from __future__ import annotations

import pytest
from uuid import UUID

from src.core.errors import AppError
from src.core.types.game import PlayerId
from src.core.types.player import PlayerType
from src.modules.ads.types import AdFreeReason
from src.modules.payments.types import ProductId

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_player(factory, username="alice"):
    p = await factory.player_service.create_player(
        username=username,
        player_type=PlayerType.HUMAN,
    )
    return PlayerId(p.id)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPurchaseFlow:
    """Tests for PaymentService purchase workflows."""

    async def test_get_products_empty(self, factory):
        """No products exist initially."""
        products = await factory.payment_service.get_products()
        assert products == []

    async def test_purchase_status_no_purchases(self, factory):
        """New player has no purchase history."""
        player_id = await _create_player(factory)

        status = await factory.payment_service.get_purchase_status(player_id)

        assert status.player_id == player_id
        assert status.has_purchased_ad_free is False

    async def test_purchase_status_player_not_found(self, factory):
        """Purchase status for nonexistent player raises NOT_FOUND."""
        fake_id = PlayerId(UUID("00000000-0000-0000-0000-000000000099"))

        with pytest.raises(AppError) as exc_info:
            await factory.payment_service.get_purchase_status(fake_id)

        assert "NOT_FOUND" in exc_info.value.code

    async def test_validate_purchase_already_ad_free(self, factory):
        """Validating purchase when player already ad-free raises CONFLICT."""
        player_id = await _create_player(factory)

        # Grant ad-free first
        await factory.ad_service.grant_ad_free_status(
            player_id,
            reason=AdFreeReason.ADMIN_GRANT,
        )

        # Now try to validate a purchase — should conflict
        from src.modules.payments.types import PurchaseReceipt, PaymentProvider

        receipt = PurchaseReceipt(
            provider=PaymentProvider.MOCK,
            receipt_data="test_receipt_data",
            product_id=ProductId("ad_free_permanent"),
        )

        with pytest.raises(AppError) as exc_info:
            await factory.payment_service.validate_purchase(player_id, receipt)

        assert "CONFLICT" in exc_info.value.code

    async def test_initiate_purchase_product_not_found(self, factory):
        """Initiating purchase for nonexistent product raises NOT_FOUND."""
        player_id = await _create_player(factory)

        with pytest.raises(AppError) as exc_info:
            await factory.payment_service.initiate_purchase(
                player_id,
                ProductId("nonexistent_product"),
            )

        assert "NOT_FOUND" in exc_info.value.code
