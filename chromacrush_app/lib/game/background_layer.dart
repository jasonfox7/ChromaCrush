/// Full-screen background — three scrolling cloud layers + ripple rings.
///
/// Uses the same seamless cloud PNG at 100%, 75%, and 50% scale,
/// each drifting in a different direction. A ColorFilter tints the dark
/// texture pixels to a visible purple-gray so clouds show against the
/// dark base. Intensity drives scroll speed and tint color.
/// Ripple rings drawn as expanding Canvas circles on gem matches.
library;

import 'dart:math';
import 'dart:typed_data';
import 'dart:ui';

import 'package:flame/components.dart';
import 'package:flutter/services.dart' show rootBundle;

import '../config/visual_config.dart';
import '../config/visual_theme_service.dart';

class BackgroundLayer extends PositionComponent {
  BackgroundLayer({required Vector2 screenSize, required this.theme})
    : super(position: Vector2.zero(), size: screenSize, priority: -10);

  final VisualThemeBase theme;

  Image? _backgroundImage;
  double _elapsed = 0.0;
  double _intensity = 0.0;
  double _targetIntensity = 0.0;

  /// Lerp speed: fraction of the gap closed per second.
  /// 2.0 ≈ smooth ~0.5 s settle time.
  static const double _intensityLerpSpeed = 2.0;

  // Scroll offsets (accumulated in update).
  double _scroll1X = 0, _scroll1Y = 0;
  double _scroll2X = 0, _scroll2Y = 0;
  double _scroll3X = 0, _scroll3Y = 0;

  // Ripple sources.
  final List<({double originX, double originY, double startTime})> _ripples =
      [];

  /// Set the game intensity (0.0 calm → 1.0 stormy).
  void setIntensity(double value) {
    _targetIntensity = value.clamp(0.0, 1.0);
  }

  /// Add a ripple at the given screen coordinates.
  void addRipple(double screenX, double screenY) {
    if (_ripples.length >= kMaxRipples) {
      _ripples.removeAt(0);
    }
    _ripples.add((originX: screenX, originY: screenY, startTime: _elapsed));
  }

  @override
  Future<void> onLoad() async {
    try {
      final data = await rootBundle.load('assets/graphics/background.png');
      final codec = await instantiateImageCodec(data.buffer.asUint8List());
      final frame = await codec.getNextFrame();
      _backgroundImage = frame.image;
    } catch (_) {
      _backgroundImage = null;
    }
  }

  @override
  void update(double dt) {
    super.update(dt);
    _elapsed += dt;

    // Smoothly approach target intensity.
    final diff = _targetIntensity - _intensity;
    if (diff.abs() < 0.001) {
      _intensity = _targetIntensity;
    } else {
      _intensity += diff * (_intensityLerpSpeed * dt).clamp(0.0, 1.0);
    }

    final speed = kBackgroundBaseSpeed + _intensity * kBackgroundIntensitySpeed;

    // Layer 1 (front, 100%): drift right + slightly down.
    _scroll1X += kBgLayer1SpeedX * speed * dt;
    _scroll1Y += kBgLayer1SpeedY * speed * dt;

    // Layer 2 (mid, 75%): drift left.
    _scroll2X += kBgLayer2SpeedX * speed * dt;
    _scroll2Y += kBgLayer2SpeedY * speed * dt;

    // Layer 3 (back, 50%): drift right + up.
    _scroll3X += kBgLayer3SpeedX * speed * dt;
    _scroll3Y += kBgLayer3SpeedY * speed * dt;

    // Prune expired ripples.
    _ripples.removeWhere((r) => (_elapsed - r.startTime) > kRippleLifetime);
  }

  @override
  void render(Canvas canvas) {
    final rect = Rect.fromLTWH(0, 0, size.x, size.y);

    // Solid dark base.
    canvas.drawRect(rect, Paint()..color = theme.backgroundBase);

    final image = _backgroundImage;
    if (image != null) {
      final tint = Color.lerp(
        theme.backgroundCalmTint,
        theme.backgroundStormTint,
        _intensity,
      )!;

      // Layer 3 (back): 50% apparent size.
      _drawLayer(canvas, rect, image, 2.0, _scroll3X, _scroll3Y, tint);

      // Layer 2 (mid): 75% apparent size.
      _drawLayer(canvas, rect, image, 1.333, _scroll2X, _scroll2Y, tint);

      // Layer 1 (front): 100% scale.
      _drawLayer(canvas, rect, image, 1.0, _scroll1X, _scroll1Y, tint);
    }

    // Ripple rings on top of everything.
    _drawRipples(canvas);
  }

  void _drawLayer(
    Canvas canvas,
    Rect rect,
    Image image,
    double scale,
    double scrollX,
    double scrollY,
    Color tint,
  ) {
    final matrix = Float64List(16);
    matrix[0] = scale;
    matrix[5] = scale;
    matrix[10] = 1.0;
    matrix[15] = 1.0;
    matrix[12] = scrollX * scale;
    matrix[13] = scrollY * scale;

    final paint = Paint()
      ..shader = ImageShader(
        image,
        TileMode.repeated,
        TileMode.repeated,
        matrix,
      )
      ..colorFilter = ColorFilter.mode(tint, BlendMode.modulate);

    canvas.drawRect(rect, paint);
  }

  void _drawRipples(Canvas canvas) {
    for (final r in _ripples) {
      final age = _elapsed - r.startTime;
      if (age < 0 || age > kRippleLifetime) continue;

      final radius = age * kRippleSpeed;
      final decay = (1.0 - age / kRippleLifetime);
      final alpha = (decay * decay * 0.15).clamp(0.0, 1.0);

      final paint = Paint()
        ..style = PaintingStyle.stroke
        ..strokeWidth = 2.0
        ..color = Color.fromRGBO(
          theme.rippleRgb[0],
          theme.rippleRgb[1],
          theme.rippleRgb[2],
          alpha,
        );

      canvas.drawCircle(Offset(r.originX, r.originY), radius, paint);

      // Second fainter ring trailing behind.
      if (radius > kRippleInnerOffset) {
        final innerPaint = Paint()
          ..style = PaintingStyle.stroke
          ..strokeWidth = 1.5
          ..color = Color.fromRGBO(
            theme.rippleRgb[0],
            theme.rippleRgb[1],
            theme.rippleRgb[2],
            alpha * 0.5,
          );
        canvas.drawCircle(
          Offset(r.originX, r.originY),
          max(radius - kRippleInnerOffset, 0),
          innerPaint,
        );
      }
    }
  }
}
