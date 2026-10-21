/// 8x8 gem grid — renders and animates the game board.
///
/// Positioned as a child of ChromaCrushGame. Manages gem creation, layout,
/// swap animations, removal, gravity, and board sync.
library;

import 'dart:async';

import 'package:flame/components.dart';
import 'package:flame/effects.dart';
import 'package:flame/events.dart';

import '../config/animation_timings.dart';
import '../config/visual_theme_service.dart';
import '../extensions/grid_math.dart';
import '../models/backend_contract.dart';
import '../models/gem_type.dart';
import 'gem_component.dart';

class BoardLayer extends PositionComponent with DragCallbacks {
  BoardLayer({
    this.onGemTapped,
    this.onDragGesture,
    required this.theme,
    required this.layout,
  });

  final VisualThemeBase theme;
  final BoardLayout layout;

  /// 8x8 grid of gem components. Null = empty cell.
  final List<List<GemComponent?>> gems = List.generate(
    kBoardSize,
    (_) => List<GemComponent?>.filled(kBoardSize, null),
  );

  /// Callback when a gem is tapped.
  void Function(int row, int col)? onGemTapped;

  /// Callback when a drag gesture completes (raw pixel delta).
  void Function(int startRow, int startCol, double deltaX, double deltaY)?
  onDragGesture;

  // Drag tracking
  ({int row, int col})? _dragStartGrid;
  Vector2 _dragDelta = Vector2.zero();

  @override
  Future<void> onLoad() async {
    size = Vector2(layout.boardExtent, layout.boardExtent);
  }

  // ---------------------------------------------------------------------------
  // Board population
  // ---------------------------------------------------------------------------

  /// Populate the board from a backend BoardStateResponse.
  void loadBoard(BoardStateResponse board) {
    // Remove all existing gems.
    for (var r = 0; r < kBoardSize; r++) {
      for (var c = 0; c < kBoardSize; c++) {
        gems[r][c]?.removeFromParent();
        gems[r][c] = null;
      }
    }

    // Create new gems with color and function.
    for (var r = 0; r < kBoardSize; r++) {
      for (var c = 0; c < kBoardSize; c++) {
        final gemType = GemType.fromValue(board.cells[r][c]);
        if (!gemType.isEmpty) {
          final rawFunc = board.functions[r][c];
          final func = GemFunction.fromValue(rawFunc);
          _createGem(r, c, gemType, func, rawFunc);
        }
      }
    }
  }

  /// Snap all gems to match the server board state (visual sync invariant).
  ///
  /// Also removes orphaned GemComponents that are still in the Flame tree
  /// but no longer tracked in the [gems] grid (e.g. from animation drift).
  void syncToBoard(List<List<int>> cells, List<List<int>> functions) {
    // Collect currently tracked gems so we can detect orphans.
    final tracked = <GemComponent>{};
    for (var r = 0; r < kBoardSize; r++) {
      for (var c = 0; c < kBoardSize; c++) {
        final g = gems[r][c];
        if (g != null) tracked.add(g);
      }
    }

    // Sync grid to server state — type and function always in lock step.
    for (var r = 0; r < kBoardSize; r++) {
      for (var c = 0; c < kBoardSize; c++) {
        final serverType = GemType.fromValue(cells[r][c]);
        final rawFunc = functions[r][c];
        final serverFunc = GemFunction.fromValue(rawFunc);
        final existing = gems[r][c];

        if (serverType.isEmpty) {
          existing?.removeFromParent();
          gems[r][c] = null;
        } else if (existing == null) {
          _createGem(r, c, serverType, serverFunc, rawFunc);
        } else {
          if (existing.gemType != serverType) {
            existing.updateGemType(serverType);
          }
          if (existing.rawFunction != rawFunc) {
            existing.updateGemFunction(serverFunc, raw: rawFunc);
          }
        }
        // Snap position and reset visual state.
        final gem = gems[r][c];
        if (gem != null) {
          gem.position = layout.gridToPosition(r, c);
          gem.updateGridPosition(r, c);
          gem.scale = Vector2.all(1.0);
        }
      }
    }

    // Remove orphaned GemComponents still in the tree but not in the grid.
    final nowTracked = <GemComponent>{};
    for (var r = 0; r < kBoardSize; r++) {
      for (var c = 0; c < kBoardSize; c++) {
        final g = gems[r][c];
        if (g != null) nowTracked.add(g);
      }
    }
    for (final child in children.toList()) {
      if (child is GemComponent && !nowTracked.contains(child)) {
        child.removeFromParent();
      }
    }
  }

  GemComponent? gemAt(int row, int col) {
    if (row < 0 || row >= kBoardSize || col < 0 || col >= kBoardSize) {
      return null;
    }
    return gems[row][col];
  }

  // ---------------------------------------------------------------------------
  // Animation methods
  // ---------------------------------------------------------------------------

