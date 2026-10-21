/// Visual theme service — loads visual_theme.json and provides typed access.
///
/// Injected via Provider in main.dart. All components read visual values
/// through this service instead of hardcoded constants.
///
/// Currently loads from local assets (baked into the app bundle at build time).
/// To make server-controlled: add a GET /api/v1/config/visual-theme endpoint,
/// fetch here at startup, and fall back to local assets on failure.
library;

import 'dart:convert';
import 'dart:ui';

import 'package:flutter/services.dart' show rootBundle;

/// Abstract base for testability.
abstract class VisualThemeBase {
  Color gemColor(int gemTypeValue);

  /// Obstacle color tinted by special requirement.
  ///
  /// Plain glass (funcValue 0) returns the base obstacle grey.
  /// Specials (1 = H-blast, 2 = V-blast, 3 = bomb) return a subtly tinted
  /// variant derived via HSL: same lightness as the base grey, fixed
  /// saturation, and a hue chosen to avoid the 6 gem colors.
  Color obstacleColor(int funcValue);

  int gemShape(int gemTypeValue);
  double get gemPulseRate;
  double get gemPulseAmplitude;
  double get gemBrightness;
  double get gemGlowRadius;
  String specialSymbol(int funcValue);
  String gemName(int gemTypeValue);
  String specialName(int funcValue);
  String megaName(int megaFuncValue);
  Color get wallColor;
  int get wallShape;
  String get wallSymbol;
  Color particleColor(String effectName);
  List<Color> get chromaticRainColors;
  List<Color> get victoryConfettiColors;
  Color get backgroundBase;
  Color get backgroundCalmTint;
  Color get backgroundStormTint;
  List<int> get rippleRgb;
}

/// Concrete implementation loading from assets/config/visual_theme.json.
class VisualThemeService implements VisualThemeBase {
  VisualThemeService._();

  late final Map<int, Color> _gemColors;
  late final Map<int, int> _gemShapes;
  late final double _pulseRate;
  late final double _pulseAmplitude;
  late final double _brightness;
  late final double _glowRadius;
  late final Map<int, String> _specialSymbols;
  late final Map<int, String> _gemNames;
  late final Map<int, String> _specialNames;
  late final Map<int, String> _megaNames;
  late final Map<String, Color> _particleColors;
  late final List<Color> _chromaticRainColors;
  late final List<Color> _victoryConfettiColors;
  late final Color _bgBase;
  late final Color _bgCalmTint;
  late final Color _bgStormTint;
  late final List<int> _rippleRgb;
  late final Color _wallColor;
  late final int _wallShape;
  late final String _wallSymbol;

  /// Load the theme from the asset bundle.
  static Future<VisualThemeService> load() async {
    final service = VisualThemeService._();
    try {
      final jsonStr = await rootBundle.loadString(
        'assets/config/visual_theme.json',
      );
      final data = json.decode(jsonStr) as Map<String, dynamic>;
      service._parse(data);
    } catch (_) {
      service._useDefaults();
    }
    return service;
  }

  /// Create from a pre-parsed map (for tests or direct construction).
  static VisualThemeService fromMap(Map<String, dynamic> data) {
    final service = VisualThemeService._();
    service._parse(data);
    return service;
  }

