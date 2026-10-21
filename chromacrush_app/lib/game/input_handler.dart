/// Gesture state machine for board interaction.
///
/// States: idle → selected → swapping → animating.
/// Handles tap-to-select, tap-adjacent-to-swap, and drag-to-swap.
library;

import '../config/game_config.dart';
import '../extensions/grid_math.dart';

/// Input handler state.
enum InputState { idle, selected, swapping, animating }

/// Callback for when a swap gesture is committed.
typedef SwapCallback =
    void Function(int fromRow, int fromCol, int toRow, int toCol);

/// Callback to check if a cell is an obstacle (Campaign mode).
typedef IsObstacleCallback = bool Function(int row, int col);

class InputHandler {
  InputHandler({required this.onSwap, this.isObstacle});

  InputState state = InputState.idle;
  int? selectedRow;
  int? selectedCol;

  /// Called when a swap is committed.
  final SwapCallback onSwap;

  /// Optional obstacle check — blocks gestures involving obstacle cells.
  /// Wired by CampaignGame; null in standard ChromaCrushGame (no obstacles).
  final IsObstacleCallback? isObstacle;

  /// Called when selection changes (for visual highlight).
  void Function(int? row, int? col)? onSelectionChanged;

  /// Handle a gem tap.
  void onGemTapped(int row, int col) {
    // Block taps on obstacle cells.
    if (isObstacle != null && isObstacle!(row, col)) return;

    switch (state) {
      case InputState.idle:
        _select(row, col);

      case InputState.selected:
        if (row == selectedRow && col == selectedCol) {
          // Tap same gem → deselect.
          _deselect();
        } else if (isAdjacent(selectedRow!, selectedCol!, row, col)) {
          // Tap adjacent → commit swap.
          _commitSwap(selectedRow!, selectedCol!, row, col);
        } else {
          // Tap non-adjacent → select new.
          _deselect();
          _select(row, col);
        }

      case InputState.swapping:
      case InputState.animating:
        // Ignore taps during animation.
        break;
    }
  }

  /// Handle a drag gesture completing.
  /// [startRow]/[startCol] is where the drag started.
  /// [deltaX]/[deltaY] is the total drag distance.
  void onDragComplete(
    int startRow,
    int startCol,
    double deltaX,
    double deltaY,
  ) {
    if (state == InputState.swapping || state == InputState.animating) return;

    // Block drags starting on obstacle cells.
    if (isObstacle != null && isObstacle!(startRow, startCol)) return;

    // Require minimum drag threshold.
    final absX = deltaX.abs();
    final absY = deltaY.abs();

    if (absX < kSwipeThreshold && absY < kSwipeThreshold) return;

    int toRow = startRow;
    int toCol = startCol;

    if (absX > absY) {
      // Horizontal drag.
      toCol = deltaX > 0 ? startCol + 1 : startCol - 1;
    } else {
      // Vertical drag.
      toRow = deltaY > 0 ? startRow + 1 : startRow - 1;
    }

    // Bounds check.
    if (toRow < 0 || toRow >= kBoardSize || toCol < 0 || toCol >= kBoardSize) {
      return;
    }

    // Block drags targeting obstacle cells.
    if (isObstacle != null && isObstacle!(toRow, toCol)) return;

    _deselect();
    _commitSwap(startRow, startCol, toRow, toCol);
  }

  /// Called when animations complete and input can resume.
  void onAnimationComplete() {
    state = InputState.idle;
  }

  void _select(int row, int col) {
    selectedRow = row;
    selectedCol = col;
    state = InputState.selected;
    onSelectionChanged?.call(row, col);
  }

  void _deselect() {
    selectedRow = null;
    selectedCol = null;
    state = InputState.idle;
    onSelectionChanged?.call(null, null);
  }

  void _commitSwap(int fromRow, int fromCol, int toRow, int toCol) {
    state = InputState.swapping;
    onSelectionChanged?.call(null, null);
    onSwap(fromRow, fromCol, toRow, toCol);
  }
}
