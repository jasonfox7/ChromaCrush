/// In-app purchase service — StoreKit integration for gold packs.
///
/// On iOS: connects to App Store via `in_app_purchase` package, handles
/// purchase flow, sends receipts to backend for validation + gold crediting.
/// On Windows (dev): stub that logs calls without real purchases.
///
/// Product IDs are server-derived: the barter screen fetches marketplace
/// data and calls [loadProducts] with the store_product_ids from gold_pack
/// items. No hardcoded product IDs in the frontend.
library;

import 'dart:async';
import 'dart:io' show Platform;

import 'package:flutter/foundation.dart';
import 'package:in_app_purchase/in_app_purchase.dart';

import '../models/backend_contract.dart';
import 'api_client.dart';
import 'debug_logger.dart';
import 'session_manager.dart';

/// Abstract interface for testability.
abstract class IapServiceBase {
  Future<void> init();
  Future<void> loadProducts(Set<String> productIds);
  Future<void> buyGoldPack(String productId);
  bool get available;
  bool get productsLoaded;
  void dispose();
}

/// Concrete StoreKit IAP service for iOS.
class StoreKitIapService implements IapServiceBase {
  StoreKitIapService({
    required ApiClientBase apiClient,
    required SessionManager sessionManager,
    required DebugLogger debugLogger,
  }) : _api = apiClient,
       _session = sessionManager,
       _log = debugLogger;

  final ApiClientBase _api;
  final SessionManager _session;
  final DebugLogger _log;

  StreamSubscription<List<PurchaseDetails>>? _subscription;
  Set<ProductDetails> _products = {};
  bool _available = false;
  bool _productsLoaded = false;

  @override
  bool get available => _available;

  @override
  bool get productsLoaded => _productsLoaded;

  @override
  Future<void> init() async {
    final iap = InAppPurchase.instance;
    _available = await iap.isAvailable();
    if (!_available) {
      _log.logError('IAP: Store not available');
      return;
    }

    // Listen to purchase updates. Product query is deferred to
    // loadProducts() — called by the barter screen with server-derived IDs.
    _subscription = iap.purchaseStream.listen(
      _handlePurchaseUpdate,
      onError: (Object error) {
        _log.logError('IAP: Purchase stream error: $error');
      },
    );

    _log.logApiRequest(
      '/iap/init',
      'IAP',
      body: {'available': _available, 'productsLoaded': false},
    );
  }

  @override
  Future<void> loadProducts(Set<String> productIds) async {
    if (!_available || productIds.isEmpty) return;

    final iap = InAppPurchase.instance;
    final response = await iap.queryProductDetails(productIds);
    if (response.error != null) {
      _log.logError('IAP: Product query error: ${response.error}');
    }
    _products = response.productDetails.toSet();
    _productsLoaded = _products.isNotEmpty;
    _log.logApiRequest(
      '/iap/loadProducts',
      'IAP',
      body: {
        'requested': productIds.length,
        'found': _products.length,
      },
    );
  }

  @override
  Future<void> buyGoldPack(String productId) async {
    final product = _products.firstWhere(
      (p) => p.id == productId,
      orElse: () => throw StateError('Product not found: $productId'),
    );
    final purchaseParam = PurchaseParam(productDetails: product);
    await InAppPurchase.instance.buyConsumable(purchaseParam: purchaseParam);
  }

  Future<void> _handlePurchaseUpdate(
    List<PurchaseDetails> purchaseDetailsList,
  ) async {
    for (final purchase in purchaseDetailsList) {
      bool serverConfirmed = false;

      if (purchase.status == PurchaseStatus.purchased ||
          purchase.status == PurchaseStatus.restored) {
        if (_session.accessToken != null) {
          serverConfirmed = await _verifyAndDeliver(purchase);
        } else {
          // Not authenticated yet — StoreKit delivers pending transactions
          // on app start before sign-in. Don't complete: let StoreKit
          // redeliver after auth so the customer gets their gold.
          _log.logError(
            'IAP: Skipping validation (not authenticated), will retry later',
            context: {
              'productId': purchase.productID,
              'transactionId': purchase.purchaseID,
            },
          );
        }
      } else if (purchase.status == PurchaseStatus.error) {
        _log.logError(
          'IAP: Purchase error: ${purchase.error?.message}',
          context: {'productId': purchase.productID},
        );
      }

      // Only complete (finish) the transaction after the server has
      // confirmed receipt — either as a new purchase or a known duplicate.
      // This guarantees the customer's gold is credited before we tell
      // StoreKit to stop redelivering. We skip the pendingCompletePurchase
      // guard because finishTransaction on an already-finished transaction
      // is a documented no-op, and the guard was silently preventing stuck
      // transactions from being cleared.
      if (serverConfirmed) {
        try {
          await InAppPurchase.instance.completePurchase(purchase);
        } catch (e) {
          _log.logError(
            'IAP: completePurchase failed: $e',
            context: {
              'productId': purchase.productID,
              'transactionId': purchase.purchaseID,
            },
          );
        }
      }
    }
  }

  /// Sends receipt to backend for validation and gold crediting.
  /// Returns true if the server confirmed the purchase (new or duplicate).
  Future<bool> _verifyAndDeliver(PurchaseDetails purchase) async {
    try {
      final result = await _api.validatePurchase(
        ValidatePurchaseRequest(
          productId: purchase.productID,
          receiptData: purchase.verificationData.serverVerificationData,
          provider: 'apple',
          transactionId: purchase.purchaseID ?? '',
        ),
      );

      if (result.data != null) {
        // Refresh gold balance after successful purchase.
        final gold = await _api.getGold();
        if (gold.data != null) {
          _session.updateGold(gold.data!);
        }
        _log.logApiRequest(
          '/iap/delivered',
          'IAP',
          body: {
            'productId': purchase.productID,
            'transactionId': purchase.purchaseID,
          },
        );
      }

      // Server returned 200 — purchase is recorded (new or duplicate).
      return true;
    } catch (e) {
      _log.logError(
        'IAP: Delivery failed: $e',
        context: {'productId': purchase.productID},
      );
      // Don't complete — let StoreKit redeliver so we can retry.
      return false;
    }
  }

  @override
  void dispose() {
    _subscription?.cancel();
  }
}

/// Stub IAP service for Windows development and testing.
class StubIapService implements IapServiceBase {
  StubIapService({DebugLogger? debugLogger}) : _log = debugLogger;

  final DebugLogger? _log;

  @override
  bool get available => false;

  @override
  bool get productsLoaded => false;

  @override
  Future<void> init() async {
    _log?.logApiRequest(
      '/iap/init',
      'IAP_STUB',
      body: {'available': false, 'reason': 'StubIapService (non-iOS platform)'},
    );
  }

  @override
  Future<void> loadProducts(Set<String> productIds) async {}

  @override
  Future<void> buyGoldPack(String productId) async {
    _log?.logError('IAP stub: buyGoldPack called on non-iOS platform');
  }

  @override
  void dispose() {}
}

/// Factory — returns real service on iOS, stub elsewhere.
IapServiceBase createIapService({
  required ApiClientBase apiClient,
  required SessionManager sessionManager,
  required DebugLogger debugLogger,
}) {
  if (!kIsWeb && Platform.isIOS) {
    return StoreKitIapService(
      apiClient: apiClient,
      sessionManager: sessionManager,
      debugLogger: debugLogger,
    );
  }
  return StubIapService(debugLogger: debugLogger);
}
