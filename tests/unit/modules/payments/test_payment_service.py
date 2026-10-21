"""Comprehensive unit tests for PaymentService.

Tests all 8 public methods plus error paths:
initiate_purchase, validate_purchase, get_purchase_status,
get_purchase_history, process_refund, restore_purchases,
get_products, verify_webhook_signature.

Uses pytest + pytest-asyncio with AsyncMock/MagicMock dependencies.
"""

from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID, uuid4

import pytest

from src.core.errors import AppError
from src.core.types.game import PlayerId
from src.modules.payments.dto import PaginatedResult
from src.modules.payments.service import PaymentService
from src.modules.payments.types import (
    PaymentProvider,
    PlayerPurchaseStatus,
    Product,
    ProductId,
    ProductType,
    PurchaseId,
    PurchaseIntent,
    PurchaseIntentStatus,
    PurchaseRecord,
    PurchaseReceipt,
    PurchaseResult,
    PurchaseStatus,
    ReceiptValidationResult,
    RefundNotification,
    RefundResult,
    RestoreResult,
)
from tests.mocks.services import MockConfigService, MockErrorService, MockLogService

# ============================================================================
# Helpers
# ============================================================================

NOW = datetime.now(timezone.utc)
HOUR_AGO = NOW - timedelta(hours=1)
FIVE_MIN_LATER = NOW + timedelta(minutes=5)


def _pid() -> PlayerId:
    return PlayerId(uuid4())


def make_player(player_id: PlayerId | None = None) -> MagicMock:
    """Create a mock Player-like object."""
    p = MagicMock()
    p.id = player_id or _pid()
    p.username = "testplayer"
    return p


def make_product(
    product_id: str = "chromacrush_ad_free",
    name: str = "Remove Ads Forever",
    price_cents: int = 100,
    currency: str = "USD",
    product_type: str = "one_time",
    is_active: bool = True,
) -> MagicMock:
    """Create a mock product record."""
    p = MagicMock()
    p.id = product_id
    p.name = name
    p.description = "Remove all ads permanently"
    p.price_cents = price_cents
    p.currency = currency
    p.product_type = product_type
    p.is_active = is_active
    return p


def make_intent(
    intent_id: UUID | None = None,
    player_id: UUID | None = None,
    product_id: str = "chromacrush_ad_free",
    status: str = "pending",
    created_at: datetime | None = None,
    expires_at: datetime | None = None,
) -> MagicMock:
    """Create a mock purchase intent record."""
    r = MagicMock()
    r.id = intent_id or uuid4()
    r.player_id = player_id or uuid4()
    r.product_id = product_id
    r.status = status
    r.created_at = created_at or NOW
    r.expires_at = expires_at or FIVE_MIN_LATER
    r.completed_at = None
    return r


def make_purchase(
    purchase_id: UUID | None = None,
    player_id: UUID | None = None,
    product_id: str = "chromacrush_ad_free",
    provider: str = "apple",
    transaction_id: str = "txn_123",
    status: str = "completed",
    price_cents: int = 100,
    currency: str = "USD",
    is_sandbox: bool = False,
    created_at: datetime | None = None,
    refunded_at: datetime | None = None,
) -> MagicMock:
    """Create a mock purchase record."""
    r = MagicMock()
    r.id = purchase_id or uuid4()
    r.player_id = player_id or uuid4()
    r.product_id = product_id
    r.provider = provider
    r.transaction_id = transaction_id
    r.status = status
    r.price_cents = price_cents
    r.currency = currency
    r.is_sandbox = is_sandbox
    r.created_at = created_at or NOW
    r.refunded_at = refunded_at
    return r


def make_validation_record(
    validation_id: UUID | None = None,
    player_id: UUID | None = None,
    purchase_id: UUID | None = None,
    validation_result: str = "valid",
    transaction_id: str = "txn_123",
    receipt_hash: str = "abc123",
) -> MagicMock:
    """Create a mock receipt validation record."""
    r = MagicMock()
    r.id = validation_id or uuid4()
    r.player_id = player_id or uuid4()
    r.purchase_id = purchase_id
    r.validation_result = validation_result
    r.transaction_id = transaction_id
    r.receipt_hash = receipt_hash
    r.created_at = NOW
    return r


