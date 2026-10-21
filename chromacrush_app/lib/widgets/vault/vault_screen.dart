/// Vault screen — card collection with equip slots, horizontal carousel, and merge.
///
/// Layout (top to bottom):
///   1. Back button (top-left) + title
///   2. Three equip slots (horizontal row) + merge button
///   3. Horizontal card carousel (swipe left/right to browse owned cards)
///
/// Gestures:
///   - Drag up on carousel card → equip into first available slot
///   - Drag down on equip slot → unequip (return to carousel)
///   - Tap merge button → merge 3 same-rarity equipped cards
library;

import 'dart:ui' show PointerDeviceKind;

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../models/backend_contract.dart';
import '../../services/api_client.dart';
import '../../services/session_manager.dart';
import '../../theme/chroma_theme.dart';
import '../shell/starfield_background.dart';
import 'card_widget.dart';
import 'vault_help_overlay.dart';

class VaultScreen extends StatefulWidget {
  const VaultScreen({super.key});

  @override
  State<VaultScreen> createState() => _VaultScreenState();
}

/// Sort modes for vault cards.
enum _SortMode { rarity, name, value }

/// Rarity order for sorting (ascending).
const _rarityOrder = {'common': 0, 'rare': 1, 'epic': 2, 'legendary': 3};

class _VaultScreenState extends State<VaultScreen> {
  bool _loading = true;
  String? _error;
  List<PlayerCardResponse> _ownedCards = [];
  EquippedLoadoutResponse? _loadout;
  int _carouselIndex = 0;
  bool _merging = false;
  bool _exchanging = false;
  _SortMode _sortMode = _SortMode.rarity;
  String? _filterRarity; // null = show all
  bool _previewExpanded = false;
  bool _showHelp = false;

  @override
  void initState() {
    super.initState();
    _fetchCards();
  }

  Future<void> _fetchCards() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final api = context.read<ApiClientBase>();
      final session = context.read<SessionManager>();

      final cardsResp = await api.getPlayerCards(limit: 200);
      final loadoutResp = await api.getEquippedCards();

      if (!mounted) return;

      if (cardsResp.data != null) {
        session.updateOwnedCards(cardsResp.data!.cards);
      }
      if (loadoutResp.data != null) {
        session.updateEquippedLoadout(loadoutResp.data!);
      }

