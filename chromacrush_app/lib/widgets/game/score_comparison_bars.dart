/// Dual score comparison bars flanking the game board.
///
/// Left bar (player): real-time score updates via EventBus.
/// Right bar (bot): delayed jumps for psychological tension.
/// Both bars fill from bottom to top as a fraction of a dynamic max score.
library;

import 'dart:async';
import 'dart:math';

import 'package:flutter/material.dart';

import '../../config/animation_timings.dart';
import '../../config/game_config.dart';
import '../../extensions/grid_math.dart' show BoardLayout;
import '../../services/bot_player_service.dart';
import '../../services/event_bus.dart';
import '../../view_models/match_view_model.dart';

class ScoreComparisonBars extends StatefulWidget {
  const ScoreComparisonBars({
    super.key,
    required this.eventBus,
    required this.matchViewModel,
    this.botPlayerService,
  });

  final EventBus eventBus;
  final MatchViewModel matchViewModel;
  final BotPlayerServiceBase? botPlayerService;

  @override
  State<ScoreComparisonBars> createState() => _ScoreComparisonBarsState();
}

class _ScoreComparisonBarsState extends State<ScoreComparisonBars> {
  final _random = Random();

  int _playerScore = 0;
  int _displayedBotScore = 0;
  int _dynamicMax = kScoreInitialMax;

  Timer? _botRevealTimer;
  StreamSubscription<ScoreUpdatedEvent>? _scoreSub;
  StreamSubscription<BotScoreUpdatedEvent>? _botScoreSub;

  // Flash state for bot bar.
  bool _botFlash = false;

  @override
  void initState() {
    super.initState();
    _playerScore = widget.matchViewModel.myScore;

    _scoreSub = widget.eventBus.on<ScoreUpdatedEvent>().listen((event) {
      setState(() {
        _playerScore = event.newScore;
        _maybeExpandMax();
      });
    });

    _botScoreSub = widget.eventBus.on<BotScoreUpdatedEvent>().listen((_) {
      // Don't update displayed score yet — wait for reveal timer.
    });

    _scheduleBotReveal();
  }

  @override
  void dispose() {
    _scoreSub?.cancel();
    _botScoreSub?.cancel();
    _botRevealTimer?.cancel();
    super.dispose();
  }

  void _scheduleBotReveal() {
    final delayMs =
        kBotRevealDelayMinMs + _random.nextInt(kBotRevealDelayRangeMs); // 3-5s
    _botRevealTimer = Timer(Duration(milliseconds: delayMs), _revealBotScore);
  }

  void _revealBotScore() {
    if (!mounted) return;

    final actualBotScore = widget.botPlayerService?.currentScore ?? 0;
    final gap = actualBotScore - _displayedBotScore;

    if (gap > 0) {
      // Reveal 50-100% of the gap.
      final revealFraction = 0.5 + _random.nextDouble() * 0.5;
      final reveal = (gap * revealFraction).round().clamp(1, gap);

      setState(() {
        _displayedBotScore += reveal;
        _botFlash = true;
        _maybeExpandMax();
      });

      // Clear flash after 150ms.
      Future.delayed(const Duration(milliseconds: 150), () {
        if (mounted) setState(() => _botFlash = false);
      });
    }

    _scheduleBotReveal();
  }

  void _maybeExpandMax() {
    final maxScore = max(_playerScore, _displayedBotScore);
    while (maxScore > _dynamicMax * kScoreExpansionThreshold) {
      _dynamicMax *= 2;
    }
  }

  /// Format a score value for scale ticks (e.g. 5000 → "5K", 1500000 → "1.5M").
  static String _formatValue(int value) {
    if (value >= 1000000) return '${(value / 1000000).toStringAsFixed(1)}M';
    if (value >= 1000) return '${value ~/ 1000}K';
    return '$value';
  }

