"""CLI commands for the payments module.

Provides Click commands for payment operations: product listing,
purchase initiation, receipt validation, status checks, history,
restore, simulated refunds, and debug operations.

Ads-related imports are guarded behind try/except so the CLI
registers cleanly even when the ads module is not yet available.
When ads are unavailable, a stub that returns "not ad-free" is used.

Commands:
    payments products           -- List available products
    payments initiate           -- Initiate a purchase
    payments validate           -- Validate a purchase receipt
    payments status             -- Check player purchase status
    payments history            -- View purchase history
    payments restore            -- Restore purchases
    payments simulate-refund    -- Simulate a refund notification
    payments list-refunds       -- List refund notifications
    payments get-purchase       -- Get purchase details
    payments get-validation     -- Get validation details
"""

from __future__ import annotations

from typing import Any
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.cli.helpers.async_bridge import resolve_player, run_cli_async
from src.core.composition_root import ApplicationContext
from src.core.errors import AppError
from src.core.types.game import PlayerId
from src.modules.payments.service import PaymentRepositoryBundle, PaymentService
from src.modules.payments.types import (
    PaymentProvider,
    ProductId,
    PurchaseReceipt,
    RefundNotification,
)

# ---------------------------------------------------------------------------
# Guarded ads imports
# ---------------------------------------------------------------------------
_ADS_AVAILABLE = False
try:
    from src.modules.ads.types import AdFreeReason, AdFreeStatus

    _ADS_AVAILABLE = True
except ImportError:
    pass

console = Console()


def _run_async(coro_factory: Any, config_path: str = "config/app.toml") -> None:
    """Bridge sync Click commands to async PaymentService operations."""

    async def _bridge(ctx: ApplicationContext) -> None:
        await coro_factory(_build_payment_service(ctx), ctx)

    run_cli_async(_bridge, config_path)


def _build_ads_service_stub() -> Any:
    """Build a minimal ads service stub for PaymentService dependency.

    When the ads module is available, uses its types for realistic stubs.
    When unavailable, returns a duck-typed stub that satisfies the
    AdServiceProtocol expected by PaymentService.
    """

    class _AdsServiceStub:
        async def check_ad_free_status(self, player_id: PlayerId) -> Any:
            if _ADS_AVAILABLE:
                return AdFreeStatus(
                    player_id=player_id,
                    is_ad_free=False,
                )
            # Duck-typed stub when ads types unavailable
            from dataclasses import dataclass

            @dataclass
            class _Stub:
                player_id: Any
                is_ad_free: bool = False
                reason: Any = None
                granted_at: Any = None
                expires_at: Any = None
                is_permanent: bool = False

            return _Stub(player_id=player_id)

        async def grant_ad_free_status(
            self,
            player_id: PlayerId,
            reason: Any,
            duration_days: Any = None,
            granted_by: Any = None,
        ) -> Any:
            if _ADS_AVAILABLE:
                return AdFreeStatus(
                    player_id=player_id,
                    is_ad_free=True,
                    reason=reason,
                    is_permanent=True,
                )
            from dataclasses import dataclass

            @dataclass
            class _Stub:
                player_id: Any
                is_ad_free: bool = True
                reason: Any = None
                granted_at: Any = None
                expires_at: Any = None
                is_permanent: bool = True

            return _Stub(player_id=player_id, reason=reason)

        async def revoke_ad_free_status(
            self,
            player_id: PlayerId,
            reason: str,
        ) -> None:
            pass

    return _AdsServiceStub()


