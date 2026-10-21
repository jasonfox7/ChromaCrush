"""CLI commands for the ads module.

Provides Click commands for ad lifecycle management: ad-free status,
interstitial and rewarded ad simulation, banner impressions, player
stats, bot attribution reports, and event ad opportunities.

All ads-related imports are guarded behind try/except so the CLI
registers cleanly even when the ads module is not yet available.

Commands:
    ads check-status           -- Check player ad-free status
    ads grant-ad-free          -- Grant ad-free status
    ads revoke-ad-free         -- Revoke ad-free status
    ads request-interstitial   -- Request interstitial ad
    ads record-interstitial    -- Record interstitial impression
    ads request-rewarded       -- Request rewarded video
    ads complete-rewarded      -- Complete rewarded video
    ads record-banner          -- Record banner impression
    ads player-stats           -- Show player ad statistics
    ads impressions            -- List player ad impressions
    ads match-attribution      -- Show match ad attribution
    ads bot-report             -- Show bot ad attribution report
    ads event-opportunities    -- List event ad opportunities
    ads claim-opportunity      -- Claim event ad opportunity
"""

from __future__ import annotations

from datetime import date
from typing import Any
from uuid import UUID

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.cli.helpers.async_bridge import resolve_player, run_cli_async
from src.core.composition_root import ApplicationContext
from src.core.errors import AppError
from src.core.types.game import EventId, MatchId, PlayerId

# ---------------------------------------------------------------------------
# Guarded ads imports
# ---------------------------------------------------------------------------
_ADS_AVAILABLE = False
try:
    from src.modules.ads.service import AdRepositoryBundle, AdService
    from src.modules.ads.types import (
        AdFreeReason,
        AdRequestId,
        AdType,
        BannerPlacement,
        InterstitialTrigger,
        RewardedAdType,
        StatsPeriod,
    )

    _ADS_AVAILABLE = True
except ImportError:
    pass

console = Console()


def _ads_unavailable() -> None:
    """Print a warning that the ads module is not available."""
    console.print("[yellow]Ads module not available yet.[/yellow]")


def _run_async(coro_factory: Any, config_path: str = "config/app.toml") -> None:
    """Bridge sync Click commands to async AdService operations."""

    async def _bridge(ctx: ApplicationContext) -> None:
        await coro_factory(_build_ad_service(ctx), ctx)

    run_cli_async(_bridge, config_path)


def _build_ad_service(ctx: ApplicationContext) -> Any:
    """Build an AdService from the application context."""
    from src.data.repositories.ad_free_status_repository import (
        SQLAlchemyAdFreeStatusRepository,
    )
    from src.data.repositories.ad_impression_repository import (
        SQLAlchemyAdImpressionRepository,
    )
    from src.data.repositories.ad_request_repository import (
        SQLAlchemyAdRequestRepository,
    )
    from src.data.repositories.ad_reward_repository import (
        SQLAlchemyAdRewardRepository,
    )
    from src.data.repositories.energy_state_repository import (
        SQLAlchemyEnergyStateRepository,
    )
    from src.data.repositories.event_ad_claim_repository import (
        SQLAlchemyEventAdClaimRepository,
    )
    from src.data.repositories.event_ad_opportunity_repository import (
        SQLAlchemyEventAdOpportunityRepository,
    )
    from src.data.repositories.player_stats_repository import (
        SQLAlchemyPlayerStatsRepository,
    )
    from src.modules.ads.service import AdRepositoryBundle, AdService
    from src.modules.ads.types import AdProviderResponse
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

    # Minimal events service stub (only get_event and get_event_participant)
    class _EventServiceStub:
        def __init__(self, data_ctx: Any) -> None:
            self._data_ctx = data_ctx

        async def get_event(self, event_id: EventId) -> Any:
            from src.data.repositories.event_repository import (
                SQLAlchemyEventRepository,
            )

            repo = SQLAlchemyEventRepository(
                self._data_ctx,
                ctx.logger,
                ctx.errors,
            )
            return await repo.find_by_id(event_id)

        async def get_event_participant(
            self,
            event_id: EventId,
            player_id: PlayerId,
        ) -> Any:
            return None  # Stub for CLI purposes

    events_stub = _EventServiceStub(ctx.data_ctx)

    # Mock ad provider for CLI testing
    class _MockAdProvider:
        async def request_interstitial(
            self,
            ad_unit_id: str,
            user_id: str,
        ) -> Any:
            return AdProviderResponse(ad_available=True, ad_data={"provider": "mock"})

        async def request_rewarded_video(
            self,
            ad_unit_id: str,
            user_id: str,
        ) -> Any:
            return AdProviderResponse(ad_available=True, ad_data={"provider": "mock"})

        async def verify_impression(
            self,
            ad_request_id: str,
            impression_data: dict[str, Any],
        ) -> bool:
            return True

        async def get_estimated_cpm(self, ad_type: str) -> int:
            return 200

    # Ad repositories
    repos = AdRepositoryBundle(
        ad_request=SQLAlchemyAdRequestRepository(
            ctx.data_ctx,
            ctx.logger,
            ctx.errors,
        ),
        ad_impression=SQLAlchemyAdImpressionRepository(
            ctx.data_ctx,
            ctx.logger,
            ctx.errors,
        ),
        ad_free_status=SQLAlchemyAdFreeStatusRepository(
            ctx.data_ctx,
            ctx.logger,
            ctx.errors,
        ),
        ad_reward=SQLAlchemyAdRewardRepository(
            ctx.data_ctx,
            ctx.logger,
            ctx.errors,
        ),
        event_opportunity=SQLAlchemyEventAdOpportunityRepository(
            ctx.data_ctx,
            ctx.logger,
            ctx.errors,
        ),
        event_claim=SQLAlchemyEventAdClaimRepository(
            ctx.data_ctx,
            ctx.logger,
            ctx.errors,
        ),
    )

    return AdService(
        config=ctx.config,
        logger=ctx.logger,
        errors=ctx.errors,
        player_service=player_service,
        events_service=events_stub,
        repos=repos,
        ad_provider=_MockAdProvider(),
    )


