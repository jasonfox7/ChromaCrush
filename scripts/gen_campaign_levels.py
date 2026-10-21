"""Generate 120 campaign level definitions for config/campaign_levels.json.

Run: python scripts/gen_campaign_levels.py > config/campaign_levels.json

Level ranges:
  1-50:   Original difficulty curve, basic obstacles only.
  51-60:  Invincible walls (gravity_wall, funnel, corner_walls patterns).
  61-70:  Layered shells (concentric obstacle rings + walls from 66+).
  71-80:  Obstacle spread (infection mechanic + walls from 76+).
  81-90:  Obstacle regeneration (respawning obstacles + walls from 86+).
  91-100: Combined mechanics (walls + spread + regen).
  101-120: Harder combined (all mechanics, tighter budgets).
"""

import json
import math


def _lerp(lo: int, hi: int, level: int, range_lo: int, range_hi: int) -> int:
    """Linear interpolation, rounded."""
    t = (level - range_lo) / max(1, range_hi - range_lo)
    return round(lo + t * (hi - lo))


# ---------------------------------------------------------------------------
# Difficulty curves
# ---------------------------------------------------------------------------

def _obstacle_count(level: int, is_checkpoint: bool) -> int:
    """Obstacle count curve with checkpoint spike."""
    if level <= 10:
        # 2,2,3,3,4,4,5,5,6,6
        base = 1 + (level + 1) // 2
        base = max(2, min(6, base))
    elif level <= 30:
        base = _lerp(4, 8, level, 11, 30)
    elif level <= 50:
        base = _lerp(6, 10, level, 31, 50)
    elif level <= 70:
        base = _lerp(8, 12, level, 51, 70)
    elif level <= 85:
        base = _lerp(10, 14, level, 71, 85)
    elif level <= 100:
        base = _lerp(12, 16, level, 86, 100)
    else:
        base = _lerp(10, 16, level, 101, 120)

    if is_checkpoint:
        base += 2

    return base


def _moves(level: int, is_checkpoint: bool) -> int:
    """Move budget curve with checkpoint penalty."""
    if level <= 10:
        base = _lerp(30, 25, level, 1, 10)
    elif level <= 30:
        base = _lerp(25, 22, level, 11, 30)
    elif level <= 50:
        base = _lerp(22, 20, level, 31, 50)
    elif level <= 70:
        base = _lerp(22, 20, level, 51, 70)
    elif level <= 85:
        base = _lerp(22, 18, level, 71, 85)
    elif level <= 100:
        base = _lerp(20, 16, level, 86, 100)
    else:
        base = _lerp(20, 16, level, 101, 120)

    if is_checkpoint:
        base -= 2

    return base


def _gem_colors(level: int) -> int:
    return 5 if level >= 86 else 6


def _func_pool(level: int) -> list[int]:
    """Available obstacle func values for this level range.

    Capped at func 0-3 (glass, H-blast, V-blast, radial bomb).
    Chromatic orb (func=4) excluded because its blast only targets
    same-color gems and can never reach obstacles (color=7).
    """
    if level <= 10:
        return [0]
    elif level <= 20:
        return [0, 0, 0, 1]          # 70/30 glass vs LINE_H
    elif level <= 30:
        return [0, 0, 1, 2]          # 50/25/25
    elif level <= 50:
        return [0, 1, 2, 3]          # ~25% each
    elif level <= 70:
        return [0, 1, 2, 3]          # 25% each
    elif level <= 85:
        return [0, 1, 1, 2, 2, 3, 3]  # 14% glass, 29% each keyed
    elif level <= 100:
        return [1, 2, 3]              # No glass, 33% each keyed
    else:
        return [1, 2, 3]              # No glass, all keyed


# ---------------------------------------------------------------------------
# Obstacle placement (original)
# ---------------------------------------------------------------------------

