/// Near-miss psychology text — frames narrow losses to trigger "one more try".
///
/// Animated text reveal with score differential prominently displayed.
library;

import 'package:flutter/material.dart';

import '../../config/animation_timings.dart';
import '../../theme/chroma_theme.dart';

class NearMissWidget extends StatefulWidget {
  const NearMissWidget({
    super.key,
    required this.scoreDifferential,
    this.delay = Duration.zero,
  });

  final int scoreDifferential;
  final Duration delay;

  @override
  State<NearMissWidget> createState() => _NearMissWidgetState();
}

class _NearMissWidgetState extends State<NearMissWidget>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  late final Animation<double> _fadeAnimation;
  late final Animation<Offset> _slideAnimation;
  bool _visible = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: kNearMissAnimDuration,
    );
    _fadeAnimation = CurvedAnimation(parent: _controller, curve: Curves.easeIn);
    _slideAnimation = Tween<Offset>(
      begin: const Offset(0, 0.2),
      end: Offset.zero,
    ).animate(CurvedAnimation(parent: _controller, curve: Curves.easeOutCubic));

    Future.delayed(widget.delay, () {
      if (mounted) {
        setState(() => _visible = true);
        _controller.forward();
      }
    });
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!_visible) return const SizedBox.shrink();

    return FadeTransition(
      opacity: _fadeAnimation,
      child: SlideTransition(
        position: _slideAnimation,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'You lost by ${widget.scoreDifferential} points',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: Colors.red.shade200,
                  fontSize: 20,
                  fontWeight: FontWeight.w700,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                'One more cascade would have changed everything.',
                textAlign: TextAlign.center,
                style: TextStyle(
                  color: ChromaColors.textTertiary,
                  fontSize: 14,
                  fontStyle: FontStyle.italic,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