def make_refund_notification_record(
    notification_id: UUID | None = None,
    provider: str = "apple",
    transaction_id: str = "txn_123",
    processed: bool = False,
) -> MagicMock:
    """Create a mock refund notification record."""
    r = MagicMock()
    r.id = notification_id or uuid4()
    r.provider = provider
    r.transaction_id = transaction_id
    r.processed = processed
    r.received_at = NOW
    return r


def make_ad_free_status(
    player_id: PlayerId | None = None,
    is_ad_free: bool = False,
    granted_at: datetime | None = None,
) -> MagicMock:
    """Create a mock AdFreeStatus-like object."""
    s = MagicMock()
    s.player_id = player_id or _pid()
    s.is_ad_free = is_ad_free
    s.granted_at = granted_at
    s.reason = None
    return s


def make_validation_result(
    valid: bool = True,
    transaction_id: str = "txn_123",
    product_id: str = "chromacrush_ad_free",
    is_sandbox: bool = False,
    error_code: str | None = None,
) -> ReceiptValidationResult:
    """Create a ReceiptValidationResult."""
    return ReceiptValidationResult(
        valid=valid,
        provider=PaymentProvider.APPLE,
        transaction_id=transaction_id,
        product_id=product_id,
        purchase_date=NOW,
        is_duplicate=False,
        is_sandbox=is_sandbox,
        error_code=error_code,
        raw_response={"status": "ok"} if valid else {"status": "error"},
    )


def build_service(
    config_overrides: dict | None = None,
    player_service: AsyncMock | None = None,
    ads_service: AsyncMock | None = None,
    product_repo: AsyncMock | None = None,
    intent_repo: AsyncMock | None = None,
    purchase_repo: AsyncMock | None = None,
    receipt_repo: AsyncMock | None = None,
    refund_repo: AsyncMock | None = None,
    payment_provider: AsyncMock | None = None,
) -> tuple[PaymentService, dict[str, AsyncMock]]:
    """Build PaymentService with injected mocks. Returns (service, mocks_dict)."""
    config = MockConfigService(config_overrides or {})
    logger = MockLogService()
    errors = MockErrorService(logger)

    ps = player_service or AsyncMock()
    if player_service is None:
        ps.get_player = AsyncMock(return_value=make_player())

    ads = ads_service or AsyncMock()
    if ads_service is None:
        ads.check_ad_free_status = AsyncMock(
            return_value=make_ad_free_status(is_ad_free=False),
        )
        ads.grant_ad_free_status = AsyncMock(
            return_value=make_ad_free_status(is_ad_free=True),
        )
        ads.revoke_ad_free_status = AsyncMock(return_value=None)

    pr = product_repo or AsyncMock()
    ir = intent_repo or AsyncMock()
    pur = purchase_repo or AsyncMock()
    rr = receipt_repo or AsyncMock()
    ref = refund_repo or AsyncMock()
    pp = payment_provider or AsyncMock()

    # Default return values
    if product_repo is None:
        pr.find_by_id = AsyncMock(return_value=make_product())
        pr.find_all_active = AsyncMock(return_value=[make_product()])

    if intent_repo is None:
        ir.create = AsyncMock(return_value=make_intent())

    if receipt_repo is None:
        rr.find_by_hash = AsyncMock(return_value=None)
        rr.create = AsyncMock(return_value=make_validation_record())
        rr.update = AsyncMock(return_value=make_validation_record())

    if purchase_repo is None:
        pur.find_completed_by_player = AsyncMock(return_value=[])
        pur.find_by_player = AsyncMock(return_value=([], 0))
        pur.create = AsyncMock(return_value=make_purchase())
        pur.find_by_transaction = AsyncMock(return_value=None)
        pur.update = AsyncMock(return_value=make_purchase())

    if refund_repo is None:
        ref.create = AsyncMock(return_value=make_refund_notification_record())
        ref.mark_processed = AsyncMock(return_value=make_refund_notification_record())
        ref.find_unprocessed = AsyncMock(return_value=[])

    if payment_provider is None:
        pp.validate_receipt = AsyncMock(return_value=make_validation_result())
        pp.verify_webhook_signature = AsyncMock(return_value=True)

    svc = PaymentService(
        config=config,
        logger=logger,
        errors=errors,
        player_service=ps,
        ads_service=ads,
        product_repo=pr,
        intent_repo=ir,
        purchase_repo=pur,
        receipt_repo=rr,
        refund_repo=ref,
        payment_provider=pp,
    )

    mocks = {
        "config": config,
        "logger": logger,
        "errors": errors,
        "player_service": ps,
        "ads_service": ads,
        "product_repo": pr,
        "intent_repo": ir,
        "purchase_repo": pur,
        "receipt_repo": rr,
        "refund_repo": ref,
        "payment_provider": pp,
    }
    return svc, mocks