  void _parse(Map<String, dynamic> data) {
    // Gem colors.
    final colorsMap = data['gem_colors'] as Map<String, dynamic>? ?? {};
    _gemColors = colorsMap.map(
      (k, v) => MapEntry(int.parse(k), _hexToColor(v as String)),
    );

    // Gem shapes.
    final shapesMap = data['gem_shapes'] as Map<String, dynamic>? ?? {};
    _gemShapes = shapesMap.map(
      (k, v) => MapEntry(int.parse(k), (v as num).toInt()),
    );

    // Shader params.
    final shader = data['gem_shader'] as Map<String, dynamic>? ?? {};
    _pulseRate = (shader['pulse_rate'] as num?)?.toDouble() ?? 1.5;
    _pulseAmplitude = (shader['pulse_amplitude'] as num?)?.toDouble() ?? 0.3;
    _brightness = (shader['brightness'] as num?)?.toDouble() ?? 1.0;
    _glowRadius = (shader['glow_radius'] as num?)?.toDouble() ?? 0.3;

    // Special symbols.
    final symsMap = data['special_symbols'] as Map<String, dynamic>? ?? {};
    _specialSymbols = symsMap.map(
      (k, v) => MapEntry(int.parse(k), v as String),
    );

    // Gem display names.
    final gemNamesMap = data['gem_names'] as Map<String, dynamic>? ?? {};
    _gemNames = gemNamesMap.map((k, v) => MapEntry(int.parse(k), v as String));

    // Special gem display names.
    final specNamesMap = data['special_names'] as Map<String, dynamic>? ?? {};
    _specialNames = specNamesMap.map(
      (k, v) => MapEntry(int.parse(k), v as String),
    );

    // Mega combo display names.
    final megaNamesMap = data['mega_names'] as Map<String, dynamic>? ?? {};
    _megaNames = megaNamesMap.map(
      (k, v) => MapEntry(int.parse(k), v as String),
    );

    // Particle colors.
    final partMap = data['particle_colors'] as Map<String, dynamic>? ?? {};
    _particleColors = partMap.map(
      (k, v) => MapEntry(k, _hexToColor(v as String)),
    );

    // Color arrays.
    _chromaticRainColors = _parseColorList(data['chromatic_rain_colors']);
    _victoryConfettiColors = _parseColorList(data['victory_confetti_colors']);

    // Background.
    final bg = data['background'] as Map<String, dynamic>? ?? {};
    _bgBase = _hexToColor(bg['base'] as String? ?? '0D0D14');
    _bgCalmTint = _hexToColor(bg['calm_tint'] as String? ?? 'AA77DD');
    _bgStormTint = _hexToColor(bg['storm_tint'] as String? ?? 'DD8844');
    final rgb = bg['ripple_rgb'] as List<dynamic>?;
    _rippleRgb = rgb != null
        ? rgb.map((e) => (e as num).toInt()).toList()
        : [80, 60, 120];

    // Wall config.
    final wall = data['wall'] as Map<String, dynamic>? ?? {};
    _wallColor = _hexToColor(wall['color'] as String? ?? '4A4A5A');
    _wallShape = (wall['shape'] as num?)?.toInt() ?? 5;
    _wallSymbol = wall['symbol'] as String? ?? '\u25A0';
  }

  void _useDefaults() {
    _gemColors = {
      1: const Color(0xFFFF2D55),
      2: const Color(0xFF007AFF),
      3: const Color(0xFF34C759),
      4: const Color(0xFFFFCC00),
      5: const Color(0xFFAF52DE),
      6: const Color(0xFFFF9500),
    };
    _gemShapes = {1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5};
    _pulseRate = 1.5;
    _pulseAmplitude = 0.3;
    _brightness = 1.0;
    _glowRadius = 0.3;
    _specialSymbols = {1: '\u2194', 2: '\u2195', 3: '\u2738', 4: '\u2726'};
    _gemNames = {};
    _specialNames = {};
    _megaNames = {};
    _particleColors = {
      'ambient': const Color(0xFFFFFFFF),
      'match_burst_bright': const Color(0xFFFFFFFF),
      'line_sweep': const Color(0xFFFFD700),
      'radial_wave_start': const Color(0xFFFF6B00),
      'radial_wave_end': const Color(0xFFFFCC00),
      'fusion_storm_start': const Color(0xFFFFD700),
      'fusion_storm_end': const Color(0xFFFF6B00),
      'mega_merge_sparks': const Color(0xFFFFD700),
      'mega_merge_bright': const Color(0xFFFFFFFF),
      'mega_activation': const Color(0xFFFFD700),
      'mega_activation_bright': const Color(0xFFFFFFFF),
      'near_miss_sparkle': const Color(0xFFFFFFFF),
      'defeat_dust_dark': const Color(0xFF666666),
      'defeat_dust_light': const Color(0xFF999999),
    };
    _chromaticRainColors = const [
      Color(0xFFFF2D55),
      Color(0xFF007AFF),
      Color(0xFF34C759),
      Color(0xFFFFCC00),
      Color(0xFFAF52DE),
      Color(0xFFFF9500),
    ];
    _victoryConfettiColors = const [
      Color(0xFFFF2D55),
      Color(0xFF007AFF),
      Color(0xFF34C759),
      Color(0xFFFFCC00),
      Color(0xFFAF52DE),
      Color(0xFFFF9500),
    ];
    _bgBase = const Color(0xFF0D0D14);
    _bgCalmTint = const Color(0xFFAA77DD);
    _bgStormTint = const Color(0xFFDD8844);
    _rippleRgb = [80, 60, 120];
    _wallColor = const Color(0xFF4A4A5A);
    _wallShape = 5;
    _wallSymbol = '\u25A0';
  }

  // -----------------------------------------------------------------------
  // VisualThemeBase implementation
  // -----------------------------------------------------------------------

  @override
  Color gemColor(int gemTypeValue) =>
      _gemColors[gemTypeValue] ?? const Color(0xFFFFFFFF);

