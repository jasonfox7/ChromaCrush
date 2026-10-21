# Database Reference

## Connection

PostgreSQL and Redis run in Docker containers.

```bash
# Containers
docker ps  # chromacrush-postgres, chromacrush-redis

# Interactive psql shell
docker exec -it chromacrush-postgres psql -U chromacrush -d chromacrush

# One-off query
docker exec chromacrush-postgres psql -U chromacrush -d chromacrush -c "SELECT ..."
```

Connection string: `chromacrush:chromacrush_dev@localhost:5432/chromacrush`

That password is the local Docker Compose default from `.env.example`. It is not a hosted credential.

## Migrations (Alembic)

Migrations live in `src/data/migrations/versions/`. Run from the **repo root** (where `alembic.ini` is).

```bash
# Check current version
docker exec chromacrush-postgres psql -U chromacrush -d chromacrush -c "SELECT version_num FROM alembic_version;"

# List heads (there may be multiple branches)
cd <repo-root>
python -m alembic heads

# Upgrade to a specific revision
python -m alembic upgrade 010

# NOTE: If multiple heads exist, you must specify a target revision
# instead of using "head". Use "heads" for all branches.
```

## Common Operations

### Reset bot energy (hearts)
```sql
UPDATE energy_states SET hearts = max_hearts
WHERE player_id = (SELECT id FROM players WHERE username = 'chromacrush_sp_bot');
```

### List all tables
```sql
\dt
```

### Inspect a table schema
```sql
\d player_cards
```

### Find foreign keys pointing at a table
```sql
SELECT tc.table_name, kcu.column_name
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY' AND ccu.table_name = 'players';
```

### Seed cards for the guest player
Cards reference definition IDs from `config/card_definitions.json` (15 cards across 3 sets). The `player_cards` table has a unique constraint on `(player_id, position)` so positions must be sequential.

```sql
INSERT INTO player_cards (player_id, card_id, position, source)
VALUES
  ((SELECT id FROM players WHERE username = 'chromacrush_guest'), 1, 1, 'seed'),
  ((SELECT id FROM players WHERE username = 'chromacrush_guest'), 2, 2, 'seed');
```

### Delete a player and all related data
The `players` table has **38 foreign key references** (NO CASCADE). You must delete from all child tables first. Use a temp table to collect IDs:

```sql
BEGIN;
CREATE TEMP TABLE target_ids AS SELECT id FROM players WHERE username LIKE 'some_pattern%';

DELETE FROM match_moves WHERE player_id IN (SELECT id FROM target_ids);
DELETE FROM matches WHERE player1_id IN (SELECT id FROM target_ids) OR player2_id IN (SELECT id FROM target_ids) OR winner_id IN (SELECT id FROM target_ids) OR forfeit_by IN (SELECT id FROM target_ids);
DELETE FROM sessions WHERE player_id IN (SELECT id FROM target_ids);
DELETE FROM api_keys WHERE player_id IN (SELECT id FROM target_ids);
DELETE FROM energy_states WHERE player_id IN (SELECT id FROM target_ids);
DELETE FROM player_stats WHERE player_id IN (SELECT id FROM target_ids);
DELETE FROM player_cards WHERE player_id IN (SELECT id FROM target_ids);
DELETE FROM vault_artifacts WHERE owner_id IN (SELECT id FROM target_ids);
DELETE FROM vault_shields WHERE player_id IN (SELECT id FROM target_ids);
DELETE FROM raid_logs WHERE attacker_id IN (SELECT id FROM target_ids) OR defender_id IN (SELECT id FROM target_ids);
DELETE FROM events WHERE created_by IN (SELECT id FROM target_ids);
DELETE FROM event_participants WHERE player_id IN (SELECT id FROM target_ids);
DELETE FROM event_matches WHERE player_id IN (SELECT id FROM target_ids);
DELETE FROM event_ad_claims WHERE player_id IN (SELECT id FROM target_ids);
DELETE FROM ad_rewards_granted WHERE player_id IN (SELECT id FROM target_ids);
DELETE FROM ad_impressions WHERE player_id IN (SELECT id FROM target_ids);
DELETE FROM ad_requests WHERE player_id IN (SELECT id FROM target_ids);
DELETE FROM ad_free_status WHERE player_id IN (SELECT id FROM target_ids) OR granted_by IN (SELECT id FROM target_ids);
DELETE FROM receipt_validations WHERE player_id IN (SELECT id FROM target_ids);
DELETE FROM purchases WHERE player_id IN (SELECT id FROM target_ids);
DELETE FROM purchase_intents WHERE player_id IN (SELECT id FROM target_ids);
DELETE FROM bot_earnings_daily WHERE bot_player_id IN (SELECT id FROM target_ids);
DELETE FROM bot_payout_requests WHERE bot_player_id IN (SELECT id FROM target_ids) OR owner_player_id IN (SELECT id FROM target_ids) OR processed_by IN (SELECT id FROM target_ids);
DELETE FROM bot_attribution_entries WHERE bot_player_id IN (SELECT id FROM target_ids) OR opponent_player_id IN (SELECT id FROM target_ids);
DELETE FROM bot_earnings_ledger WHERE bot_player_id IN (SELECT id FROM target_ids) OR owner_player_id IN (SELECT id FROM target_ids);
DELETE FROM campaign_attempts WHERE player_id IN (SELECT id FROM target_ids);
DELETE FROM gold_transactions WHERE player_id IN (SELECT id FROM target_ids);
DELETE FROM gold_balances WHERE player_id IN (SELECT id FROM target_ids);
DELETE FROM mega_gem_inventory WHERE player_id IN (SELECT id FROM target_ids);
-- Finally:
DELETE FROM players WHERE id IN (SELECT id FROM target_ids);

DROP TABLE target_ids;
COMMIT;
```

## Table Overview

Core tables with player foreign keys:

| Table | Key Columns | Notes |
|-------|-------------|-------|
| `players` | `id`, `username`, `player_type`, `campaign_level` | `human` or `bot`. `campaign_level` (default 1) tracks single-player progress |
| `player_stats` | `player_id` | Wins, losses, elo history |
| `energy_states` | `player_id`, `hearts`, `max_hearts` | Hearts system |
| `sessions` | `player_id` | JWT sessions |
| `api_keys` | `player_id` | Bot X-API-Key auth |
| `matches` | `player1_id`, `player2_id`, `winner_id` | Match records |
| `match_moves` | `player_id`, `match_id` | Individual moves |
| `player_cards` | `player_id`, `card_id`, `position` | Card collection (card_id refs `card_definitions.json`) |
| `vault_artifacts` | `owner_id` | Vault items |
| `vault_shields` | `player_id` | Vault defense |
| `gold_balances` | `player_id`, `balance` | Player gold balance |
| `gold_transactions` | `player_id`, `amount`, `reason` | Gold transaction ledger |
| `mega_gem_inventory` | `player_id` | Mega gem stock |
| `campaign_attempts` | `player_id`, `level_number`, `status` | Campaign level attempts (in_progress/won/lost/abandoned) |
