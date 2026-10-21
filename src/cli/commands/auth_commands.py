"""CLI commands for the auth module.

Provides Click commands for authentication, session management, API key
management, and password utilities. Uses ``run_cli_async`` to bridge
synchronous Click commands to the fully async AuthService via
ApplicationContext.

Commands:
    auth hash-password    -- Hash a password with bcrypt (via AuthService)
    auth verify-password  -- Verify a password against a hash (via AuthService)
    auth show-config      -- Display auth configuration values
    auth login            -- Authenticate and get tokens (async)
    auth validate-token   -- Validate a JWT or API key (async)
    auth refresh          -- Refresh tokens (async)
    auth logout           -- Invalidate sessions (async)
    auth sessions         -- List active sessions (async)
    auth create-key       -- Create an API key for a bot (async)
    auth list-keys        -- List API keys for a player (async)
    auth revoke-key       -- Revoke an API key (async)
    auth rate-limit       -- Check rate limit for an API key (async)
    auth cleanup-sessions -- Delete expired sessions (async)
"""

from __future__ import annotations

from uuid import UUID

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.cli.helpers.async_bridge import resolve_player, run_cli_async
from src.core.composition_root import ApplicationContext, load_config
from src.core.errors import AppError
from src.core.types.game import PlayerId

console = Console()


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------


@click.group()
def auth() -> None:
    """Authentication management commands."""


# ---------------------------------------------------------------------------
# Password commands (route through AuthService for validation)
# ---------------------------------------------------------------------------


@auth.command("hash-password")
@click.argument("password")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def hash_password(password: str, config_path: str) -> None:
    """Hash a password with bcrypt (routes through AuthService for validation)."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            hashed = ctx.auth_service.hash_password(password)
            console.print(f"[bold green]Hash:[/bold green] {hashed}")
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)


@auth.command("verify-password")
@click.argument("password")
@click.argument("hash_value", metavar="HASH")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def verify_password(password: str, hash_value: str, config_path: str) -> None:
    """Verify a password against a bcrypt hash (routes through AuthService)."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            match = ctx.auth_service.verify_password(password, hash_value)
            if match:
                console.print("[bold green]Password matches![/bold green]")
            else:
                console.print("[bold red]Password does not match.[/bold red]")
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)


@auth.command("show-config")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def show_config(config_path: str) -> None:
    """Display auth configuration values."""
    config = load_config(config_path)

    table = Table(title="Auth Configuration", show_header=True)
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="yellow")

    rows: list[tuple[str, str]] = [
        ("jwt_algorithm", str(config.get("auth.jwt_algorithm", "HS256"))),
        (
            "access_token_expiry_minutes",
            str(config.get("auth.access_token_expiry_minutes", 60)),
        ),
        (
            "refresh_token_expiry_days",
            str(config.get("auth.refresh_token_expiry_days", 30)),
        ),
        ("api_key_prefix", str(config.get("auth.api_key_prefix", "cc_"))),
        ("api_key_length", str(config.get("auth.api_key_length", 32))),
        ("bcrypt_rounds", str(config.get("auth.bcrypt_rounds", 12))),
        ("password_min_length", str(config.get("auth.password_min_length", 8))),
        ("rate_limit_requests", str(config.get("auth.rate_limit_requests", 100))),
        (
            "rate_limit_window_seconds",
            str(config.get("auth.rate_limit_window_seconds", 60)),
        ),
        (
            "max_sessions_per_player",
            str(config.get("auth.max_sessions_per_player", 5)),
        ),
        ("jwt_secret", "[SET]" if config.get("auth.jwt_secret") else "[NOT SET]"),
    ]

    for key, value in rows:
        table.add_row(key, value)

    console.print(table)


# ---------------------------------------------------------------------------
# Async commands
# ---------------------------------------------------------------------------


@auth.command("login")
@click.option("--username", required=True, help="Player username")
@click.option("--password", required=True, help="Player password")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def login(username: str, password: str, config_path: str) -> None:
    """Authenticate and get tokens."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            result = await ctx.auth_service.authenticate(username, password)

            console.print("[bold green]Authentication successful![/bold green]")
            console.print(f"  Access Token:  {result.access_token[:20]}...")
            console.print(f"  Refresh Token: {result.refresh_token[:20]}...")
            console.print(f"  Expires In:    {result.expires_in} seconds")
            console.print(f"  Token Type:    {result.token_type}")
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)


@auth.command("validate-token")
@click.argument("token")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def validate_token(token: str, config_path: str) -> None:
    """Validate a JWT or API key."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            auth_token = await ctx.auth_service.validate_token(token)

            console.print("[bold green]Token valid![/bold green]")
            console.print(f"  Type:       {auth_token.token_type.value}")
            console.print(f"  Player ID:  {auth_token.player_id}")
            console.print(f"  Issued At:  {auth_token.issued_at}")
            if auth_token.expires_at:
                console.print(f"  Expires At: {auth_token.expires_at}")
            else:
                console.print("  Expires At: Never (API key)")
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)


