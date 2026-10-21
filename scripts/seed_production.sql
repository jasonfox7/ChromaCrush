-- seed_production.sql
-- Optional local seed: a guest player, a single-player bot, and gold products.
-- The hosted database this script originally targeted has been deleted.
--
-- Generate a bcrypt hash before running, and paste it over the placeholders:
--   python -c "import bcrypt; print(bcrypt.hashpw(b'choose-a-password', bcrypt.gensalt()).decode())"
--
--   psql -U chromacrush -d chromacrush -h localhost -f scripts/seed_production.sql

BEGIN;

-- ============================================================
-- 1. Guest player (human)
-- ============================================================
INSERT INTO players (id, username, username_lower, player_type, elo_rating, password_hash, created_at, updated_at)
VALUES (
  'a10b8389-4c7f-4d37-8cd5-bf8ce4aaa7e7',
  'chromacrush_guest',
  'chromacrush_guest',
  'human',
  1000,
  -- bcrypt hash of the guest password; generate one (see header)
  '<REPLACE_WITH_BCRYPT_HASH>',
  NOW(), NOW()
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO player_stats (player_id, total_matches, wins, losses, draws, highest_score, longest_chain, total_gems_matched, created_at, updated_at)
VALUES (
  'a10b8389-4c7f-4d37-8cd5-bf8ce4aaa7e7',
  0, 0, 0, 0, 0, 0, 0,
  NOW(), NOW()
)
ON CONFLICT (player_id) DO NOTHING;

INSERT INTO energy_states (player_id, hearts, max_hearts, last_regen_at, daily_streak, created_at, updated_at)
VALUES (
  'a10b8389-4c7f-4d37-8cd5-bf8ce4aaa7e7',
  5, 5, NOW(), 0,
  NOW(), NOW()
)
ON CONFLICT (player_id) DO NOTHING;

INSERT INTO gold_balances (player_id, balance, lifetime_earned, lifetime_spent, created_at, updated_at)
VALUES (
  'a10b8389-4c7f-4d37-8cd5-bf8ce4aaa7e7',
  0, 0, 0,
  NOW(), NOW()
)
ON CONFLICT (player_id) DO NOTHING;

-- ============================================================
-- 2. Single-player bot
-- ============================================================
INSERT INTO players (id, username, username_lower, player_type, elo_rating, created_at, updated_at)
VALUES (
  'ce898c27-cfc0-4521-9b27-ba5254292f60',
  'chromacrush_sp_bot',
  'chromacrush_sp_bot',
  'bot',
  1000,
  NOW(), NOW()
)
ON CONFLICT (id) DO NOTHING;

INSERT INTO player_stats (player_id, total_matches, wins, losses, draws, highest_score, longest_chain, total_gems_matched, created_at, updated_at)
VALUES (
  'ce898c27-cfc0-4521-9b27-ba5254292f60',
  0, 0, 0, 0, 0, 0, 0,
  NOW(), NOW()
)
ON CONFLICT (player_id) DO NOTHING;

INSERT INTO energy_states (player_id, hearts, max_hearts, last_regen_at, daily_streak, created_at, updated_at)
VALUES (
  'ce898c27-cfc0-4521-9b27-ba5254292f60',
  5, 5, NOW(), 0,
  NOW(), NOW()
)
ON CONFLICT (player_id) DO NOTHING;

-- ============================================================
-- 3. IAP products (gold packs)
-- ============================================================
INSERT INTO products (id, name, description, price_cents, currency, product_type, is_active) VALUES
  ('chromacrush_gold_1500',  'Pocket of Gold',  '1,500 Gold',  49,   'USD', 'one_time', true),
  ('chromacrush_gold_3000',  'Trader''s Pouch', '3,000 Gold',  99,   'USD', 'one_time', true),
  ('chromacrush_gold_15000', 'Sack of Gold',    '15,000 Gold', 499,  'USD', 'one_time', true),
  ('chromacrush_gold_35000', 'Chest of Gold',   '35,000 Gold', 999,  'USD', 'one_time', true),
  ('chromacrush_gold_80000', 'Vault of Gold',   '80,000 Gold', 1799, 'USD', 'one_time', true)
ON CONFLICT (id) DO NOTHING;

-- ============================================================
-- 4. Bot API key
-- ============================================================
-- key_hash is the bcrypt hash of a bot API key you generate locally.
-- key_prefix is the first 11 characters of that key (the "cc_" prefix plus 8 more).
INSERT INTO api_keys (id, player_id, key_hash, key_prefix, description, created_at, updated_at)
VALUES (
  'b5ca3b42-b67d-4d98-96e7-7ddde23e6711',
  'ce898c27-cfc0-4521-9b27-ba5254292f60',
  '<REPLACE_WITH_BCRYPT_HASH>',
  'cc_example0',
  'Single-player bot API key',
  NOW(), NOW()
)
ON CONFLICT (id) DO NOTHING;

COMMIT;

-- Verify
SELECT 'Players:' AS info, count(*) FROM players;
SELECT 'API Keys:' AS info, count(*) FROM api_keys;
SELECT 'Energy States:' AS info, count(*) FROM energy_states;
SELECT 'Player Stats:' AS info, count(*) FROM player_stats;
SELECT 'Products:' AS info, count(*) FROM products;
