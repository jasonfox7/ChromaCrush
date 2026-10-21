# Auth Module -- Stage 2 P0 Interface Compliance Report

**Module:** auth
**Reviewer:** Karen (Stage 2 P0 Sweep)
**Date:** 2026-02-06
**Reference:** `docs/guidance/interface-contracts.md`

---

## Protocol Signature Deviations

```
[P0] [protocols.py:134-153] create_api_key has extra parameter `description: str | None = None` not in contract -> contract specifies `create_api_key(player_id: PlayerId) -> ApiKeyCreationResult` with no description parameter per interface-contracts.md section 4.4
```

```
[P0] [protocols.py:172-189] list_api_keys has extra parameter `include_revoked: bool = False` not in contract -> contract specifies `list_api_keys(player_id: PlayerId) -> list[ApiKeyInfo]` with no include_revoked parameter per interface-contracts.md section 4.4
```

```
[P0] [protocols.py:99-113] Extra method `logout` not in contract -> remove from protocol or escalate to Orchestrator for contract amendment per interface-contracts.md section 4.4
```

```
[P0] [protocols.py:115-131] Extra method `get_active_sessions` not in contract -> remove from protocol or escalate to Orchestrator for contract amendment per interface-contracts.md section 4.4
```

```
[P0] [protocols.py:193-208] Extra method `check_rate_limit` not in contract -> remove from protocol or escalate to Orchestrator for contract amendment per interface-contracts.md section 4.4
```

```
[P0] [protocols.py:210-227] Extra method `record_api_request` not in contract -> remove from protocol or escalate to Orchestrator for contract amendment per interface-contracts.md section 4.4
```

```
[P0] [protocols.py:230-247] Extra method `hash_password` not in contract -> remove from protocol or escalate to Orchestrator for contract amendment per interface-contracts.md section 4.4
```

```
[P0] [protocols.py:249-266] Extra method `verify_password` not in contract -> remove from protocol or escalate to Orchestrator for contract amendment per interface-contracts.md section 4.4
```

```
[P0] [protocols.py:269-298] Extra protocol `PasswordStoreProtocol` not in contract -> remove from protocol file or escalate to Orchestrator for contract amendment per interface-contracts.md section 4.4
```

## DTO Deviations

```
[P0] [dto.py:17-28] AuthResult adds extra property `authorization_header` not in contract -> minor, but not in contract spec; the 4 fields (access_token, refresh_token, token_type, expires_in) match exactly per interface-contracts.md section 4.4
```

```
[P0] [dto.py:40-48] Extra DTO `SessionInfo` not in contract -> remove or escalate; used by `get_active_sessions` which is also not in contract per interface-contracts.md section 4.4
```

```
[P0] [dto.py:51-63] Extra DTO `RateLimitStatus` not in contract -> remove or escalate; used by `check_rate_limit` and `record_api_request` which are not in contract per interface-contracts.md section 4.4
```

```
[P0] [dto.py:66-75] Extra DTO `TokenPayload` not in contract -> remove or escalate; appears to be an internal implementation detail per interface-contracts.md section 4.4
```

## Type Alias Deviations

No type alias deviations found. Module correctly imports `PlayerId` from `src.core.types.game`, and `AuthToken`, `ApiKeyInfo` from `src.core.types.auth`. Uses `UUID` from stdlib where appropriate.

## Error Code Deviations

```
[P0] [protocols.py:167] Docstring references error code `NOT_FOUND_API_KEY` which does not exist in error taxonomy -> should be `AUTH_API_KEY_NOT_FOUND` per interface-contracts.md section 2.2 (Authentication Errors)
```

```
[P0] [protocols.py:206] Docstring references error code `NOT_FOUND_API_KEY` which does not exist in error taxonomy -> should be `AUTH_API_KEY_NOT_FOUND` per interface-contracts.md section 2.2 (Authentication Errors)
```

```
[P0] [protocols.py:225] Docstring references error code `NOT_FOUND_API_KEY` which does not exist in error taxonomy -> should be `AUTH_API_KEY_NOT_FOUND` per interface-contracts.md section 2.2 (Authentication Errors)
```

---

## Summary

| Category | P0 Count |
|----------|----------|
| Extra parameters on contract methods | 2 |
| Extra methods not in contract | 6 |
| Extra protocol classes not in contract | 1 |
| DTO extra properties/fields | 1 |
| Extra DTOs not in contract | 3 |
| Error code mismatches | 3 |
| **Total P0 issues** | **16** |

**Recommendation:** Corrections needed. The two contract methods with extra parameters (`create_api_key`, `list_api_keys`) must be fixed. The 3 error code references to `NOT_FOUND_API_KEY` must be corrected to `AUTH_API_KEY_NOT_FOUND` to match the taxonomy. The extra methods (`logout`, `get_active_sessions`, `check_rate_limit`, `record_api_request`, `hash_password`, `verify_password`), extra protocol (`PasswordStoreProtocol`), and extra DTOs (`SessionInfo`, `RateLimitStatus`, `TokenPayload`) should be escalated to the Orchestrator for contract amendment decision -- several (especially `hash_password`/`verify_password` and `logout`) are likely legitimate extensions.
