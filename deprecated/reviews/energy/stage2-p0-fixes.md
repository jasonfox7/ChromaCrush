# Energy Module -- Stage 2 P0 Interface Compliance Report

**Module:** energy
**Reviewer:** Karen (Stage 2 P0 Sweep)
**Date:** 2026-02-06
**Reference:** `docs/guidance/interface-contracts.md`

---

## Structural Deviation

```
[P0] [protocols.py:30] Energy operations are defined in a separate `EnergyServiceProtocol` class, but the contract places energy operations (`get_energy`, `consume_energy`) inside `PlayerServiceProtocol` -> energy should either be folded into PlayerServiceProtocol or the contract must be amended to define a separate EnergyServiceProtocol per interface-contracts.md section 4.3
```

## Protocol Signature Deviations

```
[P0] [protocols.py:35-54] Method `get_energy` returns `EnergyInfo` (module-local DTO) instead of `EnergyState` (from `src.core.types.player`) -> contract specifies return type `EnergyState` per interface-contracts.md section 4.3
```

```
[P0] [protocols.py:56-78] Method is named `consume_heart` instead of `consume_energy` -> contract specifies method name `consume_energy` per interface-contracts.md section 4.3
```

```
[P0] [protocols.py:56-78] `consume_heart` returns `EnergyConsumeResult` (module-local DTO) instead of `EnergyState` -> contract specifies return type `EnergyState` per interface-contracts.md section 4.3
```

```
[P0] [protocols.py:80-99] Extra method `can_play` not in contract -> remove from protocol or escalate to Orchestrator for contract amendment per interface-contracts.md section 4.3
```

```
[P0] [protocols.py:103-118] Extra method `apply_pending_regeneration` not in contract -> remove from protocol or escalate to Orchestrator for contract amendment per interface-contracts.md section 4.3
```

```
[P0] [protocols.py:120-136] Extra method `get_time_to_next_heart` not in contract -> remove from protocol or escalate to Orchestrator for contract amendment per interface-contracts.md section 4.3
```

```
[P0] [protocols.py:140-158] Extra method `record_login` not in contract -> remove from protocol or escalate to Orchestrator for contract amendment per interface-contracts.md section 4.3
```

```
[P0] [protocols.py:160-175] Extra method `get_streak` not in contract -> remove from protocol or escalate to Orchestrator for contract amendment per interface-contracts.md section 4.3
```

```
[P0] [protocols.py:179-204] Extra method `grant_bonus_hearts` not in contract -> remove from protocol or escalate to Orchestrator for contract amendment per interface-contracts.md section 4.3
```

```
[P0] [protocols.py:206-227] Extra method `refund_heart` not in contract -> remove from protocol or escalate to Orchestrator for contract amendment per interface-contracts.md section 4.3
```

## DTO Deviations

```
[P0] [dto.py:14-22] DTO `BonusSource` (Enum) not in contract -> remove or escalate; used by `grant_bonus_hearts` which is not in contract per interface-contracts.md section 4.3
```

```
[P0] [dto.py:25-36] DTO `EnergyInfo` not in contract -> contract uses `EnergyState` from `src.core.types.player` as the return type for energy operations per interface-contracts.md section 1.4 and 4.3
```

```
[P0] [dto.py:29] `EnergyInfo.player_id` is typed as `str` instead of `PlayerId` (which is `NewType("PlayerId", UUID)`) -> if this DTO is retained, player_id must use `PlayerId` type per interface-contracts.md section 1.1
```

```
[P0] [dto.py:39-47] DTO `EnergyConsumeResult` not in contract -> contract specifies `consume_energy` returns `EnergyState` per interface-contracts.md section 4.3
```

```
[P0] [dto.py:50-58] DTO `RegenResult` not in contract -> remove or escalate; used by `apply_pending_regeneration` which is not in contract per interface-contracts.md section 4.3
```

```
[P0] [dto.py:61-69] DTO `TimeToHeartResult` not in contract -> remove or escalate; used by `get_time_to_next_heart` which is not in contract per interface-contracts.md section 4.3
```

```
[P0] [dto.py:72-81] DTO `LoginResult` not in contract -> remove or escalate; used by `record_login` which is not in contract per interface-contracts.md section 4.3
```

```
[P0] [dto.py:84-93] DTO `StreakInfo` not in contract -> remove or escalate; used by `get_streak` which is not in contract per interface-contracts.md section 4.3
```

```
[P0] [dto.py:96-106] DTO `BonusGrantResult` not in contract -> remove or escalate; used by `grant_bonus_hearts` which is not in contract per interface-contracts.md section 4.3
```

## Type Alias Deviations

```
[P0] [dto.py:29] `EnergyInfo.player_id` uses `str` type -> should use `PlayerId` from `src.core.types.game` per interface-contracts.md section 1.1
```

## Error Code Deviations

All error codes referenced in docstrings (`NOT_FOUND_PLAYER`, `FORBIDDEN_INSUFFICIENT_ENERGY`, `VALIDATION_INVALID_INPUT`) exist in the error taxonomy (interface-contracts.md section 2.2). No error code deviations.

---

## Summary

| Category | P0 Count |
|----------|----------|
| Structural deviation (separate protocol) | 1 |
| Method name mismatches | 1 |
| Return type mismatches | 2 |
| Extra methods not in contract | 7 |
| Extra DTOs/Enums not in contract | 8 |
| Type alias violations | 1 |
| **Total P0 issues** | **20** |

**Recommendation:** Corrections needed. This module has the most severe structural deviation -- the contract defines energy operations as part of `PlayerServiceProtocol` with `EnergyState` return types, but the implementation creates an entirely separate `EnergyServiceProtocol` with its own DTO hierarchy. The Orchestrator must decide whether to:

1. **Amend the contract** to formalize the separate `EnergyServiceProtocol` and its DTOs (if this split is intentional and desired), OR
2. **Merge energy operations** back into `PlayerServiceProtocol` per the current contract.

Either way, the `consume_heart` -> `consume_energy` rename is required, and `EnergyInfo.player_id` must use `PlayerId` instead of `str`. The 7 extra methods and 8 extra DTOs need Orchestrator disposition.
