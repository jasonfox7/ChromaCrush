/// Compares old board state to new board state and produces MatchEvent sequence.
///
/// The backend returns only the FINAL board state, not intermediate cascade steps.
/// This class derives animation events by identifying survivors per column using
/// bottom-up greedy matching, then computing removal, gravity, and fill events.
library;

import '../models/match_event.dart';

class BoardDiffer {
  const BoardDiffer();

  /// Derive animation events from an old board, new board, and move info.
  ///
  /// The swap animation already played (optimistic). We sync directly to the
  /// server's final board state. This guarantees visual correctness — the
  /// greedy per-column diffing was unreliable with duplicate gem types and
  /// multi-cascade scenarios, causing wrong tiles to disappear.
  ///
  /// differ is implemented that handles cascades correctly.
  List<MatchEvent> derive({
    required List<List<int>> oldBoard,
    required List<List<int>> newBoard,
    required List<List<int>> newFunctions,
    required int fromRow,
    required int fromCol,
    required int toRow,
    required int toCol,
    required int scoreGained,
  }) {
    // Snap to final server state. The swap animation already played.
    return [BoardSyncEvent(finalBoard: newBoard, finalFunctions: newFunctions)];
  }
}
