/// GameContainerWidget — wraps Flame GameWidget + Flutter HUD overlay.
///
/// Stack layout: GameWidget fills the screen, HUD overlaid on top.
/// Focused on active gameplay only — navigation shell handles matchmaking,
/// main menu, and post-match screens via GoRouter.
library;

import 'package:flame/game.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../extensions/grid_math.dart' show BoardLayout;
import '../../game/chroma_crush_game.dart';
import '../../services/api_client.dart';
import '../../config/visual_theme_service.dart';
import '../../services/audio_engine.dart';
import '../../services/debug_logger.dart';
import '../../services/event_bus.dart';
import '../../services/haptics_engine.dart';
import '../../services/intensity_service.dart';
import '../../services/session_manager.dart';
import '../../theme/chroma_theme.dart';
import '../../view_models/match_view_model.dart';
import '../shared/connection_overlay.dart';
import 'bot_move_preview.dart';
import 'game_hud.dart';
import 'score_comparison_bars.dart';

class GameContainerWidget extends StatefulWidget {
  const GameContainerWidget({super.key});

  @override
  State<GameContainerWidget> createState() => _GameContainerWidgetState();
}

class _GameContainerWidgetState extends State<GameContainerWidget> {
  late final ChromaCrushGame _game;
  late final MatchViewModel _viewModel;

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

    _game = ChromaCrushGame(
      apiClient: apiClient,
      eventBus: eventBus,
      sessionManager: sessionManager,
      debugLogger: debugLogger,
      audioEngine: audioEngine,
      hapticsEngine: hapticsEngine,
      intensityService: intensityService,
      visualTheme: visualTheme,
    );

    // Read shared MatchViewModel from Provider tree.
    _viewModel = context.read<MatchViewModel>();
    _viewModel.addListener(_onViewModelChanged);

    // Load board immediately if match is already in progress (arriving from matchmaking).
    _loadBoardIfReady();
  }

  bool _boardLoaded = false;

  void _loadBoardIfReady() {
    if (_viewModel.state == MatchState.playing &&
        _viewModel.currentBoard != null &&
        !_boardLoaded) {
      // Flame's onLoad() is async — boardLayer isn't available until it completes.
      if (!_game.isReady) {
        _game.onReady = _loadBoardIfReady;
        return;
      }
      _game.matchId = _viewModel.matchId;
      _game.loadBoard(_viewModel.currentBoard!);
      _game.reloadEquippedCards();
      _boardLoaded = true;
    }
  }

  void _onViewModelChanged() {
    _loadBoardIfReady();

    // Reset flag when match ends so next match loads fresh.
    if (_viewModel.state != MatchState.playing) {
      _boardLoaded = false;
    }

    // Navigate to post-match on match end.
    if (_viewModel.state == MatchState.ended && mounted) {
      // Stop game music and restart menu music.
      final audio = context.read<AudioEngineBase>();
      audio.stopMusic();
      audio.playMenuMusic();
      context.go('/post-match');
      return;
    }

    // Rejoin failed (match no longer active) — go back to main menu.
    if (_viewModel.state == MatchState.idle &&
        _viewModel.errorMessage != null &&
        mounted) {
      context.read<AudioEngineBase>().playMenuMusic();
      context.go('/');
      return;
    }

    // Trigger rebuild for HUD updates.
    if (mounted) setState(() {});
  }

  void _showForfeitDialog(BuildContext context) {
    showCupertinoDialog<void>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: const Text('Forfeit Match?'),
        content: const Text('You will receive a loss.'),
        actions: [
          CupertinoDialogAction(
            child: const Text('Cancel'),
            onPressed: () => Navigator.of(ctx).pop(),
          ),
          CupertinoDialogAction(
            isDestructiveAction: true,
            child: const Text('Forfeit'),
            onPressed: () {
              Navigator.of(ctx).pop();
              _viewModel.forfeit();
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

          // Score comparison bars (player vs bot).
          if (_viewModel.state == MatchState.playing)
            ScoreComparisonBars(
              eventBus: context.read<EventBus>(),
              matchViewModel: _viewModel,
              botPlayerService: _viewModel.botPlayerService,
            ),

          // Bot move preview (faked mini-board below the main board).
          if (_viewModel.state == MatchState.playing)
            Builder(
              builder: (context) {
                final screen = MediaQuery.sizeOf(context);
                final layout = BoardLayout(screen.width, screen.height);
                final previewTop = layout.boardTop + layout.boardExtent + 16;
                return Positioned(
                  top: previewTop,
                  left: (screen.width - 240) / 2,
                  child: BotMovePreview(eventBus: context.read<EventBus>()),
                );
              },
            ),

          // HUD overlay (score, moves, opponent info).
          if (_viewModel.state == MatchState.playing)
            GameHUD(viewModel: _viewModel, eventBus: context.read<EventBus>()),

          // Forfeit button (top-right).
          if (_viewModel.state == MatchState.playing)
            SafeArea(
              child: Align(
                alignment: Alignment.topRight,
                child: Padding(
                  padding: const EdgeInsets.only(top: 8, right: 8),
                  child: GestureDetector(
                    onTap: () => _showForfeitDialog(context),
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

          // Slow connection overlay (above game, below loading).
          if (_viewModel.state == MatchState.playing)
            ConnectionOverlay(eventBus: context.read<EventBus>()),

          // Loading overlay (board being fetched).
          if (_viewModel.state == MatchState.loading) const _LoadingOverlay(),
        ],
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
              'Loading board...',
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