  /// Animate swapping two gems.
  Future<void> animateSwap(
    int fromRow,
    int fromCol,
    int toRow,
    int toCol, {
    Duration duration = kSwapDuration,
  }) async {
    final gemA = gems[fromRow][fromCol];
    final gemB = gems[toRow][toCol];
    if (gemA == null && gemB == null) return;

    final posA = layout.gridToPosition(fromRow, fromCol);
    final posB = layout.gridToPosition(toRow, toCol);

    final futures = <Future<void>>[];
    if (gemA != null) futures.add(gemA.animateMoveTo(posB, duration: duration));
    if (gemB != null) futures.add(gemB.animateMoveTo(posA, duration: duration));
    await Future.wait(futures);

    // Update grid references.
    gems[fromRow][fromCol] = gemB;
    gems[toRow][toCol] = gemA;
    gemA?.updateGridPosition(toRow, toCol);
    gemB?.updateGridPosition(fromRow, fromCol);
  }

  /// Animate removal (scale+fade) of gems at given positions.
  ///
  /// Obstacles get a distinct shatter animation (brief scale-up crack
  /// then fast collapse) while standard gems use the normal scale-to-zero.
  Future<void> animateRemoval(
    List<({int row, int col})> positions, {
    Duration duration = kBoardRemovalDuration,
  }) async {
    final futures = <Future<void>>[];
    for (final pos in positions) {
      final gem = gems[pos.row][pos.col];
      if (gem != null) {
        if (gem.gemType.isObstacle) {
          futures.add(_animateObstacleShatter(gem, duration));
        } else {
          futures.add(gem.animateRemoval(duration: duration));
        }
        gems[pos.row][pos.col] = null;
      }
    }
    await Future.wait(futures);
  }

  /// Obstacle shatter: brief scale-up crack then fast collapse to zero.
  Future<void> _animateObstacleShatter(
    GemComponent gem,
    Duration totalDuration,
  ) {
    final completer = Completer<void>();
    final crackMs = (totalDuration.inMilliseconds * 0.25).round();
    final collapseMs = totalDuration.inMilliseconds - crackMs;
    // Phase 1: scale up slightly (crack).
    gem.add(
      ScaleEffect.to(
        Vector2.all(1.15),
        EffectController(duration: crackMs / 1000.0),
        onComplete: () {
          // Phase 2: collapse to zero and remove.
          gem.add(
            ScaleEffect.to(
              Vector2.zero(),
              EffectController(duration: collapseMs / 1000.0),
              onComplete: () {
                gem.removeFromParent();
                completer.complete();
              },
            ),
          );
        },
      ),
    );
    return completer.future;
  }

  /// Animate gems dropping to new positions.
  ///
  /// Uses a snapshot approach: all gem references are resolved before any
  /// grid mutation, preventing drops from overwriting each other's slots.
  Future<void> animateDrops(
    List<({int fromRow, int fromCol, int toRow, int toCol})> drops, {
    Duration durationPerRow = kBoardDropPerRowDuration,
  }) async {
    // Phase 1: Snapshot — resolve every gem reference before mutating the grid.
    final resolved = <int, GemComponent>{};
    for (var i = 0; i < drops.length; i++) {
      final drop = drops[i];
      final gem = gems[drop.fromRow][drop.fromCol];
      if (gem != null) {
        resolved[i] = gem;
      }
    }

    // Phase 2: Clear all source slots.
    for (final drop in drops) {
      gems[drop.fromRow][drop.fromCol] = null;
    }

    // Phase 3: Place gems at destinations and start animations.
    final futures = <Future<void>>[];
    for (var i = 0; i < drops.length; i++) {
      final gem = resolved[i];
      if (gem == null) continue;
      final drop = drops[i];

      // Snap to expected pre-drop position (prevents visual drift).
      gem.position = layout.gridToPosition(drop.fromRow, drop.fromCol);

      final rowDist = (drop.toRow - drop.fromRow).abs();
      final dur = Duration(
        milliseconds: durationPerRow.inMilliseconds * rowDist,
      );
      final target = layout.gridToPosition(drop.toRow, drop.toCol);

      futures.add(gem.animateMoveToElastic(target, duration: dur));
      gems[drop.toRow][drop.toCol] = gem;
      gem.updateGridPosition(drop.toRow, drop.toCol);
    }
    await Future.wait(futures);
  }

  /// Animate new gems appearing (spawned to fill empty cells).
  Future<void> animateFill(
    List<({int row, int col, int gemType})> spawns, {
    Duration duration = kBoardFillDuration,
  }) async {
    // Create all gems first, then wait for them to mount in the Flame tree
    // before starting scale animations. Effects added to not-yet-mounted
    // components don't advance until the lifecycle catches up, which can
    // leave gems stuck at scale 0 during multi-step cascades.
    final newGems = <GemComponent>[];
    for (final spawn in spawns) {
      final type = GemType.fromValue(spawn.gemType);
      newGems.add(_createGem(spawn.row, spawn.col, type));
    }
    if (newGems.isEmpty) return;
    await Future.wait([for (final g in newGems) g.loaded]);
    await Future.wait([
      for (final g in newGems) g.animateAppear(duration: duration),
    ]);
  }

