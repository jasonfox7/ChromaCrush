"""Direct test of mega gem attraction logic.

Bypasses HTTP — calls BoardService directly with crafted boards.
Tests:
  1. _check_special_attractions detection
  2. _process_attractions merging
  3. Full process_move cascade with attractions
  4. Mega gem activation when matched
"""

import sys
import numpy as np

# Minimal stubs for BoardService dependencies.

class StubConfig:
    def get(self, key, default=None):
        return {
            "game.board_width": 8,
            "game.board_height": 8,
            "game.gem_types": 6,
            "game.min_match_length": 3,
        }.get(key, default)

class StubLogger:
    def info(self, *a, **kw): pass
    def debug(self, *a, **kw): pass
    def warning(self, *a, **kw): pass
    def error(self, *a, **kw): pass
    def trace(self, *a, **kw): pass

class StubErrors:
    def create(self, *a, **kw):
        raise RuntimeError(f"StubErrors.create called: {a} {kw}")

# Now import the real code.
from src.core.types.board import BoardState
from src.core.types.game import GemFunction, GemType, Move, Position, is_mega_gem
from src.modules.board.service import BoardService

def make_board_service():
    return BoardService(StubConfig(), StubLogger(), StubErrors())

def print_board(board, label="Board"):
    """Pretty-print a board with colors and functions."""
    print(f"\n{'='*60}")
    print(f"  {label}")
    print(f"{'='*60}")
    print("  Color grid (1=R, 2=B, 3=G, 4=Y, 5=P, 6=O):")
    for r in range(board.height):
        row = " ".join(f"{int(board.grid[r, c]):2d}" for c in range(board.width))
        print(f"    row {r}: [{row}]")
    print("  Func grid (0=none, 1=H, 2=V, 3=B, 4=O, 11-44=mega):")
    for r in range(board.height):
        row = " ".join(f"{int(board.func_grid[r, c]):2d}" for c in range(board.width))
        print(f"    row {r}: [{row}]")
    print()


# ============================================================
# TEST 1: Direct attraction detection
# ============================================================
def test_attraction_detection():
    print("\n" + "=" * 60)
    print("TEST 1: _check_special_attractions detection")
    print("=" * 60)

    # Board with no matches. Two specials at (3,2) and (3,4) with regular gem at (3,3).
    # Colors designed to have NO 3-in-a-row anywhere (checkerboard-ish).
    grid = np.array([
        [1, 2, 1, 2, 1, 2, 1, 2],
        [3, 4, 3, 4, 3, 4, 3, 4],
        [1, 2, 1, 2, 1, 2, 1, 2],
        [3, 4, 5, 6, 5, 4, 3, 4],  # specials at col 2 and col 4
        [1, 2, 1, 2, 1, 2, 1, 2],
        [3, 4, 3, 4, 3, 4, 3, 4],
        [1, 2, 1, 2, 1, 2, 1, 2],
        [3, 4, 3, 4, 3, 4, 3, 4],
    ], dtype=np.int8)

    func_grid = np.zeros((8, 8), dtype=np.int8)
    func_grid[3, 2] = int(GemFunction.LINE_BLAST_H)  # 1
    func_grid[3, 4] = int(GemFunction.RADIAL_BOMB)    # 3

    board = BoardState(grid=grid, func_grid=func_grid)
    print_board(board, "Initial board with 2 specials at (3,2) and (3,4)")

    # Call static method directly.
    pairs = BoardService._check_special_attractions(board)

    print(f"  Attraction pairs found: {len(pairs)}")
    for i, (a, b, c) in enumerate(pairs):
        print(f"    Pair {i}: posA=({a.row},{a.col}) posB=({b.row},{b.col}) center=({c.row},{c.col})")

    if len(pairs) == 1:
        a, b, c = pairs[0]
        assert a == Position(3, 2), f"Expected posA=(3,2), got ({a.row},{a.col})"
        assert b == Position(3, 4), f"Expected posB=(3,4), got ({b.row},{b.col})"
        assert c == Position(3, 3), f"Expected center=(3,3), got ({c.row},{c.col})"
        print("  PASS: Attraction detected correctly!")
    else:
        print("  FAIL: Expected 1 attraction pair!")
    return len(pairs) == 1


