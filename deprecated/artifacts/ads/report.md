# Module Report: ads

## Header
- **Author:** Scout Agent (ads)
- **Date:** 2026-02-05

---

## Summary

The **ads** module has been designed to handle all advertisement integration for ChromaCrush, supporting the primary monetization mechanism for free-tier players. Key design outcomes:

1. **Three Ad Types Supported:** Interstitial (between matches), rewarded video (opt-in for rewards), and banner (passive display)

2. **Ad-Free Status Management:** Full lifecycle support for granting, checking, and revoking ad-free status, with support for permanent (purchase) and time-limited (promotion) ad-free

3. **Bot Revenue Attribution:** Comprehensive system for tracking which ad impressions were influenced by bot matches, enabling the bot_earnings module to calculate revenue sharing

4. **Event Integration:** Special ad opportunities during events, allowing players to watch ads for bonus event points or other rewards

5. **Third-Party SDK Abstraction:** Ad provider logic is abstracted behind a `Protocol` interface, allowing for mock testing and future provider switching without module changes

6. **Cooldown System:** Rate limiting on interstitial and rewarded ads to prevent spam while maintaining monetization

---

## Alternatives Considered

### 1. Revenue Attribution Model

**Options:**
- (A) Direct match attribution only (ad triggered immediately after match)
- (B) Session-based attribution (any ad within N minutes of match)
- (C) Weighted multi-match attribution

**Chosen:** Option A - Direct match attribution only

**Rationale:** Simplest to implement and explain. Clear causality chain. Session-based would require tracking player sessions. Multi-match attribution adds complexity without clear benefit. Bot owners will understand "your bot played against a human, they saw an ad, you get 30%."

---

### 2. Ad Provider Integration Pattern

**Options:**
- (A) Direct SDK integration in service
- (B) Abstract `Protocol` interface with provider implementations
- (C) Event-driven (emit "ad needed" events, separate handler)

**Chosen:** Option B - Protocol interface abstraction

**Rationale:** Enables mock provider for testing without external dependencies. Allows switching providers (Google, Unity, etc.) without touching business logic. Clean dependency injection per framework patterns.

---

### 3. Banner Impression Tracking

**Options:**
- (A) Track all banner displays regardless of duration
- (B) Track only banners above minimum view threshold
- (C) No banner tracking (only interstitial/rewarded)

**Chosen:** Option B - Minimum view threshold

**Rationale:** Sub-second banner views aren't meaningful impressions. 1-second minimum is standard industry practice. Prevents impression inflation from rapid navigation.

---

### 4. Event Ad Opportunity Structure

**Options:**
- (A) Events module owns all opportunity logic
- (B) Ads module owns all opportunity logic
- (C) Split: events defines opportunities, ads handles execution

**Chosen:** Option C - Split responsibility

**Rationale:** Events module knows what rewards make sense for its context. Ads module knows how to request, record, and verify ad completion. Natural separation of concerns per module ownership rules.

---

### 5. Ad-Free Status Storage

**Options:**
- (A) Boolean flag on player record
- (B) Separate ad_free_status table
- (C) Redis cache only

**Chosen:** Option B - Separate table

**Rationale:** Allows tracking history (granted_at, granted_by, reason). Supports time-limited ad-free with expiration. Clean separation from player module's data ownership.

---

## Risks

### R1: Ad Provider SDK Stability (Medium)

**Risk:** Third-party ad SDKs may have outages, rate limits, or breaking changes.

**Mitigation:** Protocol abstraction allows graceful degradation. Timeout handling prevents blocking user flows. Mock provider for testing. Logging captures provider errors for monitoring.

---

### R2: Revenue Estimation Accuracy (Low)

**Risk:** Estimated revenue may not match actual payments from ad providers.

**Mitigation:** Clear labeling of estimates. Documentation that bot earnings are based on estimates. Actual reconciliation is a finance concern outside this module's scope.

---

### R3: Bot Attribution Gaming (Medium)

**Risk:** Bad actors could create bot farms to accumulate ad attribution.

**Mitigation:** Attribution requires human player to see ad (bots don't watch ads). Rate limits on matchmaking prevent spam. ELO system naturally separates active bots from farm bots. Admin tools can revoke earnings.

---

### R4: Cooldown Bypass Attempts (Low)

**Risk:** Clients might try to bypass cooldowns by manipulating requests.

**Mitigation:** All cooldown logic is server-side. Cooldown uses `created_at` timestamp from database, not client time. Request expiration prevents replay.

---

### R5: Privacy Concerns with Ad Tracking (Low)

**Risk:** Detailed ad impression tracking could raise privacy concerns.

**Mitigation:** Ad data is per-player, not cross-player. No PII in ad impressions. Players can request data deletion per GDPR (soft-delete preserves ad-free status). Presentation layer filters what data is exposed.

---

## Dependencies & Sequencing Notes

### Confirmed Dependencies

| Dependency | Artifact Status | Interface Used |
|------------|-----------------|----------------|
| `player` (Wave 1) | Complete | `PlayerServiceProtocol.get_player()`, `Player.is_bot` |
| `events` (Wave 6) | Complete | `EventServiceProtocol.get_event()`, `EventServiceProtocol.get_event_participant()` |

### Dependents

| Dependent | Build Wave | Interface Provided |
|-----------|------------|-------------------|
| `payments` (Wave 8) | Blocked on this | `grant_ad_free_status()` for purchase completion |
| `bot_earnings` (Wave 8) | Blocked on this | `get_bot_ad_attributions()`, `get_match_ad_attribution()` |

### Build Order Notes

1. **Wave 7 (this module):** Can begin immediately after events (Wave 6) artifact is complete
2. **Parallel with nothing:** This is a single-module wave
3. **Blocks Wave 8:** Both `payments` and `bot_earnings` depend on this module's interface

### Integration Points

1. **With payments module:** Payments calls `grant_ad_free_status()` when $1 purchase completes
2. **With bot_earnings module:** Bot earnings calls `get_bot_ad_attributions()` to calculate revenue share
3. **With events module:** Events can define ad opportunities; ads module executes them
4. **With energy module (future):** Rewarded ad completion should call `energy_service.grant_bonus_hearts()` - requires energy module Protocol to be defined

### Open Integration Questions

None. The interfaces between this module and its dependents are fully specified:
- `payments` will call `grant_ad_free_status(player_id, AdFreeReason.PURCHASE)`
- `bot_earnings` will call `get_bot_ad_attributions(bot_player_id, start_date, end_date)`

---

## Escalations

None required. All edge cases have been resolved within existing error taxonomy and guidance documents.

---

## Artifact Checklist

- [x] Public interface defined (Protocol)
- [x] All inputs documented with validation rules
- [x] All outputs documented with data structures
- [x] Error cases mapped to error taxonomy
- [x] Async behavior specified
- [x] Configuration keys defined
- [x] Logging events specified
- [x] Data ownership defined (6 tables)
- [x] Repository interfaces defined
- [x] Cross-module data access documented
- [x] Transaction requirements specified
- [x] Presentation boundary defined
- [x] Internal design documented
- [x] CLI surface defined
- [x] Edge cases resolved
- [x] No open questions

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-05 | 1.0 | Initial report | Scout Agent (ads) |
