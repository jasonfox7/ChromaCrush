/// Campaign map — sectioned level grid with checkpoint reward bars.
///
/// Levels grouped into sections of 10, each tinted by a gem color.
/// Checkpoint levels (every 10th) render as full-width reward bars.
/// Fetches progress from the campaign API.
library;

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../config/visual_theme_service.dart';
import '../../models/backend_contract.dart';
import '../../services/api_client.dart';
import '../../theme/chroma_theme.dart';
import '../../theme/glass_panel.dart';

class CampaignScreen extends StatefulWidget {
  const CampaignScreen({super.key});

  @override
  State<CampaignScreen> createState() => _CampaignScreenState();
}

class _CampaignScreenState extends State<CampaignScreen> {
  bool _loading = true;
  String? _error;
  int _campaignLevel = 1;
  List<CampaignLevelSummary> _levels = [];
  final _scrollController = ScrollController();

  @override
  void initState() {
    super.initState();
    _fetchLevels();
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  Future<void> _fetchLevels() async {
    try {
      final api = context.read<ApiClientBase>();
      final result = await api.getCampaignLevels();
      if (!mounted) return;
      if (result.data != null) {
        setState(() {
          _campaignLevel = result.data!.campaignLevel;
          _levels = result.data!.levels;
          _loading = false;
        });
        _scrollToCurrentLevel();
      } else {
        setState(() {
          _error = 'Failed to load levels';
          _loading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = 'Failed to load levels: $e';
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
              // Header row.
              Padding(
                padding: const EdgeInsets.symmetric(
                  horizontal: 16,
                  vertical: 12,
                ),
                child: Row(
                  children: [
                    GestureDetector(
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
                    const SizedBox(width: 12),
                    Text(
                      'CAMPAIGN',
                      style: ChromaText.headlineMedium.copyWith(
                        color: ChromaColors.textPrimary,
                        letterSpacing: 4,
                      ),
                    ),
                    const Spacer(),
                    GlassPanel(
                      borderRadius: 16,
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 6,
                      ),
                      child: Text(
                        'Level $_campaignLevel',
                        style: ChromaText.labelSmall.copyWith(
                          color: ChromaColors.accentGlow,
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              // Card ability warning.
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 8,
                  ),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFCC00).withValues(alpha: 0.08),
                    borderRadius: BorderRadius.circular(10),
                    border: Border.all(
                      color: const Color(0xFFFFCC00).withValues(alpha: 0.2),
                    ),
                  ),
                  child: Row(
                    children: [
                      Icon(
                        CupertinoIcons.exclamationmark_triangle_fill,
                        color: const Color(0xFFFFCC00).withValues(alpha: 0.7),
                        size: 16,
                      ),
                      const SizedBox(width: 8),
                      Expanded(
                        child: Text(
                          'Campaign mode may prove difficult '
                          'without card abilities.',
                          style: TextStyle(
                            color:
                                const Color(0xFFFFCC00).withValues(alpha: 0.7),
                            fontSize: 11,
                            fontWeight: FontWeight.w500,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 8),

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
                        : _buildSections(),
              ),
            ],
          ),
        ),
      ),
    );
  }

  void _scrollToCurrentLevel() {
    // Wait one frame for the ListView to lay out.
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!mounted || !_scrollController.hasClients) return;
      // Each section is ~10 levels. Estimate ~200px per section.
      final sectionIndex = (_campaignLevel - 1) ~/ 10;
      const estimatedSectionHeight = 200.0;
      final target = sectionIndex * estimatedSectionHeight;
      final maxScroll = _scrollController.position.maxScrollExtent;
      _scrollController.jumpTo(target.clamp(0.0, maxScroll));
    });
  }

  Widget _buildSections() {
    final theme = context.read<VisualThemeBase>();

    // Group levels into sections of 10.
    final sectionCount = (_levels.length / 10).ceil();

    return ListView.builder(
      controller: _scrollController,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      itemCount: sectionCount,
      itemBuilder: (context, sectionIndex) {
        final startIndex = sectionIndex * 10;
        final endIndex = (startIndex + 10).clamp(0, _levels.length);
        final sectionLevels = _levels.sublist(startIndex, endIndex);

        // Split into regular levels and checkpoint.
        final regularLevels = <CampaignLevelSummary>[];
        CampaignLevelSummary? checkpoint;
        for (final level in sectionLevels) {
          if (level.isCheckpoint) {
            checkpoint = level;
          } else {
            regularLevels.add(level);
          }
        }

        // Section gem color — cycle through 6 gem colors.
        final gemColor = theme.gemColor((sectionIndex % 6) + 1);

        return _LevelSection(
          sectionIndex: sectionIndex,
          regularLevels: regularLevels,
          checkpoint: checkpoint,
          gemColor: gemColor,
          campaignLevel: _campaignLevel,
          onLevelTap: (levelNum) => context.push('/campaign/level/$levelNum'),
        );
      },
    );
  }
}

// ---------------------------------------------------------------------------
// Level section — group of 9 tiles + checkpoint bar
// ---------------------------------------------------------------------------

class _LevelSection extends StatelessWidget {
  const _LevelSection({
    required this.sectionIndex,
    required this.regularLevels,
    required this.checkpoint,
    required this.gemColor,
    required this.campaignLevel,
    required this.onLevelTap,
  });

  final int sectionIndex;
  final List<CampaignLevelSummary> regularLevels;
  final CampaignLevelSummary? checkpoint;
  final Color gemColor;
  final int campaignLevel;
  final ValueChanged<int> onLevelTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16),
      decoration: BoxDecoration(
        color: gemColor.withValues(alpha: 0.04),
        borderRadius: BorderRadius.circular(16),
        border: Border(
          left: BorderSide(
            color: gemColor.withValues(alpha: 0.3),
            width: 3,
          ),
        ),
      ),
      child: Padding(
        padding: const EdgeInsets.all(10),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Regular level tiles in a 5-column wrap.
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: regularLevels.map((level) {
                final isCurrent = level.level == campaignLevel;
                final completed = level.level < campaignLevel;
                return SizedBox(
                  width: _tileSize(context),
                  height: _tileSize(context),
                  child: _LevelTile(
                    levelNumber: level.level,
                    unlocked: level.unlocked,
                    isCheckpoint: false,
                    isCurrent: isCurrent,
                    completed: completed,
                    onTap: level.unlocked
                        ? () => onLevelTap(level.level)
                        : null,
                  ),
                );
              }).toList(),
            ),

            // Checkpoint bar.
            if (checkpoint != null) ...[
              const SizedBox(height: 10),
              _CheckpointBar(
                level: checkpoint!,
                gemColor: gemColor,
                isCurrent: checkpoint!.level == campaignLevel,
                completed: checkpoint!.level < campaignLevel,
                onTap: checkpoint!.unlocked
                    ? () => onLevelTap(checkpoint!.level)
                    : null,
              ),
            ],
          ],
        ),
      ),
    );
  }

  double _tileSize(BuildContext context) {
    // 5 columns with spacing, inside section padding + screen padding.
    final available = MediaQuery.of(context).size.width - 32 - 20 - 3;
    return (available - 4 * 8) / 5;
  }
}

