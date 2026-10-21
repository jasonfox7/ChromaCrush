# Module Artifact: ads

## Header
- **Author:** Scout Agent (ads)
- **Date:** 2026-02-05
- **Version:** 1.0
- **Status:** Final
- **Dependencies:** `player` (Wave 1), `events` (Wave 6)
- **Dependents:** `payments`, `bot_earnings`

---

## Purpose

The **ads** module handles all advertisement integration for ChromaCrush, serving as the primary monetization mechanism for free-tier players. It manages:

1. **Interstitial Ads** - Full-screen ads displayed between matches
2. **Rewarded Video Ads** - Opt-in ads that grant bonus hearts or rewards
3. **Banner Ads** - Passive display ads in non-gameplay screens
4. **Ad-Free Status Checking** - Verifying if a player has purchased ad removal
5. **Impression Tracking** - Recording all ad views with player/match context
6. **Revenue Attribution** - Tracking which players (human or bot) triggered ad impressions
7. **Bot Revenue Data** - Providing ad impression data to `bot_earnings` for revenue sharing
8. **Event Ad Opportunities** - Special ad placements triggered by events

Per the GDD, free players see ads while a $1 purchase removes them. Bots don't watch ads but generate revenue attribution through matches - when a human watches an ad after playing against a bot, that impression is partially attributed to the bot for revenue sharing purposes.

This module is **asynchronous** - all public methods involving database operations or external ad SDK calls are `async def`.

---

## Public Interface

### Class: `AdService`

The ads module exposes a single service class that receives dependencies via `__init__` injection.

```python
class AdService:
    def __init__(
        self,
        config: ConfigProtocol,
        logger: LoggerProtocol,
        errors: ErrorServiceProtocol,
        data_ctx: DataContextProtocol,
        player_service: PlayerServiceProtocol,
        events_service: EventServiceProtocol,
        ad_impression_repository: AdImpressionRepositoryProtocol,
        ad_reward_repository: AdRewardRepositoryProtocol,
        ad_provider: AdProviderProtocol,  # Third-party SDK abstraction
    ) -> None:
        ...
```

---

### Inputs

#### `check_ad_free_status(player_id: PlayerId) -> AdFreeStatus`

Checks if a player has ad-free status (purchased or granted).

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `player_id` | `PlayerId` | The player to check | Must exist |

---

#### `can_show_ad(player_id: PlayerId, ad_type: AdType, context: AdContext | None = None) -> AdEligibility`

Determines if an ad can be shown to a player at this time.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `player_id` | `PlayerId` | The player | Must exist |
| `ad_type` | `AdType` | Type of ad (interstitial, rewarded, banner) | Valid enum |
| `context` | `AdContext \| None` | Optional context (match_id, event_id) | Valid if provided |

---

#### `request_interstitial(player_id: PlayerId, trigger: InterstitialTrigger, match_id: MatchId | None = None) -> InterstitialAdResult`

Requests an interstitial ad be shown to a player.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `player_id` | `PlayerId` | The player | Must exist, not ad-free |
| `trigger` | `InterstitialTrigger` | What triggered the ad | Valid enum |
| `match_id` | `MatchId \| None` | Associated match if applicable | Valid if provided |

---

#### `record_interstitial_impression(ad_request_id: AdRequestId, viewed: bool, duration_ms: int) -> AdImpression`

Records the result of an interstitial ad display.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `ad_request_id` | `AdRequestId` | From request_interstitial | Must exist, not already recorded |
| `viewed` | `bool` | Whether player viewed ad | - |
| `duration_ms` | `int` | How long ad was displayed | >= 0 |

---

#### `request_rewarded_video(player_id: PlayerId, reward_type: RewardedAdType) -> RewardedVideoRequest`

Requests a rewarded video ad for the player.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `player_id` | `PlayerId` | The player | Must exist, not ad-free |
| `reward_type` | `RewardedAdType` | What reward the player will get | Valid enum |

---

#### `complete_rewarded_video(ad_request_id: AdRequestId, completed: bool, watched_duration_ms: int) -> RewardedVideoResult`

Records completion of a rewarded video and grants reward if fully watched.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `ad_request_id` | `AdRequestId` | From request_rewarded_video | Must exist, not already completed |
| `completed` | `bool` | Whether player watched full video | - |
| `watched_duration_ms` | `int` | How long player watched | >= 0 |

---

#### `record_banner_impression(player_id: PlayerId, banner_placement: BannerPlacement, view_duration_ms: int) -> AdImpression`

Records a banner ad impression.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `player_id` | `PlayerId` | The player who saw banner | Must exist, not ad-free |
| `banner_placement` | `BannerPlacement` | Where banner was displayed | Valid enum |
| `view_duration_ms` | `int` | How long banner was visible | >= 0 |

---

#### `get_player_ad_stats(player_id: PlayerId, period: StatsPeriod = StatsPeriod.LIFETIME) -> PlayerAdStats`

Gets ad-related statistics for a player.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `player_id` | `PlayerId` | The player | Must exist |
| `period` | `StatsPeriod` | Time period for stats | Valid enum |

---

#### `get_ad_impressions(player_id: PlayerId, ad_type: AdType | None = None, limit: int = 50, offset: int = 0) -> PaginatedResult[AdImpression]`

Gets ad impression history for a player.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `player_id` | `PlayerId` | The player | Must exist |
| `ad_type` | `AdType \| None` | Filter by type | Valid if provided |
| `limit` | `int` | Max results | 1-100 |
| `offset` | `int` | Pagination offset | >= 0 |

---

#### `get_match_ad_attribution(match_id: MatchId) -> MatchAdAttribution`

Gets ad attribution data for a specific match (for bot_earnings module).

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `match_id` | `MatchId` | The match | Must exist |

---

#### `get_bot_ad_attributions(bot_player_id: PlayerId, start_date: date, end_date: date) -> BotAdAttributionReport`

Gets aggregated ad attribution data for a bot over a date range.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `bot_player_id` | `PlayerId` | The bot player | Must exist, must be bot |
| `start_date` | `date` | Start of date range | Valid date |
| `end_date` | `date` | End of date range | Must be >= start_date |

---

#### `grant_ad_free_status(player_id: PlayerId, reason: AdFreeReason, duration_days: int | None = None, granted_by: PlayerId | None = None) -> AdFreeStatus`

