# Stage 2 P0 Fixes: ads

**Reviewer:** Karen P0 (Stage 2 Interface Compliance)
**Date:** 2026-02-06
**Files reviewed:**
- `src/modules/ads/protocols.py`
- `src/modules/ads/types.py`
- `src/modules/ads/dto.py`

**Reference documents:**
- `docs/guidance/interface-contracts.md` (Sections 1-2)
- `docs/artifacts/ads/artifact.md` (Public Interface & Outputs)

---

## Protocol Signature Checks

All `AdServiceProtocol` method signatures in `protocols.py` match the artifact exactly:
- `check_ad_free_status(player_id: PlayerId) -> AdFreeStatus`: match
- `can_show_ad(player_id, ad_type, context)`: match
- `request_interstitial(player_id, trigger, match_id)`: match
- `record_interstitial_impression(ad_request_id, viewed, duration_ms)`: match
- `request_rewarded_video(player_id, reward_type)`: match
- `complete_rewarded_video(ad_request_id, completed, watched_duration_ms)`: match
- `record_banner_impression(player_id, banner_placement, view_duration_ms)`: match
- `get_player_ad_stats(player_id, period)`: match
- `get_ad_impressions(player_id, ad_type, limit, offset)`: match
- `get_match_ad_attribution(match_id)`: match
- `get_bot_ad_attributions(bot_player_id, start_date, end_date)`: match
- `grant_ad_free_status(player_id, reason, duration_days, granted_by)`: match
- `revoke_ad_free_status(player_id, reason)`: match
- `get_event_ad_opportunities(player_id, event_id)`: match
- `claim_event_ad_reward(player_id, event_id, opportunity_id)`: match

All methods are `async def`: confirmed.

No P0 issues found in protocol signatures.

---

## Type Alias Checks

- `PlayerId` imported from `src.core.types.game`: correct per interface-contracts.md Section 1.1
- `MatchId` imported from `src.core.types.game`: correct
- `EventId` imported from `src.core.types.game`: correct
- `AdRequestId = NewType("AdRequestId", UUID)` defined in `types.py`: correct (module-specific opaque ID, not a core type)
- `AdImpressionId = NewType("AdImpressionId", UUID)` defined in `types.py`: correct (module-specific opaque ID)

No P0 issues found in type aliases.

---

## DTO / Dataclass Shape Checks

All output dataclass shapes in `types.py` match their artifact definitions exactly:

- `AdFreeStatus`: fields match artifact (player_id, is_ad_free, reason, granted_at, expires_at, is_permanent)
- `AdEligibility`: fields match artifact (can_show, reason, cooldown_remaining_seconds, ad_request_token)
- `InterstitialAdResult`: fields match artifact (ad_request_id, ad_unit_id, should_show, ad_data, created_at)
- `AdImpression`: fields match artifact (id, player_id, ad_type, ad_request_id, viewed, view_duration_ms, trigger, match_id, event_id, attributed_to, estimated_revenue_cents, created_at)
- `RewardedVideoRequest`: fields match artifact (ad_request_id, ad_unit_id, reward_type, reward_value, video_available, ad_data, expires_at)
- `RewardedVideoResult`: fields match artifact (ad_request_id, completed, watched_duration_ms, reward_granted, reward_type, reward_value, impression)
- `PlayerAdStats`: fields match artifact (player_id, period, total_impressions, interstitial_count, rewarded_video_count, banner_impression_count, total_rewards_earned, average_view_duration_ms, last_ad_at)
- `MatchAdAttribution`: fields match artifact (match_id, player1_id, player2_id, player1_is_bot, player2_is_bot, impressions, total_impressions, estimated_revenue_cents, bot_attribution_cents)
- `BotAdAttributionReport`: fields match artifact (bot_player_id, start_date, end_date, total_matches, matches_with_impressions, total_attributed_impressions, estimated_revenue_cents, attributed_revenue_cents, attribution_share_percent, daily_breakdown)
- `EventAdOpportunity`: fields match artifact (opportunity_id, event_id, ad_type, reward_type, reward_value, description, times_available, times_claimed, cooldown_minutes, available, next_available_at)
- `EventAdRewardResult`: fields match artifact. Note: artifact does not explicitly define `EventAdRewardResult` as a formal output section, but the implementation's shape (opportunity_id, event_id, player_id, reward_type, reward_value, impression, claimed_at) is consistent with the method return type `claim_event_ad_reward -> EventAdRewardResult`.
- `AdProviderResponse`: fields match artifact (success, ad_available, ad_data, error_code, error_message)