// ---------------------------------------------------------------------------
// Checkpoint bar — full-width with reward display
// ---------------------------------------------------------------------------

const _rarityColors = <String, Color>{
  'common': Color(0xFF8A8A8A),
  'rare': Color(0xFF4FC3F7),
  'epic': Color(0xFFCE93D8),
  'legendary': Color(0xFFFFD54F),
};

class _CheckpointBar extends StatelessWidget {
  const _CheckpointBar({
    required this.level,
    required this.gemColor,
    required this.isCurrent,
    required this.completed,
    this.onTap,
  });

  final CampaignLevelSummary level;
  final Color gemColor;
  final bool isCurrent;
  final bool completed;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final unlocked = level.unlocked;
    final borderColor = isCurrent
        ? ChromaColors.accentGlow
        : unlocked
            ? const Color(0xFFFFD700)
            : Colors.white.withValues(alpha: 0.08);

    return GestureDetector(
      onTap: onTap,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
        decoration: BoxDecoration(
          color: unlocked
              ? gemColor.withValues(alpha: 0.08)
              : Colors.white.withValues(alpha: 0.02),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: borderColor,
            width: isCurrent ? 2 : 1,
          ),
        ),
        child: Row(
          children: [
            // Star + level number.
            Icon(
              completed
                  ? CupertinoIcons.checkmark_seal_fill
                  : CupertinoIcons.star_fill,
              color: unlocked
                  ? const Color(0xFFFFD700)
                  : Colors.white.withValues(alpha: 0.15),
              size: 20,
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'CHECKPOINT ${level.level}',
                    style: TextStyle(
                      color: unlocked
                          ? (isCurrent
                              ? ChromaColors.accentGlow
                              : Colors.white)
                          : Colors.white.withValues(alpha: 0.25),
                      fontSize: 13,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 2,
                    ),
                  ),
                  if (level.heartCost > 0)
                    Padding(
                      padding: const EdgeInsets.only(top: 2),
                      child: Row(
                        children: [
                          Icon(
                            CupertinoIcons.heart_fill,
                            color: unlocked
                                ? const Color(0xFFFF2D55)
                                : Colors.white.withValues(alpha: 0.15),
                            size: 10,
                          ),
                          const SizedBox(width: 3),
                          Text(
                            '${level.heartCost}',
                            style: TextStyle(
                              color: unlocked
                                  ? Colors.white54
                                  : Colors.white.withValues(alpha: 0.15),
                              fontSize: 10,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              ),
            ),

            // Reward display.
            if (level.reward != null) _buildReward(level.reward!),

            // Lock icon for locked checkpoints.
            if (!unlocked)
              Padding(
                padding: const EdgeInsets.only(left: 8),
                child: Icon(
                  CupertinoIcons.lock_fill,
                  color: Colors.white.withValues(alpha: 0.15),
                  size: 16,
                ),
              ),
          ],
        ),
      ),
    );
  }

