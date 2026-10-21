# Module Report: payments

## Header
- **Author:** Scout Agent (payments)
- **Date:** 2026-02-05

---

## Summary

The payments module artifact has been designed to handle ChromaCrush's single monetization purchase: a $1 one-time payment to permanently remove ads.

### Key Outcomes

1. **Minimal Scope** - Module handles exactly one product (ad-free tier), with no subscriptions, consumables, or other IAP complexity
2. **Server-Side Validation** - All receipt validation happens server-side for security; client handles payment UI via app store SDKs
3. **Provider Abstraction** - Payment provider (Apple/Google) abstracted behind Protocol for testability and future expansion
4. **Idempotent Design** - Duplicate receipt handling via hash-based detection and unique constraints
5. **Full Audit Trail** - All purchase attempts, validations, and refunds stored for compliance and debugging
6. **Refund Handling** - Webhook-based refund processing automatically revokes ad-free status

### Integration Points Designed

- **ads module** - Calls `grant_ad_free_status()` on successful purchase, `revoke_ad_free_status()` on refund
- **player module** - Validates player existence before any purchase operation

---

## Alternatives Considered

### Alt-1: Client-Side Validation Only

**Considered:** Trust client-reported purchase status without server validation.

**Rejected:** Security risk. Easy to spoof purchase confirmation. Industry standard is server-side receipt validation.

### Alt-2: Unified Payment Provider Interface

**Considered:** Single provider interface that handles both Apple and Google identically.

**Chosen:** Provider-specific implementations behind a common Protocol. While Apple and Google have different APIs (verifyReceipt vs. Google Play Developer API), the Protocol abstraction allows testing with mocks while real implementations handle provider differences.

### Alt-3: Store Receipt Data Externally

**Considered:** Not storing receipt data in our database, only validation results.

**Rejected:** Receipt storage is needed for:
- Audit trail and compliance
- Support investigations
- Re-validation if needed
- Duplicate detection

### Alt-4: Eager Ad-Free Check (Pre-Validation)

**Considered:** Grant ad-free immediately on purchase initiation, revoke if validation fails.

**Rejected:** Creates window for exploitation. Standard pattern is validate-then-grant.

---

## Risks

### R-1: Payment Provider API Changes

**Risk:** Apple or Google change their receipt validation API format/endpoints.

**Likelihood:** Low (breaking changes are rare and well-announced)

**Mitigation:** Provider implementations are isolated behind Protocol. Changes affect only the specific provider implementation, not the rest of the module.

### R-2: Refund Webhook Delays

**Risk:** Payment provider webhook arrives late or not at all, leaving player with ad-free after refund.

**Likelihood:** Medium (webhooks can be delayed by hours in rare cases)

**Mitigation:**
- Store all refund notifications for manual review
- Consider periodic reconciliation job (not in initial scope)
- Support tools can manually revoke if needed

### R-3: Receipt Validation Cost at Scale

**Risk:** Each validation requires external API call, adding latency.

**Likelihood:** Low (one-time purchases, not frequent operations)

**Mitigation:**
- Async processing doesn't block user
- Purchase is one-time, so validation only happens once per user lifetime

### R-4: Fraud via Stolen Receipts

**Risk:** Attacker uses stolen receipt to grant ad-free to different account.

**Likelihood:** Low (Apple/Google receipts are tied to app store accounts)

**Mitigation:**
- Receipt hash prevents same receipt being used twice
- Provider validation verifies receipt authenticity
- Transaction ID uniqueness constraint

---

## Dependencies & Sequencing Notes

### Build Order Position

- **Wave:** 8
- **Depends on:** `player` (Wave 1), `ads` (Wave 7)
- **Depended on by:** None (terminal node)

### Implementation Sequence

1. `payments` can be implemented after `ads` module is complete
2. No other modules depend on payments, so it won't block anything
3. Should implement together with `bot_earnings` (also Wave 8) for efficient resource use

### Integration Requirements

Before payments module implementation:

