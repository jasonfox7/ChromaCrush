/// Custom Flame EffectControllers for Phase 2 juice animations.
///
/// ElasticBounceController: overshoot + diminishing bounces for gem drops.
/// ShakeController: decaying random offset for screen shake.
/// FlashOverlay: full-screen color flash component.
library;

import 'dart:math';

import 'package:flame/components.dart';
import 'package:flame/effects.dart';
import 'package:flutter/painting.dart';

import '../config/visual_config.dart';

/// EffectController that produces an elastic bounce curve.
///
/// The gem overshoots its target by [overshoot] (default 15%) and then
/// performs [bounces] diminishing bounces before settling at 1.0.
///
/// Curve: y = 1 - A * |sin(pi * bounces * t)| * e^(-decay * t)
/// where t goes from 0→1 over [duration].
class ElasticBounceController extends EffectController {
  ElasticBounceController({
    required double duration,
    this.overshoot = kElasticOvershoot,
    this.bounces = kElasticBounces,
    this.decay = kElasticDecay,
  }) : _duration = duration,
       super.empty();

  final double _duration;
  final double overshoot;
  final int bounces;
  final double decay;

  double _timer = 0;

  @override
  bool get completed => _timer >= _duration;

  @override
  double? get duration => _duration;

  @override
  double get progress {
    if (_duration <= 0) return 1.0;
    final t = (_timer / _duration).clamp(0.0, 1.0);
    // Elastic bounce curve: overshoots then settles.
    final bounce = overshoot * (sin(pi * bounces * t)).abs() * exp(-decay * t);
    return (1.0 + bounce).clamp(0.0, 1.0 + overshoot);
  }

  @override
  double advance(double dt) {
    _timer += dt;
    if (_timer >= _duration) {
      final leftover = _timer - _duration;
      _timer = _duration;
      return leftover;
    }
    return 0;
  }

  @override
  double recede(double dt) => 0;

  @override
  void setToStart() {
    _timer = 0;
  }

  @override
  void setToEnd() {
    _timer = _duration;
  }
}

/// EffectController for screen shake — decaying random offsets.
///
/// Returns a progress value that oscillates randomly and decays
/// exponentially over [duration].
class ShakeController extends EffectController {
  ShakeController({
    required double duration,
    this.maxDisplacement = kDefaultShakeDisplacement,
    this.frequency = kShakeFrequency,
  }) : _duration = duration,
       _random = Random(),
       super.empty();

  final double _duration;
  final double maxDisplacement;
  final double frequency;
  final Random _random;

  double _timer = 0;

  /// Current shake offset (updated each advance).
  Vector2 get offset {
    if (_duration <= 0 || _timer >= _duration) return Vector2.zero();
    final decay = 1.0 - (_timer / _duration);
    final amp = maxDisplacement * decay;
    return Vector2(
      (_random.nextDouble() * 2 - 1) * amp,
      (_random.nextDouble() * 2 - 1) * amp,
    );
  }

  @override
  bool get completed => _timer >= _duration;

  @override
  double? get duration => _duration;

  @override
  double get progress => (_timer / _duration).clamp(0.0, 1.0);

  @override
  double advance(double dt) {
    _timer += dt;
    if (_timer >= _duration) {
      final leftover = _timer - _duration;
      _timer = _duration;
      return leftover;
    }
    return 0;
  }

  @override
  double recede(double dt) => 0;

  @override
  void setToStart() {
    _timer = 0;
  }

  @override
  void setToEnd() {
    _timer = _duration;
  }
}

/// Full-screen color flash overlay.
///
/// Fades in then out: alpha 0 → [peakAlpha] → 0 over [duration].
class FlashOverlay extends RectangleComponent {
  FlashOverlay({
    required Vector2 gameSize,
    required Color flashColor,
    Duration duration = const Duration(milliseconds: 150),
    this.peakAlpha = kFlashPeakAlpha,
  }) : _totalSeconds = duration.inMilliseconds / 1000.0,
       super(
         size: gameSize,
         paint: Paint()..color = flashColor.withValues(alpha: 0),
         priority: 50,
       );

  final double _totalSeconds;
  final double peakAlpha;
  double _timer = 0;

  @override
  void update(double dt) {
    super.update(dt);
    _timer += dt;

    if (_timer >= _totalSeconds) {
      removeFromParent();
      return;
    }

    // Triangle wave: ramp up first half, ramp down second half.
    final t = _timer / _totalSeconds;
    final alpha = t < 0.5
        ? peakAlpha * (t / 0.5)
        : peakAlpha * (1.0 - (t - 0.5) / 0.5);
    paint.color = paint.color.withValues(alpha: alpha);
  }
}
