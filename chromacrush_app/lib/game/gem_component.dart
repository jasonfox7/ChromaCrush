/// Individual gem — shader-based SDF shapes with Canvas fallback.
///
/// Phase 2: PositionComponent with custom render(). Uses gem_base.frag
/// shader when available (iOS/Impeller), falls back to Canvas SDF
/// shapes in test/Skia environments.
library;

import 'dart:async';
import 'dart:ui' hide TextStyle;

import 'package:flutter/painting.dart' show TextStyle;

import 'package:flame/components.dart';
import 'package:flame/effects.dart';
import 'package:flame/events.dart';

import '../config/animation_timings.dart';
import '../config/visual_config.dart';
import '../config/visual_theme_service.dart';
import '../extensions/flame_effects_ext.dart';
import '../models/gem_type.dart';
import 'gem_shader_library.dart';

class GemComponent extends PositionComponent with TapCallbacks {
  GemComponent({
    required this.gemType,
    required this.gridRow,
    required this.gridCol,
    required this.theme,
    required double cellSize,
    Vector2? initialPosition,
    this.gemFunction = GemFunction.neutral,
    int? rawFunc,
    this.onTap,
  }) : _cellSize = cellSize,
       rawFunction = rawFunc ?? 0,
       super(
         size: Vector2.all(cellSize),
         position: initialPosition ?? Vector2.zero(),
         anchor: Anchor.topLeft,
       );

  final double _cellSize;
  final VisualThemeBase theme;
  GemType gemType;
  GemFunction gemFunction;

  /// Raw func_grid value — needed for mega gem shader mapping (11-44).
  int rawFunction;
  int gridRow;
  int gridCol;

  /// Callback when this gem is tapped.
  void Function(int row, int col)? onTap;

  /// Paint for Canvas fallback rendering.
  final Paint _fillPaint = Paint();
  final Paint _glowPaint = Paint();

  /// Cached glow blur filter (avoid recreating GPU convolution resources).
  static final MaskFilter _glowBlur = MaskFilter.blur(
    BlurStyle.normal,
    kGemGlowBlurSigma,
  );

  /// Elapsed time for shader animation.
  double _elapsedTime = 0;

  /// Intensity-driven overrides (set by ChromaCrushGame from IntensityService).
  double? pulseRateOverride;
  double? pulseAmpOverride;

  /// Alpha multiplier for dimming (0.0–1.0). Used by status bar to dim empty slots.
  double paintAlpha = 1.0;

  /// Symbol label for special gems (↔, ↕, ✸, ✦, etc.).
  TextComponent? _symbolLabel;

  @override
  Future<void> onLoad() async {
    await super.onLoad();
    _updatePaints();

    _symbolLabel = TextComponent(
      text: _labelText(),
      textRenderer: TextPaint(
        style: const TextStyle(
          fontSize: 12,
          color: Color(0xFFFFFFFF),
          fontWeight: FontWeight.bold,
        ),
      ),
      position: Vector2(_cellSize / 2, _cellSize / 2),
      anchor: Anchor.center,
    );
    add(_symbolLabel!);
  }

  /// Resolve render color — tinted for obstacles with special requirements,
  /// normal gem color otherwise.
  Color _resolveColor() {
    if (gemType == GemType.obstacle && rawFunction > 0) {
      return theme.obstacleColor(rawFunction);
    }
    return theme.gemColor(gemType.value);
  }

  void _updatePaints() {
    final color = _resolveColor();
    _fillPaint.color = color;
    _glowPaint
      ..color = color.withValues(alpha: 0.3)
      ..maskFilter = _glowBlur;
  }

  /// Whether this gem is currently selected.
  bool _selected = false;
  bool get isSelected => _selected;

  void setSelected(bool selected) {
    if (_selected == selected) return;
    _selected = selected;
  }

  /// Update gem color and repaint.
  void updateGemType(GemType newType) {
    gemType = newType;
    _updatePaints();
    _symbolLabel?.text = _labelText();
  }

  /// Update gem function (special ability).
  void updateGemFunction(GemFunction newFunction, {int? raw}) {
    gemFunction = newFunction;
    rawFunction = raw ?? newFunction.value;
    _updatePaints();
    _symbolLabel?.text = _labelText();
  }

