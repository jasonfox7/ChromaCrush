/// Faked bot move preview — mini 2-row board animation.
///
/// Triggered by [BotScoreUpdatedEvent]. Generates a random 2×8 gem grid
/// with a pre-arranged 3-match, animates a swap + pop, fades out.
/// Pure CustomPaint — no Flame, no API calls.
library;

import 'dart:async';
import 'dart:math';
import 'dart:ui' as ui;

import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../config/animation_timings.dart';
import '../../config/game_config.dart';
import '../../config/visual_theme_service.dart';
import '../../models/gem_type.dart';
import '../../services/event_bus.dart';
import '../../theme/chroma_theme.dart';

/// Preview width — roughly 65% of the main board (366px).
const double _kPreviewWidth = kBotPreviewWidth;

/// Cell sizing for mini grid.
const int _kCols = 8;
const int _kRows = 2;
const double _kCellSize = kBotPreviewCellSize;
const double _kCellSpacing = kBotPreviewCellSpacing;
const double _kCellStride = _kCellSize + _kCellSpacing;
const double _kGridWidth = _kCellStride * _kCols - _kCellSpacing;
const double _kGridHeight = _kCellStride * _kRows - _kCellSpacing;

/// Total animation duration.
const Duration _kAnimDuration = kBotPreviewDuration;

/// Standard gem types for random generation (excludes empty).
const _standardGems = [
  GemType.red,
  GemType.blue,
  GemType.green,
  GemType.yellow,
  GemType.purple,
  GemType.orange,
];

class BotMovePreview extends StatefulWidget {
  const BotMovePreview({super.key, required this.eventBus});

  final EventBus eventBus;

  @override
  State<BotMovePreview> createState() => _BotMovePreviewState();
}

