# Module Report: bot_earnings

## Header
- **Author:** Scout Agent (bot_earnings)
- **Date:** 2026-02-05

---

## Summary

The `bot_earnings` module has been designed to track and manage revenue sharing for bots in ChromaCrush. The key outcomes of this design work:

1. **Earnings Ledger Architecture** - Designed a three-table schema (`bot_earnings_ledger`, `bot_attribution_entries`, `bot_payout_requests`) that provides:
   - Running balance tracking with atomic updates
   - Complete audit trail of individual attributions
   - Full payout request lifecycle management

2. **Integration with Ads Module** - Defined clear integration pattern with `ads.get_bot_ad_attributions()`:
   - Periodic sync mechanism pulls new attributions
   - Deduplication via unique `ad_impression_id` constraint
   - Error handling for ads service unavailability

3. **Payout Request Flow** - Designed owner-initiated, admin-processed payout system:
   - Minimum threshold ($10) to reduce overhead
   - Hold period (72 hours) for fraud review
   - Single pending payout per bot
   - Full audit trail with external references

4. **Fraud Prevention** - Built-in controls:
   - Ownership verification for all operations
   - Impression deduplication
   - Hold period for review
   - Admin manual approval required

---

## Alternatives Considered

### Alternative 1: Real-time Attribution Recording

**Considered:** Record earnings immediately when ads module records an impression, via event/callback.

**Rejected because:**
- Increases coupling between modules
- Requires event bus infrastructure not yet built
- Risk of data inconsistency if callback fails
- Adds complexity to ads module

**Chosen approach:** Periodic sync pulls data from ads module. Simpler, decoupled, and handles failures gracefully.

---

### Alternative 2: Partial Payouts

**Considered:** Allow bot owners to request specific amounts rather than full balance.

**Rejected because:**
- Complicates balance tracking (available vs. requested vs. reserved)
- Increases fraud surface (many small withdrawals)
- Adds UI/API complexity
- Not a user-stated requirement

**Chosen approach:** Full-balance payouts only. Simpler accounting, reduces fraud risk. Can add partial payouts later if needed.

---

### Alternative 3: Automated Payout Processing

**Considered:** Integrate Stripe Connect or PayPal directly for automated payouts.

**Rejected because:**
- Key Decision #8 explicitly defers automated payouts
- Requires significant third-party integration work
- Needs KYC/tax compliance considerations
- Manual review is preferred for initial fraud detection

**Chosen approach:** Track requests for manual fulfillment. Admin processes payouts externally and records reference. Clean separation allows future automation.

---

### Alternative 4: Shared Table with Ads Module

**Considered:** Store attribution data in ads module's tables, bot_earnings only reads.

**Rejected because:**
- Violates single ownership principle
- Bot earnings needs to track earnings balance, paid amounts
- Different lifecycle (earnings persist after ad data may be pruned)
- Audit requirements differ

**Chosen approach:** Bot earnings owns its tables, copies relevant data during sync. Clear ownership boundaries.

---

### Alternative 5: On-Demand Calculation

**Considered:** Calculate balance by summing all attributions on each request.

**Rejected because:**
- Performance degrades as attribution count grows
- Complex queries for available balance (sum minus payouts)
- No atomic balance operations

**Chosen approach:** Maintain running ledger balance with atomic increments. O(1) balance lookups, guaranteed consistency.

---

## Risks

### Risk 1: Attribution Volume Growth (Medium)

**Description:** As bot population grows, attribution_entries table could become very large.

**Mitigation:**
- Indexed on `(bot_player_id, attribution_date)` for efficient queries
- Daily summary table reduces need to query individual entries
- Can implement archival policy (move old entries to cold storage) if needed

---

### Risk 2: Ads Module API Changes (Low)

**Description:** Changes to `get_bot_ad_attributions()` return format could break sync.

**Mitigation:**
- Interface is defined via Protocol in ads module artifact
- Sync catches and logs errors rather than crashing
- Can add versioning/compatibility layer if needed

---

### Risk 3: Fraud via Attribution Gaming (Medium)

**Description:** Malicious actors could attempt to inflate bot earnings through coordinated ad viewing.

**Mitigation:**
- 72-hour hold period allows manual review
- Admin approval required for all payouts
- Impression deduplication prevents double-counting
- Attribution tied to actual match completion
- Future: Add velocity checks, pattern detection

---

### Risk 4: Currency/Tax Compliance (Low for Initial Scope)

**Description:** Tracking earnings in cents may need country-specific handling.