  Widget _buildReward(Map<String, dynamic> reward) {
    final type = reward['type'] as String? ?? '';
    final rarity = reward['rarity'] as String? ?? 'common';
    final count = reward['count'] as int? ?? 1;
    final amount = reward['amount'] as int? ?? count;
    final rarityColor = _rarityColors[rarity] ?? const Color(0xFF8A8A8A);

    final IconData icon;
    final String label;
    final Color badgeColor;

    switch (type) {
      case 'card_pack':
        icon = CupertinoIcons.rectangle_stack;
        label = count > 1
            ? '$count\u00D7 ${_capitalize(rarity)} Pack'
            : '${_capitalize(rarity)} Pack';
        badgeColor = rarityColor;
      case 'gold':
        icon = CupertinoIcons.circle_fill;
        label = '${_formatNumber(amount)} Gold';
        badgeColor = const Color(0xFFFFD700);
      case 'mega_gem':
        icon = CupertinoIcons.burst;
        label = count > 1 ? '$count\u00D7 Mega' : 'Mega Gem';
        badgeColor = ChromaColors.accent;
      case 'heart':
        icon = CupertinoIcons.heart_fill;
        label = '$count Heart${count > 1 ? 's' : ''}';
        badgeColor = const Color(0xFFFF2D55);
      default:
        icon = CupertinoIcons.gift;
        label = 'Reward';
        badgeColor = rarityColor;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: badgeColor.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(8),
        border: Border.all(
          color: badgeColor.withValues(alpha: 0.3),
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, color: badgeColor, size: 14),
          const SizedBox(width: 5),
          Text(
            label,
            style: TextStyle(
              color: badgeColor,
              fontSize: 11,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }

  static String _capitalize(String s) =>
      s.isEmpty ? s : '${s[0].toUpperCase()}${s.substring(1)}';

  static String _formatNumber(int n) => n.toString().replaceAllMapped(
        RegExp(r'(\d)(?=(\d{3})+(?!\d))'),
        (m) => '${m[1]},',
      );
}

// ---------------------------------------------------------------------------
// Level tile — individual level cell
// ---------------------------------------------------------------------------

class _LevelTile extends StatelessWidget {
  const _LevelTile({
    required this.levelNumber,
    required this.unlocked,
    required this.isCheckpoint,
    required this.isCurrent,
    required this.completed,
    this.onTap,
  });

  final int levelNumber;
  final bool unlocked;
  final bool isCheckpoint;
  final bool isCurrent;
  final bool completed;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final borderColor = isCurrent
        ? ChromaColors.accentGlow
        : unlocked
            ? ChromaColors.glassBorder
            : Colors.white.withValues(alpha: 0.05);

    final bgColor = isCurrent
        ? ChromaColors.accent.withValues(alpha: 0.25)
        : completed
            ? Colors.white.withValues(alpha: 0.08)
            : unlocked
                ? ChromaColors.glassWhite
                : Colors.white.withValues(alpha: 0.02);

    return GestureDetector(
      onTap: onTap,
      child: Container(
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: BorderRadius.circular(10),
          border: Border.all(
            color: borderColor,
            width: isCurrent ? 2 : 1,
          ),
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            if (completed)
              Icon(
                CupertinoIcons.checkmark_alt,
                color: ChromaColors.accentGlow.withValues(alpha: 0.7),
                size: 12,
              ),
            Text(
              '$levelNumber',
              style: TextStyle(
                color: unlocked
                    ? (isCurrent ? ChromaColors.accentGlow : Colors.white)
                    : Colors.white.withValues(alpha: 0.2),
                fontSize: isCurrent ? 16 : 13,
                fontWeight: isCurrent ? FontWeight.w900 : FontWeight.w600,
              ),
            ),
            if (!unlocked)
              Icon(
                CupertinoIcons.lock_fill,
                color: Colors.white.withValues(alpha: 0.15),
                size: 10,
              ),
          ],
        ),
      ),
    );
  }
}
