# Stage 1 Drift Report: vault

**Reviewer:** Document Reviewer (Karen Compliance Sweep)
**Date:** 2026-02-06
**Artifact:** docs/artifacts/vault/report.md + artifact.md
**Implementation Doc:** docs/implementation/vault/implementation.md

---

## Method Count Comparison

Artifact defines 18 public methods on `VaultServiceProtocol`:
1. `add_artifact`
2. `get_artifact`
3. `get_player_artifacts`
4. `get_vault_summary`
5. `remove_artifact`
6. `transfer_artifact`
7. `get_artifact_definition`
8. `list_artifact_definitions`
9. `get_collection_progress`
10. `check_set_complete`
11. `activate_shield`
12. `get_shield_status`
13. `deactivate_shield`
14. `is_protected`
15. `attempt_raid`
16. `can_raid`
17. `get_raid_history`
18. `get_raid_cooldown`

Implementation doc documents 17 public methods on `VaultServiceProtocol`.

[DRIFT] Artifact specifies `check_set_complete(player_id, artifact_set) -> bool` as a public method on VaultServiceProtocol -> Implementation doc does not list this method. It appears to have been dropped during implementation.

---

## Error Handling Comparison

Artifact error cases:
- `VALIDATION_INVALID_INPUT` (invalid artifact type, invalid duration, self-raid, wrong owner, duration <= 0, limit out of range, vault full)
- `NOT_FOUND_PLAYER` (player doesn't exist)
- `NOT_FOUND_ARTIFACT` (artifact doesn't exist, artifact type not in catalog)
- `FORBIDDEN_VAULT_PROTECTED` (defender has active shield)
- `FORBIDDEN_INSUFFICIENT_ENERGY` (attacker lacks raid energy -- delegated to energy module)
- `CONFLICT_SHIELD_ALREADY_ACTIVE` (shield already exists)
- `CONFLICT_RAID_COOLDOWN` (raided too recently)

Implementation doc error codes:
- `VALIDATION_INVALID_INPUT` (matching cases plus deactivate_shield edge cases)
- `NOT_FOUND_ARTIFACT` (matching)
- `NOT_FOUND_PLAYER` (matching, via player_service)
- `INTERNAL_UNEXPECTED` (definition missing for existing artifact, definition missing after transfer)
- `CONFLICT_SHIELD_ALREADY_ACTIVE` (matching)
- `FORBIDDEN_VAULT_PROTECTED` (matching)
- `CONFLICT_RAID_COOLDOWN` (matching)
- `NOT_FOUND_RESOURCE` (vault_shield_repository.delete shield not found)

[DRIFT] Artifact does not mention `INTERNAL_UNEXPECTED` error code -> Implementation doc introduces two `INTERNAL_UNEXPECTED` error cases (definition missing for existing artifact in `get_artifact`, definition missing after transfer in `transfer_artifact`). These are defensive error paths not in the artifact's error taxonomy.

[DRIFT] Artifact does not mention `NOT_FOUND_RESOURCE` error code -> Implementation doc introduces `NOT_FOUND_RESOURCE` in vault_shield_repository.delete. This is a repository-level error not specified in the artifact.

[DRIFT] Artifact specifies `FORBIDDEN_INSUFFICIENT_ENERGY` for raids -> Implementation doc does not list `FORBIDDEN_INSUFFICIENT_ENERGY`. The vault service does not appear to consume energy directly; the artifact's report mentions "energy via player" as an indirect dependency. The artifact's `attempt_raid` docstring says "Consumes energy from attacker" but the impl doc's raid flow does not mention energy consumption. This needs code verification in Stage 3.

---

## Public Interface Shape

[DRIFT] Artifact specifies `check_set_complete(player_id, artifact_set) -> bool` -> Implementation doc omits this method entirely. The collection system in the impl appears to only expose `get_collection_progress`, and the `is_complete` property on `CollectionProgress` provides equivalent functionality, but the explicit protocol method is missing.

Remaining 17 methods have matching signatures between artifact and impl doc.

---

## Configuration Keys

Artifact defines 7 config keys. Impl doc documents 7 matching config keys.

**Result:** No configuration drift.

---

## Async Behavior

Artifact: all methods async. Impl doc: all 17 public methods async. Match.

Impl doc additionally documents that `raid_engine.py` and `collection.py` pure functions are synchronous. This is consistent with artifact design.

---

## Additional Observations

[DRIFT] Artifact `collection.py` defines `calculate_collection_progress` as `async def` -> Implementation doc documents it as a synchronous `def`. The impl doc explicitly states "The three pure helper modules (raid_engine.py, collection.py) are synchronous." This is a sensible deviation (the function performs no I/O), but it contradicts the artifact's code listing which shows `async def`.

---

## CLI Surface Comparison

Artifact specifies 16 CLI commands including: `catalog-show`, `collection`, `collection-check`, `shield-deactivate`, `raid-cooldown`, `transfer`.

Implementation doc lists 10 CLI commands: `list`, `summary`, `add`, `get`, `catalog`, `shield-status`, `shield-activate`, `raid`, `can-raid`, `raid-history`.

[DRIFT] Artifact specifies 16 CLI commands -> Implementation doc documents only 10 CLI commands. Missing from impl: `catalog-show`, `collection`, `collection-check`, `shield-deactivate`, `transfer`, `raid-cooldown`. Six CLI commands from the artifact are not documented in the implementation.

---

## Deviations Section

Implementation doc section 3 states: "Not assessed -- document produced from code examination only."

---

## Document Thickness

Implementation doc is 473 lines. This is thorough for the module's complexity.

---

## Findings Summary

```
[DRIFT] Artifact specifies check_set_complete() as public method on VaultServiceProtocol -> Implementation doc omits this method (17 methods instead of 18)
[DRIFT] Artifact does not mention INTERNAL_UNEXPECTED error code -> Implementation doc introduces two INTERNAL_UNEXPECTED defensive error cases
[DRIFT] Artifact does not mention NOT_FOUND_RESOURCE error code -> Implementation doc introduces NOT_FOUND_RESOURCE in repository layer
[DRIFT] Artifact specifies FORBIDDEN_INSUFFICIENT_ENERGY for attempt_raid -> Implementation doc does not document energy consumption in raid flow
[DRIFT] Artifact defines calculate_collection_progress as async def -> Implementation doc documents it as synchronous def
[DRIFT] Artifact specifies 16 CLI commands -> Implementation doc documents only 10 CLI commands (6 missing: catalog-show, collection, collection-check, shield-deactivate, transfer, raid-cooldown)
```