class _BotMovePreviewState extends State<BotMovePreview>
    with SingleTickerProviderStateMixin {
  final _random = Random();

  late final AnimationController _anim;
  StreamSubscription<BotScoreUpdatedEvent>? _sub;

  /// Current grid (2×8 gem types).
  List<List<GemType>> _grid = [];

  /// Which cells are the 3-match (row, col).
  List<(int, int)> _matchCells = [];

  /// Swap source and target (row, col).
  (int, int) _swapFrom = (0, 0);
  (int, int) _swapTo = (0, 0);

  /// Whether an animation is currently playing.
  bool _playing = false;

  /// Queued event waiting to play after current finishes.
  bool _queued = false;

  @override
  void initState() {
    super.initState();
    _anim = AnimationController(vsync: this, duration: _kAnimDuration)
      ..addStatusListener(_onAnimStatus);

    _sub = widget.eventBus.on<BotScoreUpdatedEvent>().listen((_) {
      if (_playing) {
        _queued = true; // Play after current finishes.
        return;
      }
      _startPreview();
    });
  }

  @override
  void dispose() {
    _sub?.cancel();
    _anim.dispose();
    super.dispose();
  }

  void _onAnimStatus(AnimationStatus status) {
    if (status == AnimationStatus.completed) {
      setState(() => _playing = false);
      if (_queued) {
        _queued = false;
        // Small gap before next preview.
        Future.delayed(kBotPreviewGapDuration, () {
          if (mounted) _startPreview();
        });
      }
    }
  }

  void _startPreview() {
    _generateGrid();
    setState(() => _playing = true);
    _anim.forward(from: 0.0);
  }

  /// Generate random 2×8 grid with a pre-arranged horizontal 3-match.
  void _generateGrid() {
    // Fill with random gems.
    _grid = List.generate(
      _kRows,
      (_) => List.generate(_kCols, (_) => _randomGem()),
    );

    // Pick match position: 3 consecutive cells in row 0.
    final matchStart = _random.nextInt(_kCols - 2); // 0..5
    final matchColor = _randomGem();

    // Set the 3-match in row 0.
    _grid[0][matchStart] = matchColor;
    _grid[0][matchStart + 1] = matchColor;
    // The third cell will be filled by the swap — put a different color there.
    GemType swapAwayColor;
    do {
      swapAwayColor = _randomGem();
    } while (swapAwayColor == matchColor);
    _grid[0][matchStart + 2] = swapAwayColor;

    // The swap gem is in row 1 directly below the third match cell.
    _grid[1][matchStart + 2] = matchColor;

    // Ensure no accidental matches elsewhere in row 0.
    for (var c = 0; c < _kCols - 2; c++) {
      if (c == matchStart) continue; // Skip our intentional match zone.
      if (_grid[0][c] == _grid[0][c + 1] &&
          _grid[0][c + 1] == _grid[0][c + 2]) {
        do {
          _grid[0][c + 2] = _randomGem();
        } while (_grid[0][c + 2] == _grid[0][c + 1]);
      }
    }

    _matchCells = [(0, matchStart), (0, matchStart + 1), (0, matchStart + 2)];
    _swapFrom = (1, matchStart + 2); // Row 1 gem swaps up.
    _swapTo = (0, matchStart + 2); // Into row 0 to complete match.
  }

  GemType _randomGem() => _standardGems[_random.nextInt(_standardGems.length)];

  @override
  Widget build(BuildContext context) {
    if (!_playing) return const SizedBox.shrink();

    return AnimatedBuilder(
      animation: _anim,
      builder: (context, _) {
        final t = _anim.value; // 0.0 → 1.0 over 1500ms.

        // Fade envelope.
        double opacity;
        if (t < 0.133) {
          // 0-200ms: fade in.
          opacity = (t / 0.133).clamp(0.0, 1.0);
        } else if (t > 0.733) {
          // 1100-1500ms: fade out.
          opacity = ((1.0 - t) / 0.267).clamp(0.0, 1.0);
        } else {
          opacity = 1.0;
        }

        return Opacity(
          opacity: opacity,
          child: Container(
            width: _kPreviewWidth,
            padding: const EdgeInsets.fromLTRB(10, 18, 10, 8),
            decoration: BoxDecoration(
              color: ChromaColors.bgSurface.withValues(alpha: 0.8),
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: ChromaColors.glassBorder),
              boxShadow: [
                BoxShadow(
                  color: const Color(0xFFFF6D00).withValues(alpha: 0.15),
                  blurRadius: 12,
                ),
              ],
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                // "BOT" label.
                Align(
                  alignment: Alignment.topLeft,
                  child: Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Text(
                      'Opponent',
                      style: ChromaText.labelSmall.copyWith(
                        color: const Color(0xFFFF9500).withValues(alpha: 0.6),
                        fontWeight: FontWeight.w900,
                      ),
                    ),
                  ),
                ),
                // Mini board.
                SizedBox(
                  width: _kGridWidth,
                  height: _kGridHeight,
                  child: CustomPaint(
                    painter: _BotPreviewPainter(
                      grid: _grid,
                      matchCells: _matchCells,
                      swapFrom: _swapFrom,
                      swapTo: _swapTo,
                      progress: t,
                      theme: context.read<VisualThemeBase>(),
                    ),
                  ),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}

/// Paints the 2×8 mini gem grid with animated swap, flash, and pop.
class _BotPreviewPainter extends CustomPainter {
  _BotPreviewPainter({
    required this.grid,
    required this.matchCells,
    required this.swapFrom,
    required this.swapTo,
    required this.progress,
    required this.theme,
  });

  final List<List<GemType>> grid;
  final List<(int, int)> matchCells;
  final (int, int) swapFrom;
  final (int, int) swapTo;
  final double progress; // 0.0 → 1.0 over 1500ms.
  final VisualThemeBase theme;

  // Timeline thresholds (as fraction of 1500ms).
  static const double _swapStart = 0.133; // 200ms
  static const double _swapEnd = 0.300; // 450ms
  static const double _flashEnd = 0.333; // 500ms
  static const double _popEnd = 0.533; // 800ms

  @override
  void paint(Canvas canvas, Size size) {
    // Compute swap animation progress (0→1 during swap phase).
    final swapT = progress < _swapStart
        ? 0.0
        : progress > _swapEnd
        ? 1.0
        : (progress - _swapStart) / (_swapEnd - _swapStart);

    // Smooth ease-out for swap.
    final easedSwapT = Curves.easeOutCubic.transform(swapT.clamp(0.0, 1.0));

    // Pop progress (0→1 during pop phase).
    final popT = progress < _flashEnd
        ? 0.0
        : progress > _popEnd
        ? 1.0
        : (progress - _flashEnd) / (_popEnd - _flashEnd);

    // Is flashing?
    final flashing = progress >= _swapEnd && progress < _flashEnd;

    for (var row = 0; row < _kRows; row++) {
      for (var col = 0; col < _kCols; col++) {
        final gem = grid[row][col];
        if (gem == GemType.empty) continue;

        var cx = col * _kCellStride + _kCellSize / 2;
        var cy = row * _kCellStride + _kCellSize / 2;
        var scale = 1.0;

        final isSwapFrom = row == swapFrom.$1 && col == swapFrom.$2;
        final isSwapTo = row == swapTo.$1 && col == swapTo.$2;
        final isMatch = matchCells.any((c) => c.$1 == row && c.$2 == col);

        // Animate swap positions.
        if (isSwapFrom) {
          final targetCx = swapTo.$2 * _kCellStride + _kCellSize / 2;
          final targetCy = swapTo.$1 * _kCellStride + _kCellSize / 2;
          cx = ui.lerpDouble(cx, targetCx, easedSwapT)!;
          cy = ui.lerpDouble(cy, targetCy, easedSwapT)!;
        } else if (isSwapTo) {
          final targetCx = swapFrom.$2 * _kCellStride + _kCellSize / 2;
          final targetCy = swapFrom.$1 * _kCellStride + _kCellSize / 2;
          cx = ui.lerpDouble(cx, targetCx, easedSwapT)!;
          cy = ui.lerpDouble(cy, targetCy, easedSwapT)!;
        }

        // After swap completes, the match cells should pop.
        // The swapFrom gem is now at swapTo position — it's part of the match.
        final isMatchAfterSwap = isMatch || isSwapFrom;
        if (isMatchAfterSwap && popT > 0) {
          scale = (1.0 - popT).clamp(0.0, 1.0);
          if (scale <= 0.01) continue; // Fully popped — skip.
        }

        final color = theme.gemColor(gem.value);
        final r = (_kCellSize * 0.4) * scale;

        // Glow.
        final glowPaint = Paint()
          ..color = (flashing && isMatchAfterSwap)
              ? Colors.white.withValues(alpha: 0.5)
              : color.withValues(alpha: 0.25)
          ..maskFilter = const MaskFilter.blur(BlurStyle.normal, 3);
        _drawGem(canvas, cx, cy, r + 2, glowPaint, gem);

        // Fill.
        final fillPaint = Paint()
          ..color = (flashing && isMatchAfterSwap) ? Colors.white : color;
        _drawGem(canvas, cx, cy, r, fillPaint, gem);
      }
    }

    // Sparkle particles during pop phase.
    if (popT > 0 && popT < 1.0) {
      _drawSparkles(canvas, popT);
    }
  }

  /// Draw faceted gemstone shape matching the shader polygon SDFs.
  void _drawGem(
    Canvas canvas,
    double cx,
    double cy,
    double r,
    Paint paint,
    GemType gem,
  ) {
    if (r <= 0) return;
    final shape = theme.gemShape(gem.value);
    switch (shape) {
      case 0: // Round Brilliant — 10-facet
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
      case 1: // Marquise Diamond — 8-facet kite
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
      case 3: // Cushion Cut — 12-facet
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
      case 4: // Heart Cut — 14-facet
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

  /// Draw expanding sparkle particles for popping match cells.
  void _drawSparkles(Canvas canvas, double popT) {
    final sparkPaint = Paint();
    final rng = Random(42); // Fixed seed for deterministic sparkles.

    for (final cell in matchCells) {
      final baseCx = cell.$2 * _kCellStride + _kCellSize / 2;
      final baseCy = cell.$1 * _kCellStride + _kCellSize / 2;
      final color = theme.gemColor(grid[cell.$1][cell.$2].value);

      for (var i = 0; i < 5; i++) {
        final angle = rng.nextDouble() * 2 * pi;
        final dist = 4 + popT * (12 + rng.nextDouble() * 8);
        final px = baseCx + cos(angle) * dist;
        final py = baseCy + sin(angle) * dist;
        final sparkR = (1.5 + rng.nextDouble()) * (1.0 - popT);

        sparkPaint.color = Color.lerp(
          color,
          Colors.white,
          0.5,
        )!.withValues(alpha: (1.0 - popT) * 0.8);
        canvas.drawCircle(Offset(px, py), sparkR, sparkPaint);
      }
    }

    // Also sparkle for the swapFrom cell (now at swapTo position).
    final sfCx = swapTo.$2 * _kCellStride + _kCellSize / 2;
    final sfCy = swapTo.$1 * _kCellStride + _kCellSize / 2;
    final sfColor = theme.gemColor(grid[swapFrom.$1][swapFrom.$2].value);

    for (var i = 0; i < 5; i++) {
      final angle = rng.nextDouble() * 2 * pi;
      final dist = 4 + popT * (12 + rng.nextDouble() * 8);
      final px = sfCx + cos(angle) * dist;
      final py = sfCy + sin(angle) * dist;
      final sparkR = (1.5 + rng.nextDouble()) * (1.0 - popT);

      sparkPaint.color = Color.lerp(
        sfColor,
        Colors.white,
        0.5,
      )!.withValues(alpha: (1.0 - popT) * 0.8);
      canvas.drawCircle(Offset(px, py), sparkR, sparkPaint);
    }
  }

  @override
  bool shouldRepaint(_BotPreviewPainter old) => old.progress != progress;
}
