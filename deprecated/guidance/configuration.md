# Configuration Guidance Document

**Version:** 1.0
**Date:** 2026-02-05
**Author:** Configuration Agent
**Status:** Final
**Framework:** LLM-Orchestrated Multi-Agent Development Framework v4

---

## 1. Composition Root Design

The composition root is the single location where all services are instantiated and wired. No service instantiation occurs anywhere else in the codebase.

### 1.1 Location and Structure

```
src/core/composition_root.py   # Main application composition
src/cli/cli_entry.py           # CLI-specific composition (reuses core)
```

### 1.2 Main Application Composition Root

```python
# src/core/composition_root.py

from typing import Protocol
import asyncio
from contextlib import asynccontextmanager

from src.core.config import ConfigService
from src.core.logger import LogService
from src.core.errors import ErrorService
from src.core.data_context import DataContext


class ApplicationContext:
    """
    Holds all instantiated services. Created once at startup.
    Passed to FastAPI via lifespan context.
    """

    def __init__(
        self,
        config: ConfigService,
        logger: LogService,
        errors: ErrorService,
        data_ctx: DataContext,
    ):
        self.config = config
        self.logger = logger
        self.errors = errors
        self.data_ctx = data_ctx


async def create_application_context(
    config_path: str = "config/app.toml"
) -> ApplicationContext:
    """
    Async factory that initializes all services in correct order.
    Called once at application startup.
    """
    # Phase 1: Load configuration (sync, no dependencies)
    config = ConfigService.load(config_path)

    # Phase 2: Create logger (depends on config)
    logger = LogService(config)
    logger.info("Application starting", environment=config.get("app.environment"))

    # Phase 3: Create error service (depends on logger, config)
    errors = ErrorService(logger, config)

    # Phase 4: Initialize data layer (async, depends on config, logger, errors)
    data_ctx = await DataContext.create(config, logger, errors)

    logger.info("Application context created successfully")

    return ApplicationContext(
        config=config,
        logger=logger,
        errors=errors,
        data_ctx=data_ctx,
    )


async def shutdown_application_context(ctx: ApplicationContext) -> None:
    """Graceful shutdown. Close connections in reverse order."""
    ctx.logger.info("Application shutting down")
    await ctx.data_ctx.close()
    ctx.logger.info("Shutdown complete")
```

### 1.3 FastAPI Integration

```python
# src/main.py

from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, Request

from src.core.composition_root import (
    ApplicationContext,
    create_application_context,
    shutdown_application_context,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup/shutdown."""
    app.state.ctx = await create_application_context()
    yield
    await shutdown_application_context(app.state.ctx)


app = FastAPI(lifespan=lifespan)


def get_app_context(request: Request) -> ApplicationContext:
    """FastAPI dependency to access application context."""
    return request.app.state.ctx


def get_config(ctx: ApplicationContext = Depends(get_app_context)) -> ConfigService:
    return ctx.config


def get_logger(ctx: ApplicationContext = Depends(get_app_context)) -> LogService:
    return ctx.logger
```

### 1.4 Async Initialization Sequence

| Order | Service | Async | Dependencies |
|-------|---------|-------|--------------|
| 1 | ConfigService | No | None (file read) |
| 2 | LogService | No | ConfigService |
| 3 | ErrorService | No | LogService, ConfigService |
| 4 | DataContext (PostgreSQL) | **Yes** | ConfigService, LogService, ErrorService |
| 5 | RedisContext | **Yes** | ConfigService, LogService, ErrorService |
| 6 | ArqContext (task queue) | **Yes** | RedisContext, ConfigService |
| 7 | Repositories | No | DataContext |
| 8 | Module Services | No | All above as needed |

---

## 2. Config Schema

### 2.1 App Namespace

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| `app.name` | string | `"ChromaCrush"` | No | Application name |
| `app.version` | string | `"0.1.0"` | No | Application version |
| `app.environment` | enum | `"development"` | No | development, test, staging, production |
| `app.debug` | bool | `false` | No | Global debug mode |

### 2.2 Database Namespace

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| `database.host` | string | `"localhost"` | No | PostgreSQL host |
| `database.port` | int | `5432` | No | PostgreSQL port |
| `database.name` | string | `"chromacrush"` | No | Database name |
| `database.user` | string | - | **Yes** | Database username |
| `database.password` | string | - | **Yes (secret)** | Database password |
| `database.pool_size` | int | `5` | No | Connection pool size |