def _place_obstacles(level: int, count: int, func_pool: list[int]) -> list[dict]:
    """Place obstacles symmetrically on the board.

    Generate left-half positions, mirror to right half.
    Deterministic seed = level * 31.
    """
    seed = level * 31
    rng_state = seed

    def _next_rng() -> int:
        nonlocal rng_state
        # Simple LCG matching the project's style.
        rng_state = (rng_state * 1103515245 + 12345) & 0x7FFFFFFF
        return rng_state

    # Usable zone: rows 1-6, cols 1-3 (left half for mirroring).
    candidates = []
    for r in range(1, 7):
        for c in range(1, 4):
            candidates.append((r, c))

    # Shuffle candidates deterministically.
    for i in range(len(candidates) - 1, 0, -1):
        j = _next_rng() % (i + 1)
        candidates[i], candidates[j] = candidates[j], candidates[i]

    # Minimum distance constraint: Manhattan >= 2 for levels 1-30, >= 1 for 31+.
    min_dist = 2 if level <= 30 else 1

    # Pick count/2 left-half positions (pairs will mirror).
    half_count = count // 2
    has_center = count % 2 == 1  # odd count gets a center obstacle

    chosen_left: list[tuple[int, int]] = []
    for r, c in candidates:
        if len(chosen_left) >= half_count:
            break
        # Check distance from already-chosen left positions AND their mirrors.
        too_close = False
        for cr, cc in chosen_left:
            if abs(r - cr) + abs(c - cc) < min_dist:
                too_close = True
                break
            # Also check against mirror of chosen.
            mc = 7 - cc
            if abs(r - cr) + abs(c - mc) < min_dist:
                too_close = True
                break
        if not too_close:
            chosen_left.append((r, c))

    # If we couldn't get enough with distance constraint, relax and fill.
    if len(chosen_left) < half_count:
        for r, c in candidates:
            if len(chosen_left) >= half_count:
                break
            if (r, c) not in chosen_left:
                chosen_left.append((r, c))

    # Build full positions: left + mirror.
    positions: list[tuple[int, int]] = []
    for r, c in chosen_left:
        positions.append((r, c))
        positions.append((r, 7 - c))

    # Center obstacle for odd count.
    if has_center:
        # Pick from center columns (3 or 4), rows 1-6.
        center_candidates = [(r, 4) for r in range(1, 7)] + [(r, 3) for r in range(1, 7)]
        # Shuffle deterministically.
        for i in range(len(center_candidates) - 1, 0, -1):
            j = _next_rng() % (i + 1)
            center_candidates[i], center_candidates[j] = center_candidates[j], center_candidates[i]

        for r, c in center_candidates:
            if (r, c) not in positions:
                positions.append((r, c))
                break

    # Assign funcs round-robin from pool.
    obstacles = []
    for i, (r, c) in enumerate(positions):
        func = func_pool[i % len(func_pool)]
        obstacles.append({"row": r, "col": c, "func": func})

    # Sort by row then col for readability.
    obstacles.sort(key=lambda o: (o["row"], o["col"]))

    return obstacles


# ---------------------------------------------------------------------------
# Invincible wall placement (func=10)
# ---------------------------------------------------------------------------

def _place_walls(level: int, pattern: str) -> list[dict]:
    """Place invincible wall obstacles (func=10).

    Patterns:
      "gravity_wall" - Full row at row 3 with 2-col gap in center.
      "funnel"       - Two partial rows at rows 2 and 5, leaving cols 3-4 open.
      "corner_walls" - L-shaped walls in top-left and bottom-right corners.
    """
    walls = []
    if pattern == "gravity_wall":
        # Row 3, all cols except 3 and 4 (the gap).
        for c in range(8):
            if c not in (3, 4):
                walls.append({"row": 3, "col": c, "func": 10})
    elif pattern == "funnel":
        # Row 2: cols 0-1 and 6-7. Row 5: cols 0-1 and 6-7.
        for r in (2, 5):
            for c in (0, 1, 6, 7):
                walls.append({"row": r, "col": c, "func": 10})
    elif pattern == "corner_walls":
        # Top-left L: row 0 cols 0-2, row 1 col 0, row 2 col 0.
        for c in range(3):
            walls.append({"row": 0, "col": c, "func": 10})
        walls.append({"row": 1, "col": 0, "func": 10})
        walls.append({"row": 2, "col": 0, "func": 10})
        # Bottom-right L: row 7 cols 5-7, row 6 col 7, row 5 col 7.
        for c in range(5, 8):
            walls.append({"row": 7, "col": c, "func": 10})
        walls.append({"row": 6, "col": 7, "func": 10})
        walls.append({"row": 5, "col": 7, "func": 10})
    return walls


# ---------------------------------------------------------------------------
# Layered shell placement (concentric obstacle rings)
# ---------------------------------------------------------------------------

