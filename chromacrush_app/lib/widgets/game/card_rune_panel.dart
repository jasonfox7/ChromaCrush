/// Card rune panel — displays equipped card glyphs with proc glow effects.
///
/// Self-contained widget that subscribes to EquippedCardsEvent and
/// CardProcEvent via EventBus. Used by both GameHUD and CampaignHUD.
/// Returns SizedBox.shrink() when no cards are equipped.
library;

import 'dart:async';

import 'package:flutter/material.dart';

import '../../services/event_bus.dart';
import '../../theme/glass_panel.dart';

const _rarityColors = <String, Color>{
  'common': Color(0xFF8E8E93),
  'rare': Color(0xFF4FC3F7),
  'epic': Color(0xFFAB47BC),
  'legendary': Color(0xFFFFB300),
};

class CardRunePanel extends StatefulWidget {
  const CardRunePanel({super.key, required this.eventBus});

  final EventBus eventBus;

  @override
  State<CardRunePanel> createState() => _CardRunePanelState();
}

class _CardRunePanelState extends State<CardRunePanel> {
  List<EquippedCardInfo> _cards = [];
  final Map<int, Timer> _procTimers = {};
  final Set<int> _glowingCardIds = {};
  StreamSubscription<EquippedCardsEvent>? _cardsSub;
  StreamSubscription<CardProcEvent>? _procSub;

  @override
  void initState() {
    super.initState();
    _cardsSub = widget.eventBus.on<EquippedCardsEvent>().listen((e) {
      setState(() => _cards = e.cards);
    });
    _procSub = widget.eventBus.on<CardProcEvent>().listen((e) {
      setState(() => _glowingCardIds.addAll(e.cardIds));
      for (final id in e.cardIds) {
        _procTimers[id]?.cancel();
        _procTimers[id] = Timer(const Duration(milliseconds: 800), () {
          if (mounted) setState(() => _glowingCardIds.remove(id));
        });
      }
    });
  }

  @override
  void dispose() {
    _cardsSub?.cancel();
    _procSub?.cancel();
    for (final t in _procTimers.values) {
      t.cancel();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_cards.isEmpty) return const SizedBox.shrink();

    return GlassPanel(
      borderRadius: 12,
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          for (var i = 0; i < _cards.length; i++) ...[
            if (i > 0) const SizedBox(width: 4),
            _buildRuneGlyph(_cards[i]),
          ],
        ],
      ),
    );
  }

  Widget _buildRuneGlyph(EquippedCardInfo card) {
    final color = _rarityColors[card.rarity] ?? _rarityColors['common']!;
    final glowing = _glowingCardIds.contains(card.cardId);
    final glyph = String.fromCharCode(0x12F90 + card.cardId);

    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      decoration: glowing
          ? BoxDecoration(
              shape: BoxShape.circle,
              boxShadow: [
                BoxShadow(
                  color: color.withValues(alpha: 0.9),
                  blurRadius: 24,
                  spreadRadius: 6,
                ),
                BoxShadow(
                  color: color.withValues(alpha: 0.5),
                  blurRadius: 48,
                  spreadRadius: 12,
                ),
              ],
            )
          : null,
      child: Text(
        glyph,
        style: TextStyle(
          fontFamily: 'CyproMinoan',
          fontSize: 22,
          color: glowing ? Colors.white : color,
          shadows: [
            Shadow(color: color.withValues(alpha: 0.3), blurRadius: 6),
            if (glowing) Shadow(color: color, blurRadius: 16),
          ],
        ),
      ),
    );
  }
}
