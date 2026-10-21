/// Glassmorphism panel — frosted glass container with blur and translucent fill.
///
/// Wraps child in ClipRRect → BackdropFilter → translucent Container.
/// Used across all screens for consistent elevated surface styling.
library;

import 'dart:ui';

import 'package:flutter/material.dart';

import '../config/game_config.dart';
import 'chroma_theme.dart';

class GlassPanel extends StatelessWidget {
  const GlassPanel({
    super.key,
    required this.child,
    this.borderRadius = kGlassBorderRadius,
    this.padding = const EdgeInsets.all(kGlassPadding),
    this.blurSigma = kGlassBlurSigma,
  });

  final Widget child;
  final double borderRadius;
  final EdgeInsetsGeometry padding;
  final double blurSigma;

  @override
  Widget build(BuildContext context) {
    return ClipRRect(
      borderRadius: BorderRadius.circular(borderRadius),
      child: BackdropFilter(
        filter: ImageFilter.blur(sigmaX: blurSigma, sigmaY: blurSigma),
        child: Container(
          padding: padding,
          decoration: BoxDecoration(
            color: ChromaColors.glassWhite,
            borderRadius: BorderRadius.circular(borderRadius),
            border: Border.all(color: ChromaColors.glassBorder),
          ),
          child: child,
        ),
      ),
    );
  }
}
