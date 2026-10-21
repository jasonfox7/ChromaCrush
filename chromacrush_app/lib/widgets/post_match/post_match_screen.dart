/// Post-match psychology screen — animated win/loss/draw sequences.
///
/// Win flow (3s):  VICTORY scale-in → score count-up → vault raid placeholder → buttons
/// Loss flow (2.5s): DEFEAT fade-in → near-miss messaging → vault raided → buttons
/// Draw flow: same as win with DRAW title in white, no vault raid.
library;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../config/animation_timings.dart';
import '../../models/view_state.dart';
import '../../services/audio_engine.dart';
import '../../services/haptics_engine.dart';
import '../../theme/chroma_theme.dart';
import '../../theme/glass_panel.dart';
import '../../view_models/match_view_model.dart';
import 'near_miss_widget.dart';
import 'score_reveal_widget.dart';

class PostMatchScreen extends StatefulWidget {
  const PostMatchScreen({super.key});

  @override
  State<PostMatchScreen> createState() => _PostMatchScreenState();
}

class _PostMatchScreenState extends State<PostMatchScreen>
    with TickerProviderStateMixin {
  late final MatchViewModel _viewModel;
  late final AudioEngineBase _audioEngine;
  late final HapticsEngineBase _hapticsEngine;

  // Title animation.
  late final AnimationController _titleController;
  late final Animation<double> _titleScale;
  late final Animation<double> _titleOpacity;

  // Buttons fade-in.
  late final AnimationController _buttonsController;
  late final Animation<double> _buttonsOpacity;

  bool _showScores = false;
  bool _showNearMiss = false;
  bool _showReward = false;
  bool _showRaidResult = false;
  bool _showButtons = false;

  @override
  void initState() {
    super.initState();
    _viewModel = context.read<MatchViewModel>();
    _audioEngine = context.read<AudioEngineBase>();
    _hapticsEngine = context.read<HapticsEngineBase>();

    final isWin = _viewModel.matchResult == MatchOutcome.win;
    final isDraw = _viewModel.matchResult == MatchOutcome.draw;

    // Title animation: win scales 0→1.2→1.0, loss/draw fades in.
    _titleController = AnimationController(
      vsync: this,
      duration: kTitleAnimDuration,
    );

    if (isWin || isDraw) {
      _titleScale =
          TweenSequence<double>([
            TweenSequenceItem(tween: Tween(begin: 0.0, end: 1.2), weight: 60),
            TweenSequenceItem(tween: Tween(begin: 1.2, end: 1.0), weight: 40),
          ]).animate(
            CurvedAnimation(parent: _titleController, curve: Curves.easeOut),
          );
      _titleOpacity = AlwaysStoppedAnimation(1.0);
    } else {
      _titleScale = AlwaysStoppedAnimation(1.0);
      _titleOpacity = CurvedAnimation(
        parent: _titleController,
        curve: Curves.easeIn,
      );
    }

    // Buttons fade-in.
    _buttonsController = AnimationController(
      vsync: this,
      duration: kButtonsFadeDuration,
    );
    _buttonsOpacity = CurvedAnimation(
      parent: _buttonsController,
      curve: Curves.easeIn,
    );

    // Start the sequence.
    _runSequence();
  }

  Future<void> _runSequence() async {
    final isWin = _viewModel.matchResult == MatchOutcome.win;
    final isLoss = _viewModel.matchResult == MatchOutcome.loss;
    final isNearMiss = _viewModel.isNearMiss;

    // Phase 1: Title (T+0–500ms).
    _titleController.forward();
    if (isWin) {
      _audioEngine.playSfx(SoundId.victoryFanfare);
      _hapticsEngine.playPattern(HapticPattern.victory);
    } else if (isLoss) {
      _audioEngine.playSfx(SoundId.defeatSting);
      _hapticsEngine.playPattern(HapticPattern.defeat);
    }

    // Phase 2: Score count-up (T+500ms).
    await Future<void>.delayed(kScorePhaseDelay);
    if (!mounted) return;
    setState(() => _showScores = true);

    // Phase 2b: Near-miss messaging for close losses (T+800ms).
    if (isLoss && isNearMiss) {
      await Future<void>.delayed(kNearMissPhaseDelay);
      if (!mounted) return;
      setState(() => _showNearMiss = true);
    }

    // Phase 2c: Card reward (only shown to the winner — losers don't earn cards).
    if (isWin &&
        _viewModel.rewardResult != null &&
        _viewModel.rewardResult!.awarded) {
      await Future<void>.delayed(kRewardPhaseDelay);
      if (!mounted) return;
      setState(() => _showReward = true);
    }

    // Phase 2d: Raid result (if a card raid occurred).
    if (_viewModel.raidResult != null && _viewModel.raidResult!.occurred) {
      await Future<void>.delayed(kRaidPhaseDelay);
      if (!mounted) return;
      setState(() => _showRaidResult = true);
    }

    // Phase 3: Buttons appear.
    final buttonsDelay = isWin
        ? kButtonsDelayWin // T+3000ms total
        : kButtonsDelayLoss; // T+2000ms total for loss
    await Future<void>.delayed(buttonsDelay);
    if (!mounted) return;
    setState(() => _showButtons = true);
    _buttonsController.forward();
  }

  @override
  void dispose() {
    _titleController.dispose();
    _buttonsController.dispose();
    super.dispose();
  }

  /// Rarity -> glow color for reward card glyphs.
  static const _rarityColors = {
    'common': Color(0xFF8E8E93),
    'rare': Color(0xFF4FC3F7),
    'epic': Color(0xFFAB47BC),
    'legendary': Color(0xFFFFB300),
  };

  Widget _buildRewardPanel() {
    final reward = _viewModel.rewardResult!;
    final cards = reward.cards;
    final multiple = cards.length > 1;
    final label = multiple ? 'Cards earned!' : 'Card earned!';

    return GlassPanel(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              for (var i = 0; i < cards.length; i++) ...[
                if (i > 0) const SizedBox(width: 8),
                Text(
                  String.fromCharCode(0x12F90 + cards[i].cardId),
                  style: TextStyle(
                    fontFamily: 'CyproMinoan',
                    fontSize: 28,
                    color:
                        _rarityColors[cards[i].rarity] ??
                        _rarityColors['common']!,
                  ),
                ),
              ],
            ],
          ),
          const SizedBox(height: 6),
          Text(
            label,
            style: TextStyle(
              color: _rarityColors[cards.first.rarity] ?? Colors.white70,
              fontSize: 16,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildRaidPanel(bool isWin) {
    final raid = _viewModel.raidResult!;
    final cardName = raid.stolenCardName ?? 'a card';
    final cardId = raid.stolenCardId ?? 0;
    // Cypro-Minoan rune glyph for card identity.
    final runeGlyph = String.fromCharCode(0x12F90 + cardId);

    final String message;
    final Color messageColor;
    final bool showShieldIcon;

    if (raid.blockedByCard) {
      final protectorName = raid.blockedByCardName ?? 'a card';
      if (!isWin) {
        message = 'Protected by $protectorName';
      } else {
        message = 'Blocked by $protectorName';
      }
      messageColor = Colors.green.shade300;
      showShieldIcon = true;
    } else if (isWin && !raid.wasShielded) {
      message = 'You raided $cardName!';
      messageColor = Colors.amber;
      showShieldIcon = false;
    } else if (isWin && raid.wasShielded) {
      message = 'Opponent\'s shield held';
      messageColor = Colors.cyan.shade300;
      showShieldIcon = true;
    } else if (!isWin && raid.wasShielded) {
      message = 'Your shield protected $cardName';
      messageColor = Colors.cyan.shade300;
      showShieldIcon = true;
    } else {
      message = '$cardName was raided!';
      messageColor = Colors.red.shade300;
      showShieldIcon = false;
    }

    return GlassPanel(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (!showShieldIcon)
            Text(
              runeGlyph,
              style: TextStyle(
                fontSize: 28,
                color: isWin ? Colors.amber : Colors.red.shade300,
              ),
            ),
          if (showShieldIcon) Icon(Icons.shield, size: 28, color: messageColor),
          const SizedBox(width: 12),
          Text(
            message,
            style: TextStyle(
              color: messageColor,
              fontSize: 16,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final result = _viewModel.matchResult;
    final isWin = result == MatchOutcome.win;
    final isLoss = result == MatchOutcome.loss;

    final (title, titleColor) = switch (result) {
      MatchOutcome.win => ('VICTORY', Colors.amber),
      MatchOutcome.loss => ('DEFEAT', Colors.red.shade300),
      MatchOutcome.draw => ('DRAW', Colors.white70),
      null => ('MATCH OVER', Colors.white70),
    };

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: ChromaGradients.screen),
        child: SafeArea(
          child: LayoutBuilder(
            builder: (context, constraints) {
              final h = constraints.maxHeight;
              // Scale everything relative to available height.
              // Reference height ~812 (iPhone X). Clamp so it never gets absurd.
              final scale = (h / 812).clamp(0.65, 1.2);
              final titleSize = 48.0 * scale;
              final scoreSize = 16.0 * scale;
              final buttonSize = 18.0 * scale;
              final glowSize = 200.0 * scale;
              final gap = 24.0 * scale;
              final bigGap = 48.0 * scale;

              return Center(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    // Title with animation (glow layered behind via Stack).
                    Stack(
                      alignment: Alignment.center,
                      children: [
                        if (isWin)
                          Container(
                            width: glowSize,
                            height: glowSize,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              gradient: RadialGradient(
                                colors: [
                                  Colors.amber.withValues(alpha: 0.08),
                                  Colors.transparent,
                                ],
                              ),
                            ),
                          ),
                        FadeTransition(
                          opacity: _titleOpacity,
                          child: ScaleTransition(
                            scale: _titleScale,
                            child: Text(
                              title,
                              style: TextStyle(
                                color: titleColor,
                                fontSize: titleSize,
                                fontWeight: FontWeight.w900,
                                letterSpacing: 6,
                              ),
                            ),
                          ),
                        ),
                      ],
                    ),

                    SizedBox(height: gap),

                    // Score count-up in glass cards.
                    if (_showScores)
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          GlassPanel(
                            padding: EdgeInsets.symmetric(
                              horizontal: 20 * scale,
                              vertical: 12 * scale,
                            ),
                            child: ScoreRevealWidget(
                              label: 'YOU',
                              targetScore: _viewModel.myScore,
                              outcome: result,
                            ),
                          ),
                          SizedBox(width: 16 * scale),
                          GlassPanel(
                            padding: EdgeInsets.symmetric(
                              horizontal: 20 * scale,
                              vertical: 12 * scale,
                            ),
                            child: ScoreRevealWidget(
                              label: 'OPP',
                              targetScore: _viewModel.opponentScore,
                              outcome: result,
                              delay: kOpponentScoreDelay,
                            ),
                          ),
                        ],
                      ),

                    // Score differential for wins.
                    if (_showScores &&
                        !isLoss &&
                        _viewModel.scoreDifferential > 0) ...[
                      SizedBox(height: 8 * scale),
                      Text(
                        '+${_viewModel.scoreDifferential} points ahead',
                        style: TextStyle(
                          color: Colors.green.shade300,
                          fontSize: scoreSize,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                    ],

                    // Near-miss messaging for close losses.
                    if (_showNearMiss) ...[
                      SizedBox(height: gap * 0.75),
                      NearMissWidget(
                        scoreDifferential: _viewModel.scoreDifferential,
                        delay: const Duration(milliseconds: 200),
                      ),
                    ],

                    // Card reward panel.
                    if (_showReward) ...[
                      SizedBox(height: gap * 0.75),
                      _buildRewardPanel(),
                    ],

                    // Raid result panel.
                    if (_showRaidResult) ...[
                      SizedBox(height: gap * 0.75),
                      _buildRaidPanel(isWin),
                    ],

                    SizedBox(height: bigGap),

                    // Action buttons.
                    if (_showButtons)
                      FadeTransition(
                        opacity: _buttonsOpacity,
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            // Play Again (primary CTA) — gradient pill.
                            GestureDetector(
                              onTap: () => context.go('/matchmaking'),
                              child: Container(
                                padding: EdgeInsets.symmetric(
                                  horizontal: 40 * scale,
                                  vertical: 14 * scale,
                                ),
                                decoration: BoxDecoration(
                                  gradient: ChromaGradients.accent,
                                  borderRadius: BorderRadius.circular(24),
                                  boxShadow: [
                                    BoxShadow(
                                      color: ChromaColors.accent.withValues(
                                        alpha: 0.3,
                                      ),
                                      blurRadius: 16,
                                      spreadRadius: 1,
                                    ),
                                  ],
                                ),
                                child: Text(
                                  'PLAY AGAIN',
                                  style: TextStyle(
                                    color: Colors.white,
                                    fontSize: buttonSize,
                                    fontWeight: FontWeight.bold,
                                    letterSpacing: 2,
                                  ),
                                ),
                              ),
                            ),

                            // Revenge button for near-miss losses — glass outlined pill.
                            if (_viewModel.isNearMiss) ...[
                              SizedBox(height: 10 * scale),
                              GestureDetector(
                                onTap: () => context.go('/matchmaking'),
                                child: Container(
                                  padding: EdgeInsets.symmetric(
                                    horizontal: 40 * scale,
                                    vertical: 12 * scale,
                                  ),
                                  decoration: BoxDecoration(
                                    borderRadius: BorderRadius.circular(24),
                                    border: Border.all(
                                      color: Colors.amber,
                                      width: 1.5,
                                    ),
                                  ),
                                  child: Text(
                                    'REVENGE',
                                    style: TextStyle(
                                      color: Colors.amber,
                                      fontSize: buttonSize * 0.88,
                                      fontWeight: FontWeight.bold,
                                      letterSpacing: 2,
                                    ),
                                  ),
                                ),
                              ),
                            ],

                            SizedBox(height: 12 * scale),

                            // Main menu.
                            GestureDetector(
                              onTap: () => context.go('/'),
                              child: Text(
                                'MAIN MENU',
                                style: TextStyle(
                                  color: ChromaColors.textTertiary,
                                  fontSize: 14 * scale,
                                  letterSpacing: 2,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                  ],
                ),
              );
            },
          ),
        ),
      ),
    );
  }
}
