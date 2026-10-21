# Stage 1 Drift Report: ads

**Reviewer:** Document Reviewer (Karen Compliance Sweep)
**Date:** 2026-02-06
**Artifact:** docs/artifacts/ads/report.md + docs/artifacts/ads/artifact.md
**Implementation Doc:** docs/implementation/ads/implementation.md

---

## Method Count

[DRIFT] Artifact defines 15 public methods in the Inputs section (check_ad_free_status, can_show_ad, request_interstitial, record_interstitial_impression, request_rewarded_video, complete_rewarded_video, record_banner_impression, get_player_ad_stats, get_ad_impressions, get_match_ad_attribution, get_bot_ad_attributions, grant_ad_free_status, revoke_ad_free_status, get_event_ad_opportunities, claim_event_ad_reward) -> Implementation doc states "AdServiceProtocol (16 methods)". The impl doc does not enumerate all 16 method names, making it impossible to determine which method was added without reading source code. Recommend closer scrutiny in Stage 3 to identify the 16th method.

## Constructor Signature

[DRIFT] Artifact constructor has 9 parameters (config, logger, errors, data_ctx, player_service, events_service, ad_impression_repository, ad_reward_repository, ad_provider) -> Implementation doc deviation #1 documents that AdRepositoryBundle was created to group 6 repository dependencies, reducing constructor to 7 parameters (config, logger, errors, player_service, events_service, repos, ad_provider). Note that `data_ctx` is absent from the impl constructor -- it appears to have been dropped entirely or is accessed through the bundle.

The artifact lists 6 repository protocols (AdImpressionRepository, AdRequestRepository, AdFreeStatusRepository, AdRewardRepository, EventAdOpportunityRepository, EventAdClaimRepository), but the artifact constructor only names 2 of them (ad_impression_repository, ad_reward_repository). The impl groups all 6 into AdRepositoryBundle. This means the artifact constructor was already incomplete relative to its own repository interface definitions.

## Error Codes

[DRIFT] Artifact error cases table lists 15 error codes including `VALIDATION_REWARDED_AD_NOT_COMPLETED` -> Implementation doc error table lists 12 error codes. Missing from impl doc: `VALIDATION_REWARDED_AD_NOT_COMPLETED`, `CONFLICT_EVENT_NOT_ACTIVE`, `FORBIDDEN_NOT_EVENT_PARTICIPANT`. These may still be implemented but are not documented.

[DRIFT] Implementation doc adds `RATE_LIMIT_OPPORTUNITY_COOLDOWN` which is in the artifact but also adds `NOT_FOUND_PLAYER` as a separate error code that the artifact does not list in its error cases table (though it does mention "Player not found" -> `NOT_FOUND_PLAYER`). On closer inspection this is present in both. No additional drift here.

## Public Interface Shape

Artifact defines 10 output dataclasses. Implementation doc does not enumerate output types individually but lists "14 dataclasses for domain objects" in types.py. Without enumerating them, impossible to confirm exact match. Recommend code scrutiny in Stage 3.

## Configuration Keys

[DRIFT] Artifact lists 14 config keys (including `ads.provider_api_key`, `ads.banner_unit_id`, `ads.ad_free_trial_days`) -> Implementation doc lists 11 config keys. Missing from impl: `ads.provider_api_key`, `ads.banner_unit_id`, `ads.ad_free_trial_days`. These three config keys from the artifact are not documented in the implementation.

## Helper Extraction

Implementation doc deviation #2 documents extraction of 9 pure functions into `_helpers.py` to stay under 500-line limit. This is an architectural addition not in the artifact but is documented with justification. Acceptable per best-practices guidance.

## Minimal Dependency Protocols

Implementation doc deviation #3 documents that ads module defines its own minimal `PlayerServiceProtocol` and `EventServiceProtocol` rather than importing from those modules. Documented with justification referencing events module pattern.

## Data Ownership

Artifact report says "6 tables." Implementation doc lists 6 tables. Consistent.

## Deviations Documented

Three deviations documented in implementation doc. All include justification.

## Implementation Doc Completeness

Implementation doc is 158 lines. Not flagged as thin.

## Summary

- 1 method count discrepancy (15 artifact vs 16 impl) -- the extra method is unidentified
- Constructor shape changed significantly (9 artifact params vs 7 impl params via bundle pattern)
- 3 config keys from artifact not documented in impl
- 3 error codes from artifact not documented in impl
- Output type count unclear (artifact 10 explicit, impl says 14 dataclasses)
- All deviations documented with justification
