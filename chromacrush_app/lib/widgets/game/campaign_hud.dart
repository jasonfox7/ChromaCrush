/// Campaign HUD — score, obstacles remaining, moves remaining, equipped cards.
///
/// Flutter widget overlaid on top of the Flame GameWidget via Stack.
/// Replaces opponent bar + chain counter with obstacle counter.
/// Card rune panel delegated to shared CardRunePanel widget.
library;

import 'dart:async';

import 'package:flutter/material.dart';

import '../../services/event_bus.dart';
import '../../theme/chroma_theme.dart';
import '../../theme/glass_panel.dart';
import '../../view_models/campaign_view_model.dart';
import 'card_rune_panel.dart';

class CampaignHUD extends StatefulWidget {
  const CampaignHUD({
    super.key,
    required this.viewModel,
    required this.eventBus,
  });

  final CampaignViewModel viewModel;
  final EventBus eventBus;

  @override
  State<CampaignHUD> createState() => _CampaignHUDState();
}

class _CampaignHUDState extends State<CampaignHUD> {
  StreamSubscription<ScoreUpdatedEvent>? _scoreSub;
  StreamSubscription<MovesUpdatedEvent>? _movesSub;
  StreamSubscription<ObstaclesUpdatedEvent>? _obsSub;

  EventBus get eventBus => widget.eventBus;
  CampaignViewModel get viewModel => widget.viewModel;

  @override
  void initState() {
    super.initState();
    _scoreSub = eventBus.on<ScoreUpdatedEvent>().listen((_) {
      if (mounted) setState(() {});
    });
    _movesSub = eventBus.on<MovesUpdatedEvent>().listen((_) {
      if (mounted) setState(() {});
    });
    _obsSub = eventBus.on<ObstaclesUpdatedEvent>().listen((_) {
      if (mounted) setState(() {});
    });
  }

  @override
  void dispose() {
    _scoreSub?.cancel();
    _movesSub?.cancel();
    _obsSub?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: Column(
          children: [
            // Top section: card panel (left) + level label (centered).
            Stack(
              alignment: Alignment.center,
              children: [
                GlassPanel(
                  borderRadius: 12,
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 8,
                  ),
                  child: Text(
                    'LEVEL ${viewModel.currentLevel}',
                    style: ChromaText.bodyMedium.copyWith(
                      fontWeight: FontWeight.w600,
                      letterSpacing: 2,
                    ),
                  ),
                ),
                Align(
                  alignment: Alignment.centerLeft,
                  child: CardRunePanel(eventBus: eventBus),
                ),
              ],
            ),
            const Spacer(),
            // Bottom bar: score, obstacles, moves.
            _buildScoreBar(),
          ],
        ),
      ),
    );
  }

  Widget _buildScoreBar() {
    final moves = viewModel.movesRemaining;
    final movesColor = moves <= 3
        ? Colors.red
        : moves <= 7
            ? Colors.orange
            : ChromaColors.textPrimary;

    final obs = viewModel.obstaclesRemaining;
    final obsColor = obs <= 2 ? Colors.orange : ChromaColors.textPrimary;

    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        // Score.
        GlassPanel(
          borderRadius: 12,
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('SCORE', style: ChromaText.labelSmall),
              Text(
                '${viewModel.myScore}',
                style: const TextStyle(
                  color: ChromaColors.textPrimary,
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ),
        // Obstacles remaining.
        GlassPanel(
          borderRadius: 12,
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('OBSTACLES', style: ChromaText.labelSmall),
              Text(
                '$obs',
                style: TextStyle(
                  color: obsColor,
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ),
        // Moves remaining.
        GlassPanel(
          borderRadius: 12,
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.end,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text('MOVES', style: ChromaText.labelSmall),
              Text(
                '$moves',
                style: TextStyle(
                  color: movesColor,
                  fontSize: 28,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
