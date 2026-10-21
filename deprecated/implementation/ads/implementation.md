# Ads Module Implementation Document

## Module Overview

The ads module manages all advertisement-related functionality for ChromaCrush: interstitial ads, rewarded videos, banner impressions, ad-free status management, bot revenue attribution, and event-specific ad opportunities.

## Files Created

### Module Source (`src/modules/ads/`)

| File | Lines | Purpose |
|------|-------|---------|
| `types.py` | ~180 | Enums (AdType, InterstitialTrigger, RewardedAdType, BannerPlacement, AdFreeReason, AdRequestStatus, StatsPeriod), NewTypes (AdRequestId, AdImpressionId), and 14 dataclasses for domain objects |
| `dto.py` | ~122 | Repository DTOs: AdRequestCreate, AdRequestUpdate, AdImpressionCreate, AdFreeStatusUpsert, AdRewardCreate, EventAdOpportunityCreate, EventAdClaimCreate, PaginatedResult[T] |
| `protocols.py` | ~321 | AdServiceProtocol (16 methods), 6 repository protocols, AdProviderProtocol, minimal dependency protocols (PlayerServiceProtocol, EventServiceProtocol) |
| `service.py` | ~407 | AdRepositoryBundle class, AdService class with 16 public methods and 6 private helpers |
| `_helpers.py` | ~171 | Pure builder functions extracted from service to stay under 500-line limit |
| `__init__.py` | ~50 | Public exports for all types, DTOs, protocols, and service classes |

### Data Layer

| File | Purpose |
|------|---------|
| `src/data/models/ad_request.py` | AdRequestModel ORM (ad_requests table) |
| `src/data/models/ad_impression.py` | AdImpressionModel ORM (ad_impressions table) |
| `src/data/models/ad_free_status.py` | AdFreeStatusModel ORM (ad_free_status table) |
| `src/data/models/ad_reward.py` | AdRewardModel ORM (ad_rewards_granted table) |
| `src/data/models/event_ad_opportunity.py` | EventAdOpportunityModel ORM (event_ad_opportunities table) |
| `src/data/models/event_ad_claim.py` | EventAdClaimModel ORM (event_ad_claims table) |
| `src/data/protocols/ad_impression_repository.py` | Protocol for ad impression repository |
| `src/data/protocols/ad_request_repository.py` | Protocol for ad request repository |
| `src/data/protocols/ad_free_status_repository.py` | Protocol for ad-free status repository |
| `src/data/protocols/ad_reward_repository.py` | Protocol for ad reward repository |
| `src/data/protocols/event_ad_opportunity_repository.py` | Protocol for event ad opportunity repository |
| `src/data/protocols/event_ad_claim_repository.py` | Protocol for event ad claim repository |
| `src/data/repositories/ad_request_repository.py` | SQLAlchemy implementation |
| `src/data/repositories/ad_impression_repository.py` | SQLAlchemy implementation |
| `src/data/repositories/ad_free_status_repository.py` | SQLAlchemy implementation |
| `src/data/repositories/ad_reward_repository.py` | SQLAlchemy implementation |
| `src/data/repositories/event_ad_opportunity_repository.py` | SQLAlchemy implementation |
| `src/data/repositories/event_ad_claim_repository.py` | SQLAlchemy implementation |
| `src/data/migrations/versions/007_ad_tables.py` | Alembic migration for all 6 tables |

### CLI Commands (`src/cli/commands/ads_commands.py`)

14 commands covering all artifact-specified CLI operations:
- `ads check-status` -- Check player ad-free status
- `ads grant-ad-free` -- Grant ad-free status
- `ads revoke-ad-free` -- Revoke ad-free status
- `ads request-interstitial` -- Request interstitial ad
- `ads record-interstitial` -- Record interstitial impression
- `ads request-rewarded` -- Request rewarded video
- `ads complete-rewarded` -- Complete rewarded video
- `ads record-banner` -- Record banner impression
- `ads player-stats` -- Show player ad statistics
- `ads impressions` -- List player ad impressions
- `ads match-attribution` -- Show match ad attribution
- `ads bot-report` -- Show bot ad attribution report
- `ads event-opportunities` -- List event ad opportunities
- `ads claim-opportunity` -- Claim event ad opportunity

### Tests (`tests/unit/modules/ads/test_ad_service.py`)

35 test cases covering:
- All 16 public methods (happy path)
- Error paths: not_found, conflict, validation, forbidden, rate_limited
- Edge cases: EC-1 (mid-request ad-free), EC-5 (duplicate recording), EC-6 (expiration), EC-7 (banner minimum), EC-8 (event cooldown)
- Ad provider error wrapping

## Deviations from Artifact

### 1. AdRepositoryBundle (Approved Pattern)

The artifact defines AdService with 9 constructor parameters (config, logger, errors, player_service, events_service, and 6 repositories). Best practices guidance limits constructors to 6 parameters.

