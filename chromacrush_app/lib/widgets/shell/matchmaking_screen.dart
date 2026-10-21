/// Matchmaking screen — searching animation with 2s minimum floor.
///
/// Phase 1: Spinner + "Finding opponent..." (min 2s)
/// Phase 2: Opponent card slides in (1s hold)
/// Phase 3: Navigate to /game
library;

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../config/animation_timings.dart';
import '../../theme/chroma_theme.dart';
import '../../theme/glass_panel.dart';
import '../../view_models/match_view_model.dart';

class MatchmakingScreen extends StatefulWidget {
  const MatchmakingScreen({super.key});

  @override
  State<MatchmakingScreen> createState() => _MatchmakingScreenState();
}

class _MatchmakingScreenState extends State<MatchmakingScreen>
    with SingleTickerProviderStateMixin {
  late final MatchViewModel _viewModel;
  late final AnimationController _slideController;
  late final Animation<Offset> _slideAnimation;

  bool _opponentRevealed = false;
  bool _navigating = false;

  @override
  void initState() {
    super.initState();

    _slideController = AnimationController(
      vsync: this,
      duration: kMatchmakingSlideInDuration,
    );
    _slideAnimation =
        Tween<Offset>(begin: const Offset(1.0, 0.0), end: Offset.zero).animate(
          CurvedAnimation(parent: _slideController, curve: Curves.easeOutCubic),
        );

    // Read shared MatchViewModel from Provider tree.
    _viewModel = context.read<MatchViewModel>();
    _viewModel.addListener(_onViewModelChanged);

    // Start matchmaking if not already in progress.
    if (_viewModel.state == MatchState.idle ||
        _viewModel.state == MatchState.ended) {
      _viewModel.startSinglePlayer();
    }
  }

  void _onViewModelChanged() {
    if (!mounted) return;

    if (_viewModel.state == MatchState.playing && !_navigating) {
      // Opponent found → reveal card, then navigate after hold.
      if (!_opponentRevealed) {
        setState(() => _opponentRevealed = true);
        _slideController.forward();
        // Hold for 1s, then navigate.
        Future.delayed(kMatchmakingHoldDuration, _navigateToGame);
      }
    }

    if (_viewModel.state == MatchState.idle &&
        _viewModel.errorMessage != null) {
      setState(() {});
    }
  }

  void _navigateToGame() {
    if (!mounted || _navigating) return;
    _navigating = true;
    context.go('/game');
  }

  @override
  void dispose() {
    _viewModel.removeListener(_onViewModelChanged);
    _slideController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: ChromaGradients.screen),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              // Error state.
              if (_viewModel.errorMessage != null) ...[
                Icon(
                  CupertinoIcons.exclamationmark_circle,
                  color: Colors.red.shade300,
                  size: 48,
                ),
                const SizedBox(height: 16),
                Text(
                  _viewModel.errorMessage!,
                  textAlign: TextAlign.center,
                  style: ChromaText.bodyMedium,
                ),
                const SizedBox(height: 24),
                GestureDetector(
                  onTap: () => context.go('/'),
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 32,
                      vertical: 14,
                    ),
                    decoration: BoxDecoration(
                      gradient: ChromaGradients.accent,
                      borderRadius: BorderRadius.circular(24),
                    ),
                    child: const Text(
                      'BACK',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        letterSpacing: 2,
                      ),
                    ),
                  ),
                ),
              ] else ...[
                // Searching spinner.
                const CupertinoActivityIndicator(
                  radius: 16,
                  color: ChromaColors.accentGlow,
                ),
                const SizedBox(height: 24),
                Text(
                  _opponentRevealed ? 'Opponent found!' : 'Finding opponent...',
                  style: ChromaText.titleMedium.copyWith(
                    color: ChromaColors.textSecondary,
                  ),
                ),

                // Opponent card (slides in when found).
                if (_opponentRevealed) ...[
                  const SizedBox(height: 32),
                  SlideTransition(
                    position: _slideAnimation,
                    child: _OpponentCard(
                      name: _viewModel.opponentName ?? 'Opponent',
                      isBot: _viewModel.opponentIsBot ?? false,
                      cards: _viewModel.opponentCards,
                    ),
                  ),
                ],
              ],
            ],
          ),
        ),
      ),
    );
  }
}

/// Rarity -> glow color (matches PlayerStatusBar encoding).
const _runeRarityColors = {
  'common': Color(0xFF8E8E93),
  'rare': Color(0xFF4FC3F7),
  'epic': Color(0xFFAB47BC),
  'legendary': Color(0xFFFFB300),
};

class _OpponentCard extends StatelessWidget {
  const _OpponentCard({
    required this.name,
    required this.isBot,
    this.cards = const [],
  });
  final String name;
  final bool isBot;
  final List<({int cardId, String rarity})> cards;

  @override
  Widget build(BuildContext context) {
    return GlassPanel(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                isBot ? CupertinoIcons.ant : CupertinoIcons.person,
                color: ChromaColors.accentGlow,
                size: 28,
              ),
              const SizedBox(width: 12),
              Text(name, style: ChromaText.titleMedium),
            ],
          ),
          if (cards.isNotEmpty) ...[
            const SizedBox(height: 8),
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                for (final card in cards) ...[
                  Text(
                    String.fromCharCode(0x12F90 + card.cardId),
                    style: TextStyle(
                      fontFamily: 'CyproMinoan',
                      fontSize: 20,
                      color:
                          _runeRarityColors[card.rarity] ??
                          _runeRarityColors['common']!,
                    ),
                  ),
                  if (card != cards.last) const SizedBox(width: 8),
                ],
              ],
            ),
          ],
        ],
      ),
    );
  }
}