Grants ad-free status to a player (called by payments module or admin).

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `player_id` | `PlayerId` | The player | Must exist |
| `reason` | `AdFreeReason` | Why ad-free was granted | Valid enum |
| `duration_days` | `int \| None` | Duration (None = permanent) | > 0 if provided |
| `granted_by` | `PlayerId \| None` | Admin who granted | Valid if provided |

---

#### `revoke_ad_free_status(player_id: PlayerId, reason: str) -> None`

Revokes ad-free status (admin operation, e.g., refund).

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `player_id` | `PlayerId` | The player | Must exist, must have ad-free |
| `reason` | `str` | Why revoked | Max 500 chars |

---

#### `get_event_ad_opportunities(player_id: PlayerId, event_id: EventId) -> list[EventAdOpportunity]`

Gets special ad opportunities available during an event.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `player_id` | `PlayerId` | The player | Must exist, must be event participant |
| `event_id` | `EventId` | The event | Must exist, must be active |

---

#### `claim_event_ad_reward(player_id: PlayerId, event_id: EventId, opportunity_id: str) -> EventAdRewardResult`

Claims a reward from an event ad opportunity.

| Parameter | Type | Description | Validation |
|-----------|------|-------------|------------|
| `player_id` | `PlayerId` | The player | Must exist |
| `event_id` | `EventId` | The event | Must exist, must be active |
| `opportunity_id` | `str` | The opportunity being claimed | Must be valid, not already claimed |

---

### Outputs

#### `AdFreeStatus`

```python
@dataclass
class AdFreeStatus:
    """Player's ad-free status."""
    player_id: PlayerId
    is_ad_free: bool
    reason: AdFreeReason | None  # None if not ad-free
    granted_at: datetime | None
    expires_at: datetime | None  # None if permanent
    is_permanent: bool
```

---

#### `AdEligibility`

```python
@dataclass
class AdEligibility:
    """Whether an ad can be shown to a player."""
    can_show: bool
    reason: str | None  # Why can't show (if can_show=False)
    cooldown_remaining_seconds: int | None  # If rate limited
    ad_request_token: str | None  # Token to use when requesting ad
```

---

#### `InterstitialAdResult`

```python
@dataclass
class InterstitialAdResult:
    """Result of requesting an interstitial ad."""
    ad_request_id: AdRequestId
    ad_unit_id: str  # From ad provider
    should_show: bool  # False if no ad available
    ad_data: dict[str, Any] | None  # Provider-specific data
    created_at: datetime
```

---

#### `AdImpression`

```python
@dataclass
class AdImpression:
    """Record of an ad being shown."""
    id: AdImpressionId
    player_id: PlayerId
    ad_type: AdType
    ad_request_id: AdRequestId | None
    viewed: bool
    view_duration_ms: int
    trigger: str  # What caused the ad
    match_id: MatchId | None  # If triggered by match
    event_id: EventId | None  # If triggered by event
    attributed_to: PlayerId | None  # Bot player for attribution
    estimated_revenue_cents: int | None  # Estimated revenue in cents
    created_at: datetime
```

---

#### `RewardedVideoRequest`

```python
@dataclass
class RewardedVideoRequest:
    """Result of requesting a rewarded video."""
    ad_request_id: AdRequestId
    ad_unit_id: str
    reward_type: RewardedAdType
    reward_value: int  # Hearts, coins, etc.
    video_available: bool
    ad_data: dict[str, Any] | None
    expires_at: datetime  # Request expires after this
```

---

#### `RewardedVideoResult`

```python
@dataclass
class RewardedVideoResult:
    """Result of completing a rewarded video."""
    ad_request_id: AdRequestId
    completed: bool
    watched_duration_ms: int
    reward_granted: bool
    reward_type: RewardedAdType | None
    reward_value: int | None
    impression: AdImpression
```

---

#### `PlayerAdStats`

```python
@dataclass
class PlayerAdStats:
    """Ad statistics for a player."""
    player_id: PlayerId
    period: StatsPeriod
    total_impressions: int
    interstitial_count: int
    rewarded_video_count: int
    banner_impression_count: int
    total_rewards_earned: int  # Hearts from rewarded ads
    average_view_duration_ms: int
    last_ad_at: datetime | None
```

---

#### `MatchAdAttribution`

```python
@dataclass
class MatchAdAttribution:
    """Ad attribution data for a match."""
    match_id: MatchId
    player1_id: PlayerId
    player2_id: PlayerId
    player1_is_bot: bool
    player2_is_bot: bool
    impressions: list[AdImpression]
    total_impressions: int
    estimated_revenue_cents: int
    bot_attribution_cents: int  # Revenue attributed to bot(s)
```

---

#### `BotAdAttributionReport`

```python
@dataclass
class BotAdAttributionReport:
    """Aggregated ad attribution for a bot."""
    bot_player_id: PlayerId
    start_date: date
    end_date: date
    total_matches: int
    matches_with_impressions: int
    total_attributed_impressions: int
    estimated_revenue_cents: int
    attributed_revenue_cents: int
    attribution_share_percent: float  # Config value for bot share
    daily_breakdown: list[DailyAttribution]
```

---

#### `EventAdOpportunity`

```python
@dataclass
class EventAdOpportunity:
    """Special ad opportunity during an event."""
    opportunity_id: str
    event_id: EventId
    ad_type: AdType
    reward_type: str  # "energy", "event_points", "artifact_chance"
    reward_value: int
    description: str
    times_available: int  # How many times can be claimed
    times_claimed: int
    cooldown_minutes: int | None
    available: bool  # Can claim right now
    next_available_at: datetime | None
```

---

### Error Cases

