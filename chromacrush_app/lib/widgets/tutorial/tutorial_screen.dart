/// Tutorial screen — standalone, zero API calls.
///
/// Loads the enriched tutorial JSON from assets, creates a [TutorialGame]
/// with full cascade animations, and overlays a [CoachOverlay] between steps.
///
/// State machine: loading → showingCoach → waitingForInput → animating → showingCoach → ... → complete.
library;

import 'dart:convert';

import 'package:flame/game.dart';
import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter/services.dart' show rootBundle;
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../config/visual_theme_service.dart';
import '../../extensions/grid_math.dart';
import '../../game/tutorial_game.dart';
import '../../models/tutorial_script.dart';
import '../../services/audio_engine.dart';
import '../../services/haptics_engine.dart';
import '../../theme/chroma_theme.dart';
import '../../theme/glass_panel.dart';
import 'coach_overlay.dart';

class TutorialScreen extends StatefulWidget {
  const TutorialScreen({super.key});

  @override
  State<TutorialScreen> createState() => _TutorialScreenState();
}

class _TutorialScreenState extends State<TutorialScreen> {
  late final TutorialGame _game;
  TutorialScript? _script;
  bool _isLoading = true;
  bool _showingCoach = false;
  bool _showWellDone = false;
  bool _tutorialComplete = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    final visualTheme = context.read<VisualThemeBase>();
    final audioEngine = context.read<AudioEngineBase>();
    final hapticsEngine = context.read<HapticsEngineBase>();

    _game = TutorialGame(
      visualTheme: visualTheme,
      audioEngine: audioEngine,
      hapticsEngine: hapticsEngine,
    );

    _game.onStepAdvanced = _onStepAdvanced;
    _game.onTutorialComplete = _onTutorialComplete;
    _game.onFinalCascadeStarted = _onFinalCascadeStarted;