# ============================================================
# TEST 2: Attraction processing (func_grid mutation)
# ============================================================
def test_attraction_processing():
    print("\n" + "=" * 60)
    print("TEST 2: _process_attractions merging")
    print("=" * 60)

    grid = np.array([
        [1, 2, 1, 2, 1, 2, 1, 2],
        [3, 4, 3, 4, 3, 4, 3, 4],
        [1, 2, 1, 2, 1, 2, 1, 2],
        [3, 4, 5, 6, 5, 4, 3, 4],
        [1, 2, 1, 2, 1, 2, 1, 2],
        [3, 4, 3, 4, 3, 4, 3, 4],
        [1, 2, 1, 2, 1, 2, 1, 2],
        [3, 4, 3, 4, 3, 4, 3, 4],
    ], dtype=np.int8)

    func_grid = np.zeros((8, 8), dtype=np.int8)
    func_grid[3, 2] = int(GemFunction.LINE_BLAST_H)  # 1
    func_grid[3, 4] = int(GemFunction.RADIAL_BOMB)    # 3

    board = BoardState(grid=grid, func_grid=func_grid)

    triples = [(Position(3, 2), Position(3, 4), Position(3, 3))]
    new_board, attractions = BoardService._process_attractions(board, triples)

    print(f"  Attractions generated: {len(attractions)}")
    for att in attractions:
        print(f"    posA=({att.pos_a.row},{att.pos_a.col}) func={att.func_a}")
        print(f"    posB=({att.pos_b.row},{att.pos_b.col}) func={att.func_b}")
        print(f"    center=({att.center_pos.row},{att.center_pos.col}) mega_func={att.mega_func}")

    # Check func_grid was mutated correctly.
    center_func = int(new_board.func_grid[3, 3])
    posA_func = int(new_board.func_grid[3, 2])
    posB_func = int(new_board.func_grid[3, 4])

    print(f"\n  After processing:")
    print(f"    func_grid[3,2] = {posA_func} (should be 0 = stripped)")
    print(f"    func_grid[3,3] = {center_func} (should be 13 = H+B mega)")
    print(f"    func_grid[3,4] = {posB_func} (should be 0 = stripped)")
    print(f"    grid[3,3] color = {int(new_board.grid[3, 3])} (should be unchanged)")

    ok = (posA_func == 0 and posB_func == 0 and center_func == 13)
    print(f"  {'PASS' if ok else 'FAIL'}: Attraction processing {'correct' if ok else 'incorrect'}!")
    return ok


