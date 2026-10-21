# Stage 1 Drift Report: events

**Reviewer:** Document Reviewer (Karen Compliance Sweep)
**Date:** 2026-02-06
**Artifact:** docs/artifacts/events/report.md + docs/artifacts/events/artifact.md
**Implementation Doc:** docs/implementation/events/implementation.md

---

## Method Count

Artifact defines 15 public methods on EventService. Implementation doc lists 15 public methods.

No drift on method count.

## Constructor Signature

[DRIFT] Artifact constructor has 12 parameters (includes separate `redis_ctx: RedisContextProtocol`) -> Implementation constructor has 11 parameters (uses `data_ctx.redis` instead of separate `redis_ctx`). Deviation is documented in impl doc section 3 with justification referencing orchestrator guidance.

## Error Codes

[DRIFT] Artifact error cases table lists `NOT_FOUND_PLAYER` as an error code -> Implementation doc error table (section 5) does not list `NOT_FOUND_PLAYER`. The impl doc lists 10 error codes; the artifact lists 11 (including NOT_FOUND_PLAYER). The missing error likely still occurs (via player_service propagation) but is not documented in the impl error table.

[DRIFT] Artifact does not list `CONFLICT_MAX_MATCHES_REACHED` in its error cases table -> Artifact internal algorithm pseudocode (record_event_match) uses `CONFLICT_MAX_MATCHES_REACHED`; the implementation doc does not list it in the error table either. Both documents reference it only in algorithm context, so this is consistent, but the artifact error cases table is incomplete relative to its own algorithm section.

## Public Interface Shape

[DRIFT] Artifact `PlayerEventRank.points_to_next_tier` is typed `int | None` with meaningful calculation expected -> Implementation doc deviation #2 states this always returns `None` (simplified). Documented with justification, but represents a feature gap.

[DRIFT] Artifact `finalize_event` validation says "Must be ended, not already finalized" -> Implementation doc deviation #3 says implementation allows both `ended` and `active` status. Documented, but expands the accepted states beyond artifact intent.

## Data Access

Artifact report mentions `event_matches` table for match-level granularity. Implementation doc lists the same three tables (events, event_participants, event_matches) plus two Redis structures. No drift.

## Configuration Keys

Artifact report lists 12 config keys. Implementation doc section 6 lists 12 identical keys with matching defaults. No drift.

## Deviations Documented

Three deviations documented in implementation doc section 3. All include justification. The `redis_ctx` simplification references orchestrator guidance.

## Implementation Doc Completeness

Implementation doc is 164 lines. Not flagged as thin.

## Summary

- 2 documented deviations with justification (redis_ctx, points_to_next_tier simplification, finalize status expansion)
- 1 undocumented gap: `NOT_FOUND_PLAYER` error missing from impl error table
- 1 feature simplification: `points_to_next_tier` always returns None
