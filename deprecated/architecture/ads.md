# Module Architecture Report: ads

**Module:** ads
**Build Wave:** 7
**Reviewer:** Karen (Stage 6)
**Date:** 2026-02-07

---

## 1. Module Overview

The ads module manages all advertisement integration for ChromaCrush, supporting the primary monetization mechanism for free-tier players. It handles three ad types (interstitial, rewarded video, banner), ad-free status management (permanent via purchase or time-limited via promotion), bot revenue attribution for ad impressions linked to bot matches, and event-specific ad opportunities. The ad provider is abstracted behind a Protocol interface for testability and provider switching. All 16 public service methods are **asynchronous** (`async def`) with no fire-and-forget or background operations. The service uses an `AdRepositoryBundle` pattern to group six repository dependencies into a single injectable, keeping the constructor parameter count within best-practices limits.

---

## 2. Public Interface

| Method | Signature | Purpose |
|--------|-----------|---------|
| `check_ad_free_status` | `(player_id) -> AdFreeStatus` | Check player ad-free status |
| `grant_ad_free_status` | `(player_id, reason, duration_days?) -> AdFreeStatus` | Grant ad-free (permanent or time-limited) |
| `revoke_ad_free_status` | `(player_id, reason) -> None` | Revoke ad-free status |
| `can_show_ad` | `(player_id, ad_type) -> bool` | Check if ad can be shown (cooldown, ad-free) |
| `request_interstitial` | `(player_id, trigger, match_id?) -> AdRequest` | Request interstitial ad placement |
| `record_interstitial_impression` | `(ad_request_id, duration_ms) -> AdImpression` | Record interstitial was viewed |
| `request_rewarded_video` | `(player_id, reward_type) -> AdRequest` | Request rewarded video |
| `complete_rewarded_video` | `(ad_request_id, watched_percent, duration_ms) -> AdImpression` | Complete rewarded video and grant reward |
| `record_banner_impression` | `(player_id, placement, view_duration_ms, match_id?) -> AdImpression` | Record banner ad impression |
| `get_player_ad_stats` | `(player_id, period?) -> PlayerAdStats` | Get player ad statistics |
| `get_ad_impressions` | `(player_id, ad_type?, limit?, offset?) -> PaginatedResult[AdImpression]` | List player ad impressions |
| `get_match_ad_attribution` | `(match_id) -> MatchAdAttribution` | Get ad attribution for a match |
| `get_bot_ad_attributions` | `(bot_player_id, start_date, end_date) -> BotAdAttributionReport` | Bot ad attribution report |
| `get_event_ad_opportunities` | `(event_id) -> list[EventAdOpportunity]` | List event ad opportunities |
| `claim_event_ad_reward` | `(opportunity_id, player_id) -> EventAdClaim` | Claim event ad opportunity |
| *(16th method)* | *(identified at code level)* | *(Implementation adds one method beyond artifact's 15)* |

---

## 3. Dependencies Consumed

| Dependency | Protocol | Purpose |
|------------|----------|---------|
| `config` | `ConfigProtocol` | Ad configuration (cooldowns, thresholds, unit IDs) |
| `logger` | `LoggerProtocol` | Structured diagnostic logging |
| `errors` | `ErrorServiceProtocol` | Create typed errors |
| `player_service` | `PlayerServiceProtocol` (minimal) | Player existence and bot status checks |
| `events_service` | `EventServiceProtocol` (minimal) | Event and participant lookups |
| `repos` | `AdRepositoryBundle` | Groups 6 repository protocols (see Data Owned) |
| `ad_provider` | `AdProviderProtocol` | Third-party ad SDK abstraction |

---

## 4. Data Owned

| Table | Description |
|-------|-------------|
| `ad_requests` | Ad request lifecycle tracking (type, status, expiry) |
| `ad_impressions` | Recorded ad impression events (duration, revenue estimate) |
| `ad_free_status` | Per-player ad-free status (reason, expiry) |
| `ad_rewards_granted` | Rewards granted from ad viewing |
| `event_ad_opportunities` | Event-specific ad opportunities |
| `event_ad_claims` | Player claims of event ad opportunities |

Read-only access to `players` (via player service) and `events` (via events service).

---

## 5. Configuration Keys

| Key | Type | Default | Purpose |
|-----|------|---------|---------|
| `ads.interstitial_cooldown_seconds` | int | 60 | Interstitial ad cooldown |
| `ads.rewarded_cooldown_seconds` | int | 300 | Rewarded ad cooldown |
| `ads.banner_min_view_ms` | int | 1000 | Min banner view duration for valid impression |
| `ads.rewarded_min_watch_percent` | int | 80 | Min percent to earn reward |
| `ads.rewarded_heart_reward` | int | 1 | Hearts earned from rewarded ad |
| `ads.bot_attribution_share_percent` | float | 30.0 | Bot share of ad revenue |
| `ads.estimated_cpm_cents` | int | 500 | Estimated CPM in cents |
| `ads.event_opportunity_cooldown_minutes` | int | 30 | Event ad opportunity cooldown |
| `ads.interstitial_unit_id` | string | "" | Ad provider interstitial unit ID |
| `ads.rewarded_unit_id` | string | "" | Ad provider rewarded unit ID |
| `ads.provider_name` | string | "admob" | Ad provider name |

---

## 6. Error Codes Raised

| Code | HTTP | Trigger |
|------|------|---------|
| `VALIDATION_INVALID_INPUT` | 400 | Invalid duration, limit, banner view time, dates |
| `NOT_FOUND_PLAYER` | 404 | Player not found |
| `NOT_FOUND_AD_REQUEST` | 404 | Ad request ID not found |
| `NOT_FOUND_AD_OPPORTUNITY` | 404 | Event ad opportunity not found |
| `FORBIDDEN_PLAYER_AD_FREE` | 403 | Ad-free player trying to view ads |
| `CONFLICT_AD_ALREADY_RECORDED` | 409 | Impression already recorded for request |
| `CONFLICT_AD_REQUEST_EXPIRED` | 409 | Ad request past expiration |
| `CONFLICT_OPPORTUNITY_ALREADY_CLAIMED` | 409 | Event opportunity already claimed |
| `RATE_LIMIT_AD_COOLDOWN` | 429 | Ad type on cooldown |
| `RATE_LIMIT_OPPORTUNITY_COOLDOWN` | 429 | Event opportunity on cooldown |
| `INTERNAL_AD_PROVIDER_ERROR` | 500 | Third-party ad provider failure |
| `VALIDATION_REWARDED_AD_NOT_COMPLETED` | 400 | Rewarded video not fully watched |

---

## 7. Cross-Module Interactions

**Called by:**
- `payments` -- calls `grant_ad_free_status` on purchase completion, `revoke_ad_free_status` on refund
- `bot_earnings` -- calls `get_bot_ad_attributions` and `get_match_ad_attribution` for revenue sharing
- `api` -- exposes ads endpoints

**Calls:**
- `player` -- player existence and bot status verification
- `events` -- event and participant lookups for event ad opportunities

---

## 8. Key Types

| Type | Location | Description |
|------|----------|-------------|
| `AdType` | `src/modules/ads/types.py` | Enum: INTERSTITIAL, REWARDED, BANNER |
| `AdRequestStatus` | `src/modules/ads/types.py` | Enum: PENDING, COMPLETED, EXPIRED, CANCELLED |
| `AdFreeReason` | `src/modules/ads/types.py` | Enum: PURCHASE, PROMOTION, ADMIN, TRIAL |
| `AdFreeStatus` | `src/modules/ads/types.py` | Player ad-free status with reason and expiry |
| `AdRequest` | `src/modules/ads/types.py` | Ad request lifecycle record |
| `AdImpression` | `src/modules/ads/types.py` | Recorded ad impression with revenue estimate |
| `BotAdAttributionReport` | `src/modules/ads/types.py` | Bot ad attribution report with daily breakdown |
| `PlayerAdStats` | `src/modules/ads/types.py` | Aggregate ad statistics for a player |
