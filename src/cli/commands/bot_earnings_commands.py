"""CLI commands for the bot_earnings module.

Provides Click commands for bot earnings management: balance queries,
earnings summaries, daily reports, attribution history, sync operations,
and payout request lifecycle.

Ads-related imports are guarded behind try/except so the CLI
registers cleanly even when the ads module is not yet available.
When ads are unavailable, a stub returning zero-attribution reports
is used to satisfy the BotEarningsService dependency.

Commands:
    bot-earnings balance            -- Show bot earnings balance
    bot-earnings summary            -- Show earnings summary for period
    bot-earnings daily              -- Show daily earnings breakdown
    bot-earnings attributions       -- List attribution entries
    bot-earnings sync               -- Sync attributions for a bot
    bot-earnings sync-all           -- Bulk sync all bots
    bot-earnings request-payout     -- Request a payout
    bot-earnings payout-requests    -- List payout requests
    bot-earnings cancel-payout      -- Cancel a pending payout
    bot-earnings process-payout     -- Process a pending payout (admin)
    bot-earnings reject-payout      -- Reject a pending payout (admin)
    bot-earnings pending-payouts    -- List pending payouts
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.cli.helpers.async_bridge import run_cli_async
from src.core.composition_root import ApplicationContext
from src.core.errors import AppError
from src.core.types.game import PlayerId
from src.modules.bot_earnings.service import BotEarningsService
from src.modules.bot_earnings.types import (
    EarningsPeriod,
    PayoutRequestId,
    PayoutStatus,
)

# ---------------------------------------------------------------------------
# Guarded ads imports
# ---------------------------------------------------------------------------
_ADS_AVAILABLE = False
try:
    from src.modules.ads.types import BotAdAttributionReport

    _ADS_AVAILABLE = True
except ImportError:
    pass

console = Console()


def _run_async(coro_factory: Any, config_path: str = "config/app.toml") -> None:
    """Bridge sync Click commands to async BotEarningsService operations."""

    async def _bridge(ctx: ApplicationContext) -> None:
        await coro_factory(_build_bot_earnings_service(ctx), ctx)

    run_cli_async(_bridge, config_path)


def _build_ads_service_stub() -> Any:
    """Build a minimal ads service stub for BotEarningsService dependency.

    When the ads module is available, uses its types for realistic stubs.
    When unavailable, returns a duck-typed stub that satisfies the
    AdServiceProtocol expected by BotEarningsService.
    """

    class _AdsServiceStub:
        async def get_bot_ad_attributions(
            self,
            bot_player_id: PlayerId,
            start_date: date,
            end_date: date,
        ) -> Any:
            if _ADS_AVAILABLE:
                return BotAdAttributionReport(
                    bot_player_id=bot_player_id,
                    start_date=start_date,
                    end_date=end_date,
                    total_matches=0,
                    matches_with_impressions=0,
                    total_attributed_impressions=0,
                    estimated_revenue_cents=0,
                    attributed_revenue_cents=0,
                    attribution_share_percent=0.0,
                    daily_breakdown=[],
                )
            # Duck-typed stub when ads types unavailable
            from dataclasses import dataclass, field

            @dataclass
            class _Stub:
                bot_player_id: Any
                start_date: Any
                end_date: Any
                total_matches: int = 0
                matches_with_impressions: int = 0
                total_attributed_impressions: int = 0
                estimated_revenue_cents: int = 0
                attributed_revenue_cents: int = 0
                attribution_share_percent: float = 0.0
                daily_breakdown: list = field(default_factory=list)

            return _Stub(
                bot_player_id=bot_player_id,
                start_date=start_date,
                end_date=end_date,
            )

    return _AdsServiceStub()


def _build_bot_earnings_service(ctx: ApplicationContext) -> BotEarningsService:
    """Build a BotEarningsService from the application context."""
    from src.data.repositories.bot_attribution_entry_repository import (
        SQLAlchemyAttributionEntryRepository,
    )
    from src.data.repositories.bot_daily_earnings_repository import (
        SQLAlchemyDailyEarningsRepository,
    )
    from src.data.repositories.bot_earnings_ledger_repository import (
        SQLAlchemyEarningsLedgerRepository,
    )
    from src.data.repositories.bot_payout_request_repository import (
        SQLAlchemyPayoutRequestRepository,
    )
    from src.data.repositories.energy_state_repository import (
        SQLAlchemyEnergyStateRepository,
    )
    from src.data.repositories.player_stats_repository import (
        SQLAlchemyPlayerStatsRepository,
    )
    from src.modules.player.service import PlayerService

    # Player service
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

    # Repositories
    ledger_repo = SQLAlchemyEarningsLedgerRepository(
        ctx.data_ctx, ctx.logger, ctx.errors
    )
    attribution_repo = SQLAlchemyAttributionEntryRepository(
        ctx.data_ctx, ctx.logger, ctx.errors
    )
    payout_repo = SQLAlchemyPayoutRequestRepository(
        ctx.data_ctx, ctx.logger, ctx.errors
    )
    daily_repo = SQLAlchemyDailyEarningsRepository(ctx.data_ctx, ctx.logger, ctx.errors)

    return BotEarningsService(
        config=ctx.config,
        logger=ctx.logger,
        errors=ctx.errors,
        player_service=player_service,
        ads_service=_build_ads_service_stub(),
        earnings_ledger_repository=ledger_repo,
        attribution_entry_repository=attribution_repo,
        payout_request_repository=payout_repo,
        daily_earnings_repository=daily_repo,
    )


@click.group("bot-earnings")
def bot_earnings() -> None:
    """Bot earnings management commands."""


@bot_earnings.command("balance")
@click.argument("bot_player_id")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def balance(bot_player_id: str, config_path: str) -> None:
    """Show bot earnings balance."""

    async def _do(svc: BotEarningsService, ctx: Any) -> None:
        try:
            pid = PlayerId(UUID(bot_player_id))
            b = await svc.get_earnings_balance(pid)
            console.print(
                Panel(
                    f"  Total earned:      ${b.total_earned_cents / 100:.2f}\n"
                    f"  Total paid out:    ${b.total_paid_out_cents / 100:.2f}\n"
                    f"  Pending payout:    ${b.pending_payout_cents / 100:.2f}\n"
                    f"  Available balance: ${b.available_balance_cents / 100:.2f}\n"
                    f"  Last attribution:  {b.last_attribution_at or 'Never'}\n"
                    f"  Last sync:         {b.last_sync_at or 'Never'}",
                    title=f"Earnings Balance: {bot_player_id[:8]}...",
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


@bot_earnings.command("summary")
@click.argument("bot_player_id")
@click.option(
    "--period",
    type=click.Choice(["day", "week", "month", "quarter", "year", "lifetime"]),
    default="lifetime",
)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def summary(bot_player_id: str, period: str, config_path: str) -> None:
    """Show earnings summary for a period."""

    async def _do(svc: BotEarningsService, ctx: Any) -> None:
        try:
            pid = PlayerId(UUID(bot_player_id))
            p = EarningsPeriod(period)
            s = await svc.get_earnings_summary(pid, p)
            top = (
                f"{s.top_earning_day} (${s.top_earning_day_cents / 100:.2f})"
                if s.top_earning_day
                else "N/A"
            )
            console.print(
                Panel(
                    f"  Period:            {s.period_start} to {s.period_end}\n"
                    f"  Total attributions: {s.total_attributions}\n"
                    f"  Matches:           {s.total_matches}\n"
                    f"  Impressions:       {s.total_impressions}\n"
                    f"  Earnings:          ${s.earnings_cents / 100:.2f}\n"
                    f"  Average daily:     ${s.average_daily_cents / 100:.2f}\n"
                    f"  Best day:          {top}",
                    title=f"Earnings Summary: {bot_player_id[:8]}... ({period})",
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


@bot_earnings.command("daily")
@click.argument("bot_player_id")
@click.option("--start", required=True, help="Start date (YYYY-MM-DD).")
@click.option("--end", required=True, help="End date (YYYY-MM-DD).")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def daily(bot_player_id: str, start: str, end: str, config_path: str) -> None:
    """Show daily earnings breakdown."""

    async def _do(svc: BotEarningsService, ctx: Any) -> None:
        try:
            pid = PlayerId(UUID(bot_player_id))
            sd = date.fromisoformat(start)
            ed = date.fromisoformat(end)
            entries = await svc.get_daily_earnings(pid, sd, ed)
            if not entries:
                console.print("No daily earnings found.")
                return
            table = Table(title=f"Daily Earnings: {bot_player_id[:8]}...")
            table.add_column("Date")
            table.add_column("Attrs", justify="right")
            table.add_column("Matches", justify="right")
            table.add_column("Impr", justify="right")
            table.add_column("Earnings", justify="right")
            for d in entries:
                table.add_row(
                    str(d.date),
                    str(d.attributions),
                    str(d.matches),
                    str(d.impressions),
                    f"${d.earnings_cents / 100:.2f}",
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


@bot_earnings.command("attributions")
@click.argument("bot_player_id")
@click.option("--start", default=None, help="Start date (YYYY-MM-DD).")
@click.option("--end", default=None, help="End date (YYYY-MM-DD).")
@click.option("--limit", default=50, type=int)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def attributions(
    bot_player_id: str,
    start: str | None,
    end: str | None,
    limit: int,
    config_path: str,
) -> None:
    """List attribution entries for a bot."""

    async def _do(svc: BotEarningsService, ctx: Any) -> None:
        try:
            pid = PlayerId(UUID(bot_player_id))
            sd = date.fromisoformat(start) if start else None
            ed = date.fromisoformat(end) if end else None
            result = await svc.get_attribution_entries(pid, sd, ed, limit=limit)
            if not result.items:
                console.print("No attribution entries found.")
                return
            table = Table(title="Attribution Entries")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Date")
            table.add_column("Match", no_wrap=True)
            table.add_column("Attributed", justify="right")
            table.add_column("Share %", justify="right")
            table.add_column("Recorded")
            for a in result.items:
                table.add_row(
                    str(a.id)[:8] + "...",
                    str(a.attribution_date),
                    str(a.match_id)[:8] + "...",
                    f"${a.attributed_cents / 100:.2f}",
                    f"{a.attribution_share_percent:.1f}%",
                    str(a.recorded_at),
                )
            console.print(table)
            console.print(f"\nShowing {len(result.items)} of {result.total}")
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    _run_async(_do, config_path)


@bot_earnings.command("sync")
@click.argument("bot_player_id")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def sync(bot_player_id: str, config_path: str) -> None:
    """Sync attributions for a bot."""

    async def _do(svc: BotEarningsService, ctx: Any) -> None:
        try:
            pid = PlayerId(UUID(bot_player_id))
            result = await svc.sync_attributions(pid)
            console.print(
                Panel(
                    f"[bold green]Sync complete![/bold green]\n\n"
                    f"  New attributions: {result.new_attributions}\n"
                    f"  New earnings:     ${result.new_earnings_cents / 100:.2f}\n"
                    f"  Duration:         {(result.sync_end - result.sync_start).total_seconds():.1f}s\n"
                    f"  Errors:           {len(result.errors)}",
                    title=f"Attribution Sync: {bot_player_id[:8]}...",
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


@bot_earnings.command("sync-all")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def sync_all(config_path: str) -> None:
    """Bulk sync attributions for all bots."""

    async def _do(svc: BotEarningsService, ctx: Any) -> None:
        try:
            result = await svc.sync_all_attributions()
            console.print(
                Panel(
                    f"[bold green]Bulk sync complete![/bold green]\n\n"
                    f"  Bots synced:       {result.bots_synced}\n"
                    f"  New attributions:  {result.total_new_attributions}\n"
                    f"  New earnings:      ${result.total_new_earnings_cents / 100:.2f}\n"
                    f"  Duration:          {(result.sync_end - result.sync_start).total_seconds():.1f}s\n"
                    f"  Errors:            {len(result.errors)}",
                    title="Bulk Attribution Sync",
                )
            )
            if result.errors:
                for bot_id, err in result.errors:
                    console.print(f"  [red]Error[/red] {str(bot_id)[:8]}...: {err}")
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    _run_async(_do, config_path)


@bot_earnings.command("request-payout")
@click.argument("bot_player_id")
@click.option("--owner", required=True, help="Owner player ID (UUID).")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def request_payout(bot_player_id: str, owner: str, config_path: str) -> None:
    """Request a payout for bot earnings."""

    async def _do(svc: BotEarningsService, ctx: Any) -> None:
        try:
            pid = PlayerId(UUID(bot_player_id))
            oid = PlayerId(UUID(owner))
            p = await svc.request_payout(pid, oid)
            console.print(
                Panel(
                    f"[bold green]Payout request created![/bold green]\n\n"
                    f"  Request ID: {p.id}\n"
                    f"  Amount:     ${p.amount_cents / 100:.2f}\n"
                    f"  Status:     {p.status.value}",
                    title="Payout Request",
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


@bot_earnings.command("payout-requests")
@click.argument("bot_player_id")
@click.option(
    "--status",
    type=click.Choice(["pending", "processing", "completed", "rejected", "cancelled"]),
    default=None,
)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def payout_requests(bot_player_id: str, status: str | None, config_path: str) -> None:
    """List payout requests for a bot."""

    async def _do(svc: BotEarningsService, ctx: Any) -> None:
        try:
            pid = PlayerId(UUID(bot_player_id))
            ps = PayoutStatus(status) if status else None
            result = await svc.get_payout_requests(pid, ps)
            if not result.items:
                console.print("No payout requests found.")
                return
            table = Table(title="Payout Requests")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Amount", justify="right")
            table.add_column("Status")
            table.add_column("Requested")
            table.add_column("Processed")
            for p in result.items:
                table.add_row(
                    str(p.id)[:8] + "...",
                    f"${p.amount_cents / 100:.2f}",
                    p.status.value,
                    str(p.requested_at),
                    str(p.processed_at) if p.processed_at else "N/A",
                )
            console.print(table)
            console.print(f"\nShowing {len(result.items)} of {result.total}")
        except AppError as e:
            console.print(
                Panel(
                    f"[bold red]{e.message}[/bold red]\n  Code: {e.code}",
                    title="Error",
                    border_style="red",
                )
            )

    _run_async(_do, config_path)


@bot_earnings.command("cancel-payout")
@click.argument("payout_request_id")
@click.option("--owner", required=True, help="Owner player ID (UUID).")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def cancel_payout(payout_request_id: str, owner: str, config_path: str) -> None:
    """Cancel a pending payout request."""

    async def _do(svc: BotEarningsService, ctx: Any) -> None:
        try:
            prid = PayoutRequestId(UUID(payout_request_id))
            oid = PlayerId(UUID(owner))
            p = await svc.cancel_payout_request(prid, oid)
            console.print(
                Panel(
                    f"[bold yellow]Payout cancelled[/bold yellow]\n\n"
                    f"  Request ID: {p.id}\n"
                    f"  Amount:     ${p.amount_cents / 100:.2f}\n"
                    f"  Status:     {p.status.value}",
                    title="Payout Cancelled",
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


@bot_earnings.command("process-payout")
@click.argument("payout_request_id")
@click.option("--processor", required=True, help="Admin player ID (UUID).")
@click.option("--reference", default=None, help="External payment reference.")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def process_payout(
    payout_request_id: str,
    processor: str,
    reference: str | None,
    config_path: str,
) -> None:
    """Process a pending payout request (admin)."""

    async def _do(svc: BotEarningsService, ctx: Any) -> None:
        try:
            prid = PayoutRequestId(UUID(payout_request_id))
            proc = PlayerId(UUID(processor))
            p = await svc.process_payout(prid, proc, external_reference=reference)
            console.print(
                Panel(
                    f"[bold green]Payout processed![/bold green]\n\n"
                    f"  Request ID:  {p.id}\n"
                    f"  Amount:      ${p.amount_cents / 100:.2f}\n"
                    f"  Processed by: {p.processed_by}\n"
                    f"  Reference:   {p.external_reference or 'N/A'}",
                    title="Payout Processed",
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


@bot_earnings.command("reject-payout")
@click.argument("payout_request_id")
@click.option("--processor", required=True, help="Admin player ID (UUID).")
@click.option("--reason", required=True, help="Rejection reason.")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def reject_payout(
    payout_request_id: str,
    processor: str,
    reason: str,
    config_path: str,
) -> None:
    """Reject a pending payout request (admin)."""

    async def _do(svc: BotEarningsService, ctx: Any) -> None:
        try:
            prid = PayoutRequestId(UUID(payout_request_id))
            proc = PlayerId(UUID(processor))
            p = await svc.reject_payout(prid, proc, reason)
            console.print(
                Panel(
                    f"[bold yellow]Payout rejected[/bold yellow]\n\n"
                    f"  Request ID: {p.id}\n"
                    f"  Amount:     ${p.amount_cents / 100:.2f}\n"
                    f"  Reason:     {p.rejection_reason}",
                    title="Payout Rejected",
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


@bot_earnings.command("pending-payouts")
@click.option(
    "--past-hold-only", is_flag=True, default=False, help="Only show past hold period."
)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def pending_payouts(past_hold_only: bool, config_path: str) -> None:
    """List pending payout requests."""

    async def _do(svc: BotEarningsService, ctx: Any) -> None:
        try:
            payouts = await svc.get_pending_payouts(past_hold_only=past_hold_only)

            if not payouts:
                console.print("No pending payout requests found.")
                return

            table = Table(title="Pending Payouts")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Bot", no_wrap=True)
            table.add_column("Amount", justify="right")
            table.add_column("Status")
            table.add_column("Requested")
            for p in payouts:
                table.add_row(
                    str(p.id)[:8] + "...",
                    str(p.bot_player_id)[:8] + "...",
                    f"${p.amount_cents / 100:.2f}",
                    p.status.value,
                    str(p.requested_at),
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
