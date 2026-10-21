/// CampaignGameContainer — wraps Flame CampaignGame + CampaignHUD + overlays.
///
/// Stack layout: GameWidget fills the screen, HUD overlaid on top,
/// with win/lose overlays and a back button.
/// Follows GameContainerWidget pattern but uses CampaignViewModel.
library;

import 'dart:async';

import 'package:flame/game.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../config/visual_theme_service.dart';
import '../../game/campaign_game.dart';
import '../../services/api_client.dart';
import '../../services/audio_engine.dart';
import '../../services/debug_logger.dart';
import '../../services/event_bus.dart';
import '../../services/haptics_engine.dart';
import '../../services/intensity_service.dart';
import '../../services/session_manager.dart';
import '../../config/animation_timings.dart';
import '../../config/game_config.dart';
import '../../extensions/grid_math.dart' show BoardLayout;
import '../../theme/chroma_theme.dart';
import '../../theme/glass_panel.dart';
import '../../view_models/campaign_view_model.dart';
import '../game/campaign_hud.dart';
import '../shared/connection_overlay.dart';

class CampaignGameContainer extends StatefulWidget {
  const CampaignGameContainer({super.key});

  @override
  State<CampaignGameContainer> createState() => _CampaignGameContainerState();
}

class _CampaignGameContainerState extends State<CampaignGameContainer> {
  late final CampaignGame _game;
  late final CampaignViewModel _viewModel;

  @override
  void initState() {
    super.initState();
    final apiClient = context.read<ApiClientBase>();
    final eventBus = context.read<EventBus>();
    final sessionManager = context.read<SessionManager>();
    final debugLogger = context.read<DebugLogger>();
    final audioEngine = context.read<AudioEngineBase>();
    final hapticsEngine = context.read<HapticsEngineBase>();
    final intensityService = context.read<IntensityService>();
    final visualTheme = context.read<VisualThemeBase>();

    _game = CampaignGame(
      apiClient: apiClient,
      eventBus: eventBus,
      sessionManager: sessionManager,
      debugLogger: debugLogger,
      audioEngine: audioEngine,
      hapticsEngine: hapticsEngine,
      intensityService: intensityService,
      visualTheme: visualTheme,
    );

    _viewModel = context.read<CampaignViewModel>();
    _viewModel.addListener(_onViewModelChanged);

    _loadBoardIfReady();
  }

  bool _boardLoaded = false;
  bool _showObjectiveTooltip = false;

  void _loadBoardIfReady() {
    if (_viewModel.state == CampaignState.playing &&
        _viewModel.currentBoard != null &&
        !_boardLoaded) {
      if (!_game.isReady) {
        _game.onReady = _loadBoardIfReady;
        return;
      }
      _game.attemptId = _viewModel.attemptId;
      _game.loadBoard(_viewModel.currentBoard!);
      _game.reloadEquippedCards();
      _boardLoaded = true;

      // Show objective tooltip briefly.
      _showObjectiveTooltip = true;
      Future.delayed(const Duration(milliseconds: 2500), () {
        if (mounted) setState(() => _showObjectiveTooltip = false);
      });
    }
  }

  void _onViewModelChanged() {
    _loadBoardIfReady();

    if (_viewModel.state != CampaignState.playing) {
      _boardLoaded = false;
    }

    if (mounted) setState(() {});
  }

