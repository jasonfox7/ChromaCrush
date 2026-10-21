import 'package:flutter_test/flutter_test.dart';
import 'package:chromacrush_app/services/event_bus.dart';

void main() {
  group('EventBus', () {
    late EventBus bus;

    setUp(() {
      bus = EventBus();
    });

    tearDown(() {
      bus.dispose();
    });

    test('fire delivers event to stream listener', () async {
      const event = ScoreUpdatedEvent(newScore: 100, delta: 50);
      expectLater(bus.stream, emits(isA<ScoreUpdatedEvent>()));
      bus.fire(event);
    });

    test('on<T> filters by event type', () async {
      const scoreEvent = ScoreUpdatedEvent(newScore: 100, delta: 50);
      const movesEvent = MovesUpdatedEvent(movesRemaining: 25);

      final scoreEvents = <ScoreUpdatedEvent>[];
      bus.on<ScoreUpdatedEvent>().listen(scoreEvents.add);

      bus.fire(movesEvent);
      bus.fire(scoreEvent);

      // Allow microtask to complete.
      await Future<void>.delayed(Duration.zero);

      expect(scoreEvents.length, 1);
      expect(scoreEvents[0].newScore, 100);
    });

    test('multiple subscribers receive same event', () async {
      const event = ChainCompletedEvent(chainLength: 5, totalScore: 500);

      final sub1 = <GameEvent>[];
      final sub2 = <GameEvent>[];
      bus.stream.listen(sub1.add);
      bus.stream.listen(sub2.add);

      bus.fire(event);
      await Future<void>.delayed(Duration.zero);

      expect(sub1.length, 1);
      expect(sub2.length, 1);
    });

    test('fire after dispose does not throw', () {
      bus.dispose();
      // Should silently ignore.
      expect(
        () => bus.fire(const MovesUpdatedEvent(movesRemaining: 10)),
        returnsNormally,
      );
    });

    test('MatchEndedEvent carries all fields', () async {
      const event = MatchEndedEvent(
        matchId: 'm-1',
        won: true,
        myScore: 500,
        opponentScore: 300,
      );

      expectLater(
        bus.on<MatchEndedEvent>(),
        emits(
          predicate<MatchEndedEvent>(
            (e) =>
                e.matchId == 'm-1' &&
                e.won == true &&
                e.myScore == 500 &&
                e.opponentScore == 300,
          ),
        ),
      );
      bus.fire(event);
    });

    test('EnergyChangedEvent carries all fields', () async {
      const event = EnergyChangedEvent(currentHearts: 3, maxHearts: 5);
      expectLater(
        bus.on<EnergyChangedEvent>(),
        emits(
          predicate<EnergyChangedEvent>(
            (e) => e.currentHearts == 3 && e.maxHearts == 5,
          ),
        ),
      );
      bus.fire(event);
    });

    test('CardProcEvent carries card IDs', () async {
      const event = CardProcEvent(cardIds: [3, 12, 49]);
      expectLater(
        bus.on<CardProcEvent>(),
        emits(
          predicate<CardProcEvent>(
            (e) =>
                e.cardIds.length == 3 &&
                e.cardIds[0] == 3 &&
                e.cardIds[2] == 49,
          ),
        ),
      );
      bus.fire(event);
    });
  });
}
