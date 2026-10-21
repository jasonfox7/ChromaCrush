/// Barter screen — tabbed marketplace for buying items with gold or real money.
///
/// Layout:
///   1. Back button (top-left) + title
///   2. Gold balance display (pinned)
///   3. Glass pill tab bar: Energy | Arsenal | Cards | Gold
///   4. Responsive grid of product cards (2 cols on phone, 3+ on tablet)
library;

import 'dart:ui' show PointerDeviceKind;

import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../models/backend_contract.dart';
import '../../services/api_client.dart';
import '../../services/iap_service.dart';
import '../../services/session_manager.dart';
import '../../theme/chroma_theme.dart';
import '../../theme/glass_panel.dart';
import '../shell/starfield_background.dart';

/// Tab definitions for the marketplace.
enum _BarterTab { energy, arsenal, cards, gold }

class BarterScreen extends StatefulWidget {
  const BarterScreen({super.key});

  @override
  State<BarterScreen> createState() => _BarterScreenState();
}

class _BarterScreenState extends State<BarterScreen> {
  bool _loading = true;
  String? _error;
  List<MarketplaceItemResponse> _items = [];
  Map<int, int> _megaCounts = {}; // slot_index → owned count
  String? _buyingItemId;
  _BarterTab _selectedTab = _BarterTab.energy;

  @override
  void initState() {
    super.initState();
    _fetchMarketplace();
  }