# ============================================================
# TEST 3: Full cascade with attraction
# ============================================================
def test_full_cascade_with_attraction():
    print("\n" + "=" * 60)
    print("TEST 3: Full process_move cascade producing attraction")
    print("=" * 60)

    svc = make_board_service()

    # Design a board where:
    # - A move creates a 3-in-a-row match (triggering cascade)
    # - After match clear + gravity + fill, two specials end up 2 apart
    #
    # Simpler approach: pre-place two specials 2 apart and make a move
    # that matches elsewhere. After that match resolves, the cascade loop
    # will check for attractions on the NEXT iteration (when no more matches).
    #
    # Row 0: a match-3 waiting to happen with one swap.
    # Row 5: two specials with a regular gem between.

    grid = np.array([
        [1, 1, 2, 1, 5, 6, 5, 6],  # swap (0,1)<->(0,2) makes 1,1,1
        [2, 3, 4, 5, 6, 5, 6, 5],
        [3, 4, 5, 6, 5, 6, 5, 6],
        [4, 5, 6, 5, 6, 5, 6, 5],
        [5, 6, 5, 6, 5, 6, 5, 6],
        [6, 5, 1, 2, 3, 6, 5, 6],  # specials at (5,2) and (5,4)
        [5, 6, 5, 6, 5, 6, 5, 6],
        [6, 5, 6, 5, 6, 5, 6, 5],
    ], dtype=np.int8)

    func_grid = np.zeros((8, 8), dtype=np.int8)
    func_grid[5, 2] = int(GemFunction.LINE_BLAST_V)   # 2
    func_grid[5, 4] = int(GemFunction.CHROMATIC_ORB)   # 4

    board = BoardState(grid=grid, func_grid=func_grid)
    print_board(board, "Board before move")

    # Move: swap (0,1) and (0,2) — makes row 0 cols 0,1,2 all color 1 (match-3).
    # But wait — swapping makes (0,2) become 1, giving [1,1,1,...] — that's a match.
    # Actually, (0,0)=1, (0,1)=1, (0,2)=2. Swapping (0,2)<->(0,1) gives:
    #   (0,0)=1, (0,1)=2, (0,2)=1 — NOT a match.
    # Let me reconsider. Swap (0,2) with (0,3):
    #   before: [1, 1, 2, 1, ...] -> after: [1, 1, 1, 2, ...] — match-3 at (0,0)-(0,1)-(0,2)!

    move = Move(from_pos=Position(0, 2), to_pos=Position(0, 3), timestamp_ms=0)
    print(f"  Move: swap ({move.from_pos.row},{move.from_pos.col}) <-> ({move.to_pos.row},{move.to_pos.col})")

    result = svc.process_move(board, move, seed=42)

    print(f"\n  Result: valid={result.was_valid_match}, cascades={len(result.cascades)}")

    attraction_found = False
    for i, step in enumerate(result.cascades):
        n_removals = len([pos for mg in step.matches.matches for pos in mg.positions])
        n_attractions = len(step.special_attractions)
        n_activations = len(step.special_activations)
        print(f"    Step {step.step_number}: matches={len(step.matches.matches)} "
              f"removals={n_removals} attractions={n_attractions} activations={n_activations}")
        if n_attractions > 0:
            attraction_found = True
            for att in step.special_attractions:
                print(f"      ATTRACTION: ({att.pos_a.row},{att.pos_a.col})[func={int(att.func_a)}] + "
                      f"({att.pos_b.row},{att.pos_b.col})[func={int(att.func_b)}] -> "
                      f"center=({att.center_pos.row},{att.center_pos.col}) mega={att.mega_func}")

    # Check the final board for mega gems.
    final = result.final_board
    print(f"\n  Final func_grid scan for mega gems:")
    found_mega = False
    for r in range(final.height):
        for c in range(final.width):
            fv = int(final.func_grid[r, c])
            if fv != 0:
                print(f"    ({r},{c}) func={fv} {'MEGA' if is_mega_gem(fv) else 'SPECIAL'} color={int(final.grid[r, c])}")
                if is_mega_gem(fv):
                    found_mega = True

    if attraction_found:
        print("  PASS: Attraction found in cascade!")
    else:
        print("  FAIL: No attraction found in cascade steps.")
        # Check if specials survived or were consumed by gravity/fill.
        print("\n  Diagnosing: checking if specials survived the cascade...")
        for step_idx, step in enumerate(result.cascades):
            after = step.board_after_fill
            for r in range(after.height):
                for c in range(after.width):
                    fv = int(after.func_grid[r, c])
                    if fv != 0:
                        print(f"    After step {step_idx+1}: ({r},{c}) func={fv} color={int(after.grid[r, c])}")

    return attraction_found