def _build_payment_service(ctx: ApplicationContext) -> PaymentService:
    """Build a PaymentService from the application context."""
    from src.data.repositories.energy_state_repository import (
        SQLAlchemyEnergyStateRepository,
    )
    from src.data.repositories.player_stats_repository import (
        SQLAlchemyPlayerStatsRepository,
    )
    from src.data.repositories.product_repository import (
        SQLAlchemyProductRepository,
    )
    from src.data.repositories.purchase_intent_repository import (
        SQLAlchemyPurchaseIntentRepository,
    )
    from src.data.repositories.purchase_repository import (
        SQLAlchemyPurchaseRepository,
    )
    from src.data.repositories.receipt_validation_repository import (
        SQLAlchemyReceiptValidationRepository,
    )
    from src.data.repositories.refund_notification_repository import (
        SQLAlchemyRefundNotificationRepository,
    )
    from src.modules.player.service import PlayerService

    # Player service (required dependency)
    stats_repo = SQLAlchemyPlayerStatsRepository(ctx.data_ctx, ctx.logger, ctx.errors)
    energy_repo = SQLAlchemyEnergyStateRepository(ctx.data_ctx, ctx.logger, ctx.errors)
    player_service = PlayerService(
        config=ctx.config,
        logger=ctx.logger,
        errors=ctx.errors,
        player_repo=ctx.player_repo,
        stats_repo=stats_repo,
        energy_repo=energy_repo,
    )

    # Mock payment provider for CLI testing
    class _MockPaymentProvider:
        async def validate_receipt(
            self,
            receipt_data: str,
            product_id: str,
            is_sandbox: bool = False,
        ) -> Any:
            from src.modules.payments.types import ReceiptValidationResult

            return ReceiptValidationResult(
                valid=True,
                provider=PaymentProvider.MOCK,
                transaction_id=f"mock_txn_{receipt_data[:8]}",
                product_id=product_id,
                purchase_date=None,
                is_duplicate=False,
                is_sandbox=True,
                error_code=None,
                raw_response={"provider": "mock", "status": "ok"},
            )

        async def verify_webhook_signature(
            self,
            payload: bytes,
            signature: str,
        ) -> bool:
            return True

    # Payment repositories
    repos = PaymentRepositoryBundle(
        product_repo=SQLAlchemyProductRepository(ctx.data_ctx, ctx.logger, ctx.errors),
        intent_repo=SQLAlchemyPurchaseIntentRepository(
            ctx.data_ctx, ctx.logger, ctx.errors
        ),
        purchase_repo=SQLAlchemyPurchaseRepository(
            ctx.data_ctx, ctx.logger, ctx.errors
        ),
        receipt_repo=SQLAlchemyReceiptValidationRepository(
            ctx.data_ctx, ctx.logger, ctx.errors
        ),
        refund_repo=SQLAlchemyRefundNotificationRepository(
            ctx.data_ctx, ctx.logger, ctx.errors
        ),
    )

    return PaymentService(
        config=ctx.config,
        logger=ctx.logger,
        errors=ctx.errors,
        player_service=player_service,
        ads_service=_build_ads_service_stub(),
        repos=repos,
        payment_provider=_MockPaymentProvider(),
    )


def _get_ad_free_product_id(config: Any) -> str:
    """Get the ad-free product ID from config (public API, no private attrs)."""
    return config.get("payments.ad_free_product_id", "chromacrush_ad_free")


@click.group()
def payments() -> None:
    """Payment management commands."""


@payments.command("products")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def products(config_path: str) -> None:
    """List available products."""

    async def _do(svc: PaymentService, ctx: Any) -> None:
        try:
            product_list = await svc.get_products()
            if not product_list:
                console.print("No products available.")
                return
            table = Table(title="Available Products")
            table.add_column("ID", style="cyan")
            table.add_column("Name")
            table.add_column("Price", justify="right")
            table.add_column("Type")
            table.add_column("Status")
            for p in product_list:
                price_str = f"${p.price_cents / 100:.2f} {p.currency}"
                status = "Active" if p.is_active else "Inactive"
                table.add_row(
                    str(p.product_id),
                    p.name,
                    price_str,
                    p.product_type.value,
                    status,
                )
            console.print(table)
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    _run_async(_do, config_path)


@payments.command("initiate")
@click.argument("player_username")
@click.option("--product", "product_id", required=True, help="Product ID to purchase.")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def initiate(player_username: str, product_id: str, config_path: str) -> None:
    """Initiate a purchase for a player."""

    async def _do(svc: PaymentService, ctx: Any) -> None:
        try:
            pid = PlayerId(await resolve_player(ctx, player_username))
            intent = await svc.initiate_purchase(pid, ProductId(product_id))
            console.print(
                Panel(
                    f"[bold green]Purchase intent created![/bold green]\n\n"
                    f"  Intent ID:  {intent.intent_id}\n"
                    f"  Product:    {intent.product_name}\n"
                    f"  Price:      ${intent.price_cents / 100:.2f} {intent.currency}\n"
                    f"  Status:     {intent.status.value}\n"
                    f"  Expires:    {intent.expires_at}",
                    title="Purchase Intent",
                )
            )
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    _run_async(_do, config_path)


