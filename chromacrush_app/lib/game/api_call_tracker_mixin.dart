/// Mixin that retries API calls on network failure with an overlay.
///
/// When a move/mega API call fails due to a network error (server
/// unreachable), fires [ConnectionSlowEvent] to show the overlay, then
/// retries every 2 seconds until the server responds. On success, fires
/// [ConnectionRestoredEvent] to hide the overlay. Non-network errors
/// (400, 409, 500, etc.) are rethrown immediately.
library;

import '../models/app_error.dart';
import '../services/event_bus.dart';

mixin ApiCallTrackerMixin {
  EventBus get eventBus;

  /// Wrap an API call with network-failure retry and overlay.
  Future<T> trackApiCall<T>(Future<T> Function() apiCall) async {
    bool overlayShown = false;

    while (true) {
      try {
        final result = await apiCall();
        if (overlayShown) {
          eventBus.fire(const ConnectionRestoredEvent());
        }
        return result;
      } on NetworkError {
        // Server unreachable — show overlay and retry.
        if (!overlayShown) {
          overlayShown = true;
          eventBus.fire(const ConnectionSlowEvent());
        }
        await Future<void>.delayed(const Duration(seconds: 2));
      }
      // All other exceptions (ApiError, etc.) propagate normally.
    }
  }
}
