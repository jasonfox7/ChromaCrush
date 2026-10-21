/// Overlay shown when an API call takes too long (>3 seconds).
///
/// Subscribes to [ConnectionSlowEvent] / [ConnectionRestoredEvent] on the
/// [EventBus] and fades a dark scrim with "Reestablishing connection..." text.
/// Shared between PvP and Campaign game containers.
library;

import 'dart:async';

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

import '../../services/event_bus.dart';
import '../../theme/chroma_theme.dart';

class ConnectionOverlay extends StatefulWidget {
  const ConnectionOverlay({super.key, required this.eventBus});

  final EventBus eventBus;

  @override
  State<ConnectionOverlay> createState() => _ConnectionOverlayState();
}

class _ConnectionOverlayState extends State<ConnectionOverlay>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;
  StreamSubscription<ConnectionSlowEvent>? _slowSub;
  StreamSubscription<ConnectionRestoredEvent>? _restoredSub;
  bool _visible = false;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 300),
    );

    _slowSub = widget.eventBus.on<ConnectionSlowEvent>().listen((_) {
      if (!_visible) {
        _visible = true;
        _controller.forward();
        if (mounted) setState(() {});
      }
    });

    _restoredSub = widget.eventBus.on<ConnectionRestoredEvent>().listen((_) {
      if (_visible) {
        _controller.reverse().then((_) {
          _visible = false;
          if (mounted) setState(() {});
        });
      }
    });
  }

  @override
  void dispose() {
    _slowSub?.cancel();
    _restoredSub?.cancel();
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!_visible && !_controller.isAnimating) return const SizedBox.shrink();

    return FadeTransition(
      opacity: _controller,
      child: Container(
        color: Colors.black.withValues(alpha: 0.5),
        child: Center(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const CupertinoActivityIndicator(
                radius: 14,
                color: ChromaColors.accentGlow,
              ),
              const SizedBox(height: 16),
              Text(
                'Reestablishing connection...',
                style: ChromaText.bodyMedium.copyWith(
                  color: ChromaColors.textSecondary,
                  letterSpacing: 0.5,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
