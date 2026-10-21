/// Main Flame game — composition root for the game layer.
///
/// Receives services via constructor (not context). Creates BoardLayer,
/// InputHandler, AnimationSequencer. Coordinates move submission and animation.
library;

import 'package:flame/game.dart';
import 'package:flutter/painting.dart';

import '../config/visual_config.dart';
import '../config/visual_theme_service.dart';
import '../extensions/grid_math.dart';
import '../models/backend_contract.dart';
import '../services/api_client.dart';
import '../services/audio_engine.dart';
import '../services/debug_logger.dart';
import '../services/event_bus.dart';
import '../services/haptics_engine.dart';
import '../services/intensity_service.dart';
import '../services/session_manager.dart';
import 'animation_sequencer.dart';
import 'background_layer.dart';
import 'board_layer.dart';
import 'cascade_animator.dart';
import 'api_call_tracker_mixin.dart';
import 'game_loadout_mixin.dart';
import 'gem_shader_library.dart';
import 'input_handler.dart';
import 'particle_layer.dart';
import 'player_status_bar.dart';

class ChromaCrushGame extends FlameGame with GameLoadoutMixin, ApiCallTrackerMixin {
  ChromaCrushGame({
    required this.apiClient,
    required this.eventBus,
    required this.sessionManager,
    required this.debugLogger,
    required this.visualTheme,
    this.audioEngine,
    this.hapticsEngine,
    this.intensityService,
  });

  @override
  final ApiClientBase apiClient;
  @override
  final EventBus eventBus;
  final SessionManager sessionManager;
  final DebugLogger debugLogger;
  final VisualThemeBase visualTheme;
  @override
  final AudioEngineBase? audioEngine;
  final HapticsEngineBase? hapticsEngine;
  @override
  final IntensityService? intensityService;

  late final BoardLayout layout;
  @override
  late final BackgroundLayer backgroundLayer;
  @override
  late final BoardLayer boardLayer;
  late final InputHandler inputHandler;
  late final AnimationSequencer animationSequencer;
  late final CascadeAnimator cascadeAnimator;
  @override
  late final ParticleLayer particleLayer;
  @override
  late final PlayerStatusBar playerStatusBar;

  String? matchId;

  /// Whether onLoad has completed and the game is ready to accept boards.
  bool isReady = false;

  /// Callback fired once when the game finishes loading (for deferred board load).
  void Function()? onReady;

  /// Cumulative score for the current match.
  int _cumulativeScore = 0;

  /// Current board state (for diffing after moves).
  List<List<int>>? _currentBoard;

  @override
  Color backgroundColor() => const Color(0xFF0D0D14);