def _place_layered_shell(level: int, seed: int) -> list[dict]:
    """Concentric obstacle rings: outer ring basic glass, inner ring keyed.

    Outer ring: rows 1,6 x cols 1-6 and rows 2-5 x cols 1,6 -> func=0
    Inner ring: rows 2,5 x cols 2-5 and rows 3-4 x cols 2,5 -> func from pool
    """
    rng_state = seed

    def _next():
        nonlocal rng_state
        rng_state = (rng_state * 1103515245 + 12345) & 0x7FFFFFFF
        return rng_state

    inner_pool = [1, 2, 3]
    obstacles = []

    # Outer ring.
    outer = set()
    for c in range(1, 7):
        outer.add((1, c))
        outer.add((6, c))
    for r in range(2, 6):
        outer.add((r, 1))
        outer.add((r, 6))

    # Inner ring.
    inner = set()
    for c in range(2, 6):
        inner.add((2, c))
        inner.add((5, c))
    for r in range(3, 5):
        inner.add((r, 2))
        inner.add((r, 5))

    # Remove inner positions from outer to avoid overlap.
    outer -= inner

    for r, c in sorted(outer):
        obstacles.append({"row": r, "col": c, "func": 0})

    for r, c in sorted(inner):
        func = inner_pool[_next() % len(inner_pool)]
        obstacles.append({"row": r, "col": c, "func": func})

    return obstacles


# ---------------------------------------------------------------------------
# Spread and regen config
# ---------------------------------------------------------------------------

def _spread_config(level: int) -> dict | None:
    """Return obstacle_spread config for levels using infection."""
    if 71 <= level <= 80:
        t = (level - 71) / 9
        return {
            "chance": round(0.15 + t * 0.15, 2),   # 0.15 -> 0.30
            "func": 0,
            "max_per_turn": 1 + (level - 71) // 5,  # 1 then 2
        }
    if 91 <= level <= 100:
        return {"chance": 0.25, "func": 0, "max_per_turn": 2}
    if 101 <= level <= 120:
        t = (level - 101) / 19
        return {
            "chance": round(0.25 + t * 0.15, 2),   # 0.25 -> 0.40
            "func": 0,
            "max_per_turn": 2,
        }
    return None


def _regen_config(level: int) -> dict | None:
    """Return obstacle_regen config for levels using regeneration."""
    if 81 <= level <= 90:
        after = 8 if level <= 85 else 6
        return {"after_moves": after}
    if 91 <= level <= 100:
        return {"after_moves": 6}
    if 101 <= level <= 120:
        after = 6 if level <= 110 else 4
        return {"after_moves": after}
    return None


# ---------------------------------------------------------------------------
# Checkpoint rewards
# ---------------------------------------------------------------------------

def _checkpoint_reward(level: int) -> dict:
    """Alternating item/gold rewards for checkpoints."""
    rewards = {
        10: {"type": "card_pack", "rarity": "common", "count": 1},
        20: {"type": "gold", "amount": 1000},
        30: {"type": "card_pack", "rarity": "rare", "count": 1},
        40: {"type": "gold", "amount": 2000},
        50: {"type": "card_pack", "rarity": "epic", "count": 1},
        60: {"type": "gold", "amount": 3000},
        70: {"type": "mega_gem", "item_id": "mega_hh_10", "count": 1},
        80: {"type": "gold", "amount": 4000},
        90: {"type": "card_pack", "rarity": "legendary", "count": 1},
        100: {"type": "gold", "amount": 5000},
        110: {"type": "mega_gem", "item_id": "mega_hh_10", "count": 10},
        120: {"type": "gold", "amount": 10000},
    }
    return rewards.get(level, {"type": "gold", "amount": 1000})


# ---------------------------------------------------------------------------
# Level generation
# ---------------------------------------------------------------------------