### 2.3 Redis Namespace

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| `redis.host` | string | `"localhost"` | No | Redis host |
| `redis.port` | int | `6379` | No | Redis port |
| `redis.key_prefix` | string | `"chromacrush:"` | No | Prefix for all keys |

### 2.4 Auth Namespace

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| `auth.jwt_secret` | string | - | **Yes (secret)** | JWT signing secret |
| `auth.jwt_algorithm` | string | `"HS256"` | No | JWT signing algorithm |
| `auth.access_token_expiry_minutes` | int | `60` | No | Access token expiry |
| `auth.refresh_token_expiry_days` | int | `30` | No | Refresh token expiry |
| `auth.api_key_prefix` | string | `"cc_"` | No | API key prefix for bots |
| `auth.api_key_length` | int | `32` | No | Generated API key length |
| `auth.bcrypt_rounds` | int | `12` | No | Bcrypt hashing rounds |
| `auth.password_min_length` | int | `8` | No | Minimum password length |
| `auth.rate_limit_requests` | int | `100` | No | API key rate limit (requests) |
| `auth.rate_limit_window_seconds` | int | `3600` | No | API key rate limit window |
| `auth.max_sessions_per_player` | int | `5` | No | Max concurrent sessions |

### 2.5 Game Namespace

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| `game.board_width` | int | `8` | No | Board width in cells |
| `game.board_height` | int | `8` | No | Board height in cells |
| `game.gem_types` | int | `6` | No | Number of gem colors |
| `game.moves_per_match` | int | `20` | No | Moves per player per match |
| `game.min_match_length` | int | `3` | No | Minimum gems to form a match |

### 2.6 Matchmaking Namespace

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| `matchmaking.elo_initial` | int | `1000` | No | Starting ELO rating |
| `matchmaking.elo_k_factor` | int | `32` | No | ELO K-factor |
| `matchmaking.queue_max_size` | int | `10000` | No | Maximum players in queue |
| `matchmaking.initial_elo_range` | int | `50` | No | Initial ELO range for matching (±) |
| `matchmaking.max_elo_range` | int | `500` | No | Maximum ELO range (±) |
| `matchmaking.elo_range_expansion_interval_seconds` | int | `10` | No | Seconds between range expansions |
| `matchmaking.elo_range_expansion` | int | `50` | No | ELO points to expand per interval |
| `matchmaking.queue_timeout_seconds` | int | `300` | No | Queue entry expiry |
| `matchmaking.queue_poll_interval_ms` | int | `500` | No | Milliseconds between queue checks |
| `matchmaking.min_wait_before_expansion` | int | `10` | No | Minimum seconds before ELO expansion |

### 2.7 Energy Namespace

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| `energy.max_hearts` | int | `5` | No | Maximum hearts |
| `energy.regen_interval_minutes` | int | `30` | No | Minutes per heart regeneration |
| `energy.bonus_overflow_limit` | int | `10` | No | Max hearts including bonus overflow |
| `energy.streak_reward_threshold_7` | int | `1` | No | Bonus hearts for 7-day streak |
| `energy.streak_reward_threshold_14` | int | `2` | No | Bonus hearts for 14-day streak |
| `energy.streak_reward_threshold_30` | int | `3` | No | Bonus hearts for 30-day streak |
| `energy.streak_reward_repeat_interval` | int | `30` | No | Days between streak reward repeats |

### 2.8 Payments Namespace

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| `payments.ad_free_product_id` | string | `"chromacrush_ad_free"` | Yes | Product ID for ad-free tier |
| `payments.ad_free_price_cents` | int | `100` | No | Price in cents |
| `payments.ad_free_currency` | string | `"USD"` | No | Currency code |
| `payments.intent_expiry_minutes` | int | `30` | No | Purchase intent timeout |
| `payments.apple_bundle_id` | string | - | **Yes** | iOS bundle ID |
| `payments.apple_shared_secret` | string | - | **Yes (secret)** | App Store shared secret |
| `payments.apple_verify_url` | string | `"https://buy.itunes.apple.com/verifyReceipt"` | No | Production URL |
| `payments.apple_sandbox_verify_url` | string | `"https://sandbox.itunes.apple.com/verifyReceipt"` | No | Sandbox URL |
| `payments.google_package_name` | string | - | **Yes** | Android package name |
| `payments.google_service_account_key` | string | - | **Yes (secret)** | GCP service account JSON |
| `payments.webhook_apple_secret` | string | - | **Yes (secret)** | Apple webhook secret |
| `payments.webhook_google_secret` | string | - | **Yes (secret)** | Google webhook secret |
| `payments.allow_sandbox_purchases` | bool | `false` | No | Allow sandbox receipts |