  /// Label text: symbols for special gems overlaid on the gem center.
  /// Uses rawFunction so megas (11-44) show dual symbols (e.g. ↔✸).
  String _labelText() {
    return theme.specialSymbol(rawFunction);
  }

  /// Update grid position tracking (does NOT move visually — use effects for that).
  void updateGridPosition(int row, int col) {
    gridRow = row;
    gridCol = col;
  }

  @override
  void onTapUp(TapUpEvent event) {
    onTap?.call(gridRow, gridCol);
  }

  @override
  void update(double dt) {
    super.update(dt);
    _elapsedTime += dt;
  }

  @override
  void render(Canvas canvas) {
    if (paintAlpha < 1.0) {
      canvas.saveLayer(
        null,
        Paint()
          ..color = Color.fromARGB((paintAlpha * 255).round(), 255, 255, 255),
      );
    }
    final shader = GemShaderLibrary.instance.sharedGemShader;
    if (shader != null) {
      _renderShader(canvas, shader);
    } else {
      _renderFallback(canvas);
    }
    if (paintAlpha < 1.0) {
      canvas.restore();
    }
  }

  // ---------------------------------------------------------------------------
  // Shader rendering
  // ---------------------------------------------------------------------------

  void _renderShader(Canvas canvas, FragmentShader shader) {
    final color = _resolveColor();

    // Expand render rect so SDF glow fades naturally instead of clipping.
    const pad = kGemGlowPadding;
    final renderW = size.x + pad * 2;
    final renderH = size.y + pad * 2;

    // Set uniforms.
    shader.setFloat(GemUniforms.sizeX, renderW);
    shader.setFloat(GemUniforms.sizeY, renderH);
    shader.setFloat(GemUniforms.time, _elapsedTime);
    shader.setFloat(
      GemUniforms.pulseRate,
      pulseRateOverride ?? theme.gemPulseRate,
    );
    shader.setFloat(
      GemUniforms.pulseAmp,
      pulseAmpOverride ?? theme.gemPulseAmplitude,
    );
    shader.setFloat(
      GemUniforms.brightness,
      theme.gemBrightness + _flashOverlay * 2.0,
    );
    shader.setFloat(GemUniforms.glowRadius, theme.gemGlowRadius);
    shader.setFloat(GemUniforms.colorR, color.r);
    shader.setFloat(GemUniforms.colorG, color.g);
    shader.setFloat(GemUniforms.colorB, color.b);
    shader.setFloat(GemUniforms.selected, _selected ? 1.0 : 0.0);
    final shapeIdx = (gemType == GemType.obstacle && rawFunction >= 10)
        ? theme.wallShape
        : theme.gemShape(gemType.value);
    shader.setFloat(GemUniforms.shape, shapeIdx.toDouble());
    shader.setFloat(
      GemUniforms.functionType,
      funcToShaderValue(rawFunction).toDouble(),
    );
    shader.setFloat(GemUniforms.scale, renderW / size.x);

    final paint = Paint()..shader = shader;
    canvas.drawRect(Rect.fromLTWH(-pad, -pad, renderW, renderH), paint);
  }

  // ---------------------------------------------------------------------------
  // Canvas SDF fallback
  // ---------------------------------------------------------------------------

  void _renderFallback(Canvas canvas) {
    final cx = size.x / 2;
    final cy = size.y / 2;
    final r = size.x * 0.4;
    final shape = (gemType == GemType.obstacle && rawFunction >= 10)
        ? theme.wallShape
        : theme.gemShape(gemType.value);

    // Glow layer.
    _drawFallbackShape(canvas, cx, cy, r + 3, _glowPaint, shape);

    // Fill layer.
    _drawFallbackShape(canvas, cx, cy, r, _fillPaint, shape);

    // Chromatic conversion flash: white shape overlay.
    if (_flashOverlay > 0.0) {
      final flashPaint = Paint()
        ..color = Color.fromRGBO(255, 255, 255, _flashOverlay * 0.8);
      _drawFallbackShape(canvas, cx, cy, r, flashPaint, shape);
    }

    // Selection ring.
    if (_selected) {
      final ringPaint = Paint()
        ..color = const Color(0x80FFFFFF)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 3;
      _drawFallbackShape(canvas, cx, cy, r + 2, ringPaint, shape);
    }
  }

