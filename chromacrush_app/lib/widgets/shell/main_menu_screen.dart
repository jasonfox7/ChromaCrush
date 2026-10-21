/// Main menu — primary entry point with Play button and game info.
///
/// Gradient background, shader-masked title, glass energy pill, gradient play button.
library;

import 'dart:async';

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../models/backend_contract.dart';
import '../../services/api_client.dart';
import '../../services/session_manager.dart';
import '../../theme/chroma_theme.dart';
import '../../theme/glass_panel.dart';
import '../../view_models/match_view_model.dart';
import 'starfield_background.dart';

class MainMenuScreen extends StatefulWidget {
  const MainMenuScreen({super.key});

  @override
  State<MainMenuScreen> createState() => _MainMenuScreenState();
}

class _MainMenuScreenState extends State<MainMenuScreen> {
  Timer? _tickTimer;
  Timer? _syncTimer;
  String? _activeMatchId;
  List<LeaderboardEntry>? _eloLeaderboard;
  List<LeaderboardEntry>? _highScoreLeaderboard;
  String _leaderboardMode = 'elo';
  bool _leaderboardExpanded = false;

  @override
  void initState() {
    super.initState();
    // Immediate sync on screen entry (e.g. returning from a match).
    _syncEnergy();
    _syncGold();
    _syncLeaderboard();
    _checkActiveMatch();
    // 1-second tick for client-side countdown.
    _tickTimer = Timer.periodic(const Duration(seconds: 1), (_) {
      context.read<SessionManager>().tickRegenTimer();
    });
    // 30-second server re-sync.
    _syncTimer = Timer.periodic(const Duration(seconds: 30), (_) {
      _syncEnergy();
      _syncGold();
      _syncLeaderboard();
    });
  }

  Future<void> _checkActiveMatch() async {
    try {
      final api = context.read<ApiClientBase>();
      final result = await api.getActiveMatches();
      if (result.data != null && result.data!.isNotEmpty && mounted) {
        setState(() {
          _activeMatchId = result.data!.first.matchId;
        });
      }
    } catch (_) {}
  }

  void _resumeMatch() {
    if (_activeMatchId == null) return;
    final vm = context.read<MatchViewModel>();
    vm.rejoinMatch(_activeMatchId!);
    context.push('/game');
  }

  Future<void> _syncEnergy() async {
    try {
      final api = context.read<ApiClientBase>();
      final result = await api.getEnergy();
      if (result.data != null && mounted) {
        context.read<SessionManager>().updateEnergy(result.data!);
      }
    } catch (_) {
      // Non-critical — timer will retry.
    }
  }

  void _startSinglePlayer(BuildContext context) {
    final session = context.read<SessionManager>();
    final energy = session.energy;
    if (energy != null && energy.currentHearts < 1) {
      _showHeartPurchaseDialog(context, session.goldBalance);
      return;
    }
    context.push('/matchmaking');
  }

  void _showHeartPurchaseDialog(BuildContext context, int goldBalance) {
    final canAfford = goldBalance >= 100;

    showCupertinoDialog<void>(
      context: context,
      builder: (dialogContext) => CupertinoAlertDialog(
        title: const Text('Out of Energy!'),
        content: Text(
          canAfford
              ? 'Buy 1 heart for 100 gold to keep playing?'
              : 'Not enough gold! Visit the Barter to get more.',
        ),
        actions: [
          if (canAfford)
            CupertinoDialogAction(
              onPressed: () async {
                Navigator.of(dialogContext).pop();
                await _buyHeartAndPlay();
              },
              child: const Text('Buy (100g)'),
            ),
          CupertinoDialogAction(
            onPressed: () {
              Navigator.of(dialogContext).pop();
              context.push('/barter');
            },
            child: const Text('Barter'),
          ),
          CupertinoDialogAction(
            isDestructiveAction: true,
            onPressed: () => Navigator.of(dialogContext).pop(),
            child: const Text('Cancel'),
          ),
        ],
      ),
    );
  }

  Future<void> _buyHeartAndPlay() async {
    try {
      final api = context.read<ApiClientBase>();
      final result = await api.buyItem(BuyItemRequest(itemId: 'heart_1'));
      if (!mounted) return;
      if (result.data != null) {
        context.read<SessionManager>().updateGoldBalance(
          result.data!.newBalance,
        );
      }
      // Refresh energy after purchase.
      final energy = await api.getEnergy();
      if (energy.data != null && mounted) {
        context.read<SessionManager>().updateEnergy(energy.data!);
      }
      if (mounted) context.push('/matchmaking');
    } catch (_) {
      // Purchase failed — stay on menu.
    }
  }

