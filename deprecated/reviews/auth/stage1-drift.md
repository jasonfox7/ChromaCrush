# Stage 1 Drift Review: auth

**Artifact Report:** `docs/artifacts/auth/report.md`
**Implementation Doc:** `docs/implementation/auth/implementation.md`
**Reviewer:** Karen (Stage 1 Document Sweep)
**Date:** 2026-02-06

---

## Method Count Comparison

Artifact defines 12 public methods on `AuthServiceProtocol`:
1. `authenticate`
2. `validate_token`
3. `refresh_token`
4. `logout`
5. `get_active_sessions`
6. `create_api_key`
7. `revoke_api_key`
8. `list_api_keys`
9. `check_rate_limit`
10. `record_api_request`
11. `hash_password` (sync)
12. `verify_password` (sync)

Implementation doc (Section 4) documents 12 public methods on `AuthService` matching the same set exactly. Match confirmed.

---

## Findings

[DRIFT] Artifact specifies `constants.py` in the internal file structure (Section 6.1) -> Implementation doc (Section 2) does not list a `constants.py` file among the files created. Minor omission or the file was not created.

[DRIFT] Artifact does NOT specify a `PasswordStoreProtocol` -> Implementation doc introduces `PasswordStoreProtocol` as a new protocol (in `protocols.py`) with `get_password_hash` and `set_password_hash` async methods. This is an undocumented addition to the public interface surface. The artifact says password access goes through `Player` entity (Section 4.3: "Password hash: `Player` entity (internal field)"), but the implementation uses a separate protocol to avoid leaking password hashes through the Player domain type.

[DRIFT] Artifact specifies `AuthService.__init__` takes `ConfigProtocol`, `LoggerProtocol`, `ErrorServiceProtocol`, `DataContext` and accesses repositories/player service -> Implementation doc shows `AuthService.__init__` takes 8 parameters: `config`, `logger`, `errors`, `player_service`, `session_repo`, `api_key_repo`, `password_store`, `redis`. The `DataContext` is not directly injected into the service (repositories handle their own data context). This is a significant signature difference from the artifact's dependency table.

[DRIFT] Artifact reports `refresh_token_hash` column uses "bcrypt hash of refresh token" in sessions table -> Implementation doc (Section 9) states refresh tokens are stored as "SHA-256 hashes (not bcrypt) because JWTs can exceed bcrypt's 72-byte limit and are already high-entropy." This is an undocumented implementation deviation from the artifact's data schema.

[DRIFT] Artifact error taxonomy lists `NOT_FOUND_PLAYER` (404) for `logout` and `get_active_sessions` -> Implementation doc error codes table does not list `NOT_FOUND_PLAYER` at all. The implementation focuses on auth-specific error codes. Either the player-not-found errors propagate from `player_service` without being caught, or they are handled differently.

[DRIFT] Artifact CLI section shows 12 commands total -> Implementation doc lists 12 commands: `hash-password`, `verify-password`, `show-config`, `login`, `validate-token`, `refresh`, `logout`, `sessions`, `create-key`, `list-keys`, `revoke-key`, `rate-limit`. The artifact lists the same 12 commands. Match confirmed, though `show-config` is an addition not explicitly in the artifact CLI listing (artifact has no `show-config`; it only shows auth-operation commands).

[DRIFT] Artifact CLI `logout` command shows `[--session-id <id>] [--all]` flags -> Implementation doc does not describe the specific CLI command signatures. This cannot be verified at document level.

---

## Document Health

Implementation doc is 323 lines -- thorough and detailed, with comprehensive internal design notes covering JWT structure, refresh token rotation, session management, API key design, rate limiting, password handling, and CLI architecture.

---

## Summary

5 drift items found. The most significant are: (1) the introduction of `PasswordStoreProtocol` not present in the artifact, (2) the `AuthService.__init__` signature change from 4 core parameters to 8 specific injections, and (3) the refresh token hash algorithm change from bcrypt to SHA-256. Items (1) and (2) represent reasonable design improvements but were not formally documented as deviations. Item (3) is a security-relevant implementation choice that diverges from the artifact's data schema.