  /// Flash gems at given positions bright white (chromatic conversion combos).
  ///
  /// Sets the flash overlay on each gem. The caller is responsible for
  /// timing (hold duration) and the gems will be removed by the subsequent
  /// removal animation, clearing the flash naturally.
  void flashPositions(List<({int row, int col})> positions) {
    for (final pos in positions) {
      gems[pos.row][pos.col]?.setFlashOverlay(1.0);
    }
  }

  /// Place a special gem at the given position, removing any existing gem there.
  ///
  /// Returns the new GemComponent (ready for animateAppear) or null if the
  /// color type is empty.
  GemComponent? placeSpecialGem(
    int row,
    int col,
    GemType colorType,
    GemFunction func,
  ) {
    if (colorType.isEmpty) return null;
    // Remove whatever was there (should already be null after removal animation).
    gems[row][col]?.removeFromParent();
    gems[row][col] = null;
    return _createGem(row, col, colorType, func);
  }

  // ---------------------------------------------------------------------------
  // Drag gestures
  // ---------------------------------------------------------------------------

  @override
  void onDragStart(DragStartEvent event) {
    super.onDragStart(event);
    _dragStartGrid = layout.positionToGrid(event.localPosition);
    _dragDelta = Vector2.zero();
  }

  @override
  void onDragUpdate(DragUpdateEvent event) {
    _dragDelta += event.localDelta;
  }

  @override
  void onDragEnd(DragEndEvent event) {
    super.onDragEnd(event);
    final startGrid = _dragStartGrid;
    final delta = _dragDelta;
    _dragStartGrid = null;
    _dragDelta = Vector2.zero();

    if (startGrid == null) return;
    onDragGesture?.call(startGrid.row, startGrid.col, delta.x, delta.y);
  }

  @override
  void onDragCancel(DragCancelEvent event) {
    super.onDragCancel(event);
    _dragStartGrid = null;
    _dragDelta = Vector2.zero();
  }

  // ---------------------------------------------------------------------------
  // Private helpers
  // ---------------------------------------------------------------------------

  /// Animate a special attraction: two specials transfer their function to
  /// the center gem, which becomes a mega gem. No gems are removed.
  Future<void> animateAttraction({
    required int posARow,
    required int posACol,
    required int posBRow,
    required int posBCol,
    required int centerRow,
    required int centerCol,
    required int megaFunc,
  }) async {
    final gemA = gems[posARow][posACol];
    final gemB = gems[posBRow][posBCol];
    final gemCenter = gems[centerRow][centerCol];

    // Pulse on source gems (~300ms) to highlight the attraction.
    final futures = <Future<void>>[];
    if (gemA != null) {
      futures.add(gemA.animatePulse(duration: kAttractionPulseDuration));
    }
    if (gemB != null) {
      futures.add(gemB.animatePulse(duration: kAttractionPulseDuration));
    }
    await Future.wait(futures);

    // Strip special from sources, apply mega to center.
    gemA?.updateGemFunction(GemFunction.neutral);
    gemB?.updateGemFunction(GemFunction.neutral);
    if (gemCenter != null) {
      final dominant = GemFunction.fromValue(megaFunc);
      gemCenter.updateGemFunction(dominant, raw: megaFunc);
    }

    // Pulse on center gem (~250ms) to show the merge result.
    if (gemCenter != null) {
      await gemCenter.animatePulse(duration: kAttractionResultPulseDuration);
    }
  }

  GemComponent _createGem(
    int row,
    int col,
    GemType type, [
    GemFunction func = GemFunction.neutral,
    int? rawFunc,
  ]) {
    final gem = GemComponent(
      gemType: type,
      gridRow: row,
      gridCol: col,
      theme: theme,
      cellSize: layout.cellSize,
      initialPosition: layout.gridToPosition(row, col),
      gemFunction: func,
      rawFunc: rawFunc ?? func.value,
      onTap: (r, c) => onGemTapped?.call(r, c),
    );
    // Remove any gem at this position — either tracked in the grid or
    // orphaned in the Flame tree (still animating its removal after the
    // grid reference was already nulled by animateRemoval).
    gems[row][col]?.removeFromParent();
    for (final child in children.toList()) {
      if (child is GemComponent &&
          child != gem &&
          child.gridRow == row &&
          child.gridCol == col) {
        child.removeFromParent();
      }
    }
    gems[row][col] = gem;
    add(gem);
    return gem;
  }
}