def generate_levels() -> list[dict]:
    levels = []

    # Levels 1-50: unchanged (original difficulty curve, basic obstacles only).
    for lvl in range(1, 51):
        is_cp = lvl % 10 == 0
        count = _obstacle_count(lvl, is_cp)
        pool = _func_pool(lvl)
        obstacles = _place_obstacles(lvl, count, pool)

        entry: dict = {
            "level": lvl,
            "moves": _moves(lvl, is_cp),
            "gem_colors": _gem_colors(lvl),
            "objective": "clear_all_obstacles",
            "is_checkpoint": is_cp,
        }

        if is_cp:
            entry["heart_cost"] = 1
            entry["reward"] = _checkpoint_reward(lvl)

        entry["obstacles"] = obstacles
        levels.append(entry)

    # Levels 51-120: new mechanics phased in.
    for lvl in range(51, 121):
        is_cp = lvl % 10 == 0
        seed = lvl * 31

        entry: dict = {
            "level": lvl,
            "moves": _moves(lvl, is_cp),
            "gem_colors": _gem_colors(lvl),
            "objective": "clear_all_obstacles",
            "is_checkpoint": is_cp,
        }
        if is_cp:
            entry["heart_cost"] = 1
            entry["reward"] = _checkpoint_reward(lvl)

        pool = _func_pool(lvl)
        count = _obstacle_count(lvl, is_cp)

        # --- Determine mechanics for this level range ---

        if 51 <= lvl <= 60:
            # Introduce invincible walls. Alternate patterns.
            patterns = ["gravity_wall", "funnel", "corner_walls"]
            pattern = patterns[(lvl - 51) % len(patterns)]
            walls = _place_walls(lvl, pattern)
            clearable = _place_obstacles(lvl, count, pool)
            wall_positions = {(w["row"], w["col"]) for w in walls}
            clearable = [o for o in clearable if (o["row"], o["col"]) not in wall_positions]
            entry["obstacles"] = walls + clearable

        elif 61 <= lvl <= 70:
            # Layered shells + walls on harder levels.
            shell = _place_layered_shell(lvl, seed)
            if lvl >= 66:
                walls = _place_walls(lvl, "corner_walls")
                shell_positions = {(o["row"], o["col"]) for o in shell}
                walls = [w for w in walls if (w["row"], w["col"]) not in shell_positions]
                entry["obstacles"] = walls + shell
            else:
                entry["obstacles"] = shell

        elif 71 <= lvl <= 80:
            # Obstacle spread (infection) + walls on some levels.
            if lvl >= 76:
                walls = _place_walls(lvl, "funnel")
                clearable = _place_obstacles(lvl, max(4, count - 3), pool)
                wall_positions = {(w["row"], w["col"]) for w in walls}
                clearable = [o for o in clearable if (o["row"], o["col"]) not in wall_positions]
                entry["obstacles"] = walls + clearable
            else:
                entry["obstacles"] = _place_obstacles(lvl, count, pool)
            entry["obstacle_spread"] = _spread_config(lvl)

        elif 81 <= lvl <= 90:
            # Obstacle regeneration + walls on some levels.
            if lvl >= 86:
                walls = _place_walls(lvl, "gravity_wall")
                clearable = _place_obstacles(lvl, count, pool)
                wall_positions = {(w["row"], w["col"]) for w in walls}
                clearable = [o for o in clearable if (o["row"], o["col"]) not in wall_positions]
                entry["obstacles"] = walls + clearable
            else:
                entry["obstacles"] = _place_obstacles(lvl, count, pool)
            entry["obstacle_regen"] = _regen_config(lvl)

        elif 91 <= lvl <= 100:
            # Combined: walls + spread + regen.
            pattern = "funnel" if lvl % 2 == 1 else "gravity_wall"
            walls = _place_walls(lvl, pattern)
            clearable = _place_obstacles(lvl, count, pool)
            wall_positions = {(w["row"], w["col"]) for w in walls}
            clearable = [o for o in clearable if (o["row"], o["col"]) not in wall_positions]
            entry["obstacles"] = walls + clearable
            spread = _spread_config(lvl)
            if spread:
                entry["obstacle_spread"] = spread
            regen = _regen_config(lvl)
            if regen:
                entry["obstacle_regen"] = regen

        else:  # 101-120
            # Harder combined: all mechanics, tighter budgets.
            if lvl <= 110:
                shell = _place_layered_shell(lvl, seed)
                walls = _place_walls(lvl, "corner_walls")
                shell_positions = {(o["row"], o["col"]) for o in shell}
                walls = [w for w in walls if (w["row"], w["col"]) not in shell_positions]
                entry["obstacles"] = walls + shell
            else:
                pattern = "funnel" if lvl % 2 == 1 else "gravity_wall"
                walls = _place_walls(lvl, pattern)
                clearable = _place_obstacles(lvl, count, pool)
                wall_positions = {(w["row"], w["col"]) for w in walls}
                clearable = [o for o in clearable if (o["row"], o["col"]) not in wall_positions]
                entry["obstacles"] = walls + clearable
            spread = _spread_config(lvl)
            if spread:
                entry["obstacle_spread"] = spread
            regen = _regen_config(lvl)
            if regen:
                entry["obstacle_regen"] = regen

        entry["obstacles"].sort(key=lambda o: (o["row"], o["col"]))
        levels.append(entry)

    return levels


if __name__ == "__main__":
    levels = generate_levels()
    print(json.dumps(levels, indent=2))