  Future<void> _fetchMarketplace() async {
    setState(() {
      _loading = true;
      _error = null;
    });

    try {
      final api = context.read<ApiClientBase>();
      final results = await Future.wait([
        api.getMarketplace(),
        api.getMegaInventory(),
        api.getGold(),
        api.getEnergy(),
      ]);

      if (!mounted) return;

      final marketplace = results[0] as ApiResponse<MarketplaceListResponse>;
      final inventory = results[1] as ApiResponse<MegaInventoryResponse>;
      final gold = results[2] as ApiResponse<GoldResponse>;
      final energy = results[3] as ApiResponse<EnergyResponse>;

      final session = context.read<SessionManager>();
      if (gold.data != null) session.updateGold(gold.data!);
      if (energy.data != null) session.updateEnergy(energy.data!);

      final counts = <int, int>{};
      for (final slot in inventory.data?.slots ?? <MegaInventorySlot>[]) {
        counts[slot.slotIndex] = slot.count;
      }

      final items = marketplace.data?.items ?? [];

      // Extract store product IDs from gold_pack items and load StoreKit
      // products. IDs are server-derived — no hardcoded product list.
      final goldIds = items
          .where((i) => i.itemType == 'gold_iap')
          .map((i) => i.itemParams['store_product_id'] as String?)
          .whereType<String>()
          .toSet();
      if (goldIds.isNotEmpty) {
        final iap = context.read<IapServiceBase>();
        await iap.loadProducts(goldIds);
      }

      setState(() {
        _items = items;
        _megaCounts = counts;
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

  List<MarketplaceItemResponse> _itemsForTab(_BarterTab tab) {
    switch (tab) {
      case _BarterTab.energy:
        return _items.where((i) => i.category == 'energy').toList();
      case _BarterTab.arsenal:
        return _items.where((i) => i.category == 'arsenal').toList();
      case _BarterTab.cards:
        return _items.where((i) => i.category == 'forge_supply').toList();
      case _BarterTab.gold:
        return _items.where((i) => i.category == 'gold_pack').toList();
    }
  }

  Future<void> _buyItem(MarketplaceItemResponse item) async {
    if (_buyingItemId != null) return;

    // Gold IAP — route through StoreKit, not gold purchase.
    if (item.itemType == 'gold_iap') {
      final storeProductId = item.itemParams['store_product_id'] as String?;
      if (storeProductId == null) return;
      setState(() => _buyingItemId = item.itemId);
      try {
        final iap = context.read<IapServiceBase>();
        await iap.buyGoldPack(storeProductId);
      } catch (e) {
        if (mounted) {
          showCupertinoDialog<void>(
            context: context,
            builder: (ctx) => CupertinoAlertDialog(
              title: const Text('Store Unavailable'),
              content: Text('$e'),
              actions: [
                CupertinoDialogAction(
                  onPressed: () => Navigator.of(ctx).pop(),
                  child: const Text('OK'),
                ),
              ],
            ),
          );
        }
      }
      if (!mounted) return;
      setState(() => _buyingItemId = null);
      return;
    }

    setState(() => _buyingItemId = item.itemId);

    try {
      final api = context.read<ApiClientBase>();
      final result = await api.buyItem(BuyItemRequest(itemId: item.itemId));
      if (!mounted) return;

      if (result.data != null) {
        context.read<SessionManager>().updateGoldBalance(
          result.data!.newBalance,
        );
      }

      // Refresh relevant state after purchase.
      if (item.itemType == 'mega_gem') {
        final inv = await api.getMegaInventory();
        if (inv.data != null && mounted) {
          final counts = <int, int>{};
          for (final slot in inv.data!.slots) {
            counts[slot.slotIndex] = slot.count;
          }
          setState(() => _megaCounts = counts);
        }
      } else if (item.itemType == 'heart') {
        final energy = await api.getEnergy();
        if (energy.data != null && mounted) {
          context.read<SessionManager>().updateEnergy(energy.data!);
        }
      }
    } catch (e) {
      if (mounted) {
        showCupertinoDialog<void>(
          context: context,
          builder: (ctx) => CupertinoAlertDialog(
            title: const Text('Purchase Failed'),
            content: Text('$e'),
            actions: [
              CupertinoDialogAction(
                onPressed: () => Navigator.of(ctx).pop(),
                child: const Text('OK'),
              ),
            ],
          ),
        );
      }
    }

    if (!mounted) return;
    setState(() => _buyingItemId = null);
  }

  @override
  Widget build(BuildContext context) {
    final session = context.watch<SessionManager>();
    final goldBalance = session.goldBalance;

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
              LayoutBuilder(
                builder: (context, constraints) {
                  final scale = (constraints.maxHeight / 812).clamp(0.7, 1.3);

                  return Column(
                    children: [
                      SizedBox(height: 20 * scale),

                      // Title.
                      ShaderMask(
                        shaderCallback: (bounds) =>
                            ChromaGradients.accent.createShader(bounds),
                        child: Text(
                          'BARTER',
                          style: TextStyle(
                            color: Colors.white,
                            fontSize: 24 * scale,
                            fontWeight: FontWeight.w900,
                            letterSpacing: 4,
                          ),
                        ),
                      ),

                      SizedBox(height: 12 * scale),

                      // Gold balance.
                      _GoldBalanceHeader(balance: goldBalance, scale: scale),

                      SizedBox(height: 12 * scale),

                      // Tab bar.
                      _GlassPillTabBar(
                        selectedTab: _selectedTab,
                        onTabChanged: (tab) =>
                            setState(() => _selectedTab = tab),
                        scale: scale,
                      ),

                      SizedBox(height: 12 * scale),

                      // Content.
                      Expanded(
                        child: _buildContent(goldBalance, constraints, scale),
                      ),
                    ],
                  );
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildContent(
    int goldBalance,
    BoxConstraints constraints,
    double scale,
  ) {
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
              'Failed to load marketplace',
              style: ChromaText.bodyMedium.copyWith(
                color: ChromaColors.textTertiary,
              ),
            ),
            const SizedBox(height: 12),
            GestureDetector(
              onTap: _fetchMarketplace,
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

    final tabItems = _itemsForTab(_selectedTab);

    // Energy tab has a hearts status row at top.
    final session = context.watch<SessionManager>();
    final showHeartsHeader = _selectedTab == _BarterTab.energy;

    return ScrollConfiguration(
      behavior: ScrollConfiguration.of(context).copyWith(
        dragDevices: {
          PointerDeviceKind.touch,
          PointerDeviceKind.mouse,
          PointerDeviceKind.trackpad,
        },
      ),
      child: CustomScrollView(
        slivers: [
          // Hearts status row for energy tab.
          if (showHeartsHeader)
            SliverToBoxAdapter(
              child: _HeartsStatusRow(energy: session.energy, scale: scale),
            ),

          // Product grid.
          SliverPadding(
            padding: EdgeInsets.symmetric(
              horizontal: constraints.maxWidth * 0.05,
              vertical: 8 * scale,
            ),
            sliver: SliverGrid(
              delegate: SliverChildBuilderDelegate((context, index) {
                final item = tabItems[index];
                final canAfford = item.itemType == 'gold_iap'
                    ? true
                    : goldBalance >= item.price;
                final isBuying = _buyingItemId == item.itemId;
                int? ownedCount;
                if (_megaCounts.isNotEmpty &&
                    item.itemParams.containsKey('slot_index')) {
                  ownedCount =
                      _megaCounts[item.itemParams['slot_index'] as int];
                }
                return _ProductCard(
                  item: item,
                  canAfford: canAfford,
                  isBuying: isBuying,
                  onBuy: () => _buyItem(item),
                  ownedCount: ownedCount,
                  scale: scale,
                );
              }, childCount: tabItems.length),
              gridDelegate: SliverGridDelegateWithMaxCrossAxisExtent(
                maxCrossAxisExtent: constraints.maxWidth * 0.48,
                childAspectRatio: 1.1,
                crossAxisSpacing: 10 * scale,
                mainAxisSpacing: 10 * scale,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Gold balance header
// ---------------------------------------------------------------------------

class _GoldBalanceHeader extends StatelessWidget {
  const _GoldBalanceHeader({required this.balance, required this.scale});
  final int balance;
  final double scale;

  @override
  Widget build(BuildContext context) {
    final coinSize = 24.0 * scale;
    return GlassPanel(
      borderRadius: 20,
      padding: EdgeInsets.symmetric(
        horizontal: 20 * scale,
        vertical: 10 * scale,
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: coinSize,
            height: coinSize,
            decoration: const BoxDecoration(
              shape: BoxShape.circle,
              gradient: LinearGradient(
                begin: Alignment.topLeft,
                end: Alignment.bottomRight,
                colors: [Color(0xFFFFD700), Color(0xFFDAA520)],
              ),
            ),
            child: Center(
              child: Text(
                'G',
                style: TextStyle(
                  color: const Color(0xFF5C3D00),
                  fontSize: 13 * scale,
                  fontWeight: FontWeight.w900,
                ),
              ),
            ),
          ),
          SizedBox(width: 8 * scale),
          Text(
            _formatGold(balance),
            style: TextStyle(
              color: Colors.white,
              fontSize: 20 * scale,
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }

  String _formatGold(int amount) {
    if (amount >= 1000) {
      final formatted = amount.toString().replaceAllMapped(
        RegExp(r'(\d)(?=(\d{3})+(?!\d))'),
        (m) => '${m[1]},',
      );
      return '\u00D7$formatted';
    }
    return '\u00D7$amount';
  }
}

// ---------------------------------------------------------------------------
// Glass pill tab bar
// ---------------------------------------------------------------------------

const _tabLabels = {
  _BarterTab.energy: 'Energy',
  _BarterTab.arsenal: 'Arsenal',
  _BarterTab.cards: 'Cards',
  _BarterTab.gold: 'Gold',
};

class _GlassPillTabBar extends StatelessWidget {
  const _GlassPillTabBar({
    required this.selectedTab,
    required this.onTabChanged,
    required this.scale,
  });
  final _BarterTab selectedTab;
  final ValueChanged<_BarterTab> onTabChanged;
  final double scale;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.symmetric(horizontal: 24 * scale),
      child: Row(
        children: _BarterTab.values.map((tab) {
          final isSelected = tab == selectedTab;
          return Expanded(
            child: Padding(
              padding: EdgeInsets.symmetric(horizontal: 3 * scale),
              child: GestureDetector(
                onTap: () => onTabChanged(tab),
                child: AnimatedContainer(
                  duration: const Duration(milliseconds: 200),
                  curve: Curves.easeOut,
                  padding: EdgeInsets.symmetric(vertical: 8 * scale),
                  decoration: BoxDecoration(
                    gradient: isSelected ? ChromaGradients.accent : null,
                    color: isSelected
                        ? null
                        : Colors.white.withValues(alpha: 0.06),
                    borderRadius: BorderRadius.circular(12 * scale),
                    border: isSelected
                        ? null
                        : Border.all(
                            color: Colors.white.withValues(alpha: 0.1),
                          ),
                  ),
                  child: Center(
                    child: Text(
                      _tabLabels[tab]!,
                      style: TextStyle(
                        color: isSelected ? Colors.white : Colors.white54,
                        fontSize: 11 * scale,
                        fontWeight: isSelected
                            ? FontWeight.w700
                            : FontWeight.w500,
                        letterSpacing: 1,
                      ),
                    ),
                  ),
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Hearts status row (energy tab header)
// ---------------------------------------------------------------------------

class _HeartsStatusRow extends StatelessWidget {
  const _HeartsStatusRow({required this.energy, required this.scale});
  final EnergyResponse? energy;
  final double scale;

  @override
  Widget build(BuildContext context) {
    final hearts = energy?.currentHearts ?? 0;
    final maxHearts = energy?.maxHearts ?? 7;
    final regenSeconds = energy?.secondsToNextHeart;

    return Padding(
      padding: EdgeInsets.symmetric(
        horizontal: MediaQuery.of(context).size.width * 0.05,
        vertical: 8 * scale,
      ),
      child: GlassPanel(
        borderRadius: 14,
        padding: EdgeInsets.symmetric(
          horizontal: 16 * scale,
          vertical: 12 * scale,
        ),
        child: Row(
          children: [
            // Heart icons.
            Expanded(
              child: Wrap(
                spacing: 4 * scale,
                runSpacing: 2 * scale,
                children: List.generate(maxHearts, (i) {
                  final filled = i < hearts;
                  return Icon(
                    filled ? CupertinoIcons.heart_fill : CupertinoIcons.heart,
                    color: filled ? const Color(0xFFFF4D6A) : Colors.white24,
                    size: 18 * scale,
                  );
                }),
              ),
            ),

            // Regen timer.
            if (regenSeconds != null && hearts < maxHearts)
              Text(
                _formatTimer(regenSeconds),
                style: TextStyle(
                  color: Colors.white38,
                  fontSize: 11 * scale,
                  fontWeight: FontWeight.w600,
                ),
              ),
          ],
        ),
      ),
    );
  }

  String _formatTimer(int seconds) {
    final m = seconds ~/ 60;
    final s = seconds % 60;
    return '${m.toString().padLeft(2, '0')}:${s.toString().padLeft(2, '0')}';
  }
}

// ---------------------------------------------------------------------------
// Product card
// ---------------------------------------------------------------------------

const _megaIcons = <String, IconData>{
  'mega_shuffle_20': CupertinoIcons.shuffle,
  'mega_hh_10': CupertinoIcons.arrow_right_arrow_left,
  'mega_vv_10': CupertinoIcons.arrow_up_arrow_down,
  'mega_bb_5': CupertinoIcons.burst,
  'mega_oo_1': CupertinoIcons.circle_grid_hex,
};

const _rarityColors = <String, Color>{
  'common': Color(0xFF8A8A8A),
  'rare': Color(0xFF4FC3F7),
  'epic': Color(0xFFCE93D8),
  'legendary': Color(0xFFFFD54F),
};

class _ProductCard extends StatelessWidget {
  const _ProductCard({
    required this.item,
    required this.canAfford,
    required this.isBuying,
    required this.onBuy,
    required this.scale,
    this.ownedCount,
  });
  final MarketplaceItemResponse item;
  final bool canAfford;
  final bool isBuying;
  final VoidCallback onBuy;
  final double scale;
  final int? ownedCount;

  IconData get _icon {
    switch (item.itemType) {
      case 'mega_gem':
        return _megaIcons[item.itemId] ?? CupertinoIcons.star;
      case 'heart':
        return CupertinoIcons.heart_fill;
      case 'card_pack':
        return CupertinoIcons.rectangle_stack;
      case 'gold_iap':
        return CupertinoIcons.circle_fill;
      default:
        return CupertinoIcons.square_grid_2x2;
    }
  }

  Color get _accentColor {
    switch (item.itemType) {
      case 'mega_gem':
        return ChromaColors.accent;
      case 'heart':
        return const Color(0xFFFF4D6A);
      case 'card_pack':
        return _rarityColors[item.itemParams['rarity']] ?? Colors.white54;
      case 'gold_iap':
        return const Color(0xFFFFD700);
      default:
        return Colors.white54;
    }
  }

  bool get _isGoldIap => item.itemType == 'gold_iap';

  @override
  Widget build(BuildContext context) {
    return GlassPanel(
      borderRadius: 16 * scale,
      padding: EdgeInsets.zero,
      child: Padding(
        padding: EdgeInsets.all(12 * scale),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            // Icon + owned count.
            Column(
              children: [
                Icon(_icon, color: _accentColor, size: 28 * scale),
                if (ownedCount != null) ...[
                  SizedBox(height: 2 * scale),
                  Text(
                    'Owned: $ownedCount',
                    style: TextStyle(
                      color: Colors.white.withValues(alpha: 0.35),
                      fontSize: 8 * scale,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ],
              ],
            ),

            // Name + quantity/description.
            Column(
              children: [
                Text(
                  item.name,
                  textAlign: TextAlign.center,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 12 * scale,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                SizedBox(height: 2 * scale),
                Text(
                  _isGoldIap
                      ? '${_formatNumber(item.quantity)} gold'
                      : '\u00D7${item.quantity}',
                  style: TextStyle(
                    color: Colors.white.withValues(alpha: 0.5),
                    fontSize: 10 * scale,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ],
            ),

            // Price button.
            GestureDetector(
              onTap: canAfford && !isBuying ? onBuy : null,
              child: Container(
                padding: EdgeInsets.symmetric(
                  horizontal: 12 * scale,
                  vertical: 7 * scale,
                ),
                decoration: BoxDecoration(
                  gradient: canAfford && !isBuying
                      ? ChromaGradients.accent
                      : null,
                  color: canAfford
                      ? null
                      : Colors.white.withValues(alpha: 0.06),
                  borderRadius: BorderRadius.circular(10 * scale),
                  border: canAfford
                      ? null
                      : Border.all(color: Colors.white.withValues(alpha: 0.1)),
                ),
                child: _isGoldIap ? _buildDollarPrice() : _buildGoldPrice(),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildGoldPrice() {
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        // Gold coin mini.
        Container(
          width: 12 * scale,
          height: 12 * scale,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: canAfford
                ? const Color(0xFFFFD700)
                : Colors.white.withValues(alpha: 0.2),
          ),
        ),
        SizedBox(width: 4 * scale),
        Text(
          isBuying ? '...' : '${item.price}',
          style: TextStyle(
            color: canAfford ? Colors.white : Colors.white30,
            fontSize: 11 * scale,
            fontWeight: FontWeight.w700,
          ),
        ),
      ],
    );
  }

  Widget _buildDollarPrice() {
    final cents = item.itemParams['cents'] as int? ?? item.price;
    final dollars = cents / 100;
    final priceStr = dollars == dollars.truncateToDouble()
        ? '\$${dollars.toInt()}'
        : '\$${dollars.toStringAsFixed(2)}';

    return Text(
      isBuying ? '...' : priceStr,
      style: TextStyle(
        color: Colors.white,
        fontSize: 11 * scale,
        fontWeight: FontWeight.w700,
      ),
    );
  }

  String _formatNumber(int n) {
    return n.toString().replaceAllMapped(
      RegExp(r'(\d)(?=(\d{3})+(?!\d))'),
      (m) => '${m[1]},',
    );
  }
}