@payments.command("validate")
@click.argument("player_username")
@click.option(
    "--provider", required=True, type=click.Choice(["apple", "google", "mock"])
)
@click.option("--receipt", "receipt_data", required=True, help="Receipt data string.")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def validate(
    player_username: str, provider: str, receipt_data: str, config_path: str
) -> None:
    """Validate a purchase receipt."""

    async def _do(svc: PaymentService, ctx: Any) -> None:
        try:
            pid = PlayerId(await resolve_player(ctx, player_username))
            product_id = ProductId(_get_ad_free_product_id(ctx.config))
            receipt = PurchaseReceipt(
                provider=PaymentProvider(provider),
                receipt_data=receipt_data,
                product_id=product_id,
            )
            console.print("Validating receipt...")
            result = await svc.validate_purchase(pid, receipt)
            if result.success:
                console.print(
                    Panel(
                        f"[bold green]Purchase completed![/bold green]\n\n"
                        f"  Purchase ID:    {result.purchase_id}\n"
                        f"  Transaction ID: {result.transaction_id}\n"
                        f"  Product:        {result.product_id}\n"
                        f"  Ad-Free:        {'Granted (permanent)' if result.ad_free_granted else 'Not granted'}",
                        title="Validation Result",
                    )
                )
            else:
                console.print(
                    Panel(
                        f"[bold yellow]Validation failed[/bold yellow]\n\n"
                        f"  Error Code:    {result.error_code}\n"
                        f"  Error Message: {result.error_message}",
                        title="Validation Result",
                    )
                )
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    _run_async(_do, config_path)


@payments.command("status")
@click.argument("player_username")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def status(player_username: str, config_path: str) -> None:
    """Check player purchase status."""

    async def _do(svc: PaymentService, ctx: Any) -> None:
        try:
            pid = PlayerId(await resolve_player(ctx, player_username))
            st = await svc.get_purchase_status(pid)
            lines = [
                f"  Has Ad-Free:    {'Yes' if st.has_purchased_ad_free else 'No'}",
            ]
            if st.has_purchased_ad_free:
                lines.append(f"  Purchase Date:  {st.purchase_date}")
                lines.append(f"  Transaction ID: {st.transaction_id}")
                lines.append(
                    f"  Provider:       {st.provider.value if st.provider else 'N/A'}"
                )
                lines.append(f"  Refunded:       {'Yes' if st.is_refunded else 'No'}")
                if st.is_refunded and st.refund_date:
                    lines.append(f"  Refund Date:    {st.refund_date}")
            console.print(
                Panel(
                    "\n".join(lines),
                    title=f"Purchase Status: {player_username}",
                )
            )
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    _run_async(_do, config_path)


@payments.command("history")
@click.argument("player_username")
@click.option("--limit", default=50, type=int)
@click.option("--offset", default=0, type=int)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def history(player_username: str, limit: int, offset: int, config_path: str) -> None:
    """View purchase history for a player."""

    async def _do(svc: PaymentService, ctx: Any) -> None:
        try:
            pid = PlayerId(await resolve_player(ctx, player_username))
            result = await svc.get_purchase_history(pid, limit, offset)
            if not result.items:
                console.print("No purchase history found.")
                return
            table = Table(title=f"Purchase History: {player_username}")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Product")
            table.add_column("Provider")
            table.add_column("Transaction")
            table.add_column("Price", justify="right")
            table.add_column("Status")
            table.add_column("Date")
            for rec in result.items:
                table.add_row(
                    str(rec.id)[:8] + "...",
                    str(rec.product_id),
                    rec.provider.value,
                    rec.transaction_id or "N/A",
                    f"${rec.price_cents / 100:.2f}",
                    rec.status.value,
                    str(rec.created_at),
                )
            console.print(table)
            console.print(
                f"\nShowing {offset + 1}-{offset + len(result.items)} of {result.total}",
            )
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    _run_async(_do, config_path)


@payments.command("restore")
@click.argument("player_username")
@click.option(
    "--provider", required=True, type=click.Choice(["apple", "google", "mock"])
)
@click.option("--receipt", "receipt_data", required=True, help="Receipt data string.")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def restore(player_username: str, provider: str, receipt_data: str, config_path: str) -> None:
    """Restore purchases for a player."""

    async def _do(svc: PaymentService, ctx: Any) -> None:
        try:
            pid = PlayerId(await resolve_player(ctx, player_username))
            product_id = ProductId(_get_ad_free_product_id(ctx.config))
            receipts = [
                PurchaseReceipt(
                    provider=PaymentProvider(provider),
                    receipt_data=receipt_data,
                    product_id=product_id,
                ),
            ]
            result = await svc.restore_purchases(pid, receipts)
            console.print(
                Panel(
                    f"[bold green]Restore completed![/bold green]\n\n"
                    f"  Restored:       {result.restored_count}\n"
                    f"  Already Active: {result.already_active_count}\n"
                    f"  Invalid:        {result.invalid_count}",
                    title="Restore Result",
                )
            )
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    _run_async(_do, config_path)


