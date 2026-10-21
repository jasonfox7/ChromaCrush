/// Dart-side haptic pattern definitions.
///
/// Each pattern defines intensity, sharpness, and duration values
/// matching the design skeleton Section 4.3. These are sent to the
/// iOS platform channel for Core Haptics AHAP playback.
library;

import '../services/haptics_engine.dart';

/// Haptic event type sent to the platform channel.
class HapticEvent {
  const HapticEvent({
    required this.type,
    required this.intensity,
    required this.sharpness,
    this.durationMs = 0,
    this.delayMs = 0,
  });

  /// 'transient' for sharp taps, 'continuous' for sustained vibrations.
  final String type;

  /// Intensity 0.0–1.0.
  final double intensity;

  /// Sharpness 0.0–1.0.
  final double sharpness;

  /// Duration in ms (only for continuous events).
  final int durationMs;

  /// Delay before this event starts (ms from pattern start).
  final int delayMs;

  Map<String, dynamic> toJson() => {
    'type': type,
    'intensity': intensity,
    'sharpness': sharpness,
    'durationMs': durationMs,
    'delayMs': delayMs,
  };
}

/// Full haptic pattern: one or more events played in sequence.
class HapticPatternDef {
  const HapticPatternDef({required this.events});

  final List<HapticEvent> events;

  List<Map<String, dynamic>> toJson() => events.map((e) => e.toJson()).toList();
}

/// Maps HapticPattern enum to its event definition.
const Map<HapticPattern, HapticPatternDef> hapticPatterns = {
  // Gem select: light transient tap.
  HapticPattern.gemSelect: HapticPatternDef(
    events: [HapticEvent(type: 'transient', intensity: 0.4, sharpness: 0.6)],
  ),

  // Gem swap: medium transient tap.
  HapticPattern.gemSwap: HapticPatternDef(
    events: [HapticEvent(type: 'transient', intensity: 0.5, sharpness: 0.4)],
  ),

  // Match light (3-gem): transient hit.
  HapticPattern.matchLight: HapticPatternDef(
    events: [HapticEvent(type: 'transient', intensity: 0.6, sharpness: 0.5)],
  ),

  // Match medium (4-gem): stronger transient.
  HapticPattern.matchMedium: HapticPatternDef(
    events: [HapticEvent(type: 'transient', intensity: 0.7, sharpness: 0.6)],
  ),

  // Match heavy (5+ gem): heavy transient.
  HapticPattern.matchHeavy: HapticPatternDef(
    events: [HapticEvent(type: 'transient', intensity: 0.9, sharpness: 0.7)],
  ),

  // Cascade step: escalating transient (base intensity, caller adds step bonus).
  HapticPattern.cascadeStep: HapticPatternDef(
    events: [HapticEvent(type: 'transient', intensity: 0.6, sharpness: 0.5)],
  ),

  // Special activation: continuous buzz → transient hit.
  HapticPattern.specialActivation: HapticPatternDef(
    events: [
      HapticEvent(
        type: 'continuous',
        intensity: 0.5,
        sharpness: 0.3,
        durationMs: 200,
      ),
      HapticEvent(
        type: 'transient',
        intensity: 0.8,
        sharpness: 0.7,
        delayMs: 200,
      ),
    ],
  ),

  // Fusion combo: multi-phase ramp 0.3→1.0 over 800ms.
  HapticPattern.fusionCombo: HapticPatternDef(
    events: [
      HapticEvent(
        type: 'continuous',
        intensity: 0.3,
        sharpness: 0.3,
        durationMs: 200,
      ),
      HapticEvent(
        type: 'continuous',
        intensity: 0.5,
        sharpness: 0.5,
        durationMs: 200,
        delayMs: 200,
      ),
      HapticEvent(
        type: 'continuous',
        intensity: 0.7,
        sharpness: 0.7,
        durationMs: 200,
        delayMs: 400,
      ),
      HapticEvent(
        type: 'continuous',
        intensity: 1.0,
        sharpness: 0.9,
        durationMs: 200,
        delayMs: 600,
      ),
    ],
  ),

  // Victory: sustained buzz.
  HapticPattern.victory: HapticPatternDef(
    events: [
      HapticEvent(
        type: 'continuous',
        intensity: 0.6,
        sharpness: 0.4,
        durationMs: 500,
      ),
    ],
  ),

  // Defeat: single heavy transient.
  HapticPattern.defeat: HapticPatternDef(
    events: [HapticEvent(type: 'transient', intensity: 0.7, sharpness: 0.9)],
  ),

  // Raid alert: 3x escalating transients with gaps.
  HapticPattern.raidAlert: HapticPatternDef(
    events: [
      HapticEvent(type: 'transient', intensity: 0.5, sharpness: 0.6),
      HapticEvent(
        type: 'transient',
        intensity: 0.7,
        sharpness: 0.7,
        delayMs: 100,
      ),
      HapticEvent(
        type: 'transient',
        intensity: 0.9,
        sharpness: 0.8,
        delayMs: 200,
      ),
    ],
  ),
};
