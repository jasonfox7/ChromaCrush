# Vault Module -- Stage 4 Compliance Fixes

**Module:** vault
**Date:** 2026-02-07
**Scope:** P2-04 (transaction boundary), P3-04 (magic numbers)

---

## Changes Applied

### P2-04: Transaction Boundary -- DataContext Injection

**Finding:** `VaultService.__init__` did not receive a `DataContextProtocol`, so multi-step mutations like `attempt_raid` (raid log creation + artifact transfer) and `transfer_artifact` could not be wrapped in explicit transaction boundaries.

**Fix:**
- Added `from src.core.protocols.data_context import DataContextProtocol` under `TYPE_CHECKING` in `src/modules/vault/service.py`.
- Added `data_ctx: DataContextProtocol | None = None` parameter to `VaultService.__init__`.
- Stored as `self._data_ctx` with inline TODO comment noting the transaction boundary intent for `attempt_raid` and `transfer_artifact`.
- Updated docstring `Args` section to document the new parameter.
- Updated `src/cli/commands/vault_commands.py` `_build_vault_service()` to pass `data_ctx=ctx.data_ctx`.

**Rationale:** The `DataContextProtocol` exists in `src/core/protocols/data_context.py` and is already used by the match service. The parameter is optional (`None` default) so existing callers (including tests) are not broken. Actual transaction wrapping is deferred until the service-layer transaction orchestration pattern is established project-wide.

**Files changed:**
- `src/modules/vault/service.py` (lines 34, 72, 82-86)
- `src/cli/commands/vault_commands.py` (line 132)

---

### P3-04: Magic Number 100

**Finding:** `service.py:215` used bare `100` as the maximum page limit for `get_player_artifacts` validation.

**Fix:**
- Defined module-level constant `_MAX_PAGE_LIMIT: int = 100` after imports.
- Replaced `limit > 100` with `limit > _MAX_PAGE_LIMIT` in the validation check.
- Updated the error message to use an f-string referencing the constant.

**Files changed:**
- `src/modules/vault/service.py` (constant definition after imports; usage in `get_player_artifacts`)

---

## Items NOT Fixed (Out of Scope)

| Finding | Reason |
|---------|--------|
| P3-01 (file length) | Excluded per assignment |
| P3-02 (function length) | Excluded per assignment |
| P3-05 (test patching) | Requires test file changes (Stage 5 work) |
| P3-07 (FORBIDDEN_INSUFFICIENT_ENERGY) | Significant feature addition, not a compliance fix |
| P2-01 (config namespace) | Orchestrator escalation item, not a code fix |