| Condition | Error Code | Error Type | Context Fields |
|-----------|------------|------------|----------------|
| Player not found | `NOT_FOUND_PLAYER` | not_found | `player_id` |
| Player is ad-free | `FORBIDDEN_PLAYER_AD_FREE` | forbidden | `player_id`, `reason` |
| Ad request not found | `NOT_FOUND_AD_REQUEST` | not_found | `ad_request_id` |
| Ad already recorded | `CONFLICT_AD_ALREADY_RECORDED` | conflict | `ad_request_id`, `recorded_at` |
| Ad request expired | `CONFLICT_AD_REQUEST_EXPIRED` | conflict | `ad_request_id`, `expired_at` |
| Rewarded ad not completed | `VALIDATION_REWARDED_AD_NOT_COMPLETED` | validation | `watched_duration_ms`, `required_duration_ms` |
| Ad cooldown active | `RATE_LIMIT_AD_COOLDOWN` | rate_limited | `ad_type`, `retry_after` |
| Event not active | `CONFLICT_EVENT_NOT_ACTIVE` | conflict | `event_id`, `current_status` |
| Not event participant | `FORBIDDEN_NOT_EVENT_PARTICIPANT` | forbidden | `event_id`, `player_id` |
| Opportunity not found | `NOT_FOUND_AD_OPPORTUNITY` | not_found | `opportunity_id` |
| Opportunity already claimed | `CONFLICT_OPPORTUNITY_ALREADY_CLAIMED` | conflict | `opportunity_id`, `claimed_at` |
| Opportunity on cooldown | `RATE_LIMIT_OPPORTUNITY_COOLDOWN` | rate_limited | `opportunity_id`, `retry_after` |
| Player is not a bot | `VALIDATION_PLAYER_NOT_BOT` | validation | `player_id` |
| Invalid date range | `VALIDATION_INVALID_INPUT` | validation | `start_date`, `end_date` |
| Ad provider error | `INTERNAL_AD_PROVIDER_ERROR` | internal | `provider`, `error` |

---

### Async Behavior

**This module is fully asynchronous.**

All public methods are `async def` because they involve:
- Database reads/writes via repositories
- External ad provider SDK calls (third-party)
- Cross-module service calls to `player_service`, `events_service`

**Async operations:**
- `check_ad_free_status` - DB read
- `can_show_ad` - DB read + rate limit check
- `request_interstitial` - DB write + ad provider call
- `record_interstitial_impression` - DB write
- `request_rewarded_video` - DB write + ad provider call
- `complete_rewarded_video` - DB write + reward grant
- `record_banner_impression` - DB write
- `get_player_ad_stats` - DB read (aggregate)
- `get_ad_impressions` - DB read
- `get_match_ad_attribution` - DB read
- `get_bot_ad_attributions` - DB read (aggregate)
- `grant_ad_free_status` - DB write
- `revoke_ad_free_status` - DB write
- `get_event_ad_opportunities` - DB read + events_service call
- `claim_event_ad_reward` - DB write + reward grant

**Error propagation:** All errors are raised through the injected `ErrorServiceProtocol`. External ad provider errors are caught and wrapped in `INTERNAL_AD_PROVIDER_ERROR`. Cross-module errors propagate unchanged.

---

## Mandatory Service Usage

### Configuration Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `ads.interstitial_cooldown_seconds` | int | 180 | Min seconds between interstitials |
| `ads.rewarded_cooldown_seconds` | int | 60 | Min seconds between rewarded ads |
| `ads.banner_min_view_ms` | int | 1000 | Min view duration for banner impression |
| `ads.rewarded_min_watch_percent` | int | 95 | % of video required for reward |
| `ads.rewarded_heart_reward` | int | 1 | Hearts granted for rewarded video |
| `ads.bot_attribution_share_percent` | float | 30.0 | % of impression revenue attributed to bots |
| `ads.estimated_cpm_cents` | int | 200 | Estimated CPM for revenue calculation |
| `ads.provider_name` | str | "mock" | Ad provider (mock, google, unity) |
| `ads.provider_api_key` | str | (secret) | Ad provider API key |
| `ads.interstitial_unit_id` | str | - | Ad unit ID for interstitials |
| `ads.rewarded_unit_id` | str | - | Ad unit ID for rewarded videos |
| `ads.banner_unit_id` | str | - | Ad unit ID for banners |
| `ads.ad_free_trial_days` | int | 0 | Days of ad-free for new players (0 = none) |
| `ads.event_opportunity_cooldown_minutes` | int | 60 | Default cooldown for event ad opportunities |

---

### Logging Events

| Event | Severity | Trigger | Context |
|-------|----------|---------|---------|
| `ads.interstitial_requested` | INFO | Interstitial requested | `player_id`, `trigger`, `match_id` |
| `ads.interstitial_shown` | INFO | Interstitial displayed | `player_id`, `ad_request_id`, `duration_ms` |
| `ads.interstitial_skipped` | DEBUG | Player skipped/closed | `player_id`, `ad_request_id`, `duration_ms` |
| `ads.rewarded_requested` | INFO | Rewarded video requested | `player_id`, `reward_type` |
| `ads.rewarded_completed` | INFO | Rewarded video fully watched | `player_id`, `ad_request_id`, `reward_granted` |
| `ads.rewarded_abandoned` | DEBUG | Rewarded video not completed | `player_id`, `ad_request_id`, `watched_percent` |
| `ads.banner_impression` | DEBUG | Banner viewed | `player_id`, `placement`, `duration_ms` |
| `ads.ad_free_granted` | INFO | Ad-free status granted | `player_id`, `reason`, `duration_days` |
| `ads.ad_free_revoked` | WARN | Ad-free status revoked | `player_id`, `reason` |
| `ads.ad_free_check` | DEBUG | Ad-free status checked | `player_id`, `is_ad_free` |
| `ads.attribution_recorded` | DEBUG | Bot attribution recorded | `match_id`, `bot_player_id`, `attribution_cents` |
| `ads.event_opportunity_claimed` | INFO | Event ad reward claimed | `player_id`, `event_id`, `opportunity_id` |
| `ads.provider_error` | ERROR | Ad provider SDK error | `provider`, `operation`, `error` |
| `ads.cooldown_blocked` | DEBUG | Ad blocked by cooldown | `player_id`, `ad_type`, `retry_after` |

---

### Error Types Used

From the error taxonomy (Interface Agent guidance):

- `NOT_FOUND_PLAYER` - Player ID doesn't exist
- `NOT_FOUND_AD_REQUEST` - Ad request ID doesn't exist
- `NOT_FOUND_AD_OPPORTUNITY` - Event ad opportunity doesn't exist
- `VALIDATION_INVALID_INPUT` - Invalid parameters
- `VALIDATION_REWARDED_AD_NOT_COMPLETED` - Didn't watch enough of video
- `VALIDATION_PLAYER_NOT_BOT` - Player is not a bot
- `FORBIDDEN_PLAYER_AD_FREE` - Can't show ads to ad-free player
- `FORBIDDEN_NOT_EVENT_PARTICIPANT` - Not in the event
- `CONFLICT_AD_ALREADY_RECORDED` - Impression already recorded
- `CONFLICT_AD_REQUEST_EXPIRED` - Request timed out
- `CONFLICT_EVENT_NOT_ACTIVE` - Event not running
- `CONFLICT_OPPORTUNITY_ALREADY_CLAIMED` - Already claimed this opportunity
- `RATE_LIMIT_AD_COOLDOWN` - Must wait between ads
- `RATE_LIMIT_OPPORTUNITY_COOLDOWN` - Event opportunity on cooldown
- `INTERNAL_AD_PROVIDER_ERROR` - External ad SDK error
- `INTERNAL_DATABASE_ERROR` - Database operation failed

