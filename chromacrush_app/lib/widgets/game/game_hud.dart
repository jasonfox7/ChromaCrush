/// HUD overlay — score, moves remaining, opponent info, equipped cards.
///
/// Flutter widget overlaid on top of the Flame GameWidget via Stack.
/// Listens to EventBus via StreamBuilder for real-time updates.
/// Glass panels for all HUD elements.
library;

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

import '../../services/event_bus.dart';
import '../../theme/chroma_theme.dart';
import '../../theme/glass_panel.dart';
import '../../view_models/match_view_model.dart';
import 'card_rune_panel.dart';

class GameHUD extends StatelessWidget {
  const GameHUD({super.key, required this.viewModel, required this.eventBus});

  final MatchViewModel viewModel;
  final EventBus eventBus;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        child: Column(
          children: [
            // Top section: card panel (left) + opponent info (centered).
            Stack(
              alignment: Alignment.center,
              children: [
                // Opponent bar — centered.
                _buildOpponentBar(),
                // Card panel — left-aligned.
                Align(
                  alignment: Alignment.centerLeft,
                  child: CardRunePanel(eventBus: eventBus),
                ),
              ],
            ),
            const Spacer(),
            // Bottom bar: score and moves.
            _buildScoreBar(),
          ],
        ),
      ),
    );
  }

  Widget _buildOpponentBar() {
    final name = viewModel.opponentName ?? 'Opponent';
    final isBot = viewModel.opponentIsBot ?? false;

    return GlassPanel(
      borderRadius: 12,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            isBot ? CupertinoIcons.ant : CupertinoIcons.person,
            color: ChromaColors.textTertiary,
            size: 16,
          ),
          const SizedBox(width: 6),
          Text(
            name,
            style: ChromaText.bodyMedium.copyWith(fontWeight: FontWeight.w500),
          ),
        ],
      ),
    );
  }

  Widget _buildScoreBar() {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        // Score.
        StreamBuilder<ScoreUpdatedEvent>(
          stream: eventBus.on<ScoreUpdatedEvent>(),
          builder: (context, snapshot) {
            return GlassPanel(
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
            );
          },
        ),
        // Chain counter (appears during cascades).
        StreamBuilder<ChainCompletedEvent>(
          stream: eventBus.on<ChainCompletedEvent>(),
          builder: (context, snapshot) {
            if (!snapshot.hasData) return const SizedBox.shrink();
            return _ChainCounter(chainLength: snapshot.data!.chainLength);
          },
        ),
        // Moves remaining.
        StreamBuilder<MovesUpdatedEvent>(
          stream: eventBus.on<MovesUpdatedEvent>(),
          builder: (context, snapshot) {
            final moves = viewModel.movesRemaining;
            final color = moves <= 3
                ? Colors.red
                : moves <= 7
                ? Colors.orange
                : ChromaColors.textPrimary;
            return GlassPanel(
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
                      color: color,
                      fontSize: 28,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            );
          },
        ),
      ],
    );
  }
}

class _ChainCounter extends StatelessWidget {
  const _ChainCounter({required this.chainLength});
  final int chainLength;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(8),
        boxShadow: [
          BoxShadow(
            color: Colors.amber.withValues(alpha: 0.3),
            blurRadius: 16,
            spreadRadius: 2,
          ),
        ],
      ),
      child: Text(
        'x$chainLength',
        style: TextStyle(
          color: Colors.amber.shade300,
          fontSize: 32,
          fontWeight: FontWeight.w900,
        ),
      ),
    );
  }
}