  Future<void> _syncGold() async {
    try {
      final api = context.read<ApiClientBase>();
      final result = await api.getGold();
      if (result.data != null && mounted) {
        context.read<SessionManager>().updateGold(result.data!);
      }
    } catch (_) {}
  }

  Future<void> _syncLeaderboard() async {
    try {
      final api = context.read<ApiClientBase>();
      final eloResult = await api.getLeaderboard(limit: 50, sortBy: 'elo');
      final hsResult =
          await api.getLeaderboard(limit: 50, sortBy: 'high_score');
      if (mounted) {
        setState(() {
          if (eloResult.data != null) {
            _eloLeaderboard = eloResult.data!.entries;
          }
          if (hsResult.data != null) {
            _highScoreLeaderboard = hsResult.data!.entries;
          }
        });
      }
    } catch (_) {}
  }

  @override
  void dispose() {
    _tickTimer?.cancel();
    _syncTimer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<SessionManager>();
    final energy = session.energy;

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: ChromaGradients.screen),
        child: SafeArea(
          child: Stack(
            children: [
              const Positioned.fill(child: StarfieldBackground()),

              // Subtle radial glow from center.
              Center(
                child: Container(
                  width: 300,
                  height: 300,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: RadialGradient(
                      colors: [
                        ChromaColors.accent.withValues(alpha: 0.06),
                        Colors.transparent,
                      ],
                    ),
                  ),
                ),
              ),

              // Settings gear (top-right).
              Positioned(
                top: 16,
                right: 16,
                child: IconButton(
                  icon: const Icon(
                    CupertinoIcons.gear,
                    color: Colors.white54,
                    size: 28,
                  ),
                  onPressed: () => context.push('/settings'),
                ),
              ),

              // Energy + gold display (top-left).
              Positioned(
                top: 16,
                left: 16,
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (energy != null)
                      _EnergyDisplay(
                        currentHearts: energy.currentHearts,
                        maxHearts: energy.maxHearts,
                        regenSeconds: session.regenSecondsRemaining,
                      ),
                    if (energy != null && session.gold != null)
                      const SizedBox(width: 8),
                    if (session.gold != null)
                      _GoldDisplay(balance: session.goldBalance),
                  ],
                ),
              ),

