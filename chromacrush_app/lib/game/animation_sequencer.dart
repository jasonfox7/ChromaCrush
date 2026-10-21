/// Chains backend move results into visual animation sequences.
///
/// Consumes MoveResultResponse and plays cascade animation steps provided
/// by the server. Each cascade step maps to removal → gravity → fill events.
library;

import '../audio/sound_bank.dart';
import '../config/animation_timings.dart';
import '../config/visual_config.dart';
import '../extensions/grid_math.dart';
import '../models/backend_contract.dart';
import '../models/gem_type.dart';
import '../models/match_event.dart';
import '../services/audio_engine.dart';
import '../services/event_bus.dart';
import '../services/haptics_engine.dart';
import 'background_layer.dart';
import 'board_layer.dart';
import 'cascade_animator.dart';
import 'particle_layer.dart';

class AnimationSequencer {
  AnimationSequencer({
    required this.boardLayer,
    required this.eventBus,
    required this.layout,
    this.cascadeAnimator,
    this.particleLayer,
    this.backgroundLayer,
    this.audioEngine,
    this.hapticsEngine,
  });

  final BoardLayer boardLayer;
  final EventBus eventBus;
  final BoardLayout layout;
  final CascadeAnimator? cascadeAnimator;
  final ParticleLayer? particleLayer;
  final BackgroundLayer? backgroundLayer;
  final AudioEngineBase? audioEngine;
  final HapticsEngineBase? hapticsEngine;

  /// Play the full animation sequence for a move result.
  ///
  /// The swap animation has already played (optimistic). This method handles
  /// the cascade: removal → gravity → fill → board sync.
  Future<void> playMoveResult({
    required List<List<int>> oldBoard,
    required MoveResultResponse result,
    required int fromRow,
    required int fromCol,
    required int toRow,
    required int toCol,
  }) async {
    final board = result.newBoard;
    if (board == null) return;
    final newBoard = board.cells;
    final newFunctions = board.functions;

    if (result.cascadeSteps.isNotEmpty) {
      // Server provided cascade animation buffer — play it directly.
      await playCascadeSteps(result.cascadeSteps, newBoard, newFunctions);
    } else {
      // Fallback: snap to final state (no cascade data).
      await _playEvent(
        BoardSyncEvent(finalBoard: newBoard, finalFunctions: newFunctions),
      );
    }
  }

