/// Player status bar — hearts + mega gem inventory.
///
/// Positioned above the game board. Displays energy hearts on the left
/// and 5 tappable mega gem slots on the right (4 megas + 1 shuffle).
/// Count badges show remaining quantity.
///
/// Card runes are displayed separately in the GameHUD glass panel.
///
/// All sizes are proportional to [cellSize] — zero hardcoded pixel values.
library;

import 'dart:ui';

import 'package:flame/components.dart';

import '../config/visual_config.dart';
import '../config/visual_theme_service.dart';
import '../models/gem_type.dart';
import 'gem_component.dart';

/// Slot configuration for each mega gem in the bar.
class _MegaSlot {
  const _MegaSlot({
    required this.displayRawFunc,
    required this.actualMega,
    required this.color,
    required this.symbol,
  });

  /// Raw func value for the shader (visual only — shows the dominant effect).
  final int displayRawFunc;

  /// Actual mega gem value for server activation (Phase 4).
  final int actualMega;

  /// Base gem color for the slot.
  final GemType color;

  /// Symbol indicating the mega gem's effect.
  final String symbol;
}

const _megaSlots = [
  _MegaSlot(
    displayRawFunc: 11,
    actualMega: 11,
    color: GemType.purple,
    symbol: '\u2194\u2194',
  ), // ↔↔ H+H blast
  _MegaSlot(
    displayRawFunc: 22,
    actualMega: 22,
    color: GemType.blue,
    symbol: '\u2195\u2195',
  ), // ↕↕ V+V blast
  _MegaSlot(
    displayRawFunc: 33,
    actualMega: 33,
    color: GemType.orange,
    symbol: '\u2738\u2738',
  ), // ✸✸ bomb+bomb
  _MegaSlot(
    displayRawFunc: 44,
    actualMega: 44,
    color: GemType.yellow,
    symbol: '\u221E',
  ), // ∞ chroma chroma
  _MegaSlot(
    displayRawFunc: 0,
    actualMega: -1,
    color: GemType.green,
    symbol: '\u27F3',
  ), // ⟳ shuffle
];

class PlayerStatusBar extends PositionComponent {
  PlayerStatusBar({
    required Vector2 barPosition,
    required double barWidth,
    required this.theme,
    required this.cellSize,
  }) : super(
         position: barPosition,
         size: Vector2(barWidth, cellSize * kStatusBarHeightRatio),
         priority: 5,
       );

  final VisualThemeBase theme;
  final double cellSize;

  // -- Proportional sizes derived from cellSize --
  late final double _gs = cellSize * kStatusGemRatio;
  late final double _pad = cellSize * 0.16;
  late final double _fontSize = cellSize * 0.35;
  late final double _spacing = cellSize * 0.05;
  late final double _badgeW = cellSize * 1.2;
  late final double _cornerRadius = cellSize * 0.32;

  int _currentHearts = 0;
  final List<int> _megaCounts = [0, 0, 0, 0, 0];
  final List<GemComponent> _megaGems = [];

  /// Callback fired when a mega gem slot is tapped (slot 0-4).
  void Function(int slotIndex)? onMegaTapped;

  // Pre-built paragraph objects for count badges (rebuilt when counts change).
  final List<Paragraph?> _countParagraphs = [null, null, null, null, null];

  // Heart count paragraph (rebuilt when hearts change).
  Paragraph? _heartCountParagraph;
  int _lastRenderedHearts = -1;

  /// Update heart display.
  void setHearts(int current, int max) {
    _currentHearts = current.clamp(0, max);
    _heartCountParagraph = null; // rebuild on next render
  }

  /// Update mega gem count for a slot (0-4).
  void setMegaCount(int slotIndex, int count) {
    if (slotIndex < 0 || slotIndex >= _megaCounts.length) return;
    _megaCounts[slotIndex] = count;
    _countParagraphs[slotIndex] = null; // rebuild on next render
    // Dim gem when count is 0, brighten when > 0.
    if (slotIndex < _megaGems.length) {
      _megaGems[slotIndex].paintAlpha = count > 0 ? 1.0 : 0.35;
    }
  }

  /// X position of the i-th mega gem slot within the bar.
  double _gemX(int index) {
    final rightEdge = size.x - _pad - _gs;
    return rightEdge - (_megaSlots.length - 1 - index) * (_gs + _spacing);
  }