  @override
  Color obstacleColor(int funcValue) {
    if (funcValue >= 10) return _wallColor;
    final base = gemColor(7);
    if (funcValue <= 0) return base;

    // Extract lightness from the base grey via RGB→HSL.
    final r = base.r;
    final g = base.g;
    final b = base.b;
    final cMax = r > g ? (r > b ? r : b) : (g > b ? g : b);
    final cMin = r < g ? (r < b ? r : b) : (g < b ? g : b);
    final l = (cMax + cMin) / 2.0;

    // Fixed saturation — visible tint but still reads as "grey-ish".
    const s = 0.30;

    // Hues in the gaps between the 6 gem palette colors.
    const hueMap = <int, double>{
      1: 180.0, // H-blast → teal  (gap between green 135° and blue 211°)
      2: 90.0, // V-blast → chartreuse (gap between yellow 48° and green 135°)
      3: 250.0, // Bomb → indigo (gap between blue 211° and purple 277°)
    };
    final h = hueMap[funcValue] ?? 0.0;

    return _hslToColor(h, s, l);
  }

  /// Convert HSL (h 0-360, s 0-1, l 0-1) to an opaque Color.
  static Color _hslToColor(double h, double s, double l) {
    final c = (1.0 - (2.0 * l - 1.0).abs()) * s;
    final x = c * (1.0 - ((h / 60.0) % 2.0 - 1.0).abs());
    final m = l - c / 2.0;

    double r, g, b;
    if (h < 60) {
      r = c; g = x; b = 0;
    } else if (h < 120) {
      r = x; g = c; b = 0;
    } else if (h < 180) {
      r = 0; g = c; b = x;
    } else if (h < 240) {
      r = 0; g = x; b = c;
    } else if (h < 300) {
      r = x; g = 0; b = c;
    } else {
      r = c; g = 0; b = x;
    }

    return Color.fromARGB(
      255,
      ((r + m) * 255).round().clamp(0, 255),
      ((g + m) * 255).round().clamp(0, 255),
      ((b + m) * 255).round().clamp(0, 255),
    );
  }

  @override
  int gemShape(int gemTypeValue) =>
      _gemShapes[gemTypeValue] ?? (gemTypeValue - 1).clamp(0, 5);

  @override
  Color get wallColor => _wallColor;

  @override
  int get wallShape => _wallShape;

  @override
  String get wallSymbol => _wallSymbol;

  @override
  double get gemPulseRate => _pulseRate;

  @override
  double get gemPulseAmplitude => _pulseAmplitude;

  @override
  double get gemBrightness => _brightness;

  @override
  double get gemGlowRadius => _glowRadius;

  @override
  String specialSymbol(int funcValue) {
    // Mega gems (11-44): compose symbols from both fused specials.
    if (funcValue >= 11) {
      final a = funcValue ~/ 10;
      final b = funcValue % 10;
      if (a >= 1 && a <= 4 && b >= 1 && b <= 4) {
        return '${_specialSymbols[a] ?? ''}${_specialSymbols[b] ?? ''}';
      }
    }
    // Invincible walls (func == 10).
    if (funcValue >= 10) return _wallSymbol;
    return _specialSymbols[funcValue] ?? '';
  }

  @override
  String gemName(int gemTypeValue) =>
      _gemNames[gemTypeValue] ?? 'Gem $gemTypeValue';

  @override
  String specialName(int funcValue) =>
      _specialNames[funcValue] ?? 'Special $funcValue';

  @override
  String megaName(int megaFuncValue) =>
      _megaNames[megaFuncValue] ?? 'Mega $megaFuncValue';

  @override
  Color particleColor(String effectName) =>
      _particleColors[effectName] ?? const Color(0xFFFFFFFF);

  @override
  List<Color> get chromaticRainColors => _chromaticRainColors;

  @override
  List<Color> get victoryConfettiColors => _victoryConfettiColors;

  @override
  Color get backgroundBase => _bgBase;

  @override
  Color get backgroundCalmTint => _bgCalmTint;

  @override
  Color get backgroundStormTint => _bgStormTint;

  @override
  List<int> get rippleRgb => _rippleRgb;

  // -----------------------------------------------------------------------
  // Helpers
  // -----------------------------------------------------------------------

  static Color _hexToColor(String hex) {
    final h = hex.replaceFirst('#', '');
    return Color(int.parse('FF$h', radix: 16));
  }

  static List<Color> _parseColorList(dynamic raw) {
    if (raw is! List) return [];
    return raw.map((e) => _hexToColor(e as String)).toList();
  }
}