1. **ads module must expose:**
   - `grant_ad_free_status(player_id, reason, duration_days=None)`
   - `revoke_ad_free_status(player_id, reason)`
   - `check_ad_free_status(player_id)`

2. **player module must expose:**
   - `get_player(player_id)` - to validate player exists

### Configuration Prerequisites

The following config keys need to be added to `docs/guidance/configuration.md`:

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `payments.ad_free_product_id` | str | Yes | Product ID for ad-free tier |
| `payments.ad_free_price_cents` | int | No | Default 100 |
| `payments.ad_free_currency` | str | No | Default USD |
| `payments.intent_expiry_minutes` | int | No | Default 30 |
| `payments.apple_bundle_id` | str | Yes | iOS bundle ID |
| `payments.apple_shared_secret` | str | Secret | App Store shared secret |
| `payments.apple_verify_url` | str | No | Default production URL |
| `payments.apple_sandbox_verify_url` | str | No | Default sandbox URL |
| `payments.google_package_name` | str | Yes | Android package name |
| `payments.google_service_account_key` | str | Secret | GCP service account JSON |
| `payments.webhook_apple_secret` | str | Secret | Apple webhook secret |
| `payments.webhook_google_secret` | str | Secret | Google webhook secret |
| `payments.allow_sandbox_purchases` | bool | No | Default false |

### Error Types to Add

The following error types should be added to `docs/guidance/interface-contracts.md`:

| Code | HTTP | Description |
|------|------|-------------|
| `NOT_FOUND_PRODUCT` | 404 | Product ID doesn't exist |
| `NOT_FOUND_PURCHASE` | 404 | Purchase record not found |
| `CONFLICT_RECEIPT_ALREADY_PROCESSED` | 409 | Duplicate receipt |
| `CONFLICT_PURCHASE_ALREADY_REFUNDED` | 409 | Already refunded |
| `CONFLICT_PLAYER_ALREADY_AD_FREE` | 409 | Player already has ad-free |
| `CONFLICT_PURCHASE_INTENT_EXPIRED` | 409 | Intent timed out |
| `VALIDATION_RECEIPT_INVALID` | 400 | Receipt validation failed |
| `VALIDATION_RECEIPT_WRONG_PRODUCT` | 400 | Receipt for different product |
| `VALIDATION_RECEIPT_WRONG_PLAYER` | 400 | Receipt tied to different user |
| `VALIDATION_INVALID_REFUND_NOTIFICATION` | 400 | Malformed refund data |
| `AUTH_INVALID_WEBHOOK_SIGNATURE` | 401 | Webhook signature failed |
| `INTERNAL_PAYMENT_PROVIDER_ERROR` | 500 | External API error |

---

## Escalations

### Escalation: New Config Keys Required

**Issue:** The payments module requires 14 new configuration keys not currently in `docs/guidance/configuration.md`.

**Request:** Orchestrator to add payments namespace config keys to configuration guidance.

**Details:** See "Configuration Prerequisites" section above for full list.

### Escalation: New Error Types Required

**Issue:** The payments module requires 12 new error codes not currently in `docs/guidance/interface-contracts.md`.

**Request:** Orchestrator to add payments error types to interface contracts guidance.

**Details:** See "Error Types to Add" section above for full list.

---

## Complexity Assessment

| Aspect | Complexity | Notes |
|--------|------------|-------|
| Business Logic | Low | Simple one-time purchase, no subscription management |
| External Integration | Medium | Apple and Google have different APIs |
| Data Model | Low | 5 tables, straightforward schema |
| Error Handling | Medium | Multiple failure modes to handle gracefully |
| Testing | Medium | Need mock provider for unit tests |
| Security | Medium | Receipt validation, webhook signatures |

**Overall Complexity:** Low-Medium

This is one of the simpler modules in the system due to the deliberately minimal scope (single $1 purchase). The main complexity comes from the two external payment provider integrations.

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-05 | 1.0 | Initial report | Scout Agent (payments) |
