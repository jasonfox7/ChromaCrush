# Stage 2 P0 Fixes: events

**Reviewer:** Karen P0 (Stage 2 Interface Compliance)
**Date:** 2026-02-06
**Files reviewed:**
- `src/modules/events/protocols.py`
- `src/modules/events/types.py`
- `src/modules/events/dto.py`

**Reference documents:**
- `docs/guidance/interface-contracts.md` (Sections 1-2)
- `docs/artifacts/events/artifact.md` (Public Interface & Outputs)

---

## Protocol Signature Checks

All `EventServiceProtocol` method signatures in `protocols.py` match the artifact exactly:
- Method names: exact match
- Parameter names: exact match
- Parameter types: exact match
- Return types: exact match
- All methods are `async def`: confirmed

No P0 issues found in protocol signatures.

---

## Type Alias Checks

- `EventId` imported from `src.core.types.game` (not redefined): correct per interface-contracts.md Section 1.1
- `PlayerId` imported from `src.core.types.game`: correct
- `MatchId` imported from `src.core.types.game`: correct

No P0 issues found in type aliases.

---

## DTO / Dataclass Shape Checks

[P0] [src/modules/events/types.py:136] `Event` dataclass has field `max_participants: int | None` between `rules` and `participant_count` -- artifact output spec (artifact.md lines 242-261) does NOT include this field in the output dataclass definition

This is a shape mismatch: any caller expecting the artifact-defined `Event` output will encounter an unexpected field. While the field is reasonable (it appears in the DB schema and the `EventCreate` DTO), the authoritative output spec omits it. Every mock and test constructing an `Event` must account for this extra field.

---

## Error Code Checks

The following error codes used in the artifact's "Error Cases" table are NOT present in the interface-contracts.md Section 2 error taxonomy:

[P0] [artifact:error-cases] `CONFLICT_EVENT_NOT_ACTIVE` not in interface-contracts.md Section 2 error taxonomy
[P0] [artifact:error-cases] `CONFLICT_EVENT_ALREADY_FINALIZED` not in interface-contracts.md Section 2 error taxonomy
[P0] [artifact:error-cases] `CONFLICT_ALREADY_PARTICIPANT` not in interface-contracts.md Section 2 error taxonomy
[P0] [artifact:error-cases] `FORBIDDEN_NOT_EVENT_PARTICIPANT` not in interface-contracts.md Section 2 error taxonomy
[P0] [artifact:error-cases] `FORBIDDEN_EVENT_REQUIREMENTS_NOT_MET` not in interface-contracts.md Section 2 error taxonomy
[P0] [artifact:error-cases] `FORBIDDEN_CANNOT_LEAVE_EVENT` not in interface-contracts.md Section 2 error taxonomy
[P0] [artifact:error-cases] `CONFLICT_EVENT_AT_CAPACITY` not in interface-contracts.md Section 2 error taxonomy

**Note:** These codes ARE defined in the artifact and used consistently in the implementation. The issue is that the interface-contracts.md error taxonomy was never updated to include events module error codes (unlike payments/bot_earnings codes which were added in v1.2). This is an escalation item for the Orchestrator to update the interface-contracts.md error taxonomy.

---

## Summary

| Check | Result |
|-------|--------|
| Protocol method signatures | PASS |
| Parameter names/types | PASS |
| Return types | PASS |
| Async behavior | PASS |
| Type aliases from core | PASS |
| DTO/dataclass shapes | 1 P0 (extra field on Event) |
| Error codes in taxonomy | 7 P0 (codes not in interface-contracts.md) |

**Recommendation:** Corrections needed.

1. **Event dataclass**: Either add `max_participants` to the artifact output spec, or remove it from `types.py`. Given that the DB schema and `EventCreate` DTO include it, the artifact output spec should be updated (Orchestrator action).

2. **Error codes**: The Orchestrator must add the 7 events-specific error codes to `docs/guidance/interface-contracts.md` Section 2 (same pattern as the payments/bot_earnings codes that were added in v1.2). Until then, the codes are artifact-authorized but not contract-authorized.
