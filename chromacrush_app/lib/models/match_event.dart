/// Backend events that drive the animation sequencer.
///
/// When a move is submitted, the backend returns a MoveResultResponse.
/// The animation sequencer decomposes this into a sequence of MatchEvents
/// that are played in order (swap, match, gravity, fill, cascade repeat).
sealed class MatchEvent {
  const MatchEvent();
}

/// Two gems swapped positions.
class SwapEvent extends MatchEvent {
  const SwapEvent({
    required this.fromRow,
    required this.fromCol,
    required this.toRow,
    required this.toCol,
  });
  final int fromRow;
  final int fromCol;
  final int toRow;
  final int toCol;
}

/// Swap was invalid — rubber-band animation back.
class InvalidSwapEvent extends MatchEvent {
  const InvalidSwapEvent({
    required this.fromRow,
    required this.fromCol,
    required this.toRow,
    required this.toCol,
  });
  final int fromRow;
  final int fromCol;
  final int toRow;
  final int toCol;
}

/// Gems matched and should be removed.
class MatchRemovalEvent extends MatchEvent {
  const MatchRemovalEvent({required this.positions, required this.scoreGained});
  final List<({int row, int col})> positions;
  final int scoreGained;
}

/// Gems fell due to gravity.
class GravityEvent extends MatchEvent {
  const GravityEvent({required this.drops});
  final List<({int fromRow, int fromCol, int toRow, int toCol})> drops;
}

/// New gems spawned to fill empty cells.
class FillEvent extends MatchEvent {
  const FillEvent({required this.spawns});
  final List<({int row, int col, int gemType})> spawns;
}

/// A special gem was created.
class SpecialGemCreatedEvent extends MatchEvent {
  const SpecialGemCreatedEvent({
    required this.row,
    required this.col,
    required this.gemType,
    required this.color,
  });
  final int row;
  final int col;
  final int gemType;
  final int color;
}

/// A special gem was activated.
class SpecialGemActivatedEvent extends MatchEvent {
  const SpecialGemActivatedEvent({
    required this.row,
    required this.col,
    required this.gemType,
  });
  final int row;
  final int col;
  final int gemType;
}

/// Two special gems attracted toward a center gem, forming a mega gem.
class SpecialAttractionEvent extends MatchEvent {
  const SpecialAttractionEvent({
    required this.posARow,
    required this.posACol,
    required this.posBRow,
    required this.posBCol,
    required this.centerRow,
    required this.centerCol,
    required this.megaFunc,
  });

  final int posARow;
  final int posACol;
  final int posBRow;
  final int posBCol;
  final int centerRow;
  final int centerCol;
  final int megaFunc;
}

/// The board should sync to final server state (visual sync invariant).
class BoardSyncEvent extends MatchEvent {
  const BoardSyncEvent({
    required this.finalBoard,
    required this.finalFunctions,
  });
  final List<List<int>> finalBoard;
  final List<List<int>> finalFunctions;
}