No P0 issues found in DTO/dataclass shapes.

---

## Error Code Checks

The following error codes used in the artifact's "Error Cases" table are NOT present in the interface-contracts.md Section 2 error taxonomy:

[P0] [artifact:error-cases] `FORBIDDEN_PLAYER_AD_FREE` not in interface-contracts.md Section 2 error taxonomy
[P0] [artifact:error-cases] `NOT_FOUND_AD_REQUEST` not in interface-contracts.md Section 2 error taxonomy
[P0] [artifact:error-cases] `CONFLICT_AD_ALREADY_RECORDED` not in interface-contracts.md Section 2 error taxonomy
[P0] [artifact:error-cases] `CONFLICT_AD_REQUEST_EXPIRED` not in interface-contracts.md Section 2 error taxonomy
[P0] [artifact:error-cases] `VALIDATION_REWARDED_AD_NOT_COMPLETED` not in interface-contracts.md Section 2 error taxonomy
[P0] [artifact:error-cases] `RATE_LIMIT_AD_COOLDOWN` not in interface-contracts.md Section 2 error taxonomy
[P0] [artifact:error-cases] `NOT_FOUND_AD_OPPORTUNITY` not in interface-contracts.md Section 2 error taxonomy
[P0] [artifact:error-cases] `CONFLICT_OPPORTUNITY_ALREADY_CLAIMED` not in interface-contracts.md Section 2 error taxonomy
[P0] [artifact:error-cases] `RATE_LIMIT_OPPORTUNITY_COOLDOWN` not in interface-contracts.md Section 2 error taxonomy
[P0] [artifact:error-cases] `VALIDATION_PLAYER_NOT_BOT` not in interface-contracts.md Section 2 error taxonomy
[P0] [artifact:error-cases] `INTERNAL_AD_PROVIDER_ERROR` not in interface-contracts.md Section 2 error taxonomy

The following codes ARE present in the interface-contracts.md taxonomy and are used correctly:
- `NOT_FOUND_PLAYER`: present in taxonomy
- `VALIDATION_INVALID_INPUT`: present in taxonomy
- `CONFLICT_EVENT_NOT_ACTIVE`: NOT in taxonomy (same issue as events module)
- `FORBIDDEN_NOT_EVENT_PARTICIPANT`: NOT in taxonomy (same issue as events module)
- `INTERNAL_DATABASE_ERROR`: present in taxonomy

**Note on `INTERNAL_ADS_SERVICE_ERROR`:** The interface-contracts.md taxonomy includes `INTERNAL_ADS_SERVICE_ERROR` (Section 2.6 Internal Errors table). However, the ads module artifact defines a slightly different code `INTERNAL_AD_PROVIDER_ERROR` (singular "AD" vs the taxonomy's "ADS"). Checking: the taxonomy has `INTERNAL_ADS_SERVICE_ERROR` for "Ads module call failed" and also `INTERNAL_PAYMENT_PROVIDER_ERROR` for "Payment provider error". The ads artifact uses `INTERNAL_AD_PROVIDER_ERROR` which is distinct from both. This is technically a new code not in the taxonomy.

**Note:** Similar to the events module, the ads-specific error codes ARE defined in the artifact and used consistently. The issue is that the interface-contracts.md error taxonomy was never updated to include ads module error codes. This is an escalation item for the Orchestrator.

---

## Summary

| Check | Result |
|-------|--------|
| Protocol method signatures | PASS |
| Parameter names/types | PASS |
| Return types | PASS |
| Async behavior | PASS |
| Type aliases from core | PASS |
| DTO/dataclass shapes | PASS |
| Error codes in taxonomy | 11 P0 (codes not in interface-contracts.md) |

**Recommendation:** Corrections needed.

1. **Error codes**: The Orchestrator must add the 11 ads-specific error codes to `docs/guidance/interface-contracts.md` Section 2. Until then, the codes are artifact-authorized but not contract-authorized. This is the same pattern as the events module -- these modules were designed after the initial interface-contracts.md was written.