### 2.9 Bot Earnings Namespace

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| `bot_earnings.minimum_payout_cents` | int | `1000` | No | Minimum balance for payout ($10) |
| `bot_earnings.attribution_share_percent` | float | `30.0` | No | Bot share of impression revenue |
| `bot_earnings.sync_lookback_days` | int | `7` | No | Days to look back during sync |
| `bot_earnings.max_date_range_days` | int | `90` | No | Max days for date range queries |
| `bot_earnings.payout_hold_hours` | int | `72` | No | Hours to hold new payouts |
| `bot_earnings.sync_batch_size` | int | `100` | No | Bots per batch in bulk sync |

### 2.10 WebSocket Namespace

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| `websocket.enabled` | bool | `true` | No | Enable WebSocket server |
| `websocket.path` | string | `"/ws"` | No | WebSocket endpoint path |
| `websocket.heartbeat_interval_seconds` | int | `30` | No | Ping interval for connection keep-alive |
| `websocket.connection_timeout_seconds` | int | `60` | No | Idle timeout before disconnect |
| `websocket.max_connections_per_player` | int | `3` | No | Max concurrent WS connections per player |
| `websocket.max_message_size_bytes` | int | `65536` | No | Maximum incoming message size (64KB) |
| `websocket.rate_limit_messages_per_second` | int | `10` | No | Per-connection message rate limit |

### 2.11 API Namespace

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| `api.host` | string | `"0.0.0.0"` | No | Bind address for the API server |
| `api.port` | int | `8000` | No | Port for the API server |
| `api.cors_origins` | list[string] | `["*"]` | No | Allowed CORS origins |
| `api.docs_enabled` | bool | `true` | No | Enable OpenAPI docs (/docs, /redoc) |
| `api.bot_hints_enabled` | bool | `true` | No | Enable bot hint generation for API key requests |
| `api.rate_limit.requests_per_minute` | int | `60` | No | Rate limit per identifier per minute |
| `api.rate_limit.burst_size` | int | `10` | No | Burst allowance above rate limit |

### 2.12 Scoring Namespace

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| `scoring.base_points` | int | `50` | No | Points per gem in a basic match |
| `scoring.chain_multipliers` | string | `"1.0,1.5,2.0,2.5,3.0"` | No | CSV multipliers by cascade step |
| `scoring.length_multipliers` | string | `"1.0,1.5,2.0,3.0"` | No | CSV multipliers by match length (3,4,5,6+) |
| `scoring.special_gem_creation_bonus` | int | `100` | No | Bonus for creating a special gem |
| `scoring.line_blast_activation_bonus` | int | `25` | No | Bonus for activating line blast |
| `scoring.line_blast_per_gem` | int | `30` | No | Points per gem destroyed by line blast |
| `scoring.radial_bomb_activation_bonus` | int | `200` | No | Bonus for activating radial bomb |
| `scoring.radial_bomb_per_gem` | int | `40` | No | Points per gem destroyed by radial bomb |
| `scoring.chromatic_orb_activation_bonus` | int | `200` | No | Bonus for activating chromatic orb |
| `scoring.chromatic_orb_per_gem` | int | `40` | No | Points per gem destroyed by chromatic orb |

### 2.13 Board Gen Namespace

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| `board_gen.default_cascade_potential` | float | `0.5` | No | Default cascade potential target |
| `board_gen.default_near_miss_factor` | float | `0.3` | No | Default near-miss density |
| `board_gen.max_generation_attempts` | int | `100` | No | Max attempts before failure |
| `board_gen.max_starting_specials` | int | `3` | No | Max special gems on new board |
| `board_gen.enable_near_miss` | bool | `true` | No | Enable near-miss tuning |
| `board_gen.competitive_cascade_potential` | float | `0.4` | No | Cascade potential for competitive |
| `board_gen.casual_cascade_potential` | float | `0.6` | No | Cascade potential for casual |
| `board_gen.tutorial_cascade_potential` | float | `0.3` | No | Cascade potential for tutorial |

