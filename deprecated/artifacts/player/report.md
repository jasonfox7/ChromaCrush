# Player Module Report

> **Module:** player
> **Author:** Scout Agent
> **Date:** 2026-02-05
> **Version:** 1.0
> **Status:** Draft

---

## 1. Summary

The player module has been designed as a foundational Wave 1 module for ChromaCrush, managing all player account, profile, ELO rating, and statistics functionality. The module serves both human and bot players with appropriate validation and creation flows for each type.

### Key Design Highlights

1. **Clean Separation of Concerns**
   - Player module owns player data (accounts, stats, energy state records)
   - Energy business logic delegated to energy module (Wave 2)
   - Authentication delegated to auth module (Wave 2)

2. **GDPR-Compliant Soft Delete**
   - Players can request account deletion
   - Data retained with `deleted_at` timestamp for audit/recovery
   - Username released by appending deletion timestamp

3. **Case-Insensitive Username Handling**
   - `username_lower` column for fast case-insensitive lookups
   - Prevents user confusion from similar-looking usernames
   - Index on lowercase version for query performance

4. **Standard ELO Implementation**
   - Configurable K-factor (default 32)
   - Initial rating of 1000
   - Floor of 0 (no negative ratings)
   - Calculation method exposed for match module to orchestrate updates

5. **Energy State Data Ownership**
   - Player module owns the `energy_states` table
   - Energy module (Wave 2) provides business logic
   - Clean dependency ordering maintained

---

## 2. Alternatives Considered

### 2.1 Hard Delete vs Soft Delete

**Considered:** Hard delete (complete removal of player records)

**Rejected because:**
- Match history references would become orphaned or require cascade deletes
- No recovery path for accidental deletions
- GDPR "right to erasure" can be satisfied with soft delete + anonymization
- Soft delete allows audit trail for abuse prevention

**Chosen:** Soft delete with `deleted_at` timestamp and username release via suffix

---

### 2.2 Energy State Location

**Considered:** Energy state fully owned by energy module

**Rejected because:**
- Creates circular dependency: player needs energy for creation, energy needs player
- Energy module is Wave 2, player is Wave 1
- Data and business logic can be separated

**Chosen:** Player owns energy_states table (data layer), energy module owns business logic (regeneration, consumption rules)

---

### 2.3 Username Uniqueness Approach

**Considered:** Case-sensitive usernames (treat "User1" and "user1" as different)

**Rejected because:**
- User confusion ("I registered as User1, why can't I log in?")
- Potential for impersonation (user1 vs User1 vs USER1)
- Industry standard is case-insensitive

**Chosen:** Case-insensitive via `username_lower` column with unique constraint, preserving original casing for display

---

### 2.4 ELO Calculation Responsibility

**Considered:** ELO calculation in matchmaking module

**Rejected because:**
- Player module owns ELO data
- Match module orchestrates game flow and knows outcomes
- Matchmaking uses ELO for pairing but doesn't modify it

**Chosen:** Player module provides `calculate_elo_change` (pure calculation) and `update_elo` (persistence). Match module calls both after determining winner.

---

### 2.5 Stats Initialization Timing

**Considered:** Lazy initialization (create stats record on first match)

**Rejected because:**
- Requires null checks everywhere stats are accessed
- Race condition if two matches complete simultaneously for new player
- Complicates queries (left join vs inner join)

**Chosen:** Eager initialization (create stats record atomically with player in single transaction)

---

## 3. Risks

### 3.1 Username Collision After Soft Delete

**Risk:** Deleted username "alice" becomes "alice_deleted_1707123456789", new user creates "alice", deleted user reactivated creates naming conflict.

**Likelihood:** Low (reactivation is rare, would require manual intervention)

**Mitigation:**
- Reactivation process must check for conflicts before restoring original username
- Consider adding `original_username` field if reactivation becomes a feature

---

### 3.2 ELO Manipulation via Bot Farms

**Risk:** Bad actors create multiple bot accounts that intentionally lose to boost a main account's ELO.

**Likelihood:** Medium (common in competitive games)