              // Center content + leaderboard.
              Positioned(
                top: 56,
                bottom: 56,
                left: 16,
                right: 16,
                child: Column(
                  children: [
                    const Spacer(flex: 2),
                    GlassPanel(
                      borderRadius: 20,
                      padding: const EdgeInsets.symmetric(
                        horizontal: 28,
                        vertical: 28,
                      ),
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          // Title with gradient shader mask.
                          ShaderMask(
                            shaderCallback: (bounds) =>
                                ChromaGradients.accent.createShader(bounds),
                            child: const Text(
                              'CHROMA\u2726CRUSH',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 24,
                                fontWeight: FontWeight.w900,
                                letterSpacing: 4,
                              ),
                            ),
                          ),
                          const SizedBox(height: 24),

                          // Single player / resume button.
                          _PlayButton(
                            label: _activeMatchId != null
                                ? 'RESUME MATCH'
                                : 'SINGLE PLAYER',
                            onPressed: _activeMatchId != null
                                ? _resumeMatch
                                : () => _startSinglePlayer(context),
                          ),

                          const SizedBox(height: 12),

                          // Card vault button (locked during active match).
                          _PlayButton(
                            label: 'CARD VAULT',
                            onPressed: _activeMatchId != null
                                ? () {
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      const SnackBar(
                                        content: Text(
                                          'Cards are locked during an active match',
                                        ),
                                        duration: Duration(seconds: 2),
                                      ),
                                    );
                                  }
                                : () => context.push('/vault'),
                            secondary: true,
                          ),

                          const SizedBox(height: 12),

                          // Barter button.
                          _PlayButton(
                            label: 'BARTER',
                            onPressed: () => context.push('/barter'),
                            secondary: true,
                          ),

                          const SizedBox(height: 12),

                          // Tutorial button.
                          _PlayButton(
                            label: 'TUTORIAL',
                            onPressed: () => context.push('/tutorial'),
                            secondary: true,
                          ),

                          const SizedBox(height: 12),

                          // Campaign button.
                          _PlayButton(
                            label: 'CAMPAIGN',
                            onPressed: () => context.push('/campaign'),
                            secondary: true,
                          ),
                        ],
                      ),
                    ),

                    // Player info + logout.
                    if (session.player != null)
                      Padding(
                        padding: const EdgeInsets.only(top: 16),
                        child: Column(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            Text(
                              session.player!.username,
                              style: ChromaText.bodyMedium.copyWith(
                                color: ChromaColors.textTertiary,
                              ),
                            ),
                            const SizedBox(height: 8),
                            GestureDetector(
                              onTap: () async {
                                try {
                                  await context.read<ApiClientBase>().logout();
                                } catch (_) {}
                                session.clearAuth();
                                if (context.mounted) context.go('/login');
                              },
                              child: Text(
                                'LOG OUT',
                                style: TextStyle(
                                  color: Colors.white.withValues(alpha: 0.3),
                                  fontSize: 11,
                                  fontWeight: FontWeight.w500,
                                  letterSpacing: 2,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),

                    const SizedBox(height: 12),

                    // Leaderboard fills remaining space (tap to expand).
                    if (_eloLeaderboard != null ||
                        _highScoreLeaderboard != null)
                      Expanded(
                        flex: 3,
                        child: GestureDetector(
                          onTap: () =>
                              setState(() => _leaderboardExpanded = true),
                          child: _LeaderboardPanel(
                            eloEntries: _eloLeaderboard ?? [],
                            highScoreEntries: _highScoreLeaderboard ?? [],
                            currentPlayerId: session.player?.playerId,
                            mode: _leaderboardMode,
                            onModeChanged: (mode) {
                              setState(() => _leaderboardMode = mode);
                            },
                          ),
                        ),
                      ),
                    if (_eloLeaderboard == null &&
                        _highScoreLeaderboard == null)
                      const Spacer(flex: 3),
                  ],
                ),
              ),

              // Expanded leaderboard overlay.
              IgnorePointer(
                ignoring: !_leaderboardExpanded,
                child: AnimatedOpacity(
                  opacity: _leaderboardExpanded ? 1.0 : 0.0,
                  duration: const Duration(milliseconds: 250),
                  curve: Curves.easeOut,
                  child: GestureDetector(
                    onTap: () =>
                        setState(() => _leaderboardExpanded = false),
                    child: Container(
                      color: Colors.black.withValues(alpha: 0.7),
                      child: SafeArea(
                        child: Padding(
                          padding: const EdgeInsets.all(20),
                          child: GestureDetector(
                            onTap: () {}, // absorb taps on the panel
                            child: Column(
                              children: [
                                // Header row.
                                Row(
                                  children: [
                                    Text(
                                      'LEADERBOARD',
                                      style: TextStyle(
                                        color: Colors.white
                                            .withValues(alpha: 0.7),
                                        fontSize: 14,
                                        fontWeight: FontWeight.w800,
                                        letterSpacing: 3,
                                      ),
                                    ),
                                    const Spacer(),
                                    GestureDetector(
                                      onTap: () => setState(
                                        () =>
                                            _leaderboardExpanded = false,
                                      ),
                                      child: Container(
                                        width: 32,
                                        height: 32,
                                        decoration: BoxDecoration(
                                          color: Colors.white
                                              .withValues(alpha: 0.1),
                                          shape: BoxShape.circle,
                                        ),
                                        child: const Icon(
                                          CupertinoIcons.xmark,
                                          color: Colors.white54,
                                          size: 16,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 12),
                                // Full leaderboard panel.
                                Expanded(
                                  child: _LeaderboardPanel(
                                    eloEntries: _eloLeaderboard ?? [],
                                    highScoreEntries:
                                        _highScoreLeaderboard ?? [],
                                    currentPlayerId:
                                        session.player?.playerId,
                                    mode: _leaderboardMode,
                                    onModeChanged: (mode) {
                                      setState(
                                        () => _leaderboardMode = mode,
                                      );
                                    },
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                    ),
                  ),
                ),
              ),

              // Players-first value prop (bottom) — commented out for now.
              // Positioned(
              //   left: 0,
              //   right: 0,
              //   bottom: 16,
              //   child: Column(
              //     mainAxisSize: MainAxisSize.min,
              //     children: [
              //       Text(
              //         'PLAYERS FIRST',
              //         textAlign: TextAlign.center,
              //         style: TextStyle(
              //           color: Colors.white.withValues(alpha: 0.35),
              //           fontSize: 11,
              //           fontWeight: FontWeight.w700,
              //           letterSpacing: 3,
              //         ),
              //       ),
              //       const SizedBox(height: 3),
              //       Text(
              //         'Minimal ads \u2022 Cheap extras \u2022 Ad-free \$1 (Extras 50% off)',
              //         textAlign: TextAlign.center,
              //         style: TextStyle(
              //           color: Colors.white.withValues(alpha: 0.25),
              //           fontSize: 10,
              //           fontWeight: FontWeight.w400,
              //           letterSpacing: 0.5,
              //         ),
              //       ),
              //     ],
              //   ),
              // ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PlayButton extends StatefulWidget {
  const _PlayButton({
    required this.onPressed,
    this.label = 'PLAY',
    this.secondary = false,
  });
  final VoidCallback onPressed;
  final String label;
  final bool secondary;

  @override
  State<_PlayButton> createState() => _PlayButtonState();
}

class _PlayButtonState extends State<_PlayButton>
    with SingleTickerProviderStateMixin {
  AnimationController? _pulseController;
  Animation<double>? _pulseAnimation;

  @override
  void initState() {
    super.initState();
    if (!widget.secondary) {
      _pulseController = AnimationController(
        vsync: this,
        duration: const Duration(milliseconds: 2000),
      )..repeat(reverse: true);
      _pulseAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
        CurvedAnimation(parent: _pulseController!, curve: Curves.easeInOut),
      );
    }
  }

  @override
  void dispose() {
    _pulseController?.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final button = GestureDetector(
      onTap: widget.onPressed,
      child: widget.secondary ? _buildSecondary() : _buildPrimary(),
    );
    if (_pulseAnimation == null) return button;
    return AnimatedBuilder(
      animation: _pulseAnimation!,
      builder: (context, child) => child!,
      child: button,
    );
  }

  Widget _buildPrimary() {
    if (_pulseAnimation == null) {
      return _primaryContainer(glowAlpha: 0.4, glowSpread: 1.0);
    }
    return AnimatedBuilder(
      animation: _pulseAnimation!,
      builder: (context, _) {
        final t = _pulseAnimation!.value;
        return _primaryContainer(
          glowAlpha: 0.3 + 0.25 * t,
          glowSpread: 1.0 + 4.0 * t,
        );
      },
    );
  }

  Widget _primaryContainer({
    required double glowAlpha,
    required double glowSpread,
  }) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 14),
      decoration: BoxDecoration(
        gradient: ChromaGradients.accent,
        borderRadius: BorderRadius.circular(22),
        boxShadow: [
          BoxShadow(
            color: ChromaColors.accent.withValues(alpha: glowAlpha),
            blurRadius: 16 + 4 * glowSpread,
            spreadRadius: glowSpread,
          ),
        ],
      ),
      child: Text(
        widget.label,
        style: const TextStyle(
          color: Colors.white,
          fontSize: 16,
          fontWeight: FontWeight.bold,
          letterSpacing: 4,
        ),
      ),
    );
  }

  Widget _buildSecondary() {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 6),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            ChromaColors.accent.withValues(alpha: 0.15),
            ChromaColors.accentGlow.withValues(alpha: 0.10),
          ],
        ),
        borderRadius: BorderRadius.circular(22),
        border: Border.all(color: ChromaColors.accent.withValues(alpha: 0.20)),
      ),
      child: Text(
        widget.label,
        style: const TextStyle(
          color: Colors.white70,
          fontSize: 13,
          fontWeight: FontWeight.bold,
          letterSpacing: 3,
        ),
      ),
    );
  }
}

class _EnergyDisplay extends StatelessWidget {
  const _EnergyDisplay({
    required this.currentHearts,
    required this.maxHearts,
    this.regenSeconds,
  });
  final int currentHearts;
  final int maxHearts;
  final int? regenSeconds;

  String _formatTimer(int seconds) {
    final m = seconds ~/ 60;
    final s = seconds % 60;
    return '$m:${s.toString().padLeft(2, '0')}';
  }

  @override
  Widget build(BuildContext context) {
    return GlassPanel(
      borderRadius: 20,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(
            CupertinoIcons.heart_fill,
            color: Colors.redAccent,
            size: 20,
          ),
          const SizedBox(width: 2),
          Text(
            '\u00D7$currentHearts',
            style: const TextStyle(
              color: Colors.white70,
              fontSize: 14,
              fontWeight: FontWeight.w700,
            ),
          ),
          if (regenSeconds != null &&
              regenSeconds! > 0 &&
              currentHearts < maxHearts) ...[
            const SizedBox(width: 8),
            Text(
              _formatTimer(regenSeconds!),
              style: const TextStyle(
                color: Colors.white54,
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _GoldDisplay extends StatelessWidget {
  const _GoldDisplay({required this.balance});
  final int balance;

  @override
  Widget build(BuildContext context) {
    return GlassPanel(
      borderRadius: 20,
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 18,
            height: 18,
            decoration: const BoxDecoration(
              shape: BoxShape.circle,
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [Color(0xFFFFD700), Color(0xFFDAA520)],
              ),
            ),
            child: const Center(
              child: Text(
                'G',
                style: TextStyle(
                  color: Color(0xFF5C3D00),
                  fontSize: 10,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
          ),
          const SizedBox(width: 4),
          Text(
            '\u00D7$balance',
            style: const TextStyle(
              color: Colors.white70,
              fontSize: 14,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _LeaderboardPanel extends StatelessWidget {
  const _LeaderboardPanel({
    required this.eloEntries,
    required this.highScoreEntries,
    required this.mode,
    required this.onModeChanged,
    this.currentPlayerId,
  });
  final List<LeaderboardEntry> eloEntries;
  final List<LeaderboardEntry> highScoreEntries;
  final String? currentPlayerId;
  final String mode;
  final ValueChanged<String> onModeChanged;

  @override
  Widget build(BuildContext context) {
    final isElo = mode == 'elo';
    final entries = isElo ? eloEntries : highScoreEntries;

    return GestureDetector(
      onHorizontalDragEnd: (details) {
        if (details.primaryVelocity == null) return;
        if (details.primaryVelocity! < -100) {
          onModeChanged('high_score');
        } else if (details.primaryVelocity! > 100) {
          onModeChanged('elo');
        }
      },
      child: GlassPanel(
        borderRadius: 20,
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Row(
              children: [
                Text(
                  'LEADERBOARD',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.5),
                    fontSize: 11,
                    fontWeight: FontWeight.w700,
                    letterSpacing: 3,
                  ),
                ),
                const Spacer(),
                _ModeToggle(isElo: isElo, onModeChanged: onModeChanged),
              ],
            ),
            const SizedBox(height: 8),
            Expanded(
              child: ListView.builder(
                padding: EdgeInsets.zero,
                itemCount: entries.length,
                itemBuilder: (context, index) {
                  final entry = entries[index];
                  final isMe = entry.playerId == currentPlayerId;
                  return _LeaderboardRow(
                    rank: entry.rank,
                    username: entry.username,
                    value: isElo
                        ? entry.eloRating
                        : (entry.highestScore ?? 0),
                    isCurrentPlayer: isMe,
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _ModeToggle extends StatelessWidget {
  const _ModeToggle({required this.isElo, required this.onModeChanged});
  final bool isElo;
  final ValueChanged<String> onModeChanged;

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white.withValues(alpha: 0.06),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _toggleSegment('ELO', isElo, () => onModeChanged('elo')),
          _toggleSegment('SCORE', !isElo, () => onModeChanged('high_score')),
        ],
      ),
    );
  }

  Widget _toggleSegment(String label, bool active, VoidCallback onTap) {
    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: active
              ? ChromaColors.accent.withValues(alpha: 0.25)
              : Colors.transparent,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Text(
          label,
          style: TextStyle(
            color: active
                ? Colors.white.withValues(alpha: 0.9)
                : Colors.white.withValues(alpha: 0.35),
            fontSize: 10,
            fontWeight: FontWeight.w700,
            letterSpacing: 1,
          ),
        ),
      ),
    );
  }
}

class _LeaderboardRow extends StatelessWidget {
  const _LeaderboardRow({
    required this.rank,
    required this.username,
    required this.value,
    this.isCurrentPlayer = false,
  });
  final int rank;
  final String username;
  final int value;
  final bool isCurrentPlayer;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 4, horizontal: 4),
      decoration: isCurrentPlayer
          ? BoxDecoration(
              color: ChromaColors.accent.withValues(alpha: 0.12),
              borderRadius: BorderRadius.circular(6),
            )
          : null,
      child: Row(
        children: [
          SizedBox(
            width: 24,
            child: Text(
              '$rank',
              textAlign: TextAlign.right,
              style: TextStyle(
                color: Colors.white.withValues(alpha: 0.4),
                fontSize: 12,
                fontWeight: FontWeight.w600,
              ),
            ),
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              username,
              overflow: TextOverflow.ellipsis,
              maxLines: 1,
              style: TextStyle(
                color: isCurrentPlayer ? Colors.white : Colors.white70,
                fontSize: 12,
                fontWeight: isCurrentPlayer ? FontWeight.w700 : FontWeight.w500,
              ),
            ),
          ),
          Text(
            '$value',
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.5),
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}
