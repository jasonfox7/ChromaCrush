/// Coach overlay for the tutorial screen.
///
/// Dims the board with a semi-transparent scrim, cuts circular spotlights
/// around the from/to gem positions, animates a hand icon sliding between
/// them, and shows the coach text in a glass panel below the board.
///
/// Tap anywhere to dismiss.
library;

import 'dart:math' show pi;

import 'package:flutter/material.dart';

import '../../extensions/grid_math.dart';
import '../../theme/chroma_theme.dart';
import '../../theme/glass_panel.dart';

class CoachOverlay extends StatefulWidget {
  const CoachOverlay({
    super.key,
    required this.fromRow,
    required this.fromCol,
    required this.toRow,
    required this.toCol,
    required this.coachText,
    required this.layout,
    required this.onDismiss,
    required this.stepNumber,
    required this.totalSteps,
  });

  final int fromRow;
  final int fromCol;
  final int toRow;
  final int toCol;
  final String coachText;
  final BoardLayout layout;
  final VoidCallback onDismiss;
  final int stepNumber;
  final int totalSteps;

  @override
  State<CoachOverlay> createState() => _CoachOverlayState();
}

class _CoachOverlayState extends State<CoachOverlay>
    with SingleTickerProviderStateMixin {
  late final AnimationController _handController;

  @override
  void initState() {
    super.initState();
    _handController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1500),
    )..repeat();
  }

  @override
  void dispose() {
    _handController.dispose();
    super.dispose();
  }

  /// Convert grid (row, col) to screen-space center of that cell.
  Offset _gridToScreen(int row, int col) {
    final x = widget.layout.boardLeft +
        col * widget.layout.cellStride +
        widget.layout.cellSize / 2;
    final y = widget.layout.boardTop +
        row * widget.layout.cellStride +
        widget.layout.cellSize / 2;
    return Offset(x, y);
  }

  @override
  Widget build(BuildContext context) {
    final fromCenter = _gridToScreen(widget.fromRow, widget.fromCol);
    final toCenter = _gridToScreen(widget.toRow, widget.toCol);
    final spotlightRadius = widget.layout.cellSize * 0.55;
    final screen = MediaQuery.sizeOf(context);

    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: widget.onDismiss,
      child: Stack(
        children: [
          // Dim scrim with spotlight cutouts.
          CustomPaint(
            size: screen,
            painter: _SpotlightPainter(
              fromCenter: fromCenter,
              toCenter: toCenter,
              radius: spotlightRadius,
            ),
          ),

          // Animated hand icon sliding from → to.
          AnimatedBuilder(
            animation: _handController,
            builder: (context, child) {
              final t = Curves.easeInOut.transform(_handController.value);
              final pos = Offset.lerp(fromCenter, toCenter, t)!;
              // Compute rotation angle from direction.
              final dx = toCenter.dx - fromCenter.dx;
              final dy = toCenter.dy - fromCenter.dy;
              final angle = dx.abs() > dy.abs()
                  ? (dx > 0 ? 0.0 : pi)
                  : (dy > 0 ? pi / 2 : -pi / 2);
              return Positioned(
                left: pos.dx - 16,
                top: pos.dy - 16,
                child: Transform.rotate(
                  angle: angle,
                  child: const Icon(
                    Icons.touch_app,
                    color: Colors.white,
                    size: 32,
                    shadows: [
                      Shadow(
                        color: Colors.black54,
                        blurRadius: 8,
                      ),
                    ],
                  ),
                ),
              );
            },
          ),

          // Coach text panel at the bottom.
          Positioned(
            left: 24,
            right: 24,
            bottom: MediaQuery.paddingOf(context).bottom + 40,
            child: GlassPanel(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    widget.coachText,
                    style: ChromaText.titleMedium.copyWith(
                      color: ChromaColors.textPrimary,
                    ),
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'Tap to continue',
                    style: ChromaText.labelSmall.copyWith(
                      color: ChromaColors.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// Paints a dark scrim with two circular cutouts (even-odd fill).
class _SpotlightPainter extends CustomPainter {
  const _SpotlightPainter({
    required this.fromCenter,
    required this.toCenter,
    required this.radius,
  });

  final Offset fromCenter;
  final Offset toCenter;
  final double radius;

  @override
  void paint(Canvas canvas, Size size) {
    final path = Path()
      ..fillType = PathFillType.evenOdd
      ..addRect(Rect.fromLTWH(0, 0, size.width, size.height))
      ..addOval(Rect.fromCircle(center: fromCenter, radius: radius))
      ..addOval(Rect.fromCircle(center: toCenter, radius: radius));

    canvas.drawPath(
      path,
      Paint()..color = Colors.black.withValues(alpha: 0.65),
    );
  }

  @override
  bool shouldRepaint(_SpotlightPainter oldDelegate) {
    return fromCenter != oldDelegate.fromCenter ||
        toCenter != oldDelegate.toCenter ||
        radius != oldDelegate.radius;
  }
}
