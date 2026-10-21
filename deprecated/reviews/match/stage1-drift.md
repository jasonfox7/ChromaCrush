# Stage 1 Drift Report: match

**Reviewer:** Document Reviewer (Karen Compliance Sweep)
**Date:** 2026-02-06
**Artifact:** docs/artifacts/match/report.md + artifact.md
**Implementation Doc:** docs/implementation/match/implementation.md

---

## Method Count Comparison

Artifact defines 8 public methods on `MatchService`:
1. `create_match(player1_id, player2_id, board_seed, match_type) -> MatchState`
2. `submit_move(match_id, player_id, move) -> MoveSubmissionResult`
3. `get_match_state(match_id, for_player_id) -> MatchState`
4. `get_player_board(match_id, player_id) -> PlayerBoardState`
5. `forfeit_match(match_id, player_id) -> MatchState`
6. `get_match_history(player_id, limit, offset, status) -> PaginatedResult[MatchSummary]`
7. `get_move_history(match_id, player_id) -> list[MoveRecord]`
8. `abandon_stale_matches() -> int`

Implementation doc documents 10 public methods:
1. `create_match` (matches artifact)
2. `submit_move` (matches artifact)
3. `get_match(match_id) -> MatchState` (NEW -- not in artifact)
4. `get_match_state(match_id, for_player_id) -> MatchState` (matches artifact)
5. `get_player_board` (matches artifact)
6. `get_active_matches(player_id) -> list[MatchState]` (NEW -- not in artifact)
7. `forfeit_match` (matches artifact)
8. `get_match_history` (matches artifact)
9. `get_move_history` (matches artifact)
10. `abandon_stale_matches` (matches artifact)

[DRIFT] Artifact specifies 8 public methods -> Implementation doc documents 10 public methods. Two undocumented additions: `get_match(match_id)` and `get_active_matches(player_id)`.

The impl doc itself notes (Section 14): "`get_match_state` is Not in MatchServiceProtocol but present in service implementation." This is confusing -- looking more carefully, the impl doc says the `MatchServiceProtocol` has 9 public methods, not 10. It appears `get_match_state` may be on the service but not on the protocol. Meanwhile, `get_match` and `get_active_matches` appear in both the protocol and the service.

[DRIFT] Artifact does not define `get_match(match_id)` as a separate method from `get_match_state` -> Implementation doc introduces `get_match` as a simpler version without participant validation. This is an undocumented API addition.

[DRIFT] Artifact does not define `get_active_matches(player_id)` -> Implementation doc introduces this method. The artifact's match module uses `find_active_by_player` in the repository layer but does not expose it as a public service method. The matchmaking artifact references `find_active_by_player` on the match service protocol, which may have driven this addition.

---

## Constructor Dependencies Comparison

Artifact constructor takes 12 parameters:
- config, logger, errors, data_ctx, board_gen_service, board_service, scoring_service, special_gems_service, player_service, auth_service, energy_service, match_repository

Implementation doc constructor takes 13 parameters (all of the above plus):
- `match_move_repository: MatchMoveRepositoryProtocol`

[DRIFT] Artifact constructor specifies `match_repository` as a single dependency -> Implementation doc shows two separate repository dependencies: `match_repository` and `match_move_repository`. The artifact defines `MatchMoveRepository` as a protocol but does not inject it separately in the constructor; it appears the artifact expected both repositories to be accessed through a single injection point or for the move repository to be internal to the match repository.

---

## Error Handling Comparison

Artifact error cases (13 codes):
- `NOT_FOUND_PLAYER`, `NOT_FOUND_MATCH`, `VALIDATION_INVALID_INPUT`, `FORBIDDEN_NOT_MATCH_PARTICIPANT`, `VALIDATION_NO_MOVES_REMAINING`, `CONFLICT_MATCH_ALREADY_COMPLETED`, `CONFLICT_PLAYER_IN_MATCH`, `FORBIDDEN_INSUFFICIENT_ENERGY`, `VALIDATION_POSITIONS_NOT_ADJACENT`, `VALIDATION_OUT_OF_BOUNDS`, `VALIDATION_INVALID_GEM_SWAP`, `CONFLICT_MATCH_NOT_IN_PROGRESS`, `INTERNAL_DATABASE_ERROR`