# ============================================================================
# initiate_purchase
# ============================================================================


@pytest.mark.asyncio
async def test_initiate_purchase_success() -> None:
    """Successful purchase initiation returns PurchaseIntent."""
    pid = _pid()
    svc, m = build_service()
    result = await svc.initiate_purchase(pid, ProductId("chromacrush_ad_free"))
    assert isinstance(result, PurchaseIntent)
    assert result.status == PurchaseIntentStatus.PENDING
    assert result.product_name == "Remove Ads Forever"
    m["intent_repo"].create.assert_awaited_once()
    m["player_service"].get_player.assert_awaited_once_with(pid)


@pytest.mark.asyncio
async def test_initiate_purchase_player_not_found() -> None:
    """Initiate with non-existent player raises not_found."""
    ps = AsyncMock()
    ps.get_player = AsyncMock(
        side_effect=AppError(
            code="NOT_FOUND_PLAYER",
            message="Player not found",
        )
    )
    svc, _ = build_service(player_service=ps)
    with pytest.raises(AppError) as exc_info:
        await svc.initiate_purchase(_pid(), ProductId("chromacrush_ad_free"))
    assert exc_info.value.code == "NOT_FOUND_PLAYER"


@pytest.mark.asyncio
async def test_initiate_purchase_product_not_found() -> None:
    """Initiate with non-existent product raises not_found."""
    pr = AsyncMock()
    pr.find_by_id = AsyncMock(return_value=None)
    svc, _ = build_service(product_repo=pr)
    with pytest.raises(AppError) as exc_info:
        await svc.initiate_purchase(_pid(), ProductId("nonexistent"))
    assert exc_info.value.code == "NOT_FOUND_PRODUCT"


# ============================================================================
# validate_purchase
# ============================================================================


@pytest.mark.asyncio
async def test_validate_purchase_success() -> None:
    """Successful receipt validation creates purchase and grants ad-free."""
    pid = _pid()
    receipt = PurchaseReceipt(
        provider=PaymentProvider.APPLE,
        receipt_data="valid_receipt_data",
        product_id=ProductId("chromacrush_ad_free"),
    )
    svc, m = build_service()
    result = await svc.validate_purchase(pid, receipt)
    assert isinstance(result, PurchaseResult)
    assert result.success is True
    assert result.ad_free_granted is True
    assert result.purchase_id is not None
    m["purchase_repo"].create.assert_awaited_once()
    m["ads_service"].grant_ad_free_status.assert_awaited_once()