All errors created through injected `ErrorServiceProtocol`, never bare raises.

---

## Data Access

### Owned Data

The ads module owns these database tables:

#### `ad_free_status` Table

```sql
CREATE TABLE ad_free_status (
    player_id UUID PRIMARY KEY REFERENCES players(id),
    is_ad_free BOOLEAN NOT NULL DEFAULT false,
    reason VARCHAR(50),  -- 'purchase', 'promotion', 'admin_grant', 'trial'
    granted_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,  -- NULL if permanent
    granted_by UUID REFERENCES players(id),  -- Admin who granted
    revoked_at TIMESTAMPTZ,
    revoke_reason TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ad_free_expires ON ad_free_status(expires_at) WHERE is_ad_free = true AND expires_at IS NOT NULL;
```

#### `ad_requests` Table

```sql
CREATE TABLE ad_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id UUID NOT NULL REFERENCES players(id),
    ad_type VARCHAR(20) NOT NULL,  -- 'interstitial', 'rewarded', 'banner'
    ad_unit_id VARCHAR(100),
    trigger VARCHAR(50),  -- 'match_end', 'menu', 'event', etc.
    reward_type VARCHAR(30),  -- For rewarded: 'heart', 'event_points', etc.
    reward_value INTEGER,

    match_id UUID,  -- Associated match if applicable
    event_id UUID,  -- Associated event if applicable

    status VARCHAR(20) NOT NULL DEFAULT 'pending',  -- 'pending', 'shown', 'completed', 'expired', 'failed'

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    completed_at TIMESTAMPTZ,

    provider_response JSONB  -- Raw response from ad provider
);

CREATE INDEX idx_ad_requests_player ON ad_requests(player_id, created_at DESC);
CREATE INDEX idx_ad_requests_status ON ad_requests(status) WHERE status = 'pending';
CREATE INDEX idx_ad_requests_match ON ad_requests(match_id) WHERE match_id IS NOT NULL;
```

#### `ad_impressions` Table

```sql
CREATE TABLE ad_impressions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id UUID NOT NULL REFERENCES players(id),
    ad_request_id UUID REFERENCES ad_requests(id),

    ad_type VARCHAR(20) NOT NULL,
    trigger VARCHAR(50) NOT NULL,
    placement VARCHAR(50),  -- For banners

    viewed BOOLEAN NOT NULL DEFAULT false,
    view_duration_ms INTEGER NOT NULL DEFAULT 0,
    completed BOOLEAN NOT NULL DEFAULT false,  -- For rewarded videos

    match_id UUID,  -- For attribution
    event_id UUID,
    opponent_id UUID,  -- Opponent in the match (for bot attribution)

    attributed_to UUID,  -- Bot player ID if attributing to a bot
    attribution_share_percent DECIMAL(5,2),  -- % attributed to bot
    estimated_revenue_cents INTEGER,  -- Estimated revenue

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    recorded_date DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE INDEX idx_ad_impressions_player ON ad_impressions(player_id, created_at DESC);
CREATE INDEX idx_ad_impressions_match ON ad_impressions(match_id) WHERE match_id IS NOT NULL;
CREATE INDEX idx_ad_impressions_attributed ON ad_impressions(attributed_to, recorded_date) WHERE attributed_to IS NOT NULL;
CREATE INDEX idx_ad_impressions_date ON ad_impressions(recorded_date, ad_type);
```

#### `ad_rewards_granted` Table

```sql
CREATE TABLE ad_rewards_granted (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id UUID NOT NULL REFERENCES players(id),
    ad_request_id UUID NOT NULL REFERENCES ad_requests(id),
    impression_id UUID NOT NULL REFERENCES ad_impressions(id),

    reward_type VARCHAR(30) NOT NULL,
    reward_value INTEGER NOT NULL,

    granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_ad_reward UNIQUE (ad_request_id)
);

CREATE INDEX idx_ad_rewards_player ON ad_rewards_granted(player_id, granted_at DESC);
```

#### `event_ad_opportunities` Table

```sql
CREATE TABLE event_ad_opportunities (
    id VARCHAR(100) NOT NULL,  -- Composite: event_type + opportunity_type
    event_id UUID NOT NULL REFERENCES events(id),

    ad_type VARCHAR(20) NOT NULL,
    reward_type VARCHAR(30) NOT NULL,
    reward_value INTEGER NOT NULL,
    description TEXT,

    times_available_per_player INTEGER NOT NULL DEFAULT 1,
    cooldown_minutes INTEGER,

    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    PRIMARY KEY (id, event_id)
);

CREATE INDEX idx_event_ad_opportunities_event ON event_ad_opportunities(event_id);
```

#### `event_ad_claims` Table

```sql
CREATE TABLE event_ad_claims (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES events(id),
    opportunity_id VARCHAR(100) NOT NULL,
    player_id UUID NOT NULL REFERENCES players(id),

    impression_id UUID NOT NULL REFERENCES ad_impressions(id),

    claimed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    CONSTRAINT unique_event_ad_claim UNIQUE (event_id, opportunity_id, player_id, claimed_at)
);

CREATE INDEX idx_event_ad_claims_player ON event_ad_claims(player_id, event_id);
```

---

### Repository Interfaces Required

