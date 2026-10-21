/// Shader loading, caching, and uniform management.
///
/// Attempts to load gem_base.frag via FragmentProgram.fromAsset().
/// If shaders fail (test env, GPU issue), sets shadersAvailable = false
/// and GemComponent uses Canvas-based SDF fallback.
library;

import 'dart:ui';

/// Manages the gem base shader lifecycle.
class GemShaderLibrary {
  GemShaderLibrary._();

  static final GemShaderLibrary instance = GemShaderLibrary._();

  /// Whether gem shaders loaded successfully.
  bool shadersAvailable = false;

  /// The compiled fragment program (null if unavailable).
  FragmentProgram? _gemBaseProgram;

  /// The compiled ripple background program (null if unavailable).
  FragmentProgram? _rippleProgram;

  /// Whether the ripple background shader loaded successfully.
  bool get rippleShaderAvailable => _rippleProgram != null;

  /// Load shaders. Call once at game init.
  Future<void> load() async {
    try {
      _gemBaseProgram = await FragmentProgram.fromAsset(
        'shaders/gem_base.frag',
      );
      shadersAvailable = true;
    } catch (_) {
      shadersAvailable = false;
    }

    // Load ripple shader independently — gem shaders still work if this fails.
    try {
      _rippleProgram = await FragmentProgram.fromAsset(
        'shaders/ripple_background.frag',
      );
    } catch (_) {
      _rippleProgram = null;
    }
  }

  /// Single shared gem shader instance (reused across all gems).
  FragmentShader? _sharedGemShader;

  /// Create a new gem shader instance.
  ///
  /// Returns null if shaders are unavailable.
  FragmentShader? createGemShader() {
    if (!shadersAvailable || _gemBaseProgram == null) return null;
    return _gemBaseProgram!.fragmentShader();
  }

  /// Return the shared gem shader (created once, reused by all gems).
  ///
  /// Safe because uniforms are set immediately before each drawRect call.
  FragmentShader? get sharedGemShader {
    if (!shadersAvailable || _gemBaseProgram == null) return null;
    return _sharedGemShader ??= _gemBaseProgram!.fragmentShader();
  }

  /// Create a new ripple background shader instance.
  ///
  /// Returns null if the ripple shader is unavailable.
  FragmentShader? createRippleShader() {
    if (_rippleProgram == null) return null;
    return _rippleProgram!.fragmentShader();
  }
}

/// Uniform indices for gem_base.frag.
///
/// Maps to the uniform declarations in the GLSL shader.
/// Each float uniform occupies one index. Vec2/vec3 occupy consecutive indices.
class GemUniforms {
  // u_size (vec2) — indices 0, 1
  static const int sizeX = 0;
  static const int sizeY = 1;

  // u_time (float) — index 2
  static const int time = 2;

  // u_pulse_rate (float) — index 3
  static const int pulseRate = 3;

  // u_pulse_amp (float) — index 4
  static const int pulseAmp = 4;

  // u_brightness (float) — index 5
  static const int brightness = 5;

  // u_glow_radius (float) — index 6
  static const int glowRadius = 6;

  // u_color (vec3) — indices 7, 8, 9
  static const int colorR = 7;
  static const int colorG = 8;
  static const int colorB = 9;

  // u_selected (float) — index 10
  static const int selected = 10;

  // u_shape (float) — index 11
  static const int shape = 11;

  // u_function (float) — index 12
  static const int functionType = 12;

  // u_scale (float) — index 13
  static const int scale = 13;
}

/// Uniform indices for ripple_background.frag.
class RippleUniforms {
  // u_size (vec2) — indices 0, 1
  static const int sizeX = 0;
  static const int sizeY = 1;

  // u_time (float) — index 2
  static const int time = 2;

  // u_ripple_count (float) — index 3
  static const int rippleCount = 3;

  // u_ripple0..7 (vec3 each) — indices 4..27
  // Each ripple: (originX, originY, startTime) at base + 0, 1, 2
  static int rippleOriginX(int index) => 4 + index * 3;
  static int rippleOriginY(int index) => 4 + index * 3 + 1;
  static int rippleStartTime(int index) => 4 + index * 3 + 2;

  // u_intensity (float) — index 28
  static const int intensity = 28;

  // u_tex_size (vec2) — indices 29, 30
  static const int texSizeX = 29;
  static const int texSizeY = 30;
}
