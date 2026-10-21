/// Haptics engine interface — iOS Core Haptics via platform channel.
///
/// Dart interface with two backends:
/// 1. IOSHapticsEngine — platform channel to Swift Core Haptics (Phase 2).
/// 2. StubHapticsEngine — no-op for Windows development and testing.
library;

/// Haptic pattern identifiers.
enum HapticPattern {
  gemSelect,
  gemSwap,
  matchLight,
  matchMedium,
  matchHeavy,
  cascadeStep,
  specialActivation,
  fusionCombo,
  victory,
  defeat,
  raidAlert,
  megaMerge,
  megaActivation,
}

/// Abstract haptics engine interface.
abstract class HapticsEngineBase {
  Future<void> initialize();
  Future<void> dispose();

  void playPattern(HapticPattern pattern, {double intensity = 1.0});
  bool get isEnabled;
  set isEnabled(bool value);
  bool get isSupported;
}

/// Stub haptics engine — no-op. Used on Windows and in tests.
class StubHapticsEngine extends HapticsEngineBase {
  bool _enabled = true;

  @override
  Future<void> initialize() async {}
  @override
  Future<void> dispose() async {}
  @override
  void playPattern(HapticPattern pattern, {double intensity = 1.0}) {}
  @override
  bool get isEnabled => _enabled;
  @override
  set isEnabled(bool value) => _enabled = value;
  @override
  bool get isSupported => false;
}