```python
# src/data/protocols/ad_impression_repository.py
from typing import Protocol
from uuid import UUID
from datetime import date, datetime

from src.core.types.game import PlayerId, MatchId, EventId


class AdImpressionRepository(Protocol):
    """Repository interface for ad impressions."""

    async def create(self, data: "AdImpressionCreate") -> "AdImpressionRecord":
        """Create a new ad impression."""
        ...

    async def find_by_id(self, impression_id: UUID) -> "AdImpressionRecord | None":
        """Find impression by ID."""
        ...

    async def find_by_request_id(self, ad_request_id: UUID) -> "AdImpressionRecord | None":
        """Find impression by ad request ID."""
        ...

    async def find_by_player(
        self,
        player_id: UUID,
        ad_type: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list["AdImpressionRecord"], int]:
        """Find impressions for a player."""
        ...

    async def find_by_match(self, match_id: UUID) -> list["AdImpressionRecord"]:
        """Find impressions associated with a match."""
        ...

    async def get_player_stats(
        self,
        player_id: UUID,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> "PlayerAdStatsRecord":
        """Get aggregated ad stats for a player."""
        ...

    async def get_bot_attributions(
        self,
        bot_player_id: UUID,
        start_date: date,
        end_date: date,
    ) -> "BotAttributionRecord":
        """Get aggregated attribution data for a bot."""
        ...

    async def get_daily_attributions(
        self,
        bot_player_id: UUID,
        start_date: date,
        end_date: date,
    ) -> list["DailyAttributionRecord"]:
        """Get daily attribution breakdown for a bot."""
        ...


class AdRequestRepository(Protocol):
    """Repository interface for ad requests."""

    async def create(self, data: "AdRequestCreate") -> "AdRequestRecord":
        """Create a new ad request."""
        ...

    async def find_by_id(self, request_id: UUID) -> "AdRequestRecord | None":
        """Find request by ID."""
        ...

    async def update(self, request_id: UUID, changes: "AdRequestUpdate") -> "AdRequestRecord":
        """Update request status."""
        ...

    async def find_pending_by_player(self, player_id: UUID) -> list["AdRequestRecord"]:
        """Find pending requests for a player."""
        ...

    async def find_last_by_type(
        self,
        player_id: UUID,
        ad_type: str,
    ) -> "AdRequestRecord | None":
        """Find most recent request of a type for cooldown check."""
        ...

    async def expire_old_requests(self, before: datetime) -> int:
        """Expire old pending requests. Returns count expired."""
        ...


class AdFreeStatusRepository(Protocol):
    """Repository interface for ad-free status."""

    async def find_by_player(self, player_id: UUID) -> "AdFreeStatusRecord | None":
        """Get ad-free status for a player."""
        ...

    async def upsert(self, data: "AdFreeStatusUpsert") -> "AdFreeStatusRecord":
        """Create or update ad-free status."""
        ...

    async def revoke(self, player_id: UUID, reason: str) -> "AdFreeStatusRecord":
        """Revoke ad-free status."""
        ...

    async def find_expiring(self, before: datetime) -> list["AdFreeStatusRecord"]:
        """Find ad-free statuses expiring soon."""
        ...


class AdRewardRepository(Protocol):
    """Repository interface for ad rewards."""

    async def create(self, data: "AdRewardCreate") -> "AdRewardRecord":
        """Record a granted reward."""
        ...

    async def find_by_request_id(self, ad_request_id: UUID) -> "AdRewardRecord | None":
        """Find reward by ad request (to check for duplicate)."""
        ...


class EventAdOpportunityRepository(Protocol):
    """Repository interface for event ad opportunities."""

    async def find_by_event(self, event_id: UUID) -> list["EventAdOpportunityRecord"]:
        """Find all opportunities for an event."""
        ...

    async def find_by_id(
        self,
        event_id: UUID,
        opportunity_id: str,
    ) -> "EventAdOpportunityRecord | None":
        """Find specific opportunity."""
        ...

    async def create(self, data: "EventAdOpportunityCreate") -> "EventAdOpportunityRecord":
        """Create an event ad opportunity."""
        ...


class EventAdClaimRepository(Protocol):
    """Repository interface for event ad claims."""

    async def create(self, data: "EventAdClaimCreate") -> "EventAdClaimRecord":
        """Record a claim."""
        ...

    async def count_claims(
        self,
        event_id: UUID,
        opportunity_id: str,
        player_id: UUID,
    ) -> int:
        """Count how many times player claimed this opportunity."""
        ...

    async def find_last_claim(
        self,
        event_id: UUID,
        opportunity_id: str,
        player_id: UUID,
    ) -> "EventAdClaimRecord | None":
        """Find most recent claim for cooldown check."""
        ...
```

---

### Data Read from Other Modules

| Data | Source Module | Access Method | Purpose |
|------|---------------|---------------|---------|
| Player entity | `player` | `PlayerServiceProtocol.get_player()` | Validate player exists, check if bot |
| Player type | `player` | `Player.is_bot` | Determine if bot for attribution |
| Event entity | `events` | `EventServiceProtocol.get_event()` | Validate event exists and is active |
| Event participation | `events` | `EventServiceProtocol.get_event_participant()` | Verify player is in event |

---

### Transaction Requirements

| Operation | Transaction Scope | Notes |
|-----------|-------------------|-------|
| `check_ad_free_status` | Read only | Simple lookup |
| `can_show_ad` | Read only | Lookup + cooldown check |
| `request_interstitial` | Single transaction | Create request + mark pending |
| `record_interstitial_impression` | Single transaction | Create impression + update request |
| `request_rewarded_video` | Single transaction | Create request |
| `complete_rewarded_video` | Single transaction | Create impression + create reward + update request |
| `record_banner_impression` | Single transaction | Create impression |
| `grant_ad_free_status` | Single transaction | Upsert status |
| `revoke_ad_free_status` | Single transaction | Update status |
| `claim_event_ad_reward` | Single transaction | Create impression + create claim + grant reward |

---

## Presentation Boundary

### Business Logic API Surface

The ads module exposes domain objects and DTOs:
- Input: `PlayerId`, `MatchId`, `EventId`, `AdType`, `AdContext`, `InterstitialTrigger`, `RewardedAdType`, `BannerPlacement`
- Output: `AdFreeStatus`, `AdEligibility`, `InterstitialAdResult`, `RewardedVideoRequest`, `RewardedVideoResult`, `AdImpression`, `PlayerAdStats`, `MatchAdAttribution`, `BotAdAttributionReport`, `EventAdOpportunity`

All types are defined in this module (`src/modules/ads/types.py`) or imported from `src/core/types/`.

### Adapter Needs

Presentation adapters need to:
1. Convert `AdFreeStatus` to `AdFreeStatusResponse` (format dates)
2. Convert `AdImpression` to `AdImpressionResponse` (exclude internal attribution data for non-admins)
3. Convert `BotAdAttributionReport` to `BotEarningsResponse` (for bot_earnings module)
4. Format revenue cents as dollars for display
5. Calculate time remaining on ad-free status
6. Format event ad opportunity countdown timers

