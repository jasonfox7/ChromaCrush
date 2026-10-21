"""CLI commands for the API module.

Provides Click commands for managing the ChromaCrush API server:
starting the server, listing registered routes, checking health,
and displaying API configuration.

Commands:
    api start       -- Start the API server via uvicorn
    api routes      -- List all registered routes
    api health      -- Check the health endpoint of a running server
    api config      -- Display API configuration values
"""

from __future__ import annotations

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.core.composition_root import load_config

console = Console()

# -- Default values -----------------------------------------------------------

_DEFAULT_HOST = "0.0.0.0"
_DEFAULT_PORT = 8000
_DEFAULT_CONFIG_PATH = "config/app.toml"


# -- CLI group ----------------------------------------------------------------


@click.group()
def api() -> None:
    """API server management commands."""


# -- start command ------------------------------------------------------------


@api.command("start")
@click.option(
    "--host",
    default=_DEFAULT_HOST,
    show_default=True,
    help="Bind host address.",
)
@click.option(
    "--port",
    default=_DEFAULT_PORT,
    type=int,
    show_default=True,
    help="Bind port number.",
)
@click.option(
    "--reload",
    "auto_reload",
    is_flag=True,
    help="Enable auto-reload for development.",
)
@click.option(
    "--config",
    "config_path",
    default=_DEFAULT_CONFIG_PATH,
    show_default=True,
    help="Path to the TOML configuration file.",
)
def start(host: str, port: int, auto_reload: bool, config_path: str) -> None:
    """Start the ChromaCrush API server.

    Launches the FastAPI application using uvicorn. Configuration values
    from the TOML file are used as defaults but CLI options override them.
    """
    import uvicorn

    config = load_config(config_path)

    # Use config defaults unless CLI explicitly overrides
    effective_host = (
        config.get("api.host", _DEFAULT_HOST) if host == _DEFAULT_HOST else host
    )
    effective_port = (
        config.get("api.port", _DEFAULT_PORT) if port == _DEFAULT_PORT else port
    )

    console.print(
        Panel(
            f"[bold green]ChromaCrush API[/bold green]\n"
            f"Host: {effective_host}\n"
            f"Port: {effective_port}\n"
            f"Reload: {auto_reload}\n"
            f"Config: {config_path}",
            title="Starting Server",
            border_style="green",
        )
    )

    uvicorn.run(
        "src.modules.api.factory:create_app",
        host=effective_host,
        port=effective_port,
        reload=auto_reload,
        factory=True,
    )


# -- routes command -----------------------------------------------------------


@api.command("routes")
def routes() -> None:
    """List all registered API routes.

    Creates a lightweight FastAPI app with all routers to inspect the
    route table, then displays a formatted table of methods and paths.
    No service dependencies are needed -- routers are standalone.
    """
    from fastapi import FastAPI
    from src.modules.api.routes import (
        ads_router,
        auth_router,
        bot_earnings_router,
        cards_router,
        economy_router,
        energy_router,
        events_router,
        health_router,
        inventory_router,
        matchmaking_router,
        matches_router,
        payments_router,
        players_router,
        vault_router,
        ws_router,
    )

    # Build a minimal app with only routers -- no middleware, no services.
    app = FastAPI()
    for router in (
        health_router,
        ws_router,
        auth_router,
        players_router,
        energy_router,
        matchmaking_router,
        matches_router,
        vault_router,
        cards_router,
        inventory_router,
        events_router,
        ads_router,
        payments_router,
        bot_earnings_router,
        economy_router,
    ):
        app.include_router(router)

    table = Table(
        title="Registered API Routes",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Methods", style="green", min_width=10)
    table.add_column("Path", style="yellow")
    table.add_column("Tags", style="dim")

    route_count = 0
    for route in app.routes:
        methods_set = getattr(route, "methods", None)
        path = getattr(route, "path", None)
        if methods_set is None or path is None:
            continue

        # Filter out HEAD and OPTIONS for readability
        display_methods = sorted(methods_set - {"HEAD", "OPTIONS"})
        if not display_methods:
            continue

        tags = ", ".join(getattr(route, "tags", []) or [])
        table.add_row(", ".join(display_methods), path, tags)
        route_count += 1

    console.print(table)
    console.print(f"\n[bold]{route_count}[/bold] routes registered.")


# -- health command -----------------------------------------------------------


@api.command("health")
@click.option(
    "--url",
    default="http://localhost:8000",
    show_default=True,
    help="Base URL of the running API server.",
)
def health(url: str) -> None:
    """Check the health endpoint of a running API server.

    Sends a GET request to /api/v1/health and displays the response.
    Requires the server to be running.
    """
    import json
    from urllib.request import urlopen
    from urllib.error import URLError

    endpoint = f"{url}/api/v1/health"

    try:
        with urlopen(endpoint, timeout=5) as resp:
            data = json.loads(resp.read().decode())
            status_code = resp.status
    except URLError as exc:
        console.print(f"[bold red]Connection failed:[/bold red] {exc}")
        return
    except Exception as exc:
        console.print(f"[bold red]Error:[/bold red] {exc}")
        return

    # Display result
    color = "green" if status_code == 200 else "red"
    status = data.get("status", "unknown")

    table = Table(title="Health Check", show_header=True)
    table.add_column("Field", style="cyan")
    table.add_column("Value", style="yellow")

    table.add_row("URL", endpoint)
    table.add_row("HTTP Status", f"[{color}]{status_code}[/{color}]")
    table.add_row("Status", f"[{color}]{status}[/{color}]")

    if "version" in data:
        table.add_row("Version", str(data["version"]))
    if "timestamp" in data:
        table.add_row("Timestamp", str(data["timestamp"]))

    console.print(table)


# -- config command -----------------------------------------------------------


@api.command("config")
@click.option(
    "--config",
    "config_path",
    default=_DEFAULT_CONFIG_PATH,
    show_default=True,
    help="Path to the TOML configuration file.",
)
def show_config(config_path: str) -> None:
    """Display API configuration values.

    Reads the configuration file and shows all api.* settings along
    with key values from related namespaces.
    """
    config = load_config(config_path)

    table = Table(
        title="API Configuration",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Key", style="cyan", min_width=30)
    table.add_column("Value", style="yellow")

    rows: list[tuple[str, str]] = [
        ("api.host", str(config.get("api.host", _DEFAULT_HOST))),
        ("api.port", str(config.get("api.port", _DEFAULT_PORT))),
        ("api.cors_origins", str(config.get("api.cors_origins", ["*"]))),
        ("api.docs_enabled", str(config.get("api.docs_enabled", True))),
        ("api.bot_hints_enabled", str(config.get("api.bot_hints_enabled", True))),
        (
            "api.rate_limit.requests_per_minute",
            str(config.get("api.rate_limit.requests_per_minute", 60)),
        ),
        ("api.rate_limit.burst_size", str(config.get("api.rate_limit.burst_size", 10))),
        ("app.name", str(config.get("app.name", "ChromaCrush"))),
        ("app.version", str(config.get("app.version", "0.1.0"))),
        ("app.environment", str(config.get("app.environment", "development"))),
        ("app.debug", str(config.get("app.debug", False))),
        ("websocket.enabled", str(config.get("websocket.enabled", True))),
        ("websocket.path", str(config.get("websocket.path", "/ws"))),
        (
            "websocket.heartbeat_interval_seconds",
            str(config.get("websocket.heartbeat_interval_seconds", 30)),
        ),
    ]

    for key, value in rows:
        table.add_row(key, value)

    console.print(table)


