# Energy Module -- Stage 4 Compliance Fixes

**Module:** energy
**Date:** 2026-02-07
**Scope:** P2-04 (transaction boundary), P3-04 (magic numbers)

---

## Changes Applied

### P2-04: Transaction Boundary -- DataContext Injection

**Finding:** `EnergyService.__init__` did not receive a `DataContextProtocol`, so `consume_heart()` could not wrap its regen+update sequence in an explicit transaction boundary.

**Fix:**
- Added `from src.core.protocols.data_context import DataContextProtocol` under `TYPE_CHECKING` in `src/modules/energy/service.py`.
- Added `data_ctx: DataContextProtocol | None = None` parameter to `EnergyService.__init__`.
- Stored as `self._data_ctx` with inline TODO comment noting the transaction boundary intent for `consume_heart`.
- Updated `src/cli/commands/energy_commands.py` `_build_energy_service()` to pass `data_ctx=ctx.data_ctx`.

**Rationale:** The `DataContextProtocol` exists in `src/core/protocols/data_context.py` and is already used by the match service. The parameter is optional (`None` default) so existing callers (including tests) are not broken. Actual transaction wrapping is deferred until the service-layer transaction orchestration pattern is established project-wide.

**Files changed:**
- `src/modules/energy/service.py` (lines 40, 70-75)
- `src/cli/commands/energy_commands.py` (line 102)

---

### P3-04: Magic Number 86400

**Finding:** `service.py:565` used bare `86400` (seconds in 24 hours) as the Redis TTL for idempotency keys.

**Fix:**
- Defined module-level constant `_IDEMPOTENCY_TTL_SECONDS: int = 86400` after imports.
- Replaced `86400` in the `self._redis.setex()` call with `_IDEMPOTENCY_TTL_SECONDS`.

**Files changed:**
- `src/modules/energy/service.py` (constant definition after imports; usage in `grant_bonus_hearts`)

---

## Items NOT Fixed (Out of Scope)

| Finding | Reason |
|---------|--------|
| P3-01 (file length) | Excluded per assignment |
| P3-02 (function length) | Excluded per assignment |
| P2-01 (config namespace) | Orchestrator escalation item, not a code fix |
