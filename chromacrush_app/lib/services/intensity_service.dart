/// Intensity system — 0.0–1.0 global scalar driven by gameplay state.
///
/// Subscribes to EventBus events (moves, score, cascades) and computes
/// a composite intensity value. Outputs drive gem pulse rate, ambient
/// particles, board vignette, and adaptive music parameters.
library;

import 'dart:async';
import 'dart:math';

import 'package:flutter/foundation.dart';

import '../config/game_config.dart';
import 'event_bus.dart';

class IntensityService extends ChangeNotifier {
  IntensityService({required EventBus eventBus}) : _eventBus = eventBus {
    _subscribe();
  }

  final EventBus _eventBus;
  final List<StreamSubscription<dynamic>> _subscriptions = [];

  // -- Raw inputs --
  int _movesRemaining = 20;
  int _maxMoves = 20;
  int _myScore = 0;
  int _opponentScore = 0;
  int _recentCascadeLength = 0;
  double _cascadeDecayTimer = 0;

  // -- Computed intensity (0.0–1.0) --
  double _intensity = 0.0;
  double get intensity => _intensity;

  // -- Outputs: computed from intensity --

  /// Gem heartbeat pulse rate in Hz (1.0 calm → 2.5 critical).
  double get gemPulseRate => kGemPulseRateMin + _intensity * kGemPulseRateRange;

  /// Gem glow amplitude (0.05 calm → 0.40 critical).
  double get gemGlowAmplitude => kGemGlowAmpMin + _intensity * kGemGlowAmpRange;

  /// Ambient drifting particle count (0 calm → 50 critical).
  int get ambientParticleCount => (_intensity * kAmbientParticleMax).round();

  /// Board vignette alpha (0.0 calm → 0.3 critical).
  double get vignetteAlpha => _intensity * kVignetteAlphaMax;

  /// Music playback speed multiplier (1.0 calm → 1.3 critical).
  double get musicSpeedMultiplier => 1.0 + _intensity * kMusicSpeedRange;

  /// Music high-pass filter frequency in Hz (0 calm → 800 critical).
  double get musicHighPassFreq => _intensity * kMusicHighPassMax;

  // ---------------------------------------------------------------------------
  // Event subscriptions
  // ---------------------------------------------------------------------------

  void _subscribe() {
    _subscriptions.add(
      _eventBus.on<MovesUpdatedEvent>().listen((event) {
        _movesRemaining = event.movesRemaining;
        _recompute();
      }),
    );

    _subscriptions.add(
      _eventBus.on<ScoreUpdatedEvent>().listen((event) {
        _myScore = event.newScore;
        _recompute();
      }),
    );

    _subscriptions.add(
      _eventBus.on<ChainCompletedEvent>().listen((event) {
        _recentCascadeLength = event.chainLength;
        _cascadeDecayTimer = kCascadeDecaySeconds;
        _recompute();
      }),
    );

    _subscriptions.add(
      _eventBus.on<BotScoreUpdatedEvent>().listen((event) {
        updateOpponentScore(event.botScore);
      }),
    );

    _subscriptions.add(
      _eventBus.on<MatchEndedEvent>().listen((_) {
        // Reset intensity on match end.
        reset();
      }),
    );
  }

  // ---------------------------------------------------------------------------
  // Computation
  // ---------------------------------------------------------------------------

  void _recompute() {
    final oldIntensity = _intensity;

    // Factor 1: Moves remaining (0.0–0.4).
    // More pressure as moves run out.
    final movesFactor =
        ((_maxMoves - _movesRemaining) / _maxMoves).clamp(0.0, 1.0) *
        kMovesFactorWeight;

    // Factor 2: Score differential (0.0–0.3).
    // Close match = high tension. Blowout = low.
    final totalScore = _myScore + _opponentScore;
    final scoreFactor = totalScore > 0
        ? (1.0 - (_myScore - _opponentScore).abs() / totalScore).clamp(
                0.0,
                1.0,
              ) *
              kScoreFactorWeight
        : 0.0;

    // Factor 3: Recent cascade length (0.0–0.2).
    // Decays via _cascadeDecayTimer in tick().
    final cascadeFactor = _cascadeDecayTimer > 0
        ? (min(_recentCascadeLength / 5.0, 1.0) * kCascadeFactorWeight)
        : 0.0;

    // Factor 4: Board hints (0.0–0.1) — placeholder.
    const boardFactor = 0.0;

    _intensity = (movesFactor + scoreFactor + cascadeFactor + boardFactor)
        .clamp(0.0, 1.0);

    // Only notify if change exceeds threshold (avoid excessive rebuilds).
    if ((_intensity - oldIntensity).abs() > kIntensityNotifyThreshold) {
      _eventBus.fire(IntensityChangedEvent(intensity: _intensity));
      notifyListeners();
    }
  }

  /// Call from game loop to decay cascade contribution over time.
  void tick(double dt) {
    if (_cascadeDecayTimer > 0) {
      _cascadeDecayTimer -= dt;
      if (_cascadeDecayTimer <= 0) {
        _cascadeDecayTimer = 0;
        _recentCascadeLength = 0;
        _recompute();
      }
    }
  }

  /// Reset all inputs (new match).
  void reset() {
    _movesRemaining = _maxMoves;
    _myScore = 0;
    _opponentScore = 0;
    _recentCascadeLength = 0;
    _cascadeDecayTimer = 0;
    _intensity = 0.0;
    notifyListeners();
  }

  /// Set the max moves for intensity scaling (called at match start).
  void setMaxMoves(int maxMoves) {
    _maxMoves = maxMoves > 0 ? maxMoves : 20;
  }

  /// Update opponent score (from MatchViewModel or API response).
  void updateOpponentScore(int score) {
    _opponentScore = score;
    _recompute();
  }

  @override
  void dispose() {
    for (final sub in _subscriptions) {
      sub.cancel();
    }
    super.dispose();
  }
}