Implementation doc error codes (10 codes):
- `VALIDATION_INVALID_INPUT`, `NOT_FOUND_PLAYER`, `NOT_FOUND_MATCH`, `CONFLICT_CONCURRENT_MATCH`, `FORBIDDEN_INSUFFICIENT_ENERGY`, `FORBIDDEN_NOT_MATCH_PARTICIPANT`, `CONFLICT_MATCH_ALREADY_COMPLETED`, `CONFLICT_MATCH_NOT_IN_PROGRESS`, `VALIDATION_NO_MOVES_REMAINING`, `VALIDATION_INVALID_GEM_SWAP`

[DRIFT] Artifact specifies `CONFLICT_PLAYER_IN_MATCH` error code -> Implementation doc uses `CONFLICT_CONCURRENT_MATCH` instead. Same semantic meaning but different code name.

[DRIFT] Artifact specifies `VALIDATION_POSITIONS_NOT_ADJACENT` and `VALIDATION_OUT_OF_BOUNDS` as error codes in the match module -> Implementation doc does not list these. These may be raised by the board_service dependency rather than directly by the match service, but the artifact lists them as match module errors.

[DRIFT] Artifact specifies `INTERNAL_DATABASE_ERROR` -> Implementation doc does not list this error code. The artifact states "Database errors are caught and wrapped in INTERNAL_DATABASE_ERROR" but this pattern is not documented in the impl.

---

## Public Interface Shape

[DRIFT] Artifact's `MatchState` type does not include `get_player_state`, `get_opponent_state`, `both_finished`, `is_participant` as methods -> Implementation doc documents these as methods/properties on `MatchState`. The artifact's code listing does include these in the Internal Design section, so this is more of a documentation structure issue than a real drift.

---

## Configuration Keys

Artifact defines 8 config keys (including `game.board_width` and `game.board_height`). Implementation doc documents 6 config keys (match-specific only, omitting `game.board_width` and `game.board_height`).

[DRIFT] Artifact lists `game.board_width` and `game.board_height` as config keys used by match module -> Implementation doc does not list these, suggesting the match module may not read them directly (relying on board_gen_service instead).

---

## Async Behavior

Artifact: all public methods async. Impl doc: all public methods async. Match.

---

## CLI Commands

Artifact specifies 8 CLI commands: create, move, get, board, history, moves, forfeit, abandon-stale.

Implementation doc documents 9 CLI commands: create, submit-move, show, board, active, history, moves, forfeit, abandon-stale.

[DRIFT] Artifact CLI command `get` -> Implementation doc renames to `show`
[DRIFT] Artifact CLI command `move` -> Implementation doc renames to `submit-move`
[DRIFT] Artifact does not include `active` CLI command -> Implementation doc adds `active` command (lists active matches for player), which corresponds to the undocumented `get_active_matches` method

---

## Deviations Section

Implementation doc section 3 states: "Not assessed -- document produced from code examination only."

Implementation doc section 14 "Deviations from Standard Patterns" documents three deviations:
1. Extra `get_match_state` method not in protocol
2. MatchType enum mapping to board_gen MatchType
3. Deterministic seed derivation

These are self-identified but the first confirms the method count drift.

---

## Document Thickness

Implementation doc is 600 lines. This is thorough for the module's complexity.

---

## Findings Summary

```
[DRIFT] Artifact specifies 8 public methods -> Implementation doc documents 10 public methods (added get_match, get_active_matches)
[DRIFT] Artifact constructor takes 12 dependencies (match_repository) -> Implementation takes 13 (match_repository + match_move_repository as separate injections)
[DRIFT] Artifact specifies CONFLICT_PLAYER_IN_MATCH -> Implementation uses CONFLICT_CONCURRENT_MATCH (renamed)
[DRIFT] Artifact specifies VALIDATION_POSITIONS_NOT_ADJACENT, VALIDATION_OUT_OF_BOUNDS as match module errors -> Implementation doc does not list these (likely delegated to board_service)
[DRIFT] Artifact specifies INTERNAL_DATABASE_ERROR -> Implementation doc does not list this error code
[DRIFT] Artifact lists game.board_width and game.board_height as config keys -> Implementation doc omits these
[DRIFT] Artifact CLI command "get" -> Implementation renames to "show"; "move" -> "submit-move"; adds "active" command
```
