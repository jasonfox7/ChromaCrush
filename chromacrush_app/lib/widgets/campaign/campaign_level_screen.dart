/// Campaign level detail — shows obstacle layout, move budget, and start button.
///
/// Fetches the full level definition from the campaign API and displays
/// a mini preview grid with obstacle positions, move count, and heart cost.
library;

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../config/visual_theme_service.dart';
import '../../models/backend_contract.dart';
import '../../services/api_client.dart';
import '../../services/audio_engine.dart';
import '../../theme/chroma_theme.dart';
import '../../theme/glass_panel.dart';
import '../../view_models/campaign_view_model.dart';

class CampaignLevelScreen extends StatefulWidget {
  const CampaignLevelScreen({super.key, required this.levelNumber});

  final int levelNumber;

  @override
  State<CampaignLevelScreen> createState() => _CampaignLevelScreenState();
}

class _CampaignLevelScreenState extends State<CampaignLevelScreen> {
  bool _loading = true;
  String? _error;
  CampaignLevelResponse? _level;

  @override
  void initState() {
    super.initState();
    _fetchLevel();
  }

  Future<void> _fetchLevel() async {
    try {
      final api = context.read<ApiClientBase>();
      final result = await api.getCampaignLevel(widget.levelNumber);
      if (!mounted) return;
      if (result.data != null) {
        setState(() {
          _level = result.data!;
          _loading = false;
        });
      } else {
        setState(() {
          _error = 'Failed to load level';
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = 'Failed to load level: $e';
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: ChromaGradients.screen),
        child: SafeArea(
          child: Column(
            children: [
              // Header.
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 12,
                ),
                child: Row(
                  children: [
                    GestureDetector(
                      onTap: () => context.pop(),
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
                    const SizedBox(width: 12),
                    Text(
                      'LEVEL ${widget.levelNumber}',
                      style: ChromaText.headlineMedium.copyWith(
                        color: ChromaColors.textPrimary,
                        letterSpacing: 4,
                      ),
                    ),
                  ],
                ),
              ),

              // Body.
              Expanded(
                child: _loading
                    ? const Center(
                        child: CupertinoActivityIndicator(
                          radius: 16,
                          color: ChromaColors.accentGlow,
                        ),
                      )
                    : _error != null
                        ? Center(
                            child: Text(
                              _error!,
                              style: ChromaText.bodyMedium.copyWith(
                                color: Colors.redAccent,
                              ),
                            ),
                          )
                        : _buildContent(),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildContent() {
    final level = _level!;

    return SingleChildScrollView(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Column(
        children: [
          const SizedBox(height: 16),

          // Obstacle preview grid.
          GlassPanel(
            borderRadius: 16,
            padding: const EdgeInsets.all(16),
            child: Column(
              children: [
                Text(
                  'OBSTACLE LAYOUT',
                  style: ChromaText.labelSmall.copyWith(
                    color: ChromaColors.textSecondary,
                    letterSpacing: 2,
                  ),
                ),
                const SizedBox(height: 12),
                _ObstaclePreviewGrid(obstacles: level.obstacles),
              ],
            ),
          ),
          const SizedBox(height: 16),

          // Stats row.
          Row(
            children: [
              Expanded(
                child: GlassPanel(
                  borderRadius: 12,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  child: Column(
                    children: [
                      Text(
                        'MOVES',
                        style: ChromaText.labelSmall.copyWith(
                          color: ChromaColors.textSecondary,
                          letterSpacing: 2,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${level.moves}',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 28,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: GlassPanel(
                  borderRadius: 12,
                  padding: const EdgeInsets.symmetric(vertical: 12),
                  child: Column(
                    children: [
                      Text(
                        'OBSTACLES',
                        style: ChromaText.labelSmall.copyWith(
                          color: ChromaColors.textSecondary,
                          letterSpacing: 2,
                        ),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        '${level.obstacles.length}',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 28,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),

          // Heart cost (checkpoint only).
          if (level.isCheckpoint)
            GlassPanel(
              borderRadius: 12,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(
                    CupertinoIcons.heart_fill,
                    color: Color(0xFFFF2D55),
                    size: 18,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'Costs ${level.heartCost} heart',
                    style: ChromaText.bodyMedium.copyWith(
                      color: ChromaColors.textPrimary,
                    ),
                  ),
                ],
              ),
            ),
          if (level.isCheckpoint) const SizedBox(height: 12),

          // Checkpoint badge.
          if (level.isCheckpoint)
            GlassPanel(
              borderRadius: 12,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
              child: Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(
                    CupertinoIcons.star_fill,
                    color: Color(0xFFFFD700),
                    size: 18,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'CHECKPOINT',
                    style: ChromaText.labelSmall.copyWith(
                      color: const Color(0xFFFFD700),
                      letterSpacing: 2,
                    ),
                  ),
                ],
              ),
            ),

          const SizedBox(height: 32),

          // Start button.
          GestureDetector(
            onTap: () {
              final campaignVM = context.read<CampaignViewModel>();
              context.read<AudioEngineBase>().stopMusic();
              campaignVM.startLevel(
                widget.levelNumber,
                checkpoint: _level?.isCheckpoint ?? false,
                levelReward: _level?.reward,
              );
              context.go('/campaign/play');
            },
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 14),
              decoration: BoxDecoration(
                gradient: ChromaGradients.accent,
                borderRadius: BorderRadius.circular(22),
                boxShadow: [
                  BoxShadow(
                    color: ChromaColors.accent.withValues(alpha: 0.4),
                    blurRadius: 20,
                    spreadRadius: 1,
                  ),
                ],
              ),
              child: const Text(
                'START',
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 4,
                ),
              ),
            ),
          ),
          const SizedBox(height: 32),
        ],
      ),
    );
  }
}

/// Mini 8x8 grid showing obstacle positions as grey markers.
class _ObstaclePreviewGrid extends StatelessWidget {
  const _ObstaclePreviewGrid({required this.obstacles});

  final List<ObstacleDefinition> obstacles;

  @override
  Widget build(BuildContext context) {
    final theme = context.read<VisualThemeBase>();

    // Build a set of obstacle positions for fast lookup.
    final obstacleSet = <(int, int)>{};
    for (final obs in obstacles) {
      obstacleSet.add((obs.row, obs.col));
    }
    // Build a map for func values.
    final funcMap = <(int, int), int>{};
    for (final obs in obstacles) {
      funcMap[(obs.row, obs.col)] = obs.func;
    }

    const boardSize = 8;
    return AspectRatio(
      aspectRatio: 1.0,
      child: GridView.builder(
        physics: const NeverScrollableScrollPhysics(),
        gridDelegate: const SliverGridDelegateWithFixedCrossAxisCount(
          crossAxisCount: boardSize,
          mainAxisSpacing: 2,
          crossAxisSpacing: 2,
        ),
        itemCount: boardSize * boardSize,
        itemBuilder: (context, index) {
          final row = index ~/ boardSize;
          final col = index % boardSize;
          final isObstacle = obstacleSet.contains((row, col));
          final func = funcMap[(row, col)] ?? 0;

          final obstacleColor = func >= 10
              ? theme.wallColor
              : theme.obstacleColor(func);

          return Container(
            decoration: BoxDecoration(
              color: isObstacle
                  ? obstacleColor
                  : Colors.white.withValues(alpha: 0.04),
              borderRadius: BorderRadius.circular(3),
              border: isObstacle
                  ? Border.all(
                      color: Colors.white.withValues(alpha: 0.3),
                      width: 0.5,
                    )
                  : null,
            ),
            child: isObstacle && func > 0
                ? Center(
                    child: Text(
                      theme.specialSymbol(func),
                      style: const TextStyle(fontSize: 10, color: Colors.white),
                    ),
                  )
                : null,
          );
        },
      ),
    );
  }
}