@payments.command("simulate-refund")
@click.option(
    "--provider", required=True, type=click.Choice(["apple", "google", "mock"])
)
@click.option("--transaction", "transaction_id", required=True, help="Transaction ID.")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def simulate_refund(provider: str, transaction_id: str, config_path: str) -> None:
    """Simulate a refund notification."""

    async def _do(svc: PaymentService, ctx: Any) -> None:
        try:
            notification = RefundNotification(
                provider=PaymentProvider(provider),
                notification_type="REFUND",
                transaction_id=transaction_id,
                original_transaction_id=None,
                payload={"simulated": True},
                signature="simulated",
            )
            console.print("Simulating refund notification...")
            result = await svc.process_refund(notification)
            if result.success:
                console.print(
                    Panel(
                        f"[bold green]Refund processed![/bold green]\n\n"
                        f"  Purchase ID:   {result.purchase_id}\n"
                        f"  Player ID:     {result.player_id}\n"
                        f"  Ad-Free Revoked: {'Yes' if result.ad_free_revoked else 'No'}",
                        title="Refund Result",
                    )
                )
            else:
                console.print(
                    Panel(
                        f"[bold yellow]Refund failed[/bold yellow]\n\n"
                        f"  Error Code:    {result.error_code}\n"
                        f"  Error Message: {result.error_message}",
                        title="Refund Result",
                    )
                )
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    _run_async(_do, config_path)


@payments.command("list-refunds")
@click.option(
    "--unprocessed", is_flag=True, default=False, help="Only show unprocessed."
)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def list_refunds(unprocessed: bool, config_path: str) -> None:
    """List refund notifications."""

    async def _do(svc: PaymentService, ctx: Any) -> None:
        try:
            notifications = await svc.list_refund_notifications(
                unprocessed_only=unprocessed
            )
            if not notifications:
                console.print("No unprocessed refund notifications found.")
                return
            table = Table(title="Refund Notifications")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Provider")
            table.add_column("Transaction")
            table.add_column("Type")
            table.add_column("Processed")
            table.add_column("Result")
            table.add_column("Received")
            for n in notifications:
                table.add_row(
                    str(n.id)[:8] + "...",
                    n.provider,
                    n.transaction_id,
                    n.notification_type,
                    "Yes" if n.processed else "No",
                    n.process_result or "N/A",
                    str(n.received_at),
                )
            console.print(table)
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    _run_async(_do, config_path)


@payments.command("get-purchase")
@click.argument("purchase_id")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def get_purchase(purchase_id: str, config_path: str) -> None:
    """Get purchase details by ID."""

    async def _do(svc: PaymentService, ctx: Any) -> None:
        try:
            rec = await svc.get_purchase(purchase_id)
            console.print(
                Panel(
                    f"  ID:             {rec.id}\n"
                    f"  Player:         {rec.player_id}\n"
                    f"  Product:        {rec.product_id}\n"
                    f"  Provider:       {rec.provider}\n"
                    f"  Transaction:    {rec.transaction_id}\n"
                    f"  Status:         {rec.status}\n"
                    f"  Price:          ${rec.price_cents / 100:.2f} {rec.currency}\n"
                    f"  Sandbox:        {rec.is_sandbox}\n"
                    f"  Created:        {rec.created_at}\n"
                    f"  Refunded At:    {rec.refunded_at or 'N/A'}",
                    title=f"Purchase: {purchase_id[:8]}...",
                )
            )
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    _run_async(_do, config_path)


@payments.command("get-validation")
@click.argument("player_username")
@click.option("--transaction", "transaction_id", required=True, help="Transaction ID.")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def get_validation(player_username: str, transaction_id: str, config_path: str) -> None:
    """Get validation details by player and transaction ID."""

    async def _do(svc: PaymentService, ctx: Any) -> None:
        try:
            rec = await svc.get_validation_by_transaction(transaction_id)
            console.print(
                Panel(
                    f"  ID:             {rec.id}\n"
                    f"  Player:         {rec.player_id}\n"
                    f"  Provider:       {rec.provider}\n"
                    f"  Result:         {rec.validation_result}\n"
                    f"  Transaction:    {rec.transaction_id or 'N/A'}\n"
                    f"  Product:        {rec.product_id or 'N/A'}\n"
                    f"  Sandbox:        {rec.is_sandbox}\n"
                    f"  Error:          {rec.error_code or 'N/A'}\n"
                    f"  Created:        {rec.created_at}",
                    title=f"Validation: {transaction_id[:12]}...",
                )
            )
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    _run_async(_do, config_path)
