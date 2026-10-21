/// iOS haptics engine — Core Haptics via platform channel.
///
/// Sends haptic pattern data to Swift via MethodChannel.
/// Falls back silently if the channel is unavailable or Core Haptics
/// is not supported on the device.
library;

import 'package:flutter/services.dart';

import '../services/haptics_engine.dart';
import 'haptic_patterns.dart';

class IOSHapticsEngine extends HapticsEngineBase {
  static const _channel = MethodChannel('com.chromacrush/haptics');

  bool _enabled = true;
  bool _supported = false;

  @override
  Future<void> initialize() async {
    try {
      final result = await _channel.invokeMethod<bool>('initialize');
      _supported = result ?? false;
    } catch (_) {
      _supported = false;
    }
  }

  @override
  Future<void> dispose() async {
    if (!_supported) return;
    try {
      await _channel.invokeMethod<void>('dispose');
    } catch (_) {}
  }

  @override
  void playPattern(HapticPattern pattern, {double intensity = 1.0}) {
    if (!_supported || !_enabled) return;

    final def = hapticPatterns[pattern];
    if (def == null) return;

    try {
      _channel.invokeMethod<void>('playPattern', {
        'events': def.toJson(),
        'intensityScale': intensity.clamp(0.0, 1.0),
      });
    } catch (_) {}
  }

  @override
  bool get isEnabled => _enabled;

  @override
  set isEnabled(bool value) => _enabled = value;

  @override
  bool get isSupported => _supported;
}