    _loadScript();
  }

  Future<void> _loadScript() async {
    try {
      final jsonString = await rootBundle.loadString(
        'assets/config/tutorial_script.json',
      );
      final json = jsonDecode(jsonString) as Map<String, dynamic>;
      final script = TutorialScript.fromJson(json);

      setState(() {
        _script = script;
        _isLoading = false;
      });

      // Wait for Flame game to be ready, then load the board.
      if (_game.isReady) {
        _startTutorial(script);
      } else {
        _game.onReady = () => _startTutorial(script);
      }
    } catch (e) {
      setState(() {
        _isLoading = false;
        _error = 'Failed to load tutorial: $e';
      });
    }
  }

  void _startTutorial(TutorialScript script) {
    _game.loadScript(script);
    // Block input until coach is dismissed.
    _game.setInputEnabled(false);
    if (mounted) {
      setState(() => _showingCoach = true);
    }
  }

  void _onCoachDismissed() {
    setState(() => _showingCoach = false);
    // Unblock input so player can make their move.
    _game.setInputEnabled(true);
  }

  void _onStepAdvanced(int stepIndex) {
    // Block input and show next coach.
    _game.setInputEnabled(false);
    if (mounted) {
      setState(() => _showingCoach = true);
    }
  }

  void _onFinalCascadeStarted() {
    if (mounted) {
      setState(() => _showWellDone = true);
    }
  }

  void _onTutorialComplete() {
    if (mounted) {
      setState(() {
        _showingCoach = false;
        _tutorialComplete = true;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: ChromaColors.bgBase,
      body: Stack(
        children: [
          // Flame game fills the screen.
          GameWidget(game: _game),

          // Loading overlay.
          if (_isLoading) const _LoadingOverlay(),

          // Error overlay.
          if (_error != null) _ErrorOverlay(error: _error!),

          // Coach overlay between steps.
          if (_showingCoach && _script != null && !_game.isComplete)
            Builder(
              builder: (context) {
                final step = _script!.steps[_game.currentStep];
                final screen = MediaQuery.sizeOf(context);
                final layout = BoardLayout(screen.width, screen.height);
                return CoachOverlay(
                  fromRow: step.fromRow,
                  fromCol: step.fromCol,
                  toRow: step.toRow,
                  toCol: step.toCol,
                  coachText: step.coachText,
                  layout: layout,
                  onDismiss: _onCoachDismissed,
                  stepNumber: step.step,
                  totalSteps: _script!.steps.length,
                );
              },
            ),

          // "Well done!!" flash during final cascade.
          if (_showWellDone && !_tutorialComplete) const _WellDoneFlash(),

          // Completion overlay.
          if (_tutorialComplete) _CompletionOverlay(onBack: () => context.go('/')),

          // Step indicator (top center).
          if (_script != null && !_isLoading && !_tutorialComplete)
            SafeArea(
              child: Align(
                alignment: Alignment.topCenter,
                child: Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 16,
                      vertical: 6,
                    ),
                    decoration: BoxDecoration(
                      color: Colors.black.withValues(alpha: 0.5),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: Text(
                      'Step ${_game.currentStep + 1} of ${_script!.steps.length}',
                      style: ChromaText.bodyMedium.copyWith(
                        color: ChromaColors.textPrimary,
                      ),
                    ),
                  ),
                ),
              ),
            ),

          // Back button (top-left).
          SafeArea(
            child: Align(
              alignment: Alignment.topLeft,
              child: Padding(
                padding: const EdgeInsets.only(top: 8, left: 8),
                child: GestureDetector(
                  onTap: () => context.go('/'),
                  child: Container(
                    width: 36,
                    height: 36,
                    decoration: BoxDecoration(
                      color: Colors.black.withValues(alpha: 0.4),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(
                      CupertinoIcons.back,
                      color: Colors.white54,
                      size: 20,
                    ),
                  ),
                ),
              ),
            ),
          ),
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
              'Loading tutorial...',
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

class _ErrorOverlay extends StatelessWidget {
  const _ErrorOverlay({required this.error});

  final String error;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: ChromaColors.bgBase.withValues(alpha: 0.87),
      child: Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Text(
            error,
            style: ChromaText.bodyMedium.copyWith(color: Colors.redAccent),
            textAlign: TextAlign.center,
          ),
        ),
      ),
    );
  }
}

class _WellDoneFlash extends StatefulWidget {
  const _WellDoneFlash();

  @override
  State<_WellDoneFlash> createState() => _WellDoneFlashState();
}

class _WellDoneFlashState extends State<_WellDoneFlash>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _scale;
  late final Animation<double> _opacity;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..forward();

    _scale = TweenSequence<double>([
      TweenSequenceItem(
        tween: Tween(begin: 0.3, end: 1.1)
            .chain(CurveTween(curve: Curves.easeOutBack)),
        weight: 40,
      ),
      TweenSequenceItem(
        tween: Tween(begin: 1.1, end: 1.0)
            .chain(CurveTween(curve: Curves.easeInOut)),
        weight: 20,
      ),
      TweenSequenceItem(
        tween: ConstantTween(1.0),
        weight: 40,
      ),
    ]).animate(_controller);

    _opacity = TweenSequence<double>([
      TweenSequenceItem(
        tween: Tween(begin: 0.0, end: 1.0)
            .chain(CurveTween(curve: Curves.easeOut)),
        weight: 20,
      ),
      TweenSequenceItem(
        tween: ConstantTween(1.0),
        weight: 50,
      ),
      TweenSequenceItem(
        tween: Tween(begin: 1.0, end: 0.0)
            .chain(CurveTween(curve: Curves.easeIn)),
        weight: 30,
      ),
    ]).animate(_controller);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedBuilder(
      animation: _controller,
      builder: (context, child) {
        return IgnorePointer(
          child: Center(
            child: Opacity(
              opacity: _opacity.value,
              child: Transform.scale(
                scale: _scale.value,
                child: Text(
                  'Well done!!',
                  style: ChromaText.displayLarge.copyWith(
                    color: ChromaColors.accentGlow,
                    fontSize: 48,
                    fontWeight: FontWeight.w900,
                    shadows: [
                      const Shadow(
                        color: Colors.black87,
                        blurRadius: 16,
                      ),
                      Shadow(
                        color: ChromaColors.accentGlow.withValues(alpha: 0.6),
                        blurRadius: 32,
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        );
      },
    );
  }
}

class _CompletionOverlay extends StatelessWidget {
  const _CompletionOverlay({required this.onBack});

  final VoidCallback onBack;

  @override
  Widget build(BuildContext context) {
    return Container(
      color: Colors.black.withValues(alpha: 0.7),
      child: Center(
        child: GlassPanel(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'Tutorial Complete!',
                style: ChromaText.headlineMedium.copyWith(
                  color: ChromaColors.accentGlow,
                ),
              ),
              const SizedBox(height: 16),
              Text(
                'You\'ve learned the basics of ChromaCrush.\nNow go crush it!',
                style: ChromaText.bodyMedium.copyWith(
                  color: ChromaColors.textPrimary,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 24),
              CupertinoButton.filled(
                onPressed: onBack,
                child: const Text('Back to Menu'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