@pytest.mark.asyncio
async def test_validate_purchase_player_already_ad_free() -> None:
    """Validation when player already ad-free raises conflict."""
    pid = _pid()
    ads = AsyncMock()
    ads.check_ad_free_status = AsyncMock(
        return_value=make_ad_free_status(is_ad_free=True, granted_at=NOW),
    )
    svc, _ = build_service(ads_service=ads)
    receipt = PurchaseReceipt(
        provider=PaymentProvider.APPLE,
        receipt_data="receipt",
        product_id=ProductId("chromacrush_ad_free"),
    )
    with pytest.raises(AppError) as exc_info:
        await svc.validate_purchase(pid, receipt)
    assert exc_info.value.code == "CONFLICT_PLAYER_ALREADY_AD_FREE"


@pytest.mark.asyncio
async def test_validate_purchase_duplicate_receipt() -> None:
    """Duplicate receipt submission raises conflict."""
    pid = _pid()
    purchase_id = uuid4()
    existing_validation = make_validation_record(
        validation_result="valid",
        purchase_id=purchase_id,
    )
    existing_purchase = make_purchase(
        purchase_id=purchase_id,
        status="completed",
    )

    rr = AsyncMock()
    rr.find_by_hash = AsyncMock(return_value=existing_validation)
    rr.create = AsyncMock(return_value=make_validation_record())
    rr.update = AsyncMock(return_value=make_validation_record())

    pur = AsyncMock()
    pur.find_by_id = AsyncMock(return_value=existing_purchase)
    pur.create = AsyncMock(return_value=make_purchase())
    pur.find_completed_by_player = AsyncMock(return_value=[])
    pur.find_by_player = AsyncMock(return_value=([], 0))
    pur.find_by_transaction = AsyncMock(return_value=None)
    pur.update = AsyncMock(return_value=make_purchase())

    svc, _ = build_service(receipt_repo=rr, purchase_repo=pur)
    receipt = PurchaseReceipt(
        provider=PaymentProvider.APPLE,
        receipt_data="duplicate_receipt",
        product_id=ProductId("chromacrush_ad_free"),
    )
    with pytest.raises(AppError) as exc_info:
        await svc.validate_purchase(pid, receipt)
    assert exc_info.value.code == "CONFLICT_RECEIPT_ALREADY_PROCESSED"


@pytest.mark.asyncio
async def test_validate_purchase_provider_error() -> None:
    """Payment provider error raises internal error."""
    pid = _pid()
    pp = AsyncMock()
    pp.validate_receipt = AsyncMock(side_effect=Exception("Provider down"))

    svc, _ = build_service(payment_provider=pp)
    receipt = PurchaseReceipt(
        provider=PaymentProvider.APPLE,
        receipt_data="receipt",
        product_id=ProductId("chromacrush_ad_free"),
    )
    with pytest.raises(AppError) as exc_info:
        await svc.validate_purchase(pid, receipt)
    assert exc_info.value.code == "INTERNAL_PAYMENT_PROVIDER_ERROR"


@pytest.mark.asyncio
async def test_validate_purchase_invalid_receipt() -> None:
    """Invalid receipt returns failed PurchaseResult (not an exception)."""
    pid = _pid()
    pp = AsyncMock()
    pp.validate_receipt = AsyncMock(
        return_value=make_validation_result(
            valid=False,
            error_code="INVALID_RECEIPT",
        )
    )

    svc, m = build_service(payment_provider=pp)
    receipt = PurchaseReceipt(
        provider=PaymentProvider.APPLE,
        receipt_data="bad_receipt",
        product_id=ProductId("chromacrush_ad_free"),
    )
    result = await svc.validate_purchase(pid, receipt)
    assert result.success is False
    assert result.error_code == "VALIDATION_RECEIPT_INVALID"
    assert result.ad_free_granted is False
    # Should NOT call purchase_repo.create
    m["purchase_repo"].create.assert_not_awaited()