**Solution:** Created `AdRepositoryBundle` class that groups all 6 repository dependencies into a single injectable, reducing the AdService constructor to 7 parameters (config, logger, errors, player_service, events_service, repos, ad_provider).

**Justification:** Follows the composition pattern seen elsewhere in the codebase. The bundle is a simple data holder with no business logic -- it only groups related repositories for injection convenience.

### 2. Helper Extraction to `_helpers.py`

The artifact presents all logic within a single AdService class. The initial implementation exceeded the 500-line hard limit at 956 lines.

**Solution:** Extracted 9 pure builder/converter functions into `_helpers.py`:
- `build_ad_free_status` -- Convert DB record to domain AdFreeStatus
- `build_impression` -- Convert DB record to domain AdImpression
- `calc_revenue` -- Calculate estimated revenue per impression
- `stats_date_range` -- Compute date range for StatsPeriod enum
- `build_player_stats` -- Convert stats aggregate to domain object
- `build_daily_attr` -- Convert daily attribution record
- `build_event_opp` -- Convert event opportunity record
- `build_match_attribution` -- Build MatchAdAttribution from impressions
- `build_bot_report` -- Build BotAdAttributionReport from aggregates

All extracted functions are pure (no side effects, no service dependencies) and are not part of the public API.

**Justification:** Mandatory per best-practices guidance. The `_helpers.py` file is a private implementation detail prefixed with underscore, not importable from the module's `__init__.py`.

### 3. Minimal Dependency Protocols

The artifact references `PlayerServiceProtocol` and `EventServiceProtocol` from their respective modules. To avoid circular imports, the ads module defines its own minimal protocol interfaces in `protocols.py`:

- `PlayerServiceProtocol` with only `get_player()`
- `EventServiceProtocol` with only `get_event()` and `get_event_participant()`

These are the only methods the ads module actually calls on these dependencies.

**Justification:** Follows the pattern established by the events module (`src/modules/events/protocols.py` defines its own minimal dependency protocols).

## Configuration Keys Used

| Key | Default | Purpose |
|-----|---------|---------|
| `ads.interstitial_cooldown_seconds` | 180 | Cooldown between interstitial requests |
| `ads.rewarded_cooldown_seconds` | 60 | Cooldown between rewarded video requests |
| `ads.banner_min_view_ms` | 1000 | Minimum banner view time for valid impression |
| `ads.rewarded_min_watch_percent` | 95 | Minimum watch percentage for reward grant |
| `ads.rewarded_heart_reward` | 1 | Hearts granted per rewarded video |
| `ads.bot_attribution_share_percent` | 30.0 | Percentage of revenue attributed to bots |
| `ads.estimated_cpm_cents` | 200 | Estimated CPM in cents |
| `ads.event_opportunity_cooldown_minutes` | 60 | Default event ad opportunity cooldown |
| `ads.interstitial_unit_id` | "default_interstitial" | Ad unit ID for interstitials |
| `ads.rewarded_unit_id` | "default_rewarded" | Ad unit ID for rewarded videos |
| `ads.provider_name` | "mock" | Ad provider name for logging |

## Error Codes Used

| Code | HTTP | When |
|------|------|------|
| `VALIDATION_INVALID_INPUT` | 400 | Invalid duration, limit, banner view time, dates |
| `VALIDATION_PLAYER_NOT_BOT` | 400 | Bot report requested for non-bot player |
| `NOT_FOUND_PLAYER` | 404 | Player not found or not ad-free (revoke) |
| `NOT_FOUND_AD_REQUEST` | 404 | Ad request ID not found |
| `NOT_FOUND_AD_OPPORTUNITY` | 404 | Event ad opportunity not found |
| `FORBIDDEN_PLAYER_AD_FREE` | 403 | Ad-free player trying to view ads |
| `CONFLICT_AD_ALREADY_RECORDED` | 409 | Impression already recorded for request |
| `CONFLICT_AD_REQUEST_EXPIRED` | 409 | Ad request past expiration time |
| `CONFLICT_OPPORTUNITY_ALREADY_CLAIMED` | 409 | Event opportunity fully claimed |
| `RATE_LIMIT_AD_COOLDOWN` | 429 | Ad type on cooldown |
| `RATE_LIMIT_OPPORTUNITY_COOLDOWN` | 429 | Event opportunity on cooldown |
| `INTERNAL_AD_PROVIDER_ERROR` | 500 | Third-party ad provider failure |

## Async Contract

All 16 public methods are `async def`. The service is fully async with no fire-and-forget or background operations.

## Data Ownership

The ads module owns all 6 tables:
- `ad_requests` (lifecycle tracking)
- `ad_impressions` (impression records)
- `ad_free_status` (per-player status)
- `ad_rewards_granted` (reward grants)
- `event_ad_opportunities` (event-specific opportunities)
- `event_ad_claims` (player claims of opportunities)

Read-only access: `players` (via player service), `events` (via events service).
