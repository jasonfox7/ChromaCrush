/// Standalone FlameGame for the tutorial screen.
///
/// Creates the same visual components as [ChromaCrushGame] (BoardLayer,
/// ParticleLayer, BackgroundLayer, AnimationSequencer) but skips all
/// API, session, card, mega, and bot systems.
///
/// Moves are constrained to the scripted tutorial sequence. Wrong moves
/// rubber-band; correct moves play full cascade animations from the
/// pre-enriched tutorial JSON.
library;

import 'package:flame/game.dart';
import 'package:flutter/painting.dart';

import '../config/visual_theme_service.dart';
import '../extensions/grid_math.dart';
import '../models/tutorial_script.dart';
import '../services/audio_engine.dart';
import '../services/event_bus.dart';
import '../services/haptics_engine.dart';
import 'animation_sequencer.dart';
import 'background_layer.dart';
import 'board_layer.dart';
import 'cascade_animator.dart';
import 'gem_shader_library.dart';
import 'input_handler.dart';
import 'particle_layer.dart';

class TutorialGame extends FlameGame {
  TutorialGame({
    required this.visualTheme,
    this.audioEngine,
    this.hapticsEngine,
  });

  final VisualThemeBase visualTheme;
  final AudioEngineBase? audioEngine;
  final HapticsEngineBase? hapticsEngine;

  late final BoardLayout layout;
  late final BackgroundLayer backgroundLayer;
  late final BoardLayer boardLayer;
  late final InputHandler inputHandler;
  late final AnimationSequencer animationSequencer;
  late final CascadeAnimator cascadeAnimator;
  late final ParticleLayer particleLayer;

  /// Isolated event bus — tutorial events don't leak into the main app.
  final EventBus _eventBus = EventBus();

  TutorialScript? _script;
  int _currentStep = 0;

  /// Whether onLoad has completed.
  bool isReady = false;

  /// Callback fired once when the game finishes loading.
  void Function()? onReady;

  /// Callback when a step is completed (step index after completion).
  void Function(int stepIndex)? onStepAdvanced;

  /// Callback when all tutorial steps are done.
  void Function()? onTutorialComplete;

  /// Callback when the final step's cascade begins (for "Well done!!" flash).
  void Function()? onFinalCascadeStarted;

  /// Callback when a wrong move is attempted.
  void Function()? onWrongMove;

  @override
  Color backgroundColor() => const Color(0xFF0D0D14);

  @override
  Future<void> onLoad() async {
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

    particleLayer = ParticleLayer(theme: visualTheme, layout: layout);
    particleLayer.position.setValues(layout.boardLeft, layout.boardTop);
    add(particleLayer);

    inputHandler = InputHandler(onSwap: _onSwapCommitted);
    inputHandler.onSelectionChanged = _onSelectionChanged;

    cascadeAnimator = CascadeAnimator(
      boardContainer: boardLayer,
      gameRef: this,
    );

    animationSequencer = AnimationSequencer(
      boardLayer: boardLayer,
      eventBus: _eventBus,
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

  /// Load the tutorial script and display the first board.
  void loadScript(TutorialScript script) {
    _script = script;
    _currentStep = 0;
    boardLayer.loadBoard(script.initialBoard);
  }

  /// Load the board for the current step (board_before).
  void loadCurrentStepBoard() {
    final script = _script;
    if (script == null) return;
    if (_currentStep >= script.steps.length) return;
    boardLayer.loadBoard(script.steps[_currentStep].boardBefore);
  }

  /// The current step index.
  int get currentStep => _currentStep;

  /// Whether all steps are done.
  bool get isComplete =>
      _script != null && _currentStep >= _script!.steps.length;

  /// Block/unblock input (used by coach overlay).
  void setInputEnabled(bool enabled) {
    if (enabled) {
      if (inputHandler.state == InputState.animating) {
        inputHandler.onAnimationComplete();
      }
    } else {
      inputHandler.state = InputState.animating;
    }
  }

  // ---------------------------------------------------------------------------
  // Input handling
  // ---------------------------------------------------------------------------

  void _onGemTapped(int row, int col) {
    inputHandler.onGemTapped(row, col);
  }

  void _onSelectionChanged(int? row, int? col) {
    for (var r = 0; r < 8; r++) {
      for (var c = 0; c < 8; c++) {
        boardLayer.gemAt(r, c)?.setSelected(false);
      }
    }
    if (row != null && col != null) {
      boardLayer.gemAt(row, col)?.setSelected(true);
    }
  }

  Future<void> _onSwapCommitted(
    int fromRow,
    int fromCol,
    int toRow,
    int toCol,
  ) async {
    final script = _script;
    if (script == null) return;
    if (_currentStep >= script.steps.length) return;

    final step = script.steps[_currentStep];
    inputHandler.state = InputState.animating;

    // Check if this matches the scripted move (either direction).
    final isCorrect = _matchesScriptedMove(
      fromRow,
      fromCol,
      toRow,
      toCol,
      step,
    );

    if (!isCorrect) {
      // Wrong move — rubber-band.
      await boardLayer.animateSwap(fromRow, fromCol, toRow, toCol);
      await boardLayer.animateSwap(toRow, toCol, fromRow, fromCol);
      inputHandler.onAnimationComplete();
      onWrongMove?.call();
      return;
    }

    // Correct move — optimistic swap + full cascade.
    await boardLayer.animateSwap(fromRow, fromCol, toRow, toCol);

    // Flash "Well done!!" as the final cascade begins.
    if (_currentStep == script.steps.length - 1) {
      onFinalCascadeStarted?.call();
    }

    final oldBoard =
        step.boardBefore.cells.map((row) => List<int>.from(row)).toList();

    try {
      await animationSequencer.playMoveResult(
        oldBoard: oldBoard,
        result: step.moveResult,
        fromRow: fromRow,
        fromCol: fromCol,
        toRow: toRow,
        toCol: toCol,
      );
    } catch (_) {
      // Animation error — force sync.
    }

    // Sync to the final board state for this step.
    boardLayer.syncToBoard(step.boardAfter.cells, step.boardAfter.functions);

    // Advance to next step.
    _currentStep++;

    if (_currentStep >= script.steps.length) {
      onTutorialComplete?.call();
    } else {
      onStepAdvanced?.call(_currentStep);
    }

    inputHandler.onAnimationComplete();
  }

  bool _matchesScriptedMove(
    int fromRow,
    int fromCol,
    int toRow,
    int toCol,
    TutorialStep step,
  ) {
    // Forward match.
    if (fromRow == step.fromRow &&
        fromCol == step.fromCol &&
        toRow == step.toRow &&
        toCol == step.toCol) {
      return true;
    }
    // Reverse match (swap direction doesn't matter).
    if (fromRow == step.toRow &&
        fromCol == step.toCol &&
        toRow == step.fromRow &&
        toCol == step.fromCol) {
      return true;
    }
    return false;
  }
}
