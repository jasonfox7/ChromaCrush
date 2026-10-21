# Stage 4 — Compliance Fixes: matchmaking

**Date:** 2026-02-07

---

## P1-07: Inline `_PasswordStore` with raw data access in CLI

**Finding:** `src/cli/commands/matchmaking_commands.py:127-153` -- inline `_PasswordStore` class contained raw SQLAlchemy `select()`, `update()`, and `session.execute()` calls, violating the "no raw data access in CLI" rule.

**Fix:**
1. Created `src/data/repositories/password_store_repository.py` with `SQLAlchemyPasswordStoreRepository` class implementing the `PasswordStoreProtocol` interface. This is the proper repository layer for password hash read/write operations.
2. Removed the inline `_PasswordStore` class from `src/cli/commands/matchmaking_commands.py`.
3. Added import of `SQLAlchemyPasswordStoreRepository` and instantiated it in `_build_services()`.
4. Removed unused `from uuid import UUID` import (was only used by the deleted `_PasswordStore`).

**Files changed:**
- `src/data/repositories/password_store_repository.py` -- new file, proper repository implementation
- `src/cli/commands/matchmaking_commands.py` -- removed inline `_PasswordStore`, imported repository

**Note:** The same `_PasswordStore` inline pattern exists in `auth_commands.py`, `events_commands.py`, and `match_commands.py`. Those files are outside the scope of this assignment but could be updated to use the new shared repository in a future pass.

---

## P3-04: Magic numbers in service.py

**Finding:** Five magic number occurrences in `src/modules/matchmaking/service.py`.

**Fix:** Defined five module-level named constants after imports:

| Constant | Value | Location replaced |
|---|---|---|
| `_STATUS_OPPONENT_SEARCH_LIMIT` | 100 | `service.py` line 221 (`get_queue_status`) |
| `_MATCH_OPPONENT_SEARCH_LIMIT` | 10 | `service.py` lines 297, 375 (`find_match`, `process_queue`) |
| `_BASE_WAIT_ESTIMATE_SECONDS` | 30 | `service.py` line 641 (`_estimate_wait_time`) |
| `_WAIT_REDUCTION_FACTOR` | 5 | `service.py` line 642 (`_estimate_wait_time`) |
| `_MIN_WAIT_ESTIMATE_SECONDS` | 5 | `service.py` line 643 (`_estimate_wait_time`) |

**Files changed:**
- `src/modules/matchmaking/service.py` -- added 5 named constants, replaced all 5 magic number occurrences

**Not fixed (per instructions):**
- P3-01: File length (645 lines)
- P3-02: Function length (`join_queue`, `find_match`, `process_queue`)
- P3-05: Unused `patch` import in test file (test files excluded from Stage 4)