@pytest.mark.asyncio
async def test_validate_purchase_wrong_product() -> None:
    """Receipt for wrong product raises validation error."""
    pid = _pid()
    pp = AsyncMock()
    pp.validate_receipt = AsyncMock(
        return_value=make_validation_result(
            valid=True,
            product_id="some_other_product",
        )
    )

    svc, _ = build_service(payment_provider=pp)
    receipt = PurchaseReceipt(
        provider=PaymentProvider.APPLE,
        receipt_data="receipt",
        product_id=ProductId("chromacrush_ad_free"),
    )
    with pytest.raises(AppError) as exc_info:
        await svc.validate_purchase(pid, receipt)
    assert exc_info.value.code == "VALIDATION_RECEIPT_WRONG_PRODUCT"


# ============================================================================
# get_purchase_status
# ============================================================================


@pytest.mark.asyncio
async def test_get_purchase_status_no_purchases() -> None:
    """Player with no purchases shows has_purchased_ad_free=False."""
    pid = _pid()
    svc, _ = build_service()
    result = await svc.get_purchase_status(pid)
    assert isinstance(result, PlayerPurchaseStatus)
    assert result.has_purchased_ad_free is False
    assert result.provider is None


@pytest.mark.asyncio
async def test_get_purchase_status_with_purchase() -> None:
    """Player with completed purchase shows has_purchased_ad_free=True."""
    pid = _pid()
    purchase = make_purchase(player_id=pid, status="completed")
    pur = AsyncMock()
    pur.find_completed_by_player = AsyncMock(return_value=[purchase])
    pur.find_by_player = AsyncMock(return_value=([], 0))
    pur.create = AsyncMock(return_value=make_purchase())
    pur.find_by_transaction = AsyncMock(return_value=None)
    pur.find_by_id = AsyncMock(return_value=None)
    pur.update = AsyncMock(return_value=make_purchase())

    svc, _ = build_service(purchase_repo=pur)
    result = await svc.get_purchase_status(pid)
    assert result.has_purchased_ad_free is True
    assert result.provider == PaymentProvider.APPLE


@pytest.mark.asyncio
async def test_get_purchase_status_player_not_found() -> None:
    """Non-existent player raises not_found."""
    ps = AsyncMock()
    ps.get_player = AsyncMock(
        side_effect=AppError(
            code="NOT_FOUND_PLAYER",
            message="Player not found",
        )
    )
    svc, _ = build_service(player_service=ps)
    with pytest.raises(AppError) as exc_info:
        await svc.get_purchase_status(_pid())
    assert exc_info.value.code == "NOT_FOUND_PLAYER"


# ============================================================================
# get_purchase_history
# ============================================================================


@pytest.mark.asyncio
async def test_get_purchase_history_success() -> None:
    """Returns paginated purchase history."""
    pid = _pid()
    purchases = [make_purchase(player_id=pid) for _ in range(3)]
    pur = AsyncMock()
    pur.find_by_player = AsyncMock(return_value=(purchases, 3))
    pur.find_completed_by_player = AsyncMock(return_value=[])
    pur.create = AsyncMock(return_value=make_purchase())
    pur.find_by_transaction = AsyncMock(return_value=None)
    pur.find_by_id = AsyncMock(return_value=None)
    pur.update = AsyncMock(return_value=make_purchase())

    svc, _ = build_service(purchase_repo=pur)
    result = await svc.get_purchase_history(pid, limit=50, offset=0)
    assert isinstance(result, PaginatedResult)
    assert len(result.items) == 3
    assert result.total == 3


@pytest.mark.asyncio
async def test_get_purchase_history_invalid_limit() -> None:
    """Limit outside 1-100 range raises validation error."""
    svc, _ = build_service()
    with pytest.raises(AppError) as exc_info:
        await svc.get_purchase_history(_pid(), limit=200)
    assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


@pytest.mark.asyncio
async def test_get_purchase_history_negative_offset() -> None:
    """Negative offset raises validation error."""
    svc, _ = build_service()
    with pytest.raises(AppError) as exc_info:
        await svc.get_purchase_history(_pid(), offset=-1)
    assert exc_info.value.code == "VALIDATION_INVALID_INPUT"


# ============================================================================
# process_refund
# ============================================================================


