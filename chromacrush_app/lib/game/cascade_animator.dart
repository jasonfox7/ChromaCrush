/// Cascade visual effects manager — screen shake, slow-mo, zoom pulse, fusion.
///
/// Sits alongside AnimationSequencer and provides the "juice" effects
/// that accompany cascade animations. Does not control gem movement —
/// only visual effects on the game scene.
library;

import 'dart:async';

import 'package:flame/components.dart';
import 'package:flame/effects.dart';
import 'package:flame/game.dart';
import 'package:flutter/animation.dart';

import '../config/animation_timings.dart';
import '../config/visual_config.dart';
import '../extensions/flame_effects_ext.dart';

/// Manages scene-level visual effects during cascades and special activations.
///
/// Requires a reference to the game's board container (for shake/zoom)
/// and the game component (for adding flash overlays).
class CascadeAnimator {
  CascadeAnimator({required this.boardContainer, required this.gameRef});

  /// The board layer component (receives shake + zoom effects).
  final PositionComponent boardContainer;

  /// The game root (receives flash overlays).
  final FlameGame gameRef;

  /// Original board position (for shake reset).
  Vector2? _originalPosition;

  /// Whether a shake is currently active.
  bool _shaking = false;

  // ---------------------------------------------------------------------------
  // Screen shake
  // ---------------------------------------------------------------------------

  /// Play a screen shake effect on the board container.
  ///
  /// [maxDisplacement] is the peak pixel offset (decays over duration).
  Future<void> screenShake({
    Duration duration = kShakeDuration,
    double maxDisplacement = kDefaultShakeDisplacement,
  }) async {
    if (_shaking) return;
    _shaking = true;

    _originalPosition ??= boardContainer.position.clone();
    final origin = _originalPosition!.clone();

    final controller = ShakeController(
      duration: duration.inMilliseconds / 1000.0,
      maxDisplacement: maxDisplacement,
    );

    final completer = Completer<void>();

    boardContainer.add(
      _ShakeEffect(
        controller: controller,
        origin: origin,
        onDone: () {
          boardContainer.position.setFrom(origin);
          _shaking = false;
          completer.complete();
        },
      ),
    );

    return completer.future;
  }

  // ---------------------------------------------------------------------------
  // Screen flash
  // ---------------------------------------------------------------------------

  /// Play a full-screen color flash.
  void screenFlash({
    Color color = const Color(0xFFFFFFFF),
    Duration duration = kFlashDuration,
    double peakAlpha = kFlashPeakAlpha,
  }) {
    final gameSize = gameRef.size;
    gameRef.add(
      FlashOverlay(
        gameSize: gameSize,
        flashColor: color,
        duration: duration,
        peakAlpha: peakAlpha,
      ),
    );
  }

  // ---------------------------------------------------------------------------
  // Zoom pulse
  // ---------------------------------------------------------------------------

  /// Play a zoom pulse on the board: 1.0 → 1.03 → 1.0 over [duration].
  Future<void> zoomPulse({Duration duration = kZoomPulseDuration}) async {
    final halfSeconds = duration.inMilliseconds / 2000.0;
    final completer = Completer<void>();

    boardContainer.add(
      ScaleEffect.to(
        Vector2.all(kZoomPulseScale),
        EffectController(duration: halfSeconds, curve: Curves.easeOut),
      ),
    );

    // After reaching peak, scale back.
    await Future<void>.delayed(
      Duration(milliseconds: duration.inMilliseconds ~/ 2),
    );

    boardContainer.add(
      ScaleEffect.to(
        Vector2.all(1.0),
        EffectController(duration: halfSeconds, curve: Curves.easeIn),
        onComplete: completer.complete,
      ),
    );

    return completer.future;
  }

  // ---------------------------------------------------------------------------
  // Fusion sequence (simplified for Phase 2)
  // ---------------------------------------------------------------------------

  /// Play the simplified fusion jackpot sequence.
  ///
  /// T+0: slow-mo hint (caller handles timeScale)
  /// T+100: screen shake
  /// T+400: flash + shake ends
  /// T+500: (particles triggered by caller)
  /// T+1500: settle
  Future<void> playFusionSequence() async {
    // T+0: Start screen shake (builds over 600ms).
    final shakeFuture = screenShake(
      duration: kFusionShakeDuration,
      maxDisplacement: kFusionShakeDisplacement,
    );

    // T+100: Wait briefly for shake to establish.
    await Future<void>.delayed(kFusionFlashDelay);

    // T+400: Flash.
    screenFlash(
      color: kFusionFlashColor,
      duration: kFusionFlashDuration,
      peakAlpha: kFusionFlashPeakAlpha,
    );

    // T+500: Zoom pulse.
    zoomPulse(duration: kFusionZoomDuration);

    // Wait for shake to complete.
    await shakeFuture;

    // T+1500: Brief settle.
    await Future<void>.delayed(kFusionSettleDuration);
  }
}

/// Internal Effect that applies shake offsets to a component each frame.
class _ShakeEffect extends Effect {
  _ShakeEffect({
    required ShakeController controller,
    required this.origin,
    VoidCallback? onDone,
  }) : _shakeController = controller,
       _onDone = onDone,
       super(controller);

  final ShakeController _shakeController;
  final Vector2 origin;
  final VoidCallback? _onDone;

  @override
  void apply(double progress) {
    final target = parent;
    if (target is PositionComponent) {
      final offset = _shakeController.offset;
      target.position.setValues(origin.x + offset.x, origin.y + offset.y);
    }
  }

  @override
  void onFinish() {
    super.onFinish();
    _onDone?.call();
  }
}