@auth.command("refresh")
@click.option("--refresh-token", required=True, help="Refresh token")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def refresh(refresh_token: str, config_path: str) -> None:
    """Refresh access token using a refresh token."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            result = await ctx.auth_service.refresh_token(refresh_token)

            console.print("[bold green]Token refreshed![/bold green]")
            console.print(f"  Access Token:  {result.access_token[:20]}...")
            console.print(f"  Refresh Token: {result.refresh_token[:20]}...")
            console.print(f"  Expires In:    {result.expires_in} seconds")
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)


@auth.command("logout")
@click.argument("player_username")
@click.option("--session-id", default=None, help="Specific session to revoke")
@click.option("--all", "revoke_all", is_flag=True, help="Revoke all sessions")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def logout(
    player_username: str,
    session_id: str | None,
    revoke_all: bool,
    config_path: str,
) -> None:
    """Invalidate sessions for a player."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            sid = UUID(session_id) if session_id else None
            if revoke_all:
                sid = None

            await ctx.auth_service.logout(
                PlayerId(player_id), session_id=sid
            )
            console.print("[bold green]Session(s) invalidated.[/bold green]")
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)


@auth.command("sessions")
@click.argument("player_username")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def sessions(player_username: str, config_path: str) -> None:
    """List active sessions for a player."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            session_list = await ctx.auth_service.get_active_sessions(
                PlayerId(player_id)
            )

            if not session_list:
                console.print("No active sessions.")
                return

            table = Table(title=f"Active Sessions for {player_username}")
            table.add_column("Session ID", style="cyan", no_wrap=True)
            table.add_column("Created", style="green")
            table.add_column("Last Used", style="yellow")
            table.add_column("Expires", style="red")
            table.add_column("Device")

            for s in session_list:
                table.add_row(
                    str(s.session_id)[:8] + "...",
                    str(s.created_at),
                    str(s.last_used_at),
                    str(s.expires_at),
                    s.device_info or "",
                )

            console.print(table)
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)


@auth.command("create-key")
@click.argument("player_username")
@click.option("--description", default=None, help="Key description")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def create_key(player_username: str, description: str | None, config_path: str) -> None:
    """Create an API key for a bot player."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            result = await ctx.auth_service.create_api_key(
                PlayerId(player_id),
                description=description,
            )

            console.print("[bold green]API key created![/bold green]")
            console.print(f"  Key ID:  {result.key_info.key_id}")
            console.print(f"  Prefix:  {result.key_info.prefix}")
            console.print()
            console.print(
                "[bold yellow]IMPORTANT: Save this key now. "
                "It will not be shown again:[/bold yellow]"
            )
            console.print(f"  {result.raw_key}")
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)


@auth.command("list-keys")
@click.argument("player_username")
@click.option("--include-revoked", is_flag=True, help="Include revoked keys")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def list_keys(player_username: str, include_revoked: bool, config_path: str) -> None:
    """List API keys for a player."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            keys = await ctx.auth_service.list_api_keys(
                PlayerId(player_id),
                include_revoked=include_revoked,
            )

            if not keys:
                console.print("No API keys found.")
                return

            table = Table(title=f"API Keys for {player_username}")
            table.add_column("Status", style="bold")
            table.add_column("Key ID", style="cyan", no_wrap=True)
            table.add_column("Prefix", style="green")
            table.add_column("Created", style="yellow")
            table.add_column("Last Used")

            for key in keys:
                status = (
                    "[red]REVOKED[/red]" if key.revoked else "[green]ACTIVE[/green]"
                )
                last_used = str(key.last_used_at) if key.last_used_at else "Never"
                table.add_row(
                    status,
                    str(key.key_id)[:8] + "...",
                    key.prefix,
                    str(key.created_at),
                    last_used,
                )

            console.print(table)
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)


@auth.command("revoke-key")
@click.argument("key_id")
@click.option("--player", "player_username", required=True, help="Owner player username")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def revoke_key(key_id: str, player_username: str, config_path: str) -> None:
    """Revoke an API key."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            player_id = await resolve_player(ctx, player_username)
            await ctx.auth_service.revoke_api_key(
                UUID(key_id),
                PlayerId(player_id),
            )
            console.print("[bold green]API key revoked.[/bold green]")
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)


@auth.command("rate-limit")
@click.argument("key_id")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def rate_limit(key_id: str, config_path: str) -> None:
    """Check rate limit status for an API key."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            status = await ctx.auth_service.check_rate_limit(UUID(key_id))

            table = Table(title=f"Rate Limit for {key_id[:8]}...")
            table.add_column("Field", style="cyan")
            table.add_column("Value", style="yellow")

            table.add_row("Requests Remaining", str(status.requests_remaining))
            table.add_row("Requests Limit", str(status.requests_limit))
            table.add_row("Window (seconds)", str(status.window_seconds))
            table.add_row("Reset At", str(status.reset_at))
            table.add_row(
                "Exceeded",
                "[red]YES[/red]" if status.is_exceeded else "[green]NO[/green]",
            )

            console.print(table)
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)


@auth.command("cleanup-sessions")
@click.option(
    "--config",
    "config_path",
    default="config/app.toml",
    help="Path to the TOML configuration file.",
    show_default=True,
)
def cleanup_sessions(config_path: str) -> None:
    """Delete expired sessions (expired > 7 days ago)."""

    async def _do(ctx: ApplicationContext) -> None:
        try:
            count = await ctx.auth_service.cleanup_expired_sessions()
            if count > 0:
                console.print(
                    f"[bold green]Deleted {count} expired session(s).[/bold green]"
                )
            else:
                console.print("[dim]No expired sessions to clean up.[/dim]")
        except AppError as e:
            console.print(f"[bold red]Error:[/bold red] {e}", highlight=False)

    run_cli_async(_do, config_path)