  /// Draw faceted gemstone shape matching the shader polygon SDFs.
  ///
  /// 0 (red): round brilliant 10-gon, 1 (blue): marquise diamond 8-gon,
  /// 2 (green): emerald 8-gon, 3 (yellow): cushion 12-gon,
  /// 4 (purple): heart 14-gon, 5 (orange): pear 14-gon.
  void _drawFallbackShape(
    Canvas canvas,
    double cx,
    double cy,
    double r,
    Paint paint,
    int shape,
  ) {
    switch (shape) {
      case 0: // Round Brilliant — 10-facet polygon
        final s = r * 0.82;
        final path = Path()
          ..moveTo(cx, cy - s)
          ..lineTo(cx + s * 0.588, cy - s * 0.809)
          ..lineTo(cx + s * 0.951, cy - s * 0.309)
          ..lineTo(cx + s * 0.951, cy + s * 0.309)
          ..lineTo(cx + s * 0.588, cy + s * 0.809)
          ..lineTo(cx, cy + s)
          ..lineTo(cx - s * 0.588, cy + s * 0.809)
          ..lineTo(cx - s * 0.951, cy + s * 0.309)
          ..lineTo(cx - s * 0.951, cy - s * 0.309)
          ..lineTo(cx - s * 0.588, cy - s * 0.809)
          ..close();
        canvas.drawPath(path, paint);
      case 1: // Marquise Diamond — 8-facet elongated kite
        final s = r * 0.82;
        final path = Path()
          ..moveTo(cx, cy - s)
          ..lineTo(cx + s * 0.35, cy - s * 0.55)
          ..lineTo(cx + s * 0.55, cy)
          ..lineTo(cx + s * 0.35, cy + s * 0.55)
          ..lineTo(cx, cy + s)
          ..lineTo(cx - s * 0.35, cy + s * 0.55)
          ..lineTo(cx - s * 0.55, cy)
          ..lineTo(cx - s * 0.35, cy - s * 0.55)
          ..close();
        canvas.drawPath(path, paint);
      case 3: // Cushion Cut — 12-facet rounded square
        final s = r * 0.68;
        final path = Path()
          ..moveTo(cx - s * 0.65, cy - s)
          ..lineTo(cx + s * 0.65, cy - s)
          ..lineTo(cx + s * 0.88, cy - s * 0.88)
          ..lineTo(cx + s, cy - s * 0.65)
          ..lineTo(cx + s, cy + s * 0.65)
          ..lineTo(cx + s * 0.88, cy + s * 0.88)
          ..lineTo(cx + s * 0.65, cy + s)
          ..lineTo(cx - s * 0.65, cy + s)
          ..lineTo(cx - s * 0.88, cy + s * 0.88)
          ..lineTo(cx - s, cy + s * 0.65)
          ..lineTo(cx - s, cy - s * 0.65)
          ..lineTo(cx - s * 0.88, cy - s * 0.88)
          ..close();
        canvas.drawPath(path, paint);
      case 4: // Heart Cut — 14-facet heart
        final s = r * 0.72;
        final path = Path()
          ..moveTo(cx, cy - s * 0.35)
          ..lineTo(cx + s * 0.22, cy - s * 0.65)
          ..lineTo(cx + s * 0.45, cy - s * 0.82)
          ..lineTo(cx + s * 0.68, cy - s * 0.72)
          ..lineTo(cx + s * 0.78, cy - s * 0.42)
          ..lineTo(cx + s * 0.68, cy - s * 0.05)
          ..lineTo(cx + s * 0.42, cy + s * 0.28)
          ..lineTo(cx, cy + s * 0.85)
          ..lineTo(cx - s * 0.42, cy + s * 0.28)
          ..lineTo(cx - s * 0.68, cy - s * 0.05)
          ..lineTo(cx - s * 0.78, cy - s * 0.42)
          ..lineTo(cx - s * 0.68, cy - s * 0.72)
          ..lineTo(cx - s * 0.45, cy - s * 0.82)
          ..lineTo(cx - s * 0.22, cy - s * 0.65)
          ..close();
        canvas.drawPath(path, paint);
      case 5: // Pear Cut — 14-facet teardrop
        final s = r * 0.75;
        final path = Path()
          ..moveTo(cx, cy - s * 0.68)
          ..lineTo(cx + s * 0.32, cy - s * 0.6)
          ..lineTo(cx + s * 0.52, cy - s * 0.38)
          ..lineTo(cx + s * 0.58, cy - s * 0.08)
          ..lineTo(cx + s * 0.5, cy + s * 0.18)
          ..lineTo(cx + s * 0.35, cy + s * 0.42)
          ..lineTo(cx + s * 0.18, cy + s * 0.62)
          ..lineTo(cx, cy + s * 0.78)
          ..lineTo(cx - s * 0.18, cy + s * 0.62)
          ..lineTo(cx - s * 0.35, cy + s * 0.42)
          ..lineTo(cx - s * 0.5, cy + s * 0.18)
          ..lineTo(cx - s * 0.58, cy - s * 0.08)
          ..lineTo(cx - s * 0.52, cy - s * 0.38)
          ..lineTo(cx - s * 0.32, cy - s * 0.6)
          ..close();
        canvas.drawPath(path, paint);
      default: // 2: Emerald Cut — 8-facet chamfered box
        final hw = r / 1.4;
        final hh = r;
        final c = 0.414 * hw;
        final path = Path()
          ..moveTo(cx - hw + c, cy - hh)
          ..lineTo(cx + hw - c, cy - hh)
          ..lineTo(cx + hw, cy - hh + c)
          ..lineTo(cx + hw, cy + hh - c)
          ..lineTo(cx + hw - c, cy + hh)
          ..lineTo(cx - hw + c, cy + hh)
          ..lineTo(cx - hw, cy + hh - c)
          ..lineTo(cx - hw, cy - hh + c)
          ..close();
        canvas.drawPath(path, paint);
    }
  }

