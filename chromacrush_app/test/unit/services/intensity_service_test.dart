import 'package:chromacrush_app/services/event_bus.dart';
import 'package:chromacrush_app/services/intensity_service.dart';
import 'package:flutter_test/flutter_test.dart';

/// Let async stream events process.
Future<void> pump() => Future<void>.delayed(Duration.zero);

void main() {
  late EventBus eventBus;
  late IntensityService service;

  setUp(() {
    eventBus = EventBus();
    service = IntensityService(eventBus: eventBus);
  });

  tearDown(() {
    service.dispose();
    eventBus.dispose();
  });

  group('IntensityService', () {
    test('starts at intensity 0.0', () {
      expect(service.intensity, 0.0);
    });

    test('moves factor increases as moves decrease', () async {
      eventBus.fire(const MovesUpdatedEvent(movesRemaining: 20));
      await pump();
      expect(service.intensity, 0.0);

      eventBus.fire(const MovesUpdatedEvent(movesRemaining: 10));
      await pump();
      expect(service.intensity, closeTo(0.2, 0.05));

      eventBus.fire(const MovesUpdatedEvent(movesRemaining: 0));
      await pump();
      expect(service.intensity, closeTo(0.4, 0.05));
    });

    test('score differential factor increases when scores are close', () async {
      eventBus.fire(const ScoreUpdatedEvent(newScore: 1000, delta: 1000));
      await pump();
      service.updateOpponentScore(1000);
      expect(service.intensity, closeTo(0.3, 0.05));
    });

    test('score differential factor is low when scores diverge', () async {
      eventBus.fire(const ScoreUpdatedEvent(newScore: 3000, delta: 3000));
      await pump();
      service.updateOpponentScore(100);
      expect(service.intensity, lessThan(0.05));
    });

    test('cascade factor contributes during active cascade', () async {
      eventBus.fire(const ChainCompletedEvent(chainLength: 5, totalScore: 500));
      await pump();
      expect(service.intensity, closeTo(0.2, 0.05));
    });

    test('cascade factor decays over time via tick()', () async {
      eventBus.fire(const ChainCompletedEvent(chainLength: 5, totalScore: 500));
      await pump();
      expect(service.intensity, closeTo(0.2, 0.05));

      service.tick(3.1);
      expect(service.intensity, 0.0);
    });

    test('combined factors add up correctly', () async {
      eventBus.fire(const MovesUpdatedEvent(movesRemaining: 5));
      await pump();
      eventBus.fire(const ScoreUpdatedEvent(newScore: 1000, delta: 1000));
      await pump();
      service.updateOpponentScore(1000);
      eventBus.fire(const ChainCompletedEvent(chainLength: 3, totalScore: 300));
      await pump();

      expect(service.intensity, closeTo(0.72, 0.1));
    });

    test('intensity clamps to 1.0 maximum', () async {
      eventBus.fire(const MovesUpdatedEvent(movesRemaining: 0));
      await pump();
      eventBus.fire(const ScoreUpdatedEvent(newScore: 1000, delta: 1000));
      await pump();
      service.updateOpponentScore(1000);
      eventBus.fire(
        const ChainCompletedEvent(chainLength: 10, totalScore: 1000),
      );
      await pump();

      expect(service.intensity, closeTo(0.9, 0.05));
      expect(service.intensity, lessThanOrEqualTo(1.0));
    });

    test('reset() clears all state', () async {
      eventBus.fire(const MovesUpdatedEvent(movesRemaining: 5));
      await pump();
      expect(service.intensity, greaterThan(0.0));

      service.reset();
      expect(service.intensity, 0.0);
    });

    test('MatchEndedEvent triggers reset', () async {
      eventBus.fire(const MovesUpdatedEvent(movesRemaining: 5));
      await pump();
      expect(service.intensity, greaterThan(0.0));

      eventBus.fire(
        const MatchEndedEvent(
          matchId: 'test',
          won: true,
          myScore: 100,
          opponentScore: 50,
        ),
      );
      await pump();

      expect(service.intensity, 0.0);
    });

    test('setMaxMoves adjusts scaling', () async {
      service.setMaxMoves(30);
      eventBus.fire(const MovesUpdatedEvent(movesRemaining: 15));
      await pump();
      expect(service.intensity, closeTo(0.2, 0.05));
    });

    group('output getters', () {
      test('gemPulseRate scales correctly', () {
        expect(service.gemPulseRate, 1.0);
      });

      test('gemGlowAmplitude scales correctly', () {
        expect(service.gemGlowAmplitude, closeTo(0.05, 0.01));
      });

      test('ambientParticleCount is 0 at calm', () {
        expect(service.ambientParticleCount, 0);
      });

      test('vignetteAlpha is 0 at calm', () {
        expect(service.vignetteAlpha, 0.0);
      });

      test('musicSpeedMultiplier starts at 1.0', () {
        expect(service.musicSpeedMultiplier, 1.0);
      });

      test('musicHighPassFreq starts at 0', () {
        expect(service.musicHighPassFreq, 0.0);
      });
    });

    test('fires IntensityChangedEvent when change exceeds threshold', () async {
      final events = <IntensityChangedEvent>[];
      eventBus.on<IntensityChangedEvent>().listen(events.add);

      eventBus.fire(const MovesUpdatedEvent(movesRemaining: 0));
      await pump();
      // IntensityChangedEvent is also async — pump again.
      await pump();

      expect(events, isNotEmpty);
      expect(events.last.intensity, closeTo(0.4, 0.05));
    });
  });
}