  void _showAbandonDialog(BuildContext context) {
    showCupertinoDialog<void>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: const Text('Abandon Level?'),
        content: const Text('Your progress will be lost.'),
        actions: [
          CupertinoDialogAction(
            child: const Text('Cancel'),
            onPressed: () => Navigator.of(ctx).pop(),
          ),
          CupertinoDialogAction(
            isDestructiveAction: true,
            child: const Text('Abandon'),
            onPressed: () async {
              Navigator.of(ctx).pop();
              final audio = context.read<AudioEngineBase>();
              final router = GoRouter.of(context);
              await _viewModel.abandon();
              if (mounted) {
                audio.stopMusic();
                audio.playMenuMusic();
                router.go('/campaign');
              }
            },
          ),
        ],
      ),
    );
  }

  @override
  void dispose() {
    _viewModel.removeListener(_onViewModelChanged);
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: ChromaColors.bgBase,
      body: Stack(
        children: [
          // Flame game fills the screen.
          GameWidget(game: _game),

          // Score bar (player only, left side of board).
          if (_viewModel.state == CampaignState.playing)
            _CampaignScoreBar(
              eventBus: context.read<EventBus>(),
              viewModel: _viewModel,
            ),

          // HUD overlay (score, obstacles, moves).
          if (_viewModel.state == CampaignState.playing)
            CampaignHUD(
              viewModel: _viewModel,
              eventBus: context.read<EventBus>(),
            ),

          // Back/abandon button (top-left).
          if (_viewModel.state == CampaignState.playing)
            SafeArea(
              child: Align(
                alignment: Alignment.topRight,
                child: Padding(
                  padding: const EdgeInsets.only(top: 8, right: 8),
                  child: GestureDetector(
                    onTap: () => _showAbandonDialog(context),
                    child: Container(
                      width: 36,
                      height: 36,
                      decoration: BoxDecoration(
                        color: Colors.black.withValues(alpha: 0.4),
                        shape: BoxShape.circle,
                      ),
                      child: const Icon(
                        Icons.close,
                        color: Colors.white54,
                        size: 20,
                      ),
                    ),
                  ),
                ),
              ),
            ),

          // Level complete overlay.
          if (_viewModel.state == CampaignState.complete)
            _CompletionOverlay(
              level: _viewModel.currentLevel,
              score: _viewModel.myScore,
              isCheckpoint: _viewModel.isCheckpoint,
              reward: _viewModel.reward,
              onContinue: () {
                _viewModel.reset();
                context.read<AudioEngineBase>().stopMusic();
                context.read<AudioEngineBase>().playMenuMusic();
                context.go('/campaign');
              },
            ),

          // Level failed overlay.
          if (_viewModel.state == CampaignState.failed)
            _FailedOverlay(
              level: _viewModel.currentLevel,
              onRetry: () {
                _viewModel.startLevel(_viewModel.currentLevel);
              },
              onBack: () {
                _viewModel.reset();
                context.read<AudioEngineBase>().stopMusic();
                context.read<AudioEngineBase>().playMenuMusic();
                context.go('/campaign');
              },
            ),

          // Objective tooltip (fades out after board loads).
          if (_showObjectiveTooltip)
            const _ObjectiveTooltip(),

          // Slow connection overlay (above game, below loading).
          if (_viewModel.state == CampaignState.playing)
            ConnectionOverlay(eventBus: context.read<EventBus>()),

          // Loading overlay.
          if (_viewModel.state == CampaignState.loading)
            const _LoadingOverlay(),
        ],
      ),
    );
  }
}

class _CompletionOverlay extends StatefulWidget {
  const _CompletionOverlay({
    required this.level,
    required this.score,
    required this.isCheckpoint,
    required this.onContinue,
    this.reward,
  });

  final int level;
  final int score;
  final bool isCheckpoint;
  final Map<String, dynamic>? reward;
  final VoidCallback onContinue;

  @override
  State<_CompletionOverlay> createState() => _CompletionOverlayState();
}