      setState(() {
        _ownedCards = cardsResp.data?.cards ?? [];
        _loadout = loadoutResp.data;
        _loading = false;
      });
    } catch (e) {
      if (!mounted) return;
      setState(() {
        _error = e.toString();
        _loading = false;
      });
    }
  }

  /// Cards not in equip slots (position > 3).
  List<PlayerCardResponse> get _vaultCards =>
      _ownedCards.where((c) => c.position > 3).toList();

  /// Vault cards with rarity filter and sort applied.
  List<PlayerCardResponse> get _filteredSortedVaultCards {
    var cards = _vaultCards;

    // Apply rarity filter.
    if (_filterRarity != null) {
      cards = cards.where((c) => c.definition.rarity == _filterRarity).toList();
    }

    // Apply sort.
    switch (_sortMode) {
      case _SortMode.rarity:
        cards.sort((a, b) {
          final ra = _rarityOrder[a.definition.rarity] ?? 0;
          final rb = _rarityOrder[b.definition.rarity] ?? 0;
          if (ra != rb) return rb.compareTo(ra); // Highest rarity first.
          return a.definition.name.compareTo(b.definition.name);
        });
      case _SortMode.name:
        cards.sort((a, b) => a.definition.name.compareTo(b.definition.name));
      case _SortMode.value:
        cards.sort(
          (a, b) => b.definition.baseValue.compareTo(a.definition.baseValue),
        );
    }

    return cards;
  }

  void _cycleSortMode() {
    setState(() {
      final modes = _SortMode.values;
      _sortMode = modes[(_sortMode.index + 1) % modes.length];
      _carouselIndex = 0;
    });
  }

  void _toggleRarityFilter(String? rarity) {
    setState(() {
      _filterRarity = _filterRarity == rarity ? null : rarity;
      _carouselIndex = 0;
    });
  }

  /// Equipped cards sorted by position.
  List<PlayerCardResponse?> get _equippedSlots {
    final equipped = _loadout?.cards ?? [];
    return List.generate(3, (i) {
      final slot = i + 1;
      final match = equipped.where((c) => c.position == slot);
      return match.isNotEmpty ? match.first : null;
    });
  }

  /// Whether merge is allowed: all 3 slots filled, same rarity, not legendary.
  bool get _canMerge {
    final slots = _equippedSlots;
    if (slots.any((s) => s == null)) return false;
    final rarities = slots.map((s) => s!.definition.rarity).toSet();
    if (rarities.length != 1) return false;
    return rarities.first != 'legendary';
  }

  String get _mergeLabel {
    final slots = _equippedSlots;
    if (slots.any((s) => s == null)) return 'FILL SLOTS';
    final rarities = slots.map((s) => s!.definition.rarity).toSet();
    if (rarities.length != 1) return 'MATCH RARITY';
    if (rarities.first == 'legendary') return 'MAX TIER';
    return 'MERGE';
  }

  /// Whether exchange is allowed: all 3 slots filled (any rarity mix).
  bool get _canExchange {
    final slots = _equippedSlots;
    return slots.every((s) => s != null);
  }

  /// Preview gold amount from selling equipped cards (40% of base_value each).
  int get _exchangeGoldPreview {
    final slots = _equippedSlots;
    if (!_canExchange) return 0;
    return slots.fold<int>(
      0,
      (sum, card) => sum + (card!.definition.baseValue * 0.4).round(),
    );
  }

  String get _exchangeLabel {
    if (!_canExchange) return 'FILL SLOTS';
    return 'EXCHANGE';
  }

  Future<void> _equipCard(PlayerCardResponse card) async {
    // Find first empty slot.
    final slots = _equippedSlots;
    int targetSlot = -1;
    for (int i = 0; i < 3; i++) {
      if (slots[i] == null) {
        targetSlot = i + 1;
        break;
      }
    }
    if (targetSlot == -1) return; // All slots full.

    try {
      final api = context.read<ApiClientBase>();
      await api.equipCard(
        CardEquipRequest(cardInstanceId: card.id, slot: targetSlot),
      );
      await _fetchCards();
    } catch (_) {}
  }

  Future<void> _unequipCard(PlayerCardResponse card) async {
    try {
      final api = context.read<ApiClientBase>();
      await api.unequipCard(CardUnequipRequest(cardInstanceId: card.id));
      await _fetchCards();
    } catch (_) {}
  }

  Future<void> _confirmMerge() async {
    if (!_canMerge || _merging) return;
    final slots = _equippedSlots;
    final rarity = slots.first!.definition.rarity.toUpperCase();
    final confirmed = await showCupertinoDialog<bool>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: const Text('Merge Cards'),
        content: Text('Merge 3 $rarity cards into 1 higher-tier card?'),
        actions: [
          CupertinoDialogAction(
            isDefaultAction: true,
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          CupertinoDialogAction(
            isDestructiveAction: true,
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Merge'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;

    setState(() => _merging = true);
    try {
      final api = context.read<ApiClientBase>();
      await api.mergeCards();
      await _fetchCards();
    } catch (_) {}
    if (!mounted) return;
    setState(() => _merging = false);
  }

  Future<void> _confirmExchange() async {
    if (!_canExchange || _exchanging) return;
    final gold = _exchangeGoldPreview;
    final confirmed = await showCupertinoDialog<bool>(
      context: context,
      builder: (ctx) => CupertinoAlertDialog(
        title: const Text('Exchange Cards'),
        content: Text(
          'Sell 3 equipped cards for ${gold}g?\nThis cannot be undone.',
        ),
        actions: [
          CupertinoDialogAction(
            isDefaultAction: true,
            onPressed: () => Navigator.pop(ctx, false),
            child: const Text('Cancel'),
          ),
          CupertinoDialogAction(
            isDestructiveAction: true,
            onPressed: () => Navigator.pop(ctx, true),
            child: const Text('Sell'),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;

    setState(() => _exchanging = true);
    try {
      final api = context.read<ApiClientBase>();
      final result = await api.sellEquippedCards();
      if (result.data != null && mounted) {
        context.read<SessionManager>().updateGoldBalance(
          result.data!.newBalance,
        );
      }
      await _fetchCards();
    } catch (_) {}
    if (!mounted) return;
    setState(() => _exchanging = false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(gradient: ChromaGradients.screen),
        child: SafeArea(
          child: Stack(
            children: [
              const Positioned.fill(child: StarfieldBackground()),

              // Subtle radial glow.
              Center(
                child: Container(
                  width: 300,
                  height: 300,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: RadialGradient(
                      colors: [
                        ChromaColors.accent.withValues(alpha: 0.04),
                        Colors.transparent,
                      ],
                    ),
                  ),
                ),
              ),

              // Back button (top-left).
              Positioned(
                top: 16,
                left: 16,
                child: IconButton(
                  icon: const Icon(
                    CupertinoIcons.back,
                    color: Colors.white54,
                    size: 28,
                  ),
                  onPressed: () => context.pop(),
                ),
              ),

              // Main content.
              Column(
                children: [
                  const SizedBox(height: 20),

                  // Title.
                  ShaderMask(
                    shaderCallback: (bounds) =>
                        ChromaGradients.accent.createShader(bounds),
                    child: const Text(
                      'CARD VAULT',
                      style: TextStyle(
                        color: Colors.white,
                        fontSize: 24,
                        fontWeight: FontWeight.w900,
                        letterSpacing: 4,
                      ),
                    ),
                  ),

                  const SizedBox(height: 16),

                  // Equip slots (centered).
                  _buildEquipRow(),

                  const SizedBox(height: 10),

                  // Merge + Exchange buttons (side-by-side under equip slots).
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      _ActionButton(
                        enabled: _canMerge && !_merging,
                        label: _merging ? '...' : _mergeLabel,
                        icon: CupertinoIcons.arrow_merge,
                        onPressed: _confirmMerge,
                      ),
                      const SizedBox(width: 12),
                      _ActionButton(
                        enabled: _canExchange && !_exchanging,
                        label: _exchanging ? '...' : _exchangeLabel,
                        subtitle: _canExchange
                            ? '+${_exchangeGoldPreview}g'
                            : null,
                        icon: CupertinoIcons.money_dollar_circle,
                        onPressed: _confirmExchange,
                      ),
                    ],
                  ),

                  const SizedBox(height: 8),

                  // Experimental warning.
                  Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 32),
                    child: Text(
                      'Advanced Strategy: Overlapping effects follow priority logic.'
                      'Some specials such as Heavy Gravity in position 3 would '
                      'override Heavenly Gift in position 1.',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        color: Colors.white.withValues(alpha: 0.25),
                        fontSize: 9,
                        fontWeight: FontWeight.w400,
                        height: 1.4,
                      ),
                    ),
                  ),

                  const SizedBox(height: 10),

                  // Divider label.
                  Text(
                    'COLLECTION',
                    style: ChromaText.labelSmall.copyWith(
                      color: ChromaColors.textTertiary,
                      letterSpacing: 3,
                    ),
                  ),

                  const SizedBox(height: 6),

                  // Sort + rarity filter row.
                  _buildFilterRow(),

                  const SizedBox(height: 4),

                  // Full carousel + swipe-down hint.
                  Expanded(child: _buildBody()),
                  if (_filteredSortedVaultCards.isNotEmpty)
                    Padding(
                      padding: const EdgeInsets.only(top: 4, bottom: 8),
                      child: Text(
                        '\u25BC  swipe down to preview',
                        style: TextStyle(
                          color: Colors.white.withValues(alpha: 0.2),
                          fontSize: 9,
                          letterSpacing: 1,
                        ),
                      ),
                    ),
                ],
              ),

              // Help button (top-right).
              Positioned(
                top: 16,
                right: 16,
                child: _GlowingHelpButton(
                  onTap: () => setState(() => _showHelp = true),
                ),
              ),

              // Help overlay.
              if (_showHelp)
                VaultHelpOverlay(
                  onDismiss: () => setState(() => _showHelp = false),
                ),

              // Fullscreen card preview overlay — slides up from bottom.
              Positioned.fill(
                child: IgnorePointer(
                  ignoring: !_previewExpanded,
                  child: ClipRect(
                    child: AnimatedSlide(
                      offset: Offset(0, _previewExpanded ? 0.0 : 1.0),
                      duration: const Duration(milliseconds: 350),
                      curve: _previewExpanded
                          ? Curves.easeOutCubic
                          : Curves.easeInCubic,
                      child: Container(
                        color: Colors.black.withValues(alpha: 0.92),
                        child: Column(
                          children: [
                            const SizedBox(height: 8),
                            // Collapse handle — tap to close.
                            GestureDetector(
                              onTap: () =>
                                  setState(() => _previewExpanded = false),
                              behavior: HitTestBehavior.opaque,
                              child: Padding(
                                padding: const EdgeInsets.symmetric(
                                  vertical: 4,
                                  horizontal: 40,
                                ),
                                child: Container(
                                  width: 36,
                                  height: 4,
                                  decoration: BoxDecoration(
                                    color: Colors.white.withValues(alpha: 0.2),
                                    borderRadius: BorderRadius.circular(2),
                                  ),
                                ),
                              ),
                            ),
                            const SizedBox(height: 4),
                            // Mini carousel.
                            SizedBox(
                              height: 90,
                              child: _buildCompactCarousel(),
                            ),
                            // Large card preview fills remaining space.
                            Expanded(child: _buildActiveCardPreview()),
                          ],
                        ),
                      ),
                    ),
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildEquipRow() {
    final slots = _equippedSlots;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          for (int i = 0; i < 3; i++) ...[
            if (i > 0) const SizedBox(width: 8),
            _EquipSlot(
              card: slots[i],
              slotIndex: i + 1,
              onUnequip: slots[i] != null
                  ? () => _unequipCard(slots[i]!)
                  : null,
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildActiveCardPreview() {
    final displayCards = _filteredSortedVaultCards;
    if (displayCards.isEmpty || _loading || _error != null) {
      return const SizedBox.shrink();
    }
    final idx = _carouselIndex.clamp(0, displayCards.length - 1);
    final card = displayCards[idx];

    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onPanEnd: (details) {
        final dx = details.velocity.pixelsPerSecond.dx;
        final dy = details.velocity.pixelsPerSecond.dy;

        // Pick dominant axis.
        if (dx.abs() > dy.abs()) {
          // Horizontal — change card.
          if (dx < -200 && idx < displayCards.length - 1) {
            setState(() => _carouselIndex = idx + 1);
          } else if (dx > 200 && idx > 0) {
            setState(() => _carouselIndex = idx - 1);
          }
        } else {
          // Vertical — close preview.
          if (dy.abs() > 100) {
            setState(() => _previewExpanded = false);
          }
        }
      },
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 48, vertical: 8),
        child: Column(
          children: [
            Padding(
              padding: const EdgeInsets.only(bottom: 6),
              child: Text(
                '\u25C0  swipe  \u25B6     \u25B2  close  \u25BC',
                style: TextStyle(
                  color: Colors.white.withValues(alpha: 0.2),
                  fontSize: 9,
                  letterSpacing: 1,
                ),
              ),
            ),
            Expanded(
              child: Center(child: CardWidget(card: card)),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCompactCarousel() {
    final displayCards = _filteredSortedVaultCards;
    if (displayCards.isEmpty) return const SizedBox.shrink();
    return _CardCarousel(
      cards: displayCards,
      currentIndex: _carouselIndex.clamp(0, displayCards.length - 1),
      onIndexChanged: (i) => setState(() => _carouselIndex = i),
      onSwipeUp: _equipCard,
      compact: true,
    );
  }

  Widget _buildFilterRow() {
    const rarities = ['common', 'rare', 'epic', 'legendary'];
    const rarityLabels = {
      'common': 'C',
      'rare': 'R',
      'epic': 'E',
      'legendary': 'L',
    };
    const rarityColors = {
      'common': Color(0xFF8A8A8A),
      'rare': Color(0xFF4FC3F7),
      'epic': Color(0xFFCE93D8),
      'legendary': Color(0xFFFFD54F),
    };

    final sortLabel = switch (_sortMode) {
      _SortMode.rarity => 'RARITY',
      _SortMode.name => 'NAME',
      _SortMode.value => 'VALUE',
    };

    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 24),
      child: Row(
        children: [
          // Sort toggle button.
          GestureDetector(
            onTap: _cycleSortMode,
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: Colors.white.withValues(alpha: 0.2)),
                color: Colors.white.withValues(alpha: 0.06),
              ),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    CupertinoIcons.sort_down,
                    size: 12,
                    color: Colors.white.withValues(alpha: 0.6),
                  ),
                  const SizedBox(width: 4),
                  Text(
                    sortLabel,
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.6),
                      fontSize: 9,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1,
                    ),
                  ),
                ],
              ),
            ),
          ),

          const Spacer(),

          // Rarity filter chips.
          for (final rarity in rarities) ...[
            GestureDetector(
              onTap: () => _toggleRarityFilter(rarity),
              child: Container(
                width: 28,
                height: 24,
                margin: const EdgeInsets.only(left: 6),
                decoration: BoxDecoration(
                  borderRadius: BorderRadius.circular(6),
                  border: Border.all(
                    color: _filterRarity == rarity
                        ? rarityColors[rarity]!
                        : Colors.white.withValues(alpha: 0.12),
                    width: _filterRarity == rarity ? 1.5 : 1,
                  ),
                  color: _filterRarity == rarity
                      ? rarityColors[rarity]!.withValues(alpha: 0.2)
                      : Colors.white.withValues(alpha: 0.04),
                ),
                alignment: Alignment.center,
                child: Text(
                  rarityLabels[rarity]!,
                  style: TextStyle(
                    color: _filterRarity == rarity
                        ? rarityColors[rarity]!
                        : Colors.white.withValues(alpha: 0.4),
                    fontSize: 10,
                    fontWeight: FontWeight.w800,
                  ),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }

  Widget _buildBody() {
    if (_loading) {
      return const Center(
        child: CupertinoActivityIndicator(color: Colors.white54),
      );
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              'Failed to load cards',
              style: ChromaText.bodyMedium.copyWith(
                color: ChromaColors.textTertiary,
              ),
            ),
            const SizedBox(height: 12),
            GestureDetector(
              onTap: _fetchCards,
              child: const Text(
                'TAP TO RETRY',
                style: TextStyle(
                  color: ChromaColors.accentGlow,
                  fontSize: 12,
                  letterSpacing: 2,
                ),
              ),
            ),
          ],
        ),
      );
    }

    if (_vaultCards.isEmpty && _ownedCards.isEmpty) {
      return Center(
        child: Text(
          'No cards yet.\nPlay matches to earn cards!',
          textAlign: TextAlign.center,
          style: ChromaText.bodyMedium.copyWith(
            color: ChromaColors.textTertiary,
          ),
        ),
      );
    }

    if (_vaultCards.isEmpty) {
      return Center(
        child: Text(
          'All cards equipped.',
          style: ChromaText.bodyMedium.copyWith(
            color: ChromaColors.textTertiary,
          ),
        ),
      );
    }

    final displayCards = _filteredSortedVaultCards;

    if (displayCards.isEmpty) {
      return Center(
        child: Text(
          'No ${_filterRarity ?? ''} cards.',
          style: ChromaText.bodyMedium.copyWith(
            color: ChromaColors.textTertiary,
          ),
        ),
      );
    }

    // Horizontal card carousel.
    return _CardCarousel(
      cards: displayCards,
      currentIndex: _carouselIndex.clamp(0, displayCards.length - 1),
      onIndexChanged: (i) => setState(() => _carouselIndex = i),
      onSwipeUp: _equipCard,
      onSwipeDown: (_) => setState(() => _previewExpanded = true),
      compact: false,
    );
  }
}

// ---------------------------------------------------------------------------
// Equip slot widget — drag down to unequip
// ---------------------------------------------------------------------------

class _EquipSlot extends StatefulWidget {
  const _EquipSlot({
    required this.card,
    required this.slotIndex,
    this.onUnequip,
  });
  final PlayerCardResponse? card;
  final int slotIndex;
  final VoidCallback? onUnequip;

  @override
  State<_EquipSlot> createState() => _EquipSlotState();
}

class _EquipSlotState extends State<_EquipSlot>
    with SingleTickerProviderStateMixin {
  double _dragOffset = 0;
  static const _triggerThreshold = 60.0;

  late final AnimationController _snapBack;

  @override
  void initState() {
    super.initState();
    _snapBack =
        AnimationController(
          vsync: this,
          duration: const Duration(milliseconds: 200),
        )..addListener(() {
          setState(() {
            _dragOffset = _dragOffset * (1 - _snapBack.value);
          });
        });
  }

  @override
  void dispose() {
    _snapBack.dispose();
    super.dispose();
  }

  bool get _pastThreshold => _dragOffset > _triggerThreshold;

  @override
  Widget build(BuildContext context) {
    const slotSize = 80.0;

    if (widget.card == null) {
      // Empty slot placeholder.
      return Container(
        width: slotSize,
        height: slotSize * 1.4, // 5:7 ratio
        decoration: BoxDecoration(
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: Colors.white.withValues(alpha: 0.1),
            width: 1.5,
          ),
        ),
        child: Center(
          child: Text(
            '${widget.slotIndex}',
            style: TextStyle(
              color: Colors.white.withValues(alpha: 0.15),
              fontSize: 24,
              fontWeight: FontWeight.bold,
            ),
          ),
        ),
      );
    }

    // Filled slot — drag down to unequip.
    return GestureDetector(
      onVerticalDragUpdate: (details) {
        if (widget.onUnequip == null) return;
        setState(() {
          // Only allow dragging downward.
          _dragOffset = (_dragOffset + details.delta.dy).clamp(0.0, 120.0);
        });
      },
      onVerticalDragEnd: (_) {
        if (_pastThreshold && widget.onUnequip != null) {
          _dragOffset = 0;
          widget.onUnequip!();
        } else {
          // Animate snap-back.
          _snapBack.forward(from: 0);
        }
      },
      onVerticalDragCancel: () {
        _snapBack.forward(from: 0);
      },
      child: Transform.translate(
        offset: Offset(0, _dragOffset),
        child: AnimatedOpacity(
          opacity: _pastThreshold ? 0.5 : 1.0,
          duration: const Duration(milliseconds: 100),
          child: SizedBox(
            width: slotSize,
            height: slotSize * 1.4, // 5:7 ratio
            child: Stack(
              clipBehavior: Clip.none,
              children: [
                CardWidget(card: widget.card!, compact: true),
                // Drag hint arrow.
                if (_dragOffset > 10)
                  Positioned(
                    bottom: -16,
                    left: 0,
                    right: 0,
                    child: Icon(
                      CupertinoIcons.arrow_down,
                      size: 14,
                      color: _pastThreshold
                          ? ChromaColors.accentGlow
                          : Colors.white38,
                    ),
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Action button (Merge / Exchange)
// ---------------------------------------------------------------------------

class _ActionButton extends StatelessWidget {
  const _ActionButton({
    required this.enabled,
    required this.label,
    required this.icon,
    required this.onPressed,
    this.subtitle,
  });
  final bool enabled;
  final String label;
  final IconData icon;
  final VoidCallback onPressed;
  final String? subtitle;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: enabled ? onPressed : null,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        decoration: BoxDecoration(
          gradient: enabled ? ChromaGradients.accent : null,
          color: enabled ? null : ChromaColors.bgSurface,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: enabled
                ? Colors.transparent
                : Colors.white.withValues(alpha: 0.1),
          ),
          boxShadow: enabled
              ? [
                  BoxShadow(
                    color: ChromaColors.accent.withValues(alpha: 0.3),
                    blurRadius: 12,
                    spreadRadius: 1,
                  ),
                ]
              : null,
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              color: enabled ? Colors.white : Colors.white24,
              size: 18,
            ),
            const SizedBox(height: 3),
            Text(
              label,
              style: TextStyle(
                color: enabled ? Colors.white : Colors.white24,
                fontSize: 9,
                fontWeight: FontWeight.w700,
                letterSpacing: 1,
              ),
            ),
            if (subtitle != null) ...[
              const SizedBox(height: 2),
              Text(
                subtitle!,
                style: TextStyle(
                  color: enabled
                      ? const Color(0xFFFFD700)
                      : Colors.white.withValues(alpha: 0.15),
                  fontSize: 9,
                  fontWeight: FontWeight.w600,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Horizontal card carousel — drag up to equip
// ---------------------------------------------------------------------------

class _CardCarousel extends StatefulWidget {
  const _CardCarousel({
    required this.cards,
    required this.currentIndex,
    required this.onIndexChanged,
    required this.onSwipeUp,
    this.onSwipeDown,
    this.compact = false,
  });
  final List<PlayerCardResponse> cards;
  final int currentIndex;
  final ValueChanged<int> onIndexChanged;
  final ValueChanged<PlayerCardResponse> onSwipeUp;
  final ValueChanged<PlayerCardResponse>? onSwipeDown;
  final bool compact;

  @override
  State<_CardCarousel> createState() => _CardCarouselState();
}

class _CardCarouselState extends State<_CardCarousel> {
  late PageController _pageController;

  @override
  void initState() {
    super.initState();
    _pageController = PageController(
      viewportFraction: widget.compact ? 0.3 : 0.42,
      initialPage: widget.currentIndex,
    );
  }

  @override
  void didUpdateWidget(covariant _CardCarousel oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.compact != widget.compact) {
      final page = _pageController.hasClients
          ? _pageController.page?.round() ?? widget.currentIndex
          : widget.currentIndex;
      _pageController.dispose();
      _pageController = PageController(
        viewportFraction: widget.compact ? 0.3 : 0.42,
        initialPage: page,
      );
    } else if (oldWidget.currentIndex != widget.currentIndex &&
        _pageController.hasClients) {
      // Index changed externally (e.g. preview PageView swipe) — sync.
      _pageController.animateToPage(
        widget.currentIndex,
        duration: const Duration(milliseconds: 250),
        curve: Curves.easeInOut,
      );
    }
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    // Enable mouse drag scrolling on desktop (Flutter disables it by default).
    return ScrollConfiguration(
      behavior: ScrollConfiguration.of(context).copyWith(
        dragDevices: {
          PointerDeviceKind.touch,
          PointerDeviceKind.mouse,
          PointerDeviceKind.trackpad,
        },
      ),
      child: PageView.builder(
        controller: _pageController,
        itemCount: widget.cards.length,
        onPageChanged: widget.onIndexChanged,
        itemBuilder: (context, index) {
          final card = widget.cards[index];
          final isActive = index == widget.currentIndex;

          return AnimatedScale(
            scale: isActive ? 1.0 : 0.85,
            duration: const Duration(milliseconds: 200),
            child: AnimatedOpacity(
              opacity: isActive ? 1.0 : 0.6,
              duration: const Duration(milliseconds: 200),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 8),
                child: _DraggableCard(
                  card: card,
                  compact: widget.compact,
                  onSwipeUp: () => widget.onSwipeUp(card),
                  onSwipeDown: widget.onSwipeDown != null
                      ? () => widget.onSwipeDown!(card)
                      : null,
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Draggable card — tracks vertical drag with visual feedback
// ---------------------------------------------------------------------------

class _DraggableCard extends StatefulWidget {
  const _DraggableCard({
    required this.card,
    required this.onSwipeUp,
    this.onSwipeDown,
    this.compact = false,
  });
  final PlayerCardResponse card;
  final VoidCallback onSwipeUp;
  final VoidCallback? onSwipeDown;
  final bool compact;

  @override
  State<_DraggableCard> createState() => _DraggableCardState();
}

class _DraggableCardState extends State<_DraggableCard>
    with SingleTickerProviderStateMixin {
  double _dragOffset = 0;
  static const _upThreshold = -80.0; // Negative = upward.
  static const _downThreshold = 60.0; // Positive = downward.

  late final AnimationController _snapBack;
  double _snapFrom = 0;

  @override
  void initState() {
    super.initState();
    _snapBack =
        AnimationController(
          vsync: this,
          duration: const Duration(milliseconds: 250),
          lowerBound: 0,
          upperBound: 1,
        )..addListener(() {
          setState(() {
            _dragOffset = _snapFrom * (1 - _snapBack.value);
          });
        });
  }

  @override
  void dispose() {
    _snapBack.dispose();
    super.dispose();
  }

  bool get _pastUpThreshold => _dragOffset < _upThreshold;
  bool get _pastDownThreshold =>
      widget.onSwipeDown != null && _dragOffset > _downThreshold;

  /// Fraction of progress toward up trigger (0..1).
  double get _upProgress =>
      (_dragOffset < 0 ? _dragOffset / _upThreshold : 0.0).clamp(0.0, 1.0);

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      // Immediately claim vertical drags so PageView doesn't eat them.
      onVerticalDragStart: (_) {},
      onVerticalDragUpdate: (details) {
        setState(() {
          final maxDown = widget.onSwipeDown != null ? 100.0 : 0.0;
          _dragOffset = (_dragOffset + details.delta.dy).clamp(-150.0, maxDown);
        });
      },
      onVerticalDragEnd: (_) {
        if (_pastUpThreshold) {
          setState(() => _dragOffset = 0);
          widget.onSwipeUp();
        } else if (_pastDownThreshold) {
          setState(() => _dragOffset = 0);
          widget.onSwipeDown!();
        } else {
          _snapFrom = _dragOffset;
          _snapBack.forward(from: 0);
        }
      },
      onVerticalDragCancel: () {
        _snapFrom = _dragOffset;
        _snapBack.forward(from: 0);
      },
      child: Transform.translate(
        offset: Offset(0, _dragOffset),
        child: AnimatedOpacity(
          opacity: (_pastUpThreshold || _pastDownThreshold) ? 0.4 : 1.0,
          duration: const Duration(milliseconds: 100),
          child: Stack(
            clipBehavior: Clip.none,
            children: [
              // Scale down slightly as you drag up.
              Transform.scale(
                scale: 1.0 - _upProgress * 0.08,
                child: CardWidget(card: widget.card, compact: widget.compact),
              ),
              // Upward arrow hint.
              if (_upProgress > 0.1)
                Positioned(
                  top: -24,
                  left: 0,
                  right: 0,
                  child: Icon(
                    CupertinoIcons.arrow_up,
                    size: 18,
                    color: _pastUpThreshold
                        ? ChromaColors.accentGlow
                        : Colors.white38,
                  ),
                ),
              // "EQUIP" label appears near threshold.
              if (_upProgress > 0.5)
                Positioned(
                  top: -42,
                  left: 0,
                  right: 0,
                  child: Text(
                    'EQUIP',
                    textAlign: TextAlign.center,
                    style: TextStyle(
                      color: _pastUpThreshold
                          ? ChromaColors.accentGlow
                          : Colors.white38,
                      fontSize: 10,
                      fontWeight: FontWeight.w800,
                      letterSpacing: 2,
                    ),
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Glowing question-mark help button
// ---------------------------------------------------------------------------

class _GlowingHelpButton extends StatefulWidget {
  const _GlowingHelpButton({required this.onTap});
  final VoidCallback onTap;

  @override
  State<_GlowingHelpButton> createState() => _GlowingHelpButtonState();
}

class _GlowingHelpButtonState extends State<_GlowingHelpButton>
    with SingleTickerProviderStateMixin {
  late final AnimationController _pulse;

  @override
  void initState() {
    super.initState();
    _pulse = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulse.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: widget.onTap,
      child: AnimatedBuilder(
        animation: _pulse,
        builder: (context, child) {
          final glowOpacity = 0.3 + _pulse.value * 0.5;
          return Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              shape: BoxShape.circle,
              color: ChromaColors.bgElevated,
              border: Border.all(
                color: ChromaColors.accentGlow.withValues(alpha: 0.6),
                width: 1.5,
              ),
              boxShadow: [
                BoxShadow(
                  color: ChromaColors.accentGlow.withValues(alpha: glowOpacity),
                  blurRadius: 12,
                  spreadRadius: 2,
                ),
              ],
            ),
            child: const Center(
              child: Text(
                '?',
                style: TextStyle(
                  color: ChromaColors.accentGlow,
                  fontSize: 18,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
          );
        },
      ),
    );
  }
}
