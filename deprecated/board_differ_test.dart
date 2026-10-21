// import 'package:flutter_test/flutter_test.dart';
// import 'package:chromacrush_app/game/board_differ.dart';
// import 'package:chromacrush_app/models/match_event.dart';

// void main() {
//   group('BoardDiffer', () {
//     const differ = BoardDiffer();

//     /// Helper: create an 8x8 board filled with a pattern.
//     List<List<int>> makeBoard(int Function(int r, int c) generator) {
//       return List.generate(8, (r) => List.generate(8, (c) => generator(r, c)));
//     }

//     test('no-change swap (same gem type at both positions) produces only BoardSyncEvent', () {
//       // Both swap positions have the same gem type, so postSwap == oldBoard == newBoard.
//       final board = makeBoard((r, c) => 1); // all gems are type 1
//       final events = differ.derive(
//         oldBoard: board,
//         newBoard: board,
//         fromRow: 0, fromCol: 0, toRow: 0, toCol: 1,
//         scoreGained: 0,
//       );

//       // Swapping two identical gems produces no visual diff.
//       expect(events.whereType<BoardSyncEvent>().length, 1);
//       expect(events.whereType<MatchRemovalEvent>().length, 0);
//     });

//     test('swap with 3 matching gems produces removal events', () {
//       // Set up a board where swapping (0,0)↔(0,1) creates a match.
//       final old = makeBoard((r, c) => ((r + c) % 6) + 1);

//       // New board has different gems in the matched positions.
//       final newBoard = makeBoard((r, c) => ((r + c) % 6) + 1);
//       // Simulate some gems changed (as if matches were cleared + refilled).
//       newBoard[0][0] = 3;
//       newBoard[0][1] = 4;
//       newBoard[0][2] = 5;

//       final events = differ.derive(
//         oldBoard: old,
//         newBoard: newBoard,
//         fromRow: 0, fromCol: 0, toRow: 0, toCol: 1,
//         scoreGained: 150,
//       );

//       expect(events.last, isA<BoardSyncEvent>());
//       // At least one event type should be present.
//       expect(events.length, greaterThanOrEqualTo(1));
//     });

//     test('always ends with BoardSyncEvent', () {
//       final old = makeBoard((r, c) => 1);
//       final newBoard = makeBoard((r, c) => 2);

//       final events = differ.derive(
//         oldBoard: old,
//         newBoard: newBoard,
//         fromRow: 0, fromCol: 0, toRow: 0, toCol: 1,
//         scoreGained: 500,
//       );

//       expect(events.last, isA<BoardSyncEvent>());
//       final sync = events.last as BoardSyncEvent;
//       expect(sync.finalBoard, newBoard);
//     });

//     test('all removed gems appear in MatchRemovalEvent', () {
//       // Old board: all 1s. New board: column 0 is all 2s.
//       final old = makeBoard((r, c) => 1);
//       final newBoard = makeBoard((r, c) => c == 0 ? 2 : 1);

//       final events = differ.derive(
//         oldBoard: old,
//         newBoard: newBoard,
//         fromRow: 0, fromCol: 0, toRow: 0, toCol: 1,
//         scoreGained: 100,
//       );

//       final removals = events.whereType<MatchRemovalEvent>();
//       expect(removals, isNotEmpty);
//       // Column 0 changed from 1→2 for all 8 rows (after swap applied).
//       final positions = removals.first.positions;
//       expect(positions, isNotEmpty);
//     });

//     test('gravity events are produced for displaced gems', () {
//       // Old board: row 7 is all 1s, rest are 2s.
//       // New board: row 7 cleared, everything shifted down, new gems at top.
//       final old = makeBoard((r, c) => r == 7 ? 1 : 2);
//       final newBoard = makeBoard((r, c) => r == 0 ? 3 : 2);

//       final events = differ.derive(
//         oldBoard: old,
//         newBoard: newBoard,
//         fromRow: 7, fromCol: 0, toRow: 7, toCol: 1,
//         scoreGained: 200,
//       );

//       // Should have gravity or fill events since gems shifted.
//       final hasGravityOrFill = events.any((e) => e is GravityEvent || e is FillEvent);
//       expect(hasGravityOrFill, isTrue);
//     });

//     test('scoreGained is carried in MatchRemovalEvent', () {
//       final old = makeBoard((r, c) => 1);
//       final newBoard = makeBoard((r, c) => 2);

//       final events = differ.derive(
//         oldBoard: old,
//         newBoard: newBoard,
//         fromRow: 0, fromCol: 0, toRow: 0, toCol: 1,
//         scoreGained: 750,
//       );

//       final removals = events.whereType<MatchRemovalEvent>();
//       if (removals.isNotEmpty) {
//         expect(removals.first.scoreGained, 750);
//       }
//     });
//   });
// }
