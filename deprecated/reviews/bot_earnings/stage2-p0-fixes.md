# Stage 2 P0 Fixes: bot_earnings

**Reviewer:** Karen P0 (Stage 2 Interface Compliance)
**Date:** 2026-02-06
**Files reviewed:**
- `src/modules/bot_earnings/protocols.py`
- `src/modules/bot_earnings/types.py`
- `src/modules/bot_earnings/dto.py`

**Reference documents:**
- `docs/guidance/interface-contracts.md` (Sections 1-2)
- `docs/artifacts/bot_earnings/artifact.md` (Public Interface & Outputs)

---

## Protocol Signature Checks

All `BotEarningsServiceProtocol` method signatures in `protocols.py` match the artifact exactly:
- `get_earnings_balance(bot_player_id) -> EarningsBalance`: match
- `get_earnings_summary(bot_player_id, period) -> EarningsSummary`: match
- `get_attribution_entries(bot_player_id, start_date, end_date, limit, offset) -> PaginatedResult[AttributionEntry]`: match
- `get_daily_earnings(bot_player_id, start_date, end_date) -> list[DailyEarnings]`: match
- `sync_attributions(bot_player_id) -> AttributionSyncResult`: match
- `sync_all_attributions() -> BulkSyncResult`: match
- `request_payout(bot_player_id, requesting_owner_id) -> PayoutRequest`: match
- `get_payout_requests(bot_player_id, status, limit, offset) -> PaginatedResult[PayoutRequest]`: match
- `get_payout_request(payout_request_id) -> PayoutRequest`: match
- `cancel_payout_request(payout_request_id, requesting_owner_id) -> PayoutRequest`: match
- `process_payout(payout_request_id, processor_id, external_reference) -> PayoutRequest`: match
- `reject_payout(payout_request_id, processor_id, reason) -> PayoutRequest`: match
- `get_bot_owner(bot_player_id) -> PlayerId`: match

All methods are `async def`: confirmed.

No P0 issues found in protocol signatures.

---

## Type Alias Checks

- `PlayerId` imported from `src.core.types.game`: correct per interface-contracts.md Section 1.1
- `MatchId` imported from `src.core.types.game`: correct
- `PayoutRequestId = NewType("PayoutRequestId", UUID)`: correct (module-specific opaque ID)
- `AttributionEntryId = NewType("AttributionEntryId", UUID)`: correct (module-specific opaque ID)
- `AdImpressionId = NewType("AdImpressionId", UUID)`: correct (module-specific opaque ID)

No P0 issues found in type aliases.

---

## DTO / Dataclass Shape Checks

### `EarningsBalance`
Implementation (types.py:60-70) vs artifact (artifact.md:208-218):
- `bot_player_id: PlayerId`: match
- `total_earned_cents: int`: match
- `total_paid_out_cents: int`: match
- `pending_payout_cents: int`: match
- `available_balance_cents: int`: match
- `last_attribution_at: datetime | None`: match
- `last_sync_at: datetime | None`: match

PASS.

### `EarningsSummary`
Implementation (types.py:74-87) vs artifact (artifact.md:225-239):
- `bot_player_id: PlayerId`: match
- `period: EarningsPeriod`: match
- `period_start: date`: match
- `period_end: date`: match
- `total_attributions: int`: match
- `total_matches: int`: match
- `total_impressions: int`: match
- `earnings_cents: int`: match
- `average_daily_cents: int`: match
- `top_earning_day: date | None`: match
- `top_earning_day_cents: int`: match

PASS.

### `AttributionEntry`
Implementation (types.py:91-103) vs artifact (artifact.md:246-259):
- `id: AttributionEntryId`: match
- `bot_player_id: PlayerId`: match
- `match_id: MatchId`: match
- `ad_impression_id: AdImpressionId`: match
- `opponent_player_id: PlayerId`: match
- `estimated_impression_revenue_cents: int`: match
- `attribution_share_percent: float`: match
- `attributed_cents: int`: match
- `recorded_at: datetime`: match
- `attribution_date: date`: match

PASS.

### `DailyEarnings`
Implementation (types.py:107-114) vs artifact (artifact.md:266-274):
- `date: date`: match
- `attributions: int`: match
- `matches: int`: match
- `impressions: int`: match
- `earnings_cents: int`: match

PASS.

### `AttributionSyncResult`
Implementation (types.py:118-126) vs artifact (artifact.md:282-290):
- `bot_player_id: PlayerId`: match
- `new_attributions: int`: match
- `new_earnings_cents: int`: match
- `sync_start: datetime`: match
- `sync_end: datetime`: match
- `errors: list[str]`: match (artifact says `list[str]`, implementation uses `field(default_factory=list)` which is correct)

PASS.

