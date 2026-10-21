# Module Report: vault

> **Author:** Scout Agent
> **Date:** 2026-02-05
> **Module:** vault
> **Build Wave:** 3

---

## Summary

The vault module has been designed to manage ChromaCrush's artifact collection and raid system. Key outcomes:

1. **Complete Artifact Lifecycle** — Full CRUD operations for artifact instances, including acquisition from multiple sources (match rewards, events, raids, purchases) and transfer between players.

2. **Raid System** — Implemented a balanced raid mechanic with:
   - Per-attacker-defender cooldowns (24 hours default)
   - Energy cost to prevent spam
   - Weighted random artifact selection favoring common items
   - Shield protection system

3. **Shield Mechanics** — 8-hour default protection with single active shield constraint. Shields cannot be stacked, preventing indefinite protection.

4. **Collection Tracking** — Progress tracking for artifact sets with completion detection. Actual bonus granting delegated to the events module.

5. **Audit Trail** — Complete raid history logging for analytics, cooldown enforcement, and player dispute resolution.

---

## Alternatives Considered

### 1. Artifact Ownership Model

**Considered:** Shared artifact instances (one artifact record, multiple owners with quantity tracking)

**Rejected because:**
- Increases complexity for transfer operations
- Makes "this specific artifact was stolen in this raid" tracking difficult
- ChromaCrush artifacts are meant to feel unique and personal

**Chosen:** One artifact instance per player. Each acquisition creates a new record with its own provenance.

---

### 2. Raid Target Selection

**Considered:** Allow raiders to choose which artifact to steal

**Rejected because:**
- Removes suspense and excitement from raids
- Would let players always target legendaries
- Reduces defender's sense of "any artifact could go"

**Chosen:** Weighted random selection where common items are 4x more likely to be selected than legendary. Raiders know they're targeting a vault, not a specific item.

---

### 3. Shield Duration Model

**Considered:** Consumable shield items with varying durations

**Rejected because:**
- Adds inventory management complexity
- Creates potential pay-to-win concerns
- Not specified in GDD scope

**Chosen:** Single configurable duration (8 hours default). Future iteration could add shield sources (match rewards, purchases) without changing the core mechanic.

---

### 4. Cooldown Scope

**Considered:** Global cooldown (player can only raid once per N hours total)

**Rejected because:**
- Too restrictive for active players
- Reduces engagement with raid system
- Doesn't address targeting (same victim repeatedly)

**Chosen:** Per attacker-defender pair cooldown. Player A can raid different players freely, but must wait 24 hours before raiding the same victim again.

---

### 5. Artifact Catalog Storage

**Considered:** Static configuration file (YAML/JSON)

**Rejected because:**
- Requires deployment to add new artifacts
- No admin interface for content management
- Harder to version/migrate

**Chosen:** Database table (`artifact_definitions`). Seed data provides initial catalog; admin tools can add/modify artifacts without code deployment.

---

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Raid griefing (targeting new players) | Medium | High | `empty_vault_protection` config flag; new players get automatic shield after first artifact |
| Legendary inflation (too easy to acquire) | Low | Medium | Weighted selection + success chance modifier ensures legendaries remain rare |
| Shield abuse (never raidable) | Low | Medium | Single shield, fixed duration, no stacking. Players must choose when to use protection. |
| Concurrent raid race conditions | Low | Medium | PostgreSQL transaction isolation; worst case is both raiders fail |
| Large vault performance | Low | Low | Pagination on list operations; max artifact limit config |
| Player frustration from losses | Medium | High | Shield system, cooldowns, and future "revenge raid" mechanics provide counterplay |

---

## Dependencies & Sequencing Notes

### Module Dependencies

| Dependency | Type | Interface Required | Status |
|------------|------|-------------------|--------|
| `player` | Direct | `PlayerServiceProtocol.get_player()` | Artifact available |
| `energy` | Indirect (via player) | Energy consumption for raid cost | Artifact available |

### Build Order

The vault module is **Wave 3** in the dependency graph:

```
Wave 1: board, player    (no dependencies)
Wave 2: scoring, auth, energy
Wave 3: special_gems, vault   <-- This module
Wave 4: board_gen
Wave 5: match
...
```

### Pre-Implementation Requirements

Before vault implementation begins:
1. `src/core/` services must be complete (config, logger, errors, data_context)
2. `src/data/` repository infrastructure must be in place
3. `player` module must be implemented (vault reads player data)
4. `energy` module must be implemented (raid costs energy)

### Coordination Notes

1. **Events Module** — Will consume `VaultServiceProtocol` to:
   - Grant artifacts as event rewards
   - Check collection completeness for set bonuses
   - Events module is Wave 6; no blocking dependency

2. **Match Module** — Will consume `VaultServiceProtocol` to:
   - Grant artifacts as match rewards (post-match flow)
   - Match module is Wave 5; no blocking dependency

3. **API Module** — Will expose vault endpoints:
   - List player artifacts
   - Get vault summary
   - Attempt raid
   - Shield management
   - API module is Wave 9; no blocking dependency

### Database Migration Ordering

Vault migrations must run after:
1. `players` table exists (FK reference)

Vault migrations create:
1. `vault_artifacts` table
2. `vault_shields` table
3. `artifact_definitions` table
4. `raid_logs` table
5. Seed data for initial artifact catalog

---

## Testing Considerations

### Key Test Scenarios

1. **Artifact Acquisition** — Test all source types (match, event, raid, purchase)
2. **Raid Success/Failure** — Mock RNG for deterministic testing
3. **Shield Blocking** — Verify raids fail against shielded players
4. **Cooldown Enforcement** — Test time-based cooldown logic
5. **Collection Progress** — Test partial and complete set detection
6. **Transaction Atomicity** — Verify raid transfers are atomic
7. **Edge Cases** — Empty vault, self-raid, concurrent raids

### Mocking Requirements

- `PlayerServiceProtocol` — Mock player existence checks
- `RNG` — Inject seeded random for raid outcome testing
- `DataContext` — Standard test session with rollback
- `datetime.utcnow()` — Mock for cooldown/shield expiry testing

---

## Future Considerations

Not in current scope, but the design accommodates:

1. **Artifact Trading** — `transfer_artifact` method supports trade use case
2. **Artifact Upgrading** — Could add upgrade mechanics via new methods
3. **Raid Revenge** — History tracking enables "raid back" features
4. **Shield Sources** — Shield activation could track source for analytics
5. **Collection Rewards** — Events module can query collections for bonus grants
6. **Artifact Destruction** — `remove_artifact` supports future destruction mechanics

---

## Checklist

- [x] Public interface defined with full type annotations
- [x] All error cases documented with taxonomy codes
- [x] Config keys listed with types and defaults
- [x] Logging events documented with severity and context
- [x] Repository interfaces defined as Protocols
- [x] Transaction boundaries specified
- [x] Async behavior documented (all methods async)
- [x] CLI commands specified for testing
- [x] Edge cases documented with handling
- [x] Dependencies identified (player, energy via player)
- [x] No implementation code written (design only)
- [x] Presentation boundary respected (returns domain objects only)

---

*End of vault module report.*
