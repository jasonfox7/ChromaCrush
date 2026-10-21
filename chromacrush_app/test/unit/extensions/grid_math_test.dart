import 'package:flutter_test/flutter_test.dart';
import 'package:flame/components.dart';
import 'package:chromacrush_app/extensions/grid_math.dart';

void main() {
  group('BoardLayout', () {
    // iPhone 16 Pro: 414x896 logical pixels.
    late BoardLayout layout;

    setUp(() {
      layout = BoardLayout(414.0, 896.0);
    });

    test('cellSize computed from screen width minus margins', () {
      // available = 414 - 40*2 = 334
      // cellSize = (334 + 2) / 8 - 2 = 336/8 - 2 = 42 - 2 = 40
      expect(layout.cellSize, 40.0);
    });

    test('cellStride is cellSize + spacing', () {
      expect(layout.cellStride, layout.cellSize + kCellSpacing);
    });

    test('boardExtent is correct', () {
      final expected = layout.cellStride * kBoardSize - kCellSpacing;
      expect(layout.boardExtent, expected);
    });

    test('boardLeft centers the board horizontally', () {
      final expected = (414.0 - layout.boardExtent) / 2;
      expect(layout.boardLeft, expected);
    });

    test('boardTop is fraction of screen height', () {
      expect(layout.boardTop, 896.0 * kBoardTopFraction);
    });

    test('gridToPosition converts (0,0) to origin', () {
      final pos = layout.gridToPosition(0, 0);
      expect(pos.x, 0.0);
      expect(pos.y, 0.0);
    });

    test('gridToPosition converts (1,2) correctly', () {
      final pos = layout.gridToPosition(1, 2);
      expect(pos.x, 2 * layout.cellStride);
      expect(pos.y, 1 * layout.cellStride);
    });

    test('gridToPosition converts (7,7) to bottom-right', () {
      final pos = layout.gridToPosition(7, 7);
      expect(pos.x, 7 * layout.cellStride);
      expect(pos.y, 7 * layout.cellStride);
    });

    test('positionToGrid converts valid position', () {
      final result = layout.positionToGrid(
        Vector2(2 * layout.cellStride + 5, 3 * layout.cellStride + 10),
      );
      expect(result, isNotNull);
      expect(result!.row, 3);
      expect(result.col, 2);
    });

    test('positionToGrid returns null for negative position', () {
      final result = layout.positionToGrid(Vector2(-10, -10));
      expect(result, isNull);
    });

    test('positionToGrid returns null for out-of-bounds position', () {
      final result = layout.positionToGrid(Vector2(layout.boardExtent + 10, 0));
      expect(result, isNull);
    });

    test('adapts to different screen widths', () {
      final narrow = BoardLayout(360.0, 800.0);
      final wide = BoardLayout(500.0, 800.0);
      expect(wide.cellSize, greaterThan(narrow.cellSize));
      expect(wide.boardExtent, greaterThan(narrow.boardExtent));
    });
  });

  group('isAdjacent', () {
    test('returns true for horizontal neighbors', () {
      expect(isAdjacent(3, 4, 3, 5), isTrue);
      expect(isAdjacent(3, 4, 3, 3), isTrue);
    });

    test('returns true for vertical neighbors', () {
      expect(isAdjacent(3, 4, 4, 4), isTrue);
      expect(isAdjacent(3, 4, 2, 4), isTrue);
    });

    test('returns false for diagonal', () {
      expect(isAdjacent(3, 4, 4, 5), isFalse);
    });

    test('returns false for same position', () {
      expect(isAdjacent(3, 4, 3, 4), isFalse);
    });

    test('returns false for distant cells', () {
      expect(isAdjacent(0, 0, 7, 7), isFalse);
    });
  });
}