@click.group()
def ads() -> None:
    """Ad management commands."""


@ads.command("check-status")
@click.argument("player_username")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def check_status(player_username: str, config_path: str) -> None:
    """Check player ad-free status."""
    if not _ADS_AVAILABLE:
        _ads_unavailable()
        return

    async def _do(svc: Any, ctx: Any) -> None:
        try:
            pid = PlayerId(await resolve_player(ctx, player_username))
            st = await svc.check_ad_free_status(pid)
            status_text = "Ad-free" if st.is_ad_free else "Not ad-free"
            lines = [
                f"  Status:    {status_text}",
                f"  Reason:    {st.reason.value if st.reason else 'N/A'}",
                f"  Permanent: {st.is_permanent}",
            ]
            if st.expires_at:
                lines.append(f"  Expires:   {st.expires_at}")
            if st.granted_at:
                lines.append(f"  Granted:   {st.granted_at}")
            console.print(
                Panel("\n".join(lines), title=f"Ad-Free Status: {player_username}")
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


@ads.command("grant-ad-free")
@click.argument("player_username")
@click.option(
    "--reason",
    required=True,
    type=click.Choice(["purchase", "promotion", "admin_grant"]),
)
@click.option(
    "--days", default=None, type=int, help="Duration in days (omit for permanent)."
)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def grant_ad_free(
    player_username: str, reason: str, days: int | None, config_path: str
) -> None:
    """Grant ad-free status to a player."""
    if not _ADS_AVAILABLE:
        _ads_unavailable()
        return

    async def _do(svc: Any, ctx: Any) -> None:
        try:
            pid = PlayerId(await resolve_player(ctx, player_username))
            r = AdFreeReason(reason)
            st = await svc.grant_ad_free_status(pid, r, duration_days=days)
            dur = f"{days} days" if days else "Permanent"
            console.print(
                Panel(
                    f"[bold green]Ad-free status granted![/bold green]\n\n"
                    f"  Player:   {player_username}\n"
                    f"  Reason:   {reason}\n"
                    f"  Duration: {dur}\n"
                    f"  Granted:  {st.granted_at}",
                    title="Grant Ad-Free",
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


@ads.command("revoke-ad-free")
@click.argument("player_username")
@click.option("--reason", required=True, help="Revocation reason.")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def revoke_ad_free(player_username: str, reason: str, config_path: str) -> None:
    """Revoke ad-free status from a player."""
    if not _ADS_AVAILABLE:
        _ads_unavailable()
        return

    async def _do(svc: Any, ctx: Any) -> None:
        try:
            pid = PlayerId(await resolve_player(ctx, player_username))
            await svc.revoke_ad_free_status(pid, reason)
            console.print(
                Panel(
                    f"[bold yellow]Ad-free status revoked[/bold yellow]\n\n"
                    f"  Player: {player_username}\n"
                    f"  Reason: {reason}",
                    title="Revoke Ad-Free",
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


@ads.command("request-interstitial")
@click.argument("player_username")
@click.option(
    "--trigger",
    required=True,
    type=click.Choice(["match_end", "level_start", "menu_transition"]),
)
@click.option("--match", "match_id", default=None, help="Match ID (UUID).")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def request_interstitial(
    player_username: str, trigger: str, match_id: str | None, config_path: str
) -> None:
    """Request an interstitial ad."""
    if not _ADS_AVAILABLE:
        _ads_unavailable()
        return

    async def _do(svc: Any, ctx: Any) -> None:
        try:
            pid = PlayerId(await resolve_player(ctx, player_username))
            mid = MatchId(UUID(match_id)) if match_id else None
            t = InterstitialTrigger(trigger)
            result = await svc.request_interstitial(pid, t, mid)
            console.print(
                Panel(
                    f"[bold green]Interstitial requested![/bold green]\n\n"
                    f"  Request ID: {result.ad_request_id}\n"
                    f"  Ad available: {'Yes' if result.should_show else 'No'}\n"
                    f"  Created: {result.created_at}",
                    title="Interstitial Request",
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


@ads.command("record-interstitial")
@click.argument("ad_request_id")
@click.option("--viewed/--not-viewed", default=True, help="Whether ad was viewed.")
@click.option("--duration", required=True, type=int, help="View duration in ms.")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def record_interstitial(
    ad_request_id: str, viewed: bool, duration: int, config_path: str
) -> None:
    """Record an interstitial impression."""
    if not _ADS_AVAILABLE:
        _ads_unavailable()
        return

    async def _do(svc: Any, ctx: Any) -> None:
        try:
            rid = AdRequestId(UUID(ad_request_id))
            imp = await svc.record_interstitial_impression(rid, viewed, duration)
            console.print(
                Panel(
                    f"[bold green]Interstitial recorded![/bold green]\n\n"
                    f"  Viewed:   {'Yes' if imp.viewed else 'No'}\n"
                    f"  Duration: {imp.view_duration_ms}ms\n"
                    f"  Revenue:  {(imp.estimated_revenue_cents or 0) / 100:.3f}",
                    title="Impression Recorded",
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


@ads.command("request-rewarded")
@click.argument("player_username")
@click.option(
    "--reward-type",
    required=True,
    type=click.Choice(["bonus_heart", "score_boost", "extra_moves"]),
)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def request_rewarded(player_username: str, reward_type: str, config_path: str) -> None:
    """Request a rewarded video."""
    if not _ADS_AVAILABLE:
        _ads_unavailable()
        return

    async def _do(svc: Any, ctx: Any) -> None:
        try:
            pid = PlayerId(await resolve_player(ctx, player_username))
            rt = RewardedAdType(reward_type)
            result = await svc.request_rewarded_video(pid, rt)
            console.print(
                Panel(
                    f"[bold green]Rewarded video requested![/bold green]\n\n"
                    f"  Request ID:  {result.ad_request_id}\n"
                    f"  Available:   {'Yes' if result.video_available else 'No'}\n"
                    f"  Reward type: {result.reward_type.value}\n"
                    f"  Reward value: {result.reward_value}\n"
                    f"  Expires:     {result.expires_at}",
                    title="Rewarded Video Request",
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


@ads.command("complete-rewarded")
@click.argument("ad_request_id")
@click.option(
    "--completed/--abandoned", default=True, help="Whether video was fully watched."
)
@click.option("--duration", required=True, type=int, help="Watch duration in ms.")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def complete_rewarded(
    ad_request_id: str, completed: bool, duration: int, config_path: str
) -> None:
    """Complete a rewarded video."""
    if not _ADS_AVAILABLE:
        _ads_unavailable()
        return

    async def _do(svc: Any, ctx: Any) -> None:
        try:
            rid = AdRequestId(UUID(ad_request_id))
            result = await svc.complete_rewarded_video(rid, completed, duration)
            reward_text = (
                f"  Reward: {result.reward_type.value} x{result.reward_value}"
                if result.reward_granted
                else "  Reward: None (not granted)"
            )
            console.print(
                Panel(
                    f"[bold green]Rewarded video completed![/bold green]\n\n"
                    f"  Completed:  {'Yes' if result.completed else 'No'}\n"
                    f"  Duration:   {result.watched_duration_ms}ms\n"
                    f"  Granted:    {'Yes' if result.reward_granted else 'No'}\n"
                    f"{reward_text}",
                    title="Rewarded Video Result",
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


@ads.command("record-banner")
@click.argument("player_username")
@click.option(
    "--placement",
    required=True,
    type=click.Choice(["home_bottom", "match_result", "shop_banner"]),
)
@click.option("--duration", required=True, type=int, help="View duration in ms.")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def record_banner(
    player_username: str, placement: str, duration: int, config_path: str
) -> None:
    """Record a banner impression."""
    if not _ADS_AVAILABLE:
        _ads_unavailable()
        return

    async def _do(svc: Any, ctx: Any) -> None:
        try:
            pid = PlayerId(await resolve_player(ctx, player_username))
            bp = BannerPlacement(placement)
            imp = await svc.record_banner_impression(pid, bp, duration)
            console.print(
                Panel(
                    f"[bold green]Banner recorded![/bold green]\n\n"
                    f"  Placement: {placement}\n"
                    f"  Duration:  {imp.view_duration_ms}ms\n"
                    f"  Revenue:   {(imp.estimated_revenue_cents or 0) / 100:.3f}",
                    title="Banner Impression",
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


@ads.command("player-stats")
@click.argument("player_username")
@click.option(
    "--period",
    type=click.Choice(["day", "week", "month", "lifetime"]),
    default="lifetime",
)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def player_stats(player_username: str, period: str, config_path: str) -> None:
    """Show player ad statistics."""
    if not _ADS_AVAILABLE:
        _ads_unavailable()
        return

    async def _do(svc: Any, ctx: Any) -> None:
        try:
            pid = PlayerId(await resolve_player(ctx, player_username))
            p = StatsPeriod(period)
            stats = await svc.get_player_ad_stats(pid, p)
            console.print(
                Panel(
                    f"  Total impressions:  {stats.total_impressions}\n"
                    f"  Interstitials:      {stats.interstitial_count}\n"
                    f"  Rewarded videos:    {stats.rewarded_video_count}\n"
                    f"  Banners:            {stats.banner_impression_count}\n"
                    f"  Rewards earned:     {stats.total_rewards_earned}\n"
                    f"  Avg view duration:  {stats.average_view_duration_ms}ms\n"
                    f"  Last ad:            {stats.last_ad_at or 'Never'}",
                    title=f"Ad Stats: {player_username} ({period})",
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


@ads.command("impressions")
@click.argument("player_username")
@click.option(
    "--type",
    "ad_type",
    type=click.Choice(["interstitial", "rewarded", "banner"]),
    default=None,
)
@click.option("--limit", default=50, type=int)
@click.option("--offset", default=0, type=int)
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def impressions(
    player_username: str, ad_type: str | None, limit: int, offset: int, config_path: str
) -> None:
    """List player ad impressions."""
    if not _ADS_AVAILABLE:
        _ads_unavailable()
        return

    async def _do(svc: Any, ctx: Any) -> None:
        try:
            pid = PlayerId(await resolve_player(ctx, player_username))
            t = AdType(ad_type) if ad_type else None
            result = await svc.get_ad_impressions(pid, t, limit, offset)
            if not result.items:
                console.print("No impressions found.")
                return
            table = Table(title="Ad Impressions")
            table.add_column("ID", style="cyan", no_wrap=True)
            table.add_column("Type")
            table.add_column("Viewed")
            table.add_column("Duration", justify="right")
            table.add_column("Revenue", justify="right")
            table.add_column("Created")
            for imp in result.items:
                table.add_row(
                    str(imp.id)[:8] + "...",
                    imp.ad_type.value,
                    "Yes" if imp.viewed else "No",
                    f"{imp.view_duration_ms}ms",
                    f"${(imp.estimated_revenue_cents or 0) / 100:.3f}",
                    str(imp.created_at),
                )
            console.print(table)
            console.print(
                f"\nShowing {offset + 1}-{offset + len(result.items)} of {result.total}"
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


@ads.command("match-attribution")
@click.argument("match_id")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def match_attribution(match_id: str, config_path: str) -> None:
    """Show match ad attribution."""
    if not _ADS_AVAILABLE:
        _ads_unavailable()
        return

    async def _do(svc: Any, ctx: Any) -> None:
        try:
            mid = MatchId(UUID(match_id))
            attr = await svc.get_match_ad_attribution(mid)
            console.print(
                Panel(
                    f"  Match:         {attr.match_id}\n"
                    f"  Player 1:      {str(attr.player1_id)[:8]}... (bot: {attr.player1_is_bot})\n"
                    f"  Player 2:      {str(attr.player2_id)[:8]}... (bot: {attr.player2_is_bot})\n"
                    f"  Impressions:   {attr.total_impressions}\n"
                    f"  Revenue:       ${attr.estimated_revenue_cents / 100:.3f}\n"
                    f"  Bot attributed: ${attr.bot_attribution_cents / 100:.3f}",
                    title="Match Ad Attribution",
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


@ads.command("bot-report")
@click.argument("bot_player_username")
@click.option("--start", required=True, help="Start date (YYYY-MM-DD).")
@click.option("--end", required=True, help="End date (YYYY-MM-DD).")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def bot_report(bot_player_username: str, start: str, end: str, config_path: str) -> None:
    """Show bot ad attribution report."""
    if not _ADS_AVAILABLE:
        _ads_unavailable()
        return

    async def _do(svc: Any, ctx: Any) -> None:
        try:
            pid = PlayerId(await resolve_player(ctx, bot_player_username))
            sd = date.fromisoformat(start)
            ed = date.fromisoformat(end)
            report = await svc.get_bot_ad_attributions(pid, sd, ed)
            lines = [
                f"  Period:            {report.start_date} to {report.end_date}",
                f"  Total matches:     {report.total_matches}",
                f"  With impressions:  {report.matches_with_impressions}",
                f"  Attributed imps:   {report.total_attributed_impressions}",
                f"  Est. revenue:      ${report.estimated_revenue_cents / 100:.2f}",
                f"  Attributed rev:    ${report.attributed_revenue_cents / 100:.2f} ({report.attribution_share_percent}%)",
            ]
            if report.daily_breakdown:
                lines.append(f"\n  Daily breakdown (first 5 days):")
                for d in report.daily_breakdown[:5]:
                    lines.append(
                        f"    {d.date}: {d.matches} matches, {d.impressions} impressions, ${d.attributed_cents / 100:.2f} attributed"
                    )
            console.print(
                Panel("\n".join(lines), title=f"Bot Report: {bot_player_username}")
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


@ads.command("event-opportunities")
@click.argument("event_id")
@click.option("--player", required=True, help="Player username.")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def event_opportunities(event_id: str, player: str, config_path: str) -> None:
    """List event ad opportunities for a player."""
    if not _ADS_AVAILABLE:
        _ads_unavailable()
        return

    async def _do(svc: Any, ctx: Any) -> None:
        try:
            eid = EventId(UUID(event_id))
            pid = PlayerId(await resolve_player(ctx, player))
            opps = await svc.get_event_ad_opportunities(pid, eid)
            if not opps:
                console.print("No ad opportunities for this event.")
                return
            table = Table(title="Event Ad Opportunities")
            table.add_column("ID", style="cyan")
            table.add_column("Type")
            table.add_column("Reward")
            table.add_column("Claimed", justify="right")
            table.add_column("Available")
            for o in opps:
                table.add_row(
                    o.opportunity_id,
                    o.ad_type.value,
                    f"{o.reward_type} x{o.reward_value}",
                    f"{o.times_claimed}/{o.times_available}",
                    "Yes" if o.available else "No",
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


@ads.command("claim-opportunity")
@click.argument("event_id")
@click.argument("opportunity_id")
@click.option("--player", required=True, help="Player username.")
@click.option("--config", "config_path", default="config/app.toml", show_default=True)
def claim_opportunity(
    event_id: str, opportunity_id: str, player: str, config_path: str
) -> None:
    """Claim an event ad opportunity."""
    if not _ADS_AVAILABLE:
        _ads_unavailable()
        return

    async def _do(svc: Any, ctx: Any) -> None:
        try:
            eid = EventId(UUID(event_id))
            pid = PlayerId(await resolve_player(ctx, player))
            result = await svc.claim_event_ad_reward(pid, eid, opportunity_id)
            console.print(
                Panel(
                    f"[bold green]Opportunity claimed![/bold green]\n\n"
                    f"  Opportunity: {result.opportunity_id}\n"
                    f"  Reward:      {result.reward_type} x{result.reward_value}\n"
                    f"  Claimed at:  {result.claimed_at}",
                    title="Event Ad Claim",
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