### What Does NOT Belong in This Module

- No JSON serialization (adapter responsibility)
- No HTTP response construction
- No terminal formatting
- No actual ad rendering (client-side responsibility)
- No payment processing (payments module responsibility)
- No earnings calculation (bot_earnings module responsibility)
- No energy granting logic (energy module provides the interface)
- No event reward logic beyond ad rewards (events module responsibility)

---

## Internal Design

### Ad Provider Abstraction

The module uses a `Protocol` interface to abstract the third-party ad SDK, allowing for mock testing and provider switching.

```python
# src/modules/ads/protocols.py

class AdProviderProtocol(Protocol):
    """Interface for third-party ad provider SDKs."""

    async def request_interstitial(
        self,
        ad_unit_id: str,
        user_id: str,
    ) -> AdProviderResponse:
        """Request an interstitial ad from the provider."""
        ...

    async def request_rewarded_video(
        self,
        ad_unit_id: str,
        user_id: str,
    ) -> AdProviderResponse:
        """Request a rewarded video ad from the provider."""
        ...

    async def verify_impression(
        self,
        ad_request_id: str,
        impression_data: dict[str, Any],
    ) -> bool:
        """Verify an impression with the provider."""
        ...

    async def get_estimated_cpm(
        self,
        ad_type: str,
    ) -> int:
        """Get estimated CPM in cents for revenue estimation."""
        ...


@dataclass
class AdProviderResponse:
    """Response from ad provider."""
    success: bool
    ad_available: bool
    ad_data: dict[str, Any] | None
    error_code: str | None
    error_message: str | None
```

---

### Core Data Structures

```python
# src/modules/ads/types.py

from dataclasses import dataclass
from datetime import datetime, date
from enum import Enum
from typing import NewType, Any
from uuid import UUID

from src.core.types.game import PlayerId, MatchId, EventId


AdRequestId = NewType("AdRequestId", UUID)
AdImpressionId = NewType("AdImpressionId", UUID)


class AdType(Enum):
    INTERSTITIAL = "interstitial"
    REWARDED = "rewarded"
    BANNER = "banner"


class InterstitialTrigger(Enum):
    MATCH_END = "match_end"
    MENU_RETURN = "menu_return"
    MATCHMAKING_WAIT = "matchmaking_wait"
    EVENT_JOIN = "event_join"


class RewardedAdType(Enum):
    BONUS_HEART = "bonus_heart"
    EXTRA_HEARTS = "extra_hearts"
    EVENT_POINTS = "event_points"
    CONTINUE_MATCH = "continue_match"
    DOUBLE_REWARDS = "double_rewards"


class BannerPlacement(Enum):
    MAIN_MENU = "main_menu"
    LEADERBOARD = "leaderboard"
    PROFILE = "profile"
    SETTINGS = "settings"


class AdFreeReason(Enum):
    PURCHASE = "purchase"
    PROMOTION = "promotion"
    ADMIN_GRANT = "admin_grant"
    TRIAL = "trial"
    REFUND = "refund"


class AdRequestStatus(Enum):
    PENDING = "pending"
    SHOWN = "shown"
    COMPLETED = "completed"
    EXPIRED = "expired"
    FAILED = "failed"


class StatsPeriod(Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    LIFETIME = "lifetime"


@dataclass
class AdContext:
    """Context for ad display."""
    match_id: MatchId | None = None
    event_id: EventId | None = None
    opponent_id: PlayerId | None = None
    trigger_source: str | None = None


@dataclass
class DailyAttribution:
    """Daily breakdown of bot ad attribution."""
    date: date
    matches: int
    impressions: int
    estimated_revenue_cents: int
    attributed_cents: int
```

---

### Algorithm: Bot Revenue Attribution

When an ad impression occurs after a match involving a bot, revenue is attributed to the bot based on the configured share percentage.

```python
async def _calculate_bot_attribution(
    self,
    impression: AdImpressionCreate,
    match_id: MatchId | None,
) -> tuple[PlayerId | None, float | None]:
    """
    Calculate bot attribution for an impression.

    Returns (bot_player_id, attribution_share) or (None, None) if no attribution.
    """
    if match_id is None:
        return None, None

    # Get match details to check for bot opponent
    # This requires match info - we store opponent_id in impression
    if impression.opponent_id is None:
        return None, None

    opponent = await self._player_service.get_player(impression.opponent_id)
    if not opponent.is_bot:
        return None, None

    # Attribute to bot
    share = self._config.get("ads.bot_attribution_share_percent", 30.0)
    return impression.opponent_id, share


def _calculate_estimated_revenue(
    self,
    ad_type: AdType,
    viewed: bool,
    duration_ms: int,
) -> int:
    """Calculate estimated revenue in cents for an impression."""
    if not viewed:
        return 0

    cpm_cents = self._config.get("ads.estimated_cpm_cents", 200)

    # Adjust based on ad type
    if ad_type == AdType.REWARDED:
        # Rewarded typically has higher CPM
        cpm_cents = int(cpm_cents * 1.5)
    elif ad_type == AdType.BANNER:
        # Banners have lower CPM
        cpm_cents = int(cpm_cents * 0.3)

    # One impression = CPM / 1000
    return cpm_cents // 1000
```

---

### Algorithm: Request Interstitial

