# Player Module -- Stage 2 P0 Interface Compliance Report

**Module:** player
**Reviewer:** Karen (Stage 2 P0 Sweep)
**Date:** 2026-02-06
**Reference:** `docs/guidance/interface-contracts.md`

---

## Protocol Signature Deviations

```
[P0] [protocols.py:27-33] create_player has extra parameter `email: str | None = None` not in contract -> remove `email` parameter per interface-contracts.md section 4.3
```

```
[P0] [protocols.py:250-265] Method name `get_energy_state` does not match contract -> rename to `get_energy` per interface-contracts.md section 4.3
```

```
[P0] [protocols.py:250-265] `get_energy_state` returns `EnergyState` (correct type) but method name is wrong -> rename method to `get_energy` per interface-contracts.md section 4.3
```

```
[P0] [protocols.py:267-285] Method `update_energy_state(player_id, energy_update: EnergyStateUpdate) -> EnergyState` does not match contract -> contract specifies `consume_energy(player_id, amount: int = 1) -> EnergyState` per interface-contracts.md section 4.3
```

```
[P0] [protocols.py:103-118] Extra method `soft_delete_player` not in contract -> remove from protocol or escalate to Orchestrator for contract amendment per interface-contracts.md section 4.3
```

```
[P0] [protocols.py:120-139] Extra method `list_players` not in contract -> remove from protocol or escalate to Orchestrator for contract amendment per interface-contracts.md section 4.3
```

```
[P0] [protocols.py:143-158] Extra method `get_elo` not in contract -> remove from protocol or escalate to Orchestrator for contract amendment per interface-contracts.md section 4.3
```

```
[P0] [protocols.py:180-200] Extra method `calculate_elo_change` not in contract -> remove from protocol or escalate to Orchestrator for contract amendment per interface-contracts.md section 4.3
```

```
[P0] [protocols.py:221-246] Extra method `record_match_result` not in contract -> remove from protocol or escalate to Orchestrator for contract amendment per interface-contracts.md section 4.3
```

```
[P0] [protocols.py:287-302] Extra method `initialize_energy_state` not in contract -> remove from protocol or escalate to Orchestrator for contract amendment per interface-contracts.md section 4.3
```

## DTO Deviations

```
[P0] [dto.py:17-22] PlayerUpdate has field `email: str | None = None` not in contract -> remove `email` field; contract specifies only `username` and `elo_rating` per interface-contracts.md section 4.3
```

```
[P0] [dto.py:17-22] PlayerUpdate is missing field `elo_rating: int | None = None` from contract -> add `elo_rating: int | None = None` per interface-contracts.md section 4.3
```

```
[P0] [dto.py:25-31] DTO `EnergyStateUpdate` not in contract -> remove or escalate; contract specifies `consume_energy` method, not a generic energy update DTO per interface-contracts.md section 4.3
```

```
[P0] [dto.py:34-46] DTO `PaginatedResult` not in contract -> remove or escalate; `list_players` method that uses it is also not in contract per interface-contracts.md section 4.3
```

## Type Alias Deviations

No type alias deviations found. Module correctly imports `PlayerId` from `src.core.types.game` and domain types from `src.core.types.player`.

## Error Code Deviations

All error codes referenced in docstrings (`VALIDATION_INVALID_INPUT`, `CONFLICT_USERNAME_TAKEN`, `NOT_FOUND_PLAYER`) exist in the error taxonomy (interface-contracts.md section 2.2). No error code deviations.

---

## Summary

| Category | P0 Count |
|----------|----------|
| Method signature mismatches | 2 |
| Extra methods not in contract | 5 |
| Extra parameters on contract methods | 1 |
| DTO field mismatches | 3 |
| Extra DTOs not in contract | 2 |
| **Total P0 issues** | **13** |

**Recommendation:** Corrections needed. The core contract methods (`create_player`, `get_energy`, `consume_energy`) must be fixed to match exactly. The extra methods (`soft_delete_player`, `list_players`, `get_elo`, `calculate_elo_change`, `record_match_result`, `initialize_energy_state`) and extra DTOs (`EnergyStateUpdate`, `PaginatedResult`) should be escalated to the Orchestrator -- they may be legitimate extensions that need to be added to the contract, or they may be scope drift. The `PlayerUpdate` DTO must be corrected to match the contract (add `elo_rating`, remove `email`).