### 2.14 Special Gems Namespace

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| `special_gems.radial_bomb_radius` | int | `2` | No | Radial bomb explosion radius |
| `special_gems.mega_bomb_radius` | int | `3` | No | Mega bomb explosion radius |
| `special_gems.triple_line_count` | int | `3` | No | Lines cleared by triple line blast |
| `special_gems.chain_reaction_enabled` | bool | `true` | No | Enable chain reactions |

### 2.15 Player Namespace

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| `player.username_min_length` | int | `3` | No | Minimum username length |
| `player.username_max_length` | int | `20` | No | Maximum username length |
| `player.username_pattern` | string | `"^[a-zA-Z0-9_]+$"` | No | Allowed username pattern |

### 2.16 Vault Namespace

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| `vault.shield_duration_hours` | int | `24` | No | Shield protection duration |
| `vault.raid_cooldown_hours` | int | `4` | No | Hours between raids |
| `vault.raid_energy_cost` | int | `2` | No | Hearts consumed per raid |
| `vault.raid_success_base_chance` | float | `0.5` | No | Base raid success probability |
| `vault.empty_vault_protection` | bool | `true` | No | Prevent raids on empty vaults |
| `vault.legendary_steal_chance_modifier` | float | `0.5` | No | Multiplier for legendary steal chance |
| `vault.max_artifacts_per_player` | int | `100` | No | Max artifacts a player can hold |

### 2.17 Match Namespace

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| `match.moves_per_player` | int | `20` | No | Moves per player per match |
| `match.timeout_hours` | int | `24` | No | Hours before match times out |
| `match.energy_cost` | int | `1` | No | Hearts consumed to start a match |
| `match.allow_concurrent` | bool | `false` | No | Allow concurrent matches |
| `match.max_concurrent` | int | `1` | No | Max concurrent matches per player |
| `match.deadlock_reshuffle` | bool | `true` | No | Auto-reshuffle on deadlock |

### 2.18 Events Namespace

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| `events.flash_duration_hours` | int | `4` | No | Flash event duration |
| `events.weekly_duration_days` | int | `7` | No | Weekly event duration |
| `events.seasonal_duration_days` | int | `30` | No | Seasonal event duration |
| `events.entry_energy_cost` | int | `1` | No | Energy to join event |
| `events.match_energy_cost` | int | `1` | No | Energy per event match |
| `events.max_participants_flash` | int | `100` | No | Flash event player cap |
| `events.max_participants_weekly` | int | `1000` | No | Weekly event player cap |
| `events.max_participants_seasonal` | int | `10000` | No | Seasonal event player cap |
| `events.leaderboard_cache_ttl_seconds` | int | `60` | No | Redis leaderboard cache TTL |
| `events.auto_finalize_delay_minutes` | int | `15` | No | Delay before auto-finalization |
| `events.min_matches_for_rewards` | int | `3` | No | Min matches to earn rewards |
| `events.allow_leave_after_match` | bool | `false` | No | Allow leaving after playing |

### 2.19 Ads Namespace

| Key | Type | Default | Required | Description |
|-----|------|---------|----------|-------------|
| `ads.interstitial_cooldown_seconds` | int | `60` | No | Interstitial ad cooldown |
| `ads.rewarded_cooldown_seconds` | int | `300` | No | Rewarded ad cooldown |
| `ads.banner_min_view_ms` | int | `1000` | No | Min banner view duration |
| `ads.rewarded_min_watch_percent` | int | `80` | No | Min percent to earn reward |
| `ads.rewarded_heart_reward` | int | `1` | No | Hearts earned from rewarded ad |
| `ads.bot_attribution_share_percent` | float | `30.0` | No | Bot share of ad revenue |
| `ads.estimated_cpm_cents` | int | `500` | No | Estimated CPM in cents |
| `ads.event_opportunity_cooldown_minutes` | int | `30` | No | Event ad opportunity cooldown |
| `ads.interstitial_unit_id` | string | `""` | No | Ad provider interstitial unit |
| `ads.rewarded_unit_id` | string | `""` | No | Ad provider rewarded unit |
| `ads.provider_name` | string | `"admob"` | No | Ad provider name |

---

## 3. Environment Strategy