```python
async def request_interstitial(
    self,
    player_id: PlayerId,
    trigger: InterstitialTrigger,
    match_id: MatchId | None = None,
) -> InterstitialAdResult:
    # 1. Check player exists
    player = await self._player_service.get_player(player_id)

    # 2. Check ad-free status
    ad_free = await self._check_ad_free_status_internal(player_id)
    if ad_free.is_ad_free:
        raise self._errors.forbidden(
            "Player has ad-free status",
            code="FORBIDDEN_PLAYER_AD_FREE",
            player_id=str(player_id),
            reason=ad_free.reason.value if ad_free.reason else None,
        )

    # 3. Check cooldown
    cooldown_seconds = self._config.get("ads.interstitial_cooldown_seconds", 180)
    last_request = await self._ad_request_repo.find_last_by_type(
        player_id, AdType.INTERSTITIAL.value
    )

    if last_request is not None:
        elapsed = (datetime.utcnow() - last_request.created_at).total_seconds()
        if elapsed < cooldown_seconds:
            retry_after = int(cooldown_seconds - elapsed)
            raise self._errors.rate_limited(
                "Interstitial ad on cooldown",
                retry_after=retry_after,
                code="RATE_LIMIT_AD_COOLDOWN",
                ad_type="interstitial",
            )

    # 4. Get opponent info for attribution (if match provided)
    opponent_id = None
    if match_id is not None:
        # This would come from match context passed in
        # For now we'd get it from match service if needed
        pass

    # 5. Request ad from provider
    ad_unit_id = self._config.get("ads.interstitial_unit_id", "default_interstitial")
    try:
        provider_response = await self._ad_provider.request_interstitial(
            ad_unit_id=ad_unit_id,
            user_id=str(player_id),
        )
    except Exception as e:
        self._logger.error(
            "Ad provider error",
            provider=self._config.get("ads.provider_name"),
            operation="request_interstitial",
            error=str(e),
        )
        raise self._errors.internal(
            "Ad provider error",
            code="INTERNAL_AD_PROVIDER_ERROR",
            provider=self._config.get("ads.provider_name"),
            error=str(e),
        )

    # 6. Create ad request record
    expires_at = datetime.utcnow() + timedelta(minutes=5)

    ad_request = await self._ad_request_repo.create(AdRequestCreate(
        player_id=player_id,
        ad_type=AdType.INTERSTITIAL.value,
        ad_unit_id=ad_unit_id,
        trigger=trigger.value,
        match_id=match_id,
        status=AdRequestStatus.PENDING.value,
        expires_at=expires_at,
        provider_response=provider_response.ad_data,
    ))

    self._logger.info(
        "Interstitial requested",
        player_id=str(player_id),
        trigger=trigger.value,
        match_id=str(match_id) if match_id else None,
    )

    return InterstitialAdResult(
        ad_request_id=AdRequestId(ad_request.id),
        ad_unit_id=ad_unit_id,
        should_show=provider_response.ad_available,
        ad_data=provider_response.ad_data,
        created_at=ad_request.created_at,
    )
```

---

### Algorithm: Complete Rewarded Video

```python
async def complete_rewarded_video(
    self,
    ad_request_id: AdRequestId,
    completed: bool,
    watched_duration_ms: int,
) -> RewardedVideoResult:
    # 1. Find and validate request
    ad_request = await self._ad_request_repo.find_by_id(ad_request_id)
    if ad_request is None:
        raise self._errors.not_found(
            "Ad request not found",
            code="NOT_FOUND_AD_REQUEST",
            ad_request_id=str(ad_request_id),
        )

    if ad_request.status != AdRequestStatus.PENDING.value:
        raise self._errors.conflict(
            "Ad request already completed",
            code="CONFLICT_AD_ALREADY_RECORDED",
            ad_request_id=str(ad_request_id),
            recorded_at=ad_request.completed_at.isoformat() if ad_request.completed_at else None,
        )

    if datetime.utcnow() > ad_request.expires_at:
        await self._ad_request_repo.update(
            ad_request_id,
            AdRequestUpdate(status=AdRequestStatus.EXPIRED.value),
        )
        raise self._errors.conflict(
            "Ad request expired",
            code="CONFLICT_AD_REQUEST_EXPIRED",
            ad_request_id=str(ad_request_id),
            expired_at=ad_request.expires_at.isoformat(),
        )

    # 2. Check if video was watched enough
    min_watch_percent = self._config.get("ads.rewarded_min_watch_percent", 95)
    # Assume standard rewarded video is ~30 seconds
    expected_duration_ms = 30000
    watched_percent = (watched_duration_ms / expected_duration_ms) * 100

    reward_granted = completed and watched_percent >= min_watch_percent

    # 3. Calculate bot attribution
    opponent_id = None  # Would get from match context
    attributed_to, attribution_share = await self._calculate_bot_attribution(
        AdImpressionCreate(
            player_id=ad_request.player_id,
            opponent_id=opponent_id,
        ),
        ad_request.match_id,
    )

    # 4. Calculate estimated revenue
    estimated_revenue = self._calculate_estimated_revenue(
        AdType.REWARDED,
        completed,
        watched_duration_ms,
    )

    # 5. Create impression record
    async with self._data_ctx.session() as session:
        impression = await self._ad_impression_repo.create(AdImpressionCreate(
            player_id=ad_request.player_id,
            ad_request_id=ad_request_id,
            ad_type=AdType.REWARDED.value,
            trigger="rewarded_request",
            viewed=completed,
            view_duration_ms=watched_duration_ms,
            completed=completed,
            match_id=ad_request.match_id,
            attributed_to=attributed_to,
            attribution_share_percent=attribution_share,
            estimated_revenue_cents=estimated_revenue,
        ))

        # 6. Grant reward if completed
        reward_type = None
        reward_value = None

        if reward_granted:
            reward_type = RewardedAdType(ad_request.reward_type)
            reward_value = ad_request.reward_value

            # Record reward
            await self._ad_reward_repo.create(AdRewardCreate(
                player_id=ad_request.player_id,
                ad_request_id=ad_request_id,
                impression_id=impression.id,
                reward_type=reward_type.value,
                reward_value=reward_value,
            ))

            # Grant the actual reward (e.g., hearts via energy module)
            # This would call energy_service.grant_bonus_hearts()
            # For now, we just record it

        # 7. Update request status
        await self._ad_request_repo.update(
            ad_request_id,
            AdRequestUpdate(
                status=AdRequestStatus.COMPLETED.value,
                completed_at=datetime.utcnow(),
            ),
        )

    if reward_granted:
        self._logger.info(
            "Rewarded video completed",
            player_id=str(ad_request.player_id),
            ad_request_id=str(ad_request_id),
            reward_granted=True,
        )
    else:
        self._logger.debug(
            "Rewarded video abandoned",
            player_id=str(ad_request.player_id),
            ad_request_id=str(ad_request_id),
            watched_percent=watched_percent,
        )

    return RewardedVideoResult(
        ad_request_id=ad_request_id,
        completed=completed,
        watched_duration_ms=watched_duration_ms,
        reward_granted=reward_granted,
        reward_type=reward_type,
        reward_value=reward_value,
        impression=self._build_impression(impression),
    )
```

---

## CLI Surface

### Commands