@pytest.mark.asyncio
async def test_process_refund_success() -> None:
    """Successful refund updates purchase and revokes ad-free."""
    purchase = make_purchase(status="completed")
    pur = AsyncMock()
    pur.find_by_transaction = AsyncMock(return_value=purchase)
    pur.update = AsyncMock(return_value=purchase)
    pur.find_completed_by_player = AsyncMock(return_value=[])
    pur.find_by_player = AsyncMock(return_value=([], 0))
    pur.create = AsyncMock(return_value=make_purchase())
    pur.find_by_id = AsyncMock(return_value=None)

    notification = RefundNotification(
        provider=PaymentProvider.APPLE,
        notification_type="REFUND",
        transaction_id="txn_123",
        original_transaction_id=None,
        payload={"reason": "customer_request"},
        signature="valid_sig",
    )

    svc, m = build_service(purchase_repo=pur)
    result = await svc.process_refund(notification)
    assert isinstance(result, RefundResult)
    assert result.success is True
    assert result.ad_free_revoked is True
    m["ads_service"].revoke_ad_free_status.assert_awaited_once()
    m["refund_repo"].mark_processed.assert_awaited()


@pytest.mark.asyncio
async def test_process_refund_purchase_not_found() -> None:
    """Refund for non-existent purchase returns failure."""
    notification = RefundNotification(
        provider=PaymentProvider.APPLE,
        notification_type="REFUND",
        transaction_id="nonexistent_txn",
        original_transaction_id=None,
        payload={},
        signature="sig",
    )

    svc, m = build_service()
    result = await svc.process_refund(notification)
    assert result.success is False
    assert result.error_code == "NOT_FOUND_PURCHASE"
    m["refund_repo"].mark_processed.assert_awaited()


@pytest.mark.asyncio
async def test_process_refund_already_refunded() -> None:
    """Refund on already-refunded purchase returns success (idempotent)."""
    purchase = make_purchase(status="refunded")
    pur = AsyncMock()
    pur.find_by_transaction = AsyncMock(return_value=purchase)
    pur.update = AsyncMock(return_value=purchase)
    pur.find_completed_by_player = AsyncMock(return_value=[])
    pur.find_by_player = AsyncMock(return_value=([], 0))
    pur.create = AsyncMock(return_value=make_purchase())
    pur.find_by_id = AsyncMock(return_value=None)

    notification = RefundNotification(
        provider=PaymentProvider.APPLE,
        notification_type="REFUND",
        transaction_id="txn_123",
        original_transaction_id=None,
        payload={},
        signature="sig",
    )

    svc, m = build_service(purchase_repo=pur)
    result = await svc.process_refund(notification)
    assert result.success is True
    assert result.ad_free_revoked is False
    # Should NOT call revoke because already refunded
    m["ads_service"].revoke_ad_free_status.assert_not_awaited()


@pytest.mark.asyncio
async def test_process_refund_fallback_to_original_transaction() -> None:
    """Refund uses original_transaction_id when primary lookup fails."""
    purchase = make_purchase(status="completed", transaction_id="original_txn")
    pur = AsyncMock()
    # First call (with transaction_id) returns None, second (original) finds it
    pur.find_by_transaction = AsyncMock(
        side_effect=[None, purchase],
    )
    pur.update = AsyncMock(return_value=purchase)
    pur.find_completed_by_player = AsyncMock(return_value=[])
    pur.find_by_player = AsyncMock(return_value=([], 0))
    pur.create = AsyncMock(return_value=make_purchase())
    pur.find_by_id = AsyncMock(return_value=None)

    notification = RefundNotification(
        provider=PaymentProvider.APPLE,
        notification_type="REFUND",
        transaction_id="renewal_txn",
        original_transaction_id="original_txn",
        payload={},
        signature="sig",
    )

    svc, _ = build_service(purchase_repo=pur)
    result = await svc.process_refund(notification)
    assert result.success is True