### 3.1 Config Source Priority

1. **Environment variables** - Always win
2. **Environment-specific config file** - `config/app.{environment}.toml`
3. **Base config file** - `config/app.toml`
4. **Hardcoded defaults**

### 3.2 Environment Variable Mapping

```
DATABASE_HOST      -> database.host
AUTH_JWT_SECRET    -> auth.jwt_secret
GAME_BOARD_WIDTH   -> game.board_width
```

### 3.3 Secrets Handling

**NEVER in code or config files:**
- `database.password`
- `auth.jwt_secret`
- `redis.password`
- `payments.apple_shared_secret`
- `payments.google_service_account_key`
- `payments.webhook_apple_secret`
- `payments.webhook_google_secret`

**Required:** Environment variables in production, `.env` file for local dev (gitignored).

---

## 4. Config File Format

```toml
# config/app.toml

[app]
name = "ChromaCrush"
version = "0.1.0"
environment = "development"
debug = false

[database]
host = "localhost"
port = 5432
name = "chromacrush"
user = "chromacrush"
# password = [secret] Set DATABASE_PASSWORD env var
pool_size = 5

[redis]
host = "localhost"
port = 6379
key_prefix = "chromacrush:"

[auth]
# jwt_secret = [secret] Set AUTH_JWT_SECRET env var
jwt_expiry_minutes = 60
api_key_prefix = "cc_"

[game]
board_width = 8
board_height = 8
gem_types = 6
moves_per_match = 20

[matchmaking]
elo_initial = 1000
elo_k_factor = 32
queue_max_size = 10000
elo_range_initial = 50
elo_range_max = 500
elo_expansion_interval_seconds = 10
elo_expansion_step = 50
match_timeout_seconds = 300
queue_poll_interval_ms = 500

[energy]
max_hearts = 5
regen_interval_minutes = 30

[payments]
ad_free_product_id = "chromacrush_ad_free"
ad_free_price_cents = 100
ad_free_currency = "USD"
intent_expiry_minutes = 30
# apple_bundle_id = [required] Set in env-specific config
# apple_shared_secret = [secret] Set PAYMENTS_APPLE_SHARED_SECRET env var
# google_package_name = [required] Set in env-specific config
# google_service_account_key = [secret] Set PAYMENTS_GOOGLE_SERVICE_ACCOUNT_KEY env var
# webhook_apple_secret = [secret] Set PAYMENTS_WEBHOOK_APPLE_SECRET env var
# webhook_google_secret = [secret] Set PAYMENTS_WEBHOOK_GOOGLE_SECRET env var
allow_sandbox_purchases = false

[bot_earnings]
minimum_payout_cents = 1000
attribution_share_percent = 30.0
sync_lookback_days = 7
max_date_range_days = 90
payout_hold_hours = 72
sync_batch_size = 100

[websocket]
enabled = true
path = "/ws"
heartbeat_interval_seconds = 30
connection_timeout_seconds = 60
max_connections_per_player = 3
max_message_size_bytes = 65536
rate_limit_messages_per_second = 10

[logging]
level = "INFO"
format = "json"
```

---

## 5. Feature Flags

```toml
[features]
experimental_near_miss_tuning = { enabled = false, lifecycle = "experimental" }
vault_raids = { enabled = true, lifecycle = "stable" }
```

**Lifecycle stages:** `experimental`, `stable`, `deprecated`

---

## 6. Debug Mode

Global: `app.debug = true`

Per-module:
```toml
[debug]
board = true
scoring = true
match = true
```

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-07 | 2.0 | Stage 3 batch update: added 8 new namespaces (scoring, board_gen, special_gems, player, vault, match, events, ads), updated auth (+8 keys), energy (+5 keys), matchmaking (reconciled key names, +1 key), game (+1 key). Total: 96 additional keys across 13 namespaces. | Orchestrator |
| 2026-02-05 | 1.3 | Added websocket namespace (7 keys) for real-time support | Orchestrator |
| 2026-02-05 | 1.2 | Added payments namespace (13 keys) + bot_earnings namespace (6 keys) | Orchestrator |
| 2026-02-05 | 1.1 | Added matchmaking config keys (queue_max_size, elo_range_*, expansion_*, timeout, poll_interval) | Orchestrator |
| 2026-02-05 | 1.0 | Initial guidance | Configuration Agent |
