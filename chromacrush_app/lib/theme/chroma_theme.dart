/// Design tokens — centralized colors, typography, and gradients.
///
/// Every screen uses these constants for a cohesive dark spacey casino aesthetic.
/// Layered depth hierarchy: bgDeep → bgBase → bgSurface → bgElevated.
library;

import 'package:flutter/material.dart';

/// Color palette — dark spacey casino with neon purple accents.
abstract final class ChromaColors {
  // Background depth layers (darkest → lightest).
  static const Color bgDeep = Color(0xFF080810);
  static const Color bgBase = Color(0xFF0D0D14);
  static const Color bgSurface = Color(0xFF14142A);
  static const Color bgElevated = Color(0xFF1C1C3A);

  // Accent.
  static const Color accent = Color(0xFF7C4DFF);
  static const Color accentGlow = Color(0xFF9C7CFF);

  // Glass.
  static final Color glassWhite = Colors.white.withValues(alpha: 0.06);
  static final Color glassBorder = Colors.white.withValues(alpha: 0.12);

  // Text hierarchy.
  static const Color textPrimary = Colors.white;
  static const Color textSecondary = Colors.white70;
  static const Color textTertiary = Colors.white38;
  static const Color textAccent = accentGlow;
}

/// Typography — consistent text styles across all screens.
abstract final class ChromaText {
  static const TextStyle displayLarge = TextStyle(
    color: ChromaColors.textPrimary,
    fontSize: 36,
    fontWeight: FontWeight.w900,
    letterSpacing: 6,
  );

  static const TextStyle headlineMedium = TextStyle(
    color: ChromaColors.textPrimary,
    fontSize: 24,
    fontWeight: FontWeight.w700,
  );

  static const TextStyle titleMedium = TextStyle(
    color: ChromaColors.textPrimary,
    fontSize: 18,
    fontWeight: FontWeight.w600,
  );

  static const TextStyle bodyMedium = TextStyle(
    color: ChromaColors.textSecondary,
    fontSize: 14,
  );

  static const TextStyle labelSmall = TextStyle(
    color: ChromaColors.textTertiary,
    fontSize: 10,
    letterSpacing: 1.5,
  );
}

/// Reusable gradients.
abstract final class ChromaGradients {
  /// Vertical screen background — bgDeep at top, bgBase at bottom.
  static const LinearGradient screen = LinearGradient(
    begin: Alignment.topCenter,
    end: Alignment.bottomCenter,
    colors: [ChromaColors.bgDeep, ChromaColors.bgBase],
  );

  /// Horizontal accent gradient for buttons and title masks.
  static const LinearGradient accent = LinearGradient(
    colors: [ChromaColors.accent, ChromaColors.accentGlow],
  );
}
