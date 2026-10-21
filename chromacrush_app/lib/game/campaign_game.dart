/// Campaign Flame game — single-player level with obstacle-clearing objective.
///
/// Follows ChromaCrushGame pattern but skips PvP-only components
/// (no BotPlayerService). Uses campaign API (submitCampaignMove /
/// activateCampaignMega).
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

class CampaignGame extends FlameGame with GameLoadoutMixin, ApiCallTrackerMixin {
  CampaignGame({
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

  /// The current campaign attempt ID (set by CampaignGameContainer).
  String? attemptId;

  /// Whether onLoad has completed and the game is ready to accept boards.
  bool isReady = false;

  /// Callback fired once when the game finishes loading.
  void Function()? onReady;

  /// Cumulative score for the current level.
  int _cumulativeScore = 0;

  /// Current board state (for diffing after moves).
  List<List<int>>? _currentBoard;

  @override
  Color backgroundColor() => const Color(0xFF0D0D14);

  @override
  Future<void> onLoad() async {
    await GameLoadoutMixin.discoverMusicTracks();
    await GemShaderLibrary.instance.load();

    layout = BoardLayout(size.x, size.y);

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

  void loadBoard(BoardStateResponse board) {
    _cumulativeScore = 0;
    _currentBoard = board.cells.map((row) => List<int>.from(row)).toList();
    boardLayer.loadBoard(board);

    playRandomMusicTrack();

    debugLogger.logBoardState(
      'campaign_initial_load',
      board.cells,
      matchId: attemptId,
    );
  }

  // ---------------------------------------------------------------------------
  // Periodic shuffle (Void Instability, Tremor, Earthquake)
  // ---------------------------------------------------------------------------

  @override
  void onPeriodicShuffleTriggered(String cardName) async {
    final currentAttemptId = attemptId;
    if (currentAttemptId == null) return;
    if (inputHandler.state != InputState.idle) return;

    inputHandler.state = InputState.animating;

    try {
      final request = MegaActivationRequest(
        slotIndex: 4,
        timestampMs: DateTime.now().millisecondsSinceEpoch,
        source: 'card_shuffle',
      );

      final response = await trackApiCall(
        () => apiClient.activateCampaignMega(currentAttemptId, request),
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

        if (result.status == 'won' || result.obstaclesRemaining == 0) {
          audioEngine?.stopMusic();
          cancelPeriodicShuffleTimers();
          eventBus.fire(ObstaclesUpdatedEvent(remaining: 0));
        }
      }
    } catch (e) {
      debugLogger.logError(
        '$cardName shuffle error: $e',
        matchId: currentAttemptId,
      );
    }

    inputHandler.onAnimationComplete();
  }

  // ---------------------------------------------------------------------------
  // Mega gem activation
  // ---------------------------------------------------------------------------

  Future<void> _onMegaActivated(int slotIndex) async {
    final currentAttemptId = attemptId;
    if (currentAttemptId == null) return;
    if (inputHandler.state != InputState.idle) return;

    inputHandler.state = InputState.animating;

    try {
      final request = MegaActivationRequest(
        slotIndex: slotIndex,
        timestampMs: DateTime.now().millisecondsSinceEpoch,
      );

      debugLogger.logApiRequest(
        '/campaign/$currentAttemptId/mega',
        'POST',
        matchId: currentAttemptId,
        body: {'slotIndex': slotIndex},
      );

      final response = await trackApiCall(
        () => apiClient.activateCampaignMega(currentAttemptId, request),
      );

      if (!response.success || response.data == null) {
        debugLogger.logApiResponse(
          '/campaign/$currentAttemptId/mega',
          false,
          matchId: currentAttemptId,
          error: 'success=${response.success}, data=null',
        );
        await loadMegaInventory();
        return;
      }

      final result = response.data!;
      final scoreGained = result.scoreGained;

      // Detect win early — fire events BEFORE cascade so overlay shows
      // immediately while animations continue in the background.
      final isWin =
          result.status == 'won' || result.obstaclesRemaining == 0;
      if (isWin) {
        if (scoreGained > 0) {
          _cumulativeScore += scoreGained;
        }
        eventBus.fire(
          ScoreUpdatedEvent(
              newScore: _cumulativeScore, delta: scoreGained),
        );
        eventBus.fire(MegaActivatedEvent(
            slotIndex: slotIndex, scoreGained: scoreGained));

        final cleared = <({int row, int col})>[];
        final transmuted =
            <({int row, int col, int fromFunc, int toFunc})>[];
        for (final oe in result.obstacleEvents) {
          if (oe.type == 'cleared') {
            cleared.add((row: oe.row, col: oe.col));
          } else if (oe.type == 'transmuted') {
            transmuted.add((
              row: oe.row,
              col: oe.col,
              fromFunc: oe.fromFunc ?? 0,
              toFunc: oe.toFunc ?? 0,
            ));
          }
        }
        eventBus.fire(ObstaclesUpdatedEvent(
          remaining: 0,
          cleared: cleared.isNotEmpty ? cleared : null,
          transmuted: transmuted.isNotEmpty ? transmuted : null,
        ));

        audioEngine?.stopMusic();
        cancelPeriodicShuffleTimers();
      }

      // Play cascade animation and sync board.
      final oldBoard = _currentBoard;
      final board = result.newBoard;

      if (oldBoard != null && board != null) {
        final newBoard = board.cells;
        final newFunctions = board.functions;

        if (result.cascadeSteps.isNotEmpty) {
          try {
            await animationSequencer.playCascadeSteps(
              result.cascadeSteps,
              newBoard,
              newFunctions,
            );
          } catch (e) {
            debugLogger.logError(
              'Campaign mega animation error, forcing board sync: $e',
              matchId: currentAttemptId,
            );
          }
        }

        // Always sync to server board state.
        boardLayer.syncToBoard(newBoard, newFunctions);
        _currentBoard = newBoard.map((row) => List<int>.from(row)).toList();

        debugLogger.logBoardSync(
          'after_campaign_mega',
          newBoard,
          matchId: currentAttemptId,
        );
      }

      // Fire events only if not a win (already fired above for wins).
      if (!isWin) {
        if (scoreGained > 0) {
          _cumulativeScore += scoreGained;
        }
        eventBus.fire(
          ScoreUpdatedEvent(
              newScore: _cumulativeScore, delta: scoreGained),
        );
        eventBus.fire(MegaActivatedEvent(
            slotIndex: slotIndex, scoreGained: scoreGained));

        final cleared = <({int row, int col})>[];
        final transmuted =
            <({int row, int col, int fromFunc, int toFunc})>[];
        for (final oe in result.obstacleEvents) {
          if (oe.type == 'cleared') {
            cleared.add((row: oe.row, col: oe.col));
          } else if (oe.type == 'transmuted') {
            transmuted.add((
              row: oe.row,
              col: oe.col,
              fromFunc: oe.fromFunc ?? 0,
              toFunc: oe.toFunc ?? 0,
            ));
          }
        }
        eventBus.fire(ObstaclesUpdatedEvent(
          remaining: result.obstaclesRemaining,
          cleared: cleared.isNotEmpty ? cleared : null,
          transmuted: transmuted.isNotEmpty ? transmuted : null,
        ));
      }

      if (result.appliedModifiers.isNotEmpty) {
        final cardIds = result.appliedModifiers
            .map((m) => m.cardId)
            .toSet()
            .toList();
        eventBus.fire(CardProcEvent(cardIds: cardIds));
      }

      // Refresh inventory counts after activation.
      await loadMegaInventory();
    } catch (e) {
      debugLogger.logError(
        'Campaign mega activation error: $e',
        matchId: currentAttemptId,
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
    final currentAttemptId = attemptId;
    if (currentAttemptId == null) return;

    inputHandler.state = InputState.animating;

    if (_currentBoard != null) {
      debugLogger.logMoveAttempt(
        fromRow,
        fromCol,
        toRow,
        toCol,
        _currentBoard!,
        matchId: currentAttemptId,
      );
    }

    // Optimistic swap animation.
    await boardLayer.animateSwap(fromRow, fromCol, toRow, toCol);

    try {
      final request = MoveRequest(
        fromRow: fromRow,
        fromCol: fromCol,
        toRow: toRow,
        toCol: toCol,
        timestampMs: DateTime.now().millisecondsSinceEpoch,
      );

      debugLogger.logApiRequest(
        '/campaign/$currentAttemptId/move',
        'POST',
        matchId: currentAttemptId,
        body: {
          'from': [fromRow, fromCol],
          'to': [toRow, toCol],
        },
      );

      final response = await trackApiCall(
        () => apiClient.submitCampaignMove(currentAttemptId, request),
      );

      if (!response.success || response.data == null) {
        debugLogger.logApiResponse(
          '/campaign/$currentAttemptId/move',
          false,
          matchId: currentAttemptId,
          error: 'success=${response.success}, data=null',
        );
        // Rubber-band.
        await boardLayer.animateSwap(toRow, toCol, fromRow, fromCol);
        inputHandler.onAnimationComplete();
        return;
      }

      final result = response.data!;

      debugLogger.logMoveResponse(
        valid: result.valid,
        scoreGained: result.scoreGained,
        matchesFound: result.cascadeSteps.length,
        cascades: result.cascadeSteps.length,
        movesRemaining: result.movesRemaining,
        newBoard: result.newBoard?.cells,
        matchId: currentAttemptId,
      );

      if (!result.valid) {
        // Invalid move — rubber-band.
        await boardLayer.animateSwap(toRow, toCol, fromRow, fromCol);
        inputHandler.onAnimationComplete();
        return;
      }

      // Valid move — play cascade animation and sync board.
      final oldBoard = _currentBoard;
      final board = result.newBoard;
      final scoreGained = result.scoreGained;

      // Detect win early — fire events BEFORE cascade so overlay shows
      // immediately while animations continue in the background.
      final isWin =
          result.status == 'won' || result.obstaclesRemaining == 0;
      if (isWin) {
        if (scoreGained > 0) {
          _cumulativeScore += scoreGained;
        }
        eventBus.fire(
          ScoreUpdatedEvent(
              newScore: _cumulativeScore, delta: scoreGained),
        );
        eventBus.fire(
            MovesUpdatedEvent(movesRemaining: result.movesRemaining));

        final cleared = <({int row, int col})>[];
        final transmuted =
            <({int row, int col, int fromFunc, int toFunc})>[];
        for (final oe in result.obstacleEvents) {
          if (oe.type == 'cleared') {
            cleared.add((row: oe.row, col: oe.col));
          } else if (oe.type == 'transmuted') {
            transmuted.add((
              row: oe.row,
              col: oe.col,
              fromFunc: oe.fromFunc ?? 0,
              toFunc: oe.toFunc ?? 0,
            ));
          }
        }
        eventBus.fire(ObstaclesUpdatedEvent(
          remaining: 0,
          cleared: cleared.isNotEmpty ? cleared : null,
          transmuted: transmuted.isNotEmpty ? transmuted : null,
        ));

        audioEngine?.stopMusic();
        cancelPeriodicShuffleTimers();
      }

      if (oldBoard != null && board != null) {
        final newBoard = board.cells;
        final newFunctions = board.functions;

        if (result.cascadeSteps.isNotEmpty) {
          try {
            await animationSequencer.playCascadeSteps(
              result.cascadeSteps,
              newBoard,
              newFunctions,
            );
          } catch (e) {
            debugLogger.logError(
              'Campaign animation error, forcing board sync: $e',
              matchId: currentAttemptId,
            );
          }
        }

        // Always sync to server board state.
        boardLayer.syncToBoard(newBoard, newFunctions);
        _currentBoard = newBoard.map((row) => List<int>.from(row)).toList();

        debugLogger.logBoardSync(
          'after_campaign_move',
          newBoard,
          matchId: currentAttemptId,
        );
      }

      // Fire events only if not a win (already fired above for wins).
      if (!isWin) {
        if (scoreGained > 0) {
          _cumulativeScore += scoreGained;
        }
        eventBus.fire(
          ScoreUpdatedEvent(
              newScore: _cumulativeScore, delta: scoreGained),
        );
        eventBus.fire(
            MovesUpdatedEvent(movesRemaining: result.movesRemaining));

        final cleared = <({int row, int col})>[];
        final transmuted =
            <({int row, int col, int fromFunc, int toFunc})>[];
        for (final oe in result.obstacleEvents) {
          if (oe.type == 'cleared') {
            cleared.add((row: oe.row, col: oe.col));
          } else if (oe.type == 'transmuted') {
            transmuted.add((
              row: oe.row,
              col: oe.col,
              fromFunc: oe.fromFunc ?? 0,
              toFunc: oe.toFunc ?? 0,
            ));
          }
        }
        eventBus.fire(ObstaclesUpdatedEvent(
          remaining: result.obstaclesRemaining,
          cleared: cleared.isNotEmpty ? cleared : null,
          transmuted: transmuted.isNotEmpty ? transmuted : null,
        ));

        if (result.cascadeSteps.isNotEmpty) {
          eventBus.fire(ChainCompletedEvent(
            chainLength: result.cascadeSteps.length,
            totalScore: scoreGained,
          ));
        }

        if (result.status == 'lost' ||
            (result.movesRemaining == 0 && result.obstaclesRemaining > 0)) {
          audioEngine?.stopMusic();
          cancelPeriodicShuffleTimers();
        }
      }

      if (result.appliedModifiers.isNotEmpty) {
        final cardIds = result.appliedModifiers
            .map((m) => m.cardId)
            .toSet()
            .toList();
        eventBus.fire(CardProcEvent(cardIds: cardIds));
      }
    } catch (e) {
      debugLogger.logError(
        'Campaign move error: $e',
        matchId: currentAttemptId,
      );
      // Rubber-band on error.
      await boardLayer.animateSwap(toRow, toCol, fromRow, fromCol);
    }

    inputHandler.onAnimationComplete();
  }
}