  @override
  Future<void> onLoad() async {
    // Heart gem (red, neutral) — left-aligned.
    final heartGem = GemComponent(
      gemType: GemType.red,
      gridRow: 0,
      gridCol: 0,
      theme: theme,
      cellSize: _gs,
      initialPosition: Vector2(_pad, _pad),
      gemFunction: GemFunction.neutral,
      rawFunc: 0,
    );
    add(heartGem);

    // Mega gem slots — right-aligned.
    for (var i = 0; i < _megaSlots.length; i++) {
      final slot = _megaSlots[i];
      final slotIndex = i;
      final gem = GemComponent(
        gemType: slot.color,
        gridRow: 0,
        gridCol: i,
        theme: theme,
        cellSize: _gs,
        initialPosition: Vector2(_gemX(i), _pad),
        gemFunction: GemFunction.fromValue(slot.displayRawFunc),
        rawFunc: slot.displayRawFunc,
        onTap: (_, _) => onMegaTapped?.call(slotIndex),
      );
      _megaGems.add(gem);
      add(gem);
    }
  }

  @override
  void render(Canvas canvas) {
    _drawBackground(canvas);
    _drawHearts(canvas);
    _drawCountBadges(canvas);
  }

  // ---------------------------------------------------------------------------
  // Background
  // ---------------------------------------------------------------------------

  void _drawBackground(Canvas canvas) {
    final rect = Rect.fromLTWH(0, 0, size.x, size.y);
    final rrect = RRect.fromRectAndRadius(rect, Radius.circular(_cornerRadius));

    // Fill.
    canvas.drawRRect(rrect, Paint()..color = kStatusBarBgColor);

    // Border.
    canvas.drawRRect(
      rrect,
      Paint()
        ..color = const Color(0x1FFFFFFF)
        ..style = PaintingStyle.stroke
        ..strokeWidth = 1.0,
    );
  }

  // ---------------------------------------------------------------------------
  // Hearts
  // ---------------------------------------------------------------------------

  void _drawHearts(Canvas canvas) {
    if (_currentHearts != _lastRenderedHearts) {
      _heartCountParagraph = _buildHeartCountParagraph();
      _lastRenderedHearts = _currentHearts;
    }
    final badgeY = _pad + _gs + _gs * 0.05;
    canvas.drawParagraph(_heartCountParagraph!, Offset(_pad, badgeY));
  }

  Paragraph _buildHeartCountParagraph() {
    final color = _currentHearts > 0 ? kCountAvailableColor : kCountZeroColor;
    final builder =
        ParagraphBuilder(
            ParagraphStyle(textAlign: TextAlign.center, maxLines: 1),
          )
          ..pushStyle(
            TextStyle(
              color: color,
              fontSize: _fontSize,
              fontWeight: FontWeight.w700,
            ),
          )
          ..addText('\u00D7$_currentHearts'); // ×N
    return builder.build()..layout(ParagraphConstraints(width: _gs));
  }

  // ---------------------------------------------------------------------------
  // Count badges
  // ---------------------------------------------------------------------------

  void _drawCountBadges(Canvas canvas) {
    for (var i = 0; i < _megaSlots.length; i++) {
      final count = _megaCounts[i];
      final gemCenterX = _gemX(i) + _gs / 2;
      final badgeY = _pad + _gs + _gs * 0.05;

      // Build paragraph lazily.
      _countParagraphs[i] ??= _buildCountParagraph(i, count);
      final paragraph = _countParagraphs[i]!;

      canvas.drawParagraph(
        paragraph,
        Offset(gemCenterX - _badgeW / 2 + _gs * 0.2, badgeY),
      );
    }
  }

  Paragraph _buildCountParagraph(int slotIndex, int count) {
    final color = count > 0 ? kCountAvailableColor : kCountZeroColor;
    final builder =
        ParagraphBuilder(
            ParagraphStyle(textAlign: TextAlign.center, maxLines: 1),
          )
          ..pushStyle(
            TextStyle(
              color: color,
              fontSize: _fontSize,
              fontWeight: FontWeight.w700,
            ),
          )
          ..addText('\u00D7$count'); // ×N
    return builder.build()..layout(ParagraphConstraints(width: _badgeW));
  }
}