# ============================================================
# TEST 4: Direct unit test — attraction on a no-match board
# ============================================================
def test_attraction_in_cascade_loop():
    """Call process_move on a board that has no matches after the first one,
    but two specials 2 apart. The cascade loop should detect and process them."""
    print("\n" + "=" * 60)
    print("TEST 4: Cascade loop attraction (isolated)")
    print("=" * 60)

    svc = make_board_service()

    # Craft a board where:
    # - Swapping (0,2)<->(0,3) creates exactly [1,1,1] in row 0
    # - No other matches exist (careful color placement)
    # - Two specials at (5,2) and (5,4) with regular gem at (5,3)
    # - After clear+gravity+fill of the match, the specials stay untouched
    #   (they're far from the match area)

    # 6-color no-match grid. Each row offset by 2, guaranteeing no 3-in-a-row
    # horizontally (sequential different) or vertically (col cycles 1,3,5 or 2,4,6).
    # Row 0 is specially modified so swap (0,2)<->(0,3) creates match-3 of color 1.
    base = np.array([
        [1, 1, 3, 1, 5, 6, 1, 2],  # row 0: swap (0,2)<->(0,3) -> [1,1,1,3,5,6,1,2]
        [3, 4, 5, 6, 1, 2, 3, 4],
        [5, 6, 1, 2, 3, 4, 5, 6],
        [2, 1, 4, 3, 6, 5, 2, 1],  # shifted differently to break col patterns
        [4, 3, 6, 5, 2, 1, 4, 3],
        [6, 5, 2, 4, 1, 3, 6, 5],  # specials at (5,2)=func1 and (5,4)=func3, center (5,3)=regular
        [1, 2, 4, 5, 6, 3, 1, 2],  # different shift to break verticals with row 5
        [3, 4, 6, 1, 2, 5, 3, 4],  # different shift to break verticals with row 6
    ], dtype=np.int8)

    func_grid = np.zeros((8, 8), dtype=np.int8)
    func_grid[5, 2] = int(GemFunction.LINE_BLAST_H)   # 1
    func_grid[5, 4] = int(GemFunction.RADIAL_BOMB)     # 3

    board = BoardState(grid=base, func_grid=func_grid)
    print_board(board, "Board before move")

    # First verify attraction detection on this board directly.
    pairs = BoardService._check_special_attractions(board)
    print(f"  Pre-move attraction pairs: {len(pairs)}")
    for a, b, c in pairs:
        print(f"    ({a.row},{a.col}) + ({b.row},{b.col}) -> center ({c.row},{c.col})")

    move = Move(from_pos=Position(0, 2), to_pos=Position(0, 3), timestamp_ms=0)
    print(f"\n  Move: swap (0,2)<->(0,3)")

    # Verify the swap creates a match.
    swapped_grid = board.grid.copy()
    swapped_grid[0, 2], swapped_grid[0, 3] = swapped_grid[0, 3], swapped_grid[0, 2]
    print(f"  After swap row 0: {[int(swapped_grid[0, c]) for c in range(8)]}")
    swapped = BoardState(grid=swapped_grid, func_grid=board.func_grid.copy())
    matches = svc.detect_matches(swapped)
    print(f"  Matches detected after swap: {len(matches.matches)}")
    for mg in matches.matches:
        positions = [(p.row, p.col) for p in mg.positions]
        print(f"    Match: color={int(mg.gem_type)} positions={positions}")

    result = svc.process_move(board, move, seed=12345)

    print(f"\n  Result: valid={result.was_valid_match}, cascades={len(result.cascades)}")

    attraction_found = False
    for i, step in enumerate(result.cascades):
        n_matches = len(step.matches.matches)
        n_att = len(step.special_attractions)
        n_act = len(step.special_activations)
        print(f"    Step {step.step_number}: matches={n_matches} attractions={n_att} activations={n_act}")
        if n_att > 0:
            attraction_found = True
            for att in step.special_attractions:
                print(f"      ATTRACTION: ({att.pos_a.row},{att.pos_a.col})[{int(att.func_a)}] + "
                      f"({att.pos_b.row},{att.pos_b.col})[{int(att.func_b)}] -> "
                      f"({att.center_pos.row},{att.center_pos.col}) mega={att.mega_func}")

        # Print board state after each step.
        after = step.board_after_fill
        specials_in_step = []
        for r in range(after.height):
            for c in range(after.width):
                fv = int(after.func_grid[r, c])
                if fv != 0:
                    specials_in_step.append((r, c, fv))
        if specials_in_step:
            print(f"      Specials remaining: {specials_in_step}")

    final = result.final_board
    print(f"\n  Final board specials:")
    for r in range(final.height):
        for c in range(final.width):
            fv = int(final.func_grid[r, c])
            if fv != 0:
                label = "MEGA" if is_mega_gem(fv) else "SPECIAL"
                print(f"    ({r},{c}) func={fv} {label} color={int(final.grid[r, c])}")

    if attraction_found:
        print("\n  PASS: Attraction found in cascade!")
    else:
        print("\n  FAIL: No attraction in cascade.")
        print("  Possible causes:")
        print("    - Specials were consumed by gravity/fill from the match above")
        print("    - Cascade match cascaded into the specials")
        print("    - Fill spawned matching colors that created more matches over specials")

    return attraction_found


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    results = {}
    results["detection"] = test_attraction_detection()
    results["processing"] = test_attraction_processing()
    results["full_cascade"] = test_full_cascade_with_attraction()
    results["isolated_cascade"] = test_attraction_in_cascade_loop()

    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, passed in results.items():
        print(f"  {name}: {'PASS' if passed else 'FAIL'}")

    all_passed = all(results.values())
    print(f"\n  Overall: {'ALL PASSED' if all_passed else 'SOME FAILED'}")
    sys.exit(0 if all_passed else 1)