@pytest.mark.asyncio
async def test_process_refund_revoke_failure_still_succeeds() -> None:
    """Refund succeeds even if ad-free revocation fails (EC-6)."""
    purchase = make_purchase(status="completed")
    pur = AsyncMock()
    pur.find_by_transaction = AsyncMock(return_value=purchase)
    pur.update = AsyncMock(return_value=purchase)
    pur.find_completed_by_player = AsyncMock(return_value=[])
    pur.find_by_player = AsyncMock(return_value=([], 0))
    pur.create = AsyncMock(return_value=make_purchase())
    pur.find_by_id = AsyncMock(return_value=None)

    ads = AsyncMock()
    ads.check_ad_free_status = AsyncMock(
        return_value=make_ad_free_status(is_ad_free=False),
    )
    ads.grant_ad_free_status = AsyncMock(
        return_value=make_ad_free_status(is_ad_free=True),
    )
    ads.revoke_ad_free_status = AsyncMock(
        side_effect=Exception("Player not found"),
    )

    notification = RefundNotification(
        provider=PaymentProvider.APPLE,
        notification_type="REFUND",
        transaction_id="txn_123",
        original_transaction_id=None,
        payload={},
        signature="sig",
    )

    svc, _ = build_service(purchase_repo=pur, ads_service=ads)
    result = await svc.process_refund(notification)
    assert result.success is True
    assert result.ad_free_revoked is False  # Failed but refund still processed


# ============================================================================
# restore_purchases
# ============================================================================


@pytest.mark.asyncio
async def test_restore_purchases_success() -> None:
    """Successful restore validates and creates purchase."""
    pid = _pid()
    receipt = PurchaseReceipt(
        provider=PaymentProvider.APPLE,
        receipt_data="restore_receipt",
        product_id=ProductId("chromacrush_ad_free"),
    )

    svc, m = build_service()
    result = await svc.restore_purchases(pid, [receipt])
    assert isinstance(result, RestoreResult)
    assert result.restored_count == 1
    assert result.invalid_count == 0
    assert len(result.restored_purchases) == 1
    m["ads_service"].grant_ad_free_status.assert_awaited_once()


@pytest.mark.asyncio
async def test_restore_purchases_already_active() -> None:
    """Restore with already-processed receipt counts as already_active."""
    pid = _pid()
    purchase_id = uuid4()
    existing_validation = make_validation_record(
        validation_result="valid",
        purchase_id=purchase_id,
    )
    existing_purchase = make_purchase(
        purchase_id=purchase_id,
        status="completed",
    )

    rr = AsyncMock()
    rr.find_by_hash = AsyncMock(return_value=existing_validation)
    rr.create = AsyncMock(return_value=make_validation_record())
    rr.update = AsyncMock(return_value=make_validation_record())

    pur = AsyncMock()
    pur.find_by_id = AsyncMock(return_value=existing_purchase)
    pur.find_completed_by_player = AsyncMock(return_value=[])
    pur.find_by_player = AsyncMock(return_value=([], 0))
    pur.create = AsyncMock(return_value=make_purchase())
    pur.find_by_transaction = AsyncMock(return_value=None)
    pur.update = AsyncMock(return_value=make_purchase())

    receipt = PurchaseReceipt(
        provider=PaymentProvider.APPLE,
        receipt_data="existing_receipt",
        product_id=ProductId("chromacrush_ad_free"),
    )

    svc, _ = build_service(receipt_repo=rr, purchase_repo=pur)
    result = await svc.restore_purchases(pid, [receipt])
    assert result.already_active_count == 1
    assert result.restored_count == 0


@pytest.mark.asyncio
async def test_restore_purchases_invalid_receipt() -> None:
    """Restore with invalid receipt counts as invalid."""
    pid = _pid()
    pp = AsyncMock()
    pp.validate_receipt = AsyncMock(
        return_value=make_validation_result(
            valid=False,
            error_code="INVALID",
        )
    )
    pp.verify_webhook_signature = AsyncMock(return_value=True)

    receipt = PurchaseReceipt(
        provider=PaymentProvider.APPLE,
        receipt_data="bad_receipt",
        product_id=ProductId("chromacrush_ad_free"),
    )

    svc, _ = build_service(payment_provider=pp)
    result = await svc.restore_purchases(pid, [receipt])
    assert result.invalid_count == 1
    assert result.restored_count == 0


