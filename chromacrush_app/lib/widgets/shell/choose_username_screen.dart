/// Username picker screen — shown after first Apple Sign-In or from settings.
///
/// Debounced server-side availability checking, client-side format validation,
/// and accent-styled confirm button. Reused for both initial pick and later changes.
library;

import 'dart:async';

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../models/backend_contract.dart';
import '../../services/api_client.dart';
import '../../services/session_manager.dart';
import '../../theme/chroma_theme.dart';
import '../../theme/glass_panel.dart';

class ChooseUsernameScreen extends StatefulWidget {
  const ChooseUsernameScreen({super.key});

  @override
  State<ChooseUsernameScreen> createState() => _ChooseUsernameScreenState();
}

class _ChooseUsernameScreenState extends State<ChooseUsernameScreen> {
  final _controller = TextEditingController();
  final _focusNode = FocusNode();

  Timer? _debounce;
  bool _checking = false;
  bool? _available;
  String? _error;
  bool _submitting = false;

  /// Regex matching the backend validation pattern.
  static final _usernamePattern = RegExp(r'^[a-zA-Z0-9_]+$');

  @override
  void initState() {
    super.initState();
    // Pre-fill with current username when changing from settings.
    final session = context.read<SessionManager>();
    if (session.player != null) {
      _controller.text = session.player!.username;
    }
    _controller.addListener(_onChanged);
  }