### `BulkSyncResult`
Implementation (types.py:130-138) vs artifact (artifact.md:296-306):
- `bots_synced: int`: match
- `total_new_attributions: int`: match
- `total_new_earnings_cents: int`: match
- `errors: list[tuple[PlayerId, str]]`: match
- `sync_start: datetime`: match
- `sync_end: datetime`: match

PASS.

### `PayoutRequest`
Implementation (types.py:142-155) vs artifact (artifact.md:312-327):
- `id: PayoutRequestId`: match
- `bot_player_id: PlayerId`: match
- `owner_player_id: PlayerId`: match
- `amount_cents: int`: match
- `status: PayoutStatus`: match
- `requested_at: datetime`: match
- `processed_at: datetime | None`: match
- `processed_by: PlayerId | None`: match
- `external_reference: str | None`: match
- `rejection_reason: str | None`: match
- `notes: str | None`: match

PASS.

---

## Error Code Checks

All error codes referenced in the artifact's "Error Cases" are verified against interface-contracts.md Section 2:

- `NOT_FOUND_PLAYER`: present in Section 2 Not Found Errors table. PASS.
- `NOT_FOUND_PAYOUT_REQUEST`: present in Section 2 Not Found Errors table. PASS.
- `VALIDATION_INSUFFICIENT_BALANCE`: present in Section 2 Validation Errors table. PASS.
- `VALIDATION_BELOW_PAYOUT_THRESHOLD`: present in Section 2 Validation Errors table. PASS.
- `VALIDATION_DATE_RANGE_TOO_LARGE`: present in Section 2 Validation Errors table. PASS.
- `VALIDATION_INVALID_INPUT`: present in Section 2 Validation Errors table. PASS.
- `FORBIDDEN_NOT_BOT_OWNER`: present in Section 2 Authorization Errors table. PASS.
- `CONFLICT_PAYOUT_NOT_PENDING`: present in Section 2 Conflict Errors table. PASS.
- `CONFLICT_PENDING_PAYOUT_EXISTS`: present in Section 2 Conflict Errors table. PASS.
- `CONFLICT_SYNC_IN_PROGRESS`: present in Section 2 Conflict Errors table. PASS.
- `INTERNAL_ADS_SERVICE_ERROR`: present in Section 2 Internal Errors table. PASS.
- `INTERNAL_DATABASE_ERROR`: present in Section 2 Internal Errors table. PASS.

The following error codes from the artifact are NOT in the interface-contracts.md taxonomy:

[P0] [artifact:error-cases] `VALIDATION_PLAYER_NOT_BOT` not in interface-contracts.md Section 2 error taxonomy -- artifact uses this but interface-contracts.md has `FORBIDDEN_NOT_BOT` (Section 2 Authorization Errors 403) instead

This is a code mismatch. The artifact says `VALIDATION_PLAYER_NOT_BOT` (validation error, 400 status), while the interface-contracts.md taxonomy defines `FORBIDDEN_NOT_BOT` (authorization error, 403 status) with message "Action requires bot account". These are semantically different: one treats "not a bot" as a validation failure, the other as an authorization failure. The contract's `FORBIDDEN_NOT_BOT` should be authoritative.

[P0] [artifact:error-cases] `FORBIDDEN_NOT_ADMIN` not in interface-contracts.md Section 2 error taxonomy

The artifact defines `FORBIDDEN_NOT_ADMIN` for admin-only operations (process_payout, reject_payout) but this code does not appear in the interface-contracts.md error taxonomy.

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
| Error codes in taxonomy | 2 P0 findings |

### P0 Findings

```
[P0] [artifact:error-cases] VALIDATION_PLAYER_NOT_BOT used in artifact but interface-contracts.md §2 defines FORBIDDEN_NOT_BOT (403) instead -> implementation and artifact should use FORBIDDEN_NOT_BOT per interface-contracts.md §2 Authorization Errors
[P0] [artifact:error-cases] FORBIDDEN_NOT_ADMIN not in interface-contracts.md §2 error taxonomy -> Orchestrator must add to taxonomy or use existing code
```

**Recommendation:** Corrections needed.

1. **`VALIDATION_PLAYER_NOT_BOT` vs `FORBIDDEN_NOT_BOT`**: The interface-contracts.md defines `FORBIDDEN_NOT_BOT` (403) for "Action requires bot account" with context field `player_id`. The artifact and implementation should use `FORBIDDEN_NOT_BOT` instead of `VALIDATION_PLAYER_NOT_BOT`. This changes the error category from validation (400) to authorization (403), which is semantically more correct -- the player exists and the input is valid, they just lack the required account type.

2. **`FORBIDDEN_NOT_ADMIN`**: The Orchestrator should add this code to interface-contracts.md Section 2 Authorization Errors, or define a standard mechanism for admin authorization failures. This code is needed by bot_earnings (and potentially other modules with admin operations).