**Mitigation (outside player module scope):**
- Matchmaking module should implement bot-vs-bot, human-vs-human, and mixed pools
- Rate limiting on player creation (auth module)
- Anomaly detection on win patterns (events module or external system)

---

### 3.3 Energy State Race Conditions

**Risk:** Concurrent requests to consume/regenerate energy could lead to inconsistent state.

**Likelihood:** Medium (mobile users may have poor connectivity, retry requests)

**Mitigation:**
- Repository layer uses `SELECT FOR UPDATE` on energy state modifications
- Energy module (Wave 2) should implement idempotent operations with timestamps
- Transaction isolation at service layer

---

### 3.4 Statistics Overflow

**Risk:** `total_gems_matched` is BIGINT but could theoretically overflow for extreme players.

**Likelihood:** Very Low (would require billions of matches)

**Mitigation:**
- BIGINT provides 9.2 quintillion max value
- Monitor in production; implement archival if ever needed

---

## 4. Dependencies & Sequencing Notes

### 4.1 Build Order Position

The player module is a **Wave 1 leaf node** with no module dependencies. It can be:
- Scouted in parallel with `board` module
- Implemented immediately after core services and data layer (Phase 2.0)
- Verified by Karen independently

### 4.2 Modules That Depend on Player

| Module | Dependency Type | Notes |
|--------|-----------------|-------|
| `auth` | Creates players, reads for authentication | Wave 2 |
| `energy` | Uses player's energy state data | Wave 2 |
| `match` | References players, updates ELO and stats | Wave 5 |
| `matchmaking` | Reads ELO for pairing | Wave 6 |
| `vault` | Associates artifacts with players | Wave 3 |
| `events` | Tracks player participation | Wave 6 |
| `ads` | Associates impressions with players | Wave 7 |
| `payments` | Associates purchases with players | Wave 8 |
| `bot_earnings` | Tracks earnings for bot players | Wave 8 |

### 4.3 Interface Stability

The `PlayerServiceProtocol` interface is designed to be stable. Dependent modules should rely on:
- `get_player` for reading player data
- `update_elo` for post-match rating changes
- `record_match_result` for statistics updates
- `get_energy_state` / `update_energy_state` for energy module

### 4.4 Migration Sequencing

The player module's migrations must run before any module that references `players(id)`:
1. `001_create_players_table.py`
2. `002_create_player_stats_table.py`
3. `003_create_energy_states_table.py`

Other modules' migrations can then create foreign keys to `players.id`.

---

## 5. Testing Priorities

### 5.1 Critical Path Tests (Unit)

1. **Username validation** - all format rules, edge cases
2. **ELO calculation** - various rating differentials, draws, K-factor variations
3. **Soft delete** - username release, query exclusion
4. **Stats aggregation** - win rate calculation, highest score tracking

### 5.2 Integration Tests

1. **Player creation atomic transaction** - player + stats + energy in single commit
2. **Username conflict detection** - case-insensitive collision
3. **Concurrent ELO updates** - no lost updates
4. **Pagination correctness** - limit, offset, total count

### 5.3 Edge Case Tests

1. Create bot with password (reject)
2. Create human without password (reject)
3. Update to own username (no-op success)
4. Get deleted player (not found)
5. Negative ELO (reject)
6. Hearts exceeding max (reject)

---

## 6. Implementation Estimates

| Component | Complexity | Estimated Effort |
|-----------|------------|------------------|
| PlayerService implementation | Low | 2-3 hours |
| Repository implementations | Low | 2 hours |
| ELO calculation helpers | Low | 1 hour |
| CLI commands | Low | 1-2 hours |
| Unit tests | Medium | 3-4 hours |
| Integration tests | Medium | 2-3 hours |
| **Total** | **Low** | **~12-15 hours** |

The player module is classified as **Low complexity** per the feasibility report. The design is straightforward CRUD with well-defined validation rules.

---

## Changelog

| Date | Version | Change | Author |
|------|---------|--------|--------|
| 2026-02-05 | 1.0 | Initial report | Scout Agent |