  @override
  void dispose() {
    _debounce?.cancel();
    _controller.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _onChanged() {
    final text = _controller.text.trim();

    // Reset state on every keystroke.
    setState(() {
      _available = null;
      _error = null;
      _checking = false;
    });

    _debounce?.cancel();

    if (text.isEmpty) return;

    // Client-side pre-validation.
    final clientError = _validateLocally(text);
    if (clientError != null) {
      setState(() => _error = clientError);
      return;
    }

    // Skip server check if it matches current username.
    final session = context.read<SessionManager>();
    if (session.player != null && text == session.player!.username) {
      setState(() {
        _available = true;
        _error = null;
      });
      return;
    }

    // Debounce 500ms before server check.
    setState(() => _checking = true);
    _debounce = Timer(
      const Duration(milliseconds: 500),
      () => _checkAvailability(text),
    );
  }

  String? _validateLocally(String username) {
    if (username.length < 3) return 'Must be at least 3 characters';
    if (username.length > 32) return 'Must be at most 32 characters';
    if (!_usernamePattern.hasMatch(username)) {
      return 'Letters, numbers, and underscores only';
    }
    return null;
  }

  Future<void> _checkAvailability(String username) async {
    if (!mounted) return;

    final api = context.read<ApiClientBase>();
    try {
      final result = await api.checkUsername(username);
      if (!mounted || _controller.text.trim() != username) return;

      setState(() {
        _checking = false;
        if (result.data != null) {
          _available = result.data!.available;
          _error = result.data!.error;
        }
      });
    } catch (_) {
      if (!mounted || _controller.text.trim() != username) return;
      setState(() {
        _checking = false;
        _error = 'Could not check availability';
      });
    }
  }

  Future<void> _confirm() async {
    final username = _controller.text.trim();
    if (username.isEmpty || _available != true || _submitting) return;

    setState(() => _submitting = true);

    final api = context.read<ApiClientBase>();
    final session = context.read<SessionManager>();

    try {
      final result = await api.updateProfile(
        PlayerUpdateRequest(username: username),
      );
      if (!mounted) return;

      if (result.data != null) {
        session.updateUsername(result.data!.username);
        context.go('/');
      } else {
        setState(() {
          _submitting = false;
          _error = 'Failed to update username';
        });
      }
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _submitting = false;
        _error = 'Username already taken';
      });
    }
  }

  void _skip() {
    context.go('/');
  }

  @override
  Widget build(BuildContext context) {
    final canConfirm = _available == true && !_submitting;

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: ChromaGradients.screen),
        child: SafeArea(
          child: Center(
            child: SingleChildScrollView(
              padding: const EdgeInsets.symmetric(horizontal: 32),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    'CHOOSE YOUR NAME',
                    style: ChromaText.headlineMedium.copyWith(letterSpacing: 3),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'Pick a unique username for the leaderboard',
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.5),
                      fontSize: 14,
                    ),
                    textAlign: TextAlign.center,
                  ),

                  const SizedBox(height: 32),

                  // Input panel.
                  GlassPanel(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 20,
                      vertical: 24,
                    ),
                    child: Column(
                      children: [
                        TextField(
                          controller: _controller,
                          focusNode: _focusNode,
                          autofocus: true,
                          maxLength: 32,
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 18,
                          ),
                          decoration: InputDecoration(
                            hintText: 'Username',
                            hintStyle: TextStyle(
                              color: Colors.white.withValues(alpha: 0.3),
                            ),
                            counterText: '',
                            enabledBorder: UnderlineInputBorder(
                              borderSide: BorderSide(
                                color: Colors.white.withValues(alpha: 0.2),
                              ),
                            ),
                            focusedBorder: const UnderlineInputBorder(
                              borderSide: BorderSide(
                                color: ChromaColors.accent,
                              ),
                            ),
                            suffixIcon: _buildSuffixIcon(),
                          ),
                          textInputAction: TextInputAction.done,
                          onSubmitted: (_) {
                            if (canConfirm) _confirm();
                          },
                        ),

                        const SizedBox(height: 12),

                        // Status message.
                        SizedBox(height: 20, child: _buildStatusMessage()),

                        const SizedBox(height: 20),

                        // Confirm button.
                        GestureDetector(
                          onTap: canConfirm ? _confirm : null,
                          child: AnimatedOpacity(
                            opacity: canConfirm ? 1.0 : 0.4,
                            duration: const Duration(milliseconds: 200),
                            child: Container(
                              width: double.infinity,
                              padding: const EdgeInsets.symmetric(vertical: 14),
                              decoration: BoxDecoration(
                                gradient: ChromaGradients.accent,
                                borderRadius: BorderRadius.circular(22),
                                boxShadow: canConfirm
                                    ? [
                                        BoxShadow(
                                          color: ChromaColors.accent.withValues(
                                            alpha: 0.4,
                                          ),
                                          blurRadius: 16,
                                          spreadRadius: 1,
                                        ),
                                      ]
                                    : null,
                              ),
                              alignment: Alignment.center,
                              child: _submitting
                                  ? const SizedBox(
                                      width: 20,
                                      height: 20,
                                      child: CircularProgressIndicator(
                                        color: Colors.white,
                                        strokeWidth: 2.5,
                                      ),
                                    )
                                  : const Text(
                                      'CONFIRM',
                                      style: TextStyle(
                                        color: Colors.white,
                                        fontSize: 16,
                                        fontWeight: FontWeight.bold,
                                        letterSpacing: 4,
                                      ),
                                    ),
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),

                  const SizedBox(height: 20),

                  // Skip option.
                  GestureDetector(
                    onTap: _skip,
                    child: Text(
                      'SKIP FOR NOW',
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.35),
                        fontSize: 12,
                        fontWeight: FontWeight.w500,
                        letterSpacing: 2,
                      ),
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

  Widget? _buildSuffixIcon() {
    if (_checking) {
      return const SizedBox(
        width: 20,
        height: 20,
        child: Padding(
          padding: EdgeInsets.all(2),
          child: CircularProgressIndicator(
            strokeWidth: 2,
            color: ChromaColors.accent,
          ),
        ),
      );
    }
    if (_available == true) {
      return const Icon(Icons.check_circle, color: Colors.green, size: 22);
    }
    if (_error != null && _controller.text.trim().isNotEmpty) {
      return Icon(Icons.cancel, color: Colors.red.shade300, size: 22);
    }
    return null;
  }

  Widget _buildStatusMessage() {
    if (_checking) {
      return Text(
        'Checking availability...',
        style: TextStyle(
          color: Colors.white.withValues(alpha: 0.4),
          fontSize: 12,
        ),
      );
    }
    if (_available == true) {
      return const Text(
        'Available!',
        style: TextStyle(color: Colors.green, fontSize: 12),
      );
    }
    if (_error != null) {
      return Text(
        _error!,
        style: TextStyle(color: Colors.red.shade300, fontSize: 12),
      );
    }
    return const SizedBox.shrink();
  }
}
