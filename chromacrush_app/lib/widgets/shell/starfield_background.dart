/// Procedural starfield — faint drifting star wisps for menu backgrounds.
///
/// Lightweight CustomPainter with a fixed pool of stars that drift slowly
/// and twinkle by cycling opacity. No shaders, no Flame dependency.
library;

import 'dart:math';

import 'package:flutter/material.dart';

/// Animated starfield widget. Place behind other content in a Stack.
class StarfieldBackground extends StatefulWidget {
  const StarfieldBackground({super.key, this.starCount = 60});

  /// Number of stars in the pool.
  final int starCount;

  @override
  State<StarfieldBackground> createState() => _StarfieldBackgroundState();
}

class _StarfieldBackgroundState extends State<StarfieldBackground>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final List<_Star> _stars;

  @override
  void initState() {
    super.initState();
    final rng = Random(42);
    _stars = List.generate(widget.starCount, (_) => _Star(rng));
    _controller = AnimationController.unbounded(vsync: this)
      ..addListener(_tick);
    _lastTime = 0;
    _controller.repeat(
      min: 0,
      max: 86400,
      period: const Duration(seconds: 86400),
    );
  }

  double _lastTime = 0;

  void _tick() {
    final now = _controller.value;
    final dt = (now - _lastTime).clamp(0.0, 0.1);
    _lastTime = now;
    for (final s in _stars) {
      s.update(dt);
    }
    // Repaint at animation frame rate (setState triggers CustomPaint rebuild).
    if (mounted) setState(() {});
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return RepaintBoundary(
      child: CustomPaint(
        painter: _StarfieldPainter(_stars),
        size: Size.infinite,
      ),
    );
  }
}

/// Single star with normalized position (0–1), drift velocity, and twinkle.
class _Star {
  _Star(Random rng)
    : x = rng.nextDouble(),
      y = rng.nextDouble(),
      radius = 0.5 + rng.nextDouble() * 1.5,
      driftX = (rng.nextDouble() - 0.5) * 0.008,
      driftY = -0.002 - rng.nextDouble() * 0.006,
      _phase = rng.nextDouble() * pi * 2,
      _twinkleSpeed = 0.4 + rng.nextDouble() * 0.8,
      _baseAlpha = 0.15 + rng.nextDouble() * 0.25;

  double x, y;
  final double radius;
  final double driftX, driftY;
  final double _phase;
  final double _twinkleSpeed;
  final double _baseAlpha;
  double _time = 0;

  double get alpha =>
      (_baseAlpha + sin(_phase + _time * _twinkleSpeed) * 0.15).clamp(0.0, 1.0);

  void update(double dt) {
    _time += dt;
    x += driftX * dt;
    y += driftY * dt;
    // Wrap around edges.
    if (x < 0) x += 1;
    if (x > 1) x -= 1;
    if (y < 0) y += 1;
    if (y > 1) y -= 1;
  }
}

class _StarfieldPainter extends CustomPainter {
  _StarfieldPainter(this.stars);
  final List<_Star> stars;

  @override
  void paint(Canvas canvas, Size size) {
    for (final s in stars) {
      final paint = Paint()
        ..color = Color.fromRGBO(255, 255, 255, s.alpha)
        ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 1.0);
      canvas.drawCircle(
        Offset(s.x * size.width, s.y * size.height),
        s.radius,
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _StarfieldPainter oldDelegate) => true;
}