  /// Play server-provided cascade steps as sequential animations.
  ///
  /// Mirrors the backend pipeline 1:1 per step:
  /// JUICE → DRAIN (removals + activations) → PLACE → GRAVITY → ATTRACT → FILL → INJECT
  Future<void> playCascadeSteps(
    List<CascadeStepResponse> steps,
    List<List<int>> finalBoard,
    List<List<int>> finalFunctions,
  ) async {
    final isFusion = steps.length >= 4;

    for (var stepIndex = 0; stepIndex < steps.length; stepIndex++) {
      final step = steps[stepIndex];

      // ── JUICE (fire-and-forget) ──────────────────────────────────────
      if (stepIndex == 0 && isFusion) {
        cascadeAnimator?.playFusionSequence();
        audioEngine?.playSfx(SoundId.fusionFanfare);
        hapticsEngine?.playPattern(HapticPattern.fusionCombo);
      } else if (stepIndex >= 1) {
        cascadeAnimator?.screenShake(
          maxDisplacement: 4.0 + stepIndex * 2.0,
          duration: kCascadeShakeDuration,
        );
        final pitchIndex = (stepIndex - 1).clamp(
          0,
          kCascadePitchLadder.length - 1,
        );
        audioEngine?.playSfx(
          SoundId.cascadeStep,
          pitch: kCascadePitchLadder[pitchIndex],
        );
        final hapticIntensity = (0.6 + stepIndex * 0.1).clamp(0.0, 1.0);
        hapticsEngine?.playPattern(
          HapticPattern.cascadeStep,
          intensity: hapticIntensity,
        );
      }

      // ── DRAIN wave 0: match removals ─────────────────────────────────
      if (step.removals.isNotEmpty) {
        // Audio.
        if (stepIndex == 0 && !isFusion) {
          audioEngine?.playSfx(SoundId.matchChime);
          hapticsEngine?.playPattern(HapticPattern.matchLight);
        }

        // Particles.
        final firstGem = boardLayer.gemAt(
          step.removals.first.row,
          step.removals.first.col,
        );
        final burstColor = firstGem?.gemType ?? GemType.red;
        if (stepIndex >= 1) {
          particleLayer?.cascadeBurst(step.removals, burstColor);
        } else {
          particleLayer?.matchBurst(step.removals, burstColor);
        }
        if (isFusion && stepIndex == 0) {
          particleLayer?.fusionStorm(
            step.removals.first.row,
            step.removals.first.col,
          );
        }

        // Background ripple at centroid.
        _addRippleAtCentroid(step.removals);

        await _playEvent(
          MatchRemovalEvent(positions: step.removals, scoreGained: 0),
        );
      }

      // ── DRAIN waves 1..N: special activations (sequential) ───────────
      for (final activation in step.specialActivations) {
        if (activation.affected.isEmpty) continue;

        final isMega = activation.isMega;

        // Shake.
        cascadeAnimator?.screenShake(
          maxDisplacement: isMega
              ? kMegaShakeDisplacement
              : kSpecialShakeDisplacement,
          duration: isMega ? kMegaShakeDuration : kSpecialShakeDuration,
        );

        // Audio + haptics.
        if (isMega) {
          audioEngine?.playSfx(SoundId.megaActivation);
          hapticsEngine?.playPattern(HapticPattern.megaActivation);
          particleLayer?.megaActivationBurst(activation.row, activation.col);
        } else {
          audioEngine?.playSfx(SoundId.specialActivation);
          hapticsEngine?.playPattern(HapticPattern.specialActivation);
        }

        // ARCHITECTURE NOTE — Cosmetic vs. server-driven separation:
        // Cell destruction is 100% server-driven: activation.affected contains
        // the exact positions the backend computed via EffectInterpreter +
        // board_rules.json. That list is always correct regardless of backend
        // config changes.
        //
        // Particle effects below are purely cosmetic and dispatched by gem
        // function ID — NOT by the backend's actual effect shape. If a backend
        // rule were changed (e.g. radialBomb reconfigured to clear a cross
        // pattern instead of a 3x3 radius), the correct cells would still be
        // destroyed, but particles would still show a radial wave.
        //
        // To decouple: backend could add an effect_style hint (e.g. "line_h",
        // "radial", "color_match") to SpecialActivationResponse, and the
        // frontend would dispatch particles based on that instead of gem_type.
        final func = GemFunction.fromValue(activation.gemType.abs());
        switch (func) {
          case GemFunction.lineBlastH:
            particleLayer?.lineSweep(
              activation.row,
              activation.col,
              horizontal: true,
            );
          case GemFunction.lineBlastV:
            particleLayer?.lineSweep(
              activation.row,
              activation.col,
              horizontal: false,
            );
          case GemFunction.radialBomb:
            particleLayer?.radialWave(activation.row, activation.col);
          case GemFunction.chromaticOrb:
            particleLayer?.chromaticRain(activation.row, activation.col);
          case GemFunction.neutral:
            break;
        }

        // Background ripple.
        if (backgroundLayer != null) {
          final screenX =
              layout.boardLeft +
              activation.col * layout.cellStride +
              layout.cellSize / 2;
          final screenY =
              layout.boardTop +
              activation.row * layout.cellStride +
              layout.cellSize / 2;
          backgroundLayer!.addRipple(screenX, screenY);
        }

        // ARCHITECTURE NOTE — Hardcoded mega combo values:
        // These mega_func values (14, 24, 34) identify orb combos that produce
        // a chromatic conversion visual (flash on affected positions before
        // removal). These values are hardcoded here rather than derived from
        // backend config. If new orb combos were added or existing combos
        // changed behavior, this check would not adapt automatically.
        //
        // To decouple: backend could add a has_chromatic_flash flag to
        // SpecialActivationResponse, or this could be subsumed by an
        // effect_style hint (any "color_match" style gets the flash).
        // Chromatic conversion flash (O combos: H+O, V+O, B+O).
        final isChromaConversion =
            isMega &&
            (activation.megaFunc == 14 ||
                activation.megaFunc == 24 ||
                activation.megaFunc == 34);
        if (isChromaConversion) {
          boardLayer.flashPositions(activation.affected);
          await Future<void>.delayed(
            kChromaFlashDuration + kChromaFlashHoldDuration,
          );
        }

        // Flash, then remove affected positions.
        await _playEvent(
          SpecialGemActivatedEvent(
            row: activation.row,
            col: activation.col,
            gemType: activation.gemType,
          ),
        );
        await _playEvent(
          MatchRemovalEvent(positions: activation.affected, scoreGained: 0),
        );
      }

      // ── PLACE special gem created by this match ──────────────────────
      if (step.specialGemCreated != null) {
        final sp = step.specialGemCreated!;
        final func = GemFunction.fromValue(sp.gemType.abs());
        final colorType = GemType.fromValue(sp.color);
        final gem = boardLayer.placeSpecialGem(sp.row, sp.col, colorType, func);
        if (gem != null) {
          await gem.loaded;
          await gem.animateAppear(duration: kSpecialAppearDuration);
        }
      }

      // ── GRAVITY ──────────────────────────────────────────────────────
      if (step.drops.isNotEmpty) {
        await _playEvent(
          GravityEvent(
            drops: step.drops
                .map(
                  (d) => (
                    fromRow: d.fromRow,
                    fromCol: d.fromCol,
                    toRow: d.toRow,
                    toCol: d.toCol,
                  ),
                )
                .toList(),
          ),
        );
      }

      // ── ATTRACT (post-gravity mega formation) ────────────────────────
      for (final att in step.specialAttractions) {
        audioEngine?.playSfx(SoundId.megaMerge);
        hapticsEngine?.playPattern(HapticPattern.megaMerge);
        particleLayer?.megaMergeSparks(
          att.posARow,
          att.posACol,
          att.posBRow,
          att.posBCol,
          att.centerRow,
          att.centerCol,
        );
        if (backgroundLayer != null) {
          final screenX =
              layout.boardLeft +
              att.centerCol * layout.cellStride +
              layout.cellSize / 2;
          final screenY =
              layout.boardTop +
              att.centerRow * layout.cellStride +
              layout.cellSize / 2;
          backgroundLayer!.addRipple(screenX, screenY);
        }
        await _playEvent(
          SpecialAttractionEvent(
            posARow: att.posARow,
            posACol: att.posACol,
            posBRow: att.posBRow,
            posBCol: att.posBCol,
            centerRow: att.centerRow,
            centerCol: att.centerCol,
            megaFunc: att.megaFunc,
          ),
        );
      }

      // ── FILL ─────────────────────────────────────────────────────────
      if (step.spawns.isNotEmpty) {
        await _playEvent(
          FillEvent(
            spawns: step.spawns
                .map((s) => (row: s.row, col: s.col, gemType: s.gemType))
                .toList(),
          ),
        );
      }

      // ── INJECT (card injection — e.g. Heavenly Gift) ────────────────
      if (step.injectedSpecial != null) {
        final inj = step.injectedSpecial!;
        final func = GemFunction.fromValue(inj.function);
        // Read the existing gem's color before replacing.
        final existingGem = boardLayer.gemAt(inj.row, inj.col);
        final colorType = existingGem?.gemType ?? GemType.red;
        final gem = boardLayer.placeSpecialGem(
          inj.row,
          inj.col,
          colorType,
          func,
        );
        if (gem != null) {
          await gem.loaded;
          await gem.animateAppear(duration: kSpecialAppearDuration);
        }
      }

      // ── INJECTED ACTIVATION (fire_immediately — bomb goes off) ─────
      if (step.injectedActivation != null) {
        final activation = step.injectedActivation!;
        final isMega = activation.isMega;

        cascadeAnimator?.screenShake(
          maxDisplacement: isMega
              ? kMegaShakeDisplacement
              : kSpecialShakeDisplacement,
          duration: isMega ? kMegaShakeDuration : kSpecialShakeDuration,
        );

        if (isMega) {
          audioEngine?.playSfx(SoundId.megaActivation);
          hapticsEngine?.playPattern(HapticPattern.megaActivation);
          particleLayer?.megaActivationBurst(activation.row, activation.col);
        } else {
          audioEngine?.playSfx(SoundId.specialActivation);
          hapticsEngine?.playPattern(HapticPattern.specialActivation);
        }

        // Same cosmetic-vs-server-driven note as DRAIN activations above:
        // particles dispatched by gem function ID, not backend effect shape.
        // See ARCHITECTURE NOTE near line 168 for full explanation.
        final func = GemFunction.fromValue(activation.gemType.abs());
        switch (func) {
          case GemFunction.lineBlastH:
            particleLayer?.lineSweep(
              activation.row,
              activation.col,
              horizontal: true,
            );
          case GemFunction.lineBlastV:
            particleLayer?.lineSweep(
              activation.row,
              activation.col,
              horizontal: false,
            );
          case GemFunction.radialBomb:
            particleLayer?.radialWave(activation.row, activation.col);
          case GemFunction.chromaticOrb:
            particleLayer?.chromaticRain(activation.row, activation.col);
          case GemFunction.neutral:
            break;
        }

        if (backgroundLayer != null) {
          final screenX =
              layout.boardLeft +
              activation.col * layout.cellStride +
              layout.cellSize / 2;
          final screenY =
              layout.boardTop +
              activation.row * layout.cellStride +
              layout.cellSize / 2;
          backgroundLayer!.addRipple(screenX, screenY);
        }

        await _playEvent(
          SpecialGemActivatedEvent(
            row: activation.row,
            col: activation.col,
            gemType: activation.gemType,
          ),
        );
        await _playEvent(
          MatchRemovalEvent(positions: activation.affected, scoreGained: 0),
        );
      }

      // ── INJECTED GRAVITY (fire_immediately aftermath) ──────────────
      if (step.injectedDrops.isNotEmpty) {
        await _playEvent(
          GravityEvent(
            drops: step.injectedDrops
                .map(
                  (d) => (
                    fromRow: d.fromRow,
                    fromCol: d.fromCol,
                    toRow: d.toRow,
                    toCol: d.toCol,
                  ),
                )
                .toList(),
          ),
        );
      }

      // ── INJECTED FILL (fire_immediately aftermath) ─────────────────
      if (step.injectedSpawns.isNotEmpty) {
        await _playEvent(
          FillEvent(
            spawns: step.injectedSpawns
                .map((s) => (row: s.row, col: s.col, gemType: s.gemType))
                .toList(),
          ),
        );
      }

      // ── SETTLE ───────────────────────────────────────────────────────
      await Future<void>.delayed(kCascadeSettleDuration);
    }

    // Safety net: snap to final server state.
    await _playEvent(
      BoardSyncEvent(finalBoard: finalBoard, finalFunctions: finalFunctions),
    );
  }

