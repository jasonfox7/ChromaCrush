/// Help overlay for the Card Vault screen.
///
/// Dims the screen with a semi-transparent scrim and shows directional
/// arrow hints for the card gestures (swipe left/right, up, down).
///
/// Tap anywhere to dismiss.
library;

import 'package:flutter/material.dart';

import '../../theme/chroma_theme.dart';
import '../../theme/glass_panel.dart';

class VaultHelpOverlay extends StatelessWidget {
  const VaultHelpOverlay({super.key, required this.onDismiss});

  final VoidCallback onDismiss;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onTap: onDismiss,
      child: Container(
        color: Colors.black.withValues(alpha: 0.75),
        child: Center(
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 32),
            child: GlassPanel(
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  // Title.
                  Text(
                    'Card Vault Controls',
                    style: ChromaText.titleMedium.copyWith(
                      color: ChromaColors.accentGlow,
                    ),
                  ),
                  const SizedBox(height: 20),

                  // Swipe left/right.
                  _HintRow(
                    icon: Icons.swap_horiz,
                    text: 'Swipe left / right to browse cards',
                  ),
                  const SizedBox(height: 16),

                  // Swipe up.
                  _HintRow(
                    icon: Icons.arrow_upward,
                    text: 'Swipe up to equip card',
                  ),
                  const SizedBox(height: 16),

                  // Swipe down.
                  _HintRow(
                    icon: Icons.arrow_downward,
                    text: 'Swipe down for full card preview',
                  ),
                  const SizedBox(height: 16),

                  // Unequip hint.
                  _HintRow(
                    icon: Icons.arrow_downward,
                    text: 'Drag equipped card down to unequip',
                  ),

                  const SizedBox(height: 20),

                  // Dismiss hint.
                  Text(
                    'Tap anywhere to dismiss',
                    style: ChromaText.labelSmall.copyWith(
                      color: ChromaColors.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _HintRow extends StatelessWidget {
  const _HintRow({required this.icon, required this.text});

  final IconData icon;
  final String text;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 36,
          height: 36,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: ChromaColors.accent.withValues(alpha: 0.2),
            border: Border.all(
              color: ChromaColors.accentGlow.withValues(alpha: 0.4),
            ),
          ),
          child: Icon(icon, color: ChromaColors.accentGlow, size: 20),
        ),
        const SizedBox(width: 14),
        Expanded(
          child: Text(
            text,
            style: ChromaText.bodyMedium.copyWith(
              color: ChromaColors.textPrimary,
            ),
          ),
        ),
      ],
    );
  }
}
