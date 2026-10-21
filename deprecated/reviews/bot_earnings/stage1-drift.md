# Stage 1 Drift Report: bot_earnings

**Reviewer:** Document Reviewer (Karen Compliance Sweep)
**Date:** 2026-02-06
**Artifact:** docs/artifacts/bot_earnings/report.md + docs/artifacts/bot_earnings/artifact.md
**Implementation Doc:** docs/implementation/bot_earnings/implementation.md

---

## Method Count

Artifact defines 13 public methods (get_earnings_balance, get_earnings_summary, get_attribution_entries, get_daily_earnings, sync_attributions, sync_all_attributions, request_payout, get_payout_requests, get_payout_request, cancel_payout_request, process_payout, reject_payout, get_bot_owner). Implementation doc states "BotEarningsService with 13 public methods."

No drift on method count.

## Constructor Signature

[DRIFT] Artifact constructor has 9 parameters (config, logger, errors, data_ctx, player_service, ads_service, earnings_ledger_repository, attribution_entry_repository, payout_request_repository) -> Implementation doc deviation #1 adds `daily_earnings_repository` parameter (10 total). Documented with justification: the `get_daily_earnings` method and sync operations require it. The artifact does define a `DailyEarningsRepository` protocol in its repository interfaces section but omits it from the constructor.

## Error Codes

[DRIFT] Artifact error cases table lists 13 error codes (including `FORBIDDEN_NOT_ADMIN`, `CONFLICT_SYNC_IN_PROGRESS`) -> Implementation doc deviation #4 explicitly states `FORBIDDEN_NOT_ADMIN` is NOT implemented ("Admin validation is not implemented in the service layer since admin authorization is a cross-cutting concern handled at the API/auth layer"). The implementation doc does not list error codes systematically, so `CONFLICT_SYNC_IN_PROGRESS` status is unknown from documentation alone.

## Public Interface Shape

Artifact output types: EarningsBalance, EarningsSummary, AttributionEntry, DailyEarnings, AttributionSyncResult, BulkSyncResult, PayoutRequest (7 types). Implementation doc mentions output dataclasses in types.py but does not enumerate them. Cannot confirm exact match from documentation alone.

## Sync Attribution Strategy

[DRIFT] Artifact algorithm pseudocode shows per-impression attribution entries (one entry per ad impression) -> Implementation doc deviation #2 states "daily aggregate entries instead (one attribution entry per bot per day) with deterministic UUID v5-based impression IDs for deduplication." This is a significant algorithmic change that affects the granularity of the audit trail. The artifact's `AttributionEntry` dataclass has `match_id` and `ad_impression_id` fields implying per-impression records; daily aggregates would not have meaningful values for these fields.

## Migration Numbering

[DRIFT] Implementation doc deviation #3 notes migration is `009` with `down_revision = "007"` because migration `008` does not exist -> This suggests the payments module migration (expected to be `008`) was either skipped or created after this module despite being in the same wave. This is a sequencing concern worth flagging but not a document drift per se.

## Configuration Keys

[DRIFT] Artifact report lists 6 config keys -> Implementation doc does not have a dedicated configuration keys section. Config keys are only mentioned obliquely in "Key Design Decisions" section as "Config keys read in __init__." The 6 artifact config keys are not documented in the implementation doc.

## Data Ownership

Artifact report lists 4 tables (bot_earnings_ledger, bot_attribution_entries, bot_payout_requests, bot_earnings_daily). Implementation doc lists 4 ORM models matching these tables. Consistent.

## CLI Commands

Artifact defines 12 CLI commands. Implementation doc lists 12 commands. Match confirmed.

## Deviations Documented

Four deviations documented in implementation doc. All include justification.

## Implementation Doc Completeness

[FLAG] Implementation doc is thin (72 lines) -- recommend closer code scrutiny in Stage 3.

The doc lacks:
- Error codes section (artifact has 13 error codes, none documented in impl)
- Configuration keys section (artifact has 6 config keys, none documented in impl)
- Public interface detail (method signatures not shown)
- Data access patterns section
- Testing detail beyond "40+ test cases"

This is the thinnest implementation doc of the four modules reviewed. It reads as a minimal file manifest with deviations rather than a comprehensive implementation record.

## Summary

- Constructor gains 1 parameter (daily_earnings_repository) -- documented deviation
- Sync algorithm fundamentally changed from per-impression to daily-aggregate -- documented but significant
- `FORBIDDEN_NOT_ADMIN` intentionally not implemented -- documented deviation
- No error codes section (13 artifact error codes undocumented)
- No configuration keys section (6 artifact config keys undocumented)
- Migration numbering anomaly (009 with down_revision 007, skipping 008)
- Implementation doc is critically thin at 72 lines -- major documentation gap
