/// Login screen — Apple Sign-In primary, dev login secondary.
///
/// Apple Sign-In handles both login and registration via native iOS sheet.
/// Backend auto-creates accounts for new Apple users (grants starter cards
/// + pool bot). Dev login (username/password) available as a toggle for
/// development on non-Apple platforms.
library;

import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:sign_in_with_apple/sign_in_with_apple.dart';

import '../../models/backend_contract.dart';
import '../../services/api_client.dart';
import '../../services/session_manager.dart';
import '../../theme/chroma_theme.dart';
import 'starfield_background.dart';

class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen>
    with SingleTickerProviderStateMixin {
  bool _loading = false;
  String? _error;
  bool _showDevLogin = false;

  final _usernameController = TextEditingController();
  final _passwordController = TextEditingController();
  final _usernameFocus = FocusNode();
  final _passwordFocus = FocusNode();

  late final AnimationController _pulseController;
  late final Animation<double> _pulseAnimation;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2500),
    )..repeat(reverse: true);
    _pulseAnimation = Tween<double>(begin: 0.15, end: 0.45).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
    // Try to restore session from saved tokens.
    _tryRestore();
  }

  /// Attempt to resume a previous session using persisted tokens.
  /// If the saved token is still valid, skip the login form entirely.
  Future<void> _tryRestore() async {
    final api = context.read<ApiClientBase>();
    final session = context.read<SessionManager>();

    try {
      final profileResult = await api.getProfile();
      if (profileResult.data != null) {
        final p = profileResult.data!;
        final player = PlayerResponse(
          playerId: p.playerId,
          username: p.username,
          playerType: p.playerType,
          eloRating: p.eloRating,
          createdAt: p.createdAt,
        );
        // Build a synthetic LoginResponse so setAuth works.
        // The real tokens are already loaded inside HttpApiClient.
        session.setAuth(
          LoginResponse(
            accessToken: '',
            refreshToken: '',
            tokenType: 'Bearer',
            expiresIn: 0,
          ),
          player,
        );
        final energy = await api.getEnergy();
        if (energy.data != null) session.updateEnergy(energy.data!);
        final gold = await api.getGold();
        if (gold.data != null) session.updateGold(gold.data!);
        if (mounted) context.go('/');
      }
    } catch (_) {
      // No saved token or it expired — show the login form.
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _usernameController.dispose();
    _passwordController.dispose();
    _usernameFocus.dispose();
    _passwordFocus.dispose();
    super.dispose();
  }

  // ---------------------------------------------------------------------------
  // Apple Sign-In
  // ---------------------------------------------------------------------------

  Future<void> _signInWithApple() async {
    if (_loading) return;

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final credential = await SignInWithApple.getAppleIDCredential(
        scopes: [AppleIDAuthorizationScopes.fullName],
      );

      final identityToken = credential.identityToken;
      if (identityToken == null) {
        if (mounted) setState(() => _error = 'Apple Sign-In failed');
        return;
      }

      // Build display name from Apple's given/family name (only sent on first auth).
      String? displayName;
      if (credential.givenName != null || credential.familyName != null) {
        displayName = [
          credential.givenName,
          credential.familyName,
        ].where((s) => s != null && s.isNotEmpty).join(' ');
        if (displayName.isEmpty) displayName = null;
      }

      await _completeAppleLogin(
        identityToken: identityToken,
        authorizationCode: credential.authorizationCode,
        displayName: displayName,
      );
    } on SignInWithAppleAuthorizationException catch (e) {
      if (e.code == AuthorizationErrorCode.canceled) {
        // User cancelled — not an error.
      } else {
        if (mounted) setState(() => _error = 'Apple Sign-In failed');
      }
    } on SignInWithAppleNotSupportedException {
      // Platform doesn't support Apple Sign-In (Windows, etc.).
      if (mounted) {
        setState(() {
          _showDevLogin = true;
          _error = 'Apple Sign-In not available on this platform';
        });
      }
    } catch (_) {
      // Network error, timeout, or other unexpected failure.
      if (mounted) {
        setState(() => _error = 'Sign-in failed — check your connection');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _completeAppleLogin({
    required String identityToken,
    String? authorizationCode,
    String? displayName,
  }) async {
    final api = context.read<ApiClientBase>();
    final session = context.read<SessionManager>();

    final result = await api.appleLogin(
      AppleLoginRequest(
        identityToken: identityToken,
        authorizationCode: authorizationCode,
        displayName: displayName,
      ),
    );

    if (result.data == null) {
      if (mounted) {
        setState(() => _error = result.error?.message ?? 'Login failed');
      }
      return;
    }

    final reg = result.data!;
    session.setAuth(reg.auth, reg.player);

    final energy = await api.getEnergy();
    if (energy.data != null) session.updateEnergy(energy.data!);
    final gold = await api.getGold();
    if (gold.data != null) session.updateGold(gold.data!);
    if (mounted) {
      context.go(reg.isNewPlayer ? '/choose-username' : '/');
    }
  }

  // ---------------------------------------------------------------------------
  // Dev login (username/password)
  // ---------------------------------------------------------------------------

  Future<void> _authenticate({required bool register}) async {
    if (_loading) return;

    final username = _usernameController.text.trim();
    final password = _passwordController.text;

    if (username.isEmpty || password.isEmpty) {
      setState(() => _error = 'Enter username and password');
      return;
    }

    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final api = context.read<ApiClientBase>();
      final session = context.read<SessionManager>();

      if (session.isLoggedIn) {
        if (mounted) context.go('/');
        return;
      }

      if (register) {
        final regResult = await api.register(
          RegisterRequest(username: username, password: password),
        );
        if (regResult.data == null) {
          if (mounted) {
            setState(
              () => _error = regResult.error?.message ?? 'Registration failed',
            );
          }
          return;
        }
      }

      final loginResult = await api.login(
        LoginRequest(username: username, password: password),
      );
      if (loginResult.data == null) {
        if (mounted) {
          setState(() => _error = loginResult.error?.message ?? 'Login failed');
        }
        return;
      }

      final profileResult = await api.getProfile();
      if (profileResult.data != null) {
        final p = profileResult.data!;
        final player = PlayerResponse(
          playerId: p.playerId,
          username: p.username,
          playerType: p.playerType,
          eloRating: p.eloRating,
          createdAt: p.createdAt,
        );
        session.setAuth(loginResult.data!, player);
      }
      final energy = await api.getEnergy();
      if (energy.data != null) session.updateEnergy(energy.data!);
      final gold = await api.getGold();
      if (gold.data != null) session.updateGold(gold.data!);
      if (mounted) context.go('/');
    } catch (e) {
      if (mounted) {
        setState(() => _error = 'Could not connect to server');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  // ---------------------------------------------------------------------------
  // Build
  // ---------------------------------------------------------------------------

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: ChromaGradients.screen),
        child: Stack(
          children: [
            const Positioned.fill(child: StarfieldBackground()),
            SafeArea(
              child: Center(
                child: SingleChildScrollView(
                  padding: const EdgeInsets.symmetric(horizontal: 32),
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      // Logo with pulsing radial glow behind it.
                      ConstrainedBox(
                        constraints: const BoxConstraints(maxWidth: 320),
                        child: FractionallySizedBox(
                          widthFactor: 0.65,
                          child: AspectRatio(
                            aspectRatio: 1.0,
                            child: Stack(
                              alignment: Alignment.center,
                              children: [
                                AnimatedBuilder(
                                  animation: _pulseAnimation,
                                  builder: (context, _) => Container(
                                    width: double.infinity,
                                    height: double.infinity,
                                    decoration: BoxDecoration(
                                      shape: BoxShape.circle,
                                      gradient: RadialGradient(
                                        colors: [
                                          ChromaColors.accent.withValues(
                                            alpha: _pulseAnimation.value,
                                          ),
                                          ChromaColors.accentGlow.withValues(
                                            alpha: _pulseAnimation.value * 0.4,
                                          ),
                                          Colors.transparent,
                                        ],
                                        stops: const [0.0, 0.4, 1.0],
                                      ),
                                    ),
                                  ),
                                ),
                                Image.asset(
                                  'assets/graphics/logo.png',
                                  fit: BoxFit.contain,
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),

                      const SizedBox(height: 40),

                      // Apple Sign-In button (primary).
                      GestureDetector(
                        onTap: _loading ? null : _signInWithApple,
                        child: Container(
                          width: 280,
                          padding: const EdgeInsets.symmetric(vertical: 14),
                          decoration: BoxDecoration(
                            gradient: ChromaGradients.accent,
                            borderRadius: BorderRadius.circular(22),
                            boxShadow: [
                              BoxShadow(
                                color: ChromaColors.accent.withValues(
                                  alpha: 0.4,
                                ),
                                blurRadius: 16,
                                spreadRadius: 1,
                              ),
                            ],
                          ),
                          alignment: Alignment.center,
                          child: _loading && !_showDevLogin
                              ? const SizedBox(
                                  width: 20,
                                  height: 20,
                                  child: CircularProgressIndicator(
                                    color: Colors.white,
                                    strokeWidth: 2.5,
                                  ),
                                )
                              : const FittedBox(
                                  fit: BoxFit.scaleDown,
                                  child: Row(
                                    mainAxisSize: MainAxisSize.min,
                                    children: [
                                      Icon(
                                        Icons.apple,
                                        color: Colors.white,
                                        size: 24,
                                      ),
                                      SizedBox(width: 8),
                                      Text(
                                        'Sign in with Apple',
                                        style: TextStyle(
                                          color: Colors.white,
                                          fontSize: 16,
                                          fontWeight: FontWeight.w600,
                                          letterSpacing: 1,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                        ),
                      ),

                      const SizedBox(height: 24),

                      // Dev Login toggle.
                      GestureDetector(
                        onTap: () =>
                            setState(() => _showDevLogin = !_showDevLogin),
                        child: Text(
                          _showDevLogin ? 'HIDE DEV LOGIN' : 'DEV LOGIN',
                          style: TextStyle(
                            color: Colors.white.withValues(alpha: 0.35),
                            fontSize: 12,
                            fontWeight: FontWeight.w500,
                            letterSpacing: 2,
                          ),
                        ),
                      ),

                      // Dev login form (collapsible).
                      if (_showDevLogin) ...[
                        const SizedBox(height: 24),

                        // Username field.
                        SizedBox(
                          width: 280,
                          child: TextField(
                            controller: _usernameController,
                            focusNode: _usernameFocus,
                            style: const TextStyle(color: Colors.white),
                            decoration: InputDecoration(
                              hintText: 'Username',
                              hintStyle: TextStyle(
                                color: Colors.white.withValues(alpha: 0.4),
                              ),
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
                            ),
                            textInputAction: TextInputAction.next,
                            onSubmitted: (_) => _passwordFocus.requestFocus(),
                          ),
                        ),

                        const SizedBox(height: 16),

                        // Password field.
                        SizedBox(
                          width: 280,
                          child: TextField(
                            controller: _passwordController,
                            focusNode: _passwordFocus,
                            obscureText: true,
                            style: const TextStyle(color: Colors.white),
                            decoration: InputDecoration(
                              hintText: 'Password',
                              hintStyle: TextStyle(
                                color: Colors.white.withValues(alpha: 0.4),
                              ),
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
                            ),
                            textInputAction: TextInputAction.done,
                            onSubmitted: (_) => _authenticate(register: false),
                          ),
                        ),

                        const SizedBox(height: 24),

                        // LOGIN button.
                        GestureDetector(
                          onTap: () => _authenticate(register: false),
                          child: Container(
                            width: 220,
                            padding: const EdgeInsets.symmetric(vertical: 14),
                            decoration: BoxDecoration(
                              gradient: ChromaGradients.accent,
                              borderRadius: BorderRadius.circular(22),
                              boxShadow: [
                                BoxShadow(
                                  color: ChromaColors.accent.withValues(
                                    alpha: 0.4,
                                  ),
                                  blurRadius: 16,
                                  spreadRadius: 1,
                                ),
                              ],
                            ),
                            alignment: Alignment.center,
                            child: _loading
                                ? const SizedBox(
                                    width: 20,
                                    height: 20,
                                    child: CircularProgressIndicator(
                                      color: Colors.white,
                                      strokeWidth: 2.5,
                                    ),
                                  )
                                : const Text(
                                    'LOGIN',
                                    style: TextStyle(
                                      color: Colors.white,
                                      fontSize: 16,
                                      fontWeight: FontWeight.bold,
                                      letterSpacing: 4,
                                    ),
                                  ),
                          ),
                        ),

                        const SizedBox(height: 12),

                        // REGISTER link.
                        GestureDetector(
                          onTap: () => _authenticate(register: true),
                          child: Text(
                            'NEW PLAYER? REGISTER',
                            style: TextStyle(
                              color: Colors.white.withValues(alpha: 0.5),
                              fontSize: 13,
                              fontWeight: FontWeight.w500,
                              letterSpacing: 2,
                            ),
                          ),
                        ),
                      ],

                      // Error message.
                      if (_error != null) ...[
                        const SizedBox(height: 24),
                        Text(
                          _error!,
                          style: TextStyle(
                            color: Colors.red.shade300,
                            fontSize: 14,
                          ),
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