**Mitigation:**
- Initial scope is tracking only, not payment
- All amounts stored in integer cents (no floating point)
- Manual payouts allow case-by-case compliance
- Future: Add currency conversion, tax forms when automating

---

### Risk 5: Bot Owner Identification (Low)

**Description:** Determining who "owns" a bot for payout authorization.

**Mitigation:**
- `owner_player_id` stored in ledger at creation
- Linked to whoever created the bot account
- Admin can manually update if needed
- Future: Add formal ownership transfer process

---

## Dependencies & Sequencing Notes

### Build Order

- **Build Wave:** 8 (parallel with `payments`)
- **Must wait for:** `ads` module (Wave 7) to be complete
- **Can build in parallel with:** `payments` module

### Dependency Artifacts Verified

1. **ads module artifact** (v1.0)
   - Confirmed `get_bot_ad_attributions(bot_player_id, start_date, end_date)` interface
   - Returns `BotAdAttributionReport` with `daily_breakdown`, `attributed_revenue_cents`
   - Error handling: ads module raises errors through error service

2. **player module artifact** (v1.0)
   - Confirmed `Player.is_bot` property for bot verification
   - `get_player(player_id)` raises `NOT_FOUND_PLAYER` if not found
   - No bot ownership tracking in player module (stored in bot_earnings ledger)

### Interface Contracts Used

- Error codes from interface-contracts.md v1.1
- Repository Pattern from data-layer.md v1.0
- Async patterns from best-practices.md v1.0

### New Error Types Required

The following error types need to be added to `interface-contracts.md`:

| Code | Message Template | Context Fields | When to Use |
|------|------------------|----------------|-------------|
| `VALIDATION_INSUFFICIENT_BALANCE` | `"Insufficient earnings balance"` | `available_cents`, `requested_cents` | Payout amount exceeds available |
| `VALIDATION_BELOW_PAYOUT_THRESHOLD` | `"Balance below minimum payout threshold"` | `available_cents`, `minimum_cents` | Balance < minimum for payout |
| `VALIDATION_DATE_RANGE_TOO_LARGE` | `"Date range exceeds maximum"` | `days_requested`, `max_days` | Query date range too wide |
| `FORBIDDEN_NOT_BOT_OWNER` | `"Not authorized for this bot"` | `bot_player_id`, `requester_id` | Non-owner requesting payout |
| `CONFLICT_PENDING_PAYOUT_EXISTS` | `"Pending payout request exists"` | `bot_player_id`, `existing_request_id` | Second payout while one pending |
| `CONFLICT_PAYOUT_NOT_PENDING` | `"Payout request not in pending status"` | `payout_request_id`, `current_status` | Process/cancel non-pending |
| `CONFLICT_SYNC_IN_PROGRESS` | `"Attribution sync already in progress"` | `bot_player_id`, `started_at` | Concurrent sync attempts |
| `NOT_FOUND_PAYOUT_REQUEST` | `"Payout request not found"` | `payout_request_id` | Invalid payout request ID |
| `INTERNAL_ADS_SERVICE_ERROR` | `"Ads service error"` | `operation`, `error` | Ads module call failed |

**Escalation:** These error types should be added to `interface-contracts.md` by the Orchestrator.

### New Config Keys Required

The following config keys need to be added to `configuration.md`:

| Key | Type | Default | Description |
|-----|------|---------|-------------|
| `bot_earnings.minimum_payout_cents` | int | 1000 | Minimum balance to request payout |
| `bot_earnings.attribution_share_percent` | float | 30.0 | Bot share of impression revenue |
| `bot_earnings.sync_lookback_days` | int | 7 | Days to look back during sync |
| `bot_earnings.max_date_range_days` | int | 90 | Max days for date range queries |
| `bot_earnings.payout_hold_hours` | int | 72 | Hours to hold new payouts |
| `bot_earnings.sync_batch_size` | int | 100 | Bots per batch in bulk sync |

**Escalation:** These config keys should be added to `configuration.md` by the Orchestrator.

### Data Ownership Summary

| Table | Owner | Read By |
|-------|-------|---------|
| `bot_earnings_ledger` | bot_earnings | api |
| `bot_attribution_entries` | bot_earnings | api |
| `bot_payout_requests` | bot_earnings | api |
| `bot_earnings_daily` | bot_earnings | api |
| `ad_impressions` | ads | bot_earnings (via ads service) |
| `players` | player | bot_earnings (via player service) |

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-05 | 1.0 | Initial report | Scout Agent (bot_earnings) |