```bash
# Ad-free status management
chromacrush ads check-status <player-id>
chromacrush ads grant-ad-free <player-id> --reason purchase|promotion|admin_grant [--days N]
chromacrush ads revoke-ad-free <player-id> --reason "Refund processed"

# Ad simulation (for testing)
chromacrush ads request-interstitial <player-id> --trigger match_end [--match <match-id>]
chromacrush ads record-interstitial <ad-request-id> --viewed --duration 5000
chromacrush ads request-rewarded <player-id> --reward-type bonus_heart
chromacrush ads complete-rewarded <ad-request-id> --completed --duration 30000

# Statistics and reporting
chromacrush ads player-stats <player-id> [--period day|week|month|lifetime]
chromacrush ads impressions <player-id> [--type interstitial|rewarded|banner] [--limit 50]
chromacrush ads match-attribution <match-id>
chromacrush ads bot-report <bot-player-id> --start 2026-01-01 --end 2026-01-31

# Event ad opportunities
chromacrush ads event-opportunities <event-id> --player <player-id>
chromacrush ads claim-opportunity <event-id> <opportunity-id> --player <player-id>
```

### Example Invocations

```bash
$ chromacrush ads check-status abc123
Ad-Free Status for player abc123:
  Status: Not ad-free
  Last ad: 2026-02-05 10:30:00 UTC

$ chromacrush ads grant-ad-free abc123 --reason purchase
Ad-free status granted!
  Player: abc123
  Reason: purchase
  Duration: Permanent
  Granted at: 2026-02-05 15:00:00 UTC

$ chromacrush ads request-interstitial def456 --trigger match_end --match xyz789
Interstitial requested!
  Request ID: 550e8400-e29b-41d4-a716-446655440001
  Ad available: Yes
  Expires: 2026-02-05 15:05:00 UTC

$ chromacrush ads record-interstitial 550e8400 --viewed --duration 5000
Interstitial recorded!
  Viewed: Yes
  Duration: 5000ms
  Estimated revenue: $0.002

$ chromacrush ads player-stats def456 --period month
Ad Stats for player def456 (last 30 days):
  Total impressions: 45
  Interstitials: 30
  Rewarded videos: 12
  Banners: 3
  Hearts earned: 12
  Last ad: 2026-02-05 10:30:00 UTC

$ chromacrush ads bot-report bot789 --start 2026-01-01 --end 2026-01-31
Bot Attribution Report: bot789
  Period: 2026-01-01 to 2026-01-31
  Matches played: 1,234
  Matches with ad impressions: 892
  Total attributed impressions: 892
  Estimated ad revenue: $18.50
  Bot attributed revenue: $5.55 (30%)

  Daily breakdown (first 5 days):
    2026-01-01: 28 matches, 21 impressions, $0.18 attributed
    2026-01-02: 31 matches, 25 impressions, $0.21 attributed
    ...
```

---

## Edge Cases & Decisions

### EC-1: Player Becomes Ad-Free Mid-Request

**Scenario:** Player requests an interstitial, then purchases ad-free before the impression is recorded.

**Decision:** If ad_free_status.granted_at > ad_request.created_at, do not record the impression. Return success but with no_impression flag. The ad was requested legitimately; we just don't charge them now.

**Rationale:** Good customer experience. They paid for ad-free; honor it immediately.

---

### EC-2: Ad Provider Unavailable

**Scenario:** Third-party ad SDK returns error or times out.

**Decision:** Return `InterstitialAdResult` with `should_show=False`. Log the error. Do not block the user's flow. Retry logic handled at client level.

**Rationale:** Ad failures should not break gameplay. Ads are optional revenue, not critical path.

---

### EC-3: Rewarded Video Partially Watched

**Scenario:** Player watches 80% of rewarded video then closes it.

**Decision:** `completed=False`, no reward granted. Impression still recorded with `completed=false`. Player can request another rewarded video after cooldown.

**Rationale:** Contract with ad provider requires full view for full reward. Partial views don't count.

---

### EC-4: Bot Attribution for Bot vs Bot Match

**Scenario:** Two bots play each other. Human watches ad after spectating.

**Decision:** No attribution to either bot. Attribution only applies when a human directly plays against a bot and then sees an ad. Spectator ads are not attributed.

**Rationale:** Attribution is for incentivizing bots to create engaging matches for humans, not for bot-on-bot games.

---

### EC-5: Duplicate Impression Recording

**Scenario:** Client sends `record_interstitial_impression` twice for same ad_request_id.

**Decision:** Second call returns `CONFLICT_AD_ALREADY_RECORDED` error. First impression stands.

**Rationale:** Prevents double-counting and fraud.

---

### EC-6: Ad Request Expiration

**Scenario:** Client requests interstitial but doesn't show it within 5 minutes.

**Decision:** Request expires. Recording attempt after expiration returns `CONFLICT_AD_REQUEST_EXPIRED`. Client must request new ad.

**Rationale:** Ad provider tokens/data expire. Stale requests shouldn't be recorded.

---

### EC-7: Banner Minimum View Duration

**Scenario:** Banner was displayed for only 500ms before player navigated away.

**Decision:** Do not record impression if `view_duration_ms < banner_min_view_ms` (default 1000ms).

**Rationale:** Sub-second views aren't meaningful impressions. Prevents inflation.

---

### EC-8: Event Ad Opportunity Cooldown

**Scenario:** Event has a "Watch Ad for 100 Points" opportunity with 60-minute cooldown. Player tries to claim again after 30 minutes.

**Decision:** Return `RATE_LIMIT_OPPORTUNITY_COOLDOWN` with `retry_after` showing remaining time.

**Rationale:** Cooldowns are per-opportunity, per-player to prevent spam.

---

### EC-9: Ad-Free Status Expires

**Scenario:** Player had 7-day promotional ad-free that expired.

**Decision:** Background job (or lazy evaluation on check) updates `is_ad_free=false` when `expires_at < now()`. Player sees ads again.

**Rationale:** Time-limited ad-free is legitimate promotion tool.

---

### EC-10: Revenue Estimation Accuracy

**Scenario:** Estimated revenue doesn't match actual provider payments.

**Decision:** `estimated_revenue_cents` is clearly labeled as estimate. Actual reconciliation happens separately (finance module, not in scope). Bot earnings use estimated values with clear documentation.

**Rationale:** Exact revenue requires settlement reports from ad providers. Estimates are useful for immediate feedback.

---

## Open Questions

None. All design decisions have been resolved based on:
- Feasibility report specifications
- Interface contracts guidance
- Data layer guidance
- Dependency module artifacts (player, events)
- GDD requirements for ad integration and bot revenue sharing

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-05 | 1.0 | Initial artifact | Scout Agent (ads) |
