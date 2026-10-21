import 'package:flutter_test/flutter_test.dart';
import 'package:chromacrush_app/game/input_handler.dart';

void main() {
  group('InputHandler', () {
    late InputHandler handler;
    final swaps = <(int, int, int, int)>[];
    int? lastSelRow;
    int? lastSelCol;

    setUp(() {
      swaps.clear();
      lastSelRow = null;
      lastSelCol = null;
      handler = InputHandler(
        onSwap: (fr, fc, tr, tc) => swaps.add((fr, fc, tr, tc)),
      );
      handler.onSelectionChanged = (r, c) {
        lastSelRow = r;
        lastSelCol = c;
      };
    });

    test('starts in idle state', () {
      expect(handler.state, InputState.idle);
      expect(handler.selectedRow, isNull);
      expect(handler.selectedCol, isNull);
    });

    test('tap selects gem in idle state', () {
      handler.onGemTapped(3, 4);
      expect(handler.state, InputState.selected);
      expect(handler.selectedRow, 3);
      expect(handler.selectedCol, 4);
      expect(lastSelRow, 3);
      expect(lastSelCol, 4);
    });

    test('tap same gem deselects', () {
      handler.onGemTapped(3, 4);
      handler.onGemTapped(3, 4);
      expect(handler.state, InputState.idle);
      expect(handler.selectedRow, isNull);
      expect(lastSelRow, isNull);
    });

    test('tap adjacent commits swap', () {
      handler.onGemTapped(3, 4);
      handler.onGemTapped(3, 5); // adjacent (same row, col+1)
      expect(handler.state, InputState.swapping);
      expect(swaps.length, 1);
      expect(swaps[0], (3, 4, 3, 5));
    });

    test('tap non-adjacent selects new gem', () {
      handler.onGemTapped(3, 4);
      handler.onGemTapped(6, 6); // not adjacent
      expect(handler.state, InputState.selected);
      expect(handler.selectedRow, 6);
      expect(handler.selectedCol, 6);
      expect(swaps, isEmpty);
    });

    test('tap ignored during swapping state', () {
      handler.onGemTapped(3, 4);
      handler.onGemTapped(3, 5); // swap
      handler.onGemTapped(0, 0); // should be ignored
      expect(swaps.length, 1);
    });

    test('tap ignored during animating state', () {
      handler.state = InputState.animating;
      handler.onGemTapped(0, 0);
      expect(swaps, isEmpty);
    });

    test('drag right commits swap', () {
      handler.onDragComplete(3, 4, 30.0, 0.0);
      expect(swaps.length, 1);
      expect(swaps[0], (3, 4, 3, 5));
    });

    test('drag left commits swap', () {
      handler.onDragComplete(3, 4, -30.0, 0.0);
      expect(swaps.length, 1);
      expect(swaps[0], (3, 4, 3, 3));
    });

    test('drag down commits swap', () {
      handler.onDragComplete(3, 4, 0.0, 30.0);
      expect(swaps.length, 1);
      expect(swaps[0], (3, 4, 4, 4));
    });

    test('drag up commits swap', () {
      handler.onDragComplete(3, 4, 0.0, -30.0);
      expect(swaps.length, 1);
      expect(swaps[0], (3, 4, 2, 4));
    });

    test('drag below threshold is ignored', () {
      handler.onDragComplete(3, 4, 10.0, 5.0);
      expect(swaps, isEmpty);
    });

    test('drag out of bounds is ignored', () {
      handler.onDragComplete(0, 0, 0.0, -30.0); // drag up from row 0
      expect(swaps, isEmpty);
    });

    test('onAnimationComplete resets to idle', () {
      handler.onGemTapped(3, 4);
      handler.onGemTapped(3, 5); // swap → swapping state
      handler.onAnimationComplete();
      expect(handler.state, InputState.idle);
    });
  });
}
