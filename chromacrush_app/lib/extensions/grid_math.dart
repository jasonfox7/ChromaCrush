/// Grid coordinate ↔ screen position math.
///
/// Board: 8x8 grid. Cell size computed from screen width at runtime
/// to fit score bars + tick labels on each side.
library;

import 'package:flame/components.dart';

/// Board dimension (8x8).
const int kBoardSize = 8;

/// Spacing between gem cells.
const double kCellSpacing = 2.0;

/// Side margin per side reserved for score bars + tick labels.
/// Breakdown: bar (14) + gap (6) + tick gap (2) + tick label (~18).
const double kBoardSideMargin = 40.0;

/// Board vertical position as fraction of screen height.
const double kBoardTopFraction = 0.25;

/// Responsive board layout — computes cell size from screen dimensions.
class BoardLayout {
  BoardLayout._({
    required this.cellSize,
    required this.cellStride,
    required this.boardExtent,
    required this.boardLeft,
    required this.boardTop,
  });

  factory BoardLayout(double screenWidth, double screenHeight) {
    final available = screenWidth - kBoardSideMargin * 2;
    final cellSize = (available + kCellSpacing) / kBoardSize - kCellSpacing;
    final cellStride = cellSize + kCellSpacing;
    final boardExtent = cellStride * kBoardSize - kCellSpacing;
    final boardLeft = (screenWidth - boardExtent) / 2;
    final boardTop = screenHeight * kBoardTopFraction;
    return BoardLayout._(
      cellSize: cellSize,
      cellStride: cellStride,
      boardExtent: boardExtent,
      boardLeft: boardLeft,
      boardTop: boardTop,
    );
  }

  final double cellSize;
  final double cellStride;
  final double boardExtent;
  final double boardLeft;
  final double boardTop;

  /// Convert grid (row, col) to local position within the board layer.
  /// Row 0 is the top row; col 0 is the leftmost column.
  Vector2 gridToPosition(int row, int col) {
    return Vector2(col * cellStride, row * cellStride);
  }

  /// Convert a local position within the board layer to grid (row, col).
  /// Returns null if the position is outside the grid.
  ({int row, int col})? positionToGrid(Vector2 position) {
    final col = (position.x / cellStride).floor();
    final row = (position.y / cellStride).floor();

    if (row < 0 || row >= kBoardSize || col < 0 || col >= kBoardSize) {
      return null;
    }
    return (row: row, col: col);
  }
}

/// Check if two grid positions are adjacent (horizontally or vertically).
bool isAdjacent(int row1, int col1, int row2, int col2) {
  final dr = (row1 - row2).abs();
  final dc = (col1 - col2).abs();
  return (dr == 1 && dc == 0) || (dr == 0 && dc == 1);
}
