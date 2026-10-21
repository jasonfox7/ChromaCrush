/// Stream-based pub/sub for cross-layer communication.
///
/// Decouples Flame game scene from Flutter widgets.
/// No retained state — fire and forget. Subscribers manage their own state.
library;

import 'dart:async';

/// Base class for all game events.
sealed class GameEvent {
  const GameEvent();
}

/// Score updated during gameplay.
class ScoreUpdatedEvent extends GameEvent {
  const ScoreUpdatedEvent({required this.newScore, required this.delta});
  final int newScore;
  final int delta;
}

/// Moves remaining changed.
class MovesUpdatedEvent extends GameEvent {
  const MovesUpdatedEvent({required this.movesRemaining});
  final int movesRemaining;
}

/// Chain cascade completed.
class ChainCompletedEvent extends GameEvent {
  const ChainCompletedEvent({
    required this.chainLength,
    required this.totalScore,
  });
  final int chainLength;
  final int totalScore;
}

/// Match ended.
class MatchEndedEvent extends GameEvent {
  const MatchEndedEvent({
    required this.matchId,
    required this.won,
    required this.myScore,
    required this.opponentScore,
  });
  final String matchId;
  final bool? won;
  final int myScore;
  final int opponentScore;
}

/// Energy state changed.
class EnergyChangedEvent extends GameEvent {
  const EnergyChangedEvent({
    required this.currentHearts,
    required this.maxHearts,
  });
  final int currentHearts;
  final int maxHearts;
}

/// Bot opponent score updated.
class BotScoreUpdatedEvent extends GameEvent {
  const BotScoreUpdatedEvent({required this.botScore, required this.delta});
  final int botScore;
  final int delta;
}

/// Intensity level changed (0.0–1.0).
class IntensityChangedEvent extends GameEvent {
  const IntensityChangedEvent({required this.intensity});
  final double intensity;
}

/// Campaign obstacle state changed (cleared or transmuted).
class ObstaclesUpdatedEvent extends GameEvent {
  const ObstaclesUpdatedEvent({required this.remaining, this.cleared, this.transmuted});
  final int remaining;
  final List<({int row, int col})>? cleared;
  final List<({int row, int col, int fromFunc, int toFunc})>? transmuted;
}

/// Mega gem activated from inventory (slots 0-3 = mega, slot 4 = shuffle).
class MegaActivatedEvent extends GameEvent {
  const MegaActivatedEvent({
    required this.slotIndex,
    required this.scoreGained,
  });
  final int slotIndex;
  final int scoreGained;
}

/// Card modifiers were applied during a move.
class CardProcEvent extends GameEvent {
  const CardProcEvent({required this.cardIds});
  final List<int> cardIds;
}

/// API call is taking too long (>3 seconds).
class ConnectionSlowEvent extends GameEvent {
  const ConnectionSlowEvent();
}

/// API call completed after a slow connection event was fired.
class ConnectionRestoredEvent extends GameEvent {
  const ConnectionRestoredEvent();
}

/// Equipped card loadout loaded — consumed by GameHUD card panel.
class EquippedCardsEvent extends GameEvent {
  const EquippedCardsEvent({required this.cards});
  final List<EquippedCardInfo> cards;
}

/// Lightweight card info for HUD display.
class EquippedCardInfo {
  const EquippedCardInfo({required this.cardId, required this.rarity});
  final int cardId;
  final String rarity;
}

/// Event bus with broadcast stream.
class EventBus {
  final _controller = StreamController<GameEvent>.broadcast();

  Stream<GameEvent> get stream => _controller.stream;

  /// Listen for events of a specific type.
  Stream<T> on<T extends GameEvent>() =>
      _controller.stream.where((e) => e is T).cast<T>();

  /// Fire an event to all subscribers.
  void fire(GameEvent event) {
    if (!_controller.isClosed) {
      _controller.add(event);
    }
  }

  void dispose() {
    _controller.close();
  }
}