  @override
  Future<void> onLoad() async {
    // Discover music tracks from asset bundle.
    await GameLoadoutMixin.discoverMusicTracks();

    // Load gem shaders (falls back to Canvas SDF if unavailable).
    // Also loads ripple background shader.
    await GemShaderLibrary.instance.load();

    // Compute responsive board layout from screen size.
    layout = BoardLayout(size.x, size.y);

    // Full-screen ripple background (renders behind everything at priority -10).
    backgroundLayer = BackgroundLayer(screenSize: size, theme: visualTheme);
    add(backgroundLayer);

    boardLayer = BoardLayer(
      onGemTapped: _onGemTapped,
      onDragGesture: (startRow, startCol, deltaX, deltaY) {
        inputHandler.onDragComplete(startRow, startCol, deltaX, deltaY);
      },
      theme: visualTheme,
      layout: layout,
    );

    boardLayer.position.setValues(layout.boardLeft, layout.boardTop);

    add(boardLayer);

    // Player status bar — hearts + mega gem inventory, above the board.
    playerStatusBar = PlayerStatusBar(
      barPosition: Vector2(
        layout.boardLeft,
        layout.boardTop -
            layout.cellSize * kStatusBarHeightRatio -
            layout.cellSize * kStatusBarGapRatio,
      ),
      barWidth: layout.boardExtent,
      theme: visualTheme,
      cellSize: layout.cellSize,
    );
    final energy = sessionManager.energy;
    playerStatusBar.setHearts(
      energy?.currentHearts ?? 0,
      energy?.maxHearts ?? 7,
    );
    playerStatusBar.onMegaTapped = _onMegaActivated;
    add(playerStatusBar);

    // Fetch equipped card loadout for rune display + mega inventory.
    loadEquippedCards();
    loadMegaInventory();

    // Particle layer sits above the board (priority renders on top).
    particleLayer = ParticleLayer(theme: visualTheme, layout: layout);
    particleLayer.position.setValues(layout.boardLeft, layout.boardTop);
    add(particleLayer);

    inputHandler = InputHandler(onSwap: _onSwapCommitted);
    inputHandler.onSelectionChanged = handleSelectionChanged;

    cascadeAnimator = CascadeAnimator(
      boardContainer: boardLayer,
      gameRef: this,
    );

    animationSequencer = AnimationSequencer(
      boardLayer: boardLayer,
      eventBus: eventBus,
      layout: layout,
      cascadeAnimator: cascadeAnimator,
      particleLayer: particleLayer,
      backgroundLayer: backgroundLayer,
      audioEngine: audioEngine,
      hapticsEngine: hapticsEngine,
    );

    // CardProcEvent is now handled by the GameHUD card panel directly.

    isReady = true;
    onReady?.call();
  }

  @override
  void update(double dt) {
    super.update(dt);
    applyIntensity(dt);
  }

  // ---------------------------------------------------------------------------
  // Board loading
  // ---------------------------------------------------------------------------

  /// Load initial board state from backend. Starts background music.
  void loadBoard(BoardStateResponse board) {
    _cumulativeScore = board.score;
    _currentBoard = board.cells.map((row) => List<int>.from(row)).toList();
    boardLayer.loadBoard(board);

    // Start a random music track for this match.
    playRandomMusicTrack();

    debugLogger.logBoardState('initial_load', board.cells, matchId: matchId);
  }

  // ---------------------------------------------------------------------------
  // Periodic shuffle (Void Instability, Tremor, Earthquake)
  // ---------------------------------------------------------------------------

  @override
  void onPeriodicShuffleTriggered(String cardName) async {
    final currentMatchId = matchId;
    if (currentMatchId == null) return;
    if (inputHandler.state != InputState.idle) return;

    inputHandler.state = InputState.animating;

    try {
      final request = MegaActivationRequest(
        slotIndex: 4,
        timestampMs: DateTime.now().millisecondsSinceEpoch,
        source: 'card_shuffle',
      );

      final response = await trackApiCall(
        () => apiClient.activateMega(currentMatchId, request),
      );

      if (response.success && response.data != null) {
        final result = response.data!;
        final board = result.newBoard;

        if (_currentBoard != null && board != null) {
          boardLayer.syncToBoard(board.cells, board.functions);
          _currentBoard =
              board.cells.map((row) => List<int>.from(row)).toList();
        }

        eventBus.fire(MegaActivatedEvent(slotIndex: 4, scoreGained: 0));
      }
    } catch (e) {
      debugLogger.logError(
        '$cardName shuffle error: $e',
        matchId: currentMatchId,
      );
    }

    inputHandler.onAnimationComplete();
  }

  // ---------------------------------------------------------------------------
  // Mega gem activation
  // ---------------------------------------------------------------------------

