/// Animated score count-up — counts from 0 to final score over 800ms.
///
/// Color adapts to match outcome: gold (win), gray-red (loss), white (draw).
library;

import 'package:flutter/material.dart';

import '../../config/animation_timings.dart';
import '../../models/view_state.dart';
import '../../theme/chroma_theme.dart';

class ScoreRevealWidget extends StatefulWidget {
  const ScoreRevealWidget({
    super.key,
    required this.label,
    required this.targetScore,
    required this.outcome,
    this.delay = Duration.zero,
  });

  final String label;
  final int targetScore;
  final MatchOutcome? outcome;
  final Duration delay;

  @override
  State<ScoreRevealWidget> createState() => _ScoreRevealWidgetState();
}

class _ScoreRevealWidgetState extends State<ScoreRevealWidget>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _countAnimation;
  bool _started = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: kScoreCountUpDuration,
    );
    _countAnimation = CurvedAnimation(
      parent: _controller,
      curve: Curves.easeOut,
    );

    if (widget.delay == Duration.zero) {
      _started = true;
      _controller.forward();
    } else {
      Future.delayed(widget.delay, () {
        if (mounted) {
          setState(() => _started = true);
          _controller.forward();
        }
      });
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Color get _scoreColor => switch (widget.outcome) {
    MatchOutcome.win => Colors.amber,
    MatchOutcome.loss => Colors.red.shade300,
    MatchOutcome.draw => ChromaColors.textSecondary,
    null => ChromaColors.textSecondary,
  };

  @override
  Widget build(BuildContext context) {
    if (!_started) {
      return Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(widget.label, style: ChromaText.labelSmall),
          const SizedBox(height: 4),
          Text(
            '0',
            style: TextStyle(
              color: _scoreColor,
              fontSize: 36,
              fontWeight: FontWeight.bold,
            ),
          ),
        ],
      );
    }

    return AnimatedBuilder(
      animation: _countAnimation,
      builder: (context, child) {
        final displayScore = (_countAnimation.value * widget.targetScore)
            .round();
        return Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(widget.label, style: ChromaText.labelSmall),
            const SizedBox(height: 4),
            Text(
              '$displayScore',
              style: TextStyle(
                color: _scoreColor,
                fontSize: 36,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        );
      },
    );
  }
}
