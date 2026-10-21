"""Payment service implementation.

Fully async service managing purchase intents, receipt validation,
ad-free granting, refund processing, and purchase restoration.
All dependencies arrive via ``__init__`` injection.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from src.core.types.game import PlayerId
from src.modules.payments._helpers import hash_receipt, to_purchase_record
from src.modules.payments.dto import (
    PaginatedResult,
    PurchaseCreate,
    PurchaseIntentCreate,
    PurchaseIntentUpdate,
    PurchaseUpdate,
    ReceiptValidationCreate,
    ReceiptValidationUpdate,
    RefundNotificationCreate,
)
from src.modules.payments.types import (
    PaymentProvider,
    PlayerPurchaseStatus,
    Product,
    ProductId,
    ProductType,
    PurchaseId,
    PurchaseIntent,
    PurchaseIntentId,
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

if TYPE_CHECKING:
    from src.core.protocols.config import ConfigProtocol
    from src.core.protocols.error_service import ErrorServiceProtocol
    from src.core.protocols.logger import LoggerProtocol
    from src.data.protocols.gold_balance_repository import (
        GoldBalanceRepositoryProtocol,
    )
    from src.data.protocols.gold_transaction_repository import (
        GoldTransactionRepositoryProtocol,
    )
    from src.modules.payments.protocols import (
        AdServiceProtocol,
        PaymentProviderProtocol,
        PlayerServiceProtocol,
        ProductRepositoryProtocol,
        PurchaseIntentRepositoryProtocol,
        PurchaseRepositoryProtocol,
        ReceiptValidationRepositoryProtocol,
        RefundNotificationRepositoryProtocol,
    )

# Gold IAP products — App Store product ID → gold amount.
_GOLD_PRODUCTS: dict[str, int] = {
    "chromacrush_gold_1500": 1500,
    "chromacrush_gold_3000": 3000,
    "chromacrush_gold_15000": 15000,
    "chromacrush_gold_35000": 35000,
    "chromacrush_gold_80000": 80000,
}

_MAX_HISTORY_LIMIT = 100


class PaymentRepositoryBundle:
    """Groups all payment-related repositories into a single injectable.

    Reduces the number of constructor parameters for ``PaymentService``
    from 11 to 7, matching the pattern used by ``AdRepositoryBundle``.
    """

    def __init__(
        self,
        product_repo: ProductRepositoryProtocol,
        intent_repo: PurchaseIntentRepositoryProtocol,
        purchase_repo: PurchaseRepositoryProtocol,
        receipt_repo: ReceiptValidationRepositoryProtocol,
        refund_repo: RefundNotificationRepositoryProtocol,
    ) -> None:
        self.product = product_repo
        self.intent = intent_repo
        self.purchase = purchase_repo
        self.receipt = receipt_repo
        self.refund = refund_repo


class PaymentService:
    """Concrete implementation of ``PaymentServiceProtocol``."""

    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        player_service: PlayerServiceProtocol,
        ads_service: AdServiceProtocol,
        repos: PaymentRepositoryBundle | None = None,
        payment_provider: PaymentProviderProtocol | None = None,
        gold_repo: GoldBalanceRepositoryProtocol | None = None,
        gold_tx_repo: GoldTransactionRepositoryProtocol | None = None,
        # Legacy individual repo parameters (prefer ``repos`` bundle)
        product_repo: ProductRepositoryProtocol | None = None,
        intent_repo: PurchaseIntentRepositoryProtocol | None = None,
        purchase_repo: PurchaseRepositoryProtocol | None = None,
        receipt_repo: ReceiptValidationRepositoryProtocol | None = None,
        refund_repo: RefundNotificationRepositoryProtocol | None = None,
    ) -> None:
        self._config = config
        self._logger = logger
        self._errors = errors
        self._players = player_service
        self._ads = ads_service

        # Accept either the bundle or individual repo params (backward compat)
        if repos is not None:
            self._product_repo = repos.product
            self._intent_repo = repos.intent
            self._purchase_repo = repos.purchase
            self._receipt_repo = repos.receipt
            self._refund_repo = repos.refund
        else:
            self._product_repo = product_repo  # type: ignore[assignment]
            self._intent_repo = intent_repo  # type: ignore[assignment]
            self._purchase_repo = purchase_repo  # type: ignore[assignment]
            self._receipt_repo = receipt_repo  # type: ignore[assignment]
            self._refund_repo = refund_repo  # type: ignore[assignment]

        self._provider = payment_provider  # type: ignore[assignment]
        self._gold_repo = gold_repo
        self._gold_tx_repo = gold_tx_repo

        # Config values with defaults
        self._ad_free_product_id: str = config.get(
            "payments.ad_free_product_id",
            "chromacrush_ad_free",
        )
        self._ad_free_price_cents: int = config.get(
            "payments.ad_free_price_cents",
            100,
        )
        self._ad_free_currency: str = config.get(
            "payments.ad_free_currency",
            "USD",
        )
        self._intent_expiry_minutes: int = config.get(
            "payments.intent_expiry_minutes",
            30,
        )
        self._allow_sandbox: bool = config.get(
            "payments.allow_sandbox_purchases",
            False,
        )

    # === Public methods ===

    async def initiate_purchase(
        self,
        player_id: PlayerId,
        product_id: ProductId,
    ) -> PurchaseIntent:
        """Create a purchase intent record when player initiates checkout."""
        # 1. Validate player exists
        await self._players.get_player(player_id)

        # 2. Validate product exists
        product = await self._product_repo.find_by_id(str(product_id))
        if product is None:
            raise self._errors.not_found(
                "Product not found",
                code="NOT_FOUND_PRODUCT",
                product_id=str(product_id),
            )

        # 3. Create intent
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=self._intent_expiry_minutes)

        intent_rec = await self._intent_repo.create(
            PurchaseIntentCreate(
                player_id=player_id,
                product_id=str(product_id),
                status=PurchaseIntentStatus.PENDING.value,
                expires_at=expires_at,
            )
        )

        self._logger.info(
            "Purchase intent created",
            player_id=str(player_id),
            product_id=str(product_id),
            intent_id=str(intent_rec.id),
        )

        return PurchaseIntent(
            intent_id=PurchaseIntentId(intent_rec.id),
            player_id=player_id,
            product_id=product_id,
            product_name=product.name,
            price_cents=product.price_cents,
            currency=product.currency,
            status=PurchaseIntentStatus.PENDING,
            created_at=intent_rec.created_at,
            expires_at=expires_at,
        )

    async def validate_purchase(
        self,
        player_id: PlayerId,
        receipt: PurchaseReceipt,
    ) -> PurchaseResult:
        """Validate a purchase receipt and grant the purchased product."""
        # 1. Validate player exists
        await self._players.get_player(player_id)

        # 2. Check if already ad-free (only for ad-free purchases)
        is_gold_product = str(receipt.product_id) in _GOLD_PRODUCTS
        if not is_gold_product:
            ad_free_status = await self._ads.check_ad_free_status(player_id)
            if ad_free_status.is_ad_free:
                raise self._errors.conflict(
                    "Player already has ad-free status",
                    code="CONFLICT_PLAYER_ALREADY_AD_FREE",
                    player_id=str(player_id),
                    granted_at=(
                        ad_free_status.granted_at.isoformat()
                        if ad_free_status.granted_at
                        else None
                    ),
                )

        # 3. Check for duplicate receipt (skip for consumable gold products —
        #    each StoreKit transaction is unique, dedup by transaction_id in DB)
        receipt_hash = hash_receipt(receipt.receipt_data)
        if not is_gold_product:
            existing_validation = await self._receipt_repo.find_by_hash(
                receipt_hash,
            )

            if (
                existing_validation is not None
                and existing_validation.validation_result == "valid"
            ):
                existing_purchase = await self._purchase_repo.find_by_id(
                    existing_validation.purchase_id,
                )
                if (
                    existing_purchase is not None
                    and existing_purchase.status == PurchaseStatus.COMPLETED.value
                ):
                    self._logger.info(
                        "Duplicate receipt submitted",
                        player_id=str(player_id),
                        transaction_id=existing_validation.transaction_id,
                        original_purchase_id=str(existing_validation.purchase_id),
                    )
                    raise self._errors.conflict(
                        "Receipt has already been processed",
                        code="CONFLICT_RECEIPT_ALREADY_PROCESSED",
                        transaction_id=existing_validation.transaction_id,
                        original_purchase_id=str(existing_validation.purchase_id),
                    )

        # 4. Validate with payment provider
        self._logger.info(
            "Receipt validation started",
            player_id=str(player_id),
            provider=receipt.provider.value,
        )

        try:
            validation_result = await self._provider.validate_receipt(
                receipt_data=receipt.receipt_data,
                product_id=str(receipt.product_id),
                is_sandbox=self._allow_sandbox,
            )
        except Exception as e:
            self._logger.error(
                "Payment provider error",
                provider=receipt.provider.value,
                operation="validate_receipt",
                error=str(e),
            )
            raise self._errors.internal(
                "Payment provider error",
                code="INTERNAL_PAYMENT_PROVIDER_ERROR",
                provider=receipt.provider.value,
                error=str(e),
            )

        # 5. Record validation attempt
        validation_record = await self._receipt_repo.create(
            ReceiptValidationCreate(
                player_id=player_id,
                provider=receipt.provider.value,
                receipt_data=receipt.receipt_data,
                receipt_hash=receipt_hash,
                validation_result="valid" if validation_result.valid else "invalid",
                validation_response=validation_result.raw_response,
                transaction_id=validation_result.transaction_id,
                product_id=validation_result.product_id,
                purchase_date=validation_result.purchase_date,
                is_sandbox=validation_result.is_sandbox,
                error_code=validation_result.error_code,
            ),
        )

        # 6. Handle validation failure
        if not validation_result.valid:
            self._logger.warn(
                "Receipt validation failed",
                player_id=str(player_id),
                provider=receipt.provider.value,
                error_code=validation_result.error_code,
            )
            return PurchaseResult(
                success=False,
                purchase_id=None,
                player_id=player_id,
                product_id=receipt.product_id,
                transaction_id=None,
                receipt_validation=validation_result,
                ad_free_granted=False,
                ad_free_status=None,
                error_code="VALIDATION_RECEIPT_INVALID",
                error_message=validation_result.error_code,
            )

        # 7. Verify product is recognized (ad-free or gold)
        validated_product = validation_result.product_id
        gold_amount = _GOLD_PRODUCTS.get(validated_product or "")
        is_ad_free = validated_product == self._ad_free_product_id

        if not is_ad_free and gold_amount is None:
            self._logger.warn(
                "Receipt validation failed - unknown product",
                player_id=str(player_id),
                actual_product=validated_product,
            )
            raise self._errors.validation(
                "Receipt is for unrecognized product",
                code="VALIDATION_RECEIPT_WRONG_PRODUCT",
                actual_product=validated_product,
            )

        # 8. Determine price for the purchase record
        price_cents = self._ad_free_price_cents
        if gold_amount is not None:
            # Look up cents from gold product marketplace definitions
            for gp_id, gp_cents in {
                "chromacrush_gold_1500": 49,
                "chromacrush_gold_3000": 99,
                "chromacrush_gold_15000": 499,
                "chromacrush_gold_35000": 999,
                "chromacrush_gold_80000": 1799,
            }.items():
                if validated_product == gp_id:
                    price_cents = gp_cents
                    break

        # 9. Create purchase record — idempotent on duplicate transaction ID.
        #    StoreKit may replay unfinished transactions on app restart; the
        #    client calls finishTransaction only after a successful response,
        #    so we must return 200 for duplicates (no double-grant).
        try:
            purchase = await self._purchase_repo.create(
                PurchaseCreate(
                    player_id=player_id,
                    product_id=str(receipt.product_id),
                    provider=receipt.provider.value,
                    transaction_id=validation_result.transaction_id,
                    status=PurchaseStatus.COMPLETED.value,
                    price_cents=price_cents,
                    currency=self._ad_free_currency,
                    is_sandbox=validation_result.is_sandbox,
                )
            )
        except Exception as exc:
            if (
                "unique_transaction" in str(exc).lower()
                or "uniqueviolation" in str(exc).lower()
            ):
                self._logger.info(
                    "Duplicate transaction — checking ledger for missing delivery",
                    transaction_id=validation_result.transaction_id,
                    player_id=str(player_id),
                )
                existing = await self._purchase_repo.find_by_transaction(
                    receipt.provider.value,
                    validation_result.transaction_id,
                )

                # Reconciliation: if this is a gold purchase, verify the
                # ledger has a matching credit.  If not, the original
                # delivery failed — re-credit and record it now.
                # TODO(ads): When ad-free purchases are added, mirror this
                # reconciliation pattern — check if ad-free status was
                # granted, and re-grant it here if missing.
                dup_gold = _GOLD_PRODUCTS.get(validated_product or "")
                if (
                    dup_gold is not None
                    and self._gold_repo is not None
                    and self._gold_tx_repo is not None
                ):
                    ledger_hit = await self._gold_tx_repo.find_by_reference(
                        validation_result.transaction_id or "",
                    )
                    if ledger_hit is None:
                        from uuid import UUID as _UUID

                        gold_pid = _UUID(str(player_id))
                        record = await self._gold_repo.find_by_player_id(gold_pid)
                        if record is None:
                            await self._gold_repo.create(gold_pid)
                        record = await self._gold_repo.credit(gold_pid, dup_gold)
                        await self._gold_tx_repo.create(
                            player_id=gold_pid,
                            tx_type="purchase",
                            amount=dup_gold,
                            balance_after=record.balance,
                            source=f"iap:{validated_product}",
                            reference_id=validation_result.transaction_id,
                        )
                        self._logger.info(
                            "Gold re-credited on duplicate — original delivery was missing",
                            transaction_id=validation_result.transaction_id,
                            player_id=str(player_id),
                            gold_amount=dup_gold,
                        )

                return PurchaseResult(
                    success=True,
                    purchase_id=PurchaseId(existing.id) if existing else None,
                    player_id=player_id,
                    product_id=receipt.product_id,
                    transaction_id=validation_result.transaction_id,
                    receipt_validation=validation_result,
                    ad_free_granted=False,
                    ad_free_status=None,
                    error_code=None,
                    error_message="Already processed",
                )
            raise

        # Update validation record with purchase_id
        await self._receipt_repo.update(
            validation_record.id,
            ReceiptValidationUpdate(purchase_id=purchase.id),
        )

        # 10. Grant the purchased product
        ad_free_granted = False
        new_ad_free_status = None

        if gold_amount is not None:
            # Gold IAP — credit gold to player balance
            if self._gold_repo is not None:
                from uuid import UUID as _UUID

                gold_pid = _UUID(str(player_id))
                record = await self._gold_repo.find_by_player_id(gold_pid)
                if record is None:
                    await self._gold_repo.create(gold_pid)
                record = await self._gold_repo.credit(gold_pid, gold_amount)

                # Record in gold transaction ledger
                if self._gold_tx_repo is not None:
                    await self._gold_tx_repo.create(
                        player_id=gold_pid,
                        tx_type="purchase",
                        amount=gold_amount,
                        balance_after=record.balance,
                        source=f"iap:{validation_result.product_id}",
                        reference_id=validation_result.transaction_id,
                    )

            self._logger.info(
                "Gold IAP purchase completed",
                player_id=str(player_id),
                purchase_id=str(purchase.id),
                gold_amount=gold_amount,
                transaction_id=validation_result.transaction_id,
            )
        else:
            # Ad-free purchase — grant ad-free status
            from src.modules.ads.types import AdFreeReason

            new_ad_free_status = await self._ads.grant_ad_free_status(
                player_id=player_id,
                reason=AdFreeReason.PURCHASE,
                duration_days=None,  # Permanent
            )
            ad_free_granted = True

            self._logger.info(
                "Ad-free purchase completed",
                player_id=str(player_id),
                purchase_id=str(purchase.id),
                transaction_id=validation_result.transaction_id,
            )

        return PurchaseResult(
            success=True,
            purchase_id=PurchaseId(purchase.id),
            player_id=player_id,
            product_id=receipt.product_id,
            transaction_id=validation_result.transaction_id,
            receipt_validation=validation_result,
            ad_free_granted=ad_free_granted,
            ad_free_status=new_ad_free_status,
            error_code=None,
            error_message=None,
        )

    async def get_purchase_status(
        self,
        player_id: PlayerId,
    ) -> PlayerPurchaseStatus:
        """Get the current purchase status for a player."""
        await self._players.get_player(player_id)

        completed = await self._purchase_repo.find_completed_by_player(
            player_id,
            product_id=self._ad_free_product_id,
        )

        if not completed:
            return PlayerPurchaseStatus(
                player_id=player_id,
                has_purchased_ad_free=False,
                purchase_date=None,
                transaction_id=None,
                provider=None,
                is_refunded=False,
                refund_date=None,
            )

        # Get the most recent completed purchase
        purchase = completed[0]
        is_refunded = purchase.status == PurchaseStatus.REFUNDED.value

        return PlayerPurchaseStatus(
            player_id=player_id,
            has_purchased_ad_free=True,
            purchase_date=purchase.created_at,
            transaction_id=purchase.transaction_id,
            provider=PaymentProvider(purchase.provider),
            is_refunded=is_refunded,
            refund_date=getattr(purchase, "refunded_at", None),
        )

    async def get_purchase_history(
        self,
        player_id: PlayerId,
        limit: int = 50,
        offset: int = 0,
    ) -> PaginatedResult[PurchaseRecord]:
        """Get purchase history for a player."""
        await self._players.get_player(player_id)

        if limit < 1 or limit > _MAX_HISTORY_LIMIT:
            raise self._errors.validation(
                f"Limit must be between 1 and {_MAX_HISTORY_LIMIT}",
                code="VALIDATION_INVALID_INPUT",
                field="limit",
            )
        if offset < 0:
            raise self._errors.validation(
                "Offset must be non-negative",
                code="VALIDATION_INVALID_INPUT",
                field="offset",
            )

        records, total = await self._purchase_repo.find_by_player(
            player_id,
            limit,
            offset,
        )

        items = [to_purchase_record(r) for r in records]

        return PaginatedResult(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    async def process_refund(
        self,
        refund_notification: RefundNotification,
    ) -> RefundResult:
        """Process a refund notification from the payment provider."""
        # 1. Store the notification
        notification_record = await self._refund_repo.create(
            RefundNotificationCreate(
                provider=refund_notification.provider.value,
                transaction_id=refund_notification.transaction_id,
                original_transaction_id=refund_notification.original_transaction_id,
                notification_type=refund_notification.notification_type,
                notification_payload=refund_notification.payload,
            ),
        )

        self._logger.info(
            "Refund notification received",
            transaction_id=refund_notification.transaction_id,
            provider=refund_notification.provider.value,
        )

        # 2. Find the original purchase
        purchase = await self._purchase_repo.find_by_transaction(
            provider=refund_notification.provider.value,
            transaction_id=refund_notification.transaction_id,
        )

        if purchase is None and refund_notification.original_transaction_id:
            purchase = await self._purchase_repo.find_by_transaction(
                provider=refund_notification.provider.value,
                transaction_id=refund_notification.original_transaction_id,
            )

        if purchase is None:
            await self._refund_repo.mark_processed(
                notification_record.id,
                result="not_found",
                error="No matching purchase found",
            )
            return RefundResult(
                success=False,
                purchase_id=None,
                player_id=None,
                transaction_id=refund_notification.transaction_id,
                ad_free_revoked=False,
                error_code="NOT_FOUND_PURCHASE",
                error_message="No matching purchase found for refund",
            )

        # 3. Check if already refunded
        if purchase.status == PurchaseStatus.REFUNDED.value:
            await self._refund_repo.mark_processed(
                notification_record.id,
                result="already_refunded",
            )
            return RefundResult(
                success=True,
                purchase_id=PurchaseId(purchase.id),
                player_id=PlayerId(purchase.player_id),
                transaction_id=refund_notification.transaction_id,
                ad_free_revoked=False,
                error_code=None,
                error_message=None,
            )

        # 4. Update purchase status
        await self._purchase_repo.update(
            purchase.id,
            PurchaseUpdate(
                status=PurchaseStatus.REFUNDED.value,
                refunded_at=datetime.now(timezone.utc),
            ),
        )

        # 5. Revoke ad-free status
        ad_free_revoked = False
        try:
            await self._ads.revoke_ad_free_status(
                player_id=PlayerId(purchase.player_id),
                reason=f"Refund processed: {refund_notification.transaction_id}",
            )
            ad_free_revoked = True
        except Exception as e:
            self._logger.warn(
                "Failed to revoke ad-free status on refund",
                player_id=str(purchase.player_id),
                error=str(e),
            )

        # 6. Reverse gold for gold-IAP refunds
        gold_amount = _GOLD_PRODUCTS.get(purchase.product_id)
        if gold_amount is not None and self._gold_repo is not None:
            from uuid import UUID as _UUID

            gold_pid = _UUID(str(purchase.player_id))
            try:
                record = await self._gold_repo.debit(gold_pid, gold_amount)
                if self._gold_tx_repo is not None:
                    await self._gold_tx_repo.create(
                        player_id=gold_pid,
                        tx_type="refund",
                        amount=-gold_amount,
                        balance_after=record.balance,
                        source="refund",
                        reference_id=refund_notification.transaction_id,
                    )
                self._logger.info(
                    "Gold reversed for refund",
                    player_id=str(purchase.player_id),
                    gold_amount=gold_amount,
                    transaction_id=refund_notification.transaction_id,
                )
            except Exception as e:
                self._logger.warn(
                    "Gold refund debit failed — player may have spent the gold",
                    player_id=str(purchase.player_id),
                    gold_amount=gold_amount,
                    error=str(e),
                )

        await self._refund_repo.mark_processed(
            notification_record.id,
            result="success",
        )

        self._logger.info(
            "Refund processed",
            player_id=str(purchase.player_id),
            purchase_id=str(purchase.id),
            transaction_id=refund_notification.transaction_id,
        )

        return RefundResult(
            success=True,
            purchase_id=PurchaseId(purchase.id),
            player_id=PlayerId(purchase.player_id),
            transaction_id=refund_notification.transaction_id,
            ad_free_revoked=ad_free_revoked,
            error_code=None,
            error_message=None,
        )

    async def restore_purchases(
        self,
        player_id: PlayerId,
        receipts: list[PurchaseReceipt],
    ) -> RestoreResult:
        """Restore purchases for a player (e.g., after reinstall).

        TODO(ads): Currently only handles ad-free (non-consumable) products.
        Gold IAPs are consumable and intentionally excluded from restoration.
        When ad-free purchases are added, ensure ad-free status is re-granted
        here if the purchase record exists but status was never applied.
        """
        await self._players.get_player(player_id)

        self._logger.info(
            "Purchase restore started",
            player_id=str(player_id),
            receipt_count=len(receipts),
        )

        restored_count = 0
        already_active_count = 0
        invalid_count = 0
        restored_purchases: list[PurchaseRecord] = []

        for receipt in receipts:
            # Check if this receipt was already processed
            receipt_hash = hash_receipt(receipt.receipt_data)
            existing = await self._receipt_repo.find_by_hash(receipt_hash)

            if existing is not None and existing.validation_result == "valid":
                # Already processed - check if purchase still active
                if existing.purchase_id:
                    existing_purchase = await self._purchase_repo.find_by_id(
                        existing.purchase_id,
                    )
                    if (
                        existing_purchase is not None
                        and existing_purchase.status == PurchaseStatus.COMPLETED.value
                    ):
                        already_active_count += 1
                        restored_purchases.append(
                            to_purchase_record(existing_purchase),
                        )
                        continue

            # Validate receipt with provider
            try:
                validation_result = await self._provider.validate_receipt(
                    receipt_data=receipt.receipt_data,
                    product_id=str(receipt.product_id),
                    is_sandbox=self._allow_sandbox,
                )
            except Exception as e:
                self._logger.warn(
                    "Receipt validation error during restore",
                    player_id=str(player_id),
                    error=str(e),
                )
                invalid_count += 1
                continue

            # Record validation
            validation_record = await self._receipt_repo.create(
                ReceiptValidationCreate(
                    player_id=player_id,
                    provider=receipt.provider.value,
                    receipt_data=receipt.receipt_data,
                    receipt_hash=receipt_hash,
                    validation_result="valid" if validation_result.valid else "invalid",
                    validation_response=validation_result.raw_response,
                    transaction_id=validation_result.transaction_id,
                    product_id=validation_result.product_id,
                    purchase_date=validation_result.purchase_date,
                    is_sandbox=validation_result.is_sandbox,
                    error_code=validation_result.error_code,
                ),
            )

            if not validation_result.valid:
                invalid_count += 1
                continue

            # Create purchase record
            purchase = await self._purchase_repo.create(
                PurchaseCreate(
                    player_id=player_id,
                    product_id=str(receipt.product_id),
                    provider=receipt.provider.value,
                    transaction_id=validation_result.transaction_id,
                    status=PurchaseStatus.COMPLETED.value,
                    price_cents=self._ad_free_price_cents,
                    currency=self._ad_free_currency,
                    is_sandbox=validation_result.is_sandbox,
                )
            )

            # Update validation with purchase ID
            await self._receipt_repo.update(
                validation_record.id,
                ReceiptValidationUpdate(purchase_id=purchase.id),
            )

            restored_count += 1
            restored_purchases.append(to_purchase_record(purchase))

        # Grant ad-free if any valid purchase found
        new_ad_free_status = None
        if restored_count > 0 or already_active_count > 0:
            from src.modules.ads.types import AdFreeReason

            try:
                new_ad_free_status = await self._ads.grant_ad_free_status(
                    player_id=player_id,
                    reason=AdFreeReason.PURCHASE,
                    duration_days=None,
                )
            except Exception:
                # Ad-free may already be active
                pass

        self._logger.info(
            "Purchase restore completed",
            player_id=str(player_id),
            restored_count=restored_count,
        )

        return RestoreResult(
            player_id=player_id,
            restored_count=restored_count,
            already_active_count=already_active_count,
            invalid_count=invalid_count,
            ad_free_status=new_ad_free_status,
            restored_purchases=restored_purchases,
        )

    async def get_products(self) -> list[Product]:
        """Get available products."""
        records = await self._product_repo.find_all_active()
        return [
            Product(
                product_id=ProductId(r.id),
                name=r.name,
                description=r.description or "",
                price_cents=r.price_cents,
                currency=r.currency,
                product_type=ProductType(r.product_type),
                is_active=r.is_active,
            )
            for r in records
        ]

    async def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        provider: PaymentProvider,
    ) -> bool:
        """Verify webhook signature from payment provider."""
        self._logger.debug(
            "Webhook received",
            provider=provider.value,
        )

        try:
            result = await self._provider.verify_webhook_signature(
                payload=payload,
                signature=signature,
            )
        except Exception as e:
            self._logger.warn(
                "Webhook signature verification error",
                provider=provider.value,
                error=str(e),
            )
            return False

        if not result:
            self._logger.warn(
                "Invalid webhook signature",
                provider=provider.value,
            )

        return result

    async def list_refund_notifications(
        self,
        unprocessed_only: bool = True,
    ) -> list[Any]:
        """List refund notifications, optionally filtered to unprocessed only.

        Wraps the refund repository call so CLI commands do not access
        repositories directly.
        """
        notifications = await self._refund_repo.find_unprocessed()
        self._logger.debug(
            "Refund notifications listed",
            count=len(notifications),
            unprocessed_only=unprocessed_only,
        )
        return notifications

    async def get_purchase(self, purchase_id: str) -> Any:
        """Get a single purchase record by ID.

        Wraps the purchase repository call so CLI commands do not access
        repositories directly.
        """
        from uuid import UUID as _UUID

        record = await self._purchase_repo.find_by_id(_UUID(purchase_id))
        if record is None:
            raise self._errors.not_found(
                "Purchase not found",
                code="NOT_FOUND_PURCHASE",
                purchase_id=purchase_id,
            )
        return record

    async def get_validation_by_transaction(
        self,
        transaction_id: str,
    ) -> Any:
        """Get a receipt validation record by transaction ID.

        Searches across all providers (apple, google, mock) and returns
        the first match.  Wraps the receipt repository call so CLI commands
        do not access repositories directly.
        """
        for provider in ("apple", "google", "mock"):
            record = await self._receipt_repo.find_by_transaction(
                provider,
                transaction_id,
            )
            if record is not None:
                return record

        raise self._errors.not_found(
            "Validation not found for transaction",
            code="NOT_FOUND_VALIDATION",
            transaction_id=transaction_id,
        )

    # === Private helpers (delegating to _helpers module) ===

    @staticmethod
    def _hash_receipt(receipt_data: str) -> str:
        """Create SHA-256 hash of receipt for duplicate detection."""
        return hash_receipt(receipt_data)

    @staticmethod
    def _to_purchase_record(rec: Any) -> PurchaseRecord:
        """Convert a repository record to a PurchaseRecord domain object."""
        return to_purchase_record(rec)