  Future<void> _onMegaActivated(int slotIndex) async {
    final currentMatchId = matchId;
    if (currentMatchId == null) return;
    if (inputHandler.state != InputState.idle) return;

    inputHandler.state = InputState.animating;

    try {
      final request = MegaActivationRequest(
        slotIndex: slotIndex,
        timestampMs: DateTime.now().millisecondsSinceEpoch,
      );

      final response = await trackApiCall(
        () => apiClient.activateMega(currentMatchId, request),
      );

      if (!response.success || response.data == null) {
        // API failed — still refresh inventory (server may have consumed).
        await loadMegaInventory();
        return;
      }

      final result = response.data!;

      // Play cascade animation (reuse move result animation).
      final oldBoard = _currentBoard;
      final board = result.newBoard;

      if (oldBoard != null && board != null) {
        final newBoard = board.cells;
        final newFunctions = board.functions;

        if (result.cascadeSteps.isNotEmpty) {
          try {
            await animationSequencer.playMoveResult(
              oldBoard: oldBoard,
              result: result,
              fromRow: 0,
              fromCol: 0,
              toRow: 0,
              toCol: 1,
            );
          } catch (e) {
            debugLogger.logError(
              'Mega animation error, forcing board sync: $e',
              matchId: currentMatchId,
            );
          }
        }

        // Always sync to server board state.
        boardLayer.syncToBoard(newBoard, newFunctions);
        _currentBoard = newBoard.map((row) => List<int>.from(row)).toList();
      }

      // Accumulate score and fire events.
      _cumulativeScore += result.scoreGained;
      if (result.scoreGained > 0) {
        eventBus.fire(
          ScoreUpdatedEvent(
            newScore: _cumulativeScore,
            delta: result.scoreGained,
          ),
        );
      }

      eventBus.fire(
        MegaActivatedEvent(
          slotIndex: slotIndex,
          scoreGained: result.scoreGained,
        ),
      );

      // Fire card proc event if any modifiers were applied.
      if (result.appliedModifiers.isNotEmpty) {
        final cardIds = result.appliedModifiers
            .map((m) => m.cardId)
            .toSet()
            .toList();
        eventBus.fire(CardProcEvent(cardIds: cardIds));
      }

      // Refresh inventory counts after activation.
      await loadMegaInventory();

      // Check for match completion (e.g. Lucky Rabbit instant win).
      if (result.matchCompleted) {
        audioEngine?.stopMusic();
        cancelPeriodicShuffleTimers();

        eventBus.fire(
          MatchEndedEvent(
            matchId: currentMatchId,
            won: null,
            myScore: _cumulativeScore,
            opponentScore: 0,
          ),
        );
      }
    } catch (e) {
      debugLogger.logError(
        'Mega activation error: $e',
        matchId: currentMatchId,
      );
    } finally {
      inputHandler.onAnimationComplete();
    }
  }

  // ---------------------------------------------------------------------------
  // Input handling
  // ---------------------------------------------------------------------------

  void _onGemTapped(int row, int col) {
    inputHandler.onGemTapped(row, col);
  }