  /// Generate "nice" scale tick values from 0 to [maxVal].
  /// Returns values like 0, 5K, 10K or 0, 10K, 20K depending on range.
  static List<int> _scaleTicks(int maxVal) {
    if (maxVal <= 0) return [0];
    // Pick a step that gives ~4-5 ticks.
    const steps = [
      1000,
      2000,
      2500,
      5000,
      10000,
      20000,
      25000,
      50000,
      100000,
      200000,
      500000,
      1000000,
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
        final botFill = _dynamicMax > 0
            ? (_displayedBotScore / _dynamicMax).clamp(0.0, 1.0)
            : 0.0;

        final ticks = _scaleTicks(_dynamicMax);

        final leftBarX = boardLeft - barWidth - barGap;
        final rightBarX = boardLeft + layout.boardExtent + barGap;

        return Stack(
          children: [
            // Left scale ticks (player side, labels to the left of the bar).
            for (final tick in ticks)
              if (tick > 0)
                Positioned(
                  right: screenWidth - leftBarX + 2,
                  top:
                      boardTop +
                      barHeight -
                      (barHeight * tick / _dynamicMax) -
                      5,
                  child: _ScaleTick(
                    label: _formatValue(tick),
                    alignment: TextAlign.right,
                    color: const Color(0xFF00E5FF),
                  ),
                ),
            // Right scale ticks (bot side, labels to the right of the bar).
            for (final tick in ticks)
              if (tick > 0)
                Positioned(
                  left: rightBarX + barWidth + 2,
                  top:
                      boardTop +
                      barHeight -
                      (barHeight * tick / _dynamicMax) -
                      5,
                  child: _ScaleTick(
                    label: _formatValue(tick),
                    alignment: TextAlign.left,
                    color: const Color(0xFFFF6D00),
                  ),
                ),
            // Left bar — player score (real-time).
            Positioned(
              left: leftBarX,
              top: boardTop,
              child: _ScoreBar(
                width: barWidth,
                height: barHeight,
                fill: playerFill,
                gradient: const LinearGradient(
                  begin: Alignment.bottomCenter,
                  end: Alignment.topCenter,
                  colors: [Color(0xFF00897B), Color(0xFF00E5FF)],
                ),
                glowColor: const Color(0xFF00E5FF),
                flash: false,
              ),
            ),
            // Right bar — bot score (delayed jumps).
            Positioned(
              left: rightBarX,
              top: boardTop,
              child: _ScoreBar(
                width: barWidth,
                height: barHeight,
                fill: botFill,
                gradient: const LinearGradient(
                  begin: Alignment.bottomCenter,
                  end: Alignment.topCenter,
                  colors: [Color(0xFFFF6D00), Color(0xFFFF1744)],
                ),
                glowColor: const Color(0xFFFF6D00),
                flash: _botFlash,
              ),
            ),
          ],
        );
      },
    );
  }
}

class _ScaleTick extends StatelessWidget {
  const _ScaleTick({
    required this.label,
    required this.alignment,
    required this.color,
  });

  final String label;
  final TextAlign alignment;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Text(
      label,
      textAlign: alignment,
      style: TextStyle(
        color: color.withValues(alpha: 0.35),
        fontSize: 8,
        fontWeight: FontWeight.w700,
        letterSpacing: 0.5,
      ),
    );
  }
}

class _ScoreBar extends StatelessWidget {
  const _ScoreBar({
    required this.width,
    required this.height,
    required this.fill,
    required this.gradient,
    required this.glowColor,
    required this.flash,
  });

  final double width;
  final double height;
  final double fill;
  final LinearGradient gradient;
  final Color glowColor;
  final bool flash;

  @override
  Widget build(BuildContext context) {
    final fillHeight = height * fill;

    return SizedBox(
      width: width,
      height: height,
      child: Stack(
        alignment: Alignment.bottomCenter,
        children: [
          // Track background.
          Container(
            width: width,
            height: height,
            decoration: BoxDecoration(
              color: Colors.white.withValues(alpha: 0.06),
              borderRadius: BorderRadius.circular(7),
            ),
          ),
          // Filled portion.
          AnimatedContainer(
            duration: flash
                ? kScoreBarFlashFillDuration
                : kScoreBarNormalFillDuration,
            curve: flash ? Curves.elasticOut : Curves.easeOutCubic,
            width: width,
            height: fillHeight,
            decoration: BoxDecoration(
              gradient: gradient,
              borderRadius: BorderRadius.circular(7),
              boxShadow: [
                BoxShadow(
                  color: glowColor.withValues(alpha: 0.4),
                  blurRadius: 8,
                ),
              ],
            ),
          ),
          // Flash overlay.
          if (flash)
            AnimatedOpacity(
              opacity: flash ? 1.0 : 0.0,
              duration: const Duration(milliseconds: 150),
              child: Container(
                width: width,
                height: fillHeight,
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.6),
                  borderRadius: BorderRadius.circular(7),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