class _CompletionOverlayState extends State<_CompletionOverlay>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 300),
    );
    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  static IconData _rewardIcon(Map<String, dynamic> reward) {
    return switch (reward['type']) {
      'card_pack' => CupertinoIcons.square_stack_3d_up_fill,
      'gold' => CupertinoIcons.money_dollar_circle_fill,
      _ => CupertinoIcons.gift_fill,
    };
  }

  static String _rewardLabel(Map<String, dynamic> reward) {
    return switch (reward['type']) {
      'card_pack' => '${reward['count']}x ${_capitalize(reward['rarity'] as String)} Card Pack',
      'gold' => '${_formatGold(reward['amount'] as int)} Gold',
      _ => 'Reward',
    };
  }

  static String _capitalize(String s) =>
      s.isEmpty ? s : '${s[0].toUpperCase()}${s.substring(1)}';

  static String _formatGold(int amount) {
    if (amount >= 1000) {
      return '${(amount / 1000).toStringAsFixed(amount % 1000 == 0 ? 0 : 1)}K';
    }
    return '$amount';
  }

  @override
  Widget build(BuildContext context) {
    return FadeTransition(
      opacity: _controller,
      child: GestureDetector(
        onTap: widget.onContinue,
        child: Container(
          color: Colors.black.withValues(alpha: 0.35),
          child: Center(
            child: GlassPanel(
              borderRadius: 24,
              padding:
                  const EdgeInsets.symmetric(horizontal: 32, vertical: 28),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(
                    CupertinoIcons.star_fill,
                    color: Color(0xFFFFD700),
                    size: 48,
                  ),
                  const SizedBox(height: 16),
                  Text(
                    'YOU WIN!',
                    style: ChromaText.headlineMedium.copyWith(
                      color: ChromaColors.textPrimary,
                      letterSpacing: 3,
                    ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Level ${widget.level} Complete',
                    style: ChromaText.bodyMedium.copyWith(
                      color: ChromaColors.textSecondary,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Score: ${widget.score}',
                    style: ChromaText.bodyMedium.copyWith(
                      color: ChromaColors.textSecondary,
                    ),
                  ),
                  if (widget.isCheckpoint && widget.reward != null) ...[
                    const SizedBox(height: 16),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 16,
                        vertical: 10,
                      ),
                      decoration: BoxDecoration(
                        color: const Color(0xFFFFD700).withValues(alpha: 0.12),
                        borderRadius: BorderRadius.circular(12),
                        border: Border.all(
                          color:
                              const Color(0xFFFFD700).withValues(alpha: 0.30),
                        ),
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            _rewardIcon(widget.reward!),
                            color: const Color(0xFFFFD700),
                            size: 20,
                          ),
                          const SizedBox(width: 8),
                          Text(
                            _rewardLabel(widget.reward!),
                            style: ChromaText.bodyMedium.copyWith(
                              color: const Color(0xFFFFD700),
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ],
                  const SizedBox(height: 16),
                  Text(
                    'Tap anywhere to continue',
                    style: ChromaText.labelSmall.copyWith(
                      color: ChromaColors.textSecondary.withValues(alpha: 0.6),
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

class _FailedOverlay extends StatelessWidget {
  const _FailedOverlay({
    required this.level,
    required this.onRetry,
    required this.onBack,
  });

  final int level;
  final VoidCallback onRetry;
  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.black.withValues(alpha: 0.75),
      child: Center(
        child: GlassPanel(
          borderRadius: 24,
          padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 28),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(
                CupertinoIcons.xmark_circle,
                color: Colors.redAccent,
                size: 48,
              ),
              const SizedBox(height: 16),
              Text(
                'LEVEL $level FAILED',
                style: ChromaText.headlineMedium.copyWith(
                  color: ChromaColors.textPrimary,
                  letterSpacing: 3,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'Out of moves!',
                style: ChromaText.bodyMedium.copyWith(
                  color: ChromaColors.textSecondary,
                ),
              ),
              const SizedBox(height: 24),
              Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  GestureDetector(
                    onTap: onBack,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 24,
                        vertical: 12,
                      ),
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(22),
                      ),
                      child: const Text(
                        'BACK',
                        style: TextStyle(
                          color: Colors.white70,
                          fontSize: 14,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 2,
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 16),
                  GestureDetector(
                    onTap: onRetry,
                    child: Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 32,
                        vertical: 14,
                      ),
                      decoration: BoxDecoration(
                        gradient: ChromaGradients.accent,
                        borderRadius: BorderRadius.circular(22),
                        boxShadow: [
                          BoxShadow(
                            color: ChromaColors.accent.withValues(alpha: 0.4),
                            blurRadius: 20,
                            spreadRadius: 1,
                          ),
                        ],
                      ),
                      child: const Text(
                        'RETRY',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 16,
                          fontWeight: FontWeight.bold,
                          letterSpacing: 4,
                        ),
                      ),
                    ),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ObjectiveTooltip extends StatefulWidget {
  const _ObjectiveTooltip();

  @override
  State<_ObjectiveTooltip> createState() => _ObjectiveTooltipState();
}

class _ObjectiveTooltipState extends State<_ObjectiveTooltip>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _opacity;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2400),
    );
    // Fade in 0–15%, hold 15–70%, fade out 70–100%.
    _opacity = TweenSequence<double>([
      TweenSequenceItem(tween: Tween(begin: 0.0, end: 1.0), weight: 15),
      TweenSequenceItem(tween: ConstantTween(1.0), weight: 55),
      TweenSequenceItem(tween: Tween(begin: 1.0, end: 0.0), weight: 30),
    ]).animate(_controller);
    _controller.forward();
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Positioned(
      top: MediaQuery.of(context).padding.top + 60,
      left: 40,
      right: 40,
      child: FadeTransition(
        opacity: _opacity,
        child: Center(
          child: GlassPanel(
            borderRadius: 16,
            padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 12),
            child: Text(
              'Clear all obstacles with specials',
              textAlign: TextAlign.center,
              style: ChromaText.bodyMedium.copyWith(
                color: ChromaColors.textPrimary,
                letterSpacing: 1,
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _LoadingOverlay extends StatelessWidget {
  const _LoadingOverlay();

  @override
  Widget build(BuildContext context) {
    return Container(
      color: ChromaColors.bgBase.withValues(alpha: 0.87),
      child: Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const CupertinoActivityIndicator(
              radius: 16,
              color: ChromaColors.accentGlow,
            ),
            const SizedBox(height: 24),
            Text(
              'Loading level...',
              style: ChromaText.titleMedium.copyWith(
                color: ChromaColors.textSecondary,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Campaign score bar — single vertical bar (left side of board)
// ---------------------------------------------------------------------------

class _CampaignScoreBar extends StatefulWidget {
  const _CampaignScoreBar({
    required this.eventBus,
    required this.viewModel,
  });

  final EventBus eventBus;
  final CampaignViewModel viewModel;

  @override
  State<_CampaignScoreBar> createState() => _CampaignScoreBarState();
}

class _CampaignScoreBarState extends State<_CampaignScoreBar> {
  int _playerScore = 0;
  int _dynamicMax = kScoreInitialMax;
  StreamSubscription<ScoreUpdatedEvent>? _scoreSub;

  @override
  void initState() {
    super.initState();
    _playerScore = widget.viewModel.myScore;
    _scoreSub = widget.eventBus.on<ScoreUpdatedEvent>().listen((event) {
      setState(() {
        _playerScore = event.newScore;
        _maybeExpandMax();
      });
    });
  }

  @override
  void dispose() {
    _scoreSub?.cancel();
    super.dispose();
  }

  void _maybeExpandMax() {
    while (_playerScore > _dynamicMax * kScoreExpansionThreshold) {
      _dynamicMax *= 2;
    }
  }

  static String _formatValue(int value) {
    if (value >= 1000000) return '${(value / 1000000).toStringAsFixed(1)}M';
    if (value >= 1000) return '${value ~/ 1000}K';
    return '$value';
  }

  static List<int> _scaleTicks(int maxVal) {
    if (maxVal <= 0) return [0];
    const steps = [
      1000, 2000, 2500, 5000, 10000, 20000, 25000,
      50000, 100000, 200000, 500000, 1000000,
    ];
    var step = steps.first;
    for (final s in steps) {
      if (maxVal / s <= 6) {
        step = s;
        break;
      }
    }
    final ticks = <int>[];
    for (var v = 0; v <= maxVal; v += step) {
      ticks.add(v);
    }
    if (ticks.last != maxVal) ticks.add(maxVal);
    return ticks;
  }

  @override
  Widget build(BuildContext context) {
    return LayoutBuilder(
      builder: (context, constraints) {
        final screenWidth = constraints.maxWidth;
        final screenHeight = constraints.maxHeight;
        final layout = BoardLayout(screenWidth, screenHeight);
        final boardLeft = layout.boardLeft;
        final boardTop = layout.boardTop;
        const barWidth = kScoreBarWidth;
        const barGap = kScoreBarGap;
        final barHeight = layout.boardExtent;

        final playerFill = _dynamicMax > 0
            ? (_playerScore / _dynamicMax).clamp(0.0, 1.0)
            : 0.0;

        final ticks = _scaleTicks(_dynamicMax);
        final leftBarX = boardLeft - barWidth - barGap;

        return Stack(
          children: [
            for (final tick in ticks)
              if (tick > 0)
                Positioned(
                  right: screenWidth - leftBarX + 2,
                  top: boardTop +
                      barHeight -
                      (barHeight * tick / _dynamicMax) -
                      5,
                  child: Text(
                    _formatValue(tick),
                    textAlign: TextAlign.right,
                    style: TextStyle(
                      color: const Color(0xFF00E5FF).withValues(alpha: 0.35),
                      fontSize: 8,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 0.5,
                    ),
                  ),
                ),
            Positioned(
              left: leftBarX,
              top: boardTop,
              child: SizedBox(
                width: barWidth,
                height: barHeight,
                child: Stack(
                  alignment: Alignment.bottomCenter,
                  children: [
                    Container(
                      width: barWidth,
                      height: barHeight,
                      decoration: BoxDecoration(
                        color: Colors.white.withValues(alpha: 0.06),
                        borderRadius: BorderRadius.circular(7),
                      ),
                    ),
                    AnimatedContainer(
                      duration: kScoreBarNormalFillDuration,
                      curve: Curves.easeOutCubic,
                      width: barWidth,
                      height: barHeight * playerFill,
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          begin: Alignment.bottomCenter,
                          end: Alignment.topCenter,
                          colors: [Color(0xFF00897B), Color(0xFF00E5FF)],
                        ),
                        borderRadius: BorderRadius.circular(7),
                        boxShadow: [
                          BoxShadow(
                            color: const Color(0xFF00E5FF)
                                .withValues(alpha: 0.4),
                            blurRadius: 8,
                          ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        );
      },
    );
  }
}