  Future<void> _onSwapCommitted(
    int fromRow,
    int fromCol,
    int toRow,
    int toCol,
  ) async {
    final currentMatchId = matchId;
    if (currentMatchId == null) return;

    inputHandler.state = InputState.animating;

    // Debug: log board state and move attempt.
    if (_currentBoard != null) {
      debugLogger.logMoveAttempt(
        fromRow,
        fromCol,
        toRow,
        toCol,
        _currentBoard!,
        matchId: currentMatchId,
      );
    }

    // Optimistic swap animation (150ms).
    await boardLayer.animateSwap(fromRow, fromCol, toRow, toCol);

    // Submit move to backend.
    try {
      final request = MoveRequest(
        fromRow: fromRow,
        fromCol: fromCol,
        toRow: toRow,
        toCol: toCol,
        timestampMs: DateTime.now().millisecondsSinceEpoch,
      );

      debugLogger.logApiRequest(
        '/matches/$currentMatchId/move',
        'POST',
        matchId: currentMatchId,
        body: {
          'from': [fromRow, fromCol],
          'to': [toRow, toCol],
        },
      );

      final response = await trackApiCall(
        () => apiClient.submitMove(currentMatchId, request),
      );

      if (!response.success || response.data == null) {
        debugLogger.logApiResponse(
          '/matches/$currentMatchId/move',
          false,
          matchId: currentMatchId,
          error: 'success=${response.success}, data=null',
        );
        // Swap back (rubber-band).
        await boardLayer.animateSwap(toRow, toCol, fromRow, fromCol);
        inputHandler.onAnimationComplete();
        return;
      }

      final result = response.data!;
      debugLogger.logMoveResponse(
        valid: result.valid,
        scoreGained: result.scoreGained,
        matchesFound: result.matchesFound,
        cascades: result.cascades,
        movesRemaining: result.movesRemaining,
        newBoard: result.newBoard?.cells,
        matchId: currentMatchId,
      );

      if (!result.valid) {
        // Invalid move — rubber-band.
        await boardLayer.animateSwap(toRow, toCol, fromRow, fromCol);
        inputHandler.onAnimationComplete();
        return;
      }

      // Valid move — play animation sequence and always sync board.
      final oldBoard = _currentBoard;
      final board = result.newBoard;

      if (oldBoard != null && board != null) {
        final newBoard = board.cells;
        final newFunctions = board.functions;
        try {
          await animationSequencer.playMoveResult(
            oldBoard: oldBoard,
            result: result,
            fromRow: fromRow,
            fromCol: fromCol,
            toRow: toRow,
            toCol: toCol,
          );
        } catch (e) {
          debugLogger.logError(
            'Animation error, forcing board sync: $e',
            matchId: currentMatchId,
          );
        }
        // Always sync to server board state after a valid move.
        boardLayer.syncToBoard(newBoard, newFunctions);
        _currentBoard = newBoard.map((row) => List<int>.from(row)).toList();

        debugLogger.logBoardSync(
          'after_move',
          newBoard,
          matchId: currentMatchId,
        );
      }

      // Accumulate score and fire events for HUD updates.
      _cumulativeScore += result.scoreGained;
      eventBus.fire(
        ScoreUpdatedEvent(
          newScore: _cumulativeScore,
          delta: result.scoreGained,
        ),
      );
      eventBus.fire(MovesUpdatedEvent(movesRemaining: result.movesRemaining));

      if (result.cascades > 0) {
        eventBus.fire(
          ChainCompletedEvent(
            chainLength: result.cascades,
            totalScore: result.scoreGained,
          ),
        );
      }

      // Fire card proc event if any modifiers were applied.
      if (result.appliedModifiers.isNotEmpty) {
        final cardIds = result.appliedModifiers
            .map((m) => m.cardId)
            .toSet()
            .toList();
        eventBus.fire(CardProcEvent(cardIds: cardIds));
      }

      // WORKAROUND: Backend only sets matchCompleted=true when BOTH players
      // have 0 moves remaining. In single-player bot matches, the bot never
      // plays, so matchCompleted is never true. We also trigger match end
      // when movesRemaining hits 0 (player finished their moves).
      // TODO: Remove movesRemaining check once backend auto-completes bot
      // matches, or when multiplayer "waiting for opponent" state is added.
      if (result.matchCompleted || result.movesRemaining == 0) {
        // Stop background music and periodic shuffle timers.
        audioEngine?.stopMusic();
        cancelPeriodicShuffleTimers();

        // Fire match ended event — MatchViewModel will determine win/loss
        // and fetch raid result from match state.
        eventBus.fire(
          MatchEndedEvent(
            matchId: currentMatchId,
            won:
                null, // Determined by MatchViewModel after fetching final state.
            myScore: _cumulativeScore,
            opponentScore: 0,
          ),
        );
      }
    } catch (e) {
      debugLogger.logError('Move error: $e', matchId: currentMatchId);
      // On error, rubber-band the swap.
      await boardLayer.animateSwap(toRow, toCol, fromRow, fromCol);
    }

    inputHandler.onAnimationComplete();
  }
}
