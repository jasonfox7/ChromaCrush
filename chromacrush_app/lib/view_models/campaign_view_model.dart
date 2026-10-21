/// CampaignViewModel — coordinates campaign level lifecycle.
///
/// States: idle → loading → playing → complete / failed.
/// Subscribes to EventBus for game scene events.
library;

import 'dart:async';

import 'package:flutter/widgets.dart';

import '../models/backend_contract.dart';
import '../services/api_client.dart';
import '../services/event_bus.dart';
import '../services/session_manager.dart';

/// Campaign level lifecycle state.
enum CampaignState { idle, loading, playing, complete, failed }

class CampaignViewModel extends ChangeNotifier {
  CampaignViewModel({
    required this.apiClient,
    required this.eventBus,
    required this.sessionManager,
  }) {
    _subscribeToEvents();
  }

  final ApiClientBase apiClient;
  final EventBus eventBus;
  final SessionManager sessionManager;

  // -- Observable state --
  CampaignState state = CampaignState.idle;
  int currentLevel = 1;
  bool isCheckpoint = false;
  Map<String, dynamic>? reward;
  String? attemptId;
  int obstaclesRemaining = 0;
  int movesRemaining = 0;
  int myScore = 0;
  BoardStateResponse? currentBoard;
  String? errorMessage;

  // -- Event subscriptions --
  final List<StreamSubscription<dynamic>> _subscriptions = [];

  void _subscribeToEvents() {
    _subscriptions.add(
      eventBus.on<ScoreUpdatedEvent>().listen((event) {
        myScore = event.newScore;
        notifyListeners();
      }),
    );

    _subscriptions.add(
      eventBus.on<MovesUpdatedEvent>().listen((event) {
        movesRemaining = event.movesRemaining;
        // Detect level failure: out of moves with obstacles still remaining.
        if (movesRemaining == 0 &&
            obstaclesRemaining > 0 &&
            state == CampaignState.playing) {
          state = CampaignState.failed;
        }
        notifyListeners();
      }),
    );

    _subscriptions.add(
      eventBus.on<ObstaclesUpdatedEvent>().listen((event) {
        obstaclesRemaining = event.remaining;
        if (obstaclesRemaining == 0) {
          state = CampaignState.complete;
        }
        notifyListeners();
      }),
    );
  }

  // ---------------------------------------------------------------------------
  // Level lifecycle
  // ---------------------------------------------------------------------------

  /// Start a campaign level: call API, load board.
  ///
  /// [checkpoint] and [levelReward] are persisted for the overlay and survive
  /// retries (the retry path omits them, so the previous values stick).
  Future<void> startLevel(
    int levelNumber, {
    bool? checkpoint,
    Map<String, dynamic>? levelReward,
  }) async {
    // Reset state for new attempt.
    attemptId = null;
    currentBoard = null;
    movesRemaining = 0;
    obstaclesRemaining = 0;
    myScore = 0;
    errorMessage = null;
    currentLevel = levelNumber;
    if (checkpoint != null) isCheckpoint = checkpoint;
    if (levelReward != null) reward = levelReward;
    state = CampaignState.loading;
    WidgetsBinding.instance.addPostFrameCallback((_) => notifyListeners());

    try {
      final result = await apiClient.startCampaignAttempt(levelNumber);

      if (!result.success || result.data == null) {
        state = CampaignState.idle;
        errorMessage = 'Failed to start level';
        notifyListeners();
        return;
      }

      final attempt = result.data!;
      attemptId = attempt.attemptId;
      movesRemaining = attempt.movesRemaining;
      obstaclesRemaining = attempt.obstaclesRemaining;
      currentBoard = attempt.board;

      state = CampaignState.playing;
      notifyListeners();
    } catch (e) {
      state = CampaignState.idle;
      errorMessage = e.toString();
      notifyListeners();
    }
  }

  /// Mark level as failed (out of moves with obstacles remaining).
  void markFailed() {
    if (state != CampaignState.playing) return;
    state = CampaignState.failed;
    notifyListeners();
  }

  /// Abandon the current attempt and return to idle.
  Future<void> abandon() async {
    if (attemptId == null) return;

    try {
      await apiClient.abandonCampaignAttempt(attemptId!);
    } catch (_) {
      // Best-effort — server may have already abandoned.
    }

    state = CampaignState.idle;
    attemptId = null;
    notifyListeners();
  }

  /// Reset to idle state for replay or navigation.
  void reset() {
    state = CampaignState.idle;
    attemptId = null;
    currentBoard = null;
    errorMessage = null;
    notifyListeners();
  }

  @override
  void dispose() {
    for (final sub in _subscriptions) {
      sub.cancel();
    }
    super.dispose();
  }
}