  /// Add a background ripple at the centroid of a list of positions.
  void _addRippleAtCentroid(List<({int row, int col})> positions) {
    if (backgroundLayer == null || positions.isEmpty) return;
    var sumCol = 0.0;
    var sumRow = 0.0;
    for (final pos in positions) {
      sumCol += pos.col;
      sumRow += pos.row;
    }
    final count = positions.length.toDouble();
    final screenX =
        layout.boardLeft +
        (sumCol / count) * layout.cellStride +
        layout.cellSize / 2;
    final screenY =
        layout.boardTop +
        (sumRow / count) * layout.cellStride +
        layout.cellSize / 2;
    backgroundLayer!.addRipple(screenX, screenY);
  }

  /// Play a sequence of MatchEvents in order.
  Future<void> playSequence(List<MatchEvent> events) async {
    for (final event in events) {
      await _playEvent(event);
    }
  }

  Future<void> _playEvent(MatchEvent event) async {
    switch (event) {
      case SwapEvent():
        // Swap already played optimistically. Skip.
        break;

      case InvalidSwapEvent():
        // Rubber-band: swap back.
        await boardLayer.animateSwap(
          event.toRow,
          event.toCol,
          event.fromRow,
          event.fromCol,
          duration: kInvalidSwapDuration,
        );

      case MatchRemovalEvent():
        await boardLayer.animateRemoval(
          event.positions,
          duration: kRemovalDuration,
        );
        // Pause after removal so the player can see the gap.
        await Future<void>.delayed(kRemovalPauseDuration);

      case GravityEvent():
        await boardLayer.animateDrops(
          event.drops,
          durationPerRow: kDropPerRowDuration,
        );
        // Brief settle pause after drops land.
        await Future<void>.delayed(kDropPauseDuration);

      case FillEvent():
        await boardLayer.animateFill(event.spawns, duration: kFillDuration);
        // Pause after new gems appear before next cascade check.
        await Future<void>.delayed(kFillPauseDuration);

      case SpecialGemCreatedEvent():
        // Handled inline in playCascadeSteps (needs pre-removal color snapshot).
        break;

      case SpecialGemActivatedEvent():
        // Brief flash/pause so the player sees the activation.
        await Future<void>.delayed(kSpecialActivationPause);

      case SpecialAttractionEvent():
        // Animate two specials merging into center mega gem.
        await boardLayer.animateAttraction(
          posARow: event.posARow,
          posACol: event.posACol,
          posBRow: event.posBRow,
          posBCol: event.posBCol,
          centerRow: event.centerRow,
          centerCol: event.centerCol,
          megaFunc: event.megaFunc,
        );
        // Brief settle after attraction.
        await Future<void>.delayed(kAttractionSettleDuration);

      case BoardSyncEvent():
        // Snap to final server state (visual sync invariant).
        boardLayer.syncToBoard(event.finalBoard, event.finalFunctions);
        // Brief settle pause.
        await Future<void>.delayed(kBoardSyncSettleDuration);
    }
  }
}