@pytest.mark.asyncio
async def test_restore_purchases_provider_error_counts_invalid() -> None:
    """Restore with provider error counts as invalid."""
    pid = _pid()
    pp = AsyncMock()
    pp.validate_receipt = AsyncMock(side_effect=Exception("Network error"))
    pp.verify_webhook_signature = AsyncMock(return_value=True)

    receipt = PurchaseReceipt(
        provider=PaymentProvider.APPLE,
        receipt_data="receipt",
        product_id=ProductId("chromacrush_ad_free"),
    )

    svc, _ = build_service(payment_provider=pp)
    result = await svc.restore_purchases(pid, [receipt])
    assert result.invalid_count == 1
    assert result.restored_count == 0


# ============================================================================
# get_products
# ============================================================================


@pytest.mark.asyncio
async def test_get_products_success() -> None:
    """Returns list of active products."""
    svc, _ = build_service()
    products = await svc.get_products()
    assert len(products) == 1
    assert isinstance(products[0], Product)
    assert products[0].product_id == ProductId("chromacrush_ad_free")
    assert products[0].product_type == ProductType.ONE_TIME


@pytest.mark.asyncio
async def test_get_products_empty() -> None:
    """Returns empty list when no products active."""
    pr = AsyncMock()
    pr.find_by_id = AsyncMock(return_value=None)
    pr.find_all_active = AsyncMock(return_value=[])
    svc, _ = build_service(product_repo=pr)
    products = await svc.get_products()
    assert products == []


# ============================================================================
# verify_webhook_signature
# ============================================================================


@pytest.mark.asyncio
async def test_verify_webhook_signature_valid() -> None:
    """Valid signature returns True."""
    svc, _ = build_service()
    result = await svc.verify_webhook_signature(
        b"payload",
        "valid_sig",
        PaymentProvider.APPLE,
    )
    assert result is True


@pytest.mark.asyncio
async def test_verify_webhook_signature_invalid() -> None:
    """Invalid signature returns False."""
    pp = AsyncMock()
    pp.validate_receipt = AsyncMock(return_value=make_validation_result())
    pp.verify_webhook_signature = AsyncMock(return_value=False)

    svc, _ = build_service(payment_provider=pp)
    result = await svc.verify_webhook_signature(
        b"payload",
        "bad_sig",
        PaymentProvider.APPLE,
    )
    assert result is False


@pytest.mark.asyncio
async def test_verify_webhook_signature_error() -> None:
    """Provider error during verification returns False."""
    pp = AsyncMock()
    pp.validate_receipt = AsyncMock(return_value=make_validation_result())
    pp.verify_webhook_signature = AsyncMock(
        side_effect=Exception("Crypto error"),
    )

    svc, _ = build_service(payment_provider=pp)
    result = await svc.verify_webhook_signature(
        b"payload",
        "sig",
        PaymentProvider.APPLE,
    )
    assert result is False


# ============================================================================
# _hash_receipt internal helper
# ============================================================================


def test_hash_receipt_deterministic() -> None:
    """Same receipt data produces same hash."""
    svc, _ = build_service()
    h1 = svc._hash_receipt("test_receipt_data")
    h2 = svc._hash_receipt("test_receipt_data")
    assert h1 == h2
    assert h1 == hashlib.sha256("test_receipt_data".encode()).hexdigest()


def test_hash_receipt_different_data() -> None:
    """Different receipt data produces different hashes."""
    svc, _ = build_service()
    h1 = svc._hash_receipt("receipt_a")
    h2 = svc._hash_receipt("receipt_b")
    assert h1 != h2