  // ---------------------------------------------------------------------------
  // Animation helpers
  // ---------------------------------------------------------------------------

  /// Animate moving to a new screen position over [duration].
  Future<void> animateMoveTo(Vector2 target, {required Duration duration}) {
    final completer = Completer<void>();
    add(
      MoveEffect.to(
        target,
        EffectController(duration: duration.inMilliseconds / 1000.0),
        onComplete: completer.complete,
      ),
    );
    return completer.future;
  }

  /// Animate removal: scale to 0 + fade out.
  Future<void> animateRemoval({Duration duration = kGemRemovalDuration}) {
    final completer = Completer<void>();
    final seconds = duration.inMilliseconds / 1000.0;
    add(
      ScaleEffect.to(
        Vector2.zero(),
        EffectController(duration: seconds),
        onComplete: () {
          removeFromParent();
          completer.complete();
        },
      ),
    );
    return completer.future;
  }

  /// Animate moving with elastic bounce (overshoot + diminishing bounces).
  Future<void> animateMoveToElastic(
    Vector2 target, {
    required Duration duration,
    double overshoot = 0.15,
    int bounces = 2,
  }) {
    final completer = Completer<void>();
    add(
      MoveEffect.to(
        target,
        ElasticBounceController(
          duration: duration.inMilliseconds / 1000.0,
          overshoot: overshoot,
          bounces: bounces,
        ),
        onComplete: completer.complete,
      ),
    );
    return completer.future;
  }

  /// Animate appearing: scale from 0 to 1.
  Future<void> animateAppear({Duration duration = kGemAppearDuration}) {
    final completer = Completer<void>();
    final seconds = duration.inMilliseconds / 1000.0;
    scale = Vector2.zero();
    add(
      ScaleEffect.to(
        Vector2.all(1.0),
        EffectController(duration: seconds),
        onComplete: completer.complete,
      ),
    );
    return completer.future;
  }

  /// White overlay intensity for chromatic conversion flash (0.0–1.0).
  double _flashOverlay = 0.0;

  /// Set the flash overlay intensity (0.0 = off, 1.0 = full white).
  void setFlashOverlay(double value) {
    _flashOverlay = value.clamp(0.0, 1.0);
  }

  /// Animate a pulse: scale 1.0 → peak → 1.0 (highlights without disappearing).
  Future<void> animatePulse({
    Duration duration = kGemPulseDuration,
    double peakScale = kGemPulsePeakScale,
  }) {
    final completer = Completer<void>();
    final half = duration.inMilliseconds / 2000.0;
    add(
      ScaleEffect.to(
        Vector2.all(peakScale),
        EffectController(duration: half),
        onComplete: () {
          add(
            ScaleEffect.to(
              Vector2.all(1.0),
              EffectController(duration: half),
              onComplete: completer.complete,
            ),
          );
        },
      ),
    );
    return completer.future;
  }
}
